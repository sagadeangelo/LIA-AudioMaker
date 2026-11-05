"""Non-destructive pronunciation editing, approved versions and persisted jobs.

No schema replacement: additive JSON fields in existing projects/jobs tables.
One backend process, one editor worker. No external TTS call holds the project lock.
"""
import hashlib
import json
import re
import threading
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text as sql

from .scenes import included
from .tts_provider import provider_for_voice

router = APIRouter(prefix='/api/projects/{pid}/voice-editor', tags=['Voice Editor'])
ACTIVE = threading.Lock()


def context():
    from . import main
    return main


def now():
    return datetime.now(timezone.utc).isoformat()


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Rule(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    pronunciation: str = Field(min_length=1, max_length=300)
    language: str = Field(default='es', pattern=r'^es(?:-MX|-ES)?$')
    provider: str = Field(default='all', pattern=r'^(all|kokoro|azure)$')
    character_id: str | None = None
    active: bool = True


class Preview(BaseModel):
    scope: str = Field(default='segment', pattern=r'^(segment|chapter|project)$')
    segment_id: str | None = None
    chapter_id: str | None = None
    # Exact complete alternative TTS text, never saved into the manuscript.
    override_text: str | None = Field(default=None, min_length=1, max_length=20000)


class Start(Preview):
    preview_token: str
    confirmed: bool = False


def rendered(project, segment):
    provider = provider_for_voice(segment['voice'])
    from .narrative import key
    character_id = segment.get('character_id') or next((c['id'] for c in project.get('characters', []) if key(c['name']) == key(segment.get('speaker', ''))), None)
    rules = [r for r in project.get('pronunciation_rules', [])
             if r['active'] and r['provider'] in ('all', provider)
             and (not r.get('character_id') or r['character_id'] == character_id)]
    # Character-specific entries override global ones; longest matches win.
    chosen = {}
    for r in sorted(rules, key=lambda r: (bool(r.get('uniform')), bool(r.get('character_id')))):
        chosen[r['original'].casefold()] = r
    for override in project.get('pronunciation_voice_overrides', []):
        if override['voice'] == segment['voice']:
            chosen[override['original'].casefold()] = override
    if not chosen:
        return segment['text']
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(r['original']) for r in sorted(chosen.values(), key=lambda r: -len(r['original']))) + r')(?!\w)', re.IGNORECASE)
    return pattern.sub(lambda m: chosen[m.group().casefold()]['pronunciation'], segment['text'])


def snapshot(segment):
    return {k: segment.get(k) for k in ('text', 'voice', 'speed', 'character_id', 'revision', 'excluded', 'review')}


def prepare(project, body):
    if body.override_text is not None and (body.scope != 'segment' or not body.override_text.strip()):
        raise HTTPException(422, 'El texto alternativo solo se permite para un fragmento y no puede estar vacío')
    if body.scope == 'segment' and not body.segment_id or body.scope == 'chapter' and not body.chapter_id:
        raise HTTPException(422, 'Falta el fragmento o capítulo del alcance')
    targets = []
    found = body.scope == 'project'
    for ch in project['chapters']:
        if body.scope == 'chapter' and ch['id'] != body.chapter_id:
            continue
        if body.scope == 'chapter':
            found = True
        for s in ch['segments']:
            if body.scope == 'segment' and s['id'] != body.segment_id:
                continue
            if body.scope == 'segment':
                found = True
            if not included(s) or s.get('review'):
                continue
            tts_text = body.override_text if body.override_text is not None else rendered(project, s)
            # For batch requests only regenerate actual pronunciation matches.
            if body.scope != 'segment' and tts_text == s['text']:
                continue
            targets.append({'segment_id': s['id'], 'chapter_id': ch['id'], 'chapter': ch['title'],
                            'speaker': s['speaker'], 'original_text': s['text'], 'tts_text': tts_text,
                            'voice': s['voice'], 'speed': s['speed'], 'snapshot': snapshot(s)})
    if not found:
        raise HTTPException(404, 'Fragmento o capítulo no encontrado')
    return targets


@router.get('/rules')
def rules(pid: str):
    return context().get(pid).get('pronunciation_rules', [])


