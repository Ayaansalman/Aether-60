# AETHER Codebase Map & 60% Milestone Gap Analysis

> **Document Version:** 1.0  
> **Target Milestone:** 60% Show-and-Tell Capstone Submission  
> **Source Baseline:** AETHER v3 (30% Prototype)  
> **Reference Document:** *Prompt-to-Game: First Submission Engineering Specification (Four-week roadmap for the 60% show-and-tell milestone)*

---

## 1. Executive Summary & Overview

This repository represents the **30% milestone prototype (`AETHER_V3`)** of the university Final Year Project (FYP): **AETHER** (*Autonomous Engine for Text-to-Heuristic Environmental Rendering*). The core product vision is a **prompt-to-playable-2D-game platform** where a non-technical user inputs a natural language prompt, and the system autonomously plans, validates, renders, tests via automated browser QA, and repairs a 2D game.

### Current High-Level Status:
- The current repository contains **three primary application folders**:
  1. `aether-backend`: A FastAPI Python backend with JWT auth, an in-memory mock database, and social feed endpoints.
  2. `aether-frontend`: A React 19 + Vite single-page application with a dark cyberpunk/glassmorphic UI (Forge, Nexus gallery, Vault dashboard).
  3. `aether-web`: An unconfigured, default Next.js 16 starter application generated with `create-next-app` (currently unused).
- **Core Generation Status**: Currently **100% mocked on both frontend and backend**. Clicking "Construct World" in the frontend triggers client-side `setTimeout` dummy terminal logs. The backend generation endpoint `/api/generate/` only does `await asyncio.sleep(2.0)` and returns a hardcoded blueprint JSON.
- **Game Engine & Runtime Status**: There is **no active game runtime** connected. Phaser is declared in `package.json` in the frontend but not imported. Clicking "Play" in the gallery links to an unrouted `/play/:game_id` path resulting in a blank page. Standalone HTML canvas games exist only as loose files in `Mock Games/`.

---

## 2. Deep-Dive Directory Breakdown

### 2.1 `aether-backend`

#### Purpose
`aether-backend` is the server API for the AETHER platform. It handles user registration/authentication, user profile statistics, game library management (saving, pinning, renaming, deleting), social engagement (likes, comments, share counts), and a stub for game generation.

#### Frameworks & Build Tools
- **Framework:** FastAPI (`fastapi==0.111.0`)
- **ASGI Server:** Uvicorn (`uvicorn==0.29.0`)
- **Data Validation & Schemas:** Pydantic v2 (`pydantic==2.7.1`)
- **Authentication & Security:** `python-jose[cryptography]==3.3.0` (JWT token generation and verification)
- **Database Driver:** `motor==3.4.0` (MongoDB async driver — currently substituted by an in-memory mock in `database.py`)
- **Third-Party Integrations:** `supabase==2.4.5`, `python-dotenv==1.0.1`

#### Exact Commands to Install & Run
Run from the `aether-backend` directory in Windows PowerShell:
```powershell
cd aether-backend

# 1. Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment configuration (optional defaults exist in code)
# Copy .env.example to .env if needed:
# Copy-Item .env.example .env

# 4. Start development server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- CORS is configured to allow `http://localhost:5173` (Vite) and `http://localhost:3000` (Next.js).

