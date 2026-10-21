"""Semantic selection, coherence, loading integrity and redistribution allowlists."""
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from schemas.assets import AdventureArt

PUBLIC=Path(__file__).resolve().parents[2]/'aether-frontend/public'
CATALOG=PUBLIC/'assets/adventure/catalog.json'


def catalog():return json.loads(CATALOG.read_text(encoding='utf-8'))


def validate_catalog(data=None):
    data=data or catalog();checks=[]
    def check(id,passed,**detail):checks.append({'id':id,'passed':bool(passed),**detail})
    for pid,pack in data['packs'].items():
        check(pid+'_license',pack['license']=='CC0-1.0' and pack['redistributable'])
        for url in pack['license_files']:
            path=(PUBLIC/url.lstrip('/')).resolve()
            check(pid+'_license_file',path.is_relative_to(PUBLIC.resolve()) and path.is_file())
        terrain=pack['terrain'];texture=data['assets'].get(terrain['texture'])
        refs=[*terrain.get('indoor_details',[]),*terrain['ground'],terrain['path'],*terrain['edges'].values(),terrain['solid'],terrain['decoration'],terrain['indoor_ground'],terrain['wall'],terrain['debris'],*[f for building in terrain['buildings'] for f in building]]
        total=texture['width']//texture['frame_width']*(texture['height']//texture['frame_height']) if texture else 0
        check(pid+'_terrain_roles',bool(terrain['ground']) and all(0<=f<total for f in refs) and all(len(building)==9 for building in terrain['buildings']) and all(f in texture.get('nonempty_frames',[]) for f in [*terrain['ground'],terrain['path'],*terrain['edges'].values()]))
        for role,ref in pack['roles'].items():
            a=data['assets'].get(ref['asset']);frames=a['width']//a['frame_width']*(a['height']//a['frame_height']) if a else 0
            check(pid+'_'+role,a and a['pack_id']==pid and 0<=ref.get('frame',0)<frames and (ref.get('open_frame') is None or 0<=ref['open_frame']<frames))
    for id,a in data['assets'].items():
        path=(PUBLIC/a['url'].lstrip('/')).resolve()
        if not path.is_relative_to(PUBLIC.resolve()):check(id,False);continue
        raw=path.read_bytes() if path.is_file() else b''
        dims=struct.unpack('>II',raw[16:24]) if raw.startswith(b'\x89PNG') else (0,0)
        fw,fh=a['frame_width'],a['frame_height'];total=(dims[0]//fw)*(dims[1]//fh)
        frames=[f for directions in a['animations'].values() for seq in directions.values() for f in seq]
        ok=dims==(a['width'],a['height']) and dims[0]%fw==0 and dims[1]%fh==0
        ok=ok and all(0<=f<total for f in frames) and all(seq for directions in a['animations'].values() for seq in directions.values())
        check(id,ok and hashlib.sha256(raw).hexdigest()==a['sha256'] and a['pack_id'] in data['packs'] and a['license']=='CC0-1.0',dimensions=dims,frames=total)
    return {'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks}


def choose_art(design,prompt,seed):
    data=catalog();rng=random.Random(seed)
    requested=design.art_style
    if requested=='auto':requested='tiny_rpg_forest' if re.search(r'ansimuz|tiny rpg',prompt,re.I) else 'ninja_adventure'
    if requested=='kenney_tiny':return None
    if requested not in data['packs']:raise ValueError('Requested art style is not registered')
    reason='Selected registered style from prompt/design; default primary family is Ninja Adventure.'
    pack=data['packs'][requested]
    if any(a.environment not in pack.get('supported_environments',['forest','village','ruins','dungeon','cave']) for a in design.areas) or any(a.kind in pack.get('unsupported_actor_kinds',[]) for a in design.actors):
        requested='ninja_adventure';pack=data['packs'][requested]
        reason='Tiny RPG Forest lacks required village/interior/NPC/door roles. Selected the complete Ninja family for the entire game; no art styles mixed.'
    assets={id:a for id,a in data['assets'].items() if a['pack_id']==requested}
    if requested=='ninja_adventure':
        player='ninja_sorcererorange' if re.search(r'mage|wizard|sorcerer',prompt,re.I) else 'ninja_hunter' if re.search(r'archer|ranger',prompt,re.I) else 'ninja_knight' if 'knight' in prompt.lower() else 'ninja_ninjagreen' if design.theme=='woodland' else 'ninja_ninjablue'
        actors={}
        for a in design.actors:
            words=(a.name+' '+a.role).lower()
            if a.kind=='npc':
                id='ninja_woman' if re.search(r'healer|mira',words) else 'ninja_oldwoman' if re.search(r'elder|grandmother',words) else 'ninja_oldman' if re.search(r'guide|hermit|old',words) else rng.choice(['ninja_boy','ninja_monk2','ninja_noble','ninja_princess'])
            elif a.kind=='enemy':
                requested_monster='ninja_skull' if re.search(r'skeleton|skull',words) else next((id for id,v in assets.items() if v['category']=='enemy' and any(tag in words for tag in v['tags'] if tag not in ('forest','dark','monster'))),None)
                id=requested_monster or rng.choice(['ninja_skull','ninja_skullblue','ninja_spirit'] if design.theme=='dark' else ['ninja_slime','ninja_mushroom','ninja_bamboo'])
            else:
                role='herb' if a.kind=='item' and re.search(r'herb|leaf|mint|blossom|flower',a.item+' '+a.name,re.I) else 'key' if a.kind=='item' and 'key' in (a.item+' '+a.name).lower() else 'item' if a.kind=='item' else a.kind
                id=pack['roles'][role]['asset']
            actors[a.id]=id
    else:
        player='tiny_hero';actors={a.id:('tiny_treant' if a.behavior=='patrol' else 'tiny_mole') if a.kind=='enemy' else pack['roles']['landmark' if a.kind=='landmark' else 'herb' if re.search(r'herb|leaf|mint',a.item+' '+a.name,re.I) else 'item']['asset'] for a in design.actors}
    # Resolve only gameplay dependencies, not the complete library, into the game IR.
    role_names={'exit'}
    role_names.update(a.kind for a in design.actors if a.kind not in ('item','npc','enemy'))
    if any(a.kind=='item' for a in design.actors):role_names.update(['item','herb','key'])
    if any(a.environment in ('forest','village') for a in design.areas):role_names.add('tree')
    if design.combat:role_names.update(['vfx','projectile','health'])
    roles={k:v for k,v in pack['roles'].items() if k in role_names}
    needed={player,pack['terrain']['texture'],*actors.values(),*[v['asset'] for v in roles.values()]}
    return AdventureArt(pack_id=requested,style_family=pack['style_family'],catalog_version=data['version'],source=pack['source'],license=pack['license'],
        license_files=pack['license_files'],selection_reason=reason,player=player,actors=actors,
        assets={id:assets[id] for id in sorted(needed)},roles=roles,terrain=pack['terrain'])


def redistribution_manifest(art):
    """Explicit allowlist for future game-resource exports; never export the raw archive."""
    art=AdventureArt.model_validate(art.model_dump() if hasattr(art,'model_dump') else art)
    def safe_file(url):
        path=(PUBLIC/url.lstrip('/')).resolve()
        if not url.startswith('/assets/adventure/') or not path.is_relative_to((PUBLIC/'assets/adventure').resolve()) or not path.is_file():
            raise ValueError('Export resource is outside the registered artwork directory')
        return path
    files=[]
    for a in art.assets.values():
        if hashlib.sha256(safe_file(a.url).read_bytes()).hexdigest()!=a.sha256:raise ValueError('Export checksum mismatch')
        files.append({'url':a.url,'sha256':a.sha256,'license':a.license,'source_path':a.source_path})
    files += [{'url':url,'license':art.license,'sha256':hashlib.sha256(safe_file(url).read_bytes()).hexdigest()} for url in art.license_files]
    return {'pack_id':art.pack_id,'source':art.source,'redistribution':'CC0 allowlist; excludes raw downloads, demo source and unreviewed resources','files':files}
