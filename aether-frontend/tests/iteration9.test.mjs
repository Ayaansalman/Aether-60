import test from 'node:test';
import assert from 'node:assert/strict';
import {BehaviorWorld,spawnPositions} from '../src/game/adventure/behaviors.ts';
import {Gameplay as PlatformGameplay} from '../src/game/platformer/gameplay.ts';
const config=(shots=5,interval=1000)=>({health:3,invulnerability_ms:1000,player_attack:false,outcome:'endless',duration_seconds:null,scoring:'survival_time',archetypes:[{id:'caster',name:'Caster',behavior:'shooter',speed:0,health:2,attack:{shots,interval_ms:interval,windup_ms:300,projectile_speed:180,after:'despawn'}}],spawns:[{id:'wave',archetypes:['caster'],interval_ms:1000,max_alive:1,safe_radius:128}]});
for(const [shots,interval] of [[5,1000],[3,650],[7,1400]])test(`real scheduler emits ${shots} shots ${interval}ms apart then removes source`,()=>{
  const world=new BehaviorWorld(config(shots,interval),7,[{x:400,y:400}]);const events=[];
  for(let ms=0;ms<1000+300+(shots-1)*interval+10;ms+=1000/120)world.advance(1000/120,{x:0,y:0},e=>events.push(e));
  const id=events.find(e=>e.type==='spawn').id, fired=events.filter(e=>e.type==='shot'&&e.id===id);
  assert.equal(fired.length,shots);
  fired.slice(1).forEach((e,i)=>assert.ok(Math.abs(e.at-fired[i].at-interval)<.001));
  assert.ok(events.some(e=>e.type==='despawn'&&e.id===id));assert.equal(world.enemies.has(id),false);
  assert.equal(events.filter(e=>e.type==='windup'&&e.id===id).length,shots);
});
test('spawn safety, bounded state, seed determinism and no spawn debt',()=>{
  const a=new BehaviorWorld(config(),7,[{x:10,y:10},{x:400,y:400}]),b=new BehaviorWorld(config(),7,[{x:10,y:10},{x:400,y:400}]);
  for(let i=0;i<10000;i++){a.advance(10,{x:0,y:0},()=>{});b.advance(10,{x:0,y:0},()=>{});assert.ok(a.enemies.size<=1);}
  assert.deepEqual(a.events,b.events);assert.ok(a.events.length<=100);
  assert.ok(a.events.filter(e=>e.type==='spawn').every(e=>e.distance>=128));
  const blocked=new BehaviorWorld(config(),7,[{x:0,y:0}]);blocked.advance(50000,{x:0,y:0},()=>{});assert.equal(blocked.enemies.size,0);
  blocked.advance(10,{x:500,y:500},()=>{});assert.equal(blocked.enemies.size,0);
});
test('spawn candidates have full body clearance and stay in reachable component',()=>{
  const area={width:14,height:10,tiles:Array.from({length:10},(_,y)=>Array.from({length:14},(_,x)=>x===0||y===0||x===13||y===9||x===7?1:0)),spawn:{x:3,y:4},actors:[]};
  const positions=spawnPositions(area);assert.ok(positions.length>0);
  assert.ok(positions.every(p=>p.x<7*32&&p.x>32&&p.y>32));
});
test('shared gate stays closed after first switch, opens exactly once after both',()=>{
  const state=new PlatformGameplay([{sources:['s1','s2'],target:'gate',condition:'all',action:'open_door'}]);
  assert.deepEqual(state.emit('activate','s1'),[]);assert.deepEqual(state.progress.unlock,[]);
  assert.deepEqual(state.emit('activate','s2'),['gate']);assert.deepEqual(state.emit('activate','s2'),[]);
});

test('mixed archetypes always choose one registered role across many seeds',()=>{
  for(let seed=0;seed<60;seed++){
    const c=config();c.archetypes.push({id:'chaser',name:'Chaser',behavior:'chase',speed:65,health:2,attack:null});c.spawns[0].archetypes.push('chaser');
    const world=new BehaviorWorld(c,seed,[{x:400,y:400},{x:800,y:800}]);
    for(let i=0;i<80;i++){world.advance(1000,{x:0,y:0},(_event,enemy)=>assert.ok(c.archetypes.includes(enemy.archetype)));for(const id of world.enemies.keys())world.remove(id);}
  }
});
