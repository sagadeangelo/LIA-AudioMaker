import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/audioExportOptions.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {formatAudioBytes,estimatedMp3Bytes}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('four-hour book estimates scale by bitrate and distinguish decimal file sizes',()=>{
 const duration=15981.241084;
 assert.equal(estimatedMp3Bytes(duration,96),191774893);
 assert.equal(estimatedMp3Bytes(duration,128),255699857);
 assert.equal(estimatedMp3Bytes(duration,192),383549786);
 assert.equal(formatAudioBytes(3068398402),'3.07 GB');
 assert.equal(formatAudioBytes(255699857),'255.7 MB');
});
test('actual sizes and unavailable originals never display misleading zero estimates',()=>{
 assert.equal(formatAudioBytes(undefined),'No disponible');
 assert.equal(formatAudioBytes(null),'No disponible');
 assert.equal(formatAudioBytes(12000),'12.0 kB');
 assert.equal(estimatedMp3Bytes(-1,96),0);
});
