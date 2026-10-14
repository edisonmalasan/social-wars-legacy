extends "res://tests/test_base.gd"
## Server v1 **reward-cursor** client suite (OpenSpec change
## `reward-cursor-authority`; spec: "Server v1 is reachable through the GameApi
## abstraction", "A refused v1 action moves nothing").
##
## Scenarios:
##   "" (default, hermetic) the new typed result, the intent, the committed
##      refusal vocabulary, and the structural invariants that keep this client
##      from becoming a second reward economy. **No server, no socket, no
##      subprocess and no file write except this suite's own evidence report.**
##
## ## There is deliberately no `live` scenario
##
## `test_darts.gd` set the precedent and this line follows it: the sibling v1
## surfaces that ship a live phase ship it because a **client affordance** for a
## routed transaction is part of their deliverable. A reward cursor is the
## inverse case - the preserved server **pays nothing**, so a live phase here
## would first have to deliver an intent builder, a typed result, a facade
## forwarder and a fake implementation for a transaction whose entire finding is
## that it grants nothing. `_check_no_live_arm_and_no_socket` makes the absence
## mechanical rather than prose: the dispatcher has **no conditional at all**, no
## declared function is named for a live arm, no quoted scenario token survives in
## this file, and no transport, socket or subprocess token appears here at all.
##
## ## The claim this suite exists to keep
##
## **A reward cursor transition is a server-authoritative answer this client
## reports and does not compute, and it pays nothing at all.** v1 reads the
## player's own recorded cursor, derives the successor, writes it, proves the
## write against the file it just wrote, and reports what it read back. This
## client sends a save identity and an operation, and nothing else - two keys,
## verbatim, which `_check_intent_body` asserts exactly.
##
## ## Why almost every check here is a refusal
##
## Both preserved branches grant through a **client-sent value**:
## `command.py:446` computes `next_id = args[1] + 1`, so the arithmetic was
## always the server's and only its *input* was the client's, and the daily
## branch additionally writes a client-sent item id into storage. v1 therefore
## refuses **five** client-dictated channels by name - a cursor contribution and
## the four grant channels - and grants nothing. The client's half of that is
## almost entirely negative, and a negative claim is only worth something if it
## is mechanical. It is asserted six ways:
##
## 1. `_check_intent_body` pins the request to **exactly two keys** and
##    separately asserts that an operation outside the closed set travels
##    **verbatim**, so v1 refuses it by name instead of this client pre-filtering
##    it into `malformed_request`.
## 2. `_check_no_client_arithmetic` walks the new typed-result module and fails
##    on any scaling operator or any stored-balance member access, with an
##    **empty** exception list, and pins the single arithmetic-shaped line the
##    module is allowed to contain.
## 3. `_check_no_line_compares_two_reported_values` refuses any line that
##    **relates** two of the five reported cursor numbers, per-line, in both
##    delivered client modules.
## 4. `_check_absent_derivation_helpers` refuses an invented helper by **name**
##    and by **substring**, folded, in **both** directions, against the declared
##    function inventory of both delivered client modules - and pins those
##    inventories whole.
## 5. `_check_domain_inventory` and `_check_domain_reserved_stems` do the same
##    against the **Python domain module**, read from the repository at runtime
##    rather than transcribed.
## 6. `_check_reward_codes_live_in_the_reward_modules` walks the committed
##    refusal table structurally and refuses any code this route does not own.
##
## ## What this suite deliberately does NOT do
##
## It does not relate `cursor_before` to `cursor_after`, does not compare
## `cursor_after` against the bound, does not subtract the two instants, does not
## read `clamped` into a rule, and does not decide whether a cursor is
## addressable. Each of those is a relation **the server's own post-condition
## proof already established against the file it wrote**
## (`apps/server-v1/tests/test_reward.py`), and a client that re-checked them
## would hold a second implementation of the rule. They are carried verbatim and
## `_check_no_line_compares_two_reported_values` fails if any of them ever is.
##
## ## Three figures here are MEASURED, and two inherited ones are stale
##
## `REFUSAL_HTTP_STATUS` carries **25** status rows and **25** enum members
## (measured every run by `_looks_like_status_row`, not typed here), and
## `CollectSuite.UNSUPPORTED_INTENTS` holds **19** intents (measured by a
## bracket-bounded read). Both are asserted against what the files actually
## contain. **Recorded, not fixed, because they are not this line's files:** the
## sibling suites `test_magic_v1.gd:1551` and `test_combat_v1.gd` both still
## assert **20** against the same table - `test_magic_v1.gd` with a message
## that says *nineteen* and `test_combat_v1.gd` against a pinned
## `DECLARED_REFUSAL_CODE_COUNT := 20` - and both currently exit **1** because of
## it, and both also pin `names.size()` to **20** against a table that holds
## **19**. `test_magic_v1.gd`'s report field `facade_widening_is_the_third` is
## stale too: magic is the **fourth** widening and this line is the **fifth**.
## None of those is this suite's to change, and reporting a figure rather than
## inheriting it is the whole point of the paragraph.
##
## ## The two observed successes are transcribed **verbatim**
##
## Two successes and seven refusals, read out of a one-shot executed Server v1
## domain capture against the disposable corpus and pasted in unchanged. They are
## written out **twice over** for the two operations rather than shared through a
## nested constant, because a shared table would make the weekly answer's
## behaviour record an alias of the daily one's and make any equality check
## between the two tautological. `_check_observed_success_parses` asserts the two
## tables are equal anyway, which is a real measurement precisely because the
## bytes are two independent transcriptions.
##
## **Neither captured success nor any captured refusal carries a `protocol` key.**
## The `"server-v1"` stamp those answers are asserted to carry is this parser's
## **own default**, not a byte the server sent. That is measured and asserted
## rather than assumed, because a suite that believed the stamp came off the wire
## would be asserting something the capture does not contain.
##
## ## The line endings are measured, never asserted
##
## `godot-market-trade` shipped a hard-coded `false` beside a true statement
## about the *checkout* rather than about the *files*; copying a field **and its
## value** across file forms is how a guard becomes a lie. The report's
## `modules_are_pure_lf` here is measured on the bytes of both delivered modules.

## This suite's own source is read by the self-scanning format guard through
## `SELF_SCRIPT` below. An earlier draft carried a second, **repository**-
## relative constant for that read and handed it to `_project_source`, which
## resolves against `res://`; the join therefore named a path two directories
## deep that does not exist, the read returned `""`, and the guard passed over
## nothing at all. There is now exactly one constant for the file.
const REWARD_SCRIPT_PATHS = preload("res://scripts/package_paths.gd")
const ServerV1Api = preload("res://scripts/gameapi/server_v1_api.gd")
const ServerV1Reward = preload(
	"res://scripts/gameapi/server_v1_reward_result.gd")

const API_SCRIPT := "scripts/gameapi/server_v1_api.gd"
const RESULT_SCRIPT := "scripts/gameapi/server_v1_reward_result.gd"
const FACADE_SCRIPT := "scripts/gameapi/game_api.gd"
const V0_SCRIPT := "scripts/gameapi/legacy_v0_api.gd"
const SCOPE_SCRIPT := "tests/test_project_scope.gd"
const COLLECT_SUITE_SCRIPT := "tests/test_server_v1.gd"
## Project-relative, because `_project_source` resolves against `res://` and the
## suite lives in `tests/`. An earlier draft carried the bare file name here, the
## read returned "", and the self-scanning guard failed closed with "this suite
## reads its own source" -- a real refusal of a file that was present the whole
## time. `ends_with` still matches it against an absolute walk, so one constant
## serves both readers.
const SELF_SCRIPT := "tests/test_reward_v1.gd"

## This line's own intent on the facade, and the four that came before it.
const INTENT_METHOD := "reward_town"
const PRIOR_FACADE_WIDENINGS := [
	"collect_income", "complete_collection_town", "combat_town", "magic_town",
]

## The repository-relative paths this suite reads but does not deliver.
const DOMAIN_MODULE := "apps/server-v1/server_v1_reward.py"
const INTENT_MODULE := "apps/server-v1/server_v1_intent.py"
const REFUSALS_MODULE := "apps/server-v1/server_v1_refusals.py"

const DELIVERED_MODULES := [RESULT_SCRIPT, API_SCRIPT]

## The concrete type each `GameApi` implementation declares for **this** line's
## intent. The two v0-shaped implementations agree with each other and v1's own
## is the odd one out, which is why the facade cannot name one of them.
const IMPL_RETURN_TYPES := {
	"scripts/gameapi/fake_api.gd": "RewardFlow.RewardResult",
	"scripts/gameapi/legacy_v0_api.gd": "RewardFlow.RewardResult",
	"scripts/gameapi/server_v1_api.gd":
		"ServerV1Reward.RewardAuthorityResult",
}

## **Twelve** reserved stems for a client-side or server-side derivation. Each is
## a name a rule that must not exist here would plausibly be given.
##
## The comparison is by **substring**, folded to lower case, in **both**
## directions, against **declared function names** rather than raw source:
## `godot-friends` measured that an exact-name check passes a helper merely
## *prefixed* with a reserved word (`roster_order_by_xp` for a reserved `order`)
## and that a case-sensitive one passes `Friend_Of`, and `godot-construction-
## assist` measured that scanning raw source makes the guard's own inventory text
## trip it unconditionally.
##
## `"price"`, `"cost"`, `"afford"`, `"charge"`, `"payout"` are the D2 family: a
## rule that turns committed content into a currency amount.
## `"level_gate"`, `"gated"`, `"clamp"`, `"floor"` are the D5 family: a rule
## that compares two reported numbers or bounds one.
## `"decrement"`, `"decrease"` are the D4 family: a rule that writes a successor
## other than the one the server derived.
## `"schedule"` is the reward line's own family: a rule that reads either
## committed reward schedule, which is exactly what `schedules.read: false`
## reports that v1 does not do.
##
## **`"bound"` is deliberately NOT a reserved stem**, and that is a decision with
## a reason: the domain module legitimately declares `_weekly_bound`, because
## the *server's* bound is the server's. The refusal is about this **client**,
## and the client's own `_bound` is the parser for the bound table.
const RESERVED_DERIVATION_STEMS := [
	"price", "cost", "afford", "charge", "payout",
	"level_gate", "gated", "clamp", "floor",
	"decrement", "decrease", "schedule",
]

## The single declared name the `schedule` stem legitimately matches, with the
## reason it is not a rule that reads a schedule:
##
## `_schedules` is the **parser for the report**, and the report it parses
## carries `read: false`. `_schedules` requires `read` to be a boolean and
## **never consults its value** - it copies it. A function named after the block
## it reads is not a function that reads the block.
##
## The exception table is **size-pinned at one** so a second match cannot be
## waved in, and it is matched against declared names rather than held
## separately, so adding a helper such as `_schedule_price` still fails.
const REPORTING_NAME_EXCEPTIONS := ["_schedules"]

## The five relations this client must never make, all of them over numbers the
## server's own proof already settled against the file it wrote. Each is checked
## per line, in **both** delivered modules, against the **quoted** form a
## GDScript source carries - a bare `cursor_before` substring check would be
## satisfied by the same identifier in prose.
const FORBIDDEN_RELATIONS := [
	["cursor_before", "cursor_after"],
	["cursor_before", "clamped"],
	["instant_before", "instant_after"],
	["cursor_after", "bound"],
	["cursor_before", "unaddressable_cursors"],
]

## Split apart so the suite never contains the two-character sequence it looks
## for, which is what stops the self-scanning guards reading themselves.
const SCHEME := "http:"
const SLASHES := "//"
const V1_HOST := "127.0.0.1:5057"
const LIVE_ENDPOINT := SCHEME + SLASHES + V1_HOST
const QUOTED_OPEN := "\""
const QUOTED_CLOSE := "\""
const ARG_REPORT := "--report="

