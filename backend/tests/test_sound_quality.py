import copy
import json
import subprocess
from fastapi.testclient import TestClient
from app import main as m, sound_playback as playback, sound_mixer as sm
from app.project_cleanup import project_files
from test_sound_playback import ready

c=TestClient(m.app)


def test_three_real_mp3_encodings_original_download_estimates_and_cleanup():
    p,root,item=ready();url=root+'/'+item['id'];before=copy.deepcopy(m.get(p['id']))
    opts=c.get(root).json()['mixes'][0]['export_options']
    assert [o['id'] for o in opts]==['light','balanced','high','original']
    assert [o['estimated_bytes'] for o in opts[:3]]==[24000,32000,48000]
    assert opts[3]['ready'] and opts[3]['actual_bytes']>0
    paths=[];sizes=[]
    for quality,expected in [('light',96000),('balanced',128000),('high',192000)]:
        r=c.post(url+'/prepare-mp3?quality='+quality);assert r.status_code==202,r.text
        state=c.get(root).json()['mixes'][0];opt=next(o for o in state['export_options'] if o['id']==quality)
        assert opt['ready'] and opt['actual_bytes']>0
        saved=m.get(p['id']);v=playback.variant(saved['sound_project_mixes'][0],quality);path=m.DATA/v['file'];paths.append(path);sizes.append(path.stat().st_size)
        probe=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],capture_output=True,check=True)
        stream=json.loads(probe.stdout)['streams'][0]
        assert stream['codec_name']=='mp3' and int(stream['bit_rate'])==expected
        assert c.get(url+'/audio?format=mp3&quality='+quality,headers={'Range':'bytes=0-63'}).status_code==206
        download=c.get(url+'/audio?format=mp3&download=true&quality='+quality)
        assert download.status_code==200 and quality in download.headers['content-disposition']
        assert c.post(url+'/prepare-mp3?quality='+quality).json()['already_ready']
        assert v['file'] in project_files(saved)
    assert len(set(paths))==3 and sizes[0]<sizes[1]<sizes[2]
    assert m.get(p['id'])['chapters']==before['chapters'] and m.get(p['id'])['sound_cues']==before['sound_cues']
    assert c.get(url+'/audio?format=wav&download=true').status_code==200
    assert c.delete(url).status_code==200
    assert all(not path.exists() for path in paths)


def test_profiles_reject_arbitrary_bitrates_and_recover_interrupted_quality():
    p,root,item=ready();url=root+'/'+item['id'];before=copy.deepcopy(m.get(p['id']))
    assert c.post(url+'/prepare-mp3?quality=999999').status_code==422
    assert c.get(url+'/audio?format=mp3&quality=unknown').status_code==422
    assert c.get(url+'/audio?format=mp3&quality=high').status_code==409
    assert m.get(p['id'])==before
    with m.lock:
        value=m.get(p['id']);value['sound_project_mixes'][0]['mp3_profiles']={'high':{'status':'running'}};m.save(value)
    assert c.delete(url).status_code==409
    sm.recover_mixes()
    mix=c.get(root).json()['mixes'][0];high=next(o for o in mix['export_options'] if o['id']=='high')
    assert high['status']=='error' and mix['exists']
    assert c.post(url+'/prepare-mp3?quality=high').status_code==202


def test_existing_066_balanced_file_remains_available_without_conversion(monkeypatch):
    p,root,item=ready();url=root+'/'+item['id']
    assert c.post(url+'/prepare-mp3').status_code==202
    before=copy.deepcopy(m.get(p['id']))
    def fail(*args,**kwargs):raise AssertionError('Do not reconvert existing legacy balanced file')
    monkeypatch.setattr(playback.subprocess,'run',fail)
    r=c.post(url+'/prepare-mp3?quality=balanced');assert r.json()['already_ready']
    state=c.get(root).json()['mixes'][0]
    balanced=next(o for o in state['export_options'] if o['id']=='balanced')
    assert balanced['ready'] and balanced['actual_bytes']==state['mp3_bytes']
    assert m.get(p['id'])==before
