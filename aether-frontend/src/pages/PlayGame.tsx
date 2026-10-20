import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { GameCanvas } from '../components/GameCanvas';
import type { GameIR } from '../game/gameir';
import sampleGameIR from '../game/sample-gameir.json';
import sampleSurviveIR from '../game/sample-survive.json';
import sampleMeleeIR from '../game/sample-melee.json';
import sampleAvoidIR from '../game/sample-avoid.json';
import sampleTooHardIR from '../game/sample-too-hard.json';
import sampleBouncerPillarsIR from '../game/sample-bouncer-pillars.json';
import samplePatrolLanesIR from '../game/sample-patrol-lanes.json';
import sampleDasherDefeatIR from '../game/sample-dasher-defeat.json';
import sampleShooterPillarsIR from '../game/sample-shooter-pillars.json';
import sampleMazeCollectIR from '../game/sample-maze-collect.json';
import { getSavedDemo } from '../game/savedDemos';
import { getSpec } from '../lib/apiClient';
import { Sparkles, ArrowLeft, Gamepad2, AlertTriangle, Loader2 } from 'lucide-react';

export const PlayGame: React.FC = () => {
  const { game_id } = useParams<{ game_id: string }>();

  const [dynamicSpec, setDynamicSpec] = useState<GameIR | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check saved offline demos
  const savedDemo = game_id ? getSavedDemo(game_id) : undefined;

  const isThemeRoute = Boolean(game_id?.startsWith('theme-'));

  // Check demo routes
  const isDemo =
    Boolean(savedDemo) ||
    isThemeRoute ||
    game_id === 'demo' ||
    game_id === 'demo-survive' ||
    game_id === 'demo-melee' ||
    game_id === 'demo-avoid' ||
    game_id === 'demo-too-hard' ||
    game_id === 'demo-bouncer-pillars' ||
    game_id === 'demo-patrol-lanes' ||
    game_id === 'demo-dasher-defeat' ||
    game_id === 'demo-shooter-pillars' ||
    game_id === 'demo-maze-collect' ||
    game_id === 'test-slow-100' ||
    game_id === 'test-p06';

  let staticSpec: GameIR | null = null;
  if (isThemeRoute) {
    const rawTheme = game_id!.replace('theme-', '').replace('-', '_');
    const themeMeta: Record<string, { title: string; premise: string }> = {
      fantasy: { title: 'Arcane Crystal Grove', premise: 'A mystical mage gathering glowing mana crystals while goblins pursue.' },
      sci_fi: { title: 'Cyber Void Surge', premise: 'A cybernetic drone harvesting power cells while rogue security drones pursue.' },
      pirate: { title: 'Treasure Cove Hunt', premise: 'A pirate captain gathering gold doubloons while skeleton ships pursue.' },
      spooky: { title: 'Spooky Crypt Haunt', premise: 'A spooky wizard collecting glowing crystals while phantom ghosts pursue.' },
      cozy: { title: 'Enchanted Meadow Gathering', premise: 'A woodland spirit gathering fallen stars in a peaceful twilight grove.' },
    };
    const meta = themeMeta[rawTheme] || { title: `${rawTheme.toUpperCase()} ARENA`, premise: `Survive in a ${rawTheme} arena.` };
    staticSpec = {
      ...(sampleGameIR as GameIR),
      theme: rawTheme,
      title: meta.title,
      premise: meta.premise,
    };
  } else if (savedDemo) {
    staticSpec = savedDemo.spec;
  } else if (game_id === 'demo') {
    staticSpec = sampleGameIR as GameIR;
  } else if (game_id === 'demo-survive') {
    staticSpec = sampleSurviveIR as GameIR;
  } else if (game_id === 'demo-melee') {
    staticSpec = sampleMeleeIR as GameIR;
  } else if (game_id === 'demo-avoid') {
    staticSpec = sampleAvoidIR as GameIR;
  } else if (game_id === 'demo-bouncer-pillars') {
    staticSpec = sampleBouncerPillarsIR as GameIR;
  } else if (game_id === 'demo-patrol-lanes') {
    staticSpec = samplePatrolLanesIR as GameIR;
  } else if (game_id === 'demo-dasher-defeat') {
    staticSpec = sampleDasherDefeatIR as GameIR;
  } else if (game_id === 'demo-shooter-pillars') {
    staticSpec = sampleShooterPillarsIR as GameIR;
  } else if (game_id === 'demo-maze-collect') {
    staticSpec = sampleMazeCollectIR as GameIR;
  } else if (game_id === 'demo-too-hard') {
    // Deliberately unplayable fixture: must FAIL the spec-level QA checks (repair loop input)
    staticSpec = sampleTooHardIR as GameIR;
  } else if (game_id === 'test-slow-100') {
    staticSpec = {
      ...(sampleGameIR as GameIR),
      player: {
        ...(sampleGameIR as GameIR).player,
        move_speed: 100.0,
      },
    };
  } else if (game_id === 'test-p06') {
    staticSpec = {
      schema_version: '1.0',
      title: 'Shadow Escape',
      genre: 'arena_survival',
      premise: 'Survive the relentless onslaught of fast-moving shadows in a high-stakes arena.',
      theme: 'spooky',
      player: { move_speed: 110.0, max_health: 2, attack_mode: 'avoid_only' },
      enemies: [{ type: 'chaser', count: 15, speed: 220.0 }],
      collectibles: [],
      objective: { type: 'survive_seconds', target: 30 },
      difficulty: 5,
      controls: { movement: 'WASD or arrow keys', attack: null },
      seed: 1337,
    };
  }

  useEffect(() => {
    if (isDemo || !game_id) {
      return;
    }

    let isMounted = true;
    const timer = setTimeout(() => {
      setLoading(true);
      setError(null);
      setDynamicSpec(null);
    }, 0);

    getSpec(game_id)
      .then((spec) => {
        if (!isMounted) return;
        // Basic validity check to ensure it doesn't crash on invalid spec
        if (
          !spec ||
          typeof spec !== 'object' ||
          !spec.player ||
          !spec.controls ||
          !spec.objective ||
          typeof spec.player.move_speed !== 'number'
        ) {
          setError('Invalid GameIR specification structure: required game fields are missing.');
          setLoading(false);
          return;
        }
        setDynamicSpec(spec);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Failed to load game specification.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [game_id, isDemo]);

  const gameIR = isDemo ? staticSpec : dynamicSpec;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-24 text-center flex flex-col items-center justify-center">
        <div className="glass-panel p-8 rounded-2xl border-white/10 flex flex-col items-center gap-4 max-w-md w-full">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
          <h2 className="syne text-xl font-bold tracking-widest text-white">SYNTHESIZING ARENA</h2>
          <p className="mono text-xs text-white/50">
            Loading specification for ID: <span className="text-primary font-bold">{game_id}</span>
          </p>
        </div>
      </div>
    );
  }

  if (error || (!isDemo && !gameIR)) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center flex flex-col items-center">
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 flex flex-col items-center gap-4 max-w-lg w-full mb-8">
          <AlertTriangle className="w-10 h-10 text-rose-400" />
          <h2 className="syne text-2xl font-bold text-white">Simulation Error</h2>
          <p className="mono text-xs text-white/70 max-w-md">
            {error || `Unable to load simulation specification for ID "${game_id}".`}
          </p>
          <div className="flex gap-4 mt-2">
            <Link
              to="/forge"
              className="px-4 py-2 bg-primary/20 hover:bg-primary/40 border border-primary/40 rounded-lg text-xs mono text-white uppercase tracking-wider transition-all"
            >
              Return to Forge
            </Link>
            <Link
              to="/nexus"
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs mono text-white/70 hover:text-white uppercase tracking-wider transition-all"
            >
              Back to Nexus
            </Link>
          </div>
        </div>

        <div className="flex flex-col items-center gap-3">
          <span className="mono text-xs text-white/40 uppercase tracking-widest">Available Demo Simulators</span>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link to="/play/demo" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Projectile Demo
            </Link>
            <Link to="/play/demo-melee" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Melee Demo
            </Link>
            <Link to="/play/demo-avoid" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Avoid Only Demo
            </Link>
            <Link to="/play/demo-survive" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Survival Demo
            </Link>
            <Link to="/play/demo-bouncer-pillars" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Bouncer Pillars
            </Link>
            <Link to="/play/demo-patrol-lanes" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Patrol Lanes
            </Link>
            <Link to="/play/demo-dasher-defeat" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Dasher Defeat
            </Link>
            <Link to="/play/demo-shooter-pillars" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Shooter Pillars
            </Link>
            <Link to="/play/demo-maze-collect" className="btn-play inline-flex items-center gap-2 text-xs">
              <Gamepad2 className="w-4 h-4" />
              Maze Collect
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!gameIR) {
    return null;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 pb-12 flex flex-col items-center gap-6">
      {/* Header Bar */}
      <div className="w-full max-w-[800px] flex items-center justify-between">
        <Link
          to="/nexus"
          className="inline-flex items-center gap-2 text-xs mono text-white/50 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          BACK TO NEXUS
        </Link>
        <div className="flex items-center gap-2">
          {savedDemo && (
            <span className="text-[10px] mono text-emerald-300 bg-emerald-500/10 border border-emerald-500/40 px-2 py-0.5 rounded-sm">
              Saved result (offline demo) • {savedDemo.model_label}
            </span>
          )}
          <span className="badge-primary shadow-[0_0_10px_rgba(99,102,241,0.5)]">
            {gameIR.genre}
          </span>
          <span className="text-[10px] uppercase tracking-widest text-white/40 border border-white/10 px-2 py-0.5 rounded-sm">
            {gameIR.theme}
          </span>
        </div>
      </div>

      {/* Game Title & Premise */}
      <div className="w-full max-w-[800px] flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Sparkles className="text-primary w-5 h-5" />
          <h1 className="syne text-3xl font-extrabold tracking-wide text-white">
            {gameIR.title}
          </h1>
        </div>
        <p className="text-white/60 text-sm mono">{gameIR.premise}</p>
      </div>

      {/* Phaser Game Canvas */}
      <GameCanvas gameIR={gameIR} />

      {/* Controls Info Footer */}
      <div className="w-full max-w-[800px] flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.03] border border-white/10 text-xs mono text-white/50">
        <div className="flex items-center gap-2">
          <span className="text-white/80 font-bold">Movement:</span>
          <span>{gameIR.controls.movement}</span>
        </div>
        <div>
          <span className="text-white/80 font-bold">Speed:</span>{' '}
          <span>{gameIR.player.move_speed}px/s</span>
        </div>
      </div>
    </div>
  );
};
