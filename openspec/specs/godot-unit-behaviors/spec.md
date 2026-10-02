# godot-unit-behaviors

## Purpose

Deliver the M8 `basic behaviors` line: the resurrectable-unit counter as a
typed, server-authoritative projection, the three-door command inventory, the
ignored `used_syringe`, the refusal of any syringe cost, and the explicit
absence of combat.

## Requirements

### Requirement: The dead-hero ledger is projected, and the gates are named

The client SHALL expose a player's dead-hero ledger as a typed, read-only projection carrying each
recorded item id and its recorded count, the increment and decrement shapes, and the **delete-at-zero**
rule, each reported **verbatim**. The projection SHALL name both gates exactly as the legacy helper
does: the row must be on **player team 1** and its committed `properties` must carry
**`resurrectable > 0`**. The projection SHALL compute **no** count from another: no threshold, no cap,
no clamping, and no count derived from a committed `syringes` value. A ledger that is absent or is
not a string-keyed object SHALL be reported as unresolvable with its recorded state intact, never
defaulted to an empty ledger presented as a resolved one.

#### Scenario: Counts are reported verbatim

- **WHEN** a player's dead-hero ledger is projected
- **THEN** each recorded item id and its recorded count are reported exactly as recorded, with no threshold, cap, or clamp applied

#### Scenario: Both gates are named

- **WHEN** the projection reports what may enter the ledger
- **THEN** it names exactly the two legacy gates — the row being on player team 1, and the committed `resurrectable` value being greater than zero — and derives no further eligibility

#### Scenario: The delete-at-zero rule is reported

- **WHEN** a decrement is reported
- **THEN** the projection states that reaching zero **deletes** the key rather than storing a zero, matching the legacy helper

#### Scenario: An unresolvable ledger is reported, not defaulted

- **WHEN** a player's `deadHeroes` is absent or is not a string-keyed object
- **THEN** the projection reports it as unresolvable with its recorded state intact, and never presents an empty ledger as a resolved one
### Requirement: The three-door command inventory records which command reaches the ledger

The client SHALL record the inventory of the commands that reach or bypass the dead-hero ledger,
naming `kill`, `sell`, and `resurrect_hero`, and for each SHALL record whether it reaches the
ledger and what else it mutates. It SHALL record the ledger's door count as **four**, and it SHALL
say so in the body: the requirement heading's own "three-door" wording is a **superseded label**,
retained only because a MODIFIED delta resolves its header against the existing requirement name and
Archive **refuses a renamed heading**, so the heading MUST NOT be corrected. The fourth door is the
`map_lose_item` **engine helper** (`engine.py:215-228`), which calls `push_dead_unit`, so a unit lost
in a quest is pushed onto the ledger through the same helper. `map_lose_item` is **not** a dispatcher
branch, so the named-branch count and the door count stay distinguishable, and this door is reached
from the **quest** path rather than the death path. The recorded facts SHALL include that **`map_lose_item` reaches the ledger through `push_dead_unit`**
and is counted as a door, that **`kill` deletes the row and never
touches the ledger**, that **`sell` reaches the ledger only when its reason is the combat reason and
through the `push_dead_unit` engine helper**, that `push_dead_unit` is an **engine helper rather than a
dispatcher branch**, and that **`resurrect_hero` decrements the ledger and re-places the row at
client-supplied coordinates**.

#### Scenario: Each command is classified by whether it reaches the ledger

- **WHEN** the inventory is inspected
- **THEN** each recorded command carries an explicit statement of whether it reaches the ledger and what else it mutates, and the count of ledger-reaching commands matches the committed source

#### Scenario: The combat-reason guard is recorded as the only death door

- **WHEN** the inventory describes `sell`
- **THEN** it records that the ledger is incremented only behind the combat-reason guard, that the guard is why the delivered client never reaches the death path, and that the delivered client's derived sell reason therefore closes that door in practice

#### Scenario: The engine helper is distinguished from a branch

- **WHEN** the inventory describes the increment helper
- **THEN** it records that the helper is an engine helper and not a dispatcher branch, so the ledger-reaching command count and the named-branch count stay distinguishable

#### Scenario: The door count is four, and the fourth door is named
- **WHEN** the inventory states how many doors reach the ledger
- **THEN** it states **four** and names the `map_lose_item` engine helper as the fourth, recording that the
  helper calls `push_dead_unit` so a unit lost in a quest reaches the ledger — the correction this
  requirement previously stated as three, which the M9 investigation disproved

#### Scenario: The quest path is distinguished from the death path
- **WHEN** the inventory records where the fourth door is reached
- **THEN** it records that the door is reached from the **quest** path through `map_lose_item`, not from the
  death path, so a reader consulting this capability alone cannot conclude the ledger is unreachable from
  quests

#### Scenario: The helper and the branch counts stay distinguishable
- **WHEN** the inventory reports its counts
- **THEN** it keeps the named **dispatcher branch** count separate from the **door** count, because
  `map_lose_item` is an engine helper and not a branch

#### Scenario: The superseded heading label is not corrected
- **WHEN** this requirement's heading is read
- **THEN** it still reads "three-door" while its body records four, and the body states that the label is
  superseded and that the heading MUST NOT be renamed, because a MODIFIED delta resolves its header
  against the existing requirement name and Archive refuses a renamed heading
