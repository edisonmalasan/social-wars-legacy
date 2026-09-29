# Executed-legacy placement fixture (`godot-building-placement`)

The executed-legacy parity oracle for the Compatibility API v0 placement
endpoint: one real `buy` transaction captured from the real legacy Flask
server (design D9 of the `building-placement` OpenSpec change). No Flash,
browser, Ruffle, ActionScript, or external network was involved — only the
legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_placement_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot, discards the copy, and only then publishes this
directory. The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot capture):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or the executed transaction did not match the
      derived envelope
6     Containment violation (working-tree bytes changed, or the disposable
      corpus saves changed during server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-placement/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + derivations, steps,
│                                  containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_buy/              POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the placement
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because placement parity
compares *state changes*, unlike boot parity which compared responses.

## The transaction

Intent (constants in `capture_placement_fixture.py`, verified against the
committed fresh save):

- **Item**: House I, item id `1` — `costs={"w":30}`, 2×2, `min_level 1`,
  `in_store 1`, `clicks_to_build 1` (so the persisted `attr` is `{"nc":0}`).
- **Anchor**: `(51,39)`, orientation `0` — the documented rule is
  *Manhattan-nearest free 2×2 anchor to the Command Center (item id 26)
  anchor `(51,41)`, ties broken row-major (smallest y, then smallest x)*;
  the only free distance-2 candidates are `(49,41)` and `(51,39)`, so the
  rule selects `(51,39)`. Bounds are anchor-based `0..99`
  (`GRID_EXTENT=100`); footprints may extend past the edge exactly as the
  fresh save's Harbour (anchor `(99,92)`, width 10) already does.

Derived envelope (all values **derived-provisional**: the Flash client is
never executed, so its exact envelope is unobservable — design D4):

```json
{"accessToken":"", "commands":[[0,"buy",[41,1,51,39,1,0,0,""],[0,0,0,-30,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

- slot `41` = smallest positive integer absent from `maps[0].items`
  (fresh save occupies `1..40`), team `1`, `unknown=0`, `reason=""`.
- `resources_changed` = negated config `costs` on the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`.
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.

Executed outcome (as recorded, verified by the tool before publishing):

- response `{"result":"success"}`;
- `maps[0].items["41"] = [1, 51, 39, <wall clock>, 0, [], {"nc":0}, 1]`
  (field order: item, x, y, timestamp, orientation, store, attr, player);
- `wood` 2000 → 1970 (exactly the derived −30 under the legacy
  `max(…, 0)` clamp), gold/oil/steel/xp/cash unchanged;
- `privateState.boughtUnits` `[]` → `[1]` (legacy `buy` records the bought
  item id for player team 1).

## Sanitization (design D9)

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too). The live requests always sent the real values — only the
records are redacted. Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

Re-running the capture exits 0 and reproduces every file byte-identically
**except** these documented time-dependent fields (structural diff of two
consecutive runs, 2026-09-28):

- `captured_at_utc` in every `request.json` / `response.meta.json`, and
  `executed_at_utc` in `capture-manifest.json`;
- the HTTP `Date` response header (both steps);
- the envelope `ts` inside `command_buy/request.json`'s `data` field, and
  therefore that field's sha256 digest;
- the placement entry's wall-clock `timestamp` in
  `command_buy/after.json`, and therefore the manifest's
  `transaction/steps[1].save_after_sha256`.

Everything else — save states, response bodies, the envelope's commands,
slot, and resource vector — is byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
The only working-tree writes are the files in this directory; the
disposable copy is removed before exit; no working-tree save is ever
written; the boot fixtures under `tests/fixtures/godot-compatibility-boot/`
are untouched (this tool shares the boot capture's harness but has its own
output directory).

## Tests and claim limits

Offline unit tests for the shared derivation and sanitization:
`python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
(`test_placement_envelope.py`; the placement parity suite consumes this
fixture).

Claim limits: parity covers this **one recorded `buy` transaction against
the fresh-player corpus** for the derived envelope — not progressed
players, not other commands; the price vector, envelope placeholders,
slot choice, and the Flash client's exact placement rules are derived,
never observed; insufficient resources reproduce legacy clamping
(`max(…, 0)`), never rejection (server-side validation belongs to
Server v1 / M13); no pixel-parity oracle against the legacy client
exists.
