extends RefCounted
## Typed, read-only projection of the combat-action surface (OpenSpec
## `godot-combat-actions`: "The combat request's field inventory is projected
## from the legacy branch and every discarded key is named" / "The destruction
## set is server-derived and the client count is refused" / "Every validation
## resolves before any row is removed" / "The item-keyed kill is a proven
## no-op" / "Combat-action evidence and claim limits", design D1-D8).
##
## ## What this module is, and what it deliberately is NOT
##
## This is the **third** kind of M8/M9/M10 line.  `unit_movement.gd`,
## `unit_animations.gd` and `production_flow.gd` were refusals;
## `unit_behaviors.gd` delivered a mechanism against a real committed field.
## This line delivers a **server-derived destruction**: the request carries the
## **identity** of the unit that was lost and nothing else, and the service
## derives which placed rows that identity can destroy, which one it takes, and
## how many it destroys — **exactly one**, always.
##
## ## The legacy count is REFUSED, never reproduced (design D1/D2)
##
## `end_attack` (`command.py:808-885`) derives its destruction count as
## `max(0, unit[2] - unit[3])` (`command.py:868`) on two numbers the CLIENT
## supplies, and the committed source labels them only `A` and `B` with the
## comment "number of loses is A - B". Nothing establishes what they mean.
## Reproducing that subtraction would make this server a pass-through for a
## client-computed casualty figure, which is the `AGENTS.md` "Bad" pattern and
## the identical anti-pattern the `godot-quests` line refused in `end_quest`.
##
## So `refused_client_keys()` refuses three families of key **before dispatch**,
## and the refusal is a **named, separate** guard from the eligibility check:
## eligibility is a question about the player's recorded rows, while this one is
## a question about the request's own keys. A client that sent a count must be
## able to tell "you may not say how many" apart from "there was nothing to
## find". `select_eligible_rows()` therefore answers only the second question,
## and never reports a count of the client's making.
##
## ## Why ONE destruction and not "however many match" (design D1)
##
## `map_lose_item` loops `while qty > 0` and returns the moment a pass finds no
## match (`engine.py:218-227`), so its apparent safety against over-deletion is
## **exhaustion of matches, not a check**. Mistaking one for the other is how an
## untrusted count survives review, so no loop count is derived and no clamp is
## applied: one is the largest destruction the service can justify without
## inventing a combat rule. Exhaustion is equally a **silent under-deletion**, and
## that is measured rather than argued: an identity with no matching row left the
## loop's first pass unmatched and destroyed nothing, yet the branch still printed
## `Lost 1` — see `PRINTED_COUNT_IS_A_REQUEST`.
##
## ## Both ledger gates, and no third (design D1, D7)
##
## The gates are **delegated unchanged** to `unit_behaviors.gd`, which already
## names exactly the two conditions `engine.push_dead_unit`
## (`engine.py:149-170`) evaluates and re-measures them every run. This module
## writes neither gate, neither counter, nor the delete-at-zero rule a second
## time, so a surface, the hermetic suite, the deterministic report, and the
## compatibility service cannot drift apart about what the ledger is.
##
## The **team asymmetry** between the two helpers is recorded, never exercised
## and never refused (design D7): `map_lose_item` accepts any **truthy** recorded
## team while `push_dead_unit` records only team one, so a non-team-one unit row
## would be destroyed and never enter the ledger. All 441 committed unit rows are
## team one, so the case is unreachable from the committed corpus, and refusing
## it would invent a bound the oracle does not have.
##
## ## Two kill contracts, delivered differently (design D5)
##
## `kill` (`command.py:169-181`) looks a row up **by map key**, deletes it, and
## **never** touches the ledger — structurally, because the branch holds no
## reference to `privateState['deadHeroes']` and no call to `push_dead_unit` at
## all. `kill_iid` (`command.py:183-187`) **writes nothing**: its body binds two
## locals from `args` and every assignment target is a bare `Name`, so it is
## delivered as a **proven no-op** rather than refused, because an empty branch is
## a behaviour the preserved server has and a client can be verified against.
##
## ## The field inventory is RE-DERIVED, never transcribed (design D4)
##
## `derive_field_inventory()` reads `command.py` **as bytes** on every call and
## classifies every key the branch reads. Nothing in this module holds a
## transcribed key list, and no key name appears in any constant: the read keys
## are the branch's own `if "<key>" in response:` tests, the mutation region is
## the branch's only row-removal loop **located by searching for the call**, and
## the `discarded` set is every key with no occurrence after the membership block
## ends, quote-stripped so neither a comment nor the assignment that transports
## the value out of the blob can count as a use. `print_only` is derived as the
## complement and the three-way partition is asserted, so a key fitting none of
## them fails here instead of being quietly filed under one.
##
## `source_text` is injectable on purpose: it is what makes this guard testable
## by injection rather than only by hope.
##
## ## No combat is resolved and nothing is paid
##
## `attack`, `defense`, `life`, `attack_interval`, `attack_range`,
## `best_against`, `best_against_mult` and `velocity` each measure **zero**
## legacy consumers, so the committed numbers are CONTENT and never rules. This
## module computes no damage, no outcome, no defence, no hit chance, no life or
## interval arithmetic, no honour, and no reward; it dispatches no mission; and
## it derives no duration from any committed field. The absence is structural
## rather than promised: `ABSENT_HELPERS` names the derivations this line must
## not grow, the module's **whole** static-function inventory is pinned in
## `STATIC_FUNCTIONS`, and `ARITHMETIC_RECORD` pins the operator census so "no
## derivation" is a measured fact.
##
## ## Purity
##
## This module holds no node, no clock, no request and no transport, and writes
## nothing. It reads the committed `command.py` bytes for the one derivation that
## must not be transcribed, preloads the read-only `unit_behaviors.gd` ledger
## projection and the shared `boot_data.gd` type module, and reads committed
## content only through a caller-supplied callable — never resolving an item
## definition itself.

const Paths = preload("res://scripts/package_paths.gd")
const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ---------------------------------------------------------------------------
# The commands and the closed action vocabulary (design D1/D5)
# ---------------------------------------------------------------------------

## The legacy source the field inventory is re-derived from, repository-relative.
const LEGACY_SOURCE_RELATIVE := "command.py"

## The single dispatcher branch whose client blob this line reads.
const COMBAT_BRANCH := "end_attack"

const END_ATTACK_COMMAND := "end_attack"
const KILL_COMMAND := "kill"
const KILL_IID_COMMAND := "kill_iid"

## The **closed** action vocabulary this line dispatches. One action names one
## legacy branch and nothing else is accepted — a `bytes` value is refused
## because it cannot come from a request body, and accepting it would widen the
## vocabulary to a second spelling of the same name.
const ACTIONS := ["resolve", "kill", "kill_iid"]
const ACTION_RESOLVE := "resolve"
const ACTION_KILL := "kill"
const ACTION_KILL_IID := "kill_iid"

## Which legacy branch each action dispatches, and the ONE value a client may
## name for it. The addressing is the branch's own subject; everything else is
## derived server-side.
const ACTION_COMMAND := {
	ACTION_RESOLVE: END_ATTACK_COMMAND,
	ACTION_KILL: KILL_COMMAND,
	ACTION_KILL_IID: KILL_IID_COMMAND,
}

## The **per-action** wire key the service reads the addressing under. This is
## deliberately per-action and never a single fixed key: a body is therefore
## always exactly three keys, and no fourth value is even expressible.
const ACTION_ADDRESSING_KEY := {
	ACTION_RESOLVE: "item_id",
	ACTION_KILL: "map_key",
	ACTION_KILL_IID: "item_id",
}

const ACTION_ADDRESSING := {
	ACTION_RESOLVE: "the committed item id of the unit that was lost",
	ACTION_KILL: "the map key of the placed row to remove",
	ACTION_KILL_IID: "the committed item id the legacy branch only prints",
}

## The three delivered branches as the report records them.
const BRANCHES := [
	{
		"action": ACTION_RESOLVE,
		"command": END_ATTACK_COMMAND,
		"kind": "dispatcher-branch",
		"source": "command.py:808-885",
		"addressing_key": "item_id",
		"destroys_rows": true,
		"reaches_ledger": true,
		"through": "map_lose_item (engine helper, engine.py:215-228) -> "
			+ "push_dead_unit (engine helper, engine.py:149-170)",
		"note": "the sole mutation path in the whole branch; the client payload's "
			+ "destruction count is refused rather than reproduced",
	},
	{
		"action": ACTION_KILL,
		"command": KILL_COMMAND,
		"kind": "dispatcher-branch",
		"source": "command.py:169-181",
		"addressing_key": "map_key",
		"destroys_rows": true,
		"reaches_ledger": false,
		"through": null,
		"note": "deletes the addressed row and NEVER touches privateState"
			+ "['deadHeroes']; the branch holds no push_dead_unit call, so the "
			+ "ledger's non-participation is a property of the branch rather than "
			+ "an observation of one request",
	},
	{
		"action": ACTION_KILL_IID,
		"command": KILL_IID_COMMAND,
		"kind": "dispatcher-branch",
		"source": "command.py:183-187",
		"addressing_key": "item_id",
		"destroys_rows": false,
		"reaches_ledger": false,
		"through": null,
		"note": "WRITES NOTHING: the branch binds two locals from args, every "
			+ "assignment target is a bare Name, and its only call is one print, "
			+ "so it is delivered as a proven no-op rather than refused",
	},
]

## The loopback endpoint path the live implementation dials. Named here as the
## **contract**, NOT as transport: `legacy_v0_api.gd` is the only file allowed to
## reference an endpoint, which the project-scope suite enforces, so this is the
## documented path without a scheme or a host.
const COMBAT_PATH := "/v0/combat"

# ---------------------------------------------------------------------------
# The committed row shape and the stored resources
# ---------------------------------------------------------------------------

## The committed map row shape (`engine.map_add_item`, `engine.py:8-31`):
## `[item, x, y, timestamp, orientation, store, attr, player]`.
const MAP_ROW_SLOTS := 8
const SLOT_ITEM_ID := 0
const SLOT_CELL_X := 1
const SLOT_CELL_Y := 2
const SLOT_ATTR := 6
const SLOT_PLAYER := 7

## The seven stored resource slots the post-execution proof compares — **all of
## them, never a subset**, which is what makes the no-honour / no-reward /
## no-syringe-cost claim non-tautological rather than a statement about
## resources nobody looked at. These are exactly the seven fields of
## `BootData.Resources`.
const RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]
const RESOURCE_COUNT := 7

## The ledger's own save location, delegated in full to `unit_behaviors.gd`.
const PRIVATE_STATE_KEY := "privateState"
const LEDGER_KEY := "deadHeroes"

## The three fates a read key can have, as a **closed** vocabulary. Every key the
## branch reads is reported with exactly one of them, and
## `derive_field_inventory()` asserts the three sets partition the inventory, so
## a key fitting none of them fails the derivation instead of being quietly filed
## under one.
const FATES := ["discarded", "print_only", "mutation_path"]
const FATE_DISCARDED := "discarded"
const FATE_PRINT := "print_only"
const FATE_MUTATION := "mutation_path"

# ---------------------------------------------------------------------------
# The fail-closed reasons (design D2/D3/D7)
# ---------------------------------------------------------------------------

const REASON_UNKNOWN_ACTION := "unknown_action"
const REASON_INVALID_ACTION := "invalid_action"
const REASON_MISSING_ITEM_ID := "missing_item_id"
const REASON_INVALID_ITEM_ID := "invalid_item_id"
const REASON_MISSING_MAP_KEY := "missing_map_key"
const REASON_INVALID_MAP_KEY := "invalid_map_key"
const REASON_CLIENT_DICTATED_DESTRUCTION := "client_dictated_destruction"
const REASON_NO_ELIGIBLE_ROW := "no_eligible_row"
const REASON_UNADDRESSABLE_ROW := "unaddressable_row"
const REASON_INVALID_LEDGER := "invalid_ledger"
const REASON_INVALID_VECTOR := "invalid_vector"
const REASON_INVALID_TIMESTAMP := "invalid_timestamp"
const REASON_INVALID_PAYLOAD := "invalid_payload"

# ---------------------------------------------------------------------------
# The refused client keys (design D2)
# ---------------------------------------------------------------------------

## Client keys carrying a destruction count, and the two subtraction operands
## the legacy count is computed from.
##
## These are **this line's own refusal vocabulary**, not a transcription: the
## legacy source names no such key, and `lost`, `losses`, `destroyed`, `qty`,
## `count` and their siblings are spellings a modern client might reach for. The
## third family — any key the branch itself reads — is **not** listed here; it is
## built from `derive_field_inventory()`, so it tracks a legacy edit instead of
## drifting from it.
const DESTRUCTION_COUNT_KEYS := [
	"lost", "losses", "destroyed", "destroyed_count", "units_lost", "quantity",
	"qty", "count",
]
const SENT_SURVIVED_KEYS := ["sent", "survived"]

