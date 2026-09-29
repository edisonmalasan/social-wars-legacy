# Spec Delta

## MODIFIED Requirements

### Requirement: Compatibility API v0 bootstrap service
The repository SHALL provide a Compatibility API v0 service that serves modern JSON bootstrap data by adapting the unchanged legacy boot modules in-process, listens only on loopback at an explicit documented port, fails closed with structured JSON errors on inputs it cannot resolve, and never persists state from its session or bootstrap endpoints: calling those endpoints SHALL leave every on-disk save byte-identical while the legacy in-memory boot semantics execute exactly as the legacy endpoints perform them. State-mutating gameplay execution is specified by the `godot-building-placement`, `godot-building-purchase`, `godot-building-move`, `godot-building-sell`, `godot-building-store`, `godot-building-upgrade`, `godot-building-construction`, and `godot-building-collect` capabilities and SHALL persist only through unchanged legacy command semantics into the service corpus, never into a working-tree save.

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
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()`, `get_bootstrap()`, `place_building()`, `purchase_item()`, `move_building()`, `sell_building()`, `store_building()`, `upgrade_building()`, `build_construction()`, and `collect_income()` operations with two interchangeable implementations — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data and applying the documented in-memory operation semantics with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names.

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
