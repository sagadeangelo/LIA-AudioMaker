"""Explicit, reversible dialogue/acotation splits. Never interpret review prose as code."""
import copy
import json
import re
import uuid
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import text as sql
from . import sound_mixer as sm
from .voice_editor import signature,now
from .scenes import included

router=APIRouter(prefix='/api/projects/{pid}/production-exchange/plans/{plan_id}/splits',tags=['Production dialogue splits'])
class Preview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    segment_id:str=Field(min_length=1,max_length=100)
    narration_text:str=Field(min_length=1,max_length=20000)
    dialogue_character_id:str=Field(min_length=1,max_length=100)
    narrator_character_id:str=Field(min_length=1,max_length=100)
class Apply(Preview):
    preview_token:str
    confirmed:bool=False
class Undo(BaseModel):
    confirmed:bool=False

def record(p,pid):
    x=next((x for x in p.get('production_plans',[]) if x['id']==pid),None)
    if not x:raise HTTPException(404,'Plan no encontrado en este proyecto.')
    return x

def guard(p):
    m=sm.main()
    with m.engine.connect() as db:jobs=[json.loads(row[0]) for row in db.execute(sql('SELECT payload FROM jobs'))]
    if any(j.get('project_id',j.get('pid'))==p['id'] and j.get('status') in ('queued','running') for j in jobs):raise HTTPException(409,'Espera a que terminen los trabajos del proyecto antes de dividir o deshacer.')
    if any(x.get('status') in ('queued','running') for x in p.get('sound_mixes',[])) or sm.ACTIVE.locked():raise HTTPException(409,'Espera a que termine la mezcla activa.')

def proposal(text,name):
    # Conservative suggestion only: quote closes before a third-person action or attribution.
    pattern=r'[»”"](?P<tail>\s+[“"]?(?:'+re.escape(name)+r'\b|(?:dijo|murmuró|murmurando|susurró|susurrando|respondió|preguntó|gritó|exclamó)\b).+)$'
    match=re.search(pattern,text,re.S|re.I)
    return match.group('tail') if match else ''

def permitted(record):
    plan=record['plan'];allowed=set()
    for scene in plan['scenes']:
        for i,perf in enumerate(scene.get('performances',[])):
            allowed.add(perf['segment_id'])
    return allowed

def make_preview(p,rec,body):
    if body.segment_id not in permitted(rec):raise HTTPException(422,'El fragmento no pertenece al plan guardado.')
    ch=next((ch for ch in p['chapters'] if any(s['id']==body.segment_id for s in ch['segments'])),None)
    source=next((s for s in ch['segments'] if s['id']==body.segment_id),None) if ch else None
    if source is None or not included(source):raise HTTPException(409,'El fragmento ya no está incluido.')
    if any(h['original']['id']==body.segment_id and not h.get('undone_at') for h in rec.get('splits',[])):raise HTTPException(409,'Este fragmento ya fue dividido. Consulta el historial o deshaz la división.')
    original=next(x for scene in rec['plan']['scenes'] for x in scene.get('performances',[]) if x['segment_id']==source['id'])
    if original['quote'] not in source['text']:raise HTTPException(409,'El texto cambió desde el plan. Revisa una nueva exportación antes de dividir.')
    suffix=body.narration_text
    if not source['text'].endswith(suffix):raise HTTPException(422,'La acotación debe coincidir exactamente con el final del texto actual, incluidos espacios y signos.')
    cut=len(source['text'])-len(suffix);prefix=source['text'][:cut]
    if not prefix.strip() or not suffix.strip():raise HTTPException(422,'La división necesita dos partes con texto.')
    if any(c.get('segment_id')==source['id'] for c in p.get('sound_cues',[])):raise HTTPException(409,'Este fragmento tiene pistas asignadas. Revisa o retira esas asignaciones antes de dividirlo para no desplazar sonidos.')
    chars={c['id']:c for c in p.get('characters',[])}
    if body.dialogue_character_id not in chars or body.narrator_character_id not in chars:raise HTTPException(422,'Selecciona dos personajes existentes en el proyecto.')
    if body.dialogue_character_id==body.narrator_character_id:raise HTTPException(422,'El diálogo y la acotación deben tener personajes distintos.')
    a=chars[body.dialogue_character_id];b=chars[body.narrator_character_id]
    token=signature({'source':source,'body':body.model_dump(include=set(Preview.model_fields)),'characters':[a,b],'review_revision':rec.get('review_revision',0),'chapter_order':[s['id'] for s in ch['segments']]})
    return {'preview_token':token,'segment_id':source['id'],'original_text':source['text'],'text_preserved':prefix+suffix==source['text'],
        'parts':[{'text':prefix,'character_id':a['id'],'speaker':a['name'],'voice':a['voice'],'speed':a.get('speed',1),'kind':'dialogue'},
                 {'text':suffix,'character_id':b['id'],'speaker':b['name'],'voice':b['voice'],'speed':b.get('speed',1),'kind':'narration'}],
        'notice':'Se conservará el audio anterior en el respaldo. Las dos partes necesitan audio nuevo; el resto del libro se conserva.'}