const CLIENT_DICTATED_REFUSAL := ("A CLIENT-DICTATED DESTRUCTION COUNT IS "
	+ "REFUSED, NEVER REPRODUCED. The legacy branch derives its destruction count "
	+ "as max(0, unit[2] - unit[3]) (command.py:868) on two numbers the CLIENT "
	+ "supplies, and the committed source labels them only 'A' and 'B' with the "
	+ "comment 'number of loses is A - B' -- nothing establishes what they mean. "
	+ "This operation therefore destroys exactly ONE row, derived from its own "
	+ "recorded state. Reproducing the subtraction would make this server a "
	+ "pass-through for a client-computed casualty figure, which is the "
	+ "AGENTS.md Bad pattern and the identical anti-pattern the godot-quests line "
	+ "refused in end_quest. The difference is recorded as a DIVERGENCE, never as "
	+ "parity")

const REFUSED_COUNT_NOTE := ("The legacy branch's apparent safety against "
	+ "over-deletion is EXHAUSTION OF MATCHES, NOT A CHECK: map_lose_item loops "
	+ "`while qty > 0` and returns the moment one pass finds no match "
	+ "(engine.py:218-227). Mistaking exhaustion for a bound is how an untrusted "
	+ "count survives review, so no loop count is derived here and no clamp is "
	+ "applied")

## The printed count is a **request**, never an outcome. Found by execution, not
## by reading the branch: the unconditional `print("Lost", lost)` at
## `command.py:871` executes **before** the `map_lose_item` call at `:872` and is
## not guarded by its result, so a committed item id with **zero** placed rows —
## nothing destroyed at all — still printed `Lost 1`.
##
## This is recorded because the branch's own log is the strongest-looking piece
## of evidence *against* this line's refusal, and a future reader would otherwise
## cite it as proof the count describes what happened.
const PRINTED_COUNT_IS_A_REQUEST := ("THE BRANCH'S PRINTED COUNT REPORTS WHAT THE "
	+ "CLIENT ASKED FOR, NOT WHAT IT DESTROYED. The print at command.py:871 "
	+ "precedes the row-removal call at :872 and is not conditional on it, so "
	+ "`Lost N` is printed from the client-supplied subtraction whether or not a "
	+ "single row matched. MEASURED: item id 923 -- a committed unit id with zero "
	+ "placed rows -- printed `Lost 1` and destroyed nothing. Reading that log as "
	+ "an outcome count would reinstate the untrusted subtraction, which is why "
	+ "the count is refused and the one server-derived destruction is proved "
	+ "against the persisted state instead")

# ---------------------------------------------------------------------------
# The ordering guarantee (design D3)
# ---------------------------------------------------------------------------

## Every step resolves **before** dispatch except the two that are the write and
## its proof. `DESTRUCTION_STEP` is the write, and it is the only step that
## mutates anything.
const VALIDATION_ORDER := [
	{"step": 1, "check": "action_is_in_the_closed_vocabulary",
		"resolves": "before dispatch"},
	{"step": 2, "check": "no_client_dictated_destruction_key",
		"resolves": "before dispatch", "code": REASON_CLIENT_DICTATED_DESTRUCTION},
	{"step": 3, "check": "addressing_present_and_well_typed",
		"resolves": "before dispatch"},
	{"step": 4, "check": "eligible_row_resolves",
		"resolves": "before dispatch", "code": REASON_NO_ELIGIBLE_ROW},
	{"step": 5, "check": "addressed_row_resolves",
		"resolves": "before dispatch", "code": REASON_UNADDRESSABLE_ROW},
	{"step": 6, "check": "ledger_readable",
		"resolves": "before dispatch", "code": REASON_INVALID_LEDGER},
	{"step": 7, "check": "destruction_set_derived",
		"resolves": "before dispatch"},
	{"step": 8, "check": "derivation_ready_to_execute",
		"resolves": "before dispatch"},
	{"step": 9, "check": "destruction", "resolves": "THE WRITE STEP"},
	{"step": 10, "check": "post_execution_proof", "resolves": "after dispatch"},
]
const VALIDATION_ORDER_STEPS := 10
## The compared fields of one validation step, in the order they are checked.
const VALIDATION_ORDER_FIELDS := ["step", "check", "resolves"]
## Each field's committed GDScript type. `step` is a count and the other two are
## statements, so the comparison cannot be one untyped `!=`: GDScript refuses a
## String-versus-int comparison outright, which would turn a *refusal* into an
## engine error. The type is asserted first and the value second, so a corrupted
## field of the wrong type is refused rather than crashing the parser. The count is
## compared as an INTEGER and the statements as STRINGS: the JSON transport widens
## every number to a float on the pinned engine, so a count arrives as 1.0 and
## requiring TYPE_INT of it would refuse a correct response.
## field of the wrong type is refused rather than crashing the parser.
const VALIDATION_ORDER_FIELD_TYPES := {
	"step": TYPE_INT, "check": TYPE_STRING, "resolves": TYPE_STRING,
}
const DESTRUCTION_STEP := 9

const ORDERING_RULE := ("EVERY VALIDATION COMPLETES BEFORE ANY ROW IS REMOVED "
	+ "(design D3). The legacy branch's two unguarded absent-value dereferences "
	+ "sit on OPPOSITE SIDES of its write loop: omitting attacker_units raises at "
	+ "command.py:866 before the loop body runs, while omitting victim raises at "
	+ "command.py:874 after map_lose_item already ran. Both answer HTTP 500 -- and "
	+ "the PERSISTED save is byte-identical in both cases, because command.py "
	+ "dispatches the whole batch first and calls save_session only afterwards "
	+ "(command.py:30,32), so an exception anywhere in the batch discards every "
	+ "mutation it made. MEASURED, including a two-command batch whose first "
	+ "command was valid: the branch printed its destruction and the persisted "
	+ "state did not move. The failure mode is therefore a DISCARDED save rather "
	+ "than a partially applied one, and the persistence boundary is the BATCH, "
	+ "not the command. Reproducing that ordering inside this endpoint is still "
	+ "refused: every check resolves before dispatch so a refusal can never leave "
	+ "a half-applied state, whatever a future persistence change does")

## The ORDER the derived destruction takes, as the answer reports it.
##
## It is the save's own recorded map-key order -- the order `for index in
## map_items` walks -- because that is the order `map_lose_item` pops, and it is
## **not** the numeric order of the keys.  Both differ in the committed corpus:
## the recorded oracle chose `2425` where the smallest key was `897` and where the
## key-sorted snapshot order chose `1022`, so this string is the claim that the
## right one was chosen rather than a description of "the first match".
const ORDERING_RECORD := ("the save's own recorded map-key (insertion) order, "
	+ "which is the order `for index in map_items` walks and therefore the order "
	+ "map_lose_item pops; NOT numeric key order and NOT the key-sorted order of "
	+ "a captured snapshot, and the committed corpus distinguishes all three")

## The four post-execution proof halves, as the client records them.
const PROOF_HALVES := [
	{
		"half": "placement_set_and_every_other_row",
		"checks": "the placement key set differs by exactly the derived key and "
			+ "EVERY other row is byte-identical",
		"why": "a count comparison would pass while the wrong row was removed, so "
			+ "this half is a value comparison against the whole map rather than "
			+ "about the removal",
	},
	{
		"half": "ledger_key_order_and_every_entry_by_value",
		"checks": "entries keep their recorded insertion order, a created key is "
			+ "appended (engine.py:164-167), and the derived entry matches by value",
		"why": "comparing against the shared display projection's SORTED keys "
			+ "would reject every ledger whose recorded order is not already sorted",
	},
	{
		"half": "every_stored_resource_unchanged",
		"checks": "all seven stored resources are compared, never a subset",
		"why": "legacy applies the request's own vector BEFORE the branch "
			+ "(command.py:40), so this half is what forecloses a delta smuggled "
			+ "through the request",
	},
	{
		"half": "row_count_stated_as_a_count_last",
		"checks": "the row count is checked against the derived destruction LAST",
		"why": "every other half is a value comparison, so this one can never be "
			+ "the only thing that passed",
	},
]

# ---------------------------------------------------------------------------
# The team asymmetry (design D7)
# ---------------------------------------------------------------------------

const TEAM_ASYMMETRY := {
	"status": "RECORDED, NOT EXERCISED, NOT REFUSED",
	"row_removal_helper": {
		"helper": "map_lose_item",
		"source": "engine.py:215-228",
		"accepts": "ANY TRUTHY recorded team (`map_items[index][7]`, "
			+ "engine.py:221)",
		"is_dispatcher_branch": false,
	},
	"ledger_helper": {
		"helper": "push_dead_unit",
		"source": "engine.py:149-170",
		"accepts": "PLAYER TEAM 1 ONLY (`if item[7] != 1: return False`, "
			+ "engine.py:151)",
		"is_dispatcher_branch": false,
	},
	"consequence": "a non-team-one unit row would be DESTROYED and would never "
		+ "ENTER THE LEDGER",
	"committed_unit_rows": 441,
	"committed_unit_rows_on_team_one": 441,
	"exercised": false,
	"exercised_note": "unreachable from the committed corpus: every one of the 441 "
		+ "committed unit rows across the committed save documents is on player "
		+ "team one, which is the value push_dead_unit requires",
	"refused": false,
	"refused_note": "refusing it would invent a bound the oracle does not have, "
		+ "which is the same reasoning that leaves the M6 tile-geometry gap "
		+ "recorded rather than closed",
}

# ---------------------------------------------------------------------------
# The two kill contracts (design D5)
# ---------------------------------------------------------------------------

const KILL_CONTRACT := {
	"command": KILL_COMMAND,
	"source": "command.py:169-181",
	"deletes_addressed_row": true,
	"reaches_ledger": false,
	"ledger_references": 0,
	"missing_row_behaviour": "map_get_item's falsy branch prints 'Error: item "
		+ "not found.' and RETURNS, and the server still answers the legacy "
		+ "success result, so a client cannot distinguish this outcome from a "
		+ "real deletion by the response alone. This endpoint REFUSES it instead, "
		+ "which is a recorded divergence and not parity",
	"note": "the ledger's non-participation is asserted as a property of the "
		+ "branch, not inferred from one request that happened not to change it: "
		+ "the branch contains no reference to privateState['deadHeroes'] and no "
		+ "call to push_dead_unit at all",
}

const KILL_IID_CONTRACT := {
	"command": KILL_IID_COMMAND,
	"source": "command.py:183-187",
	"local_bindings": ["item_id", "reason_str"],
	"statement_writes_save_state": false,
	"body": "print(\"Killed\", str(get_name_from_item_id(item_id)))",
	"mutates": [],
	"resources_move": false,
	"delivered": "as a proven no-op",
	"not_delivered": "as a refusal",
	"why": "the branch WRITES NOTHING -- every assignment target in its body is "
		+ "a bare Name and its only call is one print -- which is a stronger "
		+ "statement than any single observed request showing nothing changed. "
		+ "Refusing a command that does nothing would misrepresent the preserved "
		+ "server as having a rule to violate. Its INTENT is unknown: nothing "
		+ "observes whether a real client sent it, or what it was meant to do",
	"reaches_ledger": false,
}

# ---------------------------------------------------------------------------
# The recorded divergence and the refusals
# ---------------------------------------------------------------------------

const DIVERGENCE := {
	"status": "DIVERGENCE, NOT PARITY",
	"legacy_status": "the legacy server can destroy an ARBITRARY number of rows "
		+ "from one request",
	"modern_status": "this operation destroys AT MOST ONE, derived server-side",
	"reason": CLIENT_DICTATED_REFUSAL,
	"recorded_not_narrowed": "The divergence is recorded rather than narrowed, "
		+ "because narrowing it would require a combat rule the preserved source "
		+ "does not contain. The executed legacy capture measures the real "
		+ "difference against a committed village document and the fixture records "
		+ "it as a divergence field, so it cannot be reported as parity by "
		+ "omission",
	"unobserved_request_shape": "Whether the real Flash client ever sent a "
		+ "MULTI-UNIT loss in one payload is never observed: the client was never "
		+ "executed. If it did, this operation under-delivers against it, and that "
		+ "is recorded as a claim limit rather than resolved",
}

const NO_COMBAT := ("NO COMBAT IS RESOLVED OF ANY KIND. attack, defense, life, "
	+ "attack_interval, attack_range, best_against, best_against_mult, and "
	+ "velocity each measure ZERO legacy consumers across the seven legacy root "
	+ "modules, so the committed numbers are CONTENT and never rules. This "
	+ "contract computes no damage, no attack outcome, no defence application, no "
	+ "hit chance, and no life or interval arithmetic. No mission is dispatched, "
	+ "resolved, or completed either: the mission vocabulary remains owned by the "
	+ "godot-mission-vocabulary capability and nothing here references a mission "
	+ "field")

const NO_COST_OR_REWARD := ("NO HONOUR, REWARD, OR RESOURCE MOVEMENT OF ANY KIND. "
	+ "The committed blob keys are `honor` (US spelling, command.py:846-847), "
	+ "`resources`, `resources_victim`, and `townhall_gold`; each is read from the "
	+ "client blob and DISCARDED, the committed honor schedule has zero legacy "
	+ "consumers, and the branch writes no resource field at all. The derived "
	+ "resource vector is therefore the neutral all-zero one and the endpoint's "
	+ "post-execution proof requires EVERY stored resource to be unchanged, which "
	+ "is what forecloses a vector smuggled through the request")

const NO_SYRINGE_COST := UnitBehaviors.NO_SYRINGE_COST

