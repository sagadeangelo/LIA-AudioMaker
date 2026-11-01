import {useEffect,useRef} from 'react';
export type TrashedProject={id:string;title:string;deleted_at:string};
type Props={projects:TrashedProject[];busy:boolean;error:string;onClose:()=>void;onRestore:(id:string)=>void};
export function ProjectTrash({projects,busy,error,onClose,onRestore}:Props){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close()},[]);
 return <dialog className="project-trash" ref={dialog} aria-labelledby="trash-title" onCancel={e=>{e.preventDefault();if(!busy)onClose()}}><h2 id="trash-title">Papelera de proyectos</h2><p>Los proyectos eliminados salen de la biblioteca. Sus manuscritos, asignaciones y audios se conservan para poder restaurarlos.</p>{error&&<p role="alert">{error}</p>}
 {!projects.length?<p>La papelera está vacía.</p>:<ul>{projects.map(p=><li key={p.id}><div><strong>{p.title}</strong><small>Eliminado: {new Date(p.deleted_at).toLocaleString('es-MX')}</small></div><button disabled={busy} aria-label={'Restaurar '+p.title} onClick={()=>onRestore(p.id)}>Restaurar</button></li>)}</ul>}
 <button disabled={busy} onClick={onClose}>Cerrar papelera</button></dialog>
}
