import os, json, uuid, subprocess, shutil, wave, struct, threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text as sql
from .narrative import extract, analyze, key
from .casting import ensure_cast, needs_content_review, assign, undo

DATA = Path(os.getenv('DATA_DIR', 'data')).resolve(); DATA.mkdir(parents=True, exist_ok=True)
engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///' + str(DATA / 'lia.db')))
# Versioned initial schema. JSON documents preserve original text and segment history.
with engine.begin() as c:
    c.execute(sql('CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)'))
    c.execute(sql('CREATE TABLE IF NOT EXISTS projects (id VARCHAR(36) PRIMARY KEY, payload TEXT NOT NULL)'))
    c.execute(sql('CREATE TABLE IF NOT EXISTS jobs (id VARCHAR(36) PRIMARY KEY, payload TEXT NOT NULL)'))
    if not c.execute(sql('SELECT version FROM schema_versions WHERE version=1')).first(): c.execute(sql('INSERT INTO schema_versions VALUES (1)'))
lock = threading.RLock()

def save(p):
    with engine.begin() as c:
        c.execute(sql('UPDATE projects SET payload=:p WHERE id=:id'), {'p':json.dumps(p,ensure_ascii=False),'id':p['id']})
def get(pid):
    with engine.connect() as c: row = c.execute(sql('SELECT payload FROM projects WHERE id=:id'), {'id':pid}).first()
    if not row: raise HTTPException(404,'Proyecto no encontrado')
    p=json.loads(row[0]); ensure_cast(p); return p
def segment(p, sid):
    for ch in p['chapters']:
        for s in ch['segments']:
            if s['id'] == sid: return s
    raise HTTPException(404,'Fragmento no encontrado')

app = FastAPI(title='LIA AudioMaker', version='0.1.3')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['*'], allow_headers=['*'])
class Project(BaseModel):
    title: str = Field(min_length=1,max_length=200)
class Edit(BaseModel):
    speaker: str = Field(min_length=1,max_length=100)
    voice: str = Field(pattern=r'^(es|en)(\+m[1-7]|\+f[1-5])?$')
    speed: int = Field(default=160,ge=80,le=300)
    color: str = Field(default='#00D9CE',pattern=r'^#[0-9a-fA-F]{6}$')
    reviewed: bool = False
    @field_validator('speaker')
    @classmethod
    def valid_speaker(cls,value):
        value=value.strip()
        if not value or key(value) in ('sin atribuir','sin asignar'): raise ValueError('Selecciona un hablante válido')
        return value

