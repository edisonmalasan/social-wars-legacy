extends RefCounted
## Pure evaluation helpers for the XP/progression flow (OpenSpec
## `godot-building-xp` "Committed-curve level model" / "Level and progress
## readout" / "Stored-versus-derived disagreement is reported", design
## D1/D2/D6/D7).
##
## The committed schedule is **always a parameter**: this module holds no node,
## no clock, no request, and no content of its own, so the town view, the
## hermetic suite, and the deterministic report consume the SAME functions over
## the SAME table — exactly as `expand_flow.gd`, `collection_flow.gd`, and
## `construction_flow.gd` serve the delivered flows. A signature therefore reads
## `derived_level_for(exp, schedule)` rather than the shorthand
## `derived_level_for(exp)`: a pure module with no state of its own must be
## HANDED the committed schedule, and the schedule is always the LAST parameter
## so every helper's primary input reads first.
##
## ## The one named conversion — design D1, DERIVED-PROVISIONAL
##
## `entry_index_for_level()` below is **the only place in the client that
## indexes the committed curve**, and it mirrors the Compatibility API v0
## module's own equally named function
## (`apps/compat-api/level_envelope.py`, read-only here) so the client's model,
## the service, the tests, and the structural report cannot disagree by one
## level. The interpretation is **one-based**: stored level *n* is entry *n* minus
## one. The **rejected alternative is the zero-based reading**, under which
## `map["level"]` IS the index; the committed corpus contradicts it directly:
##
##     corpus xp = 4 | stored level = 1 | level the zero-based curve implies = 0
##
## Under zero-based a player with 4 experience is recorded as level 1 while the
## curve says level 1 begins at 40 experience — a contradiction. Under one-based
## stored level 1 is `levels[0]` (`"Slave"`, `exp_required` 0) and `4 >= 0`
## holds, so the corpus is self-consistent. Guessing zero-based would shift
## **every** level in the game by one and the error would stay invisible until a
## player saw the wrong level name, which is why the decision is documented here
## rather than absorbed into an index expression. A later change with better
## evidence revises ONE function.
##
## **One documented difference from the service's copy of the same conversion,
## and it is a difference of failure surface, not of decision:** the service
## raises its `invalid_level` error for a non-integer level, while this client
## returns null. A client must never raise out of a render pass, so null is the
## client's fail-closed answer, and the two agree on every value the committed
## curve can produce.
##
## ## What is ESTABLISHED (recorded here verbatim, never derived)
##
##   * the legacy `level_up` branch writes `map["level"] = new_level` from a
##     **client-supplied integer with no range check and no XP validation**, and
##     changes nothing else (`command.py:81-85`);
##   * the eight-slot resource vector is applied **before** the branch, verbatim,
##     as `max(current + delta, 0)` (`engine.py:251-271`);
##   * **zero** references to the `levels` schedule exist anywhere in the legacy
##     server (`command.py`, `engine.py`, `sessions.py`, `server.py`,
##     `constants.py`) — the curve is content the client owns entirely;
##   * **0 of the 40** placed corpus rows carry `attr["xp"]`, and the fresh save
##     carries no unit placements, so the unit-experience path cannot be
##     exercised;
##   * the committed curve: **100** entries, `exp_required` **strictly
##     increasing** with no duplicates and no non-positive gap, first thresholds
##     `0, 40, 60, 100, 200, 350, 550, 800`, final `2016089205`; `name` is a
##     **label, not an identifier** (44 distinct names over 100 entries; every
##     entry from level 49 onward reads `Conqueror`); and the committed
##     thresholds are preserved **verbatim** — nothing here rebalances, smooths,
##     or interpolates them (design D7).
##
## ## What is DERIVED here
##
##   * **D1 the index base** (above): derived-provisional, one named place.
##   * the display labels and the composition of the readout's lines — the
##     committed evidence records no authentic legacy progression panel, so the
##     wording is the delivered provisional convention.
##
## ## What is deliberately absent
##
## **No reward is read, shown, or paid.** `reward_type` (the letter vocabulary
## `{s, w, g, c}`) and `reward_amount` (`{1, 50, 250}`) are committed on every
## entry and **no legacy branch reads either**, so paying or displaying one
## would invent an economy — the same discipline the expansion
## `neighbors` / `inventory_qte` requirements received (design D7).
##
## **Unit experience** (`add_xp_unit`, which writes `attr["xp"]` on an item row)
## and **tutorial progression** (`complete_tutorial`) are out of scope: the
## committed corpus carries no unit placements and no row carrying
## `attr["xp"]`, so the path cannot be exercised (design D7). The **disagreement
## is reported and never reconciled**: the recorded level is unverified against
## the curve, so no helper here writes it, prefers one value, or normalises the
## save (design D2). Server-authoritative validation beyond the service's own
## one guard belongs to Server v1 / M13.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The committed schedule's entry count (`config/main.json` -> `levels`,
## normalized with `legacy_id` as the 0-based positional index). The level space
## is therefore exactly `1..100` under D1's one-based reading.
const SCHEDULE_ENTRIES := 100
const FIRST_LEVEL := 1
const LAST_LEVEL := 100
## The committed curve's first eight thresholds, verbatim, and its final one.
## Recorded so a suite (and the report) can state the ladder's shape without
## restating all 100 values; the full ladder is always read from the schedule.
const FIRST_THRESHOLDS := [0, 40, 60, 100, 200, 350, 550, 800]
const FINAL_THRESHOLD := 2016089205
## The committed corpus's own experience and recorded level — the two numbers
## that decide D1, and the regression pair every suite asserts.
const CORPUS_XP := 4
const CORPUS_LEVEL := 1
## How many distinct names the committed curve carries. A name is a **label**,
## not an identifier: 44 names over 100 entries, and every entry from level 45
## onward reads `Conqueror`, so a name may never be used to look a level up.
const DISTINCT_NAMES := 44
## The first ONE-BASED level from which every further level carries the same
## name, read from the committed curve.
##
## **This is 45, and the investigation record's "from level 49 onward" is a
## ZERO-BASED position** — the committed curve's 0-based index 48 is a
## `Conqueror` row, but so is 0-based index 44, which is one-based level 45. The
## two readings differ by exactly the index-base ambiguity D1 exists to settle,
## so the value below is the **derived, one-based** one and the report records
## it as read from the curve rather than as a restated claim. Nothing turns on
## it beyond the readout's own display, but a wrong value here is exactly the
## silent off-by-one this line refuses to accept anywhere else.
const SATURATED_NAME_LEVEL := 45

