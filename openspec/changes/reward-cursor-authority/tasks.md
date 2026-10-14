# Tasks

## 1. Server v1 domain

- [x] 1.1 Add the reward refusal codes to `server_v1_refusals.py`: structural input (a client-sent next id, item id, cell, player, or map index), unknown action, unaddressable or unreadable cursor, unreadable state, and post-condition violation. One code-to-status mapping, no route-local answer.
- [x] 1.2 Add `server_v1_reward.py` with a closed two-value action vocabulary and the cursor read, the successor derivation (`stored + 1`, then the preserved literal clamp), and the instant stamp.
- [x] 1.3 Implement the grant refusals so each resolves **before** the cursor advances, and prove the refusal leaves the whole document byte-identical.
- [x] 1.4 Report the bound, the rejected schedule-length derivation, and the addressability gap. Do not enforce any of the three.
- [x] 1.5 Add the two-part post-execution proof: the recorded cursor advanced to its derived successor, **and** every stored resource, storage entry, and bought-unit entry is byte-identical.
- [x] 1.6 Register `POST /v1/reward` on the v1 app. Record its position and assert it, so no future route insertion silently re-breaks a suite that slices handler source between route markers.
- [x] 1.7 Update the refusal-count pin and its guard-on-the-guard in the same commit, taking the table from 20 to its new size.

## 2. Client

- [x] 2.1 Add the typed reward result module and the `GameApi` forwarder in the shape of the existing ones.
- [x] 2.2 Refuse every unsupported intent client-locally with `unsupported_by_server_v1`, through each typed result's own `_failure` factory, so no unsupported intent reaches the transport.
- [x] 2.3 Add the hermetic suite: the closed action set, the derivation from a stored cursor, each refusal, the bound reporting, and the two-part proof.
- [x] 2.4 Add the anti-invention guards. Derivation lives in exactly one place — pinned as an inventory, not a convention — and the module declares no payout, cost, eligibility, or cooldown helper. Prove each guard by injection and record the measured failure counts.
- [x] 2.5 Write the deterministic evidence report from the suite's own live model, and verify it is byte-identical across three consecutive runs.

## 3. Verification

- [x] 3.1 Run `apps/server-v1` unittest discovery and record the observed count against the 519 baseline.
- [x] 3.2 Run the Compatibility API suite and record the count; confirm `git diff --name-only -- apps/compat-api` returns **no path**.
- [x] 3.3 Run `verify.ps1` and `verify-boot.ps1`, both to exit 0.
- [x] 3.4 Grep every referenced log for `SCRIPT ERROR`, `^ERROR:`, and `[test] FAIL`. A clean zero over an accumulating directory is not evidence about the current run — count only this run's own logs.
- [x] 3.5 Run `openspec validate --all --strict` and the preservation manifest, and record both.
- [x] 3.6 Run the live phase and confirm a disposable corpus save mutated, that the port is released, that the corpus is removed, and that no working-tree `saves/` remains.

- 3.6 is satisfied by the four **existing** v1 live phases, not by one of this
  line's own: by the darts precedent this line delivers **no** reward live
  phase, because a live phase would first have to deliver a client reward
  transport and a client able to fire `next_reward_cursor` is exactly the
  surface this line exists to refuse. All four v1 phases ran and each
  confirmed a disposable corpus save mutated, port 5057 released, the
  corpus removed and no working-tree `saves/` remaining.
- [x] 3.7 Amend the two client-side count pins together (hermetic and live) and re-run the authoritative instrument that holds them.

- 3.7 grew **three** count pins, not the two this task predicted, and the third
  was found only by running the battery: `server_v1_live_phase.py`'s
  `EXPECTED_BANNER_ROUTES` and `KNOWN_ROUTE_PATHS` (4 -> 5 routes). It also
  required a **fourth** amendment that no pin predicted: `test_combat_v1.gd`
  pins the harness tuple's exact spelling, and wrapping it across two lines
  broke that pin because `FileAccess.get_file_as_string` does not normalise
  line endings. The harness is therefore pinned to a single line and both
  sites record the reason.

## 4. Close-out

- [x] 4.1 Re-measure every inherited M13 figure at the final state rather than restating it: named branches, dispatched and undispatched, v1 routes, authoritative branches, authoritative and non-authoritative v0 routes.

- **Re-measured at the final state, not restated:** 63 named legacy branches;
  **39 dispatched / 24 not** by a v0 envelope, found by executing every
  builder over its own closed action vocabulary (**40 validated calls, 0
  refusals**), which reproduces the recorded pair exactly with reward
  added; **5 v1 routes**; **7 v1-authoritative branches** (`collect`,
  `complete_collection`, `buy_magic`, `use_magic`, `end_attack`,
  `win_daily_bonus`, `weekly_reward`) leaving **56 non-authoritative**;
  **24 v0 routes**, of which **7** carry an authoritative branch.
- [x] 4.2 Record every figure of mine that measurement contradicts, as a correction rather than a quiet edit.

- Recorded, not quietly fixed: the harness's `4 -> 5` route amendment; the
  two-line-wrap defect above; a **stale committed evidence report**
  (`evidence/server-v1/report.json` recorded 19 refusal codes and 22
  unsupported intents, both already stale by an earlier line) which
  regeneration corrected to 25 and 19; and a defect in the **typed module
  I authored**, `str(false)` being the five-character truthy string
  `"false"`, which refused every observed success and made the suite's
  85-case fail-closed walk vacuous. Its sixteen-probe injection table was
  therefore measured against a module that refused everything and was
  **withdrawn and re-measured**: fifteen probes, 42 failing checks, with
  the defect re-instated as the anchor probe.
- [x] 4.3 Write the line's claim limits: no payout, no eligibility, no gate, the divergence, the unaddressable stored cursors the corpus actually carries, and no claim about what the Flash client sent.

- Claim limits are carried in the evidence report's own `limits` block and
  in `design.md`; the five `client_dictated_*` refusals resolve from the
  request body alone, so all five are **400** where v0 answers 409 and
  where v1's own `client_dictated_destruction` is 409.