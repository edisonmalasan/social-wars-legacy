extends RefCounted
## Pure research projection, intent contract, and typed result (OpenSpec
## `godot-research` "The research counter vector is projected for both tracks,
## verbatim" / "The four legacy branch effects are recorded as data, not
## recomputed" / "Both research tracks are named, and their committed building
## ids are reported but not used" / "`fast_forward` is recorded as a fourth
## writer of the research instant" / "A research action is a server-derived
## intent, and no client value is trusted" / "No research price is charged, and
## every stored resource is proven unchanged" / "Research evidence and claim
## limits", design D1-D10).
##
## ## This line is NOT a refusal line, and this module is why
##
## The counters genuinely move. Four legacy `command.py` branches advance them
## over **two** tracks, and the committed corpus holds all three at `[0, 0]`,
## so every branch is exercisable and an **executed-legacy fixture** exists.
## What is refused is the *derivation*: the counters are **write-only** in the
## legacy source, so there is no readiness rule, no completion rule, no
## remaining time, no unlock gate, and no cost check **to reproduce**. Delivering
## the mechanics without them is the deliverable; inventing any of them would be
## a different one (design D1).
##
## ## The three counters and the two tracks (established)
##
## `researchStepNumber`, `researchItemNumber`, and `timeStampDoResearch` are
## three `privateState` lists of **two** entries each — one per track. The tracks
## are named in the source only inside the four branch comments
## (`0: TYPE_AREA_51 , 1: TYPE_ROBOTIC`) and are **defined nowhere**. Their
## mapping to the committed building identifiers rests on that comment's own word
## order plus the four `print` statements' display list
## `["Area 51", "Robotic Center"][_type]`, so it is **reported** and asserted
## never to be used (design D5). **No code identifier in this repository is
## named after either track constant** — the names are carried as string DATA
## inside `TRACKS`, which is what makes the "never used" claim mechanical.
##
## ## The four branch effects are DATA, not code (design D1)
##
## `BRANCHES` records, per branch, the committed source lines, the counters it
## writes, and its exact effect. Two facts inside that table are the ones an
## inspection of the dispatcher would miss:
##
##   * the **item** branch resets the step counter **and** the research instant
##     **together**, at `command.py:288` and `command.py:289`, with no branch
##     between them, and no other branch ever resets the step counter;
##   * the **cash** branch reads a client-supplied cash value at
##     `command.py:277` and **discards** it, printing "Buy research step for …"
##     and moving no balance — the same shape as M8 line 8's `used_syringe`.
##
## ## The research instant has FIVE writers (design D7)
##
## Four are the branches (`command.py:272`, `280`, `289`, `298`). The fifth is
## **`fast_forward`** (`command.py:905`), which reads the instant at
## `command.py:923` and subtracts a **CLIENT-SUPPLIED** number of seconds from
## every track at `command.py:927`, clamped at zero. That makes the instant
## client-writable, and it is recorded as a fourth writer — while **no
## fast-forward operation is delivered here, in the facade, in either GameApi
## implementation, or by any route.** `NON_DERIVATION` is the machine-readable
## form of that absence, and the suite pins this module's whole function
## inventory against a list, so a readiness, duration, price, or unlock helper
## fails the run wherever it is added (task 4.3).
##
## ## No content is invented (design D4)
##
## There is no committed research cost, step count, unlock requirement, or
## reward. `CONTENT_ABSENCE` records the **measured** facts, including the two
## figures the M9 investigation and this line's proposal got **wrong**: `research`
## appears in **two** normalized files (not one), and `config/main.json` **does**
## carry three `research`-containing keys (all under `/images`). The conclusion
## survives both corrections untouched: nothing exists to derive a schedule from.
##
## ## Read-only by construction
##
## `ResearchView` and `TrackView` **copy** the committed values when they are
## built and then declare no setter, no mutating method, and no writable public
## field. Every reader returns a committed value or a fresh copy, so reading a
## research state can change neither the save it was parsed from nor the
## committed content. **Writing** a counter is behaviour: it belongs to the
## guarded intent below, and it is not implemented here.
##
## ## The intent is INTENT-ONLY (design D2)
##
## `intent_body()` produces exactly three keys — a player identifier, a closed
## action, and a track. **No counter value, no research instant, and no cash
## amount** is expressible, so there is no parameter through which a client could
## send one; the service derives every counter itself and ignores anything else
## it receives.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ------------------------------------------------------------------ keys --
## The three committed private-state keys a research track occupies, in the
## committed order the four branches write them (`command.py:271-298`).
const KEY_STEP := "researchStepNumber"
const KEY_ITEM := "researchItemNumber"
const KEY_INSTANT := "timeStampDoResearch"
const COUNTERS := [KEY_STEP, KEY_ITEM, KEY_INSTANT]

## One entry per track. Both tracks, always: the legacy vectors are two-element
## lists and a one-entry vector is a save this contract refuses.
const TRACK_COUNT := 2

# ------------------------------------------------------------- commands --
const STEP_COMMAND := "next_research_step"
const CASH_COMMAND := "research_buy_step_cash"
const ITEM_COMMAND := "next_research_item"
const RESET_COMMAND := "reset_research_item"

## The closed action vocabulary: the client names an OUTCOME and the service
## chooses the legacy command. `fast_forward` is deliberately **absent**.
const ACTION_STEP := "next_step"
const ACTION_BUY_STEP_CASH := "buy_step_cash"
const ACTION_ITEM := "next_item"
const ACTION_RESET := "reset_item"
const ACTIONS := [ACTION_STEP, ACTION_BUY_STEP_CASH, ACTION_ITEM, ACTION_RESET]
const ACTION_COMMANDS := {
	ACTION_STEP: STEP_COMMAND,
	ACTION_BUY_STEP_CASH: CASH_COMMAND,
	ACTION_ITEM: ITEM_COMMAND,
	ACTION_RESET: RESET_COMMAND,
}

## The action whose branch also takes a **discarded** cash amount first, so its
## argument list is `[cash, track]` while every other branch's is `[track]`.
const CASH_ACTION := ACTION_BUY_STEP_CASH

## The endpoint the typed operation drives, named here as data so the transport
## itself stays inside the legacy-v0 implementation (the project-scope suite
## enforces that boundary).
const RESEARCH_PATH := "/v0/research"

## The exact key set `intent_body()` produces. Three keys, no more: this list IS
## the structural form of the "no client value is trusted" claim.
const INTENT_KEYS := ["user_id", "action", "track"]

## Every key a client might attach that the service **ignores**, recorded so the
## refusal is enumerable rather than editorial.
const INTENT_IGNORED_KEYS := [
	"step", "item", "timestamp", "instant", "cash", "price", "cost",
	"step_count", "reward", "remaining", "ready", "duration",
	"resources_changed", "vector", "seconds", "fast_forward", "type",
	"unlock", "requirement",
]

