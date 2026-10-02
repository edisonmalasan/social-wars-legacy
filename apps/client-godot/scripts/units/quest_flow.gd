extends RefCounted
## Pure quest-state projection, intent contract, and typed result (OpenSpec
## `godot-quests` "The quest state is projected verbatim and fails closed" /
## "The six-branch command inventory records what each branch reads and writes" /
## "The `end_quest` destruction count is refused, and the refusal is recorded as a
## divergence" / "No quest reward is paid and no stored resource moves" / "The
## committed quest-content inventory is reported and never used" / "A quest action
## is a server-derived intent, and no client outcome is trusted" / "Quest timing is
## recorded as client-writable and never delivered" / "Quest evidence and claim
## limits", design D1-D12).
##
## ## This line delivers real state AND refuses the one destructive outcome
##
## Five of the six branches move quest state a client can legitimately be the
## source of intent for, so the projection, the branch inventory, and the
## six-branch intent surface are all real behaviour. The sixth — `end_quest` —
## destroys placed rows by a **client-computed** count, and that count is
## **REFUSED** and recorded as a **DIVERGENCE** rather than as parity (design D2).
##
## ## `complete_goal` writes NOTHING AT ALL (design D3)
##
## It reads a goal id, resolves the committed title, prints it, and returns. So
## there is no completion flag, no ledger, and no reward: a goal "completes" by
## being narrated in a `print` statement. The branch is delivered as a **no-op on
## purpose**, the service's post-execution proof requires the **whole** quest state
## to be byte-identical, and `NON_DERIVATION` plus the pinned function inventory
## make the absence mechanical rather than a promise.
##
## ## Only the identifier and the title are read (design D6)
##
## `reward` has **zero** legacy consumers and is **uniformly the value 10** on all
## **91** committed entries, so it carries no information even if it were read;
## `hint`, `description`, `kind`, `legacy_id`, `source_file`, `source_layer` and
## `content_version` all have **zero** as well. The committed content is therefore
## used ONLY to resolve an identifier and read its title, and `REWARD_FIELD_ABSENT`
## records that **no delivered code identifier or computation is named after the
## reward field** — the mechanical form of "reported, never used".
##
## ## No bound, no membership test, no elapsed time (design D4/D5/D9)
##
## `set_goals` grows the goals list **on demand with no upper bound** (a client-sent
## index of 500 appends 350 entries), and that absence is reproduced rather than
## closed: a bound the legacy server does not have would make this client stricter
## in the unexamined direction. `set_quest_var` accepts **any** key against the
## eight its own comment enumerates, and refuses exactly the one key the legacy
## branch **itself** ignores. `fast_forward` makes quest timing client-writable and
## is **recorded and delivered not at all**.
##
## ## The two type facts are REPRODUCED, not normalized (design D8)
##
## The corpus records `idCurrentMission` as an **integer** `0` while
## `collect_mission` writes a **string**, and the corpus records
## `currentQuestVars` as a recorded **null** which two branches convert to a dict.
## Normalizing either would hide a real legacy shape divergence; both are
## reproduced, asserted, and reported — and the projection **fails closed** on the
## corpus's null rather than assuming a dict.
##
## ## Read-only by construction
##
## `QuestStateView` **copies** the committed values when it is built and then
## declares no setter, no mutating method, and no writable public field. Every
## reader returns a committed value or a fresh copy, so reading a quest state can
## change neither the save it was parsed from nor the committed content.
## **Writing** quest state is behaviour: it belongs to the guarded intent below.
##
## ## The intent is INTENT-ONLY (design D2)
##
## `intent_body()` produces exactly three keys — a player identifier, a closed
## action, and the branch's own addressing. **No progress pair, no value, no
## difficulty, no win/loss outcome, and no unit list** is expressible, so there is
## no parameter through which a client could send one.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ------------------------------------------------------------------- keys --
## The three committed private-state keys a quest occupies and the four map keys,
## in the order the projection reports the seven fields.
const KEY_GOALS := "goals"
const KEY_RANKS := "questsRank"
const KEY_QUEST_VARS := "currentQuestVars"
const KEY_QUEST_TIMES := "questTimes"
const KEY_MISSION := "idCurrentMission"
const KEY_LAST_CHAPTER := "timestampLastChapter"
const KEY_UNLOCKED_INDEX := "unlockedQuestIndex"
const PRIVATE_KEYS := [KEY_GOALS, KEY_RANKS, KEY_UNLOCKED_INDEX]
const MAP_KEYS := [KEY_QUEST_VARS, KEY_QUEST_TIMES, KEY_MISSION, KEY_LAST_CHAPTER]
const QUEST_FIELDS := [KEY_GOALS, KEY_RANKS, KEY_QUEST_VARS, KEY_QUEST_TIMES,
	KEY_MISSION, KEY_LAST_CHAPTER, KEY_UNLOCKED_INDEX]

# -------------------------------------------------------------- commands --
const SET_GOALS_COMMAND := "set_goals"
const COMPLETE_GOAL_COMMAND := "complete_goal"
const SET_QUEST_VAR_COMMAND := "set_quest_var"
const COLLECT_MISSION_COMMAND := "collect_mission"
const ADMIN_SET_QUEST_RANK_COMMAND := "admin_set_quest_rank"
const END_QUEST_COMMAND := "end_quest"
const QUEST_COMMANDS := [SET_GOALS_COMMAND, COMPLETE_GOAL_COMMAND,
	SET_QUEST_VAR_COMMAND, COLLECT_MISSION_COMMAND,
	ADMIN_SET_QUEST_RANK_COMMAND, END_QUEST_COMMAND]
const FAST_FORWARD_COMMAND := "fast_forward"

## The closed action vocabulary: the client names an OUTCOME and the service
## chooses the legacy command. `fast_forward` is deliberately **absent** (design D9).
const ACTION_SET_GOAL := "set_goal"
const ACTION_COMPLETE_GOAL := "complete_goal"
const ACTION_SET_QUEST_VAR := "set_quest_var"
const ACTION_COLLECT_MISSION := "collect_mission"
const ACTION_SET_QUEST_RANK := "set_quest_rank"
const ACTION_END_QUEST := "end_quest"
const ACTIONS := [ACTION_SET_GOAL, ACTION_COMPLETE_GOAL, ACTION_SET_QUEST_VAR,
	ACTION_COLLECT_MISSION, ACTION_SET_QUEST_RANK, ACTION_END_QUEST]
const ACTION_COMMANDS := {
	ACTION_SET_GOAL: SET_GOALS_COMMAND,
	ACTION_COMPLETE_GOAL: COMPLETE_GOAL_COMMAND,
	ACTION_SET_QUEST_VAR: SET_QUEST_VAR_COMMAND,
	ACTION_COLLECT_MISSION: COLLECT_MISSION_COMMAND,
	ACTION_SET_QUEST_RANK: ADMIN_SET_QUEST_RANK_COMMAND,
	ACTION_END_QUEST: END_QUEST_COMMAND,
}

## How each action is addressed — the ONE value a client may name, because it is
## the branch's own subject and never an outcome.
const ACTION_ADDRESSING := {
	ACTION_SET_GOAL: "goal index",
	ACTION_COMPLETE_GOAL: "goal index",
	ACTION_SET_QUEST_VAR: "quest-variable key",
	ACTION_COLLECT_MISSION: "mission identifier",
	ACTION_SET_QUEST_RANK: "rank index",
	ACTION_END_QUEST: "quest identifier",
}

## The client-sent request key carrying each action's addressing, and its JSON
## type. The intent body is exactly `user_id` + `action` + **this** key, so the
## key is **per-action**: the service reads the addressing out of the key that
## belongs to the branch it is about to dispatch, which is why the wire spelling
## differs per action (`goal_index`, `key`, `mission`, `quest_index`,
## `quest_id`) while the *typed* layer stays one positional parameter.
##
## **This table is the wire contract and it was WRONG once.** The transport first
## sent every action's addressing under a single fixed `addressing` key, which
## the hermetic double accepted — because the double consumed `intent_body()`
## rather than the route — so all 1047 hermetic checks passed while the live
## phase against the real service answered `missing_goal_index`. The suite now
## pins the body's third key to this table (see `_check_intents`).
const ACTION_ADDRESSING_KEY := {
	ACTION_SET_GOAL: "goal_index",
	ACTION_COMPLETE_GOAL: "goal_index",
	ACTION_SET_QUEST_VAR: "key",
	ACTION_COLLECT_MISSION: "mission",
	ACTION_SET_QUEST_RANK: "quest_index",
	ACTION_END_QUEST: "quest_id",
}
## `true` when the addressing is an integer, `false` when it is a string key.
const ACTION_ADDRESSING_IS_INTEGER := {
	ACTION_SET_GOAL: true,
	ACTION_COMPLETE_GOAL: true,
	ACTION_SET_QUEST_VAR: false,
	ACTION_COLLECT_MISSION: true,
	ACTION_SET_QUEST_RANK: true,
	ACTION_END_QUEST: true,
}

## The endpoint the typed operation drives, named here as data so the transport
## itself stays inside the legacy-v0 implementation (the project-scope suite
## enforces that boundary).
const QUEST_PATH := "/v0/quests"

## The FIXED part of every intent body, whatever the action: the save identity
## and the closed action. Only the third key varies.
const INTENT_FIXED_KEYS := ["user_id", "action"]

## The key the addressing travels under when `action` is **outside** the closed
## vocabulary, so a body formed for an unknown action is still exactly three keys
## long — and the service answers `invalid_action` for it before it ever looks at
## the addressing. It is a fallback, never a wire spelling for a real action.
const INTENT_ADDRESSING_KEY := "addressing"

## The exact key COUNT `intent_body()` produces: two fixed keys plus ONE
## addressing key. This constant IS the structural form of the "no client value
## is trusted" claim, and the operation's parameter count is asserted equal to it.
const INTENT_KEY_COUNT := 3

## Every key a client might attach that the service **ignores**, recorded so the
## refusal is enumerable rather than editorial.
const INTENT_IGNORED_KEYS := [
	"progress", "visited", "currentStep", "value", "difficulty", "win",
	"duration", "map", "units", "lost", "voluntary_end", "reward", "price",
	"cost", "resources_changed", "vector", "seconds", "fast_forward",
	"complete", "completed", "unlocked_quest_index", "unlockedQuestIndex",
]

