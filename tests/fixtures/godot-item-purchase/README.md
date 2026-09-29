# Executed-legacy purchase fixture (`godot-item-purchase`)

The executed-legacy parity oracle for the Compatibility API v0 purchase
endpoint: one real `buy_stored_item_cash` transaction captured from the real
legacy Flask server (design D9 of the `building-purchase` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_purchase_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement fixture digests,
discards the copy, and only then publishes this directory. The opt-in legacy
command recorder env var (`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from
the child.

Exit codes (identical meanings to the boot and placement captures):

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
      boot/placement fixtures changed, or the disposable corpus saves
      changed during server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-item-purchase/
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
    └── command_buy_stored_item_cash/  POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the purchase
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because purchase parity
compares *state changes*.

## The transaction

Intent (constants in `capture_purchase_fixture.py`, verified against the
committed config and fresh save):

- **Item**: Victory Arch, item id `105` — `costs={"c":5}`, 2×2, `min_level 1`,
  `in_store 1`, a building (`type "b"`).
- **Selection rule**: the store-listed, cash-priced building whose
  `min_level` (1) the fresh-player map level (1) already allows and whose
  cash price (5) is exactly the fresh player's `cash` (5) — so the recorded
  transaction is a **fully payable** purchase, not a clamped one. The fresh
  save has `maps[0].store == {}` and `privateState.boughtUnits == []`, so the
  whole storage and bought-units effect is visible in one transaction.
- **Contract**: one intent only — a save id and an item id. No price, no
  quantity, no resource deltas are sent by the client; the price is derived
  from the item's own config (below).

Derived envelope (all values **derived-provisional**: the Flash client is
never executed, so both the command the real shop button sends and the exact
envelope are unobservable — design D1/D2):

```json
{"accessToken":"", "commands":[[0,"buy_stored_item_cash",[105],[0,0,0,0,0,0,-5,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

- `buy_stored_item_cash` takes exactly one positional arg — the item id
  (`command.py:475-480`).
- `resources_changed` is the negated cash price on the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`), cash slot `6`. Every other
  slot is `0`: the derivation is **cash-only** (design D2), and an item priced
  in gold, wood, oil, steel, or a mix of them fails closed with
  `costs_not_cash` before the dispatcher runs.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.

Executed outcome (as recorded, verified by the tool before publishing):

- response `{"result":"success"}`;
- `maps[0].store` `{}` → `{"105": 1}` (legacy
  `engine.add_store_item` increments `map["store"][str(item_id)]`, quantity 1);
- `privateState.boughtUnits` `[]` → `[105]` (legacy
  `engine.bought_unit_add` appends the id when absent);
- `playerInfo.cash` `5` → `0` (exactly the derived −5 under the legacy
  `max(…, 0)` clamp); `xp`, `gold`, `wood`, `oil`, `steel`, `mana` unchanged;
- `maps[0].items` unchanged — a storage purchase places nothing on the map
  (placing from storage is the later *store* deliver line).

Those three leaves (`/maps/0/store/105`, `/playerInfo/cash`,
`/privateState/boughtUnits`) are the **only** differences between the
recorded before- and after-states, and none of them is a clock reading:
unlike the placement transaction, this command writes no wall-clock value
(`apply_resources`' timestamp write is commented out in legacy), so both
saves are byte-stable across reruns and purchase parity needs **no**
time-dependent normalization on the state.

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
- the envelope `ts` inside
  `command_buy_stored_item_cash/request.json`'s `data` field, and
  therefore that field's sha256 digest.

Everything else — both save states, both response bodies, and the
envelope's single command, argument list, and cash price vector — is
byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the two already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/` →
`4d389707e0f18676fb23b3a2a8a47031b4e233366e4066437f8bad6854e15234`,
`tests/fixtures/godot-building-placement/` →
`546a5f00e5e45319ffd17f5ee67201dd2b72cb21de833a3e35e8a9a98d60c5a8`) and
fails with exit 6 if either changed during the run. The only working-tree
writes are the files in this directory; the disposable copy is removed
before exit; no working-tree save is ever written; the service never binds
anywhere but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_purchase_envelope.py` for the derivation, sanitization, and capture
contract; `test_purchase_endpoint.py` for the `/v0/purchase` structural
contract and corpus-only persistence; `test_purchase_parity.py` consumes
this fixture and replays the recorded intent through the endpoint offline.)

Claim limits: parity covers this **one recorded `buy_stored_item_cash`
transaction against the fresh-player corpus** for the derived envelope — not
progressed players, not other commands. The chosen legacy command and the
cash-only price derivation are **derived, never observed from the Flash
client**; the envelope placeholders are derived too. The cash-only
restriction is a derivation boundary, not a gameplay rule: the spec does not
claim gold- or multi-resource-priced storage purchases exist or do not exist
(`store_add_items` remains the any-price acquisition path, out of scope here).
Insufficient cash reproduces legacy clamping (`max(…, 0)`), never rejection —
the fixture is fully payable, and the clamp is proven by the endpoint test,
not relied on by this transaction; authoritative server-side validation
belongs to Server v1 / M13. Storage is display-only here: placing from
storage, moving, and selling out of storage are later deliver lines. No Flash,
Ruffle, ActionScript, or browser executes, no external network is used, and
no pixel-parity oracle against the legacy client exists.
