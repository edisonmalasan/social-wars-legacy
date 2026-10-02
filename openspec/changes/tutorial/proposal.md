# Proposal

## Why

M9's deliver list is `XP`, `levels`, `quests`, `research`, `collections`, and
`tutorial/progression`. `quests` and `research` are delivered; `XP`/`levels` and
`collections` are partly delivered and deliberately narrowed; **`tutorial/progression`
has no delivered line at all**, and it is the last item on the list.

The committed investigation (`docs/legacy-m9-tutorial.md`, PR #264) measured that
the legacy tutorial is far smaller than its name suggests — one branch, one
write, one stored field — and that the line does **not** repeat the previous two
lines' refusal shape. It contains exactly **one** executed state transition that
the committed corpus can reach, so an executed-legacy fixture is capturable, and
that is what makes this the right moment to deliver it rather than defer it.

## What Changes

- **New capability `godot-tutorial`**, delivering the tutorial surface:
  - A typed, read-only **tutorial state projection** carrying
    `playerInfo.completed_tutorial` **verbatim**, failing closed on an absent or
    wrongly-typed `playerInfo`. It derives **no** step, **no** progress ratio,
    **no** remaining time, and **no** completion, because the legacy save stores
    no step at all.
  - The branch's **gate recorded as data**: the two arms (`>= 25`, `== 15`), the
    **nine-value hole** between them, the absent upper and lower bounds, and the
    three input shapes the legacy server answers with an unhandled **500**.
  - An **intent-only** operation: the client sends a tutorial step and **never** a
    completion outcome, a stored flag, or a resource vector. Completion is derived
    server-side from the committed disjunction.
  - Three **named refusals** — a non-numeric step, a missing step, and a null step
    — each with a named code, an empty payload, and no state change. These
    replace the legacy 500s and are recorded as a **deliberate divergence in
    failure handling only**: the legacy *state transitions* are reproduced
    exactly, and a 500 is not a behaviour worth preserving.
  - A **no-resource-moved** requirement for every tutorial action, proved against
    the captured transaction in which one client-sent request both completed the
    tutorial and moved all seven stored resources — so the proof is not
    tautological.
  - An **executed-legacy fixture** over the one reachable transition.
- **Modified capability `godot-compatibility-boot`**: the `GameApi abstraction`
  requirement gains the tutorial operation among the typed operations.
- No tutorial reward, step schedule, dialogue, or content is introduced: the
  investigation measured **zero** tutorial content in `config/main.json` at any
  depth and **zero** across all normalized packages.

### Recorded, and explicitly not delivered

These are refusals decided now rather than omissions to be discovered later, and
each is written into the capability spec rather than left implicit:

- **No step is stored.** `tutorial_step` is a local in the legacy branch, never
  persisted, so a partially-progressed save is unrepresentable and "resume the
  tutorial" cannot be expressed in the legacy save shape at all.
- **No un-complete path.** The single write site always writes `1`; there is no
  reset, no migration, and no reader.
- **No completion is derived from the step count**, no reward is paid, and no
  progress is displayed.
- **The flag is write-only in the legacy server** — the tenth committed field in
  this project with no legacy consumer. Nothing is read from it to decide
  anything.
- **The client's step is untrusted.** It is accepted as *intent* and the gate is
  applied server-side; no client-supplied completion outcome is ever honoured.
- **No server-authoritative validation beyond the closed input domain**: the
  missing upper and lower bounds are reproduced, not closed, because closing them
  is Server v1 / M13's decision.

## Capabilities

### New Capabilities

- `godot-tutorial`: the tutorial state projection, the branch gate recorded as
  data, the intent-only tutorial operation, the three named input refusals, the
  no-resource-moved proof, the executed-legacy fixture, and the evidence
  requirements with their claim limits.

### Modified Capabilities

- `godot-compatibility-boot`: the `GameApi abstraction` requirement adds the
  tutorial operation to the typed operation list, with the intent-only and
  refusal guarantees stated.

## Impact

- **`apps/compat-api/`**: a new `tutorial_envelope.py` (the intent-only envelope
  and its derivation, shared by the capture and the endpoint so the two cannot
  drift), a `/v0/tutorial` endpoint in `compat_service.py`, a
  `capture_tutorial_fixture.py` following the shared capture harness, and the
  matching unittest coverage including executed-legacy parity.
- **`apps/client-godot/`**: a `tutorial_flow.gd` projection and flow module, the
  `GameApi` forwarder, the fake-implementation behaviour, a new hermetic suite
  `test_tutorial.gd`, and a new live phase in `verify-boot.ps1`.
- **`tests/fixtures/godot-tutorial/`**: the executed-legacy fixture and its
  README.
- **`verify.ps1` / `verify-boot.ps1`**: the new hermetic suite and live phase are
  registered, and the expected suite/phase counts rise accordingly.
- **No legacy, config, save, village, content-package, conversion-package,
  registry-manifest, or prior-fixture byte changes.**

**Claim limits carried from the investigation:** parity would cover **one**
transaction against the fresh-player corpus; the gate thresholds are **recorded
verbatim** as the legacy server's rule and are **never** claimed to be what the
Flash client counts as a step; nothing is claimed about how the client renders
tutorial progress, which is established only as far as the wholesale
`playerInfo` inclusion at `get_player_info.py:15`; and no pixel parity and no
windowed capture are in scope, because nothing is rendered.