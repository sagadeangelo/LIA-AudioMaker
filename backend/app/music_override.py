"""Explicit user music replacement; independent of suggestion/draft autosaves."""
import uuid
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from . import sound_mixer as sm
from .voice_editor import now
router=APIRouter(prefix='/api/projects/{pid}/sound-mixer',tags=['Manual music choice'])
class ManualMusic(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 scene_id:str
 sound_id:str
 volume_db:float=Field(ge=-40,le=0)
@router.post('/manual-music')
def replace_music(pid:str,body:ManualMusic):
 if not sm.ACTIVE.acquire(False):raise HTTPException(409,'Espera a que termine la mezcla o producción actual para sustituir la música.')
 try:
  m=sm.main()
  with m.lock:
   p=m.get(pid)
   if any(r.get('status') in ('queued','running','paused','interrupted') for r in p.get('production_runs',[])):raise HTTPException(409,'Termina o reanuda la producción pendiente antes de sustituir la música.')
   scene=sm.scene_by_id(p,body.scene_id)
   if scene['missing']:raise HTTPException(409,'La escena tiene fragmentos sin audio aprobado. Conserva tu elección y termina esos fragmentos antes de aplicarla.')
   if not 0<scene['duration']<=sm.MAX_SCENE_SECONDS:raise HTTPException(409,'La escena necesita narración de hasta 30 minutos para mezclar música.')
   item=sm.validate_cue(p,sm.Cue(role='music',sound_id=body.sound_id,segment_id=scene['segments'][0]['id'],duration=scene['duration'],volume_db=body.volume_db,loop=True,fade_in=min(2,scene['duration']/3),fade_out=min(3,scene['duration']/3)))
   ids={s['id'] for s in scene['segments']}
   retained=[c for c in p.get('sound_cues',[]) if not(c.get('role')=='music' and c.get('segment_id') in ids)]
   if len(retained)>=500:raise HTTPException(409,'Límite de 500 pistas en el proyecto.')
   item.update(id=uuid.uuid4().hex,updated_at=now(),manual_override=True)
   p['sound_cues']=retained+[item]
   levels=p.setdefault('sound_scene_levels',{}).setdefault(scene['id'],{'narration_db':0,'effects_db':0,'music_db':0})
   levels['music_db']=0
   p.setdefault('manual_music_choices',{})[scene['id']]={'sound_id':body.sound_id,'volume_db':body.volume_db,'updated_at':now()}
   p.setdefault('sound_music_drafts',{}).pop(scene['id'],None)
   m.save(p)
   return {'saved':True,'scene_id':scene['id'],'sound_id':body.sound_id,'volume_db':body.volume_db,'cue_id':item['id'],'manual_override':True}
 finally:sm.ACTIVE.release()
