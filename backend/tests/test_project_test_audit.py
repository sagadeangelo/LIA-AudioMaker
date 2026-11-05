"""Maintenance script never guesses from names and never deletes audio."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine,text

# Keep this test optional in Docker images where only app/tests are mounted.
SCRIPT=Path(__file__).resolve().parents[2]/'scripts'/'project_test_audit.py'
if not SCRIPT.is_file():SCRIPT=Path('/tool/project_test_audit.py')
if not SCRIPT.is_file():pytest.skip('Maintenance tool is outside this test mount',allow_module_level=True)
spec=importlib.util.spec_from_file_location('project_audit',SCRIPT);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


@pytest.fixture
def database(tmp_path):
 engine=create_engine('sqlite:///'+str(tmp_path/'prod.sqlite'))
 with engine.begin() as c:
  c.execute(text('CREATE TABLE projects(id TEXT PRIMARY KEY,payload TEXT)'))
  for pid,title,original in [('candidate','Revisión en lote',audit.FIXTURES['Revisión en lote']),('real','Ángelo_El Proyecto Ditóx','Mi novela completa'),('same-name','Editor fixture','Mi manuscrito real')]:
   c.execute(text('INSERT INTO projects VALUES (:id,:p)'),{'id':pid,'p':json.dumps({'id':pid,'title':title,'original':original,'chapters':[]})})
 yield engine
 engine.dispose()


def rows(engine):
 with engine.connect() as c:return dict(c.execute(text('SELECT id,payload FROM projects')).all())


def test_audit_is_readonly_and_only_exact_fixture_candidate(database,tmp_path):
 before=rows(database);report=audit.audit(database,tmp_path/'report')
 assert rows(database)==before
 assert [r['id'] for r in report['projects'] if r['candidate']]==['candidate']
 assert (tmp_path/'report'/'informe_proyectos.csv').is_file()


def test_quarantine_and_restore_preserve_all_other_projects_and_files(database,tmp_path):
 report=tmp_path/'report';audit.audit(database,report);before=rows(database)
 audio=tmp_path/'precious.wav';audio.write_bytes(b'original-audio')
 out=tmp_path/'trash';audit.trash(database,report/'informe_proyectos.json',['candidate'],out)
 after=rows(database);assert after['real']==before['real'] and after['same-name']==before['same-name']
 assert json.loads(after['candidate'])['deleted_at'] and audio.read_bytes()==b'original-audio'
 assert audit.restore(database,out/'respaldo_papelera.json')==1
 assert rows(database)==before
 assert audit.restore(database,out/'respaldo_papelera.json')==0


def test_bad_batch_is_atomic_and_changed_projects_are_rejected(database,tmp_path):
 report=tmp_path/'report';audit.audit(database,report);before=rows(database)
 with pytest.raises(ValueError):audit.trash(database,report/'informe_proyectos.json',['candidate','real'],tmp_path/'bad')
 assert rows(database)==before and not (tmp_path/'bad').exists()
 with database.begin() as c:c.execute(text("UPDATE projects SET payload=:p WHERE id='candidate'"),{'p':json.dumps({'id':'candidate','title':'Revisión en lote','original':audit.FIXTURES['Revisión en lote'],'chapters':[],'changed':True})})
 before=rows(database)
 with pytest.raises(ValueError):audit.trash(database,report/'informe_proyectos.json',['candidate'],tmp_path/'changed')
 assert rows(database)==before


def test_restore_refuses_overwriting_new_changes(database,tmp_path):
 report=tmp_path/'report';audit.audit(database,report);out=tmp_path/'trash';audit.trash(database,report/'informe_proyectos.json',['candidate'],out)
 with database.begin() as c:c.execute(text("UPDATE projects SET payload=:p WHERE id='candidate'"),{'p':'{"id":"candidate","changed":true}'})
 before=rows(database)
 with pytest.raises(ValueError):audit.restore(database,out/'respaldo_papelera.json')
 assert rows(database)==before


def test_projects_with_library_are_not_automatic_candidates():
 p={'title':'Editor fixture','original':audit.FIXTURES['Editor fixture'],'sound_effects':[{'id':'keep'}]}
 assert not audit.classify(p)[0]


def test_extra_fixture_names_require_exact_manuscript_and_real_novel_is_protected():
 for title in ('Casting','Analysis fixture','Ángelo Ditóx','Permisos'):
  assert audit.classify({'title':title,'original':audit.FIXTURES[title],'chapters':[]})[0]
  assert not audit.classify({'title':title,'original':'Mi novela real completa','chapters':[]})[0]
 assert not audit.classify({'title':'Ángelo_El Proyecto Ditóx','original':audit.FIXTURES['Ángelo Ditóx'],'chapters':[]})[0]
 assert not audit.classify({'title':'Permisos','original':'','chapters':[{'segments':[]}]})[0]
 assert not audit.classify({'title':'Permisos','original':'','source_file':'real.txt'})[0]


def test_third_review_matches_verified_samples_and_protects_same_name_real_content():
 for title in ('Workflow','Escenas','Escena sonora','Prueba','Proyecto eliminable','Primero','Segundo','Invalid'):
  assert audit.classify({'title':title,'original':audit.FIXTURES[title],'chapters':[]})[0]
  assert not audit.classify({'title':title,'original':'Contenido real propio','chapters':[]})[0]
 assert audit.classify({'title':'Workflow','original':audit.WORKFLOW_BATCH})[0]
 assert not audit.classify({'title':'Invalid','original':'','chapters':[{}]})[0]


def test_scene_synthetic_assets_are_recognized_but_imported_library_is_protected():
 p={'id':'test-id','title':'Escena sonora','original':audit.FIXTURES['Escena sonora'],'chapters':[{'segments':[{'audio':f'narration_test-id_{i}.wav','duration':1} for i in range(2)]}],
 'sound_effects':[{'id':'sound1','name':'Claxon de prueba','author':'Autor','file':'effect_test-id.wav','duration':.3,'source_url':'https://freesound.org/people/test/sounds/123/'}]}
 assert audit.classify(p)[0]
 p['sound_effects'][0]['name']='Mi sonido de Freesound'
 assert not audit.classify(p)[0]
