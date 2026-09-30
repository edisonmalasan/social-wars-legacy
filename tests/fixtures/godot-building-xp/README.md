# Executed-legacy level fixture (`godot-building-xp`)

The executed-legacy parity oracle for the Compatibility API v0 level-up
endpoint: one real **`level_up`** command carrying the **service-derived** level
and a **neutral** vector, captured from the real legacy Flask server (design D10
of the `building-xp` OpenSpec change).  No Flash, browser, Ruffle,
ActionScript, or external network was involved — only the legacy server on
loopback under the pinned interpreter.

This is the **eleventh and last** change in the same family, and the first
whose legacy command has **no committed content behind it at all**:
`command.level_up` is one line of state change, `map["level"] = new_level`, with
**no range check and no experience validation**, and **nothing in the legacy
server reads the committed `levels` curve** — zero references across
`command.py`, `engine.py`, `sessions.py`, `server.py`, and `constants.py`.  That
absence is what makes this line the first in the family where a **real
server-side guard** is possible rather than merely an intent-only refusal: the
curve that constrains the level is committed content, and the committed corpus
decides its index base.

Like the expand fixture, it is a fixture with **no time-dependent state leaf at
all**: `level_up` writes an integer the client sent into the map and the derived
vector is the neutral all-zero vector, so both recorded save documents and the
response body are byte-identical across reruns.

## How it was captured

