extends RefCounted
## Typed read-only reward-cursor projection, wire contract, and refusal record
## (OpenSpec `godot-rewards`, milestone M10 line 1).
##
## ## The delivered surface is a CURSOR TRANSITION, not a reward
##
## The preserved feature is two branches and nothing else --
## `command.py:345-363` (`weekly_reward`) and `command.py:444-463`
## (`win_daily_bonus`). Between them they do exactly two writes this contract
## can reproduce: they advance **one** cursor and stamp **one** instant.
## Everything else either branch does is a **grant whose only input is a
## client-sent value**, and none of those values is accepted here.
##
## So nothing in this file is named after a granted, paid, or awarded reward,
## nothing here selects a schedule entry, and nothing here prices anything. The
## `NO_REWARD_MOVED`, `NO_CURSOR_SELECTION`, and `NO_ELIGIBILITY` records below are the
## three refusals this capability exists to preserve.
##
## ## What IS derived from a committed value, and what is not
##
## Task 3.1 asks for a projection "deriving nothing" from a committed value.
## Read literally that is unsatisfiable, because the spec's own requirement
## ("the derived weekly bound is ... the maximum entry length over schedule
## entries whose value is a list") demands one derivation. `DERIVATION_RECORD`
## states the reading this module implements, and the suite **re-derives the
## weekly bound independently on every run** (task 3.2) rather than trusting
## this file's copy:
##
##   * DERIVED -- exactly one quantity: the weekly bound, by transcribing
##     `get_weekly_reward_length`'s own rule (`get_game_config.py:195-204`).
##   * DERIVED -- the two successor positions, by transcribing each branch's own
##     arithmetic (`command.py:363` and `:446,451-452`).
##   * REPORTED, NEVER DERIVED -- every schedule entry (verbatim), both
##     cardinalities (a count of committed entries, not a rule), the reachability
##     sets (a set difference over two recorded ranges), every consumer count,
##     the type letters (undecoded), the seven save-only fields (no rule), and
##     the ranking-reward table (owned as content elsewhere).
##   * NOT PRESENT AT ALL -- any amount, prize, price, cost, resource movement,
##     letter-to-resource mapping, eligibility test, cooldown, window, period,
##     already-claimed comparison, or cursor-to-rung selection.
##
## ## The module census is DISCOVERED, never transcribed
##
## The consumer census is over "all eleven top-level legacy modules". That
## number is **discovered by listing every top-level `.py` in the repository
## root** (`repo_root_py_modules()`), never written out by hand, so a twelfth
## module would be counted rather than silently excluded. The discovered count
## is reported beside the census and the suite requires it to be non-zero
## **before** any zero-consumer verdict is believed -- the vacuous-census defect
## class, which has recurred three times in this project.
##
## ## Structural refusals, guarded not described (design D7)
##
## `STATIC_FUNCTIONS` pins this file's whole `static func` inventory, so an
## added or reordered helper fails the suite. `ABSENT_HELPERS` names the four
## capabilities that must not exist, `FORBIDDEN_IDENTIFIER_FRAGMENTS` the
## fragments a foreign helper would wear, and `FOREIGN_IDENTIFIERS` the three
## save fields owned by other capabilities. Every one of those is checked
## against **identifiers**, with a substring layer, and every guard is proven by
## injection rather than trusted.
##
## Nothing here reaches the network, dispatches a command, writes a save, or
## executes Flash. The wire half (`build_reward_intent`, `parse_reward`,
## `build_reward_response`) is the same contract the live endpoint answers
## through, so a shape assembled twice cannot drift from the parser that must
## accept it.

