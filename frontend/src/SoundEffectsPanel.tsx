import AutoMusic from './AutoMusic';
import SoundChecklist, {type Recommendation} from './SoundChecklist';
import SoundMixer from './SoundMixer';
import {isMusic} from './musicCatalog';
import SceneSoundReview from './SceneSoundReview';
import SoundDiscovery from './SoundDiscovery';
import ProjectSoundApply from './ProjectSoundApply';
import UploadSound from './UploadSound';
import {useEffect, useRef, useState} from 'react';
import './SoundEffectsPanel.css';

type Sound = {media_kind?:'music'|'effect';music_category?:string;id?:string; freesound_id?:number; name:string; author:string; source_url:string; license:string; license_url:string; duration:number; preview_url?:string; importable?:boolean; file?:string; conversion?:string};
type Connection = {configured:boolean; oauth_available:boolean; connected:boolean};
type Results = {count:number; page:number; has_next:boolean; results:Sound[]};
async function call(path:string, options:RequestInit={}) {
  const r=await fetch('/api'+path, options); const d=await r.json();
  if(!r.ok) throw new Error(typeof d.detail==='string'?d.detail:'No se pudo completar la operación.');
  return d;
}
const json=(body:unknown)=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const seconds=(n:number)=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;

export default function SoundEffectsPanel({projectId,disabled}:{projectId:string;disabled?:boolean}) {
  const [tab,setTab]=useState<'effects'|'music'|'assembly'>('effects');
  function navigate(next:'effects'|'music'|'assembly'){panel.current?.querySelectorAll('audio').forEach(a=>a.pause());if(next!==tab)setRecommendation(null);setTab(next);panel.current?.scrollTo({top:0});}
  const [open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [status,setStatus]=useState<Connection|null>(null),[sounds,setSounds]=useState<Sound[]>([]);
  const [query,setQuery]=useState('ocean waves'),[license,setLicense]=useState('cc0'),[results,setResults]=useState<Results|null>(null);
  const [lastSearch,setLastSearch]=useState({q:'',license:'cc0'});
  const [auth,setAuth]=useState<{state:string;url:string}|null>(null),[code,setCode]=useState('');
  const [recommendation,setRecommendation]=useState<Recommendation|null>(null),[checklistRevision,setChecklistRevision]=useState(0);
  const searchForm=useRef<HTMLFormElement>(null);
  const resultsHeading=useRef<HTMLHeadingElement>(null);
  const [searching,setSearching]=useState(false),[searchError,setSearchError]=useState('');
  useEffect(()=>{if(searching||results||searchError){resultsHeading.current?.scrollIntoView({block:'start'});resultsHeading.current?.focus({preventScroll:true})}},[searching,results,searchError]);
  const [reviewTarget,setReviewTarget]=useState({id:'',token:0});
  const panel=useRef<HTMLElement>(null);
  async function run(task:()=>Promise<void>){setBusy(true);setError('');setMessage('');try{await task()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  useEffect(()=>{const listener=()=>{setOpen(true);setTab('effects');void run(refresh)};window.addEventListener('lia-open-sound-library',listener);return()=>window.removeEventListener('lia-open-sound-library',listener)},[projectId]);
  async function refresh(){const [s,l]=await Promise.all([call('/freesound/status'),call(`/projects/${projectId}/sound-effects`)]);setStatus(s);setSounds(l.sounds)}
  function close(){panel.current?.querySelectorAll('audio').forEach(a=>a.pause());setOpen(false);setCode('');setAuth(null)}
  async function performSearch(selected:{q:string;license:string},page:number){
    selected={...selected,q:selected.q.trim().slice(0,150)};
    setResults(null);setSearchError('');setSearching(true);setLastSearch(selected);
    await run(async()=>{try{const d=await call(`/freesound/search?q=${encodeURIComponent(selected.q)}&license=${selected.license}&page=${page}`);setResults(d)}catch(e){setSearchError((e as Error).message)}finally{setSearching(false)}})
  }
  async function search(page=1,fresh=false){await performSearch(fresh?{q:query,license}:lastSearch,page)}
  async function chooseRecommendation(item:Recommendation){setRecommendation(item);const q=item.query.trim().slice(0,150);setQuery(q);await performSearch({q,license},1)}
  async function linkRecommendation(sound:Sound){if(!recommendation||!sound.id)return;await call(`/projects/${projectId}/sound-checklist/${recommendation.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({sound_id:sound.id})});setChecklistRevision(n=>n+1);setRecommendation(null)}
  const audio=(sound:Sound)=><audio aria-label={`Escuchar ${sound.name}`} controls preload="none" src={sound.file?'/api/audio/'+encodeURIComponent(sound.file):sound.preview_url} onPlay={e=>panel.current?.querySelectorAll('audio').forEach(a=>{if(a!==e.currentTarget)a.pause()})}/>;
  const metadata=(sound:Sound)=><><strong>{sound.name}</strong><p>Por {sound.author} · {seconds(sound.duration)} · {sound.license}</p><p>{sound.source_url?<a href={sound.source_url} target="_blank" rel="noreferrer">Ver en Freesound</a>:<span>Archivo subido al proyecto</span>}{sound.license_url&&<> · <a href={sound.license_url} target="_blank" rel="noreferrer">Licencia</a></>}</p></>;
  return <><button disabled={disabled} onClick={()=>{setOpen(true);void run(refresh)}}>LIA Sound Effects</button>{open&&<div className="voice-editor-overlay"><section ref={panel} className="voice-editor sound-effects-panel" role="dialog" aria-modal="true" aria-label="LIA Sound Effects" onKeyDown={e=>{if(e.key==='Escape'&&!busy)close()}}>
    <div className="voice-editor-heading"><h2>LIA Sound Effects</h2><button disabled={busy} onClick={close}>Cerrar</button></div>
    <nav className="sound-workspace-tabs" role="tablist" aria-label="Secciones de sonido">{([['effects','Efectos de sonido'],['music','Música de fondo'],['assembly','Montaje y exportación']] as const).map(([id,label])=><button key={id} id={`sound-tab-${id}`} role="tab" aria-selected={tab===id} aria-controls={`sound-panel-${id}`} onClick={()=>navigate(id)}>{label}</button>)}</nav>
    <p className="notice">Busca, escucha y guarda efectos para este proyecto. Usa el mezclador por escena para crear una prueba con narración y efectos. Los audios originales se conservan.</p>
    {error&&<p className="error" role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
    <section id="sound-panel-music" role="tabpanel" aria-labelledby={tab==='music'?'sound-tab-music':'sound-tab-assembly'} hidden={tab==='effects'}>{tab==='music'&&<AutoMusic projectId={projectId} onChanged={()=>setChecklistRevision(n=>n+1)}/>}<SoundMixer view={tab==='music'?'music':'assembly'} projectId={projectId} libraryRevision={sounds.length+checklistRevision} focusSceneId={reviewTarget.id} focusToken={reviewTarget.token} onMusicSearch={q=>{navigate('music');setRecommendation(null);setQuery(q);void performSearch({q,license},1)}} onChanged={()=>setChecklistRevision(n=>n+1)}/></section>
    <div hidden={tab==='assembly'}>{status&&<><p>Credenciales: {status.configured?'configuradas':'no disponibles en el backend'} · Cuenta para originales: {status.connected?'conectada':'pendiente de conectar'}</p>
      {!status.configured&&<p>Comprueba FREESOUND_API_KEY en .env y reconstruye el backend con el actualizador del paquete.</p>}
      {!status.connected?<button disabled={busy||!status.oauth_available} onClick={()=>void run(async()=>{setAuth(await call('/freesound/oauth/start',json({})));setCode('')})}>Conectar cuenta para originales</button>:
      <button disabled={busy} onClick={()=>void run(async()=>{setStatus(await call('/freesound/oauth',{method:'DELETE'}));setAuth(null);setCode('');setMessage('Sesión eliminada de LIA. Tus sonidos guardados se conservan.')})}>Desconectar de LIA</button>}
      {auth&&<div className="voice-version"><p>1. <a href={auth.url} target="_blank" rel="noreferrer">Abrir autorización en Freesound</a> y autorizar LIA AudioMaker.</p><p>2. Copia el código temporal que muestra Freesound y pégalo aquí. No es tu API Key. El proceso caduca en 10 minutos.</p><label>Código temporal <input autoComplete="off" type="password" value={code} onChange={e=>setCode(e.target.value)}/></label><button disabled={busy||!code.trim()} onClick={()=>void run(async()=>{try{setStatus(await call('/freesound/oauth/finish',json({state:auth.state,code:code.trim()})));setMessage('Cuenta conectada. Ya puedes guardar originales en la biblioteca.')}finally{setAuth(null);setCode('')}})}>Completar conexión</button></div>}
    </>}
    </div><section id="sound-panel-effects" role="tabpanel" aria-labelledby="sound-tab-effects" hidden={tab!=='effects'}>
    <SoundDiscovery projectId={projectId} busy={busy} onChanged={()=>setChecklistRevision(n=>n+1)}/>
    <SoundChecklist projectId={projectId} sounds={sounds} revision={checklistRevision} busy={busy} onSearch={item=>void chooseRecommendation(item)} onComplete={id=>{void run(refresh);setChecklistRevision(n=>n+1);if(recommendation?.id===id)setRecommendation(null)}}/>
    </section><div hidden={tab==='assembly'}><h3>{tab==='music'?'Buscar música en Freesound':'Buscar en Freesound'}</h3>{recommendation&&<div className="sound-recommendation-target">Buscando un recurso para: <strong>{recommendation.label}</strong>. Al guardarlo se marcará como disponible en la lista. <button disabled={busy} onClick={()=>setRecommendation(null)}>Buscar sin vincular recomendación</button></div>}<form ref={searchForm} onSubmit={e=>{e.preventDefault();void search(1,true)}}><label>Qué sonido necesitas <input aria-label="Buscar sonidos" value={query} onChange={e=>setQuery(e.target.value)} maxLength={150}/></label><label>Licencia <select value={license} onChange={e=>setLicense(e.target.value)}><option value="cc0">CC0</option><option value="by">CC BY · requiere atribución</option></select></label><button disabled={busy||!status?.configured||query.trim().length<2}>Buscar sonidos</button></form>
    <p>Prueba: ocean waves (olas), seagulls (gaviotas), footsteps (pasos), car horn (claxon). Máximo por original: 50 MB y 10 minutos. No se descargan colecciones completas.</p>
    <section className="freesound-results" aria-label="Resultados de Freesound" aria-busy={searching}>
    <h3 ref={resultsHeading} tabIndex={-1}>Resultados de Freesound</h3>
    {(searching||results||searchError)&&<p>Consulta: <strong>{lastSearch.q}</strong> · Licencia: {lastSearch.license==='cc0'?'CC0':'CC BY'}</p>}
    {searching&&<p role="status">Buscando en Freesound…</p>}
    {searchError&&<p className="error" role="alert">No se pudo realizar la búsqueda: {searchError}</p>}
    {!searching&&!results&&!searchError&&<p>Los resultados de las búsquedas aparecerán aquí. La biblioteca inferior contiene solo los sonidos que ya guardaste.</p>}
    {results&&<><p>{results.count} resultados · página {results.page}</p>{results.results.length===0&&<p>No se encontraron sonidos para esta consulta. Prueba palabras más cortas o en inglés en «Qué sonido necesitas» y pulsa Buscar sonidos. Puedes cambiar la licencia a CC BY si aceptas su atribución.</p>}{results.results.map(sound=><article className="voice-version" key={sound.freesound_id}>{metadata(sound)}{sound.preview_url?audio(sound):<p>Sin muestra disponible.</p>}<p><button disabled={busy||!status?.connected||!sound.importable||sounds.some(s=>s.freesound_id===sound.freesound_id)} onClick={()=>void run(async()=>{const d=await call(`/projects/${projectId}/sound-effects/freesound`,json({sound_id:sound.freesound_id}));if(tab==='music'){await call(`/projects/${projectId}/sound-mixer/library/${d.sound.id}/classification`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({media_kind:'music'})})}await refresh();if(recommendation){await linkRecommendation(d.sound);setMessage('Sonido guardado y recomendación marcada como disponible.')}else{setMessage(d.already_saved?'Este sonido ya está guardado.':'Sonido guardado en la biblioteca del proyecto.')}setChecklistRevision(n=>n+1)})}>{sounds.some(s=>s.freesound_id===sound.freesound_id)?'Ya guardado':'Guardar original en biblioteca'}</button>{recommendation&&sounds.some(s=>s.freesound_id===sound.freesound_id)&&<button disabled={busy} onClick={()=>void run(async()=>{await linkRecommendation(sounds.find(s=>s.freesound_id===sound.freesound_id)!);setMessage('Recomendación vinculada al sonido que ya tenías guardado.')})}>Usar para {recommendation.label}</button>}</p>{!sound.importable&&<p>Este resultado no cumple los límites o licencias admitidas.</p>}</article>)}<button disabled={busy||results.page<=1} onClick={()=>void search(results.page-1)}>Anterior</button><button disabled={busy||!results.has_next} onClick={()=>void search(results.page+1)}>Siguiente</button></>}
    </section>
    </div><section id="sound-panel-assembly" role="tabpanel" aria-labelledby="sound-tab-assembly" hidden={tab!=='assembly'}>
    <SceneSoundReview projectId={projectId} revision={checklistRevision} busy={busy} onChanged={()=>setChecklistRevision(n=>n+1)} onEdit={id=>{navigate('assembly');setReviewTarget(old=>({id,token:old.token+1}))}}/>
    <ProjectSoundApply projectId={projectId} revision={checklistRevision} busy={busy}/>
    </section><details hidden={tab==='assembly'}><summary>Biblioteca de {tab==='music'?'música':'efectos'} ({sounds.filter(s=>isMusic({...s,id:s.id||''})===(tab==='music')).length})</summary><UploadSound projectId={projectId} kind={tab==='music'?'music':'effect'} busy={busy} onSaved={()=>{void run(refresh);setChecklistRevision(n=>n+1)}}/>{!sounds.length&&<p>Aún no hay efectos guardados.</p>}{sounds.filter(s=>isMusic({...s,id:s.id||''})===(tab==='music')).map(sound=><article key={sound.id} className="voice-version">{metadata(sound)}{audio(sound)}<p>{sound.conversion}. Conserva esta atribución: «{sound.name}» — {sound.author}, {sound.freesound_id?`Freesound #${sound.freesound_id}`:'Archivo aportado por el usuario'}, {sound.license}. {sound.source_url}</p><button disabled={busy} onClick={()=>void run(async()=>{if(!window.confirm('¿Quitar este sonido de la biblioteca y de sus escenas? Las versiones ya mezcladas se conservan.'))return;await call(`/projects/${projectId}/sound-checklist/library/${sound.id}`,{method:'DELETE'});await refresh();setChecklistRevision(n=>n+1);setMessage('Sonido quitado del proyecto. Genera una nueva versión para reflejarlo en el audio.');})}>Quitar de la biblioteca</button></article>)}
    </details>
  </section></div>}</>;
}
