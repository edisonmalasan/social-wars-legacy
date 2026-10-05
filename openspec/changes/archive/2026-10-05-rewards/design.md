# Design

## D1 - The delivered surface is the two cursors; the refusal is that neither cursor can address its schedule

The line's primary finding is **not** "no reader exists". It is stronger and
structural: **both cursors are mis-sized against their own schedules.**

| cursor | derived bound | how the bound was obtained | schedule cardinality | addressable | reachable-but-unaddressable |
| --- | --- | --- | --- | --- | --- |
| `weeklyRewardIndex` | **5** | `get_weekly_reward_length()` — `max(len(value))` over rungs whose `value` is a **list** | 3 rungs | `0..2` | **3, 4** |
| `bonusNextId` | literal `> 5` → `1` | a **hardcoded literal** in the branch | `DAILY_GOLD_REWARDS`, 5 entries, **0 consumers** | `0..4` | **5** |

Two of five weekly cursor positions and one of five daily cursor positions name
**no schedule entry at all**. A grant is therefore not merely *underivable* (the
shape `godot-research` and `godot-quests` delivered — a schedule exists and
nothing reads it). It is **unaddressable** at a measurable fraction of positions,
and the mismatch is a disagreement between two committed pieces of the *same*
feature rather than an absence of code.

What is delivered is the **cursor transition** and the two bounds, plus a
**reported** addressability gap. What is not delivered is any selection of a rung
from a position.

The weekly mismatch is **reachable from committed state without fabrication**:
`Neutral.json` records cursor **3** so one recorded transaction lands on **4**,
and `Nerri.json` records **2** and lands on **3**. Both land outside the
schedule. That is why the fixture in D12 can exercise the finding against a real
corpus.

## D2 - The request carries only an action and a save id; every grant-shaped argument is refused by name

The preserved branches accept, from the client: the item id (`args[1]` for
weekly, `args[0]` for daily), the map index (`args[0]`), the cell (`args[2]`,
`args[3]`), the player (`args[4]`), and the next id (`args[1]` for daily).

All of them are **refused by name**, before any write, rather than **ignored**.

This is a deliberate choice against the `/v0/level_up` precedent, which *ignores*
a client-supplied level. Ignoring is right when the ignored value is decorative —
the client learns nothing and the server is unaffected. It is **wrong** for a
cursor: `next_id` is precisely the value the server derives, so silently
substituting the derived value while acknowledging the request would answer
success for an input the operation did not honour. Refusing is the
`godot-unit-experience` position, and it is the one that keeps the contract
honest. The rejected alternative — ignore-and-derive — is retained here.

## D3 - The weekly length is derived, and the mismatch is reported beside it

`get_weekly_reward_length` (`get_game_config.py:195-204`) is the **only**
consumer of `MONDAY_BONUS_REWARDS` and consumes it for its **length only**; it
returns an `int` and has no code path returning a rung, an item, or an amount.

The length is delivered **as the function derives it**, including that it comes
from the **item list inside rung 1** and not from the rung count. The response
reports the derived length, the schedule's cardinality, and the set difference in
both directions, so a reader sees the mismatch rather than a number that silently
hides it.

An `index -> rung` helper is **refused and structurally absent** (D7). The
delivered code performs no indexing of the schedule by any cursor value.

## D4 - The daily bound is the recorded literal, and the rejected derivation is retained

`command.py:451` wraps with a **hardcoded literal** `> 5 → 1`. `DAILY_GOLD_REWARDS`
is `[100, 250, 500, 1000, 0]` — **five** entries, matching the literal exactly, with
**zero** consumers.

**The match is a coincidence of value distribution and not provenance.** The
literal is delivered as the literal. The rejected alternative — deriving the bound
from the schedule's entry count — is retained in this design precisely so a later
reader cannot mistake the agreement for a derivation.

The schedule is reported verbatim, including the **`0` at index 4**: an
index→amount derivation a reader would have inherited would have paid **nothing**
on that day, which is worth recording precisely because it is a *false* payoff
rather than a missing one. Position **5** is reported as out of range for the same
reason D1 gives.

## D5 - Both client-sent values are divergences, and the next id is the sharper one

The **item** is the obvious divergence: the preserved server takes the granted id
from the client, so the recorded transaction cannot establish what the reward was.

The **next id** is the sharper case, because the divergence is visible *inside the
legacy source* rather than only in the executed record: `win_daily_bonus` computes
`next_id = args[1] + 1` and then, if it exceeds the literal, overwrites it with
`1`. A client that sent a larger value would therefore have its cursor set
**backwards**. The service derives `next_id` from the recorded cursor instead, and
records the difference as a divergence.

A third divergence follows from the same reading and is recorded with them: the
preserved weekly branch's arm is selected by the client's **argument count**, so
the same command with different arities places a row or grants nothing. The
service has **no arm**; it reports the boundary and each arm's recorded effect.

## D6 - Nothing is granted, and the four-part post-execution proof makes that non-tautological

The delivered operation grants nothing. "Nothing" is a claim about **four**
distinct places a grant could land, and all four are checked on every success:

1. **no map row** — the placed-item count is unchanged and every existing row is
   byte-identical;
2. **no `boughtUnits` append** — the list is byte-identical, which also covers
   `bought_unit_add`'s deduplicating behaviour;
3. **no storage entry** — the store is byte-identical, which also covers
   `add_store_item`'s accumulating behaviour;
4. **no stored resource moved** — the **complete** stored resource set the
   service exposes is byte-identical.

The fifth half is that the **addressed cursor moved by exactly the derived
transition**. Together these make "this grants nothing" a verified property
rather than an absence of evidence: a refusal that quietly placed a row, or an
implementation that derived an amount, would fail the suite.

## D7 - The grant and addressability refusals are structural, not prose