@router.get('')
def candidates(pid:str,plan_id:str):
    m=sm.main()
    with m.lock:p=copy.deepcopy(m.get(pid))
    rec=record(p,plan_id);rows=[];allowed=permitted(rec)
    for ch in p['chapters']:
        for seg in ch['segments']:
            if seg['id'] not in allowed or not included(seg):continue
            if any(h['original']['id']==seg['id'] and not h.get('undone_at') for h in rec.get('splits',[])):continue
            tail=proposal(seg['text'],seg.get('speaker',''))
            if tail:rows.append({'segment_id':seg['id'],'text':seg['text'],'suggested_narration':tail,'speaker':seg.get('speaker'),'character_id':seg.get('character_id')})
    history=[]
    for h in rec.get('splits',[]):
        audio=h['original'].get('audio');info=sm.wav_info(audio)
        history.append({'id':h['id'],'original_text':h['original']['text'],'created_at':h['created_at'],'undone_at':h.get('undone_at'),'part_ids':h['part_ids'],'original_audio_url':'/api/audio/'+audio if info else None,'parts':[{k:s.get(k) for k in ('id','text','speaker','voice','audio','duration')} for ch in p['chapters'] for s in ch['segments'] if s['id'] in h['part_ids']]})
    return {'candidates':rows,'characters':[{'id':x['id'],'name':x['name'],'voice':x['voice']} for x in p.get('characters',[])],'history':history}

@router.post('/preview')
def preview(pid:str,plan_id:str,body:Preview):
    with sm.main().lock:p=copy.deepcopy(sm.main().get(pid))
    return make_preview(p,record(p,plan_id),body)

@router.post('/apply')
def apply(pid:str,plan_id:str,body:Apply):
    if not body.confirmed:raise HTTPException(422,'Confirma la división y las voces de ambas partes.')
    m=sm.main()
    with m.lock:
        p=m.get(pid);rec=record(p,plan_id);guard(p);pr=make_preview(p,rec,body)
        if body.preview_token!=pr['preview_token']:raise HTTPException(409,'La previsualización cambió. Vuelve a preparar la división.')
        ch=next(ch for ch in p['chapters'] if any(s['id']==body.segment_id for s in ch['segments']));index=next(i for i,s in enumerate(ch['segments']) if s['id']==body.segment_id);original=copy.deepcopy(ch['segments'][index]);sid=uuid.uuid4().hex
        parts=[]
        for i,part in enumerate(pr['parts']):
            char=next(x for x in p['characters'] if x['id']==part['character_id'])
            parts.append({**{k:copy.deepcopy(original[k]) for k in ('scene','source_line','excluded') if k in original},**part,
                'id':original['id'] if i==0 else str(uuid.uuid4()),'source_text':part['text'],'color':char.get('color','#00D9CE'),
                'speaker_confirmed':True,'review':False,'content_review':False,'review_reason':'','versions':[],'audio':None,'duration':0,'revision':original.get('revision',0)+1,'production_split_id':sid})
        assert ''.join(x['text'] for x in parts)==original['text']
        ch['segments'][index:index+1]=parts
        rec.setdefault('splits',[]).append({'id':sid,'chapter_id':ch['id'],'created_at':now(),'original':original,'part_ids':[x['id'] for x in parts],'after_signature':signature(parts)})
        m.save(p)
        return {'split_id':sid,'parts':parts,'text_preserved':True,'message':'División aplicada. Se guardó respaldo del fragmento y su audio. Las dos partes están pendientes de generar.'}

@router.post('/{split_id}/undo')
def undo(pid:str,plan_id:str,split_id:str,body:Undo):
    if not body.confirmed:raise HTTPException(422,'Confirma restaurar el fragmento original.')
    m=sm.main()
    with m.lock:
        p=m.get(pid);rec=record(p,plan_id);guard(p);h=next((x for x in rec.get('splits',[]) if x['id']==split_id),None)
        if not h or h.get('undone_at'):raise HTTPException(409,'Esta división no está activa.')
        ch=next((x for x in p['chapters'] if x['id']==h['chapter_id']),None)
        if ch is None:raise HTTPException(409,'El capítulo cambió.')
        positions=[i for i,s in enumerate(ch['segments']) if s['id'] in h['part_ids']]
        if len(positions)!=2 or positions[1]!=positions[0]+1:raise HTTPException(409,'Las partes cambiaron de posición.')
        parts=ch['segments'][positions[0]:positions[1]+1]
        if [s['id'] for s in parts]!=h['part_ids'] or signature(parts)!=h['after_signature']:raise HTTPException(409,'Las partes fueron editadas o ya generadas; no se restauran automáticamente para proteger ese trabajo.')
        if any(c.get('segment_id') in h['part_ids'] for c in p.get('sound_cues',[])):raise HTTPException(409,'Hay nuevas pistas en las partes. Revísalas antes de restaurar.')
        ch['segments'][positions[0]:positions[1]+1]=[copy.deepcopy(h['original'])];h['undone_at']=now();m.save(p)
        return {'restored':True}
