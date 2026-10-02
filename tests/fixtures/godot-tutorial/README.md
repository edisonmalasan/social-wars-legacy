# Executed-legacy tutorial fixture (`godot-tutorial`)

Captured by `apps/compat-api/capture_tutorial_fixture.py` against the **real**
legacy Flask server in a disposable copy, over loopback only.

```bash
python -B apps/compat-api/capture_tutorial_fixture.py
```

`python` denotes the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
Observed exit code `0` and containment `UNCHANGED` on **five** consecutive runs.

## Why two disposable rounds

`playerInfo.completed_tutorial` is `0` in the seed and `1` after any completing
step, so the `0 -> 1` transition is exercisable exactly **once per disposable
copy**. Two rounds are therefore required, not stylistic: folding both into one
server would silently record a `1 -> 1` rewrite instead of the transition the
fixture exists to capture. This is also why each round writes under
`steps/<round>/` — the two rounds each record a `login_post` and would otherwise
collide. Every other delivered fixture uses a flat `steps/<name>/`; this is the
one layout deviation and it is structural.

| round | recorded step | vector | flag | resources moved | leaves |
| --- | --- | --- | --- | --- | --- |
| `neutral` | `command_tutorial_15` | neutral `[0]*8` | `0 -> 1` | 0 | **1** |
| `neutral` | `command_tutorial_15_again` | neutral `[0]*8` | `1 -> 1` | 0 | **0** |
| `minting` | `command_tutorial_15_minting` | `[101,3,7,11,13,17,19,23]` | `0 -> 1` | **7** | **8** |

## The measured changed-leaf sets

**The parity transaction** — `command_tutorial_15`, exactly one leaf:

```
/playerInfo/completed_tutorial
```

That is the whole transaction: the gate flipped the flag, the neutral vector
moved nothing, and every placement row, the storage, the map, the rest of
`playerInfo`, the whole `privateState`, and all seven stored resources are
byte-identical.

**The idempotent repeat** — `command_tutorial_15_again`, zero leaves. The branch
assigns `1` over `1`. This is the executed counterpart of the endpoint's
already-complete refusal: legacy answers `{"result":"success"}` and changes
nothing rather than erroring.

**The proof anchor** — `command_tutorial_15_minting`, eight leaves:

```
/maps/0/gold   /maps/0/oil    /maps/0/steel  /maps/0/wood  /maps/0/xp
/playerInfo/cash   /privateState/mana   /playerInfo/completed_tutorial
```

Deltas are the ladder verbatim: `xp 4 -> 7`, `gold 2000 -> 2007`,
`wood 2000 -> 2011`, `oil 2000 -> 2013`, `steel 2000 -> 2017`,
`cash 5 -> 24`, `mana 0 -> 23`.

**The discarded slot 0 is absent.** The ladder's `101` is the vector's `unknown`,
which `engine.apply_resources` reads and throws away at `engine.py:253`. It must
not appear among the changed leaves, and the capture asserts that it does not —
so its absence is measured rather than assumed.

## The executed probe

One probe runs in the `minting` round, after that round's recorded step and on
the same live server: **the same ladder on step `24`** — the upper edge of the
gate's nine-value hole. Observed seven resource leaves and
`/playerInfo/completed_tutorial` **absent**; the flag did not move.

This is what separates the two effects the anchor shows together: completing the
tutorial moves the flag, and the **client-sent vector** moves resources — on a
step the gate *declines*. Without it, "completing the tutorial mints resources"
would be a live misreading of the anchor, and the endpoint's two-part post-state
proof would be asserting a distinction nothing evidenced.

## Layout

```
capture-manifest.json                      the full record
steps/<round>/login_post/                  request, before, response, after
steps/<round>/command_*/                   one directory per recorded step
```

Each step directory holds `request.json`, `before.json`, `response.body`,
`response.meta.json`, and `after.json`, with **full** before/after save documents
rather than value-free deltas. Secrets are redacted in the records only:
`user_key` and the `Cookie`/`Set-Cookie` headers become `<redacted>`, and the
crafted `accessToken` is the empty placeholder and never a token value.

