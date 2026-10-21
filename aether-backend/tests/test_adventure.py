import json
import pytest
from pydantic import ValidationError
from services.adventure import fixture_design, construct, validate_world, validate_assets, enforce_requirements
from services.game_factory import genre_for_prompt, parse_ir

VILLAGE='Create a cozy top-down fantasy adventure in a small woodland village. Explore, talk to villagers, find three missing magical herbs, and return them to a healer. Make it peaceful, colorful, focused on exploration rather than combat.'
DUNGEON='Create a dark top-down dungeon adventure where I explore ancient ruins, fight monsters, collect a key, activate a magical switch, and unlock the final chamber containing a treasure.'


def test_genre_dispatch_preserves_platformer():
    assert genre_for_prompt(VILLAGE)==genre_for_prompt(DUNGEON)=='adventure'
    assert genre_for_prompt('Forest platformer with collectibles and patrol enemies')=='platformer'
    assert genre_for_prompt('A platformer adventure with jumping')=='platformer'


def test_prompt_composition_and_resources():
    calm=fixture_design(VILLAGE);dark=fixture_design(DUNGEON)
    assert not calm.combat and not any(a.kind=='enemy' for a in calm.actors)
    assert [q.kind for q in calm.quests]==['talk','collect','deliver']
    assert next(a for a in calm.actors if a.id=='herbs').quantity==3
    assert dark.combat and len(dark.areas)==2
    assert {'defeat','collect','activate','unlock'}<={q.kind for q in dark.quests}
    assert next(a for a in dark.actors if a.kind=='door').requires==['key','rune']
    assert len(dark.actors)!=len(calm.actors)


@pytest.mark.parametrize('prompt',[VILLAGE,DUNGEON,'Create a top-down forest exploration adventure','Create a cave RPG, find a lost artifact and return it to a villager'])
def test_seeded_maps_have_reachable_destinations(prompt):
    design=fixture_design(prompt)
    for seed in [0,1,42,987654321]:
        ir=construct(design,prompt,seed)
        assert validate_world(ir)['overall']=='PASS'
        assert parse_ir(json.loads(ir.model_dump_json()))==ir
    assert construct(design,prompt,42)==construct(design,prompt,42)
    assert construct(design,prompt,42).areas[0].tiles!=construct(design,prompt,43).areas[0].tiles


def test_schema_rejects_missing_targets_wrong_types_and_peaceful_enemies():
    design=fixture_design(DUNGEON).model_dump()
    for mutation in ['missing_target','wrong_kind','missing_key','no_combat','duplicate']:
        data=json.loads(json.dumps(design))
        if mutation=='missing_target':data['quests'][0]['target']='imaginary'
        if mutation=='wrong_kind':data['quests'][0]['kind']='talk'
        if mutation=='missing_key':next(a for a in data['actors'] if a['kind']=='door')['requires']=['imaginary_key']
        if mutation=='no_combat':data['combat']=False
        if mutation=='duplicate':data['actors'].append(data['actors'][0])
        with pytest.raises(ValidationError):type(fixture_design(DUNGEON)).model_validate(data)


def test_missing_connectivity_and_resource_order_fail():
    design=fixture_design(VILLAGE);ir=construct(design,VILLAGE,42)
    goal=next(a for a in ir.areas[0].actors if a.kind=='item')
    ir.areas[0].tiles[goal.y][goal.x]=1
    assert validate_world(ir)['overall']=='FAIL'
    design.quests[1],design.quests[2]=design.quests[2],design.quests[1]
    assert validate_world(construct(design,VILLAGE,42))['overall']=='FAIL'


def test_asset_checksums():
    assert validate_assets()['overall']=='PASS'


def test_delivery_guard_requires_every_distinct_collected_item():
    from schemas.adventure import Actor,Goal
    design=fixture_design(VILLAGE)
    herb=next(a for a in design.actors if a.kind=='item');herb.quantity=1
    second=herb.model_copy(update={'id':'moonmint','item':'moonmint','name':'Moonmint'})
    design.actors.append(second)
    design.quests.insert(2,Goal(kind='collect',target='moonmint',text='Collect moonmint'))
    design.quests[1].count=1
    design.quests[-1].count=1
    design.unsupported=['Equipment stats','Time of day transitions']
    guard=enforce_requirements(design,VILLAGE)
    assert guard['changes'] and design.unsupported==[]
    assert design.quests[-1].delivery_items=={'herb':1,'moonmint':1}
    assert validate_world(construct(design,VILLAGE,42))['overall']=='PASS'


def test_sealed_passage_physically_separates_final_treasure():
    ir=construct(fixture_design(DUNGEON),DUNGEON,42);area=ir.areas[0]
    door=next(a for a in area.actors if a.kind=='door')
    assert all(row[door.x]==1 for y,row in enumerate(area.tiles) if y!=door.y)
    assert area.tiles[door.y][door.x]==2
    assert all(a.x<door.x for a in area.actors if a.kind in ('item','switch','enemy'))


def test_adventure_api_uses_existing_artifacts_and_reverification(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from routes import platformer
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'))
    monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setattr(platformer,'browser_report',lambda *args:{'overall':'UNAVAILABLE','checks':[]})
    with TestClient(app) as client:
        response=client.post('/api/v2/games',json={'prompt':VILLAGE,'mode':'fixture','seed':42})
        gid=response.json()['game_id'];result=client.get(f'/api/v2/games/{gid}').json()
        assert result['job']['status']=='READY_WITH_WARNINGS'
        assert result['artifacts']['game_intent.json']['genre']=='adventure'
        assert result['artifacts']['build_manifest.json']['adapter']=='AdventureScene'
        assert result['artifacts']['validation.json']['overall']=='PASS'
        assert result['artifacts']['provider.json']['live'] is False
        assert client.get(f'/api/v2/games/{gid}/spec').json()['genre']=='adventure'
        assert client.post(f'/api/v2/games/{gid}/verify').status_code==202
        assert 'qa_retest_1.json' in client.get(f'/api/v2/games/{gid}').json()['artifacts']


def test_live_planner_uses_provider_and_validates_dialogue_targets():
    from services.adventure import plan
    from providers.base import CompletionResult
    from providers.factory import set_custom_provider
    class Provider:
        def complete(self,system,user):
            assert 'AdventureDesign' in system and user==VILLAGE
            return CompletionResult(text=fixture_design(VILLAGE).model_dump_json(),model='test-provider',latency_ms=1)
    set_custom_provider(Provider())
    try:
        design,source=plan(VILLAGE,'live')
        assert source['live'] and source['model']=='test-provider' and design.genre=='adventure'
    finally:set_custom_provider(None)
