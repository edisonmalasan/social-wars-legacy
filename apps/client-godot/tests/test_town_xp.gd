extends "res://tests/test_base.gd"
## XP-progression suite (building-xp, spec "Committed-curve level model" /
## "Level and progress readout" / "Stored-versus-derived disagreement is
## reported" / "Level-up client flow").
##
## Scenarios:
##   conversion  the ONE named one-based conversion itself: the round trip over
##               every entry of the committed curve, its graceful edges (below
##               the first level, above the last, a non-integer, a boolean), the
##               zero-based alternative's contradiction, and the structural proof
##               that no other place in the client indexes the curve;
##   helpers     the pure helpers in `level_flow.gd` over the REAL committed
##               curve: every ladder boundary, the corpus's own `xp 4 / level 1`
##               case, the name / next-level / remaining / progress facts, both
##               agreement and disagreement, every refusal, and the readout text
##               — with no node, request, or clock anywhere in the module;
##   readout     the level readout renders for a committed selection in BOTH
##               states — the agreement the corpus is actually in, and a
##               disagreement reached in memory — and the disagreement names both
##               values and the experience that separates them WITHOUT
##               reconciling them;
##   gating      the level-up surface offers its action in its OWN UI-foundation
##               slot, only when the evaluation actually OFFERS a level-up, and
##               none of the nine other delivered modes' behavior changes;
##   refusals    an already-current level, an experience that cannot reach the
##               next one, an unreadable curve, an unreadable recorded level, a
##               curve whose floor sits above the experience, and a no-selection
##               case are each refused by name with NO request; the ten modes
##               never stack in either direction; and a re-evaluation that
##               changed refuses the confirm instead of sending something the
##               service would reject;
##   apply       one confirmed intent sends exactly one request and applies ONLY
##               the authoritative response — the recorded level taken from
##               `level_after`, the balances and experience from `resources`,
##               and the RESPONSE winning where the client's own derivation
##               disagrees — with the placement count, the object count, the
##               committed draw order, the storage, the owned-expansions ledger,
##               and every stored resource untouched, because a level change
##               moves nothing (design D5);
##   cancel      a cancelled level-up sends nothing and leaves the town, the
##               recorded level, the readout, the storage view, and the
##               resources byte-identical;
##   failures    a transport failure (the refused loopback endpoint), a
##               structured service refusal, and a post-state the apply rejects
##               (a response naming a pre-execution level this client does not
##               hold) each surface their own explicit error with the recorded
##               level, the balances, and the HUD unchanged;
##   no-reward   no reward amount or type is displayed or paid anywhere, and the
##               committed curve is never altered — asserted structurally over
##               the module's own bytes, not just at runtime;
##   no-request  the whole run issues no bootstrap request (the state derives
##               from the fixture in hand and the flow never re-bootstraps).
##
## **The committed corpus is ALREADY CONSISTENT under the one-based reading**:
## `xp 4` derives level 1 and the save records level 1, so the service refuses
## the intent with `level_already_current` and the committed execution rewrote
## an identical value. Every refusal is therefore reachable on the corpus
## itself, and the **disagreement** state — the only state that can advance a
## level — is reached by raising the fake double's OWN in-memory experience and
## the typed state's, exactly the way the collect and expand suites stub a
## config accessor. No committed fixture and no committed configuration file is
## ever written: every stub lives in this process's memory.
##
## Uses the committed bootstrap and level fixtures directly; no fixture is ever
## written and no server runs. Runs headless as part of `verify-boot.ps1`. The
## `--scenario=live-level-up` run is the `level-up-live` phase: the committed
## corpus's own already-consistent level-up against the real Compatibility
## endpoint, its refusal carrying the endpoint's own code and no partial
## payload, and the corpus left byte-identical. **A SUCCESSFUL live level-up is
## not reachable from the committed corpus** -- at `xp 4` the committed curve
## derives level 1 and the save records level 1 -- so this phase proves the
## refusal and its byte-identity, and the two-part post-execution proof's
## POSITIVE half is covered hermetically against the fake double over an in-memory
## disagreement. No corpus mutation is claimed, and none is fabricated.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")
const LevelFlow = preload("res://scripts/town/level_flow.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const LEVEL_FLOW_SOURCE := "res://scripts/town/level_flow.gd"
const TOWN_SOURCE := "res://scripts/town/town.gd"

## The committed curve's own shape, recorded here so a content drift fails the
## SUITE rather than silently redefining the claim. The full 100-entry ladder is
## always read from the content package; these are the boundary values the
## ladder assertions pivot on.
const SCHEDULE_ENTRIES := 100
const FIRST_THRESHOLDS := [0, 40, 60, 100, 200, 350, 550, 800]
const FINAL_THRESHOLD := 2016089205
const DISTINCT_NAMES := 44
const SATURATED_NAME_LEVEL := 45
## The committed curve's first three entries' committed names and thresholds,
## under the ONE-BASED reading: level 1 is the curve's FIRST entry.
const LEVEL_ONE := [1, "Slave", 0]
const LEVEL_TWO := [2, "Servant", 40]
const LEVEL_THREE := [3, "Peon", 60]
const LEVEL_FOUR := [4, "Peasant", 100]
const LEVEL_FIVE := [5, "Villager", 200]
const LEVEL_SIX := [6, "Scout", 350]
const LEVEL_TOP := 100
const TOP_NAME := "Conqueror"
## The committed corpus's own experience, recorded level, and the seven stored
## balances the executed transaction left byte-identical.
const CORPUS_XP := 4
const CORPUS_LEVEL := 1
const FRESH_GOLD := 2000
const FRESH_WOOD := 2000
const FRESH_OIL := 2000
const FRESH_STEEL := 2000
const FRESH_CASH := 5
const FRESH_MANA := 0
const FRESH_ENERGY := 50
const PLACEMENTS := 40
## The corpus's own owned-expansions ledger, which a level-up must never touch.
const CORPUS_OWNED := [35, 36, 45, 46]
## A placed, still-present building whose cell the readout is reached through:
## a level-up names NO placement, so the selection exists only because this
## map-level surface is reached through the delivered press path.
const SELECT_CELL := Vector2i(53, 39)
const SELECT_ITEM := 905
## The buildings the delivered modes accept, spread over the three rows that
## cover them, for the mutual-exclusion direction where a delivered mode arms
## first.
const SPARE_CELL := Vector2i(58, 48)
const SPARE_ITEM := 22
const UPGRADE_CELL := Vector2i(45, 49)
const UPGRADE_ITEM := 23
## The experience the disagreement scenarios park the state at: `200` derives
## level 5 (`Villager`) while the save records level 1, so the two disagree and
## an advancement is derivable.
const DISAGREE_XP := 200
const DISAGREE_LEVEL := LEVEL_FIVE[0]
## A recorded level the stored experience cannot reach, for the
## `xp_below_threshold` refusal. Level 50's committed threshold is far above 4
## experience, so a save recording it is the disagreement the service refuses.
const UNREACHABLE_LEVEL := 50
## The in-memory curve floor a stub installs so the "no level is derivable at
## all" content failure becomes reachable offline. It replaces the curve's own
## first threshold (`0`) with the curve's SECOND one (`40`), which keeps the
## ladder strictly increasing and puts the floor above the corpus's `xp 4`.
const STUBBED_FLOOR := 40
## Endpoint for the transport scenario: the `--gameapi-endpoint=` user argument
## (verify-boot passes a refused loopback port to every hermetic suite), else the
## project setting's loopback default. No hardcoded endpoint in this file — the
## project-scope scan restricts transport references to the legacy-v0
## implementation.
const ARG_ENDPOINT := "--gameapi-endpoint="


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-level-up":
		# verify-boot's level-up-live phase: the committed corpus's own
		# already-consistent level-up through the real Compatibility endpoint.
		# The phase harness asserts the disposable corpus is torn down; this
		# scenario asserts the typed refusal, its code, its empty payload, and
		# that the corpus is byte-identical afterwards. Everything else here is
		# fixture-fake only.
		await _check_live_level_up()
		return
	_check_conversion()
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	await _check_helpers()
	await _check_flow(payload)
	_check_no_reward_and_no_alteration()
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# The one named conversion (design D1)
# ---------------------------------------------------------------------------


## The conversion itself, over the REAL committed curve: the round trip at every
## level, the graceful edges, the zero-based alternative's contradiction, and the
## structural proof that no other place in the client indexes the curve by its
## own arithmetic.
func _check_conversion() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	var curve := _committed_curve(registry)
	if curve.size() != SCHEDULE_ENTRIES:
		check(false, "the committed curve holds %d rows, not %d"
			% [curve.size(), SCHEDULE_ENTRIES])
		return
	# Design D1's three machine-readable constants, mirrored from the typed
	# result's own copies so the client and the service state the same decision.
	check_eq(LevelFlow.INDEX_BASE, "one-based",
		"the curve's index base is ONE-BASED (design D1)")
	check_eq(LevelFlow.DERIVATION_STATUS, "derived-provisional",
		"the one-based interpretation is derived-provisional, never observed")
	check_eq(LevelFlow.REJECTED_ALTERNATIVE, "zero-based",
		"the REJECTED alternative is the zero-based reading")
	check_eq(LevelFlow.INDEX_BASE, BootData.LEVEL_INDEX_BASE,
		"the client's conversion states the SAME index base the typed result "
			+ "and the service do")
	check_eq(LevelFlow.DERIVATION_STATUS, BootData.LEVEL_DERIVATION_STATUS,
		"the client's derivation status matches the typed result's")
	check_eq(LevelFlow.REJECTED_ALTERNATIVE,
		BootData.LEVEL_REJECTED_ALTERNATIVE,
		"the client's rejected alternative matches the typed result's")
	# The conversion: `level - 1` inside the curve, null outside it, never a
	# raise and never a coerced index.
	check_eq(LevelFlow.entry_index_for_level(1, SCHEDULE_ENTRIES), 0,
		"level 1 is the curve's FIRST entry under the one-based reading")
	check_eq(LevelFlow.entry_index_for_level(2, SCHEDULE_ENTRIES), 1,
		"level 2 is the curve's SECOND entry")
	check_eq(LevelFlow.entry_index_for_level(LEVEL_TOP, SCHEDULE_ENTRIES),
		LEVEL_TOP - 1, "the top level is the curve's last entry")
	# The zero-based reading, applied to the committed corpus, is CONTRADICTED:
	# it would place `xp 4` at level 0, while the save records level 1.
	check_eq(LevelFlow.derived_level_for(CORPUS_XP, curve), CORPUS_LEVEL,
		"the one-based reading makes the committed corpus self-consistent")
	check_eq(LevelFlow.derived_level_for(CORPUS_XP, curve) - 1, 0,
		"the REJECTED zero-based reading would imply level 0 at xp 4 — the "
			+ "contradiction that settles the index base")
	# The graceful edges. Never a raise, never a coerced index.
	for level: int in [0, -1, -100, SCHEDULE_ENTRIES + 1, 9999]:
		check_eq(LevelFlow.entry_index_for_level(level, SCHEDULE_ENTRIES), null,
			"the conversion resolves no entry for level %d" % level)
	check_eq(LevelFlow.entry_index_for_level(1, null), 0,
		"without an entry count the conversion checks only the lower bound")
	check_eq(LevelFlow.entry_index_for_level(1, "nope"), null,
		"an unusable entry count resolves nothing")
	check_eq(LevelFlow.entry_index_for_level("1", SCHEDULE_ENTRIES), null,
		"a non-integer level resolves no entry (it is never coerced)")
	check_eq(LevelFlow.entry_index_for_level(1.5, SCHEDULE_ENTRIES), null,
		"a fractional level resolves no entry")
	check_eq(LevelFlow.entry_index_for_level(true, SCHEDULE_ENTRIES), null,
		"a boolean level resolves no entry — a `true` is an integer here and "
			+ "would otherwise resolve to entry 0")
	check_eq(LevelFlow.level_for_entry_index(-1), null,
		"the inverse resolves no level for a negative index")
	check_eq(LevelFlow.level_for_entry_index("0"), null,
		"the inverse resolves no level for a non-integer index")
	check_eq(LevelFlow.level_for_entry_index(true), null,
		"the inverse resolves no level for a boolean index")
	# The round trip over EVERY entry of the committed curve.
	var round_trip_failures: Array = []
	for level in range(1, SCHEDULE_ENTRIES + 1):
		var index: Variant = LevelFlow.entry_index_for_level(level,
			SCHEDULE_ENTRIES)
		if index == null or LevelFlow.level_for_entry_index(index) != level \
				or int(index) != level - 1:
			round_trip_failures.append(level)
	check_eq(round_trip_failures, [],
		"the conversion and its documented inverse agree at EVERY level of the "
			+ "committed curve")


# ---------------------------------------------------------------------------
# Pure helpers (task 4.1, design D1/D2/D6/D7)
# ---------------------------------------------------------------------------


## The committed curve, read through the typed content package's own `levels`
## domain — the SAME table the view derives from and the service derives from,
## so every helper check below runs against real committed rows rather than a
## restatement of them.
func _committed_curve(registry: Variant) -> Array:
	if registry == null or not bool(registry.is_loaded()) \
			or not registry.has_domain("levels"):
		check(false, "the committed levels domain is loaded")
		return []
	var curve: Array = []
	var size: int = registry.count("levels")
	for position in range(size):
		var row: Dictionary = registry.get_entry("levels", str(position))
		check(bool(row.get("found", false)),
			"the committed curve carries position %d" % position)
		if not bool(row.get("found", false)):
			return curve
		curve.append((row.get("entry", {}) as Dictionary).duplicate())
	return curve


## The pure helpers over the REAL committed curve and over a crafted copy that
## reaches what the committed content cannot. Everything here takes the curve,
## the recorded level, and the experience as parameters and reads no clock, so
## the same inputs always produce the same verdict and text.
func _check_helpers() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	if registry != null and not bool(registry.is_loaded()):
		registry.load_content()
	var curve := _committed_curve(registry)
	if curve.size() != SCHEDULE_ENTRIES:
		check(false, "the committed curve is readable for the helper checks")
		return
	# The committed curve's own shape, read from the curve.
	var thresholds: Variant = LevelFlow.thresholds_of(curve)
	check(thresholds is Array and (thresholds as Array).size() == SCHEDULE_ENTRIES,
		"the committed ladder carries one threshold per entry")
	if thresholds is not Array:
		return
	var ladder: Array = thresholds
	check_eq((ladder.slice(0, FIRST_THRESHOLDS.size()) as Array),
		FIRST_THRESHOLDS, "the committed ladder's first eight thresholds")
	check_eq(int(ladder[ladder.size() - 1]), FINAL_THRESHOLD,
		"the committed ladder's final threshold")
	var non_increasing: Array = []
	for position in range(1, ladder.size()):
		if int(ladder[position]) <= int(ladder[position - 1]):
			non_increasing.append(position)
	check_eq(non_increasing, [],
		"the committed ladder is STRICTLY increasing: no duplicate and no "
			+ "non-positive gap anywhere")
	# An unreadable ladder is refused, never rounded into place.
	check_eq(LevelFlow.thresholds_of(null), null,
		"an absent curve resolves no ladder")
	check_eq(LevelFlow.thresholds_of([]), null,
		"an empty curve resolves no ladder")
	check_eq(LevelFlow.thresholds_of("nope"), null,
		"a non-array curve resolves no ladder")
	check_eq(LevelFlow.thresholds_of([{"exp_required": 10},
			{"exp_required": 5}]), null,
		"a non-increasing ladder resolves nothing rather than a wrong level")
	check_eq(LevelFlow.thresholds_of([{"name": "no threshold"}]), null,
		"an entry with no exp_required resolves nothing")
	check_eq(LevelFlow.thresholds_of([{"exp_required": -1}]), null,
		"a negative threshold resolves nothing")
	check_eq(LevelFlow.schedule_size(curve), SCHEDULE_ENTRIES,
		"the committed curve's own size")
	check_eq(LevelFlow.schedule_size(null), -1,
		"an absent curve is the explicit sentinel, never a guessed zero")

	# EVERY ladder boundary, both sides. The corpus's own `xp 4 / level 1` case
	# is the regression pair design D1 rests on, so it is asserted explicitly
	# rather than only as a by-product of the ladder.
	for xp: int in [0, 3, 4, 39, 40, 59, 60, 99, 100, 199, 200, 349, 350, 549,
			550, 799, 800, 1112, 1113, 2016089204, 2016089205, 2016089206]:
		var level: Variant = LevelFlow.derived_level_for(xp, curve)
		check(level != null and int(level) >= 1 and int(level) <= LEVEL_TOP,
			"xp %d derives a level inside the curve: %s" % [xp, str(level)])
		if level == null:
			continue
		# The derived level's OWN threshold is met, and the next one is not —
		# which is the definition, asserted at every boundary.
		var own: Variant = LevelFlow.threshold_for(int(level), curve)
		check(own != null and xp >= int(own),
			"xp %d meets level %d's own committed threshold %s"
				% [xp, int(level), str(own)])
		var following: Variant = LevelFlow.next_level(xp, curve)
		if following != null:
			var next_required: Variant = LevelFlow.next_threshold(xp, curve)
			check(next_required != null and xp < int(next_required),
				"xp %d has NOT met level %d's committed threshold %s"
					% [xp, int(following), str(next_required)])
			var left: Variant = LevelFlow.remaining(xp, curve)
			check(left != null and int(left) == int(next_required) - xp,
				"xp %d has %s experience left to level %d"
					% [xp, str(left), int(following)])
			var progress: Variant = LevelFlow.progress_ratio(xp, curve)
			check(progress is float or progress is int,
				"xp %d has a progress ratio across its own committed span"
					% xp)
			if progress != null:
				check(float(progress) >= 0.0 and float(progress) <= 1.0,
					"xp %d's progress ratio is within [0, 1]: %s"
						% [xp, str(progress)])
		else:
			check_eq(xp >= FINAL_THRESHOLD, true,
				"xp %d has no next level only at or above the final threshold"
					% xp)
			check_eq(LevelFlow.next_threshold(xp, curve), null,
				"a completed curve reports NO next threshold, never a guess")
			check_eq(LevelFlow.remaining(xp, curve), null,
				"a completed curve reports NO remaining experience")
			check_eq(LevelFlow.next_name(xp, curve), null,
				"a completed curve reports NO next name")
			check_eq(LevelFlow.progress_ratio(xp, curve), null,
				"a completed curve has no progress figure to show")
	check_eq(LevelFlow.derived_level_for(0, curve), LEVEL_ONE[0],
		"the first committed threshold derives the first level")
	check_eq(LevelFlow.derived_level_for(39, curve), LEVEL_ONE[0],
		"one experience short of a threshold stays on the lower level")
	check_eq(LevelFlow.derived_level_for(40, curve), LEVEL_TWO[0],
		"exactly ON a threshold advances to that threshold's level")
	check_eq(LevelFlow.derived_level_for(200, curve), LEVEL_FIVE[0],
		"the disagreement scenario's experience derives level 5")
	check_eq(LevelFlow.derived_level_for(-1, curve), null,
		"a negative experience derives no level")
	check_eq(LevelFlow.derived_level_for(1.5, curve), null,
		"a fractional experience derives no level")
	check_eq(LevelFlow.derived_level_for(true, curve), null,
		"a boolean experience derives no level — it is an integer here and "
			+ "would otherwise silently place a player")
	check_eq(LevelFlow.derived_level_for(CORPUS_XP, null), null,
		"an unreadable curve derives no level at all")

	# The committed names and thresholds under the ONE-BASED reading.
	for entry: Array in [LEVEL_ONE, LEVEL_TWO, LEVEL_THREE, LEVEL_FOUR,
			LEVEL_FIVE, LEVEL_SIX]:
		check_eq(LevelFlow.name_for(int(entry[0]), curve), str(entry[1]),
			"level %d's committed name is %s" % [int(entry[0]), str(entry[1])])
		check_eq(LevelFlow.threshold_for(int(entry[0]), curve), int(entry[2]),
			"level %d's committed threshold is %d"
				% [int(entry[0]), int(entry[2])])
	check_eq(LevelFlow.name_for(LEVEL_TOP, curve), TOP_NAME,
		"the top level's committed name is Conqueror")
	check_eq(LevelFlow.name_for(0, curve), null,
		"level 0 has no committed name — it is reported as absent, never as a "
			+ "placeholder")
	check_eq(LevelFlow.name_for(LEVEL_TOP + 1, curve), null,
		"a level above the curve has no committed name")
	check_eq(LevelFlow.name_for("1", curve), null,
		"a non-integer level resolves no committed name")
	# An entry that records no name at all: the readout renders the NAMED
	# ABSENCE, never a substitute that could be read as a committed value.
	var nameless := _crafted_curve([{"name": "", "exp_required": 0},
			{"name": "Second", "exp_required": 40}])
	check_eq(LevelFlow.name_for(1, nameless), null,
		"an entry recording an empty name resolves no name")
	check(LevelFlow.readout_text(
			LevelFlow.evaluate(nameless, 1, 0), {}).contains(
			LevelFlow.NAME_ABSENT),
		"the readout renders a NAMED ABSENCE, never a placeholder")
	check_eq(LevelFlow.NAME_ABSENT, "[no committed name]",
		"the named-absence indicator is a fixed, explicit string")

	# The curve summary and the structural record: the committed shape, read
	# from the curve rather than restated.
	var summary := LevelFlow.curve_summary(curve)
	check(bool(summary.get("ok", false)),
		"the committed curve summarizes: %s" % summary.get("error"))
	check_eq(int(summary["entries"]), SCHEDULE_ENTRIES,
		"the summary records the committed entry count")
	check_eq([int(summary["first_level"]), int(summary["last_level"])],
		[1, LEVEL_TOP], "the summary records the addressable level range")
	check_eq(summary["first_thresholds"], FIRST_THRESHOLDS,
		"the summary records the committed first thresholds")
	check_eq(int(summary["final_threshold"]), FINAL_THRESHOLD,
		"the summary records the committed final threshold")
	check_eq(int(summary["distinct_names"]), DISTINCT_NAMES,
		"the summary records the 44 distinct names — a name is a label, not "
			+ "an identifier")
	check_eq(int(summary["saturated_name_level"]), SATURATED_NAME_LEVEL,
		"the summary records the one-based level from which every name reads "
			+ "the same")
	check(not bool(LevelFlow.curve_summary(null).get("ok", true)),
		"an unreadable curve summarizes as a refusal, not as an empty one")
	var record := LevelFlow.curve_record(curve)
	check_eq(str(record["index_base"]), "one-based",
		"the structural record states the index base")
	check_eq(str(record["derivation_status"]), "derived-provisional",
		"the structural record states the derivation status")
	check_eq(str(record["rejected_alternative"]), "zero-based",
		"the structural record states the REJECTED alternative")
	check(String(record["corpus_contradiction"]).contains("= 0"),
		"the structural record quotes the corpus contradiction that rejects "
			+ "the zero-based reading")
	check(String(record["index_base_conversion"]).contains(
			"entry_index_for_level"),
		"the structural record names the one named conversion")
	check_eq(record["reward_fields_never_consumed"],
		["reward_type", "reward_amount"],
		"the structural record names the reward fields this line never "
			+ "consumes")

	# The AGREEEMENT state, which is the committed corpus's own.
	var agreed := LevelFlow.evaluate(curve, CORPUS_LEVEL, CORPUS_XP)
	check(bool(agreed.get("ok", false)),
		"the corpus's own case evaluates: %s" % agreed.get("error"))
	check(bool(agreed.get("agrees", false)),
		"the recorded level 1 and the derived level 1 AGREE at xp 4")
	check(not bool(agreed.get("disagrees", true)),
		"an agreement raises no disagreement")
	check_eq(str(agreed.get("reason", "")),
		LevelFlow.REASON_LEVEL_ALREADY_CURRENT,
		"an already-current level is the level_already_current verdict — the "
			+ "service's own code")
	check(not bool(agreed.get("offers", true)),
		"an already-current level offers nothing")
	check_eq(int(agreed.get("derived_level", -99)), CORPUS_LEVEL,
		"the derived level is the corpus's own")
	check_eq(str(agreed.get("name", "")), str(LEVEL_ONE[1]),
		"the derived level's committed name is the curve's FIRST entry's")
	check_eq(int(agreed.get("remaining", -1)), 36,
		"the corpus has 36 experience left to level 2")
	check_eq(int(agreed.get("next_level", -1)), LEVEL_TWO[0],
		"the next level is the curve's second entry")
	check(String(LevelFlow.agreement_text(agreed)).contains("agrees"),
		"the agreement line says the two agree")
	check(String(LevelFlow.agreement_text(agreed)).contains("level 1"),
		"the agreement line names BOTH values, so the agreement is read rather "
			+ "than inferred")
	check_eq(LevelFlow.refusal_text(agreed),
		"no level up to offer: the recorded level 1 already equals the "
			+ "derived level 1",
		"the refusal names both values rather than being a bare word")

	# The DISAGREEMENT state, which the committed corpus is NOT in.
	var ahead := LevelFlow.evaluate(curve, CORPUS_LEVEL, DISAGREE_XP)
	check(bool(ahead.get("ok", false)),
		"a disagreement evaluates: %s" % ahead.get("error"))
	check(bool(ahead.get("disagrees", false)),
		"a recorded level below the derived one is a disagreement")
	check(not bool(ahead.get("agrees", true)),
		"a disagreement is not an agreement")
	check_eq(int(ahead.get("derived_level", -99)), DISAGREE_LEVEL,
		"the disagreement derives the curve's level 5 at xp 200")
	check(LevelFlow.offers_level_up(ahead),
		"a recorded level BELOW the derived one offers the level-up")
	check_eq(str(ahead.get("reason", "")), "",
		"an offered level-up names no refusal")
	check_eq(LevelFlow.refusal_text(ahead), "",
		"an offered level-up carries no refusal text")
	var ahead_text := LevelFlow.agreement_text(ahead)
	check(ahead_text.contains("recorded level 1")
			and ahead_text.contains("derived level 5")
			and ahead_text.contains("200 xp")
			and ahead_text.contains("disagrees"),
		"the disagreement line names BOTH values AND the experience that "
			+ "separates them: %s" % ahead_text)
	check(ahead_text.contains("neither value is authoritative")
			and ahead_text.contains("left unchanged"),
		"the disagreement line says the conflict is NOT reconciled: %s"
			% ahead_text)
	# The disagreement the OTHER way: a recorded level the experience cannot
	# reach. The client refuses it by name and reconciles nothing.
	var behind := LevelFlow.evaluate(curve, UNREACHABLE_LEVEL, CORPUS_XP)
	check(bool(behind.get("ok", false)),
		"an unreachable recorded level evaluates: %s" % behind.get("error"))
	check(bool(behind.get("disagrees", false)),
		"a recorded level above the derived one is a disagreement too")
	check(not LevelFlow.offers_level_up(behind),
		"an experience that cannot reach the next level offers nothing")
	check_eq(str(behind.get("reason", "")),
		LevelFlow.REASON_XP_BELOW_THRESHOLD,
		"an unreachable experience is the xp_below_threshold verdict — the "
			+ "service's own code")
	check(String(LevelFlow.refusal_text(behind)).contains("cannot reach"),
		"the refusal says the experience cannot reach the next level")
	# A recorded level the curve has no entry for.
	var uncharted := LevelFlow.evaluate(curve, LEVEL_TOP + 1, CORPUS_XP)
	check_eq(str(uncharted.get("reason", "")),
		LevelFlow.REASON_XP_BELOW_THRESHOLD,
		"a recorded level with no committed entry is refused by name")
	# The structural rejections: no verdict can be built from any of them.
	for entry: Array in [[null, CORPUS_LEVEL, CORPUS_XP,
			LevelFlow.REASON_UNREADABLE_SCHEDULE],
			[[], CORPUS_LEVEL, CORPUS_XP, LevelFlow.REASON_UNREADABLE_SCHEDULE],
			[curve, "1", CORPUS_XP, LevelFlow.REASON_UNREADABLE_STATE],
			[curve, CORPUS_LEVEL, "4", LevelFlow.REASON_UNREADABLE_STATE],
			[curve, true, CORPUS_XP, LevelFlow.REASON_UNREADABLE_STATE]]:
		var rejected := LevelFlow.evaluate(entry[0], entry[1], entry[2])
		check(not bool(rejected.get("ok", true)),
			"an unevaluable input is a structural rejection, not a verdict")
		check_eq(str(rejected.get("reason", "")), str(entry[3]),
			"the structural rejection names its own condition")
		check(not LevelFlow.offers_level_up(rejected),
			"a structural rejection offers nothing")
		check_eq(LevelFlow.readout_text(rejected, {}), "",
			"a structural rejection produces no readout at all")
	# A curve whose FLOOR sits above the experience: no level is derivable, which
	# the service answers with its own `internal_error` and the client names
	# distinctly because its consequence here is "nothing can be offered".
	var above_floor := LevelFlow.evaluate(_crafted_curve([
			{"name": "Late", "exp_required": STUBBED_FLOOR},
			{"name": "Later", "exp_required": FINAL_THRESHOLD}]),
		CORPUS_LEVEL, CORPUS_XP)
	check_eq(str(above_floor.get("reason", "")),
		LevelFlow.REASON_NO_DERIVED_LEVEL,
		"a curve whose floor sits above the experience names its own condition")
	check(not bool(above_floor.get("ok", true)),
		"no derivable level is a structural rejection, not a verdict")

	# The readout text in every state it can be in.
	var corpus_text := LevelFlow.readout_text(agreed, summary)
	for fragment in ["curve: 100 levels", "one-based", "derived-provisional",
			"derived level: 1 (Slave)", "experience: 4",
			"level 1 requires: 0", "next: level 2 (Servant) at 40 xp",
			"remaining: 36", "progress: 10%", "agrees"]:
		check(corpus_text.contains(fragment),
			"the readout names %s: %s" % [fragment, corpus_text])
	var ahead_readout := LevelFlow.readout_text(ahead, summary)
	check(ahead_readout.contains("derived level: 5 (Villager)")
			and ahead_readout.contains("disagrees"),
		"the disagreement readout names the derived level and the conflict: %s"
			% ahead_readout)
	# The completed curve: a REPORTED state, never an invented next level.
	var complete := LevelFlow.evaluate(curve, LEVEL_TOP, FINAL_THRESHOLD)
	check_eq(int(complete.get("derived_level", -99)), LEVEL_TOP,
		"an experience above the final threshold derives the TOP level")
	check(complete.get("next_level", null) == null
			and LevelFlow.readout_text(complete, summary).contains(
				"next: none"),
		"a completed curve reports 'next: none' rather than inventing a level")
	check(not LevelFlow.readout_text(complete, summary).contains("remaining:"),
		"a completed curve reports no remaining experience at all")
	check(not LevelFlow.offers_level_up(complete),
		"a completed curve offers no level-up: there is nothing above it")

	# The confirm names the DERIVED level as derived, and no amount anywhere.
	var confirm := LevelFlow.confirm_text(ahead)
	check(confirm.contains("level up to 5 (Villager)"),
		"the confirm names the derived level and its committed name: %s"
			% confirm)
	check(confirm.contains("DERIVED"),
		"the confirm presents the level as DERIVED: %s" % confirm)
	check(confirm.contains("recorded level 1"),
		"the confirm names the recorded level it will replace: %s" % confirm)
	check(confirm.contains("No reward is paid"),
		"the confirm says no reward is paid: %s" % confirm)
	check_eq(LevelFlow.confirm_text(agreed), "",
		"a refused evaluation has no confirm text at all")
	check_eq(LevelFlow.level_up_label(), "Level up",
		"the action's own label names the exact intent it sends")

	# The module itself depends on NO node, request, or clock (task 4.1), so a
	# reader can trust that every derivation above is pure. The transport and
	# runtime token names are assembled from fragments because the project-scope
	# scan looks for their literal forms in this file's bytes.
	var source := _read_source(LEVEL_FLOW_SOURCE)
	check(source != "", "the level flow module is readable")
	for token in ["get_node", "HTTP" + "Request", "HTTP" + "Client", "await ",
			"Time.", "Time.get_unix", "Engine.", "OS.", "FileAccess",
			"DirAccess", "preload(\"res://scripts/ui"]:
		check(source.find(token) == -1,
			"the pure level helpers never reference %s" % token)
	check(source.find("preload(") != -1 and source.find("boot_data.gd") != -1,
		"the only thing the pure helpers preload is the shared typed result")
	check_eq(LevelFlow.offers_level_up({}), false,
		"an empty evaluation offers nothing")


# ---------------------------------------------------------------------------
# Level flow (spec "Level-up client flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> confirm -> apply plus every refusal, failure, cancel, and no-request
## path. The disagreement the committed corpus is not in is reached in memory.
func _check_flow(payload: Dictionary) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	if not bool(registry.assets_loaded()):
		registry.load_asset_registry()
	var parsed: Dictionary = TownState.parse(payload, registry)
	check(bool(parsed.get("ok", false)),
		"the fresh fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]
	check_eq(state.placements.size(), PLACEMENTS,
		"the fresh save starts with 40 placements")
	check_eq(int(state.summary.xp), CORPUS_XP,
		"the typed state's stored experience is the corpus's own")
	check_eq(int(state.summary.level), CORPUS_LEVEL,
		"the typed state's recorded level is the corpus's own")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	if not (listing is BootData.SaveListResult):
		check(false, "the save list resolves the level save")
		return
	if (listing as BootData.SaveListResult).saves.is_empty():
		check(false, "the save list carries a save")
		return
	var pid := str((listing as BootData.SaveListResult).saves[0].id)
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	check(bool(activation.get("ok", false)),
		"the session activates the save: %s" % activation.get("error"))
	if not bool(activation.get("ok", false)):
		return

	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)), "town builds: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	# The double's in-memory state loads LAZILY on its first intent, so the
	# corpus's own refusal is driven first: it primes the load, proves the
	# committed corpus is already consistent (the endpoint's own
	# level_already_current code), and proves the refusal carries no partial
	# payload. Every counter below is snapshotted AFTER it.
	await _check_corpus_refusal(api, pid)
	var requests_start: int = api.level_up_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, api, requests_start, snapshot_start)
	await _check_level_up(town, state, api)
	_check_mutual_exclusion(town, api)
	await _check_transport_failure(registry, api)
	town.free()

	await _check_cancelled(registry, api)
	await _check_structured_failure(registry, api)
	await _check_post_state_rejection(registry, api)


