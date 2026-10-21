import { test } from 'node:test';
import assert from 'node:assert/strict';
import {iciclePhase, enemyDecision, indicatorAnimation, exitDecision, resolveLevel} from '../src/game/platformer/behaviors.ts';
import {Gameplay,emptyProgress,triggerReady,platformPosition,enemyStep} from '../src/game/platformer/gameplay.ts';

test('proximity icicle warns before falling and only resets after collision cooldown',()=>{
  assert.equal(iciclePhase('waiting',9000,false,'proximity',2200),'waiting');
  assert.equal(iciclePhase('waiting',0,true,'proximity',2200),'warning');
  assert.equal(iciclePhase('warning',449,true,'proximity',2200),'warning');
  assert.equal(iciclePhase('warning',450,false,'proximity',2200),'falling');
  assert.equal(iciclePhase('falling',9000,false,'proximity',2200),'falling');
  assert.equal(iciclePhase('spent',2199,true,'proximity',2200),'spent');
  assert.equal(iciclePhase('spent',2200,false,'proximity',2200),'waiting');
});
test('timer icicle triggers without a nearby player at its configured period',()=>{
  assert.equal(iciclePhase('waiting',799,true,'timer',800),'waiting');
  assert.equal(iciclePhase('waiting',800,false,'timer',800),'warning');
});
test('patrol reverses at boundaries; chase reacts to player; shooter holds position and fires in lane',()=>{
  const decide=(behavior,x,playerX,playerY=100,time=1500)=>enemyDecision(behavior,x,100,10,200,-1,playerX,playerY,time);
  assert.equal(decide('patrol',5,100).vx,65);
  assert.equal(decide('patrol',205,100).vx,-65);
  assert.equal(decide('chase',100,150).vx,125);
  assert.equal(decide('chase',100,50).vx,-125);
  assert.equal(decide('chase',200,220).vx,0);
  assert.equal(decide('shooter',100,150).vx,0);
  assert.equal(decide('shooter',100,150).fire,true);
  assert.equal(decide('shooter',100,150,100,100).fire,false);
  assert.equal(decide('shooter',100,150,300).fire,false);
  assert.equal(decide('shooter',100,600).fire,false);
});
test('structured exit animation distinguishes flashing from glowing and disabled indicators',()=>{
  assert.equal(indicatorAnimation('none'),null);
  assert.equal(indicatorAnimation(undefined),null);
  assert.ok(indicatorAnimation('flash').duration<indicatorAnimation('pulse').duration);
  assert.ok(indicatorAnimation('glow').alpha<1);
});
test('exit collection gate precedes transition; only last level completes campaign',()=>{
  assert.equal(exitDecision(0,3,2,3),'locked');
  assert.equal(exitDecision(0,3,3,3),'next');
  assert.equal(exitDecision(1,3,0,0),'next');
  assert.equal(exitDecision(2,3,4,3),'won');
  assert.equal(exitDecision(0,1,0,0),'won');
});

test('level settings preserve false and old saved levels inherit omitted or null settings',()=>{
  const campaign = {title:'Journey', theme:'ice', slippery:true, exit_style:'gate', levels:[
    {title:'Learn', slippery:false, theme:'forest', objective:{required:0}},
    {title:'Climb', theme:null, slippery:null},
    {title:'Combine', slippery:true, theme:'ice'},
  ]};
  assert.equal(resolveLevel(campaign,0).slippery,false);
  assert.equal(resolveLevel(campaign,0).theme,'forest');
  assert.equal(resolveLevel(campaign,1).theme,'ice');
  assert.equal(resolveLevel(campaign,1).slippery,true);
  assert.equal(resolveLevel(campaign,2).slippery,true);
  assert.equal(campaign.title,'Journey');
  assert.equal(resolveLevel(campaign,0).exit_style,'gate');
});

test('registered trigger conditions distinguish interaction, pressure, proximity and projectile events',()=>{
  const sensor={near:true,contact:false,grounded:false,interact:false,projectile:false};
  assert.equal(triggerReady('interact',sensor),false);
  assert.equal(triggerReady('interact',{...sensor,interact:true}),true);
  assert.equal(triggerReady('proximity',sensor),true);
  assert.equal(triggerReady('touch',sensor),false);
  assert.equal(triggerReady('pressure',{...sensor,contact:true}),false);
  assert.equal(triggerReady('pressure',{...sensor,contact:true,grounded:true}),true);
  assert.equal(triggerReady('projectile',{...sensor,projectile:true}),true);
});

