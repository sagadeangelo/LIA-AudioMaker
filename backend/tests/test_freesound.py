import copy
import hashlib
import io
import json
import time
import wave

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import main as m, freesound as fs
from app.project_cleanup import project_files

c = TestClient(m.app)


def raw(sid=123, **changes):
    return dict(id=sid, name='Olas del mar', username='Autor', url=f'https://freesound.org/people/Autor/sounds/{sid}/',
                license='https://creativecommons.org/publicdomain/zero/1.0/', duration=.1,
                previews={'preview-hq-mp3':'https://cdn.freesound.org/previews/0/123.mp3'}, filesize=10000, type='wav', **changes)


@pytest.fixture(autouse=True)
def connection(monkeypatch):
    monkeypatch.setenv('FREESOUND_CLIENT_ID', 'test-id')
    monkeypatch.setenv('FREESOUND_API_KEY', 'test-secret')
    monkeypatch.setattr(fs, 'token_path', lambda: m.DATA / 'private' / 'test-freesound.json')
    fs.token_path().unlink(missing_ok=True)
    fs._pending.clear();fs._cache.clear()
    yield
    fs.token_path().unlink(missing_ok=True)
    fs._pending.clear();fs._cache.clear()


def connect(monkeypatch):
    monkeypatch.setattr(fs, 'request_json', lambda *a, **k: {'access_token':'access-private','refresh_token':'refresh-private','expires_in':86400})
    start=c.post('/api/freesound/oauth/start').json()
    result=c.post('/api/freesound/oauth/finish', json={'code':'grant-code','state':start['state']})
    assert result.status_code == 200,result.text
    return start,result


def test_no_credentials_and_no_secrets_in_status(monkeypatch):
    monkeypatch.delenv('FREESOUND_API_KEY')
    assert c.get('/api/freesound/status').json()['configured'] is False
    assert c.get('/api/freesound/search',params={'q':'ocean'}).status_code==503
    monkeypatch.setenv('FREESOUND_API_KEY', 'private-value')
    assert 'private-value' not in c.get('/api/freesound/status').text


def test_search_cache_filters_and_preview_url_validation(monkeypatch):
    calls=[]
    def request(path,**kwargs):
        calls.append((path,kwargs))
        return {'count':2,'next':None,'results':[raw(),{**raw(456),'previews':{'preview-hq-mp3':'https://evil.test/audio.mp3'}}]}
    monkeypatch.setattr(fs,'request_json',request)
    result=c.get('/api/freesound/search',params={'q':'ocean waves'}); assert result.status_code==200,result.text
    data=result.json();assert data['results'][0]['license']=='CC0' and data['results'][1]['preview_url']==''
    c.get('/api/freesound/search',params={'q':'ocean waves'})
    assert len(calls)==1 and calls[0][0]=='search/'
    assert 'license:"Creative Commons 0"' in calls[0][1]['params']['filter']
    assert c.get('/api/freesound/search',params={'q':'x'}).status_code==422
    assert c.get('/api/freesound/search',params={'q':'ocean','license':'all'}).status_code==422
    assert c.get('/api/freesound/search',params={'q':'ocean','page':1000}).status_code==422


def test_oauth_persistence_replay_and_credentials_change(monkeypatch):
    start,result=connect(monkeypatch)
    assert result.json()['connected']
    assert all(s not in result.text for s in ['access-private','refresh-private','test-secret'])
    assert fs.token_path().parent.name=='private'
    assert fs.token_path().stat().st_mode & 0o777 == 0o600
    assert c.get('/api/audio/test-freesound.json').status_code==400
    assert c.post('/api/freesound/oauth/finish',json={'code':'grant-code','state':start['state']}).status_code==409
    monkeypatch.setenv('FREESOUND_API_KEY','different-key')
    assert not c.get('/api/freesound/status').json()['connected']


def test_oauth_expiry_and_disconnect(monkeypatch):
    start=c.post('/api/freesound/oauth/start').json()
    fs._pending[start['state']]=(time.time()-1,fs.namespace())
    assert c.post('/api/freesound/oauth/finish',json={'code':'x','state':start['state']}).status_code==409
    connect(monkeypatch)
    assert c.delete('/api/freesound/oauth').json()['connected'] is False
    assert not fs.token_path().exists()


def test_refresh_uses_new_refresh_token(monkeypatch):
    fs.store_grant({'access_token':'old','refresh_token':'old-refresh','expires_in':1})
    calls=[]
    def request(path,**kwargs):
        calls.append(kwargs['form'])
        return {'access_token':'new','refresh_token':'new-refresh','expires_in':86400}
    monkeypatch.setattr(fs,'request_json',request)
    assert fs.access_token()=='new'
    assert fs.read_token()['refresh_token']=='new-refresh'
    assert calls[0]['grant_type']=='refresh_token'
    assert fs.access_token()=='new' and len(calls)==1


