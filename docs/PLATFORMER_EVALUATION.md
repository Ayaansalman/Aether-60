# Platformer evaluation results â€” 2026-10-20

All four prompts below used actual Gemini completions through the existing OpenAI-compatible provider. Fixture results are separate. Earlier failed reports are preserved inside each JSON export; final results include re-verification after developer fixes.

| Prompt | Live title | Final browser checks | Outcome |
|---|---|---|---|
| forest | Shrine of the Whispering Woods | 14 passed, 0 failed | READY |
| industrial | Factory Floor 42 | 13 passed, 0 failed | READY |
| tower | Tower of the Sky | 12 passed, 0 failed | READY_WITH_WARNINGS |
| peaceful | Whispering Woods | 12 passed, 0 failed | READY |

The original tower result reports `dash` as unsupported even though it was not requested and dash is supported. That original model output is preserved honestly. The current capability guard removes such exact registered-capability contradictions for new jobs. The fifth UI-generated design reported broader, unrequested combat/inventory limitations; the interface labels these as design limitations, not evidence that requested features were absent. The current model prompt explicitly prohibits inventing such limitations.

## Creator UI and repair evidence

A fifth real live request submitted through the UI produced **Clockwork Core Escape** (`e5737bfe-2946-4c54-a844-0a2918d0ba99`). It completed with 12 passing browser checks and design warnings. Actual initial browser route failure triggered one deterministic layout repair. `ui-live-result.json` includes the initial failed QA, evidence, before/after IR, repair validation and successful rerun. `final-runtime-qa.json` separately verifies the final renderer and a 620 px/s dash with measurable displacement.

## Verification

- Backend: 154 tests passed, including 137 preserved original tests and 17 platformer contract/API/repair tests. API unit tests explicitly stub browser outcomes; they are not presented as live QA.
- Frontend: production build and ESLint pass. Phaser remains a separately loaded large engine chunk.
- UI: 15 final checks passed, covering desktop/mobile typing, design view, honest Inspector, horizontal overflow, runtime errors, touch movement, keyboard/toolbar restart, expanded preview with Escape and evidence export. See `ui-checks-final.json`.
- Asset dimensions and SHA-256 dependencies checked. Two CC0 packs integrated without redundant individual tiles.
- Screenshot review: rendered forest, factory, tower and peaceful games, landing top/bottom, desktop creator/Inspector and mobile game/Inspector reviewed. HUD scaling was increased for narrow previews after mobile review.
- Dependency audit reduced from 16 to 7 findings: 5 high and 2 moderate in the Tailwind build-tool chain. A breaking Tailwind major migration is deferred.

## What this does not establish

Browser route checks use actual keyboard jumps from isolated launch positions. Objective/health/checkpoint transitions use disclosed controlled placement or damage injection. These are not complete autonomous playthroughs. Functional passes do not establish enjoyment, perfect prompt fidelity or an aesthetic score. Current platformer art has two authored player frames, no dedicated damage sprites or soundtrack. Only the platformer v2 genre is implemented. No deployment or push occurred.
