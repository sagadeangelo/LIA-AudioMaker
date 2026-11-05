import copy, hashlib, json, subprocess, sys, threading, time
from fastapi.testclient import TestClient
from app import main as m
from app import voice_editor as ve
from sqlalchemy import text as sql
c=TestClient(m.app)

def book():
 p=c.post('/api/projects',json={'title':'Editor fixture'}).json()
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('test.txt','Capítulo 1\nANA: Ditóx vuelve.\nANA: Ditóx sale.\nCapítulo 2\nMARCOS: Ditóx espera.'.encode())}).json()
def base(p):return f'/api/projects/{p["id"]}/voice-editor'
def first(p):return p['chapters'][0]['segments'][0]
def rule(p,**changes):return c.post(base(p)+'/rules',json={'original':'Ditóx','pronunciation':'Ditoqs',**changes})
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def wait(p,jid):
 for _ in range(300):
  j=c.get(base(p)+'/jobs/'+jid).json()
  if j['status'] not in ('queued','running') and not ve.ACTIVE.locked():return j
  time.sleep(.01)
 raise AssertionError('Worker did not finish')
def start(p,body):
 r=c.post(base(p)+'/preview',json=body);assert r.status_code==200,r.text
 r=c.post(base(p)+'/jobs',json={**body,'preview_token':r.json()['preview_token'],'confirmed':True});assert r.status_code==202,r.text
 return r.json()

def test_dictionary_matching_and_character_provider_precedence():
 p=book();s=first(p);s['text']='DITÓX, Ditóxiano y Ditóx.';ana=next(x for x in p['characters'] if x['name']=='Ana')
 assert rule(p).status_code==201
 assert rule(p,pronunciation='Di toks',character_id=ana['id']).status_code==201
 p=m.get(p['id']);assert ve.rendered(p,s)=='Di toks, Ditóxiano y Di toks.'
 p['pronunciation_rules'][1]['provider']='azure';assert ve.rendered(p,s)=='Ditoqs, Ditóxiano y Ditoqs.'
 assert rule(p,character_id='foreign').status_code==422
 assert rule(p).status_code==409
 specific=p['pronunciation_rules'][1]
 update=c.put(base(p)+'/rules/'+specific['id'],json={k:v for k,v in {**specific,'pronunciation':'Di tocs'}.items() if k!='id'})
 assert update.status_code==200 and update.json()['pronunciation']=='Di tocs'
 assert rule(p,pronunciation='').status_code==422
 rid=p['pronunciation_rules'][0]['id']
 assert c.patch(base(p)+f'/rules/{rid}?active=false').json()['active'] is False
 assert c.delete(base(p)+f'/rules/{rid}').status_code==200
 assert c.delete(base(p)+f'/rules/{rid}').status_code==404
 assert rule(p,original=' ').status_code==422

def test_preview_confirmation_staleness_and_scope():
 p=book();rule(p);body={'scope':'project'}
 view=c.post(base(p)+'/preview',json=body).json();assert view['count']==3
 assert c.post(base(p)+'/jobs',json={**body,'preview_token':view['preview_token']}).status_code==409
 assert c.post(base(p)+'/preview',json={'scope':'chapter','chapter_id':p['chapters'][0]['id']}).json()['count']==2
 rule(p,original='vuelve',pronunciation='regresa')
 assert c.post(base(p)+'/jobs',json={**body,'preview_token':view['preview_token'],'confirmed':True}).status_code==409
 assert c.post(base(p)+'/preview',json={'scope':'chapter'}).status_code==422
 assert c.post(base(p)+'/preview',json={'scope':'segment','segment_id':'foreign'}).status_code==404
 assert c.post(base(p)+'/preview',json={'scope':'project','override_text':'hola'}).status_code==422
 assert c.post(base(p)+'/preview',json={'scope':'segment','segment_id':first(p)['id'],'override_text':' '}).status_code==422
 current=m.get(p['id']);first(current)['excluded']=True;current['chapters'][0]['segments'][1]['review']=True;m.save(current)
 assert c.post(base(p)+'/preview',json=body).json()['count']==1

