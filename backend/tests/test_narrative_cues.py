import copy
from app.narrative_cues import sound_cues
from app.manuscript_analysis import analyze_project


def test_mar_gaviotas_and_vehicle_are_separate_cues_with_exact_evidence():
 text='Frente al mar, las gaviotas graznaban. Un auto pasó tocando el claxon.'
 cues=sound_cues(text)
 assert {'mar','gaviotas','vehículo pasando','claxon'} <= {c['label'] for c in cues}
 assert next(c for c in cues if c['label']=='mar')['kind']=='ambiente'
 for c in cues:
  assert text[c['start']:c['end']]==c['cue']
  assert c['requires_context_review']


def test_silent_absent_metaphorical_and_remembered_sounds():
 assert not sound_cues('Era un mar de dudas. Una lluvia de ideas.')
 assert not sound_cues('No se oían gaviotas. No había tráfico. El mar no se oía.')
 assert not sound_cues('El auto estaba estacionado.')
 cues=sound_cues('Recordó el mar y las gaviotas. Sonó un claxon.')
 assert all(c['context_status']=='revisar contexto' for c in cues if c['label']!='claxon')
 assert next(c for c in cues if c['label']=='claxon')['context_status']=='posible sonido presente'
 # The metaphor in the first sentence must not hide the real rain in the second.
 assert len(sound_cues('Era lluvia de ideas. Afuera caía lluvia.'))==1


def test_scene_plan_preserves_book_and_all_scenes_beyond_first_eight_mentions():
 segments=[{'id':str(i),'text':'Lindsay dijo: Gibrán estaba frente al mar con gaviotas. Un auto pasó y sonó el claxon.', 'speaker':'Narrador','scene':i+1,'audio':'keep.wav'} for i in range(12)]
 segments[-1]['excluded']=True
 p={'id':'fixture','original':'text','characters':[], 'chapters':[{'id':'ch','title':'Capítulo','segments':segments}]}
 before=copy.deepcopy(p);r=analyze_project(p)
 assert p==before and r['version']==2 and len(r['scene_plan'])==12
 assert {'Lindsay','Gibrán'}<={n['name'] for n in r['names']}
 assert next(n for n in r['names'] if n['name']=='Lindsay')['evidence_level']=='fuerte'
 assert 'Lindsay' in r['scene_plan'][9]['characters']
 assert {'mar'}<={x['label'] for x in r['scene_plan'][9]['ambience']}
 assert {'claxon','vehículo pasando'}<={x['label'] for x in r['scene_plan'][9]['effects']}
 assert not r['scene_plan'][-1]['ambience']


def test_compound_names_and_explicit_scene_arrival():
 p={'id':'compound','characters':[], 'chapters':[{'id':'ch','title':'Prueba','segments':[
 {'id':'a','text':'—Hola —dijo María del Carmen. Juan Carlos respondió que sí. María del Carmen susurró adiós.','speaker':'Narrador','scene':1},
 {'id':'b','text':'Llegaron al puerto frente al océano.','speaker':'Narrador','scene':1}]}]}
 r=analyze_project(p)
 assert {'María del Carmen','Juan Carlos'}<={n['name'] for n in r['names']}
 assert len(r['scene_candidates'])==1
