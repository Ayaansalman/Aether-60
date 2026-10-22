"""Bounded local corrections for the existing linear traversal contracts.

No entities or objectives are removed. Every changed field carries its invariant.
World geometry and runtime links are checked separately after construction.
"""
from copy import deepcopy


def repair_dependencies(raw):
    data = deepcopy(raw)
    changes = []
    for path, owner in [('game', data), *[(f'levels.{i}', level) for i, level in enumerate(data.get('levels', []))]]:
        sections = owner.get('sections', [])
        interactions = owner.get('interactions')
        if interactions is None:
            interactions = deepcopy(data.get('interactions', []))
            if path != 'game' and interactions:
                owner['interactions'] = interactions
        if not interactions or len(sections) < 2:
            continue
        # Repair each shared gate as one relationship, rather than independently
        # moving its door once per source. Preserve distinct switch identities.
        groups = {}
        for i, item in enumerate(interactions):
            groups.setdefault(item.get('gate') or f'isolated-{i}', []).append((i, item))
        for group in groups.values():
            door = max(min(max(item.get('door_section', 1), 1), len(sections)-1) for _, item in group)
            for i, item in group:
                before = deepcopy(item)
                item['door_section'] = door
                if before.get('door_section') == len(sections) and item.get('section',0)>0:
                    item['section'] -= 1
                item['section'] = min(max(item.get('section', 0), 0), door-1)
                if item != before:
                    changes.append(dict(field=f'{path}.interactions.{i}', before=before, after=deepcopy(item),
                        invariant='0 <= switch.section < shared door.section < section count',
                        reason='Corrected one-based section indices' if before.get('door_section')==len(sections) else 'Relocated prerequisite before its gate on the forward traversal route'))
        # A source for a later door can also be trapped behind an earlier door
        # whose source is farther ahead. Symbolically walk the actual linear route.
        activated = set()
        for section in range(len(sections)):
            for i, item in enumerate(interactions):
                if item['section'] == section:
                    activated.add(i)
            for group in groups.values():
                if group[0][1]['door_section'] != section:
                    continue
                for i, item in group:
                    if i not in activated:
                        before = deepcopy(item)
                        item['section'] = max(0, section-1)
                        activated.add(i)
                        changes.append(dict(field=f'{path}.interactions.{i}', before=before, after=deepcopy(item),
                            invariant='All mandatory door sources reachable before crossing the first blocked gate',
                            reason='Removed a cross-gate dependency cycle'))
    return data, changes


def repair_quest_order(raw):
    """Stable topological order within an area; revisiting remains valid there.

    Actors and resources are unchanged. Cross-area returns remain the existing
    world's responsibility; missing resources and cycles remain hard errors.
    """
    data=deepcopy(raw);goals=data.get('quests',[]);actors={a['id']:a for a in data.get('actors',[])}
    dependencies={i:set() for i in range(len(goals))}
    for i,q in enumerate(goals):
        actor=actors.get(q.get('target'),{})
        needs=actor.get('requires',[]) if q.get('kind')=='unlock' else list((q.get('delivery_items') or {q.get('item',''):q.get('count',1)}).keys()) if q.get('kind')=='deliver' else []
        for ref in needs:
            for j,earlier in enumerate(goals):
                provider=actors.get(earlier.get('target'),{})
                if provider.get('area',0)!=actor.get('area',0):continue
                if (earlier.get('kind')=='activate' and provider.get('id')==ref) or (earlier.get('kind')=='collect' and provider.get('item')==ref):dependencies[i].add(j)
    order=[];pending=set(dependencies)
    while pending:
        ready=[i for i in sorted(pending) if dependencies[i]<=set(order)]
        if not ready:raise ValueError('Quest prerequisite cycle; no local order preserves all required objectives')
        index=ready[0];order.append(index);pending.remove(index)
    if order==list(range(len(goals))):return data,[]
    data['quests']=[goals[i] for i in order]
    return data,[dict(field='quests',before=goals,after=data['quests'],invariant='Obtain required items and activate switches before mandatory unlock/delivery',reason='Stable topological prerequisite order; same-area return visits preserved')]
