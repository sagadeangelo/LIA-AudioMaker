export type SelectionFragment={id:string;speaker?:string;kind?:string;text?:string;source_text?:string;excluded?:boolean;is_separator?:boolean};
const normalized=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
const candidateKinds=new Set(['dialogue','dialogue_candidate','thought_or_quote','aside_candidate','thought','quote']);
const editorialLabels=new Set(['ISBN','NOTA','NOTAS','COPYRIGHT','URL','HTTP','HTTPS','ADVERTENCIA']);
export function isStructural(fragment:SelectionFragment){
 return !!fragment.is_separator||/^\s*(?:(?:\*\s*){3,}|#{3,}|(?:\.\s*){5,}|(?:…\s*){2,})\s*$/.test(fragment.source_text||fragment.text||'');
}
export function isDialogueCandidate(fragment:SelectionFragment){
 if(fragment.excluded||isStructural(fragment))return false;
 if(candidateKinds.has(fragment.kind||''))return true;
 // Human speaker assignment takes precedence over an outdated import kind.
 const speaker=normalized(fragment.speaker||'');
 if(speaker&&speaker!=='narrador')return true;
 // Older projects may not carry kind metadata or correctly detected labels.
 const source=(fragment.source_text||fragment.text||'').trimStart();
 if(/^[—–«“"]/.test(source))return true;
 const label=source.match(/^([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ .]{1,44}):\s*\S/);
 return !!label&&!editorialLabels.has(label[1].trim());
}
export function selectableScope(fragments:SelectionFragment[],scope:string){
 return fragments.filter(x=>!x.excluded&&!isStructural(x)&&(scope==='all'||isDialogueCandidate(x)));
}
