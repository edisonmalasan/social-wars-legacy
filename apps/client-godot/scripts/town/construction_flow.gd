extends RefCounted
## Pure evaluation helpers for the construction flow (building-construction,
## spec "Construction flow"): the single step a row's own state offers next,
## its click progress against the item's committed click requirement, its
## remaining countdown, the refusal reasons, and the readout text. No nodes,
## no I/O, no requests, and **no clock of its own** — the current instant is
## always a parameter — so the town view and its suite consume the same
## functions, exactly as `placement_flow.gd` and `move_flow.gd` serve the
## delivered flows (design D7).
##
## The state machine (design D5) follows the row and nothing else:
##   no construction state      -> `start`   (the service derives the
##                                 countdown from the item's committed
##                                 `build_time`; the client sends no
##                                 duration). A row that records nothing is
##                                 not building at all, so this rule holds
##                                 whatever the caller remembers about an
##                                 earlier build on the same row.
##   a counter below the required clicks -> `click`
##   a counter that reached the requirement -> `finish`
##   a construction this client already completed -> `complete` (nothing to
##                                 do)
##
## **Why the fourth rule needs one client-side fact.** The counter is *absent*
## both before the first click and after a completion: the purchase half
## seeds it (`engine.map_add_item` writes `attr["nc"] = 0` for a player row
## whose item has `clicks_to_build > 0`) and the completing command DELETES it,
## so `{cp: 5, nc: 1}` -> `finish` -> `{cp: 5}` is byte-identical to the state
## right after a `start` on a row the corpus placed before the seed existed
## (every fresh-save row carries `attr {}`). No server state distinguishes
## them, and no legacy branch ever would: **there is no server-side completion
## rule** (no branch compares `nc` with `clicks_to_build`), so deciding that a
## build is finished is the client's own act — which is exactly where the
## record belongs. The caller therefore passes `completed` (its own ledger of
## the completions it performed in this session), and this module stays pure. A
## client that has not walked the row re-offers the click, which is the same
## ambiguity the legacy client had; it is recorded, not hidden.
##
## The remaining countdown is likewise a pure client derivation —
## `cp - (now - started_at)`, clamped at zero — over data the server only
## stored and never interpreted.
##
## Ownership, price, and a level gate are deliberately absent: legacy performs
## none of them for these three commands, and the derived resource vector is
## NEUTRAL, so **no building cost is claimed** (design D4). No cancel action
## exists on purpose (design D6): the one legacy command that clears the
## attribute bag would destroy the click counter and any friend-assist
## entries, so this module offers no step that could reach it.

const TownState = preload("res://scripts/town/town_state.gd")

## The offered steps, in the endpoint's own closed action vocabulary (the
## service chooses the legacy command; the client names an outcome).
const STEP_START := "start"
const STEP_CLICK := "click"
const STEP_FINISH := "finish"
const STEP_COMPLETE := "complete"

## Refusal reasons, in evaluation order. `no_selection` is the structural one
## (no state, no selected placement) and names itself instead of evaluating.
const REASON_NO_SELECTION := "no_selection"
const REASON_UNREADABLE_STATE := "unreadable_state"
const REASON_UNADDRESSABLE := "unaddressable"
const REASON_NO_BUILD_TIME := "no_build_time"
const REASON_NO_STEP := "no_step"
const REASON_NO_REQUIREMENT := "no_requirement"


## The construction state a row carries, read through the ONE shared rule set
## (`TownState.construction_of`, which is the same function the placement
## parser itself used). `{clicks, countdown, started_at}`, each null when the
## row records none.
static func state_of(placement: Variant) -> Dictionary:
	var construction: Dictionary = TownState.construction_of(placement)
	return {
		"ok": bool(construction.get("ok", false)),
		"error": str(construction.get("error", "")),
		"clicks": construction.get("clicks", null),
		"countdown": construction.get("countdown", null),
		"started_at": construction.get("started_at", null),
	}


## True when the row records any construction state at all — a counter, a
## countdown, or both. A row with an empty attribute bag records none, which
## is why the whole fresh-player corpus offers a start.
static func has_state(construction: Dictionary) -> bool:
	return construction.get("clicks", null) != null \
		or construction.get("countdown", null) != null


