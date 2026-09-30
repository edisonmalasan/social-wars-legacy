# Executed-legacy expand fixture (`godot-building-expand`)

The executed-legacy parity oracle for the Compatibility API v0 expand
endpoint: one real **`expand`** command carrying the **content-derived**
debit, captured from the real legacy Flask server (design D10 of the
`building-expand` OpenSpec change).  No Flash, browser, Ruffle, ActionScript,
or external network was involved — only the legacy server on loopback under
the pinned interpreter.

This is the **tenth** change in the same family and the second whose derived
resource vector is deliberately **not** neutral.  It is also the **first
fixture in the family with no time-dependent state leaf at all**: an
expansion writes an int the client sent into a list, and the derived debit is
the all-zero vector, so both recorded save documents and the response body are
byte-identical across reruns.  It is the first whose vector is a **debit**,
and therefore the first whose committed *requirements* decide whether any
price is payable at all.

## How it was captured

```bash
python -B apps/compat-api/capture_expand_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move/sell/
store/upgrade/construction/collect fixture digests, discards the copy, and
only then publishes this directory.  The opt-in legacy command recorder env
var (`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
store, upgrade, construction, and collect captures):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or the executed transaction did not match the
      derived envelope
6     Containment violation (working-tree bytes changed, a committed fixture
      directory changed, or the disposable corpus saves changed during
      server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-expand/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + established/derived split
│                                  with every decision, all three executed
│                                  probes, steps, time-dependent leaves,
│                                  containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_expand/           POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the owned-expansions
                                  ledger carrying one appended id
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because expand parity
compares the *whole* ledger and the resource movement, and because this
fixture's state carries no clock reading to normalize.

## The transaction

Intent (constants in `capture_expand_fixture.py`, verified against the
committed config and fresh save):

- **Expansion id**: `0` — a **free** row of the committed 98-entry positional
  `expansion_prices` schedule.  Indexes `0..3` all record `coins 0`, `cash 0`,
  `neighbors 0`, `inventory_qte 0`, so the derived debit is the **all-zero
  vector**.
- **Why this id — and it is the only honest choice on this corpus**: under
  design D3 a row recording a positive `neighbors` or `inventory_qte`
  requirement is refused with `expansion_requirements_unmet` (409), because
  the legacy server ignores both fields and nothing the delivered stack can
  read evaluates either.  **94 of the 98 committed rows record a positive
  requirement — including *every* id the corpus itself owns** (`35, 36, 45,
  46`, all at `neighbors 15` / `inventory_qte 30`).  The purchasable set and
  the free set are therefore the *same four indexes*, `0..3`; the capture
  asserts that identity against the real table before publishing, so a content
  drift that changed it would fail the run rather than quietly alter the
  claim.  The consequence is stated, not worked around: the delivered
  end-to-end transaction is a **zero-cost** expansion.
- **Contract**: one intent per expansion step — a save id and the expansion
  id.  No amount, resource, price, time, requirement flag, or resource delta
  is sent by the client; the envelope is derived server-side (below).

Derived envelope:

```json
{"accessToken":"",
 "commands":[[0,"expand",[0],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

That vector is `[0, xp, gold, wood, oil, steel, cash, mana]` and it is a
**debit**: every slot is `0` or negative.  The committed row for id `0`
records `coins 0` and `cash 0`, so the gold slot (2) and the cash slot (6) are
both zero, and the six slots no expansion price names — the unread `unknown`
slot 0, experience, wood, oil, steel, and mana — are zero as well.  Every
other resource is therefore left untouched, and legacy's per-resource clamp
never bites (see "Rerun behavior" and the claim limits).

### Established versus derived — the provenance split

The contract was established and recorded in `docs/legacy-town-expansion.md`
before this fixture was written, so the boundary is drawn explicitly here too.

**Established from committed legacy source, executed-legacy evidence, and
committed asset evidence**

| Fact | Evidence |
| --- | --- |
| `expand(expansion)` takes exactly one positional argument, coerces it with `int()`, appends it to `map["expansions"]`, and writes **nothing else** | `command.py:211-216`; the `expand` row of `docs/legacy-protocol/commands.json` records the single `map[expansions] += [int(expansion)]` write, the `map[expansions]` read, and the security note "client unlocks any expansion id; no adjacency, level, or cost verification" |
| The price is **not** computed by the server: the client-sent 8-slot vector is applied **verbatim**, per resource, as `max(current + delta, 0)`, and the application runs **before** the branch | `command.py:40`, `engine.apply_resources` (`engine.py:251-271`); the catalog's `resource_effects` state both facts outright |
| **The clamp is reachable**, for the first time in this family: a client-sent debit larger than the balance lands on zero | **Probe 1** below, executed against this very server |
| The server **cannot arbitrate the id space**: an out-of-range id, a duplicate, and a negative id all answer success | **Probe 2** below, executed against this very server |
| A non-integer id raises an unhandled server error | **Probe 3** below, executed against this very server |
| Nothing in the server reads, validates, prices, orders, or deduplicates `map["expansions"]` | a repository-wide search finds exactly three references to the word in the whole legacy server, all three inside the branch |
| The committed schedules: `expansion_prices` = **98** positional rows with **no stable id**, all four fields fully native numbers; `town_prices` and `map_prices` = 4 rows each with levels `15 / 25 / 35 / 45` (identical values, normalized as separate schedules and deliberately never deduplicated) | `config/main.json`; `docs/game-content/census.md` records "No stable ID; positional index" for `expansion_prices`; `docs/game-content/field-types.md` records the native numeric types; `packages/game-content/README.md` (economy extension) records the 98/4/4 normalization |
| The schedule's census: indexes `0..3` all zero; index `4` = `2500 / 5 / 1 / 1`; index `5` = `5000 / 8 / 2 / 2`; per-field saturation at `coins` index `14`, `cash` index `11`, `neighbors` index `18`, `inventory_qte` index `33`, so the whole row equals `100000 / 20 / 15 / 30` from index `33` to `97`; **only indexes `0..3` record no requirement** | `config/main.json`, joined over all 98 stored rows |
| The expansion price has exactly two components, and the client's own icon for one of them is named **`gold`** while the other is named **`cash`** — so the schedule's `coins` field is the client's `gold` | the committed asset registry carries `assets/images/en/expansion_gold.jpg` **and** `assets/images/en/expansion_cash.jpg` as two distinct images with distinct sha256s |
| An expansion is a purchasable **tile** bought through a popup | the committed SWF static inventory carries the symbols `PopupExpandMC` and `btnBuyExpandTileMC`, alongside `assets/images/en/expansion.png` |
| The tile → cell geometry is **not** derivable | `tools/asset-registry/README.md`'s own scope statement: the inspection establishes "no conversion, timeline semantics, script behavior, asset validity, gameplay parity, or Godot rendering" |
| The corpus facts: a level-1 fresh player whose `maps[0]["expansions"]` is **`[35, 36, 45, 46]`** (identical in the pre-migration save), 40 placements, `level 1`, `store {}`, `xp 4` / `gold 2000` / `wood 2000` / `oil 2000` / `steel 2000` / `playerInfo.cash 5` / `privateState.mana 0`, `increasedPopulation 0`, and **no** `map_sizes` field | `tests/saves/fresh-player.json` (and `fresh-player-pre-migration.json`) |

**Derived and never observed from the Flash client** — the decisions, all
recorded verbatim in the module docstring of
`apps/compat-api/expand_envelope.py` and in the manifest's
`intent.derived.decisions`:

- **D1 — the id space is the positional index of `expansion_prices`.**  The
  price comes from the 98-entry schedule, indexed by the expansion id itself.
  Supporting evidence: the corpus's own `[35, 36, 45, 46]` is a valid index
  into **this** table and is **not** a valid index into the 4-entry
  `town_prices` / `map_prices` schedules, and it is **not** a level set either
  — the schedules' `level` values are `15, 25, 35, 45`, and while `35` and
  `45` appear in the owned list, `36` and `46` do not.  **No legacy branch
  reads the schedule**, and Probe 2 is exactly why it is derived: the server
  offers no evidence to arbitrate the id space, so it cannot be settled by
  observing it.  Two consequences are carried explicitly: a level-1 fresh
  player owning four saturated-price (`coins 100000`) expansions is **not a
  coherent game state**, which is recorded as a reason to distrust the reading
  and bounds the claim to "the price the committed table assigns to the id";
  and because the server does not range-check, an id **outside** the schedule
  is refused (`unknown_expansion_id`, 404) and an **owned** id is refused
  (`already_expanded`, 409).  *Rejected alternatives:* indexing the
  four-entry schedules by level, and indexing by `len(map["expansions"])`.
- **D2 — `coins` is the client's `gold` and lands in server slot 2.**  The
  derivation is established by **committed asset names**, not by inference
  about which resource "coins" *might* be: `expansion_gold.jpg` and
  `expansion_cash.jpg` are the expansion popup's two committed price
  components, and the server's slot 2 is `map["gold"]` while slot 6 is
  `playerInfo.cash`.  The debit's **sign and shape** are derived: `[0, 0, -C,
  0, 0, 0, -K, 0]` for a row priced `coins C, cash K`, and the all-zero vector
  for a free row.  A vocabulary note, so the two namings are not read as a
  slip: the config uses **two** resource namings — `items[].costs` uses the
  *letter* set (`g` 279, `c` 375, `w` 128, `s` 110, `o` 69 occurrences) while
  the price schedules use the *word* set (`coins`, `cash`) — so a word-keyed
  price field is a second naming layer, and the committed asset name is the
  bridge.  *Rejected alternative:* reading `coins` as an unlabelled resource
  and guessing its slot.
- **D3 — the `neighbors` / `inventory_qte` requirements are refused, never
  invented.**  The server ignores both.  Nothing any delivered surface can
  read evaluates either: no neighbour count and no inventory quantity is
  exposed by the delivered bootstrap, the client's `GameApi`, or the corpus.
  A row recording a positive value therefore fails closed with
  `expansion_requirements_unmet` (409) **before** the dispatcher runs.
  *Rejected alternatives:* enforcing a neighbour count or an inventory
  quantity from state nothing delivers, and ignoring the requirement.
  *The consequence, asserted by the capture and by the tests rather than
  hidden:* **94 of the 98 committed rows are unpurchasable, including every
  id the corpus owns**, so the only purchasable entries in the whole schedule
  are the free indexes `0..3`, and the delivered transaction is a **zero-cost**
  expansion — the correct outcome under the evidence and the wrong outcome for
  gameplay.
- **D4 — the land effect is a recorded gap, and nothing is invented.**  This
  change delivers the expansion **unlock ledger** and nothing else.  **NOT**
  implemented and **NOT** claimed: terrain growth, grid enlargement, new
  buildable cells, or any change to the placement bounds the delivered
  placement line enforces.  The committed evidence establishes the vocabulary
  (a purchasable tile, bought through a popup, priced in gold and cash) but
  **not** the tile → cell geometry, because the committed SWF inspection is
  symbols-and-tags only and its own scope statement disclaims timeline
  semantics, script behavior, and rendering.  A known evidence gap that bounds
  visual land growth; closing it requires new evidence — an extracted geometry
  table, a rendered reference, or an authoritative spec — not a derivation.
- **D5 — intent only, and a two-part post-execution proof.**  The request
  carries only the save id and the expansion id.  After execution the endpoint
  requires **both** that the owned list grew by **exactly one** entry equal to
  the sent id **at the end**, with every existing entry unchanged and in order
  and never reordered or deduplicated, **and** that **every** stored resource
  changed by **exactly** the derived debit; any other outcome fails closed with
  `internal_error` rather than reporting the legacy success.  The value-level
  half is the first in this family to exist specifically to catch a wrong
  **server-derived** price — a derivation with the wrong sign, slot, or
  magnitude would otherwise mint or burn the wrong amount and be reported as a
  success.
- **D6 — an insufficient balance fails closed rather than reproducing the
  clamp.**  Because the debit is server-derived, the endpoint can know whether
  the balance covers it, and silently under-charging to the clamp would make
  the post-state proof ambiguous (a balance that moved by less than the derived
  debit is indistinguishable from a bug).  So an insufficient balance fails
  closed with `insufficient_resources` (409) before execution.  *Rejected
  alternative:* reproducing the clamp — whose **reachability** Probe 1
  establishes.

The claim is therefore: **a debit derived from the committed schedule row the
id names, appended once, at the end, of an untouched ledger** — never that it
is the price a coherent player pays.

### The three executed probes

All three were executed against the real legacy server inside a disposable copy
and are recorded in full in the manifest's `probes` block.

**Probe 1 — what does the branch write, and what happens when the client-sent
debit exceeds the balance?**  Two batches in one run: `expand(4)` with the
neutral vector `[0,0,0,0,0,0,0,0]`, then `expand(5)` with the
`expansion_prices[5]` debit `[0,0,-5000,0,0,0,-8,0]`:

```
expansions [35, 36, 45, 46] -> [35, 36, 45, 46, 4, 5]
changed top-level map keys: ['expansions', 'gold']
gold 2000 -> 0; playerInfo.cash 5 -> 0; xp, wood, oil, steel, mana unchanged
items identical: True   privateState identical: True
response {"result":"success"} for both batches
```

Established: the branch appends and changes **nothing else** — not `items`,
not `level`, not `map_sizes`, not `increasedPopulation`, not `privateState`,
not the rest of `playerInfo` — and the price is entirely client-sent, applied
verbatim per resource.  **The clamp bit, for real, for the first time in this
family**: a client-sent `−5000` gold debit against a `2000` balance landed on
**`0`**, not `−500`, and the `5` cash against `5` cash reached `0` exactly.  It
is reachable exactly when a client-sent debit exceeds the balance, and it is
the strongest available argument for a *server-derived* price and for design
D6's refusal instead of reproducing the clamp.

**Probe 2 — can the legacy server arbitrate the id space at all?**  Three
batches: `expand(999)`, a duplicate `expand(35)` (an id the corpus already
owns), and `expand(-1)`.  **All three answered `{"result":"success"}`**
(`expand(999)` produced `[35, 36, 45, 46, 999]`).  No range check, no dedup,
no ordering rule, no level gate, no requirement check.

This is the evidence for the endpoint's **two guards** and for D1's derived id
space: `unknown_expansion_id` (404) for an id the committed schedule does not
price, and `already_expanded` (409) for an id the player's own ledger already
contains.  Without them a client could buy an expansion no committed row
prices and could append a repeat, corrupting the only ledger this line
maintains.

**Probe 3 — what happens when the id is not an integer?**  One batch,
`expand("abc")`: an **unhandled HTTP 500** raised by `int("abc")` inside the
branch.  The branch coerces its argument and does not guard it, so a
non-integer id crashes the request instead of being refused.  This is the
evidence for the endpoint's structural `invalid_expansion_id` (400) check: the
value is refused before the dispatcher runs, so a client can never turn a
malformed id into an unhandled server error.

## The command

- `expand` takes exactly one positional arg — the expansion id
  (`command.py:212`, and the `expand` row of
  `docs/legacy-protocol/commands.md`).  The branch binds `args[0]`, coerces it
  with `int()`, and appends it: `map["expansions"] += [int(expansion)]`.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the branch
  at `command.py:40`), and it carries the **derived debit**
  `[0, 0, 0, 0, 0, 0, 0, 0]`.  Because the price travels entirely in this
  vector, the derived debit is the whole contract's substance here.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.
- `command()` persists the save **once** after the whole batch
  (`command.py:19-32`), so the single command is atomic with respect to the
  save file.

## The committed schedule, and what the endpoint's refusals do with it

| indexes | `coins` | `cash` | `neighbors` | `inventory_qte` | purchasable? |
| --- | --- | --- | --- | --- | --- |
| `0 … 3` | `0` | `0` | `0` | `0` | **yes** — the free rows; derived debit is the all-zero vector |
| `4` | `2500` | `5` | `1` | `1` | no — `expansion_requirements_unmet` (409) |
| `5` | `5000` | `8` | `2` | `2` | no — `expansion_requirements_unmet` (409) |
| `6 … 13` | `10000` … `75000` | `10` … `20` | `3` … `10` | `3` … `10` | no — `expansion_requirements_unmet` (409) |
| `14 … 17` | `100000` | `20` | `11` … `14` | `11` … `14` | no — `expansion_requirements_unmet` (409) |
| `18 … 32` | `100000` | `20` | `15` | `15` … `29` | no — `expansion_requirements_unmet` (409) |
| `33 … 97` | `100000` | `20` | `15` | `30` | no — `expansion_requirements_unmet` (409) |

Per-field saturation starts at `coins` index `14`, `cash` index `11`,
`neighbors` index `18`, and `inventory_qte` index `33`; the whole row first
equals its final `100000 / 20 / 15 / 30` form at index `33` and is unchanged
from there to index `97`.

**94 of the 98 rows are unpurchasable under the requirements rule.**  The
`town_prices` / `map_prices` schedules (levels `15 / 25 / 35 / 45`, `coins`
`100000 / 300000 / 550000 / 1000000`, `cash 20`) are recorded but **not used**
by this line.

## Executed outcome (as recorded, verified by the tool before publishing)

- response `{"result":"success"}`;
- `maps[0].expansions` — `[35, 36, 45, 46]` — becomes
  **`[35, 36, 45, 46, 0]`**:
  - the ledger grew by **exactly one** entry;
  - the new entry is **the sent id `0`**, appended **at the end**;
  - the existing `[35, 36, 45, 46]` are **unchanged, in the same order, and
    not deduplicated** — legacy neither orders nor deduplicates, and the
    endpoint never rewrites or normalizes the ids it finds there;
- the placement count stays `40` — no key is added or removed, and **every one
  of the 40 rows is byte-identical**: an expansion rewrites no placement at
  all;
- `maps[0].level` stays `1`, `maps[0].increasedPopulation` stays `0`,
  `maps[0].store` stays `{}`;
- `map_sizes` stays **absent** — the committed corpus does not record that
  field (nor does any committed legacy source or the committed config), so its
  *absence* is what the whole-key-set equality check enforces; the tool also
  asserts explicitly that the field's presence did not change;
- **every other top-level map field is byte-identical**, and the map's whole
  top-level key set is unchanged (so no field this README does not name could
  have moved either);
- the whole `privateState` byte-identical, including `boughtUnits` (`[]`) and
  `deadHeroes` (`{}`): no expand branch calls `bought_unit_add`,
  `push_dead_unit`, `buy_si_help`, `finish_si`, or `add_store_item`;
- `playerInfo` byte-identical;
- **all seven stored resources are unchanged**, because the derived debit is
  the all-zero vector: `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`,
  `steel 2000`, `playerInfo.cash 5`, `privateState.mana 0`.

Exactly **one** leaf differs between the recorded before- and after-states:
`/maps/0/expansions/4` — the appended `0`.  That is asserted by
`apps/compat-api/tests/test_expand_parity.py`, and it is the first
delivered fixture in the family with a single-leaf transaction.

## Sanitization

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too).  The live requests always sent the real values — only the
records are redacted.  Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

**The recorded state and the recorded response have no time-dependent field
at all.**  An expansion writes an int the client sent into a list and the
derived debit is the all-zero vector, so `steps/login_post/before.json`,
`steps/login_post/after.json`, `steps/command_expand/before.json`,
`steps/command_expand/after.json`, and both `response.body` files are
**byte-identical across reruns** — verified by a leaf-level diff of two
consecutive runs.  There is no wall-clock reading anywhere in the recorded
state: unlike `collect`'s `item[3] = time_now()`, the expand branch writes no
clock of its own.

That diff found **exactly 8 differing file+pointer paths in total**, every one
of them named in the manifest's `time_dependent_fields.leaves`, and **none of
them in the state or the response**:

- `/captured_at_utc` in both `request.json` and both `response.meta.json`
  (four files);
- `/executed_at_utc` in `capture-manifest.json`;
- `/headers/Date` in both `response.meta.json` files;
- the envelope `ts` inside `command_expand/request.json`'s `/form/data` (and
  therefore that whole field's string, because the digest covers the payload).

Everything else — both save states, both response bodies, the envelope's
single command, its argument, and the content-derived debit
`[0, 0, 0, 0, 0, 0, 0, 0]` — is byte-stable.  The manifest's
`time_dependent_fields.state_leaves` is the **empty list**, deliberately: the
documented time-dependent *state* surface of this fixture is empty, and no
leaf was invented to fill it.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the **nine** already committed fixture
directories — `godot-compatibility-boot`, `godot-building-placement`,
`godot-item-purchase`, `godot-building-move`, `godot-building-sell`,
`godot-building-store`, `godot-building-upgrade`,
`godot-building-construction`, and `godot-building-collect` — and fails
closed if any of them changed during the run, so this capture can never
silently absorb an earlier change's evidence.  Only the disposable copy is
written and it is removed on every exit path; no working-tree save is ever
written; the service never binds anywhere but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_expand_envelope.py` for the derivation, the id-space rule, the debit's
sign and slot mapping, the requirements refusal, every slot that must stay
zero, the shared-helper round trip, real-config cross-checks, and the capture
contract; `test_expand_endpoint.py` for the `/v0/expand` structural contract,
the two guards, the two content refusals, the two-part post-execution proof,
and corpus-only persistence; `test_expand_parity.py` consumes this fixture and
replays the recorded intent through the endpoint offline.)

