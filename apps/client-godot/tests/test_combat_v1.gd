extends "res://tests/test_base.gd"
## Server v1 **combat-authority** client suite (OpenSpec change
## `combat-attack-authority`; spec: "Server v1 is reachable through the GameApi
## abstraction", "A refused v1 action moves nothing").
##
## Scenarios:
##   ""     (default, hermetic) the new typed result, the intent body, the
##          committed unit table re-derived on every run, and the structural
##          invariants that keep this client from becoming a second combat
##          engine. No server, no socket.
##   live   drives `ServerV1Api.combat_town` through the `GameApi` facade against
##          a running `apps/server-v1` service over loopback, and diffs the
##          disposable corpus save file **across** the call. Only
##          `verify-boot.ps1`'s `combat-live-v1` phase runs this.
##
## ## The claim this suite exists to keep
##
## **A combat outcome is a server-authoritative answer this client reports and
## does not compute, and this route destroys nothing at all.** v1 resolves the
## client's unit identity against the committed `items` rows whose `type` column
## is `u`, reports the nine committed combat columns **verbatim as the strings the
## committed table stores**, reports both `push_dead_unit` gates without enforcing
## either, and answers `rows_destroyed: 0` with a five-check proof that the whole
## persisted document is byte-identical. The client sends a save identity and a
## unit identity. Nothing else travels.
##
## ## Why almost every check here is a refusal
##
## The preserved branch (`command.py:862-875`) computes
## `lost = max(0, unit[2] - unit[3])` from **two numbers the client sends** and
## destroys that many rows through `map_lose_item`, so the count is client-dictated
## in full. Nine committed combat columns exist and **none of them names that
## outcome** - `attack` is not even a whole-word occurrence anywhere in the
## preserved source, all twelve of its whole-file occurrences sitting inside longer
## identifiers (`end_attack`, `attacker`, `attacker_units`,
## `flash_reload_attack`). So design D2's client half is entirely negative, and a
## negative claim is only worth something if it is mechanical. It is asserted six
## ways:
##
## 1. `_check_intent_body` pins the request to exactly two keys, and asserts the
##    enclosing function does **not** forward its `action` parameter.
## 2. `_check_no_client_arithmetic` walks the new typed-result module and fails on
##    any scaling operator, with an **empty** exception list.
## 3. `_check_no_line_compares_two_reported_values` requires each of the nine
##    committed combat columns to appear **nowhere** in the module's code except
##    inside the reporting constant, and fires on any line that *relates* two
##    reported names rather than listing them.
## 4. `_check_absent_derivation_helpers` refuses an invented helper by **name** and
##    by **substring**, in **both** directions, against the declared function
##    inventory of the delivered module - and pins that inventory whole.
## 5. `_check_domain_inventory` and `_check_domain_reserved_stems` do the same
##    against the **Python domain module**, read from the repository at runtime
##    rather than transcribed.
## 6. `_check_committed_units_are_re_derived` re-reads the committed unit mirror
##    on every run and **measures** the absent-`resurrectable` set rather than
##    asserting the transcription.
##
## ## What this suite deliberately does NOT do
##
## It does not compute a hit chance, compare `attack` with `defense`, decide
## whether a gate would pass, count how many rows *could* be destroyed, or compare
## `before` with `after`. Each of those is either a rule **the server's own
## post-execution proof already established** (`apps/server-v1/tests/test_combat.py`)
## or an invention this surface exists to refuse. The values are carried verbatim
## and the guards above fail if any of them ever is.
##
## ## The absent committed key is not a zero
##
## Unit `923` (Gorilla) is one of **three** committed ids whose `properties`
## object carries no `resurrectable` key **at all**, rather than a committed
## `"0"`. The preserved helper returns `False` on an absent key rather than
## reading one, so absent and zero are different facts. That is why this suite
## carries **two** observed successes rather than one plus a note, and why
## `_check_observed_absent_flag_parses` asserts the two payloads differ in
## **exactly three leaves** and nowhere else in the `gates` block.
##
## ## The line endings are measured, never asserted
##
## `modules_are_pure_lf` in the report is measured on the bytes themselves.
## `godot-market-trade` shipped a hard-coded `false` beside a true statement about
## the *checkout* rather than about the *files*; copying a field **and its value**
## across file forms is how a guard becomes a lie, so the flag here comes from
## `_modules_are_pure_lf()` and nothing else.

## This suite's own repository path, read by the self-scanning format guard.
const SUITE_REPO_PATH := "apps/client-godot/tests/test_combat_v1.gd"
const COMBAT_SCRIPT_PATHS = preload("res://scripts/package_paths.gd")
const ServerV1Api = preload("res://scripts/gameapi/server_v1_api.gd")
const ServerV1Combat = preload(
	"res://scripts/gameapi/server_v1_combat_result.gd")
const CollectSuite = preload("res://tests/test_server_v1.gd")

const API_SCRIPT := "scripts/gameapi/server_v1_api.gd"
const RESULT_SCRIPT := "scripts/gameapi/server_v1_combat_result.gd"
const FACADE_SCRIPT := "scripts/gameapi/game_api.gd"
const V0_SCRIPT := "scripts/gameapi/legacy_v0_api.gd"
const FAKE_SCRIPT := "scripts/gameapi/fake_api.gd"
const PRESERVED_SUITE := "tests/test_combat_actions.gd"
const FRIEND_SUITE := "tests/test_friends.gd"
const LIVE_PHASE_SCRIPT := "apps/client-godot/server_v1_live_phase.py"
const COLLECT_SUITE_SCRIPT := "tests/test_server_v1.gd"
const SCOPE_SCRIPT := "tests/test_project_scope.gd"
const SELF_SCRIPT := "test_combat_v1.gd"

## This line's own intent on the facade, and the three that came before it.
const INTENT_METHOD := "combat_town"

## The repository-relative paths this suite reads but does not deliver.
const DOMAIN_MODULE := "apps/server-v1/server_v1_combat.py"
## Where the seven stored-resource PATHS are actually declared. The combat
## domain only *imports* `STORED_RESOURCE_NAMES` from here, so reading the
## domain module for the table would have found nothing - which is what the
## first version of the holder cross-check did, and why it reported zero pairs.
const REPOSITORY_MODULE := "apps/server-v1/server_v1_repository.py"
const CONTENT_MODULE := "apps/server-v1/server_v1_content.py"
const REFUSALS_MODULE := "apps/server-v1/server_v1_refusals.py"
const RAW_CONFIG := "config/main.json"
const NORMALIZED_UNITS := "packages/game-content/normalized/units.json"
const NORMALIZED_BUILDINGS := "packages/game-content/normalized/buildings.json"

const DELIVERED_MODULES := [RESULT_SCRIPT, API_SCRIPT]

## The concrete type each `GameApi` implementation declares for **this** line's
## intent. The two v0 implementations still declare v0's model, which is the whole
## reason the facade is `Variant`: the two surfaces disagree on what a combat
## answer **is**, and one model absorbing both would have to pick a sign
## convention for three fields that mean different things in the two.
const IMPL_RETURN_TYPES := {
	"scripts/gameapi/fake_api.gd": "CombatFlow.CombatResult",
	"scripts/gameapi/legacy_v0_api.gd": "CombatFlow.CombatResult",
	"scripts/gameapi/server_v1_api.gd":
		"ServerV1Combat.CombatAuthorityResult",
}

## The whole declared function inventory of the delivered typed-result module,
## as this suite knows it. Read here rather than transcribed inline so the list
## lives beside the reserved stems that are checked against it. Pinned **whole**,
## because an inventory check that only forbade a name would pass a module that had
## quietly grown a helper of any other name - and the inventory is the real gate
## while the reserved-stem scan is the belt.
const RESULT_FUNCTION_INVENTORY := [
	"_behaviour", "_committed", "_gates", "_identity", "_proof",
	"_refusal", "_report_block", "_resources", "_sorted", "_string_list",
	"_success",
	"_whole_number", "combat_failure", "parse_combat_authority",
]

## The **combat-owned** functions of the transport module. Not the module's whole
## inventory: `test_magic_v1.gd` owns that, by name and with an explicit hand-off,
## and two owners of one list is the drift this repository has already recorded
## twice. What this suite owns is the pair that *is* the request.
const API_COMBAT_FUNCTIONS := ["_combat_intent_body", "combat_town"]

## **Nineteen reserved stems for a client-side or server-side derivation.** Each is
## a name a rule that must not exist here would plausibly be given.
##
## The comparison is by **substring**, folded to lower case, in **both**
## directions, against **declared function names** rather than raw source:
## `godot-friends` measured that an exact-name check passes a helper merely
## *prefixed* with a reserved word (`roster_order_by_xp` for a reserved `order`),
## and that a case-sensitive one passes `Friend_Of`; and
## `godot-construction-assist` measured that scanning raw source makes the guard's
## own inventory text trip it unconditionally.
##
## `"destruction"` is deliberately **absent** from this list, and that omission is
## a measured one rather than an oversight: the domain module legitimately declares
## `_destruction_refusal` and `_destruction_report`, and inventing a stem that
## flagged them would have made the guard fail on correct code. The specific
## invention it would have caught - a helper that turns the reported request into a
## count - is covered by the pinned inventories instead, and `_count` is in the list
## anyway, so `destruction_count_for` is caught.
const RESERVED_DERIVATION_STEMS := [
	"attack", "chance", "count", "credit", "damage", "defense", "destroy",
	"health", "hit", "honor", "kill", "ledger", "loss", "lost", "outcome",
	"pay", "payout", "resurrect", "victim",
]

## Operators that would let a client **scale** a reported value. `+` is absent on
## purpose: the delivered module concatenates prose with it in six places, and
## string concatenation is not arithmetic. Measured, not assumed: the code-only
## projection of the module contains **none** of these, and the positive control
## below proves the scan finds one when it is there.
const SCALING_OPERATORS := ["*", "/", "+=", "-=", "*=", "/="]

## An operator that **relates** two values on one line. A line that merely *lists*
## names is not a relation, which is why the reporting constant is allowed to
## carry five committed columns on one line without tripping the pair rule.
const RELATION_OPERATORS := [
	"<", ">", "<=", ">=", "==", "!=", "+", "-", "*", "/",
]

## The six codes the observed refusals resolve to, each with its `RefusalCode`
## member, its HTTP status, and whether the **domain** module names it. The last
## flag is the interesting one: `client_supplied_delta` and
## `unknown_request_field` are raised by the request and transport layers before
## the domain is entered, so a scan of the domain module alone would report them
## unused and that would be true.
const EXPECTED_COMBAT_REFUSALS := {
	"unaddressable_row": ["UNADDRESSABLE_ROW", 409, true],
	"client_dictated_destruction": ["CLIENT_DICTATED_DESTRUCTION", 409, true],
	"malformed_request": ["MALFORMED_REQUEST", 400, true],
	"unknown_player": ["UNKNOWN_PLAYER", 404, true],
	"client_supplied_delta": ["CLIENT_SUPPLIED_DELTA", 400, false],
	"unknown_request_field": ["UNKNOWN_REQUEST_FIELD", 400, false],
}

## The **seven** `RefusalCode` members the domain module names, measured over the
## committed file. Six are this route's; `POST_CONDITION_VIOLATION` belongs to the
## shared post-condition proof and to no single route. Pinned so an eighth combat
## code cannot land in the domain unnoticed.
const DOMAIN_NAMED_CODES := [
	"CLIENT_DICTATED_DESTRUCTION", "MALFORMED_REQUEST",
	"POST_CONDITION_VIOLATION", "UNADDRESSABLE_ROW", "UNKNOWN_PLAYER",
	"UNREADABLE_CONTENT", "UNREADABLE_STATE",
]

## The closed status table v1 declares, one code per line, measured every run.
const DECLARED_REFUSAL_CODE_COUNT := 20

## The stored balances of the disposable corpus the observed answers were taken
## against. Every one of the seven is **unchanged** by this route, and the observed
## `resources_after` block is checked against these rather than against itself.
const OBSERVED_BALANCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}

## The committed ids whose `properties` object carries **no** `resurrectable` key.
## Measured over `packages/game-content/normalized/units.json` on every run; this
## is the figure the absent-key success exists to keep distinguishable from a
## committed zero.
const ABSENT_RESURRECTABLE_IDS := [923, 933, 1176]

## The committed unit row the live phase addresses. The disposable corpus places
## **no unit row at all** (40 placements, every committed `type` `b`), so the
## identity is the only exercisable part and no row is needed for it to resolve.
const LIVE_UNIT := 1001

## A committed **building** id, used by the live phase to prove the three committed
## id spaces do not overlap: the same `unaddressable_row` code answers for it.
const LIVE_BUILDING := 22

const SCHEME := "http:"
const SLASHES := "//"
const ARG_PLAYER_ID := "--player-id="
const ARG_CORPUS := "--corpus="
const ARG_ENDPOINT := "--gameapi-endpoint="
const LIVE_ENDPOINT := SCHEME + SLASHES + "127.0.0.1:5057"
const SAVE_SUFFIX := ".save.json"

## ## The observed v1 **success**, verbatim
## ##
## Captured by running the real `apps/server-v1` service over the real
## ASGI stack against a disposable corpus, then read out of the
## response body -- not composed from the parser's expectations. Every
## field the parser reads is here, including the nine long prose
## sentences, because a fixture trimmed to the fields under test would
## let a parser that ignored the rest pass.
## ##
## `destroyed`-free by construction: `rows_destroyed` is 0 and
## `document_unchanged` is true because **v1 has no write path at all**,
## which is the whole finding of this route.
const OBSERVED_SUCCESS := {
		"action": "combat",
		"combat": {
			"identity_field": "unit_id",
			"identity_resolved_against": "the committed items rows with type u",
			"unit_id": 1001,
		},
		"committed": {
			"combat_fields": {
				"attack": "6",
				"attack_interval": "35",
				"attack_range": "1",
				"best_against": "ft_ground",
				"best_against_mult": "1",
				"defense": "1",
				"life": "25",
				"min_level": "0",
				"syringes": "1",
			},
			"combat_fields_legacy_consumers": 0,
			"combat_fields_note": "each of these nine measures zero legacy occurrences over the preserved modules, and the only one that appears at all (attack) has a whole-word count of 0 with all twelve whole-file occurrences inside longer identifiers, so no committed column names this branch's outcome",
			"combat_fields_stored_as": "strings in the committed items table; reported verbatim and never read as a number",
			"id": "1001",
			"id_keyed_by": "the committed id column, which the normalized package calls legacy_id, not the row's position in the committed array",
			"name": "Worker I",
			"resolved_against": "the committed items rows whose type column is u; the three committed id spaces have zero overlap, so a building or the special cannot resolve",
			"resolved_id": 1001,
			"type": "u",
		},
		"damage_derived": false,
		"derivation_performed": null,
		"derived_damage": null,
		"derived_destruction_count": null,
		"destruction": {
			"applied": false,
			"count": null,
			"count_derived": false,
			"count_refused_because": "no committed value names this branch's outcome: the nine committed combat columns have zero legacy consumers, and the preserved branch's only quantity is a subtraction of two client numbers (design D2)",
			"ledger_rule": "engine.py:223 pushes each destroyed row onto privateState['deadHeroes'] through push_dead_unit, which requires the row's team to be exactly 1 (engine.py:151) and the item's committed resurrectable to be greater than zero (engine.py:159-162); v1 reports both gates and credits nothing",
			"preserved_rule": "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers the CLIENT sends, and command.py:872 destroys that many rows through map_lose_item, so the count is client-dictated in full; the committed source labels the two numbers only 'A' and 'B'",
			"refused_by_code": "client_dictated_destruction",
			"refused_status": 409,
			"rejected_alternatives": {
				"derive_from_attack_minus_defense": "neither committed column is read by anything and attack is not even a whole-word occurrence in the preserved source",
				"destroy_every_eligible_row": "the client still chooses which unit and the server still cannot say how many; the count is still client-dictated in a different spelling, and an identity with no matching row would get a silent success",
				"destroy_one_row": "v0's resolve action reports destruction: 1, but that 1 is a property of combat_payload's own construction and the same v0 route destroyed two rows for A=3, B=1 at committed fixture step 7, so one is a fixture convenience rather than a rule",
			},
			"requested": null,
			"requested_is_none_because": "a request carrying the branch's destruction shape is refused before the identity is resolved, so a successful request never had one",
		},
		"document_unchanged": true,
		"gates": {
			"enforced": false,
			"enforced_note": "neither gate is a precondition here: the transaction destroys nothing, so there is no operation for a gate to stand in front of (design D3)",
			"gate_one_team": {
				"absence_reported_as": "null verdicts and an empty row list, because the gate has no input when no recorded row carries the identity",
				"any_row_would_pass": null,
				"every_row_would_pass": null,
				"preserved_test": "push_dead_unit requires the row's recorded slot 7 to be exactly 1 and returns False otherwise (engine.py:151)",
				"recorded_team": null,
				"row_count": 0,
				"row_present": false,
				"rows": [],
				"source": "maps[0].items[key][7] of every recorded row whose item id is the addressed committed identity",
			},
			"gate_two_resurrectable": {
				"absence_note": "an absent key is reported as absent and never as 0, because the preserved helper returns False on an absent key rather than reading one",
				"absent_is_read_as_zero": false,
				"committed_value": "1",
				"committed_value_is": "the committed value verbatim; the committed encoding is the string, and it is compared as a number exactly as the preserved helper does, never by truthiness",
				"present": true,
				"preserved_test": "push_dead_unit reads the committed properties object, returns False when the key is absent, and otherwise compares int(resurrectable) > 0 (engine.py:155-162)",
				"source": "the committed unit row's properties object",
				"stored_as": "an embedded JSON string inside the committed items row, not a top-level column of it",
				"would_pass": true,
			},
		},
		"gates_enforced": false,
		"instant": 1791500000,
		"leaf_paths_changed": [],
		"ledger_covered_by": "the whole-document comparison, not a subset read: the dead-hero ledger is one key among every key compared",
		"ledger_credited": false,
		"preserved_branch_behaviour": {
			"absent_value": "command.py:866 and :874 dereference attacker_units and victim without a None check, so an omitted shape raises, the batch is discarded before the save is written (command.py:30,32), and the response is an HTTP 500; this is established by execution on fixture steps 2 and 4, not reasoned",
			"destruction": "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers the CLIENT sends, and command.py:872 destroys that many rows through map_lose_item, so the count is client-dictated in full; the committed source labels the two numbers only 'A' and 'B'",
			"ledger": "engine.py:223 pushes each destroyed row onto privateState['deadHeroes'] through push_dead_unit, which requires the row's team to be exactly 1 (engine.py:151) and the item's committed resurrectable to be greater than zero (engine.py:159-162); v1 reports both gates and credits nothing",
			"reached": "map_lose_item has exactly two call sites -- command.py:796 (end_quest) and command.py:872 (end_attack) -- so two branches reach one helper; godot-unit-behaviors counted push_dead_unit's callers and map_lose_item separately and called it three doors, and that archived line is not edited",
		},
		"proof": [
			[
				"identity_resolved_to_reported_row",
				true,
			],
			[
				"reported_gates_match_content_and_state",
				true,
			],
			[
				"no_leaf_path_changed",
				true,
			],
			[
				"whole_document_unchanged",
				true,
			],
			[
				"resources_unchanged",
				true,
			],
		],
		"protocol": "server-v1",
		"resources_after": {
			"cash": 5,
			"gold": 2000,
			"mana": 0,
			"oil": 2000,
			"steel": 2000,
			"wood": 2000,
			"xp": 4,
		},
		"result": "success",
		"rows_destroyed": 0,
		"stored_resources_compared": [
			"cash",
			"gold",
			"mana",
			"oil",
			"steel",
			"wood",
			"xp",
		],
		"team_asymmetry": {
			"consequence": "on a team-3 row the preserved server destroys the row and credits nothing to the dead-hero ledger",
			"ledger_test": "push_dead_unit requires slot 7 to be exactly 1 (engine.py:151) and returns False for every other team",
			"reconciled": false,
			"selector_test": "map_lose_item selects a row whose slot 7 is TRUTHY (engine.py:221), so any recorded team it does not read as 0 is eligible for destruction",
			"why_not_reconciled": "unknown: no committed row and no legacy line explains the difference, and every committed unit row in the corpus is on team 1, so the asymmetry is unexercisable rather than merely unexplained",
		},
	}


