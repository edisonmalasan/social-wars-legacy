# Design

## Context

The contract is established in `docs/legacy-unit-production.md` (PR #219). Restated compactly,
because every decision below rests on it:

- **Exactly five branches can place a row on the map** — `buy`, `place_stored_item`,
  `weekly_reward`, `pop_unit`, `resurrect_hero` (`command.py:55, 245, 353, 408, 633`). Four
  take the `item_id` **straight from the client**; `pop_unit` moves a row that already existed.
  **None** derives an id from a completed queue, a duration, or committed content.
- **No completion command** and **no elapsed-time evaluation** (already recorded by the
  `godot-unit-queues` capability).
- **`training_time` has zero legacy consumers** — the only three substring matches are
  `sm_training_time` in `soulmixer_speedup`, a different field. The committed duration is on
  **130 of 470** buildings, 0 of 429 units.
- **Six branches call `add_store_item`**; the two plausible unit sources are unvalidated:
  `buy_offer_pack` reads `package_id` and never uses it, then `json.loads` a client-sent array
  with **no lookup** into the committed table; `buy_stored_item_cash` takes one client-sent id.
  The committed `offer_packs` (44/109) and `darts_items` (27/44) tables are read by **no**
  branch.
- **`add_xp_unit` creates nothing**: it adds a **client-sent** `attr["xp"]` to a placed row,
  with a client-sent optional level used only in a print.
- **`sell`'s `KILL` reason is unreachable**, because no reason is accepted from the client.
- The corpus has **no unit row**, **no storage**, an **empty inventory**, and 40 rows across 11
  distinct ids, all committed `type` `b`.

## Decisions

**D1 — the deliverable is an explicit refusal plus an auditable inventory, not a mechanism
(the scoping decision, and the line's whole point).** There is no production behaviour to
reproduce, so a "production" feature would have to be invented. What is deliverable, and
genuinely valuable, is the **refusal made a capability** with its evidence attached: a
projection that reports a queue's presence and start instant while stating the server cannot
say whether it is ready, and the inventory naming **where** a unit could have entered the map
and showing that none of those paths derives from a queue. Without this, the corpus's
production-shaped field plus its plausible-looking `training_time` is exactly the setup for a
later line to compute a client-side readiness and call it production — which the
`building-xp` and `godot-unit-queues` lines each had to refuse ad hoc. This makes the refusal
durable instead of incidental.

**D2 — the row-entry inventory names each `item_id` source explicitly, and classifies it as
client-sent, already-existing, or derived (the auditability decision).** An inventory that
merely listed branch names would not let a reader tell a trusted derivation from a
client-supplied id. So each entry records **where the id comes from**, and the classification is
the useful part: four of five are client-sent, and `pop_unit` is a move. A reader can then see
that **no** path derives a unit from a queue — which is the claim that matters, and it is
checkable against the committed source rather than asserted.

**D3 — `training_time` is reported as content and never used as a duration (the refusal,
matching the two precedents).** The committed distribution is reported — 130 of 470 buildings
carry it, including the Command Center's `5` — together with the measured fact that **no legacy
branch reads it** and the recorded zero-consumer precedent (`unit_capacity`, the level curve's
reward fields). No production time, no remaining time, and no progress ratio is derived. This is
the third application of one rule: *a committed field with no committed consumer gets recorded,
never invented into a rule.*

**D4 — the readiness projection deliberately exposes no readiness helper, and the suite asserts
the absence (the anti-invention guard).** The module offers presence and the recorded start
instant, and the suite asserts that **no** `is_complete`, `remaining`, `progress`, or duration
helper exists on it. Asserting absence is what makes the refusal testable: a later line that
adds such a helper fails the delivered suite rather than quietly reintroducing an invented
rule. This is the same technique used for the static/instance boundary in M8 line 1.

**D5 — `add_xp_unit` is recorded and refused: no XP is awarded from a client amount
(established; the refusal is the decision).** It is the only command that writes `attr["xp"]`,
its amount is client-sent, and its optional level is client-sent and used only in a print. So
the recorded `attr["xp"]` is **read and reported as content**, never awarded, and the report
records that the committed corpus carries `attr["xp"]` on **0 of 40** rows. This also
supersedes the unit-experience gap note in `godot-building-xp`, which said unit XP was out of
scope because the corpus could not exercise it — the sharper truth is that **nothing on the
server awards it from a trusted value**.

**D6 — no endpoint and no compat change, because there is no server-derived production
(established, and the same conclusion the M8 lines 1–2 reached).** With no mechanism, there is
no intent to send and nothing to authorise, so the compat suite must stay green **unchanged**.
Stating it as a spec requirement prevents a later line assuming a production endpoint exists.

**D7 — evidence, claim limits, and containment.** A deterministic
`unit-production-report-v1` report recording the five row-entry branches with their `item_id`
sources, the committed `training_time` distribution with its zero-consumer statement, the
`add_xp_unit` contract, the acquisition-route findings, the corpus measurement, the
established-versus-derived split, and every non-claim — byte-identical across reruns. **No
windowed capture is claimed**: nothing is rendered and no unit exists to render. Containment:
no new packages, **no network at all**, both batteries plus the guard baseline, the 3,258-entry
hash manifest, and the content validator green in the final state.

## Risks / Trade-offs

- **A refusal line can feel like nothing was delivered.** Mitigated by D1's framing: it closes a
  specific, named trap, and the spec's requirements are positive statements about what the
  projection *does* report, with the absence stated as contract rather than omission.
- **A readiness projection that cannot report readiness could be mistaken for a bug.** Mitigated
  by D4's stated-absence assertion and the module's own documentation, so the absence is a
  recorded property.
- **Reporting the `training_time` distribution could invite its use.** Mitigated by D3's
  explicit statement that no legacy branch reads it and by the spec requirement barring its use
  as a duration.
- **The inventory could become stale** as later lines add entry paths. Accepted: it is scoped to
  the five branches present in the committed legacy source, which is a closed set for that
  source, and a later acquisition line would extend it explicitly.
- **No fixture could read as missing evidence.** Mitigated by the report's non-claims: there is
  no production behaviour to capture, which is a stronger statement than "the corpus could not
  exercise it".
