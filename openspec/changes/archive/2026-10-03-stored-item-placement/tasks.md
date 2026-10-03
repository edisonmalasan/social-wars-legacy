# Tasks

Task boxes are ticked at **Archive**, not at Apply. An unticked box is not a
statement that a task is incomplete; it is the applied diff's honest state.

## 1. Executed-legacy fixture

- [x] 1.1 Add `apps/compat-api/capture_stored_placement_fixture.py` using the shared `capture_legacy_fixtures` harness, recording three transactions against a disposable corpus over `127.0.0.1:5055`: `login_post`, the content-derived seed (`complete_collection` with id `1`, whose committed prize is exactly `{"1085": 1}`), and the placement itself (slot `41`, cell `(58, 47)`, neutral vector) — asserting the placement changes **exactly two leaves**, the new row and the store key, with every stored resource, every other row, the rest of `privateState`, and the player info byte-identical. Record a fourth transaction, the sale of a second stored item, asserting **exactly one** changed leaf, the store key, and no resource credit. Verify the capture exits `0`, that working-tree containment is reported UNCHANGED, that the port is released, and that the disposable copy is removed.
- [x] 1.2 Record the **four executed probes** from `docs/legacy-stored-unit-placement.md` §3 in the same run, distinguished from recorded transactions: placing an item that was never stored, placing onto an occupied index, placing an id absent from every normalized table, and placing at `(250, -3)`. Each probe records its observed response and changed-state facts and is marked a **divergence**, never parity. Verify each probe's recorded facts match the investigation's §3.3, §3.4, §3.10, and §3.11 exactly.
- [x] 1.3 Write `tests/fixtures/godot-stored-item-placement/` with the request/response/before/after for all four transactions plus the four probes, and a README recording the containment, the exit code, the measured changed-leaf sets, the **volatile** wall-clock row instant, and the claim limits. Verify the manifest is byte-identical across two consecutive runs **except** for the documented instant, and that the README names that exception rather than hiding it.
- [x] 1.4 Add executed-legacy parity tests replaying both recorded transactions against the shared derivation, asserting the placement's two-leaf change with the derived `attr` and `player`, and the sale's one-leaf change with every resource unchanged. Verify `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` exits `0`.

## 2. Compatibility API endpoints

- [x] 2.1 Add `apps/compat-api/stored_placement_envelope.py` holding one derivation imported by **both** the capture and the endpoints, so parity is checked against a single source: the map slot as the smallest positive absent integer (reusing `placement_envelope.next_free_slot`), the row's `timestamp` as the server clock, `store` always `[]`, `player` always `1`, and `attr` as a pure function of the committed `clicks_to_build` and `properties.friend_assistable`. Add a named inverse and assert the slot derivation round-trips across the committed corpus and that the `attr` derivation matches the legacy `engine.map_add_item` `player == 1` block for **all 900** normalized items. Verify unit tests cover both.
- [x] 2.2 Add `POST /v0/place_stored` to `compat_service.py` accepting `{user_id, item_id, x, y}` plus an optional `orientation`, deriving the slot server-side, resolving the item against committed content, and refusing `not_in_storage`, `slot_occupied`, `unknown_item_id`, and `item_not_placeable` with named codes, 409, and no state change. Carry the **two-part** post-execution proof: the stored count decremented by exactly one **and** the row present at the derived slot with the derived `attr` and `player`, plus the ledger assertion that it gained the id only if newly present. Verify unit tests cover the accepting case, all four refusals, and that the proof fails when a resource does move.
- [x] 2.3 Add `POST /v0/sell_stored` accepting `{user_id, item_id}`, decrementing stock by exactly one, touching no placement, no ledger entry, and no stored resource, and refusing an absent id with a named code. Carry the post-execution proof that every stored resource is unchanged. Verify unit tests cover the accepting case, the refusal, and that the proof fails if any resource moves.
- [x] 2.4 Add tests asserting **no** request field other than the item id, cell, and orientation influences the result — specifically that a client-supplied slot, row, attribute bag, player team, quantity, or price is ignored — and that the service exposes no bounds helper, so the recorded geometry gap is mechanical rather than an oversight. Verify each test fails if such a field is honoured or such a helper exists, then restore and re-run.
- [x] 2.5 Prove the `slot_occupied` refusal is reachable despite the derived index by exercising it against an in-memory corpus with an injected conflict, and record in the change that the typed client cannot otherwise reach it. Verify the test covers the injected conflict and the ordinary derivation.

## 3. Godot storage projection and flow