# ----------------------------------------------------------- the branches --
## The six recorded branch contracts, as DATA. The absence of validation is a
## field of every record because it is the fact that most needs stating
## (design D4/D5).
const BRANCHES := [
	{
		"command": SET_GOALS_COMMAND,
		"action": ACTION_SET_GOAL,
		"source": "command.py:68-74",
		"args": ["goal index", "json progress pair"],
		"reads": ["args[0]", "args[1]", "json.loads", "the committed title"],
		"writes": ["privateState[goals][goal_index]"],
		"delegates_to": "engine.py:96-100 (engine.set_goals)",
		"mutates": true,
		"effect": "the addressed goal's entry is REPLACED by the progress pair, "
			+ "and the goals list is grown ON DEMAND with None padding",
		"grows_list_on_demand": true,
		"upper_bound": null,
		"validation": "none: no bounds check, no clamp, no membership test, no "
			+ "exception guard, and no existence check. A goal index of 500 "
			+ "appends 350 entries from one client-sent identifier, and that "
			+ "absence is reproduced, not closed",
	},
	{
		"command": COMPLETE_GOAL_COMMAND,
		"action": ACTION_COMPLETE_GOAL,
		"source": "command.py:76-79",
		"args": ["goal index"],
		"reads": ["args[0]", "the committed title"],
		"writes": [],
		"delegates_to": null,
		"mutates": false,
		"effect": "NOTHING AT ALL: the branch resolves the committed title, "
			+ "prints it, and returns. There is no completion flag, no ledger, "
			+ "and no reward",
		"grows_list_on_demand": false,
		"upper_bound": null,
		"validation": "none: no bounds check, no clamp, no membership test, and "
			+ "no existence check. get_attribute_from_goal_id calls int(id) on "
			+ "the client value with no guard, so a non-numeric goal id RAISES "
			+ "rather than refusing - a legacy crash path, recorded, not "
			+ "reproduced",
	},
	{
		"command": SET_QUEST_VAR_COMMAND,
		"action": ACTION_SET_QUEST_VAR,
		"source": "command.py:87-117",
		"args": ["key", "value"],
		"reads": ["args[0]", "args[1]", "map[currentQuestVars]"],
		"writes": ["map[currentQuestVars][key]",
			"map[idCurrentMission] (the `id` alias only)"],
		"delegates_to": null,
		"mutates": true,
		"effect": "ANY client-supplied key is persisted into the quest-variable "
			+ "map, which is SELF-HEALED from the corpus's recorded None to an "
			+ "empty dict first (command.py:113-114); the key `id` ALSO "
			+ "overwrites the current mission identifier (command.py:110-111)",
		"grows_list_on_demand": false,
		"upper_bound": null,
		"validation": "NONE beyond the ONE key the branch itself ignores: "
			+ QUEST_VAR_IGNORED_KEY + ". There is no membership test against the "
			+ "eight keys the branch's own comment enumerates, so an invented key "
			+ "is accepted and persisted",
	},
	{
		"command": COLLECT_MISSION_COMMAND,
		"action": ACTION_COLLECT_MISSION,
		"source": "command.py:430-442",
		"args": ["mission identifier"],
		"reads": ["args[0]"],
		"writes": ["map[idCurrentMission]", "map[timestampLastChapter]",
			"map[currentQuestVars]"],
		"delegates_to": null,
		"mutates": true,
		"effect": "the current mission identifier is written as a STRING "
			+ "(command.py:438) where the committed corpus records an INTEGER 0; "
			+ "the last-chapter instant is stamped with the wall clock; and the "
			+ "quest-variable map is CLEARED to an empty dict (command.py:440)",
		"grows_list_on_demand": false,
		"upper_bound": null,
		"validation": "the ONLY guard is `if next_mission > 99: next_mission = "
			+ "1` - a WRAP, not a rejection. No bounds check, no clamp, no "
			+ "membership test, and no existence check otherwise",
	},
	{
		"command": ADMIN_SET_QUEST_RANK_COMMAND,
		"action": ACTION_SET_QUEST_RANK,
		"source": "command.py:745-750",
		"args": ["rank index", "difficulty"],
		"reads": ["args[0]", "args[1]"],
		"writes": ["privateState[questsRank][str(index)]"],
		"delegates_to": null,
		"mutates": true,
		"effect": "the addressed rank's difficulty is written under the "
			+ "STRINGIFIED index, and nothing else. Both values are client-sent "
			+ "in legacy; the service derives the difficulty",
		"grows_list_on_demand": false,
		"upper_bound": null,
		"validation": "none: no bounds check, no clamp, no membership test, and "
			+ "no existence check on either side of the assignment",
	},
	{
		"command": END_QUEST_COMMAND,
		"action": ACTION_END_QUEST,
		"source": "command.py:752-806",
		"args": ["json blob"],
		"reads": ["args[0]", "json.loads", "win", "duration", "units", "map",
			"difficulty", "voluntary_end", "quest_id"],
		"writes": ["map[questTimes][str(quest_id)]",
			"and, in LEGACY ONLY, placed rows via map_lose_item - REFUSED here"],
		"delegates_to": "engine.map_lose_item (engine.py:215-228) in LEGACY ONLY",
		"mutates": true,
		"effect": "the quest-time map gains one entry under the STRINGIFIED quest "
			+ "id. The client-computed destruction count is NOT reproduced: the "
			+ "service derives the blob with an EMPTY unit list, so no placed row "
			+ "is touched",
		"grows_list_on_demand": false,
		"upper_bound": null,
		"validation": "only `if not quest_id: return` (command.py:798-800), and "
			+ "that check runs AFTER the destruction loop. `difficulty` is the "
			+ "ONLY clamped value in the branch: max(1, min(3, ...))",
		"destruction": "REFUSED",
		"difficulty_clamp": "max(1, min(3, ...)) at command.py:782",
	},
]

const BRANCH_COUNT := 6

## The one branch that mutates nothing at all (design D3).
const NO_OP_COMMAND := COMPLETE_GOAL_COMMAND

# ------------------------------------------------------------- the writers --
## Every writer of quest state. Six are dispatcher branches; the SEVENTH is
## `fast_forward` and is offered by **no** action (design D9).
const WRITERS := [
	{
		"writer": "command:" + SET_GOALS_COMMAND,
		"source": "command.py:68-74 delegating to engine.py:96-100",
		"kind": "dispatcher-branch",
		"fields_written": [KEY_GOALS],
		"client_writable": false,
	},
	{
		"writer": "command:" + COMPLETE_GOAL_COMMAND,
		"source": "command.py:76-79",
		"kind": "dispatcher-branch",
		"fields_written": [],
		"client_writable": false,
		"note": "this branch WRITES NOTHING AT ALL - recorded so the writer "
			+ "inventory is complete rather than flattering",
	},
	{
		"writer": "command:" + SET_QUEST_VAR_COMMAND,
		"source": "command.py:87-117",
		"kind": "dispatcher-branch",
		"fields_written": [KEY_QUEST_VARS, KEY_MISSION],
		"client_writable": false,
	},
	{
		"writer": "command:" + COLLECT_MISSION_COMMAND,
		"source": "command.py:430-442",
		"kind": "dispatcher-branch",
		"fields_written": [KEY_MISSION, KEY_LAST_CHAPTER, KEY_QUEST_VARS],
		"client_writable": false,
	},
	{
		"writer": "command:" + ADMIN_SET_QUEST_RANK_COMMAND,
		"source": "command.py:745-750",
		"kind": "dispatcher-branch",
		"fields_written": [KEY_RANKS],
		"client_writable": false,
	},
	{
		"writer": "command:" + END_QUEST_COMMAND,
		"source": "command.py:752-806 (write at 802)",
		"kind": "dispatcher-branch",
		"fields_written": [KEY_QUEST_TIMES],
		"client_writable": false,
	},
	{
		"writer": "command:" + FAST_FORWARD_COMMAND,
		"source": "command.py:942-944 (questTimes) and command.py:911 "
			+ "(timestampLastChapter)",
		"kind": "engine-side decrement inside a dispatcher branch",
		"fields_written": [KEY_QUEST_TIMES, KEY_LAST_CHAPTER],
		"client_writable": true,
	},
]

const WRITER_COUNT := 7
const WRITER_FAST_FORWARD := "command:" + FAST_FORWARD_COMMAND

const FAST_FORWARD_CONTRACT := ("RECORDED AND IMPLEMENTED NOT AT ALL. Quest state "
	+ "has SEVEN writers: the six branches and fast_forward, which is NOT a quest "
	+ "branch. fast_forward (command.py:905) subtracts a CLIENT-SUPPLIED number of "
	+ "seconds (`seconds = args[0]`, command.py:906) from every questTimes entry "
	+ "(command.py:942-944) and from timestampLastChapter (command.py:911), both "
	+ "clamped at zero. That makes quest timing CLIENT-WRITABLE, and for the same "
	+ "reason the research instant is: NO legacy branch reads a quest instant to "
	+ "decide anything. NO fast-forward operation is delivered by the client "
	+ "facade, by either GameApi implementation, by this flow, or by any route, and "
	+ "no elapsed-time, remaining-time, readiness, or completion behaviour is "
	+ "derived from any quest instant anywhere in this repository (design D9)")

## The committed save-migration initialization of the quest-time map: a
## **migration path**, not gameplay (design D9).
const MIGRATION := {
	"field": KEY_QUEST_TIMES,
	"where": "version.py:38-44",
	"kind": "save-migration",
	"is_gameplay": false,
	"effect": "if the map carries no questTimes it is set to None, and if it is "
		+ "then not a dict it is coerced to {} and the 'quest fix' is printed",
	"note": "RECORDED AS A MIGRATION PATH, NOT AS QUEST BEHAVIOUR. version.py "
		+ "runs once per save load and repairs the quest-time map's SHAPE. It "
		+ "resolves no goal, advances no chapter, awards nothing, and reads no "
		+ "quest content, so counting it as a seventh quest behaviour would "
		+ "overstate what the migration does",
}

