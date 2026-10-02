# Spec Delta

## Purpose

Expose the two-track research counter vector as a typed, server-authoritative projection — both tracks,
all three counters verbatim, the four legacy branch effects recorded as data, the `fast_forward` writer
named, the committed track-to-building mapping reported without being used, and the explicit absence of
any price, bound, readiness rule, or reward.

## ADDED Requirements

### Requirement: The research counter vector is projected for both tracks, verbatim

The client SHALL expose a player's research state as a typed, read-only projection carrying **both**
tracks and, for each, all **three** counters — the step counter, the item counter, and the research
instant — each reported **exactly as recorded**. The projection SHALL report **no** counter derived from
another: no remaining time, no progress ratio, no completion fraction, no derived step count, and no value
reconstructed from a building, a cost, or a schedule. A research state that is absent, is not a list, has
the wrong length, holds a non-integer, or holds a negative value SHALL be reported as **unresolvable with
its recorded state intact**, never defaulted to a zero vector presented as a resolved one.

#### Scenario: Both tracks and all three counters are reported verbatim

- **WHEN** a player's research state is projected
- **THEN** each track's step counter, item counter, and research instant are reported exactly as recorded, with no value derived from another

#### Scenario: No counter is derived from another

- **WHEN** the projection reports a track's counters
- **THEN** it derives no remaining time, progress ratio, completion fraction, or step count from them, and reconstructs nothing from a building, a cost, or a schedule

#### Scenario: An unresolvable vector is reported, not defaulted

- **WHEN** a player's research state is absent, is not a list, has the wrong length, or holds a non-integer or negative value
- **THEN** the projection reports it as unresolvable with its recorded state intact, and never presents a zero vector as a resolved one

### Requirement: The four legacy branch effects are recorded as data, not recomputed

The client SHALL record the effect of each of the **four** legacy research branches as data, naming the
counters each touches and the exact recorded change: the step branch **increments the step counter** and
**stamps the research instant**; the cash branch **zeroes the research instant and charges nothing**; the
item branch **increments the item counter** and **resets the step counter and the research instant
together**; and the reset branch **zeroes all three counters**. The recording SHALL state that the item
branch's step reset and instant reset happen **together** in one branch, and SHALL derive no rule beyond
the four recorded effects.

#### Scenario: Each branch's counter effect is recorded

- **WHEN** the branch-effect inventory is inspected
- **THEN** each of the four branches carries its exact recorded effect, and the count of branches matches the committed source

#### Scenario: The paired reset is recorded as paired

- **WHEN** the item branch's effect is reported
- **THEN** it records that the step counter and the research instant are reset together in the same branch, not independently

#### Scenario: The cash branch is recorded as charging nothing

- **WHEN** the cash branch's effect is reported
- **THEN** it records that the branch reads a cash value, discards it, and moves no stored resource

### Requirement: Both research tracks are named, and their committed building ids are reported but not used

The client SHALL report the two research tracks with their committed names and the committed building
identifiers those names resolve to. It SHALL record that the track name constants appear **only** inside
the legacy branch comments and are **defined nowhere** in the server, so the mapping is derived from the
comment's own word order together with the committed building identifiers. The mapping SHALL be reported
as content and SHALL NOT be used to derive any counter value, any unlock, any requirement, or any cost.

#### Scenario: Both tracks and their committed ids are reported

- **WHEN** the track inventory is inspected
- **THEN** it reports both tracks by their committed names and the committed building identifier each resolves to

#### Scenario: The mapping is reported and never used

- **WHEN** a counter value, an unlock, or a cost would require the track-to-building mapping
- **THEN** the projection refuses, because the track name constants are undefined in the server and the mapping supports no derivation

### Requirement: `fast_forward` is recorded as a fourth writer of the research instant

The client SHALL record that the research instant is additionally written by the legacy fast-forward
command, which subtracts a **client-supplied** number of seconds from every track's research instant and
clamps each at zero, and SHALL name that command as a **fourth writer** alongside the four branches. The
client SHALL implement **no** fast-forward operation and SHALL derive no elapsed-time behaviour from the
research instant, recording instead that nothing in the server reads it to decide anything.

#### Scenario: The fourth writer is recorded