```bash
python -B apps/compat-api/capture_level_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two recorded requests, runs one **probe** request
against the same live server (below), stops the server (`taskkill /T /F` +
port-free re-check), re-checks the working-tree containment snapshot and the
ten committed boot/placement/purchase/move/sell/store/upgrade/construction/
collect/expand fixture digests, discards the copy, and only then publishes this
directory.  The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
store, upgrade, construction, collect, and expand captures):

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
tests/fixtures/godot-building-xp/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + established/derived split
│                                  with every decision, the executed probe,
│                                  steps, time-dependent leaves, containment
│                                  digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_level_up/         POST …/command.php — 200
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with
                                  `maps[0].level` = the derived level
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because level parity compares
the *whole* recorded level and the resource movement, and because this
fixture's state carries no clock reading to normalize.

## The transaction

Intent (constants in `capture_level_fixture.py`, verified against the
committed config and fresh save):

- **Level sent**: `1` — the level the committed **one-based** curve derives for
  the corpus's own stored experience.  `maps[0].xp` is `4`; the committed
  `levels` ladder is `0, 40, 60, 100, 200, 350, 550, 800, …`; so the highest
  level the experience meets is **1**.  The level is **derived server-side from
  committed content**, never client-supplied.
- **Contract**: one intent per level-up step — a save id and nothing else.  No
  level, experience, reward, time, or resource delta is sent by the client; the
  envelope is derived server-side (below).
- **Where the recorded level stands.**  The corpus **already records level 1**,
  so the recorded transaction leaves `maps[0].level` **at 1** and every byte of
  the corpus save is identical before and after.  That is not a defect in the
  fixture — it is the exact corpus condition behind the endpoint's
  `level_already_current` refusal, and this fixture is its executed evidence.
  The **level movement** the success path promises is established by **probe 1**
  below, executed against the same live server in the same run.

Derived envelope:

```json
{"accessToken":"",
 "commands":[[0,"level_up",[1],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

That vector is `[0, xp, gold, wood, oil, steel, cash, mana]` and it is
**neutral**: every slot is `0`.  A level change moves no resource, the
committed curve pays no reward (nothing consumes `reward_type` /
`reward_amount`), and :func:`level_envelope.validate_vector` refuses anything
but the all-zero vector — so the derivation cannot even *express* a smuggling
attempt.  The endpoint's second post-execution proof half then requires that
**every** stored resource is **unchanged**, which is what forecloses the exploit
(see the probe).

### Established versus derived — the provenance split

The contract was established and recorded in `docs/legacy-xp-basics.md`
before this fixture was written, so the boundary is drawn explicitly here too.

**Established from committed legacy source, the committed command catalog, and
committed content**

| Fact | Evidence |
| --- | --- |
| `level_up(new_level)` takes exactly one positional argument and writes `map["level"] = new_level` with **no range check and no experience validation**, changing nothing else | `command.py:81-85`; the `level_up` row of `docs/legacy-protocol/commands.json` records the write `map[level] = new_level with no range or XP validation`, the read `map[level]`, and the security note "Client sets the map level directly; XP/level consistency is not verified server-side" |
| The 8-slot resource vector is applied **before** the branch, verbatim per resource, as `max(current + delta, 0)` | `command.py:40`, `engine.apply_resources` (`engine.py:251-271`); the catalog's `resource_effects` states both facts outright, and its `client_trust` names the `resources_changed` deltas |
| **Nothing in the legacy server reads the committed `levels` schedule** | a repository-wide search finds **zero** references across `command.py`, `engine.py`, `sessions.py`, `server.py`, and `constants.py` |
| The committed curve has **100** entries, each `{name, exp_required, reward_type, reward_amount}` with all four fields fully native numbers | `config/main.json`; `docs/game-content/census.md`; `docs/game-content/field-types.md`; `packages/game-content/README.md` (tables extension) records the 100-entry normalization with `legacy_id` as the 0-based positional index |
| `exp_required` is **strictly increasing** with no duplicates and no non-positive gap: `0, 40, 60, 100, 200, 350, 550, 800, …` to `2016089205` | joined over all 100 stored entries |
| `name` is **not** distinct — 44 names across 100 entries, and every entry from level 49 onward is `"Conqueror"` — so it is a **label, not an identifier** | joined over all 100 stored entries |
| `reward_type` is one of `s` / `w` / `g` / `c` — the *letter* vocabulary of `items[].costs`, not the server's resource names — and `reward_amount` takes exactly `1`, `50`, `250`; **neither is consumed by any branch** | joined over all 100 stored entries, plus the zero references above |
| `maps[0].xp` is the player's experience (the 8-slot vector's **slot 1**, written by `engine.apply_resources`); `maps[0].level` is written **only** by `level_up` | `engine.py:251-271`; `command.py:81-85` |
| **No placed corpus row carries unit experience**: 0 of the 40 placed rows have an `xp` key in their attribute bag, and the fresh save has no unit placements at all | `tests/saves/fresh-player.json`, joined over all 40 rows |
| The corpus facts: `xp 4`, `level 1`, 40 placements, `store {}`, `gold/wood/oil/steel 2000`, `playerInfo.cash 5`, `privateState.mana 0`, `increasedPopulation 0`, and **no** `map_sizes` field | `tests/saves/fresh-player.json` (and `fresh-player-pre-migration.json`) |

**Derived and never observed from the Flash client** — the decisions, all
recorded verbatim in the module docstring of
`apps/compat-api/level_envelope.py` and in the manifest's
`intent.derived.decisions`:

- **D1 — the curve is ONE-BASED: stored level *n* is `levels[n - 1]`, and the
  conversion lives in exactly one named function
  (`level_envelope.entry_index_for_level`).**  This is
  **DERIVED-PROVISIONAL**, and the **REJECTED** alternative is the
  **ZERO-BASED** reading — `map["level"]` as the index itself.
  *The corpus contradicts it directly:*

  ```
  corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0
  ```

  Under zero-based, a player with 4 experience is recorded as level 1 while the
  curve says level 1 begins at 40 experience — a direct contradiction.  Under the
  one-based reading, stored level 1 is `levels[0]` — `"Slave"`,
  `exp_required` 0 — and `4 >= 0` holds, so **the corpus is self-consistent**.
  The capture asserts that disagreement against the real schedule on every run
  and **fails if it ever disappears**, because it is the whole evidence.
  Guessing zero-based would shift **every** level in the game by one, and the
  error would stay invisible until a player noticed the wrong level name — which
  is why the decision is written down rather than absorbed into an index
  expression, and why the conversion is one named function a later change can
  revise on better evidence.
- **D2 — the recorded level is unverified, and a disagreement is reported, never
  smoothed.**  The server wrote it from a client integer with no validation, so
  it is evidence of what a client once asked for and of nothing else.  Two
  distinct facts therefore exist and are never conflated — the **derived** level
  and the **recorded** level — and the two refusals exist precisely so neither
  value is silently reconciled.
- **D3 — the target level is derived server-side; the client never supplies
  it.**  The request carries only the save id; a client-supplied `level` (or
  `new_level`, or `xp`) key is ignored, exactly as the collect and expand
  endpoints ignore client-supplied amounts and prices.  This closes the legacy
  hole where any client could set level 99.
- **D4 — both refusals are fail-closed and precede the dispatcher**, so the
  corpus is byte-identical on every error path: `level_already_current` (409)
  and `xp_below_threshold` (409).
- **D5 — the post-state proof is the level *and the absence of resource
  movement*.**  `level_up` is dispatched with a client-sent vector like every
  other command, so a non-zero vector would move a balance through this very
  branch; the derived vector is **neutral** and the endpoint requires that
  **every** stored resource be **unchanged**.  Probe 1 below is the executed
  evidence that makes that check real rather than a tautology.
- **D6 — an unaffordable next level is reported, never skipped.**  The next
  threshold and the remaining experience are information only: no gate, no
  penalty, no invented rule.
- **D7 — no tuning, no rewards, no unit experience, no tutorial.**  The
  committed `exp_required` values are preserved **verbatim** — nothing is
  rebalanced, smoothed, or interpolated.  `reward_type` / `reward_amount` are
  consumed by no legacy branch and are therefore **refused rather than
  invented**, the same discipline the expansion `neighbors` / `inventory_qte`
  requirements received.  `add_xp_unit` is out of scope because the corpus
  cannot exercise it, and `complete_tutorial` is a separate progression system.

The claim is therefore: **the recorded level is the one the committed curve
implies for the stored experience** — never one observed a Flash client send,
and **no reward** is claimed for any level.

### The one executed probe

**Probe 1 — what does the branch actually write, and what happens when the
client-sent resource vector is not neutral?**  One batch,
`level_up([2])` with a **client-sent** `[0, 500, 0, 0, 0, 0, 0, 0]` vector,
executed against this same live server in this same run, immediately after the
recorded step and on the same disposable copy:

```
level 1 -> 2
xp 4 -> 504
changed top-level map keys: ['level', 'xp']
gold, wood, oil, steel, cash and mana unchanged
response {"result":"success"}
```

Established: the branch assigns `args[0]` to `map["level"]` and writes **nothing
else** — not the placements, not `store`, not `map_sizes`, not
`increasedPopulation`, not `privateState`, not `playerInfo` — and the experience
move is **entirely client-sent**, applied verbatim per resource as
`max(current + delta, 0)` before the branch (`command.py:40`,
`engine.py:251-271`).

**Why it matters:** this is the executed evidence for the derived neutral vector
and for the endpoint's "nothing moved" post-execution proof.  A level-up that
carried a non-zero vector *would* move a balance through this very branch, so
proving after execution that **every** stored resource is unchanged is what
distinguishes a correct level-up from a resource-minting exploit wearing its
clothes (design D5).  Without probe 1 the "nothing moved" proof would be a
tautology.

## The command

- `level_up` takes exactly one positional arg — the new level
  (`command.py:82`, and the `level_up` row of
  `docs/legacy-protocol/commands.md`).  The branch binds `args[0]` and assigns
  it: `map["level"] = new_level`.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the branch at
  `command.py:40`), and it carries the **neutral** vector
  `[0, 0, 0, 0, 0, 0, 0, 0]`.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.
- `command()` persists the save **once** after the whole batch
  (`command.py:19-32`), so the single command is atomic with respect to the
  save file.

## The committed curve

| levels | `name` | `exp_required` | note |
| --- | --- | --- | --- |
| `1` | `Slave` | `0` | the floor; stored level 1 is `levels[0]` |
| `2` | `Servant` | `40` | |
| `3` | `Peon` | `60` | |
| `4` | `Peasant` | `100` | |
| `5 …` | … | `200, 350, 550, 800, …` | strictly increasing throughout |
| `100` | `Conqueror` | `2016089205` | the top; no next level |

100 entries in total.  `reward_type` is one of `s` / `w` / `g` / `c` and
`reward_amount` is one of `1` / `50` / `250` on every entry — and **nothing
consumes either**.  `name` is a label: 44 distinct names across 100 entries.

## Executed outcome (as recorded, verified by the tool before publishing)

- response `{"result":"success"}`;
- `maps[0].level` is `1` before and `1` after — it **equals the derived level**,
  and it **did not move**, because the corpus already recorded the level the
  committed curve derives for its `4` stored experience.  Recorded as the
  manifest's `transaction.level_moved: false` with `level_moved_note`, and
  stated here rather than papered over;
- **all seven stored resources are unchanged**, because the derived vector is
  neutral: `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0`;
- the placement count stays `40` — no key is added or removed, and **every one
  of the 40 rows is byte-identical**: a level-up rewrites no placement at all;
- `maps[0].increasedPopulation` stays `0`, `maps[0].store` stays `{}`;
- `map_sizes` stays **absent** — the committed corpus does not record that field
  (nor does any committed legacy source or the committed config), so its
  *absence* is what the whole-key-set equality check enforces; the tool also
  asserts explicitly that the field's presence did not change;
- **every other top-level map field is byte-identical**, and the map's whole
  top-level key set is unchanged (so no field this README does not name could
  have moved either);
- the whole `privateState` byte-identical, including `boughtUnits` (`[]`) and
  `deadHeroes` (`{}`);
- `playerInfo` byte-identical.

Exactly **zero** leaves differ between the recorded before- and after-states:
`/transaction/recorded_leaf_differences` is `[]`, and
`apps/compat-api/tests/test_level_parity.py` asserts it.

## Sanitization

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too).  The live requests always sent the real values — only the
records are redacted.  Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