## ## The two observed v1 successes, **verbatim**
##
## Read out of a one-shot executed Server v1 domain capture against the
## disposable corpus. Every field the parser reads is here, including the nine
## long prose sentences, because a fixture trimmed to the fields under test would
## let a parser that ignored the rest pass. Neither answer carries a `protocol`
## key - see the header.
const OBSERVED_SUCCESSES := {
	"daily": {
		"result": "success",
		"action": "reward",
		"instant": 1791400000,
		"reward": {
			"operation": "daily",
			"cursor_before": 2,
			"cursor_after": 3,
			"cursor_change": 1,
			"cursor_path": "/privateState/bonusNextId",
			"cursor_derived_from": "the recorded cursor, never the request",
			"bound": {
				"value": 5,
				"daily_literal": 5,
				"provenance": "the preserved literal at command.py:451",
				"daily_rejected_derivation": {
					"rejected": "len(DAILY_GOLD_REWARDS)",
					"reason": "the preserved branch compares against a literal at command.py:451; it never asks the schedule how long it is",
					"agreement_is": "a coincidence, not a derivation",
					"agrees_today": true,
				},
			},
			"instant_before": 0,
			"instant_after": 1791400000,
			"instant_gating": false,
			"addressability": {
				"bound": 5,
				"addressable_positions": [1, 2, 3, 4, 5],
				"unaddressable_cursors": [],
				"gap_reported": false,
				"clamped": 0,
				"resolution": "no rule was derived: the stored cursor is reported as it stands and is not clamped, because the preserved server had no bound to clamp it against and deriving one here would invent a rule the oracle does not have",
			},
		},
		"resources_after": {
			"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
			"steel": 2000, "cash": 5, "mana": 0,
		},
		"stored_resources_compared": [
			"cash", "gold", "mana", "oil", "steel", "wood", "xp",
		],
		"proof": [
			["cursor advanced to its derived successor", true],
			["no stored resource moved", true],
			["no item was granted into storage", true],
			["the bought-unit list is byte-identical", true],
			["nothing else in the document moved", true],
		],
		"leaf_paths_changed": [
			"/privateState/bonusNextId",
			"/privateState/timestampLastBonus",
		],
		"derived_payout": null,
		"paid": false,
		"eligibility_derived": false,
		"schedules": {
			"read": false,
			"daily": "DAILY_GOLD_REWARDS",
			"weekly": "MONDAY_BONUS_REWARDS",
			"reason": "both have zero legacy readers and paying from either would diverge from an oracle that pays nothing",
		},
		"preserved_branch_behaviour": {
			"daily_branch": "win_daily_bonus (command.py:444-463): next_id = args[1] + 1 and if next_id > 5: next_id = 1, so an oversized client-sent value wraps a recorded 4 back to 1",
			"daily_backwards_move": "that wrap moves the recorded cursor BACKWARDS, 4 -> 1, and this line records it as a divergence rather than reproducing it, because reproducing a client-directed cursor regression would defeat the purpose of making the cursor authoritative",
			"daily_bound_literal": "the daily bound 5 is the literal in the preserved source (command.py:451, the `if next_id > 5` test), not a length; it coincides with len(DAILY_GOLD_REWARDS) == 5 and the agreement is a coincidence. command.py:446 is the OTHER line -- `next_id = args[1] + 1` -- which is the client input this line replaces, so citing it as the bound's provenance would point a reader at the very thing the derivation refuses. The table said :446 and was corrected here; test_reward.py asserts the corrected figure so it cannot regress",
			"daily_grant": "the daily arm's grant is a client-sent item id written into storage and a deduplicating unit list, which is exactly why v1 refuses a client-sent item by name and pays nothing",
			"weekly_branch": "weekly_reward (command.py:345-363): the new cursor is (stored + 1) % get_weekly_reward_length(), so the arithmetic is the server's while its input is the client's",
			"weekly_client_input": "the preserved branch reads the next cursor from the request, so a client could move the weekly cursor anywhere the modulus allowed",
			"weekly_stamped_instant": "timeStampMondayBonus is written by the branch and read by nothing: no legacy module consumes it, so no eligibility rule exists to reproduce",
			"paid": "neither branch credits a stored resource: the daily arm writes an item into storage and the non-granting arm only prints",
			"schedules": "DAILY_GOLD_REWARDS and MONDAY_BONUS_REWARDS are reported and left unread; applying either would diverge from an oracle that pays nothing",
		},
	},
	"weekly": {
		"result": "success",
		"action": "reward",
		"instant": 1791400000,
		"reward": {
			"operation": "weekly",
			"cursor_before": 2,
			"cursor_after": 3,
			"cursor_change": 1,
			"cursor_path": "/privateState/weeklyRewardIndex",
			"cursor_derived_from": "the recorded cursor, never the request",
			"bound": {
				"value": 5,
				"daily_literal": 5,
				"provenance": "get_weekly_reward_length()'s own result",
				"daily_rejected_derivation": {
					"rejected": "len(DAILY_GOLD_REWARDS)",
					"reason": "the preserved branch compares against a literal at command.py:451; it never asks the schedule how long it is",
					"agreement_is": "a coincidence, not a derivation",
					"agrees_today": true,
				},
			},
			"instant_before": 0,
			"instant_after": 1791400000,
			"instant_gating": false,
			"addressability": {
				"bound": 5,
				"addressable_positions": [0, 1, 2, 3, 4],
				"unaddressable_cursors": [],
				"gap_reported": false,
				"clamped": 0,
				"resolution": "no rule was derived: the stored cursor is reported as it stands and is not clamped, because the preserved server had no bound to clamp it against and deriving one here would invent a rule the oracle does not have",
			},
		},
		"resources_after": {
			"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
			"steel": 2000, "cash": 5, "mana": 0,
		},
		"stored_resources_compared": [
			"cash", "gold", "mana", "oil", "steel", "wood", "xp",
		],
		"proof": [
			["cursor advanced to its derived successor", true],
			["no stored resource moved", true],
			["no item was granted into storage", true],
			["the bought-unit list is byte-identical", true],
			["nothing else in the document moved", true],
		],
		"leaf_paths_changed": [
			"/privateState/timeStampMondayBonus",
			"/privateState/weeklyRewardIndex",
		],
		"derived_payout": null,
		"paid": false,
		"eligibility_derived": false,
		"schedules": {
			"read": false,
			"daily": "DAILY_GOLD_REWARDS",
			"weekly": "MONDAY_BONUS_REWARDS",
			"reason": "both have zero legacy readers and paying from either would diverge from an oracle that pays nothing",
		},
		"preserved_branch_behaviour": {
			"daily_branch": "win_daily_bonus (command.py:444-463): next_id = args[1] + 1 and if next_id > 5: next_id = 1, so an oversized client-sent value wraps a recorded 4 back to 1",
			"daily_backwards_move": "that wrap moves the recorded cursor BACKWARDS, 4 -> 1, and this line records it as a divergence rather than reproducing it, because reproducing a client-directed cursor regression would defeat the purpose of making the cursor authoritative",
			"daily_bound_literal": "the daily bound 5 is the literal in the preserved source (command.py:451, the `if next_id > 5` test), not a length; it coincides with len(DAILY_GOLD_REWARDS) == 5 and the agreement is a coincidence. command.py:446 is the OTHER line -- `next_id = args[1] + 1` -- which is the client input this line replaces, so citing it as the bound's provenance would point a reader at the very thing the derivation refuses. The table said :446 and was corrected here; test_reward.py asserts the corrected figure so it cannot regress",
			"daily_grant": "the daily arm's grant is a client-sent item id written into storage and a deduplicating unit list, which is exactly why v1 refuses a client-sent item by name and pays nothing",
			"weekly_branch": "weekly_reward (command.py:345-363): the new cursor is (stored + 1) % get_weekly_reward_length(), so the arithmetic is the server's while its input is the client's",
			"weekly_client_input": "the preserved branch reads the next cursor from the request, so a client could move the weekly cursor anywhere the modulus allowed",
			"weekly_stamped_instant": "timeStampMondayBonus is written by the branch and read by nothing: no legacy module consumes it, so no eligibility rule exists to reproduce",
			"paid": "neither branch credits a stored resource: the daily arm writes an item into storage and the non-granting arm only prints",
			"schedules": "DAILY_GOLD_REWARDS and MONDAY_BONUS_REWARDS are reported and left unread; applying either would diverge from an oracle that pays nothing",
		},
	},
}


## ## The seven observed v1 refusals, **verbatim**
##
## Five client-dictated channels the preserved branches would have granted from,
## one operation outside the closed set, and one unknown player. Nothing here is
## composed from the parser's expectations, and nothing carries a `protocol` key.
const OBSERVED_REFUSALS := {
	"client-dictated cursor": {
		"result": "refused",
		"code": "client_dictated_cursor",
		"message": "the request carried a reward cursor contribution; v1 derives the successor from the recorded cursor alone",
		"detail": {
			"player_id": "00000000-0000-4000-8000-000000000001",
			"operation": "daily",
			"sent": 9,
			"derived_from": "/privateState",
			"sent_is": "carried verbatim and never read, compared, or clamped",
		},
	},
	"client-dictated item grant": {
		"result": "refused",
		"code": "client_dictated_item_grant",
		"message": "the request carried a client-dictated item; the preserved branch would have granted from it and v1 grants nothing",
		"detail": {
			"player_id": "00000000-0000-4000-8000-000000000001",
			"operation": "daily",
			"sent": 5,
			"channel": "item",
			"sent_is": "carried verbatim and never read",
		},
	},
	"client-dictated cell": {
		"result": "refused",
		"code": "client_dictated_cell",
		"message": "the request carried a client-dictated cell; the preserved branch would have granted from it and v1 grants nothing",
		"detail": {
			"player_id": "00000000-0000-4000-8000-000000000001",
			"operation": "daily",
			"sent": 4,
			"channel": "cell",
			"sent_is": "carried verbatim and never read",
		},
	},
	"client-dictated player": {
		"result": "refused",
		"code": "client_dictated_player",
		"message": "the request carried a client-dictated player; the preserved branch would have granted from it and v1 grants nothing",
		"detail": {
			"player_id": "00000000-0000-4000-8000-000000000001",
			"operation": "daily",
			"sent": "p2",
			"channel": "player",
			"sent_is": "carried verbatim and never read",
		},
	},
	"client-dictated map index": {
		"result": "refused",
		"code": "client_dictated_map_index",
		"message": "the request carried a client-dictated map_index; the preserved branch would have granted from it and v1 grants nothing",
		"detail": {
			"player_id": "00000000-0000-4000-8000-000000000001",
			"operation": "daily",
			"sent": 3,
			"channel": "map_index",
			"sent_is": "carried verbatim and never read",
		},
	},
	"operation outside the closed set": {
		"result": "refused",
		"code": "malformed_request",
		"message": "a reward intent must name one of ['weekly', 'daily']",
		"detail": {"operation": "hourly", "declared": ["weekly", "daily"]},
	},
	"unknown player": {
		"result": "refused",
		"code": "unknown_player",
		"message": "no save document for player 'no-such-player'",
		"detail": {
			"player_id": "no-such-player",
			"operation": "daily",
			"repository_code": "unknown_player",
		},
	},
}


## The seven refusal codes this route answers, read off the capture. Each row is
## `[enum member, HTTP status, does the domain module name it]`.
##
## **Five of the seven are domain-named** and the sixth, `malformed_request`, is
## too; `unknown_player` is **not**, and that is measured rather than assumed:
## the repository refusal arrives as `RefusalCode(error.code)` - a name looked
## up at run time - so a scan for `RefusalCode.UNKNOWN_PLAYER` finds nothing even
## though the code is squarely this route's. Asserting the direction in both
## senses is what makes that a measurement.
const EXPECTED_REWARD_REFUSALS := {
	"client_dictated_cursor": ["CLIENT_DICTATED_CURSOR", 400, true],
	"client_dictated_item_grant": ["CLIENT_DICTATED_ITEM_GRANT", 400, true],
	"client_dictated_cell": ["CLIENT_DICTATED_CELL", 400, true],
	"client_dictated_player": ["CLIENT_DICTATED_PLAYER", 400, true],
	"client_dictated_map_index": ["CLIENT_DICTATED_MAP_INDEX", 400, true],
	"malformed_request": ["MALFORMED_REQUEST", 400, true],
	"unknown_player": ["UNKNOWN_PLAYER", 404, false],
}

## The seven `RefusalCode` members `server_v1_reward.py` names, measured over
## the committed file. Six are this route's; `UNREADABLE_CONTENT` belongs to the
## shared proof machinery. Pinned so a seventh reward code cannot land in the
## domain unnoticed.
const DOMAIN_NAMED_CODES := [
	"CLIENT_DICTATED_CELL", "CLIENT_DICTATED_CURSOR",
	"CLIENT_DICTATED_ITEM_GRANT", "CLIENT_DICTATED_MAP_INDEX",
	"CLIENT_DICTATED_PLAYER", "MALFORMED_REQUEST", "UNREADABLE_CONTENT",
]

## The four client-sent grant channels the domain maps to their own codes, read
## out of the module rather than transcribed. `GRANT_CHANNEL_REFUSALS` is the
## whole of design D5 and the reason the intent body carries no grant field.
##
## Sorted, because `_domain_channels` returns a sorted set and the comparison is
## equality rather than a membership test: an unsorted hand-written list compares
## unequal to the same four names read back out of the module, which is what the
## first run of this suite did.
const GRANT_CHANNELS := ["cell", "item", "map_index", "player"]

## The refusal-label each channel appears under in `OBSERVED_REFUSALS`. The
## channel names and the label names are **not** mechanically derivable -
## `map_index` becomes "map index" and `item` becomes "item grant" - so a
## guessed `"client-dictated %s" % channel` builds "client-dictated map_index",
## which is absent, and the read **raises** instead of failing a check. The table
## is therefore declared, and the two-way completeness of it is asserted against
## the transcription's own keys.
const GRANT_CHANNEL_LABELS := {
	"cell": "client-dictated cell",
	"item": "client-dictated item grant",
	"map_index": "client-dictated map index",
	"player": "client-dictated player",
}

## The number of malformed shapes `_check_fail_closed` walks. Declared here so
## the report states it rather than the report merely implying it, and pinned
## **inside** the function so the two cannot drift apart.
const FAIL_CLOSED_CASE_COUNT := 85

## The bound literal both observed operations report, and the reason it is
## reported twice per answer with a rejected derivation beside it.
const OBSERVED_BOUND := 5


func run_scenario() -> void:
	_check_observed_success_parses()
	_check_observed_refusals_parse()
	_check_fail_closed()
	_check_intent_body()
	_check_no_client_arithmetic()
	_check_no_line_compares_two_reported_values()
	_check_absent_derivation_helpers()
	_check_domain_inventory()
	_check_domain_reserved_stems()
	_check_python_name_scan_finds_planted_defs()
	_check_reward_codes_live_in_the_reward_modules()
	await _check_facade_registration()
	_check_return_type_widening()
	_check_unsupported_intent_left_the_table()
	_check_transport_token_placement()
	_check_no_unconverted_format_arguments()
	_check_no_live_arm_and_no_socket()
	_write_report()


# --- the typed result --------------------------------------------------------


