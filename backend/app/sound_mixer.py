"""Scene SFX placement and separate, versioned WAV previews. No TTS calls."""
import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import threading
import uuid
import wave
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text as sql
from .project_cleanup import safe_file
from .scenes import included
from .voice_editor import approved_audio, now

router = APIRouter(prefix='/api/projects/{pid}/sound-mixer', tags=['Sound mixer'])
ACTIVE = threading.Lock()
MAX_SCENE_SECONDS = 1800
MAX_CUES = 16


def main():
    from . import main as m
    return m


def wav_info(name):
    path = safe_file(main().DATA, name)
    if not path or path.suffix != '.wav' or not path.is_file():
        return None
    try:
        with wave.open(str(path), 'rb') as w:
            duration = w.getnframes() / w.getframerate()
        return {'path': path, 'duration': duration} if duration > 0 else None
    except (OSError, ValueError, wave.Error, EOFError, ZeroDivisionError):
        return None


def scenes(project):
    result = []
    for ch in project.get('chapters', []):
        previous = object()
        current = None
        for segment in ch['segments']:
            if not included(segment): continue
            if current is None or previous != segment.get('scene', 1):
                current = {'id': segment['id'], 'chapter_id': ch['id'], 'title': ch['title'],
                           'number': segment.get('scene', 1), 'segments': [], 'duration': 0.0, 'missing': 0}
                result.append(current)
            previous = segment.get('scene', 1)
            audio = wav_info(approved_audio(segment))
            current['segments'].append({'id': segment['id'], 'text': segment['text'][:220],
                'speaker': segment.get('speaker', ''), 'offset': round(current['duration'], 6),
                'duration': round(audio['duration'], 6) if audio else None})
            current['duration'] += audio['duration'] if audio else 0
            if not audio: current['missing'] += 1
    for scene in result:
        scene['levels']=project.get('sound_scene_levels',{}).get(scene['id'],{'narration_db':0,'effects_db':0,'music_db':0})
        scene['duration'] = round(scene['duration'], 6)
        scene['cue_count'] = sum(c.get('active', True) and any(s['id'] == c['segment_id'] for s in scene['segments']) for c in project.get('sound_cues', []))
    return result


def scene_by_id(project, scene_id):
    scene = next((s for s in scenes(project) if s['id'] == scene_id), None)
    if scene is None: raise HTTPException(409, 'La escena cambió o ya no está incluida. Vuelve a seleccionarla.')
    return scene


def source_segments(project, scene):
    ids = {s['id'] for s in scene['segments']}
    return [s for ch in project['chapters'] for s in ch['segments'] if s['id'] in ids]


def scene_cues(project, scene):
    ids = {s['id'] for s in scene['segments']}
    return [c for c in project.get('sound_cues', []) if c['segment_id'] in ids and c.get('active', True)]


def fingerprint(project, scene_id):
    scene = scene_by_id(project, scene_id)
    segments = source_segments(project, scene)
    cues = scene_cues(project, scene)
    sound_ids = {c['sound_id'] for c in cues}
    sounds = [s for s in project.get('sound_effects', []) if s['id'] in sound_ids]
    # Audio files are immutable UUID versions; include file stat to detect removal/replacement.
    files = []
    for name in [approved_audio(s) for s in segments] + [s['file'] for s in sounds]:
        path = safe_file(main().DATA, name)
        stat = path.stat() if path and path.is_file() else None
        files.append((name, stat.st_size if stat else None, stat.st_mtime_ns if stat else None))
    data = {'segments': [{k:s.get(k) for k in ('id','text','voice','speed','revision','audio','versions')} for s in segments],
            'cues': cues, 'sounds': sounds, 'files': files}
    levels=project.get('sound_scene_levels',{}).get(scene_id,{})
    if any(levels.values()):data['levels']=levels
    from .voice_priority import resolved
    data['voice_priority_v2']=resolved(project,scene)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def mix_status(project, mix):
    result = copy.deepcopy(mix)
    if mix['status'] == 'ready':
        try: result['stale'] = fingerprint(project, mix['scene_id']) != mix['fingerprint']
        except HTTPException: result['stale'] = True
        result['exists'] = bool(wav_info(mix.get('file')))
    return result