### What this fixture proves

- the exact single-command envelope the Compatibility API derives for an
  expansion, carrying the content-derived debit, and that the unchanged legacy
  dispatcher accepts it;
- that the executed transaction appends **exactly one** entry equal to the sent
  id **at the end** of the ledger, with the existing `[35, 36, 45, 46]`
  unchanged, in order, and not deduplicated, and changes **nothing else** in
  the save;
- that **no** stored resource moved, because the derived debit is the
  all-zero vector;
- that the endpoint's responses and its corpus save equal the captured response
  and after-state for **every** leaf, with no clock normalization at all.

### Claim limits

- Parity covers **this one recorded expansion transaction against the
  fresh-player corpus** — not progressed players, not other commands, and not a
  second expansion.  The committed corpus is the whole corpus-side story
  available here.
- **The id-space indexing is derived, not observed.**  The server accepted
  `999`, a duplicate, and `−1` alike, so it offers no evidence to arbitrate;
  the reading rests on the corpus's own `[35, 36, 45, 46]` being a valid index
  into the 98-entry table and neither a valid four-entry index nor a level set.
  The claim is "the price the committed table assigns to that id", never "the
  price a coherent player pays" — and the corpus's own four owned ids are
  recorded as **incoherent** under the chosen schedule, which is a reason to
  distrust the reading rather than to accept it.
