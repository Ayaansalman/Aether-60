import Phaser from 'phaser';
import type {Actor,Area,AdventureArt,TextureAsset} from './types';

export function preloadArt(scene:Phaser.Scene,art:AdventureArt) {
  for(const a of Object.values(art.assets))if(!scene.textures.exists(a.id))
    scene.load.spritesheet(a.id,a.url,{frameWidth:a.frame_width,frameHeight:a.frame_height});
}

export function registerAnimations(scene:Phaser.Scene,art:AdventureArt) {
  for(const a of Object.values(art.assets))for(const [direction,states] of Object.entries(a.animations))for(const [state,frames] of Object.entries(states)){
    const key=`${a.id}:${direction}:${state}`;
    if(!scene.anims.exists(key))scene.anims.create({key,frames:frames.map(frame=>({key:a.id,frame})),frameRate:state==='walk'?9:6,repeat:state==='attack'?0:-1});
  }
}

export function applyAsset(sprite:Phaser.Physics.Arcade.Sprite,asset:TextureAsset,frame=0) {
  sprite.setTexture(asset.id,frame).setScale(asset.scale);
  if(asset.body){
    // Map coordinates describe feet, regardless of transparent frame padding.
    sprite.setOrigin(.5,(asset.body.offset_y+asset.body.height/2)/asset.frame_height);
    sprite.setSize(asset.body.width,asset.body.height).setOffset(asset.body.offset_x,asset.body.offset_y);
  }
}

export function animateActor(sprite:Phaser.Physics.Arcade.Sprite,asset:TextureAsset,vx:number,vy:number,attack=false) {
  if(!Object.keys(asset.animations).length)return;
  let direction=sprite.getData('direction')||'down';
  if(Math.abs(vx)>Math.abs(vy))direction=vx<0?'left':'right';else if(Math.abs(vy)>.1)direction=vy<0?'up':'down';
  sprite.setData('direction',direction).setFlipX(false).setAngle(0).setScale(asset.scale);
  const state=attack&&asset.animations[direction]?.attack?'attack':Math.hypot(vx,vy)>2?'walk':'idle';
  sprite.play(`${asset.id}:${direction}:${state}`,true);
}

export function actorVisual(art:AdventureArt,actor:Actor) {
  const asset=art.assets[art.actors[actor.id]];
  const role=art.roles[actor.kind];
  return {asset,frame:role?.asset===asset.id?role.frame:0};
}

export function terrainFrames(art:AdventureArt,area:Area,seed:number) {
  const t=art.terrain,outdoor=['village','forest'].includes(area.environment);
  const path=(x:number,y:number)=>area.tiles[y]?.[x]===2;
  return area.tiles.map((row,y)=>row.map((v,x)=>{
    if(v>=10)return t.ground[0]; // Complete building modules are drawn above the ground layer.
    if(v===1)return outdoor&&area.trees?.some(p=>p.x===x&&p.y===y)?t.ground[0]:outdoor?t.solid:t.wall;
    if(v===3)return outdoor?t.decoration:t.indoor_details?.length?t.indoor_details[Math.abs((x*7+y*13+seed)%t.indoor_details.length)]:t.debris;
    if(v===2&&outdoor){
      const u=!path(x,y-1),d=!path(x,y+1),l=!path(x-1,y),r=!path(x+1,y);
      const edge=u&&l?'ul':u&&r?'ur':d&&l?'dl':d&&r?'dr':u?'u':d?'d':l?'l':r?'r':'';
      return t.edges[edge]??t.path;
    }
    return outdoor?t.ground[Math.abs((x*13+y*7+seed)%t.ground.length)]:t.indoor_ground;
  }));
}
