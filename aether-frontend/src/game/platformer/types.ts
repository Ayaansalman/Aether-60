export interface Platform {
  x: number;
  y: number;
  width: number;
  kind: string;
  moving: boolean;
}
export interface Entity {
  x: number;
  y: number;
  kind: "crystal" | "enemy" | "spikes" | "checkpoint" | "exit";
  platform: number;
}
export interface PlatformerIR {
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
