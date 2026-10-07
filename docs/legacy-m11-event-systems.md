# M11 line 5 - `legacy event systems`: legacy measurement contract

Status: **committed investigation**. Nothing is implemented by this document.
It measures the preserved legacy surface so that a later proposal can be
scoped against evidence rather than against a name.

Every figure below was produced by executing or by parsing the committed sources
at the cited paths. Where a figure was asserted and then measured differently,
the difference is recorded in section 0 rather than quietly corrected.

Denominators used throughout:

- **the eleven legacy root modules**: `auctions.py`, `bundle.py`, `command.py`,
  `constants.py`, `engine.py`, `get_game_config.py`, `get_player_info.py`,
  `legacy_command_recorder.py`, `server.py`, `sessions.py`, `version.py`.
- **the 10 genuine save documents**: every `villages/*.json` and
  `tests/saves/*.json` except `manifest.json`.
  `tests/saves/manifest.json` is a **provenance index** (keys `algorithm`,
  `baseline_commit`, `classification`, `fixtures`, `sources`), not a player
  save. An early sweep of this investigation counted it and it matched *every*
  search term; those hits are meaningless and are excluded throughout.

---

## 0. Instrument faults committed by this investigation

Four faults, all mine, all found by reading output rather than by a crash. They
are recorded here because the numbers they produced were briefly on screen and
would otherwise be indistinguishable from measurements.

**0.1 A regex counted a comparison as a mutation.** The first pass harvested
reset keys with `bet\["(\w+)"\]` and reported **19** "keys reset on expiry". The
truth is **13**. The overcount came from two sources: `bet["endDate"]` is
assigned three times and was counted three times, and `bet["idUnit"] !=
auction["unit"]` at `:114` is a **comparison**, not an assignment. Replaced with
an AST walk that only accepts `ast.Store` context.

This is the second recorded instance of that defect class in this project; the
first was `engine.py:62`, recorded in `docs/legacy-unit-movement.md`. The
mistake is worth naming precisely: *reading the token is not writing the field*.

**0.2 A sweep that stopped on the wrong boundary produced a false "never".**
`auctions.py:119` is `if time_now > bet["endDate"]` - **strictly greater**. The
first sweep stepped `beginDate + {0, 59, 60, span-1, span}` and reported that an
auction with a bidder *never expires*. It does not; the sweep ended one second
before the boundary at `endDate+60`. The instrument was wrong, the module was
right. Re-swept across `endDate` itself and `endDate+60`.

**0.3 A label was a tautology.** The no-bidder sweep printed
`STILL THE ORIGINAL AUCTION` by testing
`(endDate - beginDate) == seconds`. A restarted auction has the *same* span, so
that expression is **true before and after a restart** - it could never be false.
It reported `True` on a row where the restart had just happened. Replaced with a
comparison of `beginDate` against the recorded base instant. A tautological check
is worse than no check, because it reads as evidence.

**0.4 A client-value sweep matched on the variable name, not the key.** Looking
for `#\s*bet\s*=\s*data\["bet"\]` found nothing, because the route binds the key
to a differently-named local (`bet_amount = data["bet"]` at `server.py:260`,
`bet_round = data["round"]` at `:261`). The sweep therefore reported two
client-supplied values as **absent** - the exact inverse of the truth, in the
direction that would have removed them from the record. Now matches
`data["<key>"]` wherever it appears and separately reports the local it binds to.

A fifth, smaller one: an arithmetic reconciliation line asserted
`15 created + 6 flags = 21` should equal the 20 keys the probe measured and
printed a bare `False`. The line was wrong, not the modules: `betWinner` is
written only under `checkFinish and isWinning`, so **five** flags are
unconditional. 15 + 5 = 20 served, 21 reachable. Corrected in section 6.

---

## 1. The deliver item names exactly one module, and it is the only cyclical one

The M11 deliver list is `friends`, `visits`, `scores`, `social rewards`,
`legacy event systems`, `special mechanics`. Measured across the eleven modules:

