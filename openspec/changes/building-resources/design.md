# Design

## Context

See `proposal.md` — Why, and the committed investigation record
`docs/legacy-resources.md`. Unlike every preceding line in this family, **nothing
here has to be derived**: the legacy mechanics are already established by committed
source, and the defect is entirely inside the modern client. That makes this the
first line whose design is mostly *correction* rather than derivation, and it is why
the proposal carries no derivation table — there is almost nothing unobserved to mark.

### Established, and already delivered

- The seven stored resource slots and their save locations are established by
  `engine.apply_resources` (`engine.py:251-271`):

  | Vector slot | Resource | Stored at |
  | --- | --- | --- |
  | 1 | `xp` | `maps[0].xp` |
  | 2 | `gold` | `maps[0].gold` |
  | 3 | `wood` | `maps[0].wood` |
  | 4 | `oil` | `maps[0].oil` |
  | 5 | `steel` | `maps[0].steel` |
  | 6 | `cash` | `playerInfo.cash` |
  | 7 | `mana` | `privateState.mana` |

  Slot 0 is the vector's unread `unknown`; the legacy comment at `engine.py:252`
  names it as the cheat-detection slot, and it has no stored value.
- The committed corpus agrees exactly: `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`,
  `steel 2000`, `cash 5`, `mana 0`.
- `compat_legacy.py`'s `resources()` returns exactly those seven keys from exactly
  those locations, and all nine delivered endpoints' post-execution proofs compare
  that dict.
- The client's typed `Resources` class (`boot_data.gd:198-206`) already declares the
  seven correct names — `xp, gold, wood, oil, steel, cash, mana`.

### The two defects

- **`scripts/town/town_hud.gd`'s display table** (`FIELDS`, lines 27-38) has ten rows
  and keys its first resource row `coins` and a sixth resource row `energy`. Its own
  header comment names the intended set: "the seven resources (coins, wood, steel,
  oil, cash, energy, mana)".
- **Neither `coins` nor `energy` is produced by anything.** `coins` has no server
  field (`maps[0]` has `gold`; the word appears in `compat_legacy.py` only in
  comments about the expansion price schedule at lines 453 and 456). `energy` is real
  but unexposed (`privateState.energy = 50`; `COST_ENERGY = "e"` at
  `constants.py:899`; `TOKEN_ENERGY = 7`; `CAT_ENERGY = 8`) and `apply_resources`
  never writes it.
- Because the HUD is fail-closed and renders an explicit `[missing: <field>]`
  indicator, both rows render as missing today. **The primary currency is invisible.**
- The existing `tests/test_town_hud.gd` supplies `"coins": "2000"` and
  `"energy": "50"` in its crafted payload (lines 29-30) and asserts
  `Energy: 50` renders — so the suite passes against a payload shape nothing real
  produces, and **pins the defect instead of catching it**.

### A reading that makes the fix obviously minimal

The header comment's intended set — "coins, wood, steel, oil, cash, energy, mana" —
is **exactly** the ten-row table's shape: seven resource rows plus three summary rows
(`name`, `level`, `xp`). So the table is not mis-shaped and needs no new row, no
removal, and no reordering; **one key is misnamed**. Renaming `coins` → `gold` makes
every row sourced, and sourcing `energy` makes all ten readable. That is the whole
change to the HUD.

## Decisions

**D1 — every resource is named exactly as the server names it (established; this is
the correction).** The projection's canonical name for the primary currency is
`gold`, never `coins`, because `gold` is what `apply_resources` writes, what the
corpus stores, and what the compat accessor returns. Evidence is committed source,
not inference. The claim boundary is explicit: the projection claims to display what
the save stores, and a field the server never produces is never displayed under an
invented name.

**D2 — `xp` is a counter, not a currency, and stays in the summary group
(established).** `maps[0].xp` is the vector's slot 1 and the value the `levels`
schedule consumes; nothing spends it. Grouping it with `name` and `level` in the
summary rather than with the six spendable resources is what the delivered table
already does, so this decision preserves existing behaviour rather than changing it
— recorded because a reader might otherwise "fix" it into the resource group.

**D3 — `energy` is exposed under its own name, and its regeneration rule is a
recorded gap (established resource, gap in the rule).** The stored value is surfaced
verbatim. No rule is invented for how it changes: `apply_resources` never writes it,
no legacy branch touches it, and no committed source records a regeneration
interval. Whether the legacy client regenerates it on a timer or some unrecorded path
did is **not decided by the repository**, and this change does not decide it either —
it displays the stored value and records the absence. `energy` is also not added to
the 8-slot mutation vector, because the vector is the legacy wire format and
`apply_resources` has exactly eight slots.

