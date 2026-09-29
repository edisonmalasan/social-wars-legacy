# Design

## Context

M6 left a rendering-only town: the client loads a save through `GameApi` (`list_sessions`/`get_bootstrap`), parses a typed `TownState`, and renders terrain, depth-sorted objects, HUD, selection, and camera — but no code path changes state. Compatibility API v0 serves only `/v0/session` and `/v0/bootstrap`, is read-only by contract, and never imports `sessions.save_session`. The legacy server, however, already contains the complete placement behavior: `POST …/command.php` → `command(USERID, data)` applies each command's resource vector, dispatches the `buy` branch (`bought_unit_add`, `map_add_item` with its `si`/`nc` attribute rules), and persists via batch `save_session` (see `docs/legacy-protocol/commands.md`, `command.py`, `engine.py`). `tools/protocol-replay` already proves legacy command batches execute in-process offline inside an isolated disposable child. The fresh-player save has an empty `store` and 2000 gold/wood/oil/steel, so the only exercisable placement path is `buy` (purchase + place fused in one legacy command); config items carry `costs` (JSON keys `g`/`w`/`o`/`s`/`c`), `min_level`, `in_store`, `width`/`height`, and `type` in the bootstrap payload the client already receives. See `proposal.md` for motivation; the deltas under `specs/` are the behavior contract.

## Goals / Non-Goals

**Goals:**

- One coherent player loop: pick → preview → confirm → authoritative placement persisted through unchanged legacy code → re-render.
- An executed-legacy parity oracle for that loop, replayable offline with no server and no network.
- Intent-only client contract: no client-supplied resource/XP/result deltas anywhere in the modern surface.
- Containment equal to M5/M6: loopback only, pinned interpreter, no new packages, working-tree saves never written, both batteries green, guards and hash manifest unchanged.

**Non-Goals:**

- Purchase/shop surface flows (`buy_si_help`, `buy_stored_item_cash`, `place_stored_item`, shop browsing) — separate M7 deliver lines, even though legacy `buy` fuses payment with placement.
- Move, sell, store, upgrade, construction-timer UI, collect income, town expansion, resource systems, XP basics (beyond the cost vector `buy` inherently applies).
- Server-side gameplay validation (occupancy, affordability rejection, unlock/prerequisite checks) — that is Server v1 (M13) territory per the roadmap; legacy never validated, and the Flash client's exact rules are unobservable without executing Flash.
- Unit placement, ContentRegistry changes, a second bootstrap per launch, PostgreSQL, anti-cheat, progressed-player coverage.

## Decisions

### D1 — Scope: placement through legacy `buy`, cost included

