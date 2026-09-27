# Tasks

## 1. Clock scaffold

- [x] 1.1 Implement `apps/client-godot/scripts/game_clock.gd` per design D1–D5: unanchored and running at startup with a zero epoch, `anchor(server_time) -> {ok, error}` with fail-closed validation (positive timestamp, unanchored), `clear()` returning to unanchored with zero elapsed, independent `pause()` / `resume()` / `advance(msec)` controls with fail-closed advance (positive count, paused), getters reflecting only committed state (`is_anchored`, `is_paused`, `server_time`, `elapsed_msec`, `now_epoch_sec`), and `clock_anchored` / `clock_cleared` / `clock_paused_changed` / `clock_ticked` signals with the specified emission rules — the file contains no project-scope forbidden token (camera, UI foundation, legacy protocol, transport; scope suite) and no wall-clock, persistence, or content-loading reference (direct source scan of `res://scripts/game_clock.gd` inside its own suite, since the approved scope contract keeps `FORBIDDEN` at 16 tokens and does not add a wall-clock token).
- [x] 1.2 Register the `GameClock` autoload in `apps/client-godot/project.godot` (fourth line, after `Session`) and update the `[autoload]` header comment to the four-autoload boundary.
- [x] 1.3 Add `apps/client-godot/tests/test_game_clock.gd` with the scaffold and notification scenarios (no implicit anchor at startup; anchor-once success with getter/signal assertions; invalid anchors rejected with state unchanged; pause freezes across frames and resume continues with exactly one notification each; advance exact and fail-closed for zero/negative/while-running; clear semantics including the silent repeated clear; every notification payload equal to the committed elapsed time at emission, strictly increasing within a base, exactly one notification per crossing frame) — verified `godot --headless --path apps/client-godot -s res://tests/test_game_clock.gd -- --gameapi-endpoint=http://127.0.0.1:5057` exits 0 with `[test] PASS checks=110`.

## 2. Boot integration

- [x] 2.1 Modify `apps/client-godot/scripts/boot.gd` per design D6: guard the `GameClock` autoload (`gameclock_missing`), clear any previous anchor on `_boot()` entry, anchor with `save_list.server_time` immediately before `Session.activate`, and fail closed with `gameclock_anchor` if anchoring unexpectedly fails — extend `tests/test_game_clock.gd` with the boot-integration pair (successful fake boot anchors the clock to the fixture epoch with one `clock_anchored`; a failing follow-up attempt clears the previous anchor on entry and leaves the clock unanchored) using the fake implementation and a loopback endpoint with nothing listening — verified the suite exits 0 with `[test] PASS` headless.
- [x] 2.2 Extend `apps/client-godot/tests/test_boot_scene.gd` with clock assertions: at ready the clock is anchored and its epoch is at or ahead of the fixture response timestamp within a bounded post-anchor interval; in both the `unreachable` and `api-error` scenarios the clock is unanchored with a zero epoch — verified the hermetic fake run exits 0 with `[test] PASS checks=32`, the `unreachable` run `checks=19`, the `api-error` run `checks=18`, and all three also execute under `verify-boot.ps1`.
- [x] 2.3 Add `test_game_clock` to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and header — verified `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records the suite (`test_game_clock exits 0`, `test_game_clock reports PASS` in `boot-report.json`).

## 3. Scope contract

- [x] 3.1 Update `apps/client-godot/tests/test_project_scope.gd` per design D9: `ALLOWED` += `scripts/game_clock.gd` and `tests/test_game_clock.gd`, `EXPECTED_AUTOLOADS` = exactly the four autoload lines in project order, `FORBIDDEN` drops `"GameClock"` with the count assertion 17 → 16, and the doc comments describe the four-autoload boundary — verified the suite exits 0 with `[test] PASS checks=613` headless (39 project files, 30 scanned sources) while still asserting every remaining forbidden token.

## 4. Documentation

- [x] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed six-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session, game clock) — every documented command line matches a command executed green in group 5.
- [x] 4.2 Update `apps/client-godot/README.md` with the game-clock suite's purpose, invocation, and observed check count (110), the `verify-boot.ps1` six-suite narrative, and the updated project-scope count (613) — recorded counts equal the `[test] PASS checks=N` lines observed in the final battery.

## 5. Verification and records

- [x] 5.1 Full battery in the final state, all exit 0: `powershell -File apps/client-godot/verify.ps1`; `powershell -File apps/client-godot/verify-boot.ps1` (guard verify embedded pre/post, digests equal `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348`); `git diff --check`; `openspec validate godot-game-clock --strict`; `openspec validate --all --strict` (31 passed, 0 failed). Observed counts: loader 123, scene-build 36, project-scope 613, content-registry 52, asset-ids 50, game-api-fake 29, boot-scene 32/19/18, session 67, game clock 110; `boot-report.json` 48 assertions, `pass=true`, first-render evidence byte-identical (`git status` shows no first-render or guarded-byte change).
- [x] 5.2 Scenario → executed-check mapping (below); every row names a check that actually ran.
- [x] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the GameClock scaffold delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — executed at archive stage (see ledger).

### 5.2 Scenario → executed-check mapping

Rows 1–15 are the scenarios of the `godot-game-clock` delta; rows 16–17 are the
scenarios of the modified `first-render-in-godot` R1. Commands: G = `godot
--headless --path apps/client-godot -s res://tests/<suite>.gd` (game clock with
the dead-endpoint argument), V = `verify.ps1`, VB = `verify-boot.ps1`.

