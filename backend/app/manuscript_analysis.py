"""Evidence-based heuristic review. No neural model, automatic casting or SFX."""
import json
from copy import deepcopy
import re
import threading
import uuid
from collections import defaultdict
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text as sql
from .narrative import key, speaker_match
from .scenes import included
from .voice_editor import now, signature
from .narrative_cues import sound_cues, build_scene_plan
from .sound_direction import editorial

router = APIRouter(prefix='/api/projects/{pid}/analysis', tags=['Manuscript review'])
ACTIVE = threading.Lock()
TOKEN = re.compile(r"\b[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]*(?:[-’'][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*\b")
IGNORE = set('el la los las un una unos unas yo tu él ella nosotros ellos usted ustedes mi mis su sus que qué como cómo cuando cuándo donde dónde porque por para pero aunque mientras entonces después antes ahora aquí allí si sí no nunca siempre nada todo todos cada había habia era eran fue fueron ser estar es son hay se le les lo al del de a y o e ni en con sin sobre entre hasta desde hacia tras también muy más menos capítulo capitulo escena fin isbn copyright nota notas prólogo prefacio epílogo dedicatoria narrador sin atribuir hola adiós gracias buenos buenas señor señora'.split())
PERSON_CONTEXT = re.compile(r'\b(?:dijo|respondió|preguntó|exclamó|susurró|gritó|replicó|contestó|llamó|llamaba|llamado|llamada|señor|señora|don|doña)\s*$', re.I)
PLACE_CONTEXT = re.compile(r'\b(?:en|hacia|desde|hasta|a)\s+(?:(?:la|el|los|las)\s+)?$', re.I)
PLACES = re.compile(r'\b(?:casa|bosque|ciudad|pueblo|hospital|escuela|oficina|laboratorio|habitación|cuarto|cocina|sótano|calle|carretera|río|playa|montaña|castillo|estación|puerto|iglesia|biblioteca|cueva|jardín|mar|océano|costa|muelle|avenida|autopista|parque|restaurante|aeropuerto|barco|desierto)\b', re.I)
TRANSITION = re.compile(r'^\s*(?:al día siguiente|a la mañana siguiente|horas después|días después|años después|más tarde|mientras tanto|en otro lugar|esa noche|int\.|ext\.|interior\b|exterior\b|escena\s+\d+|poco después|al amanecer|al anochecer|a medianoche|a kilómetros de allí|lejos de allí|(?:llegaron|llegó|entraron|entró|salieron|salió)\s+(?:a|al|en|del)\b)', re.I)
EMOTIONS = {
 'euforia':r'\b(?:euforia|eufóric[oa]s?|júbilo|exaltación)\b',
 'miedo':r'\b(?:miedo|aterrad[oa]s?|temblaba|terror|pánico)\b',
 'ira':r'\b(?:furios[oa]s?|ira|rabia|enojad[oa]s?|indignad[oa]s?)\b',
 'tristeza':r'\b(?:tristeza|triste|llor[óo]|lloraba|solloz[óo]|sollozaba)\b',
 'alegría':r'\b(?:alegría|feliz|felices|rió|reía|sonrió|entusiasm[oa])\b',
 'sorpresa':r'\b(?:sorprendid[oa]s?|asombrad[oa]s?|boquiabiert[oa]s?)\b',
 'voz baja':r'\b(?:susurr[óo]|susurraba|en voz baja)\b',
 'voz elevada':r'\b(?:grit[óo]|gritaba|a gritos)\b',
}



def context():
 from . import main
 return main


def document_token(p,include_scenes=True):
 return signature({'original':p.get('original'),
   'chapters':[{**{k:ch[k] for k in ('id','title')},'segments':[{k:s.get(k) for k in ('id','text','source_text','speaker','scene','excluded','revision') if include_scenes or k!='scene'} for s in ch['segments']]} for ch in p['chapters']]})


def negated(text, start):
 prefix=text[max(0,start-45):start]
 prefix=re.split(r'[.!?;:,]', prefix)[-1]
 return bool(re.search(r'\b(?:no|sin|nunca|jamás|ni)\b(?:\W+\w+){0,3}\W*$',prefix,re.I))