### Requirement: A revival is a server-derived intent, and the client-supplied syringe is ignored

The compatibility service SHALL expose a revival operation accepting **only** a player identifier and
a cell. It SHALL derive the revived **item id** and the **map key** from the server's own ledger and
from the addressed cell, SHALL ignore any client-supplied syringe count, and SHALL apply the
legacy increment/decrement rules and the **delete-at-zero** rule. It SHALL refuse a cell that no
recorded ledger entry resolves to, and SHALL refuse when the resolved entry's committed
`resurrectable` value is not greater than zero. A successful revival SHALL return the typed response
carrying the server-derived item id, the map key, and the resulting ledger state, and SHALL NOT echo
any client-supplied value it ignored.

#### Scenario: The client sends intent only

- **WHEN** a revival is requested
- **THEN** the request carries only a player identifier and a cell, and the server derives the item id, the map key, and the resulting ledger state rather than accepting them

#### Scenario: A client-supplied syringe count is ignored

- **WHEN** a revival request carries a syringe count
- **THEN** the count is ignored, the response reports no consumed syringe, and the recorded state shows the client's value had no effect

#### Scenario: An unresolvable or ineligible revival is refused

- **WHEN** the addressed cell resolves to no recorded ledger entry, or the resolved entry's committed `resurrectable` value is not greater than zero
- **THEN** the operation is refused with a named code, an empty payload, and no ledger change
### Requirement: No syringe cost, and the committed syringes field is content only

The client and the compatibility service SHALL charge **no** syringe cost and SHALL move **no** stored
resource, because the committed `syringes` field has **zero** legacy consumers. The service SHALL
report the committed `syringes` value as **content only**, and SHALL prove the no-cost claim by a
post-execution check that **every stored resource is unchanged**. No resource delta, no currency
conversion, and no cost derivation from any committed field SHALL be implemented.

#### Scenario: No resource moves on a revival

- **WHEN** a revival succeeds
- **THEN** every stored resource is unchanged, and the post-execution proof compares the full resource set rather than a selected subset

#### Scenario: The committed field is reported, never used

- **WHEN** a resolved unit's committed `syringes` value is inspected
- **THEN** it may be reported as content with its zero-consumer status, and no cost, price, or charge is computed from it
### Requirement: No combat is resolved, and no placement validation is invented

The client SHALL derive **no** combat resolution of any kind: no damage, no attack outcome, no
defence application, no hit chance, and no life or interval arithmetic, because the committed `attack`,
`defense`, `life`, `attack_interval`, `attack_range`, `best_against`, and `best_against_mult` fields
each have **zero** legacy consumers and are therefore content rather than rules. The client SHALL
**not** add occupancy, bounds, type, or terrain validation to the revived placement, reproducing the
legacy branch's absence of any such check and recording it as a server-authority gap rather than
filling it.

#### Scenario: No combat rule is derived

- **WHEN** the committed combat fields are inspected
- **THEN** their values may be reported as content with their zero-consumer status, and no damage, outcome, defence, hit, or life computation is derived from any of them

#### Scenario: The revived placement is not validated

- **WHEN** a revival re-places the row
- **THEN** no occupancy, bounds, type, or terrain check is applied, and the recorded absence is stated rather than filled with an invented rule
### Requirement: No executed-legacy behaviour fixture is claimed

The change SHALL capture **no** executed-legacy behaviour fixture, and the non-claims SHALL state the
specific cause: the committed `resurrectable` flag is **unit-only**, the committed corpus places
**only buildings** and **no unit row**, and its ledger is present and empty, so no resurrectable row
exists to exercise. The non-claims SHALL distinguish this from the refusal lines' reason, which was
the **absence of behaviour**, and SHALL record that no unit row SHALL be manufactured to make one
capturable. The committed corpus and the delivered fixture directories SHALL remain byte-identical.

#### Scenario: No fixture is captured, and the specific cause is stated

- **WHEN** this capability's evidence and claim limits are read
- **THEN** they state that no fixture was captured because the corpus holds no resurrectable row, distinguish that from the refusal lines' absence of behaviour, and note that no unit row was manufactured

#### Scenario: No coverage is manufactured

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a unit row, and the committed corpus and the delivered fixture directories stay byte-identical
### Requirement: Unit-behaviour evidence and claim limits

The change SHALL commit a deterministic `unit-behaviors-report-v1` report recording the ledger
projection, the three-door command inventory with each command's ledger effect, both gates, the
delete-at-zero rule, the ignored `used_syringe`, the zero-consumer behavioural fields with their
committed distributions, the corpus measurement, the established-versus-derived split, and the
explicit non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash, Ruffle,
ActionScript, or browser executed; **no syringe cost is charged and no stored resource moves**;
**no combat is resolved** and the committed combat fields are content with zero consumers; **no
occupancy, bounds, type, or terrain validation is added** to the revived placement; **the death and
resurrection pairing is derived**, not asserted by the source; **`clicks_to_build` is referenced and
not reimplemented**, its consumer being the construction-click counter owned elsewhere; **no
executed-legacy fixture was captured**; **no unit is revived against the committed corpus**; **no
pixel parity is claimed**; and **no windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-behaviors/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: Combat, parity, and pairing are not claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no combat is resolved, that the death/resurrection pairing is derived, that no pixel parity or windowed capture is claimed, and that no syringe cost is charged
