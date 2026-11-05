import copy
import hashlib
import math
import struct
import wave
from fastapi.testclient import TestClient
from app import main as m, sound_mixer as sm
from app.narrative_cues import sound_cues
from app.sound_direction import editorial,music_direction
from app.project_cleanup import project_files
from app.manuscript_analysis import analyze_project
from test_sound_mixer import setup,create,render

c=TestClient(m.app)


def test_heartbeat_and_actions_have_exact_evidence_and_negation_context():
    text='Su corazón empezó a latir fuerte. Respiraba agitadamente. Le dio una bofetada. Arrastró el ropero. Rompió el vidrio. Suspiró.'
    cues=sound_cues(text)
    assert {'latidos del corazón','golpe','mueble arrastrado','cristal roto','suspiro'}<={x['label'] for x in cues}
    for x in cues:assert text[x['start']:x['end']]==x['cue'] and x['requires_context_review']
    assert not any(x['label']=='latidos del corazón' for x in sound_cues('No sentía latidos.'))
    assert all(x['context_status']=='revisar contexto' for x in sound_cues('Imaginaba que su corazón empezaba a latir.'))
    assert not any(x['label']=='latidos del corazón' for x in sound_cues('El corazón de la ciudad latía.'))


def test_front_matter_and_moods_with_approved_emotions():
    assert editorial('Tabla de contenido') and editorial('Páginas iniciales') and editorial('Preámbulo')
    assert not editorial('CAPÍTULO 23 — El regreso')
    assert music_direction('ISBN','Estaba feliz.') is None
    assert music_direction('Capítulo I','Estaba eufórico y lleno de júbilo.')['mood']=='euforia'
    assert music_direction('Capítulo I','Estaba lleno de rabia.')['mood']=='ira'
    assert music_direction('Capítulo I','Una puerta.',['alegría'])['mood']=='alegría'
    assert music_direction('Capítulo I','No estaba enojado.')['mood']=='narrativo suave'


def test_scan_coverage_review_idempotence_and_saved_sources_unchanged():
    p=setup();pid=p['id'];before=copy.deepcopy(p)
    with m.lock:
        p=m.get(pid);p['chapters'][0]['segments'][0]['text']='Su corazón empezó a latir fuerte.'
        p['chapters'][0]['segments'][1]['text']='Suspiró antes de arrastrar el ropero.'
        p['chapters'].append({'id':'isbn','title':'ISBN','segments':[{'id':'isbn-row','text':'Su corazón latía.','speaker':'Narrador','scene':1}]})
        m.save(p)
    before=copy.deepcopy(m.get(pid));base=f'/api/projects/{pid}/sound-checklist';r=c.get(base+'/discovery').json()
    assert r['chapters'][0]['suggestions']>=3 and r['chapters'][1]['excluded_editorial']
    assert all(x['chapter_id']!='isbn' for x in r['items'])
    heart=next(x for x in r['items'] if x['label']=='latidos del corazón')
    body={'document_token':r['document_token'],'ids':[heart['id']],'decision':'confirm'}
    assert c.post(base+'/discovery/review',json=body).json()['added']==1
    assert c.post(base+'/discovery/review',json=body).json()['added']==0
    data=c.get(base).json();assert any(g['query']=='heartbeat' for g in data['items'])
    assert m.get(pid)['chapters']==before['chapters'] and m.get(pid)['sound_effects']==before['sound_effects']
    # Existing analysis also uses the expanded detector and suppresses front matter.
    report=analyze_project(m.get(pid));assert any(x['label']=='latidos del corazón' for x in report['sound_suggestions'])
    assert not any(x['chapter_id']=='isbn' for x in report['sound_suggestions'])


def energy(path):
    with wave.open(str(path),'rb') as w:
        raw=w.readframes(w.getnframes());values=struct.unpack('<'+'h'*(len(raw)//2),raw)
    return math.sqrt(sum(v*v for v in values)/len(values))


def test_music_loops_whole_scene_and_bus_levels_change_audible_mix_preserve_files():
    p=setup();pid=p['id'];base=f'/api/projects/{pid}/sound-mixer';sid=p['chapters'][0]['segments'][0]['id']
    original={f:hashlib.sha256((m.DATA/f).read_bytes()).hexdigest() for f in project_files(p)}
    music=c.post(base+'/music-bed',json={'scene_id':sid,'sound_id':'sound1','volume_db':-12})
    assert music.status_code==200,music.text
    assert music.json()['role']=='music' and music.json()['loop'] and music.json()['duration']==2
    first=render(p);low=energy(m.DATA/first['file'])
    assert low>0
    levels={'narration_db':0,'effects_db':0,'music_db':6}
    assert c.put(base+'/scenes/'+sid+'/levels',json=levels).status_code==200
    assert c.get(base).json()['mixes'][0]['stale']
    second=render(p);high=energy(m.DATA/second['file']);assert 1.9<high/low<2.1
    scene=c.get(base).json()['scenes'][0];assert scene['levels']==levels and scene['music_suggestion']
    # Replacing the bed does not accumulate music or erase manually placed effects.
    create(p)
    assert c.post(base+'/music-bed',json={'scene_id':sid,'sound_id':'sound1'}).status_code==200
    cues=m.get(pid)['sound_cues'];assert len(cues)==2 and sum(x.get('role')=='music' for x in cues)==1
    for f,digest in original.items():assert hashlib.sha256((m.DATA/f).read_bytes()).hexdigest()==digest
    assert c.put(base+'/scenes/'+sid+'/levels',json={**levels,'music_db':100}).status_code==422
