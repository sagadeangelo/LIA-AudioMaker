import test from 'node:test';
import assert from 'node:assert/strict';
import {filterFragments} from '../src/fragmentFilters.ts';
import {selectableScope} from '../src/selection.ts';
const rows=[{id:'n',speaker:'Narrador',review:false},{id:'a',speaker:'Ángelo',review:false,kind:'narration'},{id:'u',speaker:'Sin atribuir',review:true},{id:'r',speaker:'Narrador',review:true},{id:'e',speaker:'Ana',review:false,excluded:true}];
const cast=[{id:'angelo',name:'ANGELO'},{id:'narrator',name:'Narrador'}];
test('default view keeps narration and characters without classification filtering',()=>{
 assert.deepEqual(filterFragments(rows,'all',cast),rows);
 assert.deepEqual(selectableScope(filterFragments(rows,'all',cast),'all').map(x=>x.id),['n','a','u','r']);
});
test('unassigned excludes the narrator and includes legacy empty/unknown labels',()=>{
 const extended=[...rows,{id:'empty',speaker:''},{id:'unknown',speaker:'SIN ASIGNAR'}];
 assert.deepEqual(filterFragments(extended,'unassigned',cast).map(x=>x.id),['u','empty','unknown']);
});
test('review filter follows editorial status regardless of speaker',()=>{
 assert.deepEqual(filterFragments(rows,'review',cast).map(x=>x.id),['u','r']);
});
test('character filter handles accents and legacy narration classification',()=>{
 assert.deepEqual(filterFragments(rows,'character:angelo',cast).map(x=>x.id),['a']);
 assert.deepEqual(filterFragments(rows,'character:narrator',cast).map(x=>x.id),['n','r']);
});
test('no matches is a real empty result without changing original rows',()=>{
 const before=JSON.stringify(rows);
 assert.deepEqual(filterFragments(rows,'character:missing',cast),[]);
 assert.equal(JSON.stringify(rows),before);
});
