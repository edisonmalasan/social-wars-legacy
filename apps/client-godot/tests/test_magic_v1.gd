extends "res://tests/test_base.gd"
## Server v1 **magic-counter** client suite (OpenSpec change
## `magic-price-authority`; spec: "Server v1 is reachable through the GameApi
## abstraction", "A refused v1 action moves nothing").
##
## Scenarios:
##   ""     (default, hermetic) the new typed result, the intent, the committed
##          magic table re-derived on every run, and the structural invariants
##          that keep this client from becoming a second magic economy. No
##          server, no socket.
##   live   drives `ServerV1Api.magic_town` **twice** - once per operation -
##          through the `GameApi` facade against a running `apps/server-v1`
##          service over loopback, diffing the disposable corpus save between
##          the two calls. Only `verify-boot.ps1`'s `magic-live-v1` phase runs
##          this.
##
## ## The claim this suite exists to keep
##
## **A magic counter transition is a server-authoritative answer this client
## reports and does not compute, and it costs nothing at all.** v1 reads the
## player's own recorded ledger, derives the next value, writes it, proves the
## write against the file it just wrote, and reports what it read back. This
## client sends a save identity, a magic identity and an operation, and nothing
## else.
##
## ## Why almost every check here is a refusal
##
## The other two v1 intents each charge something, and the charge is derived
## from committed content. **This one charges nothing, and that is the finding
## rather than a gap.** Four committed numeric columns exist on the ten-row
## magic table - `gold`, `cash`, `mana`, `level` - and not one of them is named
## a price; the twelve executed-legacy transactions in
## `tests/fixtures/godot-damage/` moved zero of the eight resource slots
## `engine.apply_resources` unpacks. So the client's half of design D2 is almost
## entirely negative, and a negative claim is only worth something if it is
## mechanical. It is asserted five ways:
##
## 1. `_check_intent_body` pins the request to exactly three keys and separately
##    asserts a **negative** and a **string** magic id travel verbatim, so v1
##    refuses the identity form by name instead of the client pre-filtering it
##    into `malformed_request`.
## 2. `_check_no_client_arithmetic` walks the new typed-result module and fails
##    on any scaling operator or any stored-balance member access, with an
##    **empty** exception list.
## 3. `_check_absent_derivation_helpers` refuses an invented helper by **name**
##    and by **substring**, in **both** directions, against the declared function
##    inventory of both delivered client modules - and pins that inventory whole.
## 4. `_check_domain_inventory` does the same against the **Python domain
##    module**, read from the repository at runtime rather than transcribed, so
##    an invented price helper, an invented level gate or an invented decrement
##    inside `server_v1_magic.py` fails here too.
## 5. `_check_committed_table_is_re_derived` re-reads `config/main.json` on
##    every run and **measures** that no column of the magic table is named a
##    price, rather than asserting the transcription.
##
## ## What this suite deliberately does NOT do
##
## It does not compare `before` with `after`, does not compare `at_cap` with
## `counter_after`, does not compare `player_level` with the committed `level`,
## and does not compare `requested_id` with `resolved_id`. Each of those is a
## relation **the server's own post-condition proof already established against
## the file it wrote** (`apps/server-v1/tests/test_magic.py`), and a client that
## re-checked them would hold a second implementation of the rule. They are
## carried verbatim and `_check_no_line_compares_two_reported_values` fails if
## any of them ever is.
##
## ## The line endings are measured, never asserted
##
## Every sibling module in `scripts/gameapi/` is CRLF, so the report's
## `modules_are_pure_lf` flag is measured on the bytes themselves and comes out
## `false`. `godot-market-trade` shipped a hard-coded `false` beside a true
## statement about the *checkout* rather than about the *files*; copying a field
## **and its value** across file forms is how a guard becomes a lie, so the flag
## here is a measurement and the report says so.

## This suite's own repository path, read by the self-scanning format guard.
const SUITE_REPO_PATH := "apps/client-godot/tests/test_magic_v1.gd"
const MAGIC_SCRIPT_PATHS = preload("res://scripts/package_paths.gd")
const ServerV1Api = preload("res://scripts/gameapi/server_v1_api.gd")
const ServerV1Magic = preload(
	"res://scripts/gameapi/server_v1_magic_result.gd")
const CollectSuite = preload("res://tests/test_server_v1.gd")

const API_SCRIPT := "scripts/gameapi/server_v1_api.gd"
const RESULT_SCRIPT := "scripts/gameapi/server_v1_magic_result.gd"
const FACADE_SCRIPT := "scripts/gameapi/game_api.gd"
const V0_SCRIPT := "scripts/gameapi/legacy_v0_api.gd"
const FAKE_SCRIPT := "scripts/gameapi/fake_api.gd"
const SCOPE_SCRIPT := "tests/test_project_scope.gd"
const SELF_SCRIPT := "test_magic_v1.gd"

## This line's own intent on the facade, and the two that came before it.
const INTENT_METHOD := "magic_town"
const COLLECT_SUITE_SCRIPT := "tests/test_server_v1.gd"

## The repository-relative paths this suite reads but does not deliver.
const DOMAIN_MODULE := "apps/server-v1/server_v1_magic.py"
const CONTENT_MODULE := "apps/server-v1/server_v1_content.py"
const REFUSALS_MODULE := "apps/server-v1/server_v1_refusals.py"
const RAW_CONFIG := "config/main.json"

const DELIVERED_MODULES := [RESULT_SCRIPT, API_SCRIPT]

## The concrete type each `GameApi` implementation declares for **this** line's
## intent. `GameApi.magic_town` is `Variant` for the same reason
## `collect_income` and `complete_collection_town` are: the three do not agree,
## and a facade naming one of them would be lying to the other two callers.
const IMPL_RETURN_TYPES := {
	"scripts/gameapi/fake_api.gd": "MagicFlow.MagicResult",
	"scripts/gameapi/legacy_v0_api.gd": "MagicFlow.MagicResult",
	"scripts/gameapi/server_v1_api.gd":
		"ServerV1Magic.MagicCounterResult",
}

## **Ten reserved stems for a client-side or server-side derivation.** Each is a
## name a rule that must not exist here would plausibly be given.
##
## The comparison is by **substring**, folded to lower case, in **both**
## directions, against **declared function names** rather than raw source:
## `godot-friends` measured that an exact-name check passes a helper merely
## *prefixed* with a reserved word (`roster_order_by_xp` for a reserved `order`),
## and that a case-sensitive one passes `Friend_Of`; and
## `godot-construction-assist` measured that scanning raw source makes the
## guard's own inventory text trip it unconditionally.
##
## `"price"`, `"cost"`, `"afford"`, `"charge"` are the D2 family: a rule that
## turns a committed column into a currency amount. `"level_gate"`, `"gated"`,
## `"clamp"`, `"floor"` are the D5 family: a rule that compares two reported
## numbers or bounds one. `"decrement"`, `"decrease"`, `"reduce"` are the D4
## family: a rule that writes a value other than `before + 1` or the cap.
const RESERVED_DERIVATION_STEMS := [
	"price", "cost", "afford", "charge", "level_gate", "gated",
	"clamp", "floor", "decrement", "decrease",
]

## **Six** columns of the committed magic table are numbers - measured, not
## assumed, and re-derived from the file every run so a seventh cannot arrive
## unmentioned. Design D2 named **four** of them; `id` and `target` are the
## other two, and neither is a price either, so the refusal is unchanged while
## the count is corrected. Pinning four would have been a claim about the table
## that the table itself does not support.
const NUMERIC_COLUMNS := ["cash", "gold", "id", "level", "mana", "target"]

## The four of the six a reader could mistake for a price: two stored balances, a
## resource and a level requirement. `id` and `target` are neither.
const PRICE_CANDIDATE_COLUMNS := ["gold", "cash", "mana", "level"]

const SCHEME := "http:"
const SLASHES := "//"
const ARG_PLAYER_ID := "--player-id="
const ARG_CORPUS := "--corpus="
const ARG_ENDPOINT := "--gameapi-endpoint="
const LIVE_ENDPOINT := SCHEME + SLASHES + "127.0.0.1:5057"
const LIVE_MAGIC := 1
const SAVE_SUFFIX := ".save.json"

## ## The one observed v1 success, **verbatim**
##
## Captured by running the real service over the real ASGI stack against a
## disposable corpus, then read out of the response - not composed from the
## parser's expectations. Every field the parser reads is here, including the
## five long prose sentences, because a fixture trimmed to the fields under test
## would let a parser that ignored the rest pass.
const OBSERVED_SUCCESS := {
	"result": "success",
	"action": "magic",
	"instant": 1790705901,
	"magic": {
		"requested_id": 1,
		"resolved_id": 1,
		"operation": "buy",
		"ledger_key": "1",
		"transition_id": "26b2acbb00014d7dbd83e6c434fbec29",
	},
	"counter": {
		"before": 0,
		"after": 1,
		"had_recorded_entry": false,
		"cap": 50,
		"at_cap": false,
		"cap_is": "the literal 50 in the preserved branches",
	},
	"committed": {
		"id": 1,
		"name": "AirStrike",
		"gold": 30000,
		"cash": 50,
		"mana": 8,
		"level": 38,
		"target": 2,
		"area": [5, 7, 9],
		"kind": null,
		"player_level": 1,
		"level_compared": false,
		"level_gate_enforced": false,
		"area_stored_as":
			"an embedded JSON string in the committed table",
		"kind_source": "the raw committed magics table carries no kind "
			+ "column at all, so this is None; the normalized package "
			+ "declares kind 'magic' on all ten rows, and reading that "
			+ "here would mean consulting a second artifact for a value "
			+ "the server's own table does not carry",
		"level_gate_deferred_because": "min_level has zero legacy "
			+ "occurrences and no legacy branch compares a player level "
			+ "against a committed magic level, so there is no recorded "
			+ "gate to reproduce; 0 of 33 committed documents at level 1 "
			+ "reach any magic, so enforcing one would make this route "
			+ "unexercisable on the committed corpus (design D5)",
		"price_refused_because": "no committed column is named a price, "
			+ "nothing in the eleven legacy root modules reads any of the "
			+ "four, and the twelve executed-legacy transactions in "
			+ "tests/fixtures/godot-damage/ moved zero of the eight "
			+ "resource slots engine.apply_resources unpacks (design D2)",
		"price_charged": null,
	},
	"resources_after": {
		"cash": 5, "gold": 2000, "mana": 0, "oil": 2000,
		"steel": 2000, "wood": 2000, "xp": 4,
	},
	"stored_resources_compared": [
		"cash", "gold", "mana", "oil", "steel", "wood", "xp",
	],
	"counter_after": 1,
	"ledger_after": ["1"],
	"same_transition_for_both_operations": true,
	"divergences": ["preserved_absent_key_arm_writes_zero"],
	"preserved_branch_behaviour": {
		"buy": "command.py:652-663 grows the counter with += and min(50, "
			+ "...) on the INCREMENT, so repeated purchases climb past "
			+ "the cap without limit",
		"use": "command.py:664-675 ASSIGNS min(50, before + 1), so a "
			+ "recorded counter above the cap is reduced to the cap "
			+ "rather than refused",
		"absent_key": "both branches take the else arm for an identity with "
			+ "no recorded entry and write that entry at 0, so the "
			+ "preserved server increments nothing where this slice "
			+ "writes its derived value",
		"same_number": "the preserved use arm's min(50, before + 1) is this "
			+ "slice's rule, so the two agree exactly while the recorded "
			+ "counter is at or below the cap; the preserved buy arm is "
			+ "unbounded and never agrees at or above it",
	},
	"price_charged": null,
	"protocol": "server-v1",
}