#### Backend Endpoints & Route Map
| Prefix | Path | Method | Auth Required | Description |
|---|---|---|---|---|
| `/` | `/` | `GET` | No | Health check returning `{"message": "AETHER Backend API is running"}` |
| `/api/auth` | `/register` | `POST` | No | Creates a user in memory, returns JWT token + user profile |
| `/api/auth` | `/login` | `POST` | No | Validates credentials, returns JWT token + user profile |
| `/api/games` | `/library` | `GET` | Yes (Bearer) | Returns all saved games for authenticated user |
| `/api/games` | `/` | `GET` | No | Returns public games for the Nexus community feed |
| `/api/games` | `/save` | `POST` | Yes (Bearer) | Saves a new game to user library (enforces 20-game limit) |
| `/api/games` | `/{game_id}` | `PATCH` | Yes (Bearer) | Renames, pins, or toggles public visibility |
| `/api/games` | `/{game_id}` | `DELETE` | Yes (Bearer) | Deletes a game from the user library |
| `/api/games` | `/{game_id}/share` | `PATCH` | Yes (Bearer) | Sets `is_public: true` |
| `/api/games` | `/{game_id}/stats` | `GET` | No | Returns plays, views, likes, comments, shares |
| `/api/games` | `/{game_id}/like` | `POST` | Yes (Bearer) | Toggles user like on game |
| `/api/games` | `/{game_id}/comments` | `GET` | No | Returns list of comments for a game |
| `/api/games` | `/{game_id}/comments` | `POST` | Yes (Bearer) | Adds a user comment to a game |
| `/api/games` | `/{game_id}/comments/{id}` | `DELETE` | Yes (Bearer) | Deletes user's own comment |
| `/api/games` | `/{game_id}/share` | `POST` | No | Increments share counter |
| `/api/games` | `/{game_id}/liked` | `GET` | Yes (Bearer) | Checks if authenticated user liked game |
| `/api/users` | `/me` | `GET` | Yes (Bearer) | Returns user profile, aggregate stats, and deployed games |
| `/api/users` | `/me` | `PATCH` | Yes (Bearer) | Updates `display_name` or `subscription` |
| `/api/generate` | `/` | `POST` | Yes (Bearer) | **Mock Game Generation Endpoint** |

#### Prompt Form Submission & Mocking Details
- **Submission Destination:** In the backend code, `POST /api/generate/` receives a `GenerateRequest` (`prompt: str`, `genre: Optional[str]`).
- **Implementation Reality:** It does **NOT** call an LLM (no OpenAI/Anthropic/Gemini SDK is configured or installed).
- Code implementation (`routes/generate.py`):
  ```python
  @router.post("/", status_code=status.HTTP_200_OK)
  async def generate_game(request: GenerateRequest, user=Depends(get_current_user)):
      await asyncio.sleep(2.0)  # Simulates processing
      blueprint = MOCK_BLUEPRINT.copy()
      if request.genre:
          blueprint["genre"] = request.genre.lower()
      return {"message": "Game generated successfully", "blueprint": blueprint}
  ```
- Returns a hardcoded `MOCK_BLUEPRINT` dictionary with static space shooter attributes (`playerConfig`, `enemyConfig`, `spatialLayout`, etc.).

#### Broken, Mocked, or Incomplete Items in `aether-backend`
1. **In-Memory Database (`database.py`):** The database does not persist to MongoDB or SQLite. It uses an in-memory dictionary-backed mock class (`InMemoryDatabase`). **All data is erased upon restart.**
2. **Startup Seed Data (`seed_data.py`):** On startup, `main.py` seeds a hardcoded user (`ayaan@test.com` / `test123`) and 9 sample games with Unsplash image URLs into RAM.
3. **Hardcoded Fallback JWT Secret:** `auth.py` and `routes/auth.py` fallback to `"aether-dev-secret-key-2024"` if `SUPABASE_JWT_SECRET` is unset.
4. **No GameIR Specification:** The returned `blueprint` is an arbitrary JSON dictionary with no strict schema matching the 60% engineering specification.
5. **No Job Queue or Asynchronous Status Pipeline:** No `POST /api/v1/games` that returns HTTP 202 with `game_id` and `status: QUEUED`, no status polling route `GET /api/v1/games/{id}`, and no state transitions (`PLANNING`, `VALIDATING_SPEC`, `BUILDING`, `TESTING`, `REPAIRING`, `READY`).
6. **No Automated QA Runner or Repair Loop:** No Playwright runner or self-repair logic.

---

### 2.2 `aether-frontend`

#### Purpose
`aether-frontend` is the core client application for AETHER v3. It provides a polished, dark cyberpunk UI with glassmorphic cards, neon accent gradients, and animations for browsing community games, viewing user stats, and submitting game prompts.

