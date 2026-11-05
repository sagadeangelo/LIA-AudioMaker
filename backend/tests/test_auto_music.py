import copy
from test_sound_mixer import setup,c,m
from app.auto_music import proposal,apply_rows

def ready():
 p=setup()
 with m.lock:
  p=m.get(p['id']);p['sound_effects'][0].update(media_kind='music',music_category='Documental / narrativa')
  p['sound_chapter_music']={p['chapters'][0]['id']:{'volume_db':-18}};m.save(p)
 return p

def test_automatic_selection_save_preserves_volume_and_is_idempotent():
 p=ready();url=f"/api/projects/{p['id']}/sound-mixer/auto-music"
 before=copy.deepcopy(p['chapters']);data=c.get(url).json();assert data['counts']['assign']==1
 r=c.post(url,json={'token':data['token']});assert r.status_code==200,r.text
 p=m.get(p['id']);assert p['chapters']==before
 assert p['sound_cues'][0]['volume_db']==-18
 data=c.get(url).json();assert data['counts']['preserved']==1
 assert c.post(url,json={'token':data['token']}).json()['assigned']==0
 assert len(m.get(p['id'])['sound_cues'])==1

def test_missing_category_draft_and_stale_preview_never_overwrite():
 p=ready();p['sound_effects'][0]['music_category']='Suspenso';assert proposal(p)[0]['status']=='pending'
 sid=p['chapters'][0]['segments'][0]['id'];p['sound_music_drafts']={sid:{'sound_id':'sound1'}}
 assert proposal(p)[0]['status']=='preserved'
 url=f"/api/projects/{p['id']}/sound-mixer/auto-music";data=c.get(url).json()
 with m.lock:p=m.get(p['id']);p['title']='Cambio';m.save(p)
 assert c.post(url,json={'token':data['token']}).status_code==409
 assert not m.get(p['id']).get('sound_cues')

def test_alternates_equal_category_tracks_and_preserves_effects():
 p=ready();s=p['chapters'][0]['segments'];s[1]['scene']=2
 p['sound_effects'].append({**p['sound_effects'][0],'id':'sound2','name':'Otra pista'})
 rows=proposal(p);assert len(rows)==2;assert rows[0]['sound_id']!=rows[1]['sound_id']
 p['sound_cues']=[{'id':'effect','role':'effect','segment_id':s[0]['id'],'sound_id':'sound1','active':True}]
 effect=copy.deepcopy(p['sound_cues'][0]);apply_rows(p,rows)
 assert p['sound_cues'][0]==effect

def test_explicit_silence_in_imported_plan_is_respected():
 p=ready();sid=p['chapters'][0]['segments'][0]['id']
 p['production_plans']=[{'plan':{'scenes':[{'scene_id':sid,'decision':'intentional_silence'}]}}]
 assert proposal(p)[0]['status']=='editorial'
