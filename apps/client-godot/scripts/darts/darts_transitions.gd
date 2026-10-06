extends RefCounted
## The three recorded darts transitions for OpenSpec `godot-darts`.
##
## ## Every input of these three branches is client-sent, and one of them is refused
##
## `command.py:573-610` is three branches over six `privateState` fields. What the
## server writes is `time_now` (the server clock) plus the client's own arguments.
## Each transition below therefore reports its client-sent inputs **as
## client-sent**, with the argument each came from, and derives nothing from them
## that the preserved branch does not also derive.
##
## ## The refused input: `won_extra` (design D3)
##
## `darts_shoot_balloon` reads `won_extra = args[1]` and, if it is truthy, sets
## `dartsGotExtra = True` (`:604-605`). It verifies **nothing**: no module checks
## whether the target existed, was hittable, or was won, and the truthiness is
## unvalidated (`if won_extra:` accepts any non-empty value). Reproducing that is
## the `apply_client_state` pattern `AGENTS.md` names as Bad, so the flag is
## **refused**: no delivered transition writes it, and the refusal is reported as a
## **divergence** in `divergences`, never as parity.
##
## The corpus says nothing either way, which is worth stating plainly: over the 33
## canonical documents `dartsGotExtra` is `false` in **every one**, and the three
## documents carrying shots all record losing ones (`docs/legacy-m11-darts.md`
## §0b C4). So the refusal has **no corpus evidence in either direction**.
##
## ## The delivered shot index is INTENT, and is trusted about nothing (design D10)
##
## `index = args[0]` is *which target the player aimed at* -- the same kind of value
## as `buy_building(player_id, building_id, x, y)` in `AGENTS.md`'s own "Good"
## example. It is recorded, nothing is derived from it, and nothing is bounded with
## it. The corpus needs this to be testable at all: one document records `[18, 17]`
## and another records `[0]`, so refusing the shot outright would leave those
## documents with nothing to reproduce.
##
## ## Two rules are NOT invented
##
##   * **no length bound.** The recorded branch appends whenever the index is absent
##     (`:599-600`) and never checks a length, so a client may grow the list without
##     limit. No maximum shot count is delivered, and `LIST_BOUND_RECORD` reports the
##     absence as a fact.
##   * **no membership test.** Nothing in the eleven modules compares the index to
##     the committed darts ids, and `villages/Nerri.json` records the out-of-schedule
##     shot `[0]` against a schedule running `1..27` -- so the missing check is not
##     merely unimplemented, it is demonstrably **not enforced**. Adding one would
##     contradict the corpus, so none is delivered.
##
## ## The seed is stored verbatim and NOTHING is derived from it
##
## `darts_reset` writes client `args[0]` into `dartsRandomSeed` (`:577`) and **no
## branch ever reads it back**. So there is no intent to reconstruct -- only a value
## to store. It is delivered as a recorded client-sent write with no semantics, which
## is a stronger and separately guarded claim than the shot index's: this module
## contains no reference to the seed field outside the two places that store or
## report it.
##
## ## This module never names the committed darts schedule
##
## Not as prose only: `test_darts.gd` scans this file with comments AND strings
## stripped and requires zero occurrences of the schedule's vocabulary. The
## ownership report and the out-of-schedule corpus fact are carried by the suite and
## by `darts_state.gd`, because reading the schedule is exactly what would tempt a
## membership test.

## The three recorded branches and their sites.
const RESET_COMMAND := "darts_reset"
const FREE_COMMAND := "darts_new_free"
const SHOOT_COMMAND := "darts_shoot_balloon"
const COMMAND_SOURCE := "command.py:573-610"

## The six recorded darts fields, all in `privateState`.
const PRIVATE_STATE_KEY := "privateState"
const SEED_FIELD := "dartsRandomSeed"
const SHOTS_FIELD := "dartsBalloonsShot"
const EXTRA_FIELD := "dartsGotExtra"
const FREE_AVAILABLE_FIELD := "dartsHasFree"
const RESET_STAMP_FIELD := "timeStampDartsReset"
const NEW_FREE_STAMP_FIELD := "timeStampDartsNewFree"

