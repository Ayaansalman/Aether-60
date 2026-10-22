import json
import pytest
from pydantic import ValidationError
from schemas.platformer import GameDesign, PlatformerIR
from services.platformer import fixture_design, construct, validate_route, plan, enforce_explicit_requirements, validate_assets


@pytest.mark.parametrize('prompt',['magical forest collect crystals double jump','industrial factory robots moving platforms dash','precision climb tower','peaceful easy no enemies forest'])
def test_seeded_route_and_roundtrip(prompt):
    design=fixture_design(prompt);ir=construct(design,prompt)
    assert construct(design,prompt).model_dump()==ir.model_dump()
    assert validate_route(ir)['overall']=='PASS'
    assert PlatformerIR.model_validate_json(ir.model_dump_json())==ir
    assert len({(p.x,p.y) for p in ir.platforms})==len(ir.platforms)
    for e in ir.entities:
        p=ir.platforms[e.platform]
        assert p.x*36<=e.x<=(p.x+p.width)*36


def test_meaningful_prompt_variation():
    forest=construct(fixture_design('forest collect crystals'),'forest collect crystals')
    industry=construct(fixture_design('industrial moving machines dash'),'industrial moving machines dash')
    tower=construct(fixture_design('precision tower double jump'),'precision tower double jump')
    assert forest.theme!=industry.theme
    assert any(p.moving for p in industry.platforms)
    assert 'dash' in industry.player.abilities
    assert tower.platforms[-1].y<tower.platforms[0].y-10
    assert forest.objective['required']>0


def test_peaceful_excludes_combat():
    ir=construct(fixture_design('peaceful forest no enemies'),'peaceful forest no enemies')
    assert not any(e.kind in ('enemy','spikes') for e in ir.entities)


def test_unsupported_and_unreachable():
    design=fixture_design('multiplayer rpg forest boss')
    assert set(design.unsupported)=={'Unsupported request: multiplayer','Unsupported request: rpg'}
    assert design.boss is not None  # Dedicated boss arenas have been supported since Iteration 7.
    ir=construct(design,'forest')
    ir.platforms[1].x+=30
    assert validate_route(ir)['overall']=='FAIL'


def test_live_never_silently_falls_back(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','mock')
    with pytest.raises(ValueError,match='Live mode requires'):
        plan('forest platformer','live')


def test_live_contract_with_provider(monkeypatch):
    from providers.base import CompletionResult
    from providers.factory import set_custom_provider
    class Provider:
        def complete(self,system,user):
            assert 'JSON Schema' in system
            return CompletionResult(json.dumps(fixture_design(user).model_dump()),'test-model',5)
    set_custom_provider(Provider())
    try:
        design,provenance=plan('forest platformer','live')
        assert design.genre=='platformer' and provenance['model']=='test-model'
    finally:set_custom_provider(None)


def test_schema_rejects_generated_code_and_future_genres():
    raw=fixture_design('forest').model_dump();raw['code']='alert(1)'
    with pytest.raises(ValidationError):GameDesign.model_validate(raw)
    raw.pop('code');raw['genre']='rpg'
    with pytest.raises(ValidationError):GameDesign.model_validate(raw)


def test_requirements_guard_records_corrections():
    design=fixture_design('industrial platformer');design.unsupported=['dash']
    report=enforce_explicit_requirements(design,'peaceful forest with double jump and dash, moving platforms and no checkpoints')
    assert set(design.abilities)=={'double_jump','dash'}
    assert not any(s.enemies or s.hazards for s in design.sections)
    assert design.moving_platforms and not design.checkpoints
    assert not design.unsupported and report['changes']
    enforce_explicit_requirements(design,'No dash, no double jump, and no moving platforms')
    assert not design.abilities and not design.moving_platforms


def test_seeds_change_composition():
    d=fixture_design('forest platformer')
    a,b=construct(d,'forest',1),construct(d,'forest',2)
    assert a.platforms!=b.platforms
    assert validate_route(a)['overall']==validate_route(b)['overall']=='PASS'


def test_missing_assets_are_classified(tmp_path):
    report=validate_assets({'files':{'missing.png':'nothing'}},tmp_path)
    assert report['overall']=='FAIL' and report['checks'][0]['category']=='asset'
