import copy
import io
import subprocess
import wave
from fastapi.testclient import TestClient
from app import main as m, sound_upload as upload
from test_sound_checklist import fixture

c=TestClient(m.app)


def wav_bytes():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as w:
        w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\x20'*2400)
    return stream.getvalue()


def post(pid,**data):
    filename=data.pop('filename','grabacion.wav');content=data.pop('content',wav_bytes())
    return c.post(f'/api/projects/{pid}/sound-checklist/uploads',files={'file':(filename,content,'application/octet-stream')},data=data)


def test_upload_and_auto_link_without_freesound_credentials_preserves_narration(monkeypatch):
    monkeypatch.delenv('FREESOUND_API_KEY',raising=False)
    p=fixture();pid=p['id'];before=copy.deepcopy(p)
    base=f'/api/projects/{pid}/sound-checklist';group=c.get(base).json()['items'][0]
    response=post(pid,gid=group['id'],name='Pasos propios',author='Miguel');assert response.status_code==201,response.text
    sound=response.json()['sound'];assert sound['source']=='upload' and sound['author']=='Miguel'
    assert sound['license']=='Grabación propia' and 'freesound_id' not in sound
    assert sound['duration']==.1 and response.json()['linked']
    with wave.open(str(m.DATA/sound['file'])) as w:assert w.getframerate()==48000 and w.getnchannels()==2
    assert m.get(pid)['chapters']==before['chapters']
    current=next(g for g in c.get(base).json()['items'] if g['id']==group['id'])
    assert current['completed'] and current['sound_id']==sound['id']
    assert post(pid,gid=group['id'],name='Pasos propios',author='Miguel').json()['already_saved']
    assert len(m.get(pid)['sound_effects'])==2
    assert c.post(base+'/project-mixes').status_code==202
    mix=c.get(base+'/project-mixes').json()['mixes'][0]
    assert mix['status']=='ready'
    assert 'Miguel' in c.get(base+'/project-mixes/'+mix['id']+'/credits').text


def test_mp3_external_resource_import_and_credit(tmp_path):
    p=fixture();source=tmp_path/'in.wav';source.write_bytes(wav_bytes());target=tmp_path/'out.mp3'
    subprocess.run(['ffmpeg','-v','error','-i',str(source),str(target)],check=True)
    bad=post(p['id'],filename='efecto.mp3',content=target.read_bytes(),origin='external')
    assert bad.status_code==422
    result=post(p['id'],filename='efecto.mp3',content=target.read_bytes(),origin='external',license_note='CC BY 4.0',author='Autor externo')
    assert result.status_code==201,result.text
    assert result.json()['sound']['license']=='CC BY 4.0' and not result.json()['linked']


def test_invalid_uploads_are_atomic_and_outputs_cleaned(monkeypatch):
    p=fixture();pid=p['id'];before=copy.deepcopy(p);files=set(m.DATA.glob('sfx_user_*'))
    assert post(pid,filename='a.exe').status_code==422
    assert post(pid,content=b'').status_code==422
    assert post(pid,content=b'not audio').status_code==422
    assert post(pid,gid='not-a-recommendation').status_code==409
    monkeypatch.setattr(upload,'MAX_BYTES',5)
    assert post(pid).status_code==413
    monkeypatch.setattr(upload,'MAX_BYTES',1024*1024)
    monkeypatch.setattr(upload,'MAX_SECONDS',.01)
    assert post(pid).status_code==422
    assert set(m.DATA.glob('sfx_user_*'))==files and m.get(pid)==before


def test_dismissed_recommendation_and_cross_project_link_rejected():
    p=fixture();other=fixture();base=f'/api/projects/{p["id"]}/sound-checklist'
    g=c.get(base).json()['items'][0]
    assert c.patch(base+'/'+g['id']+'/selection',json={'dismissed':True}).status_code==200
    assert post(p['id'],gid=g['id']).status_code==409
    resource=post(other['id']).json()['sound']
    assert c.put(base+'/'+g['id'],json={'sound_id':resource['id']}).status_code==409


def test_playlist_masquerading_as_audio_is_rejected(tmp_path):
    p=fixture();source=m.DATA/p['sound_effects'][0]['file']
    playlist=("ffconcat version 1.0\nfile '"+str(source)+"'\n").encode()
    assert post(p['id'],content=playlist).status_code==422
