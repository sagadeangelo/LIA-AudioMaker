"""Audition scenes, explicitly approve current previews, then export their exact audio."""
import copy
import json
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from fastapi import APIRouter,BackgroundTasks,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from . import sound_mixer as sm
from .voice_editor import now

router=APIRouter(prefix='/scene-review',tags=['Scene sound review'])


def path_for(item):
    path=sm.safe_file(sm.main().DATA,item.get('file'))
    return path if path and path.is_file() else None


def current(p,scene_id,preview):
    if not preview or preview.get('status')!='ready' or not path_for(preview):return False
    try:return preview.get('fingerprint')==sm.fingerprint(p,scene_id)
    except HTTPException:return False


def rows(p):
    result=[]
    for scene in sm.scenes(p):
        preview=copy.deepcopy(p.get('sound_scene_previews',{}).get(scene['id']))
        valid=current(p,scene['id'],preview)
        if preview:preview.update(stale=not valid if preview['status']=='ready' else False,exists=bool(path_for(preview)))
        approval=p.get('sound_scene_approvals',{}).get(scene['id'],{})
        approved=bool(valid and approval.get('preview_id')==preview['id'] and approval.get('fingerprint')==preview['fingerprint'])
        cues=sm.scene_cues(p,scene)
        result.append({**scene,'preview':preview,'approved':approved,'effects':[{'id':x['id'],'name':next((s['name'] for s in p.get('sound_effects',[]) if s['id']==x['sound_id']),'No disponible'),'volume_db':x['volume_db'],'duration':x['duration'],'offset':x['offset']} for x in cues]})
    return result


@router.get('')
def status(pid:str):
    with sm.main().lock:p=sm.main().get(pid)
    result=rows(p)
    exports=copy.deepcopy(p.get('sound_scene_exports',[]))
    for item in exports:
        item['exists']=bool(path_for(item))
        item['stale']=any(not current(p,sid,{'status':'ready','file':ref['file'],'fingerprint':ref['fingerprint']}) for sid,ref in item.get('sources',{}).items())
    return {'scenes':result,'approved':sum(s['approved'] for s in result),'total':len(result),'exports':list(reversed(exports))}


@router.post('/prepare')
def prepare_placements(pid:str):
    from .sound_project import plan
    m=sm.main()
    with m.lock:
        p=m.get(pid);snapshot,scenes,pending,placed=plan(p)
        p['sound_cues']=snapshot['sound_cues'];m.save(p)
    return {'placements':placed,'pending':pending,'scenes':len(scenes)}


def validate_scene(p,sid):
    scene=sm.scene_by_id(p,sid)
    if scene['missing']:raise HTTPException(409,'Falta narración aprobada en esta escena.')
    if not 0<scene['duration']<=sm.MAX_SCENE_SECONDS or len(scene['segments'])>200:
        raise HTTPException(422,'La preescucha admite escenas de hasta 30 minutos y 200 fragmentos.')
    if sm.scene_cues(p,scene):sm.prepare(p,sid)
    return scene


@router.post('/{sid}/preview',status_code=202)
def preview(pid:str,sid:str,tasks:BackgroundTasks):
    if not shutil.which('ffmpeg'):raise HTTPException(503,'FFmpeg no está disponible.')
    m=sm.main()
    with m.lock:
        p=m.get(pid);old=p.get('sound_scene_previews',{}).get(sid)
        if current(p,sid,old):return old
    if not sm.ACTIVE.acquire(blocking=False):raise HTTPException(409,'Ya hay una mezcla o conversión en proceso. Espera a que termine.')
    try:
        with m.lock:
            p=m.get(pid);scene=validate_scene(p,sid)
            item={'id':uuid.uuid4().hex,'scene_id':sid,'title':f'{scene["title"]} · escena {scene["number"]}',
                'status':'queued','fingerprint':sm.fingerprint(p,sid),'duration':scene['duration'],'created_at':now()}
            if old and old.get('file'):p.setdefault('sound_scene_preview_history',[]).append(old)
            p.setdefault('sound_scene_previews',{})[sid]=item
            p.setdefault('sound_scene_approvals',{}).pop(sid,None);m.save(p);snapshot=copy.deepcopy(p)
        tasks.add_task(preview_worker,pid,sid,item['id'],snapshot,scene,old)
        return item
    except BaseException:sm.ACTIVE.release();raise