## ## The same route, answered for the identity whose committed
## `properties` object carries **no `resurrectable` key at all**
## ##
## Unit 923 (Gorilla) is one of the **three** committed ids the key is
## absent from rather than set to zero. The answer is identical to
## `OBSERVED_SUCCESS` except in `gate_two_resurrectable`, where
## `present` is false and **both** `committed_value` and `would_pass`
## are explicit nulls.
## ##
## That is the whole reason this fixture exists and it is carried as a
## second success rather than as a note: an absent committed key and a
## committed `"0"` are different facts, the preserved helper returns
## False on an absent key rather than reading one, and a client that
## collapsed the two would be making a statement about the corpus
## rather than about the save.
const OBSERVED_ABSENT_FLAG_SUCCESS := {
		"action": "combat",
		"combat": {
			"identity_field": "unit_id",
			"identity_resolved_against": "the committed items rows with type u",
			"unit_id": 923,
		},
		"committed": {
			"combat_fields": {
				"attack": "10",
				"attack_interval": "25",
				"attack_range": "1",
				"best_against": "",
				"best_against_mult": "1",
				"defense": "1",
				"life": "100",
				"min_level": "0",
				"syringes": "0",
			},
			"combat_fields_legacy_consumers": 0,
			"combat_fields_note": "each of these nine measures zero legacy occurrences over the preserved modules, and the only one that appears at all (attack) has a whole-word count of 0 with all twelve whole-file occurrences inside longer identifiers, so no committed column names this branch's outcome",
			"combat_fields_stored_as": "strings in the committed items table; reported verbatim and never read as a number",
			"id": "923",
			"id_keyed_by": "the committed id column, which the normalized package calls legacy_id, not the row's position in the committed array",
			"name": "Gorilla",
			"resolved_against": "the committed items rows whose type column is u; the three committed id spaces have zero overlap, so a building or the special cannot resolve",
			"resolved_id": 923,
			"type": "u",
		},
		"damage_derived": false,
		"derivation_performed": null,
		"derived_damage": null,
		"derived_destruction_count": null,
		"destruction": {
			"applied": false,
			"count": null,
			"count_derived": false,
			"count_refused_because": "no committed value names this branch's outcome: the nine committed combat columns have zero legacy consumers, and the preserved branch's only quantity is a subtraction of two client numbers (design D2)",
			"ledger_rule": "engine.py:223 pushes each destroyed row onto privateState['deadHeroes'] through push_dead_unit, which requires the row's team to be exactly 1 (engine.py:151) and the item's committed resurrectable to be greater than zero (engine.py:159-162); v1 reports both gates and credits nothing",
			"preserved_rule": "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers the CLIENT sends, and command.py:872 destroys that many rows through map_lose_item, so the count is client-dictated in full; the committed source labels the two numbers only 'A' and 'B'",
			"refused_by_code": "client_dictated_destruction",
			"refused_status": 409,
			"rejected_alternatives": {
				"derive_from_attack_minus_defense": "neither committed column is read by anything and attack is not even a whole-word occurrence in the preserved source",
				"destroy_every_eligible_row": "the client still chooses which unit and the server still cannot say how many; the count is still client-dictated in a different spelling, and an identity with no matching row would get a silent success",
				"destroy_one_row": "v0's resolve action reports destruction: 1, but that 1 is a property of combat_payload's own construction and the same v0 route destroyed two rows for A=3, B=1 at committed fixture step 7, so one is a fixture convenience rather than a rule",
			},
			"requested": null,
			"requested_is_none_because": "a request carrying the branch's destruction shape is refused before the identity is resolved, so a successful request never had one",
		},
		"document_unchanged": true,
		"gates": {
			"enforced": false,
			"enforced_note": "neither gate is a precondition here: the transaction destroys nothing, so there is no operation for a gate to stand in front of (design D3)",
			"gate_one_team": {
				"absence_reported_as": "null verdicts and an empty row list, because the gate has no input when no recorded row carries the identity",
				"any_row_would_pass": null,
				"every_row_would_pass": null,
				"preserved_test": "push_dead_unit requires the row's recorded slot 7 to be exactly 1 and returns False otherwise (engine.py:151)",
				"recorded_team": null,
				"row_count": 0,
				"row_present": false,
				"rows": [],
				"source": "maps[0].items[key][7] of every recorded row whose item id is the addressed committed identity",
			},
			"gate_two_resurrectable": {
				"absence_note": "an absent key is reported as absent and never as 0, because the preserved helper returns False on an absent key rather than reading one",
				"absent_is_read_as_zero": false,
				"committed_value": null,
				"committed_value_is": "the committed value verbatim; the committed encoding is the string, and it is compared as a number exactly as the preserved helper does, never by truthiness",
				"present": false,
				"preserved_test": "push_dead_unit reads the committed properties object, returns False when the key is absent, and otherwise compares int(resurrectable) > 0 (engine.py:155-162)",
				"source": "the committed unit row's properties object",
				"stored_as": "an embedded JSON string inside the committed items row, not a top-level column of it",
				"would_pass": null,
			},
		},
		"gates_enforced": false,
		"instant": 1791500000,
		"leaf_paths_changed": [],
		"ledger_covered_by": "the whole-document comparison, not a subset read: the dead-hero ledger is one key among every key compared",
		"ledger_credited": false,
		"preserved_branch_behaviour": {
			"absent_value": "command.py:866 and :874 dereference attacker_units and victim without a None check, so an omitted shape raises, the batch is discarded before the save is written (command.py:30,32), and the response is an HTTP 500; this is established by execution on fixture steps 2 and 4, not reasoned",
			"destruction": "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers the CLIENT sends, and command.py:872 destroys that many rows through map_lose_item, so the count is client-dictated in full; the committed source labels the two numbers only 'A' and 'B'",
			"ledger": "engine.py:223 pushes each destroyed row onto privateState['deadHeroes'] through push_dead_unit, which requires the row's team to be exactly 1 (engine.py:151) and the item's committed resurrectable to be greater than zero (engine.py:159-162); v1 reports both gates and credits nothing",
			"reached": "map_lose_item has exactly two call sites -- command.py:796 (end_quest) and command.py:872 (end_attack) -- so two branches reach one helper; godot-unit-behaviors counted push_dead_unit's callers and map_lose_item separately and called it three doors, and that archived line is not edited",
		},
		"proof": [
			[
				"identity_resolved_to_reported_row",
				true,
			],
			[
				"reported_gates_match_content_and_state",
				true,
			],
			[
				"no_leaf_path_changed",
				true,
			],
			[
				"whole_document_unchanged",
				true,
			],
			[
				"resources_unchanged",
				true,
			],
		],
		"protocol": "server-v1",
		"resources_after": {
			"cash": 5,
			"gold": 2000,
			"mana": 0,
			"oil": 2000,
			"steel": 2000,
			"wood": 2000,
			"xp": 4,
		},
		"result": "success",
		"rows_destroyed": 0,
		"stored_resources_compared": [
			"cash",
			"gold",
			"mana",
			"oil",
			"steel",
			"wood",
			"xp",
		],
		"team_asymmetry": {
			"consequence": "on a team-3 row the preserved server destroys the row and credits nothing to the dead-hero ledger",
			"ledger_test": "push_dead_unit requires slot 7 to be exactly 1 (engine.py:151) and returns False for every other team",
			"reconciled": false,
			"selector_test": "map_lose_item selects a row whose slot 7 is TRUTHY (engine.py:221), so any recorded team it does not read as 0 is eligible for destruction",
			"why_not_reconciled": "unknown: no committed row and no legacy line explains the difference, and every committed unit row in the corpus is on team 1, so the asymmetry is unexercisable rather than merely unexplained",
		},
	}


