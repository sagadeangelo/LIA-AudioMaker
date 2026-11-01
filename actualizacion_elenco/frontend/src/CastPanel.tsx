import {useState} from 'react';
export type CastCharacter={id:string;name:string;voice:string;speed:number;color:string};
type Props={projectId:string;characters:CastCharacter[];voices:string[];busy:boolean;selected:boolean;counts:Record<string,number>;onAssign:(id:string)=>void;onSave:(profile:Omit<CastCharacter,'id'>,id?:string)=>void};
export const CAST_MIME='application/x-lia-character';
export function CastPanel({projectId,characters,voices,busy,selected,counts,onAssign,onSave}:Props){
 const [query,setQuery]=useState(''),[form,setForm]=useState<CastCharacter|null>(null);
 const filtered=characters.filter(c=>c.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()));
 return <section className="cast-panel" aria-label="Elenco del libro"><div className="cast-heading"><h2>Elenco del libro <small>({characters.length})</small></h2><button disabled={busy} onClick={()=>setForm({id:'',name:'',voice:'es',speed:160,color:'#9C68FF'})}>+ Personaje</button></div>
 <p className="cast-help">Arrastra una tarjeta al manuscrito o al clip. También puedes seleccionar un fragmento y pulsar el nombre.</p>
 <input aria-label="Buscar personaje" placeholder="Buscar en todo el libro…" value={query} onChange={e=>setQuery(e.target.value)}/>
 <div className="cast-list">{filtered.map(c=><div key={c.id} className="cast-card" data-character-id={c.id} draggable={!busy} onDragStart={e=>{if(busy){e.preventDefault();return}e.dataTransfer.setData(CAST_MIME,JSON.stringify({projectId,characterId:c.id}));e.dataTransfer.effectAllowed='copy'}} style={{borderLeftColor:c.color}}>
 <button className="cast-assign" disabled={busy||!selected} aria-label={'Asignar '+c.name} onClick={()=>onAssign(c.id)}><b style={{color:c.color}}>{c.name}</b><small>{c.voice} · {c.speed} ppm · {counts[c.id]||0} fragmentos</small></button>
 <button className="cast-config" disabled={busy} aria-label={'Configurar '+c.name} onClick={()=>setForm({...c})}>Configurar</button></div>)}{!filtered.length&&<p>No hay coincidencias. Puedes agregar otro personaje.</p>}</div>
 {form&&<form className="cast-form" onSubmit={e=>{e.preventDefault();onSave({name:form.name.trim(),voice:form.voice,speed:form.speed,color:form.color},form.id||undefined)}}><h3>{form.id?'Voz del personaje':'Nuevo personaje'}</h3>
 <label>Nombre del personaje<input required maxLength={100} disabled={!!form.id||busy} value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label>
 <label>Voz del personaje<select aria-label="Voz del personaje" disabled={busy} value={form.voice} onChange={e=>setForm({...form,voice:e.target.value})}>{voices.map(v=><option key={v}>{v}</option>)}</select></label>
 <label>Velocidad del personaje<input type="number" min={80} max={300} required disabled={busy} value={form.speed} onChange={e=>setForm({...form,speed:+e.target.value})}/></label>
 <label>Color del personaje<input type="color" disabled={busy} value={form.color} onChange={e=>setForm({...form,color:e.target.value})}/></label>
 <p>Estos valores se aplican al asignar la tarjeta. Los fragmentos existentes conservan su configuración.</p>
 <button type="submit" disabled={busy||!form.name.trim()}>Guardar personaje</button><button type="button" disabled={busy} onClick={()=>setForm(null)}>Cerrar configuración</button>
 </form>}</section>
}
