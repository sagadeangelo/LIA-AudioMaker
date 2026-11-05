"""Persistent reusable media catalog, with independent copies and user classifications."""
import copy,hashlib,json,shutil,uuid
from typing import Literal
from fastapi import APIRouter,HTTPException,File,Form,UploadFile
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import text
from . import sound_mixer as sm
from .project_cleanup import safe_file
from .tts_provider import KOKORO_VOICES,provider_for_voice
router=APIRouter(prefix='/api/media-library',tags=['Media library'])
def initialize():
 with sm.main().engine.begin() as db:db.execute(text('CREATE TABLE IF NOT EXISTS media_catalog (id VARCHAR(120) PRIMARY KEY, payload TEXT NOT NULL)'))
def records():
 with sm.main().engine.connect() as db:return [json.loads(row[0]) for row in db.execute(text('SELECT payload FROM media_catalog'))]
def store(item,update_links=False):
 with sm.main().engine.begin() as db:
  if db.execute(text('SELECT id FROM media_catalog WHERE id=:id'),{'id':item['id']}).first():db.execute(text('UPDATE media_catalog SET payload=:p WHERE id=:id'),{'id':item['id'],'p':json.dumps(item,ensure_ascii=False)})
  else:db.execute(text('INSERT INTO media_catalog(id,payload) VALUES (:id,:p)'),{'id':item['id'],'p':json.dumps(item,ensure_ascii=False)})
  if update_links and item['kind']!='voice':
   for row in list(db.execute(text('SELECT payload FROM projects'))):
    project=json.loads(row[0]);changed=False
    for sound in project.get('sound_effects',[]):
     if sound.get('catalog_id')==item['id']:
      sound.update({k:item[k] for k in ('name','media_kind','music_category','effect_category') if k in item});changed=True
    if changed:db.execute(text('UPDATE projects SET payload=:p WHERE id=:id'),{'id':project['id'],'p':json.dumps(project,ensure_ascii=False)})
 return item

def voice_profiles(ids=None):return [{k:v for k,v in row.items() if k in ('voice_id','name','gender','age_group','role','tags')} for row in records() if row.get('kind')=='voice' and (ids is None or row.get('voice_id') in ids)]
class Classification(BaseModel):
 model_config=ConfigDict(extra='forbid')
 name:str=Field(min_length=1,max_length=200)
 kind:Literal['music','effect','voice']
 category:str=Field(default='Sin clasificar',max_length=100)
 gender:Literal['Sin clasificar','Mujer','Hombre']='Sin clasificar'
 age_group:Literal['Sin clasificar','Niño','Adulto','Adulto mayor']='Sin clasificar'
 role:Literal['Personaje','Narrador','Ambos']='Personaje'
 tags:list[str]=Field(default_factory=list,max_length=20)
class Adopt(Classification):
 project_id:str
 sound_id:str
class Voice(Classification):
 voice_id:str
class Import(BaseModel):
 project_id:str

@router.get('')
def catalog(project_id:str|None=None):
 with sm.main().lock:
  p=sm.main().get(project_id) if project_id else None
  voices=set(KOKORO_VOICES)
  with sm.main().engine.connect() as db:projects=[json.loads(r[0]) for r in db.execute(text('SELECT payload FROM projects'))]
  for project in projects:
   if not project.get('deleted_at'):voices.update(c.get('voice','') for c in project.get('characters',[]))
  result=records()
  for item in result:
   if item['kind']!='voice':item['exists']=bool(sm.wav_info(item.get('file')))
  return {'items':result,'project_sounds':copy.deepcopy(p.get('sound_effects',[])) if p else [],'voices':sorted(v for v in voices if v)}

@router.post('/adopt')
def adopt(body:Adopt):
 if sm.ACTIVE.locked():raise HTTPException(409,'Espera a que termine la mezcla antes de añadir medios al proyecto.')
 if body.kind=='voice':raise HTTPException(422,'Registra las voces en el apartado Voces.')
 with sm.main().lock:
  p=sm.main().get(body.project_id);sound=next((s for s in p.get('sound_effects',[]) if s['id']==body.sound_id),None)
  if not sound:raise HTTPException(404,'El recurso no pertenece a este proyecto.')
  source=safe_file(sm.main().DATA,sound.get('file'))
  if not source or not sm.wav_info(source.name):raise HTTPException(409,'El archivo del recurso no está disponible.')
  key=hashlib.sha256((hashlib.sha256(source.read_bytes()).hexdigest()+sound.get('license','')+sound.get('author','')).encode()).hexdigest()
  item=next((r for r in records() if r['id']==key),None);created=None
  if item is None or not sm.wav_info(item.get('file')):
   created=sm.main().DATA/('media_catalog_'+uuid.uuid4().hex+'.wav');shutil.copyfile(source,created)
   item={**copy.deepcopy(sound),'id':key,'file':created.name,'kind':body.kind}
  item.update(body.model_dump(exclude={'project_id','sound_id'}));item['media_kind']=body.kind
  item['music_category' if body.kind=='music' else 'effect_category']=body.category
  try:store(item)
  except Exception:
   if created:created.unlink(missing_ok=True)
   raise
  sound.update(media_kind=body.kind,catalog_id=key,**{('music_category' if body.kind=='music' else 'effect_category'):body.category})
  sm.main().save(p)
  return item

