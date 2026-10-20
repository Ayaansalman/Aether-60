import type { GameIR } from '../game/gameir';
import * as mockApi from './mockApi';
import type {
  GameStatus,
  GameStatusResponse,
  CreateGameResponse,
  QACheck,
  QAReport,
  GameEvent,
} from './mockApi';

export type {
  GameStatus,
  GameStatusResponse,
  CreateGameResponse,
  QACheck,
  QAReport,
  GameEvent,
};

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';

/**
 * Creates a new game generation task.
 * Corresponds to POST /api/v1/games per Blueprint Section 6.
 */
export async function createGame(prompt: string): Promise<CreateGameResponse> {
  if (USE_MOCK) {
    return mockApi.createGame(prompt);
  }

  const res = await fetch(`${BASE_URL}/api/v1/games`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt }),
  });

  if (!res.ok) {
    let errMessage = `Failed to create game (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      } else if (errData.message) {
        errMessage = errData.message;
      }
    } catch {
      // Use fallback error message
    }
    throw new Error(errMessage);
  }

  return res.json();
}

/**
 * Fetches status for a game synthesis job.
 * Corresponds to GET /api/v1/games/{id} per Blueprint Section 6.
 */
export async function getGame(id: string): Promise<GameStatusResponse> {
  if (USE_MOCK) {
    return mockApi.getGame(id);
  }

  const res = await fetch(`${BASE_URL}/api/v1/games/${id}`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    let errMessage = `Failed to get game status (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) errMessage = errData.detail;
    } catch {
      // Use fallback error message
    }
    throw new Error(errMessage);
  }

  return res.json();
}

/**
 * Fetches the validated GameIR specification.
 * Corresponds to GET /api/v1/games/{id}/spec per Blueprint Section 6.
 */
export async function getSpec(id: string): Promise<GameIR> {
  if (USE_MOCK) {
    return mockApi.getSpec(id);
  }

  const res = await fetch(`${BASE_URL}/api/v1/games/${id}/spec`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    let errMessage = `Failed to load GameIR specification (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) errMessage = errData.detail;
    } catch {
      // Use fallback
    }
    throw new Error(errMessage);
  }

  return res.json();
}

/**
 * Fetches the automated QA test report.
 * Corresponds to GET /api/v1/games/{id}/qa per Blueprint Section 6 & 7.3.
 */
export async function getQa(id: string): Promise<QAReport> {
  if (USE_MOCK) {
    return mockApi.getQa(id);
  }

  const res = await fetch(`${BASE_URL}/api/v1/games/${id}/qa`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    let errMessage = `Failed to get QA report (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) errMessage = errData.detail;
    } catch {
      // Use fallback
    }
    throw new Error(errMessage);
  }

  return res.json();
}

/**
 * Fetches the lifecycle events for a game.
 * Corresponds to GET /api/v1/games/{id}/events per Blueprint Section 6.
 */
export async function getEvents(id: string): Promise<GameEvent[]> {
  if (USE_MOCK) {
    return mockApi.getEvents(id);
  }

  const res = await fetch(`${BASE_URL}/api/v1/games/${id}/events`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    let errMessage = `Failed to load game events (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) errMessage = errData.detail;
    } catch {
      // Use fallback
    }
    throw new Error(errMessage);
  }

  const rawEvents = (await res.json()) as Array<{
    id?: number;
    game_id?: string;
    stage?: GameStatus;
    ts?: string;
    timestamp?: string;
    detail?: string;
    message?: string;
    rationale?: string | null;
    repair_rationale?: string | null;
    [key: string]: unknown;
  }>;
  return (rawEvents || []).map((e): GameEvent => ({
    ...e,
    stage: e.stage || 'BUILDING',
    ts: e.ts || e.timestamp || new Date().toISOString(),
    timestamp: e.timestamp || e.ts || new Date().toISOString(),
    detail: e.detail || e.message || '',
    message: e.message || e.detail || '',
    rationale: e.rationale || e.repair_rationale || null,
    repair_rationale: e.repair_rationale || e.rationale || null,
  }));
}