const NO_PLACEMENT_VALIDATION := ("NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN "
	+ "VALIDATION IS ADDED. map_lose_item tests only the item id and the team's "
	+ "truthiness (engine.py:221) and inventory selection adds no check of its "
	+ "own, so this contract reproduces that absence rather than filling it. "
	+ "Inventing a check here would make this client STRICTER than the legacy "
	+ "server. The gap is recorded as a Server v1 / M13 requirement, exactly as "
	+ "godot-building-move, godot-building-collect, and "
	+ "godot-stored-item-placement already do")

## Every refusal, as one machine-readable list. `implemented` is the flag that
## separates two opposite obligations, which is why the split exists: a **true**
## entry is a guard this line actively enforces, while a **false** entry is a rule
## it deliberately declines to add. Reading a false entry as an omission is the
## mistake this field prevents.
const REFUSALS := [
	{
		"refusal": "client_dictated_destruction",
		"implemented": true,
		"rule": CLIENT_DICTATED_REFUSAL,
		"note": REFUSED_COUNT_NOTE,
	},
	{"refusal": "combat_resolution", "implemented": false, "rule": NO_COMBAT},
	{"refusal": "no_cost_or_reward", "implemented": false,
		"rule": NO_COST_OR_REWARD},
	{"refusal": "syringe_cost", "implemented": false,
		"rule": NO_SYRINGE_COST},
	{"refusal": "placement_validation", "implemented": false,
		"rule": NO_PLACEMENT_VALIDATION},
]
const REFUSAL_COUNT := 5

## Both recorded-versus-measured corrections, carried beside the measured
## figures rather than silently replacing them.
const FIELD_INVENTORY_CORRECTION := {
	"recorded_read_key_count": 11,
	"measured_read_key_count": 12,
	"recorded_discarded_count": 7,
	"recorded_discarded_count_in_the_own_table": 8,
	"measured_discarded_count": 9,
	"key_absent_from_the_recorded_table": "voluntary_end",
	"omitted_in_both": "voluntary_end (command.py:839-840)",
	"note": "The committed investigation docs/legacy-m10-combat.md and the "
		+ "combat-actions spec deltas both state eleven read keys and seven "
		+ "discarded; the investigation's own table then lists eight discarded "
		+ "rows, and the proposal names eight keys while saying seven. Measured "
		+ "from the branch there are TWELVE read keys and NINE that reach "
		+ "nothing: voluntary_end (command.py:839-840) is absent from both the "
		+ "prose and the table. The conclusion is unchanged -- the keys the record "
		+ "names do reach nothing, which is the finding this capability was "
		+ "chartered to record. Only the counts are corrected, and every count "
		+ "here is re-derived on every verification run",
	"fates": "discarded = zero post-block references, quote-stripped; "
		+ "mutation_path = a reference inside the row-removal loop region located "
		+ "by SEARCHING for the map_lose_item( call; print_only = the complement. "
		+ "The three-way partition is asserted, so a key fitting none of them "
		+ "fails the derivation",
}

const CORPUS_CORRECTION := {
	"measured_unit_rows": 441,
	"measured_unit_rows_on_team_one": 441,
	"measured_unit_rows_resurrectable": 429,
	"measured_placed_rows": 3372,
	"measured_documents": 10,
	"measured_documents_with_unit_rows": 7,
	"measured_documents_with_non_empty_ledger": 4,
	"recorded_documents": 11,
	"recorded_documents_with_non_empty_ledger": 5,
	"recorded_neutral_ledger_keys": 29,
	"measured_neutral_ledger_keys": 28,
	"does_not_reproduce": [
		"'11 documents' measures 10: 8 under villages/ and 2 under tests/saves/. "
			+ "tests/saves/manifest.json is a manifest, not a save, and the "
			+ "villages/quest/ directory holds 23 quest documents of a different "
			+ "shape. The committed investigation's own table lists exactly ten "
			+ "rows",
		"'five village saves carry a non-empty deadHeroes ledger' measures FOUR, "
			+ "and the committed record's own enumeration names exactly four",
		"Neutral.json's ledger holds 28 keys, not the recorded 29. This change's "
			+ "design D8 and proposal already state 28, so the investigation's "
			+ "table row is the outlier",
	],
	"note": "Every per-document row figure and the placed-row total reproduce "
		+ "exactly; only the three derived prose figures above do not",
}

# ---------------------------------------------------------------------------
# The structural guards (design D4)
# ---------------------------------------------------------------------------

## The delivered module's **whole static-function inventory**, pinned.
##
## This is the structural half of the no-invention guard. The suite reads this
## file, extracts its `static func` declarations, and requires this list to match
## exactly in BOTH directions — nothing missing and nothing extra. Adding a
## resolution, damage, duration, honour, reward, or mission-completion helper
## therefore fails the suite rather than quietly contradicting the line's central
## finding.
const STATIC_FUNCTIONS := [
	"_validation_order_field_agrees",
	"combat_failure",
	"legacy_source_path",
	"_read_source_bytes",
	"_strip_string_literals",
	"_indent_of",
	"_branch_span",
	"_row_removal_region",
	"derive_field_inventory",
	"is_action",
	"is_item_id",
	"is_map_key",
	"_addressing_is_well_typed",
	"_addressing_reason",
	"wire_key",
	"actions",
	"branches",
	"validation_order",
	"refusals",
	"corrections",
	"team_asymmetry",
	"select_eligible_rows",
	"address_row",
	"project_ledger",
	"committed_resurrectable",
	"expected_ledger_increment",
	"refused_client_keys",
	"project_combat",
	"build_intent",
	"build_response",
	"intent_record",
	"scope_record",
	"readout_text",
	"parse_combat",
	"_whole_number",
	"_type_name",
	"_optional_int",
	"_combat_error",
]

## Helpers this capability deliberately does **not** define, and the reason each
## is absent. Recorded as a named list so the absence is an assertion the suite
## can check and the report can publish, not merely a sentence in a docstring.
const ABSENT_HELPERS := [
	{"helper": "resolve_damage", "absent_because": "none of the committed combat "
		+ "fields has a legacy consumer, so there is no committed damage rule to "
		+ "resolve"},
	{"helper": "damage_for", "absent_because": "the same absence as "
		+ "resolve_damage, stated as the noun a caller would reach for"},
	{"helper": "apply_attack", "absent_because": "`attack` and `attack_interval` "
		+ "are content with zero consumers, so there is no outcome to apply"},
	{"helper": "defend", "absent_because": "`defense` is a constant 1 on all 429 "
		+ "committed units and is read by no branch"},
	{"helper": "hit_chance", "absent_because": "no committed field records a "
		+ "probability and no branch draws a random number"},
	{"helper": "resolve_duratio", "absent_because": "no combat-adjacent duration "
		+ "has a legacy consumer; `max(0, unit[2] - unit[3])` is a subtraction of "
		+ "two unnamed client numbers, not a duration"},
	{"helper": "duration_for", "absent_because": "the same absence as "
		+ "resolve_duratio"},
	{"helper": "honor_for", "absent_because": "the committed blob key `honor` is "
		+ "read and DISCARDED (command.py:846-847) and the committed honor schedule "
		+ "has zero legacy consumers"},
	{"helper": "reward_for", "absent_because": "no committed field records a "
		+ "combat reward and the branch writes no resource field at all"},
	{"helper": "complete_mission", "absent_because": "mission vocabulary remains "
		+ "owned by godot-mission-vocabulary, which measured zero consumers; this "
		+ "line references no MISSION_ field"},
	{"helper": "lost_count", "absent_because": "the only count this operation "
		+ "derives is the constant one, so a helper named for a lost count is "
		+ "exactly where an untrusted subtraction would reappear"},
	{"helper": "resolve_type", "absent_because": "the action vocabulary is a "
		+ "closed constant of three names, so no classification is needed"},
	{"helper": "is_occupied", "absent_because": "map_lose_item tests only the item "
		+ "id and the team's truthiness (engine.py:221), so a stricter client would "
		+ "be a parity break in the opposite direction"},
	{"helper": "in_bounds", "absent_because": "the same absence as is_occupied, "
		+ "for the cell bounds the row-removal helper never checks"},
	{"helper": "terrain_at", "absent_because": "the same absence as is_occupied, "
		+ "for the terrain the row-removal helper never reads"},
]

## The arithmetic claim, recorded so the suite can prove it mechanically rather
## than by reading (design D4).
##
## The module contains **no** multiplication, division, modulo, power, shift, or
## bitwise operator in its code at all, so nothing here can compute a damage
## figure, a duration, a ratio, a probability, or an honour/reward amount.
##
## Its `+` and `-` occurrences are **MEASURED** rather than asserted. Two views
## are distinguished and the distinction is the point: a binary `+` between two
## string literals is a **concatenation** and never an addition, a leading `+` on
## a continuation line is the same thing, a `-` with nothing but whitespace and an
## operand to its left is **unary**, and the `-` of a `->` return-type annotation
## is neither. Over the **31** lines that survive that test, the suite extracts
## every identifier and compares the resulting set to `ADDITIVE_OPERANDS` in BOTH
## directions.
##
## That comparison replaces an earlier, weaker rule which required every additive
## line to name one of twelve bookkeeping tokens. It was **falsified by
## measurement**: 20 of the 31 lines name none of the twelve, because the module's
## additions are overwhelmingly over **strings, arrays, and path fragments** rather
## than over line indices. The twelve-token list is retained below as
## `SUPERSEDED_ADDITIVE_TOKENS` and is not used as a gate.
##
## The replacement is strictly stronger, because a published operand inventory is
## an **equality** rather than a lower bound: a new sum over a committed value
## introduces an identifier, and the set comparison fails. The measured set
## contains **zero** of the committed combat field names, which is asserted
## separately and does not depend on the inventory at all.
##
## Every ledger arithmetic operation — the increment, the create-at-one, the
## delete-at-zero — is **delegated** to `unit_behaviors.gd`, which already owns
## it and re-measures it every run. This module writes no counter a second time.
const ARITHMETIC_RECORD := {
	"multiply_operators": 0,
	"divide_operators": 0,
	"modulo_operators": 0,
	"power_operators": 0,
	"shift_operators": 0,
	"bitwise_operators": 0,
	"additive_operand_rule": "every identifier on a line carrying a binary + "
		+ "or - must be in ADDITIVE_OPERANDS, and every published operand must be "
		+ "measured; the comparison runs in BOTH directions, so a new sum over a "
		+ "committed value introduces an identifier and fails it",
	"additive_operands": ADDITIVE_OPERANDS,
	"binary_additive_lines": 31,
	"superseded_additive_token_rule": "the earlier rule required every additive "
		+ "line to name one of twelve bookkeeping tokens. It was falsified by "
		+ "measurement: 20 of the 31 binary additive lines name none of them, "
		+ "because the module's additions are over strings, arrays, and path "
		+ "fragments rather than over line indices. The list is retained as "
		+ "SUPERSEDED_ADDITIVE_TOKENS and gates nothing",
	"committed_combat_field_hits_on_additive_lines": 0,
	"note": "nothing here computes a damage figure, a duration, a ratio, a "
		+ "probability, an honour amount, a reward, or a mission completion from "
		+ "any committed value. The ONE destruction is a constant, not a sum",
}

## The falsified twelve-token rule, kept verbatim so the correction is auditable
## against the claim it replaces. Nothing reads it as a gate.
const SUPERSEDED_ADDITIVE_TOKENS := [
	"index", "span", "region", "block_end", "call_line", "for_start", "for_end",
	"declared", "site", "declared_at", "step", "count",
]

## Every identifier measured on a line carrying a **binary** `+` or `-`, sorted.
##
## The suite re-extracts this set from `command.py`-independent measurement of the
## module's own bytes and requires **set equality in both directions**: an
## identifier here that the measurement does not find is a stale publication, and
## an identifier the measurement finds that is absent here is new arithmetic.
## That is what makes the no-derivation claim mechanical rather than a reading.
const ADDITIVE_OPERANDS := [
	"ACTIONS", "BootData", "COMBAT_BRANCH", "GATE_COUNT",
	"LEGACY_SOURCE_RELATIVE", "PROTOCOL", "REFUSAL_COUNT", "UnitBehaviors",
	"_type_name", "action", "addressing_body", "append", "block_end", "body",
	"call_line", "compile", "declared", "field", "for_start", "gate", "get",
	"header", "index", "int", "item_id", "items", "join", "key", "labels",
	"lines", "name", "out", "parsed", "range", "region", "site", "size", "span",
	"start", "str", "wire_key", "word",
]