#### Frameworks & Build Tools
- **Framework:** React 19 (`react==^19.2.6`, `react-dom==^19.2.6`)
- **Build Tool & Dev Server:** Vite 8 (`vite==^8.0.12`, `@vitejs/plugin-react==^6.0.1`)
- **Language:** TypeScript (`typescript==~6.0.2`, `tsconfig.app.json`, `tsconfig.node.json`)
- **Styling:** TailwindCSS 3 (`tailwindcss==^3.4.19`, `postcss==^8.5.14`, `autoprefixer==^10.5.0`)
- **Routing:** React Router DOM v7 (`react-router-dom==^7.15.0`)
- **State Management:** Zustand v5 (`zustand==^5.0.13`)
- **Motion & UI Components:** Framer Motion (`framer-motion==^12.38.0`), Lucide React (`lucide-react==^1.14.0`)
- **Game Engine Dependency:** `"phaser": "^4.1.0"` (present in `package.json`, but currently unimported and unused in any component)

#### Exact Commands to Install & Run
Run from the `aether-frontend` directory in Windows PowerShell:
```powershell
cd aether-frontend

# 1. Install dependencies
npm install

# 2. Environment configuration (optional defaults to http://localhost:8000)
# Copy .env.example to .env if needed:
# Copy-Item .env.example .env

# 3. Start Vite dev server
npm run dev
```
- Client App URL: `http://localhost:5173`

#### Client Pages & Route Map
Defined in `src/App.tsx`:
| Route | Component | File Path | Functionality |
|---|---|---|---|
| `/` | `Landing` | `src/App.tsx` (inline) | Hero section with "Browse Nexus" and "Initialize Core" buttons |
| `/auth` | `Auth` | `src/pages/Auth.tsx` | Tabbed Login & Register form calling `/api/auth/*` |
| `/nexus` | `Nexus` | `src/pages/Nexus.tsx` | Public game gallery with live search, filtering, and `ManifestationCard` grid |
| `/forge` | `Forge` | `src/pages/Forge.tsx` | Prompt input textarea, template selector, simulated terminal |
| `/vault` | `Vault` | `src/pages/Vault.tsx` | User profile, animated metric tiles (plays, views, likes), deployed games list |
| `/play/:game_id` | **MISSING** | **None** | **Route does NOT exist in `App.tsx` (Causes 404/blank screen)** |

#### Where the Prompt Form Submits Right Now
In `src/pages/Forge.tsx`, the prompt form submission handler `handleGenerate` is **entirely mocked client-side with timer callbacks**:
```typescript
const handleGenerate = async () => {
  if (!prompt.trim()) return;
  setIsGenerating(true);
  addLog(`Initiating manifestation sequence for intent: "${prompt.substring(0, 30)}..."`, 'info');
  
  // Fake simulated pipeline stages:
  setTimeout(() => addLog('Semantic Intent Parser: Extracting entities...', 'info'), 1000);
  setTimeout(() => addLog('Blueprint Generation: Querying Neural Vault...', 'info'), 2500);
  setTimeout(() => addLog('Validation Engine: Schema compliance verified.', 'success'), 4000);
  setTimeout(() => addLog('Scene Assembler: Wiring system modules...', 'info'), 5000);
  setTimeout(() => {
    addLog('Manifestation complete. Simulation ready.', 'success');
    setIsGenerating(false);
  }, 6500);
};
```
- **Does it call the backend API?** **NO.** It never calls `fetch()` or `api.ts`.
- `src/lib/api.ts` does not even contain a function to invoke `/api/generate`.
- It does not redirect to a player or create a game in the user's library.

