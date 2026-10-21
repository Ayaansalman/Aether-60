import {emitterStep,safeSpawn} from './survival/stream';
import Phaser from 'phaser';
import type { GameIR } from './gameir';
import type { GameState, EnemyPosition } from './qaHook';

/**
 * Seeded pseudo-random number generator (Mulberry32).
 * Ensures deterministic enemy and collectible spawn locations from gameIR.seed.
 */
function createSeededRNG(seed: number) {
  let s = (seed >>> 0) || 1;
  return function () {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface ThemeVisualConfig {
  name: string;
  bgColor: number;
  borderColor: number;
  borderAccent: number;
  playerColor: number;
  playerAccent: number;
  enemyColor: number;
  enemyAccent: number;
  collectibleColor: number;
  collectibleAccent: number;
  projectileColor: number;
  projectileAccent: number;
  hudAccent: string;
  hudAccentNum: number;
}

export const THEME_CONFIGS: Record<string, ThemeVisualConfig> = {
  fantasy: {
    name: 'fantasy',
    bgColor: 0x0c0919,
    borderColor: 0x8b5cf6,
    borderAccent: 0xf59e0b,
    playerColor: 0x7c3aed,
    playerAccent: 0xfde047,
    enemyColor: 0x15803d,
    enemyAccent: 0x4ade80,
    collectibleColor: 0x06b6d4,
    collectibleAccent: 0xa5f3fc,
    projectileColor: 0xd946ef,
    projectileAccent: 0xfbcfe8,
    hudAccent: '#f59e0b',
    hudAccentNum: 0xf59e0b,
  },
  sci_fi: {
    name: 'sci_fi',
    bgColor: 0x030712,
    borderColor: 0x06b6d4,
    borderAccent: 0x38bdf8,
    playerColor: 0x0ea5e9,
    playerAccent: 0x38bdf8,
    enemyColor: 0xe11d48,
    enemyAccent: 0xfb7185,
    collectibleColor: 0x10b981,
    collectibleAccent: 0x6ee7b7,
    projectileColor: 0x38bdf8,
    projectileAccent: 0xe0f2fe,
    hudAccent: '#06b6d4',
    hudAccentNum: 0x06b6d4,
  },
  pirate: {
    name: 'pirate',
    bgColor: 0x071524,
    borderColor: 0xb45309,
    borderAccent: 0xf59e0b,
    playerColor: 0xb91c1c,
    playerAccent: 0xfde047,
    enemyColor: 0x57534e,
    enemyAccent: 0xa8a29e,
    collectibleColor: 0xeab308,
    collectibleAccent: 0xfef08a,
    projectileColor: 0xf97316,
    projectileAccent: 0xffedd5,
    hudAccent: '#f59e0b',
    hudAccentNum: 0xf59e0b,
  },
  spooky: {
    name: 'spooky',
    bgColor: 0x090610,
    borderColor: 0x7c3aed,
    borderAccent: 0xa855f7,
    playerColor: 0x4338ca,
    playerAccent: 0xa78bfa,
    enemyColor: 0x059669,
    enemyAccent: 0x34d399,
    collectibleColor: 0xc084fc,
    collectibleAccent: 0xf3e8ff,
    projectileColor: 0x2dd4bf,
    projectileAccent: 0x99f6e4,
    hudAccent: '#a855f7',
    hudAccentNum: 0xa855f7,
  },
  cozy: {
    name: 'cozy',
    bgColor: 0x0f1715,
    borderColor: 0x84cc16,
    borderAccent: 0xa3e635,
    playerColor: 0xd97706,
    playerAccent: 0xfde68a,
    enemyColor: 0x9f1239,
    enemyAccent: 0xf43f5e,
    collectibleColor: 0xfde047,
    collectibleAccent: 0xfef9c3,
    projectileColor: 0x10b981,
    projectileAccent: 0xa7f3d0,
    hudAccent: '#a3e635',
    hudAccentNum: 0xa3e635,
  },
};

export function getThemeVisualConfig(themeName?: string): ThemeVisualConfig {
  const normalized = (themeName || 'fantasy').toLowerCase().replace('-', '_').trim();
  return THEME_CONFIGS[normalized] || THEME_CONFIGS.fantasy;
}

export class ArenaScene extends Phaser.Scene {
  private gameIR!: GameIR;
  private themeConfig!: ThemeVisualConfig;
  private decoGraphics?: Phaser.GameObjects.Graphics;
  private streamNextAt=0;
  private streamSerial=0;
  private streamShots=0;
  private streamExpired=0;
  private streamFires:{id:number;at:number;shot:number}[]=[];
  private streamTrace:{id:number;type:string;x:number;y:number;at:number;shots?:number}[]=[];
  private touch:Record<string,boolean>={};
  private requestRestart=false;
  private player!: Phaser.GameObjects.Rectangle;
  private enemies!: Phaser.GameObjects.Group;
  private collectiblesGroup!: Phaser.GameObjects.Group;
  private projectilesGroup!: Phaser.GameObjects.Group;
  private enemyProjectilesGroup!: Phaser.GameObjects.Group;
  private obstaclesGroup!: Phaser.Physics.Arcade.StaticGroup;
  private cursors?: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasdKeys?: {
    W: Phaser.Input.Keyboard.Key;
    A: Phaser.Input.Keyboard.Key;
    S: Phaser.Input.Keyboard.Key;
    D: Phaser.Input.Keyboard.Key;
  };
  private spaceKey?: Phaser.Input.Keyboard.Key;
  private rKey?: Phaser.Input.Keyboard.Key;

  // RNG
  private rng!: () => number;

  // Health and state tracking
  private maxHealth: number = 3;
  private currentHealth: number = 3;
  private isInvulnerable: boolean = false;
  private isKnockedBack: boolean = false;
  private isGameOver: boolean = false;
  private isGameWon: boolean = false;

  // Attack cooldown & respawn timers
  private lastAttackTime: number = 0;
  private attacksPerformed: number = 0;
  private respawnTimers: Phaser.Time.TimerEvent[] = [];
  private enemiesPaused: boolean = false;

  // Objective & score tracking
  private score: number = 0;
  private targetScore: number = 8;
  private enemiesDefeated: number = 0;
  private survivalTimeRemaining: number = 0;
  private timeElapsed: number = 0;
  private totalGameTimeMs: number = 0;
  private survivalTimerEvent?: Phaser.Time.TimerEvent;
  private elapsedTimerEvent?: Phaser.Time.TimerEvent;

  // UI elements
  private healthText?: Phaser.GameObjects.Text;
  private objectiveText?: Phaser.GameObjects.Text;
  private controlsText?: Phaser.GameObjects.Text;
  private overlayContainer?: Phaser.GameObjects.Container;

  constructor() {
    super({ key: 'ArenaScene' });
  }

  private isTestMode(): boolean {
    if (typeof window === 'undefined') return false;
    return new URLSearchParams(window.location.search).get('test') === '1';
  }

  private getBugParam(): string | null {
    if (typeof window === 'undefined') return null;
    const params = new URLSearchParams(window.location.search);
    if (params.get('test') !== '1') return null;
    return params.get('bug');
  }

  init(data: {
    gameIR: GameIR;
    isRestart?: boolean;
    prevHealth?: number;
    enemiesPaused?: boolean;
  }): void {
    this.gameIR = data.gameIR;
    this.streamNextAt=0;this.streamSerial=0;this.streamShots=0;this.streamExpired=0;this.streamTrace=[];this.streamFires=[];this.touch={};this.requestRestart=false;
    this.maxHealth = this.gameIR.player?.max_health ?? 3;
    const bug = this.getBugParam();
    if (bug === 'restart_keeps_hp' && data?.isRestart) {
      // Bug fixture: restart retains pre-restart HP instead of restoring max_health
      this.currentHealth =
        data.prevHealth !== undefined && data.prevHealth < this.maxHealth
          ? data.prevHealth
          : 1;
    } else {
      this.currentHealth = this.maxHealth;
    }
    this.isInvulnerable = false;
    this.isKnockedBack = false;
    this.isGameOver = false;
    this.isGameWon = false;
    this.enemiesPaused = Boolean(data?.enemiesPaused);
    this.score = 0;
    this.enemiesDefeated = 0;
    this.timeElapsed = 0;
    this.totalGameTimeMs = 0;
    this.lastAttackTime = 0;
    this.attacksPerformed = 0;

    // Clear any previous respawn timers
    this.respawnTimers.forEach((t) => t.remove());
    this.respawnTimers = [];

    if (this.gameIR.objective?.type === 'survive_seconds') {
      this.survivalTimeRemaining = this.gameIR.objective.target ?? 30;
    } else if (this.gameIR.objective?.type === 'defeat_enemies') {
      this.targetScore = this.gameIR.objective?.target ?? 10;
    } else {
      this.targetScore = this.gameIR.objective?.target ?? 8;
    }

    this.themeConfig = { ...getThemeVisualConfig(this.gameIR.theme) };
    if (this.gameIR.visual_overrides?.accent_hex) {
      const hex = this.gameIR.visual_overrides.accent_hex;
      const num = parseInt(hex.replace('#', '0x'), 16);
      if (!isNaN(num)) {
        this.themeConfig.hudAccent = hex;
        this.themeConfig.hudAccentNum = num;
        this.themeConfig.borderAccent = num;
        this.themeConfig.playerAccent = num;
      }
    }
  }

  create(): void {
    const width = this.scale.width;
    const height = this.scale.height;
    const theme = this.themeConfig;

    // 1. Background styling
    this.cameras.main.setBackgroundColor(theme.bgColor);

    // Subtle arena grid
    const grid = this.add.graphics();
    grid.lineStyle(1, theme.borderColor, 0.08);
    for (let x = 40; x < width; x += 40) {
      grid.lineBetween(x, 10, x, height - 10);
    }
    for (let y = 40; y < height; y += 40) {
      grid.lineBetween(10, y, width - 10, y);
    }

    // Thematic arena border with corner brackets
    const border = this.add.graphics();
    border.lineStyle(2, theme.borderColor, 0.65);
    border.strokeRect(10, 10, width - 20, height - 20);
    border.lineStyle(2, theme.borderAccent, 0.9);
    border.lineBetween(10, 10, 26, 10);
    border.lineBetween(10, 10, 10, 26);
    border.lineBetween(width - 26, 10, width - 10, 10);
    border.lineBetween(width - 10, 10, width - 10, 26);
    border.lineBetween(10, height - 10, 26, height - 10);
    border.lineBetween(10, height - 26, 10, height - 10);
    border.lineBetween(width - 26, height - 10, width - 10, height - 10);
    border.lineBetween(width - 10, height - 26, width - 10, height - 10);

    // 2. Obstacles setup based on arena_layout
    this.obstaclesGroup = this.physics.add.staticGroup();
    const layout = this.gameIR.arena_layout || 'open';
    if (layout === 'pillars') {
      const pillars = [
        { x: 220, y: 160 },
        { x: 580, y: 160 },
        { x: 220, y: 440 },
        { x: 580, y: 440 },
      ];
      pillars.forEach((pos) => {
        const p = this.add.rectangle(pos.x, pos.y, 60, 60, theme.borderColor, 0.45);
        p.setStrokeStyle(2, theme.borderAccent, 0.85);
        this.physics.add.existing(p, true);
        this.obstaclesGroup.add(p);
      });
    } else if (layout === 'lanes') {
      const lanes = [
        { x: 190, y: 200, w: 260, h: 24 },
        { x: 610, y: 200, w: 260, h: 24 },
        { x: 190, y: 400, w: 260, h: 24 },
        { x: 610, y: 400, w: 260, h: 24 },
      ];
      lanes.forEach((seg) => {
        const wall = this.add.rectangle(seg.x, seg.y, seg.w, seg.h, theme.borderColor, 0.45);
        wall.setStrokeStyle(2, theme.borderAccent, 0.85);
        this.physics.add.existing(wall, true);
        this.obstaclesGroup.add(wall);
      });
    } else if (layout === 'maze') {
      const mazeSegments = [
        { x: 230, y: 170, w: 180, h: 24 },
        { x: 180, y: 185, w: 24, h: 90 },
        { x: 570, y: 170, w: 180, h: 24 },
        { x: 620, y: 185, w: 24, h: 90 },
        { x: 230, y: 430, w: 180, h: 24 },
        { x: 180, y: 415, w: 24, h: 90 },
        { x: 570, y: 430, w: 180, h: 24 },
        { x: 620, y: 415, w: 24, h: 90 },
      ];
      mazeSegments.forEach((seg) => {
        const wall = this.add.rectangle(seg.x, seg.y, seg.w, seg.h, theme.borderColor, 0.45);
        wall.setStrokeStyle(2, theme.borderAccent, 0.85);
        this.physics.add.existing(wall, true);
        this.obstaclesGroup.add(wall);
      });
    }

    // 3. Player setup (center of the canvas)
    const startX = width / 2;
    const startY = height / 2;
    this.player = this.add.rectangle(startX, startY, 32, 32, theme.playerColor);
    this.player.setStrokeStyle(2, theme.playerAccent, 1);
    this.physics.add.existing(this.player);

    const playerBody = this.player.body as Phaser.Physics.Arcade.Body;
    playerBody.setCollideWorldBounds(true);

    // Player collides with obstacles
    this.physics.add.collider(this.player, this.obstaclesGroup);

    // 4. Seeded random generator
    this.rng = createSeededRNG(this.gameIR.seed ?? 42);

    // 5. Collectibles setup
    this.collectiblesGroup = this.add.group();
    const collectibleConfig = this.gameIR.collectibles?.[0];
    const collectibleCount = collectibleConfig?.count ?? 0;

    for (let i = 0; i < collectibleCount; i++) {
      const cx = 40 + Math.floor(this.rng() * (width - 80));
      const cy = 40 + Math.floor(this.rng() * (height - 80));

      const circle = this.add.circle(cx, cy, 9, theme.collectibleColor);
      circle.setStrokeStyle(1.5, theme.collectibleAccent, 1);
      this.physics.add.existing(circle);
      const circleBody = circle.body as Phaser.Physics.Arcade.Body;
      circleBody.setCircle(9);

      this.collectiblesGroup.add(circle);
    }

    // Overlap: Player collects item
    this.physics.add.overlap(
      this.player,
      this.collectiblesGroup,
      (_, itemObj) => {
        this.handleCollectiblePickup(itemObj as Phaser.GameObjects.Arc);
      },
      undefined,
      this
    );

    // 6. Enemies setup with seeded random positions and multi-type support
    this.enemies = this.add.group();
    this.enemyProjectilesGroup = this.add.group();

    const enemyConfigs = (this.gameIR.enemies && this.gameIR.enemies.length > 0)
      ? this.gameIR.enemies
      : [{ type: 'chaser', count: 5, speed: 75.0 }];

    let enemyIndex = 0;
    if(!this.gameIR.survival_stream)for (const config of enemyConfigs) {
      const enemyCount = config.count ?? 5;
      const enemyType = config.type || 'chaser';
      const enemySpeed = config.speed ?? 75.0;

      for (let i = 0; i < enemyCount; i++) {
        let enemyX: number;
        let enemyY: number;
        let attempts = 0;
        const minDistance = 200;

        do {
          enemyX = 30 + Math.floor(this.rng() * (width - 60));
          enemyY = 30 + Math.floor(this.rng() * (height - 60));
          attempts++;
        } while (
          Math.hypot(enemyX - startX, enemyY - startY) < minDistance &&
          attempts < 100
        );

        const enemy = this.add.rectangle(enemyX, enemyY, 24, 24, theme.enemyColor);
        enemy.setStrokeStyle(1.5, theme.enemyAccent, 1);
        this.physics.add.existing(enemy);
        const enemyBody = enemy.body as Phaser.Physics.Arcade.Body;
        enemyBody.setCollideWorldBounds(true);

        enemy.setData('enemyType', enemyType);
        enemy.setData('speed', enemySpeed);
        enemy.setData('spawnIndex', enemyIndex);
        enemy.setData('patrolDir', enemyIndex % 2 === 0 ? 1 : -1);
        enemy.setData('patrolAxis', enemyIndex % 2 === 0 ? 'x' : 'y');
        enemy.setData('dashState', 'stalking');
        enemy.setData('dashTimer', 0);
        enemy.setData('lastShootTime', this.time.now + (this.rng() * 1200));

        const bounceAngle = (this.rng() * Math.PI * 2);
        enemy.setData('bounceVx', Math.cos(bounceAngle) * enemySpeed);
        enemy.setData('bounceVy', Math.sin(bounceAngle) * enemySpeed);

        if (enemyType === 'bouncer') {
          enemyBody.setBounce(1, 1);
        }

        this.enemies.add(enemy);
        enemyIndex++;
      }
    }

    // Overlap: Player takes damage from enemy
    this.physics.add.overlap(
      this.player,
      this.enemies,
      (_, enemyObj) => {
        this.handlePlayerHit(enemyObj as Phaser.GameObjects.Rectangle);
      },
      undefined,
      this
    );

    // Overlap: Player takes damage from enemy bullet
    this.physics.add.overlap(
      this.player,
      this.enemyProjectilesGroup,
      (_, bulletObj) => {
        (bulletObj as Phaser.GameObjects.Arc).destroy();
        this.damagePlayer(1);
      },
      undefined,
      this
    );

    // Enemies collide with obstacles
    this.physics.add.collider(this.enemies, this.obstaclesGroup);

    // 7. Projectiles setup
    this.projectilesGroup = this.add.group();

    // Overlap: Projectile hits enemy
    this.physics.add.overlap(
      this.projectilesGroup,
      this.enemies,
      (projObj, enemyObj) => {
        this.handleProjectileEnemyHit(
          projObj as Phaser.GameObjects.Arc,
          enemyObj as Phaser.GameObjects.Rectangle
        );
      },
      undefined,
      this
    );

    // Projectiles collide with obstacles
    this.physics.add.collider(this.projectilesGroup, this.obstaclesGroup, (proj) => {
      (proj as Phaser.GameObjects.Arc).destroy();
    });
    this.physics.add.collider(this.enemyProjectilesGroup, this.obstaclesGroup, (bullet) => {
      (bullet as Phaser.GameObjects.Arc).destroy();
    });

    // 8. Input keybindings: Cursors + WASD + Space + R
    if (this.input.keyboard) {
      this.cursors = this.input.keyboard.createCursorKeys();
      this.wasdKeys = this.input.keyboard.addKeys({
        W: Phaser.Input.Keyboard.KeyCodes.W,
        A: Phaser.Input.Keyboard.KeyCodes.A,
        S: Phaser.Input.Keyboard.KeyCodes.S,
        D: Phaser.Input.Keyboard.KeyCodes.D,
      }) as {
        W: Phaser.Input.Keyboard.Key;
        A: Phaser.Input.Keyboard.Key;
        S: Phaser.Input.Keyboard.Key;
        D: Phaser.Input.Keyboard.Key;
      };
      this.spaceKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);
      this.rKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.R);

      this.input.keyboard.on('keydown-R', () => {
        this.restartGame();
      });
    }

    // 9. Thematic HUD Setup at top-left
    const hudGraphics = this.add.graphics();
    hudGraphics.fillStyle(0x000000, 0.7);
    hudGraphics.fillRoundedRect(16, 12, 274, 84, 8);
    hudGraphics.lineStyle(1.5, theme.hudAccentNum, 0.65);
    hudGraphics.strokeRoundedRect(16, 12, 274, 84, 8);

    this.healthText = this.add.text(26, 20, '', {
      fontFamily: 'monospace',
      fontSize: '18px',
      color: '#ffffff',
      stroke: '#000000',
      strokeThickness: 3,
    });

    this.objectiveText = this.add.text(26, 46, '', {
      fontFamily: 'monospace',
      fontSize: '16px',
      color: theme.hudAccent,
      stroke: '#000000',
      strokeThickness: 3,
    });

    // Controls line from GameIR
    const moveControl = this.gameIR.controls?.movement ?? 'WASD or arrow keys';
    const attackControl = this.gameIR.controls?.attack;
    const controlsString = attackControl
      ? `Controls: ${moveControl} | ${attackControl}`
      : `Controls: ${moveControl}`;

    this.controlsText = this.add.text(26, 72, controlsString, {
      fontFamily: 'monospace',
      fontSize: '13px',
      color: '#94a3b8',
      stroke: '#000000',
      strokeThickness: 2,
    });

    // Thematic Metadata HUD Card at top-right (Title, Premise, Mode)
    hudGraphics.fillStyle(0x000000, 0.7);
    hudGraphics.fillRoundedRect(width - 326, 12, 310, 84, 8);
    hudGraphics.lineStyle(1.5, theme.hudAccentNum, 0.65);
    hudGraphics.strokeRoundedRect(width - 326, 12, 310, 84, 8);

    this.add.text(width - 316, 20, (this.gameIR.title || 'UNNAMED ARENA').toUpperCase(), {
      fontFamily: 'monospace',
      fontSize: '13px',
      color: theme.hudAccent,
      stroke: '#000000',
      strokeThickness: 2,
    });

    this.add.text(width - 316, 42, this.gameIR.premise || 'Survive the arena.', {
      fontFamily: 'monospace',
      fontSize: '11px',
      color: '#cbd5e1',
      stroke: '#000000',
      strokeThickness: 2,
      wordWrap: { width: 290 },
    });

    const pLabel = this.gameIR.visual_overrides?.player_label;
    const eLabel = this.gameIR.visual_overrides?.enemy_label;
    const legendText = (pLabel || eLabel)
      ? ` • ${pLabel || 'HERO'} vs ${eLabel || 'ENEMIES'}`
      : '';
    this.add.text(width - 316, 74, `THEME: ${theme.name.toUpperCase()} • ${(this.gameIR.player?.attack_mode ?? 'avoid_only').toUpperCase()}${legendText}`, {
      fontFamily: 'monospace',
      fontSize: '10px',
      color: '#94a3b8',
      stroke: '#000000',
      strokeThickness: 2,
    });

    // Primitive shapes decorative layer
    this.decoGraphics = this.add.graphics();
    this.decoGraphics.setDepth(10);

    this.updateHUD();

    // 9. Survival Timer (if objective is survive_seconds)
    if (this.gameIR.objective?.type === 'survive_seconds') {
      this.survivalTimerEvent = this.time.addEvent({
        delay: 1000,
        loop: true,
        callback: () => {
          if (this.isGameOver || this.isGameWon) return;
          this.survivalTimeRemaining = Math.max(0, this.survivalTimeRemaining - 1);
          this.updateHUD();

          if (this.survivalTimeRemaining <= 0) {
            this.triggerGameWin();
          }
        },
      });
    }

    // 10. Elapsed Time Tracker
    this.elapsedTimerEvent = this.time.addEvent({
      delay: 1000,
      loop: true,
      callback: () => {
        if (!this.isGameOver && !this.isGameWon) {
          this.timeElapsed += 1;
          if(this.gameIR.survival_stream)this.updateHUD();
        }
      },
    });

    if(this.gameIR.survival_stream){
      this.streamNextAt=this.time.now+this.gameIR.survival_stream.spawn_interval_ms;
      const control=(key:string,pressed:boolean)=>{this.touch[key]=pressed;if(key==='restart'&&pressed)this.requestRestart=true;};
      this.events.on('survival-control',control);
      this.events.once('shutdown',()=>this.events.off('survival-control',control));
      if(this.isTestMode()){
        const testing=window as Window & {__survivalScene?:ArenaScene};testing.__survivalScene=this;
        this.events.once('shutdown',()=>{if(testing.__survivalScene===this)delete testing.__survivalScene;});
      }
    }
    // 11. QA Test Hook Setup (?test=1 only)
    if (this.isTestMode()) {
      window.__AETHER_GAME__ = {
        ready: true,
        tick: 0,
        gameTimeMs: 0,
        getState: () => this.getQAState(),
        advanceTimer: (seconds: number) => this.advanceTimer(seconds),
        simulatePickup: () => this.simulatePickup(),
        damagePlayer: (n: number) => this.damagePlayer(n),
        getEnemyPositions: () => this.getEnemyPositions(),
        pauseEnemies: (paused: boolean) => this.pauseEnemies(paused),
      };
    } else {
      delete window.__AETHER_GAME__;
    }
  }

  private updateHUD(): void {
    if(this.gameIR.survival_stream)this.game.events.emit('survival-ui',{health:this.currentHealth,max:this.maxHealth,seconds:this.timeElapsed});
    if (this.healthText) {
      this.healthText.setText(`HP: ${this.currentHealth} / ${this.maxHealth}`);
    }

    if (this.objectiveText) {
      if(this.gameIR.objective?.type==='survive_endless'){
        this.objectiveText.setText(`Survived: ${this.timeElapsed}s · Dodge chasers & shooters`);
      } else if (this.gameIR.objective?.type === 'survive_seconds') {
        this.objectiveText.setText(`Time: ${this.survivalTimeRemaining}s`);
      } else if (this.gameIR.objective?.type === 'defeat_enemies') {
        this.objectiveText.setText(`Defeated: ${this.enemiesDefeated} / ${this.targetScore}`);
      } else {
        const cLabel = this.gameIR.visual_overrides?.collectible_label ?? 'Crystals';
        this.objectiveText.setText(`${cLabel}: ${this.score} / ${this.targetScore}`);
      }
    }
  }

  private handleAttack(): void {
    if (this.isGameOver || this.isGameWon) return;

    const attackMode = this.gameIR.player?.attack_mode ?? 'avoid_only';
    if (attackMode === 'avoid_only') return;

    const now = this.time.now;

    if (attackMode === 'projectile') {
      // 400 ms cooldown
      if (now - this.lastAttackTime < 400) return;
      this.lastAttackTime = now;
      this.fireProjectile();
    } else if (attackMode === 'melee') {
      // 500 ms cooldown
      if (now - this.lastAttackTime < 500) return;
      this.lastAttackTime = now;
      this.performMeleeAttack();
    }
  }

  private fireProjectile(): void {
    // Find nearest active enemy
    let nearestEnemy: Phaser.GameObjects.Rectangle | null = null;
    let minDistance = Infinity;

    this.enemies.getChildren().forEach((enemyObj) => {
      const enemy = enemyObj as Phaser.GameObjects.Rectangle;
      if (!enemy.active) return;
      const dist = Math.hypot(enemy.x - this.player.x, enemy.y - this.player.y);
      if (dist < minDistance) {
        minDistance = dist;
        nearestEnemy = enemy;
      }
    });

    let angle = 0;
    const targetEnemy = nearestEnemy as Phaser.GameObjects.Rectangle | null;
    if (targetEnemy) {
      angle = Phaser.Math.Angle.Between(
        this.player.x,
        this.player.y,
        targetEnemy.x,
        targetEnemy.y
      );
    }

    // Create glowing projectile circle
    const proj = this.add.circle(this.player.x, this.player.y, 6, this.themeConfig.projectileColor);
    proj.setStrokeStyle(1.5, this.themeConfig.projectileAccent, 1);
    this.physics.add.existing(proj);
    const projBody = proj.body as Phaser.Physics.Arcade.Body;
    projBody.setVelocity(Math.cos(angle) * 400, Math.sin(angle) * 400);

    this.projectilesGroup.add(proj);
    this.attacksPerformed += 1;

    // Disappears after 1.2 seconds (1200 ms)
    this.time.delayedCall(1200, () => {
      if (proj.active) {
        proj.destroy();
      }
    });
  }

  private performMeleeAttack(): void {
    const radius = 70;

    // Visual flash (expanding cyan ring)
    const flash = this.add.circle(this.player.x, this.player.y, radius, 0x38bdf8, 0.35);
    flash.setStrokeStyle(2, 0x67e8f9, 0.9);
    this.tweens.add({
      targets: flash,
      alpha: 0,
      scale: 1.15,
      duration: 180,
      onComplete: () => flash.destroy(),
    });
    this.attacksPerformed += 1;

    // Enemies in range die and respawn
    const enemiesToKill: Phaser.GameObjects.Rectangle[] = [];
    this.enemies.getChildren().forEach((enemyObj) => {
      const enemy = enemyObj as Phaser.GameObjects.Rectangle;
      if (!enemy.active) return;
      const dist = Math.hypot(enemy.x - this.player.x, enemy.y - this.player.y);
      if (dist <= radius) {
        enemiesToKill.push(enemy);
      }
    });

    enemiesToKill.forEach((enemy) => this.killEnemy(enemy));
  }

  private handleProjectileEnemyHit(
    proj: Phaser.GameObjects.Arc,
    enemy: Phaser.GameObjects.Rectangle
  ): void {
    if (!proj.active || !enemy.active) return;
    proj.destroy();
    this.killEnemy(enemy);
  }

  private killEnemy(enemy: Phaser.GameObjects.Rectangle): void {
    if (!enemy.active) return;
    const enemyType = (enemy.getData('enemyType') as string) || 'chaser';
    const enemySpeed = (enemy.getData('speed') as number) ?? 75.0;
    enemy.destroy();

    if (this.gameIR.objective?.type === 'defeat_enemies') {
      this.enemiesDefeated += 1;
      this.score = this.enemiesDefeated;
      this.updateHUD();
      if (this.enemiesDefeated >= this.targetScore) {
        this.triggerGameWin();
      }
    }

    if(this.gameIR.survival_stream)return;
    // Respawn 3 seconds later at least 200px from player
    const timer = this.time.delayedCall(3000, () => {
      this.respawnEnemy(enemyType, enemySpeed);
    });
    this.respawnTimers.push(timer);
  }

  private respawnEnemy(enemyType: string = 'chaser', speed: number = 75.0, position?:{x:number;y:number}): void {
    if (this.isGameOver || this.isGameWon) return;

    const width = this.scale.width;
    const height = this.scale.height;
    let enemyX: number;
    let enemyY: number;
    let attempts = 0;
    const minDistance = 200;

    do {
      enemyX = 30 + Math.floor(this.rng() * (width - 60));
      enemyY = 30 + Math.floor(this.rng() * (height - 60));
      attempts++;
    } while (
      Math.hypot(enemyX - this.player.x, enemyY - this.player.y) < minDistance &&
      attempts < 100
    );

    if(position){enemyX=position.x;enemyY=position.y;}
    const enemy = this.add.rectangle(enemyX, enemyY, 24, 24, this.themeConfig.enemyColor);
    enemy.setStrokeStyle(1.5, this.themeConfig.enemyAccent, 1);
    this.physics.add.existing(enemy);
    const enemyBody = enemy.body as Phaser.Physics.Arcade.Body;
    enemyBody.setCollideWorldBounds(true);

    enemy.setData('enemyType', enemyType);
    enemy.setData('speed', speed);
    enemy.setData('patrolDir', 1);
    enemy.setData('patrolAxis', 'x');
    enemy.setData('dashState', 'stalking');
    enemy.setData('dashTimer', 0);
    enemy.setData('lastShootTime', this.time.now);

    const bounceAngle = this.rng() * Math.PI * 2;
    enemy.setData('bounceVx', Math.cos(bounceAngle) * speed);
    enemy.setData('bounceVy', Math.sin(bounceAngle) * speed);

    if (enemyType === 'bouncer') {
      enemyBody.setBounce(1, 1);
      enemyBody.setVelocity(Math.cos(bounceAngle) * speed, Math.sin(bounceAngle) * speed);
    }

    if(this.gameIR.survival_stream){
      const id=this.streamSerial++;enemy.setData('streamId',id);enemy.setData('bornAt',this.time.now);enemy.setData('shots',0);
      enemy.setFillStyle(enemyType==='shooter'?0xf59e0b:0xe84c70);
      const label=this.add.text(enemyX,enemyY-24,enemyType==='shooter'?'S 0/'+this.gameIR.survival_stream.shooter_shots:'C',{fontSize:'12px',fontFamily:'monospace',color:'#fff0cc',backgroundColor:'#172131aa'}).setOrigin(.5).setDepth(20);
      enemy.setData('streamLabel',label);enemy.once('destroy',()=>label.destroy());
      this.streamTrace.push({id,type:enemyType,x:enemyX,y:enemyY,at:this.time.now});this.streamTrace=this.streamTrace.slice(-64);
    }
    this.enemies.add(enemy);
  }

  private shootEnemyBullet(enemy: Phaser.GameObjects.Rectangle): void {
    if (this.isGameOver || this.isGameWon || this.enemiesPaused || !enemy.active) return;
    const bullet = this.add.circle(enemy.x, enemy.y, 5, 0xf43f5e);
    bullet.setStrokeStyle(1, 0xffffff, 0.9);
    this.physics.add.existing(bullet);
    const body = bullet.body as Phaser.Physics.Arcade.Body;
    const angle = Phaser.Math.Angle.Between(enemy.x, enemy.y, this.player.x, this.player.y);
    const bulletSpeed = this.gameIR.survival_stream?.bullet_speed ?? 95; // slow avoidable bullet
    body.setVelocity(Math.cos(angle) * bulletSpeed, Math.sin(angle) * bulletSpeed);
    this.enemyProjectilesGroup.add(bullet);

    this.time.delayedCall(this.gameIR.survival_stream?.bullet_lifetime_ms ?? 4000, () => {
      if (bullet.active) bullet.destroy();
    });
  }

  private handleCollectiblePickup(item: Phaser.GameObjects.Arc): void {
    if (this.isGameOver || this.isGameWon) return;

    item.destroy();
    this.score += 1;
    this.updateHUD();

    if (
      this.gameIR.objective?.type === 'collect_count' &&
      this.score >= this.targetScore
    ) {
      this.triggerGameWin();
    }
  }

  private handlePlayerHit(enemy: Phaser.GameObjects.Rectangle): void {
    if (this.enemiesPaused || this.isInvulnerable || this.isGameOver || this.isGameWon) return;
    if(this.gameIR.survival_stream&&this.time.now-(enemy.getData('bornAt')??-10000)<this.gameIR.survival_stream.warning_ms)return;

    this.currentHealth = Math.max(0, this.currentHealth - 1);
    this.updateHUD();

    const playerBody = this.player.body as Phaser.Physics.Arcade.Body;

    const angle = Phaser.Math.Angle.Between(enemy.x, enemy.y, this.player.x, this.player.y);
    const knockbackSpeed = 180;
    playerBody.setVelocity(
      Math.cos(angle) * knockbackSpeed,
      Math.sin(angle) * knockbackSpeed
    );
    this.isKnockedBack = true;
    this.time.delayedCall(160, () => {
      this.isKnockedBack = false;
    });

    if (this.currentHealth <= 0) {
      this.triggerGameOver();
      return;
    }

    this.isInvulnerable = true;
    this.tweens.add({
      targets: this.player,
      alpha: 0.2,
      duration: 100,
      yoyo: true,
      repeat: 4,
      onComplete: () => {
        this.player.alpha = 1;
        this.isInvulnerable = false;
      },
    });
  }

  private triggerGameOver(): void {
    this.isGameOver = true;
    this.freezeAll();

    const width = this.scale.width;
    const height = this.scale.height;

    const backdrop = this.add.rectangle(width / 2, height / 2, width, height, 0x05050c, 0.8);
    const diedText = this.add.text(width / 2, height / 2 - 25, 'YOU DIED', {
      fontFamily: 'monospace',
      fontSize: '44px',
      color: '#ef4444',
      stroke: '#000000',
      strokeThickness: 4,
    }).setOrigin(0.5);

    const restartText = this.add.text(width / 2, height / 2 + 30, 'Press R to restart', {
      fontFamily: 'monospace',
      fontSize: '18px',
      color: '#e2e8f0',
    }).setOrigin(0.5);

    this.overlayContainer = this.add.container(0, 0, [backdrop, diedText, restartText]);
    this.overlayContainer.setDepth(100);
  }

  private triggerGameWin(): void {
    const bug = this.getBugParam();
    if (bug === 'no_win') {
      // Known-broken fixture: win condition intentionally never triggers
      return;
    }

    this.isGameWon = true;
    this.freezeAll();

    const width = this.scale.width;
    const height = this.scale.height;

    const backdrop = this.add.rectangle(width / 2, height / 2, width, height, 0x05050c, 0.8);
    const winText = this.add.text(width / 2, height / 2 - 25, 'YOU WIN', {
      fontFamily: 'monospace',
      fontSize: '44px',
      color: '#22c55e',
      stroke: '#000000',
      strokeThickness: 4,
    }).setOrigin(0.5);

    const restartText = this.add.text(width / 2, height / 2 + 30, 'Press R to restart', {
      fontFamily: 'monospace',
      fontSize: '18px',
      color: '#e2e8f0',
    }).setOrigin(0.5);

    this.overlayContainer = this.add.container(0, 0, [backdrop, winText, restartText]);
    this.overlayContainer.setDepth(100);
  }

  private freezeAll(): void {
    const playerBody = this.player.body as Phaser.Physics.Arcade.Body;
    playerBody.setVelocity(0, 0);

    this.enemies.getChildren().forEach((enemyObj) => {
      const enemyBody = (enemyObj as Phaser.GameObjects.Rectangle).body as Phaser.Physics.Arcade.Body;
      enemyBody?.setVelocity(0, 0);
    });

    if (this.survivalTimerEvent) {
      this.survivalTimerEvent.remove();
      this.survivalTimerEvent = undefined;
    }

    if (this.elapsedTimerEvent) {
      this.elapsedTimerEvent.remove();
      this.elapsedTimerEvent = undefined;
    }

    this.respawnTimers.forEach((t) => t.remove());
    this.respawnTimers = [];

    this.projectilesGroup?.clear(true, true);
    this.enemyProjectilesGroup?.clear(true, true);
  }

  private restartGame(): void {
    this.freezeAll();
    this.enemiesDefeated = 0;
    const bug = this.getBugParam();
    const nextData: {
      gameIR: GameIR;
      isRestart?: boolean;
      prevHealth?: number;
      enemiesPaused?: boolean;
    } = {
      gameIR: this.gameIR,
      isRestart: true,
      enemiesPaused: this.enemiesPaused,
    };
    if (bug === 'restart_keeps_hp') {
      nextData.prevHealth = this.currentHealth;
    }
    this.scene.restart(nextData);
  }

  // ==========================================
  // QA Test Hook Methods (window.__AETHER_GAME__)
  // ==========================================

  public getQAState(): GameState {
    let status: 'playing' | 'won' | 'lost' = 'playing';
    if (this.isGameWon) {
      status = 'won';
    } else if (this.isGameOver) {
      status = 'lost';
    }

    const activeEnemies = this.enemies
      ? this.enemies.getChildren().filter((e) => e.active).length
      : 0;

    const remainingCollectibles = this.collectiblesGroup
      ? this.collectiblesGroup.getChildren().filter((c) => c.active).length
      : 0;

    const activeProjectiles =
      (this.projectilesGroup ? this.projectilesGroup.getChildren().filter((p) => p.active).length : 0) +
      (this.enemyProjectilesGroup ? this.enemyProjectilesGroup.getChildren().filter((p) => p.active).length : 0);

    return {
      status,
      hp: this.currentHealth,
      maxHp: this.maxHealth,
      score: this.gameIR.objective?.type==='survive_endless'?this.timeElapsed:this.gameIR.objective?.type === 'defeat_enemies' ? this.enemiesDefeated : this.score,
      target:
        this.gameIR.objective?.type === 'survive_seconds'
          ? (this.gameIR.objective.target ?? 30)
          : this.targetScore,
      objectiveType:
        this.gameIR.objective?.type ?? 'collect_count',
      timeElapsed: this.timeElapsed,
      timeLeft:
        this.gameIR.objective?.type === 'survive_seconds'
          ? this.survivalTimeRemaining
          : null,
      attackMode: this.gameIR.player?.attack_mode ?? 'avoid_only',
      attacksPerformed: this.attacksPerformed,
      player: {
        x: Math.round(this.player?.x ?? 0),
        y: Math.round(this.player?.y ?? 0),
      },
      enemyCount: activeEnemies,
      collectibleCount: remainingCollectibles,
      projectileCount: activeProjectiles,
      hud: {
        health: this.healthText?.text ?? '',
        objective: this.objectiveText?.text ?? '',
        controls: this.controlsText?.text ?? '',
      },
    };
  }

  public advanceTimer(seconds: number): void {
    if (this.isGameOver || this.isGameWon) return;

    if (this.gameIR.objective?.type === 'survive_seconds') {
      this.survivalTimeRemaining = Math.max(0, this.survivalTimeRemaining - seconds);
      this.timeElapsed += seconds;
      this.updateHUD();

      if (this.survivalTimeRemaining <= 0) {
        this.triggerGameWin();
      }
    } else {
      this.timeElapsed += seconds;
    }
  }

  public simulatePickup(): void {
    if (this.isGameOver || this.isGameWon) return;

    if (this.gameIR.objective?.type === 'defeat_enemies') {
      let activeEnemy: Phaser.GameObjects.Rectangle | null = null;
      if (this.enemies) {
        const activeEnemies = this.enemies.getChildren().filter((e) => e.active);
        if (activeEnemies.length > 0) {
          activeEnemy = activeEnemies[0] as Phaser.GameObjects.Rectangle;
        }
      }
      if (activeEnemy) {
        this.killEnemy(activeEnemy);
      } else {
        this.enemiesDefeated += 1;
        this.score = this.enemiesDefeated;
        this.updateHUD();
        if (this.enemiesDefeated >= this.targetScore) {
          this.triggerGameWin();
        }
      }
      return;
    }

    let item: Phaser.GameObjects.Arc | null = null;
    if (this.collectiblesGroup) {
      const activeItems = this.collectiblesGroup
        .getChildren()
        .filter((c) => c.active);
      if (activeItems.length > 0) {
        item = activeItems[0] as Phaser.GameObjects.Arc;
      }
    }

    if (item) {
      this.handleCollectiblePickup(item);
    } else {
      // Direct logic fallback
      this.score += 1;
      this.updateHUD();
      if (
        this.gameIR.objective?.type === 'collect_count' &&
        this.score >= this.targetScore
      ) {
        this.triggerGameWin();
      }
    }
  }

  public damagePlayer(n: number): void {
    if (this.isGameOver || this.isGameWon) return;

    this.currentHealth = Math.max(0, this.currentHealth - n);
    this.updateHUD();

    if (this.currentHealth <= 0) {
      this.triggerGameOver();
      return;
    }

    // Normal hit blink feedback
    this.isInvulnerable = true;
    this.tweens.add({
      targets: this.player,
      alpha: 0.2,
      duration: 100,
      yoyo: true,
      repeat: 4,
      onComplete: () => {
        this.player.alpha = 1;
        this.isInvulnerable = false;
      },
    });
  }

  public getEnemyPositions(): EnemyPosition[] {
    if (!this.enemies) return [];
    return this.enemies
      .getChildren()
      .filter((e) => e.active)
      .map((enemyObj) => {
        const e = enemyObj as Phaser.GameObjects.Rectangle;
        return {
          x: Math.round(e.x),
          y: Math.round(e.y),
        };
      });
  }

  public pauseEnemies(paused: boolean): void {
    this.enemiesPaused = paused;
    if (paused && this.enemies) {
      this.enemies.getChildren().forEach((enemyObj) => {
        const enemy = enemyObj as Phaser.GameObjects.Rectangle;
        const enemyBody = enemy.body as Phaser.Physics.Arcade.Body;
        enemyBody?.setVelocity(0, 0);
      });
    }
  }

  update(_time: number, delta: number): void {
    if(this.gameIR.survival_stream){
      const focused=this.game.canvas.closest('.game-surface')?.contains(document.activeElement);
      this.time.paused=!focused;
      if(!focused){this.physics.pause();return;}
      if(!this.isGameOver&&!this.isGameWon)this.physics.resume();
    }
    this.totalGameTimeMs += delta;
    // Increment tick for QA test runner confirmation
    if (typeof window !== 'undefined' && window.__AETHER_GAME__) {
      window.__AETHER_GAME__.tick += 1;
      window.__AETHER_GAME__.gameTimeMs = this.totalGameTimeMs;
    }

    // R key restart
    if (this.requestRestart || this.rKey && Phaser.Input.Keyboard.JustDown(this.rKey)) {
      this.restartGame();
      return;
    }

    if (this.isGameOver || this.isGameWon) {
      return;
    }

    // Space key: Attack trigger
    if (this.spaceKey && Phaser.Input.Keyboard.JustDown(this.spaceKey)) {
      this.handleAttack();
    }

    if (!this.player || !this.player.body) return;

    // Thematic primitive shapes decorative overlay
    if (this.decoGraphics) {
      this.decoGraphics.clear();
      this.decoGraphics.setAlpha(this.player?.alpha ?? 1);
      const theme = this.themeConfig;
      const pShape = this.gameIR.visual_overrides?.player_shape;
      const eShape = this.gameIR.visual_overrides?.enemy_shape;

      const drawCustomShape = (g: Phaser.GameObjects.Graphics, shape: string, x: number, y: number, sz: number) => {
        if (shape === 'circle') {
          g.fillCircle(x, y, sz);
        } else if (shape === 'square') {
          g.fillRect(x - sz, y - sz, sz * 2, sz * 2);
        } else if (shape === 'triangle') {
          g.fillTriangle(x, y - sz - 2, x - sz, y + sz, x + sz, y + sz);
        } else if (shape === 'diamond') {
          g.fillTriangle(x, y - sz - 2, x - sz, y, x + sz, y);
          g.fillTriangle(x, y + sz + 2, x - sz, y, x + sz, y);
        }
      };

      // 1. Player thematic primitive shape
      if (this.player && this.player.active) {
        const px = this.player.x;
        const py = this.player.y;
        this.decoGraphics.fillStyle(theme.playerAccent, 1);
        if (pShape) {
          drawCustomShape(this.decoGraphics, pShape, px, py, 7);
        } else if (theme.name === 'fantasy') {
          // Arcane knight diamond rune
          this.decoGraphics.fillTriangle(px, py - 9, px - 7, py, px + 7, py);
          this.decoGraphics.fillTriangle(px, py + 9, px - 7, py, px + 7, py);
        } else if (theme.name === 'sci_fi') {
          // Cyber drone sensor visor & energy core
          this.decoGraphics.fillRect(px - 7, py - 3, 14, 3);
          this.decoGraphics.fillCircle(px, py + 3, 3);
        } else if (theme.name === 'pirate') {
          // Captain emblem cross
          this.decoGraphics.fillRect(px - 2, py - 8, 4, 16);
          this.decoGraphics.fillRect(px - 7, py - 3, 14, 4);
        } else if (theme.name === 'spooky') {
          // Wizard twin wisp eyes
          this.decoGraphics.fillCircle(px - 5, py - 2, 2.5);
          this.decoGraphics.fillCircle(px + 5, py - 2, 2.5);
        } else if (theme.name === 'cozy') {
          // 4-petal flower / clover
          this.decoGraphics.fillCircle(px - 3, py - 3, 2.5);
          this.decoGraphics.fillCircle(px + 3, py - 3, 2.5);
          this.decoGraphics.fillCircle(px - 3, py + 3, 2.5);
          this.decoGraphics.fillCircle(px + 3, py + 3, 2.5);
        }
      }

      // 2. Enemies thematic primitive shapes
      if (this.enemies) {
        this.enemies.getChildren().forEach((enemyObj) => {
          const enemy = enemyObj as Phaser.GameObjects.Rectangle;
          if (!enemy.active) return;
          const ex = enemy.x;
          const ey = enemy.y;
          this.decoGraphics!.fillStyle(theme.enemyAccent, 1);

          if (eShape) {
            drawCustomShape(this.decoGraphics!, eShape, ex, ey, 6);
          } else if (theme.name === 'fantasy') {
            // Goblin horns
            this.decoGraphics!.fillTriangle(ex - 7, ey - 10, ex - 4, ey - 5, ex - 10, ey - 5);
            this.decoGraphics!.fillTriangle(ex + 7, ey - 10, ex + 4, ey - 5, ex + 10, ey - 5);
          } else if (theme.name === 'sci_fi') {
            // Sensor LED slit
            this.decoGraphics!.fillRect(ex - 7, ey - 2, 14, 3);
          } else if (theme.name === 'pirate') {
            // Eyepatch diagonal slash
            this.decoGraphics!.fillRect(ex - 6, ey - 5, 12, 2);
            this.decoGraphics!.fillCircle(ex - 3, ey - 1, 2);
          } else if (theme.name === 'spooky') {
            // Phantom hollow eyes
            this.decoGraphics!.fillCircle(ex - 4, ey - 3, 2);
            this.decoGraphics!.fillCircle(ex + 4, ey - 3, 2);
          } else if (theme.name === 'cozy') {
            // Bramble thorn diamond
            this.decoGraphics!.fillTriangle(ex, ey - 5, ex - 4, ey + 3, ex + 4, ey + 3);
          }
        });
      }

      // 3. Collectibles thematic primitive shapes
      if (this.collectiblesGroup) {
        this.collectiblesGroup.getChildren().forEach((itemObj) => {
          const item = itemObj as Phaser.GameObjects.Arc;
          if (!item.active) return;
          const cx = item.x;
          const cy = item.y;
          this.decoGraphics!.fillStyle(theme.collectibleAccent, 1);

          if (theme.name === 'fantasy') {
            // Mana crystal inner diamond facet
            this.decoGraphics!.fillTriangle(cx, cy - 5, cx - 4, cy, cx + 4, cy);
            this.decoGraphics!.fillTriangle(cx, cy + 5, cx - 4, cy, cx + 4, cy);
          } else if (theme.name === 'sci_fi') {
            // Battery capacitor charge bars
            this.decoGraphics!.fillRect(cx - 3, cy - 3, 6, 2);
            this.decoGraphics!.fillRect(cx - 3, cy + 1, 6, 2);
          } else if (theme.name === 'pirate') {
            // Gold coin embossed center dot
            this.decoGraphics!.fillCircle(cx, cy, 3);
          } else if (theme.name === 'spooky') {
            // Soul spark teardrop / flame
            this.decoGraphics!.fillCircle(cx, cy + 1, 2.5);
            this.decoGraphics!.fillTriangle(cx, cy - 5, cx - 2, cy, cx + 2, cy);
          } else if (theme.name === 'cozy') {
            // 4-point enchanted star
            this.decoGraphics!.fillTriangle(cx, cy - 5, cx - 2, cy + 2, cx + 2, cy + 2);
            this.decoGraphics!.fillTriangle(cx, cy + 5, cx - 2, cy - 2, cx + 2, cy - 2);
            this.decoGraphics!.fillTriangle(cx - 5, cy, cx + 2, cy - 2, cx + 2, cy + 2);
            this.decoGraphics!.fillTriangle(cx + 5, cy, cx - 2, cy - 2, cx - 2, cy + 2);
          }
        });
      }
    }

    const playerBody = this.player.body as Phaser.Physics.Arcade.Body;
    const speed = this.gameIR?.player?.move_speed ?? 200;

    // Update player movement (unless in active knockback recoil)
    if (!this.isKnockedBack) {
      let ix = 0;
      let iy = 0;

      const leftPressed =
        Boolean(this.cursors?.left?.isDown) || Boolean(this.wasdKeys?.A?.isDown) || Boolean(this.touch.left);
      const rightPressed =
        Boolean(this.cursors?.right?.isDown) || Boolean(this.wasdKeys?.D?.isDown) || Boolean(this.touch.right);
      const upPressed =
        Boolean(this.cursors?.up?.isDown) || Boolean(this.wasdKeys?.W?.isDown) || Boolean(this.touch.up);
      const downPressed =
        Boolean(this.cursors?.down?.isDown) || Boolean(this.wasdKeys?.S?.isDown) || Boolean(this.touch.down);

      if (leftPressed) ix -= 1;
      if (rightPressed) ix += 1;
      if (upPressed) iy -= 1;
      if (downPressed) iy += 1;

      // Discard input along blocked axis when against world bounds before normalizing
      const isBlockedX =
        (ix < 0 && (playerBody.blocked.left || playerBody.x <= 0)) ||
        (ix > 0 && (playerBody.blocked.right || playerBody.right >= this.scale.width));
      const isBlockedY =
        (iy < 0 && (playerBody.blocked.up || playerBody.y <= 0)) ||
        (iy > 0 && (playerBody.blocked.down || playerBody.bottom >= this.scale.height));

      if (isBlockedX) ix = 0;
      if (isBlockedY) iy = 0;

      const len = Math.hypot(ix, iy);
      let vx = 0;
      let vy = 0;
      if (len > 0) {
        vx = (ix / len) * speed;
        vy = (iy / len) * speed;
      }

      playerBody.setVelocity(vx, vy);
    }

    const stream=this.gameIR.survival_stream;
    if(stream&&!this.enemiesPaused&&this.time.now>=this.streamNextAt){
      this.streamNextAt=this.time.now+stream.spawn_interval_ms;
      if(this.enemies.getLength()<stream.max_active){
        const point=safeSpawn(this.rng,this.scale.width,this.scale.height,this.player,stream.safe_radius);
        if(point){const config=this.gameIR.enemies[Math.floor(this.rng()*this.gameIR.enemies.length)];this.respawnEnemy(config.type,config.speed,point);}
      }
    }
    // Update enemies: multi-type behaviours if not paused
    if (!this.enemiesPaused) {
      const now = this.time.now;
      this.enemies.getChildren().forEach((enemyObj) => {
        const enemy = enemyObj as Phaser.GameObjects.Rectangle;
        const enemyBody = enemy.body as Phaser.Physics.Arcade.Body;
        if (!enemyBody || !enemy.active) return;

        const enemyType = (enemy.getData('enemyType') as string) || 'chaser';
        const baseSpeed = (enemy.getData('speed') as number) ?? 75.0;
        if(stream){
          const age=now-(enemy.getData('bornAt')??now);
          const label=enemy.getData('streamLabel') as Phaser.GameObjects.Text;
          label?.setPosition(enemy.x,enemy.y-24);
          if(age<stream.warning_ms){enemy.setAlpha(.45);enemyBody.setVelocity(0,0);return;}
          enemy.setAlpha(1);
          if(enemyType==='chaser'&&age>=stream.chaser_lifetime_ms){enemy.destroy();return;}
        }

        if (enemyType === 'chaser') {
          const angle = Phaser.Math.Angle.Between(
            enemy.x,
            enemy.y,
            this.player.x,
            this.player.y
          );
          enemyBody.setVelocity(
            Math.cos(angle) * baseSpeed,
            Math.sin(angle) * baseSpeed
          );
        } else if (enemyType === 'bouncer') {
          // Bouncer maintains constant diagonal velocity and ricochets
          let vx = enemyBody.velocity.x;
          let vy = enemyBody.velocity.y;
          if (Math.abs(vx) < 1 && Math.abs(vy) < 1) {
            const bAngle = (enemy.getData('bounceVx') !== undefined)
              ? Math.atan2(enemy.getData('bounceVy'), enemy.getData('bounceVx'))
              : (Math.PI / 4);
            vx = Math.cos(bAngle) * baseSpeed;
            vy = Math.sin(bAngle) * baseSpeed;
            enemyBody.setVelocity(vx, vy);
          } else {
            const curSpd = Math.hypot(vx, vy);
            if (Math.abs(curSpd - baseSpeed) > 4) {
              const scale = baseSpeed / (curSpd || 1);
              enemyBody.setVelocity(vx * scale, vy * scale);
            }
          }
        } else if (enemyType === 'patroller') {
          // Moves back and forth along lane, reverses at walls/obstacles
          const axis = (enemy.getData('patrolAxis') as 'x' | 'y') || 'x';
          let dir = (enemy.getData('patrolDir') as number) || 1;
          const pad = 28;
          if (axis === 'x') {
            if (dir > 0 && (enemyBody.blocked.right || enemy.x >= this.scale.width - pad)) {
              dir = -1;
            } else if (dir < 0 && (enemyBody.blocked.left || enemy.x <= pad)) {
              dir = 1;
            }
            enemy.setData('patrolDir', dir);
            enemyBody.setVelocity(dir * baseSpeed, 0);
          } else {
            if (dir > 0 && (enemyBody.blocked.down || enemy.y >= this.scale.height - pad)) {
              dir = -1;
            } else if (dir < 0 && (enemyBody.blocked.up || enemy.y <= pad)) {
              dir = 1;
            }
            enemy.setData('patrolDir', dir);
            enemyBody.setVelocity(0, dir * baseSpeed);
          }
        } else if (enemyType === 'dasher') {
          // Stalks slowly, then lunges at the player's last position
          const state = (enemy.getData('dashState') as string) || 'stalking';
          let timer = (enemy.getData('dashTimer') as number) || 0;
          timer += delta;
          enemy.setData('dashTimer', timer);

          if (state === 'stalking') {
            const angle = Phaser.Math.Angle.Between(enemy.x, enemy.y, this.player.x, this.player.y);
            enemyBody.setVelocity(
              Math.cos(angle) * (baseSpeed * 0.4),
              Math.sin(angle) * (baseSpeed * 0.4)
            );
            if (timer >= 2400) {
              enemy.setData('dashState', 'windup');
              enemy.setData('dashTimer', 0);
              enemyBody.setVelocity(0, 0);
              const lungeAngle = Phaser.Math.Angle.Between(enemy.x, enemy.y, this.player.x, this.player.y);
              enemy.setData('lungeAngle', lungeAngle);
            }
          } else if (state === 'windup') {
            enemyBody.setVelocity(0, 0);
            if (timer >= 400) {
              enemy.setData('dashState', 'lunging');
              enemy.setData('dashTimer', 0);
              const lAngle = (enemy.getData('lungeAngle') as number) ?? 0;
              enemyBody.setVelocity(
                Math.cos(lAngle) * (baseSpeed * 2.2),
                Math.sin(lAngle) * (baseSpeed * 2.2)
              );
            }
          } else if (state === 'lunging') {
            if (timer >= 500) {
              enemy.setData('dashState', 'stalking');
              enemy.setData('dashTimer', 0);
            }
          }
        } else if (enemyType === 'shooter') {
          // Keeps distance and fires slow bullets
          const dist = Math.hypot(this.player.x - enemy.x, this.player.y - enemy.y);
          const angle = Phaser.Math.Angle.Between(enemy.x, enemy.y, this.player.x, this.player.y);

          if (dist < 220) {
            enemyBody.setVelocity(
              -Math.cos(angle) * (baseSpeed * 0.8),
              -Math.sin(angle) * (baseSpeed * 0.8)
            );
          } else if (dist > 340) {
            enemyBody.setVelocity(
              Math.cos(angle) * (baseSpeed * 0.7),
              Math.sin(angle) * (baseSpeed * 0.7)
            );
          } else {
            const strafeAngle = angle + Math.PI / 2;
            enemyBody.setVelocity(
              Math.cos(strafeAngle) * (baseSpeed * 0.4),
              Math.sin(strafeAngle) * (baseSpeed * 0.4)
            );
          }

          const lastShoot = (enemy.getData('lastShootTime') as number) || 0;
          if(stream){
            const next=emitterStep(enemy.getData('shots')||0,lastShoot,now,stream);
            if(next.fire){this.shootEnemyBullet(enemy);this.streamShots++;this.streamFires.push({id:enemy.getData('streamId'),at:now,shot:next.shots});this.streamFires=this.streamFires.slice(-64);enemy.setData('lastShootTime',next.lastAt);enemy.setData('shots',next.shots);(enemy.getData('streamLabel') as Phaser.GameObjects.Text)?.setText(`S ${next.shots}/${stream.shooter_shots}`);}
            if(next.expired){this.streamExpired++;const record=this.streamTrace.find(r=>r.id===enemy.getData('streamId'));if(record)record.shots=next.shots;enemy.destroy();}
          } else if (now - lastShoot >= 2500) {
            enemy.setData('lastShootTime', now);
            this.shootEnemyBullet(enemy);
          }
        }
      });
    } else {
      this.enemies.getChildren().forEach((enemyObj) => {
        const enemy = enemyObj as Phaser.GameObjects.Rectangle;
        const enemyBody = enemy.body as Phaser.Physics.Arcade.Body;
        enemyBody?.setVelocity(0, 0);
      });
    }
  }
}




