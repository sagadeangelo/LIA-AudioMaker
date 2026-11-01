import test from 'node:test';
import assert from 'node:assert/strict';
import {isDialogueCandidate,selectableScope} from '../src/selection.ts';
const f=(values={})=>({id:'one',speaker:'Narrador',kind:'narration',text:'Texto de narración.',...values});
test('manual speaker overrides stale narration kind',()=>{
 assert.equal(isDialogueCandidate(f({speaker:'Ángelo'})),true);
 assert.equal(isDialogueCandidate(f({speaker:' ANA '})),true);
});
test('plain narration stays outside dialogue scope',()=>{
 assert.equal(isDialogueCandidate(f()),false);
 assert.equal(isDialogueCandidate(f({speaker:' NARRADOR '})),false);
});
test('thoughts and aside candidates remain selectable even with narrator assigned',()=>{
 for(const kind of ['dialogue','thought_or_quote','aside_candidate','dialogue_candidate'])assert.equal(isDialogueCandidate(f({kind})),true);
});
test('legacy dialogue labels and markers are included',()=>{
 for(const source_text of ['ANGELO: Hola.','—¿Qué pasó?','«Mi pensamiento».'])assert.equal(isDialogueCandidate(f({source_text})),true);
 assert.equal(isDialogueCandidate(f({source_text:'ISBN: 12345'})),false);
});
test('excluded and structural records are never selected',()=>{
 assert.equal(isDialogueCandidate(f({speaker:'Ana',excluded:true})),false);
 for(const text of ['. . . . . . .','................','***'])assert.equal(isDialogueCandidate(f({speaker:'Ana',text})),false);
});
test('both scopes reflect just the supplied visible fragments',()=>{
 const rows=[f({id:'n'}),f({id:'a',speaker:'Ana'}),f({id:'q',kind:'thought_or_quote'}),f({id:'removed',excluded:true,speaker:'Ana'})];
 assert.deepEqual(selectableScope(rows,'dialogues').map(x=>x.id),['a','q']);
 assert.deepEqual(selectableScope(rows,'all').map(x=>x.id),['n','a','q']);
 assert.deepEqual(selectableScope(rows.slice(0,1),'dialogues'),[]);
});
