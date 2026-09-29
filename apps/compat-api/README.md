# Compatibility API v0 (`apps/compat-api`)

Read-only loopback bootstrap service that answers from the **unchanged legacy
modules** themselves — the Flask app imports `get_game_config`,
`get_player_info`, `sessions`, `engine`, and `version` and initializes them in
`server.py`'s order. It exists so the Godot client can obtain the session list
and one player's boot payload without Flash, without touching the working tree,
and without any persistence path.

## Contract

- Binds **only** `127.0.0.1`, port `5056` (`--port` / `COMPAT_API_PORT`
  override; there is deliberately no host option).
- Read-only: no route imports or calls `sessions.save_session`, opens no file
  for writing, and never serves from the working tree — it serves a disposable
  corpus (below).
- Everything under this directory runs with the pinned CPython 3.9.13
  interpreter and `-B` (no `__pycache__` next to preserved sources).

## Start command

From the repository root (pinned interpreter; `python` here is never the PATH
alias):

```bash
python -B apps/compat-api/run.py
```

Optional: `--corpus PATH` (or `COMPAT_CORPUS`) to use an explicit corpus,
`--keep-corpus` to keep a corpus this run created, `--port N` to move off
5056.

Exit codes: `0` clean stop (Ctrl+C / Ctrl+Break), `2` usage, environment, or
corpus/legacy initialization failure, `3` port already in use, `4` any other
server failure.

### Disposable corpus mechanics

The legacy modules resolve every path from the process working directory
(`bundle.py` uses `"."` paths), so `run.py` builds a temporary corpus under the
system temp directory (prefix `socialwars-compat-`) and `chdir`s into it
*before* the first legacy import:

- the corpus carries copies of `config/`, `mods/`, `villages/` and a `saves/`
  directory seeded from `tests/saves/fresh-player.json` (copied byte-for-byte);
- a corpus without `saves/` is refused — legacy `load_saves()` would otherwise
  create one;
- `config/main.json` must be byte-identical to the repository config, because
  the legacy configuration is read exactly once, at first import;
- the corpus this run created is deleted on exit (also on the port-busy exit
  path). `run.py` leaves the corpus directory before deleting it: the process
  was sitting inside it, and Windows refuses to remove a live working
  directory. A pre-existing `--corpus PATH` is never deleted.

## Endpoints

`GET /v0/session`

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790449969,
 "saves": [{"id": "...", "name": "Warrior", "xp": 4, "level": 1}]}
```

`saves` is the legacy `all_saves_info()` list with `userid` renamed to `id`.

`POST /v0/bootstrap` with body `{"user_id": "<save id>"}` returns the session
envelope plus:

```json
{"config": { ... legacy get_game_config() payload ... },
 "player_info": { ... legacy get_player_info() payload ... }}
```

**Documented deviation (design D3):** the bootstrap envelope also carries
`saves`. D3 lists only `config` and `player_info`; the extra key is a strict
superset of D3 and keeps the envelope uniform for the boot client (one shape,
plus the two payload keys).

`POST /v0/place` with body `{"user_id", "item_id", "x", "y", "orientation"?}`
is the one state-mutating surface of the API. The body is an **intent only**:
extra keys, including client-supplied resource deltas, are ignored. The
endpoint derives the legacy batch envelope internally — price vector from the
loaded config, smallest positive free slot, the documented placeholders — all
values **derived-provisional**, because the Flash client is never executed
(design D4 of the `building-placement` change). It then validates structurally
(fail-closed) and executes through the unchanged legacy `command()`
dispatcher in-process over the service corpus. Success returns the legacy
answer plus the authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790609721, "result": "success",
 "placement": [1, 51, 39, 1790609721, 0, [], {"nc": 0}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 1970, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `result` is the legacy string verbatim; `placement` is the persisted
  eight-field entry (`item, x, y, timestamp, orientation, store, attr,
  player`); `resources` are the authoritative current values the client
  applies verbatim (design D7). `timestamp` is the server wall clock at
  execution — the one time-dependent field, normalized in parity.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_id` present in the loaded config (`bool` excluded), and
  anchor-based `x`/`y` in `0..99` (`GRID_EXTENT=100`; footprints may extend
  past the edge exactly as legacy placements already do). Occupancy and
  affordability are gameplay rules: the client enforces them for display
  (design D5), while insufficient funds reproduce the legacy `max(…, 0)`
  clamp rather than a rejection — server-side validation belongs to
  Server v1 / M13.

