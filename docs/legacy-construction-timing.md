# Legacy construction-timing commands (investigation record)

Status: **investigation complete; no implementation yet.** This record exists so
the next bounded M7 change — *construction timers* — can be proposed without
repeating the investigation, and so the provenance of every value is traceable
before any code is written. It follows the method the `building-upgrade` change
used: committed legacy source first, then executed-legacy probes, with the
boundary between *established* and *derived* drawn explicitly.

No Flash, Ruffle, ActionScript, or browser executed. Every probe ran the real
legacy server on `127.0.0.1:5055` inside a disposable copy under the system temp
root, wrote nothing into the repository, and removed its copy on exit.

## What the commands are

Five dispatcher branches touch construction state, all writing only
`item[3]` (the row timestamp) and `item[6]` (the row's attribute bag). They split
into two coherent clusters.

### Cluster 1 — activation and click-to-build (this deliver line)

| Command | Args | Effect | Source |
| --- | --- | --- | --- |
| `activate` | `[item_index, duration]` | `item[3] = time_now()`; when `duration > 0` sets `item[6]["cp"] = duration`, otherwise **clears the whole attribute bag** `item[6] = {}` | `command.py:412-428`, `engine.timestamp_now()` |
| `add_click` | `[item_index]` | `item[6]["nc"] += 1`, seeding it to `1` when absent | `command.py:525-535`, `engine.py:125-130` |
| `activate_item_click` | `[item_index]` | deletes `item[6]["nc"]` | `command.py:537-548`, `engine.py:132-135` |

The counter is seeded by the *purchase* half, not by these commands: when an
item's config has `clicks_to_build > 0` and the row belongs to the player
(`player == 1`), `engine.map_add_item` writes `attr["nc"] = 0`
(`engine.py:25-28`). That is why the `building-upgrade` fixture's upgraded row
arrives as `[24, 45, 49, <ts>, 0, [], {"nc": 0}, 1]`, and why the upgrade line
records "the construction counter is reported but deliberately not consumed".

**There is no server-side completion rule.** No branch compares `nc` with
`clicks_to_build`; the client decides when the build is finished and sends
`activate_item_click` to clear the counter. Any "remaining clicks" or "remaining
time" display is therefore a client-side derivation from committed config
(`clicks_to_build`, `build_time`, `activation`) plus the row's own state.

### Cluster 2 — friend assistance ("socially in construction")

| Command | Args | Effect | Source |
| --- | --- | --- | --- |
| `buy_si_help` | `[item_index]` | `item[6]["si"] = [0]`, or appends `0` when present (the `0` marks "bought instead of hiring a friend") | `command.py:549-560`, `engine.py:137-142` |
| `finish_si` | `[item_index]` | deletes `item[6]["si"]` | `command.py:561-572`, `engine.py:144-147` |

The `si` bag is seeded by `engine.map_add_item` for items whose config
`properties` carries `friend_assistable > 0` (`engine.py:20-24`) — the
depot-class buildings. This cluster is friend/social behaviour that happens to
live in the same attribute bag; it is separable from cluster 1 and is a
reasonable follow-up (or an M10 social item), not a prerequisite.

## Committed-config facts (all 778 items)

- `clicks_to_build` is `1` for 261 buildings and `0` for 154; the corpus's
  placed buildings (Turret I, Wall I, Command Center, Broken Bridge) are all
  `clicks_to_build = 1`.
- `activation` is `0` for most buildings but `1` (17), `6` (15), `3600` (9),
  `10800` (3), `21600` (8), and `86400` (2) for others — the corpus's placed
  buildings are all `activation = 0`, so the `cp` countdown has no corpus example
  among already-placed rows and a fixture must set it explicitly.
- `build_time` is the per-item build duration (1 for walls, 5 for Turret I and
  the Command Center, 600 for Turret II, 3600 for Command Center II).
- `UPGRADE_SPEEDUP_PRICING = [5, 1]`, `BUILD_SPEEDUP_PRICING = [5, 1]`, and
  `BUILD_SPEEDUP_MIN_TIME = 10` (loaded globals) price a construction *speedup*,
  not a build; no speedup command is in scope for the timer line.
- **The fresh-player corpus has no construction in progress**: every one of its
  40 rows has `attr = {}`, `timestamp = 0`, and `store = []`. Any construction
  fixture must *start* a construction rather than observe one.

## Executed-legacy probe results

Three batches, each in its own disposable copy, seeded from
`tests/saves/fresh-player.json`, every command carrying the neutral
all-zero resource vector, every response `{"result":"success"}` with HTTP 200,
and every resource unchanged.

**A — the counter's whole life, in one batch.** `buy` (Turret I `22` at
`(55, 40)`, the next free key `41`) then `add_click(41)`:

