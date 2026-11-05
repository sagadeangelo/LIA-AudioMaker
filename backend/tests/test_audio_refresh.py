import hashlib
from fastapi.testclient import TestClient
from app import main as m
from test_voice_editor import book,base,first,rule,start,wait
from test_finalization import generate_all,url
c=TestClient(m.app)
def audit(p):return c.get(url(p)+'?verify_pronunciations=true').json()
def apply_audit(p,v):return c.post(url(p)+'/apply',json={'preview_token':v['preview_token'],'confirmed':True,'verify_pronunciations':True,'selections':{r['segment_id']:r['recommended_version_id'] for r in v['rows'] if r['recommended_version_id']}})
def accept_old(p):
 p=m.get(p['id'])
 from app.finalization import rules_key
 from app.voice_editor import signature
 for ch in p['chapters']:
  for s in ch['segments']:s['manual_audio_acceptance']={'audio':s['audio'],'request':signature([s['text'],s['voice'],s['speed'],rules_key(p)])}
 m.save(p)
 return p

def test_refresh_uncovers_old_audio_after_manual_review(fake_tts):
 p=generate_all(book());old=first(p)['audio'];h=hashlib.sha256((m.DATA/old).read_bytes()).hexdigest();rule(p);p=accept_old(p)
 assert c.get(url(p)).json()['ready']
 v=audit(p);assert v['totals']['outdated']==3 and not v['ready']
 assert c.get(url(p)).json()['ready'] # inspecting refresh plan never mutates acceptance/audio
 r=apply_audit(p,v);assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['incorporated']==3 and not j['errors']
 current=m.get(p['id']);assert first(current)['audio']!=old and audit(p)['ready']
 assert hashlib.sha256((m.DATA/old).read_bytes()).hexdigest()==h
 assert first(current)['text']=='Ditóx vuelve.'

def test_refresh_recovers_matching_proposal_after_revision_only_change(fake_tts):
 p=generate_all(book());rule(p)
 j=start(p,{'scope':'project'});wait(p,j['id'])
 p=accept_old(p)
 for ch in p['chapters']:
  for s in ch['segments']:s['revision']+=2
 m.save(p);assert c.get(url(p)).json()['ready']
 v=audit(p);assert v['totals']['proposed']==3
 count=len(fake_tts);r=apply_audit(p,v);assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['incorporated']==3 and len(fake_tts)==count and audit(p)['ready']

def test_refresh_reuses_prior_approved_wav_and_rejects_wrong_source(fake_tts):
 p=generate_all(book());rule(p);j=start(p,{'scope':'project'});wait(p,j['id'])
 p=m.get(p['id'])
 for ch in p['chapters']:
  for s in ch['segments']:s['versions'][-1]['status']='approved'
 # Wrong source cannot be reused even if someone recorded identical output text.
 first(p)['versions'][-1]['source_snapshot']['text']='Otro manuscrito.'
 m.save(p);p=accept_old(p)
 v=audit(p);assert v['totals']['proposed']==2 and v['totals']['outdated']==1
 count=len(fake_tts);r=apply_audit(p,v);assert r.status_code==202,r.text
 wait(p,r.json()['id']);assert len(fake_tts)==count+1 and audit(p)['ready']

def test_refresh_tokens_are_bound_to_mode_and_dictionary(fake_tts):
 p=generate_all(book());rule(p);p=accept_old(p);v=audit(p)
 assert c.post(url(p)+'/apply',json={'preview_token':v['preview_token'],'confirmed':True}).status_code==409
 rule(p,original='vuelve',pronunciation='regresa')
 assert apply_audit(p,v).status_code==409
