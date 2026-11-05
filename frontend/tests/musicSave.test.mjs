import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import ts from 'typescript';
const js=ts.transpileModule(fs.readFileSync(new URL('../src/musicSave.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {musicJson,verifyMusicSaved,waitMusic}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('confirms exact active song and volume in selected scene',()=>{
 const selected={scene_id:'a',sound_id:'new',volume_db:-12};const data={scenes:[{id:'a',segments:[{id:'seg'}]}],cues:[{role:'music',sound_id:'new',segment_id:'seg',volume_db:-12,active:true}]};
 assert.doesNotThrow(()=>verifyMusicSaved(data,selected));
 for(const changes of [{sound_id:'old'},{volume_db:-26},{active:false},{segment_id:'elsewhere'}])assert.throws(()=>verifyMusicSaved({...data,cues:[{...data.cues[0],...changes}]},selected),/no confirmó/);
});
test('exposes backend validation errors and malformed responses',async()=>{
 const old=globalThis.fetch;try{
 globalThis.fetch=async()=>new Response(JSON.stringify({detail:'La escena tiene audio pendiente'}),{status:409});await assert.rejects(musicJson('/test'),/audio pendiente/);
 globalThis.fetch=async()=>new Response('<html>offline</html>');await assert.rejects(musicJson('/test'),/respuesta no válida/);
 globalThis.fetch=async()=>new Response(JSON.stringify({detail:[{msg:'Valor fuera de rango'}]}),{status:422});await assert.rejects(musicJson('/test'),/fuera de rango/);
 }finally{globalThis.fetch=old}
});
test('stalled autosave and request fail visibly instead of waiting forever',async()=>{
 await assert.rejects(waitMusic(new Promise(()=>{}),5),/tardando/);
 const old=globalThis.fetch;try{globalThis.fetch=async(_url,init)=>new Promise((_,reject)=>init.signal.addEventListener('abort',()=>reject(new Error('aborted'))));await assert.rejects(musicJson('/test',{},5),/confirmación/)}finally{globalThis.fetch=old}
});