## The eight observed refusals of task 6.4, each captured the same way. The
## label is the *condition* rather than the code, because two of them resolve to
## the same code: a field in the delta vocabulary and any other unknown field
## are both `client_supplied_delta`, and a bad operation and a bad identity form
## are both `malformed_request`. Asserting the code per label is what keeps that
## collapse visible instead of accidental.
const OBSERVED_REFUSALS := {
	"unknown identity": {
		"status": 409,
		"code": "unknown_magic_id",
		"message": "magic id 11 names no row of the committed magic table, "
			+ "which holds 10 rows",
		"detail": {
			"committed_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
			"committed_rows": 10,
			"committed_table_is": "magics",
			"requested_magic_id": 11,
			"resolved_row": null,
		},
		"body": {
			"result": "refused",
			"code": "unknown_magic_id",
			"message": "magic id 11 names no row of the committed magic "
				+ "table, which holds 10 rows",
			"detail": {
				"committed_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
				"committed_rows": 10,
				"committed_table_is": "magics",
				"requested_magic_id": 11,
				"resolved_row": null,
			},
			"protocol": "server-v1",
		},
	},
	"non-canonical identity form": {
		"status": 400,
		"code": "malformed_request",
		"message": "magic_id must be an integer",
		"detail": {"addressing_field": "magic_id", "received": "str"},
		"body": {
			"result": "refused",
			"code": "malformed_request",
			"message": "magic_id must be an integer",
			"detail": {"addressing_field": "magic_id", "received": "str"},
			"protocol": "server-v1",
		},
	},
	"counter above the bound": {
		"status": 409,
		"code": "counter_above_cap",
		"message": "the recorded counter 51 for magic 2 is above the "
			+ "recorded cap 50, so no next value can be derived from it; "
			+ "the recorded counter is reported, not reduced",
		"detail": {
			"cap": 50,
			"cap_is": "the literal 50 in the preserved branches",
			"legacy_behaviour": "command.py:664-675 ASSIGNS min(50, "
				+ "before + 1), so a recorded counter above the cap is "
				+ "reduced to the cap rather than refused",
			"magic_id": 2,
			"player_id": "00000000-0000-0000-4000-8000-000000000001",
			"recorded_counter": 51,
			"rolled_back": false,
		},
		"body": {
			"result": "refused",
			"code": "counter_above_cap",
			"message": "the recorded counter 51 for magic 2 is above the "
				+ "recorded cap 50, so no next value can be derived "
				+ "from it; the recorded counter is reported, not "
				+ "reduced",
			"detail": {
				"cap": 50,
				"cap_is": "the literal 50 in the preserved branches",
				"legacy_behaviour": "command.py:664-675 ASSIGNS min(50, "
					+ "before + 1), so a recorded counter above the "
					+ "cap is reduced to the cap rather than refused",
				"magic_id": 2,
				"player_id": "00000000-0000-0000-4000-8000-000000000001",
				"recorded_counter": 51,
				"rolled_back": false,
			},
			"protocol": "server-v1",
		},
	},
	"client-supplied delta": {
		"status": 400,
		"code": "client_supplied_delta",
		"message": "a v1 request carries intent only; the field 'gold' "
			+ "dictates an outcome and is refused rather than clamped, "
			+ "coerced, or ignored",
		"detail": {"delta_fields": ["gold"], "refused_field": "gold"},
		"body": {
			"result": "refused",
			"code": "client_supplied_delta",
			"message": "a v1 request carries intent only; the field "
				+ "'gold' dictates an outcome and is refused rather "
				+ "than clamped, coerced, or ignored",
			"detail": {"delta_fields": ["gold"], "refused_field": "gold"},
			"protocol": "server-v1",
		},
	},
	"unknown request field": {
		"status": 400,
		"code": "client_supplied_delta",
		"message": "a v1 request carries intent only; the field 'price' "
			+ "dictates an outcome and is refused rather than clamped, "
			+ "coerced, or ignored",
		"detail": {"delta_fields": ["price"], "refused_field": "price"},
		"body": {
			"result": "refused",
			"code": "client_supplied_delta",
			"message": "a v1 request carries intent only; the field "
				+ "'price' dictates an outcome and is refused rather "
				+ "than clamped, coerced, or ignored",
			"detail": {"delta_fields": ["price"], "refused_field": "price"},
			"protocol": "server-v1",
		},
	},
	"operation outside the closed set": {
		"status": 400,
		"code": "malformed_request",
		"message": "operation must be one of ['buy', 'use']",
		"detail": {
			"allowed_operations": ["buy", "use"],
			"operation_field": "operation",
			"received": "burn",
		},
		"body": {
			"result": "refused",
			"code": "malformed_request",
			"message": "operation must be one of ['buy', 'use']",
			"detail": {
				"allowed_operations": ["buy", "use"],
				"operation_field": "operation",
				"received": "burn",
			},
			"protocol": "server-v1",
		},
	},
	"unknown player": {
		"status": 404,
		"code": "unknown_player",
		"message": "no save document for player "
			+ "'00000000-0000-4000-8000-0000000000ff'",
		"detail": {"player_id": "00000000-0000-4000-8000-0000000000ff"},
		"body": {
			"result": "refused",
			"code": "unknown_player",
			"message": "no save document for player "
				+ "'00000000-0000-4000-8000-0000000000ff'",
			"detail": {
				"player_id": "00000000-0000-4000-8000-0000000000ff",
			},
			"protocol": "server-v1",
		},
	},
	"unreadable ledger": {
		"status": 500,
		"code": "unreadable_state",
		"message": "save '00000000-0000-0000-4000-8000-000000000001' "
			+ "has no magic ledger object at /privateState/magics",
		"detail": {
			"cause": "unreadable_state",
			"player_id": "00000000-0000-0000-4000-8000-000000000001",
		},
		"body": {
			"result": "refused",
			"code": "unreadable_state",
			"message": "save '00000000-0000-0000-4000-8000-000000000001' "
				+ "has no magic ledger object at /privateState/magics",
			"detail": {
				"cause": "unreadable_state",
				"player_id":
					"00000000-0000-0000-4000-8000-000000000001",
			},
			"protocol": "server-v1",
		},
	},
	"unreadable ledger entry": {
		"status": 500,
		"code": "unreadable_state",
		"message": "save '00000000-0000-0000-4000-8000-000000000001' "
			+ "magic counter None is not an integer",
		"detail": {
			"cause": "unreadable_state",
			"player_id": "00000000-0000-0000-4000-8000-000000000001",
		},
		"body": {
			"result": "refused",
			"code": "unreadable_state",
			"message": "save '00000000-0000-0000-4000-8000-000000000001' "
				+ "magic counter None is not an integer",
			"detail": {
				"cause": "unreadable_state",
				"player_id":
					"00000000-0000-0000-4000-8000-000000000001",
			},
			"protocol": "server-v1",
		},
	},
}

## The **six** v1 refusal codes this line's route can answer, each paired with the
## `RefusalCode` **enum member** it is declared under, the HTTP status it maps
## to, and whether the **domain** module names it.
##
## The member pairing is not cosmetic, and is the correction
## `godot-collection-v1` already recorded: `server_v1_refusals.py` is a
## `str`-valued `Enum` and every module names `RefusalCode.X`, so a check looking
## for the lowercase wire string in the domain is looking for a literal that
## cannot appear there. The third element is **measured**, not assumed: six of
## the seven codes the domain names are this route's, and
## `client_supplied_delta` is the **request layer's** answer to a field the
## client added, refused before any domain code runs.
const EXPECTED_MAGIC_REFUSALS := {
	"unknown_magic_id": ["UNKNOWN_MAGIC_ID", 409, true],
	"counter_above_cap": ["COUNTER_ABOVE_CAP", 409, true],
	"malformed_request": ["MALFORMED_REQUEST", 400, true],
	"client_supplied_delta": ["CLIENT_SUPPLIED_DELTA", 400, false],
	"unknown_player": ["UNKNOWN_PLAYER", 404, true],
	"unreadable_state": ["UNREADABLE_STATE", 500, true],
}


## The **seven** `RefusalCode` members the domain module names, measured over the
## committed file. Six are this route's; `POST_CONDITION_VIOLATION` belongs to
## the shared four-half post-condition proof and to no single route. Pinned so a
## seventh magic code cannot land in the domain unnoticed.
const DOMAIN_NAMED_CODES := [
	"COUNTER_ABOVE_CAP", "MALFORMED_REQUEST", "POST_CONDITION_VIOLATION",
	"UNKNOWN_MAGIC_ID", "UNKNOWN_PLAYER", "UNREADABLE_CONTENT",
	"UNREADABLE_STATE",
]


func run_scenario() -> void:
	if scenario == "live":
		await _check_live()
		_write_report()
		return
	_check_observed_success_parses()
	_check_observed_refusals_parse()
	_check_fail_closed()
	_check_committed_table_is_re_derived()
	_check_intent_body()
	_check_no_client_arithmetic()
	_check_no_line_compares_two_reported_values()
	_check_absent_derivation_helpers()
	_check_domain_inventory()
	_check_domain_reserved_stems()
	_check_python_name_scan_finds_planted_defs()
	_check_magic_codes_live_in_the_magic_modules()
	await _check_facade_registration()
	_check_return_type_widening()
	_check_unsupported_intent_left_the_table()
	_check_transport_token_placement()
	_check_no_unconverted_format_arguments()
	_write_report()


# --- this suite's own source --------------------------------------------------


## Task 10.x: **no `%` format argument this suite cannot account for.**
##
## `magic-live-v1` found the real fault on the delivered bytes: a live-arm
## message was written `"and the id the server resolved" % operation` with no
## placeholder in the literal. GDScript raises `not all arguments converted
## during string formatting in operator '%'`, which aborted `_check_live`
## partway through the first operation. `test_base.gd` records a function abort
## as a PASS, so the phase still exited 0, the corpus save still mutated because
## the request had already gone out, and **every remaining live assertion simply
## never ran**. The hermetic arm cannot reach the live arm, so the fault is
## guarded at the source.
##
## Two shapes are covered, because the delivered file used both:
##
##   * `literal % operand` on one line, and
##   * `literal` on one line followed by `% operand` on the next.
##
## The needle is assembled at run time so no line of this guard contains the
## two-character sequence it looks for, which is what stops the guard scanning
## itself -- the defect shape `godot-construction-assist` measured when its
## reserved-name guard read raw source and tripped on its own inventory text.
func _check_no_unconverted_format_arguments() -> void:
	var needle := "%s%s%s" % ["\"", " ", "%"]
	var lead := "%s%s" % ["%", " "]
	var source := _comment_free(_project_source(SUITE_REPO_PATH))
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
			# Continuation form: the literal is on the previous line, which must
			# end in a quote. Anything else is a bare operand, not a format.
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
	# The predicate is proved, not trusted: a planted zero-placeholder operand
	# must be counted, and a planted one with a placeholder must not be.
	check_eq(_placeholder_count("a %s and a %d"), 2,
		"the placeholder count reads two placeholders")
	check_eq(_placeholder_count("no placeholder here"), 0,
		"and reads none from a literal that carries none")
	check_eq(_placeholder_count("a literal percent sign"), 0,
		"a bare percent sign inside a word is not a placeholder")


## The number of `%s`/`%d`/`%f` conversions in a format operand. Counted with a
## character walk rather than a RegEx because the operand is GDScript source
## that also contains escaped quotes, and because a scan is easier to state
## exactly than the alternation would be.
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


# --- the typed result --------------------------------------------------------


