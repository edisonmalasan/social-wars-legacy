# Tasks

## 1. Typed `UnitInstance` over a legacy map row

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_instance.gd`: a read-only instance that **wraps** one map row plus its resolved `UnitDefinition` (D1), exposing the row's item id, cell, instant, orientation, and player team verbatim and its `attr` bag, reading identity from the definition rather than restating it, and **rejecting** a row whose committed `type` is not a unit with an error naming the key and the committed type (D1/D3) — verify: a new `test_unit_instances.gd` covers a well-formed unit row, every malformed slot, and each non-unit committed `type` failing closed with no coercion.
- [x] 1.2 Implement the **nested garrison** parse in the same module (D2): the fifth slot is a list of rows, each parsed as an instance in its own right, an empty list reading as an empty garrison distinct from a missing or malformed slot, and nesting bounded by a named `MAX_GARRISON_DEPTH` that **fails closed** naming the key and the depth rather than truncating — verify: the suite covers a one-level and a two-level garrison, an empty garrison, a missing slot, a malformed nested row, and a crafted over-deep row set refused at the bound.

## 2. Projection, capacity refusal, and recorded contracts

- [x] 2.1 Implement `apps/client-godot/scripts/units/unit_instance_projection.gd`: classify rows by **committed `type`** (never the normalized `kind`, D3), resolve each unit row's definition through `ContentRegistry`, project the garrison recursively, and report every non-unit row as a building without coercion — verify: the suite covers a mixed row set, asserts `kind` does not change any classification, and asserts the projection fails closed on an unloaded registry or a missing `units`/`buildings` domain.
- [x] 2.2 Record the garrison-container and dead-unit-counter contracts and the reserved-queue-key inventory (D5/D6/D7): a typed `RESERVED_ATTR_KEYS` naming `nu` (count), `ts` (start instant), and `ui` (optional queued unit id) with the three-key teardown rule; the dead-unit pool read as an integer map keyed by item id with **no** row, corpse, or predicate derived; and **no** capacity limit applied against `unit_capacity` (D5) — verify: the suite asserts no queue mutation helper exists, that an over-capacity garrison is neither refused nor truncated, that a resurrection property is never evaluated, and that the reserved keys' committed values are readable as content.
- [x] 2.3 Assert the **zero-instance result against the committed corpus and the no-fabrication rule** (D8): the projection over the committed fresh-player corpus returns zero instances, all 40 rows classify as buildings, no row carries a non-empty garrison, and no row carries a reserved queue key; and instances are demonstrated over a **crafted in-memory row set** labelled as test input, with no save, corpus, or fixture written — verify: the suite asserts all of it, and `git status` shows no `tests/saves/`, `tests/fixtures/`, or working-tree `saves/` change after the full run.

## 3. Battery registration and evidence

- [x] 3.1 Update the project-scope allow-list for the two new scripts, the suite, and the evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.
- [x] 3.2 Register `test_unit_instances` in the hermetic suite list in `apps/client-godot/verify-boot.ps1` (no new live phase: no endpoint, nothing mutates) and update the header sentence that lists the hermetic suites — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new suite in its documented count (29).
- [x] 3.3 Write the deterministic `unit-instances-report-v1` report into `apps/client-godot/evidence/unit-instances/` (written by the suite itself via `--report=<path>`, so its tables derive from the live model and cannot drift) recording the row contract with its source lines, the corpus measurements, the zero-instance result, the garrison container contract, the dead-counter contract, the reserved-key inventory, the committed `unit_capacity` distribution with its no-rule statement, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.

## 4. Documentation and integration review

- [x] 4.1 Document the slice in `apps/client-godot/README.md` (the row contract, the nested garrison, the classification rule, the capacity refusal, the recorded contracts, the evidence path, and the claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no executed-legacy fixture, none fabricated" limit is stated wherever the slice is described.
- [x] 4.2 Run the full preservation battery in the final state and record the residual gaps (no executed-legacy fixture and none fabricated; no acquisition, queueing, training, capacity, death, resurrection, movement, or behaviour; the first executed-legacy unit fixture belongs to the production line via the Command Center at map key 1; `kind` is a normalization artifact and classification uses committed `type`; no pixel parity) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` is green **unchanged** at `Ran 1109 tests ... OK`, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package or legacy byte changed.
- [x] 4.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D9, `specs/`, and `docs/legacy-unit-instances.md`; run `openspec validate unit-instances --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

The implementation was delegated to a worker; the root re-read the worker's diff,
**independently re-verified every claim it made**, corrected the delivered suite the
worker's findings exposed, corrected three factual errors of its own, and re-ran every
check in the final state.

### The blocker the worker found, and the root fixed

`verify-boot.ps1` exited 1 with three failing assertions in the **already-delivered**
`tests/test_unit_definitions.gd::_check_boundary`. The delivered suite asserted that
**no client source anywhere in the client** declared a unit instance — a repository-wide
absence. That was a **stronger claim than its own requirement made** (the requirement
constrains *that capability's* surface, not the repository forever), and it was falsified
by the very next line, which is chartered to exist.

The root replaced the absence assertion with a **boundary assertion that cannot rot**:

- the two modules that capability delivers (`unit_definition.gd`, `unit_catalog.gd`)
  declare no instance type and no garrison, production-queue, or train-queue state —
  permanently true;
- where an instance type **does** exist, it is a **distinct script**, it is not
  `UnitDefinition`, and every definition it holds still exposes the same field inventory
  with no field that could hold player state — so a future instance type cannot satisfy
  distinctness while quietly widening the definition it holds.

`test_unit_definitions.gd` goes from **204 to 213 checks** and passes. This is the second
time in this project that a delivered suite's over-claim was corrected rather than
worked around; the first was the `building-resources` HUD key.

### Three factual errors of mine, corrected

All three were found by the worker and **independently re-verified by the root before
accepting** — the worker was right on every one, and the root was wrong:

1. **`unit_capacity` is non-zero on 5 of 429 units** (1013 Truck 4, 1018 Zodiac 4,
   1019 Ship 6, 1032 Truck 3 6, 1035 Truck II 6), **not 0**. The investigation's
   original probe iterated only buildings for that gate, so the figure was **asserted
   rather than measured**; the stored `config/main.json` agrees with the package.
2. **The garrison-capable placed count is 9 rows across 3 distinct item ids**
   (905x1, 930x6, 931x2), **not 3 rows** — the figure counted distinct ids.
3. Consequently the design's "units carry neither" was wrong on both halves and is
   restated per field.

Corrected in `docs/legacy-unit-instances.md`, `design.md`, `proposal.md`, and the
capability spec. **The capacity decision (D5) is unaffected**: the field has **zero**
occurrences across five legacy modules, so no capacity rule is enforced regardless of its
committed value. This is the third time an investigation figure turned out to be asserted
rather than measured; the record now carries the correction rather than the original.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| Unit instances are rows, not widened definitions | `unit_instance.gd` wraps a row plus its resolved `UnitDefinition`; `test_unit_instances.gd` **437 checks** — a well-formed unit row, every malformed slot, and each non-unit committed `type` rejected with the key and type named, never coerced |
| A garrisoned unit is a row nested in a row | nested parse at one and two levels, an empty garrison distinct from a missing or malformed slot, a malformed nested row refused, and a crafted over-deep row set refused at the named `MAX_GARRISON_DEPTH` |
| Classification uses committed `type`, never `kind` | a mixed row set, an assertion that `kind` changes no classification, and the recorded note that the stored configuration carries no `kind` field at all |
| No enforced garrison capacity | an over-capacity garrison is neither refused nor truncated; the committed distribution (48 of 470 buildings, **5 of 429 units**) is reported with the explicit no-rule statement |
| Queue keys reserved, not implemented | `RESERVED_ATTR_KEYS` names `nu`, `ts`, `ui` with the three-key teardown; the suite asserts **no** queue mutation helper exists and that presence is readable without behaviour |
| A dead unit leaves no instance | the counter is read as an integer map keyed by item id with no row, corpse, or instance derived, and no resurrection predicate is evaluated |
| Zero-instance result asserted, nothing fabricated | the projection over the committed corpus returns **zero**; all 40 rows classify as buildings; no row carries a garrison or a queue key; instances are demonstrated over **crafted in-memory test input** only, and no save, corpus, or fixture is written |
| Read-only state, not a server operation | no compat route, response field, error code, or persistence change; the compat suite is green **unchanged** at `Ran 1109 tests ... OK` |
| Evidence and claim limits | `evidence/unit-instances/report.json`, schema `unit-instances-report-v1`, digest `A02EEDC8...57BBA0`, byte-identical across three runs |
| Containment and preservation | see below |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `test_unit_instances.gd` | exit 0, **437 checks** (440 with `--report`) |
| `test_unit_definitions.gd` | exit 0, **213 checks** (was 204, +9 for the boundary) |
| `test_project_scope.gd` | exit 0, **1390 checks** |
| `test_scene_build.gd` | exit 0, **36 checks** |
| `verify.ps1` | exit **0** — content package, both conversion packages, and all four registry manifests byte-unchanged |
| `verify-boot.ps1` | exit **0** — 29 hermetic suites, 13 live phases; guard digests identical pre/post (`6978b959...ff348`) |
| compat suite | `Ran 1109 tests ... OK`, exit 0 — **unchanged** |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate --all --strict` | **50 passed, 0 failed** at Apply; **51** after the spec sync |
| report determinism | byte-identical across three consecutive runs |

