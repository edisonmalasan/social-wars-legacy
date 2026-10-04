# Proposal

## Why

`end_attack` is the preserved server's only combat-resolution branch, and it is
undelivered. Measured against the executed legacy `do_command`, a single
`end_attack` request with one `attacker_units` tuple destroys **two** of the
player's own committed unit rows and increments the dead-hero ledger by two — and
the item id, the destruction count, and the subtraction that produces it are all
**client-supplied**, with nothing in the server validating any of them. The bound
on destruction is not a check but the exhaustion of matching rows.

Delivering it forces a correction the milestone could not defer. M8's
`godot-unit-behaviors` recorded, as the reason no executed-legacy fixture could be
captured, that "the committed corpus places only buildings and no unit row, and
its ledger is present and `{}`". Measured across all eleven committed save
documents, that is **false of the repository** and true of
`tests/saves/fresh-player.json` alone: **441** committed unit rows across **7 of
11** documents, all team 1, **429** of them satisfying the `resurrectable` gate,
and **five** village saves carrying a **non-empty** ledger. `resurrect_hero`
executed against `Neutral.json`'s committed 28-key ledger decrements one key and
re-places a row — so the behaviour that capability said was unexercisable
exercises cleanly, and the false premise sits in a merged requirement's SHALL text.

## What Changes

- **New endpoint for combat resolution.** A compatibility-service operation that
  accepts a combat-resolution intent and derives the affected unit identity and
  the destruction set **server-side**, refusing any client-dictated destruction
  count. This follows the M9 `quests` precedent for `end_quest`, where the
  client-dictated `lost` was refused and the resulting difference from the legacy
  server is recorded as a **divergence**, not as parity.
- **Validation strictly before any destruction.** The legacy branch's two
  unguarded `None` dereferences sit on opposite sides of the write loop: omitting
  `attacker_units` raises **before** the save is touched, while omitting `victim`
  raises **after** the rows are already gone. Any endpoint that validates after
  the write reproduces a partially-applied save on a refusal path, so the ordering
  is a requirement, not an implementation detail.
- **The request shape's discarded fields are reported structurally.** `end_attack`
  reads **eleven** keys from its client blob and **seven** reach nothing at all
  (`victim_units`, `resources_victim`, `attacker`, `resources`, `honor`,
  `duration`, `townhall_gold`, `different_island`), with `win` and
  `victim["name"]` reaching only a `print`. The non-claims become a mechanical
  guard rather than prose.
- **`kill` delivered as row deletion that never touches the ledger**, and
  **`kill_iid` delivered as a proven no-op** — the branch has no write statement
  at all, which is stronger than any single observed request.
- **Corrections to a merged spec.** `godot-unit-behaviors` claims no fixture on a
  premise this milestone disproved, and describes `map_lose_item`'s fourth ledger
  door as reached from the quest path without naming its second caller, which this
  change delivers. Both requirements are modified; the capability's own
  "no combat is resolved" requirement is **not** modified, because this change
  resolves no combat — the legacy server resolves none either.
- **Referenced, not re-delivered:** the dead-hero ledger projection and its gates
  and the `resurrect_hero` revival (`godot-unit-behaviors`); `sell` and its
  derived reason (`godot-building-sell`); the 64 `MISSION_*` declarations
  (`godot-mission-vocabulary`), of which this surface names
  `MISSION_ATTACK_PLAYER`, `MISSION_ASSAULTS_WON`, `MISSION_KILLED_ENEMY`,
  `MISSION_DEFEAT_ALL_TROLLS` and `MISSION_SACRIFICE_UNIT` and dispatches none.
- **Four prose locations corrected** in `AGENTS.md` and
  `apps/client-godot/README.md`, each of which repeated the fresh-player figures
  as though they described the repository. Three further occurrences were checked
  and are correctly scoped to that corpus; they are left alone.
- **A second discrepancy recorded, not corrected.** Four of five combat-field
  figures in the M8 record (`attack` 131, `defense` 1, `life` 150,
  `min_level` 21, `syringes` 6) reproduce under **no** counting rule measured
  here, which finds exactly zero for all four. M8's *direction* holds and this
  measurement strengthens it; the *figures* do not reproduce. The record is
  annotated rather than rewritten, and resolving the discrepancy is left to the
  line that owns those fields.

## Capabilities

### New Capabilities
- `godot-combat-actions`: the combat-action surface of the preserved server —
  `end_attack`'s request shape and the server-derived destruction set, the
  validation-before-destruction ordering, the structurally guarded set of
  read-and-discarded client fields, `kill`'s ledger-free deletion, and
  `kill_iid`'s proven emptiness — with an executed-legacy fixture and the
  recorded divergence from the legacy server's client-dictated destruction.

### Modified Capabilities
- `godot-unit-behaviors`: **"No executed-legacy behaviour fixture is claimed"** is
  false in its premise — the corpus places 441 committed unit rows and five
  committed ledgers are non-empty, so the requirement is corrected to state the
  real cause and to record that the corpus measurement supersedes the
  fresh-player-only reading.
- `godot-unit-behaviors`: **"The three-door command inventory records which
  command reaches the ledger"** names `map_lose_item`'s quest-path reach without
  naming its second caller, which this change delivers as the combat-resolution
  path; the requirement is extended so a reader consulting that capability alone
  cannot conclude the ledger is unreachable from attacks.

## Impact

- **Compatibility service** — a new state-mutating endpoint in
  `apps/compat-api/`, its request envelope, and the executed-legacy fixture
  capture script. This is the first state-mutating endpoint since M9's
  `unit-experience` line, so the compat suite grows.
- **Modern client** — a new typed read-only projection under
  `apps/client-godot/scripts/`, a generated content or evidence table, a hermetic
  suite, and a deterministic report under
  `apps/client-godot/evidence/`. Nothing is rendered, so no windowed capture and
  no pixel-parity oracle are claimed.
- **Legacy source** — read only. No file under the preserved server, the committed
  saves, the config, the villages, or the content package is modified; the
  preservation manifest must stay byte-identical at 3,258 entries.
- **Specs** — one new capability and one existing capability with two modified
  requirements. No existing requirement is removed or renamed.
- **Not in scope:** damage, health, hit chance, defence application, or any combat
  arithmetic; mission completion and the 64 mission types; rewards and honour;
  server-authoritative occupancy, bounds, terrain, or type validation, which
  remain Server v1 / M13 gaps. No client-dictated destruction count is
  reproduced in either direction.