#### Broken, Mocked, or Incomplete Items in `aether-frontend`
1. **Broken `/play/:game_id` Navigation:** In `src/components/ManifestationCard.tsx` (line 81), clicking the hover "Play" button routes to `<Link to={'/play/' + game.game_id}>`. Because `App.tsx` has no `/play/:game_id` route registered, the page goes blank.
2. **Non-Interactive Sidebar Game Items:** In `src/components/Sidebar.tsx`, the game list items in the sidebar history render only text and context menus; clicking on a game item triggers no game opening or navigation.
3. **Phaser Engine Is Completely Missing in Action:** While `"phaser": "^4.1.0"` is in `package.json`, there is no Phaser canvas component, no game runtime, and no game scene. (Note also that the 60% specification requires **Phaser 3**, not the experimental/alpha Phaser 4 release).
4. **No Auth Token Persistence Across Refreshes:** The Zustand `useAuthStore` stores `user` and `token` in memory only without `localStorage` or `sessionStorage` sync; reloading the page logs the user out immediately.
5. **Missing 60% Progress Timeline:** The generation interface shows a terminal window with hardcoded strings rather than the required job timeline showing backend stages (`QUEUED` -> `PLANNING` -> `VALIDATING_SPEC` -> `BUILDING` -> `TESTING` -> `READY`/`REPAIRING`).
6. **No QA Summary or Technical Trace Panels:** No UI exists to display Playwright smoke test passes/failures or repair diffs.

---

### 2.3 `aether-web`

#### Purpose
`aether-web` is a blank, newly scaffolded Next.js boilerplate project.

#### Frameworks & Build Tools
- **Framework:** Next.js 16 (`next==16.2.6`, `react==19.2.4`, `react-dom==19.2.4`)
- **Build Tool:** Turbopack / Next.js CLI
- **Language:** TypeScript (`typescript==^5`, `tsconfig.json`)
- **Styling:** TailwindCSS 4 (`tailwindcss==^4`, `@tailwindcss/postcss==^4`)
- **Linting:** ESLint 9 (`eslint==^9`, `eslint-config-next==16.2.6`)

#### Exact Commands to Install & Run
Run from the `aether-web` directory in Windows PowerShell:
```powershell
cd aether-web

# 1. Install dependencies
npm install

# 2. Start Next dev server
npm run dev
```
- Next.js App URL: `http://localhost:3000`

#### Pages & Routes
- `/` (`src/app/page.tsx`): The generic boilerplate starter page with the Next.js logo and Vercel documentation links.

#### Current State & Engineering Alignment
- **Where the prompt form submits:** Nowhere. There is no prompt form, no AETHER logic, and no API client in `aether-web`.
- **Verdict from 60% Engineering Specification:** Section 3 (Recommended Technology Stack) explicitly states:
  > *"Web UI Choice: Existing React app; use current Vite/build setup if already present. Why: Preserve sunk work and reduce integration risk. What NOT to add yet: Do not rewrite in Next.js just for fashion."*
- **Recommendation:** `aether-web` is an unused side-experiment. For the 60% milestone, **keep `aether-frontend` (React + Vite)** and disregard or archive `aether-web`.

---

### 2.4 `Mock Games` Folder

#### Purpose
Contains 4 standalone single-file HTML5 games:
1. `duelArena.html` (513 lines, 18 KB): A 2-player/canvas duel game.
2. `suicidePaglo.html` (431 lines, 14 KB): A Windows 95 desktop-themed canvas arena game ("Memory Leak - System Breach").
3. `swarmCommander.html` (23 KB): Top-down tactical swarm arena.
4. `carSpeedRun.html` (20 KB): 2D top-down vehicle obstacle game.

#### Implementation Reality
- These games are written directly in HTML5 Canvas 2D and vanilla JavaScript without Phaser.
- They were used as presentation props/mockups during the initial 30% milestone review.
- They do not parse GameIR, do not integrate with the React frontend, and cannot be instrumented with the 60% Playwright automated QA harness.

---

## 3. Comparison Matrix: Current 30% Prototype vs. 60% Specification Requirements

