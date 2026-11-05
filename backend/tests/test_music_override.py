import copy
from app import main as m,production_runner as runner,sound_mixer as sm
from test_sound_mixer import setup,create,c

def test_manual_replacement_preserves_audio_effects_other_scene_and_locks_choice():
 p=setup();fx=create(p);pid=p['id'];sid=p['chapters'][0]['segments'][0]['id']
 with m.lock:
  pp=m.get(pid);pp['chapters'][0]['segments'][1]['scene']=2
  pp['sound_cues']=[{**fx,'id':'fx'}, {**fx,'id':'old','role':'music','segment_id':sid}]
  pp['sound_scene_levels']={sid:dict(narration_db=2,effects_db=-3,music_db=-12)}
  before=copy.deepcopy(pp);m.save(pp)
 r=c.post(f'/api/projects/{pid}/sound-mixer/manual-music',json=dict(scene_id=sid,sound_id='sound1',volume_db=-9));assert r.status_code==200,r.text
 pp=m.get(pid);assert pp['chapters']==before['chapters'] and pp['sound_cues'][0]==before['sound_cues'][0]
 assert len(pp['sound_cues'])==2 and pp['sound_cues'][-1]['manual_override']
 assert pp['sound_scene_levels'][sid]==dict(narration_db=2,effects_db=-3,music_db=0)
 # A later automatic proposal must not add music over the manual choice.
 job={'id':'run','plan':{'scenes':[{'scene_id':sid,'music':[{}]}]}}
 runner.place_cues(pp,job)
 assert len(pp['sound_cues'])==2 and pp['sound_cues'][-1]['volume_db']==-9

def test_missing_foreign_resource_and_running_mix_are_explicit_errors():
 p=setup();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id'];base=f'/api/projects/{pid}/sound-mixer/manual-music';before=copy.deepcopy(m.get(pid))
 r=c.post(base,json=dict(scene_id=sid,sound_id='foreign',volume_db=-12));assert r.status_code==404
 assert m.get(pid)==before
 sm.ACTIVE.acquire()
 try:assert c.post(base,json=dict(scene_id=sid,sound_id='sound1',volume_db=-12)).status_code==409
 finally:sm.ACTIVE.release()
