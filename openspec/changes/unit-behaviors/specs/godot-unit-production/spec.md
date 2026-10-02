# Spec Delta

## MODIFIED Requirements

### Requirement: Unit-production evidence and claim limits

The change SHALL commit a deterministic `unit-production-report-v1` report recording the
row-entry inventory with each item id's source and classification, the committed training-time
distribution with its zero-consumer statement, the recorded experience-award contract, the
acquisition-route findings, the corpus measurement, the established-versus-derived split, and
the explicit non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash,
Ruffle, ActionScript, or browser executed; **no production mechanism, completion, or readiness
is implemented**; **no unit is created, trained, or placed**; **no duration is derived from the
committed training time**; **no experience is awarded**; **no acquisition is implemented or
claimed**, and the committed acquisition tables are read by no legacy **command branch**, so no
acquisition is derived from either; **no executed-legacy
fixture was captured, because no production behaviour exists to capture** rather than because
**the server's death and resurrection mechanism is recorded by the
`godot-unit-behaviors` capability rather than denied here** — this line's claim that death and
resurrection are unreachable **and unimplemented** stays **true of the delivered client**, which
sends no death intent and revives nothing, but it left the server behaviour unstated, and the
server does implement both halves of a resurrectable-unit counter; and no
windowed capture is claimed.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-production/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture is claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that neither a windowed capture nor an executed-legacy fixture is claimed, and distinguishes "no mechanism exists" from "the corpus could not exercise it"

#### Scenario: The server's death mechanism is recorded, not denied
- **WHEN** this requirement's non-claim about death and resurrection is read
- **THEN** it states that the claim is **scoped to the delivered client**, which sends no death
  intent and revives nothing, and it **points to `godot-unit-behaviors`** for the server behaviour
  it previously left unstated — so a reader consulting this capability alone cannot conclude
  the server has no death model at all, which would be false

#### Scenario: The delivered client's inaccessibility is unchanged
- **WHEN** the delivered client's capabilities are inspected
- **THEN** it still exposes no death and no revival operation, so the claim that death and
  resurrection are unreachable **from the delivered client** is unaffected by the record of the
  server-side mechanism
