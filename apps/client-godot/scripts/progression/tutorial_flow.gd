extends RefCounted
## Typed read-only projection and gate mirror for the tutorial/progression flow
## (OpenSpec `tutorial`, M9 line 3, design D1/D2/D4/D5/D6/D7).
##
## This module holds **no node, no clock, no request, and no content of its
## own**. It never builds a request body: the `GameApi` forwarder owns that, in
## the same shape `level_up_town()` uses, because a tutorial step is **intent**
## and the outcome is derived server-side. `test_tutorial.gd` asserts the absence
## structurally.
##
## ## What is ESTABLISHED (recorded verbatim, never derived)
##
##   * the legacy surface is **one branch with one write** (`command.py:60-66`):
##     the gate is `tutorial_step >= 25 or tutorial_step == 15` and the write is
##     `playerInfo["completed_tutorial"] = 1`. There is **no** upper bound, **no**
##     lower bound, and **no** type check in the gate itself;
##   * `completed_tutorial` has exactly **one** occurrence in the whole legacy
##     server and **zero** readers — the **tenth** committed field in this project
##     with no legacy consumer, and the second write-only progression family after
##     the three research counters;
##   * `tutorial_step` (4 occurrences over 3 lines) is a **local** in that branch
##     and is **never persisted**: the save carries no step, so no progress
##     position survives a reload and none is invented here;
##   * the flag reaches the client only through `get_player_info.py:15`, which
##     includes the whole `playerInfo` object — so the projection reads
##     `playerInfo`, **never** `maps[0]`;
##   * the nine steps `16..24` inclusive do **not** complete. They are the gate's
##     **hole**, and they are named here so a caller can never mistake a hole step
##     for a malformed one;
##   * `"15"`, a missing argument, and `null` each raise in legacy and escape as
##     HTTP 500. This line's **deliberate divergence** replaces those three with
##     named refusals. Nothing else about an accepted step is reproduced
##     differently, and the divergence is confined to failure handling.
##
## ## What is DERIVED here
##
##   * nothing numeric. `gate_satisfied()` and `gate_verdict()` are a **mirror**
##     of the committed expression, not a second derivation of it, and the mirror
##     is **total**: it answers `false` / `"none"` for every value that is not a
##     strict `int` rather than raising, because a render pass must never raise.
##
## ## What that strictness costs, stated plainly
##
## Two wire types are refused where legacy does not refuse them, and **both** are
## recorded rather than smoothed:
##
##   * a **float** step. Legacy **completes** on `15.0`, because `15.0 == 15`.
##     `LEGACY_ACCEPTS_FLOAT_STEP` records that measured fact, and the endpoint
##     refuses a float anyway (`invalid_step`), so this mirror agrees with the
##     **service** rather than with legacy. The resulting save state is identical
##     either way, because a declined `15.0` leaves the flag untouched exactly as
##     the refusal does.
##   * a **bool** step. Legacy *declines* `true` — and so does this mirror — so
##     here the two agree completely and only the response differs.
##
## The direction matters and is not interchangeable: an **outgoing** step must be
## a strict `int` (`_strict_int`), while an **incoming** value is read through
## `_integer`, because this engine decodes every JSON number as a `float` — so
## the client's own save records `0.0` for a flag legacy wrote as `0`, and the
## service's `25` arrives as `25.0`. Reusing one rule for both directions would
## either refuse every genuine response or accept every float a caller sends.
##
## ## What is deliberately absent
##
## **No step, ratio, remaining time, total step count, or completion state is
## derived.** The save stores no step and no legacy reader consumes the flag, so
## every one of those figures would be fabricated. **No reward is read, shown, or
## paid** — there is none. **No bound is added** to the gate: the legacy server
## has none, so closing one would be an invented rule, and authoritative
## validation belongs to Server v1 / M13.
##
## ## The projection is read-only and says which record it read
##
## `record()` reports `playerInfo` and never `maps[0]`. A surface that wanted to
## show the flag on the map would be inventing a location the save does not use.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The save-level record the flag lives in, verbatim from the legacy write and
## from `get_player_info.py:15`. Named here so a caller can never guess a path.
const PLAYER_INFO_RECORD := "playerInfo"
## The one key this line reads and the one the legacy branch writes.
const FLAG_KEY := "completed_tutorial"
## The single legacy command the service derives.
const COMPLETE_TUTORIAL_COMMAND := "complete_tutorial"
## The committed gate, as two constants rather than as an expression evaluated at
## a call site. `GATE_EXPRESSION` records the source text verbatim so the report
## can print what was committed rather than what this module would spell.
const GATE_LOWER_ARM := 25
const GATE_EXACT_ARM := 15
const GATE_EXPRESSION := "tutorial_step >= 25 or tutorial_step == 15"
## The hole: the steps the gate declines that a caller could mistake for
## malformed input. `[16, 24]` inclusive, so nine values.
const GATE_HOLE_LOW := 16
const GATE_HOLE_HIGH := 24
const GATE_HOLE_SIZE := 9
## The committed post-completion value, and the committed corpus's own value.
## The corpus records `0`, so the `0 -> 1` transition is exercisable exactly
## **once per disposable copy** — the reason the fixture needs two rounds.
const COMMITTED_FLAG_BEFORE := 0
const COMMITTED_FLAG_AFTER := 1
## The committed writer, and the measured reader count beside it.
const FLAG_WRITER_LINE := "command.py:65"
const FLAG_READER_COUNT := 0
## The three shapes the legacy gate raises on, and the status they escape as.
## RECORDED, NOT REPRODUCED (design D5).
const RAISING_SHAPES := ["string_step", "missing_step", "null_step"]
const RAISING_STATUS := 500
## The boundary steps the fixture replay covers from both sides, plus the negative
## case. `replay_oracle_is_executed_legacy` is a constant `false`: the gate's
## boundaries are ESTABLISHED from source, while only step 15 has an executed
## oracle.
const REPLAY_BOUNDARY_STEPS := [14, 15, 24, 25, 26, -1]
const REPLAY_ORACLE_IS_EXECUTED_LEGACY := false

