import pytest
from services.platformer import fixture_design, enforce_explicit_requirements, construct, validate_route
from services.capabilities import extract_requirements, requirement_evidence
from schemas.platformer import RequestedFeature

ICE='Create a frozen underground platformer with slippery terrain, falling icicles, collectible relics, and a flashing light at the exit.'
FACTORY='Create an industrial platformer with robotic enemies, moving platforms, dangerous machinery, and checkpoints across multiple stages.'
FOREST='Create a colorful forest platformer with collectible crystals, patrolling creatures, and a glowing shrine at the end.'

def build(prompt,seed=None):
    design=fixture_design(prompt)
    enforce_explicit_requirements(design,prompt)
    return construct(design,prompt,seed)

def test_requested_capabilities_survive_an_incorrect_plan():
    design=fixture_design('forest game')
    report=enforce_explicit_requirements(design,ICE)
    ir=construct(design,ICE)
    assert report['changes']
    assert ir.theme=='ice' and ir.slippery and ir.exit_indicator=='flash' and ir.collectible=='relics'
    assert {e.trigger for e in ir.entities if e.kind=='icicle'}=={'proximity','timer'}
    assert all(r['constructed'] and not r['verified'] for r in ir.requirements)

def test_fidelity_fails_when_supported_feature_disappears():
    ir=build(ICE)
    ir.entities=[e for e in ir.entities if e.kind!='icicle']
    report=requirement_evidence(ir,ICE)
    assert report['overall']=='FAIL'
    assert next(r for r in report['requirements'] if r['id']=='falling_icicles')['status']=='construction_failed'

def test_verification_requires_real_check_evidence():
    ir=build(ICE)
    report=requirement_evidence(ir,ICE,qa={'checks':[{'id':'falling_icicle_cycle','passed':False}]})
    assert report['overall']=='FAIL'
    assert next(r for r in report['requirements'] if r['id']=='falling_icicles')['status']=='verification_failed'
    assert not any(r['verified'] for r in report['requirements'])
    unsupported=requirement_evidence(ir,ICE,['Multiplayer'])['requirements'][-1]
    assert unsupported['status']=='unsupported' and not unsupported['supported']

def test_distinct_enemy_behaviors_and_campaign_geometry():
    ir=build(FACTORY)
    assert len(ir.levels)==3
    assert {e.behavior for level in ir.levels for e in level.entities if e.kind=='enemy'}=={'patrol','chase','shooter'}
    shapes=[[(p.x,p.y,p.width,p.moving) for p in level.platforms] for level in ir.levels]
    assert shapes[0]!=shapes[1]!=shapes[2]
    assert all(any(e.kind=='checkpoint' for e in level.entities) for level in ir.levels)
    ir.levels[-1].platforms[1].x+=100
    assert validate_route(ir)['overall']=='FAIL'

@pytest.mark.parametrize('prompt',[FOREST,FACTORY,ICE])
def test_seeded_generation_is_traversable_and_reproducible(prompt):
    for seed in range(20):
        ir=build(prompt,seed)
        assert validate_route(ir)['overall']=='PASS'
        assert build(prompt,seed)==ir

def test_exclusions_do_not_become_positive_requirements():
    assert not extract_requirements('no dash, without checkpoints, no moving platforms')
    ir=build('peaceful forest no enemies no hazards across multiple stages')
    assert not any(e.kind in ('enemy','spikes','icicle','timed_hazard') for level in ir.levels for e in level.entities)

def test_model_enumerated_requests_survive_wording_outside_phrase_rules():
    prompt='A forest with pursuing guardians'
    design=fixture_design(prompt)
    design.requested_features=[RequestedFeature(source='pursuing guardians', capability='chase', description='Creatures pursue the player')]
    enforce_explicit_requirements(design,prompt)
    ir=construct(design,prompt)
    requirement=next(r for r in ir.requirements if r['source']=='pursuing guardians')
    assert requirement['id']=='chase' and requirement['constructed'] and not requirement['verified']
    report=requirement_evidence(ir,prompt,qa={'checks':[{'id':'enemy_chase','passed':False},{'id':'enemy_chase','passed':True}]})
    assert report['overall']=='FAIL'  # A later stage cannot hide an earlier failure.

def test_configured_timer_survives_into_actual_hazard_components():
    ir=build('Ice cavern with falling icicles every 1.5 seconds')
    traps=[e for e in ir.entities if e.kind=='icicle']
    assert traps and all(e.trigger=='timer' and e.period_ms==1500 for e in traps)
    design=fixture_design('ice cavern')
    enforce_explicit_requirements(design,'falling icicles every 0.1 seconds')
    assert any('supported range' in s for s in design.unsupported)
