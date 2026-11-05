"""Audit production projects read-only; quarantine only explicit IDs from a reviewed report.
Never deletes rows, jobs, manuscripts or audio files. Does not import application startup.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text

FIXTURES={
 'Revisión en lote':'CAPÍTULO I\nLA PRUEBA\nLindsay dijo que Gibrán estaba en la playa.\nSe escuchaban gaviotas frente al mar.\nHoras después, sonó el teléfono.\nMás tarde, llovía en el bosque.',
 'Editor fixture':'Capítulo 1\nANA: Ditóx vuelve.\nANA: Ditóx sale.\nCapítulo 2\nMARCOS: Ditóx espera.',
}

# Additional exact manuscripts verified in the test source; title alone never suffices.
FIXTURES.update({
 'Casting':'Capítulo 1\nANA: Hola.\n«Mi pensamiento».\n—No sé.\nCapítulo 2\nMARCOS: Adiós.',
 'Analysis fixture':'Capítulo 1\nLindsay: Hola, Gibrán.\nGibrán: Voy hacia Madrid.\nLindsay sonrió en la casa.\nHoras después, Gibrán estaba furioso en el bosque.\nSe cerró la puerta y llovía.\nNo tenía miedo. Era una lluvia de ideas.\n---\nLindsay regresó.',
 'Ángelo Ditóx':'CAPÍTULO I\nLA VIDA DE ÁNGELO\nLindsay dijo que estaba en casa.\nFrente al mar se escuchaban los graznidos de las gaviotas.\nRecordó una habitación silenciosa.\nCAPÍTULO II\nEL SARGENTO SILVANO\nEl Sargento Silvano estaba en el parque.',
 'Permisos':'',
})

FIXTURES.update({
 'Workflow':'Capítulo 1\nANA: Hola.\n«No lo diré».\n—¿Quién?\nCapítulo 2\nANA: Adiós.\nMARCOS: Hasta luego.',
 'Escenas':'Capítulo 1\nUno.\n. . . . . . . . . .\nDos.\nANA: Espera... no salgas.\n.................................\nTres.',
 'Escena sonora':'CAPÍTULO I\nEl mar.\nSonó el claxon.',
 'Prueba':'Capítulo 1\nEl reloj marcó las nueve.\n—Hola, Ana.\n***\nEl tren partió.\nCapítulo 2\nFin.',
 'Proyecto eliminable':'Capitulo 1\nANA: Hola.',
 'Primero':'Capitulo 1\nANA: Hola.',
 'Segundo':'Capitulo 1\nANA: Hola.',
 'Invalid':'',
})
WORKFLOW_BATCH='Capítulo 1\nANA: Hola.\n'+'\n'.join('—Frase '+str(i) for i in range(40))


def scene_fixture_assets(p):
 # Exact synthetic resource created by test_sound_mixer.setup, not any imported SFX.
 sounds=p.get('sound_effects',[])
 if len(sounds)!=1:return False
 sound=sounds[0]
 if not all(sound.get(k)==v for k,v in {'id':'sound1','name':'Claxon de prueba','author':'Autor','file':f'effect_{p.get("id")}.wav','duration':.3,'source_url':'https://freesound.org/people/test/sounds/123/'}.items()):return False
 segments=[s for ch in p.get('chapters',[]) for s in ch.get('segments',[])]
 return len(segments)==2 and all(s.get('audio')==f'narration_{p.get("id")}_{i}.wav' and s.get('duration')==1 for i,s in enumerate(segments))


def normalized(value):
 return unicodedata.normalize('NFC',str(value or '').replace('\r\n','\n').replace('\r','\n')).strip()


def digest(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()


def now():return datetime.now(timezone.utc).isoformat()


def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as f:
  json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())


def classify(p):
 title=p.get('title','');original=normalized(p.get('original',''))
 if p.get('deleted_at'):return False,'Ya está en la papelera; no se modifica.'
 if title not in FIXTURES:return False,'No coincide con un caso de prueba verificado; conservar.'
 if title in ('Permisos','Invalid') and (p.get('chapters') or p.get('source_file') or p.get('source_filename')):
  return False,'El proyecto vacío tiene contenido o archivo fuente; conservar.'
 if original!=normalized(FIXTURES[title]) and not (title=='Workflow' and original==normalized(WORKFLOW_BATCH)):return False,'El nombre coincide, pero el manuscrito es distinto; conservar.'
 if any(p.get(k) for k in ('sound_effects','sound_mixes','sound_cues')) and not (title=='Escena sonora' and scene_fixture_assets(p)):
  return False,'Tiene biblioteca o mezclas de efectos; requiere revisión individual, conservar.'
 return True,'Nombre y manuscrito completos coinciden con la muestra de prueba verificada.'


def audit(engine,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 records=[]
 with engine.begin() as conn:
  if engine.dialect.name=='postgresql':conn.execute(text('SET TRANSACTION READ ONLY'))
  for pid,payload in conn.execute(text('SELECT id,payload FROM projects')):
   p=json.loads(payload);candidate,reason=classify(p)
   segments=[s for ch in p.get('chapters',[]) for s in ch.get('segments',[])]
   records.append({'id':pid,'title':p.get('title',''),'candidate':candidate,'reason':reason,
     'characters':len(p.get('original','')),'chapters':len(p.get('chapters',[])),
     'segments':len(segments),'active_audio':sum(bool(s.get('audio')) for s in segments),
     'versions':sum(len(s.get('versions',[])) for s in segments),'in_trash':bool(p.get('deleted_at')),
     'payload_sha256':digest(payload)})
 records.sort(key=lambda r:(not r['candidate'],r['title'],r['id']))
 report={'format':'lia.project-test-audit.v1','created_at':now(),'projects':records}
 write_json(out/'informe_proyectos.json',report)
 with (out/'informe_proyectos.csv').open('x',encoding='utf-8-sig',newline='') as f:
  columns=['id','title','candidate','reason','characters','chapters','segments','active_audio','versions','in_trash']
  writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(records)
 print(f'Proyectos registrados: {len(records)}; candidatos exactos: {sum(r["candidate"] for r in records)}')
 for r in records:
  if r['candidate']:print(f'CANDIDATO | {r["id"]} | {r["title"]} | {r["segments"]} fragmentos | {r["active_audio"]} audios')
 print('Solo lectura: no se modificaron proyectos ni archivos. Informe: informe_proyectos.csv / .json')
 return report


def locked_row(conn,engine,pid):
 q='SELECT payload FROM projects WHERE id=:id'
 if engine.dialect.name=='postgresql':q+=' FOR UPDATE'
 row=conn.execute(text(q),{'id':pid}).first()
 if not row:raise ValueError('Proyecto no encontrado: '+pid)
 return row[0]


def trash(engine,report_path,ids,out):
 report=json.loads(Path(report_path).read_text(encoding='utf-8-sig'))
 if report.get('format')!='lia.project-test-audit.v1':raise ValueError('Informe no reconocido.')
 approved={r['id']:r for r in report['projects']}
 if not ids:raise ValueError('Especifica los IDs revisados; no se seleccionan automáticamente.')
 selected=list(dict.fromkeys(ids));backup={'format':'lia.project-quarantine.v1','created_at':now(),'projects':[]}
 backup_path=Path(out)/'respaldo_papelera.json'
 with engine.begin() as conn:
  for pid in selected:
   r=approved.get(pid)
   if not r or not r.get('candidate'):raise ValueError('El ID no es candidato verificado del informe: '+pid)
   payload=locked_row(conn,engine,pid)
   if digest(payload)!=r['payload_sha256']:raise ValueError('El proyecto cambió desde el informe; repite la revisión: '+pid)
   p=json.loads(payload)
   if not classify(p)[0]:raise ValueError('El proyecto ya no cumple los criterios: '+pid)
   p['deleted_at']=now();updated=json.dumps(p,ensure_ascii=False)
   backup['projects'].append({'id':pid,'title':p['title'],'original_payload':payload,'trashed_sha256':digest(updated),'trashed_payload':updated})
  # Write a complete backup before the first DB mutation. Errors roll back the entire batch.
  write_json(backup_path,backup)
  for item in backup['projects']:
   conn.execute(text('UPDATE projects SET payload=:p WHERE id=:id'),{'id':item['id'],'p':item['trashed_payload']})
 print(f'Enviados a papelera: {len(selected)}. No se borraron audios, trabajos ni registros.')
 print('Respaldo reversible: respaldo_papelera.json. También puedes restaurarlos desde Papelera en LIA.')
 return backup


def restore(engine,backup_path):
 backup=json.loads(Path(backup_path).read_text(encoding='utf-8-sig'))
 if backup.get('format')!='lia.project-quarantine.v1':raise ValueError('Respaldo no reconocido.')
 restored=0
 with engine.begin() as conn:
  for item in backup['projects']:
   current=locked_row(conn,engine,item['id'])
   if digest(current)==digest(item['original_payload']):continue
   if digest(current)!=item['trashed_sha256']:raise ValueError('El proyecto cambió después de enviarlo a papelera; no se sobrescribe: '+item['id'])
   conn.execute(text('UPDATE projects SET payload=:p WHERE id=:id'),{'id':item['id'],'p':item['original_payload']});restored+=1
 print(f'Proyectos restaurados: {restored}.')
 return restored


def cli():
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['audit','trash','restore'],default='audit')
 parser.add_argument('--out',default='/report');parser.add_argument('--report');parser.add_argument('--backup');parser.add_argument('--ids',nargs='*')
 args=parser.parse_args()
 url=os.environ.get('DATABASE_URL')
 if not url:raise ValueError('No hay conexión configurada en este contenedor. No se modifica nada.')
 engine=create_engine(url)
 try:
  if args.mode=='audit':audit(engine,args.out)
  elif args.mode=='trash':
   if not args.report:raise ValueError('Falta --report con el informe revisado.')
   trash(engine,args.report,args.ids,args.out)
  else:
   if not args.backup:raise ValueError('Falta --backup.')
   restore(engine,args.backup)
 finally:engine.dispose()


if __name__=='__main__':
 try:cli()
 except (ValueError,FileNotFoundError,FileExistsError,json.JSONDecodeError) as e:print('DETENIDO: '+str(e),file=sys.stderr);sys.exit(1)
 except Exception:print('DETENIDO: fallo de conexión u operación. No se confirma ningún cambio del lote; no borres datos ni volúmenes.',file=sys.stderr);sys.exit(1)
