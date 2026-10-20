"""Design interpretation, seeded construction and conservative ballistic route validation."""
import hashlib
import json
import math
import random
import re
from schemas.platformer import GameDesign, PlatformerIR, LevelIR, Platform, Player, Entity, Section
from services.capabilities import extract_requirements, requirement_evidence


def fixture_design(prompt: str) -> GameDesign:
    """Deterministic offline provider, never presented as language-model output."""
    p = prompt.lower()
    industry = any(w in p for w in ("industrial", "robot", "factory", "machinery"))
    tower = any(w in p for w in ("tower", "climb", "precision"))
    calm = any(w in p for w in ("peaceful", "relaxed", "cozy", "easy", "no enemies"))
    ice = any(w in p for w in ("frozen", "ice", "icicle"))
    theme = "industrial" if industry else "ice" if ice else "twilight" if tower else "forest"
    unsupported = [f"Unsupported request: {word}" for word in ("multiplayer", "3d", "rpg", "dialogue", "crafting", "boss", "underwater") if re.search(r"\b" + word + r"\b", p)]
    return GameDesign(
        title="The Copperworks" if industry else "The Frostbound Vault" if ice else "Stairway to the Stars" if tower else "The Verdant Passage",
        topology="ascent" if tower else "terraces" if industry else "cavern" if ice else "journey",
        slippery="slippery" in p, falling_icicles="icicle" in p,
        timed_hazards=industry and not calm,
        exit_indicator="flash" if "flashing" in p else "glow" if "glowing" in p else "none",
        collectible="relics" if "relic" in p else "crystals",
        level_count=3 if "multiple" in p else 1,
        premise=prompt[:500], theme=theme, difficulty="relaxed" if calm else "challenging" if tower else "balanced",
        abilities=[a for a, words in [("double_jump", ("double jump", "double-jump")), ("dash", ("dash",))] if any(w in p for w in words)],
        objective="collect_and_exit" if any(w in p for w in ("collect", "crystal", "gem")) else "reach_exit",
        checkpoints="no checkpoint" not in p, moving_platforms=any(w in p for w in ("moving", "machinery")),
        sections=[Section(kind="ascent" if tower else "terraces" if industry else "cavern" if ice else "ruins" if i % 3 == 2 else "meadow",
                          encounter=("patrol", "chase", "shooter")[i % 3] if industry else "patrol",
                          length=5 + i % 3, elevation=2 if tower else i % 3 - 1,
                          gap=1 if calm else 2 + (i % 2 if tower else 0), enemies=not calm and i % 3 == 1,
                          hazards=not calm and i % 3 == 2) for i in range(9 if tower else 8)],
        unsupported=unsupported, design_notes=["Offline fixture: keyword interpretation and seeded construction; no model was called."])


