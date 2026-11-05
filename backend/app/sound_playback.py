"""Selectable MP3 copies of an existing WAV master, with estimated and real sizes."""
import shutil
import subprocess
import uuid
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, HTTPException
from . import sound_mixer as sm
from .voice_editor import now

router=APIRouter(tags=['Mixed book playback'])
Quality=Literal['light','balanced','high']
PROFILES={'light':('Ligero',96),'balanced':('Equilibrado',128),'high':('Alta calidad',192)}


def file_for(item,key):
    path=sm.safe_file(sm.main().DATA,item.get(key))
    return path if path and path.is_file() and path.stat().st_size>0 else None


def variant(item,quality):
    # Preserve and reuse the 128 kbps outputs made by version 0.6.6.
    if quality=='balanced':return {'status':item.get('mp3_status'),'file':item.get('mp3_file'),'message':item.get('mp3_message',''),'working_file':item.get('mp3_working_file'),'encoding_started_at':item.get('mp3_encoding_started_at')}
    return item.get('mp3_profiles',{}).get(quality,{})


def converting(item):
    return any(variant(item,q).get('status') in ('queued','running') for q in PROFILES)


def files(item):
    return [item.get('file'),item.get('mp3_file')]+[v.get('file') for v in item.get('mp3_profiles',{}).values()]


def conversion_time_estimate(variant,expected_bytes,written_bytes,current=None):
    if variant.get('status')=='ready':return {'estimated_remaining_seconds':0}
    if variant.get('status')!='running' or expected_bytes<=0 or written_bytes<=0:return {}
    try:
        started=datetime.fromisoformat(variant.get('encoding_started_at',''))
        if started.tzinfo is None:return {}
        elapsed=((current or datetime.now(timezone.utc))-started).total_seconds()
    except (ValueError,TypeError):return {}
    if elapsed<3:return {}
    fraction=min(.999,written_bytes/expected_bytes)
    total=elapsed/fraction
    return {'estimated_total_seconds':round(total),'estimated_remaining_seconds':max(1,round(total-elapsed)),'elapsed_seconds':round(elapsed)}


def options(item):
    result=[];duration=max(0,float(item.get('duration') or 0))
    for q,(label,kbps) in PROFILES.items():
        v=variant(item,q);path=file_for(v,'file');ready=v.get('status')=='ready' and bool(path)
        result.append(dict(id=q,label=label,format='mp3',kbps=kbps,estimated_bytes=round(duration*kbps*1000/8),
            actual_bytes=path.stat().st_size if ready else None,progress_percent=(100 if ready else min(99,round(100*working.stat().st_size/max(1,duration*kbps*1000/8))) if (working:=file_for(v,'working_file')) else 0),ready=ready,status=v.get('status','not_prepared'),message=v.get('message','')))
    for entry in result:
        v=variant(item,entry['id']);working=file_for(v,'working_file')
        entry.update(conversion_time_estimate(v,entry['estimated_bytes'],working.stat().st_size if working else 0))
    path=file_for(item,'file')
    result.append(dict(id='original',label='Original',format='wav',kbps=None,estimated_bytes=path.stat().st_size if path else None,
        actual_bytes=path.stat().st_size if path else None,ready=bool(path) and item['status']=='ready',status=item['status'],message=''))
    return result


def update_variant(pid,mid,quality,**changes):
    m=sm.main()
    with m.lock:
        p=m.get(pid);item=next((x for x in p.get('sound_project_mixes',[]) if x['id']==mid),None)
        if not item:raise HTTPException(404,'Versión no encontrada.')
        if quality=='balanced':item.update({'mp3_'+k:v for k,v in changes.items()})
        else:item.setdefault('mp3_profiles',{}).setdefault(quality,{}).update(changes)
        m.save(p)


@router.post('/{mid}/prepare-mp3',status_code=202)
def prepare_mp3(pid:str,mid:str,tasks:BackgroundTasks,quality:Quality='balanced'):
    from .sound_project import owned
    m=sm.main()
    with m.lock:
        item=owned(pid,mid);v=variant(item,quality)
        if item['status']!='ready':raise HTTPException(409,'Espera a que termine la mezcla WAV.')
        if v.get('status')=='ready' and file_for(v,'file'):return {'status':'ready','already_ready':True,'quality':quality}
        if v.get('status') in ('queued','running'):return {'status':v['status'],'already_running':True,'quality':quality}
    if not shutil.which('ffmpeg'):raise HTTPException(503,'FFmpeg no está disponible.')
    if not sm.ACTIVE.acquire(blocking=False):raise HTTPException(409,'Hay una mezcla o conversión en proceso. Espera a que termine.')
    try:
        with m.lock:
            item=owned(pid,mid)
            if item['status']!='ready':raise HTTPException(409,'La versión cambió. Actualiza la lista.')
            source=file_for(item,'file')
            if not source:raise HTTPException(404,'No se encontró el WAV terminado.')
            stat=source.stat();identity=(stat.st_size,stat.st_mtime_ns)
            update_variant(pid,mid,quality,status='queued',message='',started_at=now())
        tasks.add_task(worker,pid,mid,source,identity,quality)
        return {'status':'queued','already_ready':False,'quality':quality}
    except BaseException:
        sm.ACTIVE.release();raise


def worker(pid,mid,source,identity,quality='balanced',release_active=True):
    output=sm.main().DATA/('book_fx_'+quality+'_'+uuid.uuid4().hex+'.mp3')
    try:
        update_variant(pid,mid,quality,status='running',working_file=output.name,encoding_started_at=now())
        kbps=PROFILES[quality][1]
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
            '-protocol_whitelist','file,pipe','-i',str(source),'-map','0:a:0','-vn',
            '-c:a','libmp3lame','-compression_level','2','-b:a',str(kbps)+'k','-ar','48000','-ac','2','-write_xing','1',str(output)],
            capture_output=True,check=True,timeout=3600)
        if not output.is_file() or output.stat().st_size==0:raise ValueError('empty')
        stat=source.stat()
        if (stat.st_size,stat.st_mtime_ns)!=identity:raise ValueError('source changed')
        update_variant(pid,mid,quality,status='ready',file=output.name,working_file=None,message='',completed_at=now())
    except Exception as exc:
        output.unlink(missing_ok=True)
        message='No se pudo preparar esta calidad. El WAV original se conserva; puedes reintentar.'
        if isinstance(exc,subprocess.TimeoutExpired):message='La conversión superó una hora. El WAV original se conserva.'
        try:update_variant(pid,mid,quality,status='error',working_file=None,message=message)
        except HTTPException:pass
    finally:
        if release_active:sm.ACTIVE.release()
