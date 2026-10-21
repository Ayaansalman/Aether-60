"""Focused semantic handoff, dependency and generation regressions."""
import json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from schemas.adventure import AdventureDesign, Actor
from schemas.gameplay import Gameplay
from services import adventure, platformer
from services.semantic_intent import Intent, fidelity, feasibility

A = '''Create a top-down survival game where I must dodge enemy projectiles and survive as long as possible. I have three health points. Enemies continuously spawn at random valid positions. Each spawned enemy randomly becomes either a chaser or a shooter. Chasers pursue the player. Shooters fire five bullets, with one second between consecutive shots, then disappear. The game ends when my health reaches zero, and my score is based on how long I survive. Do not include quests, inventory, NPC conversations, collectibles, or exit gates.'''
D = 'Create an industrial platformer where I must activate two switches to open a security gate while avoiding patrolling guards and moving machinery. The exit should only become available after both switches are activated.'


def behavior(shots=5, interval=1000, health=3):
    return Gameplay(health=health,outcome='endless',scoring='survival_time',archetypes=[
        {'id':'hunter','name':'Pursuing Skull','behavior':'chase'},
        {'id':'caster','name':'Spirit Shooter','behavior':'shooter','attack':{'shots':shots,'interval_ms':interval,'after':'despawn'}}],
        spawns=[{'id':'wave','archetypes':['hunter','caster'],'interval_ms':1400}])


def design(config=None):
    return AdventureDesign(title='Spirit Barrage',premise='Dodge and survive',areas=[{'name':'Moonlit Clearing','environment':'forest'}],
        gameplay=config or behavior(),combat=True)


def semantic(prompt=A,config=None):
    config=config or behavior()
    return Intent(genre='adventure',loop='Dodge projectiles and survive',control='top_down',perspective='top_down',structure='endless',loops=['survival','avoidance'],gameplay=config,
        requirements=[{'source':prompt,'meaning':cap,'capability':cap,'count':count,'verification':'Check constructed component and runtime event'} for cap,count in
        [('top_down_movement',None),('health_damage',config.health),('enemy_spawning',None),('enemy_roles',2),('attack_sequence',config.archetypes[1].attack.shots),('survival_time',None),('no_inventory',None),('no_quests',None),('no_npcs',None),('no_collectibles',None),('no_exit',None)]])


def test_inventory_validation_is_preserved_without_invented_ids():
    d=design();assert d.actors==[] and d.quests==[]
    with pytest.raises(ValidationError,match='inventory ID'):
        AdventureDesign(**{**d.model_dump(),'actors':[{'id':'bullet','kind':'item','name':'Projectile'}]})
    with pytest.raises(ValidationError,match='Quest outcome'):
        AdventureDesign(title='Incomplete',premise='Test',areas=[{'name':'Forest','environment':'forest'}])


@pytest.mark.parametrize('config',[
    {'spawns':[{'id':'wave','archetypes':['missing']}]},
    {'outcome':'survive'}, {'duration_seconds':10},
    {'archetypes':[{'id':'caster','name':'Mage','behavior':'shooter'}]},
])
def test_dependencies(config):
    with pytest.raises(ValidationError):Gameplay(**config)


def test_construct_and_fidelity_preserve_temporal_relationships():
    intent=semantic();ir=adventure.construct(design(),A,7)
    assert ir.genre=='adventure' and ir.gameplay==intent.gameplay and not ir.quests
    assert adventure.validate_world(ir)['overall']=='PASS'
    assert fidelity(ir,intent.model_dump())['overall']=='WARN' # runtime still unverified
    ir.gameplay.archetypes[1].attack.shots=4
    assert fidelity(ir,intent.model_dump())['overall']=='FAIL'
    ir=adventure.construct(design(),A,7);ir.areas[0].actors.append(Actor(id='npc',kind='npc',name='Unwanted NPC'))
    assert fidelity(ir,intent.model_dump())['overall']=='FAIL'


def test_control_compatibility_rejects_unimplemented_composition():
    raw=semantic().model_dump();raw['control']='platform';raw['genre']='platformer'
    assert feasibility(raw)['overall']=='FAIL'


@pytest.mark.parametrize('prompt',[A,'View the clearing from above; evade magical bolts, lasting until all three hearts are gone. Casters vanish after their fifth discharge, spaced a second apart.', 'Use overhead free movement in an endless dodge challenge. Newly appearing foes either follow me or launch five shots at 1000 millisecond intervals before leaving.'])
def test_live_handoffs_are_semantic_and_bind_numeric_behavior(monkeypatch,prompt):
    from providers import factory
    from services.semantic_intent import interpret
    intent=semantic(prompt)
    class Provider:
        calls=0
        def complete(self,system,user):
            assert user==prompt
            self.calls+=1
            if self.calls==1:
                assert 'Available capabilities' in system
                value=intent.model_dump()
            else:
                value=design(behavior(2,2000,5)).model_dump() # designer drift must be corrected by binding
            return SimpleNamespace(text=json.dumps(value),model='stub',latency_ms=1)
    provider=Provider();monkeypatch.setattr(factory,'get_provider',lambda:provider)
    parsed,_=interpret(prompt,'live');d,provenance=adventure.plan(prompt,'live',intent=parsed.model_dump())
    assert provider.calls==2 and d.gameplay==intent.gameplay
    ir=adventure.construct(d,prompt,9)
    assert fidelity(ir,parsed.model_dump())['overall']!='FAIL' and provenance['normalizations']


