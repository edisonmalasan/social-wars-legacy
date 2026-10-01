# Tasks

## 1. The readiness projection and its explicit refusals

- [x] 1.1 Implement `apps/client-godot/scripts/units/production_flow.gd`: a pure module (no node, request, or clock) that projects that a queue exists and records its start instant, and reports the **commitment that the legacy server cannot say whether it is ready** — offering **no** readiness test, no completion, no remaining time, and no progress ratio (D4) — verify: `test_unit_production.gd` covers presence, an absent queue, a recorded instant, and asserts the **absence** of any `is_complete`, `remaining`, `progress`, or duration helper on the module.
- [x] 1.2 Implement the **row-entry inventory** in the same module (D2): every legacy branch that places a row on the map, each with its item id's source and its classification as **client-supplied**, **already-existing**, or **derived from committed content**, plus the recorded finding that **no** branch derives an id from a completed queue, a duration, or committed production content — verify: the suite covers each inventoried branch by name, its classification, and the closed count against the committed source.
- [x] 1.3 Implement the **`training_time` refusal** (D3) and the **`add_xp_unit` refusal** (D5): the committed duration is reportable as content with the recorded zero-consumer fact, and the recorded `attr["xp"]` is readable as content but never awarded — verify: the suite asserts a duration is never computed from `training_time`, that the zero-consumer statement and the committed distribution are present as content, that no experience is awarded from the recorded value, and that the client-supplied amount is named.

## 2. Boundary and claim assertions

- [x] 2.1 Assert the **production boundary** structurally: no client source creates a unit, runs a completion, awards experience, or derives a duration from the committed training time; and the acquired absence of any production endpoint — verify: the boundary assertions run headless and the compatibility suite is green **unchanged**.
- [x] 2.2 Assert the **acquisition finding**: the two plausible unit sources are recorded as unvalidated client-sent item lists, `package_id` is recorded as read-and-unused, and the committed acquisition tables are recorded as read by **no** legacy branch, with no mechanism implemented — verify: the suite covers each recorded route, asserts nothing enforces or trusts them, and asserts no acquisition request is issued.

## 3. Battery registration and evidence

- [x] 3.1 Update the project-scope allow-list for the new script, suite, and evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.
- [x] 3.2 Register `test_unit_production` in the hermetic suite list in `apps/client-godot/verify-boot.ps1` (no new live phase: no endpoint and nothing mutates) and update the header sentence listing the hermetic suites — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new suite in its documented count (31).
- [x] 3.3 Write the deterministic `unit-production-report-v1` report into `apps/client-godot/evidence/unit-production/` (written by the suite itself via `--report=<path>`, so its tables derive from the live model and cannot drift) recording the row-entry inventory with each item id's source and classification, the committed `training_time` distribution with its zero-consumer statement, the recorded experience-award contract, the acquisition-route findings, the corpus measurement, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.

## 4. Documentation and integration review

