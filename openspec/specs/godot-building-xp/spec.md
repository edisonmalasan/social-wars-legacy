# godot-building-xp

## Purpose

Close the town-building loop progression: show the player where they stand on the committed level curve, say plainly when the recorded level disagrees with what the curve implies, and let a level advance through one guarded intent whose target the service derives.

## Requirements

### Requirement: Committed-curve level model
The client and the service SHALL derive the player's level from the committed level
schedule and the player's stored experience, never from a client-supplied level. The
schedule's index SHALL be interpreted as one-based — stored level *n* corresponds to
schedule entry *n* minus one — and that conversion SHALL exist in exactly one named
place shared by the client model, the endpoint, the tests, and the structural report,
with its boundary cases covered. That interpretation SHALL be recorded as
derived-provisional wherever the derivation is recorded, together with the rejected
zero-based alternative and the reason it is rejected. The schedule's committed
experience thresholds SHALL be preserved verbatim: no value SHALL be rebalanced,
smoothed, or interpolated.

#### Scenario: The derived level follows the committed curve

- **WHEN** a player's stored experience is compared against the committed thresholds
- **THEN** the derived level is the highest level whose threshold the experience meets, using the one-based conversion, and no other input determines it

#### Scenario: The conversion is one named place

- **WHEN** the client model, the service, the tests, and the structural report are inspected
- **THEN** each resolves the schedule index through the same single named conversion, and no component indexes the schedule by its own arithmetic

#### Scenario: Every boundary is covered

- **WHEN** the model is exercised with experience below the first threshold, exactly on a threshold, between thresholds, and above the final threshold
- **THEN** each case yields the level the one-based conversion implies, with no off-by-one at any boundary

#### Scenario: The interpretation is recorded where it is used

- **WHEN** the conversion is recorded in the model, the envelope module, the fixture README, the application documentation, or the structural report
- **THEN** it is marked derived-provisional and the rejected zero-based reading is stated with the evidence that contradicts it

### Requirement: Level and progress readout
The readout SHALL show the player's derived level, that level's committed name, the
stored experience, the next level's committed threshold, and the experience remaining to
reach it. It SHALL NOT present the level's reward, because the committed schedule's
reward fields are consumed by no legacy behaviour and paying them would invent an
economy. A level with no committed name SHALL be reported as such rather than guessed.

#### Scenario: The readout shows the whole position

- **WHEN** a player views their progression
- **THEN** the derived level, its committed name, the stored experience, the next level's threshold, and the remaining experience are all displayed from committed content and the stored experience

#### Scenario: No reward is shown or implied

- **WHEN** the readout renders a level
- **THEN** no reward amount or reward type from the committed schedule appears, and no gate is derived from one

#### Scenario: A missing name is reported, not invented

- **WHEN** the derived level has no committed name
- **THEN** the readout states that the name is absent rather than substituting a placeholder that could be read as a real value

### Requirement: Stored-versus-derived disagreement is reported
The recorded level SHALL be treated as unverified against the committed curve, because
the legacy service writes it from a client-supplied integer with no validation. When the
recorded level and the level derived from the stored experience agree, the readout SHALL
say they agree. When they disagree, the readout SHALL state the disagreement explicitly,
naming both values and the experience that separates them, and SHALL NOT silently prefer
either value, reconcile them, or rewrite the save.

#### Scenario: Agreement is stated

- **WHEN** the recorded level equals the derived level
- **THEN** the readout reports agreement and no disagreement is raised

#### Scenario: Disagreement is surfaced with both values

- **WHEN** the recorded level differs from the derived level
- **THEN** the readout reports the disagreement and names both the recorded and the derived level together with the stored experience that separates them

#### Scenario: Neither value is silently preferred

- **WHEN** a disagreement exists
- **THEN** the readout applies no reconciliation, leaves the save unchanged, and offers no level-up step that would erase the conflict without the player acting

### Requirement: Level-up intent with a service-derived target
The service SHALL expose a level-up endpoint that accepts only the save identity and
derives the allowed target level server-side from the stored experience and the committed
schedule. It SHALL NOT accept a client-supplied level outcome: a client-supplied level
key SHALL be ignored exactly as a client-supplied amount or price is ignored elsewhere,
and a request that does not correspond to the derived level SHALL fail closed with a
structured error and no mutation. It SHALL refuse a request when the recorded level
already equals the derived level, and when the stored experience cannot reach the next
level, answering before any legacy command runs so the corpus is untouched on every
error path. After execution it SHALL require that the recorded level moved to exactly the
derived level and that **every** stored resource is unchanged, failing closed rather than
reporting success otherwise.

#### Scenario: The client cannot dictate the outcome

- **WHEN** a level-up request carries a level value alongside the save identity
- **THEN** the value is ignored, the target is derived server-side from the stored experience and the committed schedule, and the outcome depends on no client-supplied number

#### Scenario: A correct level-up advances the recorded level

- **WHEN** a valid level-up intent is sent and the recorded level differs from the derived level
- **THEN** the unchanged legacy command path executes, the recorded level becomes exactly the derived level, and no stored resource changes

#### Scenario: Nothing to do is refused

- **WHEN** the recorded level already equals the derived level
- **THEN** the service answers a structured error, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: Unreachable experience is refused

- **WHEN** the stored experience cannot reach the next level
- **THEN** the service answers a structured error, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: A post-state that diverges fails closed