| term | hits | where |
| --- | --- | --- |
| `interval` | **1** | `auctions.py:76` only |
| `expire` | **3** | `auctions.py` only |
| `make_dynamic` | 3 | `get_game_config.py` only - **darts-only**, owned by `godot-darts` |
| `powerup` | 3 | `command.py` only - `buy_powerups`, catalogued as a TODO |
| `timer` | 8 | `command.py` - construction and training, owned by M7/M8 |

`interval` and `expire` have **no occurrence outside `auctions.py`**. The auction
house is therefore not one instance of a class of event systems: it is the
**only** interval- or expiry-driven system in the preserved source. The other
time-dependent surfaces are already owned elsewhere, and this line must not
re-open them.

---

## 2. Finding A - the module cannot construct itself

This is the finding that shapes the line, and it is **not** "the import is
commented out". It is a live defect in the preserved source.

```python
# auctions.py:30-34
30  if not os.path.exists(self.PATH_AH_STATE):
31      os.makedirs(self.PATH_AH_STATE)
32  if os.path.exists(self.FILE_AH_CONFIG):
33      self.auction_state = json.load(open(self.FILE_AH_STATE))
34      self.auctions = self.auction_state["auctions"]
```

- `PATH_AH_STATE` = `AUCTIONS_DIR` = `os.path.join(".", "auctions")` - a
  **directory**, relative to the process cwd.
- `FILE_AH_CONFIG` = `config/auctionhouse.json` - **committed and present**.
- `FILE_AH_STATE` = `auctions/auctions.json` - **absent from the repository**;
  the `auctions/` directory does not exist at all.

Line 31 creates the **directory**. Line 32 tests the **config**. Line 33 reads
the **state document**. On a first run the guard admits the load and the load
has nothing to open.

Executed probe, fresh construction, no state document:

```
config/auctionhouse.json present : True
auctions/auctions.json present   : False
constructing AuctionHouse() ...
  RAISED FileNotFoundError: [Errno 2] No such file or directory: '.\auctions\auctions.json'
after the failure: auctions/ exists True, auctions/auctions.json exists False
                   directory listing of auctions: []
```

**Consequences, and they are worth separating carefully:**

1. Uncommenting `server.py:28-29` would still crash on the first run. The
   commented-out import is therefore **not** the reason the auction house is
   inert; there is a second, independent reason underneath it.
2. The absence of `auctions/` from the repository is **explained**: the module
   could never have created it successfully.
3. The behaviour is unreachable for a stronger reason than "nobody wired it up".
   That is a materially different claim, and it is the kind of thing a proposal
   must not paper over.

**This is not a bug report.** Legacy behaviour is preserved, not repaired. The
defect is recorded as a property of the oracle, because a modern replacement
that *did* bootstrap would be implementing something the original never did.

---

## 3. Finding B - the disabled surface is three complete routes

`server.py` declares exactly **three** commented-out `@app.route` lines, and all
three are auction bets. There are no others, so this is the whole disabled
surface and nothing was missed.

| route | lines | status |
| --- | --- | --- |
| `/dynamic/menvswomen/srvsexwars/bets/get_bets_list.php` | `186-215` | commented out; not registered |
| `/dynamic/menvswomen/srvsexwars/bets/get_bet_detail.php` | `217-246` | commented out; not registered |
| `/dynamic/menvswomen/srvsexwars/bets/set_bet.php` | `248-277` | commented out; not registered |

`tools/endpoint-catalog` already recorded this classification
(`docs/legacy-protocol/endpoints.md`) and also recorded that the module is
commented out at `server.py:27-29`. **This investigation adds the reason**: per
section 2 the module would fail even if the import were live.

Three server-side facts the routes contribute:

- `server.py:202-205` - the list route overwrites `isPrivate`, `isWinning`,
  `won`, `finished` to `0` for every bet, **after** `get_auctions()` has already
  computed them. The list view and the detail view disagree by construction.