const Paths = preload("res://scripts/package_paths.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ---------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------

## Where this line sits, and what it is, in one place.
const PROVENANCE := {
	"milestone": "M10",
	"line": 1,
	"capability": "godot-rewards",
	"investigation": "docs/legacy-m10-rewards.md",
	"contract": "openspec/changes/2026-10-05-rewards",
	"service_half": "apps/compat-api/rewards_envelope.py",
	"primary_finding": "the two preserved reward branches advance one cursor "
		+ "and stamp one instant and grant nothing this contract can reproduce, "
		+ "and BOTH cursors' derived bounds EXCEED the cardinality of the "
		+ "schedule they would address -- 5 against 3 weekly and 5 against 5 "
		+ "daily -- so positions the recorded cursors reach name no rung",
	"delivered_surface": "one cursor transition per action, two derived bounds "
		+ "beside their schedules' cardinalities, the reachability difference "
		+ "in both directions, the committed schedule entries verbatim, the "
		+ "eleven reward schedules with their measured consumer counts, the "
		+ "three type letters undecoded, the seven save-only fields with no "
		+ "rule, and the arm boundary",
	"nothing_delivered": "no reward, no amount, no prize, no price, no cost, "
		+ "no resource movement, no schedule-entry selection, no letter "
		+ "decoding, no eligibility, no cooldown, no window, no period, no "
		+ "already-claimed test, and no cursor-to-rung mapping",
	"service_half_is_owned_by": "the service half is NOT owned by this "
		+ "capability and was not modified here; a defect in it is reported "
		+ "to the change's owner rather than fixed in this file",
}

# ---------------------------------------------------------------------------
# the two cursors and the two instants
# ---------------------------------------------------------------------------

## The committed private-state vocabulary, read from `save["privateState"]`.
const PRIVATE_STATE_KEY := "privateState"

const WEEKLY_CURSOR_KEY := "weeklyRewardIndex"
const DAILY_CURSOR_KEY := "bonusNextId"
const WEEKLY_STAMP_KEY := "timeStampMondayBonus"
const DAILY_STAMP_KEY := "timestampLastBonus"

## Cursor key -> the instant its branch stamps. Both branches write exactly one
## instant and one cursor, and this mapping is what makes the post-execution
## leaf allowlist exact.
const CURSOR_STAMP := {
	WEEKLY_CURSOR_KEY: WEEKLY_STAMP_KEY,
	DAILY_CURSOR_KEY: DAILY_STAMP_KEY,
}

const CURSORS := [WEEKLY_CURSOR_KEY, DAILY_CURSOR_KEY]
const INSTANTS := [WEEKLY_STAMP_KEY, DAILY_STAMP_KEY]
const CURSOR_COUNT := 2

# ---------------------------------------------------------------------------
# the two commands and the closed action set
# ---------------------------------------------------------------------------

const WEEKLY_COMMAND := "weekly_reward"
const DAILY_COMMAND := "win_daily_bonus"

## The client's closed **outcome** vocabulary (design D13). The client names an
## outcome; the service chooses the preserved command.
const ACTION_WEEKLY := "weekly"
const ACTION_DAILY := "daily"
const ACTIONS := [ACTION_WEEKLY, ACTION_DAILY]
const ACTION_COUNT := 2

## action -> the preserved command it derives.
const ACTION_COMMAND := {
	ACTION_WEEKLY: WEEKLY_COMMAND,
	ACTION_DAILY: DAILY_COMMAND,
}

## action -> the addressed cursor. One cursor per action, so the request carries
## no addressing key at all.
const ACTION_CURSOR_KEY := {
	ACTION_WEEKLY: WEEKLY_CURSOR_KEY,
	ACTION_DAILY: DAILY_CURSOR_KEY,
}

## action -> the stamped instant.
const ACTION_STAMP_KEY := {
	ACTION_WEEKLY: WEEKLY_STAMP_KEY,
	ACTION_DAILY: DAILY_STAMP_KEY,
}

## action -> the committed schedule whose positions the cursor is measured
## against.
const ACTION_SCHEDULE_KEY := {
	ACTION_WEEKLY: "MONDAY_BONUS_REWARDS",
	ACTION_DAILY: "DAILY_GOLD_REWARDS",
}

const WEEKLY_SCHEDULE_KEY := ACTION_SCHEDULE_KEY[ACTION_WEEKLY]
const DAILY_SCHEDULE_KEY := ACTION_SCHEDULE_KEY[ACTION_DAILY]

## The committed globals domain the eleven reward schedules live in, read
## through the **existing** normalized content registry.
const CONTENT_DOMAIN := "globals"

## **EXPLICIT, and deliberately empty** (design D13). Neither preserved branch
## addresses a map row, a collection, a track, or any other identity -- both are
## whole-player private-state writes -- so neither action carries an addressing
## key. This is recorded as an empty mapping **rather than left to a default**
## because the quests line's largest cross-layer defect was exactly this shape:
## a transport that assumed one addressing key was universal while the service
## read a per-action one.
const ACTION_ADDRESSING_KEY := {}

const ADDRESSING_KEY_NOTE := {
	"recorded_explicitly_rather_than_defaulted": true,
	"note": "both preserved branches write only whole-player private state -- "
		+ "weeklyRewardIndex with timeStampMondayBonus, bonusNextId with "
		+ "timestampLastBonus -- and neither names a map row, a collection, a "
		+ "track, or any other identity, so NEITHER action carries an addressing "
		+ "key. An empty table cannot be misread as 'look it up somewhere', and "
		+ "the intent builder refuses rather than defaulting",
}

## The endpoint this contract speaks to.
const REWARD_PATH := "/v0/reward"

## Every key a reward request may carry.
const REQUEST_KEYS := ["user_id", "action"]

## How many keys the delivered request body carries. Two, and no more: this is
## the machine-readable form of "the request carries only an action and a save
## id".
const BODY_KEY_COUNT := 2

## The grant-shaped argument classes a request carrying one is **refused** for,
## in the order they are resolved. `item` is the granted id (`command.py:348`
## weekly, `:445` daily), `item_index` the weekly map index (`:347`), `cell`
## both coordinates (`:348-349`), `player` the team (`:351`), `next_id` the
## daily cursor (`:446`), and `amount`/`price` the two shapes a reader would
## expect a reward request to carry and which neither branch has.
const CLIENT_KEY_REFUSALS := [
	["item", "client_supplied_item"],
	["item_index", "client_supplied_item_index"],
	["cell", "client_supplied_cell"],
	["player", "client_supplied_player"],
	["next_id", "client_supplied_next_id"],
	["amount", "client_supplied_amount"],
	["price", "client_supplied_price"],
]

## Two more keys resolving to an already-listed class: the two cell
## coordinates are two keys and one class.
const CLIENT_KEY_ALIASES := {
	"x": "client_supplied_cell",
	"y": "client_supplied_cell",
}

## Literals rather than `.size()` calls: the engine's constant-expression check
## rejects a `size()` on a constant array, and a count that cannot be written as
## a constant would have to be derived at run time -- which is exactly the kind
## of quiet derivation this module refuses. The suite asserts each literal
## against the array it counts, so a renamed class cannot leave the figure behind.
const CLIENT_KEY_REFUSAL_COUNT := 7
const CLIENT_KEY_ALIAS_COUNT := 2

## reason -> the request keys that resolve it.
const REFUSAL_KEY_MAP := {
	"item": "client_supplied_item",
	"item_index": "client_supplied_item_index",
	"cell": "client_supplied_cell",
	"x": "client_supplied_cell",
	"y": "client_supplied_cell",
	"player": "client_supplied_player",
	"next_id": "client_supplied_next_id",
	"amount": "client_supplied_amount",
	"price": "client_supplied_price",
}

## Every refusal, in the order it is resolved. **Every one resolves before the
## cursor write and before the instant stamp**, so a refused request leaves the
## whole recorded document byte-identical (design D9).
##
## The order is the one `/v0/magic` already established: the request's own shape
## first, the player's recorded state last. It is not arbitrary, and the reason
## is measurable: **the addressed cursor cannot be named until the action is**,
## so an `absent_cursor` check placed first could not be evaluated and would be
## a vacuous check rather than a strict one.
const VALIDATION_ORDER := ["bad_request", "unknown_action",
	"client_supplied_item", "client_supplied_item_index",
	"client_supplied_cell", "client_supplied_player",
	"client_supplied_next_id", "client_supplied_amount",
	"client_supplied_price", "absent_reward_cursor",
	"invalid_reward_cursor", "absent_reward_instant"]

const VALIDATION_ORDER_STEPS := 12

## The write step, which follows every check above.
const WRITE_STEP := VALIDATION_ORDER_STEPS + 1

const ORDERING_RULE := {
	"every_refusal_precedes_the_cursor_write": true,
	"every_refusal_precedes_the_instant_stamp": true,
	"why_the_stamp_ordering_is_load_bearing": "a refusal that ran far enough "
		+ "to stamp would leave a WALL-CLOCK difference in a document that is "
		+ "supposed to be unchanged, which would either make the byte-identity "
		+ "assertion fail FOR THE WRONG REASON or force it to be weakened to "
		+ "accommodate that. Keeping the assertion exact is the whole point",
	"why_the_request_shape_comes_first": "the addressed cursor cannot be named "
		+ "until the action is, so a recorded-state check placed before the "
		+ "action check could not be evaluated and would be vacuous rather than "
		+ "strict",
	"the_preserved_server_performs_no_validation": "this ordering exists to "
		+ "make the SERVICE's refusals safe, not to match a recorded ordering",
}

## The refusals about the **request itself**.
const REQUEST_SHAPE_REFUSALS := ["bad_request", "unknown_action",
	"client_supplied_item", "client_supplied_item_index",
	"client_supplied_cell", "client_supplied_player",
	"client_supplied_next_id", "client_supplied_amount",
	"client_supplied_price"]

## The refusals about the **player's recorded state**. Each is a property of the
## recorded corpus, never of a foreign field.
const RECORDED_STATE_REFUSALS := ["absent_reward_cursor",
	"invalid_reward_cursor", "absent_reward_instant"]

const STRUCTURAL_REFUSAL_COUNT := 12

## The two client-side refusals this module raises before any transport is
## touched, so no HTTP call is made for a body this contract cannot build.
const CLIENT_REASONS := ["invalid_action", "missing_user_id"]

const REASON_BAD_RESPONSE := "bad_response"
const REASON_UNREACHABLE := "unreachable_endpoint"

## The rejected alternative to refusing a client-supplied cursor (design D2).
const CLIENT_CURSOR_REJECTED_ALTERNATIVE := {
	"alternative": "read the request, DISCARD the client's next id, and derive "
		+ "the successor from the recorded cursor anyway -- which is what "
		+ "/v0/level_up does with a client-supplied level",
	"rejected_because": "ignoring is right when the ignored value is "
		+ "decorative. It is WRONG for a cursor: the next id is precisely the "
		+ "value this operation derives, so acknowledging the request while "
		+ "substituting a different number answers SUCCESS for an input the "
		+ "operation did not honour. A client that sent next_id 99 would be "
		+ "told the advance succeeded",
	"chosen_instead": "REFUSE with a named code, an empty payload, and no "
		+ "mutation",
}

# ---------------------------------------------------------------------------
# the two bounds
# ---------------------------------------------------------------------------

## `get_weekly_reward_length` seeds its accumulator at **1** and then takes
## `max` over the entries whose `value` is a **list**. The floor is
## load-bearing: a schedule whose every value were a scalar would return 1, not
## 0.
const WEEKLY_BOUND_FLOOR := 1
const WEEKLY_BOUND_SOURCE := "get_game_config.py:195-204 (get_weekly_reward_length)"
const WEEKLY_BOUND_DERIVED_FROM := "the maximum entry length over the " \
	+ "schedule entries whose value is a list -- never the entry count"

## The **hardcoded literal** at `command.py:451` and the position it wraps to.
## Transcribed from the preserved source; never derived from content.
const DAILY_BOUND_LITERAL := 5
const DAILY_WRAP_TARGET := 1
const DAILY_BOUND_SOURCE := "command.py:451-452 (a hardcoded literal, `if next_id > 5:`)"
const DAILY_BOUND_IS_LITERAL := true

## The rejected content-derivation of the daily bound, retained on purpose
## (design D4).
const DAILY_BOUND_REJECTED_DERIVATION := {
	"alternative": "derive the daily bound from DAILY_GOLD_REWARDS' entry count",
	"why_it_is_rejected": "that schedule holds exactly five entries, so its "
		+ "count agrees with the literal at command.py:451 and the two numbers "
		+ "could be read as one deriving the other. THEY ARE NOT. Measured "
		+ "across every top-level legacy module the name DAILY_GOLD_REWARDS "
		+ "occurs ZERO times, so the agreement is a coincidence of the value "
		+ "distribution and NOT provenance. This note exists so a later reader "
		+ "who notices that five equals five cannot conclude that a derivation "
		+ "was chosen and then dropped: it never was",
	"the_same_reasoning_runs_the_other_way_weekly": "the weekly bound IS "
		+ "derived -- but from the schedule's LIST-VALUED entries, not from its "
		+ "entry count, and the two numbers differ (5 against 3)",
}

## Both reachability reports read a cursor as a **zero-based** position into
## its own schedule. That reading is derived-provisional and is recorded with
## the one-based alternative retained.
const SCHEDULE_INDEX_BASE := 0
const SCHEDULE_INDEX_BASE_ALTERNATIVE := 1
const SCHEDULE_INDEX_BASE_STATUS := {
	"status": "DERIVED-PROVISIONAL, with the alternative retained",
	"chosen": SCHEDULE_INDEX_BASE,
	"alternative": SCHEDULE_INDEX_BASE_ALTERNATIVE,
	"why": "the preserved server never indexes either schedule, so nothing in "
		+ "the source fixes the base. What fixes it here is that the "
		+ "zero-based reading is the one under which the committed data carries "
		+ "a MISMATCH: weeklyRewardIndex is recorded at 0..3 across the "
		+ "committed documents and the zero-based reading makes the derived "
		+ "bound (5) exceed the schedule's cardinality (3). A one-based "
		+ "reading would still leave positions unaddressed -- 4 and 5 weekly, 5 "
		+ "daily -- but on a different set, so the reported difference would "
		+ "name positions the recorded cursors do not reach. Both readings are "
		+ "recorded; neither is asserted as fact",
	"used_for": "the reachability report's set difference only. Neither is "
		+ "used to select a schedule entry, because this contract never "
		+ "selects one (design D3/D7)",
}

## The granted item the **daily** derived command carries: exactly **zero**
## (`command.py:458`'s `if item > 0:`).
##
## This is the whole mechanism by which the daily branch grants nothing, beside
## its hardcoded wrap. Both values are derived and neither is ever taken from a
## client: a request carrying an item, a next id, or any other grant shape is
## refused by name before this is reached (design D2).
const DERIVED_DAILY_ITEM := 0

## The positions each cursor can reach, over every non-negative recorded value,
## computed by the preserved branch's own arithmetic rather than asserted:
##
##   weekly -- `(v + 1) % 5` for every `v` in `0..4` yields exactly `0..4`;
##   daily  -- `v + 1` clamped to the literal yields exactly `1..5`.
##
## The suite re-derives both from the branch arithmetic on every run.
const WEEKLY_REACHABLE := [0, 1, 2, 3, 4]
const DAILY_REACHABLE := [1, 2, 3, 4, 5]
const ACTION_REACHABLE := {
	ACTION_WEEKLY: WEEKLY_REACHABLE,
	ACTION_DAILY: DAILY_REACHABLE,
}

## The recorded size of `DAILY_GOLD_REWARDS`, because the daily schedule is read
## by **no** branch so no caller derives it at runtime. It is reported -- never
## used to obtain the bound (design D4).
const DAILY_SCHEDULE_CARDINALITY := 5

## The **derivation record**, stating what this module derives and what it does
## not. It is data, so the suite can publish it and a reader cannot have to
## trust a docstring.
const DERIVATION_RECORD := {
	"derived": [
		{"quantity": "the weekly bound",
			"how": WEEKLY_BOUND_DERIVED_FROM,
			"source": WEEKLY_BOUND_SOURCE,
			"why_this_one": "the spec's own requirement demands it, and it "
				+ "transcribes a preserved helper's own rule rather than "
				+ "inventing one",
			"independently_re_derived_by": "the hermetic suite, on every run"},
		{"quantity": "the two successor positions",
			"how": "each branch's own arithmetic, transcribed",
			"source": "command.py:363 (weekly modulo) and command.py:446,451-452 "
				+ "(daily increment with a wrap)"},
	],
	"reported_but_never_derived": [
		"every schedule entry, verbatim and in committed order",
		"both schedule cardinalities, which are counts of committed entries "
			+ "rather than a rule about them",
		"the reachability sets, which are a set difference over two recorded "
			+ "ranges and deliberately perform no lookup",
		"the eleven reward schedules' measured consumer counts",
		"the three type letters, reported undecoded",
		"the seven save-only fields, reported with no rule",
		"the ranking-reward table, reported as owned content elsewhere",
	],
	"absent_entirely": [
		"any amount, prize, payout, or price",
		"any stored-resource movement, in either direction",
		"any schedule-entry selection from a cursor value",
		"any type-letter-to-resource mapping",
		"any eligibility, cooldown, window, period, or already-claimed test",
	],
	"task_3_1_reading": "read literally, 'deriving nothing from a committed "
		+ "value' is unsatisfiable, because the spec's own second requirement "
		+ "demands the derived weekly bound. The reading implemented here is: "
		+ "the weekly bound is the ONE quantity derived from a committed value "
		+ "-- it transcribes a preserved helper's rule -- and nothing else is "
		+ "derived. No amount, prize, price, letter-to-resource mapping, "
		+ "eligibility, or cursor-to-rung selection exists anywhere here. This "
		+ "reading is recorded rather than silently chosen",
}

# ---------------------------------------------------------------------------
# the eleven reward schedules
# ---------------------------------------------------------------------------

## Every committed `globals` entry whose name carries a reward, a bonus, or a
## prize, with the **measured** number of occurrences of that exact name across
## every top-level legacy module. Ten of the eleven have **zero**, and the one
## that does not is read for its **length only** -- `get_game_config.py:197`
## passes the list to `get_weekly_reward_length` and no code path returns a
## rung, an item, or an amount from it.
##
## The counts are **re-measured from committed bytes on every run** by the
## suite, over a module list this repository **discovers** rather than
## transcribes. This table is the recorded baseline those measurements are
## compared against, not a substitute for them.
const SCHEDULES := [
	{"name": "ALLIANCE_DAILY_BONUS_REWARDS", "consumers": 0,
		"consumed_for": ""},
	{"name": "DAILY_GOLD_REWARDS", "consumers": 0, "consumed_for": ""},
	{"name": "MANA_REWARD_PER_LEVEL", "consumers": 0, "consumed_for": ""},
	{"name": "MONDAY_BONUS_REWARDS", "consumers": 1,
		"consumed_for": "length only, via get_weekly_reward_length "
			+ "(get_game_config.py:197)"},
	{"name": "NEWFRIENDS_REWARD_DESCRIPTION", "consumers": 0,
		"consumed_for": ""},
	{"name": "NEWFRIENDS_REWARD_ID_UNIT", "consumers": 0, "consumed_for": ""},
	{"name": "NEWFRIENDS_REWARD_SCALE_UNIT", "consumers": 0,
		"consumed_for": ""},
	{"name": "PRIZE_COLLECTIONS_CASH", "consumers": 0, "consumed_for": ""},
	{"name": "RECRUITMENT_PRIZE", "consumers": 0, "consumed_for": ""},
	{"name": "REWARDS_CHAPTERS", "consumers": 0, "consumed_for": ""},
	{"name": "REWARDS_QUESTS", "consumers": 0, "consumed_for": ""},
]

const SCHEDULE_COUNT := 11
const SCHEDULES_WITH_NO_CONSUMER := [
	"ALLIANCE_DAILY_BONUS_REWARDS", "DAILY_GOLD_REWARDS",
	"MANA_REWARD_PER_LEVEL", "NEWFRIENDS_REWARD_DESCRIPTION",
	"NEWFRIENDS_REWARD_ID_UNIT", "NEWFRIENDS_REWARD_SCALE_UNIT",
	"PRIZE_COLLECTIONS_CASH", "RECRUITMENT_PRIZE", "REWARDS_CHAPTERS",
	"REWARDS_QUESTS",
]
const SCHEDULES_WITH_NO_CONSUMER_COUNT := 10

## The census is a statement about the **preserved server's source**, and
## nothing else. The whole `globals` object is SERVED to clients, so a client
## could have read any of these eleven schedules; this repository makes NO claim
## about what any client did with the bytes it was served.
const SCHEDULE_CENSUS_NOTE := {
	"states_only": "the preserved server's source",
	"the_whole_configuration_object_is_served": true,
	"no_claim_about_clients": true,
	"module_set": "every top-level .py in the repository root, DISCOVERED at "
		+ "run time and never transcribed; the recorded count of eleven is "
		+ "re-measured and asserted on every run",
}

## The committed ranking-reward table: owned **as normalized content**, and
## **undelivered as gameplay** by this line. Those are two different states and
## the record does not collapse them (design D11, task 5.2).
const RANKING_REWARD_TABLE := "level_ranking_reward"
const RANKING_REWARD_CONSUMERS := 0
const RANKING_REWARD_ENTRY_COUNT := 50
const RANKING_REWARD_OWNERSHIP := {
	"owned_as_normalized_content_by": ["economy-schedules-normalization",
		"content-validation"],
	"delivered_as_gameplay_by_this_line": false,
	"the_two_statements_do_not_imply_each_other": "content being validated is "
		+ "not content being played",
}

# ---------------------------------------------------------------------------
# the type letters
# ---------------------------------------------------------------------------

## The weekly schedule's own type vocabulary, verbatim, and **undecoded**.
const TYPE_LETTERS := ["g", "u", "c"]
const TYPE_LETTER_COUNT := 3

## The six independent searches, each carrying the **exact regular expression**
## the hermetic suite re-runs, so every count is a measurement a test re-derives
## rather than a figure this module asserts. All six are zero across every
## top-level legacy module, which is why reading a letter as a resource name
## would be an **invention** rather than a reproduction (design D10).
##
## The patterns are measured over the concatenation of the bodies of the
## **discovered** top-level modules. An earlier draft of this comment claimed the
## engine had no regular-expression class and that the patterns therefore could
## not be carried. That was **false**: `RegEx` exists on the pinned build, it
## compiles PCRE2, and `search_all()` counts every match -- all three verified by
## probe before the claim was corrected. Carrying the pattern is what makes the
## sentence "a test can re-derive it" true; without the pattern a reader had a
## figure and no way to reproduce it.
const DECODER_SEARCHES := [
	{"search": "a single-letter key 'g' followed by gold or coins",
		"shape": "single_letter_gold", "hits": 0,
		"pattern": "['\"]g['\"]\\s*:\\s*(?:gold|coins)"},
	{"search": "a single-letter key 'c' followed by cash",
		"shape": "single_letter_cash", "hits": 0,
		"pattern": "['\"]c['\"]\\s*:\\s*cash"},
	{"search": "a single-letter key 'u' followed by unit",
		"shape": "single_letter_unit", "hits": 0,
		"pattern": "['\"]u['\"]\\s*:\\s*unit"},
	{"search": "any single-letter dictionary key at all",
		"shape": "any_single_letter_key", "hits": 0,
		"pattern": "['\"][a-zA-Z]['\"]\\s*:"},
	{"search": "any branch comparing a type field against a one-letter string",
		"shape": "type_equals_letter", "hits": 0,
		"pattern": "type\\s*==\\s*['\"][a-zA-Z]['\"]"},
	{"search": "any subscript of a reward object by its 'type' key",
		"shape": "type_subscript", "hits": 0,
		"pattern": "\\[(?:[^\\]\\[]*)['\"]type['\"](?:[^\\]\\[]*)\\]"},
]

const DECODER_SEARCH_COUNT := 6
const DECODER_SEARCH_HIT_TOTAL := 0

## Positive controls for the six searches above, so a zero is a measurement
## rather than a broken search. Two-letter dictionary keys and string-keyed
## subscripts both match abundantly in the same corpus, which is what makes the
## single-letter results meaningful.
##
## ## MEASURED CORRECTION to two of these three figures
##
## An earlier draft recorded `quoted_subscript` at **515** and
## `unquoted_subscript` at **244**. Both were measured against a
## hand-written string scan rather than against the patterns, and re-measuring
## them against the patterns carried here gives **516** and **225**. The
## conclusion is untouched -- all three controls fire abundantly, which is the
## only thing they exist to show -- but a positive control whose count is
## wrong teaches the reader to discount the zeros beside it, so the figures are
## corrected rather than left standing as a plausible number.
const DECODER_POSITIVE_CONTROLS := [
	{"search": "a two-letter dictionary key", "shape": "two_letter_key",
		"hits": 4, "pattern": "['\"][a-z]{2}['\"]\\s*:"},
	{"search": "a subscript by a quoted key", "shape": "quoted_subscript",
		"hits": 516,
		"pattern": "\\[[^\\]\\[]*['\"][A-Za-z_][A-Za-z0-9_]*['\"][^\\]\\[]*\\]"},
	{"search": "an unquoted subscript, a list index rather than a key",
		"shape": "unquoted_subscript", "hits": 225, "pattern": "\\[[0-9]+\\]"},
]

const DECODER_POSITIVE_CONTROL_COUNT := 3

const DECODER_POSITIVE_CONTROL_NOTE := {
	"why": "the six zero results are MEASURED, not assumed. These controls run "
		+ "over the same discovered module set with the same machinery, and all "
		+ "match abundantly, so the single-letter shapes are specific rather "
		+ "than silent. A census that reports only zeros and never checks that "
		+ "its own shapes fire has produced the vacuous-census defect three "
		+ "times in this project, so the controls are part of the record",
	"counts_are_re_derived_every_run": true,
}

## A measured nuance that **strengthens** the refusal. The same three letters
## are each declared exactly once under a resource-flavoured name, and every one
## of those names has exactly one occurrence in total -- the declaration -- and
## zero consumers. They belong to the item `costs` and item-`type`
## vocabularies, and **no legacy module iterates `costs`**, so nothing bridges
## them to the reward `type` field.
const LETTER_NAMED_DECLARATIONS := [
	{"letter": "g", "declared_as": "COST_GOLD", "declared_at": "constants.py:888",
		"occurrences_total": 1, "consumers": 0,
		"belongs_to": "the item costs vocabulary"},
	{"letter": "c", "declared_as": "COST_CASH", "declared_at": "constants.py:889",
		"occurrences_total": 1, "consumers": 0,
		"belongs_to": "the item costs vocabulary"},
	{"letter": "u", "declared_as": "TYPE_UNIT", "declared_at": "constants.py:857",
		"occurrences_total": 1, "consumers": 0,
		"belongs_to": "the item type vocabulary"},
]

const LETTER_NAMED_DECLARATION_COUNT := 3

const TYPE_LETTERS_UNDECODED_NOTE := {
	"reported_verbatim_and_not_decoded": true,
	"why": "reading 'g' as gold and 'c' as cash is the obvious next step and "
		+ "would be an INVENTION: no preserved module maps any of these letters "
		+ "onto a stored resource slot, an item category, or a grant shape. The "
		+ "six searches return zero each, and the positive controls confirm the "
		+ "searches themselves fire on the same corpus",
	"the_nuance_that_strengthens_it": "the same three letters are each declared "
		+ "once in constants.py under resource-flavoured names, every one of "
		+ "those names has exactly ONE occurrence -- the declaration -- and ZERO "
		+ "consumers, they belong to the item costs and item-type vocabularies "
		+ "rather than the reward type field, and NO legacy module iterates "
		+ "costs at all, so nothing bridges them",
}

# ---------------------------------------------------------------------------
# the seven save-only fields
# ---------------------------------------------------------------------------

## Present in **every** committed save document and in **no** source line. Their
## origin is an **inference** from those two measurements, not a measurement.
const SAVE_ONLY_FIELDS := ["attacksSent", "attacksPack", "attacksReceived",
	"bestUnit", "betWin", "spyings", "strategy"]
const SAVE_ONLY_FIELD_COUNT := 7

## The committed document census: three `.json` files under `tests/saves` plus
## the eight under `villages/` plus the twenty-three under `villages/quest/`.
##
## ## Thirty-four files walked, THIRTY-THREE carrying, and the difference is
## MEASURED rather than reconciled by hand
##
## `tests/saves/manifest.json` is one of the three files under `tests/saves` and
## carries **no** `privateState` at all -- it is a manifest of the save corpus,
## not a save. So a walk that counted *files* reports 34 and a walk that counts
## *documents carrying the fields* reports 33. Both figures are carried here
## rather than only the smaller one, because a reader who re-runs a naive
## `*.json` glob and gets 34 would otherwise conclude the 33 was a mistake.
##
## MEASURED CORRECTION to the committed investigation, which recorded 39
## documents. The cursor distributions it recorded match exactly (weekly
## `{0:26, 1:5, 2:1, 3:1}` and daily `{0:7, 2:24, 3:2}`, summing to 33) and
## only the denominator differs, so no conclusion changes.
const SAVE_ONLY_FILE_COUNT := 34
const SAVE_ONLY_DOCUMENT_COUNT := 33

## The one walked document that carries no `privateState`, so the two figures
## above can never be read as an unexplained discrepancy.
const SAVE_ONLY_FILE_WITHOUT_PRIVATE_STATE := "tests/saves/manifest.json"

const SAVE_ONLY_ORIGIN_STATUS := "inference, not a measurement"

const SAVE_ONLY_NOTE := {
	"present_in_every_document": SAVE_ONLY_DOCUMENT_COUNT,
	"source_occurrences": 0,
	"origin": SAVE_ONLY_ORIGIN_STATUS,
	"why_an_inference": "written by some client this repository does not "
		+ "contain, read by nothing this repository does contain. That is a "
		+ "conclusion drawn from TOTAL source absence alongside UNIVERSAL save "
		+ "presence, and it is not itself a measurement (design D11)",
	"substring_artifact_recorded": "one field has exactly one whole-file "
		+ "occurrence, inside a longer identifier at auctions.py:176, so it is "
		+ "not a consumer of that field",
	"measured_correction": "the investigation recorded 39 documents; the "
		+ "committed census is 34 files walked of which 33 carry the fields, "
		+ "the one exclusion being " + SAVE_ONLY_FILE_WITHOUT_PRIVATE_STATE
		+ ". Only the denominator changes",
}

# ---------------------------------------------------------------------------
# the preserved arms
# ---------------------------------------------------------------------------

## The weekly branch's two arms, selected by the client's **argument count**
## and by nothing else (`command.py:346`). This contract has **no arm**; the
## table is the boundary report (design D5).
const WEEKLY_ARMS := [
	{"arm": "long", "selected_when": "the client sent five or more arguments",
		"test": "len(args) > 4", "source": "command.py:346",
		"grant_shaped": true, "reproduced": false,
		"printed": "Won <name>",
		"effect": "the branch reads five client-supplied values -- the map "
			+ "index, the item id, the two cell coordinates and the player team "
			+ "-- places a row, records the item, and prints 'Won <name>'"},
	{"arm": "short",
		"selected_when": "the client sent four or fewer arguments",
		"test": "len(args) <= 4", "source": "command.py:357",
		"grant_shaped": false, "reproduced": false,
		"printed": "Won resources",
		"effect": "the branch grants nothing at all, prints 'Won resources', "
			+ "and falls straight through to the stamp and the cursor advance"},
]

## The daily branch's two arms, selected by the **client-supplied item** and by
## nothing else (`command.py:458`).
const DAILY_ARMS := [
	{"arm": "granting", "selected_when": "the client sent a positive item",
		"test": "item > 0", "source": "command.py:458",
		"grant_shaped": true, "reproduced": false,
		"printed": "Put <name> in storage",
		"effect": "the branch records the item AND creates a storage entry, "
			+ "by two DIFFERENT rules -- the first deduplicates (it appends only "
			+ "when the id is absent, engine.py:86-89) and the second accumulates "
			+ "(it increments an existing key, engine.py:70-75) -- so one granted "
			+ "id lands in two places"},
	{"arm": "resources",
		"selected_when": "the client sent zero or a negative item",
		"test": "item <= 0", "source": "command.py:462",
		"grant_shaped": false, "reproduced": false,
		"printed": "Rewarded resources",
		"effect": "the branch grants nothing, moves no resource, and prints "
			+ "'Rewarded resources'"},
]

const ARM_COUNT_PER_ACTION := 2
const ARMS_TOTAL := 4

const ARMS_REPORT_NOTE := {
	"the_arm_boundary_is_reported_not_reproduced": true,
	"why": "both preserved branches select between granting and not granting "
		+ "on a value the CLIENT sent -- the weekly branch on its own ARGUMENT "
		+ "COUNT, so the same command name with different arities has two "
		+ "different effects, and the daily branch on the sign of a "
		+ "client-supplied item id. This contract has NO arm: it always sends the "
		+ "non-granting argument list, always grants nothing, and reports both "
		+ "arms' recorded effects so a reader sees what the arity and the sign "
		+ "would have selected. Reproducing either arm would mean accepting a "
		+ "grant-shaped value from a client, which is exactly what the request "
		+ "contract refuses",
	"reproducing_either_arm_would_require": "accepting a grant-shaped value "
		+ "from a client",
}

# ---------------------------------------------------------------------------
# the divergences
# ---------------------------------------------------------------------------

## The three recorded divergences, each with the reason it is a divergence and
## never parity.
const DIVERGENCES := [
	{"id": "client_sent_item",
		"summary": "the granted item id is taken from the client",
		"where": "command.py:348 (weekly) and command.py:445 (daily)",
		"reproduced": false,
		"consequence": "a recorded transaction establishes NOTHING about what "
			+ "was granted, because the grant was whatever the client asked for"},
	{"id": "client_sent_next_id",
		"summary": "the next cursor id is taken from the client and then "
			+ "overwritten when it exceeds the bound",
		"where": "command.py:446 and command.py:451-452",
		"reproduced": false,
		"consequence": "the preserved branch advances a CLIENT-SUPPLIED value, "
			+ "so a client that sent a larger id would have had its recorded "
			+ "cursor moved BACKWARDS onto the first position. This divergence "
			+ "is observable in the preserved SOURCE, not only in an executed "
			+ "record, which is what makes it the sharper of the two"},
	{"id": "client_sent_argument_count",
		"summary": "the weekly arm is selected by the client's argument count",
		"where": "command.py:346",
		"reproduced": false,
		"consequence": "the same command with five arguments places a row and "
			+ "with four grants nothing, so the preserved command name alone "
			+ "does not determine what it did"},
]

const DIVERGENCE_COUNT := 3
const DIVERGENCES_REPORTED_AS_PARITY := 0

# ---------------------------------------------------------------------------
# the grant refusal, the four-part proof, and the volatile fields
# ---------------------------------------------------------------------------

## The only leaf paths a successful action may change: the addressed cursor and
## the addressed instant. Every other path -- a map row, a bought-units list,
## the store, any stored resource, any cursor or instant this operation does not
## address -- is outside the allowlist, so the four-part grant proof is one
## whole-document containment check that **cannot miss a fifth landing place**
## and that names no foreign field (design D6).
const ALLOWED_LEAF_PATHS := {
	ACTION_WEEKLY: ["/" + PRIVATE_STATE_KEY + "/" + WEEKLY_CURSOR_KEY,
		"/" + PRIVATE_STATE_KEY + "/" + WEEKLY_STAMP_KEY],
	ACTION_DAILY: ["/" + PRIVATE_STATE_KEY + "/" + DAILY_CURSOR_KEY,
		"/" + PRIVATE_STATE_KEY + "/" + DAILY_STAMP_KEY],
}
const ALLOWED_LEAF_PATH_COUNT := 2

## The four parts of the grant proof, in the order the spec lists them. The
## complete stored resource set is compared as a **set**; a subset SHALL NOT be
## compared.
## `wire_key` is the key the service half uses inside its single `grant` block.
## It is recorded here so the two layers' grant proofs are recognisably the same
## four parts under two different encodings -- this file's array of typed rows
## and the service's four prose keys -- and so the parser can require all four
## **keys** to be present without comparing a single word of prose.
const REFUSAL_PROOF_PARTS := [
	{"part": 1, "id": "no_map_row", "wire_key": "part_1_no_map_row",
		"claim": "the placed-row count is unchanged and every existing row is "
			+ "byte-identical",
		"covered_by": "the whole-document leaf allowlist"},
	{"part": 2, "id": "no_bought_units_entry",
		"wire_key": "part_2_no_bought_units_append",
		"claim": "that list is byte-identical, which also covers the preserved "
			+ "helper's DEDUPLICATING behaviour",
		"covered_by": "the whole-document leaf allowlist"},
	{"part": 3, "id": "no_storage_entry", "wire_key": "part_3_no_storage_entry",
		"claim": "the store is byte-identical, which also covers the preserved "
			+ "helper's ACCUMULATING behaviour",
		"covered_by": "the whole-document leaf allowlist"},
	{"part": 4, "id": "no_stored_resource_moved",
		"wire_key": "part_4_no_stored_resource_moved",
		"claim": "the COMPLETE stored resource set the service exposes is "
			+ "byte-identical, compared as a set and NOT as a subset",
		"covered_by": "the complete resource-set equality the route performs"},
]

const REFUSAL_PROOF_PART_COUNT := 4

## The four `wire_key` values, so the parser requires exactly these four keys.
const REFUSAL_PROOF_WIRE_KEYS := [
	"part_1_no_map_row", "part_2_no_bought_units_append",
	"part_3_no_storage_entry", "part_4_no_stored_resource_moved",
]

const NO_REWARD_MOVED := {
	"nothing_is_granted": true,
	"why_non_tautological": "a grant could land in four distinct places and "
		+ "every successful action is checked against all four, so an "
		+ "implementation that quietly placed a row, appended a bought unit, or "
		+ "derived an amount would FAIL the proof rather than pass it as an "
		+ "absence of evidence",
	"carried_by": "a whole-document leaf allowlist restricted to the two paths "
		+ "this action may change, so a fifth landing place cannot be missed",
	"complete_resource_set_not_a_subset": true,
	"the_preserved_server_charges_and_credits_nothing": "measured across both "
		+ "executed arms, so any amount would be invention",
}

const NO_ELIGIBILITY := {
	"no_eligibility_cooldown_window_or_period": true,
	"no_already_claimed_test": true,
	"why": "both preserved branches stamp a wall-clock instant, and a write is "
		+ "reproducible parity, so the stamp is written. Nothing else is. The "
		+ "weekly instant has exactly ONE live write (command.py:361) and its "
		+ "only other occurrence is COMMENTED OUT; it has NO reader, so there is "
		+ "no window, no cooldown, no weekly period, no reset boundary and no "
		+ "already-claimed test to reproduce, and none is invented. Its NAME "
		+ "invites exactly the rule this contract refuses to write, which is why "
		+ "the absence is a recorded requirement rather than an implementation "
		+ "detail",
}

const NO_CURSOR_SELECTION := {
	"no_cursor_selects_a_schedule_entry": true,
	"the_weekly_bound_is_never_the_entry_count": true,
	"the_delivered_code_performs_no_indexing": "there is no helper that maps a "
		+ "cursor position to a rung, a type letter, or an amount, and the "
		+ "reachability report is a set difference over two ranges that "
		+ "deliberately performs no lookup",
	"both_differences_reported": "in BOTH directions, so the mismatch is "
		+ "visible rather than hidden inside one number",
}

## Width of the legacy **mutation** vector. `engine.apply_resources`
## (`engine.py:251-271`) unpacks exactly eight POSITIONAL slots: unknown, xp,
## gold, wood, oil, steel, cash, mana. Eight and not seven: the count is right and
## a list that dropped `oil` would read as a transcription of the source, which is
## the worse of the two defects.
##
## `privateState.energy` is a real stored resource under its own name and is
## **not** a slot of this vector; the eight-slot mutation vector has no room for
## it. This number is NOT the count of named stored resources -- see
## `RESOURCE_NAMES`, which is a different eight.
const MUTATION_VECTOR_SLOTS := 8

## The **EIGHT** stored resource slots a reward answer must expose, corrected
## from SEVEN by execution rather than by reading the service.
##
## `boot.resources()` -- the accessor the preserved server exposes -- returns
## exactly seven (`xp, gold, wood, oil, steel, cash, mana`), and the client's
## first draft listed exactly those seven. The real `/v0/reward` route answers
## with **eight**: its post-execution snapshot reads the seven and then adds
## `privateState.energy` whenever the save carries it, because `energy` is a real
## stored resource that no branch ever writes and the accessor has no slot for it.
## Every committed save document (33 of 33) carries it.
##
## So the client's list was WRONG and the live phase caught it: the parser
## demanded seven, the service answered eight, and every reward response was
## refused `bad_response` with a message that named the difference exactly. A
## seven-slot list here would have been a claim that a subset is the whole.
##
## The three sets this capability must not conflate, recorded together because
## two of them are both eights and reading the wrong one is the error:
##   * `MUTATION_VECTOR_SLOTS` -- 8 -- `engine.apply_resources` unpacks eight
##     POSITIONAL slots, the first of which is `unknown`. It is not a name list.
##   * `RESOURCE_NAMES` -- 8 -- the NAMED stored resources a reward answer
##     exposes: the seven accessor names plus `energy` under its own name.
##   * `SERVICE_ACCESSOR_NAMES` -- 7 -- what `boot.resources()` returns alone.
const RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash", "mana",
	"energy"]

