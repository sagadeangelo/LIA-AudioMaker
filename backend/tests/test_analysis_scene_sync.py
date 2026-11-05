import copy,json,hashlib
from fastapi.testclient import TestClient
from app import main as m
from app.manuscript_analysis import read_job
from test_analysis_batch import fixture,submit
from test_manuscript_analysis import run
c=TestClient(m.app)


def legacy_report(pid,jid):
 j=read_job(pid,jid);path=m.DATA/j['report_file'];r=json.loads(path.read_text());r.pop('content_token',None);path.write_text(json.dumps(r));return r


def test_scene_approval_keeps_other_categories_available_and_sound_evidence_relocated(fake_tts):
 p=fixture();sid=p['chapters'][0]['segments'][0]['id'];c.post(f'/api/projects/{p["id"]}/segments/{sid}/generate');before=copy.deepcopy(m.get(p['id']));audio=before['chapters'][0]['segments'][0]['audio'];sha=hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()
 jid,r=run(p)
 # Previously completed work must keep the same review key after the split.
 assert submit(p,jid,r,'current_scene',['0']).status_code==200
 assert submit(p,jid,r,'sound',['0']).status_code==200
 result=submit(p,jid,r,'scene',['0','1']);assert result.status_code==200,result.text
 refreshed=result.json()['report'];assert not refreshed['stale'] and len(refreshed['scenes'])==3
 assert refreshed['scenes'][0]['id']=='0'
 assert any(x['scene']==3 for x in refreshed['sound_suggestions'])
 assert len(m.get(p['id'])['manuscript_reviews'])==4
 ids=[str(i) for i in range(len(refreshed['emotions']))]
 # Fixture has no lexically detected emotion, add 42 actual report suggestions
 # with existing evidence to reproduce the user's disabled remaining category.
 j=read_job(p['id'],jid);path=m.DATA/j['report_file'];saved=json.loads(path.read_text());saved['emotions']=[{**saved['sound_suggestions'][0],'label':f'Indicio {i}'} for i in range(42)];path.write_text(json.dumps(saved))
 current=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json();assert not current['stale']
 result=submit(p,jid,current,'emotion',[str(i) for i in range(42)]);assert result.status_code==200 and result.json()['applied']==42
 after=m.get(p['id'])
 for ch in before['chapters']:
  for s in ch['segments']:
   newer=next(x for n in after['chapters'] for x in n['segments'] if x['id']==s['id'])
   assert {k:v for k,v in newer.items() if k!='scene'}=={k:v for k,v in s.items() if k!='scene'}
 assert hashlib.sha256((m.DATA/audio).read_bytes()).hexdigest()==sha


def test_pre_patch_stale_report_recovers_from_recorded_scene_history_without_reanalysis():
 p=fixture();jid,r=run(p);legacy=legacy_report(p['id'],jid)
 # Simulate 0.5.2 writing the project and leaving its report file unchanged.
 from app.manuscript_analysis import record_decision,Review
 project=m.get(p['id'])
 for i in range(2):
  body=Review(job_id=jid,document_token=legacy['document_token'],category='scene',item_id=str(i),decision='confirm')
  record_decision(project,legacy,body,legacy['scene_candidates'][i])
 m.save(project);before=copy.deepcopy(m.get(p['id']))
 current=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json()
 assert not current['stale'] and current['document_token']!=legacy['document_token']
 assert len(m.get(p['id'])['manuscript_reviews'])==2
 assert submit(p,jid,current,'place',[current['places'][0]['id']]).status_code==200
 assert m.get(p['id'])['chapters']==before['chapters']


def test_material_edits_still_block_new_and_legacy_reports():
 for old in (False,True):
  p=fixture();jid,r=run(p)
  if old:r=legacy_report(p['id'],jid)
  result=submit(p,jid,r,'scene',['0']);assert result.status_code==200
  changed=m.get(p['id']);changed['chapters'][0]['segments'][0]['text']+=' Texto nuevo real.';m.save(changed)
  current=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json();assert current['stale']
  before=copy.deepcopy(m.get(p['id']));assert submit(p,jid,current,'sound',['0']).status_code==409
  assert m.get(p['id'])==before


def test_scene_metadata_refresh_preserves_imported_editorial_ids_and_undo():
 from test_editorial_plan import setup,preview,apply
 p,plan=setup();pr=preview(p,plan);result=apply(p,plan,pr);jid=result.json()['job']['id']
 report=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json()
 assert submit(p,jid,report,'editorial_scene',[plan['scenes'][0]['id']]).status_code==200
 # Import another copy of the plan with compatible boundaries. Content remains
 # identical, so the earlier report should stay usable without losing approvals.
 project=m.get(p['id']);pr=preview(project,plan)
 # First import did not change the document token, duplicate import protection
 # correctly applies. Change scene numbers independently to simulate an undo.
 project['chapters'][0]['segments'][1]['scene']=2;project['chapters'][0]['segments'][2]['scene']=2;m.save(project)
 refreshed=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json()
 assert not refreshed['stale'] and refreshed['editorial_scenes'][0]['id']==plan['scenes'][0]['id']
 assert len(m.get(p['id'])['manuscript_reviews'])==1
