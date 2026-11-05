import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const js=ts.transpileModule(fs.readFileSync(new URL('../src/musicProgress.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {musicProgress}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const scenes=[{id:'front',segments:[{id:'f'}]},{id:'one',music_suggestion:{},segments:[{id:'a'},{id:'b'}]},{id:'two',music_suggestion:{},segments:[{id:'c'}]}];
test('unique narrative scenes only, active music with an existing resource',()=>{const cues=[{role:'music',segment_id:'a',sound_id:'m'},{role:'music',segment_id:'b',sound_id:'m'},{role:'music',segment_id:'f',sound_id:'m'},{role:'effect',segment_id:'c',sound_id:'m'},{role:'music',segment_id:'c',sound_id:'missing'},{role:'music',segment_id:'c',sound_id:'m',active:false}];assert.deepEqual(musicProgress(scenes,cues,['m']),{completed:1,total:2,remaining:1,percent:50})});
test('empty, pending without cues and complete projects',()=>{assert.equal(musicProgress([],[],[]).percent,0);assert.equal(musicProgress(scenes,[],['m']).completed,0);assert.equal(musicProgress(scenes,[{role:'music',segment_id:'a',sound_id:'m'},{role:'music',segment_id:'c',sound_id:'m'}],['m']).percent,100)});