## What `boot.resources()` returns on its own, recorded so the difference above is
## a named fact rather than something a reader has to rediscover.
const SERVICE_ACCESSOR_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana"]

const EXPOSED_RESOURCE_COUNT := 8

## The fields a successful answer cannot be compared by whole-document equality
## against, because each carries a wall clock: the answered action's own stamped
## instant, and the envelope's server time.
##
## Recorded as a prefix plus one field name rather than a flat list, because the
## stamped instant's path is **action-dependent** -- `timeStampMondayBonus` for
## the weekly action and `timestampLastBonus` for the daily one -- and a flat
## list of two literal paths would be a claim about one action only.
const VOLATILE_PRIVATE_PREFIX := "/" + PRIVATE_STATE_KEY + "/"
const VOLATILE_SERVER_TIME_FIELD := "server_time"
const VOLATILE_FIELD_COUNT := 2

# ---------------------------------------------------------------------------
# ownership, absences, and the guard inventory
# ---------------------------------------------------------------------------

## Save fields owned by **other** capabilities, recorded so the boundary is a
## hand-off and not an orphan (task 5.3).
##
## No identifier in this module is named after any of them: they appear exactly
## once each, here, in this one literal.
##
## ## THREE OWNER PATHS CORRECTED -- an earlier draft pointed all three at
## modules that do not own the field, or do not exist
##
## The first draft recorded `scripts/units/unit_instances.gd` for `boughtUnits`,
## `scripts/town/collection_flow.gd` for `store`, and
## `scripts/town/placement_flow.gd` for `items`. Measured: the first **does not
## exist**, and the second and third contain **zero** occurrences of their
## claimed field. Every one of the three hand-offs would therefore have been
## asserted against a file that cannot support it -- which is worse than not
## asserting, because the suite would have reported a boundary it never
## checked. Each path below was then found by searching the delivered client for
## the field itself, and each is verified twice by the suite: the owner file must
## **exist** and must actually **name** its field.
const FOREIGN_IDENTIFIERS := {
	"boughtUnits": "scripts/units/unit_instance_projection.gd",
	"store": "scripts/units/stored_item_flow.gd",
	"items": "scripts/town/placement_catalog.gd",
}