## The observed answer parses into every field, with the deterministic values
## checked exactly and the wall-clock one checked for shape only.
func _check_observed_success_parses() -> void:
	var parsed: Variant = ServerV1Magic.parse_magic_counter(
		OBSERVED_SUCCESS.duplicate(true))
	if not (parsed is ServerV1Magic.MagicCounterResult):
		fail("an observed v1 magic answer parses into the typed result")
		return
	var typed: ServerV1Magic.MagicCounterResult = parsed
	check(typed.ok, "the observed answer is a success")
	check_eq(typed.protocol, "server-v1", "and is stamped with v1's protocol")
	check_eq(typed.action, "magic", "and names the action that ran")
	check_eq(typed.instant, 1790705901, "and carries the recorded instant")

	check(typed.magic != null, "the addressing block is present")
	if typed.magic != null:
		check_eq(typed.magic.requested_id, 1, "and reports the id the client sent")
		check_eq(typed.magic.resolved_id, 1, "and the id the server resolved")
		check_eq(typed.magic.operation, "buy", "and the operation that ran")
		check_eq(typed.magic.ledger_key, "1", "and the ledger key it wrote")
		check_eq(typed.magic.transition_id.length(), 32,
			"and names the transition in 32 characters")
		check_eq(typed.magic.ledger_key, str(typed.magic.resolved_id),
			"the recorded ledger key is the resolved id rendered as a string")
		# And the one thing this client deliberately does **not** conclude from
		# the pair: that they are equal *because* the id resolved. That is the
		# server's decision to report; the client carries both.
		check(typed.magic.requested_id == typed.magic.resolved_id,
			"in this observed answer the two ids happen to agree")

	check_eq(typed.counter_before, 0, "the counter's before value is carried")
	check_eq(typed.counter_after, 1, "and its after value, separately")
	check(not typed.had_recorded_entry,
		"and it records that the addressed key was ABSENT")
	check_eq(typed.cap, 50, "the recorded cap literal is carried")
	check(not typed.at_cap, "and the answer reports it did not stop at the cap")
	check(typed.cap_is != "",
		"and it carries the cap's provenance sentence rather than a bare bound")
	check(typed.cap_is.find("literal") != -1,
		"and that sentence names the bound a literal")

	check(typed.committed != null, "the committed row is present")
	if typed.committed != null:
		check_eq(int(typed.committed["id"]), 1, "and is the row the id resolved to")
		check_eq(str(typed.committed["name"]), "AirStrike", "by name")
		check_eq(int(typed.committed["gold"]), 30000, "with its gold column")
		check_eq(int(typed.committed["cash"]), 50, "and its cash column")
		check_eq(int(typed.committed["mana"]), 8, "and its mana column")
		check_eq(int(typed.committed["level"]), 38, "and its level column")
		check_eq(_int_list(typed.committed["area"]), [5, 7, 9],
			"and its area, which the committed table stores as an embedded"
			+ " JSON string and v1 parses")
		check(typed.committed["kind"] == null,
			"and a null kind, because the raw table has no such column")
		check(str(typed.committed["kind_source"]) != "",
			"and the note explaining why that is null")
		check_eq(int(typed.committed["player_level"]), 1,
			"and the player's own map level, reported beside it")
		# Design D5: both levels are here, side by side, and the answer says so.
		check(typed.committed["level_compared"] == false,
			"and the server's own statement that it did not compare them")
		check(typed.committed["level_gate_enforced"] == false,
			"and that it enforced no gate")
		check(typed.committed["price_charged"] == null,
			"and the committed report's own null price")
		check(str(typed.committed["price_refused_because"]) != "",
			"and the note explaining why nothing was charged")
		check(str(typed.committed["price_refused_because"]).find("D2") != -1,
			"and that note cites design D2")

	check(typed.resources_after != null,
		"the complete stored balance set is present")
	if typed.resources_after != null:
		check_eq(int(typed.resources_after.cash), 5, "and cash is carried")
		check_eq(int(typed.resources_after.gold), 2000, "and gold is carried")
		check_eq(int(typed.resources_after.mana), 0, "and mana is carried")
		check_eq(int(typed.resources_after.oil), 2000, "and oil is carried")
		check_eq(int(typed.resources_after.steel), 2000, "and steel is carried")
		check_eq(int(typed.resources_after.wood), 2000, "and wood is carried")
		check_eq(int(typed.resources_after.xp), 4, "and xp is carried")
	check_eq(_sorted_set(_string_list(typed.stored_resources_compared)),
		_sorted_set(ServerV1Magic.STORED_RESOURCE_NAMES),
		"and the answer names exactly the seven stored resources it compared")
	check_eq(ServerV1Magic.STORED_RESOURCE_NAMES.size(), 7,
		"the stored resource set is seven: the legacy eighth slot is read"
		+ " into a local named unknown and never written")

	check_eq(_string_list(typed.ledger_after), ["1"],
		"the ledger after the transition is carried")
	check(typed.same_transition_for_both_operations,
		"the answer states that both operations share one transition")
	check_eq(_string_list(typed.divergences),
		["preserved_absent_key_arm_writes_zero"],
		"and the recorded divergence for an absent key is carried as a REASON")
	check(typed.preserved_branch_behaviour.size() >= 4,
		"and the preserved-branch behaviour table comes with it")
	check(typed.preserved_branch_behaviour.has("buy")
		and typed.preserved_branch_behaviour.has("use")
		and typed.preserved_branch_behaviour.has("absent_key")
		and typed.preserved_branch_behaviour.has("same_number"),
		"and it covers buy, use, the absent key and the agreement condition")
	check(typed.price_charged == null,
		"and the answer's own price is null, which is the line's whole finding")
	check_eq(typed.error_code, "",
		"a success carries no error code rather than an empty success marker")
	check_eq(typed.error_message, "", "and no error message")
	check_eq(typed.error_detail, {}, "and no error detail")

	# The payload is not aliased: the caller keeps this dictionary, so a shared
	# reference into a parsed payload is how a projection becomes a second
	# implementation. Mutating the source afterwards must not be visible.
	var source: Dictionary = OBSERVED_SUCCESS.duplicate(true)
	var once: Variant = ServerV1Magic.parse_magic_counter(source)
	var typed_once: ServerV1Magic.MagicCounterResult = once
	if typed_once.committed != null:
		typed_once.committed["name"] = "mutated-by-the-caller"
	var twice: Variant = ServerV1Magic.parse_magic_counter(source)
	var typed_twice: ServerV1Magic.MagicCounterResult = twice
	if typed_twice.committed != null:
		check_eq(str(typed_twice.committed["name"]), "AirStrike",
			"the parsed committed report is the caller's own dictionary")


## Every observed refusal parses, keeps v1's own code verbatim, and populates
## **nothing else**. Nine conditions, seven codes - and the collapse is asserted
## rather than left accidental.
func _check_observed_refusals_parse() -> void:
	var conditions: Array = _sorted_keys(OBSERVED_REFUSALS)
	check_eq(conditions.size(), 9,
		"task 6.4 named eight conditions; nine were observed, and the ninth is"
		+ " the ledger's own ENTRY shape rather than the ledger's shape")
	for label in conditions:
		var case: Dictionary = OBSERVED_REFUSALS[label]
		var parsed: Variant = ServerV1Magic.parse_magic_counter(
			(case["body"] as Dictionary).duplicate(true))
		if not (parsed is ServerV1Magic.MagicCounterResult):
			fail("%s must answer v1's own typed result class" % label)
			continue
		var typed: ServerV1Magic.MagicCounterResult = parsed
		check(not typed.ok, "%s is refused" % label)
		check_eq(typed.error_code, str(case["code"]),
			"%s keeps v1's own refusal code" % label)
		check_eq(typed.error_message, str(case["message"]),
			"%s keeps v1's own message" % label)
		check(typed.error_message != "",
			"%s explains itself rather than answering with a bare code" % label)
		check_eq(typed.protocol, "server-v1",
			"%s carries v1's protocol stamp" % label)
		# Nothing else. A partial success payload on a refusal is the exact
		# shape a caller would read as "the write happened but was odd".
		check(typed.magic == null, "%s carries no addressing block" % label)
		check_eq(typed.counter_before, 0, "%s names no before value" % label)
		check_eq(typed.counter_after, 0, "%s names no after value" % label)
		check(not typed.had_recorded_entry, "%s names no recorded entry" % label)
		check_eq(typed.cap, 0, "%s names no cap" % label)
		check(not typed.at_cap, "%s reports no at-cap flag" % label)
		check_eq(typed.cap_is, "", "%s carries no cap provenance" % label)
		check_eq(typed.committed, {}, "%s carries no committed row" % label)
		check(typed.resources_after == null, "%s carries no balance set" % label)
		check_eq(typed.stored_resources_compared, [],
			"%s names no compared resources" % label)
		check_eq(typed.ledger_after, [], "%s carries no ledger" % label)
		check(not typed.same_transition_for_both_operations,
			"%s claims no shared transition" % label)
		check_eq(typed.divergences, [], "%s lists no divergence reason" % label)
		check_eq(typed.preserved_branch_behaviour, {},
			"%s carries no preserved-branch table" % label)
		check(typed.price_charged == null, "%s names no price" % label)
		check_eq(typed.action, "", "%s names no action" % label)
		check_eq(typed.instant, 0, "%s names no instant" % label)

	# The detail is carried verbatim, and it is the only place the answer says
	# anything about the *request*, so it is asserted rather than assumed.
	var unknown: ServerV1Magic.MagicCounterResult = ServerV1Magic.parse_magic_counter(
		(OBSERVED_REFUSALS["unknown identity"]["body"] as Dictionary)
			.duplicate(true))
	check_eq(int(unknown.error_detail["requested_magic_id"]), 11,
		"the unknown-identity refusal echoes the id the client sent")
	check_eq(_int_list(unknown.error_detail["committed_ids"]).size(), 10,
		"and the ten committed ids it could have resolved to")
	check(unknown.error_detail["resolved_row"] == null,
		"and an explicitly null resolution, not a missing key")
	var cap: ServerV1Magic.MagicCounterResult = ServerV1Magic.parse_magic_counter(
		(OBSERVED_REFUSALS["counter above the bound"]["body"] as Dictionary)
			.duplicate(true))
	check_eq(int(cap.error_detail["recorded_counter"]), 51,
		"the above-cap refusal REPORTS the recorded counter rather than"
		+ " reducing it to the cap")
	check_eq(int(cap.error_detail["cap"]), 50, "and the cap it refused against")
	check(cap.error_detail["rolled_back"] == false,
		"and that nothing was rolled back")

	# The collapse, asserted: three distinct conditions, one code.
	var delta: Dictionary = OBSERVED_REFUSALS["client-supplied delta"]
	var unknown_field: Dictionary = OBSERVED_REFUSALS["unknown request field"]
	check_eq(str(delta["code"]), str(unknown_field["code"]),
		"a delta field and any other unknown field share one code")
	check(str(delta["detail"]["refused_field"])
		!= str(unknown_field["detail"]["refused_field"]),
		"but the detail names which field was refused, so they stay tellable")
	var form: Dictionary = OBSERVED_REFUSALS["non-canonical identity form"]
	var operation: Dictionary = OBSERVED_REFUSALS["operation outside the closed set"]
	check_eq(str(form["code"]), str(operation["code"]),
		"a bad identity form and a bad operation share one code too")