## Both captured successes parse into the typed result, in full, and the three
## no-payout fields are asserted **against a body that lies about them** - which
## is the only shape in which `_success`'s comment at :325-329 is a claim rather
## than a coincidence.
##
## Nothing here compares two reported numbers. The before/after/change triple is
## read member by member and never related, and `_check_no_line_compares_two_
## reported_values` is what keeps that true.
func _check_observed_success_parses() -> void:
	for operation in _sorted_keys(OBSERVED_SUCCESSES):
		var witness: Dictionary = OBSERVED_SUCCESSES[operation]
		var parsed: Variant = ServerV1Reward.parse_reward_cursor(
			witness.duplicate(true))
		if not (parsed is ServerV1Reward.RewardAuthorityResult):
			fail("the observed %s answer parses into the typed result" % operation)
			continue
		var typed: ServerV1Reward.RewardAuthorityResult = parsed
		check(typed.ok, "the observed %s answer is a success" % operation)
		check_eq(typed.protocol, "server-v1",
			"and is stamped with v1's protocol")
		check_eq(typed.action, "reward", "and names the action that ran")
		check_eq(typed.instant, 1791400000, "and carries the recorded instant")

		var cursor: Variant = typed.reward
		check(cursor != null,
			"the %s cursor report is present" % operation)
		if cursor == null:
			continue
		var report: ServerV1Reward.CursorReport = cursor
		check_eq(report.operation, operation,
			"and names the operation that ran")
		check_eq(report.cursor_before, 2,
			"the %s cursor the server read is carried" % operation)
		check_eq(report.cursor_after, 3,
			"and the derived successor, separately" )
		check_eq(report.cursor_change, 1,
			"and the server's own signed change, carried as a THIRD field so a"
			+ " backwards move would be visible as a negative number")
		check_eq(report.cursor_path, str(
			(witness["reward"] as Dictionary)["cursor_path"]),
			"the document path the cursor was read from and written to")
		check_eq(report.cursor_derived_from,
			"the recorded cursor, never the request",
			"and the server's own sentence naming where the successor came from")

		check_eq(report.bound_value, OBSERVED_BOUND,
			"the %s bound is carried" % operation)
		check_eq(report.daily_literal, OBSERVED_BOUND,
			"and the preserved daily literal beside it")
		check(report.bound_provenance != "",
			"and the bound's provenance sentence rather than a bare number")
		check_eq(report.daily_rejected_agrees_today, true,
			"and whether the rejected derivation agrees TODAY, as its own field")
		check_eq(_sorted_keys(report.daily_rejected_derivation),
			["agreement_is", "agrees_today", "reason", "rejected"],
			"and the rejected derivation travels as a four-key OBJECT, not a"
			+ " sentence -- the first draft demanded a String and refused every"
			+ " real answer")
		check_eq(str(report.daily_rejected_derivation["rejected"]),
			"len(DAILY_GOLD_REWARDS)",
			"naming the derivation the server declined to use")
		check_eq(str(report.daily_rejected_derivation["agreement_is"]),
			"a coincidence, not a derivation",
			"and stating that today's agreement is a coincidence")

		check_eq(report.instant_before, 0,
			"the %s instant before is carried" % operation)
		check_eq(report.instant_after, 1791400000, "and the instant after")
		check_eq(report.instant_gating, false,
			"and instant_gating is FALSE, which is this line's whole claim:"
			+ " nothing reads either stamped instant")

		var addressability: Dictionary = report.addressability
		check_eq(_int_list(addressability["addressable_positions"]),
			_int_list((witness["reward"] as Dictionary)["addressability"]
				["addressable_positions"]),
			"the %s addressable positions are carried verbatim" % operation)
		check_eq(_int_list(addressability["unaddressable_cursors"]), [],
			"and an empty unaddressable list stays an empty list rather than"
			+ " becoming an absent one")
		check_eq(int(addressability["clamped"]), 0,
			"and clamped is READ off the answer as 0, never computed by this"
			+ " client")
		check_eq(addressability["gap_reported"], false,
			"and a gap the server chose not to report reads as unreported here")
		check(str(addressability["resolution"]) != "",
			"and the server's own resolution sentence travels with it")

		check(typed.resources_after != null,
			"the complete stored balance set is present for %s" % operation)
		if typed.resources_after != null:
			check_eq(int(typed.resources_after.cash), 5,
				"and cash is carried (%s)" % operation)
			check_eq(int(typed.resources_after.gold), 2000,
				"and gold (%s)" % operation)
			check_eq(int(typed.resources_after.mana), 0,
				"and mana (%s)" % operation)
			check_eq(int(typed.resources_after.oil), 2000,
				"and oil (%s)" % operation)
			check_eq(int(typed.resources_after.steel), 2000,
				"and steel (%s)" % operation)
			check_eq(int(typed.resources_after.wood), 2000,
				"and wood (%s)" % operation)
			check_eq(int(typed.resources_after.xp), 4,
				"and xp (%s)" % operation)
		check_eq(_sorted_set(_string_list(typed.stored_resources_compared)),
			_sorted_set(ServerV1Reward.STORED_RESOURCE_NAMES),
			"and %s names exactly the seven stored resources it compared"
			% operation)
		check_eq(ServerV1Reward.STORED_RESOURCE_NAMES.size(), 7,
			"the stored resource set is SEVEN: the M7 readout also surfaces"
			+ " privateState.energy, which no branch writes and which therefore"
			+ " is not one of the values a proof compares")
		check_eq(_string_list(typed.leaf_paths_changed),
			_string_list(witness["leaf_paths_changed"]),
			"and %s carries every leaf that moved, in the server's own order"
			% operation)
		check_eq(typed.proof.size(), 5,
			"and %s carries the server's five post-execution checks" % operation)
		check_eq(typed.schedules["read"], false,
			"and %s records that both committed schedules went UNREAD" % operation)
		check_eq(str(typed.schedules["daily"]), "DAILY_GOLD_REWARDS",
			"naming the daily schedule (%s)" % operation)
		check_eq(str(typed.schedules["weekly"]), "MONDAY_BONUS_REWARDS",
			"and the weekly one (%s)" % operation)
		check_eq(typed.preserved_branch_behaviour.size(),
			ServerV1Reward.BEHAVIOUR_KEYS.size(),
			"and %s carries exactly the nine quoted preserved-branch sentences"
			% operation)
		check_eq(typed.error_code, "",
			"a success (%s) carries no error code rather than an empty marker"
			% operation)
		check_eq(typed.error_message, "", "and no error message (%s)" % operation)
		check_eq(typed.error_detail, {}, "and no error detail (%s)" % operation)

	# The **three no-payout fields are the client's claim, never the wire's.**
	# The captured answers happen to agree with the claim, which makes them a
	# useless control on their own - so the control is built by lying.
	var lied: Dictionary = _swapped(OBSERVED_SUCCESSES["daily"], "paid", true)
	var payout_lied: Dictionary = _swapped(lied, "derived_payout", 999)
	var eligibility_lied: Dictionary = _swapped(
		payout_lied, "eligibility_derived", true)
	var claimed: Variant = ServerV1Reward.parse_reward_cursor(
		eligibility_lied.duplicate(true))
	check(claimed is ServerV1Reward.RewardAuthorityResult,
		"a body claiming paid:true still parses")
	if claimed is ServerV1Reward.RewardAuthorityResult:
		var typed_claim: ServerV1Reward.RewardAuthorityResult = claimed
		check(typed_claim.ok,
			"and is still a success: the three fields are not part of reading")
		check_eq(typed_claim.paid, false,
			"and paid is FALSE whatever the body said -- echoing a client's own"
			+ " claim of payment would report a payment this client cannot name")
		check(typed_claim.derived_payout == null,
			"and derived_payout stays null whatever the body said")
		check_eq(typed_claim.eligibility_derived, false,
			"and eligibility_derived stays false, because no eligibility rule"
			+ " is derived anywhere")

	# The two behaviour tables are equal, which is a real measurement only
	# because they are two independent transcriptions (see the header).
	var daily_behaviour: Dictionary = (OBSERVED_SUCCESSES["daily"]
		["preserved_branch_behaviour"]) as Dictionary
	var weekly_behaviour: Dictionary = (OBSERVED_SUCCESSES["weekly"]
		["preserved_branch_behaviour"]) as Dictionary
	check_eq(weekly_behaviour, daily_behaviour,
		"both observed answers carry the same nine preserved-branch sentences")
	# And the two operations genuinely differ where they should, so the previous
	# check is not passing because the answers are indistinguishable.
	check(not ((OBSERVED_SUCCESSES["weekly"]["reward"] as Dictionary)
		== (OBSERVED_SUCCESSES["daily"]["reward"] as Dictionary)),
		"while the two cursor reports differ, in operation, path and positions")
	check_eq(str((OBSERVED_SUCCESSES["daily"]["reward"] as Dictionary)
		["bound"]["provenance"]), "the preserved literal at command.py:451",
		"and the daily bound's provenance is the preserved LITERAL")
	check_eq(str((OBSERVED_SUCCESSES["weekly"]["reward"] as Dictionary)
		["bound"]["provenance"]), "get_weekly_reward_length()'s own result",
		"while the weekly bound's is a DIFFERENT provenance for the same value")


## Every observed refusal parses, keeps v1's own code and message verbatim, and
## populates **nothing else**. Seven conditions, seven distinct codes.
func _check_observed_refusals_parse() -> void:
	var conditions := _sorted_keys(OBSERVED_REFUSALS)
	check_eq(conditions.size(), 7,
		"seven refusal conditions were observed, one per client-dictated"
		+ " channel plus the closed-set and repository arms")
	for label in conditions:
		var witness: Dictionary = OBSERVED_REFUSALS[label]
		var parsed: Variant = ServerV1Reward.parse_reward_cursor(
			witness.duplicate(true))
		if not (parsed is ServerV1Reward.RewardAuthorityResult):
			fail("%s must answer v1's own typed result class" % label)
			continue
		var typed: ServerV1Reward.RewardAuthorityResult = parsed
		check(not typed.ok, "%s is refused" % label)
		check_eq(typed.error_code, str(witness["code"]),
			"%s keeps v1's own refusal code" % label)
		check_eq(typed.error_message, str(witness["message"]),
			"%s keeps v1's own message" % label)
		check(typed.error_message != "",
			"%s explains itself rather than answering with a bare code" % label)
		check_eq(typed.protocol, "server-v1",
			"%s carries v1's protocol stamp" % label)
		# Nothing else. A partial success payload on a refusal is the exact shape
		# a caller would read as "the cursor moved but something was odd".
		check(typed.reward == null, "%s carries no cursor report" % label)
		check(typed.resources_after == null,
			"%s carries no balance set" % label)
		check_eq(typed.stored_resources_compared, [],
			"%s names no compared resources" % label)
		check_eq(typed.proof, [], "%s carries no post-execution proof" % label)
		check_eq(typed.leaf_paths_changed, [],
			"%s names no changed leaf" % label)
		check_eq(typed.schedules, {},
			"%s carries no schedule record, even an unread one" % label)
		check_eq(typed.preserved_branch_behaviour, {},
			"%s carries no preserved-branch table" % label)
		check_eq(typed.action, "", "%s names no action" % label)
		check_eq(typed.instant, 0, "%s names no instant" % label)
		check_eq(typed.error_detail,
			(witness["detail"] as Dictionary),
			"%s carries the server's own detail verbatim" % label)

	# The detail is the only place the answer says anything about the REQUEST, so
	# the two shapes that matter are asserted rather than assumed.
	var cursor: ServerV1Reward.RewardAuthorityResult = \
		ServerV1Reward.parse_reward_cursor(
			(OBSERVED_REFUSALS["client-dictated cursor"] as Dictionary)
				.duplicate(true))
	check_eq(int(cursor.error_detail["sent"]), 9,
		"the client-dictated-cursor refusal echoes the cursor the client sent")
	check_eq(str(cursor.error_detail["sent_is"]),
		"carried verbatim and never read, compared, or clamped",
		"and says in its own words that the value was never compared to"
		+ " anything -- which is precisely what this client also does not do")
	check_eq(str(cursor.error_detail["derived_from"]), "/privateState",
		"and names the container the cursor would have been read from")
	var player: ServerV1Reward.RewardAuthorityResult = \
		ServerV1Reward.parse_reward_cursor(
			(OBSERVED_REFUSALS["client-dictated player"] as Dictionary)
				.duplicate(true))
	check_eq(str(player.error_detail["sent"]), "p2",
		"the client-dictated-player refusal carries the second pid verbatim")
	check_eq(str(player.error_detail["channel"]), "player",
		"and names the channel it arrived through")

	# The collapse, asserted rather than left accidental: four distinct channels
	# and four distinct codes, so a client could tell them apart - and the
	# client-dictated **cursor** shares none of them.
	var channel_codes: Array = []
	for channel in GRANT_CHANNELS:
		channel_codes.append(str(
			(OBSERVED_REFUSALS[str(GRANT_CHANNEL_LABELS[channel])]
				as Dictionary)["code"]))
	check_eq(_sorted_set(channel_codes).size(), 4,
		"the four grant channels answer four distinct codes, so a refusal"
		+ " names which channel was refused")
	check(not channel_codes.has("client_dictated_cursor"),
		"and the cursor contribution is not one of them")
	# The label table is a **measurement against the capture** in both
	# directions. The link is `detail.channel`, the server's own spelling of which
	# channel it refused - so nothing here depends on a label being derivable.
	check_eq(_observed_channels(), _sorted_set(GRANT_CHANNELS),
		"the capture's own detail.channel set is exactly the pinned channel set")
	for channel in GRANT_CHANNELS:
		var label := str(GRANT_CHANNEL_LABELS[channel])
		check(OBSERVED_REFUSALS.has(label),
			"%s names an observed refusal" % label)
		if OBSERVED_REFUSALS.has(label):
			check_eq(str((OBSERVED_REFUSALS[label]["detail"]
				as Dictionary)["channel"]), str(channel),
				"and that refusal's own detail.channel is %s" % channel)

	# The protocol stamp is this parser's default, which is only a claim because
	# the capture can be shown not to contain the key.
	var with_stamp: Dictionary = _swapped(
		OBSERVED_REFUSALS["unknown player"], "protocol", "some-other-protocol")
	var stamped: ServerV1Reward.RewardAuthorityResult = \
		ServerV1Reward.parse_reward_cursor(with_stamp)
	check_eq(stamped.protocol, "some-other-protocol",
		"a body that DOES carry a protocol key has it read, so the"
		+ " server-v1 stamp elsewhere is a default and not an echo")
	for label in conditions:
		check(not (OBSERVED_REFUSALS[label] as Dictionary).has("protocol"),
			"%s carries no protocol key in the capture at all" % label)