## What each owner does with its field, so the hand-off names a role rather than
## only a path. The suite asserts the path exists and names the field; this is
## the readable half.
const FOREIGN_IDENTIFIER_ROLES := {
	"boughtUnits": "the unit-instance row projection reports which units the "
		+ "recorded save lists as bought",
	"store": "the stored-item-placement projection reads maps[0]['store'] as "
		+ "the row's garrison list",
	"items": "the building-placement catalog reads the placed rows out of "
		+ "maps[0]['items']",
}

const FOREIGN_IDENTIFIER_COUNT := 3

## The save fields this capability DOES project, so the distinction from the
## table above is visible rather than assumed.
const OWNED_IDENTIFIERS := {
	"privateState": "the one field both preserved branches write into",
	"weeklyRewardIndex": "the weekly cursor",
	"bonusNextId": "the daily cursor",
	"timeStampMondayBonus": "the instant the weekly branch stamps",
	"timestampLastBonus": "the instant the daily branch stamps",
}

const OWNED_IDENTIFIER_COUNT := 5

## Helpers this capability deliberately does **not** define (design D7/D8/D10).
##
## Recorded as a named list so each absence is an assertion the suite can check
## and the report can publish, not a sentence in a docstring. A later line
## wanting any of these must derive behaviour from evidence rather than inherit
## an invented rule.
const ABSENT_HELPERS := [
	{"capability": "grant",
		"would": "place a row, append a bought unit, or create a storage entry",
		"forbidden_because": "NO_REWARD_MOVED"},
	{"capability": "cursor-to-rung selection",
		"would": "index a schedule by a cursor value, or map a cursor position "
			+ "onto a rung, a type letter, or an amount",
		"forbidden_because": "NO_CURSOR_SELECTION"},
	{"capability": "type-letter decoding",
		"would": "map a schedule type letter onto a resource slot, a resource "
			+ "name, or a grant shape",
		"forbidden_because": "TYPE_LETTERS_UNDECODED_NOTE"},
	{"capability": "eligibility, cooldown, window, or already-claimed test",
		"would": "compare the stamped instant against the current time, or "
			+ "gate an action on an elapsed interval",
		"forbidden_because": "NO_ELIGIBILITY"},
]

const ABSENT_HELPER_COUNT := 4

## The exact identifier names that must not appear in this module. Matched by
## the suite as **exact identifiers**, and separately as **substrings** of an
## identifier, because a suffixed helper wearing the same name (`grant_for`,
## `rung_at`) otherwise passes a by-name-only check -- a lesson recorded from
## the stored-placement line.
const FORBIDDEN_IDENTIFIER_NAMES := [
	"grant", "grant_for", "grant_reward", "award", "payout", "prize_for",
	"reward_amount", "reward_for", "rung_for", "rung_at", "select_rung",
	"schedule_at", "entry_for_cursor", "decode_type", "decode_letter",
	"letter_to_resource", "type_to_resource", "is_eligible", "is_ready",
	"can_claim", "cooldown_remaining", "already_claimed", "period_remaining",
]

## Identifier **fragments** a smuggled helper would wear. Checked as substrings,
## so a suffixed helper wearing a forbidden name is caught.
const FORBIDDEN_IDENTIFIER_FRAGMENTS := [
	"grant", "award", "payout", "redeem", "claim_window", "cooldown",
	"eligible", "is_ready", "can_claim", "rung", "decode_letter",
	"letter_to_", "type_to_", "entry_for_cursor", "schedule_at",
	"bought_unit", "boughtUnits", "buy_stored", "map_add_item",
]

## The identifiers this capability must never define, because the field they
## name is owned elsewhere. Kept as a **substring** list so the foreign save
## fields are excluded however they are spelled.
const FORBIDDEN_FOREIGN_KEYS := ["boughtUnits", "bought_unit", "map_items",
	"map_add_item", "buy_stored"]

## The one foreign field whose **bare** name a module cannot avoid saying in
## prose. It is recorded explicitly so the guard below can require that the one
## legitimate mention is the recorded one and not an identifier.
const FOREIGN_STORE_KEY := "store"

## ## The whole static-function inventory, pinned (design D7).
##
## This is the structural half of every refusal in this module. The suite reads
## this file, extracts its `static func` declarations, and requires this list to
## match exactly in BOTH directions, so adding a grant, selection, decoder, or
## eligibility helper fails the suite rather than quietly contradicting the
## line's central finding.
## Pinned in **declaration order**, and the suite compares the pin against the
## extracted declarations for **equality of the whole list**, not merely set
## membership: a reordered helper fails exactly as an added one does, because an
## inventory whose order is unspecified cannot answer "was this file reordered".
## The private helpers are pinned alongside the public ones -- an unpinned
## underscore helper is where a smuggled grant would hide.
const STATIC_FUNCTIONS := [
	"reward_failure",
	"repo_root_py_modules",
	"legacy_census_text",
	"is_action",
	"weekly_bound",
	"schedule_cardinality",
	"daily_bound",
	"weekly_successor",
	"daily_successor",
	"reachable_report",
	"committed_schedule_entries",
	"project_cursor",
	"project_save",
	"refused_client_keys",
	"build_reward_intent",
	"build_reward_response",
	"parse_reward",
	"_reward_error",
	"_is_integer_valued",
	"_wire_int_set",
	"_wire_int",
	"_is_encoded_absence",
	"_is_encoded_presence",
	"_kind_name",
	"_is_recorded_zero",
	"owners",
	"coverage_limit",
	"non_claims",
]

const STATIC_FUNCTION_COUNT := 28

## The claim limits, published rather than left to a reader to reconstruct.
const NON_CLAIMS := [
	"no reward is granted, priced, credited, or displayed, and no delivered "
		+ "identifier or response field implies that one was",
	"no schedule entry is ever selected from a cursor value, and no type "
		+ "letter is mapped onto a stored resource",
	"no eligibility, cooldown, window, period, or already-claimed rule is "
		+ "derived from the stamped instant",
	"the schedule census states a fact about the PRESERVED SERVER'S SOURCE "
		+ "only; this repository makes no claim about what any client did with "
		+ "the configuration bytes it was served",
	"the save-only fields' origin is an INFERENCE from total source absence "
		+ "alongside universal save presence, not a measurement",
	"the ranking-reward table is owned as normalized content and undelivered "
		+ "as gameplay; neither statement implies the other",
	"the zero-based schedule index is derived-provisional with the one-based "
		+ "alternative retained, and neither base is used to select an entry",
	"no executed-legacy transaction is parity for what was GRANTED, because "
		+ "the grant was client-sent in both branches",
	"nothing is rendered: there is no windowed capture and no pixel-parity "
		+ "oracle, because no reward display exists to compare",
]

## What this line's coverage actually is.
const COVERAGE_LIMIT := {
	"actions": ACTION_COUNT,
	"branches": 2,
	"schedules_reported": SCHEDULE_COUNT,
	"schedules_with_no_consumer": SCHEDULES_WITH_NO_CONSUMER_COUNT,
	"save_only_fields": SAVE_ONLY_FIELD_COUNT,
	"committed_save_documents": SAVE_ONLY_DOCUMENT_COUNT,
	"committed_save_files_walked": SAVE_ONLY_FILE_COUNT,
	"cursors": CURSOR_COUNT,
	"instants": 2,
	"modules_censused": "discovered at run time; the recorded count is 11",
	"no_progressed_player_save": "the executed-legacy capture used committed "
		+ "village documents; no claim is made about any other corpus",
	"nothing_rendered": true,
	"no_pixel_parity": true,
	"no_flash": true,
	"no_network_in_the_hermetic_suite": true,
}

# ---------------------------------------------------------------------------
# the typed projections
# ---------------------------------------------------------------------------

## One reward cursor as projected recorded state.
##
## Read-only by construction. It carries no grant, no amount, and no derived
## field beyond the branch's own arithmetic, and `selected` is always false:
## there is no member that names a schedule entry.
class Cursor extends RefCounted:
	var action := ""
	var command := ""
	var key := ""
	var stamp_key := ""
	var schedule_key := ""
	## The recorded value; `value_present` distinguishes an absent key from a
	## recorded zero, so an absent cursor is never read as zero.
	var value := 0
	var value_present := false
	## The branch's own arithmetic applied to the recorded value.
	var successor := 0
	var change := 0
	## The derived (weekly) or literal (daily) bound this action applies.
	var bound := 0
	var bound_source := ""
	var bound_is_literal := false
	var bound_rejected_alternative: Variant = ""
	## The committed schedule's entry count, reported BESIDE the bound.
	var schedule_cardinality := 0
	var index_base := SCHEDULE_INDEX_BASE
	## The positions the cursor can reach, the positions the schedule can
	## answer, and the difference in BOTH directions.
	var reachable: Array = []
	var answerable: Array = []
	var reachable_not_answerable: Array = []
	var answerable_not_reachable: Array = []
	## Always false; recorded so the absence is readable rather than inferred.
	var selection_performed := false
	var stamp_present := false
	var stamp_before := -1

## One committed schedule entry, verbatim.
##
## `entry` is the committed value **untouched**. `type_letter` is the committed
## letter as stored, or "" where the entry has none. `decoded` is always false
## and `mapped_to_resource` always "", which is what makes the "undecoded"
## claim mechanical rather than prose.
class ScheduleEntry extends RefCounted:
	var schedule_key := ""
	var position := 0
	var entry: Variant = null
	var type_letter := ""
	var decoded := false
	var mapped_to_resource := ""
	## The committed `value` of a two-key object entry, or the bare committed
	## scalar for the daily schedule's shape. Carried separately from `entry`
	## because `entry` is the committed value **untouched** and the two are not
	## the same field for the object shape.
	var value: Variant = null
	var value_shape := ""
	var counts_toward_weekly_bound := false
	var committed_value_is_zero := false

## One type letter, verbatim and undecoded.
class TypeLetter extends RefCounted:
	var letter := ""
	var decoded := false
	var mapped_to_resource := ""
	var decoder_searches := 0
	var decoder_search_hits := 0
	var declared_elsewhere_as: Array = []

## Both cursors and both schedules projected out of one recorded save document.
##
## Content and reported state only: there is no member that names a rung, an
## amount, a prize, or a resource this operation would move.
class CursorProjection extends RefCounted:
	var ok := false
	var reason := ""
	var error := ""
	var private_state_present := false
	var weekly_bound := 0
	var weekly_cardinality := 0
	var daily_bound := 0
	var daily_cardinality := 0
	var cursors: Array = []
	## schedule key -> Array[ScheduleEntry]
	var schedule_entries: Dictionary = {}
	var type_letters: Array = []
	var derivation_record: Dictionary = {}

## One derived reward transition, and every record it must travel with.
class RewardResult extends RefCounted:
	var ok := false
	var reason := ""
	var error := ""
	var action := ""
	var command := ""
	var cursor_key := ""
	var cursor_before := 0
	var cursor_after := 0
	var cursor_change := 0
	var bound := 0
	var bound_source := ""
	var bound_is_literal := false
	var bound_rejected_alternative: Variant = ""
	var stamp_key := ""
	var stamp_before := -1
	var stamp_stamped := false
	var stamp_volatile := false
	var schedule_key := ""
	var schedule_cardinality := 0
	var index_base := 0
	var reachable: Array = []
	var answerable: Array = []
	var reachable_not_answerable: Array = []
	var answerable_not_reachable: Array = []
	## **Both** cursors' recomputed reachability reports, keyed by action. The
	## four fields above are the addressed cursor's, flattened for convenience;
	## this keeps the other one, because the whole point of the block is that the
	## two cursors' differences are not the same difference and a caller that
	## could only read the addressed one would be unable to tell.
	var reachability: Dictionary = {}
	var selection_performed := false
	var bounds: Dictionary = {}
	var schedules: Array = []
	var schedule_entries: Dictionary = {}
	var type_letters: Array = []
	var save_only_fields: Array = []
	var arms: Dictionary = {}
	var divergences: Array = []
	var refusal_evidence: Dictionary = {}
	var allowed_leaf_paths: Array = []
	var refusals: Array = []
	var validation_order: Array = []
	var derived_args: Array = []
	## The module's own derivation record, **not** an answer field. It is copied
	## from this module's constant rather than read off the wire, so a caller can
	## never believe the service asserted this module's rule set.
	var derivation_record: Dictionary = {}
	## The successor this client re-derived from the reported before value and the
	## reported bound, kept beside the answered one so a caller can see that they
	## agree rather than having to take the parser's word for it.
	var derived_after := 0
	var derived_change := 0
	var volatile_fields: Array = []

	# --- the wire record ----------------------------------------------------

	var protocol := ""
	var result := ""
	var game_version := ""
	## -1 until parsed. A recorded instant, never the wall clock on this side.
	var server_time := -1
	## The COMPLETE stored resource set after execution, never a subset.
	var resources: Dictionary = {}
	var resource_count := 0
	var changed: Array = []

