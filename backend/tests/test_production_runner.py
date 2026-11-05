import copy,hashlib
from app import main as m,production_runner as runner
from app.production_exchange import build_context
from test_sound_mixer import setup,c,wav

def fixture(parts=False,effect=False):
 p=setup()
 with m.lock:
  p=m.get(p['id']);char=p['characters'][0]
  for i,s in enumerate(p['chapters'][0]['segments']):
   s.update(character_id=char['id'],speaker=char['name'],voice=char['voice'],review=False,speed=1,scene=i+1)
  m.save(p)
 ctx=build_context(p,chapter_id=p['chapters'][0]['id'])
 plan=dict(format='lia.production-plan',version=1,project_id=p['id'],document_token=ctx['document_token'],resources_token=ctx['resources_token'],scope_scene_ids=[x['id'] for x in ctx['scenes']],scenes=[])
 for sc in ctx['scenes']:
  performances=[]
  for s in sc['segments']:
   perf=dict(segment_id=s['id'],quote=s['text'],character_id=char['id'],voice_id=char['voice'],speed=1,confidence='high')
   if parts and not plan['scenes']:
    perf['parts']=[dict(text=s['text'][:3],character_id=char['id'],voice_id=char['voice'],speed=1),dict(text=s['text'][3:],character_id=char['id'],voice_id=char['voice'],speed=1)]
   performances.append(perf)
  cues=[dict(segment_id=sc['segments'][0]['id'],anchor_quote=sc['segments'][0]['text'],resource_id='sound1',duration_seconds=.2,reason='Claxon literal')] if effect and plan['scenes'] else []
  plan['scenes'].append(dict(scene_id=sc['id'],decision='sound_design',performances=performances,effects=cues,music=[]))
 base=f'/api/projects/{p["id"]}/production-exchange'
 pr=c.post(base+'/preview',json={'plan':plan});assert pr.status_code==200,pr.text
 assert pr.json()['valid'],pr.text
 saved=c.post(base+'/plans',json={'plan':plan,'preview_token':pr.json()['preview_token'],'confirmed':True});assert saved.status_code==201,saved.text
 return p,base+'/plans/'+saved.json()['id']+'/production'

def start(base):
 pr=c.get(base+'/preview');assert pr.status_code==200,pr.text
 assert pr.json()['can_start'],pr.text
 r=c.post(base+'/runs',json=dict(preview_token=pr.json()['preview_token'],confirmed=True,allow_paid=True,accept_estimated_timing=True));assert r.status_code==202,r.text
 return c.get(base+'/runs').json()['runs'][0]

def test_reuse_mix_download_and_preserve_originals():
 p,base=fixture(effect=True);files={s['audio']:hashlib.sha256((m.DATA/s['audio']).read_bytes()).hexdigest() for s in p['chapters'][0]['segments']}
 r=start(base);assert r['status']=='ready',r
 assert r['reused']==2 and r['generated']==0 and r['completed_scenes']==2
 for kind in ['wav','mp3','credits']:assert c.get(base+'/runs/'+r['id']+'/'+kind).status_code==200
 assert all(hashlib.sha256((m.DATA/n).read_bytes()).hexdigest()==h for n,h in files.items())
 assert len(m.get(p['id'])['sound_cues'])==1

def test_split_failure_resume_generates_only_pending(monkeypatch):
 from app import tts_provider
 p,base=fixture(parts=True);original=''.join(s['text'] for s in p['chapters'][0]['segments']);calls=[]
 def generate(text,voice,speed,path):
  calls.append(text)
  if len(calls)==2:raise RuntimeError('temporary failure')
  wav(path.name,.5);return dict(provider='test',duration=.5)
 monkeypatch.setattr(tts_provider,'generate',generate)
 r=start(base);assert r['status']=='error' and r['generated']==1,r
 first=m.get(p['id'])['chapters'][0]['segments'][0]['audio']
 rr=c.post(base+'/runs/'+r['id']+'/resume',json={'confirmed':True});assert rr.status_code==202,rr.text
 r=c.get(base+'/runs').json()['runs'][0];assert r['status']=='ready',r
 assert len(calls)==3 and r['generated']==2 and r['reused']==1
 p=m.get(p['id']);assert p['chapters'][0]['segments'][0]['audio']==first
 assert ''.join(s['text'] for s in p['chapters'][0]['segments'])==original
 assert len(p['production_runs'][0]['backups'])==2