## The evidence's non-claims.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script" + ", or browser "
		+ "executed, and no network was used in the hermetic suite",
	"NO CLIENT-DICTATED DESTRUCTION COUNT IS REPRODUCED IN EITHER DIRECTION: the "
		+ "legacy server subtracts two client numbers; this operation destroys "
		+ "exactly one server-derived row and the difference is a DIVERGENCE, "
		+ "never parity",
	"THE LEGACY BRANCH'S PRINTED LOSS COUNT IS NOT TREATED AS AN OUTCOME COUNT. "
		+ "It is printed before the row-removal call it appears to describe and is "
		+ "not conditional on it, so an identity with zero matching rows still "
		+ "printed it. It is evidence of what a client requested and of nothing "
		+ "else",
	"NO DAMAGE, HEALTH, DEFENCE, HIT CHANCE, OR LIFE ARITHMETIC IS DELIVERED OR "
		+ "CLAIMED. attack, defense, life, attack_interval, attack_range, "
		+ "best_against, best_against_mult, and velocity each measure zero legacy "
		+ "consumers, so the committed numbers are content and never rules",
	"NO MISSION IS DISPATCHED, RESOLVED, OR COMPLETED, and the mission vocabulary "
		+ "remains owned by godot-mission-vocabulary. No MISSION_ field is "
		+ "referenced anywhere in this line's delivered code",
	"NO HONOUR OR REWARD IS PAID AND NO STORED RESOURCE MOVES: the committed blob "
		+ "keys `honor` (US spelling), `resources`, resources_victim, and "
		+ "townhall_gold are read and discarded; the derived vector is neutral and "
		+ "the proof requires every stored resource unchanged",
	"NO SYRINGE COST IS CHARGED, because the committed syringes field has zero "
		+ "legacy consumers",
	"NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED. That absence is "
		+ "reproduced, not filled, and is recorded as a Server v1 / M13 gap",
	"THE TEAM ASYMMETRY between map_lose_item's truthy-team acceptance and "
		+ "push_dead_unit's team-one requirement is RECORDED AS A CODE FACT AND NOT "
		+ "EXERCISED, because no committed unit row is on a team other than one. It "
		+ "is not refused, which would invent a bound the oracle does not have",
	"THE ITEM-KEYED KILL IS DELIVERED AS A PROVEN NO-OP, not as a refusal, and no "
		+ "replacement meaning is invented for it. Its intent is unknown",
	"PARITY COVERS THE RECORDED TRANSACTIONS AGAINST THE COMMITTED VILLAGE "
		+ "DOCUMENTS ONLY, and no progressed-player save exists for this line "
		+ "beyond those two committed documents",
	"NO WINDOWED CAPTURE AND NO PIXEL-PARITY ORACLE ARE CLAIMED, because nothing "
		+ "is rendered by this line",
]

## The number of recorded non-claims, declared beside the list rather than
## transcribed in a test, so no check can quote a figure the module does not
## deliver.
const NON_CLAIM_COUNT := 12

const PROVENANCE := {
	"capability": "godot-combat-actions",
	"milestone": "M10 line 2",
	"legacy_source": LEGACY_SOURCE_RELATIVE,
	"combat_branch": "end_attack (command.py:808-885)",
	"kill_branch": "kill (command.py:169-181)",
	"kill_iid_branch": "kill_iid (command.py:183-187)",
	"row_removal_helper": "map_lose_item (engine.py:215-228)",
	"ledger_helper": "push_dead_unit (engine.py:149-170)",
	"ledger_owner": "godot-unit-behaviors (unit_behaviors.gd), delegated whole",
	"mission_vocabulary_owner": "godot-mission-vocabulary",
	"interpretation": "Every field inventory, fate, corpus figure, and ordering "
		+ "step is RE-DERIVED from the committed legacy source on every "
		+ "verification run. Nothing is transcribed, so a legacy edit fails the "
		+ "guard instead of silently contradicting the record",
}

# ---------------------------------------------------------------------------
# The typed result
# ---------------------------------------------------------------------------

## The typed result of a combat intent: the legacy result plus the
## authoritative superset — the server-derived destruction, the derived set it was
## chosen from, the ledger on both sides, both gate records, the four proof
## halves, and the seven stored resources — or a structured failure with **no
## partial payload**.
##
## It is declared HERE rather than in `boot_data.gd` for the same reason
## `ResurrectResult` is: every other GameApi result class lives in that file and
## this line does not own it, and an untyped dictionary would break the
## "identical typed shapes by construction" property every other intent has. Both
## GameApi implementations return **this** type.
class CombatResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped. A time-dependent field, so
	## tests assert positivity and never a fixed value.
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The action that was dispatched, and the legacy command it dispatched.
	var action := ""
	var command := ""
	## The wire key the addressing travelled under, and the addressing value
	## exactly as sent.
	var addressing_key := ""
	var addressing_value := -1
	var addressing_kind := ""
	var addressing_note := ""
	## The server-derived destruction. `count` is ALWAYS 0 or 1 and is never a
	## number a client could have chosen; `derived` is asserted true by the
	## parser, so a response claiming a client-chosen count is refused outright.
	var destruction_count := 0
	var destruction_derived := false
	## The derived map key the row was removed from, `""` when nothing was
	## destroyed (the proven no-op).
	var derived_key := ""
	## The destroyed row's own eight committed slots.
	var derived_row: Array = []
	## Every row the identity could have destroyed, in the save's own recorded
	## map-key order, and how many that is.
	var eligible_keys: Array = []
	var eligible_count := 0
	var destruction_order := ""
	var printed_count_is_request := ""
	var rows_before := 0
	var rows_after := 0
	## The ledger as read BEFORE execution and re-read AFTER it, each entry
	## `{item_id, count}`.
	var ledger_before: Array = []
	var ledger_after: Array = []
	var ledger_written := false
	## Both gate records as the service evaluated them, keyed by gate name.
	var ledger_gates: Dictionary = {}
	## The two committed gates the legacy helper evaluates, and "no third".
	var gates: Array = []
	var no_third_gate := ""
	## The recorded team asymmetry, carried on every answer so a caller cannot
	## read the gates as the whole rule.
	var team_asymmetry: Dictionary = {}
	## The two kill contracts, present only for their own action.
	var kill_contract: Dictionary = {}
	var kill_iid_contract: Dictionary = {}
	## The ordering rule and the validation order the service reported, which the
	## parser requires to agree with this module's own `VALIDATION_ORDER`.
	var ordering_rule := ""
	var validation_order: Array = []
	## The service's re-derived field inventory, its two recorded corrections,
	## the recorded divergence, the five recorded refusals, the four no-*
	## statements, and the non-claims.
	var field_inventory: Dictionary = {}
	var correction: Dictionary = {}
	var divergence: Dictionary = {}
	var refusals: Array = []
	var no_combat := ""
	var no_cost_or_reward := ""
	var no_syringe_cost := ""
	var no_placement_validation := ""
	var non_claims: Array = []
	var provenance: Dictionary = {}
	## The four post-execution proof halves, and the pointers that actually moved.
	var proof_halves: Array = []
	var changed: Array = []
	var resources: BootData.Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for a combat intent — never a partial payload.
## Whether one reported validation-order field matches, compared **by its
## committed type first**. A `Variant` holding a String is refused rather than
## compared against an int, which is what keeps a corrupted response a typed
## failure instead of an engine `SCRIPT ERROR`.
static func _validation_order_field_agrees(actual: Variant, expected: Variant,
		expected_type: int) -> bool:
	if typeof(expected) != expected_type:
		return false
	if expected_type == TYPE_STRING:
		# A STATEMENT is compared as a String and never coerced, so a numeric
		# field can never satisfy a statement field.
		return typeof(actual) == TYPE_STRING \
			and (actual as String) == (expected as String)
	# A COUNT is compared as an integer. `_parse_int` accepts an int and an
	# integral float and returns null for everything else, so a non-integral
	# float, a string, a boolean, and null all still refuse.
	var actual_count: Variant = BootData._parse_int(actual)
	return actual_count != null and int(actual_count) == int(expected)


static func combat_failure(code: String, message: String) -> CombatResult:
	var result := CombatResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


# ---------------------------------------------------------------------------
# The field inventory derivation (design D4)
# ---------------------------------------------------------------------------


## Absolute path of the legacy source the inventory is re-derived from.
static func legacy_source_path() -> String:
	return Paths.repo_root().path_join(LEGACY_SOURCE_RELATIVE)


## Read the legacy source's bytes, as bytes.
static func _read_source_bytes() -> Dictionary:
	var handle := FileAccess.open(legacy_source_path(), FileAccess.READ)
	if handle == null:
		return {"ok": false,
			"error": "cannot read " + LEGACY_SOURCE_RELATIVE + ": "
				+ legacy_source_path()}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return {"ok": true, "text": bytes.get_string_from_utf8()}


## Replace every string literal with empty quotes.
##
## Two states, so an apostrophe inside a double-quoted string cannot end the scan
## early — a one-pass regular expression desynchronised on exactly that in the
## compatibility service and made three downstream scans vacuously true, which
## was found by measurement rather than by reading the code.
static func _strip_string_literals(line: String) -> String:
	var out := ""
	var quote := ""
	for index in range(line.length()):
		var character := line[index]
		if quote != "":
			if character == "\\":
				continue
			if character == quote:
				quote = ""
				out += "\"\""
			continue
		if character == "\"" or character == "'":
			quote = character
			continue
		out += character
	return out


## The half-open line span of one `cmd == "<name>"` dispatcher branch.
##
## The dispatch form is what delimits the branch, so it is matched as a syntax
## form rather than by naming any key. An absent branch is a **named failure**,
## not a silently empty inventory.
## A line's own indentation width — the count of leading space characters.
##
## Used only to delimit the row-removal loop's body, and named as its own helper
## because GDScript has no `lstrip_edges()`: an earlier version of this file
## called it and failed to parse, which is why the rule the loop region depends
## on is one place rather than two.
static func _indent_of(line: String) -> int:
	var indentation := 0
	while indentation < line.length() and line[indentation] == " ":
		indentation += 1
	return indentation


## The half-open line span of one `cmd == "<name>"` dispatcher branch.
static func _branch_span(lines: PackedStringArray, name: String) -> Dictionary:
	var pattern := RegEx.new()
	pattern.compile("^\\s*(?:el)?if\\s+cmd\\s*==\\s*\"([A-Za-z_]+)\"\\s*:\\s*$")
	var start := -1
	for index in range(lines.size()):
		var found := pattern.search(lines[index])
		if found == null or found.get_string(1) != name:
			continue
		start = index
		break
	if start < 0:
		return {"ok": false,
			"error": "the legacy source declares no " + name + " dispatcher branch"}
	var end := lines.size()
	for index in range(start + 1, lines.size()):
		if pattern.search(lines[index]) != null:
			end = index
			break
	return {"ok": true, "start": start, "end": end}


## The line span of the branch's only row-removal loop, or an empty dictionary.
##
## Located by searching for the row-removal **call**, never by naming a key, so
## the mutation region is discovered rather than transcribed and a legacy edit
## that moved the loop still fails the guard.
static func _row_removal_region(lines: PackedStringArray, span: Dictionary) -> Dictionary:
	var call_line := -1
	for index in range(int(span["start"]), int(span["end"])):
		if _strip_string_literals(lines[index]).find("map_lose_item(") != -1:
			call_line = index
			break
	if call_line < 0:
		return {}
	var loop := RegEx.new()
	loop.compile("^\\s*for\\s+\\w+\\s+in\\s+\\w+:")
	var for_start := -1
	for index in range(call_line, int(span["start"]) - 1, -1):
		if loop.search(lines[index]) != null:
			for_start = index
			break
	if for_start < 0:
		return {}
	var indent := _indent_of(lines[for_start])
	var for_end := int(span["end"])
	for index in range(for_start + 1, int(span["end"])):
		var stripped := lines[index].strip_edges()
		if stripped == "":
			continue
		if _indent_of(lines[index]) <= indent:
			for_end = index
			break
	return {"start": for_start, "end": for_end}