- **WHEN** execution completes but the recorded level did not become exactly the derived level, or any stored resource changed
- **THEN** the service answers a structured error instead of the legacy success, and the failure is reported rather than hidden

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, or the save id is missing, invalid, or unknown
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no level is written

#### Scenario: Persist into the corpus only

- **WHEN** a level-up executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with level-up execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Typed level-up operation
The client SHALL depend on a typed GameApi level-up operation with two interchangeable
implementations, one speaking JSON over loopback HTTP to the service and one serving
committed fixture data with the documented in-memory semantics and no process, server, or
socket. The typed result SHALL carry the derived level, the recorded level before and
after execution, the committed curve facts used, and the current resources, and both
implementations SHALL yield the same shapes so the flow consumes them identically.

#### Scenario: Level up through either implementation

- **WHEN** headless tests run the level-up flow with the fake implementation selected, and a live run levels up against a running Compatibility API v0
- **THEN** both implementations yield the same typed shapes, the flow applies the service's derived level rather than its own arithmetic, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: A structured failure carries no partial payload

- **WHEN** a level-up request fails
- **THEN** the typed result carries the failure and no level, curve, or resource payload that could be mistaken for a success

### Requirement: Level-up client flow
The client SHALL provide a level progression flow over the typed operation: a readout on
the selection-driven surface showing the derived level, its committed name, the stored
experience, the next threshold and the remaining experience, and an explicit agreement or
disagreement line; and a level-up action mutually exclusive with the ten delivered modes,
whose confirm names the derived level as derived and which sends exactly one intent.
Cancelling SHALL send nothing and leave the town byte-identical. On success the flow SHALL
apply **only** the authoritative response — the recorded level and the resources taken
from the response — with a full snapshot-and-rollback, and on any failure it SHALL surface
an explicit error naming the failure with the recorded level unchanged and no balance
moved. The flow SHALL NOT pay a level reward, SHALL NOT offer unit experience, SHALL NOT
advance the tutorial, and SHALL NOT alter the committed curve.

#### Scenario: Advance the level

- **WHEN** the player chooses the level-up action on a progression surface whose recorded level differs from the derived level, and confirms
- **THEN** exactly one intent is sent, and on success the recorded level and the HUD balances take the response values

#### Scenario: Balances move only by the server's numbers

- **WHEN** the client derived a level that differs from the response's
- **THEN** the response wins: the applied level and balances are the response's values, and the client's own arithmetic is discarded rather than added to them

#### Scenario: Nothing to offer, nothing sent

- **WHEN** the recorded level already equals the derived level, or the stored experience cannot reach the next level
- **THEN** no level-up action is offered and any attempt is refused with an explicit reason, with no request sent and the town unchanged

#### Scenario: A failed request moves nothing

- **WHEN** the request fails at transport or returns a structured error, including a post-state the service rejects
- **THEN** an explicit error names the failure, the recorded level keeps its previous value, and the HUD keeps its pre-request balances

### Requirement: XP evidence, provenance, and claim limits
The change SHALL commit a windowed capture of the level readout together with a
deterministic structural report recording the committed curve facts used — the entry
count, the first thresholds, and the corpus's own experience and level — the derived
level, the recorded level before and after, the disagreement state, the input digests,
the request counts, and explicit non-claims. Every artifact SHALL distinguish what is
**established** — that the legacy level command writes the recorded level from a
client-supplied integer with no validation, that the legacy service never reads the
committed schedule, that the schedule's thresholds are strictly increasing, and that no
placed corpus row carries unit experience — from what is **derived-provisional**, which
includes the one-based index interpretation and **the rejected zero-based alternative
with the evidence that contradicts it**. The non-claims SHALL state: no Flash, Ruffle,
ActionScript, or browser executed; the level is the one the committed curve implies for
the stored experience, never one observed from the Flash client; no level reward is paid
because no legacy branch reads the committed reward fields; unit experience and tutorial
progression are out of scope because the corpus cannot exercise them; the committed
thresholds are preserved verbatim and nothing is rebalanced; and parity covers one
recorded transaction against the fresh-player corpus. The report SHALL be byte-identical
across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the level readout and the structural report are committed under `apps/client-godot/evidence/building-xp/`, and the report carries the curve facts, the derived and recorded levels, the provenance split including the rejected alternative, and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation
All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing
locked dependencies and no new packages; legacy sources, configs, saves, villages,
committed fixtures, conversion packages, registry manifests, and the committed M4, M6,
and every delivered gameplay slice's evidence — other than the regenerated per-run
battery report — SHALL remain byte-identical across the change (SHA-256 guards plus the
hash manifest); level-up execution SHALL never write a working-tree save; and both
verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** the parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic XP suite and the live level-up phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record
`AGENTS.md` and the application READMEs SHALL document the exact commands actually
executed — level fixture capture, the XP tests, both batteries — with their purposes, the
loopback port, the evidence paths, the established-versus-derived provenance including
the one-based interpretation and its rejected alternative, and the limits of the level
claim; the committed investigation record SHALL be updated with the resolutions; and the
roadmap Project Status ledger SHALL record the M7 progress this change delivers with
evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record the one-based interpretation as derived-provisional with its rejected alternative

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states that the final M7 deliver line is delivered, and points to the committed evidence for the M7 exit assessment
