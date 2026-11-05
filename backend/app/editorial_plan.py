"""Import a reviewed external editorial plan by textual anchors, never replace manuscript/audio."""
import json
import re
import uuid
from functools import lru_cache
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from .narrative import key
from .scenes import included
from .voice_editor import now, signature
from .manuscript_analysis import context, document_token, save_job
from .narrative_cues import build_scene_plan

router=APIRouter(prefix='/api/projects/{pid}/analysis/editorial',tags=['Editorial plan'])

class Sound(BaseModel):
 name:str=Field(min_length=1,max_length=160)
 quote:str=Field(min_length=1,max_length=1200)
 kind:Literal['efecto','ambiente']='efecto'
 basis:Literal['explícita','inferida']='explícita'
 note:str=Field(default='',max_length=2000)

class Scene(BaseModel):
 id:str=Field(min_length=1,max_length=100)
 chapter:int=Field(ge=1,le=1000)
 title:str=Field(min_length=1,max_length=300)
 start_anchor:str=Field(min_length=12,max_length=1200)
 place:str=Field(max_length=600)
 characters:list[str]=Field(default_factory=list,max_length=100)
 emotions:list[str]=Field(default_factory=list,max_length=30)
 layer:str=Field(max_length=100)
 notes:str=Field(default='',max_length=3000)
 sounds:list[Sound]=Field(default_factory=list,max_length=100)
 avoid:list[str]=Field(default_factory=list,max_length=60)

class Character(BaseModel):
 id:str=Field(min_length=1,max_length=100)
 name:str=Field(min_length=1,max_length=100)
 aliases:list[str]=Field(default_factory=list,max_length=30)
 role:str=Field(max_length=2000)
 evidence:str=Field(min_length=4,max_length=1200)
 kind:Literal['person','animal']='person'
 review:str=Field(default='',max_length=300)

class Plan(BaseModel):
 format:Literal['lia.editorial-plan']
 version:Literal[1]
 title:str=Field(min_length=1,max_length=300)
 language:str='es'
 source:str=Field(default='',max_length=2000)
 scope:str=Field(default='',max_length=2000)
 characters:list[Character]=Field(default_factory=list,max_length=500)
 scenes:list[Scene]=Field(min_length=1,max_length=1500)
 notes:list[str]=Field(default_factory=list,max_length=100)
 non_diegetic_names:list[dict]=Field(default_factory=list,max_length=100)
 collectives:list[str]=Field(default_factory=list,max_length=100)
 embedded_references:list[str]=Field(default_factory=list,max_length=100)
 sections:list[dict]=Field(default_factory=list,max_length=100)
 @model_validator(mode='after')
 def unique(self):
  if len(json.dumps(self.model_dump(),ensure_ascii=False).encode('utf-8'))>2000000:raise ValueError('El plan supera 2 MB')
  for items in (self.scenes,self.characters):
   if len({x.id for x in items})!=len(items):raise ValueError('Identificadores repetidos en el plan')
  return self

class Preview(BaseModel):
 plan:Plan

class Apply(Preview):
 preview_token:str
 confirmed:bool=False
 accept_unresolved:bool=False
 apply_boundaries:bool=False


@lru_cache(maxsize=8192)
def normalized(s):return re.sub(r'[^\w]+',' ',key(s),flags=re.U).strip()


def chapter_number(ch):
 match=re.match(r'^\s*cap[ií]tulo\s+([ivxlcdm]+|\d+)\b',ch['title'],re.I)
 if not match:return None
 value=match[1].upper()
 if value.isdigit():return int(value)
 values={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000};total=0;previous=0
 for c in reversed(value):
  n=values[c];total+=-n if n<previous else n;previous=max(previous,n)
 return total


def locate(p,quote,number=None):
 q=normalized(quote)
 if len(q)<12:return []
 found=[]
 for ch in p['chapters']:
  if number is not None and chapter_number(ch)!=number:continue
  for i,s in enumerate(ch['segments']):
   if s.get('is_separator'):continue
   hits=[normalized(s.get(k,'')) for k in ('text','source_text')]
   if any(q in value for value in hits):
    # Complete source-line prefix is required for an actual boundary. Mid-segment
    # anchor remains annotation only; never split an existing produced fragment.
    at_start=any(value.startswith(q) for value in hits)
    found.append((ch,i,s,at_start))
 return found


def evidence(hit):
 ch,i,s,_=hit
 return {'chapter_id':ch['id'],'chapter':ch['title'],'segment_id':s['id'],'fragment':i+1,
   'scene':s.get('scene',1),'text':s['text'],'excluded':not included(s)}