- `server.py:229-231` - `checkFinish` is read from the request body and
  defaulted to `0`. It is the **only** thing that can make `betWinner` appear.
- `server.py:260-261` - `bet` and `round` are read from the body and passed
  straight through.

All three are disabled, so none of them is evidence of behaviour. They are
recorded because a proposal must not read them as a contract to satisfy.

---

## 4. Finding C - committed content, fully resolvable, outside every normalizer

`config/auctionhouse.json` is **467 bytes**, committed, and holds **3** auctions:

| uuid | unit | resolved name | level | interval | seconds | price | priceIncrement | betPrice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | 1167 | Blue Steel Bahamut | 1 | 120 | 7200 | 5000 | 1000 | 2 |
| `2` | 1168 | Blue Steel Draggy | 1 | 60 | 3600 | 1000 | 200 | 2 |
| `3` | 1226 | Red Mercury Dragon | 2 | 120 | 7200 | 8000 | 1500 | 2 |

All three unit ids resolve against `packages/game-content/normalized/units.json`
(ids `923..1431`, 429 rows). These are **endgame units**, so this is live content
pointing at real items, not filler.

- The committed `interval` is in **minutes**; `auctions.py:76` converts once:
  `seconds = auction["interval"] * 60`. Executed probe measured
  `endDate - beginDate` = 7200 / 3600 / 7200 - **exact match on all three**.
  Same shape as the `COLLECT_MINUTES` conversion in `godot-building-collect`.
- **All 7 committed keys are read** by the module. There is no dead config key
  here, which is unusual and worth stating plainly.
- **Zero** of the 607 image names in `config/main.json` match
  `auction|bet|bid`. The only top-level key whose content mentions "auction" is
  `items`.
- `config/auctionhouse.json` is a **separate file**, so it is outside the content
  census, whose scope is the 20 top-level keys of `main.json`. There is **no**
  auction output in the normalized package. Normalizing it would be new work and
  is explicitly **out of scope** for this line unless a proposal says otherwise.

---

## 5. Finding D - the bid price is client-dictated, and a bid can lower it

`set_bet` is four statements:

```python
# auctions.py:180-201
def set_bet(self, user_id, uuid, bet_amount, bet_round):
    if uuid in self.auctions:
        ...
        auction["betUsers"].append(user)
        auction["bidders"].append(bidder)
        auction["currentPrice"] = bet_amount + auction["priceIncrement"]
```

Measured across the module: `bet_amount`, `currentPrice`, `beginPrice` and
`betPrice` together have **zero** comparison operators. There is no floor, no
ceiling, no increment check, and no type check.

Executed probe on uuid `1` (committed `priceIncrement` 1000, committed
`price` 5000):

| client `bet` | resulting `currentPrice` |
| --- | --- |
| 1 | **1001** (from 5000 - the price went **down** by 3999) |
| 0 | 1000 |
| -5000 | **-4000** |
| 1000000000 | 1000001000 |

`currentPrice` is a **pure function of the client-sent amount**. This is the
"Bad" pattern from `AGENTS.md` in its purest form: the client dictates a price.

Two further measured facts:

- `bet_round` is **declared and never read**. A client-sent `round` cannot reach
  state; `round` stayed `1`.
- `set_bet` on an **unknown uuid** is a **silent no-op** - no exception, no state
  change, and the route would still have answered `{"result": "success",
  "betResult": "OK"}`.

---

## 6. Finding E - no resource is ever charged, and no settlement ever happens

### 6.1 `betPrice` is a committed price with zero consumers

`auctions.py` contains **zero** occurrences of `gold`, `coins`, `cash`, `wood`,
`steel`, `oil`, `xp`, `mana`, `energy`, `cost`, or `apply_resources`. The only
matching token is `price`, four times. `auctions.py` calls 24 distinct functions
and `apply_resources` is not among them.