def analyze_project(p):
 names={}; places={}; emotions=[]; sounds=[]; boundaries=[]; scenes={}; total=0
 cast={key(c['name']):c for c in p.get('characters',[])}
 def entity(table,name,evidence,signal):
  normalized=key(name)
  item=table.setdefault(normalized,{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,p['id']+':'+('person' if table is names else 'place')+':'+normalized)),
   'name':name,'variants':[],'count':0,'signals':[],'evidence':[],'existing_character_id':cast.get(normalized,{}).get('id') if table is names else None})
  if name not in item['variants']:item['variants'].append(name)
  if sum(c in 'ÁÉÍÓÚÜÑáéíóúüñ' for c in name)>sum(c in 'ÁÉÍÓÚÜÑáéíóúüñ' for c in item['name']):item['name']=name
  item['count']+=1
  if signal not in item['signals']:item['signals'].append(signal)
  if evidence not in item['evidence']:item['evidence'].append(evidence)
 for ch in p['chapters']:
  for index,s in enumerate(ch['segments'],1):
   if s.get('is_separator'):continue
   total+=1;text=s['text'];source=s.get('source_text',text)
   evidence={'chapter_id':ch['id'],'chapter':ch['title'],'segment_id':s['id'],'fragment':index,'scene':s.get('scene',1),'text':text[:800],'excluded':not included(s)}
   scene_key=(ch['id'],s.get('scene',1));scene=scenes.setdefault(scene_key,{'chapter_id':ch['id'],'chapter':ch['title'],'scene':s.get('scene',1),'segments':0,'included_segments':0,'first_segment_id':s['id'],'text':text[:800]})
   scene['segments']+=1;scene['included_segments']+=int(included(s))
   speaker=s.get('speaker','')
   if key(speaker) not in ('','sin atribuir','sin asignar','narrador'):
    entity(names,speaker,evidence,'atribución guardada')
   label=speaker_match(source)
   if label and key(label[1]) not in IGNORE and re.fullmatch(r"[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑáéíóúüñ .’'-]*",label[1]):
    if key(label[1])!=key(speaker):entity(names,label[1].strip(),evidence,'etiqueta de diálogo')
   # Compound personal names: explicit speech attribution, address or treatment.
   compound_spans=[]
   compound_pattern=r"\b(?:dijo|respondió|preguntó|exclamó|susurró|gritó|replicó|contestó|señor|señora|don|doña)\s+([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+(?:(?:de la|de|del)\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){1,3})"
   for group in re.finditer(compound_pattern,text):
    entity(names,group.group(1),evidence,'nombre después de atribución o tratamiento')
    compound_spans.append(group.span(1))
   for group in re.finditer(r"\b([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+(?:(?:de la|de|del)\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){0,3})\s+(?:dijo|preguntó|respondió|susurró|gritó|contestó)\b",text):
    if key(group.group(1)) not in IGNORE:
     entity(names,group.group(1),evidence,'nombre después de atribución o tratamiento')
     compound_spans.append(group.span(1))
   for match in TOKEN.finditer(text):
    if any(a<=match.start()<b for a,b in compound_spans):continue
    name=match.group();normalized=key(name)
    if len(name)<2 or normalized in IGNORE or name.isupper() and len(name)==2:continue
    before=text[:match.start()]
    if PERSON_CONTEXT.search(before):signal='nombre después de atribución o tratamiento'
    elif normalized in cast:signal='coincide con el elenco'
    elif PLACE_CONTEXT.search(before):
     entity(places,name,evidence,'nombre después de preposición de lugar');signal='nombre propio ambiguo: persona o lugar'
    elif re.search(r'[¿¡—«“]\s*$',before):signal='posible vocativo'
    else:signal='mayúscula: candidato sin confirmar'
    entity(names,name,evidence,signal)
   for match in PLACES.finditer(text):
    entity(places,match.group().lower(),evidence,'término de lugar; confirmar ubicación')
   if index>1 and TRANSITION.match(text):
    previous=ch['segments'][index-2]
    if previous.get('scene')==s.get('scene'):
     boundaries.append({'segment_id':s['id'],**evidence,'reason':'Cambio explícito de tiempo, lugar o encabezado; puede continuar la escena actual'})
   for label,pattern in EMOTIONS.items():
    for match in re.finditer(pattern,text,re.I):
     if not negated(text,match.start()):emotions.append({**evidence,'label':label,'cue':match.group(),'speaker':speaker,'certainty':'sugerencia léxica; no atribuye emoción a una persona'})
   if not editorial(ch['title'],text):sounds.extend({**evidence,**cue} for cue in sound_cues(text))
 for candidate in names.values():
  candidate['review']='existente' if candidate['existing_character_id'] else 'pendiente'
  candidate['evidence_level']='fuerte' if any(s in candidate['signals'] for s in ('atribución guardada','etiqueta de diálogo','nombre después de atribución o tratamiento')) else ('repetido' if candidate['count']>=2 else 'débil')
 result={'version':2,'method':'reglas locales ampliadas, contexto por oración y plan sonoro por escena; sin modelo semántico',
  'content_token':document_token(p,False),'document_token':document_token(p),'created_at':now(),'segments':total,
  'names':sorted(names.values(),key=lambda x:(x['evidence_level']=='débil',-x['count'],x['name'])),
  'places':sorted(places.values(),key=lambda x:-x['count']), 'scenes':list(scenes.values()),
  'scene_candidates':boundaries,'emotions':emotions,'sound_suggestions':sounds,
  'limits':['No garantiza encontrar todos los personajes o cambios de escena.',
   'Las mayúsculas pueden ser lugares o palabras de inicio de oración.',
   'Las emociones y efectos necesitan revisión del contexto; no se asignan ni mezclan automáticamente.']}
 result['scene_plan']=build_scene_plan(result)
 return result