`POST /v0/purchase` with body `{"user_id", "item_id"}` is the second
state-mutating surface (the `building-purchase` change). The body is an **intent
only**: extra keys, including a client-supplied `price`, `quantity`, or resource
delta, are ignored. The endpoint derives the legacy batch envelope internally —
the **cash-only** price from the item's loaded config `costs`, one
`buy_stored_item_cash` command whose single argument is the item id, and the
documented placeholders, all values **derived-provisional** (design D2 of
`building-purchase`) — then executes the unchanged legacy `command()` dispatcher
in-process over the service corpus. Success returns the legacy answer plus the
authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790649056, "result": "success",
 "store": {"105": 1},
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 0, "mana": 0}}
```

- `result` is the legacy string verbatim; `store` is the **full** post-execution
  storage mapping `{str(item_id): int}` (quantity `0` and unresolvable ids
  preserved, never filtered) so the client needs no arithmetic; `resources` are
  the authoritative current values the client applies verbatim (design D4). This
  payload carries no time-dependent field beyond `server_time`.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_id` present in the loaded config, and a **cash-only** config
  price. An item priced in another resource (or mixed, or unpriced) fails closed
  with `costs_not_cash` — a derivation boundary for this command, not a gameplay
  rule: the client never offers such an entry, and any-price storage acquisition
  is the separate `store_add_items` grant path this change does not cover. The
  level gate and cash affordability are gameplay rules the client enforces
  (design D5), while insufficient cash reproduces the legacy `max(…, 0)` clamp
  rather than a rejection.

