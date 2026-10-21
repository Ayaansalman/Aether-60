import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RunnerWorld} from '../src/game/runner/world.ts';
import {bossStep} from '../src/game/platformer/gameplay.ts';
const base={schema_version:'2.2',genre:'runner',title:'test',seed:7,mode:'ground',theme:'neon',player:'robot',endless:true,finish_distance:3000,speed:300,max_speed:440,acceleration:2,gravity:1500,jump_impulse:590,flap_impulse:310,gap_height:190,obstacles:['spike','gap','laser'],scoring:'distance',unsupported:[],requirements:[]};
test('seeded generation continues with bounded state and reaction margins',()=>{
 for(let seed=0;seed<20;seed++){const w=new RunnerWorld({...base,seed});const first=structuredClone(w.obstacles);for(let i=0;i<20000;i++){w.distance+=70;w.populate();w.obstacles=w.obstacles.filter(o=>o.x+o.width>w.distance-100);assert.ok(w.obstacles.length<10);for(let j=1;j<w.obstacles.length;j++)assert.ok(w.obstacles[j].x-w.obstacles[j-1].x-w.obstacles[j-1].width>=base.max_speed*(2*base.jump_impulse/base.gravity+.72)-.01);}assert.ok(w.serial>500);w.restart();assert.deepEqual(w.obstacles,first);}
});
test('ground jump is grounded-only and clears each generated obstacle at supported speeds',()=>{
 for(const speed of [180,300,440,520])for(const kind of ['spike','gap','laser','barrier']){
 const w=new RunnerWorld({...base,speed,max_speed:speed,acceleration:0});w.obstacles=[{id:1,x:600,width:kind==='gap'?speed*.23:42,kind,center:250,gap:190,passed:false}];w.nextX=1e9;
 let jumped=false;for(let i=0;i<1200;i++){const d=600-(w.distance+180);if(!jumped&&d<speed*base.jump_impulse/base.gravity-w.obstacles[0].width/2){w.action();jumped=true;const v=w.vy;w.action();assert.equal(w.vy,v);}w.step(1/120);if(w.obstacles[0]?.passed)break;assert.equal(w.state,'playing',`${speed} ${kind} ${d} ${w.y}`);}assert.ok(w.obstacles[0].passed);}
});
test('flap airborne impulse, obstacle score once, death and deterministic restart',()=>{
 const w=new RunnerWorld({...base,mode:'flap',scoring:'gaps'});w.action();assert.equal(w.vy,-310);w.step(.1);w.action();assert.equal(w.vy,-310);
 w.y=250;w.vy=0;w.obstacles=[{id:1,x:100,width:30,kind:'gate',center:250,gap:190,passed:false}];w.step(1/120);assert.equal(w.score,1);w.step(1/120);assert.equal(w.score,1);
 w.y=1;w.step(1/120);assert.equal(w.state,'lost');w.action();assert.equal(w.state,'playing');assert.equal(w.score,0);assert.equal(w.distance,0);
});
test('finite finish and speed curve',()=>{const w=new RunnerWorld({...base,endless:false,finish_distance:500});w.obstacles=[];w.nextX=1e9;for(let i=0;i<1200;i++)w.step(1/120);assert.equal(w.state,'won');assert.ok(w.speed>300&&w.speed<=440);});
test('boss telegraphs alternating charge and volley and accelerates phase two',()=>{
 let m={phase:'idle',at:0,direction:-1};let r=bossStep(m,1800,12,12,100,700,40,960,700,1700);assert.equal(r.memory.phase,'windup');assert.equal(r.vx,0);m=r.memory;r=bossStep(m,2600,12,12,100,700,40,960,700,1700);assert.equal(r.fire,false);r=bossStep(r.memory,2700,12,12,100,700,40,960,700,1700);assert.equal(r.vx,-270);
 r=bossStep({phase:'windup',at:0,direction:-1,cycle:2},800,6,12,100,700,40,960,700,1700);assert.equal(r.fire,true);r=bossStep(r.memory,900,6,12,100,700,40,960,700,1700);assert.equal(r.vx,0);
});
import {biomeAt} from '../src/game/adventure/regions.ts';
test('nested biome priority and explicitly local slipperiness',()=>{const regions=[{id:'forest',x:1,y:1,width:46,height:30,slippery:false},{id:'snow',x:10,y:10,width:20,height:20,slippery:false},{id:'lake',x:15,y:15,width:5,height:5,slippery:true}];assert.equal(biomeAt(regions,5,5).id,'forest');assert.equal(biomeAt(regions,12,12).slippery,false);assert.equal(biomeAt(regions,16,16).id,'lake');assert.equal(biomeAt(regions,16,16).slippery,true);assert.equal(biomeAt(regions,0,0),undefined);});
