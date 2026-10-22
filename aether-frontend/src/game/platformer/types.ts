export interface BossEncounter {name:string;health:number;telegraph_ms:number;cooldown_ms:number;patterns:('charge'|'volley'|'slam')[];victory:'boss_defeat';ordinary_enemies:0}
export interface Platform {
  activation_sources?: string[];
  x: number;
  y: number;
  width: number;
  kind: string;
  moving: boolean;
  route?: "main" | "optional";
  motion?: Motion;
}
export interface Motion { axis: 'horizontal' | 'vertical'; pattern: 'sine' | 'ping_pong'; distance: number; period_ms: number }
export interface EnemyConfig { health: number; cooldown_ms: number; telegraph_ms: number; radius: number }
export interface Goal { id: string; kind: 'defeat' | 'activate' | 'unlock' | 'collect' | 'survive' | 'time_limit'; count: number; seconds: number; targets: string[]; enemy_behavior?: Entity['behavior'] | null }
export interface BehaviorLink { sources: string[]; target: string; condition: 'all' | 'any'; action: 'open_door' }
export interface Entity {
  disabled_by?: string[];
  boss?: BossEncounter | null;
  id?: string;
  x: number;
  y: number;
  kind: "crystal" | "enemy" | "spikes" | "checkpoint" | "exit" | "icicle" | "timed_hazard" | 'switch' | 'pressure_plate' | 'door';
  platform: number;
  behavior?: "patrol" | "chase" | "shooter" | 'turret' | 'ambusher';
  ai?: EnemyConfig;
  activation?: 'interact' | 'touch' | 'pressure' | 'proximity' | 'projectile';
  trigger?: "proximity" | "timer";
  period_ms?: number;
  radius?: number;
}
export interface PlatformerIR {
  boss?: BossEncounter | null;
  schema_version: "2.0";
  genre: "platformer";
  title: string;
  theme: string;
  seed: number;
  tile_size: number;
  width: number;
  height: number;
  spawn: { x: number; y: number };
  player: {
    speed: number;
    jump: number;
    gravity: number;
    health: number;
    abilities: string[];
  };
  objective: { type: string; required: number; total: number };
  platforms: Platform[];
  entities: Entity[];
  slippery?: boolean;
  exit_indicator?: "none" | "glow" | "pulse" | "flash";
  exit_style?: "shrine" | "gate" | "beacon";
  collectible?: "crystals" | "relics";
  camera_mode?: "follow" | "vertical";
  difficulty?: "relaxed" | "balanced" | "challenging";
  briefing?: string;
  topology?: "journey" | "ascent" | "terraces" | "cavern";
  player_attack?: 'stomp' | 'projectile';
  goals?: Goal[];
  links?: BehaviorLink[];
  campaign_goals?: Goal[];
  levels?: (Pick<PlatformerIR, "title" | "width" | "height" | "spawn" | "objective" | "platforms" | "entities" | "camera_mode"> &
    Partial<Pick<PlatformerIR, "theme" | "slippery" | "exit_style" | "exit_indicator" | "collectible" | "difficulty" | "briefing" | "topology" | 'player_attack' | 'goals' | 'links'>> )[];
  requirements?: { id: string; source: string; status: string; verified?: boolean }[];
}
export interface StudioJob {
  job: {
    game_id: string;
    prompt: string;
    status: string;
    model_id: string;
    limitations: string[];
    error_code?: string;
  };
  events: {
    id: number;
    ts: string;
    stage: string;
    result: string;
    detail: string;
    rationale: string;
  }[];
  artifacts: Record<string, unknown>;
}
