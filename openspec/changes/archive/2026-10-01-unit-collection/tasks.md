# Tasks

## 1. Committed collection-prize projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/collection_prize.gd`: a typed read-only projection resolving a collection id to its **committed** prize bag, resolving each granted id against the content package and classifying it as a **unit** (with its committed name) or a **building**, reporting values verbatim, and reporting an out-of-table id as unresolvable with its recorded value intact (D1) — verify: `test_unit_collection.gd` covers a unit-granting collection, a building-granting collection, an out-of-table id, every committed entry resolving, and the unit-granting count reported exactly.
- [x] 1.2 Implement the **one-based index resolution with the legacy clamp**, marking it derived-provisional with the rejected zero-based alternative retained, and **reporting that ids 0 and 1 resolve to the same prize** (D3) — verify: the suite asserts the alias explicitly and that id 0 is never presented as distinct from id 1.

## 2. Acquisition inventory, authority gaps, and refusals

- [x] 2.1 Implement the **acquisition-path inventory** classifying each recorded route as **content-derived** or **client-supplied**, naming the collection completion route the sole content-derived entry, and implementing **no** client-supplied route (D4) — verify: the suite covers each route's classification, asserts the collection route is the only content-derived one, and asserts no request is issued for any client-supplied route.
- [x] 2.2 Record the two **authority gaps** as content, with **no** eligibility check implemented (D2): a caller may name any committed collection, and the index alias is reported — verify: the suite asserts no check is performed on the caller's collection state and that both gaps are stated as recorded facts.
- [x] 2.3 Implement the three **refusals** (D5): no unit income derived, no cap semantics interpreted, and no experience awarded — with the recorded reasons and the earlier `godot-unit-production` refusal standing — verify: the suite asserts no payout, cap, threshold, or experience is computed, and asserts no award helper exists.

## 3. Executed-legacy fixture and the guarded endpoint

- [x] 3.1 Implement the capture tool under `apps/compat-api/` reusing the twelve delivered captures' disposable-copy harness (pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, a crafted envelope for one `complete_collection` command carrying a **neutral** vector and the collection id whose committed prize is a unit, POST to `…/command.php`, sanitized `request.json`, full before/after saves, response, `capture-manifest.json`, `README.md`) — verify: offline tests for envelope construction and sanitization pass, and the manifest records the target collection and its committed unit prize.
- [x] 3.2 Run the capture and commit `tests/fixtures/godot-unit-collection/`; confirm containment and assert the fixture's structural facts: the corpus's empty store **gains the committed unit id** with its committed quantity, the private-state collection ledger **grows by exactly one appended id**, and the grant matches the committed prize bag **exactly** — verify: the capture exits 0, a rerun reproduces the committed fixture byte-identically apart from documented time-dependent fields, and the twelve delivered fixture directories are untouched.
- [x] 3.3 Implement `apps/compat-api/collection_envelope.py` (the completion batch envelope with exactly one command and a **neutral** vector) and the `POST /v0/collection` route: intent validation fail-closed (JSON object, resolvable save id, a collection id, **any client-supplied prize/item id/quantity ignored**), read the pre-execution store and collection ledger, derive the prize from the committed table, dispatch through the unchanged `command()` dispatcher, and the post-execution proof (the granted id and quantity equal the **committed** bag **and** the ledger grew by exactly one appended id), plus the response carrying the derived grant and the projected prize — verify: new tests cover a unit-granting completion with both proof halves, a building-granting completion, the ignored client keys, an unresolvable collection id, every fail-closed code, and retained session/bootstrap byte-identity, all with no server.
- [x] 3.4 Implement the offline fixture-replay parity suite and assert the compat suite **grows** — verify: parity tests pass with no network and `git status` shows no `saves/` or `tests/saves/` change after the run.

## 4. GameApi operation and client flow