@router.post('/rules', status_code=201)
def add_rule(pid: str, body: Rule):
    m = context()
    if not body.original.strip() or not body.pronunciation.strip():
        raise HTTPException(422, 'La palabra y su pronunciación no pueden estar vacías')
    with m.lock:
        p = m.get(pid)
        uniform_guard(p, body)
        if body.character_id and not any(c['id'] == body.character_id for c in p['characters']):
            raise HTTPException(422, 'Personaje ajeno al proyecto')
        entry = {'id': str(uuid.uuid4()), **body.model_dump(), 'original': body.original.strip(), 'pronunciation': body.pronunciation.strip()}
        rules = p.setdefault('pronunciation_rules', [])
        if any((r['original'].casefold(), r['provider'], r.get('character_id')) == (entry['original'].casefold(), entry['provider'], entry['character_id']) for r in rules):
            raise HTTPException(409, 'Ya existe esta palabra para ese motor y personaje; desactívala o elimínala antes de sustituirla')
        rules.append(entry)
        m.save(p)
    return entry


@router.put('/rules/{rid}')
def update_rule(pid: str, rid: str, body: Rule):
    m = context()
    if not body.original.strip() or not body.pronunciation.strip():
        raise HTTPException(422, 'La palabra y su pronunciación no pueden estar vacías')
    with m.lock:
        p = m.get(pid)
        rules = p.get('pronunciation_rules', [])
        entry = next((r for r in rules if r['id'] == rid), None)
        if not entry: raise HTTPException(404, 'Entrada no encontrada')
        if body.character_id and not any(c['id'] == body.character_id for c in p['characters']):
            raise HTTPException(422, 'Personaje ajeno al proyecto')
        if any(r['id'] != rid and (r['original'].casefold(), r['provider'], r.get('character_id')) == (body.original.strip().casefold(), body.provider, body.character_id) for r in rules):
            raise HTTPException(409, 'Ya existe esta palabra para ese motor y personaje')
        uniform_guard(p, body, rid)
        entry.update(body.model_dump(), original=body.original.strip(), pronunciation=body.pronunciation.strip())
        m.save(p)
    return entry


@router.patch('/rules/{rid}')
def toggle_rule(pid: str, rid: str, active: bool):
    m = context()
    with m.lock:
        p = m.get(pid)
        r = next((r for r in p.get('pronunciation_rules', []) if r['id'] == rid), None)
        if not r: raise HTTPException(404, 'Entrada no encontrada')
        if active: uniform_guard(p, Rule(**{**r, 'active': True}), rid)
        r['active'] = active
        m.save(p)
    return r


@router.delete('/rules/{rid}')
def delete_rule(pid: str, rid: str):
    m = context()
    with m.lock:
        p = m.get(pid)
        if not any(r['id'] == rid for r in p.get('pronunciation_rules', [])):
            raise HTTPException(404, 'Entrada no encontrada')
        p['pronunciation_rules'] = [r for r in p['pronunciation_rules'] if r['id'] != rid]
        m.save(p)
    return {'status': 'removed'}


@router.post('/preview')
def preview(pid: str, body: Preview):
    p = context().get(pid)
    targets = prepare(p, body)
    return {'targets': targets, 'count': len(targets), 'preview_token': signature(targets)}


def save_job(job):
    m = context()
    with m.engine.begin() as c:
        c.execute(sql('UPDATE jobs SET payload=:payload WHERE id=:id'), {'id': job['id'], 'payload': json.dumps(job, ensure_ascii=False)})


def read_job(pid, jid):
    m = context()
    m.get(pid)
    with m.engine.connect() as c:
        row = c.execute(sql('SELECT payload FROM jobs WHERE id=:id'), {'id': jid}).first()
    job = json.loads(row[0]) if row else None
    if not job or job.get('kind') != 'voice-editor' or job['project_id'] != pid:
        raise HTTPException(404, 'Trabajo no encontrado')
    return job


def public_job(job):
    return {k: v for k, v in job.items() if k != 'targets'}