# ---------------------------------------------------------------------------
# the typed result constructor
# ---------------------------------------------------------------------------


## A structured failure for a reward intent -- never a partial payload.
static func reward_failure(code: String, message: String) -> RewardResult:
	var result := RewardResult.new()
	result.ok = false
	result.reason = code
	result.error = message
	result.bound_is_literal = DAILY_BOUND_IS_LITERAL
	result.refusal_evidence = NO_REWARD_MOVED
	result.selection_performed = false
	return result

# ---------------------------------------------------------------------------
# the legacy source census -- DISCOVERED, never transcribed
# ---------------------------------------------------------------------------


## Every top-level `.py` in the repository root, sorted, as file names.
##
## **Discovered, not written out.** The consumer census is over "all eleven
## top-level legacy modules"; transcribing that list would make a twelfth
## module invisible, which is the exact failure the discovery avoids. A
## directory that cannot be opened yields an empty list, which is a figure the
## suite refuses to believe -- it asserts the count is non-zero BEFORE any
## zero-consumer verdict is accepted.
static func repo_root_py_modules() -> Array:
	var root := Paths.repo_root()
	var directory := DirAccess.open(root)
	if directory == null:
		return []
	var names: Array = []
	directory.list_dir_begin()
	var entry := directory.get_next()
	while entry != "":
		if not directory.current_is_dir() \
				and entry.get_extension().to_lower() == "py" \
				and not entry.begins_with("_"):
			names.append(str(entry))
		entry = directory.get_next()
	directory.list_dir_end()
	names.sort()
	return names


## The recorded body of every discovered top-level module, keyed by file name.
##
## `{"ok": false}` when the repository root cannot be read at all, so a caller
## can never mistake an empty corpus for a census of nothing.
static func legacy_census_text() -> Dictionary:
	var root := Paths.repo_root()
	var names := repo_root_py_modules()
	if names.is_empty():
		return {"ok": false,
			"error": "no top-level .py module found under " + root,
			"modules": [], "module_count": 0, "text": {}}
	var bodies := {}
	for name: String in names:
		var handle := FileAccess.open(root.path_join(name), FileAccess.READ)
		if handle == null:
			return {"ok": false,
				"error": "cannot read " + str(name),
				"modules": names, "module_count": names.size(), "text": {}}
		var bytes := handle.get_buffer(handle.get_length())
		handle = null
		bodies[name] = bytes.get_string_from_utf8()
	return {"ok": true, "error": "", "modules": names,
		"module_count": names.size(), "text": bodies}

# ---------------------------------------------------------------------------
# the closed vocabulary
# ---------------------------------------------------------------------------


## Whether `value` names one of the two closed reward actions.
##
## The set is **closed**: the branches' grant arms are deliberately absent, so
## there is no action that places a row, appends a bought unit, or creates a
## storage entry. Anything outside the set is refused before a request is built,
## so an unknown action can never reach a branch that would treat it as an
## unhandled command.
static func is_action(value: Variant) -> bool:
	return value is String and ACTIONS.has(str(value))

# ---------------------------------------------------------------------------
# the bounds and the successors
# ---------------------------------------------------------------------------


## `get_weekly_reward_length`'s own result, derived the same way.
##
## The preserved helper (`get_game_config.py:195-204`) seeds `length = 1` and
## then takes `max` over the entries whose `value` is a **list**. That is the
## whole rule and it is transcribed rather than approximated:
##
##   * the floor is load-bearing -- a schedule whose every value were a scalar
##     returns **1**, not 0;
##   * the bound is the maximum entry length over **list-valued** entries, so it
##     is the item list *inside* one rung, never the number of rungs;
##   * anything that is not a list of objects carrying a `value` is
##     **refused**, never skipped -- skipping would let a malformed rung change
##     the derived bound silently.
##
## For the committed schedule this yields **5** while the cardinality is **3**,
## and the two are reported side by side.
static func weekly_bound(schedule: Variant) -> Dictionary:
	if not (schedule is Array):
		return {"ok": false,
			"error": "the committed weekly schedule is not an array",
			"value": 0}
	if (schedule as Array).is_empty():
		return {"ok": false, "error": "the committed weekly schedule is empty",
			"value": 0}
	var length: int = WEEKLY_BOUND_FLOOR
	for position in range((schedule as Array).size()):
		var entry: Variant = (schedule as Array)[position]
		if not (entry is Dictionary) or not (entry as Dictionary).has("value"):
			return {"ok": false,
				"error": "weekly schedule entry " + str(position)
					+ " is not an object carrying a 'value', so no bound is "
					+ "derivable from it",
				"value": 0}
		var value: Variant = (entry as Dictionary)["value"]
		if value is Array and (value as Array).size() > length:
			length = (value as Array).size()
	return {"ok": true, "error": "", "value": length}


## The schedule's **entry count**, reported beside the derived bound.
##
## This is the number the derived bound is **not**: the spec requires both to
## be visible, because a reader who received only the bound would not know that
## some of its positions name nothing.
static func schedule_cardinality(schedule: Variant) -> Dictionary:
	if not (schedule is Array):
		return {"ok": false, "error": "the committed schedule is not an array",
			"value": 0}
	return {"ok": true, "error": "", "value": (schedule as Array).size()}


## The **hardcoded literal** at `command.py:451`, never content-derived.
##
## `DAILY_BOUND_REJECTED_DERIVATION` records the rejected alternative and why the
## agreement between this literal and the daily schedule's entry count is a
## coincidence rather than provenance (design D4).
static func daily_bound() -> int:
	return DAILY_BOUND_LITERAL


## The weekly successor: `(before + 1) % bound` (`command.py:363`).
##
## Transcribed from the branch, not invented: the preserved expression advances
## the recorded cursor by one modulo `get_weekly_reward_length()`. A bound of
## zero is **refused** rather than raising, because a service that would divide
## by an unaddressable position is not delivering behaviour.
static func weekly_successor(before: Variant, bound: Variant) -> Dictionary:
	if not _is_integer_valued(before):
		return {"ok": false, "error": "the recorded weekly cursor is not an "
			+ "integer", "value": 0}
	if not _is_integer_valued(bound) or int(bound) <= 0:
		return {"ok": false, "error": "the derived weekly bound is not a "
			+ "positive integer", "value": 0}
	return {"ok": true, "error": "",
		"value": (int(before) + 1) % int(bound)}


## The daily successor: `before + 1`, wrapped to 1 above the literal.
##
## Transcribed from the branch's own two statements (`command.py:446` and
## `:451-452`). The **recorded** cursor is fed to it, never a client value, so
## the same arithmetic produces the successor -- and the wrap means a recorded
## cursor at or above the literal moves ONTO the first position, which is the
## backwards move design D5 records as a divergence when the client sends a
## larger value.
static func daily_successor(before: Variant) -> Dictionary:
	if not _is_integer_valued(before):
		return {"ok": false, "error": "the recorded daily cursor is not an "
			+ "integer", "value": 0}
	var successor: int = int(before) + 1
	if successor > DAILY_BOUND_LITERAL:
		return {"ok": true, "error": "", "value": DAILY_WRAP_TARGET}
	return {"ok": true, "error": "", "value": successor}


## One cursor's reachability against one schedule -- a set difference only.
##
## Returns `{index_base, reachable, answerable, reachable_not_answerable,
## answerable_not_reachable, bound, cardinality, selection_performed}`.
##
## `answerable` is `range(cardinality)` under the recorded zero-based index
## base and `reachable` is the **caller's** closed range of positions that
## cursor can actually reach. Both differences are reported so the mismatch is
## visible in **both** directions rather than hidden inside one number.
##
## The reachable range is a **parameter** rather than a lookup by bound on
## purpose: both cursors' bounds are the same number, so a table keyed by bound
## could not tell the two reports apart -- the weekly cursor reaches `0..4` by a
## modulo while the daily cursor reaches `1..5` by a wrap, and conflating them
## would report the wrong reachable set for one of the two.
##
## This function performs **no schedule lookup**: it never indexes a schedule by
## a cursor, never maps a position onto a rung, a type letter, or an amount, and
## `selection_performed` is the machine-readable statement of that.
static func reachable_report(bound: int, cardinality: int,
		reachable: Array) -> Dictionary:
	var reach: Array = []
	for value: Variant in reachable:
		reach.append(int(value))
	reach.sort()
	var answerable: Array = []
	for position in range(maxi(cardinality, 0)):
		answerable.append(position)
	var reach_only: Array = []
	for value: int in reach:
		if not answerable.has(value):
			reach_only.append(value)
	var answer_only: Array = []
	for value: int in answerable:
		if not reach.has(value):
			answer_only.append(value)
	return {
		"index_base": SCHEDULE_INDEX_BASE,
		# The base's own status is deliberately NOT repeated here: the answer
		# carries it once at the top level, and a record that repeats the same
		# paragraph in six places can drift between them.
		"reachable": reach,
		"answerable": answerable,
		"reachable_not_answerable": reach_only,
		"answerable_not_reachable": answer_only,
		"bound": bound,
		"cardinality": cardinality,
		"exceeds_cardinality_by": bound - cardinality,
		"selection_performed": false,
	}

# ---------------------------------------------------------------------------
# the committed entries, verbatim
# ---------------------------------------------------------------------------


## One schedule's committed entries, reported **verbatim** and in order.
##
## Every entry is reported, in committed order, under an untouched `entry`, with
## its `type` letter reproduced exactly as stored (where the entry has one) and
## `decoded` fixed at false. Nothing is selected, indexed by a cursor,
## normalized, or mapped onto a resource (design D3/D10).
##
## Two committed facts are surfaced rather than filtered out, because both are
## what makes the bound and the schedule disagree in a way a reader would
## otherwise not see:
##
##   * an entry whose committed value is **zero** is named by position, because a
##     reader shown only the non-zero entries would conclude the schedule pays
##     at every position;
##   * a **list-valued** entry is marked, because that is precisely the entry
##     the preserved length helper counts toward the derived bound -- the bound
##     is the maximum list length, not the rung count.
##
## The two schedules have two different committed shapes -- the weekly one is a
## list of two-key objects and the daily one is five bare numbers -- and both
## are accepted and reported in full, because refusing the daily shape would
## refuse the very schedule this report exists to show.
static func committed_schedule_entries(schedule: Variant,
		schedule_key: String) -> Array:
	if not (schedule is Array):
		return []
	var rows: Array = []
	for position in range((schedule as Array).size()):
		var committed: Variant = (schedule as Array)[position]
		var row := ScheduleEntry.new()
		row.schedule_key = schedule_key
		row.position = position
		row.entry = committed
		row.decoded = false
		row.mapped_to_resource = ""
		if committed is Dictionary:
			var body: Dictionary = committed
			var letter: Variant = body.get("type")
			row.type_letter = "" if letter == null else str(letter)
			row.value = body.get("value")
			if row.value is Array:
				row.value_shape = "list"
				row.counts_toward_weekly_bound = true
			else:
				row.value_shape = _kind_name(row.value)
			row.committed_value_is_zero = _is_recorded_zero(row.value)
		else:
			row.type_letter = ""
			row.value = committed
			row.value_shape = _kind_name(committed)
			row.counts_toward_weekly_bound = false
			row.committed_value_is_zero = _is_recorded_zero(committed)
		rows.append(row)
	return rows

# ---------------------------------------------------------------------------
# the offline projection
# ---------------------------------------------------------------------------


## Project one cursor out of a recorded private state, failing closed.
##
## An absent cursor is **refused**, never read as zero: the two preserved
## branches read the key and would raise, so treating absence as zero would make
## this projection disagree with the preserved source in the one case where the
## difference matters. The instant is read alongside it for the same reason --
## an absent key is a refusal rather than a value the branch would create.
static func project_cursor(private: Variant, action: Variant,
		bound: int, cardinality: int) -> Dictionary:
	if not is_action(action):
		return {"ok": false, "reason": "unknown_action",
			"error": "action must be one of " + ", ".join(ACTIONS)}
	var name := str(action)
	if not (private is Dictionary):
		return {"ok": false, "reason": "absent_reward_cursor",
			"error": "the recorded private state is not an object"}
	var body: Dictionary = private
	var cursor_key: String = ACTION_CURSOR_KEY[name]
	var stamp_key: String = ACTION_STAMP_KEY[name]
	if not body.has(cursor_key):
		return {"ok": false, "reason": "absent_reward_cursor",
			"error": "the recorded private state carries no " + cursor_key}
	if not _is_integer_valued(body[cursor_key]):
		return {"ok": false, "reason": "invalid_reward_cursor",
			"error": cursor_key + " is not an integer"}
	if not body.has(stamp_key):
		return {"ok": false, "reason": "absent_reward_instant",
			"error": "the recorded private state carries no " + stamp_key}
	if not _is_integer_valued(body[stamp_key]):
		return {"ok": false, "reason": "invalid_reward_cursor",
			"error": stamp_key + " is not an integer"}
	var before: int = int(body[cursor_key])
	var stepped := weekly_successor(before, bound) if name == ACTION_WEEKLY \
		else daily_successor(before)
	if not bool(stepped["ok"]):
		return {"ok": false,
			"reason": "invalid_reward_schedule" if name == ACTION_WEEKLY
				else "invalid_reward_cursor",
			"error": str(stepped["error"])}
	var report := reachable_report(bound, cardinality,
		ACTION_REACHABLE[name] as Array)
	var cursor := Cursor.new()
	cursor.action = name
	cursor.command = ACTION_COMMAND[name]
	cursor.key = cursor_key
	cursor.stamp_key = stamp_key
	cursor.schedule_key = ACTION_SCHEDULE_KEY[name]
	cursor.value = before
	cursor.value_present = true
	cursor.successor = int(stepped["value"])
	cursor.change = cursor.successor - before
	cursor.bound = bound
	cursor.bound_source = WEEKLY_BOUND_SOURCE if name == ACTION_WEEKLY \
		else DAILY_BOUND_SOURCE
	cursor.bound_is_literal = name == ACTION_DAILY
	cursor.bound_rejected_alternative = DAILY_BOUND_REJECTED_DERIVATION \
		if name == ACTION_DAILY else ""
	cursor.schedule_cardinality = cardinality
	cursor.index_base = SCHEDULE_INDEX_BASE
	cursor.reachable = report["reachable"]
	cursor.answerable = report["answerable"]
	cursor.reachable_not_answerable = report["reachable_not_answerable"]
	cursor.answerable_not_reachable = report["answerable_not_reachable"]
	cursor.selection_performed = false
	cursor.stamp_present = true
	cursor.stamp_before = int(body[stamp_key])
	return {"ok": true, "reason": "", "error": "", "cursor": cursor}


