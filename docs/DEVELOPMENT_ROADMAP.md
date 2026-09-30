# Social Wars Modernization & Flash-Free Reconstruction Roadmap

**Project:** Social Wars Legacy Reconstruction  
**Primary Goal:** Reconstruct the existing Social Wars implementation into a modern, maintainable, Flash-free client/server game while preserving the behavior, content, saves, assets, and historical implementation contained in the current repository.

**Core Strategy:** Preservation-first reconstruction.

The existing repository will **not** be thrown away or treated merely as obsolete code.

It will serve as:

- Reference implementation
- Behavioral specification
- Protocol specification
- Preservation dataset
- Save-game corpus
- Content database
- Asset archive
- Regression oracle
- Migration source
- Historical documentation

The modern version will progressively replace Flash/SWF functionality with a Godot client while preserving the existing Python server until behavioral parity has been verified.

Only after the new client is substantially functional should the backend be modernized into an authoritative production architecture backed by PostgreSQL.

---

<!-- ORCHESTRATOR_STATUS_START -->

## Project Status

This section is maintained by the root Codex orchestrator.

It is a progress ledger, not the source of truth for specified behavior.

- **Current milestone:** **M8 — Units — in progress.** M7 — Construction and Economy — is **complete with its exit assessed MET**; all eleven of its deliver lines are delivered and archived. M6 — Town Vertical Slice — remains delivered with its exit assessed MET (the first major project success target); M0–M5 deliver lists are complete with their exits assessed MET. **M8's deliver list is `unit definitions`, `unit instances`, `queues`, `production`, `collection`, `movement`, `animations`, `basic behaviors`, and its exit criterion is "Core unit gameplay works"** — the first line, **`unit definitions`, is delivered and archived**; the second, **`unit instances`, is the next bounded line and its investigation is the next objective**
- **Roadmap cursor:** **M8 — Units**, line 2 of 8 — the cursor advanced from M8 line 1 after `unit-definitions` was delivered and archived as `2026-10-01-unit-definitions`. **M8 line 1 is delivered:** a typed, read-only static `UnitDefinition` over the **429 committed unit definitions** in `packages/game-content/normalized/units.json`, resolved only through the manifest-verified `units` domain via `ContentRegistry`, preserving each legacy ID verbatim as a string (`923`..`1431`, all distinct), parsing **58 committed fields** (56 on every row, plus `breeding_order`/`sm_training_time` on 300 each) in five named field groups, failing closed on any malformed field, recording conditionally-present and nullable fields as absent rather than zero, and exposing one documented raw-entry accessor so no committed field is dropped. It adds a **public `ContentRegistry.legacy_ids(domain)` accessor** so enumeration crosses the same digest gate as every other read instead of reaching into a private index or re-reading the committed file. **The static-definition/player-instance boundary is now a stated spec requirement** — a definition has no field that could hold a placement key, coordinates, an owner, or current health, asserted structurally — so `unit instances` inherits a named boundary instead of discovering one. **No endpoint, no save shape, and no Compatibility API change**, so the compat suite stayed green **unchanged** at `Ran 1109 tests ... OK`
- **Active OpenSpec change:** None — M7's eleventh and final deliver line was delivered as `building-xp`, archived as `2026-09-30-building-xp`, completing the milestone. Its evidence basis was the committed investigation `docs/legacy-xp-basics.md` (PR #198), which found the legacy server **almost entirely absent** from the area: `level_up(new_level)` sets `map["level"] = new_level` with **no range check and no XP validation**, so a client could set level 99 and the server answered success; `add_xp_unit` is *unit* experience and **0 of the 40 placed corpus rows carry `attr["xp"]`** (no unit placements exist); and **nothing in the legacy server reads the committed `levels` schedule** — zero references across `command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`. The curve: 100 entries, `exp_required` **strictly increasing** with no duplicates and no non-positive gap (`0, 40, 60, 100, 200, 350, 550, 800, …` to `2016089205`), `reward_type` in `{s, w, g, c}` — the same letter vocabulary as `items[].costs` — that **nothing consumes**, and `name` **not** distinct (44 names over 100 entries), so it is a label and not an identifier. **The one consequential decision — the index base — was resolved from the committed corpus and then confirmed by it:** at `xp 4` the **zero-based reading is actively contradicted** (it implies level 0 while the save records level 1, since the curve says level 1 begins at 40 experience), whereas **one-based** gives `4 >= exp_required(1) = 0`; the compat slice then derived **level 1** for the corpus's `xp 4`, matching the recorded level. Guessing zero-based would have shifted **every** level in the game by one, invisibly, until a player noticed the wrong level name — so the interpretation is **derived-provisional everywhere it is recorded with the rejected zero-based alternative retained**, and the conversion lives in **exactly one named function per layer** with a round trip asserted across all 100 entries. Delivered: the committed-curve model and readout; **explicit disagreement reporting** (both values named, nothing reconciled, because the recorded level is written from a client integer and is unverified against the curve); `POST /v0/level_up` accepting **only** `{user_id}` with a client-supplied level **ignored**; two 409 refusals resolved before the dispatcher; and the family's **third proof form** — the recorded level equals the derived level **and every stored resource is unchanged** — which forecloses vector smuggling through a command dispatched like any other. **Not invented:** no level reward (the reward fields are committed on every entry and consumed by no legacy branch, and the typed `LevelCurve` deliberately carries no reward field), no unit XP, no tutorial progression, and no rebalancing (the committed thresholds are preserved verbatim). Two honest consequences are recorded rather than papered over: the corpus is **already at its derived level**, so the fixture's transaction moves nothing (recorded as `level_moved: false`, with level *movement* established by a recorded probe that moved `level 1→2` and `xp 4→504`), and the `level-up-live` phase **deliberately does not assert a save mutation**, proving the refusal instead — so **a successful live level-up is unproven** and is a recorded claim limit
- **Lifecycle stage:** ARCHIVED
- **Change status:** Closed — archived as `2026-10-01-unit-definitions` (proposal PR #204 merged as `cf13a5b`, Apply PR #205 merged as `72f87a3`, spec-sync PR #206 merged as `43b8ed4`, **archive PR pending at commit time**). Implementation on `feat/unit-definitions` (one commit): the typed model, the registry-backed catalog, the hermetic suite, the deterministic report, the public registry accessor and its test, and the scope/battery registration. Artifacts: `proposal.md`, `design.md` decisions D1–D8, `tasks.md` 10 tasks (all ticked) plus the integration-review record, capability deltas `godot-unit-definitions` **ADDED** (7 requirements / 21 scenarios), `godot-compatibility-boot` **MODIFIED** (the `GameApi` abstraction requirement now records that unit **definitions** are committed content read through `ContentRegistry` and are therefore **not** a GameApi operation, plus the "Read unit definitions from committed content" scenario), and `godot-content-registry` **MODIFIED** (the public id enumeration joins the `Domain indexing and lookup` requirement's list of exposed lookups, with its committed-order contract and two scenarios). `openspec validate --all --strict` PASS at Propose, at the integration review, and at Sync (**50/50**); **49/49** after the archive move. **Two design premises in the change's own artifacts were disproved by the Apply stage and corrected rather than shipped** — `costs` and `properties` are committed **objects**, not embedded-JSON strings (content rule R2 coerces them and the schema declares both `"type": "object"`), and the field count is **58, not 53**; both were root-verified three independent ways. **A third premise was narrowed rather than implemented as designed**: the worker reached into `registry.get("_domains")` to enumerate the domain, correctly having found no public enumeration API, but the alternative of re-reading `units.json` would have bypassed the digest gate that is the registry's entire purpose — so a public accessor was added instead, turning an undocumented escape hatch into a specified capability
- **M7 exit assessment: MET** — exit criterion "Core town-building gameplay loop works" is satisfied by committed evidence across all eleven delivered lines, each with its own executed-legacy fixture, endpoint, typed operation, client flow, hermetic suite, live battery phase, and captured evidence: a player can **place** a building from the catalogue, **purchase** one with cash, **move** it, **sell** it, **store** it, **upgrade** it, watch its **construction** start and finish, **collect** its income, **expand** the town, **read** every resource the save carries, and **advance** a level on the committed curve — with every state-mutating step executed by the unchanged legacy command path behind a typed, intent-only contract, and every response applied from the server's own numbers rather than the client's arithmetic. The loop's **legibility** is committed too: `apps/client-godot/evidence/town/` renders the real town with all ten readout rows sourced (the resources line corrected the primary-currency row from a field nothing produces to `gold`, which made the currency visible for the first time), and eleven further evidence directories carry windowed captures plus deterministic reports, each byte-identical across reruns. The families' post-state proofs together are the milestone's central safety result: a value **moved by exactly** a derived delta (collect), **moved by exactly** a derived debit (expand), and proven **not to move at all** (level up), so a client-sent vector cannot mint or burn through any delivered surface. Final-state verification: `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **27 hermetic suites and 13 live phases** and guard digest `6978b959…ff348` pre=post; compat **`Ran 1109 tests ... OK`**; hash manifest 3,258 entries; `openspec validate --all --strict` 48/48 exit 0 after the final archive. **Residual gaps named by the delivered specs, none blocking the criterion:** no Flash, Ruffle, ActionScript, or browser executed anywhere and **no pixel-parity oracle** against the legacy client exists; parity everywhere rests on **one recorded transaction against the fresh-player corpus** plus recorded probes, never on progressed players (whose saves remain unavailable); the HUD's labels and layout are the delivered provisional convention; the **expansion tile-to-cell geometry is a known evidence gap**, so no terrain, grid, buildable-cell, or placement-bound growth is claimed — the expansion line delivers the unlock ledger only; no level reward is paid, unit XP and tutorial progression are out of scope because the corpus cannot exercise them, and the level curve's index base is derived-provisional from one corpus data point with its rejected alternative retained; collect's payout amounts and expand's price index are derived from committed content and never observed from the Flash client; and every stored rule's server-authoritative validation remains Server v1 (M13) work
- **M6 exit assessment: MET** — exit criterion "A player can launch and view a real legacy town without Flash" is satisfied by committed evidence: `apps/client-godot/evidence/town/town-player.png` (windowed run, boot → `town=rendered placements=40`, 1400×600, 741,893 bytes) shows the fresh save's real town, and `town-slice.png` (1400×600, 1,226,928 bytes) together with `report.json` (`town-report-v1`, committed blob sha256 `1540D11A…676AF`, `bootstrap_requests` 1) records the inputs and their digests, the derived-provisional projection constants, counts by chosen visual source (player save: 40 objects = 31 thumbnails + 9 markers; slice: 576 objects including the authentic House I and Wild Elephant sprites), the observed HUD values, selection and camera state, and five explicit non-claims. Remaining gaps named by the `godot-town-rendering` spec: projection provenance (the legacy SWF's numeric iso constants were never extracted; the constants derived from save coordinate extents, content footprints, sprite scales, and documented iso-engine identifiers remain provisional); authentic HUD/selection visuals (values and hit behavior are authoritative, but presentation uses the modern UI foundation rather than legacy Flash art); unit presence in the live save (the fresh save contains no unit placements, so authentic unit rendering is proven via the slice scene); and the systems deferred to later phases (placement/movement/disposal, buildings, economy — M7 and beyond). No pixel-parity oracle against the legacy client exists, and no Flash, Ruffle, ActionScript, or browser executed
- **M4 exit assessment: MET** — exit criterion "at least one authentic building and unit render correctly in Godot" is satisfied by committed evidence: `apps/client-godot/evidence/first-render/first-render.png` (448×224, sha256 `da15d192…bae5`, visually verified: House I tent + elephant with crisp alpha on the neutral background) and `apps/client-godot/evidence/first-render/report.json` (`pass=true`, `failures=[]`, oracle error (0,0) both entities, max_abs 1/1/1/0, entity coverage 1.0, input package digests recorded). Claim limits in `apps/client-godot/README.md`: authentic source-bitmap fidelity at authentic bounds/placement within documented tolerances — explicitly not live-Flash pixel parity (Flash execution is forbidden and no reference renders exist).
- **M3 exit assessment: MET** — exit criterion "Godot can load validated game definitions without parsing arbitrary legacy structures" is satisfied by two archived changes over the same manifest-bound package: `godot-content-registry` (the `ContentRegistry` autoload loads exactly the manifest-driven canonical package — all 22 recorded outputs’ byte counts and SHA-256 digests verified with fail-closed errors, entries indexed by `legacy_id` with duplicate rejection — never parsing arbitrary legacy structures) and `content-validator` (offline validation of that same package: manifest byte/SHA-256 integrity, 21-schema conformance, and cross-domain reference integrity). Claim limits: the validator establishes schema, manifest, and reference conformance of the committed package only — not served-byte equality, content validity, asset existence, gameplay parity, or progressed-player coverage; the two claims bind through the shared manifest digests
- **M7 progress delivered by this change:** the **eleventh and final** M7 deliver line, level progression, is closed — completing the milestone. Executed-legacy fixture committed (`tests/fixtures/godot-building-xp/`, capture exit 0 three times with a byte-identical rerun apart from the documented time-dependent fields, and the recorded probe establishing level movement); the `/v0/level_up` endpoint with the derived target, the ignored client-supplied level, the two 409 refusals, and the two-part proof including that **no** resource moved (compat suite `Ran 1109 tests ... OK`, including `test_level_envelope`, `test_level_endpoint`, and `test_level_parity`); typed `level_up_town()` on both GameApi implementations; client flow `tests/test_town_xp.gd` **767 checks**; battery integration — **27 hermetic suites and 13 live phases**; and evidence `apps/client-godot/evidence/building-xp/` (capture plus `xp-report-v1`, digest `f64a5bec…52a0`, byte-identical across runs, carrying the derived interpretation with its rejected alternative quoted). **All ten previously delivered lines remain delivered and archived.** Commands, purposes, provenance, and claim limits recorded in `AGENTS.md`, `apps/client-godot/README.md`, `apps/compat-api/README.md`, and the updated `docs/legacy-xp-basics.md`
- **Current objective:** This orchestration run completed the M7 milestone. It recorded the XP-basics investigation (PR #198), reconciled the `building-resources` archive bookkeeping (#197 / `1970325`), proposed `building-xp` (PR #199), and completed the full lifecycle (Propose → Apply → implement → test/verify → Sync → Archive → roadmap ledger update → **M7 exit assessment**) for the eleventh and final bounded M7 objective. Prior stages in this run: the `building-resources` lifecycle (#193–#197), the expand lifecycle (#188–#193), `building-collect` (#184–#187), the collect-income investigation (PR #183), the `building-construction` lifecycle (#178–#182), `building-upgrade` (#174–#177), `building-store` (#169–#172), `building-sell` (#165–#168), `building-move` (#161–#164), `building-purchase` (#157–#160), `building-placement` (#153–#156), `town-vertical-slice` (#149–#152), `content-validator` (#144–#148)
- **Last completed change:** `unit-definitions` — archived as `2026-10-01-unit-definitions`; proposal PR #204 (merged `cf13a5b`), Apply PR #205 (merged `72f87a3`), spec-sync PR #206 (merged `43b8ed4`). Previous: `building-xp` — `2026-09-30-building-xp` (#199–#202, archive PR #202 merged as `fb999618`); `building-resources` — `2026-09-30-building-resources` (#193–#197); `building-expand` — `2026-09-30-building-expand` (#189–#192); `building-collect` — `2026-09-30-building-collect` (#184–#187); `building-construction` — `2026-09-29-building-construction` (#178–#182); `building-upgrade` (#174–#177); `building-store` (#169–#172); `building-sell` (#165–#168); `building-move` (#161–#164); `building-purchase` (#157–#160); `building-placement` (#153–#156); `town-vertical-slice` (#149–#152); `content-validator` (#144–#148)
- **Next eligible objective:** **M8 line 2, `unit instances`** — the next bounded line. **The investigation comes first and is the immediate next objective:** read the command catalog's **"Units and production queues"** family (`push_unit`, `pop_unit`, `push_dead_unit`, and any real save-instance shapes) plus the committed legacy source, then establish what a unit instance actually looks like in a save. **Do not re-derive the three facts PR #203 already recorded:** the committed fresh-player corpus has **no unit placements at all** and 0 of its 40 placed rows carry `attr["xp"]`; M4's converted Wild Elephant package proves asset linkage and renderability, **not** animation or gameplay semantics; and the content package already carries the 429 committed unit definitions (now typed and delivered). **Because the corpus cannot exercise a unit instance, the investigation must record that limitation rather than fabricate a player state** — and it inherits the boundary this line just drew: a `UnitInstance` is player-owned save state with its own key, health, garrison, and ownership, and is a **new type**, never a widened `UnitDefinition`. The M8 order continues **queues → production → collection → movement → animations → basic behaviors**. Two carried facts: **authentic progressed-player saves remain unavailable**, so parity rests on the fresh-player corpus plus recorded probes; and the road-adjacent follow-ups are the friend-assist cluster, construction speedups, the upgrade row's seeded `{"nc": 0}`, the storage round trip, the premium upgrade path, the legacy level gate and daily-upgrade limit, cap semantics for a non-zero `max_collects`, **the expansion tile-to-cell geometry** (new evidence, not a derivation), and the internal `TownState.Resources.coins` alias
- **Blocking issues:** None. Source-truth observations recorded: elephant 550×400 @ 30 fps, 7 sprites, sprite 63 labels at frames 1/6/11/16/21, 28 shapes (25 with an unreferenced `65535` placeholder), 28 referenced bitmap ids = 28 JPEG3 outputs; byte-identical converter reruns additionally require the documented worktree line-ending forms of the `content_version` fingerprint inputs (README worktree-form note). Verifier observations O1–O4 accepted as non-blocking: perturbation is applied to the reference side (comparator is symmetric); reference and capture share placement resolution (cross-checked by loader tests, bounds oracle, and report assertions); building envelopes have no `fill_refs` field (placeholder fail-close covers them); the scope test scans `.gd`/`.tscn` while README/`verify.ps1` were grep-checked separately. Non-blocking follow-ups: unused `copy_tool` helper in `tools/endpoint-catalog/test_endpoint_catalog.py`; no dedicated OpenSpec verification workflow is installed — strict validation, independent verification, required checks, and final diff review are used as the fallback. Authentic progressed-player saves remain unavailable and unverified. `godot-compatibility-boot` verifier findings accepted as non-blocking: NIT-1 (the live boot phase asserts `state=ready` and the summary while the `connected` connection marker sits on the single path to `ready` — implication accepted, wording noted), NIT-3 (project display name still "Social Wars First Render" — cosmetic, deferred), NIT-4 (the guard set covers task 1.4's paths; `tools/hash-manifest/legacy-manifest.json`, `villages/`, `templates/` are not guarded but are proven unchanged by `git diff origin/main...HEAD`), O1 (capture-time guard evidence predates schema `guard-baseline-v2`, so capture-time before/after guard identity is not re-executable — disclosed in `tasks.md` 4.3 and the fixtures README; mitigated by the capture manifest's own pre/post containment snapshot and the capture's write set being disjoint from the guard set), O2 (the scope test necessarily excludes itself from its own token scan; its list sizes are asserted), O3 (repair `c54abe3` independently re-confirmed: guard verify after `verify.ps1` exits 0, first-render evidence zero diff). godot-content-registry verifier findings resolved: round-1 C1 (no sound lookup, building not exact-equality, stale `explo1` claim), C2 (passthrough SHA-256 clause unasserted), W1 (unparseable output not injected), W2 (stale `tasks 3.6` comment), W3 (proposal Impact drift) repaired in `1e7c891`/`65b2beb` and confirmed resolved in verifier round 2; W4 (this ledger) discharged here. Accepted non-blocking: the proposal-time “17 scenarios” count was a stale planning estimate corrected to the actual 18 during Apply; design D8 narrowed the EOL pins to the content package + `asset_ids.json` + `coverage.json` after the full asset suite proved M4's converter fingerprint requires the documented CRLF forms of `inspection.json`/`image_extraction.json` (30 tool files restored byte-for-byte, content identity re-proven against baseline blobs). `godot-session` verifier findings: PASS with 0 CRITICAL; W1 (claimed 48 vs the 46 committed boot-report assertions) and W2/N8 (mapping row 12 attribution, log-step wording) repaired in `c4fc993`, W3 (ledger deferral) discharged here, W4 (AGENTS does not list the standalone session-suite command) accepted under AGENTS' documented delegation of individual engine invocations to `apps/client-godot/README.md`; accepted non-blocking NOTEs: the `session_activate` fail-closed branch has no test (structurally unreachable — activation is the last step before ready), the rejection state-unchanged checks do not re-assert level/xp (validation returns precede every mutation), and re-activation-with-replacement is allowed by design D3 but untested. godot-game-clock verifier disposition: all findings repaired (W1/W2 delivered as executable checks in `14155b4`, N1/N2/N3/N6 prose in `14155b4`/`0b57ba0`, N4 audit clean, N5 discharged by this entry); disclosed unreachable boot branches (`gameclock_missing`, `gameclock_anchor`, `session_activate`) are unit-covered by direct anchor rejections per the archived `tasks.md` 5.2 and remain non-blocking; contract discovery recorded — a frame crossing several milliseconds emits exactly one `clock_ticked` carrying the new elapsed payload, not one per millisecond. `godot-ui-foundation` verifier findings accepted as non-blocking: NOTEs N1–N6 recorded under Change status (transient post-sync validate ambiguity, unrecorded symbol-pattern list behind the proposal count, indirect engine-default rationale, unasserted defensive copy of `slot_names()`, joint AGENTS/README satisfaction of R4’s command documentation, and the historical containment clauses in four earlier specs per D8). `town-vertical-slice` verifier disposition: the single CRITICAL C1 (the spec-required milestone record in this ledger) is discharged by the archive-stage ledger commit in PR #152; its INFOs are accepted as non-blocking (canonical LF report blob vs the expected worktree CRLF form under `core.autocrlf`; windowed handoff executed with the fake GameApi while `legacy_v0` is covered by the headless live phases and the handoff consumes post-bootstrap typed state; the compat-unittest `ERROR in app` line is the deliberate unhandled-failure test; report determinism recorded from task 8.3 rather than re-executed by the verifier; boot-report churn from the rerun committed as `45da61f`); `tasks.md` omitted a roadmap-ledger task line for the spec-required milestone record — recorded in the ledger instead of editing archived artifacts. `building-placement` verification disposition (2026-09-29): integration review (task 6.2) passed with strict validation exit 0 and both batteries re-run exit 0 in the final state — recorded as an orchestrator-run integration review rather than an independent-agent pass, per the fallback noted above (no dedicated OpenSpec verification workflow is installed); no CRITICAL or WARNING findings recorded. Claim-limit observations accepted as non-blocking by design: the price vector, envelope placeholders, and slot choice are derived-provisional (never Flash-observed); insufficient resources reproduce legacy clamping rather than rejection (deferred to Server v1 / M13); parity covers one recorded `buy` transaction against the fresh-player corpus only; no pixel-parity oracle exists; the committed windowed capture runs the fake GameApi, so real-execution parity rests on the fixture-replay tests and the `placement-live` phase. `tasks.md` carries an explicit integration-review record (task 6.2) listing these residual gaps alongside the still-open purchase and shop deliver line. Purchase-change observations (non-blocking): the legacy log line for `buy_stored_item_cash` reads "Bought … from unit collection" while the archived placement design grouped that command among the deferred stored/cash purchase flows, and the Flash call site is never observed — so both the command choice and the cash-only price derivation are derived-provisional claim limits, and no claim is made about resource-priced storage purchases (their candidate remains `store_add_items`, out of scope here). `compat_live_phase.py`'s save-mutation marker is labelled for the placement phase, so `verify-boot.ps1` matches that literal marker for both live phases with an explicit comment. The shop panel and the build picker are both right-anchored, so opening both surfaces at once would overlap them (cosmetic, provisional presentation; no player-facing trigger opens either surface yet — both are entered programmatically by the suites, captures, and reports). This checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing, not introduced by this change; the new purchase fixture is CRLF-in-blob, so its report is stable in any checkout). Move-change observations (non-blocking): the move command's argument values, the `frame`/`string` arguments the legacy branch reads and discards, and the **neutral** price vector are derived-provisional — the committed config records no move price anywhere (item `cost` and `cost_type` are dead fields over all 778 items, `costs` prices the purchase only, and no global holds a move cost), so the service claims neither that moving is free in the legacy client nor that it costs anything, and the price is a derivation boundary rather than a behavior claim. Occupancy, the no-op cell, and grid bounds are client-side display rules only; an out-of-bounds or overlapping target would be accepted by the service if a client sent one, since authoritative validation belongs to Server v1 (M13). A placement whose legacy map key is not a positive integer is deliberately unaddressable (never coerced, because 0 names a real row). The three live phases all match the save-mutation marker the harness prints, which is labelled for the placement phase, and the `apps/compat-api/run.py` startup banner still lists only `POST /v0/place` — cosmetic, pre-existing, and the full endpoint surface is documented in both READMEs. The placement, shop, and move surfaces are all right-anchored, so opening two at once would overlap them (provisional presentation; only one is reachable per flow). This checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing; the purchase and move fixtures are CRLF-in-blob, so their reports are stable in any checkout). Sell-change observations (non-blocking): the derived sell reason and the **neutral** price vector are derived-provisional, and the change therefore **claims no refund at all** — the committed configuration records no building-sale refund rule (item `cost` and `cost_type` are dead fields over all 778 items, `costs` prices the purchase only, and `MARKET_SELL_PERCENTAGE` governs the *resource* market — evidenced by the SWF's "SELL 100 WOOD ON MARKET" strings), the legacy refund travels only in client-sent deltas this contract refuses, and refund economics belong to Server v1 (M13) and the later *resources* line. The legacy combat `KILL` reason is unreachable because the endpoint accepts no reason (the `invalid_reason` code is server-side-only). Sellability and addressability are client-side rules only. The sell mode shares the delivered selection-driven surface, so `confirm_sell()` adds a local `sell_selection_changed` refusal and `arm_move()` a `sell_already_active` guard, both unreachable in the delivered move flow — `test_town_move.gd` and the rest of the battery stay green. The apply's rollback branch is reachable only through a rejected HUD re-attach and is verified by review rather than fault injection, the same structural gap the delivered placement, purchase, and move applies share. Cosmetic and pre-existing: the placement, shop, and move/sell surfaces are right-anchored (opening two at once would overlap them), the live-phase save-mutation marker is labelled for the placement phase, and the `apps/compat-api/run.py` startup banner still lists only `POST /v0/place`. This checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing; the purchase, move, and sell fixtures are CRLF-in-blob, so their reports are stable in any checkout). Store-change observations (non-blocking): the command's argument value and the **neutral** price vector are derived-provisional, and the change therefore **claims no storing cost and no capacity rule** — the committed configuration records no storing price (item `cost` and `cost_type` are dead fields, `costs` prices the purchase only) and the legacy catalog records no capacity check. The `store_item` branch deliberately does **not** write `boughtUnits` (unlike `buy`, `place_stored_item`, and `buy_stored_item_cash`) and the change reproduces that exactly rather than "fixing" it. This line only moves a building *into* storage, so stored items are **not yet playable**: `place_stored_item` (storage to map) and `sell_stored_item` remain open legacy commands and are the natural next storage candidate. The selection-driven surface now carries three mutually exclusive modes (move, sell, store), so arming one refuses the others and a selection change during a targetless confirm refuses the send; the delivered suites prove the earlier modes are unchanged. The applies' rollback branches are reachable only through a rejected HUD re-attach and are verified by review rather than fault injection, the same structural gap every delivered apply shares. Cosmetic and pre-existing: the surfaces are right-anchored, the live-phase save-mutation marker is labelled for the placement phase, and the `apps/compat-api/run.py` startup banner still lists only `POST /v0/place`. This checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing; the purchase, move, sell, and store fixtures are CRLF-in-blob, so their reports are stable in any checkout). Upgrade-change observations (non-blocking): the two-command pair is **derived** — that the Flash client sends exactly this `sell`+`buy` batch is never observed — while its shape, the `UPGR` reason, the key/cell reuse, the forced order, and the resulting state are **established** by committed source and executed-legacy capture, and that split is now recorded in the fixture README, the manifest, the service and client READMEs, and the report's own provenance section. The decisive design constraint is that legacy answers `{"result":"success"}` for the **reverse** order while leaving the key absent, so the endpoint's three-fact post-execution proof is load-bearing rather than decorative — this is now also committed as a **negative oracle** in the fixture manifest and re-derived offline through the real legacy `command()` in a disposable corpus. The client deliberately does **not** implement three legacy-client rules that exist in static evidence: the level gate, the daily-upgrade limit (`numUpgradesToday`, `lastUpgrades/`, `upgradeDateString`), and the space check; the level gate is the consequential one and is inexercisable on the committed corpus (`maps[0].level` is 1, and the single config pair whose next tier is at or below level 1 — Silo II → "Chained Revolution Bonus 99" — has its source unplaced), so enforcing it would make this line unreachable on the corpus the project preserves; it is recorded as an explicit follow-up. The upgraded building arrives **unfinished**: `map_add_item` seeds `{"nc": 0}` for items with `clicks_to_build > 0`, and nothing consumes it here — the construction-timers deliver line, already scoped in the next-objective line, owns the `activate` / click family and `UPGRADE_SPEEDUP_PRICING`. The client also does not carry `boughtUnits`: the response does not report it and the legacy record is deduplicated (`engine.py:86-89`), so the report records the fixture's fact rather than the client inventing a list. The upgrade apply rebuilds the object node rather than mutating it, because `town_object.gd` is outside the change's ownership and exposes no re-render entry point; the replacement lands at the same index, cell, and depth position and the old node is detached only at the last fallible step. Cosmetic and pre-existing: the surfaces are right-anchored, the live-phase save-mutation marker in `compat_live_phase.py` is labelled for the placement phase, the `apps/compat-api/run.py` startup banner still lists only `POST /v0/place`, and the shared 300 px panel width clips long tier names in the capture. This checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing; the purchase, move, sell, store, and upgrade fixtures are CRLF-in-blob, so their reports are stable in any checkout). Construction-change observations (non-blocking): the three commands and the start duration are **derived** — that a real construction sends `activate` / `add_click` / `activate_item_click`, and that the duration is the item's committed `build_time` rather than its `activation` field or a speedup-adjusted figure — while their shapes, effects, the purchase-side seeding, the countdown's recorded shape, and the absence of a server-side completion rule are **established**, and that split is now recorded in the fixture README, the manifest, the service and client READMEs, and the report's own provenance section. This line has the strongest intent discipline so far: the start duration is derived from committed content, so no client value can influence the countdown, and the per-action post-execution proof makes the endpoint's success a real claim rather than legacy's word — the same lesson the upgrade line learned when legacy answered success for a batch that deleted the building. **No building cost is claimed**: every action carries the neutral derived vector, no configuration field prices a build, and the three speedup prices (`BUILD_SPEEDUP_PRICING`, `BUILD_SPEEDUP_MIN_TIME`, `UPGRADE_SPEEDUP_PRICING`) are out of scope — the investigation record had named only the third, which the Apply stage corrected. Friend assistance (`buy_si_help` / `finish_si` / the `attr["si"]` bag) and construction speedups are explicitly out of scope, and the `activate` branch that clears the whole attribute bag is never used, so the flow offers **no cancel** at all. One genuine ambiguity is recorded rather than hidden: a finished build and a freshly started one are the **same row shape** (`{"cp": N}`), because the completing command deletes the counter and the purchase half only ever seeds it, so the flow offers no step in-session for a row this client finished and a finished build can be clicked again after a view rebuild — which is exactly what the legacy `add_click` permits whenever the counter is absent. The `no_build_time` refusal is exercised through an in-memory row because no placed building in the committed corpus has a non-positive committed build time, and the fixture's completing command is recorded but not captured (the two-command form leaves both the countdown and the counter visible in the after-state, which is why it was chosen). The upgrade row's seeded `{"nc": 0}` is deliberately **not** consumed here, because that would re-derive the upgrade contract inside a second change; the counter's origin is covered by the suite over the delivered upgrade fixture and the story is named as an explicit follow-up. Cosmetic and pre-existing: the surfaces are right-anchored and the shared panel width clips long labels, the live-phase save-mutation marker in `compat_live_phase.py` is labelled for the placement phase, the `apps/compat-api/run.py` startup banner still lists only `POST /v0/place`, and this checkout's `core.autocrlf=true` leaves the committed `godot-building-placement` fixture files CRLF on disk while `evidence/placement/report.json` records LF-blob digests, so re-running the placement report step locally rewrites three digests (pre-existing; the later fixtures are CRLF-in-blob, so their reports are stable in any checkout).
- **Last OpenSpec validation:** PASS — `building-xp` archive stage (2026-09-30): after the move `openspec list` reports "No active changes found." and `openspec validate --all --strict` reports 48 passed / 0 failed, and at Sync (before the move) 49/49; change strict validation passed at Propose and at the integration review. This completes the sync of all eleven M7 lines' specs. The archive ran with `--skip-specs` because the Sync stage had already applied the deltas — without it, archive correctly aborts with "already exists" and changes no files. This is not the unavailable dedicated verification workflow
- **Last implementation verification:** Integration review over `building-xp`, followed by the same battery re-run in the final state by the root — orchestrator-run, not an independent agent (fallback noted under Blocking issues). Actually executed by the root: `openspec validate building-xp --strict` exit 0; `verify.ps1` PASS exit 0; `verify-boot.ps1` PASS exit 0 (**27 hermetic suites** including `test_town_xp` 767 checks, **13 live phases** including `level-up-live` green, guard digest `6978b959…ff348` pre=post, port released, no working-tree `saves/`); `hash_manifest.py verify` exit 0 (3,258 entries); compat discovery `Ran 1109 tests ... OK`. The root independently re-read the committed `xp-report-v1` (provenance split, `zero-based` rejected alternative, the corpus contradiction quoted, and `reward.paid: false` / `reward.displayed: false`) and **corrected an error the Apply stage surfaced in my own investigation record** — the `Conqueror` saturation level was a zero-based position in a curve whose index base is one-based, so it is one-based level **45**, not 49. The requirement-to-evidence map, the two honest consequences of the corpus already being at its derived level, the accepted worker deviations, and the residual gaps are recorded in the tasks.md integration-review record. Prior: the ten earlier M7 integration reviews, and the `town-vertical-slice` independent verification (2026-09-28) VERDICT FAIL on exactly C1, discharged by the ledger commit in PR #152
- **Last verified commit:** `cc77b90` — the Apply-tree tip the final-state battery executed on for `building-xp` (the following commit `d04766d` recorded the documentation and integration review; Apply PR #200 merged as `4fffe05`); prior: `7163311` for `building-resources` (PR #195 merged as `1eb3d57`), `2a3516f` for `building-expand` (PR #190 merged as `974bd15`), `8121e37` for `building-collect` (PR #185 merged as `fa88a99`), `fabbb58` for `building-construction`, `8d15315` for `building-upgrade`, `120b343` for `building-store`, `77abfd0` for `building-sell`, `7c4390b` for `building-move`, `b341904` for `building-purchase`, `742f594` for `building-placement`, then `3f3406c` the archive-stage tree the independent M6 verification batteries executed on
- **Last updated:** 2026-10-01

### Status values

`BOOTSTRAP` → `EXPLORING` → `PROPOSED` → `IMPLEMENTING` → `VERIFYING` → `VERIFIED` → `ARCHIVED`

Exceptional state:

`BLOCKED`

<!-- ORCHESTRATOR_STATUS_END -->

---

# 1. Final Strategic Direction

The reconstruction should proceed through three major architectural stages.

## Stage A — Preserve the Current Implementation

```text
Flash Client
    │
    │ SWLoader.swf
    │ Basesec_*.swf
    │ FlashVars
    │ Legacy HTTP / form requests / AMF-era behavior
    ▼
Legacy Flask Server
    │
    ├── server.py
    ├── command.py
    ├── sessions.py
    ├── engine.py
    ├── get_player_info.py
    └── get_game_config.py
    │
    ▼
JSON Save Files
```

This implementation remains operational as the **behavioral oracle**.

Do not dismantle it during the first stages of development.

---

## Stage B — Flash-Free Compatibility Architecture

The first major target architecture should be:

```text
Godot Client
    │
    │ Modern JSON API
    ▼
Compatibility API v0
    │
    │ translates modern requests
    │ into legacy semantics
    ▼
Legacy Game Logic
    │
    ▼
JSON Save Files
```

At this stage:

- Flash Player is no longer required.
- The Godot client does not execute SWFs.
- The user can play through the modern client.
- Existing game behavior is preserved.
- Existing saves can still be loaded.
- Existing Python logic remains the behavioral reference.
- PostgreSQL is not yet required.
- Public account infrastructure is not yet required.

This should be achieved **before rewriting the backend**.

---

## Stage C — Production Architecture

The eventual production architecture becomes:

```text
Godot Client
    │
    │ HTTPS / JSON
    │ WebSocket only where justified
    ▼
Server API v1
    │
    ├── Authentication
    ├── Town Domain
    ├── Economy Domain
    ├── Buildings Domain
    ├── Units Domain
    ├── Inventory Domain
    ├── Research Domain
    ├── Quest Domain
    ├── Collections Domain
    ├── Missions Domain
    ├── Combat Domain
    └── Social Domain
    │
    ▼
PostgreSQL
    │
    ├── durable player state
    ├── transaction ledger
    ├── progression
    ├── missions
    ├── social state
    └── migration metadata
```

Optional infrastructure can later include:

```text
Redis
WebSockets
Admin tooling
Metrics
Job processing
CDN
```

These should only be introduced when they solve a demonstrated problem.

---

# 2. Non-Negotiable Engineering Principles

These rules should guide the entire reconstruction.

## 2.1 Preserve Before Replacing

Never remove or rewrite legacy behavior until its behavior has been:

1. observed,
2. documented,
3. recorded,
4. tested,
5. reproduced by the replacement.

---

## 2.2 Do Not Delete Original Data

Never destroy:

- SWFs
- JSON configuration
- existing saves
- images
- sounds
- XML files
- game configuration
- protocol examples
- legacy server code

Move them later into archival directories if necessary, but preserve their original versions.

---

## 2.3 Preserve Git History

When reorganizing files, use:

```bash
git mv
```

rather than deleting and recreating files whenever practical.

---

## 2.4 Do Not Redesign Gameplay During Parity Work

The reconstruction phase is not the time to rebalance the game.

Avoid changing:

- resource costs,
- XP rewards,
- building times,
- combat formulas,
- quest requirements,
- unit stats,
- progression pacing,
- unlock requirements.

First reproduce the existing game.

Improvements can happen later.

---

## 2.5 Never Rewrite Client and Server Semantics Simultaneously

A dangerous migration would be:

```text
Flash → Godot
Flask → completely different server
JSON saves → PostgreSQL
Legacy protocol → new protocol
```

all at once.

That would make behavioral regressions extremely difficult to diagnose.

Instead:

```text
Preserve server
    ↓
Replace client
    ↓
Verify parity
    ↓
Replace server internals
    ↓
Verify parity again
```

---

## 2.6 Every Migrated Feature Needs a Legacy Fixture

Before replacing a feature, capture examples of:

```text
request
before state
response
after state
```

These become golden-master tests.

---

## 2.7 Preserve Legacy IDs

Existing IDs used by:

- buildings,
- units,
- items,
- quests,
- research,
- collections,
- missions,
- effects,
- animations,
- assets

should remain stable.

The production database may use internal primary keys, but original IDs should be stored as:

```text
legacy_id
```

where appropriate.

---

## 2.8 Production Server Owns the Truth

The future server must be authoritative.

The client sends **intent**, not final state.

Bad:

```json
{
  "coins": 999999,
  "xp": 10000
}
```

Good:

```json
{
  "building_id": "barracks_01",
  "x": 24,
  "y": 17
}
```

The server determines:

```text
Is the building unlocked?
Does the player have enough resources?
Is placement valid?
What does it cost?
How much XP is awarded?
When does construction finish?
What state should be written?
```

---

## 2.9 SWF Files Become Archival References

The final runtime must not rely on:

- Adobe Flash Player
- Ruffle
- ActionScript runtime
- SWLoader.swf
- Basesec SWFs
- sprite SWFs
- FX SWFs
- AMF
- FlashVars

SWFs may remain inside:

```text
legacy/
```

for preservation and reference.

They must not be required by the final game runtime.

---

# 3. Legacy Component Classification

The existing repository should be classified before significant restructuring.

| Component | Strategy | Purpose |
|---|---|---|
| `server.py` | KEEP + FREEZE | Legacy HTTP behavior oracle |
| `sessions.py` | KEEP → REWRITE LATER | Save/session semantics |
| `command.py` | KEEP + DECOMPOSE | Primary game behavior specification |
| `engine.py` | AUDIT + EXTRACT | Reusable calculations where possible |
| `get_game_config.py` | KEEP + NORMALIZE | Content/configuration source |
| `get_player_info.py` | KEEP → REPLACE | Player bootstrap behavior |
| AMF/form protocol | LEGACY ONLY | Compatibility/reference |
| `templates/play.html` | ARCHIVE | Flash bootstrap |
| `SWLoader.swf` | ARCHIVE | Flash loader |
| `Basesec_*.swf` | ARCHIVE | Legacy client implementation |
| PNG/JPG assets | KEEP | Direct reusable content where legally permitted |
| MP3/audio assets | KEEP/CONVERT | Runtime audio source |
| SWF sprites | CONVERT | Godot-compatible assets |
| SWF effects | CONVERT/RECREATE | Godot effects |
| JSON game config | KEEP + VALIDATE | Canonical content source |
| JSON saves | KEEP + MIGRATE | Golden fixtures and migration source |

---

# 4. Target Repository Structure

Do not immediately restructure everything.

During early development the repository can gradually move toward:

```text
social-wars-legacy/
├── apps/
│   ├── client-godot/
│   ├── compat-v0/
│   └── server-v1/
│
├── packages/
│   └── game-content/
│       ├── raw/
│       ├── normalized/
│       ├── schemas/
│       └── generated/
│
├── tools/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── asset-pipeline/
│   ├── content-builder/
│   └── save-migrator/
│
├── tests/
│   ├── fixtures/
│   ├── golden/
│   ├── saves/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── legacy/
│   ├── server/
│   ├── flash/
│   ├── assets/
│   └── saves/
│
└── README.md
```

Initially keep the existing structure intact.

Move legacy components only after the migration tooling and modern directories are established.

---

# 5. Phase 0 — Freeze and Preserve the Legacy Baseline

## Objective

Create a reproducible snapshot of the working legacy implementation before modifying architecture.

---

## Tasks

Create a Git tag:

```bash
git tag legacy-baseline
```

Document:

- Python version
- dependency versions
- operating system requirements
- startup procedure
- default ports
- required environment configuration
- directory expectations
- Flash client startup flow
- default player/save
- known bugs
- known broken features
- known incomplete features
- asset versions
- EXT_VERSION or equivalent content version
- expected URLs
- expected game bootstrap process

---

## Create Asset Hash Manifest

Generate SHA-256 hashes for:

```text
*.swf
*.json
*.xml
*.png
*.jpg
*.jpeg
*.mp3
*.wav
*.gif
```

Example:

```json
{
  "path": "assets/flash/SWLoader.swf",
  "sha256": "...",
  "size": 123456
}
```

This provides a permanent record of the original artifact set.

---

## Create Canonical Save Fixtures

Preserve multiple representative saves.

Recommended fixtures:

```text
tests/saves/fresh-player.json
tests/saves/early-game.json
tests/saves/mid-game.json
tests/saves/late-game.json
tests/saves/stress-town.json
```

Try to include:

### Fresh Player

- tutorial state
- starter buildings
- starter units
- starter currencies

### Early Game

- construction
- basic unit queues
- first quests

### Mid Game

- research
- collections
- larger inventory
- multiple zones

### Late Game

- advanced unlocks
- missions
- high-level buildings
- advanced units

### Stress Town

- dense town
- many buildings
- many units
- many queued operations
- large inventory

---

## Deliverables

```text
docs/legacy-baseline.md
docs/known-legacy-bugs.md
tests/saves/
tools/hash-manifest/
legacy-manifest.json
```

---

## Exit Criteria

The legacy game can be reproduced from a clean environment using documented instructions.

---

# 6. Phase 1 — Build the Legacy Protocol Recorder

This is one of the most important phases of the entire project.

## Objective

Turn the legacy implementation into an observable behavioral specification.

---

## Capture

For every request:

```text
timestamp
endpoint
HTTP method
request body
parsed command
player ID
session ID where appropriate
state before
response
state after
HTTP status
execution duration
```

---

## Important Rule

Instrumentation must not change behavior.

The recorder should observe the legacy system, not rewrite it.

---

## Golden Fixture Structure

Example:

```text
tests/golden/building-buy/
├── request.json
├── before.json
├── response.json
└── after.json
```

Other fixture examples:

```text
tests/golden/building-move/
tests/golden/unit-order/
tests/golden/collect-income/
tests/golden/start-research/
tests/golden/claim-quest/
tests/golden/mission-attack/
```

---

# 7. Build an Exhaustive Legacy Command Catalog

`command.py` is effectively a major portion of the existing game specification.

Create:

```text
docs/legacy-protocol/commands.md
```

or preferably a machine-readable catalog plus generated documentation.

Each command should include:

```text
Command name
Domain
Endpoint
Required parameters
Optional parameters
State read
State modified
Resources consumed
Rewards produced
Timers created
Dependencies
Client-trusted fields
Security concerns
Observed fixtures
Replacement API
Migration status
```

---

## Suggested Status Values

```text
UNOBSERVED
CAPTURED
DOCUMENTED
V0_SUPPORTED
V1_SUPPORTED
PARITY_VERIFIED
RETIRED
OUT_OF_SCOPE
```

---

## Example

```yaml
command: buy
domain: buildings
status: CAPTURED

inputs:
  - building_id
  - x
  - y

reads:
  - player.resources
  - player.level
  - town.objects
  - town.zones

writes:
  - player.resources
  - town.objects
  - player.xp

security:
  legacy_client_trust: high

replacement:
  endpoint: POST /v1/towns/me/buildings
```

---

# 8. Phase 2 — Define the Canonical Domain Model

Before building extensive modern code, define the conceptual game model.

Core domain objects should include:

```text
Player
Town
Map
Zone
TownObject
Building
Decoration
Unit
UnitInstance
Resource
InventoryItem
InventoryStack
ProductionQueue
Research
Quest
QuestObjective
Collection
Mission
Battle
Friend
Visit
Reward
Event
ContentDefinition
```

---

# 9. Separate Definitions From Player State

This distinction is extremely important.

## Definition Data

Shared static game content:

```text
Barracks
cost = 500 coins
build_time = 60
footprint = 3x3
required_level = 5
```

---

## Player Instance State

Player-owned object:

```text
instance_id = 8937
definition_id = barracks
x = 24
y = 17
level = 2
construction_ready_at = ...
```

Never merge these concepts.

Use patterns similar to:

```text
BuildingDefinition
BuildingInstance

UnitDefinition
UnitInstance

QuestDefinition
QuestProgress
```

---

# 10. Phase 3 — Build Canonical Game Content

Create a normalized content package.

```text
packages/game-content/
├── raw/
├── normalized/
│   ├── buildings.json
│   ├── units.json
│   ├── items.json
│   ├── quests.json
│   ├── research.json
│   ├── collections.json
│   └── missions.json
├── schemas/
│   ├── building.schema.json
│   ├── unit.schema.json
│   ├── quest.schema.json
│   └── ...
├── generated/
└── manifest.json
```

---

## Requirements

Every content definition should preserve:

```text
legacy_id
source
content version
asset references
dependencies
```

---

## Validate Content

The content builder should detect:

```text
duplicate IDs
unknown references
missing assets
invalid costs
invalid requirements
broken quest dependencies
broken research dependencies
missing unit references
missing building references
missing reward references
```

---

# 11. Phase 4 — Build the SWF Asset Migration Pipeline

Do not manually convert assets without tracking them.

Create a central asset registry.

---

## Asset Registry Fields

Each asset should track:

```text
source SWF
source hash
symbol/class name
legacy asset ID
category
dimensions
registration point
pivot
frame count
frame rate
frame labels
nested MovieClips
masks
blend modes
color transforms
filters
scale grids
ActionScript dependencies
output path
Godot resource
conversion status
notes
```

---

## Example

```yaml
legacy_id: building_barracks_01

source:
  file: assets/sprites/buildings.swf
  symbol: Barracks01

type: building

dimensions:
  width: 270
  height: 220

registration:
  x: 135
  y: 198

animation:
  frames: 12
  fps: 24

conversion:
  status: converted
  output: assets/runtime/buildings/barracks_01/
```

---

# 12. Preserve Important Flash Rendering Semantics

Asset conversion can easily become visually incorrect if these are ignored:

- registration points
- pivots
- nested MovieClips
- masks
- alpha
- color transforms
- blend modes
- shadows
- glow filters
- scale grids
- tween timing
- frame labels
- transform inheritance
- morph animations
- ActionScript-controlled states

These should be documented per asset where relevant.

---

# 13. Asset Conversion Mapping

Recommended mappings:

| Legacy Asset | Modern Replacement |
|---|---|
| Static bitmap | PNG / WebP |
| Vector icon | SVG or rasterized texture |
| Simple MovieClip | SpriteFrames |
| Complex animation | AnimationPlayer |
| Unit animation | AnimatedSprite2D / AnimationPlayer |
| UI panel | TextureRect / NinePatchRect |
| Flash scale-grid UI | NinePatchRect |
| MovieClip hierarchy | Godot scene |
| Flash particle effect | GPUParticles2D |
| Complex FX | Godot shader / scene animation |
| MP3 | OGG/WAV |
| Flash button | Godot Control/Button scene |

---

## Asset Directory Separation

Never overwrite original assets.

Use:

```text
assets/raw/
assets/converted/
assets/runtime/
```

or equivalent.

---

# 14. Asset Conversion Priorities

Do not attempt to convert every asset before the game runs.

Suggested order:

```text
1. Terrain
2. One building
3. One unit
4. Essential HUD
5. Selection indicators
6. Placement grid
7. Common buildings
8. Common units
9. Common UI
10. Combat effects
11. Missions
12. Rare content
13. Special events
```

---

# 15. Phase 5 — Initialize the Godot Client

Use a pinned stable Godot 4.x version.

Document it in:

```text
apps/client-godot/README.md
```

---

## Recommended Language

Use **GDScript initially** unless there is a strong reason to use C#.

Reasons:

- quickest Godot iteration
- excellent engine integration
- simpler deployment
- appropriate for UI-heavy and scene-heavy work
- easier contributor setup

C# can still be introduced later for specific systems if justified.

---

# 16. Suggested Godot Structure

```text
apps/client-godot/
├── project.godot
│
├── scenes/
│   ├── boot/
│   ├── town/
│   ├── buildings/
│   ├── units/
│   ├── missions/
│   └── ui/
│
├── scripts/
│   ├── core/
│   ├── networking/
│   ├── domain/
│   └── utils/
│
├── assets/
│
└── tests/
```

---

# 17. Godot Autoloads

Keep global singletons limited.

Potential autoloads:

```text
App
GameApi
Session
ContentRegistry
GameClock
Settings
AudioManager
```

Avoid creating a giant global `GameManager` containing every system.

---

# 18. Critical GameApi Abstraction

The Godot UI should never directly know about:

```text
command.php
AMF
FlashVars
form encoding
legacy URLs
legacy command names
```

Create an abstraction such as:

```gdscript
class_name GameApi
```

with operations similar to:

```text
get_bootstrap()
get_player()
get_town()

buy_building()
move_building()
sell_building()
upgrade_building()
collect_building()

order_unit()
cancel_unit_order()
collect_unit()

start_research()
cancel_research()
claim_research()

start_quest()
claim_quest()

start_mission()
attack_target()
```

---

## Initial Implementation

```text
LegacyV0Api
```

Later:

```text
ServerV1Api
```

The rest of Godot should not care which implementation is active.

---

# 19. Phase 5.5 — Compatibility API v0

Create a modern-facing API in front of the legacy server.

For example:

```http
POST /v0/buildings/buy
```

Request:

```json
{
  "building_id": "barracks",
  "x": 24,
  "y": 17
}
```

Internally:

```text
Compatibility API
    ↓
translate request
    ↓
legacy command semantics
    ↓
legacy response
    ↓
normalize
    ↓
Godot response
```

---

## Benefits

Godot never needs to implement:

```text
legacy form encoding
command.php specifics
Flash-oriented request structures
AMF
FlashVars
```

When Server v1 arrives, only the API implementation changes.

---

# 20. Phase 6 — First Flash-Free Vertical Slice

This is the first major development target.

Do not wait for full game parity.

---

## Required Flow

```text
Launch Godot
    ↓
Connect to compatibility server
    ↓
Load game configuration
    ↓
Load player
    ↓
Load town
    ↓
Render terrain
    ↓
Render buildings
    ↓
Render at least one unit
    ↓
Display HUD resources
    ↓
Allow camera movement
    ↓
Allow object selection
```

---

## Vertical Slice Requirements

### Bootstrap

Implement:

```text
configuration loading
player loading
town loading
content registry
session initialization
```

---

### Town Renderer

Implement:

```text
isometric grid
grid-to-screen conversion
screen-to-grid conversion
camera movement
zoom
town bounds
depth sorting
object footprint handling
selection
HUD
```

---

### First Building

Convert one real building.

Support:

```text
load
render
select
move
```

---

### First Unit

Convert one real unit.

Support:

```text
load
render
idle animation
select
```

---

# 21. First Major Gate

The following must work on a machine with:

```text
NO Adobe Flash
NO Ruffle
NO Flash plugin
NO ActionScript runtime
```

Godot should:

```text
launch
load an existing save
load game content
render town terrain
render buildings
render units
render HUD
pan camera
zoom camera
select objects
```

Once this works, the reconstruction has passed its first critical milestone.

---

# 22. Phase 7 — Building System Parity

Implement building functionality in dependency order.

```text
1. Load existing town objects
2. Select objects
3. Placement preview
4. Grid validation
5. Buy building
6. Construction
7. Move
8. Flip / rotate where applicable
9. Store
10. Restore
11. Upgrade
12. Sell
13. Remove
14. Unlock zones
15. Clear obstacles
16. Collect resources
```

---

# 23. Placement System Requirements

The town grid must properly understand:

```text
multi-tile footprints
town bounds
locked zones
occupied tiles
collision rules
placement previews
object pivots
base tile positions
selection hitboxes
orientation
depth sorting
```

Do not use texture dimensions as gameplay footprint dimensions.

A large image may occupy only a small number of logical tiles.

---

# 24. Isometric Coordinate Tests

Create automated tests for:

```text
grid → screen
screen → grid
negative coordinates
boundary coordinates
large coordinates
multi-tile footprints
camera transformations
zoom transformations
```

This logic will affect almost every town interaction.

---

# 25. Phase 8 — Economy and Timer Systems

Reconstruct:

```text
coins
resources
premium currency
XP
building income
production
construction
cooldowns
collections
rewards
```

---

# 26. Server-Based Timer Model

Never trust the client clock.

Server responses should include:

```json
{
  "server_time": 1789257600,
  "ready_at": 1789257900
}
```

The client computes a server offset.

---

## Persist Timers As State

Prefer:

```text
started_at
duration
ready_at
```

over creating one background worker for every timer.

---

# 27. Economy Invariants

Create tests such as:

```text
resource balances never become invalid
premium currency cannot be duplicated
purchases cannot execute without sufficient resources
rewards cannot be claimed twice
collect cannot execute before timer completion
client clocks cannot skip timers
```

---

# 28. Economy Ledger

For the production server, important currency mutations should create ledger entries.

Example fields:

```text
player_id
resource
amount
reason
related_entity
balance_before
balance_after
timestamp
request_id
```

This is especially important for:

```text
premium currency
quest rewards
mission rewards
admin grants
migration adjustments
purchases
```

---

# 29. Phase 9 — Inventory and Crafting

Implement:

```text
load inventory
add item
remove item
buy item
consume item
store item
activate item
deactivate item
craft
recycle
expiry
gift-related inventory behavior
```

---

## Inventory Invariants

```text
quantity >= 0
cannot consume missing item
cannot claim reward twice
crafting inputs removed atomically
crafting output added atomically
unknown definitions rejected or preserved during migration
```

---

# 30. Phase 10 — Unit Systems

Separate:

```text
UnitDefinition
UnitInstance
```

---

## Unit Definition

Contains shared data such as:

```text
unit type
health
damage
movement speed
animation references
production time
cost
unlock requirements
```

---

## Unit Instance

Contains:

```text
instance ID
definition ID
current health
position
state
energy
temporary effects
```

---

## Reconstruct

```text
unit loading
production
queues
queue cancellation
queue collection
town movement
idle animation
walking animation
attack animation
damage
death
energy
revive
healing
special behaviors
```

---

# 31. Phase 11 — Player Progression

Implement:

```text
XP
levels
level rewards
unlocks
tutorial state
objectives
challenges
progress flags
```

---

## Server Owns Unlock Logic

Do not simply trust:

```text
client says player reached level X
```

Server calculates progression.

---

# 32. Phase 12 — Quest System

Model quests explicitly.

Example:

```text
QuestDefinition
├── prerequisites
├── objectives
└── rewards

QuestProgress
├── state
├── objective progress
├── started_at
└── completed_at
```

---

## Objective Types

Potential objective types:

```text
build
upgrade
collect
produce
own
spend
earn
mission
combat
research
craft
visit
help
level
```

Do not hardcode every quest as custom logic if generic objective types can represent it.

---

# 33. Phase 13 — Research System

Implement:

```text
research definitions
requirements
prerequisites
research costs
research timers
start research
cancel research
complete research
unlock effects
```

Completed research must remain permanently recorded.

---

# 34. Phase 14 — Collection System

Model separately:

```text
CollectionDefinition
CollectionProgress
CollectionReward
```

Support:

```text
item acquisition
collection progress
collection completion
reward claim
```

Reward claiming must be transactional and one-time.

---

# 35. Phase 15 — Missions and Combat

Start by reproducing compatibility behavior.

Later transition combat to server authority.

---

## Bad Combat API

```json
{
  "target_hp": 0,
  "reward": 500
}
```

This trusts the client.

---

## Correct Combat Intent

```json
{
  "attacker_id": "unit-123",
  "target_id": "enemy-456",
  "action": "attack"
}
```

Server determines:

```text
attacker exists
target exists
mission active
attacker alive
target alive
range valid
cooldown valid
energy valid
damage amount
critical result
death result
reward result
```

---

# 36. Prefer Deterministic Action-Based Combat

Social Wars does not necessarily require MMO-style server simulation.

A simpler model:

```text
initial state
+
player action
+
game rules
=
result
+
state mutation
+
combat event
```

The Godot client animates the server result.

This makes:

```text
testing
replay
anti-cheat
debugging
migration
```

significantly easier.

---

# 37. Combat Event Log

Eventually record events such as:

```text
mission_id
action_number
attacker
target
action_type
damage
critical
status_effect
resulting_hp
timestamp
```

Useful for:

```text
debugging
replay
analytics
anti-cheat
support
```

---

# 38. Phase 16 — Social Systems

Reconstruct:

```text
friends
friend scores
visits
visit rewards
help mechanics
neighbor mechanics
leaderboards
social rewards
```

The production server must own social relationship state.

---

# 39. Phase 17 — Special and Rare Legacy Systems

`command.py` contains behavior outside the main town loop.

Examples that should be explicitly audited include:

```text
SOC/event systems
temporary events
rider mechanics
penguin mechanics
dive mechanics
superspy mechanics
rage mechanics
hero mechanics
special powers
temporary items
special crafting
special buildings
event progression
event-specific currencies
```

These should not block the first playable modern client.

However, each one must eventually receive one of:

```text
IMPLEMENTED
PARITY_VERIFIED
OUT_OF_SCOPE
RETIRED
```

Do not silently forget them.

---

# 40. Phase 18 — Begin Server API v1

Only begin this stage when the Godot client is substantially functional through Compatibility API v0.

---

# 41. Recommended Production Backend Stack

Because the existing game logic is Python, a practical target is:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
Pytest
```

Optional later:

```text
Redis
background jobs
WebSockets
```

---

## Why Not Immediately Rewrite to NestJS?

A NestJS rewrite would simultaneously introduce:

```text
new language
new framework
new architecture
new persistence model
new game client
```

without materially helping the reconstruction.

Keeping Python initially allows legacy algorithms and knowledge to be migrated incrementally.

NestJS remains viable if there is a strong organizational reason to standardize on TypeScript.

---

# 42. Server v1 Domain Structure

Example:

```text
apps/server-v1/
├── api/
│   └── v1/
│
├── domain/
│   ├── players/
│   ├── towns/
│   ├── economy/
│   ├── buildings/
│   ├── units/
│   ├── inventory/
│   ├── research/
│   ├── quests/
│   ├── collections/
│   ├── missions/
│   ├── combat/
│   └── social/
│
├── services/
├── repositories/
├── infrastructure/
├── migrations/
└── tests/
```

---

# 43. Do Not Recreate `command.py`

The giant legacy command dispatcher should not become:

```text
/v1/command
```

forever.

Replace it with domain-oriented APIs.

Examples:

```http
GET /v1/bootstrap

GET /v1/towns/me

POST /v1/towns/me/buildings

POST /v1/towns/me/buildings/{id}/move

POST /v1/towns/me/buildings/{id}/upgrade

POST /v1/towns/me/buildings/{id}/collect

POST /v1/units/queues

DELETE /v1/units/queues/{id}

POST /v1/research/{id}/start

POST /v1/quests/{id}/claim

POST /v1/missions/{id}/start

POST /v1/missions/{id}/actions
```

---

# 44. Authoritative Server Rule

The legacy implementation may trust client-provided state changes.

The production implementation must not.

For example:

```text
Client:
"Build Barracks at tile 24,17"
```

Server:

```text
1. Load player state.
2. Load building definition.
3. Validate player level.
4. Validate unlock.
5. Validate prerequisites.
6. Validate town zone.
7. Validate placement.
8. Validate resource balance.
9. Calculate price.
10. Deduct resources.
11. Create building instance.
12. Calculate XP.
13. Start construction timer.
14. Increment state revision.
15. Commit transaction.
16. Return authoritative result.
```

---

# 45. PostgreSQL Data Model

Potential tables:

```text
accounts
players
towns
town_zones
town_objects
buildings
unit_instances
unit_queues
inventory_items
inventory_stacks
player_resources
economy_ledger
research_progress
quest_progress
objective_progress
collection_progress
missions
mission_sessions
combat_events
friendships
friend_visits
player_unlocks
content_versions
migration_runs
audit_events
```

Exact schema should follow discovered legacy behavior rather than being finalized prematurely.

---

# 46. Use JSONB Carefully

JSONB is useful for:

```text
unknown legacy fields
migration metadata
rare event payloads
temporary compatibility state
```

Do not simply move the entire old village JSON into one giant PostgreSQL JSONB column and call the migration complete.

Core production state should become structured.

---

# 47. Concurrency Protection

Use player or town revision numbers.

Example:

```json
{
  "expected_revision": 73
}
```

Server compares this against current revision.

If stale:

```http
409 Conflict
```

Client then resynchronizes.

---

# 48. Idempotency

Commands such as:

```text
purchase
collect
claim
craft
mission reward
premium transaction
```

must tolerate network retries.

Use:

```http
Idempotency-Key: UUID
```

If the same request is retried, the server should return the previous result instead of executing it twice.

---

# 49. Database Transactions

Operations that modify multiple pieces of state must be atomic.

Example building purchase:

```text
deduct coins
create building
award XP
update quest objective
write economy ledger
increase revision
```

All should succeed or fail together.

---

# 50. Phase 19 — Legacy Save Migration

Build a dedicated save migration CLI.

Example:

```bash
socialwars-migrate inspect old-save.json

socialwars-migrate validate old-save.json

socialwars-migrate import old-save.json

socialwars-migrate verify old-save.json
```

---

## Support Dry Runs

```bash
socialwars-migrate import old-save.json --dry-run
```

Dry-run output should show:

```text
player detected
resources detected
objects detected
units detected
inventory detected
quests detected
research detected
collections detected
unknown fields detected
validation errors
planned database mutations
```

---

# 51. Save Validation

Check:

```text
known object IDs
known unit IDs
known item IDs
known research IDs
known quests
known collections
resource validity
town positions
map bounds
object overlap
duplicate object IDs
duplicate unit IDs
queue state
timestamps
timer validity
unknown fields
```

---

# 52. Never Silently Drop Unknown Save Data

Unknown legacy fields should be retained somewhere like:

```text
legacy_extra
```

during migration.

This allows future investigation instead of destructive loss.

---

# 53. Migration Must Be Idempotent

Track:

```text
source save hash
migration version
player
import timestamp
migration status
```

Re-importing the same file should not duplicate objects or rewards.

---

# 54. Phase 20 — Authentication and Security

For local preservation mode, complex authentication may not be required.

For public hosting, implement proper account security.

---

## Required Production Measures

```text
no hardcoded secrets
environment-based secrets
HTTPS
secure password hashing where applicable
session expiry
refresh token rotation
request validation
rate limiting
payload limits
authorization checks
audit logging
server-side economy validation
server-side combat validation
server-side ownership validation
```

---

# 55. Local and Online Modes

The architecture could eventually support both.

## Preservation / Offline Mode

```text
Godot
    ↓
Local Compatibility Server
    ↓
Local Save
```

---

## Online Mode

```text
Godot
    ↓
Server API v1
    ↓
PostgreSQL
```

Because both use `GameApi`, the game client can avoid duplicating most gameplay/UI code.

---

# 56. Testing Strategy

Testing is essential because the goal is reconstruction rather than merely writing a similar game.

---

# 57. Golden-Master Tests

For each legacy operation compare:

```text
legacy before
legacy request
legacy response
legacy after
```

against the modern implementation.

Verify:

```text
resource mutations
object mutations
timers
XP
rewards
progression
queues
inventory
mission state
```

---

# 58. Replay Tests

Create gameplay sequences.

Example:

```text
load fresh player
buy building
move building
collect resource
order unit
collect unit
start research
claim research
complete quest
start mission
attack enemy
claim mission reward
```

Run the same sequence against:

```text
Legacy Server
Compatibility API v0
Server API v1
```

Compare state transitions.

---

# 59. Game Invariant Tests

Important invariants:

```text
resources remain valid
premium currency cannot duplicate
object IDs remain unique
unit IDs remain unique
buildings cannot overlap illegally
buildings cannot enter locked zones
queues respect capacity
rewards cannot be claimed twice
completed research remains completed
dead units cannot attack
unowned units cannot be controlled
client clock cannot complete timers early
```

---

# 60. Network Failure Tests

Test:

```text
request timeout
duplicate request
lost response
reconnect
server restart
database rollback
stale revision
request retry
out-of-order response
expired session
content version mismatch
client version mismatch
```

---

# 61. Visual Regression Tests

Maintain reference scenes for:

```text
town layout
building placement
unit animation
combat
HUD
missions
dialogs
```

Compare:

```text
position
scale
pivot
frame
orientation
depth
spacing
```

---

# 62. Performance Testing

Create stress scenarios for:

```text
large towns
hundreds of town objects
many animated units
many simultaneous FX
rapid pan/zoom
large inventory
large content catalog
network bootstrap
save imports
```

Measure before optimizing.

---

## Likely Optimization Areas

```text
off-screen animation throttling
visibility culling
sprite atlases
object pooling
resource caching
lazy UI loading
asset streaming
batching
```

---

# 63. CI Pipeline

The project should eventually run automated CI for:

```text
legacy regression tests
Python linting
Python type checking
Server v1 unit tests
PostgreSQL integration tests
content schema validation
save migration tests
asset manifest validation
Godot headless project import
Godot tests
Godot build
runtime dependency inspection
```

---

# 64. Flash-Free CI Gate

Production packaging should fail if the runtime artifact contains:

```text
*.swf
Flash Player runtime
Ruffle runtime
ActionScript runtime
legacy Flash loader
```

The final client should not depend on them.

---

# 65. Release Artifact Separation

Produce separate artifacts:

```text
legacy-reference
client
server
content
save-migrator
```

The production client must not accidentally package:

```text
legacy/
```

---

# 66. Observability

Production Server v1 should implement structured logging.

Include:

```text
request ID
player ID
action ID
domain
duration
result
revision
```

without exposing sensitive data.

---

## Useful Metrics

```text
request rates
error rates
database latency
slow actions
migration failures
economy anomalies
combat failures
queue failures
content mismatches
```

---

# 67. Admin and Support Tools

Eventually provide tools for:

```text
player lookup
town inspection
resource inspection
inventory inspection
action history
migration history
economy ledger
grant resource with reason
revoke resource with reason
restore snapshot
disable account
inspect content version
```

A CLI is sufficient initially.

A web dashboard can come later.

---

# 68. Content Versioning

Track:

```text
client version
protocol version
content version
server version
```

Bootstrap may return:

```json
{
  "server_version": "1.3.0",
  "protocol_version": 1,
  "content_version": "2026.09.01",
  "minimum_client_version": "0.8.0"
}
```

---

# 69. Server Owns Gameplay Rules

Critical values such as:

```text
building costs
unit costs
XP rewards
mission rewards
research requirements
timers
unlock rules
combat values
```

must be validated from server-controlled content.

Do not trust client copies of these values.

---

# 70. WebSocket Policy

Do not introduce WebSockets simply because the architecture is modern.

Use normal HTTPS requests for:

```text
town actions
building actions
inventory
quests
research
collections
mission commands
```

Use WebSockets later only when useful for:

```text
presence
real-time social events
live announcements
true live multiplayer
push notifications while connected
```

---

# 71. Legal and Provenance Workstream

This should not be ignored.

Create:

```text
PROVENANCE.md
```

and an asset registry containing:

```text
asset
source
original filename
modified status
creator where known
rights status
redistribution status
notes
```

---

## Important Distinction

The repository being GPL does **not automatically mean** every original Social Wars:

```text
art asset
music asset
sound asset
trademark
character
proprietary Flash client component
```

is automatically redistributable under GPL.

Before publicly redistributing reconstructed proprietary assets, obtain appropriate legal review.

---

# 72. Keep Implementations Distinguishable

Maintain separation between:

```text
legacy original material
decompiled reference
converted assets
clean modern implementation
```

This helps:

```text
maintenance
provenance
licensing review
debugging
preservation
```

---

# 73. Definition of Truly Flash-Free

The project is not genuinely Flash-free merely because Adobe Flash Player is gone.

For this project, Flash retirement means:

- Godot is the runtime client.
- No SWF executes during gameplay.
- No ActionScript executes.
- No Flash Player is required.
- No Ruffle runtime is required.
- `SWLoader.swf` is not packaged.
- `Basesec_*.swf` is not packaged.
- Sprite SWFs have been converted or recreated.
- FX SWFs have been converted or recreated.
- Flash UI assets have been converted or recreated.
- FlashVars are gone from the modern client.
- AMF is not required by the modern client.
- A clean machine can install and play the game without Flash-related software.
- CI verifies no Flash runtime dependency exists.

Archived SWFs may still exist in:

```text
legacy/
```

for preservation purposes.

---

# 74. Milestone Roadmap

## M0 — Preservation

Deliver:

```text
legacy baseline tag
environment documentation
dependency lock
asset hashes
canonical saves
known bug documentation
```

Exit:

Legacy implementation is reproducible.

---

## M1 — Protocol Discovery

Deliver:

```text
endpoint catalog
command catalog
legacy request examples
state mutation documentation
```

Exit:

Normal gameplay no longer contains major unknown commands.

---

## M2 — Behavioral Tooling

Deliver:

```text
protocol recorder
protocol replay
state diff
golden fixture format
```

Exit:

Legacy behavior can be automatically captured and compared.

---

## M3 — Content Normalization

Deliver:

```text
normalized game configuration
schemas
content validator
dependency validation
content manifest
```

Exit:

Godot can load validated game definitions without parsing arbitrary legacy structures.

---

## M4 — Asset Pipeline

Deliver:

```text
asset registry
SWF extraction workflow
conversion tooling
one converted building
one converted unit
```

Exit:

At least one authentic building and unit render correctly in Godot.

---

## M5 — Godot Foundation

Deliver:

```text
Godot project
GameApi
LegacyV0Api
ContentRegistry
Session
GameClock
camera
basic UI foundation
Settings
AudioManager
```

Exit:

Client boots and communicates with Compatibility API.

---

## M6 — Town Vertical Slice

Deliver:

```text
existing save loading
terrain
town objects
one building
one unit
camera
zoom
selection
HUD
```

Exit:

A player can launch and view a real legacy town without Flash.

This is the **first major project success target**.

---

## M7 — Construction and Economy

Deliver:

```text
placement
purchase
move
sell
store
upgrade
construction timers
collect income
town expansion
resources
XP basics
```

Exit:

Core town-building gameplay loop works.

---

## M8 — Units

Deliver:

```text
unit definitions
unit instances
queues
production
collection
movement
animations
basic behaviors
```

Exit:

Core unit gameplay works.

---

## M9 — Progression

Deliver:

```text
XP
levels
quests
research
collections
tutorial/progression
```

Exit:

Primary long-term progression systems work.

---

## M10 — Missions and Combat

Deliver:

```text
mission loading
mission state
combat actions
damage
death
mission completion
rewards
```

Exit:

Primary combat loop works.

---

## M11 — Social and Special Systems

Deliver:

```text
friends
visits
scores
social rewards
legacy event systems
special mechanics
```

Exit:

All relevant legacy game systems are classified and implemented or explicitly excluded.

---

## M12 — Asset Parity

Deliver:

```text
all runtime-required SWFs converted or recreated
UI assets converted
FX replaced
animation gaps resolved
```

Exit:

Godot no longer depends on runtime SWFs.

---

## M13 — Server API v1

Deliver:

```text
FastAPI architecture
domain services
authoritative validation
modern API
GameApi ServerV1 implementation
```

Exit:

Godot can operate against the modern server.

---

## M14 — PostgreSQL

Deliver:

```text
database schema
Alembic migrations
repositories
transactions
economy ledger
revisions
idempotency
```

Exit:

Production state no longer depends on filesystem JSON.

---

## M15 — Save Migration

Deliver:

```text
save validator
save importer
dry-run mode
migration report
verification
legacy_extra preservation
```

Exit:

Legacy saves can be migrated safely into PostgreSQL.

---

## M16 — Production Hardening

Deliver:

```text
authentication
authorization
rate limiting
secure secrets
HTTPS readiness
observability
admin tooling
network resilience
CI
deployment
```

Exit:

Server architecture is ready for controlled public deployment.

---

## M17 — Flash Retirement

Deliver:

```text
runtime Flash dependency scan
final package verification
legacy archival separation
documentation update
```

Exit:

The production game runs without:

```text
Flash Player
Ruffle
ActionScript
SWF execution
AMF
FlashVars
```

---

# 75. Exact Feature Migration Dependency Order

Use this order when migrating gameplay:

```text
BOOT
    ↓
CONTENT
    ↓
PLAYER
    ↓
TOWN RENDERING
    ↓
BUILDINGS
    ↓
ECONOMY
    ↓
INVENTORY
    ↓
CRAFTING
    ↓
UNITS
    ↓
XP / LEVELS
    ↓
QUESTS
    ↓
RESEARCH
    ↓
COLLECTIONS
    ↓
MISSIONS
    ↓
COMBAT
    ↓
SOCIAL
    ↓
SPECIAL EVENTS
```

Do not migrate systems randomly.

---

# 76. Initial Implementation Backlog

This is the recommended first concrete backlog.

## Preservation

### 1. Create legacy baseline Git tag

```text
chore: create legacy baseline tag
```

### 2. Document legacy environment

```text
docs: document legacy runtime and startup process
```

### 3. Lock Python dependencies

```text
chore: lock legacy Python dependencies
```

### 4. Build SHA-256 asset manifest

```text
tooling: add legacy asset hash manifest generator
```

### 5. Create canonical save fixtures

```text
test: add canonical legacy save fixtures
```

---

## Behavioral Tooling

### 6. Implement protocol recorder

```text
tooling: record legacy request and response behavior
```

### 7. Implement village state diff

```text
tooling: add before/after village state differ
```

### 8. Implement command replay

```text
tooling: add legacy command replay runner
```

### 9. Generate endpoint catalog

```text
docs: catalog legacy server endpoints
```

### 10. Generate command catalog

```text
docs: catalog legacy game commands and mutations
```

---

## Domain and Content

### 11. Define canonical game domain model

```text
docs: define canonical Social Wars domain model
```

### 12. Create game-content package

```text
feat: initialize normalized game content package
```

### 13. Add schemas

```text
feat: add schemas for normalized game content
```

### 14. Build content validator

```text
tooling: validate normalized game content
```

---

## Godot Foundation

### 15. Initialize Godot project

```text
feat: initialize Godot client
```

### 16. Implement GameApi abstraction

```text
feat: add GameApi abstraction
```

### 17. Implement Compatibility API v0

```text
feat: initialize compatibility API v0
```

### 18. Implement bootstrap loading

```text
feat: load player and game bootstrap data
```

### 19. Implement ContentRegistry

```text
feat: add canonical content registry
```

### 20. Implement asset ID registry

```text
feat: map legacy assets to modern runtime assets
```

---

## Town Renderer

### 21. Implement isometric grid-to-screen conversion

```text
feat: implement isometric coordinate conversion
```

### 22. Implement screen-to-grid conversion

```text
feat: implement inverse isometric coordinate conversion
```

### 23. Add coordinate tests

```text
test: verify isometric coordinate conversions
```

### 24. Implement town camera

```text
feat: add town camera pan and zoom
```

### 25. Implement town bounds

```text
feat: add town map boundaries
```

### 26. Render terrain

```text
feat: render legacy town terrain
```

### 27. Render static town objects

```text
feat: render town objects from existing save
```

### 28. Implement Y/depth sorting

```text
feat: implement isometric object depth sorting
```

### 29. Implement selection

```text
feat: add town object selection
```

### 30. Implement HUD resources

```text
feat: display authoritative player resource HUD
```

---

## First Asset Migration

### 31. Convert first building

```text
assets: convert first legacy building
```

### 32. Render first real building

```text
feat: render converted building in town
```

### 33. Convert first unit

```text
assets: convert first legacy unit
```

### 34. Render first real unit

```text
feat: render converted legacy unit
```

### 35. Add unit idle animation

```text
feat: play converted unit idle animation
```

---

## First Flash-Free Gate

### 36. Create no-Flash vertical-slice test

Verify:

```text
Godot launches
no Flash runtime installed
no Ruffle installed
existing legacy save loads
town renders
terrain renders
buildings render
unit renders
HUD renders
camera works
selection works
```

This is the first major milestone to target.

---

# 77. Second Implementation Backlog

After the Flash-free town works, implement:

```text
building placement preview
grid validation
building purchase
building movement
building flip/orientation
building storage
building restoration
building selling
construction timer
building collection
town expansion
obstacle clearing
inventory loading
unit queue
unit production
unit collection
unit movement
```

---

# 78. Do Not Build These Early

Avoid spending early development time on:

```text
Flask → NestJS rewrite
PostgreSQL migration before Godot works
Kubernetes
microservices
Redis everywhere
WebSockets everywhere
complete UI redesign
game rebalancing
mobile support
custom launcher/updater
public account infrastructure
new multiplayer functionality
```

The first problem to solve is:

Can the existing Social Wars game be faithfully reconstructed and played through a modern client with no Flash dependency?

Everything else follows from that.

---

# 79. Major Technical Risks

## Risk 1 — Important Logic Exists Only in Compiled SWFs

Mitigation:

```text
protocol recording
decompilation/reference analysis
behavioral observation
golden-master testing
state-diff testing
```

---

## Risk 2 — SWF Animations Are More Complex Than Expected

Mitigation:

```text
asset registry
conversion priority
automated extraction where practical
manual recreation for complex assets
visual regression testing
```

---

## Risk 3 — Hidden/Obscure Commands Are Missed

Mitigation:

```text
generated command catalog
coverage tracking
protocol recording
fixture requirements
migration status tracking
```

---

## Risk 4 — Legacy Saves Are Inconsistent

Mitigation:

```text
multiple fixtures
strict validator
raw source preservation
legacy_extra
migration reports
```

---

## Risk 5 — Server Rewrite Changes Behavior

Mitigation:

```text
replay tests
golden tests
legacy-vs-v1 comparison
state-diff tooling
```

---

## Risk 6 — Client Cheating

Mitigation:

```text
authoritative server
economy ledger
server-side rules
ownership validation
revision checking
idempotency
```

---

## Risk 7 — Duplicate Rewards Due to Network Retries

Mitigation:

```text
database transactions
idempotency keys
unique constraints
revision validation
reward claim records
```

---

## Risk 8 — Flash Dependency Survives in Rare UI/FX

Mitigation:

```text
asset dependency manifest
CI package scanning
conversion status tracking
final Flash-free gate
```

---

## Risk 9 — Original Asset Distribution Restrictions

Mitigation:

```text
provenance tracking
asset classification
distribution review
legal review before public release
```

---

# 80. Success Checkpoints

## Checkpoint A — Preservation

Successful when:

```text
legacy environment reproducible
asset hashes created
canonical saves preserved
protocol recorder operational
```

---

## Checkpoint B — First Modern Client

Successful when:

```text
Godot starts without Flash
existing player loads
existing town loads
terrain renders
buildings render
units render
camera works
HUD works
selection works
```

---

## Checkpoint C — Main Gameplay

Successful when Godot supports:

```text
build
move
collect
train units
research
quests
collections
missions
combat
```

---

## Checkpoint D — Legacy Parity

Successful when:

```text
all relevant command.py behavior classified
major replay tests pass
required assets converted
special systems classified
no unknown critical gameplay dependencies remain
```

---

## Checkpoint E — Production Server

Successful when:

```text
Server v1 authoritative
PostgreSQL active
legacy saves migrate
auth secure
economy protected
observability operational
CI operational
```

---

## Checkpoint F — Flash Retirement

Successful when the game can:

```text
install
launch
load player
load town
play normal game loop
save progress
close
restart
resume
```

without:

```text
Flash Player
SWF execution
ActionScript
Ruffle
AMF
FlashVars
```

---

# 81. Recommended Architecture Decision Record

Create:

```text
docs/adr/ADR-001-preservation-first-reconstruction.md
```

Suggested content:

# ADR-001 — Preservation-First Social Wars Reconstruction

## Status

Accepted

## Context

The current project contains a working or partially working reconstruction of Social Wars using a Flask server and the original Flash client architecture.

Although Flash is obsolete as a runtime platform, the existing repository contains valuable behavioral logic, game configuration, save data, server behavior, protocol behavior, images, sounds, and compiled client assets.

Replacing everything simultaneously would make regression detection difficult and risk losing undocumented gameplay behavior.

## Decision

The current Flask/Flash implementation will be treated as the reference implementation and preservation dataset.

The legacy implementation will be frozen while a new Godot client is built.

The first modern client will communicate through a compatibility API that preserves legacy game semantics.

Once client-side feature parity has been established, the backend will progressively migrate toward an authoritative FastAPI server backed by PostgreSQL.

Existing JSON saves will be treated as migration inputs and regression fixtures.

SWFs may remain under an archival legacy directory but must not be required by the final runtime or included in production client packages.

## Consequences

Positive:

- undocumented behavior remains discoverable
- migrations can be verified
- client and server rewrites are decoupled
- existing saves remain usable
- Flash removal can happen incrementally
- regressions become testable

Negative:

- legacy infrastructure remains temporarily
- compatibility code must be maintained during migration
- repository contains old and new implementations simultaneously

These costs are acceptable because they substantially reduce reconstruction risk.

---

# 82. End-State Repository

The eventual repository could look like:

```text
social-wars/
├── apps/
│   ├── client/
│   │   └── Godot
│   │
│   ├── server/
│   │   └── FastAPI
│   │
│   └── compat/
│       └── Legacy compatibility layer
│
├── packages/
│   └── game-content/
│
├── tools/
│   ├── asset-converter/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── save-migrator/
│   └── content-builder/
│
├── legacy/
│   ├── flask-server/
│   ├── flash-client/
│   ├── raw-assets/
│   └── saves/
│
├── tests/
│   ├── golden/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── PROVENANCE.md
└── README.md
```

---

# 83. Immediate Priority Order

The immediate development sequence should be:

```text
FREEZE
    ↓
INSTRUMENT
    ↓
CATALOG
    ↓
REPLAY
    ↓
NORMALIZE CONTENT
    ↓
CREATE GODOT CLIENT
    ↓
BUILD COMPATIBILITY API
    ↓
RENDER ONE REAL TOWN
    ↓
BUILD MAIN GAMEPLAY LOOP
    ↓
REPLACE ALL RUNTIME SWFs
    ↓
BUILD AUTHORITATIVE SERVER
    ↓
MIGRATE TO POSTGRESQL
    ↓
HARDEN PRODUCTION
    ↓
RETIRE FLASH COMPLETELY
```

---

# 84. Most Important Near-Term Target

Do **not** make PostgreSQL or the backend rewrite the first visible result.

The first major target should be:

Launch the Godot client on a computer with no Flash runtime, load one real existing Social Wars save, and faithfully render the town, buildings, units, resources, camera, and basic selection using preserved legacy data.

Once that works, the project has proven that the Flash client can actually be replaced.

---

# 85. Core Architectural Thesis

The most important idea guiding the project is:

**The existing Social Wars repository is not obsolete code that should simply be replaced. It is the reference implementation, behavioral specification, protocol specification, preservation dataset, save corpus, content source, asset archive, and regression oracle for the reconstruction.**

The correct migration therefore is not:

```text
DELETE OLD GAME
    ↓
BUILD NEW GAME FROM MEMORY
```

It is:

```text
PRESERVE
    ↓
OBSERVE
    ↓
RECORD
    ↓
DOCUMENT
    ↓
REPRODUCE
    ↓
VERIFY
    ↓
REPLACE
    ↓
RETIRE
```

The existing Flask implementation should remain available until the Godot client and Server v1 can prove through recorded behavior, replay tests, golden fixtures, and state-diff tests that every required legacy system has a verified replacement.

That approach gives the project the best chance of achieving all four goals simultaneously:

1. **Preserve the original Social Wars behavior.**
2. **Remove the dependency on Flash/SWF completely.**
3. **Modernize the client/server architecture safely.**
4. **Create a maintainable foundation that can continue evolving after preservation parity is achieved.**

---

# 86. Recommended Development Workflow

For each major feature or migration unit:

```text
1. Explore legacy implementation.
2. Identify related commands/endpoints/assets/state.
3. Capture legacy fixtures.
4. Write/update OpenSpec change.
5. Define acceptance criteria.
6. Create feature branch.
7. Implement smallest complete vertical behavior.
8. Add automated tests.
9. Replay legacy fixtures.
10. Compare state.
11. Perform Godot/manual visual verification where applicable.
12. Update migration status.
13. Update documentation.
14. Review.
15. Merge.
16. Push.
```

---

# 87. Recommended Branch Strategy

Use branch-per-feature or branch-per-migration-unit.

Examples:

```text
feat/protocol-recorder
feat/state-diff
feat/content-normalization
feat/godot-bootstrap
feat/town-renderer
feat/building-placement
feat/unit-production
feat/quest-system
feat/server-v1-buildings
feat/save-migrator
```

Avoid creating enormous branches spanning several milestones.

---

# 88. OpenSpec Usage

Use OpenSpec for meaningful behavioral or architectural changes.

Each change should define:

```text
problem
scope
non-goals
existing behavior
target behavior
acceptance criteria
affected systems
migration concerns
testing requirements
```

For reconstruction work, include:

```text
Legacy reference:
- endpoint
- command
- source files
- fixtures

Parity requirements:
- expected state mutation
- expected response
- visual behavior where relevant
```

---

# 89. Definition of Done for a Migrated Feature

A migration feature is not complete merely because the new UI appears to work.

A migrated feature should normally satisfy:

```text
legacy behavior identified
legacy fixture captured
modern behavior implemented
automated test added
state mutation verified
error conditions tested
retry behavior considered
content IDs preserved
relevant assets migrated
documentation updated
migration status updated
no new Flash dependency introduced
```

For Server v1 features additionally require:

```text
server-authoritative validation
database transaction where needed
authorization
revision handling
idempotency where needed
economy ledger where needed
```

---

# 90. Final Project Definition of Done

The complete modernization is finished when:

```text
Godot is the only gameplay client.

Normal gameplay contains no SWF execution.

Normal gameplay contains no ActionScript execution.

Adobe Flash Player is unnecessary.

Ruffle is unnecessary.

The modern client does not know about command.php.

The modern client does not use FlashVars.

The modern client does not require AMF.

All gameplay-critical legacy commands are implemented,
retired, or explicitly declared out of scope.

All runtime-critical Flash assets have been converted
or recreated.

Existing supported legacy saves can be migrated.

Production player state lives in PostgreSQL.

Production game actions are server authoritative.

Important economy mutations are auditable.

Network retries cannot duplicate important rewards.

Client clock manipulation cannot bypass timers.

Authentication and authorization are production-safe.

Automated golden/replay tests verify important legacy parity.

Visual regression coverage exists for important scenes.

CI prevents accidental reintroduction of Flash dependencies.

Legacy files remain preserved separately for historical,
debugging, migration, and research purposes.

A clean machine can install the modern client,
connect to the server, load a player,
play the game, close it, reopen it,
and continue playing without installing
any Flash-related software.
```

---

# 91. Development Priority Summary

## Build Now

```text
legacy preservation
dependency locking
hash manifest
canonical saves
protocol recorder
state diff
command replay
endpoint catalog
command catalog
content normalization
Godot initialization
GameApi abstraction
Compatibility API v0
town bootstrap
isometric renderer
camera
terrain
town objects
first building
first unit
HUD
selection
no-Flash vertical slice
```

## Build Next

```text
building placement
economy
construction
collection
inventory
unit queues
unit movement
XP
quests
research
collections
missions
combat
social
special systems
asset parity
```

## Build After Parity Is Established

```text
Server API v1
authoritative game rules
PostgreSQL
save importer
authentication
rate limiting
observability
admin tools
production deployment
```

## Build Much Later If Needed

```text
Redis
WebSockets
mobile client
new multiplayer systems
major gameplay redesign
balance changes
microservices
advanced deployment infrastructure
```

---

# 92. The First Concrete Goal

The engineering team or coding agent should treat the following as the immediate mission:

**Preserve and instrument the legacy implementation, then build the smallest Godot vertical slice capable of loading and displaying a real Social Wars town from an existing save without executing Flash or SWF content.**

Everything before that target should directly support it.

Everything that does not directly support it should generally wait.

The first sequence therefore is:

M0 Preservation
    ↓
M1 Protocol Discovery
    ↓
M2 Recorder / Replay / State Diff
    ↓
M3 Content Normalization
    ↓
M4 Initial Asset Conversion
    ↓
M5 Godot Foundation
    ↓
M6 Flash-Free Town Vertical Slice

**M6 is the first major victory.**

Do not allow backend modernization, infrastructure work, or unrelated redesign to delay reaching it.

### The M8 entry position, recorded for the next run

M8's first deliver line is **unit definitions**, and the delivered work already constrains it
in three ways that the investigation must not re-derive:

- **The corpus contains no unit placements at all**, and 0 of its 40 placed rows carry
  `attr["xp"]`, which is why the XP line's unit XP (`add_xp_unit`) and the level curve's
  `reward_type`/`reward_amount` are out of scope there and recorded as such.
- **M4 established the unit asset truth**: `tools/asset-registry/convert_unit.py` produced one
  converted unit package — a per-sprite timeline inventory with shape/bitmap linkage, **no
  tessellation and no playback semantics** — and its README states it establishes "no animation
  correctness, rendering, visual fidelity, gameplay semantics, or Godot loading". So M8's
  `animations` and any rendering claim rest on that package plus the M6 slice evidence, which
  already proved authentic unit rendering through the Wild Elephant sprite in
  `apps/client-godot/evidence/town/` while recording that the fresh save has no unit placements.
- **The committed content already carries the unit definitions**: the items normalization
  committed **429 units** of the 900 `items` entries (470 buildings, 429 units, 1 documented
  special), each with schemas and round-trip evidence, so `unit definitions` is a content-delivery
  line over committed artifacts rather than a legacy-behaviour derivation.

The honest first questions for the M8 investigation are therefore: what does the legacy server
actually do with units (the command catalog's "Units and production queues" section is the place
to start, alongside `push_unit`, `pop_unit`, and `push_dead_unit`), what a unit instance looks
like in the save, and what the corpus can and cannot exercise — with every unobserved rule marked
derived-provisional exactly as M7's were.
