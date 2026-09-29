extends RefCounted
## Pure evaluation helpers for the collection flow (building-collect, spec
## "Collection flow"): the committed collection ladder, the rung a row's
## recorded collection instant has reached, what that rung would pay, the
## countdown to the next rung, the refusal reasons, and the readout text. No
## nodes, no I/O, no requests, and **no clock of its own** — the reference
## instant is always a parameter — so the town view and its suite consume the
## same functions, exactly as `construction_flow.gd` and `move_flow.gd` serve
## the delivered flows (design D9).
##
## ## The ladder, and the one unit constant
##
## The committed configuration's `globals` record the collection ladder as
## `COLLECT_MINUTES = [5, 60, 240, 480]` paired with
## `COLLECT_MULTIPLIER = [0.25, 1, 2, 3]`. **The thresholds are MINUTES**
## while a row's recorded instant (`item[3]`) and every reference instant this
## flow is given are Unix **SECONDS**, so the comparison converts through the
## single named constant `SECONDS_PER_COMMITTED_MINUTE` and nowhere else.
## Comparing the two units directly would make the five-minute rung read as
## five *seconds* and pay the TOP rung within the first seconds of a build —
## the bug the Compatibility API side found in its own first implementation and
## corrected, recorded in the design's D1. Every rung boundary is therefore
## exercised from both sides by the suite (299/300, 3599/3600, 14399/14400,
## 28799/28800 seconds).
##
## ## What is established and what is derived
##
## **Established** by committed legacy source and executed-legacy evidence:
## the `collect` branch takes one positional argument, writes ONLY
## `item[3] = time_now()`, and the income travels entirely in the
## client-sent eight-slot vector applied verbatim per resource as
## `max(current + delta, 0)` before the branch runs. The per-item income
## content (`collect`, `collect_type`, `collect_xp`, `max_collects`) and the
## ladder globals are committed too, and an executed probe shows a collection
## on a just-started construction overwriting the build's start instant while
## the recorded countdown survives while the legacy server answers success.
##
## **Derived-provisional** (design D1-D6, never observed from the Flash
## client, because no legacy branch reads any of it):
##   * D1 the amount formula — `collect` scaled by the reached rung's
##     multiplier, clamped at the top rung and never extrapolated;
##   * D2 the experience scaling — `collect_xp` by the SAME rung (a flat
##     `collect_xp` is the recorded rejected alternative);
##   * D3 the sub-first-rung behaviour — below 300 s NO collection is offered
##     and none is executed, so the `0.25` multiplier never derives a
##     speculative amount;
##   * D4 the cap semantics — only a committed `max_collects` of `0` is
##     implemented; a non-zero cap is REFUSED, never interpreted;
##   * D5 the shared-field rule — a row carrying construction state (`cp` or
##     `nc`) is refused, in the client and again in the service, because the
##     executed probe shows the overlap is corruption rather than ambiguity;
##   * D6 the resource mapping — `g`/`w`/`o`/`s`/`c` onto gold/wood/oil/steel/
##     cash, with the unread `unknown` slot 0 and the never-produced `mana`
##     slot 7 always zero.
##
## The claim this module supports is therefore "a payout that grows in four
## committed rungs, derived from an item's committed income fields" — never
## any specific amount the legacy client pays.
##
## Ownership, price, a cap, a level gate, friend assistance, and speedups are
## deliberately absent: legacy performs none of them for this command, and
## inventing a gate would be a fabricated rule. Nothing here is applied to
## any state: the ladder decides only what the client would ASK about and what
## it would DISPLAY, while the service owns execution and the response owns
## the balances.

const TownState = preload("res://scripts/town/town_state.gd")
const ConstructionFlow = preload("res://scripts/town/construction_flow.gd")

