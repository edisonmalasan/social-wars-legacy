# Proposal

## Why

M10's deliver list reaches `damage`, and the committed investigation
**`docs/legacy-m10-damage.md`** (PR #294, merged `bf56c62`) establishes two
things that together decide this line's shape.

**First: the preserved server resolves no damage.** All seven committed
damage-shaping fields — `attack`, `defense`, `life`, `attack_interval`,
`attack_range`, `best_against`, `best_against_mult` — have **zero** legacy
consumers under six independent counting rules. `damage` reports 2 code-only
occurrences and **0** tokens: both are the substring inside `COST_DAMAGE_SELF`
and `COST_DAMAGE_ENEMY`. `attack` reports 42 whole-file occurrences and **0**
tokens — every one sits inside `end_attack`, `attacker`, `attacker_units`,
`flash_reload_attack`, or `ANIMATION_ATTACKING`.

**Second, and decisively: there is nowhere to store damage.** Across all ten
canonical save documents and **3,372 placed rows, every row is exactly 8 slots**
with a fixed type per slot, the complete `attr` bag union is `cp=28, nu=1,
si=53, ts=1, ui=1, xp=171`, and **zero** damage-shaped keys exist in any
`privateState`. The refusal is a property of the shape of the data, not a shrug
about missing code.

**But the same investigation found a real, state-mutating, capturable
combat-effect surface that no delivered line owns.** `buy_magic` and
`use_magic` at `command.py:652-674` maintain `privateState.magics`, a string-
keyed counter ledger — and **nothing in the repository ever reads it**. Twelve
executed transactions against `villages/Neutral.json` confirm the two adjacent
branches are not interchangeable:

- **`buy_magic` uses `+=` and is unbounded.** It adds `min(50, x + 1)`, which is
  not a cap. Executed: `2 → 3 → 7 → 15 → 31 → 63 → 113`, crossing 50 and still
  climbing.
- **`use_magic` uses `=` and can destroy spells.** It assigns `min(50, x + 1)`,
  an absolute clamp. Executed: **`113 → 50`**. A command that prints `"Used
  magic spell"` deleted 63 owned charges.

Neither branch charges anything — all **8** stored resource slots were compared
before and after twelve requests and **none moved**, with `mana` steady at 15
through a `use_magic`. And the committed magics carry **no damage amount at
all**: `Attack Boost`, whose description promises to "increase their attack and
life", has `mana 10, level 35, gold 10000, cash 30` and **no multiplier was ever
committed**.

So the line has an honest delivery available: the one combat-effect counter the
server actually maintains, delivered as a server-derived transition with the
legacy defects refused rather than reproduced.

## What Changes

- **A new `godot-damage` capability whose delivered surface is the magics counter,
  and whose primary finding is the damage refusal.** The capability name follows
  the roadmap line so the milestone cursor stays meaningful; nothing in it
  resolves or displays damage, and the refusal is enforced structurally rather
  than stated in prose (design D7).
- **A compatibility-service operation carrying intent only.** The client sends a
  validated magic identity and an action; the server derives the counter
  transition. A client-sent count or delta is refused by name. This follows the
  M10 combat-actions precedent, where the client-dictated destruction count was
  refused, and the M9 quests precedent, where the client-computed `lost` was.
- **Both legacy asymmetries are refused and recorded as divergences.** The
  unbounded `buy_magic` growth is not reproduced, and the charge-destroying
  `use_magic` decrease is not reproduced — the second is the sharpest case in the
  line, because the legacy behaviour contradicts its own printed message. Neither
  difference is reported as parity.
- **The magic identity is validated against the committed 10-entry table.** The
  legacy server accepts `99` — not a spell at all — and a **float** `1.0`
  creates a *distinct* ledger key `"1.0"` because `str(1.0) != str(1)`. Both are
  refused, and the difference is recorded as a divergence.
- **No price is charged, and the proof of that is non-tautological.** Every
  action carries a two-part post-execution proof: the counter changed by exactly
  the derived delta **and** every one of the 8 stored resource slots is unchanged.
- **The `50` cap is delivered as the recorded hardcoded literal it is.** It
  coincides with `AirStrike.cash = 50` and `Shortcircuit.level = 50`, and
  deriving it from either would invent a derivation; the rejected alternative is
  retained in the design so a later reader cannot mistake the coincidence for
  provenance.
- **The committed magics content is reported verbatim and nothing is derived from
  it**, including the Attack Boost multiplier the commit never made. The damage
  vocabulary that does exist — `COST_DAMAGE_SELF`, `COST_DAMAGE_ENEMY`,
  `tsAttacksReset`, `tsSpyingsReset`, `buy_mana_new` — is reported and never used.

## Impact

- **Affected capability:** `godot-damage` (**new**).
- **Referenced, not reimplemented:** `godot-combat-actions` (M10 line 2) owns
  `end_attack`, `kill`, `sell`, `kill_iid`, `resurrect_hero`, and the dead-hero
  ledger; `godot-mission-vocabulary` (M10 line 1) owns the 64 `MISSION_*`
  declarations, including the six combat-named types; `godot-unit-behaviors`
  (M8 line 8) owns `resurrectable`; `godot-unit-queues` owns `attr["nu"]`,
  `["ts"]`, `["ui"]`; `godot-building-construction` owns `attr["cp"]`;
  `godot-unit-instances` and `godot-unit-experience` own `attr["si"]` and
  `attr["xp"]`. This line touches none of them; `attr` keys appear in the
  evidence only as proof that the bag has no damage key.
- **Affected code:** one capture script and its parity test under
  `apps/compat-api/`, the compatibility service route and its envelope module,
  a typed read-only projection and hermetic suite under `apps/client-godot/`, and
  a live phase registered in `verify-boot.ps1`.
- **Evidence:** an executed-legacy fixture under `tests/fixtures/`, and a
  deterministic `damage-report-v1` report under `apps/client-godot/evidence/`.
- **No Flash, Ruffle, ActionScript, or browser executes**, and every network call
  is loopback.

## Non-goals

- **Resolving, computing, applying, or storing damage.** No oracle exists and no
  committed amount exists to derive one from.
- **Applying any magic effect.** `use_magic` increments a number. Nothing happens
  to any unit.
- **Charging a price** for a spell. Measured absent; charging one would be
  invention.
- **Mission completion, mission rewards, or honour.** Those are later M10 lines,
  and the investigation found no committed source from which to derive any of
  them.
- **Death.** Delivered by M10 line 2; this line touches neither `kill` nor the
  dead-hero ledger.
- **The attack allowance implied by `tsAttacksReset`.** No code enforces one, so
  no limit, window, or reset rule is claimed.
