"""Downward background leveling and speech-driven sidechain; never changes source files."""
import math,re,subprocess
from typing import Literal
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict
from . import sound_mixer as sm
DEFAULT={'enabled':True,'strength':'balanced'}
router=APIRouter(prefix='/api/projects/{pid}/sound-mixer/voice-priority',tags=['Voice priority'])
def resolved(p,scene):
 config=p.get('voice_priority',{})
 return {**DEFAULT,**config.get('chapters',{}).get(scene['chapter_id'],{}),**config.get('scenes',{}).get(scene['id'],{})}
def profile(strength,role):
 music,effect,ratio={'gentle':(-3,0,2),'balanced':(-6,-3,3),'strong':(-9,-6,4)}[strength]
 return (music if role=='music' else effect),ratio

def smooth_profile(strength, role='music'):
 """Return (attack ms, release ms, maximum dry-floor reduction dB).

 Music beds can duck more deeply than foreground transient effects. Existing
 callers that omit role retain the legacy music profile.
 """
 music = {'gentle': (220, 1600, 3), 'balanced': (180, 1400, 6),
          'strong': (140, 1200, 9)}
 effects = {'gentle': (45, 450, 1), 'balanced': (35, 380, 2),
            'strong': (25, 300, 3)}
 return (music if role == 'music' else effects)[strength]


def measure_loudness(path):
 """Read-only EBU R128 integrated loudness and true peak (oversampled).

 Returns None for silent/too-short audio or when FFmpeg cannot measure it;
 never alters or normalizes the source.
 """
 import json
 try:
  result = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(path),
      '-filter_complex', 'ebur128=peak=true:framelog=quiet', '-f', 'null', '-'],
      capture_output=True, timeout=120)
 except (OSError, subprocess.TimeoutExpired):
  return None
 if result.returncode != 0:
  return None
 stderr = result.stderr.decode(errors='replace')
 match = re.search(r'Integrated loudness:\s*I:\s*(-?[\d.]+) LUFS', stderr)
 peak = re.search(r'True peak:\s*Peak:\s*(-?[\d.]+) dBFS', stderr)
 if not match or not peak:
  return None
 integrated, true_peak = float(match.group(1)), float(peak.group(1))
 if not math.isfinite(integrated) or not math.isfinite(true_peak) or integrated < -70:
  return None
 return {'integrated_lufs': integrated, 'true_peak_dbtp': true_peak}

def measure(path):
 try:r=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-i',str(path),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,timeout=120)
 except (OSError,subprocess.TimeoutExpired):raise HTTPException(503,'No se pudo medir el nivel del audio para proteger las voces.') from None
 match=re.search(r'mean_volume:\s*(-?[\d.]+) dB',r.stderr.decode(errors='replace'))
 if r.returncode or not match:raise HTTPException(502,'No se pudo analizar la intensidad del audio. No se generó una mezcla sin protección.')
 value=float(match[1]);return value if math.isfinite(value) else -91

class Settings(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool=True
 strength:Literal['gentle','balanced','strong']='balanced'
class Apply(Settings):
 scope:Literal['chapter','scene']
 target_id:str
 inherit:bool=False
@router.get('')
def get_settings(pid:str):
 with sm.main().lock:p=sm.main().get(pid)
 return {'scenes':[{'id':s['id'],'chapter_id':s['chapter_id'],'title':s['title'],'number':s['number'],'settings':resolved(p,s),'override':s['id'] in p.get('voice_priority',{}).get('scenes',{})} for s in sm.scenes(p)],'chapters':p.get('voice_priority',{}).get('chapters',{}),'default':DEFAULT}
@router.put('')
def save_settings(pid:str,body:Apply):
 if not sm.ACTIVE.acquire(False):raise HTTPException(409,'Espera a que termine la mezcla o producción para ajustar la prioridad de voz.')
 try:
  m=sm.main()
  with m.lock:
   p=m.get(pid)
   if any(r.get('status') in ('queued','running','paused','interrupted') for r in p.get('production_runs',[])):raise HTTPException(409,'Termina la producción pendiente antes de modificar su mezcla.')
   valid={c['id'] for c in p['chapters']} if body.scope=='chapter' else {s['id'] for s in sm.scenes(p)}
   if body.target_id not in valid:raise HTTPException(404,'El capítulo o escena no pertenece al proyecto.')
   key='chapters' if body.scope=='chapter' else 'scenes';config=p.setdefault('voice_priority',{}).setdefault(key,{})
   if body.inherit:config.pop(body.target_id,None)
   else:config[body.target_id]=Settings(enabled=body.enabled,strength=body.strength).model_dump()
   m.save(p)
  return get_settings(pid)
 finally:sm.ACTIVE.release()
