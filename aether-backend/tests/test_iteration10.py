"""Captured production failures and general dependency/fidelity regressions."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from schemas.platformer import GameDesign
from services import adventure, platformer, runner
from services.design_repair import repair_dependencies, repair_quest_order
from services.semantic_intent import interpret, normalize_intent, feasibility, fidelity

EVIDENCE=Path(__file__).resolve().parents[2]/'docs/evidence/iteration10'

def captured(case):
    return json.loads((EVIDENCE/f'source-{case}.json').read_text(encoding='utf-8'))

def replay(monkeypatch,case):
    from providers import factory
    source=captured(case)
    source['semantic_intent.json'].pop('provenance',None)
    class Provider:
        calls=0
        def complete(self,system,prompt):
            self.calls+=1
            assert prompt==source['prompt'], 'Local repairs should need no model retry'
            return SimpleNamespace(text=json.dumps(source['semantic_intent.json'] if self.calls==1 else source['game_design.json']),model='captured-gemini',latency_ms=0,fallback_events=[])
    provider=Provider();monkeypatch.setattr(factory,'get_provider',lambda:provider)
    intent,_=interpret(source['prompt'],'live')
    adapter=adventure if intent.genre=='adventure' else runner if intent.genre=='runner' else platformer
    design,provenance=adapter.plan(source['prompt'],'live',intent=intent.model_dump())
    if adapter==adventure:adventure.enforce_requirements(design,source['prompt'])
    if adapter==platformer:platformer.enforce_explicit_requirements(design,source['prompt'])
    ir=adapter.construct(design,source['prompt'],7)
    return source,intent,design,ir,provenance,provider.calls

@pytest.mark.parametrize('case',['factory','garden','boss','runner'])
def test_captured_production_handoffs_no_additional_model_calls(monkeypatch,case):
    source,intent,design,ir,provenance,calls=replay(monkeypatch,case)
    assert calls==2
    report=fidelity(ir,intent.model_dump())
    assert report['overall']!='FAIL',report
    assert all(r['id'] for r in report['requirements'])
    if case=='factory':
        assert platformer.validate_route(ir)['overall']=='PASS'
        level=ir.levels[0];assert len(level.links)==1 and len(level.links[0].sources)==2
        assert sum(e.kind=='switch' for e in level.entities)==2
        assert all(e.platform<next(e.platform for e in level.entities if e.kind=='door') for e in level.entities if e.kind=='switch')
        assert any(p.activation_sources for p in level.platforms)
        assert any(e.disabled_by for e in level.entities if e.kind=='timed_hazard')
        assert provenance['normalizations']
    if case=='garden':
        assert adventure.validate_world(ir)['overall']=='PASS'
        assert len(ir.areas)==1 and not ir.combat
        assert ir.quests[-1].delivery_items=={'frost_blossom':1,'ice_petal':1}
        assert ir.unsupported # visual limitation remains honest
        assert {'forest','icy_ruins'}=={r.biome for r in ir.areas[0].regions}
    if case=='boss':
        assert ir.boss.patterns==['charge','volley','slam'] and len(ir.entities)==1
        assert platformer.requirement_evidence(ir,source['prompt'])['overall']!='FAIL'
    if case=='runner':assert not design.unsupported and ir.speed==340

def test_invalid_dependency_cannot_cross_schema_boundary():
    raw=captured('factory')['game_design.json']
    with pytest.raises(ValidationError,match='Switch must precede'):GameDesign.model_validate(raw)
    repaired,changes=repair_dependencies(raw)
    assert len(changes)==2 and len(repaired['interactions'])==2
    assert GameDesign.model_validate(repaired)
    assert repair_dependencies(repaired)[1]==[]
    assert raw['interactions'][1]['section']==6 # original evidence remains untouched

@pytest.mark.parametrize('gate,source',[(2,5),(3,3),(5,6),(7,9)])
def test_dependency_repair_generalizes_to_different_lengths_and_indices(gate,source):
    raw=platformer.fixture_design('An industrial puzzle with switches and no collectibles').model_dump()
    raw['interactions']=[dict(section=0,door_section=gate,gate='exit'),dict(section=source,door_section=gate,gate='exit')]
    repaired,_=repair_dependencies(raw);design=GameDesign.model_validate(repaired)
    ir=platformer.construct(design,'different puzzle',9)
    assert len(ir.links[0].sources)==2
    assert all(c['passed'] for c in platformer.validate_gameplay(ir))

def test_same_area_quest_dependencies_reorder_without_deleting_targets():
    raw=adventure.fixture_design('A dungeon with a key, switch and treasure; unlock the door').model_dump()
    # Exercise a continuous dungeon, where returning to earlier rooms is supported.
    raw['areas']=raw['areas'][:1]
    for actor in raw['actors']:actor['area']=0
    # Reverse just the independent prerequisites and unlock in a valid fixture.
    unlock=next((i for i,q in enumerate(raw['quests']) if q['kind']=='unlock'),None)
    assert unlock is not None
    original=raw['quests'];raw['quests']=[original[unlock],*original[:unlock],*original[unlock+1:]]
    repaired,changes=repair_quest_order(raw)
    assert changes and sorted(q['target'] for q in repaired['quests'])==sorted(q['target'] for q in raw['quests'])
    design=adventure.AdventureDesign.model_validate(repaired)
    assert adventure.validate_world(adventure.construct(design,'different crypt',17))['overall']=='PASS'

def test_biomes_do_not_corrupt_unrelated_constraints_or_remove_exclusions(monkeypatch):
    _,intent,_,ir,_,_=replay(monkeypatch,'runner')
    assert fidelity(ir,intent.model_dump())['overall']!='FAIL'
    source=captured('garden');normalized,changes=normalize_intent(source['semantic_intent.json'],source['prompt'])
    biomes=next(r['biomes'] for r in normalized['requirements'] if r['capability']=='biome_regions')
    assert set(biomes)=={'forest','snow','icy_ruins'} and changes
    assert next(r for r in normalized['requirements'] if r['capability']=='no_combat')['mandatory']

def test_presentation_limitations_do_not_mask_missing_gameplay(monkeypatch):
    _,intent,_,ir,_,_=replay(monkeypatch,'garden')
    data=intent.model_dump();data['requirements'].append(dict(source='Animated transitions',meaning='Animation',capability='unsupported',category='presentation',mandatory=False))
    assert fidelity(ir,data)['overall']=='WARN'
    ir.quests=[q for q in ir.quests if q.kind!='deliver']
    assert fidelity(ir,data)['overall']=='FAIL'

def test_guardian_reports_actual_unsupported_shield_and_traversal_not_control_error():
    source=captured('guardian');intent,_=normalize_intent(source['semantic_intent.json'],source['prompt'])
    report=feasibility(intent)
    assert report['overall']=='FAIL'
    assert {i['capability'] for i in report['issues']}=={'boss_shield','boss_duel'}
    assert all(i['code']=='RUNTIME_UNSUPPORTED' for i in report['issues'])
    assert any(r['capability']=='falling_icicles' for r in intent['requirements'])

@pytest.mark.parametrize('layout',['open','cover','chambers','woodland'])
def test_survival_layouts_connected_safe_and_seeded(layout):
    from tests.test_iteration9 import design
    seen=set()
    for seed in range(12):
        d=design();d.areas[0].layout=layout
        ir=adventure.construct(d,'A different survival setting',seed)
        report=adventure.validate_world(ir)
        assert report['overall']=='PASS',report
        a=ir.areas[0];seen.add(json.dumps(a.tiles))
        assert all(a.tiles[a.spawn['y']+dy][a.spawn['x']+dx]!=1 for dx in (-1,0,1) for dy in (-1,0,1))
    assert len(seen)>=10

def test_laboratory_numeric_constraints_and_spatial_prompt_fidelity():
    from tests.test_iteration9 import design,behavior
    config=behavior(shots=3,interval=500,health=4);config.outcome='survive';config.duration_seconds=60
    lab=adventure.construct(design(config),'Survive in research chambers with connecting corridors',11)
    field=adventure.construct(design(config),'Survive in an open field arena',11)
    assert lab.areas[0].layout=='chambers' and field.areas[0].layout=='open'
    assert lab.areas[0].tiles!=field.areas[0].tiles
    assert lab.gameplay==config==field.gameplay
    assert adventure.validate_world(lab)['overall']=='PASS'

def test_fresh_gemini_abbreviated_quote_recovers_original_words(monkeypatch):
    from providers import factory
    saved=json.loads((EVIDENCE/'live-garden/result.json').read_text(encoding='utf-8'))
    candidate=saved['artifacts']['design_validation.json']['attempts'][-1]['candidate']
    class Provider:
        def complete(self,system,prompt):
            assert prompt==saved['job']['prompt'] # no model retry
            return SimpleNamespace(text=json.dumps(candidate),model='saved-live',latency_ms=0)
    monkeypatch.setattr(factory,'get_provider',lambda:Provider())
    value,source=interpret(saved['job']['prompt'],'live')
    assert all(r.source.lower() in saved['job']['prompt'].lower() for r in value.requirements)
    assert all(r.category=='mechanic' and r.mandatory for r in value.requirements if r.capability=='biome_regions')

def test_explicit_exclusions_cannot_be_marked_unsupported_or_optional():
    raw={'genre':'platformer','control':'platform','loop':'Explore','requirements':[{'source':'No collectible requirements.','capability':'unsupported','status':'unsupported','meaning':'No pickups','category':'exclusion','mandatory':True}]}
    normalized,_=normalize_intent(raw,'No collectible requirements.')
    assert normalized['requirements'][0]['capability']=='no_collectibles'
    assert normalized['requirements'][0]['status']=='planned'
    raw['requirements'][0].update(capability='no_combat',category='presentation',mandatory=False,source='No combat.')
    normalized,_=normalize_intent(raw,'No combat.')
    assert normalized['requirements'][0]['mandatory'] and normalized['requirements'][0]['category']=='exclusion'

def test_requirement_identity_survives_persisted_http_generation_and_reverification(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from providers import factory
    from routes import platformer as route
    source=captured('factory');source['semantic_intent.json'].pop('provenance',None)
    class Provider:
        calls=0
        def complete(self,*args):
            self.calls+=1
            assert self.calls<=2
            return SimpleNamespace(text=json.dumps(source['semantic_intent.json'] if self.calls==1 else source['game_design.json']),model='captured-test',latency_ms=0,fallback_events=[])
    provider=Provider();monkeypatch.setattr(factory,'get_provider',lambda:provider)
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    # This test verifies persistence only. Chromium interaction evidence is separate.
    monkeypatch.setattr(route,'browser_report',lambda *args:{'overall':'PASS','checks':[{'id':cap,'passed':True} for cap in ['mandatory_route_edges','enemy_patrol','switch_world_effects','shared_gate_dependency']]})
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':source['prompt'],'mode':'live','seed':7}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json();assert result['job']['status']=='READY_WITH_WARNINGS'
        before={r['id'] for r in client.get('/api/v2/games/'+gid+'/spec').json()['requirements'] if r.get('capability')}
        assert before and before=={r['id'] for r in result['artifacts']['semantic_intent.json']['requirements']}
        assert client.post('/api/v2/games/'+gid+'/verify').status_code==202
        after={r['id'] for r in client.get('/api/v2/games/'+gid+'/spec').json()['requirements'] if r.get('capability')}
        assert after==before and provider.calls==2