# --------------------------------------------------- the recorded absences --
const NO_REWARD := ("NO QUEST REWARD IS PAID AND NONE EXISTS. MEASURED as QUOTED "
	+ "occurrences across the seven legacy modules, only two committed quest "
	+ "fields are read by anything: `id` (8 occurrences: command.py 2, "
	+ "get_game_config.py 6) and `title` (2 occurrences, both `print` statements). "
	+ "`reward` has ZERO, and it is committed on all 91 entries UNIFORMLY the value "
	+ "10 - so it carries no information even if it were read. A line that derived "
	+ "a payout from a uniform 10 would fabricate a uniform payout that is not a "
	+ "payout at all, and NO delivered code identifier or computation is named "
	+ "after the reward field, which is what makes the 'reported, never used' claim "
	+ "mechanical rather than editorial (design D6)")

const NO_RESOURCE_MOVE := ("NO STORED RESOURCE MOVES ON ANY QUEST ACTION. "
	+ "do_command applies the request's per-command resource vector BEFORE dispatch "
	+ "(command.py:40; engine.py:251-271) as max(current + delta, 0) per resource, "
	+ "so any price a client attached would be a client-trusted mint or burn. The "
	+ "derived vector is therefore NEUTRAL and every action's post-execution proof "
	+ "requires that EVERY stored resource - all seven of them, compared over the "
	+ "complete set rather than a selected subset - be UNCHANGED (design D6)")

const NO_COMPLETION := ("NO COMPLETION STATE EXISTS, AND THE SUITE ASSERTS THE "
	+ "ABSENCE STRUCTURALLY. complete_goal writes NOTHING AT ALL (command.py:76-79): "
	+ "it resolves the committed title, prints it, and returns. So there is no "
	+ "completion flag, no completion ledger, no completion accessor, and no reward "
	+ "for finishing a goal - a goal 'completes' by being narrated in a print "
	+ "statement. The service executes the real branch and its post-execution proof "
	+ "requires the WHOLE quest state to be byte-identical, and this module's whole "
	+ "function inventory is pinned, so a mark_goal_complete or is_goal_complete "
	+ "helper fails the run wherever it is added (design D3)")

const NO_BOUNDS := ("NO BOUND IS ADDED TO THE ON-DEMAND GOALS LIST. engine.set_goals "
	+ "grows the list on demand (engine.py:98-99): `while goal >= len(goals): "
	+ "goals.append(None)`. There is no upper bound, so a client-sent goal index of "
	+ "500 appends 350 entries from ONE identifier, and that absence is reproduced "
	+ "rather than closed - a bound the legacy server does not have would make this "
	+ "client stricter in the unexamined direction, which is a parity break in the "
	+ "opposite sense from the one this line refuses. The recorded absence is a "
	+ "Server v1 / M13 gap, NOT permission to invent a limit (design D4)")

const NO_MEMBERSHIP := ("NO MEMBERSHIP TEST IS ADDED TO THE QUEST-VARIABLE WRITER. "
	+ "The legacy branch accepts ANY client-invented key (command.py:116) against the "
	+ "eight keys its own comment enumerates (command.py:97-106), so inventing a "
	+ "closed set of eight would reject keys the legacy server happily persisted. "
	+ "The eight are recorded as CONTENT, what the client sends is accepted, and "
	+ "exactly ONE key is refused - idSimpleChapter - because that is the one key the "
	+ "legacy branch ITSELF ignores (command.py:91-95), which is a recorded behaviour "
	+ "rather than an absence (design D5)")

const NO_ELAPSED := ("NO ELAPSED-TIME BEHAVIOUR IS DERIVED FROM ANY QUEST INSTANT. "
	+ "No legacy branch reads timestampLastChapter or any questTimes entry to decide "
	+ "anything: the quest-time map's six sites are the branch write at "
	+ "command.py:802, the fast_forward write at command.py:942-944, and four "
	+ "save-migration lines at version.py:39-43. So there is no chapter "
	+ "duration, no remaining chapter time, no cooldown, and no readiness rule to "
	+ "reproduce, and this projection computes none of them (design D9)")

## The six refusal families, each with its non-empty recorded reason. They are
## stated as requirements (design D3/D4/D5/D6/D9), not as omissions.
const REFUSALS := [
	{"refusal": "no_reward", "implemented": false, "reason": NO_REWARD},
	{"refusal": "no_resource_move", "implemented": false,
		"reason": NO_RESOURCE_MOVE},
	{"refusal": "no_completion", "implemented": false, "reason": NO_COMPLETION},
	{"refusal": "no_bounds", "implemented": false, "reason": NO_BOUNDS},
	{"refusal": "no_membership", "implemented": false, "reason": NO_MEMBERSHIP},
	{"refusal": "no_elapsed", "implemented": false, "reason": NO_ELAPSED},
]
const REFUSAL_COUNT := 6

## The refused destruction, as its own recorded family so it cannot be lost
## inside the six above.
const REFUSED_DESTRUCTION := {
	"refusal": "destruction_count",
	"implemented": false,
	"command": END_QUEST_COMMAND,
	"status": "DIVERGENCE, NOT PARITY",
	"legacy_behaviour": "destroys placed rows via map_lose_item "
		+ "(command.py:796) using the CLIENT-COMPUTED count "
		+ "max(0, unit[2] - unit[3]) (command.py:792)",
	"modern_behaviour": "destroys nothing: the derived blob carries an EMPTY LIST "
		+ "of units, so the destruction loop iterates zero times, map_lose_item is "
		+ "never reached, and every placed row is left byte-identical over the "
		+ "COMPLETE items mapping",
	"reason": "THE DESTRUCTION COUNT IS REFUSED, AND THE DIFFERENCE FROM THE LEGACY "
		+ "SERVER IS A DIVERGENCE, NOT PARITY. Reproducing a client-dictated "
		+ "destruction is exactly the anti-pattern AGENTS.md names as Bad, so this "
		+ "line derives the end_quest blob server-side with an EMPTY unit list and "
		+ "proves the refusal over the whole placed-row set. This is the single "
		+ "place in this repository where the modern service deliberately does NOT "
		+ "reproduce legacy behaviour, and it is recorded here rather than left for "
		+ "a reader to infer (design D2)",
}

## The helpers this projection deliberately does **NOT** provide, with the reason
## each is absent. Every entry is a completion, remaining-time, price, progress,
## or unlock rule the legacy server does not have to reproduce, so adding one would
## compute an invented answer - and the suite asserts this module's whole function
## inventory, so one cannot appear unnoticed (tasks 2.2 and 4.4).
const NON_DERIVATION := [
	{"helper": "mark_goal_complete", "absent_because":
		"complete_goal writes NOTHING AT ALL, so there is no completion for a "
		+ "flag to record (design D3)"},
	{"helper": "is_goal_complete", "absent_because":
		"nothing anywhere reads the goals list to decide anything, so no "
		+ "completion test exists to reproduce (design D3)"},
	{"helper": "quest_reward", "absent_because":
		"the committed reward field has ZERO legacy consumers and is UNIFORMLY 10 "
		+ "on all 91 entries, so any amount computed here would fabricate an "
		+ "economy from a constant (design D6)"},
	{"helper": "quest_price", "absent_because":
		"no committed quest cost exists, and a price would be a client-sent "
		+ "resource delta because do_command applies the vector before the branch"},
	{"helper": "quest_progress_ratio", "absent_because":
		"the stored progress pair is never read by any legacy module and there is "
		+ "no committed total to divide by"},
	{"helper": "quest_remaining_time", "absent_because":
		"no legacy branch reads a quest instant, so there is no elapsed-time rule "
		+ "and no committed duration to subtract (design D9)"},
	{"helper": "quest_ready", "absent_because":
		"the chapter instant is reported verbatim and nothing derives a decision "
		+ "from it"},
	{"helper": "fast_forward", "absent_because":
		"the quest-time map's seventh writer subtracts a CLIENT-SUPPLIED number of "
		+ "seconds and is recorded, not delivered: no action and no route derives "
		+ "it (design D9)"},
]

## The measured content inventory. Every consumer count is MEASURED as quoted
## occurrences over the seven legacy modules; a discrepancy fails the suite.
const CONTENT_FIELD_CONSUMERS := [
	{"field": "id", "quoted_occurrences": 8,
		"where": ["command.py", "get_game_config.py"], "used": true},
	{"field": "title", "quoted_occurrences": 2, "where": ["command.py"],
		"used": true,
		"note": "both occurrences are `print` statements; the title is resolved "
			+ "only to be narrated"},
	{"field": "hint", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "description", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "reward", "quoted_occurrences": 0, "where": [], "used": false,
		"note": "UNIFORMLY 10 on all 91 committed entries and read by NOTHING, so "
			+ "it carries no information even if it were read"},
	{"field": "kind", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "legacy_id", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "source_file", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "source_layer", "quoted_occurrences": 0, "where": [], "used": false},
	{"field": "content_version", "quoted_occurrences": 0, "where": [],
		"used": false},
]
const CONTENT_FIELD_COUNT := 10
const CONTENT_FIELDS_READ := ["id", "title"]
const CONTENT_FIELDS_UNREAD := ["legacy_id", "kind", "source_file",
	"source_layer", "content_version", "hint", "description", "reward"]
const COMMITTED_QUEST_ENTRIES := 91
const COMMITTED_REWARD_VALUE := 10
const COMMITTED_ID_MIN := 1
const COMMITTED_ID_MAX := 91
const COMMITTED_GOAL_INDEX_SOURCE := "get_game_config.py:142-150"
const REWARD_FIELD_ABSENT := ("NO DELIVERED CODE IDENTIFIER OR COMPUTATION IS NAMED "
	+ "AFTER THE REWARD FIELD. The field is committed on all 91 entries as the "
	+ "UNIFORM value 10 and read by NOTHING, so a later reader cannot mistake a "
	+ "reported constant for a derived payout. The paid amount this contract reports "
	+ "is named without the committed field's own name, and the suite asserts this "
	+ "over the module's declarations and its whole function inventory (design D6)")