## Project **both** cursors and **both** schedules out of one recorded save
## document, with the three type letters beside them.
##
## This is the read-only projection the hermetic suite drives over committed
## content and committed saves, and the offline double's own derivation. It
## performs the one documented derivation (the weekly bound), reports both
## cardinalities beside it, and selects nothing.
##
## `schedules` is `{schedule key: committed value}`. A missing key is refused
## rather than defaulted to an empty array: an empty array would report a
## cardinality of 0 and a bound of 1 and look like a schedule that pays nothing.
static func project_save(save_document: Variant,
		schedules: Dictionary) -> Dictionary:
	var projection := CursorProjection.new()
	projection.derivation_record = DERIVATION_RECORD
	if not (save_document is Dictionary):
		projection.reason = "bad_request"
		projection.error = "the recorded save document is not an object"
		return {"ok": false, "projection": projection,
			"reason": projection.reason, "error": projection.error}
	var document: Dictionary = save_document
	for key: String in ACTION_SCHEDULE_KEY.values():
		if not schedules.has(key):
			projection.reason = "invalid_reward_schedule"
			projection.error = "no committed " + str(key) + " was supplied"
			return {"ok": false, "projection": projection,
				"reason": projection.reason, "error": projection.error}
	var weekly_schedule: Variant = schedules[WEEKLY_SCHEDULE_KEY]
	var daily_schedule: Variant = schedules[DAILY_SCHEDULE_KEY]
	var bound := weekly_bound(weekly_schedule)
	if not bool(bound["ok"]):
		projection.reason = "invalid_reward_schedule"
		projection.error = str(bound["error"])
		return {"ok": false, "projection": projection,
			"reason": projection.reason, "error": projection.error}
	var weekly_count := schedule_cardinality(weekly_schedule)
	var daily_count := schedule_cardinality(daily_schedule)
	if not bool(weekly_count["ok"]) or not bool(daily_count["ok"]):
		projection.reason = "invalid_reward_schedule"
		projection.error = "a committed schedule is not an array"
		return {"ok": false, "projection": projection,
			"reason": projection.reason, "error": projection.error}
	projection.weekly_bound = int(bound["value"])
	projection.weekly_cardinality = int(weekly_count["value"])
	projection.daily_bound = daily_bound()
	projection.daily_cardinality = int(daily_count["value"])
	projection.schedule_entries = {
		WEEKLY_SCHEDULE_KEY: committed_schedule_entries(weekly_schedule,
			WEEKLY_SCHEDULE_KEY),
		DAILY_SCHEDULE_KEY: committed_schedule_entries(daily_schedule,
			DAILY_SCHEDULE_KEY),
	}
	for letter: String in TYPE_LETTERS:
		var declared: Array = []
		for row: Dictionary in LETTER_NAMED_DECLARATIONS:
			if str(row["letter"]) == letter:
				declared.append(str(row["declared_as"]))
		var projected := TypeLetter.new()
		projected.letter = letter
		projected.decoded = false
		projected.mapped_to_resource = ""
		projected.decoder_searches = DECODER_SEARCH_COUNT
		projected.decoder_search_hits = DECODER_SEARCH_HIT_TOTAL
		projected.declared_elsewhere_as = declared
		projection.type_letters.append(projected)
	if not document.has(PRIVATE_STATE_KEY):
		projection.reason = "absent_reward_cursor"
		projection.error = "the recorded save carries no " + PRIVATE_STATE_KEY
		return {"ok": false, "projection": projection,
			"reason": projection.reason, "error": projection.error}
	projection.private_state_present = true
	var private: Variant = document[PRIVATE_STATE_KEY]
	for action: String in ACTIONS:
		var projected_cursor := project_cursor(private, action,
			projection.weekly_bound if action == ACTION_WEEKLY
				else projection.daily_bound,
			projection.weekly_cardinality if action == ACTION_WEEKLY
				else projection.daily_cardinality)
		if not bool(projected_cursor["ok"]):
			projection.reason = str(projected_cursor["reason"])
			projection.error = str(projected_cursor["error"])
			return {"ok": false, "projection": projection,
				"reason": projection.reason, "error": projection.error}
		projection.cursors.append(projected_cursor["cursor"])
	projection.ok = true
	return {"ok": true, "reason": "", "error": "", "projection": projection}

# ---------------------------------------------------------------------------
# the request: two keys, no addressing key, grant shapes refused
# ---------------------------------------------------------------------------


## The request keys a client-supplied body would resolve, in the pinned order.
##
## Reported rather than merely refused, so the refusal vocabulary is data a
## caller can read. The two cell coordinates resolve to the same class as `cell`,
## which is why the alias list is published beside the class list.
static func refused_client_keys(payload: Variant) -> Array:
	if not (payload is Dictionary):
		return []
	var found: Array = []
	for entry: Array in CLIENT_KEY_REFUSALS:
		var key := str(entry[0])
		if (payload as Dictionary).has(key) and not found.has(key):
			found.append(key)
	for key: String in CLIENT_KEY_ALIASES:
		if (payload as Dictionary).has(key) and not found.has(key):
			found.append(key)
	return found


## Build the delivered request body: **exactly two keys**.
##
## `user_id` and `action`. There is deliberately **no addressing key** of any
## kind, because neither preserved branch addresses a row -- and `build_reward_intent`
## REFUSES rather than defaulting, so a caller that wants one is told there is
## none instead of receiving a lookup that would silently pick something.
##
## A grant-shaped argument cannot be expressed here at all: the signature takes
## a user id and an action, and nothing else. The `client_supplied_*` refusals
## are therefore properties of a **hand-built** request, and the suite says so
## rather than implying this builder can raise one.
static func build_reward_intent(user_id: String, action: Variant) -> Dictionary:
	if not is_action(action):
		return {"ok": false, "reason": "invalid_action",
			"error": "action must be one of " + ", ".join(ACTIONS)
				+ ", got " + str(action)}
	if user_id.strip_edges() == "":
		return {"ok": false, "reason": "missing_user_id",
			"error": "user_id must be a non-empty string"}
	var body := {"user_id": user_id, "action": str(action)}
	return {"ok": true, "reason": "", "error": "", "body": body}

# ---------------------------------------------------------------------------
# the response
# ---------------------------------------------------------------------------


## Assemble the response envelope for one **accepted** reward intent.
##
## `projection` is a `project_save()` result and `post` carries the
## post-execution state a caller measured:
##
##     cursor_after  the persisted cursor value, or null when unknown
##     resources     the COMPLETE stored resource set AFTER execution
##     changed       the changed-pointer list the proof produced
##     server_time   a recorded instant -- never the wall clock
##     game_version  the recorded game version, "" when unknown
##
## ## The envelope's shape is the SERVICE's shape, not this module's
##
## The whole projection is nested under one `reward` key, beside `resources` and
## `changed`, because that is what `POST /v0/reward` answers and this module's
## parser is what **both** answers pass through. A flatter shape would have been
## easier to write here and would have been a second shape: two shapes for one
## contract is a shape that can drift from the parser that has to accept it.
## That exact class of defect -- one implementation building an envelope its own
## parser did not expect -- is what the quests line found in five separate
## places, so this one is written against the measured service payload rather
## than against a convenient local reading of it.
##
## Two fields this function used to invent are **not** on the wire, and their
## absence is deliberate rather than an oversight:
##
##   * `bound_is_literal` is not sent. It is **derived** here from the action --
##     the daily bound is the transcribed literal and the weekly bound is derived
##     from committed content -- and the parser recomputes the same answer rather
##     than reading a claim.
##   * `save_only_fields`, `validation_order`, `refusals`, and
##     `derivation_record` are not sent. They are **module records**, not answer
##     fields: they describe the contract rather than a transaction, so putting
##     them in an answer would make a caller believe the service asserted them.
##     They are published as constants and copied onto the typed result, which is
##     what makes the difference visible in one place.
static func build_reward_response(action: Variant, projection: Dictionary,
		post: Dictionary) -> Dictionary:
	var name := str(action)
	var typed: CursorProjection = projection["projection"]
	var addressed: Cursor = null
	for candidate: Cursor in typed.cursors:
		if candidate.action == name:
			addressed = candidate
	if addressed == null:
		return {"ok": false, "reason": "bad_request",
			"error": "the projection carries no cursor for " + name}
	var persisted: Variant = post.get("cursor_after")
	var cursor_after: int = addressed.successor
	if persisted is int or persisted is float:
		cursor_after = int(persisted)

	var schedule_rows: Array = []
	for row: Dictionary in SCHEDULES:
		schedule_rows.append({
			"name": str(row["name"]),
			"consumers": int(row["consumers"]),
			"consumed_for": str(row["consumed_for"]),
		})

	var entry_rows := {}
	for key: String in typed.schedule_entries:
		var out: Array = []
		for row: ScheduleEntry in typed.schedule_entries[key]:
			out.append({
				"position": row.position,
				"entry": row.entry,
				"type": row.type_letter,
				"decoded": row.decoded,
				"mapped_to_resource": row.mapped_to_resource,
				"value": row.value,
				"value_shape": row.value_shape,
				"counts_toward_weekly_bound": row.counts_toward_weekly_bound,
				"committed_value_is_zero": row.committed_value_is_zero,
			})
		entry_rows[key] = out

	var letter_rows: Array = []
	for row: TypeLetter in typed.type_letters:
		letter_rows.append({
			"letter": row.letter,
			"decoded": row.decoded,
			"mapped_to_resource": row.mapped_to_resource,
			"decoder_search_hits": row.decoder_search_hits,
			"decoder_searches": row.decoder_searches,
			"declared_elsewhere_as": row.declared_elsewhere_as.duplicate(),
			"note": TYPE_LETTERS_UNDECODED_NOTE,
		})

	var bounds_block := {
		"weekly": {
			"bound": typed.weekly_bound,
			"source": WEEKLY_BOUND_SOURCE,
			"derived_from": WEEKLY_BOUND_DERIVED_FROM,
			"floor": WEEKLY_BOUND_FLOOR,
			"cardinality": typed.weekly_cardinality,
			"schedule": WEEKLY_SCHEDULE_KEY,
			"exceeds_cardinality_by": typed.weekly_bound
				- typed.weekly_cardinality,
		},
		"daily": {
			"bound": typed.daily_bound,
			"source": DAILY_BOUND_SOURCE,
			"derived_from": "a hardcoded literal in the preserved source",
			"wrap_target": DAILY_WRAP_TARGET,
			"cardinality": typed.daily_cardinality,
			"cardinality_source": "the committed daily schedule's entry count, "
				+ "reported rather than derived: no branch reads that schedule, "
				+ "so no caller can derive its length from a legacy helper",
			"schedule": DAILY_SCHEDULE_KEY,
			"exceeds_cardinality_by": typed.daily_bound
				- typed.daily_cardinality,
			"rejected_alternative": DAILY_BOUND_REJECTED_DERIVATION,
		},
		"note": NO_CURSOR_SELECTION,
	}

	# Each cursor's reachability sits under **its own** action key rather than
	# being hoisted to the top of the answer, so one answer reports both
	# cursors' differences and a caller cannot read one cursor's reachable set
	# as the other's. The two reports differ: weekly reaches 0..4 by a modulo,
	# daily reaches 1..5 by a wrap.
	var reachability := {}
	for action_name: String in ACTIONS:
		var report := reachable_report(
			typed.weekly_bound if action_name == ACTION_WEEKLY
				else typed.daily_bound,
			typed.weekly_cardinality if action_name == ACTION_WEEKLY
				else typed.daily_cardinality,
			ACTION_REACHABLE[action_name] as Array)
		report["index_base_status"] = SCHEDULE_INDEX_BASE_STATUS
		reachability[action_name] = report

	# One `grant` block carrying all four parts as their own keys, so the
	# four-part proof is four **assertable** statements rather than one prose
	# paragraph. `allowed_leaf_paths` rides with them because it is what makes
	# the proof a containment check rather than four hand-maintained checks.
	var refusal_block := {
		"grants_nothing": true,
		"carried_by": str(NO_REWARD_MOVED["carried_by"]),
		"allowed_leaf_paths": ALLOWED_LEAF_PATHS[name],
		"note": NO_REWARD_MOVED,
	}
	for part: Dictionary in REFUSAL_PROOF_PARTS:
		refusal_block[str(part["wire_key"])] = str(part["claim"])

	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"result": "success",
		"game_version": str(post.get("game_version", "")),
		"server_time": int(post.get("server_time", 0)),
		"reward": {
			"action": name,
			"command": addressed.command,
			"cursor": {
				"key": addressed.key,
				"before": addressed.value,
				"after": cursor_after,
				"change": cursor_after - addressed.value,
			},
			"bound": addressed.bound,
			"bound_source": addressed.bound_source,
			# `None` for the weekly action and the rejected-alternative record for
			# the daily one: there is nothing to reject when the bound is derived
			# from the schedule it is about.
			"bound_rejected_alternative": DAILY_BOUND_REJECTED_DERIVATION
				if name == ACTION_DAILY else null,
			"instant": {
				"key": addressed.stamp_key,
				# The wall clock is not derivable, so the branch writes it and the
				# answer reports only what the RECORD held beforehand. The executed
				# value is compared by shape, never by equality.
				"stamped": true,
				"volatile": true,
				"value_before": addressed.stamp_before,
				"note": NO_ELIGIBILITY,
			},
			# Empty for the weekly action: an empty argument list IS the mechanism
			# by which the preserved branch's arity test selects its non-granting
			# arm. Two derived values for the daily action -- the item at zero and
			# the recorded cursor -- and neither is ever a client value.
			"derived_args": [] if name == ACTION_WEEKLY
				else [DERIVED_DAILY_ITEM, addressed.value],
			"grant": refusal_block,
			"bounds": bounds_block,
			"reachability": reachability,
			"schedules": schedule_rows,
			"schedule_entries": entry_rows,
			"type_letters": letter_rows,
			"arms": {
				"weekly": WEEKLY_ARMS,
				"daily": DAILY_ARMS,
				"note": ARMS_REPORT_NOTE,
			},
			"divergences": DIVERGENCES,
			"volatile_fields": [VOLATILE_PRIVATE_PREFIX + addressed.stamp_key,
				VOLATILE_SERVER_TIME_FIELD],
		},
		"resources": post.get("resources", {}),
		"changed": post.get("changed", []),
	}

# ---------------------------------------------------------------------------
# the typed wire parser
# ---------------------------------------------------------------------------


