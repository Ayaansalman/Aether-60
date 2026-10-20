"""Design interpretation, seeded construction and conservative ballistic route validation."""
import hashlib
import json
import math
import random
import re
from schemas.platformer import GameDesign, PlatformerIR, Platform, Player, Entity, Section


def fixture_design(prompt: str) -> GameDesign:
    """Deterministic offline provider, never presented as language-model output."""
    p = prompt.lower()
    industry = any(w in p for w in ("industrial", "robot", "factory", "machinery"))
    tower = any(w in p for w in ("tower", "climb", "precision"))
    calm = any(w in p for w in ("peaceful", "relaxed", "cozy", "easy", "no enemies"))
    theme = "industrial" if industry else "twilight" if tower else "forest"
    unsupported = [f"Unsupported request: {word}" for word in ("multiplayer", "3d", "rpg", "dialogue", "crafting", "boss", "underwater") if re.search(r"\b" + word + r"\b", p)]
    return GameDesign(
        title="The Copperworks" if industry else "Stairway to the Stars" if tower else "The Verdant Passage",
        premise=prompt[:500], theme=theme, difficulty="relaxed" if calm else "challenging" if tower else "balanced",
        abilities=[a for a, words in [("double_jump", ("double jump", "double-jump")), ("dash", ("dash",))] if any(w in p for w in words)],
        objective="collect_and_exit" if any(w in p for w in ("collect", "crystal", "gem")) else "reach_exit",
        checkpoints="no checkpoint" not in p, moving_platforms=any(w in p for w in ("moving", "machinery")),
        sections=[Section(kind="ascent" if tower else "factory" if industry else "ruins" if i % 3 == 2 else "meadow",
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
Supported: 2D side-scrolling platformer, forest/industrial/twilight art, crystals, patrol enemies,
spikes, checkpoints, double_jump, dash, optional moving platforms, reach_exit or collect_and_exit.
Put unsupported requested genres/mechanics in unsupported; never pretend they are implemented.
The unsupported array must include ONLY explicitly requested unavailable features. Leave it empty
when all requested features are supported; do not invent unrequested inventory, combat or other limitations.
Compose 5-14 varied sections. kind=meadow/ruins/factory/ascent/gauntlet, length=4..10 tiles,
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
            return design, {"provider": "openai_compat", "model": result.model, "live": True, "latency_ms": result.latency_ms, "fallbacks": result.fallback_events}
        except ValueError as exc:
            last = exc
    raise ValueError("Model returned an invalid design after two bounded attempts")


def construct(design: GameDesign, prompt: str, seed: int | None = None) -> PlatformerIR:
    seed = seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    # Leave enough vertical room for every requested ascent.
    start_y = max(14, 4 + sum(max(s.elevation, 0) for s in design.sections))
    platforms = [Platform(x=0, y=start_y, width=8, kind="meadow")]
    entities = []
    x, y = 8, start_y
    for i, section in enumerate(design.sections):
        x += section.gap
        y = max(5, min(start_y + 1, y - section.elevation))
        length = max(4, min(10, section.length + rng.choice([-1, 0, 1])))
        platform = Platform(x=x, y=y, width=length, kind=section.kind)
        platforms.append(platform)
        for offset in range(1, length - 1, 2):
            entities.append(Entity(x=(x + offset + .5) * 36, y=y * 36 - 64, kind="crystal", platform=i + 1))
        if section.enemies:
            entities.append(Entity(x=(x + length - 1.5) * 36, y=y * 36 - 22, kind="enemy", platform=i + 1))
        if section.hazards:
            entities.append(Entity(x=(x + length // 2 + .5) * 36, y=y * 36 - 10, kind="spikes", platform=i + 1))
        if design.checkpoints and i in (len(design.sections)//2 - 1,):
            entities.append(Entity(x=(x + .8) * 36, y=y * 36 - 30, kind="checkpoint", platform=i + 1))
        if design.moving_platforms and i % 2 == 0:
            # Optional elevated route; mandatory route is static and independently reachable.
            platforms.append(Platform(x=x + 1, y=y - 3, width=4, kind=section.kind, moving=True))
            # Entity references are corrected below using coordinates (optional platforms interleave).
        x += length
    for e in entities:
        e.platform = next(i for i, p in enumerate(platforms) if not p.moving and p.x * 36 <= e.x <= (p.x+p.width)*36 and abs(e.y-p.y*36) < 90)
    end = next(p for p in reversed(platforms) if not p.moving)
    entities.append(Entity(x=(end.x + end.width - 1) * 36, y=end.y * 36 - 36, kind="exit", platform=platforms.index(end)))
    count = sum(e.kind == "crystal" for e in entities)
    return PlatformerIR(title=design.title, theme=design.theme, seed=seed, width=(x+2)*36, height=(start_y+5)*36,
        spawn={"x": 90, "y": start_y*36-28}, player=Player(abilities=design.abilities, health=5 if design.difficulty=="relaxed" else 3),
        objective={"type":design.objective,"required":math.ceil(count*.6) if design.objective=="collect_and_exit" else 0,"total":count}, platforms=platforms, entities=entities)


def validate_route(ir: PlatformerIR) -> dict:
    checks = []
    path = [p for p in ir.platforms if not p.moving]
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
    supported={'dash','double_jump','double jump','moving platforms','checkpoints'}
    incorrect=[value for value in design.unsupported if value.lower().strip() in supported]
    if incorrect:
        design.unsupported=[v for v in design.unsupported if v not in incorrect]
        changes.append({'field':'unsupported','removed':incorrect,'reason':'Registered capabilities incorrectly marked unsupported by model'})
    # These are recognized explicit future requests, not claims of comprehensive NLP coverage.
    for word in ('multiplayer','3d','rpg','dialogue','crafting','boss','underwater'):
        if re.search(r'\b'+word+r'\b',p) and not any(word in v.lower() for v in design.unsupported):
            design.unsupported.append('Unsupported request: '+word)
    return {'scope':'Explicit supported requirements and recognized exclusions; semantic fidelity still requires review.',
            'changes':changes,'unsupported':design.unsupported,'overall':'WARN' if design.unsupported else 'PASS'}


def validate_assets(manifest: dict, public_dir) -> dict:
    checks=[]
    for name,expected in manifest['files'].items():
        path=(public_dir/'assets/platformer'/name).resolve()
        valid=path.is_relative_to(public_dir.resolve()) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected
        checks.append({'id':name,'passed':valid,'category':'asset','critical':True})
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}