## The committed collection ladder, exactly as the loaded configuration's
## `globals` record it (`COLLECT_MINUTES` and `COLLECT_MULTIPLIER`). The town
## view cross-checks the content package's own globals against this pair before
## offering a collection, so a content change that lengthens or reshapes the
## ladder fails closed instead of being paid under a stale local copy.
const COMMITTED_LADDER := {
	"minutes": [5, 60, 240, 480],
	"multipliers": [0.25, 1.0, 2.0, 3.0],
}
## The committed ladder's unit. The ONE place the minutes are converted to the
## seconds the elapsed time is measured in.
const SECONDS_PER_COMMITTED_MINUTE := 60
## The fixed width of the derived vector: the legacy eight-slot
## `resources_changed` `[unknown, xp, gold, wood, oil, steel, cash, mana]`.
const VECTOR_SLOTS := 8
## The experience slot of that vector (slot 1) and the committed
## `collect_type` vocabulary -> its slot (design D6).
const EXPERIENCE_SLOT := 1
const RESOURCE_SLOTS := {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6}
## The committed `collect_type` vocabulary, named in a fixed order so the
## refusal text is deterministic (`RESOURCE_SLOTS` is a Dictionary, whose key
## order is not a contract).
const COMMITTED_RESOURCE_TYPES := ["c", "g", "o", "s", "w"]
## The stored resource name each payable slot pays, in slot order from 2.
const RESOURCE_NAMES := ["gold", "wood", "oil", "steel", "cash"]
## The two slots this derivation can never fill (design D6): slot 0 is unread
## by every legacy branch and slot 7 is never produced because no committed
## item records a mana collect type.
const ALWAYS_ZERO_SLOTS := [0, 7]
## The sentinel a rung lookup that reaches no committed rung returns. Never
## `0`: rung 0 is a real rung, and confusing "none" with it would pay the
## quarter multiplier for a row that has earned nothing.
const NO_TIER := -1
## The top rung, which the elapsed time is CLAMPED at (design D1: never
## extrapolated past the last committed threshold).
const TOP_TIER := 3

## Refusal reasons, in evaluation order. `no_selection` is the structural one
## (no state, no selected placement) and names itself instead of evaluating.
const REASON_NO_SELECTION := "no_selection"
const REASON_UNREADABLE_STATE := "unreadable_state"
const REASON_UNADDRESSABLE := "unaddressable"
const REASON_NO_INCOME := "no_income"
const REASON_CAPPED := "capped"
const REASON_UNKNOWN_TYPE := "unknown_type"
const REASON_CONSTRUCTION_IN_PROGRESS := "construction_in_progress"
const REASON_TOO_EARLY := "too_early"


## The committed ladder's thresholds in MINUTES, as a copy the caller may
## mutate without touching the committed constant.
static func ladder_minutes() -> Array:
	return (COMMITTED_LADDER["minutes"] as Array).duplicate()


## The committed ladder's multipliers, as a copy the caller may mutate without
## touching the committed constant.
static func ladder_multipliers() -> Array:
	return (COMMITTED_LADDER["multipliers"] as Array).duplicate()


## The committed ladder's rung count (four today).
static func ladder_size() -> int:
	return (COMMITTED_LADDER["minutes"] as Array).size()


## One rung's committed threshold in SECONDS, through the single named unit
## constant (design D1/D3). A tier outside the committed ladder is refused
## (`0`) rather than extrapolated, so no out-of-range multiplier can ever
## reach a payout.
static func threshold_seconds(tier: int) -> int:
	if tier < 0 or tier >= ladder_size():
		return 0
	return int(ladder_minutes()[tier]) * SECONDS_PER_COMMITTED_MINUTE


## One rung's committed threshold in MINUTES, verbatim (0 outside the
## committed ladder) — recorded next to the seconds everywhere this flow's
## numbers are shown, so a reader can see the unit that was converted.
static func threshold_minutes(tier: int) -> int:
	if tier < 0 or tier >= ladder_size():
		return 0
	return int(ladder_minutes()[tier])


## The highest committed rung the elapsed seconds have reached, CLAMPED at the
## top rung (design D1), or `NO_TIER` (-1) when no rung is reached (design
## D3). Pure: the same elapsed time always reaches the same rung, whatever the
## instant it was measured from.
static func reached_tier(elapsed_seconds: int) -> int:
	if elapsed_seconds < 0:
		# A recorded instant ahead of the reference is a state this contract
		# reports, never one it pays for; the caller refuses it as `too_early`
		# and says so in words.
		return NO_TIER
	var reached := NO_TIER
	for index in range(ladder_size()):
		if elapsed_seconds >= threshold_seconds(index):
			reached = index
	return reached


