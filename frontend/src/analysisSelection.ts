export type ReviewEntry={id:string;category:string;item:Record<string,any>};
const categories:Record<string,string>={names:'name',places:'place',scenes:'current_scene',scene_candidates:'scene',emotions:'emotion',sound_suggestions:'sound',editorial_scenes:'editorial_scene'};
export const searchKey=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
export function visibleReviewEntries(report:any,tab:string,search:string,showWeak:boolean):ReviewEntry[]{
 if(!report)return [];
 const matches=(item:any)=>!search||searchKey(JSON.stringify(item)).includes(searchKey(search));
 if(tab==='scene_plan'){
  const result:ReviewEntry[]=[];
  for(const scene of report.scene_plan||[]){if(!matches(scene))continue;for(const group of ['ambience','effects','context_review'])for(const cue of scene[group]||[])result.push({id:cue.item_id,category:'sound',item:cue});}
  return [...new Map(result.map(e=>[e.id,e])).values()];
 }
 const category=categories[tab];if(!category)return [];
 return (report[tab]||[]).map((item:any,index:number)=>({id:String(item.id??index),category,item})).filter((e:ReviewEntry)=>matches(e.item)&&!(tab==='names'&&!showWeak&&!search&&e.item.evidence_level==='débil'));
}
export function selectableEntry(e:ReviewEntry,decisions:Record<string,string>):boolean{
 if(decisions[e.category+':'+e.id])return false;
 if(e.category==='name'&&(e.item.existing_character_id||e.item.kind==='animal'||!e.item.evidence?.length))return false;
 if(e.category==='editorial_scene'&&e.item.status!=='matched')return false;
 return true;
}
export function reviewStats(report:any,tab:string,decisions:Record<string,string>){
 const entries=visibleReviewEntries(report,tab,'',true);
 return {total:entries.length,pending:entries.filter(e=>selectableEntry(e,decisions)).length,
  reviewed:entries.filter(e=>!!decisions[e.category+':'+e.id]).length,
  references:entries.filter(e=>!decisions[e.category+':'+e.id]&&!selectableEntry(e,decisions)).length};
}
