# Spec Delta

## MODIFIED Requirements

### Requirement: No executed-legacy behaviour fixture is claimed

The change SHALL capture **no** executed-legacy behaviour fixture **of its own**,
and the non-claims SHALL state the cause accurately. The cause is **NOT** that the
corpus cannot exercise the behaviour: the recorded cause is that this capability
delivered the revival as a **server-derived intent** and no fixture was in scope
for it. The requirement SHALL **supersede** its earlier premise that "the
committed corpus places **only buildings** and **no unit row**, and its ledger is
present and empty, so no resurrectable row exists to exercise" — that premise was
**false of the repository** and true of the fresh-player corpus alone. Measured
across every committed save document, the repository holds **441** committed unit
rows across **7** of **11** documents, **all** on player team one, **429** of them
satisfying the `resurrectable` gate, and **five** committed village documents
carry a **non-empty** ledger. The capability SHALL record that measurement, SHALL
point to `godot-combat-actions` for the executed capture against a committed
village document, and SHALL **retain** the non-claim that no unit row was
manufactured to make a fixture capturable, which remains **true** and is now
stated independently of the corpus's contents. The committed corpus and the
delivered fixture directories SHALL remain byte-identical.

#### Scenario: No fixture is captured, and the specific cause is stated

- **WHEN** this capability's evidence and claim limits are read
- **THEN** they state that this capability captured no fixture of its own because the revival was delivered as a server-derived intent and no fixture was in scope, and they do **not** attribute the absence to the corpus being unable to exercise the behaviour

#### Scenario: The superseded premise is corrected, not deleted

- **WHEN** a reader compares this requirement against the superseded wording
- **THEN** the earlier claim that the corpus places only buildings and no unit row, with an empty ledger, is identified as **false of the repository** and true of the fresh-player corpus alone, and the correction is recorded rather than applied silently

#### Scenario: The repository-wide measurement is recorded

- **WHEN** the claim limits are read
- **THEN** they state the number of committed unit rows across the committed save documents, that they are all on player team one, how many satisfy the `resurrectable` gate, and how many committed documents carry a non-empty ledger, each measured rather than asserted

#### Scenario: The executed capture is pointed to, not restated

- **WHEN** a reader consults this capability alone
- **THEN** they are **pointed to `godot-combat-actions`** for the executed capture against a committed village document, so they cannot conclude from this capability that the behaviour is unexercisable

#### Scenario: No coverage is manufactured

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a unit row, and the committed corpus and the delivered fixture directories stay byte-identical

### Requirement: The three-door command inventory records which command reaches the ledger

The client SHALL record the inventory of the commands that reach or bypass the dead-hero ledger,
naming `kill`, `sell`, and `resurrect_hero`, and for each SHALL record whether it reaches the
ledger and what else it mutates. It SHALL record the ledger's door count as **four**, and it SHALL
say so in the body: the requirement heading's own "three-door" wording is a **superseded label**,
retained only because a MODIFIED delta resolves its header against the existing requirement name and
Archive **refuses a renamed heading**, so the heading MUST NOT be corrected. The fourth door is the
`map_lose_item` **engine helper** (`engine.py:215-228`), which calls `push_dead_unit`, so a unit lost
in a quest or lost in combat is pushed onto the ledger through the same helper. `map_lose_item` is
**not** a dispatcher branch, so the named-branch count and the door count stay distinguishable, and
this door is reached from **two** caller branches — the **quest** path and the **combat-resolution**
path — and from **neither** death path. Both callers SHALL be named here so a reader consulting this
capability alone cannot conclude the ledger is unreachable from attacks any more than from quests:
the `godot-quests` capability delivers the quest-path caller and `godot-combat-actions` delivers the
combat-resolution caller, and each is named so the ledger owner and the two callers' owners cannot
describe the same reach differently. The recorded facts SHALL include that **`map_lose_item` reaches the ledger through `push_dead_unit`**
and is counted as a door, that **`kill` deletes the row and never
touches the ledger**, that **`sell` reaches the ledger only when its reason is the combat reason and
through the `push_dead_unit` engine helper**, that `push_dead_unit` is an **engine helper rather than a
dispatcher branch**, that the ledger guard in that branch compares a **string literal** while the
corresponding constant is **never read** by the dispatcher, and that **`resurrect_hero` decrements the ledger and re-places the row at
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
  helper calls `push_dead_unit` so a unit lost in a quest or in combat reaches the ledger — the correction this
  requirement previously stated as three, which the M9 investigation disproved

#### Scenario: The quest path is distinguished from the death path
- **WHEN** this requirement records where the fourth door is reached from
- **THEN** it records that the door is reached from **two** caller branches — the **quest** path and the
  **combat-resolution** path, each through `map_lose_item` — and from neither death path, so a reader
  consulting this capability alone cannot conclude the ledger is unreachable from quests **or** from attacks

#### Scenario: The helper and the branch counts stay distinguishable
- **WHEN** the inventory reports its counts
- **THEN** it keeps the named **dispatcher branch** count separate from the **door** count, because
  `map_lose_item` is an engine helper and not a branch

#### Scenario: The superseded heading label is not corrected
- **WHEN** this requirement's heading is read
- **THEN** it still reads "three-door" while its body records four, and the body states that the label is
  superseded and that the heading MUST NOT be renamed, because a MODIFIED delta resolves its header
  against the existing requirement name and Archive refuses a renamed heading

#### Scenario: The quest path's caller is named by both capabilities
- **WHEN** this requirement records where the fourth door is reached from
- **THEN** it records that the quest path is reached through `map_lose_item`, and names `godot-quests`
  as the capability that delivers that caller, so the ledger owner and the quest owner cannot describe
  the same reach differently

#### Scenario: The combat path's caller is named by both capabilities
- **WHEN** this requirement records where the fourth door is reached from
- **THEN** it records that the combat-resolution path is reached through the same `map_lose_item` helper, and
  names `godot-combat-actions` as the capability that delivers that caller, so a reader cannot conclude the
  ledger is unreachable from combat and the two owners cannot describe the same reach differently

#### Scenario: The ledger guard's literal is recorded
- **WHEN** the inventory describes the guard that gates the ledger increment on the selling path
- **THEN** it records that the branch compares a string literal, and that the corresponding declared constant
  has no reader in the dispatcher, so the constant's existence is not mistaken for the guard being derived
  from committed content