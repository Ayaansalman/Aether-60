/**
 * QA Test Hook Type Definitions for Playwright Automated E2E Runner.
 * Conforms to Section 7.1 of the 60% Capstone Engineering Specification.
 */

export interface PlayerState {
  x: number;
  y: number;
}

export interface EnemyPosition {
  x: number;
  y: number;
}

export interface HUDState {
  health: string;
  objective: string;
  controls: string;
}

export interface GameState {
  status: 'playing' | 'won' | 'lost';
  hp: number;
  maxHp: number;
  score: number;
  target: number;
  objectiveType: 'survive_endless' | 'survive_seconds' | 'collect_count' | 'defeat_enemies';
  timeElapsed: number;
  timeLeft: number | null;
  attackMode: 'projectile' | 'melee' | 'avoid_only';
  attacksPerformed: number;
  player: PlayerState;
  enemyCount: number;
  collectibleCount: number;
  projectileCount: number;
  hud: HUDState;
}

export interface AetherGameHook {
  ready: boolean;
  tick: number;
  gameTimeMs?: number;
  getState: () => GameState;
  advanceTimer: (seconds: number) => void;
  simulatePickup: () => void;
  damagePlayer: (n: number) => void;
  getEnemyPositions: () => EnemyPosition[];
  pauseEnemies: (paused: boolean) => void;
}

declare global {
  interface Window {
    __AETHER_GAME__?: AetherGameHook;
  }
}
