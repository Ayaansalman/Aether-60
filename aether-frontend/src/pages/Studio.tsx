import { useEffect, useState } from "react";
import { Link, Route, Routes, useParams } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Braces,
  Check,
  ChevronDown,
  Code2,
  Expand,
  Flag,
  Gamepad2,
  Layers3,
  Loader2,
  Play,
  Plus,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import { PlatformerCanvas } from "../components/PlatformerCanvas";
import type { PlatformerIR, StudioJob } from "../game/platformer/types";
import "./studio.css";

const PROMPTS = [
  [
    "01",
    "The Verdant Passage",
    "A magical forest platformer where I collect crystals, avoid monsters, double jump across ruins and reach an ancient shrine.",
    "forest",
  ],
  [
    "02",
    "The Copperworks",
    "An industrial platformer with moving machinery, dangerous obstacles, robot enemies, dash and checkpoints.",
    "industrial",
  ],
  [
    "03",
    "Stairway to the Stars",
    "A challenging precision jumping platformer with moving platforms, double jump and an ascent to the top of a tower.",
    "tower",
  ],
  [
    "04",
    "A Quiet Discovery",
    "A peaceful easy forest platformer with no enemies, no hazards, crystals and checkpoints.",
    "peaceful",
  ],
];

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}
function Brand() {
  return (
    <Link className="brand" to="/">
      <span className="brand-icon">a</span>aether
      <span className="brand-dot">®</span>
    </Link>
  );
}
function Landing() {
  return (
    <div className="landing studio-theme">
      <header className="landing-nav">
        <Brand />
        <nav>
          <a href="#possibilities">What you can make</a>
          <a href="#process">How it works</a>
          <Link className="button primary" to="/studio">
            Open studio <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <section className="hero">
        <div className="eyebrow">
          <span className="status-dot" /> THE SPACE BETWEEN AN IDEA AND A GAME
        </div>
        <h1>
          A little imagination.
          <br />A whole new <em>world.</em>
        </h1>
        <p>
          Turn the game in your head into something you can play.
          <br />
          Describe your idea. Shape its world. Make it yours.
        </p>
        <div className="hero-actions">
          <Link className="button primary large" to="/studio">
            Create your first game <ArrowRight size={18} />
          </Link>
          <a className="text-link" href="#possibilities">
            Explore the possibilities <span>↘</span>
          </a>
        </div>
        <div className="hero-caption">
          <span>BUILT FOR YOUR IMAGINATION</span>
          <span>NO CODE REQUIRED</span>
          <span>2D PLATFORMERS · EARLY ACCESS</span>
        </div>
      </section>
      <section id="possibilities" className="worlds">
        <div className="section-title">
          <div>
            <div className="eyebrow">SMALL IDEAS. PLAYABLE WORLDS.</div>
            <h2>Where will you go first?</h2>
          </div>
          <p>
            One engine. Different journeys.
            <br />
            Start with a direction and see where it takes you.
          </p>
        </div>
        <div className="world-grid">
          {PROMPTS.slice(0, 3).map(([n, title, prompt, key]) => (
            <Link
              to={`/studio?example=${key}`}
              key={key}
              className={`world-card ${key}`}
            >
              <div className="world-art">
                <div className="pixel-sun" />
                <div className="pixel-hill hill-back" />
                <div className="pixel-hill" />
                <div className="pixel-ground" />
                <img
                  className="world-character"
                  src="/assets/platformer/characters.png"
                  alt=""
                />
                <span className="world-tag">
                  {key === "industrial"
                    ? "MACHINERY & MOMENTUM"
                    : key === "tower"
                      ? "A LITTLE MORE CHALLENGE"
                      : "EXPLORATION & DISCOVERY"}
                </span>
              </div>
              <div className="world-info">
                <span>
                  {n} / {key === "tower" ? "PRECISION" : "PLATFORMER"}
                </span>
                <h3>
                  {title}
                  <ArrowUpRight size={20} />
                </h3>
                <p>{prompt.split(" with ")[0].slice(0, 94)}.</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
      <section id="process" className="process">
        <div>
          <div className="eyebrow">FROM “WHAT IF” TO “ONE MORE TRY”</div>
          <h2>
            You bring the idea.
            <br />
            Aether builds the path.
          </h2>
          <p>
            Our first chapter is 2D platformers. Thoughtful level generation,
            real pixel artwork, and a workflow you can look inside.
          </p>
          <Link to="/studio" className="text-link">
            Step into the studio <ArrowRight size={18} />
          </Link>
        </div>
        <ol>
          <li>
            <span>01</span>
            <div>
              <h3>Describe your world</h3>
              <p>
                A forest full of crystals? A factory full of trouble? Tell us
                the setting, the challenge, and the feeling.
              </p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <h3>Watch it come together</h3>
              <p>
                A validated design becomes a seeded level. Inspect the actual
                design, assets, route checks, and browser QA.
              </p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <h3>Press play. Find your way.</h3>
              <p>
                Jump in, explore, and try again. Every game has its own route,
                rules, and reason to keep going.
              </p>
            </div>
          </li>
        </ol>
      </section>
      <footer>
        <Brand />
        <span>A PLACE FOR WORLDS THAT DON'T EXIST. YET.</span>
        <span>Capstone · 2026</span>
      </footer>
    </div>
  );
}

function Workspace() {
  const { id } = useParams();
  const query = new URLSearchParams(location.search).get("example");
  const initial = PROMPTS.find((p) => p[3] === query) || PROMPTS[0];
  const [prompt, setPrompt] = useState(initial[2]);
  const [mode, setMode] = useState(
    new URLSearchParams(location.search).get("mode") === "fixture"
      ? "fixture"
      : "live",
  );
  const [spec, setSpec] = useState<PlatformerIR | null>(null);
  const [job, setJob] = useState<StudioJob | null>(null);
  const [activeId, setActiveId] = useState(id || "");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [inspector, setInspector] = useState(false),
    [artifact, setArtifact] = useState("game_design.json");
  const [restart, setRestart] = useState(0),
    [preview, setPreview] = useState(!id);
  const [tab, setTab] = useState("game");
  const [expanded, setExpanded] = useState(false);
  const [recent, setRecent] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("aether-v2-jobs") || "[]");
    } catch {
      return [];
    }
  });
  useEffect(() => {
    const timer = setTimeout(
      () => window.dispatchEvent(new Event("resize")),
      0,
    );
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", close);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("keydown", close);
    };
  }, [expanded]);
  useEffect(() => {
    if (id) return;
    let current = true;
    request<PlatformerIR>(`/fixtures/${initial[3]}.json`)
      .then((s) => {
        if (current) setSpec(s);
      })
      .catch(() => {
        if (current)
          setError(
            "Example could not be loaded. Start the backend and generate a game.",
          );
      });
    return () => {
      current = false;
    };
  }, [id, initial]);
  useEffect(() => {
    if (!activeId) return;
    let current = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const data = await request<StudioJob>(`/api/v2/games/${activeId}`);
        if (!current) return;
        setJob(data);
        setPrompt(data.job.prompt);
        const ir = data.artifacts["game_ir_v2.json"] as
          | PlatformerIR
          | undefined;
        if (ir) {
          setSpec((old) =>
            JSON.stringify(old) === JSON.stringify(ir) ? old : ir,
          );
          setPreview(false);
        }
        const done = ["READY", "READY_WITH_WARNINGS", "FAILED"].includes(
          data.job.status,
        );
        setBusy(!done);
        if (data.job.status === "FAILED")
          setError(
            data.events.at(-1)?.detail ||
              "Generation failed. Inspect the recorded events.",
          );
        if (!done) timer = setTimeout(poll, 1000);
      } catch (e) {
        if (current) {
          setError(
            `Backend connection: ${e instanceof Error ? e.message : String(e)}`,
          );
          setBusy(false);
        }
      }
    }
    poll();
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [activeId]);
  async function generate() {
    if (busy || prompt.trim().length < 10) return;
    setBusy(true);
    setError("");
    setJob(null);
    try {
      const result = await request<{ game_id: string }>("/api/v2/games", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, mode }),
      });
      setActiveId(result.game_id);
      const history = [result.game_id, ...recent].slice(0, 12);
      setRecent(history);
      localStorage.setItem("aether-v2-jobs", JSON.stringify(history));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }
  function example(p: string[]) {
    setPrompt(p[2]);
    setActiveId("");
    setJob(null);
    setPreview(true);
    setError("");
    request<PlatformerIR>(`/fixtures/${p[3]}.json`)
      .then(setSpec)
      .catch((e) => setError(String(e)));
  }
  const status = job?.job.status;
  return (
    <div className="workspace studio-theme">
      <header className="studio-header">
        <Brand />
        <div className="project-name">
          Personal workspace <span>/</span>{" "}
          <strong>{spec?.title || "Untitled world"}</strong>
          <ChevronDown size={13} />
        </div>
        <Link className="header-home" to="/">
          About Aether <ArrowUpRight size={14} />
        </Link>
        <span className="avatar">A</span>
      </header>
      <div className="workspace-body">
        <aside className="creator-panel">
          <div className="panel-heading">
            <span>
              <Sparkles size={15} /> Create a world
            </span>
            <button
              aria-label="Clear prompt"
              className="icon-button"
              onClick={() => {
                if (!busy) setPrompt("");
              }}
              disabled={busy}
            >
              <Plus size={17} />
            </button>
          </div>
          <div className="creator-content">
            <div className="eyebrow">YOUR NEXT ADVENTURE STARTS HERE</div>
            <h1>
              What are we
              <br />
              making today?
            </h1>
            <p className="muted">
              A setting, a challenge, a spark of an idea.
              <br />
              Tell Aether what you'd love to play.
            </p>
            <label htmlFor="game-prompt">Your game idea</label>
            <textarea
              id="game-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={3000}
              disabled={busy}
            />
            <div className="prompt-meta">
              <span>2D platformer</span>
              <span>{prompt.length}/3000</span>
            </div>
            <label htmlFor="provider-mode" className="mode-label">
              Generation source
            </label>
            <select
              id="provider-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              disabled={busy}
            >
              <option value="live">Gemini · live generation</option>
              <option value="fixture">Offline fixture · deterministic</option>
            </select>
            <button
              className="button primary generate-button"
              onClick={generate}
              disabled={busy || prompt.trim().length < 10}
            >
              {busy ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Sparkles size={16} />
              )}{" "}
              {busy ? "Building your world…" : "Generate game"}{" "}
              {!busy && <ArrowRight size={16} />}
            </button>
            <p className="source-note">
              {mode === "live"
                ? "A real model designs the game. Levels are constructed and checked by deterministic services."
                : "Offline fixtures use keyword rules and a seed. No language model is called."}
            </p>
            {error && (
              <div className="error-message" role="alert">
                {error}
              </div>
            )}
            <div className="starter-heading">
              A LITTLE INSPIRATION <span>↙</span>
            </div>
            <div className="starter-list">
              {PROMPTS.map((p) => (
                <button key={p[0]} onClick={() => example(p)} disabled={busy}>
                  <span className={`theme-dot ${p[3]}`} />
                  <span>{p[1]}</span>
                  <ArrowUpRight size={14} />
                </button>
              ))}
            </div>
            <details className="capabilities">
              <summary>What can Aether build?</summary>
              <p>
                Forest, industrial and twilight platformers. Crystals, patrol
                enemies, spikes, checkpoints, moving platforms, double jump and
                dash. Other genres and custom mechanics are not available yet;
                requested unsupported features appear in the Inspector.
              </p>
            </details>
            {recent.length > 0 && (
              <details className="capabilities">
                <summary>Recent generations ({recent.length})</summary>
                {recent.map((gid) => (
                  <a
                    className="recent-link"
                    href={`/studio/play/${gid}`}
                    key={gid}
                  >
                    {gid.slice(0, 8)} <ArrowUpRight size={12} />
                  </a>
                ))}
              </details>
            )}
          </div>
          <div className="panel-bottom">
            <span className="status-dot" /> PLATFORMER ENGINE v2{" "}
            <span>EARLY ACCESS</span>
          </div>
        </aside>
        <main className="canvas-panel">
          <div className="canvas-toolbar">
            <div className="preview-tabs">
              <button
                className={tab === "game" ? "active" : ""}
                onClick={() => setTab("game")}
              >
                <Play size={14} /> Game preview
              </button>
              <button
                className={tab === "design" ? "active" : ""}
                onClick={() => setTab("design")}
              >
                <Layers3 size={15} /> Design
              </button>
            </div>
            <div className="toolbar-actions">
              <button
                className="icon-button"
                aria-label="Restart game"
                onClick={() => setRestart((v) => v + 1)}
                disabled={!spec}
              >
                <RotateCcw size={16} />
              </button>
              <button
                className="icon-button"
                aria-label="Expand game"
                onClick={() => {
                  setTab("game");
                  setExpanded(true);
                }}
                disabled={!spec}
              >
                <Expand size={16} />
              </button>
              <button
                className={`inspector-button ${inspector ? "selected" : ""}`}
                onClick={() => setInspector((v) => !v)}
              >
                <Code2 size={15} /> Inspector
              </button>
            </div>
          </div>
          <div className="canvas-area">
            <div className="game-heading">
              <div>
                <div className="eyebrow">
                  {preview
                    ? "EXPLORE A STARTING POINT"
                    : "YOUR GENERATED WORLD"}
                </div>
                <h2>{spec?.title || "A world is taking shape"}</h2>
              </div>
              <span className="game-badge">
                <span className="status-dot" />
                {preview
                  ? "Offline example"
                  : status?.replaceAll("_", " ").toLowerCase() || "Preparing"}
              </span>
            </div>
            {tab === "game" ? (
              <>
                <div
                  className={`preview-frame ${expanded ? "expanded-preview" : ""}`}
                  role={expanded ? "dialog" : undefined}
                  aria-modal={expanded || undefined}
                  aria-label={expanded ? "Expanded game preview" : undefined}
                >
                  {expanded && (
                    <button
                      className="exit-expanded"
                      onClick={() => setExpanded(false)}
                      aria-label="Exit expanded game"
                    >
                      <X size={18} /> Back to studio <kbd>ESC</kbd>
                    </button>
                  )}
                  {spec ? (
                    <PlatformerCanvas spec={spec} restart={restart} />
                  ) : (
                    <div className="empty-preview">
                      <Gamepad2 size={40} />
                      <p>Your next world belongs here.</p>
                    </div>
                  )}
                  <div className="preview-frame-footer">
                    <span>
                      <span className="status-dot" />
                      {preview
                        ? "SEEDED FIXTURE · NOT AI GENERATED"
                        : job?.job.model_id || "WAITING FOR DESIGN"}
                    </span>
                    <span>
                      {spec?.theme?.toUpperCase()}{" "}
                      <span className="footer-divider">/</span> 960 × 540
                    </span>
                  </div>
                </div>
                <div className="game-controls">
                  <div>
                    <kbd>←</kbd>
                    <kbd>→</kbd>
                    <span>Move</span>
                  </div>
                  <div>
                    <kbd>SPACE</kbd>
                    <span>
                      Jump
                      {spec?.player.abilities.includes("double_jump")
                        ? " / double jump"
                        : ""}
                    </span>
                  </div>
                  {spec?.player.abilities.includes("dash") && (
                    <div>
                      <kbd>SHIFT</kbd>
                      <span>Dash</span>
                    </div>
                  )}
                  <div>
                    <kbd>R</kbd>
                    <span>Restart</span>
                  </div>
                  <span className="focus-hint">Click game to focus</span>
                </div>
              </>
            ) : (
              <div className="design-view">
                <h3>World blueprint</h3>
                {spec ? (
                  <>
                    <p>
                      {spec.platforms.filter((p) => !p.moving).length} connected
                      terrain sections · Seed {spec.seed}
                    </p>
                    <div className="level-map">
                      {spec.platforms.map((p, i) => (
                        <div
                          key={i}
                          title={`${p.kind}: x ${p.x}, y ${p.y}, width ${p.width}`}
                          style={{
                            left: `${((p.x * 36) / spec.width) * 100}%`,
                            bottom: `${(1 - (p.y * 36) / spec.height) * 100}%`,
                            width: `${((p.width * 36) / spec.width) * 100}%`,
                          }}
                          className={p.moving ? "moving" : ""}
                        />
                      ))}
                    </div>
                    <dl>
                      <dt>Abilities</dt>
                      <dd>
                        {spec.player.abilities.join(", ") || "Run and jump"}
                      </dd>
                      <dt>Objective</dt>
                      <dd>
                        {spec.objective.required
                          ? `Collect ${spec.objective.required} crystals, then reach the exit`
                          : "Reach the exit"}
                      </dd>
                      <dt>Artwork</dt>
                      <dd>Kenney Pixel Platformer · CC0</dd>
                    </dl>
                  </>
                ) : (
                  <p>Generate a world to inspect its blueprint.</p>
                )}
              </div>
            )}
            <div className="generation-summary">
              <div className="summary-icon">
                {busy ? (
                  <Loader2 className="spin" size={18} />
                ) : (
                  <Flag size={18} />
                )}
              </div>
              <div>
                <strong>
                  {busy
                    ? "Building, one stage at a time."
                    : preview
                      ? "A starting point for your imagination."
                      : status === "FAILED"
                        ? "The pipeline needs attention."
                        : "Your world, with the process included."}
                </strong>
                <p>
                  {busy
                    ? job?.events.at(-1)?.detail ||
                      "Request accepted. Waiting for the backend."
                    : preview
                      ? "This is a saved deterministic example. Generate a game to create your own design."
                      : "Open the Inspector for actual events, specifications, validation and QA evidence."}
                </p>
              </div>
              <button onClick={() => setInspector(true)} className="text-link">
                View process <ArrowRight size={15} />
              </button>
            </div>
            {job?.job.limitations?.length ? (
              <div className="warnings">
                <strong>Design limitations reported</strong>
                {job.job.limitations.map((v, i) => (
                  <p key={i}>{v}</p>
                ))}
              </div>
            ) : null}
            <div className="canvas-footnote">
              <span>
                <Layers3 size={13} /> COMPOSED FROM TESTED GAME SYSTEMS
              </span>
              <span>Made with Aether</span>
            </div>
          </div>
        </main>
        {inspector && (
          <aside className="inspector-panel">
            <div className="panel-heading">
              <span>
                <Braces size={15} /> Engineering Inspector
              </span>
              <button
                className="icon-button"
                onClick={() => setInspector(false)}
                aria-label="Close inspector"
              >
                <X size={17} />
              </button>
            </div>
            <div className="inspector-content">
              <div className="eyebrow">ACTUAL PIPELINE EVIDENCE</div>
              <h2>Behind the world.</h2>
              <p className="muted">
                Deterministic services are labeled separately from model
                planning. Browser checks do not certify aesthetic quality.
              </p>
              {job ? (
                <>
                  <div className="provenance">
                    <span>Source</span>
                    <strong>
                      {job.job.model_id || "Pending model response"}
                    </strong>
                    <span>Job</span>
                    <code>{job.job.game_id.slice(0, 8)}</code>
                  </div>
                  <div className="event-list">
                    {job.events.map((e) => (
                      <div
                        key={e.id}
                        className={`event ${e.result === "FAILED" ? "failed" : ""}`}
                      >
                        <span className="event-marker">
                          {e.result === "START" ? (
                            <span />
                          ) : (
                            <Check size={11} />
                          )}
                        </span>
                        <div>
                          <strong>{e.stage.replaceAll("_", " ")}</strong>
                          <time>{new Date(e.ts).toLocaleTimeString()}</time>
                          <p>{e.detail}</p>
                          <small>{e.rationale}</small>
                        </div>
                      </div>
                    ))}
                  </div>
                  <label htmlFor="artifact-select">Persisted artifacts</label>
                  <select
                    id="artifact-select"
                    value={artifact}
                    onChange={(e) => setArtifact(e.target.value)}
                  >
                    {Array.from(
                      new Set([artifact, ...Object.keys(job.artifacts)]),
                    ).map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                  <pre>
                    {JSON.stringify(
                      job.artifacts[artifact] ||
                        "This artifact has not been produced yet.",
                      null,
                      2,
                    )}
                  </pre>
                  <button
                    className="button secondary"
                    onClick={() => {
                      const blob = new Blob([JSON.stringify(job, null, 2)], {
                        type: "application/json",
                      });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `aether-${job.job.game_id}.json`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Export engineering evidence <ArrowUpRight size={14} />
                  </button>
                </>
              ) : (
                <div className="inspector-empty">
                  <Code2 size={26} />
                  <h3>No generation has run yet.</h3>
                  <p>
                    The preview is an offline fixture. Submit your idea to see
                    real persisted events here.
                  </p>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
      <div className="studio-statusbar">
        <span>
          <span className="status-dot" /> AETHER STUDIO
        </span>
        <span>
          {busy ? "GENERATION IN PROGRESS" : "READY TO EXPLORE"}{" "}
          <span className="footer-divider">/</span> 2D PLATFORMER
        </span>
        <span>Artwork by Kenney · CC0</span>
      </div>
    </div>
  );
}
export default function Studio() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/forge" element={<Workspace />} />
      <Route path="/studio" element={<Workspace />} />
      <Route path="/studio/play/:id" element={<Workspace />} />
    </Routes>
  );
}
