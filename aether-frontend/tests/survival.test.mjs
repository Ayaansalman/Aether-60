import {test} from 'node:test';
import assert from 'node:assert/strict';
import {emitterStep,safeSpawn} from '../src/game/survival/stream.ts';
test('exact five single shots at one-second intervals; expiry only after fifth',()=>{
 const cfg={shooter_shots:5,shot_interval_ms:1000};let shots=0,at=0;
 for(let n=1;n<=5;n++){
  const early=emitterStep(shots,at,n*1000-1,cfg);assert.equal(early.fire,false);
  const next=emitterStep(shots,at,n*1000,cfg);assert.equal(next.fire,true);assert.equal(next.shots,n);assert.equal(next.expired,n===5);shots=next.shots;at=next.lastAt;
 }
 assert.equal(emitterStep(shots,at,99999,cfg).fire,false);
});
test('lag does not emit five catch-up bullets together',()=>{
 const a=emitterStep(0,0,9000,{shooter_shots:5,shot_interval_ms:1000});assert.equal(a.shots,1);
 assert.equal(emitterStep(a.shots,a.lastAt,9000,{shooter_shots:5,shot_interval_ms:1000}).fire,false);
});
test('safe spawn never falls back onto the player when no safe sample exists',()=>{
 assert.equal(safeSpawn(()=>.5,960,540,{x:480,y:285},200),null);
 const p=safeSpawn(()=>0,960,540,{x:480,y:270},200);assert.ok(p);assert.ok(Math.hypot(p.x-480,p.y-270)>=200);
});
