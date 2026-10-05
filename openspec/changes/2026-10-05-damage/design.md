# Design

## D1 — The delivered surface is the counter; the refusal is the finding

The investigation establishes that the preserved server resolves no damage and
has no field in which to store it. A line that tried to deliver "damage" would
have to invent a mechanism and an amount.

What the server *does* maintain is `privateState.magics`, a string-keyed counter
ledger written by two dispatcher branches and read by nothing. That is the only
undelivered combat-effect surface in the preserved server, and it is capturable.

So the line delivers **that counter** and refuses **damage**. The capability is
named `godot-damage` to keep the milestone cursor aligned with the roadmap's
deliver list, and design D7 makes the refusal structural so the name cannot be
read as a claim that combat damage works.

**Rejected alternative:** naming the capability `godot-magics`. It is more
accurate about the delivered surface but breaks the correspondence between the
roadmap's deliver items and the capabilities that resolve them, which is the
thing this milestone's cursor tracks. The delivered surface is stated
explicitly in the first requirement so the name is not doing load-bearing work.

## D2 — The request carries a validated identity, never a count

The request is `{user_id, action, magic_id}` and nothing else. The service
derives the transition from its own recorded state.

This is the M10 combat-actions shape (design D1 there) applied to a counter
instead of a destruction: the legacy branch trusts the client for a value the
server could compute, and the modern operation refuses that value by name
rather than ignoring it. `REASON_CLIENT_DICTATED_COUNT` is the counterpart of
`REASON_CLIENT_DICTATED_DESTRUCTION`, and the refused keys are reported through
the envelope's `refused_client_keys` so a caller can see what was dropped.

A client-sent `count`, `delta`, or `new_value` is refused with an empty payload
and no state change.

## D3 — Both legacy asymmetries are refused, and recorded as divergences

The two arms differ, and neither behaves as its name suggests:

| | legacy operator | executed result | modern |
| --- | --- | --- | --- |
| `buy_magic` | `+= min(50, x+1)` | `2 → 3 → 7 → 15 → 31 → 63 → 113`, **unbounded** | increment by 1, capped at the recorded literal |
| `use_magic` | `= min(50, x+1)` | **`113 → 50`** — 63 charges destroyed | increment by 1, capped at the recorded literal |

Reproducing either would ship a defect as parity. The unbounded growth has no
bound; the decrease destroys player property on a command whose printed message
claims the opposite. The M9 quests line refused the client-computed `lost` for
exactly this reason, and M10 line 2 refused the client-dictated destruction count.

Both differences are recorded as **divergences**. The legacy-vs-modern
difference is recorded separately from the legacy-vs-legacy difference, because
conflating them would let the second be presented as agreement with the first.

**A third divergence follows and is recorded rather than hidden:** the modern
operation applies the cap to *both* actions, where the legacy server applies it
to neither coherently. A cap the legacy arms disagree about has no recorded
rule to reproduce.

## D4 — The identity is validated against the committed table

`packages/game-content/normalized/magics.json` holds exactly **10** entries with
ids `1..10`. The modern operation refuses any id outside that table with
`unknown_magic_id`.

The legacy server validates nothing. Executed consequences:

- `buy_magic [99]` was **accepted** and created a ledger key for a spell that
  does not exist.
- `use_magic [1.0]` created the **distinct key `"1.0"`**, separate from `"1"`,
  because the branch keys on `str(magic_id)` and `str(1.0) != str(1)`. A client
  sending `1.0` instead of `1` silently acquires an unrelated ledger entry.

Refusing both is the Server v1 / M13 authority this project wants, and the
difference is recorded as a divergence. Validating an id against committed
content is the same authority M7's expansion line took when it added the two
guards the legacy server omits.

## D5 — No price is charged, and the proof is non-tautological

The probe compared **8** stored resource slots — `gold`, `wood`, `oil`, `steel`,
`cash`, `xp` from the map, and `mana`, `energy` from `privateState` — before and
after twelve requests. **None moved**, and `mana` held at 15 across a
`use_magic`.

