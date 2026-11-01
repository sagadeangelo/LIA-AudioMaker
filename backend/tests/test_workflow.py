from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)

def book(text='Capítulo 1\nANA: Hola.\n«No lo diré».\n—¿Quién?\nCapítulo 2\nANA: Adiós.\nMARCOS: Hasta luego.'):
 p=c.post('/api/projects',json={'title':'Workflow'}).json()
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.txt',text.encode())}).json()

def test_voice_setup_whole_book_preserves_unknown_and_source():
 p=book();pid=p['id'];before=p['chapters'];char=next(x for x in p['characters'] if x['name']=='Ana')
 choices=[{k:x[k] for k in ('id','voice','speed','color')} for x in p['characters']]
 for x in choices:
  if x['id']==char['id']: x.update(voice='es+f2',speed=185,color='#498BFF')
 r=c.post(f'/api/projects/{pid}/casting/apply',json={'characters':choices});assert r.status_code==200
 result=r.json();after=result['project'];assert result['updated']==3;assert result['pending_review']==2
 for ch in after['chapters']:
  for s in ch['segments']:
   old=next(x for b in before for x in b['segments'] if x['id']==s['id'])
   assert s['text']==old['text'] and s['source_text']==old['source_text']
   if s['speaker']=='Ana':assert (s['voice'],s['speed'],s['color'])==('es+f2',185,'#498BFF')
   if s['speaker']=='Sin atribuir':assert s==old
 assert after['casting_configured_at']
 assert c.get(f'/api/projects/{pid}').json()['characters']==after['characters']
 # Reject stale/incomplete catalog atomically.
 r=c.post(f'/api/projects/{pid}/casting/apply',json={'characters':choices[:-1]});assert r.status_code==409
 assert c.get(f'/api/projects/{pid}').json()['chapters']==after['chapters']

def test_batch_atomic_validation_and_deduplication():
 p=book();pid=p['id'];ids=[s['id'] for s in p['chapters'][0]['segments']];char=p['characters'][1]
 r=c.post(f'/api/projects/{pid}/segments/assign-batch',json={'character_id':char['id'],'segment_ids':[ids[0],'missing']});assert r.status_code==404
 assert c.get(f'/api/projects/{pid}').json()['chapters']==p['chapters']
 r=c.post(f'/api/projects/{pid}/segments/assign-batch',json={'character_id':char['id'],'segment_ids':[ids[1],ids[2],ids[2]]});assert r.status_code==200
 result=r.json();assert result['count']==2
 assert result['project']['chapters'][0]['segments'][1]['review']
 assert not result['project']['chapters'][0]['segments'][2]['review']
 assert result['project']['chapters'][1]==p['chapters'][1]
 r=c.post(f'/api/projects/{pid}/segments/undo-batch',json={'token':result['undo_token']});assert r.status_code==200
 after=r.json()
 for old,new in zip(p['chapters'][0]['segments'],after['chapters'][0]['segments']):
  for k,v in old.items():assert new[k]==v
 assert c.post(f'/api/projects/{pid}/segments/assign-batch',json={'character_id':char['id'],'segment_ids':[]}).status_code==422

def test_large_batch_undo_and_conflicts_are_atomic():
 p=book('Capítulo 1\nANA: Hola.\n'+'\n'.join('—Frase '+str(i) for i in range(40)));pid=p['id'];ids=[s['id'] for s in p['chapters'][0]['segments']]
 body={'character_id':p['characters'][1]['id'],'segment_ids':ids}
 result=c.post(f'/api/projects/{pid}/segments/assign-batch',json=body).json();assert result['count']==41
 restored=c.post(f'/api/projects/{pid}/segments/undo-batch',json={'token':result['undo_token']});assert restored.status_code==200
 assert restored.json()['chapters'][0]['segments'][1]['speaker']=='Sin atribuir'
 result=c.post(f'/api/projects/{pid}/segments/assign-batch',json=body).json()
 s=result['project']['chapters'][0]['segments'][0]
 c.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={k:s[k] for k in ('speaker','voice','speed','color')})
 before=c.get(f'/api/projects/{pid}').json()
 assert c.post(f'/api/projects/{pid}/segments/undo-batch',json={'token':result['undo_token']}).status_code==409
 assert c.get(f'/api/projects/{pid}').json()==before

def test_real_voice_preview_and_compact_generation():
 import shutil
 if not (shutil.which('espeak-ng') or shutil.which('espeak')):
  assert c.post('/api/voices/preview',json={'voice':'es'}).status_code==503
  return
 r=c.post('/api/voices/preview',json={'voice':'es+f2','speed':170});assert r.status_code==200
 name=r.json()['file']
 assert c.get('/api/audio/'+name).status_code==200
 assert max(c.get('/api/audio/'+name+'/waveform').json())>0
 p=book();s=p['chapters'][0]['segments'][0]
 r=c.post(f'/api/projects/{p["id"]}/segments/{s["id"]}/generate?compact=true')
 assert r.status_code==200 and set(r.json())=={'segment'}
 assert r.json()['segment']['audio']
