"""Prompt planning and seeded connected-world construction for the adventure adapter."""
import hashlib
import json
import random
import re
import struct
from collections import deque
from pathlib import Path
from schemas.adventure import AdventureDesign, AdventureIR, AreaIR, PlacedActor


def is_adventure(prompt):
    return bool(re.search(r'\b(top[ -]?down|rpg|adventure|villagers?|dungeon|healer)\b', prompt, re.I)) and not bool(re.search(r'\bplatformer\b', prompt, re.I))


def fixture_design(prompt):
    p = prompt.lower()
    peaceful = bool(re.search(r'peaceful|no (?:enemies|combat)|rather than combat|without (?:enemies|combat)', p))
    combat = not peaceful and bool(re.search(r'fight|combat|monsters?|enemies|defeat', p))
    dungeon = bool(re.search(r'dungeon|crypt|ruins|cave', p))
    village = 'village' in p or 'healer' in p
    environment = 'cave' if 'cave' in p else 'dungeon' if re.search(r'dungeon|crypt',p) else 'ruins' if dungeon else 'village' if village else 'forest'
    actors, quests = [], []
    def actor(id, kind, name, **kw):
        actors.append(dict(id=id, kind=kind, name=name, **kw))
    def quest(kind, target, text, **kw):
        quests.append(dict(kind=kind, target=target, text=text, **kw))
    if village or re.search(r'talk|villager|deliver|return', p):
        actor('guide','npc','Mira the Healer' if 'herb' in p else 'Rowan the Guide', role='healer' if 'herb' in p else 'guide',
              dialogue={'greeting':['Welcome! I need your help.','Please gather the magical herbs in the woodland clearings east of the village, then bring them back to me.' if 'herb' in p else 'Follow the paths to explore our settlement.'],
                        'active':['Look for the herbs along the eastern woodland paths. Return here when you have them.' if 'herb' in p else 'Follow the objective to find what we need.'], 'completed':['You brought everything back. Thank you, traveler!']})
        quest('talk','guide','Talk to the healer' if 'herb' in p else 'Talk to Rowan')
        actor('villager','npc','Jun the Gardener',role='villager',dialogue={'greeting':['The paths lead to every corner of our home.'], 'active':['Try exploring beyond the houses.'], 'completed':['Our village feels brighter today.']})
    if combat:
        actor('guardian','enemy','Skeleton Guard' if 'skeleton' in p else 'Ruins Guardian',behavior='patrol')
        actor('stalker','enemy','Skeleton Sentinel' if 'skeleton' in p else 'Cave Stalker',behavior='chase')
        quest('defeat','guardian','Defeat the skeleton guard' if 'skeleton' in p else 'Defeat the patrolling guardian')
        quest('defeat','stalker','Defeat the skeleton sentinel' if 'skeleton' in p else 'Defeat the stalking monster')
    if 'herb' in p:
        match=re.search(r'(\d+|one|two|three|four|five)\s+(?:missing\s+)?(?:magical\s+)?herbs?',p)
        count=min(10,int(match[1]) if match and match[1].isdigit() else {'one':1,'two':2,'three':3,'four':4,'five':5}.get(match[1] if match else '',3))
        actor('herbs','item','Magical Herb',item='herb',quantity=count)
        quest('collect','herbs',f'Find {count} magical herbs',count=count)
        if any(a['id']=='guide' for a in actors):
            quest('deliver','guide',f'Return {count} herbs to the healer',item='herb',count=count)
    elif re.search(r'artifact|relic|collect|find|key',p):
        key='key' in p
        actor('relic','item','Ancient Key' if key else 'Lost Artifact',item='key' if key else 'artifact')
        quest('collect','relic','Find the ancient key' if key else 'Recover the lost artifact')
        if not key and any(a['id']=='guide' for a in actors):
            quest('deliver','guide','Return the artifact to Rowan',item='artifact')
    requires=[]
    if any(a.get('item')=='key' for a in actors): requires.append('key')
    if re.search(r'switch|activat',p):
        actor('rune','switch','Runic Switch');quest('activate','rune','Activate the magical switch');requires.append('rune')
    if re.search(r'unlock|door|chamber|passage|shrine',p):
        actor('seal','door','Ancient Seal',requires=requires);quest('unlock','seal','Unlock the ancient passage')
    areas=[dict(name='Woodland Village' if environment=='village' else 'Whispering Forest' if environment=='forest' else 'Forgotten Crypt' if 'crypt' in p else 'Ancient Ruins',environment=environment)]
    if dungeon and re.search(r'chamber|treasure|dungeon|crypt',p):
        areas.append(dict(name='Treasure Chamber',environment='dungeon'))
        actor('treasure','treasure','Magical Relic' if 'relic' in p else 'Ancient Treasure',area=1);quest('collect','treasure','Claim the magical relic' if 'relic' in p else 'Open the treasure in the final chamber')
    elif not quests or re.search(r'explore',p) and not village:
        actor('vista','landmark','Hidden Sanctuary');quest('explore','vista','Discover the hidden sanctuary')
    unsupported=[f'Unsupported request: {w}' for w in ['multiplayer','crafting','equipment','3d','boss','procedural dialogue'] if w in p]
    design=AdventureDesign(title='The Woodland Remedy' if village else 'The Forgotten Crypt' if 'crypt' in p else 'The Sealed Depths' if dungeon else 'Whispers of the Wild',
        premise=prompt[:500],theme='dark' if dungeon else 'woodland',areas=areas,actors=actors,quests=quests,combat=combat,unsupported=unsupported)
    if re.search(r'forest|woodland|nature',p) and re.search(r'ice|icy|frozen|snow',p) and not re.search(r'(?:second|next|two|2) levels?',p):
        from schemas.adventure import AreaDesign,Actor,Goal
        design.theme='woodland';design.title='Forest and Frost'
        design.areas=[AreaDesign(name='Enchanted woodland and frozen ruins',environment='forest',regions=[
            dict(id='woodland',name='Enchanted Forest',biome='forest',x=1,y=1,width=46,height=30),
            dict(id='lake',name='Frozen Lake',biome='frozen_lake',x=20,y=10,width=12,height=12,slippery='slippery' in p),
            dict(id='ruins',name='Icy Ruins',biome='icy_ruins',x=34,y=7,width=11,height=17)])]
        if re.search(r'crystal|retrieve',p):
            design.actors=[Actor(id='villager',kind='npc',name='Rowan the Forest Keeper',region='woodland',dialogue={'greeting':['Please retrieve the magical crystal from the Icy Ruins east of the frozen lake.'],'active':['The crystal is in the Icy Ruins.'],'completed':['The forest thanks you.']}),Actor(id='crystal',kind='item',name='Magical Crystal',item='crystal',region='ruins')]
            design.quests=[Goal(kind='talk',target='villager',text='Speak to Rowan'),Goal(kind='collect',target='crystal',text='Retrieve the magical crystal from the Icy Ruins'),Goal(kind='deliver',target='villager',item='crystal',text='Return the crystal to Rowan')]
        else:
            for a in design.actors:a.area=0
    return design