| Architecture Area | Current 30% Prototype (`AETHER_V3`) | Required 60% Specification | Gap Status |
|---|---|---|---|
| **Web Frontend** | `aether-frontend` (React 19 + Vite + TailwindCSS 3) | Keep existing React + Vite app; do not rewrite in Next.js | **Keep & extend `aether-frontend`** |
| **Prompt Input** | 500-char limit in `Forge.tsx`, simulated client `setTimeout` logs | 1200-char limit, sample prompt chips, submit to `POST /api/v1/games` | **Broken/Mocked; Needs real API wiring** |
| **Job Lifecycle UI** | Fake terminal with hardcoded strings | Real timeline polling `GET /api/v1/games/{id}`: `PLANNING` -> `VALIDATING` -> `BUILDING` -> `TESTING` -> `REPAIRING` -> `READY` | **Missing; Needs to be built** |
| **Game Player Route** | No route in `App.tsx`; `/play/:id` throws blank screen | `/play/:gameId` route loading validated GameIR from backend into a Phaser 3 canvas | **Broken; Needs Phaser 3 player route** |
| **Game Engine** | Phaser 4 listed in `package.json` but 0% imported | Phaser 3 + TypeScript trusted runtime with modular components (`PlayerController`, `EnemySystem`, `AttackSystem`, `HUD`, `Restart`) | **Missing; Needs Phaser 3 runtime** |
| **Supported Genre** | Static dropdown (`space_shooter`, `endless_runner`), no engine implementation | One dependable archetype: **Top-down arena survival** | **Needs Top-Down Arena implementation** |
| **Game Contract** | Arbitrary unvalidated JSON blueprint | Versioned **GameIR v1** Pydantic schema with strict bounds and enums | **Missing; Needs GameIR Pydantic model** |
| **Model Integration** | None (`asyncio.sleep(2.0)` in `generate.py`) | `ModelProvider` protocol with official SDK (structured outputs) + `MockModelProvider` for testing | **Missing; Needs ModelProvider** |
| **Automated QA** | None | Playwright Python runner with 10 critical checks (canvas visible, player moves, objective updates, restart resets state) | **Missing; Needs Playwright QA runner** |
| **Self-Repair Loop** | None | Bounded repair (max 2 retries) with constrained `GameIRPatch` schema feeding failed test feedback back to the LLM | **Missing; Needs repair service** |
| **Job Persistence** | In-memory RAM collections (wiped on restart) | SQLite database for jobs/events + file artifacts (`artifacts/<game_id>/...`) | **Needs SQLite + artifact file storage** |
| **Evaluator Trace** | None | Technical trace drawer in UI showing GameIR, test report, repair diff, and raw event log | **Missing; Needs trace UI panel** |

---

## 4. Immediate Recommended Action Plan

To transition from the 30% mock prototype to a working 60% vertical slice without breaking existing work:

1. **Retain and standardize on `aether-backend` and `aether-frontend`:**
   - Archive or ignore `aether-web` (complying directly with Executive Decision #1 and #3).
2. **Build the GameIR v1 Contract in `aether-backend`:**
   - Define Pydantic schema `GameIR` with the required fields: `schema_version: "1.0"`, `title`, `genre: "arena_survival"`, `player` (speed, max_health, attack_mode), `enemies` (list of types and counts), `collectibles`, `objective` (survive_seconds or collect_count), `difficulty`, `controls`, and `seed`.
3. **Build the Trusted Phaser 3 Runtime in `aether-frontend`:**
   - Install stable Phaser 3 (`npm i phaser@^3.88.0`).
   - Register the `/play/:gameId` route in `App.tsx`.
   - Create a clean Phaser canvas wrapper that accepts a GameIR JSON document and renders the player, enemies, collectibles, HUD, and restart screen.
4. **Implement the FastAPI Job Queue & State Machine:**
   - Implement `POST /api/v1/games` and `GET /api/v1/games/{id}`.
   - Persist job state and events into SQLite (`data/app.db`).
5. **Connect the LLM Planner & Mock Provider:**
   - Implement `ModelProvider` protocol with structured output generation.
   - Build `MockModelProvider` returning deterministic GameIR for fast local testing without spending API credits.
6. **Implement Playwright QA Smoke Tests & Bounded Repair:**
   - Add test hooks to the Phaser runtime.
   - Launch headless Chromium via Playwright in Python to verify canvas presence, player movement, and restart.
   - If critical checks fail, trigger the repair service with `GameIRPatch` (max 2 retries).
7. **Upgrade the UI in `Forge.tsx`:**
   - Replace the fake `setTimeout` terminal with live status polling against `/api/v1/games/{id}`.
   - Display the QA report and provide a one-click launcher into the game player.
