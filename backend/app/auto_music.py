"""Fill unassigned scenes from classified project music, preserving user choices."""
import copy,collections,uuid
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from . import sound_mixer as sm
from .voice_editor import signature,now

router=APIRouter(prefix='/api/projects/{pid}/sound-mixer/auto-music',tags=['Automatic music'])
MOODS={'ternura':'Romántica','ira':'Ira / enojo','enojo':'Ira / enojo','asombro':'Asombro','suspenso':'Suspenso','euforia':'Alegría','alegría':'Alegría','tristeza':'Tristeza','narrativo suave':'Documental / narrativa'}

def proposal(p,scope=None):
    scenes=sm.directed_scenes(p); sounds={s['id']:s for s in p.get('sound_effects',[])}
    pools=collections.defaultdict(list)
    for s in sounds.values():
        if s.get('media_kind')=='music' and s.get('music_category') not in (None,'','Sin clasificar') and sm.wav_info(s.get('file')):
            pools[s['music_category']].append(s)
    counts=collections.Counter(c['sound_id'] for c in p.get('sound_cues',[]) if c.get('role')=='music' and c.get('active',True))
    decisions={}
    for record in p.get('production_plans',[]):
        for scene in record.get('plan',{}).get('scenes',[]):decisions[scene['scene_id']]=scene.get('decision')
    result=[];previous=None
    for scene in scenes:
        if scope is not None and scene['id'] not in scope:continue
        ids={s['id'] for s in scene['segments']}
        existing=[c for c in p.get('sound_cues',[]) if c.get('role')=='music' and c.get('segment_id') in ids]
        row={'scene_id':scene['id'],'title':scene['title'],'number':scene['number']}
        if existing or p.get('manual_music_choices',{}).get(scene['id']) or p.get('sound_music_drafts',{}).get(scene['id']):
            row.update(status='preserved',reason='Se conserva la música o elección existente.')
            if existing:previous=existing[0]['sound_id']
        elif decisions.get(scene['id'])=='intentional_silence':
            row.update(status='editorial',reason='Silencio intencional indicado en el plan.')
        elif not scene.get('music_suggestion'):
            row.update(status='editorial',reason='Sección sin propuesta musical.')
        elif scene['missing'] or not 0<scene['duration']<=sm.MAX_SCENE_SECONDS:
            row.update(status='pending',reason='Falta narración aprobada o duración válida.')
        else:
            mood=scene['music_suggestion']['mood'];category=MOODS.get(mood,mood);pool=pools.get(category,[])
            row.update(mood=mood,category=category)
            if not pool:row.update(status='pending',reason='No hay música disponible de esta categoría.')
            else:
                chosen=min(pool,key=lambda s:(s['id']==previous,counts[s['id']],s['name'],s['id']))
                counts[chosen['id']]+=1;previous=chosen['id']
                row.update(status='assign',sound_id=chosen['id'],name=chosen['name'])
        result.append(row)
    return result

def apply_rows(p,rows):
    added=0
    for row in rows:
        if row['status']!='assign':continue
        scene=sm.scene_by_id(p,row['scene_id']);duration=scene['duration']
        volume=p.get('sound_chapter_music',{}).get(scene['chapter_id'],{}).get('volume_db',-12)
        body=sm.Cue(role='music',sound_id=row['sound_id'],segment_id=scene['segments'][0]['id'],duration=duration,volume_db=volume,loop=True,fade_in=min(2,duration/3),fade_out=min(3,duration/3))
        item=sm.validate_cue(p,body)
        if len(p.get('sound_cues',[]))>=500:raise HTTPException(409,'Límite de 500 pistas. No se guardaron las asignaciones.')
        item.update(id=uuid.uuid4().hex,updated_at=now(),auto_music=True,music_category=row['category'])
        p.setdefault('sound_cues',[]).append(item);added+=1
    return added

def preview_data(p):
    rows=proposal(p)
    return {'rows':rows,'token':signature({'project':p,'rows':rows}),'counts':dict(collections.Counter(r['status'] for r in rows))}

@router.get('')
def preview(pid:str):
    with sm.main().lock:return preview_data(sm.main().get(pid))

class Apply(BaseModel):
    token:str

@router.post('')
def apply(pid:str,body:Apply):
    if not sm.ACTIVE.acquire(False):raise HTTPException(409,'Espera a que termine la mezcla actual.')
    try:
        with sm.main().lock:
            p=copy.deepcopy(sm.main().get(pid))
            if any(r.get('status') in ('queued','running','paused','interrupted') for r in p.get('production_runs',[])):raise HTTPException(409,'Termina la producción pendiente antes de asignar música.')
            data=preview_data(p)
            if data['token']!=body.token:raise HTTPException(409,'El proyecto cambió. Prepara de nuevo la selección automática.')
            count=apply_rows(p,data['rows']);sm.main().save(p)
            return {'assigned':count,'counts':data['counts']}
    finally:sm.ACTIVE.release()