class Character(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    voice: str = Field(default='es',pattern=r'^(es|en)(\+m[1-7]|\+f[1-5])?$')
    speed: int = Field(default=160,ge=80,le=300)
    color: str = Field(default='#F018A8',pattern=r'^#[0-9a-fA-F]{6}$')
    @field_validator('name')
    @classmethod
    def valid_name(cls,value): return Edit.valid_speaker(value)

class Assignment(BaseModel):
    character_id: str
class UndoAssignment(BaseModel):
    token: str


@app.get('/api/health')
def health():
    with engine.connect() as c: c.execute(sql('SELECT 1'))
    return {'status':'ok','database':'ok','tts': bool(shutil.which('espeak-ng') or shutil.which('espeak')), 'ffmpeg':bool(shutil.which('ffmpeg'))}
@app.get('/api/projects')
def projects():
    with engine.connect() as c:
        result=[json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM projects'))]
    for p in result: ensure_cast(p)
    return result
@app.post('/api/projects',status_code=201)
def create(body: Project):
    p = {'id':str(uuid.uuid4()),'title':body.title,'original':'','chapters':[]}
    ensure_cast(p)
    with engine.begin() as c: c.execute(sql('INSERT INTO projects VALUES (:id,:p)'), {'id':p['id'],'p':json.dumps(p)})
    return p
@app.get('/api/projects/{pid}')
def project(pid:str): return get(pid)
@app.post('/api/projects/{pid}/manuscript')
async def manuscript(pid:str, file:UploadFile):
    data = await file.read(15_000_001)
    if len(data)>15_000_000: raise HTTPException(413,'Limite: 15 MB')
    try: original = extract(data,Path(file.filename or '').suffix.lower())
    except Exception as e: raise HTTPException(422,'No se pudo extraer el manuscrito: '+str(e))
    if not original.strip(): raise HTTPException(422,'Sin texto extraíble. PDF escaneado requiere OCR externo.')
    with lock:
        p=get(pid)
        if p['original']: raise HTTPException(409,'Crea otro proyecto para conservar el manuscrito existente')
        p['original']=original
        source_name = str(uuid.uuid4()) + Path(file.filename or '').suffix.lower()
        (DATA/source_name).write_bytes(data)
        p['source_file']=source_name
        p['source_filename']=file.filename
        for ch in analyze(original):
            ch['id']=str(uuid.uuid4())
            for s in ch['segments']: s.update(id=str(uuid.uuid4()),voice='es',speed=160,color='#9C68FF' if s.get('kind') == 'thought_or_quote' else ('#F018A8' if s['speaker'] != 'Narrador' else '#00D9CE'),versions=[],audio=None)
            p['chapters'].append(ch)
        ensure_cast(p); save(p)
    return p
@app.patch('/api/projects/{pid}/segments/{sid}')
def edit(pid:str,sid:str,body:Edit):
    with lock:
        p=get(pid); s=segment(p,sid)
        pending=needs_content_review(s) and not body.reviewed
        changed=any(s.get(k)!=getattr(body,k) for k in ('speaker','voice','speed'))
        s.update(body.model_dump(exclude={'reviewed'}),speaker_confirmed=True,content_review=pending,review=pending,revision=s.get('revision',0)+1)
        if changed: s.update(audio=None,duration=0)
        if not pending: s['review_reason']=''
        ensure_cast(p)
        s['character_id']=next(c['id'] for c in p['characters'] if key(c['name'])==key(s['speaker']))
        save(p)
    return p
@app.get('/api/voices')
def voices():
    return {'provider':'espeak-ng','available':bool(shutil.which('espeak-ng') or shutil.which('espeak')), 'capabilities':{'emotion':False,'speed':True,'cloning':False},'voices':['es','es+f2','es+m3','en','en+f2','en+m3']}
@app.post('/api/projects/{pid}/segments/{sid}/generate')
def generate(pid:str,sid:str,compact:bool=False):
    executable=shutil.which('espeak-ng') or shutil.which('espeak')
    if not executable: raise HTTPException(503,'Instala eSpeak NG y agrégalo a PATH. No hay motor TTS disponible.')
    with lock:
        p=get(pid); s=segment(p,sid)
        if s['review']: raise HTTPException(409,'Confirma el hablante y la revisión del contenido antes de generar')
        name=str(uuid.uuid4())+'.wav'; path=DATA/name
        try: subprocess.run([executable,'-v',s['voice'],'-s',str(s['speed']),'-w',str(path),'--stdin'], input=s['text'],text=True,check=True,capture_output=True,timeout=60)
        except (subprocess.SubprocessError,OSError): raise HTTPException(502,'Error en motor TTS; no se modificó el fragmento')
        with wave.open(str(path)) as w: duration=w.getnframes()/w.getframerate()
        s['versions'].append({'file':name,'voice':s['voice'],'speed':s['speed'],'text':s['text']}); s['audio']=name; s['duration']=duration; s['revision']=s.get('revision',0)+1; save(p)
    return {'segment':s} if compact else p
@app.get('/api/audio/{name}')
def audio(name:str):
    if Path(name).name != name or Path(name).suffix not in ('.wav','.mp3'): raise HTTPException(400,'Nombre inválido')
    path=DATA/name
    if not path.is_file(): raise HTTPException(404,'Audio no encontrado')
    return FileResponse(path)
@app.get('/api/audio/{name}/waveform')
def waveform(name:str):
    if Path(name).name != name or not name.endswith('.wav'): raise HTTPException(400,'Nombre inválido')
    if not (DATA/name).is_file(): raise HTTPException(404)
    with wave.open(str(DATA/name)) as w:
        if w.getsampwidth()!=2: raise HTTPException(422,'PCM16 requerido')
        samples=struct.unpack('<'+'h'*w.getnframes()*w.getnchannels(),w.readframes(w.getnframes()))
    step=max(1,len(samples)//180)
    return [max(abs(x) for x in samples[i:i+step])/32768 for i in range(0,len(samples),step)]
@app.get('/api/projects/{pid}/chapters/{cid}/export')
def export(pid:str,cid:str,format:str='wav'):
    if format not in ('wav','mp3'): raise HTTPException(422,'Formato inválido')
    p=get(pid); ch=next((x for x in p['chapters'] if x['id']==cid),None)
    if not ch: raise HTTPException(404)
    if not ch['segments'] or any(not s['audio'] for s in ch['segments']): raise HTTPException(409,'Genera todos los fragmentos del capítulo')
    if not shutil.which('ffmpeg'): raise HTTPException(503,'FFmpeg no disponible')
    token=str(uuid.uuid4()); listing=DATA/(token+'.txt'); output=DATA/(token+'.'+format)
    listing.write_text('\n'.join("file '"+s['audio']+"'" for s in ch['segments']),encoding='utf-8')
    try: subprocess.run(['ffmpeg','-v','error','-f','concat','-safe','1','-i',str(listing),'-af','loudnorm=I=-19:TP=-2:LRA=7','-y',str(output)],check=True,capture_output=True,timeout=300)
    except subprocess.SubprocessError: raise HTTPException(502,'Falló exportación')
    finally: listing.unlink(missing_ok=True)
    return FileResponse(output,filename='capitulo.'+format)

@app.post('/api/projects/{pid}/characters',status_code=201)
def create_character(pid:str,body:Character):
    with lock:
        p=get(pid)
        if any(key(c['name'])==key(body.name) for c in p['characters']): raise HTTPException(409,'Ya existe ese personaje en el elenco')
        p['characters'].append({'id':str(uuid.uuid4()),**body.model_dump()});save(p)
    return p

@app.patch('/api/projects/{pid}/characters/{character_id}')
def edit_character(pid:str,character_id:str,body:Character):
    with lock:
        p=get(pid); character=next((c for c in p['characters'] if c['id']==character_id),None)
        if character is None: raise HTTPException(404,'Personaje no encontrado')
        # Name edits are excluded here to preserve existing attributions.
        if body.name!=character['name']: raise HTTPException(422,'El nombre se conserva; crea otro personaje para una identidad distinta')
        character.update(body.model_dump());save(p)
    return p

@app.post('/api/projects/{pid}/segments/{sid}/assign')
def assign_character(pid:str,sid:str,body:Assignment):
    with lock:
        p=get(pid); s=segment(p,sid)
        character=next((c for c in p['characters'] if c['id']==body.character_id),None)
        if character is None: raise HTTPException(404,'Personaje no encontrado en este proyecto')
        token=assign(p,s,character);save(p)
    return {'project':p,'undo_token':token,'segment_id':sid}

@app.post('/api/projects/{pid}/segments/{sid}/undo-assignment')
def undo_character(pid:str,sid:str,body:UndoAssignment):
    with lock:
        p=get(pid);s=segment(p,sid)
        try: undo(p,s,body.token)
        except ValueError as e: raise HTTPException(409,str(e))
        save(p)
    return p

class BatchAssignment(BaseModel):
    character_id: str
    segment_ids: list[str] = Field(min_length=1,max_length=5000)
class VoiceChoice(BaseModel):
    id: str
    voice: str = Field(pattern=r'^(es|en)(\+m[1-7]|\+f[1-5])?$')
    speed: int = Field(ge=80,le=300)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
class CastChoices(BaseModel):
    characters: list[VoiceChoice] = Field(min_length=1,max_length=5000)

@app.post('/api/projects/{pid}/segments/assign-batch')
def assign_batch(pid:str,body:BatchAssignment):
    from .casting import assign_many
    with lock:
        p=get(pid);character=next((c for c in p['characters'] if c['id']==body.character_id),None)
        if not character: raise HTTPException(404,'Personaje no encontrado')
        selected=[segment(p,sid) for sid in dict.fromkeys(body.segment_ids)]
        token=assign_many(p,selected,character);save(p)
    return {'project':p,'undo_token':token,'count':len(selected)}

@app.post('/api/projects/{pid}/segments/undo-batch')
def undo_batch(pid:str,body:UndoAssignment):
    from .casting import undo_many
    with lock:
        p=get(pid)
        try:undo_many(p,body.token)
        except ValueError as e: raise HTTPException(409,str(e))
        save(p)
    return p

@app.post('/api/projects/{pid}/casting/apply')
def apply_casting(pid:str,body:CastChoices):
    from datetime import datetime, timezone
    with lock:
        p=get(pid); ids=[c.id for c in body.characters]
        if len(set(ids))!=len(ids) or set(ids)!={c['id'] for c in p['characters']}:
            raise HTTPException(409,'El elenco cambió o faltan perfiles. Vuelve a abrir la configuración.')
        choices={c.id:c.model_dump(exclude={'id'}) for c in body.characters}
        for character in p['characters']:character.update(choices[character['id']])
        by_name={key(c['name']):c for c in p['characters']};updated=0;pending=0
        for ch in p['chapters']:
            for s in ch['segments']:
                character=by_name.get(key(s['speaker']))
                if character:
                    # Store the correspondence; original text remains unchanged.
                    token=assign(p,s,character);p['assignment_undo'].pop(token);updated+=1
                if s.get('review'):pending+=1
        p['casting_configured_at']=datetime.now(timezone.utc).isoformat();save(p)
    return {'project':p,'updated':updated,'pending_review':pending}

class VoicePreview(BaseModel):
    voice: str = Field(pattern=r'^(es|en)(\+m[1-7]|\+f[1-5])?$')
    speed: int = Field(default=160,ge=80,le=300)

@app.post('/api/voices/preview')
def preview_voice(body:VoicePreview):
    executable=shutil.which('espeak-ng') or shutil.which('espeak')
    if not executable: raise HTTPException(503,'Motor TTS no disponible')
    name=str(uuid.uuid4())+'.wav'
    sample='Hola. Esta es una muestra de mi voz para narrar tu historia.' if body.voice.startswith('es') else 'Hello. This is a sample of my voice to tell your story.'
    try: subprocess.run([executable,'-v',body.voice,'-s',str(body.speed),'-w',str(DATA/name),'--stdin'],input=sample,text=True,check=True,capture_output=True,timeout=30)
    except (subprocess.SubprocessError,OSError):raise HTTPException(502,'No se pudo generar la muestra')
    return {'file':name}