The committed `betPrice` (`2` on all three auctions) is written into state at
`:97` and `:137` and **read nowhere**. This is structurally identical to the
`PREMIUM_ACCOUNTS` amount recorded in `godot-darts`: a committed price with
**zero** consumers, where the client could have paired a debit with the action
because `engine.apply_resources` runs a **client-sent** vector *before* the
dispatch chain opens at `command.py:42`.

The difference is worth stating and is not exculpatory: `research_buy_step_cash`
*discards* a client-sent price, whereas this module **ignores** a committed one.
Either way the resource vector is client-controlled, and either way nothing is
validated here.

### 6.2 The "winner" is whichever user the client asks about

`_set_bet_flags(bet, user_id, checkFinish)` mutates `bet` and **returns
nothing** - an earlier version of the probe treated its return as a result dict
and died on `None`.

```python
# auctions.py:160-176
bet["isPrivate"] = 0
bet["isWinning"] = 0
bet["won"] = 1                      # ALWAYS 1, unconditionally
bet["finished"] = timestamp_now() >= bet["endDate"]
bet["betDetail"] = []
if len(betUsers) > 0:
    last = max(0, len(betUsers) - 1)
    user = betUsers[last]
    if user["user_id"] == user_id: # only the LAST bidder
        bet["isWinning"] = 1
    if checkFinish:                # client-sent
        if bet["isWinning"]:
            bet["betWinner"] = user_id
```

Executed probe on an auction with two bidders, `low-bidder` at 100 and
`high-bidder` at 99999:

| `checkFinish` | asked as | `isWinning` | `won` | `betWinner` |
| --- | --- | --- | --- | --- |
| 0 | `low-bidder` | 0 | 1 | - |
| 0 | `high-bidder` | 1 | 1 | - |
| 0 | `nobody` | 0 | 1 | - |
| 1 | `low-bidder` | 0 | 1 | - |
| 1 | `high-bidder` | 1 | 1 | `'high-bidder'` |
| 1 | `nobody` | 0 | 1 | - |

**The bid amounts are never compared.** The last bidder is the winner by
position, and even that is a client-relative answer: asking about
`low-bidder` yields `isWinning = 0` even though they hold a live bid. `won` is
hardcoded `1` for every bet and every user, so it carries no information; and the
list route would have zeroed it anyway (section 3).

`finished` is computed from the **live** clock at `:165`, not from the clock the
caller passed, so it cannot be driven deterministically. Recorded as a property
of the module, not as a defect to fix.

### 6.3 `betUsers` and `bidders` are two identical lists

Measured: `betUsers == bidders` is `True` after bidding. `set_bet` appends the
same four-key dict to both (`:197-198`), with `fb_name` hardcoded to `"Test"` and
`fb_picture` hardcoded to `""` (`:186-188`, `:192-194`). Nothing ever reads
either one for anything but `len()` and `[-1]`.

---

## 7. Finding F - rounds are declared three times and implemented zero times

```python
# auctions.py:119-138
if time_now > bet["endDate"]:                                   # strictly greater
    if len(bet["betUsers"]) > 0 and time_now - bet["endDate"] < 60:
        return False
    difference = time_now - bet["endDate"]
    # TODO: rounds
    count_expired = difference // seconds                      # computed...
    remaining    = difference % seconds
    bet["beginDate"] = time_now - remaining
    bet["endDate"]   = bet["beginDate"] + seconds
    bet["round"] = 1                                           # ...always 1
    bet["betUsers"] = []                                       # 5 more lists cleared
```

- `round` is written as the literal `1` at `:138` and appears in the creation
  literal. It is **never read**.
- `count_expired` at `:127` is computed and **never used**; only `remaining`
  reaches `beginDate`.
- `bet_round` is passed in from the client and **never read**.
- `betUsersPrev`, `prevRoundBidders` and `userRounds` are created, cleared on
  every expiry, and **read by nothing**. They are the residue of the round system
  that was never written.

Executed probe, jumping the clock forward 36,000 s on a 7,200 s auction -
**five** whole rounds:

