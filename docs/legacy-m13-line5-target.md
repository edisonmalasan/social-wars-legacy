# M13 line 5 - target selected: the reward cursors become authoritative

## 0. What this file is

This file **supersedes section 5** of `docs/legacy-m13-line5-candidates.md`, which declined to
name a target and stated the reason as a measurement gap: criteria 3 and 4 could not be applied
because the dispatched/undispatched split had not been reproduced.

That gap is now **closed by measurement**. This file names the target, and the record it
supersedes is **not edited** - it is retained as written.

It is a **selection** record. It is not a proposal, and nothing here is authorised.

## 1. The working dispatch probe, and the figure it produces

The two discarded probes in the superseded record failed for two different, recoverable reasons.
Recording both because each is a trap:

- **Fault 1** (confident zero): the builders take **required positional arguments**, so every call
  raised `TypeError` and a bare `except: continue` swallowed all 48.
- **Fault 2** (same symptom, different cause): `importlib.import_module` was handed a path with a
  Windows separator, so every module failed to load - a **path** fault, not an argument fault.
- **Fault 3** (found while repairing, and the substantive one): with the path fixed, all 48 calls
  raised `EnvelopeError`. The builders **validate**, and synthetic arguments are exactly the
  refused shapes. So *no* amount of argument synthesis can produce a valid batch - the envelope
  modules refuse precisely what an automated probe tends to send.

That is why the recorded investigation's method was to **execute the builders**, and why the only
sound way to execute them is to let a **real driver** supply valid arguments.

The probe therefore hooks the integration point and runs the existing suite:

- wrap `compat_legacy.LegacyBoot.execute_commands`;
- for each call, read the branch name out of `envelope["commands"][i][1]` - the actual batch a
  v0 route is about to dispatch;
- run the **whole committed compat suite** as the driver, which is a known-good exerciser of all
  24 v0 routes.

### Result at HEAD

| quantity | value |
|---|---|
| compat tests run | **3077** |
| errors / failures | **0** / **0** |
| distinct branch names observed in a real batch | **39** |
| total branch occurrences observed | **1074** |
| named branches in `command.py` | **63** |
| **never dispatched** | **24** |

**39 dispatched / 24 undispatched - reproduced.** The inherited figure in
`docs/legacy-m13-unrouted-branches.md` §2.1 is confirmed by measurement, and this probe also
independently confirms *why* the earlier `40 / 23` was wrong: `buy_mana_new` appears in the never-
dispatched list, so the `NO_OP_COMMAND` correction was right.

The 24 never dispatched, quoted in full so the figure can be checked:

```
add_inventory_item, add_xp_unit, batch_remove, buy_mana_new, buy_offer_pack,
buy_powerups, buy_si_help, fast_forward, finish_si, first_time_marketplace,
flash_debug, orient, ping, pop_unit, push_queue_unit2, push_unit,
remove_inventory_item, rt_open_graph_unit, set_resource_allies, set_variables,
soulmixer_speedup, store_add_items, trade_resource, unit_collections_completed
```

`tools/route-coverage/` is **not** contradicted. It answers a different question - whether a
handler's *source* cites a branch with a resolvable `command.py:NNN` span - and its conservative
census (24 cited / 39 not) is a citation count, not a dispatch count. Both are correct; they are
about different things.

## 2. The pool, now that the split is measured

**39** dispatched, of which **5** carry an authoritative v1 route (`collect`,
`complete_collection`, `buy_magic`, `use_magic`, `end_attack`). So the pool of
**dispatched-but-non-authoritative** branches - the ones where a v1 route would **replace a live
v0 route** rather than invent a surface - is **34**.

The **24** never-dispatched branches are a different pool and are **out of scope for a v1
authority line**: they have no client surface to replace, so a v1 route for one would be a new
client feature, which is out of milestone order.

## 3. Criterion 1 is dead, and criteria 2-5 select anyway

Criterion 1 ("a content-anchored derivation exists") remains dead for all remaining branches - the
superseded record's finding, which this measurement does not change and does not need to.

What this measurement changes is that **criteria 2-5 can now be applied at all**. Scored over the
34:

| criterion | best in pool |
|---|---|
| C2 stored outcome already server-computed | **the two reward branches** |
| C3 executed-legacy fixture depth | **the two reward branches** - 7 recorded steps |
| C4 a live v0 route to replace | **the two reward branches** - `/v0/reward` |
| C5 measured unbounded / client-dictated input | **the two reward branches** - the cursor |

One candidate wins all four, and it wins them for the *same underlying reason*.

## 4. Why the reward branches, which section 1 withdrew

The superseded record withdrew `win_daily_bonus` and `weekly_reward` as candidates. That withdrawal
was scoped, in its own §6, to **candidacy for a client-facing line** - and its own words were
that both "remain **non-authoritative** for v1".

That is exactly what this line is about, so they return to the pool. The distinction is the whole
finding: **delivered is not authoritative**, and `/v0/reward` is a route that *refuses to grant*
while leaving the branch's one server-computed quantity - the cursor - to be whatever the client
last sent.

### 4.1 The cursor is genuinely server-computed arithmetic, on a client-dictated input

