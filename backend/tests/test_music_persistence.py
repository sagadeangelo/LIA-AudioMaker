import copy
from fastapi.testclient import TestClient
from app import main as m, sound_mixer as sm
from test_sound_mixer import setup
from test_sound_upload import wav_bytes

c=TestClient(m.app)


def test_choice_survives_reload_without_becoming_applied_until_saved():
    p=setup();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id'];base=f'/api/projects/{pid}/sound-mixer'
    before=copy.deepcopy(m.get(pid));fp=sm.fingerprint(before,sid)
    body={'sound_id':'sound1','volume_db':-8}
    assert c.put(base+'/scenes/'+sid+'/music-draft',json=body).status_code==200
    reopened=TestClient(m.app).get(base).json()
    assert reopened['music_drafts'][sid]['sound_id']=='sound1' and reopened['music_drafts'][sid]['volume_db']==-8
    assert reopened['cues']==[] and sm.fingerprint(m.get(pid),sid)==fp
    r=c.post(base+'/music-bed',json={'scene_id':sid,**body});assert r.status_code==200,r.text
    reopened=TestClient(m.app).get(base).json()
    assert sid not in reopened['music_drafts']
    assert reopened['cues'][0]['sound_id']=='sound1' and reopened['cues'][0]['volume_db']==-8
    assert reopened['cues'][0]['role']=='music'
    assert m.get(pid)['chapters']==before['chapters']


def test_upload_association_is_saved_on_server_without_ui_callback():
    p=setup();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id'];base=f'/api/projects/{pid}/sound-mixer'
    result=c.post(f'/api/projects/{pid}/sound-checklist/uploads',files={'file':('musica.wav',wav_bytes(),'audio/wav')},data={'scene_id':sid,'name':'Mi música'})
    assert result.status_code==201,result.text
    uploaded=result.json()['sound']
    reopened=TestClient(m.app).get(base).json()
    assert reopened['music_drafts'][sid]['sound_id']==uploaded['id']
    assert any(s['id']==uploaded['id'] for s in reopened['sounds'])
    assert reopened['cues']==[]
    assert c.delete(f'/api/projects/{pid}/sound-checklist/library/{uploaded["id"]}').status_code==200
    assert sid not in c.get(base).json()['music_drafts']


def test_draft_cannot_reference_other_project_or_missing_scene_and_clear_keeps_saved_bed():
    p=setup();other=setup();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id'];base=f'/api/projects/{pid}/sound-mixer'
    other_sound=c.post(f'/api/projects/{other["id"]}/sound-checklist/uploads',files={'file':('a.wav',wav_bytes(),'audio/wav')}).json()['sound']
    before=copy.deepcopy(m.get(pid))
    assert c.put(base+'/scenes/'+sid+'/music-draft',json={'sound_id':other_sound['id']}).status_code==409
    assert c.put(base+'/scenes/missing/music-draft',json={'sound_id':'sound1'}).status_code==409
    assert m.get(pid)==before
    assert c.post(base+'/music-bed',json={'scene_id':sid,'sound_id':'sound1'}).status_code==200
    saved=copy.deepcopy(m.get(pid)['sound_cues'])
    assert c.put(base+'/scenes/'+sid+'/music-draft',json={'sound_id':'sound1','volume_db':-5}).status_code==200
    assert c.delete(base+'/scenes/'+sid+'/music-draft').status_code==200
    assert m.get(pid)['sound_cues']==saved


def test_scenes_keep_independent_choices_and_invalid_upload_target_is_atomic():
    p=setup();pid=p['id']
    with m.lock:
        p=m.get(pid);p['chapters'][0]['segments'][1]['scene']=2;m.save(p)
    ids=[s['id'] for s in p['chapters'][0]['segments']];base=f'/api/projects/{pid}/sound-mixer'
    for sid,volume in zip(ids,[-6,-16]):assert c.put(base+'/scenes/'+sid+'/music-draft',json={'sound_id':'sound1','volume_db':volume}).status_code==200
    drafts=c.get(base).json()['music_drafts'];assert drafts[ids[0]]['volume_db']==-6 and drafts[ids[1]]['volume_db']==-16
    before=copy.deepcopy(m.get(pid))
    result=c.post(f'/api/projects/{pid}/sound-checklist/uploads',files={'file':('a.wav',wav_bytes(),'audio/wav')},data={'scene_id':'missing'})
    assert result.status_code==409 and m.get(pid)==before


def test_music_catalog_metadata_persists_and_is_project_scoped():
    p=setup();base=f'/api/projects/{p["id"]}/sound-mixer'
    before=copy.deepcopy(m.get(p['id']))
    r=c.put(base+'/library/sound1/classification',json={'media_kind':'music','music_category':'Drama'})
    assert r.status_code==200,r.text
    sound=next(s for s in TestClient(m.app).get(base).json()['sounds'] if s['id']=='sound1')
    assert sound['media_kind']=='music' and sound['music_category']=='Drama'
    assert m.get(p['id'])['chapters']==before['chapters']
    assert c.put(base+'/library/missing/classification',json={'media_kind':'music'}).status_code==404
    assert c.put(base+'/library/sound1/classification',json={'media_kind':'invalid'}).status_code==422
    uploaded=c.post(f'/api/projects/{p["id"]}/sound-checklist/uploads',files={'file':('track.wav',wav_bytes(),'audio/wav')},data={'kind':'music'}).json()['sound']
    assert uploaded['media_kind']=='music'


def test_upload_uses_scene_category_and_reuse_preserves_manual_category():
    p=setup();url=f'/api/projects/{p["id"]}/sound-checklist/uploads'
    def upload(category):return c.post(url,files={'file':('random.wav',wav_bytes(),'audio/wav')},data={'kind':'music','music_category':category})
    first=upload('Suspenso');assert first.status_code==201,first.text
    sound=first.json()['sound'];assert sound['music_category']=='Suspenso'
    assert upload('Ira / enojo').json()['sound']['id']==sound['id']
    assert upload('Ira / enojo').json()['sound']['music_category']=='Suspenso'
    assert upload('Invalid').status_code==422
