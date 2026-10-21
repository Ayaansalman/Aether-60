"""Acceptance cases and geometry invariants across seeds, without provider calls."""
from collections import deque
import pytest
from services.adventure import fixture_design, construct, validate_world
from schemas.adventure import Actor, Goal

HERBALIST = 'Create a cozy top-down fantasy adventure in a woodland village. A village healer needs three magical herbs from the nearby forest. Let me explore the village, talk to the healer, collect the herbs, and return to complete the quest. Include charming buildings, paths, trees, friendly villagers, and colorful environments. No combat.'
CRYPT = 'Create a dark top-down dungeon adventure where I explore an ancient crypt, fight skeleton guards, discover a hidden key, unlock a sealed chamber, and claim a magical relic. Include multiple connected rooms, dungeon decorations, treasure, and a clear final objective.'


def flood(area, blocked=()):
    seen={(area.spawn['x'],area.spawn['y'])};todo=deque(seen)
    while todo:
        x,y=todo.popleft()
        for p in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            nx,ny=p
            if 0<=nx<area.width and 0<=ny<area.height and p not in seen and p not in blocked and area.tiles[ny][nx] not in (1,4) and area.tiles[ny][nx]<10:
                seen.add(p);todo.append(p)
    return seen


@pytest.mark.parametrize('prompt',[HERBALIST,CRYPT])
def test_acceptance_geometry_across_seeds(prompt):
    design=fixture_design(prompt)
    for seed in range(40):
        ir=construct(design,prompt,seed)
        assert validate_world(ir)['overall']=='PASS', (seed,validate_world(ir))
        for area in ir.areas:
            destinations=[(p['x'],p['y']) for a in area.actors for p in a.pickups]
            assert len(destinations)==len(set(destinations))
            assert all(area.tiles[p['y']][p['x']]==1 for p in area.trees)
            if area.environment=='village':
                assert len(area.buildings)>=3 and len(area.trees)>15
                assert len(area.zones)>=3
                # The settlement remains predominantly grass, not a vast road.
                assert sum(v==2 for row in area.tiles for v in row)/(area.width*area.height)<.30
            for a in area.actors:
                if a.kind=='door':
                    reachable=flood(area,[(a.x,a.y)])
                    assert (area.exit['x'],area.exit['y']) not in reachable
                    assert all((p['x'],p['y']) in reachable for item in area.actors if item.kind=='item' for p in item.pickups)


def test_contrasting_prompt_relationships():
    village=fixture_design(HERBALIST);crypt=fixture_design(CRYPT)
    assert not village.combat and all(a.kind!='enemy' for a in village.actors)
    assert [q.kind for q in village.quests]==['talk','collect','deliver']
    assert village.quests[-1].target==village.quests[0].target
    assert 'eastern woodland' in village.actors[0].dialogue.active[0]
    assert crypt.combat and any('Skeleton' in a.name for a in crypt.actors)
    assert any(a.item=='key' for a in crypt.actors)
    relic=next(a for a in crypt.actors if a.name=='Magical Relic')
    assert crypt.quests[-1].target==relic.id
    assert crypt.quests[-2].kind=='unlock'


def test_unreachable_nonobjective_key_cannot_be_conjured_by_validation():
    design=fixture_design(CRYPT)
    # Remove explicit key collection and move it to the area beyond the exit gate.
    key=next(a for a in design.actors if a.item=='key')
    design.quests=[q for q in design.quests if q.target!=key.id]
    key.area=1
    ir=construct(design,CRYPT,42)
    assert validate_world(ir)['overall']=='FAIL'


def test_builder_accepts_design_actor_counts_not_only_acceptance_templates():
    design=fixture_design(HERBALIST)
    for i in range(4):
        design.actors.append(Actor(id=f'villager_{i}',kind='npc',name=f'Resident {i}'))
    design.actors.append(Actor(id='shrine',kind='landmark',name='Woodland Shrine'))
    design.quests.append(Goal(kind='explore',target='shrine',text='Visit the woodland shrine'))
    for seed in [3,17,800]:
        ir=construct(design,HERBALIST,seed)
        assert validate_world(ir)['overall']=='PASS'
        assert len(ir.areas[0].actors)==len(design.actors)


def test_live_outdoor_return_loop_normalization_preserves_raw_and_quest_order():
    from services.adventure import plan
    from providers.base import CompletionResult
    from providers.factory import set_custom_provider
    raw=fixture_design(HERBALIST).model_dump()
    raw['areas'].append(dict(name='Moonlit Woods',environment='forest'))
    next(a for a in raw['actors'] if a['kind']=='item')['area']=1
    class Provider:
        def complete(self,system,user):
            import json
            return CompletionResult(text=json.dumps(raw),model='test-provider',latency_ms=1)
    recorded=[];set_custom_provider(Provider())
    try:
        design,source=plan(HERBALIST,'live',recorded.append)
    finally:set_custom_provider(None)
    assert recorded[0]['actors'][2]['area']==1
    assert raw['actors'][2]['area']==1
    assert len(design.areas)==1 and all(a.area==0 for a in design.actors)
    assert [q.model_dump() for q in design.quests]==raw['quests']
    assert source['normalizations'] and validate_world(construct(design,HERBALIST,42))['overall']=='PASS'


def test_village_landmark_stays_in_the_settlement():
    design=fixture_design(HERBALIST)
    design.actors.insert(0,Actor(id='square',kind='landmark',name='Village Square'))
    design.quests.insert(0,Goal(kind='explore',target='square',text='Visit the village square'))
    area=construct(design,HERBALIST,42).areas[0]
    assert next(a for a in area.actors if a.id=='square').x<26
    assert next(a for a in area.actors if a.id=='herbs').x>26
