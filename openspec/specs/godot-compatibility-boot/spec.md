## Purpose

Boot the Godot client against a Compatibility API v0 that adapts the unchanged legacy boot surface, with executed-legacy fixtures as the parity oracle, so the client can initialize a session and load bootstrap data without Flash, without modifying legacy behavior, and without leaving the loopback boundary.

## Requirements

### Requirement: Compatibility API v0 bootstrap service
The repository SHALL provide a Compatibility API v0 service that serves modern JSON bootstrap data by adapting the unchanged legacy boot modules in-process, listens only on loopback at an explicit documented port, fails closed with structured JSON errors on inputs it cannot resolve, and never persists state from its session or bootstrap endpoints: calling those endpoints SHALL leave every on-disk save byte-identical while the legacy in-memory boot semantics execute exactly as the legacy endpoints perform them. State-mutating gameplay execution is specified by the `godot-building-placement`, `godot-building-purchase`, `godot-building-move`, `godot-building-sell`, `godot-building-store`, `godot-building-upgrade`, `godot-building-construction`, `godot-building-collect`, and `godot-building-expand`, and `godot-building-xp` capabilities, and state-mutating queue execution is specified by `godot-unit-queues` and SHALL persist only through unchanged legacy command semantics into the service corpus, never into a working-tree save.

#### Scenario: Serve the session list
- **WHEN** a client requests the v0 session list
- **THEN** the response contains each saved village's id, name, xp, and level exactly as the legacy `all_saves_info()` computes them for the corpus, together with the legacy game version and a server timestamp

#### Scenario: Bootstrap a known user
- **WHEN** a client requests bootstrap for an existing save id
- **THEN** the response carries the legacy `get_game_config()` payload and the legacy `get_player_info()` payload (player info, default map, private state, neighbors) inside a documented envelope, equal to the captured legacy endpoint responses for every stable field

#### Scenario: Preserve legacy boot semantics without writing
- **WHEN** bootstrap resolves for a known user
- **THEN** the legacy in-memory boot effects (`last_logged_in` update and `reset_stuff`) occur exactly as the legacy endpoint performs them while the pre/post SHA-256 of every save file on disk is identical

#### Scenario: Fail closed on an unusable request
- **WHEN** the user id is missing or names no save
- **THEN** the service answers a structured JSON error identifying the problem with a non-2xx status and serves no config or player payload

#### Scenario: Bind to loopback only
- **WHEN** the service starts
- **THEN** it listens on `127.0.0.1` at the documented port and the documented interface is the only one clients are told to use

#### Scenario: Serve a guarded queue intent
- **WHEN** a client pushes or pops a production queue through either implementation
- **THEN** the request carries only the player identifier and the target row's key, any
  client-supplied cost, duration, count, or readiness key is ignored, and the post-execution
  proof asserts that every stored resource is unchanged while the row's attribute bag
  carries exactly the recorded queue effect

