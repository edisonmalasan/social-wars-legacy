# Executed-legacy move fixture (`godot-building-move`)

The executed-legacy parity oracle for the Compatibility API v0 move
endpoint: one real `move` transaction captured from the real
legacy Flask server (design D9 of the `building-move` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_move_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase fixture
digests, discards the copy, and only then publishes this directory. The
opt-in legacy command recorder env var (`SOCIALWARS_COMMAND_RECORD_DIR`)
is stripped from the child.

Exit codes (identical meanings to the boot, placement, and purchase
captures):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or the executed transaction did not match the
      derived envelope
6     Containment violation (working-tree bytes changed, the committed
      boot/placement/purchase fixtures changed, or the disposable corpus
      saves changed during server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-move/
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
    └── command_move/             POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the move applied
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because move parity
compares *state changes*.

## The transaction

Intent (constants in `capture_move_fixture.py`, verified against the
committed config and fresh save):

- **Placement**: the Turret I, item id `22` — 1×1, `type "b"`,
  `costs {"s":125}` (its *purchase* price) — at legacy map key `"11"`,
  anchored at `(58,48)` (`[22, 58, 48, 0, 0, [], {}, 1]` in the fresh
  save).
- **Target**: `(58,47)`.
- **Target rule**: the Manhattan-nearest free one-step neighbour of the
  anchor, ties broken row-major (smallest `y`, then smallest `x`) — the
  *same documented rule* the placement capture used for its anchor. Of the
  four one-step neighbours, `(59,48)` (slot 9) and `(58,49)` (slot 7) hold
  Wall I rows, so the free candidates are `(57,48)` and `(58,47)`; the
  row-major tiebreak prefers the smaller `y`, so the rule selects
  `(58,47)`.
- **Contract**: one intent only — a save id, the legacy map index, and the
  target cell. No price, no resource deltas, and no `frame`/`string` are
  sent by the client; the envelope is derived server-side (below).

Derived envelope (all values **derived-provisional**: the Flash client is
never executed, so the command a real drag sends, its exact argument
values, its `frame`/`string` arguments, and any price it sends are
unobservable — design D1/D2/D6):

```json
{"accessToken":"", "commands":[[0,"move",[11,58,47,0,""],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

- `move` takes exactly five positional args — `item_index`, `x`, `y`,
  `frame`, `string` (`command.py:119-134`, and the `move` row of
  `docs/legacy-protocol/commands.md` / the `move` entry of
  `docs/legacy-protocol/commands.json`).
- `item_index` is the legacy map key as an integer: legacy resolves the row
  with `engine.map_get_item(map, index)`, i.e. `map["items"][str(index)]`
  (`engine.py:36-40`).
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the
  branch at `command.py:40`) and it is **all zeros**. The committed
  configuration records no move price anywhere: every item's `cost` is
  `"0"` and every `cost_type` is `null` (dead fields), `costs` prices the
  *purchase* only (the Turret I's `{"s":125}` buys the building; a move
  never carries it), and none of the globals mentions a move cost — so the
  neutral vector is the only derivable choice (design D2). No client-sent
  price is ever accepted.
- `frame = 0` and `string = ""` are the documented placeholders for the two
  arguments legacy reads and then discards (`command.py:123-124` binds
  them to local names and never uses them).
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.

Executed outcome (as recorded, verified by the tool before publishing):

- response `{"result":"success"}`;
- `maps[0].items["11"]` `[22, 58, 48, 0, 0, [], {}, 1]` →
  `[22, 58, 47, 0, 0, [], {}, 1]` — legacy `command.move` writes exactly
  `item[1] = x` and `item[2] = y` in place (`command.py:132-133`) and
  nothing else; the row's `timestamp`, `orientation`, `store`, `attr`, and
  `player` fields are untouched;
- every other placement row byte-identical, and the placement count is
  still `40` — a move adds, removes, and re-keys nothing;
- `maps[0].store` stays `{}` and `privateState.boughtUnits` stays `[]` — a
  move neither stores nor records a purchase;
- `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0` — all unchanged, because the
  derived vector is neutral and the legacy clamp `max(…, 0)` therefore
  never rewrites a value.

`/maps/0/items/11/2` (the `y` field) is the **only** difference between
the recorded before- and after-states, and it is not a clock reading:
legacy writes `item[1]` as well, but the derived target keeps `x = 58`, so
that index is observably identical. No wall-clock value is written at all
(`apply_resources`' timestamp write is commented out in legacy,
`engine.py:269`), so both saves are byte-stable across reruns and move
parity needs **no** time-dependent normalization on the state.

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
**except** these documented time-dependent fields (verified by a structural
diff of two consecutive runs on 2026-09-29):

- `captured_at_utc` in every `request.json` / `response.meta.json`, and
  `executed_at_utc` in `capture-manifest.json`;
- the HTTP `Date` response header (both steps);
- the envelope `ts` inside `command_move/request.json`'s `data` field, and
  therefore that field's sha256 digest.

Everything else — both save states, both response bodies, and the
envelope's single command, argument list, and neutral resource vector — is
byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the three already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/` →
`4d389707e0f18676fb23b3a2a8a47031b4e233366e4066437f8bad6854e15234`,
`tests/fixtures/godot-building-placement/` →
`546a5f00e5e45319ffd17f5ee67201dd2b72cb21de833a3e35e8a9a98d60c5a8`,
`tests/fixtures/godot-item-purchase/` →
`d05e5b92b26a1222774bb32e76a42417c692e65ee1b87abdb8a2f4e6cd84e813`) and
fails with exit 6 if any of them changed during the run. The only
working-tree writes are the files in this directory; the disposable copy
is removed before exit; no working-tree save is ever written; the service
never binds anywhere but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_move_envelope.py` for the derivation, sanitization, and capture
contract; `test_move_endpoint.py` for the `/v0/move` structural contract and
corpus-only persistence; `test_move_parity.py` consumes this fixture and
replays the recorded intent through the endpoint offline.)

Claim limits: parity covers this **one recorded `move` transaction against
the fresh-player corpus** for the derived envelope — not progressed
players, not other commands, and not a second move of a *different* row.
The chosen legacy command, its argument values, the `frame`/`string`
placeholders, and the neutral price vector are all **derived, never
observed from the Flash client**; the service therefore claims neither that
moving is free in the legacy client nor that it costs anything, and no
claim is made about the vector the Flash client actually sends. Legacy
performs **no** ownership, collision, bounds, or price check for a move
("Client repositions any indexed item; no ownership, collision, or bounds
check"), so the endpoint's validation is structural fail-closed only:
occupancy, the no-op cell, and grid bounds as a gameplay rule are
client-side display rules, and authoritative server-side validation belongs
to Server v1 / M13. An item index that names no row in the corpus is
answered with a structured `unknown_item_index` error rather than legacy's
silent early return, which would otherwise persist a save and report a
success for a move that never happened. Storage is display-only here:
moving a *stored* item, `orient` (flip), `sell`, and the other storage
commands are later deliver lines. No Flash, Ruffle, ActionScript, or browser
executes, no external network is used, and no pixel-parity oracle against
the legacy client exists.