## Re-derive the combat request's field inventory from `command.py` bytes.
##
## Returns `{ok, reason, error, source, branch, branch_span, keys, key_count,
## key_names, discarded, print_only, mutation_path, fates, partition,
## row_removal_region, correction}`.
##
## **Nothing here is transcribed.** The keys are the branch's own
## `if "<key>" in response:` tests, read as bytes; the mutation region is the
## branch's only row-removal loop, found by searching for the call; and
## `discarded` is every key with no occurrence after the membership-test block
## has ended, quote-stripped so neither a comment nor the assignment that
## transports the value out of the blob can count as a use. `print_only` is
## derived as the complement and the three-way partition is asserted, so a key
## that fits none of them fails here instead of being quietly filed under one.
##
## `source_text` is injectable: with it supplied the function reads **no** file
## and a caller may hand it any text at all, which is what makes this drift guard
## testable by injection rather than only by hope. An omitted `source_text`
## (`""`) reads the committed `command.py` bytes.
static func derive_field_inventory(source_text := "") -> Dictionary:
	var header := {
		"ok": false,
		"reason": "",
		"error": "",
		"source": LEGACY_SOURCE_RELATIVE,
		"branch": COMBAT_BRANCH,
		"branch_span": [],
		"keys": [],
		"key_count": 0,
		"key_names": [],
		"discarded": [],
		"print_only": [],
		"mutation_path": [],
		"fates": FATES.duplicate(),
		"partition": false,
		"row_removal_region": [],
		"correction": (FIELD_INVENTORY_CORRECTION as Dictionary).duplicate(true),
	}
	var text := source_text
	if text == "":
		var read := _read_source_bytes()
		if not bool(read.get("ok", false)):
			header["reason"] = REASON_INVALID_PAYLOAD
			header["error"] = str(read.get("error", "unreadable legacy source"))
			return header
		text = str(read.get("text", ""))

	var lines := PackedStringArray(text.split("\n"))
	var span := _branch_span(lines, COMBAT_BRANCH)
	if not bool(span.get("ok", false)):
		header["reason"] = REASON_INVALID_PAYLOAD
		header["error"] = str(span.get("error", "no such branch"))
		return header
	header["branch_span"] = [int(span["start"]) + 1, int(span["end"])]

	# The read keys, in committed file order, each with the line its own
	# membership test declares it on, and the end of the block that transports
	# them. Both are collected in ONE pass, so the recorded declaration line can
	# never disagree with the key list it accompanies.
	var membership := RegEx.new()
	membership.compile("^\\s*if\\s+\"([A-Za-z_]+)\"\\s+in\\s+response:\\s*$")
	var key_names: Array = []
	var declared := {}
	var block_end := int(span["start"])
	for index in range(int(span["start"]), int(span["end"])):
		var found := membership.search(lines[index])
		if found == null:
			continue
		var key := found.get_string(1)
		if not key_names.has(key):
			key_names.append(key)
			declared[key] = index + 1
		block_end = index + 1

	# The membership block is NOT finished at its last membership test: each test
	# is followed by the line that transports the value out of the blob, and that
	# transport is not a use either. Measured, not assumed: stopping at the last
	# test files `resources_victim` as print-only on the strength of its OWN
	# assignment line and undercounts the discarded set by one.
	#
	# The discriminator is a subscript of `response` -- quote-stripped, so it is
	# the transport FORM rather than any particular key name. Scanning forward
	# while it holds stops at the first line that does not transport from the
	# blob, which is the blank or comment line before the branch's first real use.
	while block_end < int(span["end"]) \
			and _strip_string_literals(lines[block_end]).find("response[") != -1:
		block_end += 1

	if key_names.is_empty():
		header["reason"] = REASON_INVALID_PAYLOAD
		header["error"] = "the " + COMBAT_BRANCH + " branch reads no client keys"
		return header

	var region := _row_removal_region(lines, span)
	header["row_removal_region"] = []
	if not region.is_empty():
		header["row_removal_region"] = [
			int(region["start"]) + 1, int(region["end"])]

	var discarded: Array = []
	var printing: Array = []
	var mutation: Array = []
	var records: Array = []
	for key: String in key_names:
		var word := RegEx.new()
		word.compile("\\b" + key + "\\b")
		var sites: Array = []
		var in_region := false
		for index in range(block_end, int(span["end"])):
			if word.search(_strip_string_literals(lines[index])) == null:
				continue
			sites.append(index)
			if not region.is_empty() and int(region["start"]) <= index \
					and index < int(region["end"]):
				in_region = true
		var fate := ""
		if sites.is_empty():
			fate = FATE_DISCARDED
			discarded.append(key)
		elif in_region:
			fate = FATE_MUTATION
			mutation.append(key)
		else:
			# Derived as the complement of the two derived sets. The partition
			# asserted below is what keeps this honest.
			fate = FATE_PRINT
			printing.append(key)
		var labels: Array = []
		for site: int in sites:
			labels.append("command.py:%d" % (site + 1))
		records.append({
			"key": key,
			"fate": fate,
			# The line this key's own membership test is declared on, and the
			# lines its name occurs on afterwards. The two are reported
			# separately and never conflated: a declaration is not a use, which is
			# precisely how a discarded key would look if they were merged.
			"tested_at": "command.py:%d" % int(declared[key]),
			"post_test_sites": labels,
			"post_test_site_count": sites.size(),
			"post_test_distinct_lines": sites.size(),
			"inside_row_removal_region": in_region,
		})

	var partition := true
	for key: String in key_names:
		if not discarded.has(key) and not printing.has(key) and not mutation.has(key):
			partition = false
	header["ok"] = true
	header["keys"] = records
	header["key_count"] = key_names.size()
	header["key_names"] = key_names
	header["discarded"] = discarded
	header["print_only"] = printing
	header["mutation_path"] = mutation
	header["partition"] = partition
	return header


## The three fates, as a closed vocabulary.
# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------


## Whether a value names an action this line dispatches. A `bytes` value is
## refused because it cannot come from a request body, and accepting it would
## widen the vocabulary to a second spelling of the same name.
static func is_action(value: Variant) -> bool:
	return value is String and ACTIONS.has(str(value))


## Whether a value is a strict integer item id.
##
## A `bool` is never an integer id here, and a float is refused outright, because
## the legacy `row[0] == item` comparison never matched either.
static func is_item_id(value: Variant) -> bool:
	return _whole_number(value)


## Whether a value is a strict integer map key, under the same rule.
static func is_map_key(value: Variant) -> bool:
	return _whole_number(value)


## Whether an action's addressing is well typed — a `map_key` for `kill`, an
## `item_id` for the other two.  Spelled as one function so the step-3 check and
## `build_intent` cannot drift: an intent this line would build and an intent it
## would accept are the same question asked once.
static func _addressing_is_well_typed(action: String, value: Variant) -> bool:
	if action == ACTION_KILL:
		return is_map_key(value)
	return is_item_id(value)


## The named refusal an ill-typed addressing produces for an action.  Split from
## the test for the same reason, so the refusal a caller surfaces is the one the
## endpoint reports.
static func _addressing_reason(action: String) -> String:
	if action == ACTION_KILL:
		return REASON_INVALID_MAP_KEY
	return REASON_INVALID_ITEM_ID


## The **per-action** wire key the service reads the addressing under.
##
## Split out as a named accessor because a body must be exactly three keys, and
## a hand-written key in a transport is exactly how a fourth key gets shipped by
## accident. The suite requires the transport to call this rather than to name a
## key literal.
static func wire_key(action: Variant) -> String:
	if not is_action(action):
		return ""
	return str((ACTION_ADDRESSING_KEY as Dictionary)[str(action)])


## The closed action vocabulary, in committed order.
static func actions() -> Array:
	return ACTIONS.duplicate()


## The three delivered branches as fresh records a caller may mutate.
static func branches() -> Array:
	return (BRANCHES as Array).duplicate(true)


## The validation ordering as fresh records.
static func validation_order() -> Array:
	return (VALIDATION_ORDER as Array).duplicate(true)


## The five recorded refusals as fresh records.
static func refusals() -> Array:
	return (REFUSALS as Array).duplicate(true)


## Both recorded-versus-measured corrections as fresh records.
static func corrections() -> Dictionary:
	return {
		"field_inventory": (FIELD_INVENTORY_CORRECTION as Dictionary)
			.duplicate(true),
		"corpus": (CORPUS_CORRECTION as Dictionary).duplicate(true),
	}


## The recorded team asymmetry as a fresh record.
static func team_asymmetry() -> Dictionary:
	return (TEAM_ASYMMETRY as Dictionary).duplicate(true)


# ---------------------------------------------------------------------------
# The derived destruction set (design D1)
# ---------------------------------------------------------------------------


## The rows `map_lose_item` would consider, **in the order it would pop them**.
##
## Returns `{ok, reason, error, item_id, eligible_keys, eligible_count,
## addressed, addressed_key, addressed_row, truthy_team_only}`.
##
## Eligibility is exactly the two conditions `map_lose_item` tests
## (`engine.py:221`): the row's recorded slot 0 equals the item id **and** the
## row's recorded slot 7 is **truthy**. The addressed row is the **first**
## eligible row in the save's own recorded map-key order — the insertion order
## `for index in map_items` walks and therefore the order it pops.
##
## **The eligible keys are NOT sorted, and nothing here reorders them.** A
## numeric or lexicographic sort would pick a different row than the oracle pops
## whenever several rows share an identity, which is the ordinary case in the
## committed village corpus. This was proven by injection against the
## compatibility service, which produced six independent failures, so it is
## recorded here as a rule and checked by the suite rather than left to review.
##
## A row that is not an eight-slot row is never eligible, so a malformed row can
## neither be destroyed nor counted as a candidate.
static func select_eligible_rows(items: Variant, item_id: Variant) -> Dictionary:
	var out := {
		"ok": false,
		"reason": "",
		"error": "",
		"item_id": item_id,
		"eligible_keys": [],
		"eligible_count": 0,
		"addressed": false,
		"addressed_key": null,
		"addressed_row": null,
		"truthy_team_only": true,
	}
	if not is_item_id(item_id):
		out["reason"] = REASON_INVALID_ITEM_ID
		out["error"] = "item_id must be an integer"
		return out
	if not (items is Dictionary):
		out["reason"] = REASON_INVALID_PAYLOAD
		out["error"] = "the player's placements are " + _type_name(items) \
			+ ", not an object"
		return out
	var placements: Dictionary = items
	var matches: Array = []
	# A GDScript Dictionary iterates in its own insertion order, which is the
	# order the JSON parser recorded the save's keys in -- the same order
	# `for index in map_items` walks. Nothing here sorts it.
	for key: Variant in placements:
		var row: Variant = placements[key]
		if not (row is Array) or (row as Array).size() != MAP_ROW_SLOTS:
			continue
		var slots: Array = row
		var slot_item: Variant = BootData._parse_int(slots[SLOT_ITEM_ID])
		if slot_item == null or int(slot_item) != int(item_id):
			continue
		if not bool(slots[SLOT_PLAYER]):
			continue
		matches.append(str(key))
	out["eligible_keys"] = matches
	out["eligible_count"] = matches.size()
	if matches.is_empty():
		out["reason"] = REASON_NO_ELIGIBLE_ROW
		out["error"] = ("no placed row records item id " + str(int(item_id))
			+ " on a truthy team: map_lose_item matches a row only when its slot 0 "
			+ "equals the item id AND its slot 7 is truthy (engine.py:221), so "
			+ "there is nothing this identity can destroy")
		return out
	var addressed := str(matches[0])
	out["ok"] = true
	out["addressed"] = true
	out["addressed_key"] = addressed
	out["addressed_row"] = (placements[addressed] as Array).duplicate()
	return out


## Resolve an addressed map key to its placed row, or refuse it.
##
## Returns `{ok, reason, error, map_key, row, addressed}`.
##
## `kill` looks the row up with `map_get_item`, whose falsy branch prints and
## returns while the server still answers success (`command.py:173-176`). This
## refuses it instead, which is a recorded divergence and not parity.
static func address_row(items: Variant, map_key: Variant) -> Dictionary:
	var out := {
		"ok": false,
		"reason": "",
		"error": "",
		"map_key": map_key,
		"row": null,
		"addressed": false,
	}
	if not is_map_key(map_key):
		out["reason"] = REASON_INVALID_MAP_KEY
		out["error"] = "map_key must be an integer"
		return out
	if not (items is Dictionary):
		out["reason"] = REASON_INVALID_PAYLOAD
		out["error"] = "the player's placements are " + _type_name(items) \
			+ ", not an object"
		return out
	var placements: Dictionary = items
	var key := str(int(map_key))
	var row: Variant = placements.get(key)
	if row == null:
		out["reason"] = REASON_UNADDRESSABLE_ROW
		out["error"] = ("no placed row stands at map key " + key + ": the legacy "
			+ "kill branch prints 'Error: item not found.' and returns without any "
			+ "change while the server still answers success "
			+ "(command.py:173-176), which this endpoint refuses instead of "
			+ "reproducing")
		return out
	out["ok"] = true
	out["row"] = (row as Array).duplicate()
	out["addressed"] = true
	return out


## The **read-only** projection of `privateState['deadHeroes']`, verbatim.
##
## Delegated unchanged to `unit_behaviors.gd` rather than reimplemented, so the
## ledger's projection exists in exactly one place across the delivered code and
## this line's proof cannot drift from `godot-unit-behaviors`'s.
static func project_ledger(raw: Variant) -> Dictionary:
	return UnitBehaviors.project_ledger(raw)


## One committed definition's `properties.resurrectable`, or `null`.
##
## Delegated unchanged to `unit_behaviors.gd`, which documents the R2 coercion
## boundary: the legacy helper reads the RAW configuration **string** through
## `json.loads` (`engine.py:154-162`) while the committed normalized package
## stores `properties` as an **object**, and a committed flag is a *string*, so
## an explicit conversion is the only correct read. `null` means ABSENT, which
## the helper treats as a refusal rather than a zero.
static func committed_resurrectable(properties: Variant) -> Variant:
	return UnitBehaviors.committed_resurrectable(properties)