| # | Scenario | Executed check | Run |
|---|---|---|---|
| 1 | Start without an implicit anchor | `test_game_clock` `_check_no_implicit_anchor`: unanchored, running, zero epoch, startup counters zero | G |
| 2 | Anchor once to the response epoch | `_check_anchor_once`: `{ok}`, committed `server_time`, elapsed base zero, same-frame epoch exact, one `clock_anchored(ts)`, no tick | G |
| 3 | Reject an invalid anchor | `_check_reject_anchor_while_unanchored` + `_check_reject_anchor_while_anchored`: zero/negative/second anchors fail with named errors, state unchanged, silent | G |
| 4 | Pause freezes time and resume continues it | `_check_pause_resume`: pause-state transitions `[true,false]` once each, five paused frames with frozen elapsed/epoch and zero ticks, growth after resume | G |
| 5 | Advance exactly while paused, fail closed otherwise | `_check_advance`: `+1000 ms` / `+1 s` exact with one payload-equal tick; zero/negative/while-running rejected, state unchanged, silent | G |
| 6 | Clear back to unanchored | `_check_clear`: unanchored, zero epoch/elapsed, one `clock_cleared`, repeated clear silent | G |
| 7 | Anchored clock at ready | `_check_boot_integration` attempt 1 (anchored to fixture epoch, bounded range, one notification) and `test_boot_scene` `_assert_ready` clock block (`checks=32`) | G, VB |
| 8 | No anchor after a failed boot | `test_boot_scene` `_assert_no_anchor_after_failure` in `unreachable` (`checks=19`, VB step 6) and `api-error` (`checks=18`, VB step 7 live) | G, VB |
| 9 | Replace the previous anchor on a new attempt | `_check_boot_integration` attempt 2: entry clear notified once, never re-anchored, unanchored with zero epoch after the failure | G |
| 10 | Notify every advance | emission-time verdicts over every tick (`_tick_regressions == 0`, `_payload_mismatches == 0`), the growth-window frame sampler (`frame_mismatches == 0`: exactly one notification per crossing frame), and the frame-driven payload-equals-elapsed check | G |
| 11 | Notify transitions once | `_check_transition_notifications` (1 anchored, 1 cleared, `[true,false,true,false]`) plus inline no-op silence for repeated pause/resume/clear and rejected requests | G |
| 12 | Scope enforces the new boundary | `test_project_scope`: 39-file inventory, exactly four autoloads, 16 forbidden tokens over 30 sources, two scenes (`checks=613`) | V |
| 13 | Keep prior verifications green | `verify.ps1` + `verify-boot.ps1` exit 0; guard pre=post `6978b959…`; committed first-render report/PNG byte-identical (verify assertions) | V, VB |
| 14 | Record the executed commands | `AGENTS.md` six-suite prose; `README.md` suite purpose, invocation, counts 110 / 613 / 48 | — (docs review) |
| 15 | Record the milestone progress | roadmap `Project Status` ledger entry (task 5.3, archive stage) | — (ledger) |
| 16 | (R1) Boot with the pinned engine | `test_project_scope` engine-4.7.2 checks + `test_boot_scene` ready marker engine assertion + VB main-scene live phase | V, VB |
| 17 | (R1) Remain within the verification scope | `test_project_scope` (`checks=613`): allow-list, four autoloads, no camera/UI/legacy tokens, first-render scene and tests intact | V |

Disclosures: the `gameclock_missing` and `gameclock_anchor` boot failure branches
are specified fail-closed paths that no executed phase reaches (their inputs are
rejected earlier by construction); they are unit-covered by direct `anchor(0)` /
`anchor(-5)` / second-anchor rejections in rows 3. The `session_activate` branch
runs after the anchor point but is unreachable because a parsed `ok=true`
bootstrap always satisfies `Session.activate`'s validations — same epistemic
status as the prior change's accepted branch. The "no wall-clock, persistence,
content loading" requirement clauses of *Clock scaffold* have no scenario of
their own and are covered by the direct source scan in row 1's suite (added
after the independent verifier flagged the original task-1.1 claim as pointing
at a check that did not exist).

### Verification record (2026-09-27)

Independent verifier subagent verdict: **PASS, 0 CRITICAL, 2 WARNINGs, 6 NOTEs**.

- W1 (task 1.1 claimed a scope-scan check for wall-clock reads that did not
  exist; requirement clauses unverified) → repaired: direct source-contract scan
  (8 tokens) added to `test_game_clock.gd`, task 1.1 reworded to name it. Suite
  re-run green (`checks=110`).
- W2 (frame-tick payload equality and the per-frame rate asserted only by
  construction) → repaired: emission-time payload verdict
  (`_payload_mismatches`), the growth-window per-frame sampler
  (`frame_mismatches`), and the sync-point payload check. The verifier's
  naive "tick count == millisecond delta" rate formulation was disproven by
  the first run (a frame crossing 6 ms emits one tick, per the contract) and
  replaced by the correct per-crossing-frame assertion.
- N1/N2/N3/N6 → repaired: `boot.gd` comment now names the reachable failure
  paths, `design.md` D9 risk/rationale sentences now state that dropping the
  token stops scanning it and the inventory bounds references, the fixture
  comment now matches the exact-comparison usage, `AGENTS.md` re-wrapped.
- N4 (spec-boundary audit) → clean: only `first-render-in-godot` R1 needed the
  MODIFIED delta; no other living spec is stale. N5 (pending records/ledger) →
  discharged by this file and the archive-stage ledger entry.