## The whole committed ladder as the readout's own record: one row per rung
## with its committed threshold in BOTH units, its committed multiplier, and
## the Tree-shaped example of what it would pay. Reported verbatim, never
## derived from the wall clock, so it is byte-identical across reruns.
static func ladder_record() -> Array:
	var rows: Array = []
	for index in range(ladder_size()):
		rows.append({
			"tier": index,
			"minutes": threshold_minutes(index),
			"seconds": threshold_seconds(index),
			"multiplier": float(ladder_multipliers()[index]),
		})
	return rows


## The seconds still to wait for the NEXT rung after the reached one, clamped
## at zero, or `null` when the row has reached the top rung (there is no
## further rung — the payout is clamped there and never extrapolated). A row
## that has reached NO rung at all (`tier == NO_TIER`) waits for the FIRST one.
static func next_rung_remaining_seconds(tier: int, elapsed_seconds: int) -> Variant:
	var next := 0 if tier < 0 else tier + 1
	if next >= ladder_size():
		return null
	return maxi(threshold_seconds(next) - elapsed_seconds, 0)


## The committed-income facts the client derives for one item, as the pure
## helpers read them: `{ok, error, amount, resource_type, experience, cap}`.
## The caller supplies them from the typed content package (the very fields the
## service derives server-side, so the readout and the confirm use the same
## committed content the service does — design D9).
static func income_of(amount: int, resource_type: String, experience: int,
		cap: int) -> Dictionary:
	if amount < 0:
		return _income_reject("the committed collection amount is negative")
	if cap != 0:
		# Design D4: refused, never interpreted. Nothing in the repository says
		# whether a non-zero cap limits one collection, a daily total, or a
		# building's lifetime output, and the three readings imply different
		# payouts.
		return _income_reject("the item records a committed collection cap of %d, "
			% cap
			+ "whose semantics are unobserved, so no payout is derived")
	if not RESOURCE_SLOTS.has(resource_type):
		# Design D6: a type outside the committed five is refused rather than
		# coerced, so a content change can never pay the wrong resource.
		return _income_reject("collect_type '%s' is outside the committed set %s"
			% [resource_type, str(COMMITTED_RESOURCE_TYPES)])
	if experience < 0:
		return _income_reject("the committed collection experience is negative")
	return {"ok": true, "error": "", "amount": amount,
		"resource_type": resource_type, "experience": experience, "cap": cap}


## The derived eight-slot payout vector for one collection (design D1/D2/D6),
## or `null` when the committed ladder or the resource type does not resolve.
## The amount lands in the slot its committed resource type names and the
## experience in the experience slot, each scaled by the reached rung's
## committed multiplier and rounded half-up so a fractional product can never
## put a float on the legacy vector; the unread slot 0 and the never-produced
## mana slot stay zero. A fresh vector on every call, so a caller can never
## mutate the derivation for the next one.
static func payout_for(income: Dictionary, tier: int) -> Variant:
	if tier < 0 or tier >= ladder_size():
		return null
	var resource_type := str(income.get("resource_type", ""))
	var slot: Variant = RESOURCE_SLOTS.get(resource_type)
	if slot == null:
		return null
	var multiplier := float(ladder_multipliers()[tier])
	# The vector starts at ALL ZEROS, not at nulls: a slot this derivation
	# does not fill is a zero on the legacy vector, never a hole.
	var vector: Array = []
	vector.resize(VECTOR_SLOTS)
	for index in range(VECTOR_SLOTS):
		vector[index] = 0
	vector[int(slot)] = scale_amount(int(income.get("amount", 0)), multiplier)
	vector[EXPERIENCE_SLOT] = scale_amount(int(income.get("experience", 0)),
		multiplier)
	for index: int in ALWAYS_ZERO_SLOTS:
		vector[index] = 0
	return vector


