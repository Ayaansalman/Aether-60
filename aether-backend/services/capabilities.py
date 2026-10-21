"""Inspectable requirements with source phrases, construction witnesses and runtime checks.

This is a bounded explicit-phrase extractor, not a claim of complete NLP understanding.
The model's unsupported list is retained for requests outside this vocabulary.
"""
import re

FEATURES = {
    'boss_duel': (r'\bboss\b', 'boss_duel'),
    'ice_environment': (r'\bice\b|frozen', 'ice_composition'),
    'forest_environment': (r'forest', 'environment_composition'),
    'factory_environment': (r'industrial|factory', 'environment_composition'),
    'slippery': (r'slippery|sliding terrain', 'slippery_momentum'),
    'falling_icicles': (r'falling icicles?|icicle hazards?|falling (?:ice )?hazards?', 'falling_icicle_cycle'),
    'exit_indicator': (r'flashing light|flashing.*exit|pulsing.*exit|glowing shrine|glowing.*exit', 'exit_indicator_animation'),
    'collectibles': (r'collectible|collect.*crystal|collect.*relic', 'collectible_overlap'),
    'patrol': (r'patrolling|patrol', 'enemy_patrol'),
    'robots': (r'robotic enemies|robot enemies|robots', 'enemy_behaviors'),
    'chase': (r'chasing|chase', 'enemy_chase'),
    'ranged': (r'ranged|shooting|shooters?', 'enemy_shooter'),
    'moving_platforms': (r'moving platforms?|moving machinery', 'moving_platform_motion'),
    'timed_hazards': (r'dangerous machinery|timed hazards?', 'timed_hazard_cycle'),
    'checkpoints': (r'checkpoints?', 'checkpoint_respawn'),
    'multiple_levels': (r'(?:multiple|multi|three|two|2|3)[ -]+(?:(?:connected|ice|forest|industrial|twilight|platformer)[ -]+)*(?:levels?|stages?)', 'level_transitions'),
    'double_jump': (r'double[ -]jump', 'double_jump'),
    'dash': (r'\bdash\b', 'dash'),
    'switches': (r'\bswitch(?:es)?\b', 'switch_door'),
    'pressure_plates': (r'pressure plates?', 'pressure_plate'),
    'projectile_switches': (r'(?:shoot|projectile).*switch|switch.*(?:shoot|projectile)', 'projectile_switch'),
    'combat_objective': (r'\b(?:defeat|kill|eliminate)\b.*\b(?:enemies|creatures|guards|monsters|turrets?|ambushers?)\b', 'combat_objective'),
    'timed_objective': (r'(?:within|under)\s+\d+\s*seconds?', 'timed_objective'),
    'survival_objective': (r'survive(?: for)?\s+\d+\s*seconds?', 'survival_objective'),
    'turret': (r'\bturrets?\b', 'enemy_turret'),
    'ambusher': (r'ambush|proximity.triggered attack', 'enemy_ambusher'),
    'player_projectiles': (r'player.*(?:shoot|projectile)|blaster|fireballs?|shoot.*(?:enemies|creatures)', 'player_projectile'),
}


def extract_requirements(prompt):
    result = []
    for feature, (pattern, check) in FEATURES.items():
        match = re.search(pattern, prompt, re.I)
        if not match:
            continue
        clause=re.split(r'[.!;]',prompt[:match.start()])[-1].lower()
        if feature=='collectibles' and re.search(r'do not add|\bno\b|without',clause): continue
        prefix = prompt[max(0, match.start()-12):match.start()].lower()
        if re.search(r'(no|without)\s*$', prefix):
            continue
        result.append({'id': feature, 'source': match.group(), 'span': [match.start(), match.end()],
                       'supported': True, 'status': 'pending', 'runtime_check': check})
    return result


