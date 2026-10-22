"""Bounded intent composition and compilation of registered gameplay components."""
import re
from schemas.platformer import Entity, Goal, GoalDesign, InteractionDesign, BehaviorLink

TARGET_KINDS = {'defeat': {'enemy'}, 'activate': {'switch', 'pressure_plate'},
                'unlock': {'door'}, 'collect': {'crystal'}}


def compose_intent(design, prompt):
    """Explicit keyword guard; model-authored per-level selections remain authoritative."""
    p = prompt.lower()
    before = design.model_dump()
    def requested(pattern):
        return any(not re.search(r'(?:no|without)\s*$',p[max(0,match.start()-12):match.start()]) for match in re.finditer(pattern,p))
    peaceful = any(word in p for word in ('peaceful', 'no enemies', 'without enemies'))
    combat = bool(re.search(r'\b(defeat|kill|eliminate)\b.*\b(enemies|creatures|guards|monsters|turrets?|ambushers?)\b', p))
    def add_goal(kind, seconds=30):
        if not any(goal.kind == kind for goal in design.objectives):
            design.objectives.append(GoalDesign(kind=kind, seconds=seconds))
    if combat and not peaceful:
        add_goal('defeat')
        selected=re.search(r'(?:defeat|kill|eliminate)\s+(?:only\s+|the\s+)?(turrets?|ambushers?|shooters?)\b',p)
        if selected:
            for goal in design.objectives:
                if goal.kind=='defeat': goal.enemy_behavior=selected.group(1).rstrip('s')
        for i, section in enumerate(design.sections):
            section.enemies = i > 0 and i % 2 == 1
            section.challenge = 'combat' if section.enemies else 'traversal'
            if section.enemies and section.encounter == 'patrol': section.encounter = 'chase'
    if requested(r'\b(?:switch(?:es)?|pressure plates?)\b'):
        triggers = []
        if requested(r'\bpressure plates?\b'): triggers.append('pressure')
        if requested(r'\bswitch(?:es)?\b'):
            triggers.append('projectile' if re.search(r'(shoot|projectile).*switch|switch.*(shoot|projectile)', p) else 'proximity' if 'proximity' in p else 'interact')
        if not design.interactions:
            design.interactions = [InteractionDesign(trigger=trigger, section=i, door_section=i+2) for i, trigger in enumerate(triggers)]
        if not re.search(r'enemies|creatures|monsters|robots|guards|patrol|chase|ranged|turret|ambush',p):
            for section in design.sections: section.enemies = False
        add_goal('activate'); add_goal('unlock')
    if any(item.trigger == 'projectile' for item in design.interactions) or re.search(r'player.*(?:shoot|projectile)|(?:blaster|fireballs?)|shoot.*(?:enemies|creatures)', p):
        design.player_attack = 'projectile'
    requested_behaviors = [behavior for behavior, pattern in [('shooter', r'\branged\b|shooters?'), ('turret', r'\bturrets?\b'), ('ambusher', r'ambush|proximity.triggered attack'), ('chase',r'\bchase\b|chasing')]
                 if requested(pattern)]
    if requested_behaviors and not peaceful:
        for i, section in enumerate(design.sections):
            if i % 2 == 1: section.enemies = True; section.encounter = requested_behaviors[(i//2)%len(requested_behaviors)]
    for kind, pattern in [('survive', r'survive(?: for)?\s+(\d+)\s*seconds?'), ('time_limit', r'(?:within|under)\s+(\d+)\s*seconds?')]:
        match = re.search(pattern, p)
        if match:
            seconds = int(match.group(1))
            if 1 <= seconds <= 180: add_goal(kind, seconds)
            elif 'Unsupported duration: '+match.group() not in design.unsupported:
                design.unsupported.append('Unsupported duration: '+match.group()+'; supported range is 1–180 seconds')
    if re.search(r'(?:vertical|elevator).*platform|platform.*(?:vertical|elevator)', p):
        design.moving_platforms = True
        design.platform_motion.axis = 'vertical'
    if 'ping-pong' in p: design.platform_motion.pattern = 'ping_pong'
    return [] if before == design.model_dump() else [{'field': 'gameplay', 'before': {key:before[key] for key in ('objectives','interactions','player_attack')},
              'after': {key:design.model_dump()[key] for key in ('objectives','interactions','player_attack')}, 'reason':'Explicit gameplay requirements composed into registered components'}]


def compile_goals(specifications, entities, prefix):
    goals = []
    for index, specification in enumerate(specifications):
        targets = [e.id for e in entities if e.kind in TARGET_KINDS.get(specification.kind, set()) and
                   (specification.enemy_behavior is None or e.behavior==specification.enemy_behavior)]
        if specification.kind in TARGET_KINDS and (not targets or specification.count > len(targets)):
            raise ValueError(f'Unachievable {specification.kind} objective: insufficient matching targets')
        goals.append(Goal(**specification.model_dump(), id=f'{prefix}_goal_{index}', targets=targets))
    return goals


def compile_interactions(design, platforms, entities, prefix):
    for index, entity in enumerate(entities): entity.id = f'{prefix}_{entity.kind}_{index}'
    route = [p for p in platforms if not p.moving and p.route == 'main'][1:]
    links = []
    gates = {}
    for index, interaction in enumerate(design.interactions):
        if not 0 <= interaction.section < interaction.door_section < len(route):
            raise ValueError('Switch must precede its door on existing level sections')
        if interaction.trigger == 'projectile' and design.player_attack != 'projectile':
            raise ValueError('Projectile switches require the player projectile attack')
        source, target = route[interaction.section], route[interaction.door_section]
        switch_id = f'{prefix}_trigger_{index}'
        gate_key = ('named',interaction.gate) if interaction.gate else ('isolated',index)
        entities.append(Entity(id=switch_id, kind='pressure_plate' if interaction.trigger == 'pressure' else 'switch',
                   activation=interaction.trigger, x=(source.x+(2.1 if interaction.trigger=='projectile' else 1.1))*36, y=source.y*36-(6 if interaction.trigger == 'pressure' else 24), platform=platforms.index(source)))
        if interaction.enable_platforms:
            targets=[p for p in platforms if p.moving]
            if not targets:raise ValueError('Switch activation needs existing moving platforms')
            for platform in targets:platform.activation_sources.append(switch_id)
        if interaction.disable_hazards:
            targets=[e for e in entities if e.kind=='timed_hazard']
            if not targets:raise ValueError('Switch deactivation needs existing timed machinery hazards')
            for hazard in targets:hazard.disabled_by.append(switch_id)
        if gate_key in gates:
            link, section = gates[gate_key]
            if section != interaction.door_section:raise ValueError('Shared gate switches must reference the same door section')
            link.sources.append(switch_id)
        else:
            door_id=f'{prefix}_door_{index}'
            entities.append(Entity(id=door_id, kind='door', x=(target.x+target.width-1.5)*36, y=target.y*36-90, platform=platforms.index(target)))
            link=BehaviorLink(sources=[switch_id],target=door_id)
            gates[gate_key]=(link,interaction.door_section);links.append(link)
    goals = compile_goals(design.objectives, entities, prefix)
    # Physical doors also gate the exit, preventing an optional route from bypassing the puzzle.
    if links and not any(goal.kind == 'unlock' for goal in goals):
        goals.extend(compile_goals([GoalDesign(kind='unlock')], entities, prefix+'_doors'))
    return links, goals


def validate_gameplay(level):
    """Reference and supply checks complement, rather than replace, ballistic validation."""
    entities = {e.id:e for e in level.entities if e.id}
    checks = []
    for goal in level.goals:
        target_kind = TARGET_KINDS.get(goal.kind)
        valid = not target_kind or bool(goal.targets) and all(target in entities and entities[target].kind in target_kind for target in goal.targets) and goal.count <= len(set(goal.targets))
        checks.append({'id':'goal_'+goal.id, 'passed':bool(valid),'category':'specification','critical':True})
    for link in level.links:
        valid = all(entities[source].platform <= entities[link.target].platform for source in link.sources)
        checks.append({'id':'link_'+link.target,'passed':valid,'category':'specification','critical':True})
    deadlines = [goal.seconds for goal in level.goals if goal.kind=='time_limit']
    waits = [goal.seconds for goal in level.goals if goal.kind=='survive']
    if deadlines:
        checks.append({'id':'compatible_timers','passed':not waits or max(waits)<min(deadlines),'category':'specification','critical':True})
        if hasattr(level,'platforms') and hasattr(level,'player'):
            route=[p for p in level.platforms if not p.moving and p.route=='main']
            distance=max(0,(route[-1].x-route[0].x)*36) if route else 0
            checks.append({'id':'deadline_travel_budget','passed':min(deadlines)>=distance/level.player.speed,'category':'specification','critical':True})
    return checks
