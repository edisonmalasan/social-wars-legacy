# M13 line 5 - ranked target selection: two ranks withdrawn, and no target selected here

## 0. What this file is, and what it is not

This is the selection record for **M13 line 5**, the line that follows `combat-attack-authority`
(line 4, archived at `openspec/changes/archive/2026-10-14-combat-attack-authority/`).

It is a **selection** record in the lineage of `docs/legacy-m13-line3-candidates.md` and
`docs/legacy-m13-line4-candidates.md`. It re-derives what it can, records two **withdrawals**,
records **two of my own instrument faults**, and then **declines to name a target** — with the
reason stated as a measurement gap rather than as a preference.

It is not a proposal, and nothing here is authorised. Per this repository's standing rule the
cursor is advanced, not acted on.

## 1. The headline: two of line 4's ranks are withdrawn

`docs/legacy-m13-line4-candidates.md` §5 ranked the remaining pool and put, in order:

| rank | branch | line 4's C3 "route" column |
|---|---|---|
| 1 | `end_attack` | `/v0/combat` |
| 2 | `win_daily_bonus` | `/v0/reward` |
| 3 | `weekly_reward` | `/v0/reward` |
| 4 | the four research branches | `/v0/research` |
| 5 | `set_goals` | `/v0/quests` |
| 6 | `complete_tutorial` | `/v0/tutorial` |

**Ranks 2 and 3 are withdrawn as CANDIDATES.** `win_daily_bonus` and `weekly_reward` are
**already delivered** - by **M10 line 1**, the capability named `godot-rewards`. Measured
directly:

- `apps/compat-api/rewards_envelope.py:4` states the capability in its own header: *"M10 line 1
  (`rewards`) - the two **reward cursors**"*, and names **both** branches with their spans
  (`weekly_reward` 345-363, `win_daily_bonus` 444-463).
- `apps/compat-api/compat_service.py:2318` declares `@app.post("/v0/reward")`.
- The refusal vocabulary is already committed there: `rewards_envelope.py:809`,
  `REASON_CLIENT_SUPPLIED_ITEM = "client_supplied_item"`.
- There is a committed **executed-legacy fixture** with its own capture script: `tests/fixtures/godot-rewards/`,
  `schema: rewards-cursor-fixture-v1`, captured `2026-10-05`, exit `0`, **7 recorded steps**
  (four dedicated daily, three dedicated weekly, plus one `login_post`), and an
  `apps/compat-api/capture_rewards_fixture.py`.

The delivered line is itself a **refusal** line: the captured manifest records three divergence
classes - `arity_selects_the_arm`, `client_supplied_item`, `client_supplied_next_id` - and states
in `not_claimed` that *"Anything about WHAT WAS GRANTED"* is not claimed, because *"The grant is
client-sent in both branches"*.

**Why this matters for line 5 and not only for tidiness.** The line-4 record listed ranks 2 and 3
without noting they were already delivered, which means its ranking was scored as if the pool
were undelivered client surface. It is not. Most of that ranking - ranks 4, 5, 6 and 7
(`research`, `quests`, `tutorial`, `expand`, `level_up`) - is likewise **already delivered** at v0
by the M9/M7 lines. So the pool line 4 ranked is, with line 4's own target removed, **almost
entirely delivered client surface**.

The consequence is a reframing, not a smaller list: **M13 is not "deliver branches to the client".
The client surface is done. M13 is "make delivered branches authoritative in v1".** Every remaining
M13 line will therefore be scored on what v1 can *derive* or *refuse*, not on whether a client
surface exists.

## 2. What my own measurements corroborate

I re-measured the reward branches' content linkage from scratch, before reading
`rewards_envelope.py`, and my figures **reproduce the delivered line's own recorded analysis
exactly**:

| measurement | my figure | agrees with |
|---|---|---|
| `win_daily_bonus` span | `command.py:444-463` | yes |
| writes in the branch | `timestampLastBonus`, `bonusNextId`, plus both grant helpers | yes |
| cursor source | `next_id = args[1] + 1` (`:446`), client-sent | yes |
| bound | literal `5` at `:451`, then `= 1` | yes |
| `DAILY_GOLD_REWARDS` | `[100, 250, 500, 1000, 0]` - **5** entries | yes |
| legacy reads of `DAILY_GOLD_REWARDS` | **0** across all **11** top-level legacy modules | yes |
| readers of `timestampLastBonus` | **0** - two writes (`:454`, `:914`) and no read | yes |

This is **corroboration, not new evidence**, and is recorded as such. Two things it does
establish independently:

1. **`timestampLastBonus` is write-only, and client-writable.** `command.py:914` is inside
   `fast_forward`, which subtracts a **client-supplied** number of seconds from it. Since nothing
   reads it, there is **no eligibility, cooldown, daily-window or already-claimed rule** in the
   preserved server to reproduce. The daily bonus can be claimed as often as the client asks.