```
difference = 36000 -> count_expired = 5, remaining = 0
beginDate offset = 36000   endDate offset = 43200   round = 1
```

Five elapsed rounds produce **one** auction. There is no round counter anywhere
in the module and `# TODO: rounds` sits at `:124`.

### 7.1 The expiry boundary, measured on both sides of the grace

`:120` gates the 60-second grace on `len(bet["betUsers"]) > 0`. Measured, same
synthetic clock, identical auctions differing only in whether anyone bid:

| uuid | `seconds` | replaced at | with one bidder |
| --- | --- | --- | --- |
| `1` | 7200 | `endDate + 1` | `endDate + 60` |
| `2` | 3600 | `endDate + 1` | `endDate + 60` |
| `3` | 7200 | `endDate + 1` | `endDate + 60` |

So **having a bidder extends an auction by 60 seconds** - and nothing ever
settles it. `betUsers` gates a settlement window that is never settled.

### 7.2 A changed config rewrites live state and discards bidders

`:114` is the only read of `idUnit`, and it fires **before** any clock check:

```python
if bet["idUnit"] != auction["unit"]:
    return self._create_auction(uuid, auction, seconds, time_now)
```

Executed probe, handing the module a config entry whose unit differs from the
stored one:

```
before: uuid 2 idUnit=1168 betUsers=1
after : uuid 2 idUnit=1167 betUsers=0
```

The stored auction is recreated, its unit overwritten and its **live bidders
discarded**, on the next call. This is a legitimate reading of the code, and it
is also the reason the module is not safe to enable.

---

## 8. Finding G - 16 of 21 state keys have no server-side reader

AST census over the module, counting `ast.Store` as a write and `ast.Load` as a
read (per section 0.1).

- **15** keys created by `_create_auction`
- **6** flag keys written by `_set_bet_flags`
- **21** total

Five have an intra-module read:

| key | read by |
| --- | --- |
| `beginDate` | `_update_auction` |
| `betUsers` | `_set_bet_flags`, `_update_auction` |
| `endDate` | `_set_bet_flags`, `_update_auction` |
| `idUnit` | `_update_auction` |
| `isWinning` | `_set_bet_flags` (reading its own write, same function) |

**Sixteen have zero:** `beginPrice`, `betDetail`, `betPrice`, `betUsersPrev`,
`betWinner`, `bidders`, `currentPrice`, `finished`, `isPrivate`, `level`,
`prevRoundBidders`, `priceIncrement`, `round`, `userRounds`, `uuid`, `won`.

Wire reconciliation: `get_auctions` served **20** keys per bet. That is the 15
created plus the **five unconditional** flags; `betWinner` is the 21st and
appears only under `client-sent checkFinish` **and** a matching last bidder.
**This is an intra-module census.** Every one of these keys is serialised to the
wire by the disabled routes, so "zero reader" means **no server-side reader
only**. Whether the Flash client read any of them is **unverifiable from here** -
the same limitation already recorded for `social_items` and the `MISSION_*`
vocabulary, and it must be repeated rather than inherited silently.

---

## 9. What the corpus says: nothing, and that is measured

Over the **10 genuine save documents**, **zero** carry any of
`auction`, `betUsers`, `bidders`, `currentPrice`, `beginPrice`,
`prevRoundBidders`, `powerup`, `atom_fusion`.

For contrast, **10 of 10** carry darts state, so the search is not simply
mis-wired.

This is expected rather than surprising: the auction state lives in a **separate
document**, `auctions/auctions.json`, which - per section 2 - the module cannot
create. So unlike `godot-unit-instances` and `godot-unit-behaviors`, the absence
here is **not** the reason no fixture can be taken. A different reason applies,
and it is stronger; see section 11.

---

## 10. What is already delivered, and the ownership boundary