## How many fields each recorded branch writes, counted from the source.
const RESET_WRITE_COUNT := 6
const FREE_WRITE_COUNT := 2
const SHOOT_WRITE_COUNT := 3

## The closed command vocabulary, in source order.
const COMMANDS := [RESET_COMMAND, FREE_COMMAND, SHOOT_COMMAND]

## Every client-sent input of the three branches, named with its argument.
##
## `seed` and `shot_index` are delivered as intent; `client_claimed_outcome` is
## REFUSED, and that refusal is the reason its row carries `delivered: false`.
const CLIENT_SENT_INPUTS := [
	{
		"argument": "args[0]",
		"command": RESET_COMMAND,
		"field": SEED_FIELD,
		"role": "intent",
		"delivered": true,
		"derived_from_it": false,
		"note": "stored verbatim and read by no branch, so nothing is derived "
			+ "from it (design D10)",
	},
	{
		"argument": "args[0]",
		"command": SHOOT_COMMAND,
		"field": SHOTS_FIELD,
		"role": "intent",
		"delivered": true,
		"derived_from_it": false,
		"note": "which target the player aimed at; recorded, nothing derived, "
			+ "nothing bounded with it (design D10)",
	},
	{
		"argument": "args[1]",
		"command": SHOOT_COMMAND,
		"field": EXTRA_FIELD,
		"role": "asserted outcome",
		"delivered": false,
		"derived_from_it": false,
		"note": "REFUSED: an unvalidated client truthiness that sets a flag, "
			+ "with no verification of any kind in the eleven modules",
	},
]

## The refused input, as constants first so the tables below are built from
## constant expressions rather than from a const subscript (which Godot does not
## fold, and which would turn a table into a run-time expression).
const OUTCOME_ARGUMENT := "args[1]"
const OUTCOME_SITE := "command.py:604-605"
const OUTCOME_WHY := "an unvalidated client truthiness that sets a flag, with no " \
	+ "verification of any kind in the eleven legacy modules"
const OUTCOME_CORPUS := "none in either direction: dartsGotExtra is false in " \
	+ "all 33 canonical documents (docs/legacy-m11-darts.md 0b C4)"
const OUTCOME_WHY_CAPABILITY := "reproducing a client-dictated outcome is the " \
	+ "apply_client_state pattern AGENTS.md names as Bad"

## The refusal, as delivered data rather than as a comment.
const OUTCOME_REFUSAL := {
	"field": EXTRA_FIELD,
	"client_argument": OUTCOME_ARGUMENT,
	"site": OUTCOME_SITE,
	"written_by_this_capability": false,
	"divergence": true,
	"verified_by_preserved_server": false,
	"corpus_evidence": OUTCOME_CORPUS,
	"why": OUTCOME_WHY,
}

## The two absences, reported as facts about the recorded branch.
const LIST_BOUND_RECORD := {
	"length_bound_exists": false,
	"membership_test_exists": false,
	"appends_when_absent_only": true,
	"source": "command.py:599-600",
	"corpus_evidence": "villages/Nerri.json records the out-of-schedule shot "
		+ "[0] against a schedule running 1..27, so no membership check is "
		+ "enforced",
	"server_v1_gap": "a client may grow the list without limit, exactly as the "
		+ "preserved server allows",
}

## The closed refusal vocabulary for malformed INPUT.
const REFUSAL_STATE_TYPE := "recorded_state_not_object"
const REFUSAL_SHOTS_ABSENT := "shot_list_absent"
const REFUSAL_SHOTS_TYPE := "shot_list_not_array"
const REFUSAL_INDEX_TYPE := "shot_index_not_integer"
const REFUSAL_SEED_TYPE := "seed_not_integer"
const REFUSAL_CLOCK_NEGATIVE := "server_clock_negative"

const INPUT_REFUSALS := [
	REFUSAL_STATE_TYPE, REFUSAL_CLOCK_NEGATIVE, REFUSAL_SHOTS_ABSENT,
	REFUSAL_SHOTS_TYPE, REFUSAL_INDEX_TYPE, REFUSAL_SEED_TYPE,
]

