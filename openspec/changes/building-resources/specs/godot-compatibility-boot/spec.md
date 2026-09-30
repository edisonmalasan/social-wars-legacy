# Spec Delta

## MODIFIED Requirements

### Requirement: Compatibility API v0 bootstrap service
The repository SHALL provide a Compatibility API v0 service that serves modern JSON bootstrap data by adapting the unchanged legacy boot modules in-process, listens only on loopback at an explicit documented port, fails closed with structured JSON errors on inputs it cannot resolve, and never persists state from its session or bootstrap endpoints; it SHALL also expose the stored energy value a player save carries on its own additive read-only path rather than by widening the shared resource accessor the state-mutating endpoints' post-execution proofs compare, because no delivered path mutates that value: calling those endpoints SHALL leave every on-disk save byte-identical while the legacy in-memory boot semantics execute exactly as the legacy endpoints perform them. State-mutating gameplay execution is specified by the `godot-building-placement`, `godot-building-purchase`, `godot-building-move`, `godot-building-sell`, `godot-building-store`, `godot-building-upgrade`, `godot-building-construction`, `godot-building-collect`, and `godot-building-expand` capabilities and SHALL persist only through unchanged legacy command semantics into the service corpus, never into a working-tree save.

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

### Requirement: GameApi abstraction
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()`, `get_bootstrap()`, `place_building()`, `purchase_item()`, `move_building()`, `sell_building()`, `store_building()`, `upgrade_building()`, `build_construction()`, `collect_income()`, and `expand_town()` operations projecting every resource through one canonical mapping that names each resource exactly as the legacy server names it — the primary currency as `gold` and never `coins`, and the experience counter grouped with the player's summary — with two interchangeable implementations — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data and applying the documented in-memory operation semantics with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names.

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