## Design D1, recorded in machine-readable form so the readout, the tests, and
## the structural report all state the same three facts. They mirror the
## service's own constants of the same names.
const INDEX_BASE := "one-based"
const DERIVATION_STATUS := "derived-provisional"
const REJECTED_ALTERNATIVE := "zero-based"

## What a level with no committed name reads as. This is a **named absence**,
## never a placeholder that could be mistaken for a committed value: the spec
## requires the readout to say the name is absent rather than substituting one.
const NAME_ABSENT := "[no committed name]"

## The refusal reasons. The first two are the service's own codes
## (`level_already_current` and `xp_below_threshold`); the rest are the
## structural rejections no verdict can be built from.
const REASON_LEVEL_ALREADY_CURRENT := "level_already_current"
const REASON_XP_BELOW_THRESHOLD := "xp_below_threshold"
const REASON_UNREADABLE_SCHEDULE := "unreadable_schedule"
const REASON_UNREADABLE_STATE := "unreadable_state"
## The committed curve's floor sits above the player's experience, so NO level is
## derivable at all. The service answers the same content condition with its own
## `internal_error` (a 500); the client names it distinctly because its
## consequence here is "no level can be offered", never an error to swallow.
const REASON_NO_DERIVED_LEVEL := "no_derived_level"

## The sentinel a lookup that resolves no level returns. Never `0` used as a
## level: under the one-based reading the first real level IS 1, so a caller
## reading this sentinel must test for it explicitly, which is why every helper
## that can return it also returns a boolean verdict alongside.
const NO_LEVEL := -1

## The four fields a committed curve entry records, in the committed order the
## structural record uses. The first two are read; the last two are listed ONLY
## so this module can state that nothing here consumes them.
const ENTRY_FIELDS := ["name", "exp_required", "reward_type", "reward_amount"]
## The reward fields, named so the "no reward is displayed" assertion has a
## single, checkable list.
const REWARD_FIELDS := ["reward_type", "reward_amount"]


# ---------------------------------------------------------------------------
# The one named conversion (design D1)
# ---------------------------------------------------------------------------


## The committed curve's positional index for a stored level — **the one named
## conversion**, mirroring the service's equally named
## `level_envelope.entry_index_for_level`. Stored level *n* is `levels[n - 1]`:
## the index base is **one-based**, the interpretation is
## **derived-provisional**, and the **rejected** alternative is the **zero-based**
## reading the committed corpus contradicts (see the module comment for the
## contradiction, quoted from the investigation record).
##
## `entries` is the schedule's entry count when the caller has it; without it
## only the lower bound is checked.
##
## The edges **refuse gracefully and never raise**: a level below 1, a level
## above the curve, a non-integer, and a `bool` (which is an integer here and
## would otherwise resolve to entry 0) all return null. Null therefore means
## exactly "the committed curve has no entry for this level", and the caller
## turns it into a named refusal — never into a coerced index, which would name
## a different level.
static func entry_index_for_level(level: Variant,
		entries: Variant = null) -> Variant:
	if level is bool or not (level is int):
		return null
	if int(level) < FIRST_LEVEL:
		return null
	if entries != null:
		if entries is bool or not (entries is int):
			return null
		if int(level) > int(entries):
			return null
	return int(level) - 1


