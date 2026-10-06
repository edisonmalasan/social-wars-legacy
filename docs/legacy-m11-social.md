# M11 — Social and Special Systems: legacy measurement contract

**Status:** investigation only. No proposal, no implementation, no capability.
**Branch:** `docs/m11-social-investigation`
**Measured:** 2026-10-06, Windows x64, pinned CPython 3.9.13, from `main` at `aca5a67`.
**Scope:** the six M11 deliver items — friends, visits, scores, social rewards,
legacy event systems, special mechanics — measured against the preserved legacy
server (11 root modules), the committed save corpus, and the normalized content
package.

This document is a **measurement record**. It deliberately concludes less than a
proposal would, because M11's exit criterion is *"All relevant legacy game systems
are classified and implemented or explicitly excluded"* — classification is the
deliverable, and classification is what this document supplies.

---

## 0. Instrument faults committed by this investigation

Five faults occurred while producing the figures below. Each was caught by a
self-check rather than by inspection, and each is recorded here because **the
corrected number is only trustworthy once the reader knows the first number was
wrong**. All probes live under `%TEMP%\opencode\` and are intentionally not
committed, consistent with prior practice.

| # | Fault | Symptom | Correction |
|---|-------|---------|------------|
| 1 | Branch regex searched `command ==` | Found **0 of 63** branches; every social classification silently empty | The dispatcher compares **`cmd ==`** (`command.py:42`). Verified by grep before re-running. |
| 2 | Token self-check compared `0 == 0` | Reported **PASS** for a matcher that had never been tested | The probe words `friend`/`friendly` appeared only inside **string literals**, which the lexer strips. Rewritten to use a real code token. |
| 3 | Substring self-check inverted | Reported `False` for a **correct** matcher | `\bfriend\b` correctly refuses to match inside `friendly`; both queries returned `1` and the `!=` comparison was backwards. The property is "count on `friendly` alone must be `0`". |
| 4 | Census walk excluded all of `tests/` | 0 documents, 0 rows | Settled denominator is `tests/saves` + `villages`, excluding `tests/saves/manifest.json`. Now reproduces **33 carrying** exactly. |
| 5 | Loop body left inside `except:` handler | 0 documents inspected after the fix to #4 | Dedent restored. |
| 6 | Normalized social files assumed to be dicts | `TypeError` sorting dicts against dicts | They are **top-level lists**. |
| 7 | Write regex matched only the literal `privateState["x"]` subscript form | `magics`/`mana` wrongly reported as *read without a writer* | The branches use an **aliased local** (`magics = privateState["magics"]`) and `engine.py` writes `mana` inside `apply_resources`. Corrected in §6. |

A seventh discrepancy was **reconciled, not a fault**: this investigation first
counted **13,034** placed rows where prior work records **12,954**. Measurement
shows `12,954` is `villages/` alone (31 documents) and the extra **80** rows are
`tests/saves/` (2 documents). Both denominators are correct; the census
denominators already settled in this project (`34 walked / 33 carrying`) are
**reproduced exactly** and are not re-litigated here.

**Standing rule reaffirmed:** no figure below is trusted unless its own control
passes. Where a control could not be made non-vacuous, the figure is reported as
unmeasured rather than as zero.

---

## 1. Denominators (settled, reproduced)

| Figure | Value | Reproduced |
|--------|-------|------------|
| Legacy root modules read | 11 | yes |
| Named `command.py` dispatcher branches | **63** | yes, matches committed catalog |
| Branch spans extracted | 63, all non-empty, all names unique | yes |
| Save files on disk (`tests/saves` + `villages`) | 34 | yes |
| Save files walked (1 exclusion) | 33 | yes |
| Documents carrying ≥1 map | **33** | yes |
| Placed rows (`villages/` only) | 12,954 | yes |
| Distinct placed-row lengths | **[8]** — exactly 8 in every case | yes |
| `privateState` keys | **47** distinct, all present in all 33 | yes |
| `maps[]` keys | 28 distinct (27 in all 33; `__#__ITEMS_hint` in 6) | yes |

---

## 2. Finding A — no branch is named for any social deliver item

