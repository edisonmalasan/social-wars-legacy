# Spec Delta

## MODIFIED Requirements

### Requirement: No experience is awarded from a client amount

The client SHALL NOT award unit experience. It MAY read and report a placed row's recorded
experience value as **content**, and SHALL record that the only legacy command writing it takes
the amount from the client, with an optional client-supplied level used only in a printed
message. The client SHALL NOT compute, grant, or display an experience award arising from
production. The recorded contract SHALL state that the field has **no reader** anywhere in the
legacy source — written twice and read zero times — so the reason no award is reproduced is the
untrusted amount, **not** the corpus's contents. The capability SHALL record the fresh corpus's
absence of the field on its placed rows as a **fact about that corpus**, explicitly distinct
from the repository-wide evidence: the field is present on many rows of other committed save
documents. That repository-wide evidence, and the executed behaviour of the branch, are recorded
by the `godot-unit-experience` capability; this capability's own claim is only that **no
experience is awarded**.

#### Scenario: A recorded experience value is read, not awarded

- **WHEN** a placed row carries a recorded experience value
- **THEN** the value is reported as content, and no experience is awarded, granted, or computed from it

#### Scenario: The client-supplied amount is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that the only legacy command writing the field takes its amount from a client argument and uses an optional client-supplied level only in a print

#### Scenario: No production experience is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no experience is awarded on production, that no legacy branch reads the field, and that the fresh corpus carries the field on none of its placed rows **labelled as a fact about that corpus rather than as evidence about the repository**

#### Scenario: The repository's other evidence is pointed to, not restated as absence

- **WHEN** a reader consults this capability alone
- **THEN** they are **pointed to `godot-unit-experience`** for the field's presence on other committed save documents and for the branch's executed behaviour, so they cannot conclude from this capability that the field exists nowhere in the repository — which would be false

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
fixture was captured for production, because no production behaviour exists to capture** rather
than because
**the server's death and resurrection mechanism is recorded by the
`godot-unit-behaviors` capability rather than denied here** — this line's claim that death and
resurrection are unreachable **and unimplemented** stays **true of the delivered client**, which
sends no death intent and revives nothing, but it left the server behaviour unstated, and the
server does implement both halves of a resurrectable-unit counter; and no
windowed capture is claimed. This non-claim is **scoped to production**: the
`add_xp_unit` branch is not production, its executed behaviour **is** captured, and that capture
is recorded by the `godot-unit-experience` capability rather than denied here.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-production/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture is claimed
- **WHEN** this capability's documentation is read
- **THEN** it states that neither a windowed capture nor an executed-legacy **production**
  fixture is claimed, and distinguishes "no mechanism exists" from "the corpus could not
  exercise it" — the scope is **production**, because the `add_xp_unit` branch is not
  production and its executed behaviour **is** captured, by the `godot-unit-experience`
  capability

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

#### Scenario: The production non-claim is scoped, not contradicted
- **WHEN** this requirement's non-claim about the missing executed-legacy fixture is read
- **THEN** it states that the claim is **scoped to production behaviour**, and it **points to `godot-unit-experience`** for the `add_xp_unit` capture — so a reader consulting this capability alone cannot conclude that the branch has no executed evidence at all, which would be false