Every action therefore carries the two-part post-execution proof the combat
line established as the family's third form:

1. the counter changed by **exactly** the derived delta, **and**
2. every stored resource is unchanged.

The second half is what makes the no-price claim non-tautological. Comparing
all **8** slots, not the M7 readout's seven, because `privateState.energy` is a
real eighth resource that the service exposes and no branch writes.

## D6 — The `50` is a literal, and the rejected derivation is retained

`min(50, ...)` appears at exactly two source lines with no reference to content.
The number 50 **does** occur among the committed magics values — as
`AirStrike.cash = 50` and `Shortcircuit.level = 50` — which is precisely the
kind of coincidence that gets mistaken for provenance.

The design retains the rejected alternative explicitly:

> **Rejected:** deriving the cap from `AirStrike.cash` or
> `Shortcircuit.level`, because the source contains no such reference. Recording
> it as content-derived would invent a derivation, which is the defect this
> project's own M8 `training_time` finding warns against. The cap is delivered
> as the hardcoded literal it is, and the suite asserts the literal is used and
> that no content lookup substitutes for it.

## D7 — The damage refusal is structural, not prose

The strongest form of the refusal is one the suite can fail. The delivered
modules SHALL contain **no** helper capable of resolving damage: no damage
amount, hit-point value, attack/defense arithmetic, multiplier, mitigation,
armour, or combat outcome.

This follows the anti-invention guard the M8 lines established, and — as on every
one of those lines — **the guard is proven by injection rather than trusted**:
an offending helper is injected, the suite is confirmed to fail with independent
failures, and the file is restored byte-identically.

A prose refusal cannot fail. A guard can.

## D8 — Committed content is reported verbatim, and one absence is named

The 10 committed magics are reported with their `mana`, `level`, `gold`, `cash`,
and `target` values exactly as normalized. Nothing is derived from them, and one
absence is named rather than left implicit:

> **`Attack Boost` has no committed multiplier.** Its description reads "Your
> units will increase their attack and life to wreak havoc on enemies!!" and its
> committed numbers are `mana 10, level 35, gold 10000, cash 30, target 1`. The
> magnitude of the boost **was never committed and is never read**. No delivered
> code may synthesize one, and the suite asserts the absence.

The wider damage vocabulary — `COST_DAMAGE_SELF`, `COST_DAMAGE_ENEMY`,
`tsAttacksReset`, `tsSpyingsReset`, `buy_mana_new`, and the six combat-named
`MISSION_*` types — is **reported and never used**.

## D9 — The branch inventory is re-derived from source bytes every run

The combat line's design D4 established that a hand-maintained inventory drifts
from the source it describes. Here the delivered suite re-derives, from
`command.py` **as bytes** on every run:

- the two branch names and their line spans,
- the 63-branch dispatcher count (cross-checked against
  `tools/command-catalog/verify_commands.py`, not a regex),
- the full 8-slot row shape,
- the complete `attr` bag key union,
- the absence of any damage-shaped key.

This is what makes the refusal a **measurement** rather than an inherited
assertion. The investigation's own first row-shape walk reported 33 documents
and 13,034 rows because it recursed into fixture steps and a Godot build cache;
an instrument that is not shown to count what it claims produces confidently
wrong numbers.

## D10 — Fixture scope

The capture uses **`villages/Neutral.json`**, the only committed corpus with a
non-empty magics ledger (`{'10': 0, '9': 1, '1': 2, '2': 0, '4': 2}`), which
makes this surface capturable where several earlier lines were not.

Recorded in the manifest: the twelve transactions, the per-step ledger before and
after, the 8-slot resource comparison, the cap-crossing step, the
charge-destroying step, the accepted out-of-table id, the float-key hazard, and
all four divergences.

**Claim limit carried into the spec:** coverage is **1 of 10** committed magics.
Ledger key `1` was driven; the other nine were observed in the corpus but not
driven. The branches are id-agnostic so the transition shape is shared, but no
per-magic behaviour is claimed — and none exists to claim.
