"""Bounded semantic routing with source-grounded, observable requirements."""
import json, re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Requirement(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source: str
    meaning: str
    capability: Literal['platform_movement','top_down_movement','auto_run','flap','endless_obstacles','finite_finish','distance_score','gap_score','restart','boss_duel','boss_health_bar','boss_patterns','boss_defeat','no_ordinary_enemies','no_collectibles','no_combat','single_level','biome_regions','slippery_region','quest_delivery','projectile_attack','sword_melee','visual_theme','unsupported']
    status: Literal['planned','approximated','unsupported']='planned'
    depends_on: list[str]=Field(default_factory=list)
    verification: str
    biomes: list[Literal['forest','snow','frozen_lake','icy_ruins']]=Field(default_factory=list)
    count: int | None = Field(default=None,ge=0,le=100)
    scope: Literal['game','same_level','separate_levels']='game'

class Intent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    genre: Literal['platformer','adventure','runner','unsupported']
    loop: str
    control: Literal['platform','top_down','auto_jump','flap','unsupported']
    requirements: list[Requirement]=Field(default_factory=list)

def interpret(prompt, mode):
    if mode=='fixture':
        from services.game_factory import genre_for_prompt
        genre=genre_for_prompt(prompt)
        flap=bool(re.search(r'flap|tap.*(?:fly|airborne)|flying.*(?:tap|space)',prompt,re.I))
        return Intent(genre=genre,loop='Deterministic fixture interpretation',control='flap' if flap else 'auto_jump' if genre=='runner' else 'top_down' if genre=='adventure' else 'platform'), {'provider':'fixture','live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider): raise ValueError('Live interpretation requires configured provider')
    result=provider.complete('Interpret the requested game semantically. Return JSON only, no code. Select platformer for manual run/jump or boss arenas; adventure for top-down exploration/quests; runner for automatic horizontal scrolling survival, including gravity plus flap impulse. Unsupported genres must be explicit. Enumerate important constraints with verbatim source substrings, intended meaning, runtime capability, dependencies, and concrete verification. Preserve exact counts in count, biome names in biomes, and same_level versus separate_levels in scope. Preserve exclusions, win conditions, control model and environmental physics. Sword combat is approximated by platformer projectiles; never claim implemented melee. Schema: '+json.dumps(Intent.model_json_schema()),prompt)
    intent=Intent.model_validate_json(re.sub(r'^```(?:json)?\s*|\s*```$','',result.text.strip()))
    if any(r.source.lower() not in prompt.lower() for r in intent.requirements): raise ValueError('Intent sources must quote original prompt')
    return intent, {'provider':type(provider).__name__,'model':result.model,'live':True}
CAPABILITY_MAP = {
    'platform_movement': ('player', 'mandatory_route_edges'),
    'top_down_movement': ('areas', 'top_down_horizontal_movement'),
    'auto_run': ('mode', 'runner_input'),
    'flap': ('mode', 'repeatable_flap'),
    'endless_obstacles': ('endless', 'endless_bounded_state'),
    'finite_finish': ('finish_distance', None),
    'distance_score': ('scoring', 'score_once'),
    'gap_score': ('scoring', 'score_once'),
    'restart': ('genre', 'rapid_restart'),
    'boss_duel': ('boss', 'boss_duel'),
    'boss_health_bar': ('boss.health', 'boss_arena'),
    'boss_patterns': ('boss.patterns', 'boss_volley'),
    'boss_defeat': ('boss.victory', 'boss_duel'),
    'no_ordinary_enemies': ('entities', None),
    'no_collectibles': ('entities', None),
    'no_combat': ('combat', None),
    'single_level': ('areas/levels', None),
    'biome_regions': ('areas.regions', 'biome_regions'),
    'slippery_region': ('areas.regions.slippery', 'localized_slippery'),
    'quest_delivery': ('quests', 'adventure_completion'),
    'projectile_attack': ('player_attack', 'player_attack_damage'),
    'sword_melee': ('player_attack', 'player_attack_damage'),
    'visual_theme': ('theme', None),
    'unsupported': ('unsupported', None),
}

def fidelity(ir, intent, qa=None):
    """Map semantic requests to construction witnesses; only named runtime checks verify play."""
    if not intent:return {'overall':'UNVERIFIED','requirements':[]}
    data=ir.model_dump();genre=data['genre'];boss=data.get('boss')
    entities=[e for level in (data.get('levels') or [data]) for e in level.get('entities',[])]
    actors=[a for area in data.get('areas',[]) for a in area['actors']]
    regions=[r for area in data.get('areas',[]) for r in area.get('regions',[])]
    no_enemies=not any(e['kind']=='enemy' and not e.get('boss') for e in entities) and not any(a['kind']=='enemy' for a in actors)
    witnesses={
        'platform_movement':genre=='platformer','top_down_movement':genre=='adventure',
        'auto_run':genre=='runner' and data['mode']=='ground','flap':genre=='runner' and data['mode']=='flap',
        'endless_obstacles':genre=='runner' and data['endless'],'finite_finish':genre=='runner' and not data['endless'],
        'distance_score':data.get('scoring')=='distance','gap_score':data.get('scoring')=='gaps','restart':True,
        'boss_duel':bool(boss) and sum(bool(e.get('boss')) for e in entities)==1 and no_enemies,
        'boss_health_bar':bool(boss),'boss_patterns':bool(boss) and set(boss['patterns'])=={'charge','volley'},
        'boss_defeat':bool(boss) and boss['victory']=='boss_defeat',
        'no_ordinary_enemies':no_enemies,'no_combat':(genre=='runner' or not data.get('combat',True)) and no_enemies,
        'no_collectibles':not any(e['kind']=='crystal' for e in entities) and not any(a['kind'] in ('item','treasure') for a in actors),
        'single_level':len(data.get('areas') or data.get('levels') or [data])==1,
        'biome_regions':len(regions)>=2,'slippery_region':any(r['slippery'] for r in regions),
        'quest_delivery':any(q['kind']=='deliver' for q in data.get('quests',[])),
        'projectile_attack':data.get('player_attack')=='projectile','sword_melee':data.get('player_attack')=='projectile',
        'visual_theme':bool(data.get('theme')),'unsupported':False,
    }
    expected_control='flap' if genre=='runner' and data['mode']=='flap' else 'auto_jump' if genre=='runner' else 'top_down' if genre=='adventure' else 'platform'
    root_ok=intent.get('genre',genre)==genre and intent.get('control',expected_control)==expected_control
    checks={c['id']:c['passed'] for c in (qa or {}).get('checks',[])}
    result=[]
    for req in intent.get('requirements',[]):
        cap=req['capability'];path,check=CAPABILITY_MAP.get(cap,('unsupported',None))
        if cap=='restart':check={'adventure':'whole_game_restart','platformer':'boss_restart' if boss else 'whole_campaign_restart','runner':'rapid_restart'}[genre]
        built=witnesses.get(cap,False)
        requested_biomes=set(req.get('biomes',[]))
        if requested_biomes:
            built=built and requested_biomes.issubset({r['biome'] for r in regions})
            if req.get('scope')=='same_level': built=built and any(requested_biomes.issubset({r['biome'] for r in area.get('regions',[])}) for area in data.get('areas',[]))
        if req.get('count') is not None:
            if cap in ('boss_duel','boss_health_bar'):built=built and sum(bool(e.get('boss')) for e in entities)==req['count']
            elif cap=='single_level':built=built and len(data.get('areas') or data.get('levels') or [data])==req['count']

        status='unsupported' if cap=='unsupported' or req.get('status')=='unsupported' else 'failed' if not built else 'approximated' if cap in ('sword_melee','visual_theme') or req.get('status')=='approximated' else 'verified' if check and checks.get(check) else 'constructed_unverified' if check else 'validated_constraint'
        if check in checks and not checks[check]:status='failed'
        result.append({**req,'constructed':built,'status':status,'ir_path':path,'runtime_check':check,'runtime_verified':bool(check and checks.get(check))})
    return {'control_preserved':root_ok,'overall':'FAIL' if not root_ok or any(r['status']=='failed' for r in result) else 'WARN' if any(r['status'] in ('approximated','unsupported','constructed_unverified') for r in result) else 'PASS','requirements':result,'scope':'Structured construction witnesses plus specific runtime checks; visual style needs human review.'}