def test_approve_export_restore_persist_preserves_all_originals(fake_tts):
 p=book();sid=first(p)['id'];original=copy.deepcopy(p)
 for ch in p['chapters']:
  for s in ch['segments']:assert c.post(f'/api/projects/{p["id"]}/segments/{s["id"]}/generate').status_code==200
 p=m.get(p['id']);old=first(p)['audio'];hashes={s['audio']:digest(m.DATA/s['audio']) for ch in p['chapters'] for s in ch['segments']}
 rule(p);j=start(p,{'scope':'segment','segment_id':sid});assert wait(p,j['id'])['status']=='completed'
 current=m.get(p['id']);v=first(current)['versions'][-1]
 assert first(current)['audio']==old and v['status']=='proposed' and v['text']=='Ditoqs vuelve.'
 assert current['original']==original['original'] and current['chapters'][1]==p['chapters'][1]
 url=f'/api/projects/{p["id"]}/chapters/{p["chapters"][0]["id"]}/export'
 before_export=c.get(url);assert before_export.status_code==200
 r=c.post(base(p)+f'/segments/{sid}/versions/{v["id"]}/approve');assert r.status_code==200,r.text
 assert first(r.json())['audio']==v['file']
 after_export=c.get(url);assert after_export.status_code==200 and before_export.content!=after_export.content
 assert c.get(url+'?format=mp3').status_code==200
 legacy=c.get(base(p)+f'/segments/{sid}/versions').json()['versions'][0]
 r=c.post(base(p)+f'/segments/{sid}/versions/{legacy["id"]}/restore');assert r.status_code==200,r.text
 assert first(r.json())['audio']==old
 for name,h in hashes.items():assert digest(m.DATA/name)==h
 subprocess.run([sys.executable,'-c',f"from app.main import get; p=get('{p['id']}'); assert p['chapters'][0]['segments'][0]['audio']=='{old}'; assert p['pronunciation_rules']"],check=True)

def test_reject_preserves_candidate_and_stale_approval_refused(fake_tts):
 p=book();sid=first(p)['id'];j=start(p,{'scope':'segment','segment_id':sid,'override_text':'Hola.'});wait(p,j['id'])
 v=first(m.get(p['id']))['versions'][-1];h=digest(m.DATA/v['file'])
 current=m.get(p['id']);first(current)['revision']=42;m.save(current)
 assert c.post(base(p)+f'/segments/{sid}/versions/{v["id"]}/approve').status_code==409
 assert c.post(base(p)+f'/segments/{sid}/versions/{v["id"]}/reject').status_code==200
 assert digest(m.DATA/v['file'])==h and first(m.get(p['id']))['audio'] is None
 assert c.post(base(p)+f'/segments/{sid}/versions/{v["id"]}/restore').status_code==409

def test_cancel_does_not_block_project_reads_and_retains_completed(fake_tts,monkeypatch):
 from app.tts_provider import generate
 p=book();rule(p);entered=threading.Event();release=threading.Event()
 def blocked(*args,**kwargs):
  entered.set();assert release.wait(5);return generate(*args,**kwargs)
 monkeypatch.setattr('app.tts_provider.generate',blocked)
 j=start(p,{'scope':'project'});assert entered.wait(3)
 try:
  assert c.get(f'/api/projects/{p["id"]}').status_code==200
  assert c.post(base(p)+f'/jobs/{j["id"]}/cancel').json()['cancel_requested']
  view=c.post(base(p)+'/preview',json={'scope':'project'}).json()
  assert c.post(base(p)+'/jobs',json={'scope':'project','confirmed':True,'preview_token':view['preview_token']}).status_code==409
  other=book();assert c.get(base(other)+f'/jobs/{j["id"]}').status_code==404
 finally:release.set()
 r=wait(p,j['id']);assert r['status']=='cancelled' and r['done']==1
 assert len(first(m.get(p['id']))['versions'])==1

def test_failures_and_restart_recovery(monkeypatch):
 p=book()
 def fail(*args):raise RuntimeError('Fixture failure')
 monkeypatch.setattr('app.tts_provider.generate',fail)
 j=start(p,{'scope':'segment','segment_id':first(p)['id']});r=wait(p,j['id'])
 assert r['status']=='completed_with_errors' and len(r['errors'])==1 and first(m.get(p['id']))['audio'] is None
 r['status']='running'
 with m.engine.begin() as db:db.execute(sql('UPDATE jobs SET payload=:p WHERE id=:id'),{'id':r['id'],'p':json.dumps(r)})
 ve.recover_jobs();assert c.get(base(p)+f'/jobs/{r["id"]}').json()['status']=='interrupted'