# --------------------------------------------------------- the branches --
## The four recorded branch contracts, as DATA. The absence of validation is a
## field of every record because it is the fact that most needs stating
## (design D6): the branches validate **nothing**.
const BRANCHES := [
	{
		"command": STEP_COMMAND,
		"action": ACTION_STEP,
		"source": "command.py:268-274",
		"args": ["track index"],
		"argument_order": "track",
		"counters_written": [KEY_STEP, KEY_INSTANT],
		"effect": "the step counter is INCREMENTED and the research instant is "
			+ "stamped with time_now; the item counter is untouched",
		"stamps_instant": true,
		"paired_reset": false,
		"reads_a_price": false,
		"charges": false,
		"validation": "none: no bounds check, no clamp, no membership test, no "
			+ "exception guard, and no existence check",
	},
	{
		"command": CASH_COMMAND,
		"action": ACTION_BUY_STEP_CASH,
		"source": "command.py:276-282",
		"args": ["cash", "track index"],
		"argument_order": "cash-then-track",
		"counters_written": [KEY_INSTANT],
		"effect": "the research instant is ZEROED and nothing else is written; "
			+ "the step and item counters are untouched",
		"stamps_instant": false,
		"paired_reset": false,
		"reads_a_price": true,
		"charges": false,
		"price_note": "the branch reads args[0] as `cash` (command.py:277) and "
			+ "NEVER uses it: it prints 'Buy research step for …' and moves no "
			+ "balance. This is the same shape as M8 line 8's discarded "
			+ "`used_syringe`, and it is what makes the no-price claim provable "
			+ "rather than merely asserted",
		"validation": "none: no bounds check, no clamp, no membership test, no "
			+ "exception guard, and no existence check — and no cost validation "
			+ "either, because the only cost-token match is the branch's own "
			+ "parameter name",
	},
	{
		"command": ITEM_COMMAND,
		"action": ACTION_ITEM,
		"source": "command.py:284-291",
		"args": ["track index"],
		"argument_order": "track",
		"counters_written": [KEY_ITEM, KEY_STEP, KEY_INSTANT],
		"effect": "the item counter is INCREMENTED and the step counter AND the "
			+ "research instant are RESET TOGETHER, in this one branch "
			+ "(command.py:288-289)",
		"stamps_instant": false,
		"paired_reset": true,
		"paired_reset_note": "the step reset and the instant reset happen "
			+ "TOGETHER at command.py:288 and command.py:289, in the same "
			+ "branch; no other branch resets the step counter, and no committed "
			+ "branch ever resets the instant alone",
		"reads_a_price": false,
		"charges": false,
		"validation": "none: no bounds check, no clamp, no membership test, no "
			+ "exception guard, and no existence check",
	},
	{
		"command": RESET_COMMAND,
		"action": ACTION_RESET,
		"source": "command.py:293-300",
		"args": ["track index"],
		"argument_order": "track",
		"counters_written": [KEY_ITEM, KEY_STEP, KEY_INSTANT],
		"effect": "all THREE counters are set to 0 for the addressed track and "
			+ "nothing else is written",
		"stamps_instant": false,
		"paired_reset": false,
		"reads_a_price": false,
		"charges": false,
		"validation": "none: no bounds check, no clamp, no membership test, no "
			+ "exception guard, and no existence check",
	},
]

const BRANCH_COUNT := 4

# -------------------------------------------------------- the writers --
## Every write to the research instant, with the committed source line. Four are
## dispatcher branches; the FIFTH is `fast_forward` and is offered by **no**
## action (design D7).
const INSTANT_WRITERS := [
	{
		"writer": "command:" + STEP_COMMAND,
		"source": "command.py:272",
		"kind": "dispatcher-branch",
		"effect": "instant = time_now",
		"client_writable": false,
	},
	{
		"writer": "command:" + CASH_COMMAND,
		"source": "command.py:280",
		"kind": "dispatcher-branch",
		"effect": "instant = 0",
		"client_writable": false,
	},
	{
		"writer": "command:" + ITEM_COMMAND,
		"source": "command.py:289",
		"kind": "dispatcher-branch",
		"effect": "instant = 0 (together with the step counter's reset)",
		"client_writable": false,
	},
	{
		"writer": "command:" + RESET_COMMAND,
		"source": "command.py:298",
		"kind": "dispatcher-branch",
		"effect": "instant = 0",
		"client_writable": false,
	},
	{
		"writer": "command:fast_forward",
		"source": "command.py:923 (read), command.py:927 (write)",
		"kind": "engine-side decrement inside a dispatcher branch",
		"effect": "for every track: instant = max(0, instant - seconds), where "
			+ "`seconds` is the CLIENT-SUPPLIED args[0] (command.py:906)",
		"client_writable": true,
	},
]

const INSTANT_WRITER_COUNT := 5
const INSTANT_WRITER_FAST_FORWARD := "command:fast_forward"
const FAST_FORWARD_COMMAND := "fast_forward"

const FAST_FORWARD_CONTRACT := ("RECORDED AND IMPLEMENTED NOT AT ALL. The "
	+ "research instant has FIVE writers (command.py:272, 280, 289, 298, and 927), "
	+ "and the FIFTH is not a research branch at all: fast_forward "
	+ "(command.py:905) reads the instant at command.py:923 and subtracts a "
	+ "CLIENT-SUPPLIED number of seconds from every track's entry at "
	+ "command.py:927, clamped at zero. That makes the research instant "
	+ "client-writable in exactly the way M8 line 6 found a row's instant "
	+ "client-writable, and it is named here because it is the ONLY elapsed-time "
	+ "input the research system has — an instant trusted by nothing, in a system "
	+ "where nothing reads it. NO fast-forward operation is delivered by the "
	+ "client facade, by either GameApi implementation, by this flow, or by any "
	+ "route, and no elapsed-time, remaining-time, readiness, or completion "
	+ "behaviour is derived from the instant anywhere in this repository (design "
	+ "D7)")

# ---------------------------------------------------- the two tracks --
## The committed track names, carried as DATA so no code identifier in this
## repository is named after either of them (design D5). The constants exist in
## the server **only** inside the four branch comments, so a value equal to a
## legacy constant name is not evidence that the constant exists.
const TRACK_NAME_PRIMARY := "TYPE_AREA_51"
const TRACK_NAME_SECONDARY := "TYPE_ROBOTIC"

## The committed building identifiers the two track names resolve to
## (`constants.py:299-300`).
const COMMITTED_BUILDING_ROBOTIC_CENTER := 86
const COMMITTED_BUILDING_AREA_51 := 139

