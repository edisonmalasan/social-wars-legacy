# Tasks

## 1. Executed-legacy fixture capture

- [ ] 1.1 Confirm the capture harness pattern from `capture_magic_fixture.py`
      (two branches, one corpus, containment digest recorded before and after).
- [ ] 1.2 Capture `login_post` then `weekly_reward` with **four or fewer**
      arguments against a committed corpus recording an advanced
      `weeklyRewardIndex` (`Neutral.json` at 3, `Nerri.json` at 2), so the
      recorded successor lands on an **unaddressable** position. Record the exact
      leaf-level diff: the cursor and the stamp, and **nothing else** — which is
      the clean demonstration that the short arm grants nothing.
- [ ] 1.3 Capture `weekly_reward` with **five or more** arguments against the same
      corpus, to establish the divergence: a row is placed that the service
      refuses to place. Record the placed-row count before and after.
- [ ] 1.4 Capture `win_daily_bonus` against a corpus with a recorded
      `bonusNextId`, including **one probe with a deliberately oversized client
      next id** to establish by execution that the preserved branch moves the
      recorded cursor **backwards** when the client value exceeds the bound. This
      is the sharpest divergence in the line and it must be executed, not argued.
- [ ] 1.5 Record, in the fixture README and manifest: the two divergences, the
      unaddressable successor, the fact that **no** stored resource moved across
      every transaction, and that the grant is client-sent so **nothing** is
      established about what was granted.
- [ ] 1.6 Add the fixture integrity test, with **LF-normalized** byte counts (the
      CRLF guard defect recorded in PR #280) and **sha256** verification.

## 2. Compatibility service envelope and route

- [ ] 2.1 `rewards_envelope.py`: typed `RewardResult` carrying the action, the
      addressed cursor's before/after/change, the derived bounds, the
      reachability sets and their difference **per cursor**, the reported
      schedules, the type letters with the decoder-search result, and the
      preserved-arm report. No field named after a granted or paid reward.
- [ ] 2.2 Action set `weekly` → `weekly_reward`, `daily` → `win_daily_bonus`, with
      `ACTION_COMMAND`, `ACTION_ARGUMENT_COUNT`, and an explicit
      **no-addressing-key** mapping (D13) rather than a default, since the quests
      line's largest cross-layer defect was an addressing key assumed universal.
- [ ] 2.3 Route `POST /v0/reward`: resolve **all** refusals before the cursor
      write **and before the instant stamp** (D9), then dispatch the unchanged
      legacy branch with the **derived** cursor and a **neutral** vector.
- [ ] 2.4 Named refusals, all **409** with an empty payload and no mutation:
      one per grant-shaped argument class (`item`, `item_index`, `cell`, `player`,
      `next_id`, `amount`, `price`), plus `unknown_action` and a structural
      `bad_request`.
- [ ] 2.5 A **client-supplied next id is refused, not ignored** (D2). Record the
      ignored-and-derived alternative as rejected in the module docstring, so a
      later reader sees the choice.
- [ ] 2.6 Two-part post-execution proof: the addressed cursor moved by exactly the
      derived transition, **and** the four-part grant proof of D6 — no map row, no
      bought-units append, no storage change, and the **complete** stored resource
      set unchanged.
- [ ] 2.7 Stamp the preserved instant, report it as volatile, and assert the
      delivered module contains **no** eligibility, cooldown, window, or
      already-claimed helper (D8).
- [ ] 2.8 Add the route's unittest module, including containment, refusal,
      no-mutation-on-refusal, and the four-part proof cases.

## 3. Client projection and hermetic suite

- [ ] 3.1 A typed read-only projection reporting both cursors, both instants, the
      derived weekly bound **and** the schedule cardinality side by side, the
      reachability difference, the schedules with their consumer counts, the type
      letters undecoded, and the save-only fields — **deriving nothing** from a
      committed value.
- [ ] 3.2 The suite **re-derives** the weekly bound and the reachability
      difference from the committed schedule **on every run**, so a legacy edit
      fails the suite rather than silently contradicting it.
- [ ] 3.3 The suite **re-measures** the twelve-module consumer census on every run
      and requires the zero-consumer count, printing the subject count **before**
      any absence verdict is believed — the vacuous-census defect class, which has
      recurred three times in this project.
- [ ] 3.4 Structural guards (D7): pin the delivered module's whole static-function
      inventory; exact by-name guards for grant, selection, and decoder helpers;
      and a **substring** guard, because a suffixed helper wearing the same name
      otherwise passes the by-name check.
- [ ] 3.5 Assert the route's documented refusals are **reachable** through the
      typed client, and record in the suite why the five missing-key refusals of
      the quests line were structurally unreachable there — so this line does not
      repeat that defect class silently.
- [ ] 3.6 Register the suite in `verify-boot.ps1` as a hermetic suite and assert
      both battery totals change by exactly one.

## 4. Evidence and verification

- [ ] 4.1 Write the deterministic `rewards-report-v1` report from the suite
      itself via `--report=<path>`, so its tables derive from the live model and
      cannot drift from the code they document. Prove byte-identity across three
      consecutive runs.
- [ ] 4.2 **Prove each structural guard by injection, and restore a byte-identical
      file after each**: one invented grant helper, one invented
      cursor-to-rung selector, one invented type-letter decoder, one invented
      eligibility helper, and one **suffixed** helper wearing an existing name to
      exercise the substring guard. Record the failure count for each.
- [ ] 4.3 Register a `reward-live` phase that drives both actions against a
      disposable corpus and asserts: the typed response, the two-part proof, the
      four-part grant proof, that a refused request left the corpus byte-identical,
      and that a disposable corpus save actually mutated.
- [ ] 4.4 Run and record: the hermetic suite; the compat suite; `verify.ps1`;
      `verify-boot.ps1`; `validate_content.py`; `hash_manifest.py verify`;
      `openspec validate --all --strict`; and `git status` over the preservation
      material.
- [ ] 4.5 Inspect every battery log for `^ERROR:`, `SCRIPT ERROR`, and
      `[test] FAIL`, and report the count honestly.

## 5. Ownership and boundaries

- [ ] 5.1 Grep **role names as well as source identifiers** across `openspec/specs/`
      to confirm no existing capability claims either cursor, either branch, or
      either schedule — the `legacy-m10-death.md` §6.2 and
      `legacy-m10-mission-completion.md` §9.5 defect, which has now failed twice
      because prose specs describe behaviour by role and never by key name.
- [ ] 5.2 Confirm and record that `level_ranking_reward` remains owned **as
      normalized content** by `economy-schedules-normalization` and
      `content-validation`, and that this line does **not** claim gameplay
      ownership of it.
- [ ] 5.3 Assert the boundary mechanically: the delivered modules name **no**
      identifier after `boughtUnits`, `store`, or `maps[0].items`, whose owners are
      `godot-unit-instances`, `godot-stored-item-placement`, and
      `godot-building-placement` respectively — and where an identifier of that
      shape is unavoidable, that the **owning capability exists**, so the boundary
      is a hand-off and not an orphan.
- [ ] 5.4 Assert this capability names **no** identifier after the schedule type
      letters, so the "undecoded" claim is mechanical rather than prose.
- [ ] 5.5 Record the open documentation gap left visible: `godot-combat-actions`
      (M10 line 2) still has **no** README section. Do not backfill it inside this
      change.

## Completion record

*(filled in at Apply, with the checks actually run and their observed results —
never with a check that was not run)*
