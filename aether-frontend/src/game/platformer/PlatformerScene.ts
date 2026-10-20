import Phaser from "phaser";
import type { PlatformerIR, Platform } from "./types";
import registry from "../../../public/assets/registry.json";

export class PlatformerScene extends Phaser.Scene {
  spec!: PlatformerIR;
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
  }[] = [];
  moving: { sprite: Phaser.Physics.Arcade.Sprite; x: number; phase: number }[] =
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
  init(data: { spec: PlatformerIR }) {
    this.spec = data.spec;
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
    const s = this.spec,
      industrial = s.theme === "industrial",
      roles = registry.roles;
    this.physics.world.gravity.y = s.player.gravity;
    this.physics.world.setBounds(0, 0, s.width, s.height + 200);
    const camera = this.cameras.main;
    camera.setBounds(0, 0, s.width, s.height);
    camera.setBackgroundColor(s.theme === "twilight" ? "#505475" : "#b8dbd0");
    const background = this.add
      .tileSprite(0, 0, 960, 540, `bg-${s.theme}`)
      .setOrigin(0)
      .setScrollFactor(0)
      .setDepth(-10);
    background.setTileScale(8, 8);
    if (s.theme === "twilight") background.setTint(0x8a8ebd);
    const tiles = this.make.tilemap({
      tileWidth: 18,
      tileHeight: 18,
      width: Math.ceil(s.width / 36),
      height: Math.ceil(s.height / 36),
    });
    const texture = industrial ? "industrial" : "terrain";
    const set = tiles.addTilesetImage(texture, texture, 18, 18, 0, 0)!;
    const layer = tiles.createBlankLayer("world", set)!.setScale(2);
    for (const p of s.platforms) {
      if (p.moving) {
        const obj = this.physics.add
          .sprite(
            (p.x + p.width / 2) * 36,
            p.y * 36 + 9,
            texture,
            industrial ? roles.moving_industrial : roles.moving_forest,
          )
          .setDisplaySize(p.width * 36, 18);
        obj.setImmovable(true).setGravityY(-s.player.gravity);
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.up = true;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.down = false;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.left = false;
        (obj.body as Phaser.Physics.Arcade.Body).checkCollision.right = false;
        this.moving.push({ sprite: obj, x: obj.x, phase: p.x });
        continue;
      }
      for (let x = p.x; x < p.x + p.width; x++) {
        const top =
          (industrial ? roles.industrial_ground : roles.forest_ground) +
          (x === p.x ? 0 : x === p.x + p.width - 1 ? 2 : 1);
        tiles.putTileAt(top, x, p.y, false, layer);
        for (let y = p.y + 1; y < Math.ceil(s.height / 36); y++)
          tiles.putTileAt(
            industrial
              ? roles.industrial_fill
              : roles.forest_fill + ((x + y) % 2),
            x,
            y,
            false,
            layer,
          );
      }
      if (!industrial) {
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
    for (const e of s.entities) {
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
        });
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
        .staticSprite(e.x, e.y, "terrain", frame)
        .setScale(e.kind === "exit" ? 3 : 2)
        .refreshBody();
      if (e.kind === "crystal")
        this.tweens.add({
          targets: obj,
          y: obj.y - 7,
          duration: 1000,
          yoyo: true,
          repeat: -1,
          ease: "Sine.inOut",
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
          if (this.crystals >= s.objective.required) this.finish("won");
          else
            this.message
              .setText(
                `Find ${s.objective.required - this.crystals} more crystals to open the gate`,
              )
              .setVisible(true);
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
      .rectangle(18, 18, 330 * hudScale, 68 * hudScale, 0x162d37, 0.9)
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
        backgroundColor: "#18333e",
        padding: { x: 24, y: 18 },
      })
      .setOrigin(0.5)
      .setScrollFactor(0)
      .setDepth(60)
      .setVisible(false);
    camera.startFollow(this.hero, true, 0.1, 0.1, -150, 55);
    if (new URLSearchParams(location.search).has("test")) {
      Object.assign(window, {
        __AETHER_PLATFORMER__: {
          snapshot: () => this.snapshot(),
          restart: () => {
            this.scene.restart({ spec: this.spec });
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
          ? "Passage complete!\nPress R to play again"
          : "One more adventure?\nPress R to retry",
      )
      .setVisible(true);
  }
  snapshot() {
    const b = this.hero.body as Phaser.Physics.Arcade.Body;
    if (!b) return { ready: false, generation: this.generation };
    return {
      ready: true,
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
      ["TEXTAREA", "INPUT", "SELECT"].includes(
        document.activeElement?.tagName || "",
      )
    ) {
      Object.values(this.keys).forEach((key) => key.reset());
      this.hero.setAccelerationX(0);
      return;
    }
    if (Phaser.Input.Keyboard.JustDown(this.keys.R)) {
      this.scene.restart({ spec: this.spec });
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
      this.hero.setAccelerationX(this.facing * 1900);
    } else this.hero.setAccelerationX(0);
    const dashing = time - this.dashAt < 150;
    this.hero.setMaxVelocity(dashing ? 650 : this.spec.player.speed, 900);
    this.hero.setDragX(dashing ? 0 : 2000);
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
      if (e.sprite.x < low) e.direction = 1;
      if (e.sprite.x > high) e.direction = -1;
      e.sprite.setVelocityX(e.direction * 65);
      e.sprite.setFlipX(e.direction > 0);
      e.sprite.setFrame(
        (this.spec.theme === "industrial"
          ? registry.roles.enemy_industrial
          : registry.roles.enemy_forest)[Math.floor(time / 180) % 2],
      );
    }
    for (const p of this.moving)
      p.sprite.setVelocityX(Math.cos(time / 850 + p.phase) * 65);
    if (this.hero.y > this.spec.height - 20) {
      this.hurtAt = -2000;
      this.damage();
      if (this.state === "playing") {
        this.hero.setPosition(this.spawn.x, this.spawn.y);
        this.hero.setVelocity(0);
      }
    }
    this.hud.setText(
      `${"♥ ".repeat(Math.max(0, this.health))}    ${this.crystals} / ${this.spec.objective.total} crystals\n${this.spec.objective.required ? `Collect ${this.spec.objective.required}, then find the gate` : this.spec.theme === "industrial" ? "Reach the factory exit" : "Find the ancient gate"}${this.checkpoint >= 0 ? "  ·  Saved" : ""}`,
    );
  }
}