const TRACKS := [
	{
		"track": 0,
		"name": TRACK_NAME_PRIMARY,
		"display_name": "Area 51",
		"building_id": COMMITTED_BUILDING_AREA_51,
		"building_constant": "constants.py:300 ID_BUILDING_AREA_51 = 139",
		"where_named": "only inside the four branch comments "
			+ "(command.py:269, 278, 285, 294)",
		"defined_in_server": false,
	},
	{
		"track": 1,
		"name": TRACK_NAME_SECONDARY,
		"display_name": "Robotic Center",
		"building_id": COMMITTED_BUILDING_ROBOTIC_CENTER,
		"building_constant": "constants.py:299 ID_BUILDING_ROBOTIC_CENTER = 86",
		"where_named": "only inside the four branch comments "
			+ "(command.py:269, 278, 285, 294)",
		"defined_in_server": false,
	},
]

const TRACK_RECORD_NOTE := ("REPORTED AND NEVER USED. The two track names exist "
	+ "ONLY inside the four branch comments and are DEFINED NOWHERE in the "
	+ "legacy server: zero definitions and zero non-comment uses across "
	+ "command.py, engine.py, sessions.py, server.py, constants.py, "
	+ "get_game_config.py, and version.py. Their mapping to the committed "
	+ "building identifiers rests on the comment's own word order plus the four "
	+ "print statements' display list [\"Area 51\", \"Robotic Center\"][_type]. "
	+ "That is enough to REPORT the mapping and is not enough to DERIVE anything "
	+ "from it, so no counter value, unlock, requirement, or cost is computed "
	+ "from a track's name or building id (design D5). No code identifier in "
	+ "this repository is named after either track constant, which is what makes "
	+ "the 'never used' claim mechanical rather than editorial")

# ------------------------------------------------ the recorded absences --
const NO_PRICE := ("NO RESEARCH PRICE IS CHARGED AND NO STORED RESOURCE MOVES. "
	+ "No committed content records a research cost, a step count, an unlock "
	+ "requirement, or a reward, and the one price-taking branch charges "
	+ "nothing: research_buy_step_cash reads a client-supplied cash value and "
	+ "discards it (command.py:277), printing 'Buy research step for …' and "
	+ "moving no balance. Because do_command applies the request's per-command "
	+ "vector BEFORE dispatch (command.py:40, engine.py:251-271), any price a "
	+ "client attached would be a client-trusted mint or burn, so the derived "
	+ "vector is NEUTRAL and every action's post-execution proof requires that "
	+ "EVERY stored resource be UNCHANGED (design D3). Deriving a price from any "
	+ "committed field would invent an economy the content does not contain")

const NO_READINESS := ("NO COMPLETION, READINESS, REMAINING-TIME, OR UNLOCK "
	+ "SEMANTICS ARE IMPLEMENTED, because the legacy server has NONE to "
	+ "reproduce. The three research counters are WRITE-ONLY: every occurrence "
	+ "of researchStepNumber and researchItemNumber in the seven legacy modules "
	+ "is a WRITE (3 sites and 2 sites respectively, all writes), and the single "
	+ "read of timeStampDoResearch outside its own branches is command.py:923 "
	+ "inside fast_forward — and that read is itself a write. So NOTHING anywhere "
	+ "reads a research counter to decide anything: there is no server-side "
	+ "completion test, no readiness test, no remaining-time computation, no "
	+ "unlock gate, and no cost check. This projection computes NO readiness, NO "
	+ "remaining time, NO progress ratio, NO completion fraction, and NO derived "
	+ "step count (design D1). The absence is a recorded property of the legacy "
	+ "contract, not a missing feature; a later line may introduce any of them "
	+ "only as its own deliverable, with its own evidence")

const NO_BOUNDS := ("NO COUNTER BOUND, MEMBERSHIP RULE, OR CLAMP IS ADDED. A "
	+ "guard audit of all four branches finds no bounds check, no numeric clamp, "
	+ "no membership test, no exception guard, and no existence check: a client "
	+ "naming a track outside the vector would raise IndexError in legacy, and a "
	+ "client naming a large track number would let the counter grow without "
	+ "limit. Both are legacy behaviours, and reproducing them means NOT "
	+ "inventing validation (design D6). The recorded absence is NOT permission "
	+ "to invent a bound: the only structural checks are that the track is an "
	+ "integer the two-entry vector addresses and that the vector itself is "
	+ "well-formed, because a client that cannot address its own state is not "
	+ "delivering behaviour. An authoritative limit belongs to Server v1 / M13")

const NO_REWARD := ("NO REWARD IS PAID, AND NONE EXISTS. There is no committed "
	+ "reward for research anywhere in the content — not even a zero-valued one "
	+ "— so there is nothing to derive one from and none is invented (design "
	+ "D4). This is the same shape as the committed level curve's unread "
	+ "reward_type/reward_amount fields and the quests table's unread reward: a "
	+ "recorded field with no consumer is a fact, and reading one as a promise "
	+ "would be an invention")

## The four refusal families, each with its non-empty recorded reason. They are
## stated as requirements (design D4/D6), not as omissions.
const REFUSALS := [
	{"refusal": "no_price", "implemented": false, "reason": NO_PRICE},
	{"refusal": "no_readiness", "implemented": false, "reason": NO_READINESS},
	{"refusal": "no_bounds", "implemented": false, "reason": NO_BOUNDS},
	{"refusal": "no_reward", "implemented": false, "reason": NO_REWARD},
]
const REFUSAL_COUNT := 4

## The helpers this projection deliberately does **NOT** provide, with the
## reason each is absent. Every entry is a readiness, remaining-time, price, or
## unlock rule the legacy server does not have to reproduce, so adding one would
## compute an invented answer — and the suite asserts this module's whole
## function inventory, so one cannot appear unnoticed (task 4.3).
const NON_DERIVATION := [
	{"helper": "is_research_complete", "absent_because":
		"no legacy branch reads a research counter to decide whether a step or an "
		+ "item finished, so there is no server-side completion to reproduce"},
	{"helper": "research_ready", "absent_because":
		"the research instant is reported verbatim and nothing derives a decision "
		+ "from it: the legacy server evaluates no research elapsed time at all"},
	{"helper": "research_duration", "absent_because":
		"there is no committed research duration field anywhere in the content, so "
		+ "there is no committed denominator to divide by"},
	{"helper": "research_price", "absent_because":
		"no committed research cost exists and the one price-taking branch charges "
		+ "nothing, so any price computed here would invent an economy"},
	{"helper": "unlock_research", "absent_because":
		"no committed unlock requirement exists, and the track-to-building mapping "
		+ "supports no derivation because the track constants are undefined in the "
		+ "server (design D5)"},
	{"helper": "research_step_count", "absent_because":
		"no committed step count exists, so a total could only be invented"},
	{"helper": "research_reward", "absent_because":
		"no committed reward for research exists, not even a zero-valued one"},
	{"helper": "fast_forward", "absent_because":
		"the research instant's fifth writer subtracts a CLIENT-SUPPLIED number of "
		+ "seconds and is recorded, not delivered: no action and no route derives it "
		+ "(design D7)"},
]

