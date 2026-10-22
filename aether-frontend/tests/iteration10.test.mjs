import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {bossStep} from '../src/game/platformer/gameplay.ts';
import {RunnerWorld} from '../src/game/runner/world.ts';

test('three configured boss attacks have distinct windups, outputs and one-shot slam emission',()=>{
 const patterns=['charge','volley','slam'];
 for(let cycle=1;cycle<=3;cycle++){
  const memory={phase:'windup',at:0,direction:-1,cycle};
  const early=bossStep(memory,699,20,20,100,700,40,968,700,1500,patterns);
  assert.equal(early.memory.phase,'windup');assert.equal(early.fire,false);assert.equal(early.slam,false);
  const attack=bossStep(memory,700,20,20,100,700,40,968,700,1500,patterns);
  assert.equal(attack.pattern,patterns[cycle-1]);assert.equal(attack.fire,cycle===2);assert.equal(attack.slam,cycle===3);
  const next=bossStep(attack.memory,760,20,20,100,700,40,968,700,1500,patterns);
  assert.equal(next.fire,false);assert.equal(next.slam,false);assert.equal(next.vx!==0,cycle===1);
 }
});

test('easy and extreme courses differ in actual speed, obstacle width and reaction time',()=>{
 const load=k=>JSON.parse(fs.readFileSync(new URL(`../../docs/evidence/iteration8/${k}/spec.json`,import.meta.url)));
 const measure=s=>{
  const w=new RunnerWorld(s),all=[];
  while(all.length<30){all.push(...w.obstacles.splice(0));w.distance=w.nextX-1100;w.populate();}
  const obstacles=all.slice(0,30);
  return {speed:s.speed,width:obstacles.reduce((a,o)=>a+o.width,0)/30,reaction:obstacles.slice(1).reduce((a,o,i)=>a+(o.x-obstacles[i].x-obstacles[i].width)/s.speed,0)/29};
 };
 const easy=measure(load('A')),extreme=measure(load('B'));
 assert.ok(extreme.speed>easy.speed*1.7);assert.ok(extreme.width>easy.width*1.7);assert.ok(extreme.reaction<easy.reaction*.8);
});
