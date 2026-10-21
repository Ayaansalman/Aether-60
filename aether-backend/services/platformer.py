"""Design interpretation, seeded construction and conservative ballistic route validation."""
import hashlib
import json
import math
import random
import re
from schemas.platformer import GameDesign, LevelDesign, PlatformerIR, LevelIR, Platform, Player, Entity, Section
from services.capabilities import extract_requirements, requirement_evidence
from services.gameplay import compose_intent, compile_interactions, compile_goals, validate_gameplay


def requested_level_count(prompt: str) -> int | None:
    match = re.search(r'\b(two|three|2|3)[ -]+(?:(?:connected|ice|forest|industrial|twilight|platformer)[ -]+)*(?:levels?|stages?)\b', prompt, re.I)
    if match:
        return {'two': 2, 'three': 3, '2': 2, '3': 3}[match.group(1).lower()]
    return 3 if re.search(r'\b(?:multiple|multi)[ -](?:levels?|stages?)\b', prompt, re.I) else None


def progression_specs(design: GameDesign, prompt: str) -> list[LevelDesign]:
    """Deterministic compatibility planner for fixtures and older saved designs.

    Explicit model level specifications bypass this planner entirely.
    """
    result = []
    for stage in range(design.level_count):
        sections = []
        for j in range(5 + stage):
            source = design.sections[j % len(design.sections)]
            challenge = ('traversal', 'exploration', 'traversal', 'precision', 'traversal')[j % 5] if stage == 0 else ('traversal', 'hazards', 'exploration', 'combat', 'precision', 'moving', 'precision')[j % 7]
            if challenge == 'combat' and not any(s.enemies for s in design.sections): challenge = 'precision'
            if challenge == 'moving' and not design.moving_platforms: challenge = 'exploration'
            sections.append(source.model_copy(update={
                'challenge': challenge,
                'kind': 'bridge' if challenge == 'precision' else 'ruins' if challenge == 'exploration' else source.kind,
                'length': 8 if stage == 0 else 4 if challenge == 'precision' else 7,
                'gap': 1 if stage == 0 else 2 if stage == 1 else 3,
                'elevation': 0 if stage == 0 else 1 if j % 2 else 2,
                'enemies': any(s.enemies for s in design.sections) and j > 0 and j % 2 == 1,
                'encounter': source.encounter,
                'hazards': source.hazards and j > 0 and stage > 0,
            }))
        result.append(LevelDesign(
            title=f'{design.title[:55]} · {("Foothills", "Heights", "Summit")[stage]}',
            theme=design.theme, topology=('journey', 'ascent', 'terraces')[stage],
            difficulty='relaxed' if design.difficulty == 'relaxed' else ('relaxed', 'balanced', 'challenging')[stage],
            slippery=design.slippery,
            falling_icicles=(stage > 0 and design.falling_icicles),
            timed_hazards=stage > 0 and design.timed_hazards,
            objective=design.objective, sections=sections,
            interactions=design.interactions[:1] if stage == 0 else design.interactions,
            briefing=('Learn the terrain and explore the upper paths.', 'Climb through the new hazards.', 'Combine your skills on the final crossing.')[stage]))
    # Bounded, inspectable fixture interpretation of explicit introduction clauses.
    markers = list(re.finditer(r'\b(first|second|third|final|last)\s+(?:(?:level|stage)\b|(?=introduces?\b|combines?\b))', prompt, re.I))
    patterns = {'slippery': r'slippery|sliding terrain', 'falling_icicles': r'icicles?',
                'timed_hazards': r'timed hazards?|machinery', 'moving_platforms': r'moving platforms?'}
    clauses = [(marker.group(1).lower(), prompt[marker.end():markers[i+1].start() if i+1 < len(markers) else len(prompt)]) for i, marker in enumerate(markers)]
    scoped = {key for key, pattern in patterns.items() if any(re.search(pattern, text, re.I) for _, text in clauses)}
    for label, text in clauses:
        index = {'first': 0, 'second': 1, 'third': 2, 'final': len(result)-1, 'last': len(result)-1}[label]
        if index >= len(result): continue
        for key in scoped:
            setattr(result[index], key, bool(re.search(patterns[key], text, re.I) or re.search(r'both mechanics|combine.*both', text, re.I) and getattr(design, key)))
    return result