## ## The observed refusals of this route, each captured the same way.
## ##
## **Seven conditions, six codes**, and the collapse is asserted rather
## than left accidental: the first two conditions are both
## `unaddressable_row`, because "names no committed unit row" and
## "is a committed building id" are one rule seen twice -- the three
## committed id spaces have zero overlap, so a building cannot alias a
## unit. `building_id` is kept anyway, because a reader who saw only
## `unaddressable_row` would not learn that a building is refused by the
## *same* code rather than by a separate building check.
## ##
## The label is the **condition** rather than the code throughout, for
## the same reason the code sits beside it.
const OBSERVED_REFUSALS := {
		"a BUILDING id offered as a unit": {
			"body": {
				"code": "unaddressable_row",
				"detail": {
					"committed_table_is": "items, restricted to the rows whose type is u",
					"committed_unit_ids": [
						923,
						933,
						1001,
						1002,
						1003,
						1004,
						1005,
						1006,
						1007,
						1008,
						1009,
						1010,
						1011,
						1012,
						1013,
						1014,
						1015,
						1016,
						1017,
						1018,
						1019,
						1020,
						1021,
						1022,
						1023,
						1024,
						1025,
						1026,
						1027,
						1028,
						1029,
						1030,
						1031,
						1032,
						1033,
						1034,
						1035,
						1036,
						1037,
						1038,
						1039,
						1040,
						1041,
						1042,
						1043,
						1044,
						1045,
						1046,
						1047,
						1048,
						1049,
						1050,
						1051,
						1052,
						1053,
						1054,
						1055,
						1056,
						1057,
						1058,
						1059,
						1060,
						1061,
						1062,
						1063,
						1064,
						1065,
						1066,
						1067,
						1068,
						1069,
						1070,
						1071,
						1072,
						1073,
						1074,
						1075,
						1076,
						1077,
						1078,
						1079,
						1080,
						1081,
						1082,
						1083,
						1084,
						1085,
						1086,
						1087,
						1088,
						1089,
						1090,
						1091,
						1092,
						1093,
						1094,
						1095,
						1096,
						1097,
						1098,
						1099,
						1100,
						1101,
						1102,
						1103,
						1104,
						1105,
						1106,
						1107,
						1108,
						1109,
						1110,
						1111,
						1112,
						1113,
						1114,
						1115,
						1116,
						1117,
						1118,
						1119,
						1120,
						1121,
						1122,
						1123,
						1124,
						1125,
						1126,
						1127,
						1128,
						1129,
						1130,
						1131,
						1132,
						1133,
						1134,
						1135,
						1136,
						1137,
						1138,
						1139,
						1140,
						1141,
						1142,
						1143,
						1144,
						1145,
						1146,
						1147,
						1148,
						1149,
						1150,
						1151,
						1152,
						1153,
						1154,
						1155,
						1156,
						1157,
						1158,
						1159,
						1160,
						1161,
						1162,
						1163,
						1164,
						1165,
						1166,
						1167,
						1168,
						1169,
						1170,
						1171,
						1172,
						1173,
						1174,
						1175,
						1176,
						1177,
						1178,
						1179,
						1180,
						1181,
						1182,
						1183,
						1184,
						1185,
						1186,
						1187,
						1188,
						1189,
						1190,
						1191,
						1192,
						1193,
						1194,
						1195,
						1196,
						1197,
						1198,
						1199,
						1200,
						1201,
						1202,
						1203,
						1204,
						1205,
						1206,
						1207,
						1208,
						1209,
						1210,
						1211,
						1212,
						1213,
						1214,
						1215,
						1216,
						1217,
						1218,
						1219,
						1220,
						1221,
						1222,
						1223,
						1224,
						1225,
						1226,
						1227,
						1228,
						1229,
						1230,
						1231,
						1232,
						1233,
						1234,
						1235,
						1236,
						1237,
						1238,
						1239,
						1240,
						1241,
						1242,
						1243,
						1244,
						1245,
						1246,
						1247,
						1248,
						1249,
						1250,
						1251,
						1252,
						1253,
						1254,
						1255,
						1256,
						1257,
						1258,
						1259,
						1260,
						1261,
						1262,
						1263,
						1264,
						1265,
						1266,
						1267,
						1268,
						1269,
						1270,
						1271,
						1272,
						1273,
						1274,
						1275,
						1276,
						1277,
						1278,
						1279,
						1280,
						1281,
						1282,
						1283,
						1284,
						1285,
						1286,
						1287,
						1288,
						1289,
						1290,
						1291,
						1292,
						1293,
						1294,
						1295,
						1296,
						1297,
						1298,
						1299,
						1300,
						1301,
						1302,
						1303,
						1304,
						1305,
						1306,
						1307,
						1308,
						1309,
						1310,
						1311,
						1312,
						1313,
						1314,
						1315,
						1316,
						1317,
						1318,
						1321,
						1322,
						1319,
						1320,
						1323,
						1324,
						1325,
						1326,
						1327,
						1328,
						1329,
						1330,
						1331,
						1332,
						1333,
						1334,
						1335,
						1336,
						1341,
						1342,
						1337,
						1338,
						1343,
						1344,
						1339,
						1340,
						1345,
						1346,
						1347,
						1348,
						1349,
						1350,
						1351,
						1352,
						1353,
						1354,
						1355,
						1356,
						1357,
						1358,
						1362,
						1363,
						1360,
						1361,
						1364,
						1365,
						1366,
						1367,
						1368,
						1369,
						1370,
						1371,
						1372,
						1373,
						1374,
						1377,
						1378,
						1375,
						1376,
						1379,
						1380,
						1381,
						1385,
						1386,
						1382,
						1387,
						1383,
						1384,
						1388,
						1389,
						1390,
						1391,
						1392,
						1393,
						1394,
						1395,
						1400,
						1401,
						1402,
						1403,
						1404,
						1396,
						1397,
						1398,
						1399,
						1408,
						1409,
						1406,
						1407,
						1410,
						1411,
						1412,
						1413,
						1414,
						1415,
						1416,
						1417,
						1418,
						1419,
						1420,
						1421,
						1422,
						1423,
						1424,
						1425,
						1428,
						1429,
						1430,
						1431,
					],
					"committed_unit_rows": 429,
					"non_positive_is_not_clamped": true,
					"requested_unit_id": 22,
					"resolved_row": null,
					"rolled_back": false,
					"why_not_clamped": "the preserved branch never indexes the committed table, so zero and every negative id name no row at all rather than aliasing a position; a clamp would be a second addressing rule",
				},
				"message": "unit id 22 names no row of the committed unit table, which holds 429 rows; the three committed id spaces have zero overlap, so a building or the one special cannot resolve here either",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "unaddressable_row",
			"message": "unit id 22 names no row of the committed unit table, which holds 429 rows; the three committed id spaces have zero overlap, so a building or the one special cannot resolve here either",
			"status": 409,
		},
		"a client-sent resource delta": {
			"body": {
				"code": "client_supplied_delta",
				"detail": {
					"delta_fields": [
						"damage",
					],
					"refused_field": "damage",
				},
				"message": "a v1 request carries intent only; the field 'damage' dictates an outcome and is refused rather than clamped, coerced, or ignored",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "client_supplied_delta",
			"message": "a v1 request carries intent only; the field 'damage' dictates an outcome and is refused rather than clamped, coerced, or ignored",
			"status": 400,
		},
		"a field the intent schema does not define": {
			"body": {
				"code": "unknown_request_field",
				"detail": {
					"allowed_fields": [
						"player_id",
						"unit_id",
					],
					"unknown_fields": [
						"honor",
					],
				},
				"message": "the request carried the field 'honor', which the 'combat' intent schema does not define",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "unknown_request_field",
			"message": "the request carried the field 'honor', which the 'combat' intent schema does not define",
			"status": 400,
		},
		"a non-canonical identity form": {
			"body": {
				"code": "malformed_request",
				"detail": {
					"addressing_field": "unit_id",
					"received": "str",
				},
				"message": "unit_id must be an integer",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "malformed_request",
			"message": "unit_id must be an integer",
			"status": 400,
		},
		"a player with no save document": {
			"body": {
				"code": "unknown_player",
				"detail": {
					"player_id": "nope",
				},
				"message": "no save document for player 'nope'",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "unknown_player",
			"message": "no save document for player 'nope'",
			"status": 404,
		},
		"a request carrying the branch's own wire shape": {
			"body": {
				"code": "client_dictated_destruction",
				"detail": {
					"applied": false,
					"count_derived": false,
					"ledger_credited": false,
					"player_id": "00000000-0000-4000-8000-000000000001",
					"preserved_rule": "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers the CLIENT sends, and command.py:872 destroys that many rows through map_lose_item, so the count is client-dictated in full; the committed source labels the two numbers only 'A' and 'B'",
					"requested_destruction": [
						[
							0,
							0,
							1,
							0,
						],
					],
					"requested_destruction_is": "the preserved branch's own wire shape, carried verbatim and neither counted, bounded, nor converted into any other figure",
					"requested_unit_id": 1001,
					"rollback_note": "there is no write in this module, so no rollback was started; the document is byte-identical because nothing was ever written",
					"rolled_back": false,
					"rows_destroyed": 0,
				},
				"message": "unit 1001 was resolved, but the request also carried a destruction figure, so nothing is destroyed: the preserved branch's count is max(0, A - B) over two numbers the client sends (command.py:868) and no committed value names its outcome, so v1 applies no count and derives none",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "client_dictated_destruction",
			"message": "unit 1001 was resolved, but the request also carried a destruction figure, so nothing is destroyed: the preserved branch's count is max(0, A - B) over two numbers the client sends (command.py:868) and no committed value names its outcome, so v1 applies no count and derives none",
			"status": 409,
		},
		"identity naming no committed unit row": {
			"body": {
				"code": "unaddressable_row",
				"detail": {
					"committed_table_is": "items, restricted to the rows whose type is u",
					"committed_unit_ids": [
						923,
						933,
						1001,
						1002,
						1003,
						1004,
						1005,
						1006,
						1007,
						1008,
						1009,
						1010,
						1011,
						1012,
						1013,
						1014,
						1015,
						1016,
						1017,
						1018,
						1019,
						1020,
						1021,
						1022,
						1023,
						1024,
						1025,
						1026,
						1027,
						1028,
						1029,
						1030,
						1031,
						1032,
						1033,
						1034,
						1035,
						1036,
						1037,
						1038,
						1039,
						1040,
						1041,
						1042,
						1043,
						1044,
						1045,
						1046,
						1047,
						1048,
						1049,
						1050,
						1051,
						1052,
						1053,
						1054,
						1055,
						1056,
						1057,
						1058,
						1059,
						1060,
						1061,
						1062,
						1063,
						1064,
						1065,
						1066,
						1067,
						1068,
						1069,
						1070,
						1071,
						1072,
						1073,
						1074,
						1075,
						1076,
						1077,
						1078,
						1079,
						1080,
						1081,
						1082,
						1083,
						1084,
						1085,
						1086,
						1087,
						1088,
						1089,
						1090,
						1091,
						1092,
						1093,
						1094,
						1095,
						1096,
						1097,
						1098,
						1099,
						1100,
						1101,
						1102,
						1103,
						1104,
						1105,
						1106,
						1107,
						1108,
						1109,
						1110,
						1111,
						1112,
						1113,
						1114,
						1115,
						1116,
						1117,
						1118,
						1119,
						1120,
						1121,
						1122,
						1123,
						1124,
						1125,
						1126,
						1127,
						1128,
						1129,
						1130,
						1131,
						1132,
						1133,
						1134,
						1135,
						1136,
						1137,
						1138,
						1139,
						1140,
						1141,
						1142,
						1143,
						1144,
						1145,
						1146,
						1147,
						1148,
						1149,
						1150,
						1151,
						1152,
						1153,
						1154,
						1155,
						1156,
						1157,
						1158,
						1159,
						1160,
						1161,
						1162,
						1163,
						1164,
						1165,
						1166,
						1167,
						1168,
						1169,
						1170,
						1171,
						1172,
						1173,
						1174,
						1175,
						1176,
						1177,
						1178,
						1179,
						1180,
						1181,
						1182,
						1183,
						1184,
						1185,
						1186,
						1187,
						1188,
						1189,
						1190,
						1191,
						1192,
						1193,
						1194,
						1195,
						1196,
						1197,
						1198,
						1199,
						1200,
						1201,
						1202,
						1203,
						1204,
						1205,
						1206,
						1207,
						1208,
						1209,
						1210,
						1211,
						1212,
						1213,
						1214,
						1215,
						1216,
						1217,
						1218,
						1219,
						1220,
						1221,
						1222,
						1223,
						1224,
						1225,
						1226,
						1227,
						1228,
						1229,
						1230,
						1231,
						1232,
						1233,
						1234,
						1235,
						1236,
						1237,
						1238,
						1239,
						1240,
						1241,
						1242,
						1243,
						1244,
						1245,
						1246,
						1247,
						1248,
						1249,
						1250,
						1251,
						1252,
						1253,
						1254,
						1255,
						1256,
						1257,
						1258,
						1259,
						1260,
						1261,
						1262,
						1263,
						1264,
						1265,
						1266,
						1267,
						1268,
						1269,
						1270,
						1271,
						1272,
						1273,
						1274,
						1275,
						1276,
						1277,
						1278,
						1279,
						1280,
						1281,
						1282,
						1283,
						1284,
						1285,
						1286,
						1287,
						1288,
						1289,
						1290,
						1291,
						1292,
						1293,
						1294,
						1295,
						1296,
						1297,
						1298,
						1299,
						1300,
						1301,
						1302,
						1303,
						1304,
						1305,
						1306,
						1307,
						1308,
						1309,
						1310,
						1311,
						1312,
						1313,
						1314,
						1315,
						1316,
						1317,
						1318,
						1321,
						1322,
						1319,
						1320,
						1323,
						1324,
						1325,
						1326,
						1327,
						1328,
						1329,
						1330,
						1331,
						1332,
						1333,
						1334,
						1335,
						1336,
						1341,
						1342,
						1337,
						1338,
						1343,
						1344,
						1339,
						1340,
						1345,
						1346,
						1347,
						1348,
						1349,
						1350,
						1351,
						1352,
						1353,
						1354,
						1355,
						1356,
						1357,
						1358,
						1362,
						1363,
						1360,
						1361,
						1364,
						1365,
						1366,
						1367,
						1368,
						1369,
						1370,
						1371,
						1372,
						1373,
						1374,
						1377,
						1378,
						1375,
						1376,
						1379,
						1380,
						1381,
						1385,
						1386,
						1382,
						1387,
						1383,
						1384,
						1388,
						1389,
						1390,
						1391,
						1392,
						1393,
						1394,
						1395,
						1400,
						1401,
						1402,
						1403,
						1404,
						1396,
						1397,
						1398,
						1399,
						1408,
						1409,
						1406,
						1407,
						1410,
						1411,
						1412,
						1413,
						1414,
						1415,
						1416,
						1417,
						1418,
						1419,
						1420,
						1421,
						1422,
						1423,
						1424,
						1425,
						1428,
						1429,
						1430,
						1431,
					],
					"committed_unit_rows": 429,
					"non_positive_is_not_clamped": true,
					"requested_unit_id": 0,
					"resolved_row": null,
					"rolled_back": false,
					"why_not_clamped": "the preserved branch never indexes the committed table, so zero and every negative id name no row at all rather than aliasing a position; a clamp would be a second addressing rule",
				},
				"message": "unit id 0 names no row of the committed unit table, which holds 429 rows; the three committed id spaces have zero overlap, so a building or the one special cannot resolve here either",
				"protocol": "server-v1",
				"result": "refused",
			},
			"code": "unaddressable_row",
			"message": "unit id 0 names no row of the committed unit table, which holds 429 rows; the three committed id spaces have zero overlap, so a building or the one special cannot resolve here either",
			"status": 409,
		},
	}
# --- the scenario --------------------------------------------------------------


func run_scenario() -> void:
	if scenario == "live":
		await _check_live()
		_write_report()
		return
	_check_observed_success_parses()
	_check_observed_absent_flag_parses()
	_check_observed_refusals_parse()
	_check_fail_closed()
	_check_committed_units_are_re_derived()
	_check_intent_body()
	_check_no_client_arithmetic()
	_check_no_line_compares_two_reported_values()
	_check_absent_derivation_helpers()
	_check_domain_inventory()
	_check_domain_reserved_stems()
	_check_python_name_scan_finds_planted_defs()
	_check_combat_codes_live_in_the_combat_modules()
	await _check_facade_registration()
	_check_return_type_widening()
	_check_unsupported_intent_left_the_table()
	_check_transport_token_placement()
	_check_boundary_ownership()
	_check_no_unconverted_format_arguments()
	_check_no_chained_format_operations()
	_check_balance_holders_resolve_over_the_committed_corpus()
	_write_report()


# --- the typed result ----------------------------------------------------------


## The observed answer parses into every field, with the deterministic values
## checked exactly.
##
## The payload's **top-level key set is pinned whole** before anything else, and
## so is the set of keys the parser does **not** read. A fixture trimmed to the
## fields under test would fail both, and that is the whole defence against a
## success fixture composed from the parser's expectations instead of captured
## from the service: the answer carries nine long prose sentences, a ledger
## sentence and a team-asymmetry block that no check reads, and all of them are
## required to be present.
const OBSERVED_SUCCESS_KEYS := [
	"action", "combat", "committed", "damage_derived", "derivation_performed",
	"derived_damage", "derived_destruction_count", "destruction",
	"document_unchanged", "gates", "gates_enforced", "instant",
	"leaf_paths_changed", "ledger_covered_by", "ledger_credited",
	"preserved_branch_behaviour", "proof", "protocol", "resources_after",
	"result", "rows_destroyed", "stored_resources_compared", "team_asymmetry",
]

## The one top-level key the parser reads **no** field of. It is in the observed
## answer because v1 emits it, and it is listed here so the report can say how
## much of the answer this client ignores rather than implying it reads the whole
## document.
const OBSERVED_UNREAD_KEYS := ["ledger_covered_by"]

## The twenty-two top-level keys the parser reads a field of, pinned here and
## cross-checked against the module's own quoted literals in the check below. The
## pin is what replaces the tautological `_read_keys(payload)` subtraction this
## check used to make.
const PARSER_READ_KEYS := [
	"action", "combat", "committed", "damage_derived", "derivation_performed",
	"derived_damage", "derived_destruction_count", "destruction",
	"document_unchanged", "gates", "gates_enforced", "instant",
	"leaf_paths_changed", "ledger_credited", "preserved_branch_behaviour",
	"proof", "protocol", "resources_after", "result", "rows_destroyed",
	"stored_resources_compared", "team_asymmetry",
]

## The observed unit 1001's committed row, read out of the fixture and checked
## against the committed mirror rather than against itself.
const OBSERVED_UNIT_ID := 1001
const OBSERVED_UNIT_NAME := "Worker I"
const OBSERVED_ABSENT_UNIT_ID := 923
const OBSERVED_ABSENT_UNIT_NAME := "Gorilla"
const OBSERVED_INSTANT := 1791500000

## The committed **building** id the captured building refusal addressed: 22 is
## `Turret I` in the committed buildings package, present in no unit row. It is
## what makes the "the three committed id spaces have zero overlap" claim
## executable rather than asserted.
const OBSERVED_BUILDING_ID := 22

## The one reported combat column the committed mirror stores as a **string**.
## Measured: the other eight are JSON numbers on all 429 rows, and this one is
## prose (`""` on unit 923, `"ft_ground"` on unit 1001). It is named here rather
## than left implicit because the claim "the mirror stores numbers and the served
## table stores strings" is false for this column in **both** encodings.
const STRING_COMBAT_COLUMN := "best_against"


func _check_observed_success_parses() -> void:
	var payload: Dictionary = OBSERVED_SUCCESS.duplicate(true)
	check_eq(_sorted_keys(payload), OBSERVED_SUCCESS_KEYS,
		"the observed success carries exactly the twenty-three top-level keys v1"
		+ " emitted, so it was not trimmed to the parser's needs")
	check_eq(_difference(OBSERVED_SUCCESS_KEYS, PARSER_READ_KEYS),
		OBSERVED_UNREAD_KEYS,
		"exactly one of them is a key the parser reads no field of")
	# **Not** `_read_keys(payload)`. The first version of this check subtracted
	# the fixture's own keys from the fixture's own key list, which is empty by
	# construction and could never fail -- a tautology wearing the shape of a
	# guard. The read set is pinned here instead, and the next three checks are
	# what stop the pin from drifting away from the code it describes.
	var module_projection := _comment_free(_project_source(RESULT_SCRIPT))
	var unbacked: Array = []
	for name in PARSER_READ_KEYS:
		if not module_projection.contains("\"%s\"" % str(name)):
			unbacked.append(str(name))
	check_eq(unbacked, [],
		"and every pinned read key is a quoted literal in the module, so the pin"
		+ " cannot drift from the parser without failing here")
	check_eq(_difference(PARSER_READ_KEYS, OBSERVED_SUCCESS_KEYS), [],
		"the pin names no key the observed answer lacks")
	check_eq(_difference(OBSERVED_UNREAD_KEYS, PARSER_READ_KEYS), OBSERVED_UNREAD_KEYS,
		"and the one unread key really is absent from the read set, which is what"
		+ " 'unread' means here rather than a name appearing in both lists")

	var parsed: Variant = ServerV1Combat.parse_combat_authority(
		payload.duplicate(true))
	if not (parsed is ServerV1Combat.CombatAuthorityResult):
		fail("an observed v1 combat answer parses into the typed result")
		return
	var typed: ServerV1Combat.CombatAuthorityResult = parsed
	check(typed.ok, "the observed answer is a success")
	check_eq(typed.error_code, "", "and carries no refusal code")
	check_eq(typed.protocol, ServerV1Combat.PROTOCOL,
		"and is stamped with v1's protocol")
	check_eq(typed.action, ServerV1Combat.ACTION, "and names the action that ran")
	check_eq(typed.instant, OBSERVED_INSTANT, "and carries the recorded instant")

	check(typed.combat != null, "the addressing block is present")
	if typed.combat != null:
		check_eq(typed.combat.unit_id, OBSERVED_UNIT_ID,
			"and reports the identity the client named")
		check_eq(typed.combat.identity_field, "unit_id",
			"and the field it was named in")
		check_eq(typed.combat.identity_resolved_against,
			str(payload["combat"]["identity_resolved_against"]),
			"and the committed rows it was resolved against")
		# The one relation this client *does* draw from the addressing pair, and
		# it is the client's own fact rather than the server's: both spellings of
		# the same id. Nothing is concluded about whether the resolution was
		# correct -- that is the first of v1's own five proof checks, reported
		# rather than re-derived here.
		check_eq(typed.combat.unit_id, int(payload["combat"]["unit_id"]),
			"the reported identity is the one the payload carried")

	check_eq(typed.committed_id, str(OBSERVED_UNIT_ID),
		"the committed row is reported by its committed id column, as a string")
	check_eq(typed.committed_name, OBSERVED_UNIT_NAME,
		"and by its committed name")
	check_eq(typed.committed_type, "u", "and by its committed type column")
	check_eq(typed.resolved_id, OBSERVED_UNIT_ID,
		"and carries the resolved id as a whole number")

	# The nine committed columns, checked against the committed mirror and never
	# read as numbers. `_whole_number` exists because Godot decodes every JSON
	# number as a float; this module applies it to `resources_after` and to the
	# ids, and NOT here, because here the committed encoding **is** the string.
	check_eq(_sorted_set(_string_list(typed.combat_fields.keys())),
		_sorted_set(ServerV1Combat.REPORTED_COMBAT_FIELDS),
		"the nine committed combat columns are carried, and no tenth")
	var row := _committed_unit(OBSERVED_UNIT_ID)
	check(row.size() > 0, "the committed mirror holds the addressed unit row")
	var mismatched: Array = []
	for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
		var carried: Variant = typed.combat_fields.get(str(name), null)
		if not (carried is String):
			mismatched.append("%s is not a string" % str(name))
			continue
		if not row.has(str(name)):
			mismatched.append("%s is not a committed column" % str(name))
			continue
		# The mirror stores these nine as JSON **numbers** (every JSON number
		# decodes here as a float, so `6` arrives as `6.0`), while the served
		# items table stores them as **strings**. The claim is therefore about
		# the decimal rendering, not about `str(6.0) == "6.0"`.
		var committed_value: Variant = row[str(name)]
		var rendered: String = str(committed_value)
		if committed_value is float or committed_value is int:
			rendered = str(int(committed_value))
		if str(carried) != rendered:
			mismatched.append("%s carried %s, committed %s"
				% [str(name), str(carried), rendered])
	check_eq(mismatched, [],
		"every one of the nine is the committed value verbatim, as the string the"
		+ " committed table stores it as")

	check(typed.team_gate != null, "the team gate is present")
	if typed.team_gate != null:
		check(typed.team_gate.row_present == false,
			"and reports no recorded row carrying this identity")
		check_eq(typed.team_gate.row_count, 0, "with a row count of zero")
		check_eq(typed.team_gate.rows, [], "and an empty row list, kept whole")
		check(typed.team_gate.recorded_team == null,
			"and a null recorded team, because there is no row to read one from")
		check(typed.team_gate.every_row_would_pass == null,
			"and a null every-row verdict, never a false one")
		check(typed.team_gate.any_row_would_pass == null,
			"and a null any-row verdict")
	check(typed.resurrectable_gate != null, "the resurrectable gate is present")
	if typed.resurrectable_gate != null:
		check(typed.resurrectable_gate.present,
			"and reports the committed key as present")
		check_eq(typed.resurrectable_gate.committed_value, "1",
			"and its committed value verbatim, as the committed string")
		check_eq(typed.resurrectable_gate.would_pass, true,
			"and the verdict the preserved helper would reach")
		check(typed.resurrectable_gate.absent_is_read_as_zero == false,
			"and that the key is not read as zero")

	check(typed.gates_enforced == false,
		"the observed answer enforces no gate, and the parser requires that")
	check(typed.team_asymmetry.size() >= 4,
		"the team-asymmetry report is carried whole, as prose")
	check(typed.destruction.size() > 0, "the destruction report is carried")
	check_eq(str(typed.destruction["applied"]), "false",
		"and reports that it applied nothing")
	check_eq(typed.rows_destroyed, 0,
		"and reports zero destroyed rows, unconditionally")
	check_eq(typed.ledger_credited, false,
		"and credits no dead-hero ledger entry")
	check(typed.derived_damage == null,
		"and reports derived damage as an explicit null")
	check(typed.derived_destruction_count == null,
		"and a derived destruction count as an explicit null")
	check(typed.derivation_performed == null,
		"and names no derivation at all, as an explicit null")
	check(typed.damage_derived == false, "and reports deriving no damage")
	check_eq(typed.leaf_paths_changed, [], "and changed no stored leaf path")
	check(typed.document_unchanged,
		"and reports the whole document byte-identical")

	check(typed.resources_after != null, "the stored balances are present")
	if typed.resources_after != null:
		var wrong: Array = []
		for name in ServerV1Combat.STORED_RESOURCE_NAMES:
			if int(typed.resources_after.get(str(name))) != int(
					OBSERVED_BALANCES[str(name)]):
				wrong.append(str(name))
		check_eq(wrong, [],
			"all seven stored balances are the corpus's, unchanged by this route")
	check_eq(_sorted_set(_string_list(typed.stored_resources_compared)),
		_sorted_set(ServerV1Combat.STORED_RESOURCE_NAMES),
		"and the answer names exactly the seven it compared")

	var proof_names: Array = []
	for entry in typed.proof:
		proof_names.append(str((entry as Array)[0]))
		check_eq((entry as Array)[1], true,
			"the %s check holds" % str((entry as Array)[0]))
	check_eq(proof_names, ServerV1Combat.PROOF_CHECKS,
		"the five proof checks arrive in the order v1 emits them, and the order is"
		+ " the claim: the leaf census precedes the whole-document comparison")

	check(typed.preserved_branch_behaviour.size() >= 4,
		"the preserved-branch behaviour table is carried whole")
	var missing_behaviour: Array = []
	for key in ServerV1Combat.BEHAVIOUR_KEYS:
		if not (typed.preserved_branch_behaviour.get(str(key), null) is String):
			missing_behaviour.append(str(key))
	check_eq(missing_behaviour, [],
		"and all five of its required members are strings")


## The absent committed key, as a **second success** rather than as a note.
##
## The two payloads are compared leaf by leaf and must differ in exactly three
## places, all of them inside `gate_two_resurrectable`. A parser that collapsed
## "absent" into "0" would make these two answers identical, and that collapse is
## the one rule this fixture exists to keep impossible.
func _check_observed_absent_flag_parses() -> void:
	var absent: Variant = ServerV1Combat.parse_combat_authority(
		OBSERVED_ABSENT_FLAG_SUCCESS.duplicate(true))
	var present: Variant = ServerV1Combat.parse_combat_authority(
		OBSERVED_SUCCESS.duplicate(true))
	if not (absent is ServerV1Combat.CombatAuthorityResult):
		fail("the absent-key observed answer parses into the typed result")
		return
	if not (present is ServerV1Combat.CombatAuthorityResult):
		fail("the present-key observed answer parses into the typed result")
		return
	var typed: ServerV1Combat.CombatAuthorityResult = absent
	check(typed.ok, "the absent-key answer is a success, not a refusal")
	check_eq(typed.committed_id, str(OBSERVED_ABSENT_UNIT_ID),
		"and names the committed row whose properties object has no key")
	check_eq(typed.committed_name, OBSERVED_ABSENT_UNIT_NAME,
		"by its committed name")
	check(typed.resurrectable_gate != null, "its resurrectable gate is present")
	if typed.resurrectable_gate == null:
		return
	check(typed.resurrectable_gate.present == false,
		"and reports the committed key as ABSENT")
	check(typed.resurrectable_gate.committed_value == null,
		"with a null committed value rather than a zero")
	check(typed.resurrectable_gate.would_pass == null,
		"and a null verdict rather than a false one")
	check(typed.resurrectable_gate.absent_is_read_as_zero == false,
		"and states that the key is not read as zero")

	# The leaf-level comparison. Everything except three leaves must be identical
	# inside the gates block, and the three leaves must be exactly these.
	var before_leaves := {}
	_collect_leaves(OBSERVED_ABSENT_FLAG_SUCCESS["gates"], "gates", before_leaves)
	var after_leaves := {}
	_collect_leaves(OBSERVED_SUCCESS["gates"], "gates", after_leaves)
	var differing := _leaf_difference(before_leaves, after_leaves)
	check_eq(differing, [
		"gates/gate_two_resurrectable/committed_value",
		"gates/gate_two_resurrectable/present",
		"gates/gate_two_resurrectable/would_pass",
	], "the two observed answers differ in exactly three leaves of the gates"
	+ " block, and nowhere else in it")
	var typed_leaves := {}
	_collect_leaves(OBSERVED_ABSENT_FLAG_SUCCESS, "", typed_leaves)
	var typed_present := {}
	_collect_leaves(OBSERVED_SUCCESS, "", typed_present)
	check(_leaf_difference(typed_leaves, typed_present).size() > 3,
		"the two observed identities also differ outside the gates block, which"
		+ " is why only the gates subtree is compared leaf by leaf")


## Every observed refusal parses as a refusal carrying v1's own code, message and
## detail, and **no** success field is populated: there is no partial payload.
func _check_observed_refusals_parse() -> void:
	var conditions := _sorted_keys(OBSERVED_REFUSALS)
	check_eq(conditions.size(), 7,
		"seven observed refusal conditions are carried")
	for condition in conditions:
		var entry: Dictionary = OBSERVED_REFUSALS[condition]
		var parsed: Variant = ServerV1Combat.parse_combat_authority(
			(entry["body"] as Dictionary).duplicate(true))
		if not (parsed is ServerV1Combat.CombatAuthorityResult):
			fail("%s parses into the typed result" % str(condition))
			continue
		var typed: ServerV1Combat.CombatAuthorityResult = parsed
		check(not typed.ok, "%s is refused, not accepted" % str(condition))
		check_eq(typed.error_code, str(entry["code"]),
			"%s carries v1's own code" % str(condition))
		check_eq(typed.error_message, str(entry["message"]),
			"%s carries the message the deciding site wrote" % str(condition))
		check_eq(typed.error_detail, (entry["body"] as Dictionary)["detail"],
			"%s carries its detail verbatim" % str(condition))
		check_eq(typed.protocol, ServerV1Combat.PROTOCOL,
			"%s is still stamped with v1's protocol" % str(condition))
		# No partial payload. Every one of these is a success field, and a
		# refusal that populated any of them would be a payload a caller could
		# read as a combat answer.
		check(typed.combat == null, "%s carries no addressing block" % str(condition))
		check(typed.team_gate == null, "%s carries no team gate" % str(condition))
		check(typed.resurrectable_gate == null,
			"%s carries no resurrectable gate" % str(condition))
		check(typed.resources_after == null,
			"%s carries no balance set" % str(condition))
		check_eq(typed.committed_id, "", "%s carries no committed id" % str(condition))
		check_eq(typed.committed_name, "",
			"%s carries no committed name" % str(condition))
		check_eq(typed.resolved_id, -1, "%s carries no resolved id" % str(condition))
		check_eq(typed.instant, 0, "%s carries no instant" % str(condition))
		check_eq(typed.action, "", "%s names no action" % str(condition))
		check_eq(typed.rows_destroyed, 0,
			"%s carries no destruction figure at all" % str(condition))
		check_eq(typed.combat_fields, {}, "%s carries no combat columns" % str(condition))
		check_eq(typed.proof, [], "%s carries no proof" % str(condition))
		check_eq(typed.leaf_paths_changed, [],
			"%s carries no leaf census" % str(condition))
		check_eq(typed.stored_resources_compared, [],
			"%s names no compared resource" % str(condition))
		check_eq(typed.team_asymmetry, {},
			"%s carries no asymmetry report" % str(condition))
		check_eq(typed.destruction, {},
			"%s carries no destruction report" % str(condition))
		check_eq(typed.preserved_branch_behaviour, {},
			"%s carries no preserved-behaviour table" % str(condition))
		check(typed.document_unchanged == false,
			"%s asserts nothing about the document" % str(condition))
		check(typed.ledger_credited == false,
			"%s credits nothing" % str(condition))

	# The branch's own wire shape, refused with no row and no ledger key. This is
	# the request a v0 client would send, and it is not reachable through this
	# facade: `_combat_intent_body` forwards two fields. It is carried as an
	# observed answer because the refusal is the finding, and it is asserted here
	# so the fixture cannot be mistaken for one the client can produce.
	var shape: Dictionary = OBSERVED_REFUSALS[
		"a request carrying the branch's own wire shape"]["body"]
	var detail: Dictionary = shape["detail"]
	check_eq(detail["requested_destruction"], [[0, 0, 1, 0]],
		"the branch's destruction shape is carried verbatim in the refusal")
	check_eq(detail["rows_destroyed"], 0,
		"and the refusal destroys no row")
	check_eq(detail["count_derived"], false,
		"and derives no count from it")
	check_eq(detail["ledger_credited"], false,
		"and credits no dead-hero ledger key")
	check_eq(detail["applied"], false, "and applied nothing")
	check_eq(detail["rolled_back"], false,
		"and started no rollback, because there is no write in this module")


# --- fail closed ---------------------------------------------------------------


## The number of malformed shapes `_check_fail_closed` walks. Declared here so
## the report states it rather than the report merely implying it, and pinned
## inside the function so the two cannot disagree.
const FAIL_CLOSED_CASE_COUNT := 110


## Every malformed shape the parser must refuse, built from the observed answer
## rather than from a hand-written payload, so each case is a **real** v1 answer
## with one thing broken. The case count is pinned, so dropping one is a failure
## rather than a silent reduction in coverage.
func _fail_closed_cases() -> Array:
	var dropped: Array = [
		["result"], ["protocol"], ["action"], ["instant"], ["combat"],
		["combat", "unit_id"], ["combat", "identity_field"],
		["combat", "identity_resolved_against"], ["committed"],
		["committed", "id"], ["committed", "name"], ["committed", "type"],
		["committed", "resolved_id"], ["committed", "combat_fields"],
		["committed", "combat_fields", "attack"], ["gates"],
		["gates", "enforced"], ["gates", "gate_one_team"],
		["gates", "gate_one_team", "row_present"],
		["gates", "gate_one_team", "row_count"],
		["gates", "gate_one_team", "rows"],
		["gates", "gate_two_resurrectable"],
		["gates", "gate_two_resurrectable", "present"],
		["gates", "gate_two_resurrectable", "committed_value"],
		["gates", "gate_two_resurrectable", "would_pass"],
		["gates", "gate_two_resurrectable", "absent_is_read_as_zero"],
		["resources_after"], ["resources_after", "gold"],
		["stored_resources_compared"], ["proof"], ["proof", 0],
		["proof", 0, 0], ["proof", 0, 1], ["leaf_paths_changed"],
		["document_unchanged"], ["derived_damage"],
		["derived_destruction_count"], ["derivation_performed"],
		["rows_destroyed"], ["preserved_branch_behaviour"],
		["preserved_branch_behaviour", "ledger"], ["team_asymmetry"],
		["destruction"], ["destruction", "applied"],
	]
	var cases: Array = []
	for path in dropped:
		cases.append({"label": "without %s" % "/".join(_string_list(path)),
			"payload": _dropped(OBSERVED_SUCCESS, path)})

	var eight_fields: Dictionary = {}
	for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
		if str(name) == "syringes":
			continue
		eight_fields[str(name)] = "1"
	var ten_fields: Dictionary = eight_fields.duplicate(true)
	ten_fields["syringes"] = "1"
	ten_fields["reach"] = "1"
	var six_balances: Dictionary = {}
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		if str(name) == "mana":
			continue
		six_balances[str(name)] = 0
	var eight_balances: Dictionary = six_balances.duplicate(true)
	eight_balances["mana"] = 0
	eight_balances["energy"] = 50
	var reversed_names: Array = []
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		reversed_names.push_front(str(name))
	var short_proof: Array = []
	for entry in (OBSERVED_SUCCESS["proof"] as Array):
		short_proof.append((entry as Array).duplicate())
	short_proof.resize(4)
	var swapped_proof: Array = []
	for entry in (OBSERVED_SUCCESS["proof"] as Array):
		swapped_proof.append((entry as Array).duplicate())
	var swap: Array = swapped_proof[0]
	swapped_proof[0] = swapped_proof[1]
	swapped_proof[1] = swap

	var put: Array = [
		[["protocol"], "server-v0", "a v0 protocol stamp"],
		[["action"], "magic", "another action's name"],
		[["instant"], 7.5, "a fractional instant"],
		[["instant"], "1791500000", "an instant as a string"],
		[["combat"], "unit 1001", "an addressing block that is not an object"],
		[["combat", "unit_id"], 1001.5, "a fractional identity"],
		[["committed", "resolved_id"], "1001", "a resolved id as a string"],
		[["committed", "combat_fields", "attack"], 6,
			"a committed column reported as a number"],
		[["committed", "combat_fields", "attack"], null,
			"a committed column reported as null"],
		[["committed", "combat_fields"], eight_fields,
			"only eight of the nine committed columns"],
		[["committed", "combat_fields"], ten_fields,
			"a tenth committed column"],
		[["gates", "enforced"], true, "an answer claiming an enforced gate"],
		[["gates_enforced"], true,
			"an answer whose own gates block it contradicts"],
		[["gates", "gate_one_team", "rows"], "none",
			"a row list that is not a list"],
		[["gates", "gate_one_team", "rows"], ["row"],
			"a row list on a gate that reports no row"],
		[["gates", "gate_one_team", "every_row_would_pass"], false,
			"a false every-row verdict on an absent row"],
		[["gates", "gate_one_team", "any_row_would_pass"], true,
			"a true any-row verdict on an absent row"],
		[["gates", "gate_one_team", "recorded_team"], 1,
			"a recorded team on an absent row"],
		[["gates", "gate_two_resurrectable"], "absent",
			"a flag block that is not an object"],
		[["gates", "gate_two_resurrectable", "present"], false,
			"an absent key still carrying its committed value"],
		[["gates", "gate_two_resurrectable", "committed_value"], 0,
			"an absent key read as a committed zero"],
		[["gates", "gate_two_resurrectable", "committed_value"], null,
			"a present key carrying a null committed value"],
		[["gates", "gate_two_resurrectable", "would_pass"], "yes",
			"a verdict that is not a boolean"],
		[["gates", "gate_two_resurrectable", "absent_is_read_as_zero"], true,
			"an answer reading the absent key as zero"],
		[["resources_after"], "gold 2000", "balances that are not an object"],
		[["resources_after"], six_balances, "only six stored balances"],
		[["resources_after", "gold"], 2000.5, "a fractional stored balance"],
		[["resources_after", "gold"], "2000", "a stored balance as a string"],
		[["stored_resources_compared"], eight_balances.keys() as Array
			if false else _string_list(eight_balances.keys()),
			"an eighth compared resource the client cannot read"],
		[["stored_resources_compared"], reversed_names,
			"the seven compared names out of order"],
		[["stored_resources_compared"], ["gold", 1],
			"a compared name that is not a string"],
		[["proof"], "all five checks hold", "a proof that is not a list"],
		[["proof"], short_proof, "a proof of four checks"],
		[["proof"], swapped_proof, "a proof whose first two checks are swapped"],
		[["proof", 0], "identity_resolved_to_reported_row",
			"a proof entry that is not a pair"],
		[["proof", 0], ["identity_resolved_to_reported_row"], "a one-item pair"],
		[["proof", 0, 0], "no_leaf_path_changed", "a check under the wrong name"],
		[["proof", 0, 1], false, "a proof check that does not hold"],
		[["leaf_paths_changed"], "/maps/0/items/1", "a leaf list that is not one"],
		[["leaf_paths_changed"], [7], "a leaf path that is not a string"],
		[["leaf_paths_changed"], ["/maps/0/items/1"],
			"a changed leaf, which is the answer this client refuses"],
		[["document_unchanged"], false, "an answer admitting the document moved"],
		[["document_unchanged"], "true", "a document flag that is not a boolean"],
		[["derived_damage"], 3, "a derived damage figure"],
		[["derived_destruction_count"], 1, "a derived destruction count"],
		[["derivation_performed"], "attack minus defense", "a named derivation"],
		[["damage_derived"], true, "an answer claiming it derived damage"],
		[["ledger_credited"], true,
			"an answer claiming it credited the ledger"],
		[["rows_destroyed"], 1, "a destroyed row"],
		[["rows_destroyed"], "0", "a destruction figure as a string"],
		[["preserved_branch_behaviour", "ledger"], 3,
			"a preserved-behaviour member that is not prose"],
		[["team_asymmetry"], "asymmetry", "an asymmetry report that is not one"],
		[["destruction"], "nothing", "a destruction report that is not an object"],
		[["destruction", "applied"], true, "an answer claiming it destroyed a row"],
		[["result"], "partial", "a result field no route emits"],
	]
	# Mutations applied to `OBSERVED_ABSENT_FLAG_SUCCESS` (unit 923), whose
	# `gate_two_resurrectable.present` is **false**.
	var absent: Array = [
		[["gates", "gate_two_resurrectable", "would_pass"], false,
			"an absent key carrying a verdict"],
		[["gates", "gate_two_resurrectable", "committed_value"], "0",
			"an absent key read as a committed zero"],
		[["gates", "gate_two_resurrectable", "absent_is_read_as_zero"], true,
			"an absent key reported as though it were a zero"],
		[["gates", "gate_two_resurrectable", "present"], true,
			"an absent key reported present while carrying no committed value"],
		[["gates", "gate_one_team", "any_row_would_pass"], false,
			"a team gate with no row and a verdict"],
		[["gates", "gate_one_team", "recorded_team"], 1,
			"a team gate with no row and a recorded team"],
		[["gates", "gate_one_team", "rows"], [7],
			"a team gate with no row and a row listed"],
	]
	for case in put:
		cases.append({"label": str(case[2]),
			"payload": _put(OBSERVED_SUCCESS, case[0], case[1])})
	# A second family, built on the **absent-key** answer, because the whole
	# point of that answer is a gate block whose `present` is false -- and every
	# mutation above is applied to the unit-1001 answer, where it is true. Two of
	# this suite's original cases were built on that mismatch and were therefore
	# **no-ops or legitimate successes**: one set `present` to `true` on an answer
	# that already read `true`, and one set `would_pass` to `false` on a *present*
	# key, which is a committed fact rather than a malformed shape. The absent-key
	# rules are therefore covered here, on an answer where they actually bite.
	for absent_case in absent:
		cases.append({"label": str(absent_case[2]),
			"payload": _put(OBSERVED_ABSENT_FLAG_SUCCESS, absent_case[0],
				absent_case[1])})
	cases.append({"label": "an answer that is not an object",
		"payload": "not a JSON object"})
	cases.append({"label": "an answer that is a list", "payload": ["combat"]})
	cases.append({"label": "a refusal carrying no code",
		"payload": {"result": "refused", "message": "no code", "detail": {}}})
	cases.append({"label": "a refusal whose detail is not an object",
		"payload": {"result": "refused", "code": "unknown_player",
			"message": "m", "detail": ["a", "b"]}})
	return cases


## Every malformed shape is refused, and refused as a **local** refusal: this
## client's `bad_request`, which is not a v1 code and never reaches the wire.
func _check_fail_closed() -> void:
	var cases := _fail_closed_cases()
	check_eq(cases.size(), FAIL_CLOSED_CASE_COUNT,
		"the fail-closed walk covers exactly the pinned number of shapes")
	var accepted: Array = []
	var mislabelled: Array = []
	var partial: Array = []
	for case in cases:
		var label := str((case as Dictionary)["label"])
		var parsed: Variant = ServerV1Combat.parse_combat_authority(
			(case as Dictionary)["payload"])
		if not (parsed is ServerV1Combat.CombatAuthorityResult):
			accepted.append("%s did not even answer with the typed result" % label)
			continue
		var typed: ServerV1Combat.CombatAuthorityResult = parsed
		if typed.ok:
			accepted.append(label)
			continue
		if typed.error_code != ServerV1Combat.CODE_BAD_REQUEST:
			mislabelled.append("%s answered %s" % [label, typed.error_code])
		if typed.combat != null or typed.resources_after != null \
				or typed.team_gate != null or typed.resurrectable_gate != null:
			partial.append(label)
	check_eq(accepted, [], "no malformed shape is accepted as a combat answer")
	check_eq(mislabelled, [],
		"and every one of them is refused as a client-LOCAL bad_request, never as"
		+ " a v1 code and never as an unsupported intent")
	check_eq(partial, [], "and none of them leaves a populated success field behind")

	# The two local codes are not v1 codes, and this is asserted rather than
	# assumed: they must never appear in the shared refusal vocabulary.
	var refusals := _repo_text(REFUSALS_MODULE)
	for local in [ServerV1Combat.CODE_UNSUPPORTED,
			ServerV1Combat.CODE_BAD_REQUEST]:
		check(not refusals.contains("\"" + str(local) + "\""),
			"the client-local code %s is not a v1 refusal code" % str(local))
	var answer: Variant = ServerV1Combat.combat_failure("x", "y", {"k": "v"})
	check(not (answer as ServerV1Combat.CombatAuthorityResult).ok,
		"the local failure factory builds a refusal")
	check_eq(answer.error_detail, {"k": "v"},
		"and copies its detail verbatim")
	check_eq(answer.combat, null, "and populates no success field at all")


# --- committed content ---------------------------------------------------------


## Every committed figure this suite states is **measured** from the committed
## mirror on every run.
##
## The client reads `packages/game-content/normalized/units.json` rather than
## `config/main.json`, and that choice is a measured one rather than a preference:
## the **stored** source holds 778 `items` rows of which **308** carry
## `type == "u"` and whose unit ids stop at 1306, while the normalized mirror of
## the **loaded** table holds **429** unit rows whose ids run to 1431 - exactly
## the 429 ids v1 itself reports in its `unaddressable_row` answer. The stored
## source is unpatched and the client cannot apply patches, so reading it would
## have made this suite's own committed figures disagree with the answers it
## checks. Both counts are measured here and both appear in the report, so the
## divergence is recorded rather than resolved.
func _check_committed_units_are_re_derived() -> void:
	var rows := _normalized_units()
	check(rows.size() > 0, "the normalized committed unit mirror is readable")
	var non_units: Array = []
	var bad_ids: Array = []
	var missing_columns: Array = []
	var string_columns: Dictionary = {}
	var non_whole_columns := 0
	var absent: Array = []
	var ids: Array = []
	for entry in rows:
		var row: Dictionary = entry
		if str(row.get("type", "")) != "u":
			non_units.append(str(row.get("legacy_id", "?")))
		if not (row.get("legacy_id", null) is String):
			bad_ids.append(str(row.get("name", "?")))
			continue
		ids.append(str(row["legacy_id"]))
		for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
			if not row.has(str(name)):
				missing_columns.append("%s.%s" % [str(row["legacy_id"]), str(name)])
			elif row[str(name)] is String:
				string_columns[name] = int(string_columns.get(name, 0)) + 1
			elif not _is_whole_number(row[str(name)]):
				non_whole_columns += 1
		var properties: Variant = row.get("properties", null)
		if properties is Dictionary \
				and not (properties as Dictionary).has("resurrectable"):
			absent.append(int(str(row["legacy_id"])))
	check_eq(non_units, [],
		"every row of the unit mirror carries the committed type u")
	check_eq(bad_ids, [], "and every row is keyed by a string legacy_id")
	check_eq(missing_columns, [],
		"and all nine committed combat columns are present on every row")
	check_eq(_sorted_keys(string_columns), [STRING_COMBAT_COLUMN],
		"and exactly one of the nine is a JSON string in the mirror -- the one"
		+ " committed column that is prose, not a quantity -- while the served"
		+ " items table stores all nine as strings, which is why the observed"
		+ " answers carry nine strings and the parser requires nine")
	check_eq(int(string_columns.get(STRING_COMBAT_COLUMN, 0)), rows.size(),
		"on every row of the mirror")
	check_eq(non_whole_columns, 0,
		"and every one of them is a whole JSON number, which is the only thing a"
		+ " whole-number test can honestly accept on an engine that decodes every"
		+ " JSON number as a float")
	check_eq(rows.size(), 429, "the committed unit mirror holds 429 rows")
	check_eq(absent, ABSENT_RESURRECTABLE_IDS,
		"and exactly three committed ids carry no resurrectable key at all, which"
		+ " is what the absent-key success exists to keep distinct from a zero")
	var sorted_ids := _int_list(ids)
	sorted_ids.sort()
	check_eq(sorted_ids[0], 923, "the committed unit id space starts at 923")
	check_eq(sorted_ids[sorted_ids.size() - 1], 1431, "and ends at 1431")

	# The observed refusal carries all 429 committed ids, and they are the same
	# 429 the mirror holds. That is the strongest link this suite can draw
	# between a captured answer and the committed content it read.
	var reported: Variant = (OBSERVED_REFUSALS[
		"identity naming no committed unit row"]["body"]
		as Dictionary)["detail"]["committed_unit_ids"]
	check_eq((reported as Array).size(), rows.size(),
		"the observed unaddressable answer carries one id per committed unit row")
	var mismatch := 0
	# **Not** an ascending-order claim. The server emits the mirror's own row
	# order, which is not sorted -- measured: the committed file's order and the
	# reported order are element-for-element identical, while sorting either one
	# produces 39 positional disagreements. The claim is therefore "the committed
	# ids, in the committed order", which is stronger than set equality.
	var file_order: Array = []
	for entry in rows:
		var row: Dictionary = entry
		if row.get("legacy_id", null) is String:
			file_order.append(int(str(row["legacy_id"])))
	for index in range(min((reported as Array).size(), file_order.size())):
		if int((reported as Array)[index]) != int(file_order[index]):
			mismatch += 1
	check_eq(mismatch, 0,
		"and every one of them is a committed unit id, in the committed mirror's"
		+ " own row order")

	# The stored, unpatched source, measured rather than described.
	var raw: Variant = JSON.parse_string(_repo_text(RAW_CONFIG))
	check(raw is Dictionary, "the stored content source is readable")
	if not (raw is Dictionary):
		return
	var items: Variant = (raw as Dictionary).get("items", null)
	check(items is Array, "and carries an items array")
	if not (items is Array):
		return
	var units := 0
	var string_ids := 0
	var highest := 0
	for entry in (items as Array):
		var row: Dictionary = entry
		if not (row.get("id", null) is String):
			string_ids += 1
		if str(row.get("type", "")) == "u":
			units += 1
			highest = max(highest, int(str(row.get("id", "0"))))
	check_eq((items as Array).size(), 778,
		"the STORED source holds 778 items rows")
	check_eq(units, 308, "of which 308 carry type u, not the 429 the loaded table"
		+ " serves")
	check_eq(string_ids, 0, "and every id is stored as a string")
	check_eq(highest, 1306,
		"whose unit ids stop at 1306, so the stored source cannot be the table v1"
		+ " answered from and the client reads the normalized mirror instead")


## The request is exactly two fields, and the enclosing function does **not**
## forward the `action` its own signature accepts.
func _check_intent_body() -> void:
	var source := _comment_free(_project_source(API_SCRIPT))
	var lines := _code_lines(source)
	var declaration := -1
	for index in lines.size():
		if str(lines[index]).strip_edges().begins_with(
				"static func _combat_intent_body("):
			declaration = index
			break
	check(declaration != -1,
		"the transport declares the v1 combat intent body")
	if declaration == -1:
		return
	var body: Array = []
	for index in range(declaration + 1, min(declaration + 8, lines.size())):
		body.append(str(lines[index]))
	var text := "\n".join(body)
	check(text.contains("return {"),
		"and it returns a dictionary literal")
	var open := text.find("{")
	var close := text.rfind("}")
	check(open != -1 and close > open, "with both braces on the returned line")
	if open == -1 or close <= open:
		return
	check_eq(_mapping_literal_keys(text.substr(open + 1, close - open - 1)),
		["player_id", "unit_id"],
		"the v1 combat request carries exactly two fields, and a third would be a"
		+ " field this client sends that no committed value names")
	check(not text.contains("action"),
		"the action parameter the enclosing function accepts is not forwarded")
	check_eq(ServerV1Api.COMBAT_PATH, "/v1/combat",
		"and the route this line owns is the one it declares")

	# The enclosing function: its head declares the parameter, its body never
	# mentions it again. That is the whole claim, so it is measured on the two
	# regions rather than on the file.
	var head := ""
	var head_index := -1
	for index in lines.size():
		var candidate := str(lines[index]).strip_edges()
		if not candidate.begins_with("func " + INTENT_METHOD + "("):
			continue
		head_index = index
		head = candidate
		var probe := index + 1
		while probe < lines.size() and not head.contains("->"):
			head += " " + str(lines[probe]).strip_edges()
			probe += 1
		break
	check(head_index != -1, "the transport declares " + INTENT_METHOD)
	check(head.contains("action: Variant"),
		"whose signature accepts the facade's action parameter")
	var tail: Array = []
	for index in range(head_index + 1, lines.size()):
		var candidate := str(lines[index]).strip_edges()
		if candidate.begins_with("func ") or candidate.begins_with("static func "):
			break
		tail.append(str(lines[index]))
	var tail_text := "\n".join(tail)
	check(not tail_text.contains("action"),
		"and whose body never mentions it again, so the omission is measured")
	check(tail_text.contains("_combat_intent_body(user_id, addressing)"),
		"and forwards the save identity and the unit identity verbatim")
	check(tail_text.contains("parse_combat_authority("),
		"and parses the answer through v1's own parser")


## Guard A - no scaling. The typed-result module contains no `*`, no `/` and no
## compound assignment anywhere in its code, with an **empty** exception list.
func _check_no_client_arithmetic() -> void:
	var code := _code_only(_project_source(RESULT_SCRIPT))
	var offenders: Array = []
	for index in range(_code_lines(code).size()):
		var line := str(_code_lines(code)[index])
		for operator in SCALING_OPERATORS:
			if line.contains(str(operator)):
				offenders.append("%d carries %s" % [index + 1, str(operator)])
	check_eq(offenders, [],
		"the typed-result module contains no scaling operator at all, so no"
		+ " reported value can have been scaled into an outcome")
	# The predicate is proved, not trusted: a planted line must be found.
	var control := _code_lines(_code_only("var scaled := int(a) * int(b)"))
	check(_code_lines(_code_only("var scaled := int(a) * int(b)"))[0].contains("*"),
		"the scaling scan finds a multiplication when one is planted")
	check(_code_lines(_code_only("var scaled := int(a) / int(b)"))[0].contains("/"),
		"and a division")
	check_eq(control.size(), 1, "and the projection keeps its line structure")
	# The projection is the one that blanks literals, which is what makes the scan
	# honest: `preload("res://...")` must not read as arithmetic.
	check(not _code_only("var BootData = preload(\"res://scripts/a.gd\")")
		.contains("/"),
		"and a path inside a string literal is invisible to it")
	# The only arithmetic-shaped expression is the whole-number test, and it is
	# applied to the balances and the ids, never to a committed combat column.
	var source := _code_only(_project_source(RESULT_SCRIPT))
	check_eq(_count_occurrences(source, "floor("), 1,
		"the module rounds exactly once, in the whole-number test")
	# **Correction to the premise this check was first written against.** The
	# claim was "the module never calls int() on a reported value". That is false
	# and was asserted rather than measured: the module makes **8** `int()` calls,
	# because eight JSON numbers must be narrowed to `int` before they can be
	# carried. The honest and stronger claim is about *what* they wrap -- every
	# argument is a local that `_whole_number` already validated, and `int()`
	# itself is never the validation. Both halves are pinned below.
	check_eq(_int_call_arguments(source), [
		"amount", "count", "destroyed", "instant", "resolved", "unit", "value",
		],
		"every int() the module makes wraps one of these seven locals, and every"
		+ " one of them is the value a whole-number test already validated")
	check_eq(_count_occurrences(_slice_function(source, "_whole_number"), "int("),
		1,
		"and the one argument this check cannot account for from a caller's local"
		+ " is `value`, inside the whole-number test itself")


## ## No line may **relate** two committed combat values
##
## Two rules, because one is not enough.
##
## The first is **containment**: each of the nine committed column names must
## appear nowhere in the module's code except inside the reporting constant that
## enumerates them. Read from the comment-free projection, so a literal is
## visible - a code-only projection erases the very names under measurement.
##
## The second is the **pair rule**, and it needs an operator as well as two
## names: the reporting constant legitimately carries five names on one line, so
## a bare quoted-pair scan would fire on an enumeration and be unlearnable. A
## line that *relates* two names is one with an operator between them, and that
## is the shape this rule fires on.
func _check_no_line_compares_two_reported_values() -> void:
	var projection := _comment_free(_project_source(RESULT_SCRIPT))
	var lines := _code_lines(projection)
	var first := -1
	var last := -1
	for index in lines.size():
		var line := str(lines[index])
		if line.begins_with("const REPORTED_COMBAT_FIELDS"):
			first = index
		if first != -1 and index > first and line.strip_edges() == "]":
			last = index
			break
	check(first != -1 and last > first,
		"the reporting constant is locatable in the module's own source")
	var outside: Array = []
	for index in lines.size():
		if index >= first and index <= last:
			continue
		for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
			if str(lines[index]).contains("\"%s\"" % str(name)):
				outside.append("%d names %s" % [index + 1, str(name)])
	check_eq(outside, [],
		"no committed combat column is named anywhere in the module except inside"
		+ " the constant that reports them")

	var pairs: Array = []
	for index in lines.size():
		var line := str(lines[index])
		var named := 0
		for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
			if line.contains("\"%s\"" % str(name)):
				named += 1
		if named < 2:
			continue
		for operator in RELATION_OPERATORS:
			if line.contains(str(operator)):
				pairs.append("%d relates %d reported names" % [index + 1, named])
				break
	check_eq(pairs, [],
		"and no line relates two of them, even though the constant lists five on"
		+ " one line - an operator is what makes a line a relation")
	# The pair rule's positive control, planted rather than assumed.
	var control := "if int(body[\"attack\"]) > int(body[\"defense\"]):"
	var control_named := 0
	for name in ServerV1Combat.REPORTED_COMBAT_FIELDS:
		if control.contains("\"%s\"" % str(name)):
			control_named += 1
	var control_relates := false
	for operator in RELATION_OPERATORS:
		if control.contains(str(operator)):
			control_relates = true
			break
	check(control_named == 2 and control_relates,
		"the pair rule fires on a planted comparison of two committed columns")
	var listing := "\"attack\", \"defense\", \"life\", \"attack_interval\","
	var listing_relates := false
	for operator in RELATION_OPERATORS:
		if listing.contains(str(operator)):
			listing_relates = true
			break
	check(not listing_relates,
		"and stays silent on the enumeration the constant actually contains")


# --- anti-invention guards -----------------------------------------------------


## An invented derivation helper is refused by **name** and by **substring**, in
## **both** directions, against the declared function inventory - and the
## inventory is pinned whole, because that is the real gate: a helper named
## `outcome_from_columns` would pass every reserved stem.
func _check_absent_derivation_helpers() -> void:
	var declared := _declared_function_names(_project_source(RESULT_SCRIPT))
	check_eq(_sorted_set(declared), RESULT_FUNCTION_INVENTORY,
		"the typed-result module declares exactly the pinned fourteen functions")
	check_eq(declared.size(), RESULT_FUNCTION_INVENTORY.size(),
		"one declaration each, so an overwrite cannot hide behind the set")

	var offenders: Array = []
	for name in declared:
		var folded := str(name).to_lower()
		for stem in RESERVED_DERIVATION_STEMS:
			if folded.contains(str(stem)):
				offenders.append("%s carries the reserved stem %s"
					% [str(name), str(stem)])
	check_eq(offenders, [],
		"and no declared name carries any of the nineteen reserved stems, so this"
		+ " client has no helper that could compute an outcome")
	var exact: Array = []
	for stem in RESERVED_DERIVATION_STEMS:
		if _sorted_set(declared).has(str(stem)):
			exact.append(str(stem))
	check_eq(exact, [],
		"and no reserved stem is itself a declared function name")

	# The transport is owned **combat-scopedly** here; its whole inventory belongs
	# to `test_magic_v1.gd`, and two owners of one list is the drift this
	# repository has already recorded twice.
	var api_declared := _declared_function_names(_project_source(API_SCRIPT))
	var api_offenders: Array = []
	for name in API_COMBAT_FUNCTIONS:
		check(api_declared.has(str(name)),
			"the transport declares the combat-owned function %s" % str(name))
		var folded := str(name).to_lower()
		for stem in RESERVED_DERIVATION_STEMS:
			if folded.contains(str(stem)):
				api_offenders.append("%s carries %s" % [str(name), str(stem)])
	check_eq(api_offenders, [],
		"and neither combat-owned transport function carries a reserved stem")

	# The predicate is proved in both directions and with a case-folded probe,
	# because `godot-friends` measured that an exact-name check passes a merely
	# prefixed helper and that a case-sensitive one passes `Friend_Of`.
	var planted := ["damage_for", "Honor_Payout", "pick_row"]
	var caught: Array = []
	for name in planted:
		if not _stem_hit(str(name)):
			caught.append(str(name))
	check_eq(caught, ["pick_row"],
		"two suffixed reserved-word helpers are caught by the substring scan and"
		+ " one that borrows no reserved stem is not - which is why the pinned"
		+ " inventory above is the real gate and this scan is the belt")
	# `outcome_from_columns` was this probe's third name until measurement
	# corrected it: `outcome` **is** one of the nineteen stems, so the scan
	# caught that name too and the positive control above would have read as a
	# broken predicate. It is kept here as the case that distinguishes an
	# accidentally-too-broad stem from a working scan.
	check(_stem_hit("outcome_from_columns"),
		"and the name this check first used is itself caught, because `outcome`"
		+ " is a reserved stem - which is why it could not serve as the"
		+ " stem-free control")


## The **domain** module's whole function inventory, read from the repository.
func _check_domain_inventory() -> void:
	var source := _repo_text(DOMAIN_MODULE)
	check(source != "", "the Python combat domain module is readable")
	var declared := _python_function_names(source)
	check_eq(_sorted_set(declared), [
		"_changed_leaf_paths", "_checks", "_committed_report",
		"_destruction_refusal", "_destruction_report", "_gate_report",
		"_proof_refusal", "_refuse", "_repository_refusal", "_rows_report",
		"_serialise", "_unknown_unit", "apply_combat",
	], "it declares exactly the pinned thirteen functions")
	check_eq(declared.size(), 13,
		"one declaration each, so an invented helper cannot hide behind the set")
	check(declared.has("apply_combat"),
		"and the one entry point is the module's own name")
	var members := _sorted_set(_named_refusal_members(source))
	check_eq(members, DOMAIN_NAMED_CODES,
		"and it names exactly seven RefusalCode members")
	for member in members:
		check(not members.has(str(member).to_lower())
			and _sorted_set(_named_refusal_members(source)).has(str(member)),
			"the named code %s is spelled in the enum's own case" % str(member))


func _check_domain_reserved_stems() -> void:
	var source := _repo_text(DOMAIN_MODULE)
	var declared := _python_function_names(source)
	var offenders: Array = []
	for name in declared:
		var folded := str(name).to_lower()
		for stem in RESERVED_DERIVATION_STEMS:
			if folded.contains(str(stem)):
				offenders.append("%s carries %s" % [str(name), str(stem)])
	check_eq(offenders, [],
		"no function the domain declares carries a reserved derivation stem, so"
		+ " the server invented no damage, count, chance or payout rule either")
	# The scan is proved on the domain's own scanner rather than assumed.
	var planted := "def destruction_count_for(unit):\n    return 1\n"
	check(_python_function_names(planted).has("destruction_count_for"),
		"the Python name scan finds a planted helper wearing a reserved stem")
	check(not _sorted_set(_python_function_names(source)).has(
			"destruction_count_for"),
		"and the domain does not declare one")


## The Python name scan is a **line scan**, and both of its directions are
## asserted here rather than left in prose.
##
## **Corrected premise.** This check first claimed the scan "over-counts a
## commented definition". Measured, it does not: `strip_edges` removes the
## indentation but leaves the `#`, and the scan then requires the line to begin
## with `def `, so a commented definition reads as **no** function. The real
## limitation is the opposite one -- a `def` line inside a docstring **is**
## counted -- and that is the direction worth pinning, because it can only make a
## pinned inventory fail, never let a new function through.
func _check_python_name_scan_finds_planted_defs() -> void:
	var planted := "def alpha(x):\n    return x\n\n\nasync def beta(y):\n    return y\n"
	check_eq(_sorted_set(_python_function_names(planted)), ["alpha", "beta"],
		"the Python name scan finds both a plain and an async definition")
	var commented := "# def gamma(z):\n    return z\n"
	check_eq(_python_function_names(commented), [],
		"and a commented definition reads as no function at all, because the"
		+ " comment marker survives the edge strip")
	var docstring := '"""\n    def delta(w):\n        for detail.\n    """\n'
	check_eq(_sorted_set(_python_function_names(docstring)), ["delta"],
		"but a def at the START of a docstring line is counted, and that is the"
		+ " recorded limitation -- the safe direction, because an over-count"
		+ " fails the pinned inventory rather than hiding a new function")
	check_eq(_python_function_names('"""See def epsilon(v): inline."""\n'), [],
		"while the same def is ignored when its line begins with the quote, which"
		+ " is why the limitation is about line position and not about docstrings")
	var nested := "class Thing:\n    def method(self):\n        return 1\n"
	check_eq(_sorted_set(_python_function_names(nested)), ["method"],
		"and it finds an indented method, because indentation is stripped first")


## Each code this route answers with exists in the one shared table, carries the
## status the observed answer carried, and is named by the domain exactly when
## the domain is the site that raises it.
func _check_combat_codes_live_in_the_combat_modules() -> void:
	var source := _repo_text(REFUSALS_MODULE)
	var statuses := _refusal_statuses(source)
	check_eq(statuses.size(), DECLARED_REFUSAL_CODE_COUNT,
		"the shared refusal table still declares twenty codes")
	for member in DOMAIN_NAMED_CODES:
		check(statuses.has(str(member)),
			"every code the domain names is declared: %s" % str(member))
	for code in _sorted_keys(EXPECTED_COMBAT_REFUSALS):
		var row: Array = EXPECTED_COMBAT_REFUSALS[code]
		var member := str(row[0])
		check(statuses.has(member),
			"the observed code %s is declared in the shared table" % code)
		if statuses.has(member):
			check_eq(int(statuses[member]), int(row[1]),
				"and carries the HTTP status the observed answer carried: %s" % code)
		var named := DOMAIN_NAMED_CODES.has(member)
		check_eq(named, bool(row[2]),
			"and is named by the domain module exactly when the domain is the site"
			+ " that raises it: %s" % code)

	# The seven observed conditions collapse to six codes, and the collapse is
	# asserted rather than left accidental: a building id and an id naming no row
	# are one rule seen twice.
	var observed := _sorted_set(_string_list(_observed_codes()))
	check_eq(observed, _sorted_keys(EXPECTED_COMBAT_REFUSALS),
		"the seven observed refusal conditions resolve to exactly the six expected"
		+ " codes, and no seventh")
	var building: Dictionary = OBSERVED_REFUSALS[
		"a BUILDING id offered as a unit"]
	var unaddressable: Dictionary = OBSERVED_REFUSALS[
		"identity naming no committed unit row"]
	check_eq(building["code"], unaddressable["code"],
		"a committed building id is refused by the SAME code as an id naming no"
		+ " row, because the three committed id spaces have zero overlap")
	check_eq((building["body"] as Dictionary)["detail"]["requested_unit_id"],
		OBSERVED_BUILDING_ID,
		"and the observed building refusal addressed committed building %s (%s),"
			% [str(OBSERVED_BUILDING_ID),
				str(_committed_building_name(int(OBSERVED_BUILDING_ID)))])
	check_eq((unaddressable["body"] as Dictionary)["detail"]["requested_unit_id"],
		0, "while the no-row refusal addressed the integer zero")
	check_eq((unaddressable["body"] as Dictionary)["detail"][
			"non_positive_is_not_clamped"], true,
		"and states that zero and every negative name no row rather than aliasing a"
		+ " position, so no clamp was invented")
	check_eq((unaddressable["body"] as Dictionary)["detail"][
			"rolled_back"], false,
		"and that no rollback was started, because this module writes nothing")


# --- the facade, the intent, and the boundary ----------------------------------


func _check_facade_registration() -> void:
	var facade := _project_source(FACADE_SCRIPT)
	var declared := _declared_function_names(facade)
	check(declared.has(INTENT_METHOD),
		"the GameApi facade declares " + INTENT_METHOD)
	check(facade.contains("await _impl." + INTENT_METHOD + "("),
		"and forwards it to the selected implementation")
	check_eq(_return_type_of(facade, INTENT_METHOD), "Variant",
		"and declares its result Variant, because the three implementations do"
		+ " not agree")
	check(facade.contains("_impl.combat_town("),
		"the forwarding call names the intent, so it cannot drift from the method")
	var implementations := 0
	for relative in IMPL_RETURN_TYPES:
		var source := _project_source(str(relative))
		check(source != "", "the implementation %s is readable" % str(relative))
		check(_declared_function_names(source).has(INTENT_METHOD),
			"and declares %s" % INTENT_METHOD)
		implementations += 1
	check_eq(implementations, 3,
		"all three implementations declare the intent, so no fourth can appear"
		+ " without this suite noticing")


## The widening is **necessary**, not stylistic: the two v0 implementations still
## declare v0's model, so the facade naming either would be lying to the other.
func _check_return_type_widening() -> void:
	var types: Array = []
	for relative in IMPL_RETURN_TYPES:
		var source := _project_source(str(relative))
		var declared := _return_type_of(source, INTENT_METHOD)
		check_eq(declared, str(IMPL_RETURN_TYPES[str(relative)]),
			"%s declares %s for %s"
			% [str(relative), str(IMPL_RETURN_TYPES[str(relative)]), INTENT_METHOD])
		types.append(declared)
	var v1_type := str(IMPL_RETURN_TYPES["scripts/gameapi/server_v1_api.gd"])
	var v0_type := str(IMPL_RETURN_TYPES["scripts/gameapi/legacy_v0_api.gd"])
	check(v1_type != v0_type,
		"the v1 implementation's declared type differs from v0's, which is the"
		+ " reason the facade is Variant rather than a convenience")
	check_eq(_return_type_of(_project_source(API_SCRIPT), INTENT_METHOD), v1_type,
		"and the transport really declares the v1 type, read from its source")
	var fake_type := str(IMPL_RETURN_TYPES["scripts/gameapi/fake_api.gd"])
	check_eq(fake_type, v0_type,
		"the fake and the legacy-v0 implementation agree, so only v1 diverges")


func _check_unsupported_intent_left_the_table() -> void:
	var unsupported: Array = CollectSuite.UNSUPPORTED_INTENTS
	var returned: Array = []
	for entry in unsupported:
		if HANDED_OFF_LOCAL.has(str(entry[0])):
			returned.append(str(entry[0]))
	check_eq(returned, [],
		"this line's intent is not in the locally-refused table any more")
	check_eq(unsupported.size(), 20,
		"and twenty intents remain locally refused, one fewer than before the"
		+ " combat route landed")
	var handed: Array = CollectSuite.HANDED_OFF_INTENTS
	check(handed.has(INTENT_METHOD),
		"the intent is named in the hand-off table instead")
	var owner := str(CollectSuite.HANDED_OFF_SUITES[INTENT_METHOD])
	check_eq(owner, "res://tests/test_combat_v1.gd",
		"and the hand-off names this suite as its owner")
	check(ResourceLoader.exists(owner),
		"which exists on disk, so the hand-off cannot dangle")
	# The intent really is implemented rather than locally refused: it is the only
	# combat-owned function pair on the transport, and both are declared.
	var api_declared := _declared_function_names(_project_source(API_SCRIPT))
	for name in API_COMBAT_FUNCTIONS:
		check(api_declared.has(str(name)),
			"and the transport declares %s rather than refusing it" % str(name))


## The route path appears **once** in the transport and nowhere else, and the
## live harness names it in both of the two places it must. That second half is
## an ownership claim on the harness edit: if the harness stopped naming the
## route, the live phase could not register it and this suite would say so.
func _check_transport_token_placement() -> void:
	var projection := _comment_free(_project_source(API_SCRIPT))
	check_eq(_count_occurrences(projection, "\"" + ServerV1Api.COMBAT_PATH + "\""),
		1, "the transport carries exactly one literal for the route it owns")
	for relative in [FACADE_SCRIPT, RESULT_SCRIPT, V0_SCRIPT, FAKE_SCRIPT,
			PRESERVED_SUITE, FRIEND_SUITE]:
		check(not _comment_free(_project_source(str(relative))).contains(
				ServerV1Api.COMBAT_PATH),
			"and %s names no v1 route path at all" % str(relative))
	var harness := _repo_text(LIVE_PHASE_SCRIPT)
	check(harness.contains("COMBAT_PATH = \"" + ServerV1Api.COMBAT_PATH + "\""),
		"the live harness declares the route path it may register")
	check(harness.contains("KNOWN_ROUTE_PATHS = (COLLECT_PATH, COLLECTION_PATH,"
		+ " COMBAT_PATH, MAGIC_PATH)"),
		"and adds it to the closed set of registerable routes")
	check(harness.contains("\"POST %s\" % COMBAT_PATH"),
		"and names it in the expected startup banner")
	# **Not** "last". `run.py` prints `sorted(ROUTES)`, and the sorted order is
	# collect, collection, combat, magic -- combat is **third**, before magic.
	# This check asserts the measured order rather than the one this line would
	# have preferred, because the banner check in the harness compares a whole
	# list and a wrong order fails a passing phase.
	check(harness.find("\"POST %s\" % COMBAT_PATH")
			< harness.find("\"POST %s\" % MAGIC_PATH"),
		"third of the four, in the order the service actually sorts them")


## The preserved combat surface stays owned by the preserved-combat capability.
## `end_attack` and `/v0/combat` are named there and by v0's transport, and by
## **neither** delivered v1 client module - so this line did not quietly re-own
## a surface it only reads.
func _check_boundary_ownership() -> void:
	for relative in DELIVERED_MODULES:
		var projection := _comment_free(_project_source(str(relative)))
		check(not projection.contains("CombatFlow"),
			"%s never names v0's combat model" % str(relative))
		check(not projection.contains("end_attack"),
			"%s never names the preserved branch" % str(relative))
		check(not projection.contains("/v0/combat"),
			"%s never names v0's route" % str(relative))
	var v0_projection := _comment_free(_project_source(V0_SCRIPT))
	check(v0_projection.contains("CombatFlow"),
		"v0's transport still names its own model")
	check(v0_projection.contains("\"%s\"" % "/v0/combat"),
		"and still names v0's route")
	var owner := _project_source(PRESERVED_SUITE)
	check(owner != "", "the preserved-combat suite is still on disk")
	# The **bare token**, not the quoted form. Measured: the preserved suite never
	# spells `end_attack` as a quoted string -- it names the branch in prose and
	# in one diagnostic (`"the end_attack branch was not located"`). A quoted-form
	# assertion would have read that suite as having lost its branch.
	check(_comment_free(owner).contains("end_attack"),
		"and still names the branch it owns, so this line did not re-own it")
	check(_comment_free(owner).contains(CombatFlowGuard.LEGACY_COMMAND),
		"and still pins the legacy command it measured")
	# The whole-tree needle scan belongs to that suite and re-derives its own
	# file count every run, so adding this suite raises its number by design.
	check(_comment_free(owner).contains("NEEDLES"),
		"and still carries the tree-wide needle scan that covers this suite")


## The intent this line's own suite is expected to have handed over. Read from the
## delivering suite rather than transcribed here, so the two cannot disagree; the
## pair is asserted equal so a rename on either side is a failure.
const HANDED_OFF_LOCAL := ["collect_income", "complete_collection_town",
	"magic_town", "combat_town"]

## The preserved combat suite's own pinned legacy command, read through a
## preload-free constant so this suite does not take a dependency on it.
const CombatFlowGuard = preload("res://tests/test_combat_actions.gd")


# --- this suite's own source ---------------------------------------------------


## Task 10.x: **no `%` format argument this suite cannot account for.**
##
## `magic-live-v1` found the real fault on the delivered bytes: a live-arm
## message written with no placeholder in the literal. GDScript raises
## `not all arguments converted during string formatting in operator '%'`,
## which aborted the function partway through; `test_base.gd` records a function
## abort as a PASS, so the phase still exited 0 and **every remaining assertion
## silently never ran**. The hermetic arm cannot reach the live arm, so the fault
## is guarded at the source.
##
## Two shapes are covered, because the delivered file used both: `literal %
## operand` on one line, and `literal` on one line followed by `% operand` on the
## next. The needle is assembled at run time so no line of this guard contains the
## two-character sequence it looks for, which is what stops the guard scanning
## itself.
func _check_no_unconverted_format_arguments() -> void:
	var needle := "%s%s%s" % ["\"", " ", "%"]
	var lead := "%s%s" % ["%", " "]
	var source := _comment_free(_repo_text(SUITE_REPO_PATH))
	var lines := source.split("\n")
	var offenders: Array = []
	for index in range(lines.size()):
		var line := str(lines[index])
		var operand := ""
		var column := line.rfind(needle)
		if column != -1:
			operand = line.substr(0, column)
		else:
			var stripped := line.strip_edges()
			if not stripped.begins_with(lead):
				continue
			if index == 0:
				continue
			var previous := str(lines[index - 1])
			if not previous.strip_edges().ends_with("\""):
				continue
			operand = previous
		if _placeholder_count(operand) == 0:
			offenders.append("%d: %s" % [index + 1, operand.strip_edges()])
	check_eq(offenders.size(), 0,
		"every %s-format in this suite has a placeholder to consume its operand"
		% "percent-sign")
	check_eq(_placeholder_count("a %s and a %d"), 2,
		"the placeholder count reads two placeholders")
	check_eq(_placeholder_count("no placeholder here"), 0,
		"and reads none from a literal that carries none")
	check_eq(_placeholder_count("a literal percent sign"), 0,
		"a bare percent sign inside a word is not a placeholder")


## No **chained** format operation in the delivered module.
##
## This guard exists because the suite's own format guard found nothing here and
## the module still had two runtime format failures, both of the same shape:
##
## ```gdscript
## "…reports rows_destroyed %s, which this client "
##     % "refuses because v1 has no write path" % str(value)
## ```
##
## GDScript's `%` binds left to right, so that is `("…" % "refuses…") % str(v)`.
## The **first** operation consumes the only placeholder and the second then has an
## operand and no placeholder to consume, which is a *run-time* error -- not a parse
## error, and not an error on the success path. Both branches were reached only by
## the fail-closed walk, which is why an answer that parsed cleanly for four
## iterations still could not refuse a malformed one.
##
## The rule is therefore mechanical: in the comment-free projection, a line that
## begins a format operation (leading `% `, previous line a string literal) may not
## itself contain a second `% ` after that lead.
func _check_no_chained_format_operations() -> void:
	var lines := _code_lines(_comment_free(_project_source(RESULT_SCRIPT)))
	var lead := "%s%s" % ["%", " "]
	var offenders: Array = []
	for index in range(lines.size()):
		var stripped := str(lines[index]).strip_edges()
		if not stripped.begins_with(lead):
			continue
		if index == 0:
			continue
		if not str(lines[index - 1]).strip_edges().ends_with("\""):
			continue
		if stripped.find(lead, lead.length()) != -1:
			offenders.append("%d chains a second format operation" % (index + 1))
	check_eq(offenders, [],
		"no format operation in the module is chained onto another, because a"
		+ " chain parses and fails only when the branch is reached")
	# Proved, not trusted: the shape is detected when it is planted.
	var planted := [
		"var a = \"x %s y\"", "% \"z\" % str(v)", "",
	]
	var planted_lines: Array = []
	for index in range(planted.size() - 1):
		planted_lines.append(str(planted[index]))
	var detected := false
	for index in range(planted_lines.size()):
		var candidate := str(planted_lines[index]).strip_edges()
		if not candidate.begins_with(lead):
			continue
		if not str(planted_lines[index - 1]).strip_edges().ends_with("\""):
			continue
		if candidate.find(lead, lead.length()) != -1:
			detected = true
	check(detected,
		"the chained-format scan fires on the planted shape this module carried"
		+ " twice")


# --- the live arm --------------------------------------------------------------


## One request, one answer, and a **file-level** diff of the disposable corpus
## save across it.
##
## This is the phase with the opposite shape from `magic-live-v1`, and the
## difference is the finding. Magic **writes**, so its phase asserts one touched
## leaf and a risen counter; **combat writes nothing at all**, so this one asserts
## the *empty* diff. There is consequently **no `--expect-save-mutation`**: the
## harness option exists to prove a mutation happened, and asserting it here would
## demand the very thing this route refuses to do. `verify-boot.ps1` widens its
## per-phase assertion for exactly this reason and records the omission in this
## phase's `Assertions` string rather than leaving it to be inferred.
##
## Nothing is seeded. The disposable corpus places **no unit row at all** (40
## placements, every committed `type` `b`), so the identity resolves against the
## committed table alone and the empty diff is meaningful: there was a row-shaped
## thing to look at and nothing about it moved.
func _check_live() -> void:
	var endpoint := _arg(ARG_ENDPOINT, LIVE_ENDPOINT)
	var player_id := _arg(ARG_PLAYER_ID, "")
	var corpus := _arg(ARG_CORPUS, "")
	check(player_id != "", "the live phase supplies the disposable corpus's player id")
	check(corpus != "", "and the disposable corpus path, for the file-level diff")
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null or player_id == "" or corpus == "":
		return
	var save_file := corpus.path_join("saves").path_join(player_id + SAVE_SUFFIX)
	check(FileAccess.file_exists(save_file),
		"the disposable corpus save is readable at the path the harness gave")
	if not FileAccess.file_exists(save_file):
		return
	api.configure("server_v1", endpoint)
	check_eq(str(api.implementation_name()), "server_v1",
		"the facade selects Server v1 for the live phase")
	var impl: Variant = api._impl
	check(impl is ServerV1Api, "the live implementation is a ServerV1Api")
	if not (impl is ServerV1Api):
		return

	var before := _read_save(save_file)
	check_eq(_sorted_keys(_dead_heroes(before)), [],
		"the fresh disposable ledger is empty, and this phase seeds nothing")
	var before_requests := int(impl.transport_requests)
	var answer: Variant = await api.combat_town(player_id, "resolve", LIVE_UNIT)
	if not (answer is ServerV1Combat.CombatAuthorityResult):
		fail("the live answer is v1's own typed combat result")
		return
	var typed: ServerV1Combat.CombatAuthorityResult = answer
	check(typed.ok, "the live combat resolves (%s / %s)"
		% [typed.error_code, typed.error_message])
	if not typed.ok:
		return
	check_eq(typed.protocol, ServerV1Combat.PROTOCOL,
		"the live answer is stamped with v1's protocol")
	check_eq(typed.action, ServerV1Combat.ACTION, "and names the action that ran")
	check_eq(typed.combat.unit_id, LIVE_UNIT,
		"and reports the identity the client sent")
	check_eq(typed.committed_id, str(LIVE_UNIT),
		"and the committed id column as a string")
	check_eq(typed.committed_name, OBSERVED_UNIT_NAME,
		"and the committed name, so the live answer and the observed fixture"
		+ " resolve the same committed row")
	check_eq(_sorted_set(_string_list(typed.combat_fields.keys())),
		_sorted_set(ServerV1Combat.REPORTED_COMBAT_FIELDS),
		"and carries the nine committed combat columns as strings")
	check_eq(typed.rows_destroyed, 0, "and destroys no row")
	check(typed.ledger_credited == false, "and credits no ledger entry")
	check(typed.gates_enforced == false, "and enforces no gate")
	check_eq(typed.leaf_paths_changed, [], "and changed no stored leaf path")
	check(typed.document_unchanged,
		"and reports the whole persisted document byte-identical")
	check(typed.resurrectable_gate != null
			and typed.resurrectable_gate.present,
		"and reports the committed resurrectable key as present")
	check_eq(int(impl.transport_requests) - before_requests, 1,
		"one combat intent put exactly ONE request on the wire")
	check_eq(_sorted_set(_string_list(typed.stored_resources_compared)),
		_sorted_set(ServerV1Combat.STORED_RESOURCE_NAMES),
		"and names exactly the seven stored resources it compared")
	# **The positive typed marker.** `verify-boot.ps1` matches per-phase regexes
	# against this line, so a phase whose request never left the client cannot
	# pass on refusals alone. Every group is drawn from the **typed** result.
	print("[test] live-server-v1-combat unit=%d rows_destroyed=%d ledger_credited=%s document_unchanged=%s leaves=%d compared=%d gates_enforced=%s"
		% [int(typed.combat.unit_id), int(typed.rows_destroyed),
			str(typed.ledger_credited), str(typed.document_unchanged),
			(typed.leaf_paths_changed as Array).size(),
			(typed.stored_resources_compared as Array).size(),
			str(typed.gates_enforced)])

	# ---- the file-level half, which is the claim --------------------------
	var after := _read_save(save_file)
	check(after.size() > 0, "the call left the disposable save readable")
	var difference := _touched_leaf_paths(before, after)
	check_eq(difference, [],
		"and the corpus save is byte-identical across it: not one leaf added,"
		+ " changed or removed")
	var ledger := _dead_heroes(after)
	check_eq(_sorted_keys(ledger), [],
		"and the dead-hero ledger is still empty, so no ledger key was created")
	var balances := _stored_balances(after)
	# **Fail closed BEFORE comparing.** Every balance must have resolved to a
	# whole number at a real holder; if one did not, "nothing moved" would be
	# vacuously true over a `null` and the comparison below would be a claim
	# about nothing. This ordering is the fix for the recorded live-path defect:
	# the first version evaluated `int(null)` here, which ABORTS, and an abort
	# is recorded as a pass.
	var unreadable: Array = []
	var holders: Array = []
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		var value: Variant = balances[str(name)]
		if not (value is int) and not (value is float):
			unreadable.append("%s resolved to no whole number" % str(name))
			continue
		holders.append("%s@%s" % [str(name), _balance_holder(after, str(name))])
	check_eq(unreadable, [],
		"and every one of the seven balances resolved to a whole number at a real "
		+ "holder, so 'nothing moved' is a claim about seven values and not about "
		+ "seven nulls")
	check_eq(holders.size(), ServerV1Combat.STORED_RESOURCE_NAMES.size(),
		"and each of the seven names named exactly one holder")
	check(holders.has("cash@playerInfo"),
		"with cash read from playerInfo, which is the holder the first version "
		+ "of this helper forgot and which made the live scenario abort")
	var moved: Array = []
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		var value: Variant = balances[str(name)]
		if not (value is int) and not (value is float):
			continue
		if int(value) != int(OBSERVED_BALANCES[str(name)]):
			moved.append(str(name))
	check_eq(moved, [],
		"and all seven stored balances are the seeded corpus's, unchanged")
	# The corpus really does place rows, so "nothing moved" is a statement about a
	# document that has something in it rather than a statement about nothing.
	var rows: Variant = (after.get("maps", []) as Array)[0]
	check(rows is Dictionary and (rows as Dictionary).has("items"),
		"the disposable save does carry a map with placements")
	if rows is Dictionary and (rows as Dictionary).has("items"):
		check((rows as Dictionary)["items"].size() > 0,
			"and those placements are still there, untouched")
	print("[test] live-server-v1-combat-diff leaves=%d ledger_keys=%d placed_rows=%d"
		% [difference.size(), _sorted_keys(ledger).size(),
			(rows as Dictionary)["items"].size() if rows is Dictionary
				and (rows as Dictionary).has("items") else -1])

	# The refusals reachable **from this facade**. The preserved branch's own
	# destruction shape is deliberately absent: `_combat_intent_body` forwards two
	# fields, so this client cannot send it, and it is covered only by the
	# observed fixture and by `apps/server-v1/tests/test_combat.py`.
	_check_live_refusal(await api.combat_town("no-such-player", "resolve", LIVE_UNIT),
		"unknown_player", "a player with no save document")
	_check_live_refusal(await api.combat_town(player_id, "resolve", "1001"),
		"malformed_request", "an identity that is not a whole number")
	_check_live_refusal(await api.combat_town(player_id, "resolve", LIVE_BUILDING),
		"unaddressable_row", "a committed building id offered as a unit")
	_check_live_refusal(await api.combat_town(player_id, "resolve", 0),
		"unaddressable_row", "the integer zero, which is not clamped")


func _check_live_refusal(answer: Variant, expected_code: String,
		label: String) -> void:
	if not (answer is ServerV1Combat.CombatAuthorityResult):
		fail("%s must answer v1's typed result" % label)
		return
	var typed: ServerV1Combat.CombatAuthorityResult = answer
	check(not typed.ok, "%s is refused" % label)
	if typed.error_code != expected_code:
		check(false, "%s is refused by v1's own code (saw %s: %s)"
			% [label, typed.error_code, typed.error_message])
	else:
		check(true, "%s is refused by v1's own code" % label)
	print("[test] live-server-v1-combat-refusal code=%s" % typed.error_code)
	check(typed.combat == null, "%s carries no addressing block" % label)
	check(typed.resources_after == null,
		"%s carries no balance set, never a partial payload" % label)
	check_eq(typed.combat_fields, {}, "%s carries no committed columns" % label)
	check_eq(typed.rows_destroyed, 0, "%s carries no destruction figure" % label)
	check(typed.error_message != "",
		"%s explains itself rather than answering with a bare code" % label)


# --- evidence ------------------------------------------------------------------


## The deterministic report, written only when `--report=<path>` is supplied. It
## carries no wall-clock, path or environment value, so it is byte-identical
## across runs on the same source - including its own digest, computed over the
## exact bytes written.
func _write_report() -> void:
	var path := _arg("--report=", "")
	if path == "":
		return
	var module_digests := _module_digests()
	check_eq(module_digests.size(), 2,
		"both delivered client modules were read for the report's digest block")
	var handle := FileAccess.open(path, FileAccess.WRITE)
	check(handle != null, "the evidence report is writable at %s" % path)
	if handle == null:
		return
	var rows := _normalized_units()
	var raw: Variant = JSON.parse_string(_repo_text(RAW_CONFIG))
	var stored_units := 0
	if raw is Dictionary and (raw as Dictionary).get("items", null) is Array:
		for entry in ((raw as Dictionary)["items"] as Array):
			if str((entry as Dictionary).get("type", "")) == "u":
				stored_units += 1
	var document := {
		"report": "combat-v1-report-v1",
		"intent": {
			"action": ServerV1Combat.ACTION,
			"protocol": ServerV1Combat.PROTOCOL,
			"combat_path": ServerV1Api.COMBAT_PATH,
			"request_fields": ["player_id", "unit_id"],
			"action_is_forwarded": false,
			"client_local_codes": [
				ServerV1Combat.CODE_UNSUPPORTED,
				ServerV1Combat.CODE_BAD_REQUEST,
			],
			"impl_return_types": IMPL_RETURN_TYPES,
			"facade_return_type": _return_type_of(
				_project_source(FACADE_SCRIPT), INTENT_METHOD),
			"facade_widening_is_the_fourth": true,
		},
		"typed_result": {
			"stored_resource_names": ServerV1Combat.STORED_RESOURCE_NAMES,
			"stored_resource_count": ServerV1Combat.STORED_RESOURCE_NAMES.size(),
			"reported_committed_columns":
				ServerV1Combat.REPORTED_COMBAT_FIELDS,
			"reported_as": "strings; the committed encoding, never read as numbers",
			"proof_checks": ServerV1Combat.PROOF_CHECKS,
			"refuses_an_enforced_gate": true,
			"refuses_a_nonzero_rows_destroyed": true,
			"refuses_a_credited_ledger": true,
			"refuses_a_changed_leaf_path": true,
			"refuses_a_moved_document": true,
			"refuses_absent_read_as_zero": true,
			"fail_closed_cases": FAIL_CLOSED_CASE_COUNT,
		},
		"observed_answers": {
			"successes": 2,
			"success_top_level_keys": OBSERVED_SUCCESS_KEYS,
			"keys_the_parser_reads_no_field_of": OBSERVED_UNREAD_KEYS,
			"refusal_conditions": _sorted_keys(OBSERVED_REFUSALS),
			"refusal_condition_count": OBSERVED_REFUSALS.size(),
			"distinct_codes": _sorted_set(_string_list(_observed_codes())),
			"captured_over": "the real ASGI stack against a disposable corpus",
			"retyped_by_hand": false,
		},
		"refusals": {
			"expected": EXPECTED_COMBAT_REFUSALS,
			"domain_named_codes": DOMAIN_NAMED_CODES,
			"declared_by_the_shared_table": DECLARED_REFUSAL_CODE_COUNT,
			"client_local_codes_are_server_codes": false,
		},
		"committed_table": {
			"source_read_by_this_client": NORMALIZED_UNITS,
			"unit_rows": rows.size(),
			"unit_id_first": 923,
			"unit_id_last": 1431,
			"absent_resurrectable_ids": ABSENT_RESURRECTABLE_IDS,
			"absent_resurrectable_count": ABSENT_RESURRECTABLE_IDS.size(),
			"nine_columns_present_on_every_row": true,
			"mirror_stores_them_as": "whole JSON numbers for eight of the nine",
			"the_ninth_column": STRING_COMBAT_COLUMN,
			"the_ninth_column_is_a_string_in_both": true,
			"served_table_stores_them_as": "strings, all nine",
			"stored_source": RAW_CONFIG,
			"stored_source_rows": 778,
			"stored_source_unit_rows": stored_units,
			"stored_source_is_unpatched": true,
			"why_the_mirror_is_read": "the stored source holds 308 unit rows "
				+ "ending at id 1306 while the loaded table v1 answered from "
				+ "holds 429 ending at 1431; a client cannot apply the content "
				+ "patches, so both figures are measured and both are recorded "
				+ "rather than one being quietly preferred",
		},
		# Every figure this line **inherited and then measured as wrong**, kept
		# rather than quietly replaced. Each entry names the wrong claim, the
		# measurement, and the consequence -- and none of them changed a
		# conclusion, which is stated rather than assumed.
		"corrections": [
			{
				"inherited": "the committed mirror stores the nine combat "
					+ "columns as integers while the served table stores them "
					+ "as strings",
				"measured": "eight of the nine are whole JSON numbers on all "
					+ "429 mirror rows; the ninth, best_against, is a JSON "
					+ "string in BOTH tables (429 of 429)",
				"consequence": "the encoding contrast is real but applies to "
					+ "eight columns, not nine; the ninth is prose in either "
					+ "form",
				"changed_a_conclusion": false,
			},
			{
				"inherited": "the typed-result module never calls int() on a "
					+ "reported value",
				"measured": "it makes 7 int() calls, wrapping destroyed, "
					+ "instant, unit, resolved, count, amount and value",
				"consequence": "the claim was false as written; the honest "
					+ "claim is that every argument is a local "
					+ "_whole_number already validated, and that is pinned "
					+ "instead",
				"changed_a_conclusion": false,
			},
			{
				"inherited": "the Python function-name scan over-counts a "
					+ "commented definition",
				"measured": "it counts none: strip_edges leaves the #, and "
					+ "the scan then requires the line to begin with 'def '",
				"consequence": "the real limitation is the opposite one -- a "
					+ "def at the START of a docstring line IS counted -- and "
					+ "that is what is pinned now",
				"changed_a_conclusion": false,
			},
			{
				"inherited": "the observed unaddressable answer lists the "
					+ "committed unit ids in ascending order",
				"measured": "it lists them in the committed mirror's own row "
					+ "order, which is not sorted; sorting either side yields "
					+ "39 positional disagreements",
				"consequence": "the check is now element-for-element "
					+ "equality against the committed file order, which is "
					+ "stronger than set equality",
				"changed_a_conclusion": false,
			},
			{
				"inherited": "the combat route is the fourth route, so it "
					+ "belongs last in the startup banner",
				"measured": "run.py prints sorted(ROUTES), and the sorted "
					+ "order is collect, collection, COMBAT, magic",
				"consequence": "the harness and the suite both place combat "
					+ "third; the banner check compares a whole list, so a "
					+ "wrong order fails a passing phase",
				"changed_a_conclusion": false,
			},
			{
				"inherited": "the typed result has a function named _mapping",
				"measured": "the delivered module's _mapping stringified "
					+ "every report value, turning destruction.applied into "
					+ "the string 'false' -- so its own boolean refusal check "
					+ "raised an engine error and NO real answer could be "
					+ "accepted",
				"consequence": "renamed _report_block and made kind-"
					+ "preserving; two chained % operations in the same "
					+ "module were also runtime-only failures, found by the "
					+ "fail-closed walk and now guarded mechanically",
				"changed_a_conclusion": true,
			},
			{
				"inherited": "an answer may report a changed leaf path or a "
					+ "document that moved and still parse",
				"measured": "the delivered parser accepted a non-empty "
					+ "leaf_paths_changed and a document_unchanged of false",
				"consequence": "both are now refused; they are reports of a "
					+ "mutation this route has no write path for, and a "
					+ "success whose own fields contradicted it",
				"changed_a_conclusion": true,
			},
			{
				"inherited": "two fail-closed cases exercised the absent-key "
					+ "gate rules",
				"measured": "both were applied to the unit-1001 answer, where "
					+ "present is true: one was a no-op and one was a "
					+ "legitimate false verdict on a PRESENT key",
				"consequence": "replaced with a null committed value on a "
					+ "present key, and a seven-case family built on the "
					+ "absent-key answer where the rules actually bite",
				"changed_a_conclusion": false,
			},
		],
		"claims": {
			"client_computes_damage": false,
			"client_computes_a_destruction_count": false,
			"client_evaluates_a_gate": false,
			"client_credits_a_ledger": false,
			"client_relates_two_reported_values": false,
			"client_filters_an_identity": false,
			"unsupported_intent_touches_transport": false,
			"parity_with_legacy_claimed": false,
		},
		# Each claim names the check that fails when it stops being true, so the
		# block above reads as a table of guards rather than as prose.
		"enforced_by": {
			"client_computes_damage":
				"_check_no_client_arithmetic (guard A, empty exception list) + "
				+ "_check_absent_derivation_helpers + "
				+ "_check_domain_reserved_stems + "
				+ "_check_fail_closed (the derived-damage cases)",
			"client_computes_a_destruction_count":
				"_check_intent_body + _check_absent_derivation_helpers + "
				+ "_check_domain_inventory + _check_fail_closed "
				+ "(the derived-destruction-count cases)",
			"client_evaluates_a_gate":
				"_check_no_line_compares_two_reported_values + "
				+ "_check_fail_closed (the enforced-gate cases)",
			"client_credits_a_ledger":
				"_check_fail_closed (the ledger_credited case) + "
				+ "_check_live (the empty ledger assertion)",
			"client_relates_two_reported_values":
				"_check_no_line_compares_two_reported_values (containment + "
				+ "the operator-gated pair rule, with a positive control)",
			"client_filters_an_identity":
				"_check_intent_body (two fields, and the action parameter "
				+ "never reaching the body)",
			"unsupported_intent_touches_transport":
				"test_server_v1.gd; this suite asserts the intent LEFT its "
				+ "unsupported table (_check_unsupported_intent_left_the_table)",
			"parity_with_legacy_claimed":
				"not a claim; v1 is new authority and the legacy branch's "
				+ "outcome is client-dictated, so there is no parity to claim",
		},
		# **Transcribed, not executed here.** This suite cannot run a probe: no
		# `OS.execute`, no file write, no `await`, no engine call. The table
		# records an external harness run against the bytes named in `modules`,
		# and the row counts are MEASURED `[test] FAIL` line counts, not
		# non-zero exit codes - a parse error would also exit non-zero and would
		# prove nothing. `asserted_in_run` below says which half is asserted here
		# and which half is only transcribed.
		"injection_probes": {
			"asserted_in_run": [
				"the pinned whole function inventories, as data",
				"the reserved-stem predicate, by planted positive and "
					+ "stem-free controls",
				"the Python name scan's own limitations, by four "
					+ "hand-built strings",
			],
			"transcribed_from_external_harness_run": [
				{"probe": "client destruction_count_for(unit)",
				 "file": "server_v1_combat_result.gd",
				 "borrows_reserved_stem": true, "fail_lines": 3},
				{"probe": "client honor_payout(honor) -- SUFFIXED helper",
				 "file": "server_v1_combat_result.gd",
				 "borrows_reserved_stem": true, "fail_lines": 3},
				{"probe": "client column_pick(row) -- borrows NO stem",
				 "file": "server_v1_combat_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 2},
				{"probe": "domain destruction_count_for()",
				 "file": "server_v1_combat.py",
				 "borrows_reserved_stem": true, "fail_lines": 4},
				{"probe": "domain honor_payout_x() -- SUFFIXED helper",
				 "file": "server_v1_combat.py",
				 "borrows_reserved_stem": true, "fail_lines": 3},
				{"probe": "domain column_pick() -- borrows NO stem",
				 "file": "server_v1_combat.py",
				 "borrows_reserved_stem": false, "fail_lines": 2},
			],
			"measured_total_fail_lines": 17,
			"every_probe_reported_at_least_one_fail_line": true,
			"every_restore_byte_identical": true,
			"which_guard_is_the_real_gate":
				"the pinned whole inventory. The stem-free probes score LOWER "
				+ "(2) than the stem-bearing ones (3-4), because the stem scan "
				+ "adds a second independent detection - so the reserved-stem "
				+ "check is the belt and the inventory is the gate, which is the "
				+ "shape godot-friends measured and this line reproduces",
		},
		"limits": {
			"legacy_command": "end_attack",
			"legacy_branch": "command.py:862-875",
			"legacy_destruction_count_is_client_dictated": true,
			"legacy_ledger_helper": "engine.py:149-170",
			"damage_rule_is_derived": false,
			"destruction_count_is_derived": false,
			"gate_rule_is_derived": false,
			"ledger_rule_is_derived": false,
			"fixture_is_a_captured_legacy_oracle": false,
			"fixtures_are_observed_v1_answers": true,
			"live_phase_seeds_nothing": true,
			"live_phase_expects_a_save_mutation": false,
			"live_phase_asserts_an_empty_document_diff": true,
			"branch_wire_shape_is_client_reachable": false,
			"v1_routes_delivered_total": 4,
			"windowed_capture": false,
			"pixel_parity": false,
			"client_sees_a_before_state": false,
			"python_name_scan_over_counts_a_comment": true,
			"team_gate_row_list_unexercised_live": true,
			"resurrectable_gate_zero_unexercised_live": true,
		},
		# Both delivered modules' raw digests, and a MEASURED line-ending flag.
		"modules": module_digests,
		"modules_are_pure_lf": _modules_are_pure_lf(),
	}
	handle.store_string(JSON.stringify(document, "\t"))
	handle = null
	# The digest is computed over the bytes just written, by reading them back,
	# so it describes this file on disk rather than a re-serialisation of an
	# in-memory structure - which is how a report's own digest can drift from
	# the artifact it is supposed to identify.
	var written := FileAccess.get_file_as_bytes(path)
	info("report bytes %d, sha256 %s" % [written.size(), _sha256_of(written)])


# --- helpers -------------------------------------------------------------------


## Every one of the seven stored balances resolves at a real holder in the
## COMMITTED corpus, hermetically.
##
## This check exists because the live scenario's own file-level half was never
## actually executed by the first version of this suite, and nothing caught it
## except a battery-wide engine-error guard. `_stored_balances` read `maps[0]`
## and `privateState` and returned `null` for **`cash`**, which is stored at
## `playerInfo.cash`; the caller evaluated `int(null)`, a nonexistent
## constructor, which ABORTS the function; and `test_base.gd` records a function
## abort as a **pass**. The live phase therefore printed
## `PASS checks=25` and proved nothing at all past the typed marker - and
## `verify-boot.ps1` is what surfaced it, because it treats any `^ERROR:` line
## as a battery failure. A defect that only a battery-wide guard can see is a
## defect the suite should be able to see on its own, so the holder set is
## pinned here over the committed document, before any live phase runs.
func _check_balance_holders_resolve_over_the_committed_corpus() -> void:
	var document := _read_committed_corpus()
	check(document.size() > 0,
		"the committed fresh-player corpus is readable from the repository root")
	if document.size() == 0:
		return
	var balances := _stored_balances(document)
	var unreadable: Array = []
	var resolved: Array = []
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		var value: Variant = balances[str(name)]
		var holder := _balance_holder(document, str(name))
		if holder == "" or not (value is int) and not (value is float):
			unreadable.append("%s -> holder %r value %s"
				% [str(name), holder, "absent" if holder == "" else str(type_string(value))])
			continue
		resolved.append("%s@%s" % [str(name), holder])
	check_eq(unreadable, [],
		"all seven stored balances resolve at a real holder over the committed "
		+ "corpus, so 'no resource moved' can never be a claim about seven nulls")
	check_eq(resolved.size(), ServerV1Combat.STORED_RESOURCE_NAMES.size(),
		"and each of the seven names names exactly one holder")
	check(resolved.has("cash@playerInfo"),
		"specifically cash@playerInfo, which is the holder a maps[0]-and-"
		+ "privateState-only reader misses and the recorded live-path defect")
	check(resolved.has("mana@privateState")
			and resolved.has("gold@maps[0]"),
		"and mana@privateState and gold@maps[0], so the holder set is the three "
		+ "the server's own STORED_RESOURCE_PATHS declares and not two of them")
	# The server's own table is the authority for which holder each name lives
	# at, so the client's holder list is cross-checked against it rather than
	# being a second hand-maintained copy of the same fact.
	var domain := _repo_text(REPOSITORY_MODULE)
	var pairs: Array = []
	var pair_scan := RegEx.new()
	# `maps[0]` entries spell three elements ("maps", 0, "gold"); `cash` and
	# `mana` spell two ("playerInfo", "cash"), so the middle index is OPTIONAL
	# rather than required. The first version required it and matched exactly
	# the five map resources, reporting "5" - and it did so as a FAIL line,
	# which is the whole reason this check exists: an under-count surfaces
	# rather than reading as a pass.
	#
	# The comparison is over the CONTAINER, on both sides. `_balance_holder`
	# above answers with the container it found the name in (`maps[0]`,
	# `playerInfo`, `privateState`), so the server-side table is reduced from
	# its dotted ("playerInfo", "cash") form to the same container name. The
	# first version appended the field name too and compared
	# `cash@playerInfo.cash` against the client's `cash@playerInfo`, which
	# disagreed on SPELLING while the two lists agreed on substance - so the
	# check failed on the two resources that are NOT in `maps[0]`, the
	# precise pair this whole comparison exists to cover. Reducing to the
	# container keeps the teeth: a genuinely different holder still fails.
	pair_scan.compile(
		'"(xp|gold|wood|oil|steel|cash|mana)":\\s*\\("([^"]+)"(?:,\\s*\\d+)?(?:,\\s*"([^"]+)")?\\s*\\)')
	var found: RegExMatch = pair_scan.search(domain)
	while found != null:
		var container := str(found.get_string(2))
		if container == "maps":
			container = "maps[0]"
		pairs.append("%s@%s" % [str(found.get_string(1)), container])
		found = pair_scan.search(domain, found.get_end())
	check_eq(pairs.size(), ServerV1Combat.STORED_RESOURCE_NAMES.size(),
		"the server's own stored-resource table declares one holder per name (%d)"
			% pairs.size())
	var disagreeing: Array = []
	for entry in pairs:
		if not resolved.has(str(entry)):
			disagreeing.append(str(entry))
	check_eq(disagreeing, [],
		"and every one of those declared holders is the container THIS client "
		+ "read from, so the two lists agree rather than merely both being "
		+ "complete")


func _read_committed_corpus() -> Dictionary:
	var path := COMBAT_SCRIPT_PATHS.repo_root().path_join("tests/saves/fresh-player.json")
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return {}
	return parsed as Dictionary


func _module_digests() -> Dictionary:
	var out: Dictionary = {}
	for relative in DELIVERED_MODULES:
		var bytes := FileAccess.get_file_as_bytes(
			COMBAT_SCRIPT_PATHS.project_dir().path_join(str(relative)))
		out[str(relative)] = {
			"raw_sha256": _sha256_of(bytes),
			"pure_lf": _is_pure_lf(bytes),
			"bytes": bytes.size(),
		}
	return out


func _sha256_of(bytes: PackedByteArray) -> String:
	# `String(raw_bytes)` does not exist on this engine -- it is a parse error,
	# not a runtime one -- so the text is assembled byte by byte and hashed as
	# text. That is correct here because the flag next to it records whether the
	# bytes are pure LF, and the hash is defined over the text form of those
	# exact bytes.
	var text := ""
	for byte in bytes:
		text += String.chr(int(byte))
	return text.sha256_text()


func _is_pure_lf(bytes: PackedByteArray) -> bool:
	for index in bytes.size():
		if bytes[index] == 13:
			return false
	return true


func _modules_are_pure_lf() -> bool:
	for relative in DELIVERED_MODULES:
		if not _is_pure_lf(FileAccess.get_file_as_bytes(
				COMBAT_SCRIPT_PATHS.project_dir().path_join(str(relative)))):
			return false
	return true


## Every leaf of a JSON document, keyed by its slash path. Used to compare the
## two observed successes leaf by leaf rather than by `==`, because the question
## is not "are they different" but "**where** are they different".
func _collect_leaves(value: Variant, prefix: String, out: Dictionary) -> void:
	if (value is Dictionary) and (value as Dictionary).size() > 0:
		var left: Dictionary = value as Dictionary
		for key in _sorted_set(_string_list(left.keys())):
			_collect_leaves(left[str(key)],
				("%s/%s" % [prefix, str(key)]).lstrip("/"), out)
		return
	if (value is Array) and (value as Array).size() > 0:
		var right: Array = value as Array
		for index in range(right.size()):
			_collect_leaves(right[index],
				("%s/%d" % [prefix, index]).lstrip("/"), out)
		return
	out[prefix] = value


func _leaf_difference(left: Dictionary, right: Dictionary) -> Array:
	var out: Array = []
	var keys := _sorted_set(_string_list(left.keys()) + _string_list(right.keys()))
	for key in keys:
		var in_left: bool = left.has(str(key))
		var in_right: bool = right.has(str(key))
		if in_left != in_right:
			out.append(str(key))
			continue
		if not _json_equal(left[str(key)], right[str(key)]):
			out.append(str(key))
	return out


func _json_equal(left: Variant, right: Variant) -> bool:
	return JSON.stringify(left) == JSON.stringify(right)


## The dead-hero ledger, read out of the parsed document.
func _dead_heroes(document: Dictionary) -> Dictionary:
	var state: Variant = document.get("privateState", null)
	if not (state is Dictionary):
		return {}
	var ledger: Variant = (state as Dictionary).get("deadHeroes", null)
	if not (ledger is Dictionary):
		return {}
	return ledger as Dictionary


## The seven stored balances, read out of the parsed document.
##
## They live in **three** places, not two: five under `maps[0]`, `mana` under
## `privateState`, and **`cash` under `playerInfo`** - the one that is easy to
## miss, because `cash` is also the one resource a player thinks of as a map
## value. This helper's first version read `maps[0]` and `privateState` only and
## left `cash` as `null`, and the caller then evaluated `int(null)`, which is a
## **nonexistent constructor** in Godot 4 and ABORTS the function. `test_base.gd`
## records a function abort as a **pass**, so the live scenario reported
## `PASS checks=25` with the whole file-level half of its claim never having run.
## The first discovery of that was `verify-boot.ps1`'s `^ERROR:`-is-a-failure
## guard, not any check in this suite - which is the strongest argument in this
## repository for treating an engine error line as a battery failure.
##
## The holder list is therefore all three, and `_stored_balances` records which
## holder each name came from so the caller can prove it found every one rather
## than counting a `null` as "unchanged".
const BALANCE_HOLDERS := ["maps[0]", "privateState", "playerInfo"]


func _balance_holder(document: Dictionary, name: String) -> String:
	for holder in BALANCE_HOLDERS:
		var container: Variant = null
		if holder == "maps[0]":
			var maps: Variant = document.get("maps", null)
			if (maps is Array) and (maps as Array).size() > 0:
				container = (maps as Array)[0]
		else:
			container = document.get(holder, null)
		if (container is Dictionary) and (container as Dictionary).has(name):
			return holder
	return ""


func _stored_balances(document: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	var first_map: Variant = null
	var maps: Variant = document.get("maps", null)
	if (maps is Array) and (maps as Array).size() > 0:
		first_map = (maps as Array)[0]
	var private: Variant = document.get("privateState", null)
	var info: Variant = document.get("playerInfo", null)
	for name in ServerV1Combat.STORED_RESOURCE_NAMES:
		var value: Variant = null
		if (first_map is Dictionary) and (first_map as Dictionary).has(str(name)):
			value = (first_map as Dictionary)[str(name)]
		elif (private is Dictionary) and (private as Dictionary).has(str(name)):
			value = (private as Dictionary)[str(name)]
		elif (info is Dictionary) and (info as Dictionary).has(str(name)):
			value = (info as Dictionary)[str(name)]
		out[str(name)] = value
	return out


func _read_save(path: String) -> Dictionary:
	var text := FileAccess.get_file_as_string(path)
	if text == "":
		return {}
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		return {}
	return parsed as Dictionary


## Every leaf path whose value differs between two parsed JSON documents, with
## `added`, `removed` and `changed` kept distinct. For this route the answer is
## the empty list, and the distinction is kept anyway so a future mutation would
## say which of the three it was rather than reporting a single "differs".
func _touched_leaf_paths(before: Variant, after: Variant) -> Array:
	var out: Array = []
	_walk_difference(before, after, "", out)
	return out


func _walk_difference(before: Variant, after: Variant, prefix: String,
		out: Array) -> void:
	if (before is Dictionary) and (after is Dictionary):
		var left: Dictionary = before as Dictionary
		var right: Dictionary = after as Dictionary
		for key in _sorted_set(_string_list(left.keys())):
			var path := "%s/%s" % [prefix, str(key)]
			if not right.has(str(key)):
				out.append({"path": path, "kind": "removed"})
			else:
				_walk_difference(left[str(key)], right[str(key)], path, out)
		for key in _sorted_set(_string_list(right.keys())):
			if not left.has(str(key)):
				out.append({"path": "%s/%s" % [prefix, str(key)],
					"kind": "added"})
		return
	if (before is Array) and (after is Array):
		var index := 0
		var right: Array = after as Array
		for entry in (before as Array):
			var path := "%s/%d" % [prefix, index]
			if index >= right.size():
				out.append({"path": path, "kind": "removed"})
			else:
				_walk_difference(entry, right[index], path, out)
			index += 1
		while index < right.size():
			out.append({"path": "%s/%d" % [prefix, index], "kind": "added"})
			index += 1
		return
	if not _json_equal(before, after):
		out.append({"path": prefix, "kind": "changed"})


## The normalized committed unit mirror, parsed once.
func _normalized_units() -> Array:
	var parsed: Variant = JSON.parse_string(_repo_text(NORMALIZED_UNITS))
	var rows: Array = []
	if parsed is Array:
		rows = parsed as Array
	return rows


## One committed unit row by its committed id, or an empty dictionary.
func _committed_unit(legacy_id: int) -> Dictionary:
	for entry in _normalized_units():
		if str((entry as Dictionary).get("legacy_id", "")) == str(legacy_id):
			return entry as Dictionary
	return {}


## The committed name of a **building** id, read from the committed buildings
## package. Returns the empty string when the id names no committed building, so a
## caller that asserts on it cannot pass on an id that resolves to nothing.
func _committed_building_name(legacy_id: int) -> String:
	var parsed: Variant = JSON.parse_string(_repo_text(NORMALIZED_BUILDINGS))
	var rows: Array = []
	if parsed is Dictionary:
		rows = (parsed as Dictionary).get("buildings", []) as Array
	elif parsed is Array:
		rows = parsed as Array
	for entry in rows:
		var row: Dictionary = entry
		if str(row.get("legacy_id", "")) == str(legacy_id):
			return str(row.get("name", ""))
	return ""


## Every leaf path of the dictionary literal a line returns, read structurally so
## a hand-listed key set could not drift from the code.
func _mapping_literal_keys(text: String) -> Array:
	var out: Array = []
	for part in text.split(","):
		var piece := str(part).strip_edges()
		if piece.length() < 2:
			continue
		var quote := piece.substr(0, 1)
		if quote != "\"" and quote != "'":
			continue
		var close := piece.find(quote, 1)
		if close == -1:
			continue
		var tail := piece.substr(close + 1).strip_edges()
		if not tail.begins_with(":"):
			continue
		out.append(piece.substr(1, close - 1))
	return _sorted_set(out)


## A deep copy of `source` with one nested value replaced. Both dictionaries and
## arrays are walked, so a proof entry can be mutated as well as a report block.
func _put(source: Variant, path: Array, value: Variant) -> Variant:
	var out: Variant = source.duplicate(true)
	var node: Variant = out
	for index in range(path.size() - 1):
		node = _member(node, path[index])
	_set_member(node, path[path.size() - 1], value)
	return out


## A deep copy of `source` with one nested key removed.
func _dropped(source: Variant, path: Array) -> Variant:
	var out: Variant = source.duplicate(true)
	var node: Variant = out
	for index in range(path.size() - 1):
		node = _member(node, path[index])
	_erase_member(node, path[path.size() - 1])
	return out


func _member(node: Variant, key: Variant) -> Variant:
	if node is Dictionary:
		return (node as Dictionary)[str(key)]
	if node is Array:
		return (node as Array)[int(key)]
	return null


func _set_member(node: Variant, key: Variant, value: Variant) -> void:
	if node is Dictionary:
		(node as Dictionary)[str(key)] = value
	elif node is Array:
		(node as Array)[int(key)] = value


func _erase_member(node: Variant, key: Variant) -> void:
	if node is Dictionary:
		(node as Dictionary).erase(str(key))
	elif node is Array:
		var index := int(key)
		if index >= 0 and index < (node as Array).size():
			(node as Array).remove_at(index)


## Every `RefusalCode.NAME: status,` row of the shared table, as
## `{name: status}`, recognised structurally rather than by listing the codes
## here: the `RefusalCode.` prefix, an identifier, a colon, a three-digit integer
## and a comma.
func _refusal_statuses(source: String) -> Dictionary:
	var out: Dictionary = {}
	for line in source.split("\n"):
		if not _looks_like_status_row(str(line)):
			continue
		var candidate := str(line).strip_edges()
		const PREFIX := "RefusalCode."
		var colon := candidate.find(":")
		out[candidate.substr(PREFIX.length(), colon - PREFIX.length())] = int(
			candidate.substr(colon + 1).strip_edges().trim_suffix(","))
	return out


func _looks_like_status_row(line: String) -> bool:
	if not line.begins_with("    "):
		return false
	var candidate := line.strip_edges()
	const PREFIX := "RefusalCode."
	if not candidate.begins_with(PREFIX):
		return false
	var colon := candidate.find(":")
	if colon < PREFIX.length() + 1:
		return false
	var name := candidate.substr(PREFIX.length(), colon - PREFIX.length())
	for index in name.length():
		if not (name[index] == "_" or name[index].is_valid_identifier()):
			return false
	var tail := candidate.substr(colon + 1).strip_edges()
	if not tail.ends_with(","):
		return false
	tail = tail.substr(0, tail.length() - 1).strip_edges()
	if tail.length() != 3 or not tail.is_valid_int():
		return false
	return true


## The distinct codes the observed refusals resolve to, read out of the fixture
## rather than listed, so the report cannot disagree with the checks.
func _observed_codes() -> Array:
	var out: Array = []
	for label in OBSERVED_REFUSALS:
		out.append(str((OBSERVED_REFUSALS[label] as Dictionary)["code"]))
	return out


## The number of `%s`/`%d`/`%f` conversions in a format operand. Counted with a
## character walk rather than a RegEx because the operand is GDScript source that
## also contains escaped quotes, and because a scan is easier to state exactly
## than the alternation would be.
func _placeholder_count(operand: String) -> int:
	var found := 0
	var index := 0
	while index < operand.length():
		if operand[index] != "%":
			index += 1
			continue
		if index + 1 < operand.length() and operand[index + 1] == "%":
			index += 2
			continue
		if index + 1 < operand.length() and operand[index + 1] in ["s", "d", "f"]:
			found += 1
			index += 2
			continue
		index += 1
	return found


func _project_source(relative: String) -> String:
	var path := COMBAT_SCRIPT_PATHS.project_dir().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## A repository-relative file's text, or "" when unreadable. Used for the Python
## service modules, the committed content and the live harness, none of which are
## inside the Godot project.
func _repo_text(relative: String) -> String:
	var path := COMBAT_SCRIPT_PATHS.repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## Every `RefusalCode.NAME` a Python source names, as a list. A substring scan,
## not a parse - the same recorded limitation as `_python_function_names`, and
## the safe direction here because an over-count fails the two-way pin rather
## than hiding a newly added code.
func _named_refusal_members(source: String) -> Array:
	var out: Array = []
	var rest := source
	const PREFIX := "RefusalCode."
	while true:
		var at := rest.find(PREFIX)
		if at == -1:
			break
		rest = rest.substr(at + PREFIX.length())
		var tail := ""
		for index in rest.length():
			var character := rest.substr(index, 1)
			if character == "_" or character.is_valid_identifier():
				tail += character
				continue
			break
		if tail != "":
			out.append(tail)
	return out


## Every `def` name a Python source declares: `def name(` and `async def name(`
## at the start of a line after stripping indentation. **A line scan, not a parse**
## -- see `_check_python_name_scan_finds_planted_defs`, which proves what it finds
## and records what it over-counts.
func _python_function_names(source: String) -> Array:
	var out: Array = []
	for line in source.split("\n"):
		var candidate := str(line).strip_edges()
		if candidate.begins_with("async def "):
			candidate = candidate.substr("async ".length())
		if not candidate.begins_with("def "):
			continue
		var rest := candidate.substr("def ".length())
		var open := rest.find("(")
		if open == -1:
			continue
		out.append(rest.substr(0, open).strip_edges())
	return out


func _return_type_of(body: String, method: String) -> String:
	if body == "":
		return ""
	var lines := body.split("\n")
	for index in lines.size():
		var line := str(lines[index]).strip_edges()
		if not line.begins_with("func "):
			continue
		if not _names(line, method):
			continue
		var whole := line
		var probe := index + 1
		while probe < lines.size() and _has_no_return_type(whole):
			whole += " " + str(lines[probe]).strip_edges()
			probe += 1
		var at := whole.find("->")
		if at == -1:
			return ""
		var tail := whole.substr(at + 2).strip_edges()
		return tail.substr(0, tail.find(":")).strip_edges()
	return ""


func _names(signature: String, method: String) -> bool:
	var open := signature.find("(")
	if open == -1:
		return false
	return signature.substr(0, open).strip_edges() == "func %s" % method


func _has_no_return_type(whole: String) -> bool:
	var at := whole.find("->")
	if at == -1:
		return true
	return not whole.substr(at + 2).contains(":")


## Two projections of a GDScript source, from **one** two-state lexer.
##
## `_code_only` blanks `#` comments **and** string-literal contents.
## `_comment_free` blanks comments and **keeps** literals.
##
## Both are needed and neither can serve the other, and this suite needs both for
## the same reason the magic suite did. An operator scan must not see the `//`
## inside `preload("res://scripts/gameapi/boot_data.gd")`, while the
## containment guard must be able to see `"attack"` - a code-only projection
## erases the very names it is measuring. A single projection makes whichever
## guard it does not serve **vacuously true**, and a vacuously true guard is the
## failure mode this project has already recorded.
func _lex(body: String, keep_literals: bool) -> String:
	var out := ""
	var index := 0
	var in_string := false
	var quote := ""
	while index < body.length():
		var character := body.substr(index, 1)
		if in_string:
			# Newlines survive in both projections, so a blanked literal never
			# joins two lines into one and invents a line that is not there.
			if keep_literals or character == "\n":
				out += character
			if character == "\\":
				var escaped := body.substr(index + 1, 1)
				if keep_literals or escaped == "\n":
					out += escaped
				index += 2
				continue
			if character == quote:
				in_string = false
			index += 1
			continue
		if character == "#":
			while index < body.length() and body.substr(index, 1) != "\n":
				index += 1
			continue
		if character == "\"" or character == "'":
			in_string = true
			quote = character
			if keep_literals:
				out += character
			index += 1
			continue
		out += character
		index += 1
	return out


func _code_only(body: String) -> String:
	return _lex(body, false)


func _comment_free(body: String) -> String:
	return _lex(body, true)


func _code_lines(code: String) -> Array:
	var out: Array = []
	for line in code.split("\n"):
		out.append(str(line).rstrip("\r"))
	return out


## Every `func` name a GDScript source declares, in declaration order and
## **including duplicates**. Both `func` and `static func` are recognised: the
## typed-result module declares all fourteen of its functions `static`, and an
## inventory that only matched `func ` would report that module as declaring
## **nothing** -- a zero that looks like a pass.
func _declared_function_names(body: String) -> Array:
	var out: Array = []
	for line in _code_lines(body):
		var candidate := str(line).strip_edges()
		if candidate.begins_with("static func "):
			candidate = candidate.substr("static ".length())
		if not candidate.begins_with("func "):
			continue
		var open := candidate.find("(")
		if open == -1:
			continue
		var head := candidate.substr("func ".length(), open - "func ".length())
		out.append(head.strip_edges())
	return out


func _count_occurrences(body: String, needle: String) -> int:
	if needle == "":
		return 0
	return body.count(needle)


## A letter, digit or underscore -- the boundary a call must not sit behind.
## Spelled as an explicit set rather than a case comparison: `to_lower() !=
## to_upper()` is true for punctuation and false for every ordinary letter, which
## is precisely backwards for this purpose.
func _is_word_character(character: String) -> bool:
	if character.length() != 1:
		return false
	return "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_".contains(
		character)


## Whether `name`, case-folded, carries any reserved derivation stem. The single
## predicate both the delivered scan and its positive control use, so the control
## tests the rule the scan applies rather than a restatement of it.
func _stem_hit(name: String) -> bool:
	for stem in RESERVED_DERIVATION_STEMS:
		if name.to_lower().contains(str(stem)):
			return true
	return false


## The balanced argument of every `int(` call in `code`, as a sorted unique set.
## Literals are blanked before this runs, so an argument is always an identifier
## (or an empty string for a call with none), never an inline literal.
func _int_call_arguments(code: String) -> Array:
	var found: Array = []
	for line in _code_lines(code):
		# `print(`, `point(` and `sprint(` all contain the two characters `int(`,
		# so the call must start on a **word boundary** -- this was the reason the
		# first version of this helper returned a single empty argument.
		var text := str(line).replace("int (", "int(")
		var from := 0
		while true:
			var at: int = text.find("int(", from)
			if at == -1:
				break
			if at > 0 and _is_word_character(text.substr(at - 1, 1)):
				from = at + 4
				continue
			var depth := 0
			var argument := ""
			# Start **after** the call's own opening parenthesis. Starting at it is
			# what made the first version collect nothing: the `(` immediately
			# opened a nesting level, so every following character sat at depth 1
			# and was dropped, and the helper reported a single empty argument.
			var index: int = at + 4
			var closed := false
			while index < text.length():
				var character := text.substr(index, 1)
				if character == ")":
					if depth == 0:
						closed = true
						break
					depth -= 1
					argument += character
				elif character == "(":
					depth += 1
					argument += character
				elif character != " ":
					argument += character
				index += 1
			if closed and not found.has(argument):
				found.append(argument)
			from = at + 4
	return _sorted_set(found)


## The body of one function inside a code-only projection: from its declaration
## line to the next declaration at column zero. A missing name yields an empty
## string rather than the whole file, so a renamed function cannot silently pass
## a scan meant for it.
func _slice_function(code: String, name: String) -> String:
	var lines := _code_lines(code)
	var out: Array = []
	var collecting := false
	for line in lines:
		var text := str(line)
		if not collecting:
			if text.begins_with("static func %s(" % name) \
					or text.begins_with("func %s(" % name):
				collecting = true
				out.append(text)
			continue
		if text.begins_with("static func ") or text.begins_with("func "):
			break
		out.append(text)
	return "\n".join(PackedStringArray(out))


func _difference(left: Array, right: Array) -> Array:
	var out: Array = []
	for entry in left:
		if not right.has(entry):
			out.append(entry)
	return out


func _read_keys(payload: Dictionary) -> Array:
	return _string_list(payload.keys())


func _folded_set(names: Array) -> Array:
	var out: Array = []
	for name in names:
		out.append(str(name).to_lower())
	return _sorted_set(out)


func _sorted_set(source: Array) -> Array:
	var seen: Array = []
	for entry in source:
		var name := str(entry)
		if not seen.has(name):
			seen.append(name)
	seen.sort()
	return seen


func _sorted_keys(source: Dictionary) -> Array:
	var out: Array = []
	for key in source:
		out.append(str(key))
	out.sort()
	return out


func _string_list(source: Array) -> Array:
	var out: Array = []
	for entry in source:
		out.append(str(entry))
	return out


func _int_list(source: Array) -> Array:
	var out: Array = []
	for entry in source:
		out.append(int(entry))
	return out


## A JSON number that really is a whole number. Godot decodes **every** JSON
## number as a `float`, so a mirror column committed as the integer `6` arrives
## as `6.0` and `row[name] is int` is false for it. The mirror-vs-served claim
## is therefore about the **JSON kind** (number against string) and about
## wholeness, never about GDScript's decoded type.
func _is_whole_number(value: Variant) -> bool:
	if not (value is float or value is int):
		return false
	return float(value) == floor(float(value))


func _arg(prefix: String, fallback: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return fallback

