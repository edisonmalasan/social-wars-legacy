# Proposal

## Why

M11's first line established that social content has no consumers and social state
is never written. The committed contract `docs/legacy-m11-social.md` then
classified the milestone's remaining items and left **two of them as "Partial" with
an undelivered surface it never measured**. That measurement is now done
(`docs/legacy-m11-darts.md`, PR #315) and it found the one M11 surface where the
**server derives a value from committed content and computes it authoritatively** —
`buy_premium_account` reads its duration from the committed `PREMIUM_ACCOUNTS`
schedule — sitting beside a darts state machine whose every input is
client-sent. Neither is delivered, and the premium schedule commits a **price that
nothing anywhere reads**, so the preserved server grants a paid purchase for free.

Delivering nothing here leaves M11's classification-shaped exit criterion resting on
a guess about the one part of the milestone the client could actually implement.

## What Changes

- **Add `godot-darts`**, covering the six darts state fields, the three darts
  command branches, the one server-side week-boundary reset, and the premium
  account purchase.
- **Deliver the premium duration as a server-authoritative derived value** from the
  committed `PREMIUM_ACCOUNTS` schedule, including the recorded oversized-index
  clamp and the two-arm buy/extend selection — the first M11 surface whose value
  the server, not the client, computes.
- **Charge nothing**, and prove it non-tautologically: the committed `price` beside
  every committed `time` has **zero** consumers across all eleven legacy modules, so
  every action's post-execution proof compares the **complete** stored resource set
  and requires it byte-identical.
- **Refuse the client-dictated outcome.** `darts_shoot_balloon` takes a client
  `won_extra` truthiness that sets `dartsGotExtra`; the server verifies no win, so
  that half is recorded as a divergence and never reproduced. The shot **index** is
  intent and is delivered; the **outcome** is not.
- **Refuse the unbounded list and the missing membership test**, recording that the
  preserved server has neither, that a shot index of `0` exists in the corpus while
  the committed `darts_items` ids run `1..27`, and that `0` is accepted anyway.
- **Correct `godot-social-state`**, which currently records `timeStampEndPremium` as
  *"a single instant write"* by a client-sent branch. It is **two** writes in one
  branch, its value is **server-derived**, and it is a purchase field rather than a
  social one; `crossPromotionsFinished` is a cross-promotion flag, not social state.
  Both are declared foreign to that capability rather than left mis-filed.
- **No new content is invented.** `darts_items` stays owned by
  `darts-schedule-normalization` and `PREMIUM_ACCOUNTS` by
  `globals-tuning-normalization`; this capability reads them and derives nothing from
  them that the preserved server does not.

## Capabilities

### New Capabilities

- `godot-darts`: Deliver M11's darts and premium-account line — the darts state
  machine over six recorded fields, the server-derived premium duration and its
  buy/extend arms, the week-boundary reset predicate, and the recorded refusals for
  the client-sent shot outcome, the unbounded shot list, the missing schedule
  membership test, and the committed price nothing reads.

### Modified Capabilities

- `godot-social-state`: Two of the nineteen fields it currently requires be delivered
  as **social** state are not social. `timeStampEndPremium` is a purchase field with
  **two** writes in one branch and a **server-derived** value, recorded today as *a
  single instant write* by a client-sent branch; `crossPromotionsFinished` is a
  cross-promotion flag. The requirement stops calling all nineteen social, the
  recorded-writer requirement stops implying the premium branch is client-sent, and
  both fields are declared foreign and owned by `godot-darts`.

## Impact

- **New**: `apps/client-godot/scripts/darts/` (typed read-only projection, purchase
  derivation, week-reset predicate), its hermetic suite, its deterministic evidence
  report, and one Compatibility API route.
- **Modified**: `apps/compat-api/` — one new envelope and one new state-mutating
  endpoint. Because this line **does** add a route, the compat suite count is
  expected to grow, unlike the M11 line 1 that added no endpoint and left it
  unchanged.
- **Modified**: `apps/client-godot/scripts/social/social_state.gd` and
  `openspec/specs/godot-social-state/spec.md` — the two foreign-field corrections.
- **Modified**: `apps/client-godot/verify-boot.ps1` hermetic list and the
  project-scope allow-list; **new** live phase `darts-live`.
- **Touched by no stage**: legacy sources, `config/`, `villages/`, `tests/saves/`,
  `packages/game-content/`, and the preservation manifest are not modified.