- [x] 3.1 Add `apps/client-godot/scripts/units/stored_item_flow.gd` as a typed read-only projection over `maps[0]["store"]` and `privateState.boughtUnits`, reporting committed counts and the ledger verbatim, failing closed on a non-mapping store, a non-integer count, or a non-list ledger, and deriving no capacity, expiry, value, or price. Verify the suite exercises every path including both absent-field cases.
- [x] 3.2 Add the named `attr` mirror in the flow module with a named inverse and assert it agrees with the compatibility derivation across all 900 normalized items. Verify the suite fails on any disagreement, then restore.
- [x] 3.3 Add `apps/client-godot/tests/test_stored_item_placement.gd` as the new hermetic suite, including a guard that it builds no request body, the anti-invention pin on the module's whole static-function inventory, and an assertion that **no** delivered helper accepts an `attr` or `player` parameter — making "the client cannot dictate the row's bag or team" mechanical. Verify the suite exits `0` and that injecting one invented helper produces independent failures, after which the byte-identical restore returns it to `0`.
- [x] 3.4 Add the storage placement and sale flows over the delivered `building-store` projection and the `unit-instances` row typing, reporting the ledger as distinct ids and presenting a sale as crediting nothing. Verify the scope suite still passes and no forbidden legacy transport token appears outside the legacy-v0 implementation.

## 4. Client transport and live phase

