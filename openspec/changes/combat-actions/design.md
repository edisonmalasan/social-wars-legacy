# Design

## Context

See `proposal.md` — Why. The mechanics that matter for the *how* are recorded in
the committed investigation `docs/legacy-m10-combat.md` (PR #288): eight
executed-legacy probes plus three variants, each run against
`command.do_command` in a disposable tree, with a leaf-level diff of the save
after every request.

Three constraints shape every decision below.

1. **The preserved server resolves no combat.** `end_attack` reads a client
   payload, and its only write is a loop that subtracts two client numbers and
   removes that many rows. There is no damage, no defence, no hit chance, and no
   life arithmetic anywhere in the branch or in the committed fields that would
   express one. So a server-derived destruction **count** cannot be computed from
   combat rules — there are none to compute it with.
2. **The captured behaviour is genuinely exercisable.** `villages/AcidCaos.json`
   holds 48 committed unit rows on team one with an empty ledger, and
   `villages/Neutral.json` holds 87 with a 28-key ledger. Nothing needs to be
   manufactured, which removes the usual excuse for a refusal line.
3. **The legacy branch's two absent-value failures sit on opposite sides of its
   write loop.** Omitting the loss list raises before the save is touched;
   omitting the victim record raises after two rows are gone and the ledger is
   already incremented.

## Goals / Non-Goals

**Goals**

- Deliver the combat-resolution surface as a **server-authoritative** operation
  whose destroyed set is derived from the service's own recorded state.
- Make the discarded half of the legacy request shape **mechanically** recorded
  rather than prose, and keep it honest against future legacy edits.
- Carry the `godot-unit-behaviors` correction **in this change**, because the
  corpus measurement that falsifies its premise is what authorizes this fixture.

**Non-Goals** (design-level boundaries, not scope restatement)

- Any combat arithmetic, and any helper that could compute one.
- Mission dispatch, mission completion, and the 64 mission types.
- Honour, rewards, and resource movement of any kind.
- Occupancy, bounds, terrain, and type validation — deliberately left as Server v1
  / M13 gaps, reproducing the legacy branch's absence rather than filling it.
- Re-delivering the dead-hero ledger, `resurrect_hero`, or `sell`.

## Decisions

### D1 — The request addresses a unit identity, and the service destroys exactly one eligible row

**Chosen.** The request carries the **identity** of the unit that was lost (its
committed item id). The service derives the eligible rows — placed rows whose
recorded item id matches and whose recorded team is truthy — takes the **first**
one by recorded map-key order, removes it, and writes the ledger increment if the
row satisfies both ledger gates. The destruction count is therefore **always
one**, derived from the service's own state rather than supplied.

**Why not derive the count from the payload.** There is no rule to derive it
with (constraint 1). The only arithmetic the legacy branch performs is
`max(0, unit[2] - unit[3])` on two client numbers, and the semantics of those
two operands are established nowhere in the preserved source — `unit[2]` is
labelled `A` and `unit[3]` `B`, with the comment "number of loses is A - B".
Reproducing that subtraction would make the server a pass-through for a
client-computed casualty figure, which is the `AGENTS.md` "Bad" pattern and the
same anti-pattern the M9 `quests` line refused in `end_quest`.

**Why not refuse the whole operation.** A refusal would deliver nothing while
the corpus demonstrably exercises the branch, and it would leave the recorded
divergence undocumented. One-per-identity is the largest destruction the service
can justify without inventing a combat rule, and it is the shape the
`godot-stored-item-placement` line already established: client names the item,
server derives the instance.

**Alternatives considered.** *(a)* Reproduce the client subtraction — rejected as
the Bad pattern. *(b)* Accept the count but clamp it to available rows — rejected,
because the clamp legitimises the client number; the legacy branch's apparent
safety in probe P4 is exhaustion of matches, not a check, and mistaking one for
the other is how an untrusted count survives review. *(c)* Derive the count from
`attack` against `defense` in committed content — rejected because both have
**zero** legacy consumers, so any formula would be invented.

### D2 — Refusal of a client-dictated count is a named, separate guard

Any request field carrying a destruction count, a `sent`/`survived` pair, or the
legacy payload key is **refused before dispatch** with a named code, an empty
payload, and no state change. This is a distinct guard from the D1 eligibility
check so a caller can tell "you sent something I refuse" from "nothing to
destroy", and so the refusal is testable without an eligible row existing.

### D3 — Validation completes before the write step, proven by injection

Every structural and content check runs before any row is removed. The two
legacy absent-value failures bracket the write loop (constraint 3), so the
ordering is load-bearing rather than stylistic. Two guards back this: the
delivered flow's inventory is pinned whole, and a deliberately injected
destroy-helper placed after a validation branch is **proven to fail** the suite
before the guard is trusted. A containment or ordering guarantee established only
by the happy path is not a guarantee — the investigation recorded exactly that
failure when its first probe run aborted before its cleanup existed.

### D4 — The request's field inventory is re-derived from `command.py` bytes every run

The twelve read keys and the nine that reach nothing are **re-derived from the
preserved source on every verification run** and compared for exact identity, so
a legacy edit fails the suite instead of silently contradicting the record. The
inventory is not transcribed into a committed table, because a transcribed table
can only be checked by a human reading both sides.

The delivered suite additionally asserts that the delivered code declares **no**
helper capable of deriving the discarded values — no duration, honour, reward,
damage, or mission-completion computation — so the non-claims are structural.
That guard is proven by injection rather than trusted.

### D5 — `kill_iid` is delivered as a proven no-op, not refused

The branch contains no write statement at all, which is a stronger statement than
any single request showing nothing changed. It is therefore delivered as a
command with an empty recorded contract. The alternative — refusing a command
that does nothing — would misrepresent the preserved server as having a rule to
violate.

### D6 — The merged-spec correction is carried here, not deferred

`godot-unit-behaviors` asserts no fixture on a premise this milestone falsifies,
and that premise is in a merged requirement's SHALL text and a scenario.
Deferring the correction would land a sibling capability's executed fixture
beside a merged requirement saying the fixture was uncapturable — two merged
specs contradicting each other about the same repository. This is the M8-line-5
precedent: the `production` line's acquisition finding was *completed* by the
`collection` line rather than left standing, because the delta falsified it.

The correction is carried as two `MODIFIED` requirements. It deliberately does
**not** modify that capability's "no combat is resolved" requirement, which
remains true: this change resolves no combat, because the preserved server
resolves none either.

### D7 — The team asymmetry is recorded, not exercised and not refused

`map_lose_item` accepts any **truthy** recorded team; `push_dead_unit` records only
team one. So a non-team-one unit row would be destroyed yet never enter the
ledger. **All 441 committed unit rows are team one**, so the case is unreachable
from the committed corpus. It is recorded as a code fact with an explicit
"not exercised" status. It is not refused, because refusing it would invent a
bound the oracle does not have — the same reasoning that leaves the M6 geometry
gap recorded rather than closed.

### D8 — Fixture coverage spans two committed documents, chosen by what each holds

`AcidCaos.json` for the destruction path (48 committed unit rows, empty ledger, so
the ledger increment is unambiguous), `Neutral.json` for the ledger path (a
committed 28-key ledger, so a decrement is observable against existing state).
Both are committed and both pass the legacy loader's validator unchanged.

## Risks / Trade-offs

- **[The divergence is large]** — the legacy server can destroy an arbitrary
  number of rows from one request where this operation destroys at most one. The
  divergence is deliberate and is recorded as such rather than narrowed, because
  closing it would require a combat rule the preserved source does not contain.
  Mitigation: the divergence is a named scenario in the new capability and a
  dedicated fixture field, so it cannot be reported as parity by omission.
- **[Capping destruction at one may be wrong]** — if the real client reports a
  multi-unit loss in one payload, this operation under-delivers against it. No
  evidence either way exists, since the Flash client was never observed. Mitigation:
  recorded as a claim limit naming the unobserved request shape.
- **[The two references can drift]** — `godot-unit-behaviors` and this capability
  both describe the ledger's fourth door. Mitigation: both name the other by
  capability id, and each asserts the other exists and asserts the same fact,
  so a reader of either alone is directed to the owner of the other.
- **[The corrected counts may grow]** — future lines measure more corpora and the
  numbers in the corrected requirement are a measurement, not a constant.
  Mitigation: the requirement states they were measured, and the delivered report
  re-measures them per run.
- **[Two more hermetic suites raise two other suites' counts]** — `test_project_scope.gd`
  and the client-source-walking suites count added sources, so their pinned counts
  rise. Mitigation: re-measure rather than assert the pre-change figures.

## Migration Plan

Not applicable in the deployment sense. This change adds a compatibility-service
endpoint and a read-only client projection, modifies no preserved byte, and
migrates no data. Rollback is reverting the change; the recorded fixtures and
reports are additive and inert.

The compatibility service continues to bind `127.0.0.1:5056` only, and every
network call in verification remains loopback.

## Open Questions

None that affect the specs, the approach, or the task breakdown. The following
are recorded in the investigation as deferrable and are deliberately left open:
whether the unobserved Flash client ever sent a multi-unit loss in one payload;
what the legacy payload's `A` and `B` operands mean; and why four of the M8
combat-field figures reproduce under no counting rule measured — a question for
the line that owns those fields, not this one.