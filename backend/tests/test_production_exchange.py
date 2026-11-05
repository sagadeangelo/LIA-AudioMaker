import copy,io,json,zipfile
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import main as m
from app.production_exchange import ProductionPlan,build_context
from test_editorial_plan import setup
c=TestClient(m.app)
def unpack(response):
    assert response.status_code==200,response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:return {name:z.read(name).decode() for name in z.namelist()}

def test_export_full_text_scopes_and_no_mutation_or_credentials():
    p,_=setup()
    with m.lock:
        p=m.get(p['id']);p['chapters'][0]['segments'][0]['text']='Texto íntegro '+('palabras extensas '*60)
        p['sound_effects']=[{'id':'fx','name':'Lluvia','media_kind':'effect','file':'private.wav','token':'secret-token','original_filename':'private.mp3','license':'CC0'}]
        p['credentials']={'api_key':'do-not-export'};m.save(p)
    before=copy.deepcopy(m.get(p['id']))
    files=unpack(c.get(f'/api/projects/{p["id"]}/production-exchange/export'))
    context=json.loads(files['contexto.json']);template=json.loads(files['plantilla_produccion.json'])
    assert context['scenes'][0]['segments'][0]['text']==before['chapters'][0]['segments'][0]['text']
    assert all(word not in files['contexto.json'] for word in ('private.wav','secret-token','do-not-export','private.mp3'))
    assert ProductionPlan.model_validate(template).scenes[0].decision=='pending'
    assert 'additionalProperties' in files['esquema_produccion.json']
    assert json.loads(files['esquema_editorial_actual.json'])['properties']['format']['const']=='lia.editorial-plan'
    assert m.get(p['id'])==before
    scope=context['scenes'][0]['id']
    selected=json.loads(unpack(c.get(f'/api/projects/{p["id"]}/production-exchange/export',params={'scene_id':scope}))['contexto.json'])
    assert selected['scope_scene_ids']==[scope] and len(selected['scenes'])==1
    assert c.get(f'/api/projects/{p["id"]}/production-exchange/export',params={'scene_id':'unknown'}).status_code==409
    assert c.get('/api/projects/missing/production-exchange/export').status_code==404

def test_tokens_change_with_manuscript_and_resources_and_excluded_segments_omitted():
    p,_=setup();p=m.get(p['id']);first=build_context(p)
    q=copy.deepcopy(p);q['chapters'][0]['segments'][0]['text']+=' cambiado'
    assert build_context(q)['document_token']!=first['document_token']
    q=copy.deepcopy(p);q['sound_effects']=[{'id':'new','name':'Nueva pista','music_category':'Drama'}]
    assert build_context(q)['resources_token']!=first['resources_token']
    q=copy.deepcopy(p);seg=q['chapters'][0]['segments'][0];seg['excluded']=True
    assert seg['id'] not in {x['id'] for s in build_context(q)['scenes'] for x in s['segments']}

def test_production_format_not_accepted_as_editorial_and_schema_rejects_commands():
    p,_=setup();files=unpack(c.get(f'/api/projects/{p["id"]}/production-exchange/export'));plan=json.loads(files['plantilla_produccion.json'])
    assert c.post(f'/api/projects/{p["id"]}/analysis/editorial/preview',json={'plan':plan}).status_code==422
    plan['command']='run something'
    with pytest.raises(ValidationError):ProductionPlan.model_validate(plan)
