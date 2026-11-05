import test from 'node:test';
import assert from 'node:assert/strict';
import {visibleReviewEntries,selectableEntry} from '../src/analysisSelection.ts';
test('filtered selection preserves original report indexes for sounds',()=>{
 const r={sound_suggestions:[{label:'mar'},{label:'gaviotas'},{label:'claxon'}]};
 assert.deepEqual(visibleReviewEntries(r,'sound_suggestions','GAVIOTAS',true).map(e=>e.id),['1']);
});
test('weak names hidden by filter do not enter select all',()=>{
 const r={names:[{id:'a',name:'María',evidence_level:'débil'},{id:'b',name:'Lindsay',evidence_level:'fuerte'}]};
 assert.deepEqual(visibleReviewEntries(r,'names','',false).map(e=>e.id),['b']);
 assert.deepEqual(visibleReviewEntries(r,'names','Maria',false).map(e=>e.id),['a']);
});
test('select all skips decided names, existing casting, animals and unbound editorial scenes',()=>{
 assert(!selectableEntry({id:'x',category:'sound',item:{}},{'sound:x':'reject'}));
 for(const item of [{existing_character_id:'c'},{kind:'animal'},{evidence:[]}])assert(!selectableEntry({id:'x',category:'name',item},{}));
 assert(!selectableEntry({id:'s',category:'editorial_scene',item:{status:'missing'}},{}));
 assert(selectableEntry({id:'s',category:'editorial_scene',item:{status:'matched'}},{}));
});
test('scene plan selection includes only sounds of visible scenes and deduplicates cues',()=>{
 const r={scene_plan:[{chapter:'Costa',ambience:[{item_id:'0'}],effects:[{item_id:'1'}],context_review:[]},{chapter:'Casa',ambience:[{item_id:'2'}],effects:[],context_review:[]}]};
 assert.deepEqual(visibleReviewEntries(r,'scene_plan','Costa',true).map(e=>[e.category,e.id]),[['sound','0'],['sound','1']]);
 assert.equal(visibleReviewEntries(r,'scene_plan','sin coincidencia',true).length,0);
});

import {reviewStats} from '../src/analysisSelection.ts';
test('93 authorized places reduce tab pending count to zero without deleting report data',()=>{
 const report={places:Array.from({length:93},(_,i)=>({id:String(i),name:'Lugar '+i}))};
 const decisions=Object.fromEntries(report.places.map(x=>['place:'+x.id,'confirm']));
 assert.deepEqual(reviewStats(report,'places',decisions),{total:93,pending:0,reviewed:93,references:0});
 assert.equal(report.places.length,93);
});
test('counts include both individual confirmations and rejections with stable ids',()=>{
 const report={sound_suggestions:[{label:'mar'},{label:'gaviotas'},{label:'claxon'}]};
 assert.equal(reviewStats(report,'sound_suggestions',{'sound:0':'confirm','sound:2':'reject'}).pending,1);
 assert.equal(reviewStats(report,'sound_suggestions',{'sound:0':'confirm','sound:1':'reject','sound:2':'reject'}).pending,0);
});
test('scene plan counts share sound decisions and references remain separate from pending work',()=>{
 const report={scene_plan:[{ambience:[{item_id:'0'}],effects:[{item_id:'1'}],context_review:[]}],editorial_scenes:[{id:'s1',status:'matched'},{id:'s2',status:'missing'}],names:[{id:'a',existing_character_id:'c',evidence:[{}]},{id:'b',kind:'animal',evidence:[{}]},{id:'c',evidence:[{}]}]};
 assert.equal(reviewStats(report,'scene_plan',{'sound:0':'confirm','sound:1':'reject'}).pending,0);
 assert.deepEqual(reviewStats(report,'editorial_scenes',{'editorial_scene:s1':'confirm'}),{total:2,pending:0,reviewed:1,references:1});
 assert.deepEqual(reviewStats(report,'names',{}),{total:3,pending:1,reviewed:0,references:2});
});