2. **The committed ladder grants nothing.** The branch's `else` arm (`item <= 0`) only
   `print("Rewarded resources")`. The oracle never credits gold. So applying
   `DAILY_GOLD_REWARDS` in v1 would be a **divergence from the oracle**, not a parity claim.

## 3. Criterion 1 is still dead, and that is the programme-level finding

Line 4's ordering rule puts **criterion 1 first: a content-anchored derivation exists.** It
measured this dead for all 29 then-pool branches. With `end_attack` delivered the pool is **28**,
and the finding **carries over unchanged**: not one of the 28 has a committed value naming its
outcome.

The two branches that *do* have committed reward ladders are exactly the two already delivered at
v0, and their ladders are unread by the preserved server. So the two most content-anchored
candidates in the whole pool are the two a v1 route would have to **diverge** to serve.

**This is the finding worth recording: M13's content-anchored derivation pool is exhausted, not
merely narrowed.** Every remaining line will be a refusal line unless criterion 1 is revisited on
its own terms.

## 4. Instrument faults in my own measurements - two, both discarded

The project rule is that a defective instrument is **discarded, not reported**. Both probes below
are recorded so a later reader does not repeat them, and neither contributes a figure anywhere in
this file.

**Fault 1 - a probe that returned a confident zero.** I executed every `build*` function in all
21 `apps/compat-api/*_envelope.py` modules and read the branch name out of each returned batch. It
reported **0 dispatched, 63 undispatched** across 48 calls. That is a plausible-looking and
completely false result: the builders take **required positional arguments**, so every call raised
`TypeError` and my `except: continue` swallowed all 48.

**Fault 2 - the repair failed the same way.** I rebuilt the probe to synthesise arguments from
each `inspect.signature`, including an arity variant to catch arity-selected arms. It reported
**48 calls, 0 successes, 0 dispatched** - the modules require the compat bootstrap that I did not
initialise. Two probes, zero usable output.

**Therefore the dispatched/undispatched split is NOT re-measured here and is INHERITED.**
`docs/legacy-m13-unrouted-branches.md` §2.1 records **39 dispatched / 24 undispatched**, obtained
by executing the builders. I could not reproduce it, and the recorded investigation's own history
shows why that figure has been dangerous: it was first published as `40 / 23`, then **withdrawn**
and corrected to `39 / 24` after `buy_mana_new` was found to be declared `NO_OP_COMMAND` and read
only inside a *reported* record.

For completeness, the tool that exists for a **different** question reports, at HEAD:
`branches_cited_by_line_span = 24`, `branches_without_cited_route = 39`,
`branches_covered_permissive_reading = 37`, `branches_covered = 24`, `legacy_branches = 63`,
`routes = 24`. These are **citation-grounding** counts, not dispatch counts, and the recorded
investigation already explains the divergence: the tool asks whether a handler's source cites a
branch with a resolvable `command.py:NNN` span, which is neither necessary nor sufficient for the
branch to be dispatched. Quoting `39` from either source as "dispatched" without saying which
question is being answered is how the earlier `40 / 23` error happened.

## 5. Why no target is named here

A target cannot be selected on an inherited split whose two reproductions I could not build, and
the criteria that would break the tie - 3 (fixture depth) and 4 (a live v0 route to replace) -
both require that split to be current. Naming one anyway would repeat exactly the defect this
file exists to record: a confident document asserting a ranking whose inputs were not measured.

What is needed before line 5 can be proposed:

1. **A working dispatch probe**, or the acceptance of the inherited `39 / 24` as a labelled
   input rather than a measured one.
2. **A criterion-1 revisit on its own terms** - not to find a survivor, since the section 3
   finding is that there is none, but to decide whether "no committed outcome" should now select
   for the *strongest* refusal rather than merely disqualify.
3. **An explicit ruling on divergence**, because both content-anchored branches would diverge from
   the oracle to serve. That is a programme decision, not a line decision, and it belongs to a
   proposal, not to this record.

## 6. Claim limits

- **No target is selected.** This file is not authorisation for anything.
- The withdrawals in section 1 are **about candidacy for a client-facing line**, not about M13
  authority: both reward branches remain **non-authoritative** for v1, and no figure here claims
  otherwise. The M13 counts are unchanged by this file - **5** of **63** named branches carry an
  authoritative v1 route, **58** do not; **4** of **24** v0 routes have an authoritative
  counterpart, **20** do not.
- Every figure in section 2 was re-measured at HEAD from source. Every figure in section 4's tool
  paragraph is the tool's own output, quoted with its question attached.
- The `39 / 24` split is **inherited and not reproduced**. It is labelled here rather than
  silently relied on.
- **Nothing about what the Flash client sent.** No client was executed.
- Claim **no ordinal** over the count of inherited figures this milestone has found wrong; the
  recorded instances disagree over different scopes.

## 7. Corrections carried forward

- `docs/legacy-m13-line4-candidates.md` §5 ranks 2 and 3 are **withdrawn** as candidates. The
  record itself is **not edited** - it is retained as written, per the ledger's own rule.
- The `39 / 24` split, if it is used by any later line, must be labelled inherited.