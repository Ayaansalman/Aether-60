import type { GameIR, GameTheme, AttackMode } from '../game/gameir';
import sampleGameIR from '../game/sample-gameir.json';

export type GameStatus =
  | 'QUEUED'
  | 'PLANNING'
  | 'VALIDATING_SPEC'
  | 'BUILDING'
  | 'TESTING'
  | 'REPAIRING'
  | 'READY'
  | 'READY_WITH_WARNINGS'
  | 'FAILED';

export interface QACheck {
  id: string;
  critical: boolean;
  passed: boolean;
  message?: string;
  patchable?: boolean;
  details?: Record<string, unknown>;
  measured?: unknown;
  [key: string]: unknown;
}

export interface QAReport {
  url: string;
  overall: 'PASS' | 'FAIL';
  checks: QACheck[];
  page_errors?: string[];
  screenshot_path?: string;
  repair_recommended?: boolean;
}

export interface GameEvent {
  id?: number;
  game_id?: string;
  ts: string;
  timestamp: string;
  stage: GameStatus;
  result?: string;
  detail: string;
  message: string;
  attempt?: number;
  rationale?: string | null;
  repair_rationale?: string | null;
  diff?: {
    before?: Record<string, unknown>;
    after?: Record<string, unknown>;
  } | null;
}

export interface GameStatusResponse {
  game_id: string;
  status: GameStatus;
  stage: string;
  prompt: string;
  attempt?: number;
  max_attempts?: number;
  created_at: string;
  updated_at: string;
  game_url?: string | null;
  qa_summary?: {
    passed: number;
    failed: number;
    critical_failed: string[];
  } | null;
  error_code?: string | null;
  error_message?: string | null;
  limitations?: string[];
  spec?: GameIR | null;
  qa?: QAReport | null;
  repair_rationale?: string | null;
  diff?: {
    before?: Record<string, unknown>;
    after?: Record<string, unknown>;
  } | null;
}

export interface CreateGameResponse {
  game_id: string;
  status: GameStatus;
  stage: string;
  message: string;
  created_at?: string;
  prompt?: string;
}

interface MockGameEntry {
  id: string;
  prompt: string;
  createdAt: number;
  isRepairDemo: boolean;
  spec: GameIR;
  repairedSpec: GameIR;
  repairRationale: string;
  diff: {
    before: Record<string, unknown>;
    after: Record<string, unknown>;
  };
}

// In-memory fake database
const mockGames = new Map<string, MockGameEntry>();

// Session storage sync key
const STORAGE_PREFIX = 'aether_mock_game_';

function persistGame(entry: MockGameEntry): void {
  try {
    sessionStorage.setItem(`${STORAGE_PREFIX}${entry.id}`, JSON.stringify(entry));
  } catch {
    // Ignore storage quota errors in mock
  }
}

function restoreGame(id: string): MockGameEntry | undefined {
  if (mockGames.has(id)) {
    return mockGames.get(id);
  }
  try {
    const raw = sessionStorage.getItem(`${STORAGE_PREFIX}${id}`);
    if (raw) {
      const entry = JSON.parse(raw) as MockGameEntry;
      mockGames.set(id, entry);
      return entry;
    }
  } catch {
    // Ignore storage parse errors
  }
  return undefined;
}

/**
 * Keyword-based GameIR generator mimicking section 7.2 / mock provider.
 */
function buildSpecFromPrompt(prompt: string): GameIR {
  const p = prompt.toLowerCase();

  let theme: GameTheme = 'fantasy';
  let title = 'Enchanted Arena Survival';
  let premise = 'Collect magical stars while fantasy golems chase the hero.';
  let colType = 'star';

  if (p.includes('spooky')) {
    theme = 'spooky';
    title = 'Wizard Crystal Rush';
    premise = 'Collect crystals while ghosts chase the player.';
    colType = 'crystal';
  } else if (p.includes('pirate')) {
    theme = 'pirate';
    title = "Pirate Captain's Cove";
    premise = 'Survive the stormy cove while rival pirate chasers attempt to capture the ship.';
    colType = 'coin';
  } else if (p.includes('robot') || p.includes('sci-fi') || p.includes('scifi') || p.includes('cyber')) {
    theme = 'sci_fi';
    title = 'Neon Cybernetic Survival';
    premise = 'Outmaneuver rogue robotic drones in the neon cyber arena.';
    colType = 'battery';
  } else if (p.includes('cozy')) {
    theme = 'cozy';
    title = 'Cozy Garden Gathering';
    premise = 'Collect fallen gems while gentle forest critters chase you around the garden.';
    colType = 'gem';
  }

  const isSurvive = p.includes('survive') || p.includes('survival') || p.includes('seconds') || p.includes('timer');
  const isMelee = p.includes('melee') || p.includes('slash') || p.includes('sword') || p.includes('punch');
  const isAvoid = p.includes('avoid') || (!isMelee && isSurvive && !p.includes('attack'));

  const attackMode: AttackMode = isMelee ? 'melee' : (isAvoid ? 'avoid_only' : 'projectile');

  const base = JSON.parse(JSON.stringify(sampleGameIR)) as GameIR;
  base.title = title;
  base.theme = theme;
  base.premise = premise;
  base.player.attack_mode = attackMode;

  if (isSurvive) {
    base.objective = {
      type: 'survive_seconds',
      target: 30,
    };
    base.collectibles = [];
    base.controls = {
      movement: 'WASD or arrow keys',
      ...(attackMode !== 'avoid_only' ? { attack: 'Space' } : {}),
    };
  } else {
    base.objective = {
      type: 'collect_count',
      target: 8,
    };
    base.collectibles = [
      {
        type: colType,
        count: 10,
      },
    ];
    base.controls = {
      movement: 'WASD or arrow keys',
      attack: attackMode !== 'avoid_only' ? 'Space' : undefined,
    };
  }

  return base;
}