## ## The fail-closed walk, and why the case count is pinned
##
## Every case below is a real way a JSON body could arrive malformed, and every
## one must produce a **local** `bad_request` rather than a partially-populated
## success. The one that matters most is `price_charged`: a v1 answer that
## charged something would be the exact defect this line exists to refuse, so the
## parser refuses it rather than carrying it.
##
## `FAIL_CLOSED_CASE_COUNT` is declared and pinned **inside** this function, so
## the report can state the number without the two ever drifting apart.
func _check_fail_closed() -> void:
	var cases: Array = []

	cases.append(["not an object at all", "not-an-object"])
	cases.append(["an array", [1, 2, 3]])
	cases.append(["null", null])
	cases.append(["no result field", _without("result")])
	cases.append(["an unknown result field", _swapped(OBSERVED_SUCCESS,
		"result", "maybe")])
	cases.append(["a refusal with no code",
		_merged(OBSERVED_REFUSALS["unknown player"]["body"],
			{"code": ""})])
	cases.append(["a refusal whose detail is not an object",
		_merged(OBSERVED_REFUSALS["unknown player"]["body"],
			{"detail": "text"})])

	cases.append(["the wrong protocol", _swapped(OBSERVED_SUCCESS,
		"protocol", "server-v0")])
	cases.append(["no protocol", _without("protocol")])
	cases.append(["the wrong action", _swapped(OBSERVED_SUCCESS,
		"action", "collection")])
	cases.append(["no action", _without("action")])
	cases.append(["no instant", _without("instant")])
	cases.append(["a fractional instant", _swapped(OBSERVED_SUCCESS,
		"instant", 1790705901.5)])
	cases.append(["an instant as a string", _swapped(OBSERVED_SUCCESS,
		"instant", "1790705901")])

	cases.append(["no magic block", _without("magic")])
	cases.append(["a magic block that is not an object",
		_swapped(OBSERVED_SUCCESS, "magic", "magic-1")])
	cases.append(["no requested id", _swapped(OBSERVED_SUCCESS, "magic",
		_merged(OBSERVED_SUCCESS["magic"], {"requested_id": null}))])
	cases.append(["a fractional requested id", _swapped(OBSERVED_SUCCESS,
		"magic", _merged(OBSERVED_SUCCESS["magic"],
			{"requested_id": 1.5}))])
	cases.append(["no resolved id", _swapped(OBSERVED_SUCCESS, "magic",
		_merged(OBSERVED_SUCCESS["magic"], {"resolved_id": null}))])
	cases.append(["an operation outside the closed set", _swapped(
		OBSERVED_SUCCESS, "magic", _merged(OBSERVED_SUCCESS["magic"],
			{"operation": "burn"}))])
	cases.append(["a missing operation", _swapped(OBSERVED_SUCCESS, "magic",
		_merged(OBSERVED_SUCCESS["magic"], {"operation": ""}))])
	cases.append(["a ledger key that is not a string", _swapped(
		OBSERVED_SUCCESS, "magic", _merged(OBSERVED_SUCCESS["magic"],
			{"ledger_key": 1}))])
	cases.append(["an empty ledger key", _swapped(OBSERVED_SUCCESS, "magic",
		_merged(OBSERVED_SUCCESS["magic"], {"ledger_key": ""}))])
	cases.append(["no transition id", _swapped(OBSERVED_SUCCESS, "magic",
		_merged(OBSERVED_SUCCESS["magic"], {"transition_id": ""}))])

	cases.append(["no counter block", _without("counter")])
	cases.append(["a counter block that is not an object",
		_swapped(OBSERVED_SUCCESS, "counter", 50)])
	for field in ["before", "after", "cap"]:
		cases.append(["no counter %s" % field, _swapped(OBSERVED_SUCCESS,
			"counter", _merged(OBSERVED_SUCCESS["counter"], {field: null}))])
	cases.append(["a fractional counter after", _swapped(OBSERVED_SUCCESS,
		"counter", _merged(OBSERVED_SUCCESS["counter"], {"after": 1.5}))])
	cases.append(["a non-boolean recorded-entry flag", _swapped(
		OBSERVED_SUCCESS, "counter", _merged(OBSERVED_SUCCESS["counter"],
			{"had_recorded_entry": "false"}))])
	cases.append(["a non-boolean at-cap flag", _swapped(OBSERVED_SUCCESS,
		"counter", _merged(OBSERVED_SUCCESS["counter"], {"at_cap": 1}))])
	cases.append(["a cap provenance that is not a string", _swapped(
		OBSERVED_SUCCESS, "counter", _merged(OBSERVED_SUCCESS["counter"],
			{"cap_is": 50}))])

	cases.append(["no committed report", _without("committed")])
	cases.append(["a committed report that is not an object",
		_swapped(OBSERVED_SUCCESS, "committed", "row 1")])
	# **A null is the malformed shape for eight of the nine** reported fields,
	# because those are columns the committed table really has. `kind` is the
	# measured exception - the raw table carries no such column, so its null is
	# the observed value - which makes a **non-null** kind the malformed shape
	# there. The first draft used null for all nine, and for `kind` that produced
	# a case byte-identical to a valid answer: twelve cases reported "accepted as
	# a success", of which one was not malformed at all.
	for field in ServerV1Magic.REPORTED_COMMITTED_FIELDS:
		var label := "no committed %s" % str(field)
		var broken: Variant = null
		if str(field) == "kind":
			label = "a committed kind the table does not carry"
			broken = "air_strike"
		cases.append([label, _swapped(OBSERVED_SUCCESS, "committed",
			_merged(OBSERVED_SUCCESS["committed"], {field: broken}))])
	for field in ["player_level", "level_compared", "level_gate_enforced"]:
		cases.append(["no committed %s" % field, _swapped(OBSERVED_SUCCESS,
			"committed", _merged(OBSERVED_SUCCESS["committed"],
				{field: null}))])
	cases.append(["a level_compared flag that is not a boolean", _swapped(
		OBSERVED_SUCCESS, "committed", _merged(OBSERVED_SUCCESS["committed"],
			{"level_compared": "false"}))])
	cases.append(["a level gate the server claims it enforced", _swapped(
		OBSERVED_SUCCESS, "committed", _merged(OBSERVED_SUCCESS["committed"],
			{"level_gate_enforced": true}))])

	cases.append(["no balance set", _without("resources_after")])
	cases.append(["a balance set that is not an object", _swapped(
		OBSERVED_SUCCESS, "resources_after", "2000")])
	cases.append(["a partial balance set", _swapped(OBSERVED_SUCCESS,
		"resources_after", {"cash": 5, "gold": 2000})])
	cases.append(["an extra balance the server does not store", _swapped(
		OBSERVED_SUCCESS, "resources_after",
		_merged(OBSERVED_SUCCESS["resources_after"], {"energy": 50}))])
	cases.append(["a fractional balance", _swapped(OBSERVED_SUCCESS,
		"resources_after", _merged(OBSERVED_SUCCESS["resources_after"],
			{"gold": 2000.5}))])

	cases.append(["no compared-resource list",
		_without("stored_resources_compared")])
	cases.append(["a compared-resource list that is not a list", _swapped(
		OBSERVED_SUCCESS, "stored_resources_compared", "cash")])
	cases.append(["a compared-resource list naming something unstored", _swapped(
		OBSERVED_SUCCESS, "stored_resources_compared",
		["cash", "gold", "mana", "oil", "steel", "wood", "xp", "energy"])])
	cases.append(["a compared-resource list with a non-string", _swapped(
		OBSERVED_SUCCESS, "stored_resources_compared", ["cash", 7])])

	cases.append(["no counter_after", _without("counter_after")])
	cases.append(["a fractional counter_after", _swapped(OBSERVED_SUCCESS,
		"counter_after", 1.5)])
	cases.append(["no ledger", _without("ledger_after")])
	cases.append(["a ledger that is not a list", _swapped(OBSERVED_SUCCESS,
		"ledger_after", "1")])
	cases.append(["a ledger with a non-string entry", _swapped(OBSERVED_SUCCESS,
		"ledger_after", [1])])

	cases.append(["no shared-transition flag",
		_without("same_transition_for_both_operations")])
	cases.append(["a shared-transition flag that is not a boolean", _swapped(
		OBSERVED_SUCCESS, "same_transition_for_both_operations", "true")])
	cases.append(["**a shared-transition flag the server denies**", _swapped(
		OBSERVED_SUCCESS, "same_transition_for_both_operations", false)])

	cases.append(["no divergence list", _without("divergences")])
	cases.append(["a divergence list that is not a list", _swapped(
		OBSERVED_SUCCESS, "divergences", {})])
	cases.append(["a divergence list with a non-string", _swapped(
		OBSERVED_SUCCESS, "divergences", [7])])

	cases.append(["no preserved-branch table",
		_without("preserved_branch_behaviour")])
	cases.append(["a preserved-branch table that is not an object", _swapped(
		OBSERVED_SUCCESS, "preserved_branch_behaviour", "quoted")])
	for key in ["buy", "use", "absent_key", "same_number"]:
		cases.append(["no preserved-branch %s" % key, _swapped(
			OBSERVED_SUCCESS, "preserved_branch_behaviour", _merged(
				OBSERVED_SUCCESS["preserved_branch_behaviour"],
				{key: null}))])

	# The two headline cases, each named so the report can point at it.
	cases.append(["**a v1 answer that charges a price**", _swapped(
		OBSERVED_SUCCESS, "price_charged", 50)])
	cases.append(["**a v1 answer with no price_charged field at all**", _without(
		"price_charged")])

	check_eq(cases.size(), FAIL_CLOSED_CASE_COUNT,
		"the fail-closed walk covers exactly the pinned number of shapes")
	var accepted: Array = []
	for entry in cases:
		var label := str(entry[0])
		var payload: Variant = entry[1]
		var parsed: Variant = ServerV1Magic.parse_magic_counter(payload)
		if not (parsed is ServerV1Magic.MagicCounterResult):
			accepted.append("%s: no typed result at all" % label)
			continue
		var typed: ServerV1Magic.MagicCounterResult = parsed
		if typed.ok:
			accepted.append("%s: accepted as a success" % label)
			continue
		if typed.error_code != ServerV1Magic.CODE_BAD_REQUEST:
			accepted.append("%s: refused as %s rather than locally"
				% [label, typed.error_code])
			continue
		if typed.protocol != "" or typed.action != "" or typed.magic != null:
			accepted.append("%s: refused but populated" % label)
	check_eq(accepted, [],
		"every malformed shape is refused locally and populated with nothing")
	# Two cases are the finding rather than a shape, so they are checked by name
	# and the message is asserted: a caller reading the error must be able to see
	# *why* the answer was rejected.
	var priced: ServerV1Magic.MagicCounterResult = ServerV1Magic.parse_magic_counter(
		_swapped(OBSERVED_SUCCESS, "price_charged", 50))
	check(not priced.ok, "a priced v1 answer is refused")
	check(priced.error_message.find("never derives") != -1,
		"and its refusal says the route derives no price")
	var denied: ServerV1Magic.MagicCounterResult = ServerV1Magic.parse_magic_counter(
		_swapped(OBSERVED_SUCCESS, "same_transition_for_both_operations", false))
	check(not denied.ok, "an answer denying the shared transition is refused")
	check(denied.error_message.find("share one transition") != -1,
		"and its refusal says the two operations stopped being one")


# --- the committed table -----------------------------------------------------


## ## Every committed-table figure this suite states is **measured**
##
## Task 6.3 asks for exactly this, and the reason is not ceremony: the refusal
## that defines this line is "no committed column is named a price", and a
## transcribed constant asserting that would be indistinguishable from a guess
## that happened to be written down. So the raw table is re-read every run, the
## row count and the id set and the field names and the numeric columns are
## derived from it, and the claim is made about **those** derivations.
##
## The raw file is read rather than the normalized package because that is what
## `apps/server-v1` reads: `server_v1_content.py` declares
## `CONFIG_MAIN = ("config", "main.json")` and `server_v1_collection.py` does
## the same. Task 2.1 named the normalized path, and the divergence is recorded
## in `tasks.md` rather than papered over - the normalized package is verified
## independently by `packages/game-content/tools/validate_content.py`, which is
## where a normalization error should be caught.
func _check_committed_table_is_re_derived() -> void:
	var raw := _repo_text(RAW_CONFIG)
	check(raw != "", "the committed %s is readable" % RAW_CONFIG)
	if raw == "":
		return
	var document: Variant = JSON.parse_string(raw)
	if not (document is Dictionary):
		fail("%s is a JSON object" % RAW_CONFIG)
		return
	var table: Variant = (document as Dictionary).get("magics", null)
	if not (table is Array):
		fail("%s carries a `magics` array" % RAW_CONFIG)
		return
	var rows: Array = table as Array
	check_eq(rows.size(), 10, "the committed magic table holds ten rows")
	check_eq(rows.size(), ServerV1Magic.REPORTED_COMMITTED_FIELDS.size() + 1,
		"and the reported field count is the table's own field count")

	var ids: Array = []
	var fields: Array = []
	var numeric: Array = []
	for row in rows:
		if not (row is Dictionary):
			fail("every committed magic row is an object")
			return
		var entry: Dictionary = row as Dictionary
		ids.append(int(entry.get("id", -1)))
		for key in entry:
			fields.append(str(key))
			var value: Variant = entry[key]
			if value is int or value is float:
				numeric.append(str(key))
	var sorted_ids := _int_list(ids)
	check_eq(sorted_ids, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
		"the committed ids are the contiguous run 1..10")
	var sorted_fields := _sorted_set(fields)
	check(sorted_fields.has("id") and sorted_fields.has("name"),
		"the table names every row by id and by name")
	check_eq(_sorted_set(numeric), _sorted_set(NUMERIC_COLUMNS),
		"and its numeric columns are exactly the six measured from the file")
	var absent_candidates: Array = []
	for name in PRICE_CANDIDATE_COLUMNS:
		if not _sorted_set(numeric).has(str(name)):
			absent_candidates.append(str(name))
	check_eq(absent_candidates, [],
		"and the four a reader could mistake for a price - gold, cash, mana"
		+ " and level - are all among them")
	# **The claim this line exists for**, made about the derivation above.
	var price_words := ["price", "cost", "mana_cost", "cash_price", "gold_cost"]
	var named_like_a_price: Array = []
	for name in sorted_fields:
		for word in price_words:
			if str(name).find(word) != -1:
				named_like_a_price.append("%s contains %s" % [str(name), word])
	check_eq(named_like_a_price, [],
		"NO committed magic column is named a price, measured on the file"
		+ " rather than transcribed")
	# ...and every column this client reports is one the table really has, so
	# the typed result cannot claim a field the oracle does not carry.
	# The report and the table are reconciled **in both directions**: a one-way
	# check passes on a set that merely contains the other.
	var reported: Array = []
	for field in ServerV1Magic.REPORTED_COMMITTED_FIELDS:
		reported.append(str(field))
		if str(field) == "kind":
			continue
		check(sorted_fields.has(str(field)),
			"the reported committed field %s exists in the table"
			% str(field))
	var only_in_table: Array = []
	for name in sorted_fields:
		if not reported.has(str(name)):
			only_in_table.append(str(name))
	var only_in_report: Array = []
	for name in _sorted_set(reported):
		if not sorted_fields.has(str(name)):
			only_in_report.append(str(name))
	check_eq(_sorted_set(only_in_table), ["description", "img_name"],
		"the two columns the report leaves out are the two it has no claim to"
		+ " carry: the prose and the asset name")
	check_eq(_sorted_set(only_in_report), ["kind"],
		"and the one field it reports that the table lacks is `kind`, which is"
		+ " the whole of task 2.1's divergence from the normalized package")
	check(not sorted_fields.has("kind"),
		"the raw table carries no `kind` column, which is why the answer"
		+ " reports a null kind and a note")
	# The area column really is an embedded JSON string, which is why the answer
	# carries a parsed list and a sentence saying so.
	var first: Dictionary = rows[0] as Dictionary
	check(first["area"] is String,
		"the committed `area` column is stored as a JSON string, not a list")
	var area_parsed: Variant = JSON.parse_string(str(first["area"]))
	check(area_parsed is Array,
		"and it parses to the list the answer reports")
	# One recorded data point, measured: the identity the live phase uses.
	var airstrike := _row_with_id(rows, LIVE_MAGIC)
	check(airstrike != null, "magic 1 exists in the committed table")
	if airstrike != null:
		check_eq(str(airstrike["name"]), "AirStrike", "and it is AirStrike")
		check_eq(int(airstrike["cash"]), 50,
			"whose committed cash column is 50 -- the same figure as the"
			+ " counter cap, which is why it can never be read AS the cap")


