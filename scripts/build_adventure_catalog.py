"""Curate verified CC0 downloads into a reproducible, semantic runtime catalog.

Input: archives extracted under aether-backend/artifacts/asset-imports.
No downloaded source code executes. Derived sheets only crop/repack authored pixels.
"""
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
IMPORT=ROOT/'aether-backend/artifacts/asset-imports'
PUBLIC=ROOT/'aether-frontend/public'
DEST=PUBLIC/'assets/adventure/library'
NINJA=IMPORT/'ninja/Ninja Adventure - Asset Pack'
TINY=IMPORT/'tiny-rpg/tiny-RPG-forest-files'
catalog={'version':'1.1','packs':{},'assets':{}}
REVIEWED_ARCHIVES={'ninja.zip':'95a06f4fdcfd1882f061a45ff313b7c905dbe2de1e8512b281d7937df62a7b15',
    'tiny-rpg.zip':'84543133ce250c2123e4e536be8c6f8e467549f8be2f533af137abeee90154b6'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(id,root,source,author,archive,licensefile):
    if sha(IMPORT/archive)!=REVIEWED_ARCHIVES[archive]:raise ValueError('Archive changed; inspect contents and license before updating reviewed hash')
    target=DEST/id;target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root/licensefile,target/Path(licensefile).name)
    catalog['packs'][id]={'id':id,'source':source,'author':author,'license':'CC0-1.0','redistributable':True,
        'style_family':id,'license_files':['/'+(target/Path(licensefile).name).relative_to(PUBLIC).as_posix()],
        'archive_sha256':sha(IMPORT/archive),'categories':{},'source_file_count':len([p for p in root.rglob('*') if p.is_file()]),
        'selection_notes':'A game uses one style family; no cross-pack fallback inside a selected game.'}