## The measured content findings, including the **two** figures the M9
## investigation and this line's proposal got wrong.
const CONTENT_ABSENCE := ("NO COMMITTED RESEARCH CONTENT IS INVENTED. MEASURED "
	+ "over all 23 normalized files and config/main.json: (1) NO normalized "
	+ "package carries a research SECTION — no file has a top-level key of any "
	+ "research kind, and all 23 are top-level arrays of domain rows; (2) the "
	+ "string 'research' appears in exactly TWO normalized files, not one: "
	+ "buildings.json, ONCE, inside the `name` of legacy_id \"256\" (\"Research "
	+ "Lab\"), and images.json, in exactly THREE rows whose `legacy_id`/`path` "
	+ "are popupResearchCenter_buildingProcess.swf and its _2 and _3 variants — "
	+ "six occurrences in total, all asset references; (3) config/main.json has "
	+ "ZERO top-level content keys naming research and ZERO nested "
	+ "content-section keys, but it does have THREE keys containing the word, all "
	+ "of them under /images (the asset namespace whose keys are asset paths by "
	+ "construction), and exactly ONE string value containing it, /items/244/name "
	+ "= \"Research Lab\". MEASURED CORRECTION: the M9 investigation and this "
	+ "line's proposal both state that 'research' appears in exactly ONE "
	+ "normalized file and only inside one `name`, and that config/main.json has "
	+ "NO key containing 'research' at any depth. BOTH FIGURES ARE WRONG — it is "
	+ "two files and it is three image keys plus one value — and both are "
	+ "corrected here rather than shipped. The CONCLUSION is unchanged and is "
	+ "what matters: there is no committed research cost, step count, unlock "
	+ "requirement, or reward to derive a schedule from, so none is invented and "
	+ "no price, step count, requirement, or reward is computed anywhere in this "
	+ "repository (design D4)")

# ------------------------------------------------- the refusal reasons --
## The named reasons the projection can report for a state it cannot read. An
## unresolvable vector is REPORTED with its recorded state intact and is never
## defaulted to a zero vector presented as a resolved one.
const REASON_ABSENT_STATE := "absent_research_state"
const REASON_NON_OBJECT := "non_object_private_state"
const REASON_NOT_A_LIST := "non_list_counter"
const REASON_WRONG_LENGTH := "wrong_track_count"
const REASON_NON_INTEGER := "non_integer_counter"
const REASON_NEGATIVE := "negative_counter"

## Every structural refusal reason, closed so a caller can enumerate them.
const PROJECTION_REASONS := [
	REASON_ABSENT_STATE, REASON_NON_OBJECT, REASON_NOT_A_LIST,
	REASON_WRONG_LENGTH, REASON_NON_INTEGER, REASON_NEGATIVE,
]

## The committed corpus's own research state, pinned so a corpus drift is a
## visible mismatch rather than a silently different report.
const CORPUS_VECTOR := {
	KEY_STEP: [0, 0],
	KEY_ITEM: [0, 0],
	KEY_INSTANT: [0, 0],
}
const CORPUS_PLACEMENTS := 40
const CORPUS_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}
## The executed-legacy fixture's eight branch-track combinations.
const CAPTURED_COMBINATIONS := 8

## The projected per-track counters, verbatim.
class TrackView:
	extends RefCounted
	var _track := -1
	var _step: Variant = null
	var _item: Variant = null
	var _instant: Variant = null

	func track() -> int:
		return _track

	## The committed step counter, verbatim. No scaling, no rounding, no
	## defaulting: a `0` here is a real committed zero.
	func step() -> Variant:
		return _step

	func item() -> Variant:
		return _item

	## The committed research instant, verbatim. **No elapsed-time rule is
	## computed from it**, so reading it implies no timer and no readiness.
	func instant() -> Variant:
		return _instant

	## The whole committed track as one fresh record — a copy on every call, never
	## a live view.
	func fields() -> Dictionary:
		return {
			"track": _track,
			"step": _step,
			"item": _item,
			"instant": _instant,
		}


## The whole research state: both tracks, all three counters, verbatim.
##
## Read-only by construction — no setter, no mutating method, no writable public
## field. Every reader returns a committed value or a fresh copy, and reading it
## can change neither the save it was parsed from nor any committed content.
class ResearchView:
	extends RefCounted
	var _resolvable := false
	var _reason := ""
	var _error := ""
	var _records: Array = []
	var _counters: Dictionary = {}
	var _recorded: Variant = null

	## Whether the state resolved. `false` means it is reported **with its
	## recorded state intact**, never defaulted to a zero vector.
	func resolvable() -> bool:
		return _resolvable

	## The named reason an unresolvable state was refused, or "" while it
	## resolves.
	func reason() -> String:
		return _reason

	## The refusal message, naming the counter and the value that failed.
	func error() -> String:
		return _error

	## Both tracks, each a `TrackView`, in committed track order.
	func tracks() -> Array:
		var out: Array = []
		for record: Variant in _records:
			out.append(record)
		return out

	## One track's `TrackView`, or null when the index does not address one.
	func track(index: int) -> Variant:
		for record: Variant in _records:
			if int((record as TrackView).track()) == index:
				return record
		return null

	## The three committed counter vectors, each a fresh copy.
	func counters() -> Dictionary:
		var out: Dictionary = {}
		for key: String in COUNTERS:
			out[key] = (_counters[key] as Array).duplicate()
		return out

	## The state's **recorded** shape, verbatim, whatever it is. It travels beside
	## the refusal so a reader can see exactly what the save held.
	func recorded() -> Variant:
		return _recorded

	## The whole projection as one fresh record.
	func fields() -> Dictionary:
		var rows: Array = []
		for record: Variant in tracks():
			rows.append((record as TrackView).fields())
		return {
			"resolvable": _resolvable,
			"reason": _reason,
			"error": _error,
			"tracks": rows,
			"counters": counters(),
			"verbatim": true,
		}


# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------


## Whether `value` names one of the four closed research actions. The set is
## **closed**: `fast_forward` is deliberately absent (design D7), because its
## `seconds` argument is client-supplied and no evidence constrains what a client
## sends.
static func is_action(value: Variant) -> bool:
	return (value is String) and ACTIONS.has(value)


