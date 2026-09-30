# Design

## Context

The contract is established in `docs/legacy-production-queues.md` (PR #213). Restated
compactly, because every decision below rests on it:

- Three dispatcher branches, each taking **only a map index** (plus `unit_id` for
  `push_queue_unit2`), each doing nothing but `map_get_item` → an engine helper → a print.
  **No validation whatsoever**: not producer-ness, not `training_time`, not `min_level`, not
  a cap on `nu`.
- `nu` = count, `ts` = start instant, `ui` = optional queued unit id (atom fusion only);
  `pop_queue_unit` **deletes all three together** at zero (`engine.py:183-213`).
- **Every `attr["ts"]` use is a write or a deletion.** No branch reads a queue's elapsed
  time, so no server-side completion rule exists.
- `soulmixer_speedup` is the sole reader of `ts`; it needs `ts` **and** `ui` (so
  `KeyError` on a fresh row), reads `sm_training_time` **off the queued unit** (300 of 429
  units, 0 of 470 buildings, 84 distinct values), treats it as **seconds**, computes
  `ceil(remaining / 3600)`, **charges nothing**, sets `ts = 0`, and is commented
  *"Quite useless cost calculation for understanding it."*
- **No `complete_queue_unit` exists.** The `complete_*` family is `complete_collection`,
  `complete_goal`, `complete_tutorial`.
- `apply_resources(save, map, resources_changed)` runs **before** dispatch, with the
  request's vector.
- The corpus places **id 26, Command Center, map key 1**, `training_time` 5, `min_level` 1,
  `group_type` `COMMAND_CENTER`, row `[26, 51, 41, 0, 0, [], {}, 1]` — **empty `attr`**.

## Decisions

**D1 — the projection is read-only, and it reports presence and values without deciding
readiness (established).** A queue projection reads `nu`, `ts`, and `ui` and reports
whether a queue is present. It explicitly offers **no** `is_complete()`, no `remaining`,
and no progress ratio, because the legacy server has no such rule to reproduce and a
computed readiness would be an invented one. This is the `building-xp` no-reward
precedent applied to time.

**D2 — a recorded "no server-side completion" fact, stated as a requirement (the honesty
decision).** The spec states that no completion exists and that this capability therefore
introduces none. Without that stated, a reader would reasonably assume a missing feature;
with it, the absence is a recorded property of the legacy contract, and the `production`
line inherits a named gap rather than a silent one.

**D3 — the executed-legacy fixture is the `push`/`pop` pair against the Command Center, and
the completion question is recorded as the gap it is (established reachability).** The
corpus's real placed producer with an empty `attr` makes both commands exercisable
**without fabricating a player state** — the first M8 line that can say so. The fixture
records what a push and a pop actually do, and its manifest records that **no** completion
was captured and that none exists. The `production` line then owns the missing completion
as its finding rather than inheriting a fixture that pretends otherwise.

**D4 — a neutral resource vector, and a two-part proof that no resource moved (established
by the delivered precedent, and the reason the claim is non-tautological).** A push or pop
sends a **neutral** vector and the endpoint's post-execution proof asserts that **every
stored resource is unchanged** — the same proof form the delivered `building-xp` line
established for a command that must not move a balance. Without it, a client-sent vector
could mint or burn resources through a command dispatched like any other; with it, the
untrusted `apply_resources` path is foreclosed for this endpoint. This is the family's
**third** proof form alongside collect's "moved by exactly a derived delta" and expand's
"moved by exactly a derived debit".

**D5 — no cost, no duration semantics, and no count bound (the three refusals).** No cost
because the vector is client-sent. No duration semantics because `training_time` is a
building field no queue branch reads and `sm_training_time` is the soul-mixer path only.
No bound on `nu` because the engine sets none — **the recorded absence is not a licence to
invent a cap.** Each is stated in the spec so a later line cannot read a documented absence
as a rule.

**D6 — `soulmixer_speedup` is recorded verbatim and implemented not at all (the decision
that protects the economy).** The projection reports the recorded facts — the `ts`+`ui`
precondition, the `KeyError` on an empty `attr`, the duration's source, the seconds
reading, the cost shape, the `ts = 0` teardown, and the "quite useless" verdict — and
implements **no** cost, **no** timer, and **no** speedup. Reproducing a formula the legacy
source itself labels useless, which never charges anything, would invent an economy; this
is the same refusal the delivered XP line applied to the unread `reward_type`.

**D7 — the queued unit id is resolved through the registry, and an unresolvable id is
reported rather than dropped (established shape, derived handling).** `ui` names a unit, so
the projection resolves it against the `units` domain like any other content reference. A
queued id that does not resolve is **reported as unresolvable with its recorded value
intact** — never dropped, never coerced to a name — because `push_queue_unit2` takes the id
from the **client** and no evidence establishes which ids a client actually sends.

**D8 — evidence, claim limits, and containment.** A deterministic `unit-queues-report-v1`
report recording the three commands' effects, the recorded absence of validation, the
three-key teardown, the corpus measurement, the fixture's before/after, the
`soulmixer_speedup` facts, the established-versus-derived split, and every non-claim,
byte-identical across reruns. Containment: the legacy capture runs in a disposable copy
like the ten delivered ones, the service listens on loopback only, both batteries plus the
guard baseline, the 3,258-entry hash manifest, and the content validator stay green.

## Risks / Trade-offs

- **A queue with no completion may read as broken.** Mitigated by D2's stated requirement
  and the report's non-claims, so it reads as a recorded property.
- **Reporting an unresolvable queued id could look like a defect.** Mitigated by D7's
  explicit "recorded value intact, never coerced", since the id is client-supplied.
- **Not bounding `nu` may look like an oversight.** Mitigated by D5's statement that the
  engine sets no bound and that a cap would be invented.
- **A fixture that captures only push/pop may be mistaken for a production fixture.**
  Mitigated by D3: the manifest records that no completion exists and none was captured,
  and the `production` line owns the missing completion.
- **The `soulmixer_speedup` `KeyError` is a legacy crash.** Mitigated by recording it as an
  established failure mode rather than reproducing a crash: the projection reports the
  precondition as unmet and refuses, where the legacy code would raise.