## The two arms, named. A bare boolean would hide which arm applied.
const ARM_LOWER := "lower_arm"
const ARM_EXACT := "exact_arm"
const ARM_NONE := "none"
## The one wire kind this line ever produces for a step. The service names its
## vocabulary too (`tutorial_envelope.step_kind`), and the two are kept in step:
## a completion reports `"integer"`, never a Python class name and never `"int"`.
const STEP_KIND_INTEGER := "integer"

## The refusals. All three are **structural**: no verdict can be built from the
## save, so `ok` is false rather than a verdict that guessed.
const REASON_ABSENT_PLAYER_INFO := "absent_player_info"
const REASON_NON_OBJECT_PLAYER_INFO := "non_object_player_info"
const REASON_ABSENT_FLAG := "absent_completed_tutorial"
const REASON_UNREADABLE_FLAG := "unreadable_completed_tutorial"

## Every refusal this module can return, as a closed set. A caller enumerates
## this rather than matching strings, and the suite pins it, so a refusal added
## without a note here is a visible edit instead of a silent one.
const REFUSAL_REASONS := [
	REASON_ABSENT_PLAYER_INFO,
	REASON_NON_OBJECT_PLAYER_INFO,
	REASON_ABSENT_FLAG,
	REASON_UNREADABLE_FLAG,
]

## Measured, not reproduced: legacy's gate is a Python comparison, so the float
## `15.0` completes it. Recorded because it is the one wire type whose legacy
## outcome differs from this contract's refusal in no way that reaches the save.
const LEGACY_ACCEPTS_FLOAT_STEP := true

## The derived 8-slot resource vector the service sends: **all zeros** (tutorial
## design D4). Recorded here so a report can print the vector the endpoint uses
## and so the "no reward" claim names the thing that would have moved a balance if
## one existed. It is the endpoint's derivation, never a client's to set.
const NEUTRAL_VECTOR := [0, 0, 0, 0, 0, 0, 0, 0]
## The number of slots that vector carries, as the committed corpus records it.
const NEUTRAL_VECTOR_SLOTS := 8

## The committed capture manifest, which is the tutorial fixture's own ORACLE: its
## `gate` block is compared field by field against this module's mirror, so the
## committed expression and the client cannot drift apart silently.
const CAPTURE_MANIFEST := "tests/fixtures/godot-tutorial/capture-manifest.json"

## The committed content absence, stated as a measured constant so the report can
## print it. There is **no** committed tutorial content anywhere: no step names,
## no reward table, no step count.
const COMMITTED_CONTENT_OCCURRENCES := 0

## The absence inventory — the contract, not a list of omissions. Each entry is a
## helper a reader might expect and that this line delivers **not at all**. The
## suite asserts no delivered code identifier is named after any of them, which
## is what makes "not implemented" mechanical rather than a promise.
const ABSENT_HELPERS := [
	"tutorial_step_count",
	"tutorial_total_steps",
	"tutorial_progress_ratio",
	"tutorial_remaining_steps",
	"tutorial_remaining_time",
	"tutorial_reward",
	"tutorial_reward_for",
	"tutorial_reward_amount",
	"mark_tutorial_complete",
	"tutorial_unlocked",
	"tutorial_bounds",
	"clamp_tutorial_step",
	"fast_forward",
	"intent_body",
	"tutorial_vector",
	"tutorial_price",
]


## The whole static-function inventory of this module, pinned by the suite.
##
## This is the anti-invention guard made checkable: adding a helper is a visible
## edit to this list, so an invented derivation cannot be added quietly and the
## absence inventory above stays honest. Names beginning with `_` are internal and
## listed too, so no private helper can be added unseen either.
const STATIC_FUNCTIONS := [
	"gate_satisfied",
	"gate_verdict",
	"gate_hole_steps",
	"gate_record",
	"is_step",
	"completed_flag",
	"project",
	"evaluate",
	"offers_completion",
	"readout_text",
	"confirm_text",
	"step_label",
	"record",
	"result_failure",
	"parse_result",
	"_integer",
	"_strict_int",
	"_type_name",
	"_result_error",
	"_parse_flag_pair",
	"_gate_field_equal",
	"_number_text",
	"_bool_text",
	"_verdict_text",
]


# ---------------------------------------------------------------------------
# The named gate mirror, and its named inverse
# ---------------------------------------------------------------------------