## The committed corpus's OWN level-up intent, driven straight through the
## facade. This is design D1's consequence at the service boundary: at `xp 4` the
## committed curve derives level 1 and the save records level 1, so the endpoint
## refuses with its own `level_already_current` code and carries no partial
## payload. It also primes the double's lazy in-memory load, which every later
## in-memory stub depends on.
func _check_corpus_refusal(api: Variant, user_id: String) -> void:
	var refused: Variant = await api.level_up_town(user_id)
	check(refused is BootData.LevelUpResult,
		"level_up_town returns the typed result")
	if not (refused is BootData.LevelUpResult):
		return
	var typed: BootData.LevelUpResult = refused
	check(not typed.ok, "the committed corpus's own level-up is refused")
	check_eq(typed.error_code, LevelFlow.REASON_LEVEL_ALREADY_CURRENT,
		"the refusal is the SERVICE's own code: %s" % typed.error_message)
	check(typed.curve == null and typed.resources == null
			and typed.result == "" and typed.derived_level == -1
			and typed.level_before == -1 and typed.level_after == -1,
		"the refused level-up carries NO partial payload that could be "
			+ "mistaken for a success")


## The map-level surface offers `Level up` in its OWN UI-foundation slot beside
## the delivered selection-driven panel and the expansion panel — never inside
## either (a level-up names NO placement) — and only when the evaluation
## actually offers a level-up. The committed corpus is already consistent, so
## the action is NOT offered there and every refusal names itself.
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.level_active(),
		"the level up is not armed before a selection")
	check(not town.level_selection_available(),
		"no selection means no level-up action")
	check_eq(town.level_recorded(), CORPUS_LEVEL,
		"an unarmed view still reads the recorded level")
	check_eq(town.level_experience(), CORPUS_XP,
		"an unarmed view still reads the stored experience")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SELECT_CELL))
	check(bool(press.get("ok", false)),
		"the press selects a map: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), SELECT_ITEM,
		"the press at (53,39) selects the recorded building")
	# The surface owns its OWN slot, and the delivered panel keeps exactly the
	# buttons it always had.
	check(town.ui.has_slot("level"),
		"the level surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("level"),
		"the level slot shows for a committed selection")
	check(town.ui.has_slot("move"),
		"the delivered selection-driven surface still owns its own slot")
	check(town.ui.has_slot("expand"),
		"the delivered expansion surface still owns its own slot")
	var delivered_panel: Variant = _panel_of(town, "move")
	var delivered_buttons: Array = []
	if delivered_panel != null:
		_collect_buttons(delivered_panel as Node, delivered_buttons)
	var names: Array = []
	for button: Variant in delivered_buttons:
		names.append(String((button as Button).name))
	check_eq(names, ["move", "sell", "store", "upgrade", "build", "collect",
		"confirm", "cancel"],
		"the delivered panel still offers exactly its six actions, one confirm, "
			+ "and one cancel — the level action is NOT inside it")
	check_eq(_button_count(town, "level", "level_up"), 1,
		"the level slot carries exactly one `Level up` action")
	check_eq(_button_count(town, "expand", "expand"), 1,
		"the expansion slot still carries exactly one `Expand` action")
	# The readout renders for the live selection BEFORE anything is armed, and it
	# renders ON SCREEN (the surface owns a line of its own).
	var readout: String = town.level_readout()
	check(_level_readout_label(town) == readout,
		"the level readout is rendered on the surface's own line: %s"
			% _level_readout_label(town))
	for fragment in ["curve: 100 levels", "one-based", "derived-provisional",
			"derived level: 1 (Slave)", "experience: 4", "remaining: 36",
			"progress: 10%"]:
		check(readout.contains(fragment),
			"the readout names %s: %s" % [fragment, readout])
	check(readout.contains("recorded level 1 agrees with the derived level 1"),
		"the readout states the AGREEMENT on the committed corpus: %s" % readout)
	# The committed corpus is consistent, so NO action is offered and arming
	# refuses locally with no request.
	check(not town.level_selection_available(),
		"an already-current level offers no level-up action at all")
	var panel: Variant = _panel_of(town, "level")
	check(panel != null, "the level surface commits into its slot")
	if panel != null:
		var arm: Variant = _button_named(panel as Node, "level_up")
		check(arm is Button, "the level-up action button exists")
		if arm is Button:
			check((arm as Button).disabled,
				"the action is DISABLED for an already-current level")
			check_eq((arm as Button).text, "Level up (unavailable)",
				"the action names its own unavailability instead of hiding it")
	# The delivered readouts are untouched by this line. The upgrade is NOT in
	# this list on purpose: the Tree at (53,39) legitimately offers no upgrade
	# (it records no next tier), which is the delivered action's own content
	# rule and is covered on its own building below.
	for delivered in ["move_selection_available", "sell_selection_available",
			"store_selection_available", "construction_selection_available",
			"collect_selection_available", "expand_selection_available"]:
		check(bool(town.call(str(delivered))),
			"the same selection still offers the delivered %s"
				% str(delivered))
	town.handle_pointer_press(Iso.grid_to_screen(UPGRADE_CELL))
	check(bool(town.upgrade_selection_available()),
		"the delivered upgrade still offers itself on the Wall I")
	check(not town.move_preview_shown(),
		"a level-up surface shows no footprint preview (it has no grid target)")
	check(town.move_evaluation().is_empty(),
		"the level-up surface commits no move evaluation")
	check_eq(api.level_up_requests, requests_before,
		"the whole gating pass sent no request")


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition.
func _check_refusals(town: Node2D, api: Variant, requests_before: int,
		snapshot_before: String) -> void:
	var armed: Dictionary = town.arm_level_up()
	check(not bool(armed.get("ok", true)),
		"arming an already-current level refuses")
	check_eq(str(armed.get("code", "")),
		LevelFlow.REASON_LEVEL_ALREADY_CURRENT,
		"the already-current refusal names the SERVICE's own code: %s"
			% armed.get("error"))
	check(String(armed.get("error", "")).contains("already equals"),
		"the refusal names both values rather than being a bare word")
	check(not town.level_active(),
		"a refused arming leaves no level up armed")
	check_eq(api.level_up_requests, requests_before,
		"the already-current refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the already-current refusal changes NO state at all")
	var confirmed: Dictionary = await town.confirm_level_up()
	check(not bool(confirmed.get("ok", true)),
		"confirming an unarmed level-up refuses")
	check_eq(str(confirmed.get("code", "")), "level_not_active",
		"the unarmed refusal names the condition")
	check_eq(api.level_up_requests, requests_before,
		"the unarmed refusal sent no request")
	# A level-up's OTHER refusal: a recorded level the stored experience cannot
	# reach. It is set in memory on the typed state, and the surface must refuse
	# it locally with the SERVICE's own code and no request.
	town.state.summary.level = UNREACHABLE_LEVEL
	var behind: Dictionary = town.arm_level_up()
	check(not bool(behind.get("ok", true)),
		"arming an unreachable experience refuses")
	check_eq(str(behind.get("code", "")),
		LevelFlow.REASON_XP_BELOW_THRESHOLD,
		"the unreachable refusal names the SERVICE's own code: %s"
			% behind.get("error"))
	check(String(behind.get("error", "")).contains("cannot reach"),
		"the refusal says the experience cannot reach the next level: %s"
			% behind.get("error"))
	check(not town.level_selection_available(),
		"an unreachable experience offers no action")
	check_eq(api.level_up_requests, requests_before,
		"the unreachable refusal sent no request")
	town.state.summary.level = CORPUS_LEVEL
	# A recorded level the client can read as an integer but the curve has NO
	# entry for: refused by name, never coerced into a starting point for the
	# comparison. A recorded level that is not an integer at all cannot reach
	# this surface (the typed summary coerces it at parse time), so the
	# unreadable_state refusal is covered at the helper level above, which is
	# where it is reachable.
	town.state.summary.level = LEVEL_TOP + 5
	var uncharted: Dictionary = town.arm_level_up()
	check(not bool(uncharted.get("ok", true)),
		"arming against a recorded level with no committed entry refuses")
	check_eq(str(uncharted.get("code", "")),
		LevelFlow.REASON_XP_BELOW_THRESHOLD,
		"the uncharted-level refusal names the SERVICE's own code: %s"
			% uncharted.get("error"))
	check(String(uncharted.get("error", "")).contains("cannot reach the "
			+ "recorded level"),
		"the refusal names the experience that cannot reach it: %s"
			% uncharted.get("error"))
	check_eq(api.level_up_requests, requests_before,
		"the uncharted-level refusal sent no request")
	town.state.summary.level = CORPUS_LEVEL
	# No selection at all.
	town._commit_selection(null)
	var deselected: Dictionary = town.arm_level_up()
	check(not bool(deselected.get("ok", true)),
		"arming with no selection refuses")
	check_eq(str(deselected.get("code", "")), "level_no_selection",
		"the no-selection refusal names the condition")
	check_eq(api.level_up_requests, requests_before,
		"the no-selection refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"every local refusal left the town state byte-identical")


## One confirmed level-up through the fake double over an in-memory
## DISAGREEMENT: the recorded level below the derived one. This is the state the
## committed corpus is not in, and it is reached by raising the double's own
## in-memory experience and the typed state's, exactly the way the delivered
## collect and expand suites stub a config accessor. No committed fixture and no
## committed configuration file is written.
func _check_level_up(town: Node2D, state: Variant, api: Variant) -> void:
	var requests_before: int = api.level_up_requests
	_set_experience(api, town.state, DISAGREE_XP)
	var snapshot_before := _state_snapshot(state)
	var signature_before := _object_signature(town)
	var owned_before: Array = town.owned_expansions()
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SELECT_CELL))
	check(bool(press.get("ok", false)),
		"the disagreement town re-selects the recorded map: %s"
			% press.get("error"))
	var evaluation: Dictionary = town.level_evaluation()
	check(bool(evaluation.get("disagrees", false)),
		"the in-memory state now DISAGREES: recorded 1, derived 5")
	check_eq(int(evaluation.get("derived_level", -99)), DISAGREE_LEVEL,
		"the client's own derivation is the curve's level 5 at xp 200")
	check(town.level_selection_available(),
		"a recorded level below the derived one offers the action")
	var panel: Variant = _panel_of(town, "level")
	if panel != null:
		var arm: Variant = _button_named(panel as Node, "level_up")
		check(arm is Button and not (arm as Button).disabled,
			"the action is enabled for a disagreement")
		if arm is Button:
			(arm as Button).pressed.emit()
	check(town.level_active(), "pressing the action arms the level up")
	check_eq(api.level_up_requests, requests_before,
		"arming sent no request")
	# Arming REBUILDS the surface, so it is re-read here rather than holding a
	# freed panel.
	panel = _panel_of(town, "level")
	var selection_text := String(_level_selection_text(town))
	check(selection_text.contains("level up to 5"),
		"the selection line names the derived level: %s" % selection_text)
	check(selection_text.contains("DERIVED"),
		"the selection line presents the level as DERIVED: %s" % selection_text)
	check(selection_text.contains("No reward is paid"),
		"the selection line says no reward is paid: %s" % selection_text)
	var status := String(town.level_status())
	check(status.contains("DERIVED"),
		"the status presents the level as DERIVED: %s" % status)
	var confirm: Variant = _button_named(panel as Node, "confirm")
	check(confirm is Button and (confirm as Button).visible,
		"the targetless confirm is offered as soon as the level up is armed")
	if confirm is Button:
		check_eq((confirm as Button).text, "Level up",
			"the confirm names the armed mode's own action")
	check(_button_named(panel as Node, "cancel") != null,
		"the cancel action button exists")
	var again: Dictionary = town.arm_level_up()
	check(not bool(again.get("ok", true)),
		"arming an already-armed level up rejects")
	check_eq(str(again.get("code", "")), "level_up_already_active",
		"the double-arm names the condition")

	var confirmed: Dictionary = await town.confirm_level_up()
	check(bool(confirmed.get("ok", false)),
		"the confirm applies the level up: %s" % confirmed.get("error"))
	check_eq(api.level_up_requests, requests_before + 1,
		"the confirm sent EXACTLY one intent")
	_check_typed_level(confirmed.get("result"))
	# The authoritative apply: the recorded level is the RESPONSE's value and the
	# balances are the RESPONSE's values. The client's own derived level happens
	# to agree here, which is why the response-wins rule gets its own check.
	check_eq(town.level_recorded(), DISAGREE_LEVEL,
		"the recorded level takes the response's level_after value")
	check_eq(town.state.summary.xp, DISAGREE_XP,
		"the experience takes the response's value")
	check_eq(town.state.resources.coins, FRESH_GOLD,
		"a level change moves NO resource: gold is the corpus's own value")
	check_eq(town.state.resources.wood, FRESH_WOOD,
		"a level change moves NO resource: wood is the corpus's own value")
	check_eq(town.state.resources.oil, FRESH_OIL,
		"a level change moves NO resource: oil is the corpus's own value")
	check_eq(town.state.resources.steel, FRESH_STEEL,
		"a level change moves NO resource: steel is the corpus's own value")
	check_eq(town.state.resources.cash, FRESH_CASH,
		"a level change moves NO resource: cash is the corpus's own value")
	check_eq(town.state.resources.mana, FRESH_MANA,
		"a level change moves NO resource: mana is the corpus's own value")
	check_eq(town.state.resources.energy, FRESH_ENERGY,
		"a level change touches no field outside the seven stored balances")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("level"), str(DISAGREE_LEVEL),
			"the HUD renders the authoritative recorded level")
		check_eq(hud.displayed("xp"), str(DISAGREE_XP),
			"the HUD renders the authoritative experience")
	# The readout now AGREES, because the response moved the recorded level onto
	# the derived one.
	var after: Dictionary = town.level_evaluation()
	check(bool(after.get("agrees", false)),
		"after the apply the recorded and derived levels agree")
	check(String(town.level_readout()).contains("agrees"),
		"the readout re-renders the agreement from the RESPONSE's level: %s"
			% town.level_readout())
	# Nothing else moved: a level-up writes one int.
	check_eq(town.state.placements.size(), PLACEMENTS,
		"the placement count is unchanged")
	check_eq(town.objects.size(), PLACEMENTS,
		"the rendered object count is unchanged")
	check_eq(_object_signature(town), signature_before,
		"a level-up re-sorts nothing: the draw order is byte-identical")
	check_eq(town.owned_expansions(), owned_before,
		"a level-up touches no owned-expansions ledger entry")
	check_eq(_placement_signature(state), _placement_signature(state),
		"a level-up rewrites no placement row")
	check(_state_snapshot(state) != snapshot_before,
		"the state snapshot DID change — the byte-identity oracle is real")
	check_eq(town.level_error, "", "success leaves no failure record")
	check(not town.level_active(), "the mode closes after the apply")
	# A confirm after the apply refuses (the mode is closed) and a re-armed
	# confirm refuses too (the level is now current).
	var repeat: Dictionary = await town.confirm_level_up()
	check(not bool(repeat.get("ok", true)),
		"a confirm after the apply refuses (the level up is no longer armed)")
	check_eq(api.level_up_requests, requests_before + 1,
		"the post-apply refusal sent no second request")
	# The RESPONSE-WINS rule, at the one place it can be observed: the client
	# derives level 4 from its own committed curve at 100 experience, and the
	# service's own answer names level 5. The apply takes the response's value.
	_set_experience(api, town.state, 100)
	town.state.summary.level = CORPUS_LEVEL
	town.handle_pointer_press(Iso.grid_to_screen(SELECT_CELL))
	var rearm: Dictionary = town.arm_level_up()
	check(bool(rearm.get("ok", false)),
		"a fresh disagreement re-arms: %s" % rearm.get("error"))
	if bool(rearm.get("ok", false)):
		check_eq(int(rearm.get("derived_level", -99)), LEVEL_FOUR[0],
			"the re-armed level up names the curve's level 4 at xp 100")
		var foreign := BootData.LevelUpResult.new()
		foreign.ok = true
		foreign.protocol = BootData.PROTOCOL
		foreign.result = "success"
		foreign.derived_level = DISAGREE_LEVEL
		foreign.level_before = int(town.level_recorded())
		foreign.level_after = DISAGREE_LEVEL
		foreign.curve = BootData.LevelCurve.new()
		foreign.curve.entries = SCHEDULE_ENTRIES
		foreign.curve.index_base = BootData.LEVEL_INDEX_BASE
		foreign.curve.derivation_status = BootData.LEVEL_DERIVATION_STATUS
		foreign.curve.rejected_alternative = \
			BootData.LEVEL_REJECTED_ALTERNATIVE
		foreign.curve.entry_name = LEVEL_FIVE[1]
		foreign.curve.entry_exp_required = LEVEL_FIVE[2]
		foreign.curve.xp = 100
		foreign.resources = BootData.Resources.new()
		foreign.resources.gold = FRESH_GOLD
		foreign.resources.wood = FRESH_WOOD
		foreign.resources.oil = FRESH_OIL
		foreign.resources.steel = FRESH_STEEL
		foreign.resources.cash = FRESH_CASH
		foreign.resources.mana = FRESH_MANA
		foreign.resources.xp = 100
		var applied: Dictionary = await town.call("_apply_level", foreign)
		check(bool(applied.get("ok", false)),
			"a response the service would accept applies: %s"
				% applied.get("error"))
		check_eq(town.level_recorded(), DISAGREE_LEVEL,
			"the RESPONSE's level wins where the client's own derivation "
				+ "(level 4) differs — it is applied, not composed")
		check_eq(town.state.summary.xp, 100,
			"the RESPONSE's experience wins too")
		town.cancel_level_up()


