# Tasks

## 1. Executed-legacy fixture capture

- [x] 1.1 Confirm the capture harness pattern from `capture_magic_fixture.py`
      (two branches, one corpus, containment digest recorded before and after).
- [x] 1.2 Capture `login_post` then `weekly_reward` with **four or fewer**
      arguments against a committed corpus recording an advanced
      `weeklyRewardIndex` (`Neutral.json` at 3, `Nerri.json` at 2), so the
      recorded successor lands on an **unaddressable** position. Record the exact
      leaf-level diff: the cursor and the stamp, and **nothing else** — which is
      the clean demonstration that the short arm grants nothing.
- [x] 1.3 Capture `weekly_reward` with **five or more** arguments against the same
      corpus, to establish the divergence: a row is placed that the service
      refuses to place. Record the placed-row count before and after.
- [x] 1.4 Capture `win_daily_bonus` against a corpus with a recorded
      `bonusNextId`, including **one probe with a deliberately oversized client
      next id** to establish by execution that the preserved branch moves the
      recorded cursor **backwards** when the client value exceeds the bound. This
      is the sharpest divergence in the line and it must be executed, not argued.
- [x] 1.5 Record, in the fixture README and manifest: the two divergences, the
      unaddressable successor, the fact that **no** stored resource moved across
      every transaction, and that the grant is client-sent so **nothing** is
      established about what was granted.
