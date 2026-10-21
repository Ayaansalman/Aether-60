import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {RunnerWorld} from '../src/game/runner/world.ts';
import {jumpEnvelope,reachableGate} from '../src/game/runner/challenges.ts';
import {ARCADE_ART} from '../src/game/runner/presentation.ts';
const spec=k=>JSON.parse(fs.readFileSync(new URL(`../../docs/evidence/iteration8/${k}/spec.json`,import.meta.url)));
const samples={};
function course(s,n=40){const w=new RunnerWorld(s),all=[];while(all.length<n){all.push(...w.obstacles.splice(0));w.distance=w.nextX-1100;w.populate();}return {w,all:all.slice(0,n)};}
test('contrasting specifications produce different measurable geometry and motifs',()=>{
 for(const k of ['A','B','C','D']){
  const {w,all}=course(spec(k));
  samples[k]={speed:w.spec.speed,max_speed:w.spec.max_speed,gap_height:w.spec.mode==='flap'?w.spec.gap_height:null,mean_width:all.reduce((a,o)=>a+o.width,0)/all.length,mean_spacing:all.slice(1).reduce((a,o,i)=>a+o.x-all[i].x-all[i].width,0)/(all.length-1),patterns:[...new Set(all.map(o=>o.pattern))],repairs:w.stream.repairs};
  assert.ok(samples[k].patterns.length>=4);assert.ok(w.stream.pending.length<=8);
 }
 assert.ok(samples.B.speed>samples.A.speed*1.7);assert.ok(samples.B.mean_width>samples.A.mean_width*1.7);
 assert.ok(samples.D.gap_height<samples.C.gap_height*.6);assert.ok(samples.D.mean_spacing/samples.D.speed<samples.C.mean_spacing/samples.C.speed*.7);
 fs.writeFileSync(new URL('../../docs/evidence/iteration8/comparison.json',import.meta.url),JSON.stringify(samples,null,2));
});
test('seeded phrases vary geometry and composition, restart is deterministic, active state stays bounded',()=>{
 for(const k of ['A','B','C','D']){
  const a=course(spec(k),24).all,b=course({...spec(k),seed:23},24).all;
  assert.notDeepEqual(a.map(o=>[o.kind,o.width,o.center,o.pattern]),b.map(o=>[o.kind,o.width,o.center,o.pattern]));
  const w=new RunnerWorld(spec(k)),initial=structuredClone(w.obstacles);
  for(let i=0;i<1200;i++){w.distance+=100;w.populate();w.obstacles=w.obstacles.filter(o=>o.x+o.width>w.distance-100);assert.ok(w.obstacles.length<12);assert.ok(w.stream.pending.length<=8);}
  assert.ok(w.serial>100);w.restart();assert.deepEqual(w.obstacles,initial);assert.equal(w.distance,0);assert.equal(w.score,0);
 }
});
test('ground phrases admit a real grounded-jump trajectory at both speed extremes',()=>{
 for(const key of ['A','B'])for(let seed=0;seed<12;seed++)for(const speed of [spec(key).speed,spec(key).max_speed]){
  const s={...spec(key),seed,speed,max_speed:speed,acceleration:0};
  const w=new RunnerWorld(s);let jumped=-1,passed=0;
  for(let i=0;i<25000&&passed<24;i++){
   const o=w.obstacles.find(o=>!o.passed);
   if(o&&o.id!==jumped&&o.x+o.width/2-(w.distance+180)<=speed*s.jump_impulse/s.gravity){w.action();jumped=o.id;}
   w.step(1/120);
   assert.equal(w.state,'playing',`${key} seed ${seed} speed ${speed} obstacle ${JSON.stringify(o)} y ${w.y}`);
   passed=w.obstacles.filter(o=>o.passed).length+Math.max(0,w.serial-w.obstacles.length-w.stream.pending.length);
  }
  assert.ok(passed>=24);
 }
});
test('flying beam rejects impossible corridors and retains witnesses across seeded phrases',()=>{
 const s=spec('D');assert.deepEqual(reachableGate(s,[{y:250,v:0}],100,{width:60,center:60,gap:10},500),[]);
 for(const k of ['C','D'])for(let seed=0;seed<15;seed++){
  const {w,all}=course({...spec(k),seed},35);assert.ok(w.stream.low.length&&w.stream.high.length);
  for(const o of all){assert.ok(o.gap>=28+s.flap_impulse**2/(2*s.gravity));assert.ok(o.center-o.gap/2>=30&&o.center+o.gap/2<=510);}
 }
});
test('physics bounds, finite finish, stable progression, scoring, collision and session best',()=>{
 const s=spec('B');const env=jumpEnvelope(s,60);assert.ok(env.apex>60&&env.clearWidth>0);
 const finite=new RunnerWorld({...s,endless:false,finish_distance:800});assert.ok(finite.obstacles.every(o=>o.x<=980));
 finite.obstacles=[];finite.nextX=1e9;for(let i=0;i<1000;i++)finite.step(1/120);assert.equal(finite.state,'won');const best=finite.best;finite.restart();assert.equal(finite.best,best);assert.equal(finite.score,0);
 const stable=new RunnerWorld({...spec('A'),progression:'stable'});stable.obstacles=[];stable.nextX=1e9;for(let i=0;i<2400;i++)stable.step(1/120);assert.equal(stable.speed,stable.spec.speed);
 const flap=new RunnerWorld(spec('C'));flap.obstacles=[{id:0,x:100,width:30,kind:'gate',center:250,gap:240,passed:false}];flap.nextX=1e9;flap.step(1/120);flap.step(1/120);assert.equal(flap.score,1);flap.y=1;flap.step(1/120);assert.equal(flap.state,'lost');flap.action();assert.equal(flap.score,0);assert.equal(flap.best,1);
});
test('themes select coherent distinct existing atlas roles and compositions',()=>{
 assert.equal(ARCADE_ART.forest.atlas,'terrain');assert.equal(ARCADE_ART.factory.atlas,'industrial');assert.notEqual(ARCADE_ART.forest.background,ARCADE_ART.factory.background);
 assert.equal(new Set(Object.values(ARCADE_ART).map(a=>a.sky)).size,5);
});