## The ledger `push_dead_unit` leaves behind, or proof it wrote nothing.
##
## Reproduces `engine.push_dead_unit` (`engine.py:149-170`) exactly, and every
## counter arithmetic in it is **delegated** to `UnitBehaviors.expected_increment`
## so the increment, the create-at-one and the delete-at-zero rule exist in one
## place only:
##
##   * the row must be on **player team 1** (`engine.py:151`) — any other team is
##     destroyed by `map_lose_item` yet never enters the ledger (design D7);
##   * the committed `properties` must carry `resurrectable` **at all**
##     (`engine.py:159`), so an **absent** flag is a refusal and never a zero;
##   * and it must be **greater than zero** (`engine.py:162`);
##   * when both gates hold the count **increments by one**, creating the key at
##     `1` when it is absent (`engine.py:164-167`).
##
## A `bool`, a container, or a non-integral float flag is refused by name rather
## than coerced, because coercing it would invent a gate result the save does not
## hold. `null` is checked FIRST and still means absent.
static func expected_ledger_increment(ledger: Variant, item_id: Variant,
		team: Variant, flag: Variant) -> Dictionary:
	if not is_item_id(item_id):
		return {
			"ok": false,
			"reason": REASON_INVALID_ITEM_ID,
			"error": "item_id must be an integer",
		}
	var increment := UnitBehaviors.expected_increment(ledger, item_id)
	if not bool(increment.get("resolvable", false)):
		return {
			"ok": false,
			"reason": REASON_INVALID_LEDGER,
			"error": str(increment.get("error", "the ledger is unreadable")),
		}
	# `null` is the ABSENT flag, which the helper treats as a refusal
	# (`engine.py:159`) rather than a zero -- so it is checked before the type
	# rule, which exists only to keep a bool or a container out of an integer.
	var flag_present := flag != null
	var flag_positive := false
	if flag_present:
		if not _whole_number(flag) and not (flag is String \
				and str(flag).strip_edges().is_valid_int()):
			return {
				"ok": false,
				"reason": REASON_INVALID_ITEM_ID,
				"error": "the committed resurrectable flag must be read as an "
					+ "integer or its string form",
			}
		flag_positive = UnitBehaviors.passes_resurrectable_gate(flag)
	var team_one := UnitBehaviors.passes_team_gate(team)
	var written := team_one and flag_positive
	var out := {
		"ok": true,
		"reason": "",
		"error": "",
		"entries": (increment.get("entries", {}) as Dictionary).duplicate(true),
		"written": written,
		"present_before": bool(increment.get("present_before", false)),
		"count_before": int(increment.get("count_before", 0)),
		"count_after": int(increment.get("count_after", 0)),
		"item_id": str(int(item_id)),
		"increment_computed_with_gates_held": true,
		"gates": {
			"player_team_one": {
				"recorded_team": team,
				"required": UnitBehaviors.PLAYER_TEAM,
				"holds": team_one,
			},
			"resurrectable_positive": {
				"recorded_flag": flag,
				"present": flag_present,
				"positive": flag_positive,
				"holds": flag_positive,
			},
		},
	}
	# The delegated increment assumed the write; when a gate declined there is no
	# write at all, so the pre-execution entries are the whole answer. This is
	# NOT a second ledger rule -- it is the "no write happened" arm of the one the
	# helper's shape already describes, and the suite exercises both arms.
	if not written:
		out["entries"] = UnitBehaviors.ledger_entries(ledger)
		out["count_before"] = int(out["entries"].get(str(int(item_id)), 0))
		out["count_after"] = out["count_before"]
		out["increment_computed_with_gates_held"] = false
	return out


## Every client key this line **REFUSES**, in sorted order.
##
## Three families, all refused before dispatch (design D2):
##
## 1. a **destruction count** — `lost`, `losses`, `destroyed`, and siblings;
## 2. the two **subtraction operands** the legacy count is computed from —
##    `sent` and `survived`;
## 3. the **legacy payload key** itself — any key `end_attack` reads.
##
## The third family is built from the derived inventory, so it tracks a legacy
## edit instead of drifting from it. When the inventory cannot be derived the
## derived set is empty and only the first two families are refused, which is
## **reported** rather than silently widened.
static func refused_client_keys(payload: Variant, inventory: Array = []) -> Array:
	if not (payload is Dictionary):
		return []
	var body: Dictionary = payload
	var refused: Array = []
	for key: Variant in body:
		var name := str(key)
		if DESTRUCTION_COUNT_KEYS.has(name) or SENT_SURVIVED_KEYS.has(name):
			refused.append(name)
			continue
		if inventory.has(name):
			refused.append(name)
	var unique: Array = []
	for name: String in refused:
		if not unique.has(name):
			unique.append(name)
	unique.sort()
	return unique


## The whole **read-only** projection of one combat intent, or its refusal.
##
## Every step of `VALIDATION_ORDER` that belongs to this module runs **here**,
## before anything is dispatched, which is what makes a refused request leave the
## recorded document byte-identical (design D3).
##
## `item_of` is a callable taking an **item id** and returning that item's
## committed configuration row (or `null`), so this module reads committed
## content through a parameter and **never resolves an item definition itself**.
##
## `inventory` is an already-derived field inventory, passed in so a caller can
## refuse the design-D2 client keys and project from **one** derivation rather
## than two independent reads of `command.py`. Omitted, it is derived here.
##
## Returns `{ok, reason, error, action, command, addressing_key, addressing_kind,
## eligible, addressed_row, ledger_before, ledger_after, destruction,
## ledger_written, gates, resource_delta, inventory}`.
static func project_combat(items: Variant, ledger: Variant, action: Variant,
		addressing: Variant, item_of: Callable,
		inventory: Dictionary = {}) -> Dictionary:
	var resolved_inventory: Dictionary = inventory
	if not bool(inventory.get("ok", false)):
		resolved_inventory = derive_field_inventory()
	var out := {
		"ok": false,
		"reason": "",
		"error": "",
		"action": action,
		"command": null,
		"addressing_key": null,
		"addressing_kind": "",
		"addressed_row": null,
		"ledger_before": null,
		"ledger_after": null,
		"destruction": 0,
		"ledger_written": false,
		"gates": UnitBehaviors.gates(),
		"resource_delta": [0, 0, 0, 0, 0, 0, 0, 0],
		"inventory": resolved_inventory,
		"ordering_rule": ORDERING_RULE,
		"validation_order": validation_order(),
	}

	# --- step 1: the action names one of the three branches ----------------
	if not is_action(action):
		out["reason"] = REASON_INVALID_ACTION
		out["error"] = "action must be one of " + ", ".join(ACTIONS)
		return out
	var name := str(action)
	out["command"] = str((ACTION_COMMAND as Dictionary)[name])
	out["addressing_key"] = wire_key(name)
	out["addressing_kind"] = str((ACTION_ADDRESSING as Dictionary)[name])

	# --- step 3: the addressing is well typed -------------------------------
	if not _addressing_is_well_typed(name, addressing):
		out["reason"] = _addressing_reason(name)
		out["error"] = str(out["addressing_key"]) \
			+ " must be an integer for action " + name
		return out

	# --- step 6: the ledger is read BEFORE anything is destroyed ------------
	var ledger_projection := project_ledger(ledger)
	out["ledger_before"] = ledger_projection
	if not bool(ledger_projection.get("ok", false)):
		out["reason"] = REASON_INVALID_LEDGER
		out["error"] = str(ledger_projection.get("error", "unreadable ledger"))
		return out
	var before_entries := UnitBehaviors.ledger_entries(ledger)

	if name == ACTION_KILL:
		# --- steps 4/5: the addressed row resolves --------------------------
		var resolved := address_row(items, addressing)
		if not bool(resolved.get("ok", false)):
			out["reason"] = str(resolved.get("reason", ""))
			out["error"] = str(resolved.get("error", ""))
			return out
		out["addressed_row"] = resolved.get("row")
		# The addressed row IS the whole eligible set for `kill`, because the
		# branch resolves one map key rather than searching for an identity. The
		# record is shaped exactly as `select_eligible_rows` shapes one, so a
		# caller -- and the typed parser -- reads one shape for both actions.
		out["eligible"] = {
			"ok": true,
			"reason": "",
			"error": "",
			"item_id": int(addressing),
			"eligible_keys": [str(int(addressing))],
			"eligible_count": 1,
			"addressed": true,
			"addressed_key": str(int(addressing)),
			"addressed_row": (resolved.get("row") as Array).duplicate(),
		}
		# --- `kill` NEVER touches the ledger (design D5) --------------------
		out["ok"] = true
		out["destruction"] = 1
		out["ledger_written"] = false
		out["ledger_after"] = {
			"entries": before_entries.duplicate(true),
			"written": false,
			"item_id": null,
			"note": "the kill branch holds no reference to privateState"
				+ "['deadHeroes'] and no call to push_dead_unit, so no ledger "
				+ "change is derived for it at all",
		}
		return out

	if name == ACTION_KILL_IID:
		# --- design D5: a proven no-op, delivered rather than refused -------
		out["ok"] = true
		out["ledger_written"] = false
		out["ledger_after"] = {
			"entries": before_entries.duplicate(true),
			"written": false,
			"item_id": null,
			"note": "the branch writes nothing -- every assignment target in its "
				+ "body is a bare Name and its only call is one print -- so no "
				+ "ledger change is derived for it at all",
		}
		return out

	# --- step 4: an eligible row resolves ----------------------------------
	var eligible := select_eligible_rows(items, addressing)
	out["eligible"] = eligible
	if not bool(eligible.get("ok", false)):
		out["reason"] = str(eligible.get("reason", ""))
		out["error"] = str(eligible.get("error", ""))
		return out
	var row: Array = eligible.get("addressed_row", [])

	# --- steps 6/7: the ledger increment, behind BOTH gates and no third ---
	var committed: Variant = null
	if item_of.is_valid():
		committed = item_of.call(int(row[SLOT_ITEM_ID]))
	var properties: Variant = null
	if committed is Dictionary:
		properties = (committed as Dictionary).get(UnitBehaviors.PROPERTIES_FIELD)
	var derived := expected_ledger_increment(ledger, addressing,
		row[SLOT_PLAYER], committed_resurrectable(properties))
	if not bool(derived.get("ok", false)):
		out["reason"] = str(derived.get("reason", ""))
		out["error"] = str(derived.get("error", ""))
		return out
	out["ledger_after"] = derived
	out["ledger_written"] = bool(derived.get("written", false))
	out["committed_resurrectable"] = committed_resurrectable(properties)
	out["ok"] = true
	# ALWAYS ONE. Never a count, never a loop, never a clamp.
	out["destruction"] = 1
	return out


## Build the request body for one combat intent, or a named refusal.
##
## Returns `{ok, reason, error, body}`; `body` is exactly **three** keys —
## `user_id`, `action`, and the addressing under that action's **own** wire key
## from `wire_key()`. There is deliberately **no** parameter through which a
## client could dictate a destruction count, a `sent`/`survived` pair, a
## resource delta, an honour, a reward, or a price: the body cannot express any
## of them, which is what makes `refused_client_keys()` a guard on a hostile
## request rather than on this line's own transport.
static func build_intent(user_id: String, action: Variant,
		addressing: Variant) -> Dictionary:
	if not is_action(action):
		return {"ok": false, "reason": REASON_INVALID_ACTION,
			"error": "action must be one of " + ", ".join(ACTIONS)}
	var name := str(action)
	if not _addressing_is_well_typed(name, addressing):
		return {"ok": false,
			"reason": _addressing_reason(name),
			"error": wire_key(name) + " must be an integer"}
	var body := {"user_id": user_id, "action": name}
	body[wire_key(name)] = int(addressing)
	return {"ok": true, "reason": "", "error": "", "body": body}


