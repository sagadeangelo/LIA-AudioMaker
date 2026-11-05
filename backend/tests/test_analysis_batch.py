import copy,hashlib
from fastapi.testclient import TestClient
from app import main as m
from test_manuscript_analysis import run
c=TestClient(m.app)


def fixture():
 p=c.post('/api/projects',json={'title':'Revisión en lote'}).json()
 text='CAPÍTULO I\nLA PRUEBA\nLindsay dijo que Gibrán estaba en la playa.\nSe escuchaban gaviotas frente al mar.\nHoras después, sonó el teléfono.\nMás tarde, llovía en el bosque.'
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('b.txt',text.encode())}).json()


def submit(p,jid,r,category,ids,decision='confirm',**more):
 return c.post(f'/api/projects/{p["id"]}/analysis/review-batch',json={'job_id':jid,'document_token':r['document_token'],'category':category,'item_ids':ids,'decision':decision,'confirmed':True,**more})


def test_bulk_sound_approval_and_replay_preserve_wav_and_profiles(fake_tts):
 p=fixture();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id'];c.post(f'/api/projects/{pid}/segments/{sid}/generate')
 before=copy.deepcopy(m.get(pid));audio=before['chapters'][0]['segments'][0]['audio'];sha=hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()
 jid,r=run(p);ids=[str(i) for i in range(len(r['sound_suggestions']))];assert len(ids)>=3
 result=submit(p,jid,r,'sound',ids);assert result.status_code==200,result.text
 assert result.json()['applied']==len(ids) and not result.json()['stale']
 after=m.get(pid);assert after['chapters']==before['chapters'] and after['characters']==before['characters']
 assert hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()==sha
 replay=submit(p,jid,r,'sound',ids+ids);assert replay.status_code==200 and replay.json()['applied']==0 and replay.json()['already_reviewed']==len(ids)
 assert len(m.get(pid)['manuscript_reviews'])==len(ids)


def test_invalid_batch_is_atomic_and_conflict_does_not_partially_reject():
 p=fixture();jid,r=run(p);before=copy.deepcopy(m.get(p['id']))
 result=submit(p,jid,r,'name',[r['names'][0]['id'],'missing']);assert result.status_code==404
 assert m.get(p['id'])==before
 ids=['0','1'];assert submit(p,jid,r,'sound',['1']).status_code==200
 before=copy.deepcopy(m.get(p['id']))
 assert submit(p,jid,r,'sound',ids,'reject').status_code==409
 assert m.get(p['id'])==before


def test_scene_batch_all_boundaries_apply_without_stale_between_items():
 p=fixture();before=copy.deepcopy(p['chapters']);jid,r=run(p);assert len(r['scene_candidates'])==2
 result=submit(p,jid,r,'scene',['0','1']);assert result.status_code==200,result.text
 assert result.json()['applied']==2 and not result.json()['stale']
 assert len({s['scene'] for s in m.get(p['id'])['chapters'][0]['segments']})==3
 for _ in range(2):assert c.post(f'/api/projects/{p["id"]}/analysis/undo-scene').status_code==200
 assert m.get(p['id'])['chapters']==before


def test_current_scene_review_is_only_metadata_and_stale_confirmation_guard():
 p=fixture();jid,r=run(p);before=copy.deepcopy(m.get(p['id']))
 assert submit(p,jid,r,'current_scene',['0'],confirmed=False).status_code==422
 assert m.get(p['id'])==before
 assert submit(p,jid,r,'current_scene',['0']).status_code==200
 assert m.get(p['id'])['chapters']==before['chapters']
 changed=m.get(p['id']);changed['chapters'][0]['segments'][0]['text']+=' Cambio';m.save(changed)
 assert submit(p,jid,r,'sound',['0']).status_code==409
 other=fixture();assert submit(other,jid,r,'sound',['0']).status_code==404
