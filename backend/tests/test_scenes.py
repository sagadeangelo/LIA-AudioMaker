import copy, io, shutil, wave
from fastapi.testclient import TestClient
from app.main import app,save
from app.narrative import analyze
from app.scenes import detect_scenes
c=TestClient(app)

def book():
 p=c.post('/api/projects',json={'title':'Escenas'}).json()
 original='Capítulo 1\nUno.\n. . . . . . . . . .\nDos.\nANA: Espera... no salgas.\n.................................\nTres.'
 p=c.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.txt',original.encode())}).json()
 return p,original

def test_only_standalone_long_dot_lines_are_boundaries():
 ch=analyze('Capítulo 1\nUno... todavía.\n...\n....\n. . . . . .\nDos.\n……\nTres.')[0]
 assert [s['text'] for s in ch['segments']]==['Uno... todavía.','...','....','Dos.','Tres.']
 assert [s['scene'] for s in ch['segments']]==[1,1,1,2,3]

def test_legacy_conversion_is_idempotent_and_preserves_settings_audio():
 p,_=book();pid=p['id'];ch=p['chapters'][0]
 # Reproduce old imports where dot lines were narrated as ordinary paragraphs.
 base=copy.deepcopy(ch['segments'][0]);base.update(id='old-dot-line',text='. . . . . . .',source_text='. . . . . . .',audio='historic.wav',versions=[{'file':'historic.wav'}],speaker='Ana',voice='es+f2',color='#498BFF')
 for s in ch['segments']:s['scene']=1
 ch['segments'].insert(1,base);p.pop('scene_rules_version',None);before=copy.deepcopy(p);save(p)
 result=c.get(f'/api/projects/{pid}').json();after=result['chapters'][0]['segments']
 assert [s['id'] for s in after]==[s['id'] for s in ch['segments']]
 assert after[1]['excluded'] and after[1]['is_separator']
 assert after[1]['audio']=='historic.wav' and after[1]['voice']=='es+f2'
 assert after[2]['scene']==2
 assert result['original']==p['original']
 again=copy.deepcopy(result);detect_scenes(again);assert result==again
 assert c.post(f'/api/projects/{pid}/segments/{base["id"]}/generate').status_code==409
 assert c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':[base['id']],'excluded':False}).status_code==409

def test_quit_and_restore_preserves_original_ids_and_audio():
 p,original=book();pid=p['id'];segments=p['chapters'][0]['segments'];ids=[s['id'] for s in segments if s['scene']==2]
 segments[1].update(audio='existing.wav',duration=2.5,versions=[{'file':'existing.wav'}]);save(p)
 result=c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':ids,'excluded':True});assert result.status_code==200
 after=result.json();assert after['original']==original
 assert all(s['excluded'] for s in after['chapters'][0]['segments'] if s['id'] in ids)
 assert after['chapters'][0]['segments'][0]==segments[0]
 assert c.post(f'/api/projects/{pid}/segments/{ids[0]}/generate').status_code==409
 assert c.post(f'/api/projects/{pid}/segments/assign-batch',json={'segment_ids':ids,'character_id':p['characters'][0]['id']}).status_code==409
 restored=c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':ids,'excluded':False}).json()
 assert restored['chapters'][0]['segments'][1]['audio']=='existing.wav'
 assert restored['chapters'][0]['segments'][1]['versions']==segments[1]['versions']
 assert [s['id'] for s in restored['chapters'][0]['segments']]==[s['id'] for s in segments]
 # Missing IDs must not exclude the first valid ID partially.
 before=c.get(f'/api/projects/{pid}').json()
 assert c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':[ids[0],'missing'],'excluded':True}).status_code==404
 assert c.get(f'/api/projects/{pid}').json()==before

def test_export_omits_excluded_unproduced_fragments():
 if not (shutil.which('espeak-ng') or shutil.which('espeak')):return
 p,_=book();pid=p['id'];ch=p['chapters'][0]
 # Include only the first and last segments in the final chapter.
 remove=[s['id'] for s in ch['segments'][1:-1]]
 c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':remove,'excluded':True}).raise_for_status()
 duration=0
 for s in (ch['segments'][0],ch['segments'][-1]):
  r=c.post(f'/api/projects/{pid}/segments/{s["id"]}/generate?compact=true');assert r.status_code==200
  duration+=r.json()['segment']['duration']
 r=c.get(f'/api/projects/{pid}/chapters/{ch["id"]}/export?format=wav');assert r.status_code==200
 with wave.open(io.BytesIO(r.content)) as w:assert abs(w.getnframes()/w.getframerate()-duration)<.05
 assert c.get(f'/api/projects/{pid}/chapters/{ch["id"]}/export?format=mp3').status_code==200
 all_ids=[s['id'] for s in ch['segments']]
 c.post(f'/api/projects/{pid}/segments/inclusion',json={'segment_ids':all_ids,'excluded':True}).raise_for_status()
 assert c.get(f'/api/projects/{pid}/chapters/{ch["id"]}/export').status_code==409