def fixture_design(prompt: str) -> GameDesign:
    """Deterministic offline provider, never presented as language-model output."""
    p = prompt.lower()
    industry = any(w in p for w in ("industrial", "robot", "factory", "machinery"))
    tower = any(w in p for w in ("tower", "climb", "precision"))
    calm = any(w in p for w in ("peaceful", "relaxed", "cozy", "easy", "no enemies"))
    ice = any(w in p for w in ("frozen", "ice", "icicle"))
    theme = "industrial" if industry else "ice" if ice else "twilight" if tower else "forest"
    unsupported = [f"Unsupported request: {word}" for word in ("multiplayer", "3d", "rpg", "dialogue", "crafting", "underwater") if re.search(r"\b" + word + r"\b", p)]
    design = GameDesign(
        title="The Copperworks" if industry else "The Frostbound Vault" if ice else "Stairway to the Stars" if tower else "The Verdant Passage",
        topology="ascent" if tower else "terraces" if industry else "cavern" if ice else "journey",
        slippery="slippery" in p, falling_icicles="icicle" in p,
        timed_hazards=industry and not calm,
        exit_indicator="flash" if "flashing" in p else "glow" if "glowing" in p else "none",
        collectible="relics" if "relic" in p else "crystals",
        level_count=requested_level_count(prompt) or 1,
        premise=prompt[:500], theme=theme, difficulty="relaxed" if calm else "challenging" if tower else "balanced",
        abilities=[a for a, words in [("double_jump", ("double jump", "double-jump")), ("dash", ("dash",))] if any(w in p for w in words)],
        objective="collect_and_exit" if any(w in p for w in ("collect", "crystal", "gem")) else "reach_exit",
        checkpoints="no checkpoint" not in p, moving_platforms="moving" in p,
        sections=[Section(kind="ascent" if tower else "terraces" if industry else "cavern" if ice else "ruins" if i % 3 == 2 else "meadow",
                          encounter='shooter' if 'ranged' in p else ("patrol", "chase", "shooter")[i % 3] if industry else "patrol",
                          length=5 + i % 3, elevation=2 if tower else i % 3 - 1,
                          gap=1 if calm else 2 + (i % 2 if tower else 0), enemies=not calm and (not ice or any(w in p for w in ('enemies', 'monsters', 'creatures', 'robots'))) and i % 3 == 1,
                          hazards=not calm and i % 3 == 2) for i in range(9 if tower else 8)],
        unsupported=unsupported, design_notes=["Offline fixture: keyword interpretation and seeded construction; no model was called."])
    compose_intent(design, prompt)
    if 'boss' in p:
        from schemas.platformer import BossEncounter
        design.title='Duel at the Castle'
        design.boss=BossEncounter()
        design.player_attack='projectile'
        design.collectibles_enabled=False
    return design


