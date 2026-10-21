import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {AdventureState} from '../src/game/adventure/state.ts';
const fixture=name=>JSON.parse(fs.readFileSync(new URL(`../public/fixtures/${name}.json`,import.meta.url)));

test('early pickups persist, delivery consumes quantities once and dialogue reflects completion',()=>{
  const spec=fixture('village'),s=new AdventureState(spec);
  const herbs=spec.areas[0].actors.find(a=>a.kind==='item'),npc=spec.areas[0].actors.find(a=>a.id==='guide');
  assert.deepEqual(s.states,['ACTIVE','NOT_STARTED','NOT_STARTED']);
  for(let i=0;i<3;i++)s.pickup(herbs,`herbs:${i}`);
  s.pickup(herbs,'herbs:0');assert.equal(s.inventory.herb,3);
  s.interact(npc);assert.equal(s.current,-1);assert.equal(s.inventory.herb,0);
  assert.deepEqual(s.interact(npc),npc.dialogue.completed);
  assert.equal(s.inventory.herb,0);assert.equal(s.leave(),true);assert.equal(s.won,true);
});

test('delivery requires full inventory and a second talk; restart creates fresh state',()=>{
  const spec=fixture('village'),s=new AdventureState(spec),npc=spec.areas[0].actors.find(a=>a.id==='guide'),herbs=spec.areas[0].actors.find(a=>a.id==='herbs');
  s.interact(npc);assert.equal(s.current,1);assert.equal(s.leave(),false);
  s.pickup(herbs,'herbs:0');s.interact(npc);assert.equal(s.inventory.herb,1);
  s.pickup(herbs,'herbs:1');s.pickup(herbs,'herbs:2');assert.equal(s.current,2);
  s.interact(npc);assert.equal(s.inventory.herb,0);assert.equal(s.current,-1);
  const fresh=new AdventureState(spec);assert.equal(fresh.current,0);assert.deepEqual(fresh.inventory,{});
});

test('dungeon gates require both a real key and switch, preserve state through area transition',()=>{
  const spec=fixture('dungeon'),s=new AdventureState(spec),actors=spec.areas[0].actors;
  const door=actors.find(a=>a.kind==='door'),key=actors.find(a=>a.kind==='item'),sw=actors.find(a=>a.kind==='switch');
  s.interact(door);assert.equal(s.unlocked.size,0);
  s.pickup(key,'relic:0');s.interact(door);assert.equal(s.unlocked.size,0);
  s.interact(sw);s.interact(door);assert.equal(s.unlocked.size,1);assert.equal(s.leave(),false);
  for(const enemy of actors.filter(a=>a.kind==='enemy'))s.defeat(enemy.id);
  assert.equal(s.leave(),true);assert.equal(s.area,1);assert.equal(s.inventory.key,1);
  s.interact(spec.areas[1].actors[0]);assert.equal(s.leave(),true);assert.equal(s.won,true);
});

test('exploration is event-driven and unvisited landmarks do not complete',()=>{
  const spec=fixture('village');spec.quests=[{kind:'explore',target:'landmark',count:1,text:'Find the grove',item:''}];
  const s=new AdventureState(spec);assert.equal(s.current,0);s.explore('another');assert.equal(s.current,0);s.explore('landmark');assert.equal(s.current,-1);
});

test('multi-item delivery consumes the whole requested set atomically',()=>{
  const spec=fixture('village'),npc=spec.areas[0].actors.find(a=>a.id==='guide');
  spec.quests=[{kind:'deliver',target:npc.id,text:'Return all herbs',count:1,item:'herb',delivery_items:{sunpetal:1,moonmint:2}}];
  const s=new AdventureState(spec);s.inventory={sunpetal:1,moonmint:1};s.interact(npc);
  assert.equal(s.current,0);assert.equal(s.inventory.sunpetal,1);assert.equal(s.inventory.moonmint,1);
  s.inventory.moonmint++;s.interact(npc);assert.equal(s.current,-1);assert.deepEqual(s.inventory,{sunpetal:0,moonmint:0});
});
