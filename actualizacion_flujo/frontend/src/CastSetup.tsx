import {useEffect,useRef,useState} from 'react';
import type {CastCharacter} from './CastPanel';
export function voiceLabel(id:string){const language=id.startsWith('es')?'Español':'Inglés';return `${language} · ${id.includes('+f')?'Femenina básica':id.includes('+m')?'Masculina básica':'Voz base'} (${id})`}
type Props={characters:CastCharacter[];voices:string[];busy:boolean;error:string;tts:boolean;onClose:()=>void;onApply:(rows:CastCharacter[],audio:boolean)=>void};
export function CastSetup({characters,voices,busy,error,tts,onClose,onApply}:Props){
 const [step,setStep]=useState(0),[rows,setRows]=useState(characters.map(c=>({...c})));
 const dialog=useRef<HTMLDialogElement>(null),player=useRef<HTMLAudioElement|null>(null);
 const [previewing,setPreviewing]=useState(false),[previewError,setPreviewError]=useState('');
 useEffect(()=>()=>{player.current?.pause()},[]);
 async function preview(voice:string,speed:number){setPreviewing(true);setPreviewError('');try{player.current?.pause();const response=await fetch('/api/voices/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voice,speed})});const result=await response.json();if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'No se pudo generar la muestra');if(!dialog.current?.open)return;player.current=new Audio('/api/audio/'+result.file);await player.current.play()}catch(e){setPreviewError(String(e))}finally{setPreviewing(false)}}
 useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close()},[]);
 const count=characters.filter(c=>c.name.toLowerCase()!=='narrador').length;
 function edit(id:string,field:string,value:unknown){setRows(xs=>xs.map(x=>x.id===id?{...x,[field]:value}:x))}
 return <dialog ref={dialog} className="cast-setup" aria-labelledby="cast-setup-title" onCancel={e=>{e.preventDefault();if(!busy)onClose()}}><h2 id="cast-setup-title">{step===0?'Tu manuscrito: reparto de voces':'Elige las voces del libro'}</h2>
 {(error||previewError)&&<p role="alert">{error||previewError}</p>}<p>Se encontraron <b>{count} personajes o roles con atribución</b>, además del narrador. Revisa el elenco: puede contener variantes o nombres por completar.</p>
 {step===0?<><p>¿Deseas configurar una voz para cada personaje y aplicarla a sus diálogos en todos los capítulos?</p><div className="setup-actions"><button className="primary" disabled={busy} onClick={()=>setStep(1)}>Sí, elegir voces</button><button disabled={busy} onClick={onClose}>Revisar después</button></div></>:<>
 <p>Catálogo actual: voces básicas en español e inglés. Las voces infantiles, de ancianos y con actuación emocional todavía no están disponibles. Los valores iniciales son las voces actuales de cada perfil.</p>
 <div className="setup-rows">{rows.map(c=><div className="setup-row" key={c.id}><strong>{c.name}<button className="voice-preview" disabled={busy||previewing||!tts} onClick={()=>preview(c.voice,c.speed)}>Escuchar {c.name}</button></strong><label>Voz para {c.name}<select aria-label={'Voz para '+c.name} disabled={busy} value={c.voice} onChange={e=>edit(c.id,'voice',e.target.value)}>{voices.map(v=><option key={v} value={v}>{voiceLabel(v)}</option>)}</select></label><label>Velocidad para {c.name}<input type="number" min={80} max={300} disabled={busy} value={c.speed} onChange={e=>edit(c.id,'speed',+e.target.value)}/></label><label>Color para {c.name}<input type="color" disabled={busy} value={c.color} onChange={e=>edit(c.id,'color',e.target.value)}/></label></div>)}</div>
 <p>Se aplicará a las atribuciones conocidas de todo el libro. Los hablantes desconocidos y las acotaciones pendientes requerirán revisión. Cambiar una voz deja su audio anterior pendiente de regenerar.</p>
 <div className="setup-actions"><button disabled={busy||rows.some(c=>c.speed<80||c.speed>300)} onClick={()=>onApply(rows,false)}>Guardar voces y aplicar</button><button className="primary" disabled={busy||!tts||rows.some(c=>c.speed<80||c.speed>300)} onClick={()=>onApply(rows,true)}>Aplicar voces y procesar audio</button><button disabled={busy} onClick={onClose}>Cerrar</button></div></>}
 </dialog>
}