## Assemble the response envelope for one **accepted** combat intent.
##
## `projection` is a `project_combat()` result and `post` carries the
## post-execution state a caller measured:
##
##     ledger_after  the persisted ledger, in its RECORDED key order, or null
##     rows_before   the placement count before execution
##     rows_after    the placement count after execution
##     changed       the changed-pointer list the proof produced
##     resources     the seven stored resources AFTER execution
##     server_time   a recorded instant -- never the wall clock
##     game_version  the recorded game version, "" when unknown
##
## The envelope's shape is written in **exactly one place** in this module, and
## that is deliberate: the live service builds the same shape in
## `compat_service.py` and this module's typed parser is what both answers pass
## through, so a shape assembled twice inside one implementation is a shape that
## can drift from the parser that has to accept it.
##
## Every recorded absence travels in the answer beside the derived value, so a
## `false` here can never be read as a field that simply went missing.
static func build_response(action: Variant, addressing: Variant,
		projection: Dictionary, post: Dictionary) -> Dictionary:
	var name := str(action)
	var eligible: Dictionary = {}
	if projection.get("eligible") is Dictionary:
		eligible = projection.get("eligible")
	var derived_key: Variant = eligible.get("addressed_key", null)
	# The addressed row is read from the SAME record the eligible set lives in, for
	# both identity-addressed actions. `resolve` keeps its row under
	# `eligible.addressed_row` and never sets a top-level `addressed_row`, so
	# reading the top level reported `derived_row: null` for every destroy and the
	# typed parser then refused the very response the projection had built. The
	# top level is still consulted as a fallback, so the shape stays readable.
	var derived_row: Variant = null
	if eligible.get("addressed_row") is Array:
		derived_row = eligible.get("addressed_row")
	elif projection.get("addressed_row") is Array:
		derived_row = projection.get("addressed_row")
	var ledger_projection: Dictionary = {}
	if projection.get("ledger_before") is Dictionary:
		ledger_projection = projection.get("ledger_before")
	var derived_ledger: Dictionary = {}
	if projection.get("ledger_after") is Dictionary:
		derived_ledger = projection.get("ledger_after")
	var persisted: Variant = post.get("ledger_after")
	var ledger_after_entries: Array = []
	if persisted is Dictionary:
		# Recorded ORDER, deliberately not the sorted projection order: the
		# projection is a display, and this is the persisted document.
		for key: Variant in persisted as Dictionary:
			ledger_after_entries.append({
				"item_id": str(key),
				"count": int((persisted as Dictionary)[key]),
			})
	var branch: Dictionary = {}
	for record: Variant in BRANCHES:
		if str((record as Dictionary).get("action", "")) == name:
			branch = record
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(post.get("game_version", "")),
		"server_time": int(post.get("server_time", 0)),
		"result": "success",
		"action": name,
		"command": str(projection.get("command", "")),
		"branch": branch.duplicate(true),
		"addressing": {
			"key": str(projection.get("addressing_key", "")),
			"value": int(addressing),
			"kind": str(projection.get("addressing_kind", "")),
			"note": "the request names an IDENTITY or a KEY and nothing else; the "
				+ "destruction set is derived from the player's own recorded rows",
		},
		"destruction": {
			"count": int(projection.get("destruction", 0)),
			"derived": true,
			"derived_key": derived_key,
			"derived_row": (derived_row as Array).duplicate(true)
				if derived_row is Array else null,
			"eligible_keys": (eligible.get("eligible_keys") as Array).duplicate(true)
				if eligible.get("eligible_keys") is Array else [],
			# Read through `_parse_int`, never through `or 0`: GDScript's `or` is a
			# BOOLEAN operator, so `3 or 0` collapses the eligible count to `true` and
			# `int(true)` is 1. The count therefore read 1 against a three-row
			# eligible set and the typed parser's own consistency check caught it.
			"eligible_count": (BootData._parse_int(
				eligible.get("eligible_count")) as int)
				if BootData._parse_int(eligible.get("eligible_count")) != null else 0,
			"order": ORDERING_RECORD,
			"refused_count": CLIENT_DICTATED_REFUSAL,
			"refused_count_note": REFUSED_COUNT_NOTE,
			"printed_count_is_request": PRINTED_COUNT_IS_A_REQUEST,
			"rows_before": int(post.get("rows_before", 0)),
			"rows_after": int(post.get("rows_after", 0)),
		},
		"ledger_before": (ledger_projection.get("entries") as Array)
			.duplicate(true) if ledger_projection.get("entries") is Array else [],
		"ledger_after": ledger_after_entries if persisted is Dictionary else null,
		"ledger_written": bool(projection.get("ledger_written", false)),
		"ledger_gates": (derived_ledger.get("gates") as Dictionary)
			.duplicate(true) if derived_ledger.get("gates") is Dictionary else {},
		"gates": UnitBehaviors.gates(),
		"no_third_gate": UnitBehaviors.NO_THIRD_GATE,
		"team_asymmetry": team_asymmetry(),
		"kill_contract": (KILL_CONTRACT as Dictionary).duplicate(true)
			if name == ACTION_KILL else null,
		"kill_iid_contract": (KILL_IID_CONTRACT as Dictionary).duplicate(true)
			if name == ACTION_KILL_IID else null,
		"ordering_rule": ORDERING_RULE,
		"validation_order": validation_order(),
		"field_inventory": (projection.get("inventory") as Dictionary)
			.duplicate(true),
		"correction": corrections(),
		"divergence": (DIVERGENCE as Dictionary).duplicate(true),
		"refusals": (REFUSALS as Array).duplicate(true),
		"no_combat": NO_COMBAT,
		"no_cost_or_reward": NO_COST_OR_REWARD,
		"no_syringe_cost": NO_SYRINGE_COST,
		"no_placement_validation": NO_PLACEMENT_VALIDATION,
		"non_claims": (NON_CLAIMS as Array).duplicate(true),
		"provenance": (PROVENANCE as Dictionary).duplicate(true),
		"resources": (post.get("resources") as Dictionary).duplicate(true)
			if post.get("resources") is Dictionary else {},
		"changed": (post.get("changed") as Array).duplicate(true)
			if post.get("changed") is Array else [],
	}


## The intent's wire contract as the evidence report records it: the closed action
## vocabulary, the per-action addressing key, the keys a client may never send,
## and the four-part post-execution proof the endpoint requires.
static func intent_record() -> Dictionary:
	return {
		"actions": ACTIONS.duplicate(),
		"action_command": (ACTION_COMMAND as Dictionary).duplicate(true),
		"addressing_key": (ACTION_ADDRESSING_KEY as Dictionary).duplicate(true),
		"addressing": (ACTION_ADDRESSING as Dictionary).duplicate(true),
		"path": COMBAT_PATH,
		"body_keys": 3,
		"destruction_count": "ALWAYS 0 or 1, derived server-side; never a client "
			+ "number",
		"refused_client_keys": refused_client_keys({}),
		"destruction_count_keys": (DESTRUCTION_COUNT_KEYS as Array).duplicate(),
		"sent_survived_keys": (SENT_SURVIVED_KEYS as Array).duplicate(),
		"note": "THE REQUEST CARRIES AN IDENTITY AND NOTHING ELSE. The body is "
			+ "exactly three keys -- the save identity, a closed action, and the "
			+ "addressing under that action's own wire key -- so no destruction "
			+ "count, no sent/survived pair, no resource delta, no honour, and no "
			+ "price is even expressible (design D1/D2)",
		"proof": PROOF_HALVES,
		"identical_typed_shapes": true,
	}


## The whole recorded scope: what this line sends, what it never sends, and every
## refusal travelling with the answer.
static func scope_record() -> Dictionary:
	return {
		"delivered": [
			"a typed combat intent carrying only a save identity, a closed "
				+ "action, and that action's own addressing",
			"the server-derived destruction: the eligible rows, the addressed "
				+ "row, and a count of exactly one",
			"the field inventory RE-DERIVED from command.py bytes, with each key's "
				+ "fate measured rather than transcribed",
			"the four-part post-execution proof the endpoint requires",
			"the two kill contracts, delivered differently: kill deletes a row and "
				+ "never touches the ledger; kill_iid is a proven no-op",
		],
		"not_delivered": [
			"any client-dictated destruction count, in either direction",
			"any combat resolution: no damage, outcome, defence, hit chance, or "
				+ "life arithmetic",
			"any honour, reward, or resource movement, and no syringe cost",
			"any occupancy, bounds, type, or terrain check on a removed or "
				+ "reinstated row",
			"any mission dispatch, resolution, or completion: the mission "
				+ "vocabulary remains owned by godot-mission-vocabulary",
			"a reimplementation of the ledger projection or either increment gate, "
				+ "which are delegated whole to unit_behaviors.gd",
		],
		"delegated": [
			"project_ledger, committed_resurrectable, the increment, and both "
				+ "gates all live in unit_behaviors.gd",
		],
		"absent_helpers": (ABSENT_HELPERS as Array).duplicate(true),
		"arithmetic": (ARITHMETIC_RECORD as Dictionary).duplicate(true),
	}


## Display: the combat readout, with every recorded absence beside the answer so
## "it cost nothing" and "nothing else was checked" can never be read as
## interchangeable.
static func readout_text(result: CombatResult) -> String:
	var parts: Array = []
	if not result.ok:
		parts.append("no combat action (%s): %s"
			% [result.error_code, result.error_message])
		return " | ".join(parts)
	parts.append("action %s dispatched %s" % [result.action, result.command])
	if result.destruction_count == 0:
		parts.append("destroyed nothing: a proven no-op")
	else:
		parts.append("destroyed exactly %d server-derived row at map key %s"
			% [result.destruction_count, result.derived_key])
	parts.append("derived from %d eligible row(s) in recorded map-key order"
		% result.eligible_count)
	parts.append("ledger written: %s" % ("yes" if result.ledger_written else "no"))
	parts.append("two gates and no third (player team 1; committed resurrectable "
		+ "greater than zero)")
	parts.append("a client-dictated count is refused before dispatch; the legacy "
		+ "printed count is a REQUEST, not an outcome")
	parts.append("no damage, honour, reward, or syringe cost; nothing paid; no "
		+ "mission completed; no occupancy or bounds check")
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# The typed response
# ---------------------------------------------------------------------------