def update_preview(pid,sid,preview_id,**changes):
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=p.get('sound_scene_previews',{}).get(sid)
        if not item or item['id']!=preview_id:raise HTTPException(409,'La preescucha cambió.')
        item.update(changes);m.save(p)


def preview_worker(pid,sid,preview_id,p,scene,old):
    output=sm.main().DATA/('scene_preview_'+uuid.uuid4().hex+'.wav')
    try:
        update_preview(pid,sid,preview_id,status='running')
        with tempfile.TemporaryDirectory(prefix='lia-preview-') as tmp:
            credits=sm.render_scene(p,scene,Path(tmp),output)
        update_preview(pid,sid,preview_id,status='ready',file=output.name,credits=credits,completed_at=now())
        # Old previews may be referenced by exported books: retain their files until project cleanup.
    except Exception as exc:
        output.unlink(missing_ok=True)
        try:update_preview(pid,sid,preview_id,status='error',message=exc.detail if isinstance(exc,HTTPException) else 'No se pudo preparar la preescucha.')
        except HTTPException:pass
    finally:sm.ACTIVE.release()


class Approval(BaseModel):
    preview_id:str=Field(min_length=1,max_length=80)
    approved:bool=True


@router.put('/{sid}/approval')
def approve(pid:str,sid:str,body:Approval):
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=p.get('sound_scene_previews',{}).get(sid)
        if not item or item['id']!=body.preview_id or not current(p,sid,item):
            raise HTTPException(409,'Genera y escucha la preescucha vigente antes de marcarla como revisada.')
        if body.approved:p.setdefault('sound_scene_approvals',{})[sid]={'preview_id':item['id'],'fingerprint':item['fingerprint'],'approved_at':now()}
        else:p.setdefault('sound_scene_approvals',{}).pop(sid,None)
        m.save(p)
    return {'approved':body.approved}


@router.get('/{sid}/audio')
def audio(pid:str,sid:str,download:bool=False):
    with sm.main().lock:p=sm.main().get(pid)
    item=p.get('sound_scene_previews',{}).get(sid)
    if not current(p,sid,item):raise HTTPException(409,'La preescucha no está lista o cambió. Vuelve a generarla.')
    return FileResponse(path_for(item),media_type='audio/wav',filename='LIA_escena_'+sid[:8]+'.wav',content_disposition_type='attachment' if download else 'inline')


class Selection(BaseModel):
    scene_ids:list[str]=Field(min_length=1,max_length=2000)
    preview_ids:dict[str,str]


def selected(p,body):
    if len(set(body.scene_ids))!=len(body.scene_ids):raise HTTPException(422,'La selección contiene escenas repetidas.')
    requested=set(body.scene_ids);ordered=[];sources={}
    for row in rows(p):
        if row['id'] not in requested:continue
        if not row['approved'] or row['preview']['id']!=body.preview_ids.get(row['id']):
            raise HTTPException(409,'Una escena seleccionada cambió o no está revisada. Actualiza y escucha su preescucha.')
        ordered.append(row);sources[row['id']]=row['preview']
    if len(ordered)!=len(requested):raise HTTPException(409,'Una escena seleccionada ya no está incluida.')
    return ordered,sources


@router.post('/export/{mode}',status_code=202)
def export(pid:str,mode:str,body:Selection,tasks:BackgroundTasks):
    from .sound_project import signature
    if mode not in ('zip','book'):raise HTTPException(422,'Elige ZIP de escenas o libro unido.')
    if not sm.ACTIVE.acquire(blocking=False):raise HTTPException(409,'Hay una mezcla o conversión en proceso. Espera a que termine.')
    try:
        m=sm.main()
        with m.lock:
            p=m.get(pid);ordered,sources=selected(p,body)
            field='sound_project_mixes' if mode=='book' else 'sound_scene_exports'
            if len(p.get(field,[]))>=5:raise HTTPException(409,'Conserva hasta cinco exportaciones de este tipo; quita una anterior antes de crear otra.')
            ids=[s['id'] for s in ordered]
            item={'id':uuid.uuid4().hex,'status':'queued','created_at':now(),'scene_ids':ids,'sources':sources,
                'duration':sum(s['duration'] for s in ordered),'completed_scenes':0,'total_scenes':len(ids),
                'placements':sum(s['cue_count'] for s in ordered),'skipped':[],
                'is_complete_book':len(ordered)==len(sm.scenes(p)),'fingerprint':signature(p,ids)}
            p.setdefault(field,[]).append(item);m.save(p)
        tasks.add_task(export_worker,pid,item['id'],mode,copy.deepcopy(item))
        return item
    except BaseException:sm.ACTIVE.release();raise


