# Spec Delta

## MODIFIED Requirements

### Requirement: GameApi abstraction
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()`, `get_bootstrap()`, `place_building()`, `purchase_item()`, `move_building()`, `sell_building()`, `store_building()`, `upgrade_building()`, `build_construction()`, `collect_income()`, `expand_town()`, and `level_up_town()`, `push_queue_unit_town(map_key)` and `pop_queue_unit_town(map_key)` and `complete_collection_town(collection_id)` operations, with the two queue operations sending **only a map key** and no cost, duration, readiness, count, or outcome, and the collection operation sending **only a collection id** with its grant derived entirely from committed content, with the level-up operation deriving its target level from the player's stored experience and the committed level schedule rather than accepting a client-supplied level outcome projecting every resource through one canonical mapping that names each resource exactly as the legacy server names it — the primary currency as `gold` and never `coins`, and the experience counter grouped with the player's summary — with two interchangeable implementations — and unit **definitions**, which are read from the committed content package through the content registry and are therefore **not** a GameApi operation, as is unit **movement**, whose placement, footprint, and velocity are committed content read through that same registry and whose only legacy command is already delivered by `godot-building-move`, so a unit move needs no server round trip, no compatibility surface, and no client intent: no server round trip, no compatibility surface, and no client-supplied or server-supplied unit content — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data and applying the documented in-memory operation semantics with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names., as is unit **animation**, whose labels, frame positions, and recorded frame counts are committed asset linkage read from the committed converted package rather than from the registry, and which no legacy branch ever selects, and `resurrect_hero_town()`, whose revived item id and map key the server derives from its own ledger and from the addressed cell, discarding any client-supplied syringe count exactly as a client-sent prize is discarded by `complete_collection_town(collection_id)`

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

#### Scenario: Unit movement needs no server round trip

- **WHEN** the client reads a unit row's placement, and when headless tests resolve a unit's committed footprint and velocity through the content registry
- **THEN** both are read from the already-loaded registry and the committed row with no request issued and no compatibility route added, and no travel time, path, or interpolation is computed from them

#### Scenario: Unit animation needs no server round trip
- **WHEN** the client reads a unit's recorded animation labels, and when headless tests read the committed converted unit package's frame positions and frame counts
- **THEN** both are read from committed bytes already on disk with no request issued and no compatibility route added, and no duration, loop, state machine, or transition is computed from them

#### Scenario: The revival intent derives what the client must not send
- **WHEN** the client revives a unit
- **THEN** it sends only a player identifier and a cell, the service derives the item id, the map
  key, and the resulting ledger state from its own state, and no client-supplied outcome, price,
  or quantity is trusted
