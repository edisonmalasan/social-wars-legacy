# Spec Delta

## MODIFIED Requirements

### Requirement: Construction evidence, provenance, and claim limits

The change SHALL commit a windowed capture of a completed construction sequence together with a deterministic structural report recording its inputs and digests, the intent and its resolved action, the derived duration together with the committed field it came from, both rows, the click counter, the countdown, the request counts, and explicit non-claims, and every artifact SHALL distinguish the parts of the contract that are **established** from committed legacy source and executed-legacy evidence (the three commands' argument shapes and effects, that they write only the row's timestamp and attribute bag, that the click counter is seeded by the purchase half, the start countdown's recorded shape, and that no server-side completion rule exists) from the parts that are **derived** and never observed from the Flash client (that a real construction sends these commands, that the duration is the item's committed build time rather than its activation field or a speedup-adjusted figure, and the automatic timing of the legacy client's loop). The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no building cost is claimed**; the click threshold and the remaining time are client-side derivations with no server enforcement; construction speedups and their recorded price are out of scope; the friend-assist mechanism is out of scope, so no friend can be hired or finished here; the legacy command that clears the attribute bag is never used as a cancel; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists. The report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing a building under construction and the structural report are committed under `apps/client-godot/evidence/building-construction/`, and the report carries the established-versus-derived split and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly


#### Scenario: The construction-click counter's committed source is named
- **WHEN** the deliberately unconsumed construction-click counter is read
- **THEN** it names `clicks_to_build` as the committed field whose **single** legacy consumer
  seeds it at placement, records that the field has exactly **one** legacy read and is
  therefore **not** a zero-consumer field, and states that `godot-unit-behaviors` references that
  relationship while **reimplementing nothing**, so the counter keeps exactly one owner
