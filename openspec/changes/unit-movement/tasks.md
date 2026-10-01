# Tasks

## 1. Placement projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_movement.gd`: a typed read-only placement projection for a unit row, carrying the **committed** cell coordinates, orientation, footprint (`width`/`height`), `elevation`, and `velocity`, each reported **verbatim**, with no value derived from another (D1) — verify: `test_unit_movement.gd` covers every field verbatim, asserts that no coordinate comes from a velocity, no offset from a footprint, no position from an elevation, and no intermediate position between instants.
- [x] 1.2 Implement the **fail-closed** path: a row whose committed coordinates are absent or malformed is reported as **unresolvable with its recorded state intact**, never defaulted to the origin — verify: the suite covers an absent coordinate, a malformed coordinate, and a non-integer coordinate, each refusing rather than defaulting.

## 2. Content-only reporting and the movement-command inventory

- [x] 2.1 Report the committed `velocity`, `width`, `height`, and `elevation` as **content only**, with the **zero-consumer** fact stated in the module's own documentation and the committed distributions recorded (D2) — verify: the suite asserts the values are reported, that the zero-consumer statement is present, and that the recorded distributions match the committed package.
- [x] 2.2 Implement the **movement-command inventory** (D3) naming `move`, `orient`, `pop_unit`, and `fast_forward`, and for each recording what it **checks and what it does not**, including that `move` is **type-agnostic**, that its `frame` and `string` arguments are read but unused, that it **already ships** as `godot-building-move`, that `orient` is a plain orientation write, that `pop_unit` overwrites the row's item id, and that **no unit-specific movement command exists** — verify: the suite covers each recorded command with its checks and non-checks and asserts none is implemented here.
- [x] 2.3 Record the **client-writable instant**: that a client-supplied time shift rewrites every row's recorded instant **and** its queue start instant, and that the instant is therefore treated as an **opaque recorded value** with no elapsed, remaining, or readiness computation (D4) — verify: the suite asserts the instant is opaque and that no readiness or elapsed helper exists.
- [x] 2.4 Assert the **anti-invention guard** (D4): the suite fails if any travel-time, path, terrain, elevation-interaction, occupancy, bounds, readiness, interpolation, or animation helper is added to the module — verify: inject one such helper, observe the failure, restore the file, and confirm the suite passes again; record the result in the review.

## 3. Boundary, battery registration, and evidence

- [x] 3.1 Assert the **no-endpoint boundary**: no compatibility route, response field, or error code was added, no move intent is issued, and `apps/compat-api/**` is untouched — verify: the boundary assertions run headless and the compatibility suite is green **unchanged**.
- [x] 3.2 Update the project-scope allow-list for the new script, suite, and evidence files; register `test_unit_movement` in the hermetic list (**33** hermetic) and update the header sentence listing the hermetic suites (no new live phase) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new suite in its documented count.
- [x] 3.3 Write the deterministic `unit-movement-report-v1` report into `apps/client-godot/evidence/unit-movement/` (written by the suite itself via `--report=<path>`, bare `--report` defaulting there) recording the placement fields verbatim, the committed velocity and footprint distributions with their zero-consumer statements, the movement-command inventory with each command's checks and non-checks, the client-writable instant recording, the corpus measurement, the M6 tile-geometry gap, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.

## 4. Documentation and integration review

