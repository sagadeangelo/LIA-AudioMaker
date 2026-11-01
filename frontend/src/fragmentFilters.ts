export type FragmentFilterInput={id:string;speaker?:string;review?:boolean};
export type FilterCharacter={id:string;name:string};
const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
export function filterFragments<T extends FragmentFilterInput>(fragments:T[],filter:string,characters:FilterCharacter[]):T[]{
 if(filter==='all')return [...fragments];
 if(filter==='unassigned')return fragments.filter(x=>!normalize(x.speaker||'')||['sin atribuir','sin asignar'].includes(normalize(x.speaker||'')));
 if(filter==='review')return fragments.filter(x=>!!x.review);
 if(filter.startsWith('character:')){
  const character=characters.find(c=>c.id===filter.slice('character:'.length));
  return character?fragments.filter(x=>normalize(x.speaker||'')===normalize(character.name)):[];
 }
 return [];
}
