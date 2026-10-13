# Design

## Context

`end_attack` (`command.py:808-885`) is the top-ranked target of
`docs/legacy-m13-line4-candidates.md` §6.1 and the highest-ranked branch of the M13
D6 pool. This design re-derives every ranking-relevant figure, and its central
consequence is that **the line derives nothing** (§4 of the selection record: **0 of
29** remaining pool branches have a committed value naming their outcome).

### The branch, read as executed

```python
elif cmd == "end_attack":                              # :808
    response = None
    unknown = args[1]                                   # :810  read, never used
    try:
        response = json.loads(args[0])                  # :813
    except:
        print("Error: Failed to parse command."); return
    if not response:
        print("Error: Failed to parse command."); return  # :818  empty blob = success
    voluntary_end = True                                # :826
    victim = None                                       # :827   deref :874
    attacker = None
    resources = None
    honor = 0
    duration = 0
    townhall_gold = 0
    win = False                                         # :833
    different_island = True
    victim_units = None
    attacker_units = None                               # :836   deref :866
    resources_victim = None
    ...                                                 # :839-862  twelve fields
    privateState = save["privateState"]
    for unit in attacker_units:                         # :866
        lost = max(0, unit[2] - unit[3])  # number of loses is A - B   :868
        if lost > 0:
            print(f"Lost {lost} {get_name_from_item_id(unit[0])}(s)")
            map_lose_item(map, privateState, unit[0], lost)   # :872
    if "name" in victim:                                # :874
```

Five measured properties, each of which carries a decision below:

1. **The branch's entire stored effect is one call.** `map_lose_item` at `:872` is
   the only mutation. The count of `map_*`/`add_*`/`pop_*`/`set_*` calls in the body
   is **0**. Span confirmed: header `:808`, last executable line **884**, `:885`
   blank, next `elif` `rt_open_graph_unit` at `:886`. This reproduces
   `legacy_branches.spans["end_attack"] == [808, 885]` in `tools/route-coverage`.
2. **The count is a subtraction of two client numbers with no names.**
   `command.py:867`'s own comment is `# item_id (not on map), sent_to_battle, A, B`.
   `A` and `B` are the branch's entire vocabulary for what it destroys.
3. **Twelve blob fields; three read after assignment; one reaches stored state.**
   Read after assignment: `attacker_units` (`:866`, drives the mutation), `victim`
   (`:874`) and `win` (`:876/:881/:883`) — and `victim`/`win` are read only to build
   `print` strings. Assigned and never read: `voluntary_end`, `attacker`, `resources`,
   `honor`, `duration`, `townhall_gold`, `different_island`, `victim_units`,
   `resources_victim`. This is a **direct read of the span**. It is deliberately not
   the selection record's "uses after assignment" tally, which §9.6 of that record
   records as over-counting because it counted the pre-initialiser lines `:826-837`.
4. **Two unguarded `None` dereferences.** `victim` at `:827`→`:874` and
   `attacker_units` at `:836`→`:866`. Both are reachable **and both were executed**:
   fixture steps **2** and **4** answer HTTP **500**.
5. **One request writes two pieces of authoritative state.** `map_lose_item`
   (`engine.py:215-228`) calls `push_dead_unit` at `:223`, which writes
   `privateState["deadHeroes"]`.

### The one mutation, and its only two doors

```python
def map_lose_item(map, privateState, item_id, qty):        # engine.py:215-228
    ...
    while qty > 0:                                          # :218
        ...                                                 # :221  slot 0 == item_id and truthy team
        push_dead_unit(privateState, row)                   # :223
```

- **`map_lose_item` has exactly two call sites in the whole preserved source**:
  `command.py:796` (`end_quest`) and `command.py:872` (`end_attack`). Measured, not
  inferred. `godot-unit-behaviors` claimed the ledger has "three doors"; that figure
  counted `push_dead_unit`'s own two callers and `map_lose_item` separately. This
  line's reading is: **two branches reach `map_lose_item`, and one helper
  (`map_lose_item`) reaches `push_dead_unit`.**
- **The safety is exhaustion, not a check.** `while qty > 0` returns the moment a
  pass finds no match, so the count is an **upper bound realised from the save**. A
  client asking for nine rows on a map holding one destroys one — silently.
- **The row is selected by item id (slot 0) plus a truthy team (slot 7)** at
  `engine.py:221`, popped in the save's own recorded map-key order. The committed
  fixture records this end to end: the oracle removed `2425`, the **first key in the
  committed village document's own order**, not the lowest key and not the first key
  of the sorted snapshot.

### The two committed gates, and the asymmetry between them

`push_dead_unit` (`engine.py:149-170`) gates the ledger increment behind **two**
conditions, and only two:

| # | Gate | Line | Measured behaviour |
|---|---|---|---|
| 1 | the row's player team is `1` | `engine.py:151` | `if item[7] != 1: return False` — **exactly** team 1, not any truthy value |
| 2 | committed `resurrectable > 0` | `engine.py:159,162` | an **absent** key returns `False`; it is never read as `0` |

`resurrectable` is the **only** committed combat field with real consumers, and its
consumers are exactly these two reads. The gates belong to `godot-unit-behaviors`,
which owns the ledger; this line reports them and acts on neither.

**The asymmetry, measured:** `map_lose_item` accepts **any truthy** team
(`engine.py:221`) while `push_dead_unit` requires **exactly** team 1. So on a team-3
row the legacy server **destroys the row and credits nothing**. Every one of the
committed unit rows is on team 1, so the fixture records the asymmetry and exercises
nothing.

