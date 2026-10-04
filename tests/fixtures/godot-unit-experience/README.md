# Executed-legacy unit-experience fixture (`add_xp_unit`)

Golden fixture for the **single** legacy `add_xp_unit` branch, `command.py:322-343`,
captured by executing the real legacy Flask server against a committed, progressed
village save. Contract: `docs/legacy-unit-xp.md`. Change: `unit-experience-evidence`.

## What this fixture is, and what it is not

It is **evidence about an oracle**. It records what the legacy server does when a
client sends `add_xp_unit`.

It is **not** a client intent, and it does **not** license a modern endpoint. The
amount is `args[1]`, taken from the request with **no validation of any kind**, not
even `int()`. Three independent measurements refute the committed per-unit experience
field as the award's source. Delivering a route from this evidence would mean either
repeating the untrusted-amount anti-pattern or building something that exists only to
refuse — so this line delivers evidence and a correction, and the compat-side guard
asserts that no unit-experience route is answered and no award helper exists.

## Command

```bash
python -B apps/compat-api/capture_unit_xp_fixture.py
```

Pinned interpreter: CPython 3.9.13 (Windows x64). The `python` on `PATH` is not it
and every pinned tool here refuses that one.

| | |
|---|---|
| Observed exit code | **0** |
| Transactions recorded | **12** (plus one recorded login step) |
| Legacy server starts | **12** — one per transaction |
| Containment digest, before and after | `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724` — **identical** |
| Seed `villages/AcidCaos.json` sha256 | `870a3c2001dcaccdb0feb743a02c3062c2172ffd011523f5e220be91cd20e9cd` — identical |
| Working-tree `saves/` after the run | **absent** |
| Already-committed fixtures after the run | **17 unchanged**, byte for byte |
| Consecutive identical runs | **3** |
| Network | loopback `127.0.0.1:5055` only |

No Flash, Ruffle, ActionScript, or browser executes anywhere in this command.

## The seed, and why this one

`villages/AcidCaos.json` — a **committed** save, used as-is. **No player state is
fabricated**, which is the point: this is the repository's first capture seeded from a
village save rather than from `tests/saves/fresh-player.json`, and it exists because
the fresh corpus has **zero** placed rows carrying `attr["xp"]`, so it cannot exercise
this branch at all.

Choice status: **derived-provisional**, chosen by measurement rather than preference.
It is the smallest of the five committed save documents carrying the field by
placed-row count (**319**, against 569 / 367 / 549 / 576), and it carries **36** rows
*with* the key and **283** *without* it — including **12** unit rows with an empty bag
and **271** building rows — so both write arms and both row kinds are exercisable from
one authentic document. Any other of the five would also have worked; the choice is
recorded so a rerun reproduces these bytes.

The pid is read from `playerInfo.pid` **in the document**, never derived from the
filename stem. For three of the eight committed village saves the two disagree
(`GM30.json` → `100000030`, `GM31.json` → `100000031`, `initial.json` → `null`), and a
`null` pid makes the harness fail loudly rather than write a `None.save.json`.

## One server per transaction — not an optimisation

`sessions.load_saves()` caches the corpus in a module global **at import time**, so a
running server never re-reads the save file from disk. Restoring the seed between
probes on one server leaves the *in-memory* corpus already mutated and silently
produces a different result. The investigation that established this contract lost its
first twelve probes to exactly that. Twelve disposables, twelve servers, twelve stops.

Each disposable also asserts that the corpus is **unchanged by server startup**, so a
server that failed to read the committed seed is caught rather than measured.

## The twelve transactions

All batches carry the **neutral** resource vector `[0,0,0,0,0,0,0,0]`, and `ts` is
pinned to `1700000000` so the recorded `data` field is byte-stable.