## A rung-scaled amount, rounded to a whole resource (half-up). The committed
## multipliers are `0.25`, `1`, `2`, and `3`, so every committed product of a
## committed amount is already an integer (`20 x 0.25 = 5`); the rounding
## exists so a future fractional multiplier can never put a float on the
## legacy vector — the Tree's `collect_xp` of 1 at the quarter rung pays `0`.
static func scale_amount(value: int, multiplier: float) -> int:
	var scaled := float(value) * multiplier
	if scaled <= 0.0:
		return 0
	if scaled == floor(scaled):
		return int(scaled)
	return int(scaled + 0.5)


## The stored resource a vector's payable slot pays, or "" when the vector
## carries nothing in any payable slot (a refused or empty derivation).
static func vector_resource_name(vector: Variant) -> String:
	if not (vector is Array):
		return ""
	var typed: Array = vector
	for index in range(2, RESOURCE_NAMES.size() + 2):
		if index < typed.size() and int(typed[index]) != 0:
			return str(RESOURCE_NAMES[index - 2])
	return ""


## A derived vector as the confirm names it: the paid amount and resource plus
## the experience, e.g. `"60 wood, 3 xp"`. The experience is always named, even
## when it rounds to zero, because the vector always carries that slot and a
## silent zero would read as "forgot to derive it". Every part of the text is
## **derived**, and the confirm says so where it is shown.
static func payout_text(vector: Variant) -> String:
	if not (vector is Array):
		return ""
	var typed: Array = vector
	var parts: Array = []
	for index in range(2, RESOURCE_NAMES.size() + 2):
		if index < typed.size() and int(typed[index]) != 0:
			parts.append("%d %s" % [int(typed[index]),
				str(RESOURCE_NAMES[index - 2])])
	var experience: int = int(typed[EXPERIENCE_SLOT]) \
		if typed.size() > EXPERIENCE_SLOT else 0
	parts.append("%d xp" % experience)
	return ", ".join(parts)


## The collection state a row carries, read through the ONE shared construction
## accessor (`TownState.construction_of`, the same function the placement
## parser itself used) so the two facts about the shared `item[3]` field are
## read by one rule set. The refusal below is the CLIENT half of design D5's
## two-layer rule; the service refuses the same row independently.
static func construction_of(placement: Variant) -> Dictionary:
	return ConstructionFlow.state_of(placement)