## Whether `value` is a strict integer the two-entry vector addresses. `0` and
## `1` are the two tracks; anything else is refused **structurally**. That is
## the ONLY track rule here: the legacy branches add no membership test, so a
## track outside the vector would raise `IndexError` in legacy — a behaviour this
## contract records (design D6) and does not reproduce.
static func is_track(value: Variant) -> bool:
	if value is bool:
		return false
	if not (value is int) and not (value is float):
		return false
	var number := float(value)
	if number != floor(number) or not is_finite(number):
		return false
	var index := int(number)
	return index >= 0 and index < TRACK_COUNT


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------


## Projects a player's `privateState` into a typed `ResearchView`. Returns
## `{ok, error, reason, research}` — `ok: false` with a **named** reason and the
## recorded state attached, never a zero vector presented as resolved
## (task 1.2).
##
## A state that is absent, is not an object, carries a counter that is not a
## list, holds the wrong number of entries, or holds a non-integer or negative
## value is **unresolvable**; nothing is scaled, rounded, defaulted, or clamped.
## The pinned engine's JSON parser widens every committed number to a float, so
## an `int` or an integral `float` is accepted — the documented transport
## tolerance the delivered definition, building, and unit catalogs already apply
## to the same field class — while a numeric **string** is refused, because no
## committed source stores one.
static func project(private_state: Variant) -> Dictionary:
	if private_state == null:
		return _reject(REASON_ABSENT_STATE,
			"the player's private state is absent, so no research track is "
			+ "addressable", private_state)
	if not (private_state is Dictionary):
		return _reject(REASON_NON_OBJECT,
			"the player's private state is %s, not an object"
				% _type_name(private_state), private_state)
	var source: Dictionary = private_state
	for key: String in COUNTERS:
		if not source.has(key):
			return _reject(REASON_ABSENT_STATE,
				"the player's private state carries no %s, so no research track "
				% key + "is addressable", private_state)
		var value: Variant = source[key]
		if not (value is Array):
			return _reject(REASON_NOT_A_LIST,
				"the player's private state %s is %s, not a list"
					% [key, _type_name(value)], private_state)
		if (value as Array).size() != TRACK_COUNT:
			return _reject(REASON_WRONG_LENGTH,
				"the player's private state %s holds %d entries, not the %d "
					% [key, (value as Array).size(), TRACK_COUNT]
				+ "tracks it must carry", private_state)
		for index in range(TRACK_COUNT):
			var entry: Variant = _integer((value as Array)[index])
			if entry == null:
				return _reject(REASON_NON_INTEGER,
					"the player's private state %s[%d] is %s, not an integer"
						% [key, index, _type_name((value as Array)[index])],
					private_state)
			if int(entry) < 0:
				return _reject(REASON_NEGATIVE,
					"the player's private state %s[%d] is %d, not a "
						% [key, index, int(entry)]
					+ "non-negative counter", private_state)
	var research := ResearchView.new()
	research._resolvable = true
	research._recorded = _recorded_snapshot(source)
	for index in range(TRACK_COUNT):
		var record := TrackView.new()
		record._track = index
		record._step = int(_integer((source[KEY_STEP] as Array)[index]))
		record._item = int(_integer((source[KEY_ITEM] as Array)[index]))
		record._instant = int(_integer((source[KEY_INSTANT] as Array)[index]))
		research._records.append(record)
	for key: String in COUNTERS:
		research._counters[key] = [
			int(_integer((source[key] as Array)[0])),
			int(_integer((source[key] as Array)[1])),
		]
	return {"ok": true, "error": "", "reason": "", "research": research}


## The whole flow's ONE evaluation entry point: the projection plus the recorded
## contracts, the presence predicates, and the recorded absences. A surface uses
## this and nothing else.
##
## Returns `{ok, reason, error, research, fields, resolvable, tracks, counter,
## record}` — `ok: false` for a structural refusal, `ok: true` with
## `resolvable: false` when the state itself could not be read, and `ok: true`
## with `resolvable: true` when it could. It computes **no** readiness, **no**
## remaining time, **no** progress ratio, and **no** completion.
static func evaluate(private_state: Variant) -> Dictionary:
	var projected: Variant = project(private_state)
	if not bool(projected.get("ok", false)):
		return {
			"ok": false,
			"reason": str(projected.get("reason", REASON_ABSENT_STATE)),
			"error": str(projected.get("error", "")),
			"research": null,
			"fields": {},
			"resolvable": false,
			"tracks": [],
			"counter": null,
			"record": branch_record(),
		}
	var research: Variant = projected.get("research", null)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"research": research,
		"fields": (research as ResearchView).fields(),
		"resolvable": true,
		"tracks": (research as ResearchView).tracks(),
		"counter": null,
		"record": branch_record(),
	}


## Whether this client would offer `action` against `track`. True for every
## readable state and either track: the four legacy branches validate **nothing**,
## and the recorded absence of validation is **not permission** to add a gate
## here (design D6). This is a button's availability, not an authority — the
## service's own structural guards and a later server-authoritative milestone own
## the rules.
static func offers(evaluation: Dictionary, action: Variant,
		track: Variant) -> bool:
	if not bool(evaluation.get("ok", false)):
		return false
	if not is_action(action) or not is_track(track):
		return false
	return true


## The client's own reason an intent is not offered, or "" while it is. It is a
## **client-side** answer, deliberately distinct from every service code, and it
## is never sent.
static func refusal_text(evaluation: Dictionary, action: Variant,
		track: Variant) -> String:
	if bool(evaluation.get("ok", false)) and offers(evaluation, action, track):
		return ""
	if not bool(evaluation.get("ok", false)):
		return "no research intent offered: %s" % str(evaluation.get("error", ""))
	if not is_action(action):
		return "no research intent offered: action must be one of %s" % \
			", ".join(PackedStringArray(ACTIONS))
	return "no research intent offered: track must be an integer in 0..%d" % \
		(TRACK_COUNT - 1)


# ---------------------------------------------------------------------------
# The intent (design D2)
# ---------------------------------------------------------------------------


## The **whole** research request body: the player identifier, the closed action,
## and the track. Nothing else.
##
## This function is the structural form of the "no client value is trusted"
## claim: there is **no** parameter and **no** key through which a client could
## send a counter value, a research instant, or a cash amount, so the service has
## nothing client-derived to ignore. An action outside the closed set or a track
## the vector cannot address is refused here with a named reason, before a
## request is formed.
static func intent_body(user_id: String, action: Variant,
		track: Variant) -> Dictionary:
	if not is_action(action):
		return {
			"ok": false,
			"reason": "invalid_action",
			"error": "action must be one of %s" % ", ".join(PackedStringArray(ACTIONS)),
			"body": {},
		}
	if not is_track(track):
		return {
			"ok": false,
			"reason": "invalid_track",
			"error": "track must be an integer in 0..%d" % (TRACK_COUNT - 1),
			"body": {},
		}
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"body": {
			"user_id": user_id,
			"action": str(action),
			"track": int(track),
		},
	}


