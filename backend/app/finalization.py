"""Project-wide, explicit publication of reviewed audio. Originals are retained."""
import copy
import json
import threading
import uuid
import wave
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text as sql
from . import voice_editor as ve
from .scenes import included
from .project_cleanup import safe_file

from .narrative import key

RESOLUTION_FIELDS=('speaker','character_id','voice','speed','color','audio','duration','review','content_review','speaker_confirmed','review_reason','manual_audio_acceptance')

router = APIRouter(prefix='/api/projects/{pid}/finalization', tags=['Project audio status'])


def exists(name):
    path = safe_file(ve.context().DATA, name)
    return bool(path and path.is_file())


def rules_key(p):
    return ve.signature([p.get('pronunciation_rules', []), p.get('pronunciation_voice_overrides', [])])


def plan(p, verify_pronunciations=False):
    rows = []
    totals = dict(current=0, historical=0, proposed=0, outdated=0, missing=0, review=0, excluded=0)
    for ch in p['chapters']:
        for number, s in enumerate(ch['segments'], 1):
            expected = ve.rendered(p, s)
            active = ve.approved_audio(s)
            current = next((v for v in s.get('versions', []) if v.get('file') == active), None)
            proposals = [v for v in s.get('versions', []) if v.get('status') == 'proposed'
                         and v.get('source_snapshot') == ve.snapshot(s) and exists(v.get('file'))
                         and v.get('duration', 0) > 0 and v.get('voice') == s['voice']
                         and v.get('speed') == s['speed']]
            matching = [v for v in proposals if v.get('text') == expected]
            recorded = current and current.get('provider') and current.get('text') == expected and current.get('voice') == s['voice'] and current.get('speed') == s['speed']
            # An explicitly selected alternative remains valid until source/voice/rules change.
            manual = current and current.get('finalization_rules') == rules_key(p) and current.get('source_snapshot', {}).get('text') == s['text'] and current.get('voice') == s['voice'] and current.get('speed') == s['speed']
            accepted = s.get('manual_audio_acceptance', {})
            manual = manual or (accepted.get('audio') == active and accepted.get('request') == ve.signature([s['text'], s['voice'], s['speed'], rules_key(p)]))
            if verify_pronunciations and expected != s['text']:
                # A manual review can preserve an old WAV without incorporating saved phonetics.
                # In this explicit audit mode use recorded TTS evidence, not that review stamp.
                manual = False
                if not recorded:
                    proposals = [v for v in s.get('versions', [])
                                 if v.get('file') != active and v.get('status') in ('proposed','approved')
                                 and v.get('provider') and v.get('text') == expected
                                 and v.get('source_snapshot', {}).get('text') == s['text']
                                 and v.get('voice') == s['voice'] and v.get('speed') == s['speed']
                                 and v.get('duration', 0) > 0 and exists(v.get('file'))]
                    matching = proposals
            if proposals: status = 'proposed'
            elif not active or not exists(active): status = 'missing'
            elif recorded or manual: status = 'current'
            elif expected != s['text'] or (current and current.get('provider') and (current.get('voice') != s['voice'] or current.get('speed') != s['speed'] or current.get('text') != expected)): status = 'outdated'
            else: status = 'historical'
            audio_status = status
            if not included(s): status = 'excluded'
            elif s.get('review'): status = 'review'
            totals[status] += 1
            rows.append(dict(segment_id=s['id'], chapter_id=ch['id'], chapter=ch['title'], number=number,
                speaker=s['speaker'], voice=s['voice'], speed=s['speed'], status=status, audio_status=audio_status,
                review_reason=s.get('review_reason', ''),
                character_id=next((c['id'] for c in p.get('characters', []) if c.get('id')==s.get('character_id') or key(c['name'])==key(s['speaker'])), None),
                audio=active if exists(active) else None, text=s['text'], tts_text=expected,
                snapshot=ve.snapshot(s), old_audio=s.get('audio'),
                recommended_version_id=matching[-1]['id'] if matching else None,
                proposals=[{k:v.get(k) for k in ('id','file','text','voice','speed','created_at')} for v in reversed(proposals)]))
    blockers = sum(totals[k] for k in ('proposed','outdated','missing','review'))
    return dict(rows=rows, characters=p.get('characters', []), totals=totals, ready=bool(rows) and not blockers and totals['current']+totals['historical']>0,
                verify_pronunciations=verify_pronunciations, preview_token=ve.signature([rows, rules_key(p), p.get('characters', []), verify_pronunciations]))


@router.get('')
def status(pid: str, verify_pronunciations: bool = False):
    return plan(ve.context().get(pid), verify_pronunciations)


class Apply(BaseModel):
    preview_token: str
    confirmed: bool = False
    selections: dict[str, str] = Field(default_factory=dict)
    verify_pronunciations: bool = False
    confirm_reviews: bool = False
    review_choices: dict[str, str] = Field(default_factory=dict)


