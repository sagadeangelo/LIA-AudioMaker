import copy,hashlib,json
from fastapi.testclient import TestClient
from app import main as m
c=TestClient(m.app)


def setup():
 p=c.post('/api/projects',json={'title':'Ángelo Ditóx'}).json()
 text='CAPÍTULO I\nLA VIDA DE ÁNGELO\nLindsay dijo que estaba en casa.\nFrente al mar se escuchaban los graznidos de las gaviotas.\nRecordó una habitación silenciosa.\nCAPÍTULO II\nEL SARGENTO SILVANO\nEl Sargento Silvano estaba en el parque.'
 p=c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('b.txt',text.encode())}).json()
 scenes=[]
 for idx,(ch,quote) in enumerate([(1,'Lindsay dijo que estaba en casa'),(1,'Frente al mar se escuchaban'),(2,'El Sargento Silvano estaba en el parque')]):
  scenes.append({'id':str(idx),'chapter':ch,'title':quote,'start_anchor':quote,'place':'playa' if idx==1 else 'casa','characters':['Lindsay'],'emotions':['calma'],'layer':'acción','sounds':[{'name':'gaviotas','quote':'los graznidos de las gaviotas','kind':'efecto','basis':'explícita'}] if idx==1 else []})
 plan={'format':'lia.editorial-plan','version':1,'title':'Ángelo Ditóx','characters':[{'id':'l','name':'Lindsay','aliases':['Lindsay'],'role':'Hermana','evidence':'Lindsay dijo que estaba en casa','kind':'person'}],'scenes':scenes}
 return p,plan


def preview(p,plan):
 r=c.post(f'/api/projects/{p["id"]}/analysis/editorial/preview',json={'plan':plan});assert r.status_code==200,r.text
 return r.json()


def apply(p,plan,pr,**more):return c.post(f'/api/projects/{p["id"]}/analysis/editorial/import',json={'plan':plan,'preview_token':pr['preview_token'],'confirmed':True,**more})


def test_preview_import_plan_and_audio_preservation(fake_tts):
 p,plan=setup();pid=p['id'];sid=p['chapters'][0]['segments'][0]['id']
 assert c.post(f'/api/projects/{pid}/segments/{sid}/generate').status_code==200
 p=m.get(pid);before=copy.deepcopy(p);filename=p['chapters'][0]['segments'][0]['audio'];sha=hashlib.sha256((m.DATA/filename).read_bytes()).hexdigest()
 pr=preview(p,plan);assert pr['matched_scenes']==3 and pr['matched_sounds']==1 and pr['can_import']
 r=apply(p,plan,pr);assert r.status_code==201,r.text
 after=m.get(pid)
 for field in ('chapters','characters','pronunciation_rules','pronunciation_voice_overrides'):assert after.get(field)==before.get(field)
 assert hashlib.sha256((m.DATA/filename).read_bytes()).hexdigest()==sha
 report=c.get(f'/api/projects/{pid}/analysis/jobs/{r.json()["job"]["id"]}/report').json()
 assert len(report['editorial_scenes'])==3 and report['sound_suggestions'][0]['label']=='gaviotas' and not report['stale']
 assert apply(p,plan,pr).status_code==409
 other,_=setup();assert c.get(f'/api/projects/{other["id"]}/analysis/jobs/{r.json()["job"]["id"]}/report').status_code==404


def test_apply_divisions_undo_and_concurrent_guard():
 p,plan=setup();before=copy.deepcopy(p['chapters']);pr=preview(p,plan)
 r=apply(p,plan,pr,apply_boundaries=True);assert r.status_code==201,r.text
 assert m.get(p['id'])['chapters']!=before
 before_segments={s['id']:{k:v for k,v in s.items() if k!='scene'} for ch in before for s in ch['segments']}
 after_segments={s['id']:{k:v for k,v in s.items() if k!='scene'} for ch in m.get(p['id'])['chapters'] for s in ch['segments']}
 assert after_segments==before_segments
 undo={'import_id':r.json()['job']['id'],'confirmed':True}
 assert c.post(f'/api/projects/{p["id"]}/analysis/editorial/undo',json=undo).status_code==200
 assert m.get(p['id'])['chapters']==before
 p,plan=setup();pr=preview(p,plan);r=apply(p,plan,pr,apply_boundaries=True);p=m.get(p['id']);p['chapters'][0]['segments'][-1]['scene']=77;m.save(p)
 undo['import_id']=r.json()['job']['id']
 assert c.post(f'/api/projects/{p["id"]}/analysis/editorial/undo',json=undo).status_code==409
 assert m.get(p['id'])['chapters'][0]['segments'][-1]['scene']==77


def test_mid_segment_short_ambiguous_missing_and_stale_anchors():
 p,plan=setup();plan['scenes'][1]['start_anchor']='se escuchaban los graznidos'
 plan['scenes'][1]['sounds'].append({'name':'inexistente','quote':'no pertenece al manuscrito'})
 pr=preview(p,plan);assert pr['scenes'][1]['status']=='matched' and not pr['scenes'][1]['can_divide']
 assert apply(p,plan,pr).status_code==422
 assert apply(p,plan,pr,accept_unresolved=True).status_code==201
 p,plan=setup();pr=preview(p,plan);p=m.get(p['id']);p['chapters'][0]['segments'][0]['text']+=' Cambiado.';m.save(p)
 assert apply(p,plan,pr).status_code==409
 p,plan=setup();plan['scenes'][0]['start_anchor']='Este texto no aparece en ningún lugar';plan['scenes'][2]['start_anchor']='Esto tampoco aparece en este capítulo'
 pr=preview(p,plan);assert not pr['can_import'];assert apply(p,plan,pr,accept_unresolved=True).status_code==409
 p,plan=setup();p['chapters'][0]['segments'][2]['text']='Frente al mar se escuchaban los graznidos de las gaviotas.';m.save(p)
 pr=preview(p,plan);assert pr['scenes'][1]['status']=='ambiguous'


def test_repeated_ids_and_invalid_plan_rejected():
 p,plan=setup();plan['scenes'].append(copy.deepcopy(plan['scenes'][0]))
 assert c.post(f'/api/projects/{p["id"]}/analysis/editorial/preview',json={'plan':plan}).status_code==422


def test_animal_cannot_be_automatically_cast_as_human():
 p,plan=setup();plan['characters'].append({'id':'animal','name':'Edward','role':'Chihuahua','kind':'animal','evidence':'Lindsay dijo que estaba en casa'})
 pr=preview(p,plan);r=apply(p,plan,pr);assert r.status_code==201
 jid=r.json()['job']['id'];report=c.get(f'/api/projects/{p["id"]}/analysis/jobs/{jid}/report').json();animal=next(x for x in report['names'] if x['kind']=='animal')
 body={'job_id':jid,'document_token':report['document_token'],'category':'name','item_id':animal['id'],'decision':'confirm'}
 assert c.post(f'/api/projects/{p["id"]}/analysis/review',json=body).status_code==409
 assert not any(x['name']=='Edward' for x in m.get(p['id'])['characters'])