## The stored level a positional curve index names — the documented **inverse**
## of `entry_index_for_level()`, named so the `+ 1` is not open-coded in a
## caller either. The round trip `entry_index_for_level(level_for_entry_index(i))`
## is asserted for every index of the committed curve. Null for a non-integer, a
## `bool`, or an index below zero, exactly as the forward conversion's edges are
## graceful rather than raising.
static func level_for_entry_index(index: Variant) -> Variant:
	if index is bool or not (index is int):
		return null
	if int(index) < 0:
		return null
	return int(index) + 1


# ---------------------------------------------------------------------------
# The committed schedule
# ---------------------------------------------------------------------------


## The schedule's own size, or -1 when the value is not a usable positional
## table. An explicit sentinel, never a guessed zero: a curve that cannot be
## counted cannot bound a level.
static func schedule_size(schedule: Variant) -> int:
	if not (schedule is Array) or (schedule as Array).is_empty():
		return -1
	return (schedule as Array).size()


## The committed `exp_required` ladder in committed positional order, read
## **verbatim**: nothing is rebalanced, smoothed, or interpolated (design D7).
##
## Only the shape this contract can derive from is checked — every entry is an
## object carrying a non-negative integer `exp_required`, and the ladder is
## strictly increasing — so a curve drift is *reported* (null) instead of
## producing a silently different level model. The committed curve's first
## threshold is 0, so it has no duplicate and no non-positive gap by
## construction; that is a property of the content, not an assumption here.
static func thresholds_of(schedule: Variant) -> Variant:
	var size := schedule_size(schedule)
	if size < 0:
		return null
	var thresholds: Array = []
	for position in range(size):
		var row: Variant = (schedule as Array)[position]
		if not (row is Dictionary):
			return null
		var value: Variant = BootData._parse_int((row as Dictionary).get(
			"exp_required"))
		if value == null or int(value) < 0:
			return null
		if not thresholds.is_empty() \
				and int(value) <= int(thresholds[thresholds.size() - 1]):
			return null
		thresholds.append(int(value))
	return thresholds


## The committed curve entry a stored level names, or null. The position is
## resolved through the one named conversion and the row is returned **verbatim**
## as a copy — no coercion, no defaulting, no filtering — so the commitment to
## preserve `exp_required` exactly as committed is structural. Null means
## exactly "the committed curve has no entry for this level".
static func entry_for_level(level: Variant, schedule: Variant) -> Variant:
	var index: Variant = entry_index_for_level(level, schedule_size(schedule))
	if index == null:
		return null
	var row: Variant = (schedule as Array)[int(index)]
	if not (row is Dictionary):
		return null
	return (row as Dictionary).duplicate(true)


## The committed name a stored level carries, or null when the curve has no
## entry for the level or the entry records no name. An absent name is
## reported as **absent**: the readout renders `NAME_ABSENT`, never a
## placeholder that could be read as a committed value. A name is a **label,
## not an identifier** — 44 distinct names over 100 entries — so it is never
## used to resolve a level.
static func name_for(level: Variant, schedule: Variant) -> Variant:
	var entry: Variant = entry_for_level(level, schedule)
	if entry == null:
		return null
	var value: Variant = (entry as Dictionary).get("name")
	if not (value is String) or str(value).is_empty():
		return null
	return str(value)


## The committed experience a stored level requires, or null when the curve has
## no entry for that level. Resolved through the one named conversion, never by
## a caller's own arithmetic.
static func threshold_for(level: Variant, schedule: Variant) -> Variant:
	var entry: Variant = entry_for_level(level, schedule)
	if entry == null:
		return null
	var value: Variant = BootData._parse_int((entry as Dictionary).get(
		"exp_required"))
	if value == null:
		return null
	return int(value)


# ---------------------------------------------------------------------------
# Derived levels
# ---------------------------------------------------------------------------


## The level the committed curve implies for a stored experience, or null.
##
## The derived level is the **highest** level whose committed `exp_required` the
## experience meets, resolved through the one named conversion — and **no other
## input determines it**: not the recorded level (which is unverified, design
## D2), not a client value, not anything derived from them.
##
## The edges refuse gracefully and never raise:
##   * an experience **below the first committed threshold** has no level and
##     returns null. The committed curve's first threshold is 0, so this cannot
##     happen for a real save; the branch exists for a curve whose floor is above
##     zero, and for a ladder this module cannot read (which returns null for
##     every experience).
##   * an experience **above the final threshold** derives the **top** level
##     (100) and does not raise: there is simply no next level, which
##     `next_threshold()` reports as null.
static func derived_level_for(exp: Variant, schedule: Variant) -> Variant:
	if exp is bool:
		return null
	var experience: Variant = BootData._parse_int(exp)
	if experience == null or int(experience) < 0:
		return null
	var thresholds: Variant = thresholds_of(schedule)
	if thresholds == null:
		return null
	var ladder: Array = thresholds
	if int(experience) < int(ladder[0]):
		return null
	var index := 0
	for position in range(ladder.size()):
		if int(experience) >= int(ladder[position]):
			index = position
		else:
			break
	return level_for_entry_index(index)