@router.post('/apply', status_code=202)
def apply(pid: str, body: Apply):
    m = ve.context()
    if not body.confirmed: raise HTTPException(409, 'Confirma los audios revisados y la generación pendiente')
    with m.lock:
        p = m.get(pid); view = plan(p, body.verify_pronunciations)
        if view['preview_token'] != body.preview_token: raise HTTPException(409, 'El proyecto cambió. Actualiza el estado y revisa de nuevo.')
        targets = []
        for row in view['rows']:
            if row['status'] not in ('proposed','outdated','missing','review'): continue
            original = m.segment(p, row['segment_id'])
            desired = copy.deepcopy(original)
            profile = None
            keep = False
            if row['status'] == 'review':
                if not body.confirm_reviews: continue
                choice = body.review_choices.get(row['segment_id'])
                if choice == 'keep':
                    if not row['audio']: raise HTTPException(409, 'No se puede conservar un audio inexistente. Selecciona un personaje para generar el fragmento.')
                    keep = True
                else:
                    profile = next((c for c in p.get('characters', []) if c['id'] == choice), None)
                    if not profile: raise HTTPException(409, 'Elige un personaje o conserva explícitamente el audio reparado de cada revisión.')
                    desired.update(speaker=profile['name'], character_id=profile['id'], voice=profile['voice'], speed=profile['speed'], color=profile['color'])
                    # A profile selection only changes the WAV when its TTS request changes.
                    keep = bool(row['audio'] and desired['voice']==original['voice'] and desired['speed']==original['speed'] and ve.rendered(p,desired)==ve.rendered(p,original) and row['audio_status'] in ('current','historical'))
                desired.update(review=False, content_review=False, speaker_confirmed=True, review_reason='')
            selected = body.selections.get(row['segment_id'])
            candidate = next((v for v in row['proposals'] if v['id'] == selected), None)
            if row['status'] == 'proposed' and not candidate:
                raise HTTPException(409, 'Elige una propuesta revisada para cada fragmento pendiente de aplicar.')
            # Review decisions use the existing repaired WAV or a new request for the chosen profile.
            if row['status'] == 'review': candidate = None
            targets.append({**row, 'version_id': candidate['id'] if candidate else None,
                            'keep_audio': keep, 'desired': {k:desired[k] for k in ('speaker','character_id','voice','speed','color') if k in desired}, 'profile': profile,
                            'before': {k:copy.deepcopy(original[k]) for k in RESOLUTION_FIELDS if k in original},
                            'tts_text': candidate['text'] if candidate else ve.rendered(p, desired)})
        if not targets: raise HTTPException(409, 'No hay cambios aplicables. Revisa los fragmentos bloqueados.')
        if not ve.ACTIVE.acquire(blocking=False): raise HTTPException(409, 'Hay un trabajo de voz en curso. Espera a que termine.')
        j = dict(id=str(uuid.uuid4()), kind='voice-editor', project_id=pid, finalization=True,
                 incorporate=True, original='Todo el proyecto', status='queued', created_at=ve.now(),
                 targets=targets, total=len(targets), done=0, incorporated=0, processed=0, errors=[], cancel_requested=False,
                 rules_key=rules_key(p), verify_pronunciations=body.verify_pronunciations, review_resolution=True, resolutions=[], reviewed=0)
        try:
            with m.engine.begin() as c:
                c.execute(sql('INSERT INTO jobs (id,payload) VALUES (:id,:p)'), dict(id=j['id'], p=json.dumps(j, ensure_ascii=False)))
            threading.Thread(target=worker, args=(pid,j['id']), daemon=True).start()
        except Exception:
            ve.ACTIVE.release(); raise
    return ve.public_job(j)


