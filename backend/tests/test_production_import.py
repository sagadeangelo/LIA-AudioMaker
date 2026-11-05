import copy,json,io,zipfile
from fastapi.testclient import TestClient
from app import main as m
from app.production_exchange import build_context
from test_editorial_plan import setup
c=TestClient(m.app)
def fixture():
 p,_=setup();p=m.get(p['id']);ctx=build_context(p);scene=ctx['scenes'][0];seg=scene['segments'][0]
 # Export one scene to obtain the actual per-scope resources token.
 ctx=build_context(p,scene['id'])
 plan={'format':'lia.production-plan','version':1,'project_id':p['id'],'document_token':ctx['document_token'],'resources_token':ctx['resources_token'],'scope_scene_ids':[scene['id']],'scenes':[{'scene_id':scene['id'],'decision':'sound_design','performances':[{'segment_id':seg['id'],'quote':seg['text'],'character_id':None,'voice_id':None}],'effects':[],'music':[],'questions':[{'segment_id':seg['id'],'question':'Revisar voz'}]}],'notes':['Conservar asignaciones existentes.']}
 return p,plan,f'/api/projects/{p["id"]}/production-exchange'
def preview(base,plan):
 r=c.post(base+'/preview',json={'plan':plan});assert r.status_code==200,r.text
 return r.json()
def test_preview_save_reload_duplicate_preserve_project_fields():
 p,plan,base=fixture();before=copy.deepcopy(m.get(p['id']));pr=preview(base,plan)
 assert pr['valid'] and pr['can_save'] and pr['counts']['questions']==1 and pr['warnings']
 assert m.get(p['id'])==before
 body={'plan':plan,'preview_token':pr['preview_token'],'confirmed':True}
 r=c.post(base+'/plans',json=body);assert r.status_code==201,r.text
 rid=r.json()['id'];saved=TestClient(m.app).get(base+'/plans/'+rid).json()
 assert saved['plan']['scenes'][0]['effects']==[] and saved['validation']['valid']
 assert c.post(base+'/plans',json=body).json()['already_saved']
 after=copy.deepcopy(m.get(p['id']));assert len(after.pop('production_plans'))==1;assert after==before
 assert len(c.get(base+'/plans').json()['plans'])==1
 other,_,otherbase=fixture();assert c.get(otherbase+'/plans/'+rid).status_code==404

def test_references_quotes_scope_duplicates_and_wrong_project_block_save():
 p,plan,base=fixture()
 for mutate in [lambda q:q.update(project_id='other'),lambda q:q['scope_scene_ids'].append(q['scope_scene_ids'][0]),lambda q:q['scenes'].append(copy.deepcopy(q['scenes'][0])),lambda q:q['scenes'][0]['performances'][0].update(quote='not in book'),lambda q:q['scenes'][0]['performances'][0].update(voice_id='invented'),lambda q:q['scenes'][0]['performances'][0].update(character_id='invented'),lambda q:q['scenes'][0]['performances'][0].update(segment_id='outside')]:
  q=copy.deepcopy(plan);mutate(q);pr=preview(base,q);assert not pr['valid'] and pr['errors']
  assert c.post(base+'/plans',json={'plan':q,'confirmed':True,'preview_token':pr['preview_token']}).status_code==409
 assert not m.get(p['id']).get('production_plans')

def test_stale_tokens_and_confirmation_revalidated_at_save():
 p,plan,base=fixture();pr=preview(base,plan)
 assert c.post(base+'/plans',json={'plan':plan,'preview_token':pr['preview_token']}).status_code==422
 assert c.post(base+'/plans',json={'plan':plan,'confirmed':True,'preview_token':'bad'}).status_code==409
 with m.lock:
  p=m.get(p['id']);p['sound_effects']=[{'id':'new','name':'Nuevo'}];m.save(p)
 assert c.post(base+'/plans',json={'plan':plan,'confirmed':True,'preview_token':pr['preview_token']}).status_code==409
 assert not preview(base,plan)['valid']

def test_errors_short_no_full_manuscript_echo_and_missing_resource_is_pending():
 p,plan,base=fixture();q=copy.deepcopy(plan);q['scenes'][0]['performances'][0]['command']='DO_NOT_ECHO_PRIVATE_VALUE'
 r=c.post(base+'/preview',json={'plan':q});assert r.status_code==422 and 'DO_NOT_ECHO_PRIVATE_VALUE' not in r.text
 assert c.post(base+'/preview',content='not json').status_code==422
 assert c.post(base+'/preview',content=b' '* (5*1024*1024+1)).status_code==413
 seg=plan['scenes'][0]['performances'][0];cue={'segment_id':seg['segment_id'],'anchor_quote':seg['quote'],'resource_id':None,'search_request':'pasos','reason':'Revisar si es literal.'}
 plan['scenes'][0]['effects']=[cue];pr=preview(base,plan);assert pr['valid'] and any('pendiente de conseguir' in x['message'] for x in pr['warnings'])
 plan['scenes'][0]['effects'][0]['resource_id']='foreign';assert not preview(base,plan)['valid']
 plan['scenes'][0]['effects']=[cue,copy.deepcopy(cue)];assert not preview(base,plan)['valid']
