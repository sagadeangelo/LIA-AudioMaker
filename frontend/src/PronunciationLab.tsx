import React,{useEffect,useRef,useState} from 'react';
import {VoiceOptions} from './VoiceOptions';
import {voiceLabel,isSupportedVoice} from './voiceConfig';
type Sample={id:string;status:string;text:string;voice:string;speed:number;variant:string;result?:{file:string};errors:{message:string}[]};
type Props={projectId:string;original:string;pronunciation:string;voices:string[];provider:string;preferredVoice?:string;preferredSpeed?:number;disabled:boolean};
async function api(path:string,body?:unknown,method?:string){const r=await fetch('/api'+path,{method:method||(body===undefined?'GET':'POST'),headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data}
export default function PronunciationLab({projectId,original,pronunciation,voices,provider,preferredVoice,preferredSpeed,disabled}:Props){
 const [voice,setVoice]=useState(''),[speed,setSpeed]=useState(1),[phrase,setPhrase]=useState(''),[samples,setSamples]=useState<Sample[]>([]),[job,setJob]=useState<Sample|null>(null),[pending,setPending]=useState(false),[error,setError]=useState(''),[deleting,setDeleting]=useState('');
 const request=useRef(false);
 useEffect(()=>{let stopped=false;const refresh=()=>api(`/projects/${projectId}/voice-editor/auditions`).then((js:Sample[])=>{if(stopped)return;const auditions=js.filter((j:any)=>j.audition);setSamples(auditions.filter(j=>j.result).reverse());setJob(auditions.find(j=>['queued','running'].includes(j.status))||null)}).catch(e=>{if(!stopped)setError(String(e))});refresh();window.addEventListener('lia-auditions-changed',refresh);return()=>{stopped=true;window.removeEventListener('lia-auditions-changed',refresh)}},[projectId]);
 const available=[...new Set(voices)].filter(v=>isSupportedVoice(v)&&(provider==='all'||(provider==='kokoro'?v.startsWith('em_')||v.startsWith('ef_'):v.startsWith('es-'))));
 useEffect(()=>{setVoice(available.includes(preferredVoice||'')?preferredVoice!:available[0]||'');setSpeed(preferredSpeed&&preferredSpeed>=.5&&preferredSpeed<=2?preferredSpeed:1)},[preferredVoice,preferredSpeed,provider,available.join('|')]);
 useEffect(()=>{if(!job)return;let stopped=false;let timer:ReturnType<typeof setTimeout>;async function poll(){try{const next:Sample=await api(`/projects/${projectId}/voice-editor/jobs/${job!.id}`);if(stopped)return;if(['queued','running'].includes(next.status)){timer=setTimeout(poll,800)}else{setJob(null);if(next.result)setSamples(xs=>[next,...xs]);else setError(next.errors[0]?.message||'Prueba interrumpida. Puedes volver a intentarlo.')}}catch(e){if(!stopped){setError(String(e));timer=setTimeout(poll,2500)}}}timer=setTimeout(poll,300);return()=>{stopped=true;clearTimeout(timer)}},[job?.id,projectId]);
 async function audition(variant:string){if(request.current||job)return;request.current=true;setPending(true);setError('');try{setJob(await api(`/projects/${projectId}/voice-editor/auditions`,{original,pronunciation,phrase,voice,speed,variant}))}catch(e){setError(String(e))}finally{request.current=false;setPending(false)}}
 async function removeSample(sample:Sample){
  if(request.current||job)return;
  if(!window.confirm('¿Eliminar esta muestra de prueba? Se borrará su archivo de audio. Las reglas y los audios del libro se conservan.'))return;
  request.current=true;setDeleting(sample.id);setError('');
  const players=Array.from(document.querySelectorAll<HTMLAudioElement>('audio')).filter(audio=>audio.getAttribute('src')==='/api/audio/'+sample.result!.file);
  players.forEach(audio=>{audio.pause();audio.removeAttribute('src');audio.load()});
  try{await api(`/projects/${projectId}/voice-editor/auditions/${sample.id}`,undefined,'DELETE');setSamples(xs=>xs.filter(s=>s.id!==sample.id));window.dispatchEvent(new CustomEvent('lia-audition-deleted',{detail:sample.id}))}catch(e){players.forEach(audio=>{audio.src='/api/audio/'+sample.result!.file});setError(String(e))}finally{request.current=false;setDeleting('')}
 }
 const locked=disabled||pending||!!job||!!deleting;
 return <section className="voice-preview pronunciation-lab" aria-label="Laboratorio de pronunciación"><h3>Probar antes de guardar</h3><p>Elige una voz del catálogo y ajusta letras o acentos hasta que suene como deseas. Esta prueba no guarda reglas ni cambia el casting o los audios del libro.</p>
 <label>Voz de prueba<select aria-label="Voz de prueba" value={voice} disabled={locked||!available.length} onChange={e=>setVoice(e.target.value)}>{!available.length&&<option value="">No hay voces en este catálogo</option>}<VoiceOptions voices={available}/></select></label>
 <label>Velocidad de prueba · {speed.toFixed(2)}x<input aria-label="Velocidad de prueba" type="range" min="0.5" max="2" step="0.05" value={speed} disabled={locked} onChange={e=>setSpeed(+e.target.value)}/></label>
 <label>Frase de prueba (opcional)<textarea aria-label="Frase de prueba" maxLength={1000} value={phrase} disabled={locked} placeholder={original?`Escribe una frase que contenga «${original}», o déjala vacía para escuchar solo la palabra.`:'Escribe primero la palabra original.'} onChange={e=>setPhrase(e.target.value)}/></label>
 <p>Original: <b>{original||'—'}</b> · Pronunciación: <b>{pronunciation||'—'}</b></p>
 {voice.startsWith('es-')&&<p>Esta prueba usa Azure y consume caracteres de la cuota de tu servicio.</p>}
 <button type="button" disabled={locked||!voice||!original.trim()||!pronunciation.trim()} onClick={()=>audition('original')}>Escuchar original</button><button type="button" className="primary" disabled={locked||!voice||!original.trim()||!pronunciation.trim()} onClick={()=>audition('replacement')}>Probar pronunciación</button>
 {job&&<p role="status">Generando muestra… Puedes cerrar el editor y la prueba terminará en el servidor.</p>}{error&&<p role="alert" className="error">{error}</p>}
 {samples.map(s=><article key={s.id} className="voice-version"><b>{s.variant==='original'?'Original de prueba':'Pronunciación de prueba'}</b><small>{voiceLabel(s.voice)} · {s.speed}x</small><p>Texto enviado: {s.text}</p><audio controls preload="none" aria-label={'Muestra '+s.id} src={'/api/audio/'+s.result!.file}/><button type="button" className="remove-action" disabled={locked} onClick={()=>removeSample(s)}>{deleting===s.id?'Eliminando…':'Eliminar muestra'}</button></article>)}
 </section>;
}