def worker(pid, jid):
    m = ve.context()
    try:
        with m.lock:
            j = ve.read_job(pid,jid); j['status']='running'; ve.save_job(j)
        for t in j['targets']:
            with m.lock:
                j=ve.read_job(pid,jid)
                if j['cancel_requested']: break
            try:
                if t['keep_audio'] or t['version_id']:
                    generated=None
                else:
                    name=str(uuid.uuid4())+'.wav'
                    from .tts_provider import generate
                    result=generate(t['tts_text'],t['desired']['voice'],t['desired']['speed'],m.DATA/name)
                    with wave.open(str(m.DATA/name),'rb') as w: duration=w.getnframes()/w.getframerate()
                    generated=dict(id=str(uuid.uuid4()), file=name, segment_id=t['segment_id'],
                        text=t['tts_text'],voice=t['desired']['voice'],speed=t['desired']['speed'],duration=duration,
                        provider=result['provider'],created_at=ve.now(),status='proposed',source_snapshot=t['snapshot'])
                with m.lock:
                    p=m.get(pid); s=m.segment(p,t['segment_id']); ve.normalize_versions(s,m.DATA)
                    v=generated or next((v for v in s['versions'] if v.get('id')==t['version_id']),None)
                    if generated: s['versions'].append(generated)
                    current_fields={k:copy.deepcopy(s[k]) for k in RESOLUTION_FIELDS if k in s}
                    profile_valid=not t['profile'] or t['profile'] in p.get('characters', [])
                    valid=(ve.snapshot(s)==t['snapshot'] and current_fields==t['before']
                           and rules_key(p)==j['rules_key'] and profile_valid)
                    if t['keep_audio']:
                        valid=valid and exists(t['audio'])
                        if valid:
                            # Check the actual WAV before clearing a leftover review flag.
                            with wave.open(str(m.DATA/t['audio']),'rb') as w: duration=w.getnframes()/w.getframerate()
                            valid=duration>0
                    else:
                        valid=valid and v and (v.get('status')=='proposed' or j.get('verify_pronunciations') and t['version_id'] and v.get('status')=='approved') and exists(v.get('file'))
                    if valid:
                        revision=s.get('revision',0)+1
                        if not t['keep_audio']:
                            v.update(status='approved',approved_at=ve.now(),incorporation_job_id=jid,
                                previous_audio=t['old_audio'],activation_revision=revision,finalization_rules=j['rules_key'])
                        for k in ('speaker','character_id','voice','speed','color'):
                            if k in t['desired']: s[k]=t['desired'][k]
                        if t['status']=='review':
                            s.update(review=False,content_review=False,speaker_confirmed=True,review_reason='')
                        s.update(audio=t['audio'] if t['keep_audio'] else v['file'],duration=duration if t['keep_audio'] else v['duration'],revision=revision)
                        if t['keep_audio']:
                            s['manual_audio_acceptance']=dict(audio=s['audio'],request=ve.signature([s['text'],s['voice'],s['speed'],rules_key(p)]),at=ve.now())
                    m.save(p)
                    if not valid: raise ValueError('El fragmento cambió durante el lote; se conserva el audio anterior. Actualiza y revisa.')
                    j=ve.read_job(pid,jid);j['done']+=1;j['incorporated']+=int(not t['keep_audio']);j['reviewed']+=int(t['status']=='review');j['processed']+=1
                    j['resolutions'].append(dict(segment_id=s['id'],before=t['before'],revision=s['revision'],audio=s['audio'],after={k:copy.deepcopy(s[k]) for k in RESOLUTION_FIELDS if k in s}))
                    ve.save_job(j)
            except Exception as exc:
                with m.lock:
                    j=ve.read_job(pid,jid);j['processed']+=1
                    j['errors'].append(dict(segment_id=t['segment_id'],message=str(exc) if isinstance(exc,ValueError) else 'No se pudo aplicar el audio. El anterior se conserva; vuelve a intentar.'))
                    ve.save_job(j)
        with m.lock:
            j=ve.read_job(pid,jid);j['status']='cancelled' if j['cancel_requested'] else 'completed_with_errors' if j['errors'] else 'completed'
            j['finished_at']=ve.now();ve.save_job(j)
    except Exception:
        with m.lock:
            j=ve.read_job(pid,jid);j['status']='interrupted';ve.save_job(j)
    finally: ve.ACTIVE.release()


def require_ready(p):
    if not plan(p)['ready']:
        raise HTTPException(409, 'Hay correcciones o revisiones pendientes. Abre Estado del libro, aplica los cambios revisados y vuelve a exportar. Para escuchar el estado actual usa vista previa parcial.')


def restore_resolutions(p, j):
    """Restore review decisions and assignments as one guarded batch; retain WAVs."""
    m=ve.context(); changes=[]
    for record in j.get('resolutions', []):
        s=m.segment(p,record['segment_id'])
        fields={k:copy.deepcopy(s[k]) for k in RESOLUTION_FIELDS if k in s}
        if s.get('revision')!=record['revision'] or fields!=record['after']:
            raise HTTPException(409, 'Un fragmento cambió después del lote. No se restauró ningún cambio.')
        if record['before'].get('audio') and not exists(record['before']['audio']):
            raise HTTPException(409, 'Una versión anterior no está disponible. No se restauró ningún cambio.')
        changes.append((s,record))
    if not changes: raise HTTPException(409, 'No hay cambios completados para restaurar')
    for s,record in changes:
        for k in RESOLUTION_FIELDS:
            if k in record['before']: s[k]=copy.deepcopy(record['before'][k])
            else: s.pop(k,None)
        s['revision']=record['revision']+1
    m.save(p);j['restored_at']=ve.now();ve.save_job(j)
    return p
