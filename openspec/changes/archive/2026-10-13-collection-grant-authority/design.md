# Design

## Context

`complete_collection` (`command.py:504-523`) is the only branch in the routed,
fixture-proven half of the command surface whose **grant** is already server-derived
from committed content. Everything else in that pool takes its outcome from client
arguments. That is what makes it the right second slice for Server v1, and it is also
what makes it tractable: parity is defined against committed content, so there is no
prediction involved.

The hole is large and is measured here rather than asserted. Four facts compose:

| # | Fact | Where measured |
| --- | --- | --- |
| 1 | The prize bag comes from committed content | `get_game_config.py:170-175` |
| 2 | Eligibility is never checked, and v0 says so | `compat_service.py:6170-6173` |
| 3 | The branch charges nothing; `cashPrice` is unread | `command.py:475-481` pattern; 0 consumers |
| 4 | The grant is not idempotent | `command.py:517-518` |

Composed: an unbounded, unconditional, free grant of any of ten committed prizes.

### The committed table, measured

All ten rows, from `packages/game-content/normalized/collections.json`, which is
normalized from raw `config/main.json` and does not lose either field (raw `item_ids`
occurrences: 10; raw `cashPrice`: 10).

| id | name | `item_ids` | `cashPrice` | `prize` |
| --- | --- | --- | --- | --- |
| 1 | Draggy Collection | 66,67,68,69,70 | 35 | `{"1085": 1}` |
| 2 | Transformer Collection | 46,47,48,49,50 | 60 | `{"1062": 1}` |
| 3 | Plane Collection | 51,52,53,54,55 | 75 | `{"1096": 1}` |
| 4 | Defense Collection | 71,72,73,74,75 | 10 | `{"164": 1}` |
| 5 | Gun Collection | 41,42,43,44,45 | 20 | `{"1073": 1}` |
| 6 | Tank Collection | 56,57,58,59,60 | 30 | `{"1010": 1}` |
| 7 | Launcher Collection | 76,77,78,79,80 | 9 | `{"45": 1}` |
| 8 | Soldier Awards Collection | 86,87,88,89,90 | 10 | `{"136": 1}` |
| 9 | Relaxing Time Collection | 81,82,83,84,85 | 10 | `{"106": 1}` |
| 10 | Animal Collection | 61,62,63,64,65 | 15 | `{"1056": 1}` |

Four measured properties of this table carry the design:

- **`item_ids` is uniform**: exactly 5 on every row, min = max = 5.
- **The 50 ids are disjoint** across the ten rows. Holding collection 1's five items
  confers no eligibility for collection 2. This is what makes eligibility a real
  membership test rather than a global flag, and it is why "does the player hold the
  requirements" is a checkable claim.
- **`cashPrice` is not constant**: 8 distinct values over 10 rows
  `{9, 10, 15, 20, 30, 35, 60, 75}`. This is a meaningful contrast with the social
  tables, where `findable_items.coins` is `100` on all 10 and `neighbor_assists.reward`
  is one identical object on all 5, and where a committed price would have carried no
  information even if a reader existed. Here a reader yields ten different prices.
- **`legacy_id` is 1..10 and equals `id` on every row.** This matters because
  `get_collection_prize` indexes `max(0, collection - 1)`, i.e. it treats the argument
  as a 1-based id. For `collection >= 1` that is correct; the clamp exists only to
  absorb `collection == 0` and negatives.

### Corpus feasibility

`tests/saves/fresh-player.json` and `fresh-player-pre-migration.json` both record
`privateState.collections == []` and `maps[0].store == {}`. So the committed corpus:

- **can** exercise the grant, and does so exactly as the committed fixture
  `tests/fixtures/godot-unit-collection/` records (`{}` → `{"1085": 1}`, ledger `[]` →
  `[1]`);