## The click progress of a row against the item's committed click requirement:
## `{clicks, required, remaining, reached}`. An ABSENT counter reads as `0`
## clicks — a row that was never seeded has simply had no build click yet,
## which is the same state a freshly started build is in. Never negative, and
## a requirement of `0` is a building that needs no clicks at all.
static func click_progress(construction: Dictionary,
		clicks_required: int) -> Dictionary:
	var clicks: int = 0
	if construction.get("clicks", null) != null:
		clicks = int(construction["clicks"])
	var required: int = maxi(clicks_required, 0)
	var remaining: int = maxi(required - clicks, 0)
	return {"clicks": clicks, "required": required, "remaining": remaining,
		"reached": clicks >= required}


## The remaining countdown in whole seconds, or null when the row records no
## countdown (or a countdown with no usable start instant — a zero timestamp
## means nothing stamped the row, so no remaining time can be derived from it).
## `cp - (now - started_at)`, clamped at zero: a run past its deadline shows
## zero rather than a negative duration.
static func remaining_seconds(construction: Dictionary, now: int) -> Variant:
	var countdown: Variant = construction.get("countdown", null)
	if countdown == null:
		return null
	var started: Variant = construction.get("started_at", null)
	if started == null:
		return null
	return maxi(int(countdown) - (now - int(started)), 0)


## The single step a row's state offers next, or `STEP_COMPLETE` when there is
## nothing to do. `completed` is the caller's own record that THIS client
## already completed the build at this row (see the module header for why that
## fact cannot come from the row). It is consulted ONLY while the row carries
## construction state: a row that records nothing is not building at all, so a
## start is offered whatever the caller remembers about an earlier build on it.
## Pure: same inputs, same step, every time.
static func next_step(construction: Dictionary, clicks_required: int,
		completed: bool = false) -> String:
	if not has_state(construction):
		return STEP_START
	if completed:
		return STEP_COMPLETE
	var progress := click_progress(construction, clicks_required)
	if int(progress["remaining"]) > 0:
		return STEP_CLICK
	return STEP_FINISH


## Evaluates a selected placement against the committed content facts the
## client derives for it (the click requirement and the build time), and
## returns `{ok, error, step, reason, item, slot, clicks, required, remaining,
## countdown, started_at, remaining_seconds, label}`. `now` is the instant the
## remaining time is evaluated at and is always supplied by the caller — this
## module reads no clock. Structural failures (no state, no selected
## placement) and the three documented refusals return `{ok: false}` with a
## named `reason` and no step; a successful evaluation returns the offered
## step, which may legitimately be `STEP_COMPLETE` (nothing to do).
##
## The refusals, in evaluation order:
##   unaddressable     the placement's legacy map key is not a positive
##                     integer, so no construction intent can name it (the
##                     delivered flows' own reason; the index is never
##                     coerced, because a coerced index would address a
##                     different row);
##   unreadable_state  the row's attribute bag is not an object, so no
##                     construction fact can be read from it at all — the
##                     shared parser keeps such a row verbatim and the flow
##                     refuses it by name rather than reading a counter out of
##                     a value that is not a bag;
##   no_requirement    the item resolves no click requirement in the content
##                     package, so the step machine has no threshold to
##                     evaluate — fail-closed, never a guessed requirement;
##   no_build_time     the item records no resolvable POSITIVE committed build
##                     time, so a `start` has no derivable countdown; the
##                     service refuses the same row with `no_build_time`, and
##                     the client never sends a request it knows will fail;
##   no_step           the row offers nothing to do (a build this client
##                     already completed), so a confirm is refused by name
##                     with no request. This is the RECORDED limit of the
##                     client-side completion record: once this client has
##                     completed a build on a row, that row offers nothing
##                     further in the session, because the row and the legacy
##                     server never distinguished a completed build from a
##                     freshly started one.
static func evaluate(state: Variant, placement: Variant, clicks_required: int,
		build_time: int, completed: bool = false, now: int = 0) -> Dictionary:
	if state == null:
		return _reject("the town state is unavailable", REASON_NO_SELECTION)
	if placement == null or not (placement is TownState.Placement):
		return _reject("no building is selected", REASON_NO_SELECTION)
	var typed: TownState.Placement = placement
	var construction := state_of(typed)
	if not bool(construction["ok"]):
		return _reject(str(construction["error"]), REASON_UNREADABLE_STATE)
	var evaluation := {
		"ok": true,
		"error": "",
		"reason": "",
		"item": int(typed.item),
		"slot": int(typed.slot),
		"clicks": 0,
		"required": maxi(clicks_required, 0),
		"remaining": 0,
		"countdown": construction["countdown"],
		"started_at": construction["started_at"],
		"remaining_seconds": null,
		"has_state": has_state(construction),
		"label": "the selected building",
		"step": STEP_COMPLETE,
	}
	if not TownState.is_addressable(typed):
		return _refuse(evaluation, REASON_UNADDRESSABLE)
	if clicks_required < 0:
		return _refuse(evaluation, REASON_NO_REQUIREMENT)
	var progress := click_progress(construction, clicks_required)
	evaluation["clicks"] = int(progress["clicks"])
	evaluation["required"] = int(progress["required"])
	evaluation["remaining"] = int(progress["remaining"])
	var step := next_step(construction, clicks_required, completed)
	if step == STEP_COMPLETE:
		evaluation["reason"] = REASON_NO_STEP
		evaluation["step"] = STEP_COMPLETE
	elif step == STEP_START and build_time <= 0:
		# A start is the only step that needs a duration, and the duration is
		# the service's derivation from committed content — so a row whose
		# item has none is refused here rather than sent and refused.
		return _refuse(evaluation, REASON_NO_BUILD_TIME)
	else:
		evaluation["step"] = step
	evaluation["remaining_seconds"] = remaining_seconds(construction, now)
	return evaluation


