# Tasks

## 1. Typed static `UnitDefinition` model

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_definition.gd`: a read-only typed model parsed from one committed registry entry, in the five named field groups of design D3 (identity/presentation, footprint and placement, statistics, economy, training and upgrade), with the embedded-JSON `costs` and `properties` bags parsed and the cost vocabulary matching the delivered endpoints' mapping (D4), the two partially-absent fields and the three nullable fields recorded as **absent** rather than zero (D4), `legacy_id` preserved verbatim as a string (D5), no field that could carry player state (D2), and no helper computing behaviour from a parsed statistic (D3) — verify: a new `test_unit_definitions.gd` covers every group, both embedded-JSON bags, every malformed-field refusal naming the definition and field, absent-vs-zero, and the no-player-state field inventory, all passing headless with no content file modified.
- [x] 1.2 Implement `apps/client-godot/scripts/units/unit_catalog.gd`: registry-backed lookup by legacy ID, `has`/`count`/all-IDs, the documented raw-entry accessor for committed fields the typed model does not parse (D3), and the fail-closed unloaded/absent-`units`-domain path (D1) — verify: the suite covers a resolving lookup, an unknown legacy ID, the wrong-form legacy ID (D5), the unloaded and absent-domain paths, and the raw accessor returning a field outside the parsed groups.

## 2. Boundary and linkage assertions

- [x] 2.1 Assert the static/instance boundary in the suite: no `UnitInstance` type, save shape, instance-parsing, garrison, or production-queue surface exists in the client, and no compatibility route, response field, or error code was added (D2, D6) — verify: the boundary assertions run headless and the compatibility suite is green **unchanged**.
- [x] 2.2 Cover the committed asset linkage through `ContentRegistry.resolve_asset`: a definition reports **whether** its committed `img_name` reference resolves and the recorded status, claiming nothing about rendering, animation, or visual fidelity (D7) — verify: the suite asserts at least one resolving reference with its recorded status and that the model's own documentation states the no-rendering claim.

## 3. Battery registration and evidence

- [x] 3.1 Update the project-scope allow-list for the new scripts, suite, and evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.
- [x] 3.2 Register `test_unit_definitions` in the hermetic suite list in `apps/client-godot/verify-boot.ps1` (no new live phase: this line has no endpoint and mutates nothing) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new suite in its documented count.
- [x] 3.3 Write the deterministic `unit-definitions-report-v1` report into `apps/client-godot/evidence/unit-definitions/` recording the committed counts, the legacy-ID range and distinctness, the content fingerprint and manifest digest, the per-group parsed-field inventory, the 300/429 coverage of each partially-absent field, the raw-entry escape hatch, the asset-linkage statuses, the static/instance boundary, and every non-claim from the delta — verify: the report is committed, lists every required field, and a rerun reproduces its committed bytes exactly.

## 4. Documentation and integration review

- [x] 4.1 Document the slice in `apps/client-godot/README.md` (the model, the catalog, the boundary, the evidence path, and the claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no unit is rendered, animated, or played" limit is stated wherever the slice is described.
- [x] 4.2 Run the full preservation battery in the final state and record the residual gaps (no unit instance, queue, production, collection, movement, animation, or behaviour; no gameplay semantics on any parsed statistic; the cost vocabulary inherited from the delivered endpoints rather than observed in the client; asset linkage reported and nothing more; the corpus's lack of unit placements so no instance behaviour is evidenced; no windowed capture claimed) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` is green **unchanged** at its prior test count, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` reports identical digests before and after, and `git diff` shows no content-package or legacy byte changed.
- [x] 4.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D8, and `specs/`, run `openspec validate unit-definitions --strict` and both batteries once more, and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

The implementation was delegated to a worker; the root re-read the worker's diff, **independently
re-verified every claim it made**, corrected the artifacts where the worker was right and I was
wrong, and re-ran every check in the final state.

### What the Apply stage disproved in this change's own planning artifacts

Both errors were mine, in the proposal and design, and both were found by executing against the
committed package rather than reading it. They are recorded in `design.md` (Context, D1, D4) and
in the spec rather than quietly worked around.

1. **`costs` and `properties` are committed objects, not embedded-JSON strings.** Content rule
   R2 coerces them at build time; the committed schema declares both `"type": "object"` with
   `costs` restricting `propertyNames` to `o/s/g/w/c`. Root-verified: `{'dict': 429}` for both,
   against 429 rows. The committed object form is the required input; a JSON string is accepted
   only as the same transport tolerance the delivered `placement_catalog.gd` applies to the
   served bootstrap payload, and both fail closed identically.
2. **The field count is 58, not 53** (56 on every row, 2 optional on 300 each). Root-verified
   three ways: the data union is 58, `unit.schema.json` declares exactly 58 properties and 56
   required, and data and schema agree with no field in one and absent from the other.

### A design gap the root closed rather than shipped

The worker reached into `registry.get("_domains")` to enumerate the domain, having correctly
found that `ContentRegistry` exposes no public id enumeration. The alternative was re-reading
`units.json` behind the registry's back, which would bypass the byte-count and digest
verification that is the registry's entire purpose. The root rejected both and instead added a
small **public `ContentRegistry.legacy_ids(domain)`** accessor over the index the registry built
during its verified load, with a `godot-content-registry` spec delta so it is a specified
capability rather than an undocumented escape hatch. It reports the **committed order, not a
collation** of the digit strings — pinned by a discriminating assertion, since `units`' committed
first id is `923` while a lexicographic sort of the same ids would begin `1001`. This is the
fourth time a design premise in this project was narrowed during Apply rather than implemented
as designed.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| Static unit definitions; legacy ID verbatim and unique | `unit_definition.gd` (typed, read-only, five groups) + `unit_catalog.gd`; `test_unit_definitions.gd` **204 checks** — 429 distinct string ids over `923`..`1431`, each lookup returning its own definition, a wrong-form id failing closed, and the unloaded / absent-domain / zero-entry / count-disagreement paths all failing closed |
| No player state in a definition; enumeration crosses the verification gate | asserted structurally through `definition.get_property_list()` against a named `PLAYER_STATE_NAMES` list; enumeration goes through the public accessor, cross-checked against `count()` |
| Typed fields, no gameplay semantics, raw-entry escape hatch | each parsed field compared against the committed row verbatim; the absence of any behaviour-computing helper asserted (no `damage()`, `can_defend()`, `speed()`, `lifetime()`, `next_attack()`); `raw_entry()` returns a field outside the five groups |
| Fail-closed parsing; committed object bags; absent-is-not-zero | one refusal per numeric/string-parsed field class, each naming the definition and field; both bags parsed from the committed object form with the `g/c/w/o/s` vocabulary **aliased** from `placement_catalog.gd`; the four conditionally-present / nullable fields carry presence flags and the report records `committed_zero_present: 0` for each |
| Content, not a server operation | no compat route, response field, error code, or persistence change; the compat suite is green **unchanged** at `Ran 1109 tests ... OK` |
| Committed asset linkage only | `sprite_linkage()` reports resolution and the recorded status; 424/429 whole references resolve (419 `extracted`, 1 `converted`, 1 `missing_source`, 3 `pending`) and the 5 comma-joined rows resolve per part (446/446) |
| Evidence and claim limits | `evidence/unit-definitions/report.json`, schema `unit-definitions-report-v1`, digest `f997eb2d...66d5`, byte-identical across three consecutive runs; all eight required non-claims present and audited by reading the committed bytes, not the generator |
| Containment and preservation | see below |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `test_unit_definitions.gd` | exit 0, **204 checks** (207 with `--report`) |
| `test_content_registry.gd` | exit 0, **87 checks** (was 52; +35 for the enumeration) |
| `test_project_scope.gd` | exit 0, **1339 checks** |
| `test_scene_build.gd` | exit 0, **36 checks** |
| `verify.ps1` | exit **0** — content package, both conversion packages, and all four registry manifests byte-unchanged |
| `verify-boot.ps1` | exit **0** — 28 hermetic suites, 13 live phases; guard digests identical pre/post (`6978b959...ff348`); port 5056 released; no working-tree `saves/` |
| `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` | `Ran 1109 tests ... OK`, exit 0 — **unchanged**, as claimed |
| `python -B packages/game-content/tools/validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `python -B tools/hash-manifest/hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate --all --strict` | **50 passed, 0 failed** after the sync |
| report determinism | byte-identical across three consecutive runs |