## Evaluates a selected placement against the committed content facts the
## client derives for it, and returns
## `{ok, error, reason, item, slot, income, payout, tier, elapsed_seconds,
## collected_at, reference, next_remaining_seconds, has_income, label}`.
## `reference` is the instant the elapsed time is measured at and is ALWAYS
## supplied by the caller — this module reads no clock — so the rung, the
## countdown, and the whole readout are pure derivations.
##
## The refusals, in evaluation order:
##   unreadable_state          the row's attribute bag is not an object, so
##                             neither its construction state nor its
##                             collection clock can be read from it — the flow
##                             refuses by name rather than reading a counter
##                             out of a value that is not a bag;
##   unaddressable             the placement's legacy map key is not a positive
##                             integer, so no collection intent can name it (the
##                             delivered flows' own reason; the index is never
##                             coerced, because a coerced index would address a
##                             different row);
##   no_income                 the item records no committed collection amount
##                             in the content package, or the one it records is
##                             zero — the service answers `no_income` for the
##                             same row, and the client never sends a request it
##                             knows will fail;
##   capped                    the item records a NON-ZERO committed cap, whose
##                             semantics are unobserved, so the row is refused
##                             (design D4) rather than paid under a guess;
##   unknown_type              the item records a resource type outside the
##                             committed five, which the service refuses with
##                             `unknown_collect_type` (design D6);
##   construction_in_progress  the row records a countdown or a build-click
##                             counter, so `item[3]` is a build's start instant
##                             and a collection would overwrite it while the
##                             countdown survived (design D5, the executed
##                             probe's finding);
##   too_early                 the row's recorded collection instant is behind
##                             the reference by less than the first committed
##                             rung, so no amount is derived and nothing is
##                             offered (design D3).
##
## A REFUSAL returns `{ok: true, reason: <one of the above>}` — the
## evaluation itself succeeded and what it found is a verdict, exactly as
## `construction_flow.gd` reports its refusals. Only a structural rejection
## (no state, no selected placement) returns `{ok: false}`, and that one is an
## error rather than a verdict. `offers_collect()` is the single predicate a
## caller uses to ask "may I confirm this?", and it is false for every refusal.
static func evaluate(state: Variant, placement: Variant, income: Variant,
		reference: int) -> Dictionary:
	if state == null:
		return _reject("the town state is unavailable", REASON_NO_SELECTION)
	if placement == null or not (placement is TownState.Placement):
		return _reject("no building is selected", REASON_NO_SELECTION)
	var typed: TownState.Placement = placement
	var construction := construction_of(typed)
	if not bool(construction.get("ok", false)):
		return _reject(str(construction.get("error", "")),
			REASON_UNREADABLE_STATE)
	var clock: Dictionary = TownState.collection_of(typed)
	if not bool(clock.get("ok", false)):
		return _reject(str(clock.get("error", "")), REASON_UNREADABLE_STATE)
	var collected: int = int(clock.get("collected_at", 0))
	var evaluation := {
		"ok": true,
		"error": "",
		"reason": "",
		"item": int(typed.item),
		"slot": int(typed.slot),
		"label": "the selected building",
		"income": income if income is Dictionary else {},
		"payout": [],
		"tier": NO_TIER,
		"elapsed_seconds": 0,
		"collected_at": collected,
		"reference": reference,
		"next_remaining_seconds": null,
		"has_income": false,
	}
	if not TownState.is_addressable(typed):
		return _refuse(evaluation, REASON_UNADDRESSABLE)
	if not (income is Dictionary) or not bool((income as Dictionary).get(
			"ok", false)):
		# The committed income facts are absent or unusable: the service
		# refuses the same row with `no_income`, so the client names the
		# condition and sends nothing (design D9).
		var reason := REASON_NO_INCOME
		var message := str((income as Dictionary).get("error", ""))
		if (income as Dictionary).get("capped", false):
			reason = REASON_CAPPED
		elif (income as Dictionary).get("unknown_type", false):
			reason = REASON_UNKNOWN_TYPE
		if message == "":
			message = "item %d records no committed collection income" \
				% int(typed.item)
		return _refuse(evaluation, reason, message)
	var facts: Dictionary = income as Dictionary
	evaluation["has_income"] = int(facts.get("amount", 0)) > 0
	if not bool(evaluation["has_income"]):
		return _refuse(evaluation, REASON_NO_INCOME)
	if ConstructionFlow.has_state(construction):
		return _refuse(evaluation, REASON_CONSTRUCTION_IN_PROGRESS)
	var elapsed: int = reference - collected
	evaluation["elapsed_seconds"] = elapsed
	var tier := reached_tier(elapsed)
	if tier == NO_TIER:
		# Design D3: no rung reached, so no amount is derived and no confirm is
		# offered. The countdown to the first rung is still reported, so the
		# player can see when it will be.
		evaluation["next_remaining_seconds"] = next_rung_remaining_seconds(
			NO_TIER, elapsed)
		return _refuse(evaluation, REASON_TOO_EARLY)
	evaluation["tier"] = tier
	evaluation["next_remaining_seconds"] = next_rung_remaining_seconds(tier,
		elapsed)
	var payout: Variant = payout_for(facts, tier)
	if payout == null:
		return _refuse(evaluation, REASON_UNKNOWN_TYPE,
			"the committed collection ladder does not resolve a payout")
	evaluation["payout"] = payout
	return evaluation


## True when the evaluation offers a collection this client may confirm. Every
## refusal and every structural rejection offers nothing.
static func offers_collect(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false)) \
		and str(evaluation.get("reason", "")) == "" \
		and (evaluation.get("payout", []) as Array).size() == VECTOR_SLOTS


