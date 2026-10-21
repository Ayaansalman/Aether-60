"""Focused composition, safety and campaign tests. No live provider requests."""
import pytest
from pydantic import ValidationError
from schemas.platformer import PlatformerIR, GoalDesign, LevelDesign, InteractionDesign
from services.platformer import fixture_design, enforce_explicit_requirements, construct, validate_route
from services.capabilities import requirement_evidence

PROMPTS = {
    'combat': 'Create a forest platformer where I must defeat creatures guarding an ancient temple.',
    'factory': 'Create a factory platformer where I must activate switches to open security doors while avoiding machinery.',
    'ice': 'Create a difficult ice platformer with slippery terrain, falling hazards, and ranged enemies.',
}


def build(prompt):
    design=fixture_design(prompt)
    enforce_explicit_requirements(design,prompt)
    return design,construct(design,prompt,1234)


@pytest.mark.parametrize('case', PROMPTS)
def test_prompt_components_are_distinct_and_serializable(case):
    design,ir=build(PROMPTS[case])
    assert PlatformerIR.model_validate_json(ir.model_dump_json())==ir
    assert validate_route(ir)['overall']=='PASS'
    assert requirement_evidence(ir,PROMPTS[case])['overall']!='FAIL'
    assert construct(design,PROMPTS[case],1234)==ir
    if case=='combat':
        assert any(goal.kind=='defeat' for goal in ir.goals)
        assert any(e.kind=='enemy' for e in ir.entities)
        assert not ir.links and not ir.slippery and not any(e.kind=='icicle' for e in ir.entities)
    elif case=='factory':
        assert ir.links and {goal.kind for goal in ir.goals}=={'activate','unlock'}
        assert {'switch','door','timed_hazard'} <= {e.kind for e in ir.entities}
        assert not any(e.kind=='enemy' for e in ir.entities)
    else:
        assert ir.slippery and {'icicle','enemy'} <= {e.kind for e in ir.entities}
        assert {e.behavior for e in ir.entities if e.kind=='enemy'}=={'shooter'}
        assert not ir.links and not ir.goals


def test_switch_sources_precede_doors_and_exit_requires_unlock():
    _,ir=build(PROMPTS['factory'])
    entities={e.id:e for e in ir.entities}
    for link in ir.links:
        assert all(entities[source].platform<entities[link.target].platform for source in link.sources)
    assert any(goal.kind=='unlock' and {link.target for link in ir.links}<=set(goal.targets) for goal in ir.goals)


@pytest.mark.parametrize('prompt,activation',[
    ('A forest with pressure plates opening doors','pressure'),
    ('A factory with switches that I shoot with projectiles to open doors','projectile'),
    ('A forest with proximity switches opening doors','proximity'),
])
def test_registered_trigger_modes(prompt,activation):
    _,ir=build(prompt)
    assert any(e.kind in ('switch','pressure_plate') and e.activation==activation for e in ir.entities)
    if activation=='projectile': assert ir.player_attack=='projectile'


def test_explicit_per_level_composition_and_campaign_targets():
    design=fixture_design('forest with switches and defeat creatures')
    design.level_count=2
    design.levels=[
        LevelDesign(title='Introduction',sections=design.sections,interactions=[],objectives=[]),
        LevelDesign(title='Temple locks',sections=design.sections,interactions=[InteractionDesign(section=0,door_section=2)],objectives=[GoalDesign(kind='defeat')]),
    ]
    design.campaign_objectives=[GoalDesign(kind='defeat')]
    ir=construct(design,'two linked levels',42)
    assert not ir.levels[0].links and not ir.levels[0].goals
    assert ir.levels[1].links and any(goal.kind=='defeat' for goal in ir.levels[1].goals)
    target_ids=ir.campaign_goals[0].targets
    assert any(target.startswith('L1_') for target in target_ids) and any(target.startswith('L2_') for target in target_ids)
    assert PlatformerIR.model_validate_json(ir.model_dump_json())==ir
    assert validate_route(ir)['overall']=='PASS'