## True when the evaluation offers a step this client may confirm (a refusal
## and the terminal `complete` state both offer nothing).
static func offers_step(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false)) \
		and str(evaluation.get("reason", "")) == "" \
		and str(evaluation.get("step", "")) != STEP_COMPLETE


## The explicit refusal text for an evaluation that offers no step: the reason
## plus what the player needs to know about this row, so no rejection is
## ever a bare word. Returns "" while a step is offered.
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if offers_step(evaluation):
		return ""
	var item := int(evaluation.get("item", 0))
	match str(evaluation.get("reason", "")):
		REASON_UNADDRESSABLE:
			return "not buildable: item %d has no addressable save key" % item
		REASON_UNREADABLE_STATE:
			return "not buildable: item %d carries no readable attribute bag" \
				% item
		REASON_NO_REQUIREMENT:
			return "not buildable: item %d resolves no click requirement" % item
		REASON_NO_BUILD_TIME:
			return ("not buildable: item %d has no resolvable committed build "
				% item + "time, so no countdown can be derived")
		REASON_NO_STEP:
			return "item %d: nothing to do, its build is already complete" % item
	return "not buildable"


## The construction readout for a row that records construction state: the
## building, its click progress against the committed requirement, and — while
## a countdown is recorded — the remaining seconds derived from that countdown
## and the row's own start instant. Returns "" for a row with NO construction
## state (there is nothing to read out) and names each missing half of the
## state rather than substituting a value: a countdown with no usable start
## instant, or no countdown at all, each say so.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if not bool(evaluation.get("has_state", false)):
		return ""
	var parts: Array = ["build: item %d" % int(evaluation.get("item", 0))]
	parts.append("clicks %d/%d" % [int(evaluation.get("clicks", 0)),
		int(evaluation.get("required", 0))])
	var remaining: Variant = evaluation.get("remaining_seconds", null)
	if evaluation.get("countdown", null) == null:
		parts.append("no countdown recorded")
	elif remaining == null:
		parts.append("countdown recorded with no start time")
	else:
		parts.append("%d s remaining" % int(remaining))
	if str(evaluation.get("step", "")) == STEP_COMPLETE:
		parts.append("complete")
	return " | ".join(parts)


## The step's own button label, so the confirm names the exact action it will
## send rather than a generic "Confirm".
static func step_label(step: String) -> String:
	match step:
		STEP_START:
			return "Start build"
		STEP_CLICK:
			return "Add build click"
		STEP_FINISH:
			return "Finish build"
	return ""


## The house rejection envelope: names the condition, never evaluates.
static func _reject(message: String, reason: String) -> Dictionary:
	return {"ok": false, "error": "[construction] rejected: " + message,
		"reason": reason, "step": STEP_COMPLETE, "item": 0, "slot": -1,
		"clicks": 0, "required": 0, "remaining": 0, "countdown": null,
		"started_at": null, "remaining_seconds": null, "has_state": false,
		"label": "the selected building"}


## A refusal carrying the evaluation's own context (which the caller already
## computed), so the explicit error and the readout can both name the row.
static func _refuse(evaluation: Dictionary, reason: String) -> Dictionary:
	evaluation["ok"] = false
	evaluation["reason"] = reason
	evaluation["step"] = STEP_COMPLETE
	evaluation["error"] = "[construction] refused: " + reason
	return evaluation
