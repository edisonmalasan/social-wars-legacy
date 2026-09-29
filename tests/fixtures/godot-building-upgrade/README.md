# Executed-legacy upgrade fixture (`godot-building-upgrade`)

The executed-legacy parity oracle for the Compatibility API v0 upgrade
endpoint: one real **two-command** upgrade batch captured from the real
legacy Flask server (design D9 of the `building-upgrade` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_upgrade_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move/sell/
store fixture digests, discards the copy, and only then publishes this
directory. The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
and store captures):

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
tests/fixtures/godot-building-upgrade/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + established/derived split,
│                                  steps, negative oracle, time-dependent
│                                  leaves, containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_upgrade/          POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the row replaced
                                  in place and boughtUnits grown
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because upgrade parity
compares *state changes* on both the map and `privateState.boughtUnits`.

## The transaction

Intent (constants in `capture_upgrade_fixture.py`, verified against the
committed config and fresh save):

- **Building**: the Wall I, item id `23` — 1×1, `type "b"`,
  `costs {"w":5}` (its *purchase* price, irrelevant here),
  `upgrades_to "24"`, `clicks_to_build "1"` — at legacy map key `"12"`,
  anchored at `(45,49)` (`[23, 45, 49, 0, 0, [], {}, 1]` in the fresh
  save).
- **Target**: the **Wall II**, item id `24` — the tier the item's own
  `upgrades_to` names, resolved server-side with the documented
  `-1`/`0`-and-unresolvable-means-no-path rule
  (`packages/game-content/tools/build_items.py:546-557`). It is never
  client-supplied.
- **Target cell**: none of its own. The `buy` half reuses the replaced
  row's **own key and own cell**, which is how the pair upgrades in place
  instead of re-keying the map. Slot `12` is a wall segment, distinct from
  the move fixture's slot `11` and the sell fixture's slot `20` (Turret Is)
  and the store fixture's slot `2` (the Tree decoration), so every
  delivered fixture stays independently readable.
- **Contract**: one intent only — a save id and the legacy map index. No
  target tier, no reason, no coordinates, no orientation, no player, no
  quantity, no price, and no resource deltas are sent by the client; the
  envelope is derived server-side (below).

Derived envelope:

