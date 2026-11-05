import {useState} from 'react';
type Row={scene_id:string;title:string;number:number;status:string;category?:string;name?:string;reason?:string};
type Preview={token:string;rows:Row[];counts:Record<string,number>};
export default function AutoMusic({projectId,onChanged}:{projectId:string;onChanged:()=>void}){
 const [data,setData]=useState<Preview|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 async function run(save=false){setBusy(true);setMessage('');try{
  const r=await fetch(`/api/projects/${projectId}/sound-mixer/auto-music`,save?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:data?.token})}:{cache:'no-store'});
  const d=await r.json();if(!r.ok)throw Error(d.detail||'No se pudo preparar la música.');
  if(save){setMessage(`${d.assigned} escenas con música asignada y guardada. Genera una preescucha o una nueva mezcla para escuchar los cambios.`);setData(null);onChanged()}else setData(d);
 }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <section className="voice-version"><h3>Música automática desde tu biblioteca</h3><p>Completa las escenas sin música según su ambiente sugerido y las categorías guardadas. Alterna canciones y conserva las asignaciones existentes. El análisis disponible orienta la elección; puedes sustituirla después.</p><button disabled={busy} onClick={()=>void run()}>{busy?'Procesando…':'Preparar música automáticamente'}</button>{data&&<><p>{data.counts.assign||0} por completar · {data.counts.preserved||0} conservadas · {data.counts.editorial||0} sin propuesta · {data.counts.pending||0} pendientes por recursos o narración.</p><details><summary>Ver selección y pendientes</summary>{data.rows.map(r=><p key={r.scene_id}>{r.title} · escena {r.number}: {r.name?`${r.category} — ${r.name}`:r.reason}</p>)}</details><button disabled={busy||!data.counts.assign} onClick={()=>void run(true)}>Asignar y guardar toda la música pendiente</button></>}{message&&<p role="status">{message}</p>}</section>
}
