import pytest
from pathlib import Path
from pydantic import ValidationError
from schemas.survival import SurvivalDesign,SurvivalStream,SurvivalObjective
from services.survival import plan,construct
from services.game_factory import genre_for_prompt,parse_ir
from services.semantic_intent import fidelity
PROMPT=(Path(__file__).resolve().parents[2]/'docs/evidence/survival-fix/prompt.txt').read_text(encoding='utf-8')

def test_user_loop_routes_to_existing_arena_family():
    assert genre_for_prompt(PROMPT)=='arena_survival'
    d,_=plan(PROMPT,'fixture');ir=construct(d,PROMPT,7)
    assert ir.player.max_health==3 and ir.player.attack_mode=='avoid_only'
    assert ir.survival_stream.shooter_shots==5 and ir.survival_stream.shot_interval_ms==1000
    assert ir.objective.type=='survive_endless' and ir.objective.target==0
    assert ir.collectibles==[] and parse_ir(ir.model_dump())==ir
    assert construct(d,PROMPT,7)==ir

@pytest.mark.parametrize('values',[{'shooter_shots':0},{'max_active':1000},{'shot_interval_ms':0},{'expire_after_burst':False}])
def test_invalid_stream_rejected(values):
    with pytest.raises(ValidationError):SurvivalStream(**values)

def test_endless_cannot_silently_turn_into_a_timer_or_quest():
    with pytest.raises(ValidationError):SurvivalObjective(type='survive_endless',target=60)
    with pytest.raises(ValidationError):SurvivalDesign(quests=[{'kind':'collect'}])
    with pytest.raises(ValidationError):SurvivalDesign(collectibles=[{'type':'coin','count':1}])

def test_count_and_interval_are_checked_against_constructed_runtime_config():
    d,_=plan(PROMPT,'fixture');ir=construct(d,PROMPT,7)
    intent={'genre':'arena_survival','control':'top_down','requirements':[{'source':'5 bullets after 1 second each','capability':'emitter_lifecycle','count':5,'interval_ms':1000}]}
    assert fidelity(ir,intent)['overall']=='WARN' # Constructed; no runtime evidence injected.
    ir.survival_stream.shooter_shots=4
    assert fidelity(ir,intent)['overall']=='FAIL'
    ir.survival_stream.shooter_shots=5;ir.survival_stream.shot_interval_ms=2500
    assert fidelity(ir,intent)['overall']=='FAIL'

def test_live_semantic_and_design_provider_contract(monkeypatch):
    from types import SimpleNamespace
    import json
    from providers import factory
    from services.semantic_intent import interpret
    class Provider:
        def complete(self,system,user):
            assert user==PROMPT
            if 'Interpret the requested game' in system:
                assert 'Top-down is a perspective' in system
                return SimpleNamespace(text=json.dumps({'genre':'arena_survival','control':'top_down','loop':'Dodge and survive','requirements':[]}),model='test-provider')
            assert 'shooter_shots' in system and 'no player attacks, quests' in system
            return SimpleNamespace(text=SurvivalDesign().model_dump_json(),model='test-provider')
    monkeypatch.setattr(factory,'get_provider',lambda:Provider())
    intent,_=interpret(PROMPT,'live');d,p=plan(PROMPT,'live',intent.model_dump())
    assert d.genre=='arena_survival' and p['live']

def test_actual_v2_api_routes_and_reverifies_survival(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from routes import platformer
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setattr(platformer,'browser_report',lambda *args:{'overall':'PASS','checks':[{'id':'endless_survival','passed':True}]})
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':PROMPT,'mode':'fixture','seed':7}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json()
        assert result['job']['status']=='READY',result
        assert result['artifacts']['build_manifest.json']['runtime']=='ArenaScene'
        assert client.get('/api/v2/games/'+gid+'/spec').json()['genre']=='arena_survival'
        client.post('/api/v2/games/'+gid+'/verify')
        assert client.get('/api/v2/games/'+gid).json()['job']['status']=='READY'

def test_schema_failure_is_reported_without_raw_pydantic_input(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from schemas.adventure import AdventureDesign
    def invalid(*args,**kwargs):
        return AdventureDesign(title='Bad draft',premise='Bad draft',areas=[{'name':'Forest','environment':'forest'}],actors=[{'id':'item','kind':'item','name':'Item'}],quests=[{'kind':'collect','target':'item','text':'Collect'}])
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setattr('services.adventure.plan',invalid)
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':'Create a top-down adventure','mode':'fixture'}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json();detail=result['events'][-1]['detail']
        assert result['job']['status']=='FAILED'
        assert 'could not be validated' in detail and 'input_value' not in detail and 'pydantic.dev' not in detail
        assert result['artifacts']['design_validation_errors.json']['errors']

def test_unsolicited_warnings_do_not_turn_valid_evasion_into_failure():
    from services.survival import enforce_requirements
    d=SurvivalDesign(unsupported=['Player attacks, weapons, and offensive abilities','Quests, NPCs, doors, inventory, and collectibles','Multiplayer'])
    guard=enforce_requirements(d,PROMPT)
    assert len(guard['changes'])==2 and d.unsupported==['Multiplayer']
    d=SurvivalDesign(unsupported=['Player attacks, weapons, and offensive abilities'])
    enforce_requirements(d,'The player can shoot with my gun.')
    assert d.unsupported