Of the 63 named dispatcher branches, matching on name against social vocabulary
(`friend`, `visit`, `score`, `social`, `neighbor`, `neighbour`, `assist`,
`allied`, `allies`, `gift`, `send`, `invite`, `cooperat`, `raid`, `attack`,
`trade`):

| Branch | Matched word | Actual subject |
|--------|--------------|----------------|
| `trade_resource` | `trade` | market resource trading |
| `set_resource_allies` | `allies` | auction-house resource selection |
| `end_attack` | `attack` | combat termination (owned by `godot-unit-behaviors`) |

All three are **substring artifacts of non-social systems**. There is **no
branch** named for friends, visits, scores, or social rewards.

This is a *naming* finding only. It is not by itself evidence that the
functionality is absent — a project has already been delivered whose vocabulary
lived in a dead module. Sections 3–5 measure substance instead of names.

---

## 3. Finding B — the social content tables have ZERO consumers

Three normalized tables exist with schemas, round-trip evidence and manifest
entries (`packages/game-content/normalized/`):

| Table | Entries | Whole-file tokens | Code-only tokens | Quoted-key form |
|-------|---------|-------------------|-----------------|-----------------|
| `social_items` | 26 | **0** | **0** | **0** |
| `findable_items` | 10 | **0** | **0** | **0** |
| `neighbor_assists` | 5 | **0** | **0** | **0** |

Measured across all 11 legacy modules, under six counting rules (whole-file
occurrences, distinct lines, code-only with comments and string literals
stripped, code-only distinct lines, exact identifier tokens, quoted-access
form). All six return zero for all three tables, against **both** the normalized
names and the raw `config/main.json` key names (confirmed present at
`config/main.json:44946`, `:45047`, `:47262`).

The content is real and committed — `neighbor_assists` carries `task`,
`reward`, `position`, `notification`; `findable_items` carries `title` and
`coins`; `social_items` carries `workers` and `worker_cost` — and **nothing in
the preserved server reads any of it**.

These are three more committed content fields with no legacy consumer, joining
the established class in this project (which already includes `unit_capacity`,
`velocity`, `max_frame`, `training_time`, `unlockedQuestIndex`,
`reward_type`/`reward_amount`, `completed_tutorial`).

---

## 4. Finding C — social **state** exists in every document and is never written

This is the finding that makes M11 a real surface rather than a closure, and it
is the exact shape that made `godot-rewards` real: **state that is persisted but
never written.**

19 social-looking state keys were measured for writes and reads across all 11
modules.

**13 of 19 have ZERO occurrences of any kind** — not a read, not a write, not a
mention:

`friendsHelpedCoveredItem`, `neighborAssists`, `receivedAssists`,
`firstTimeAlliance`, `helpMap`, `attacksSent`, `attacksReceived`, `attacksPack`,
`spyings`, `spyingsPack`, `questsRank`, `resourcesTraded`,
`crossPromotionsFinished`

**6 of 19 are written**, and every one is written by a branch whose subject is
not the social system it names:

| Field | Written by | Note |
|-------|-----------|------|
| `resourceAlliesMarket` | `set_resource_allies` (`command.py:637`) | writes `map["resourceAlliesMarket"] = resource` from **client-sent `args[0]`** |
| `publishedOpenGraphUnit` | `rt_open_graph_unit` (`:886`) | appends a client-sent item id to a list |
| `marketPlaceFirstTime` | `first_time_marketplace` (`:899`) | sets `True`, unconditionally |
| `numTradesDone` | `trade_resource`, `engine.py` | increments a trade counter |
| `timestampLastTrade` | `trade_resource`, `fast_forward` | instant; `fast_forward` subtracts a **client-supplied** second count |
| `timeStampEndPremium` | `buy_premium_account` | single instant write |

`questsRank` is the sole exception to the zero group: it has **one read** and
**no write**, in `admin_set_quest_rank`.

### 4.1 Every zero-consumer field is uniformly empty in the whole corpus

Across all 33 documents, each of the 12 write-less fields holds exactly **one**
distinct value:

