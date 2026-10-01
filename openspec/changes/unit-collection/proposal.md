# Proposal

## Why

M8 has delivered four of its eight lines: `unit definitions`, `unit instances`, `queues`, and
`production`. Line 5 is `collection`, and its investigation is committed as
`docs/legacy-unit-collection.md` (PR #224).

The first three M8 lines were defined by what the legacy server **cannot** do — a queue never
finishes, a unit is never produced — and `production` made that refusal a capability. This line
is **materially different, and in the project's favour**: it is the first M8 line to find a
**server-side grant that derives its contents from committed content**, and therefore the first
with a genuinely capturable unit transaction.

**The finding.** `complete_collection` calls `get_collection_prize(collection_id)`, which reads
the committed `collections` table positionally and returns its committed prize bag; the branch
then grants that bag into `map["store"]`. **Six of the ten committed collections grant a unit:**

| `collection_id` | Name | Committed prize |
| --- | --- | --- |
| 1 | Draggy Collection | **unit 1085 Metal Draggy** |
| 2 | Transformer Collection | **unit 1062 MegaBot** |
| 3 | Plane Collection | **unit 1096 F-117** |
| 4 | Defense Collection | building 164 |
| 5 | Gun Collection | **unit 1073 Erradicator** |
| 6 | Tank Collection | **unit 1010 APC** |
| 7 | Launcher Collection | building 45 |
| 8 | Soldier Awards Collection | building 136 |
| 9 | Relaxing Time Collection | building 106 |
| 10 | Animal Collection | **unit 1056 Elephant rider** |

**The client sends a collection id, never what it receives.** This **corrects and extends** the
`production` line's acquisition picture: `buy_offer_pack` and `buy_stored_item_cash` really are
unvalidated client-sent item lists, but they are **not the only route** — and this one derives its
grant from committed content, which the production investigation did not find.

**It is capturable against the corpus.** The committed save has `maps[0]["store"] == {}` and
`privateState["collections"] == []`, so a completion **writes** the committed prize into the
store — a real, observable, content-derived mutation. With `place_stored_item` (already covered by
the delivered `building-store` line) this is a **two-step, fully committed, server-derived path by
which a unit enters a town**, captured **without fabricating a player state**.

Two further facts shape the line. **`collect` is field-agnostic**: the whole command re-stamps the
row's slot-3 timestamp and does nothing else, and `collect`, `collect_type`, `collect_xp`,
`max_collects`, and `max_elem_vol` all have **zero** legacy reads — the fourth and fifth such
committed fields in this project — and `harvester`, which is **not** a top-level field but a
`properties` flag key on 5 Worker units all carrying `collect` 0, is likewise never read. And **no unit carries income at all**: 0 of 429 have a
positive `collect`, the five `harvester` units are on a disjoint set, and `max_collects` is 0 on
every unit, so the cap semantics `building-collect` deliberately refused have **no unit analogue**.

## What Changes

- **A typed, read-only collection-prize projection** over the committed `collections` table: the
  one-based index resolution with the recorded id-0/id-1 alias, the committed prize bag, and each
  prize classified as a **unit** or a **building** by resolving it against the content package.
- **An acquisition-path inventory** distinguishing the one **content-derived** route
  (`complete_collection` → `map["store"]` → `place_stored_item`) from the **unvalidated
  client-sent** routes the `production` line already recorded, so the difference is auditable
  rather than implied.
- **The two authority gaps recorded as requirements, not smoothed over**: nothing verifies that a
  collection was *earned*, so a client may name any of the ten; and the one-based index makes
  **id 0 and id 1 alias**. Both are stated as legacy-contract facts, and the second is marked
  derived-provisional with its rejected zero-based alternative.
- **The `collect` refusal for units** — no unit income derived, because no unit carries a positive
  `collect` and no collect field is ever read — plus the `max_collects` and `collect_xp` refusals,
  the latter reinforced by the delivered `godot-unit-production` requirement that **no experience
  is awarded from a client amount**.
- **An executed-legacy fixture** for `complete_collection` granting a committed **unit** prize
  into the corpus's empty store: **the project's first content-derived, server-authoritative unit
  acquisition**. Its endpoint proof asserts the granted id and quantity match the **content-derived**
  prize bag exactly and that the private-state collection ledger grew by exactly one appended id.
- **Tests and evidence** — a hermetic suite over the projection, the inventory, the refusals, the
  recorded gaps, and the absence of any collect/XP award path; the fixture-replay parity tests; a
  live battery phase; and a deterministic `unit-collection-report-v1` report.

### Explicitly not in this change

**No unit income and no unit collection payout**, because no unit carries a positive `collect` and
the server reads no collect field — so a collection cannot pay out income here. **No XP**, because
`collect_xp` is never read and the only command that writes `attr["xp"]` takes a client-sent amount.
**No collection eligibility check**, because none exists: the line records that gap and does not
invent one. **No claim that a collection is earned or that a client cannot name any collection.**
**No `collect` on a unit row**, because the corpus has no unit row and a unit has no committed
income. **No delivery of `place_stored_item`** — the stored-item round trip is a carried follow-up,
so the fixture stops at the grant into storage. **No production**, which the delivered
`godot-unit-production` capability already refuses. No `movement`, `animations`, or `basic
behaviors` — each its own later M8 line. No change to M8 lines 1–4 or the eleven M7 lines. No
pixel parity. Legacy sources, configs, saves, villages, the twelve delivered fixture directories,
conversion packages, and registry manifests stay byte-identical. No Flash, Ruffle, ActionScript,
or browser executes, and every network call is loopback.

## Capabilities

### New Capabilities

- `godot-unit-collection`: the committed collection prize as a typed, read-only, content-derived
  projection — including the six collections that grant a unit — together with the
  acquisition-path inventory separating the one content-derived route from the unvalidated
  client-sent ones, the recorded eligibility and index-alias gaps, and the refusals of unit
  income, cap semantics, and any experience award.

### Modified Capabilities

- `godot-building-collect`: its claim limits recorded that unit experience was out of scope
  because the corpus cannot exercise it; the sharper position is that **no unit carries income at
  all** and the server reads no collect field, so this capability's derived payout applies to
  buildings only.
- `godot-unit-production`: its acquisition finding named only unvalidated client-sent routes, which
  would read as "no committed unit is obtainable"; this capability adds the **content-derived**
  route, so the finding becomes complete rather than amended.
- `godot-compatibility-boot`: the execution boundary and `GameApi` abstraction gain the guarded
  collection-completion intent, which sends **only a player identifier and a collection id** and
  derives the grant entirely from committed content.

## Impact

- **Godot client** — a new `scripts/units/collection_prize.gd`, a new `tests/test_unit_collection.gd`,
  scope-test allow-list entries, and evidence under `apps/client-godot/evidence/unit-collection/`.
- **Compatibility API v0** — a new `collection_envelope.py`, a `POST /v0/collection` endpoint, and
  its post-execution proof; the compat suite **grows**.
- **Executed-legacy fixture** — a new `tests/fixtures/godot-unit-collection/` captured from a
  disposable copy of the legacy server.
- **Legacy** — unchanged and read only.
- **Content package** — unchanged and read only; prizes resolve through the registry's `units` and
  `buildings` domains, so the manifest digests remain the gate.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (32 hermetic) and a fifteenth live
  phase; the guard baseline, hash manifest, content validator, and both batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, `apps/compat-api/README.md`, and
  the roadmap Project Status ledger.
