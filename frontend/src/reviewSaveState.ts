export function reviewSaveState(response:{decision:string;note:string}|null,decision:string,note:string){
 const dirty=decision!==(response?.decision||'pending')||note.trim()!==(response?.note||'');
 const saved=!!response&&!dirty;
 const message=dirty?'Hay cambios sin guardar.':!response?'Todavía no hay una respuesta guardada.':response.decision==='needs_change'?'✓ Respuesta guardada. El cambio solicitado sigue pendiente de aplicar.':response.decision==='deferred'?'✓ Respuesta guardada. Decidiste resolver este punto después.':'✓ Respuesta guardada en el plan.';
 return {dirty,saved,message};
}
