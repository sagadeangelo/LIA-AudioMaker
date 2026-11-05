import copy
import hashlib
import io
import json
import wave
import zipfile
from fastapi.testclient import TestClient
from app import main as m, sound_mixer as sm
from app.project_cleanup import project_files
from test_sound_checklist import fixture
from test_sound_project import link_all

c=TestClient(m.app)


def setup():
    p=fixture();pid=p['id']
    with m.lock:
        p=m.get(pid);p['chapters'][0]['segments'][1]['scene']=2;m.save(p)
    base,_=link_all(p);root=base+'/scene-review'
    assert c.post(root+'/prepare').status_code==200
    return pid,base,root,c.get(root).json()['scenes']


def audition(root,s):
    r=c.post(root+'/'+s['id']+'/preview');assert r.status_code==202,r.text
    row=next(x for x in c.get(root).json()['scenes'] if x['id']==s['id'])
    assert row['preview']['status']=='ready',row
    assert c.put(root+'/'+s['id']+'/approval',json={'preview_id':row['preview']['id']}).status_code==200
    return row


def selection(rows):
    return {'scene_ids':[s['id'] for s in rows],'preview_ids':{s['id']:s['preview']['id'] for s in rows}}


def samples(path):
    with wave.open(str(path),'rb') as w:return w.readframes(w.getnframes())


def test_review_two_scenes_zip_and_join_exact_listened_audio_in_book_order():
    pid,base,root,scenes=setup();before=copy.deepcopy(m.get(pid))
    hashes={f:hashlib.sha256((m.DATA/f).read_bytes()).hexdigest() for f in project_files(before)}
    heard=[audition(root,s) for s in scenes];state=c.get(root).json();assert state['approved']==2
    preview_files=[m.DATA/s['preview']['file'] for s in heard]
    assert any(samples(preview_files[0])) # real SFX mixed into silence fixture
    body=selection(list(reversed(heard)))
    z=c.post(root+'/export/zip',json=body);assert z.status_code==202,z.text
    export=c.get(root).json()['exports'][0];assert export['status']=='ready'
    download=c.get(root+'/exports/'+export['id']+'/download');assert download.status_code==200
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        entries=json.loads(archive.read('escenas.json'));assert [s['scene_id'] for s in entries]==[s['id'] for s in scenes]
        names=[n for n in archive.namelist() if n.endswith('.wav')]
        assert archive.read(names[0])==preview_files[0].read_bytes()
        assert 'Autor' in archive.read('creditos.txt').decode()
    book=c.post(root+'/export/book',json=body);assert book.status_code==202,book.text
    output=c.get(base+'/project-mixes').json()['mixes'][0]
    assert output['status']=='ready' and output['is_complete_book'] and not output['stale']
    saved=m.get(pid)['sound_project_mixes'][0]
    assert samples(m.DATA/saved['file'])==b''.join(samples(path) for path in preview_files)
    assert c.get(base+'/project-mixes/'+saved['id']+'/audio?download=true').status_code==200
    assert m.get(pid)['chapters']==before['chapters']
    for f,digest in hashes.items():assert hashlib.sha256((m.DATA/f).read_bytes()).hexdigest()==digest
    assert set(s['preview']['file'] for s in heard)<=project_files(m.get(pid))
    assert c.delete(root+'/exports/'+export['id']).status_code==200
    assert all(path.exists() for path in preview_files)


def test_unreviewed_changed_or_unseen_preview_rejected_and_regeneration_requires_review():
    pid,base,root,scenes=setup();first=audition(root,scenes[0])
    assert c.post(root+'/export/book',json={'scene_ids':[scenes[1]['id']],'preview_ids':{}}).status_code==409
    assert c.post(root+'/export/zip',json={'scene_ids':[first['id']],'preview_ids':{first['id']:'wrong'}}).status_code==409
    oldfile=m.DATA/first['preview']['file']
    assert c.post(root+'/'+first['id']+'/preview').json()['id']==first['preview']['id']
    with m.lock:
        p=m.get(pid);cue=next(x for x in p['sound_cues'] if x['segment_id']==first['id']);cue['volume_db']=-6;m.save(p)
    rows=c.get(root).json()['scenes'];changed=next(s for s in rows if s['id']==first['id'])
    assert not changed['approved'] and changed['preview']['stale']
    assert c.get(root+'/'+first['id']+'/audio').status_code==409
    assert c.post(root+'/export/book',json=selection([first])).status_code==409
    renewed=audition(root,scenes[0]);assert renewed['preview']['id']!=first['preview']['id']
    assert oldfile.exists() and oldfile.name in project_files(m.get(pid))
    assert c.put(root+'/'+first['id']+'/approval',json={'preview_id':first['preview']['id']}).status_code==409
    assert not sm.ACTIVE.locked()


def test_subset_export_is_explicit_not_complete_book_and_estimate_uses_subset():
    pid,base,root,scenes=setup();heard=audition(root,scenes[1])
    r=c.post(root+'/export/book',json=selection([heard]));assert r.status_code==202,r.text
    output=c.get(base+'/project-mixes').json()['mixes'][0]
    assert not output['is_complete_book'] and output['scene_ids']==[heard['id']]
    assert output['duration']==heard['duration']==1
    assert output['export_options'][0]['estimated_bytes']==12000
    assert c.post(root+'/export/book',json={'scene_ids':[heard['id'],heard['id']],'preview_ids':{heard['id']:heard['preview']['id']}}).status_code==422


def test_plain_scene_preview_and_restart_recovery():
    pid,base,root,scenes=setup()
    with m.lock:
        p=m.get(pid);p['sound_cues']=[x for x in p['sound_cues'] if x['segment_id']!=scenes[0]['id']];m.save(p)
    heard=audition(root,scenes[0]);assert heard['cue_count']==0
    with m.lock:
        p=m.get(pid);p['sound_scene_previews'][scenes[0]['id']]['status']='running'
        p['sound_scene_exports']=[{'id':'interrupted','status':'queued','sources':{}}];m.save(p)
    sm.recover_mixes();p=m.get(pid)
    assert p['sound_scene_previews'][scenes[0]['id']]['status']=='error'
    assert p['sound_scene_exports'][0]['status']=='error'