## True when the committed gate completes the tutorial for `step` — the one named
## place the gate exists on the client, mirroring
## `apps/compat-api/tutorial_envelope.py`'s equally named `gate_satisfied` so the
## client's model, the service, the tests, and the structural report cannot
## disagree about the thresholds. A future revision of the gate is **one** edit in
## each layer rather than an audit.
##
## **A step must be a strict `int`.** A `bool` and a `float` are both refused,
## which is the endpoint's own `invalid_step` rule: `true` is not a step any
## legacy player sent, and legacy *completes* on `15.0` while this contract
## refuses it — a deliberate, recorded divergence. Note the direction: this
## function judges the **outgoing** step, which the caller holds as a real
## integer, whereas `_integer()` widens integers on the **incoming** side, where
## every JSON number arrives as a float. A render pass must never raise, so the
## answer here is `false` rather than an error.
static func gate_satisfied(step: Variant) -> bool:
	var exact: Variant = _strict_int(step)
	if exact == null:
		return false
	return int(exact) >= GATE_LOWER_ARM or int(exact) == GATE_EXACT_ARM


## Which arm of the committed disjunction fires for `step`, or `ARM_NONE` — the
## **named inverse** of `gate_satisfied()`, so a report, a fixture record, or a
## surface can tell the two arms apart instead of reading a bare boolean that
## hides which one applied.
##
## Total over the same domain as `gate_satisfied()`, with the same caveat. The
## ordering mirrors legacy's own `or` short-circuit: the `>=` arm is tested first,
## so a step satisfying **both** is reported as `ARM_LOWER`.
static func gate_verdict(step: Variant) -> String:
	var exact: Variant = _strict_int(step)
	if exact == null:
		return ARM_NONE
	if int(exact) >= GATE_LOWER_ARM:
		return ARM_LOWER
	if int(exact) == GATE_EXACT_ARM:
		return ARM_EXACT
	return ARM_NONE


## True when `step` is a value this contract can compare: a **strict integer**.
##
## **A `bool` is refused.** `true` is not a step any legacy player reached, and
## accepting it would carry a wire type the committed gate never saw.
##
## **A `float` is refused too**, matching `apps/compat-api/tutorial_envelope.py`'s
## `validate_step`, which raises `invalid_step` for it. This is the one place the
## contract is *stricter* than legacy, and the divergence is recorded rather than
## smoothed: `LEGACY_ACCEPTS_FLOAT_STEP` records that legacy **completes** on
## `15.0`. The resulting save state is identical either way, because a declined
## `15.0` leaves the flag untouched just as this refusal does.
static func is_step(value: Variant) -> bool:
	return _strict_int(value) != null


## The gate's **hole** — the nine declined steps a caller could mistake for
## malformed input — as a fresh array each call, in ascending order. A caller
## never mutates this module's constants through the returned value.
static func gate_hole_steps() -> Array:
	var hole: Array = []
	for step in range(GATE_HOLE_LOW, GATE_HOLE_HIGH + 1):
		hole.append(step)
	return hole


## The committed gate as the report records it: both arms, the expression
## verbatim, the hole, and the three absences the gate does **not** have. Every
## number here is a constant above, so the record cannot drift from the mirror.
static func gate_record() -> Dictionary:
	return {
		"command": COMPLETE_TUTORIAL_COMMAND,
		"expression": GATE_EXPRESSION,
		"lower_arm": GATE_LOWER_ARM,
		"exact_arm": GATE_EXACT_ARM,
		"hole_low": GATE_HOLE_LOW,
		"hole_high": GATE_HOLE_HIGH,
		"hole_size": GATE_HOLE_SIZE,
		"hole_steps": gate_hole_steps(),
		"has_upper_bound": false,
		"has_lower_bound": false,
		"has_type_check": false,
		"raising_shapes": (RAISING_SHAPES as Array).duplicate(),
		"raising_status": RAISING_STATUS,
		"replay_boundary_steps": (REPLAY_BOUNDARY_STEPS as Array).duplicate(),
		"replay_oracle_is_executed_legacy": REPLAY_ORACLE_IS_EXECUTED_LEGACY,
	}


# ---------------------------------------------------------------------------
# The projection: the recorded flag, verbatim
# ---------------------------------------------------------------------------


## The recorded completion flag, exactly as the save carries it.
##
## Returns `{ok, reason, resolvable, stored, completed, record, key}`:
##   * `ok`          the save records a flag this client can read;
##   * `resolvable`  the same fact, as a bare boolean for callers that only need
##     the decision — `ok` and `resolvable` are deliberately the same value, so a
##     surface cannot read one and be told something different by the other;
##   * `stored`      the value **verbatim** — never coerced, never normalised,
##     and never turned into a boolean in place of the recorded number;
##   * `completed`   `true`/`false` **only** when `ok`, and `null` when it is not.
##     An unreadable flag is **never** reported as "not complete": that would
##     present an undecided state as a decided one, and the legacy branch would
##     have written the key regardless.
##
## A flag that is **present but not a strict integer** is refused with its own
## reason rather than folded into the absent case. The committed corpus records
## the flag as an integer, so a string or a boolean there would be a shape no
## legacy player reached, and reporting `completed: false` for it would be a
## decision this client has no basis to make.
##
## `record` and `key` name where the value was read, so a surface can state the
## source instead of implying the flag is a map field.
static func completed_flag(player_info: Variant) -> Dictionary:
	var flag := {
		"ok": false,
		"reason": REASON_ABSENT_FLAG,
		"resolvable": false,
		"stored": null,
		"completed": null,
		"record": PLAYER_INFO_RECORD,
		"key": FLAG_KEY,
	}
	if not (player_info is Dictionary):
		flag["reason"] = REASON_ABSENT_FLAG
		return flag
	var stored: Variant = (player_info as Dictionary).get(FLAG_KEY)
	if stored == null:
		return flag
	var exact: Variant = _integer(stored)
	if exact == null:
		flag["reason"] = REASON_UNREADABLE_FLAG
		return flag
	flag["ok"] = true
	flag["resolvable"] = true
	flag["stored"] = stored
	flag["completed"] = int(exact) == COMMITTED_FLAG_AFTER
	return flag


