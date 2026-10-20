# How to Run AETHER (Operational Guide)

This guide provides exact Windows PowerShell commands to run, test, evaluate, and demonstrate the AETHER Game Synthesis and Self-Repair Engine.

---

## 1. Prerequisites Check

Open PowerShell and verify:
```powershell
python --version   # Must be 3.11+
node --version     # Must be 18.0+ or 20.0+
npm --version
```

If Node.js is installed in `C:\Program Files\nodejs` but not on your user PATH:
```powershell
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
```

---

## 2. Running in Mock Mode (Zero API Usage / Offline Testing)

Mock mode runs the entire pipeline locally without contacting any external LLM provider. It uses deterministic spec synthesis and repair, making it ideal for testing, automated QA, and offline development.

### Option A: Using the One-Click Launcher
```powershell
# From the repository root:
.\scripts\start_all.ps1 -Mock
```
This script:
1. Sets `MODEL_PROVIDER=mock` for the process.
2. Starts the FastAPI backend on `http://localhost:8000`.
3. Starts the Vite dev server on `http://localhost:5173`.
4. Waits for `/api/v1/health` to report ready.
5. Launches your default browser directly to `http://localhost:5173/forge`.

### Option B: Running Manually in Separate Terminals

**Terminal 1 (Backend):**
```powershell
cd aether-backend
$env:MODEL_PROVIDER = "mock"
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd aether-frontend
npm run dev
```

### Stopping All Servers
```powershell
.\scripts\stop_all.ps1
```

---

## 3. Running in Live Gemini Mode (Real Model Generation)

Live mode connects to Google AI Studio Gemini API via the OpenAI-compatible endpoint.

### Step 1: Configure `.env`
Ensure `aether-backend\.env` contains your API key:
```dotenv
MODEL_PROVIDER=openai_compat
MODEL_API_KEY=your_gemini_api_key_here
MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL_NAME=gemini-3.5-flash-lite
MODEL_FALLBACKS=gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite
MODEL_TIMEOUT_SECONDS=60.0
```

### Step 2: Launch the System
```powershell
# From the repository root:
.\scripts\start_all.ps1
```
The console banner will verify:
```
============================================================
              AETHER SYSTEM LAUNCHER (V3)                  
============================================================
  Backend Provider : openai_compat
  Primary Model    : gemini-3.5-flash-lite
  API Key Status   : Configured (Hidden)
============================================================
```

---

## 4. Running the Verification & Test Suites

### A. Python Backend Pytest Suite (137 tests)
```powershell
# From the repository root:
.\aether-backend\venv\Scripts\python.exe -m pytest aether-backend\tests -v
```

### B. Frontend TypeScript & Production Build Verification
```powershell
cd aether-frontend
npx tsc --noEmit
npm run lint
npm run build
cd ..
```

### C. Headless Playwright QA Suites (All 4 Baseline Demo Routes)
```powershell
# Verifies all 17 QA checks on /play/demo, /play/demo-survive, /play/demo-melee, and /play/demo-avoid:
.\aether-backend\venv\Scripts\python.exe scripts\run_qa_all.py
```

### D. Headless Playwright QA Suites (All 5 Mechanic Variety Routes)
```powershell
# Verifies all 17 QA checks on bouncer-pillars, patrol-lanes, dasher-defeat, shooter-pillars, and maze-collect:
.\aether-backend\venv\Scripts\python.exe scripts\run_variety_qa.py
```

### E. Known-Broken Fixture Verification (3/3 Detection)
```powershell
# Verifies deliberate failure modes (restart_keeps_hp, no_win, demo-too-hard) are detected & rejected:
.\aether-backend\venv\Scripts\python.exe scripts\run_qa_fixtures.py
```

### F. End-to-End Pipeline Smoke Test
```powershell
# Starts servers, submits prompt, tests game in headless browser, captures screenshot:
.\aether-backend\venv\Scripts\python.exe scripts\e2e_smoke.py
```

### G. Automated Repair Demo
```powershell
# Demonstrates lethal spec failure triggering repair agent to produce a playable game:
.\aether-backend\venv\Scripts\python.exe scripts\repair_demo.py
```

---

## 5. Running Full-Pipeline Evaluation (`run_real_eval.ps1`)

The standalone evaluation runner automates running the benchmark prompt suite across real models or mock mode.

### Running Mock Evaluation Benchmark:
```powershell
.\scripts\run_real_eval.ps1 -Mock
```

