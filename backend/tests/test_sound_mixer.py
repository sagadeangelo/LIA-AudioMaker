import copy
import hashlib
import struct
import time
import wave

import pytest
from fastapi.testclient import TestClient
from app import main as m, sound_mixer as mix
from app.project_cleanup import project_files
from app.scenes import included

c=TestClient(m.app)


def wav(name,duration=1,rate=24000,amplitude=0):
    path=m.DATA/name
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'))
        w.writeframes(struct.pack('<h',amplitude)*round(rate*duration))
    return path


def setup():
    p=c.post('/api/projects',json={'title':'Escena sonora'}).json();pid=p['id']
    c.post(f'/api/projects/{pid}/manuscript',files={'file':('b.txt','CAPÍTULO I\nEl mar.\nSonó el claxon.'.encode())})
    with m.lock:
        p=m.get(pid)
        segments=[s for ch in p['chapters'] for s in ch['segments'] if included(s)]
        # Keep two one-second segments and deliberately different input sample rates.
        p['chapters'][0]['segments']=segments[:2]
        for i,s in enumerate(p['chapters'][0]['segments']):
            name=f'narration_{pid}_{i}.wav';wav(name,rate=24000 if i==0 else 48000)
            s['audio']=name;s['duration']=1;s['scene']=1
        fx=f'effect_{pid}.wav';wav(fx,.3,amplitude=12000)
        p['sound_effects']=[{'id':'sound1','file':fx,'name':'Claxon de prueba','author':'Autor','license':'CC BY','source_url':'https://freesound.org/people/test/sounds/123/','license_url':'https://creativecommons.org/licenses/by/4.0/','duration':.3}]
        m.save(p)
    return m.get(pid)


def body(p,**extra):
    return dict(sound_id='sound1',segment_id=p['chapters'][0]['segments'][1]['id'],offset=.2,source_start=0,duration=.2,volume_db=-6,fade_in=0,fade_out=0,loop=False,active=True,**extra)


def create(p,**changes):
    b=body(p);b.update(changes)
    r=c.post(f'/api/projects/{p["id"]}/sound-mixer/cues',json=b)
    assert r.status_code==200,r.text
    return r.json()


def render(p):
    r=c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':p['chapters'][0]['segments'][0]['id']})
    assert r.status_code==202,r.text
    data=c.get(f'/api/projects/{p["id"]}/sound-mixer').json()
    result=next(x for x in data['mixes'] if x['id']==r.json()['id'])
    assert result['status']=='ready',result
    return result


