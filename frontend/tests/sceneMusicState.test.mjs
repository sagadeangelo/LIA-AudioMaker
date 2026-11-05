import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/sceneMusicState.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {sceneMusicAssignments,primaryMusic,resolveMusicChoice}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const sounds=[{id:'a',name:'Piano'},{id:'b',name:'Suspenso'}];
test('saved music and volume restore from server cues after reloading',()=>{
 const saved={sound_id:'a',volume_db:-7,active:true};
 assert.deepEqual(resolveMusicChoice(saved,undefined,sounds),{sound_id:'a',volume_db:-7,pending:false,savedName:'Piano',selectedName:'Piano'});
});
test('pending uploaded choice restores separately from applied music and ignores deleted resources',()=>{
 const saved={sound_id:'a',volume_db:-12};
 const draft={sound_id:'b',volume_db:-8};
 const choice=resolveMusicChoice(saved,draft,sounds);
 assert.equal(choice.sound_id,'b');assert.equal(choice.pending,true);assert.equal(choice.savedName,'Piano');
 assert.equal(resolveMusicChoice(saved,{sound_id:'deleted',volume_db:-4},sounds).sound_id,'a');
});
test('scene music badges use music only and prefer latest active assignment',()=>{
 const cues=[{id:'1',role:'music',segment_id:'s1',sound_id:'a',volume_db:-8},{id:'2',role:'effect',segment_id:'s1',sound_id:'b',volume_db:-2},{id:'3',role:'music',segment_id:'s2',sound_id:'b',volume_db:-5},{id:'4',role:'music',segment_id:'s1',sound_id:'b',volume_db:-4,active:false}];
 const assigned=sceneMusicAssignments(cues,['s1']);assert.equal(assigned.length,2);
 assert.equal(primaryMusic(assigned).id,'1');
 assert.equal(sceneMusicAssignments(cues,['other']).length,0);
});
test('chapter default only fills unassigned scenes and preserves explicit exceptions',()=>{
 assert.equal(resolveMusicChoice(undefined,undefined,sounds,-18).volume_db,-18);
 assert.equal(resolveMusicChoice({sound_id:'a',volume_db:-9},undefined,sounds,-18).volume_db,-9);
 assert.equal(resolveMusicChoice(undefined,{sound_id:'b',volume_db:-21},sounds,-18).volume_db,-21);
});