`POST /v0/move` with body `{"user_id", "item_index", "x", "y"}` is the third
state-mutating surface (the `building-move` change). The body is an **intent
only**: extra keys, including a client-supplied price, `resources_changed`, or
the arguments legacy discards (`frame`, `string`), are ignored. The endpoint
resolves `item_index` against the save's own `map["items"]` **before** executing
— legacy's missing-item path is a silent early return that still persists, so
reporting it as success would claim a change that never happened — then derives
the legacy batch envelope internally (one `move` command whose arguments are
`[item_index, x, y, frame, string]`, the `frame`/`string` placeholders legacy
discards, and a **neutral** resource vector, design D2 of `building-move`) and
executes the unchanged legacy `command()` dispatcher in-process over the service
corpus. Success returns the legacy answer plus the same authoritative superset
shape as `/v0/place`:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790657765, "result": "success",
 "placement": [22, 58, 47, 0, 0, [], {}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `placement` is the persisted eight-field row **re-read from the save after
  execution** (`item, x, y, timestamp, orientation, store, attr, player`), so
  the client reuses the placement result type; `resources` are the authoritative
  current values. A move derives a neutral vector because the committed config
  records no move price, so a real move never changes resources.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_index` present in the save, and anchor-based `x`/`y` in
  `0..99`. Grid bounds, footprint occupancy (with the moving building's own
  cells excluded), and refusing a no-op move are gameplay rules the client
  enforces (design D5); there is no server-authoritative validation.

`POST /v0/sell` with body `{"user_id", "item_index"}` is the fourth
state-mutating surface (the `building-sell` change). The body is an **intent
only**: extra keys - including a `reason`, a price, a refund, or a resource
delta - are ignored, so the legacy combat reason that would route a row through
the resurrectable-unit path is unreachable through this endpoint. The endpoint
resolves `item_index` against the save's own `map["items"]` and reads that row
**before** executing (legacy's missing-item path is a silent early return that
still persists, so accepting it would claim a removal that never happened), then
derives the legacy batch envelope internally (one `sell` command with arguments
`[item_index, reason]`, the reason **derived** as the empty string legacy
compares against `"KILL"` and otherwise uses as a log label, and a **neutral**
resource vector, design D2 of `building-sell`) and executes the unchanged legacy
`command()` dispatcher in-process over the service corpus. Success returns the
legacy answer plus an authoritative superset naming the removal:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790665230, "result": "success",
 "removed": [22, 41, 48, 0, 0, [], {}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `removed` is the eight-field row **as read before execution** (`item, x, y,
  timestamp, orientation, store, attr, player`), so the client can match exactly
  what disappeared; the service separately proves the key is absent from the
  persisted save after execution and fails closed otherwise. `resources` are the
  authoritative current values.
- **No refund is claimed.** The derived vector is neutral because the committed
  configuration records no building-sale refund rule (item `cost`/`cost_type`
  are dead fields, `costs` prices the purchase only, and
  `MARKET_SELL_PERCENTAGE` governs the resource market), the legacy refund
  travels only in client-sent deltas this contract refuses, and refund economics
  belong to Server v1 (M13) and the later *resources* line. A sale therefore
  removes the building and changes no balance.
- Validation is structural only: a JSON object body, a resolvable save id, and a
  strict-int `item_index` present in the save. Sellability and addressability are
  client-side rules (design D6); no server-authoritative validation exists.

`POST /v0/store` with body `{"user_id", "item_index"}` is the fifth
state-mutating surface (the `building-store` change). The body is an **intent
only**: extra keys - including a price, a quantity, or a resource delta - are
ignored. The endpoint resolves `item_index` against the save's own
`map["items"]` and reads that row **before** executing (legacy's missing-item
path is a silent early return that still persists), then derives the legacy
batch envelope internally (one `store_item` command whose single argument is
the item index, and a **neutral** resource vector, design D2 of
`building-store`) and executes the unchanged legacy `command()` dispatcher
in-process over the service corpus. Success returns the legacy answer plus a
two-sided authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790670611, "result": "success",
 "removed": [905, 53, 39, 0, 0, [], {}, 1],
 "store": {"905": 1},
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `removed` is the eight-field row **as read before execution** (the same
  record the sell line established); `store` is the **full** post-execution
  storage mapping, exactly what the purchase response carries, so the client
  needs no arithmetic for pre-existing contents; `resources` are the
  authoritative current values.
- The service proves both halves after execution: the popped key is absent
  from the map and the storage entry is present, failing closed with
  `internal_error` otherwise.
- **No storing cost and no capacity rule are claimed.** The derived vector is
  neutral because the committed configuration records no price for storing
  (item `cost`/`cost_type` are dead fields, `costs` prices the purchase only)
  and the catalog records that the legacy server has no capacity check; the
  refund-style economics belong to Server v1 (M13) and the later *resources*
  line.
- Unlike `buy`, `place_stored_item`, and `buy_stored_item_cash`, the
  `store_item` branch does **not** write `boughtUnits`; the endpoint reproduces
  that exactly rather than "fixing" it.
- Validation is structural only: a JSON object body, a resolvable save id, and
  a strict-int `item_index` present in the save. Storability and addressability
  are client-side rules (design D5); no server-authoritative validation exists.

### Structured errors

Always JSON, always `ok:false`, keys exactly
`{protocol, ok, error}` with `error: {code, message}` — never a partial payload:

| code | HTTP | when |
| --- | --- | --- |
| `invalid_payload` | 400 | body missing, not JSON, or not a JSON object |
| `missing_user_id` | 400 | `user_id` absent, null, or empty/whitespace |
| `invalid_user_id` | 400 | `user_id` present but not a string |
| `unknown_user_id` | 404 | well-formed id that names no save |
| `missing_item_id` | 400 | `/v0/place` or `/v0/purchase` body carries no `item_id` |
| `invalid_item_id` | 400 | `item_id` present but not an integer (`bool` excluded) |
| `unknown_item_id` | 404 | integer id absent from the loaded config |
| `invalid_coordinates` | 400 | `x`/`y` missing, not integers, or outside `0..99` |
| `invalid_orientation` | 400 | `orientation` present but not an integer |
| `costs_not_cash` | 400 | `/v0/purchase` item's config `costs` is not exactly a cash price (absent, empty, another resource, or mixed) |
| `missing_item_index` | 400 | `/v0/move` body carries no `item_index` |
| `invalid_item_index` | 400 | `item_index` present but not an integer (`bool` excluded) |
| `unknown_item_index` | 404 | integer index that names no placement in the save's `map["items"]` (legacy would silently no-op) |
| `invalid_reason` | 400 | server-side only: the derived sell reason is not a string (unreachable through the contract) |
| `bad_request` | 400 | other malformed requests Flask rejects |
| `not_found` | 404 | unknown path |
| `method_not_allowed` | 405 | known path, unsupported method |
| `internal_error` | 500 | unhandled server failure, including legacy execution raising after validation passed |

## Commands actually executed

All run from the repository root on Windows x64 with the pinned interpreter
(CPython 3.9.13); exit codes are the real observed ones (bootstrap-era
counts 2026-09-27; placement-, purchase-, move-, sell-, and store-era counts
2026-09-29):

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

→ `Ran 390 tests ... OK`, exit `0` (90 before `building-purchase`, 157 before
`building-move`, 227 before `building-sell`, 306 before `building-store`).
Covers envelope/error shapes, bootstrap and
session parity against the committed fixtures, pre/post save SHA-256 identity,
the no-persistence source guard, and the offline socket guard (the suite opens
no socket and starts no server) — plus, since the `building-placement` change,
the placement envelope derivation and sanitization (`test_placement_envelope`),
the `/v0/place` structural contract and corpus-only persistence
(`test_place_endpoint`), and the executed-legacy placement parity replay of
the committed `buy` fixture (`test_place_parity`) — and, since the
`building-purchase` change, the cash-only purchase envelope derivation
(`test_purchase_envelope`), the `/v0/purchase` structural contract, the
clamp-at-zero path, and corpus-only persistence (`test_purchase_endpoint`),
plus the executed-legacy purchase parity replay of the committed
`buy_stored_item_cash` fixture (`test_purchase_parity`).

```bash
python -B apps/compat-api/tests/smoke_loopback.py
```

→ 24 checks, `SMOKE RESULT: PASS`, exit `0`. Starts the real service on
`127.0.0.1:5056`, exercises both endpoints and the 400/404/404-error paths
over real HTTP, asserts the port-busy exit (`3`) plus that instance's corpus
cleanup, then stops the server (exit `0`) and asserts the disposable corpus was
removed and the working tree still has no `saves/`. Opt-in only — discovery
matches `test_*.py`, so this file never runs inside the unit suite, and it
needs port 5056 to be free.

```bash
python -B apps/compat-api/guard_baseline.py verify
```

→ `guard-baseline: OK - 6 group(s), combined 6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348`,
exit `0`. Verifies the pre-change SHA-256 guard set (legacy sources, `config/`,
both conversion packages, three registry manifests, committed M4 evidence,
on-disk saves) against `tests/fixtures/godot-compatibility-boot/guard-baseline.json`.
Guard digests are line-ending invariant (`guard-baseline-v2`): text files
(valid UTF-8 without NUL) are hashed after CRLF → LF normalization, all other
files as exact bytes — so a `core.autocrlf=true` checkout form and the
`report.json` producer's LF output never change a digest of unchanged content.

Fixture capture (task 1.1/1.2 evidence, one-shot) — see
`tests/fixtures/godot-compatibility-boot/README.md` for its invocation, exit
code `0`, and containment record:

```bash
python -B apps/compat-api/capture_legacy_fixtures.py
```

Placement fixture capture (the `building-placement` change's executed-legacy
oracle, one-shot) — see `tests/fixtures/godot-building-placement/README.md`
for its invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_placement_fixture.py
```

Purchase fixture capture (the `building-purchase` change's executed-legacy
oracle, one-shot) — see `tests/fixtures/godot-item-purchase/README.md`
for its invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_purchase_fixture.py
```

Move fixture capture (the `building-move` change's executed-legacy oracle,
one-shot) — see `tests/fixtures/godot-building-move/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_move_fixture.py
```

Sell fixture capture (the `building-sell` change's executed-legacy oracle,
one-shot) - see `tests/fixtures/godot-building-sell/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_sell_fixture.py
```

Store fixture capture (the `building-store` change's executed-legacy oracle,
one-shot) - see `tests/fixtures/godot-building-store/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_store_fixture.py
```

## Layout

- `compat_legacy.py` — corpus build/layout checks and the in-process adapter
  over the legacy modules (`initialize()` mirrors `server.py`'s import and
  `load_saves` / `load_static_villages` / `load_quests` order).
- `compat_service.py` — Flask app, envelopes, and the error table; owns
  `PROTOCOL`, `HOST`, `DEFAULT_PORT`.
- `placement_envelope.py` — the derived-provisional `/v0/place` envelope
  (slot choice, price vector, documented placeholders) and sanitizers.
- `purchase_envelope.py` — the derived-provisional `/v0/purchase` envelope
  (cash-only price vector, one `buy_stored_item_cash` command, the documented
  placeholders), reusing the placement module's shared helpers unchanged.
- `run.py` — documented start command (corpus lifecycle, exit codes).
- `guard_baseline.py` — generate/verify the SHA-256 guard set.
- `field_stability.py` — derive the field-stability record from two captures.
- `capture_legacy_fixtures.py` — executed-legacy boot fixture capture.
- `capture_placement_fixture.py` — executed-legacy placement fixture capture.
- `capture_purchase_fixture.py` - executed-legacy purchase fixture capture.
- `move_envelope.py` - the derived-provisional `/v0/move` envelope (argument
  list, neutral resource vector, the `frame`/`string` placeholders legacy
  discards), reusing the placement module's shared helpers unchanged.
- `sell_envelope.py` - the derived-provisional `/v0/sell` envelope (argument
  list, neutral resource vector, derived reason), reusing the placement
  module's shared helpers unchanged.
- `capture_move_fixture.py` - executed-legacy move fixture capture.
- `capture_sell_fixture.py` - executed-legacy sell fixture capture.
- `store_envelope.py` - the derived-provisional `/v0/store` envelope (single
  argument, neutral resource vector).
- `capture_store_fixture.py` - executed-legacy store fixture capture.
- `tests/` — `test_compat_v0.py` (service + containment), `test_parity.py`
  (offline replay against the committed boot fixtures),
  `test_placement_envelope.py` (offline envelope derivation/sanitization),
  `test_place_endpoint.py` (structural contract + corpus-only persistence),
  `test_place_parity.py` (offline placement replay against the executed
  fixture), `test_purchase_envelope.py` (offline cash-only purchase
  derivation), `test_purchase_endpoint.py` (structural contract, clamp,
  corpus-only persistence), `test_purchase_parity.py` (offline purchase replay
  against the executed fixture), `test_move_envelope.py` (offline move envelope
  derivation: argument list, neutral vector, discarded placeholders, grid
  bounds), `test_move_endpoint.py` (structural contract, unknown-index
  fail-closed, neutral resources, corpus-only persistence),
  `test_move_parity.py` (offline move replay against the executed fixture),
  `test_sell_envelope.py` (offline sell envelope derivation: argument list,
  neutral vector, derived reason), `test_sell_endpoint.py` (structural
  contract, post-execution removal proof, unknown-index fail-closed, no client
  reason), `test_sell_parity.py` (offline sell replay against the executed
  fixture),
  `compat_test_harness.py`,
  `smoke_loopback.py` (opt-in loopback smoke).

## Claim limits

This service establishes **bootstrap parity for the fresh-save corpus**:
session list, game version, config, and player-info payloads equal to the
committed executed-legacy fixtures for stable fields and under the documented
normalizations for time-dependent fields. Since the `building-placement`
change it also establishes **placement parity for one recorded `buy`
transaction**: `POST /v0/place` replayed against the executed-legacy
placement fixture equals its response and after-state for every stable field
(the envelope `ts` and the placement entry's wall-clock `timestamp` are the
documented time-dependent fields). Since the `building-purchase` change it
additionally establishes **purchase parity for one recorded
`buy_stored_item_cash` transaction**: `POST /v0/purchase` replayed against the
executed-legacy purchase fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields). Since the `building-move` change it establishes **move
parity for one recorded `move` transaction**: `POST /v0/move` replayed against
the executed-legacy move fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields). Since the `building-sell` change it establishes **sell
parity for one recorded `sell` transaction**: `POST /v0/sell` replayed against
the executed-legacy sell fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields).

It does **not** establish authentication security, progressed-player coverage,
or parity for any other command. The price vector, envelope placeholders, and
slot choice are derived-provisional — never observed from the Flash client; the
same holds for the **choice of `buy_stored_item_cash` as the purchase command**
and for the **cash-only price derivation**, which also means the service claims
nothing about whether a resource-priced storage purchase exists in the legacy
client, and for the **move command's argument values**, the **arguments legacy
discards** (`frame`, `string`), and the **neutral move price vector** — the
service therefore claims neither that moving is free in the legacy client nor
that it costs anything. The **sell reason** is derived the same way (the empty
string, which legacy compares against `"KILL"` and otherwise uses as a log
label) and the **sell price vector** is neutral for the same reason the move
one is, so the change **claims no refund at all**: the committed configuration
records no building-sale refund rule and the legacy refund travels only in
client-sent deltas this contract refuses. Insufficient resources reproduce the
legacy `max(…, 0)` clamp, never a rejection (authoritative server-side validation
belongs to Server v1 / M13), and occupancy, grid-bounds, level-gate,
cash-affordability, no-op-move, sellability, storability, and addressability
rules are enforced client-side only. Persistence is confined to the disposable service
corpus: `POST /v0/place`, `POST /v0/purchase`, `POST /v0/move`,
`POST /v0/sell`, and `POST /v0/store` persist through the legacy dispatcher into
the corpus `saves/`,
while the session and bootstrap endpoints remain strictly non-persisting, and
the working tree is never written.
