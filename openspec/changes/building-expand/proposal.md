# Proposal

## Why

M7's first eight deliver lines are delivered and archived: placement, purchase,
move, sell, store, upgrade, construction, and collect income. A player can now
build, upgrade, watch a build finish, and collect a building's income — and can
never grow the town. The `expand` command has no delivered surface, and the one
thing the game asks a player to do after building is to unlock more land.

The contract was established by investigation and is committed as
`docs/legacy-town-expansion.md` (PR #188), with two further probes and a
committed-asset-evidence pass during this proposal. The branch is one line of
state change (`command.py:211-216`): `map["expansions"] += [int(expansion)]`. The
price is **entirely client-sent**, and the investigation's probe showed the
per-resource clamp is reachable for the first time in this family — a client-sent
`-2500` gold debit against a `2000` balance landed on `0`, not `-500`. That is
direct evidence that a client-sent price is a client-trusted mint or burn, and it
is the reason this line's endpoint derives the debit from committed content and
proves the resulting balances by value.

Two of the investigation's four open questions turned out to be answerable from
evidence already committed, without any further execution:

- **the `coins` field is the client's `gold`** — the asset registry carries
  `assets/images/en/expansion_gold.jpg` *and* `assets/images/en/expansion_cash.jpg`,
  two distinct committed images, which are the expansion popup's two price
  components; the server's slot 2 is `gold`;
- **an expansion is a purchasable *tile*** — the committed SWF symbols name
  `PopupExpandMC` and `btnBuyExpandTileMC`, alongside `expansion.png`.

The third question — whether the `neighbors` and `inventory_qte` requirements are
implemented or refused — is answered by refusing, because neither requirement can
be evaluated by anything the delivered stack can read. The fourth — what an
expansion does for the player — is a **known evidence gap**: the tile vocabulary
is established, but the tile-to-cell geometry is not, because the SWF inspection
is symbols-and-tags only and its own scope statement disclaims timeline semantics,
script behavior, and rendering. **That gap bounds visual land growth; it does not
block the evidence-supported unlock-ledger slice**, which is what this change
delivers.

## What Changes

- **Executed-legacy expand fixture** — capture one real `command.php` `expand`
  command from the real legacy Flask server inside a disposable copy under the
  pinned interpreter, committing request, complete before/after saves, response,
  manifest, and README under `tests/fixtures/godot-building-expand/`, with the same
  containment as the eight delivered captures, and with the clamp-reaching probe
  and the no-arbitration probe recorded as the evidence for the two endpoint
  guards.
- **Expansion price derivation** — an `expand_envelope` module deriving the
  six-key legacy batch envelope for exactly one `expand` command whose 8-slot
  resource vector is **derived from committed content** (the id's row in the
  98-entry `expansion_prices` positional table, `coins` into the gold slot and
  `cash` into the cash slot, as a debit), with the id-space derivation and the
  `coins`→gold mapping marked derived or established exactly as the design states.
- **Expansion execution endpoint** — `POST /v0/expand` on Compatibility API v0
  accepting only the intent `{user_id, expansion_id}`, rejecting an id outside the
  committed table and an id the player already owns (the two things the legacy
  server lets through and that would corrupt the ledger), refusing the
  `neighbors` / `inventory_qte` requirements it cannot evaluate, and answering with
  the legacy `result` plus an authoritative superset: the owned list before and
  after, the derived debit, the committed schedule row used, and the current
  resources.
- **A two-part post-state proof that includes the money** — the owned list grew by
  **exactly one** entry equal to the sent id **at the end**, and **every** stored
  resource changed by **exactly** the derived debit. This is the first endpoint
  whose second proof half exists specifically to catch a wrong server-derived
  price.
- **Typed expansion operation** — `GameApi.expand_town()` on both implementations
  (`FakeApi` as the deterministic in-memory double, `LegacyV0Api` over loopback
  JSON), with a typed result carrying both lists, the derived debit, the schedule
  row, and the resources.
- **Expansion flow** — an expansion readout on the delivered selection-driven
  surface (the committed schedule, the player's owned ids, the next purchasable
  entry and its derived cost) plus an `Expand` action — the **seventh mutually
  exclusive mode** — that sends exactly one intent and applies **only** the
  authoritative response, so a player's balances move by the server's numbers and
  never by the client's own arithmetic; a full rollback on any failure.
- **Evidence, tests, and documentation** — a windowed capture plus a deterministic
  `expand-report-v1` report under `apps/client-godot/evidence/building-expand/`, a
  hermetic `test_town_expand` suite plus fake/live GameApi coverage, an
  `expand-live` battery phase proving a disposable corpus save mutates, and
  `AGENTS.md` / README command, provenance, and claim-limit documentation including
  the land-shape gap and the corpus consequence named as gaps rather than features.

### Explicitly not in this change

**Terrain growth, grid enlargement, new buildable cells, and any change to the
placement bounds the delivered placement line enforces.** No committed evidence
maps an expansion id to land geometry, so none is invented; the tile-to-cell
mapping is recorded as a known evidence gap everywhere the slice is described.

Also out of scope: the neighbor and inventory requirement implementations, the
town-versus-map schedule disambiguation beyond what the corpus decides, `map_sizes`,
`increasedPopulation`, server-authoritative validation (Server v1 / M13), resources
and XP basics (the remaining M7 lines), and any change to the eight delivered
lines' behavior. Legacy sources, configs, saves, villages, committed fixtures,
conversion packages, registry manifests, and every delivered slice's evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). No Flash, Ruffle,
ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-expand`: unlocking a town expansion through the modern stack —
  an executed-legacy expand fixture as the parity oracle, a loopback-only
  `/v0/expand` intent endpoint whose debit is **derived from committed content**
  against the 98-entry positional expansion schedule, with the two guards the
  legacy server omits (range and duplicate), the unsupported-requirement refusal,
  and a **two-part post-state proof including the balances**, a typed
  `GameApi.expand_town()` operation, an expansion readout and `Expand` action on
  the selection-driven surface, and the evidence, containment, provenance, and
  claim limits that bound the expansion claim — including the land-shape gap.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all nine
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, `godot-building-sell`,
  `godot-building-store`, `godot-building-upgrade`, `godot-building-construction`,
  `godot-building-collect`, and `godot-building-expand`) as the only sanctioned
  execution paths, and the `GameApi` abstraction requirement gains the typed
  `expand_town()` operation with an "Expand through either implementation"
  scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/expand_envelope.py`, content
  accessors for an expansion price in `compat_legacy.py` (mirroring the delivered
  `item_upgrade_to` / `item_collect_amount` patterns), a `POST /v0/expand` route in
  `apps/compat-api/compat_service.py` (reusing the delivered `has_map_item` /
  `map_item` accessors and the collect endpoint's value-level proof), a new
  `apps/compat-api/capture_expand_fixture.py`, and new compat tests (envelope,
  endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `constants.py`, `sessions.py`,
  `config/`, `villages/`, `tests/saves/`, and every existing committed fixture are
  read only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`, `fake_api.gd`,
  `legacy_v0_api.gd`; `scripts/town/town_state.gd` (the typed owned-expansions
  list on a map), a new `scripts/town/expand_flow.gd` for the pure schedule and
  affordability helpers, `scripts/town/town.gd` (an expand mode and the readout); a
  new `tests/test_town_expand.gd`; scope-test allow-list entries and the new
  evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic expand suite and the
  `expand-live` phase; the Compatibility API guard baseline, the hash manifest, and
  both batteries must stay green with no new packages and no non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, `docs/legacy-town-expansion.md` (the four questions
  as resolved, including the two new pieces of committed evidence and the two new
  probe results), the new fixture README, and the roadmap Project Status ledger.