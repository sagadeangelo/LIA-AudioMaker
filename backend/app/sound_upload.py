"""Bounded local sound import. No network requests or credential requirements."""
import hashlib
import shutil
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from . import sound_mixer as sm
from .voice_editor import now

router=APIRouter(prefix='/uploads',tags=['User sound effects'])
MAX_BYTES=50*1024*1024
MAX_SECONDS=600
EXTENSIONS={'.wav','.mp3','.ogg','.flac','.m4a','.aac','.webm','.aif','.aiff'}


def available(p,gid):
    from .sound_checklist import recommendations
    if not gid:return
    group=next((g for g in recommendations(p) if g['id']==gid),None)
    if not group:raise HTTPException(409,'La recomendación ya no está disponible. Actualiza la lista.')
    if group['dismissed']:raise HTTPException(409,'Restaura esta recomendación antes de vincular un archivo.')


@router.post('',status_code=201)
def upload(pid:str,file:UploadFile=File(...),name:str=Form('',max_length=200),
           author:str=Form('',max_length=200),origin:str=Form('own',max_length=20),
           license_note:str=Form('',max_length=500),gid:str=Form('',max_length=80),scene_id:str=Form('',max_length=80),kind:Literal['effect','music']=Form('effect'),
           music_category:str=Form('',max_length=100)):
    m=sm.main();output=None
    try:
        # Existing scene/project upload contract remains a fixed set.
        # Direct library uploads (pid=None) allow user-defined genres.
        if pid is not None and music_category not in {'Romántica','Ira / enojo','Asombro','Drama','Suspenso','Acción / épica','Fantasía','Tristeza','Alegría','Calma','Documental / narrativa','Sin clasificar',''}:
            raise HTTPException(422,'La categoría no pertenece al catálogo de escenas. Los géneros propios se guardan desde Biblioteca de medios.')
        with m.lock:
            if pid:
                p=m.get(pid);available(p,gid)
                if scene_id:sm.scene_by_id(p,scene_id)
        filename=(file.filename or '').replace('\\','/').split('/')[-1]
        if Path(filename).suffix.lower() not in EXTENSIONS:
            raise HTTPException(422,'Elige WAV, MP3, OGG, FLAC, M4A, AAC, WEBM o AIFF.')
        if origin not in ('own','external'):raise HTTPException(422,'Elige grabación propia o recurso externo.')
        if origin=='external' and not license_note.strip():
            raise HTTPException(422,'Indica la licencia o permiso del recurso externo para conservarlo en los créditos.')
        if not shutil.which('ffmpeg'):raise HTTPException(503,'FFmpeg no está disponible en el backend.')
        with tempfile.TemporaryDirectory(prefix='lia-own-sfx-') as tmp:
            original=Path(tmp)/('original'+Path(filename).suffix.lower())
            size=0;digest=hashlib.sha256()
            with original.open('wb') as target:
                while True:
                    block=file.file.read(1024*1024)
                    if not block:break
                    size+=len(block)
                    if size>MAX_BYTES:raise HTTPException(413,'El archivo supera 50 MB.')
                    digest.update(block);target.write(block)
            if not size:raise HTTPException(422,'El archivo está vacío.')
            output=m.DATA/('sfx_user_'+uuid.uuid4().hex+'.wav')
            try:
                result=subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-protocol_whitelist','file,pipe',
                    '-format_whitelist','wav,mp3,ogg,flac,mov,aac,matroska,webm,aiff','-i',str(original),'-map','0:a:0','-vn','-t',str(MAX_SECONDS+1),'-ar','48000','-ac','2',
                    '-c:a','pcm_s16le',str(output)],capture_output=True,timeout=60)
            except (OSError,subprocess.TimeoutExpired):
                raise HTTPException(503,'No se pudo convertir el archivo de audio. Comprueba FFmpeg.') from None
            if result.returncode or not output.is_file():raise HTTPException(422,'El archivo no contiene audio compatible o está dañado.')
            try:
                with wave.open(str(output),'rb') as w:duration=w.getnframes()/w.getframerate()
            except (OSError,wave.Error,EOFError,ZeroDivisionError):raise HTTPException(422,'No se pudo leer el sonido convertido.') from None
            if not 0<duration<=MAX_SECONDS:raise HTTPException(422,'El efecto debe durar como máximo 10 minutos.')
        item=dict(id=uuid.uuid4().hex,file=output.name,name=name.strip() or Path(filename).stem[:200],
            author=author.strip() or ('Grabación propia del usuario' if origin=='own' else 'Autor no indicado'),
            media_kind=kind,source='upload',source_url='',license=license_note.strip() or 'Grabación propia',license_url='',
            duration=round(duration,6),origin=origin,original_filename=filename[:255],
            original_sha256=digest.hexdigest(),imported_at=now(),conversion='WAV PCM 48 kHz estéreo')
        if kind=='music' and music_category:item['music_category']=music_category
        if pid is None:
            from .media_library import records,store
            with m.lock:
                existing=next((s for s in records() if s.get('kind')==kind and all(s.get(k)==item[k] for k in ('original_sha256','name','author','license','origin')) and sm.wav_info(s.get('file'))),None)
                if existing:
                    output.unlink(missing_ok=True)
                    return {'sound':existing,'already_saved':True,'linked':False}
                item.update(kind=kind,category=music_category or 'Sin clasificar',classification_saved=True)
                store(item)
                return {'sound':item,'already_saved':False,'linked':False}
        with m.lock:
            p=m.get(pid);available(p,gid)
            if scene_id:sm.scene_by_id(p,scene_id)
            # Identical bytes and credit metadata may be reused; never deduplicate other projects.
            existing=next((s for s in p.get('sound_effects',[]) if s.get('source')=='upload'
                and all(s.get(k)==item[k] for k in ('original_sha256','name','author','license','origin'))
                and sm.wav_info(s.get('file'))),None)
            if existing:
                item=existing
                if kind=='music':
                    item['media_kind']='music'
                    if music_category and item.get('music_category','Sin clasificar')=='Sin clasificar':item['music_category']=music_category
            else:p.setdefault('sound_effects',[]).append(item)
            if gid:p.setdefault('sound_checklist_links',{})[gid]={'sound_id':item['id'],'linked_at':now()}
            if scene_id:p.setdefault('sound_music_drafts',{})[scene_id]={'sound_id':item['id'],'volume_db':p.get('sound_chapter_music',{}).get(sm.scene_by_id(p,scene_id)['chapter_id'],{}).get('volume_db',-12),'updated_at':now()}
            m.save(p)
        if existing:output.unlink(missing_ok=True)
        return {'sound':item,'already_saved':bool(existing),'linked':bool(gid)}
    except BaseException:
        if output:output.unlink(missing_ok=True)
        raise
    finally:file.file.close()