| Field | Value | Documents |
|-------|-------|------------|
| `friendsHelpedCoveredItem` | `null` | 33/33 |
| `firstTimeAlliance` | `null` | 33/33 |
| `neighborAssists` | `{}` | 33/33 |
| `receivedAssists` | `{}` | 33/33 |
| `resourcesTraded` | `{}` | 33/33 |
| `helpMap` | `[]` | 33/33 |
| `attacksSent` | `[]` | 33/33 |
| `attacksReceived` | `[]` | 33/33 |
| `spyings` | `[]` | 33/33 |
| `crossPromotionsFinished` | `[]` | 33/33 |
| `attacksPack` | `0` | 33/33 |
| `spyingsPack` | `0` | 33/33 |

**The corpus contains no example of a populated social field.** Any future line
claiming parity for these would have zero executed-legacy evidence available,
and this is a *corpus* fact that must be recorded as such — not as evidence that
the behaviour is absent.

### 4.2 `set_resource_allies` also stamps an addressed building

```python
elif cmd == "set_resource_allies":
    resource = args[0]
    index = args[1]
    item = map_get_item(map, index)
    if item:
        item[3] = time_now
        finish_si(item)
    map["resourceAlliesMarket"] = resource
    print("Set Allies Market resource")
```

Two distinct effects: the market resource is a **client-sent value written
verbatim**, and an **addressed building** has its slot 3 overwritten with
`time_now` and `finish_si` called. Whether that stamp means anything is
unmeasured here — no reader of `item[3]` is claimed.

---

## 5. Finding D — visits and scores have no surface at all

| Token | Code-only | Quoted-key | Verdict |
|-------|-----------|------------|---------|
| `visit`, `visits`, `visitMap`, `visit_map`, `neighborMap`, `friendMap` | 0 | 0 | **absent** |
| `helpMap` | 0 | 0 | absent from code (state only, §4) |
| `world_id`, `worldId`, `worldChange` | 0 | 0 | **absent** |
| `score`, `scores`, `leaderboard`, `ranking`, `points`, `highscore`, `bestUnit` | 0 | 0 | **absent** |
| Arithmetic on any score-like value in `command.py` | **0 matching lines** | — | **absent** |

`world_id` and `worldChange` **are** map keys present in all 33 documents, yet
appear **zero** times in the legacy source. They are carried state with no
server-side concept of a world.

Two apparent positives were checked and **rejected as scores**:

- `lost` — 6 code-only occurrences, all a **local unit-loss counter**
  (`command.py:792`, `:868`, plus print lines), not a score.
- `won` — 2 quoted-key occurrences; the only real write is
  `auctions.py:164` `bet["won"] = 1`, an auction-bet result, not a leaderboard.

Neither is scored, ranked, or aggregated.

---

## 6. Finding E — special mechanics: darts is real state, the rest is thin

| Field | Writes | Reads | Written by |
|-------|--------|-------|-----------|
| `dartsBalloonsShot` | 1 | 1 | `darts_reset` |
| `dartsGotExtra` | 2 | 0 | `darts_reset`, `darts_shoot_balloon` |
| `dartsHasFree` | 3 | 0 | `darts_reset`, `darts_new_free`, `darts_shoot_balloon` |
| `dartsRandomSeed` | 1 | 0 | `darts_reset` |
| `timeStampDartsNewFree` | 4 | 0 | `darts_reset`, `darts_new_free`, `darts_shoot_balloon`, `fast_forward` |
| `timeStampDartsReset` | 2 | 0 | `darts_reset`, `fast_forward` |
| `timeStampEndPremium` | 1 | 0 | `buy_premium_account` |
| `crossPromotionsFinished` | **0** | 0 | — |
| `magics` | **0**\* | 2 | — (\*see correction below) |
| `mana` | **0**\* | 1 | — (\*see correction below) |
| `unlockedSkins` | **0** | 0 | — |