@router.put('/items/{item_id}')
def classify(item_id:str,body:Classification):
 if sm.ACTIVE.locked():raise HTTPException(409,'Espera a que termine la mezcla antes de cambiar clasificaciones vinculadas.')
 with sm.main().lock:
  item=next((r for r in records() if r['id']==item_id),None)
  if not item:raise HTTPException(404,'Recurso no encontrado en la biblioteca de medios.')
  if (item['kind']=='voice')!=(body.kind=='voice'):raise HTTPException(422,'Una voz de motor no se convierte en archivo de música o efecto.')
  item.update(body.model_dump())
  item['classification_saved']=True
  if body.kind!='voice':item['media_kind']=body.kind;item['music_category' if body.kind=='music' else 'effect_category']=body.category
  return store(item,update_links=True)

@router.post('/voices')
def classify_voice(body:Voice):
 if body.kind!='voice':raise HTTPException(422,'Selecciona el apartado Voces.')
 try:provider_for_voice(body.voice_id)
 except ValueError:raise HTTPException(422,'Voz no compatible con los motores actuales.') from None
 with sm.main().lock:return store({'id':'voice:'+body.voice_id,**body.model_dump()})

@router.post('/items/{item_id}/use')
def use(item_id:str,body:Import):
 if sm.ACTIVE.locked():raise HTTPException(409,'Espera a que termine la mezcla antes de importar medios al proyecto.')
 with sm.main().lock:
  p=sm.main().get(body.project_id);item=next((r for r in records() if r['id']==item_id and r['kind']!='voice'),None)
  if not item:raise HTTPException(404,'Archivo no encontrado en la biblioteca de medios.')
  existing=next((s for s in p.get('sound_effects',[]) if s.get('catalog_id')==item_id and sm.wav_info(s.get('file'))),None)
  if existing:return {'sound':existing,'already_saved':True}
  source=safe_file(sm.main().DATA,item.get('file'))
  if not source or not sm.wav_info(source.name):raise HTTPException(409,'El archivo de la biblioteca no está disponible.')
  target=sm.main().DATA/('sfx_library_'+uuid.uuid4().hex+'.wav');shutil.copyfile(source,target)
  sound={**copy.deepcopy(item),'id':uuid.uuid4().hex,'catalog_id':item_id,'file':target.name,'media_kind':item['kind']}
  p.setdefault('sound_effects',[]).append(sound)
  try:sm.main().save(p)
  except Exception:target.unlink(missing_ok=True);raise
  return {'sound':sound,'already_saved':False}


@router.post('/sync')
def sync_downloaded():
 """Register existing project downloads without altering scene assignments."""
 if sm.ACTIVE.locked():raise HTTPException(409,'Espera a que termine la mezcla para actualizar la biblioteca.')
 added=0;missing=0
 with sm.main().lock:
  known={r['id'] for r in records()}
  with sm.main().engine.connect() as db:projects=[json.loads(row[0]) for row in db.execute(text('SELECT payload FROM projects'))]
  for project in projects:
   if project.get('deleted_at'):continue
   for sound in project.get('sound_effects',[]):
    if sound.get('catalog_id') in known:continue
    if not sm.wav_info(sound.get('file')):missing+=1;continue
    source=safe_file(sm.main().DATA,sound.get('file'))
    key=hashlib.sha256((hashlib.sha256(source.read_bytes()).hexdigest()+sound.get('license','')+sound.get('author','')).encode()).hexdigest()
    if key in known:
     current=sm.main().get(project['id'])
     linked=next(s for s in current['sound_effects'] if s['id']==sound['id'])
     linked['catalog_id']=key;sm.main().save(current)
     continue
    kind='music' if sound.get('media_kind')=='music' or sound.get('music_category') else 'effect'
    category=sound.get('music_category' if kind=='music' else 'effect_category') or 'Sin clasificar'
    item=adopt(Adopt(project_id=project['id'],sound_id=sound['id'],name=sound.get('name') or 'Recurso descargado',kind=kind,category=category))
    if item['id'] not in known:added+=1;known.add(item['id'])
 return {'added':added,'missing':missing}


@router.post('/uploads',status_code=201)
def upload_catalog(file:UploadFile=File(...),name:str=Form('',max_length=200),author:str=Form('',max_length=200),origin:str=Form('own',max_length=20),license_note:str=Form('',max_length=500),kind:Literal['music','effect']=Form('music'),music_category:str=Form('',max_length=100)):
 from .sound_upload import upload
 return upload(pid=None,file=file,name=name,author=author,origin=origin,license_note=license_note,gid='',scene_id='',kind=kind,music_category=music_category)
