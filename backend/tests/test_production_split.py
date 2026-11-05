import copy,hashlib
from fastapi.testclient import TestClient
from app import main as m
from app.production_exchange import build_context
from app.production_split import proposal
from app.project_cleanup import project_files
from test_sound_mixer import setup
c=TestClient(m.app)
def fixture():
 p=setup()
 with m.lock:
  p=m.get(p['id']);seg=p['chapters'][0]['segments'][0];seg.update(text='«¡Qué… novedad!!» Ángelo tenía una mueca muy irónica en la cara. ',speaker='Ángelo',voice='em_alex',review=False)
  m.ensure_cast(p);char=next(x for x in p['characters'] if x['name']=='Ángelo');seg['character_id']=char['id'];m.save(p)
 p=m.get(p['id']);seg=p['chapters'][0]['segments'][0];ctx=build_context(p,seg['id']);plan={'format':'lia.production-plan','version':1,'project_id':p['id'],'document_token':ctx['document_token'],'resources_token':ctx['resources_token'],'scope_scene_ids':[seg['id']],'scenes':[{'scene_id':seg['id'],'decision':'sound_design','performances':[{'segment_id':seg['id'],'quote':seg['text'],'character_id':char['id'],'voice_id':'em_alex'}]}]}
 base=f'/api/projects/{p["id"]}/production-exchange';pr=c.post(base+'/preview',json={'plan':plan}).json();rid=c.post(base+'/plans',json={'plan':plan,'confirmed':True,'preview_token':pr['preview_token']}).json()['id'];base+='/plans/'+rid+'/splits'
 data=c.get(base).json();row=data['candidates'][0];narrator=next(x for x in p['characters'] if x['name']=='Narrador')
 body={'segment_id':seg['id'],'narration_text':row['suggested_narration'],'dialogue_character_id':char['id'],'narrator_character_id':narrator['id']}
 return m.get(p['id']),rid,base,body

def test_exact_preview_apply_preserves_audio_and_other_segments_then_undo():
 p,rid,base,body=fixture();before=copy.deepcopy(p);seg=p['chapters'][0]['segments'][0];audio=seg['audio'];sha=hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()
 pr=c.post(base+'/preview',json=body);assert pr.status_code==200,pr.text
 pr=pr.json();assert ''.join(x['text'] for x in pr['parts'])==seg['text'] and pr['parts'][1]['speaker']=='Narrador'
 assert m.get(p['id'])==before
 result=c.post(base+'/apply',json={**body,'preview_token':pr['preview_token'],'confirmed':True});assert result.status_code==200,result.text
 after=m.get(p['id']);parts=after['chapters'][0]['segments'][:2];assert ''.join(s['text'] for s in parts)==seg['text'];assert all(s['audio'] is None and s['versions']==[] for s in parts)
 assert after['chapters'][0]['segments'][2:]==before['chapters'][0]['segments'][1:];assert after['original']==before['original'];assert after['sound_effects']==before['sound_effects']
 assert audio in project_files(after) and hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()==sha
 assert c.post(base+'/apply',json={**body,'preview_token':pr['preview_token'],'confirmed':True}).status_code==409
 h=c.get(base).json()['history'][0];assert h['original_audio_url'] and len(h['parts'])==2
 undo=c.post(base+'/'+result.json()['split_id']+'/undo',json={'confirmed':True});assert undo.status_code==200,undo.text
 assert m.get(p['id'])['chapters']==before['chapters']

def test_generate_only_parts_and_refuse_undo_after_generation(fake_tts):
 p,rid,base,body=fixture();pr=c.post(base+'/preview',json=body).json();r=c.post(base+'/apply',json={**body,'preview_token':pr['preview_token'],'confirmed':True}).json()
 for part in r['parts']:
  res=c.post(f'/api/projects/{p["id"]}/segments/{part["id"]}/generate?compact=true');assert res.status_code==200,res.text
 assert len(fake_tts)==2
 assert c.post(base+'/'+r['split_id']+'/undo',json={'confirmed':True}).status_code==409
 assert m.get(p['id'])['chapters'][0]['segments'][2:]==p['chapters'][0]['segments'][1:]

def test_confirmation_tokens_text_characters_cues_and_project_isolation():
 p,rid,base,body=fixture();pr=c.post(base+'/preview',json=body).json();before=copy.deepcopy(m.get(p['id']))
 assert c.post(base+'/apply',json={**body,'preview_token':pr['preview_token']}).status_code==422
 assert c.post(base+'/apply',json={**body,'preview_token':'stale','confirmed':True}).status_code==409
 assert c.post(base+'/preview',json={**body,'narration_text':'Rewritten text'}).status_code==422
 assert c.post(base+'/preview',json={**body,'narrator_character_id':'other-project'}).status_code==422
 assert m.get(p['id'])==before
 other=setup();assert c.get(base.replace(p['id'],other['id'])).status_code==404
 with m.lock:
  q=m.get(p['id']);q['sound_cues']=[{'segment_id':body['segment_id'],'sound_id':'sound1'}];m.save(q)
 assert c.post(base+'/apply',json={**body,'preview_token':pr['preview_token'],'confirmed':True}).status_code==409

def test_suggestion_preserves_stray_quote_and_no_metaphorical_split():
 text='«¿Y yo era el malo de la película?»  “Ángelo movió la cabeza en símbolo de descontento.'
 tail=proposal(text,'Ángelo');assert tail=='  “Ángelo movió la cabeza en símbolo de descontento.'
 assert proposal('Me levanté y salí de casa.','Ángelo')==''