def test_bounded_repair_keeps_original_prompt_and_inventory_validation(monkeypatch):
    from providers import factory
    bad=design().model_dump();bad['actors']=[{'id':'survival_relic','kind':'item','name':'Survival Emblem'}]
    class Provider:
        calls=0
        def complete(self,system,user):
            self.calls+=1
            if self.calls==2:assert user.startswith(A) and 'Items need an inventory ID' in user
            return SimpleNamespace(text=json.dumps(bad if self.calls==1 else design().model_dump()),model='stub',latency_ms=1)
    p=Provider();monkeypatch.setattr(factory,'get_provider',lambda:p)
    bound=semantic().model_dump();bound['requirements']=[]
    d,provenance=adventure.plan(A,'live',intent=bound)
    assert p.calls==2 and not d.actors and len(provenance['validation_attempts'])==2
    assert provenance['validation_attempts'][0]['errors'][0]['loc']==()


def test_shared_switch_gate_constructs_one_door():
    d=platformer.fixture_design(D);d.collectibles_enabled=False
    from schemas.platformer import InteractionDesign
    d.interactions=[InteractionDesign(**v) for v in [{'trigger':'interact','section':0,'door_section':4,'gate':'security'},{'trigger':'interact','section':2,'door_section':4,'gate':'security'}]]
    # Validate typed overrides before construction.
    from schemas.platformer import GameDesign
    d=GameDesign.model_validate(d.model_dump());platformer.enforce_explicit_requirements(d,D)
    ir=platformer.construct(d,D,7)
    assert len(ir.links)==1 and len(ir.links[0].sources)==2
    assert len([e for e in ir.entities if e.kind=='door'])==1
    assert not any(e.kind=='crystal' for e in ir.entities)
    assert any(g.kind=='unlock' for g in ir.goals)

def test_semantic_exclusion_does_not_need_literal_no_combat_words(monkeypatch):
    from providers import factory
    prompt='Let this be a tranquil stroll through the woodland with friendly conversation.'
    peaceful=adventure.fixture_design('Create a peaceful top-down woodland adventure')
    hostile=adventure.fixture_design('Create a top-down forest adventure with enemies')
    intent=Intent(genre='adventure',control='top_down',loop='Explore peacefully',requirements=[{'source':prompt,'meaning':'No hostile encounters','capability':'no_combat','verification':'No enemies'}])
    class Provider:
        calls=0
        def complete(self,system,user):
            self.calls+=1
            if self.calls==2:assert user.startswith(prompt) and 'no_combat' in user
            return SimpleNamespace(text=(hostile if self.calls==1 else peaceful).model_dump_json(),model='stub',latency_ms=0)
    p=Provider();monkeypatch.setattr(factory,'get_provider',lambda:p)
    d,source=adventure.plan(prompt,'live',intent=intent.model_dump())
    assert p.calls==2 and not d.combat
    assert fidelity(adventure.construct(d,prompt,7),intent.model_dump())['overall']=='PASS'


def test_multi_role_spawns_and_invalid_concurrency_are_bounded():
    with pytest.raises(ValidationError,match='budget'):
        Gameplay(**{**behavior().model_dump(),'spawns':[{'id':'wave','archetypes':['hunter','caster'],'max_alive':40,'interval_ms':500}]})


def test_failed_model_repair_is_bounded_and_reports_fields(monkeypatch):
    from services.design_validation import DesignFailure
    from providers import factory
    class Provider:
        calls=0
        def complete(self,*args):
            self.calls+=1
            return SimpleNamespace(text='{"title":"invalid"}',model='stub',latency_ms=0)
    p=Provider();monkeypatch.setattr(factory,'get_provider',lambda:p)
    with pytest.raises(DesignFailure) as caught:adventure.plan(A,'live')
    assert p.calls==2 and len(caught.value.attempts)==2
    assert any(e['loc']==('areas',) for e in caught.value.attempts[0]['errors'])


def test_secondary_designer_labels_do_not_override_semantic_authority(monkeypatch):
    from providers import factory
    from schemas.platformer import RequestedFeature
    d=platformer.fixture_design(D);d.requested_features=[RequestedFeature(source='exit should only become available after both switches are activated',capability='combat_objective',description='Mislabeled gate requirement')]
    class Provider:
        def complete(self,*args):return SimpleNamespace(text=d.model_dump_json(),model='stub',latency_ms=0,fallback_events=[])
    monkeypatch.setattr(factory,'get_provider',lambda:Provider())
    parsed,source=platformer.plan(D,'live',{'genre':'platformer','control':'platform','requirements':[]})
    assert parsed.requested_features==[] and source['advisory_designer_requirements'] and source['requirement_authority']=='semantic_intent.json'


def test_fidelity_does_not_confuse_hostile_projectiles_with_player_weapons():
    ir=adventure.construct(design(),A,7)
    req={'source':A,'meaning':'Player weapon','capability':'projectile_attack','verification':'Player fires'}
    assert fidelity(ir,{'requirements':[req]})['overall']=='FAIL'
    assert fidelity(ir,{'requirements':[{**req,'mandatory':False}]})['overall']=='WARN'
    report=fidelity(ir,semantic().model_dump(),{'checks':[{'id':'composition_attack_sequence','passed':False},{'id':'composition_attack_sequence','passed':True}]})
    assert report['overall']=='FAIL'