The M7 deliver line *placement* is delivered as the full vertical slice using the legacy `buy` command, including its resource application. Alternative: `place_stored_item` alone (rejected — the fresh save's `store` is `{}`, so there is nothing placeable; the slice would be unexercisable for a player), or a client-only placement subsystem with no execution (rejected — state would never mutate through legacy code, breaking the preservation chain). The `costs` vector is applied because legacy `buy` always runs `apply_resources` before its branch: skipping it would exercise a *partial* legacy path. The separate *purchase* deliver line remains open (shop surface, stored/cash purchases, help flows); this boundary is stated in the proposal so the roadmap ledger can track it honestly.

### D2 — Execution venue: in-process legacy dispatcher inside Compatibility API v0

The endpoint calls the unchanged legacy `command()` (not the Flask `command.php` route, not a rewritten domain module). Alternatives: (a) the Godot client posting to the legacy Flask server directly — rejected, the client must never reference legacy URLs/form encoding (`godot-compatibility-boot` scope contract); (b) reimplementing placement in a modern domain module — rejected, that replaces legacy behavior without parity evidence; (c) deferring execution to Server v1 — rejected, M13 is many milestones away and M7 requires the loop to work on the v0 path the architecture mandates ("Build `LegacyV0Api` before `ServerV1Api`"). In-process execution over the disposable corpus is exactly the pattern `tools/protocol-replay` already validates, and the compat service already chdirs into a corpus before legacy imports.

### D3 — Intent-only contract; the envelope is synthesized server-side

`POST /v0/place` accepts `{user_id, item_id, x, y, orientation}` and derives the legacy batch envelope internally. Alternative: accepting the full legacy envelope (with `resource_deltas`) from the client — more byte-faithful to the wire protocol, but it violates the architecture rule that clients never send trusted resource/XP/result deltas, and would put envelope-construction logic in presentation code (forbidden tokens). The derived envelope reproduces what the Flash client *would* have sent; because Flash is never executed, the derivation is recorded **derived-provisional** (same epistemic class as the M6 iso constants). Parity is therefore claimed at the *legacy execution* layer: for an identical envelope, executed legacy and compat produce identical response and after-state.

### D4 — Envelope derivations (all recorded, none observable from Flash)

| Field | Value | Basis |
| --- | --- | --- |
| `resources_changed` | `-[costs]` per key mapped `g→gold, w→wood, o→oil, s→steel, c→cash` in the legacy 8-slot vector `[unknown, xp, gold, wood, oil, steel, cash, mana]`, `xp = 0`, others `0` | config `costs`; XP deliberately deferred to the *XP basics* deliver line |
| `args[0]` slot | smallest positive integer absent from `map.items` | legacy map keys are `1..N`; Flash's choice unobservable |
| `args[4]` player | `1` | all 40 fresh placements use `player=1` |
| `args[5]` orientation | passthrough, default `0` | existing entries use `0` |
| `args[6]` unknown, `args[7]` reason | `0`, `""` | unobservable placeholders, documented |
| `first_number`, `publishActions`, `ts`, `tries`, `accessToken` | `0`, `[]`, current time, `1`, `""` | keys `command()` reads; values unobservable, sanitized in fixtures |

Cost application is legacy-exact: the same `apply_resources` clamps every resource with `max(…, 0)`, so insufficient funds place anyway with zeroed resources — preserved deliberately as legacy behavior (rejection belongs to Server v1) and covered by its own test.

### D5 — Validation split mirrors the evidenced Flash-era division of labor

`engine.map_add_item` performs **no** validation — proof that placement rules lived in the Flash client, not the legacy server. Therefore:

- **Client** (derived, documented): grid bounds, footprint non-overlap with existing placements, affordability display; invalid targets render an invalid preview and send nothing.
- **Endpoint** (structural, fail-closed): JSON object body, resolvable save id, item id present in config, integer **anchor** coordinates inside the shared town grid (`0..99`, the M6 derived-provisional extent). The footprint is deliberately *not* required to stay inside the grid: correcting this design during Apply, verification against the committed fresh save showed all 40 placements have anchors `≤ 99` while the Harbour anchored at `(99,92)` with width 10 reaches `x=108` — observed legacy placements already cross the edge, so an anchor-only rule is the one consistent with them (the client's existing `Iso.in_bounds` is likewise cell-based). This is an *input resolvability* rule — an anchor outside the renderable grid cannot resolve to a displayable town state — and is documented as a v0 deviation from legacy acceptance, not as a gameplay-validation claim.
- **Endpoint does not check occupancy or funds-rejection**: occupancy is a Flash-client gameplay rule (client-enforced; legacy would accept overlaps), and funds reproduce legacy clamping. Alternative rejected: full server-side validation — it would claim rules we cannot verify against Flash and would deviate from observed legacy behavior.

### D6 — Persistence scope: corpus only, with the spec re-scoped

`command()` persists through `save_session` into `./saves/<pid>.save.json` of the process corpus (temp corpus by default, `--corpus PATH` for tests). The `godot-compatibility-boot` delta re-scopes "never persists" to the session/bootstrap endpoints so placement can persist without contradicting the boot contract; the bootstrap scenarios (byte-identical saves for boot calls) are untouched. The alternative — a read-only placement endpoint — was rejected as meaningless: legacy `command.php` persists by design, and a placement that does not survive a restart delivers no M7 behavior. Working-tree `saves/` (and `tests/saves/`) are never the corpus and are guard-hashed around every battery run.

### D7 — Response carries an authoritative superset

Legacy returns only `{"result": "success"}`; the client must render the new object and update HUD resources without a second bootstrap (the one-bootstrap-per-launch contract). The endpoint therefore returns the legacy `result` plus `placement` (the persisted eight-field entry) and `resources` (post-application values) — a documented envelope superset, following the precedent that the bootstrap envelope already carries `saves` beyond design D3. The client applies *only* these authoritative values.

### D8 — FakeApi is a documented test double, not a parity oracle

`FakeApi.place_building` applies the same documented semantics in memory (cost map, clamp, slot selection, entry construction) over the committed fixture state, deterministically, with no process/server/socket. Parity is owned exclusively by the compat fixture-replay tests; the fake exists so client flow tests are hermetic. Alternative — having the fake fail closed as "unsupported" — rejected: the placement flow could then never be tested headlessly, which the batteries require.

### D9 — Fixture capture: new tool, new fixture directory, full after-state

A new capture tool (sharing the containment harness of `apps/compat-api/capture_legacy_fixtures.py`) starts the real legacy server in a disposable copy, seeds it from `tests/saves/fresh-player.json`, POSTs the crafted `buy` envelope to `…/command.php`, and records `request.json` (sanitized: no `user_key`/token values), `before.json` (full save), `response.body` + `response.meta.json`, `after.json` (full save), plus `capture-manifest.json` and `README.md` (command, exit codes, containment) under `tests/fixtures/godot-building-placement/`. Full save JSON (not just hashes) is required because placement parity compares *state changes*, unlike boot parity which compared responses; the seed is synthetic/committed, so there is no privacy issue. Boot fixtures and their manifests stay byte-identical (fixtures are capability-scoped; the existing boot capture tool is not modified). Time-dependent fields (`timestamp` entries, `server_time`) are normalized exactly as the boot parity tests document.

### D10 — Client flow structure

The bootstrap payload already in hand (one request per launch) carries all 900 items; a typed placement catalog parses the needed fields fail-closed from it (`id`, `name`, `costs`, `min_level`, `in_store`, `width`, `height`, `type`) — same pattern as `TownState`, never re-fetching config. The town scene gains a placement mode: a picker panel over the catalog (store-listed, `min_level ≤` loaded level) built on the UI-foundation slot registry, a footprint preview drawn through the existing iso projection and content footprints (highlight valid/invalid), and confirm → `GameApi.place_building()` → apply response (append object at depth, update HUD slots from `resources`). Selection input routes to placement mode while active and to selection otherwise, so the M6 selection contract is untouched. All new scripts and suites extend the project-scope allow-list; `verify-boot.ps1` registers the new suites and gains one live placement phase (start compat over a disposable corpus, place, assert the corpus save mutated, teardown asserting port release and corpus cleanup — same contract as the existing live phases).

### D11 — Evidence: fake-based windowed capture + deterministic report; real execution proven headlessly

Following the D10 evidence pattern of M6: a windowed run (fake API) captures the town containing the placed building into `apps/client-godot/evidence/placement/placement.png`; a headless run writes a deterministic `report.json` (inputs/digests, intent, counts before/after, resources, projection constants pointer, every non-claim) whose rerun reproduces its bytes. The report states plainly that the capture runs the fake implementation and that real-execution parity is established by the fixture-replay tests and the verify-boot live phase — the claim limits carry that pointer so no reader can mistake the screenshot for executed-legacy proof.

## Risks / Trade-offs

- **Derived price/envelope may differ from what real Flash sent** → parity is claimed only against the executed-legacy fixture for the derived envelope (mechanics parity); the derivation is recorded derived-provisional in the report, README, and ledger.
- **Legacy clamping lets a hostile client place without funds** → accepted as preserved legacy behavior; client pre-filters, guards prevent working-tree writes, Server v1 (M13) adds authoritative validation; documented as a non-claim.
- **A mutating endpoint exists in a formerly read-only service** → persistence confined to the corpus; bootstrap/session byte-identity tests retained; guards + hash manifest around every battery; fail-closed tests assert no mutation on every error path.
- **Occupancy/bounds rules are derived (Flash unobservable)** → enforced client-side only (bounds additionally as endpoint input resolvability), documented as derived in the delta and report.
- **Scope creep into purchase/shop UI** → non-goals list, picker limited to a filter over the typed catalog, deliver-line boundary stated in proposal and tasks.
- **Bootstrap payload parsing growth (900 items)** → single fail-closed parse of only the needed fields at load time; no repeated parsing in the frame loop.

## Migration Plan

Branch flow per AGENTS: `docs/building-placement-proposal` (Propose, merged first) → `feat/building-placement` (Apply: fixture capture → endpoint → GameApi → client flow → batteries/evidence → docs) → `docs/building-placement-spec-sync` (Sync) → `chore/archive-building-placement` (Archive + ledger). No data migration and no deployment step: corpora are disposable, the legacy tree is untouched, and rollback is a plain revert of the merge commits (no history rewrite).

## Open Questions

- The exact `reason`/`unknown` placeholder values inside the synthesized `buy` args may be revised if a genuine Flash request surface is ever observed; this cannot change the specs (they require documented derivation, not specific placeholder values) and does not affect the task breakdown.
