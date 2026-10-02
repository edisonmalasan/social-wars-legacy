# Spec Delta

## Purpose

Expose the six legacy quest branches as a typed, server-authoritative surface — the quest-state
projection, the branch inventory including the branch that mutates nothing, the committed-content
inventory, the refused `end_quest` destruction count, and the committed quest fields recorded as content
with zero consumers.

## ADDED Requirements

### Requirement: The quest state is projected verbatim and fails closed

The client SHALL expose a player's quest state as a typed, read-only projection carrying the `goals`
list, the `questsRank` map, the `currentQuestVars` map, the `questTimes` map, the current mission
identifier, the last-chapter instant, and the unlocked-quest index, each reported **exactly as recorded**
with **no** value derived from another. It SHALL derive **no** completion state, **no** remaining time, **no**
progress ratio, and **no** reward. A quest state that is absent, is of the wrong type, or holds a
malformed element SHALL be reported as **unresolvable with its recorded state intact**, never defaulted to
an empty value presented as a resolved one — and a **null** `currentQuestVars` SHALL be reported as a
recorded null rather than treated as an empty map.

#### Scenario: Every recorded quest field is reported verbatim

- **WHEN** a player's quest state is projected
- **THEN** the goals list, the rank map, the quest-variable map, the quest-time map, the current mission identifier, the last-chapter instant, and the unlocked-quest index are each reported exactly as recorded

#### Scenario: No quest value is derived from another

- **WHEN** the projection reports the quest state
- **THEN** it derives no completion state, remaining time, progress ratio, or reward from any recorded field

#### Scenario: A null quest-variable field is reported as null

- **WHEN** a player's quest-variable field is recorded as null
- **THEN** the projection reports that recorded null and never presents an empty map in its place

#### Scenario: A malformed quest state is reported, not defaulted

- **WHEN** a quest state is absent, is of the wrong type, or holds a malformed element
- **THEN** the projection reports it as unresolvable with its recorded state intact, and never presents an empty value as a resolved one

### Requirement: The six-branch command inventory records what each branch reads and writes

The client SHALL record the inventory of the six legacy quest branches, and for each SHALL record what it
reads, what it writes, and whether it mutates anything at all. The recorded facts SHALL include that
**`complete_goal` writes nothing at all**, that `set_goals` delegates its write to an engine helper which
stores a client-sent progress pair and **grows the goals list on demand**, that `set_quest_var` writes
**any** client-supplied key, that `collect_mission` writes a **stringified** mission identifier where the
corpus records an **integer**, clears the quest-variable map, and **wraps** an out-of-range identifier
rather than rejecting it, and that `admin_set_quest_rank` writes a client-sent key and value with no bound.

#### Scenario: Each branch's reads and writes are recorded

- **WHEN** the branch inventory is inspected
- **THEN** each of the six branches carries its recorded reads, its recorded writes, and an explicit statement of whether it mutates anything, and the branch count matches the committed source

#### Scenario: The no-op branch is recorded as a no-op

- **WHEN** the inventory describes the goal-completion branch
- **THEN** it records that the branch resolves the committed title, prints it, and **mutates no state**, so no completion flag, ledger, or reward exists

#### Scenario: The on-demand list growth is recorded

- **WHEN** the inventory describes the goal-progress branch
- **THEN** it records that the goals list grows on demand from a client-sent goal identifier with **no upper bound**

#### Scenario: The stringified identifier and the wrap are recorded

- **WHEN** the inventory describes the chapter-advance branch
- **THEN** it records that the mission identifier is written as a **string** where the committed corpus records an **integer**, that the quest-variable map is cleared, and that an identifier above the recorded bound **wraps** rather than being rejected

### Requirement: The `end_quest` destruction count is refused, and the refusal is recorded as a divergence

