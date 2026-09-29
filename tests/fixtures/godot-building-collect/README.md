# Executed-legacy collect fixture (`godot-building-collect`)

The executed-legacy parity oracle for the Compatibility API v0 collect
endpoint: one real **`collect`** command carrying the **content-derived**
payout, captured from the real legacy Flask server (design D10 of the
`building-collect` OpenSpec change).  No Flash, browser, Ruffle, ActionScript,
or external network was involved — only the legacy server on loopback under
the pinned interpreter.

This is the **ninth** change in the same family and the first whose derived
resource vector is deliberately **not** neutral: every earlier line had to
invent nothing because nothing in the repository priced its action, while here
the committed configuration describes the income outright (`collect`,
`collect_type`, `collect_xp`, `max_collects`) and the collection ladder
(`COLLECT_MINUTES` / `COLLECT_MULTIPLIER`) is committed too.  That makes the
payout a **derivation**, and makes every rung of it **derived-provisional** —
the boundary is drawn explicitly below, as the construction fixture's is.

## How it was captured

```bash
python -B apps/compat-api/capture_collect_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move/sell/
store/upgrade/construction fixture digests, discards the copy, and only then
publishes this directory.  The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
store, upgrade, and construction captures):

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
tests/fixtures/godot-building-collect/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + established/derived split
│                                  with all six decisions, both executed
│                                  probes, steps, time-dependent leaves,
│                                  containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_collect/          POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the row's
                                  collection instant re-stamped and the
                                  derived payout applied to xp and wood
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because collect parity
compares *state changes* on the addressed row and the resource movement.

## The transaction

Intent (constants in `capture_collect_fixture.py`, verified against the
committed config and fresh save):

- **Building**: the placed **Tree**, item id `905` — `type "b"`, committed
  `collect "20"`, `collect_type "w"`, `collect_xp "1"`, `max_collects "0"`,
  `activation "6"` — at legacy map key `"2"`, anchored at `(53,39)`
  (`[905, 53, 39, 0, 0, [], {}, 1]` in the fresh save).
- **Why this row**: the committed fresh-player corpus has **no row with a
  recent collection instant** — all 40 rows carry `item[3] == 0` and
  `attr = {}` — so the elapsed time for any of them is unbounded and the
  **top** ladder rung applies deterministically in every run.  Slot `2` is the
  same row the store fixture puts into storage in **its own independent
  transaction** (each capture seeds a fresh corpus from the same committed
  save), so the two fixtures stay independently readable; the construction and
  move fixtures' slot `11` (a Turret I), the upgrade fixture's slot `12`
  (Wall I), and the sell fixture's slot `20` (a Turret I) are untouched here.
- **Contract**: one intent per collection step — a save id and the legacy map
  index.  No amount, resource, tier, time, price, or resource delta is sent by
  the client; the envelope is derived server-side (below).

Derived envelope:

```json
{"accessToken":"",
 "commands":[[0,"collect",[2],[0,3,0,60,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

That vector is `[0, xp, gold, wood, oil, steel, cash, mana]` with
`xp 1 x 3 = 3` in slot 1 and `wood 20 x 3 = 60` in slot 3 — the item's
committed income scaled by the **top** committed ladder rung
(`COLLECT_MULTIPLIER[3] = 3`), with the unread `unknown` slot 0 and the
never-produced `mana` slot 7 left zero.

### Established versus derived — the provenance split

The contract was established and recorded in
`docs/legacy-collect-income.md` before this fixture was written, so the
boundary is drawn explicitly here too.

**Established from committed legacy source and executed-legacy evidence**

| Fact | Evidence |
| --- | --- |
| `collect(item_index)` takes exactly one positional argument and writes **only** `item[3] = time_now()` | `command.py:136-147`; the `collect` row of `docs/legacy-protocol/commands.json` records the single `item[3] = time_now` write and the silent early return on a missing row |
| The income is **not** computed by the server: the client-sent 8-slot vector is applied **verbatim**, per resource, as `max(current + delta, 0)`, and the application runs **before** the branch | `command.py:40`, `engine.apply_resources` (`engine.py:251-271`); the catalog's `resource_effects` state both facts outright |
| The per-item income content: `collect` (amount), `collect_type` (which resource), `collect_xp` (experience), `max_collects` (a cap where non-zero) | `config/main.json`, census over the 778 stored items: `collect "0"` for 727; `collect_type` `g` 731 / `w` 23 / `o` 11 / `s` 11 / `c` 2; `collect_xp "0"` for 419; `max_collects "0"` for 767 with `"25"` (9) and `"100"` (2) |
| The collection ladder: `COLLECT_MINUTES = [5, 60, 240, 480]` and the parallel `COLLECT_MULTIPLIER = [0.25, 1, 2, 3]`, in **minutes** | the loaded `globals` of `config/main.json` |
| The corpus facts: the only income-bearing placed rows are the decorations — the Tree `905` at slot 2 and the eight `930` / `931` forest rows at slots 21-28, each `collect 20` / `w` / `1`; all 40 rows carry `item[3] == 0` | `tests/saves/fresh-player.json` joined against the committed `items` |
| A collection on a just-started construction overwrites the build's start instant while the recorded countdown **survives**, and the legacy server answers `{"result":"success"}` | **Probe 2** below, executed against this very server |

**Derived and never observed from the Flash client** — the six decisions, all
recorded verbatim in the module docstring of
`apps/compat-api/collect_envelope.py` and in the manifest's
`intent.derived.decisions`:

- **D1 — the amount formula.** `amount = collect x COLLECT_MULTIPLIER[r]` for
  the highest committed rung `r` the elapsed time has reached, **clamped at
  the top rung** and never extrapolated.  Supporting evidence: the two globals
  are parallel four-element arrays and the amount is otherwise a constant, so
  a ladder that did not scale the amount would have no effect at all.  *No
  legacy branch reads either global.*  *Rejected alternative:* a flat
  `collect`, or extrapolating past the last rung.
- **D2 — the experience scaling.** `collect_xp` is scaled by the **same** rung
  as the amount.  *Rejected alternative:* a flat `collect_xp`, which is
  equally unobservable and is recorded so a later change can revisit it with
  evidence instead of rediscovering it.
- **D3 — below the first rung.** No collection is offered and none is
  executed: the endpoint fails closed with `too_early` rather than deriving a
  quarter of the amount from the `0.25` multiplier.  The committed threshold is
  5 **minutes**, i.e. 300 **seconds** — the unit conversion is the only place
  it happens, and getting it wrong would pay the top rung within seconds.
  *Rejected alternatives:* deriving a sub-rung amount, and silently paying
  nothing.
- **D4 — the cap semantics.** Only a committed `max_collects` of `0` is
  implemented; a non-zero cap is **refused** with `capped_collection`, never
  interpreted, because nothing in the repository says whether a non-zero cap
  limits one collection, a daily total, or a building's lifetime output — the
  three readings imply different payouts.  *Rejected alternatives:* treating
  the cap as a per-collection limit, and ignoring it.
- **D5 — the shared `item[3]` field.** A collection is refused on a row whose
  attribute bag carries a countdown (`cp`) or a build-click counter (`nc`),
  in **both** layers: the client offers no `Collect` action, and the endpoint
  fails closed with `construction_in_progress` **before** the dispatcher runs.
  This is an **established risk with a derived rule** — the probe below shows
  legacy does *not* prevent the corruption and reports success; what the legacy
  client itself would do is never observed.
- **D6 — the cash and experience mapping.** `g` → gold (slot 2), `w` → wood
  (3), `o` → oil (4), `s` → steel (5), `c` → cash (6); the unread `unknown`
  slot 0 and the never-produced `mana` slot 7 are always zero, because **no
  item records a mana collect type**.  A type outside the committed five is
  refused with `unknown_collect_type`, never coerced.  *Rejected alternative:*
  a `"m"` mapping for a content value no item records.

The claim is therefore: **a payout that grows in four committed rungs, derived
from an item's committed income fields** — never any specific amount the
legacy client pays.

### The two executed probes

Both were executed against the real legacy server inside a disposable copy and
are recorded in full in the manifest's `probes` block.

**Probe 1 — what the branch writes, and is the vector applied verbatim?**
One command, `collect(2)` on the Tree, carrying a deliberately recognisable
vector `[0, 7, -5, 60, 0, 0, 0, 0]` (xp +7, gold −5, wood +60):

```
row 2 before: [905, 53, 39, 0, 0, [], {}, 1]
row 2 after : [905, 53, 39, <wall-clock>, 0, [], {}, 1]
placements 40 -> 40; every other row byte-identical
privateState identical; store {}; playerInfo identical
xp 4 -> 11; wood 2000 -> 2060; gold 2000 -> 1995
response {"result":"success"} (HTTP 200)
```

Established: the branch stamps **only** the row's timestamp, and the
client-sent vector is applied **verbatim**, per resource, including a negative
delta; nothing else in the save moves.  The **clamp was deliberately not
exercised** — a `−5` gold delta on a `2000` balance stays positive — so
`max(…, 0)` only bites when a delta would drive a balance below zero, which
the derived payouts of this change never do.

**Probe 2 — what happens on a row under construction?** (the evidence for
**D5**.) One batch, `activate(11, 3600)` then `collect(11)` with
`[0, 1, 0, 20, 0, 0, 0, 0]`:

```
row 11 before: [22, 58, 48, 0,       0, [], {},             1]
row 11 after : [22, 58, 48, <collect instant>, 0, [], {"cp": 3600}, 1]
xp 4 -> 5; wood 2000 -> 2020; every other row, privateState, playerInfo identical
response {"result":"success"}
```

`item[3]` moved to the **collect** instant while `attr["cp"] = 3600`
**survived**.  The row therefore still advertises a full hour of construction,
but its start instant is now the collection time: the delivered construction
line's remaining-time derivation `cp - (now - item[3])` measures the countdown
from the wrong epoch and silently restarts an active build's timer — and
legacy reports success.  So the overlap is not ambiguous, it is corruption, and
the safe rule is forced: the client refuses such a row **and** the endpoint
fails closed before the dispatcher runs, so a client that ignores the
client-side rule still cannot corrupt the timers the delivered construction
line depends on.

## The command

- `collect` takes exactly one positional arg — the legacy map index
  (`command.py:137`, and the `collect` row of
  `docs/legacy-protocol/commands.md`).  The index is the legacy map key as an
  integer: legacy resolves the row with `engine.map_get_item(map, index)`,
  i.e. `map["items"][str(index)]` (`engine.py:36-40`).
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the branch
  at `command.py:40`), and it carries the **derived payout** `[0, 3, 0, 60, 0,
  0, 0, 0]`.  Because the income travels entirely in this vector, the derived
  vector is the whole contract's substance here — the first delivered line
  whose vector is not a deliberate zero.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.
- `command()` persists the save **once** after the whole batch
  (`command.py:19-32`), so the single command is atomic with respect to the
  save file.

## The committed ladder and the Tree's payout at every rung

| rung | after | multiplier | wood (`20 x mult`) | xp (`1 x mult`) |
| --- | --- | --- | --- | --- |
| 0 | 5 minutes (300 s) | `0.25` | 5 | 0 |
| 1 | 60 minutes (3 600 s) | `1` | 20 | 1 |
| 2 | 240 minutes (14 400 s) | `2` | 40 | 2 |
| 3 | 480 minutes (28 800 s) | `3` | 60 | 3 |

The recorded request carries **tier 3**, the top rung, because every corpus
row's `item[3]` is `0` and the elapsed time is therefore unbounded.  The
endpoint never extrapolates past rung 3.

## Executed outcome (as recorded, verified by the tool before publishing)

- response `{"result":"success"}`;
- `maps[0].items["2"]` — `[905, 53, 39, 0, 0, [], {}, 1]` — becomes
  `[905, 53, 39, <wall-clock timestamp>, 0, [], {}, 1]`:
  - the same **key** and the same **cell** `(53,39)`, the same
    `orientation 0`, the same `player 1`, the same empty attribute bag, and
    still no stored units — a collection never destroys, moves, re-keys, or
    annotates a row;
  - **only** `item[3]` changes: the re-stamped **collection instant** (the
    branch writes it and nothing else), which is the one documented
    time-dependent leaf of the recorded state;
- the placement count stays `40` — no key is added or removed;
- every other placement row byte-identical;
- `maps[0].store` stays `{}` — a collection stores nothing;
- the whole `privateState` byte-identical, including `boughtUnits` (`[]`) and
  `deadHeroes` (`{}`): no collect command calls `bought_unit_add`,
  `push_dead_unit`, `buy_si_help`, `finish_si`, or `add_store_item`;
- `playerInfo` byte-identical;
- the resource movement, asserted by the tool to be **exactly** the derived
  payout under legacy's `max(current + delta, 0)`:
  `xp 4 → 7` (+3), `wood 2000 → 2060` (+60), and `gold 2000`, `oil 2000`,
  `steel 2000`, `playerInfo.cash 5`, `privateState.mana 0` all unchanged.

Exactly **three** leaves differ between the recorded before- and after-states
(asserted by `apps/compat-api/tests/test_collect_parity.py`):

| leaf | change |
| --- | --- |
| `/maps/0/items/2/3` | `0` → a wall-clock collection instant — **the documented time-dependent field** |
| `/maps/0/xp` | `4` → `7` — the derived experience |
| `/maps/0/wood` | `2000` → `2060` — the derived wood |

## Sanitization

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too).  The live requests always sent the real values — only the
records are redacted.  Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

Re-running the capture exits 0 and reproduces every file byte-identically
**except** these documented time-dependent fields.  Verified by a leaf-level
diff of two consecutive runs: **11 differing leaves in total**, every one of
them named in the manifest's `time_dependent_fields.leaves`:

- `/captured_at_utc` in both `request.json` and both `response.meta.json`
  (four files);
- `/executed_at_utc` in `capture-manifest.json`;
- `/headers/Date` in both `response.meta.json` files;
- the envelope `ts` inside `command_collect/request.json`'s `/form/data` (and
  therefore that whole field's string, because the digest covers the payload);
- the row's re-stamped wall-clock collection instant at
  `steps/command_collect/after.json`'s `/maps/0/items/2/3`, and the two
  manifest leaves derived from it — `/transaction/row_after/3` and
  `/transaction/steps/1/save_after_sha256`.

Everything else — both save states, both response bodies, the envelope's single
command, its argument, and the content-derived payout `[0, 3, 0, 60, 0, 0, 0,
0]` — is byte-stable.  The resource movement is byte-stable *by derivation*:
every corpus row's `item[3]` is `0`, so the top rung applies deterministically
and the payout is always the same vector.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the **eight** already committed fixture
directories — `godot-compatibility-boot`, `godot-building-placement`,
`godot-item-purchase`, `godot-building-move`, `godot-building-sell`,
`godot-building-store`, `godot-building-upgrade`, and
`godot-building-construction` — and fails closed if any of them changed during
the run, so this capture can never silently absorb an earlier change's
evidence.  Only the disposable copy is written and it is removed on every exit
path; no working-tree save is ever written; the service never binds anywhere
but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_collect_envelope.py` for the derivation, the closed resource
vocabulary, every rung, the six refusal paths, sanitization, and the capture
contract; `test_collect_endpoint.py` for the `/v0/collect` structural
contract, the five content/guard refusals, the two-part post-execution proof,
and corpus-only persistence; `test_collect_parity.py` consumes this fixture and
replays the recorded intent through the endpoint offline.)

### What this fixture proves

- the exact single-command envelope the Compatibility API derives for a
  collection, carrying the content-derived payout, and that the unchanged
  legacy dispatcher accepts it;
- that the executed transaction rewrites **exactly one** row in place — the
  same key, cell, item, orientation, store, attribute bag, and player — writing
  only its `item[3]`, and changes nothing else in the save;
- that the applied resource movement is **exactly** the derived payout, in
  exactly the two slots it names, with all five other resources untouched;
- that the endpoint's responses and its corpus save equal the captured response
  and after-state for every stable field.

### Claim limits

- Parity covers **this one recorded collection transaction against the
  fresh-player corpus** — not progressed players, not other commands, not a
  second collection, and not a second item.  The committed corpus is the whole
  corpus-side story available here.
- **Every number in the payout is derived.**  The amount formula (D1), the
  experience scaling (D2), the sub-first-rung refusal (D3), the cap semantics
  (D4), the shared-field refusal rule (D5), and the cash/experience mapping
  (D6) are all **derived-provisional** and never observed from the Flash
  client.  What is **established** is the branch's argument shape and its
  single write, the verbatim per-resource application of the client-sent
  vector under the documented clamp, the per-item income content and the
  ladder globals, the corpus facts, the construction-overlap corruption shown
  by Probe 2, and the resulting state of this executed transaction.  The claim
  is "a payout that grows in four committed rungs derived from committed
  income fields", never any specific amount the legacy client pays.
- The corpus's **only income-bearing rows are decorations** — the Tree and the
  eight forest rows — because the real factories and depots are not placed, so
  this fixture's payout is a decoration's.  Nothing is claimed about what a
  factory would pay beyond what its own committed `collect` / `collect_type` /
  `collect_xp` fields and the committed ladder derive.
- **The clamp is never exercised by this fixture.**  Legacy's
  `max(current + delta, 0)` only bites when a delta would drive a balance
  below zero, and the derived payout is a credit added to balances that sit far
  above zero.  The clamp itself remains exactly what `engine.py:262-268` says,
  and observing it would need a delta larger than the balance.
- **No cap semantics are implemented.**  Only a committed `max_collects` of
  `0` is; a non-zero cap is refused with `capped_collection` rather than
  interpreted, and that refusal is stub-covered in the endpoint's tests because
  no placed corpus item carries one.
- **No pixel-parity oracle against the legacy client exists.**  The client
  readout, its countdown, and the amounts a player sees are not compared to
  anything here.
- Legacy performs no ownership, state, or gameplay validation of any kind, so
  the endpoint's validation is structural fail-closed only, and authoritative
  validation belongs to Server v1 / M13.  An index that names no row is
  answered `unknown_item_index` rather than legacy's silent early return; a
  capped item, an unmappable type, a zero income, a sub-first-rung clock, and
  a row under construction are all refused **before** the dispatcher runs; and
  a post-state that is not the promised collection — the row gone, not eight
  fields, a non-integer or non-forward collection instant, or a resource that
  did not move by exactly the derived delta — fails closed with
  `internal_error` rather than reporting the legacy success.
- The `item[3]` overlap is **closed by refusal, not by interpretation**: this
  contract never treats a construction stamp as a collection stamp or the
  reverse.  A construction that resets a collection clock, or a collection that
  resets a build's timer, are both refused rather than modelled.
- The friend-assist cluster (`buy_si_help` / `finish_si` and the `attr["si"]`
  bag) is **out of scope**: a row carrying only `si` is collectible, because
  the construction-state refusal names exactly `cp` and `nc`.
- Friend assistance, construction speedups, the storage round trip, the premium
  upgrade path, `orient`, town expansion, XP basics, and anything
  server-authoritative are later deliver lines.
- No Flash, Ruffle, ActionScript, or browser executes, no external network is
  used, and no pixel-parity oracle against the legacy client exists.