- **No id the corpus owns could have been bought under the requirements rule.**
  All four record `neighbors 15` / `inventory_qte 30`, and 94 of the 98
  committed rows record a positive requirement, so the only purchasable
  entries are the free indexes `0..3` and the delivered transaction uses a
  **zero-cost** committed row.  Nothing is claimed about what a **priced**
  expansion would cost a player on this corpus: the priced path is exercised in
  the endpoint's tests by stubbing the committed row, never by a committed
  price the requirements rule would let through.
- The debit's **sign and shape** are derived: that the price is a debit, that
  `coins` is negated into the gold slot and `cash` into the cash slot, and that
  the six unnamed slots stay zero.  What is **established** is that the branch
  appends the id and changes nothing else, that the client-sent vector is
  applied verbatim per resource under the documented clamp, the three probe
  results, the committed schedules and their census, the committed asset names
  that settle `coins` → `gold`, and the resulting state of this executed
  transaction.
- **The clamp is not exercised by this fixture.**  The committed row is free,
  so the derived debit is the all-zero vector and no balance moves at all.  The
  clamp itself remains exactly what `engine.py:262-268` says, and Probe 1
  establishes that it is reachable when a debit exceeds the balance.
- **The affordability refusal is preferred over reproducing the clamp.**  The
  clamp alternative is recorded as the rejected option; the reason it was
  rejected is that a partially applied debit is indistinguishable from a wrong
  server-derived price, which is what design D5's value-level proof exists to
  catch.
