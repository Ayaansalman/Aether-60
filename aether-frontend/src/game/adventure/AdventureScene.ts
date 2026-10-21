import Phaser from 'phaser';
import type { Actor, AdventureIR } from './types';
import { AdventureState } from './state';
import {preloadArt,registerAnimations,applyAsset,animateActor,actorVisual,terrainFrames} from './art';

type Sprite = Phaser.Physics.Arcade.Sprite;
type LiveActor = { data:Actor; sprite:Sprite; health:number; homeX:number; homeY:number };

/** Genre adapter: zero gravity, tile collisions, persistent state across area scenes. */
export class AdventureScene extends Phaser.Scene {
  spec!: AdventureIR;
  state!: AdventureState;
  player!: Sprite;
  actors: LiveActor[]=[];
  keys!: Record<string,Phaser.Input.Keyboard.Key>;
  touch:Record<string,boolean>={};
  touched=new Set<string>();
  facing=new Phaser.Math.Vector2(1,0);
  hud!: Phaser.GameObjects.Text;
  hint!: Phaser.GameObjects.Text;
  dialog!: Phaser.GameObjects.Text;
  objectiveMarker!: Phaser.GameObjects.Text;
  compass!: Phaser.GameObjects.Text;
  dialogue:string[]=[];
  shots!: Phaser.Physics.Arcade.Group;
  lastAttack=0;
  lastDamage=0;
  generation=0;
  constructor() { super('Adventure'); }
  init(data:{spec:AdventureIR;state?:AdventureState;generation?:number}) {
    this.spec=data.spec;this.state=data.state||new AdventureState(this.spec);
    this.generation=(data.generation||0)+1;
    this.actors=[];this.dialogue=[];this.touch={};this.touched=new Set();this.lastAttack=0;this.lastDamage=0;
  }
  preload() {
    if(this.spec.art){preloadArt(this,this.spec.art);return;}
    for (const name of ['tiny-town','tiny-dungeon'])
      if (!this.textures.exists(name)) this.load.spritesheet(name,`/assets/adventure/${name}.png`,{frameWidth:16,frameHeight:16});
  }
  create() {
    const area=this.spec.areas[this.state.area],size=32,outdoor=['forest','village'].includes(area.environment);
    const art=this.spec.art;
    if(art)registerAnimations(this,art);
    this.cameras.main.setBackgroundColor(outdoor?'#5c8e55':'#211e30');
    const tiles=art?terrainFrames(art,area,this.spec.seed):area.tiles.map(row=>row.map(v=>outdoor ? v===1?4:v>=10?48+Math.floor((v-10)/3)*12+(v-10)%3:v===2?25:v===3?2:0 : v===1?14:v===3?24:this.spec.theme==='dark'?0:48));
    const map=this.make.tilemap({data:tiles,tileWidth:16,tileHeight:16});
    const tileSet=map.addTilesetImage(art?.terrain.texture||(outdoor?'tiny-town':'tiny-dungeon'))!;
    const layer=map.createLayer(0,tileSet)!.setScale(2);
    if(this.spec.theme==='dark')layer.setTint(0xb7a8c2);
    // Per-tile properties keep collision independent from visual frame IDs.
    layer.forEachTile(tile=>{if ([1,4].includes(area.tiles[tile.y][tile.x])||area.tiles[tile.y][tile.x]>=13) tile.setCollision(true,true,true,true);});
    // Each complete house has one footprint depth so actors can pass behind its roof.
    if(art)for(const b of area.buildings||[]){
      const frames=art.terrain.buildings[b.variant%art.terrain.buildings.length];
      if(!frames)continue;
      for(let dy=0;dy<3;dy++)for(let dx=0;dx<3;dx++)
        this.add.image((b.x+dx)*32+16,(b.y+dy)*32+16,art.terrain.texture,frames[dy*3+dx]).setScale(2).setDepth((b.y+2)*32+31);
    }
    // Render saved older worlds too; their house modules are encoded in tile values.
    if(art&&!area.buildings?.length)for(let y=0;y<area.height;y++)for(let x=0;x<area.width;x++){
      const v=area.tiles[y][x];if(v<10)continue;
      const frames=art.terrain.buildings[this.spec.seed%art.terrain.buildings.length];
      if(frames)this.add.image(x*32+16,y*32+16,art.terrain.texture,frames[v-10]).setScale(2).setDepth((y+2-Math.floor((v-10)/3))*32+31);
    }
    this.physics.world.setBounds(0,0,area.width*size,area.height*size);
    this.player=this.physics.add.sprite(area.spawn.x*size+16,area.spawn.y*size+16,art?.player||'tiny-dungeon',art?0:96).setScale(2).setDepth(10).setCollideWorldBounds(true);
    if(art)applyAsset(this.player,art.assets[art.player]);else this.player.setSize(9,9).setOffset(3,6);
    this.physics.add.collider(this.player,layer);
    const enemies=this.physics.add.group();
    // These sprites already have dynamic Arcade bodies; retain that body type in
    // the collision group (a static group would query the wrong spatial tree).
    const doors=this.physics.add.group({immovable:true,allowGravity:false});
    for (const actor of area.actors) {
      const herb=actor.kind==='item'&&/herb|leaf|mint|blossom|flower/i.test(actor.item+' '+actor.name);
      const key=actor.kind==='item'&&/key/i.test(actor.item+' '+actor.name);
      const frame=actor.kind==='npc'?(actor.role==='healer'?84:88):actor.kind==='item'?(herb?2:key?117:116):actor.kind==='enemy'?(actor.behavior==='patrol'?110:121):actor.kind==='switch'?32:actor.kind==='door'?45:actor.kind==='treasure'?89:20;
      const copies=actor.kind==='item'?actor.quantity:1;
      for (let i=0;i<copies;i++) {
        const instance=actor.kind==='item'?`${actor.id}:${i}`:actor.id;
        if (this.state.removed.has(instance)||this.state.defeated.has(actor.id)) continue;
        const position=actor.pickups?.[i]||actor;
        const x=position.x*size+16,y=position.y*size+16;
        const visual=art?actorVisual(art,actor):null;
        const sprite=this.physics.add.sprite(x,y,visual?.asset.id||(herb||key?'tiny-town':'tiny-dungeon'),visual?.frame??frame).setScale(2).setDepth(5).setImmovable(true);
        if(visual){applyAsset(sprite,visual.asset,visual.frame);animateActor(sprite,visual.asset,0,0);}
        sprite.setData('instance',instance);
        const live={data:actor,sprite,health:2,homeX:x,homeY:y};this.actors.push(live);
        if (actor.kind==='enemy') {
          enemies.add(sprite);sprite.setImmovable(false).setCollideWorldBounds(true);
          if(!visual)sprite.setSize(10,10);
        } else if (actor.kind==='door') {
          if(this.state.unlocked.has(actor.id))sprite.setFrame(art?.roles.door.open_frame??33).setAlpha(.5);
          else doors.add(sprite);
        } else if(actor.kind==='switch'&&this.state.activated.has(actor.id)&&art?.roles.switch.open_frame!=null){
          sprite.setFrame(art.roles.switch.open_frame);
        } else if(actor.kind==='item') {
          this.physics.add.overlap(this.player,sprite,()=>{
            this.state.pickup(actor,instance);this.toast(x,y,`+1 ${actor.name}`);sprite.destroy();this.refresh();
          });
        }
        if(actor.kind==='npc')this.physics.add.collider(this.player,sprite);
        if(actor.kind==='npc'||actor.kind==='landmark')this.add.text(x,y-30,actor.name,{fontSize:'12px',fontFamily:'monospace',color:'#ffffff',backgroundColor:'#172231cc',padding:{x:4,y:3}}).setOrigin(.5).setDepth(2100);
      }
    }
    this.physics.add.collider(enemies,layer);this.physics.add.collider(enemies,doors);this.physics.add.collider(this.player,doors);
    this.shots=this.physics.add.group({allowGravity:false});
    this.physics.add.collider(this.shots,layer,shot=>shot.destroy());
    this.physics.add.collider(this.shots,doors,shot=>shot.destroy());
    this.physics.add.overlap(this.shots,enemies,(shot,enemy)=>{
      const target=this.actors.find(a=>a.sprite===enemy);
      shot.destroy();
      if(target && --target.health<=0){this.state.defeat(target.data.id);this.effect(target.sprite.x,target.sprite.y);target.sprite.destroy();this.refresh();}
      else if(target){target.sprite.setTint(0xffb5b5);this.time.delayedCall(150,()=>{if(target.sprite.active)target.sprite.clearTint();});}
    });
    this.physics.add.overlap(this.player,enemies,()=>{
      if(this.time.now-this.lastDamage<1000||this.state.lost||this.state.won||this.dialogue.length)return;
      this.lastDamage=this.time.now;this.state.health--;this.player.setTint(0xff7777);
      this.time.delayedCall(250,()=>this.player.clearTint());
      if(this.state.health<=0)this.state.lost=true;this.refresh();
    });
    const exitArt=art?.roles.exit;
    this.add.sprite(area.exit.x*size+16,area.exit.y*size+16,exitArt?.asset||'tiny-dungeon',exitArt?.frame??44).setScale(exitArt?art!.assets[exitArt.asset].scale:2).setDepth(5);
    if(art&&outdoor&&art.roles.tree){
      const tree=art.assets[art.roles.tree.asset];
      for(const p of area.trees||[])
        this.add.image(p.x*32+16,p.y*32+25,tree.id).setScale(tree.scale).setOrigin(.5,1).setDepth(p.y*32+30);
    }
    for(const zone of area.zones||[])
      this.add.text(zone.x*32+16,zone.y*32-60,zone.name,{fontSize:'11px',fontFamily:'monospace',color:outdoor?'#e9f4c0':'#cfc0dc',backgroundColor:'#17223199',padding:{x:5,y:3}}).setOrigin(.5).setDepth(2100);
    const marker=this.add.text(area.exit.x*size+16,area.exit.y*size-18,this.state.area<this.spec.areas.length-1?'NEXT AREA · E':'EXIT · E',{fontSize:'12px',color:'#ffe5a6',backgroundColor:'#172231cc',padding:{x:4,y:3}}).setOrigin(.5).setDepth(6);
    this.tweens.add({targets:marker,alpha:.5,yoyo:true,repeat:-1,duration:900});
    this.cameras.main.setBounds(0,0,area.width*size,area.height*size).startFollow(this.player,true,.14,.14);
    this.hud=this.add.text(20,16,'',{fontFamily:'monospace',fontSize:'15px',color:'#fff4d9',backgroundColor:'#172231ee',padding:{x:14,y:10},wordWrap:{width:610}}).setScrollFactor(0).setDepth(3000);
    this.hint=this.add.text(20,466,'WASD / arrows · move    E · talk / use    R · restart',{fontFamily:'monospace',fontSize:'15px',color:'#ffffff',backgroundColor:'#172231ee',padding:{x:10,y:8},wordWrap:{width:880}}).setScrollFactor(0).setDepth(3000);
    this.dialog=this.add.text(80,340,'',{fontFamily:'monospace',fontSize:'18px',color:'#fff4d9',backgroundColor:'#172231f5',padding:{x:20,y:16},wordWrap:{width:750}}).setScrollFactor(0).setDepth(3001).setVisible(false);
    this.objectiveMarker=this.add.text(0,0,'◆',{fontSize:'22px',color:'#ffe09a',stroke:'#172231',strokeThickness:4}).setOrigin(.5).setDepth(2200);
    this.compass=this.add.text(20,116,'',{fontFamily:'monospace',fontSize:'14px',color:'#ffe09a',backgroundColor:'#172231dd',padding:{x:8,y:6}}).setScrollFactor(0).setDepth(3000);
    this.keys=this.input.keyboard!.addKeys('UP,DOWN,LEFT,RIGHT,W,A,S,D,E,F,X,R,SPACE') as typeof this.keys;
    this.events.on('touch-control',(key:string,pressed:boolean)=>{this.touch[key]=pressed;if(!pressed)this.touched.delete(key);});
    this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>this.events.removeAllListeners('touch-control'));
    if(new URLSearchParams(location.search).get('test')==='1') {
      const hook={
        snapshot:()=>this.snapshot(),
        teleport:(x:number,y:number)=>{this.player.setPosition(x,y).setVelocity(0,0);},
        restart:()=>{this.scene.restart({spec:this.spec,generation:this.generation});},
      };
      Object.assign(window,{__AETHER_ADVENTURE__:hook});
      const removeHook=()=>{
        const testing=window as Window & {__AETHER_ADVENTURE__?:typeof hook};
        if(testing.__AETHER_ADVENTURE__===hook)delete testing.__AETHER_ADVENTURE__;
      };
      this.events.once(Phaser.Scenes.Events.SHUTDOWN,removeHook);
      this.events.once(Phaser.Scenes.Events.DESTROY,removeHook);
    }
    this.refresh();
    this.toast(this.player.x,this.player.y-40,`You · ${outdoor?'explore the paths':'enter the depths'}`);
  }
  snapshot() {
    if(!this.physics?.world||!this.player?.body)return {ready:false,generation:this.generation};
    return {ready:true,generation:this.generation,genre:'adventure',area:this.state.area,x:this.player.x,y:this.player.y,
      vx:this.player.body?.velocity.x,vy:this.player.body?.velocity.y,gravity:this.physics.world.gravity.y,
      inventory:this.state.inventory,quests:this.state.states,objective:this.state.objective,health:this.state.health,
      won:this.state.won,lost:this.state.lost,dialogue:this.dialogue,unlocked:[...this.state.unlocked],activated:[...this.state.activated],
      actors:this.actors.filter(a=>a.sprite.active).map(a=>({id:a.data.id,kind:a.data.kind,x:a.sprite.x,y:a.sprite.y,health:a.health,
        body:a.sprite.body?{x:a.sprite.body.x,y:a.sprite.body.y,width:a.sprite.body.width,height:a.sprite.body.height,enabled:a.sprite.body.enable}:null})),
      assetPack:this.spec.art?.pack_id||'kenney_tiny',playerTexture:this.player.texture.key,playerFrame:this.player.frame.name,animation:this.player.anims.currentAnim?.key,
      selectedAssets:this.spec.art?Object.keys(this.spec.art.assets):['tiny-town','tiny-dungeon'],
      missingAssets:(this.spec.art?Object.keys(this.spec.art.assets):['tiny-town','tiny-dungeon']).filter(k=>!this.textures.exists(k))};
  }
  toast(x:number,y:number,message:string) {
    const text=this.add.text(x,y-25,message,{fontSize:'14px',fontFamily:'monospace',color:'#fff4c0',backgroundColor:'#172231ee',padding:{x:6,y:4}}).setOrigin(.5).setDepth(2400);
    this.tweens.add({targets:text,y:text.y-24,alpha:0,delay:700,duration:800,onComplete:()=>text.destroy()});
  }
  effect(x:number,y:number) {
    const role=this.spec.art?.roles.vfx;if(!role)return;
    const key=`${role.asset}:effect`;
    if(!this.anims.exists(key))this.anims.create({key,frames:this.anims.generateFrameNumbers(role.asset),frameRate:14,repeat:0});
    this.add.sprite(x,y,role.asset).setDepth(2300).play(key).once('animationcomplete',function(this:Phaser.GameObjects.Sprite){this.destroy();});
  }
  refresh() {
    const s=this.state;
    this.hud.setText(`${this.spec.areas[s.area].name}   ·   ${this.spec.combat?`${s.health}/5 hearts`:'Exploration'}   ·   Quest ${s.completed.filter(Boolean).length}/${s.completed.length}\n${s.won?'ADVENTURE COMPLETE! Press R to play again.':s.lost?'You fell in battle. Press R to restart.':s.objective}\nInventory: ${Object.entries(s.inventory).filter(([,n])=>n>0).map(([k,n])=>`${k} ×${n}`).join('   ')||'empty'}`);
    this.emitUI();
  }
  emitUI() {
    const s=this.state;
    this.game.events.emit('adventure-ui',{
      objective:s.won?'Adventure complete! Press R to play again.':s.lost?'You fell in battle. Press R to restart.':s.objective,
      inventory:Object.entries(s.inventory).filter(([,n])=>n>0).map(([k,n])=>`${k} ×${n}`).join(', ')||'empty',
      dialogue:this.dialogue[0]||'',health:s.health,progress:`${s.completed.filter(Boolean).length}/${s.completed.length}`,
    });
  }
  pressed(key:string,touch=key.toLowerCase()) {
    const keyboard=Phaser.Input.Keyboard.JustDown(this.keys[key]);
    if(this.touch[touch]&&!this.touched.has(touch)){this.touched.add(touch);return true;}
    return keyboard;
  }
  showDialogue(lines:string[],name='') {
    this.dialogue=lines.map((s,i)=>i===0&&name?`${name}\n${s}`:s);this.advanceDialogue(false);
  }
  advanceDialogue(shift=true) {
    if(shift)this.dialogue.shift();
    this.dialog.setVisible(this.dialogue.length>0);
    if(this.dialogue.length)this.dialog.setText(`${this.dialogue[0]}\n\nE · continue`);
    this.emitUI();
  }
  update(time:number) {
    if(!this.player||!this.keys)return;
    this.player.setDepth(this.player.y);
    for(const a of this.actors)if(a.sprite.active)a.sprite.setDepth(a.sprite.y);
    const goal=this.spec.quests[this.state.current];
    const target=this.actors.filter(a=>a.sprite.active&&a.data.id===goal?.target).sort((a,b)=>Phaser.Math.Distance.Between(this.player.x,this.player.y,a.sprite.x,a.sprite.y)-Phaser.Math.Distance.Between(this.player.x,this.player.y,b.sprite.x,b.sprite.y))[0];
    const targetX=target?.sprite.x??this.spec.areas[this.state.area].exit.x*32+16;
    const targetY=target?.sprite.y??this.spec.areas[this.state.area].exit.y*32+16;
    this.objectiveMarker.setPosition(targetX,targetY-39+Math.sin(time/220)*3).setVisible(!this.state.won&&!this.state.lost);
    const mx=targetX-this.player.x,my=targetY-this.player.y;
    this.compass.setText(`${my<-30?'↑ ':my>30?'↓ ':''}${mx<-30?'← ':mx>30?'→ ':''}${Math.round(Math.hypot(mx,my)/32)} tiles to ${target?.data.name||'exit'}`);
    const focused=this.game.canvas.parentElement?.contains(document.activeElement);
    if(!focused){this.player.setVelocity(0);this.actors.filter(a=>a.data.kind==='enemy'&&a.sprite.active).forEach(a=>a.sprite.setVelocity(0));return;}
    if(this.pressed('R','restart')){this.scene.restart({spec:this.spec,generation:this.generation});return;}
    const use=this.pressed('E','interact');
    if(this.state.won||this.state.lost){this.player.setVelocity(0);this.actors.filter(a=>a.data.kind==='enemy'&&a.sprite.active).forEach(a=>a.sprite.setVelocity(0));return;}
    if(this.dialogue.length){this.player.setVelocity(0);this.actors.filter(a=>a.data.kind==='enemy'&&a.sprite.active).forEach(a=>a.sprite.setVelocity(0));if(use)this.advanceDialogue();return;}
    const dx=Number(this.keys.RIGHT.isDown||this.keys.D.isDown||!!this.touch.right)-Number(this.keys.LEFT.isDown||this.keys.A.isDown||!!this.touch.left);
    const dy=Number(this.keys.DOWN.isDown||this.keys.S.isDown||!!this.touch.down)-Number(this.keys.UP.isDown||this.keys.W.isDown||!!this.touch.up);
    const velocity=new Phaser.Math.Vector2(dx,dy).normalize().scale(155);this.player.setVelocity(velocity.x,velocity.y);
    if(dx||dy)this.facing.set(dx,dy).normalize();
    if(this.spec.art)animateActor(this.player,this.spec.art.assets[this.spec.art.player],velocity.x,velocity.y,time-this.lastAttack<130);
    else if(dx||dy){this.player.setFlipX(dx<0).setAngle(Math.sin(time/85)*4).setScale(2,2+Math.sin(time/70)*.045);}
    else this.player.setAngle(0).setScale(2);
    const near=this.actors.filter(a=>a.sprite.active&&a.data.kind!=='item'&&a.data.kind!=='enemy'&&!(a.data.kind==='door'&&this.state.unlocked.has(a.data.id))&&!(a.data.kind==='treasure'&&this.state.removed.has(a.data.id)))
      .sort((a,b)=>Phaser.Math.Distance.Between(this.player.x,this.player.y,a.sprite.x,a.sprite.y)-Phaser.Math.Distance.Between(this.player.x,this.player.y,b.sprite.x,b.sprite.y))[0];
    const distance=near?Phaser.Math.Distance.Between(this.player.x,this.player.y,near.sprite.x,near.sprite.y):Infinity;
    const area=this.spec.areas[this.state.area],atExit=Phaser.Math.Distance.Between(this.player.x,this.player.y,area.exit.x*32+16,area.exit.y*32+16)<55;
    this.hint.setText(distance<58?`E · ${near.data.kind==='npc'?'Talk to':'Use'} ${near.data.name}`:atExit?'E · enter the passage':'WASD / arrows · move    E · interact'+(this.spec.combat?'    F / X · attack':'')+'    R · restart');
    if(near?.data.kind==='landmark'&&distance<50&&!this.state.explored.has(near.data.id)){this.state.explore(near.data.id);this.refresh();}
    if(use){
      if(distance<58){
        const lines=this.state.interact(near.data);
        if(near.data.kind==='door'&&this.state.unlocked.has(near.data.id)){
          (near.sprite.body as Phaser.Physics.Arcade.Body).enable=false;near.sprite.setFrame(this.spec.art?.roles.door.open_frame??33).setAlpha(.5);
        }
        if(near.data.kind==='switch'&&this.spec.art?.roles.switch.open_frame!=null)near.sprite.setFrame(this.spec.art.roles.switch.open_frame);
        if(near.data.kind==='treasure'){near.sprite.destroy();}
        this.showDialogue(lines,near.data.name);this.refresh();
      } else if(atExit){
        if(this.state.leave()){
          if(!this.state.won)this.scene.restart({spec:this.spec,state:this.state,generation:this.generation});else this.refresh();
        }else this.showDialogue(['Complete the objectives in this area before leaving.']);
      }
    }
    if(this.spec.combat && (this.pressed('F','attack')||this.pressed('X')) && time-this.lastAttack>260){
      this.lastAttack=time;
      const projectile=this.spec.art?.roles.projectile;
      const origin=this.spec.art?this.player.body!.center:this.player;
      const shot=this.shots.create(origin.x+this.facing.x*18,origin.y+this.facing.y*18,projectile?.asset||'tiny-dungeon',projectile?.frame??116) as Sprite;
      shot.setScale(projectile?this.spec.art!.assets[projectile.asset].scale:1.5).setDepth(2300).setVelocity(this.facing.x*360,this.facing.y*360);
      this.time.delayedCall(1200,()=>{if(shot.active)shot.destroy();});
    }
    for(const a of this.actors){
      if(a.data.kind!=='enemy'||!a.sprite.active)continue;
      const distance=Phaser.Math.Distance.Between(a.sprite.x,a.sprite.y,this.player.x,this.player.y);
      if(distance<220){this.physics.moveToObject(a.sprite,this.player,66);}
      else if(a.data.behavior==='patrol'){
        const tx=a.homeX+Math.sin(time/1600)*65;
        this.physics.moveTo(a.sprite,tx,a.homeY,40);
      }else a.sprite.setVelocity(0);
      if(this.spec.art)animateActor(a.sprite,this.spec.art.assets[this.spec.art.actors[a.data.id]],a.sprite.body?.velocity.x||0,a.sprite.body?.velocity.y||0);
      else a.sprite.setFlipX((a.sprite.body?.velocity.x||0)<0);
    }
  }
}