def read_job(pid,jid):
 m=context();m.get(pid)
 with m.engine.connect() as c:row=c.execute(sql('SELECT payload FROM jobs WHERE id=:id'),{'id':jid}).first()
 j=json.loads(row[0]) if row else None
 if not j or j.get('kind')!='manuscript-analysis' or j.get('project_id')!=pid:raise HTTPException(404,'Análisis no encontrado')
 return j


def save_job(j):
 from .voice_editor import save_job as persist
 persist(j)


@router.post('/jobs',status_code=202)
def start(pid:str):
 m=context()
 with m.lock:
  p=m.get(pid)
  if not p['chapters']:raise HTTPException(409,'Importa un manuscrito antes de analizar')
  if not ACTIVE.acquire(blocking=False):raise HTTPException(409,'Hay un análisis en curso')
  j={'id':str(uuid.uuid4()),'kind':'manuscript-analysis','project_id':pid,'status':'queued','created_at':now()}
  try:
   with m.engine.begin() as c:c.execute(sql('INSERT INTO jobs VALUES (:id,:p)'),{'id':j['id'],'p':json.dumps(j)})
   threading.Thread(target=worker,args=(j,p),daemon=True).start()
  except Exception:ACTIVE.release();raise
 return j


def worker(j,p):
 try:
  j['status']='running';save_job(j)
  report=analyze_project(p);name=str(uuid.uuid4())+'.analysis.json'
  (context().DATA/name).write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
  j.update(status='completed',report_file=name,finished_at=now());save_job(j)
 except Exception:
  j.update(status='error',message='No se pudo completar el análisis. Los datos del proyecto se conservan.');save_job(j)
 finally:ACTIVE.release()


