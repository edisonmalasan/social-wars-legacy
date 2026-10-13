# Proposal

## Why

M13 lines 1, 2 and 3 each landed on a surface where the legacy server reached its
answer from committed content: `collect` from committed income, `complete_collection`
from a committed prize and a named `cashPrice`, the magic counter from a recorded
bound. Line 4's target is the one the binding selection record
(`docs/legacy-m13-line4-candidates.md`, PR #398) ranked first: `end_attack` at
`POST /v0/combat`, the `resolve` action.

It wins on three of the four criteria that survived criterion 1, and loses on none.
**Criterion 1 is dead for every option**, and that is the whole of this proposal's
character: §4 of the selection record applies "a content-anchored derivation
exists" to all 29 remaining pool branches and **none passes**. Every content-anchored
M13 line is already delivered. So this is a **refusal line**, and it says so up
front rather than at the end: **it derives nothing at all.**

`end_attack` is the strongest available target. That is not the same as a good one,
and the selection record says so in §6.1 in its own words.

### What the branch does

`command.py:808-885`, read line by line:

```python
elif cmd == "end_attack":
    response = None
    unknown = args[1]                       # :810  read, never used
    try:
        response = json.loads(args[0])      # :813  the whole input is a client blob
    except:
        print("Error: Failed to parse command."); return
    if not response:
        print("Error: Failed to parse command."); return   # :818 empty blob = success, no change
    ...
    for unit in attacker_units:                              # :866  attacker_units may be None
        lost = max(0, unit[2] - unit[3])   # number of loses is A - B     :868
        if lost > 0:
            print(f"Lost {lost} {get_name_from_item_id(unit[0])}(s)")
            map_lose_item(map, privateState, unit[0], lost)  # :872  the only mutation
    if "name" in victim:                                      # :874  victim may be None
```

Four facts, each measured against the preserved source rather than taken from the
selection record:

- **The branch's entire stored effect is one call.** `map_lose_item` at `:872` is the
  only state mutation; the count of `map_*`/`add_*`/`pop_*`/`set_*` calls in the body
  is **0**. Everything else in the branch is a local.
- **Both the item id and the number of rows destroyed are client-dictated.**
  `lost = max(0, unit[2] - unit[3])` at `:868` subtracts two numbers whose only
  recorded labels are `A` and `B`, in the branch's own comment at `:867`
  (`# item_id (not on map), sent_to_battle, A, B`). Nothing anywhere establishes
  what they are.
- **Of the twelve fields copied out of the client blob, three are read after
  assignment, and only one of the three reaches stored state.** `attacker_units`
  drives the mutation; `victim` and `win` drive `print` strings and nothing else.
  The remaining nine — `voluntary_end`, `attacker`, `resources`, `honor`, `duration`,
  `townhall_gold`, `different_island`, `victim_units`, `resources_victim` — are
  assigned and never read. This count is a direct read of the span, **not** the
  selection record's "uses after assignment" tally, which §9.6 of that record already
  recorded as over-counting because it included the pre-initialiser lines.
- **One client request writes two pieces of authoritative state.** `map_lose_item`
  (`engine.py:215-228`) calls `push_dead_unit` at `:223`, which mutates
  `privateState["deadHeroes"]`. The placed row and the dead-hero ledger are both
  written by one request.

### The number cannot be derived, and the measurement is a census

There is no committed value that names this branch's outcome. Re-measured over
`command.py`, `engine.py`, `server.py`, `sessions.py`, `constants.py`, `version.py`,
`get_game_config.py` under six counting rules — whole-file occurrences, whole-file
distinct lines, code-only occurrences (comments and string literals stripped by a
two-state lexer), code-only distinct lines, whole-word, and the quoted `"field"` form:

| committed field | whole-file | whole-file lines | code-only | code-only lines | whole-word | quoted |
|---|---|---|---|---|---|---|
| `attack` | **12** | 10 | **5** | 5 | **0** | **0** |
| `defense`, `life`, `attack_interval`, `attack_range`, `best_against`, `best_against_mult`, `velocity` | **0** | 0 | **0** | 0 | **0** | **0** |
| `resurrectable` | 5 | 5 | 3 | 3 | 5 | 2 |

`attack`'s twelve whole-file occurrences are **all** inside longer identifiers —
`end_attack`, `attacker`, `attacker_units`, `flash_reload_attack` — so its whole-word
count is **0**. It is a substring artefact in every view that reports it as present.
`resurrectable` is the one row with real consumers, and those consumers belong to
`godot-unit-behaviors`.

**Therefore there is nothing to derive a destruction count from, and the count is
refused.** Not "derive it more carefully": refused, because the only arithmetic the
branch performs is a subtraction of two client numbers.

### What v0 already does with the same branch, and why v1 does not repeat it

`apps/compat-api/combat_envelope.py` already ships the identical refusal at v0. Its
`CLIENT_DICTATED_REFUSAL` refuses the `max(0, unit[2] - unit[3])` shape, derives a
destruction set, and reports `destruction: 1`. That `1` is **an artefact of the
envelope's own construction**, not a rule: executing `combat_payload('resolve')`
returns `{"attacker_units":[[0,0,1,0]],"victim":{"name":"derived"}}`, where the
trailing `0` is `_DERIVED_IDENTITY` set by `project_combat`. A client that sent
`A=3, B=1` would make the same envelope destroy two rows, and the committed fixture
records exactly that — step **7** of `tests/fixtures/godot-combat-actions/`, where
the legacy oracle destroyed **two** rows while the delivered v0 endpoint destroyed
exactly **one**. The fixture's own manifest records that transaction as a
**divergence**, not as parity.

v1 therefore does not carry the count forward in either available form:

- **"Destroy exactly one"** is inherited from a payload this repository constructed,
  not from the branch. Promoting it into a v1 rule would convert a test fixture's
  convenience into server authority.
- **"Destroy every eligible row"** re-runs `map_lose_item`'s `while qty > 0` loop
  with a count the server has no way to produce. That is the client-dictated
  destruction with a different spelling.

### What is established, and what stays unknown

| Claim | Status |
|---|---|
| The branch's span, its one mutation, its two unguarded `None` dereferences | **established** (preserved source, read directly) |
| `lost = max(0, unit[2] - unit[3])` on two client numbers labelled only `A` and `B` | **established** (`command.py:867-868`) |
| Both raises — absent `attacker_units`, absent `victim` — are reachable | **established by execution**: fixture steps **2** and **4** answer HTTP **500** with the save byte-identical |
| A raise anywhere discards the whole save | **established**: `command.py:30,32` dispatches the batch before saving |
| An empty blob answers success with no change | **established**: fixture step **3**, `command.py:818` |
| The twelve blob fields, and that nine are assigned and never read | **established** (direct read of the span) |
| The committed combat fields name this branch's outcome | **refuted as derivable** — the census above |
| **Whether a real client ever sent either malformed shape** | **unknown.** The Flash client was never executed; every fixture payload is crafted |
| **What the 12 fields meant to the Flash client** | **unknown, permanently** |
| Whether `A` and `B` are counts, casualties, or anything else | **unknown, and unanswerable here** |

The distinction between the last three rows and the first six is load-bearing, and it
is sharper than the selection record states it: **the reachability of both raises is
established, because the fixture executed them.** What is unknown is only whether a
real client sent either shape. §8 of the selection record calls the reachability
unknown too; §Corrections below records the correction.

## What Changes

- **`POST /v1/combat`** added to `apps/server-v1/`: one route, one action, one
  request `{player_id, unit_id}`. The identity is bound to the committed **unit** id
  space. The action vocabulary is v1's own, **not** `command.py`'s branch name, for
  the reason line 2 recorded: v1's vocabulary must not become a subset of the 63
  branch names.
- **No derivation and no destruction.** A resolve resolves the identity, reports the
  two committed ledger gates, reports the client-dictated count it **will not apply**,
  and destroys nothing. The count is not narrowed and the branch is not reproduced.
- **The two committed `push_dead_unit` gates are resolved and reported, never acted
  on**: the committed `resurrectable` flag, and the row's recorded player team. An
  absent committed flag is reported **absent**, never as zero — that is the recorded
  behaviour of `engine.py:159-162`, and reading it as zero would be a fabrication.
- **Exactly one new refusal code**, `client_dictated_destruction` (409), taking the
  closed table from **19** to **20**. This **requires amending**
  `apps/server-v1/tests/test_boundary_invariant.py:492`, which asserts
  `len(RefusalCode) < 20` and would fail at exactly 20. See `design.md` D5 — the pin
  exists to force this argument into the open, and this line is the argument.
- **`end_quest` is deliberately excluded.** `map_lose_item` has exactly **two** call
  sites — `command.py:796` (`end_quest`) and `command.py:872` (`end_attack`) — and
  `godot-quests` already delivered the identical refusal for `end_quest`, including a
  recorded divergence where the legacy server destroyed a placed row (40 → 39) and
  the modern endpoint destroyed none.
- **Branch and route arithmetic moves by exactly one.** `end_attack` becomes the
  fifth authoritative v1 branch over four routes, so the branches-without-an-
  authoritative-route figure moves **59 → 58** and the non-authoritative v0 routes
  move **21 → 20**. The routed/unrouted split of **39**/**24** is **unchanged** and
  `docs/legacy-m13-unrouted-branches.md` is not edited.

## Non-goals

- **No derivation.** The whole of this line. Stated in the proposal's own opening,
  not in a footnote.
- **No parity claim against the legacy server.** The oracle is
  `tests/fixtures/godot-combat-actions/`, read as committed bytes; it is **not**
  re-captured, and no live legacy server is started.
- **No change to `apps/compat-api/**`.** It is the parity oracle, not the thing being
  replaced. Line 1's D1 (coexistence) holds unchanged, and `/v0/combat` keeps its
  `resolve` action and its recorded divergence.
- **No `kill` and no `kill_iid`.** `kill` (`command.py:169-181`) deletes by **map
  key** and holds no `push_dead_unit` call at all, so the ledger's non-participation
  is a property of that branch and not of this one; `kill_iid` (`command.py:183-187`)
  has no write statement in its body, its entire content being one `print`.
- **No mission dispatch, resolution, completion, or reward.** Mission vocabulary stays
  owned by `godot-mission-vocabulary`.
- **No damage, health, defence, hit chance, honour, or resource movement.** Nine
  committed fields measure zero consumers under every view; none becomes a rule.
- **No occupancy, bounds, type, or terrain validation.** `map_lose_item` tests only the
  item id and the team's truthiness (`engine.py:221`) and this line records that
  absence rather than filling it.
- **No SQL, PostgreSQL, or Alembic migration.** Line 1's D4 defers them.
- **No claim about what the Flash client sent, displayed, or expected.** Every rule
  here is derived from committed content or the preserved branch.
- **No windowed capture and no pixel-parity claim**, because nothing is rendered.
- **No ordinal claimed for any zero-consumer field**, and **no ordinal claimed for the
  recorded flaky surfaces** — the surrounding sections of this repository already
  disagree on that count over different scopes.

## Impact

- Affected specs: `server-v1-combat-authority` (new), `server-v1-authority-boundary`
  (extended — the boundary gains a fourth worked transaction, of a category neither
  the first three covers: one that **moves nothing and destroys nothing**, proven by
  whole-document byte-identity rather than by a resource comparison).
- Affected code: `apps/server-v1/` only, plus the client-side `ServerV1Api` facade the
  boundary already registered, plus one hermetic suite and one v1 live phase.
- Two count pins move, as ownership hand-offs rather than loosenings: **53 → 54**
  hermetic and **26 → 27** live phases.
- One cross-line guard is amended for a recorded reason: the `< 20` refusal-count pin.
- The Compatibility API suite stays at its recorded baseline as a **verified** figure,
  because this change adds no v0 route and touches no `apps/compat-api/**` file.