> **CORRECTION (2026-10-06, same day, before any proposal).** The table above
> originally reported `magics` and `mana` as *read without any writer*, and the
> prose did too. **That was wrong**, and the cause is a seventh instrument fault:
> the write regex matched only the literal `privateState["magics"]` subscript
> form, so it missed the **aliased local** the branches actually use —
> `magics = privateState["magics"]` at `command.py:656` and `:668`, followed by
> `magics[str(magic_id)] += min(50, ...)` at `:658`/`:670` and
> `magics[str(magic_id)] = 0` at `:660`/`:672`. `mana` is likewise written at
> `engine.py:268`, `save["privateState"]["mana"] = max(... + mana, 0)`, inside
> `apply_resources`.
>
> Both fields are therefore **written**, and neither is social state: `magics` is
> a per-magic-id counter bounded at 50, and `mana` is one of the seven stored
> resource slots. The only genuinely inert special field is `unlockedSkins`
> (zero occurrences of any kind), plus `crossPromotionsFinished`.
>
> This correction strengthens the §7 classification rather than weakening it, and
> it is recorded here rather than quietly edited because the superseded claim was
> published in PR #309. It also narrows §8's open item: `magics`/`mana` is no
> longer unresolved.

**Darts is the one special system with genuine multi-branch state**: four
branches (`darts_reset`, `darts_new_free`, `darts_shoot_balloon`, plus
`fast_forward` touching two of its instants) across six fields. Note the
established `fast_forward` pattern — a client-supplied second count subtracted
from stored instants, making them client-writable.

`magics` and `mana` are **read without any writer in `command.py`**, which
inverts the usual shape and is worth a follow-up measurement rather than a
conclusion here. `crossPromotionsFinished` and `unlockedSkins` are inert.

`specials.json` holds exactly **1** entry, `legacy_id` `"925"`, with the full
57-field item shape — a documented special, not a system.

---

## 7. Classification of the six M11 deliver items

| Deliver item | Classification | Basis |
|--------------|----------------|-------|
| **Friends** | **State-only, no consumer.** Persisted in 33/33 documents, zero legacy occurrences, uniformly empty | §4, §4.1 |
| **Visits** | **Absent.** No token, no branch, no arithmetic; `world_id`/`worldChange` carried but never read | §5 |
| **Scores** | **Absent.** No token, no arithmetic; `lost`/`won` checked and rejected | §5 |
| **Social rewards** | **Content committed, behaviour absent.** 3 tables / 41 entries with zero consumers; `neighborAssists` + `receivedAssists` state uniformly `{}` | §3, §4 |
| **Legacy event systems** | **Partial.** `weekly_reward` and `win_daily_bonus` delivered by `godot-rewards`; darts is real multi-branch state | §6, prior work |
| **Special mechanics** | **Partial.** Darts state real; premium/mana/magic thin or inert; one `specials` entry | §6 |

**M11's exit criterion is classification-shaped, and this table satisfies it** —
subject to the verification limits below.

---

## 8. What this investigation does NOT establish

- **No parity claim.** Nothing here was executed against the legacy server. Every
  figure is a static source or corpus measurement.
- **The 12 uniformly-empty fields are a corpus fact, not an absence claim.** A
  progressed player might populate them; no such save exists in the repository.
- **Absence of a token is not absence of a feature.** The Flash client may have
  had friends and scores entirely client-side, in which case no server branch
  would ever exist. This is the most likely explanation for §5 and it is
  **unverifiable from the preserved oracle** — the same limitation that made
  M10's exit criterion unsatisfiable.
- **No new zero-consumer field is claimed without the six-rule count.** §3 and §4
  report six rules each; both were run and both returned zero.
- **`set_resource_allies`'s building stamp is unexplained.** `item[3] =
  time_now` is reported verbatim; no semantics are derived from it.
- ~~**`magics`/`mana` read-without-write is unresolved**~~ — **resolved by the
  §6 correction**: both are written, and neither is social state. The remaining
  inert special fields are `unlockedSkins` and `crossPromotionsFinished`.

## 9. Recommended next step

The natural first M11 line is the one this document most supports and least
invents: a **`godot-social-state` refusal line** projecting the persisted social
state verbatim — the 19 measured fields, their uniform corpus values, and the
recorded zero-consumer census — while **refusing** to decode
`neighbor_assists` rewards, to charge `findable_items` coins, to select
`social_items` workers, or to treat any absent field as an empty one.

That is the same shape as the delivered refusal lines (`godot-unit-animations`,
`godot-unit-movement`, `godot-unit-production`): content and state reported,
mechanism refused, and the **absence recorded as a property** rather than read
as permission to invent a rule.

**This is a recommendation, not a proposal.** No OpenSpec change is created by
this document.
