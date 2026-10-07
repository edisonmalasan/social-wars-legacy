# Proposal

## Why

M11's last unexamined deliver item, `social rewards`, is classified in the
deliver-item table of `docs/legacy-m11-social.md` §7 as **"Content committed,
behaviour absent"**, on the basis of §3 and §4, and by
`social-tables-normalization` and by `godot-social-state`'s eighth requirement.
That classification is **reproduced and true of the three tables**, and **false
of the deliver item**. The preserved server holds a social-assistance state
machine the tables never mention: `attr["si"]` is **"Socially In Construction"**
(`engine.py:19`), it is gated by the committed `properties.friend_assistable`
flag, it is written by three functions, it is dispatched from **three** branches
— one of which is not named for it — and it is persisted on **53 of 3,372**
placed rows in the committed corpus.

The line therefore exists to close a **real, unowned, behaviour-bearing surface**
rather than to close a deliver item by measurement, and to record that the surface
is the **inverse** of its name: the only value any writer ever appends is `0`,
which `engine.py:142` names as *"buying instead of hiring friends"*. The list
records a **paid substitute for a friend**, and no reward is ever granted.

## What Changes

- **New capability `godot-construction-assist`** delivering a typed, read-only,
  fail-closed projection of the `attr["si"]` assist state on a placed row —
  presence, list length, and each element's recorded type and value **verbatim**.
- **New requirement set** recording the three dispatchers and their effects
  quoted from source with `reproduced: false`: `buy_si_help`
  (`command.py:549`), `finish_si` (`:561`), and the differently-named
  `set_resource_allies` (`:637`), which calls `finish_si` at `:644`.
- **New requirement** recording that the only appended element is `0`, that its
  meaning is fixed by a source comment rather than inferred, and that **the friend
  arm has no writer anywhere** — measured `0 / 0 / 0 / 0 / 0 / 0` over all eleven
  legacy modules under six counting rules, and corroborated by the corpus holding
  **7** elements and **one** distinct element value.
- **New requirement** recording three corpus **gaps rather than explanations**,
  because two of them falsify any claim that `si` implies `friend_assistable` in
  either direction: 2 of 53 `si` rows sit on ids lacking the flag (and are the only
  non-empty lists), 2 flagged ids are placed with no `si`, and 8 of 26 are never
  placed.
- **New requirement** recording `giftable` and `gift_level` as two more committed
  fields with zero legacy consumers, **with no ordinal position claimed**,
  completing `godot-unit-behaviors`'s existing units-only census row for
  `gift_level` and recording that `giftable` is in no census at all.
- **New requirement** requiring every refusal to be enforced by a guard proven by
  **injection against a byte-identical copy** with the restored digest recorded,
  so no refusal is a claim a reader has to take on trust.
- **Modified `godot-social-state`**, and nothing else: requirement 1's standing
  refusal to imply a social-rewards feature is superseded by an ownership
  hand-off to a third capability — this capability owns the assist lifecycle,
  that one keeps the state fields. Its requirement 7's record of
  `set_resource_allies` is amended to name the `finish_si` call it currently
  omits, and its requirement 11's reason (*"no social command exists"*) is
  corrected, since three exist. Those are the **only** three requirements in the
  repository whose text this change falsifies or leaves materially incomplete.
- **No route, no `apps/compat-api/**` change.** `attr["si"]` is already carried on
  `/v0/bootstrap`, so the compatibility suite must hold at its **3077** baseline
  as a *verified* figure rather than a skipped check.
- **No executed-legacy fixture.** Unlike the refusal lines, the reason here is a
  **decision, not a limitation**: the transaction grants nothing, charges nothing,
  and its only appended value is a fixed sentinel.

## Capabilities

### New Capabilities

- `godot-construction-assist`: the `attr["si"]` Socially-In-Construction assist
  lifecycle — a typed read-only projection, the three recorded dispatchers, the
  `0` sentinel, the absent friend arm, the corpus's three gaps, and the two
  zero-consumer gift fields.

### Modified Capabilities

- `godot-social-state`: requirement 1 becomes an ownership hand-off to a third
  capability rather than a standing refusal, **without weakening the prohibition
  it carries**; requirement 7 names the `finish_si` call it omits; requirement 11's
  *"no social command exists"* reason is corrected, since three exist.

No other capability is modified. Two candidates were examined and **rejected as
not warranted**, each because its requirement survives measurement unchanged:

