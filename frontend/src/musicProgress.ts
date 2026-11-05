type ProgressScene={id:string;music_suggestion?:unknown;segments:Array<{id:string}>};
type ProgressCue={role?:string;segment_id:string;sound_id:string;active?:boolean};
export function musicProgress(scenes:ProgressScene[],cues:ProgressCue[],soundIds:string[]){
 const available=new Set(soundIds);
 const active=new Set(cues.filter(c=>c.role==='music'&&c.active!==false&&available.has(c.sound_id)).map(c=>c.segment_id));
 const eligible=scenes.filter(s=>!!s.music_suggestion);
 const completed=eligible.filter(s=>s.segments.some(x=>active.has(x.id))).length;
 return {completed,total:eligible.length,remaining:eligible.length-completed,percent:eligible.length?Math.round(completed/eligible.length*100):0};
}