def test_stale_preview_and_partial_chapter_block():
 p,base=fixture();pr=c.get(base+'/preview').json()
 assert c.post(base+'/runs',json={'confirmed':True,'preview_token':'bad'}).status_code==409
 with m.lock:
  p=m.get(p['id']);p['chapters'][0]['segments'][0]['text']+=' edit';m.save(p)
 assert not c.get(base+'/preview').json()['can_start']
 assert c.post(base+'/runs',json={'confirmed':True,'preview_token':pr['preview_token']}).status_code==409

def test_pause_recover_and_changed_project_cannot_resume(monkeypatch):
 p,base=fixture();original=runner.generate_one
 def paused(pid,planid,runid,sid):
  with m.lock:
   pp=m.get(pid);pp['production_runs'][-1]['pause_requested']=True;m.save(pp)
  return original(pid,planid,runid,sid)
 monkeypatch.setattr(runner,'generate_one',paused)
 r=start(base);assert r['status']=='paused',r
 with m.lock:
  pp=m.get(p['id']);pp['chapters'][0]['segments'][0]['text']+='changed';m.save(pp)
 assert c.post(base+'/runs/'+r['id']+'/resume',json={'confirmed':True}).status_code==409

def test_export_chapter_and_paid_consent_and_recovery(monkeypatch):
 from app import tts_provider
 p,base=fixture();exchange=base.split('/plans/')[0]
 exported=c.get(exchange+'/export',params={'chapter_id':p['chapters'][0]['id']});assert exported.status_code==200
 with m.lock:
  pp=m.get(p['id']);rec=pp['production_plans'][0]
  # The normal fixture uses local voices; a changed voice requires a new plan/context,
  # so force pending generation while preserving the exported configured voice.
  pp['chapters'][0]['segments'][0]['audio']=None
  pp['chapters'][0]['segments'][0]['versions']=[]
  ctx=build_context(pp,chapter_id=pp['chapters'][0]['id']);rec['plan']['document_token']=ctx['document_token'];rec['plan']['resources_token']=ctx['resources_token'];m.save(pp)
 def generate(text,voice,speed,path):
  wav(path.name,.5);return dict(provider='test',duration=.5)
 monkeypatch.setattr(tts_provider,'generate',generate)
 r=start(base);assert r['status']=='ready',r
 with m.lock:
  pp=m.get(p['id']);pp['production_runs'][0]['status']='running';m.save(pp)
 runner.recover();assert c.get(base+'/runs').json()['runs'][0]['status']=='interrupted'
 assert c.post(base+'/runs/'+r['id']+'/resume',json={'confirmed':True}).status_code==202
 assert c.get(base+'/runs').json()['runs'][0]['status']=='ready'

def test_missing_resource_and_unreviewed_question_block():
 p,base=fixture(effect=True)
 with m.lock:
  pp=m.get(p['id']);(m.DATA/pp['sound_effects'][0]['file']).unlink();m.save(pp)
 assert not c.get(base+'/preview').json()['can_start']
 p,base=fixture()
 with m.lock:
  pp=m.get(p['id']);pp['production_plans'][0]['plan']['scenes'][0]['questions']=[{'segment_id':None,'question':'Quién habla aquí?'}];m.save(pp)
 pr=c.get(base+'/preview').json();assert not pr['can_start'] and any('revisión pendiente' in e for e in pr['errors'])
