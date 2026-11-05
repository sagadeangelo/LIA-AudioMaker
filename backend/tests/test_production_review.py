import copy
from fastapi.testclient import TestClient
from app import main as m
from test_production_import import fixture,preview
c=TestClient(m.app)
def saved():
 p,plan,base=fixture();pr=preview(base,plan);rid=c.post(base+'/plans',json={'plan':plan,'confirmed':True,'preview_token':pr['preview_token']}).json()['id']
 return p,base,rid,c.get(base+'/plans/'+rid).json()
def decision(base,rid,d,item,choice='reviewed',note='Mantener la configuración actual.'):
 return c.post(base+'/plans/'+rid+'/review',json={'item_id':item['id'],'decision':choice,'note':note,'preview_token':d['validation']['preview_token'],'review_token':d['review']['review_token']})
def test_review_survives_reload_and_keeps_original_plan_and_project_unchanged():
 p,base,rid,d=saved();before=copy.deepcopy(m.get(p['id']));item=d['review']['items'][0]
 r=decision(base,rid,d,item);assert r.status_code==200,r.text
 after=c.get(base+'/plans/'+rid).json();assert after['review']['completed']==1 and after['review']['history_count']==1
 assert after['plan']==d['plan'] and after['review']['execution_available'] is False
 assert next(x for x in after['review']['items'] if x['id']==item['id'])['response']['note']=='Mantener la configuración actual.'
 actual=copy.deepcopy(m.get(p['id']));a=actual.pop('production_plans');b=before.pop('production_plans');assert actual==before and a[0]['plan']==b[0]['plan']
 assert decision(base,rid,d,item).status_code==409

def test_changes_deferred_reopen_and_note_requirement():
 p,base,rid,d=saved();item=d['review']['items'][0]
 assert decision(base,rid,d,item,note=' ').status_code==422
 assert decision(base,rid,d,item,'needs_change','Cambiar la propuesta, sin ejecutar aún.').status_code==200
 d=c.get(base+'/plans/'+rid).json();assert d['review']['changes_requested']==1 and d['review']['completed']==0
 assert decision(base,rid,d,item,'deferred','').status_code==200
 d=c.get(base+'/plans/'+rid).json();assert d['review']['changes_requested']==0
 assert decision(base,rid,d,item,'keep_existing','Conservar narración actual.').status_code==200
 d=c.get(base+'/plans/'+rid).json();assert d['review']['completed']==1
 assert decision(base,rid,d,item,'pending','').status_code==200
 d=c.get(base+'/plans/'+rid).json();assert d['review']['completed']==0 and d['review']['history_count']==4

def test_all_reviewed_does_not_enable_execution_and_stale_blocks_new_answers():
 p,base,rid,d=saved()
 for item in d['review']['items']:
  assert decision(base,rid,d,item).status_code==200;d=c.get(base+'/plans/'+rid).json()
 assert d['review']['status']=='editorial_reviewed' and d['review']['pending']==0 and not d['review']['execution_available']
 with m.lock:
  p=m.get(p['id']);p['chapters'][0]['segments'][0]['text']+=' actualizado';m.save(p)
 assert decision(base,rid,d,d['review']['items'][0]).status_code==409
 d=c.get(base+'/plans/'+rid).json();assert d['review']['status']=='stale' and d['review']['completed']>0

def test_unknown_item_cross_project_and_bad_fields_rejected():
 p,base,rid,d=saved()
 assert decision(base,rid,d,{'id':'not-an-issue'}).status_code==422
 _,_,otherbase=fixture()
 assert decision(otherbase,rid,d,d['review']['items'][0]).status_code==404
 assert c.post(base+'/plans/'+rid+'/review',json={'item_id':'x','decision':'execute','preview_token':'x','review_token':'x'}).status_code==422