def test_actual_mix_places_effect_at_anchor_and_preserves_sources():
    p=setup();create(p)
    before=copy.deepcopy(m.get(p['id']));hashes={n:hashlib.sha256((m.DATA/n).read_bytes()).hexdigest() for n in project_files(before) if (m.DATA/n).is_file()}
    result=render(p);assert not result['stale'] and result['exists']
    after=m.get(p['id']);assert after['chapters']==before['chapters'] and after['sound_effects']==before['sound_effects']
    assert all(hashlib.sha256((m.DATA/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    with wave.open(str(m.DATA/result['file'])) as w:
        assert w.getframerate()==48000 and w.getnchannels()==2
        assert abs(w.getnframes()/w.getframerate()-2)<.002
        samples=struct.unpack('<'+'h'*(w.getnframes()*2),w.readframes(w.getnframes()))
    def average(t):
        s=samples[round(t*48000)*2:round((t+.03)*48000)*2]
        return sum(abs(x) for x in s)/len(s)
    assert average(.3)<2 and average(1.1)<2 and average(1.3)>4000 and average(1.7)<2
    assert result['file'] in project_files(after)
    assert 'Claxon de prueba' in c.get(f'/api/projects/{p["id"]}/sound-mixer/mixes/{result["id"]}/credits').text
    assert c.get(f'/api/projects/{p["id"]}/sound-mixer/mixes/{result["id"]}/audio').status_code==200


def test_cue_edit_changes_only_metadata_and_marks_mix_stale():
    p=setup();cue=create(p);result=render(p)
    before=copy.deepcopy(m.get(p['id'])['chapters'])
    b=body(p);b['volume_db']=-20
    r=c.put(f'/api/projects/{p["id"]}/sound-mixer/cues/{cue["id"]}',json=b);assert r.status_code==200,r.text
    assert m.get(p['id'])['chapters']==before
    data=c.get(f'/api/projects/{p["id"]}/sound-mixer').json();assert data['mixes'][0]['stale']
    assert c.delete(f'/api/projects/{p["id"]}/sound-mixer/cues/{cue["id"]}').status_code==200
    assert len(m.get(p['id'])['sound_effects'])==1
    assert c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':result['scene_id']}).status_code==409


def test_missing_audio_exclusion_and_unapproved_audio_block_render():
    p=setup();create(p);pid=p['id'];first=p['chapters'][0]['segments'][0]
    with m.lock:
        current=m.get(pid);current['chapters'][0]['segments'][0]['versions']=[{'file':first['audio'],'status':'proposed'}];m.save(current)
    scene_id=first['id']
    assert c.post(f'/api/projects/{pid}/sound-mixer/mixes',json={'scene_id':scene_id}).status_code==409
    data=c.get(f'/api/projects/{pid}/sound-mixer').json();assert data['scenes'][0]['missing']==1
    with m.lock:
        current=m.get(pid);current['chapters'][0]['segments'][1]['excluded']=True;m.save(current)
    assert c.get(f'/api/projects/{pid}/sound-mixer').json()['cues'][0]['orphaned']


@pytest.mark.parametrize('changes',[{'sound_id':'another'},{'segment_id':'missing'},{'source_start':1},{'duration':1},{'fade_in':.2,'fade_out':.2},{'volume_db':5}])
def test_invalid_or_foreign_cues_rejected(changes):
    p=setup();b=body(p);b.update(changes)
    assert c.post(f'/api/projects/{p["id"]}/sound-mixer/cues',json=b).status_code in (404,422)
    assert not m.get(p['id']).get('sound_cues')


def test_loop_and_fades_render_and_bounds_checked():
    p=setup();create(p,duration=.7,loop=True,fade_in=.1,fade_out=.1)
    result=render(p);assert result['duration']==2
    with wave.open(str(m.DATA/result['file'])) as w:
        samples=struct.unpack('<'+'h'*(w.getnframes()*2),w.readframes(w.getnframes()))
    def level(t):
        values=samples[round(t*48000)*2:round((t+.005)*48000)*2]
        return sum(abs(v) for v in values)/len(values)
    assert level(1.5)>4000 and level(1.205)<1000 and level(1.89)<1000

    cue=m.get(p['id'])['sound_cues'][0];b=body(p);b.update(offset=.9,duration=.2)
    c.put(f'/api/projects/{p["id"]}/sound-mixer/cues/{cue["id"]}',json=b)
    assert c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':p['chapters'][0]['segments'][0]['id']}).status_code==409


def test_mix_rejects_offset_after_anchor_even_if_scene_has_time():
    p=setup();create(p,segment_id=p['chapters'][0]['segments'][0]['id'],offset=1.1)
    assert c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':p['chapters'][0]['segments'][0]['id']}).status_code==409


def test_global_busy_guard_and_worker_failure_release(monkeypatch):
    p=setup();create(p)
    mix.ACTIVE.acquire()
    try:assert c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':p['chapters'][0]['segments'][0]['id']}).status_code==409
    finally:mix.ACTIVE.release()
    def broken(*a):raise RuntimeError('private-path')
    monkeypatch.setattr(mix,'render_scene',broken)
    r=c.post(f'/api/projects/{p["id"]}/sound-mixer/mixes',json={'scene_id':p['chapters'][0]['segments'][0]['id']});assert r.status_code==202
    result=c.get(f'/api/projects/{p["id"]}/sound-mixer').json()['mixes'][0]
    assert result['status']=='error' and 'private-path' not in result['message']
    assert mix.ACTIVE.acquire(blocking=False);mix.ACTIVE.release()


def test_mix_ownership_deletion_and_restart_recovery():
    p=setup();create(p);result=render(p);pid=p['id']
    other=c.post('/api/projects',json={'title':'Otro'}).json()['id']
    assert c.get(f'/api/projects/{other}/sound-mixer/mixes/{result["id"]}/audio').status_code==404
    assert c.delete(f'/api/projects/{pid}/sound-mixer/mixes/{result["id"]}').status_code==200
    assert not (m.DATA/result['file']).exists() and m.get(pid)['sound_effects']
    with m.lock:
        current=m.get(pid);current['sound_mixes']=[{'id':'abandoned','scene_id':result['scene_id'],'status':'running'}];m.save(current)
    mix.recover_mixes();assert m.get(pid)['sound_mixes'][0]['status']=='error'


def test_overlapping_effects_limit_peaks_without_shortening_scene():
    p=setup()
    for _ in range(4):create(p,volume_db=0)
    result=render(p)
    with wave.open(str(m.DATA/result['file'])) as w:
        samples=struct.unpack('<'+'h'*(w.getnframes()*2),w.readframes(w.getnframes()))
        assert w.getnframes()==96000
    peak=max(abs(v) for v in samples)
    assert 20000<peak<=31131
