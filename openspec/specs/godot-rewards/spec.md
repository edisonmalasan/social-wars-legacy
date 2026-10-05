# godot-rewards

## Purpose

Deliver the M10 `rewards` line. Both preserved reward branches are **real
granting surfaces** rather than closures — each moves private state — but what
each moves is **one cursor and one instant**, and neither grants anything this
contract can reproduce: the item is client-sent, and the preserved server charges
and credits nothing in either branch across both executed arms, so any amount
would be invention.

The line's finding is that **neither cursor can address the whole of the schedule
it would address**, for **two different reasons**, which is why a single figure
would hide half of it. Weekly's derived bound is **5 against 3** rungs, so
positions **3 and 4** name no rung. Daily's bound is **5 against 5** entries —
**no exceedance at all** — and the real defect is a one-based vs zero-based
offset, leaving position **5** unreachable *and* position **0** unreachable.

What the line delivers is therefore the two cursor transitions derived
server-side from recorded state, each derived bound beside its schedule's
cardinality and **the difference in both directions**, the stamped instant, the
committed schedule entries verbatim, and the surrounding undecoded and unread
surface reported rather than invented: the three schedule type letters, the ten
of eleven committed reward schedules no preserved branch consumes, the seven
private-state fields present in every committed save and in no source line, and
the ranking-reward table's split ownership.

**Nothing is granted, selected, priced, credited, charged, or displayed.** No
capability name, identifier, or response field in this capability implies a payout
was paid.

## Requirements

### Requirement: A reward operation carries only an action and a save id, and the delivered surface is a cursor transition rather than a reward

The compatibility service SHALL expose a reward operation whose request carries
**only** an action and a save id, and which derives the resulting cursor
transition **from its own recorded state**. The service SHALL NOT accept a
client-supplied item, item index, cell, player, next id, amount, or price.

The delivered surface SHALL be the cursor transition, the derived bounds, and a
reported addressability gap — **and nothing else**. The service SHALL NOT grant,
select, price, credit, charge, or display any reward. No capability name,
identifier, or response field SHALL imply that a reward was paid.

A client-supplied item, item index, cell, player, next id, amount, or price SHALL
be refused with a named code, an empty payload, and no change to the recorded
state — **refused, not ignored**, because a cursor supplied by the client is the
very value the operation derives, so silently substituting a derived value would
answer success for an input the operation did not honour.

#### Scenario: The client sends an action and a save id only

- **WHEN** a reward operation is requested
- **THEN** the request carries an action and a save id and no item, item index, cell, player, next id, amount, or price, and the service derives the before value, the after value, and the change from its own recorded state

#### Scenario: A client-supplied grant shape is refused by name

- **WHEN** a reward request carries an item, an item index, a cell, a player, a next id, an amount, or a price
- **THEN** the operation is refused with a named code, an empty payload, and no change to the recorded state

#### Scenario: Nothing in the delivered surface implies a payout

- **WHEN** the delivered implementation and its response shape are inspected
- **THEN** no delivered identifier or response field is named after a granted, paid, or awarded reward, and no field reports one

### Requirement: Both cursors are delivered, and their mis-sizing against their own schedules is reported rather than hidden

The operation SHALL deliver both reward cursors as projected recorded state and
SHALL derive each one's successor from the recorded value. The operation SHALL
report, for each cursor, the derived bound, the cardinality of the schedule it
would address, the set of positions the cursor can reach, and the set of those
positions the schedule **cannot** answer.

The operation SHALL NOT select a schedule entry from a cursor value. The weekly
bound is derived from the schedule's **list-valued** entries rather than from its
entry count. The operation SHALL report each cursor's derived bound **beside** its
schedule's cardinality, the positions the cursor reaches, the positions the
schedule answers, and **the difference in both directions** — rather than
emitting either the bound or a single derived figure alone.

The two cursors carry **two different defects**, which is why the difference must
be reported in both directions rather than as one figure:

- **weekly** — the derived bound is **5** against a cardinality of **3**, an
  exceedance of **2**, so positions **3 and 4** name no rung;
- **daily** — the derived bound is **5** against a cardinality of **5**, so the
  exceedance is **0** and there is **no exceedance at all**; the defect is a
  one-based vs zero-based offset, leaving position **5** unreachable *and* position
  **0** unreachable.

A reader who received only an exceedance figure would not know that the daily
cursor cannot reach the first position of its own schedule at all. This
requirement exists because the mismatch is a **cardinality disagreement between
two committed pieces of the same feature** and is **reachable from committed
recorded state**: two committed documents record cursor values whose successors
fall outside their own schedule.

#### Scenario: The cursor successor is derived from the recorded value

- **WHEN** a reward operation succeeds
- **THEN** the addressed cursor's successor equals the recorded value advanced by the derived bound's arithmetic, and the response reports the before value, the after value, and the change

#### Scenario: The weekly bound is derived from the list-valued entries, not the entry count

- **WHEN** the weekly bound is derived
- **THEN** it is the maximum entry length over schedule entries whose value is a list, and it is **not** the schedule's entry count, and the response reports both numbers so the difference is visible