- **No claim is made about any area of the town becoming buildable.**  This
  change delivers the **unlock ledger** only.  There is **no** terrain, grid,
  buildable-cell, footprint, or placement-bound behavior anywhere in the
  derivation, the endpoint, or this fixture, and none is claimed: no committed
  source maps an expansion id to land geometry.  The committed evidence
  establishes the *vocabulary* — a purchasable tile, bought through a popup,
  priced in gold and cash (`PopupExpandMC`, `btnBuyExpandTileMC`,
  `expansion.png`, `expansion_gold.jpg`, `expansion_cash.jpg`) — and the
  committed inspection's own scope statement is why the **tile → cell geometry**
  cannot be derived from the preserved evidence.  That is a **known evidence
  gap** bounding visual land growth, and closing it needs new evidence rather
  than a derivation.
- **No pixel-parity oracle against the legacy client exists.**  The client
  readout, the popup, and the amounts a player sees are not compared to
  anything here.
- Legacy performs no ownership, state, or gameplay validation of any kind, so
  the endpoint's validation is structural fail-closed plus the two guards and
  the two content refusals named above; authoritative validation belongs to
  Server v1 / M13.  An id outside the schedule is answered
  `unknown_expansion_id`, an owned id `already_expanded`, a blocked row
  `expansion_requirements_unmet`, and an unaffordable balance
  `insufficient_resources` — all **before** the dispatcher runs, so the corpus
  is byte-identical on every error path; and a post-state that is not the
  promised transaction — the ledger not grown by exactly the sent id at the end
  with the existing entries unchanged and in order, or a resource that did not
  change by exactly the derived debit — fails closed with `internal_error`
  rather than reporting the legacy success.
- The committed corpus's own ledger is **incoherent** under the chosen
  schedule and is therefore **tolerated verbatim**: the endpoint must not
  rewrite, normalize, reorder, or deduplicate the ids it finds, and a ledger
  entry this service cannot read as an integer fails closed rather than being
  coerced.
- The `neighbors` / `inventory_qte` requirement **implementations** — whatever
  a neighbour count or an inventory quantity means, and how the client would
  evaluate either — are out of scope, as are `map_sizes`, `increasedPopulation`,
  the town-versus-map schedule disambiguation beyond what the corpus decides,
  and anything server-authoritative (Server v1 / M13).
- No Flash, Ruffle, ActionScript, or browser executes, no external network is
  used, and no pixel-parity oracle against the legacy client exists.