```json
{"accessToken":"",
 "commands":[[0,"sell",[12,"UPGR"],[0,0,0,0,0,0,0,0]],
             [0,"buy",[12,24,45,49,1,0,0,""],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

### Established versus derived — the provenance split

This is the seventh change in the same family and the first whose contract
had to be *established* rather than chosen, so the boundary is drawn
explicitly.

**Established from committed legacy source and executed-legacy evidence**

| Fact | Evidence |
| --- | --- |
| There is no `upgrade` command | 63 named `command.py` dispatcher branches (`docs/legacy-protocol/commands.json`); none named `upgrade`, and the only branch consuming a second argument as a *reason* is `sell` |
| The upgrade sell reason is `"UPGR"` | `constants.py:970` `SELL_REASON_UPGRADE = "UPGR"` |
| `sell` is the row-removing half | `command.py:149-168` reads `item_index` and `reason`, resolves with `engine.map_get_item`, deletes with `engine.map_delete_item` (`engine.py:36-52`), writes nothing else |
| `buy` can reuse an exact key and cell | `command.py:42-58` takes `[item_index, item_id, x, y, playerID, orientation, unknown, reason]` and calls `map_add_item(map, item_index, item_id, x, y, …)` — the **key** and the cell are client-supplied |
| `buy` writes a *fresh* row | `engine.py:8-31`: `timestamp` defaults to `timestamp_now()`, `store` to `[]`, and for a `player == 1` item with `clicks_to_build > 0`, `attr["nc"] = 0` |
| `buy` records the new tier | `command.py:52-53`: `bought_unit_add(save, item_id)` when `playerID == 1`; `engine.py:86-89` appends only when the item is not already listed |
| The target tier is in the configuration | every item carries `upgrades_to`; `-1`/`0` mean none and other values resolve against the item set (`build_items.py:546-557`); Wall I (23) → Wall II (24) |
| No upgrade price exists | item `cost` is `"0"` and `cost_type` is `null` across all 778 items (dead fields), `costs` prices the *purchase* only, and the 139 populated `premium_upgrade_costs` entries belong to the separate premium path (`btnUpgradeCash` / `CmdPremiumUpgrade`), whose relationship to this contract is unproven |
| The order is forced and the result is established | this fixture's execution, plus the reverse-order probe below |

**Derived and never observed from the Flash client**

- that the Flash client sends **exactly this pair** of commands (its static
  inventory names `CmdUpgrade`, `PopupUpgradeBuilding`, `btnUpgrade`,
  `btnUpgradeCash`, `upgradeinfo`, `getUpgradeBuilding`, `upgrades_to`,
  `premium_upgrade`, `premium_upgrade_costs`, `numUpgradesToday`,
  `lastUpgrades/`, but no executed request was ever observed — Flash is never
  executed in this repository);
- the buy half's `orientation` and `playerID` arguments (taken from the
  replaced row, because that is the only behaviour-preserving choice) and its
  discarded `unknown = 0` / `reason = ""` arguments;
- the **price vector**: all zeros on both commands, so **no upgrade cost is
  claimed at all** — not the target tier's `costs` (`{"s":15}`), not the
  difference between tiers, and nothing about `premium_upgrade_costs`.

### The commands

- `sell` takes exactly two positional args — `item_index` and `reason`
  (`command.py:150-151`, and the `sell` row of
  `docs/legacy-protocol/commands.md`). `item_index` is the legacy map key as
  an integer: legacy resolves the row with `engine.map_get_item(map, index)`,
  i.e. `map["items"][str(index)]` (`engine.py:36-40`).
- `reason = "UPGR"` is the committed constant (`constants.py:970`). It is
  **derived server-side, never chosen by a client**, so no client can claim
  another reason and in particular cannot claim the combat `"KILL"` reason
  that would route the row through `push_dead_unit` and the resurrectable-unit
  path in `privateState.deadHeroes`.
- `buy` takes exactly eight positional args (`command.py:43-50`) and reads six
  of them: `item_index` and `item_id` feed `map_add_item`, `x`/`y` are the
  row's own cell, `orientation` is the row's own, `playerID` is the row's own
  team (`== 1` selects the `bought_unit_add` record and the click-to-build
  seed), and `unknown` / `reason` are bound and discarded — the same
  documented placeholders the placement line uses.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* each
  branch at `command.py:40`) and it is **all zeros on both commands**.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.
- `command()` executes the commands in list order and persists the save
  **once** after the whole batch (`command.py:19-32`), so the two commands
  are atomic with respect to the save file.

## The negative oracle: a success status is not evidence of an upgrade

Sending the **same two commands in the reverse order** — `buy` first, then
`sell`:

```json
[[0,"buy",[12,24,45,49,1,0,0,""],[0,0,0,0,0,0,0,0]],
 [0,"sell",[12,"UPGR"],[0,0,0,0,0,0,0,0]]]
