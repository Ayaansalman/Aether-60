# QA recheck synchronization fix — 2026-10-22

The reported Last Stand job is `f7251922-96c7-4e47-8f64-53a981bb943c`. Its saved status was READY_WITH_WARNINGS and its first explicit recheck passed all 12 browser checks, but `qa_report.json` still contained the original failure. The new public preview gate consulted that original file and therefore withheld the game. The recheck backend already updated `latest_qa_json`, semantic coverage and job status, but saved the new report only as `qa_retest_1.json`. This pre-existing inconsistency was missed by the readiness update's initial tests, which used fresh pipelines without failed-then-passing explicit rechecks.

Changes:

- Rechecks update the current canonical QA report, preserve the original report and every numbered recheck, clear obsolete processing errors and emit a terminal status event. A recheck processing exception now becomes an explicit FAILED job with a safe diagnostic rather than leaving TESTING forever.
- Studio uses the highest numbered completed recheck when loading historical jobs whose canonical report is stale. A later failing or unavailable recheck still blocks play; mandatory semantic failures still block play. Historical failure reports no longer label an actively running recheck as stopped.
- The original composition projectile probe's snapshot showed health zero before its damage test could complete. That probe reused the character from an earlier real-time scheduling/evasion test. It now starts a fresh real run for collision testing and chooses an emitted projectile at least 80 pixels from enemies, excluding contact damage as the source. Timers, health values and projectile collision rules are not overridden, and the damage check remains mandatory.

Verification:

- 77 focused backend tests pass, including failed → passing → failing rechecks for platformer, runner and adventure, preserved original evidence, terminal exception handling and previous Iteration 7/10 coverage.
- 44 frontend behavior/state tests, lint, TypeScript and production build pass. Existing Phaser bundle-size warning remains.
- 14 controlled-response browser UI checks pass, including historical canonical FAIL plus numbered recheck PASS and active-recheck display with stale failed reports.
- The exact saved Last Stand specification passed all 12 browser QA checks in a direct run with the isolated projectile probe, then in two actual HTTP rechecks. The final recheck was triggered through the real Inspector action: public canvas hidden during TESTING, current and numbered reports both PASS, original FAIL retained, READY_WITH_WARNINGS terminal event, visible runtime, real keyboard movement and zero page exceptions.

One intermediate observer script initiated a recheck externally after its browser had already stopped polling a terminal job. That browser stayed on its previous ready output; the observer was corrected to use the actual Inspector action, which resumes polling. This was a test setup issue, not evidence that the Studio action failed to hold the preview. A separate initial browser probe omitted the existing `test=1` telemetry flag and timed out waiting for a development-only hook; it was corrected without changing the runtime.

Evidence: `evidence/qa-recheck-fix/source.json`, `damage-run-1/qa_report.json`, `browser-recovery.json`, and `last-stand-recovered.png`; expanded UI evidence remains in `evidence/presentation-ready/ui/`. Reproduction: `scripts/verify_saved_recheck.py <built-job-id>` performs a real explicit recheck and consumes one of the existing three allowed user rechecks. Last Stand has now reached that limit and needs no further recheck to play.

The main local backend was restarted with the correction. No new model completions, game regeneration, validation downgrades, push or deployment. The original failed QA evidence remains available for inspection. These controlled browser probes are not a certification of every generated prompt or an autonomous full playthrough.
