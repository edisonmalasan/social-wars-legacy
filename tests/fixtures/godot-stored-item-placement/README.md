# Executed-legacy stored-placement fixture (`godot-stored-item-placement`)

The executed-legacy parity oracle for the Compatibility API v0
`place_stored` and `sell_stored` endpoints: a real **`place_stored_item`**
and a real **`sell_stored_item`** against the committed fresh-player corpus,
both seeded by the **content-derived** `complete_collection` branch, captured
from the real legacy Flask server (design D1/D6 of the
`godot-stored-item-placement` OpenSpec change). No Flash, Ruffle, ActionScript,
or browser was involved, no external network was used, and every request went
to the legacy server on **127.0.0.1:5055** inside a disposable copy of the
repository.

This closes the round trip the delivered `godot-unit-collection` line recorded
as a carried follow-up: a unit acquired from **committed content** reaches the
map. The placement count grows **40 -> 41**, the placement count stays 41
through the sale, and every seed is content-derived, so no client-sent item id
list appears in any recorded transaction and **no fabricated player state** is
involved anywhere.

## What was captured

Five steps, in the order they were sent, against the committed corpus whose
`maps[0]["store"]` is `{}`, whose `privateState["boughtUnits"]` is `[]`, and
whose `privateState["collections"]` is `[]`:

| # | step | command | what it wrote |
| --- | --- | --- | --- |
| 1 | `login_post` | - (login form) | nothing; recorded for session fidelity |
| 2 | `command_complete_collection` | `complete_collection([1, 0])` | `store {"1085": 1}`, `collections [1]` |
| 3 | `command_place_stored_item` | `place_stored_item([41, 1085, 58, 47, 1, 0, 0, 0])` | the map row at slot **41**, `store {}`, `boughtUnits [1085]` |
| 4 | `command_complete_collection_2` | `complete_collection([2, 0])` | `store {"1062": 1}`, `collections [1, 2]` |
| 5 | `command_sell_stored_item` | `sell_stored_item([1062])` | `store {}` and **nothing else** |

Both seeds are the project's content-derived grant route, which is what makes
this fixture possible without fabricating storage: the committed prize of
collection **1** is exactly `{"1085": 1}` (unit `1085` Metal Draggy) and of
collection **2** is exactly `{"1062": 1}` (unit `1062` MegaBot). The client
names *which* collection and the server looks up *what it grants*.

### The placement

The row is server-owned in **five of its eight slots**:

| slot | value | owner |
| --- | --- | --- |
| 0 item id | `1085` | client (the placement's whole point) |
| 1, 2 cell | `58`, `47` | client (target cell) |
| **3 instant** | **server clock** | `int(time.time())`, `engine.py:13-14` |
| 4 orientation | `0` | client, verbatim passthrough |
| 5 garrison | `[]` | **always** an empty list, `engine.py:11-12` |
| 6 attribute bag | `{}` | **derived** from committed content, `engine.py:15-29` |
| **7 team** | **`1`** | **always**, `command.py:238` reads `args[4]` and `command.py:245` does not pass it on |

| | value |
| --- | --- |
| map slot | **41** (derived: smallest positive integer absent from `maps[0]["items"]`; the committed corpus places keys `1..40`) |
| committed `collection 1` prize | `{"1085": 1}` -> unit `1085`, Metal Draggy |
| `maps[0]["store"]` | `{"1085": 1}` -> `{}` |
| `privateState["boughtUnits"]` | `[]` -> `[1085]` |
| `maps[0]["items"]["41"]` | `[1085, 58, 47, <server instant>, 0, [], {}, 1]` |
| placement count | **40 -> 41** |
| every other row, the rest of the map, the player info | byte-identical |
| all seven stored resources | unchanged (`xp` 4, `gold`/`wood`/`oil`/`steel` 2000, `cash` 5, `mana` 0) |
| response | `{"result": "success"}` |

### The sale

`sell_stored_item` (`command.py:250-256`) reads one argument, calls
`remove_store_item` with its default `quantity=1`, and prints. **A sale credits
NOTHING**: the executed result changes **exactly one leaf**, the storage key,
because `remove_store_item` deletes the key when the remaining quantity is not
positive (`engine.py:80-83`). No row is added, no `boughtUnits` entry is written
or removed, no resource is credited, and no refund exists to claim.

| | value |
| --- | --- |
| item id sent | `1062` |
| `maps[0]["store"]` | `{"1062": 1}` -> `{}` |
| `privateState["boughtUnits"]` | `[1085]` -> `[1085]` (untouched) |
| `maps[0]["items"]` | every row untouched, count **41 -> 41** |
| changed leaves | **exactly one**: `/maps/0/store/1062` |
| all seven stored resources | unchanged |
| response | `{"result": "success"}` |

## The three-leaf correction to the change's own task text

The change's tasks predicted that the placement changes **exactly two leaves**
("the new row and the store key"). Measured, it changes **three leaves** for the
whole document and **two at map scope**:

```
/maps/0/items/41
/maps/0/store/1085
/privateState/boughtUnits
```

No conclusion changes. The cause is the seed route: the committed investigation
seeded with `store_add_items`, which calls `bought_unit_add` in the **same**
batch (`command.py:264`), so its ledger already held the id and the placement's
own append-if-absent (`command.py:246`; `engine.py:86-89`) left the ledger
alone. Seeding with the content-derived `complete_collection` instead - which
appends to `privateState["collections"]` and **never** to `boughtUnits` - makes
that third write observable. Both statements are pinned in
`capture-manifest.json`, under `changed_leaf_correction` and `placement`.

## Determinism and time-dependent fields

**NO normalization is applied.** The recorded state carries exactly **one
volatile state leaf**, `/maps/0/items/41/3`, the server clock read inside
`engine.map_add_item`. It is excluded from the replay comparison and that
exclusion is asserted to be the **only** exclusion; every other leaf of every
recorded document is compared by value. The seed step is compared with **no**
exclusion at all, because it precedes the placement and contains no placed row.

The sale's own before/after documents contain the placed row, so they move with
that instant even though the sale writes no clock value of its own. The
manifest's `time_dependent_fields.state_leaf_documents` names the five documents
that carry it. The parity suite additionally proves the claim mechanically:
`expected_row` called with two different instants yields two rows differing at
exactly `ROW_SLOT_TIMESTAMP`, so no other slot of the eight can be
clock-derived.

Everything else is byte-stable across reruns because each value is either a
fixed constant or a pure function of committed content: the derived slot, the
cell, the orientation, the empty garrison, the team, the attribute bag, the
appended ledger id, the placement count, and all seven stored resources. The
four probe batches and the two `store_add_items` preparation batches pin
`ts` to `1700000000`, and no probe is written as a step document, so no probe
save appears in this fixture at all.

### Rerun behavior

The fixture is **re-runnable**: re-running the capture exits 0 and reproduces
every file byte-identically **except** these documented time-dependent fields
(verified on 2026-10-03 by capturing three times and diffing the whole
directory with only the four field kinds below normalized; with them normalized
the directory was byte-identical across runs, and with them **not** normalized
every file carrying one differed):

- `captured_at_utc` in every `request.json` / `response.meta.json`, and
  `executed_at_utc` in `capture-manifest.json`;
- the HTTP `Date` response header (every step);
- the envelope `ts` inside each **recorded** command step's `request.json`
  `/form/data`, and therefore that whole field's string and its sha256 digest,
  because the digest covers the payload;
- consequently every `save_before_sha256` / `save_after_sha256` whose document is
  named in `time_dependent_fields.state_leaf_documents`, since those documents
  contain the placed row.

Everything else — every save state, every response body, the envelopes' single
commands, argument lists, and neutral resource vectors, the derived slot 41, the
`changed_leaf_correction`, the probes, and the containment digests — is
byte-stable. The full list is pinned in `capture-manifest.json` under
`time_dependent_fields.leaves`, so it cannot drift from the bytes it describes.

## The four refusals, recorded as executed probes

All four are **deliberate divergence** from the legacy server, which answers
`{"result": "success"}` in every case. They are recorded here as executed
probes with `parity: false`, never as parity, and none of them is replayed as a
success path.

| probe | question | legacy behaviour | modern refusal |
| --- | --- | --- | --- |
| 1 | place a committed unit that was never stored (`1071`) | places it anyway: rows 41 -> 42, store unchanged, `boughtUnits` grew | `not_in_storage` (409) |
| 2 | name a map key an existing row already holds (slot `1`, the Command Center) | **overwrites** it: five leaves rewritten, row **count** unchanged | `slot_occupied` (409) |
| 3 | name an id in no table anywhere (`999999`) | places a row with an empty bag and appends it to `boughtUnits` | `unknown_item_id` (409) |
| 4 | target a cell outside the grid (`(250, -3)`) | stores the cell verbatim and answers success | **none - recorded, not refused** |

Probe 1 is why `not_in_storage` is not vacuously true, and probe 2 is why a
placement proof must compare **values** and not counts: a count-based check
cannot see a destroyed row. `item_not_placeable` is a fifth code with no probe
of its own because **0 of 778 loaded rows and 0 of 900 normalized items** lack
both committed fields; it is exercised in the endpoint suite against an
in-memory row.

## Recorded gaps and out-of-scope work

* **Bounds are recorded, not refused.** Probe 4 stored `(250, -3)` verbatim.
  Tile-to-cell geometry is the already-recorded **M6 tile-to-cell geometry gap**;
  closing it needs new evidence, not a derivation, and inventing a `0..99` bound
  here would fabricate a rule the oracle does not have. Every success response
  therefore reports `geometry.bounds_refused == false`, which makes the gap
  mechanical rather than an oversight. Authoritative bounds validation belongs
  to Server v1 / M13.
* **Cell occupancy is not checked either.** No branch reads a neighbouring row
  and no committed content records a footprint-aware derivation. `slot_occupied`
  is not a contradiction of this: it destroys an **existing** row, which is a
  different and more serious failure than an out-of-range coordinate that
  damages nothing.
* **No capacity, expiry, value, or price rule exists** anywhere in the committed
  content or the legacy server on this path.
* **`store_add_items` is out of scope** (an unvalidated client-sent item id
  list). It appears in this fixture only as a **probe preparation** device and
  in no recorded transaction.
* No Python-to-English translation of any label; none is needed, because no
  legacy branch selects one.

## How it was captured

```
python -B apps/compat-api/capture_stored_placement_fixture.py
```

* Interpreter: the pinned **CPython 3.9.13** baseline for this change.
* Server: `python -B server.py` in a **disposable copy** of the repository under
  the system temp root, started after a TCP readiness check on 127.0.0.1:5055
  and stopped by `taskkill /T /F`, followed by a port-free re-check.
* **Exit code 0.** The capture fails before writing any fixture if the
  worktree hashes differ.
* The seed save is `tests/saves/fresh-player.json` (SHA-256
  `25df5b5a...2643f5`), copied verbatim as `saves/<pid>.save.json` in the
  disposable copy and never rewritten by these branches.

## Containment

* The disposable copy is removed before the manifest is written, and the server
  is stopped within the run; the port is free afterwards.
* A SHA-256 snapshot of every read working-tree group (`config`, `mods`,
  root Python files, `saves`, `templates`, `tests/saves`, `villages`) is taken
  before the run and after the server stopped, and is **identical**
  (`18e5e55b...a724`). No working-tree `saves/` exists before or after.
* The **sixteen** already-committed fixture directories are digest-pinned for
  the same reason and are unchanged.
* Loopback only; no Flash, Ruffle, ActionScript, or browser; no non-loopback
  traffic.
* The only working-tree writes are the fixture files under this directory.

## Claim limits

* Parity covers **five recorded transactions** (one of them the login form)
  against the **fresh-player corpus only**. No progressed-player save exists,
  so nothing is claimed about a populated town, a large storage, or a map whose
  keys are not `1..40`.
* The **derived** quantities are derived, not observed from the Flash client:
  that the client sends exactly `[[0, "place_stored_item", [41, 1085, 58, 47,
  1, 0, 0, 0], ...]]` and `[[0, "sell_stored_item", [1062], ...]]` is never
  observed. The envelopes' **shapes**, effects, recorded results, refusals, and
  changed-leaf sets are established; the argument values are
  **derived-provisional**, and the collection id space's one-based reading is
  **derived-provisional** too (corroborated by the committed content's own
  `id` column, and never observed from the Flash client).
* The captured round trip places a **1x1 unit**. Footprint-aware cell
  derivation for the 2x2 and 3x3 prizes is blocked on the same M6 gap and is
  recorded, not delivered.
* **No refund is claimed**, because none exists: the committed configuration
  records no stored-item sale price and the legacy branch writes only the store
  key.
* **No pixel parity** is claimed, and no storage **capacity** or **expiry**
  rule, no stock limit, no cell-occupancy rule, no grid bound, and no
  per-resource clamp; the legacy per-resource clamp is never exercised by this
  fixture because both derived vectors are the neutral all-zero vector.
* No Flash, Ruffle, ActionScript, or browser executes at any point, and every
  network call is loopback.