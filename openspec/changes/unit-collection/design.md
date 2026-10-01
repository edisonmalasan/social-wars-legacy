# Design

## Context

The contract is established in `docs/legacy-unit-collection.md` (PR #224). Restated compactly:

- **`complete_collection`** calls `get_collection_prize(collection_id)`, which does
  `index = max(0, collection - 1)`, bounds-checks `index < len(collections)`, and returns
  `json.loads(collections[index]["prize"])`; the branch grants that bag into `map["store"]` via
  `add_store_item`, then appends the id to `privateState["collections"]`.
- **Six of ten** committed collections grant a **unit** (1085, 1062, 1096, 1073, 1010, 1056); four
  grant a building (164, 45, 136, 106).
- **No eligibility check** anywhere, and **id 0 clamps to index 0**, so ids 0 and 1 alias.
- **The corpus** has `store == {}` and `collections == []`, so a grant is an observable write.
- **`collect`** re-stamps slot 3 and does nothing else; `collect`, `collect_type`, `collect_xp`,
  `max_collects`, `max_elem_vol`, `harvester` all have **zero** legacy reads.
- **0 of 429** units have `collect > 0`; the 5 `harvester` units are disjoint from any positive
  `collect`; `max_collects` is 0 on all units.
- **`unit_collections_completed`** only appends an id and grants nothing; **`collect_mission`** is
  unrelated; **`unit_collection_categories`** is read by no branch.

## Decisions

**D1 — the grant is content-derived, so the endpoint derives it and never accepts one (the
core decision).** The client sends a **collection id**; the service looks up what that collection
grants in the committed table. **No prize, id, or quantity is ever accepted from the request**,
and any such key is ignored — exactly the intent-only discipline the delivered lines use for
prices and levels. This is the first M8 endpoint whose payload is *fully* content-derived, and it
is why the line can make a strong non-tautological claim: the proof compares the granted bag
against the committed prize, not against a client-supplied expectation.

**D2 — the two authority gaps are stated requirements, not defects to fix (the honesty
decision).** Nothing verifies a collection was earned, so a client may name any of the ten; and the
one-based index makes id 0 and id 1 alias. Both are recorded as **legacy-contract facts**. Adding
an eligibility check would invent a rule the legacy server does not have — the same refusal the
project has applied to `unit_capacity`, `training_time`, and the level curve's reward fields — and
authoritative validation belongs to M13.

**D3 — the one-based index is derived-provisional, with the rejected alternative retained and the
alias named.** `collection - 1` with a `max(0, ...)` clamp implies a 1-based id. The committed
table's own `id` column runs `1`..`10` against `legacy_id` `0`..`9`, which **corroborates** the
reading — so it is recorded as derived-provisional rather than merely plausible, with the
zero-based alternative retained. The `max(0, ...)` clamp is then reported as what it is: **id 0
and id 1 resolve to the same prize**, so the model must never report id 0 as distinct from id 1.

**D4 — an acquisition-path inventory that classifies each route, because the finding changed
(the auditability decision).** The `production` line recorded that `buy_offer_pack` and
`buy_stored_item_cash` are unvalidated client-sent lists, which reads as "no committed unit is
obtainable". That is true of *those* routes and false of the server. So the inventory records each
row-entry and acquisition route with an explicit classification — **content-derived** versus
**client-supplied** — and `complete_collection` is the sole content-derived one. Without the
classification, a reader inherits the earlier, broader claim and would wrongly refuse to implement
this line.

**D5 — no unit income, no cap semantics, and no XP, each with its recorded reason (three
refusals).** No unit income because **0 of 429** units carry a positive `collect` and no collect
field is ever read, so there is nothing to derive. No cap semantics because `max_collects` is
**0 on every unit** — the cap `building-collect` deliberately refused has **no unit analogue**,
and inventing one would fabricate a threshold. No XP because `collect_xp` is never read and the
only writer takes a **client-sent** amount, which the delivered `godot-unit-production`
requirement already refuses; a collection must not reopen it.

**D6 — the fixture stops at the grant, and that is deliberate (the scope decision).** The
fixture captures `complete_collection` writing a committed **unit** prize into the corpus's empty
store — the project's **first content-derived, server-authoritative unit acquisition**, with no
fabricated player state. It does **not** chain `place_stored_item`, because the stored-item round
trip is a **carried follow-up** and delivering it here would widen the line beyond its contract.
The record states that the two steps together form a committed path, and that only the first is
delivered.

**D7 — evidence, claim limits, and containment.** A deterministic
`unit-collection-report-v1` report recording the ten committed collections with their prize
classification, the index resolution with the alias, the acquisition inventory, the two authority
gaps, the collect-field zero-consumer findings, the corpus measurement, the established-versus-
derived split, and every non-claim — byte-identical across reruns. Containment: the legacy capture
runs in a disposable copy, the service listens on loopback only, both batteries plus the guard
baseline, the 3,258-entry hash manifest, and the content validator stay green.

## Risks / Trade-offs

- **A grant with no eligibility check is exploitable.** Mitigated by D2's explicit recording and
  by D1: the *contents* are content-derived, so a client choosing the wrong collection obtains only
  what that collection genuinely grants. The eligibility gap is named for M13 rather than hidden.
- **The id-0/id-1 alias could surprise a caller.** Mitigated by D3's requirement that the model
  report the alias rather than treat id 0 as distinct.
- **Recording an acquisition route may invite an implementation of the client-sent ones.**
  Mitigated by D4's explicit classification: those routes are recorded as **client-supplied** and
  the change implements none of them.
- **The fixture stops short of placing the unit, which could read as an incomplete path.**
  Mitigated by D6's stated reason (the stored-item round trip is a separate carried follow-up).
- **`collect` on a unit could be added later by someone reading the command alone.** Mitigated by
  D5's requirement and by the suite asserting that no unit income is derived.
