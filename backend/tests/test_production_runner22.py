import copy
from app import main as m,production_runner as runner,production_exchange as exchange,tts_provider
from app.production_exchange import ProductionPlan,build_context,validate_plan
from app.voice_editor import signature
from test_production_runner import fixture,c,start
from test_sound_mixer import wav

def test_three_parts_disable_cue_fit_music_and_preserve_other_scene(monkeypatch):
 p,base=fixture();pid=p['id']
 with m.lock:
  pp=m.get(pid);rec=pp['production_plans'][0];plan=rec['plan'];s=pp['chapters'][0]['segments'][0];char=pp['characters'][0]
  pp['sound_cues']=[dict(id='oldfx',sound_id='sound1',segment_id=s['id'],offset=0,source_start=0,duration=.2,volume_db=-18,fade_in=0,fade_out=0,loop=False,active=True),dict(id='music',role='music',sound_id='sound1',segment_id=s['id'],offset=0,source_start=0,duration=.9,volume_db=-18,fade_in=.1,fade_out=.1,loop=True,active=True)]
  # Active music is anchored to the first fragment: splitting is disallowed, so
  # put three parts on the other scene, and change voice duration on first scene.
  second=pp['chapters'][0]['segments'][1]
  perf=plan['scenes'][1]['performances'][0]
  perf['parts']=[dict(text=t,character_id=char['id'],voice_id=char['voice'],speed=1) for t in [second['text'][:2],second['text'][2:4],second['text'][4:]]]
  s['audio']=None;s['versions']=[]
  plan['scenes'][0]['existing_cue_actions']=[dict(cue_id='oldfx',action='disable',reason='Duplicate effect')];plan['scenes'][0]['fit_existing_music']=True
  ctx=build_context(pp,chapter_id=pp['chapters'][0]['id']);plan.update(document_token=ctx['document_token'],resources_token=ctx['resources_token']);m.save(pp)
 def gen(text,voice,speed,path):
  wav(path.name,.5);return dict(provider='test',duration=.5)
 monkeypatch.setattr(tts_provider,'generate',gen)
 r=start(base);assert r['status']=='ready',r
 pp=m.get(pid);assert pp['sound_cues'][0]['active'] is False
 assert pp['sound_cues'][1]['duration']==.5
 assert pp['production_runs'][0]['cue_backups'][0]['active'] is True
 assert len(pp['chapters'][0]['segments'])==4
 assert ''.join(s['text'] for s in pp['chapters'][0]['segments'])==''.join(s['text'] for s in p['chapters'][0]['segments'])

def test_disabled_anchored_effect_allows_split_but_foreign_action_blocks():
 p,base=fixture(parts=True)
 with m.lock:
  pp=m.get(p['id']);rec=pp['production_plans'][0];sid=pp['chapters'][0]['segments'][0]['id']
  pp['sound_cues']=[dict(id='fx',segment_id=sid,sound_id='sound1',offset=0,duration=.1,active=True)]
  ctx=build_context(pp,chapter_id=pp['chapters'][0]['id']);rec['plan'].update(document_token=ctx['document_token'],resources_token=ctx['resources_token']);m.save(pp)
 assert not c.get(base+'/preview').json()['can_start']
 with m.lock:
  pp=m.get(p['id']);pp['production_plans'][0]['plan']['scenes'][0]['existing_cue_actions']=[dict(cue_id='fx',action='disable',reason='Remove duplication')];m.save(pp)
 assert c.get(base+'/preview').json()['can_start']
 with m.lock:
  pp=m.get(p['id']);pp['production_plans'][0]['plan']['scenes'][0]['existing_cue_actions'][0]['cue_id']='foreign';m.save(pp)
 assert not c.get(base+'/preview').json()['can_start']