function buildPassingChecks(): QACheck[] {
  return [
    { id: 'canvas_visible', critical: true, passed: true, message: 'Canvas visible in viewport' },
    { id: 'hook_ready', critical: true, passed: true, message: 'Hook ready and ticking' },
    { id: 'no_page_errors', critical: true, passed: true, message: 'No console or page errors' },
    { id: 'player_present', critical: true, passed: true, message: 'Player coordinate within bounds' },
    { id: 'player_moves', critical: true, passed: true, message: 'Straight and diagonal speed within 15%' },
    { id: 'player_attacks', critical: true, passed: true, message: 'Attack executed and registered' },
    { id: 'enemies_present', critical: true, passed: true, message: 'Enemies spawned' },
    { id: 'hud_visible', critical: true, passed: true, message: 'HUD displayed' },
    { id: 'win_condition_verified', critical: true, passed: true, message: 'Win state achievable' },
    { id: 'restart_resets_after_win', critical: true, passed: true, message: 'State reset on restart' },
    { id: 'lose_condition_verified', critical: true, passed: true, message: 'Loss state triggerable' },
    { id: 'restart_resets_after_lose', critical: true, passed: true, message: 'State reset on restart' },
    { id: 'no_duplicate_enemies_after_restart', critical: true, passed: true, message: 'Enemy count preserved' },
    { id: 'screenshot_captured', critical: true, passed: true, message: 'Screenshot saved' },
  ];
}

function buildFailingChecks(): QACheck[] {
  return [
    { id: 'canvas_visible', critical: true, passed: true, message: 'Canvas visible in viewport' },
    { id: 'hook_ready', critical: true, passed: true, message: 'Hook ready and ticking' },
    { id: 'no_page_errors', critical: true, passed: true, message: 'No console or page errors' },
    { id: 'player_present', critical: true, passed: true, message: 'Player coordinate within bounds' },
    {
      id: 'player_moves',
      critical: true,
      passed: false,
      message: 'Diagonal movement distance deviates by 28.4% from straight movement (tolerance limit: 15%)',
    },
    { id: 'player_attacks', critical: true, passed: true, message: 'Attack executed and registered' },
    { id: 'enemies_present', critical: true, passed: true, message: 'Enemies spawned' },
    { id: 'hud_visible', critical: true, passed: true, message: 'HUD displayed' },
    { id: 'win_condition_verified', critical: true, passed: true, message: 'Win state achievable' },
    { id: 'restart_resets_after_win', critical: true, passed: true, message: 'State reset on restart' },
    { id: 'lose_condition_verified', critical: true, passed: true, message: 'Loss state triggerable' },
    { id: 'restart_resets_after_lose', critical: true, passed: true, message: 'State reset on restart' },
    { id: 'no_duplicate_enemies_after_restart', critical: true, passed: true, message: 'Enemy count preserved' },
    { id: 'screenshot_captured', critical: true, passed: true, message: 'Screenshot saved' },
  ];
}

// Stage sequences
const NORMAL_STAGES: GameStatus[] = ['QUEUED', 'PLANNING', 'VALIDATING_SPEC', 'BUILDING', 'TESTING', 'READY'];
const REPAIR_STAGES: GameStatus[] = [
  'QUEUED',
  'PLANNING',
  'VALIDATING_SPEC',
  'BUILDING',
  'TESTING',
  'REPAIRING',
  'VALIDATING_SPEC',
  'BUILDING',
  'TESTING',
  'READY',
];

const STAGE_INTERVAL_MS = 1500;

function getStageIndex(createdAt: number, maxIndex: number): number {
  const elapsed = Date.now() - createdAt;
  const index = Math.floor(elapsed / STAGE_INTERVAL_MS);
  return Math.min(index, maxIndex);
}