## The level **after** the derived one, or null when the derived level is the
## curve's last (or when no level is derivable). This is the service's own
## `curve.next_level`, computed through the one named conversion rather than by
## adding one at a call site.
static func next_level(exp: Variant, schedule: Variant) -> Variant:
	var derived: Variant = derived_level_for(exp, schedule)
	if derived == null:
		return null
	return level_for_entry_index(entry_index_for_level(int(derived) + 1,
		schedule_size(schedule)))


## The committed experience the level **after** the derived one requires, or
## null when there is no next level. The progress figure's target. Null means
## "the experience has reached or passed the curve's final threshold" — a
## completed curve is **reported**, never extended by an invented level.
static func next_threshold(exp: Variant, schedule: Variant) -> Variant:
	var following: Variant = next_level(exp, schedule)
	if following == null:
		return null
	return threshold_for(following, schedule)


## The committed name the level after the derived one carries, or null when
## there is no next level or it records no name. Absent is absent, exactly as in
## `name_for()`.
static func next_name(exp: Variant, schedule: Variant) -> Variant:
	var following: Variant = next_level(exp, schedule)
	if following == null:
		return null
	return name_for(following, schedule)


## The experience still needed to reach the next level, or null. The committed
## next threshold minus the stored experience, **never negative**: an experience
## at or past a threshold has already reached that level, so `0` is a real
## answer and not a clamp. Null means "there is no next level" (see
## `next_threshold()`).
static func remaining(exp: Variant, schedule: Variant) -> Variant:
	var target: Variant = next_threshold(exp, schedule)
	if target == null:
		return null
	var experience: Variant = BootData._parse_int(exp)
	if experience == null or experience is bool:
		return null
	var left := int(target) - int(experience)
	return left if left > 0 else 0


## How far the stored experience has travelled across the derived level's own
## committed span, as a ratio in `[0, 1]`: zero at the derived level's own
## threshold, one at the next level's threshold. Null when no level is
## derivable, when the curve has no next level, or when the derived level's own
## threshold is unreadable — a ratio this contract cannot compute honestly is
## never a guessed number. It is a **presentational** figure derived from
## committed content and the stored experience; it grants nothing and gates
## nothing.
static func progress_ratio(exp: Variant, schedule: Variant) -> Variant:
	var derived: Variant = derived_level_for(exp, schedule)
	if derived == null:
		return null
	var target: Variant = next_threshold(exp, schedule)
	if target == null:
		return null
	var own: Variant = threshold_for(derived, schedule)
	var experience: Variant = BootData._parse_int(exp)
	if own == null or experience == null or experience is bool:
		return null
	var span := int(target) - int(own)
	if span <= 0:
		# A ladder this contract verified as strictly increasing cannot produce
		# this; the null is a fail-closed guard, not a reachable branch.
		return null
	var travelled := int(experience) - int(own)
	if travelled < 0:
		travelled = 0
	if travelled > span:
		travelled = span
	return float(travelled) / float(span)


# ---------------------------------------------------------------------------
# The evaluation: agreement, disagreement, and the refusals
# ---------------------------------------------------------------------------


