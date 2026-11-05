import copy, subprocess, sys
from fastapi.testclient import TestClient
from app.main import app, get, save
c=TestClient(app)

def book():
 p=c.post('/api/projects',json={'title':'Casting'}).json()
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.txt','Capítulo 1\nANA: Hola.\n«Mi pensamiento».\n—No sé.\nCapítulo 2\nMARCOS: Adiós.'.encode())}).json()

def test_legacy_cast_all_chapters_and_new_character_persist():
 p=book();p.pop('characters',None);save(p)
 r=c.get(f'/api/projects/{p["id"]}').json()
 assert {x['name'] for x in r['characters']}=={'Narrador','Ana','Marcos'}
 ids=[x['id'] for x in r['characters']]
 assert ids==[x['id'] for x in c.get(f'/api/projects/{p["id"]}').json()['characters']]
 r=c.post(f'/api/projects/{p["id"]}/characters',json={'name':'Rachel','voice':'ef_dora','color':'#9C68FF','speed':1.15})
 assert r.status_code==201
 assert c.get(f'/api/projects/{p["id"]}').json()['characters'][-1]['name']=='Rachel'
 assert c.post(f'/api/projects/{p["id"]}/characters',json={'name':'RÁCHEL'}).status_code==409
 assert c.post(f'/api/projects/{p["id"]}/characters',json={'name':'  '}).status_code==422
 subprocess.run([sys.executable,'-c',f"from app.main import get; assert any(c['name']=='Rachel' for c in get('{p['id']}')['characters'])"],check=True)

def test_assign_single_segment_and_undo_restores_audio_and_review():
 p=book();pid=p['id'];s=p['chapters'][0]['segments'][0]
 s.update(audio='old.wav',duration=4,versions=[{'file':'old.wav'}]);save(p)
 before=copy.deepcopy(p['chapters']);character=next(x for x in p['characters'] if x['name']=='Marcos')
 r=c.post(f'/api/projects/{pid}/segments/{s["id"]}/assign',json={'character_id':character['id']});assert r.status_code==200
 result=r.json();after=result['project']['chapters'][0]['segments'][0]
 assert after['speaker']=='Marcos' and after['audio'] is None
 assert result['project']['chapters'][1]==before[1]
 assert after['versions']==s['versions']
 token=result['undo_token']
 r=c.post(f'/api/projects/{pid}/segments/{s["id"]}/undo-assignment',json={'token':token});assert r.status_code==200
 restored=r.json()['chapters'][0]['segments'][0]
 assert restored['audio']=='old.wav' and restored['speaker']=='Ana' and restored['duration']==4
 assert c.post(f'/api/projects/{pid}/segments/{s["id"]}/undo-assignment',json={'token':token}).status_code==409

def test_content_review_is_separate_from_assignment():
 p=book();pid=p['id'];s=p['chapters'][0]['segments'][1];char=p['characters'][1]
 r=c.post(f'/api/projects/{pid}/segments/{s["id"]}/assign',json={'character_id':char['id']}).json()
 s=r['project']['chapters'][0]['segments'][1]
 assert s['speaker_confirmed'] and s['review'] and s['content_review']
 body={k:s[k] for k in ('speaker','voice','speed','color')}
 r=c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json=body).json()
 assert r['chapters'][0]['segments'][1]['review']
 r=c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={**body,'reviewed':True}).json()
 assert not r['chapters'][0]['segments'][1]['review']
 # An unknown spoken dialogue only needs speaker attribution.
 s=p['chapters'][0]['segments'][2]
 r=c.post(f'/api/projects/{pid}/segments/{s["id"]}/assign',json={'character_id':char['id']}).json()
 assert not r['project']['chapters'][0]['segments'][2]['review']

def test_profile_configuration_future_assignments_and_conflict():
 p=book();pid=p['id'];char=p['characters'][1];s=p['chapters'][0]['segments'][0]
 body={k:char[k] for k in ('name','voice','speed','color')};body.update(voice='ef_dora',speed=1.25,color='#498BFF')
 r=c.patch(f'/api/projects/{pid}/characters/{char["id"]}',json=body);assert r.status_code==200
 assert r.json()['chapters']==p['chapters']
 result=c.post(f'/api/projects/{pid}/segments/{s["id"]}/assign',json={'character_id':char['id']}).json()
 s=result['project']['chapters'][0]['segments'][0]
 assert (s['voice'],s['speed'],s['color'])==('ef_dora',1.25,'#498BFF')
 c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={k:s[k] for k in ('speaker','voice','speed','color')})
 assert c.post(f'/api/projects/{pid}/segments/{s["id"]}/undo-assignment',json={'token':result['undo_token']}).status_code==409
 assert c.post(f'/api/projects/{pid}/segments/{s["id"]}/assign',json={'character_id':'foreign'}).status_code==404

def test_color_only_does_not_discard_audio():
 p=book();pid=p['id'];s=p['chapters'][0]['segments'][0];s.update(audio='old.wav',duration=3);save(p)
 r=c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={'speaker':s['speaker'],'voice':s['voice'],'speed':s['speed'],'color':'#498BFF'})
 assert r.json()['chapters'][0]['segments'][0]['audio']=='old.wav'
