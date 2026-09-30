# Spec Delta

## MODIFIED Requirements

### Requirement: GameApi abstraction
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()`, `get_bootstrap()`, `place_building()`, `purchase_item()`, `move_building()`, `sell_building()`, `store_building()`, `upgrade_building()`, `build_construction()`, `collect_income()`, `expand_town()`, and `level_up_town()` operations, with the level-up operation deriving its target level from the player's stored experience and the committed level schedule rather than accepting a client-supplied level outcome projecting every resource through one canonical mapping that names each resource exactly as the legacy server names it — the primary currency as `gold` and never `coins`, and the experience counter grouped with the player's summary — with two interchangeable implementations — and unit **definitions**, which are read from the committed content package through the content registry and are therefore **not** a GameApi operation: no server round trip, no compatibility surface, and no client-supplied or server-supplied unit content — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data and applying the documented in-memory operation semantics with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names.

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
