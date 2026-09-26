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

### Structured errors

Always JSON, always `ok:false`, keys exactly
`{protocol, ok, error}` with `error: {code, message}` — never a partial payload:

| code | HTTP | when |
| --- | --- | --- |
| `invalid_payload` | 400 | body missing, not JSON, or not a JSON object |
| `missing_user_id` | 400 | `user_id` absent, null, or empty/whitespace |
| `invalid_user_id` | 400 | `user_id` present but not a string |
| `unknown_user_id` | 404 | well-formed id that names no save |
| `bad_request` | 400 | other malformed requests Flask rejects |
| `not_found` | 404 | unknown path |
| `method_not_allowed` | 405 | known path, unsupported method |
| `internal_error` | 500 | unhandled server failure |

## Commands actually executed

All run from the repository root on Windows x64 with the pinned interpreter
(CPython 3.9.13); exit codes are the real observed ones (2026-09-27):

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

→ `Ran 31 tests ... OK`, exit `0`. Covers envelope/error shapes, bootstrap and
session parity against the committed fixtures, pre/post save SHA-256 identity,
the no-persistence source guard, and the offline socket guard (the suite opens
no socket and starts no server).

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

→ `guard-baseline: OK - 6 group(s), combined 636698690d74b0e5b802e7ca7cf93fd693c87d2c28e69f9c0776d74df167d085`,
exit `0`. Verifies the pre-change SHA-256 guard set (legacy sources, `config/`,
both conversion packages, three registry manifests, committed M4 evidence,
on-disk saves) against `tests/fixtures/godot-compatibility-boot/guard-baseline.json`.

Fixture capture (task 1.1/1.2 evidence, one-shot) — see
`tests/fixtures/godot-compatibility-boot/README.md` for its invocation, exit
code `0`, and containment record:

```bash
python -B apps/compat-api/capture_legacy_fixtures.py
```

## Layout

- `compat_legacy.py` — corpus build/layout checks and the in-process adapter
  over the legacy modules (`initialize()` mirrors `server.py`'s import and
  `load_saves` / `load_static_villages` / `load_quests` order).
- `compat_service.py` — Flask app, envelope, and the error table; owns
  `PROTOCOL`, `HOST`, `DEFAULT_PORT`.
- `run.py` — documented start command (corpus lifecycle, exit codes).
- `guard_baseline.py` — generate/verify the SHA-256 guard set.
- `field_stability.py` — derive the field-stability record from two captures.
- `capture_legacy_fixtures.py` — executed-legacy fixture capture.
- `tests/` — `test_compat_v0.py` (service + containment), `test_parity.py`
  (offline replay against the committed fixtures), `compat_test_harness.py`,
  `smoke_loopback.py` (opt-in loopback smoke).

## Claim limits

This service establishes **read-only bootstrap parity for the fresh-save
corpus**: session list, game version, config, and player-info payloads equal to
the committed executed-legacy fixtures for stable fields and under the
documented normalizations for time-dependent fields. It does **not** establish
gameplay parity, authentication security, progressed-player coverage, or any
write/persistence behavior.
