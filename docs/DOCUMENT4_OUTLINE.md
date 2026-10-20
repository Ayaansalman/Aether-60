# Capstone Document 4 Outline & Evidence Traceability Matrix

This document outlines the structure of Final Capstone Document 4 and maps each section to the repository technical documents and evaluation artifacts providing its evidence.

---

## 1. Safe Engineering Claim (Blueprint Section 17)

> **Official Safe Claim**:  
> *"We built a prompt-to-browser-game prototype with a structured game representation, automated smoke tests, and a bounded repair loop."*

---

## 2. Document 4 Chapter Outline & Artifact Mapping

### Chapter 1: Introduction, Problem Statement & Motivation
- **Content**: Challenges of LLM game generation (code hallucination, syntax crashes, unplayable physics parameters).
- **Feeding Artifacts & Docs**:
  - `docs/architecture.md` (System overview, pipeline architecture)
  - `docs/LIMITATIONS.md` (Scope definition, 60% boundary)

### Chapter 2: System Architecture & The GameIR Contract
- **Content**: Intermediate representation design, Pydantic v2 strict typing, state machine lifecycle (`QUEUED` to `READY`).
- **Feeding Artifacts & Docs**:
  - `docs/architecture.md` (State machine, SQLite store, concurrency model)
  - `docs/GameIR-v1.md` (Complete schema specifications and allowed patch ranges)
  - `docs/api-contract.md` (REST API `/api/v1` routes and error codes)

### Chapter 3: Automated Browser QA Verification (Playwright)
- **Content**: Black-box simulation testing, `window.__AETHER_GAME__` hook, 17 spec-level smoke checks, velocity sampling, survival bounds.
- **Feeding Artifacts & Docs**:
  - `docs/QA_CHECKS.md` (Complete definitions of all 17 checks, patchable vs non-patchable policy)
  - `docs/QA_HOOK.md` (Hook API and security isolation)
  - `scripts/run_qa_all.py` (Empirical 17/17 pass across 4 demo archetypes)
  - `scripts/run_qa_fixtures.py` (Detection of seeded failure fixtures)

### Chapter 4: The Closed-Loop Bounded Self-Repair Agent
- **Content**: Playability failure diagnosis, prompt formulation, patch validation, no-op rejection, max 2 repairs.
- **Feeding Artifacts & Docs**:
  - `docs/REPAIR_LOOP.md` (Repair loop design and empirical evidence)
  - `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` (Run A: 0 of 2 repairs succeeded)
  - `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json` (Run A2: re-run of 3 dev prompts after tuning repair prompt; repaired 2 of 2 (`s01`, `s02`), `p06` was not repaired; tiny sample, dev cases, not an unbiased estimate)
  - `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json` (Run D: 3 of 3 repairs succeeded)
  - `scripts/repair_demo.py` (Deterministic repair demonstration)

### Chapter 5: Empirical Evaluation & Comparative Benchmark Analysis
- **Content**: Multi-model benchmark results, Playable@1 vs Playable@3, latency distribution, limitation honesty, evaluation caveats.
- **Feeding Artifacts & Docs**:
  - `docs/EVAL_RESULTS.md` (Comprehensive benchmark comparative tables)
  - `docs/TEST_REPORT.md` (Empirical dashboard across all test suites)
  - `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` (Run A 12-prompt dataset: 91.7% first-valid, 75.0% Playable@1, 75.0% Playable@3, 0/2 repairs, median latency 45,807.6 ms)
  - `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json` (Run D: upgraded engine, 12/12 completed, first-valid 12/12, Playable@1 9/12, Playable@3 12/12, repair 3/3, 18 model requests, median latency 47,020.5 ms)
- **Evaluation Caveats**:
  - Playable@1 equals Run A (9/12).
  - `p06`, `s01`, and `s02` failed first in Runs A, A2, and D and were also the cases used to tune the QA check and repair prompt, so Run D is a development-set result, not a held-out estimate.
  - One run per prompt, results can vary between runs.
  - Run D prompts are the same 12 as Run A and do not measure the new enemy types and layouts.
  - The engine, QA runner, and repair prompt differ from Run A, so the comparison is not single-variable.

### Chapter 6: Demo Resilience, Operational Launchers & Packaging
- **Content**: Zero-API offline demo implementation, PowerShell automation scripts, fallback chains.
- **Feeding Artifacts & Docs**:
  - `README.md` (Setup instructions)
  - `docs/HOW_TO_RUN.md` (Exact operational commands)
  - `docs/DEMO_RUNBOOK.md` (Demo scripts and contingency procedures)

### Chapter 7: Limitations, Ethical Considerations & Future Work
- **Content**: Boundaries of 60% milestone, single archetype constraint, chaser enemy restriction, future path to 100% milestone.
- **Feeding Artifacts & Docs**:
  - `docs/LIMITATIONS.md`
  - `docs/MODULE_OWNERSHIP.md` (Viva questions and subsystem mastery)