The service SHALL **refuse** to destroy placed rows on an `end_quest` request, because the legacy branch
computes the destroyed count from a **client-supplied** tuple and this contract rejects client-dictated
outcomes. It SHALL accept the recorded outcome and quest identifier, derive what it legitimately can, and
SHALL leave **every** placed row **byte-identical**, proving the refusal with a post-execution comparison
over the **complete** placed-row set. It SHALL record the refusal as a **divergence from the legacy
server's behaviour** rather than as achieved parity, and SHALL refuse a request whose recorded quest
identifier is missing with a **named** code, an **empty** payload, and **no** state change.

#### Scenario: The destruction count is refused

- **WHEN** an `end_quest` request carries a client-computed destroyed-unit count
- **THEN** the service destroys nothing, every placed row is byte-identical before and after, and the post-execution proof compares the complete placed-row set

#### Scenario: The refusal is recorded as a divergence

- **WHEN** this capability's documentation is read
- **THEN** it states that the legacy server destroys rows on this command and the modern service deliberately does **not**, and names the difference a divergence rather than parity

#### Scenario: A request with no quest identifier is refused

- **WHEN** an `end_quest` request carries no recorded quest identifier
- **THEN** the operation is refused with a named code, an empty payload, and no state change

### Requirement: No quest reward is paid and no stored resource moves

The client and the service SHALL pay **no** quest reward and SHALL move **no** stored resource for any
quest action, because the committed reward field has **zero** legacy consumers and is **uniformly the same
value** on every committed entry, so deriving a payout from it would fabricate an economy. Every quest
action's post-execution proof SHALL establish that **every** stored resource is unchanged, comparing the
**complete** stored resource set rather than a selected subset. No reward, credit, cost, or requirement
SHALL be derived from any committed quest field.

#### Scenario: No resource moves on a quest action

- **WHEN** a quest action succeeds
- **THEN** every stored resource is byte-identical before and after, and the proof compares the complete stored resource set

#### Scenario: The uniform reward value is not a payout

- **WHEN** the committed reward field is inspected
- **THEN** its measured zero-consumer status and its uniform value are reported, and no amount, credit, or requirement is derived from it

### Requirement: The committed quest-content inventory is reported and never used

The client SHALL record which committed quest fields any legacy module reads, and SHALL report that only
the identifier and the title have consumers while every other committed field has **zero**, naming the
reward field among them and recording its uniform value. The projection SHALL use the committed quest
content **only** to resolve an identifier and read its title, and SHALL derive **no** reward, cost,
requirement, schedule, or completion rule from it. **No delivered code identifier or computation SHALL be
named after the reward field**, so the "reported, never used" claim is mechanically checkable.

#### Scenario: Only the identifier and title have consumers

- **WHEN** the committed-content inventory is inspected
- **THEN** it records the measured consumer count for each committed field and states that every field other than the identifier and the title has zero

#### Scenario: No computation is named after the reward field

- **WHEN** the delivered module is inspected
- **THEN** no code identifier or computation is named after the committed reward field, so a later reader cannot mistake the reported uniform value for a derived payout

#### Scenario: The unlocked-quest index is reported, never written

- **WHEN** the unlocked-quest index is projected
- **THEN** it is reported as recorded content and is **never** written by any delivered operation, because it has zero legacy consumers

### Requirement: A quest action is a server-derived intent, and no client outcome is trusted

The service SHALL expose the legacy quest branches that legitimately mutate state, each accepting **only** a
player identifier and the branch's own addressing. It SHALL derive every stored value it writes,
SHALL ignore any client-supplied progress pair, key, value, rank, or outcome rather than persisting it
unchecked, and SHALL refuse a structurally invalid request with a **named** code, an **empty** payload, and
**no** state change. It SHALL accept an invented quest-variable key, as the legacy branch does, and SHALL
refuse the one key the legacy branch itself ignores, because that is a recorded legacy behaviour rather
than an absence. A successful action SHALL return the resulting server-derived state and SHALL NOT echo
any ignored client value.