### Corpus feasibility

| Fact | Value |
|---|---|
| `tests/saves/fresh-player.json` placed rows | **40**, **11** distinct ids, **0** unit rows |
| its `privateState.deadHeroes` | `{}` |
| its `maps[0].store` | `{}` |
| its team slots | `{1, 3}` |
| committed **unit** ids | **429**, all `type: "u"`, distinct `legacy_id`s over `923..1431` |
| committed building ids / specials | **470** all `type: "b"` / **1** `type: "l"` |
| **overlap between the three committed id spaces** | **0** |
| `villages/` rows carrying a team slot | **3292**, of which **2410** on team 1 |

Three consequences:

- **A destruction is reachable on the fresh corpus, and a ledger credit is not.** Any
  of its 40 rows carries a truthy team, so `map_lose_item` would destroy it; but every
  one is a committed **building**, and `push_dead_unit` would then read that building's
  committed `resurrectable` — absent on all 470 — and credit nothing. The **fresh**
  corpus can demonstrate a destruction and cannot demonstrate a ledger movement.
- **The unit half is exercisable only against a village corpus**, so the live phase
  drives the *gate reporting* over the fresh corpus and states the absence rather
  than refusing on it.
- **Zero id-space overlap** means validating `unit_id` against the committed **unit**
  space cannot accidentally accept a building or a special. That is a measurement,
  not an assumption, and the hermetic suite re-derives it every run.

### Fixture strength

`tests/fixtures/godot-combat-actions/` holds **13 transactions** plus one recorded
login, over **14** `request.json` files. Measured by this line:

| Rule | `end_attack` |
|---|---|
| steps carrying the branch | **10** |
| dedicated — carries the branch and no other **branch** | **10** |
| dedicated — carries the branch and no other **occurrence** | **9** |
| occurrences | **11** |

The 10/9 split is **rule-dependent, not a discrepancy**: `txn_resolve_batch_discarded_on_raise`
carries `end_attack` twice, so it is dedicated under one rule and not under the other.
The selection record §10.3 records exactly this and resolves it to 10 with the rule
named; this line uses **10** (branch-set difference) and states the rule. `kill` is 2
steps / 2 dedicated, `kill_iid` 1 / 1. The arithmetic closes: 10 + 2 + 1 + 1 login = 14.

This is the **second**-strongest fixture in the repository and the strongest in the
pool. Its **13 transactions** include three HTTP-500 raises, one empty-blob success,
one two-row destruction, one no-eligible-row success, and one key-creation and one
increment on the ledger across two different seeds. Under a **neutral** vector,
**every stored resource is byte-identical in all thirteen**.

**No new executed-legacy fixture is captured by this line, and none is needed.** The
existing 13-transaction set *is* the oracle, it was captured on `2026-10-05` by a
delivered line, and re-capturing it would produce the same bytes for a different
commit. It is read as committed bytes and never re-captured.

### Ownership, measured

- `openspec/specs/godot-combat-actions/spec.md` owns the **v0** client surface for
  `/v0/combat`, the `CLIENT_DICTATED_REFUSAL`, the twelve-field inventory, the two
  `None` dereferences, the order-of-record finding and the recorded divergence.
- `openspec/specs/godot-quests/spec.md` owns `end_quest`'s identical refusal.
- `openspec/specs/godot-unit-behaviors/spec.md` owns the dead-hero ledger and the two
  `push_dead_unit` gates.
- `openspec/specs/godot-mission-vocabulary/spec.md` owns mission vocabulary.
- **No spec names any `/v1/` route path.**

This line therefore specifies **authority** over the same surface and **re-specifies
none** of the four capabilities above, in the same way line 3 left
`godot-damage`'s v0 surface untouched.

## Goals / Non-Goals

**Goals**

- Close the client's ability to name **how many rows** a combat resolution destroys.
- Report, from committed content and recorded state, the two gates the preserved
  server would have applied — without acting on either.
- Prove the refusal by the strongest available instrument: **whole-document
  byte-identity, including the dead-hero ledger.**
- Demonstrate on the boundary a fourth worked transaction of a category none of the
  first three covers: one that **moves no stored resource and destroys no row**.

**Non-Goals**