## The single DIVERGENCE this capability records against the preserved server.
const DIVERGENCES := [
	{
		"id": OUTCOME_ARGUMENT,
		"what": "the recorded branch sets the got-extra flag from a client "
			+ "truthiness; this capability never writes it",
		"site": OUTCOME_SITE,
		"is_parity": false,
		"corpus_evidence": OUTCOME_CORPUS,
	},
]

## Why two inputs are refused on SHAPE, and what the recorded branch did instead.
##
## Neither is parity: the recorded branch appends ANY value to the shot list and
## stores ANY value as the seed, because it never inspects either. A delivered
## field that the corpus only ever holds as a whole number is refused on any other
## shape, so a malformed input cannot reach it. Recorded here so the refusal is a
## stated choice rather than an accident.
const INPUT_SHAPE_RECORD := {
	REFUSAL_INDEX_TYPE: {
		"legacy_behaviour": "command.py:594-600 appends args[0] whatever it is",
		"corpus_shapes": "integers in every committed document",
		"is_parity": false,
	},
	REFUSAL_SEED_TYPE: {
		"legacy_behaviour": "command.py:577 stores args[0] whatever it is",
		"corpus_shapes": "integers in every committed document",
		"is_parity": false,
	},
	REFUSAL_SHOTS_ABSENT: {
		"legacy_behaviour": "command.py:598 reads the key directly, so an "
			+ "absent list raises KeyError in the preserved server",
		"corpus_shapes": "every committed document carries the list",
		"is_parity": false,
	},
}


## `darts_reset` (`command.py:573-584`): six fields written from one client
## argument and the server clock.
##
## The recorded list is REPLACED with `[]`, not appended to; the seed is stored
## verbatim; both instants are stamped with the server clock; the free flag is set
## and the got-extra flag cleared -- and that last write is NOT a client outcome,
## it is an unconditional reset to `false`, so it is delivered.
static func reset(seed: Variant, now: int) -> Dictionary:
	var outcome := _base(RESET_COMMAND, now)
	if now < 0:
		return _refuse(outcome, REFUSAL_CLOCK_NEGATIVE)
	if not _is_integral(seed):
		return _refuse(outcome, REFUSAL_SEED_TYPE)
	outcome["ok"] = true
	outcome["client_sent"] = {
		SEED_FIELD: {
			"argument": "args[0]",
			"source": COMMAND_SOURCE,
			"role": "intent",
			"stored_verbatim": true,
			"semantics_derived": false,
		},
	}
	outcome["written"] = {
		SEED_FIELD: int(seed),
		SHOTS_FIELD: [],
		FREE_AVAILABLE_FIELD: true,
		EXTRA_FIELD: false,
		RESET_STAMP_FIELD: now,
		NEW_FREE_STAMP_FIELD: now,
	}
	outcome["field_count"] = RESET_WRITE_COUNT
	outcome["list_replaced"] = true
	outcome["extra_flag_from_client_claim"] = false
	outcome["extra_flag_reset"] = true
	return outcome


## `darts_new_free` (`command.py:586-591`): the one branch that reads NO argument.
##
## Two fields, both derived: the flag is set and the instant stamped. There is no
## client input to name, which is worth recording -- this is the only darts branch
## whose inputs are entirely server-side.
static func new_free(now: int) -> Dictionary:
	var outcome := _base(FREE_COMMAND, now)
	if now < 0:
		return _refuse(outcome, REFUSAL_CLOCK_NEGATIVE)
	outcome["ok"] = true
	outcome["client_sent"] = {}
	outcome["written"] = {
		FREE_AVAILABLE_FIELD: true,
		NEW_FREE_STAMP_FIELD: now,
	}
	outcome["field_count"] = FREE_WRITE_COUNT
	outcome["client_argument_count"] = 0
	return outcome