def plan(prompt: str, mode: str, intent=None):
    if mode == "fixture":
        return fixture_design(prompt), {"provider": "fixture", "model": None, "live": False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider = get_provider()
    if isinstance(provider, MockModelProvider):
        raise ValueError("Live mode requires MODEL_PROVIDER=openai_compat and a configured API key. Use the explicitly labeled fixture mode for offline work.")
    system = """You are Aether's platformer game designer. Interpret the user's requirements faithfully.
Return ONLY a JSON object matching the following schema. No executable code.
Boss encounters: boss is a BossEncounter or null. For a duel choose exactly one boss, ordinary_enemies=0,
victory=boss_defeat and patterns charge+volley. This builds a bounded arena, not traversal sections.
Explicitly decide collectibles_enabled: only true when the requested loop uses collectibles.
Use player_attack=projectile as the available combat ability; sword melee is an approximation,
and design_notes must disclose this. collectibles_enabled=false for no collectible requests.
Do not select ordinary enemies, exit objectives, extra levels or hazards for a one-on-one duel.
Supported: platformer; forest/industrial/twilight/ice environments; crystals or relics;
patrol, chase and shooter enemies (section.encounter); proximity or timed falling icicles; slippery
terrain; timed machinery; checkpoints; double_jump; dash; moving platforms; exit_indicator
none/glow/pulse/flash and exit_style shrine/gate/beacon; 1-3 connected levels. Choose topology journey/ascent/terraces/cavern.
Set falling_icicles/slippery/timed_hazards/level_count/collectible explicitly to match requests.
For multiple levels, populate levels with exactly level_count LevelDesign objects. Each has its own
title, theme, topology, difficulty, objective, briefing and 5-14 sections. Explicitly set per-level
mechanic booleans, including false when a mechanic has not been introduced yet. Follow first/second/final
level instructions precisely. Introduce, develop, then combine requested mechanics; never clone stages.
Use section.challenge traversal/precision/combat/hazards/exploration/moving to compose encounters,
optional collectible shelves and moving alternate paths. Combat/hazards still require their corresponding
enemies/hazards flags. Do not introduce unrequested mechanics merely for variety.
Gameplay components: interactions connect an interact/touch/pressure/proximity/projectile trigger in
section N to a latched security door in a later section. Each trigger must precede its door. The builder
uses ZERO-BASED section indices: 0 <= section < door_section < len(sections) for each individual level.
assigns safe stable IDs and links; no scripting. Projectile switches require player_attack=projectile.
Available encounters: patrol, chase, shooter (retreats when crowded), stationary turret, and ambusher
(proximity windup then a bounded lunge). Section.ai configures health, cooldown_ms, telegraph_ms, radius.
player_attack=stomp/projectile; projectile controls are F/X. Select projectile attacks only if requested or
needed by a projectile switch. Prefer existing stomp combat for ordinary defeat-creature requests.
objectives is a conjunction of defeat/activate/unlock/collect/survive/time_limit conditions plus the exit.
count=0 means all matching targets; positive counts must fit the available entities. seconds=1..180.
Use campaign_objectives for conditions evaluated only at the final exit, with targets across levels.
Do not combine a survival duration with a shorter deadline. Provide enough traversal time for deadlines.
LevelDesign.objectives and interactions override defaults, including [] for an introduction without them.
platform_motion configures bounded horizontal/vertical sine/ping_pong movement, never unlimited drift.
Prompt distinctions: temple guards -> defeat goals and combat; factory switches -> interactions and unlock
goals with requested machinery; ice/ranged enemies -> slippery, icicles and shooters. Do not add every system.
Enumerate each concrete user request in requested_features, with an exact substring of the user's
prompt as source, a registered capability and a description. Unavailable behavior must use
capability=unsupported and also appear in unsupported. Do not drop a request to fit the engine.
Subjective style requests should be described in design_notes, not certified by functional QA.
Choose encounters deliberately, safe introductory segments and more demanding later sections.
Put unsupported requested genres/mechanics in unsupported; never pretend they are implemented.
The unsupported array must include ONLY explicitly requested unavailable features. Leave it empty
when all requested features are supported; do not invent unrequested inventory, combat or other limitations.
Compose 5-14 varied sections. kind=meadow/ruins/factory/ascent/gauntlet/cavern/terraces/bridge, length=4..10 tiles,
elevation=-1..2 tiles (positive climbs), gap=1..3 tiles, enemies/hazards boolean.
Tower requests should use ascending sections; peaceful requests should exclude enemies and hazards.
Set collectibles_enabled=false unless pickups are requested. For multiple switches opening ONE gate, give their interactions the same gate ID and door_section; condition is all switches. Separate gates use distinct IDs. Preserve exact requested switch counts.
GameDesign JSON Schema:\n""" + json.dumps(GameDesign.model_json_schema())
    if intent: system += "\nPreserve this semantic interpretation and requirement relationships: "+json.dumps(intent)
    from services.design_validation import validated_response
    result=provider.complete(system,prompt)
    secondary_requirements=[]
    def grounded(raw):
        if intent:
            # Interpretation owns the requirement contract. A second classifier
            # in the designer previously relabeled gate objectives as combat.
            secondary_requirements.extend(raw.get('requested_features',[]))
            raw={**raw,'requested_features':[]}
        design=GameDesign.model_validate(raw)
        if any(feature.source.lower() not in prompt.lower() for feature in design.requested_features):
            raise ValueError('requested_features.source must quote the original prompt exactly')
        return design.model_dump()
    design,attempts=validated_response(provider,system,prompt,result,GameDesign,grounded)
    return design, {"provider":type(provider).__name__,"model":attempts[-1]['model'],"live":True,
        "initial_latency_ms":result.latency_ms,"fallbacks":getattr(result,'fallback_events',[]),"validation_attempts":attempts,
        "requirement_authority":"semantic_intent.json" if intent else "designer requested_features and deterministic extraction",
        "advisory_designer_requirements":secondary_requirements}



def construct(design: GameDesign, prompt: str, seed: int | None = None, level_id: str = 'L1') -> PlatformerIR:
    if design.boss:
        from services.boss import construct_arena
        return construct_arena(design,prompt,seed)
    seed = seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    # Leave enough vertical room for every requested ascent.
    start_y = max(14, 4 + 2 * len(design.sections))
    platforms = [Platform(x=0, y=start_y, width=8, kind=design.topology)]
    entities = []
    x, y = 8, start_y
    for i, section in enumerate(design.sections):
        # Reusable components vary geometry as well as encounters. Mandatory gaps stay
        # within a single jump; moving platforms and exploration shelves are optional.
        precision = section.challenge == 'precision'
        gap = min(section.gap, 2) if design.slippery else section.gap
        x += gap
        rise = section.elevation
        if design.topology == "ascent":
            rise = max(1, section.elevation)
        y = max(5, min(start_y + 2, y - rise))
        length = max(4, min(10, section.length + rng.choice([-1, 0, 1])))
        if precision: length = 6 if section.enemies else 4
        if section.challenge == 'combat': length = max(8, length)
        platform = Platform(x=x, y=y, width=length, kind=section.kind)
        platforms.append(platform)
        main_index = len(platforms) - 1
        offsets = range(1, length - 1, 2) if section.kind not in ('bridge', 'gauntlet') else [length // 2]
        for offset in (offsets if design.collectibles_enabled else []):
            lift = 20 * (1 - abs(offset - length/2) / (length/2)) if design.topology == 'journey' else (offset % 3)*10
            entities.append(Entity(x=(x + offset + .5) * 36, y=y * 36 - 56 - lift, kind="crystal", platform=main_index))
        if section.enemies:
            # Reserve a run-up at the departure edge; encounters belong within the
            # platform, away from the narrow landing and checkpoint zones.
            entities.append(Entity(x=(x + length * .4) * 36, y=y * 36 - 22, kind="enemy", platform=main_index, behavior=section.encounter, ai=section.ai))
        if design.falling_icicles and i % 2 == 1:
            trigger = ('proximity' if i % 4 == 1 else 'timer') if design.icicle_trigger == 'mixed' else design.icicle_trigger
            entities.append(Entity(x=(x + length * .65) * 36, y=y * 36 - 220, kind="icicle", platform=len(platforms)-1, trigger=trigger, period_ms=design.hazard_period_ms))
        if design.timed_hazards and i % 3 == 2:
            entities.append(Entity(x=(x + length * .65) * 36, y=y*36 - 16, kind="timed_hazard", platform=len(platforms)-1, period_ms=design.hazard_period_ms))
        if section.hazards and not design.falling_icicles and not design.timed_hazards:
            entities.append(Entity(x=(x + length // 2 + .5) * 36, y=y * 36 - 10, kind="spikes", platform=main_index))
        if design.checkpoints and (i == len(design.sections)//2 - 1 or (i > 0 and section.challenge in ('precision', 'hazards', 'combat') and design.sections[i-1].challenge == 'traversal')):
            previous_index = next(j for j in range(main_index-1, -1, -1) if not platforms[j].moving and platforms[j].route == 'main')
            previous = platforms[previous_index]
            entities.append(Entity(x=(previous.x + previous.width - 1)*36, y=previous.y*36-30, kind='checkpoint', platform=previous_index))
        clear_stomp = section.enemies and design.player_attack == 'stomp'
        moving = design.moving_platforms and not clear_stomp and (i % 2 == 0 or section.challenge == 'moving')
        if moving:
            # Optional elevated route; mandatory route is static and independently reachable.
            platforms.append(Platform(x=x + 1, y=y - 2, width=4, kind='bridge', moving=True, route='optional', motion=design.platform_motion))
        if (section.challenge == 'exploration' or section.kind in ('ruins', 'terraces') and i % 3 == 2) and not moving and not clear_stomp:
            # An optional suspended shelf creates an alternate collectible route, not a mandatory jump.
            platforms.append(Platform(x=x+1, y=y-2, width=4, kind='bridge', route='optional'))
            if design.collectibles_enabled: entities.append(Entity(x=(x+3)*36, y=(y-2)*36-45, kind='crystal', platform=len(platforms)-1))
        x += length
    if design.moving_platforms and not any(p.moving for p in platforms):
        platforms.append(Platform(x=1,y=start_y-2,width=4,kind='bridge',moving=True,route='optional',motion=design.platform_motion))
    end = next(p for p in reversed(platforms) if not p.moving and p.route == 'main')
    entities.append(Entity(x=(end.x + end.width - 1) * 36, y=end.y * 36 - 36, kind="exit", platform=platforms.index(end)))
    count = sum(e.kind == "crystal" for e in entities)
    links, goals = compile_interactions(design, platforms, entities, level_id)
    ir = PlatformerIR(title=design.title, theme=design.theme, seed=seed, width=(x+2)*36, height=(start_y+5)*36,
        spawn={"x": 90, "y": start_y*36-28}, player=Player(abilities=design.abilities, health=5 if design.difficulty=="relaxed" else 3),
        slippery=design.slippery, exit_indicator=design.exit_indicator, exit_style=design.exit_style, collectible=design.collectible,
        difficulty=design.difficulty, topology=design.topology,
        links=links, goals=goals, player_attack=design.player_attack,
        camera_mode="vertical" if design.topology=="ascent" else "follow",
        objective={"type":design.objective,"required":math.ceil(sum(e.kind=='crystal' and platforms[e.platform].route=='main' for e in entities)*.6) if design.objective=="collect_and_exit" else 0,"total":count}, platforms=platforms, entities=entities)

    if design.level_count > 1 or design.levels:
        for stage, specification in enumerate(design.levels or progression_specs(design, prompt)):
            child = design.model_copy(deep=True)
            child.level_count = 1
            child.levels = []
            child.campaign_objectives = []
            for key, value in specification.model_dump(exclude_none=True).items():
                if key != 'briefing': setattr(child, key, getattr(specification,key))
            child.sections = [section.model_copy(deep=True) for section in specification.sections]
            level = construct(child, prompt, (seed + stage * 7919) % 4294967296, f'L{stage+1}')
            level.briefing = specification.briefing
            ir.levels.append(LevelIR.model_validate({k: getattr(level, k) for k in LevelIR.model_fields}))
        for field in LevelIR.model_fields:
            if field != 'title':
                setattr(ir, field, getattr(ir.levels[0], field))
    ir.campaign_goals = compile_goals(design.campaign_objectives, [e for level in (ir.levels or [ir]) for e in level.entities], 'campaign')
    ir.requirements = requirement_evidence(ir, prompt, design.unsupported, requested=design.requested_features)['requirements']
    return ir


def validate_route(ir: PlatformerIR) -> dict:
    if ir.levels:
        checks = []
        for index, level in enumerate(ir.levels):
            child = PlatformerIR.model_validate({**ir.model_dump(), **level.model_dump(exclude_none=True), 'levels': [], 'campaign_goals': []})
            report = validate_route(child)
            checks.extend([{**c, 'id': f"stage_{index+1}_{c['id']}"} for c in report['checks']])
        from types import SimpleNamespace
        checks.extend(validate_gameplay(SimpleNamespace(entities=[e for level in ir.levels for e in level.entities], goals=ir.campaign_goals, links=[])))
        return {'overall': 'PASS' if all(c['passed'] for c in checks) else 'FAIL', 'checks': checks}
    checks = validate_gameplay(ir)
    path = [p for p in ir.platforms if not p.moving and p.route == 'main']
    for i, (a, b) in enumerate(zip(path, path[1:])):
        rise = (a.y - b.y)*36
        disc = ir.player.jump**2 - 2*ir.player.gravity*rise
        flight = (ir.player.jump + math.sqrt(disc))/ir.player.gravity if disc >= 0 else 0
        # Include 18px launch and landing margins and 15% control safety margin.
        distance = (b.x-a.x-a.width)*36 + 36
        passed = disc >= 0 and distance <= ir.player.speed*flight*.85
        checks.append({"id":f"route_{i}_{i+1}","passed":passed,"category":"level_layout","critical":True,
                       "details":{"gap_with_margin":distance,"safe_range":round(ir.player.speed*flight*.85,1),"rise":rise}})
    checks.append({"id":"objective_consistent","passed":0 <= ir.objective['required'] <= sum(e.kind=='crystal' for e in ir.entities),"category":"specification","critical":True})
    checks.append({'id': 'objective_on_main_route', 'passed': ir.objective['required'] <= sum(e.kind == 'crystal' and 0 <= e.platform < len(ir.platforms) and ir.platforms[e.platform].route == 'main' for e in ir.entities), 'category': 'specification', 'critical': True})
    checks.append({'id': 'entry_exit', 'passed': bool(path) and path[0].x*36 <= ir.spawn['x'] <= (path[0].x+path[0].width)*36 and (bool(ir.boss) and len(ir.entities)==1 and ir.entities[0].boss is not None or not ir.boss and sum(e.kind == 'exit' for e in ir.entities) == 1 and any(e.kind == 'exit' and e.platform == ir.platforms.index(path[-1]) for e in ir.entities)), 'category': 'specification', 'critical': True})
    checks.append({'id': 'entity_supports', 'passed': all(0 <= e.platform < len(ir.platforms) and ir.platforms[e.platform].x*36 <= e.x <= (ir.platforms[e.platform].x+ir.platforms[e.platform].width)*36 for e in ir.entities), 'category': 'specification', 'critical': True})
    return {"overall":"PASS" if all(c['passed'] for c in checks) else "FAIL", "checks":checks,
            "scope":"Conservative ballistic route checks; does not certify gameplay difficulty or visual quality."}


def enforce_explicit_requirements(design: GameDesign, prompt: str) -> dict:
    """Capability guard after model interpretation; modifications are inspectable, not silent."""
    p = prompt.lower()
    if re.search(r'no (?:ordinary |regular )?collectibl|do not add.*collectible',p):
        design.collectibles_enabled=False
        design.objective='reach_exit'
    if re.search(r'\bboss\b',p) and re.search(r'duel|one.on.one|arena|exactly one',p):
        from schemas.platformer import BossEncounter
        design.boss=design.boss or BossEncounter()
        design.player_attack='projectile'
        design.level_count=1;design.levels=[]
        design.collectibles_enabled=False
        design.unsupported=[v for v in design.unsupported if 'boss' not in v.lower()]
        if 'sword' in p:
            note='Sword melee approximated by the available F/X projectile combat ability.'
            if note not in design.design_notes: design.design_notes.append(note)
    # Exclusions inside a level clause belong to that level's model specification.
    # Campaign-wide exclusions occur before the first scoped instruction.
    exclusions = re.split(r'\b(?:first|second|third|final|last)\s+(?:level|stage)\b', p, maxsplit=1)[0]
    changes = []
    for ability, phrases in [('double_jump', ('double jump', 'double-jump')), ('dash', ('dash',))]:
        excluded=any(prefix+phrase in p for phrase in phrases for prefix in ('no ','without '))
        if excluded and ability in design.abilities:
            design.abilities.remove(ability);changes.append({'field':'abilities','removed':ability,'reason':'Explicit user exclusion'})
        elif not excluded and any(re.search(r'\b'+re.escape(word)+r'\b',p) for word in phrases) and ability not in design.abilities:
            design.abilities.append(ability); changes.append({'field':'abilities','added':ability,'reason':'Explicit supported user requirement'})
    for field, words in [('enemies',('no enemies','without enemies','peaceful')),('hazards',('no hazards','without hazards','peaceful'))]:
        if any(word in exclusions for word in words):
            for i,section in enumerate(design.sections):
                if getattr(section,field):
                    setattr(section,field,False);changes.append({'field':f'sections.{i}.{field}','before':True,'after':False,'reason':'Explicit exclusion in prompt'})
    if 'no checkpoint' in exclusions and design.checkpoints:
        design.checkpoints=False;changes.append({'field':'checkpoints','before':True,'after':False,'reason':'Explicit exclusion'})
    excluded_moving=any(word in exclusions for word in ('no moving platform','without moving platform','no moving machinery','without moving machinery'))
    if excluded_moving and design.moving_platforms:
        design.moving_platforms=False;changes.append({'field':'moving_platforms','before':True,'after':False,'reason':'Explicit exclusion'})
    elif not excluded_moving and any(word in p for word in ('moving platform','moving machinery')) and not design.moving_platforms:
        design.moving_platforms=True;changes.append({'field':'moving_platforms','before':False,'after':True,'reason':'Explicit supported requirement'})
    features = {r['id'] for r in extract_requirements(prompt)}
    features.update(f.capability for f in design.requested_features if f.capability != 'unsupported')
    for feature in design.requested_features:
        if feature.capability == 'unsupported' and feature.description not in design.unsupported:
            design.unsupported.append(feature.description)
    overrides = {}
    if 'ice_environment' in features: overrides.update(theme='ice', topology='cavern')
    elif 'factory_environment' in features: overrides.update(theme='industrial', topology='terraces')
    elif 'forest_environment' in features: overrides.update(theme='forest')
    for key in ('slippery', 'falling_icicles', 'timed_hazards', 'moving_platforms'):
        if key in features: overrides[key] = True
    if requested_level_count(prompt): overrides['level_count'] = requested_level_count(prompt)
    if 'exit_indicator' in features:
        overrides['exit_indicator'] = 'flash' if any(w in p for w in ('flash', 'blink')) else 'pulse' if 'puls' in p else 'glow' if 'glow' in p else design.exit_indicator if design.exit_indicator != 'none' else 'pulse'
    interval=re.search(r'every\s+(\d+(?:\.\d+)?)\s*(?:seconds?|s\b)',p)
    if 'falling_icicles' in features and interval:
        milliseconds=round(float(interval.group(1))*1000)
        if 800 <= milliseconds <= 10000:
            overrides.update(icicle_trigger='timer',hazard_period_ms=milliseconds)
        else:
            limitation='Unsupported icicle interval '+interval.group()+': supported range is 0.8 to 10 seconds'
            if limitation not in design.unsupported: design.unsupported.append(limitation)
    if 'shrine' in p: overrides['exit_style'] = 'shrine'
    elif 'light' in p and 'exit' in p: overrides['exit_style'] = 'beacon'
    if 'collectibles' in features:
        overrides['objective'] = 'collect_and_exit'
        overrides['collectible'] = 'relics' if 'relic' in p else 'crystals'
    if 'checkpoints' in features: overrides['checkpoints'] = True
    for key, value in overrides.items():
        if getattr(design, key) != value:
            changes.append({'field': key, 'before': getattr(design, key), 'after': value, 'reason': 'Explicit requested capability'})
            setattr(design, key, value)
    if not any(w in exclusions for w in ('no enemies', 'without enemies', 'peaceful')):
        if features & {'patrol', 'robots', 'chase', 'ranged'}:
            for i, section in enumerate(design.sections):
                section.enemies = i % 2 == 1
                section.encounter = ('shooter' if 'ranged' in features else 'chase' if 'chase' in features else
                                     ('patrol', 'chase', 'shooter')[i % 3] if 'robots' in features else 'patrol')
    if any(w in exclusions for w in ('peaceful', 'no hazards', 'without hazards')):
        design.falling_icicles = False
        design.timed_hazards = False
    supported={'dash','double_jump','double jump','moving platforms','checkpoints'}
    incorrect=[value for value in design.unsupported if value.lower().strip() in supported]
    if incorrect:
        design.unsupported=[v for v in design.unsupported if v not in incorrect]
        changes.append({'field':'unsupported','removed':incorrect,'reason':'Registered capabilities incorrectly marked unsupported by model'})
    # These are recognized explicit future requests, not claims of comprehensive NLP coverage.
    for word in ('multiplayer','3d','rpg','dialogue','crafting','underwater'):
        if re.search(r'\b'+word+r'\b',p) and not any(word in v.lower() for v in design.unsupported):
            design.unsupported.append('Unsupported request: '+word)
    if design.levels and len(design.levels) != design.level_count:
        raise ValueError('Explicit level count does not match the planned level specifications')
    if not design.levels and design.level_count > 1:
        changes.extend(compose_intent(design, prompt))
        design.levels = progression_specs(design, prompt)
        changes.append({'field': 'levels', 'reason': 'Expanded campaign defaults into explicit progressive level specifications'})
    else:
        changes.extend(compose_intent(design, prompt))
    for path, owner in [('game',design), *[(f'levels.{index}',level) for index,level in enumerate(design.levels)]]:
        for index, interaction in enumerate(owner.interactions or []):
            if interaction.door_section == len(owner.sections):
                before = interaction.model_dump()
                interaction.door_section -= 1
                if interaction.section > 0: interaction.section -= 1
                changes.append({'field':f'{path}.interactions.{index}','before':before,'after':interaction.model_dump(),
                                'reason':'Converted out-of-range one-based interaction indices into existing zero-based sections; preserved trigger and door'})
    # Global exclusions apply to every explicit level. Positive requests stay scoped
    # to their specified levels rather than being forced onto the introductory stage.
    for index, level in enumerate(design.levels):
        for field, words in [('enemies', ('no enemies', 'without enemies', 'peaceful')), ('hazards', ('no hazards', 'without hazards', 'peaceful'))]:
            if any(word in exclusions for word in words):
                for section in level.sections: setattr(section, field, False)
                if field == 'hazards': level.falling_icicles = level.timed_hazards = False
        for field, excluded in [('checkpoints', 'no checkpoint' in exclusions), ('moving_platforms', excluded_moving)]:
            if excluded and getattr(level, field) is not False:
                setattr(level, field, False)
                changes.append({'field': f'levels.{index}.{field}', 'after': False, 'reason': 'Explicit exclusion'})
    return {'scope':'Explicit phrase extraction plus model-enumerated requests; subjective style requires human review.',
            'requirements':extract_requirements(prompt),'changes':changes,'unsupported':design.unsupported,'overall':'WARN' if design.unsupported else 'PASS'}


def validate_assets(manifest: dict, public_dir) -> dict:
    checks=[]
    for name,expected in manifest['files'].items():
        path=(public_dir/'assets/platformer'/name).resolve()
        valid=path.is_relative_to(public_dir.resolve()) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected
        checks.append({'id':name,'passed':valid,'category':'asset','critical':True})
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}