const CONTENT_RECORD_NOTE := ("REPORTED AND NEVER USED. The committed quest content "
	+ "is read by the legacy server for exactly two things: an identifier lookup "
	+ "(get_game_config.py:142 and 144-146) and a title to print (command.py:74 and "
	+ "79). Nothing else. So the committed content is used ONLY to resolve an "
	+ "identifier and read its title, and NO reward, cost, requirement, schedule, or "
	+ "completion rule is derived from it. `hint` and `description` exist to be "
	+ "DISPLAYED BY THE FLASH CLIENT and are read by no server branch; MEASURED, "
	+ "every one of the 91 committed `hint` values is EMPTY and every `description` "
	+ "is non-empty (design D6)")

## The zero-consumer fact, following the `resurrectable` precedent (design D7).
const ZERO_CONSUMER_FIELDS := [
	{
		"field": "privateState[unlockedQuestIndex]",
		"quoted_sites": 0,
		"written_by": [],
		"read_by": [],
		"consequence": "committed player state with ZERO legacy consumers. It is "
			+ "projected as content and consumed by nothing, and NO delivered "
			+ "operation writes it",
	},
]

## The dead-hero ledger door this line touches (design D10).
const LEDGER_DOOR := {
	"door": "map_lose_item",
	"source": "engine.py:215-228",
	"calls_helper_at": "engine.py:223 (push_dead_unit)",
	"is_a_dispatcher_branch": false,
	"callers": ["command.py:796 (end_quest)", "command.py:872 (end_attack)"],
	"modern_behaviour": "the quest-side caller is REFUSED here: the derived "
		+ "end_quest blob carries an empty unit list, so map_lose_item is never "
		+ "reached through this endpoint and no dead-hero ledger entry is written "
		+ "by a quest action",
	"status": "the quest path's reach into the dead-hero ledger is recorded, "
		+ "REFUSED, and asserted byte-identical on the whole placed-row set",
}

# ------------------------------------------------- the recorded absences of shape --
## The one key the legacy `set_quest_var` branch EXPLICITLY ignores.
const QUEST_VAR_IGNORED_KEY := "idSimpleChapter"
## The key that ALSO aliases the current mission identifier.
const QUEST_VAR_ALIAS_KEY := "id"
## The eight keys the branch's OWN comment enumerates - recorded as CONTENT and
## enforced **nowhere** (design D5).
const QUEST_VAR_COMMENT_KEYS := ["id", "spawned", "ended", "visited",
	"activators", "boss", "treasure", "killed"]
const QUEST_VAR_COMMENT_NOTE := ("RECORDED AS CONTENT AND NEVER ENFORCED, SO THE "
	+ "ACCEPTED SET IS UNBOUNDED. The legacy branch's own comment "
	+ "(command.py:97-106) enumerates these eight keys, and there is NO membership "
	+ "test anywhere in it. Inventing a closed set of eight would reject keys the "
	+ "legacy server happily stored, which would make this client STRICTER than "
	+ "legacy in the unexamined direction (design D5)")
const MISSION_WRAP_BOUND := 99
const MISSION_WRAP_TARGET := 1
const MISSION_WRAP_NOTE := ("A WRAP, NOT A REJECTION. The branch's only guard is `if "
	+ "next_mission > 99: next_mission = 1` (command.py:432-436), and the source's "
	+ "own comment admits uncertainty past chapter 99")

# --------------------------------------------- the derived client constants --
## The progress pair the service writes for `set_goals`, the marker it writes for
## a quest variable, and the floor of the branch's own difficulty clamp. All three
## are **service-derived** and never client-supplied; the client mirrors them only
## so the offline double produces the same typed shape.
const DERIVED_PROGRESS := [0, 0]
const DERIVED_QUEST_VALUE := true
const DERIVED_DIFFICULTY := 1
## The floor and ceiling of the one clamp any of the six branches contains.
const DIFFICULTY_MIN := 1
const DIFFICULTY_MAX := 3
const REWARD_PAID := 0
const DERIVED_WIN := true
const DERIVED_VOLUNTARY_END := true
const DERIVED_DURATION := 0
const DERIVED_MAP := 0

# ------------------------------------------------- the refusal reasons --
## The named reasons the projection can report for a state it cannot read. An
## unresolvable state is REPORTED with its recorded shape intact and is never
## defaulted to an empty value presented as a resolved one.
const REASON_ABSENT_STATE := "absent_quest_state"
const REASON_NON_OBJECT := "non_object_state"
const REASON_NOT_A_LIST := "non_list_goals"
const REASON_NON_INTEGER := "non_integer_unlocked_index"
const REASON_WRONG_MISSION := "non_integer_or_string_mission"
const REASON_WRONG_CHAPTER := "non_integer_last_chapter"
const REASON_NOT_AN_OBJECT := "non_object_quest_var_map"

## Every structural refusal reason, closed so a caller can enumerate them.
const PROJECTION_REASONS := [
	REASON_ABSENT_STATE, REASON_NON_OBJECT, REASON_NOT_A_LIST,
	REASON_NON_INTEGER, REASON_WRONG_MISSION, REASON_WRONG_CHAPTER,
	REASON_NOT_AN_OBJECT,
]

## The recorded `null` quest-variable field is a legitimate committed state and is
## reported as a recorded null. It is **not** a refusal, so it is deliberately
## absent from `PROJECTION_REASONS` and carried as its own flag instead.
const REASON_NULL_QUEST_VARS := "recorded_null_quest_vars"

## The committed corpus's own quest state, pinned so a corpus drift is a visible
## mismatch rather than a silently different report.
const CORPUS_GOALS_LENGTH := 151
const CORPUS_GOALS_ALL_NONE := true
const CORPUS_RANKS := {}
const CORPUS_UNLOCKED_INDEX := 0
const CORPUS_QUEST_VARS_IS_NULL := true
const CORPUS_QUEST_TIMES := {}
const CORPUS_MISSION := 0
const CORPUS_LAST_CHAPTER := 0
const CORPUS_PLACEMENTS := 40
const CORPUS_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}
## The executed-legacy fixture's six recorded branches.
const CAPTURED_BRANCHES := 6


## The projected quest state: all seven fields, verbatim.
##
## Read-only by construction — no setter, no mutating method, no writable public
## field. Every reader returns a committed value or a fresh copy, and reading it
## can change neither the save it was parsed from nor any committed content.
class QuestStateView:
	extends RefCounted
	var _resolvable := false
	var _reason := ""
	var _error := ""
	var _goals: Array = []
	var _ranks: Dictionary = {}
	var _quest_vars_is_null := true
	var _quest_vars: Dictionary = {}
	var _quest_times: Dictionary = {}
	var _mission: Variant = null
	var _last_chapter: Variant = null
	var _unlocked_index: Variant = null
	var _recorded: Variant = null

	## Whether the state resolved. `false` means it is reported **with its
	## recorded state intact**, never defaulted to an empty value.
	func resolvable() -> bool:
		return _resolvable

	## The named reason an unresolvable state was refused, or "" while it resolves.
	func reason() -> String:
		return _reason

	## The refusal message, naming the field and the value that failed.
	func error() -> String:
		return _error

	## The goals list, verbatim, as a fresh copy. Its length is **not** constrained
	## by this projection: the on-demand growth is a legacy behaviour.
	func goals() -> Array:
		return (_goals as Array).duplicate()

	## How many goals entries are the recorded null. Reported, never computed from.
	func goals_null_entries() -> int:
		var count := 0
		for entry: Variant in _goals:
			if entry == null:
				count += 1
		return count

	## The rank map, verbatim, as a fresh copy.
	func ranks() -> Dictionary:
		return (_ranks as Dictionary).duplicate(true)

	## Whether the quest-variable map is the committed corpus's recorded **null**.
	## `true` here is a legitimate recorded state, never a defaulted empty map.
	func quest_vars_is_null() -> bool:
		return _quest_vars_is_null

	## The quest-variable map, verbatim, as a fresh copy. An **empty** map is
	## returned when the recorded state is a null — and `quest_vars_is_null()` is
	## what distinguishes the two, so an empty map can never stand in for a
	## recorded null without the flag saying so.
	func quest_vars() -> Dictionary:
		return (_quest_vars as Dictionary).duplicate(true)

	## The quest-time map, verbatim, as a fresh copy.
	func quest_times() -> Dictionary:
		return (_quest_times as Dictionary).duplicate(true)

	## The current mission identifier, verbatim: an **integer** in the committed
	## corpus and a **string** after `collect_mission`. Both are reported as
	## recorded; neither is normalized into the other (design D8).
	func mission() -> Variant:
		return _mission

	func mission_is_string() -> bool:
		return _mission is String

	## The last-chapter instant, verbatim. **No elapsed-time rule is computed from
	## it**, so reading it implies no timer and no readiness.
	func last_chapter() -> Variant:
		return _last_chapter

	## The unlocked-quest index, verbatim. It has **zero** legacy consumers and is
	## **never written** by any delivered operation (design D7).
	func unlocked_index() -> Variant:
		return _unlocked_index

	## The state's **recorded** shape, whatever it is. It travels beside the
	## refusal so a reader can see exactly what the save held.
	func recorded() -> Variant:
		return _recorded

	## The whole projection as one fresh record.
	func fields() -> Dictionary:
		return {
			"resolvable": _resolvable,
			"reason": _reason,
			"error": _error,
			"goals": goals(),
			"goals_null_entries": goals_null_entries(),
			"ranks": ranks(),
			"quest_vars": quest_vars(),
			"quest_vars_is_null": _quest_vars_is_null,
			"quest_times": quest_times(),
			"mission": _mission,
			"mission_is_string": mission_is_string(),
			"last_chapter": _last_chapter,
			"unlocked_index": _unlocked_index,
			"verbatim": true,
		}


# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------


## Whether `value` names one of the six closed quest actions. The set is
## **closed**: `fast_forward` is deliberately absent (design D9).
static func is_action(value: Variant) -> bool:
	return (value is String) and ACTIONS.has(value)