## The projection for one save document, read from the **save-level**
## `playerInfo` object and never from `maps[0]`.
##
## Fails closed on a save that is not an object, on one with no `playerInfo`, and
## on a `playerInfo` that is not an object — each with its own named reason, so a
## surface can say what it found. Every refusal hands back the recorded value as a
## **snapshot** rather than an alias, so a caller can never write through it.
static func project(save: Variant) -> Dictionary:
	var projection := {
		"ok": false,
		"reason": "",
		"error": "",
		"resolvable": false,
		"stored": null,
		"completed": null,
		"record": PLAYER_INFO_RECORD,
		"key": FLAG_KEY,
		"already_completed": false,
	}
	if not (save is Dictionary):
		projection["reason"] = REASON_ABSENT_PLAYER_INFO
		projection["error"] = ("[tutorial] projection refused (%s): the save is a "
			% REASON_ABSENT_PLAYER_INFO + "%s, not an object"
				% _type_name(save))
		return projection
	var body: Dictionary = save as Dictionary
	if not body.has(PLAYER_INFO_RECORD):
		projection["reason"] = REASON_ABSENT_PLAYER_INFO
		projection["error"] = ("[tutorial] projection refused (%s): this save "
			% REASON_ABSENT_PLAYER_INFO + "records no %s object"
				% PLAYER_INFO_RECORD)
		return projection
	var player_info: Variant = body[PLAYER_INFO_RECORD]
	if not (player_info is Dictionary):
		projection["reason"] = REASON_NON_OBJECT_PLAYER_INFO
		projection["error"] = ("[tutorial] projection refused (%s): this save's "
			% REASON_NON_OBJECT_PLAYER_INFO + "%s is a %s, not an object"
				% [PLAYER_INFO_RECORD, _type_name(player_info)])
		return projection
	var flag := completed_flag(player_info)
	if not bool(flag.get("ok", false)):
		projection["reason"] = str(flag.get("reason", REASON_ABSENT_FLAG))
		projection["error"] = ("[tutorial] projection refused (%s): this save "
			% str(projection["reason"]) + "records no readable %s.%s (found %s)"
				% [PLAYER_INFO_RECORD, FLAG_KEY,
					_type_name((player_info as Dictionary).get(FLAG_KEY))])
		return projection
	projection["ok"] = true
	projection["resolvable"] = true
	projection["stored"] = flag["stored"]
	projection["completed"] = flag["completed"]
	projection["already_completed"] = bool(flag["completed"])
	return projection


## The whole tutorial evaluation for one save and one client step, and the ONLY
## entry point a surface uses. Returns
## `{ok, reason, error, step, step_kind, gate_satisfied, gate_arm, in_gate_hole,
## resolvable, stored, completed, already_completed, offers, no_op_reason,
## command, record, key}`.
##
## The refusals, in evaluation order — all **structural**, so `ok` is false and
## no step is judged:
##   * `absent_player_info`            the save records no `playerInfo` object;
##   * `non_object_player_info`        its `playerInfo` is not an object;
##   * `absent_completed_tutorial`     it records no flag at all;
##   * `unreadable_completed_tutorial` it records one that is not a strict
##     integer, which no legacy save carries.
##
## **A step this contract cannot compare is not a refusal here.** It is reported
## as `gate_satisfied: false` with `gate_arm: "none"`, because the mirror is
## total by design and the **service** owns the named refusal for a malformed
## step. Splitting it this way keeps one authority for each decision: the client
## says "this step does not complete", the service says "this step is not a step".
##
## The two no-op cases are **verdicts, not refusals**: `gate_declined` for a step
## the gate declines and `already_completed` for a flag already at the committed
## post-value. Legacy answers `{"result": "success"}` and changes nothing in both,
## so reporting either as an error would be a divergence with no evidence behind
## it.
static func evaluate(save: Variant, step: Variant) -> Dictionary:
	var projection := project(save)
	var evaluation := {
		"ok": false,
		"reason": str(projection.get("reason", "")),
		"error": str(projection.get("error", "")),
		"step": null,
		"step_kind": _type_name(step),
		"gate_satisfied": false,
		"gate_arm": ARM_NONE,
		"in_gate_hole": false,
		"resolvable": false,
		"stored": null,
		"completed": null,
		"already_completed": false,
		"offers": false,
		"no_op_reason": "",
		"command": COMPLETE_TUTORIAL_COMMAND,
		"record": PLAYER_INFO_RECORD,
		"key": FLAG_KEY,
	}
	if not bool(projection.get("ok", false)):
		return evaluation
	# The OUTGOING step, so the strict rule applies: a float the caller supplies
	# is a caller mistake and the service refuses it too, while the float widening
	# this client sees on every value it READS is handled by `_integer()` inside
	# `project()` above.
	var exact: Variant = _strict_int(step)
	if exact != null:
		evaluation["step"] = int(exact)
		evaluation["step_kind"] = STEP_KIND_INTEGER
	evaluation["gate_satisfied"] = gate_satisfied(step)
	evaluation["gate_arm"] = gate_verdict(step)
	evaluation["in_gate_hole"] = exact != null \
		and gate_hole_steps().has(int(exact))
	evaluation["resolvable"] = true
	evaluation["stored"] = projection["stored"]
	evaluation["completed"] = projection["completed"]
	evaluation["already_completed"] = bool(projection["already_completed"])
	evaluation["ok"] = true
	if bool(evaluation["already_completed"]):
		evaluation["no_op_reason"] = "already_completed"
		return evaluation
	if not bool(evaluation["gate_satisfied"]):
		evaluation["no_op_reason"] = "gate_declined"
		return evaluation
	evaluation["offers"] = true
	return evaluation