test('all/any links latch once, deduplicate events and preserve campaign progress without sharing mutable state',()=>{
  const game=new Gameplay([{sources:['a','b'],target:'door',condition:'all',action:'open_door'}]);
  assert.deepEqual(game.emit('activate','a'),[]);
  assert.deepEqual(game.emit('activate','b'),['door']);
  assert.deepEqual(game.emit('activate','b'),[]);
  const next=new Gameplay([],game.progress);
  next.emit('defeat','guard');
  assert.deepEqual(game.progress.defeat,[]);
  assert.deepEqual(next.progress.unlock,['door']);
  assert.deepEqual(emptyProgress().unlock,[]);
  const either=new Gameplay([{sources:['a','b'],target:'door',condition:'any',action:'open_door'}]);
  assert.deepEqual(either.emit('activate','b'),['door']);
});

test('objective conjunction tracks specific defeats, collections, switches, survival and deadline failure',()=>{
  const game=new Gameplay([]);
  const goals=[{id:'guards',kind:'defeat',targets:['g1','g2'],count:0,seconds:30},
    {id:'wait',kind:'survive',targets:[],count:0,seconds:2},
    {id:'deadline',kind:'time_limit',targets:[],count:0,seconds:5}];
  game.emit('defeat','unrelated');game.emit('defeat','g1');game.emit('defeat','g1');
  assert.equal(game.conditions(goals,1000)[0].amount,1);
  assert.equal(game.conditions(goals,1000).every(g=>g.complete),false);
  game.emit('defeat','g2');
  assert.equal(game.conditions(goals,2000).every(g=>g.complete),true);
  assert.equal(game.conditions(goals,5001)[2].failed,true);
  assert.equal(new Gameplay([]).conditions(goals,0)[0].amount,0);
});

test('platform motion remains bounded on the configured axis over repeated cycles',()=>{
  for(const axis of ['horizontal','vertical']) for(const pattern of ['sine','ping_pong']) {
    const config={axis,pattern,distance:72,period_ms:2400};
    for(let time=0;time<20000;time+=71){
      const point=platformPosition(100,200,config,time);
      assert.ok(Math.abs(point.x-100)<=72 && Math.abs(point.y-200)<=72);
      assert.equal(axis==='vertical'?point.x:point.y,axis==='vertical'?100:200);
    }
  }
});

test('ranged windup fires once, cooldown gates attacks, turret anchors, and ambusher commits a bounded lunge',()=>{
  const sensor={x:100,y:100,low:0,high:300,playerX:250,playerY:100};
  const config={health:2,cooldown_ms:1000,telegraph_ms:300,radius:300};
  for(const behavior of ['shooter','turret','ambusher']) {
    let step=enemyStep(behavior,{phase:'idle',at:0,direction:-1},sensor,0,config);
    assert.equal(step.memory.phase,'windup');assert.equal(step.fire,false);assert.equal(step.vx,0);
    step=enemyStep(behavior,step.memory,sensor,299,config);assert.equal(step.fire,false);
    step=enemyStep(behavior,step.memory,sensor,300,config);
    assert.equal(step.fire,behavior!=='ambusher');
    step=enemyStep(behavior,step.memory,sensor,400,config);assert.equal(step.fire,false);
    assert.equal(step.vx,behavior==='ambusher'?280:0);
    step=enemyStep(behavior,step.memory,sensor,700,config);assert.equal(step.memory.phase,'recover');
    step=enemyStep(behavior,step.memory,sensor,900,config);assert.equal(step.memory.phase,'recover');
  }
  const hurt=enemyStep('chase',{phase:'hurt',at:0,direction:-1},sensor,200,config);
  assert.equal(hurt.vx,0);
});

test('shooters reposition before firing while turrets hold their position',()=>{
  const sensor={x:180,y:100,low:0,high:400,playerX:250,playerY:100};
  const config={health:1,cooldown_ms:1000,telegraph_ms:300,radius:300};
  let shooter=enemyStep('shooter',{phase:'idle',at:0,direction:-1},sensor,0,config);
  assert.equal(shooter.memory.phase,'reposition');
  shooter=enemyStep('shooter',shooter.memory,sensor,100,config);
  assert.equal(shooter.vx,-110);assert.equal(shooter.fire,false);
  shooter=enemyStep('shooter',shooter.memory,sensor,350,config);
  assert.equal(shooter.memory.phase,'windup');assert.equal(shooter.vx,0);
  const turret=enemyStep('turret',{phase:'idle',at:0,direction:-1},sensor,0,config);
  assert.equal(turret.memory.phase,'windup');assert.equal(turret.vx,0);
});
