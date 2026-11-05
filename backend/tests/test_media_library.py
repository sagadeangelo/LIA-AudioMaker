import copy
from app import main as m
from app.media_library import voice_profiles
from app.project_cleanup import cleanup_files,project_files
from test_sound_mixer import setup,c

def test_adopt_classify_reuse_independent_storage_and_no_duplicate():
 p=setup();pid=p['id'];base='/api/media-library';before=copy.deepcopy(m.get(pid))
 body=dict(project_id=pid,sound_id='sound1',name='Lluvia de prueba',kind='effect',category='Clima / lluvia')
 r=c.post(base+'/adopt',json=body);assert r.status_code==200,r.text
 item=r.json();assert item['file']!=before['sound_effects'][0]['file'];assert (m.DATA/item['file']).is_file()
 assert c.post(base+'/adopt',json=body).json()['id']==item['id']
 assert m.get(pid)['chapters']==before['chapters']
 other=c.post('/api/projects',json={'title':'Destino'}).json()
 result=c.post(base+'/items/'+item['id']+'/use',json={'project_id':other['id']});assert result.status_code==200,result.text
 sound=result.json()['sound'];assert sound['file']!=item['file'] and sound['effect_category']=='Clima / lluvia'
 assert c.post(base+'/items/'+item['id']+'/use',json={'project_id':other['id']}).json()['already_saved']
 cleanup_files(m.DATA,project_files(m.get(pid)))
 assert (m.DATA/item['file']).is_file() and (m.DATA/sound['file']).is_file()
 assert c.get(base).json()['items']


def test_custom_music_category_and_voice_profiles_are_exportable():
 p=setup();body=dict(project_id=p['id'],sound_id='sound1',name='Mi música',kind='music',category='Thriller atmosférico')
 r=c.post('/api/media-library/adopt',json=body);assert r.status_code==200,r.text
 voice=dict(name='Santa narrador',kind='voice',voice_id='em_santa',gender='Hombre',age_group='Adulto',role='Narrador')
 assert c.post('/api/media-library/voices',json=voice).status_code==200
 assert voice_profiles({'em_santa'})[0]['gender']=='Hombre'
 from app.production_exchange import build_context
 context=build_context(m.get(p['id']))
 assert context['resources']['sounds'][0]['music_category']=='Thriller atmosférico'
 assert context['resources']['voice_profiles'][0]['voice_id']=='em_santa'


def test_foreign_sources_and_invalid_voice_do_not_create_files():
 p=setup();before=set(m.DATA.iterdir())
 r=c.post('/api/media-library/adopt',json=dict(project_id=p['id'],sound_id='foreign',name='No',kind='effect'));assert r.status_code==404
 assert c.post('/api/media-library/voices',json=dict(name='No',kind='voice',voice_id='unavailable')).status_code==422
 assert c.post('/api/media-library/items/absent/use',json={'project_id':p['id']}).status_code==404
 assert set(m.DATA.iterdir())==before

def test_classification_changes_reach_linked_project_catalog():
 p=setup();r=c.post('/api/media-library/adopt',json=dict(project_id=p['id'],sound_id='sound1',name='Efecto',kind='effect',category='Clima'));assert r.status_code==200
 item=r.json();r=c.put('/api/media-library/items/'+item['id'],json=dict(name='Lluvia',kind='effect',category='Lluvia intensa'));assert r.status_code==200,r.text
 assert r.json()['classification_saved'] is True
 assert next(i for i in c.get('/api/media-library').json()['items'] if i['id']==item['id'])['classification_saved'] is True
 sound=m.get(p['id'])['sound_effects'][0];assert sound['effect_category']=='Lluvia intensa' and sound['name']=='Lluvia'


def test_classified_voice_available_to_ai_before_character_assignment():
 p=setup();voice=dict(name='Narrador alternativo',kind='voice',voice_id='es-MX-CecilioNeural',gender='Hombre',age_group='Adulto',role='Narrador')
 assert c.post('/api/media-library/voices',json=voice).status_code==200
 from app.production_exchange import build_context
 context=build_context(m.get(p['id']))
 assert 'es-MX-CecilioNeural' in {v['id'] for v in context['resources']['voices']}
 assert 'es-MX-CecilioNeural' in {v['voice_id'] for v in context['resources']['voice_profiles']}


def test_sync_existing_downloads_idempotent_preserves_mix():
 p=setup();pid=p['id'];before=copy.deepcopy(m.get(pid)['chapters'])
 p=m.get(pid);sound=p['sound_effects'][0];sound.update(media_kind='music',music_category='Suspenso',author='sync music fixture');m.save(p)
 r=c.post('/api/media-library/sync');assert r.status_code==200,r.text
 items=c.get('/api/media-library').json()['items']
 item=next(i for i in items if i['id']==m.get(pid)['sound_effects'][0]['catalog_id'])
 assert item['kind']=='music' and item['category']=='Suspenso'
 assert m.get(pid)['chapters']==before
 assert c.post('/api/media-library/sync').json()['added']==0
 assert (m.DATA/sound['file']).is_file()


def test_upload_music_direct_to_catalog_without_project():
 import io,wave
 stream=io.BytesIO()
 with wave.open(stream,'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\x00\x00'*800)
 payload=stream.getvalue();data={'kind':'music','music_category':'Esperanza nueva','name':'Directa','origin':'own'}
 before=len(c.get('/api/projects').json())
 r=c.post('/api/media-library/uploads',data=data,files={'file':('direct.wav',payload,'audio/wav')});assert r.status_code==201,r.text
 item=r.json()['sound'];assert item['kind']=='music' and item['category']=='Esperanza nueva' and item['classification_saved']
 second=c.post('/api/media-library/uploads',data=data,files={'file':('direct.wav',payload,'audio/wav')});assert second.json()['already_saved']
 assert second.json()['sound']['id']==item['id']
 assert len(c.get('/api/projects').json())==before
 assert any(i['id']==item['id'] for i in c.get('/api/media-library').json()['items'])
