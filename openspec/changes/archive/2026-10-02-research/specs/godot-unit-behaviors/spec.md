# Spec Delta

## MODIFIED Requirements

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
