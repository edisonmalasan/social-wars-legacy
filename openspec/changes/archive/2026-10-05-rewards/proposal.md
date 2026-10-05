# Proposal

## Why

M10's deliver list ends at `rewards`, and the committed investigation
**`docs/legacy-m10-rewards.md`** (PR #302, merged `50b2700`) established that this
is a **real, undelivered surface** — the opposite verdict from `death` and
`mission completion`, and measured rather than assumed. Those two had no
mechanism to find. This one has two branches that mutate state and grant
something, and **nothing in the repository owned any of it**.

**Two branches grant, both from a client-sent item id.**

| branch | span | grants | charges |
| --- | --- | --- | --- |
| `weekly_reward` | `command.py:345-363` | a **client-sent** item, placed on the map | **nothing** |
| `win_daily_bonus` | `command.py:444-463` | a **client-sent** item, stored | **nothing** |

`weekly_reward` has **two arms** on `if len(args) > 4:`. With five or more
arguments it places a client-sent item at a client-sent index, cell and player;
with fewer it prints *"Won resources"* and **grants nothing at all**. **Both** arms
stamp `timeStampMondayBonus` and advance `weeklyRewardIndex`, so the cursor moves
whether or not anything was granted. No resource is read or written in either arm
— checked mechanically against the seven stored slots, not asserted.

**Both cursors are write-only.** `weeklyRewardIndex` has exactly one site and
`bonusNextId` has exactly one site, and in both cases the site *is* the write.
They record *that* a reward was taken and never *what it should be* — the same
shape `godot-research` delivered for the three research counters.

**And the decisive finding is stronger than "no reader". Both cursors are
mis-sized against their own schedules, so neither can address it.** The
investigation derived a weekly rotation length of **five** from a schedule with
**three** rungs: the length is `max(len(value))` over rungs whose `value` is a
**list**, and only the unit rung qualifies, so counting the rungs — the intuitive
reading — gives 3 and the function returns 5. The cursor therefore ranges over
`0..4` while the schedule is addressable at `0..2`:

| cursor position | rung at that position |
| --- | --- |
| 0 | `type='g'`, `value=2500` |
| 1 | `type='u'`, `value=[1055, 1033, 1046, 1063, 1198]` |
| 2 | `type='c'`, `value=5` |
| **3** | **no rung — the schedule has 3 entries** |
| **4** | **no rung — the schedule has 3 entries** |

**Two of five cursor positions name nothing at all.** This is not a gap to be
filled by a derivation; it is a cardinality mismatch between two committed
pieces of the same feature. And it is **reachable from committed state without
any fabrication**: `Neutral.json` records `weeklyRewardIndex` **3**, so one
recorded transaction lands on **4**, and `Nerri.json` records **2** and lands on
**3**. Both are unaddressable.

The daily side has the same shape for a different reason. The bound at
`command.py:451` is a **hardcoded literal** `> 5 → 1`, so the cursor reaches
`1..5`, while `DAILY_GOLD_REWARDS` — which has **zero** consumers — is addressable
at `0..4`. Position **5** is out of range, and position **4** of that schedule is
**`0`**, so any index→amount derivation a reader would have inherited would pay
**nothing** on that day. The literal's agreement with the schedule's five entries
is a **coincidence of value distribution, not provenance**, and the design retains
the rejected content-derivation alternative so a later reader cannot mistake it
for a derivation.

**Ten of the eleven committed reward schedules have zero consumers** across all
**eleven** top-level legacy modules, and the schedule's own type letters `g`, `u`
and `c` are **undecoded** — six independent searches for a decoder all return
zero, so reading `g` as gold and `c` as cash would be an invention rather than a
reproduction. Seven `privateState` fields (`attacksSent`, `attacksPack`,
`attacksReceived`, `bestUnit`, `betWin`, `spyings`, `strategy`) are **save-only**:
present in **39 of 39** committed documents, in **zero** source lines.
`level_ranking_reward` — 50 entries — is owned **as normalized content** by
`economy-schedules-normalization` and **undelivered as gameplay** by anyone;
those are different states and this line does not collapse them.

Unlike most M10 lines, **this one is not blocked by a fresh-player corpus.**
Seven documents carry `weeklyRewardIndex > 0` and twenty-six carry a non-zero
`timestampLastBonus`, and two of the seven advance to a position the schedule
cannot address.

## What Changes

- **A new `godot-rewards` capability whose delivered surface is the two cursors
  and their two derived bounds, and whose primary finding is that neither cursor
  can address its schedule.** The capability name follows the roadmap line so the
  milestone cursor stays meaningful; nothing in it grants a reward, and the
  addressability refusal is enforced structurally rather than stated in prose
  (design D7).
- **A compatibility-service operation carrying intent only.** The client sends an
  action and a save id; the server derives the cursor transition from its own
  recorded state. Every grant-shaped argument the preserved branches accepted —
  the item id, the map index, the cell, the player, the next id — is **refused by
  name** rather than ignored, because silently deriving a different value from an
  accepted one is the failure mode the project's `apply_client_state(...)` rule
  exists to prevent.
- **Nothing is granted, and the proof of that is four-part.** No map row is added,
  no `boughtUnits` entry is appended, no storage entry is created, and **no**
  stored resource moves — checked on every success, so "this grants nothing" is a
  verified property rather than a claim.
- **Both client-sent values are recorded as divergences and neither is reproduced
  as parity.** The item is the obvious one. The **next id is the sharper one**,
  because the daily branch computes `next_id = args[1] + 1` from a client-supplied
  cursor while the service derives it from the recorded one — a case where the
  legacy server's trust in the client is directly observable in its own source.
- **The weekly length is delivered as derived and the mismatch is reported beside
  it.** An index→rung selection is refused, and no delivered helper performs one.
- **The daily bound is delivered as the recorded hardcoded literal it is**, with
  the rejected `DAILY_GOLD_REWARDS` derivation retained in the design (D4).
- **The two-armed weekly branch is reported, not reproduced.** The arm is selected
  by the client's *argument count*, so the service has no arm; it reports the
  boundary and the per-arm effect and never places a row.
- **The instant stamp is written and no eligibility gate is derived from it.**
  `timeStampMondayBonus` has one live write and its only other occurrence is
  commented out; it has no reader, so no window, reset rule, or "already claimed"
  test exists to reproduce, and none is invented.
- **Ten zero-consumer schedules, seven save-only fields, and the undecoded type
  letters are reported with no rule**, and `level_ranking_reward`'s split
  ownership is stated rather than resolved.

## Impact

- **Affected capability:** `godot-rewards` (**new**).
- **Referenced, not reimplemented:** `godot-building-placement` owns
  `map_add_item`; `godot-unit-instances` owns `boughtUnits`; `godot-stored-item-placement`
  owns storage grants and the `add_store_item` accumulation semantics;
  `godot-research` owns the write-only-counter precedent this line follows;
  `godot-unit-collection` and `godot-quests` own collection prizes and quest
  rewards; `economy-schedules-normalization` and `content-validation` own
  `level_ranking_reward` **as content**. This line touches none of them and
  duplicates none of their rules.
- **Affected code:** one capture script and its parity test under
  `apps/compat-api/`, the compatibility service route and its envelope module, a
  typed read-only projection and hermetic suite under `apps/client-godot/`, and a
  live phase registered in `verify-boot.ps1`.
- **Evidence:** an executed-legacy fixture under `tests/fixtures/`, and a
  deterministic `rewards-report-v1` report under `apps/client-godot/evidence/`.
- **No Flash, Ruffle, ActionScript, or browser executes**, and every network call
  is loopback.

## Non-goals

- **Granting, selecting, pricing, or displaying any reward.** A grant is not
  merely underivable here — at 2 of 5 weekly positions and 1 of 5 daily positions
  there is no schedule entry to select, and everywhere else nothing reads the
  schedule to select it.
- **Decoding the type letters `g`, `u`, or `c`.** No branch maps `g` or `c` onto a
  stored resource slot; the mapping is recorded as unread vocabulary.
- **Charging or crediting any resource.** Measured absent across both arms, so any
  amount would be invention.
- **An eligibility, cooldown, window, or "already claimed" rule** for either
  reward. No reader exists to derive one from.
- **Deriving the weekly or daily price, item, or amount from committed content.**
  The five committed unit ids resolve, which makes a grant *representable*; it
  does not make one *derivable*, and this line delivers the distinction rather
  than the grant.
- **Fixing the cardinality mismatch.** Correcting the weekly length to 3 or
  extending the schedule to 5 would be authoring content or correcting the
  preserved server, neither of which this line does.
- **Quest rewards, collection prizes, chapter rewards, or ranking rewards.** Those
  are owned or out of scope; §5 of the investigation records which is which.
- **Combat rewards or honour.** No committed source from which to derive any.
