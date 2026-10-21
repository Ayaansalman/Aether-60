import Phaser from "phaser";
import type { PlatformerIR, Platform, Entity } from "./types";
import { iciclePhase, enemyDecision, indicatorAnimation, exitDecision, resolveLevel } from "./behaviors";
import type { IcicleState } from "./behaviors";
import registry from "../../../public/assets/registry.json";

export class PlatformerScene extends Phaser.Scene {
  spec!: PlatformerIR;
  campaign!: PlatformerIR;
  levelIndex = 0;
  exits: Phaser.GameObjects.Sprite[] = [];
  traps: { sprite: Phaser.Physics.Arcade.Sprite; spec: Entity; state: IcicleState; at: number; activations: number }[] = [];
  machines: { sprite: Phaser.Physics.Arcade.Sprite; spec: Entity; active: boolean }[] = [];
  projectiles: Phaser.Physics.Arcade.Group | undefined;
  shotsFired = 0;
  messageUntil = 0;
  hero!: Phaser.Physics.Arcade.Sprite;
  keys!: Record<string, Phaser.Input.Keyboard.Key>;
  health = 3;
  crystals = 0;
  state = "playing";
  checkpoint = -1;
  spawn = { x: 90, y: 400 };
  jumps = 0;
  groundedAt = -1000;
  jumpAt = -1000;
  hurtAt = -2000;
  dashAt = -2000;
  facing = 1;
  hud!: Phaser.GameObjects.Text;
  message!: Phaser.GameObjects.Text;
  enemies: {
    sprite: Phaser.Physics.Arcade.Sprite;
    platform: Platform;
    direction: number;
    behavior: string;
    shotAt: number;
  }[] = [];
  moving: { sprite: Phaser.Physics.Arcade.Sprite; x: number; phase: number; motion: boolean }[] =
    [];
  missingAssets: string[] = [];
  touch: Record<string, boolean> = {
    left: false,
    right: false,
    jump: false,
    dash: false,
  };
  generation = 0;
  landedPlatforms = new Set<number>();
  constructor() {
    super("Platformer");
  }
  init(data: { spec: PlatformerIR; levelIndex?: number }) {
    this.campaign = data.spec;
    this.levelIndex = data.levelIndex || 0;
    this.spec = resolveLevel(data.spec, this.levelIndex);
    this.exits = [];
    this.traps = [];
    this.machines = [];
    this.shotsFired = 0;
    this.messageUntil = 0;
    this.health = this.spec.player.health;
    this.crystals = 0;
    this.state = "playing";
    this.generation++;
    this.landedPlatforms = new Set<number>();
    this.checkpoint = -1;
    this.spawn = { ...this.spec.spawn };
    this.jumps = 0;
    this.hurtAt = -2000;
    this.dashAt = -2000;
    this.groundedAt = -1000;
    this.jumpAt = -1000;
    this.enemies = [];
    this.moving = [];
    this.missingAssets = [];
    this.touch = { left: false, right: false, jump: false, dash: false };
  }
  preload() {
    for (const [key, texture] of Object.entries(registry.textures)) {
      this.load.spritesheet(key, texture.url, {
        frameWidth: texture.frameWidth,
        frameHeight: texture.frameHeight,
      });
    }
    for (const [key, url] of Object.entries(registry.backgrounds))
      this.load.image(`bg-${key}`, url);
    this.load.on("loaderror", (file: Phaser.Loader.File) =>
      this.missingAssets.push(file.key),
    );
  }
  create() {
    this.physics.resume();
    const s = this.spec,
      industrial = s.theme === "industrial",
      ice = s.theme === "ice",
      roles = registry.roles;
    this.physics.world.gravity.y = s.player.gravity;
    this.physics.world.setBounds(0, 0, s.width, s.height + 200);
    const camera = this.cameras.main;
    camera.setBounds(0, 0, s.width, s.height);
    camera.setBackgroundColor(s.theme === "twilight" ? "#505475" : "#b8dbd0");
    if (ice && !this.textures.exists("ice")) {
      // Original procedural ice blocks: no grass silhouette or foliage is reused.
      const art = this.make.graphics({ x: 0, y: 0 });
      for (let i = 0; i < 20; i++) {
        const x = i * 18;
        art.fillStyle(i < 3 ? 0x9ce5ef : 0x335d86).fillRect(x, 0, 18, 18);
        art.fillStyle(i < 3 ? 0xe2ffff : 0x45769b).fillRect(x, 0, 18, 3);
        art.lineStyle(1, 0x70b2cd, .7).lineBetween(x+3, 6, x+12, 16);
      }
      art.generateTexture("ice", 360, 18);
      art.destroy();
      this.textures.addSpriteSheet("ice", this.textures.get("ice"), {frameWidth:18, frameHeight:18});
    }
    if (!this.textures.exists("icicle")) {
      const art = this.make.graphics({x:0,y:0});
      art.fillStyle(0xc4faff).fillTriangle(0,0,24,0,12,48);
      art.fillStyle(0x659fca).fillTriangle(12,0,24,0,12,48);
      art.generateTexture("icicle",24,48); art.destroy();
    }
    for (const style of ["shrine", "gate", "beacon"]) {
      if (this.textures.exists(`exit-${style}`)) continue;
      const art=this.make.graphics({x:0,y:0});
      const stone=style==="shrine"?0x698b7e:style==="beacon"?0x4e7894:0x586578;
      art.fillStyle(stone).fillRect(1,26,22,4).fillRect(3,10,4,16).fillRect(17,10,4,16);
      if(style==="shrine")art.fillTriangle(0,10,24,10,12,1);
      else art.fillRect(3,4,18,6);
      art.fillStyle(style==="beacon"?0xb9faff:0xffeab0).fillRect(9,12,6,10);
      art.fillStyle(0xe2f7e9).fillRect(5,10,1,14).fillRect(19,10,1,14);
      art.generateTexture(`exit-${style}`,24,30);art.destroy();
    }
    if(!this.textures.exists("relic")){
      const art=this.make.graphics({x:0,y:0});
      art.fillStyle(0x604b64).fillRect(4,1,10,16);
      art.fillStyle(0xe9c77b).fillRect(3,3,12,12);
      art.lineStyle(2,0x506785).strokeRect(6,6,6,6).lineBetween(9,4,9,14);
      art.generateTexture("relic",18,18);art.destroy();
    }
    const background = this.add
      .tileSprite(0, 0, 960, 540, `bg-${ice ? "twilight" : s.theme}`)
      .setOrigin(0)
      .setScrollFactor(0)
      .setDepth(-10);
    background.setTileScale(8, 8);
    if (s.theme === "twilight") background.setTint(0x8a8ebd);
    if (ice) {
      background.setVisible(false);
      camera.setBackgroundColor(s.topology === 'journey' ? '#244b65' : s.topology === 'ascent' ? '#142b49' : '#101d37');
      const cave = this.add.graphics().setDepth(-8).setScrollFactor(.35, .45);
      for (let x = 0; x < s.width; x += 170) {
        const height = 70 + ((x * 7 + this.levelIndex * 53) % 150);
        cave.fillStyle(0x213f64).fillTriangle(x,0,x+160,0,x+80,height+120);
        cave.fillStyle(0x315b7c).fillTriangle(x+30,500,x+100,500,x+75,300-height/3);
        cave.fillStyle(0x83d3e5,.45).fillTriangle(x+60,460,x+95,460,x+80,390);
      }
    }
    const tiles = this.make.tilemap({
      tileWidth: 18,
      tileHeight: 18,
      width: Math.ceil(s.width / 36),
      height: Math.ceil(s.height / 36),
    });
    const texture = industrial ? "industrial" : ice ? "ice" : "terrain";
    const set = tiles.addTilesetImage(texture, texture, 18, 18, 0, 0)!;
    const layer = tiles.createBlankLayer("world", set)!.setScale(2);
    for (const p of s.platforms) {
      if (p.moving || p.route === "optional") {
        const obj = this.physics.add
          .sprite(
            (p.x + p.width / 2) * 36,
            p.y * 36 + 9,
            texture,
            industrial ? roles.moving_industrial : ice ? 1 : roles.moving_forest,
          )
          .setDisplaySize(p.width * 36, 18);
        obj.setImmovable(true).setGravityY(-s.player.gravity);
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.up = true;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.down = false;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.left = false;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.right = false;
        this.moving.push({ sprite: obj, x: obj.x, phase: p.x, motion: p.moving });
        continue;
      }
      for (let x = p.x; x < p.x + p.width; x++) {
        const top =
          (industrial ? roles.industrial_ground : ice ? 0 : roles.forest_ground) +
          (x === p.x ? 0 : x === p.x + p.width - 1 ? 2 : 1);
        tiles.putTileAt(top, x, p.y, false, layer);
        for (let y = p.y + 1; y < (p.kind === "bridge" || p.kind === "ruins" ? p.y + 2 : Math.ceil(s.height / 36)); y++)
          tiles.putTileAt(
            industrial
              ? roles.industrial_fill
              : ice ? 4 + ((x+y)%2) : roles.forest_fill + ((x + y) % 2),
            x,
            y,
            false,
            layer,
          );
      }
      if (ice) {
        const decor = this.add.graphics().setDepth(-2);
        const x = (p.x + p.width - 1)*36, y = p.y*36;
        decor.fillStyle(0x7fdcea,.8).fillTriangle(x-15,y,x+16,y,x+3,y-65);
        decor.fillStyle(0xd5fcff).fillTriangle(x+3,y,x+16,y,x+3,y-65);
      } else if (!industrial) {
        // Trees, flowers, stonework and signposts use the same authored tiles as terrain.
        for (let x = p.x + 1; x < p.x + p.width - 1; x += 3) {
          this.add
            .image(
              x * 36 + 18,
              p.y * 36 - 18,
              "terrain",
              p.kind === "ruins"
                ? roles.forest_ruins
                : roles.forest_props[x % roles.forest_props.length],
            )
            .setScale(2);
          if (x % 2 === 0) {
            this.add
              .image(x * 36 + 18, p.y * 36 - 30, "terrain", roles.tree_trunk)
              .setScale(3)
              .setDepth(-2);
            this.add
              .image(x * 36 + 18, p.y * 36 - 65, "terrain", roles.tree_crown)
              .setScale(5)
              .setDepth(-2)
              .setTint(0x88bc9b);
          }
        }
      } else {
        this.add
          .image(
            (p.x + 1) * 36,
            p.y * 36 - 36,
            "industrial",
            roles.industrial_prop,
          )
          .setScale(4)
          .setDepth(-2);
        this.add
          .image(
            (p.x + p.width - 1) * 36,
            p.y * 36 - 18,
            "industrial",
            roles.industrial_sign,
          )
          .setScale(2);
      }
    }
    layer.setCollisionByExclusion([-1]);
    this.hero = this.physics.add
      .sprite(
        this.spawn.x,
        this.spawn.y,
        "characters",
        registry.animations.idle[0],
      )
      .setScale(2);
    this.hero
      .setSize(12, 19)
      .setOffset(6, 5)
      .setMaxVelocity(650, 900)
      .setDragX(2000)
      .setCollideWorldBounds(true);
    this.physics.add.collider(this.hero, layer);
    this.moving.forEach((p) => this.physics.add.collider(this.hero, p.sprite));
    for (const [name, frames] of Object.entries({
      idle: registry.animations.idle,
      run: registry.animations.run,
      jump: registry.animations.jump,
      fall: registry.animations.fall,
    })) {
      if (!this.anims.exists(name))
        this.anims.create({
          key: name,
          frames: frames.map((frame) => ({ key: "characters", frame })),
          frameRate: 9,
          repeat: -1,
        });
    }
    this.projectiles = this.physics.add.group({allowGravity:false});
    this.physics.add.collider(this.projectiles, layer, (bullet) => bullet.destroy());
    this.physics.add.overlap(this.hero, this.projectiles, (_hero, bullet) => {this.damage(); bullet.destroy();});
    for (const e of s.entities) {
      if (e.kind === "icicle") {
        const obj = this.physics.add.sprite(e.x,e.y,"icicle");
        const body = obj.body as Phaser.Physics.Arcade.Body;
        body.setAllowGravity(false);
        this.traps.push({sprite:obj,spec:e,state:"waiting",at:this.time.now,activations:0});
        this.physics.add.collider(obj,layer,()=>{
          const trap=this.traps.find(t=>t.sprite===obj)!;
          if (trap.state === "falling") { trap.state="spent"; trap.at=this.time.now; obj.disableBody(true,true); this.burst(obj.x,obj.y,0x9eefff); }
        });
        this.physics.add.overlap(this.hero,obj,()=>{
          if (this.traps.find(t=>t.sprite===obj)?.state==="falling") this.damage();
        });
        continue;
      }
      if (e.kind === "timed_hazard") {
        const obj=this.physics.add.staticSprite(e.x,e.y,"industrial",roles.industrial_prop).setScale(2).refreshBody();
        this.machines.push({sprite:obj,spec:e,active:false});
        this.physics.add.overlap(this.hero,obj,()=>{if(this.machines.find(m=>m.sprite===obj)?.active)this.damage();});
        continue;
      }
      if (e.kind === "enemy") {
        const obj = this.physics.add
          .sprite(
            e.x,
            e.y,
            "characters",
            (industrial ? roles.enemy_industrial : roles.enemy_forest)[0],
          )
          .setScale(1.7);
        obj.setSize(14, 17).setOffset(5, 6);
        this.physics.add.collider(obj, layer);
        this.enemies.push({
          sprite: obj,
          platform: s.platforms[e.platform],
          direction: -1,
          behavior: e.behavior || "patrol",
          shotAt: this.time.now,
        });
        if (e.behavior === "shooter") obj.setTint(0xffb56a);
        if (e.behavior === "chase") obj.setTint(0xeaa0db);
        this.physics.add.overlap(this.hero, obj, () => {
          const body = this.hero.body as Phaser.Physics.Arcade.Body;
          if (body.velocity.y > 70 && this.hero.y < obj.y - 12) {
            obj.destroy();
            this.hero.setVelocityY(-300);
            this.burst(obj.x, obj.y, 0xf7ca72);
          } else this.damage();
        });
        continue;
      }
      const frame =
        e.kind === "crystal"
          ? roles.crystal
          : e.kind === "spikes"
            ? roles.spikes
            : e.kind === "checkpoint"
              ? roles.checkpoint
              : roles.exit;
      const obj = this.physics.add
        .staticSprite(e.x, e.y, e.kind === "exit" ? `exit-${s.exit_style || "gate"}` : e.kind === "crystal" && s.collectible === "relics" ? "relic" : "terrain", e.kind === "exit" || e.kind === "crystal" && s.collectible === "relics" ? undefined : frame)
        .setScale(e.kind === "exit" ? 3 : 2)
        .refreshBody();
      if (e.kind === "exit") {
        this.exits.push(obj);
        const animation = indicatorAnimation(s.exit_indicator);
        if (animation) {
          const glow = this.add.circle(e.x,e.y,42,ice ? 0x8ef7ff : 0xf8eab0,.35).setDepth(-1);
          this.tweens.add({targets:[glow,obj],...animation,yoyo:true,repeat:-1,ease:"Sine.inOut"});
        }
      }
      if (e.kind === "crystal")
        this.tweens.add({
          targets: obj,
          y: obj.y - 7,
          duration: 1000,
          yoyo: true,
          repeat: -1,
          ease: "Sine.inOut",
          onUpdate: () => { if (obj.active && obj.body) obj.refreshBody(); },
        });
      this.physics.add.overlap(this.hero, obj, () => {
        if (this.state !== "playing") return;
        if (e.kind === "crystal") {
          this.crystals++;
          this.burst(obj.x, obj.y, 0x7ee1ef);
          obj.destroy();
        } else if (e.kind === "spikes") this.damage();
        else if (e.kind === "checkpoint" && this.checkpoint !== e.platform) {
          this.checkpoint = e.platform;
          this.spawn = { x: e.x, y: e.y - 25 };
          obj.setTint(0x8effb2);
          this.burst(e.x, e.y, 0x91efb8);
        } else if (e.kind === "exit") {
          const action=exitDecision(this.levelIndex,this.campaign.levels?.length || 1,this.crystals,s.objective.required);
          if (action !== "locked") {
            if (action === "next") {
              this.state = "transitioning";
              this.hero.setVelocity(0);
              this.physics.pause();
              this.message.setText(`Level ${this.levelIndex+1} complete!\nNext: ${this.campaign.levels?.[this.levelIndex+1].title}`).setVisible(true);
              this.cameras.main.fadeOut(250);
              this.time.delayedCall(260,()=>this.scene.restart({spec:this.campaign,levelIndex:this.levelIndex+1}));
            } else this.finish("won");
          }
          else {
            this.messageUntil=this.time.now+2200;
            this.message
              .setText(
                `Find ${s.objective.required - this.crystals} more ${s.collectible || "crystals"} to open the gate`,
              )
              .setVisible(true);
          }
        }
      });
    }
    this.keys = this.input.keyboard!.addKeys(
      "LEFT,RIGHT,UP,A,D,W,SPACE,SHIFT,R",
    ) as Record<string, Phaser.Input.Keyboard.Key>;
    this.events.on("touch-control", (key: string, pressed: boolean) => {
      this.touch[key] = pressed;
    });
    this.input.keyboard!.disableGlobalCapture();
    const hudScale = Math.min(
      2.5,
      Math.max(1, 960 / (this.game.canvas.parentElement?.clientWidth || 960)),
    );
    this.add
      .rectangle(18, 18, 360 * hudScale, 96 * hudScale, 0x162d37, 0.9)
      .setOrigin(0)
      .setScrollFactor(0)
      .setDepth(50);
    this.hud = this.add
      .text(18 + 16 * hudScale, 18 + 12 * hudScale, "", {
        fontFamily: "monospace",
        fontSize: `${Math.round(14 * hudScale)}px`,
        color: "#f0f5e6",
        lineSpacing: 10 * hudScale,
      })
      .setScrollFactor(0)
      .setDepth(51);
    this.message = this.add
      .text(480, 245, "", {
        fontFamily: "sans-serif",
        fontSize: "25px",
        color: "#ffffff",
        align: "center",
        wordWrap: { width: 780, useAdvancedWrap: true },
        backgroundColor: "#18333e",
        padding: { x: 24, y: 18 },
      })
      .setOrigin(0.5)
      .setScrollFactor(0)
      .setDepth(60)
      .setVisible(false);
    this.message.setText(`Level ${this.levelIndex+1}: ${s.title}\n${s.briefing || (s.objective.required ? `Collect ${s.objective.required} ${s.collectible || 'crystals'}, then find the exit.` : 'Find the exit.')}`).setVisible(true);
    this.messageUntil = this.time.now + 2400;
    camera.fadeIn(250);
    camera.startFollow(this.hero, true, 0.1, 0.1, s.camera_mode === "vertical" ? 0 : -150, 55);
    if (new URLSearchParams(location.search).has("test")) {
      Object.assign(window, {
        __AETHER_PLATFORMER__: {
          snapshot: () => this.snapshot(),
          restart: (levelIndex = 0) => {
            this.scene.restart({ spec: this.campaign, levelIndex: Math.max(0, Math.min(levelIndex, (this.campaign.levels?.length || 1)-1)) });
          },
          teleport: (x: number, y: number) => {
            this.hero.setPosition(x, y);
            this.hero.setVelocity(0);
          },
          damage: () => {
            this.hurtAt = -2000;
            this.damage();
          },
        },
      });
    }
    this.events.once("shutdown", () => {
      this.events.removeAllListeners("touch-control");
      delete (window as unknown as Record<string, unknown>)
        .__AETHER_PLATFORMER__;
    });
  }
  burst(x: number, y: number, color: number) {
    for (let i = 0; i < 7; i++) {
      const p = this.add
        .image(x, y, "terrain", 152)
        .setScale(0.35)
        .setTint(color);
      this.tweens.add({
        targets: p,
        x: x + Math.cos(i) * 35,
        y: y - 30 + Math.sin(i) * 25,
        alpha: 0,
        duration: 450,
        onComplete: () => p.destroy(),
      });
    }
  }
  damage() {
    if (this.state !== "playing" || this.time.now - this.hurtAt < 1200) return;
    this.hurtAt = this.time.now;
    this.health--;
    this.hero.setVelocity(-this.facing * 160, -200);
    this.cameras.main.shake(100, 0.004);
    if (this.health <= 0) this.finish("lost");
  }
  finish(state: string) {
    this.state = state;
    this.hero.setVelocity(0);
    this.physics.pause();
    this.message
      .setText(
        state === "won"
          ? `All ${this.campaign.levels?.length || 1} levels complete!\nPress R to play again`
          : `Journey ended at level ${this.levelIndex+1}\nPress R to restart the journey`,
      )
      .setVisible(true);
  }
  snapshot() {
    const b = this.hero.body as Phaser.Physics.Arcade.Body;
    if (!b) return { ready: false, generation: this.generation };
    return {
      ready: true,
      levelIndex: this.levelIndex,
      levelCount: this.campaign.levels?.length || 1,
      levelTitle: this.spec.title,
      topology: this.spec.topology,
      objective: this.spec.objective,
      respawn: this.spawn,
      exitAlpha: this.exits[0]?.alpha,
      exitStyle: this.spec.exit_style || "gate",
      enemies: this.enemies.filter(e=>e.sprite.active).map(e=>({behavior:e.behavior,x:e.sprite.x,y:e.sprite.y,vx:(e.sprite.body as Phaser.Physics.Arcade.Body).velocity.x})),
      icicles: this.traps.map(t=>({state:t.state,x:t.sprite.x,y:t.sprite.y,activations:t.activations,trigger:t.spec.trigger})),
      machines: this.machines.map(m=>({active:m.active,x:m.sprite.x,y:m.sprite.y})),
      movingPlatforms: this.moving.map(p=>({x:p.sprite.x,y:p.sprite.y})),
      shotsFired: this.shotsFired,
      slippery: !!this.spec.slippery,
      environment: this.spec.theme,
      terrainTexture: this.spec.theme === "ice" ? "ice" : this.spec.theme === "industrial" ? "industrial" : "terrain",
      generation: this.generation,
      landedPlatforms: [...this.landedPlatforms],
      x: this.hero.x,
      y: this.hero.y,
      vx: b.velocity.x,
      vy: b.velocity.y,
      grounded:
        b.blocked.down || (b.touching.down && Math.abs(b.velocity.y) < 1),
      health: this.health,
      crystals: this.crystals,
      state: this.state,
      checkpoint: this.checkpoint,
      missingAssets: this.missingAssets,
      animation: this.hero.anims.currentAnim?.key,
      seed: this.spec.seed,
      time: this.time.now,
    };
  }
  update() {
    const time = this.time.now;
    if (!this.hero) return;
    if (
      !this.game.canvas.parentElement?.contains(document.activeElement) || ["TEXTAREA", "INPUT", "SELECT"].includes(
        document.activeElement?.tagName || "",
      )
    ) {
      Object.values(this.keys).forEach((key) => key.reset());
      this.hero.setAccelerationX(0);
      this.touch = {left:false,right:false,jump:false,dash:false};
    }
    if (Phaser.Input.Keyboard.JustDown(this.keys.R)) {
      this.scene.restart({ spec: this.campaign });
      return;
    }
    if (this.state !== "playing") return;
    const b = this.hero.body as Phaser.Physics.Arcade.Body;
    const grounded =
      b.blocked.down || (b.touching.down && Math.abs(b.velocity.y) < 1);
    if (b.blocked.down)
      this.spec.platforms.forEach((p, i) => {
        if (
          !p.moving &&
          this.hero.x >= p.x * 36 &&
          this.hero.x <= (p.x + p.width) * 36 &&
          Math.abs(this.hero.y + 24 - p.y * 36) < 6
        )
          this.landedPlatforms.add(i);
      });
    if (grounded) {
      this.groundedAt = time;
      this.jumps = 0;
    }
    const left = this.keys.LEFT.isDown || this.keys.A.isDown || this.touch.left,
      right = this.keys.RIGHT.isDown || this.keys.D.isDown || this.touch.right;
    if (left || right) {
      this.facing = left ? -1 : 1;
      this.hero.setAccelerationX(this.facing * (this.spec.slippery ? 700 : 1900));
    } else this.hero.setAccelerationX(0);
    const dashing = time - this.dashAt < 150;
    this.hero.setMaxVelocity(dashing ? 650 : this.spec.player.speed, 900);
    this.hero.setDragX(dashing ? 0 : this.spec.slippery ? 180 : 2000);
    if (
      Phaser.Input.Keyboard.JustDown(this.keys.SPACE) ||
      Phaser.Input.Keyboard.JustDown(this.keys.UP) ||
      Phaser.Input.Keyboard.JustDown(this.keys.W) ||
      this.touch.jump
    ) {
      this.jumpAt = time;
      this.touch.jump = false;
    }
    const canJump =
      grounded ||
      time - this.groundedAt < 100 ||
      (this.spec.player.abilities.includes("double_jump") && this.jumps < 2);
    if (time - this.jumpAt < 120 && canJump) {
      this.hero.setVelocityY(-this.spec.player.jump);
      this.jumps++;
      this.groundedAt = -1000;
      this.jumpAt = -1000;
    }
    if (
      (Phaser.Input.Keyboard.JustDown(this.keys.SHIFT) || this.touch.dash) &&
      this.spec.player.abilities.includes("dash") &&
      time - this.dashAt > 700
    ) {
      this.dashAt = time;
      this.hero
        .setMaxVelocity(650, 900)
        .setDragX(0)
        .setVelocityX(this.facing * 620);
    }
    this.touch.dash = false;
    if (dashing)
      this.hero.setAccelerationX(0).setVelocity(this.facing * 620, 0);
    this.hero.setFlipX(this.facing < 0);
    this.hero.play(
      !grounded
        ? b.velocity.y < 0
          ? "jump"
          : "fall"
        : Math.abs(b.velocity.x) > 15
          ? "run"
          : "idle",
      true,
    );
    this.hero.setAlpha(
      time - this.hurtAt < 1200 ? (Math.floor(time / 100) % 2 ? 0.4 : 1) : 1,
    );
    for (const e of this.enemies) {
      if (!e.sprite.active) continue;
      const low = (e.platform.x + 0.5) * 36,
        high = (e.platform.x + e.platform.width - 0.5) * 36;
      const decision=enemyDecision(e.behavior,e.sprite.x,e.sprite.y,low,high,e.direction,this.hero.x,this.hero.y,time-e.shotAt);
      e.direction=decision.direction;
      e.sprite.setVelocityX(decision.vx);
      if (decision.fire) {
        e.shotAt=time; this.shotsFired++;
        const bullet=this.projectiles!.create(e.sprite.x,e.sprite.y,"terrain",registry.roles.crystal) as Phaser.Physics.Arcade.Sprite;
        bullet.setScale(.65).setTint(0xff855e).setVelocityX(e.direction*190);
        this.time.delayedCall(2400,()=>{if(bullet.active)bullet.destroy();});
      }
      e.sprite.setFlipX(e.direction > 0);
      e.sprite.setFrame(
        (this.spec.theme === "industrial"
          ? registry.roles.enemy_industrial
          : registry.roles.enemy_forest)[Math.floor(time / 180) % 2],
      );
    }
    for (const trap of this.traps) {
      const elapsed=time-trap.at, body=trap.sprite.body as Phaser.Physics.Arcade.Body;
      const next=iciclePhase(trap.state,elapsed,Math.abs(this.hero.x-trap.spec.x)<(trap.spec.radius || 110) && this.hero.y>trap.spec.y,
        trap.spec.trigger || "proximity",trap.spec.period_ms || 2200);
      if(trap.state==="warning")trap.sprite.setTint(Math.floor(time/80)%2?0xffffff:0x4488bb);
      if(next!==trap.state){
        trap.state=next;trap.at=time;
        if(next==="falling"){trap.activations++;body.setAllowGravity(true);trap.sprite.setVelocityY(80);}
        if(next==="waiting"){
          trap.sprite.enableBody(true,trap.spec.x,trap.spec.y,true,true).clearTint();
          body.setAllowGravity(false);trap.sprite.setVelocity(0);
        }
      }
      if(trap.state==="falling" && trap.sprite.y>this.spec.height+50){
        trap.state="spent";trap.at=time;trap.sprite.disableBody(true,true);
      }
    }
    for(const machine of this.machines){
      machine.active=(time % (machine.spec.period_ms || 2200))<(machine.spec.period_ms || 2200)*.5;
      machine.sprite.setTint(machine.active?0xff6655:0x668899).setAlpha(machine.active?1:.4);
      if(machine.active)machine.sprite.rotation=time/100;
    }
    if(this.messageUntil && time>this.messageUntil){this.message.setVisible(false);this.messageUntil=0;}
    for (const p of this.moving)
      p.sprite.setVelocityX(p.motion ? Math.cos(time / 850 + p.phase) * 65 : 0);
    if (this.hero.y > this.spec.height - 20) {
      this.hurtAt = -2000;
      this.damage();
      if (this.state === "playing") {
        this.hero.setPosition(this.spawn.x, this.spawn.y);
        this.hero.setVelocity(0);
        this.jumps = 0;
        this.groundedAt = -1000;
      }
    }
    this.hud.setText(
      `${"♥ ".repeat(Math.max(0, this.health))}  Level ${this.levelIndex+1}/${this.campaign.levels?.length || 1}\n${this.crystals} collected · ${this.spec.objective.required} needed · ${this.spec.objective.total} ${this.spec.collectible || "crystals"}\n${this.crystals < this.spec.objective.required ? "Collect items, then reach the exit" : this.levelIndex+1 < (this.campaign.levels?.length || 1) ? "Reach the exit to the next level" : "Reach the exit"}${this.checkpoint >= 0 ? " · Saved" : ""}`,
    );
  }
}
