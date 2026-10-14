# Tasks

## 1. Server v1 domain

- [ ] 1.1 Add the reward refusal codes to `server_v1_refusals.py`: structural input (a client-sent next id, item id, cell, player, or map index), unknown action, unaddressable or unreadable cursor, unreadable state, and post-condition violation. One code-to-status mapping, no route-local answer.
- [ ] 1.2 Add `server_v1_reward.py` with a closed two-value action vocabulary and the cursor read, the successor derivation (`stored + 1`, then the preserved literal clamp), and the instant stamp.
- [ ] 1.3 Implement the grant refusals so each resolves **before** the cursor advances, and prove the refusal leaves the whole document byte-identical.
- [ ] 1.4 Report the bound, the rejected schedule-length derivation, and the addressability gap. Do not enforce any of the three.
- [ ] 1.5 Add the two-part post-execution proof: the recorded cursor advanced to its derived successor, **and** every stored resource, storage entry, and bought-unit entry is byte-identical.
- [ ] 1.6 Register `POST /v1/reward` on the v1 app. Record its position and assert it, so no future route insertion silently re-breaks a suite that slices handler source between route markers.
- [ ] 1.7 Update the refusal-count pin and its guard-on-the-guard in the same commit, taking the table from 20 to its new size.

## 2. Client

- [ ] 2.1 Add the typed reward result module and the `GameApi` forwarder in the shape of the existing ones.
- [ ] 2.2 Refuse every unsupported intent client-locally with `unsupported_by_server_v1`, through each typed result's own `_failure` factory, so no unsupported intent reaches the transport.
- [ ] 2.3 Add the hermetic suite: the closed action set, the derivation from a stored cursor, each refusal, the bound reporting, and the two-part proof.
- [ ] 2.4 Add the anti-invention guards. Derivation lives in exactly one place — pinned as an inventory, not a convention — and the module declares no payout, cost, eligibility, or cooldown helper. Prove each guard by injection and record the measured failure counts.
- [ ] 2.5 Write the deterministic evidence report from the suite's own live model, and verify it is byte-identical across three consecutive runs.

## 3. Verification

- [ ] 3.1 Run `apps/server-v1` unittest discovery and record the observed count against the 519 baseline.
- [ ] 3.2 Run the Compatibility API suite and record the count; confirm `git diff --name-only -- apps/compat-api` returns **no path**.
- [ ] 3.3 Run `verify.ps1` and `verify-boot.ps1`, both to exit 0.
- [ ] 3.4 Grep every referenced log for `SCRIPT ERROR`, `^ERROR:`, and `[test] FAIL`. A clean zero over an accumulating directory is not evidence about the current run — count only this run's own logs.
- [ ] 3.5 Run `openspec validate --all --strict` and the preservation manifest, and record both.
- [ ] 3.6 Run the live phase and confirm a disposable corpus save mutated, that the port is released, that the corpus is removed, and that no working-tree `saves/` remains.
- [ ] 3.7 Amend the two client-side count pins together (hermetic and live) and re-run the authoritative instrument that holds them.

## 4. Close-out

- [ ] 4.1 Re-measure every inherited M13 figure at the final state rather than restating it: named branches, dispatched and undispatched, v1 routes, authoritative branches, authoritative and non-authoritative v0 routes.
- [ ] 4.2 Record every figure of mine that measurement contradicts, as a correction rather than a quiet edit.
- [ ] 4.3 Write the line's claim limits: no payout, no eligibility, no gate, the divergence, the unaddressable stored cursors the corpus actually carries, and no claim about what the Flash client sent.