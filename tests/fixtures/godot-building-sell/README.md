# Executed-legacy sell fixture (`godot-building-sell`)

The executed-legacy parity oracle for the Compatibility API v0 sell
endpoint: one real `sell` transaction captured from the real
legacy Flask server (design D10 of the `building-sell` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_sell_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move
fixture digests, discards the copy, and only then publishes this directory.
The opt-in legacy command recorder env var (`SOCIALWARS_COMMAND_RECORD_DIR`)
is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, and move
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
      boot/placement/purchase/move fixtures changed, or the disposable
      corpus saves changed during server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-sell/
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
    └── command_sell/             POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the row removed
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because sell parity
compares *state changes*.

## The transaction

Intent (constants in `capture_sell_fixture.py`, verified against the
committed config and fresh save):

- **Placement**: the Turret I, item id `22` — 1×1, `type "b"`,
  `costs {"s":125}` (its *purchase* price) — at legacy map key `"20"`,
  anchored at `(41,48)` (`[22, 41, 48, 0, 0, [], {}, 1]` in the fresh
  save).
- **Target rule**: none — a sell has no target cell and no grid input.
  Slot `20` is the **second** Turret I in map-slot order (the first is the
  move fixture's slot `11`), chosen so this fixture's target differs from
  the move fixture's and the two stay independently readable.
- **Contract**: one intent only — a save id and the legacy map index. No
  reason, no refund, no price, and no resource deltas are sent by the
  client; the envelope is derived server-side (below).

Derived envelope (all values **derived-provisional**: the Flash client is
never executed, so the command a real sale sends, its exact argument
values, its reason, and any refund it sends are unobservable — design
D1/D2/D3/D7):

```json
{"accessToken":"", "commands":[[0,"sell",[20,""],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

- `sell` takes exactly two positional args — `item_index` and `reason`
  (`command.py:149-168`, and the `sell` row of
  `docs/legacy-protocol/commands.md` / the `sell` entry of
  `docs/legacy-protocol/commands.json`).
- `item_index` is the legacy map key as an integer: legacy resolves the row
  with `engine.map_get_item(map, index)`, i.e. `map["items"][str(index)]`
  (`engine.py:36-40`), and deletes it with `engine.map_delete_item`
  (`engine.py:48-52`).
- `reason = ""` is **derived, never chosen** (design D3). The branch
  compares the reason against `"KILL"` and otherwise uses it only as a log
  label, so the empty string is behaviorally inert. The static SWF
  inventory shows only combat/system reasons (`SELL_REASON_KILL`,
  `SELL_REASON_BULLDOZE`, `SELL_REASON_UPGRADE`, `SELL_REASON_TREASURE`,
  `SELL_REASON_ACTIVATOR`, …) and no reason specific to a player-initiated
  sale, so the value the Flash client actually sends is unobserved and this
  change claims nothing about it. The endpoint accepts **no** reason from
  the client, so no client can claim `"KILL"` and reach `push_dead_unit`
  and the resurrectable-unit path — that combat path is a later milestone.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the
  branch at `command.py:40`) and it is **all zeros** (design D2). The
  committed configuration records no building-sale refund rule anywhere:
  every item's `cost` is `"0"` and every `cost_type` is `null` (dead
  fields), `costs` prices the *purchase* only (the Turret I's `{"s":125}`
  buys the building; a sell never carries it), the only sell-named global is
  `MARKET_SELL_PERCENTAGE` (0.75), which sits next to
  `MARKET_BASE_COSTS` and `MARKET_AMOUNT_TRADE` and governs the *resource*
  market ("SELL 100 WOOD ON MARKET") rather than building sales, and no
  other global mentions a refund. The catalog records that **the refund
  travels entirely through the client-sent deltas** — the server computes
  no price — and this contract refuses those. **This change therefore
  claims no refund at all**: the neutral vector is a derivation boundary,
  not a claim that selling is free in the legacy client.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.

Executed outcome (as recorded, verified by the tool before publishing):

- response `{"result":"success"}`;
- `maps[0].items["20"]` — `[22, 41, 48, 0, 0, [], {}, 1]` — is **absent**
  afterwards. Legacy `command.sell` deletes exactly that key with
  `engine.map_delete_item` (`command.py:162`, `engine.py:48-52`) and writes
  nothing else; no other row, field, or count moves;
- every other placement row byte-identical, and the placement count drops
  `40` → `39` — a sell removes exactly the row the client named and
  re-keys nothing;
- `maps[0].store` stays `{}` and `privateState.boughtUnits` stays `[]` — a
  sell neither stores nor records a purchase;
- the **whole** `privateState` — including `deadHeroes` (`{}`) — is
  byte-identical, because the derived reason is not `"KILL"` and so
  `push_dead_unit` never runs;
- `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0` — all unchanged, because the
  derived vector is neutral and the legacy clamp `max(…, 0)` therefore
  never rewrites a value.

`/maps/0/items/20` is the **only** difference between the recorded
before- and after-states, and it is a removed key, not a clock reading:
`command.sell` writes nothing at all, and `apply_resources`' timestamp
write is commented out in legacy (`engine.py:269`). No wall-clock value is
written, so both saves are byte-stable across reruns and sell parity needs
**no** time-dependent normalization on the state.

## Sanitization (design D10)

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
- the envelope `ts` inside `command_sell/request.json`'s `data` field, and
  therefore that field's sha256 digest.

Everything else — both save states, both response bodies, and the
envelope's single command, argument list, derived reason, and neutral
resource vector — is byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the four already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/` →
`4d389707e0f18676fb23b3a2a8a47031b4e233366e4066437f8bad6854e15234`,
`tests/fixtures/godot-building-placement/` →
`546a5f00e5e45319ffd17f5ee67201dd2b72cb21de833a3e35e8a9a98d60c5a8`,
`tests/fixtures/godot-item-purchase/` →
`d05e5b92b26a1222774bb32e76a42417c692e65ee1b87abdb8a2f4e6cd84e813`,
`tests/fixtures/godot-building-move/` →
`b3c477a7947fbe409330f03a8658cdca707a2631b52d1d4c5127f440619799c1`) and
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

(`test_sell_envelope.py` for the derivation, sanitization, and capture
contract; `test_sell_endpoint.py` for the `/v0/sell` structural contract and
corpus-only persistence; `test_sell_parity.py` consumes this fixture and
replays the recorded intent through the endpoint offline.)

Claim limits: parity covers this **one recorded `sell` transaction against
the fresh-player corpus** for the derived envelope — not progressed
players, not other commands, and not a second sell of a *different* row.
The chosen legacy command, its argument values, the derived reason, and the
neutral price vector are all **derived, never observed from the Flash
client**. **No refund is claimed**: the committed configuration records no
building-sale refund rule, the legacy refund travels in client-sent deltas
this contract refuses, and the player's own `Sell for #0#` UI template
means the Flash client computes a refund the repository never records. The
combat `KILL` reason — and with it the `push_dead_unit` resurrectable-unit
path in `privateState.deadHeroes` — is **never reached**, because the
endpoint accepts no reason from the client. Legacy performs **no**
ownership, price, or state check for a sell ("Client chooses the victim
item and the reason; resurrectability is a server-side lookup, not a client
flag"), so the endpoint's validation is structural fail-closed only:
whether a building is sellable at all is a client-side display rule, and
authoritative server-side validation belongs to Server v1 / M13. An item
index that names no row in the corpus is answered with a structured
`unknown_item_index` error rather than legacy's silent early return, which
would otherwise persist a save and report a success for a removal that
never happened; and a key that survived execution fails closed with
`internal_error` rather than claiming a removal the persisted save does not
show. Storage is display-only here: `sell_stored_item` and the other
storage commands, the combat `kill`/`batch_remove` paths, `orient`,
`collect`, upgrade paths, construction timers, town expansion, resources,
and XP are later deliver lines. No Flash, Ruffle, ActionScript, or browser
executes, no external network is used, and no pixel-parity oracle against
the legacy client exists.
