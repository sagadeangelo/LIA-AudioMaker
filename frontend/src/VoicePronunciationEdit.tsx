import React,{useEffect,useState} from 'react';
import {voiceLabel,voiceGroup} from './voiceConfig';
type Sample={id:string;status:string;text:string;result?:{file:string};errors:{message:string}[]};
type Props={projectId:string;original:string;voice:string;speed:number;initial:string;onClose:()=>void;onSaved:(view:any)=>void};
async function api(path:string,method='GET',body?:unknown){const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail));return j}
export default function VoicePronunciationEdit({projectId,original,voice,speed,initial,onClose,onSaved}:Props){
 const [text,setText]=useState(initial),[phrase,setPhrase]=useState(''),[samples,setSamples]=useState<Sample[]>([]),[job,setJob]=useState<Sample|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[deleting,setDeleting]=useState('');const base=`/projects/${projectId}/voice-editor`;
 useEffect(()=>{if(!job)return;let stopped=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{try{const j:Sample=await api(base+'/jobs/'+job.id);if(stopped)return;if(['queued','running'].includes(j.status))timer=setTimeout(poll,800);else{setJob(null);if(j.result){setSamples(xs=>[j,...xs]);window.dispatchEvent(new Event('lia-auditions-changed'))}else setError(j.errors[0]?.message||'Prueba interrumpida')}}catch(e){if(!stopped){setError(String(e));timer=setTimeout(poll,2500)}}};timer=setTimeout(poll,400);return()=>{stopped=true;clearTimeout(timer)}},[job?.id]);
 async function run(fn:()=>Promise<void>){if(busy)return;setBusy(true);setError('');try{await fn()}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function removeSample(sample:Sample){
  if(busy||job||deleting)return;
  if(!window.confirm('¿Eliminar esta muestra de prueba? Se borrará su WAV. El ajuste de pronunciación y los audios del libro se conservan.'))return;
  const players=Array.from(document.querySelectorAll<HTMLAudioElement>('audio')).filter(audio=>audio.getAttribute('src')==='/api/audio/'+sample.result!.file);
  players.forEach(audio=>{audio.pause();audio.removeAttribute('src');audio.load()});
  setDeleting(sample.id);
  await run(async()=>{
   try{await api(base+'/auditions/'+sample.id,'DELETE');setSamples(xs=>xs.filter(s=>s.id!==sample.id));window.dispatchEvent(new CustomEvent('lia-audition-deleted',{detail:sample.id}));window.dispatchEvent(new Event('lia-auditions-changed'))}
   catch(e){players.forEach(audio=>{audio.src='/api/audio/'+sample.result!.file});throw e}
   finally{setDeleting('')}
  });
 }
 const locked=busy||!!job||!!deleting;
 return <div className="voice-editor-overlay" style={{zIndex:100}}><section className="voice-editor" style={{maxWidth:620}} role="dialog" aria-modal="true" aria-labelledby="voice-adjust-title"><div className="voice-editor-heading"><h2 id="voice-adjust-title">Editar pronunciación por voz</h2><button onClick={onClose}>Cerrar ajuste</button></div><p><b>{voiceLabel(voice)}</b> · {voiceGroup(voice)} · {speed}x</p><p>Este ajuste de «{original}» se aplicará a todos los personajes que usen esta voz. Las demás voces conservarán su pronunciación.</p>
 <label>Pronunciación para esta voz<input aria-label="Pronunciación para esta voz" maxLength={300} value={text} disabled={locked} onChange={e=>setText(e.target.value)}/></label><label>Frase de prueba para esta voz (opcional)<textarea aria-label="Frase de prueba para esta voz" maxLength={1000} value={phrase} disabled={locked} placeholder={`Debe contener «${original}». Vacía para probar solo el nombre.`} onChange={e=>setPhrase(e.target.value)}/></label>{voice.startsWith('es-')&&<p>Generar esta prueba consume cuota de Azure.</p>}
 <button type="button" disabled={locked||!text.trim()} onClick={()=>run(async()=>{setJob(await api(base+'/auditions','POST',{original,pronunciation:text,voice,speed,phrase}))})}>Probar ajuste de voz</button><button type="button" className="primary" disabled={locked||!text.trim()} onClick={()=>run(async()=>{const result=await api(base+'/voice-pronunciation','PUT',{original,pronunciation:text,voice});onSaved(result.mentions);onClose()})}>Guardar ajuste de voz</button>
 {job&&<p role="status">Generando muestra…</p>}{error&&<p className="error" role="alert">{error}</p>}{samples.map(s=><article className="voice-version" key={s.id}><b>{voiceLabel(voice)}</b><p>{s.text}</p><audio controls preload="none" src={'/api/audio/'+s.result!.file}/><button type="button" className="remove-action" disabled={locked} onClick={()=>removeSample(s)}>{deleting===s.id?'Eliminando…':'Eliminar muestra'}</button></article>)}<p>Guardar no incorpora aún el cambio al libro. Usa después «Incorporar en el audio». Puedes eliminar aquí los intentos que no te gusten; el borrado es permanente y no elimina el ajuste guardado.</p>
 </section></div>;
}
