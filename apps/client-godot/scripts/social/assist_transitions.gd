extends RefCounted
## The recorded assist-dispatch table for OpenSpec `godot-construction-assist`.
##
## ## This module is CENSUS, not behaviour (design D3)
##
## Everything here is a **record of source text**, quoted and never executed.
## It is a separate module from `construction_assist_state.gd` precisely so a
## reader cannot mistake a quoted `[0]` append beside live projection code for
## something the client does. Every entry carries `reproduced: false`, and no
## delivered route performs any of them.
##
## ## Three branches reach the key, and one is NOT named for it
##
## `set_resource_allies` is the trap a reader consulting only the two
## assist-named branches falls into: it reaches `finish_si` at `command.py:644`,
## so the DELETE path has **two** dispatchers, not one. That branch is named here
## for exactly that reason.
##
## ## A separate module also keeps the census vocabulary out of the projection
##
## The projection module answers "what does this row record". This one answers
## "what did the preserved server do". Merging them would invite the second
## question to be answered from the first.

## The three recorded dispatchers, in source order.
##
## `reproduced: false` is not decoration: it is the claim a reader needs, because
## every effect below is real legacy behaviour that this capability deliberately
## does not deliver.
const DISPATCHERS := [
	{
		"command": "buy_si_help",
		"file": "command.py",
		"lines": "549-559",
		"named_for_the_key": true,
		"precondition": "the addressed map slot resolves to a row",
		"absent_row_behaviour": "prints \"Error: item not found.\" and "
			+ "RETURNS at command.py:555, so nothing is written",
		"effects": [
			{
				"effect": "reaches the engine helper at command.py:557, which "
					+ "creates the key as [ 0 ] when absent",
				"site": "engine.py:139-140",
				"recorded_source": "if \"si\" not in attr:",
				"reproduced": false,
			},
			{
				"effect": "appends 0 when the key is present",
				"site": "engine.py:142",
				"recorded_source":
					"attr[\"si\"].append(0) # 0 is for buying instead of hiring "
					+ "friends",
				"reproduced": false,
			},
		],
		"charges": false,
		"grants": false,
		"gate_checked": false,
		"type_checked": false,
		"team_checked": false,
	},
	{
		"command": "finish_si",
		"file": "command.py",
		"lines": "561-571",
		"named_for_the_key": true,
		"precondition": "the addressed map slot resolves to a row",
		"absent_row_behaviour": "prints \"Error: item not found.\" and "
			+ "RETURNS at command.py:567, so nothing is written",
		"effects": [
			{
				"effect": "reaches the engine helper at command.py:569, which "
					+ "deletes the key when present",
				"site": "engine.py:147",
				"recorded_source": "del attr[\"si\"]",
				"reproduced": false,
			},
		],
		"charges": false,
		"grants": false,
		"gate_checked": false,
		"type_checked": false,
		"team_checked": false,
	},
	{
		"command": "set_resource_allies",
		"file": "command.py",
		"lines": "637-647",
		"named_for_the_key": false,
		"precondition": "NO precondition for the market write; the stamp and "
			+ "the delete are conditional on the addressed row resolving",
		"absent_row_behaviour": "does NOT return: `if item:` at command.py:642 "
			+ "skips the stamp and the delete, and command.py:646 still "
			+ "writes the market from the client-supplied argument",
		"why_named_here": "it reaches finish_si at command.py:644, so the delete "
			+ "path has two dispatchers and a reader consulting only the two "
			+ "assist-named branches would conclude otherwise",
		"effects": [
			{
				"effect": "writes resourceAlliesMarket from a client-supplied "
					+ "argument, UNCONDITIONALLY",
				"site": "command.py:646",
				"recorded_source":
					"map[\"resourceAlliesMarket\"] = resource",
				"reproduced": false,
				"owner": "godot-social-state",
				"note": "this line sits OUTSIDE the `if item:` block, so it "
					+ "runs even when the addressed row does not resolve",
			},
			{
				"effect": "stamps the addressed row's recorded instant",
				"site": "command.py:643",
				"recorded_source": "item[3] = time_now",
				"reproduced": false,
				"owner": "godot-social-state",
				"meaning_derived": false,
				"note": "client-reachable through the generic vector this "
					+ "project refuses, which is why the instant is recorded "
					+ "rather than trusted",
			},
			{
				"effect": "calls finish_si, which deletes the row's si key",
				"site": "command.py:644",
				"recorded_source": "finish_si(item)",
				"reproduced": false,
				"owner": "godot-construction-assist",
				"note": "inside `if item:`, so the delete is skipped when "
					+ "the row does not resolve while the market write above "
					+ "still happens",
			},
		],
		"charges": false,
		"grants": false,
		"gate_checked": false,
		"type_checked": false,
		"team_checked": false,
	},
]

