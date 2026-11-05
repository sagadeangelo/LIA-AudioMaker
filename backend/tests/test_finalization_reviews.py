import copy, hashlib
from fastapi.testclient import TestClient
from app import main as m
from test_voice_editor import book, base, first, wait, rule
from test_finalization import view, url, generate_all
c=TestClient(m.app)
def apply_reviews(p,v,choices):
 return c.post(url(p)+'/apply',json={'preview_token':v['preview_token'],'confirmed':True,'confirm_reviews':True,'review_choices':choices,'selections':{r['segment_id']:r['recommended_version_id'] for r in v['rows'] if r['recommended_version_id']}})
def reviewed_fixture():
 p=generate_all(book())
 for ch in p['chapters']:
  for s in ch['segments']:s.update(review=True,content_review=True,review_reason='Confirmar acotación.')
 m.save(p)
 return p

def test_confirm_previously_repaired_wavs_without_paid_generation_and_undo(fake_tts):
 p=reviewed_fixture();before=copy.deepcopy(p);hashes={s['audio']:hashlib.sha256((m.DATA/s['audio']).read_bytes()).hexdigest() for ch in p['chapters'] for s in ch['segments']}
 count=len(fake_tts);v=view(p);assert v['totals']['review']==3
 r=apply_reviews(p,v,{s['segment_id']:'keep' for s in v['rows']});assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['reviewed']==3 and j['incorporated']==0 and not j['errors'];assert len(fake_tts)==count
 v=view(p);assert v['ready'] and v['totals']['review']==0
 after=m.get(p['id']);assert after['original']==before['original']
 for ch,old_ch in zip(after['chapters'],before['chapters']):
  for s,old in zip(ch['segments'],old_ch['segments']):
   assert s['audio']==old['audio'] and s['text']==old['text'] and not s['review'] and not s['content_review'] and s['speaker_confirmed']
 for name,digest in hashes.items():assert hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()==digest
 restored=c.post(base(p)+f'/incorporation/{j["id"]}/restore');assert restored.status_code==200,restored.text
 assert view(p)['totals']['review']==3 and len(fake_tts)==count

def test_unknown_without_audio_needs_cast_but_can_be_resolved_in_same_batch(fake_tts):
 p=book();s=first(p);s.update(speaker='Sin atribuir',review=True,content_review=True);s.pop('character_id',None);m.save(p)
 v=view(p);row=next(r for r in v['rows'] if r['segment_id']==s['id']);assert row['character_id'] is None
 assert apply_reviews(p,v,{s['id']:'keep'}).status_code==409
 assert apply_reviews(p,v,{}).status_code==409
 narrator=next(ch for ch in v['characters'] if ch['name']=='Narrador')
 r=apply_reviews(p,v,{s['id']:narrator['id']});assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['reviewed']==1 and j['incorporated']==3 and not j['errors']
 current=first(m.get(p['id']));assert current['speaker']=='Narrador' and current['voice']==narrator['voice'] and not current['review']
 assert view(p)['ready']

def test_manual_audio_acceptance_does_not_regenerate_known_correct_pronunciation(fake_tts):
 p=reviewed_fixture();rule(p);v=view(p);assert all(r['audio_status']=='outdated' for r in v['rows'])
 # The user explicitly certifies the WAVs were already repaired outside this recorded TTS request.
 count=len(fake_tts);r=apply_reviews(p,v,{s['segment_id']:'keep' for s in v['rows']});assert r.status_code==202
 wait(p,r.json()['id']);assert view(p)['ready'] and len(fake_tts)==count
 # Future dictionary edits invalidate this manual confirmation.
 rid=c.get(base(p)+'/rules').json()[0]['id'];c.put(base(p)+'/rules/'+rid,json={'original':'Ditóx','pronunciation':'Di toks'})
 assert not view(p)['ready']

def test_voice_change_generates_correct_profile_and_guarded_restore(fake_tts):
 p=reviewed_fixture();v=view(p);profile=next(ch for ch in p['characters'] if ch['name']=='Narrador');profile.update(voice='ef_dora',speed=1.25)
 for ch in p['chapters']:
  for s in ch['segments']:
   if s['id']!=first(p)['id']:s.update(review=False,content_review=False)
 m.save(p);v=view(p);r=apply_reviews(p,v,{first(p)['id']:profile['id']});assert r.status_code==202,r.text
 j=wait(p,r.json()['id']);assert j['incorporated']==1 and j['reviewed']==1
 current=m.get(p['id']);s=first(current);assert s['voice']=='ef_dora' and s['speed']==1.25 and fake_tts[-1][1:] == ('ef_dora',1.25)
 s['revision']+=1;m.save(current)
 assert c.post(base(p)+f'/incorporation/{j["id"]}/restore').status_code==409
 assert not first(m.get(p['id']))['review']

def test_stale_review_plan_is_rejected_before_flags_are_cleared(fake_tts):
 p=reviewed_fixture();v=view(p);current=m.get(p['id']);first(current)['review_reason']='Cambio de la revisión';m.save(current)
 assert apply_reviews(p,v,{s['segment_id']:'keep' for s in v['rows']}).status_code==409
 assert view(p)['totals']['review']==3