def test_unapproved_audio_never_exported(fake_tts):
 p=book();s=first(p);p=c.post(f'/api/projects/{p["id"]}/segments/{s["id"]}/generate').json()
 s=first(p);s['versions'][0]['status']='proposed';m.save(p);assert ve.approved_audio(s) is None
 assert c.get(f'/api/projects/{p["id"]}/chapters/{p["chapters"][0]["id"]}/export').status_code==409
 assert c.get(f'/api/projects/{p["id"]}/export-book?partial=true').status_code==409
 assert c.post(f'/api/projects/{p["id"]}/export-book/jobs?partial=true').status_code==409


def test_kokoro_http_adapter_with_fixture_wav_and_real_ffmpeg(monkeypatch):
 """Real HTTP+WAV normalization contract, synthetic audio, no model claim."""
 from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
 from io import BytesIO
 from app import kokoro
 import wave
 body=BytesIO()
 with wave.open(body,'wb') as w:
  w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x00\x01'*12000)
 requests=[]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
   self.send_response(200);self.send_header('Content-Type','audio/wav');self.end_headers();self.wfile.write(body.getvalue())
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 monkeypatch.setattr(kokoro,'KOKORO_URL',f'http://127.0.0.1:{server.server_port}')
 import urllib.request
 monkeypatch.setattr(kokoro.urllib.request,'urlopen',urllib.request.build_opener(urllib.request.ProxyHandler({})).open)
 path=m.DATA/'kokoro-contract.wav'
 try:
  result=kokoro.generate('Ditoqs vuelve.','em_santa',path,speed=1.1)
  assert result['duration']==.5 and requests[0]['input']=='Ditoqs vuelve.'
  assert requests[0]['voice']=='em_santa' and result['provider']=='kokoro'
 finally:server.shutdown();server.server_close();thread.join()


def test_audition_repeats_without_changing_project_or_existing_audio(fake_tts):
 p=book();sid=first(p)['id'];c.post(f'/api/projects/{p["id"]}/segments/{sid}/generate')
 before=m.get(p['id']);old=first(before)['audio'];h=digest(m.DATA/old)
 for pron in ['Di toks','Dítóks']:
  r=c.post(base(p)+'/auditions',json={'original':'Ditóx','pronunciation':pron,'phrase':'Ditóx vuelve.','voice':'ef_dora','speed':1.1})
  assert r.status_code==202,r.text
  j=wait(p,r.json()['id']);assert j['status']=='completed' and j['audition']
  assert j['text']==pron+' vuelve.' and c.get('/api/audio/'+j['result']['file']).status_code==200
 assert m.get(p['id'])==before and digest(m.DATA/old)==h
 assert fake_tts[-1]==('Dítóks vuelve.','ef_dora',1.1)
 r=c.post(base(p)+'/auditions',json={'original':'Ditóx','pronunciation':'Di toks','voice':'em_santa','variant':'original'})
 assert wait(p,r.json()['id'])['text']=='Ditóx'


def test_audition_validation_and_provider_error(monkeypatch):
 p=book();body={'original':'Ditóx','pronunciation':'Di toks','voice':'em_santa'}
 for bad in [{'phrase':'Otra palabra.'},{'voice':'unknown'},{'original':' '},{'speed':3},{'phrase':'x'*1001}]:
  assert c.post(base(p)+'/auditions',json={**body,**bad}).status_code==422
 def fail(*args):raise RuntimeError('Fixture unavailable')
 monkeypatch.setattr('app.tts_provider.generate',fail)
 r=c.post(base(p)+'/auditions',json=body);assert r.status_code==202
 j=wait(p,r.json()['id']);assert j['status']=='completed_with_errors' and 'result' not in j
 assert not first(m.get(p['id']))['versions']


def test_delete_audition_isolated_idempotent_and_not_in_history(fake_tts):
 p=book();before=m.get(p['id']);ids=[]
 for pron in ['Di toks','Dítóks']:
  r=c.post(base(p)+'/auditions',json={'original':'Ditóx','pronunciation':pron,'voice':'em_santa'})
  ids.append(wait(p,r.json()['id']))
 removed,kept=ids
 assert c.delete(base(p)+'/auditions/'+removed['id']).status_code==200
 assert not (m.DATA/removed['result']['file']).exists()
 assert (m.DATA/kept['result']['file']).is_file()
 assert m.get(p['id'])==before
 assert c.delete(base(p)+'/auditions/'+removed['id']).status_code==200
 assert 'result' not in c.get(base(p)+'/jobs/'+removed['id']).json()
 listed=c.get(base(p)+'/auditions').json()
 assert removed['id'] not in [j['id'] for j in listed] and kept['id'] in [j['id'] for j in listed]
 other=book();assert c.delete(base(other)+'/auditions/'+kept['id']).status_code==404