#### Scenario: The unreachable positions are reported, per cursor, in both directions

- **WHEN** a reward operation succeeds
- **THEN** the response reports the positions the cursor can reach, the positions the schedule can answer, and the difference between them **in both directions**, for each of the two cursors

#### Scenario: No cursor-to-schedule selection exists

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper capable of selecting a schedule entry from a cursor value, indexing a schedule by a cursor, or mapping a cursor position to a type letter or an amount, and this absence is enforced by a guard that fails when such a helper is introduced

### Requirement: The daily bound is the recorded hardcoded literal, and the rejected content derivation is retained rather than silently chosen

The operation SHALL apply the daily bound as the **hardcoded literal recorded in
the preserved source** and SHALL NOT derive it from committed content.

That literal's value also equals the entry count of an unread committed schedule,
which is a coincidence of the value distribution and **not** its provenance; the
preserved source contains no reference to that schedule. The design SHALL retain
the rejected content-derivation alternative explicitly, so a later reader cannot
mistake the agreement for a derivation.

The unread schedule SHALL be reported verbatim, and the report SHALL name both the
cursor position the bound permits that the schedule cannot answer and any entry
whose committed value is zero, rather than reporting only the entries a reader
would want to see.

#### Scenario: The daily bound is the recorded literal

- **WHEN** the delivered implementation applies the daily bound
- **THEN** it uses the literal recorded in the preserved source, and no committed reward schedule's entry count is read to obtain it

#### Scenario: The rejected derivation is retained in the record

- **WHEN** the design is read
- **THEN** it names the content-derivation alternative it rejected and why, rather than leaving only the chosen option

#### Scenario: The unread schedule's zero entry and out-of-range position are named

- **WHEN** the unread daily schedule is reported
- **THEN** every entry is reported verbatim including any zero-valued entry, and the cursor position the bound permits that the schedule cannot answer is named explicitly

### Requirement: Nothing is granted, and the four-part post-execution proof makes that non-tautological

The operation SHALL grant **nothing**. Every successful action SHALL carry a
post-execution proof covering all four places a grant could land:

1. **no map row** — the placed-row count is unchanged and every existing row is
   byte-identical;
2. **no bought-units entry** — that list is byte-identical, which also covers the
   preserved helper's deduplicating behaviour;
3. **no storage entry** — the store is byte-identical, which also covers the
   preserved helper's accumulating behaviour;
4. **no stored resource moved** — the **complete** stored resource set the service
   exposes is byte-identical, and a subset SHALL NOT be compared.

Together with the addressed cursor having moved by exactly the derived transition,
these make "this grants nothing" a verified property rather than an absence of
evidence: an implementation that quietly placed a row, appended a bought unit, or
derived an amount would fail the proof.

The preserved server charges and credits nothing in either branch, measured across
both executed arms, so any amount would be invention.

#### Scenario: No map row is added

- **WHEN** a reward operation succeeds
- **THEN** the placed-row count is unchanged and every existing row is byte-identical to its state before the request

#### Scenario: No bought-units entry is appended

- **WHEN** a reward operation succeeds
- **THEN** the bought-units list is byte-identical to its state before the request

#### Scenario: No storage entry is created or incremented

- **WHEN** a reward operation succeeds
- **THEN** the store is byte-identical to its state before the request, so neither a new entry nor an incremented quantity is possible

#### Scenario: Every stored resource is unchanged

- **WHEN** a reward operation succeeds
- **THEN** all stored resource slots the service exposes are byte-identical to their values before the request, compared as a complete set rather than a subset

### Requirement: Both client-sent values are recorded as divergences, and neither is reproduced as parity

The operation SHALL NOT reproduce either preserved client-sent value: the granted
item id, and the next cursor id. The operation SHALL derive the successor cursor
from the recorded value.

The operation SHALL record each difference as a **divergence** and SHALL NOT report
it as parity. The next-id difference SHALL be recorded separately from the item
difference, because it is observable in the preserved source rather than only in an
executed record: the preserved branch advances a **client-supplied** cursor and
then, if it exceeds the bound, **overwrites it with the first position**, so a
larger client value would have moved the recorded cursor backwards.

A third divergence SHALL be recorded with them: the preserved weekly branch selects
between granting and not granting on the **client's argument count**, so the same
command with different arities has two different effects. The operation SHALL have
no such arm and SHALL report the boundary and each arm's recorded effect instead.

#### Scenario: The successor cursor is derived, never taken from the client

- **WHEN** a daily reward operation succeeds
- **THEN** the successor cursor is derived from the recorded cursor and the derived bound, and the request's client-supplied next id is refused rather than honoured or ignored

#### Scenario: The two divergences are recorded separately

- **WHEN** the recorded behaviour is compared against the executed preserved-server behaviour
- **THEN** the item divergence, the next-id divergence, and the arm-selection divergence are each recorded separately, and none is reported as matching parity

#### Scenario: The arm boundary is reported, not reproduced

- **WHEN** the weekly operation on `weeklyRewardIndex` succeeds
- **THEN** the response reports which preserved arm the recorded client behaviour would have taken, what each arm's recorded effect is, and that the operation itself has no arm and places nothing

