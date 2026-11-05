import copy
import hashlib
import subprocess
from fastapi.testclient import TestClient
from app import main as m, sound_mixer as sm, sound_playback as playback
from app.project_cleanup import project_files
from test_sound_checklist import fixture
from test_sound_project import link_all

c=TestClient(m.app)


def ready(legacy=False):
    p=fixture();base,_=link_all(p);root=base+'/project-mixes'
    assert c.post(root).status_code==202
    item=c.get(root).json()['mixes'][0]
    assert item['status']=='ready'
    if legacy:
        current=m.get(p['id']);mix=current['sound_project_mixes'][0]
        playback.file_for(mix,'mp3_file').unlink()
        for key in list(mix):
            if key.startswith('mp3_'):mix.pop(key)
        m.save(current);item=c.get(root).json()['mixes'][0]
    return p,root,item


def test_existing_wav_to_mp3_inline_download_range_and_credits_unchanged():
    p,root,item=ready(legacy=True);pid=p['id'];url=root+'/'+item['id']
    before=copy.deepcopy(m.get(pid));wav=playback.file_for(before['sound_project_mixes'][0],'file')
    digest=hashlib.sha256(wav.read_bytes()).hexdigest()
    assert c.get(url+'/audio?format=mp3').status_code==409
    response=c.post(url+'/prepare-mp3');assert response.status_code==202,response.text
    status=c.get(root).json()['mixes'][0]
    assert status['mp3_status']=='ready' and status['mp3_exists'] and status['mp3_bytes']>0
    inline=c.get(url+'/audio?format=mp3',headers={'Range':'bytes=0-63'})
    assert inline.status_code==206 and len(inline.content)==64
    assert inline.headers['content-type']=='audio/mpeg'
    assert inline.headers['content-disposition'].startswith('inline;')
    download=c.get(url+'/audio?format=mp3&download=true')
    assert download.status_code==200 and download.headers['content-disposition'].startswith('attachment;')
    assert c.get(url+'/audio?format=wav&download=true').headers['content-disposition'].startswith('attachment;')
    assert hashlib.sha256(wav.read_bytes()).hexdigest()==digest
    after=m.get(pid);assert after['chapters']==before['chapters'] and after['sound_cues']==before['sound_cues']
    assert after['sound_project_mixes'][0]['credits']==before['sound_project_mixes'][0]['credits']
    assert after['sound_project_mixes'][0]['mp3_file'] in project_files(after)
    assert c.post(url+'/prepare-mp3').json()['already_ready']
    assert not sm.ACTIVE.locked()
    mp3=playback.file_for(after['sound_project_mixes'][0],'mp3_file')
    assert c.delete(url).status_code==200
    assert not wav.exists() and not mp3.exists()
    assert all((m.DATA/s['audio']).exists() for ch in before['chapters'] for s in ch['segments'])


def test_conversion_failure_keeps_existing_mix_and_allows_retry(monkeypatch):
    p,root,item=ready(legacy=True);url=root+'/'+item['id'];before=copy.deepcopy(m.get(p['id']))
    files=set(m.DATA.glob('book_fx_browser_*'))
    def fail(*args,**kwargs):raise subprocess.CalledProcessError(1,args[0])
    monkeypatch.setattr(playback.subprocess,'run',fail)
    assert c.post(url+'/prepare-mp3').status_code==202
    after=c.get(root).json()['mixes'][0]
    assert after['status']=='ready' and after['exists'] and after['mp3_status']=='error'
    assert m.get(p['id'])['chapters']==before['chapters'] and not sm.ACTIVE.locked()
    assert files==set(m.DATA.glob('book_fx_browser_*'))
    assert c.get(url+'/audio').status_code==200


def test_restart_marks_conversion_interrupted_without_invalidating_wav():
    p,root,item=ready()
    with m.lock:
        value=m.get(p['id']);value['sound_project_mixes'][0]['mp3_status']='running';m.save(value)
    sm.recover_mixes()
    result=c.get(root).json()['mixes'][0]
    assert result['status']=='ready' and result['exists'] and result['mp3_status']=='error'


def test_large_wav_range_above_two_gib_does_not_overflow():
    p,root,item=ready();url=root+'/'+item['id']
    value=m.get(p['id']);path=m.DATA/value['sound_project_mixes'][0]['file']
    size=3068398402
    try:
        with path.open('r+b') as f:f.truncate(size)
        result=c.get(url+'/audio?format=wav&download=true',headers={'Range':f'bytes={size-64}-{size-1}'})
        assert result.status_code==206 and len(result.content)==64
        assert result.headers['content-range']==f'bytes {size-64}-{size-1}/{size}'
    finally:path.unlink(missing_ok=True)


def test_conversion_progress_estimate_and_ready_reuse():
 from app.sound_playback import options
 import uuid
 name='progress_'+uuid.uuid4().hex+'.mp3'
 path=m.DATA/name;path.write_bytes(b'x'*8000)
 item={'status':'ready','duration':1,'mp3_status':'running','mp3_working_file':name}
 balanced=next(o for o in options(item) if o['id']=='balanced')
 assert balanced['progress_percent']==50 and not balanced['ready']
 item.update(mp3_status='ready',mp3_file=name,mp3_working_file=None)
 balanced=next(o for o in options(item) if o['id']=='balanced')
 assert balanced['ready'] and balanced['progress_percent']==100


def test_new_mix_has_balanced_copy_without_another_prepare_request():
 p,root,item=ready()
 assert item['mp3_status']=='ready' and item['mp3_bytes']>0
 assert c.post(root+'/'+item['id']+'/prepare-mp3').json()['already_ready']
 assert not sm.ACTIVE.locked()


def test_conversion_time_estimate_uses_elapsed_and_written_bytes():
 from datetime import datetime,timezone,timedelta
 current=datetime.now(timezone.utc)
 v={'status':'running','encoding_started_at':(current-timedelta(seconds=20)).isoformat()}
 estimate=playback.conversion_time_estimate(v,10000,2500,current)
 assert estimate['estimated_total_seconds']==80 and estimate['estimated_remaining_seconds']==60
 assert playback.conversion_time_estimate(v,10000,0,current)=={}
 assert playback.conversion_time_estimate({'status':'running'},10000,2500,current)=={}
 assert playback.conversion_time_estimate({'status':'queued'},10000,2500,current)=={}
 assert playback.conversion_time_estimate({'status':'ready'},10000,10000,current)['estimated_remaining_seconds']==0
