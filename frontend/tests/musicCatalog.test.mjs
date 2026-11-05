import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/musicCatalog.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {isMusic,musicCategory,groupedMusic,categoryForMood}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('music metadata excludes effects even with a musical title',()=>{assert.equal(isMusic({id:'e',name:'Piano Calm',media_kind:'effect'}),false);assert.equal(isMusic({id:'m',name:'Mi pista',media_kind:'music'}),true);assert.equal(isMusic({id:'e',name:'respiración agitada'}),false)});
test('legacy titles grouped with manual override and saved assignment fallback',()=>{assert.equal(musicCategory({id:'1',name:'Tenderness'}),'Romántica');assert.equal(musicCategory({id:'2',name:'Drama Tension'}),'Suspenso');assert.equal(musicCategory({id:'2',name:'Drama Tension',music_category:'Drama'}),'Drama');assert.equal(isMusic({id:'3',name:'Mi pista'},['3']),true);assert.equal(groupedMusic([{id:'e',name:'risa'},{id:'m',name:'Piano Calm'}]).flatMap(g=>g.items).length,1)});

test('scene mood determines upload category independently of filename',()=>{assert.equal(categoryForMood('suspenso'),'Suspenso');assert.equal(categoryForMood('enojo'),'Ira / enojo');assert.equal(categoryForMood('asombro'),'Asombro');assert.equal(categoryForMood('alegría'),'Alegría');assert.equal(categoryForMood('narrativo suave'),'Documental / narrativa')});
test('custom music genres remain visible and separate from effects',()=>{
 const items=[{id:'custom',name:'Track',media_kind:'music',music_category:'Thriller atmosférico'},{id:'fx',name:'Rain',media_kind:'effect'}];
 assert.equal(musicCategory(items[0]),'Thriller atmosférico');
 assert.equal(groupedMusic(items).find(g=>g.category==='Thriller atmosférico').items[0].id,'custom');
});
