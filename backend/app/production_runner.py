"""Checkpointed chapter trial production, external plan only; no model calls."""
import copy,json,uuid,tempfile,shutil
from pathlib import Path
from fastapi import APIRouter,HTTPException,BackgroundTasks
from fastapi.responses import FileResponse,PlainTextResponse
from pydantic import BaseModel,ConfigDict
from sqlalchemy import text as sql
from . import sound_mixer as sm
from .production_exchange import ProductionPlan,validate_plan,review_state
from .voice_editor import signature,now,approved_audio,normalize_versions,rendered,snapshot
from .project_cleanup import safe_file

router=APIRouter(prefix='/api/projects/{pid}/production-exchange/plans/{plan_id}/production',tags=['Chapter production trial'])
class Start(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preview_token:str
    confirmed:bool=False
    allow_paid:bool=False
    accept_estimated_timing:bool=False
class Confirm(BaseModel):
    confirmed:bool=False

def record(p,rid):
    x=next((x for x in p.get('production_plans',[]) if x['id']==rid),None)
    if not x:raise HTTPException(404,'Plan no encontrado en este proyecto.')
    return x

def state(p):
    return signature({k:p.get(k) for k in ('original','chapters','characters','sound_effects','sound_cues','sound_scene_levels','voice_priority','pronunciation_rules','pronunciation_voice_overrides')})

def run_record(p,rid,runid):
    r=next((x for x in p.get('production_runs',[]) if x['id']==runid and x['plan_id']==rid),None)
    if not r:raise HTTPException(404,'Producción no encontrada en este plan.')
    return r

def public(r):
    keys=('id','plan_id','status','stage','message','created_at','updated_at','completed','total','generated','reused','completed_scenes','scene_ids','pause_requested','file','mp3_file')
    return {k:r.get(k) for k in keys}

def preflight(p,rid):
    rec=record(p,rid);plan=ProductionPlan.model_validate(rec['plan']);v=validate_plan(p,plan);errors=[x['message'] for x in v['errors']]
    scopes=[s for s in sm.scenes(p) if s['id'] in plan.scope_scene_ids];chapters={s['chapter_id'] for s in scopes}
    if len(chapters)!=1:errors.append('La prueba automática requiere exactamente un capítulo completo.')
    elif set(plan.scope_scene_ids)!={s['id'] for s in sm.scenes(p) if s['chapter_id'] in chapters}:errors.append('Exporta e importa todas las escenas del capítulo para esta prueba.')
    if not shutil.which('ffmpeg'):errors.append('FFmpeg no está disponible.')
    reviews={x['id']:x for x in review_state(rec,v)['items']}
    for x in reviews.values():
        if x['path']=='capabilities':continue
        if not x['response'] or x['response']['decision'] not in ('reviewed','keep_existing'):errors.append('Resuelve la revisión pendiente: '+x['message'])
    source={s['id']:s for ch in p['chapters'] for s in ch['segments']};chars={c['id']:c for c in p['characters']};sounds={s['id']:s for s in p.get('sound_effects',[])}
    disabled={a.cue_id for sc in plan.scenes for a in sc.existing_cue_actions}
    total=generated=paid=0;split_count=0
    for scene in plan.scenes:
        current=next((x for x in scopes if x['id']==scene.scene_id),None)
        if current is None:continue
        ids={s['id'] for s in current['segments']}
        if scene.decision=='pending':errors.append('Hay una escena sin analizar.')
        if {x.segment_id for x in scene.performances}!=ids:errors.append('Cada fragmento del capítulo necesita una propuesta de interpretación.')
        for perf in scene.performances:
            seg=source.get(perf.segment_id)
            if seg is None:continue
            targets=perf.parts or [perf]
            total+=len(targets)
            if perf.parts:
                split_count+=1
                if any(c.get('segment_id')==perf.segment_id and c.get('active',True) and c.get('id') not in disabled for c in p.get('sound_cues',[])):errors.append('Una división tiene pistas ancladas: revisa esas asignaciones antes de producir.')
            for t in targets:
                if t.character_id not in chars or not t.voice_id:errors.append('Hay personajes o voces sin resolver.');continue
                if not perf.parts and seg.get('review'):errors.append('Un fragmento conserva una revisión de contenido pendiente.')
                regenerate=bool(perf.parts) or t.voice_id!=seg.get('voice') or t.speed!=seg.get('speed',1) or t.character_id!=seg.get('character_id') or not sm.wav_info(approved_audio(seg))
                if regenerate:
                    generated+=1
                    if t.voice_id.startswith('es-'):paid+=1
        if len([x for x in p.get('sound_cues',[]) if x.get('active',True) and x.get('id') not in disabled and x.get('segment_id') in ids])+len(scene.effects)+len(scene.music)>sm.MAX_CUES:errors.append('Una escena excede 16 pistas activas.')
        for role,cues in [('effect',scene.effects),('music',scene.music)]:
            for cue in cues:
                if role=='music' and p.get('manual_music_choices',{}).get(scene.scene_id):continue
                if cue.resource_id is None or cue.resource_id not in sounds or not sm.wav_info(sounds.get(cue.resource_id,{}).get('file')):errors.append('Hay recursos de música o efectos sin archivo disponible.');continue
                if any(x.get('sound_id')==cue.resource_id and x.get('segment_id')==cue.segment_id and x.get('role','effect')==role for x in p.get('sound_cues',[])):errors.append('El plan propone una pista ya asignada; retírala del JSON para conservar la existente sin duplicarla.')
                seg=source.get(cue.segment_id)
                if seg and seg['text'].count(cue.anchor_quote)!=1:errors.append('Una cita sonora no es única dentro del fragmento.')
                perf=next((x for x in scene.performances if x.segment_id==cue.segment_id),None)
                if perf and perf.parts and sum(cue.anchor_quote in x.text for x in perf.parts)!=1:errors.append('Una entrada sonora cruza el corte de una división.')
    if len(p.get('sound_cues',[]))+sum(len(x.effects)+len(x.music) for x in plan.scenes)>500:errors.append('El proyecto excedería 500 pistas.')
    result={'can_start':not errors,'errors':list(dict.fromkeys(errors)),'chapter':next((ch['title'] for ch in p['chapters'] if ch['id'] in chapters),''),'scenes':len(scopes),'segments':total,'to_generate':generated,'reuse':total-generated,'paid_segments':paid,'splits':split_count,'estimated_timing':bool(split_count or generated or any(s.effects or s.music or s.fit_existing_music for s in plan.scenes)),'disabled_cues':[{'id':a.cue_id,'sound_name':sounds.get(next((x.get('sound_id') for x in p.get('sound_cues',[]) if x['id']==a.cue_id),''),{}).get('name','Pista existente'),'reason':a.reason} for sc in plan.scenes for a in sc.existing_cue_actions],'fit_music_scenes':sum(sc.fit_existing_music for sc in plan.scenes),'notice':'Prueba automática: conserva grabaciones válidas; la emoción no cambia el motor. Las entradas por citas son estimaciones proporcionales, no alineación exacta. El resultado requiere escucha.'}
    result['preview_token']=signature({'state':state(p),'plan':rec['plan_hash'],'review':rec.get('review_revision',0),'result':result})
    return result

def guard_jobs(p):
    with sm.main().engine.connect() as db:jobs=[json.loads(x[0]) for x in db.execute(sql('SELECT payload FROM jobs'))]
    if any(j.get('project_id',j.get('pid'))==p['id'] and j.get('status') in ('queued','running') for j in jobs):raise HTTPException(409,'Espera a que finalicen los trabajos del proyecto.')

def commit(p,r,**changes):
    r.update(changes,updated_at=now());r['state_token']=state(p);sm.main().save(p)

def check(p,r):
    if state(p)!=r['state_token']:raise HTTPException(409,'El proyecto cambió fuera de esta producción. Exporta un plan actualizado antes de continuar.')
    if r.get('pause_requested'):
        commit(p,r,status='paused',message='Pausado entre operaciones; puedes reanudar.');return False
    return True

@router.get('/preview')
def preview(pid:str,plan_id:str):
    with sm.main().lock:p=copy.deepcopy(sm.main().get(pid))
    return preflight(p,plan_id)

@router.get('/runs')
def runs(pid:str,plan_id:str):
    with sm.main().lock:p=sm.main().get(pid);record(p,plan_id)
    return {'runs':[public(r) for r in reversed(p.get('production_runs',[])) if r['plan_id']==plan_id]}

@router.post('/runs',status_code=202)
def start(pid:str,plan_id:str,body:Start,tasks:BackgroundTasks):
    if not body.confirmed:raise HTTPException(422,'Confirma producir esta prueba de capítulo.')
    if not sm.ACTIVE.acquire(False):raise HTTPException(409,'Hay otra mezcla o producción activa.')
    try:
        with sm.main().lock:
            p=sm.main().get(pid);guard_jobs(p);pr=preflight(p,plan_id)
            if not pr['can_start']:raise HTTPException(409,'El plan tiene pendientes. Revisa la previsualización de producción.')
            if body.preview_token!=pr['preview_token']:raise HTTPException(409,'La previsualización cambió. Vuelve a comprobarla.')
            if pr['paid_segments'] and not body.allow_paid:raise HTTPException(422,'Confirma el uso de tu motor de pago para los fragmentos pendientes.')
            if pr['estimated_timing'] and not body.accept_estimated_timing:raise HTTPException(422,'Acepta las entradas estimadas antes de generar esta prueba.')
            if any(x['plan_id']==plan_id and x['status'] not in ('ready','cancelled') for x in p.get('production_runs',[])):raise HTTPException(409,'Este plan ya tiene una producción. Reanúdala en lugar de duplicarla.')
            if len(p.get('production_runs',[]))>=20:raise HTTPException(409,'Límite de 20 producciones conservadas por proyecto.')
            rec=record(p,plan_id);r={'id':uuid.uuid4().hex,'plan_id':plan_id,'status':'queued','stage':'preparación','created_at':now(),'plan':copy.deepcopy(rec['plan']),'completed':0,'total':pr['segments']+pr['scenes']+1,'generated':0,'reused':0,'completed_scenes':0,'scene_ids':rec['plan']['scope_scene_ids'],'done_segments':[],'clips':{},'pause_requested':False,'allow_paid':body.allow_paid}
            p.setdefault('production_runs',[]).append(r);commit(p,r)
        tasks.add_task(worker,pid,plan_id,r['id']);return public(r)
    except BaseException:sm.ACTIVE.release();raise

@router.post('/runs/{run_id}/pause')
def pause(pid:str,plan_id:str,run_id:str):
    with sm.main().lock:
        p=sm.main().get(pid);r=run_record(p,plan_id,run_id)
        if r['status'] not in ('queued','running'):raise HTTPException(409,'La producción no está en marcha.')
        r['pause_requested']=True;sm.main().save(p)
    return {'pause_requested':True}

@router.post('/runs/{run_id}/resume',status_code=202)
def resume(pid:str,plan_id:str,run_id:str,body:Confirm,tasks:BackgroundTasks):
    if not body.confirmed:raise HTTPException(422,'Confirma reanudar; conservará la autorización inicial de generación.')
    if not sm.ACTIVE.acquire(False):raise HTTPException(409,'Hay otra mezcla o producción activa.')
    try:
        with sm.main().lock:
            p=sm.main().get(pid);r=run_record(p,plan_id,run_id);guard_jobs(p)
            if r['status'] not in ('paused','error','interrupted'):raise HTTPException(409,'Esta producción no necesita reanudarse.')
            if state(p)!=r['state_token']:raise HTTPException(409,'El proyecto cambió. No se reanuda sobre datos distintos.')
            commit(p,r,status='queued',pause_requested=False,message='Reanudando con los pasos completados.')
        tasks.add_task(worker,pid,plan_id,run_id);return public(r)
    except BaseException:sm.ACTIVE.release();raise

def prepare_segments(p,r):
    r['cue_backups']=copy.deepcopy(p.get('sound_cues',[]))
    r['old_scene_durations']={s['id']:s['duration'] for s in sm.scenes(p) if s['id'] in r['scene_ids']}
    disabled={a['cue_id'] for sc in r['plan']['scenes'] for a in sc.get('existing_cue_actions',[])}
    for cue in p.get('sound_cues',[]):
        if cue['id'] in disabled:cue.update(active=False,updated_at=now(),disabled_by_production_run=r['id'])
    chars={x['id']:x for x in p['characters']};mapping={};targets=[];r['backups']=[]
    for scene in r['plan']['scenes']:
        for perf in scene['performances']:
            source=sm.main().segment(p,perf['segment_id']);r['backups'].append(copy.deepcopy(source));descriptors=perf.get('parts') or [perf];ids=[];new=[]
            for i,t in enumerate(descriptors):
                item=copy.deepcopy(source);char=chars[t['character_id']];changed=bool(perf.get('parts')) or any(item.get(k)!=t.get(v) for k,v in [('voice','voice_id'),('speed','speed'),('character_id','character_id')])
                if changed:
                    normalize_versions(item,sm.main().DATA)
                    item.update(audio=None,duration=0)
                if perf.get('parts'):
                    item.update(id=source['id'] if i==0 else str(uuid.uuid4()),text=t['text'],source_text=t['text'],versions=[],kind='narration' if char['name'].casefold()=='narrador' else 'dialogue')
                item.update(character_id=char['id'],speaker=char['name'],voice=t['voice_id'],speed=t['speed'],color=char.get('color','#00D9CE'),review=False,content_review=False,speaker_confirmed=True,revision=source.get('revision',0)+(1 if changed else 0))
                ids.append(item['id']);new.append(item);targets.append(item['id'])
            ch=next(ch for ch in p['chapters'] if any(s['id']==source['id'] for s in ch['segments']));pos=next(i for i,s in enumerate(ch['segments']) if s['id']==source['id']);ch['segments'][pos:pos+1]=new;mapping[source['id']]=ids
    r.update(prepared=True,mapping=mapping,targets=targets)

def generate_one(pid,planid,runid,sid):
    from .tts_provider import generate
    m=sm.main();path=m.DATA/('production_voice_'+uuid.uuid4().hex+'.wav')
    with m.lock:
        p=m.get(pid);r=run_record(p,planid,runid)
        if not check(p,r):return False
        s=m.segment(p,sid)
        if sm.wav_info(approved_audio(s)):
            r['done_segments'].append(sid);commit(p,r,reused=r['reused']+1,completed=r['completed']+1);return True
        if s['voice'].startswith('es-') and not r.get('allow_paid'):raise HTTPException(409,'No hay autorización para esta voz de pago.')
        before=r['state_token'];segment_copy=copy.deepcopy(s);project_copy=copy.deepcopy(p);tts_text=rendered(p,s);commit(p,r,stage='generando voz',message=s['speaker']+': '+s['text'][:100])
    try:
        result=generate(tts_text,segment_copy['voice'],segment_copy['speed'],path)
        if not sm.wav_info(path.name):raise HTTPException(502,'El motor no produjo un WAV válido.')
        with m.lock:
            p=m.get(pid);r=run_record(p,planid,runid)
            if state(p)!=before:raise HTTPException(409,'El proyecto cambió durante la generación; no se sustituyó el audio activo.')
            s=m.segment(p,sid);normalize_versions(s,m.DATA);s.setdefault('versions',[]).append({'id':uuid.uuid4().hex,'file':path.name,'voice':s['voice'],'speed':s['speed'],'text':tts_text,'provider':result['provider'],'status':'approved','duration':result['duration'],'created_at':now(),'segment_id':sid,'source_snapshot':snapshot(s),'production_run_id':runid})
            s.update(audio=path.name,duration=result['duration'],revision=s.get('revision',0)+1);r['done_segments'].append(sid);commit(p,r,generated=r['generated']+1,completed=r['completed']+1)
        return True
    except BaseException:path.unlink(missing_ok=True);raise

def place_cues(p,r):
    # Existing full-scene music follows the new narration length; finite effects stay unchanged.
    for sid,old_duration in r.get('old_scene_durations',{}).items():
        scene=sm.scene_by_id(p,sid)
        fit=next((sc.get('fit_existing_music',False) for sc in r['plan']['scenes'] if sc['scene_id']==sid),False)
        for cue in p.get('sound_cues',[]):
            if cue.get('active',True) and cue.get('role')=='music' and cue.get('loop') and cue['segment_id']==sid and cue.get('offset',0)==0 and (fit or abs(cue['duration']-old_duration)<.1):
                cue['duration']=scene['duration'];cue['updated_at']=now()
    sounds={s['id']:s for s in p.get('sound_effects',[])}
    for sc in r['plan']['scenes']:
        scene=sm.scene_by_id(p,sc['scene_id'])
        for role,items in [('effect',sc.get('effects',[])),('music',sc.get('music',[]))]:
            for index,cue in enumerate(items):
                if role=='music' and p.get('manual_music_choices',{}).get(sc['scene_id']):continue
                candidates=[sm.main().segment(p,sid) for sid in r['mapping'][cue['segment_id']]];anchor=next(s for s in candidates if cue['anchor_quote'] in s['text']);duration=sm.wav_info(approved_audio(anchor))['duration'];pos=anchor['text'].index(cue['anchor_quote']);pos+=len(cue['anchor_quote']) if cue['placement']=='after' else 0
                offset=min(max(0,duration*pos/max(1,len(anchor['text']))-(.1 if cue['placement']=='before' else 0)),max(0,duration-.001));start=next(s['offset'] for s in scene['segments'] if s['id']==anchor['id'])+offset;remaining=scene['duration']-start;info=sm.wav_info(sounds[cue['resource_id']]['file'])
                length=min(cue['duration_seconds'] or (remaining if role=='music' else info['duration']),remaining,1800 if role=='music' else 600)
                loop=cue['loop'] or role=='music'
                if not loop:length=min(length,info['duration'])
                if length<=0:raise HTTPException(422,'Una pista no tiene duración dentro de la escena.')
                body=sm.Cue(role=role,sound_id=cue['resource_id'],segment_id=anchor['id'],offset=offset,source_start=0,duration=length,volume_db=cue['gain_db'],fade_in=min(.5,length/4),fade_out=min(1,length/4),loop=loop,active=True)
                item=sm.validate_cue(p,body);item.update(id=signature({'run':r['id'],'scene':sc['scene_id'],'role':role,'index':index})[:32],production_run_id=r['id'],updated_at=now());p.setdefault('sound_cues',[]).append(item)
    from .auto_music import proposal,apply_rows
    scope={sc['scene_id'] for sc in r['plan']['scenes'] if sc.get('decision')!='intentional_silence'}
    apply_rows(p,proposal(p,scope))
    r['cues_placed']=True

def worker(pid,planid,runid):
    m=sm.main()
    try:
        with m.lock:
            p=m.get(pid);r=run_record(p,planid,runid)
            if not check(p,r):return
            if not r.get('prepared'):prepare_segments(p,r)
            commit(p,r,status='running',stage='narración');targets=list(r['targets'])
        for sid in targets:
            with m.lock:
                p=m.get(pid);r=run_record(p,planid,runid)
                if not check(p,r):return
                done=sid in r['done_segments']
                if done and not sm.wav_info(approved_audio(m.segment(p,sid))):raise HTTPException(409,'Un audio completado desapareció. Revisa el proyecto antes de reanudar.')
            if not done and not generate_one(pid,planid,runid,sid):return
        with m.lock:
            p=m.get(pid);r=run_record(p,planid,runid)
            if not check(p,r):return
            if not r.get('cues_placed'):place_cues(p,r)
            commit(p,r,stage='mezclando escenas');sceneids=list(r['scene_ids'])
        for sid in sceneids:
            with m.lock:
                p=m.get(pid);r=run_record(p,planid,runid)
                if not check(p,r):return
                clip=r['clips'].get(sid)
                if clip and sm.wav_info(clip['file']):continue
                scene=sm.scene_by_id(p,sid)
                if scene['missing'] or not 0<scene['duration']<=1800 or len(scene['segments'])>200 or len(sm.scene_cues(p,scene))>16:raise HTTPException(409,'La escena excede límites o tiene audio pendiente.')
                for cue in sm.scene_cues(p,scene):
                    sm.validate_cue(p,sm.Cue(**{k:v for k,v in cue.items() if k in sm.Cue.model_fields}))
                    if cue['offset']>=next(x['duration'] for x in scene['segments'] if x['id']==cue['segment_id']):raise HTTPException(409,'Una pista empieza fuera de su fragmento. Ajusta su entrada.')
                    if next(x['offset'] for x in scene['segments'] if x['id']==cue['segment_id'])+cue['offset']+cue['duration']>scene['duration']+.001:raise HTTPException(409,'Una pista existente rebasa la duración de la escena actualizada. Ajusta esa pista antes de producir.')
                captured=copy.deepcopy(p);before=r['state_token']
            output=m.DATA/('production_scene_'+uuid.uuid4().hex+'.wav')
            try:
                with tempfile.TemporaryDirectory(prefix='lia-chapter-scene-') as folder:credits=sm.render_scene(captured,scene,Path(folder),output)
                with m.lock:
                    p=m.get(pid);r=run_record(p,planid,runid)
                    if state(p)!=before:raise HTTPException(409,'El proyecto cambió durante la mezcla.')
                    r['clips'][sid]={'file':output.name,'credits':credits,'duration':scene['duration']};commit(p,r,completed=len(r['done_segments'])+len(r['clips']),completed_scenes=len(r['clips']))
            except BaseException:output.unlink(missing_ok=True);raise
        with m.lock:
            p=m.get(pid);r=run_record(p,planid,runid)
            if not check(p,r):return
            before=r['state_token'];clips=[copy.deepcopy(r['clips'][s]) for s in r['scene_ids']];commit(p,r,stage='exportando capítulo',message='Uniendo escenas y preparando MP3 equilibrado.')
        output=m.DATA/('production_chapter_'+uuid.uuid4().hex+'.wav');mp3=output.with_suffix('.mp3')
        try:
            with tempfile.TemporaryDirectory(prefix='lia-chapter-export-') as folder:
                listing=Path(folder)/'concat.txt';listing.write_text(''.join("file '"+str(sm.wav_info(x['file'])['path'])+"'\n" for x in clips))
                sm.ffmpeg(['-f','concat','-safe','0','-i',str(listing),'-c:a','pcm_s16le','-rf64','auto',str(output)])
            sm.ffmpeg(['-i',str(output),'-codec:a','libmp3lame','-b:a','128k',str(mp3)])
            with m.lock:
                p=m.get(pid);r=run_record(p,planid,runid)
                if state(p)!=before:raise HTTPException(409,'El proyecto cambió antes de registrar la exportación.')
                commit(p,r,status='ready',stage='terminado',file=output.name,mp3_file=mp3.name,credits='\n'.join(dict.fromkeys(x['credits'] for x in clips)),completed=r['total'],message='Prueba de capítulo terminada. Escúchala antes de aprobarla; no se marcó calidad como aprobada.')
        except BaseException:output.unlink(missing_ok=True);mp3.unlink(missing_ok=True);raise
    except Exception as e:
        with m.lock:
            try:
                p=m.get(pid);r=run_record(p,planid,runid);r.update(status='error',message=e.detail if isinstance(e,HTTPException) else 'La producción se interrumpió. Revisa el motor y reanuda.',updated_at=now());m.save(p)
            except HTTPException:pass
    finally:sm.ACTIVE.release()

@router.get('/runs/{run_id}/{kind}')
def download(pid:str,plan_id:str,run_id:str,kind:str,download:bool=False):
    with sm.main().lock:p=sm.main().get(pid);r=copy.deepcopy(run_record(p,plan_id,run_id))
    if r['status']!='ready':raise HTTPException(409,'La prueba de capítulo no está terminada.')
    if kind=='credits':return PlainTextResponse(r.get('credits',''),headers={'Content-Disposition':'attachment; filename="creditos_capitulo.txt"'})
    if kind not in ('wav','mp3'):raise HTTPException(404,'Formato no disponible.')
    path=safe_file(sm.main().DATA,r.get('file' if kind=='wav' else 'mp3_file'))
    if not path or not path.is_file():raise HTTPException(404,'El archivo ya no está disponible.')
    return FileResponse(path,media_type='audio/wav' if kind=='wav' else 'audio/mpeg',filename=('capitulo_'+run_id[:8]+'.'+kind) if download else None)

def recover():
    m=sm.main()
    with m.lock:
        with m.engine.connect() as db:projects=[json.loads(row[0]) for row in db.execute(sql('SELECT payload FROM projects'))]
        for p in projects:
            changed=False
            for r in p.get('production_runs',[]):
                if r.get('status') in ('running','queued'):r.update(status='interrupted',message='El servicio se reinició. Puedes reanudar con los pasos guardados.');changed=True
            if changed:m.save(p)