## Whether `value` is a strict integer. `bool` is refused explicitly, because
## `isinstance(true, int)` is false but a transported boolean would otherwise
## read as the integers 0 and 1.
static func is_strict_int(value: Variant) -> bool:
	if value is bool:
		return false
	if value is int:
		return true
	if value is float:
		var number := float(value)
		return number == floor(number) and is_finite(number) \
			and absf(number) <= 9007199254740992.0
	return false


## Whether `value` is a goal index the on-demand list can address: a
## **non-negative** integer. The legacy helper has **no upper bound**, so a large
## index is accepted here too and the unbounded growth is reproduced rather than
## closed (design D4). A **negative** index is refused structurally, because
## Python would otherwise write `goals[-1]`, aliasing the LAST entry.
static func is_goal_index(value: Variant) -> bool:
	if not is_strict_int(value):
		return false
	var index := int(value)
	return index == floor(float(index)) and index >= 0


## Whether `value` is a quest-variable key the branch would persist: any
## non-empty string. **No membership test** against the eight keys the branch's
## own comment enumerates (design D5).
static func is_quest_var_key(value: Variant) -> bool:
	return (value is String) and str(value).strip_edges() != ""


## Whether `value` is a mission identifier: any strict integer, **including** one
## above the wrap bound, because the branch WRAPS such a value rather than
## rejecting it.
static func is_mission(value: Variant) -> bool:
	return is_strict_int(value)


## Whether `value` is a rank index: any strict integer, **with no bound in either
## direction**. The branch writes `privateState["questsRank"][str(index)]`, so
## even a negative index is just a distinct string key and nothing is aliased.
static func is_quest_rank_index(value: Variant) -> bool:
	return is_strict_int(value)


## Whether `value` is a quest identifier: any strict integer, **with no bound**,
## because the branch writes `map["questTimes"][str(quest_id)]`.
static func is_quest_id(value: Variant) -> bool:
	return is_strict_int(value)


## The request key `action`'s addressing travels under on the wire, read from
## :data:`ACTION_ADDRESSING_KEY`. An `action` outside the closed vocabulary
## falls back to :data:`INTENT_ADDRESSING_KEY` so the body stays exactly
## :data:`INTENT_KEY_COUNT` keys long; the service then answers `invalid_action`
## and never reads the addressing. **This is the ONE place the wire spelling is
## decided**, which is why the transport reads it instead of hardcoding it.
static func wire_key(action: Variant) -> String:
	var table: Variant = ACTION_ADDRESSING_KEY
	if (table is Dictionary) and (table as Dictionary).has(str(action)):
		return str((table as Dictionary)[str(action)])
	return INTENT_ADDRESSING_KEY


## Whether `addressing` is valid for `action`. This is the ONLY client-side gate,
## and it is a **structural** one: the endpoint must be able to address its own
## state, and a goal index outside the addressed range is not an authority
## question.
static func is_addressing(action: Variant, addressing: Variant) -> bool:
	if not is_action(action):
		return false
	var action_text := str(action)
	if action_text == ACTION_SET_GOAL or action_text == ACTION_COMPLETE_GOAL:
		return is_goal_index(addressing)
	if action_text == ACTION_SET_QUEST_VAR:
		return is_quest_var_key(addressing)
	if action_text == ACTION_COLLECT_MISSION:
		return is_mission(addressing)
	if action_text == ACTION_SET_QUEST_RANK:
		return is_quest_rank_index(addressing)
	return is_quest_id(addressing)


## The mission identifier the branch will actually store: the wrap, not a
## rejection.
static func wrap_mission(value: Variant) -> int:
	var mission := int(value)
	return MISSION_WRAP_TARGET if mission > MISSION_WRAP_BOUND else mission


## The one clamp any of the six branches contains: `end_quest` clamps its
## difficulty to `max(1, min(3, ...))` (`command.py:782`). Reproducing that clamp
## is reproducing legacy, so a value outside the range lands on the nearest bound
## rather than being refused.
##
## The service does **not** send a client value through this clamp: it derives
## `DERIVED_DIFFICULTY`, so a client's number is never persisted. The clamp is
## delivered so the recorded behaviour is real rather than described, and the
## suite asserts it against the committed source.
static func clamp_difficulty(value: Variant) -> int:
	if not is_strict_int(value):
		return -1
	var difficulty := int(value)
	if difficulty < DIFFICULTY_MIN:
		return DIFFICULTY_MIN
	if difficulty > DIFFICULTY_MAX:
		return DIFFICULTY_MAX
	return difficulty


## The refusal code for an addressing that is not valid for its action, or ""
## while it is. It is a **client-side** answer and is never sent.
static func addressing_reason(action: Variant, addressing: Variant) -> String:
	if is_addressing(action, addressing):
		return ""
	var action_text := str(action)
	if not is_action(action):
		return "invalid_action"
	if action_text == ACTION_SET_GOAL or action_text == ACTION_COMPLETE_GOAL:
		return "invalid_goal_index"
	if action_text == ACTION_SET_QUEST_VAR:
		return "invalid_key"
	if action_text == ACTION_COLLECT_MISSION:
		return "invalid_mission"
	if action_text == ACTION_SET_QUEST_RANK:
		return "invalid_quest_index"
	return "invalid_quest_id"


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------


## Projects a player's quest state from its `privateState` and first `map`.
## Returns `{ok, error, reason, quests, recorded}` — `ok: false` with a **named**
## reason and the recorded state attached, never a defaulted empty value presented
## as a resolved one.
##
## A state that is absent, is not an object, carries a goals list that is not a
## list, a rank map that is not an object, a non-integer unlocked index, a mission
## that is neither an integer nor a string, or a non-integer last-chapter instant
## is **unresolvable**; nothing is scaled, rounded, defaulted, or clamped. The
## pinned engine's JSON parser widens every committed number to a float, so an
## `int` or an integral `float` is accepted while a numeric **string** is refused.
static func project(private_state: Variant, first_map: Variant) -> Dictionary:
	if private_state == null:
		return _reject(REASON_ABSENT_STATE,
			"the player's private state is absent, so no quest field is "
			+ "addressable", private_state, first_map)
	if not (private_state is Dictionary):
		return _reject(REASON_NON_OBJECT,
			"the player's private state is %s, not an object"
				% _type_name(private_state), private_state, first_map)
	if first_map == null:
		return _reject(REASON_ABSENT_STATE,
			"the player's first map is absent, so no map-side quest field is "
			+ "addressable", private_state, first_map)
	if not (first_map is Dictionary):
		return _reject(REASON_NON_OBJECT,
			"the player's first map is %s, not an object"
				% _type_name(first_map), private_state, first_map)
	var source: Dictionary = private_state
	var map_source: Dictionary = first_map
	for key: String in PRIVATE_KEYS:
		if not source.has(key):
			return _reject(REASON_ABSENT_STATE,
				"the player's private state carries no %s, so no quest field is "
					% key + "addressable", private_state, first_map)
	for key: String in MAP_KEYS:
		if not map_source.has(key):
			return _reject(REASON_ABSENT_STATE,
				"the player's first map carries no %s, so no quest field is "
					% key + "addressable", private_state, first_map)
	var goals: Variant = source[KEY_GOALS]
	if not (goals is Array):
		return _reject(REASON_NOT_A_LIST,
			"the player's private state %s is %s, not a list"
				% [KEY_GOALS, _type_name(goals)], private_state, first_map)
	var ranks: Variant = source[KEY_RANKS]
	if not (ranks is Dictionary):
		return _reject(REASON_NOT_AN_OBJECT,
			"the player's private state %s is %s, not an object"
				% [KEY_RANKS, _type_name(ranks)], private_state, first_map)
	var unlocked: Variant = source[KEY_UNLOCKED_INDEX]
	if not is_strict_int(unlocked):
		return _reject(REASON_NON_INTEGER,
			"the player's private state %s is %s, not an integer"
				% [KEY_UNLOCKED_INDEX, _type_name(unlocked)],
			private_state, first_map)
	var quest_vars: Variant = map_source[KEY_QUEST_VARS]
	if quest_vars != null and not (quest_vars is Dictionary):
		return _reject(REASON_NOT_AN_OBJECT,
			"the player's first map %s is %s, neither an object nor a recorded "
				% [KEY_QUEST_VARS, _type_name(quest_vars)] + "null",
			private_state, first_map)
	var quest_times: Variant = map_source[KEY_QUEST_TIMES]
	if not (quest_times is Dictionary):
		return _reject(REASON_NOT_AN_OBJECT,
			"the player's first map %s is %s, not an object"
				% [KEY_QUEST_TIMES, _type_name(quest_times)],
			private_state, first_map)
	var mission: Variant = map_source[KEY_MISSION]
	if not (is_strict_int(mission) or mission is String):
		return _reject(REASON_WRONG_MISSION,
			"the player's first map %s is %s, neither an integer, a boolean, nor "
				% [KEY_MISSION, _type_name(mission)] + "a string",
			private_state, first_map)
	var last_chapter: Variant = map_source[KEY_LAST_CHAPTER]
	if not is_strict_int(last_chapter):
		return _reject(REASON_WRONG_CHAPTER,
			"the player's first map %s is %s, not an integer"
				% [KEY_LAST_CHAPTER, _type_name(last_chapter)],
			private_state, first_map)
	var quests := QuestStateView.new()
	quests._resolvable = true
	quests._goals = (goals as Array).duplicate(true)
	quests._ranks = _string_keyed(ranks)
	quests._quest_vars_is_null = quest_vars == null
	quests._quest_vars = _string_keyed(quest_vars) if quest_vars != null else {}
	quests._quest_times = _string_keyed(quest_times)
	quests._mission = mission
	quests._last_chapter = int(last_chapter)
	quests._unlocked_index = int(unlocked)
	quests._recorded = {
		"privateState": _string_keyed(source),
		"map": _string_keyed(map_source),
	}
	return {"ok": true, "error": "", "reason": "", "quests": quests,
		"recorded": quests.recorded()}


