# Tasks

## 1. The dead-hero ledger projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_behaviors.gd`: a typed read-only projection of `privateState["deadHeroes"]` carrying each recorded item id and its recorded count, the increment and decrement shapes, and the **delete-at-zero** rule verbatim, with no count derived from another (D1) — verify: `test_unit_behaviors.gd` covers every recorded entry verbatim and asserts that no threshold, cap, or clamp is applied.
- [x] 1.2 Name **both** legacy gates exactly as `push_dead_unit` does — the row on **player team 1** and the committed **`resurrectable > 0`** — and derive no further eligibility (task 1.1's second half) — verify: the suite asserts both gates are named with their recorded source lines and that a third gate is not invented.
- [x] 1.3 Implement the **fail-closed** path: a ledger that is absent or is not a string-keyed object is reported **unresolvable with its recorded state intact**, never defaulted to an empty ledger presented as a resolved one — verify: the suite covers an absent ledger, a non-object ledger, a non-string key, and a non-integer count, each refusing rather than defaulting.
- [x] 1.4 Assert the **committed distribution** the projection's eligibility rests on: `resurrectable` is positive on **426 of 429** units and **0 of 470** buildings, so the flag is **unit-only**, measured in the same run rather than asserted (D4) — verify: both figures are compared against the recorded constants and a discrepancy fails the suite.

## 2. The three-door command inventory

- [x] 2.1 Record the inventory naming `kill`, `sell`, and `resurrect_hero`, each with whether it reaches the ledger and what else it mutates (D2) — verify: the suite asserts all three are named with an explicit ledger effect, and that the count of ledger-reaching commands matches the committed source.
- [x] 2.2 Record that **`kill` never touches the ledger**, that **`sell` reaches it only behind the combat-reason guard and only through the `push_dead_unit` engine helper**, that the helper is an **engine helper and not a dispatcher branch**, and that the 63-branch count and the ledger-reaching command count stay distinguishable — verify: each of the four facts is asserted, and the branch-name set is pinned so a future dispatcher edit is caught.
- [x] 2.3 Record the **`resurrect_hero` placement shape**: the ledger decrement with the **delete-at-zero** rule, then a re-placement at **client-supplied** `index`/`x`/`y`, and the **`used_syringe` argument read and discarded** — verify: the suite asserts the discard is recorded and that no committed field is read in its place.

## 3. The revival endpoint

- [x] 3.1 Add `apps/compat-api/behavior_envelope.py` and `POST /v0/resurrect` accepting **only** a player identifier and a cell, deriving the **item id**, the **map key**, and the resulting ledger state server-side, and **ignoring** any client-supplied syringe count (D2) — verify: the endpoint refuses a request carrying extra fields, the response carries no echo of any ignored value, and the compat suite covers both.
- [x] 3.2 Apply the legacy decrement and **delete-at-zero** rules and **both** gates server-side; refuse a cell that resolves to no recorded ledger entry and refuse one whose resolved entry's committed `resurrectable` is not greater than zero, each with a **named code**, an **empty payload**, and **no ledger change** — verify: both refusals are asserted with their codes, their empty payloads, and a byte-identical ledger before and after.
- [x] 3.3 Add the **two-part post-execution proof**: the ledger entry is **gone** after a revival that reaches zero, and **every stored resource is unchanged** — the second half being what makes the no-syringe-cost claim non-tautological (D3) — verify: both halves are asserted, and the resource half compares the **full** resource set rather than a selected subset.
- [x] 3.4 Add typed `resurrect_hero_town()` to **both** GameApi implementations and a `behavior_flow.gd` client flow that sends only intent and never a derived value — verify: the fake and legacy-v0 implementations return the same typed shape, and the flow suite asserts the request body carries only the player identifier and the cell.
- [x] 3.5 Register the **`behavior-live`** phase in `verify-boot.ps1` with `--expect-save-mutation`, driving one revival through the real v0 endpoint against a disposable corpus seeded with a resurrectable ledger entry, and asserting the ledger entry is removed; update the hermetic list (**35**) and the header sentence — verify: `verify-boot.ps1` exits 0 end to end, the phase proves the disposable save mutated, and the port is released with no working-tree `saves/` left behind.

## 4. The refusals and the anti-invention guard

- [x] 4.1 Implement the **refusals as stated requirements**: no syringe cost and no resource movement; **no** combat resolution of any kind (no damage, outcome, defence, hit, or life computation) from the seven zero-consumer combat fields; and **no** occupancy, bounds, type, or terrain validation added to the revived placement, reproducing the legacy branch's absence rather than filling it (D3, D5) — verify: each refusal family is present with a non-empty reason, and the committed combat fields are reported with their **measured** zero-consumer counts.
- [x] 4.2 Assert the **anti-invention guard** (D7): the suite fails if any syringe-cost, damage, attack, defence, hit, occupancy, or charge helper is added to the module — verify: inject one such helper, observe the failure, restore the file from a byte-identical copy, and confirm the suite passes again; record the result in the review.
- [x] 4.3 Measure **every** legacy and content figure in the same run rather than taking any on trust — the twenty behavioural fields' zero-consumer counts across the seven modules, the 63-branch inventory, the `resurrectable` and `syringes` distributions, the corpus measurement, and the `clicks_to_build` single read — verify: each measurement is compared against its recorded constant and a discrepancy fails the suite rather than being averaged away.
- [x] 4.4 Assert the **`clicks_to_build` boundary**: its single legacy consumer is the construction-click counter owned by `godot-building-construction`, and this line **reimplements nothing** (D6) — verify: the suite asserts the relationship is recorded and that no consumer of that field exists in the new module.

## 5. Boundary, evidence, and integration

- [x] 5.1 Assert the **no-manufactured-coverage boundary**: no save, corpus, or fixture is created or modified to hold a unit row, and the corpus's unit-only flag and building-only placements are recorded as the specific cause of the absent executed-legacy fixture (D4) — verify: the boundary assertions run headless, `git status` shows no corpus or fixture byte changed, and the recorded reason distinguishes the corpus limitation from the refusal lines' absence of behaviour.
- [x] 5.2 Write the deterministic `unit-behaviors-report-v1` report into `apps/client-godot/evidence/unit-behaviors/` (written by the suite itself via `--report=<path>`, bare `--report` defaulting there, with the destination directory created first) recording the ledger projection, the three-door inventory, both gates, the delete-at-zero rule, the ignored `used_syringe`, the zero-consumer behavioural fields with their distributions, the corpus measurement, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.
- [x] 5.3 Document the slice in `apps/client-godot/README.md` and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no combat is resolved" and "no syringe cost" limits are stated wherever the slice is described.
- [x] 5.4 Run the full preservation battery in the final state and record the residual gaps (no syringe cost and no resource movement; no combat resolved; no occupancy/bounds/type/terrain validation added; the death/resurrection pairing derived; `clicks_to_build` referenced and not reimplemented; no executed-legacy fixture and the specific corpus cause; no unit revived against the committed corpus; no pixel parity and no windowed capture) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, the compat suite is green and **grown** by this line's endpoint tests, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed.
- [x] 5.5 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D8, `specs/`, and `docs/legacy-unit-behaviors.md`; run `openspec validate unit-behaviors --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

---

# Review record

Recorded by the orchestrator after the Apply stage. Every figure below was **re-measured** rather
than taken from the implementation worker's report; seven of that report's corrections to the brief
and to the committed investigation were **confirmed correct**, and the orchestrator's own
documentation was corrected accordingly.

## Requirement-to-evidence map

| Requirement | Evidence | Status |
| --- | --- | --- |
| The dead-hero ledger is projected, and the gates are named | `unit_behaviors.gd` `project_ledger` / `ledger_entries` / `expected_increment` / `gates` / `gate_count`; suite asserts verbatim counts, both gates, delete-at-zero, and four fail-closed paths | met |
| The three-door command inventory records which command reaches the ledger | `command_inventory`, `engine_helpers`, `ledger_reaching_commands`; suite asserts `kill` never reaches it, `sell` only behind the guard, the helper is not a branch, and the 63-branch set is pinned | met |
| A revival is a server-derived intent, and the client-supplied syringe is ignored | `POST /v0/resurrect` in `behavior_envelope.py`; compat suite **+92** tests; `resurrect_hero_town()` on both GameApi implementations; `behavior_flow.gd` sends a 3-key intent | met |
| No syringe cost, and the committed syringes field is content only | Two-part post-execution proof includes the **full** resource set unchanged; `syringes` reported with its measured zero-consumer count | met |
| No combat is resolved, and no placement validation is invented | `ABSENT_HELPERS` names twelve absent helpers with a legacy reason each; the suite pins the module's whole static-function inventory | met |
| No executed-legacy behaviour fixture is claimed | No fixture captured; the **specific** corpus cause is stated; no committed corpus or fixture byte changed | met |
| Unit-behaviour evidence and claim limits | `evidence/unit-behaviors/report.json`, digest `0FE80C47…8F59`, 39,979 bytes, byte-identical across three runs | met |

## Measured in the final state

| Check | Result |
| --- | --- |
| `test_unit_behaviors.gd` | exit 0, **573 checks** (587 with `--report`) — the **35th** hermetic suite |
| `test_unit_animations.gd` / `test_unit_movement.gd` / `test_unit_production.gd` | exit 0, **628** / **245** / **568** checks |
| `test_project_scope.gd` | exit 0, **1645** checks |
| `verify.ps1` | exit **0** |
| `verify-boot.ps1` | exit **0**, **35 hermetic suites, 16 live phases** |
| compat suite | **`Ran 1444 tests ... OK`**, exit 0 — up from 1352 by **+92** |
| content validator | exit 0, `result: valid`, 21 schemas |
| hash manifest | 3,258 entries, exit 0 |
| `openspec validate unit-behaviors --strict` | valid |

## The anti-invention guard was tested, not trusted

Re-run **by the orchestrator**, independently of the implementation worker's report:

1. copied `unit_behaviors.gd` to a byte-identical backup (SHA-256 `12AEFD7B…`)
2. appended one invented `static func syringe_cost(syringes: Variant) -> int`
3. the suite **exited 1 with 5 independent FAIL lines** — the guard is a **whole static-function
   inventory compared against a pinned list**, plus a `FORBIDDEN_HELPERS` list, so an addition fails
   on both axes
4. restored from the byte-identical copy (SHA-256 unchanged at `12AEFD7B…`)
5. the suite returned to exit 0 with **573 checks** and **0 FAIL**

## Two battery runs: one exit 1 that was not this line

The first `verify-boot.ps1` run exited **1** with five failed checks. Inspecting
`.godot/verify-boot/*.txt` — rather than trusting the exit code — showed **none of them was this
line's**:

- `test_town_xp` tripped the known nondeterministic `^ERROR:` RID-leak guard on an untouched suite.
- The four `level-up live phase` failures came from a single run of `46-level-up-live` that died with
  `exit=3228369023` (`0xC06D007F`, a Windows delay-load/module-load crash) having printed **no** test
  output at all. **The same phase passed nine times in the same battery run**, on an untouched M7
  phase.

A rerun exited **0** with all checks green. Both were the already-recorded engine-level flakes, and
narrowing the `^ERROR:` guard remains a carried follow-up.

## Corrections to the committed investigation, all independently re-verified

`docs/legacy-unit-behaviors.md` carried five figures that were **asserted rather than measured**.
The Apply stage measured them and the orchestrator re-measured each before accepting it. The record
now carries a corrections section rather than quiet edits:

1. the zero-consumer count is **twenty-one**, not twenty (the prose said "twenty of twenty-two" while
   naming twenty-one), and the behavioural total is **twenty-three**
2. four source lines were each **off by one**: `push_dead_unit` is `engine.py:149-170`,
   `resurrect_hero` is `172-181`, `del deadHeroes[itemstr]` is at **179**, and the
   `if num_heroes <= 0:` guard is at **178**
3. `resurrectable` is **carried** by 426 of 429 units with the key **absent entirely** on ids **923**,
   **933**, and **1176** rather than set to zero; every present value is the string `"1"`; **0 of 470**
   buildings carry the key
4. `clicks_to_build` takes **two** distinct values over the units (both `0`) rather than three; over
   the buildings it is `{0: 172, 1: 298}`
5. `collect_type` takes **two** distinct values over the **units** (`g` 427, `w` 2); the five-value
   `w`/`o`/`s`/`c`/`g` spread belongs to the **buildings** only

**None changes the conclusion**: the mechanism, both gates, the delete-at-zero rule, the three doors,
the `used_syringe` discard, and the corpus's inability to exercise any of it are all unchanged.

## A stale figure that was not wrong at the time it was written

`AGENTS.md` had recorded the unit-collection suite at **1845/1857**, itself a correction of an older
**1793/1805**. Re-measured on unmodified code it is **1884/1896**, stable across four consecutive
runs and unaffected by clearing the Godot import cache. The cause is not non-determinism: that suite
walks `CLIENT_SCAN_ROOTS` (`res://scripts` and `res://tests`, **93 files** today) and asserts per
walked source, so **its check count grows with every client source a line adds**. The record now
states that dependency instead of pinning a number that will drift again.

## Deviation, approved

`apps/client-godot/scripts/gameapi/game_api.gd` was edited although it was not in the implementation
worker's ownership list. All fifteen existing live phases drive through the `GameApi` autoload
facade, so the `behavior-live` phase would otherwise have had to instantiate `LegacyV0Api` directly
and diverge from the established pattern. The change is three additive pieces in the exact shape of
the fifteen existing forwarders, and `test_game_api_fake.gd` (1322 checks) still passes.

## Three bugs the suite itself had, found by measurement

- `_code_only()` was passed a **path** instead of the body, making the syringe-cost, `nc`, and
  clicks scans **vacuously true**
- it then desynchronised on an apostrophe inside a double-quoted string, fixed with a proper
  two-state lexer
- the live scenario's `addressed.size() != 3` guard silently aborted after 7 checks, which is why the
  first two live attempts showed no save mutation

## Residual gaps carried forward

- **No syringe cost** and **no resource movement** — the committed `syringes` field has zero
  consumers, so charging one would invent an economy.
- **No combat is resolved.** Seven committed combat fields measure zero consumers; the numbers are
  content, never rules.
- **No occupancy, bounds, type, or terrain validation** on the revived placement. The legacy branch
  checks none; this is a Server v1 / M13 gap and was deliberately not filled, since filling it would
  make the modern client *stricter* than the legacy server.
- **The death/resurrection pairing is derived**, not asserted by the source.
- **No executed-legacy fixture**, and the cause is a corpus limitation with a named cause — the
  absence of a **resurrectable row**, not the absence of a mechanism. No unit row was manufactured.
- **No unit is revived against the committed corpus**, **no pixel parity**, and **no windowed
  capture**.
- The committed corpus is **not** all team 1 — keys 1–20 are team 1 and **21–40 are team 3**.
