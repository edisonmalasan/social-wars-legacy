# Godot compatibility boot fixtures

Executed-legacy boot evidence for the OpenSpec change
`godot-compatibility-boot` (tasks 1.2, 1.3, 1.4). Everything here was produced
by actually running the real legacy Flask server; nothing is hand-written,
hand-edited, or derived from source reading alone.

## 1. How the fixtures were produced

| item | value |
| --- | --- |
| executable | `C:\Users\Edison\AppData\Local\Temp\opencode\cpython39\pkg\tools\python.exe` (pinned CPython 3.9.13) |
| capture command | `python -B apps/compat-api/capture_legacy_fixtures.py` |
| capture exit code | **0** (executed 2026-09-26T18:15:06+00:00, recorded in `capture-manifest.json`) |
| field-stability command | `python -B apps/compat-api/field_stability.py --capture-a tests/fixtures/godot-compatibility-boot --capture-b <transient capture B> --out tests/fixtures/godot-compatibility-boot/field-stability.json` |
| field-stability exit code | **0** |
| guard baseline command | `python -B apps/compat-api/guard_baseline.py generate` |
| guard baseline exit code | **0** (`python -B apps/compat-api/guard_baseline.py verify` also exited **0** on the captured baseline) |

`python` in those commands is the pinned interpreter above, not the PATH
`python` (which is a newer interpreter and is not the change's baseline).
There is no browser, no Flash, no Ruffle, no ActionScript, and no external
network in any of these commands.

The capture command starts `server.py` in a **disposable copy** of the legacy
runtime (system temp root, `socialwars-capture-*`), seeds it with
`saves/<pid>.save.json` copied from `tests/saves/fresh-player.json`, talks to
`127.0.0.1:5055` only, stops the server inside the run, and deletes the
disposable copy before writing fixtures. The second capture (capture B), used
only to derive `field-stability.json`, was written to a transient
`tests/fixtures/godot-compatibility-boot-capture-b/` directory inside the
working tree and **deleted after the record was derived** — only capture A is
committed.

## 2. What each fixture records

```
capture-manifest.json        executable, invocation, exit code, server command,
                             per-request status/bytes/SHA-256, containment
field-stability.json         stable vs time/environment-dependent fields with
                             the normalization for each non-stable field
guard-baseline.json          pre-change SHA-256 baseline of the guarded paths
.gitattributes               `* -text` so committed bytes stay byte-exact
steps/<step>/request.json    method, target, headers, body actually sent
steps/<step>/before.json     SHA-256 of every corpus save before the call
steps/<step>/response.body   response bytes exactly as served
steps/<step>/response.meta.json  status + headers + SHA-256 + byte count
steps/<step>/after.json      SHA-256 of every corpus save after the call
steps/login_page/save-list.json  save-list surface parsed out of the login page
```

The five executed steps, in order, with their observed statuses:

| step | request | status |
| --- | --- | --- |
| `login_page` | `GET /` | 200 |
| `login_post` | `POST /` form `USERID` + `GAMEVERSION=Basesec_1.5.4.swf` | 302 → `/play.html` |
| `play_page` | `GET /play.html` with the session cookie | 200 |
| `get_game_config` | `GET .../get_game_config.php?USERID=...&user_key=123456789&language=en` | 200 (1,092,491 bytes) |
| `get_player_info` | `POST .../get_player_info.php` form `USERID`, `user_key`, `language` | 200 (5,492 bytes) |

`get_player_info` exercises the legacy **current-player** branch (no `user`
form field), which is the branch the v0 bootstrap uses.

## 3. Containment evidence (as executed)

* Working-tree containment snapshot (root `*.py`, `config/`, `mods/`,
  `villages/`, `templates/`, `tests/saves/`, `saves/`) is identical before the
  run and after the server stopped:
  `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`.
* `tests/saves/` digest before/after every request is identical
  (`a528533419993e919fcbf4cc5ae652e02e0c992d4c75f514a54918a0b8da6302`), and
  each step's `saves_unchanged_by_call` is `true`; the working tree has **no**
  `saves/` directory before or after (`"exists": false` in the manifest).
* The seed file `tests/saves/fresh-player.json` kept its own SHA-256
  (`25df5b5a665b5eb07a88af1ea8179f0416fa0078cfaac8dd4b8749a3762643f5`) and the
  server start did not rewrite the seeded save (`startup_preserved_seed`).
* Port 5055 was free before start and after stop; the disposable copy was
  removed before the manifest was written; `SOCIALWARS_COMMAND_RECORD_DIR` was
  stripped from the child environment.
* Only working-tree writes are the fixture files under this directory.
* `guard_baseline.py verify` re-checks the guarded paths (legacy sources,
  `config/`, both conversion packages, the three registry manifests, committed
  M4 first-render evidence, on-disk saves) and exited **0** after these runs.

## 4. Field stability (task 1.3)

`field-stability.json` was derived from two executed captures plus code
inspection of the legacy boot modules, and records for every step:

* `get_game_config` — **0** differing paths between the two captures (the
  darts `start_date` rewrap landed in the same window); the field is still
  classified time-dependent by code inspection (`get_game_config.make_dynamic`)
  and normalized **format-only**.
* `get_player_info` — exactly **2** differing paths, both documented
  normalizations: `timestamp` (positive epoch) and `playerInfo.last_logged_in`
  (equal to the same response's `timestamp`).
* `play_page` — equal after masking the `serverTime=<digits>` FlashVar.
* `login_page` — parsed save-list equal *and* raw body equal; `login_post` —
  equal status and `Location`.
* `neighbors` — environment-dependent (`os.listdir` order), compared as a
  pid-keyed mapping.

## 5. Claim limits

This directory establishes that the legacy server was executed and what it
returned for **one fresh save on this machine at this time**. It does not
establish gameplay parity, progressed-player coverage, authentication
security, rendering correctness, or Godot loading. Response bytes are
observations of a running legacy server, not an authored specification;
`response.meta.json` headers (Date/Server) are capture-time metadata and are
never compared. The guard baseline is over worktree bytes under this
checkout's `core.autocrlf=true` configuration.