| step | args | status | `attr["xp"]` | changed leaves |
|---|---|---|---|---|
| `txn_increment_existing` | `[772, 5]` | 200 | `23` → `28` | `/maps/0/items/772/6/xp` |
| `txn_assign_absent_key` | `[1783, 7]` | 200 | absent → `7` | `/maps/0/items/1783/6/xp` |
| `txn_missing_row` | `[999999, 5]` | **200** | row absent → row absent | **none** |
| `txn_negative_no_clamp` | `[772, -1000]` | 200 | `23` → `-977` | `/maps/0/items/772/6/xp` |
| `txn_zero_amount` | `[772, 0]` | 200 | `23` → `23` | **none** |
| `txn_unbounded_amount` | `[772, 1000000000000]` | 200 | `23` → `1000000000023` | `/maps/0/items/772/6/xp` |
| `txn_float_amount_persisted` | `[772, 2.5]` | 200 | `23` → `25.5` | `/maps/0/items/772/6/xp` |
| `txn_building_row_type_agnostic` | `[3, 11]` | 200 | absent → `11` | `/maps/0/items/3/6/xp` |
| `txn_level_argument_ignored` | `[772, 5, 9]` | 200 | `23` → `28` | `/maps/0/items/772/6/xp` |
| `txn_string_amount_increment_fails` | `[772, "5"]` | **500** | `23` → `23` | **none** |
| `txn_string_amount_assign_persisted` | `[1783, "5"]` | 200 | absent → `"5"` | `/maps/0/items/1783/6/xp` |
| `txn_bool_amount_increments_as_one` | `[772, true]` | 200 | `23` → `24` | `/maps/0/items/772/6/xp` |

Every transaction asserts, offline, from its own before/after documents: the recomputed
whole-document leaf diff equals the claimed set; the digest over **every leaf outside**
that set is equal before and after; the placed-row count is unchanged; and **all seven
stored resources are byte-identical**. The seed's `attrs` bags and the recorded values
are compared with a **type-aware** equality that refuses to call `1`, `1.0` and `True`
equal — which matters here, because the boolean row is real evidence and a
value-only comparison would pass it for the wrong reason.

The resource slots are read at the three different owners `engine.apply_resources`
actually uses (`engine.py:251-271`): five on `maps[0]`, `cash` on `playerInfo`, `mana`
on `privateState`. `energy` is excluded — nothing in the legacy source ever writes it,
so including it would make the "unchanged" proof cover a value this branch cannot move.

## The five findings this fixture establishes

1. **Two write arms, both unguarded.** Present key → `attr["xp"] += args[1]`; absent
   key → `attr["xp"] = args[1]`. No range check, no bound, no type check, no
   membership test.
2. **A missing row still answers success.** An unaddressable key hits the falsy-item
   early return, prints `Error: item not found.` and *returns* — and the server answers
   the legacy `{"result": "success"}`. A client cannot tell this from a real award by
   the response alone.
3. **No clamp and no bound.** A client-sent `-1000` persists `-977`. A client-sent
   `10**12` persists verbatim. This is the sharp asymmetry with
   `engine.apply_resources`, which runs every vector slot through `max(..., 0)`.
4. **The branch is type-agnostic.** Key `3` is a **Wall I** building row, and it
   accepts and stores unit experience exactly as a unit row does.
5. **The two arms are asymmetric on type.** The assign arm **persists** a string;
   the increment arm **raises** `TypeError` against one and answers HTTP 500. So one
   request can poison a save, and every later increment against that row then fails.
   This reachable state is why the delivered projection classifies the recorded value's
   kind instead of reporting a bare value.

`True` is worth exactly **+1**, because the branch does arithmetic on the gain — which
is why `bool` is a separate member of the delivered projection's closed classification
vocabulary and is not folded into `int`.

## The third argument is display-only — established, not read off the source

`txn_increment_existing` sends `[772, 5]`; `txn_level_argument_ignored` sends
`[772, 5, 9]`. The capture asserts the pair, and refuses to publish otherwise:

- same `attr` afterwards — **true**
- same changed-leaf set — **true**
- same whole-state sha256 — **true**
- same printed line — **false**, and required to be false

