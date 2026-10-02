# Spec Delta

## MODIFIED Requirements

### Requirement: Sell evidence and claim limits

The change SHALL commit a windowed capture of a completed sale together with a deterministic structural report recording its inputs and digests, the sell intent, the removed building's row and cell, the placement and object counts and resources before and after, the request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the derived sell reason and the neutral price vector are derived, never observed from the Flash client; **no refund is claimed**, because the committed configuration records no building-sale refund rule and the legacy refund travels in client-sent deltas this contract refuses; the legacy combat reason is never reached, which is what closes the dead-hero path in practice **and** that same guard is the only door into the server's dead-hero counter, as the `godot-unit-behaviors` capability records in full; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town without the sold building and the structural report are committed under `apps/client-godot/evidence/building-sell/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly


#### Scenario: The combat-reason guard is the death path's only door

- **WHEN** this requirement's claim that the combat reason is never reached is read
- **THEN** it records that the identical guard in the `sell` branch is the **only** way the legacy
  server increments its dead-hero ledger, so the derived sell reason this capability sends is
  the concrete reason the death path is closed in practice — a reader cannot mistake the
  closed door for the absence of a mechanism
