"""Project checklist of approved sound recommendations and explicit library links."""
import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .narrative import key
from .project_cleanup import safe_file
from .scenes import included
from .voice_editor import now

router=APIRouter(prefix='/api/projects/{pid}/sound-checklist',tags=['Sound checklist'])
ALIASES={'oceano':'mar','olas':'mar','oleaje':'mar','océano':'mar'}
SEARCH={'mar':'ocean waves','lluvia':'rain','gaviotas':'seagulls','claxon':'car horn','viento':'wind','pasos':'footsteps',
 'puerta':'door','disparo':'gunshot','telefono':'phone ringing','trueno':'thunder','aves':'birds','grillos':'crickets','perro':'dog bark',
 'latidos del corazon':'heartbeat','respiracion agitada':'heavy breathing','suspiro':'sigh','llanto':'sobbing','risa':'laughter','susurros':'whispering','gritos':'scream','cristal roto':'glass breaking','rechinido':'door squeak','excavacion':'digging','radio comunicador':'walkie talkie static','mueble arrastrado':'furniture dragging','herramientas de corte':'wire cutter','poda':'lawn mower','fuego':'fire crackling','cerradura':'door lock','pasos corriendo':'running footsteps','multitud':'crowd ambience','golpe':'punch impact','caida':'body falling','agua de tuberia':'water tap','aspersores':'garden sprinkler','aplausos':'applause','ropa y movimiento':'clothes rustle','escaleras':'stairs footsteps',
 'rio':'river','motor':'engine','trafico':'traffic','vehiculo pasando':'car passing','beso':'kiss'}


def search_query(label):
 normalized=ALIASES.get(key(label),key(label))
 if normalized in SEARCH:return SEARCH[normalized]
 if 'aceleracion' in normalized or 'acelerar' in normalized:
  return 'car accelerating away' if 'retirada' in normalized else 'car acceleration'
 # Search endpoint admits at most 150 characters; editorial descriptions may be longer.
 return label.strip()[:150].rsplit(' ',1)[0] if len(label.strip())>150 else label.strip()


def main():
 from . import main as m
 return m


def recommendations(p):
 segments={s['id']:(ch,s) for ch in p['chapters'] for s in ch['segments'] if included(s)}
 occurrences={}
 for action in p.get('manuscript_reviews',[]):
  if action.get('category')!='sound' or action.get('undone_at'):continue
  evidence=action.get('evidence',{});sid=evidence.get('segment_id')
  label=str(evidence.get('label','')).strip()
  if not label or sid not in segments:continue
  ch,s=segments[sid];quote=str(evidence.get('cue') or evidence.get('context_text') or '').strip()
  if quote and key(quote) not in key(s['text']):continue
  normalized=ALIASES.get(key(label),key(label))
  occurrence=(normalized,sid,key(quote))
  occurrences[occurrence]=(action.get('decision'),label,normalized,ch,s,quote)
 groups={}
 for decision,label,normalized,ch,s,quote in occurrences.values():
  if decision!='confirm':continue
  gid=hashlib.sha256(normalized.encode()).hexdigest()[:24]
  group=groups.setdefault(gid,{'id':gid,'label':'Mar / océano' if normalized=='mar' else label,
    'query':search_query(label),'locations':[]})
  group['locations'].append({'chapter':ch['title'],'scene':s.get('scene',1),'segment_id':s['id'],'text':s['text'][:350],'quote':quote})
 links=p.get('sound_checklist_links',{})
 for g in groups.values():
  sound=next((s for s in p.get('sound_effects',[]) if s['id']==links.get(g['id'],{}).get('sound_id')),None)
  path=safe_file(main().DATA,sound.get('file')) if sound else None
  saved=bool(path and path.suffix=='.wav' and path.is_file())
  g.update(dismissed=g['id'] in p.get('sound_checklist_dismissed',[]),completed=saved,sound_id=sound['id'] if saved else None,sound_name=sound['name'] if saved else None,count=len(g['locations']))
 return sorted(groups.values(),key=lambda g:(g['completed'],key(g['label'])))


@router.get('')
def checklist(pid:str):
 with main().lock:p=main().get(pid)
 groups=recommendations(p)
 return {'items':groups,'total':len(groups),'dismissed':sum(g['dismissed'] for g in groups),'completed':sum(g['completed'] and not g['dismissed'] for g in groups),'pending':sum(not g['completed'] and not g['dismissed'] for g in groups)}


class Link(BaseModel):
 sound_id:str=Field(min_length=1,max_length=80)


@router.put('/{gid}')
def link(pid:str,gid:str,body:Link):
 m=main()
 with m.lock:
  p=m.get(pid)
  if not any(g['id']==gid for g in recommendations(p)):raise HTTPException(404,'Esta recomendación ya no está vigente. Actualiza la lista.')
  sound=next((s for s in p.get('sound_effects',[]) if s['id']==body.sound_id),None)
  path=safe_file(m.DATA,sound.get('file')) if sound else None
  if not path or path.suffix!='.wav' or not path.is_file():raise HTTPException(409,'Elige un sonido guardado y disponible en la biblioteca de este proyecto.')
  p.setdefault('sound_checklist_links',{})[gid]={'sound_id':body.sound_id,'linked_at':now()};m.save(p)
 return checklist(pid)


@router.delete('/{gid}')
def unlink(pid:str,gid:str):
 m=main()
 with m.lock:
  p=m.get(pid);p.setdefault('sound_checklist_links',{}).pop(gid,None);m.save(p)
 return checklist(pid)


class Selection(BaseModel):
 dismissed:bool


@router.patch('/{gid}/selection')
def select_recommendation(pid:str,gid:str,body:Selection):
 m=main()
 with m.lock:
  p=m.get(pid)
  if not any(g['id']==gid for g in recommendations(p)):raise HTTPException(404,'Recomendación no encontrada.')
  ids=set(p.get('sound_checklist_dismissed',[]))
  if body.dismissed:ids.add(gid)
  else:ids.discard(gid)
  p['sound_checklist_dismissed']=sorted(ids)
  # Remove only placements generated by this recommendation, preserve manual placements.
  if body.dismissed:p['sound_cues']=[c for c in p.get('sound_cues',[]) if c.get('recommendation_id')!=gid]
  m.save(p)
 return checklist(pid)


@router.delete('/library/{sound_id}')
def remove_library_sound(pid:str,sound_id:str):
 m=main()
 with m.lock:
  p=m.get(pid)
  if not any(s['id']==sound_id for s in p.get('sound_effects',[])):raise HTTPException(404,'Sonido no encontrado.')
  p['sound_effects']=[s for s in p['sound_effects'] if s['id']!=sound_id]
  p['sound_cues']=[c for c in p.get('sound_cues',[]) if c['sound_id']!=sound_id]
  p['sound_music_drafts']={sid:d for sid,d in p.get('sound_music_drafts',{}).items() if d.get('sound_id')!=sound_id}
  p['sound_checklist_links']={k:v for k,v in p.get('sound_checklist_links',{}).items() if v.get('sound_id')!=sound_id}
  # Keep physical source files: existing exported mixes and other projects may refer to them.
  m.save(p)
 return {'removed':True}


from .sound_project import router as project_sound_router
router.include_router(project_sound_router)

from .sound_upload import router as sound_upload_router
router.include_router(sound_upload_router)


from .sound_scene_review import router as scene_review_router
router.include_router(scene_review_router)

from .sound_discovery import router as discovery_router
router.include_router(discovery_router)
