import os,subprocess,sys,shutil
from fastapi.testclient import TestClient
from app.main import app,DATA
c=TestClient(app)

def book(title='Proyecto eliminable'):
 p=c.post('/api/projects',json={'title':title}).json()
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.txt',b'Capitulo 1\nANA: Hola.')}).json()

def test_delete_hides_project_and_restore_preserves_manuscript_cast_audio():
 p=book();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id']
 if shutil.which('espeak-ng') or shutil.which('espeak'):
  p=c.post(f'/api/projects/{pid}/segments/{sid}/generate').json()
 before=c.get(f'/api/projects/{pid}').json();source=(DATA/before['source_file']).read_bytes()
 assert c.delete(f'/api/projects/{pid}').status_code==200
 assert pid not in {x['id'] for x in c.get('/api/projects').json()}
 assert c.get(f'/api/projects/{pid}').status_code==404
 trash=next(x for x in c.get('/api/projects?trash=true').json() if x['id']==pid)
 assert set(trash)=={'id','title','deleted_at'}
 assert (DATA/before['source_file']).read_bytes()==source
 audio=before['chapters'][0]['segments'][0]['audio']
 if audio:assert (DATA/audio).is_file()
 restored=c.post(f'/api/projects/{pid}/restore');assert restored.status_code==200
 assert restored.json()==before
 assert pid not in {x['id'] for x in c.get('/api/projects?trash=true').json()}
 assert pid in {x['id'] for x in c.get('/api/projects').json()}

def test_delete_idempotent_and_does_not_touch_other_project():
 a=book('Primero');b=book('Segundo');before=c.get(f'/api/projects/{b["id"]}').json()
 c.delete(f'/api/projects/{a["id"]}').raise_for_status()
 deleted=next(x for x in c.get('/api/projects?trash=true').json() if x['id']==a['id'])['deleted_at']
 c.delete(f'/api/projects/{a["id"]}').raise_for_status()
 assert deleted==next(x for x in c.get('/api/projects?trash=true').json() if x['id']==a['id'])['deleted_at']
 assert c.get(f'/api/projects/{b["id"]}').json()==before
 assert c.delete('/api/projects/not-a-project').status_code==404
 assert c.post('/api/projects/not-a-project/restore').status_code==404

def test_trash_persists_between_processes_and_blocks_edits():
 p=book();pid=p['id'];s=p['chapters'][0]['segments'][0]
 c.delete(f'/api/projects/{pid}').raise_for_status()
 assert c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={k:s[k] for k in ('speaker','voice','speed','color')}).status_code==404
 subprocess.run([sys.executable,'-c',f"from app.main import get; assert get('{pid}',include_deleted=True)['deleted_at']"],check=True)
 assert c.post(f'/api/projects/{pid}/restore').status_code==200