### Requirement: Every refusal resolves before any write, including before the instant stamp, so a refused request leaves the recorded document byte-identical

The operation SHALL complete **all** validation — structural, argument-shape, and
content — **before** any cursor write and **before** any instant stamp, so that a
refused request provably leaves the whole recorded document byte-identical.

The stamp ordering is load-bearing rather than incidental. A refusal that ran far
enough to stamp would leave a **wall-clock** difference in a document that is
supposed to be unchanged, which would either make the byte-identity assertion fail
for the wrong reason or force it to be weakened to accommodate that. The ordering
requirement exists to keep the assertion exact.

The preserved server's ordering cannot be reproduced because it performs no
validation at all; this requirement therefore exists to make the service's refusals
safe rather than to match a recorded ordering.

#### Scenario: A refused request leaves the document byte-identical

- **WHEN** a reward request is refused for any reason
- **THEN** the whole recorded document is byte-identical to its state before the request, including the cursors and every instant

#### Scenario: Validation ordering is asserted structurally

- **WHEN** the delivered implementation is inspected
- **THEN** every validation precedes the cursor write and the instant stamp, and the delivered module's function inventory is pinned whole so a reordering fails the suite

### Requirement: The instant is stamped and no eligibility, window, or cooldown rule is derived from it

The operation SHALL stamp the wall-clock instant the preserved branch stamps, and
SHALL derive **no** rule from it: no eligibility test, no cooldown, no weekly
period, no reset window, and no "already claimed" comparison.

The stamped instant's only other occurrence in the preserved server is **commented
out**, and it has no reader, so there is no rule to reproduce. Its *name* invites
exactly the rule this requirement refuses to write, which is why the absence is
recorded as a requirement rather than left as an implementation detail.

Because the stamp is wall-clock, it is a **volatile field**: a successful execution
cannot be compared by whole-document equality. Refusals still can, because every
refusal resolves before the stamp.

#### Scenario: The instant is stamped

- **WHEN** a reward operation succeeds
- **THEN** the preserved branch's instant field is stamped with the operation's own time, and that instant is reported as a volatile field

#### Scenario: No eligibility rule is derived from the instant

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper that compares the stamped instant against the current time, tests whether a reward is already claimable, or gates an action on an elapsed interval, and this absence is enforced by a guard that fails when such a helper is introduced

### Requirement: The schedule's type letters are reported undecoded, and no letter is mapped onto a resource

The operation SHALL report the schedule's own type letters verbatim and SHALL NOT
map any of them onto a stored resource, an item category, or a grant shape.

Six independent searches across the preserved server's own modules for any
letter-to-resource mapping return zero, so reading a letter as a resource name
would be an **invention** rather than a reproduction. The operation SHALL report
that absence beside the letters rather than presenting them as if decoded.

#### Scenario: The letters are reported undecoded

- **WHEN** the reward schedule is reported
- **THEN** each entry's type letter is reported verbatim together with the recorded result of the decoder searches, and no delivered code maps a letter onto a stored resource slot

#### Scenario: No decoder exists

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper capable of mapping a schedule type letter onto a resource slot, a resource name, or a grant shape, and this absence is enforced by a guard that fails when such a helper is introduced

### Requirement: The unread schedules and the save-only fields are reported with no rule

The operation SHALL report, with no rule derived from any of them:

- the committed reward schedules that **no** preserved-server branch consumes,
  with the measured consumer count beside each;
- the private-state fields that exist in every committed save and in **no** source
  line, with the measured occurrence count and document-presence count beside each;
- the committed ranking-reward table, stating that it is owned **as normalized
  content** and undelivered **as gameplay**, and not collapsing those two states.

The schedule census SHALL be stated as a statement about the **preserved server's
source**, because the whole configuration object is served to clients and a client
could have read any of the schedules; the operation SHALL NOT claim anything about
what any client did.

The origin of the save-only fields SHALL be reported as an **inference** from their
total absence in every source line alongside universal presence in every save, and
not as a measurement.

The document-presence count SHALL be stated with its **denominator**: the
committed corpus is walked as **34** `.json` files across the three corpus
directories, of which **33** carry a `privateState` — the single exclusion being
the corpus manifest, which is a manifest of the corpus rather than a save — and
**all 33** carry every one of the seven fields. A presence figure without its
denominator would leave a reader unable to tell a manifest from a save.

#### Scenario: Unread schedules are reported with their consumer counts

- **WHEN** the reward schedules are reported
- **THEN** each committed reward schedule is listed with its measured consumer count, the ones with no consumer are marked as such, and no rule is derived from any of them

#### Scenario: Save-only fields are reported, and their origin is labelled an inference

- **WHEN** the save-only private-state fields are reported
- **THEN** each is listed with its measured source-occurrence count and document-presence count **stated against its denominator**, and their origin is labelled as an inference from those two measurements rather than stated as a measurement

#### Scenario: The ranking-reward table's split ownership is stated

- **WHEN** the ranking-reward table is reported
- **THEN** it is reported as owned as normalized content and undelivered as gameplay, and the report does not claim that either statement implies the other