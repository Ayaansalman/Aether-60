import { test } from 'node:test';
import assert from 'node:assert/strict';
import {iciclePhase, enemyDecision, indicatorAnimation, exitDecision} from '../src/game/platformer/behaviors.ts';

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
