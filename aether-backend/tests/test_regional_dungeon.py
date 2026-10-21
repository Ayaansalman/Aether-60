"""Regression for the user's saved dark/garden dungeon and gated region placement."""
import json
from pathlib import Path
from collections import deque
import pytest
from schemas.adventure import AdventureDesign
from services.adventure import construct,validate_world,enforce_requirements
from services.semantic_intent import fidelity
ROOT=Path(__file__).resolve().parents[2]
PROMPT='Create a dual themed top-down dungeon adventure with one half of the dungeon in dark themed and the other half in flower greenish garden themed area where I explore ancient ruins, fight monsters, collect a key, activate a magical switch, and unlock the final chamber containing a treasure.'
def design():
    d=AdventureDesign.model_validate_json((ROOT/'docs/evidence/dual-dungeon-fix/original_final_design.json').read_text(encoding='utf-8'))
    enforce_requirements(d,PROMPT);return d

def reachable(area,blocked=()):
    todo=deque([(area.spawn['x'],area.spawn['y'])]);seen=set(todo)
    while todo:
        x,y=todo.popleft()
        for point in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            nx,ny=point
            if point not in seen and point not in blocked and 0<=nx<area.width and 0<=ny<area.height and area.tiles[ny][nx] not in (1,4) and area.tiles[ny][nx]<10:
                seen.add(point);todo.append(point)
    return seen

@pytest.mark.parametrize('swapped',[False,True])
def test_region_gates_keep_prerequisites_outside_and_treasure_inside(swapped):
    d=design()
    if swapped:
        for r in d.areas[0].regions:r.x=24 if r.x==2 else 2
    for seed in range(20):
        ir=construct(d,PROMPT,seed);area=ir.areas[0]
        assert validate_world(ir)['overall']=='PASS'
        actors={a.id:a for a in area.actors};door=actors['chamber_door'];locked=reachable(area,[(door.x,door.y)])
        for name in ['guardian_elena','ruin_slime','ruin_bat','ancient_key','magical_switch']:
            a=actors[name];assert (a.x,a.y) in locked,(swapped,seed,name)
            region=next(r for r in area.regions if r.id==a.region)
            assert region.x<=a.x<region.x+region.width and region.y<=a.y<region.y+region.height
        treasure=actors['ultimate_treasure'];assert (treasure.x,treasure.y) not in locked
        assert (treasure.x,treasure.y) in reachable(area)
        # Indoor regional decoration must retain a substantial walled dungeon.
        assert sum(v==1 for row in area.tiles for v in row)>300

def test_actual_themes_do_not_turn_dark_crypt_into_ice():
    assert [r.biome for r in design().areas[0].regions]==['garden','dark']

def test_saved_semantic_capabilities_bind_to_adventure_components():
    intent=json.loads((ROOT/'docs/evidence/dual-dungeon-fix/original_semantic_intent.json').read_text(encoding='utf-8'))
    report=fidelity(construct(design(),PROMPT,7),intent)
    assert report['overall']!='FAIL',report
    caps={r['capability'] for r in report['requirements']}
    assert {'quest_collect','quest_activate','treasure_finish'}<=caps

def test_failed_early_goal_does_not_grant_unreachable_key_or_unlock():
    ir=construct(design(),PROMPT,7);area=ir.areas[0];key=next(a for a in area.actors if a.id=='ancient_key')
    for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:area.tiles[key.y+dy][key.x+dx]=1
    report=validate_world(ir);assert report['overall']=='FAIL'
    unlock=next(c for c in report['checks'] if c.get('target')=='chamber_door')
    assert not unlock['passed'] and not unlock['prior_objectives_valid']