```

also answers HTTP 200 `{"result":"success"}` — and leaves **key `"12"`
absent**, with the placement count dropping `40` → `39` and
`privateState.boughtUnits` still gaining `24`. The building is *destroyed*,
not upgraded, and the legacy server reports success anyway.

Two consequences, both load-bearing:

1. **The order is forced.** The derived envelope is always `sell` then
   `buy`; the reverse is a documented anti-pattern, recorded in the capture
   manifest's `negative_oracle` block.
2. **The endpoint must prove the post-state.** `POST /v0/upgrade` therefore
   requires all three facts after execution — the key still exists, its item
   id equals the derived target tier, and its cell equals the pre-execution
   cell — and fails closed with `internal_error` on any other outcome. A
   placement with no resolvable next tier answers `no_upgrade_path` (400)
   *before* the dispatcher runs, so such a building is never reduced to a
   bare sale.

The reverse-order outcome is re-derived offline against the unchanged legacy
dispatcher by `apps/compat-api/tests/test_upgrade_endpoint.py`
(`ReverseOrderOracleTests`), which runs the reversed batch in a disposable
corpus and asserts the key is gone and the count fell — no server, no
network.

## Executed outcome (as recorded, verified by the tool before publishing)

- response `{"result":"success"}`;
- `maps[0].items["12"]` — `[23, 45, 49, 0, 0, [], {}, 1]` — becomes
  `[24, 45, 49, <wall-clock timestamp>, 0, [], {"nc": 0}, 1]`:
  - the same **key**, so nothing is re-keyed and the placement count stays
    `40`;
  - the same **cell** `(45,49)`, the same `orientation 0`, and the same
    `player 1`;
  - a **fresh** `timestamp` — the replaced row's own timestamp, `store`, and
    `attr` are **not** carried over, because `engine.map_add_item` writes a
    new row (design D5; the same documented normalization the placement
    fixture uses);
  - `attr` becomes `{"nc": 0}` because Wall II's configuration has
    `clicks_to_build "1" > 0` (`engine.py:25-29`) — the click-to-build
    counter. **It is seeded but unconsumed here**: this line shows the
    upgraded building as immediately present with no timer, and consuming
    `nc` belongs to the `activate` / `add_click` / `activate_item_click` /
    `finish_si` family that the construction-timers line owns;
- `privateState.boughtUnits` goes `[]` → `[24]` because `buy` with
  `playerID == 1` calls `bought_unit_add` (which appends only a not-yet-listed
  item, `engine.py:86-89`);
- every other placement row byte-identical;
- `maps[0].store` stays `{}` — an upgrade stores nothing;
- the rest of `privateState` byte-identical, including `deadHeroes` (`{}`),
  because the reason is `"UPGR"`, never `"KILL"`, so `push_dead_unit` never
  runs;
- `playerInfo` byte-identical;
- `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0` — all unchanged, because both
  derived vectors are neutral and the legacy clamp `max(…, 0)` therefore
  never rewrites a value.

Exactly **four** leaves differ between the recorded before- and after-states,
and exactly **one** of them is a clock reading (asserted by
`apps/compat-api/tests/test_upgrade_parity.py`):

| leaf | change |
| --- | --- |
| `/maps/0/items/12/0` | `23` → `24` — the new tier |
| `/maps/0/items/12/3` | `0` → a wall-clock stamp — **the documented time-dependent field** |
| `/maps/0/items/12/6/nc` | absent → `0` — the click-to-build seed |
| `/privateState/boughtUnits` | `[]` → `[24]` — the purchase half's record |

## Sanitization

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too). The live requests always sent the real values — only the
records are redacted. Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

Re-running the capture exits 0 and reproduces every file byte-identically
**except** these documented time-dependent fields. Verified by a leaf-level
diff of two consecutive runs: 11 differing leaves in total, every one of
them named in the manifest's `time_dependent_fields.leaves`:

- `/captured_at_utc` in every `request.json` / `response.meta.json`;
- `/executed_at_utc` in `capture-manifest.json`;
- `/headers/Date` in both `response.meta.json` files;
- the envelope `ts` inside `command_upgrade/request.json`'s `/form/data`
  (and therefore that field's sha256 digest);
- the upgraded row's wall-clock timestamp at
  `steps/command_upgrade/after.json`'s `/maps/0/items/12/3`, and the two
  manifest leaves derived from it —
  `/transaction/upgraded_row_after/3` and
  `/transaction/steps/1/save_after_sha256`.

Everything else — both save states, both response bodies, and the envelope's
two commands, their order, both argument lists, the committed reason, and
both neutral resource vectors — is byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the six already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/` →
`4d389707e0f18676fb23b3a2a8a47031b4e233366e4066437f8bad6854e15234`,
`tests/fixtures/godot-building-placement/` →
`546a5f00e5e45319ffd17f5ee67201dd2b72cb21de833a3e35e8a9a98d60c5a8`,
`tests/fixtures/godot-item-purchase/` →
`d05e5b92b26a1222774bb32e76a42417c692e65ee1b87abdb8a2f4e6cd84e813`,
`tests/fixtures/godot-building-move/` →
`b3c477a7947fbe409330f03a8658cdca707a2631b52d1d4c5127f440619799c1`,
`tests/fixtures/godot-building-sell/` →
`fa85af3fb12ef8b9298203a64632b6d7b31c1ed48f8d1ba716151f25ec7ab1c4`, and
`tests/fixtures/godot-building-store/` →
`d4dff84132353a60e3a005c42d067185772ec8d6a2548ffdc5aa4779a2055194`) and
fails closed if any of them changed during the run, so this capture can never
silently absorb an earlier change's evidence. Only the disposable copy is
written and it is removed on every exit path; no working-tree save is ever
written; the service never binds anywhere but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_upgrade_envelope.py` for the derivation, sanitization, and capture
contract; `test_upgrade_endpoint.py` for the `/v0/upgrade` structural
contract, the no-upgrade-path error, the three-part post-execution proof, the
reverse-order negative oracle, and corpus-only persistence;
`test_upgrade_parity.py` consumes this fixture and replays the recorded
intent through the endpoint offline.)

### What this fixture proves

- the exact two-command batch envelope the Compatibility API derives for an
  upgrade intent, and that the unchanged legacy dispatcher accepts it;
- that the executed transaction replaces **exactly one** row in place — the
  same key, the same cell, the new tier, a fresh timestamp, and the
  click-to-build seed — and writes nothing else beyond `boughtUnits`;
- that legacy's own success status is not evidence of an upgrade, because the
  reverse order succeeds too while destroying the building;
- that the endpoint's response equals the captured response and that its
  corpus save equals the captured after-state for every stable field.

### Claim limits

- Parity covers **this one recorded upgrade transaction against the
  fresh-player corpus** — not progressed players, not other commands, and not
  a second upgrade of a different row. The fixture's target tier happens to
  be a wall segment; nothing is claimed about other buildings' tier chains
  beyond what the committed configuration's `upgrades_to` values say.
- The composed pair is **derived** (that the Flash client sends exactly this
  pair), although its shape, the committed reason, the client-supplied key and
  cell of `buy`, the ordering, and the resulting state are **established**.
- **No upgrade cost is claimed.** The committed configuration records no
  upgrade price anywhere, prices travel only in client-sent deltas that this
  contract refuses, and therefore both derived vectors are neutral. That is a
  derivation boundary, not a claim that upgrading is free in the legacy
  client. Nothing is claimed about `premium_upgrade_costs` either, and the
  premium upgrade path (`btnUpgradeCash` / `CmdPremiumUpgrade`) is a separate,
  unrecorded price class.
- The `{"nc": 0}` construction counter is **seeded but unconsumed**. This line
  does not construct, complete, or time the upgraded building; consuming
  `nc` belongs to the construction-timers line.
- The legacy client's **level gate** ("You need to be level #0# to upgrade this
  building."), **daily-upgrade limit** (`numUpgradesToday` / `lastUpgrades/`),
  and **space check** ("No space to upgrade") are known to exist and are
  **deliberately not implemented** here. None is enforced by the legacy
  server and none can be reproduced from the repository; the space check is
  vacuous for this contract because the same key and cell are reused; and the
  level gate is *inexercisable on the committed corpus* — the fresh save's
  `maps[0].level` is 1 and no placement in that corpus has a next tier with
  `min_level <= 1` (the lowest reachable is 5, Turret I → Turret II; the
  fixture's own target tier needs 9). Enforcing it would make this deliver
  line unreachable on the corpus the project preserves, so it is named as an
  explicit follow-up instead of invented.
- Legacy performs **no** ownership, price, or state check for an upgrade, so
  the endpoint's validation is structural fail-closed only: whether a
  building is upgradeable *today* is a client-side display rule, and
  authoritative server-side validation belongs to Server v1 / M13. A building
  with no resolvable next tier is answered with a structured
  `no_upgrade_path` error rather than being reduced to a bare sale; an item
  index that names no row is answered with `unknown_item_index` rather than
  legacy's silent early return; and a post-state that is not the derived
  upgrade fails closed with `internal_error` rather than claiming one.
- `privateState.boughtUnits` gains the target tier while that tier is not
  already listed (`bought_unit_add` deduplicates), so the list is not a
  per-upgrade ledger.
- Storage is display-only here: `place_stored_item`, `sell_stored_item`,
  `orient`, `collect`, the premium upgrade path, town expansion, resources,
  and XP are later deliver lines.
- No Flash, Ruffle, ActionScript, or browser executes, no external network is
  used, and no pixel-parity oracle against the legacy client exists.