- [x] 1.6 Add the fixture integrity test, with **LF-normalized** byte counts (the
      CRLF guard defect recorded in PR #280) and **sha256** verification.

## 2. Compatibility service envelope and route

- [x] 2.1 `rewards_envelope.py`: typed `RewardResult` carrying the action, the
      addressed cursor's before/after/change, the derived bounds, the
      reachability sets and their difference **per cursor**, the reported
      schedules, the type letters with the decoder-search result, and the
      preserved-arm report. No field named after a granted or paid reward.
- [x] 2.2 Action set `weekly` → `weekly_reward`, `daily` → `win_daily_bonus`, with
      `ACTION_COMMAND`, `ACTION_ARGUMENT_COUNT`, and an explicit
      **no-addressing-key** mapping (D13) rather than a default, since the quests
      line's largest cross-layer defect was an addressing key assumed universal.
- [x] 2.3 Route `POST /v0/reward`: resolve **all** refusals before the cursor
      write **and before the instant stamp** (D9), then dispatch the unchanged
      legacy branch with the **derived** cursor and a **neutral** vector.
- [x] 2.4 Named refusals, all **409** with an empty payload and no mutation:
      one per grant-shaped argument class (`item`, `item_index`, `cell`, `player`,
      `next_id`, `amount`, `price`), plus `unknown_action` and a structural
      `bad_request`.
- [x] 2.5 A **client-supplied next id is refused, not ignored** (D2). Record the
      ignored-and-derived alternative as rejected in the module docstring, so a
      later reader sees the choice.
- [x] 2.6 Two-part post-execution proof: the addressed cursor moved by exactly the
      derived transition, **and** the four-part grant proof of D6 — no map row, no
      bought-units append, no storage change, and the **complete** stored resource
      set unchanged.
- [x] 2.7 Stamp the preserved instant, report it as volatile, and assert the
      delivered module contains **no** eligibility, cooldown, window, or
      already-claimed helper (D8).
- [x] 2.8 Add the route's unittest module, including containment, refusal,
      no-mutation-on-refusal, and the four-part proof cases.

## 3. Client projection and hermetic suite

- [x] 3.1 A typed read-only projection reporting both cursors, both instants, the
      derived weekly bound **and** the schedule cardinality side by side, the
      reachability difference, the schedules with their consumer counts, the type
      letters undecoded, and the save-only fields — **deriving nothing** from a
      committed value.
- [x] 3.2 The suite **re-derives** the weekly bound and the reachability
      difference from the committed schedule **on every run**, so a legacy edit
      fails the suite rather than silently contradicting it.
- [x] 3.3 The suite **re-measures** the twelve-module consumer census on every run
      and requires the zero-consumer count, printing the subject count **before**
      any absence verdict is believed — the vacuous-census defect class, which has
      recurred three times in this project.
- [x] 3.4 Structural guards (D7): pin the delivered module's whole static-function
      inventory; exact by-name guards for grant, selection, and decoder helpers;
      and a **substring** guard, because a suffixed helper wearing the same name
      otherwise passes the by-name check.
- [x] 3.5 Assert the route's documented refusals are **reachable** through the
      typed client, and record in the suite why the five missing-key refusals of
      the quests line were structurally unreachable there — so this line does not
      repeat that defect class silently.
- [x] 3.6 Register the suite in `verify-boot.ps1` as a hermetic suite and assert
      both battery totals change by exactly one.

## 4. Evidence and verification

- [x] 4.1 Write the deterministic `rewards-report-v1` report from the suite
      itself via `--report=<path>`, so its tables derive from the live model and
      cannot drift from the code they document. Prove byte-identity across three
      consecutive runs.
- [x] 4.2 **Prove each structural guard by injection, and restore a byte-identical
      file after each**: one invented grant helper, one invented
      cursor-to-rung selector, one invented type-letter decoder, one invented
      eligibility helper, and one **suffixed** helper wearing an existing name to
      exercise the substring guard. Record the failure count for each.
- [x] 4.3 Register a `reward-live` phase that drives both actions against a
      disposable corpus and asserts: the typed response, the two-part proof, the
      four-part grant proof, that a refused request left the corpus byte-identical,
      and that a disposable corpus save actually mutated.
- [x] 4.4 Run and record: the hermetic suite; the compat suite; `verify.ps1`;
      `verify-boot.ps1`; `validate_content.py`; `hash_manifest.py verify`;
      `openspec validate --all --strict`; and `git status` over the preservation
      material.
- [x] 4.5 Inspect every battery log for `^ERROR:`, `SCRIPT ERROR`, and
      `[test] FAIL`, and report the count honestly.

## 5. Ownership and boundaries

- [x] 5.1 Grep **role names as well as source identifiers** across `openspec/specs/`
      to confirm no existing capability claims either cursor, either branch, or
      either schedule — the `legacy-m10-death.md` §6.2 and
      `legacy-m10-mission-completion.md` §9.5 defect, which has now failed twice
      because prose specs describe behaviour by role and never by key name.
- [x] 5.2 Confirm and record that `level_ranking_reward` remains owned **as
      normalized content** by `economy-schedules-normalization` and
      `content-validation`, and that this line does **not** claim gameplay
      ownership of it.
- [x] 5.3 Assert the boundary mechanically: the delivered modules name **no**
      identifier after `boughtUnits`, `store`, or `maps[0].items`, whose owners are
      `godot-unit-instances`, `godot-stored-item-placement`, and
      `godot-building-placement` respectively — and where an identifier of that
      shape is unavoidable, that the **owning capability exists**, so the boundary
      is a hand-off and not an orphan.
- [x] 5.4 Assert this capability names **no** identifier after the schedule type
      letters, so the "undecoded" claim is mechanical rather than prose.
- [x] 5.5 Record the open documentation gap left visible: `godot-combat-actions`
      (M10 line 2) still has **no** README section. Do not backfill it inside this
      change.

## Completion record

*(filled in at Apply, with the checks actually run and their observed results —
never with a check that was not run)*

### What the orchestrator re-ran itself, on the merged state

Every row below was executed by the orchestrator on `main` after the Apply PR
merged. Nothing here is quoted from a worker's report.

| check | observed result |
| --- | --- |
| `capture_rewards_fixture.py` | **exit 0**, run twice; containment `18e5e55ba85473bb` **identical before and after** both runs |
| fixture reproducibility analysis | all **129** leaves that change on a re-run classified: **20** reward stamps, **20** row timestamp slots (`/items/<key>/3`), **17** capture times, **8** HTTP `Date` headers, **28** manifest records of a stamp, **10** flat `instant_before` aliases, **26** digests over state containing a stamp. **Zero** other leaves. |
| `test_rewards.gd` (hermetic) | **419 checks** PASS, exit **0** (**417** before the review fixes; **422** with `--report`) |
| `verify-boot.ps1` | exit **0**, `PASS all checks succeeded` — **44 hermetic suites**, every one `exit=0`; **218 assertions**, all ok; **0 failures**; guard digest `6978b959…ff348` **identical before and after** |
| battery log grep | **832** log files, **0** `^ERROR:`, **0** `SCRIPT ERROR`, **0** `[test] FAIL` |
| `verify.ps1` | exit **0**, `PASS all checks succeeded` |
| compat suite | `Ran 2921 tests` … **OK**, exit **0** (2662 baseline **+259** = 134 envelope + 74 endpoint + 51 parity) |
| `validate_content.py` | `"result": "valid"`, exit **0** |
| `hash_manifest.py verify` | **3,258 entries**, 758,423,699 bytes, exit **0** |
| `openspec validate --all --strict` | **65 passed, 0 failed** |
| evidence report determinism | `evidence/rewards/report.json` regenerated **three** consecutive runs **byte-identical**, 45,135 bytes LF, sha256 `A86E3443308F9496B348EE23…`, normalised to CRLF at 46,304 bytes |
| preservation material | `git status` over `command.py`, `engine.py`, `config/`, `villages/`, `tests/saves/`, `packages/`, `tools/`, `tests/fixtures/`, `docs/` — **clean** |

### Reported at Apply and NOT independently re-proven by the orchestrator

Stated so a later reader does not mistake these for orchestrator-verified:

- the **seven server-half structural guards**, each reportedly proven by injection
  with a byte-identical restore. The orchestrator proved **one** guard — the new
  documentation-gap guard added during review — by injection (see below) but did
  not re-inject the other seven.
- per-suite check counts for the **sibling** suites.

### Three defects the review found in this line's own client half

All three are instances of the class this project has already recorded: *a check
that fires on its own prose*. Fixed in `fix/rewards-review-findings` (PR #305,
merged `2b19d73`).

1. **The suite reported a section that does not exist.** `documentation gap:
   godot-combat-actions README section present = true` — but **no
   `godot-combat-actions` heading exists anywhere in the README**. The check was
   `readme.contains("godot-combat-actions")`, and the only occurrence of that
   string in the file is this capability's **own prose recording the gap**, so the
   text documenting the gap satisfied the search for the gap. It was also an
   `info()` line, so it **asserted nothing**, and its own comment stated the
   opposite intent. Now searched as a **heading**, and the gap is **asserted still
   open**. **Proven by injection:** a fake heading produced **1 failure, exit 1**;
   the restore is byte-identical (SHA-256 `9D3767681B52D487…` both sides).
2. **Two prose sites claimed "BOTH derived bounds EXCEED the cardinality."** False
   for the daily cursor, and **the data never said so** — `exceeds_cardinality_by`
   is **0** there. The measured reality is **two different defects** (weekly bound
   5 vs 3 rungs, an exceedance of 2; daily bound 5 vs 5 entries, **no exceedance**,
   a one-based vs zero-based offset). The suite already said so at
   `test_rewards.gd:370` — *a report carrying only the exceedance would hide that
   the daily cursor cannot reach position 0 at all* — so the prose **contradicted
   the test guarding it**.
3. **A census comment contradicted the pins beside it.** Line 105 read *"Measured
   over all 34 walked documents that carry a `privateState`"* while the constants
   below are 34 walked / 33 carrying.

### Two figures re-measured independently

- **The save-document census.** Measured directly: **34** `.json` files across
  `tests/saves`, `villages`, `villages/quest`; **33** carry a `privateState`; the
  one exclusion is `tests/saves/manifest.json`, a corpus manifest rather than a
  save; and **all 33** carry every one of the 7 save-only fields — **zero**
  documents anywhere in the tree miss any of them. The delivered pins were right.
  The investigation's earlier `39/39` was a **different scope** (it counted
  fixture step files), not a contradiction of the load-bearing claim.