- **cannot** exercise the once-only refusal in a single call, because it requires a
  second call against an already-claimed collection. That is reachable by issuing two
  calls against a disposable corpus, which is what the live phase must do.

## Goals / Non-Goals

**Goals**

- Close the unbounded half of the hole: a collection is granted at most once.
- Make eligibility server-decided from committed `item_ids`.
- Make the price server-decided from committed `cashPrice`, and refuse the client
  vector outright.
- Keep the grant itself committed-derived, so the post-execution proof compares against
  committed content and remains non-tautological.

**Non-Goals**

- No change to `apps/compat-api/**`; it stays the oracle.
- No SQL / PostgreSQL / Alembic (line 1's D4 defers them to M14).
- No conversion of any other route; no adoption of v1 in gameplay.
- No claim about Flash client behaviour; every rule below is derived from committed
  content or the preserved branch.

## Decisions

### D1 — The request carries intent only: `{user_id, collection_id}`

No prize, item id, quantity, price, or resource delta is accepted. This is line 1's D3
carried forward and is not new: a request carrying a resource delta is **refused**, not
clamped and not ignored, because silently ignoring it is indistinguishable from a
working feature.

**Rejected alternative:** accepting an optional expected-prize field for comparison.
It would make the proof tautological by letting the client state the answer.

### D2 — The grant is committed-derived, and stays that way

The prize comes from the committed table through the same
`max(0, collection - 1)` positional index the legacy branch uses, and the response
carries the resolved index, whether the clamp moved it, and which id an aliased id
resolves to. This is inherited from v0's D1, which is already correct.

### D3 — An id that does not name a distinct committed collection is refused

`collection = 0`, and every negative id, clamp to index 0 and therefore resolve to
collection 1. A negative id would otherwise index the table from its end in a different
implementation; here it would silently alias.

v1 **refuses** rather than serving the clamped prize. Rationale: the clamp is a
legacy convenience for an id space the modern server does not have to accept, and
silently serving collection 1's prize for `collection_id: 0` is exactly the kind of
silent substitution this project has repeatedly recorded as a defect. v0's behaviour is
**preserved and reported**, and the refusal is recorded as a **divergence**, not as
parity.

**Rejected alternative:** reproduce the clamp and report `clamped: true`. It preserves
parity but preserves a defect, and the project has already chosen to refuse rather than
reproduce the client-dictated anti-pattern. The distinction is recorded per refusal:
this one is *derived from committed content*, not *client-sent*, so it is a judgement
call and is labelled as such.

### D4 — Eligibility is verified from committed `item_ids`

A collection may be claimed only when the player holds **every** one of its 5
`item_ids`. "Holds" means present in the player's recorded storage
(`maps[0].store`), which is the same place the prize is granted.

This is **derived**, not established: `item_ids` has **0 whole-file and 0 code-only**
occurrences across all seven legacy root modules, so no branch ever read it, and
nothing observed from the Flash client ever consulted it. The derivation is that the
field's own name, its uniform 5-per-row shape, and its disjointness across rows
describe a per-collection requirement list, and that the repository's own normalization
rule preserves it as a first-class field.

**Rejected alternatives:**

1. *Do not check eligibility* (v0's D2). Rejected: that is the hole.
2. *Treat any one of the 5 as sufficient.* Rejected: nothing supports it, and it would
   be inventing a threshold. All-or-nothing is the only reading the shape supports.
3. *Check against placed map rows instead of storage.* Rejected: the prize is granted
   **into storage**, so storage is the consistent place to look, and the requirement
   ids (41-90) are not committed units.

### D5 — The price is derived from committed `cashPrice`, and charged server-side

The completion costs `cashPrice`, debited from the player's stored cash by v1's own
economy authority. This is the strongest derivation in the line and the one most likely
to be wrong, so it is stated plainly: **the legacy branch charges nothing**, and the
legacy "cost", if a client paid one, arrived as a client-sent vector at
`command.py:40`. v1 charging a committed price is therefore a **divergence from the
preserved branch**, not parity, and it is justified on exactly the ground `AGENTS.md`
names: a client must never dictate a price.

**Rejected alternative:** charge nothing, matching the branch. Rejected because the
committed field exists, carries ten distinct values, and is unread; leaving it unread
keeps the free-grant hole's economic half open. Charging is also what makes
`cashPrice` a consumer rather than an eleventh zero-consumer field.

### D6 — The ledger is the once-only authority

`command.py:517-518` appends the collection id **only if absent**. That makes
`privateState.collections` the committed record of what has already been claimed, and v1
refuses a second claim on that basis.

This is derived from the branch's own control flow rather than invented, and it is the
one authority rule here that is *not* new content: the legacy branch already contains
the information needed to be idempotent and simply does not act on it.

**Rejected alternative:** a new "claimed" flag. Rejected: it would duplicate a field
that already exists and would create two sources of truth that can drift.

### D7 — A refusal moves nothing, and the proof is two-part

Inherited from line 1 and extended. A successful completion's post-execution proof has
two value-level halves:

1. the granted id **and quantity** equal the committed prize exactly, no other stored
   key moved, and **every stored resource moved by exactly the derived debit** (the
   `cashPrice`); and
2. the collection ledger matches the derived one - exactly one appended id when absent.

A refused completion must leave storage, ledger, and every stored resource
**byte-identical**.

The "no other resource moved" half is what makes the proof non-tautological: v0's
recorded fixture shows a *neutral* vector and no balance movement, while v1's own debit
must move cash by exactly `cashPrice` and every other slot by exactly zero.

### D8 — The status table stays in `server_v1_refusals.py`

Line 1 recorded that v0's 24 per-route derivations are the cost of a protocol that
gave the derivation nowhere central to live. v1's refusal vocabulary is **12** codes in
one table. New codes for this line are added **there**, and the route may not grow its
own answer. This is the shape that prevents the v0 failure from recurring.

### D9 — `apps/compat-api/**` is untouched

The oracle is not the thing being replaced. This change adds no v0 route, so the
Compatibility API suite stays at its recorded **3077** baseline as a **verified**
figure - re-run and reported, not assumed - exactly as `godot-friends` and
`godot-construction-assist` did.

## Risks / Trade-offs

- **D4 and D5 are derived, not established.** Both are recorded with their rejected
  alternatives, and both produce a **divergence** from the preserved branch. If a later
  line finds contrary evidence, D4 and D5 are the two decisions to revisit; the rest of
  the line does not depend on them.
- **Enforcing eligibility may refuse requests that the legacy server accepted.** That is
  the point, and it is why the refusals are typed and the divergence is labelled rather
  than hidden.
- **The once-only rule needs two calls** to exercise, so the hermetic suite cannot prove
  it from the fresh corpus alone and the live phase must issue two.

## Migration Plan

1. Extend `server_v1_refusals.py` with the codes this line needs (D8).
2. Implement the domain service: committed-table lookup, alias resolution (D3),
   eligibility (D4), price derivation (D5), once-only (D6).
3. Implement `POST /v1/collection` through the existing boundary; no new derivation path.
4. Hermetic client suite over `ServerV1Api` and its typed result, re-deriving every
   table figure from the committed package each run.
5. Live phase: two calls against a disposable corpus - one granted, one refused - and
   assert the save mutated on the first and stayed byte-identical on the second.

## Open Questions

- **Q1.** Should a partially-complete requirement set produce a distinct refusal code
  from an empty one? Treated as **one** code for this line, since both are "not
  eligible", with the missing ids reported in the refusal body. Re-opened if the client
  ever needs to render a progress hint.
- **Q2.** `item_ids` includes ids (41-90) that are neither committed units nor in the
  fresh corpus's storage. Whether those are buildings, units, or decoration is **not
  established** and does not affect the rule, which is membership in storage.