def resolve(p,plan):
 rows=[];boundaries={};unresolved=[];cue_rows=[]
 for scene in plan.scenes:
  hits=locate(p,scene.start_anchor,scene.chapter)
  row={'id':scene.id,'title':scene.title,'chapter_number':scene.chapter,'layer':scene.layer,
       'anchor':scene.start_anchor,'status':'matched' if len(hits)==1 else ('ambiguous' if hits else 'missing')}
  if len(hits)==1:
   hit=hits[0];row.update(evidence(hit),can_divide=bool(hit[3] and hit[1]>0 and included(hit[2])))
   if row['can_divide']:boundaries.setdefault(hit[0]['id'],set()).add(hit[1])
   if not hit[3]:row['notice']='El ancla cae dentro de un fragmento: se anota sin dividir ni regenerar el audio.'
  else:unresolved.append({'category':'scene','id':scene.id,'quote':scene.start_anchor,'status':row['status']})
  rows.append(row)
  for idx,cue in enumerate(scene.sounds):
   matches=locate(p,cue.quote,scene.chapter)
   cid=scene.id+':'+str(idx)
   status='matched' if len(matches)==1 else ('ambiguous' if matches else 'missing')
   cr={'id':cid,'scene_id':scene.id,'status':status,**cue.model_dump()}
   if len(matches)==1:cr.update(evidence(matches[0]))
   else:unresolved.append({'category':'sound','id':cid,'quote':cue.quote,'status':status})
   cue_rows.append(cr)
 # A pasted text anchor cannot prove the whole manuscript's identity. Coverage is
 # explicit, and application is blocked if fewer than half of scene starts match.
 matched=sum(r['status']=='matched' for r in rows)
 token=signature({'project_id':p['id'],'document':document_token(p),'plan':plan.model_dump()})
 return {'preview_token':token,'title':plan.title,'scene_count':len(rows),'matched_scenes':matched,
  'sound_count':len(cue_rows),'matched_sounds':sum(r['status']=='matched' for r in cue_rows),
  'eligible_boundaries':sum(len(v) for v in boundaries.values()),'unresolved':unresolved,
  'scenes':rows,'sounds':cue_rows,'can_import':matched>=max(1,(len(rows)+1)//2)},boundaries


def make_report(p,plan,preview):
 from .manuscript_analysis import analyze_project
 base=analyze_project(p)
 base.update(method='Lectura editorial externa con anclas textuales verificadas; no ejecución de un modelo local',
  imported_editorial=True,editorial_title=plan.title,editorial_notes=plan.notes,
  editorial_scenes=[],editorial_unresolved=preview['unresolved'],names=[],places=[],emotions=[],sound_suggestions=[],scene_candidates=[])
 def ent(name,ev,**extra):
  return {'id':str(uuid.uuid4()),'name':name,'variants':[name],'count':len(ev),'signals':['lectura editorial del manuscrito'],
     'evidence':ev,'evidence_level':'fuerte' if ev else 'débil','review':'pendiente',**extra}
 for c in plan.characters:
  hits=locate(p,c.evidence)
  # Short, unsupported or changed source quotations stay visible for review but
  # can never trigger automatic casting. No alias matching or merging here.
  cast=next((v for v in p.get('characters',[]) if key(v['name'])==key(c.name)),{})
  base['names'].append(ent(c.name,[evidence(h) for h in hits],variants=c.aliases,role=c.role,kind=c.kind,
      existing_character_id=cast.get('id'),source_evidence=c.evidence))
 resolved={r['id']:r for r in preview['scenes']}
 for scene in plan.scenes:
  row=resolved[scene.id];data=scene.model_dump();data.update(status=row['status'])
  if row['status']=='matched':
   data.update({k:row[k] for k in ('chapter','chapter_id','segment_id','fragment','scene','text','excluded')})
   base['places'].append(ent(scene.place,[{k:row[k] for k in ('chapter','chapter_id','segment_id','fragment','scene','text','excluded')}]))
   for label in scene.emotions:base['emotions'].append({**evidence_from_row(row),'label':label,'certainty':'lectura editorial de la unidad; no emoción de todos los hablantes'})
  else:data['chapter']=f'Capítulo {scene.chapter}'
  base['editorial_scenes'].append(data)
 for cue in preview['sounds']:
  if cue['status']!='matched':continue
  scene=next(s for s in plan.scenes if s.id==cue['scene_id'])
  base['sound_suggestions'].append({**evidence_from_row(cue),'label':cue['name'],'kind':cue['kind'],
   'cue':cue['quote'],'context_text':cue['quote'],'context_status':'revisar contexto' if scene.layer in ('sueño narrado','ficción dentro de ficción','relato de terceros') else 'posible sonido presente',
   'reason':f"{scene.title} · {scene.layer} · Evidencia {cue['basis']}. {cue['note']}",
   'basis':cue['basis'],'editorial_scene_id':scene.id,'requires_context_review':True,
   'placement':'escena' if cue['kind']=='ambiente' else 'fragmento','timing':'sin sincronización temporal; no insertado'})
 base['scene_plan']=build_scene_plan(base)
 base['limits']=['El plan se vincula por citas; coincidencias ausentes o ambiguas no se aplican.',
  'Las escenas son propuestas editoriales; sus subdivisiones no cambian por sí solas el audio.',
  'No se insertaron sonidos ni se modificaron voces, texto, pronunciaciones o versiones de audio.']
 return base


def evidence_from_row(row):
 return {k:row[k] for k in ('chapter','chapter_id','segment_id','fragment','scene','text','excluded')}


@router.post('/preview')
def preview(pid:str,body:Preview):return resolve(context().get(pid),body.plan)[0]


@router.post('/import',status_code=201)
def apply(pid:str,body:Apply):
 m=context()
 with m.lock:
  p=m.get(pid);pr,bounds=resolve(p,body.plan)
  if not body.confirmed:raise HTTPException(422,'Confirma la importación del plan')
  if body.preview_token!=pr['preview_token']:raise HTTPException(409,'El proyecto o el plan cambió. Vuelve a revisar la importación')
  if not pr['can_import']:raise HTTPException(409,'Coinciden menos de la mitad de las escenas; revisa que sea la misma edición del libro')
  if pr['unresolved'] and not body.accept_unresolved:raise HTTPException(422,'Revisa y acepta las citas sin coincidencia antes de importar parcialmente')
  if any(j.get('token')==body.preview_token for j in p.get('editorial_imports',[])):
   raise HTTPException(409,'Este plan ya se importó con este estado del manuscrito')
  previous=[]
  if body.apply_boundaries:
   for ch in p['chapters']:
    idxs=bounds.get(ch['id'],set())
    if not idxs:continue
    old=[{'id':s['id'],'scene':s.get('scene',1)} for s in ch['segments']];number=1;last=None
    for i,s in enumerate(ch['segments']):
     current=s.get('scene',1)
     if i and (i in idxs or current!=last):number+=1
     s['scene']=number;last=current
    after=[{'id':s['id'],'scene':s.get('scene',1)} for s in ch['segments']]
    if old!=after:previous.append({'chapter_id':ch['id'],'before':old,'after':after})
   p['scene_rules_version']=1
  jid=str(uuid.uuid4());filename=jid+'.analysis.json'
  pr,_=resolve(p,body.plan);r=make_report(p,body.plan,pr)
  r['document_token']=document_token(p);r['editorial_import_id']=jid
  path=m.DATA/filename
  path.write_text(json.dumps(r,ensure_ascii=False),encoding='utf-8')
  j={'id':jid,'kind':'manuscript-analysis','project_id':pid,'status':'completed','created_at':now(),
       'finished_at':now(),'report_file':filename,'source':'editorial-import'}
  record={'id':jid,'at':now(),'title':body.plan.title,'token':body.preview_token,'plan':body.plan.model_dump(),'scene_changes':previous}
  p.setdefault('editorial_imports',[]).append(record)
  # All persistent project/job metadata commits together. No audio file writes.
  with m.engine.begin() as c:
   from sqlalchemy import text as sql
   c.execute(sql('UPDATE projects SET payload=:p WHERE id=:id'),{'p':json.dumps(p,ensure_ascii=False),'id':pid})
   c.execute(sql('INSERT INTO jobs VALUES (:id,:p)'),{'id':jid,'p':json.dumps(j)})
  return {'project':p,'job':j,'summary':pr,'changed_chapters':len(previous)}

class Undo(BaseModel):
 import_id:str
 confirmed:bool=False

@router.post('/undo')
def undo(pid:str,body:Undo):
 m=context()
 with m.lock:
  if not body.confirmed:raise HTTPException(422,'Confirma la restauración de divisiones')
  p=m.get(pid);record=next((x for x in p.get('editorial_imports',[]) if x['id']==body.import_id),None)
  if record is None or record.get('undone_at'):raise HTTPException(409,'Importación inexistente o ya restaurada')
  if not record['scene_changes']:raise HTTPException(409,'Este plan no cambió las divisiones')
  for change in record['scene_changes']:
   ch=next((c for c in p['chapters'] if c['id']==change['chapter_id']),None)
   if not ch or [{'id':s['id'],'scene':s.get('scene',1)} for s in ch['segments']]!=change['after']:
    raise HTTPException(409,'Las escenas cambiaron después; no se restauraron divisiones')
  for change in record['scene_changes']:
   ch=next(c for c in p['chapters'] if c['id']==change['chapter_id']);old={s['id']:s['scene'] for s in change['before']}
   for s in ch['segments']:s['scene']=old[s['id']]
  record['undone_at']=now();m.save(p)
  return p
