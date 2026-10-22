"""Bounded semantic routing with source-grounded, observable requirements."""
import hashlib, json, re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.gameplay import Gameplay

class Requirement(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source: str
    id: str | None = None
    meaning: str
    capability: Literal['platform_movement','top_down_movement','auto_run','flap','endless_obstacles','finite_finish','distance_score','gap_score','restart','boss_duel','boss_health_bar','boss_patterns','boss_defeat','no_ordinary_enemies','no_collectibles','no_combat','single_level','biome_regions','slippery_region','slippery_platforms','falling_icicles','boss_shield','quest_delivery','quest_collect','quest_activate','quest_unlock','quest_explore','adventure_combat','treasure_finish','projectile_attack','sword_melee','visual_theme','unsupported','health_damage','enemy_spawning','enemy_roles','attack_sequence','survival_time','no_inventory','no_quests','no_npcs','no_exit','switch_gate','moving_platforms','patrol_enemies']
    status: Literal['planned','approximated','unsupported']='planned'
    depends_on: list[str]=Field(default_factory=list)
    verification: str | None = None
    biomes: list[Literal['forest','garden','dark','snow','frozen_lake','icy_ruins']]=Field(default_factory=list)
    count: int | None = Field(default=None,ge=0,le=100)
    scope: Literal['game','same_level','separate_levels']='game'
    mandatory: bool = True
    category: Literal['mechanic','exclusion','presentation'] = 'mechanic'


def normalize_intent(raw, prompt):
    """Ground enum metadata to quoted prose; preserve the original candidate in logs.

    Cold terrain descriptions can use a snowy ruins renderer, but a named lake
    or garden remains a concrete constraint. No gameplay requirement is removed.
    """
    from copy import deepcopy
    value=deepcopy(raw);changes=[]
    for i, req in enumerate(value.get('requirements', [])):
        before=deepcopy(req);source=req.get('source','');cap=req.get('capability');s=source.lower()
        if not req.get('id'):
            req['id']='req_'+hashlib.sha256(f'{i}:{source}:{cap}'.encode()).hexdigest()[:12]
        if cap.startswith('no_'):req['category']='exclusion'
        if cap=='visual_theme':req['category']='presentation'
        if cap not in ('visual_theme','unsupported'):
            req['category']='exclusion' if cap.startswith('no_') else 'mechanic'
            if not re.search(r'\boptional(?:ly)?\b|if possible',s):req['mandatory']=True
        count=req.get('count')
        number_words={0:'zero',1:'one',2:'two',3:'three',4:'four',5:'five',6:'six',7:'seven',8:'eight',9:'nine',10:'ten'}
        if count is not None and not re.search(r'\b'+str(count)+r'\b|\b'+number_words.get(count,'__unmatched_number__')+r'\b',s) and not (count==0 and re.search(r'\bno\b|without|do not',s)):
            req['count']=None
        if cap=='unsupported' and re.search(r'animat|visual|artwork|transition|parallax',s) and not re.search(r'shield|damage|activat|unlock',s):
            req['category']='presentation'
        # Explicit exclusions occasionally arrive under unrelated enum labels.
        for pattern, correct in [(r'\bno quests\b','no_quests'),(r'\bno exit (?:gate|portal)', 'no_exit'),
                (r'\bno collectible','no_collectibles'),(r'\bno (?:enemies|combat)','no_combat'),
                (r'\bno (?:npcs|npc conversations)','no_npcs'),(r'\bno inventory','no_inventory')]:
            if re.search(pattern,s) and cap in ('unsupported','single_level','no_ordinary_enemies'):
                req.update(capability=correct,status='planned',category='exclusion',count=None);cap=correct
        if value.get('control')=='platform':
            if cap=='slippery_region':req['capability']='slippery_platforms';cap='slippery_platforms'
            if cap=='patrol_enemies' and re.search(r'icicles?',s):req['capability']='falling_icicles';cap='falling_icicles'
        biome_patterns={'forest':r'forest|woodland','garden':r'\bgarden\b','dark':r'\bdark\b|crypt',
            'snow':r'snow|frozen|\bice\b|icy','frozen_lake':r'(?:frozen|ice|icy) lake','icy_ruins':r'(?:icy|snowy|frozen).*ruins|ruins.*(?:icy|snowy|frozen)'}
        req['biomes']=[b for b in req.get('biomes',[]) if re.search(biome_patterns[b],s)]
        if req!=before:changes.append({'field':f'requirements.{i}','before':before,'after':deepcopy(req),'reason':'Source-grounded capability and biome metadata; stable requirement identity'})
    # Empty top-down default containers cannot bind side-scrolling construction.
    config=value.get('gameplay')
    if value.get('control')!='top_down' and config and not config.get('archetypes') and not config.get('spawns') and config.get('outcome','quests')=='quests':
        changes.append({'field':'gameplay','before':config,'after':None,'reason':'Empty top-down-only container; platformer health/combat use its own contract'})
        value['gameplay']=None
    if value.get('control')=='platform' and re.search(r'shield.*(?:prevents|prevent|invulnerab|disable|damag)',prompt,re.I|re.S) and not any(r['capability']=='boss_shield' for r in value.get('requirements',[])):
        source=next((s for s in re.split(r'(?<=[.!?])\s+',prompt) if re.search(r'shield',s,re.I)),prompt)
        value.setdefault('requirements',[]).append({'id':'req_'+hashlib.sha256(source.encode()).hexdigest()[:12],'source':source,'meaning':'Boss damage immunity controlled by activation prerequisites','capability':'boss_shield','status':'planned','mandatory':True,'verification':'Damage blocked until required switches activate'})
        changes.append({'field':'requirements','after':value['requirements'][-1],'reason':'Explicit boss shield cannot be replaced with a door dependency'})
    return value,changes

class ArcadeIntent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    difficulty: Literal['easy','medium','hard','extreme'] | None = None
    progression: Literal['stable','gradual','surge'] | None = None
    theme: Literal['neon','factory','forest','sky','ice'] | None = None
    player: Literal['robot','creature','bird','cube'] | None = None
    endless: bool | None = None
    exclusions: list[Literal['spike','gap','laser','barrier']] | None = None

class Intent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    genre: Literal['platformer','adventure','runner','unsupported']
    loop: str
    control: Literal['platform','top_down','auto_jump','flap','unsupported']
    requirements: list[Requirement]=Field(default_factory=list)
    arcade: ArcadeIntent | None = None
    perspective: Literal['side_scrolling','top_down'] | None = None
    structure: Literal['arena','connected_levels','world','endless','finite'] | None = None
    loops: list[Literal['exploration','combat','survival','quest','avoidance','boss','collection','interaction']] = Field(default_factory=list)
    gameplay: Gameplay | None = None

    @model_validator(mode='after')
    def dimensions(self):
        expected='top_down' if self.control=='top_down' else 'side_scrolling'
        if self.perspective and self.control!='unsupported' and self.perspective!=expected:
            raise ValueError('Perspective conflicts with the selected control model')
        if self.control=='top_down' and 'survival' in self.loops and (not self.gameplay or self.gameplay.outcome=='quests'):
            raise ValueError('Top-down survival requires explicit endless or finite survival gameplay, not a quest outcome')
        return self

def interpret(prompt, mode):
    if mode=='fixture':
        from services.game_factory import genre_for_prompt
        genre=genre_for_prompt(prompt)
        flap=bool(re.search(r'flap|tap.*(?:fly|airborne)|flying.*(?:tap|space)',prompt,re.I))
        arcade=None
        if genre=='runner':
            from services.runner import fixture_design
            d=fixture_design(prompt)
            arcade=ArcadeIntent(**{k:getattr(d,k) for k in ArcadeIntent.model_fields})
        return Intent(genre=genre,loop='Deterministic fixture interpretation',control='flap' if flap else 'auto_jump' if genre=='runner' else 'top_down' if genre=='adventure' else 'platform',arcade=arcade), {'provider':'fixture','live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider): raise ValueError('Live interpretation requires configured provider')
    system='Interpret the requested game semantically. Return JSON only, no code. Select platformer for manual run/jump or boss arenas; adventure for ALL top-down movement including non-quest survival; runner for automatic horizontal scrolling survival, including gravity plus flap impulse. Unsupported genres must be explicit. Enumerate important constraints with verbatim source substrings, intended meaning, runtime capability, dependencies, and concrete verification. Preserve exact counts in count, biome names in biomes, and same_level versus separate_levels in scope. Preserve exclusions, win conditions, control model and environmental physics. For runner requests also fill arcade with explicitly requested difficulty (very difficult means extreme), progression, theme (industrial factory versus neon city), player, endless and exclusions; leave unspecified fields null. These constraints bind the designer and fidelity report. For adventure requests use quest_collect for keys/items, quest_activate for switches, quest_unlock for doors, adventure_combat for monsters, and treasure_finish for final treasure. quest_delivery is ONLY an item return to an NPC; finite_finish is ONLY a finite runner. Dark and flower garden regions use dark/garden biome IDs. Sword combat is approximated by platformer projectiles; never claim implemented melee. Populate perspective, loops and structure independently. For top-down spawning, custom health or non-quest outcomes fill gameplay; preserve exact numeric attack/lifecycle parameters there. outcome=endless requires duration_seconds=null, never zero; use outcome=survive only for a finite requested survival deadline. Spawn archetypes are chosen uniformly. Projectiles are attack components, never inventory items. Dodge-only games have player_attack=false. Explicit exclusions use no_inventory/no_quests/no_npcs/no_exit/no_collectibles/no_combat. For platformer multi-switch dependencies use switch_gate (count is switch count), moving_platforms and patrol_enemies. Available capabilities: '+json.dumps(planner_catalog())+' Schema: '+json.dumps(Intent.model_json_schema())
    system+='\nFor platform controls gameplay MUST be null: bosses use BossEncounter, never top-down spawn archetypes. Use slippery_platforms for platform ice and falling_icicles for falling hazards; patrol_enemies only for enemies. A boss shield controlled by switches is boss_shield, not a switch opening a door. Use biomes only for explicitly named environments in the quoted source; NEVER copy the entire biome enum. Set count only for an explicit numeric quantity of this capability, not inferred decoration. Environmental artwork/animation is category=presentation; explicit mechanics and exclusions stay mandatory. Three boss attacks can use charge, volley and a telegraphed ground slam. A traversal level followed by a shielded boss is currently unavailable; preserve and report it.'
    result=provider.complete(system,prompt)
    from services.design_validation import validated_response
    grounding=[]
    def grounded(raw):
        raw,changes=normalize_intent(raw,prompt)
        grounding.extend(changes)
        value=Intent.model_validate(raw)
        for i,r in enumerate(value.requirements):
            if r.source.lower() not in prompt.lower():
                # Models often shorten a list clause. Expand only an ordered token
                # subsequence to its literal source sentence; never invent synonyms.
                words=re.findall(r'\w+',r.source.lower())
                match=None
                for sentence in re.split(r'(?<=[.!?])\s+',prompt):
                    tokens=iter(re.findall(r'\w+',sentence.lower()))
                    if len(words)>=2 and all(any(token==word for token in tokens) for word in words):
                        match=sentence;break
                if not match and len(words)>=5 and re.search(r'\.\.\.|…',r.source):
                    # Expand a model-abbreviated cross-sentence quote using only
                    # ordered original words, retaining the exact original span.
                    tokens=list(re.finditer(r'\w+',prompt.lower()));positions=[];cursor=0
                    for word in words:
                        found=next((j for j in range(cursor,len(tokens)) if tokens[j].group()==word),None)
                        if found is None:positions=[];break
                        positions.append(found);cursor=found+1
                    if positions:match=prompt[tokens[positions[0]].start():tokens[positions[-1]].end()]
                if match:
                    grounding.append({'field':f'requirements.{i}.source','before':r.source,'after':match,'reason':'Expanded ordered quote tokens to their original source sentence'})
                    r.source=match
                else:raise ValueError(f'requirements.{i}.source must quote an exact contiguous substring of the original prompt; invalid source: {r.source!r}')
        compatibility=feasibility(value.model_dump())
        correctable=[issue for issue in compatibility['issues'] if issue.get('code')!='RUNTIME_UNSUPPORTED']
        if correctable:raise ValueError('Capability/control mismatch: '+json.dumps(correctable))
        return value.model_dump()
    intent,attempts=validated_response(provider,system,prompt,result,Intent,grounded)
    return intent, {'provider':type(provider).__name__,'model':attempts[-1]['model'],'live':True,'validation_attempts':attempts,'source_grounding':grounding}
CAPABILITY_MAP: dict[str,tuple[str,str|None]] = {
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
    **{cap:('quests',cap) for cap in ['quest_collect','quest_activate','quest_unlock','quest_explore','adventure_combat']},
    'treasure_finish':('quests','adventure_completion'),
    'projectile_attack': ('player_attack', 'player_attack_damage'),
    'sword_melee': ('player_attack', 'player_attack_damage'),
    'visual_theme': ('theme', None),
    'unsupported': ('unsupported', None),
    'slippery_platforms': ('slippery','slippery_momentum'),
    'falling_icicles': ('entities','falling_icicle_cycle'),
    'boss_shield': ('boss.shield',None),
    'switch_gate': ('links','shared_gate_dependency'),
    'moving_platforms': ('platforms.moving','moving_platform_motion'),
    'patrol_enemies': ('entities.behavior','enemy_patrol'),
    'health_damage': ('gameplay.health','composition_health_loss'),
    'enemy_spawning': ('gameplay.spawns','composition_safe_spawning'),
    'enemy_roles': ('gameplay.archetypes','composition_enemy_roles'),
    'attack_sequence': ('gameplay.archetypes.attack','composition_attack_sequence'),
    'survival_time': ('gameplay.scoring','composition_survival_score'),
    **{cap:('gameplay',None) for cap in ['no_inventory','no_quests','no_npcs','no_exit']},
}

class Capability(BaseModel):
    model_config=ConfigDict(extra='forbid')
    ir_path: str
    verification: str | None
    controls: list[str]
    dependencies: list[str]
    required_configuration: list[str] = Field(default_factory=list)
    behavior_types: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    runtime: str
    limitation: str | None = None


def planner_catalog():
    """One registry feeds interpretation, feasibility, Inspector and fidelity paths."""
    composed={'health_damage','enemy_spawning','enemy_roles','attack_sequence','survival_time'}
    dependencies={'enemy_spawning':['top_down_movement','health_damage'], 'attack_sequence':['enemy_roles','health_damage'], 'survival_time':['health_damage']}
    return {name:Capability(ir_path=path,verification=check,controls=['top_down'] if name in composed or name in ('top_down_movement','biome_regions','slippery_region','quest_delivery','adventure_combat','treasure_finish') or name.startswith('quest_') else
        ['platform'] if name.startswith('boss_') or name in ('platform_movement','switch_gate','moving_platforms','patrol_enemies','slippery_platforms','falling_icicles') else
        ['auto_jump','flap'] if name in ('endless_obstacles','distance_score','gap_score','finite_finish') else [],
        dependencies=dependencies.get(name,[]),
        required_configuration=['gameplay',path] if name in composed else [path],
        behavior_types=['chase','patrol','shooter'] if name in ('enemy_spawning','enemy_roles') else ['timed_projectile_sequence'] if name=='attack_sequence' else [],
        conflicts=['no_combat'] if name in ('enemy_spawning','enemy_roles','attack_sequence','boss_duel','adventure_combat') else [],
        runtime='AdventureScene + BehaviorWorld' if name in composed else 'existing family adapter',
        limitation='One connected area; safe spawns may defer when no valid tile exists; uniform archetype choice' if name=='enemy_spawning' else None).model_dump()
        for name,(path,check) in CAPABILITY_MAP.items()}

def feasibility(intent):
    catalog=planner_catalog();issues=[]
    requested={r['capability'] for r in intent.get('requirements',[]) if r.get('status')!='unsupported'}
    for req in intent.get('requirements',[]):
        cap=req['capability'];entry=catalog.get(cap)
        if cap=='boss_shield':
            issues.append({'capability':cap,'requirement_id':req.get('id'),'code':'RUNTIME_UNSUPPORTED','reason':'Boss damage shields controlled by switches are not implemented; door links cannot target boss immunity'})
        if not entry or cap=='unsupported' or req.get('status')=='unsupported':continue
        if entry['controls'] and intent['control'] not in entry['controls']:
            issues.append({'capability':cap,'reason':'Capability requires controls '+','.join(entry['controls'])})
        if set(entry['conflicts']) & requested:
            issues.append({'capability':cap,'reason':'Conflicts with '+','.join(sorted(set(entry['conflicts']) & requested))})
    if intent.get('gameplay') and intent['control']!='top_down':
        issues.append({'capability':'gameplay','reason':'Composed spawn/attack components currently require the top-down adapter'})
    if 'boss_duel' in requested and requested & {'moving_platforms','slippery_platforms','falling_icicles','switch_gate'}:
        issues.append({'capability':'boss_duel','code':'RUNTIME_UNSUPPORTED','reason':'Boss adapter constructs a dedicated single arena and cannot preserve a preceding traversal route or switch puzzle'})
    return {'overall':'FAIL' if issues else 'PASS','issues':issues,'decision_source':'deterministic capability compatibility','catalog':catalog,
            'relationships':intent.get('gameplay'),'scope':'Control compatibility and typed component dependencies; construction and runtime verification follow.'}

def fidelity(ir, intent, qa=None):
    """Map semantic requests to construction witnesses; only named runtime checks verify play."""
    if not intent:return {'overall':'UNVERIFIED','requirements':[]}
    data=ir.model_dump();genre=data['genre'];boss=data.get('boss')
    entities=[e for level in (data.get('levels') or [data]) for e in level.get('entities',[])]
    actors=[a for area in data.get('areas',[]) for a in area['actors']]
    regions=[r for area in data.get('areas',[]) for r in area.get('regions',[])]
    gameplay=data.get('gameplay') or {}
    no_enemies=not gameplay.get('archetypes') and not any(e['kind']=='enemy' and not e.get('boss') for e in entities) and not any(a['kind']=='enemy' for a in actors)
    witnesses={
        'platform_movement':genre=='platformer','top_down_movement':genre=='adventure',
        'auto_run':genre=='runner' and data['mode']=='ground','flap':genre=='runner' and data['mode']=='flap',
        'endless_obstacles':genre=='runner' and data['endless'],'finite_finish':(genre=='runner' and not data['endless']) or (genre=='adventure' and bool(data['quests'])),
        'distance_score':data.get('scoring')=='distance','gap_score':data.get('scoring')=='gaps','restart':True,
        'boss_duel':bool(boss) and sum(bool(e.get('boss')) for e in entities)==1 and no_enemies,
        'boss_health_bar':bool(boss),'boss_patterns':bool(boss) and {'charge','volley'}<=set(boss['patterns']),
        'boss_defeat':bool(boss) and boss['victory']=='boss_defeat',
        'no_ordinary_enemies':no_enemies,'no_combat':no_enemies and not boss and not (genre=='adventure' and data.get('combat')),
        'switch_gate':any(len(link['sources'])>=2 and link['condition']=='all' for level in (data.get('levels') or [data]) for link in level.get('links',[])),
        'moving_platforms':any(p.get('moving') for level in (data.get('levels') or [data]) for p in level.get('platforms',[])),
        'patrol_enemies':any(e['kind']=='enemy' and e.get('behavior')=='patrol' for e in entities),
        'no_collectibles':not any(e['kind']=='crystal' for e in entities) and not any(a['kind'] in ('item','treasure') for a in actors),
        'single_level':len(data.get('areas') or data.get('levels') or [data])==1,
        'biome_regions':len(regions)>=2,'slippery_region':any(r['slippery'] for r in regions),
        'slippery_platforms':bool(data.get('slippery')),'falling_icicles':any(e['kind']=='icicle' for e in entities),
        'boss_shield':False,
        'quest_delivery':any(q['kind']=='deliver' for q in data.get('quests',[])),
        'projectile_attack':data.get('player_attack')=='projectile' or (genre=='adventure' and (gameplay.get('player_attack',False) if gameplay else data['combat'])),'sword_melee':data.get('player_attack')=='projectile',
        'visual_theme':bool(data.get('theme')),'unsupported':False,
    }
    witnesses.update({cap:any(q['kind']==kind for q in data.get('quests',[])) for cap,kind in [('quest_collect','collect'),('quest_activate','activate'),('quest_unlock','unlock'),('quest_explore','explore')]})
    witnesses['adventure_combat']=genre=='adventure' and data['combat'] and any(a['kind']=='enemy' for a in actors)
    witnesses['treasure_finish']=genre=='adventure' and any(q['kind']=='collect' and any(a['id']==q['target'] and a['kind']=='treasure' for a in actors) for q in data.get('quests',[]))
    witnesses.update(health_damage=bool(gameplay),enemy_spawning=bool(gameplay.get('spawns')),enemy_roles=bool(gameplay.get('archetypes')),
        attack_sequence=any(a.get('attack') for a in gameplay.get('archetypes',[])),survival_time=gameplay.get('scoring')=='survival_time',
        no_inventory=not any(a['kind']=='item' for a in actors) and not any(q['kind']=='deliver' for q in data.get('quests',[])),
        no_quests=not data.get('quests'),no_npcs=not any(a['kind']=='npc' for a in actors),no_exit=bool(boss) or genre=='runner' and data.get('endless') or gameplay.get('outcome') in ('endless','survive'))
    expected_control='flap' if genre=='runner' and data['mode']=='flap' else 'auto_jump' if genre=='runner' else 'top_down' if genre=='adventure' else 'platform'
    root_ok=intent.get('genre',genre)==genre and intent.get('control',expected_control)==expected_control
    arcade_checks={k:{'requested':v,'actual':data.get(k),'preserved':data.get(k)==v} for k,v in (intent.get('arcade') or {}).items() if v is not None}
    root_ok=root_ok and all(c['preserved'] for c in arcade_checks.values())
    behavior_preserved=intent.get('gameplay') is None or intent['gameplay']==data.get('gameplay')
    root_ok=root_ok and behavior_preserved
    checks={}
    for c in (qa or {}).get('checks',[]):checks[c['id']]=checks.get(c['id'],True) and bool(c['passed'])
    result=[]
    for req in intent.get('requirements',[]):
        cap=req['capability']
        # Backward-compatible binding for saved intents from the narrower registry.
        # Keep the original ID in the report; do not broaden NPC delivery semantics.
        if genre=='adventure':
            if cap=='quest_delivery' and not witnesses['quest_delivery']:
                if re.search(r'activat|switch',req['source'],re.I):cap='quest_activate'
                elif re.search(r'collect|key|pick up',req['source'],re.I):cap='quest_collect'
            if cap=='finite_finish':cap='treasure_finish'
        path,check=CAPABILITY_MAP.get(cap,('unsupported',None))
        if cap=='moving_platforms' and re.search(r'switch.*(?:activat|enabl)',req['source'],re.I):check='switch_world_effects'
        if genre=='adventure' and cap=='projectile_attack':check='adventure_combat'
        if cap=='restart':check={'adventure':'whole_game_restart','platformer':'boss_restart' if boss else 'whole_campaign_restart','runner':'rapid_restart'}[genre]
        built=witnesses.get(cap,False)
        if cap=='moving_platforms' and check=='switch_world_effects':
            built=built and any(p.get('activation_sources') for level in (data.get('levels') or [data]) for p in level.get('platforms',[]))
        requested_biomes=set(req.get('biomes',[]))
        if 'forest' in requested_biomes and 'garden' in {r['biome'] for r in regions} and re.search(r'garden',req['source'],re.I):
            requested_biomes.discard('forest');requested_biomes.add('garden')
        if requested_biomes and cap in ('biome_regions','slippery_region'):
            actual_biomes={r['biome'] for r in regions}
            # Snow is a terrain family; snowy ruins have snow ground too.
            if actual_biomes & {'icy_ruins','frozen_lake'}:actual_biomes.add('snow')
            built=built and requested_biomes.issubset(actual_biomes)
            if req.get('scope')=='same_level':
                built=built and any(requested_biomes.issubset({r['biome'] for r in area.get('regions',[])} | ({'snow'} if any(r['biome'] in ('icy_ruins','frozen_lake') for r in area.get('regions',[])) else set())) for area in data.get('areas',[]))
        if req.get('count') is not None:
            if cap in ('boss_duel','boss_health_bar'):built=built and sum(bool(e.get('boss')) for e in entities)==req['count']
            elif cap=='single_level':built=built and len(data.get('areas') or data.get('levels') or [data])==req['count']

            elif cap=='switch_gate':built=built and any(len(link['sources'])==req['count'] for level in (data.get('levels') or [data]) for link in level.get('links',[]))
            elif cap=='health_damage':built=built and gameplay.get('health')==req['count']
            elif cap=='enemy_roles':built=built and len(gameplay.get('archetypes',[]))==req['count']
            elif cap=='attack_sequence':built=built and all(a['attack']['shots']==req['count'] for a in gameplay.get('archetypes',[]) if a.get('attack'))
            elif cap=='quest_collect':built=built and sum(q['count'] for q in data.get('quests',[]) if q['kind']=='collect')==req['count']
            elif cap=='boss_patterns' and req['count']>1:built=built and len(set((boss or {}).get('patterns',[])))==req['count']

        status='unsupported' if cap=='unsupported' or req.get('status')=='unsupported' else 'failed' if not built else 'approximated' if cap in ('sword_melee','visual_theme') or req.get('status')=='approximated' else 'verified' if check and checks.get(check) else 'constructed_unverified' if check else 'validated_constraint'
        if built and cap=='moving_platforms' and check=='switch_world_effects':status='approximated'
        if status=='failed' and not req.get('mandatory',True):status='optional_unavailable'
        if check in checks and not checks[check]:status='failed' if req.get('mandatory',True) and req.get('category')!='presentation' else 'optional_unavailable'
        if status=='failed' and req.get('category')=='presentation':status='optional_unavailable'
        result.append({**req,'requested_capability':req['capability'],'capability':cap,'bound_biomes':sorted(requested_biomes),'constructed':built,'status':status,'failure_stage':'construction' if not built else 'runtime' if check in checks and not checks[check] else None,'ir_path':path,'runtime_check':check,'runtime_verified':bool(built and check and checks.get(check))})
    unsupported_core=[r['id'] if r.get('id') else r['source'] for r in result if r['status']=='unsupported' and r.get('mandatory',True) and r.get('category')!='presentation']
    return {'behavior_preserved':behavior_preserved,'control_preserved':root_ok,'arcade_constraints':arcade_checks,'unsupported_core':unsupported_core,'overall':'FAIL' if not root_ok or unsupported_core or any(r['status']=='failed' for r in result) else 'WARN' if any(r['status'] in ('approximated','unsupported','constructed_unverified','optional_unavailable') for r in result) else 'PASS','requirements':result,'scope':'Structured construction witnesses plus specific runtime checks; visual style needs human review.'}