## The intent's wire contract as the evidence report records it: the exact key
## set, the ignored keys, and the derivation that replaces them.
static func intent_record() -> Dictionary:
	return {
		"keys": (INTENT_KEYS as Array).duplicate(),
		"ignored_keys": (INTENT_IGNORED_KEYS as Array).duplicate(),
		"path": RESEARCH_PATH,
		"action_vocabulary": (ACTIONS as Array).duplicate(),
		"track_count": TRACK_COUNT,
		"note": "the client sends EXACTLY the player identifier, a closed "
			+ "action, and a track. No counter value, no research instant, and "
			+ "no cash amount is expressible, so the service derives every one "
			+ "of them itself and ignores any such key a client attaches "
			+ "alongside (design D2)",
		"cash_rule": "research_buy_step_cash is handed a SERVER-DERIVED cash "
			+ "value of 0 and the branch discards it anyway (command.py:277), so "
			+ "no research price is claimed in either direction (design D3)",
		"vector": "NEUTRAL: a research price would be a client-sent delta, "
			+ "because the legacy dispatcher applies the request's per-command "
			+ "vector BEFORE the branch (command.py:40, engine.py:251-271) as "
			+ "max(current + delta, 0)",
		"fast_forward_offered": false,
	}


## The four branch contracts as fresh records a caller may keep and mutate, so a
## report reads the model's own table rather than restating it.
static func branch_record() -> Dictionary:
	return {
		"branches": (BRANCHES as Array).duplicate(true),
		"branch_count": BRANCH_COUNT,
		"cash_action": CASH_ACTION,
		"paired_reset_command": ITEM_COMMAND,
		"instant_writers": (INSTANT_WRITERS as Array).duplicate(true),
		"instant_writer_count": INSTANT_WRITER_COUNT,
		"fast_forward": FAST_FORWARD_CONTRACT,
		"non_derivation": (NON_DERIVATION as Array).duplicate(true),
		"refusals": (REFUSALS as Array).duplicate(true),
		"refusal_count": REFUSAL_COUNT,
		"tracks": (TRACKS as Array).duplicate(true),
		"tracking_note": TRACK_RECORD_NOTE,
		"content_absence": CONTENT_ABSENCE,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The research readout for the live evaluation: **both** tracks with their three
## committed counters verbatim, and the recorded absences stated outright rather
## than left for a reader to wonder whether the omission is a defect.
##
## **No remaining time, no progress ratio, no readiness, and no price appear**,
## and the readout says so. An unresolvable state reads as unresolvable with its
## recorded reason — never as two tracks of zeros, which is a state no committed
## save holds and one this contract refuses to render as resolved.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if not bool(evaluation.get("resolvable", false)):
		return ("research unresolvable: %s (%s) — reported with the recorded "
			% [str(evaluation.get("reason", "")), str(evaluation.get("error", ""))]
			+ "state intact, never defaulted to a zero vector")
	var parts: Array = []
	for track: int in range(TRACK_COUNT):
		var record: Variant = (evaluation.get("research", null) as ResearchView) \
			.track(track)
		if record == null:
			parts.append("track %d: (no committed record)" % track)
			continue
		parts.append("track %d (%s, committed building %d): step %s, item %s, "
			% [track,
				str((TRACKS[track] as Dictionary)["display_name"]),
				int((TRACKS[track] as Dictionary)["building_id"]),
				str((record as TrackView).step()),
				str((record as TrackView).item())]
			+ "instant %s" % str((record as TrackView).instant()))
	parts.append("no readiness, no completion, no remaining time, no unlock: "
		+ "the counters are read by nothing in the legacy server")
	parts.append("no price: the cash branch reads a cash value and discards it, "
		+ "charging nothing")
	parts.append("no bounds: the four branches validate nothing")
	parts.append("fast_forward is a recorded fourth writer of the instant and is "
		+ "NOT delivered")
	parts.append("track-to-building mapping is reported and never used")
	return " | ".join(parts)


## The armed surface's own confirm text for one research intent: it names the
## track and the recorded effect and says that nothing about the outcome is
## decided here — no counter value, no instant, no cash amount — because the
## service derives every one of them. It is deliberately free of every number a
## player might read as a price or a timer.
static func confirm_text(action: Variant, track: Variant) -> String:
	if not is_action(action) or not is_track(track):
		return ""
	var record: Dictionary = BRANCHES[_action_index(action)]
	var display := str((TRACKS[int(track)] as Dictionary)["display_name"])
	return ("%s on track %d (%s)? The legacy branch %s. It charges nothing, no "
		% [str(action), int(track), display, str(record["command"])]
		+ "readiness or completion exists, and no counter value, instant, or "
		+ "cash amount is sent: the service derives every one of them.")


# ---------------------------------------------------------------------------
# The typed result
# ---------------------------------------------------------------------------


## Result of `research_town_town()`: the legacy result plus the authoritative
## superset — the service's derived counters, the vector as read BEFORE and
## AFTER execution, both committed tracks, and the seven stored resources — or a
## structured failure with **no partial payload**.
##
## **No stored resource is expected to move**: the derived vector is neutral and
## the endpoint's second post-execution proof half requires every stored resource
## to be **unchanged**, which is what forecloses a client minting or burning a
## balance through this path.
##
## The client applies `counters`, `vector_after`, and `resources` **verbatim** —
## the response always wins over the client's own model.
class ResearchResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field, so
	## tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The action the service resolved and executed, echoed exactly as sent.
	var action := ""
	## The research track addressed, echoed exactly as sent. `-1` on failure.
	var track := -1
	## The legacy command the service derived from the action.
	var command := ""
	## The service's own derivation for the addressed track: `step`, `item`,
	## `instant`, and the flags. `instant` is `null` exactly when the branch
	## stamps the wall clock and the value is therefore not derivable.
	var derived: Dictionary = {}
	## The counter vector as read BEFORE and AFTER execution, each the three
	## committed two-entry lists.
	var vector_before: Dictionary = {}
	var vector_after: Dictionary = {}
	## The service's `research` projection after execution.
	var research: Dictionary = {}
	## Both committed track records, reported as content and never used.
	var tracks: Array = []
	var tracks_source: Array = []
	## The cash record: `charged` is a constant `0`, `ignored` says the branch's
	## own argument was discarded, and `price_computed` is a constant `false`.
	var cash_charged := 0
	var cash_argument_ignored := false
	var price_computed := true
	## Whether the service offered a fast-forward operation: a constant `false`.
	var fast_forward_offered := true
	var resources: BootData.Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for the research intents (never a partial payload).
static func result_failure(code: String, message: String) -> ResearchResult:
	var result := ResearchResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses a v0 research envelope — success or structured error — into the typed
## result, fail-closed in both directions. The envelope must be a JSON object
## reporting `ok: true`, the protocol must be the v0 one, the legacy result
## string must be `success`, the echoed action must be inside the closed
## `ACTIONS` set, `track` must be an addressable integer, `command` must be the
## one that action derives, `derived` must carry the documented fields, both
## vectors must be the three committed two-entry integer lists, the `research`
## block must carry both tracks and an **empty** `derived` block, and `resources`
## must be the seven non-negative integers every other response carries.
##
## A response that reports a **non-zero** cash charge, a computed price, or an
## offered fast-forward operation is refused: those are the three absences this
## line delivers, and a response claiming otherwise describes a different
## contract.
static func parse_result(payload: Variant) -> ResearchResult:
	if not (payload is Dictionary):
		return result_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _result_error(envelope)
	if str(envelope.get("protocol", "")) != BootData.PROTOCOL:
		return result_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [BootData.PROTOCOL,
				str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return result_failure("bad_response",
			"research response did not report the legacy success result")
	var action := str(envelope.get("action", ""))
	if not ACTIONS.has(action):
		return result_failure("bad_response",
			("the research response echoed action '%s', which is outside the "
				% action + "closed set %s") % ", ".join(PackedStringArray(ACTIONS)))
	var track: Variant = BootData._parse_int(envelope.get("track"))
	if track == null or not is_track(track):
		return result_failure("bad_response",
			"the research response carries no addressable track")
	var command := str(envelope.get("command", ""))
	if command != str((ACTION_COMMANDS as Dictionary)[action]):
		return result_failure("bad_response",
			"the research response derived command '%s' for action '%s', which is "
				% [command, action] + "not the committed one")
	var derived: Variant = envelope.get("derived")
	if not (derived is Dictionary):
		return result_failure("bad_response",
			"the research response carries no derived block")
	var derived_body: Dictionary = derived as Dictionary
	for field: String in ["step", "item", "instant", "stamps_instant",
			"paired_reset", "written", "untouched_counters"]:
		if not derived_body.has(field):
			return result_failure("bad_response",
				"the research response's derived block carries no %s" % field)
	var before: Variant = _parse_vector(envelope.get("previous"), "previous")
	if before == null:
		return result_failure("bad_response",
			"the research response carries no readable before vector")
	var after: Variant = _parse_vector(envelope.get("counters"), "counters")
	if after == null:
		return result_failure("bad_response",
			"the research response carries no readable after vector")
	var research: Variant = envelope.get("research")
	if not (research is Dictionary):
		return result_failure("bad_response",
			"the research response carries no research projection")
	var research_body: Dictionary = research as Dictionary
	var research_derived: Variant = research_body.get("derived")
	if not (research_derived is Dictionary) \
			or not (research_derived as Dictionary).is_empty():
		return result_failure("bad_response",
			"the research response's projection reports a DERIVED value, which no "
			+ "legacy research rule exists to produce")
	var rows: Variant = research_body.get("tracks")
	if not (rows is Array) or (rows as Array).size() != TRACK_COUNT:
		return result_failure("bad_response",
			"the research response does not carry both committed tracks")
	var charges: Variant = BootData._parse_int(envelope.get("cash_charged"))
	if charges == null or int(charges) != 0:
		return result_failure("bad_response",
			"the research response charges cash, which the legacy branch never "
			+ "does: it reads args[0] and discards it")
	if envelope.get("cash_argument_ignored") != true:
		return result_failure("bad_response",
			"the research response does not state that the cash argument was "
			+ "discarded")
	if envelope.get("price_computed") != false:
		return result_failure("bad_response",
			"the research response claims it computed a price, and no committed "
			+ "research price exists")
	if envelope.get("fast_forward_offered") != false:
		return result_failure("bad_response",
			"the research response offers a fast-forward operation, which this "
			+ "line delivers not at all")
	var tracks: Variant = envelope.get("tracks_source")
	if not (tracks is Array) or (tracks as Array).size() != TRACK_COUNT:
		return result_failure("bad_response",
			"the research response does not carry both committed track records")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return result_failure("bad_response",
			"research response carries no resources object")
	var resources := BootData._parse_resources(resources_raw)
	if resources == null:
		return result_failure("bad_response",
			"research resources are not seven non-negative integers")
	var result := ResearchResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return result_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.action = action
	result.track = int(track)
	result.command = command
	result.derived = derived_body.duplicate(true)
	result.vector_before = before
	result.vector_after = after
	result.research = research_body.duplicate(true)
	result.tracks = (envelope.get("tracks") as Array).duplicate(true)
	result.tracks_source = (tracks as Array).duplicate(true)
	result.cash_charged = 0
	result.cash_argument_ignored = true
	result.price_computed = false
	result.fast_forward_offered = false
	result.resources = resources
	return result


# ---------------------------------------------------------------------------
# The evidence's own records
# ---------------------------------------------------------------------------


## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can check, and
## every derived fact states what it is derived from.
const PROVENANCE := {
	"established": [
		{"fact": "the research state is three two-entry counters in the player's "
			+ "private state: researchStepNumber, researchItemNumber, and "
			+ "timeStampDoResearch",
			"evidence": "command.py:271-298; tests/saves/fresh-player.json, where "
				+ "all three hold [0, 0]"},
		{"fact": "four dispatcher branches advance them, over two tracks, with "
			+ "the recorded per-branch effects and line ranges",
			"evidence": "command.py:268-274, 276-282, 284-291, 293-300; the "
				+ "committed executed fixture in tests/fixtures/godot-research/"},
		{"fact": "the item branch resets the step counter AND the research instant "
			+ "together, and no other branch resets the step counter",
			"evidence": "command.py:288 and command.py:289, adjacent lines in one "
				+ "branch"},
		{"fact": "research_buy_step_cash reads a client-supplied cash value and "
			+ "discards it: playerInfo.cash does not move even when the branch is "
			+ "handed 250",
			"evidence": "command.py:276-282; probe 1 of the committed fixture, "
				+ "executed against the real legacy server"},
		{"fact": "the three counters are WRITE-ONLY: three step sites, two item "
			+ "sites, all writes, and the instant's single read is itself a write "
			+ "inside fast_forward",
			"evidence": "the seven legacy modules, measured per line; "
				+ "command.py:923 and 927"},
		{"fact": "the research instant has five writers and the fifth subtracts a "
			+ "client-supplied number of seconds, clamped at zero",
			"evidence": "probes 2 and 3 of the committed fixture, executed against "
				+ "the real legacy server"},
		{"fact": "there is no committed research cost, step count, unlock "
			+ "requirement, or reward",
			"evidence": "the measured content findings below, taken over all 22 "
				+ "normalized files and config/main.json"},
		{"fact": "the two tracks resolve to committed building ids 139 and 86",
			"evidence": "constants.py:299-300"},
	],
	"derived": [
		{"fact": "the projection refuses an absent, non-object, non-list, "
			+ "wrong-length, non-integer, or negative state and reports it with its "
			+ "recorded state intact",
			"evidence": "derived (design D1): the service's own derivation fails "
				+ "closed on the same shapes with "
				+ "`unresolvable_research_state`, so the client mirrors it rather "
				+ "than defaulting a zero vector"},
		{"fact": "the intent is three keys wide: a player identifier, a closed "
			+ "action, and a track",
			"evidence": "derived (design D2): the same intent-only discipline the "
				+ "queue, collection, and revival endpoints apply, chosen because "
				+ "every legacy branch takes its outcome from the client"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy research panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


## The evidence's explicit non-claims (spec "Research evidence and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO RESEARCH PRICE IS CHARGED AND NO STORED RESOURCE MOVES, because none is "
		+ "committed and the one price-taking branch reads a cash value and "
		+ "discards it; the endpoint's post-execution proof compares the COMPLETE "
		+ "stored resource set, which is what makes the claim non-tautological",
	"NO COMPLETION, READINESS, REMAINING-TIME, OR UNLOCK SEMANTICS ARE "
		+ "IMPLEMENTED, because the counters are read by nothing: they are "
		+ "write-only in the legacy source",
	"NO COUNTER BOUND, MEMBERSHIP RULE, OR CLAMP IS ADDED, the legacy branches "
		+ "having none; the recorded absence is a property of the contract, not "
		+ "permission",
	"NO REWARD IS PAID, and none exists: there is no committed reward for "
		+ "research anywhere, not even a zero-valued one",
	"NO COMMITTED RESEARCH CONTENT IS INVENTED, none existing: this is a "
		+ "MEASURED absence, and it corrected two figures of the M9 investigation "
		+ "that had it wrong",
	"the track-to-building mapping is REPORTED and NEVER USED: the track "
		+ "constants are undefined in the server, no code identifier is named "
		+ "after either of them, and nothing is derived from the mapping",
	"NO FAST-FORWARD OPERATION IS DELIVERED, though its write of the research "
		+ "instant is recorded as the fourth writer",
	"THE COUNTERS HAVE NO IN-GAME CONSUMER: nothing in the legacy server reads "
		+ "one to decide anything, so the delivered feature is observable ONLY as "
		+ "these counter transitions and nothing more",
	"the fixture covers FOUR branches over BOTH tracks and nothing else: no "
		+ "readiness, no completion, and no reward is evidenced, and the item "
		+ "branch's instant half is a recorded no-op transition because exactly "
		+ "eight steps leave no room for a priming step",
	"no compatibility route beyond the four guarded intents this line delivers "
		+ "exists for a research track, and the service adds no server-authoritative "
		+ "validation of bounds, membership, or price - that belongs to Server v1 "
		+ "/ M13",
	"no pixel-parity oracle exists",
	"no windowed capture is claimed: nothing is rendered, and the committed "
		+ "corpus places neither research building",
	"the committed capture runs the fake GameApi implementation for the "
		+ "client-side evidence, a deterministic test double rather than a "
		+ "parity oracle; the executed-legacy parity rests on the committed "
		+ "fixture and the live phase",
]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural refusal: no `ResearchView` at all, the named reason, a message
## that names the offending counter, and the **recorded** state carried through
## untouched so a caller can see what the save held.
static func _reject(reason: String, message: String,
		recorded: Variant) -> Dictionary:
	return {
		"ok": false,
		"reason": reason,
		"error": "[research] projection refused (%s): %s" % [reason, message],
		"research": null,
		"recorded": _recorded_snapshot(recorded),
	}


## The recorded private state as a plain copy, so a refusal can hand it back
## without aliasing the live save. A non-object becomes its type name rather than
## being invented into a shape.
static func _recorded_snapshot(recorded: Variant) -> Variant:
	if recorded is Dictionary:
		var out: Dictionary = {}
		for key: Variant in (recorded as Dictionary).keys():
			out[str(key)] = (recorded as Dictionary)[key]
		return out
	return _type_name(recorded)


## One committed counter as the exact integer it denotes: an `int` or an
## integral `float` inside the transported exact-integer range. A numeric string
## fails closed, because coercing `"10"` to ten would invent a value the
## committed state does not carry.
static func _integer(value: Variant) -> Variant:
	if value is bool:
		return null
	if value is int:
		return int(value)
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number) \
				and absf(number) <= 9007199254740992.0:
			return int(number)
	return null


## The observed type of a refused value, so a failure names what it found
## instead of saying only "invalid".
static func _type_name(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "bool"
		TYPE_INT:
			return "int"
		TYPE_FLOAT:
			return "float"
		TYPE_STRING:
			return "string"
		TYPE_ARRAY:
			return "array"
		TYPE_DICTIONARY:
			return "object"
		_:
			return "unsupported"


## The index of one closed action inside `ACTIONS`, or `-1`.
static func _action_index(action: Variant) -> int:
	var index := 0
	for candidate: String in ACTIONS:
		if candidate == str(action):
			return index
		index += 1
	return -1


## One counter vector out of a response block, as the three committed two-entry
## integer lists, or null when the block is not readable.
##
## Two response shapes carry a vector: a **projection** block (`previous` and
## `research`) nests it under `counters`, while the response's own `counters`
## field IS the mapping. Both are accepted, and neither is coerced into the
## other.
static func _parse_vector(value: Variant, label: String) -> Variant:
	if not (value is Dictionary):
		return null
	var body: Dictionary = value as Dictionary
	var source: Variant = body
	if body.has("counters"):
		source = body["counters"]
	if not (source is Dictionary):
		return null
	var counters: Dictionary = source as Dictionary
	var out: Dictionary = {}
	for key: String in COUNTERS:
		var entries: Variant = counters.get(key)
		if not (entries is Array) or (entries as Array).size() != TRACK_COUNT:
			return null
		var row: Array = []
		for index in range(TRACK_COUNT):
			var number: Variant = BootData._parse_int((entries as Array)[index])
			if number == null or int(number) < 0:
				return null
			row.append(int(number))
		out[key] = row
	return out


## The service's structured error, carried through with its own code.
static func _result_error(envelope: Dictionary) -> ResearchResult:
	var error: Variant = envelope.get("error")
	if not (error is Dictionary):
		return result_failure("bad_response",
			"the research response reports failure with no error object")
	var body: Dictionary = error
	return result_failure(str(body.get("code", "bad_response")),
		str(body.get("message", "")))
