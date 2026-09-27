# Spec Delta

## Purpose

Boot the Godot client against a Compatibility API v0 that adapts the unchanged legacy boot surface, with executed-legacy fixtures as the parity oracle, so the client can initialize a session and load bootstrap data without Flash, without modifying legacy behavior, and without leaving the loopback boundary.

## ADDED Requirements

### Requirement: Compatibility API v0 bootstrap service
The repository SHALL provide a Compatibility API v0 service that serves modern JSON bootstrap data by adapting the unchanged legacy boot modules in-process, listens only on loopback at an explicit documented port, fails closed with structured JSON errors on inputs it cannot resolve, and never persists state: calling the service SHALL leave every on-disk save byte-identical while the legacy in-memory boot semantics execute exactly as the legacy endpoints perform them.

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
The Godot client SHALL depend on a `GameApi` autoload for every server interaction, exposing typed `list_sessions()` and `get_bootstrap()` operations with two interchangeable implementations — `LegacyV0Api`, speaking JSON over loopback HTTP to Compatibility API v0, and `FakeApi`, serving committed fixture data with no process, server, or socket — and no boot or presentation code SHALL reference `command.php`, AMF, FlashVars, legacy form encoding, legacy URLs, or legacy command names.

#### Scenario: Boot offline with the fake implementation
- **WHEN** headless tests run with the fake implementation selected
- **THEN** session list and bootstrap resolve from committed fixture data with no server or network involved, producing the same typed shapes the live implementation returns

#### Scenario: Boot live against Compatibility API
- **WHEN** the legacy-v0 implementation requests session list and bootstrap against a running Compatibility API v0
- **THEN** it yields the same typed boot data the fake implementation produces and the boot scene consumes it without presentation-code changes beyond the implementation switch

#### Scenario: Keep legacy transport out of the UI
- **WHEN** the project scripts are scanned by the scope test
- **THEN** only the legacy-v0 implementation references the compat endpoint and no script contains the forbidden legacy protocol tokens

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