func _row_with_id(rows: Array, wanted: int) -> Dictionary:
	for row in rows:
		if not (row is Dictionary):
			continue
		var entry: Dictionary = row as Dictionary
		if int(entry.get("id", -1)) == wanted:
			return entry
	return {}


# --- the intent --------------------------------------------------------------


## The request this client builds is exactly three fields. Four things are
## **not** sent and could not be smuggled even by accident: a count, a price, a
## delta and a balance.
##
## A negative and a string identity both travel **verbatim**, deliberately. A
## client that normalised them first would turn v1's named `unknown_magic_id` and
## `malformed_request` into a client-local code, which is the mistake
## `complete_collection_town` already documents avoiding for a negative
## collection id.
func _check_intent_body() -> void:
	var body: Dictionary = ServerV1Api._magic_intent_body(
		"player-1", "buy", LIVE_MAGIC)
	check_eq(_sorted_keys(body),
		["magic_id", "operation", "player_id"],
		"the v1 magic intent carries a save identity, an operation and a magic"
		+ " id, and nothing else")
	check_eq(str(body["player_id"]), "player-1", "the identity is verbatim")
	check_eq(str(body["operation"]), "buy", "the operation is verbatim")
	check_eq(int(body["magic_id"]), LIVE_MAGIC, "the magic id is verbatim")

	var forbidden: Array = []
	forbidden.append_array(ServerV1Magic.STORED_RESOURCE_NAMES)
	forbidden.append_array([
		"resources_changed", "amount", "price", "cost", "payout",
		"counter", "before", "after", "cap", "at_cap", "count",
		"level", "expected", "ledger", "instant", "target", "divergences",
	])
	for name in forbidden:
		check(not body.has(str(name)),
			"the intent carries no %s field" % str(name))
	# `magic_id` is exempt from the non-negative rule the other two routes
	# enforce, and that exemption is **measured** rather than assumed: the
	# negative and the string form both have to survive the body builder.
	var negative: Dictionary = ServerV1Api._magic_intent_body(
		"player-1", "use", -3)
	check_eq(int(negative["magic_id"]), -3,
		"a negative magic id is sent verbatim for the server to refuse")
	check_eq(_sorted_keys(negative), ["magic_id", "operation", "player_id"],
		"and a negative id changes nothing else about the request")
	var stringly: Dictionary = ServerV1Api._magic_intent_body(
		"player-1", "buy", "1")
	check_eq(str(stringly["magic_id"]), "1",
		"a string magic id is sent verbatim rather than coerced")
	var floating: Dictionary = ServerV1Api._magic_intent_body(
		"player-1", "buy", 1.0)
	check(float(floating["magic_id"]) == 1.0,
		"and a float identity travels as the float the caller gave")
	# An operation outside the closed set is **not** pre-filtered either, for
	# the same reason: v1 owns that vocabulary and names its own refusal.
	var burned: Dictionary = ServerV1Api._magic_intent_body(
		"player-1", "burn", 1)
	check_eq(str(burned["operation"]), "burn",
		"an operation outside the closed set is sent verbatim too")
	check_eq(_sorted_keys(burned), ["magic_id", "operation", "player_id"],
		"and adds no field to say it looks wrong")


# --- structural invariants ---------------------------------------------------


## ## Guard A - no scaling. Guard B - no balance is touched.
##
## The exception list here is **EMPTY**, unlike `test_server_v1.gd`'s, which must
## admit this module's two request-counter `+=` lines. A non-empty list here
## would be a fourth place to add a `+=` without noticing.
##
## The signature arrow is not an operator, so it is removed before scanning, and
## the scan runs over **code only** with comments and string literals blanked --
## so a sentence in a docstring cannot fail the guard and a string that says
## `"price_charged"` cannot satisfy it either.
func _check_no_client_arithmetic() -> void:
	var offending: Array = []
	var forbidden_operators := ["*", "/", "+=", "-=", "*=", "/="]
	for relative in [RESULT_SCRIPT]:
		var body := _project_source(relative)
		check(body != "", "%s is readable" % relative)
		if body == "":
			continue
		# **Two projections, deliberately.** The operator scan needs comments and
		# string contents gone, or `preload("res://scripts/...")` supplies its own
		# `/`. The balance scan needs literals **kept**, because the shape it
		# forbids is `body["gold"]` - a subscript whose index is a string. Reading
		# both from one projection silently makes one of the two guards
		# vacuously true, which is precisely what happened before.
		var code := _code_only(body).replace("->", "  ")
		for line in _code_lines(code):
			for operator in forbidden_operators:
				if str(line).find(operator) != -1:
					offending.append("A %s: %s (%s)"
						% [relative, str(line).strip_edges(), operator])
					break
		var literal_code := _comment_free(body).replace("->", "  ")
		for name in ServerV1Magic.STORED_RESOURCE_NAMES:
			if literal_code.find(".%s" % str(name)) != -1:
				offending.append("B %s: member access .%s" % [relative, name])
			if literal_code.find("[\"%s\"]" % str(name)) != -1:
				offending.append("B %s: subscript \"%s\"" % [relative, name])
	check_eq(offending, [],
		"the delivered magic result neither scales a value nor touches a balance")
	check_eq(forbidden_operators.size(), 6,
		"the forbidden-operator list is intact")
	# The single arithmetic-shaped expression the module is allowed to contain,
	# pinned literally so a second one cannot hide behind the guard's silence.
	const WHOLE_TEST := "if float(value) != floor(float(value)):"
	var whole_tests := 0
	for line in _code_lines(_code_only(_project_source(RESULT_SCRIPT))):
		if str(line).strip_edges() == WHOLE_TEST:
			whole_tests += 1
	check_eq(whole_tests, 1,
		"the whole-number test appears exactly once, and it is the only"
		+ " arithmetic-shaped line the module contains")
	# And the reason it is the only one: the module must not even be able to
	# *store* a reported balance, which the subscript check above covers. This
	# is the control for that check - a balance name it does not match, so a
	# widened `STORED_RESOURCE_NAMES` that added an eighth entry would fail
	# here rather than pass by finding nothing.
	var unmatched := 0
	var literal_module := _comment_free(_project_source(RESULT_SCRIPT))
	for name in ServerV1Magic.STORED_RESOURCE_NAMES:
		if literal_module.find("\"%s\"" % str(name)) == -1:
			unmatched += 1
	check_eq(unmatched, 0,
		"every stored-resource name the module validates also appears in it,"
		+ " so the balance guard has real names to find")


## ## No line of either delivered module may **relate** two reported values.
##
## This is the guard for D5 and D7, and it is why the report can state
## `client_relates_two_reported_values: false` as a mechanical fact rather than
## as prose. The five relations this client must never make:
##
##   * `before` with `after`                      (the counter's own rule)
##   * `after` with `cap`                         (the bound)
##   * `after` with `at_cap`                      (the same bound, as a flag)
##   * `player_level` with `level`                (design D5's gate)
##   * `requested_id` with `resolved_id`          (design D7's addressing)
##
## The check is over the **code**, with string literals blanked, so the five
## names are invisible to it -- which is exactly right: the module names all
## five, and the guard must fire on an expression *relating* them rather than
## on the names appearing.
##
## `==` and `!=` are excluded from the operator set on purpose, and that exclusion
## is asserted below rather than left implicit: two of the five relations above
## would most naturally be written with `==`, and the module legitimately uses
## equality on a **boolean flag** (`same_transition_for_both_operations != true`)
## and on the null price. Forbidding `==` outright would fail on those two
## correct uses, so the sharper guard is the **pair** check below plus this one.
func _check_no_line_compares_two_reported_values() -> void:
	var relational := ["<", ">", "<=", ">="]
	var pairs := [
		["before", "after"], ["after", "cap"], ["after", "at_cap"],
		["player_level", "level"], ["requested_id", "resolved_id"],
	]
	var offending: Array = []
	for relative in DELIVERED_MODULES:
		var body := _project_source(relative)
		if body == "":
			fail("%s is readable for the comparison guard" % relative)
			continue
		# `->` is a **return-type arrow**, not a comparison; blanking it is what
		# keeps all forty of the transport's signatures out of the relational set.
		# The relational scan reads the literals-blanked projection so a `<` in a
		# reported string is not read as a comparison, and the pair scan reads the
		# literals-kept one, because the forbidden shape is
		# `body["before"] > body["after"]` and the quoted names **are** what is
		# being looked for.
		var code := _code_only(body).replace("->", "  ")
		var literal_code := _comment_free(body).replace("->", "  ")
		for line in _code_lines(code):
			var candidate := str(line).strip_edges()
			if candidate == "":
				continue
			for operator in relational:
				if candidate.find(operator) != -1:
					offending.append("%s: %s (%s)"
						% [relative, candidate, operator])
		for literal_line in _code_lines(literal_code):
			var candidate := str(literal_line).strip_edges()
			if candidate == "":
				continue
			for pair in pairs:
				# Both names, **inside the module's own spelling**: a GDScript
				# source carries them quoted, and the quoted form is required --
				# `si` as a bare two-character substring occurs inside "assist",
				# "position" and "using" throughout a typical module, so a bare
				# substring check here could never fire.
				var left := "\"%s\"" % str(pair[0])
				var right := "\"%s\"" % str(pair[1])
				if candidate.find(left) != -1 and candidate.find(right) != -1:
					offending.append("%s: %s relates %s with %s"
						% [relative, candidate, str(pair[0]), str(pair[1])])
	check_eq(offending, [],
		"neither delivered client module relates two reported values")
	check_eq(relational.size(), 4, "the relational-operator list is intact")
	check_eq(pairs.size(), 5, "and all five forbidden relations are listed")
	# The control: the pairs are non-trivial, so the check above is not passing
	# on a vocabulary nothing in the module could ever write.
	var reachable := 0
	# Literals **kept** here: this control exists to prove the five names are
	# findable at all, which is exactly what the literals-blanked projection
	# cannot show. It measured **zero of ten** when the two were conflated.
	var module_code := _comment_free(_project_source(RESULT_SCRIPT))
	for pair in pairs:
		for name in pair:
			if module_code.find("\"%s\"" % str(name)) != -1:
				reachable += 1
	check(reachable >= 10,
		"every forbidden relation is reachable from a name the module really"
		+ " contains: %d of %d name-occurrences found"
		% [reachable, pairs.size() * 2])


## **Ten** reserved derivation stems, checked by substring against declared
## function names in both delivered modules, folded to lower case, in **both**
## directions.
##
## **The whole-inventory pin is the real gate.** It asserts the exact declared
## name sets, so any new function at all is visible. The stems are the belt, and
## they are substrings because `godot-friends` measured that an exact-name check
## passes a helper merely *prefixed* with a reserved word, and that a
## case-sensitive one passes `Friend_Of`.
func _check_absent_derivation_helpers() -> void:
	var expected := {
		RESULT_SCRIPT: [
			"magic_failure", "parse_magic_counter", "_refusal", "_success",
			"_identity", "_counter", "_committed", "_resources",
			"_string_list", "_behaviour", "_whole_number",
		],
		API_SCRIPT: _api_function_inventory(),
	}
	for relative in expected:
		var body := _project_source(relative)
		check(body != "", "%s is readable" % relative)
		if body == "":
			continue
		var declared := _declared_function_names(body)
		check_eq(_sorted_set(declared), _sorted_set(expected[relative]),
			"%s declares exactly the functions this suite knows about" % relative)
		var folded := _folded_set(declared)
		for stem in RESERVED_DERIVATION_STEMS:
			var hits: Array = []
			for name in folded:
				if str(name).find(stem) != -1:
					hits.append(str(name))
			check_eq(hits, [],
				"%s declares no %s-shaped function (%s)"
				% [relative, stem, str(hits)])
	check_eq(RESERVED_DERIVATION_STEMS.size(), 10,
		"the reserved-derivation list is intact")
	var matched_anywhere := 0
	for stem in RESERVED_DERIVATION_STEMS:
		for relative in expected:
			for name in _folded_set(
					_declared_function_names(_project_source(relative))):
				if str(name).find(stem) != -1:
					matched_anywhere += 1
	check_eq(matched_anywhere, 0,
		"and none of the delivered functions matches one")
	# The **other** direction, and the reason the pins are hand-maintained lists
	# rather than "whatever is there": a name in `expected` that the module does
	# **not** declare would leave a guard reading a function that moved or was
	# deleted, which is the drift this project has recorded twice.
	var missing: Array = []
	for relative in expected:
		var declared := _declared_function_names(_project_source(relative))
		for name in (expected[relative] as Array):
			if not declared.has(str(name)):
				missing.append("%s: %s" % [relative, str(name)])
	check_eq(missing, [], "and every expected name is really declared")