def asset(packid,id,category,source,tags,frame=None,animations=None,body=None,derived=None):
    target=DEST/packid/category/(id+'.png');target.parent.mkdir(parents=True,exist_ok=True)
    if derived is None:shutil.copyfile(source,target)
    else:derived.save(target)
    im=Image.open(target)
    entry={'id':id,'pack_id':packid,'style_family':packid,'category':category,'tags':tags,
        'url':'/'+target.relative_to(PUBLIC).as_posix(),'width':im.width,'height':im.height,'sha256':sha(target),
        'frame_width':frame[0] if frame else im.width,'frame_height':frame[1] if frame else im.height,
        'source_path':str(source.relative_to(NINJA if packid=='ninja_adventure' else TINY)).replace('\\','/'),
        'license':'CC0-1.0','redistributable':True,'animations':animations or {},'body':body,
        'scale':2 if frame and frame[0]==16 else 1}
    fw,fh=entry['frame_width'],entry['frame_height'];pixels=im.convert('RGBA')
    entry['nonempty_frames']=[i for i in range(im.width//fw*(im.height//fh)) if pixels.crop((i%(im.width//fw)*fw,i//(im.width//fw)*fh,i%(im.width//fw)*fw+fw,i//(im.width//fw)*fh+fh)).getbbox()]
    catalog['assets'][id]=entry
    catalog['packs'][packid]['categories'].setdefault(category,[]).append(id)
    return entry


def crop(file,index,columns=None):
    im=Image.open(file).convert('RGBA');columns=columns or im.width//16
    x=index%columns*16;y=index//columns*16
    assert x+16<=im.width and y+16<=im.height
    return im.crop((x,y,x+16,y+16))


def compose(base,overlay):
    result=base.copy();result.alpha_composite(overlay);return result


def old_animations(monster=False):
    return {direction:{'idle':[d],'walk':[d+4*i for i in range(0 if monster else 1,4)],
                       **({} if monster else {'attack':[16+d]})}
            for d,direction in enumerate(['down','up','left','right'])}


def ninja():
    pid='ninja_adventure'
    pack(pid,NINJA,'https://pixel-boy.itch.io/ninja-adventure-asset-pack','Pixel-Boy and AAA','ninja.zip','LICENSE.txt')
    shutil.copyfile(NINJA/'README.md',DEST/pid/'SOURCE-README.md')
    tile=NINJA/'Backgrounds/Tilesets';field=tile/'TilesetField.png';nature=tile/'TilesetNature.png';floor=tile/'TilesetFloor.png';house=tile/'TilesetHouse.png';dungeon=tile/'TilesetDungeon.png'
    grass=crop(field,18)
    frames=[grass,crop(field,19),crop(field,6),*[crop(field,i) for i in [0,1,2,5,7,10,11,12]],
        compose(grass,crop(nature,240)),compose(grass,crop(nature,264)),crop(floor,342),crop(house,700),compose(crop(floor,342),crop(floor,409))]
    frames += [crop(house,y*33+x) for y in range(3) for x in [4,5,7]]
    frames += [crop(house,y*33+x) for y in range(3) for x in [12,13,15]]
    frames += [crop(house,193),crop(house,71),crop(dungeon,40),crop(dungeon,41),crop(dungeon,25),crop(dungeon,27)]
    frames += [compose(crop(floor,342),crop(dungeon,i)) for i in [38,43,44,39]]
    sheet=Image.new('RGBA',(8*16,((len(frames)+7)//8)*16))
    for i,frame in enumerate(frames):sheet.paste(frame,(i%8*16,i//8*16))
    terrain=asset(pid,'ninja_terrain','environment',field,['forest','village','ruins','dungeon','cave'],(16,16),derived=sheet)
    terrain['derivation']={'method':'Repacked unmodified 16px cells; shrub/flower cells composited on ground',
        'sources':[str(p.relative_to(NINJA)).replace('\\','/') for p in [field,nature,floor,house,dungeon]],
        'source_sha256':{p.name:sha(p) for p in [field,nature,floor,house,dungeon]}}
    catalog['packs'][pid]['terrain']={'texture':'ninja_terrain','ground':[0,0,0,1],'path':2,'edges':{'ul':3,'u':4,'ur':5,'l':6,'r':7,'dl':8,'d':9,'dr':10},
        'solid':11,'decoration':12,'indoor_ground':13,'wall':14,'debris':15,'indoor_details':[40,41,42,43],'buildings':[list(range(16,25)),list(range(25,34))]}
    names=['NinjaBlue','NinjaGreen','Knight','Hunter','Woman','OldWoman','OldMan','Master','Monk','Monk2','Princess','Boy','Noble','Samurai','SorcererOrange','NinjaMageBlack','Caveman','Cavegirl','Eskimo','NinjaRed']
    for name in names:
        source=NINJA/f'Actor/Character/{name}/SpriteSheet.png'
        if not source.exists():continue
        category='character' if name in ['NinjaBlue','NinjaGreen','Knight','Hunter','SorcererOrange','Cavegirl'] else 'npc'
        total=Image.open(source).height//16*4
        animations={d:{state:[f for f in frames if f<total] for state,frames in modes.items() if any(f<total for f in frames)} for d,modes in old_animations().items()}
        asset(pid,'ninja_'+name.lower(),category,source,[name.lower(),*(['healer','mage'] if name in ['Woman','Monk','SorcererOrange'] else []),*(['elder','guide'] if 'Old' in name else [])],(16,16),animations,{'width':9,'height':9,'offset_x':3,'offset_y':6})
    for name in ['Slime','Slime2','Skull','SkullBlue','Mushroom','Mole','BlueBat','Snake','Beast','Spirit','Bamboo','Cyclope']:
        folder=NINJA/f'Actor/Monster/{name}'
        source=folder/'SpriteSheet.png'
        if not source.exists():source=next((p for p in folder.glob('*.png') if p.name!='Faceset.png'),None)
        if source is None:continue
        im=Image.open(source)
        if im.size!=(64,64):continue
        asset(pid,'ninja_'+name.lower(),'enemy',source,[name.lower(),'monster','dark' if 'Skull' in name or 'Spirit' in name else 'forest'],(16,16),old_animations(True),{'width':10,'height':10,'offset_x':3,'offset_y':5})
    for id,category,source,tags,frame in [
        ('ninja_herb','collectible','Items/Resource/Grass.png',['herb','leaf','mint','blossom'],None),
        ('ninja_key','collectible','Items/Treasure/GoldKey.png',['key'],None),
        ('ninja_gem','collectible','Items/Resource/GemGreen.png',['artifact','gem','relic'],None),
        ('ninja_chest','interactive_object','Items/Treasure/LittleTreasureChest.png',['treasure','chest'],(16,16)),
        ('ninja_projectile','vfx','Items/Projectile/Kunai.png',['projectile','attack'],None),
        ('ninja_smoke','vfx','Fx/Smoke/Smoke/SpriteSheet.png',['defeat','smoke'],(32,32)),
        ('ninja_hearts','ui','Ui/Receptacle/Heart.png',['health'],(16,16)),
        ('ninja_tree','decoration','Backgrounds/Tilesets/TilesetNature.png',['tree','woodland'],None),
    ]:
        source=NINJA/source
        derived=Image.open(source).crop((0,0,32,32)) if id=='ninja_tree' else None
        entry=asset(pid,id,category,source,tags,frame,derived=derived)
        if id in ['ninja_key','ninja_herb','ninja_gem','ninja_projectile','ninja_tree']:entry['scale']=2
    for name,frame,openframe in [('door',34,35),('switch',36,37),('exit',38,None),('landmark',39,None)]:
        catalog['packs'][pid].setdefault('roles',{})[name]={'asset':'ninja_terrain','frame':frame,'open_frame':openframe}
    catalog['packs'][pid]['roles'].update({key:{'asset':value,'frame':0,**({'open_frame':1} if key=='treasure' else {})} for key,value in
        {'herb':'ninja_herb','key':'ninja_key','item':'ninja_gem','treasure':'ninja_chest','projectile':'ninja_projectile','vfx':'ninja_smoke','health':'ninja_hearts','tree':'ninja_tree'}.items()})


def tiny_actor(kind,frame_size):
    root=TINY/'Assets/PNG/spritesheets'/kind
    fw,fh=frame_size;sheet=Image.new('RGBA',(fw*6,fh*5));animations={}
    for d,(direction,source_direction) in enumerate([('down','front'),('up','back'),('left','side'),('right','side')]):
        pattern=f'*{source_direction}*';walk=next((root/'walk').glob(pattern+'.png'));im=Image.open(walk).convert('RGBA');count=im.width//fw
        for i in range(count):
            frame=im.crop((i*fw,0,(i+1)*fw,fh))
            if direction=='left':frame=frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            sheet.paste(frame,(i*fw,d*fh))
        idle=Image.open(next((root/'idle').glob(pattern+'.png'))).convert('RGBA')
        if direction=='left':idle=idle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        sheet.paste(idle,(d*fw,4*fh));animations[direction]={'idle':[24+d],'walk':list(range(d*6,d*6+count))}
    return sheet,animations,walk


def tiny():
    pid='tiny_rpg_forest'
    pack(pid,TINY,'https://ansimuz.itch.io/tiny-rpg-forest','Luis Zuno (Ansimuz)','tiny-rpg.zip','public-license.pdf')
    if (TINY/'public-license.txt').exists():shutil.copyfile(TINY/'public-license.txt',DEST/pid/'LICENSE-extracted.txt')
    for name,size in [('hero',(32,32)),('mole',(24,24)),('treant',(31,35))]:
        sheet,animations,source=tiny_actor(name,size)
        entry=asset(pid,'tiny_'+name,'character' if name=='hero' else 'enemy',source,[name,'forest','ranger' if name=='hero' else 'monster'],size,animations,
            {'width':10,'height':9,'offset_x':(size[0]-10)//2,'offset_y':size[1]-11},derived=sheet)
        entry['derivation']={'method':'Repacked supplied directional walk/idle frames; mirrored side frames for left',
            'frame_count':sum(len(seq) for modes in animations.values() for seq in modes.values()),'sheet_cells':30}
        entry['scale']=2
    env=TINY/'Assets/PNG/environment/tileset.png';ground=crop(env,625);path=crop(env,873)
    frames=[ground,ground,path,*[crop(env,i) for i in [838,839,841,872,875,940,941,943]]]
    assert all(frame.getbbox() for frame in frames),'Terrain roles may not resolve to empty tiles'
    bush=Image.open(TINY/'Assets/PNG/environment/sliced-objects/bush.png').convert('RGBA').resize((16,16),Image.Resampling.NEAREST)
    rock=Image.open(TINY/'Assets/PNG/environment/sliced-objects/rock.png').convert('RGBA').resize((16,16),Image.Resampling.NEAREST)
    frames += [compose(ground,bush),crop(env,865),ground,compose(ground,rock),ground]
    frames += [ground]*24
    sheet=Image.new('RGBA',(128,80))
    for i,f in enumerate(frames):sheet.paste(f,(i%8*16,i//8*16))
    asset(pid,'tiny_terrain','environment',env,['forest','mountain','terrain'],(16,16),derived=sheet)
    catalog['packs'][pid]['terrain']={'texture':'tiny_terrain','ground':[0,1],'path':2,'edges':{'ul':3,'u':4,'ur':5,'l':6,'r':7,'dl':8,'d':9,'dr':10},'solid':11,'decoration':12,'indoor_ground':13,'wall':14,'debris':15,'buildings':[]}
    for id,category,source,tags,frame in [
        ('tiny_gem','collectible','Assets/PNG/spritesheets/misc/gem.png',['gem','artifact','collectible'],(7,7)),
        ('tiny_coin','collectible','Assets/PNG/spritesheets/misc/coin.png',['coin'],(5,7)),
        ('tiny_projectile','vfx','Assets/Phaser Demo/assets/sprites/arrow.png',['arrow','attack'],None),
        ('tiny_smoke','vfx','Assets/PNG/spritesheets/misc/enemy-death.png',['defeat'],(30,32)),
        ('tiny_monument','decoration','Assets/PNG/environment/sliced-objects/rock-monument.png',['landmark','ruins'],None),
        ('tiny_tree','decoration','Assets/PNG/environment/sliced-objects/tree-pink.png',['tree'],None),
        ('tiny_bush','collectible','Assets/PNG/environment/sliced-objects/bush.png',['herb'],None),
    ]:
        p=TINY/source
        if not p.exists():
            if id=='tiny_projectile':p=next((TINY/'Assets/PNG').rglob('arrow*.png'))
            else:raise ValueError(source)
        a=asset(pid,id,category,p,tags,frame)
        a['scale']=2
        if id in ['tiny_monument','tiny_tree']:a['scale']=.65
    catalog['packs'][pid]['roles']={k:{'asset':v,'frame':0} for k,v in {'item':'tiny_gem','herb':'tiny_bush','landmark':'tiny_monument','exit':'tiny_monument','projectile':'tiny_projectile','vfx':'tiny_smoke','tree':'tiny_tree'}.items()}
    catalog['packs'][pid]['supported_environments']=['forest']
    catalog['packs'][pid]['unsupported_actor_kinds']=['npc','door','switch','treasure']


if __name__=='__main__':
    ninja();tiny()
    DEST.parent.joinpath('catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    print('Catalog:',len(catalog['assets']),'assets', {k:{c:len(ids) for c,ids in v['categories'].items()} for k,v in catalog['packs'].items()})