## `darts_shoot_balloon` (`command.py:593-610`).
##
## `state` is the recorded `privateState` object, passed in read-only. The branch
## READS `dartsBalloonsShot` (`:598`), so its absence is a recorded hard
## requirement rather than a shape this module may default -- hence the explicit
## `shot_list_absent` refusal instead of an empty list.
##
## The result carries `divergences` whenever the client claimed an outcome, so the
## refusal is visible in the response rather than silent.
static func shoot(state: Variant, shot_index: Variant,
		client_claimed_outcome: Variant, now: int) -> Dictionary:
	var outcome := _base(SHOOT_COMMAND, now)
	if now < 0:
		return _refuse(outcome, REFUSAL_CLOCK_NEGATIVE)
	if not (state is Dictionary):
		return _refuse(outcome, REFUSAL_STATE_TYPE)
	var recorded: Dictionary = state
	if not recorded.has(SHOTS_FIELD):
		return _refuse(outcome, REFUSAL_SHOTS_ABSENT)
	var shots_v: Variant = recorded[SHOTS_FIELD]
	if not (shots_v is Array):
		return _refuse(outcome, REFUSAL_SHOTS_TYPE)
	if not _is_integral(shot_index):
		return _refuse(outcome, REFUSAL_INDEX_TYPE)

	var shots: Array = (shots_v as Array).duplicate()
	var index: int = int(shot_index)
	var appended: bool = false
	if not shots.has(index):
		shots.append(index)
		appended = true
	outcome["ok"] = true
	outcome["client_sent"] = {
		SHOTS_FIELD: {
			"argument": "args[0]",
			"source": COMMAND_SOURCE,
			"role": "intent",
			"value": index,
			"appended": appended,
			"already_recorded": not appended,
			"derived_from_it": false,
			"bounded_with_it": false,
		},
		EXTRA_FIELD: {
			"argument": OUTCOME_ARGUMENT,
			"source": COMMAND_SOURCE,
			"role": "asserted outcome",
			"claimed": bool(client_claimed_outcome),
			"delivered": false,
			"note": OUTCOME_WHY_CAPABILITY,
		},
	}
	outcome["written"] = {
		SHOTS_FIELD: shots,
		FREE_AVAILABLE_FIELD: false,
		NEW_FREE_STAMP_FIELD: now,
	}
	outcome["field_count"] = SHOOT_WRITE_COUNT
	outcome["recorded_shots_before"] = (shots_v as Array).duplicate()
	outcome["recorded_list_length"] = shots.size()
	outcome["length_bound"] = LIST_BOUND_RECORD["length_bound_exists"]
	outcome["membership_tested"] = LIST_BOUND_RECORD["membership_test_exists"]
	outcome["extra_flag_from_client_claim"] = false
	if bool(client_claimed_outcome):
		outcome["refusals"] = [OUTCOME_ARGUMENT]
		outcome["divergences"] = DIVERGENCES.duplicate(true)
	return outcome


## The shared result shape, so all three transitions report the same columns.
static func _base(command: String, now: int) -> Dictionary:
	return {
		"ok": false,
		"error": "",
		"command": command,
		"command_source": COMMAND_SOURCE,
		"store": PRIVATE_STATE_KEY,
		"clock_source": "server",
		"clock": now,
		"client_sent": {},
		"written": {},
		"field_count": 0,
		"refusals": [],
		"divergences": [],
		"extra_flag_from_client_claim": false,
		"charged": false,
		"resources_moved": 0,
		"client_argument_count": 1,
	}


## A refusal: `ok` false, a named error, and NO written fields at all, so a
## refused transition can never be mistaken for one that wrote something.
static func _refuse(outcome: Dictionary, reason: String) -> Dictionary:
	outcome["error"] = reason
	outcome["written"] = {}
	outcome["field_count"] = 0
	outcome["refusals"] = [reason]
	return outcome


## True for an integral int or an integral float.
##
## Every committed value of these six fields is a whole number or an array, and
## JSON decodes numbers as floats. A string, a bool, a null, and a fractional
## number all fail, so a malformed input cannot reach a written field.
static func _is_integral(value: Variant) -> bool:
	var kind: int = typeof(value)
	if kind != TYPE_INT and kind != TYPE_FLOAT:
		return false
	var as_float: float = float(value)
	return is_equal_approx(as_float, float(int(as_float)))