## The explicit refusal text for an evaluation that offers no collection: the
## reason plus what the player needs to know about this row, so no rejection is
## ever a bare word. Returns "" while a collection is offered.
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if offers_collect(evaluation):
		return ""
	var item := int(evaluation.get("item", 0))
	match str(evaluation.get("reason", "")):
		REASON_UNADDRESSABLE:
			return "not collectable: item %d has no addressable save key" % item
		REASON_UNREADABLE_STATE:
			return ("not collectable: item %d carries no readable attribute bag "
				% item + "or collection clock")
		REASON_NO_INCOME:
			return ("not collectable: item %d records no committed collection "
				% item + "amount")
		REASON_CAPPED:
			return ("not collectable: item %d records a committed collection cap "
				% item + "whose semantics are unobserved")
		REASON_UNKNOWN_TYPE:
			return ("not collectable: item %d records a collection type outside "
				% item + "the committed set")
		REASON_CONSTRUCTION_IN_PROGRESS:
			return ("not collectable: item %d is under construction, and a "
				% item + "collection would overwrite its build's start instant")
		REASON_TOO_EARLY:
			return ("not collectable: item %d has reached no committed ladder "
				% item + "rung yet")
	return "not collectable"


## The collection readout for a row: what the next collection would yield and
## in which resource (both **derived**), the committed rung the row has
## reached, and how long until the next one. Renders for ANY selected
## placement that records a readable collection clock — armed or not — so a
## player sees an income building's state without arming anything, and sees it
## update from every authoritative response.
##
## Empty text means the row's item records no committed income, which is the
## whole fresh-player corpus apart from its decorations: the line then has
## nothing truthful to show and says nothing rather than implying an income
## that is not there.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if not bool(evaluation.get("has_income", false)):
		return ""
	var parts: Array = ["collect: item %d" % int(evaluation.get("item", 0))]
	var tier: int = int(evaluation.get("tier", NO_TIER))
	if tier == NO_TIER:
		parts.append("no committed rung reached")
		parts.append("derived payout: none (too early)")
	else:
		parts.append("derived payout: %s (rung %d, x%s)" % [
			payout_text(evaluation.get("payout", [])),
			tier,
			str(ladder_multipliers()[tier])])
		parts.append("rung %d: %d min / %d s" % [tier,
			threshold_minutes(tier), threshold_seconds(tier)])
	var remaining: Variant = evaluation.get("next_remaining_seconds", null)
	if remaining == null:
		parts.append("top rung reached, clamped")
	else:
		parts.append("next rung in %d s" % int(remaining))
	return " | ".join(parts)


## The action's own button label, so the confirm names the exact action it will
## send rather than a generic "Confirm".
static func collect_label() -> String:
	return "Collect"


## The house income rejection: names the condition instead of deriving from it.
static func _income_reject(message: String) -> Dictionary:
	var capped := message.find("collection cap") != -1
	var unknown := message.find("outside the committed set") != -1
	return {"ok": false, "error": "[collect] refused: " + message,
		"amount": 0, "resource_type": "", "experience": 0, "cap": -1,
		"capped": capped, "unknown_type": unknown}


## The house rejection envelope: names the condition, never evaluates.
static func _reject(message: String, reason: String) -> Dictionary:
	return {"ok": false, "error": "[collect] rejected: " + message,
		"reason": reason, "item": 0, "slot": -1, "label": "the selected building",
		"income": {}, "payout": [], "tier": NO_TIER, "elapsed_seconds": 0,
		"collected_at": 0, "reference": 0, "next_remaining_seconds": null,
		"has_income": false}


## A refusal carrying the evaluation's own context (which the caller already
## computed), so the explicit error, the refusal text, AND the readout can all
## name the row. A CONTENT or CLOCK refusal deliberately keeps `ok: true`: the
## evaluation itself succeeded (it read the row and the committed content and
## derived a verdict) — what it found is a refusal, carried in `reason` exactly
## as `construction_flow.gd` carries its own. Only a STRUCTURAL rejection (no
## state, no placement) sets `ok: false`, and that one produces no readout and
## no refusal text because it is an error, not a verdict. This is what lets a
## too-early row — the state a player actually watches — still render its
## countdown.
static func _refuse(evaluation: Dictionary, reason: String,
		message: String = "") -> Dictionary:
	evaluation["reason"] = reason
	evaluation["payout"] = []
	if message != "":
		evaluation["error"] = "[collect] refused: " + message
	else:
		evaluation["error"] = "[collect] refused: " + reason
	return evaluation