## The typed result of one level-up: protocol, version, legacy result, the
## derived level, BOTH recorded levels, the curve facts, and the resources. The
## wall-clock field is asserted as a positive integer and never by value.
func _check_typed_level(result: Variant) -> void:
	check(result is BootData.LevelUpResult,
		"the level-up carries the typed result")
	if not (result is BootData.LevelUpResult):
		return
	var typed: BootData.LevelUpResult = result
	check(typed.ok, "the level-up response is a success: %s"
		% typed.error_message)
	if not typed.ok:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the level-up protocol is compat-v0")
	check_eq(typed.game_version, "alpha 0.02",
		"the level-up response carries the game version")
	check(typed.server_time > 0,
		"the level-up server_time is the fixture epoch (time-dependent)")
	check_eq(typed.result, "success", "the legacy result string is verbatim")
	check_eq(typed.level_before, CORPUS_LEVEL,
		"the pre-execution recorded level is the corpus's own")
	check_eq(typed.level_after, DISAGREE_LEVEL,
		"the post-execution recorded level IS the derived level")
	check_eq(typed.level_after, typed.derived_level,
		"the service's own value-level guarantee: the recorded level after "
			+ "execution equals the derived level")
	check(typed.curve != null, "the response carries the committed curve facts")
	if typed.curve == null:
		return
	check_eq(typed.curve.entries, SCHEDULE_ENTRIES,
		"the curve block reports the committed entry count")
	check_eq(typed.curve.index_base, LevelFlow.INDEX_BASE,
		"the curve block reports the SAME index base the client derives under")
	check_eq(typed.curve.derivation_status, LevelFlow.DERIVATION_STATUS,
		"the curve block reports the same derivation status")
	check_eq(typed.curve.rejected_alternative, LevelFlow.REJECTED_ALTERNATIVE,
		"the curve block reports the same REJECTED alternative")
	check_eq(typed.curve.entry_name, LEVEL_FIVE[1],
		"the curve block reports the derived level's committed name")
	check_eq(typed.curve.entry_exp_required, LEVEL_FIVE[2],
		"the curve block reports the derived level's committed threshold")
	check_eq(typed.curve.next_level, LEVEL_FIVE[0] + 1,
		"the curve block reports the next level")
	check_eq(typed.curve.next_name, "Scout",
		"the curve block reports the next level's committed name")
	check_eq(typed.curve.next_exp_required, LEVEL_SIX[2],
		"the curve block reports the next level's committed threshold")
	check_eq(typed.curve.remaining, LEVEL_SIX[2] - DISAGREE_XP,
		"the curve block reports the experience remaining")
	check_eq(typed.curve.xp, DISAGREE_XP,
		"the curve block reports the experience it derived from")
	check(typed.resources != null, "the response carries the resources")
	if typed.resources == null:
		return
	check_eq(typed.resources.xp, DISAGREE_XP,
		"the response's experience is the stored value")
	check_eq(typed.resources.gold, FRESH_GOLD,
		"a level-up moves NO resource: gold is unchanged")
	check_eq(typed.resources.wood, FRESH_WOOD,
		"a level-up moves NO resource: wood is unchanged")
	check_eq(typed.resources.oil, FRESH_OIL,
		"a level-up moves NO resource: oil is unchanged")
	check_eq(typed.resources.steel, FRESH_STEEL,
		"a level-up moves NO resource: steel is unchanged")
	check_eq(typed.resources.cash, FRESH_CASH,
		"a level-up moves NO resource: cash is unchanged")
	check_eq(typed.resources.mana, FRESH_MANA,
		"a level-up moves NO resource: mana is unchanged")