**The recorded state and the recorded response have no time-dependent field
at all.**  `level_up` writes an integer the client sent into the map and the
derived vector is neutral, so `steps/login_post/before.json`,
`steps/login_post/after.json`, `steps/command_level_up/before.json`,
`steps/command_level_up/after.json`, and both `response.body` files are
**byte-identical across reruns** — verified by a leaf-level diff of two
consecutive runs.  There is no wall-clock reading anywhere in the recorded
state: unlike `collect`'s `item[3] = time_now()`, the `level_up` branch writes
no clock of its own.

That diff found **exactly 8 differing file+pointer paths in total**, every one
of them named in the manifest's `time_dependent_fields.leaves`, and **none of
them in the state or the response**:

- `/captured_at_utc` in both `request.json` and both `response.meta.json`
  (four files);
- `/executed_at_utc` in `capture-manifest.json`;
- `/headers/Date` in both `response.meta.json` files;
- the envelope `ts` inside `command_level_up/request.json`'s `/form/data` (and
  therefore that whole field's string, because the digest covers the payload).

Everything else — both save states, both response bodies, the envelope's single
command, its derived argument, and the neutral vector `[0, 0, 0, 0, 0, 0, 0, 0]`
— is byte-stable.  The manifest's `time_dependent_fields.state_leaves` is the
**empty list**, deliberately: the documented time-dependent *state* surface of
this fixture is empty, and no leaf was invented to fill it.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the **ten** already committed fixture
directories — `godot-compatibility-boot`, `godot-building-placement`,
`godot-item-purchase`, `godot-building-move`, `godot-building-sell`,
`godot-building-store`, `godot-building-upgrade`,
`godot-building-construction`, `godot-building-collect`, and
`godot-building-expand` — and fails closed if any of them changed during the
run, so this capture can never silently absorb an earlier change's evidence.
Only the disposable copy is written and it is removed on every exit path; no
working-tree save is ever written; the service never binds anywhere but
`127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_level_envelope.py` for the derivation, the one-based conversion, every
ladder boundary, the corpus case, the neutral vector, the refusal paths, the
shared-helper round trip, real-config cross-checks, and the capture contract;
`test_level_endpoint.py` for the `/v0/level_up` structural contract, both
refusals, the two-part post-execution proof, and corpus-only persistence;
`test_level_parity.py` consumes this fixture and replays the recorded intent
through the endpoint offline.)

