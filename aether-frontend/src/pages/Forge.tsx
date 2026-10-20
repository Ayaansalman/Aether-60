import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { GlassPanel } from '../components/GlassPanel';
import { createGame, getGame, getEvents, getQa, getSpec } from '../lib/apiClient';
import type { GameStatus, GameEvent, QAReport } from '../lib/apiClient';
import type { GameIR } from '../game/gameir';
import { SAVED_DEMOS, type SavedDemo } from '../game/savedDemos';
import {
  Sparkles,
  Send,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Gamepad2,
  ChevronDown,
  ChevronUp,
  Wrench,
  Terminal,
  Activity,
  FileCode,
  Check,
  XCircle,
} from 'lucide-react';

interface PromptChip {
  label: string;
  prompt: string;
}

const EXAMPLE_CHIPS: PromptChip[] = [
  {
    label: 'Spooky Wizard',
    prompt: 'Spooky wizard collecting crystals while ghosts chase the player in a haunted arena',
  },
  {
    label: 'Pirate Survival',
    prompt: 'Pirate captain surviving in a stormy cove dodging rival ships and cannons',
  },
  {
    label: 'Cyber Arena',
    prompt: 'Cybernetic robot in a sci-fi arena dodging rogue drones and collecting energy cells',
  },
  {
    label: 'Repair Demo',
    prompt: 'repair demo: cozy garden gathering with challenging rogue chasers and high difficulty',
  },
];

const STANDARD_STAGES: GameStatus[] = [
  'QUEUED',
  'PLANNING',
  'VALIDATING_SPEC',
  'BUILDING',
  'TESTING',
  'READY',
];

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

const STAGE_LABELS: Record<GameStatus, string> = {
  QUEUED: 'Queued',
  PLANNING: 'Planning',
  VALIDATING_SPEC: 'Validating Spec',
  BUILDING: 'Building',
  TESTING: 'Testing QA',
  REPAIRING: 'Repairing',
  READY: 'Ready',
  READY_WITH_WARNINGS: 'Ready (Warnings)',
  FAILED: 'Failed',
};

function getFriendlyErrorMessage(code: string | null | undefined, rawMsg?: string | null): string {
  if (code === 'PROMPT_INVALID') {
    return 'The prompt could not be parsed or violated content guidelines. Please refine your description.';
  }
  if (code === 'MODEL_TIMEOUT') {
    return 'The AI planning engine timed out. Please try again.';
  }
  if (code === 'MODEL_HTTP_ERROR') {
    return 'Upstream AI model connection failed. Please check service connectivity and try again.';
  }
  if (code === 'MODEL_OUTPUT_INVALID') {
    return 'The AI planner generated an invalid GameIR specification. Please retry.';
  }
  if (code === 'SPEC_UNSUPPORTED' || code === 'VALIDATION_FAILED') {
    return 'The game specification failed strict structural validation rules.';
  }
  if (code === 'QA_CRASHED') {
    return 'Automated browser verification runner crashed or timed out.';
  }
  if (code === 'QA_FAILED') {
    return 'A critical runtime check failed that cannot be repaired automatically (needs developer).';
  }
  if (code === 'REPAIR_LIMIT_REACHED') {
    return 'The game could not be repaired within the maximum number of attempts.';
  }
  if (code === 'GAME_NOT_FOUND') {
    return 'The requested game was not found.';
  }
  if (code === 'INTERNAL_ERROR') {
    return 'An internal server error occurred while processing the game.';
  }
  if (rawMsg) return rawMsg;
  return 'An unexpected error occurred during game synthesis.';
}