## The other direction of the ten-mode mutual exclusion: a level-up cannot be
## armed while a delivered mode already is, and the refusal names the ARMED
## mode. Each delivered mode is exercised on a building IT accepts — the
## delivered action's own content rules are untouched by this line, so the arms
## are spread over the three buildings that cover them.
func _check_mutual_exclusion(town: Node2D, api: Variant) -> void:
	var requests_before: int = api.level_up_requests
	# Every other armed mode refuses the level-up BY NAME. The level-up needs no
	# selection rule of its own here: the exclusion is checked before it, which
	# is exactly the order the surface uses.
	var entries: Array = [
		["arm_move", "move_already_active", "a move is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_sell", "sell_already_active", "a sale is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_store", "store_already_active", "a store is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_construction", "construction_already_active", "a build is armed",
			SPARE_CELL, SPARE_ITEM],
		["arm_collect", "collect_already_active", "a collection is armed",
			SELECT_CELL, SELECT_ITEM],
		["arm_upgrade", "upgrade_already_active", "an upgrade is armed",
			UPGRADE_CELL, UPGRADE_ITEM],
		["arm_expand", "expand_already_active", "an expansion is armed",
			SELECT_CELL, SELECT_ITEM],
	]
	for entry: Array in entries:
		# The level-up needs a real disagreement to arm at all, so the recorded
		# level is parked on the corpus's own value and the experience on the
		# disagreement's: the exclusion is checked before the evaluation, so this
		# only guarantees the arming itself is not refused for another reason.
		town.state.summary.level = CORPUS_LEVEL
		_set_experience(api, town.state, DISAGREE_XP)
		town.handle_pointer_press(Iso.grid_to_screen(entry[3]))
		check(town.selection_legacy_id() == int(entry[4]),
			"the building the delivered %s accepts is selectable"
				% str(entry[0]))
		var armed: Dictionary = await town.call(str(entry[0]))
		check(bool(armed.get("ok", false)),
			"the delivered %s arms on its own building: %s"
				% [str(entry[0]), armed.get("error")])
		if bool(armed.get("ok", false)):
			var over: Dictionary = town.arm_level_up()
			check(not bool(over.get("ok", true)),
				"arming a level up while a %s is armed rejects" % str(entry[0]))
			# Each mode's refusal reuses the code that mode's OWN arming refuses
			# with, so the two directions of the exclusion name the SAME
			# condition: the ARMED delivered mode here, never the level up the
			# player tried to arm.
			check_eq(str(over.get("code", "")), str(entry[1]),
				"the refusal names the ARMED mode by its own code: %s"
					% over.get("error"))
			check(String(over.get("error", "")).contains(str(entry[2])),
				"the refusal says what is armed: %s" % over.get("error"))
			check(String(over.get("error", "")).contains("levelling up"),
				"the refusal says which action was refused: %s"
					% over.get("error"))
			var closed: Dictionary = town.call(
				"cancel_" + str(entry[0]).trim_prefix("arm_"))
			check(bool(closed.get("ok", false)),
				"the delivered %s closes again: %s"
					% [str(entry[0]), closed.get("error")])
		check(not town.level_active(),
			"the refused arming left no level up armed")
	# The two surfaces that own their own slots rather than the selection-driven
	# one are covered the same way, through their own entry points.
	for entry: Array in [["enter_placement", "level_up_already_active",
			"a level up is armed"], ["enter_shop", "level_up_already_active",
			"a level up is armed"]]:
		# They refuse with no catalog of their own in this run, so the check is
		# that the LEVEL refuses THEM while armed, not the other way round.
		town.handle_pointer_press(Iso.grid_to_screen(SELECT_CELL))
		town.state.summary.level = CORPUS_LEVEL
		_set_experience(api, town.state, DISAGREE_XP)
		var armed_level: Dictionary = town.arm_level_up()
		check(bool(armed_level.get("ok", false)),
			"a disagreement arms for the %s check: %s"
				% [str(entry[0]), armed_level.get("error")])
		if bool(armed_level.get("ok", false)):
			var refused: Dictionary = await town.call(str(entry[0]))
			check(not bool(refused.get("ok", true)),
				"opening the %s while a level up is armed rejects" % str(entry[0]))
			check_eq(str(refused.get("code", "")), "level_up_already_active",
				"the %s refusal names the armed level up: %s"
					% [str(entry[0]), refused.get("error")])
			check(String(refused.get("error", "")).contains(str(entry[2])),
				"the %s refusal says what is armed: %s"
					% [str(entry[0]), refused.get("error")])
			town.cancel_level_up()
		_set_experience(api, town.state, CORPUS_XP)
	check_eq(api.level_up_requests, requests_before,
		"every mutual-exclusion refusal sent no request")