| surface | owner | why it must not be re-opened |
| --- | --- | --- |
| `make_dynamic` | `godot-darts` | darts-only date rewriting |
| `soulmixer_speedup` | `godot-unit-queues` | recorded verbatim, implemented not at all |
| `buy_powerups` | `tools/command-catalog` | already catalogued: `args[0] powerup_index (read but unused)`, "branch body is a TODO that only logs" |
| `SOUL_MIXER_POWERUPS_LEVELS` | `build_globals` | 1 of 105 normalized global rows; no `main.json` key matches `power|fusion` |
| the three disabled routes | `tools/endpoint-catalog` | already classified "Commented out; not registered" |

`buy_powerups` deserves one sentence: it is a genuine dispatcher branch and it
**mutates nothing** - `powerup_index = args[0]`, `# TODO`, one `print`. It is the
only stub-shaped branch besides the quest-data TODOs at `:822-824`, and the
catalog already describes it correctly. **This line does not need to measure it
again.**

---

## 11. What this investigation does NOT establish

- **That the auction house ever ran.** Section 2 shows it cannot bootstrap. Every
  Part-2 figure is from a **constructed precondition** - a hand-seeded
  `{"auctions": {}}` - that the real system can never satisfy.
- **That no fixture could ever be taken.** The blocker is **not** a missing
  corpus row. It is that the behaviour has **no request path**: all three routes
  and the module import are commented out. A fixture would have to be produced
  by instantiating `AuctionHouse` directly, which is **not** a transaction any
  client made and would misrepresent a dead surface as a served one. Enabling the
  routes to obtain a fixture is forbidden by `AGENTS.md` ("Do not modify legacy
  behavior merely to make modern implementation easier").
- **What the Flash client displayed.** No image in committed content matches
  `auction|bet|bid`, and absence of a server-side reader is not evidence of
  absence from the client.
- **Any price, cost, fee, or refund.** `betPrice` is committed and unread.
- **Any settlement, winner selection, round history, or award.** Measured absent.
- **Whether the two views' disagreement was ever observed.** All three routes are
  disabled, so `server.py:202-205` is a code reading, not a captured behaviour.

---

## 12. Recommended next step

Propose a **projection-only** capability over the committed auction schedule and
the measured module semantics. Specifically in scope:

1. The **3 committed auctions** with their resolved unit names, levels, prices,
   increments and `betPrice`, reported verbatim from
   `config/auctionhouse.json`.
2. The **derived duration** `interval x 60`, with the minutes-to-seconds
   conversion named and asserted, as `godot-building-collect` did for
   `COLLECT_MINUTES`.
3. The **recorded expiry semantics**: `endDate+1` with no bidder, `endDate+60`
   with a bidder, the literal `round = 1`, and the discarded `count_expired`.
4. The **refusals**, each traceable to a measurement above: no price is charged,
  no round advances, no winner is derived, `checkFinish` is client-controlled,
  and the client-dictated `currentPrice` is not reproduced as parity.
5. The **bootstrap defect** recorded as a property of the oracle, so a future
   implementation cannot silently "fix" it into a claim of parity.

Explicitly out of scope: normalizing `auctionhouse.json` into the content package
(section 4), any route, any `apps/compat-api/**` change, any live phase, and any
element of `special mechanics` - which is the sixth and final M11 item and needs
its own investigation before it may be proposed.

---

## 13. Corrections to earlier records

- **No earlier record claims anything false about the auction house.** The
  endpoint catalog's "Commented out; not registered" and its note that the
  module is commented out at `server.py:27-29` are both correct. This
  investigation adds the reason underneath, and adds no correction.
- **The content census's scope is not a gap here.** `auctionhouse.json` is a
  separate file from `main.json`, so its absence from the 20 census keys and from
  the normalized package is **by construction**, not an oversight. Recorded so a
  later line does not "fix" it as though it were a defect.
- **An instance of the byte-form defect class.** Section 9's first sweep counted
  `tests/saves/manifest.json` as a save document. It is a provenance index and
  matched every term searched. Any future corpus census in this repository must
  exclude it by name, and this is recorded as the second time an index document
  has been mistaken for data in this project.