## ## The **domain** module's whole function inventory, read from the repository.
##
## Task 6.5 asks for the domain module's inventory to be pinned, and the pins
## above cover only the two client modules. This is the other half, and it is the
## half that matters: an invented price helper or an invented level gate would
## most likely be written in **Python**, next to the derivation, not in the
## transport that calls it.
##
## The names are re-read from `apps/server-v1/server_v1_magic.py` on every run
## rather than transcribed, because a transcribed inventory is a claim about a
## file that can drift, and this project has recorded a pinned count going stale
## within a day.
func _check_domain_inventory() -> void:
	var source := _repo_text(DOMAIN_MODULE)
	check(source != "", "%s is readable" % DOMAIN_MODULE)
	if source == "":
		return
	var declared := _python_function_names(source)
	check(declared.size() >= 15,
		"the domain module declares at least fifteen functions: %d found"
		% declared.size())
	check(declared.has("issue_magic_transition"),
		"and it declares the issuance entry point")
	check(declared.has("apply_magic"),
		"and the apply entry point")
	check(declared.has("declared_operations"),
		"and the operations reader")
	check(declared.has("_prove"),
		"and the post-condition proof")
	check(declared.has("_half_checks"),
		"and the four property checks that proof calls")
	check(declared.has("_violated_half"),
		"and the helper that names which half failed")
	check(declared.has("_changed_leaf_paths"),
		"and the leaf walker the proof reads the file with")
	check(declared.has("_rollback"),
		"and the rollback the above-cap refusal reports on")
	# The pinned set, compared as a **sorted unique** set. A positional list
	# comparison fails against the delivered module itself, because `__init__`,
	# `committed` and `cap_provenance` are declared inside classes and this scan
	# does not distinguish them from module-level functions.
	var pinned := [
		"__init__", "_changed_leaf_paths", "_committed_report",
		"_half_checks", "_ordered_ledger", "_prove", "_read_only",
		"_recorded_map_level", "_refuse", "_repository_refusal",
		"_rollback", "_unknown_magic", "_violated_half",
		"apply_magic", "cap_provenance", "committed",
		"declared_operations", "issue_magic_transition",
	]
	check_eq(_sorted_set(_string_list(declared)), _sorted_set(pinned),
		"the domain module declares exactly the functions this suite pins")
	var missing: Array = []
	for name in pinned:
		if not declared.has(str(name)):
			missing.append(str(name))
	check_eq(missing, [],
		"and every pinned name is really declared, so a renamed helper cannot"
		+ " leave a guard reading a function that moved")


## The ten reserved stems against the **domain** module's declared names.
func _check_domain_reserved_stems() -> void:
	var declared := _python_function_names(_repo_text(DOMAIN_MODULE))
	check(declared.size() > 0, "the domain module's names were read")
	var folded := _folded_set(_string_list(declared))
	for stem in RESERVED_DERIVATION_STEMS:
		var hits: Array = []
		for name in folded:
			if str(name).find(stem) != -1:
				hits.append(str(name))
		check_eq(hits, [],
			"the domain module declares no %s-shaped function (%s)"
			% [stem, str(hits)])
	var matched := 0
	for stem in RESERVED_DERIVATION_STEMS:
		for name in folded:
			if str(name).find(stem) != -1:
				matched += 1
	check_eq(matched, 0,
		"and none of the domain module's functions matches one of the %d stems"
		% RESERVED_DERIVATION_STEMS.size())


## ## The Python name scan is a **line scan**, and that is a limitation.
##
## It recognises `def name(` and `async def name(` at the start of a line after
## stripping indentation, which is what covers module-level functions, class
## methods and nested functions - but it also matches a `def` inside a **docstring
## or comment**, because it runs over the raw source.
##
## That is recorded rather than fixed, because the fix would be an AST parse and
## this suite may not execute Python. The consequence is the opposite of the one
## that would matter: the scan can only report **too many** names, so a planted
## helper inside a comment would be caught here even though it does nothing -
## a false positive, not a false negative. The next check proves the scan is not
## vacuous.
func _check_python_name_scan_finds_planted_defs() -> void:
	const PLANT := "def a_planted_helper(x):\n\treturn x\n\nclass C:\n\tdef m(self):\n\t\tpass\n\nasync def top():\n\tpass\n"
	var found := _python_function_names(PLANT)
	check_eq(_sorted_set(_string_list(found)),
		["a_planted_helper", "m", "top"],
		"the Python name scan finds a module-level def, a method and an async"
		+ " def, so it is not passing on a vacuous zero")
	check(found.has("m"),
		"and it finds an INDENTED def, which is the case a naive scan misses")
	# The control for the recorded limitation, in **both** directions. A `def`
	# behind a `#` is NOT found, because the scan needs the line to begin with
	# `def` once indentation is stripped - the first draft of this check asserted
	# the opposite and failed, which is how the over-count turned out to be
	# narrower than it had been described. A `def` inside a docstring IS found,
	# and that is the limitation: a line scan, not a parse.
	check(not _python_function_names("# def commented_out(x):\n").has(
		"commented_out"),
		"a def behind a # is NOT found: the line must begin with def")
	const PLANT_DOCSTRING := "class C:\n\t\"\"\"\n\tdef in_a_docstring(x):\n\t\treturn x\n\t\"\"\"\n"
	check(_python_function_names(PLANT_DOCSTRING).has("in_a_docstring"),
		"but a def inside a docstring IS found -- the recorded limitation"
		+ " above, and the safe direction")
	var real := _python_function_names(_repo_text(DOMAIN_MODULE))
	check(real.size() > found.size(),
		"and the domain module yields strictly more names than the plant")


## The magic refusal codes are declared by the **magic** modules, not by the
## transport, and each maps to the status the client would see.
func _check_magic_codes_live_in_the_magic_modules() -> void:
	var refusals := _repo_text(REFUSALS_MODULE)
	check(refusals != "", "%s is readable" % REFUSALS_MODULE)
	if refusals == "":
		return
	# Counted **from the committed module** rather than from a number typed
	# here, so a sixth magic code cannot land without this suite noticing.
	var declared := 0
	for line in refusals.split("\n"):
		if _looks_like_status_row(str(line)):
			declared += 1
	check_eq(declared, 20,
		"the committed refusal table maps exactly nineteen codes")
	check_eq(EXPECTED_MAGIC_REFUSALS.size(), 6,
		"and this route answers exactly six distinct codes")
	for code in EXPECTED_MAGIC_REFUSALS:
		var row: Array = EXPECTED_MAGIC_REFUSALS[code]
		var member := "    RefusalCode.%s:" % str(row[0])
		check(refusals.find(member) != -1,
			"the committed table declares %s" % str(code))
		var marker := "%s %d," % [member, int(row[1])]
		check(refusals.find(marker) != -1,
			"the committed table maps %s to HTTP %d"
			% [str(code), int(row[1])])
		check(refusals.find("\"%s\"" % str(code)) != -1,
			"and the table carries %s as its wire value" % str(code))
	# And the codes this line's route raises live in the **domain** module, not
	# in the transport: `post_magic` names no `RefusalCode` member at all.
	var domain := _repo_text(DOMAIN_MODULE)
	for code in EXPECTED_MAGIC_REFUSALS:
		var named: bool = bool((EXPECTED_MAGIC_REFUSALS[code] as Array)[2])
		var spelled: bool = domain.find("RefusalCode.%s"
			% str((EXPECTED_MAGIC_REFUSALS[code] as Array)[0])) != -1
		check_eq(spelled, named,
			"the domain module %s name %s"
			% ["names" if named else "does NOT name", str(code)])
	check_eq(_sorted_set(_named_refusal_members(domain)),
		_sorted_set(DOMAIN_NAMED_CODES),
		"and the domain names exactly the seven pinned members, so a seventh"
		+ " magic code cannot land there unnoticed")
	var content := _repo_text(CONTENT_MODULE)
	check(content.find("CONFIG_MAIN") != -1,
		"and the content module still declares its raw-config path")
	check(content.find("\"config\", \"main.json\"") != -1
		or content.find("(\"config\", \"main.json\")") != -1,
		"which is the RAW table -- task 2.1's letter named the normalized"
		+ " package, and this is the divergence recorded in tasks.md")


# --- the facade --------------------------------------------------------------


## The facade selects the third implementation, describes its endpoint, and
## releases it again. Repeated from the other two suites because this route must
## be reachable **through the facade** and not only through the implementation.
func _check_facade_registration() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var before := str(api.implementation_name())
	api.configure("server_v1", LIVE_ENDPOINT)
	check_eq(str(api.implementation_name()), "server_v1",
		"the facade selects the Server v1 implementation")
	check_eq(str(api.describe_transport()), LIVE_ENDPOINT,
		"the facade describes v1's own endpoint")
	check(api._impl is ServerV1Api,
		"the facade's active implementation is a ServerV1Api")
	check_eq(str(api._impl.resolved_endpoint()), LIVE_ENDPOINT,
		"the selected implementation dials the endpoint it was given")
	check_eq(api.magic_requests, 0,
		"selecting an implementation issues no request")
	api.configure("fake")
	check_eq(str(api.implementation_name()), "fake",
		"the facade restores the fake implementation")
	check(not (api._impl is ServerV1Api),
		"the v1 implementation is released on reconfigure")
	info("implementation in force before this suite selected one: %s" % before)


## Task 6.2 says do **not** widen `GameApi` unless a declared return type
## genuinely differs. It does, and this is the measurement that shows it: the
## three implementations declare **two** concrete types for `magic_town` - the
## two v0-shaped ones agree with each other and v1's own is the odd one out - so
## a facade naming either would be lying to the other two. The first draft of
## this check asserted three distinct types and was wrong: `fake_api.gd` and
## `legacy_v0_api.gd` both return v0's `MagicFlow.MagicResult`.
##
## The widening is also only safe because **every** call site binds its result to
## `Variant` or to an untyped local, and that is measured over the whole project
## rather than asserted in prose.
func _check_return_type_widening() -> void:
	var files: Array = []
	_collect_sources(MAGIC_SCRIPT_PATHS.project_dir(), "", files)
	check(files.size() > 40,
		"the project sources were walked: %d files" % files.size())
	var offenders: Array = []
	var call_sites := 0
	var declarations := 0
	var per_file: Dictionary = {}
	for absolute in files:
		var name := str(absolute)
		if name.ends_with(SELF_SCRIPT):
			continue
		var body := FileAccess.get_file_as_string(name)
		if body.find("magic_town") == -1:
			continue
		var lines := body.split("\n")
		for index in lines.size():
			var line := str(lines[index]).strip_edges()
			if not line.contains("magic_town("):
				continue
			if line.begins_with("#"):
				continue
			# **Declarations and call sites are counted apart.** The first draft
			# pinned five and measured ten: ten is the true number of lines
			# carrying `magic_town(`, and it is four declarations plus six calls.
			if line.begins_with("func ") or line.begins_with("static func "):
				declarations += 1
				continue
			var where := str(absolute).get_file()
			call_sites += 1
			per_file[where] = int(per_file.get(where, 0)) + 1
			if not _binds_untyped(line, lines, index):
				offenders.append("%s: %s" % [where, line])
	check_eq(offenders, [],
		"every magic_town call site binds to Variant or untyped")
	check_eq(call_sites, 6,
		"six call sites: five in test_damage_magic.gd and the facade's own"
		+ " forwarder")
	check_eq(declarations, 4,
		"and four declarations -- the facade plus the three implementations")
	check_eq(_sorted_keys(per_file), ["game_api.gd", "test_damage_magic.gd"],
		"the six call sites live in exactly two files")
	check_eq(int(per_file["test_damage_magic.gd"]), 5,
		"five of them are the pre-existing v0 client's own")
	var distinct: Array = []
	for relative in IMPL_RETURN_TYPES:
		var declared := _return_type_of(_project_source(relative), INTENT_METHOD)
		check_eq(declared, str(IMPL_RETURN_TYPES[relative]),
			"%s declares %s for magic_town"
			% [relative, str(IMPL_RETURN_TYPES[relative])])
		distinct.append(declared)
	check_eq(_sorted_set(distinct).size(), 2,
		"three implementations declare TWO distinct concrete types -- the two"
		+ " v0-shaped ones agree, and v1's is the odd one out -- which is why"
		+ " the facade cannot name one of them")
	check_eq(_return_type_of(_project_source(FACADE_SCRIPT), INTENT_METHOD),
		"Variant", "the facade's magic_town is declared Variant")
	info("magic_town call sites measured: %d" % call_sites)