## The whole flow's ONE evaluation entry point: the projection plus the recorded
## contracts, the presence predicate, and the recorded absences. A surface uses
## this and nothing else.
##
## Returns `{ok, reason, error, quests, fields, resolvable, record}` — `ok: false`
## for a structural refusal, `ok: true` with `resolvable: false` when the state
## itself could not be read, and `ok: true` with `resolvable: true` when it could.
## It computes **no** completion state, **no** remaining time, **no** progress
## ratio, and **no** reward.
static func evaluate(private_state: Variant, first_map: Variant) -> Dictionary:
	var projected: Variant = project(private_state, first_map)
	if not bool(projected.get("ok", false)):
		return {
			"ok": false,
			"reason": str(projected.get("reason", REASON_ABSENT_STATE)),
			"error": str(projected.get("error", "")),
			"quests": null,
			"fields": {},
			"resolvable": false,
			"record": branch_record(),
		}
	var quests: Variant = projected.get("quests", null)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"quests": quests,
		"fields": (quests as QuestStateView).fields(),
		"resolvable": true,
		"record": branch_record(),
	}


## Whether this client would offer `action` against `addressing`. True for every
## readable state and a structurally valid addressing: the six legacy branches
## validate **nothing**, and the recorded absence of validation is **not
## permission** to add a gate here (design D4/D5). This is a button's availability,
## not an authority — the service's own structural guards and a later
## server-authoritative milestone own the rules.
static func offers(evaluation: Dictionary, action: Variant,
		addressing: Variant) -> bool:
	if not bool(evaluation.get("ok", false)):
		return false
	if not is_action(action) or not is_addressing(action, addressing):
		return false
	if str(action) == ACTION_SET_QUEST_VAR \
			and str(addressing) == QUEST_VAR_IGNORED_KEY:
		# The ONE key the legacy branch itself ignores: offering it would be
		# offering an action whose only legacy effect is to print "Ignored".
		return false
	return true


## The client's own reason an intent is not offered, or "" while it is. It is a
## **client-side** answer, deliberately distinct from every service code, and it is
## never sent.
static func refusal_text(evaluation: Dictionary, action: Variant,
		addressing: Variant) -> String:
	if bool(evaluation.get("ok", false)) and offers(evaluation, action, addressing):
		return ""
	if not bool(evaluation.get("ok", false)):
		return "no quest intent offered: %s" % str(evaluation.get("error", ""))
	if not is_action(action):
		return "no quest intent offered: action must be one of %s" % \
			", ".join(PackedStringArray(ACTIONS))
	if str(action) == ACTION_SET_QUEST_VAR \
			and str(addressing) == QUEST_VAR_IGNORED_KEY:
		return ("no quest intent offered: the legacy branch itself ignores %s, "
			% QUEST_VAR_IGNORED_KEY
			+ "so the endpoint refuses it rather than persisting it")
	var reason := addressing_reason(action, addressing)
	return "no quest intent offered: %s" % reason


# ---------------------------------------------------------------------------
# The intent (design D2)
# ---------------------------------------------------------------------------


## The **whole** quest request body: the player identifier, the closed action, and
## the branch's own addressing, carried under **that action's own wire key**
## (`wire_key()`), which is why the body's third key differs per action.
##
## The body is exactly :data:`INTENT_KEY_COUNT` keys whatever the action, so the
## request shape cannot widen with the action vocabulary. This function is the
## structural form of the "no client value is trusted" claim: there is **no**
## parameter and **no** key through which a client could send a progress pair, a
## value, a difficulty, an outcome, or a unit list, so the service has nothing
## client-derived to ignore.
##
## The key set is produced here and nowhere else, and both implementations consume
## this function's result, so the wire body cannot drift from the key the service
## reads. An `action` outside the closed vocabulary never reaches the returned
## body at all — it is refused above.
static func intent_body(user_id: String, action: Variant,
		addressing: Variant) -> Dictionary:
	if not is_action(action):
		return {
			"ok": false,
			"reason": "invalid_action",
			"error": "action must be one of %s" % ", ".join(PackedStringArray(ACTIONS)),
			"body": {},
		}
	var reason := addressing_reason(action, addressing)
	if reason != "":
		return {"ok": false, "reason": reason,
			"error": "the %s is not addressable: got %s"
				% [str((ACTION_ADDRESSING as Dictionary)[str(action)]), addressing],
			"body": {}}
	if str(action) == ACTION_SET_QUEST_VAR \
			and str(addressing) == QUEST_VAR_IGNORED_KEY:
		return {
			"ok": false,
			"reason": "ignored_quest_var_key",
			"error": "the legacy branch itself ignores %s (command.py:91-95)"
				% QUEST_VAR_IGNORED_KEY,
			"body": {},
		}
	var action_text := str(action)
	var value: Variant = addressing
	if bool((ACTION_ADDRESSING_IS_INTEGER as Dictionary)[action_text]):
		value = int(addressing)
	else:
		value = str(addressing)
	var body := {
		"user_id": user_id,
		"action": action_text,
	}
	body[wire_key(action_text)] = value
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"body": body,
	}


## The intent's wire contract as the evidence report records it: the fixed keys,
## the per-action addressing key table, the per-action bodies, the ignored keys,
## and the derivation that replaces them.
static func intent_record() -> Dictionary:
	var bodies := {}
	for action: String in ACTIONS:
		var integer: bool = bool(
				(ACTION_ADDRESSING_IS_INTEGER as Dictionary)[action])
		var example: Variant = 0 if integer else "aNonEmptyKey"
		bodies[action] = {
			"wire_key": wire_key(action),
			"wire_type": "integer" if integer else "string",
			"example_value": example,
			"kind": str((ACTION_ADDRESSING as Dictionary)[action]),
		}
	return {
		"fixed_keys": (INTENT_FIXED_KEYS as Array).duplicate(),
		"key_count": INTENT_KEY_COUNT,
		"unknown_action_key": INTENT_ADDRESSING_KEY,
		"ignored_keys": (INTENT_IGNORED_KEYS as Array).duplicate(),
		"path": QUEST_PATH,
		"action_vocabulary": (ACTIONS as Array).duplicate(),
		"addressing_keys": (ACTION_ADDRESSING_KEY as Dictionary).duplicate(true),
		"addressing_kinds": (ACTION_ADDRESSING as Dictionary).duplicate(true),
		"per_action_bodies": bodies,
		"note": "the client sends EXACTLY the player identifier, a closed action, "
			+ "and the branch's own addressing under THAT ACTION'S OWN wire key "
			+ "(goal_index, key, mission, quest_index, or quest_id), so the body is "
			+ "three keys wide whatever the action. No progress pair, no value, no "
			+ "difficulty, no win/loss outcome, and no unit list is expressible, so "
			+ "the service derives every one of them itself and ignores any such key "
			+ "a client attaches alongside (design D2)",
		"progress_pair": DERIVED_PROGRESS.duplicate(),
		"quest_var_value": DERIVED_QUEST_VALUE,
		"difficulty": DERIVED_DIFFICULTY,
		"end_quest_units": [],
		"vector": "NEUTRAL: a quest price would be a client-sent delta, because "
			+ "the legacy dispatcher applies the request's per-command vector "
			+ "BEFORE the branch (command.py:40, engine.py:251-271) as "
			+ "max(current + delta, 0)",
		"reward_paid": REWARD_PAID,
		"reward_derived_from_content": false,
		"fast_forward_offered": false,
		"unlocked_index_written": false,
	}