@router.get('/jobs')
def jobs(pid: str):
    m = context(); m.get(pid)
    with m.engine.connect() as c:
        values = [json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM jobs'))]
    return [public_job(j) for j in values if j.get('kind') == 'voice-editor' and j.get('project_id') == pid][-30:]


@router.post('/jobs', status_code=202)
def start(pid: str, body: Start):
    m = context()
    with m.lock:
        p = m.get(pid)
        targets = prepare(p, body)
        if signature(targets) != body.preview_token:
            raise HTTPException(409, 'La vista previa cambió; vuelve a revisar los fragmentos')
        if not targets: raise HTTPException(409, 'No hay fragmentos elegibles; revisa el contenido y el diccionario')
        if len(targets) > 1 and not body.confirmed:
            raise HTTPException(409, 'Confirma explícitamente la regeneración por lotes')
        if not ACTIVE.acquire(blocking=False):
            raise HTTPException(409, 'Ya hay un trabajo de pronunciación activo')
        job = {'id': str(uuid.uuid4()), 'kind': 'voice-editor', 'project_id': pid,
               'status': 'queued', 'created_at': now(), 'total': len(targets), 'done': 0,
               'errors': [], 'cancel_requested': False, 'targets': targets}
        try:
            with m.engine.begin() as c:
                c.execute(sql('INSERT INTO jobs (id,payload) VALUES (:id,:payload)'), {'id': job['id'], 'payload': json.dumps(job, ensure_ascii=False)})
            threading.Thread(target=worker, args=(pid, job['id']), daemon=True).start()
        except Exception:
            ACTIVE.release(); raise
    return public_job(job)


@router.get('/jobs/{jid}')
def job_status(pid: str, jid: str):
    return public_job(read_job(pid, jid))


@router.post('/jobs/{jid}/cancel')
def cancel(pid: str, jid: str):
    m = context()
    with m.lock:
        j = read_job(pid, jid)
        if j['status'] in ('queued', 'running'):
            j['cancel_requested'] = True; save_job(j)
    return public_job(j)


def worker(pid, jid):
    m = context()
    try:
        with m.lock:
            j = read_job(pid, jid); j['status'] = 'running'; save_job(j)
        for target in j['targets']:
            with m.lock:
                j = read_job(pid, jid)
                if j['cancel_requested']: break
            name = str(uuid.uuid4()) + '.wav'
            path = m.DATA / name
            try:
                from .tts_provider import generate
                result = generate(target['tts_text'], target['voice'], target['speed'], path)
                with wave.open(str(path), 'rb') as w:
                    duration = w.getnframes() / w.getframerate()
                with m.lock:
                    p = m.get(pid); s = m.segment(p, target['segment_id'])
                    version = {'id': str(uuid.uuid4()), 'file': name, 'segment_id': s['id'],
                               'voice': target['voice'], 'speed': target['speed'], 'text': target['tts_text'],
                               'provider': result['provider'], 'created_at': now(), 'duration': duration,
                               'status': 'proposed', 'source_snapshot': target['snapshot']}
                    # Even a concurrent edit cannot replace the active audio.
                    if j.get('incorporate'):
                        normalize_versions(s, m.DATA)
                        version['incorporation_job_id'] = jid
                        version['previous_audio'] = target['old_audio']
                        valid = (snapshot(s) == target['snapshot'] and s.get('audio') == target['old_audio']
                                 and rendered(p, s) == target['tts_text'])
                        if valid:
                            version.update(status='approved', approved_at=now(), activation_revision=s.get('revision', 0)+1)
                            s.update(audio=name, duration=duration, revision=version['activation_revision'])
                        else:
                            version['activation_conflict'] = True
                    s.setdefault('versions', []).append(version); m.save(p)
                    j = read_job(pid, jid); j['done'] += 1
                    if j.get('incorporate'):
                        j['processed'] = j.get('processed', 0) + 1
                        if version['status'] == 'approved': j['incorporated'] += 1
                        else: j['errors'].append({'segment_id': s['id'], 'message': 'El fragmento o su regla cambió; se conservó el audio activo y la propuesta queda para revisión.'})
                    save_job(j)
            except Exception:
                # Keep any generated WAV: never delete a potentially valuable result.
                with m.lock:
                    j = read_job(pid, jid)
                    j['errors'].append({'segment_id': target['segment_id'], 'message': 'No se pudo generar o registrar la propuesta; el audio activo se conserva.'})
                    if j.get('incorporate'): j['processed'] = j.get('processed', 0) + 1
                    save_job(j)
        with m.lock:
            j = read_job(pid, jid)
            j['status'] = 'cancelled' if j['cancel_requested'] else ('completed_with_errors' if j['errors'] else 'completed')
            j['finished_at'] = now(); save_job(j)
    except Exception:
        # A failed job remains visible, with completed proposals preserved.
        with m.lock:
            with m.engine.connect() as c:
                row = c.execute(sql('SELECT payload FROM jobs WHERE id=:id'), {'id': jid}).first()
            if row:
                j = json.loads(row[0]); j['status'] = 'interrupted'; save_job(j)
    finally:
        ACTIVE.release()


def normalize_versions(s, data):
    """Adopt pre-editor audio as approved, without rewriting any WAV."""
    versions = s.setdefault('versions', [])
    if s.get('audio') and not any(v.get('file') == s['audio'] for v in versions):
        versions.append({'file': s['audio'], 'voice': s['voice'], 'speed': s['speed'], 'text': s['text'], 'duration': s.get('duration', 0)})
    for v in versions:
        v.setdefault('id', v['file'])
        v.setdefault('status', 'approved')
        v.setdefault('segment_id', s['id'])
        v.setdefault('created_at', None)  # Do not fabricate historical dates.
        if 'duration' not in v:
            try:
                with wave.open(str(data / v['file']), 'rb') as w: v['duration'] = w.getnframes() / w.getframerate()
            except (OSError, wave.Error, EOFError): v['duration'] = 0
    return versions


@router.get('/segments/{sid}/versions')
def versions(pid: str, sid: str):
    m = context()
    with m.lock:
        p = m.get(pid); s = m.segment(p, sid)
        result = normalize_versions(s, m.DATA); m.save(p)
    return {'active_audio': s.get('audio'), 'versions': result}


@router.post('/segments/{sid}/versions/{vid}/{action}')
def decide(pid: str, sid: str, vid: str, action: str):
    if action not in ('approve', 'reject', 'restore'):
        raise HTTPException(422, 'Acción inválida')
    m = context()
    with m.lock:
        p = m.get(pid); s = m.segment(p, sid)
        versions = normalize_versions(s, m.DATA)
        v = next((v for v in versions if v['id'] == vid), None)
        if not v: raise HTTPException(404, 'Versión no encontrada')
        if action == 'reject':
            if v['file'] == s.get('audio'): raise HTTPException(409, 'No puedes descartar la versión activa')
            if v['status'] != 'proposed': raise HTTPException(409, 'Solo se descartan propuestas')
            v['status'] = 'rejected'
        else:
            if not included(s) or s.get('review'): raise HTTPException(409, 'Restaura y revisa primero el fragmento')
            if action == 'restore' and v['status'] != 'approved': raise HTTPException(409, 'Solo se restauran versiones aprobadas')
            if action == 'approve' and v['status'] != 'proposed': raise HTTPException(409, 'Solo se aprueban propuestas')
            if action == 'approve' and v.get('source_snapshot') != snapshot(s):
                raise HTTPException(409, 'El fragmento cambió desde la propuesta; genera una nueva antes de aprobar')
            from .project_cleanup import safe_file
            path = safe_file(m.DATA, v['file'])
            if path is None or not path.is_file(): raise HTTPException(409, 'Archivo no disponible')
            if not v.get('duration'): raise HTTPException(409, 'Duración de audio no válida')
            v['status'] = 'approved'; v['approved_at'] = now()
            s['audio'] = v['file']; s['duration'] = v['duration']
            if action == 'restore':
                s['voice'] = v.get('voice', s['voice']); s['speed'] = v.get('speed', s['speed'])
            s['revision'] = s.get('revision', 0) + 1
        p.setdefault('voice_editor_history', []).append({'segment_id': sid, 'version_id': vid, 'action': action, 'at': now()})
        m.save(p)
    return p


def approved_audio(segment):
    """Legacy audio is accepted; explicitly unapproved candidates are never exported."""
    name = segment.get('audio')
    v = next((v for v in segment.get('versions', []) if v.get('file') == name), None)
    return name if name and (v is None or v.get('status', 'approved') == 'approved') else None


def recover_jobs():
    """Mark abandoned workers interrupted on process startup; no automatic paid retry."""
    m = context()
    with m.engine.begin() as c:
        rows = list(c.execute(sql('SELECT id,payload FROM jobs')))
        for jid, payload in rows:
            j = json.loads(payload)
            if j.get('kind') == 'voice-editor' and j['status'] in ('queued', 'running'):
                j['status'] = 'interrupted'
                c.execute(sql('UPDATE jobs SET payload=:payload WHERE id=:id'), {'id': jid, 'payload': json.dumps(j, ensure_ascii=False)})

class Audition(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    pronunciation: str = Field(min_length=1, max_length=300)
    phrase: str = Field(default='', max_length=1000)
    voice: str = Field(min_length=1, max_length=100)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    variant: str = Field(default='replacement', pattern=r'^(original|replacement)$')


@router.post('/auditions', status_code=202)
def audition(pid: str, body: Audition):
    """Bounded, isolated audition: no dictionary/casting/version changes."""
    m = context(); m.get(pid)
    if not body.original.strip() or not body.pronunciation.strip():
        raise HTTPException(422, 'Escribe la palabra y la pronunciación de prueba')
    try: provider = provider_for_voice(body.voice)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    source = body.phrase.strip() or body.original.strip()
    pattern = re.compile(r'(?<!\w)' + re.escape(body.original.strip()) + r'(?!\w)', re.IGNORECASE)
    if not pattern.search(source):
        raise HTTPException(422, 'La frase de prueba debe contener la palabra original completa')
    tts_text = pattern.sub(lambda _: body.pronunciation.strip(), source) if body.variant == 'replacement' else source
    if len(tts_text) > 1500:
        raise HTTPException(422, 'Acorta la frase de prueba')
    if not ACTIVE.acquire(blocking=False):
        raise HTTPException(409, 'Espera a que termine la prueba o el lote actual')
    j = {'id': str(uuid.uuid4()), 'kind': 'voice-editor', 'audition': True,
         'project_id': pid, 'status': 'queued', 'created_at': now(), 'total': 1,
         'done': 0, 'errors': [], 'cancel_requested': False, 'targets': [],
         'text': tts_text, 'voice': body.voice, 'speed': body.speed,
         'provider': provider, 'variant': body.variant}
    try:
        with m.engine.begin() as c:
            c.execute(sql('INSERT INTO jobs (id,payload) VALUES (:id,:payload)'), {'id': j['id'], 'payload': json.dumps(j, ensure_ascii=False)})
        threading.Thread(target=audition_worker, args=(pid, j['id']), daemon=True).start()
    except Exception:
        ACTIVE.release(); raise
    return public_job(j)


def audition_worker(pid, jid):
    m = context()
    try:
        with m.lock:
            j = read_job(pid, jid)
            if j['cancel_requested']:
                j['status'] = 'cancelled'; save_job(j); return
            j['status'] = 'running'; save_job(j)
        from .tts_provider import generate
        name = str(uuid.uuid4()) + '.wav'
        path = m.DATA / name
        result = generate(j['text'], j['voice'], j['speed'], path)
        with wave.open(str(path), 'rb') as w:
            duration = w.getnframes() / w.getframerate()
        with m.lock:
            j = read_job(pid, jid)
            j.update(status='completed', done=1, finished_at=now(),
                     result={'file': name, 'duration': duration, 'provider': result['provider']})
            save_job(j)
    except Exception:
        with m.lock:
            j = read_job(pid, jid)
            j.update(status='completed_with_errors', finished_at=now(),
                     errors=[{'message': 'No se pudo generar la prueba. Comprueba que el motor y la voz estén disponibles.'}])
            save_job(j)
    finally:
        ACTIVE.release()


def references_file(value, filename):
    if isinstance(value, dict):
        return any(references_file(v, filename) for v in value.values())
    if isinstance(value, list):
        return any(references_file(v, filename) for v in value)
    return value == filename


@router.delete('/auditions/{jid}')
def delete_audition(pid: str, jid: str):
    """Delete only an isolated audition, never project audio or shared files."""
    m = context()
    from .project_cleanup import safe_file
    with m.lock:
        j = read_job(pid, jid)
        if not j.get('audition'): raise HTTPException(404, 'Muestra no encontrada')
        if j['status'] == 'deleted': return {'id': jid, 'status': 'deleted'}
        if j['status'] not in ('completed', 'deleting') or not j.get('result'):
            raise HTTPException(409, 'La muestra aún no está disponible para eliminar')
        name = j['result'].get('file')
        path = safe_file(m.DATA, name)
        if path is None or path.suffix.lower() != '.wav':
            raise HTTPException(409, 'Archivo de muestra no válido')
        with m.engine.connect() as c:
            projects = [json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM projects'))]
            others = [json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM jobs WHERE id<>:id'), {'id': jid})]
        if any(references_file(p, name) for p in projects + others):
            raise HTTPException(409, 'Este audio está referenciado por un proyecto, versión u otro trabajo; no se eliminó')
        # Persist the intention first. A retry can finish after a process interruption.
        previous_status = j['status']
        j['status'] = 'deleting'; save_job(j)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            j['status'] = previous_status; save_job(j)
            raise HTTPException(409, 'No se pudo borrar la muestra; detén su reproducción y vuelve a intentarlo') from exc
        j.pop('result', None)
        j.update(status='deleted', deleted_at=now())
        save_job(j)
    return {'id': jid, 'status': 'deleted'}


@router.get('/auditions')
def list_auditions(pid: str):
    m = context(); m.get(pid)
    with m.engine.connect() as c:
        values = [json.loads(r[0]) for r in c.execute(sql('SELECT payload FROM jobs'))]
    return [public_job(j) for j in sorted(values, key=lambda j: j.get('created_at', ''))
            if j.get('kind') == 'voice-editor' and j.get('project_id') == pid
            and j.get('audition') and j.get('status') != 'deleted']


def name_mentions(project, original):
    from .narrative import key
    original = original.strip()
    if not original or len(original) > 200:
        raise HTTPException(422, 'Escribe un nombre de hasta 200 caracteres')
    pattern = re.compile(r'(?<!\w)' + re.escape(original) + r'(?!\w)', re.IGNORECASE)
    groups = {}
    for ci, ch in enumerate(project['chapters'], 1):
        for si, s in enumerate(ch['segments'], 1):
            if s.get('is_separator'): continue
            count = len(pattern.findall(s['text']))
            if not count: continue
            char = next((c for c in project['characters'] if c['id'] == s.get('character_id')), None)
            if not char: char = next((c for c in project['characters'] if key(c['name']) == key(s.get('speaker', ''))), None)
            group_key = (char['id'] if char else s.get('speaker', 'Sin atribuir'), s['voice'], s['speed'])
            g = groups.setdefault(group_key, {'character_id': char['id'] if char else None,
                'speaker': s.get('speaker', 'Sin atribuir'), 'voice': s['voice'], 'speed': s['speed'],
                'count': 0, 'eligible_count': 0, 'occurrences': [],
                'pronunciation': rendered(project, {**s, 'text': original}),
                'voice_override_id': next((r['id'] for r in project.get('pronunciation_voice_overrides', []) if r['voice'] == s['voice'] and r['original'].casefold() == original.casefold()), None)})
            eligible = included(s) and not s.get('review') and char is not None
            g['count'] += count
            if eligible: g['eligible_count'] += count
            g['occurrences'].append({'segment_id': s['id'], 'chapter_id': ch['id'],
                'chapter': ch['title'], 'chapter_number': ci, 'fragment_number': si,
                'scene': s.get('scene'), 'text': s['text'], 'count': count,
                'excluded': not included(s), 'review': bool(s.get('review')),
                'eligible': eligible, 'audio': approved_audio(s), 'revision': s.get('revision', 0)})
    conflicts = [r for r in project.get('pronunciation_rules', []) if r['active']
                 and pattern.search(r['original'])]
    result = {'original': original, 'groups': list(groups.values()), 'rules': conflicts,
              'total': sum(g['count'] for g in groups.values()),
              'eligible_count': sum(g['eligible_count'] for g in groups.values()),
              'voice_overrides': [r for r in project.get('pronunciation_voice_overrides', []) if r['original'].casefold() == original.casefold()]}
    result['snapshot_token'] = signature(result)
    return result


@router.get('/mentions')
def mentions(pid: str, original: str):
    return name_mentions(context().get(pid), original)


class UniformPronunciation(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    pronunciation: str = Field(min_length=1, max_length=300)
    snapshot_token: str
    confirmed: bool = False


def uniform_guard(project, body, rid=None):
    for rule in project.get('pronunciation_rules', []):
        matches = re.search(r'(?<!\w)' + re.escape(rule['original']) + r'(?!\w)', body.original.strip(), re.IGNORECASE)
        if rule.get('uniform') and rule['active'] and matches:
            if rule['id'] == rid:
                if body.provider != 'all' or body.character_id:
                    raise HTTPException(409, 'La pronunciación uniforme se aplica a todos los motores y hablantes')
            elif body.active and (body.original.strip().casefold() != rule['original'].casefold() or body.pronunciation.strip() != rule['pronunciation']):
                raise HTTPException(409, 'Hay una pronunciación uniforme activa para este nombre. Edítala desde Quiénes dicen este nombre')


@router.put('/uniform-pronunciation')
def set_uniform_pronunciation(pid: str, body: UniformPronunciation):
    m = context()
    if not body.original.strip() or not body.pronunciation.strip():
        raise HTTPException(422, 'Escribe el nombre y su pronunciación')
    if not body.confirmed:
        raise HTTPException(409, 'Confirma aplicar la misma escritura fonética a todos los hablantes')
    with m.lock:
        p = m.get(pid); view = name_mentions(p, body.original)
        if view['snapshot_token'] != body.snapshot_token:
            raise HTTPException(409, 'Las menciones o reglas cambiaron; vuelve a buscar antes de guardar')
        if not view['total']: raise HTTPException(409, 'No hay menciones del nombre en este proyecto')
        entries = p.setdefault('pronunciation_rules', [])
        entry = next((r for r in entries if r['original'].casefold() == body.original.strip().casefold()
                      and r['provider'] == 'all' and not r.get('character_id')), None)
        pattern = re.compile(r'(?<!\w)' + re.escape(body.original.strip()) + r'(?!\w)', re.IGNORECASE)
        before = [dict(r) for r in entries if pattern.search(r['original'])]
        if entry is None:
            entry = {'id': str(uuid.uuid4())}; entries.append(entry)
        for r in entries:
            if r is not entry and pattern.search(r.get('original', '')):
                r['active'] = False
        entry.update(original=body.original.strip(), pronunciation=body.pronunciation.strip(),
                     language='es', provider='all', character_id=None, active=True, uniform=True)
        p.setdefault('voice_editor_history', []).append({'action': 'uniform-pronunciation',
            'at': now(), 'original': body.original.strip(), 'pronunciation': body.pronunciation.strip(),
            'previous_rules': before, 'mentions': view['total']})
        m.save(p)
    return {'rule': entry, 'mentions': name_mentions(p, body.original)}


def pronunciation_for_voice(project, original, voice):
    override = next((r for r in project.get('pronunciation_voice_overrides', [])
                     if r['original'].casefold() == original.casefold() and r['voice'] == voice), None)
    if override: return override['pronunciation']
    uniform = next((r for r in project.get('pronunciation_rules', [])
                    if r['active'] and r.get('uniform') and r['original'].casefold() == original.casefold()), None)
    return uniform['pronunciation'] if uniform else original


class VoicePronunciation(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    pronunciation: str = Field(min_length=1, max_length=300)
    voice: str = Field(min_length=1, max_length=100)


@router.put('/voice-pronunciation')
def save_voice_pronunciation(pid: str, body: VoicePronunciation):
    m = context()
    if not body.original.strip() or not body.pronunciation.strip():
        raise HTTPException(422, 'Escribe el nombre y la pronunciación para esta voz')
    try: provider_for_voice(body.voice)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    with m.lock:
        p = m.get(pid); view = name_mentions(p, body.original)
        if not any(g['voice'] == body.voice for g in view['groups']):
            raise HTTPException(409, 'Esta voz no tiene menciones del nombre en el proyecto')
        overrides = p.setdefault('pronunciation_voice_overrides', [])
        entry = next((r for r in overrides if r['original'].casefold() == body.original.strip().casefold() and r['voice'] == body.voice), None)
        before = dict(entry) if entry else None
        if entry is None:
            entry = {'id': str(uuid.uuid4())}; overrides.append(entry)
        entry.update(original=body.original.strip(), pronunciation=body.pronunciation.strip(), voice=body.voice)
        p.setdefault('voice_editor_history', []).append({'action': 'voice-pronunciation', 'at': now(), 'before': before, 'after': dict(entry)})
        m.save(p)
    return {'override': entry, 'mentions': name_mentions(p, body.original)}


@router.delete('/voice-pronunciation/{oid}')
def remove_voice_pronunciation(pid: str, oid: str):
    m = context()
    with m.lock:
        p = m.get(pid)
        entry = next((r for r in p.get('pronunciation_voice_overrides', []) if r['id'] == oid), None)
        if entry is None: raise HTTPException(404, 'Ajuste de voz no encontrado')
        p['pronunciation_voice_overrides'] = [r for r in p['pronunciation_voice_overrides'] if r['id'] != oid]
        p.setdefault('voice_editor_history', []).append({'action': 'remove-voice-pronunciation', 'at': now(), 'before': entry})
        m.save(p)
    return {'mentions': name_mentions(p, entry['original'])}


def incorporation_plan(p, original):
    original = original.strip()
    view = name_mentions(p, original)
    targets = []; skipped = {'review_or_excluded': 0, 'no_audio': 0, 'already_current': 0}
    from .project_cleanup import safe_file
    for g in view['groups']:
        for o in g['occurrences']:
            s = context().segment(p, o['segment_id'])
            if not o['eligible']:
                skipped['review_or_excluded'] += 1; continue
            active = approved_audio(s)
            path = safe_file(context().DATA, active)
            if not active or path is None or not path.is_file():
                skipped['no_audio'] += 1; continue
            tts_text = rendered(p, s)
            current = next((v for v in s.get('versions', []) if v.get('file') == active), None)
            # Legacy WAVs without an exact recorded request are considered unknown.
            if current and current.get('text') == tts_text and current.get('voice') == s['voice'] and current.get('speed') == s['speed']:
                skipped['already_current'] += 1; continue
            targets.append({'segment_id': s['id'], 'chapter_id': o['chapter_id'], 'chapter': o['chapter'],
                'speaker': s['speaker'], 'voice': s['voice'], 'speed': s['speed'],
                'original_text': s['text'], 'tts_text': tts_text, 'old_audio': active,
                'snapshot': snapshot(s)})
    return {'original': original, 'targets': targets, 'count': len(targets), 'skipped': skipped,
            'preview_token': signature({'view': view['snapshot_token'], 'targets': targets, 'skipped': skipped})}


@router.get('/incorporation')
def preview_incorporation(pid: str, original: str):
    return incorporation_plan(context().get(pid), original)


class Incorporate(BaseModel):
    original: str = Field(min_length=1, max_length=200)
    preview_token: str
    confirmed: bool = False


@router.post('/incorporation', status_code=202)
def start_incorporation(pid: str, body: Incorporate):
    m = context()
    if not body.confirmed: raise HTTPException(409, 'Confirma la sustitución de los audios activos indicados en la vista previa')
    with m.lock:
        p = m.get(pid); plan = incorporation_plan(p, body.original)
        if body.preview_token != plan['preview_token']:
            raise HTTPException(409, 'La vista previa cambió; vuelve a revisar antes de incorporar')
        if not plan['targets']: raise HTTPException(409, 'No hay audios pendientes de incorporar para este nombre')
        if not ACTIVE.acquire(blocking=False): raise HTTPException(409, 'Espera a que termine el trabajo de voz actual')
        j = {'id': str(uuid.uuid4()), 'kind': 'voice-editor', 'project_id': pid,
             'incorporate': True, 'original': body.original.strip(), 'status': 'queued', 'created_at': now(),
             'targets': plan['targets'], 'total': plan['count'], 'done': 0, 'incorporated': 0, 'processed': 0,
             'errors': [], 'cancel_requested': False}
        try:
            with m.engine.begin() as c:
                c.execute(sql('INSERT INTO jobs VALUES (:id,:p)'), {'id': j['id'], 'p': json.dumps(j, ensure_ascii=False)})
            threading.Thread(target=worker, args=(pid, j['id']), daemon=True).start()
        except Exception:
            ACTIVE.release(); raise
    return public_job(j)


@router.post('/incorporation/{jid}/restore')
def restore_incorporation(pid: str, jid: str):
    """Atomic restore for an untouched completed subset; never removes any file."""
    m = context()
    with m.lock:
        p = m.get(pid); j = read_job(pid, jid)
        if not j.get('incorporate') or j['status'] in ('queued', 'running') or j.get('restored_at'):
            raise HTTPException(409, 'El lote no está disponible para restaurar')
        if j.get('review_resolution'):
            from .finalization import restore_resolutions
            return restore_resolutions(p, j)
        changes = []
        for ch in p['chapters']:
            for s in ch['segments']:
                v = next((v for v in s.get('versions', []) if v.get('incorporation_job_id') == jid and v.get('status') == 'approved'), None)
                if v:
                    if s.get('audio') != v['file'] or s.get('revision') != v.get('activation_revision'):
                        raise HTTPException(409, 'Un fragmento cambió después de incorporar; restaura sus versiones individualmente. No se modificó el lote')
                    from .project_cleanup import safe_file
                    old = next((old for old in s['versions'] if old.get('file') == v['previous_audio']), None)
                    old_path = safe_file(m.DATA, v['previous_audio'])
                    if j.get('finalization') and not v['previous_audio']:
                        old = {'file': None, 'duration': 0}
                    elif not old or old_path is None or not old_path.is_file(): raise HTTPException(409, 'Una versión anterior no está disponible')
                    changes.append((s, old))
        if not changes: raise HTTPException(409, 'No hay incorporaciones completadas para restaurar')
        for s, old in changes:
            s['audio'] = old['file']; s['duration'] = old.get('duration', 0); s['revision'] = s.get('revision', 0) + 1
        p.setdefault('voice_editor_history', []).append({'action': 'restore-incorporation', 'job_id': jid, 'at': now(), 'count': len(changes)})
        m.save(p); j['restored_at'] = now(); save_job(j)
    return p
