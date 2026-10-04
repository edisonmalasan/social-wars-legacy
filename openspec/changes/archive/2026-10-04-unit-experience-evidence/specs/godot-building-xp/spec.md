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
placed row of **this corpus** carries unit experience — from what is
**derived-provisional**, which includes the one-based index interpretation and **the rejected zero-based alternative
with the evidence that contradicts it**. The non-claims SHALL state: no Flash, Ruffle,
ActionScript, or browser executed; the level is the one the committed curve implies for
the stored experience, never one observed from the Flash client; no level reward is paid
because no legacy branch reads the committed reward fields; **unit experience is out of
scope because no trusted award exists** — the only legacy command writing `attr["xp"]`
takes its amount from a client argument with no validation, and the field has **no reader**
anywhere in the legacy source, so no award is derivable and none is implemented (the
`godot-unit-production` capability records that refusal and `godot-unit-experience` records
the executed branch behaviour) — with the corpus figure that no row of this corpus carries
`attr["xp"]` retained **explicitly as a fact about this corpus** and **not** as the reason,
because the field is present on many rows of other committed save documents; the player-owned
unit **instance** because the corpus contains no unit row
at all, which the `godot-unit-instances` capability now specifies separately and where the same
limitation is recorded as a claim limit rather than worked around; **tutorial progression is
not out of scope**, because the `godot-tutorial` capability delivers it; the committed
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
- **THEN** it distinguishes unit **experience** (no trusted award exists because the only writer takes a client amount) from the unit **instance** (the corpus contains no unit row at all), and it points to the `godot-unit-instances` capability rather than leaving the instance half unowned

#### Scenario: The unit-experience gap names why no award is reproduced
- **WHEN** this requirement's out-of-scope note about unit experience is read
- **THEN** it states that the only legacy command writing `attr["xp"]` takes a client-supplied amount and that the field has no legacy reader, points to `godot-unit-production` for that refusal and to `godot-unit-experience` for the executed branch behaviour, and claims no experience award arising from production

#### Scenario: The corpus figure is labelled, never used as the reason
- **WHEN** the unit-experience note is read
- **THEN** the fact that this corpus carries `attr["xp"]` on none of its rows is present **and labelled a fact about this corpus**, and it is not offered as the reason the capability is out of scope — so a reader cannot conclude the field is absent from the repository

#### Scenario: Tutorial progression is not claimed out of scope
- **WHEN** this requirement's non-claims are read
- **THEN** tutorial progression is absent from them and the `godot-tutorial` capability is named, so the note cannot report as out of scope a system that has been delivered and archived