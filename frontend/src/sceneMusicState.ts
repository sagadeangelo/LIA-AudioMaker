export type MusicAssignment={id?:string;sound_id:string;volume_db:number;active?:boolean};
export type MusicChoice={sound_id:string;volume_db:number};
export function sceneMusicAssignments(cues:Array<MusicAssignment&{role?:string;segment_id:string}>,segmentIds:string[]):MusicAssignment[]{
 const ids=new Set(segmentIds);return cues.filter(c=>c.role==='music'&&ids.has(c.segment_id));
}
export function primaryMusic(items:MusicAssignment[]):MusicAssignment|undefined{return [...items].reverse().find(c=>c.active!==false)||items.at(-1)}
export function resolveMusicChoice(saved:MusicAssignment|undefined,pending:MusicChoice|undefined,sounds:Array<{id:string;name:string}>,defaultVolume=-12){
 const draft=pending&&sounds.some(s=>s.id===pending.sound_id)?pending:undefined;
 const selected=draft||saved;
 return {sound_id:selected?.sound_id||'',volume_db:selected?.volume_db??defaultVolume,
  pending:!!draft&&(draft.sound_id!==saved?.sound_id||draft.volume_db!==saved?.volume_db),
  savedName:sounds.find(s=>s.id===saved?.sound_id)?.name||'Pista no disponible',
  selectedName:sounds.find(s=>s.id===selected?.sound_id)?.name||'Pista no disponible'};
}
