"""Iteration 3 contracts and deterministic progression; no provider calls."""
import pytest
from pydantic import ValidationError
from schemas.platformer import GameDesign, LevelDesign, PlatformerIR
from services.platformer import fixture_design, enforce_explicit_requirements, construct, validate_route

ICE = ('Create a three-level ice platformer. The first level introduces slippery terrain, '
       'the second introduces falling icicles, and the final level combines both mechanics with difficult platforming.')


def build(prompt=ICE, seed=41):
    design = fixture_design(prompt)
    enforce_explicit_requirements(design, prompt)
    return design, construct(design, prompt, seed)


@pytest.mark.parametrize('count', ['two-level', '2 levels', 'two connected stages', 'three-level', '3 stages'])
def test_count_phrases_and_determinism(count):
    prompt = f'Create a {count} forest platformer with crystals and moving platforms'
    design, ir = build(prompt)
    assert len(ir.levels) == (2 if count.startswith(('two', '2')) else 3)
    assert construct(design, prompt, 41) == ir
    assert validate_route(ir)['overall'] == 'PASS'


def test_ice_introduction_development_combination():
    design, ir = build()
    assert len(design.levels) == len(ir.levels) == 3
    assert [level.slippery for level in ir.levels] == [True, False, True]
    assert [any(e.kind == 'icicle' for e in level.entities) for level in ir.levels] == [False, True, True]
    assert [level.topology for level in ir.levels] == ['journey', 'ascent', 'terraces']
    assert [level.difficulty for level in ir.levels] == ['relaxed', 'balanced', 'challenging']
    assert len({tuple((p.x,p.y,p.width,p.kind) for p in level.platforms) for level in ir.levels}) == 3
    assert PlatformerIR.model_validate_json(ir.model_dump_json()) == ir
    assert validate_route(ir)['overall'] == 'PASS'


def test_model_levels_override_global_mechanics_and_objectives():
    design = fixture_design('forest with falling icicles slippery moving platforms')
    design.level_count = 2
    design.levels = [
        LevelDesign(title='Forest introduction', theme='forest', slippery=False, falling_icicles=False,
                    moving_platforms=False, objective='reach_exit', sections=design.sections),
        LevelDesign(title='Ice ascent', theme='ice', topology='ascent', slippery=True,
                    falling_icicles=True, moving_platforms=True, objective='collect_and_exit', sections=design.sections),
    ]
    design = GameDesign.model_validate(design.model_dump())
    ir = construct(design, 'two themed levels')
    assert [level.theme for level in ir.levels] == ['forest', 'ice']
    assert [level.slippery for level in ir.levels] == [False, True]
    assert not any(e.kind == 'icicle' for e in ir.levels[0].entities)
    assert not any(p.moving for p in ir.levels[0].platforms)
    assert ir.levels[0].objective['required'] == 0 < ir.levels[1].objective['required']
    assert validate_route(ir)['overall'] == 'PASS'


def test_invalid_level_count_is_rejected():
    design, _ = build()
    raw = design.model_dump()
    raw['levels'].pop()
    with pytest.raises(ValidationError, match='exactly level_count'):
        GameDesign.model_validate(raw)


def test_scoped_exclusion_preserves_later_encounters():
    design, _ = build('Create two forest levels')
    design.levels[0].sections = [s.model_copy(update={'enemies':False}) for s in design.sections]
    design.levels[1].sections = [s.model_copy(update={'enemies':True}) for s in design.sections]
    enforce_explicit_requirements(design, 'Create two levels. The first level has no enemies. The final level has patrolling enemies.')
    assert not any(s.enemies for s in design.levels[0].sections)
    assert all(s.enemies for s in design.levels[1].sections)


def test_fixture_respects_reversed_mechanic_introduction():
    _, ir = build('Create two-level ice platforming. The first level introduces falling icicles. The second level introduces slippery terrain.')
    assert [level.slippery for level in ir.levels] == [False, True]
    assert [any(e.kind == 'icicle' for e in level.entities) for level in ir.levels] == [True, False]


def test_optional_collectibles_keep_support_and_are_never_required():
    _, ir = build('Create two levels of forest exploration with collectible crystals and moving platforms')
    for level in ir.levels:
        assert any(p.route == 'optional' for p in level.platforms)
        main = sum(e.kind == 'crystal' and level.platforms[e.platform].route == 'main' for e in level.entities)
        assert 0 < level.objective['required'] <= main
        for entity in level.entities:
            support = level.platforms[entity.platform]
            assert support.x*36 <= entity.x <= (support.x+support.width)*36


def test_later_objective_and_exit_failures_are_not_hidden():
    _, ir = build()
    ir.levels[-1].entities = [e for e in ir.levels[-1].entities if e.kind != 'exit']
    assert validate_route(ir)['overall'] == 'FAIL'


@pytest.mark.parametrize('seed', range(12))
def test_ice_campaign_routes_across_seeds(seed):
    _, ir = build(seed=seed)
    assert validate_route(ir)['overall'] == 'PASS'