def normalize_outdoor_return(data):
    """A delivery loop must stay on one traversable village/woodland map.

    Area portals are forward-only. Merge only an outdoor collection/return loop;
    never reorder objectives or silently merge dungeon gates/interiors.
    """
    data=json.loads(json.dumps(data));changes=[]
    areas=data.get('areas',[]);actors=data.get('actors',[]);quests=data.get('quests',[])
    by_id={a.get('id'):a for a in actors}
    order=[by_id.get(q.get('target'),{}).get('area',0) for q in quests]
    if len(areas)>1 and all(a.get('environment') in ('village','forest') for a in areas) and any(q.get('kind')=='deliver' for q in quests) and order!=sorted(order):
        home=next((a for a in areas if a.get('environment')=='village'),areas[0])
        changes.append({'field':'areas','before':areas,'after':[home],
                        'reason':'Outdoor return quest uses connected settlement and woodland zones; area portals are forward-only.'})
        data['areas']=[home]
        for actor in actors:actor['area']=0
    return data,changes


def plan(prompt, mode, raw_callback=None, intent=None):
    if mode=='fixture':
        return fixture_design(prompt), {'provider':'fixture','model':None,'live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider):
        raise ValueError('Live mode requires a configured model provider. Fixture mode is available offline.')
    system='''Biome regions and localized slippery momentum are implemented runtime capabilities. Do not list them as unsupported.
Biome regions are spatial rectangles within one 48x32 area (interior x=1..46,y=1..30).
Use AreaDesign.regions for same-world forest, snow, frozen_lake and icy_ruins. Later regions override earlier regions, so a large forest may surround a smaller lake. Give each an id/name/biome/x/y/width/height. slippery=true ONLY when requested. Set actor.region to the requested location (crystal in icy ruins, villager in forest). Preserve same-level constraints with exactly one area; use separate areas only for explicit separate levels.
You design Aether top-down adventures. Return ONLY JSON matching the schema below.
Use supported event-driven sequential quests: talk to NPC, collect item, deliver inventory to NPC,
explore landmark, defeat enemy, activate switch, unlock door. All targets are actor IDs.
Areas progress in order via an exit portal. Put all earlier-area quests before later-area quests.
Collection/delivery adventures returning to an NPC MUST use ONE area: village and nearby forest
are connected zones of that map. Never put their herbs in a second area then return to area zero.
Door requires contains inventory item IDs or switch actor IDs; these are latched, keys are retained.
Every collect target must have enough quantity; every deliver needs item (inventory ID) and count,
or delivery_items mapping every requested item ID to its quantity when returning multiple different items.
Use at most one sealed door per area. A door creates a real blocking passage; later targets are beyond it.
An item quantity is distributed as separate pickups. Never reuse an item pickup for later collect goals.
Avoid delivering keys needed later. All areas must be meaningful. Compose only mechanics requested.
Peaceful/no-combat requests MUST have combat=false and no enemies. Use combat=true when fighting is requested.
NPC dialogue greeting/active/completed are short arrays of lines. Refer only to existing characters/items
and supported mechanics. Do not invent spatial clues: no rivers/streams, bridges or special props unless
they are supported actors in the specification. Locations are determined by the map builder.
Use concrete contextual requests, and give NPCs names and roles.
No code, arbitrary scripts, stats, crafting, multiplayer or equipment. Record ONLY explicitly requested
unsupported features. Do not list unsolicited limitations or subjective mood as an unsupported mechanic.
Actors need unique lowercase IDs; area is zero based. No coordinates: the world builder places actors.
Prefer one coherent quest with 3-6 stages, at most two small areas. A key is a prerequisite, never a replacement for the requested relic. Put the relic after the unlock goal, in the same area or the next. Use talk/collect/deliver for healer quests and defeat/collect-key/unlock/claim-relic for crypt quests. Prefer 1-2 small areas, varied meaningful goals. Theme woodland/dark/fantasy.
Art style: auto selects the primary Ninja Adventure family. art_style can be ninja_adventure,
tiny_rpg_forest (forest exploration/combat only, no NPCs, doors or interiors), or kenney_tiny
for the older compatibility theme. Never add gameplay to match an asset. Select actors and environments
from the user requirements; registered resources are resolved after design validation.
Schema: '''+json.dumps(AdventureDesign.model_json_schema())
    if intent: system += "\nPreserve this semantic interpretation: "+json.dumps(intent)
    result=provider.complete(system,prompt)
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',result.text.strip())
    raw=json.loads(text)
    if raw_callback:raw_callback(raw)
    normalized,changes=normalize_outdoor_return(raw)
    design=AdventureDesign.model_validate(normalized)
    if re.search(r'peaceful|no combat|no enemies|rather than combat',prompt,re.I) and design.combat:
        raise ValueError('Model contradicted explicit peaceful requirement')
    return design, {'provider':type(provider).__name__,'model':result.model,'live':True,'latency_ms':result.latency_ms,'normalizations':changes}


def enforce_requirements(design, prompt):
    """Small explicit corrections with preserved raw output; no extra provider request."""
    changes=[]
    words={'multiplayer':r'multiplayer|co-op|online','crafting':r'craft','equipment':r'equipment|equip|armor|stats',
           '3d':r'\b3d\b','boss':r'\bboss\b','time of day':r'day.?night|time of day','inventory management':r'complex inventory|inventory management'}
    registered = {
        'slippery terrain physics modifier': any(r.slippery for area in design.areas for r in area.regions),
        'slippery terrain': any(r.slippery for area in design.areas for r in area.regions),
        'seamless biome transition without loading screens': len(design.areas)==1 and len(design.areas[0].regions)>1,
        'same level biome regions': len(design.areas)==1 and len(design.areas[0].regions)>1,
    }
    retained=[]
    for limitation in design.unsupported:
        if registered.get(limitation.lower().strip().removeprefix('unsupported: ').removeprefix('unsupported request: ')):
            changes.append({'field':'unsupported','before':limitation,'reason':'Typed biome regions instantiate this registered capability; runtime verification follows'})
            continue
        matches=[pattern for name,pattern in words.items() if name in limitation.lower()]
        if any(re.search(pattern,prompt,re.I) for pattern in matches) or limitation.lower() in prompt.lower() or (not matches and not re.search(r'cozy|non-combat|peaceful',limitation,re.I)):retained.append(limitation)
        else:changes.append({'field':'unsupported','before':limitation,'reason':'No matching requested unavailable capability; raw model output preserved'})
    design.unsupported=retained
    actors={a.id:a for a in design.actors};pending={}
    for q in design.quests:
        a=actors[q.target]
        if q.kind=='collect' and a.kind=='item':pending[a.item]=pending.get(a.item,0)+q.count
        if q.kind=='deliver':
            if len(pending)>1 and re.search(r'herbs|items|artifacts|them|all ',q.text+' '+prompt,re.I) and not q.delivery_items:
                q.delivery_items=dict(pending);changes.append({'field':'delivery_items','target':q.target,'after':dict(pending),'reason':'Returning the collected set requires every item, not only the first'})
            for item in (q.delivery_items or {q.item:q.count}):pending.pop(item,None)
        # Position hints cannot be known before procedural placement; target names are grounded.
        if q.kind in ('collect','explore') and re.search(r'near |by the |under |stream|garden|oak tree',q.text,re.I):
            before=q.text;q.text=('Find ' if q.kind=='collect' else 'Discover ')+a.name
            changes.append({'field':'quest.text','before':before,'after':q.text,'reason':'Removed spatial claim not represented by a placed actor'})
    for a in design.actors:
        if a.kind!='npc':continue
        for phase in ('greeting','active','completed'):
            lines=getattr(a.dialogue,phase)
            for i,line in enumerate(lines):
                if re.search(r'near the gardens?|by the stream|under the.*tree|craft (?:you|an?|the)',line,re.I):
                    lines[i]='Follow the paths and explore the current objective.'
                    changes.append({'field':f'{a.id}.dialogue.{phase}','before':line,'after':lines[i],'reason':'Unrepresented location or mechanic'})
    return {'changes':changes,'scope':'Bounded explicit feature/resource guards, not general semantic fidelity certification'}


def construct(design, prompt, seed=None):
    seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16)
    from services.adventure_world import build_area
    areas=[build_area(design,index,seed) for index in range(len(design.areas))]
    from services.adventure_assets import choose_art
    return AdventureIR(title=design.title,premise=design.premise,theme=design.theme,seed=seed,combat=design.combat,art=choose_art(design,prompt,seed),
                       areas=areas,quests=design.quests,unsupported=design.unsupported)