## Parse one reward answer into a typed `RewardResult`.
##
## ## The parser RE-DERIVES; it does not believe
##
## Every number the answer reports is recomputed from recorded state and
## committed content before it is accepted, and a disagreement is a **refusal**,
## not a re-labelled acceptance:
##
##   * the successor is recomputed from the reported before value and the
##     reported bound, and the reported after value and change must both agree;
##   * each cursor's reachability sets are recomputed from the reported bound and
##     cardinality, in BOTH directions;
##   * each reported `exceeds_cardinality_by` is recomputed from the reported
##     bound and cardinality;
##   * the derived argument list is recomputed from the action and the reported
##     before value;
##   * the volatile-field list is recomputed from the answered action;
##   * the granted item is re-checked as **zero**, which is the whole mechanism
##     by which the daily branch's grant arm is never selected;
##   * every schedule entry and every type letter must report itself undecoded
##     and unmapped.
##
## ## Where the two layers' encodings legitimately differ
##
## Four fields differ in **encoding** between the offline answer and the live
## one, and the parser accepts both spellings while still refusing a value:
##
##   * `bound_rejected_alternative` -- the service sends a prose string where
##     this module sends its own record object;
##   * `mapped_to_resource` -- the service sends `null`, this module sends `""`;
##   * a schedule row's `type` -- `null` where the entry has no letter, `""`
##     here;
##   * `value_shape` for a **number** -- `int` or `float` on the service side and
##     `number` here, because the pinned engine decodes every JSON number as a
##     float and this module cannot tell an integer from a real number.
##
## Each of those is an encoding, not a claim, so accepting both is not a weakened
## check: every one of them is refused the moment it carries a **value** that
## would imply a grant, a mapping, or a decoded letter.
##
## ## The one field the parser deliberately does NOT compare
##
## A census row's `consumed_for` is **prose**, and the two layers spell its
## absence differently -- the service sends `null`, this module sends `""`. It is
## therefore not compared at all, in either direction: comparing prose would make
## a rewording on one side a wire fault, which is the opposite of what a
## comparison is for. Everything a census row asserts that is **checkable** --
## its `name` and its `consumers` -- is re-derived above, so the row is still
## load-bearing; only the description is left alone.
static func parse_reward(payload: Variant) -> RewardResult:
	if not (payload is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _reward_error(envelope)
	if str(envelope.get("protocol", "")) != BootData.PROTOCOL:
		return reward_failure("protocol_mismatch",
			"expected protocol " + BootData.PROTOCOL + ", got "
				+ str(envelope.get("protocol")))
	if str(envelope.get("result", "")) != "success":
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response did not report the legacy success result")
	# The whole projection is nested. A flat answer is a different contract, and
	# accepting one would hide exactly the drift this parser exists to catch.
	var reward: Variant = envelope.get("reward")
	if not (reward is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no reward object; this contract nests "
				+ "the whole projection under one 'reward' key")
	var body: Dictionary = reward
	if not is_action(body.get("action")):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response names no delivered action")
	var action := str(body.get("action"))
	if str(body.get("command", "")) != str(ACTION_COMMAND[action]):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response reports a command the action does not dispatch")
	if not ACTION_ADDRESSING_KEY.is_empty():
		return reward_failure(REASON_BAD_RESPONSE,
			"this contract records an empty addressing table; an answer naming "
				+ "one contradicts it")

	var result := RewardResult.new()
	result.ok = true
	result.action = action
	result.command = str(body.get("command", ""))
	result.protocol = str(envelope.get("protocol", ""))
	result.result = str(envelope.get("result", ""))
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _wire_int(envelope.get("server_time"))

	# --- the cursor object, and the transition it claims ---------------------
	var cursor: Variant = body.get("cursor")
	if not (cursor is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no cursor object")
	var cursor_body: Dictionary = cursor
	if str(cursor_body.get("key", "")) != str(ACTION_CURSOR_KEY[action]):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response addresses " + str(cursor_body.get("key", ""))
				+ ", not the action's own cursor")
	var before := _wire_int(cursor_body.get("before"))
	if before < 0:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no readable recorded before value")
	var bound := _wire_int(body.get("bound"))
	if bound <= 0:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response reports a bound of " + str(bound))
	var stepped := weekly_successor(before, bound) if action == ACTION_WEEKLY \
		else daily_successor(before)
	if not bool(stepped["ok"]):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response reports a before value this client refuses: "
				+ str(stepped["error"]))
	var derived_after: int = int(stepped["value"])
	var derived_change: int = derived_after - before
	var cursor_after := _wire_int(cursor_body.get("after"))
	if cursor_after != derived_after:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's cursor moved to " + str(cursor_after)
				+ ", not the " + str(derived_after) + " this client re-derives "
				+ "from the recorded " + str(before))
	if _wire_int(cursor_body.get("change")) != derived_change:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's change disagrees with its own after value")

	# --- the bound: a derived weekly length, or a transcribed daily literal --
	# `bound_is_literal` is not on the wire and is not invented here: it is
	# re-derived from the action, so a caller cannot be told a weekly bound is a
	# literal or a daily one is derived by anything but the action's own name.
	result.bound_is_literal = action == ACTION_DAILY
	if str(body.get("bound_source", "")) != (
			DAILY_BOUND_SOURCE if action == ACTION_DAILY
				else WEEKLY_BOUND_SOURCE):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's bound_source does not name the recorded "
				+ "source for this action's bound")
	if action == ACTION_DAILY and bound != DAILY_BOUND_LITERAL:
		return reward_failure(REASON_BAD_RESPONSE,
			"the daily bound is the recorded literal "
				+ str(DAILY_BOUND_LITERAL) + ", not " + str(bound))
	var rejected: Variant = body.get("bound_rejected_alternative")
	if action == ACTION_WEEKLY and not _is_encoded_absence(rejected):
		return reward_failure(REASON_BAD_RESPONSE,
			"the weekly bound is derived from " + WEEKLY_SCHEDULE_KEY
				+ ", so there is no rejected alternative to report for it")
	if action == ACTION_DAILY and not _is_encoded_presence(rejected):
		return reward_failure(REASON_BAD_RESPONSE,
			"the daily answer omits the rejected content-derivation of its "
				+ "literal bound, so a later reader could not tell the "
				+ "derivation was never chosen")
	result.bound_rejected_alternative = rejected

	# --- the instant: stamped, volatile, never compared by value ------------
	var instant: Variant = body.get("instant")
	if not (instant is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no instant object")
	var stamp_body: Dictionary = instant
	if str(stamp_body.get("key", "")) != str(ACTION_STAMP_KEY[action]):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response stamps "
				+ str(stamp_body.get("key", "")) + ", not the action's own "
				+ "instant")
	if stamp_body.get("stamped") != true:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not report the instant as stamped, and "
				+ "both preserved branches write it unconditionally")
	if stamp_body.get("volatile") != true:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not report the stamped instant as "
				+ "volatile, though it is a wall clock")

	# --- the derived argument list, re-derived ------------------------------
	# The weekly list is EMPTY and that emptiness is the mechanism: the preserved
	# branch picks its arm on `len(args) > 4`, so zero arguments is what selects
	# the non-granting arm. The daily list carries the item at ZERO and the
	# recorded cursor; a positive item would take the branch's granting arm, which
	# places a row and creates a storage entry.
	var derived_args: Variant = body.get("derived_args")
	if not (derived_args is Array):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no derived argument list")
	var got_args: Array = (derived_args as Array).duplicate()
	var want_args: Array = [] if action == ACTION_WEEKLY \
		else [DERIVED_DAILY_ITEM, before]
	for index in range(got_args.size()):
		got_args[index] = _wire_int(got_args[index])
	if got_args != want_args:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's derived arguments are " + str(got_args)
				+ ", not the " + str(want_args) + " that grant nothing")

	# --- the reachability, recomputed rather than believed -------------------
	var reports: Variant = body.get("reachability")
	if not (reports is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no reachability object")
	for action_name: String in ACTIONS:
		var row: Variant = (reports as Dictionary).get(action_name)
		if not (row is Dictionary):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reachability report omits " + action_name)
		var row_body: Dictionary = row
		var row_bound := _wire_int(row_body.get("bound"))
		var row_cardinality := _wire_int(row_body.get("cardinality"))
		if row_bound <= 0 or row_cardinality < 0:
			return reward_failure(REASON_BAD_RESPONSE,
				"the " + action_name + " reachability report carries no readable "
					+ "bound and cardinality")
		var recomputed := reachable_report(row_bound, row_cardinality,
			ACTION_REACHABLE[action_name] as Array)
		if _wire_int(row_body.get("index_base")) != int(recomputed["index_base"]):
			return reward_failure(REASON_BAD_RESPONSE,
				"the " + action_name + " report's index base disagrees with the "
					+ "recorded zero-based reading")
		if row_body.get("selection_performed") != false:
			return reward_failure(REASON_BAD_RESPONSE,
				"the " + action_name + " report claims it selected a schedule "
					+ "entry, which this contract never does")
		for field: String in ["reachable", "answerable",
				"reachable_not_answerable", "answerable_not_reachable"]:
			var reported: Variant = row_body.get(field)
			if not (reported is Array):
				return reward_failure(REASON_BAD_RESPONSE,
					"the " + action_name + " report carries no " + field + " set")
			var got: Array = []
			for value: Variant in reported as Array:
				got.append(_wire_int(value))
			got.sort()
			var wanted: Array = (recomputed[field] as Array).duplicate()
			wanted.sort()
			if got != wanted:
				return reward_failure(REASON_BAD_RESPONSE,
					"the " + action_name + " report's " + field + " is "
						+ str(got) + ", not the " + str(wanted)
						+ " this client recomputes from the reported bound and "
						+ "cardinality")
		result.bounds = body.get("bounds", {})
	# The addressed cursor's own report is the one copied onto the typed result.
	var addressed_report: Dictionary = (reports as Dictionary)[action]
	var cardinality := _wire_int(addressed_report.get("cardinality"))
	result.schedule_cardinality = cardinality
	result.index_base = _wire_int(addressed_report.get("index_base"))
	# The four sets are read through `_wire_int` rather than copied verbatim, for
	# the same reason the resource values are: the engine decodes every JSON
	# number as a float, so a verbatim copy answers `[3.0, 4.0]` where the
	# committed positions are `[3, 4]`. The re-derivation above already proved
	# each set equals the recomputed one, so these are the recomputed VALUES --
	# the assertion is not weakened by projecting the recomputation.
	result.reachable = _wire_int_set(addressed_report.get("reachable", []))
	result.answerable = _wire_int_set(addressed_report.get("answerable", []))
	result.reachable_not_answerable = _wire_int_set(
		addressed_report.get("reachable_not_answerable", []))
	result.answerable_not_reachable = _wire_int_set(
		addressed_report.get("answerable_not_reachable", []))
	result.reachability = (reports as Dictionary).duplicate(true)
	result.selection_performed = false

	# --- the bounds block, whose two exceedances are recomputed -------------
	var bounds_block: Variant = body.get("bounds")
	if not (bounds_block is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no bounds block")
	for action_name: String in ACTIONS:
		var row: Variant = (bounds_block as Dictionary).get(action_name)
		if not (row is Dictionary):
			return reward_failure(REASON_BAD_RESPONSE,
				"the bounds block omits " + action_name)
		var row_body: Dictionary = row
		var row_bound := _wire_int(row_body.get("bound"))
		var row_cardinality := _wire_int(row_body.get("cardinality"))
		if str(row_body.get("schedule", "")) != str(ACTION_SCHEDULE_KEY[action_name]):
			return reward_failure(REASON_BAD_RESPONSE,
				"the " + action_name + " bound names "
					+ str(row_body.get("schedule", "")) + " as its schedule, not "
					+ str(ACTION_SCHEDULE_KEY[action_name]))
		if _wire_int(row_body.get("exceeds_cardinality_by")) \
				!= row_bound - row_cardinality:
			return reward_failure(REASON_BAD_RESPONSE,
				"the " + action_name + " bound's reported exceedance disagrees "
					+ "with its own bound and cardinality")

	# --- the schedules, verbatim and undecoded -------------------------------
	var schedule_entries: Variant = body.get("schedule_entries")
	if not (schedule_entries is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no schedule entries object")
	for key: String in ACTION_SCHEDULE_KEY.values():
		if not (schedule_entries as Dictionary).has(key):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response omits the committed " + str(key))
		var rows: Variant = (schedule_entries as Dictionary)[key]
		if not (rows is Array):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response's " + str(key) + " rows are not an array")
		for position in range((rows as Array).size()):
			var row: Variant = (rows as Array)[position]
			if not (row is Dictionary):
				return reward_failure(REASON_BAD_RESPONSE,
					"a " + str(key) + " row is not an object")
			var entry_body: Dictionary = row
			if _wire_int(entry_body.get("position")) != position:
				return reward_failure(REASON_BAD_RESPONSE,
					"a " + str(key) + " row reports position "
						+ str(_wire_int(entry_body.get("position")))
						+ ", not its own index " + str(position)
						+ "; the committed order is part of the verbatim claim")
			if entry_body.get("decoded") != false:
				return reward_failure(REASON_BAD_RESPONSE,
					"the reward response reports a decoded schedule entry, "
						+ "which this contract never produces")
			if not _is_encoded_absence(entry_body.get("mapped_to_resource")):
				return reward_failure(REASON_BAD_RESPONSE,
					"the reward response maps a schedule entry onto a stored "
						+ "resource, which this contract never does")
			var shape := str(entry_body.get("value_shape", ""))
			if shape != "list" and not NUMBER_SHAPE_NAMES.has(shape):
				return reward_failure(REASON_BAD_RESPONSE,
					"the reward response reports an unreadable value shape "
						+ shape + " for a " + str(key) + " entry")
	if not (schedule_entries as Dictionary)[str(ACTION_SCHEDULE_KEY[action])] \
			is Array:
		return reward_failure(REASON_BAD_RESPONSE,
			"the addressed schedule's rows are not an array")
	var addressed_rows: Array = (schedule_entries as Dictionary)[
		str(ACTION_SCHEDULE_KEY[action])] as Array
	if addressed_rows.size() != cardinality:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response reports " + str(addressed_rows.size())
				+ " rows for the addressed schedule against its own reported "
				+ "cardinality of " + str(cardinality))

	# --- the schedule census, names and consumer counts ----------------------
	var schedules: Variant = body.get("schedules")
	if not (schedules is Array) or (schedules as Array).size() != SCHEDULE_COUNT:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not report all " + str(SCHEDULE_COUNT)
				+ " reward schedules with their consumer counts")
	# The recorded name list is built from `SCHEDULES` rather than transcribed a
	# second time: two lists of eleven names could disagree, and a disagreement
	# between them would be a report about the module instead of about the wire.
	var wanted_names: Array = []
	var wanted_zero: Array = []
	for recorded: Dictionary in SCHEDULES:
		wanted_names.append(str(recorded["name"]))
		if int(recorded["consumers"]) == 0:
			wanted_zero.append(str(recorded["name"]))
	var reported_names: Array = []
	var reported_zero: Array = []
	for row: Variant in schedules as Array:
		if not (row is Dictionary):
			return reward_failure(REASON_BAD_RESPONSE,
				"a reward-schedule census row is not an object")
		var row_body: Dictionary = row
		var name_value := str(row_body.get("name", ""))
		if not wanted_names.has(name_value):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response names a schedule outside the recorded "
					+ "census: " + name_value)
		var consumers := _wire_int(row_body.get("consumers"))
		if consumers < 0:
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response reports a negative consumer count for "
					+ name_value)
		reported_names.append(name_value)
		if consumers == 0:
			reported_zero.append(name_value)
	reported_names.sort()
	reported_zero.sort()
	wanted_names.sort()
	wanted_zero.sort()
	if reported_names != wanted_names:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's schedule census names " + str(reported_names)
				+ ", not the recorded " + str(wanted_names))
	if reported_zero != wanted_zero:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's zero-consumer set is " + str(reported_zero)
				+ ", not the recorded " + str(wanted_zero))

	# --- the letters, undecoded, beside their recorded search result ----------
	var letters: Variant = body.get("type_letters")
	if not (letters is Array) or (letters as Array).size() != TYPE_LETTER_COUNT:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not report all " + str(TYPE_LETTER_COUNT)
				+ " type letters")
	var seen: Array = []
	for row: Variant in letters as Array:
		if not (row is Dictionary):
			return reward_failure(REASON_BAD_RESPONSE,
				"a type letter row is not an object")
		var letter_body: Dictionary = row
		var letter := str(letter_body.get("letter", ""))
		if not TYPE_LETTERS.has(letter):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response names a type letter outside the committed "
					+ "vocabulary: " + letter)
		if letter_body.get("decoded") != false:
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response reports a decoded type letter, which "
					+ "this contract never produces")
		if not _is_encoded_absence(letter_body.get("mapped_to_resource")):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response maps a type letter onto a stored resource")
		if _wire_int(letter_body.get("decoder_search_hits")) \
				!= DECODER_SEARCH_HIT_TOTAL:
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response's decoder-search result disagrees with the "
					+ "recorded " + str(DECODER_SEARCH_COUNT) + " searches")
		seen.append(letter)
	# Both sides are sorted before the comparison, and the module's own
	# `TYPE_LETTERS` array is left in **committed order**. Comparing a sorted
	# answer against an unsorted committed list would report a vocabulary
	# disagreement that does not exist -- and the kind that gets "fixed" by
	# editing the committed order, which is how a transcription error becomes
	# indistinguishable from a requirement.
	var committed_letters: Array = TYPE_LETTERS.duplicate()
	committed_letters.sort()
	seen.sort()
	if seen != committed_letters:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response reports the letters " + str(seen) + ", not the "
				+ "committed vocabulary " + str(committed_letters))

	# --- the arms and the divergences, reported and never reproduced --------
	var arms: Variant = body.get("arms")
	if not (arms is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no arms block")
	for action_name: String in ACTIONS:
		var arm_rows: Variant = (arms as Dictionary).get(action_name)
		if not (arm_rows is Array) \
				or (arm_rows as Array).size() != ARM_COUNT_PER_ACTION:
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response does not report both of the "
					+ action_name + " branch's arms")
		for row: Variant in arm_rows as Array:
			if not (row is Dictionary):
				return reward_failure(REASON_BAD_RESPONSE,
					"an " + action_name + " arm row is not an object")
			if (row as Dictionary).get("reproduced") != false:
				return reward_failure(REASON_BAD_RESPONSE,
					"the reward response claims it reproduced a preserved arm, "
						+ "which it must never do: both arms are selected by a "
						+ "client-sent value")
	var divergences: Variant = body.get("divergences")
	if not (divergences is Array) \
			or (divergences as Array).size() != DIVERGENCE_COUNT:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not report all " + str(DIVERGENCE_COUNT)
				+ " recorded divergences")
	for row: Variant in divergences as Array:
		if not (row is Dictionary):
			return reward_failure(REASON_BAD_RESPONSE,
				"a divergence row is not an object")
		if (row as Dictionary).get("reproduced") != false:
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response reports a divergence as reproduced, which "
					+ "would be a parity claim it cannot make")

	# --- the four-part grant proof, as four assertable keys ------------------
	var block: Variant = body.get("grant")
	if not (block is Dictionary):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no grant block")
	var proof_body: Dictionary = block
	if proof_body.get("grants_nothing") != true:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not carry the structural grant refusal")
	for wire_key: String in REFUSAL_PROOF_WIRE_KEYS:
		if not _is_encoded_presence(proof_body.get(wire_key)):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response omits the grant-proof part " + wire_key)
	var allowed: Variant = proof_body.get("allowed_leaf_paths")
	if not (allowed is Array) or (allowed as Array).size() \
			!= ALLOWED_LEAF_PATH_COUNT:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response does not carry exactly "
				+ str(ALLOWED_LEAF_PATH_COUNT) + " allowed leaf paths, which is "
				+ "what makes the four-part proof a containment check")
	var wanted_allowed: Array = ALLOWED_LEAF_PATHS[action]
	var got_allowed: Array = []
	for value: Variant in allowed as Array:
		got_allowed.append(str(value))
	if got_allowed != wanted_allowed:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's allowed leaf paths are " + str(got_allowed)
				+ ", not this action's own " + str(wanted_allowed))

	# --- the volatile fields, re-derived from the answered action ------------
	var volatile: Variant = body.get("volatile_fields")
	var wanted_volatile: Array = [VOLATILE_PRIVATE_PREFIX
		+ str(ACTION_STAMP_KEY[action]), VOLATILE_SERVER_TIME_FIELD]
	var got_volatile: Array = []
	if volatile is Array:
		for value: Variant in volatile as Array:
			got_volatile.append(str(value))
	if got_volatile != wanted_volatile:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response's volatile fields are " + str(got_volatile)
				+ ", not the " + str(wanted_volatile) + " this client re-derives "
				+ "for " + action)

	# --- the post-execution proof halves ------------------------------------
	# The COMPLETE stored resource set, compared as a set and by value. A subset
	# comparison would let a slot this contract never read pass as unchanged.
	var resources: Variant = envelope.get("resources")
	if not (resources is Dictionary) or (resources as Dictionary).is_empty():
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no stored resource set, so the "
				+ "no-resource-moved half of the proof cannot be read")
	var resource_names: Array = []
	for key: String in (resources as Dictionary):
		resource_names.append(key)
	resource_names.sort()
	var wanted_resources: Array = RESOURCE_NAMES.duplicate()
	wanted_resources.sort()
	if resource_names != wanted_resources:
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response exposes the stored resources "
				+ str(resource_names) + ", not the complete recorded set "
				+ str(wanted_resources) + "; a subset comparison would let an "
				+ "unread slot pass as unchanged")
	# Every stored resource is a whole number in every committed save, and the
	# pinned engine decodes all JSON numbers as floats. The values are therefore
	# read through `_wire_int` exactly as every other integer on this wire is,
	# so a caller comparing against a save read the same way sees equal values.
	# A value that is NOT integer-valued is refused rather than truncated: a
	# truncated resource would compare equal to a whole number that was never
	# stored, which is the "no resource moved" proof passing for the wrong
	# reason. This was found by the live phase, which compared a float-valued
	# answer against an int-valued save and reported a difference that was not
	# one.
	var whole_resources: Dictionary = {}
	for name: String in resource_names:
		var value: Variant = (resources as Dictionary)[name]
		if not _is_integer_valued(value):
			return reward_failure(REASON_BAD_RESPONSE,
				"the reward response's stored resource " + name + " is "
					+ str(value) + ", which is not a whole number; every "
					+ "committed save stores these as integers")
		whole_resources[name] = _wire_int(value)
	var changed: Variant = envelope.get("changed")
	if not (changed is Array):
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response carries no changed-pointer list")
	var changed_paths: Array = []
	for value: Variant in changed as Array:
		changed_paths.append(str(value))
	var outside: Array = []
	for path: String in changed_paths:
		if not wanted_allowed.has(path):
			outside.append(path)
	if not outside.is_empty():
		return reward_failure(REASON_BAD_RESPONSE,
			"the reward response changed " + str(outside)
				+ ", which is outside the two paths it may change ("
				+ str(wanted_allowed) + "); a reward operation places nothing, "
				+ "appends nothing, creates nothing, and moves no stored resource")

	result.cursor_key = str(cursor_body.get("key", ""))
	result.cursor_before = before
	result.cursor_after = cursor_after
	result.cursor_change = cursor_after - before
	result.derived_after = derived_after
	result.derived_change = derived_change
	result.bound = bound
	result.bound_source = str(body.get("bound_source", ""))
	result.schedule_key = str(ACTION_SCHEDULE_KEY[action])
	result.stamp_key = str(stamp_body.get("key", ""))
	result.stamp_before = _wire_int(stamp_body.get("value_before"))
	result.stamp_stamped = true
	result.stamp_volatile = true
	result.derived_args = got_args
	result.bounds = bounds_block
	result.schedules = schedules
	result.schedule_entries = (schedule_entries as Dictionary).duplicate(true)
	result.type_letters = letters
	result.arms = arms
	result.divergences = divergences
	result.refusal_evidence = proof_body
	result.allowed_leaf_paths = got_allowed
	result.volatile_fields = got_volatile
	result.resources = whole_resources
	result.resource_count = whole_resources.size()
	result.changed = changed_paths
	# The four module records are NOT answer fields. They describe the contract
	# rather than a transaction, so they are copied from this module's own
	# constants instead of read off the wire -- which is what keeps "the service
	# asserted this" distinct from "this client records this".
	result.save_only_fields = SAVE_ONLY_FIELDS.duplicate()
	result.refusals = VALIDATION_ORDER.duplicate()
	result.validation_order = VALIDATION_ORDER.duplicate()
	result.derivation_record = DERIVATION_RECORD
	return result