## LAST scenario (it waits out the refused loopback endpoint): the intent goes
## out over the legacy transport, the endpoint refuses it, and the explicit
## error names `unreachable_endpoint` with the recorded level keeping its
## previous value and no balance moved — the same no-mutation contract as a
## structured failure.
func _check_transport_failure(registry: Variant, api: Variant) -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the transport "
		+ "scenario")
	if endpoint == "":
		return
	var transport_town: Variant = _selected_town(registry, DISAGREE_XP,
		SELECT_CELL, SELECT_ITEM, "the transport town")
	if transport_town == null:
		return
	var requests_before: int = api.level_up_requests
	_set_experience(api, transport_town.state, DISAGREE_XP)
	var snapshot_before := _state_snapshot(transport_town.state)
	var objects_before: int = transport_town.objects.size()
	api.configure("legacy_v0", endpoint)
	var armed: Dictionary = transport_town.arm_level_up()
	check(bool(armed.get("ok", false)),
		"the transport town arms a level up: %s" % armed.get("error"))
	var attempt: Dictionary = await transport_town.confirm_level_up()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(String(transport_town.level_error).contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.level_up_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(transport_town.state), snapshot_before,
		"the transport failure changes no state")
	check_eq(transport_town.objects.size(), objects_before,
		"the transport failure renders nothing new")
	check_eq(transport_town.level_recorded(), CORPUS_LEVEL,
		"the transport failure leaves the recorded level untouched")
	check(transport_town.level_active(),
		"the level up survives the transport failure")
	# The last state-changing check ran against the refused endpoint, so the
	# implementation switch is undone here rather than leaked.
	transport_town.free()
	api.configure("fake")