## `magic_town` must have LEFT the collect suite's `UNSUPPORTED_INTENTS` table.
## This is a genuine cross-suite guard rather than a restatement: the table is
## read out of `test_server_v1.gd`'s source at runtime, so re-adding the intent
## there - which would reinstate a local refusal the client no longer produces -
## fails **here**.
func _check_unsupported_intent_left_the_table() -> void:
	var body := _project_source(COLLECT_SUITE_SCRIPT)
	check(body != "", "%s is readable" % COLLECT_SUITE_SCRIPT)
	if body == "":
		return
	var start := body.find("const UNSUPPORTED_INTENTS := [")
	check(start != -1, "the collect suite still declares its unsupported table")
	var tail := body.substr(start) if start != -1 else ""
	var names: Array = []
	# The read is BOUNDED at the table's own closing bracket. An unbounded tail
	# keeps matching rows in whatever tables follow this one, which is how a
	# first version of this check reported 27 intents for a 22-entry table - and,
	# worse, a *plausible* wrong number rather than an obviously broken one.
	var depth := 0
	var closed := false
	for line in tail.split("\n"):
		var candidate := str(line).strip_edges()
		if candidate == "" or candidate.begins_with("#"):
			continue
		depth += candidate.count("[") - candidate.count("]")
		if depth <= 0:
			closed = true
			break
		if candidate.begins_with("[\"") and candidate.ends_with("],"):
			names.append(candidate.substr(2, candidate.find("\",") - 2))
	check(closed, "the unsupported table's closing bracket was found, so the"
		+ " read is bounded by it rather than by the end of the file")
	check_eq(names.size(), 20,
		"the collect suite pins exactly the twenty-one intents v1 still lacks")
	check(not names.has(INTENT_METHOD),
		"magic_town left the unsupported table, because v1 implements it now")
	check(not names.has("collect_income"),
		"and so did the first v1 intent")
	check(not names.has("complete_collection_town"),
		"and so did the second")
	check(names.has("place_building"),
		"the table is still a real list, not an emptied one")


## The positive control for the scope suite's measured carrier set: the v1
## transport carries all three tokens, the legacy-v0 one still does, and **this
## line's** typed-result module carries none - so the carrier measurement has a
## third real thing to find and cannot be passing on a vacuous zero.
func _check_transport_token_placement() -> void:
	var api_body := _project_source(API_SCRIPT)
	var result_body := _project_source(RESULT_SCRIPT)
	var v0_body := _project_source(V0_SCRIPT)
	var tokens := _transport_tokens()
	check_eq(tokens.size(), 3,
		"the committed scope suite still confines exactly three tokens")
	check(api_body.find(LIVE_ENDPOINT) != -1,
		"the v1 implementation names v1's own loopback port")
	check(v0_body.find("5057") == -1,
		"the legacy-v0 implementation names no v1 port")
	check(api_body.find(ServerV1Api.MAGIC_PATH) != -1,
		"the v1 transport names its own magic path")
	if tokens.size() != 3:
		return
	for token in tokens:
		check(api_body.find(token) != -1,
			"the v1 transport carries the %s token" % token)
		check(v0_body.find(token) != -1,
			"the legacy-v0 implementation still carries %s" % token)
		check(result_body.find(token) == -1,
			"this line's typed-result module carries no %s token" % token)
		check(_project_source(SELF_SCRIPT).find(token) == -1,
			"this suite spells no transport token either (%s)" % token)


## The three transport tokens, READ OUT of the committed scope suite rather than
## transcribed, so the positive control cannot drift from the guard it
## corroborates. Returns [] when the declaration cannot be read.
func _transport_tokens() -> Array:
	var body := _project_source(SCOPE_SCRIPT)
	var start := body.find("RESTRICTED_TO_TRANSPORT_IMPLS")
	if start == -1:
		return []
	var tail := body.substr(start)
	var end := tail.find("]")
	if end == -1:
		return []
	var tokens: Array = []
	for line in tail.substr(0, end).split("\n"):
		var candidate := str(line).strip_edges()
		if not candidate.begins_with('"') or not candidate.ends_with(","):
			continue
		tokens.append(candidate.substr(1, candidate.length() - 3))
	return tokens


# --- the live arm ------------------------------------------------------------


## ## Two operations, one identity, and a **file-level** diff between them.
##
## Task 7.3 asks for, per operation: that the corpus save mutated, that exactly
## one leaf path changed, and that all seven stored resources are byte-identical
## across both. None of that is answerable from the response - the response is
## the server's own summary of itself, so a client that diffed it would be
## diffing that summary. The disposable corpus **file** is the evidence, and the
## harness passes its path as `--corpus=` for exactly this.
##
## Nothing is seeded. The fresh corpus's ledger is already `{}`, which is
## already exercisable, so the first operation **adds** a leaf and the second
## changes it. Both are counted as one touched leaf each, and the kind is
## reported, because "added" and "changed" are different facts about the same
## count of one.
func _check_live() -> void:
	var endpoint := _arg(ARG_ENDPOINT, LIVE_ENDPOINT)
	var player_id := _arg(ARG_PLAYER_ID, "")
	var corpus := _arg(ARG_CORPUS, "")
	check(player_id != "",
		"the live phase supplies the disposable corpus's player id")
	check(corpus != "",
		"and the disposable corpus path, for the file-level diff")
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null or player_id == "":
		return
	var save_file := corpus.path_join("saves").path_join(
		player_id + SAVE_SUFFIX)
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

	var zero: Dictionary = _read_save(save_file)
	check_eq(_sorted_keys(_ledger(zero)), [],
		"the fresh disposable ledger is empty, and this phase seeds nothing")

	var reports: Array = []
	var touched: Array = []
	for operation in ["buy", "use"]:
		var before_document := _read_save(save_file)
		var before_requests := int(impl.transport_requests)
		var answer: Variant = await api.magic_town(
			player_id, operation, LIVE_MAGIC)
		if not (answer is ServerV1Magic.MagicCounterResult):
			fail("the live %s answers v1's own typed result class" % operation)
			return
		var typed: ServerV1Magic.MagicCounterResult = answer
		check(typed.ok, "the live %s resolves (%s / %s)"
			% [operation, typed.error_code, typed.error_message])
		if not typed.ok:
			return
		check_eq(typed.protocol, "server-v1",
			"the live %s answer is stamped with v1's protocol" % operation)
		check_eq(typed.action, "magic",
			"the live %s answer names the action" % operation)
		check_eq(str(typed.magic.operation), str(operation),
			"the live %s answer reports the operation that ran" % operation)
		check_eq(typed.magic.requested_id, LIVE_MAGIC,
			"the live %s answer reports the id the client sent" % operation)
		check_eq(typed.magic.resolved_id, LIVE_MAGIC,
			"and the id the server resolved")
		check_eq(typed.magic.ledger_key, str(LIVE_MAGIC),
			"and the ledger key it wrote")
		check_eq(typed.magic.transition_id.length(), 32,
			"and it names the transition in 32 characters")
		check_eq(typed.cap, 50,
			"the live answer carries the cap literal")
		check(typed.cap_is != "", "with its provenance sentence")
		check(typed.price_charged == null,
			"and the live %s answer charges no price" % operation)
		check_eq(_sorted_set(_string_list(typed.stored_resources_compared)),
			_sorted_set(ServerV1Magic.STORED_RESOURCE_NAMES),
			"and names exactly the seven stored resources it compared")
		check(typed.committed != null,
			"and carries the committed row verbatim")
		if typed.committed != null:
			check_eq(int(typed.committed["gold"]), 30000,
				"whose gold column is the committed 30000, not a charge")
			check(typed.committed["level_gate_enforced"] == false,
				"and the server enforced no level gate on it")
			check(typed.committed["level_compared"] == false,
				"and compared no player level against it")
		check_eq(int(impl.transport_requests) - before_requests, 1,
			"one %s intent put exactly ONE request on the wire" % operation)
		# **The positive typed marker.** `verify-boot.ps1` asserts per-phase
		# regexes on these rather than trusting the harness exit code, so a phase
		# whose request never left the client cannot pass on refusals alone. Every
		# group is drawn from the **typed** result, not from the raw payload, so
		# the assertion is about what the client read rather than about bytes that
		# happened to arrive. `price_charged` is spelled the way it is printed,
		# because "the literal word null" is the strongest available statement
		# that nothing was priced (design D2).
		print("[test] live-server-v1-magic operation=%s requested=%d resolved=%d transition=%s before=%d after=%d cap=%d price_charged=%s compared=%d divergences=%d"
			% [str(operation), int(typed.magic.requested_id),
				int(typed.magic.resolved_id), str(typed.magic.transition_id),
				int(typed.counter_before), int(typed.counter_after),
				int(typed.cap),
				"null" if typed.price_charged == null else str(typed.price_charged),
				(typed.stored_resources_compared as Array).size(),
				(typed.divergences as Array).size()])

		# ---- the file-level half ------------------------------------------
		var after_document := _read_save(save_file)
		check_eq(after_document.size() > 0, true,
			"the %s call left the disposable save readable" % operation)
		var difference := _touched_leaf_paths(before_document, after_document)
		check_eq(difference.size(), 1,
			"the %s transition touched EXACTLY ONE stored leaf path"
			% operation)
		touched.append(difference)
		var ledger_after := _ledger(after_document)
		check_eq(_sorted_keys(ledger_after), [str(LIVE_MAGIC)],
			"and the ledger after the %s holds exactly the addressed key"
			% operation)
		reports.append(_resource_report(after_document))
		info("live %s: touched=%s ledger=%s"
			% [operation, JSON.stringify(difference),
				JSON.stringify(ledger_after)])

	check_eq(_sorted_set(reports[0].keys()),
		_sorted_set(reports[1].keys()),
		"both operations report the same seven stored resources")
	var unchanged := 0
	for name in ServerV1Magic.STORED_RESOURCE_NAMES:
		if int(reports[0][name]) == int(reports[1][name]):
			unchanged += 1
	check_eq(unchanged, 7,
		"and all seven stored resources are byte-identical across both")
	# The counter really did rise, which is what makes "one leaf" mean
	# "one ledger entry" rather than "one unrelated field".
	check_eq(_ledger(_read_save(save_file))[str(LIVE_MAGIC)], 2,
		"the addressed ledger key rose from nothing to 2 across the two")
	# The first operation ADDS a leaf and the second CHANGES one. Both count as
	# one, and the difference is asserted rather than flattened, because a
	# counter that merely changed a value is a different fact from one that
	# created the record.
	check_eq(touched[0], [{"path": "/privateState/magics/1", "kind": "added"}],
		"the first operation ADDED the addressed ledger leaf")
	check_eq(touched[1], [{"path": "/privateState/magics/1", "kind": "changed"}],
		"and the second CHANGED it")

	# The refusals this route owns, over the same live service.
	_check_live_refusal(
		await api.magic_town(player_id, "buy", 9999),
		"unknown_magic_id", "a magic id outside the committed table")
	_check_live_refusal(
		await api.magic_town(player_id, "buy", "1"),
		"malformed_request", "a non-canonical identity form")
	_check_live_refusal(
		await api.magic_town(player_id, "burn", LIVE_MAGIC),
		"malformed_request", "an operation outside the closed set")
	_check_live_refusal(
		await api.magic_town("00000000-0000-4000-8000-0000000000ff",
			"buy", LIVE_MAGIC),
		"unknown_player", "a player with no save document")


func _check_live_refusal(answer: Variant, expected_code: String,
		label: String) -> void:
	if not (answer is ServerV1Magic.MagicCounterResult):
		fail("%s must answer v1's typed result" % label)
		return
	var typed: ServerV1Magic.MagicCounterResult = answer
	check(not typed.ok, "%s is refused" % label)
	if typed.error_code != expected_code:
		check(false, "%s is refused by v1's own code (saw %s: %s)"
			% [label, typed.error_code, typed.error_message])
	else:
		check(true, "%s is refused by v1's own code" % label)
	print("[test] live-server-v1-magic-refusal code=%s" % typed.error_code)
	check_eq(typed.committed, {}, "%s carries no committed row" % label)
	check(typed.resources_after == null,
		"%s carries no balance set, never a partial payload" % label)
	check(typed.magic == null, "%s carries no addressing block" % label)
	check_eq(typed.ledger_after, [], "%s carries no ledger" % label)
	check(typed.price_charged == null, "%s names no price" % label)
	check(typed.error_message != "",
		"%s explains itself rather than answering with a bare code" % label)


## Every leaf path whose value differs between two parsed JSON documents, with
## `added`, `removed` and `changed` kept distinct.
##
## The distinction is the whole point for this line: the **first** live operation
## adds a ledger key where there was none, and a counter that flattened that into
## "changed" would report a mutation the file does not contain. An empty list and
## a list are accepted; a leaf holding `{}` or `[]` is still a leaf, so a key
## added as an empty object counts as one touched path.
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
				_walk_difference(left[key], right[key], path, out)
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