- [x] 4.1 Document the slice in `apps/client-godot/README.md` (the refusal surface, the inventory, the evidence path, and the claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no production mechanism exists to reproduce" limit is stated wherever the slice is described.
- [x] 4.2 Run the full preservation battery in the final state and record the residual gaps (no mechanism, completion, readiness, duration, experience award, or acquisition; no executed-legacy fixture because there is no production behaviour to capture; death and resurrection unreachable; production-adjacent collection, movement, animations, and behaviours undelivered; the committed acquisition tables belong to later milestones; no pixel parity) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` is green **unchanged** at `Ran 1257 tests ... OK`, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package or legacy byte changed.
- [x] 4.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D7, `specs/`, and `docs/legacy-unit-production.md`; run `openspec validate unit-production --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Implementation was delegated to a worker. The root **independently re-verified every claim
before accepting it**, which mattered: **five corrections were accepted and one was rejected.**

### One worker claim REJECTED after measurement

The worker reported **2** occurrences of the substring `training_time` across the six legacy
modules and **pinned that number** in a named constant. Independent measurement shows **3**
(`command.py` line 735 twice and line 737, all inside the soul-mixer branch): the worker had
counted **distinct lines** rather than occurrences. **The investigation's original figure of 3
was right.**

The root corrected it and fixed the underlying conflation rather than only the constant:

- `TRAINING_SUBSTRING_MATCH_COUNT := 3` is now documented as the **occurrence** count;
- `TRAINING_SUBSTRING_MATCH_DISTINCT_LINES := 2` was added for the **line** count;
- the suite's measurement now counts **occurrences per line** (`line.count(field)`), so the
  under-report cannot recur;
- the two counts are **asserted separately**, and the report carries
  `substring_match_occurrence_count` and `substring_match_distinct_line_count` as distinct keys;
- one assertion that compared the **line** count against the **occurrence** constant was
  corrected to compare against the line constant.

`test_unit_production.gd` went from **566 to 568 checks**. This is the third time in this
project that independent verification protected a figure: two workers were right about errors of
mine, and one was wrong about a figure I had measured correctly the first time.

### Five errors of mine, corrected after measurement

| # | The investigation claimed | Measured truth |
| --- | --- | --- |
| 1 | "109 unit references" | **distinct** ids: 609 occurrences across `offer_packs` resolve to **109 distinct units and 42 distinct buildings**; 213 across `darts_items` to **44 units and 24 buildings**. A units-only count silently dropped buildings |
| 2 | the acquisition tables are "read by no legacy branch" | `darts_items` **is** walked at **module** level by `get_game_config.py`'s `make_dynamic` / `update_darts`, which rewrite each entry's `start_date` (7 occurrences). "No legacy module" would be **false**; the precise claim is **branch-level**, and `offer_packs` genuinely is read by no module |
| 3 | "`training_time` on 130 of 470 buildings, 0 of 429 units" | the **key** is carried by **every** item in both domains (470/470, 429/429) and the domain takes only the values `0` and `5`. Those figures are the **positive-value** reading, not key presence |
| 4 | `sell`'s `KILL` is unreachable because "no reason is accepted from the client" | `reason = args[1]` is **positional**, so the legacy server *does* accept a client reason. What is unreachable is the **delivered client**, which derives its own reason |
| 5 | `pop_unit` "moves a row that already existed" | it **overwrites** the garrison row's item with the client id (`unit[0] = item_id`), so even the "already-existing" path places a **client-supplied** id — which **strengthens** the finding |

All five are corrected in `docs/legacy-unit-production.md`, `proposal.md`, and the capability
spec, each marked as a correction with its measured figure rather than quietly restated.

### The anti-invention guard was tested, not trusted

The worker's central claim is that the suite **asserts the absence** of any readiness,
remaining-time, progress, duration, or award helper. The root tested that by injecting a single
`static func is_complete` into the module:

    [test] FAIL ... the delivered module's function inventory is unchanged ...
    [test] FAIL ... no client source declares 'is_complete' in code ...
    [test] NOT-PASS ... checks=566 failures=4

and after restoring the file, `PASS ... checks=566`. **The guard fires**, so a later line that
adds a readiness helper fails the delivered suite rather than quietly reintroducing an invented
rule. That is the point of the line, and it is now evidence rather than an intention.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| Production is refused, with the evidence recorded | `production_flow.gd` exposes no readiness, completion, duration, or award path; `test_unit_production.gd` **568 checks** (581 with `--report`) — and the injection test above proves the absence is enforced |
| The row-entry inventory names every item id's source | all five branches named with source and classification (client-supplied / already-existing / derived), the closed count asserted against the committed source, and `pop_unit`'s client-id overwrite recorded in its note |
| No duration is derived from the committed training time | the committed value is reported as content, the **zero-consumer** statement and the distribution are present, the occurrence and distinct-line counts are asserted separately, and no production time, remaining time, or progress ratio is computed |
| No experience is awarded from a client amount | a recorded `attr["xp"]` is readable as content, never awarded; the client-sent amount and the client-sent level are named; the corpus's 0-of-40 absence is recorded |
| No server operation is exposed | `apps/compat-api/**` is **untouched**; the compat suite is green **unchanged** at `Ran 1257 tests ... OK`; no request is issued |
| Evidence and claim limits | `evidence/unit-production/report.json`, schema `unit-production-report-v1`, digest `E56A470B...33CD6`, byte-identical across reruns, carrying every non-claim |
| Containment and preservation | see below |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `test_unit_production.gd` | exit 0, **568 checks** (581 with `--report`) |
| report rerun | byte-identical, digest `E56A470B...33CD6` |
| `test_unit_queues.gd` / `test_unit_instances.gd` / `test_unit_definitions.gd` | exit 0, **411** / **437** / **213** — unchanged |
| `test_project_scope.gd` | exit 0, **1475 checks** (was 1441) |
| `test_scene_build.gd` | exit 0, **36 checks** |
| `verify.ps1` | exit **0** — content package, both conversion packages, and all four registry manifests byte-unchanged |
| `verify-boot.ps1` | exit **0** — 31 hermetic suites, 14 live phases; guard digests identical pre/post (`6978b959...ff348`) |
| compat suite | `Ran 1257 tests ... OK`, exit 0 — **unchanged**, as designed |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate --all --strict` | **52 passed, 0 failed** at Apply; **53** after the spec sync |

`git status` showed no legacy, config, save, content-package, or fixture byte changed, and
`apps/compat-api/**` was not touched at all. No Flash, Ruffle, ActionScript, or browser
executed; **no network was used**.

### Accepted deviations

- **The suite re-derives the recorded legacy facts from `command.py` rather than trusting the
  prose** — the five row-placing call sites and their enclosing branches, the six
  `add_store_item` sites, the `complete_*` family, the 63-branch count, and the
  `training_time` matches — and a missing legacy file is a hard `fail`, never a silently smaller
  search. This is a new cross-boundary read of frozen legacy source from a client suite; if
  legacy were ever removed the suite **fails loudly by design** rather than going vacuous. It
  was adopted precisely because the corrections above were only findable by measuring.
- **Occurrence and distinct-line counts are now separate recorded facts** rather than one
  number, which is what the rejected worker claim exposed.
- **The whole-client boundary scan depends on 13 needle tokens** being absent from client code.
  A legitimate future use of one would fail the suite — the intended pressure, but it is a
  coupling worth recording.

### Residual gaps (recorded, non-blocking)

- **No executed-legacy fixture, because no production behaviour exists to capture** — a
  stronger statement than "the corpus could not exercise it".
- **No unit is created, trained, or placed**, and **no acquisition is implemented or claimed**:
  no committed unit is store-listed, and the committed `offer_packs` and `darts_items` tables
  are read by no command branch, so enforcing their content is later-milestone work. The darts
  date rewriting in `get_game_config.py` is a content-freshness concern belonging to the
  content-census record.
- **No death or resurrection**: `sell`'s `KILL` reason is unreachable from the delivered client,
  and neither is implemented.
- **No production duration** is derived from `training_time` — the third zero-consumer committed
  field in this project, after `unit_capacity` and the level curve's reward fields.
- **`collection`, `movement`, `animations`, and `basic behaviors` remain undelivered**, each its
  own later M8 line.
- No pixel-parity oracle exists, and nothing here speaks for what the Flash client displayed.