def test_delete_audition_protects_project_history_and_other_jobs(fake_tts):
 p=book();r=c.post(base(p)+'/auditions',json={'original':'Ditóx','pronunciation':'Di toks','voice':'em_santa'});j=wait(p,r.json()['id']);name=j['result']['file'];h=digest(m.DATA/name)
 p=m.get(p['id']);first(p)['versions']=[{'file':name,'status':'approved'}];m.save(p)
 assert c.delete(base(p)+'/auditions/'+j['id']).status_code==409
 assert digest(m.DATA/name)==h
 p['deleted_at']='fixture';m.save(p)
 other=book();otherj=dict(j,id='shared-fixture',project_id=other['id'])
 with m.engine.begin() as db:db.execute(sql('INSERT INTO jobs VALUES (:id,:p)'),{'id':otherj['id'],'p':json.dumps(otherj)})
 assert c.delete(base(other)+'/auditions/shared-fixture').status_code==409
 assert digest(m.DATA/name)==h
 # An ordinary fragment job is never a deletable audition.
 normal=start(other,{'scope':'segment','segment_id':first(other)['id']});wait(other,normal['id'])
 assert c.delete(base(other)+'/auditions/'+normal['id']).status_code==404


def test_delete_sample_rejects_unsafe_path_and_file_error_can_retry(fake_tts,monkeypatch):
 from pathlib import Path
 p=book();r=c.post(base(p)+'/auditions',json={'original':'Ditóx','pronunciation':'Di toks','voice':'em_santa'});j=wait(p,r.json()['id']);path=m.DATA/j['result']['file']
 before=path.read_bytes();original_unlink=Path.unlink
 def denied(target,*args,**kwargs):
  if target==path:raise PermissionError('Fixture busy file')
  return original_unlink(target,*args,**kwargs)
 monkeypatch.setattr(Path,'unlink',denied)
 assert c.delete(base(p)+'/auditions/'+j['id']).status_code==409
 assert path.read_bytes()==before and c.get(base(p)+'/jobs/'+j['id']).json()['status']=='completed'
 monkeypatch.setattr(Path,'unlink',original_unlink)
 j['result']['file']='../private.wav'
 with m.engine.begin() as db:db.execute(sql('UPDATE jobs SET payload=:p WHERE id=:id'),{'id':j['id'],'p':json.dumps(j)})
 assert c.delete(base(p)+'/auditions/'+j['id']).status_code==409 and path.read_bytes()==before
 j['result']['file']=path.name;j['status']='running'
 with m.engine.begin() as db:db.execute(sql('UPDATE jobs SET payload=:p WHERE id=:id'),{'id':j['id'],'p':json.dumps(j)})
 assert c.delete(base(p)+'/auditions/'+j['id']).status_code==409
 j['status']='deleting'
 with m.engine.begin() as db:db.execute(sql('UPDATE jobs SET payload=:p WHERE id=:id'),{'id':j['id'],'p':json.dumps(j)})
 assert c.delete(base(p)+'/auditions/'+j['id']).status_code==200 and not path.exists()


def test_mentions_group_real_speakers_counts_and_pending():
 p=book();current=m.get(p['id']);first(current)['text']='Ditóx y DITÓX. Ditóxiano no cuenta.'
 current['chapters'][0]['segments'][1]['excluded']=True
 current['chapters'][1]['segments'][0].update(speaker='Sin atribuir',review=True)
 m.save(current)
 r=c.get(base(p)+'/mentions',params={'original':'Ditóx'});assert r.status_code==200
 v=r.json();assert v['total']==4 and v['eligible_count']==2 and len(v['groups'])==2
 ana=v['groups'][0];assert ana['speaker']=='Ana' and ana['count']==3 and len(ana['occurrences'])==2
 assert ana['occurrences'][1]['excluded'] and not ana['occurrences'][1]['eligible']
 assert v['groups'][1]['character_id'] is None
 assert c.get(base(p)+'/mentions',params={'original':' '}).status_code==422
 assert c.get(base(p)+'/mentions',params={'original':'Nada'}).json()['total']==0