export async function createGame(prompt: string): Promise<CreateGameResponse> {
  const trimmed = prompt.trim();
  if (!trimmed) {
    throw new Error('Prompt cannot be empty');
  }

  const id = `game-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  const now = Date.now();
  const isRepairDemo = trimmed.toLowerCase().includes('repair demo');

  const baseSpec = buildSpecFromPrompt(trimmed);
  const initialSpec = JSON.parse(JSON.stringify(baseSpec)) as GameIR;
  const repairedSpec = JSON.parse(JSON.stringify(baseSpec)) as GameIR;

  const repairRationale =
    "QA check 'player_moves' failed: Player move speed (340 px/s) exceeded tolerance bounds and diagonal movement was desynchronized. Clamped move_speed to 220 px/s and normalized diagonal vectors.";

  const diff = {
    before: {
      player: {
        move_speed: 340,
        max_health: 3,
        attack_mode: initialSpec.player.attack_mode,
      },
      enemies: [
        {
          type: 'chaser',
          count: 8,
          speed: 110,
        },
      ],
    },
    after: {
      player: {
        move_speed: 220,
        max_health: 3,
        attack_mode: repairedSpec.player.attack_mode,
      },
      enemies: [
        {
          type: 'chaser',
          count: 5,
          speed: 75,
        },
      ],
    },
  };

  if (isRepairDemo) {
    initialSpec.player.move_speed = 340;
    initialSpec.enemies = [{ type: 'chaser', count: 8, speed: 110 }];
    repairedSpec.player.move_speed = 220;
    repairedSpec.enemies = [{ type: 'chaser', count: 5, speed: 75 }];
  }

  const entry: MockGameEntry = {
    id,
    prompt: trimmed,
    createdAt: now,
    isRepairDemo,
    spec: initialSpec,
    repairedSpec,
    repairRationale,
    diff,
  };

  mockGames.set(id, entry);
  persistGame(entry);

  return {
    game_id: id,
    status: 'QUEUED',
    stage: 'QUEUED',
    message: 'Job accepted and queued for processing',
    created_at: new Date(now).toISOString(),
    prompt: trimmed,
  };
}

export async function getGame(id: string): Promise<GameStatusResponse> {
  const entry = restoreGame(id);
  if (!entry) {
    throw new Error(`Game not found: ${id}`);
  }

  const stages = entry.isRepairDemo ? REPAIR_STAGES : NORMAL_STAGES;
  const stageIndex = getStageIndex(entry.createdAt, stages.length - 1);
  const currentStage = stages[stageIndex];

  // In repair demo, initial TESTING stage (index 4) fails QA
  let qa: QAReport | null = null;
  if (entry.isRepairDemo) {
    if (stageIndex === 4 || stageIndex === 5) {
      qa = {
        url: `http://localhost:5173/play/${id}?test=1`,
        overall: 'FAIL',
        checks: buildFailingChecks(),
        page_errors: [],
        screenshot_path: `artifacts/qa/${id}.png`,
        repair_recommended: true,
      };
    } else if (stageIndex >= 8) {
      qa = {
        url: `http://localhost:5173/play/${id}?test=1`,
        overall: 'PASS',
        checks: buildPassingChecks(),
        page_errors: [],
        screenshot_path: `artifacts/qa/${id}.png`,
        repair_recommended: false,
      };
    }
  } else {
    if (stageIndex >= 4) {
      qa = {
        url: `http://localhost:5173/play/${id}?test=1`,
        overall: 'PASS',
        checks: buildPassingChecks(),
        page_errors: [],
        screenshot_path: `artifacts/qa/${id}.png`,
        repair_recommended: false,
      };
    }
  }

  const activeSpec = entry.isRepairDemo && stageIndex >= 5 ? entry.repairedSpec : entry.spec;
  const hasRepairData = entry.isRepairDemo && stageIndex >= 5;

  return {
    game_id: id,
    status: currentStage,
    stage: currentStage,
    prompt: entry.prompt,
    attempt: hasRepairData ? 2 : 1,
    max_attempts: 3,
    created_at: new Date(entry.createdAt).toISOString(),
    updated_at: new Date().toISOString(),
    game_url: `http://localhost:5173/play/${id}`,
    qa_summary: qa
      ? {
          passed: qa.checks.filter((c) => c.passed).length,
          failed: qa.checks.filter((c) => !c.passed).length,
          critical_failed: qa.checks.filter((c) => !c.passed && c.critical).map((c) => c.id),
        }
      : null,
    error_code: null,
    error_message: null,
    limitations: [
      'Adapted discrete wave dynamics to a continuous 2D top-down arena chaser field.',
    ],
    spec: activeSpec,
    qa,
    repair_rationale: hasRepairData ? entry.repairRationale : null,
    diff: hasRepairData ? entry.diff : null,
  };
}