```
two:   [+] COMMAND: add_xp_unit(['772', 5])    -> Soldier +5xp
three: [+] COMMAND: add_xp_unit(['772', 5, 9]) -> Soldier +5xp BOUGHT LEVEL UP -> 9
```

The stored effect of `args[2]` is nil. *Derived-provisional:* that the two forms are
**interchangeable**, because their stored effects were measured equal; the source shows
a truthiness test feeding only an f-string.

The failing string case records the dispatcher's trace line with an **empty** result —
`[+] COMMAND: add_xp_unit(['772', '5']) ->` — because the branch raised before reaching
its own print. That is the oracle reporting its own failure, captured verbatim.

## Determinism, stated precisely

Three consecutive runs produce **byte-identical** `before.json`, `after.json`,
`transaction.json` and `response.body` for all twelve transactions, and a
byte-identical manifest body.

Exactly three kinds of file differ between runs, and only because of one field:
`request.json`, `response.meta.json` and `capture-manifest.json`, each carrying a
wall-clock `captured_at_utc`. That is the provenance stamp every capture in this
repository records, so "byte-identical rerun" is claimed for the evidence and not for
those stamps. `ts` is **not** volatile: it is pinned, exactly as on the
stored-placement capture.

## The failing transaction's body is safe to commit

`server.py` runs `app.run(..., debug=False)`, so a failing request answers the
framework's plain error page — no traceback, no absolute path. The capture **asserts**
the body does not contain the disposable path before writing it, rather than assuming
it, because a leaked temp path would make the fixture non-reproducible and would
record machine-specific state.

## Layout

```
README.md
capture-manifest.json
steps/login_post/                      request, before, response.body, response.meta, after
steps/txn_<name>/request.json          the exact crafted batch
steps/txn_<name>/before.json           full canonical save document
steps/txn_<name>/response.body         exact response bytes
steps/txn_<name>/response.meta.json    status, reason, headers, byte count, sha256
steps/txn_<name>/after.json            full canonical save document
steps/txn_<name>/transaction.json      the verified facts for this transaction
```

`before.json` / `after.json` are **full** canonical save documents, per this
repository's stated preference for golden fixtures carrying request, before, response
and after state. At **1,465 KB** across 79 files this is the repository's second-largest
fixture; the size is **26 copies** of one 53 KB save (the 12 transactions plus the login
step, before and after), which is what makes every transition independently diffable by
a reviewer with `git diff`. The full-document shape was chosen over a compact leaf-delta
encoding precisely because the compact form would still need the seed committed once and
would make a reviewer's diff depend on a reconstruction step.

`transaction.json` is this line's addition to the house shape. Every other fixture
verifies its transaction and then records only the response; because this line has no
endpoint to replay against, the verification output is committed **as** the evidence,
so the fixture stays checkable offline forever. `apps/compat-api/tests/test_unit_xp_fixture.py`
recomputes it.

## Redactions

`user_key` in the recorded form, and `Cookie` / `Set-Cookie` in recorded headers. The
live request always sends the real bytes; only the record is redacted. `accessToken` is
the crafted empty placeholder, never a token value — the capture redacts it anyway if
that ever changes.

## Containment

The fixture is staged **outside** the working tree and published only after every check
passed, so a failed run writes nothing into the repository. Every disposable is removed
in a `finally` block. The capture refuses to publish if the working-tree containment
digest moved, if the committed seed's sha256 moved, if any of the 17 already-committed
fixture directories changed, or if a working-tree `saves/` directory exists.

## Established vs derived vs not claimed

**Established:** everything in "The five findings", plus the argument positions, the
neutral-vector resource result, and the third argument's nil stored effect.

**Derived-provisional:** the interchangeability conclusion, and the seed choice.

**Not claimed:** any award schedule, unit level, threshold, or per-unit experience
source; that these amounts are what a player earns (they are what a **client sent**);
any resource movement; any server-authoritative validation. There is **no pixel
parity** and **no windowed capture** — nothing here is rendered. There is no
committed per-unit level schedule anywhere in the package, the `levels` curve is a
*player* curve, and both its helper functions are dead in the legacy source.