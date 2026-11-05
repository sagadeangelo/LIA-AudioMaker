"""Apply linked, selected recommendations to existing narration; preserve every source."""
import copy
import hashlib
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from fastapi.responses import FileResponse, PlainTextResponse
from . import sound_mixer as sm
from .voice_editor import now, approved_audio

router=APIRouter(prefix='/project-mixes',tags=['Project sound production'])


def signature(p,scene_ids=None):
    # Ignore output metadata, include source ordering, selections, files and manual edits.
    data={'scenes':[(s['id'],sm.fingerprint(p,s['id'])) for s in sm.scenes(p) if scene_ids is None or s['id'] in scene_ids],
          'links':p.get('sound_checklist_links',{}),'dismissed':p.get('sound_checklist_dismissed',[]),
          'reviews':p.get('manuscript_reviews',[])}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def plan(p):
    from .sound_checklist import recommendations
    snapshot=copy.deepcopy(p)
    # Reconcile generated placements; manual placements remain unchanged.
    manual=[c for c in p.get('sound_cues',[]) if not c.get('recommendation_id')]
    previous={c.get('auto_key'):c for c in p.get('sound_cues',[]) if c.get('auto_key')}
    cues=list(manual);pending=[];placed=0
    scene_list=sm.scenes(p)
    if not scene_list:raise HTTPException(409,'El proyecto no tiene fragmentos incluidos.')
    if any(s['missing'] for s in scene_list):raise HTTPException(409,'Faltan audios aprobados. Completa o aprueba la narración antes de aplicar los sonidos.')
    anchors={s['id']:s for scene in scene_list for s in scene['segments']}
    for group in recommendations(p):
        if group['dismissed']:continue
        if not group['completed']:
            pending.append(group['label']);continue
        sound=next(s for s in p['sound_effects'] if s['id']==group['sound_id'])
        info=sm.wav_info(sound['file'])
        if not info:raise HTTPException(409,'Uno de los sonidos vinculados no está disponible.')
        for sid in dict.fromkeys(l['segment_id'] for l in group['locations']):
            identity=group['id']+':'+sid
            old=previous.get(identity)
            if old and old['sound_id']==sound['id']:
                cues.append(copy.deepcopy(old));placed+=1;continue
            duration=min(5.0,info['duration'],anchors[sid]['duration'])
            if duration<=0:continue
            cues.append(dict(id=uuid.uuid4().hex,auto_key=identity,recommendation_id=group['id'],
                sound_id=sound['id'],segment_id=sid,offset=0,source_start=0,duration=duration,
                volume_db=-18,fade_in=min(.2,duration/3),fade_out=min(.5,duration/3),
                loop=False,active=True,updated_at=now()))
            placed+=1
    if len(cues)>500:raise HTTPException(409,'El proyecto supera el límite de 500 colocaciones de efectos.')
    snapshot['sound_cues']=cues
    for scene in scene_list:
        if sm.scene_cues(snapshot,scene):sm.prepare(snapshot,scene['id'])
    if not any(c.get('active',True) for c in cues):raise HTTPException(409,'Vincula al menos un sonido disponible o añade un efecto manual antes de aplicar.')
    return snapshot,scene_list,pending,placed


@router.get('')
def status(pid:str,response:Response,fast:bool=False):
    response.headers['Cache-Control']='no-store'
    with sm.main().lock:p=sm.main().get(pid)
    result=copy.deepcopy(p.get('sound_project_mixes',[]))
    for mix in result:
        if mix['status']=='ready':
            mix['exists']=bool((path:=sm.safe_file(sm.main().DATA,mix.get('file'))) and path.is_file())
            from .sound_playback import file_for, options
            mix['export_options']=options(mix)
            mix['wav_bytes']=path.stat().st_size if path and path.is_file() else 0
            mp3=file_for(mix,'mp3_file')
            mix['mp3_exists']=bool(mp3)
            mix['mp3_bytes']=mp3.stat().st_size if mp3 else 0
            # Download refresh needs only saved outputs, not a new full-book scan.
            mix['stale_checked']=not fast
            mix['stale']=None if fast else mix.get('fingerprint')!=signature(p,mix.get('scene_ids'))
    return {'mixes':list(reversed(result))}


def update(pid,mid,**changes):
    m=sm.main()
    with m.lock:
        p=m.get(pid)
        item=next((x for x in p.get('sound_project_mixes',[]) if x['id']==mid),None)
        if item is None:raise HTTPException(404,'Versión no encontrada.')
        item.update(changes);m.save(p)


@router.post('',status_code=202)
def apply(pid:str,tasks:BackgroundTasks):
    if not shutil.which('ffmpeg'):raise HTTPException(503,'FFmpeg no está disponible.')
    if not sm.ACTIVE.acquire(blocking=False):raise HTTPException(409,'Hay una mezcla en proceso. Espera a que termine.')
    try:
        m=sm.main()
        with m.lock:
            p=m.get(pid)
            if len(p.get('sound_project_mixes',[]))>=5:raise HTTPException(409,'Conserva hasta cinco versiones con efectos. Quita una anterior para crear otra.')
            snapshot,scenes,pending,placed=plan(p)
            # Repeated click for identical source state reuses the existing finished output.
            fp=signature(snapshot)
            old=next((x for x in p.get('sound_project_mixes',[]) if x['status']=='ready' and x.get('fingerprint')==fp and (path:=sm.safe_file(m.DATA,x.get('file'))) and path.is_file()),None)
            if old:return old
            p['sound_cues']=snapshot['sound_cues']
            item=dict(id=uuid.uuid4().hex,status='queued',created_at=now(),completed_scenes=0,
                total_scenes=len(scenes),placements=placed,skipped=pending,fingerprint=fp,
                duration=sum(s['duration'] for s in scenes))
            p.setdefault('sound_project_mixes',[]).append(item);m.save(p)
            snapshot=copy.deepcopy(p)
        tasks.add_task(worker,pid,item['id'],snapshot,scenes)
        # Worker owns ACTIVE until completion.
        return item
    except BaseException:
        sm.ACTIVE.release();raise
    finally:
        # Fast path did not schedule a worker.
        if 'old' in locals() and old:sm.ACTIVE.release()