export async function getSpec(id: string): Promise<GameIR> {
  const entry = restoreGame(id);
  if (!entry) {
    throw new Error(`Game not found: ${id}`);
  }
  const stages = entry.isRepairDemo ? REPAIR_STAGES : NORMAL_STAGES;
  const stageIndex = getStageIndex(entry.createdAt, stages.length - 1);
  return entry.isRepairDemo && stageIndex >= 5 ? entry.repairedSpec : entry.spec;
}

export async function getQa(id: string): Promise<QAReport> {
  const game = await getGame(id);
  if (game.qa) {
    return game.qa;
  }
  return {
    url: `http://localhost:5173/play/${id}?test=1`,
    overall: 'PASS',
    checks: buildPassingChecks(),
    page_errors: [],
    screenshot_path: `artifacts/qa/${id}.png`,
    repair_recommended: false,
  };
}

export async function getEvents(id: string): Promise<GameEvent[]> {
  const entry = restoreGame(id);
  if (!entry) {
    throw new Error(`Game not found: ${id}`);
  }

  const stages = entry.isRepairDemo ? REPAIR_STAGES : NORMAL_STAGES;
  const stageIndex = getStageIndex(entry.createdAt, stages.length - 1);

  const events: GameEvent[] = [];

  const stageMessagesNormal: Record<GameStatus, string> = {
    QUEUED: 'Game synthesis job accepted and queued for orchestration.',
    PLANNING: 'Synthesizing GameIR schema from user natural language prompt.',
    VALIDATING_SPEC: 'Validating GameIR v1 schema and property bounds.',
    BUILDING: 'Compiling scene parameters, physics bodies, and asset definitions.',
    TESTING: 'Executing Playwright headless automated QA validation suite.',
    REPAIRING: 'Repair service triggered.',
    READY: 'All 14 critical QA checks PASSED. Simulation ready.',
    READY_WITH_WARNINGS: 'Simulation ready with non-critical warnings.',
    FAILED: 'Simulation generation failed.',
  };

  if (!entry.isRepairDemo) {
    for (let i = 0; i <= stageIndex; i++) {
      const stage = stages[i];
      const eventTime = new Date(entry.createdAt + i * STAGE_INTERVAL_MS).toISOString();
      const msg = stageMessagesNormal[stage] || `Stage ${stage} completed.`;
      events.push({
        id: i + 1,
        game_id: id,
        ts: eventTime,
        timestamp: eventTime,
        stage,
        result: 'SUCCESS',
        detail: msg,
        message: msg,
        attempt: 1,
      });
    }
  } else {
    const repairMessages: { stage: GameStatus; message: string; rationale?: string; diff?: { before: Record<string, unknown>; after: Record<string, unknown> } }[] = [
      { stage: 'QUEUED', message: 'Game synthesis job accepted and queued for orchestration.' },
      { stage: 'PLANNING', message: 'Synthesizing initial GameIR specification from user prompt.' },
      { stage: 'VALIDATING_SPEC', message: 'Initial GameIR validated against schema structure.' },
      { stage: 'BUILDING', message: 'Compiling initial scene configurations and player attributes.' },
      { stage: 'TESTING', message: 'Playwright automated QA suite completed: 1 critical check FAILED (player_moves).' },
      {
        stage: 'REPAIRING',
        message: 'Bounded self-repair triggered: Clamping player speed and re-balancing enemy parameters.',
        rationale: entry.repairRationale,
        diff: entry.diff,
      },
      { stage: 'VALIDATING_SPEC', message: 'Re-validating patched GameIR specification against schema.' },
      { stage: 'BUILDING', message: 'Re-compiling game runtime with corrected parameters.' },
      { stage: 'TESTING', message: 'Re-running Playwright automated QA suite on patched build.' },
      { stage: 'READY', message: 'All 14 critical QA checks PASSED. Game binary ready for simulation.' },
    ];

    for (let i = 0; i <= stageIndex && i < repairMessages.length; i++) {
      const item = repairMessages[i];
      const eventTime = new Date(entry.createdAt + i * STAGE_INTERVAL_MS).toISOString();
      events.push({
        id: i + 1,
        game_id: id,
        ts: eventTime,
        timestamp: eventTime,
        stage: item.stage,
        result: item.stage === 'REPAIRING' ? 'START' : 'SUCCESS',
        detail: item.message,
        message: item.message,
        attempt: i >= 5 ? 2 : 1,
        rationale: item.rationale || null,
        repair_rationale: item.rationale || null,
        ...(item.diff ? { diff: item.diff } : {}),
      });
    }
  }

  return events;
}