- No derivation of anything. §4 of the selection record is the reason.
- No change to `apps/compat-api/**`; it stays the oracle.
- No re-specification of `godot-combat-actions`'s delivered v0 surface.
- No `kill`, no `kill_iid`, no `end_quest` (D11).
- No SQL / PostgreSQL / Alembic (line 1's D4 defers them).
- No mission, damage, honour, reward, XP, or resource movement.
- No occupancy, bounds, type, or terrain validation.
- No claim about Flash client behaviour.

## Established vs Derived

The boundary capability requires every v1 claim to be labelled. This line's split:

**ESTABLISHED** — observed in committed legacy source or in executed-legacy evidence:

- The span `:808-885`, the single mutation at `:872`, and **0** other
  `map_*`/`add_*`/`pop_*`/`set_*` calls in the body.
- `lost = max(0, unit[2] - unit[3])` at `:868`, on two client numbers the branch's own
  comment at `:867` labels only `A` and `B`.
- The twelve copied blob fields, the three read after assignment, and that only
  `attacker_units` reaches stored state.
- `unknown = args[1]` at `:810`, read and never used.
- `map_lose_item`'s two call sites, its `while qty > 0` exhaustion semantics, and its
  `slot 0 == item_id and truthy team` selection at `engine.py:221`.
- Both `None` dereferences being reachable — **executed**, fixture steps 2 and 4,
  HTTP 500, save byte-identical.
- A raise anywhere skipping `save_session` entirely (`command.py:30,32`), so the batch
  is the persistence boundary and the failure mode is a discarded save, never a
  partially applied one.
- An empty blob answering success with no change (`command.py:818`, fixture step 3).
- The two `push_dead_unit` gates, verbatim, including that an absent committed
  `resurrectable` returns `False` and is never read as `0`.
- The census: `attack` 12/10/5/5/0/0 with all twelve inside longer identifiers, and
  **0** in every view for the nine other committed combat fields.
- **No stored resource moves** across all thirteen executed transactions, under a
  neutral vector.
- The measured divergence at fixture step **7**: `A=3, B=1` destroyed **two** rows in
  the oracle and **one** at v0.
- Every one of the fresh corpus's 40 rows being a committed **building**, so no unit
  row can be addressed there.

**DERIVED** — chosen by this design, never observed from the Flash client. Each
carries its rejected alternative below.

- D1 the route shape and the action vocabulary.
- D2 **the refusal of the destruction entirely** (the *refusal* is derived; the
  absence of any derivable count is established).
- D3 the gate reporting, including reporting absence rather than refusing on it.
- D4 the structural closure of the `attacker_units` shape.
- D5 the refusal vocabulary.
- D6 the proof shape.
- D7 the oracle-untouched posture.
- D8 the arithmetic.
- D9 the anti-invention guards.
- D11 the exclusion of `end_quest`.

**The one thing this line establishes that no earlier line did:** that **the strongest
available proof on this boundary is not "no resource moved" but "the whole persisted
document is byte-identical."** Line 1 proved a derived amount was exactly right; line
2 proved a grant was exactly the committed prize; line 3 proved no resource moved. A
destruction moves a **row** and a **ledger key**, so only whole-document identity
covers it.

## Decisions

### D1 — One route, `POST /v1/combat`, one action, one identity field

The request is `{player_id, unit_id}`, where `unit_id` is a **required integer**
naming a committed unit row. There is no operation field and no action field: the
route has exactly one thing it can do, and a second operation name over it would be
line 3's D7 problem restated on a route that has nothing to distinguish.

The identity is the committed item id, matching v0's own `ACTION_ADDRESSING_KEY` for
`resolve` (`"item_id"`), for the same reason line 2 matched `collection_envelope`'s
id: a migrating client must be able to send what it sent, and v1 then refuses the
part it may not send.

**The action vocabulary is v1's own, not `command.py`'s branch name.** Naming a v1
route `/v1/end_attack` would make v1's vocabulary a subset of the 63 branch names,
which is the inheritance the boundary exists to stop (line 2's recorded reasoning).

**Rejected alternative:** `POST /v1/combat/resolve`. Rejected: one route with one
action is one fact, and a path segment that cannot vary adds a second `KNOWN_ROUTE_PATHS`
entry, a second route-literal, and a client string that must agree, for zero
information.

**Rejected alternative:** carry all three of v0's actions (`resolve`, `kill`,
`kill_iid`) on one v1 route. Rejected: they are three **different branches**
(`end_attack`, `command.py:169-181`; `kill_iid`, `command.py:183-187`), `kill` deletes
by **map key** and holds no `push_dead_unit` call at all, and `kill_iid`'s entire body
is one `print` with no write statement. Bundling them would put one branch's deletion
semantics and a proven no-op behind one route, and would blur the very fact the
fixture records as established — that the ledger's non-participation is a property of
`kill` rather than of combat.

**Rejected alternative:** address by map key, as `kill` does. Rejected: `end_attack`'s
subject is the per-tuple item id at `command.py:870` (`item = unit[0]`), not a map key,
and the two addressings are not interchangeable — the fresh corpus has 40 map keys and
0 unit rows, so a map-key route would be exercisable while an item-id route is not,
and choosing the exercisable one would be choosing against the branch.

### D2 — No derivation. The destruction is refused in full, and nothing is destroyed

The route **never** destroys a row and **never** increments the ledger. It resolves
the identity, reports the gates, reports the client-dictated count it will not apply,
and leaves the document untouched.

Six inputs, each measured:

1. **The only quantity the branch computes is a subtraction of two client numbers**
   whose labels are `A` and `B` (`command.py:867-868`). There is nothing else in the
   body.
2. **No committed field names the outcome.** The six-rule census above: nine committed
   combat fields measure **0** in every view; `attack` — the only one that appears at
   all — is a substring artefact whose whole-word count is **0**.
3. **`0 of 29`** remaining pool branches have a committed value naming their outcome
   (selection record §4). This is not a property of `end_attack`; it is the state of
   the pool.
4. **The fixture measured the oracle destroying two rows** for one client figure
   (step 7). A rule that could have chosen two would have to be `A - B`.
5. **The team asymmetry** means even a correctly-counted destruction is not
   self-consistent: a team-3 row is destroyed and credited nothing.
6. **Nothing in the branch reads `attack`, `defense`, `life`, `attack_interval`,
   `attack_range`, `best_against` or `best_against_mult`.** There is no rule to
   reproduce because there is no rule.

**Rejected alternative:** destroy exactly **one** row, as v0 does. Rejected because
that `1` is a property of `combat_payload`'s construction — executing
`combat_payload('resolve')` returns `{"attacker_units":[[0,0,1,0]],...}`, the trailing
`0` being `_DERIVED_IDENTITY` — and the same v0 route destroyed **two** rows for the
client figure `A=3, B=1`. Promoting a fixture's convenience into server authority is
the same class of error as promoting a test's input into a schema.

**Rejected alternative:** destroy **every eligible row** for the addressed identity,
dropping the count entirely and letting `map_lose_item`'s exhaustion bound it.
Rejected: this is the client-dictated destruction wearing a different spelling. The
client still chooses *which* unit and the server still cannot say how many; and the
bound is realised from the save, so a client naming a unit with no matching row gets a
**silent success** and no destruction at all — which is the legacy behaviour as an
authority hole rather than as parity.

**Rejected alternative:** derive the count from committed `attack` minus committed
`defense`. Rejected: neither field is read by anything; `attack` is not even a
whole-word occurrence; and a number nothing reads cannot name an outcome.

**Rejected alternative:** derive nothing and let the **client** destroy, i.e. ship only
the gate reporting and no refusal. Rejected: it would leave `AGENTS.md`'s named
anti-pattern — "client dictates authoritative outcome" — in place while adding a route
that appears to authorise combat.

### D3 — The two committed gates are resolved and reported, never acted on

The response reports, for the addressed identity:

- the committed `resurrectable` value **verbatim**, and whether the second gate would
  pass;
- whether a row for that item id is **present** on the recorded map, and if so its
  recorded player team and whether the first gate would pass — and, when no row is
  present, that fact reported as an absence with `null` values, **not** as a refusal;
- the **team asymmetry** between `map_lose_item`'s truthy test and `push_dead_unit`'s
  exact-`1` test, stated plainly.

Reporting rather than enforcing is the decision, and it is v0's established posture
carried forward: `combat_envelope.TEAM_ASYMMETRY` already records the asymmetry
without exercising or refusing it, because every one of the committed unit rows is on
team 1.

The gates are read from **committed content** through the existing content registry
and from **recorded state** through the repository seam. Neither is transcribed.

**Rejected alternative:** enforce the gates, refusing a resolve on a team-3 row or a
unit whose committed `resurrectable` is absent. Rejected: the refusal would fire on
corpus-real states for a reason the client cannot act on, and the transaction has
nothing to gate — it destroys nothing (D2). A gate in front of no operation is a
decoration, and the reporting posture states the same facts without inventing an
outcome.

**Rejected alternative:** report only `resurrectable` and skip the team, because the
team lives in the save and a client sending an unplaced identity has no team.
Rejected: the **absence of a row** is the more informative report, and reporting it as
a fact rather than as a refusal is precisely what distinguishes this route from one
that refuses everything the fresh corpus contains.

### D4 — The two `None` dereferences are closed structurally, and the split is stated

v1's request carries a single identity. There is no `attacker_units` field, so the
`for unit in attacker_units:` raise at `:866` is **not representable** — the shape
that causes it has no request encoding. The `victim` raise at `:874` is likewise not
representable: there is no `victim` field. What v1 *does* is refuse, before dispatch,
any request whose body carries an `attacker_units`, `victim`, or `victim_units` key,
with `client_supplied_delta` (400) or `unknown_request_field` (400) as the closed
structural channels already provide, and it **asserts** that no delivered code path
can reach either dereference.

**The established/unknown split, stated precisely because it is the sharpest one in
this proposal:**

| Claim | Status |
|---|---|
| Both raises are **reachable** in the preserved server | **established by execution** — fixture steps 2 and 4, HTTP 500, save byte-identical |
| A raise anywhere **discards** the whole save rather than partially applying it | **established** — `command.py:30,32` |
| Whether a **real client** ever sent either malformed shape | **unknown** |
| What the twelve fields meant to the Flash client | **unknown, permanently** |

Reachability was **executed**, not reasoned. What is unknown is only the real client's
behaviour, which no amount of repository measurement can recover. §8 of the selection
record describes the reachability as unknown and says this record "did not execute a
probe"; that is true of *that* record and **false of the fixture**, which predates it.
The correction is recorded in §Corrections below and the selection record is not
edited.

**Rejected alternative:** reproduce the 500s. Rejected: an HTTP 500 is not a contract.
v1 refuses with a named code and leaves the document byte-identical, which is what the
oracle's *persistence* behaviour already achieved — the raise and the byte-identity
were both measured, and only the second is worth keeping.

### D5 — Exactly one new refusal code, and the `< 20` pin is amended rather than evaded

New code, in `server_v1_refusals.py` only:

| Code | Status | Meaning |
| --- | --- | --- |
| `client_dictated_destruction` | 409 | the request attempts to name a destruction, a casualty count, or a damage/loss figure |

Reused codes: `malformed_request` (400) for a missing field or a non-integer
`unit_id`; `client_supplied_delta` (400) for any resource, damage, result, outcome,
life, hp or health key; `unknown_request_field` (400) for anything else;
`unknown_player` (404); `unreadable_state` (500) for a save that cannot be read.

**Why the code is new rather than a reuse of `CLIENT_SUPPLIED_DELTA`.** Two costs,
both structural:

1. **It belongs to the wrong layer.** `client_supplied_delta` is decided by
   `server_v1_intent.parse_intent` on **key names alone**, before any domain code
   runs, and it is a 400 structural category. A decision about **what the transaction
   would have destroyed** is a domain decision; having the domain raise a code the
   intent layer owns is the layer blur line 2 recorded and forbids.
2. **It is the wrong status band.** A structural key-name rejection is 400; a request
   whose content asks the server to destroy rows is a **conflict with the recorded
   document**, which is what the other 409 codes mean (`capped_collection`,
   `below_first_rung`, `construction_in_progress`, `counter_above_cap`).

The shape is genuinely not a delta: `server_v1_intent.DELTA_KEYS` **already** contains
`damage`, `result`, `outcome`, `life`, `hp`, `health`. So a request carrying
`"damage": 3` is refused `client_supplied_delta` (400) by the intent layer, while a
request carrying `"attacker_units": [[0,0,3,1]]` — the branch's actual wire shape — is
refused `client_dictated_destruction` (409) by the domain. Two different answers for
two different encodings of the same request, which is correct: they are different
mistakes.

**The measured consequence, and the amendment.** The closed table holds **19** codes.
`apps/server-v1/tests/test_boundary_invariant.py:492` asserts
`self.assertLess(len(list(RefusalCode)), 20)`. One new code makes it **exactly 20** and
fails. So this line **amends the pin to `< 21`**, and records why rather than
silently bumping it:

- **The pin was written to force exactly this argument into the open.** A bound that
  cannot be reached without a decision is a decision prompt. Three lines have now
  answered it: line 2 added three (17), line 3 added two and deliberately stayed
  under it (19), and this line is the first to need the ceiling itself to move.
- **The amendment is recorded with its rationale, in the changed file**, so the next
  reader sees that 21 was chosen rather than typed.
- **Line 3's own pin on the pin must move with it.** `test_magic.py:2024` and `:2039`
  both assert `assertEqual(19, len(list(RefusalCode)))`, and `:2037` asserts the
  **exact spelling** of the boundary invariant's line
  (`"self.assertLess(len(list(RefusalCode)), 20)"`). Amending only the guard would
  break a suite that is guarding the guard.

**Rejected alternative:** reuse `CLIENT_SUPPLIED_DELTA` and add **no** code. Rejected
for the two reasons above. It is retained here as a real option, not a strawman: it is
what line 3's design chose for its identity-form refusals, where `malformed_request`
was already the right channel. Here it is not.

**Rejected alternative:** add three codes, one per un-derivable quantity (destruction,
honour, resources). Rejected: `honor`, `resources`, `resources_victim` and
`townhall_gold` are read and discarded by the branch and are closed by the existing
`client_supplied_delta` key-name channel, and three codes for one decision is how a
closed vocabulary stops being closed.

### D6 — The post-execution proof is two-part, and only its second half is evidential

1. **Specification half.** The identity resolves to a committed unit row; the response
   reports the committed `resurrectable` verbatim, the recorded team (or its absence),
   each gate's pass/fail, the asymmetry statement, and the client-dictated count the
   route **refused to apply** together with the named code that refused it.
2. **Falsifiable half.** **The entire persisted document is byte-identical** to its
   pre-request bytes — *every* key, including `privateState["deadHeroes"]`, the placed
   rows, the map level, the storage and the player info.

**Why half 2 is not tautological, stated precisely.** Half 1 is a *specification*
check: v1 is the only implementation writing the save on this path, so comparing v1's
report against v1's own derivation could not fail for an interesting reason, and it is
presented as such rather than dressed as parity with a preserved branch that is not
executed here.

Half 2 is falsifiable **because of D2**, and it is the strongest such instrument in
this project. Every alternative this design rejected — destroy one, destroy every
eligible row, destroy `A - B` — moves at least one leaf, and every one of them moves
one through `map_lose_item`, which either deletes a row from `maps[0].items` or
increments `privateState["deadHeroes"]` at `engine.py:223`. Both are inside half 2's
scope, so **any** destruction of **any** size at **any** identity fails it. Line 1's
proof could be satisfied by a wrong amount; line 2's by a wrong prize; line 3's by a
single debited resource. This one cannot be satisfied by a wrong destruction, because
it does not admit one.

**Ordering is load-bearing.** The leaf census runs **before** the whole-document
comparison, so a destruction surfaces as *which leaves moved* rather than only as a
document diff. Line 3's suite had the opposite order available and recorded why the
ordering matters; this line fixes it deliberately.

A **refused** request leaves the whole document byte-identical, and the suite asserts
that for each refusal independently rather than once.

### D7 — `apps/compat-api/**` is untouched, and the recorded baseline is re-run

The oracle is not the thing being replaced. This change adds no v0 route and edits no
v0 file. `/v0/combat` keeps its `resolve` action, its `CLIENT_DICTATED_REFUSAL`, its
`destruction: 1` and its recorded divergence at fixture step 7 — all of which are
`godot-combat-actions`' delivered surface, and none of which this line re-decides.

The Compatibility API suite therefore stays at its recorded **3077** as a **verified**
figure: re-run and reported, exactly as `godot-friends` and
`godot-construction-assist` did, and as this repository has twice had to learn the
hard way. Confirmed structurally by `git diff --name-only -- apps/compat-api` returning
no path.

### D8 — The arithmetic moves by exactly one, and the routed/unrouted split does not move

| Figure | Before | After |
| --- | --- | --- |
| Named legacy branches | **63** | **63** |
| Dispatched by a v0 route / by none | **39** / **24** | **39** / **24** — **unchanged** |
| v1 routes | **3** | **4** |
| Authoritative v1 branches | **4** (`collect`, `complete_collection`, `buy_magic`, `use_magic`) | **5** (+ `end_attack`) |
| Branches without an authoritative v1 route | **59** | **58** |
| v0 routes | **24** | **24** — **unchanged** |
| Non-authoritative v0 routes | **21** | **20** |

The routed/unrouted split does **not** move, because `/v1/combat` is a **v1** route and
adds no v0 route. `docs/legacy-m13-unrouted-branches.md` is **not** edited and
`tools/route-coverage/` is untouched; its suite re-runs at **44** as a verification.

The **39**/**24** pair is the corrected one, re-measured by executing every committed
envelope builder and reading the branch out of the batch it returns. The withdrawn
**40**/**23** pair and the withdrawn non-authoritative total of **62** are not reused
anywhere in this change.

### D9 — Anti-invention guards, proven by injection rather than trusted

The boundary's established shape is that an absence is a **structural guard**, not a
comment, and that the guard is **measured to fire**:

- **Whole function inventory pinned** for the new domain module, so any added helper
  fails. The inventory is the real gate; the reserved-stem list is the belt — the
  pattern `godot-friends` and `godot-construction-assist` both measured, and
  `godot-friends` measured that an exact-name check misses a **suffixed** helper, so
  the stem guard is a case-folded **substring** match in **both** directions.
- **No arithmetic over any committed value or client value** in the domain module: no
  `*`, `/`, `%`, `**`, `<<` or `&` node anywhere in it. The same shape
  `test_combat_actions.gd` already applies to its own module, so the claim is
  mechanically true rather than argued.
- **Reserved stems** covering the invented mechanisms this surface invites:
  a destruction/damage/kill/loss count, an honour or resource payout, a mission
  completion, and an occupancy/bounds/terrain test.
- **Injection probes**: inject an invented count helper, an invented payout helper, and
  an invented combat-rule helper that borrows no reserved word; record the **measured**
  failure count of each; restore byte-identically and verify by digest.
- **The GDScript side needs no new guard**, because `test_combat_actions.gd` already
  scans the **whole client tree** (`res://scripts` + `res://tests`) for its thirteen
  needle fragments. That is a constraint on what this line may name, and the task set
  records it as one: a delivered client source that uses any of those fragments fails
  an existing suite, correctly.

The harness must re-assert the recorded defects rather than assume them: LF
normalisation before mutation, an **abort** when a probe reports zero `[test] FAIL`
lines (a parse-error detection proves nothing about a guard — `godot-unit-experience`
recorded that a GDScript slip produced six silent passes), restore verified by
digest with **no universal trailing-newline rule**, and `git diff --numstat
--ignore-cr-at-eol` plus `git status --short` equal to their pre-probe values.

### D10 — Established architecture invariants, restated as invariants and not re-decided

Lines 1–3 established these and this line **obeys** them. They are restated here so
the next line has them in one place, and each is stated as a property the suite can
fail, not as a convention:

1. **The refusal vocabulary is closed, lives in `server_v1_refusals.py` only, and has
   exactly one code→status table.** No route may grow its own answer; v0 accumulated
   24 of them and that is what the table exists to stop.
2. **Derivation lives in exactly one place per domain.** This line derives nothing,
   which is the degenerate case of the rule and the easiest to state mechanically: the
   domain module contains no arithmetic at all.
3. **The transport names no refusal code.** `post_combat` is byte-identical in shape to
   `post_collect` / `post_collection` / `post_magic`: hand the bytes to the intent
   module, call the domain, translate through `_envelope`.
4. **The intent layer imports neither store nor content and performs no arithmetic.**
   It owns addressing and structural refusals only. It legitimately knows the *name*
   `unit_id`, because it owns the row's addressing.
5. **The repository seam preserves unknown fields by construction**, and every read
   and write asserts it. A save carrying keys this repository has never seen round-trips
   unchanged — which is also why whole-document byte-identity (D6) is a meaningful
   instrument rather than a diff over known fields.
6. **Every route carries a post-execution proof whose first half is a specification
   check and only whose second half is falsifiable.** Stated in D6 because this line's
   second half is the strongest in the project.

### D11 — `end_quest` is deliberately excluded, and `kill` / `kill_iid` with it

`map_lose_item` has exactly **two** call sites: `command.py:796` (`end_quest`) and
`command.py:872` (`end_attack`). `godot-quests` already delivered the identical
client-dictated-destruction refusal for `end_quest`, including a recorded **probe**
in which the legacy server destroyed a placed row (40 → 39) while the modern endpoint
derived `units: []` and destroyed none — a divergence recorded in that line's
manifest, not reported as parity.

Re-delivering it here would be two surfaces for one decision. `end_attack` is the
un-delivered half and is the whole of this line.

`kill` and `kill_iid` are excluded with their own measured reasons: `kill` deletes by
map key, holds **no** `push_dead_unit` call, and never touches
`privateState["deadHeroes"]` — a property of *that branch* that bundling it here would
blur; `kill_iid` contains **no write statement at all**, its entire body being one
`print`, so nothing can move and no request can change that.

## Instrument faults in my own measurements

Recorded because a figure that is wrong because of the instrument is worse than no
figure. These are mine, in this session, on top of the selection record's own nine.

1. **I nearly inherited "twelve of the twelve blob fields are used".** The selection
   record's §9.6 records that its "uses after assignment" tally over-counted because
   it counted the pre-initialiser lines `:826-837`, and it resolved the structural
   facts by reading the body instead. I read the body. The result — three read after
   assignment, one reaching stored state — is **not** a figure the selection record
   states, so it is mine and it is a direct read.
2. **My first instinct was to reuse the selection record's `attacker_units = None` line
   number.** It reads `:837` in §6.1. Measured: `victim_units = None` is `:835` and
   `attacker_units = None` is **`:836`**. The dereference is `:866` in both. Recorded
   as a correction below rather than a silent fix.
3. **The `attack` row needed a per-occurrence check, not a count.** `12` whole-file and
   `5` code-only both look like consumers. Checking each of the twelve individually
   shows every one inside `end_attack`, `attacker`, `attacker_units`, or
   `flash_reload_attack`. The census figure that matters is the **whole-word `0`**,
   and reporting `12` without that sentence would have been the trap §4 of the
   selection record already names for this field.
4. **`godot-unit-behaviors`'s "three doors" figure did not survive contact with the
   call-site count.** It counts `push_dead_unit`'s two callers plus `map_lose_item` as
   three; there are **two branches** that reach it, through **one** helper. I did not
   edit that archived line — it is not this change's to rewrite — and the discrepancy
   is recorded here and in this line's suite, which counts **call sites** and names
   the module at each one.

## Contradictions with `docs/legacy-m13-line4-candidates.md`

The selection record is the binding document for **which** target, and this design
accepts its target without re-ranking. Its framing of the shape is sharpened in one
respect and confirmed in the rest. Reported rather than quietly adopted:

| # | Record says | Measured | Which is right |
|---|---|---|---|
| 1 | §8: the two `None` dereferences' "reachability … is **unknown**", and "this record did not execute a probe" | reachability is **established by execution** — fixture steps 2 and 4 answered HTTP 500 — because `tests/fixtures/godot-combat-actions/` was archived on **2026-10-05**, before this record | the measurement; see §Corrections C4 |
| 2 | §6.1: "`attacker_units` is initialised to `None` at `:837`" | `attacker_units = None` is at **`:836`**; `:837` is blank | the measurement; see §Corrections C3 |
| 3 | §5 R4 / §6.1: `map_lose_item` "additionally pushes every destroyed row onto the dead-hero ledger" | true, and with a stronger consequence the record does not state: a **team-3** row is destroyed and credited nothing, because `map_lose_item` accepts any truthy team while `push_dead_unit` requires exactly `1` | the measurement; the record is not wrong, it is thinner |
| 4 | §6.1: "**R3** — the worst client input in the pool, and it is a destruction" | confirmed and unchanged; the record's own framing, which this design adopts | the record |
| 5 | §6.1: the shape "derive the destruction set server-side (or refuse it)" | the record explicitly approves neither, and measurement takes the second option with **no derivation at all** | neither is approved; D2 |
| 6 | §4: "`end_attack` — committed content a derivation would read: **none**" | confirmed by a fresh six-rule census: nine fields at `0` in every view, `attack` at whole-word `0` | the record |

**None of these moves the ranking.** The target stands. What changes is that the line's
shape is fixed as **a refusal with no derivation whatsoever** — not even line 3's
partial derivation of a counter from a recorded bound — and that the record's single
`unknown` understates what the fixture had already established.

## Risks / Trade-offs

- **This line delivers no derivation.** Stated here rather than in a footnote, and
  stated in the proposal's opening. Its value is that it closes the worst client input
  in the pool and demonstrates a boundary category none of the first three covers: a
  transaction that **moves nothing and destroys nothing**, proven by whole-document
  byte-identity.
- **D2's route always succeeds.** A resolve cannot be refused for want of a
  derivation, because it derives none. That could read as a route that accepts
  everything; it is mitigated by the identity binding (D1) and by the fact that half 2
  of the proof is a whole-document identity, so the only thing a successful request
  can do is report.
- **The `< 20` pin's amendment is a real decision.** It is the first time a line has
  needed the ceiling to move, and the amendment is recorded in the changed file with
  its rationale rather than applied silently.
- **Line 3's three assertions on that pin must move with it**, including the one that
  pins the **spelling** of the guard's line. A guard that pins its own text is
  unusual and is recorded here so it is not mistaken for over-specification.
- **Two cross-line guards will go red and must be amended as ownership hand-offs, not
  loosened**: the hermetic/live count pins in `test_auction_schedule.gd` and
  `test_market_trade.gd`, currently **53 hermetic / 26 live**. The pins move to
  **54 / 27**.
- **`test_market_trade.gd`'s two pin *messages* are stale** — they read "fifty-two" and
  "twenty-five" while the constants are 53 and 26 — a value/prose mismatch left by
  line 3. This line fixes them while bumping. `test_auction_schedule.gd`'s messages
  are already generic and need no such fix. Recorded because a pin whose message
  disagrees with its constant is a small lie that survives re-runs.
- **Two delivered client sources will be added**, and `test_combat_actions.gd`'s
  whole-client-tree needle scan therefore runs over **two more files**. That suite's
  count is not a fixed number and rises by design.
- **The gate reporting is not enforcement**, so a team-3 or non-resurrectable unit
  resolves successfully and destroys nothing. That is deliberate (D3) and it is the
  one place a reader could reasonably want a stricter behaviour; the reasoning is that
  a gate in front of no operation decorates rather than authorises.

## Migration Plan

1. Amend `server_v1_refusals.py` with **one** code, its 409 status, its purpose and its
   v0 equivalent (D5), and amend the `< 20` pin and line 3's three assertions **with
   the rationale recorded in the changed files**.
2. Extend `server_v1_intent.py`: one schema row for `combat`, one addressing-field row,
   and **no** operation field — there is one action (D1). No new machinery beyond the
   declaration style already used.
3. Implement `server_v1_combat.py`: committed-identity lookup through the existing
   content registry (**do not transcribe** any committed value), gate resolution from
   content and recorded state, the refusal of the destruction set, and every refusal
   before any write.
4. Register `POST /v1/combat` in `server_v1_app.py` with no arithmetic, no refusal
   vocabulary and no domain value construction.
5. Client: one `ServerV1Api` facade forwarder plus a typed result module, in the exact
   shape lines 1–3 established, and a widened `GameApi` declaration only if the three
   implementations genuinely disagree on the return type.
6. Hermetic suite `res://tests/test_combat_v1.gd`, re-deriving the id-space overlap,
   the gate figures and the corpus figures from the committed documents on each run,
   and generating its report from the live model.
7. Live phase `combat-live-v1` on the v1 port against a disposable corpus, asserting
   the **typed response**, the **whole-document byte-identity**, and — deliberately —
   **no save mutation**, because the transaction destroys nothing and there is nothing
   to mutate. The harness's `--expect-save-mutation` flag is **not** set for this
   phase, and that is the correct answer rather than an omission.

## Corrections to inherited figures

Recorded here rather than edited into the source documents, as the correction
discipline requires. Four items.

### C1 — The refusal-count guard is at `test_boundary_invariant.py:492`, not `:392`

Line 3's `proposal.md` (archived) cites `apps/server-v1/tests/test_boundary_invariant.py:392`
for `assertLess(len(list(RefusalCode)), 20)`. Measured: the assertion is at **line
492**. The archived line is not edited — it belongs to `magic-price-authority` — and
the archived proposal already records the figure's substance correctly; only the line
number is wrong.

### C2 — The count pins are 53 hermetic / 26 live, not 52 / 25

Line 3's `design.md` §Risks records the pins "currently **52 hermetic / 25 live**
after line 2. The pins move to **53 / 26**." The *post*-line-3 values are correct;
the pre-values are the ones it describes as current, and they are the ones a reader
checking this line's starting state would compare against. Measured on this line's
bytes: `test_auction_schedule.gd:165-166` and `test_market_trade.gd:212-213` both hold
`RECORDED_HERMETIC_COUNT := 53` and `RECORDED_LIVE_PHASE_COUNT := 26`, and
`verify-boot.ps1`'s `$hermetic` list holds **53** names. This line moves them to
**54 / 27**.

### C3 — `attacker_units = None` is at `command.py:836`, not `:837`

The selection record §6.1 says `attacker_units` is initialised to `None` at `:837`.
Measured: `:835` is `victim_units = None`, `:836` is `attacker_units = None`, and
`:837` is blank. The dereference at `:866` is correct in the record. The
selection record is **not** edited — it is a delivered investigation owned elsewhere
— and its `victim = None` at `:827` is correct as written.

### C4 — The reachability of both `None` dereferences is **established**, not unknown

The selection record §8 lists as an unknown whether the two dereferences at `:866`
and `:874` are reachable, and says the record "did not execute a probe against it".
Measured against `tests/fixtures/godot-combat-actions/`: **step 2**
(`resolve_absent_attacker_units`) and **step 4** (`resolve_absent_victim`) both
execute the corresponding shape against the real legacy server and both answer HTTP
**500** with the persisted document byte-identical. The fixture was captured and
archived on **2026-10-05**, before this selection record.

The honest split is therefore narrower than the record's: reachability is
**established by execution**; what remains unknown is only **whether a real client
ever sent either shape**, since the Flash client was never executed and every fixture
payload is crafted. The reachability claim does not move the design — D4 closes both
shapes structurally either way — but a spec is the source of truth and an understated
`unknown` in one is as wrong as an overstated one.

## Open Questions

- **Q1.** What are `A` and `B` (`command.py:868`)? The branch's comment names them
  nothing. **Unknown, and unanswerable here.** D2 refuses rather than guesses.
- **Q2.** What did the twelve blob fields mean to the Flash client? **Unknown,
  permanently.** Nine of them are assigned and never read by the server; that is a fact
  about the preserved server, not about the client.
- **Q3.** Did a real client ever omit `attacker_units` or `victim`? **Unknown.** The
  raises are established; the client that would have triggered them is not observable
  from this repository.
- **Q4.** Should the two gates be enforced? Deferred with its condition (D3): a gate
  becomes worth enforcing the day this route has an operation that destroys something.
- **Q5.** Why does `push_dead_unit` require team **exactly 1** while `map_lose_item`
  accepts **any** truthy team? **Unknown.** Recorded and reported, never reconciled.
- **Q6.** Which committed rows would a real combat have destroyed? **Unanswerable
  without a damage rule**, and there is none (§4).
- **Q7.** What did the Flash client display after an attack resolved? **Unknown, and
  permanently so** — this line reads the server and the committed content only.