**D4 — no Compatibility API change at all, and the shared `resources` accessor is NOT widened (established; corrected during Apply).** This decision originally read that the stored energy value had to reach the client on a new additive read-only path, because `resources()` is the `apply_resources` contract all nine state-mutating endpoints' value-level proofs compare and its shape is baked into nine committed executed-legacy parity fixtures — widening it would re-baseline nine proven fixtures for no gain. **Apply established that the premise was false**: the client's town state already maps `energy` to `privateState.energy` (`TownState.RESOURCE_FIELDS`), the stored value is already inside the payload the client receives, and the captured readout renders `Energy: 50`. So the energy row is *sourced*, not fail-closed, and **the endpoint needs no accessor, no field, and no route change** — the whole change is client-side. The narrowing reasoning still holds and is recorded as the reason the shared accessor is untouched: it remains the `apply_resources` contract, and nothing in this change widens it.

**D5 — a single-source projection, and no duplicate or invented rows.** One module
owns the mapping from save location to display label for every row, so no row can
claim a field nothing provides. A row whose field is genuinely absent still renders
the explicit missing-field indicator — the fail-closed behaviour the delivered HUD
already has is preserved and is now *meaningful*, because absence means absence
rather than a misnamed key.

**D6 — validation and authority are unchanged.** This change introduces no
state-mutating action, so there is nothing to authorise: it is a read-only projection
over data the service already returns. No server-authoritative resource validation is
added or implied (Server v1 / M13), and no balance moves.

**D7 — evidence, claim limits, and containment.** A windowed capture of the HUD with
every row sourced, plus a headless deterministic `resources-report-v1` report
recording the canonical projection table (row, canonical name, save location,
group), the stored values observed, the `energy` gap and its evidence, the
established-versus-derived split, and the non-claims — byte-identical across reruns.
Containment carries forward unchanged: no new packages, loopback only, both batteries
plus the guard baseline and the 3,258-entry hash manifest green in the final state,
and the orchestrator-run integration review as the fallback for the unavailable
dedicated verification workflow.

## Risks / Trade-offs

- **Widening the shared `resources` accessor would have been simpler** and is
  rejected in D4 with a reason: it re-baselines nine proven value-level proofs for no
  gain. The cost of the additive path is one extra read-only field on the
  player-overview response and the corresponding evidence regeneration.
- **`energy` displayed with no regeneration rule could mislead** → mitigated by D3:
  the value is displayed verbatim and the missing rule is recorded in the report's
  non-claims, so nothing is implied about how it changes over time.
- **Correcting the HUD suite removes assertions that currently pass** → that is the
  point; the replacement assertions are stronger, because they run against the field
  names the real bootstrap produces rather than a fabricated payload. The review
  record must show exactly which assertions were replaced and why.
- **A projection fix could regress a delivered line's display** → all nine delivered
  suites must stay green unchanged, and the resource rows they read (`gold`, `cash`,
  `xp`, `mana`) keep their values, so a regression would surface in an existing suite
  rather than hiding behind the new one.

### Correction made during the Apply stage

**The design's premise about energy needing a service accessor was wrong, and the change was
narrowed rather than implemented as designed.** The design assumed the stored energy value had
to be added to the service because `engine.apply_resources` never writes it. Apply established
that it does not have to be added: the client's `TownState.RESOURCE_FIELDS` already maps
`energy` to `privateState.energy`, the committed fresh-save payload already carries the value,
and the windowed capture renders `Energy: 50`. So:

- **the Compatibility API is not modified at all** — no accessor, no bootstrap field, no route,
  no response shape, and no error-table row;
- the spec's service-side requirement to *expose* the energy value is replaced by a requirement
  to **display the value the payload already carries** and to record that no delivered path
  changes it;
- the `godot-compatibility-boot` delta keeps only the `GameApi` projection requirement; the
  bootstrap-service modification describing an additive energy path is **removed**, because no
  such path exists or is needed;
- and D4's narrowing reasoning is retained as the documented reason the shared `resources`
  accessor stays untouched.

This is the narrowest possible change to the defect, and it keeps the promise that no
state-mutating surface — nor the read-only ones — is disturbed.
