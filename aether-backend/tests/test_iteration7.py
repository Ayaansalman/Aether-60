import pytest
from pydantic import ValidationError
from services import platformer,adventure,runner
from services.game_factory import genre_for_prompt,parse_ir
from schemas.runner import RunnerDesign
from schemas.adventure import BiomeRegion
A='Create a single-level medieval platformer set in a castle arena. I must fight one powerful knight boss in a one-on-one duel. The boss should have multiple attack patterns and a visible health bar. I can attack using my sword or an available combat ability. Do not add ordinary enemies or collectible objectives. I win only when the boss is defeated.'
B='Create a top-down fantasy adventure in one connected world where a lush enchanted forest surrounds a frozen lake and icy ruins. I should be able to walk naturally from the green forest into the snowy region without changing levels. The frozen lake has slippery terrain. A forest villager asks me to retrieve a magical crystal from the icy ruins. Keep the game focused on exploration with no combat.'
C='Create a fast-paced endless 2D runner in a neon cyberpunk city. My character should automatically run forward while I jump over spikes, gaps, and laser obstacles. Make the course become gradually faster and more challenging. Track my distance, and let me instantly restart after crashing.'
D='Create a colorful arcade game where I control a small flying creature. The world scrolls from right to left, and pressing Space or tapping the screen makes the creature flap upward against gravity. I must fly between gaps in obstacles, earn points for each gap passed, and survive as long as possible.'
@pytest.mark.parametrize('prompt,genre',[(A,'platformer'),(B,'adventure'),(C,'runner'),(D,'runner')])
def test_routing(prompt,genre):assert genre_for_prompt(prompt)==genre

def test_boss_fidelity():
    design=platformer.fixture_design(A);platformer.enforce_explicit_requirements(design,A);ir=platformer.construct(design,A,7)
    assert len(ir.entities)==1 and ir.entities[0].boss and ir.boss.health>=4
    assert ir.player_attack=='projectile' and ir.objective['type']=='boss_defeat' and not ir.levels
    assert platformer.validate_route(ir)['overall']=='PASS'
    assert any('approximated' in n for n in design.design_notes)
    assert parse_ir(ir.model_dump())==ir
@pytest.mark.parametrize('seed',range(12))
def test_same_world_biomes(seed):
    design=adventure.fixture_design(B);ir=adventure.construct(design,B,seed)
    assert len(ir.areas)==1 and not ir.combat and not any(a.kind=='enemy' for a in ir.areas[0].actors)
    assert adventure.validate_world(ir)['overall']=='PASS'
    lake=next(r for r in ir.areas[0].regions if r.biome=='frozen_lake');assert lake.slippery
    crystal=next(a for a in ir.areas[0].actors if a.item=='crystal');region=next(r for r in ir.areas[0].regions if r.id==crystal.region)
    assert region.biome=='icy_ruins' and region.x<=crystal.x<region.x+region.width
    assert [q.kind for q in ir.quests]==['talk','collect','deliver']
    assert parse_ir(ir.model_dump())==ir
@pytest.mark.parametrize('prompt,mode',[(C,'ground'),(D,'flap')])
def test_runner_contract(prompt,mode):
    d,_=runner.plan(prompt,'fixture');ir=runner.construct(d,prompt,123)
    assert ir.mode==mode and ir.endless and ir.scoring==('gaps' if mode=='flap' else 'distance')
    assert parse_ir(ir.model_dump())==ir
    assert runner.construct(d,prompt,123)==ir

def test_schema_guards():
    with pytest.raises(ValidationError):RunnerDesign(speed=400,max_speed=200)
    with pytest.raises(ValidationError):BiomeRegion(id='bad',name='bad',biome='snow',x=44,y=1,width=10,height=10)

