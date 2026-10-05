# Legacy contract: M10 `rewards`

**Status:** investigation. No proposal, no code.
**Scope:** the M10 deliver item `rewards` — the milestone's **last** undelivered item —
recorded before any implementation, per the project's standing rule that a committed
investigation precedes a proposal.
**Verdict:** **`rewards` is a REAL, UNDELIVERED surface. It is NOT a closure.** Two
branches grant something, both mutate private state, both take the granted item from the
client, and committed reward schedules exist to reason about. Nothing owns any of it.

This is the opposite verdict to `death` and `mission completion`, and the difference is
measured rather than assumed: those two had no mechanism to find, this one has two.

---

## 1. The two branches that grant

| branch | span | grants | charges |
| --- | --- | --- | --- |
| `weekly_reward` | `command.py:345-363` | a **client-sent** `item_id`, placed on the map | **nothing** |
| `win_daily_bonus` | `command.py:444-463` | a **client-sent** `item`, stored | **nothing** |

Both are two-armed or two-step, and both are reproduced here verbatim because the arms are
where the behaviour lives:

```python
elif cmd == "weekly_reward":                              # command.py:345
    if len(args) > 4:                                      # command.py:346
        item_index = args[0]
        item_id = args[1]
        x = args[2]
        y = args[3]
        playerID = args[4] # player team

        map_add_item(map, item_index, item_id, x, y, player=playerID)
        bought_unit_add(save, item_id)

        print("Won", str(get_name_from_item_id(item_id)))
    else:
        print("Won resources")

    # Disable Monday bonus until next Monday
    save["privateState"]["timeStampMondayBonus"] = time_now
    # Advance Monday bonus
    save["privateState"]["weeklyRewardIndex"] = (save["privateState"]["weeklyRewardIndex"] + 1) % get_weekly_reward_length()
```

`weekly_reward` therefore has **two arms**: with **five or more** arguments it places a
client-sent item on the map at a client-sent index, cell and player; with **fewer** it
prints *"Won resources"* and **grants nothing at all**. **Both** arms stamp
`timeStampMondayBonus` and advance `weeklyRewardIndex`, so the cursor moves whether or not
anything was granted. No resource is read or written in either arm.

`win_daily_bonus` takes `item = args[0]` and `next_id = args[1] + 1`, wraps `next_id` to `1`
when it exceeds `5`, stamps `timestampLastBonus`, sets `bonusNextId`, and stores the item only
when `item > 0`.

**Neither branch derives what to grant.** Both take the item id from the client.

## 2. Committed reward schedules exist, and ten of eleven are read by nothing

Reader census over all **eleven** top-level legacy modules, with the raw site printed before
any absence verdict is believed:

| schedule | occurrences | read? |
| --- | --- | --- |
| `MONDAY_BONUS_REWARDS` | **1** | **yes — for its length only** |
| `DAILY_GOLD_REWARDS` | **0** | no |
| `ALLIANCE_DAILY_BONUS_REWARDS` | **0** | no |
| `REWARDS_CHAPTERS` | **0** | no |
| `REWARDS_QUESTS` | **0** | no |
| `PRIZE_COLLECTIONS_CASH` | **0** | no |
| `RECRUITMENT_PRIZE` | **0** | no |
| `NEWFRIENDS_REWARD_ID_UNIT` | **0** | no |
| `NEWFRIENDS_REWARD_SCALE_UNIT` | **0** | no |
| `NEWFRIENDS_REWARD_DESCRIPTION` | **0** | no |
| `MANA_REWARD_PER_LEVEL` | **0** | no |

All eleven live under `config["globals"]`. **This is a statement about the preserved
server's own source**: the whole `globals` object is *served* to clients, so a Flash client
could have read any of them, and that is unobserved. No server branch consumes ten of the
eleven at all.

## 3. The one schedule that is read, and the trap inside it

```python
def get_weekly_reward_length() -> int:                   # get_game_config.py:195
    # This would be better if it was called at the start, instead of being calculated every time
    rewards = __game_config["globals"]["MONDAY_BONUS_REWARDS"]
    length = 1
    for reward in rewards:
        value = reward["value"]
        if type(value) == list:
            length = max(length, len(value))

    return length
```

The committed schedule:

| rung | `type` | `value` |
| --- | --- | --- |
| 0 | `g` | `2500` |
| 1 | `u` | `[1055, 1033, 1046, 1063, 1198]` |
| 2 | `c` | `5` |

**The schedule has three rungs and the rotation length is five.** The length is
`max(len(value))` over rungs whose `value` is a **list**, and only rung 1 qualifies — its
item list has five entries. Counting the rungs, the intuitive reading, gives **3**; the
function returns **5**. A line delivered on this must derive **5**.

So `weeklyRewardIndex` cycles `0..4`.

**The function returns an `int`.** It cannot express a grant: no code path returns a rung, an
item, or an amount. This is the single most important sentence in this document — a grant is
**representable** but not **derivable** by the preserved server.

