# Spec Delta

## MODIFIED Requirements

### Requirement: Move evidence and claim limits

The change SHALL commit a windowed capture of a completed move together with a deterministic structural report recording its inputs and digests, the move intent, the moved building's cell before and after, the placement count and resources, the request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the command's argument values, the arguments the legacy branch discards, and the neutral price vector are derived, never observed from the Flash client, so no claim is made about what moving costs in the legacy client; parity covers one recorded transaction against the fresh-player corpus, not progressed players; occupancy and grid-bounds rules are client-side only, with no server-authoritative validation; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing the building at its new cell and the structural report are committed under `apps/client-godot/evidence/building-move/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: A move is not a movement

- **WHEN** a move is executed and this capability's claim limits are read
- **THEN** they record that the move command is **type-agnostic**, so a unit row moves exactly as a building row does, and that the committed `velocity`, `width`, `height`, and `elevation` fields are **read by no legacy branch** — a move therefore travels no distance, consumes no time, and obeys no speed, which the `godot-unit-movement` capability records in full

#### Scenario: The unread fields are not adopted here either

- **WHEN** this capability's surface is inspected for a travel time
- **THEN** none is computed, and the committed fields are neither interpreted as a speed nor used to derive a path, so the delivered move capability does not pre-empt the movement capability's refusal
