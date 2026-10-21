"""Seeded spatial grammar: settlement/foraging zones and a gated room graph.

Geometry precedes decoration. Actor reservations and paths are never overwritten.
The same grammar accepts arbitrary validated actors, quantities and quest order.
"""
import random
import re
from schemas.adventure import AreaIR, PlacedActor


def build_area(design, index, seed):
    rng = random.Random(seed + index * 7919)
    area = design.areas[index]
    outdoor = area.environment in ('village', 'forest')
    w, h = 48, 32
    tiles = [[1 for _ in range(w)] for _ in range(h)]
    protected, used, trees, buildings, zones = set(), set(), [], [], []

    def rect(x, y, width, height, value=0):
        for py in range(y, y + height):
            for px in range(x, x + width):
                if 0 < px < w - 1 and 0 < py < h - 1:
                    tiles[py][px] = value

    def path(a, b, radius=0):
        x, y = a
        tx, ty = b
        while True:
            for dy in (range(-radius, radius + 1) if radius else (0, 1)):
                for dx in (range(-radius, radius + 1) if radius else (0, 1)):
                    px, py = x + dx, y + dy
                    if 0 < px < w - 1 and 0 < py < h - 1:
                        tiles[py][px] = 2
                        protected.add((px, py))
            if x != tx: x += 1 if tx > x else -1
            elif y != ty: y += 1 if ty > y else -1
            else: break

    if outdoor:
        rect(1, 1, w - 2, h - 2)
        spawn, exit = (12, 17), (43, 16)
        hub = (13, 17)
        zones = [dict(name='Village square' if area.environment == 'village' else 'Trailhead', x=13, y=17),
                 dict(name='Herbalist clearing', x=36, y=9), dict(name='Deepwood grove', x=38, y=24)]
        rect(10, 14, 7, 7, 2)
        path((2, 18), hub, 1)
        path(hub, (29, 17), 0)
        path((29, 17), exit, 0)
        path((29, 17), (36, 9), 0)
        path((29, 17), (38, 24), 0)
        if area.environment == 'village':
            slots = [(5, 10), (5, 23), (19, 23)]
            rng.shuffle(slots)
            slots.insert(0, (19, 10))  # The first quest giver's home fronts the square.
            for n, (x, y) in enumerate(slots[:rng.randint(3, 4)]):
                buildings.append(dict(x=x, y=y, variant=(seed+n) % 2))
                for dy in range(3):
                    for dx in range(3): tiles[y+dy][x+dx] = 10 + dy*3 + dx
                path((x+1, y+3), (13, y+3))
                path((13, y+3), hub)
    else:
        spawn, exit = (8, 23), (43, 23)
        hub = (8, 23)
        # An entrance, guard hall, side discovery, archive and sealed destination.
        centers = [(8, 23), (rng.randint(7,9), rng.randint(7,9)),
                   (rng.randint(22,24), rng.randint(7,9)), (23, 23), (39, 23)]
        labels = ['Entrance hall', 'Guard chamber', 'Forgotten archive', 'Reliquary approach', 'Sealed sanctum']
        final_only = index > 0 and len([a for a in design.actors if a.area == index]) <= 2
        if final_only:
            centers = [(8,23), (23,23), (39,23)]
            labels = ['Inner threshold', 'Relic gallery', 'Heart of the crypt']
        for (x, y), name in zip(centers, labels):
            rx, ry = rng.randint(4,5), rng.randint(3,4)
            rect(x-rx, y-ry, rx*2+1, ry*2+1)
            zones.append(dict(name=name, x=x, y=y))
        edges = [(0,1),(1,2)] if final_only else [(0,1),(1,2),(2,3),(0,3),(3,4)]
        for a, b in edges:
            path(centers[a], centers[b], 0 if b == len(centers)-1 else 1)

    used.update([spawn, exit])
    placed = []
    actors = [a for a in design.actors if a.area == index]
    door = next((a for a in actors if a.kind == 'door'), None)
    door_order = next((i for i, q in enumerate(design.quests) if door and q.target == door.id), len(design.quests))
    door_x, door_y = (31, 23) if not outdoor else (32, 17)

    region=None
    def reserve(center, bounds):
        candidates = [(x, y) for y in range(bounds[1], bounds[3]) for x in range(bounds[0], bounds[2])
                      if tiles[y][x] < 10 and tiles[y][x] != 1 and
                      (region is None or next((r.id for r in reversed(area.regions) if r.x<=x<r.x+r.width and r.y<=y<r.y+r.height),None)==region.id) and
                      all(abs(x-u)+abs(y-v) >= 3 for u, v in used)]
        if not candidates: raise ValueError('Spatial zone exhausted by adventure actors')
        candidates.sort(key=lambda p: abs(p[0]-center[0])+abs(p[1]-center[1])+rng.random()*3)
        pos = candidates[0]
        used.add(pos)
        # Preserve the semantic ground in clearings; reserve a generous approach.
        for y in range(pos[1]-1, pos[1]+2):
            for x in range(pos[0]-1, pos[0]+2): protected.add((x, y))
        return pos

    for n, actor in enumerate(actors):
        order = next((i for i, q in enumerate(design.quests) if q.target == actor.id), -1)
        beyond = door and order > door_order
        if actor.kind == 'door':
            x, y = door_x, door_y
            placed.append(PlacedActor(**actor.model_dump(), x=x, y=y))
            continue
        if outdoor:
            settlement = actor.kind == 'npc' or actor.kind == 'landmark' and re.search(r'village|square|market|fountain|well',actor.name+' '+actor.role, re.I)
            first_npc = actor.kind == 'npc' and not any(a.kind=='npc' for a in actors[:n])
            center = ((20,14) if first_npc and buildings else (7+n%2*7,16)) if actor.kind == 'npc' else hub if settlement else (36, 8+n%3*8)
            bounds = (4, 4, 26, 29) if settlement else (34 if beyond else 27, 4, 45, 29)
            if door and not beyond: bounds = (bounds[0], bounds[1], min(bounds[2], door_x-2), bounds[3])
        else:
            center = (39, 23) if beyond or final_only else centers[2] if actor.kind in ('item', 'switch', 'treasure') else centers[1+n%2]
            bounds = (34, 19, 45, 28) if beyond or final_only else (3, 4, 29, 28)
        region=next((r for r in area.regions if r.id==actor.region),None)
        if region:
            bounds=(region.x+1,region.y+1,region.x+region.width-1,region.y+region.height-1)
            center=(region.x+region.width//2,region.y+region.height//2)
        x, y = reserve(center, bounds)
        pickups = []
        if actor.kind == 'item':
            pickups.append(dict(x=x, y=y))
            for i in range(1, actor.quantity):
                px, py = reserve((center[0], 6 + (i*7+n*3) % 21), bounds)
                pickups.append(dict(x=px, y=py))
        for p in pickups or [dict(x=x, y=y)]:
            anchor = (29, 17) if outdoor else min(centers, key=lambda c: abs(c[0]-p['x'])+abs(c[1]-p['y']))
            if outdoor and settlement: anchor = hub
            if beyond: anchor = (39, door_y)
            path(anchor, (p['x'], p['y']))
        placed.append(PlacedActor(**actor.model_dump(), x=x, y=y, pickups=pickups))

    if outdoor:
        # Clustered tree lines frame clearings and leave the settlement readable.
        for y in range(2, h-2, 2):
            for x in range(2, w-2, 2):
                forest = x > 25 or x < 4 or y < 4 or y > 28
                if not forest or rng.random() > .70: continue
                if any((x+dx, y+dy) in protected or tiles[y+dy][x+dx] >= 10 for dx in (-1,0,1) for dy in (-1,0,1)): continue
                tiles[y][x] = 1
                trees.append(dict(x=x, y=y))
        for y in range(2, h-2):
            for x in range(2, w-2):
                if tiles[y][x] == 0 and (x,y) not in protected and rng.random() < (.055 if x>25 else .018): tiles[y][x] = 3
    else:
        # Urns/statues frame the rooms rather than littering the walking route.
        for zone in zones:
            for dx, dy in [(-3,-2),(3,-2),(-3,2),(3,2)]:
                x,y=zone['x']+dx,zone['y']+dy
                if tiles[y][x] == 0 and (x,y) not in protected: tiles[y][x] = 3
    # Deliberate biome clearings preserve all routes and remove incompatible tree modules.
    for region in area.regions:
        if region.biome=='forest': continue
        for ry in range(region.y,region.y+region.height):
            for rx in range(region.x,region.x+region.width):
                if tiles[ry][rx] in (1,3,4): tiles[ry][rx]=0
        trees=[t for t in trees if not (region.x<=t['x']<region.x+region.width and region.y<=t['y']<region.y+region.height)]
        zones.append(dict(name=region.name,x=region.x+region.width//2,y=region.y+2))
    if door:
        for y in range(1, h-1): tiles[y][door_x] = 1
        tiles[door_y][door_x] = 2
        tiles[door_y][door_x-1] = tiles[door_y][door_x+1] = 2
        trees = [p for p in trees if p['x'] != door_x]
    return AreaIR(**area.model_dump(), width=w, height=h, tiles=tiles,
                  spawn=dict(zip(('x','y'), spawn)), exit=dict(zip(('x','y'), exit)),
                  actors=placed, zones=zones, trees=trees, buildings=buildings)