export const Forge: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const [activeGameId, setActiveGameId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<GameStatus | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [networkError, setNetworkError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [events, setEvents] = useState<GameEvent[]>([]);
  const [qaReport, setQaReport] = useState<QAReport | null>(null);
  const [spec, setSpec] = useState<GameIR | null>(null);
  const [limitations, setLimitations] = useState<string[]>([]);
  const [repairRationale, setRepairRationale] = useState<string | null>(null);
  const [repairDiff, setRepairDiff] = useState<{ before?: Record<string, unknown>; after?: Record<string, unknown> } | null>(null);
  const [loadedSavedDemo, setLoadedSavedDemo] = useState<SavedDemo | null>(null);

  // Technical Trace Drawer state
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'events' | 'repair' | 'qa' | 'spec'>('summary');

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isTerminal =
    currentStatus === 'READY' ||
    currentStatus === 'READY_WITH_WARNINGS' ||
    currentStatus === 'FAILED';

  const hasRepairOccurred =
    Boolean(repairRationale) ||
    Boolean(repairDiff) ||
    currentStatus === 'REPAIRING' ||
    events.some((e) => e.stage === 'REPAIRING');

  // Choose the timeline stages sequence based on whether repair was triggered
  const timelineStages = hasRepairOccurred ? REPAIR_STAGES : STANDARD_STAGES;

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const handlePoll = async (gameId: string) => {
    try {
      const game = await getGame(gameId);
      setNetworkError(false);
      setCurrentStatus(game.status);

      if (game.error_code) setErrorCode(game.error_code);
      if (game.error_message) setErrorMessage(game.error_message);

      if (game.repair_rationale) setRepairRationale(game.repair_rationale);
      if (game.diff) setRepairDiff(game.diff);
      if (game.spec) setSpec(game.spec);
      if (game.qa) setQaReport(game.qa);
      if (game.limitations && Array.isArray(game.limitations)) {
        setLimitations(game.limitations);
      }

      // Load events
      try {
        const evts = await getEvents(gameId);
        setEvents(evts);
        const repairEvt = evts.find(
          (e) => e.stage === 'REPAIRING' && (e.repair_rationale || e.rationale)
        );
        if (repairEvt) {
          const rat = repairEvt.repair_rationale || repairEvt.rationale || null;
          if (rat) setRepairRationale(rat);
          if (repairEvt.diff) setRepairDiff(repairEvt.diff);
        }
      } catch {
        // Events endpoint error is non-fatal
      }

      // Check if reached terminal state
      if (
        game.status === 'READY' ||
        game.status === 'READY_WITH_WARNINGS' ||
        game.status === 'FAILED'
      ) {
        stopPolling();
        setIsSubmitting(false);

        // Fetch final QA and spec if not already populated
        if (!game.spec) {
          getSpec(gameId).then((s) => setSpec(s)).catch(() => {});
        }
        if (!game.qa) {
          getQa(gameId).then((q) => setQaReport(q)).catch(() => {});
        }
      }
    } catch {
      setNetworkError(true);
      // Keep polling or allow user to click retry
    }
  };

  const startPolling = (gameId: string) => {
    stopPolling();
    // Poll every 1.5 seconds per requirements
    pollTimerRef.current = setInterval(() => {
      handlePoll(gameId);
    }, 1500);
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  const handleCreate = async () => {
    const trimmed = prompt.trim();
    if (!trimmed) {
      setValidationError('Please enter a game manifestation prompt.');
      return;
    }
    if (trimmed.length < 5) {
      setValidationError('Prompt must be at least 5 characters.');
      return;
    }
    if (trimmed.length > 1200) {
      setValidationError('Prompt exceeds maximum 1200 character limit.');
      return;
    }

    setValidationError(null);
    setLoadedSavedDemo(null);
    setIsSubmitting(true);
    setNetworkError(false);
    setErrorCode(null);
    setErrorMessage(null);
    setCurrentStatus('QUEUED');
    setEvents([]);
    setQaReport(null);
    setSpec(null);
    setLimitations([]);
    setRepairRationale(null);
    setRepairDiff(null);

    try {
      const res = await createGame(trimmed);
      setActiveGameId(res.game_id);
      setCurrentStatus(res.status || 'QUEUED');
      // Trigger initial poll immediately, then schedule periodic poll
      handlePoll(res.game_id);
      startPolling(res.game_id);
    } catch (err) {
      setIsSubmitting(false);
      setNetworkError(true);
      setErrorMessage(err instanceof Error ? err.message : 'Network error: Failed to initiate game creation.');
    }
  };

  const handleRetry = () => {
    setNetworkError(false);
    if (activeGameId) {
      handlePoll(activeGameId);
      startPolling(activeGameId);
    } else {
      handleCreate();
    }
  };

  const handleSelectChip = (chipPrompt: string) => {
    setLoadedSavedDemo(null);
    setPrompt(chipPrompt);
    setValidationError(null);
  };

  const handleLoadSavedDemo = (demo: SavedDemo) => {
    stopPolling();
    setLoadedSavedDemo(demo);
    setActiveGameId(demo.id);
    setPrompt(demo.prompt);
    setValidationError(null);
    setNetworkError(false);
    setIsSubmitting(false);
    setErrorCode(null);
    setErrorMessage(null);
    setCurrentStatus('READY');
    setSpec(demo.spec);
    setQaReport(demo.qa);
    setEvents(demo.events);
    setLimitations(demo.limitations || []);
    setRepairRationale(demo.repair_rationale || null);
    setRepairDiff(demo.repair_diff || null);
  };

  // Determine stage status for timeline rendering
  const getStageState = (_stageName: GameStatus, stageIndex: number) => {
    if (!currentStatus) return 'pending';

    if (currentStatus === 'FAILED') {
      return stageIndex === timelineStages.length - 1 ? 'failed' : 'completed';
    }

    // Find current index in timelineStages
    let currentIndex = timelineStages.indexOf(currentStatus);
    if (hasRepairOccurred && currentStatus === 'TESTING' && repairRationale) {
      // If repaired, this is the second testing stage (index 8)
      currentIndex = 8;
    } else if (hasRepairOccurred && currentStatus === 'BUILDING' && repairRationale) {
      currentIndex = 7;
    } else if (hasRepairOccurred && currentStatus === 'VALIDATING_SPEC' && repairRationale) {
      currentIndex = 6;
    }

    if (currentStatus === 'READY' || currentStatus === 'READY_WITH_WARNINGS') {
      return 'completed';
    }

    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'current';
    return 'pending';
  };

  return (
    <div className="max-w-[1600px] mx-auto px-6 pb-12 flex flex-col gap-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Sparkles className="text-primary w-6 h-6 animate-pulse" />
            <h1 className="syne text-3xl font-black tracking-widest text-white">THE FORGE</h1>
          </div>
          <p className="mono text-xs text-white/50 tracking-wider mt-1">
            Autonomous Engine for Text-to-Heuristic Environmental Rendering
          </p>
        </div>

        {activeGameId && (
          <div className="mono text-xs bg-white/5 border border-white/10 px-4 py-2 rounded-xl text-white/60">
            Active Job ID: <span className="text-primary font-bold">{activeGameId}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Prompt Configuration */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <GlassPanel className="p-6 flex flex-col gap-6 border-white/10">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <span className="mono text-xs text-white/60 uppercase tracking-widest font-bold">
                Natural Language Intent
              </span>
              <span className={`mono text-xs ${prompt.length > 1150 ? 'text-amber-400 font-bold' : 'text-white/40'}`}>
                {prompt.length} / 1200
              </span>
            </div>

            {/* Prompt Textarea */}
            <div className="flex flex-col gap-2">
              <textarea
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  if (validationError) setValidationError(null);
                }}
                placeholder="Describe your game manifestation (e.g. 'Spooky wizard collecting crystals while ghosts chase the player in a haunted arena')..."
                className="w-full h-44 bg-black/50 border border-white/10 rounded-xl p-4 text-white placeholder-white/30 focus:outline-none focus:border-primary focus:bg-black/80 transition-all resize-none text-sm leading-relaxed"
                maxLength={1200}
                disabled={isSubmitting && !isTerminal}
              />

              {validationError && (
                <div className="flex items-center gap-2 text-rose-400 text-xs mono bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-lg">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{validationError}</span>
                </div>
              )}
            </div>

            {/* Load saved demo row labeled "Saved result (offline demo)" */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="mono text-[11px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  Load saved demo
                </label>
                <span className="mono text-[10px] text-emerald-300 font-bold px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30">
                  Saved result (offline demo)
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {SAVED_DEMOS.map((demo) => {
                  const isSelected = activeGameId === demo.id;
                  return (
                    <button
                      key={demo.id}
                      type="button"
                      onClick={() => handleLoadSavedDemo(demo)}
                      className={`text-left p-3 rounded-xl border transition-all flex flex-col gap-1.5 group cursor-pointer ${
                        isSelected
                          ? 'bg-emerald-500/20 border-emerald-400 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)] ring-1 ring-emerald-400/50'
                          : 'bg-white/[0.03] hover:bg-white/[0.07] border-white/10 hover:border-emerald-500/40 text-white/80 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-bold text-xs group-hover:text-emerald-300 truncate">
                          {demo.title}
                        </span>
                        {demo.is_repaired && (
                          <span className="mono text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shrink-0">
                            Repaired
                          </span>
                        )}
                      </div>
                      <span className="mono text-[10px] text-emerald-400 font-semibold truncate">
                        {demo.model_label}
                      </span>
                      <span className="mono text-[9px] text-white/40">
                        Offline demo • 0 API calls
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Example Prompt Chips */}
            <div className="flex flex-col gap-2">
              <label className="mono text-[11px] text-white/50 uppercase tracking-wider">
                Preset Archetypes & Test Scenarios
              </label>
              <div className="grid grid-cols-2 gap-2">
                {EXAMPLE_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    onClick={() => handleSelectChip(chip.prompt)}
                    disabled={isSubmitting && !isTerminal}
                    className="text-left px-3 py-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 hover:border-primary/40 text-xs mono text-white/80 hover:text-white transition-all flex flex-col gap-0.5 group disabled:opacity-50 cursor-pointer"
                  >
                    <span className="font-bold text-primary group-hover:text-primary/90 flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3" />
                      {chip.label}
                    </span>
                    <span className="text-[10px] text-white/40 truncate w-full">
                      {chip.prompt}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleCreate}
              disabled={(isSubmitting && !isTerminal) || !prompt.trim()}
              className="w-full bg-primary hover:bg-primary/80 disabled:bg-white/10 disabled:text-white/30 text-white font-bold py-4 rounded-xl tracking-widest uppercase text-sm transition-all flex items-center justify-center gap-2 group cursor-pointer shadow-[0_0_20px_rgba(99,102,241,0.3)] disabled:shadow-none"
            >
              {isSubmitting && !isTerminal ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Synthesizing World...</span>
                </>
              ) : (
                <>
                  <span>Construct World</span>
                  <Send className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </GlassPanel>

          {/* Network Failure Banner with Retry Button */}
          {networkError && (
            <div className="glass-panel p-4 rounded-2xl border-rose-500/30 bg-rose-500/10 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
                <div>
                  <h4 className="font-bold text-rose-300 text-xs mono uppercase">Network Disconnection</h4>
                  <p className="text-[11px] text-white/60">
                    Failed to communicate with the game generation service.
                  </p>
                </div>
              </div>
              <button
                onClick={handleRetry}
                className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 rounded-lg text-xs mono font-bold text-rose-200 uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </button>
            </div>
          )}

          {/* Friendly Error Message if job failed */}
          {currentStatus === 'FAILED' && (
            <div className="glass-panel p-4 rounded-2xl border-rose-500/30 bg-rose-500/10 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-rose-400 font-bold mono text-xs uppercase">
                <XCircle className="w-4 h-4" />
                Synthesis Failed {errorCode ? `[${errorCode}]` : ''}
              </div>
              <p className="text-xs text-white/80">
                {getFriendlyErrorMessage(errorCode, errorMessage)}
              </p>
              <button
                onClick={handleCreate}
                className="mt-2 self-start px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-xs mono uppercase tracking-wider text-white transition-all cursor-pointer"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Timeline & Terminal & Trace Drawer */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Main Status / Timeline Card */}
          <GlassPanel className="p-6 flex flex-col gap-6 border-white/10">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <Activity className="text-primary w-5 h-5" />
                <h3 className="syne text-lg font-bold tracking-wider text-white">
                  LIFECYCLE PIPELINE
                </h3>
              </div>

              {currentStatus ? (
                <div className="flex items-center gap-2">
                  <span className="mono text-[11px] text-white/40 uppercase">Status:</span>
                  <span
                    className={`mono text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider ${
                      currentStatus === 'READY'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.3)]'
                        : currentStatus === 'READY_WITH_WARNINGS'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : currentStatus === 'FAILED'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : currentStatus === 'REPAIRING'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse'
                        : 'bg-primary/20 text-primary border border-primary/40'
                    }`}
                  >
                    {STAGE_LABELS[currentStatus] || currentStatus}
                  </span>
                </div>
              ) : (
                <span className="mono text-xs text-white/30">IDLE - AWAITING SUBMISSION</span>
              )}
            </div>

            {/* Saved result banner */}
            {loadedSavedDemo && (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 mono text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    Offline Demo: <strong>{loadedSavedDemo.title}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-white/60">Model: {loadedSavedDemo.model_label}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    Saved result (offline demo)
                  </span>
                </div>
              </div>
            )}

            {/* Stages Timeline */}
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {timelineStages.map((stage, idx) => {
                  const state = getStageState(stage, idx);
                  return (
                    <div
                      key={`${stage}-${idx}`}
                      className={`p-3 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition-all ${
                        state === 'completed'
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.15)]'
                          : state === 'current'
                          ? 'bg-primary/20 border-primary text-white shadow-[0_0_15px_rgba(99,102,241,0.4)] scale-105'
                          : state === 'failed'
                          ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                          : 'bg-white/[0.02] border-white/5 text-white/30'
                      }`}
                    >
                      <div className="w-6 h-6 flex items-center justify-center">
                        {state === 'completed' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                        {state === 'current' && <Loader2 className="w-5 h-5 text-primary animate-spin" />}
                        {state === 'failed' && <XCircle className="w-5 h-5 text-rose-400" />}
                        {state === 'pending' && (
                          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
                        )}
                      </div>
                      <span className="mono text-[10px] font-bold uppercase tracking-wider">
                        {STAGE_LABELS[stage] || stage}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* In-flight stage indicator */}
              {isSubmitting && !isTerminal && currentStatus && (
                <div className="flex items-center gap-2 pt-2 text-xs mono text-white/60">
                  <span className="w-2 h-2 rounded-full bg-primary animate-ping" />
                  <span>Processing stage: <strong className="text-white">{STAGE_LABELS[currentStatus] || currentStatus}</strong>...</span>
                </div>
              )}
            </div>

            {/* Terminal Actions: Play Game Launch & QA Summary */}
            {(currentStatus === 'READY' || currentStatus === 'READY_WITH_WARNINGS') && activeGameId && (
              <div className="pt-4 border-t border-white/10 flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-primary/10 border border-primary/30">
                  <div>
                    <h4 className="syne font-bold text-white text-base">Manifestation Complete</h4>
                    <p className="mono text-xs text-white/60">
                      Simulation compiled, validated, and verified with Playwright QA.
                    </p>
                  </div>

                  <Link
                    to={`/play/${activeGameId}`}
                    className="btn-play inline-flex items-center gap-2 whitespace-nowrap"
                  >
                    <Gamepad2 className="w-5 h-5" />
                    PLAY SIMULATION
                  </Link>
                </div>

                {/* QA Summary Banner */}
                {qaReport && (
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span className="mono text-xs font-bold text-white uppercase tracking-wider">
                          QA Summary Report
                        </span>
                      </div>
                      <span
                        className={`mono text-[10px] font-bold px-2 py-0.5 rounded ${
                          qaReport.overall === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}
                      >
                        {qaReport.overall}
                      </span>
                    </div>
                    <div className="mono text-xs text-white/60 flex items-center gap-4">
                      <span>
                        Critical Checks Passed:{' '}
                        <strong className="text-emerald-400">
                          {qaReport.checks.filter((c) => c.passed).length} / {qaReport.checks.length}
                        </strong>
                      </span>
                      {qaReport.page_errors && qaReport.page_errors.length === 0 && (
                        <span className="text-white/40">Zero Runtime Errors</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </GlassPanel>

          {/* Self-Repair Rationale Callout (if repair occurred) */}
          {hasRepairOccurred && repairRationale && (
            <GlassPanel className="p-5 border-cyan-500/30 bg-cyan-500/5 rounded-2xl flex flex-col gap-3">
              <div className="flex items-center gap-2 text-cyan-300 font-bold mono text-xs uppercase tracking-wider">
                <Wrench className="w-4 h-4" />
                Autonomous Self-Repair Sequence Executed
              </div>
              <p className="text-xs text-white/80 leading-relaxed mono">
                {repairRationale}
              </p>
            </GlassPanel>
          )}

          {/* Limitations Callout ("What We Adapted") from the planner */}
          {limitations.length > 0 && (
            <GlassPanel className="p-5 border-amber-500/30 bg-amber-500/5 rounded-2xl flex flex-col gap-3">
              <div className="flex items-center gap-2 text-amber-400 font-bold mono text-xs uppercase tracking-wider">
                <Sparkles className="w-4 h-4" />
                What We Adapted (Planner Constraints & Scope)
              </div>
              <ul className="list-disc list-inside text-xs mono text-amber-200/80 space-y-1">
                {limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </GlassPanel>
          )}

          {/* Technical Trace Drawer */}
          {(events.length > 0 || spec || qaReport || limitations.length > 0) && (
            <GlassPanel className="p-0 overflow-hidden border-white/10 flex flex-col">
              {/* Drawer Toggle Header */}
              <button
                type="button"
                onClick={() => setDrawerOpen((prev) => !prev)}
                className="w-full px-6 py-4 bg-white/[0.03] hover:bg-white/[0.06] border-b border-white/10 flex items-center justify-between text-left transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <Terminal className="w-4 h-4 text-primary" />
                  <span className="mono text-xs font-bold uppercase tracking-widest text-white">
                    Technical Trace Drawer
                  </span>
                  <span className="text-[10px] mono text-white/40 border border-white/10 px-2 py-0.5 rounded">
                    {events.length} Events Logged
                  </span>
                </div>
                {drawerOpen ? (
                  <ChevronUp className="w-4 h-4 text-white/50" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-white/50" />
                )}
              </button>

              {drawerOpen && (
                <div className="p-6 flex flex-col gap-4">
                  {/* Tab Navigation */}
                  <div className="flex items-center gap-2 border-b border-white/10 pb-3 overflow-x-auto">
                    <button
                      type="button"
                      onClick={() => setActiveTab('summary')}
                      className={`px-3 py-1.5 rounded-lg text-xs mono uppercase tracking-wider transition-all cursor-pointer ${
                        activeTab === 'summary'
                          ? 'bg-primary text-white font-bold'
                          : 'text-white/50 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      GameIR Summary
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab('events')}
                      className={`px-3 py-1.5 rounded-lg text-xs mono uppercase tracking-wider transition-all cursor-pointer ${
                        activeTab === 'events'
                          ? 'bg-primary text-white font-bold'
                          : 'text-white/50 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      Events ({events.length})
                    </button>
                    {hasRepairOccurred && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('repair')}
                        className={`px-3 py-1.5 rounded-lg text-xs mono uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 ${
                          activeTab === 'repair'
                            ? 'bg-cyan-600 text-white font-bold'
                            : 'text-cyan-300 hover:text-white hover:bg-cyan-500/10'
                        }`}
                      >
                        <Wrench className="w-3 h-3" />
                        Repair Diff
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setActiveTab('qa')}
                      className={`px-3 py-1.5 rounded-lg text-xs mono uppercase tracking-wider transition-all cursor-pointer ${
                        activeTab === 'qa'
                          ? 'bg-primary text-white font-bold'
                          : 'text-white/50 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      QA Report
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab('spec')}
                      className={`px-3 py-1.5 rounded-lg text-xs mono uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1 ${
                        activeTab === 'spec'
                          ? 'bg-primary text-white font-bold'
                          : 'text-white/50 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      <FileCode className="w-3 h-3" />
                      Raw JSON
                    </button>
                  </div>

                  {/* Tab: GameIR Summary */}
                  {activeTab === 'summary' && (
                    <div className="flex flex-col gap-4">
                      {spec ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Title</span>
                            <span className="text-xs mono font-bold text-white">{spec.title}</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Genre</span>
                            <span className="text-xs mono font-bold text-primary">{spec.genre}</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Theme</span>
                            <span className="text-xs mono font-bold text-white">{spec.theme}</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Move Speed</span>
                            <span className="text-xs mono font-bold text-white">{spec.player.move_speed} px/s</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Attack Mode</span>
                            <span className="text-xs mono font-bold text-emerald-300">{spec.player.attack_mode}</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Objective</span>
                            <span className="text-xs mono font-bold text-amber-300">
                              {spec.objective.type}: {spec.objective.target}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Enemy Count</span>
                            <span className="text-xs mono font-bold text-white">
                              {spec.enemies.reduce((acc, e) => acc + e.count, 0)}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Difficulty</span>
                            <span className="text-xs mono font-bold text-white">{spec.difficulty} / 5</span>
                          </div>
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                            <span className="text-[10px] mono text-white/40 uppercase block">Controls</span>
                            <span className="text-[11px] mono text-white/80">{spec.controls.movement}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="mono text-xs text-white/40">GameIR specification pending compilation...</span>
                      )}
                    </div>
                  )}

                  {/* Tab: Lifecycle Events */}
                  {activeTab === 'events' && (
                    <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-2">
                      {events.map((evt, idx) => (
                        <div
                          key={`${evt.timestamp}-${idx}`}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex flex-col gap-1 text-xs mono"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-primary font-bold">{evt.stage}</span>
                            <span className="text-[10px] text-white/40">
                              {new Date(evt.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-white/70">{evt.detail || evt.message}</p>
                          {(evt.repair_rationale || evt.rationale) && (
                            <div className="mt-1 p-2 rounded bg-cyan-500/10 border border-cyan-500/20 text-[11px] text-cyan-200">
                              <strong>Rationale:</strong> {evt.repair_rationale || evt.rationale}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Tab: Repair Diff */}
                  {activeTab === 'repair' && (
                    <div className="flex flex-col gap-4">
                      {repairRationale && (
                        <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs mono text-cyan-200">
                          <strong className="block text-cyan-100 mb-1">Repair Rationale:</strong>
                          {repairRationale}
                        </div>
                      )}

                      {repairDiff && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1">
                            <span className="mono text-xs font-bold text-rose-400 uppercase">
                              Before (Failing Spec)
                            </span>
                            <pre className="p-3 rounded-xl bg-black/60 border border-rose-500/20 text-[11px] mono text-rose-300/80 overflow-x-auto">
                              {JSON.stringify(repairDiff.before, null, 2)}
                            </pre>
                          </div>
                          <div className="flex flex-col gap-1">
                            <span className="mono text-xs font-bold text-emerald-400 uppercase">
                              After (Patched Spec)
                            </span>
                            <pre className="p-3 rounded-xl bg-black/60 border border-emerald-500/20 text-[11px] mono text-emerald-300/80 overflow-x-auto">
                              {JSON.stringify(repairDiff.after, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Tab: QA Report */}
                  {activeTab === 'qa' && (
                    <div className="flex flex-col gap-3">
                      {qaReport ? (
                        <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-2">
                          {qaReport.checks.map((chk) => (
                            <div
                              key={chk.id}
                              className={`p-2.5 rounded-lg border text-xs mono flex items-center justify-between ${
                                chk.passed
                                  ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300'
                                  : 'bg-rose-500/5 border-rose-500/20 text-rose-300'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                {chk.passed ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                                )}
                                <span className="font-bold">{chk.id}</span>
                              </div>
                              <span className="text-[10px] text-white/50">{chk.message || 'Check passed'}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="mono text-xs text-white/40">QA testing has not run yet.</span>
                      )}
                    </div>
                  )}

                  {/* Tab: Raw JSON */}
                  {activeTab === 'spec' && (
                    <div className="flex flex-col gap-2">
                      <pre className="p-4 rounded-xl bg-black/80 border border-white/10 text-[11px] mono text-white/80 max-h-72 overflow-auto">
                        {JSON.stringify(spec, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </GlassPanel>
          )}
        </div>
      </div>
    </div>
  );
};