- [x] 4.1 Document the slice in `apps/client-godot/README.md` and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no movement rule exists" limit is stated wherever the slice is described.
- [x] 4.2 Run the full preservation battery in the final state and record the residual gaps (no velocity-based travel time, path, terrain or elevation interaction, occupancy, bounds, readiness, interpolation, or animation; the committed movement fields read by no legacy branch; no unit-specific movement command and none invented; no unit placed or moved; the corpus holds no unit row; no executed-legacy fixture and the reason being the absence of behaviour rather than only the corpus; no pixel parity and the M6 tile-geometry gap remaining a gap) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` is green **unchanged** at `Ran 1352 tests ... OK`, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package or legacy byte changed.
- [x] 4.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D7, `specs/`, and `docs/legacy-unit-movement.md`; run `openspec validate unit-movement --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.
"""
---

## Review record (task 4.3)

Every requirement in `specs/godot-unit-movement/spec.md` maps to a check in
`apps/client-godot/tests/test_unit_movement.gd` (245 checks) or to a recorded claim
limit carried in `apps/client-godot/evidence/unit-movement/report.json` (digest
`785B0482\u20269165E`, byte-identical across three runs).

| Requirement | Evidence |
| --- | --- |
| A unit row's placement is projected, never derived | `_check_projection` \u2014 the eight fields reported verbatim; `no_derivation` and `cell_refusal` carried on every result; the six no-derivation flags asserted false; `readiness` reported as `READINESS_UNKNOWN`; `move`'s untransformed client write measured in `_check_legacy` |
| Committed movement fields are content, not rules | `_check_content` \u2014 all four reported verbatim against the registry; `consumer_count` 0; every per-field and sibling count measured 0 across the seven modules; the distributions asserted; `TILE_GEOMETRY_GAP` present; `ZERO_CONSUMER_PRECEDENTS` each carrying its fact |
| The movement-command inventory classifies each command | `_check_inventory` \u2014 all four commands with `checks` and `does_not_check`; `TYPE_AGNOSTIC`; `move_already_delivered_as`; `pop_unit`'s item-id overwrite; the **measured** five slot 0\u20132 assignments, 63 named branches, and exactly two coordinate writers; the token-matched movement branches |
| The row instant is client-writable, and no readiness is derived | `_check_instant` \u2014 `client_writable`; `treated_as` opaque; `derived_from_it` false; and the branch **body** measured to rewrite `data[3]`, `data[6]["ts"]`, and exactly eleven further instants |
| Movement is content, not a server operation | `_check_boundary` \u2014 `no_endpoint_record()` keys asserted; the client-source scan finds no `move_unit_town`, `/v0/move_unit`, `travel_time`, or `unit_path` outside the module; `apps/compat-api/**` untouched and the suite green unchanged at `Ran 1352 tests ... OK` |
| No executed-legacy movement fixture is claimed | `fixture_record()` \u2014 `captured` false; `reason_kind` states the ABSENCE of behaviour is the reason, which is stronger than a corpus limitation; `corpus_distinction` keeps the corpus as a second reason; `existing_move_fixture` names `godot-building-move`; no save, corpus, or fixture byte changed |
| Unit-movement evidence and claim limits | `unit-movement-report-v1` \u2014 all 22 top-level keys present, 18 `ABSENT_HELPERS`, 12 `NON_CLAIMS`, the tile-geometry gap, and both corrections |

### Two defects found and corrected during the line

1. **The investigation's own slot-0\u20132 write count was six, not five.** `engine.py:62` is
   `if item[0] == item_id:` \u2014 a **comparison** inside `engine.pop_unit`'s garrison scan, not
   an assignment. Measured with a pattern that excludes `==`, the count is **five**. The
   conclusion was unaffected and independently re-measured: exactly two branches write
   coordinates. `docs/legacy-unit-movement.md` carries the correction, and
   `INVESTIGATION_CORRECTIONS` records it in the report.

2. **The suite's own `ft_flying` measurement was 137, not 135.** The normalized package
   stores the `properties` flags as **strings** (`"1"` / `"0"`) and leaves most **absent**,
   so `int(props.get("ft_flying", 0) or 0) > 0` counts a non-empty String as truthy,
   collapses the committed `"0"` to `true`, and `int(true)` is 1. Ids 1357 and 1369 are the
   two the package marks `"0"`. Verified by probe that `int("0")` is 0, so **135** is
   correct; the flags are now read through one named `_committed_flag` helper, the encoding
   is recorded in the report under `committed_flag_encoding`, and the figure is asserted so
   it cannot drift again.

### Guard tested, not trusted (task 2.4)

Injecting one deliberately invented

```gdscript
static func travel_time(from_cell: Variant, to_cell: Variant, velocity: Variant) -> float:
```

produced **two independent failures** \u2014 the pinned-inventory check
(`expected [], got ["travel_time"]`) and the per-helper absence check \u2014 and restoring the
file returned the suite to its passing state and **exit 0**. The evidence report's digest was
unchanged across the injection, so the guard never touched the committed evidence.

### Verification actually run (2026-10-01)

| Check | Result |
| --- | --- |
| `test_unit_movement.gd` | 245 checks, exit 0 (246 with `--report`) |
| `test_unit_movement.gd -- --report` \u00d7 3 | digest `785B0482\u20269165E` identical, 42,510 bytes |
| guard injection + restore | 2 failures injected \u2192 restored to a passing state |
| `verify.ps1` | exit 0 |
| `verify-boot.ps1` | exit 0 \u2014 **33 hermetic suites**, 15 live phases, no new live phase |
| compat unittest discovery | `Ran 1352 tests ... OK`, exit 0, **unchanged** |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate unit-movement --strict` | valid |
| `git status` on content/legacy/compat paths | **no byte changed** |

*One recorded flake:* the first `verify-boot.ps1` run reported the compat discovery exiting 1
while the suite itself reported `OK`; standalone it passed with `Ran 1352 tests ... OK`, exit
0, and the battery passed on rerun. No `apps/compat-api/**` byte changed. Consistent with the
recorded guard-narrowing follow-up.