**All five unit ids resolve against committed content**, so the item list names real things:

| id | name | type | `img_name` | `clicks_to_build` | `build_time` |
| --- | --- | --- | --- | --- | --- |
| 1055 | Mr. Treat | `u` | `1055_mr_t_m` | `0` | `0` |
| 1033 | Mr. Cigar | `u` | `1033_mr_cigar` | `0` | `0` |
| 1046 | Flamethrower | `u` | `1046_flamethrower_m` | `0` | `0` |
| 1063 | Bazooka IV | `u` | `1063_bazooka_4_m` | `0` | `0` |
| 1198 | Nebular Knight | `u` | `1198_nebular_horse_rider` | `0` | `0` |

### The type letters are undecoded

The schedule's own vocabulary is `g`, `u`, `c`. Searching every module for any decoder:

| search | hits |
| --- | --- |
| `"g"` mapped to `gold`/`coins` | **0** |
| `"c"` mapped to `cash` | **0** |
| `"u"` mapped to `unit` | **0** |
| any single-letter dict key | **0** |
| a `type == "x"` branch | **0** |
| `reward["type"]` | **0** |

**No branch maps `g` or `c` onto a stored resource slot.** Reading `g` as gold and `c` as
cash would be an invention, not a reproduction, and this document does not make it.

## 4. Both cursors are write-only

| field | sites | readers outside its own write |
| --- | --- | --- |
| `weeklyRewardIndex` | **1** (`command.py:363`) | **0** |
| `bonusNextId` | **1** (`command.py:455`) | **0** |
| `timeStampMondayBonus` | 2 (`:361` live, `:915` **commented out** in `fast_forward`) | **0** |
| `timestampLastBonus` | 2 (`:454` write, `:914` `fast_forward` read-modify) | **0** |

`weeklyRewardIndex` is read only by the expression that overwrites it.
`bonusNextId` has exactly one site in the whole preserved server, and it is a pure write.

So neither cursor **decides** anything. They record *that* a reward was taken, never *what
it should be* — which is the same write-only shape `godot-research` delivered for the three
research counters.

## 5. Seven reward-adjacent fields exist in every save and in no source

| field | source occurrences | in committed saves |
| --- | --- | --- |
| `attacksSent` | **0** | **39 / 39** |
| `attacksPack` | **0** | **39 / 39** |
| `attacksReceived` | **0** | **39 / 39** |
| `bestUnit` | **0** | **39 / 39** |
| `betWin` | **0** | **39 / 39** |
| `spyings` | **0** | **39 / 39** |
| `strategy` | **0** | **39 / 39** |

These are **save-only**: written by some client the repository does not contain, read by
nothing the repository does contain. They are reported here as recorded state with no
consumer, and no rule is derived for any of them.

`level_ranking_reward` — 50 committed entries covering levels 1..50, with `cash`, `level`
and `units` keys — has **zero** occurrences across all eleven modules. The
`economy-schedules-normalization` capability owns it **as normalized content**; nothing owns
it **as gameplay**, and owning the table is not the same as delivering its effect.

## 6. The corpus is genuinely exercised

| field | present | recorded values |
| --- | --- | --- |
| `weeklyRewardIndex` | 39 / 39 | `0` ×32, `1` ×5, `2` ×1, `3` ×1 |
| `bonusNextId` | 39 / 39 | `0` ×13, `2` ×24, `3` ×2 |
| `timeStampMondayBonus` | 39 / 39 | `0` ×32, non-zero ×7 |
| `timestampLastBonus` | 39 / 39 | `0` ×13, non-zero ×26 |

**Seven documents carry `weeklyRewardIndex > 0`** — `Nerri.json` at 2, `Neutral.json` at 3,
and five more at 1 — and **twenty-six carry `timestampLastBonus > 0`**, so both reward paths
have genuinely run against committed documents. Unlike most M10 lines, this one is not
blocked by a fresh-player corpus.

## 7. The grant helpers, and what a repeat grant does

```python
def add_store_item(map: dict, item: int, quantity: int = 1):   # engine.py:70
    itemstr = str(item)
    if itemstr not in map["store"]:
        map["store"][itemstr] = quantity
    else:
        map["store"][itemstr] += quantity

def bought_unit_add(save: dict, item: int):                     # engine.py:86
    boughtUnits = save["privateState"]["boughtUnits"]
    if item not in boughtUnits:
        boughtUnits.append(item)
```

They differ, and the difference is a save-shape fact rather than a rule: `add_store_item`
**accumulates** a quantity, so a repeat daily grant increments the stored count, while
`bought_unit_add` **deduplicates**, so a repeat weekly grant of an already-owned item leaves
`boughtUnits` unchanged.

`map_add_item` is already delivered and owned by `godot-building-placement`, and it derives
two `attr` fields from committed content (`attr["si"]` from `properties`, `attr["nc"]` from
`clicks_to_build`) — all five weekly-reward units record `clicks_to_build` `0`, so the
derived counter is `0` for every one of them.

