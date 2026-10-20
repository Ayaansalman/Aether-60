# AETHER REST API Contract (`/api/v1`)

This document specifies the complete REST API contract exposed by the AETHER backend (`aether-backend/routes/games_v1.py`).

---

## 1. General Conventions

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json` (unless downloading raw artifact files)
- **Authentication**: Public endpoints (no API keys or session cookies required for local capstone scope)
- **CORS**: Allows origin `http://localhost:5173` with credentials

---

## 2. Endpoint Specifications

### 2.1 Submit Generation Request
- **Route**: `POST /api/v1/games`
- **Status Code**: `202 Accepted`
- **Description**: Submits a natural language prompt to the synthesis pipeline. The job is persisted immediately in SQLite before background processing begins.
- **Request Body**:
  ```json
  {
    "prompt": "a cybernetic ninja dodging laser drones in a neon rooftop arena"
  }
  ```
  - `prompt`: String, minimum 1 character, maximum 1200 characters (trimmed).
- **Success Response (`202 Accepted`)**:
  ```json
  {
    "id": "7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "status": "QUEUED"
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Empty, whitespace-only, or prompt exceeding 1200 characters.

---

### 2.2 Get Game Status & Summary
- **Route**: `GET /api/v1/games/{id}`
- **Description**: Returns the execution state, current stage, attempt count, QA check summary, and limitation disclosures.
- **Success Response (`200 OK`)**:
  ```json
  {
    "id": "7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "prompt": "a cybernetic ninja dodging laser drones in a neon rooftop arena",
    "status": "READY",
    "stage": "TESTING",
    "attempt": 1,
    "max_attempts": 3,
    "created_at": 1728901200.0,
    "updated_at": 1728901245.0,
    "game_url": "http://localhost:5173/play/7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "qa_summary": {
      "passed": [
        "canvas_visible", "hook_ready", "no_page_errors", "player_present",
        "player_moves", "movement_speed_consistent", "attack_responds",
        "hud_consistent", "win_reachable", "no_actions_after_end",
        "restart_resets_after_win", "lose_reachable", "restart_resets_after_lose",
        "no_duplicate_enemies_after_restart", "screenshot_captured",
        "idle_survival_min_seconds", "flee_bot_survives"
      ],
      "failed": [],
      "critical_failed": []
    },
    "limitations": [
      "Adapted 3D rooftop into 2D top-down arena",
      "Using standard chaser enemy archetype for drones"
    ],
    "error_code": null
  }
  ```
- **Error Responses**:
  - `404 Not Found`: Job ID does not exist (`GAME_NOT_FOUND`).

---

### 2.3 Get Validated GameIR Specification
- **Route**: `GET /api/v1/games/{id}/spec`
- **Description**: Returns the active, validated GameIR v1 JSON specification consumed by the Phaser 3 frontend.
- **Success Response (`200 OK`)**: Complete `GameIR` JSON document.
- **Error Responses**:
  - `404 Not Found`: Game does not exist or spec has not yet been validated.

---

### 2.4 Get Latest QA Report
- **Route**: `GET /api/v1/games/{id}/qa`
- **Description**: Returns the detailed Playwright QA test report for the latest test attempt.
- **Success Response (`200 OK`)**:
  ```json
  {
    "url": "http://localhost:5173/play/7b0b69fb-13c5-430c-96b6-3c0516ca8371?test=1",
    "overall": "PASS",
    "checks": [
      {
        "id": "canvas_visible",
        "critical": true,
        "patchable": false,
        "passed": true,
        "message": ""
      },
      {
        "id": "idle_survival_min_seconds",
        "critical": true,
        "patchable": true,
        "passed": true,
        "message": "Player survived 5.31s without input (>= 4.0s required)"
      }
    ],
    "page_errors": [],
    "screenshot_path": "artifacts/7b0b69fb-13c5-430c-96b6-3c0516ca8371/screenshots/7b0b69fb-13c5-430c-96b6-3c0516ca8371.png",
    "repair_recommended": false
  }
  ```
- **Error Responses**:
  - `404 Not Found`: No QA report available for this game.

---

### 2.5 Get Chronological Event Audit Stream
- **Route**: `GET /api/v1/games/{id}/events`
- **Description**: Returns an ordered list of timeline events recording state transitions, validation results, and repair patches.
- **Success Response (`200 OK`)**:
  ```json
  [
    {
      "timestamp": 1728901201.2,
      "stage": "PLANNING",
      "result": "OK",
      "detail": "Prompt dispatched to gemini-3.5-flash-lite",
      "attempt": 1
    },
    {
      "timestamp": 1728901220.5,
      "stage": "VALIDATING_SPEC",
      "result": "OK",
      "detail": "GameIR validated successfully",
      "attempt": 1
    },
    {
      "timestamp": 1728901245.1,
      "stage": "TESTING",
      "result": "OK",
      "detail": "All 17 QA checks passed (17/17)",
      "attempt": 1
    }
  ]
  ```

---

### 2.6 Safe Artifact Download
- **Route**: `GET /api/v1/games/{id}/artifacts/{name}`
- **Description**: Safely retrieves raw artifact files using a strict whitelist.
- **Whitelisted Filenames**:
  - `game_ir_v1.json`, `game_ir_v2.json`, `game_ir_v3.json`
  - `qa_report_attempt_1.json`, `qa_report_attempt_2.json`, `qa_report_attempt_3.json`
  - `agent_trace.jsonl`
- **Error Responses**:
  - `400 Bad Request`: Requested filename is not whitelisted or path traversal detected.
  - `404 Not Found`: Artifact file does not exist.

---

### 2.7 System Health Check
- **Route**: `GET /api/v1/health`
- **Description**: Returns active provider, model name, and boolean key status. **Never exposes secret tokens or API keys**.
- **Success Response (`200 OK`)**:
  ```json
  {
    "status": "ok",
    "provider": "openai_compat",
    "model": "gemini-3.5-flash-lite",
    "key_configured": true
  }
  ```

---

## 3. Standardized Error Code Registry

| Error Code | HTTP Status | Description & Root Cause |
|---|---|---|
| `PROMPT_INVALID` | `400` | User prompt was empty, whitespace-only, or exceeded 1200 characters. |
| `MODEL_TIMEOUT` | `504` | Model provider failed to respond within `MODEL_TIMEOUT_SECONDS` (default 60s). |
| `MODEL_HTTP_ERROR` | `502` | Provider returned fatal HTTP 5xx or unresolvable 429 after retries and fallback exhaustion. |
| `MODEL_OUTPUT_INVALID` | `422` | Model output was not valid JSON or failed Pydantic schema validation after 2 retries. |
| `SPEC_UNSUPPORTED` | `422` | Spec requested unsupported genre or mechanics outside the 60% GameIR boundary. |
| `QA_CRASHED` | `500` | Headless Playwright subprocess crashed, timed out (>180s), or threw an unexpected exception. |
| `QA_FAILED` | `422` | Critical non-patchable check failed (e.g. canvas stalled, restart broke). |
| `REPAIR_LIMIT_REACHED` | `422` | Spec remained unplayable after maximum allowed repair attempts (2 repairs = 3 tests). |
| `GAME_NOT_FOUND` | `404` | Requested `game_id` was not found in SQLite store. |
| `INTERNAL_ERROR` | `500` | Server was restarted while job was in-flight, or uncaught server exception. |
