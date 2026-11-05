import copy
from app import main as m,sound_mixer as sm
from test_sound_mixer import setup,c,body,create

def test_chapter_volume_scoped_persistent_preserves_effects_and_balance():
 p=setup();pid=p['id'];ch=p['chapters'][0]['id'];effect=create(p)
 with m.lock:
  pp=m.get(pid);music={**effect,'id':'music','role':'music','volume_db':-12};pp['sound_cues'].append(music)
  other=copy.deepcopy(pp['chapters'][0]);other['id']='other';other['segments']=[{**s,'id':'other'+s['id']} for s in other['segments']];pp['chapters'].append(other)
  pp['sound_cues'].append({**music,'id':'othermusic','segment_id':other['segments'][0]['id']})
  pp['sound_scene_levels']={pp['chapters'][0]['segments'][0]['id']:{'narration_db':2,'effects_db':-3,'music_db':-6}}
  pp['sound_music_drafts']={pp['chapters'][0]['segments'][0]['id']:{'sound_id':'sound1','volume_db':-12}}
  before=copy.deepcopy(pp);m.save(pp)
 base=f'/api/projects/{pid}/sound-mixer';r=c.put(base+f'/chapters/{ch}/music-volume',json={'volume_db':-18});assert r.status_code==200,r.text
 pp=m.get(pid);assert pp['chapters']==before['chapters'] and pp['sound_effects']==before['sound_effects']
 assert pp['sound_cues'][0]==before['sound_cues'][0] and pp['sound_cues'][2]==before['sound_cues'][2]
 assert pp['sound_cues'][1]['volume_db']==-18
 assert next(iter(pp['sound_scene_levels'].values()))==dict(narration_db=2,effects_db=-3,music_db=0)
 assert next(iter(pp['sound_music_drafts'].values()))['volume_db']==-18
 assert c.get(base).json()['chapter_music'][ch]['volume_db']==-18
 scene=pp['chapters'][0]['segments'][0]['id']
 r=c.post(base+'/music-bed',json={'scene_id':scene,'sound_id':'sound1'});assert r.status_code==200,r.text
 assert r.json()['volume_db']==-18
 r=c.post(base+'/music-bed',json={'scene_id':scene,'sound_id':'sound1','volume_db':-22});assert r.json()['volume_db']==-22

def test_validation_busy_and_foreign_chapter_do_not_mutate():
 p=setup();base=f'/api/projects/{p["id"]}/sound-mixer/chapters/';ch=p['chapters'][0]['id'];before=copy.deepcopy(m.get(p['id']))
 assert c.put(base+ch+'/music-volume',json={'volume_db':-50}).status_code==422
 assert c.put(base+'foreign/music-volume',json={'volume_db':-18}).status_code==404
 sm.ACTIVE.acquire()
 try:assert c.put(base+ch+'/music-volume',json={'volume_db':-18}).status_code==409
 finally:sm.ACTIVE.release()
 assert m.get(p['id'])==before

def test_upload_inherits_chapter_default_and_old_preview_becomes_stale():
 from test_sound_upload import wav_bytes
 from test_sound_mixer import render
 p=setup();pid=p['id'];ch=p['chapters'][0]['id'];create(p)
 base=f'/api/projects/{pid}/sound-mixer';sid=p['chapters'][0]['segments'][0]['id']
 with m.lock:
  pp=m.get(pid);pp['sound_cues'].append({**pp['sound_cues'][0],'id':'music','role':'music'});m.save(pp)
 result=render(p)
 assert c.put(base+f'/chapters/{ch}/music-volume',json={'volume_db':-22}).status_code==200
 assert c.get(base).json()['mixes'][0]['stale']
 uploaded=c.post(f'/api/projects/{pid}/sound-checklist/uploads',files={'file':('music.wav',wav_bytes(),'audio/wav')},data={'scene_id':sid,'name':'Nueva musica','media_kind':'music'})
 assert uploaded.status_code==201,uploaded.text
 assert c.get(base).json()['music_drafts'][sid]['volume_db']==-22
