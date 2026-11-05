import copy
from fastapi.testclient import TestClient
from app import main as m
from test_sound_mixer import setup

c=TestClient(m.app)


def fixture():
 p=setup()
 with m.lock:
  p=m.get(p['id']);segments=p['chapters'][0]['segments']
  segments[0]['text']='El mar brillaba.';segments[1]['text']='La lluvia caía sobre el mar.'
  p['manuscript_reviews']=[{'category':'sound','decision':'confirm','evidence':{'label':label,'segment_id':s['id'],'cue':quote}} for label,s,quote in [('mar',segments[0],'mar'),('océano',segments[1],'mar'),('lluvia',segments[1],'lluvia')]]
  m.save(p)
 return m.get(p['id'])


def test_grouped_recommendations_link_existing_sound_and_unlink_preserve_audio():
 p=fixture();pid=p['id'];base=f'/api/projects/{pid}/sound-checklist'
 data=c.get(base).json();assert data['pending']==2 and data['completed']==0
 sea=next(x for x in data['items'] if x['query']=='ocean waves');assert sea['count']==2
 assert all(l['chapter'] and l['scene']==1 for l in sea['locations'])
 before=copy.deepcopy(m.get(pid));r=c.put(base+'/'+sea['id'],json={'sound_id':'sound1'})
 assert r.status_code==200,r.text
 assert r.json()['completed']==1 and r.json()['pending']==1
 linked=next(x for x in c.get(base).json()['items'] if x['id']==sea['id']);assert linked['completed'] and linked['sound_name']=='Claxon de prueba'
 # Explicit resource choice is allowed; filenames never auto-complete a recommendation.
 after=m.get(pid);assert after['chapters']==before['chapters'] and after['sound_effects']==before['sound_effects']
 assert c.delete(base+'/'+sea['id']).json()['completed']==0
 assert m.get(pid)['sound_effects']==before['sound_effects']


def test_reject_undone_and_excluded_recommendations_do_not_enter_list():
 p=fixture();pid=p['id']
 with m.lock:
  p=m.get(pid);p['manuscript_reviews'][0]['undone_at']='now';p['manuscript_reviews'][1]['decision']='reject';p['chapters'][0]['segments'][1]['excluded']=True;m.save(p)
 assert c.get(f'/api/projects/{pid}/sound-checklist').json()['total']==0


def test_removed_file_becomes_pending_and_cannot_be_relinked():
 p=fixture();pid=p['id'];base=f'/api/projects/{pid}/sound-checklist';gid=c.get(base).json()['items'][0]['id']
 assert c.put(base+'/'+gid,json={'sound_id':'sound1'}).status_code==200
 (m.DATA/p['sound_effects'][0]['file']).unlink()
 assert c.get(base).json()['pending']==2
 assert c.put(base+'/'+gid,json={'sound_id':'sound1'}).status_code==409


def test_links_reject_unknown_group_and_foreign_project_sound():
 p=fixture();base=f'/api/projects/{p["id"]}/sound-checklist';gid=c.get(base).json()['items'][0]['id']
 assert c.put(base+'/missing',json={'sound_id':'sound1'}).status_code==404
 assert c.put(base+'/'+gid,json={'sound_id':'not-in-project'}).status_code==409
 assert c.get('/api/projects/missing/sound-checklist').status_code==404


def test_duplicate_reviews_are_deduplicated_and_later_rejection_wins():
 p=fixture();pid=p['id']
 with m.lock:
  p=m.get(pid);p['manuscript_reviews'].append(copy.deepcopy(p['manuscript_reviews'][0]));m.save(p)
 data=c.get(f'/api/projects/{pid}/sound-checklist').json();assert sum(g['count'] for g in data['items'])==3
 with m.lock:
  p=m.get(pid);p['manuscript_reviews'][-1]['decision']='reject';m.save(p)
 data=c.get(f'/api/projects/{pid}/sound-checklist').json();assert sum(g['count'] for g in data['items'])==2


def test_changed_text_no_longer_contains_quote_is_not_recommended():
 p=fixture();pid=p['id']
 with m.lock:
  p=m.get(pid);p['chapters'][0]['segments'][0]['text']='Se hizo silencio.';m.save(p)
 sea=next(g for g in c.get(f'/api/projects/{pid}/sound-checklist').json()['items'] if g['query']=='ocean waves')
 assert sea['count']==1


def test_editorial_search_query_is_bounded_and_acceleration_is_searchable():
 from app.sound_checklist import search_query
 assert search_query('Aceleración de retirada')=='car accelerating away'
 assert search_query('Aceleración rápida')=='car acceleration'
 assert 1<len(search_query('Descripción muy larga de efecto sonoro '*30))<=150
 assert search_query('Beso')=='kiss'