def test_uniform_name_all_voices_preserves_audio_and_disables_conflicting_rules(fake_tts):
 p=book();ana=next(c for c in p['characters'] if c['name']=='Ana')
 rule(p,pronunciation='Otro',character_id=ana['id']);rule(p,original='Ditóx vuelve',pronunciation='Más largo')
 for ch in p['chapters']:
  for s in ch['segments']:c.post(f'/api/projects/{p["id"]}/segments/{s["id"]}/generate')
 before=m.get(p['id']);names={s['audio']:digest(m.DATA/s['audio']) for ch in before['chapters'] for s in ch['segments']}
 view=c.get(base(p)+'/mentions',params={'original':'Ditóx'}).json()
 body={'original':'Ditóx','pronunciation':'Di tóks','snapshot_token':view['snapshot_token']}
 assert c.put(base(p)+'/uniform-pronunciation',json=body).status_code==409
 r=c.put(base(p)+'/uniform-pronunciation',json={**body,'confirmed':True});assert r.status_code==200,r.text
 after=m.get(p['id']);assert after['chapters']==before['chapters'] and after['original']==before['original']
 assert r.json()['rule']['uniform'] and r.json()['rule']['character_id'] is None
 for ch in after['chapters']:
  for s in ch['segments']:
   for voice in ['em_santa','ef_dora','es-MX-JorgeMultilingualNeural']:
    assert ve.rendered(after,{**s,'voice':voice}).startswith('Di tóks ')
 for name,h in names.items():assert digest(m.DATA/name)==h
 assert len([r for r in after['pronunciation_rules'] if r['active']])==1
 assert rule(p,pronunciation='Conflicto',character_id=ana['id']).status_code==409
 assert rule(p,original='Ditóx espera',pronunciation='Conflicto').status_code==409
 old=after['pronunciation_rules'][0]
 assert c.patch(base(p)+f'/rules/{old["id"]}?active=true').status_code==409
 assert c.put(base(p)+'/uniform-pronunciation',json={**body,'confirmed':True}).status_code==409
 # New generation uses the uniform rule and keeps original manuscript text.
 c.post(f'/api/projects/{p["id"]}/segments/{first(p)["id"]}/generate')
 assert fake_tts[-1][0]=='Di tóks vuelve.'


def test_voice_exception_only_selected_voice_and_incorporation_restore(fake_tts):
 p=book();pid=p['id']
 # Different voice in the second chapter, same name in every fragment.
 current=m.get(pid);current['chapters'][1]['segments'][0]['voice']='ef_dora';m.save(current)
 for ch in current['chapters']:
  for s in ch['segments']:assert c.post(f'/api/projects/{pid}/segments/{s["id"]}/generate').status_code==200
 p=m.get(pid);before=p['chapters'];hashes={s['audio']:digest(m.DATA/s['audio']) for ch in p['chapters'] for s in ch['segments']}
 view=c.get(base(p)+'/mentions',params={'original':'Ditóx'}).json()
 assert c.put(base(p)+'/uniform-pronunciation',json={'original':'Ditóx','pronunciation':'Di toks','snapshot_token':view['snapshot_token'],'confirmed':True}).status_code==200
 r=c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Dítóks','voice':'em_santa'});assert r.status_code==200,r.text
 assert all(g['pronunciation']==('Dítóks' if g['voice']=='em_santa' else 'Di toks') for g in r.json()['mentions']['groups'])
 current=m.get(pid)
 assert ve.rendered(current,first(current))=='Dítóks vuelve.'
 assert ve.rendered(current,current['chapters'][1]['segments'][0])=='Di toks espera.'
 plan=c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json();assert plan['count']==3
 body={'original':'Ditóx','preview_token':plan['preview_token']}
 assert c.post(base(p)+'/incorporation',json=body).status_code==409
 r=c.post(base(p)+'/incorporation',json={**body,'confirmed':True});assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['incorporated']==3 and j['status']=='completed'
 after=m.get(pid)
 assert after['original']==p['original']
 for ch,old_ch in zip(after['chapters'],before):
  for s,old in zip(ch['segments'],old_ch['segments']):
   assert s['audio']!=old['audio'] and s['text']==old['text'] and s['voice']==old['voice']
   assert s['versions'][-1]['status']=='approved'
 for name,h in hashes.items():assert digest(m.DATA/name)==h
 assert c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json()['count']==0
 assert c.get(f'/api/projects/{pid}/chapters/{after["chapters"][0]["id"]}/export').status_code==200
 r=c.post(base(p)+f'/incorporation/{j["id"]}/restore');assert r.status_code==200,r.text
 restored=m.get(pid)
 assert [s['audio'] for ch in restored['chapters'] for s in ch['segments']]==list(hashes)
 assert c.post(base(p)+f'/incorporation/{j["id"]}/restore').status_code==409
 oid=current['pronunciation_voice_overrides'][0]['id']
 assert c.delete(base(p)+'/voice-pronunciation/'+oid).status_code==200
 assert ve.rendered(m.get(pid),first(m.get(pid)))=='Di toks vuelve.'