### Requirement: GameApi abstraction
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()`, `get_bootstrap()`, `place_building()`, `purchase_item()`, `move_building()`, `sell_building()`, `store_building()`, `upgrade_building()`, `build_construction()`, `collect_income()`, `expand_town()`, and `level_up_town()`, `push_queue_unit_town(map_key)` and `pop_queue_unit_town(map_key)` and `complete_collection_town(collection_id)` operations, with the two queue operations sending **only a map key** and no cost, duration, readiness, count, or outcome, and the collection operation sending **only a collection id** with its grant derived entirely from committed content, with the level-up operation deriving its target level from the player's stored experience and the committed level schedule rather than accepting a client-supplied level outcome projecting every resource through one canonical mapping that names each resource exactly as the legacy server names it — the primary currency as `gold` and never `coins`, and the experience counter grouped with the player's summary — with two interchangeable implementations — and unit **definitions**, which are read from the committed content package through the content registry and are therefore **not** a GameApi operation: no server round trip, no compatibility surface, and no client-supplied or server-supplied unit content — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data and applying the documented in-memory operation semantics with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names.

#### Scenario: Boot offline with the fake implementation
- **WHEN** headless tests run with the fake implementation selected
- **THEN** session list and bootstrap resolve from committed fixture data with no server or network involved, producing the same typed shapes the live implementation returns

#### Scenario: Boot live against Compatibility API
- **WHEN** the legacy-v0 implementation requests session list and bootstrap against a running Compatibility API v0
- **THEN** it yields the same typed boot data the fake implementation produces and the boot scene consumes it without presentation-code changes beyond the implementation switch

#### Scenario: Keep legacy transport out of the UI
- **WHEN** the project scripts are scanned by the scope test
- **THEN** only the legacy-v0 implementation references the compat endpoint and no script contains the forbidden legacy protocol tokens

#### Scenario: Place through either implementation
- **WHEN** headless tests run the placement flow with the fake implementation selected, and a live run places against a running Compatibility API v0
- **THEN** both implementations yield the same typed placement result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Purchase through either implementation
- **WHEN** headless tests run the purchase flow with the fake implementation selected, and a live run purchases against a running Compatibility API v0
- **THEN** both implementations yield the same typed purchase result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Move through either implementation
- **WHEN** headless tests run the move flow with the fake implementation selected, and a live run moves against a running Compatibility API v0
- **THEN** both implementations yield the same typed result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Sell through either implementation
- **WHEN** headless tests run the sell flow with the fake implementation selected, and a live run sells against a running Compatibility API v0
- **THEN** both implementations yield the same typed sell result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Store through either implementation
- **WHEN** headless tests run the store flow with the fake implementation selected, and a live run stores against a running Compatibility API v0
- **THEN** both implementations yield the same typed store result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Upgrade through either implementation
- **WHEN** headless tests run the upgrade flow with the fake implementation selected, and a live run upgrades against a running Compatibility API v0
- **THEN** both implementations yield the same typed upgrade result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Construct through either implementation
- **WHEN** headless tests run the construction flow with the fake implementation selected, and a live run starts a construction against a running Compatibility API v0
- **THEN** both implementations yield the same typed construction result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Collect through either implementation
- **WHEN** headless tests run the collection flow with the fake implementation selected, and a live run collects against a running Compatibility API v0
- **THEN** both implementations yield the same typed collection result shapes consumed identically by the flow, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Expand through either implementation
- **WHEN** headless tests run the expansion flow with the fake implementation selected, and a live run expands against a running Compatibility API v0
- **THEN** both implementations yield the same typed expansion result shapes consumed identically by the flow, the response's owned list and derived debit are applied rather than the client's own arithmetic, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Project every resource under its server name
- **WHEN** headless tests render the resource readout against a payload produced by either implementation
- **THEN** every resource the legacy resource application writes renders its real stored value under the name the service produces, no row renders an absent-field indicator for a resource the service does produce, a genuinely absent resource still renders the explicit absent-field indicator, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Level up through either implementation
- **WHEN** headless tests run the level-up flow with the fake implementation selected, and a live run levels up against a running Compatibility API v0
- **THEN** both implementations yield the same typed shapes, the flow applies the service's derived level rather than its own arithmetic, a client-supplied level is ignored exactly as a client-supplied amount or price is ignored elsewhere, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Read unit definitions from committed content
- **WHEN** the client needs a committed unit definition, and when headless tests resolve definitions through the content registry's unit domain
- **THEN** the definition is read from the already-loaded registry with no request issued, no compatibility route added, and no player-owned unit instance state introduced, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: Push and pop a queue through either implementation
- **WHEN** headless tests run the queue flow with the fake implementation selected, and a live run pushes and pops a queue against a running Compatibility API v0
- **THEN** each intent carries only the player identifier and the target row's key, any client-supplied cost, duration, count, or readiness key is ignored, the response reports the projected queue, and the post-execution proof asserts that every stored resource is unchanged while the row's attribute bag carries exactly the recorded queue effect, and neither implementation reports whether a queue is complete or how long remains

#### Scenario: Complete a collection through either implementation
- **WHEN** a collection completion runs with the fake implementation selected, and a live run completes a collection against a running Compatibility API v0
- **THEN** each intent carries only the player identifier and the collection id, any client-supplied prize, item id, or quantity is ignored, the grant is derived from the committed collection table, and the post-execution proof asserts that the granted id and quantity equal the committed prize bag and that the collection ledger grew by exactly one appended id

### Requirement: Boot scene
The project SHALL provide a boot scene as the main scene that initializes the session, requests bootstrap, and displays engine version, connection state, and a player summary derived from the response; an unreachable endpoint or a structured API error SHALL surface as an explicit error state naming the failure, never as a blank screen or a partial success.

#### Scenario: Boot end to end
- **WHEN** the documented boot verification command runs against a locally started Compatibility API v0 over a disposable corpus
- **THEN** the headless boot run reports connected, the displayed player summary (name, level, xp) equals the fixture save, and the command exits 0

#### Scenario: Fail visibly when unreachable
- **WHEN** bootstrap runs with no service listening
- **THEN** the boot scene enters an error state naming the failure and the headless verification observes that error state instead of a success claim

#### Scenario: Fail visibly on API error
- **WHEN** the service returns a structured error
- **THEN** the boot scene displays that error rather than an empty or guessed summary

### Requirement: Windowed boot-to-town transition
After the boot scene reaches its ready state with successfully validated typed bootstrap data, a windowed run SHALL hand that already-validated state to the town scene and replace the boot view with the town view — without issuing a second bootstrap request (the legacy bootstrap mutates `last_logged_in`, so exactly one request per launch is part of the contract) and without the raw transport payload reaching presentation code; a handoff that cannot build a valid town state SHALL surface an explicit error naming the failure in place of the view, never a blank window and never a partially rendered town; and a headless run SHALL never enter the town scene, keeping the existing headless marker, summary, error-state, and exit-code contract byte-for-byte unchanged.

#### Scenario: Exactly one bootstrap per launch into the town
- **WHEN** a windowed run completes bootstrap successfully against either GameApi implementation
- **THEN** exactly one bootstrap request was made, the boot view is replaced by the town view rendering that save's terrain, objects, and HUD, and the committed evidence capture records the view

#### Scenario: Headless boot behavior is unchanged
- **WHEN** the headless boot verification runs (success and unreachable-endpoint cases)
- **THEN** its markers, displayed summary, error states, and exit codes are exactly as before, and no town scene is instantiated

#### Scenario: Fail explicitly instead of a blank window
- **WHEN** the handed state cannot build a valid town state at transition time
- **THEN** an explicit error naming the failure replaces the view, and no partial town is shown

### Requirement: Legacy parity fixtures
Before the Compatibility API behavior is implemented, the repository SHALL capture golden fixtures by executing the real legacy endpoints — request, before-state, response, and after-state — inside a disposable copy under the pinned interpreter, commit them under a documented path together with a field-stability record, and the Compatibility API tests SHALL reproduce those responses with no server running for all stable fields, with every time-dependent field documented and normalized.

#### Scenario: Capture from the executed legacy server
- **WHEN** the fixture capture command runs
- **THEN** `get_game_config.php` and `get_player_info.php` request/response pairs plus before/after save hashes for the fresh-player corpus are committed, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline
- **WHEN** the Compatibility API parity tests run with no network
- **THEN** its session and bootstrap outputs equal the captured legacy responses field-by-field except the documented time-dependent fields, which match their documented normalization

### Requirement: Containment and preservation
All execution SHALL stay on loopback with no Flash, Ruffle, ActionScript, browser, or external network; Python SHALL run under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, conversion packages, preservation manifests, and the committed M4 first-render evidence SHALL remain byte-identical across the change (SHA-256 guards), and the M4 verification SHALL remain green in the final state.

#### Scenario: Verify without side effects
- **WHEN** fixture capture, Compatibility API tests, boot verification, and first-render verification have all run
- **THEN** guard hashes over legacy sources, both conversion packages, the three registry manifests, and the committed M4 evidence are identical before and after, and only disposable copies were mutated

#### Scenario: Keep M4 green
- **WHEN** the first-render verification command runs in the final state
- **THEN** it exits 0 and the committed `first-render.png` and `report.json` remain byte-identical to their recorded digests

### Requirement: Documented commands and assessment record
`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed (fixture capture, Compatibility API tests, boot verification, first-render verification), the loopback port, the evidence paths, and the limits of the v0 claim — read-only bootstrap parity for the fresh-save corpus, not gameplay parity, not authentication security, not progressed-player coverage — and the roadmap Project Status ledger SHALL record the M5 progress this change delivers.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states which M5 items this change delivers (§16 GameApi, §17 Compatibility API v0, §18 bootstrap loading), which M5 items remain, and points to the committed evidence