The line asserts the absence of the helpers that would undo it, and those guards
are **tested by injection rather than trusted** — the practice established in
`godot-mission-vocabulary`, `godot-research`, `godot-unit-experience` and
`godot-unit-behaviors`, each of which proved its guard by injecting a helper,
observing the failures, and restoring a byte-identical file.

Three guard layers, because each catches a different disguise:

- a **whole static-function inventory pin**, the real gate: a reordering or an
  added function fails the suite;
- an exact **by-name** guard against invented grant, selection, and decoder
  helpers;
- a **substring** guard, because a suffixed helper wearing the same name
  (`damage_for`, `refund_for`) otherwise passes the by-name check — a lesson
  recorded from the stored-placement line, where the by-name guard was found to
  match only the exact name and was strengthened.

## D8 - The instant stamp is written, and no eligibility rule is derived from it

Both preserved branches stamp a wall-clock instant into `privateState`
(`timeStampMondayBonus`, `timestampLastBonus`). The line writes the stamp — a
write is reproducible parity — and derives **no** rule from it.

`timeStampMondayBonus` has **one** live write; its only other occurrence is
**commented out**. It has **no** reader, so no window, cooldown, weekly-period, or
"already claimed" test exists to reproduce, and none is invented. This is the
`tsAttacksReset` position from the `damage` line, recorded because the field's
*name* invites exactly the rule the line refuses to write.

Because the stamp is wall-clock, it is a **volatile field**. A successful
execution therefore cannot be compared by whole-document equality. Refusals still
are, because every refusal resolves before the stamp (D9). The fixture's replay
compares the stamp as a documented volatile field, following the
`/v0/session` `server_time` precedent.

## D9 - Every refusal resolves before any write, including before the instant stamp

Structural, content, and argument-shape validation all complete **before** the
cursor write and **before** the stamp, so a refused request leaves the whole
recorded document byte-identical.

The stamp ordering is the non-obvious half. A refusal that ran the branch far
enough to stamp would leave a wall-clock difference in a document that is supposed
to be unchanged — which would make the byte-identity assertion **fail for the
wrong reason**, or worse, be weakened to accommodate it. The ordering requirement
exists to keep the assertion exact.

The preserved server's ordering cannot be reproduced because it performs no
validation at all, so this requirement exists to make the service's refusals safe
rather than to match a recorded ordering.

## D10 - The type letters are reported undecoded, and no decoder is invented

The schedule's own vocabulary is `g`, `u`, `c`. Six independent searches across all
eleven legacy modules for any letter→resource mapping return **zero**: `'g'` mapped
to gold or coins, `'c'` mapped to cash, `'u'` mapped to unit, any single-letter
dict key, any `type == "x"` branch, and `reward["type"]`.

Reading `g` as gold and `c` as cash is the obvious next step and would be an
**invention**, not a reproduction. The letters are reported verbatim with the
recorded search results beside them, and no delivered code maps any of them onto a
stored resource slot.

## D11 - Ten zero-consumer schedules and seven save-only fields are reported with no rule

| group | measured | reported as |
| --- | --- | --- |
| reward schedules with zero consumers | **10 of 11** | committed content, unread, no rule |
| save-only `privateState` fields | **7**, in **39/39** documents, **0** source lines | recorded state of unknown origin, no rule |
| `level_ranking_reward` | **50** entries, **0** source occurrences | owned **as content**, undelivered **as gameplay** |

The seven save-only fields were written by a client this repository does not
contain. That is an **inference** from their total absence from all eleven modules
alongside universal presence in every save, and it is labelled as an inference
rather than a measurement.

The schedule census is a statement about the **preserved server's source**. The
whole `globals` object is *served* to clients, so a Flash client could have read
any of the eleven schedules; no claim is made about what it did.

## D12 - Fixture scope

Two branches, and the fixture's value is concentrated in the **short arm** of the
weekly branch.

The weekly **short arm** (`len(args) <= 4`) is the clean capture: it prints
*"Won resources"*, grants nothing, stamps, and advances the cursor — so the state
diff is **exactly** the cursor and the stamp, with no placed row to disentangle.
Running it against `Neutral.json` (cursor 3) advances to **4**, an unaddressable
position, which is the finding demonstrated by execution rather than by argument.

The weekly **long arm** is captured to establish the **divergence**: it places a
row the service refuses to place.

The daily branch is captured against a corpus with a recorded `bonusNextId`, to
establish that the preserved cursor is computed from a client-sent value.

Candidate corpora are the committed documents under `villages/` and `tests/saves/`;
the investigation records their recorded cursor values so the choice is not
arbitrary. **No capture is fabricated** and no document is edited to create a
precondition — `Neutral.json` already records the advanced cursor this line needs,
which is the first M10 line able to say that.

Scope limits are recorded with the fixture, not assumed: parity covers these
transactions against these corpora and nothing else; the grant is client-sent and
therefore unestablished; and the unaddressable positions are established for the
weekly schedule only, because the daily schedule is unread by any branch.

## D13 - Naming

The capability is `godot-rewards`, matching the roadmap deliver item so the
milestone cursor stays meaningful, on the `godot-damage` precedent where the
capability name follows the roadmap line while the delivered surface is something
else (the magics counter). Nothing in `godot-rewards` grants a reward; the name
identifies the M10 deliver line, and the spec says so explicitly so a later reader
cannot infer a payout from the capability name.

The route is `/v0/reward` with two actions, `weekly` and `daily`, on the
`/v0/magic` precedent (one domain noun, two preserved branches, an action set
that maps each action to its preserved command name). Neither action carries an
addressing key, because neither preserved branch addresses a row — recorded
explicitly rather than left to a default, because the quests line's largest
cross-layer defect was an addressing key the transport assumed was universal.