`git status` showed no content-package, fixture, save, config, village, conversion-package, or
legacy-source byte changed. No Flash, Ruffle, ActionScript, or browser executed; no non-loopback
traffic.

### Accepted deviations

- **The two artifact corrections above**, applied to `proposal.md`, `design.md`, and the spec.
- **The public registry accessor** was added rather than the private-field read shipped; this
  widened the change to a third capability (`godot-content-registry`) but is the smaller coherent
  change in the long run.
- **The report records three facts the artifacts did not anticipate**, all corrections rather
  than concessions: `img_name` is a comma-joined list on 5 of 429 rows (reporting only the whole
  string would have misrepresented them as unresolvable when every part resolves); the committed
  `name` values are not unique (six shared by two rows each), so `find_by_name()` returns every
  match; and `best_against` is a string on all 429 rows while the schema also permits an integer
  code, so the field is a variant.
- **No live phase and no windowed capture.** The line has no endpoint and mutates nothing, and
  it changes nothing visual, so a capture would assert nothing.

### Residual gaps (recorded, non-blocking)

- No pixel-parity oracle exists, and the committed definitions say nothing about what the Flash
  client read.
- The five named field groups and the choice of which committed fields to type are a
  **presentation** of the committed row, not a claim about any legacy consumer.
- The committed `-1` in the upgrade chain and every key in the `properties` flag bag are
  reproduced verbatim; the schema's "-1 and 0 mean none" note is **not** interpreted and no
  property key is read as a capability.
- The committed corpus has **no unit placements at all**, so nothing in this line speaks for a
  placed unit. Every behaviour-bearing M8 line inherits that limitation and must either find
  corpus coverage or record the gap rather than fabricate a player state.