## The recorded counts, pinned so the suite asserts a closed set.
const DISPATCHER_COUNT := 3
const NAMED_FOR_KEY_COUNT := 2
const DELETE_DISPATCHER_COUNT := 2
const ENGINE_HELPERS := ["buy_si_help", "finish_si"]

## The recorded helper inventory: two engine helpers, plus the one caller that
## reaches them from a branch not named for them.
const ENGINE_HELPER_SITES := {
	"buy_si_help": "engine.py:137-142",
	"finish_si": "engine.py:144-147",
	"map_add_item": "engine.py:8-31",
	"map_add_item_from_item": "engine.py:33-34",
}

## `map_add_item_from_item` bypasses the gate entirely. Recorded as a recorded
## fact about a second writer of the same bag, and NOT as an explanation for the
## corpus gaps - nothing performs it in a way the corpus can be shown to follow.
const GATE_BYPASS_SITE := "engine.py:33-34"
const GATE_BYPASS_RECORDED := true
const GATE_BYPASS_IS_A_CORPUS_EXPLANATION := false

## No effect is reproduced here, and no route is delivered (design D1).
const REPRODUCED_EFFECTS := []
const DELIVERED_ROUTES := []


## Every recorded dispatcher, verbatim.
static func dispatchers() -> Array:
	return (DISPATCHERS as Array).duplicate(true)


## Every recorded effect across every dispatcher, flattened.
static func effects() -> Array:
	var out: Array = []
	for entry: Dictionary in DISPATCHERS:
		for effect: Dictionary in entry["effects"]:
			out.append(effect)
	return out


## Every recorded effect carries `reproduced: false`. A single missing flag is
## the failure this accessor exists to make visible.
static func reproduced_flags() -> Array:
	var out: Array = []
	for effect: Dictionary in effects():
		out.append(bool(effect.get("reproduced", true)))
	return out


## One recorded dispatcher's record, or `null` when the name was not measured.
static func dispatcher(command: String) -> Variant:
	for entry: Dictionary in DISPATCHERS:
		if str(entry["command"]) == command:
			return entry
	return null


## The branch NOT named for the key, which reaches it anyway.
static func unnamed_dispatcher() -> Dictionary:
	for entry: Dictionary in DISPATCHERS:
		if not bool(entry["named_for_the_key"]):
			return entry
	return {}


## The recorded precondition of each dispatcher, and whether this module
## enforces any of them. It enforces none.
##
## The first draft of this accessor said every dispatcher SHARES one
## precondition. That was false and is corrected here: the two assist-named
## branches RETURN when the addressed row does not resolve, while
## `set_resource_allies` does not return and writes the market unconditionally.
## One shared precondition would have hidden exactly the asymmetry that makes
## the third dispatcher worth naming.
static func precondition() -> Dictionary:
	var per_command: Dictionary = {}
	for entry: Dictionary in DISPATCHERS:
		per_command[str(entry["command"])] = {
			"precondition": str(entry["precondition"]),
			"absent_row_behaviour": str(entry["absent_row_behaviour"]),
		}
	return {
		"shared_by_every_dispatcher": false,
		"per_command": per_command,
		"gate_checked_by_any": false,
		"type_checked_by_any": false,
		"team_checked_by_any": false,
		"enforced_here": false,
		"why_not": "the preserved branches have no such check, and enforcing "
			+ "the gate would refuse two committed corpus rows",
	}
