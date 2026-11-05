import copy,time,hashlib
from fastapi.testclient import TestClient
from app import main as m
from app.manuscript_analysis import analyze_project
from app.narrative import analyze
c=TestClient(m.app)


def book():
 p=c.post('/api/projects',json={'title':'Analysis fixture'}).json()
 text='Capítulo 1\nLindsay: Hola, Gibrán.\nGibrán: Voy hacia Madrid.\nLindsay sonrió en la casa.\nHoras después, Gibrán estaba furioso en el bosque.\nSe cerró la puerta y llovía.\nNo tenía miedo. Era una lluvia de ideas.\n---\nLindsay regresó.'
 return c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.txt',text.encode())}).json()


def run(p):
 r=c.post(f'/api/projects/{p["id"]}/analysis/jobs');assert r.status_code==202,r.text
 jid=r.json()['id']
 for _ in range(300):
  j=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}').json()
  if j['status'] not in ('queued','running'):break
  time.sleep(.01)
 assert j['status']=='completed',j
 r=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report');assert r.status_code==200,r.text
 return jid,r.json()


def test_mixed_case_and_accented_labels_and_extra_separators():
 chapters=analyze('Lindsay: Hola.\nGibrán: Adiós.\n---\nLindsay: Regresé.')
 s=chapters[0]['segments'];assert s[0]['speaker']=='Lindsay' and s[1]['speaker']=='Gibrán'
 assert s[2]['scene']==2
 assert analyze('Nota: texto.')[0]['segments'][0]['speaker']=='Narrador'
 assert analyze('En el bosque: había luz.')[0]['segments'][0]['speaker']=='Narrador'


def test_analysis_evidence_and_figurative_negated_cues():
 p=book();before=copy.deepcopy(p);r=analyze_project(p)
 names={n['name'] for n in r['names']}
 assert 'Lindsay' in names and 'Gibrán' in names and p==before
 assert all(x['evidence'] for x in r['names'])
 assert any(x['name']=='Madrid' for x in r['places'])
 assert any(x['label']=='ira' for x in r['emotions'])
 assert not any(x['label']=='miedo' for x in r['emotions'])
 rain=[x for x in r['sound_suggestions'] if x['label']=='lluvia'];assert len(rain)==1
 assert any(x['label']=='puerta' for x in r['sound_suggestions'])
 assert len(r['scenes'])==2 and len(r['scene_candidates'])==1


def test_review_names_scenes_undo_and_stale_data(fake_tts):
 p=book();pid=p['id'];s=p['chapters'][0]['segments'][0]
 c.post(f'/api/projects/{pid}/segments/{s["id"]}/generate')
 before=m.get(pid);name=before['chapters'][0]['segments'][0]['audio'];h=hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()
 jid,r=run(p);assert not r['stale']
 # A name inferred from narration can be added, but no speaker/audio is reassigned.
 candidate=next(n for n in r['names'] if not n['existing_character_id'])
 body={'job_id':jid,'document_token':r['document_token'],'category':'name','item_id':candidate['id'],'decision':'confirm'}
 result=c.post(f'/api/projects/{pid}/analysis/review',json=body);assert result.status_code==200,result.text
 assert result.json()['project']['chapters']==before['chapters']
 assert c.post(f'/api/projects/{pid}/analysis/review',json=body).status_code==200
 body.update(category='scene',item_id='0')
 result=c.post(f'/api/projects/{pid}/analysis/review',json=body);assert result.status_code==200,result.text
 assert [s['scene'] for s in result.json()['project']['chapters'][0]['segments']]!=[s['scene'] for s in before['chapters'][0]['segments']]
 assert c.post(f'/api/projects/{pid}/analysis/review',json=body).status_code==409
 result=c.post(f'/api/projects/{pid}/analysis/undo-scene');assert result.status_code==200
 assert result.json()['chapters']==before['chapters']
 assert hashlib.sha256((m.DATA/name).read_bytes()).hexdigest()==h
 other=book();assert c.get(f'/api/projects/{other["id"]}/analysis/jobs/{jid}/report').status_code==404


def test_mentions_route_present_and_empty_search_not_404():
 p=book();r=c.get(f'/api/projects/{p["id"]}/voice-editor/mentions',params={'original':'Ángelo'})
 assert r.status_code==200 and r.json()['total']==0
 spec=c.get('/openapi.json').json();assert '/api/projects/{pid}/voice-editor/mentions' in spec['paths']