- [x] 4.1 Add the typed `CollectionResult` and its parse functions to `scripts/gameapi/boot_data.gd` and `complete_collection_town(collection_id)` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed shape, derived-grant parse, structured failure, and **ignored client keys** passes headless.
- [x] 4.2 Implement it in `fake_api.gd` as a deterministic in-memory double over the committed fixture and the committed collection table, granting exactly the committed prize into an in-memory store and appending exactly one ledger id — verify: the fake suite covers a unit-granting completion, a building-granting completion, an unresolvable id, and each fail-closed code with no process, server, or socket.
- [x] 4.3 Implement it in `legacy_v0_api.gd` (loopback JSON POST, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.
- [x] 4.4 Add `scripts/units/collection_flow.gd` (pure, mirroring `level_flow.gd`) exposing the projection, the unit/building classification, the recorded authority gaps, the refusals, and the display text — with **no** payout, cap, or experience helper — verify: the helpers are unit-covered, the module depends on no node, request, or clock, and the suite asserts no award or cap helper exists.

## 5. Battery, live phase, and evidence

- [x] 5.1 Update the project-scope allow-list; register `test_unit_collection` in the hermetic list (**32** hermetic suites) and add a fifteenth live phase `collection-live` that starts the Compatibility API over a disposable corpus, completes a unit-granting collection, asserts the typed response and its content-derived proof including the exact committed bag and the single appended ledger id, asserts via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, and tears down asserting port release and corpus cleanup with no working-tree `saves/` — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new phase.
- [x] 5.2 Write the deterministic `unit-collection-report-v1` report into `apps/client-godot/evidence/unit-collection/` recording the ten committed collections with their prize classification, the index resolution and its alias, the acquisition inventory, the two authority gaps, the collect-field zero-consumer findings, the corpus measurement, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, lists all required fields, and a rerun reproduces its committed bytes.
- [x] 5.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `validate_content.py` exits 0, `hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, the twelve delivered fixture directories and every delivered slice's evidence are unchanged apart from the new fixture directory and the per-run battery report, and `git diff` shows no legacy, config, save, or content-package byte changed.

## 6. Documentation and integration review

- [x] 6.1 Document the slice in `apps/client-godot/README.md`, `apps/compat-api/README.md`, and `AGENTS.md` — including that this is the **first content-derived, server-authoritative unit acquisition** and that it **corrects** the production line's broader acquisition reading — verify: each documented command matches one run successfully in this change.
- [x] 6.2 Record the residual gaps: no unit income, payout, cap semantics, or experience award; no collection eligibility check, so a caller may name any committed collection; ids 0 and 1 alias; the stored-item placement step is **not** delivered, so the fixture evidences the grant into storage and not a placed unit; the committed collections' `item_ids` requirements are unchecked; production, movement, animations, and behaviours remain undelivered; parity covers one recorded grant against the fresh-player corpus with no progressed saves; no pixel-parity oracle — verify: each gap is in the report's non-claims and the ledger.
- [x] 6.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D7, `specs/`, and `docs/legacy-unit-collection.md`; run `openspec validate unit-collection --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Implementation was delegated to a worker. The root **read the captured fixture's bytes directly**
rather than trusting the suite's assertions, re-ran every battery in the final state, and
corrected one imprecision the worker found.

### The fixture, verified from its committed bytes

The committed prize for collection 1 (Draggy Collection) is exactly `{"1085": 1}` — one unit, id
1085 Metal Draggy, quantity 1. The capture:

| Step | `maps[0]["store"]` | `privateState["collections"]` |
| --- | --- | --- |
| `login_post` | `{}` | `[]` |
| `command_complete_collection` | **`{"1085": 1}`** | **`[1]`** |

So the grant equals the **committed bag exactly**, the ledger grew by **exactly one appended
id**, and **no player state was fabricated** — the corpus's store was empty. This is the
**project's first content-derived, server-authoritative unit acquisition**, and reading the bytes
is what makes it evidence rather than an assertion. The manifest was audited for the four
statements the design requires — content-derived grant, target collection named, the stored-item
placement step recorded as **not chained**, and the neutral vector — and all four are present.

### What this line corrected rather than amended

The `production` line recorded that `buy_offer_pack` and `buy_stored_item_cash` are unvalidated
client-sent item lists, which reads as *no committed unit is obtainable*. That remains true of
those two routes and is **false of the server**. So the `godot-unit-production` delta **completes**
that finding rather than amending it, naming this as the sole content-derived route. Without it a
delivered spec would have asserted something false at exactly the moment the line disproved it.

### One imprecision of mine, corrected

The worker found that **`harvester` is not a top-level committed field** but a `properties` flag
key on **5** units — Worker I, Worker II, Worker III, Worker IV, Orc Worker — **every one with
`collect` 0**. I had listed it alongside top-level fields in the "zero legacy reads" table. The
zero-consumer finding is unchanged (it is still never read by any legacy module), but the list is
no longer read as six top-level fields. Corrected in the investigation and the proposal.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| A collection prize is derived from committed content | `collection_prize.gd`; `test_unit_collection.gd` **1793 checks** (1805 with `--report`) — a unit-granting collection, a building-granting collection, an out-of-table id, every committed entry resolving, and the unit-granting count reported exactly |
| The index is one-based, and the id-0/id-1 alias is reported | the one-based clamped resolution with the derived-provisional marking and the rejected zero-based alternative; the alias asserted explicitly and id 0 never presented as distinct from id 1 |
| One route is content-derived and the rest are client-supplied | each recorded route carries an explicit classification, the collection route is the sole content-derived entry, no client-supplied route is implemented, and no request is issued for any of them |
| Collection eligibility is not checked, and that gap is recorded | no check is performed on the caller's collection state and the recorded gap is stated in both the module and the report |
| No unit income, no cap semantics, and no experience award | no payout, cap, threshold, or experience is computed; the recorded reasons are present; the suite asserts no award or cap helper exists |
| The completion intent carries only an identifier | `POST /v0/collection` accepts only a player id and collection id, **ignores** any client-supplied prize/item id/quantity, and its proof compares against the committed bag rather than the request |
| An executed-legacy fixture for the committed grant | `tests/fixtures/godot-unit-collection/` — a disposable-copy capture against a unit-granting collection, re-runnable, containment verified, the twelve delivered fixture directories untouched, and the manifest recording both the content derivation and the unchained placement step |
| Evidence and claim limits | `evidence/unit-collection/report.json`, schema `unit-collection-report-v1`, digest `81EFAD48...64C`, byte-identical across three runs |
| Containment and preservation | see below |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `test_unit_collection.gd` | exit 0, **1793 checks** (1805 with `--report`) |
| report rerun | byte-identical, digest `81EFAD48...64C` |
| `test_game_api_fake.gd` | exit 0, **1322 checks** (was 1205) |
| `test_project_scope.gd` | exit 0, **1526 checks** |
| `verify.ps1` | exit **0** — content package, both conversion packages, and all four registry manifests byte-unchanged |
| `verify-boot.ps1` | exit **0** on two consecutive final-state runs — **32 hermetic suites, 15 live phases**; guard digests identical pre/post (`6978b959...ff348`); `collection-live` drove one completion with its content-derived two-part proof and mutated the disposable corpus save |
| compat suite | `Ran 1352 tests ... OK`, exit 0 — **grown** from 1257 (**+95**), because this line adds an endpoint |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate --all --strict` | **53 passed, 0 failed** at Apply; **54** after the spec sync |

**One known-flaky-guard occurrence:** the root's first battery run failed on the `^ERROR:` guard
with the `collection-live` phase passing; two consecutive reruns passed clean and no RID-leak line
was present in the retained logs. Reported as the known flake, not a regression — narrowing that
guard remains a recorded follow-up.

`git status` showed no legacy, config, save, content-package, or prior-fixture byte changed. No
Flash, Ruffle, ActionScript, or browser executed; every network call was loopback.

### Accepted deviations

- **`id_column` normalisation is a presentation fix only.** The pinned engine widens committed
  numbers to float, so the readout renders a whole number as its integer rather than inventing a
  shape. The underlying committed value is unchanged.
- **The fixture's `README.md` is hand-written** rather than tool-emitted, unlike the capture
  tool's own summary sections.
- **The hermetic suite is large (1793 checks)** because it covers the ten-entry committed table
  combinatorially with the classification, index, refusal, and absence assertions. Accepted as the
  cost of making the content-derived projection auditable.

### Residual gaps (recorded, non-blocking)

- **No unit income, payout, cap semantics, or experience award** — no unit carries a positive
  `collect`, no collect field is ever read, `max_collects` is 0 on every unit, and `collect_xp` is
  never read with a client-sent writer.
- **No collection eligibility is checked**, so a caller may name any committed collection. A
  server-authority gap for M13, recorded rather than fixed.
- **Collection ids 0 and 1 alias** under the legacy `max(0, collection - 1)` clamp, and the
  projection reports it.
- **The stored-item placement step is not delivered.** The fixture evidences the grant into
  storage, **not** a unit placed on the map — that round trip remains a carried follow-up.
- The committed collections' `item_ids` completion requirements are unchecked by the server.
- `production`, `movement`, `animations`, and `basic behaviors` remain undelivered; no pixel-parity
  oracle exists; no windowed capture is claimed.