## The six branch contracts, the writer inventory, the refusals, the refused
## destruction, the ledger door, and the migration — as fresh records a caller may
## keep and mutate, so a report reads the model's own tables rather than
## restating them.
static func branch_record() -> Dictionary:
	return {
		"branches": (BRANCHES as Array).duplicate(true),
		"branch_count": BRANCH_COUNT,
		"no_op_command": NO_OP_COMMAND,
		"writers": (WRITERS as Array).duplicate(true),
		"writer_count": WRITER_COUNT,
		"writer_fast_forward": WRITER_FAST_FORWARD,
		"fast_forward": FAST_FORWARD_CONTRACT,
		"migration": MIGRATION.duplicate(true),
		"non_derivation": (NON_DERIVATION as Array).duplicate(true),
		"refusals": (REFUSALS as Array).duplicate(true),
		"refusal_count": REFUSAL_COUNT,
		"refused_destruction": REFUSED_DESTRUCTION.duplicate(true),
		"ledger_door": LEDGER_DOOR.duplicate(true),
		"content_fields": (CONTENT_FIELD_CONSUMERS as Array).duplicate(true),
		"content_fields_read": (CONTENT_FIELDS_READ as Array).duplicate(),
		"content_fields_unread": (CONTENT_FIELDS_UNREAD as Array).duplicate(),
		"reward_field_absent": REWARD_FIELD_ABSENT,
		"content_note": CONTENT_RECORD_NOTE,
		"zero_consumer_fields": (ZERO_CONSUMER_FIELDS as Array).duplicate(true),
		"quest_var_comment_keys": (QUEST_VAR_COMMENT_KEYS as Array).duplicate(),
		"quest_var_comment_note": QUEST_VAR_COMMENT_NOTE,
		"quest_var_ignored_key": QUEST_VAR_IGNORED_KEY,
		"quest_var_alias_key": QUEST_VAR_ALIAS_KEY,
		"wrap_bound": MISSION_WRAP_BOUND,
		"wrap_target": MISSION_WRAP_TARGET,
		"wrap_note": MISSION_WRAP_NOTE,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The quest readout for the live evaluation: the goals list's length and null
## count, the rank map, the quest-variable map **including whether the recorded
## state is a null**, the quest-time map, the mission identifier **with its
## recorded type**, the last-chapter instant, and the unlocked index — with every
## recorded absence stated outright rather than left for a reader to wonder
## whether the omission is a defect.
##
## **No completion, no remaining time, no progress ratio, and no reward appear**,
## and the readout says so. An unresolvable state reads as unresolvable with its
## recorded reason — never as an empty quest, which is a state no committed save
## holds and one this contract refuses to render as resolved.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if not bool(evaluation.get("resolvable", false)):
		return ("quest unresolvable: %s (%s) — reported with the recorded "
			% [str(evaluation.get("reason", "")), str(evaluation.get("error", ""))]
			+ "state intact, never defaulted to an empty quest")
	var quests: Variant = evaluation.get("quests", null)
	if quests == null:
		return ""
	var parts: Array = []
	parts.append("goals %d entries, %d recorded null"
		% [(quests as QuestStateView).goals().size(),
			(quests as QuestStateView).goals_null_entries()])
	parts.append("ranks %s" % JSON.stringify((quests as QuestStateView).ranks()))
	if (quests as QuestStateView).quest_vars_is_null():
		parts.append("quest vars: recorded null (not an empty map)")
	else:
		parts.append("quest vars %s"
			% JSON.stringify((quests as QuestStateView).quest_vars()))
	parts.append("quest times %s"
		% JSON.stringify((quests as QuestStateView).quest_times()))
	parts.append("current mission %s (%s)"
		% [str((quests as QuestStateView).mission()),
			"string" if (quests as QuestStateView).mission_is_string()
				else "integer"])
	parts.append("last chapter %s"
		% str((quests as QuestStateView).last_chapter()))
	parts.append("unlocked index %s (reported, NEVER written)"
		% str((quests as QuestStateView).unlocked_index()))
	parts.append("no completion state: complete_goal writes NOTHING AT ALL")
	parts.append("no reward is paid and no stored resource moves: the committed "
		+ "reward field has zero legacy consumers and is uniformly 10")
	parts.append("no bounds: the goals list grows on demand with no upper bound")
	parts.append("no membership test on the quest-variable writer: an invented "
		+ "key is accepted, and only %s is refused" % QUEST_VAR_IGNORED_KEY)
	parts.append("fast_forward is a recorded seventh writer of quest state and is "
		+ "NOT delivered")
	parts.append("end_quest destroys nothing here: the client-computed "
		+ "destruction count is REFUSED as a DIVERGENCE")
	return " | ".join(parts)


## The armed surface's own confirm text for one quest intent: it names the branch
## and the addressing and says that nothing about the outcome is decided here — no
## progress pair, no value, no difficulty, no win/loss — because the service
## derives every one of them. It is deliberately free of every number a player
## might read as a price or a reward.
static func confirm_text(action: Variant, addressing: Variant) -> String:
	if not is_addressing(action, addressing):
		return ""
	var record: Dictionary = BRANCHES[_action_index(action)]
	var subject := str(addressing)
	if str(action) == ACTION_COMPLETE_GOAL:
		return ("%s on %s? The legacy branch %s — which resolves the committed "
			% [str(action), subject, str(record["command"])]
			+ "title, prints it, and writes NOTHING AT ALL. No completion flag "
			+ "exists and no reward is paid.")
	if str(action) == ACTION_END_QUEST:
		return ("%s for %s? The legacy branch %s. No stored resource moves, and "
			% [str(action), subject, str(record["command"])]
			+ "the client-computed destruction count is REFUSED: the derived "
			+ "request carries an empty unit list, so no placed row is touched.")
	return ("%s with %s? The legacy branch %s. It charges nothing, no completion "
		% [str(action), str((ACTION_ADDRESSING as Dictionary)[str(action)]),
			subject, str(record["command"])]
		+ "exists, and no progress pair, value, difficulty, or outcome is sent: "
		+ "the service derives every one of them.")


# ---------------------------------------------------------------------------
# The typed result
# ---------------------------------------------------------------------------


## Result of one quest intent: the legacy result plus the authoritative superset —
## the service's derived values, the quest state as read BEFORE and AFTER
## execution, and the seven stored resources — or a structured failure with **no
## partial payload**.
##
## **No stored resource is expected to move**: the derived vector is neutral and
## the endpoint's second post-execution proof half requires every stored resource
## to be **unchanged**, which is what forecloses a client minting or burning a
## balance through this path. **No reward is reported**: `reward_paid` is the
## derived `0` and `reward_derived_from_content` is a constant `false`.
##
## The client applies `quest_state`, `quests`, and `resources` **verbatim** — the
## response always wins over the client's own model.
class QuestResult:
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
	## The branch's own addressing, echoed exactly as sent. `null` on failure.
	var addressing: Variant = null
	## How the addressing is described, e.g. "goal index".
	var addressing_kind := ""
	## The legacy command the service derived from the action.
	var command := ""
	## The service's own derivation: which fields the branch wrote, which it did
	## not, whether it mutates at all, and the two wall-clock flags.
	var derived: Dictionary = {}
	## The quest state as read BEFORE and AFTER execution.
	var previous: Dictionary = {}
	var quest_state: Dictionary = {}
	## The service's `quests` projection after execution.
	var quests: Dictionary = {}
	## The six recorded branch contracts and the seven-entry writer inventory.
	var branches: Array = []
	var writers: Array = []
	## The refused destruction, the ledger door, the migration, and the refusals.
	var destruction: Dictionary = {}
	var migration: Dictionary = {}
	var refusals: Array = []
	## The server-derived `end_quest` blob, or `{}` for every other action.
	var end_quest_blob: Dictionary = {}
	## Constants: `reward_paid` is `0`, `reward_derived_from_content` and
	## `fast_forward_offered` are `false`, and `unlocked_quest_index_written` is
	## `false`.
	var reward_paid := -1
	var reward_derived_from_content := true
	var fast_forward_offered := true
	var unlocked_quest_index_written := true
	var resources: BootData.Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for the quest intents (never a partial payload).
static func result_failure(code: String, message: String) -> QuestResult:
	var result := QuestResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses a v0 quest envelope — success or structured error — into the typed
## result, fail-closed in both directions. The envelope must be a JSON object
## reporting `ok: true`, the protocol must be the v0 one, the legacy result
## string must be `success`, the echoed action must be inside the closed `ACTIONS`
## set, `command` must be the one that action derives, `derived` must carry the
## documented fields, both projections must resolve, and `resources` must be the
## seven non-negative integers every other response carries.
##
## A response that reports a **non-zero** reward, a reward derived from the
## committed content, an **offered** fast-forward operation, or a **written**
## unlocked-quest index is refused: those are the four absences this line
## delivers, and a response claiming otherwise describes a different contract.
static func parse_result(payload: Variant) -> QuestResult:
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
			"quest response did not report the legacy success result")
	var action := str(envelope.get("action", ""))
	if not ACTIONS.has(action):
		return result_failure("bad_response",
			("the quest response echoed action '%s', which is outside the "
				% action + "closed set %s") % ", ".join(PackedStringArray(ACTIONS)))
	if not (ACTION_ADDRESSING as Dictionary).has(action):
		return result_failure("bad_response",
			"the quest response echoed an action with no addressing record")
	var addressing: Variant = envelope.get("addressing")
	if not is_addressing(action, addressing):
		return result_failure("bad_response",
			"the quest response echoed an addressing this action cannot carry")
	var command := str(envelope.get("command", ""))
	if command != str((ACTION_COMMANDS as Dictionary)[action]):
		return result_failure("bad_response",
			"the quest response derived command '%s' for action '%s', which is "
				% [command, action] + "not the committed one")
	var derived: Variant = envelope.get("derived")
	if not (derived is Dictionary):
		return result_failure("bad_response",
			"the quest response carries no derived block")
	var derived_body: Dictionary = derived
	for field: String in ["written", "untouched", "mutates", "stamps_instant",
			"stamps_chapter", "progress_pair", "quest_var_value", "difficulty",
			"wrapped_mission"]:
		if not derived_body.has(field):
			return result_failure("bad_response",
				"the quest response's derived block carries no %s" % field)
	var quests: Variant = envelope.get("quests")
	if not (quests is Dictionary):
		return result_failure("bad_response",
			"the quest response carries no quests projection")
	var quests_body: Dictionary = quests
	if quests_body.get("resolvable") != true:
		return result_failure("bad_response",
			"the quest response's own projection reports an UNRESOLVABLE state "
			+ "after a successful action")
	var quest_state: Variant = envelope.get("quest_state")
	if not (quest_state is Dictionary):
		return result_failure("bad_response",
			"the quest response carries no quest state")
	var state_body: Dictionary = quest_state
	for key: String in QUEST_FIELDS:
		if not state_body.has(key):
			return result_failure("bad_response",
				"the quest response's state carries no %s" % key)
	var previous: Variant = envelope.get("previous")
	if not (previous is Dictionary):
		return result_failure("bad_response",
			"the quest response carries no previous projection")
	var previous_body: Dictionary = previous
	if previous_body.get("resolvable") != true:
		return result_failure("bad_response",
			"the quest response's previous projection reports an UNRESOLVABLE "
			+ "state before a successful action")
	var paid: Variant = BootData._parse_int(envelope.get("reward_paid"))
	if paid == null or int(paid) != REWARD_PAID:
		return result_failure("bad_response",
			"the quest response pays a reward, which the legacy branch never "
			+ "does: the committed reward field has zero consumers and is "
			+ "uniformly 10")
	if envelope.get("reward_derived_from_content") != false:
		return result_failure("bad_response",
			"the quest response claims a reward derived from committed content")
	if envelope.get("fast_forward_offered") != false:
		return result_failure("bad_response",
			"the quest response offers a fast-forward operation, which this line "
			+ "delivers not at all")
	if envelope.get("unlocked_quest_index_written") != false:
		return result_failure("bad_response",
			"the quest response claims it wrote the unlocked-quest index, which "
			+ "has zero legacy consumers")
	var destruction: Variant = envelope.get("destruction")
	if not (destruction is Dictionary):
		return result_failure("bad_response",
			"the quest response carries no destruction record")
	var destruction_body: Dictionary = destruction
	if str(destruction_body.get("status", "")) != "REFUSED":
		return result_failure("bad_response",
			"the quest response does not report the destruction count as REFUSED")
	if destruction_body.get("placed_rows_byte_identical") != true:
		return result_failure("bad_response",
			"the quest response does not prove every placed row byte-identical")
	var branches: Variant = envelope.get("branches")
	if not (branches is Array) or (branches as Array).size() != BRANCH_COUNT:
		return result_failure("bad_response",
			"the quest response does not carry the six recorded branches")
	var writers: Variant = envelope.get("writers")
	if not (writers is Array) or (writers as Array).size() != WRITER_COUNT:
		return result_failure("bad_response",
			"the quest response does not carry the seven recorded quest writers")
	# The blob is present for `end_quest` and ABSENT for the other five actions,
	# and both directions are checked: the service sends ``None`` for an action
	# that has no blob, and a blob on a `set_goal` response would be a claim about
	# a branch that owns no blob at all. Requiring the block unconditionally was
	# a real defect — it refused five of the six successful live responses.
	var blob: Variant = envelope.get("end_quest_blob")
	var blob_body := {}
	if action == ACTION_END_QUEST:
		if not (blob is Dictionary):
			return result_failure("bad_response",
				"the end_quest response carries no end_quest blob block")
		blob_body = blob
		var units: Variant = (blob_body as Dictionary).get("units")
		if not (units is Array) or (units as Array).size() != 0:
			return result_failure("bad_response",
				"the end_quest response carries %r units: the destruction count "
					% units + "is REFUSED and an empty list is what refuses it")
	elif blob != null:
		return result_failure("bad_response",
			"the %s response carries an end_quest blob, which only the "
				% str(action) + "end_quest branch has")
	if envelope.get("persisted_client_values") == null:
		return result_failure("bad_response",
			"the quest response states no persisted-client-value list")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return result_failure("bad_response",
			"quest response carries no resources object")
	var resources := BootData._parse_resources(resources_raw)
	if resources == null:
		return result_failure("bad_response",
			"quest resources are not seven non-negative integers")
	var result := QuestResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return result_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.action = action
	result.addressing = addressing
	result.addressing_kind = str(envelope.get("addressing_kind", ""))
	result.command = command
	result.derived = derived_body.duplicate(true)
	result.previous = previous_body.duplicate(true)
	result.quest_state = state_body.duplicate(true)
	result.quests = quests_body.duplicate(true)
	result.branches = (branches as Array).duplicate(true)
	result.writers = (writers as Array).duplicate(true)
	result.destruction = destruction_body.duplicate(true)
	var migration: Variant = envelope.get("migration")
	if migration is Dictionary:
		result.migration = (migration as Dictionary).duplicate(true)
	var refusals: Variant = envelope.get("refusals")
	if refusals is Array:
		result.refusals = (refusals as Array).duplicate(true)
	result.end_quest_blob = (blob_body as Dictionary).duplicate(true)
	result.reward_paid = REWARD_PAID
	result.reward_derived_from_content = false
	result.fast_forward_offered = false
	result.unlocked_quest_index_written = false
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
		{"fact": "the quest state is three private-state keys and four map keys, "
			+ "reported verbatim with nothing derived from another",
			"evidence": "command.py:68-74, 76-79, 87-117, 430-442, 745-750, "
				+ "752-806; tests/saves/fresh-player.json"},
		{"fact": "complete_goal writes NOTHING AT ALL: it resolves the committed "
			+ "title, prints it, and returns",
			"evidence": "command.py:76-79, and the committed fixture's recorded "
				+ "step whose before and after states are byte-identical"},
		{"fact": "the goals list grows ON DEMAND with no upper bound",
			"evidence": "engine.py:96-100, and probe 1 of the committed capture, "
				+ "which grew the list from 151 to 501 entries"},
		{"fact": "set_quest_var accepts ANY key, and the one key it ignores is "
			+ "idSimpleChapter",
			"evidence": "command.py:87-117, and probes 2 and 2b of the committed "
				+ "capture: the ignored key changed nothing and an invented key "
				+ "was accepted"},
		{"fact": "collect_mission stringifies the mission identifier, wraps above "
			+ "99, stamps the last-chapter instant, and clears the quest-variable "
			+ "map",
			"evidence": "command.py:430-442, and probe 3 of the committed capture"},
		{"fact": "only the identifier and the title are read; the reward field has "
			+ "ZERO consumers and is uniformly 10 on all 91 entries",
			"evidence": "the measured content inventory, taken over the seven "
				+ "legacy modules and packages/game-content/normalized/"
				+ "quests.json in the same run"},
		{"fact": "unlockedQuestIndex has zero legacy sites",
			"evidence": "the seven legacy modules, counted as quoted occurrences"},
		{"fact": "fast_forward subtracts a client-supplied number of seconds from "
			+ "every quest time and from the last-chapter instant",
			"evidence": "command.py:911 and 942-944, and probe 5 of the "
				+ "committed capture"},
		{"fact": "the legacy server DOES destroy placed rows on end_quest, and "
			+ "this repository's endpoint does NOT",
			"evidence": "probe 4 of the committed capture: one placed row was "
				+ "destroyed against the live legacy server"},
	],
	"derived": [
		{"fact": "the intent body is three keys wide for EVERY action: a player "
			+ "identifier, a closed action, and the addressing under one fixed key",
			"evidence": "derived (design D2): the same intent-only discipline the "
				+ "research, queue, collection, and revival endpoints apply, "
				+ "chosen because every legacy branch takes its outcome from the "
				+ "client"},
		{"fact": "the service derives the progress pair, the quest-variable value, "
			+ "the rank difficulty, and the whole end_quest blob",
			"evidence": "derived (design D2/D6): the committed reward field is a "
				+ "uniform constant with zero consumers, so no amount is "
				+ "derivable, and a client-sent one would be client-trusted"},
		{"fact": "a negative goal index is refused while a large one is accepted",
			"evidence": "derived (design D4): Python would otherwise write "
				+ "goals[-1], aliasing the last entry, so the alias is refused "
				+ "structurally while the legacy absence of an upper bound is "
				+ "reproduced"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy quest panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


## The evidence's explicit non-claims (spec "Quest evidence and claim limits").
## The runtime tokens in the first claim are assembled from fragments for the
## same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO QUEST REWARD IS PAID AND NO STORED RESOURCE MOVES, because the committed "
		+ "reward field has ZERO legacy consumers and is UNIFORMLY 10 on all 91 "
		+ "entries; the endpoint's post-execution proof compares the COMPLETE "
		+ "stored resource set, which is what makes the claim non-tautological",
	"THE `end_quest` DESTRUCTION COUNT IS REFUSED and every placed row is left "
		+ "byte-identical; the legacy server DOES destroy rows on this command, so "
		+ "the difference is a DIVERGENCE and NOT parity, and authoritative combat "
		+ "belongs to Server v1 / M13",
	"NO COMPLETION STATE EXISTS, because `complete_goal` writes NOTHING AT ALL; the "
		+ "branch is delivered as a no-op and its whole-state identity is proved",
	"NO BOUND IS ADDED to the on-demand goals list, so a client-supplied "
		+ "identifier can still grow it without limit, and that is a Server v1 / "
		+ "M13 gap",
	"NO MEMBERSHIP TEST is added to the quest-variable writer: an invented key is "
		+ "accepted, as legacy does, and only the one key the legacy branch itself "
		+ "ignores is refused",
	"THE UNLOCKED-QUEST INDEX is reported and NEVER written, because it has zero "
		+ "legacy consumers",
	"NO FAST-FORWARD OPERATION IS DELIVERED, though its write of quest state is "
		+ "recorded as the seventh writer",
	"NO ELAPSED-TIME, remaining-chapter, readiness, or cooldown rule is derived "
		+ "from any quest instant, because no legacy branch reads one",
	"THE COMMITTED QUEST CONTENT IS REPORTED AND NEVER USED: only the identifier "
		+ "and the title are read, and no code identifier or computation is named "
		+ "after the reward field",
	"NO CLAIM IS MADE ABOUT WHAT THE LEGACY CLIENT DISPLAYED: no authentic quest "
		+ "panel has been captured, and the readout's wording is the delivered "
		+ "provisional convention",
	"the fixture covers all SIX branches against the fresh-player corpus and "
		+ "nothing else: no reward, no completion, no destruction, and no "
		+ "quest-timing semantics is evidenced, and no fixture is absent",
	"no compatibility route beyond the six guarded intents this line delivers "
		+ "exists for a quest, and the service adds no server-authoritative "
		+ "validation of bounds, membership, price, or reward - that belongs to "
		+ "Server v1 / M13",
	"no pixel-parity oracle exists",
	"no windowed capture is claimed: nothing is rendered, and the committed "
		+ "corpus places no quest content",
	"the committed capture runs the fake GameApi implementation for the "
		+ "client-side evidence, a deterministic test double rather than a parity "
		+ "oracle; the executed-legacy parity rests on the committed fixture and "
		+ "the live phase",
]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural refusal: no `QuestStateView` at all, the named reason, a message
## that names the offending field, and the **recorded** state carried through
## untouched so a caller can see what the save held.
static func _reject(reason: String, message: String, private_state: Variant,
		first_map: Variant) -> Dictionary:
	return {
		"ok": false,
		"reason": reason,
		"error": "[quest] projection refused (%s): %s" % [reason, message],
		"quests": null,
		"recorded": _recorded_snapshot(private_state, first_map),
	}


## The recorded state as plain copies, so a refusal can hand it back without
## aliasing the live save. A non-object becomes its type name rather than being
## invented into a shape.
static func _recorded_snapshot(private_state: Variant,
		first_map: Variant) -> Variant:
	if private_state == null and first_map == null:
		return "absent"
	return {"privateState": _string_keyed_or_name(private_state),
		"map": _string_keyed_or_name(first_map)}


## A mapping with its keys stringified, or the observed type name when the value
## is not an object.
static func _string_keyed_or_name(value: Variant) -> Variant:
	if value is Dictionary:
		return _string_keyed(value)
	return _type_name(value)


## A fresh copy of a mapping with its keys stringified. The JSON parser already
## yields string keys, and stringifying here means a hand-built caller cannot make
## two spellings of one key look like two entries.
static func _string_keyed(value: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	for key: Variant in (value as Dictionary).keys():
		out[str(key)] = (value as Dictionary)[key]
	return out


## The observed type of a refused value, so a failure names what it found instead
## of saying only "invalid".
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


## The service's structured error, carried through with its own code.
static func _result_error(envelope: Dictionary) -> QuestResult:
	var error: Variant = envelope.get("error")
	if not (error is Dictionary):
		return result_failure("bad_response",
			"the quest response reports failure with no error object")
	var body: Dictionary = error
	return result_failure(str(body.get("code", "bad_response")),
		str(body.get("message", "")))