- [x] 4.1 Add the `place_stored_item_town(item_id, x, y, orientation)` and `sell_stored_item_town(item_id)` forwarders to `apps/client-godot/scripts/gameapi/game_api.gd` in the exact shape of the existing forwarders, plus both implementations' behaviour in `legacy_v0_api.gd` and `fake_api.gd`. Verify `test_game_api_fake.gd` and `test_project_scope.gd` still pass.
- [x] 4.2 Add the `stored-placement-live` phase to `apps/client-godot/verify-boot.ps1`, driving one placement and then one sale against the loopback service with their typed responses and post-state proofs, asserting the refused placement left the corpus byte-identical, and asserting a disposable corpus save mutated. Register the new hermetic suite in the same script and update the recorded suite and phase counts. Verify the script exits `0`.
- [x] 4.3 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1`, then inspect the whole verify log and every `verify-boot/*.err.txt` for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines, re-running before treating any failure as a regression given the recorded flaky surfaces. Verify both scripts exit `0`.

## 5. Documentation and integration checks

- [x] 5.1 Document the storage-placement deliver line in `apps/client-godot/README.md` following the existing "Building collection" and "Level progression" sections, including the evidence steps, the content-derived seed, the four refusals as deliberate divergences, the recorded-not-refused geometry gap, and the claim limits. Verify the documented commands are exactly the ones executed.
- [x] 5.2 Run the content validator and the preservation manifest, and confirm `git status` shows no legacy, config, save, village, content-package, conversion-package, registry-manifest, or prior-fixture byte changed. Verify `python -B packages/game-content/tools/validate_content.py` exits `0` and `python -B tools/hash-manifest/hash_manifest.py verify` exits `0`.
- [x] 5.3 Run `openspec validate stored-item-placement --strict` and confirm the change validates with no warning that Archive would refuse, then review the full diff against `docs/legacy-stored-unit-placement.md`.
- [x] 5.4 Update the roadmap `## Project Status` ledger and `### Resume point`, and record that the `unit-collection` line's carried follow-up is closed by executed evidence.

## Deferred, with reasons

- **`store_add_items`** — an unvalidated client-sent item list. `unit-production`
  already recorded it as an acquisition anti-pattern; it is used in the probes
  only, never as a delivered route.
- **Grid bounds and cell occupancy** — the already-recorded M6 tile-to-cell
  geometry gap. Requires new evidence, not a derivation.
- **Footprint-aware cell derivation** — needed for the 2×2 General Sculpture and
  3×3 Fountain prizes; blocked on the same gap. The line ships on the 1×1 Metal
  Draggy prize and records the rest.
- **`place_unit_from_store`** — a separate legacy branch named by
  `godot-unit-movement`'s recorded "type-agnostic move" finding; not this line.
- **Acceptance tests and any sale value** — the legacy server has neither and
  authoring one would invent a rule.

---

## Integration review (Archive)

Every box above was checked against the applied diff before being ticked, not
against the design's intent. Four things in this list are **not** what the tasks
predicted, and they are recorded here rather than quietly reconciled.

### 1. `tasks.md` has **twenty** boxes, not eighteen

An earlier note in this change's own artifacts, in the roadmap ledger, and in the
client README said "18 unticked tasks". **Measured: 20** — 1.1–1.4, 2.1–2.5,
3.1–3.4, 4.1–4.3, 5.1–5.4. The figure was written from memory at Propose and
never counted. It changed nothing, but a ledger that miscounts its own tasks is
not a ledger, so the correction is recorded where the wrong number was written
(PR #275).

### 2. Task 1.1's "exactly two leaves" was **wrong**, and the correction is in the manifest

The task predicted a two-leaf placement change — the new row and the store key.
**Measured: three** at whole-document scope, **two** at map scope:

```
/maps/0/items/41
/maps/0/store/1085
/privateState/boughtUnits
```

The cause is recorded in the fixture manifest and is not a defect: the committed
investigation had seeded with `store_add_items`, which calls `bought_unit_add`
in the **same** batch (`command.py:264`), so its ledger already held the id and
the placement's own append-if-absent (`command.py:246`; `engine.py:86-89`) left
the ledger alone. Seeding instead with the content-derived `complete_collection`
— which appends to `privateState["collections"]` and **never** to `boughtUnits` —
makes that third write observable. No conclusion of the investigation changes, and
`test_the_manifest_records_the_three_leaf_correction` pins the correction so it
cannot be silently reverted to the predicted number.

### 3. The capture is **five** chained steps, not four

Task 1.1 asked for `login_post`, the seed, the placement, and a sale. The sale
needs a *second* seed, because the sale consumed the only stored unit and the
collection ledger append is **if-absent** — a repeat completion grants the prize
again while the ledger stands still. So the recorded chain is `login_post` →
`complete_collection(1)` → `place_stored_item` → `complete_collection(1)` →
`sell_stored_item`, and the live phase walks the same five steps for the same
reason. This was found by the live phase, after the offline suite was green.

### 4. `slot_occupied` **is** implemented — and it is not the geometry gap

The four refusals all ship, each with its executed probe recorded as a
**divergence**: `not_in_storage`, `slot_occupied`, `unknown_item_id`,
`item_not_placeable`, all 409, all changing nothing. What is *not* refused is an
out-of-grid cell, and the manifest states why the two are different: an occupied
slot **destroys an existing row** and is invisible to any count-based check,
which is a more serious failure than an out-of-range coordinate that damages
nothing. No bounds helper exists in the module and the suites assert that absence
mechanically rather than trusting it.

### What was verified, and how

| check | result |
| --- | --- |
| fixture capture | exit **0** on four consecutive runs, containment **UNCHANGED** (`18e5e55b…a724`) |
| re-runnability | **measured**: normalizing exactly the four documented wall-clock field kinds made the directory byte-identical; not normalizing them made every file carrying one differ |
| compat suite | `Ran 2130 tests ... OK`, exit 0 (**+216** over the 1,914 baseline); the three new modules alone are **216** tests |
| `test_stored_item_placement.gd` | **544** checks, the **39th** hermetic suite |
| `stored-placement-live` | 119 checks, exit 0, and the disposable corpus save mutated |
| batteries | `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **39 hermetic suites and 20 live phases** |
| log sweep | **574** files, **zero** `[test] FAIL` / `^ERROR:` / `SCRIPT ERROR` |
| content + preservation | validator `valid`, 21 schemas; manifest **3,258 entries** |
| OpenSpec | `validate --all --strict` **61 passed / 0 failed** after the spec sync |
| report | `c5bea9dd…8d18`, 13,618 bytes, byte-identical across **four** runs |

### Two anti-invention guards, proven by injection

`cell_is_free` into the delivered flow module produced **3** independent
failures and exit 1. `refund_for` produced **1** — which is what exposed that the
by-name guard matched only the exact name and missed a suffixed helper wearing the
same disguise. A substring check was added; the same injection then produced
**2**. Both restores were byte-identical (`0b437e5d…0edbd`, re-measured after
restore) and returned the suite to 544 checks, exit 0.

### Four cross-layer defects the hermetic suite structurally could not catch

**544** offline checks passed while the live phase failed **four** separate
times: the bootstrap payload is keyed `map` while the recorded fixture documents
are keyed `maps[0]` (so one storage assertion had been passing for the wrong
reason); `CollectionResult` has no `count_after`, so a bad field aborted the
function before the sale and both refusals ran; the service's and the client's
copies of the recorded notes are deliberately not identical, so a byte-equality
assertion was claiming "verbatim" — stronger than anything true; and the
if-absent ledger append, above.

### One cross-suite boundary amended, not deleted

`test_unit_collection.gd::_check_boundary()` asserted the placement token was
absent from **every** client source. That claim became false the moment this line
landed and was **measured failing with 4 failures** before being touched. It is
now an ownership claim whose recipient this suite asserts, so the owner list lives
in exactly one place. Its count went **1,988 → 1,894**.

### A sixth recorded flaky surface was found and **fixed**, not re-run

`verify-boot.ps1` failed `test_collection_endpoint.ContainmentTests` once on
`server_time` 1791066504 against 1791066505 with every other field identical;
three immediate reruns passed. `/v0/session` stamps the current time on every
response, so the assertion was **testing the clock, not the session list**. The
first fix was then found wrong in the **other** direction by running that file
alone, because inside one second the clock does *not* differ; the assertion is
now that the differing-field set is a **subset** of the documented volatile
field. It was made to fail rather than trusted — injecting a real session-list
change produced `AssertionError: {'saves'} not less than or equal to
{'server_time'}` — and restoring the byte-identical file (`8efd62d8…7ab6`)
returned it to 36 tests and `OK`. This is the project's first flaky surface
closed rather than re-run.

### Deferred, and still deferred

Every entry in the section above is still deferred, with the same reasons. The
M6 tile-to-cell geometry gap remains the blocker for footprint-aware cell
derivation, so the 2×2 and 3×3 collection prizes still cannot be given a correct
cell; this line ships on the 1×1 Metal Draggy prize.