def requirement_evidence(ir, prompt, unsupported=(), qa=None, requested=()):
    levels = ir.levels or [ir]
    entities = [e for level in levels for e in level.entities]
    platforms = [p for level in levels for p in level.platforms]
    goals = [goal for level in levels for goal in level.goals] + ir.campaign_goals
    witnesses = {
        'boss_duel': bool(ir.boss) and sum(e.boss is not None for e in entities)==1 and len(entities)==1,
        'ice_environment': any((level.theme or ir.theme) == 'ice' for level in levels), 'forest_environment': any((level.theme or ir.theme) == 'forest' for level in levels),
        'factory_environment': any((level.theme or ir.theme) == 'industrial' for level in levels), 'slippery': any(level.slippery if level.slippery is not None else ir.slippery for level in levels),
        'falling_icicles': any(e.kind == 'icicle' for e in entities),
        'exit_indicator': any((level.exit_indicator or ir.exit_indicator) != 'none' for level in levels), 'collectibles': any(e.kind == 'crystal' for e in entities),
        'robots': any((level.theme or ir.theme) == 'industrial' and any(e.kind == 'enemy' for e in level.entities) for level in levels),
        'moving_platforms': any(p.moving for p in platforms),
        'timed_hazards': any(e.kind == 'timed_hazard' for e in entities),
        'checkpoints': any(e.kind == 'checkpoint' for e in entities), 'multiple_levels': len(levels) > 1,
        'switches': any(e.kind=='switch' for e in entities) and any(level.links for level in levels),
        'pressure_plates': any(e.kind=='pressure_plate' for e in entities),
        'projectile_switches': any(e.kind=='switch' and e.activation=='projectile' for e in entities) and any(level.player_attack=='projectile' for level in levels),
        'combat_objective': any(goal.kind=='defeat' for goal in goals),
        'timed_objective': any(goal.kind=='time_limit' for goal in goals),
        'survival_objective': any(goal.kind=='survive' for goal in goals),
        'player_projectiles': any(level.player_attack=='projectile' for level in levels),
        **{name: any(e.kind == 'enemy' and e.behavior == behavior for e in entities)
           for name, behavior in [('patrol', 'patrol'), ('chase', 'chase'), ('ranged', 'shooter'), ('turret','turret'), ('ambusher','ambusher')]},
        **{ability: ability in ir.player.abilities for ability in ['double_jump', 'dash']},
    }
    checks = {}
    for check in (qa or {}).get('checks', []):
        prior = checks.get(check['id'])
        checks[check['id']] = {**check, 'passed': check['passed'] and (prior is None or prior['passed'])}
    requirements = extract_requirements(prompt)
    # Retain model-enumerated requests across construction, polling and re-verification.
    prior = [dict(r) for r in ir.requirements if r.get('id') != 'unsupported']
    prior.extend({'id': f.capability, 'source': f.source, 'description': f.description,
                  'supported': f.capability != 'unsupported',
                  'runtime_check': FEATURES.get(f.capability, ('', None))[1]}
                 for f in requested if f.capability != 'unsupported')
    for requirement in prior:
        existing = next((r for r in requirements if r['id'] == requirement['id']), None)
        if existing is None:
            requirements.append(requirement)
        else:
            sources = existing.setdefault('model_sources', [])
            for source in [requirement['source'], *requirement.get('model_sources', [])]:
                if source.lower() != existing['source'].lower() and source not in sources:
                    sources.append(source)
    for req in requirements:
        built = bool(witnesses.get(req['id']))
        check = checks.get(req['runtime_check'])
        if check is None and req['runtime_check']=='switch_door':
            check=checks.get('projectile_switch')  # A physically opened projectile-linked door also verifies a switch/door interaction.
        req.update(constructed=built, verified=bool(built and check and check['passed']),
                   status='construction_failed' if not built else 'verification_failed' if check and not check['passed']
                   else 'implemented_verified' if check else 'implemented_unverified',
                   evidence={'spec': req['id'], 'qa': check['id'] if check else None})
    for value in unsupported:
        requirements.append({'id': 'unsupported', 'source': value, 'supported': False, 'status': 'unsupported', 'verified': False})
    return {'requirements': requirements, 'overall': 'FAIL' if any(r['status'] in ('construction_failed', 'verification_failed') for r in requirements)
            else 'WARN' if any(not r.get('verified') for r in requirements) else 'PASS',
            'scope': 'Explicit phrase extraction plus model-reported unsupported requests. Construction and runtime verification are separate; unrecognized wording can require review.'}
