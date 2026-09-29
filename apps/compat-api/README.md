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

### Structured errors

Always JSON, always `ok:false`, keys exactly
`{protocol, ok, error}` with `error: {code, message}` — never a partial payload:

| code | HTTP | when |
| --- | --- | --- |
| `invalid_payload` | 400 | body missing, not JSON, or not a JSON object |
| `missing_user_id` | 400 | `user_id` absent, null, or empty/whitespace |
| `invalid_user_id` | 400 | `user_id` present but not a string |
| `unknown_user_id` | 404 | well-formed id that names no save |
| `missing_item_id` | 400 | `/v0/place` body carries no `item_id` |
| `invalid_item_id` | 400 | `item_id` present but not an integer (`bool` excluded) |
| `unknown_item_id` | 404 | integer id absent from the loaded config |
| `invalid_coordinates` | 400 | `x`/`y` missing, not integers, or outside `0..99` |
| `invalid_orientation` | 400 | `orientation` present but not an integer |
| `bad_request` | 400 | other malformed requests Flask rejects |
| `not_found` | 404 | unknown path |
| `method_not_allowed` | 405 | known path, unsupported method |
| `internal_error` | 500 | unhandled server failure, including legacy execution raising after validation passed |

## Commands actually executed

All run from the repository root on Windows x64 with the pinned interpreter
(CPython 3.9.13); exit codes are the real observed ones (bootstrap-era
counts 2026-09-27; placement-era counts 2026-09-29):

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

→ `Ran 90 tests ... OK`, exit `0`. Covers envelope/error shapes, bootstrap and
session parity against the committed fixtures, pre/post save SHA-256 identity,
the no-persistence source guard, and the offline socket guard (the suite opens
no socket and starts no server) — plus, since the `building-placement` change,
the placement envelope derivation and sanitization (`test_placement_envelope`),
the `/v0/place` structural contract and corpus-only persistence
(`test_place_endpoint`), and the executed-legacy placement parity replay of
the committed `buy` fixture (`test_place_parity`).

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

## Layout

- `compat_legacy.py` — corpus build/layout checks and the in-process adapter
  over the legacy modules (`initialize()` mirrors `server.py`'s import and
  `load_saves` / `load_static_villages` / `load_quests` order).
- `compat_service.py` — Flask app, envelopes, and the error table; owns
  `PROTOCOL`, `HOST`, `DEFAULT_PORT`.
- `placement_envelope.py` — the derived-provisional `/v0/place` envelope
  (slot choice, price vector, documented placeholders) and sanitizers.
- `run.py` — documented start command (corpus lifecycle, exit codes).
- `guard_baseline.py` — generate/verify the SHA-256 guard set.
- `field_stability.py` — derive the field-stability record from two captures.
- `capture_legacy_fixtures.py` — executed-legacy boot fixture capture.
- `capture_placement_fixture.py` — executed-legacy placement fixture capture.
- `tests/` — `test_compat_v0.py` (service + containment), `test_parity.py`
  (offline replay against the committed boot fixtures),
  `test_placement_envelope.py` (offline envelope derivation/sanitization),
  `test_place_endpoint.py` (structural contract + corpus-only persistence),
  `test_place_parity.py` (offline placement replay against the executed
  fixture), `compat_test_harness.py`, `smoke_loopback.py` (opt-in loopback
  smoke).

## Claim limits

This service establishes **bootstrap parity for the fresh-save corpus**:
session list, game version, config, and player-info payloads equal to the
committed executed-legacy fixtures for stable fields and under the documented
normalizations for time-dependent fields. Since the `building-placement`
change it also establishes **placement parity for one recorded `buy`
transaction**: `POST /v0/place` replayed against the executed-legacy
placement fixture equals its response and after-state for every stable field
(the envelope `ts` and the placement entry's wall-clock `timestamp` are the
documented time-dependent fields).

It does **not** establish authentication security, progressed-player coverage,
or parity for any other command. The price vector, envelope placeholders, and
slot choice are derived-provisional — never observed from the Flash client.
Insufficient resources reproduce the legacy `max(…, 0)` clamp, never a
rejection (authoritative server-side validation belongs to Server v1 / M13),
and occupancy and grid-bounds rules are enforced client-side only.
Persistence is confined to the disposable service corpus: `POST /v0/place`
persists through the legacy dispatcher into the corpus `saves/`, while the
session and bootstrap endpoints remain strictly non-persisting, and the
working tree is never written.