## JSON equality by canonical text. `JSON.stringify` sorts this engine's
## dictionary keys, so two documents with the same content render identically -
## which is what makes the walk above usable on a parsed file.
func _json_equal(left: Variant, right: Variant) -> bool:
	return JSON.stringify(left) == JSON.stringify(right)


func _read_save(path: String) -> Dictionary:
	var text := FileAccess.get_file_as_string(path)
	if text == "":
		return {}
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		return {}
	return parsed as Dictionary


func _ledger(document: Dictionary) -> Dictionary:
	var state: Variant = document.get("privateState", null)
	if not (state is Dictionary):
		return {}
	var entry: Variant = (state as Dictionary).get("magics", null)
	if not (entry is Dictionary):
		return {}
	return entry as Dictionary


## The seven stored resources, read out of the file. They live in **three**
## different places - six under `maps[0]` and `mana` under `privateState` - and
## `cash` is under `maps[0]` too in this corpus, which is why this reads each
## holder rather than assuming one.
func _resource_report(document: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	var map_state: Variant = document.get("maps", null)
	var first_map: Variant = null
	if (map_state is Array) and (map_state as Array).size() > 0:
		first_map = (map_state as Array)[0]
	var private: Variant = document.get("privateState", null)
	for name in ServerV1Magic.STORED_RESOURCE_NAMES:
		var value: Variant = null
		if (first_map is Dictionary) and (first_map as Dictionary).has(str(name)):
			value = (first_map as Dictionary)[str(name)]
		elif (private is Dictionary) and (private as Dictionary).has(str(name)):
			value = (private as Dictionary)[str(name)]
		else:
			var info: Variant = document.get("playerInfo", null)
			if (info is Dictionary) and (info as Dictionary).has(str(name)):
				value = (info as Dictionary)[str(name)]
		out[str(name)] = value
	return out


# --- evidence ----------------------------------------------------------------


## The deterministic report, written only when `--report=<path>` is supplied. It
## carries no wall-clock, path or environment value, so it is byte-identical
## across runs on the same source - including its own digest, computed over the
## exact bytes written.
##
## `modules_are_pure_lf` is **measured** on every run. Three sibling reports
## carry a hard-coded `false`; for those files it was true, because they were
## checked out CRLF, and for one of them it was written as a statement about the
## checkout rather than about the files. Copying a field **and its value** across
## file forms is how a guard becomes a lie, so the value here comes from
## `_modules_are_pure_lf()` and nothing else.
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
	var committed_rows := _committed_row_count()
	var document := {
		"report": "magic-v1-report-v1",
		"intent": {
			"action": ServerV1Magic.ACTION,
			"protocol": ServerV1Magic.PROTOCOL,
			"magic_path": ServerV1Api.MAGIC_PATH,
			"operations": ServerV1Magic.OPERATIONS,
			"request_fields": ["player_id", "magic_id", "operation"],
			"negative_id_is_filtered_client_side": false,
			"operation_is_filtered_client_side": false,
			"client_local_codes": [
				ServerV1Magic.CODE_UNSUPPORTED,
				ServerV1Magic.CODE_BAD_REQUEST,
			],
			"impl_return_types": IMPL_RETURN_TYPES,
			"facade_return_type": _return_type_of(
				_project_source(FACADE_SCRIPT), INTENT_METHOD),
			"facade_widening_is_the_third": true,
		},
		"typed_result": {
			"stored_resource_names":
				ServerV1Magic.STORED_RESOURCE_NAMES,
			"stored_resource_count": 7,
			"reported_committed_fields":
				ServerV1Magic.REPORTED_COMMITTED_FIELDS,
			"refuses_a_non_null_price_charged": true,
			"refuses_a_denied_shared_transition": true,
			"fail_closed_cases": FAIL_CLOSED_CASE_COUNT,
		},
		"refusals": {
			"observed_conditions": _sorted_keys(OBSERVED_REFUSALS),
			"observed_condition_count": OBSERVED_REFUSALS.size(),
			"distinct_codes": _sorted_set(
				_string_list(_observed_codes())),
			"declared_by_the_committed_table": 20,
			"client_local_codes_are_server_codes": false,
		},
		"committed_table": {
			"source": RAW_CONFIG,
			"rows": committed_rows,
			"numeric_columns": NUMERIC_COLUMNS,
			"price_candidate_columns": PRICE_CANDIDATE_COLUMNS,
			"no_column_is_named_a_price": true,
			"raw_table_has_no_kind_column": true,
			"area_is_an_embedded_json_string": true,
		},
		"claims": {
			"client_computes_a_price": false,
			"client_evaluates_a_level_gate": false,
			"client_derives_the_next_counter": false,
			"client_relates_two_reported_values": false,
			"client_filters_an_identity_or_operation": false,
			"unsupported_intent_touches_transport": false,
			"parity_with_legacy_claimed": false,
		},
		# Each claim names the check that fails when it stops being true, so the
		# block above reads as a table of guards rather than as prose.  A claim
		# with no enforcing check would be an assertion, which is the defect this
		# suite exists to catch in the modules.
		"enforced_by": {
			"client_computes_a_price":
				"_check_no_client_arithmetic (guard A) + "
				+ "_check_absent_derivation_helpers + "
				+ "_check_domain_reserved_stems + "
				+ "_check_committed_table_is_re_derived + "
				+ "_check_fail_closed (the priced-answer case)",
			"client_evaluates_a_level_gate":
				"_check_no_line_compares_two_reported_values + "
				+ "_check_absent_derivation_helpers + "
				+ "_check_fail_closed (the enforced-gate case)",
			"client_derives_the_next_counter":
				"_check_no_line_compares_two_reported_values + "
				+ "_check_domain_inventory",
			"client_relates_two_reported_values":
				"_check_no_line_compares_two_reported_values (five pairs)",
			"client_filters_an_identity_or_operation":
				"_check_intent_body",
			"unsupported_intent_touches_transport":
				"test_server_v1.gd; this suite asserts the intent LEFT its "
				+ "unsupported table (_check_unsupported_intent_left_the_table)",
			"parity_with_legacy_claimed":
				"not a claim; v1 is new behaviour and no legacy oracle exists",
		},
		"limits": {
			"legacy_command": "buy_magic / use_magic",
			"legacy_branch": "command.py:652-675",
			"price_is_derived": false,
			"level_gate_is_derived": false,
			"counter_rule_is_derived": true,
			"cap_is_a_preserved_branch_literal": true,
			"fixture_is_a_captured_legacy_oracle": false,
			"fixtures_are_observed_v1_answers": true,
			"live_phase_seeds_nothing": true,
			"ledger_shape_refusal_needs_an_in_memory_row": true,
			"v1_routes_delivered_total": 3,
			"windowed_capture": false,
			"pixel_parity": false,
			"client_sees_a_before_state": false,
			"python_name_scan_over_counts_a_docstring": true,
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
	var text := ""
	for byte in written:
		text += String.chr(int(byte))
	var digest := text.sha256_text()
	info("report bytes %d, sha256 %s" % [written.size(), digest])


func _module_digests() -> Dictionary:
	var out: Dictionary = {}
	for relative in DELIVERED_MODULES:
		var bytes := FileAccess.get_file_as_bytes(
			MAGIC_SCRIPT_PATHS.project_dir().path_join(relative))
		out[relative] = {
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
	# exact bytes. `godot-market-trade` recorded the same lesson after it hit it.
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
				MAGIC_SCRIPT_PATHS.project_dir().path_join(relative))):
			return false
	return true


func _committed_row_count() -> int:
	var document: Variant = JSON.parse_string(_repo_text(RAW_CONFIG))
	if not (document is Dictionary):
		return -1
	var table: Variant = (document as Dictionary).get("magics", null)
	if not (table is Array):
		return -1
	return (table as Array).size()


## The distinct codes the observed refusals resolve to, read out of the fixture
## rather than listed, so the report cannot disagree with the checks.
func _observed_codes() -> Array:
	var out: Array = []
	for label in OBSERVED_REFUSALS:
		out.append(str((OBSERVED_REFUSALS[label] as Dictionary)["code"]))
	return out


## The number of malformed shapes `_check_fail_closed` walks. Declared here so
## the report states it rather than the report merely implying it, and pinned
## inside the function so the two cannot disagree.
const FAIL_CLOSED_CASE_COUNT := 77


# --- helpers -----------------------------------------------------------------


## The whole declared function inventory of the transport module, as this suite
## knows it. Read here rather than transcribed inline so the list lives beside
## the reserved stems that are checked against it.
func _api_function_inventory() -> Array:
	return [
		"_ready", "_call", "_failure", "_transport_message",
		"resolved_endpoint", "_unsupported", "_intent_body",
		"_collection_intent_body", "_combat_intent_body", "_magic_intent_body",
		"collect_income", "complete_collection_town", "magic_town",
		"list_sessions", "get_bootstrap", "place_building",
		"purchase_item", "move_building", "sell_building", "store_building",
		"upgrade_building", "build_construction", "expand_town",
		"level_up_town", "push_queue_unit_town", "pop_queue_unit_town",
		"resurrect_hero_town", "advance_research_town", "advance_quest_town",
		"complete_tutorial_town", "place_stored_item_town",
		"sell_stored_item_town", "combat_town", "reward_town",
	]


func _project_source(relative: String) -> String:
	var path := MAGIC_SCRIPT_PATHS.project_dir().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## A repository-relative file's text, or "" when unreadable. Used for the Python
## service modules and the committed config, which are not inside the Godot
## project.
func _repo_text(relative: String) -> String:
	var path := MAGIC_SCRIPT_PATHS.repo_root().path_join(relative)
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
## Both are needed and neither can serve the other, which this suite's first run
## measured rather than assumed: an operator scan must not see the `//` inside
## `preload("res://scripts/gameapi/boot_data.gd")`, while the balance guard and
## the five-pair guard must be able to see `["gold"]` and `"before"`. A single
## projection makes whichever guard it does not serve **vacuously true**, and a
## vacuously true guard is the failure mode this project has already recorded.
##
## The lexer is a proper two-state machine with backslash escapes. The version
## this replaces tested the **opening** quote before the closing one, so every
## literal re-opened itself and nothing after the first `preload` was ever
## blanked - which is why all thirty-one of that run's arithmetic "offences"
## were doc comments, and why the seven-name balance control found none of the
## seven names it exists to prove findable. The positive control below is what
## caught it: seven names, seven misses.
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


## Comments and string contents blanked. Newlines preserved.
func _code_only(body: String) -> String:
	return _lex(body, false)


## Comments blanked, string literals kept verbatim. Newlines preserved.
func _comment_free(body: String) -> String:
	return _lex(body, true)


func _code_lines(code: String) -> Array:
	var out: Array = []
	for line in code.split("\n"):
		out.append(str(line).rstrip("\r"))
	return out


## Every `func` name a GDScript source declares, in declaration order and
## **including duplicates**. Both `func` and `static func` are recognised: the
## typed-result module declares all eleven of its functions `static`, and an
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


func _swapped(source: Dictionary, field: String, value: Variant) -> Dictionary:
	var out: Dictionary = source.duplicate(true)
	out[field] = value
	return out


func _without(field: String) -> Dictionary:
	var out: Dictionary = OBSERVED_SUCCESS.duplicate(true)
	out.erase(field)
	return out


func _merged(base: Variant, extra: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	if base is Dictionary:
		for key in base:
			out[str(key)] = base[key]
	for key in extra:
		out[str(key)] = extra[key]
	return out


## True when a `magic_town` call binds its result without narrowing it to a
## concrete class. A call wrapped over several lines has its binding on an earlier
## line, so the walk goes back up to three lines.
func _binds_untyped(line: String, lines: Array, index: int) -> bool:
	var at := line.find("magic_town(")
	if at == -1:
		return true
	var head := line.substr(0, at)
	var back := 0
	while not head.contains("=") and back < 3 and index - back - 1 >= 0:
		back += 1
		head = str(lines[index - back]).strip_edges() + " " + head
	if not head.contains("="):
		return true
	if not head.contains("await"):
		return true
	var declared := head.split("=")[0].strip_edges()
	if not declared.contains(":"):
		return true
	return declared.substr(declared.rfind(":") + 1).strip_edges() == "Variant"


## One `RefusalCode.NAME: status,` row of `REFUSAL_HTTP_STATUS`, recognised
## structurally rather than by listing the codes here: the `RefusalCode.` prefix,
## an identifier, a colon, a three-digit integer, a comma.
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


func _collect_sources(root: String, prefix: String, out: Array) -> void:
	var directory := DirAccess.open(root.path_join(prefix))
	if directory == null:
		return
	for name in directory.get_files():
		if str(name).get_extension() == "gd":
			out.append(root.path_join(prefix).path_join(str(name)))
	for name in directory.get_directories():
		if str(name) == ".godot":
			continue
		_collect_sources(root, prefix.path_join(str(name)), out)


func _arg(prefix: String, fallback: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return fallback