@router.get('/jobs')
def list_jobs(pid:str):
 m=context();m.get(pid)
 with m.engine.connect() as c:values=[json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM jobs'))]
 return [j for j in values if j.get('kind')=='manuscript-analysis' and j.get('project_id')==pid]


@router.get('/jobs/{jid}')
def status(pid:str,jid:str):return read_job(pid,jid)


def synchronized_report(r,p,jid):
 """Reproject scene metadata only when the original analyzed content is provable.

 Legacy reports have no content fingerprint. Undo this job's recorded scene
 changes in a detached copy and require the exact original document hash.
 Never infer safety from excerpts, timestamps or a user-supplied override.
 """
 r=deepcopy(r);current=document_token(p)
 safe=current==r['document_token'] or (bool(r.get('content_token')) and r['content_token']==document_token(p,False))
 if not safe and not r.get('content_token'):
  candidate=deepcopy(p)
  for action in reversed(p.get('manuscript_reviews',[])):
   if action.get('job_id')!=jid or action.get('category')!='scene' or action.get('decision')!='confirm' or action.get('undone_at'):continue
   previous={x['id']:x['scene'] for x in action.get('previous_scenes',[])}
   for ch in candidate['chapters']:
    for segment in ch['segments']:
     if segment['id'] in previous:segment['scene']=previous[segment['id']]
  safe=document_token(candidate)==r['document_token']
 if not safe:
  r['stale']=True
  return r
 # Keep IDs of original scene rows so already reviewed rows retain their state.
 original_ids={row['first_segment_id']:str(row.get('id',i)) for i,row in enumerate(r.get('scenes',[]))}
 segments={seg['id']:(ch,seg,i) for ch in p['chapters'] for i,seg in enumerate(ch['segments'],1)}
 def update(value):
  if isinstance(value,list):
   for v in value:update(v)
  elif isinstance(value,dict):
   sid=value.get('segment_id') or value.get('first_segment_id')
   if sid in segments:
    ch,seg,i=segments[sid];value['scene']=seg.get('scene',1)
    if 'fragment' in value:value['fragment']=i
    if 'chapter' in value:value['chapter']=ch['title']
    if 'excluded' in value:value['excluded']=not included(seg)
   for v in value.values():
    if isinstance(v,(dict,list)):update(v)
 update(r)
 scenes={}
 for ch in p['chapters']:
  for seg in ch['segments']:
   if seg.get('is_separator'):continue
   k=(ch['id'],seg.get('scene',1))
   row=scenes.setdefault(k,{'id':original_ids.get(seg['id'],'scene:'+seg['id']),'chapter_id':ch['id'],'chapter':ch['title'],
     'scene':seg.get('scene',1),'segments':0,'included_segments':0,'first_segment_id':seg['id'],'text':seg['text'][:800]})
   row['segments']+=1;row['included_segments']+=int(included(seg))
 r['scenes']=list(scenes.values());r['scene_plan']=build_scene_plan(r)
 r.update(document_token=current,content_token=document_token(p,False),stale=False,scene_metadata_refreshed=current!=r['document_token'])
 return r


@router.get('/jobs/{jid}/report')
def report(pid:str,jid:str):
 m=context();j=read_job(pid,jid)
 if j['status']!='completed':raise HTTPException(409,'El análisis todavía no está listo')
 from .project_cleanup import safe_file
 path=safe_file(m.DATA,j.get('report_file'))
 if path is None or not path.is_file():raise HTTPException(404,'Informe no encontrado')
 with m.lock:
  result=json.loads(path.read_text(encoding='utf-8'))
  return synchronized_report(result,m.get(pid),jid)


class Review(BaseModel):
 job_id:str
 document_token:str
 category:str=Field(pattern=r'^(name|scene|place|emotion|sound|current_scene|editorial_scene)$')
 item_id:str
 decision:str=Field(pattern=r'^(confirm|reject)$')


CATEGORIES={'name':'names','scene':'scene_candidates','place':'places','emotion':'emotions',
 'sound':'sound_suggestions','current_scene':'scenes','editorial_scene':'editorial_scenes'}


def review_item(r,category,item_id):
 item=next((v for i,v in enumerate(r.get(CATEGORIES[category],[])) if str(v.get('id',i))==item_id),None)
 if item is None:raise HTTPException(404,'Sugerencia no encontrada')
 if category=='editorial_scene' and item.get('status')!='matched':raise HTTPException(409,'La escena editorial no tiene una coincidencia única en el manuscrito')
 return item


def record_decision(p,r,body,item):
 prior=next((a for a in reversed(p.get('manuscript_reviews',[])) if a['job_id']==body.job_id and a['category']==body.category and a['item_id']==body.item_id and not a.get('undone_at')),None)
 if prior:
  if prior['decision']!=body.decision:raise HTTPException(409,'La sugerencia ya tiene otra decisión guardada')
  return prior,False
 action={'at':now(),'job_id':body.job_id,'category':body.category,'item_id':body.item_id,'decision':body.decision,'evidence':item}
 if body.decision=='confirm' and body.category=='name':
  if item.get('kind')=='animal' or (r.get('imported_editorial') and not item.get('evidence')):raise HTTPException(409,'Esta entidad no tiene evidencia humana vinculada para añadirla al elenco')
  character=next((c for c in p['characters'] if key(c['name'])==key(item['name'])),None)
  if character is None:
   character={'id':str(uuid.uuid4()),'name':item['name'],'voice':'em_santa','speed':1.0,'color':'#9C68FF'}
   p['characters'].append(character)
  action['character_id']=character['id']
 elif body.decision=='confirm' and body.category=='scene':
  ch=next(ch for ch in p['chapters'] if ch['id']==item['chapter_id']);idx=next(i for i,s in enumerate(ch['segments']) if s['id']==item['segment_id'])
  if idx==0:raise HTTPException(409,'El capítulo ya empieza con una escena')
  action['previous_scenes']=[{'id':s['id'],'scene':s.get('scene',1)} for s in ch['segments']]
  # Preserve existing boundaries and add the selected one; no segment/audio is deleted.
  number=1;previous=None
  for i,s in enumerate(ch['segments']):
   old=s.get('scene',1)
   if i and (i==idx or old!=previous):number+=1
   s['scene']=number;previous=old
  p['scene_rules_version']=1
 p.setdefault('manuscript_reviews',[]).append(action)
 return action,True


def checked_report(pid,job_id,token):
 r=report(pid,job_id)
 if r['stale'] or r['document_token']!=token:raise HTTPException(409,'El proyecto cambió. Ejecuta otro análisis antes de aplicar decisiones')
 return r


@router.post('/review')
def review(pid:str,body:Review):
 m=context()
 with m.lock:
  p=m.get(pid);r=checked_report(pid,body.job_id,body.document_token)
  item=review_item(r,body.category,body.item_id)
  action,changed=record_decision(p,r,body,item)
  if changed:m.save(p)
 return {'project':p,'review':action,'report':synchronized_report(r,p,body.job_id)}


class BatchReview(BaseModel):
 job_id:str
 document_token:str
 category:str=Field(pattern=r'^(name|scene|place|emotion|sound|current_scene|editorial_scene)$')
 item_ids:list[str]=Field(min_length=1,max_length=10000)
 decision:str=Field(pattern=r'^(confirm|reject)$')
 confirmed:bool=False


@router.post('/review-batch')
def review_batch(pid:str,body:BatchReview):
 if not body.confirmed:raise HTTPException(422,'Confirma la decisión sobre las sugerencias seleccionadas')
 m=context()
 with m.lock:
  p=m.get(pid);r=checked_report(pid,body.job_id,body.document_token)
  ids=list(dict.fromkeys(body.item_ids));actions=[];changed=0
  # p is detached JSON. No write occurs until every item has been validated and
  # processed. A stale report or invalid item leaves the whole batch unapplied.
  for item_id in ids:
   one=Review(job_id=body.job_id,document_token=body.document_token,category=body.category,item_id=item_id,decision=body.decision)
   item=review_item(r,body.category,item_id)
   action,modified=record_decision(p,r,one,item);actions.append(action);changed+=int(modified)
  if changed:m.save(p)
  refreshed=synchronized_report(r,p,body.job_id)
 return {'project':p,'reviews':actions,'applied':changed,'already_reviewed':len(actions)-changed,'stale':refreshed['stale'],'report':refreshed}


def recover_jobs():
 m=context()
 with m.engine.begin() as c:
  for jid,payload in list(c.execute(sql('SELECT id,payload FROM jobs'))):
   j=json.loads(payload)
   if j.get('kind')=='manuscript-analysis' and j.get('status') in ('queued','running'):
    j.update(status='interrupted',message='Análisis interrumpido por reinicio; puedes iniciarlo otra vez')
    c.execute(sql('UPDATE jobs SET payload=:p WHERE id=:id'),{'id':jid,'p':json.dumps(j)})

@router.post('/undo-scene')
def undo_scene(pid:str):
 m=context()
 with m.lock:
  p=m.get(pid)
  action=next((a for a in reversed(p.get('manuscript_reviews',[])) if a['category']=='scene' and a['decision']=='confirm' and not a.get('undone_at')),None)
  if not action:raise HTTPException(409,'No hay una división de escena para deshacer')
  ch=next(ch for ch in p['chapters'] if ch['id']==action['evidence']['chapter_id'])
  # Restore scene numbers only; all text, voices and audio remain untouched.
  previous={s['id']:s['scene'] for s in action['previous_scenes']}
  for s in ch['segments']:
   if s['id'] in previous:s['scene']=previous[s['id']]
  action['undone_at']=now();m.save(p)
 return p
