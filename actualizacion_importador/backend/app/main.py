import os, json, uuid, subprocess, shutil, wave, struct, threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text as sql
from .narrative import extract, analyze

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
    return json.loads(row[0])
def segment(p, sid):
    for ch in p['chapters']:
        for s in ch['segments']:
            if s['id'] == sid: return s
    raise HTTPException(404,'Fragmento no encontrado')

app = FastAPI(title='LIA AudioMaker', version='0.1.1')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['*'], allow_headers=['*'])
class Project(BaseModel):
    title: str = Field(min_length=1,max_length=200)
class Edit(BaseModel):
    speaker: str = Field(min_length=1,max_length=100)
    voice: str = Field(pattern=r'^(es|en)(\+m[1-7]|\+f[1-5])?$')
    speed: int = Field(default=160,ge=80,le=300)
    color: str = Field(default='#00D9CE',pattern=r'^#[0-9a-fA-F]{6}$')

@app.get('/api/health')
def health():
    with engine.connect() as c: c.execute(sql('SELECT 1'))
    return {'status':'ok','database':'ok','tts': bool(shutil.which('espeak-ng') or shutil.which('espeak')), 'ffmpeg':bool(shutil.which('ffmpeg'))}
@app.get('/api/projects')
def projects():
    with engine.connect() as c: return [json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM projects'))]
@app.post('/api/projects',status_code=201)
def create(body: Project):
    p = {'id':str(uuid.uuid4()),'title':body.title,'original':'','chapters':[]}
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
        save(p)
    return p
@app.patch('/api/projects/{pid}/segments/{sid}')
def edit(pid:str,sid:str,body:Edit):
    with lock:
        p=get(pid); s=segment(p,sid); s.update(body.model_dump()); s['review']=False; s['audio']=None; save(p)
    return p
@app.get('/api/voices')
def voices():
    return {'provider':'espeak-ng','available':bool(shutil.which('espeak-ng') or shutil.which('espeak')), 'capabilities':{'emotion':False,'speed':True,'cloning':False},'voices':['es','es+f2','es+m3','en','en+f2','en+m3']}
@app.post('/api/projects/{pid}/segments/{sid}/generate')
def generate(pid:str,sid:str):
    executable=shutil.which('espeak-ng') or shutil.which('espeak')
    if not executable: raise HTTPException(503,'Instala eSpeak NG y agrégalo a PATH. No hay motor TTS disponible.')
    with lock:
        p=get(pid); s=segment(p,sid)
        if s['review']: raise HTTPException(409,'Revisa y asigna el hablante antes de generar')
        name=str(uuid.uuid4())+'.wav'; path=DATA/name
        try: subprocess.run([executable,'-v',s['voice'],'-s',str(s['speed']),'-w',str(path),'--stdin'], input=s['text'],text=True,check=True,capture_output=True,timeout=60)
        except (subprocess.SubprocessError,OSError): raise HTTPException(502,'Error en motor TTS; no se modificó el fragmento')
        with wave.open(str(path)) as w: duration=w.getnframes()/w.getframerate()
        s['versions'].append({'file':name,'voice':s['voice'],'speed':s['speed'],'text':s['text']}); s['audio']=name; s['duration']=duration; save(p)
    return p
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