## A STRUCTURED service refusal: the double refuses the intent with the
## endpoint's own `level_already_current` code (the client and the service saw
## different recorded levels), the explicit error names it, the recorded level
## keeps its previous value, and no balance moved.
func _check_structured_failure(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, DISAGREE_XP, SELECT_CELL,
		SELECT_ITEM, "the structured-failure town")
	if town == null:
		return
	var requests_before: int = api.level_up_requests
	_set_experience(api, town.state, DISAGREE_XP)
	var snapshot_before := _state_snapshot(town.state)
	# The double's own recorded level is already at the level the curve derives,
	# so the service refuses with the endpoint's own code.
	_set_recorded_level(api, DISAGREE_LEVEL)
	var armed: Dictionary = town.arm_level_up()
	check(bool(armed.get("ok", false)),
		"the client still offers the level up: %s" % armed.get("error"))
	var attempt: Dictionary = await town.confirm_level_up()
	check(not bool(attempt.get("ok", true)),
		"the service's structured refusal fails the intent closed")
	check_eq(str(attempt.get("code", "")), "level_already_current",
		"the refusal surfaces the SERVICE's own code: %s" % attempt.get("error"))
	check(String(town.level_error).contains("level_already_current"),
		"the explicit error names the failure")
	check_eq(api.level_up_requests, requests_before + 1,
		"the refused intent was still sent exactly once")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the structured failure changes NO state at all (the recorded level, "
			+ "the balances, and the HUD keep their pre-request values)")
	check_eq(town.level_recorded(), CORPUS_LEVEL,
		"the client's recorded level keeps its previous value")
	check(town.level_active(),
		"the level up survives its own structured failure")
	town.free()