def update_export(pid,eid,mode,**changes):
    from .sound_project import update
    if mode=='book':return update(pid,eid,**changes)
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=next((x for x in p.get('sound_scene_exports',[]) if x['id']==eid),None)
        if not item:raise HTTPException(404,'Exportación no encontrada.')
        item.update(changes);m.save(p)


def export_worker(pid,eid,mode,item):
    output=sm.main().DATA/('reviewed_'+uuid.uuid4().hex+('.wav' if mode=='book' else '.zip'))
    try:
        update_export(pid,eid,mode,status='running')
        sources=[item['sources'][sid] for sid in item['scene_ids']]
        credits='\n'.join(dict.fromkeys(x.get('credits','') for x in sources))
        if mode=='zip':
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
                for i,source in enumerate(sources):
                    path=path_for(source)
                    if not path:raise HTTPException(409,'Una preescucha dejó de estar disponible.')
                    z.write(path,f'{i+1:03d}_escena_{source["scene_id"][:8]}.wav')
                    update_export(pid,eid,mode,completed_scenes=i+1)
                z.writestr('creditos.txt',credits)
                z.writestr('escenas.json',json.dumps([{'position':i+1,'title':s['title'],'scene_id':s['scene_id'],'duration':s['duration']} for i,s in enumerate(sources)],ensure_ascii=False,indent=2))
        else:
            with tempfile.TemporaryDirectory(prefix='lia-reviewed-book-') as tmp:
                tmp=Path(tmp);listing=tmp/'concat.txt'
                # UUID filenames are validated direct children; copy no audio through the browser.
                paths=[path_for(s) for s in sources]
                if any(path is None for path in paths):raise HTTPException(409,'Una preescucha dejó de estar disponible.')
                listing.write_text(''.join("file '"+str(path)+"'\n" for path in paths))
                sm.ffmpeg(['-f','concat','-safe','0','-i',str(listing),'-c:a','pcm_s16le','-rf64','auto',str(output)])
            update_export(pid,eid,mode,completed_scenes=len(sources))
        update_export(pid,eid,mode,status='ready',file=output.name,credits=credits,completed_at=now())
    except Exception as exc:
        output.unlink(missing_ok=True)
        try:update_export(pid,eid,mode,status='error',message=exc.detail if isinstance(exc,HTTPException) else 'No se pudo exportar la selección revisada.')
        except HTTPException:pass
    finally:sm.ACTIVE.release()


@router.get('/exports/{eid}/download')
def download(pid:str,eid:str):
    with sm.main().lock:p=sm.main().get(pid)
    item=next((x for x in p.get('sound_scene_exports',[]) if x['id']==eid),None)
    if not item or item['status']!='ready' or not path_for(item):raise HTTPException(404,'El ZIP no está disponible.')
    return FileResponse(path_for(item),media_type='application/zip',filename='LIA_escenas_revisadas_'+eid[:8]+'.zip')


@router.delete('/exports/{eid}')
def delete_export(pid:str,eid:str):
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=next((x for x in p.get('sound_scene_exports',[]) if x['id']==eid),None)
        if not item:raise HTTPException(404,'Exportación no encontrada.')
        if item['status'] in ('queued','running'):raise HTTPException(409,'Espera a que termine la exportación.')
        p['sound_scene_exports']=[x for x in p['sound_scene_exports'] if x['id']!=eid];m.save(p)
    path=path_for(item)
    if path:path.unlink(missing_ok=True)
    return {'removed':True}
