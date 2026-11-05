import copy
import hashlib
import wave
from fastapi.testclient import TestClient
from app import main as m
from app import sound_mixer as sm
from app.project_cleanup import project_files
from test_sound_checklist import fixture

c=TestClient(m.app)


def link_all(p):
    base=f'/api/projects/{p["id"]}/sound-checklist'
    items=c.get(base).json()['items']
    for g in items:assert c.put(base+'/'+g['id'],json={'sound_id':'sound1'}).status_code==200
    return base,items


def test_dismiss_before_download_restore_and_remove_resource():
    p=fixture();base=f'/api/projects/{p["id"]}/sound-checklist'
    items=c.get(base).json()['items'];g=items[0]
    assert c.patch(base+'/'+g['id']+'/selection',json={'dismissed':True}).json()['pending']==1
    assert c.get(base).json()['dismissed']==1
    assert c.patch(base+'/'+g['id']+'/selection',json={'dismissed':False}).json()['pending']==2
    assert c.put(base+'/'+g['id'],json={'sound_id':'sound1'}).status_code==200
    source=m.DATA/p['sound_effects'][0]['file']
    assert c.delete(base+'/library/sound1').status_code==200
    assert source.exists() and c.get(base).json()['pending']==2
    assert m.get(p['id'])['chapters']==p['chapters']


def test_actual_book_mix_reuses_narration_idempotent_and_dismiss_updates():
    p=fixture();base,items=link_all(p);root=base+'/project-mixes'
    before=copy.deepcopy(m.get(p['id']))
    hashes={n:hashlib.sha256((m.DATA/n).read_bytes()).hexdigest() for n in project_files(before)}
    response=c.post(root);assert response.status_code==202,response.text
    data=c.get(root).json()['mixes'];assert len(data)==1 and data[0]['status']=='ready',data
    item=data[0];assert item['placements']==3 and not item['stale']
    after=m.get(p['id']);assert after['chapters']==before['chapters']
    for n,digest in hashes.items():assert hashlib.sha256((m.DATA/n).read_bytes()).hexdigest()==digest
    with wave.open(str(m.DATA/after['sound_project_mixes'][0]['file'])) as w:
        assert w.getnframes()/w.getframerate()==2
        assert any(w.readframes(w.getnframes()))
    assert c.get(root+'/'+item['id']+'/audio').status_code==200
    assert 'Autor' in c.get(root+'/'+item['id']+'/credits').text
    assert c.post(root).json()['id']==item['id']
    assert not sm.ACTIVE.locked()
    sea=next(g for g in items if g['query']=='ocean waves')
    assert c.patch(base+'/'+sea['id']+'/selection',json={'dismissed':True}).status_code==200
    assert not any(x.get('recommendation_id')==sea['id'] for x in m.get(p['id'])['sound_cues'])
    assert c.get(root).json()['mixes'][0]['stale']
    r=c.post(root);assert r.status_code==202,r.text
    latest=c.get(root).json()['mixes'][0];assert latest['placements']==1 and latest['status']=='ready'
    assert c.delete(root+'/'+item['id']).status_code==200
    assert all((m.DATA/n).exists() for n in hashes)


def test_missing_audio_rejects_atomically_and_missing_resources_reported():
    p=fixture();base,items=link_all(p);root=base+'/project-mixes'
    segment=p['chapters'][0]['segments'][0];(m.DATA/segment['audio']).unlink()
    before=copy.deepcopy(m.get(p['id']))
    assert c.post(root).status_code==409
    assert m.get(p['id'])==before and not sm.ACTIVE.locked()


def test_partial_available_explicit_skipped_report_and_manual_preserved():
    p=fixture();base=f'/api/projects/{p["id"]}/sound-checklist';items=c.get(base).json()['items']
    assert c.put(base+'/'+items[0]['id'],json={'sound_id':'sound1'}).status_code==200
    from test_sound_mixer import create
    manual=create(p)
    r=c.post(base+'/project-mixes');assert r.status_code==202,r.text
    result=c.get(base+'/project-mixes').json()['mixes'][0]
    assert result['status']=='ready' and len(result['skipped'])==1
    assert any(x==manual for x in m.get(p['id'])['sound_cues'])
    assert c.delete(base+'/library/sound1').status_code==200
    assert not m.get(p['id'])['sound_cues']
    assert c.get(base+'/project-mixes').json()['mixes'][0]['stale']


def test_fast_download_refresh_skips_full_book_fingerprint(monkeypatch):
 from app import sound_project
 p=fixture();base,_=link_all(p);root=base+'/project-mixes'
 assert c.post(root).status_code==202
 def expensive(*args,**kwargs):raise AssertionError('Fast refresh must not rescan the book')
 monkeypatch.setattr(sound_project,'signature',expensive)
 response=c.get(root+'?fast=true');assert response.status_code==200,response.text
 assert response.headers['cache-control']=='no-store'
 mix=response.json()['mixes'][0]
 assert mix['exists'] and mix['export_options'] and mix['stale_checked'] is False
 assert mix['stale'] is None