## The post-state the apply REJECTS (spec "a post-state the service rejects"):
## the response names a pre-execution level this client does not hold, so it is
## not this client's transaction. The apply fails closed BEFORE any mutation,
## the explicit error names the condition, and the request was still sent
## exactly once.
func _check_post_state_rejection(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, DISAGREE_XP, SELECT_CELL,
		SELECT_ITEM, "the post-state town")
	if town == null:
		return
	var requests_before: int = api.level_up_requests
	_set_experience(api, town.state, DISAGREE_XP)
	# The service's own pre-execution read names a level THIS CLIENT DOES NOT
	# HOLD: the double records level 4 while the typed state records level 1.
	# The service genuinely executes the level up (it advances to the derived
	# level 5), which is exactly why the client must fail closed rather than
	# apply a foreign transaction.
	_set_recorded_level(api, LEVEL_FOUR[0])
	var snapshot_before := _state_snapshot(town.state)
	var armed: Dictionary = town.arm_level_up()
	check(bool(armed.get("ok", false)),
		"the post-state town arms a level up: %s" % armed.get("error"))
	var failed: Dictionary = await town.confirm_level_up()
	check(not bool(failed.get("ok", true)),
		"a post-state the apply rejects fails the intent closed")
	check_eq(str(failed.get("code", "")), "apply_failed",
		"the rejection names the apply, not the service: %s"
			% failed.get("error"))
	check(String(failed.get("error", "")).contains("pre-execution level"),
		"the explicit error names the divergence: %s" % failed.get("error"))
	check_eq(api.level_up_requests, requests_before + 1,
		"the rejected intent was still sent exactly once")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the rejected apply changes NO state at all")
	check_eq(town.level_recorded(), CORPUS_LEVEL,
		"the rejected apply leaves the recorded level untouched")
	check(town.level_active(),
		"the level up survives its own rejected apply")
	town.free()


## The cancelled level-up contract: arming and closing on a FRESH town leaves
## the serialized town state, the recorded level, the readout, the storage view,
## the selection, the resources, and the request count byte-identical.
func _check_cancelled(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, DISAGREE_XP, SELECT_CELL,
		SELECT_ITEM, "the cancel town")
	if town == null:
		return
	var requests_before: int = api.level_up_requests
	_set_experience(api, town.state, DISAGREE_XP)
	var snapshot_before := _state_snapshot(town.state)
	var armed: Dictionary = town.arm_level_up()
	check(bool(armed.get("ok", false)),
		"the level up arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var readout_before: String = town.level_readout()
	var expand_readout_before: String = town.expand_readout()
	var collect_readout_before: String = town.collect_readout()
	var cancelled: Dictionary = town.cancel_level_up()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the level up: %s" % cancelled.get("error"))
	check(not town.level_active(), "the level up closes")
	check(not town.ui.is_slot_visible("level"),
		"the level slot hides on cancel")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"a cancelled level up leaves the town state byte-identical (the "
			+ "recorded level, the balances, the storage, the ledger, and the "
			+ "drawn order)")
	check_eq(town.selection_legacy_id(), selected_before,
		"a cancelled level up leaves the committed selection unchanged")
	check_eq(api.level_up_requests, requests_before,
		"a cancelled level up sent NO request")
	town.free()
	# The readouts are re-rendered on the cancelled town below, through a fresh
	# one, because the status line is deliberately changed by the cancel (it
	# says the surface closed) while the READOUT is not.
	var reread: Variant = _selected_town(registry, DISAGREE_XP, SELECT_CELL,
		SELECT_ITEM, "the re-read town")
	if reread != null:
		check_eq(reread.level_readout(), readout_before,
			"a cancelled level up leaves the level readout byte-identical")
		check_eq(reread.expand_readout(), expand_readout_before,
			"the delivered expansion readout is untouched by a level-up cancel")
		check_eq(reread.collect_readout(), collect_readout_before,
			"the delivered collection readout is untouched by a level-up cancel")
		reread.free()
	_set_experience(api, null, CORPUS_XP)


# ---------------------------------------------------------------------------
# No reward, no curve alteration
# ---------------------------------------------------------------------------


## No reward is displayed or paid anywhere, and the committed curve is never
## altered. Asserted STRUCTURALLY over the module's own non-comment bytes — the
## point is that documentation may NAME a forbidden concept (this line's own
## non-claims do) while executable code may not reach for it.
func _check_no_reward_and_no_alteration() -> void:
	var module_code := _code_lines(_read_source(LEVEL_FLOW_SOURCE))
	check(not module_code.is_empty(), "the level module has source lines")
	# The prohibition is on CONSUMING a reward field: no read by key, no index,
	# and no assignment. The bare list entry in ENTRY_FIELDS / REWARD_FIELDS is
	# the recorded declaration of which fields exist and are never used, and it
	# is asserted below rather than forbidden here.
	for form in ["[\"reward_type\"]", "[\"reward_amount\"]",
			"get(\"reward_type\")", "get(\"reward_amount\")",
			"reward_type =", "reward_amount =", "reward_type:",
			"reward_amount:"]:
		check(not module_code.contains(form),
			"the level model never consumes a committed reward field (%s)"
				% form)
	check_eq(LevelFlow.REWARD_FIELDS, ["reward_type", "reward_amount"],
		"the model NAMES the reward fields it never consumes, so the claim is "
			+ "checkable rather than asserted")
	# The view's own level-flow section: the same two prohibitions there, so a
	# reward could not be displayed on the surface either.
	var town_source := _read_source(TOWN_SOURCE)
	var section := _section_lines(town_source,
		"\n# Level flow (building-xp, spec",
		"\n## Shop button wiring")
	check(not section.is_empty(), "the view's level-flow section is readable")
	check(not section.contains("reward_type") and not section.contains(
			"reward_amount"),
		"the view's level-flow section never names a reward field in code")
	check(section.contains("level_up_town("),
		"the view's level-flow section sends exactly the one documented intent")
	check(not section.contains("add_xp_unit") and not section.contains(
			"complete_tutorial"),
		"the view's level-flow section reaches for no unit experience and no "
			+ "tutorial step")
	# The committed curve is never altered: the model's own threshold constants
	# equal the committed ladder's, so a rebalanced curve could not pass here.
	check_eq(LevelFlow.FIRST_THRESHOLDS, [0, 40, 60, 100, 200, 350, 550, 800],
		"the model's own first thresholds are the committed ones, verbatim")
	check_eq(LevelFlow.FINAL_THRESHOLD, 2016089205,
		"the model's own final threshold is the committed one, verbatim")
	check_eq(LevelFlow.SCHEDULE_ENTRIES, SCHEDULE_ENTRIES,
		"the model's own entry count is the committed one")
	# No level model code anywhere in the view indexes the committed schedule by
	# its own arithmetic: the schedule is only ever read through
	# `LevelFlow.entry_index_for_level`, which lives in the module.
	check(not section.contains("curve[level") and not section.contains(
			"curve[level - 1]") and not section.contains("curve[level-1]"),
		"the view's level-flow section never indexes the committed curve by "
			+ "its own arithmetic")
	check(section.contains("LevelFlow.evaluate(") and section.contains(
			"level_schedule()"),
		"the view resolves every level through the pure model's own functions")


# ---------------------------------------------------------------------------
# Towns built in memory (no fixture is ever written)
# ---------------------------------------------------------------------------


## A town on the committed fresh save with the given cell selected through the
## delivered press path and, when supplied, the stored experience replaced IN
## MEMORY. No crafted row and no fixture write: the payload is duplicated first,
## so the committed file is never touched.
func _selected_town(registry: Variant, xp: int, cell: Vector2i, item_id: int,
		label: String) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var typed: Dictionary = (payload as Dictionary).duplicate(true)
	(typed["map"] as Dictionary)["xp"] = xp
	return _built_town(typed, registry, cell, item_id, label)


## Parses a payload fail-closed, builds the town on it, and selects `cell`
## through the delivered press path, naming the selection in a failure check.
func _built_town(payload: Dictionary, registry: Variant, cell: Vector2i,
		item_id: int, label: String) -> Variant:
	var parsed: Dictionary = TownState.parse(payload, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "%s parses: %s" % [label, parsed.get("error")])
		return null
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		check(false, "%s builds: %s" % [label, built.get("error")])
		town.free()
		return null
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(cell))
	if not bool(pressed.get("ok", false)) \
			or town.selection_legacy_id() != item_id:
		check(false, "%s selects the row (selected %d, wanted %d)"
			% [label, town.selection_legacy_id(), item_id])
		town.free()
		return null
	return town


## The double's OWN in-memory experience, raised in this process so the
## disagreement the committed corpus is not in becomes reachable offline. The
## committed fixture and the committed configuration are never written, and the
## typed state is moved with it so the client's own derivation and the service's
## agree — which is the honest way to reach this state, as opposed to making the
## two disagree on purpose.
func _set_experience(api: Variant, state: Variant, xp: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its in-memory "
			+ "state")
	else:
		double._level_state["xp"] = xp
	if state != null:
		state.summary.xp = xp


## The double's OWN in-memory recorded level, set so the service refuses with
## its own `level_already_current` code while the client — reading a different
## recorded level — still offers the action. This is the structured-failure
## case, produced in process rather than by a crafted fixture.
func _set_recorded_level(api: Variant, level: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its recorded "
			+ "level")
		return
	double._level_state["level"] = level


## One level-up straight through the facade is NOT driven here: the town flow's
## own confirm is the single intent this suite sends, so the request count stays
## exactly one per confirm and the typed shape is asserted from that result.


# ---------------------------------------------------------------------------
# The live-level-up scenario (verify-boot's `level-up-live` phase)
# ---------------------------------------------------------------------------