## The service's own structured refusal (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
static func _reward_error(envelope: Dictionary) -> RewardResult:
	var code := REASON_BAD_RESPONSE
	var message := "compatibility API reported an error"
	var error: Variant = envelope.get("error")
	if error is Dictionary and not (error as Dictionary).is_empty():
		code = str((error as Dictionary).get("code", code))
		message = str((error as Dictionary).get("message", message))
	return reward_failure(code, message)


## Whether `value` is an exact integer for this contract's recorded vocabulary.
##
## The pinned engine decodes every JSON number as a **float**, so an integer-
## valued float is accepted and an integer-typed value is accepted; a numeric
## **string** is refused, because no committed source stores one for these keys.
static func _is_integer_valued(value: Variant) -> bool:
	if value is bool:
		return false
	if value is int:
		return true
	if value is float:
		return is_finite(value) and value == floor(value) \
			and absf(value) <= 9007199254740992.0
	return false


## A wire list of positions, read through `_wire_int` and kept in its recorded
## order. Order is preserved rather than sorted here: the reachability sets are
## reported ascending by both this module and the service, and the earlier
## re-derivation compares them **sorted**, so projecting them unsorted keeps a
## reordered wire from reading as a different set in the typed result while the
## set comparison itself stays order-independent.
static func _wire_int_set(value: Variant) -> Array:
	var out: Array = []
	if not (value is Array):
		return out
	for element: Variant in value as Array:
		out.append(_wire_int(element))
	return out


## The engine's JSON numbers, read as integers. A missing value reads as -1,
## which no recorded cursor, bound, or cardinality can be.
static func _wire_int(value: Variant) -> int:
	if value is bool:
		return -1
	if value is int:
		return int(value)
	if value is float and is_finite(value) and value == floor(value):
		return int(value)
	return -1


## Whether `value` is this contract's **absence** encoding for a field that must
## carry no value.
##
## The two layers spell absence differently -- the service sends `null` and this
## module sends `""` -- so both are accepted, and the check that matters is the
## one on the other side: a field carrying either spelling of a **value** is
## refused. Accepting two spellings of "nothing" is not a weakened check; it is
## the only way two layers can say the same true thing.
static func _is_encoded_absence(value: Variant) -> bool:
	if value == null:
		return true
	return value is String and str(value) == ""


## Whether `value` is this contract's **presence** encoding: something present
## that carries a value, in either layer's spelling.
static func _is_encoded_presence(value: Variant) -> bool:
	if value == null:
		return false
	if value is String:
		return str(value) != ""
	if value is Array:
		return not (value as Array).is_empty()
	if value is Dictionary:
		return not (value as Dictionary).is_empty()
	return true


## A name for a committed value's shape, for the verbatim schedule rows. It
## describes the **encoding**, never a meaning.
##
## The names are the service half's own (`rewards_envelope.py`'s
## `type(value).__name__`, with the one deliberate divergence spelled out below),
## because two layers that disagree about what to call a shape make the wire
## field unreadable. Two of them cannot match by construction and are recorded
## rather than forced:
##
##   * `"list"` matches -- both layers call an array a list.
##   * `"object"` / `"string"` / `"boolean"` / `"null"` are the same words.
##   * a **number** is `int` or `float` on the service side and `number` here,
##     because the pinned engine decodes every JSON number as a float, so this
##     module cannot tell an integer from a real number. The parser therefore
##     requires a number's shape to be one of the three names and never treats
##     the difference as a disagreement.
static func _kind_name(value: Variant) -> String:
	if value is Array:
		return "list"
	if value is Dictionary:
		return "object"
	if value is String:
		return "string"
	if value is bool:
		return "boolean"
	if value is int or value is float:
		return "number"
	if value == null:
		return "null"
	return "unknown"


## The shape names a committed **number** may be reported under, across both
## layers. Three, and the parser accepts any of them: `int` and `float` are the
## service half's, `number` is this module's, and which one appears depends on
## whether the value crossed a JSON boundary.
const NUMBER_SHAPE_NAMES := ["int", "float", "number"]


## Whether a committed value is a recorded zero. `false` is not a zero: the two
## differ in JSON and in every consumer of these schedules.
static func _is_recorded_zero(value: Variant) -> bool:
	if value is bool:
		return false
	if value is int:
		return int(value) == 0
	if value is float:
		return is_finite(value) and float(value) == 0.0
	return false

# ---------------------------------------------------------------------------
# the ownership record and the claim limits
# ---------------------------------------------------------------------------


## The fields this capability projects, and the fields owned elsewhere.
##
## Returned as a derived table rather than a constant so a caller cannot read a
## claim that the module's own constants do not support.
static func owners() -> Array:
	var rows: Array = []
	for key: String in CURSORS:
		rows.append({"field": key, "owned_by": "godot-rewards",
			"kind": "cursor"})
	for key: String in INSTANTS:
		rows.append({"field": key, "owned_by": "godot-rewards",
			"kind": "stamped instant"})
	rows.append({"field": PRIVATE_STATE_KEY, "owned_by": "godot-rewards",
		"kind": "the one object both branches write into"})
	for key: String in FOREIGN_IDENTIFIERS:
		rows.append({"field": key,
			"owned_by": "another capability",
			"named_here_only_as": "a string in FOREIGN_IDENTIFIERS",
			"asserted_by": FOREIGN_IDENTIFIERS[key],
			"role": str(FOREIGN_IDENTIFIER_ROLES.get(key, ""))})
	rows.append({"field": RANKING_REWARD_TABLE,
		"owned_by": "economy-schedules-normalization and content-validation, "
			+ "as normalized content only",
		"named_here_only_as": "a string in RANKING_REWARD_OWNERSHIP"})
	return rows


static func coverage_limit() -> Dictionary:
	return COVERAGE_LIMIT


static func non_claims() -> Array:
	return NON_CLAIMS