```
placements 40 -> 41, boughtUnits [] -> [22]
row 41 after: [22, 55, 40, 1790687808, 0, [], {"nc": 1}, 1]
```

The purchase seeded `{"nc": 0}` and the click raised it to `1`, which is exactly
the item's `clicks_to_build` — so a one-click building is complete at `nc == 1`.

**B — an activation countdown.** `activate(11, 3600)` on the placed Turret I at
`(58, 48)`:

```
row 11 before: [22, 58, 48, 0,          0, [], {},             1]
row 11 after : [22, 58, 48, 1790687811, 0, [], {"cp": 3600},  1]
```

The row's timestamp becomes the start instant and `cp` the duration, so the
remaining time is `cp - (now - item[3])` — a pure client derivation over data the
server never interprets.

**C — finishing clears the counter, and a zero activation clears everything.**
`add_click(11)`, `activate_item_click(11)`, then `activate(11, 0)`:

```
row 11 after: [22, 58, 48, 1790687814, 0, [], {}, 1]
```

`nc` is gone, `cp` was never set, and the final `activate(…, 0)` re-stamped
`item[3]` and left the bag empty. Note the bag-clearing behaviour: `activate` with
a non-positive duration **destroys** both `nc` and `si`, so a client must never
send it as a "cancel build" without accepting that.

## Provenance: established versus derived

**Established** (committed legacy source, plus the probes above): the five
commands' argument shapes and effects; that only `item[3]` and `item[6]` are
written; that the purchase seeds `nc = 0` and only for `player == 1` items whose
config has `clicks_to_build > 0`; that no server-side completion rule exists; the
`cp`/timestamp shape of an activation; that `activate` with a non-positive
duration clears the whole bag; that every probe answered `success` and left every
resource unchanged.

**Derived and never observed from the Flash client**: that these are the commands
a real construction sends; the `duration` value a client sends to `activate`
(whether it mirrors the item's `activation`, `build_time`, or a speedup-adjusted
figure); whether the client sends `activate_item_click` immediately at
`nc == clicks_to_build` or only after a visual build effect; whether a
`cp` countdown is ever started for an item whose `activation` is `0`; and whether
the friend-assist cluster's `si` counters are ever consumed by a timer display.

## Shape of the next bounded change

A coherent *construction timers* slice is cluster 1 only:

- one intent-only endpoint per command the client needs (`activate`, `add_click`,
  `activate_item_click`), or one `construction` endpoint family sharing the
  delivered pre-execution index resolution and post-execution row read;
- the target tier's `{"nc": 0}` from the delivered `building-upgrade` fixture is
  the natural first fixture, because it *consumes* the exact state the upgrade
  line deliberately left behind and its delta already points here;
- a client construction readout (progress from `nc` / `clicks_to_build`,
  remaining time from `cp` minus `now - item[3]`) plus the flows to start a build,
  add a build click, and finish one;
- the same claim limits as the delivered lines: neutral derived price vector, the
  completion threshold is a client-side rule with no server enforcement, and
  cluster 2 (`buy_si_help` / `finish_si`) stays open.

Deliberate non-goals for that change: the friend-assist cluster, speedups
(`UPGRADE_SPEEDUP_PRICING`), `buy_si_help`/`finish_si` premium paths, and any
server-authoritative timer validation (Server v1 / M13).