## 8. Ownership: nothing owns this

| component | owner |
| --- | --- |
| `level_ranking_reward` **as normalized content** | `economy-schedules-normalization`, `content-validation` |
| quest reward | `godot-quests` — already records *no* quest reward is paid |
| collection prizes | `godot-unit-collection`, `quest-normalization` |
| `weeklyRewardIndex`, `bonusNextId`, `timeStampMondayBonus`, `timestampLastBonus` | **none** |
| `weekly_reward`, `win_daily_bonus` | **none** |
| `MONDAY_BONUS_REWARDS`, `DAILY_GOLD_REWARDS`, the other nine | **none** |

Ownership was tested by **role name as well as source identifier**, for the reason
`docs/legacy-m10-death.md` §6.2 and `docs/legacy-m10-mission-completion.md` §9.5 each record
in their own words: a literal grep against prose specifications is wrong for the wrong
reason, and it has now failed that way twice.

## 9. Three measurement defects found while measuring this

### 9.1 A reader/writer census inverted by a missing quote

My first classifier matched a write as `\[<field>"\]\s*=` — a subscript with a quote on the
**closing** side only. Real sites are `save["privateState"]["timeStampMondayBonus"] = v`,
with a quote on **both** sides, so the pattern never matched and every such write fell
through to the quoted-**read** label. `timeStampMondayBonus`, `bonusNextId`, `questsRank`
and `collections` were all reported as *read* when they are *written*.

This is the **same defect class** as the classifier that inverted the mission-completion
census, reached from a different direction, and it is the reason the fixed probe prints the
raw sites rather than only a verdict: a wrong verdict and a right one look identical
otherwise.

### 9.2 A hardcoded field name stopped the probe rather than reporting wrong

The item-resolution step indexed `row["legacy_id"]` and raised `KeyError`. The raw
`config/main.json` items use **`id`**; `legacy_id` is the *normalized package's* field name.
The probe now measures which field the document uses. Recording this because a crash is
visible and cheap, while the same mistake inside a `try/except` would have shipped an empty
resolution table that read as "none of these ids resolve".

### 9.3 An assumption worth stating because it is false

It was tempting to read the daily wrap bound (`> 5` at `command.py:451`) as derived from
`DAILY_GOLD_REWARDS`, which has exactly five entries. **It is not derived.** It is a
hardcoded literal in a branch whose only reader of that schedule does not exist. The two
numbers agree, and the agreement is a coincidence. Unlike the weekly bound, which *is*
derived and is the interesting case, nothing enforces this one.

## 10. What a line here would and would not be

A `godot-rewards` line would be **neither a pure refusal nor a routine feature**. It would:

- **deliver** the two cursors as projected state, and the **derived** weekly rotation length
  of **5** — including that it comes from the item list, not the rung count;
- **refuse** to derive the grant itself, because the only reader of the schedule returns an
  `int`, and because both cursors have zero readers;
- **refuse** to decode `g` and `c` into resources, since nothing does;
- **record** the client-sent grant as a **divergence** rather than reproducing it, in the
  `damage` line's manner;
- record **ten** reward schedules with zero consumers and **seven** save-only fields with no
  rule.

That is a real deliverable with real refusals, and it is the shape of `damage` (the `magics`
counter) rather than the shape of `death`.

## 11. Claim limits

- Everything above is a measurement of the **preserved server's source**, across all eleven
  top-level legacy modules. The served `globals` object contains all eleven schedules, so a
  Flash client could have read any of them; **no claim is made about what it did**, and none
  about what a player ever saw.
- **No grant is claimed to have existed on the server side.** The finding is that the server
  accepted a client-dictated grant and recorded only that one was taken.
- **The weekly rotation length of 5 is derived from committed content** and is the one
  reward number this document derives. The **daily** wrap bound of 5 is a **hardcoded
  literal** (§9.3) and is deliberately **not** attributed to `DAILY_GOLD_REWARDS`.
- `g` and `c` are **not** decoded. Reading them as gold and cash would be an invention.
- The claim that both cursors are write-only is a claim about **server code**. A client
  reading `weeklyRewardIndex` out of its own save to decide what to send next is entirely
  plausible and unobserved.
- The seven save-only fields are reported with **no rule**. Their origin is a client not in
  this repository.
- `level_ranking_reward` is **owned as content and undelivered as gameplay**. Those are
  different states and this document does not collapse them.
- The corpus figures in §6 are counts of **recorded values**, and establish that the paths
  ran. They do not establish what was granted, because the grant was client-sent.
- **No executed-legacy fixture is captured in this investigation**, and none is fabricated.
  A capture is available and expected on the Apply stage; §6 identifies candidate corpora
  with advanced cursors and room to place or store.
- **No Flash, Ruffle, ActionScript, or browser executes** in any measurement here, and **no
  network is used**.