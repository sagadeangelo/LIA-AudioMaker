import copy, hashlib, threading
from fastapi.testclient import TestClient
from app import main as m
from test_voice_editor import book, base, first, rule, start, wait
c=TestClient(m.app)
def url(p):return f'/api/projects/{p["id"]}/finalization'
def view(p):
 r=c.get(url(p));assert r.status_code==200,r.text
 return r.json()
def apply(p,v,**kwargs):return c.post(url(p)+'/apply',json={'preview_token':v['preview_token'],'confirmed':True,**kwargs})
def generate_all(p):
 for ch in p['chapters']:
  for s in ch['segments']:assert c.post(f'/api/projects/{p["id"]}/segments/{s["id"]}/generate').status_code==200
 return m.get(p['id'])
def digest(name):return hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()
def test_whole_book_reuse_missing_stale_and_restore(fake_tts):
 p=generate_all(book());old=copy.deepcopy(p);hashes={s['audio']:digest(s['audio']) for ch in p['chapters'] for s in ch['segments']}
 assert view(p)['ready'];rule(p)
 j=start(p,{'scope':'segment','segment_id':first(p)['id']});wait(p,j['id'])
 p=m.get(p['id']);candidate=first(p)['versions'][-1];p['chapters'][1]['segments'][0]['audio']=None;m.save(p)
 v=view(p);assert v['totals']['proposed']==1 and v['totals']['outdated']==1 and v['totals']['missing']==1
 assert c.post(f'/api/projects/{p["id"]}/export-book/jobs?partial=false').status_code==409
 assert apply(p,v).status_code==409
 before=len(fake_tts);r=apply(p,v,selections={first(p)['id']:candidate['id']});assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['incorporated']==3 and not j['errors'];assert len(fake_tts)==before+2
 current=m.get(p['id']);assert first(current)['audio']==candidate['file'];assert view(p)['ready'] and view(p)['totals']['current']==3
 for name,h in hashes.items():assert digest(name)==h
 assert current['original']==old['original']
 assert all(s['text']==o['text'] for ch,och in zip(current['chapters'],old['chapters']) for s,o in zip(ch['segments'],och['segments']))
 assert apply(p,view(p)).status_code==409
 restored=c.post(base(p)+f'/incorporation/{j["id"]}/restore');assert restored.status_code==200,restored.text
 assert first(restored.json())['audio']==first(old)['audio'];assert restored.json()['chapters'][1]['segments'][0]['audio'] is None
 assert (m.DATA/candidate['file']).exists()
def test_manual_alternative_selection_is_explicit_and_persists(fake_tts):
 p=generate_all(book());sid=first(p)['id'];j=start(p,{'scope':'segment','segment_id':sid,'override_text':'Ditox vuelve con una pausa.'});wait(p,j['id'])
 v=view(p);row=next(x for x in v['rows'] if x['segment_id']==sid);assert row['recommended_version_id'] is None;assert apply(p,v).status_code==409
 calls=len(fake_tts);r=apply(p,v,selections={sid:row['proposals'][0]['id']});assert r.status_code==202
 wait(p,r.json()['id']);assert len(fake_tts)==calls and view(p)['ready'];rule(p);assert not view(p)['ready']
def test_review_excluded_and_stale_confirmation(fake_tts):
 p=book();p['chapters'][0]['segments'][0]['review']=True;p['chapters'][0]['segments'][1]['excluded']=True;m.save(p)
 v=view(p);assert v['totals']['review']==1 and v['totals']['excluded']==1;rule(p);assert apply(p,v).status_code==409
 r=apply(p,view(p));assert r.status_code==202;wait(p,r.json()['id']);v=view(p)
 assert not v['ready'] and v['totals']['review']==1 and v['totals']['current']==1 and len(fake_tts)==1
 assert c.get(f'/api/projects/{p["id"]}/export-book?partial=false').status_code==409
def test_concurrent_change_keeps_old_audio_and_retries(fake_tts,monkeypatch):
 p=generate_all(book());rule(p);old=m.get(p['id']);sid=first(old)['id'];old_audio=first(old)['audio'];entered=threading.Event();release=threading.Event()
 from app.tts_provider import generate
 def slow(*args,**kwargs):
  entered.set();assert release.wait(5);return generate(*args,**kwargs)
 monkeypatch.setattr('app.tts_provider.generate',slow);r=apply(p,view(p));assert r.status_code==202;assert entered.wait(3)
 try:
  assert apply(p,view(p)).status_code==409
  current=m.get(p['id']);first(current)['revision']+=1;m.save(current)
 finally:release.set()
 j=wait(p,r.json()['id']);assert j['errors'] and j['status']=='completed_with_errors';assert first(m.get(p['id']))['audio']==old_audio and not view(p)['ready']
 monkeypatch.setattr('app.tts_provider.generate',generate);v=view(p);row=next(x for x in v['rows'] if x['segment_id']==sid);assert row['status']=='outdated'
 r=apply(p,v);assert r.status_code==202;wait(p,r.json()['id']);assert view(p)['ready']
def test_legacy_with_affected_name_is_not_mistaken_for_current(fake_tts):
 p=generate_all(book());p=m.get(p['id']);first(p)['versions']=[];m.save(p);assert view(p)['totals']['historical']==1 and view(p)['ready']
 c.get(base(p)+f'/segments/{first(p)["id"]}/versions');rule(p);v=view(p);assert v['totals']['outdated']==3 and not v['ready']

def test_failure_cancel_and_voice_exception_are_visible(fake_tts,monkeypatch):
 from app.tts_provider import generate
 p=generate_all(book());rule(p)
 current=m.get(p['id']);current['pronunciation_voice_overrides']=[{'id':'test','original':'Ditóx','pronunciation':'Di tocs','voice':'em_santa'}];m.save(current)
 def fail(*args,**kwargs):raise RuntimeError('test provider unavailable')
 monkeypatch.setattr('app.tts_provider.generate',fail)
 r=apply(p,view(p));assert r.status_code==202
 j=wait(p,r.json()['id']);assert len(j['errors'])==3 and j['processed']==3 and not view(p)['ready']
 monkeypatch.setattr('app.tts_provider.generate',generate)
 r=apply(p,view(p));wait(p,r.json()['id']);assert view(p)['ready']
 assert all('Di tocs' in request[0] for request in fake_tts[-3:])

def test_cancel_keeps_completed_subset_and_retry_skips_it(fake_tts,monkeypatch):
 from app.tts_provider import generate
 p=generate_all(book());rule(p);entered=threading.Event();release=threading.Event()
 def slow(*args,**kwargs):
  entered.set();assert release.wait(5);return generate(*args,**kwargs)
 monkeypatch.setattr('app.tts_provider.generate',slow)
 r=apply(p,view(p));assert r.status_code==202;assert entered.wait(3)
 try:assert c.post(base(p)+f'/jobs/{r.json()["id"]}/cancel').status_code==200
 finally:release.set()
 j=wait(p,r.json()['id']);assert j['status']=='cancelled' and j['incorporated']==1
 v=view(p);assert v['totals']['current']==1 and v['totals']['outdated']==2
 monkeypatch.setattr('app.tts_provider.generate',generate);before=len(fake_tts)
 r=apply(p,v);wait(p,r.json()['id']);assert view(p)['ready'] and len(fake_tts)==before+2