## Containment

* Parent interpreter verified as CPython 3.9.x before anything runs.
* Port conflict on `127.0.0.1:5055` detected before starting anything.
* Working-tree containment snapshot taken before anything runs, and the digest
  of all **fifteen** already-committed fixture directories snapshotted too.
* Disposables built under the system temp root; root `*.py`, `config/`, `mods/`,
  `villages/`, `templates/`, and `saves/` seeded from
  `tests/saves/fresh-player.json`.
* Server startup checked not to have rewritten the seeded saves; the login step
  checked to leave the save byte-identical.
* Both servers torn down, the port proven free after each, both disposables
  removed, and containment re-verified.

Exit codes: `0` success, `2` environment, `3` port busy, `4` server start/stop,
`5` request or derivation contradiction, `6` containment violation, `7` fixture
write.

## Re-runnability

Byte-identical across consecutive runs except for four wall-clock surfaces,
which were **measured** by diffing two runs field by field rather than assumed:

| field | where | why it moves |
| --- | --- | --- |
| `executed_at_utc` | `capture-manifest.json` | the capture's own instant |
| `captured_at_utc` | every `request.json` | the step's instant |
| `headers.Date` | every `response.meta.json` | set by the legacy Flask server |
| `form.data` | every `request.json` | the signed envelope embeds a wall-clock `ts`, so its HMAC changes too |

Everything else is byte-identical: every `before.json`, every `after.json`, every
`response.body`, and every other manifest field — including all three outcomes
and the whole gate record. Two captures of this fixture were compared file by
file and then key by key to produce the table above.

## Claim limits

* **Parity covers one transaction against the fresh-player corpus.** No
  progressed-player save exists with the flag at any other value, and **none can
  exist**: the step is a local and is never persisted, so a mid-tutorial save is
  unrepresentable in the legacy save shape. All **8** committed village saves
  carry the key; **7** record `1` and exactly one — `villages/initial.json`, the
  new-player template — records `0`. **No player state was fabricated.**
  *(Correction: an earlier draft of this file claimed "31 village saves, 30
  recording `1`". That was an assertion, not a measurement, and it is wrong on
  both counts — the committed `villages/` directory holds **8** files, counted
  directly. The Apply stage re-measured it and the delivered client suite asserts
  8 with 7 and 1 rather than accepting this sentence.)*
* **The request's exact shape is DERIVED; its effect is ESTABLISHED.** No Flash
  client was executed and none exists to execute here.
* **The boundary arithmetic is not claimed as new work.** It is already pinned by
  `tools/protocol-replay/test_protocol_replay.py:173-179` (`test_tutorial_boundaries`),
  which covers steps 14, 15, 24, 25, 26 and -1 — but against a **stub oracle**
  inside the replay harness, so it is not an executed-legacy oracle. This capture
  adds the executed fixture beside it.
* **The minting transaction is recorded, not reproduced.** It is the anchor for
  the endpoint's second proof half; the endpoint's derived vector is neutral by
  construction and therefore cannot express the ladder at all.
* **No reward is paid and no stored resource moves in the parity transaction**,
  because zero committed tutorial content exists — `tutorial` has **0**
  occurrences in `config/main.json` at any depth and **0** across the normalized
  packages. The capture measures that absence and fails if it ever stops holding.
* **No gate bound is added.** Legacy has no upper bound, no lower bound, and no
  type check; a bound it does not have would be an invented rule. Authoritative
  validation belongs to Server v1 (M13).
* **The three input shapes legacy answers with an unhandled HTTP 500** — a string
  step, a missing step, and a `null` step — are **refused** by the endpoint with
  named codes. This is the line's one deliberate divergence, confined to failure
  handling; for every step legacy *accepts*, the state transition is identical.
* **No pixel parity and no windowed capture.** Nothing is rendered here.