def test_original_genres_smoke():
    d=platformer.fixture_design('Create a peaceful forest platformer');platformer.enforce_explicit_requirements(d,d.premise)
    assert platformer.validate_route(platformer.construct(d,d.premise,7))['overall']=='PASS'
    d=adventure.fixture_design('Create a peaceful top-down forest adventure');assert adventure.validate_world(adventure.construct(d,d.premise,7))['overall']=='PASS'

def test_semantic_model_routes_without_runner_keywords(monkeypatch):
    import json
    from types import SimpleNamespace
    from services.semantic_intent import interpret
    from providers import factory
    prompt='The scenery travels past while my only control sends the creature upward.'
    class Provider:
        def complete(self,system,user):
            assert user==prompt
            return SimpleNamespace(text=json.dumps({'genre':'runner','loop':'Survive scrolling gaps','control':'flap','requirements':[{'source':'only control sends the creature upward','meaning':'Airborne impulse','capability':'flap','status':'planned','depends_on':[],'verification':'Repeat input in midair'}]}),model='test-model')
    monkeypatch.setattr(factory,'get_provider',lambda:Provider())
    intent,source=interpret(prompt,'live');assert intent.genre=='runner' and intent.control=='flap' and source['live']

def test_semantic_fidelity_rejects_wrong_control_and_missing_exclusion():
    from services.semantic_intent import fidelity
    design,_=runner.plan(C,'fixture');ir=runner.construct(design,C,7)
    requirements=[{'source':'flap upward','meaning':'Airborne control','capability':'flap','status':'planned','depends_on':[],'verification':'Airborne impulse'}]
    report=fidelity(ir,{'requirements':requirements});assert report['overall']=='FAIL'
    design=platformer.fixture_design('Create a forest platformer with collectible crystals');ir=platformer.construct(design,design.premise,7)
    requirements[0]['capability']='no_collectibles';assert fidelity(ir,{'requirements':requirements})['overall']=='FAIL'

@pytest.mark.parametrize('prompt',[C,D])
def test_runner_api_and_reverification(tmp_path,monkeypatch,prompt):
    from fastapi.testclient import TestClient
    from main import app
    from routes import platformer as route
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setattr(route,'browser_report',lambda *args:{'overall':'PASS','checks':[{'id':'runner_input','passed':True}]})
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':prompt,'mode':'fixture','seed':7}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json();assert result['job']['status']=='READY'
        assert result['artifacts']['semantic_intent.json']['genre']=='runner'
        assert client.get('/api/v2/games/'+gid+'/spec').json()['genre']=='runner'
        assert client.post('/api/v2/games/'+gid+'/verify').status_code==202
        assert client.get('/api/v2/games/'+gid).json()['job']['status']=='READY'

def test_boss_and_runner_physics_invariants():
    from schemas.platformer import BossEncounter
    with pytest.raises(ValidationError):BossEncounter(patterns=['charge','charge'])
    with pytest.raises(ValidationError):RunnerDesign(speed=180,max_speed=200,gravity=1800,jump_impulse=520,obstacles=['barrier'])
    d=platformer.fixture_design(A);platformer.enforce_explicit_requirements(d,A);ir=platformer.construct(d,A,7)
    raw=ir.model_dump();raw['entities'].append(dict(raw['entities'][0],id='extra_boss'))
    with pytest.raises(ValidationError):parse_ir(raw)

def test_primary_control_is_enforced_even_without_enumerated_requirements():
    from services.semantic_intent import fidelity
    d,_=runner.plan(C,'fixture');ir=runner.construct(d,C,7)
    assert fidelity(ir,{'genre':'runner','control':'flap','requirements':[]})['overall']=='FAIL'

def test_supported_biome_normalization_is_backed_by_actual_region_specs():
    d=adventure.fixture_design(B);d.unsupported=['slippery terrain physics modifier','seamless biome transition without loading screens','crafting']
    report=adventure.enforce_requirements(d,B+' Include crafting.')
    assert d.unsupported==['crafting'] and len(report['changes'])==2
