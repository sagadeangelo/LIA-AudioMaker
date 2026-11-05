import VoicePronunciationEdit from './VoicePronunciationEdit';
import IncorporatePronunciation from './IncorporatePronunciation';
import React,{useEffect,useRef,useState} from 'react';
import {voiceLabel,voiceGroup,isSupportedVoice} from './voiceConfig';
type Occurrence={segment_id:string;chapter:string;chapter_number:number;fragment_number:number;scene:number;text:string;count:number;excluded:boolean;review:boolean;eligible:boolean};
type Group={character_id:string|null;speaker:string;voice:string;speed:number;pronunciation:string;voice_override_id?:string|null;count:number;eligible_count:number;occurrences:Occurrence[]};
type View={original:string;groups:Group[];total:number;eligible_count:number;snapshot_token:string;rules:{id:string;original:string;pronunciation:string;provider:string;character_id:string|null;uniform?:boolean}[]};
type Sample={id:string;text:string;voice:string;speed:number;status:string;result?:{file:string};errors:{message:string}[]};
type Props={projectId:string;original:string;pronunciation:string;disabled:boolean;onBusyChange:(busy:boolean)=>void;onUpdate:(p:any)=>void;onSaved:(original:string,pronunciation:string)=>Promise<void>};
async function api(path:string,method='GET',body?:unknown){const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(r.status===404&&j.detail==='Not Found'?'El backend no tiene esta ruta de Voice Editor. Reconstruye el backend y comprueba su versión en /openapi.json; después recarga con Ctrl+F5.':typeof j.detail==='string'?j.detail:JSON.stringify(j.detail));return j}
export default function NameMentions({projectId,original,pronunciation,disabled,onBusyChange,onUpdate,onSaved}:Props){
 const [query,setQuery]=useState(original),[phonetic,setPhonetic]=useState(pronunciation),[view,setView]=useState<View|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[confirmed,setConfirmed]=useState(false),[testConfirmed,setTestConfirmed]=useState(false),[samples,setSamples]=useState<Sample[]>([]),[progress,setProgress]=useState(''),[editing,setEditing]=useState<Group|null>(null);
 const inFlight=useRef(false),stop=useRef(false),mounted=useRef(true);
 const base=`/projects/${projectId}/voice-editor`;
 useEffect(()=>{const removed=(event:Event)=>setSamples(xs=>xs.filter(s=>s.id!==(event as CustomEvent<string>).detail));window.addEventListener('lia-audition-deleted',removed);return()=>window.removeEventListener('lia-audition-deleted',removed)},[]);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;stop.current=true;onBusyChange(false)}},[]);
 useEffect(()=>{if(original.trim()&&original!==query){setQuery(original);setView(null);setConfirmed(false);setTestConfirmed(false)}},[original]);
 useEffect(()=>{setPhonetic(pronunciation);setConfirmed(false);setTestConfirmed(false)},[pronunciation]);
 async function run(fn:()=>Promise<void>){if(inFlight.current)return;inFlight.current=true;setBusy(true);onBusyChange(true);setError('');try{await fn()}catch(e){if(mounted.current)setError(String(e))}finally{inFlight.current=false;if(mounted.current){setBusy(false);onBusyChange(false)}}}
 const distinct=view?.groups.filter(g=>g.eligible_count>0&&isSupportedVoice(g.voice)).filter((g,i,all)=>all.findIndex(x=>x.voice===g.voice&&x.speed===g.speed)===i)||[];
 async function testAll(){if(!view)return;const name=view.original,spelling=phonetic.trim(),targets=[...distinct];stop.current=false;
 for(let i=0;i<targets.length;i++){
  if(stop.current||!mounted.current)break;
  const g=targets[i];setProgress(`Probando voz ${i+1} de ${targets.length}: ${voiceLabel(g.voice)}`);
  let j:Sample=await api(base+'/auditions','POST',{original:name,pronunciation:g.voice_override_id?g.pronunciation:spelling,voice:g.voice,speed:g.speed});
  while(['queued','running'].includes(j.status)){
   await new Promise(resolve=>setTimeout(resolve,800));j=await api(base+'/jobs/'+j.id);
  }
  if(mounted.current){if(j.result)setSamples(xs=>[j,...xs]);else setError(j.errors[0]?.message||'Prueba interrumpida. Las muestras terminadas se conservan.')}
 }
 if(mounted.current){setProgress(stop.current?'Pruebas detenidas; las muestras terminadas se conservan.':'Pruebas finalizadas. Escucha cada voz antes de guardar.');window.dispatchEvent(new Event('lia-auditions-changed'))}
 }
 const locked=busy||disabled;
 return <section className="voice-preview" aria-label="Quiénes dicen este nombre"><h3>Quiénes dicen este nombre</h3><p>Historial de menciones en el manuscrito, agrupado por hablante y voz. La regla global sirve como base para todos, incluido el narrador. Puedes guardar excepciones de pronunciación por voz.</p>
 <label>Nombre que quieres localizar<input aria-label="Nombre que quieres localizar" maxLength={200} value={query} disabled={locked} placeholder="Ángelo" onChange={e=>{setQuery(e.target.value);setView(null);setConfirmed(false);setTestConfirmed(false)}}/></label>
 <button type="button" disabled={locked||!query.trim()} onClick={()=>run(async()=>{setView(await api(base+'/mentions?original='+encodeURIComponent(query.trim())));setConfirmed(false);setTestConfirmed(false)})}>Buscar menciones</button>
 {error&&<p className="error" role="alert">{error}</p>}
 {view&&<><p role="status">{view.total} menciones · {view.groups.length} grupos de hablante/voz · {view.eligible_count} menciones listas para producir.</p>{view.groups.map((g,i)=><div key={i}><button type="button" disabled={locked||!isSupportedVoice(g.voice)} onClick={()=>setEditing(g)}>Editar pronunciación · {voiceLabel(g.voice)}</button><details><summary>{g.speaker} · {voiceLabel(g.voice)} · {g.count} menciones</summary><small>{voiceGroup(g.voice)} · {g.speed}x · {g.eligible_count} listas · Pronunciación guardada: {g.pronunciation}{g.voice_override_id?' (ajuste de voz)':''}</small>{g.voice_override_id&&<button type="button" disabled={locked} onClick={()=>run(async()=>{const result=await api(base+'/voice-pronunciation/'+g.voice_override_id,'DELETE');setView(result.mentions)})}>Volver a pronunciación global</button>}{g.occurrences.map(o=><article className="voice-version" key={o.segment_id}><b>{o.chapter_number}. {o.chapter} · Escena {o.scene} · Fragmento {o.fragment_number}</b><small>{o.count} mención(es){o.excluded?' · Quitado del audiolibro':o.review||!o.eligible?' · Revisión pendiente':''}</small><p>{o.text}</p></article>)}</details></div>)}
 <label>Una misma pronunciación para todas las voces<input aria-label="Una misma pronunciación para todas las voces" maxLength={300} value={phonetic} disabled={locked} onChange={e=>{setPhonetic(e.target.value);setConfirmed(false);setTestConfirmed(false)}}/></label>
 <p>Se probarán {distinct.length} combinaciones distintas de voz y velocidad, una muestra por combinación. Diferentes motores pueden interpretar la misma escritura de forma distinta: escúchalas antes de guardar.</p>
 <label><input type="checkbox" disabled={locked} checked={testConfirmed} onChange={e=>setTestConfirmed(e.target.checked)}/>Confirmo generar estas muestras. Las voces Azure consumen cuota.</label>
 <button type="button" disabled={locked||!distinct.length||!phonetic.trim()||!testConfirmed} onClick={()=>run(testAll)}>Probar con todas estas voces</button>
 {busy&&progress&&<button type="button" onClick={()=>{stop.current=true}}>Detener después de la muestra actual</button>}{progress&&<p role="status">{progress}</p>}
 {view.rules.length>0&&<details><summary>{view.rules.length} regla(s) activa(s) para este nombre</summary>{view.rules.map(r=><p key={r.id}>{r.original} → {r.pronunciation} · {r.provider} · {r.character_id?'Un personaje':'Todos los hablantes'}{r.uniform?' · Uniforme':''}</p>)}</details>}
 <label><input type="checkbox" checked={confirmed} disabled={locked} onChange={e=>setConfirmed(e.target.checked)}/>Confirmo guardar esta pronunciación para todos los hablantes y motores. Las otras reglas de este nombre se desactivarán y conservarán en el historial; los ajustes explícitos por voz se conservan.</label>
 <button type="button" className="primary" disabled={locked||!view.total||!phonetic.trim()||!confirmed} onClick={()=>run(async()=>{const result=await api(base+'/uniform-pronunciation','PUT',{original:view.original,pronunciation:phonetic,snapshot_token:view.snapshot_token,confirmed:true});setView(result.mentions);setConfirmed(false);await onSaved(result.rule.original,result.rule.pronunciation);setProgress('Pronunciación uniforme guardada. Los audios existentes se conservan; revisa y regenera solo los fragmentos que quieras actualizar.')})}>Guardar pronunciación uniforme</button>
 <p>Guardar no regenera ni sustituye los audios existentes. Las futuras generaciones usarán la regla global. Para actualizar el libro, revisa la incorporación y confirma el lote.</p><IncorporatePronunciation projectId={projectId} original={view.original} revision={view.snapshot_token} disabled={locked} onUpdate={book=>{onUpdate(book);api(base+'/mentions?original='+encodeURIComponent(view.original)).then(setView).catch(e=>setError(String(e)))}}/></>}
 {samples.map(s=><article className="voice-version" key={s.id}><b>{voiceLabel(s.voice)} · {s.speed}x</b><p>Texto probado: {s.text}</p><button type="button" disabled={locked||!view?.groups.some(g=>g.voice===s.voice)} onClick={()=>setEditing(view?.groups.find(g=>g.voice===s.voice)||null)}>Editar esta voz</button><audio controls preload="none" src={'/api/audio/'+s.result!.file}/><small>Esta muestra también aparece en el laboratorio, donde puedes eliminarla.</small></article>)}
 {editing&&view&&<VoicePronunciationEdit projectId={projectId} original={view.original} voice={editing.voice} speed={editing.speed} initial={editing.voice_override_id?editing.pronunciation:phonetic||editing.pronunciation} onClose={()=>setEditing(null)} onSaved={next=>{setView(next);setConfirmed(false);setTestConfirmed(false)}}/>}
 </section>;
}