@router.get('')
def get_mixer(pid: str):
    with main().lock: project = main().get(pid)
    valid_ids = {s['id'] for ch in project['chapters'] for s in ch['segments'] if included(s)}
    cues = [{**c, 'orphaned': c['segment_id'] not in valid_ids} for c in project.get('sound_cues', [])]
    return {'scenes': directed_scenes(project), 'cues': cues,
            'mixes': [mix_status(project, x) for x in reversed(project.get('sound_mixes', []))],
            'sounds': project.get('sound_effects', []), 'music_drafts':project.get('sound_music_drafts',{}),'chapter_music':project.get('sound_chapter_music',{})}


def directed_scenes(project):
    from .sound_direction import music_direction
    result=scenes(project)
    texts={s['id']:s['text'] for ch in project['chapters'] for s in ch['segments']}
    for scene in result:
        ids={s['id'] for s in scene['segments']}
        full_text=' '.join(texts[s['id']] for s in scene['segments'])
        emotions=[a.get('evidence',{}).get('label','') for a in project.get('manuscript_reviews',[]) if a.get('category')=='emotion' and a.get('decision')=='confirm' and not a.get('undone_at') and a.get('evidence',{}).get('segment_id') in ids]
        scene['music_suggestion']=music_direction(scene['title'],full_text,emotions)
    return result


