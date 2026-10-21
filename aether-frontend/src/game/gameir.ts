/**
 * GameIR (Game Intermediate Representation) v1
 * Central contract between natural-language planner and Phaser runtime.
 * Based on Section 5.1 of the 60% Capstone Engineering Specification.
 */

export type GameGenre = 'arena_survival';

export type GameTheme = 'fantasy' | 'sci_fi' | 'pirate' | 'spooky' | 'cozy' | string;

export type AttackMode = 'projectile' | 'melee' | 'avoid_only';

export interface PlayerConfig {
  move_speed: number; // e.g. 100 - 300
  max_health: number; // e.g. 1 - 10
  attack_mode: AttackMode;
}

export type EnemyType = 'chaser' | 'bouncer' | 'patroller' | 'dasher' | 'shooter' | string;

export interface EnemyConfig {
  type: EnemyType;
  count: number;
  speed: number;
}

export interface CollectibleConfig {
  type: string; // e.g. 'crystal', 'battery', 'coin', 'gem', 'star'
  count: number;
}

export type ObjectiveType = 'survive_endless' | 'survive_seconds' | 'collect_count' | 'defeat_enemies';

export interface ObjectiveConfig {
  type: ObjectiveType;
  target: number;
}

export type ArenaLayout = 'open' | 'pillars' | 'lanes' | 'maze';

export type ShapeType = 'circle' | 'square' | 'triangle' | 'diamond';

export interface VisualOverrides {
  player_label?: string;
  enemy_label?: string;
  collectible_label?: string;
  player_shape?: ShapeType;
  enemy_shape?: ShapeType;
  accent_hex?: string;
}

export interface ControlsConfig {
  movement: string;
  attack?: string | null;
  [key: string]: string | null | undefined;
}

export interface GameIR {
  survival_stream?: import('./survival/stream').SurvivalStream;
  schema_version: string; // "1.0"
  title: string;
  genre: GameGenre;
  premise: string;
  theme: GameTheme;
  arena_layout?: ArenaLayout;
  visual_overrides?: VisualOverrides;
  player: PlayerConfig;
  enemies: EnemyConfig[];
  collectibles: CollectibleConfig[];
  objective: ObjectiveConfig;
  difficulty: number; // 1 - 5
  controls: ControlsConfig;
  seed?: number;
}
