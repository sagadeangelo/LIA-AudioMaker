export type CatalogSound={id:string;name:string;media_kind?:'music'|'effect';music_category?:string};
export const musicCategories=['Romántica','Ira / enojo','Asombro','Drama','Suspenso','Acción / épica','Fantasía','Tristeza','Alegría','Calma','Documental / narrativa','Sin clasificar'];
const rules:Array<[string,RegExp]>=[
 ['Romántica',/romantic|romant|tender|love|amor/],['Suspenso',/tension|suspens|mister|mystery|shadow|thriller|horror/],
 ['Acción / épica',/epic|epica|action|accion|escape corridor|battle/],['Fantasía',/fantasy|fantasia|magical|magic/],
 ['Tristeza',/sad|triste|melanchol|melancol/],['Alegría',/happy|joyful|alegr|uplifting/],
 ['Calma',/calm|relax|peaceful|warm winter/],['Drama',/drama|emotional/],['Documental / narrativa',/documentary|documental|background history|cinematic|cinemat|narrativ/]];
export function musicCategory(s:CatalogSound){if(s.music_category&&s.music_category!=='Sin clasificar')return s.music_category;const n=s.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();return rules.find(([,re])=>re.test(n))?.[0]||'Sin clasificar'}
export function isMusic(s:CatalogSound,knownIds:string[]=[]){if(s.media_kind)return s.media_kind==='music';if(knownIds.includes(s.id))return true;return musicCategory(s)!=='Sin clasificar'||/\b(music|musica|piano|instrumental|soundtrack)\b/i.test(s.name)}
export function groupedMusic(sounds:CatalogSound[],knownIds:string[]=[]){return Array.from(new Set([...musicCategories,...sounds.map(musicCategory)])).map(category=>({category,items:sounds.filter(s=>isMusic(s,knownIds)&&musicCategory(s)===category).sort((a,b)=>a.name.localeCompare(b.name,'es'))})).filter(g=>g.items.length)}

export function categoryForMood(mood:string){const n=mood.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();return ({suspenso:'Suspenso',ira:'Ira / enojo',enojo:'Ira / enojo',asombro:'Asombro',euforia:'Alegría',alegria:'Alegría',tristeza:'Tristeza',ternura:'Romántica','narrativo suave':'Documental / narrativa'} as Record<string,string>)[n]||'Sin clasificar'}