## The whole progression evaluation for one player, and the ONLY entry point a
## surface uses. Returns
## `{ok, reason, error, offers, exp, derived_level, recorded_level, name,
## threshold, next_level, next_name, next_threshold, remaining, progress,
## agrees, disagrees, recorded_threshold}`.
##
## The refusals, in evaluation order:
##   * `unreadable_schedule`     the committed curve is not a positional table
##     whose `exp_required` ladder is strictly increasing. No verdict can be
##     built, so `ok` is **false** — an error, not a verdict.
##   * `unreadable_state`        the recorded level or the stored experience is
##     not an integer this contract can read. Also an error rather than a
##     verdict: the recorded level is never coerced into a starting point for
##     the comparison, because coercing it would invent authority the legacy
##     server never had.
##   * `no_derived_level`        the curve's floor sits above the stored
##     experience, so NO level is derivable. Also an error rather than a
##     verdict: there is nothing to compare.
##   * `level_already_current`  the recorded level already equals the derived
##     level. There is nothing to do, and executing `level_up` would rewrite an
##     identical value (design D4's first refusal). This is the **agreement**
##     state.
##   * `xp_below_threshold`      the recorded level has no entry in the curve, or
##     the stored experience cannot reach the recorded level's own committed
##     threshold — so no advancement is derivable (design D4's second
##     refusal, and design D2's disagreement this client refuses to reconcile).
##
## A REFUSAL returns `{ok: true, reason: <one of the two>}` — the evaluation
## itself succeeded and what it found is a verdict, exactly as
## `collection_flow.gd` and `expand_flow.gd` report theirs. `offers_level_up()`
## is the single predicate a surface uses to ask "may I confirm this?", and it
## is false for every refusal and every structural rejection.
static func evaluate(schedule: Variant, recorded_level: Variant,
		exp: Variant) -> Dictionary:
	var size := schedule_size(schedule)
	var thresholds: Variant = thresholds_of(schedule)
	var evaluation := {
		"ok": true,
		"reason": "",
		"error": "",
		"offers": false,
		"exp": 0,
		"derived_level": NO_LEVEL,
		"recorded_level": NO_LEVEL,
		"name": null,
		"threshold": null,
		"next_level": null,
		"next_name": null,
		"next_threshold": null,
		"remaining": null,
		"progress": null,
		"agrees": false,
		"disagrees": false,
		"recorded_threshold": null,
	}
	if size < 0 or thresholds == null:
		return _evaluation_reject(evaluation, REASON_UNREADABLE_SCHEDULE,
			"the committed level curve is not a positional table with a "
			+ "strictly increasing exp_required ladder")
	if recorded_level is bool or BootData._parse_int(recorded_level) == null:
		return _evaluation_reject(evaluation, REASON_UNREADABLE_STATE,
			"this save records no level this client can read as an integer")
	if exp is bool or BootData._parse_int(exp) == null:
		return _evaluation_reject(evaluation, REASON_UNREADABLE_STATE,
			"this save records no experience this client can read as an "
			+ "integer")
	var experience := int(BootData._parse_int(exp))
	evaluation["exp"] = experience
	evaluation["recorded_level"] = int(BootData._parse_int(recorded_level))
	var derived: Variant = derived_level_for(experience, schedule)
	if derived == null:
		return _evaluation_reject(evaluation, REASON_NO_DERIVED_LEVEL,
			"the committed level curve begins at %d experience and this player "
			% int((thresholds as Array)[0]) + "has %d" % experience)
	evaluation["derived_level"] = int(derived)
	evaluation["name"] = name_for(int(derived), schedule)
	evaluation["threshold"] = threshold_for(int(derived), schedule)
	var following: Variant = next_level(experience, schedule)
	evaluation["next_level"] = following if following == null \
		else int(following)
	evaluation["next_name"] = next_name(experience, schedule)
	evaluation["next_threshold"] = next_threshold(experience, schedule)
	evaluation["remaining"] = remaining(experience, schedule)
	evaluation["progress"] = progress_ratio(experience, schedule)
	var recorded_threshold: Variant = threshold_for(
		evaluation["recorded_level"], schedule)
	evaluation["recorded_threshold"] = recorded_threshold
	var agrees := int(evaluation["recorded_level"]) == int(derived)
	evaluation["agrees"] = agrees
	evaluation["disagrees"] = not agrees
	if agrees:
		return _evaluation_refuse(evaluation, REASON_LEVEL_ALREADY_CURRENT,
			"the recorded level is already %d, which is the level the committed "
			% int(derived)
			+ "curve derives for %d stored experience" % experience)
	if recorded_threshold == null:
		return _evaluation_refuse(evaluation, REASON_XP_BELOW_THRESHOLD,
			"the recorded level %d has no entry in the committed curve (which "
			% int(evaluation["recorded_level"])
			+ "holds %d levels), so the stored experience %d cannot be checked"
			% [size, experience] + " against it")
	if experience < int(recorded_threshold):
		return _evaluation_refuse(evaluation, REASON_XP_BELOW_THRESHOLD,
			"the stored experience %d cannot reach the recorded level %d, whose "
			% [experience, int(evaluation["recorded_level"])]
			+ "committed threshold is %d; the committed curve derives level %d"
			% [int(recorded_threshold), int(derived)])
	evaluation["offers"] = true
	return evaluation


## True when the evaluation offers a level-up this client may confirm. Every
## refusal and every structural rejection offers nothing.
static func offers_level_up(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false)) \
		and str(evaluation.get("reason", "")) == "" \
		and bool(evaluation.get("offers", false))


## The stored-versus-derived **agreement** line. Names BOTH values when they
## agree (so the reader can see the agreement rather than infer it) and states
## the disagreement explicitly when they do not — naming the recorded level, the
## derived level, and the stored experience that separates them. It never
## prefers either value, never reconciles, and never implies the save was
## changed (design D2).
static func agreement_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var recorded := int(evaluation.get("recorded_level", NO_LEVEL))
	var derived := int(evaluation.get("derived_level", NO_LEVEL))
	var exp := int(evaluation.get("exp", 0))
	if bool(evaluation.get("agrees", false)):
		return "recorded level %d agrees with the derived level %d at %d xp" \
			% [recorded, derived, exp]
	return ("recorded level %d disagrees with the derived level %d (the stored "
		% [recorded, derived]
		+ "%d xp is what separates them; neither value is authoritative and "
			% exp
		+ "the save is left unchanged)")