- **The bounds.** `exceeds_cardinality_by` is **2** for weekly and **0** for
  daily. The report was always honest; only prose over-claimed.

### One requirement reconciled at Sync, not silently inherited

Requirement 2 originally read *"SHALL report that the derived bound exceeds the
schedule's cardinality and by how much"*, which asserts an exceedance for **both**
cursors and is **false for daily**. The implementation had to contradict its own
contract to stay accurate. **The requirement was corrected, not the code**, and the
correction is recorded in place in this change's spec delta with the reason, the
two-row table, and the note that the suite had already stated why.

### The fixture is re-runnable, and deliberately NOT byte-deterministic

Re-running the capture **rewrites 129 leaves** — and every one is a wall clock or
a digest over state containing one. That is **by design**: both branches stamp the
wall clock, which is the very behaviour the capability specifies, and the manifest
already records `instant_is_volatile: true` and `instant_compared_by: "shape only,
never by value"`. So "re-runnable" means **semantically reproducible**, and
byte-identity was correctly claimed only for the **evidence report**, which was
verified byte-identical across three runs. The orchestrator **restored** the
committed fixture bytes rather than committing timestamp-only churn.

### Task boxes

Ticked on the strength of the **suite passing**, not on a line-by-line reading of
each item. The structural items in group 5 are asserted by the suite itself (the
boundary and type-letter absences are mechanical), and item 5.5 was verified
directly during review — the gap is still open and is now asserted open.