def test_incorporation_stale_rules_skips_missing_and_unchanged(fake_tts):
 p=book();sid=first(p)['id'];c.post(f'/api/projects/{p["id"]}/segments/{sid}/generate')
 assert c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Cambio','voice':'unknown'}).status_code==422
 assert c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Cambio','voice':'ef_dora'}).status_code==409
 plan=c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json()
 assert plan['count']==0 and plan['skipped']['already_current']==1 and plan['skipped']['no_audio']==2
 c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Cambio','voice':'em_santa'})
 assert c.post(base(p)+'/incorporation',json={'original':'Ditóx','preview_token':plan['preview_token'],'confirmed':True}).status_code==409
 plan=c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json();assert plan['count']==1
 current=m.get(p['id']);first(current)['review']=True;m.save(current)
 assert c.post(base(p)+'/incorporation',json={'original':'Ditóx','preview_token':plan['preview_token'],'confirmed':True}).status_code==409


def test_incorporation_conflict_keeps_active_and_stores_candidate(fake_tts,monkeypatch):
 from app.tts_provider import generate
 p=book();sid=first(p)['id'];c.post(f'/api/projects/{p["id"]}/segments/{sid}/generate')
 c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Cambio','voice':'em_santa'})
 old=first(m.get(p['id']))['audio'];entered=threading.Event();release=threading.Event()
 def blocked(*args,**kwargs):
  entered.set();assert release.wait(5);return generate(*args,**kwargs)
 monkeypatch.setattr('app.tts_provider.generate',blocked)
 plan=c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json()
 r=c.post(base(p)+'/incorporation',json={'original':'Ditóx','preview_token':plan['preview_token'],'confirmed':True});assert r.status_code==202
 assert entered.wait(3)
 try:
  current=m.get(p['id']);first(current)['revision']=999;m.save(current)
 finally:release.set()
 j=wait(p,r.json()['id']);assert j['incorporated']==0 and j['errors'] and j['processed']==1
 s=first(m.get(p['id']));assert s['audio']==old and s['versions'][-1]['status']=='proposed'


def test_incorporation_cancel_partial_resume_plan_and_restore_guard(fake_tts,monkeypatch):
 p=book();pid=p['id']
 for ch in p['chapters']:
  for s in ch['segments']:c.post(f'/api/projects/{pid}/segments/{s["id"]}/generate')
 original=m.get(pid);old=[s['audio'] for ch in original['chapters'] for s in ch['segments']]
 c.put(base(p)+'/voice-pronunciation',json={'original':'Ditóx','pronunciation':'Cambio','voice':'em_santa'})
 from app.tts_provider import generate
 entered=threading.Event();release=threading.Event()
 def blocked(*args,**kwargs):
  entered.set();assert release.wait(5);return generate(*args,**kwargs)
 monkeypatch.setattr('app.tts_provider.generate',blocked)
 plan=c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json()
 r=c.post(base(p)+'/incorporation',json={'original':'Ditóx','preview_token':plan['preview_token'],'confirmed':True});assert r.status_code==202
 assert entered.wait(3)
 try:assert c.post(base(p)+'/jobs/'+r.json()['id']+'/cancel').status_code==200
 finally:release.set()
 j=wait(p,r.json()['id']);assert j['status']=='cancelled' and j['incorporated']==1
 current=m.get(pid);active=[s['audio'] for ch in current['chapters'] for s in ch['segments']]
 assert active[0]!=old[0] and active[1:]==old[1:]
 assert c.get(base(p)+'/incorporation',params={'original':'Ditóx'}).json()['count']==2
 first(current)['revision']+=1;m.save(current)
 assert c.post(base(p)+f'/incorporation/{j["id"]}/restore').status_code==409
 assert [s['audio'] for ch in m.get(pid)['chapters'] for s in ch['segments']]==active