def validate_world(ir):
    checks=[]
    for area in ir.areas:
        start=(area.spawn['x'],area.spawn['y']);seen={start};queue=deque([start])
        while queue:
            x,y=queue.popleft()
            for nx,ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                if 0<=nx<area.width and 0<=ny<area.height and (nx,ny) not in seen and area.tiles[ny][nx] not in (1,4) and area.tiles[ny][nx]<10:
                    seen.add((nx,ny));queue.append((nx,ny))
        targets=[(a.x,a.y) for a in area.actors]+[(area.exit['x'],area.exit['y'])]
        targets += [(p['x'],p['y']) for a in area.actors for p in a.pickups]
        checks.append({'id':area.name,'passed':all(t in seen for t in targets),'reachable_tiles':len(seen),'destinations':len(targets)})
    # Symbolic ordered objective replay catches consumed-item and premature pickup softlocks.
    actors={a.id:a for area in ir.areas for a in area.actors};inventory={};picked=set();activated=set();unlocked=set()
    def reachable(area):
        blocked={(a.x,a.y) for a in area.actors if a.kind=='door' and a.id not in unlocked}
        start=(area.spawn['x'],area.spawn['y']);seen={start};todo=deque([start])
        while todo:
            x,y=todo.popleft()
            for nx,ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                if 0<=nx<area.width and 0<=ny<area.height and (nx,ny) not in blocked and (nx,ny) not in seen and area.tiles[ny][nx] not in (1,4) and area.tiles[ny][nx]<10:
                    seen.add((nx,ny));todo.append((nx,ny))
        return seen
    for q in ir.quests:
        a=actors[q.target];ok=True
        seen=reachable(ir.areas[a.area])
        if q.kind=='unlock':
            ok=any((a.x+dx,a.y+dy) in seen for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)])
        else:ok=(a.x,a.y) in seen
        if q.kind=='collect':
            ok=ok and a.id not in picked and all((p['x'],p['y']) in seen for p in a.pickups);picked.add(a.id)
            if a.item: inventory[a.item]=inventory.get(a.item,0)+a.quantity
        elif q.kind=='deliver':
            for item,count in (q.delivery_items or {q.item:q.count}).items():
                ok=ok and inventory.get(item,0)>=count;inventory[item]=inventory.get(item,0)-count
        elif q.kind=='activate':activated.add(a.id)
        elif q.kind=='unlock':
            # Non-objective keys may be freely collected en route.
            for item in actors.values():
                if item.kind=='item' and item.id not in picked and item.area==a.area and all((p['x'],p['y']) in seen for p in item.pickups):
                    inventory[item.item]=inventory.get(item.item,0)+item.quantity;picked.add(item.id)
            ok=ok and all(inventory.get(ref,0)>0 or ref in activated for ref in a.requires)
            if ok:unlocked.add(a.id)
        checks.append({'id':q.text,'passed':ok})
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks,
            'scope':'Flood-fill destinations and ordered resource prerequisites; browser verifies actual gameplay.'}


def asset_manifest(art=None):
    if art is not None:return art.model_dump()
    from services.adventure_assets import catalog
    return catalog()


def validate_assets():
    public=Path(__file__).resolve().parents[2]/'aether-frontend/public'
    checks=[]
    legacy=json.loads((public/'assets/adventure/registry.json').read_text())
    for key,entry in legacy['textures'].items():
        path=public/entry['url'].lstrip('/')
        data=path.read_bytes() if path.is_file() else b''
        dimensions=struct.unpack('>II',data[16:24]) if data.startswith(b'\x89PNG') and len(data)>=24 else None
        checks.append({'id':key,'passed':bool(data) and hashlib.sha256(data).hexdigest()==entry['sha256'] and dimensions==(entry['width'],entry['height']),
                       'dimensions':dimensions})
    from services.adventure_assets import validate_catalog
    checks.extend(validate_catalog()['checks'])
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}