### What this fixture proves

- the exact single-command envelope the Compatibility API derives for a
  level-up, carrying the **derived** level and the **neutral** vector, and that
  the unchanged legacy dispatcher accepts it;
- that the executed transaction writes **exactly** the level the client sent and
  changes **nothing else** in the save — no placement, no storage, no private
  state, no player info, no other map field;
- that **no** stored resource moved, because the derived vector is neutral;
- that the branch *does* move the level and *does* move a balance when the
  client sends one (probe 1), which is what makes the "nothing moved" proof
  meaningful;
- and that the endpoint's responses and its corpus save equal the captured
  response and after-state for **every** leaf, with no clock normalization at
  all.

### Claim limits

- Parity covers **this one recorded level transaction against the fresh-player
  corpus** — not progressed players, not other commands, and not a second
  level-up.  The committed corpus is the whole corpus-side story available
  here.
- **The recorded level did not move on this corpus.**  The committed curve
  derives level 1 for the corpus's `4` experience and the corpus already
  records level 1, so the recorded transaction writes an identical value.  The
  movement the endpoint's success path promises is established by **probe 1**,
  and the *recorded* fixture shows the corpus condition behind the endpoint's
  `level_already_current` refusal.  Nothing is claimed about what a level-up
  looked like for a player who actually advanced.
