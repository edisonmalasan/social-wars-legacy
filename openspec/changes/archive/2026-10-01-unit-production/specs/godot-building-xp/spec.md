# Spec Delta

## MODIFIED Requirements

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
because no legacy branch reads the committed reward fields; unit experience and tutorial progression are out of scope because the corpus cannot
exercise them — unit **experience** because no placed corpus row carries
`attr["xp"]` **and the only legacy command writing that field takes its amount from a
client argument**, so no trusted experience award exists to reproduce and none is implemented (the `godot-unit-production` capability records that refusal), and the player-owned unit **instance** because the corpus contains no unit row
at all, which the `godot-unit-instances` capability now specifies separately and where the same
limitation is recorded as a claim limit rather than worked around; the committed
thresholds are preserved verbatim and nothing is rebalanced; and parity covers one
recorded transaction against the fresh-player corpus. The report SHALL be byte-identical
across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the level readout and the structural report are committed under `apps/client-godot/evidence/building-xp/`, and the report carries the curve facts, the derived and recorded levels, the provenance split including the rejected alternative, and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: The unit-instance gap is specified elsewhere, not forgotten
- **WHEN** this requirement's out-of-scope note is read
- **THEN** it distinguishes unit experience (no placed row carries `attr["xp"]`) from the unit instance (the corpus contains no unit row at all), and it points to the `godot-unit-instances` capability rather than leaving the instance half unowned

#### Scenario: The unit-experience gap names why no award is reproduced
- **WHEN** this requirement's out-of-scope note about unit experience is read
- **THEN** it states that no placed corpus row carries `attr["xp"]` and that the only legacy command writing it takes a client-supplied amount, points to the `godot-unit-production` capability for that refusal, and claims no experience award arising from production