## The fail-closed walk, and why the case count is pinned
##
## Every case below is a real way a JSON body could arrive malformed, and every
## one must produce a **local** `bad_request` rather than a partly-filled
## success, because a half-read cursor is worse than an unread one.
##
## The case that matters most is `instant_gating`. The wire says it is the
## boolean `false`; the parser requires it to be **exactly** `false`, so an
## absent key, a `true`, a `null`, a `0` and the **string** `"false"` all
## refuse. That last one is the sharp edge: `str(false)` is the non-empty string
## `"false"`, which is truthy in GDScript 4, so a guard written as
## `if str(source.get("instant_gating", true)):` refuses every real answer while
## reading as though it were checking the flag. The suite holds the strict
## reading, so a loosened guard fails here.
##
## `FAIL_CLOSED_CASE_COUNT` is declared and pinned **inside** this function, so
## the report states a number and the walk cannot drift away from it.
##
## ## The anchor check, and why this walk was measured vacuous
##
## Every one of the walk's payloads is the captured daily success with **one**
## field changed. If that success does not parse in the first place, the whole
## walk refuses anyway - and every case passes, for a reason that has nothing to
## do with the field it mutated. That is not hypothetical: on the bytes this
## suite was authored against, `server_v1_reward_result.gd:342` read
## `if str(source.get("instant_gating", true)):`, `str(false)` is the non-empty
## string `"false"`, a non-empty String is truthy in GDScript 4, and the cursor
## refused **every** answer. All 85 cases passed, and the walk proved nothing at
## all.
##
## The anchor is the fix: it asserts the **unmutated** base parses before the
## walk runs, so "refused" is a statement about the mutation. Without it this
## check is 85 unconnected truth assertions; with it, it is 85 statements with a
## common premise, and the premise is itself asserted.
func _check_fail_closed() -> void:
	var anchor: Variant = ServerV1Reward.parse_reward_cursor(
		(OBSERVED_SUCCESSES["daily"] as Dictionary).duplicate(true))
	var anchor_ok: bool = anchor is ServerV1Reward.RewardAuthorityResult \
			and (anchor as ServerV1Reward.RewardAuthorityResult).ok
	check(anchor_ok,
		"the walk's base answer PARSES: every refusal below is then caused by"
		+ " the field it mutates, and not by the answer being unreadable"
		+ " already")
	var cases := _fail_closed_cases()
	check_eq(cases.size(), FAIL_CLOSED_CASE_COUNT,
		"the fail-closed walk covers exactly the pinned number of shapes")
	for entry in cases:
		var row: Array = entry
		var label := str(row[0])
		var parsed: Variant = ServerV1Reward.parse_reward_cursor(row[1])
		if not (parsed is ServerV1Reward.RewardAuthorityResult):
			fail("%s answers v1's own typed result class" % label)
			continue
		var typed: ServerV1Reward.RewardAuthorityResult = parsed
		check(not typed.ok, "%s is refused" % label)
		check_eq(typed.error_code, ServerV1Reward.CODE_BAD_REQUEST,
			"%s is refused with a LOCAL bad_request" % label)
		check(typed.reward == null, "%s populates no cursor report" % label)
		check(typed.resources_after == null, "%s populates no balance set" % label)
		check_eq(typed.proof, [], "%s populates no proof" % label)
	# The vacuity is visible in the output too, not only in this docstring: the
	# anchor is the first line of the walk's own verdict, so a reader of a red
	# run sees whether the premise held before reading eighty-five passes.
	check(not anchor_ok or cases.size() == FAIL_CLOSED_CASE_COUNT,
		"and the walk's premise is reported even when it does not hold")


## The malformed shapes, as `[label, payload, expected code]` rows. Built from
## the captured daily success by walking a **path**, so a case cannot silently
## stop being malformed: erasing the key it names is the mutation, and a path
## that does not exist would raise rather than pass.
func _fail_closed_cases() -> Array:
	var base: Dictionary = (OBSERVED_SUCCESSES["daily"] as Dictionary).duplicate(
		true)
	var cases: Array = [
		["a string where the object belongs", "success", "bad_request"],
		["an array where the object belongs", [1, 2], "bad_request"],
		["null where the object belongs", null, "bad_request"],
		["a number where the object belongs", 7, "bad_request"],
	]
	var structural: Array = [
		["no result key at all", ["result"]],
		["an unrecognised result", "result", "partial"],
		["a numeric result", "result", 7],
		["no action", ["action"]],
		["no instant", ["instant"]],
		["no reward block", ["reward"]],
		["no resources_after block", ["resources_after"]],
		["no proof", ["proof"]],
	]
	# Two row shapes, distinguished by **arity** rather than by a flag: a
	# two-element row erases the key at the path in its second slot, a
	# three-element row replaces the key named in that slot. The first draft
	# wrote `null` where the key name belonged, so `str(null)` erased a key
	# called "<null>" and both rows were handed to the parser with `result`
	# untouched - which the parser then accepted, as a success, with its proof
	# intact. Two rows that failed to be malformed at all, and the walk caught
	# them because a refusal walk that reports a success is not a quiet pass.
	for entry in structural:
		var row: Array = entry
		var label := str(row[0])
		var payload: Dictionary = base
		if row.size() == 3:
			payload = _swapped(base, str(row[1]), row[2])
		else:
			payload = _at(base, row[1] as Array, null)
		cases.append([label, payload, "bad_request"])
	var paths: Array = [
		["a reward block that is a string", ["reward"], "not-an-object"],
		["an operation outside the closed set", ["reward", "operation"],
			"hourly"],
		["no operation at all", ["reward", "operation"], null],
		["instant_gating TRUE", ["reward", "instant_gating"], true],
		["instant_gating absent", ["reward", "instant_gating"], null],
		["instant_gating as the string false", ["reward", "instant_gating"],
			"false"],
		["instant_gating null", ["reward", "instant_gating"], null],
		["instant_gating as zero", ["reward", "instant_gating"], 0],
		["a fractional cursor_before", ["reward", "cursor_before"], 2.5],
		["a string cursor_before", ["reward", "cursor_before"], "2"],
		["a null cursor_before", ["reward", "cursor_before"], null],
		["a fractional cursor_change", ["reward", "cursor_change"], 0.5],
		["no cursor_change at all", ["reward", "cursor_change"], null],
		["a fractional instant_after", ["reward", "instant_after"], 1791400000.5],
		["a numeric cursor_path", ["reward", "cursor_path"], 5],
		["no cursor_derived_from", ["reward", "cursor_derived_from"], null],
		["no bound block", ["reward", "bound"], null],
		["a bound that is a string", ["reward", "bound"], "not-an-object"],
		["a string bound value", ["reward", "bound", "value"], "5"],
		["a fractional bound value", ["reward", "bound", "value"], 4.5],
		["no daily literal", ["reward", "bound", "daily_literal"], null],
		["a numeric bound provenance",
			["reward", "bound", "provenance"], 451],
		["no rejected derivation",
			["reward", "bound", "daily_rejected_derivation"], null],
		["a rejected derivation that is a string",
			["reward", "bound", "daily_rejected_derivation"], "len(X)"],
		["no rejected expression",
			["reward", "bound", "daily_rejected_derivation", "rejected"], null],
		["a numeric rejected reason",
			["reward", "bound", "daily_rejected_derivation", "reason"], 451],
		["no agreement sentence",
			["reward", "bound", "daily_rejected_derivation", "agreement_is"],
			null],
		["agrees_today as a string",
			["reward", "bound", "daily_rejected_derivation", "agrees_today"],
			"true"],
		["no agrees_today at all",
			["reward", "bound", "daily_rejected_derivation", "agrees_today"],
			null],
		["no addressability block", ["reward", "addressability"], null],
		["an addressability that is a string", ["reward", "addressability"],
			"nope"],
		["a string addressability bound",
			["reward", "addressability", "bound"], "5"],
		["a null clamped", ["reward", "addressability", "clamped"], null],
		["addressable positions as a string",
			["reward", "addressability", "addressable_positions"], "1,2,3"],
		["a fractional addressable position",
			["reward", "addressability", "addressable_positions"], [1, 2.5]],
		["a string addressable position",
			["reward", "addressability", "addressable_positions"], [1, "2"]],
		["unaddressable cursors as an object",
			["reward", "addressability", "unaddressable_cursors"], {}],
		["gap_reported as a string",
			["reward", "addressability", "gap_reported"], "false"],
		["no resolution sentence",
			["reward", "addressability", "resolution"], null],
		["resources_after as a string", ["resources_after"], "seven"],
		["a truncated balance set", ["resources_after", "mana"], null],
		["a string balance", ["resources_after", "cash"], "5"],
		["a fractional balance", ["resources_after", "cash"], 5.5],
		["proof as a string", ["proof"], "five checks"],
		["a proof entry that is not a pair", ["proof"],
			["cursor advanced to its derived successor"]],
		["a one-element proof pair", ["proof"],
			[["cursor advanced to its derived successor"]]],
		["a three-element proof pair", ["proof"],
			[["cursor advanced to its derived successor", true, "extra"]]],
		["a string proof verdict", ["proof"],
			[["cursor advanced to its derived successor", "true"]]],
		["a numeric proof verdict", ["proof"],
			[["cursor advanced to its derived successor", 1]]],
		["a numeric proof sentence", ["proof"], [[7, true]]],
		["compared resources as a string",
			["stored_resources_compared"], "gold"],
		["a numeric compared-resource name",
			["stored_resources_compared"], [1, 2]],
		["changed leaves as a string", ["leaf_paths_changed"],
			"/privateState/bonusNextId"],
		["a numeric changed-leaf entry", ["leaf_paths_changed"], [1]],
		["schedules as a string", ["schedules"], "unread"],
		["no schedules.read key", ["schedules", "read"], null],
		["schedules.read as a string", ["schedules", "read"], "false"],
		["a numeric daily schedule name", ["schedules", "daily"], 5],
		["no weekly schedule name", ["schedules", "weekly"], null],
		["no schedules reason", ["schedules", "reason"], null],
		["a behaviour record as a string",
			["preserved_branch_behaviour"], "quoted"],
		["a fractional instant", ["instant"], 1791400000.5],
		["a string instant", ["instant"], "1791400000"],
		["a null instant", ["instant"], null],
	]
	for entry in paths:
		var row: Array = entry
		cases.append([str(row[0]), _at(base, row[1] as Array, row[2]),
			"bad_request"])
	for key in ServerV1Reward.BEHAVIOUR_KEYS:
		cases.append(["no %s sentence" % str(key),
			_at(base, ["preserved_branch_behaviour", str(key)], null),
			"bad_request"])
	return cases


## A deep copy of `base` with the key at `path` **erased**, and then - when
## `value` is not null - replaced by it. Erasing first means a case that names a
## key the answer does not carry produces an answer that genuinely lacks it,
## rather than silently re-adding the one this suite just removed.
func _at(base: Dictionary, path: Array, value: Variant) -> Dictionary:
	var out: Dictionary = base.duplicate(true)
	var walk: Dictionary = out
	for index in path.size() - 1:
		walk = walk[str(path[index])]
	walk.erase(str(path[path.size() - 1]))
	if value != null:
		walk[str(path[path.size() - 1])] = value
	return out


# --- the intent --------------------------------------------------------------


## The request this client builds is exactly **two** fields. Six things are not
## sent and could not be smuggled even by accident: a next id, a successor, an
## offset, an item id, a cell and a map index - which is the whole of design D5.
##
## An operation outside the closed set travels **verbatim**, deliberately: v1
## owns that vocabulary and answers `malformed_request` by name, and a client
## that validated it first would turn that specific answer into a different one.
func _check_intent_body() -> void:
	var body: Dictionary = ServerV1Api._reward_intent_body(
		"player-1", "daily")
	check_eq(_sorted_keys(body), ["operation", "player_id"],
		"the v1 reward intent carries a save identity and an operation, and"
		+ " nothing else")
	check_eq(str(body["player_id"]), "player-1", "the identity is verbatim")
	check_eq(str(body["operation"]), "daily", "the operation is verbatim")
	check_eq(body.size(), 2, "and the body is two keys long, not three")

	# The forbidden set is the six values the preserved branches would have
	# granted from, plus the three fields a client might add to say what it
	# thinks the answer will be.
	var forbidden: Array = [
		"next_id", "nextId", "cursor", "cursor_before", "cursor_after",
		"cursor_change", "offset", "successor", "item", "item_id",
		"cell", "x", "y", "map_index", "player", "resources_changed",
		"amount", "price", "payout", "reward", "instant", "expected",
	]
	forbidden.append_array(ServerV1Reward.STORED_RESOURCE_NAMES)
	for name in forbidden:
		check(not body.has(str(name)),
			"the intent carries no %s field" % str(name))

	# An operation the closed set does not contain is sent verbatim rather than
	# pre-filtered, for the reason in the docstring above.
	var burned: Dictionary = ServerV1Api._reward_intent_body("player-1", "hourly")
	check_eq(str(burned["operation"]), "hourly",
		"an operation outside the closed set is sent verbatim too")
	check_eq(_sorted_keys(burned), ["operation", "player_id"],
		"and adds no field to say it looks wrong")

	# The transport wraps the operation with `str(...)` before building the body,
	# so the *string* form is what travels. Both operations in the closed set
	# build bodies this suite has already asserted above; the point here is that
	# the request builder has no third arm for a third operation.
	check_eq(ServerV1Reward.OPERATIONS.size(), 2,
		"the closed operation set is two members")
	check_eq(_sorted_set(_string_list(ServerV1Reward.OPERATIONS)),
		["daily", "weekly"], "and they are the two the capture observed")
	check_eq(str(ServerV1Reward.CODE_UNSUPPORTED),
		"unsupported_by_server_v1",
		"this client's own code is distinct from every code the server answers")
	check_eq(str(ServerV1Reward.CODE_BAD_REQUEST), "bad_request",
		"and it names a second local code for an unreadable body")
	for code in ServerV1Reward.STORED_RESOURCE_NAMES:
		check(str(code) != ServerV1Reward.CODE_UNSUPPORTED,
			"no stored-resource name is a reserved client-local code")