## Parses a v0 combat envelope — success or structured error — into the typed
## result, fail-closed in both directions.
##
## The parser is deliberately strict about exactly the claims this line exists
## to make, and lenient about everything else:
##
##   * `destruction.derived` **must** be `true` and the count must be `0` or `1`,
##     so a response claiming a client-chosen count is refused outright;
##   * `validation_order` must agree with this module's own `VALIDATION_ORDER`
##     step for step, so a service that reordered the checks fails here rather
##     than in a post-execution proof;
##   * `field_inventory.fates` must be this module's closed three-fate
##     vocabulary, so a fourth fate fails the parse;
##   * `ledger_written: true` requires BOTH gate records to report `holds: true`,
##     which is what forecloses a ledger write behind a declined gate;
##   * `resolve` requires a derived key that is among the reported eligible keys
##     and an eight-slot derived row; `kill` requires the derived key to be the
##     addressing itself; `kill_iid` requires a count of zero and no derived key;
##   * `refusals` must carry all five recorded refusals and `gates` exactly the
##     two the legacy helper evaluates;
##   * `resources` must be the seven non-negative integers every other response
##     carries, read through the shared `BootData` parsers.
##
## The response is the AUTHORITATIVE record of what the service did: the client
## applies `derived_row`, `ledger_after` and `resources` **verbatim** and
## discards its own expectations even where the two disagree.
static func parse_combat(payload: Variant) -> CombatResult:
	if not (payload is Dictionary):
		return combat_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _combat_error(envelope)
	if str(envelope.get("protocol", "")) != BootData.PROTOCOL:
		return combat_failure("protocol_mismatch",
			"expected protocol " + BootData.PROTOCOL + ", got "
				+ str(envelope.get("protocol")))
	if str(envelope.get("result", "")) != "success":
		return combat_failure("bad_response",
			"combat response did not report the legacy success result")
	if not is_action(envelope.get("action")):
		return combat_failure("bad_response",
			"the combat response names no delivered action")
	var action := str(envelope.get("action"))
	if str(envelope.get("command", "")) != str((ACTION_COMMAND as Dictionary)[action]):
		return combat_failure("bad_response",
			"the combat response reports a command the action does not dispatch")

	# --- the addressing, under the action's own wire key ---------------------
	var addressing: Variant = envelope.get("addressing")
	if not (addressing is Dictionary):
		return combat_failure("bad_response",
			"the combat response carries no addressing object")
	var addressing_body: Dictionary = addressing
	if str(addressing_body.get("key", "")) != wire_key(action):
		return combat_failure("bad_response",
			"the combat response reports its addressing under "
				+ str(addressing_body.get("key")) + ", not the action's own wire "
				+ "key " + wire_key(action))

	# --- the server-derived destruction (design D1/D2) ----------------------
	var destruction: Variant = envelope.get("destruction")
	if not (destruction is Dictionary):
		return combat_failure("bad_response",
			"the combat response carries no destruction object")
	var body: Dictionary = destruction
	if body.get("derived") != true:
		return combat_failure("bad_response",
			"the combat response does not mark its destruction count as "
				+ "server-derived, which is the load-bearing claim of this line")
	var count: Variant = BootData._parse_int(body.get("count"))
	if count == null or (int(count) != 0 and int(count) != 1):
		return combat_failure("bad_response",
			"the combat response reports a destruction count of "
				+ str(body.get("count")) + "; this operation derives exactly zero "
				+ "or one, never a count a client could have chosen")
	var derived_key: Variant = body.get("derived_key")
	var derived_row: Variant = body.get("derived_row")
	var eligible_keys: Variant = body.get("eligible_keys")
	var eligible_count: Variant = BootData._parse_int(body.get("eligible_count"))
	if not (eligible_keys is Array) or eligible_count == null:
		return combat_failure("bad_response",
			"the combat response carries no derived eligible set")
	if str(body.get("refused_count", "")) == "" \
			or str(body.get("printed_count_is_request", "")) == "":
		return combat_failure("bad_response",
			"the combat response omits the recorded refusal or the recorded "
				+ "reading of the legacy printed count")
	if int(eligible_count) != (eligible_keys as Array).size():
		return combat_failure("bad_response",
			"the combat response reports %d eligible rows against %d listed"
				% [int(eligible_count), (eligible_keys as Array).size()])
	if int(count) == 0:
		# A destruction of zero names NOTHING.  The earlier reading of this guard
		# required `derived_row` to be an array even when nothing was destroyed,
		# which contradicted the service: it sends `derived_row: null` whenever no
		# row was resolved, so the proven no-op could never be parsed.  Requiring
		# BOTH to be null is the stricter check, because it also rejects a response
		# that destroys nothing yet names a row.
		if derived_key != null or derived_row != null:
			return combat_failure("bad_response",
				"the combat response destroys nothing yet names a destroyed row")
		if action == ACTION_RESOLVE:
			return combat_failure("bad_response",
				"a resolve action that derived no eligible row cannot answer "
					+ "success; the service refuses it as no_eligible_row")
	elif not (derived_key is String) or str(derived_key) == "":
		return combat_failure("bad_response",
			"the combat response destroys a row but names no derived map key")
	elif not (derived_row is Array) or (derived_row as Array).size() != MAP_ROW_SLOTS:
		return combat_failure("bad_response",
			"the combat response carries no eight-slot derived row")
	if action == ACTION_KILL and derived_key != null:
		# The addressing is compared as an INTEGER, never as a string. The JSON
		# transport widens every number to a float on the pinned engine, so the
		# value the service echoes back arrives as 11.0 while the derived key is
		# the string "11" -- `str(11.0)` is "11.0", and a `str()`-on-both-sides
		# comparison therefore refused a correct response. `_optional_int` is the
		# module's own tolerance: it accepts an int and an integral float and
		# returns -1 for everything else, so a non-integer addressing still
		# cannot equal a real map key and the guard is not weakened.
		if str(derived_key) != str(_optional_int(addressing_body.get("value"))):
			return combat_failure("bad_response",
				"the kill response derived a map key other than the one it "
					+ "addressed")
	if action == ACTION_RESOLVE and derived_key != null:
		if not (eligible_keys as Array).has(str(derived_key)):
			return combat_failure("bad_response",
				"the destroy response derived a key outside its own reported "
					+ "eligible set")
	if action == ACTION_KILL_IID and int(count) != 0:
		return combat_failure("bad_response",
			"the item-keyed kill is a proven no-op and must destroy nothing")

	# --- the ledger, on both sides, and both gate records -------------------
	var ledger_before: Variant = envelope.get("ledger_before")
	if not (ledger_before is Array):
		return combat_failure("bad_response",
			"the combat response carries no ledger before execution")
	for entry: Variant in ledger_before as Array:
		if not (entry is Dictionary) or not (entry as Dictionary).has("item_id"):
			return combat_failure("bad_response",
				"a reported ledger entry carries no item id")
	var ledger_after: Variant = envelope.get("ledger_after")
	if ledger_after != null and not (ledger_after is Array):
		return combat_failure("bad_response",
			"the combat response carries an unreadable ledger after execution")
	var written_variant: Variant = envelope.get("ledger_written")
	# The type test comes BEFORE the value test. `written_variant != true` alone is
	# a mixed String/bool comparison, and GDScript refuses to evaluate it, so a
	# malformed field raised instead of refusing the response.
	if not (written_variant is bool):
		return combat_failure("bad_response",
			"the combat response carries no boolean ledger_written statement")
	var ledger_written := bool(written_variant)
	var ledger_gates: Variant = envelope.get("ledger_gates")
	if not (ledger_gates is Dictionary):
		return combat_failure("bad_response",
			"the combat response carries no evaluated gate records")
	if ledger_written:
		for gate: String in ["player_team_one", "resurrectable_positive"]:
			var record: Variant = (ledger_gates as Dictionary).get(gate)
			if not (record is Dictionary):
				return combat_failure("bad_response",
					"a ledger write is reported without the " + gate + " record")
			if (record as Dictionary).get("holds") != true:
				return combat_failure("bad_response",
					"the combat response writes the ledger behind a declined "
						+ gate + ", which is exactly the third rule this line "
						+ "refuses to invent")

	# --- the recorded absences and both gates --------------------------------
	var gates: Variant = envelope.get("gates")
	if not (gates is Array) or (gates as Array).size() != UnitBehaviors.GATE_COUNT:
		return combat_failure("bad_response",
			"the combat response does not carry the "
				+ str(UnitBehaviors.GATE_COUNT) + " gates the legacy helper "
				+ "evaluates")
	for gate: Variant in gates as Array:
		if not (gate is Dictionary) or str((gate as Dictionary).get("source", "")) == "":
			return combat_failure("bad_response",
				"a reported gate names no source line")
	if str(envelope.get("no_third_gate", "")) == "":
		return combat_failure("bad_response",
			"the combat response omits the recorded absence of a third gate")
	var asymmetry: Variant = envelope.get("team_asymmetry")
	if not (asymmetry is Dictionary) or (asymmetry as Dictionary).is_empty():
		return combat_failure("bad_response",
			"the combat response omits the recorded team asymmetry")
	if str(envelope.get("ordering_rule", "")) == "":
		return combat_failure("bad_response",
			"the combat response omits the recorded ordering rule")
	var reported_order: Variant = envelope.get("validation_order")
	if not (reported_order is Array):
		return combat_failure("bad_response",
			"the combat response carries no validation order")
	if (reported_order as Array).size() != VALIDATION_ORDER_STEPS:
		return combat_failure("bad_response",
			"the combat response reports %d validation steps, not the %d this "
				% [(reported_order as Array).size(), VALIDATION_ORDER_STEPS]
				+ "client declares")
	for index in range(VALIDATION_ORDER_STEPS):
		var expected: Dictionary = (VALIDATION_ORDER as Array)[index]
		var actual: Variant = (reported_order as Array)[index]
		if not (actual is Dictionary):
			return combat_failure("bad_response",
				"a reported validation step is not an object")
		for field: String in VALIDATION_ORDER_FIELDS:
			var expected_value: Variant = expected.get(field)
			var actual_value: Variant = (actual as Dictionary).get(field)
			if not _validation_order_field_agrees(actual_value,
					expected_value, VALIDATION_ORDER_FIELD_TYPES[field]):
				return combat_failure("bad_response",
					"the combat response's validation order disagrees with the "
						+ "client's at step " + str(index + 1) + " field " + field)

	# --- the field inventory, its corrections, and the divergence ----------
	var inventory: Variant = envelope.get("field_inventory")
	if not (inventory is Dictionary) or (inventory as Dictionary).get("ok") != true:
		return combat_failure("bad_response",
			"the combat response carries no re-derived field inventory")
	var inventory_body: Dictionary = inventory
	var reported_fates: Variant = inventory_body.get("fates")
	if not (reported_fates is Array) or (reported_fates as Array).size() != \
			(FATES as Array).size():
		return combat_failure("bad_response",
			"the combat response reports a fate vocabulary this client does not "
				+ "know, so a key could be filed under an unrecognised fate")
	for index in range((FATES as Array).size()):
		if str((reported_fates as Array)[index]) != str((FATES as Array)[index]):
			return combat_failure("bad_response",
				"the combat response's fate vocabulary disagrees with the "
					+ "client's")
	if not (inventory_body.get("keys") is Array) \
			or (inventory_body["keys"] as Array).is_empty():
		return combat_failure("bad_response",
			"the combat response's field inventory names no keys")
	if inventory_body.get("partition") != true:
		return combat_failure("bad_response",
			"the combat response's field inventory does not partition into the "
				+ "three fates, so a key was filed under none of them")
	var correction: Variant = envelope.get("correction")
	if not (correction is Dictionary) \
			or not (correction as Dictionary).has("field_inventory") \
			or not (correction as Dictionary).has("corpus"):
		return combat_failure("bad_response",
			"the combat response omits a recorded-versus-measured correction")
	var divergence: Variant = envelope.get("divergence")
	if not (divergence is Dictionary) \
			or str((divergence as Dictionary).get("status", "")) \
			!= "DIVERGENCE, NOT PARITY":
		return combat_failure("bad_response",
			"the combat response does not report the recorded divergence, which "
				+ "is this line's load-bearing non-parity claim")
	var refusals: Variant = envelope.get("refusals")
	if not (refusals is Array) or (refusals as Array).size() != REFUSAL_COUNT:
		return combat_failure("bad_response",
			"the combat response does not carry the "
				+ str(REFUSAL_COUNT) + " recorded refusals")
	if str(envelope.get("no_combat", "")) == "" \
			or str(envelope.get("no_cost_or_reward", "")) == "" \
			or str(envelope.get("no_syringe_cost", "")) == "" \
			or str(envelope.get("no_placement_validation", "")) == "":
		return combat_failure("bad_response",
			"the combat response omits one of the four recorded no-* statements, "
				+ "so a recorded absence could be read as an omission")
	var kill_contract: Variant = envelope.get("kill_contract")
	var kill_iid_contract: Variant = envelope.get("kill_iid_contract")
	if action == ACTION_KILL and not (kill_contract is Dictionary):
		return combat_failure("bad_response",
			"the kill response carries no kill contract")
	if action == ACTION_KILL_IID and not (kill_iid_contract is Dictionary):
		return combat_failure("bad_response",
			"the item-keyed kill response carries no proven-no-op contract")
	var no_op_contract := {} if not (kill_iid_contract is Dictionary) \
		else (kill_iid_contract as Dictionary)
	if not no_op_contract.is_empty() \
			and no_op_contract.get("statement_writes_save_state") != false:
		return combat_failure("bad_response",
			"the item-keyed kill contract no longer records that the branch "
				+ "writes nothing")
	var non_claims: Variant = envelope.get("non_claims")
	if not (non_claims is Array) or (non_claims as Array).is_empty():
		return combat_failure("bad_response",
			"the combat response carries no non-claims")
	var provenance: Variant = envelope.get("provenance")
	if not (provenance is Dictionary) or (provenance as Dictionary).is_empty():
		return combat_failure("bad_response",
			"the combat response carries no provenance")
	var changed: Variant = envelope.get("changed")
	if not (changed is Array):
		return combat_failure("bad_response",
			"the combat response carries no changed-pointer list")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return combat_failure("bad_response",
			"combat response carries no resources object")
	var resources := BootData._parse_resources(resources_raw)
	if resources == null:
		return combat_failure("bad_response",
			"combat resources are not seven non-negative integers")

	var result := CombatResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return combat_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.action = action
	result.command = str(envelope.get("command", ""))
	result.addressing_key = str(addressing_body.get("key", ""))
	result.addressing_value = _optional_int(addressing_body.get("value"))
	result.addressing_kind = str(addressing_body.get("kind", ""))
	result.addressing_note = str(addressing_body.get("note", ""))
	result.destruction_count = int(count)
	result.destruction_derived = true
	result.derived_key = "" if derived_key == null else str(derived_key)
	result.derived_row = [] if not (derived_row is Array) \
		else (derived_row as Array).duplicate(true)
	result.eligible_keys = (eligible_keys as Array).duplicate(true)
	result.eligible_count = int(eligible_count)
	result.destruction_order = str(body.get("order", ""))
	result.printed_count_is_request = str(body.get("printed_count_is_request", ""))
	result.rows_before = _optional_int(body.get("rows_before"))
	result.rows_after = _optional_int(body.get("rows_after"))
	result.ledger_before = (ledger_before as Array).duplicate(true)
	result.ledger_after = [] if ledger_after == null \
		else (ledger_after as Array).duplicate(true)
	result.ledger_written = ledger_written
	result.ledger_gates = (ledger_gates as Dictionary).duplicate(true)
	result.gates = (gates as Array).duplicate(true)
	result.no_third_gate = str(envelope.get("no_third_gate", ""))
	result.team_asymmetry = (asymmetry as Dictionary).duplicate(true)
	result.kill_contract = {} if not (kill_contract is Dictionary) \
		else (kill_contract as Dictionary).duplicate(true)
	result.kill_iid_contract = {} if not (kill_iid_contract is Dictionary) \
		else (kill_iid_contract as Dictionary).duplicate(true)
	result.ordering_rule = str(envelope.get("ordering_rule", ""))
	result.validation_order = (reported_order as Array).duplicate(true)
	result.field_inventory = (inventory_body as Dictionary).duplicate(true)
	result.correction = (correction as Dictionary).duplicate(true)
	result.divergence = (divergence as Dictionary).duplicate(true)
	result.refusals = (refusals as Array).duplicate(true)
	result.no_combat = str(envelope.get("no_combat", ""))
	result.no_cost_or_reward = str(envelope.get("no_cost_or_reward", ""))
	result.no_syringe_cost = str(envelope.get("no_syringe_cost", ""))
	result.no_placement_validation = str(envelope.get("no_placement_validation", ""))
	result.non_claims = (non_claims as Array).duplicate(true)
	result.provenance = (provenance as Dictionary).duplicate(true)
	result.proof_halves = (PROOF_HALVES as Array).duplicate(true)
	result.changed = (changed as Array).duplicate(true)
	result.resources = resources
	return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


## Whether a value is a whole number the legacy helpers could compare against an
## item id. The pinned engine's JSON parser widens every committed number to a
## float, so an integral float is accepted and nothing else is: a `bool` is never
## an item id, and a non-integer is **unreadable** rather than coercible.
static func _whole_number(value: Variant) -> bool:
	if value is bool:
		return false
	if value is int:
		return true
	if value is float:
		var number := float(value)
		return number == floor(number) and not is_inf(number) and not is_nan(number)
	return false


## The recorded type of a value as a readable name, so a refusal can say what the
## save actually held rather than only that it was wrong.
static func _type_name(value: Variant) -> String:
	if value == null:
		return "null"
	if value is bool:
		return "boolean"
	if value is int:
		return "int"
	if value is float:
		return "float"
	if value is String:
		return "String"
	if value is Array:
		return "Array"
	if value is Dictionary:
		return "Dictionary"
	return type_string(typeof(value))


## An integer field that is legitimately absent from a response, so an absent one
## reads as `-1` rather than `0`.
static func _optional_int(value: Variant) -> int:
	var parsed: Variant = BootData._parse_int(value)
	return -1 if parsed == null else int(parsed)


## The service's own structured error (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
static func _combat_error(envelope: Dictionary) -> CombatResult:
	var code := "bad_response"
	var message := "compatibility API reported an error"
	if envelope.get("ok") == false:
		var error: Variant = envelope.get("error")
		if error is Dictionary:
			code = str((error as Dictionary).get("code", code))
			message = str((error as Dictionary).get("message", message))
	elif envelope.get("ok") == null:
		return combat_failure("bad_response",
			"the combat response reports no `ok` statement")
	return combat_failure(code, message)