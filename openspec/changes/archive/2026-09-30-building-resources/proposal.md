# Proposal

## Why

M7's first nine deliver lines are delivered and archived: placement, purchase,
move, sell, store, upgrade, construction, collect income, and town expansion.
Every one of them moves resources correctly **server-side** — the unchanged legacy
`apply_resources` applies the client-sent 8-slot vector verbatim per resource as
`max(current + delta, 0)` (`engine.py:251-271`), the collect line derives its payout
from committed content, and the expand line derives its debit, refuses an uncovered
balance, and proves the resulting balances by value.

The tenth deliver line, **resources**, is about the other half of that sentence: the
player must be able to **see** the resources. And they cannot, because of two
defects in the client's projection of a model that is otherwise entirely established.

The contract was established by investigation and is committed as
`docs/legacy-resources.md` (PR #193). The seven server resources and where each one
lives in the save are established by `engine.apply_resources` and confirmed by the
corpus (`xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`, `cash 5`,
`mana 0`), and the Compatibility API's `resources` accessor already returns exactly
those seven keys. **The model is not the problem.** The problem is that the HUD's
display table asks for two fields nothing produces.

## What Changes

- **The HUD's primary currency row becomes readable.** `scripts/town/town_hud.gd`
  keys its first resource row `coins`. There is no `coins` resource: the server's
  field is `gold`, `maps[0]` has `gold` and no `coins`, and the only two occurrences
  of the word in the Compatibility API are *comments about the expansion price
  schedule*. Because the HUD is fail-closed by design and renders an explicit
  `[missing: <field>]` indicator for an absent field, **the player's primary currency
  is displayed as missing and its real value never appears on screen.** This change
  keys that row `gold`.
- **A single-source resource projection.** A canonical projection in the client
  naming each resource by the name the server actually uses, with `xp` kept distinct
  from the six spendable resources because it is the experience counter and not a
  currency, and with every row traceable to exactly one save location. No duplicate
  rows and no invented resources.
- **`energy` exposed under its own name, with its regeneration rule recorded as a
  gap.** `energy` is a real eighth resource in the save — `privateState.energy = 50`
  in the corpus, `COST_ENERGY = "e"` at `constants.py:899`, plus `TOKEN_ENERGY = 7`
  and `CAT_ENERGY = 8` — but `apply_resources` never writes it, the 8-slot vector has
  no slot for it, and no delivered accessor exposes it, so its HUD row is missing
  today while the resource is genuinely part of the economy (`items[].costs` may name
  it). The change exposes the stored value verbatim and records the absence of any
  regeneration rule as a named gap.
- **Corrected tests.** The existing HUD suite **pins the defect** by supplying
  `"coins": "2000"` and `"energy": "50"` in a crafted payload shape nothing real
  produces. It is corrected to the real field names, and new assertions pin that
  `gold` renders its real value, that no row is keyed `coins`, that `energy` renders
  its stored value, and that a genuinely absent resource still renders the explicit
  missing-field indicator.
- **Evidence and documentation** — a windowed capture plus a deterministic
  `resources-report-v1` report under `apps/client-godot/evidence/building-resources/`,
  an expanded hermetic resource-projection suite, and `AGENTS.md` / README updates
  recording the commands, the provenance, and the claim limits.

### Explicitly not in this change

**No state-mutating surface changes.** None of the nine delivered endpoints gains,
loses, or renames a field, no new endpoint is added, and no balance changes — the
defect is entirely in how the client names what the server already sends. The
`resources` accessor that all nine post-execution proofs share is **not** widened with
`energy`, because that would change nine response shapes and their committed parity
fixtures for no behavioural gain; the energy value travels on its own additive path
instead. Also out of scope: the market and trade counters (`trade_resource`,
`set_resource_allies`, whose arguments the catalog records as *read but unused*, so
their resource movement is client-sent), item-cost mapping onto the resource
vocabulary, energy regeneration, server-authoritative resource validation (Server v1 /
M13), and any change to the nine delivered lines' behaviour. Legacy sources, configs,
saves, villages, committed fixtures, conversion packages, registry manifests, and
every delivered slice's evidence stay byte-identical (existing SHA-256 guards plus the
hash manifest). No Flash, Ruffle, ActionScript, or browser executes, and no external
network is used.

## Capabilities

### New Capabilities

- `godot-building-resources`: the player's resource model as the client projects it —
  a single canonical projection naming every resource by the name the server uses, a
  HUD in which all seven (later eight) resource rows are readable with **no phantom
  or duplicate rows**, `gold` displayed by value for the first time, `energy` exposed
  under its own name with its regeneration rule recorded as an explicit gap, and the
  evidence, containment, provenance, and claim limits that bound the projection claim
  — all delivered **without changing any state-mutating surface**.

### Modified Capabilities

- `godot-compatibility-boot`: the `GameApi` abstraction requirement records the
  canonical resource projection the client depends on — every resource named as the
  server names it, `gold` never `coins` — with a "Project every resource under its
  server name" scenario; and the bootstrap-service requirement notes that the
  read-only energy value travels on its own additive path rather than by widening the
  `resources` accessor the nine gameplay endpoints share.

## Impact

- **Godot client** — `scripts/town/town_hud.gd` (the corrected display table), a new
  `scripts/town/resource_projection.gd` for the single-source projection, and the
  expanded `tests/test_town_hud.gd` plus a new `tests/test_town_resources.gd`; the
  scope-test allow-list and the new evidence files.
- **Compatibility API v0** — one additive read-only accessor for the stored energy
  value in `compat_legacy.py` and its exposure on the bootstrap path, plus compat
  tests. **No change to any of the nine state-mutating routes, their responses, or
  their error tables.**
- **Legacy** — unchanged and read only: `command.py`, `engine.py`, `constants.py`,
  `sessions.py`, `config/`, `villages/`, `tests/saves/`, and every committed fixture.
- **Verification** — `verify-boot.ps1` gains the hermetic resource-projection suite;
  the guard baseline, the hash manifest, and both batteries must stay green with no
  new packages and no non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, and the updated `docs/legacy-resources.md`.