### Running Real Gemini Benchmark:
```powershell
# Run with gemini-3.5-flash-lite (5s delay between prompts):
.\scripts\run_real_eval.ps1 -ModelId "gemini-3.5-flash-lite" -Delay 5.0 -MaxRequests 60

# Run with gemini-3.8-flash (13s delay to respect free-tier RPM limits):
.\scripts\run_real_eval.ps1 -ModelId "gemini-3.8-flash" -Delay 13.0 -MaxRequests 18
```
This automatically:
1. Enforces fallback disabled (`MODEL_FALLBACKS=""`) to guarantee clean, unpolluted per-model measurements.
2. Starts the Vite dev server.
3. Executes `scripts/run_eval.py --real --qa-mode real`.
4. Gracefully stops the Vite server.
5. Saves results to `artifacts/eval/` and copies them to `docs/eval/`.
6. Regenerates the comprehensive `docs/EVAL_RESULTS.md` report table.

---

## 6. Running the Offline Demo (Zero AI Agent / Zero Backend)

The offline demo provides a failsafe demonstration experience that requires **zero LLM API calls** and can run with the **backend completely stopped**.

### Method 1: Using the "Load saved demo" Row on the Forge Page
1. Ensure the frontend is running (`cd aether-frontend; npm run dev`).
2. Open `http://localhost:5173/forge`.
3. Locate the **"Load saved demo"** section (labeled with the **"Saved result (offline demo)"** badge).
4. Click any of the 3 pre-recorded authentic generation artifacts:
   - **Spooky Crystal Dungeon** (gemini-3.5-flash-lite Run A p01): Collect crystals while avoiding ghosts.
   - **Pirate Cove Treasure Hunt** (gemini-3.5-flash-lite Run A p03): Collect pirate treasure chests while pursued by rival skiffs.
   - **Shadow Pursuit (Repaired)** (gemini-3.5-flash-lite Run A2 s01 repaired): A high-speed pursuit arena repaired by lowering enemy speed and boosting player health.
5. The Forge page instantly populates the full timeline, validated GameIR spec, QA checks, and Play button without calling the backend.

### Method 2: Direct Static Browser URLs
You can open any of the following URLs directly in Google Chrome (with frontend running on `http://localhost:5173`):

#### Baseline Archetypes:
- `http://localhost:5173/play/demo`: Baseline fantasy projectile attack survival game.
- `http://localhost:5173/play/demo-survive`: Sci-fi survive 30-seconds objective.
- `http://localhost:5173/play/demo-melee`: Spooky melee-attack survival.
- `http://localhost:5173/play/demo-avoid`: Cozy avoid-only objective.

#### 5 Mechanic Variety Demos:
- `http://localhost:5173/play/demo-bouncer-pillars`: Bouncer AI (ricochet) + 4 pillar obstacles.
- `http://localhost:5173/play/demo-patrol-lanes`: Patroller AI (horizontal lane oscillation) + horizontal partition wall lanes, avoid-only movement, collect 8 berries objective.
- `http://localhost:5173/play/demo-dasher-defeat`: Dasher AI (lunge) + melee weapon + defeat_enemies objective.
- `http://localhost:5173/play/demo-shooter-pillars`: Shooter AI (ranged bullets) + pillars layout.
- `http://localhost:5173/play/demo-maze-collect`: Maze layout with safe central corridors + crystal collection.

#### Visual Themes:
- `http://localhost:5173/play/theme-fantasy`: Arcane Crystal Grove (purple/gold palette).
- `http://localhost:5173/play/theme-sci-fi`: Cyber Void Surge (cyan/neon palette).
- `http://localhost:5173/play/theme-pirate`: Treasure Cove Hunt (emerald/gold palette).
- `http://localhost:5173/play/theme-spooky`: Spooky Crypt Haunt (green/purple palette).
- `http://localhost:5173/play/theme-cozy`: Enchanted Meadow Gathering (warm amber palette).

#### Offline Fallback Demos:
- `http://localhost:5173/play/fallback-spooky`: Spooky Crystal Dungeon (Run A p01).
- `http://localhost:5173/play/fallback-pirate`: Pirate Cove Treasure Hunt (Run A p03).
- `http://localhost:5173/play/fallback-repaired`: Shadow Pursuit (Repaired) (Run A2 s01).

#### Test / Unplayable Fixtures:
- `http://localhost:5173/play/demo-too-hard`: Brutal unplayable fixture (12 enemies @ 240 px/s, 1 HP).