class Cue(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    role: Literal['effect','music'] = 'effect'
    sound_id: str = Field(min_length=1, max_length=80)
    segment_id: str = Field(min_length=1, max_length=80)
    offset: float = Field(default=0, ge=0, le=1800)
    source_start: float = Field(default=0, ge=0, le=600)
    duration: float = Field(default=5, gt=0, le=1800)
    volume_db: float = Field(default=-18, ge=-40, le=0)
    fade_in: float = Field(default=.2, ge=0, le=10)
    fade_out: float = Field(default=.5, ge=0, le=10)
    loop: bool = False
    active: bool = True


def validate_cue(project, body):
    if body.role=='effect' and body.duration>600:raise HTTPException(422,'Un efecto puntual admite hasta 10 minutos; usa Música para un fondo de escena más largo.')
    segment = main().segment(project, body.segment_id)
    if not included(segment): raise HTTPException(409, 'El fragmento está excluido. Elige uno incluido.')
    sound = next((s for s in project.get('sound_effects', []) if s['id'] == body.sound_id), None)
    if not sound: raise HTTPException(404, 'El sonido no pertenece a la biblioteca de este proyecto.')
    info = wav_info(sound.get('file'))
    if not info: raise HTTPException(409, 'El WAV del efecto no está disponible.')
    if body.source_start >= info['duration']: raise HTTPException(422, 'El inicio del recorte queda fuera del sonido.')
    if not body.loop and body.duration > info['duration'] - body.source_start + .001:
        raise HTTPException(422, 'La duración excede el audio disponible. Redúcela o activa Repetir.')
    if body.fade_in + body.fade_out > body.duration:
        raise HTTPException(422, 'Los fundidos sumados no pueden superar la duración del efecto.')
    return body.model_dump()


@router.post('/cues')
def add_cue(pid: str, body: Cue):
    m = main()
    with m.lock:
        p = m.get(pid)
        item = validate_cue(p, body)
        if len(p.get('sound_cues', [])) >= 500: raise HTTPException(409, 'Límite de 500 efectos por proyecto; elimina los que no necesites.')
        item.update(id=uuid.uuid4().hex, updated_at=now())
        p.setdefault('sound_cues', []).append(item); m.save(p)
    return item


@router.put('/cues/{cue_id}')
def edit_cue(pid: str, cue_id: str, body: Cue):
    m = main()
    with m.lock:
        p = m.get(pid)
        cue = next((x for x in p.get('sound_cues', []) if x['id'] == cue_id), None)
        if cue is None: raise HTTPException(404, 'Efecto no encontrado.')
        item = validate_cue(p, body); cue.update(item, updated_at=now()); m.save(p)
    return cue


@router.delete('/cues/{cue_id}')
def delete_cue(pid: str, cue_id: str):
    m = main()
    with m.lock:
        p = m.get(pid)
        if not any(c['id'] == cue_id for c in p.get('sound_cues', [])): raise HTTPException(404, 'Efecto no encontrado.')
        p['sound_cues'] = [c for c in p['sound_cues'] if c['id'] != cue_id]; m.save(p)
    return {'removed': True}


class Render(BaseModel):
    scene_id: str = Field(min_length=1, max_length=80)


def prepare(project, scene_id):
    scene = scene_by_id(project, scene_id)
    if scene['missing']: raise HTTPException(409, f'Faltan {scene["missing"]} audios aprobados en esta escena. Genéralos o apruébalos primero.')
    if not 0 < scene['duration'] <= MAX_SCENE_SECONDS: raise HTTPException(422, 'La mezcla de prueba admite escenas de hasta 30 minutos.')
    if len(scene['segments']) > 200: raise HTTPException(422, 'Divide esta escena: el máximo de prueba es 200 fragmentos.')
    cues = scene_cues(project, scene)
    if not cues: raise HTTPException(409, 'Asigna al menos un efecto activo a esta escena.')
    if len(cues) > MAX_CUES: raise HTTPException(422, 'La mezcla admite hasta 16 efectos activos por escena.')
    for cue in cues:
        validate_cue(project, Cue(**{k:v for k,v in cue.items() if k in Cue.model_fields}))
        anchor = next(s for s in scene['segments'] if s['id'] == cue['segment_id'])
        if cue['offset'] >= anchor['duration']:
            raise HTTPException(409, 'Un efecto empieza después de que termina su fragmento. Ajusta su retraso.')
        if anchor['offset'] + cue['offset'] + cue['duration'] > scene['duration'] + .001:
            raise HTTPException(409, 'Un efecto rebasa el final de la escena. Reduce su duración.')
    return scene


def update_mix(pid, mid, **changes):
    m = main()
    with m.lock:
        p = m.get(pid)
        mix = next((x for x in p.get('sound_mixes', []) if x['id'] == mid), None)
        if mix is None: raise HTTPException(404, 'Mezcla no encontrada.')
        mix.update(changes); m.save(p)


@router.post('/mixes', status_code=202)
def start_mix(pid: str, body: Render, tasks: BackgroundTasks):
    if not shutil.which('ffmpeg'): raise HTTPException(503, 'FFmpeg no está disponible en el backend.')
    if not ACTIVE.acquire(blocking=False): raise HTTPException(409, 'Ya hay una mezcla en proceso. Espera a que termine.')
    try:
        m = main()
        with m.lock:
            p = m.get(pid); scene = prepare(p, body.scene_id)
            if len(p.get('sound_mixes', [])) >= 20: raise HTTPException(409, 'Conserva hasta 20 mezclas; elimina una versión anterior antes de crear otra.')
            mix = {'id': uuid.uuid4().hex, 'scene_id': body.scene_id, 'title': f'{scene["title"]} · escena {scene["number"]}',
                   'status':'queued', 'created_at':now(), 'duration':scene['duration'], 'fingerprint': fingerprint(p, body.scene_id)}
            p.setdefault('sound_mixes', []).append(mix); m.save(p)
            snapshot = copy.deepcopy(p)
        tasks.add_task(worker, pid, mix['id'], snapshot, scene)
        return mix
    except BaseException:
        ACTIVE.release(); raise


def ffmpeg(args):
    try:
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',*args], check=True, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired: raise HTTPException(504, 'La mezcla excedió el tiempo permitido.') from None
    except (OSError, subprocess.CalledProcessError): raise HTTPException(502, 'No se pudo mezclar el audio. Comprueba que los WAV estén disponibles y sean válidos.') from None


def max_simultaneous_cues(cues, scene, selected_role):
    """Peak number of overlapping cues of a role, not total cues in scene.

    Interval ends are exclusive. This is used only for conservative headroom;
    actual gain and ducking remain unchanged.
    """
    offsets = {s['id']: s['offset'] for s in scene['segments']}
    events = []
    for cue in cues:
        role = 'music' if cue.get('role') == 'music' else 'effect'
        if role != selected_role or cue['segment_id'] not in offsets:
            continue
        start = offsets[cue['segment_id']] + cue['offset']
        end = start + cue['duration']
        events.extend(((start, 1), (end, -1)))
    concurrent = peak = 0
    for _, change in sorted(events, key=lambda item: (item[0], item[1])):
        concurrent += change
        peak = max(peak, concurrent)
    return max(1, peak)


def render_scene(project, scene, folder, output):
    segments = source_segments(project, scene)
    # Normalize each approved input first: scene clips may use different TTS sample rates.
    for i, segment in enumerate(segments):
        info = wav_info(approved_audio(segment))
        if not info: raise HTTPException(409, 'Un audio aprobado dejó de estar disponible.')
        ffmpeg(['-i', str(info['path']), '-map','0:a:0','-vn','-ar','48000','-ac','2','-c:a','pcm_s16le',str(folder/f'n_{i}.wav')])
    listing = folder/'concat.txt'
    listing.write_text(''.join(f"file 'n_{i}.wav'\n" for i in range(len(segments))))
    narration = folder/'narration.wav'
    ffmpeg(['-f','concat','-safe','1','-i',str(listing),'-c:a','pcm_s16le',str(narration)])
    command = ['-i', str(narration)]
    levels=project.get('sound_scene_levels',{}).get(scene['id'],{})
    cues = scene_cues(project, scene)
    from .voice_priority import resolved,measure,profile,smooth_profile
    priority=resolved(project,scene);protect=priority['enabled'] and bool(cues)
    voice_mean=measure(narration) if protect else -91
    protect=protect and voice_mean>-65
    voice_gain=levels.get('narration_db',0)
    if protect:
        filters=[f'[0:a]volume={voice_gain}dB,asplit={len(cues)+1}[narr]'+''.join(f'[det{i}]' for i in range(1,len(cues)+1))]
    else:filters=[f'[0:a]volume={voice_gain}dB[narr]']
    credits = []
    for i, cue in enumerate(cues, 1):
        sound = next(s for s in project['sound_effects'] if s['id'] == cue['sound_id'])
        info = wav_info(sound['file'])
        if not info: raise HTTPException(409, 'Un sonido dejó de estar disponible.')
        clip = folder/f'fx_{i}.wav'
        clip_duration = min(cue['duration'], info['duration'] - cue['source_start'])
        ffmpeg(['-ss',str(cue['source_start']),'-i',str(info['path']),'-t',str(clip_duration),'-map','0:a:0','-vn','-ar','48000','-ac','2','-c:a','pcm_s16le',str(clip)])
        if cue['loop']: command += ['-stream_loop', '-1']
        command += ['-i', str(clip)]
        start = next(s['offset'] for s in scene['segments'] if s['id'] == cue['segment_id']) + cue['offset']
        gain=cue['volume_db']+levels.get('music_db' if cue.get('role')=='music' else 'effects_db',0)
        if protect:
            import math
            role='music' if cue.get('role')=='music' else 'effect'
            count=max_simultaneous_cues(cues, scene, role)
            gap,ratio=profile(priority['strength'],role)
            ceiling=voice_mean+voice_gain+gap-10*math.log10(max(1,count))
            gain+=min(0,ceiling-(measure(clip)+gain))
        chain = [f'[{i}:a]atrim=duration={cue["duration"]}', 'asetpts=PTS-STARTPTS', f'volume={gain}dB']
        # FFmpeg treats d=0 as its default sample-based fade, not as no fade.
        if cue['fade_in'] > 0: chain.append(f'afade=t=in:d={cue["fade_in"]}')
        if cue['fade_out'] > 0: chain.append(f'afade=t=out:st={max(0,cue["duration"]-cue["fade_out"])}:d={cue["fade_out"]}')
        chain.append(f'adelay={round(start*48000)}S:all=1[fx{i}]')
        filters.append(','.join(chain))
        if protect:
            filters.append(f'[det{i}]volume={min(24,-18-voice_mean-voice_gain)}dB[side{i}]')
            filters.append(f'[fx{i}]apad,atrim=duration={scene["duration"]}[pad{i}]')
            attack,release,max_reduction=smooth_profile(priority['strength'],role)
            # Parallel dry floor bounds voice-triggered attenuation; keep the bed audible.
            floor=10**(-max_reduction/20)
            filters.append(f'[pad{i}]asplit=2[dry{i}][wet{i}]')
            filters.append(f'[wet{i}][side{i}]sidechaincompress=threshold=0.05:ratio={ratio}:attack={attack}:release={release}:knee=8:makeup=1:link=maximum:detection=rms[compressed{i}]')
            filters.append(f'[dry{i}][compressed{i}]amix=inputs=2:weights={floor} {1-floor}:normalize=0:duration=first:dropout_transition=0[duck{i}]')
        credits.append(f'«{sound["name"]}» — {sound["author"]}. {sound["license"]}. {sound["source_url"]}\nLicencia: {sound.get("license_url") or sound.get("license_original", "")}\nAdaptación: recorte, volumen, fundidos y/o repetición en mezcla.\n')
    labels = '[narr]' + ''.join(f'[duck{i}]' if protect else f'[fx{i}]' for i in range(1, len(cues)+1))
    filters.append(labels+f'amix=inputs={len(cues)+1}:duration=first:normalize=0:dropout_transition=0,alimiter=limit=0.95:level=0:latency=1[out]')
    ffmpeg(command+['-filter_complex',';'.join(filters),'-map','[out]','-t',str(scene['duration']),'-ar','48000','-ac','2','-c:a','pcm_s16le',str(output)])
    return '\n'.join(dict.fromkeys(credits))


def worker(pid, mid, project, scene):
    output = main().DATA / ('mix_' + uuid.uuid4().hex + '.wav')
    try:
        update_mix(pid, mid, status='running')
        with tempfile.TemporaryDirectory(prefix='lia-scene-mix-') as folder:
            credits = render_scene(project, scene, Path(folder), output)
        from .voice_priority import measure_loudness
        loudness = measure_loudness(output)
        update_mix(pid, mid, status='ready', file=output.name, credits=credits, completed_at=now(), loudness=loudness)
    except Exception as exc:
        output.unlink(missing_ok=True)
        try: update_mix(pid, mid, status='error', message=exc.detail if isinstance(exc, HTTPException) else 'La mezcla se interrumpió; puedes volver a generarla.')
        except HTTPException: pass  # project may have been removed while rendering
    finally:
        ACTIVE.release()


def owned_mix(pid, mid):
    project = main().get(pid)
    mix = next((x for x in project.get('sound_mixes', []) if x['id'] == mid), None)
    if mix is None: raise HTTPException(404, 'Mezcla no encontrada en este proyecto.')
    return mix


@router.get('/mixes/{mid}/audio')
def mix_audio(pid: str, mid: str):
    mix = owned_mix(pid, mid)
    if mix['status'] != 'ready': raise HTTPException(409, 'La mezcla aún no está lista.')
    info = wav_info(mix.get('file'))
    if not info: raise HTTPException(404, 'No se encontró el WAV de la mezcla.')
    return FileResponse(info['path'], media_type='audio/wav', filename=f'LIA_escena_mezcla_{mid[:8]}.wav')


@router.get('/mixes/{mid}/credits')
def mix_credits(pid: str, mid: str):
    mix = owned_mix(pid, mid)
    return PlainTextResponse(mix.get('credits', ''), headers={'Content-Disposition':f'attachment; filename="LIA_creditos_{mid[:8]}.txt"'})


@router.delete('/mixes/{mid}')
def delete_mix(pid: str, mid: str):
    m = main()
    with m.lock:
        p = m.get(pid); mix = next((x for x in p.get('sound_mixes', []) if x['id'] == mid), None)
        if mix is None: raise HTTPException(404, 'Mezcla no encontrada.')
        if mix['status'] in ('queued', 'running'): raise HTTPException(409, 'Espera a que termine esta mezcla.')
        path = safe_file(m.DATA, mix.get('file'))
        if path: path.unlink(missing_ok=True)
        p['sound_mixes'] = [x for x in p['sound_mixes'] if x['id'] != mid];m.save(p)
    return {'removed':True}


def recover_mixes():
    m = main()
    with m.engine.begin() as conn:
        for pid, payload in list(conn.execute(sql('SELECT id,payload FROM projects'))):
            p = json.loads(payload); changed = False
            for mix in p.get('sound_mixes', []) + p.get('sound_project_mixes', []) + list(p.get('sound_scene_previews',{}).values()) + p.get('sound_scene_exports',[]):
                for profile in mix.get('mp3_profiles',{}).values():
                    if profile.get('status') in ('queued','running'):
                        profile.update(status='error',message='La conversión se interrumpió al reiniciar. El WAV se conserva; puedes reintentar.');changed=True
                if mix.get('mp3_status') in ('queued','running'):
                    mix.update(mp3_status='error',mp3_message='La conversión MP3 se interrumpió al reiniciar. El WAV se conserva; puedes reintentar.');changed=True
                if mix['status'] in ('queued', 'running'):
                    mix.update(status='error', message='El backend se reinició durante la mezcla. Vuelve a generarla.');changed=True
            if changed: conn.execute(sql('UPDATE projects SET payload=:p WHERE id=:id'), {'p':json.dumps(p,ensure_ascii=False),'id':pid})


class SceneLevels(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    narration_db:float=Field(default=0,ge=-24,le=6)
    effects_db:float=Field(default=0,ge=-24,le=6)
    music_db:float=Field(default=0,ge=-24,le=6)


@router.put('/scenes/{sid}/levels')
def save_levels(pid:str,sid:str,body:SceneLevels):
    m=main()
    with m.lock:
        p=m.get(pid);scene_by_id(p,sid)
        p.setdefault('sound_scene_levels',{})[sid]=body.model_dump();m.save(p)
    return body.model_dump()


class MusicBed(BaseModel):
    scene_id:str=Field(min_length=1,max_length=80)
    sound_id:str=Field(min_length=1,max_length=80)
    volume_db:float|None=Field(default=None,ge=-40,le=0)


@router.post('/music-bed')
def music_bed(pid:str,body:MusicBed):
    from .sound_direction import editorial
    m=main()
    with m.lock:
        p=m.get(pid);scene=scene_by_id(p,body.scene_id)
        if editorial(scene['title']):raise HTTPException(409,'Esta sección editorial no recibe una música sugerida automáticamente. Puedes usar el mezclador manual si lo necesitas.')
        if scene['missing'] or not 0<scene['duration']<=MAX_SCENE_SECONDS:raise HTTPException(409,'La música de fondo requiere una escena de hasta 30 minutos con narración aprobada.')
        duration=scene['duration']
        item=validate_cue(p,Cue(role='music',sound_id=body.sound_id,segment_id=scene['segments'][0]['id'],duration=duration,
            volume_db=body.volume_db if body.volume_db is not None else p.get('sound_chapter_music',{}).get(scene['chapter_id'],{}).get('volume_db',-12),loop=True,fade_in=min(2,duration/3),fade_out=min(3,duration/3)))
        ids={s['id'] for s in scene['segments']}
        retained=[c for c in p.get('sound_cues',[]) if not (c.get('role')=='music' and c['segment_id'] in ids)]
        if len(retained)>=500:raise HTTPException(409,'Límite de 500 colocaciones por proyecto.')
        item.update(id=uuid.uuid4().hex,updated_at=now());p['sound_cues']=retained+[item]
        p.setdefault('sound_music_drafts',{}).pop(body.scene_id,None);m.save(p)
    return item


class MusicDraft(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    sound_id:str=Field(min_length=1,max_length=80)
    volume_db:float|None=Field(default=None,ge=-40,le=0)


@router.put('/scenes/{sid}/music-draft')
def save_music_draft(pid:str,sid:str,body:MusicDraft):
    m=main()
    with m.lock:
        p=m.get(pid);scene=scene_by_id(p,sid)
        sound=next((s for s in p.get('sound_effects',[]) if s['id']==body.sound_id),None)
        if not sound or not wav_info(sound.get('file')):raise HTTPException(409,'La pista no está disponible en la biblioteca de este proyecto.')
        item={**body.model_dump(),'volume_db':body.volume_db if body.volume_db is not None else p.get('sound_chapter_music',{}).get(scene['chapter_id'],{}).get('volume_db',-12),'updated_at':now()}
        p.setdefault('sound_music_drafts',{})[sid]=item;m.save(p)
    return item


@router.delete('/scenes/{sid}/music-draft')
def clear_music_draft(pid:str,sid:str):
    m=main()
    with m.lock:
        p=m.get(pid);scene_by_id(p,sid)
        p.setdefault('sound_music_drafts',{}).pop(sid,None);m.save(p)
    return {'removed':True}


class LibraryClassification(BaseModel):
    model_config = ConfigDict(extra='forbid')
    media_kind: Literal['music','effect']
    music_category: Literal['Romántica','Ira / enojo','Asombro','Drama','Suspenso','Acción / épica','Fantasía','Tristeza','Alegría','Calma','Documental / narrativa','Sin clasificar'] = 'Sin clasificar'

@router.put('/library/{sound_id}/classification')
def classify_library(pid:str,sound_id:str,body:LibraryClassification):
    m=main()
    with m.lock:
        p=m.get(pid)
        item=next((s for s in p.get('sound_effects',[]) if s['id']==sound_id),None)
        if item is None:raise HTTPException(404,'Recurso no encontrado en este proyecto.')
        item['media_kind']=body.media_kind
        item['music_category']=body.music_category
        m.save(p)
        return {'sound':item}


class ChapterMusicVolume(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    volume_db:float=Field(ge=-40,le=0)

@router.put('/chapters/{chapter_id}/music-volume')
def chapter_music_volume(pid:str,chapter_id:str,body:ChapterMusicVolume):
    m=main()
    if not ACTIVE.acquire(False):raise HTTPException(409,'Espera a que termine la mezcla o producción activa.')
    try:
        with m.lock:
            p=m.get(pid)
            if any(r.get('status') in ('queued','running','paused','interrupted','error') for r in p.get('production_runs',[])):
                raise HTTPException(409,'Hay una producción sin terminar. Complétala antes de cambiar el volumen; una edición impediría reanudarla.')
            ch=next((ch for ch in p['chapters'] if ch['id']==chapter_id),None)
            if ch is None:raise HTTPException(404,'Capítulo no encontrado en este proyecto.')
            ids={x['id'] for x in ch['segments']};chapter_scenes=[sc for sc in scenes(p) if sc['chapter_id']==chapter_id]
            affected=0
            for cue in p.get('sound_cues',[]):
                if cue.get('role')=='music' and cue.get('segment_id') in ids:
                    cue.update(volume_db=body.volume_db,updated_at=now());affected+=1
            for sc in chapter_scenes:
                levels=p.setdefault('sound_scene_levels',{}).setdefault(sc['id'],{'narration_db':0,'effects_db':0,'music_db':0})
                levels['music_db']=0
                draft=p.get('sound_music_drafts',{}).get(sc['id'])
                if draft:draft.update(volume_db=body.volume_db,updated_at=now())
            p.setdefault('sound_chapter_music',{})[chapter_id]={'volume_db':body.volume_db,'updated_at':now()}
            m.save(p)
            return {'volume_db':body.volume_db,'updated_tracks':affected,'scenes':len(chapter_scenes)}
    finally:ACTIVE.release()