def plan(prompt: str, mode: str):
    if mode == "fixture":
        return fixture_design(prompt), {"provider": "fixture", "model": None, "live": False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider = get_provider()
    if isinstance(provider, MockModelProvider):
        raise ValueError("Live mode requires MODEL_PROVIDER=openai_compat and a configured API key. Use the explicitly labeled fixture mode for offline work.")
    system = """You are Aether's platformer game designer. Interpret the user's requirements faithfully.
Return ONLY a JSON object matching the following schema. No executable code.
Supported: platformer; forest/industrial/twilight/ice environments; crystals or relics;
patrol, chase and shooter enemies (section.encounter); proximity or timed falling icicles; slippery
terrain; timed machinery; checkpoints; double_jump; dash; moving platforms; exit_indicator
none/glow/pulse/flash and exit_style shrine/gate/beacon; 1-3 connected levels. Choose topology journey/ascent/terraces/cavern.
Set falling_icicles/slippery/timed_hazards/level_count/collectible explicitly to match requests.
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
GameDesign JSON Schema:\n""" + json.dumps(GameDesign.model_json_schema())
    last = None
    for attempt in range(2):
        result = provider.complete(system, prompt if attempt == 0 else prompt + "\nCorrect your previous invalid response: " + str(last)[:1000])
        try:
            content = result.text.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
            design = GameDesign.model_validate_json(content)
            if any(feature.source.lower() not in prompt.lower() for feature in design.requested_features):
                raise ValueError('Requested feature source must quote the original prompt')
            return design, {"provider": "openai_compat", "model": result.model, "live": True, "latency_ms": result.latency_ms, "fallbacks": result.fallback_events}
        except ValueError as exc:
            last = exc
    raise ValueError("Model returned an invalid design after two bounded attempts")


def construct(design: GameDesign, prompt: str, seed: int | None = None) -> PlatformerIR:
    seed = seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    # Leave enough vertical room for every requested ascent.
    start_y = max(14, 4 + (2 * len(design.sections) if design.topology == 'ascent' else sum(max(s.elevation, 0) for s in design.sections)))
    platforms = [Platform(x=0, y=start_y, width=8, kind=design.topology)]
    entities = []
    x, y = 8, start_y
    for i, section in enumerate(design.sections):
        x += section.gap
        rise = section.elevation
        if design.topology == "ascent":
            rise = max(1, section.elevation)
        elif design.topology == "terraces":
            rise = (1, 2, -1, 1, -1)[i % 5]
        elif design.topology == "cavern":
            rise = (-1, 1, 0, 2, -1)[i % 5]
        y = max(5, min(start_y + 2, y - rise))
        length = max(4, min(10, section.length + rng.choice([-1, 0, 1])))
        platform = Platform(x=x, y=y, width=length, kind=section.kind)
        platforms.append(platform)
        offsets = range(1, length - 1, 2) if section.kind not in ('bridge', 'gauntlet') else [length // 2]
        for offset in offsets:
            lift = 20 * (1 - abs(offset - length/2) / (length/2)) if design.topology == 'journey' else (offset % 3)*10
            entities.append(Entity(x=(x + offset + .5) * 36, y=y * 36 - 56 - lift, kind="crystal", platform=i + 1))
        if section.enemies:
            entities.append(Entity(x=(x + length - 1.5) * 36, y=y * 36 - 22, kind="enemy", platform=i + 1, behavior=section.encounter))
        if design.falling_icicles and i % 2 == 1:
            trigger = ('proximity' if i % 4 == 1 else 'timer') if design.icicle_trigger == 'mixed' else design.icicle_trigger
            entities.append(Entity(x=(x + length * .65) * 36, y=y * 36 - 220, kind="icicle", platform=len(platforms)-1, trigger=trigger, period_ms=design.hazard_period_ms))
        if design.timed_hazards and i % 3 == 2:
            entities.append(Entity(x=(x + length * .65) * 36, y=y*36 - 16, kind="timed_hazard", platform=len(platforms)-1, period_ms=design.hazard_period_ms))
        if section.hazards and not design.falling_icicles and not design.timed_hazards:
            entities.append(Entity(x=(x + length // 2 + .5) * 36, y=y * 36 - 10, kind="spikes", platform=i + 1))
        if design.checkpoints and i in (len(design.sections)//2 - 1,):
            entities.append(Entity(x=(x + .8) * 36, y=y * 36 - 30, kind="checkpoint", platform=i + 1))
        if design.moving_platforms and i % 2 == 0:
            # Optional elevated route; mandatory route is static and independently reachable.
            platforms.append(Platform(x=x + 1, y=y - 3, width=4, kind=section.kind, moving=True))
            # Entity references are corrected below using coordinates (optional platforms interleave).
        if section.kind in ('ruins', 'terraces') and i % 3 == 2 and not (design.moving_platforms and i % 2 == 0):
            # An optional suspended shelf creates an alternate collectible route, not a mandatory jump.
            platforms.append(Platform(x=x+1, y=y-3, width=4, kind='bridge', route='optional'))
            entities.append(Entity(x=(x+3)*36, y=(y-3)*36-45, kind='crystal', platform=len(platforms)-1))
        x += length
    for e in entities:
        e.platform = next(i for i, p in enumerate(platforms) if not p.moving and p.x * 36 <= e.x <= (p.x+p.width)*36 and abs(e.y-p.y*36) < (250 if e.kind == "icicle" else 90))
    end = next(p for p in reversed(platforms) if not p.moving and p.route == 'main')
    entities.append(Entity(x=(end.x + end.width - 1) * 36, y=end.y * 36 - 36, kind="exit", platform=platforms.index(end)))
    count = sum(e.kind == "crystal" for e in entities)
    ir = PlatformerIR(title=design.title, theme=design.theme, seed=seed, width=(x+2)*36, height=(start_y+5)*36,
        spawn={"x": 90, "y": start_y*36-28}, player=Player(abilities=design.abilities, health=5 if design.difficulty=="relaxed" else 3),
        slippery=design.slippery, exit_indicator=design.exit_indicator, exit_style=design.exit_style, collectible=design.collectible,
        camera_mode="vertical" if design.topology=="ascent" else "follow",
        objective={"type":design.objective,"required":math.ceil(count*.6) if design.objective=="collect_and_exit" else 0,"total":count}, platforms=platforms, entities=entities)

    if design.level_count > 1:
        for stage in range(design.level_count):
            child = design.model_copy(deep=True)
            child.level_count = 1
            child.title = f"{design.title} · Stage {stage + 1}"
            child.topology = [design.topology, "ascent", "terraces"][stage]
            child.sections = child.sections[:5 + stage]
            for j, section in enumerate(child.sections):
                section.enemies = section.enemies or (any(s.enemies for s in design.sections) and stage > 0 and j % 2 == 1)
                if stage > 0:
                    section.encounter = ["patrol", "chase", "shooter"][(stage+j) % 3]
            level = construct(child, prompt, (seed + stage * 7919) % 4294967296)
            ir.levels.append(LevelIR.model_validate({k: getattr(level, k) for k in LevelIR.model_fields}))
        for field in LevelIR.model_fields:
            if field != 'title':
                setattr(ir, field, getattr(ir.levels[0], field))
    ir.requirements = requirement_evidence(ir, prompt, design.unsupported, requested=design.requested_features)['requirements']
    return ir


def validate_route(ir: PlatformerIR) -> dict:
    if ir.levels:
        checks = []
        for index, level in enumerate(ir.levels):
            child = PlatformerIR.model_validate({**ir.model_dump(), **level.model_dump(), 'levels': []})
            report = validate_route(child)
            checks.extend([{**c, 'id': f"stage_{index+1}_{c['id']}"} for c in report['checks']])
        return {'overall': 'PASS' if all(c['passed'] for c in checks) else 'FAIL', 'checks': checks}
    checks = []
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
    return {"overall":"PASS" if all(c['passed'] for c in checks) else "FAIL", "checks":checks,
            "scope":"Conservative ballistic route checks; does not certify gameplay difficulty or visual quality."}


def enforce_explicit_requirements(design: GameDesign, prompt: str) -> dict:
    """Capability guard after model interpretation; modifications are inspectable, not silent."""
    p = prompt.lower()
    changes = []
    for ability, phrases in [('double_jump', ('double jump', 'double-jump')), ('dash', ('dash',))]:
        excluded=any(prefix+phrase in p for phrase in phrases for prefix in ('no ','without '))
        if excluded and ability in design.abilities:
            design.abilities.remove(ability);changes.append({'field':'abilities','removed':ability,'reason':'Explicit user exclusion'})
        elif not excluded and any(re.search(r'\b'+re.escape(word)+r'\b',p) for word in phrases) and ability not in design.abilities:
            design.abilities.append(ability); changes.append({'field':'abilities','added':ability,'reason':'Explicit supported user requirement'})
    for field, words in [('enemies',('no enemies','without enemies','peaceful')),('hazards',('no hazards','without hazards','peaceful'))]:
        if any(word in p for word in words):
            for i,section in enumerate(design.sections):
                if getattr(section,field):
                    setattr(section,field,False);changes.append({'field':f'sections.{i}.{field}','before':True,'after':False,'reason':'Explicit exclusion in prompt'})
    if 'no checkpoint' in p and design.checkpoints:
        design.checkpoints=False;changes.append({'field':'checkpoints','before':True,'after':False,'reason':'Explicit exclusion'})
    excluded_moving=any(word in p for word in ('no moving platform','without moving platform','no moving machinery','without moving machinery'))
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
    if 'multiple_levels' in features: overrides['level_count'] = 3 if 'three' in p or 'multiple' in p else 2
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
    if not any(w in p for w in ('no enemies', 'without enemies', 'peaceful')):
        if features & {'patrol', 'robots', 'chase', 'ranged'}:
            for i, section in enumerate(design.sections):
                section.enemies = i % 2 == 1
                section.encounter = ('shooter' if 'ranged' in features else 'chase' if 'chase' in features else
                                     ('patrol', 'chase', 'shooter')[i % 3] if 'robots' in features else 'patrol')
    if any(w in p for w in ('peaceful', 'no hazards', 'without hazards')):
        design.falling_icicles = False
        design.timed_hazards = False
    supported={'dash','double_jump','double jump','moving platforms','checkpoints'}
    incorrect=[value for value in design.unsupported if value.lower().strip() in supported]
    if incorrect:
        design.unsupported=[v for v in design.unsupported if v not in incorrect]
        changes.append({'field':'unsupported','removed':incorrect,'reason':'Registered capabilities incorrectly marked unsupported by model'})
    # These are recognized explicit future requests, not claims of comprehensive NLP coverage.
    for word in ('multiplayer','3d','rpg','dialogue','crafting','boss','underwater'):
        if re.search(r'\b'+word+r'\b',p) and not any(word in v.lower() for v in design.unsupported):
            design.unsupported.append('Unsupported request: '+word)
    return {'scope':'Explicit phrase extraction plus model-enumerated requests; subjective style requires human review.',
            'requirements':extract_requirements(prompt),'changes':changes,'unsupported':design.unsupported,'overall':'WARN' if design.unsupported else 'PASS'}


def validate_assets(manifest: dict, public_dir) -> dict:
    checks=[]
    for name,expected in manifest['files'].items():
        path=(public_dir/'assets/platformer'/name).resolve()
        valid=path.is_relative_to(public_dir.resolve()) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected
        checks.append({'id':name,'passed':valid,'category':'asset','critical':True})
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}