- **WHEN** the writers of the research instant are inventoried
- **THEN** the four branches and the fast-forward command are all recorded, with the fast-forward command named as making the instant client-writable

#### Scenario: No fast-forward operation is delivered

- **WHEN** the delivered operations are inspected
- **THEN** no fast-forward operation exists, and no elapsed-time or readiness computation is derived from the research instant

### Requirement: A research action is a server-derived intent, and no client value is trusted

The compatibility service SHALL expose one operation per legacy branch, each accepting **only** a player
identifier and a research track. It SHALL derive every counter value, every research instant, and every
reset server-side, and SHALL ignore any client-supplied counter, timestamp, or cash value rather than
persisting or charging it. It SHALL refuse a request whose track is not an integer, or whose research
state is not resolvable, each with a **named** refusal code, an **empty** payload, and **no** state change.
A successful action SHALL return the resulting server-derived state for the addressed track and SHALL NOT
echo any ignored client value.

#### Scenario: The client sends a player identifier and a track only

- **WHEN** a research action is requested
- **THEN** the request carries only the player identifier and the track, and the service derives every counter value and research instant rather than accepting them

#### Scenario: A client-supplied cash value is ignored

- **WHEN** a cash-branch request carries a cash value
- **THEN** the value is ignored, the response reports no consumed cash, and the recorded state shows the client's value had no effect

#### Scenario: A structurally invalid request is refused

- **WHEN** the track is not an integer, or the player's research state is not resolvable
- **THEN** the operation is refused with a named code, an empty payload, and no state change

### Requirement: No research price is charged, and every stored resource is proven unchanged

The client and the compatibility service SHALL charge **no** price and SHALL move **no** stored resource
for any research action. Every action's post-execution proof SHALL establish that **every** stored resource
is unchanged, comparing the **complete** stored resource set rather than a selected subset, so that no
action can move a balance through an uncompared slot. No cost, price, or debit SHALL be derived from any
committed field, and the absence of committed research content SHALL be recorded as a finding rather than
filled with an invented schedule.

#### Scenario: No resource moves on any research action

- **WHEN** a research action succeeds
- **THEN** every stored resource is byte-identical before and after, and the proof compares the complete stored resource set

#### Scenario: The absent content is recorded, not filled

- **WHEN** the committed content is inspected for a research cost, step count, unlock requirement, or reward
- **THEN** the absence of every one of them is recorded, and no schedule, price, or requirement is invented to fill it

### Requirement: Executed-legacy behaviour fixtures are captured

The change SHALL capture executed-legacy behaviour fixtures for the research branches, recording each
branch's request and the committed corpus state before and after execution, and SHALL replay them as
parity tests. The fixtures SHALL be captured in a **disposable copy** of the corpus and SHALL leave the
committed corpus byte-identical. Because the committed corpus holds every research counter at its initial
value, this line SHALL record **no** absence of a fixture and SHALL NOT claim the corpus cannot exercise
this subsystem.

#### Scenario: A fixture is captured for each branch

- **WHEN** the evidence step runs
- **THEN** an executed-legacy fixture exists for each of the four branches, recording its request and the corpus state before and after

#### Scenario: The committed corpus stays byte-identical

- **WHEN** fixture capture completes
- **THEN** the committed corpus is byte-identical to its pre-capture state, and capture occurred only inside a disposable copy

### Requirement: Research evidence and claim limits

The change SHALL commit a deterministic `research-report-v1` report recording the counter vector, the four
branch effects, both tracks with their committed building identifiers, the fast-forward writer, the
recorded absence of committed research content, and the explicit non-claims, byte-identical across reruns.
The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no research price is
charged and no stored resource moves**; **no completion, readiness, remaining-time, or unlock semantics are
implemented**, because the counters are read by nothing; **no counter bound, membership rule, or clamp is
added**, the legacy branches having none; **no reward is paid**; **no committed research content is
invented**, none existing; **the track-to-building mapping is reported and never used**; **no fast-forward
operation is delivered**; the counters have **no in-game consumer**, so the delivered feature is observable
only as these counter transitions; **no pixel parity is claimed**; and **no windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/research/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: The feature's observable scope is stated

- **WHEN** this capability's documentation is read
- **THEN** it states that the counters have no in-game consumer, that the delivered feature means these counter transitions and nothing more, and that no price, readiness, bound, or reward is claimed