`git status` showed no content-package, fixture, save, config, village, conversion-package,
or legacy-source byte changed. No Flash, Ruffle, ActionScript, or browser executed; no
network was used at all.

### Accepted deviations

- **The delivered `test_unit_definitions` boundary assertion was rewritten** (above),
  which raised its check count and changed its meaning from a repository-wide absence to
  a boundary invariant. The capability's own requirement was **not** changed, because it
  never made the stronger claim.
- **`MAX_GARRISON_DEPTH = 4` is derived**, recorded as such: the artifacts named a bound
  but no value, and the legacy engine nests exactly one level, so 4 is headroom.
- **Both a placed unit row's and a placed building row's fifth slot are parsed
  identically**, because the 48 garrison-capable committed rows are all buildings and none
  trains anything, while a *garrisoned* row is always parsed as a unit instance. Recorded
  as derived.
- **An absent or `null` `deadHeroes` is refused** rather than read as an empty count,
  because `version.py:26-30` writes `null` for a pre-version save, so the case is
  reachable.
- **One classification branch is unreachable against committed content**: no committed row
  has a `type` outside `{u, b}`, so the distribution is asserted instead of the branch
  being exercised, and the report says so.

### Residual gaps (recorded, non-blocking)

- **No executed-legacy fixture, and none fabricated.** The corpus contains no unit row, so
  the projection is demonstrated over crafted in-memory test input rather than over a real
  save. **The first executed-legacy unit fixture belongs to `production` (M8 line 4)**,
  because the Command Center at map key 1 (`training_time` 5, `min_level` 1) is a real
  placed training producer and makes the queue genuinely exercisable.
- **No acquisition is claimed.** No committed unit is store-listed (`in_store` is 0 for all
  429); the only committed unit sources are `offer_packs` (109 refs) and `darts_items`
  (44), which are later-milestone systems.
- **Queues, production, collection, movement, animations, and basic behaviors remain
  undelivered**, each its own later M8 line.
- The `attr` bag is handed out as a deep copy while the row and definition are held by
  reference, so a caller cannot write back into the save through an instance — but a
  caller mutating the copy it was given would diverge silently. The suite asserts the row
  is byte-identical after every read; nothing prevents a future caller from mutating its
  own copy.
- No pixel-parity oracle exists, and nothing here speaks for what the Flash client
  displayed or how a unit was obtained in play.