`command.py:444-463`:

```
item    = args[0]
next_id = args[1] + 1
if next_id > 5: next_id = 1
privateState["timestampLastBonus"] = time_now
privateState["bonusNextId"] = next_id
```

The **modulo-like clamp and the successor arithmetic are the server's own** - they are not
client-sent. But the *input* to them is: `args[1]` is whatever the client last sent, and
`timestampLastBonus` has **no reader anywhere**, so nothing bounds how often this may run. The
captured fixture executes this rather than arguing it: an oversized next id moves the recorded
cursor **backwards**, `4 -> 1`.

That is a real, closable authority defect and a genuine C2+C5 hit, which nothing else in the pool
offers.

### 4.2 The one-based index is corroborated by the corpus

This matters because the **level curve's** index base was contested, guessed wrong once, and had to
be corrected. Here the corpus settles it.

Measured across the **10** committed save documents carrying a reward cursor:

- `bonusNextId`: **`0` in 7 documents, `2` in 3** - no document records a value above `2`.
- `weeklyRewardIndex`: **`0` in 8, `2` in 1, `3` in 1**.

The branch can only ever store **1..5** (`args[1] + 1`, clamped). So a stored **`0` is off the
ladder** and is a fresh-player seed meaning "the first row is next". That is consistent with the
**one-based** reading and inconsistent with zero-based, exactly as `docs/legacy-m13-unrouted-branches.md`
recorded - and here the corpus, not a guess, is the evidence.

The committed schedule agrees: `DAILY_GOLD_REWARDS = [100, 250, 500, 1000, 0]` at
`packages/game-content/normalized/globals.json:778` - **five** entries, matching the branch's
hardcoded literal `5`. Its fifth entry is `0`, a **zero payout**, which is why the delivered
line records one of five daily positions naming no rung.

### 4.3 The divergence is structural, and is recorded rather than reproduced

`command.py` credits **nothing** on either branch: the daily arm's grant is
`bought_unit_add` + `add_store_item` on a **client-sent item id**, and its non-granting arm only
`print`s. A v1 route that applied `DAILY_GOLD_REWARDS` would therefore **diverge from the
oracle** - it would pay where the oracle pays nothing.

The line's decision is to take the **authority improvement that is derivable** (derive the
successor from the *stored* cursor, never the client-sent one) and to **not** invent the payout,
recording the divergence in the same shape line 4 used. The ladder stays unread, exactly as
`DAILY_GOLD_REWARDS` has zero legacy readers today.

## 5. Target

**M13 line 5 = the two reward branches, `win_daily_bonus` (primary) and `weekly_reward`, behind a
single `POST /v1/reward`, replacing the authority of `/v0/reward`.** One route, one closed action
set, mirroring `/v1/magic`'s `operation` shape, which already covers two branches.

It is a **mixed line**: partly a derivation (the successor from the stored cursor) and partly a
refusal (every grant-shaped input, the unread ladder, and the absent eligibility rule). Both halves
are established by the executed fixture; neither is invented.

## 6. Claim limits

- **No proposal is authorised by this file.** It is a selection record.
- The **39 / 24** split is now **measured** at HEAD by a probe that runs the whole committed suite
  (3077 tests, 0 errors, 0 failures). The tool's citation counts answer a different question and
  are quoted with it attached.
- The corpus distributions (**10** documents; `bonusNextId` 7×`0`, 3×`2`; `weeklyRewardIndex`
  8×`0`, 1×`2`, 1×`3`) are **measured**, and the one-based reading is **derived from them**, not
  asserted - with the zero-based alternative rejected on the same evidence rather than left open.
- **No payout is claimed or derived.** `DAILY_GOLD_REWARDS` and `MONDAY_BONUS_REWARDS` have zero
  legacy readers; the daily ladder's type letters are the **undecoded** letters the delivered line
  already reports.
- **No eligibility, cooldown, daily-window or already-claimed rule is claimed**, because
  `timestampLastBonus` has **no reader** and there is nothing in the preserved server to reproduce.
- The pool figure **34** follows from **39 dispatched − 5 authoritative**; the **24** never-
  dispatched branches are out of scope for an authority line and are not ranked against it.
- Claim **no ordinal** over inherited figures found wrong; the recorded instances disagree over
  different scopes.
- **Nothing about what the Flash client sent.** No client was executed. No Flash, Ruffle,
  ActionScript, or browser ran; the compat suite used no network beyond loopback.

## 7. Corrections carried forward

- `docs/legacy-m13-line5-candidates.md` §5 ("no target is named here") is **superseded** by this
  file. That record is **not edited**.
- §5's two instrument faults are **corrected here** rather than merely listed: there were **three**
  (the path-separator fault, `Fault 2`, was not visible until the argument fault was fixed, and the
  `EnvelopeError` finding, `Fault 3`, is the substantive one).
- `docs/legacy-m13-unrouted-branches.md` §2.1's **39 / 24** is **confirmed by measurement**. The
  record is not edited.
- `docs/legacy-m13-line4-candidates.md` §5 ranks 2 and 3 stay **withdrawn as client-facing
  candidates** and are **restored as M13 authority candidates** by this file. The record is not
  edited.