## True when the evaluation offers a completion this client may report. Every
## refusal, and both no-op verdicts, offer nothing — which is why a surface can
## never show a "confirm" affordance for a step the gate declines or for a
## tutorial the save says is already finished.
static func offers_completion(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false)) \
		and str(evaluation.get("no_op_reason", "")) == "" \
		and bool(evaluation.get("offers", false))


## The tutorial readout: where the flag is read from, its recorded value, whether
## the save already records the tutorial complete, the committed gate and its
## hole, and the verdict for this step.
##
## **No step, ratio, remaining time, or total step count appears**, because the
## save stores none and no legacy reader consumes the flag. A hole step is named
## as a hole rather than as an error, because declining it is the gate's own
## behaviour and not a fault.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var parts: Array = []
	parts.append("flag: %s.%s = %s"
		% [str(evaluation.get("record", PLAYER_INFO_RECORD)),
			str(evaluation.get("key", FLAG_KEY)),
			_number_text(evaluation.get("stored", null))])
	parts.append("completed: %s" % _bool_text(evaluation.get("completed", null)))
	parts.append("gate: %s" % GATE_EXPRESSION)
	parts.append("hole: %d..%d (%d steps)"
		% [GATE_HOLE_LOW, GATE_HOLE_HIGH, GATE_HOLE_SIZE])
	parts.append("step: %s" % _number_text(evaluation.get("step", null)))
	parts.append("verdict: %s" % _verdict_text(evaluation))
	return " | ".join(parts)


## The armed surface's own confirm text. It names the **gate** and says the
## service decides, so a player is never shown a completion the client chose as if
## it were authoritative. No reward, price, or amount appears anywhere in it,
## because no legacy branch pays one.
static func confirm_text(evaluation: Dictionary) -> String:
	if not offers_completion(evaluation):
		return ""
	var step := int(evaluation.get("step", 0))
	var write := "%s.%s = %d" % [PLAYER_INFO_RECORD, FLAG_KEY,
		COMMITTED_FLAG_AFTER]
	return ("report tutorial step %d? — the committed gate is %s, so this step "
		% [step, GATE_EXPRESSION]
		+ "completes it and the service writes " + write
		+ " itself. No reward is paid: no legacy branch reads a reward and none "
		+ "is committed")


## The action's own button label, so a confirm names the exact action it will
## send rather than a generic "Confirm".
static func step_label() -> String:
	return "Report tutorial step"


## The committed tutorial facts as the evidence report records them: the record
## and key, both gate arms, the hole, the three absences, the writer line beside
## the measured zero reader count, the corpus's own flag, and the whole
## static-function inventory this module pins. Nothing here restates a number the
## constants above already carry, and nothing is computed by the client's own
## arithmetic.
static func record() -> Dictionary:
	return {
		"record_name": PLAYER_INFO_RECORD,
		"key": FLAG_KEY,
		"command": COMPLETE_TUTORIAL_COMMAND,
		"gate": gate_record(),
		"corpus_flag_before": COMMITTED_FLAG_BEFORE,
		"corpus_flag_after": COMMITTED_FLAG_AFTER,
		"one_round_per_transition": ("the corpus records %d and any completing "
			% COMMITTED_FLAG_BEFORE
			+ "step writes %d, so the %d -> %d transition is exercisable exactly "
				% [COMMITTED_FLAG_AFTER, COMMITTED_FLAG_BEFORE,
					COMMITTED_FLAG_AFTER]
			+ "once per disposable copy — which is why the fixture needs two "
			+ "rounds rather than one"),
		"flag_writer_line": FLAG_WRITER_LINE,
		"flag_readers_in_legacy": FLAG_READER_COUNT,
		"committed_content_occurrences": COMMITTED_CONTENT_OCCURRENCES,
		"legacy_accepts_float_step": LEGACY_ACCEPTS_FLOAT_STEP,
		"static_functions": (STATIC_FUNCTIONS as Array).duplicate(),
		"absent_helpers": (ABSENT_HELPERS as Array).duplicate(),
		"no_step_persisted": true,
		"no_reward_paid": true,
		"no_gate_bounds_added": true,
		"legacy_raising_shapes_reproduced": false,
	}


## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and check,
## and the one derived reading states what it is derived from.
const PROVENANCE := {
	"established": [
		{"fact": "the legacy tutorial surface is ONE branch with ONE write: the "
			+ "gate is tutorial_step >= 25 or tutorial_step == 15 and the write "
			+ "is playerInfo[\"completed_tutorial\"] = 1",
			"evidence": "command.py:60-66 (committed legacy server source)"},
		{"fact": "completed_tutorial has exactly ONE occurrence in the whole "
			+ "legacy server and ZERO readers",
			"evidence": "measured across the eleven root modules; the writer is "
				+ "command.py:65. This is the tenth committed field in this "
				+ "project with no legacy consumer"},
		{"fact": "tutorial_step appears 4 times over 3 lines and is a LOCAL in "
			+ "that branch: it is never persisted",
			"evidence": "command.py:63. The save therefore carries no step, so "
				+ "no progress position survives a reload and none is invented"},
		{"fact": "the flag reaches the client only through get_player_info.py:15, "
			+ "which includes the whole playerInfo object",
			"evidence": "get_player_info.py:15. This is why the projection reads "
				+ "playerInfo and NEVER maps[0]"},
		{"fact": "the nine steps 16..24 inclusive do NOT complete",
			"evidence": "the committed disjunction has no third arm; measured "
				+ "over the gate directly. Named here so a hole step is never "
				+ "reported as malformed input"},
		{"fact": "the gate carries NO upper bound, NO lower bound, and NO type "
			+ "check of its own",
			"evidence": "command.py:63. Closing a bound the legacy server does "
				+ "not have would be an invented rule; authoritative validation "
				+ "belongs to Server v1 / M13"},
		{"fact": "a string step, a missing argument, and a null step each RAISE "
			+ "in legacy and escape as HTTP 500",
			"evidence": "command.py:63 (TypeError), the args[0] IndexError, and "
				+ "the None comparison; executed in the committed capture and "
				+ "recorded in tests/fixtures/godot-tutorial/"},
		{"fact": "the committed corpus records completed_tutorial = 0, and "
			+ "completing a tutorial moves no stored resource at all",
			"evidence": "tests/saves/fresh-player.json; the committed "
				+ "transaction in tests/fixtures/godot-tutorial/steps/neutral/, "
				+ "whose whole diff is the single flag leaf"},
	],
	"derived": [
		{"fact": "gate_satisfied() and gate_verdict() are a client MIRROR of the "
			+ "committed expression, and the mirror is TOTAL: false / \"none\" "
			+ "for every non-integer rather than raising",
			"evidence": "derived from the client's own transport, not from "
				+ "legacy. The client parses every JSON number as a float, so a "
				+ "raising predicate would raise inside a render pass. What "
				+ "totality costs is stated in the module comment: legacy "
				+ "COMPLETES on 15.0, and this mirror answers false for it — the "
				+ "same state outcome a declined step produces, because the "
				+ "refusal precedes any dispatch"},
		{"fact": "the readout's wording and the composition of its lines",
			"evidence": "derived: no authentic legacy tutorial panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


## The evidence's explicit non-claims.
const NON_CLAIMS := [
	"no step, ratio, remaining time, total step count, or completion state is "
		+ "derived, because the save persists no step and no legacy branch reads "
		+ "the flag: every one of those figures would be fabricated",
	"no reward is paid, shown, or read, and none is committed: paying one would "
		+ "invent an economy",
	"no bound is added to the gate, so a client may still report any integer; "
		+ "the legacy gate has none and authoritative validation belongs to "
		+ "Server v1 / M13",
	"the flag is read from the save-level playerInfo and never from maps[0]: the "
		+ "legacy branch writes playerInfo and the map carries no such key",
	"the three shapes legacy raises on are RECORDED and deliberately NOT "
		+ "reproduced: a crash is not a behaviour, so each gets a named refusal "
		+ "instead. Every accepted step's state transition IS reproduced exactly",
	"a float step is refused where legacy completes; the measured legacy fact is "
		+ "recorded as LEGACY_ACCEPTS_FLOAT_STEP and the resulting save state is "
		+ "identical either way",
	"the gate's boundary steps are ESTABLISHED from committed source while only "
		+ "step 15 has an executed oracle, so replay_oracle_is_executed_legacy "
		+ "is false",
	"parity covers two recorded transactions and one probe against the "
		+ "fresh-player corpus only: no progressed player and no other command",
	"no un-complete path exists: the legacy branch writes 1 and nothing ever "
		+ "writes it back to 0",
	"no pixel-parity oracle against the legacy client exists",
	"the committed capture runs the fake GameApi implementation, a deterministic "
		+ "test double rather than a parity oracle",
]


# ---------------------------------------------------------------------------
# The typed result
# ---------------------------------------------------------------------------


## One tutorial response, typed and fail-closed. Every field is **authoritative
## from the response**: the client applies `tutorial`, `gate`, `changed`, and
## `resources` verbatim and never prefers its own mirror over them, so a wrong
## client-side gate can never be silently compounded.
class TutorialResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field, so
	## tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The service's own `tutorial` block: the command, the echoed step and its
	## wire kind, the record and key, `flag_before` / `flag_after` / `flag_moved`,
	## `gate_satisfied` / `gate_arm` / `in_gate_hole`, `already_completed`,
	## `no_op_reason`, `dispatched`, `resolvable`, `completed`, and `stored`.
	var tutorial: Dictionary = {}
	## The service's `gate` record, reported as content.
	var gate: Dictionary = {}
	## The changed-leaf list. For an accepted completion it is exactly the single
	## flag leaf; for either no-op it is empty.
	var changed: Array = []
	var resources: BootData.Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for the tutorial intent (never a partial payload).
static func result_failure(code: String, message: String) -> TutorialResult:
	var result := TutorialResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses a v0 tutorial envelope — success or structured error — into the typed
## result, fail-closed in both directions. The envelope must be a JSON object
## reporting `ok: true`, the protocol must be the v0 one, the legacy result string
## must be `success`, `tutorial` must carry every documented field, `gate` must
## be the committed gate record, and `resources` must be the seven non-negative
## integers every other response carries.
##
## Four responses are refused because they would describe a different contract:
##   * a `tutorial.command` other than the one committed command;
##   * a `tutorial.record` / `tutorial.key` pair naming anything but
##     `playerInfo` / `completed_tutorial`, which is how a map-borne flag would
##     arrive;
##   * a `changed` list that is non-empty while the response reports no dispatch,
##     or that omits the flag leaf while one does;
##   * a `gate_satisfied: true` with a `gate_arm` outside the closed arm set.
static func parse_result(payload: Variant) -> TutorialResult:
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
			"tutorial response did not report the legacy success result")
	var tutorial: Variant = envelope.get("tutorial")
	if not (tutorial is Dictionary):
		return result_failure("bad_response",
			"the tutorial response carries no tutorial block")
	var block: Dictionary = tutorial as Dictionary
	for field: String in ["command", "step", "step_kind", "record", "key",
			"flag_before", "flag_after", "flag_moved", "gate_satisfied",
			"gate_arm", "in_gate_hole", "already_completed", "no_op_reason",
			"dispatched", "resolvable", "completed", "stored"]:
		if not block.has(field):
			return result_failure("bad_response",
				"the tutorial response's tutorial block carries no %s" % field)
	if str(block.get("command", "")) != COMPLETE_TUTORIAL_COMMAND:
		var derived := str(block.get("command", ""))
		return result_failure("bad_response",
			("the tutorial response derived command '%s', which is not the "
				% derived)
				+ ("committed one %s" % COMPLETE_TUTORIAL_COMMAND))
	if str(block.get("record", "")) != PLAYER_INFO_RECORD \
			or str(block.get("key", "")) != FLAG_KEY:
		var named := "%s.%s" % [str(block.get("record", "")),
			str(block.get("key", ""))]
		var committed := "%s.%s" % [PLAYER_INFO_RECORD, FLAG_KEY]
		return result_failure("bad_response",
			("the tutorial response names %s, which is not the committed %s: "
				% [named, committed]
				+ "the flag is a save-level record, never a map field"))
	var arm := str(block.get("gate_arm", ""))
	if not [ARM_LOWER, ARM_EXACT, ARM_NONE].has(arm):
		return result_failure("bad_response",
			("the tutorial response reported gate arm '%s', which is outside "
				% arm) + "the closed arm set")
	var gate: Variant = envelope.get("gate")
	if not (gate is Dictionary):
		return result_failure("bad_response",
			"the tutorial response carries no gate record")
	var gate_body: Dictionary = gate as Dictionary
	var expected_gate := gate_record()
	for field: String in ["command", "expression", "lower_arm", "exact_arm",
			"hole_low", "hole_high", "hole_size", "hole_steps",
			"has_upper_bound", "has_lower_bound", "has_type_check",
			"raising_shapes", "raising_status", "replay_boundary_steps",
			"replay_oracle_is_executed_legacy"]:
		if not gate_body.has(field):
			return result_failure("bad_response",
				"the tutorial response's gate record carries no %s" % field)
		if not _gate_field_equal(gate_body.get(field),
				expected_gate.get(field)):
			return result_failure("bad_response",
				("the tutorial response's gate record reports %s = '%s', which "
					% [field, str(gate_body.get(field, ""))]
					+ "contradicts the committed gate this client mirrors"))
	var changed: Variant = envelope.get("changed")
	if not (changed is Array):
		return result_failure("bad_response",
			"the tutorial response carries no changed list")
	var leaves: Array = changed as Array
	var flag_leaf := "/%s/%s" % [PLAYER_INFO_RECORD, FLAG_KEY]
	if block.get("dispatched") == true:
		if leaves != [flag_leaf]:
			return result_failure("bad_response",
				("the tutorial response dispatched a completion but reported "
					+ "changed leaves %s, which is not exactly the flag leaf")
					% str(leaves))
	elif not leaves.is_empty():
		return result_failure("bad_response",
			("the tutorial response reported no dispatch yet claims changed "
				+ "leaves %s") % str(leaves))
	var pair: Variant = _parse_flag_pair(block)
	if pair == null:
		return result_failure("bad_response",
			"the tutorial response carries no readable flag pair")
	var flag_body: Dictionary = pair
	var pair_moved: bool = int(flag_body["flag_after"]) \
		!= int(flag_body["flag_before"])
	if block.get("flag_moved") != pair_moved:
		return result_failure("bad_response",
			("the tutorial response reports flag_moved = %s while its own "
				% str(block.get("flag_moved", ""))
				+ "flag pair %d -> %d says otherwise")
				% [int(flag_body["flag_before"]), int(flag_body["flag_after"])])
	if block.get("dispatched") == true and not pair_moved:
		return result_failure("bad_response",
			("the tutorial response dispatched a completion yet its flag pair "
				+ "%d -> %d did not move")
				% [int(flag_body["flag_before"]), int(flag_body["flag_after"])])
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return result_failure("bad_response",
			"tutorial response carries no resources object")
	var resources := BootData._parse_resources(resources_raw)
	if resources == null:
		return result_failure("bad_response",
			"tutorial resources are not seven non-negative integers")
	var result := TutorialResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return result_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.tutorial = block.duplicate(true)
	result.gate = gate_body.duplicate(true)
	result.changed = leaves.duplicate(true)
	result.resources = resources
	return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## One value as the exact integer it denotes, for the **incoming** direction: an
## `int`, or an integral `float` inside the transported exact-integer range. A
## `bool` and a numeric string both fail closed, because coercing `"15"` to
## fifteen — or `true` to one — would carry a wire type the committed gate never
## saw, and legacy itself raises on a string rather than completing.
##
## The float arm exists **only** because Godot decodes every JSON number as a
## float: it is what lets this client read its own save, whose recorded flag is
## the integer `0` or `1`, and the service's gate record, whose thresholds are
## integers. The **outgoing** step is judged by `_strict_int()` instead.
static func _integer(value: Variant) -> Variant:
	if value is bool:
		return null
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and is_finite(typed) \
				and absf(typed) <= 9007199254740992.0:
			return int(typed)
	return null


## One value as a **strict** integer, for the **outgoing** direction: an `int`, and
## nothing else. A `bool` is refused even though it is an `int` in GDScript, and
## so is a `float`.
##
## This is the deliberate asymmetry with `_integer()` above, and it exists because
## the two directions genuinely differ. A step the *caller* supplies is a real
## integer, so a float there is a caller mistake — and the service refuses it too
## (`validate_step` raises `invalid_step`), so accepting it here would offer a
## completion the endpoint then rejects. A value this client *reads back* is
## always float-widened by the decoder, so there the float arm is mandatory.
static func _strict_int(value: Variant) -> Variant:
	if value is bool:
		return null
	if value is int:
		return int(value)
	return null


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


## The response's `flag_before` / `flag_after` pair, when both are readable
## integers; null otherwise, so a half-read pair is refused as a whole.
static func _parse_flag_pair(block: Dictionary) -> Variant:
	var before: Variant = _integer(block.get("flag_before"))
	var after: Variant = _integer(block.get("flag_after"))
	if before == null or after == null:
		return null
	return {"flag_before": int(before), "flag_after": int(after)}


## Whether one **gate** field agrees with the committed mirror.
##
## This exists because of the transport, and comparing with `str()` is WRONG on
## the pinned engine: **Godot decodes every JSON number as a `float`**, so the
## service's integer `25` arrives as `25.0` and `str(25.0) != str(25)`. A string
## comparison would therefore refuse every genuine response — the offline double
## and the live service alike — and turn a correct envelope into `bad_response`.
## So numbers compare as numbers, arrays compare element-wise, dictionaries
## compare by key, a `bool` compares by identity (never as `0`/`1`), and
## anything else compares as text.
##
## A `bool` is deliberately **not** numeric here: `has_upper_bound` is a real
## boolean, and reading `false` as `0` would let a service report "bounded" by
## sending `0`.
static func _gate_field_equal(actual: Variant, expected: Variant) -> bool:
	if (actual is bool) or (expected is bool):
		return typeof(actual) == typeof(expected) and bool(actual) == bool(expected)
	if (actual is int or actual is float) \
			and (expected is int or expected is float):
		return is_equal_approx(float(actual), float(expected))
	if (actual is Array) and (expected is Array):
		var left: Array = actual
		var right: Array = expected
		if left.size() != right.size():
			return false
		for index in range(left.size()):
			if not _gate_field_equal(left[index], right[index]):
				return false
		return true
	if (actual is Dictionary) and (expected is Dictionary):
		var left: Dictionary = actual
		var right: Dictionary = expected
		if left.size() != right.size():
			return false
		for key: Variant in right.keys():
			if not left.has(key) \
					or not _gate_field_equal(left[key], right[key]):
				return false
		return true
	return str(actual) == str(expected)


## The structured error out of a failing envelope, keeping the service's own code
## so `invalid_step`, `missing_step`, `null_step`, and
## `unresolvable_tutorial_state` reach the caller unchanged.
static func _result_error(envelope: Dictionary) -> TutorialResult:
	var error: Variant = envelope.get("error")
	if not (error is Dictionary):
		return result_failure("bad_response",
			"the tutorial response reports failure with no error object")
	var body: Dictionary = error
	return result_failure(str(body.get("code", "bad_response")),
		str(body.get("message", "")))


## A committed number as the readout renders it, or "unknown" when this contract
## could not read it. Never a substituted zero.
static func _number_text(value: Variant) -> String:
	var exact: Variant = _integer(value)
	if exact == null:
		return "unknown"
	return str(int(exact))


## A derived boolean as the readout renders it. `null` renders as "unknown", not
## as "false": an unreadable flag is never reported as a decided one.
static func _bool_text(value: Variant) -> String:
	if value == null:
		return "unknown"
	return "true" if bool(value) else "false"


## The evaluation's verdict as the readout renders it, distinguishing the two
## no-op reasons from each other and from an offer, because both no-ops are
## legacy-faithful successes that change nothing.
static func _verdict_text(evaluation: Dictionary) -> String:
	if bool(evaluation.get("gate_satisfied", false)):
		return "the gate completes this step"
	match str(evaluation.get("no_op_reason", "")):
		"already_completed":
			return "the save already records the tutorial complete"
		"gate_declined":
			return "the gate declines this step%s" % (" (a hole step)"
				if bool(evaluation.get("in_gate_hole", false)) else "")
	return "no verdict"