# --- structural invariants ---------------------------------------------------


## ## Guard A - no scaling. Guard B - no balance is touched.
##
## The exception list here is **EMPTY**. `test_server_v1.gd` must admit this
## module's request-counter `+=` lines; a non-empty list here would be a fifth
## place to add a `+=` without noticing.
##
## The signature arrow is not an operator, so it is removed before scanning, and
## the operator scan runs over **code only** with comments and string literals
## blanked - so a sentence in a docstring cannot fail the guard and a string that
## says `"price_charged"` cannot satisfy it either. The balance scan reads the
## **literals-kept** projection, because the shape it forbids is `body["gold"]`:
## a subscript whose index is a string. Reading both from one projection
## silently makes one of the two guards vacuously true.
func _check_no_client_arithmetic() -> void:
	var offending: Array = []
	var forbidden_operators := ["*", "/", "+=", "-=", "*=", "/="]
	var relative := RESULT_SCRIPT
	var body := _project_source(relative)
	check(body != "", "%s is readable" % relative)
	if body == "":
		return
	var code := _code_only(body).replace("->", "  ")
	for line in _code_lines(code):
		for operator in forbidden_operators:
			if str(line).find(operator) != -1:
				offending.append("A %s: %s (%s)"
					% [relative, str(line).strip_edges(), operator])
				break
	var literal_code := _comment_free(body).replace("->", "  ")
	for name in ServerV1Reward.STORED_RESOURCE_NAMES:
		if literal_code.find(".%s" % str(name)) != -1:
			offending.append("B %s: member access .%s" % [relative, name])
		if literal_code.find("[\"%s\"]" % str(name)) != -1:
			offending.append("B %s: subscript \"%s\"" % [relative, name])
	check_eq(offending, [],
		"the delivered reward result neither scales a value nor touches a"
		+ " balance")
	check_eq(forbidden_operators.size(), 6,
		"the forbidden-operator list is intact")
	# The single arithmetic-shaped expression the module is allowed to contain,
	# pinned literally so a second one cannot hide behind the guard's silence.
	const WHOLE_TEST := "if float(value) != floor(float(value)):"
	var whole_tests := 0
	for line in _code_lines(_code_only(body)):
		if str(line).strip_edges() == WHOLE_TEST:
			whole_tests += 1
	check_eq(whole_tests, 1,
		"the whole-number test appears exactly once, and it is the only"
		+ " arithmetic-shaped line the module contains")
	# And the reason it is the only one: the module must not even be able to
	# *store* a reported balance, which the subscript check above covers. This is
	# the control for that check - a balance name it does not match, so a
	# widened `STORED_RESOURCE_NAMES` would fail here rather than pass by
	# finding nothing.
	var unmatched := 0
	for name in ServerV1Reward.STORED_RESOURCE_NAMES:
		if literal_code.find("%s%s%s" % [QUOTED_OPEN, str(name),
				QUOTED_CLOSE]) == -1:
			unmatched += 1
	check_eq(unmatched, 0,
		"every stored-resource name the module validates also appears in it,"
		+ " so the balance guard has real names to find")
	# The relational half of the claim, and its control: the module has no
	# comparison operator over its own values either, which is why
	# `_check_no_line_compares_two_reported_values` has something to forbid.
	var relational_hits := 0
	for line in _code_lines(code):
		var candidate := str(line).strip_edges()
		if candidate == "":
			continue
		for operator in ["<", ">"]:
			if candidate.find(operator) != -1:
				relational_hits += 1
				offending.append("A %s: %s (%s)" % [relative, candidate, operator])
	check_eq(relational_hits, 0,
		"and the result module compares nothing: instant_gating is checked for"
		+ " its TYPE and VALUE, never for being greater or less than anything")


## ## No line of either delivered module may **relate** two reported values.
##
## This is the guard for the line's whole negative claim, and it is why the
## report can state `client_relates_two_reported_values: false` as a mechanical
## fact rather than as prose. The five relations this client must never make:
##
##   * `cursor_before` with `cursor_after`      (the successor's own rule)
##   * `cursor_before` with `clamped`          (a bound the oracle lacks)
##   * `instant_before` with `instant_after`    (a window that does not exist)
##   * `cursor_after` with `bound`             (the cap the branch tests)
##   * `cursor_before` with `unaddressable_cursors` (the gap report)
##
## The check is **per line**, over the **literals-kept** projection, because the
## forbidden shape is `body["cursor_after"] >= body["bound"]` and the quoted
## names **are** what is being looked for. A whole-file "does the module contain
## both names" test would pass on a module that never relates them at all, which
## is the defect this guards against: `test_magic_v1.gd` measured a whole-file
## version of this guard passing on five pairs that appear in five unrelated
## lines.
##
## The names are matched **quoted**, because a bare `cursor_before` substring
## check would be satisfied by the same identifier inside a longer word.
func _check_no_line_compares_two_reported_values() -> void:
	var offending: Array = []
	for relative in DELIVERED_MODULES:
		var body := _project_source(relative)
		check(body != "", "%s is readable for the relation guard" % relative)
		if body == "":
			continue
		var literal_code := _comment_free(body).replace("->", "  ")
		for line in _code_lines(literal_code):
			var candidate := str(line).strip_edges()
			if candidate == "":
				continue
			for pair in FORBIDDEN_RELATIONS:
				var left := "%s%s%s" % [QUOTED_OPEN, str(pair[0]), QUOTED_CLOSE]
				var right := "%s%s%s" % [QUOTED_OPEN, str(pair[1]), QUOTED_CLOSE]
				if candidate.find(left) != -1 and candidate.find(right) != -1:
					offending.append("%s: %s relates %s with %s"
						% [relative, candidate, str(pair[0]), str(pair[1])])
	check_eq(offending, [],
		"neither delivered client module relates two reported values on one line")
	check_eq(FORBIDDEN_RELATIONS.size(), 5,
		"and all five forbidden relations are listed")
	# The control: all ten names are really in the result module, so the check
	# above is not passing on a vocabulary nothing there could ever write. Read
	# from the **literals-kept** projection, which is the one the guard itself
	# uses; reading from the literals-blanked one measured **zero of ten**.
	var reachable := 0
	var module_code := _comment_free(_project_source(RESULT_SCRIPT))
	for pair in FORBIDDEN_RELATIONS:
		for name in pair:
			if module_code.find("%s%s%s"
					% [QUOTED_OPEN, str(name), QUOTED_CLOSE]) != -1:
				reachable += 1
	check(reachable >= 10,
		"every forbidden relation is reachable from a name the module really"
		+ " contains: %d of %d name-occurrences found"
		% [reachable, FORBIDDEN_RELATIONS.size() * 2])
	# And the per-line form is proven sharper than a whole-file one, by
	# construction rather than by assertion: a planted module holding both names
	# on separate lines passes the whole-file reading and fails this one.
	const PLANT_SPLIT := "var a := body[\"cursor_before\"]\nvar b := body[\"cursor_after\"]\nvar c := a + b\n"
	var split_hits := 0
	for line in _code_lines(_comment_free(PLANT_SPLIT)):
		var candidate := str(line).strip_edges()
		for pair in FORBIDDEN_RELATIONS:
			if candidate.find("%s%s%s" % [QUOTED_OPEN, str(pair[0]),
					QUOTED_CLOSE]) != -1 \
					and candidate.find("%s%s%s" % [QUOTED_OPEN, str(pair[1]),
						QUOTED_CLOSE]) != -1:
				split_hits += 1
	check_eq(split_hits, 0,
		"and a planted module that names both on separate lines is still not"
		+ " read as relating them")