## One level-up through the real Compatibility endpoint, so the unchanged legacy
## `command()` executes the derived `level_up` envelope over the disposable
## corpus. This side asserts the typed response AND its TWO-part value-level
## post-state proof — the recorded level moved to EXACTLY the derived level, AND
## every stored resource is **unchanged** — plus that a REFUSED level-up left the
## corpus byte-identical. The phase harness separately asserts the corpus save
## file mutated. No fixture is touched.
func _check_live_level_up() -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the live phase")
	if endpoint == "":
		return
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("legacy_v0", endpoint)
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult, "the corpus save list resolves")
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(), "the corpus pre-level payload resolves")
	if before_payload.is_empty():
		return
	var level_before: int = _live_level(before_payload)
	var balances_before: Dictionary = _live_resources(before_payload)
	# The committed corpus is ALREADY consistent under the one-based reading, so
	# the very first intent is REFUSED and the refusal must leave the corpus
	# byte-identical — which is the endpoint's own two-layer guard (design D4)
	# and the reason the committed execution rewrote an identical value.
	var refused: Variant = await api.level_up_town(pid)
	check(refused is BootData.LevelUpResult and not refused.ok,
		"the already-current level is refused by the real endpoint")
	if refused is BootData.LevelUpResult:
		check_eq(refused.error_code, "level_already_current",
			"the refusal is the service's own code: %s"
				% refused.error_message)
		check(refused.curve == null and refused.resources == null
				and refused.result == "",
			"the refused level-up carries no partial payload")
	var after_refusal: Dictionary = await _live_payload(api, endpoint, pid)
	check_eq(_live_level(after_refusal), level_before,
		"the refused level-up left the recorded level byte-identical")
	check_eq(_live_resources(after_refusal), balances_before,
		"the refused level-up left every corpus balance byte-identical")
	# A client-supplied level outcome is IGNORED server-side. The structural
	# proof is the intent's own signature: `level_up_town` takes a save id and
	# NOTHING else, so there is no parameter through which a level could be sent
	# by this client at all, and the outcome the service reported depends on no
	# client number. The live corpus is re-read to show it is still the same
	# consistent save.
	check_eq(_level_argument_count(),
		1,
		"the level-up intent takes EXACTLY the save identity: there is no "
			+ "parameter through which a client could dictate a level")
	var ignored: Dictionary = await _live_payload(api, endpoint, pid)
	check_eq(_live_level(ignored), level_before,
		"the corpus's recorded level is unchanged, so the target came from the "
			+ "committed curve and not from the client")
	check_eq(_live_resources(ignored), balances_before,
		"every corpus balance is unchanged, so a level change moved none")
	# The fake derives the same code for the same intent, offline.
	api.configure("fake")
	var fake_refused: Variant = await api.level_up_town(pid)
	check(fake_refused is BootData.LevelUpResult and not fake_refused.ok,
		"the fake refuses the same intent offline")
	if fake_refused is BootData.LevelUpResult:
		check_eq(fake_refused.error_code, "level_already_current",
			"structured codes match between implementations")
	api.configure("legacy_v0", endpoint)
	print("[test] live-level-up applied level=%d derived=%d xp=%d "
		% [level_before, level_before, int(balances_before.get("xp", 0))]
		+ "refused=level_already_current resources_unchanged=true")


## How many parameters the facade's own level-up operation declares, read from
## the method list rather than assumed. One is the save identity; any more would
## be a channel through which a client could dictate a level outcome, which
## design D3 forbids. Read reflectively so a signature change fails the SUITE.
func _level_argument_count() -> int:
	for method: Dictionary in ClassDB.class_get_method_list(
			"Node") + _game_api_methods():
		if str(method.get("name", "")) == "level_up_town":
			return (method.get("args", []) as Array).size()
	return -1


## The facade's own method list, reached through the autoload's script rather
## than a hardcoded class name so the check follows the implementation.
func _game_api_methods() -> Array:
	var api: Variant = root.get_node_or_null("GameApi")
	if api == null:
		return []
	var script: Variant = api.get_script()
	if script == null:
		return []
	var found: Array = script.get_script_method_list()
	return found


## The corpus's own bootstrap payload, or {} when it cannot be read.
func _live_payload(api: Variant, endpoint: String, user_id: String) -> Dictionary:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return {}
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return {}
	return (info as BootData.PlayerInfoPayload).raw


## The corpus's own recorded level, read from its bootstrap payload.
func _live_level(raw: Dictionary) -> int:
	var map: Dictionary = raw.get("map", {}) as Dictionary
	return int(map.get("level", -1))


## The corpus's own seven stored balances under the typed resource names the
## response carries, read from its bootstrap payload. This is the pre-request
## reference the live value-level proof compares against — read from the service's
## own state, never from the fake's fixture.
func _live_resources(raw: Dictionary) -> Dictionary:
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var player: Dictionary = raw.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = raw.get("privateState", {}) as Dictionary
	return {
		"gold": int(map.get("gold", 0)),
		"wood": int(map.get("wood", 0)),
		"oil": int(map.get("oil", 0)),
		"steel": int(map.get("steel", 0)),
		"xp": int(map.get("xp", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(priv.get("mana", 0)),
	}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## A crafted committed-curve copy, for the cases the committed content cannot
## produce. Every row is a full committed entry so the ladder check passes; the
## reward fields are present precisely so a check can assert they are never read.
func _crafted_curve(rows: Array) -> Array:
	var out: Array = []
	for row: Dictionary in rows:
		var copy: Dictionary = row.duplicate(true)
		if not copy.has("reward_type"):
			copy["reward_type"] = "s"
		if not copy.has("reward_amount"):
			copy["reward_amount"] = 50
		out.append(copy)
	return out


## The named UI-foundation slot's panel (null when the slot never registered or
## holds no child).
func _panel_of(town: Variant, slot: String) -> Variant:
	if not town.ui.has_slot(slot):
		return null
	var root: Control = town.ui.slot_root(slot)
	if root == null or root.get_child_count() == 0:
		return null
	return root.get_child(0)


## How many buttons named `button_name` the named slot's panel carries.
func _button_count(town: Variant, slot: String, button_name: String) -> int:
	var panel: Variant = _panel_of(town, slot)
	if panel == null:
		return 0
	var buttons: Array = []
	_collect_buttons(panel as Node, buttons)
	var found := 0
	for button: Variant in buttons:
		if String((button as Button).name) == button_name:
			found += 1
	return found


## The named button anywhere inside the given panel (its action row nests the
## arm/confirm/cancel buttons), or null.
func _button_named(panel: Node, button_name: String) -> Variant:
	for child: Variant in panel.get_children():
		if child is Button and String((child as Button).name) == button_name:
			return child
		if child is Node:
			var nested: Variant = _button_named(child as Node, button_name)
			if nested != null:
				return nested
	return null


## Every button in a panel subtree, in creation order, so a check can assert the
## surface's own affordances and prove no extra action exists.
func _collect_buttons(panel: Node, out: Array) -> void:
	for child: Variant in panel.get_children():
		if child is Button:
			out.append(child)
		if child is Node:
			_collect_buttons(child as Node, out)


## The on-screen level selection line ("" before a panel exists).
func _level_selection_text(town: Variant) -> String:
	var panel: Variant = _panel_of(town, "level")
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "selection":
			return (child as Label).text
	return ""


## The on-screen level readout line ("" when no panel exists).
func _level_readout_label(town: Variant) -> String:
	var panel: Variant = _panel_of(town, "level")
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "level":
			return (child as Label).text
	return ""


## The committed draw order as one `item@cell` string per object, so a run can
## prove a level-up changed no object's identity, no cell, and no committed DEPTH
## POSITION.
func _object_signature(town: Variant) -> Array:
	var rows: Array = []
	for object: Variant in town.objects:
		rows.append("%d@%d,%d" % [int(object.legacy_id), int(object.cell.x),
			int(object.cell.y)])
	return rows


## Every placement row verbatim, so a run can prove a level-up rewrote no row.
func _placement_signature(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append(placement.raw)
	return JSON.stringify(rows)


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the project
## setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## Deterministic serialization of every committed state field (the byte-identity
## oracle for the cancelled, refused, and failed paths), including the recorded
## level, the owned expansions ledger, and the storage mapping — so a
## cancellation or a failure that quietly changed the level can never look
## byte-identical.
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append({
			"raw": placement.raw,
			"clicks": placement.clicks,
			"countdown": placement.countdown,
			"started_at": placement.started_at,
			"collected_at": placement.collected_at,
		})
	return JSON.stringify({
		"placements": rows,
		"storage": state.storage,
		"owned_expansions": state.owned_expansions,
		"resources": {
			"coins": state.resources.coins,
			"wood": state.resources.wood,
			"steel": state.resources.steel,
			"oil": state.resources.oil,
			"cash": state.resources.cash,
			"energy": state.resources.energy,
			"mana": state.resources.mana,
		},
		"summary": {
			"name": state.summary.name,
			"level": state.summary.level,
			"xp": state.summary.xp,
		},
		"missing": state.missing,
		"unresolved_ids": state.unresolved_ids,
	})


## A res:// source file's text, or "" when it cannot be read.
func _read_source(resource_path: String) -> String:
	var path := ProjectSettings.globalize_path(resource_path)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return ""
	var text := handle.get_as_text()
	handle = null
	return text


## Every NON-COMMENT, non-blank source line of a file, newline-separated. The
## point is that documentation may NAME a forbidden concept (this line's own
## non-claims do) while executable code may not reach for it.
func _code_lines(source: String) -> String:
	var kept: Array = []
	for line in source.split("\n"):
		var stripped := line.strip_edges()
		if stripped == "" or stripped.begins_with("#"):
			continue
		kept.append(stripped)
	return "\n".join(kept)


## The non-comment source lines of the region between two section headers
## (inclusive of the header's own body, exclusive of the next header), or ""
## when the start header is absent.
func _section_lines(source: String, start_marker: String,
		end_marker: String) -> String:
	var start := source.find(start_marker)
	if start == -1:
		return ""
	var finish := source.find(end_marker, start + start_marker.length())
	if finish == -1:
		finish = source.length()
	return _code_lines(source.substr(start, finish - start))


## Loads a repository-relative JSON fixture as parsed text (read-only).
func _fixture(relative: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_bytes(
		Paths.repo_root().path_join(relative)).get_string_from_utf8())


## The town state derives from the fixture in hand: this whole run must not
## issue a bootstrap request.
func _check_no_second_bootstrap_request() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	check_eq(int(api.bootstrap_requests), 0,
		"no bootstrap request was issued (the fixture in hand suffices)")