- **The one-based index interpretation is derived-provisional**, and the
  **rejected zero-based alternative** is recorded with the corpus contradiction
  that rejects it (`xp 4 | stored level 1 | zero-based implies 0`).  The
  evidence is one data point in a hand-built corpus, so a later change with
  better evidence revises **one named function** rather than auditing the
  codebase.  Guessing zero-based would shift every level by one.
- **No level reward is paid, and none is claimed.**  `reward_type` and
  `reward_amount` are committed on every entry and consumed by no legacy branch,
  so paying one would invent an economy.  The neutral vector is the whole
  economic content of a level-up under this contract.
- **Unit experience and tutorial progression are out of scope**: the committed
  corpus has no unit placements and 0 of its 40 placed rows carry `attr["xp"]`,
  and `complete_tutorial` is a separate progression system.
- **The curve is preserved verbatim.**  No `exp_required` value is rebalanced,
  smoothed, or interpolated; the committed ladder is used as committed.
- **No pixel-parity oracle against the legacy client exists.**  The client
  readout, the level-up prompt, and the level names a player sees are not
  compared to anything here.
- Legacy performs no ownership, state, or gameplay validation of any kind for
  this command, so the endpoint's validation is structural fail-closed plus the
  curve-derived target and the two refusals; authoritative validation beyond
  this one guard belongs to Server v1 / M13.  Both refusals answer **before**
  the dispatcher runs, so the corpus is byte-identical on every error path; and
  a post-state that is not the promised transaction — the recorded level not
  exactly the derived level, or **any** stored resource changed — fails closed
  with `internal_error` rather than reporting the legacy success.
- The recorded-versus-derived disagreement is **reported, never reconciled**:
  the endpoint does not prefer either value, does not normalize the save, and
  never offers a level-up that would erase the conflict without the client
  acting.
- The **clamp is not exercised by this fixture**: the derived vector is
  neutral, so no balance moves and legacy's `max(current + delta, 0)` never
  bites.  The clamp itself remains exactly what `engine.py:262-268` says, and
  probe 1 is the executed evidence that the vector *is* client-sent.
- No Flash, Ruffle, ActionScript, or browser executes, no external network is
  used, and no pixel-parity oracle against the legacy client exists.