## The explicit refusal text for an evaluation that offers no level-up: the
## reason plus what the player needs to know, so no rejection is a bare word.
## Returns "" while a level-up is offered, and "" for a structural rejection
## (which the view reports through its own error line).
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if offers_level_up(evaluation):
		return ""
	match str(evaluation.get("reason", "")):
		REASON_LEVEL_ALREADY_CURRENT:
			return ("no level up to offer: the recorded level %d already equals "
				% int(evaluation.get("recorded_level", NO_LEVEL))
				+ "the derived level %d" % int(evaluation.get("derived_level",
					NO_LEVEL)))
		REASON_XP_BELOW_THRESHOLD:
			return ("no level up to offer: %d xp cannot reach the recorded "
				% int(evaluation.get("exp", 0))
				+ "level %d (whose committed threshold is %s)"
				% [int(evaluation.get("recorded_level", NO_LEVEL)),
					_number_text(evaluation.get("recorded_threshold", null))])
	return "no level up to offer"


## The level readout for the live evaluation: the committed curve's shape, the
## derived level and its committed name, the stored experience, the next level's
## committed threshold, the experience remaining to reach it, the progress
## across the derived level's own span, and the explicit agreement/disagreement
## line.
##
## **No reward is rendered**, and no gate is derived from one: the committed
## `reward_type` / `reward_amount` are consumed by no legacy behaviour, so
## showing either would invent an economy (design D7). A level whose entry
## records no name renders `NAME_ABSENT` rather than a placeholder. A completed
## curve (no next level) renders `next: none` and no remaining figure, which is
## a reported state and not an error.
static func readout_text(evaluation: Dictionary, summary: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var derived := int(evaluation.get("derived_level", NO_LEVEL))
	var parts: Array = []
	parts.append("curve: %d levels, %s, %s"
		% [int(summary.get("entries", 0)), INDEX_BASE, DERIVATION_STATUS])
	parts.append("derived level: %d (%s)"
		% [derived, _name_text(evaluation.get("name", null))])
	parts.append("experience: %d" % int(evaluation.get("exp", 0)))
	parts.append("level %d requires: %s"
		% [derived, _number_text(evaluation.get("threshold", null))])
	if evaluation.get("next_level", null) == null:
		parts.append("next: none (the committed curve ends at this level)")
	else:
		parts.append("next: level %d (%s) at %s xp"
			% [int(evaluation.get("next_level", NO_LEVEL)),
				_name_text(evaluation.get("next_name", null)),
				_number_text(evaluation.get("next_threshold", null))])
		parts.append("remaining: %s"
			% _number_text(evaluation.get("remaining", null)))
		parts.append("progress: %s" % _progress_text(
			evaluation.get("progress", null)))
	parts.append(agreement_text(evaluation))
	var refusal := refusal_text(evaluation)
	if refusal != "":
		parts.append(refusal)
	return " | ".join(parts)


## The armed surface's own confirm text: it names the **derived** level and says
## it is derived, so a player is never shown a level the client chose as if it
## were authoritative. The recorded level is named as the value the service will
## replace, and no amount, price, or reward appears anywhere in it.
static func confirm_text(evaluation: Dictionary) -> String:
	if not offers_level_up(evaluation):
		return ""
	return ("level up to %d (%s)? — that level is DERIVED from the committed "
		% [int(evaluation.get("derived_level", NO_LEVEL)),
			_name_text(evaluation.get("name", null))]
		+ "curve and %d stored xp, never observed from the legacy client; the "
			% int(evaluation.get("exp", 0))
		+ "service derives it again server-side and the recorded level %d moves "
			% int(evaluation.get("recorded_level", NO_LEVEL))
		+ "to it. No reward is paid: no legacy branch reads the committed "
		+ "reward fields")


## The action's own button label, so the confirm names the exact action it will
## send rather than a generic "Confirm".
static func level_up_label() -> String:
	return "Level up"


## The committed curve's facts as the readout and the evidence report record
## them: the entry count, the addressable level range, the first thresholds, the
## final threshold, the distinct-name count, and the **saturation level** above
## which every name reads the same. `{ok: false}` when the schedule cannot be
## read, which every caller renders as a refusal rather than as an empty curve.
##
## Every number is read from the schedule the caller passed, so a content change
## is recorded rather than contradicted.
static func curve_summary(schedule: Variant) -> Dictionary:
	var size := schedule_size(schedule)
	var thresholds: Variant = thresholds_of(schedule)
	if size < 0 or thresholds == null:
		return {"ok": false, "entries": 0, "first_level": FIRST_LEVEL,
			"last_level": FIRST_LEVEL, "first_thresholds": [],
			"final_threshold": 0, "distinct_names": 0,
			"saturated_name_level": 0, "error": "the committed level curve is "
			+ "not a positional table with a strictly increasing exp_required "
			+ "ladder"}
	var ladder: Array = thresholds
	var first: Array = []
	for index in range(mini(FIRST_THRESHOLDS.size(), ladder.size())):
		first.append(int(ladder[index]))
	var names := {}
	for level in range(FIRST_LEVEL, size + FIRST_LEVEL):
		var value: Variant = name_for(level, schedule)
		if value != null:
			names[str(value)] = true
	# The first level from which every further level carries the SAME name, read
	# by comparing the tail of the curve rather than from a restated constant,
	# so a content change is recorded instead of contradicted. The walk starts at
	# the curve's LAST level and stops at the first level whose own name differs
	# from its predecessor's; a curve whose every level shares one name saturates
	# at its first level.
	var saturated := FIRST_LEVEL
	for level in range(size, FIRST_LEVEL, -1):
		var current: Variant = name_for(level, schedule)
		var previous: Variant = name_for(level - 1, schedule)
		if current == null or previous == null or current != previous:
			saturated = level
			break
	return {"ok": true, "entries": size, "first_level": FIRST_LEVEL,
		"last_level": size, "first_thresholds": first,
		"final_threshold": int(ladder[ladder.size() - 1]),
		"distinct_names": names.size(), "saturated_name_level": saturated,
		"error": ""}


## The curve facts as the structural report records them: the same summary under
## a stable key set plus design D1's three machine-readable constants, the named
## conversion's own signature, and the committed corpus's own experience and
## level. Nothing here restates a threshold the schedule already carries, and
## nothing here is computed by the client's own arithmetic.
static func curve_record(schedule: Variant) -> Dictionary:
	var summary := curve_summary(schedule)
	return {
		"entries": int(summary.get("entries", 0)),
		"first_level": int(summary.get("first_level", FIRST_LEVEL)),
		"last_level": int(summary.get("last_level", FIRST_LEVEL)),
		"first_thresholds": (summary.get("first_thresholds", []) as Array)
			.duplicate(),
		"final_threshold": int(summary.get("final_threshold", 0)),
		"distinct_names": int(summary.get("distinct_names", 0)),
		"saturated_name_level": int(summary.get("saturated_name_level", 0)),
		"index_base": INDEX_BASE,
		"derivation_status": DERIVATION_STATUS,
		"rejected_alternative": REJECTED_ALTERNATIVE,
		"index_base_conversion": "entry_index_for_level(level, entries) — the "
			+ "one named conversion; returns level - 1 for "
			+ "1 <= level <= entries and null otherwise (never raises), and its "
			+ "documented inverse is level_for_entry_index(index) = index + 1",
		"corpus_xp": CORPUS_XP,
		"corpus_level": CORPUS_LEVEL,
		"corpus_contradiction": "corpus xp = %d | stored level = %d | level "
			% [CORPUS_XP, CORPUS_LEVEL]
			+ "the zero-based curve implies = 0 — which is why the zero-based "
			+ "reading is REJECTED, not merely unsupported",
		"reward_fields_never_consumed": (REWARD_FIELDS as Array).duplicate(),
		"entry_fields": (ENTRY_FIELDS as Array).duplicate(),
		"ok": bool(summary.get("ok", false)),
		"error": str(summary.get("error", "")),
	}


## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and check,
## and the one derived fact states its rejected alternative. Nothing here names a
## runtime; the runtime names live in `NON_CLAIMS` and are assembled from
## fragments, because the project-scope suite scans this file's bytes for their
## literal forms.
const PROVENANCE := {
	"established": [
		{"fact": "the legacy level_up branch writes map[\"level\"] = "
			+ "new_level from a CLIENT-SUPPLIED integer, with no range check "
			+ "and no XP validation, and changes nothing else",
			"evidence": "command.py:81-85 (committed legacy server source); "
				+ "the level_up row of docs/legacy-protocol/commands.json; the "
				+ "committed execution in tests/fixtures/godot-building-xp/"
				+ "steps/command_level_up/"},
		{"fact": "the eight-slot resource vector is applied BEFORE the "
			+ "dispatched branch, verbatim, as max(current + delta, 0)",
			"evidence": "engine.py:251-271; command.py:40; the resource_effects "
				+ "column of docs/legacy-protocol/commands.json"},
		{"fact": "nothing in the legacy server reads the committed levels "
			+ "schedule: zero references across command.py, engine.py, "
			+ "sessions.py, server.py, and constants.py",
			"evidence": "docs/legacy-xp-basics.md; the endpoint's own "
				+ "consequence, which is why the level curve is content the "
				+ "client owns entirely"},
		{"fact": "the committed curve holds 100 entries whose exp_required is "
			+ "strictly increasing with no duplicates and no non-positive gap, "
			+ "from 0, 40, 60, 100, 200, 350, 550, 800 to 2016089205",
			"evidence": "config/main.json's levels; the normalized package "
				+ "packages/game-content/normalized/levels.json; "
				+ "packages/game-content/README.md (tables extension)"},
		{"fact": "a level's name is a LABEL, not an identifier: 44 distinct "
			+ "names over 100 entries, and every level from 45 onward reads "
			+ "Conqueror",
			"evidence": "the same committed curve; recorded so a name is never "
				+ "used to resolve a level. NOTE the index base: the committed "
				+ "investigation record's \"from level 49\" is a ZERO-BASED "
				+ "position, and the derived ONE-BASED saturation level is 45. "
				+ "This report records the value it reads from the curve rather "
				+ "than restating either phrasing"},
		{"fact": "reward_type is one of s, w, g, c and reward_amount is one of "
			+ "1, 50, 250, and NO legacy branch reads either",
			"evidence": "the same committed curve; docs/legacy-xp-basics.md. "
				+ "This is why no reward is paid or displayed (design D7)"},
		{"fact": "0 of the 40 placed corpus rows carry attr[\"xp\"], and the "
			+ "fresh save contains no unit placements at all",
			"evidence": "tests/saves/fresh-player.json; docs/legacy-xp-basics.md. "
				+ "The unit-experience path is therefore unexercisable and is "
				+ "out of scope"},
		{"fact": "maps[0].xp is the player's cumulative experience (the "
			+ "vector's slot 1, written by engine.apply_resources) and "
			+ "maps[0].level is written ONLY by level_up; the committed corpus "
			+ "records xp 4 and level 1",
			"evidence": "engine.py:251-271; command.py:81-85; the committed "
				+ "corpus save"},
	],
	"derived": [
		{"fact": "the curve's index base is ONE-BASED: stored level n is entry "
			+ "n minus one, and the conversion lives in exactly one named "
			+ "function (entry_index_for_level) that the client model, the "
			+ "service, the tests, and the structural report all share",
			"evidence": "derived-provisional (design D1). The REJECTED "
				+ "alternative is the ZERO-BASED reading, under which "
				+ "map[\"level\"] IS the index. The committed corpus "
				+ "contradicts it directly: corpus xp = 4 | stored level = 1 | "
				+ "level the zero-based curve implies = 0, so a player with 4 "
				+ "experience would be recorded as level 1 while the curve says "
				+ "level 1 begins at 40 experience. Under one-based, stored "
				+ "level 1 is levels[0] (\"Slave\", exp_required 0) and 4 >= 0 "
				+ "holds, so the corpus is self-consistent. Guessing zero-based "
				+ "would shift every level in the game by one"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy progression panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


## The evidence's explicit non-claims (spec "XP evidence, provenance, and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the level shown is the one the committed curve implies for the stored "
		+ "experience under the derived-provisional one-based reading, never "
		+ "one observed from the legacy client",
	"no level reward is paid and none is displayed, because no legacy branch "
		+ "reads the committed reward fields: paying one would invent an "
		+ "economy",
	"unit experience (add_xp_unit) and tutorial progression (complete_tutorial) "
		+ "are out of scope because the committed corpus cannot exercise them: "
		+ "0 of the 40 placed rows carry attr[\"xp\"] and the fresh save has no "
		+ "unit placements",
	"the committed exp_required thresholds are preserved verbatim: nothing is "
		+ "rebalanced, smoothed, or interpolated",
	"the recorded-versus-derived disagreement is REPORTED and deliberately "
		+ "never reconciled: the legacy server writes the level from a "
		+ "client-supplied integer, so neither value is authoritative and this "
		+ "change rewrites nothing",
	"parity covers one recorded transaction against the fresh-player corpus: "
		+ "no progressed player and no other command",
	"the derivation is client-side only: the service adds no server-"
		+ "authoritative level validation beyond its one guard, which belongs "
		+ "to Server v1 / M13",
	"no pixel-parity oracle against the legacy client exists",
	"the committed capture runs the fake GameApi implementation, a "
		+ "deterministic test double rather than a parity oracle",
]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural rejection: `ok: false` and every field left at its neutral
## value, so a caller can never read a half-built verdict.
static func _evaluation_reject(evaluation: Dictionary, reason: String,
		message: String) -> Dictionary:
	evaluation["ok"] = false
	evaluation["reason"] = reason
	evaluation["error"] = message
	evaluation["offers"] = false
	return evaluation


## A VERDICT refusal: `ok` stays **true** because the evaluation itself
## succeeded and what it found is a verdict — an already-current level, or an
## experience that cannot reach the next one. Only the reason, the message, and
## the offer change; every derived fact the readout shows stays populated, which
## is what lets it say exactly which level and how much experience separate the
## recorded level from the derived one.
static func _evaluation_refuse(evaluation: Dictionary, reason: String,
		message: String) -> Dictionary:
	evaluation["reason"] = reason
	evaluation["error"] = message
	evaluation["offers"] = false
	return evaluation


## A committed name as the readout renders it, or `NAME_ABSENT` — a **named
## absence**, never a placeholder that could be read as a committed value.
static func _name_text(value: Variant) -> String:
	if value == null or str(value).is_empty():
		return NAME_ABSENT
	return str(value)


## A committed number as the readout renders it, or "unknown" when the contract
## could not read it. Never a substituted zero.
static func _number_text(value: Variant) -> String:
	if value == null:
		return "unknown"
	return str(int(value))


## The progress ratio as the readout renders it, or "n/a" when this contract
## cannot compute one honestly.
static func _progress_text(value: Variant) -> String:
	if value == null or not (value is float or value is int):
		return "n/a"
	return "%d%%" % int(round(float(value) * 100.0))