def worker(pid,mid,p,scenes):
    output=sm.main().DATA/('book_fx_'+uuid.uuid4().hex+'.wav')
    try:
        update(pid,mid,status='running')
        credits=[]
        with tempfile.TemporaryDirectory(prefix='lia-book-fx-') as folder_name:
            folder=Path(folder_name)
            for i,scene in enumerate(scenes):
                part=folder/f'part_{i}.wav'
                work=folder/f'scene_{i}';work.mkdir()
                if sm.scene_cues(p,scene) or p.get('sound_scene_levels',{}).get(scene['id'],{}).get('narration_db',0):
                    credits.append(sm.render_scene(p,scene,work,part))
                else:
                    segs=sm.source_segments(p,scene)
                    for j,segment in enumerate(segs):
                        info=sm.wav_info(approved_audio(segment))
                        if not info:raise HTTPException(409,'La narración dejó de estar disponible.')
                        sm.ffmpeg(['-i',str(info['path']),'-vn','-ar','48000','-ac','2','-c:a','pcm_s16le',str(work/f'n_{j}.wav')])
                    listing=work/'concat.txt';listing.write_text(''.join(f"file 'n_{j}.wav'\n" for j in range(len(segs))))
                    sm.ffmpeg(['-f','concat','-safe','1','-i',str(listing),'-c:a','pcm_s16le',str(part)])
                update(pid,mid,completed_scenes=i+1)
            listing=folder/'book.txt';listing.write_text(''.join(f"file 'part_{i}.wav'\n" for i in range(len(scenes))))
            # RIFF WAV has a 4 GiB limit: RF64 automatically when necessary.
            sm.ffmpeg(['-f','concat','-safe','1','-i',str(listing),'-c:a','pcm_s16le','-rf64','auto',str(output)])
        update(pid,mid,status='ready',file=output.name,credits='\n'.join(dict.fromkeys(credits)),completed_at=now())
        # Keep the existing WAV available while preparing the usual download.
        from .sound_playback import worker as prepare_playback,update_variant
        update_variant(pid,mid,'balanced',status='queued',message='',started_at=now())
        stat=output.stat()
        prepare_playback(pid,mid,output,(stat.st_size,stat.st_mtime_ns),'balanced',release_active=False)
    except Exception as exc:
        output.unlink(missing_ok=True)
        try:update(pid,mid,status='error',message=exc.detail if isinstance(exc,HTTPException) else 'No se pudo completar la versión con efectos. Puedes volver a intentarlo.')
        except HTTPException:pass
    finally:sm.ACTIVE.release()


def owned(pid,mid):
    p=sm.main().get(pid)
    item=next((x for x in p.get('sound_project_mixes',[]) if x['id']==mid),None)
    if not item:raise HTTPException(404,'Versión no encontrada.')
    return item


@router.get('/{mid}/audio')
def audio(pid:str,mid:str,format:Literal['wav','mp3']='wav',download:bool=False,quality:Literal['light','balanced','high']='balanced'):
    from .sound_playback import file_for, variant
    item=owned(pid,mid)
    if item['status']!='ready':raise HTTPException(409,'La versión todavía no está lista.')
    selected=variant(item,quality) if format=='mp3' else item
    if format=='mp3' and selected.get('status')!='ready':raise HTTPException(409,'Prepara primero la reproducción MP3.')
    path=file_for(selected,'file')
    if not path:raise HTTPException(404,'El archivo no está disponible.')
    return FileResponse(path,media_type='audio/mpeg' if format=='mp3' else 'audio/wav',
        filename=f'LIA_libro_con_efectos_{mid[:8]}_{quality if format=="mp3" else "original"}.{format}',
        content_disposition_type='attachment' if download else 'inline')


@router.get('/{mid}/credits')
def credits(pid:str,mid:str):
    return PlainTextResponse(owned(pid,mid).get('credits',''),headers={'Content-Disposition':'attachment; filename="creditos_sonidos.txt"'})


@router.delete('/{mid}')
def remove(pid:str,mid:str):
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=owned(pid,mid)
        from .sound_playback import converting, files
        if item['status'] in ('queued','running') or converting(item):raise HTTPException(409,'Espera a que termine la mezcla.')
        p['sound_project_mixes']=[x for x in p['sound_project_mixes'] if x['id']!=mid];m.save(p)
    for name in files(item):
        path=sm.safe_file(m.DATA,name)
        if path:path.unlink(missing_ok=True)
    return {'removed':True}


from .sound_playback import router as playback_router
router.include_router(playback_router)