def test_original_import_preserves_project_audio_deduplicates_and_cleanup(monkeypatch,fake_tts):
    connect(monkeypatch)
    p=c.post('/api/projects',json={'title':'Prueba de sonidos'}).json();pid=p['id']
    p=c.post(f'/api/projects/{pid}/manuscript',files={'file':('test.txt','CAPÍTULO I\nÁngelo miró el mar.'.encode())}).json()
    sid=p['chapters'][0]['segments'][0]['id'];c.post(f'/api/projects/{pid}/segments/{sid}/generate')
    before=copy.deepcopy(m.get(pid));name=before['chapters'][0]['segments'][0]['audio'];digest=hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()
    monkeypatch.setattr(fs,'request_json',lambda *a,**k:raw())
    def download(sid,target,token):
        assert token=='access-private'
        # Simulate a concurrent edit while the download is in flight.
        with m.lock:
            current=m.get(pid);current['title']='Edición concurrente';m.save(current)
        with wave.open(str(target),'wb') as w:
            w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x00\x00'*2400)
    monkeypatch.setattr(fs,'download_original',download)
    res=c.post(f'/api/projects/{pid}/sound-effects/freesound',json={'sound_id':123});assert res.status_code==200,res.text
    item=res.json()['sound'];after=m.get(pid)
    assert after['title']=='Edición concurrente'
    assert after['chapters']==before['chapters'] and after['characters']==before['characters']
    assert hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()==digest
    assert item['author']=='Autor' and item['license']=='CC0' and item['duration']==.1
    with wave.open(str(m.DATA/item['file'])) as w:assert w.getframerate()==48000 and w.getnchannels()==2
    assert c.get('/api/audio/'+item['file']).status_code==200
    assert item['file'] in project_files(after)
    repeat=c.post(f'/api/projects/{pid}/sound-effects/freesound',json={'sound_id':123}).json()
    assert repeat['already_saved'] and len(m.get(pid)['sound_effects'])==1
    other=c.post('/api/projects',json={'title':'Otro'}).json()
    assert c.get(f'/api/projects/{other["id"]}/sound-effects').json()['sounds']==[]
    assert c.get('/api/projects/missing/sound-effects').status_code==404


def test_import_requires_oauth_and_supported_license(monkeypatch):
    pid=c.post('/api/projects',json={'title':'Permisos'}).json()['id']
    monkeypatch.setattr(fs,'request_json',lambda *a,**k:raw())
    assert c.post(f'/api/projects/{pid}/sound-effects/freesound',json={'sound_id':123}).status_code==409
    monkeypatch.setattr(fs,'request_json',lambda *a,**k:{**raw(),'license':'https://creativecommons.org/licenses/by-nc/4.0/'})
    assert c.post(f'/api/projects/{pid}/sound-effects/freesound',json={'sound_id':123}).status_code==422
    assert fs.license_name('https://evil.test/licenses/by/4.0/')=='No admitida'


def test_failed_decode_leaves_no_sound_or_orphan_file(monkeypatch):
    connect(monkeypatch)
    pid=c.post('/api/projects',json={'title':'Audio inválido'}).json()['id']
    monkeypatch.setattr(fs,'request_json',lambda *a,**k:raw())
    monkeypatch.setattr(fs,'download_original',lambda sid,target,token:target.write_bytes(b'not audio'))
    before=set(m.DATA.glob('sfx_*.wav'))
    assert c.post(f'/api/projects/{pid}/sound-effects/freesound',json={'sound_id':123}).status_code==422
    assert set(m.DATA.glob('sfx_*.wav'))==before and not m.get(pid).get('sound_effects')


def test_download_redirects_strip_auth_and_reject_untrusted(monkeypatch,tmp_path):
    seen=[]
    def handle(req):
        seen.append(req)
        if req.url.host=='freesound.org':return httpx.Response(302,headers={'location':'https://cdn.freesound.org/original.wav'})
        return httpx.Response(200,content=b'wav-bytes')
    original_client=httpx.Client
    monkeypatch.setattr(fs.httpx,'Client',lambda **kw:original_client(transport=httpx.MockTransport(handle),**kw))
    target=tmp_path/'file';fs.download_original(123,target,'secret')
    assert target.read_bytes()==b'wav-bytes'
    assert seen[0].headers['Authorization']=='Bearer secret' and 'Authorization' not in seen[1].headers
    def evil(req):return httpx.Response(302,headers={'location':'http://localhost/private'})
    monkeypatch.setattr(fs.httpx,'Client',lambda **kw:original_client(transport=httpx.MockTransport(evil),**kw))
    with pytest.raises(HTTPException) as exc:fs.download_original(123,target,'secret')
    assert exc.value.status_code==502


def test_download_size_limit_and_errors_sanitized(monkeypatch,tmp_path):
    original_client=httpx.Client
    monkeypatch.setattr(fs,'MAX_BYTES',3)
    monkeypatch.setattr(fs.httpx,'Client',lambda **kw:original_client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'toolong')),**kw))
    with pytest.raises(HTTPException) as exc:fs.download_original(123,tmp_path/'file','secret')
    assert exc.value.status_code==413
    monkeypatch.setattr(fs.httpx,'Client',lambda **kw:original_client(transport=httpx.MockTransport(lambda r:httpx.Response(401,json={'detail':'test-secret'})),**kw))
    with pytest.raises(HTTPException) as exc:fs.request_json('search/')
    assert 'test-secret' not in exc.value.detail