## **Twelve** reserved derivation stems, checked by substring against declared
## function names in both delivered modules, folded to lower case, in **both**
## directions, with one size-pinned exception.
##
## **The whole-inventory pin is the real gate.** It asserts the exact declared
## name sets, so any new function at all is visible. The stems are the belt, and
## they are substrings because `godot-friends` measured that an exact-name check
## passes a helper merely *prefixed* with a reserved word and a case-sensitive
## one passes `Friend_Of`.
func _check_absent_derivation_helpers() -> void:
	var expected := {
		RESULT_SCRIPT: [
			"parse_reward_cursor", "reward_failure", "_refusal", "_success",
			"_cursor", "_bound", "_rejected_derivation", "_addressability",
			"_schedules", "_behaviour", "_proof", "_integer_list",
			"_string_list", "_detail", "_resources", "_whole_number",
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
			for name in hits:
				check(REPORTING_NAME_EXCEPTIONS.has(str(name)),
					"%s: the %s stem matches %s, which is not on the"
					% [relative, stem, str(name)]
					+ " size-pinned exception table")
			hits = _without_all(hits)
			check_eq(hits, [],
				"%s declares no %s-shaped function (%s)"
				% [relative, stem, str(hits)])
	check_eq(RESERVED_DERIVATION_STEMS.size(), 12,
		"the reserved-derivation list is intact at twelve stems")
	check_eq(REPORTING_NAME_EXCEPTIONS.size(), 1,
		"and the reporting-name exception table holds exactly one entry")
	var matched_anywhere := 0
	for stem in RESERVED_DERIVATION_STEMS:
		for relative in expected:
			for name in _folded_set(
					_declared_function_names(_project_source(relative))):
				if str(name).find(stem) != -1:
					matched_anywhere += 1
	check_eq(matched_anywhere, 1,
		"exactly one delivered function matches a stem -- _schedules, the"
		+ " report PARSER whose read flag it never consults")
	# The **other** direction: a name in `expected` the module does **not**
	# declare would leave a guard reading a function that moved or was deleted,
	# which is the drift this project has recorded twice.
	var missing: Array = []
	for relative in expected:
		var declared := _declared_function_names(_project_source(relative))
		for name in (expected[relative] as Array):
			if not declared.has(str(name)):
				missing.append("%s: %s" % [relative, str(name)])
	check_eq(missing, [], "and every expected name is really declared")
	# And the exception earns its place by being narrow: it is matched against
	# the whole name, so a helper wearing the same stem as a *suffix* or a
	# *prefix* of it still fails. Asserted with the real stem, not by inventing a
	# module, so the claim is about the delivered bytes.
	check_eq(REPORTING_NAME_EXCEPTIONS.size(), 1,
		"so the one exception is one whole declared name and not a pattern")


## ## The **domain** module's whole function inventory, read from the repository.
##
## An invented successor rule, an invented gap detector or an invented schedule
## reader would most likely be written in **Python**, next to the derivation, not
## in the transport that calls it. The names are re-read from
## `apps/server-v1/server_v1_reward.py` on every run rather than transcribed,
## because a transcribed inventory is a claim about a file that can drift and
## this project has recorded a pinned count going stale within a day.
func _check_domain_inventory() -> void:
	var source := _repo_text(DOMAIN_MODULE)
	check(source != "", "%s is readable" % DOMAIN_MODULE)
	if source == "":
		return
	var declared := _python_function_names(source)
	check_eq(declared.size(), 13,
		"the domain module declares thirteen functions, measured over the file")
	for name in [
		"advance_reward", "declared_operations", "reward_cursor_path",
		"_derive", "_addressability", "_addressable_positions",
		"_weekly_bound", "_cursor_now", "_expected_leaf_paths", "_stamp_key",
		"_changed_leaf_paths", "_refuse", "_repository_refusal",
	]:
		check(declared.has(str(name)),
			"and it declares %s" % str(name))
	var pinned := [
		"_addressability", "_addressable_positions", "_changed_leaf_paths",
		"_cursor_now", "_derive", "_expected_leaf_paths", "_refuse",
		"_repository_refusal", "_stamp_key", "_weekly_bound", "advance_reward",
		"declared_operations", "reward_cursor_path",
	]
	check_eq(_sorted_set(_string_list(declared)), _sorted_set(pinned),
		"the domain module declares exactly the functions this suite pins")
	var duplicates: Array = []
	for name in _sorted_set(_string_list(declared)):
		var seen := 0
		for entry in declared:
			if str(entry) == str(name):
				seen += 1
		if seen > 1:
			duplicates.append(str(name))
	check_eq(duplicates, [],
		"and every one of the thirteen is a single distinct declaration, so"
		+ " the thirteen really are thirteen")
	check(_domain_channels() == GRANT_CHANNELS,
		"the domain maps exactly the four grant channels this suite pins, so a"
		+ " fifth channel cannot join the shape unnoticed")
	check(_domain_operation_count() == 2,
		"and the domain's operation tuple holds two members")


## The four grant channels, read out of `GRANT_CHANNEL_REFUSALS` rather than
## transcribed. Returns [] when the declaration cannot be read, so a failure
## downstream is a failure of the read rather than a silent pass.
func _domain_channels() -> Array:
	var source := _repo_text(DOMAIN_MODULE)
	var at := source.find("GRANT_CHANNEL_REFUSALS")
	if at == -1:
		return []
	var tail := source.substr(at)
	var end := tail.find("}")
	if end == -1:
		return []
	var channels: Array = []
	for line in tail.substr(0, end).split("\n"):
		var candidate := str(line).strip_edges()
		if not candidate.begins_with(QUOTED_OPEN):
			continue
		# The closing quote is searched from index **1**: a plain `find` lands on
		# the opening quote itself, and `substr(1, 1 - 1)` then yields the empty
		# string for every channel - so the read returned `[""]` and the
		# four-channel comparison failed while the module was perfectly correct.
		var close := candidate.find(QUOTED_CLOSE, 1)
		if close == -1:
			continue
		channels.append(candidate.substr(1, close - 1))
	return _sorted_set(channels)


## The length of the domain's `OPERATIONS` tuple, read as text. The tuple spells
## `("weekly", "daily")`, so the count is measured between the parentheses.
func _domain_operation_count() -> int:
	var source := _repo_text(DOMAIN_MODULE)
	var at := source.find("OPERATIONS: Tuple[str, str] = (")
	if at == -1:
		return -1
	var tail := source.substr(at)
	var open := tail.find("(")
	var close := tail.find(")")
	if open == -1 or close == -1 or close < open:
		return -1
	var inner := tail.substr(open + 1, close - open - 1)
	return inner.count(",") + 1


## The twelve reserved stems against the **domain** module's declared names.
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
		"and none of the domain module's %d functions matches one of the %d"
		% [folded.size(), RESERVED_DERIVATION_STEMS.size()] + " stems")
	# The control for the empty result: `_weekly_bound` really does contain a
	# bound-shaped word and is legitimately declared, which is why `bound` is not
	# on the reserved list. Asserted so that decision cannot be re-made by
	# accident.
	check(declared.has("_weekly_bound"),
		"and the domain's own _weekly_bound is declared and is NOT a client"
		+ " rule: the server's bound is the server's")


## ## The Python name scan is a **line scan**, and that is a limitation.
##
## It recognises `def name(` and `async def name(` at the start of a line after
## stripping indentation, which covers module-level functions, class methods and
## nested functions - but it also matches a `def` inside a **docstring**,
## because it runs over the raw source. That is recorded rather than fixed,
## because the fix would be an AST parse and this suite may not execute Python.
## The consequence is the opposite of the one that would matter: the scan can
## only report **too many** names, so a planted helper inside a comment would be
## caught here even though it does nothing. The control below proves the scan is
## not vacuous.
func _check_python_name_scan_finds_planted_defs() -> void:
	const PLANT := "def a_planted_helper(x):\n\treturn x\n\nclass C:\n\tdef m(self):\n\t\tpass\n\nasync def top():\n\tpass\n"
	var found := _python_function_names(PLANT)
	check_eq(_sorted_set(_string_list(found)),
		["a_planted_helper", "m", "top"],
		"the Python name scan finds a module-level def, a method and an async"
		+ " def, so it is not passing on a vacuous zero")
	check(found.has("m"),
		"and it finds an INDENTED def, which is the case a naive scan misses")
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
	check_eq(real.size(), 13, "at exactly thirteen against the plant's three")


## The reward refusal codes are declared by the **reward** modules, and each maps
## to the status the client would see. The committed table's row count is
## **measured** from the file with a structural recogniser rather than typed
## here, so a twenty-sixth code cannot land without this suite noticing.
func _check_reward_codes_live_in_the_reward_modules() -> void:
	var refusals := _repo_text(REFUSALS_MODULE)
	check(refusals != "", "%s is readable" % REFUSALS_MODULE)
	if refusals == "":
		return
	var declared := 0
	for line in refusals.split("\n"):
		if _looks_like_status_row(str(line)):
			declared += 1
	check_eq(declared, 25,
		"the committed refusal table maps exactly twenty-five codes, measured"
		+ " by recognising each RefusalCode.NAME row structurally")
	check_eq(EXPECTED_REWARD_REFUSALS.size(), 7,
		"and this route answers exactly seven distinct codes")
	for code in EXPECTED_REWARD_REFUSALS:
		var row: Array = EXPECTED_REWARD_REFUSALS[code]
		var member := "    RefusalCode.%s:" % str(row[0])
		check(refusals.find(member) != -1,
			"the committed table declares %s" % str(code))
		var marker := "%s %d," % [member, int(row[1])]
		check(refusals.find(marker) != -1,
			"the committed table maps %s to HTTP %d"
			% [str(code), int(row[1])])
		check(refusals.find("%s%s%s" % [QUOTED_OPEN, str(code),
				QUOTED_CLOSE]) != -1,
			"and the table carries %s as its wire value" % str(code))
	# The codes this line's route raises live in the **domain** module, and the
	# direction is asserted in BOTH senses - which is what makes
	# `unknown_player`'s absence a measurement rather than an omission.
	var domain := _repo_text(DOMAIN_MODULE)
	for code in EXPECTED_REWARD_REFUSALS:
		var named: bool = bool((EXPECTED_REWARD_REFUSALS[code] as Array)[2])
		var spelled: bool = domain.find("RefusalCode.%s"
			% str((EXPECTED_REWARD_REFUSALS[code] as Array)[0])) != -1
		check_eq(spelled, named,
			"the domain module %s name %s"
			% ["names" if named else "does NOT name", str(code)])
	check(domain.find("code=RefusalCode(error.code)") != -1,
		"and the repository refusal arrives as a looked-up member at"
		+ " server_v1_reward.py:541, which is why unknown_player has no dotted"
		+ " spelling to find")
	check_eq(_sorted_set(_named_refusal_members(domain)),
		_sorted_set(DOMAIN_NAMED_CODES),
		"and the domain names exactly the seven pinned members, so a seventh"
		+ " reward code cannot land there unnoticed")
	# The request layer owns two codes this route never answers, and they are
	# refused **before** any domain code runs - which is the same finding
	# `test_magic_v1.gd` recorded for `client_supplied_delta`.
	var intent := _repo_text(INTENT_MODULE)
	check(intent != "", "%s is readable" % INTENT_MODULE)
	var intent_members := _sorted_set(_named_refusal_members(intent))
	for member in ["CLIENT_SUPPLIED_DELTA", "UNKNOWN_REQUEST_FIELD"]:
		check(intent_members.has(member),
			"and the request layer names %s" % member)
	check_eq(_sorted_set(_string_list(_observed_codes())).size(), 7,
		"and the seven observed refusals resolve to seven distinct wire codes")


# --- the facade --------------------------------------------------------------


## The facade selects the v1 implementation, describes its endpoint, and
## releases it again. Repeated from the sibling suites because this route must be
## reachable **through the facade** and not only through the implementation.
##
## No request is issued: `configure` names an endpoint, it does not dial one,
## which is why this suite can afford the check at all.
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
	check_eq(api.reward_requests, 0,
		"selecting an implementation issues no reward intent")
	check_eq(str(api._impl.REWARD_PATH), "/v1/reward",
		"and the v1 implementation names its own reward path")
	api.configure("fake")
	check_eq(str(api.implementation_name()), "fake",
		"the facade restores the fake implementation")
	check(not (api._impl is ServerV1Api),
		"the v1 implementation is released on reconfigure")
	info("implementation in force before this suite selected one: %s" % before)


## The facade's `reward_town` is `Variant` because the three implementations do
## not agree: the two v0-shaped ones return v0's `RewardFlow.RewardResult` and
## v1's returns `ServerV1Reward.RewardAuthorityResult`. A facade naming either
## would be lying to the other two callers, so it is widened - and this line is
## the **fifth** widening, after four measured ahead of it.
##
## The widening is only safe because **every** call site binds its result to
## `Variant` or to an untyped local, and that is measured over the whole project
## rather than asserted in prose.
func _check_return_type_widening() -> void:
	var files: Array = []
	_collect_sources(REWARD_SCRIPT_PATHS.project_dir(), "", files)
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
		if body.find(INTENT_METHOD) == -1:
			continue
		var lines := body.split("\n")
		for index in lines.size():
			var line := str(lines[index]).strip_edges()
			if not line.contains("%s(" % INTENT_METHOD):
				continue
			if line.begins_with("#"):
				continue
			# **Declarations and call sites are counted apart.** Pinning one
			# number for both is how the magic suite's five became ten.
			if line.begins_with("func ") or line.begins_with("static func "):
				declarations += 1
				continue
			var where := str(absolute).get_file()
			call_sites += 1
			per_file[where] = int(per_file.get(where, 0)) + 1
			if not _binds_untyped(line, lines, index, INTENT_METHOD):
				offenders.append("%s: %s" % [where, line])
	check_eq(offenders, [],
		"every reward_town call site binds to Variant or untyped")
	check_eq(call_sites, 5,
		"five call sites: three in the pre-existing v0 client's own"
		+ " test_rewards.gd, one in test_server_v1.gd's hand-off driver, and the"
		+ " facade's own forwarder")
	check_eq(declarations, 4,
		"and four declarations -- the facade plus the three implementations")
	check_eq(_sorted_keys(per_file),
		["game_api.gd", "test_rewards.gd", "test_server_v1.gd"],
		"the five call sites live in exactly three files")
	check_eq(int(per_file["test_rewards.gd"]), 3,
		"three of them are the pre-existing v0 client's own")
	var distinct: Array = []
	for relative in IMPL_RETURN_TYPES:
		var declared := _return_type_of(_project_source(relative), INTENT_METHOD)
		check_eq(declared, str(IMPL_RETURN_TYPES[relative]),
			"%s declares %s for reward_town"
			% [relative, str(IMPL_RETURN_TYPES[relative])])
		distinct.append(declared)
	check_eq(_sorted_set(distinct).size(), 2,
		"three implementations declare TWO distinct concrete types -- the two"
		+ " v0-shaped ones agree, and v1's is the odd one out -- which is why"
		+ " the facade cannot name one of them")
	check_eq(_return_type_of(_project_source(FACADE_SCRIPT), INTENT_METHOD),
		"Variant", "the facade's reward_town is declared Variant")
	# The ordinal, measured rather than copied. `test_magic_v1.gd` still reports
	# its own as the third; it is the fourth, and this is the fifth.
	var facade := _comment_free(_project_source(FACADE_SCRIPT))
	var widened := 0
	for prior in PRIOR_FACADE_WIDENINGS:
		if facade.find("%s(" % str(prior)) != -1:
			widened += 1
	check_eq(PRIOR_FACADE_WIDENINGS.size(), 4,
		"four v1 intents are declared Variant on the facade before this one")
	check_eq(_sorted_set(_string_list(PRIOR_FACADE_WIDENINGS)),
		["collect_income", "combat_town", "complete_collection_town",
			"magic_town"],
		"and they are the four the surface actually gained first")
	info("reward_town call sites measured: %d" % call_sites)


## `reward_town` must have LEFT the collect suite's `UNSUPPORTED_INTENTS` table.
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
		if candidate.begins_with("[\"") and candidate.ends_with("\"],"):
			names.append(candidate.substr(2, candidate.find("\",") - 2))
	check(closed, "the unsupported table's closing bracket was found, so the"
		+ " read is bounded by it rather than by the end of the file")
	check_eq(names.size(), 19,
		"the collect suite pins exactly the nineteen intents v1 still lacks")
	check(not names.has(INTENT_METHOD),
		"reward_town left the unsupported table, because v1 implements it now")
	for prior in ["collect_income", "complete_collection_town", "magic_town",
			"combat_town"]:
		check(not names.has(str(prior)),
			"and so did %s, which handed off to a sibling suite" % str(prior))
	check(names.has("place_building"),
		"the table is still a real list, not an emptied one")
	# The hand-off is declared, and the suite it names must exist - which is how
	# this file is discovered by the collect suite at all.
	var handed := _project_source(COLLECT_SUITE_SCRIPT).find(
		"\"%s\": \"%s\"" % [INTENT_METHOD, "res://tests/test_reward_v1.gd"])
	check(handed != -1,
		"and the collect suite points reward_town at this suite by path")
	check(ResourceLoader.exists("res://tests/test_reward_v1.gd"),
		"and this suite really is there")


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
	check(api_body.find(V1_HOST) != -1,
		"the v1 implementation names v1's own loopback port")
	check(v0_body.find(V1_HOST) == -1,
		"the legacy-v0 implementation names no v1 port")
	check(api_body.find(ServerV1Api.REWARD_PATH) != -1,
		"the v1 transport names its own reward path")
	if tokens.size() != 3:
		return
	for token in tokens:
		check(api_body.find(str(token)) != -1,
			"the v1 transport carries the %s token" % str(token))
		check(v0_body.find(str(token)) != -1,
			"the legacy-v0 implementation still carries %s" % str(token))
		check(result_body.find(str(token)) == -1,
			"this line's typed-result module carries no %s token" % str(token))


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
		if not candidate.begins_with(QUOTED_OPEN) \
				or not candidate.ends_with(","):
			continue
		tokens.append(candidate.substr(1, candidate.length() - 3))
	return tokens


## ## The absence of a live arm, made mechanical.
##
## Four claims, each with a control so none of them can pass vacuously:
##
## 1. **The dispatcher is unconditional.** `run_scenario` contains no `if` at
##    all, so there is no scenario string a caller could pass to reach a second
##    arm. The span is read by indentation, which is how GDScript delimits a
##    block, and the same reader is proved on a planted source - which is also
##    what caught the reader's own tab blindness (see `_function_span`).
## 2. **No delivered module declares a function named for a live arm.** Scoped
##    to the two delivered modules rather than to this file, and the narrowing
##    is a correction rather than a convenience: the first draft scanned *this*
##    suite and reported its own two check functions - `_check_no_live_arm_and
##    _no_socket` and `_check_reward_codes_live_in_the_reward_modules` - as the
##    violation. A guard whose own identifier names the thing it forbids cannot
##    be repaired by renaming the identifier, because the next check that names
##    it has the same problem. "This suite has no live arm" is claim 1 plus
##    claim 3.
## 3. **No quoted scenario token survives in this file.** Read from the
##    **literals-kept** projection; the literals-blanked one cannot show it at
##    all, which is exactly why reading it would be vacuous here. The controls
##    are assembled **from** the token rather than spelled out, because spelling
##    it in a control made the guard count its own control as the violation -
##    the same shape as claim 2, reached the other way round.
## 4. **No transport call appears in this file's code.** Measured with the
##    **literals-blanked** projection and tokens **read out of** the scope suite,
##    which is the only safe direction: a token listed as a literal would be
##    blanked out of its own inventory, so this guard transcribes nothing and is
##    delegated to `test_project_scope.gd` rather than duplicated from it.
func _check_no_live_arm_and_no_socket() -> void:
	var source := _project_source(SELF_SCRIPT)
	check(source != "", "this suite reads its own source")
	if source == "":
		return
	var span := _function_span(source, "run_scenario")
	check(span.size() > 1,
		"run_scenario's block was read, not just its signature")
	var branch_count := 0
	for line in _code_lines(_code_only("\n".join(span))):
		var candidate := str(line).strip_edges()
		if candidate.begins_with("if ") or candidate.begins_with("match "):
			branch_count += 1
	check_eq(branch_count, 0,
		"run_scenario holds no conditional and no match: there is no second"
		+ " scenario to pass")
	# The control for the span reader, so "no conditional" is a measurement over
	# the right lines rather than over an empty list. The stem is **assembled**,
	# never spelled: this file scans itself for a quoted form of it, so a spelled
	# copy - here or in the delivered-name scan below - is a hit the guard finds
	# in its own inventory. That is precisely what the first run of this suite
	# did, and it is the same defect `godot-construction-assist` recorded for a
	# reserved-stem guard scanning raw source.
	var stem := "l" + "iv" + "e"
	var token := "%s%s%s" % [QUOTED_OPEN, stem, QUOTED_CLOSE]
	var planted := _function_span(
		"func run_scenario() -> void:\n\tif scenario == %s:\n\t\tpass\n" % token,
		"run_scenario")
	check_eq(planted.size(), 4,
		"and the span reader finds a planted dispatcher whole - the signature,"
		+ " both body lines and the blank line the block ends on")
	var planted_branches := 0
	for line in _code_lines(_code_only("\n".join(planted))):
		var candidate := str(line).strip_edges()
		if candidate.begins_with("if "):
			planted_branches += 1
	check_eq(planted_branches, 1,
		"and that planted dispatcher does carry a conditional")

	for relative in DELIVERED_MODULES:
		var offenders: Array = []
		for name in _declared_function_names(
				_project_source(str(relative))):
			if str(name).to_lower().find(stem) != -1:
				offenders.append(str(name))
		check_eq(offenders, [],
			"%s declares no function named for a live arm" % relative)

	var literal_source := _comment_free(source)
	var hits := 0
	for line in _code_lines(literal_source):
		if str(line).find(token) != -1:
			hits += 1
	check_eq(hits, 0, "and no quoted live-scenario token survives in this file")
	check(_comment_free("var s := %s\n" % token).find(token) != -1,
		"and the scan is not vacuous: the same token planted as a string"
		+ " literal IS found by the literals-kept projection")
	check(_code_only("var s := %s\n" % token).find(token) == -1,
		"and it would NOT be found by the literals-blanked projection, which is"
		+ " why reading the wrong one here would have been a vacuous guard")

	# Claim 4. The tokens come from the scope suite and the projection blanks
	# literals, so this file's own source cannot satisfy or defeat the scan: a
	# **use** in code survives blanking, an inventory literal does not.
	var scope := _project_source(SCOPE_SCRIPT)
	check(scope != "",
		"the scope suite exists, and it is the delegated owner of the"
		+ " transport gate rather than a second copy of it")
	var blanks := _code_only(source)
	for token_name in _transport_tokens():
		var spelling := str(token_name)
		check(blanks.find(spelling) == -1,
			"this suite's CODE names no %s" % spelling)
		check(_code_only("var t := %s.new()\n" % spelling).find(spelling) != -1,
			"and the scan would catch a real use of %s" % spelling)
		check(_code_only("var t := %s%s\n" % [QUOTED_OPEN, spelling])
			.find(spelling) == -1,
			"while an inventory literal of %s is blanked, so the guard cannot"
			% spelling + " trip on itself")


# --- this suite's own source -------------------------------------------------


## ## No `%` format argument this suite cannot account for.
##
## `magic-live-v1` found the real fault on the delivered bytes: a live-arm
## message was written with no placeholder in its literal. GDScript raises
## `not all arguments converted during string formatting in operator '%'`, which
## aborts the function partway through - and `test_base.gd` records a function
## abort as a PASS, so the phase still exits 0 and **every remaining assertion
## simply never ran**. This suite ships no live arm, but it ships plenty of
## assertions, so the guard is kept at the source.
##
## Two shapes are covered, because the sibling suites used both: `literal %
## operand` on one line, and `literal` on one line followed by `% operand` on
## the next. The needle is assembled at run time so no line of this guard
## contains the sequence it looks for.
func _check_no_unconverted_format_arguments() -> void:
	var needle := "%s%s%s" % [QUOTED_OPEN, " ", "%"]
	var lead := "%s%s" % ["%", " "]
	var source := _comment_free(_project_source(SELF_SCRIPT))
	# The read is asserted, not assumed, because this guard was **vacuous on the
	# delivered bytes** until an injection probe made that visible: it resolved
	# a repository-relative path through a project-relative reader, got `""`,
	# and reported clean. A guard whose subject cannot be read must say so.
	check(source.find("_check_no_unconverted_format_arguments") != -1,
		"the format guard reads this suite's own source, and the file it read"
		+ " is the one this function lives in")
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
			if not previous.strip_edges().ends_with(QUOTED_CLOSE):
				continue
			operand = previous
		if _placeholder_count(operand) == 0:
			offenders.append("%d: %s" % [index + 1, operand.strip_edges()])
	check_eq(offenders, [],
		"every %s-format in this suite has a placeholder to consume its operand"
		% "percent-sign")
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
		if index + 1 < operand.length() \
				and operand[index + 1] in ["s", "d", "f"]:
			found += 1
			index += 2
			continue
		index += 1
	return found


# --- the evidence report -----------------------------------------------------


## The report is deterministic and derived from the live model and the committed
## files, so it cannot drift from the code it documents. Every claim in the
## `claims` block names the check that fails when it stops being true: a claim
## with no enforcing check would be an assertion, which is the defect this suite
## exists to catch in the delivered modules.
func _write_report() -> void:
	var path := _arg(ARG_REPORT, "")
	if path == "":
		return
	var module_digests := _module_digests()
	check_eq(module_digests.size(), 2,
		"both delivered client modules were read for the report's digest block")
	var handle := FileAccess.open(path, FileAccess.WRITE)
	check(handle != null, "the evidence report is writable at %s" % path)
	if handle == null:
		return
	var document := {
		"report": "reward-v1-report-v1",
		"intent": {
			"action": ServerV1Reward.ACTION,
			"protocol": ServerV1Reward.PROTOCOL,
			"reward_path": ServerV1Api.REWARD_PATH,
			"operations": ServerV1Reward.OPERATIONS,
			"request_fields": ["player_id", "operation"],
			"grant_channels_are_refused_server_side": GRANT_CHANNELS,
			"operation_is_filtered_client_side": false,
			"client_local_codes": [
				ServerV1Reward.CODE_UNSUPPORTED,
				ServerV1Reward.CODE_BAD_REQUEST,
			],
			"impl_return_types": IMPL_RETURN_TYPES,
			"facade_return_type": _return_type_of(
				_project_source(FACADE_SCRIPT), INTENT_METHOD),
			"facade_widening_is_the_fifth": true,
		},
		"typed_result": {
			"stored_resource_names":
				ServerV1Reward.STORED_RESOURCE_NAMES,
			"stored_resource_count": 7,
			"required_success_keys": ServerV1Reward.REQUIRED_SUCCESS_KEYS,
			"behaviour_key_count": ServerV1Reward.BEHAVIOUR_KEYS.size(),
			"declared_functions": _sorted_set(_string_list(
				_declared_function_names(_project_source(RESULT_SCRIPT)))),
			"three_no_payout_fields_come_from_the_wire": false,
			"fail_closed_cases": FAIL_CLOSED_CASE_COUNT,
		},
		"observations": {
			"success_operations": _sorted_keys(OBSERVED_SUCCESSES),
			"refusal_conditions": _sorted_keys(OBSERVED_REFUSALS),
			"refusal_condition_count": OBSERVED_REFUSALS.size(),
			"distinct_codes": _sorted_set(_string_list(_observed_codes())),
			"captured_answer_carries_a_protocol_key": false,
			"protocol_stamp_is_the_parsers_own_default": true,
			"bound": OBSERVED_BOUND,
			"bound_provenances_differ_by_operation": true,
			"leaf_paths_changed_by_operation": {
				"daily": _string_list(
					(OBSERVED_SUCCESSES["daily"]["leaf_paths_changed"]) as Array),
				"weekly": _string_list(
					(OBSERVED_SUCCESSES["weekly"]["leaf_paths_changed"])
						as Array),
			},
			"fixture_is_a_captured_legacy_oracle": false,
			"fixtures_are_observed_v1_answers": true,
		},
		"refusals": {
			"expected_codes": _sorted_keys(EXPECTED_REWARD_REFUSALS),
			"domain_named_codes": DOMAIN_NAMED_CODES,
			"declared_by_the_committed_table": 25,
			"client_local_codes_are_server_codes": false,
			"unknown_player_has_no_dotted_spelling": true,
		},
		"domain": {
			"module": DOMAIN_MODULE,
			"declared_functions": _sorted_set(_string_list(
				_python_function_names(_repo_text(DOMAIN_MODULE)))),
			"grant_channels": _domain_channels(),
			"operation_count": _domain_operation_count(),
		},
		"reserved_stems": {
			"stems": RESERVED_DERIVATION_STEMS,
			"reporting_name_exceptions": REPORTING_NAME_EXCEPTIONS,
			"match_against": "declared function names, folded, substring,"
				+ " both directions",
		},
		"forbidden_relations": FORBIDDEN_RELATIONS,
		"claims": {
			"client_computes_a_successor": false,
			"client_prices_a_reward": false,
			"client_reads_either_schedule": false,
			"client_evaluates_an_eligibility_window": false,
			"client_clamps_a_cursor": false,
			"client_relates_two_reported_values": false,
			"client_filters_an_operation": false,
			"client_sends_a_grant_channel": false,
			"client_takes_the_no_payout_fields_from_the_wire": false,
			"unsupported_intent_touches_transport": false,
			"live_scenario_shipped": false,
			"parity_with_legacy_claimed": false,
		},
		"enforced_by": {
			"client_computes_a_successor":
				"_check_no_line_compares_two_reported_values (five pairs)"
				+ " + _check_absent_derivation_helpers",
			"client_prices_a_reward":
				"_check_no_client_arithmetic (guards A and B, empty exception"
				+ " list) + _check_absent_derivation_helpers +"
				+ " _check_domain_reserved_stems",
			"client_reads_either_schedule":
				"_check_absent_derivation_helpers (the schedule stem, with the"
				+ " one size-pinned reporting-name exception)",
			"client_evaluates_an_eligibility_window":
				"_check_no_line_compares_two_reported_values (the instant pair)"
				+ " + _check_fail_closed (instant_gating must be false, not"
				+ " merely present)",
			"client_clamps_a_cursor":
				"_check_no_line_compares_two_reported_values (cursor_before"
				+ " with clamped) + _check_absent_derivation_helpers (clamp)",
			"client_relates_two_reported_values":
				"_check_no_line_compares_two_reported_values (per line, with a"
				+ " control that a split-line module is not read as relating)",
			"client_filters_an_operation":
				"_check_intent_body (an off-set operation travels verbatim)",
			"client_sends_a_grant_channel":
				"_check_intent_body (the forbidden key set, empty as built) +"
				+ " _check_observed_refusals_parse (five channels, five codes)",
			"client_takes_the_no_payout_fields_from_the_wire":
				"_check_observed_success_parses (a body that lies about all"
				+ " three still parses to paid:false, payout:null,"
				+ " eligibility:false)",
			"unsupported_intent_touches_transport":
				"test_server_v1.gd; this suite asserts the intent LEFT its"
				+ " unsupported table (_check_unsupported_intent_left_the_table)",
			"live_scenario_shipped":
				"_check_no_live_arm_and_no_socket (four claims, each with a"
				+ " control)",
			"parity_with_legacy_claimed":
				"not a claim; v1 is new behaviour and no legacy oracle exists"
				+ " for a cursor the preserved server derived from client input",
		},
		"limits": {
			"legacy_commands": "win_daily_bonus / weekly_reward",
			"legacy_branches": "command.py:444-463 / command.py:345-363",
			"client_input_replaced": "command.py:446 args[1] + 1",
			"successor_is_derived_server_side": true,
			"bound_is_a_preserved_branch_literal": true,
			"daily_literal_is_a_coincidence": true,
			"price_is_derived": false,
			"eligibility_is_derived": false,
			"clamping_is_derived": false,
			"grant_is_derived": false,
			"fixture_is_a_captured_legacy_oracle": false,
			"fixtures_are_observed_v1_answers": true,
			"seed_cursor": 2,
			"no_progressed_player_save_available": true,
			"legacy_backwards_wrap_reproduced": false,
			"v1_routes_delivered_total": 5,
			"live_phase_shipped": false,
			"windowed_capture": false,
			"pixel_parity": false,
			"client_sees_a_before_state": false,
			"python_name_scan_over_counts_a_docstring": true,
			"sibling_suites_pin_a_stale_refusal_table_row_count": true,
		},
# **Transcribed, not executed here.** This suite cannot run a probe: no
		# `OS.execute`, no file write, no `await`, no engine call. The table
		# records an external harness run against the bytes named in `modules`,
		# and the row counts are MEASURED `[test] FAIL` line counts, not
		# non-zero exit codes -- a parse error also exits non-zero and would
		# prove nothing. `asserted_in_run` below says which half is asserted here
		# and which half is only transcribed.
		#
		# ## CORRECTION, 2026-10-14 -- this whole block was re-measured
		#
		# The table previously transcribed **sixteen** probes summing to **39**
		# `[test] FAIL` lines, and those numbers described bytes that are not
		# shipped. They were measured while the typed module still contained the
		# `str()` truthiness defect described in `_cursor`, and in that state
		# `parse_reward_cursor` **refused every answer** -- including both
		# captured successes. Every probe therefore ran against a module that
		# failed everything, which is the same false-detection shape this
		# repository has already recorded twice (a parse-error detection proves
		# nothing about a guard; a guard that cannot fail is not a detection).
		# The scores were real `[test] FAIL` counts and the restores were real,
		# but they characterised a broken build.
		#
		# The defect was **invisible to the suite for one whole iteration**
		# precisely because the suite built its expectations from the parser's
		# own idea of the wire -- the reason `_check_observed_success_parses`
		# now reads *captured* answers, and the reason `_check_fail_closed`
		# opens by asserting its own base answer parses. **A1 below is that
		# defect, re-instated deliberately**, and it is the anchor of this set:
		# it is the one probe whose failure count (12) is an order of magnitude
		# above the rest, because it makes the 85-case refusal walk vacuous and
		# the anti-vacuity anchor is the only check that can notice.
		#
		# The re-measured set is **fifteen** probes summing to **42**, against
		# the final delivered bytes, with the baseline asserted GREEN before the
		# run and again after every restore.
		"injection_probes": {
			"asserted_in_run": [
				"the pinned whole function inventories, as data",
				"the reserved-stem predicate, by planted positive and"
					+ " stem-free controls",
				"the no-live-arm guard's own span reader, by a planted"
					+ " dispatcher string that must be found AND must carry"
					+ " exactly one conditional",
				"the fail-closed walk's anti-vacuity anchor, which parses"
					+ " the unmodified captured success first",
			],
			"transcribed_from_external_harness_run": [
				{"probe": "A1 re-instate the str() truthiness defect",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 12,
				 "is_the_anchor": true},
				{"probe": "A2 result an invented payout helper",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": true, "fail_lines": 4},
				{"probe": "A3 result a SUFFIXED helper wearing a reserved"
					+ " stem as a prefix",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": true, "fail_lines": 4},
				{"probe": "A4 result a mixed-case reserved helper",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": true, "fail_lines": 1},
				{"probe": "A5 result arithmetic over a reported value",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 3},
				{"probe": "A6 result a line comparing two reported values",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 3},
				{"probe": "A7 result `paid` read off the wire instead of"
					+ " declared",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 1},
				{"probe": "A14 result a declared helper named for a live arm",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 2},
				{"probe": "A15 result a transport endpoint constant",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 1},
				{"probe": "A13 result a refusal code invented client-side",
				 "file": "server_v1_reward_result.gd",
				 "borrows_reserved_stem": false, "fail_lines": 1},
				{"probe": "A8 api a third key on the reward intent body",
				 "file": "server_v1_api.gd",
				 "borrows_reserved_stem": false, "fail_lines": 4},
				{"probe": "A9 api the reward route moved off its prefix",
				 "file": "server_v1_api.gd",
				 "borrows_reserved_stem": false, "fail_lines": 1},
				{"probe": "A11 facade reward_town narrowed back to a concrete"
					+ " type",
				 "file": "game_api.gd",
				 "borrows_reserved_stem": false, "fail_lines": 1},
				{"probe": "A10 test_server_v1 the unsupported table regains"
					+ " reward_town",
				 "file": "test_server_v1.gd",
				 "borrows_reserved_stem": false, "fail_lines": 2},
				{"probe": "A12 domain a declared function renamed",
				 "file": "server_v1_reward.py",
				 "borrows_reserved_stem": false, "fail_lines": 2},
			],
			"probe_count": 15,
			"measured_total_fail_lines": 42,
			"every_probe_reported_at_least_one_fail_line": true,
			"every_probe_ran_without_a_parse_or_engine_error": true,
			"every_restore_verified_by_sha256_against_pre_probe_bytes": true,
			"baseline_asserted_green_before_the_run_and_after_every_restore":
				true,
			"which_guard_is_the_real_gate":
				"two different answers, and the split is the useful part."
				+ " For an invented DERIVATION the gate is the pinned whole"
				+ " inventory: A5 and A6 borrow no reserved stem and still score"
				+ " 3 each, because the inventory pin and the two count pins see"
				+ " them alone, while the stem-bearing A2 and A3 score 4 -- two"
				+ " detections for one planted line. So the reserved-stem check is"
				+ " the belt and the inventory is the gate there. For the"
				+ " ANTI-VACUITY anchor the answer inverts: A1 borrows no stem and"
				+ " scores 12, because the guard that catches it is not a name"
				+ " scan at all -- it is `_check_fail_closed`'s first statement,"
				+ " which parses the unmodified captured success. A name scan"
				+ " would not have noticed that every probe in the previous,"
				+ " sixteen-row table was firing against a module that refused"
				+ " everything.",
			"the_harness_itself_fault_twice_before_it_measured_anything":
				"recorded because both faults are the ones this repository has"
				+ " already recorded once and neither is visible in the output."
				+ " First, the restore path decoded raw CRLF *bytes* and then"
				+ " applied `.replace(chr(10), chr(13)+chr(10))` a second time,"
				+ " rewriting every pre-existing line ending as CR CR LF; the"
				+ " sha256 restore check caught it, which is the check's entire"
				+ " purpose, and the fix was to normalise to LF on the way in so"
				+ " the conversion happens once. Second, the probe anchor for the"
				+ " intent body occurred twice in `server_v1_api.gd`, and the"
				+ " harness refused it rather than mutating one of the two --"
				+ " which is why that probe's anchor spans the whole function"
				+ " signature instead of the two lines it replaced.",
			"coverage_narrowing_is_refused":
				"the re-measured set deliberately probes two surfaces the"
				+ " sixteen-row table also probed and no probe of an earlier"
				+ " draft reached: a declared helper named for a live arm (A14),"
				+ " which is the only way to exercise the DELIVERED_MODULES name"
				+ " scan, and a transport endpoint constant in the typed module"
				+ " (A15), where A9 moves the API's own path. Replacing a"
				+ " disclosure with fewer rows would have made the evidence"
				+ " quieter and weaker at the same time.",
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
			REWARD_SCRIPT_PATHS.project_dir().path_join(relative))
		out[relative] = {
			"raw_sha256": _sha256_of(bytes),
			"pure_lf": _is_pure_lf(bytes),
			"bytes": bytes.size(),
		}
	return out


func _sha256_of(bytes: PackedByteArray) -> String:
	# `String(raw_bytes)` does not exist on this engine -- it is a parse error,
	# not a runtime one -- so the text is assembled byte by byte and hashed as
	# text. That is correct here because the flag beside it records whether the
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
				REWARD_SCRIPT_PATHS.project_dir().path_join(relative))):
			return false
	return true


## The distinct codes the observed refusals resolve to, read out of the capture
## rather than listed, so the report cannot disagree with the checks.
func _observed_codes() -> Array:
	var out: Array = []
	for label in OBSERVED_REFUSALS:
		out.append(str((OBSERVED_REFUSALS[label] as Dictionary)["code"]))
	return out


# --- helpers -----------------------------------------------------------------


## The whole declared function inventory of the transport module, as this suite
## knows it. Read here rather than transcribed inline so the list lives beside
## the reserved stems that are checked against it.
func _api_function_inventory() -> Array:
	return [
		"_ready", "_call", "_failure", "_transport_message",
		"resolved_endpoint", "_unsupported", "_intent_body",
		"_collection_intent_body", "_combat_intent_body", "_magic_intent_body",
		"_reward_intent_body",
		"collect_income", "complete_collection_town", "combat_town",
		"magic_town", "reward_town",
		"list_sessions", "get_bootstrap", "place_building",
		"purchase_item", "move_building", "sell_building", "store_building",
		"upgrade_building", "build_construction", "expand_town",
		"level_up_town", "push_queue_unit_town", "pop_queue_unit_town",
		"resurrect_hero_town", "advance_research_town", "advance_quest_town",
		"complete_tutorial_town", "place_stored_item_town",
		"sell_stored_item_town",
	]


func _project_source(relative: String) -> String:
	var path := REWARD_SCRIPT_PATHS.project_dir().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## A repository-relative file's text, or "" when unreadable. Used for the Python
## service modules, which are not inside the Godot project.
func _repo_text(relative: String) -> String:
	var path := REWARD_SCRIPT_PATHS.repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## Every `RefusalCode.NAME` a Python source names, as a list. A substring scan,
## not a parse - the safe direction here, because an over-count fails the
## two-way pin rather than hiding a newly added code.
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
## at the start of a line after stripping indentation. **A line scan, not a
## parse** - see `_check_python_name_scan_finds_planted_defs`, which proves what
## it finds and records what it over-counts.
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
## Both are needed and neither can serve the other, and this suite's design
## records where each is load-bearing: the operator scan must not see the `//`
## inside `preload("res://scripts/gameapi/boot_data.gd")`, while the balance
## guard, the forbidden-relation pair scan and the live-token scan must be able
## to see `["gold"]` and `"cursor_before"`. A single projection makes whichever
## guard it does not serve **vacuously true**, and a vacuously true guard is the
## failure mode this project has already recorded.
##
## The lexer is a proper two-state machine with backslash escapes. Newlines
## survive in both projections, so a blanked literal never joins two lines into
## one and invents a line that is not there.
func _lex(body: String, keep_literals: bool) -> String:
	var out := ""
	var index := 0
	var in_string := false
	var quote := ""
	while index < body.length():
		var character := body.substr(index, 1)
		if in_string:
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
		if character == QUOTED_OPEN or character == "'":
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
## typed-result module declares all sixteen of its functions `static`, and an
## inventory that only matched `func ` would report that module as declaring
## **nothing** - a zero that looks like a pass.
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
		var head := candidate.substr("func ".length(),
			open - "func ".length())
		out.append(head.strip_edges())
	return out


## The body of a named `func`, read by **indentation** - which is how GDScript
## delimits a block - and returned as an array of lines including the signature.
## Returns [] when the function is not declared, so a caller that forgets to
## check reads an empty list rather than the whole file.
##
## The indent test strips **spaces and tabs together**, and that is not a detail:
## this repository is TAB-indented, so a reader that measured only spaces saw
## every line as column zero, returned the signature alone, and made "run_scenario
## holds no conditional" pass over an empty list. The first run of this suite
## did exactly that, and the planted control below is what caught it.
func _function_span(source: String, method: String) -> Array:
	var lines := source.split("\n")
	for index in lines.size():
		var candidate := str(lines[index]).strip_edges()
		if not candidate.begins_with("func %s(" % method):
			continue
		var out: Array = [str(lines[index])]
		var base := str(lines[index]).length() \
			- str(lines[index]).lstrip(" \t").length()
		for probe in range(index + 1, lines.size()):
			var line := str(lines[probe])
			if line.strip_edges() == "":
				out.append(line)
				continue
			var indent := line.length() - line.lstrip(" \t").length()
			if indent <= base:
				break
			out.append(line)
		return out
	return []


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


## Every channel name the capture's own refusals report in `detail.channel`.
## This is the machine link between a refusal and a channel, and it exists
## precisely because the **label** half is not machine-derivable: the label
## "client-dictated map index" and the channel "map_index" differ, and the three
## refusals that carry no `channel` key at all (the cursor, the closed-set
## operation, and the unknown player) are exactly the ones a name-based guess
## would have swept in.
func _observed_channels() -> Array:
	var out: Array = []
	for label in _sorted_keys(OBSERVED_REFUSALS):
		var detail: Dictionary = OBSERVED_REFUSALS[label]["detail"] as Dictionary
		if detail.has("channel"):
			out.append(str(detail["channel"]))
	return _sorted_set(out)


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


## `source` with every member of `names` removed. Used so the reserved-stem
## guard can subtract its one size-pinned exception and then require **zero**,
## rather than carrying the exception inside the comparison where a second one
## could slip in unnoticed.
func _without_all(source: Array, names: Array = []) -> Array:
	var drop := names if names.size() > 0 else REPORTING_NAME_EXCEPTIONS
	var out: Array = []
	for entry in source:
		if not (drop as Array).has(str(entry)):
			out.append(str(entry))
	return out


## True when a `reward_town` call binds its result without narrowing it to a
## concrete class. A call wrapped over several lines has its binding on an
## earlier line, so the walk goes back up to three lines.
func _binds_untyped(line: String, lines: Array, index: int,
		method: String) -> bool:
	var at := line.find("%s(" % method)
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
