# Design — `godot-social-state`

## D1 — The capability projects **state**, not content, and not behaviour

The delivered surface is a typed read-only projection over the social fields a
committed save actually carries. It reports what is stored and refuses to imply
what it means.

Rejected: projecting the three social **content** tables. That is already owned by
`social-tables-normalization`, which explicitly classifies those rows as
"recorded display data and amounts, not implemented social behavior". Two
capabilities projecting the same rows would be drift waiting to happen.

## D2 — The zero-consumer census is **measured on every run**, never inherited

The investigation recorded 13 of 19 fields with zero occurrences of any kind.
A delivered suite that merely *asserted* `13` would be asserting a number that a
future legacy edit could invalidate silently.

The suite therefore **re-derives** the census across the declared module list on
every run and requires the recomputed set to equal the pinned expectation in both
directions. This is the same technique `godot-mission-vocabulary` uses to
re-derive its declarations from `constants.py` as bytes, and it is what turns
"the vocabulary exists and nothing read it" from an assertion into a measurement.

## D3 — Uniform emptiness is reported as **one recorded value plus its count**

Each of the 12 write-less fields holds exactly one value across 33 documents. The
projection reports that value and the document count, and refuses to synthesize a
non-empty example.

Refused: treating `{}` as "no friends exist" or `[]` as "no assists received".
Those are readings, and the corpus cannot distinguish "never used" from "reset".

## D4 — Absent is **not** empty

A field missing from a document is reported as **absent**, never coerced to the
field's committed uniform value. The distinction is load-bearing: 33/33 documents
carry all 19 keys today, so a missing key would mean a document this line has
never seen, and defaulting it would hide exactly that.

## D5 — `set_resource_allies` is recorded, not reproduced

`command.py:637` writes `map["resourceAlliesMarket"] = resource` from
**client-sent `args[0]`**, and separately stamps `item[3] = time_now` on a
client-addressed building before calling `finish_si(item)`.

The line records both effects verbatim. It **does not** reproduce them, and it
delivers **no endpoint**. This is the `godot-building-move` precedent: the
type-agnostic, client-coordinated command exists, is already documented there, and
re-deriving it here would duplicate a surface owned elsewhere.

The `item[3]` stamp is reported with **no semantics derived** — no reader of
`item[3]` is claimed.

## D6 — Naming: `godot-social-state`, after the artifact

Named for what it projects (persisted social **state**), following the
`godot-unit-definitions` / `godot-unit-instances` precedent, and deliberately not
`godot-friends`: a capability called "friends" would assert a feature the
measurement refuses.

`social-tables-normalization` remains the owner of the content tables. The two
are siblings, not overlapping, and the suite asserts that boundary.

## D7 — Anti-invention guards, proven by injection before acceptance

The line's central claim is an **absence**, and an absence is exactly what a
future contributor erases by accident. Two structural guards, both to be proven
by injection with a byte-identical restore:

1. **No social helper exists** — a pinned inventory of absent helpers
   (`assist_reward`, `friend_level`, `visit_state`, `score_for`, …), matched
   case-insensitively **and by substring** so a suffixed helper wearing the name
   is still caught. (`godot-stored-item-placement` found that an exact-name check
   missed `damage_for` when it was hunting `damage`.)
2. **No key is read as a rule** — the delivered module contains no comparison of
   one committed social value against another.

Both guards must be shown to **fail** when a violation is injected. A guard never
demonstrated failing is not a guard.

## D8 — No endpoint, no fixture, and that is the deliverable

There is no social behaviour to capture: no social command exists, and the corpus
holds no populated social field, so an executed-legacy fixture would have to
fabricate its own precondition.

Recorded explicitly, because a refusal line with no fixture can otherwise read as
an oversight. This matches `godot-unit-animations` ("no animation behaviour for
the legacy server to have") and `godot-unit-production` ("a stronger statement
than a corpus limitation").

## D9 — `questsRank` is the one field with a reader and no writer

`admin_set_quest_rank` **reads** `questsRank`; nothing writes it. It is therefore
not in the 13-field zero group, and the suite must place it correctly rather than
folding it in by name similarity.

## D10 — M11's classification advances; its exit criterion is not asserted

This line closes the **friends**, **visits**, **scores**, and **social rewards**
rows of the M11 classification by measurement. It does **not** assert M11's exit
criterion is met, and it does not modify the roadmap's status block beyond
recording the classification — the orchestrator owns that block.