#### Scenario: The client sends intent only

- **WHEN** a quest action is requested
- **THEN** the request carries only a player identifier and the branch's addressing, and the service derives the values it writes rather than accepting them

#### Scenario: An invented quest-variable key is accepted

- **WHEN** a quest-variable key outside the eight the legacy comment enumerates is sent
- **THEN** it is accepted and persisted, matching the legacy branch, while the branch's one explicitly ignored key is refused

#### Scenario: A structurally invalid request is refused

- **WHEN** the addressing is missing or of the wrong type, or the quest state is unresolvable
- **THEN** the operation is refused with a named code, an empty payload, and no state change

### Requirement: Quest timing is recorded as client-writable and never delivered

The client SHALL record that the legacy fast-forward command writes quest state by subtracting a
**client-supplied** number of seconds from every recorded quest time and from the last-chapter instant, and
SHALL name it as a **quest-state writer** distinct from the six branches. The client SHALL implement **no**
fast-forward operation and SHALL derive **no** elapsed-time behaviour from any quest instant, recording
instead that no legacy branch reads a quest instant to decide anything. It SHALL record the committed
save-migration initialization of the quest-time map as a **migration path**, not as gameplay behaviour.

#### Scenario: The fast-forward writers are recorded

- **WHEN** the writers of quest state are inventoried
- **THEN** the six branches and the fast-forward command are all recorded, with the fast-forward command named as making quest timing client-writable

#### Scenario: No fast-forward operation is delivered

- **WHEN** the delivered operations are inspected
- **THEN** no fast-forward operation exists, and no elapsed-time or completion computation is derived from any quest instant

#### Scenario: The migration initialization is not gameplay

- **WHEN** the quest-time map's initialization is recorded
- **THEN** it is recorded as a committed save migration from a null value to an empty map, and not as quest behaviour

### Requirement: No executed-legacy behaviour fixture absence is claimed

The change SHALL capture executed-legacy behaviour fixtures for the quest branches, recording each
branch's request and the committed corpus state before and after execution, and SHALL replay them as parity
tests. The fixtures SHALL be captured in a **disposable copy** of the corpus and SHALL leave the committed
corpus byte-identical. Because the committed corpus holds every quest field at its initial value, this
line SHALL record **no** absence of a fixture and SHALL NOT attribute any missing fixture to a corpus
limitation.

#### Scenario: A fixture is captured for each branch

- **WHEN** the evidence step runs
- **THEN** an executed-legacy fixture exists for each of the six branches, recording its request and the corpus state before and after

#### Scenario: The committed corpus stays byte-identical

- **WHEN** fixture capture completes
- **THEN** the committed corpus is byte-identical to its pre-capture state, and capture occurred only inside a disposable copy

### Requirement: Quest evidence and claim limits

The change SHALL commit a deterministic `quests-report-v1` report recording the quest-state projection, the
six-branch inventory with each branch's reads and writes, the committed-content inventory with its
measured consumer counts, the refused destruction count and the client-writable timing, and the explicit
non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash, Ruffle, ActionScript, or
browser executed; **no quest reward is paid and no stored resource moves**; **the destruction count is
refused** and the difference from the legacy server is a **divergence**, not parity; **no bound is added**
to the on-demand goals list, so a client-supplied identifier can still grow it and that is a Server v1 /
M13 gap; **no membership test is added** to the quest-variable writer; **the unlocked-quest index is
reported and never written**; **no fast-forward operation is delivered**; **no completion state exists**
because the goal-completion branch mutates nothing; the committed content is **reported and never used**;
**no pixel parity is claimed**; and **no windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/quests/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: The refusals are stated, not implied

- **WHEN** this capability's documentation is read
- **THEN** it states that no reward is paid, that the destruction count is refused as a divergence, that no bounds or membership rules were added, and that the goal-completion branch mutates nothing