- `godot-stored-item-placement` requirement 2 already derives the attribute bag
  from the committed `friend_assistable` flag, and its scenario is scoped to
  placement. `buy_si_help` is a different command, so nothing it claims is
  contradicted. The ownership is instead **asserted by this change's own
  requirement**, which checks that the owning capability's spec exists — the
  pattern `godot-unit-collection` established for its hand-off — so a rename there
  cannot orphan the link.
- `social-tables-normalization` — see the recorded correction below.

## Corrections recorded during planning

Three defects in this proposal's own verification were found by measurement and
are recorded rather than quietly fixed.

**1. A claim about a delivered spec was falsified, and the amendment is
withdrawn.** The proposal originally proposed modifying
`social-tables-normalization` because its *"26 social items"* was said to imply 26
distinct items where the table encodes 13. Re-measured, the requirement is
**literally true**: the 26 rows carry 26 **distinct** `legacy_id` values —
`3, 9, 12, 16, 28, 37, 44, 54, 61, 64, 74, 75, 140` and
`3003, 3009, 3012, 3016, 3028, 3037, 3044, 3054, 3061, 3064, 3074, 3075, 3140` —
so the *one definition per stored entry* claim, the *decimal id* claim, and the
capability's own id-uniqueness requirement all hold. The measured fact is that 13
*items* each recur twice at a fixed `+3000`, which is a content observation and
not a violated requirement. The MODIFIED delta is therefore withdrawn, and the
clause that would have made this capability report that recurrence is withdrawn
too — it contradicted the neighbouring clause forbidding this capability to
project those content rows. The measurement stays in
`docs/legacy-m11-social-rewards.md`.

**2. A measurement printed a vacuous truth and looked like a finding.** The first
re-measurement used a `legacy_id` regex that matched **nothing**, reported 0
occurrences and 0 distinct ids, and then reported
`low+3000 == high set: True` by comparing **two empty lists**. A vacuous `True`
in a comparison is exactly the tautology class `godot-friends` closed by reading
real key names instead of a projection's own declared list. The claim was voided
and re-measured against the file's real shape, which is how correction 1 was
found at all.

**3. The spec search method under-counted in the direction that mattered.** A raw
substring search reported `"no social command exists"` **absent** from
`godot-social-state` and `"friend-assistable"` absent from
`godot-stored-item-placement`. Both are present, because both are split across a
line wrap. Collapsing whitespace fixes the first (`no\nsocial command exists`)
but **not** the second, which is hyphen-wrapped (`friend-` + newline +
`assistable`) and becomes `friend- assistable` even after collapsing — so a
hyphenated term needs the wrap *removed*, not whitespace collapsed. Searching on
the raw form would have let this change amend a requirement for a reason that does
not exist in it. A **fourth** instance of the same instrument class appeared while
checking this proposal's citations: a case-sensitive search for
*"content committed, behaviour absent"* reported **0** occurrences in
`docs/legacy-m11-social.md`, when the phrase is present in §7's table as
`**Content committed, behaviour absent.**` A search that can report a present
string as absent is not evidence of absence in either direction — which is the
whole reason corrections 1 to 3 were worth the probes.

Because a MODIFIED delta replaces a requirement **in full**, each delta here was
diffed line-by-line against a wrap-normalised copy of the original, so that a
paraphrase could not silently weaken text this change has no licence to change.
Every original sentence survives verbatim, and every added scenario is additive.

## Impact

- **New client modules** under `apps/client-godot/scripts/social/`, a new hermetic
  suite registered in `verify-boot.ps1`, a new report under
  `apps/client-godot/evidence/`, a README section, and an `AGENTS.md` section.
- **`apps/client-godot/tests/test_project_scope.gd`** must be amended for the new
  sources, the new suite, and the new report in its allow-list — the one recorded
  mechanism by which a delivered line can add a client file.
- **`godot-unit-behaviors`**: this line completes its census rather than replacing
  it, so its `gift_level` row gains a buildings-side measurement and `giftable`
  becomes a recorded row instead of a gap.
- **No compatibility change.** `apps/compat-api/**` is untouched and the suite's
  3077 baseline is asserted.
- **No new live phase**, so the count stays at 23 — the same trade `godot-darts`
  recorded, for the same reason: delivering a client affordance for a command that
  grants nothing is the surface this line exists to refuse.