def test_invalid_ids_target_kinds_and_generated_code_are_rejected():
    _,ir=build(PROMPTS['factory'])
    raw=ir.model_dump();raw['links'][0]['target']='missing'
    with pytest.raises(ValidationError): PlatformerIR.model_validate(raw)
    raw=ir.model_dump();raw['links'][0]['action']='eval'
    with pytest.raises(ValidationError): PlatformerIR.model_validate(raw)
    raw=ir.model_dump();raw['goals'][0]['targets']=[next(e.id for e in ir.entities if e.kind=='crystal')]
    with pytest.raises(ValidationError): PlatformerIR.model_validate(raw)
    raw=ir.model_dump();raw['entities'][0]['script']='alert(1)'
    with pytest.raises(ValidationError): PlatformerIR.model_validate(raw)


def test_impossible_objective_and_switch_order_do_not_silently_substitute():
    design=fixture_design('peaceful forest no enemies')
    design.objectives=[GoalDesign(kind='defeat',count=5)]
    with pytest.raises(ValueError,match='Unachievable'): construct(design,'peaceful')
    design.objectives=[];design.interactions=[InteractionDesign(section=3,door_section=1)]
    with pytest.raises(ValueError,match='precede'): construct(design,'switch')


def test_timers_and_vertical_platform_configuration():
    _,ir=build('Create a forest with vertical ping-pong moving platforms. Survive for 10 seconds and reach the exit within 60 seconds.')
    assert {goal.kind for goal in ir.goals}=={'survive','time_limit'}
    assert all(p.motion.axis=='vertical' and p.motion.pattern=='ping_pong' for p in ir.platforms if p.moving)
    assert validate_route(ir)['overall']=='PASS'
    ir.goals[1].seconds=2
    assert validate_route(ir)['overall']=='FAIL'


@pytest.mark.parametrize('behavior',['turret','ambusher'])
def test_enemy_selection_and_safe_parameters(behavior):
    _,ir=build(f'A forest guarded by {behavior} enemies')
    assert any(e.behavior==behavior for e in ir.entities if e.kind=='enemy')
    raw=ir.model_dump()
    next(e for e in raw['entities'] if e['kind']=='enemy')['ai']['cooldown_ms']=0
    with pytest.raises(ValidationError): PlatformerIR.model_validate(raw)


def test_requested_enemy_families_are_composed_without_overwriting_each_other():
    _,ir=build('A forest guarded by ranged enemies, turrets and ambushers')
    assert {e.behavior for e in ir.entities if e.kind=='enemy'}=={'shooter','turret','ambusher'}


def test_stomp_objectives_keep_an_unobstructed_attack_column():
    _,ir=build('Defeat creatures in a forest with moving platforms')
    assert any(p.moving for p in ir.platforms)
    for entity in (e for e in ir.entities if e.kind=='enemy'):
        assert not any(p.route=='optional' and p.x*36<entity.x<(p.x+p.width)*36 and 0<ir.platforms[entity.platform].y-p.y<=3 for p in ir.platforms)


def test_target_specific_enemy_cohorts_and_component_exclusions():
    _,ir=build('Defeat only turrets while avoiding chasing enemies in a forest')
    goal=next(goal for goal in ir.goals if goal.kind=='defeat')
    assert goal.enemy_behavior=='turret'
    assert all(next(e for e in ir.entities if e.id==target).behavior=='turret' for target in goal.targets)
    assert any(e.kind=='enemy' and e.behavior=='chase' for e in ir.entities)
    design,ir=build('A peaceful forest without switches and no turrets')
    assert not ir.links and not design.interactions


def test_one_based_model_indices_are_corrected_with_inspectable_evidence():
    design=fixture_design('A factory with switches')
    design.interactions=[InteractionDesign(section=2,door_section=len(design.sections))]
    report=enforce_explicit_requirements(design,'A factory with switches')
    assert design.interactions[0].door_section==len(design.sections)-1
    assert any('one-based' in change.get('reason','') for change in report['changes'])
    assert validate_route(construct(design,'factory switches'))['overall']=='PASS'


def test_specific_projectile_interaction_evidence_verifies_generic_switches_without_hiding_failures():
    _,ir=build('Projectile switches open doors in a factory')
    report=requirement_evidence(ir,'projectile switches',qa={'checks':[{'id':'projectile_switch','passed':True}]})
    assert all(r['verified'] for r in report['requirements'] if r['id'] in ('switches','projectile_switches'))
    failed=requirement_evidence(ir,'projectile switches',qa={'checks':[{'id':'switch_door','passed':False},{'id':'projectile_switch','passed':True}]})
    assert next(r for r in failed['requirements'] if r['id']=='switches')['status']=='verification_failed'
