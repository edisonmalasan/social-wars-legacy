extends RefCounted
## Darts and premium state projection for OpenSpec `godot-darts`.
##
## ## What this line is, and is not
##
## This module projects the darts state a committed save actually carries, and
## holds the two fields `godot-social-state` measured and found NOT to be social:
## `timeStampEndPremium` (a paid-purchase instant with a **server-derived**
## value) and `crossPromotionsFinished` (a cross-promotion flag).
##
## It is emphatically **not** a claim that darts is a playable feature, that a
## balloon may be shot at a player, or that a premium entitlement exists to be
## displayed. The preserved server has three darts branches whose every input is
## client-sent; what it does **not** have is anything that verifies a shot, a
## target, or a purchase. Whether the Flash client presented a darts table or a
## premium-buy screen is **unverifiable from the preserved oracle** and is not
## claimed either way.
##
## ## The corpus denominator is 33, and that is a correction (C3)
##
## The committed investigation `docs/legacy-m11-darts.md` §5 measured this corpus
## as **231** documents. Two hundred of those were generated `tests/fixtures/**`
## files -- the `before.json`/`after.json` pairs that executed-legacy captures
## produce -- each a derived copy of a canonical save recording both sides of one
## transaction. The denominator was inflated roughly sevenfold; see §0b C3 of that
## document.
##
## The canonical corpus is the definition the sibling `godot-social-state` suite
## already uses: `tests/saves` + `villages`, excluding `tests/saves/manifest.json`,
## counting a document that carries at least one map. That is **33** documents, and
## all 33 carry a map. Every distinct-value count in §5 reproduces exactly
## (15, 15, 21, 2, 4, 1, 2); only the multiplicities were wrong, because fixtures
## are copies and add no new values. `EXPECTED_CORPUS` below pins 33 and the suite
## re-derives it, so this class of drift fails the run instead of rotting.
##
## ## The committed corpus never records a won shot (C4)
##
## `dartsGotExtra` is `false` in **33 of 33** documents, and all three documents
## carrying a non-empty shot list record **losing** shots. So the corpus contains
## no document in which the client-dictated `won_extra` ever set the flag. The
## refusal of that value is therefore recorded as having **no corpus evidence in
## either direction** -- not as a case where the corpus shows the legacy behaviour
## working, and not as one where it shows it misfiring. A reader should not have to
## rediscover that, because the natural reading of "darts is played" suggests the
## opposite.
##
## ## An absent field is ABSENT, never defaulted
##
## All 33 canonical documents carry all six darts fields, so a missing key means a
## document shape this capability has never observed. Every accessor therefore
## reports absence and never substitutes that field's recorded uniform value.
## Folding "absent" into "empty" would hide precisely the case worth seeing.

## The six darts state fields, in the investigation's order.
##
## `store` is the recorded storage location. `recorded_values` is the measured
## distribution over the canonical 33-document corpus, keyed by the JSON form of
## the value. `distinct` is how many distinct values the corpus holds, and
## `documents` how many documents carry the field at all.
##
## Declared as Dictionaries so the table stays a plain constant the suite can
## compare directly, matching `social_state.gd`'s `FIELDS` convention.
const DARTS_FIELDS := [
	{
		"name": "dartsRandomSeed", "store": "privateState",
		"distinct": 15, "documents": 33,
		"recorded_values": {
			"2366": 10, "0": 5, "4555": 3, "2137": 3, "2184": 2,
			"23340": 1, "3595": 1, "4627": 1, "9709": 1, "8704": 1,
			"2900": 1, "8538": 1, "9919": 1, "7018": 1, "7808": 1,
		},
		"written_by": ["darts_reset"],
		"readers": [],
		"client_sent": true,
		"note": "written from client args[0] by darts_reset and read by NO "
			+ "branch; no semantics are derived from it anywhere (design D10)",
	},
	{
		"name": "dartsBalloonsShot", "store": "privateState",
		"distinct": 4, "documents": 33,
		"recorded_values": {"[]": 30, "[18,17]": 1, "[0]": 1, "[18]": 1},
		"written_by": ["darts_reset", "darts_shoot_balloon"],
		"readers": [],
		"client_sent": true,
		"note": "the ONLY played list in the corpus; 30 of 33 documents hold [] "
			+ "and the three that do not are named in OUT_OF_SCHEDULE_SHOTS",
	},
	{
		"name": "dartsGotExtra", "store": "privateState",
		"distinct": 1, "documents": 33,
		"recorded_values": {"false": 33},
		"written_by": ["darts_shoot_balloon"],
		"readers": [],
		"client_sent": true,
		"note": "UNIFORMLY false in 33 of 33 documents, so the corpus records no "
			+ "won shot at all; the client-dictated write is refused and has no "
			+ "corpus evidence either way (C4)",
	},
	{
		"name": "dartsHasFree", "store": "privateState",
		"distinct": 2, "documents": 33,
		"recorded_values": {"true": 26, "false": 7},
		"written_by": ["darts_reset", "darts_new_free", "darts_shoot_balloon"],
		"readers": [],
		"client_sent": false,
		"note": "true in 26 of 33 documents, yet NO branch reads it to decide "
			+ "anything, so no eligibility rule is derived from it",
	},
	{
		"name": "timeStampDartsReset", "store": "privateState",
		"distinct": 15, "documents": 33,
		"recorded_values": {
			"1672677498": 10, "0": 5, "1672069701": 3, "1671881466": 3,
			"1672167906": 2, "1705671822": 1, "1705940140": 1, "1705775953": 1,
			"1705795645": 1, "1688698313": 1, "1672159213": 1, "1703527908": 1,
			"1703527723": 1, "1703544899": 1, "1704755505": 1,
		},
		"written_by": ["darts_reset", "sessions.create_player", "reset_stuff"],
		"readers": ["reset_stuff"],
		"client_sent": false,
		"note": "the ONLY time-derived darts mutation; reset_stuff writes it to "
			+ "0, never to the server clock (design D5)",
	},
	{
		"name": "timeStampDartsNewFree", "store": "privateState",
		"distinct": 21, "documents": 33,
		"recorded_values": {
			"0": 5, "1672763991": 3, "1672839826": 3, "1672875500": 3,
			"1672098185": 2, "1671967335": 2, "1705744789": 1, "1705940140": 1,
			"1705775972": 1, "1705795645": 1, "1688927899": 1, "1672159213": 1,
			"1672069701": 1, "1671867066": 1, "1672167906": 1, "1672250740": 1,
			"1672677498": 1, "1703527908": 1, "1703527723": 1, "1703557046": 1,
			"1704761785": 1,
		},
		"written_by": ["darts_reset", "darts_new_free", "darts_shoot_balloon"],
		"readers": [],
		"client_sent": false,
		"note": "stamped by three branches and read by none, so no availability "
			+ "window is derived from it",
	},
]

## The two fields HANDED to this capability by `godot-social-state`.
##
## That capability measured nineteen social fields and delivered them all; these
## two are not social. `timeStampEndPremium` was recorded there as "a single
## instant write" by a client-sent branch, which is wrong twice: `command.py:612-623`
## writes it **twice** (`:619` set arm, `:622` extend arm) with a **server-derived**
## value. `crossPromotionsFinished` is a cross-promotion flag.
##
## Both remain MEASURED in `godot-social-state` -- its census is about occurrence,
## and re-filing ownership must not change a census result -- so the correction is
## a hand-off, not a deletion. `test_social_state.gd::_check_handoff` verifies this
## module exists and really carries both names, so the hand-off cannot rot into an
## orphan.
const HANDED_FIELDS := [
	{
		"name": "timeStampEndPremium", "store": "privateState",
		"distinct": 2, "documents": 33,
		"recorded_values": {"0": 32, "1682945878": 1},
		"written_by": ["buy_premium_account"],
		"readers": ["buy_premium_account"],
		"client_sent": false,
		"note": "ONE document of 33 records a live instant (villages/Neutral.json, "
			+ "1682945878 = 2023-05-01 12:57:58 UTC, in the past); the branch reads "
			+ "it and writes it twice from a committed schedule",
	},
	{
		"name": "crossPromotionsFinished", "store": "privateState",
		"distinct": 1, "documents": 33,
		"recorded_values": {"[]": 33},
		"written_by": [], "readers": [],
		"client_sent": false,
		"note": "uniformly empty and never touched by any of the eleven legacy "
			+ "modules; reported as an inert event-system flag, not as social state",
	},
]

## There is NO premium flag -- only an instant (investigation B3).
##
## Measured over all 33 canonical documents: `premiumAccount` appears in **zero**
## of them. So nothing records whether a player IS premium; the only evidence is
## the instant, and a premium account that has expired is indistinguishable from
## one never bought. No boolean is derived from the instant, because deriving one
## would invent a state the save does not carry.
const PREMIUM_FLAG_ABSENT := {
	"flag_name": "premiumAccount",
	"documents_carrying": 0,
	"documents_measured": 33,
	"boolean_derived": false,
	"note": "there is no premium flag in any committed document; only the "
		+ "instant exists, so an expired premium is indistinguishable from none",
}

## The committed darts schedule's id range, read but never used to validate.
##
## `darts_items` is owned by `darts-schedule-normalization`; this capability reads
## it to REPORT the absence of a membership test and never to enforce one. The
## range is recorded so the corpus fact below is checkable rather than asserted.
const SCHEDULE_RANGE := {"owner": "darts-schedule-normalization", "first": 1, "last": 27}

## The three corpus documents that carry a non-empty shot list, by name.
##
## `villages/Nerri.json` records `[0]`, and `0` is NOT among the committed ids
## `1..27` -- so the preserved server accepted a shot absent from the schedule.
## That single document is the evidence that the missing membership test is not
## merely unimplemented but demonstrably **not enforced**, which is why no
## membership rule is invented here (design D4).
const OUT_OF_SCHEDULE_SHOTS := [
	{"document": "villages/AcidCaos.json", "shots": [18, 17], "outside_schedule": []},
	{"document": "villages/Nerri.json", "shots": [0], "outside_schedule": [0]},
	{"document": "villages/Scarlet.json", "shots": [18], "outside_schedule": []},
]

## The one document recording a live premium instant, named rather than counted.
const LIVE_PREMIUM_DOCUMENT := {
	"document": "villages/Neutral.json",
	"instant": 1682945878,
	"elapsed": true,
	"extend_arm_reachable": false,
	"note": "every committed instant has PASSED, so the extend arm of "
		+ "buy_premium_account is unreachable in the corpus and any coverage of "
		+ "it is crafted input, never corpus evidence",
}

## The canonical corpus, pinned and re-derived on every run.
const EXPECTED_CORPUS := {
	"roots": ["tests/saves", "villages"],
	"exclude": ["tests/saves/manifest.json"],
	"documents": 33,
	"village_documents": 31,
	"save_documents": 2,
	"carrying_rule": "a document that carries at least one map",
}

## Why the canonical fresh-player document cannot exercise this surface.
##
## It carries every darts field at its initial value and `timeStampEndPremium` at
## `0`, so it cannot exercise the shoot arm, the free arm, or either premium arm.
## Any coverage of those arms over it is CRAFTED INPUT and is reported as such.
## This is why no executed-legacy fixture is claimed for this line.
const FRESH_PLAYER_LIMIT := {
	"document": "tests/saves/fresh-player.json",
	"dartsRandomSeed": 0,
	"dartsBalloonsShot": [],
	"dartsGotExtra": false,
	"dartsHasFree": false,
	"timeStampDartsReset": 0,
	"timeStampDartsNewFree": 0,
	"timeStampEndPremium": 0,
	"crossPromotionsFinished": [],
	"shoot_arm_reachable": false,
	"free_arm_reachable": false,
	"premium_arm_reachable": false,
	"coverage_kind": "crafted input only",
}

## Every helper this module therefore does not provide (design D5/D9).
##
## Matched case-insensitively and by SUBSTRING, because an exact-name check was
## measured in this project to miss a suffixed helper wearing a reserved name.
## `absent_because` records the measured reason for each, so the inventory cannot
## be padded with a name nobody can justify.
const ABSENT_HELPERS := [
	{"helper": "darts_charge", "absent_because":
		"the committed PREMIUM_ACCOUNTS price has zero consumers across all "
		+ "eleven legacy modules, so premium is bought for free"},
	{"helper": "premium_price", "absent_because":
		"no legacy module reads the committed price beside any committed duration"},
	{"helper": "shot_limit", "absent_because":
		"darts_shoot_balloon appends with no length bound and none is invented"},
	{"helper": "max_shots", "absent_because":
		"no committed bound on the balloon list exists to reproduce"},
	{"helper": "in_schedule", "absent_because":
		"no membership test exists, and villages/Nerri.json records an accepted "
		+ "out-of-schedule shot, so adding one would contradict the corpus"},
	{"helper": "verify_win", "absent_because":
		"nothing in the eleven modules checks whether a shot was winnable"},
	{"helper": "target_exists", "absent_because":
		"the schedule is read to report its absence as a check, never consulted "
		+ "for existence"},
	{"helper": "client_duration", "absent_because":
		"the duration is derived from the committed schedule; no client value "
		+ "reaches it"},
	{"helper": "darts_seed_order", "absent_because":
		"the seed is written and read by no branch, so no ordering is derived"},
	{"helper": "darts_eligibility", "absent_because":
		"dartsHasFree is read by nothing, so no availability rule is derived"},
	{"helper": "free_window", "absent_because":
		"timeStampDartsNewFree is stamped by three branches and read by none"},
	{"helper": "weekday_of", "absent_because":
		"reset_stuff's offset comment mentions Thursday and Monday, but no "
		+ "weekday is computed anywhere in the preserved server"},
	{"helper": "premium_entitlement", "absent_because":
		"no committed document carries a premium flag, so no entitlement state "
		+ "exists to derive"},
	{"helper": "darts_score", "absent_because":
		"dartsGotExtra is the only outcome flag and it is refused; no score is "
		+ "kept or ranked"},
	{"helper": "darts_ui", "absent_because":
		"nothing is rendered; whether the Flash client showed darts is "
		+ "unverifiable from the preserved oracle"},
]


## Every projected field name -- the six darts fields plus the two handed ones.
static func field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in DARTS_FIELDS:
		out.append(str(entry["name"]))
	for entry: Dictionary in HANDED_FIELDS:
		out.append(str(entry["name"]))
	return out


## Just the six darts state fields, excluding the handed ones.
static func darts_field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in DARTS_FIELDS:
		out.append(str(entry["name"]))
	return out


## One field's record, or `null` when the name was not projected.
##
## Returns `null` rather than a synthesized entry, so an unmeasured name cannot
## be mistaken for a measured one.
static func field_record(field_name: String) -> Variant:
	for entry: Dictionary in DARTS_FIELDS:
		if str(entry["name"]) == field_name:
			return entry
	for entry: Dictionary in HANDED_FIELDS:
		if str(entry["name"]) == field_name:
			return entry
	return null


## The recorded distinct-value count for a field, or `-1` when not projected.
static func distinct_values_of(field_name: String) -> int:
	var record: Variant = field_record(field_name)
	if record == null:
		return -1
	return int((record as Dictionary).get("distinct", -1))


## The recorded value distribution for a field, or `{}` when not projected.
static func recorded_values_of(field_name: String) -> Dictionary:
	var record: Variant = field_record(field_name)
	if record == null:
		return {}
	return ((record as Dictionary).get("recorded_values", {}) as Dictionary).duplicate()


## Whether a projected field's value is client-sent by the preserved branch.
static func is_client_sent(field_name: String) -> bool:
	var record: Variant = field_record(field_name)
	if record == null:
		return false
	return bool((record as Dictionary).get("client_sent", false))


## Project a committed save document.
static func project(document: Variant = null) -> DartsProjection:
	return DartsProjection.new(document)


## The read-only projection over one committed save document.
##
## Named `DartsProjection`, NOT `Projection`: the sibling `godot-social-state`
## module had to rename its inner class away from `Projection` because it is a
## built-in Godot type, and an inner class sharing a preloaded script's name makes
## every static call resolve to the inner class (design D2).
class DartsProjection extends RefCounted:
	var _present: Dictionary = {}

	func _init(document: Variant = null) -> void:
		if typeof(document) != TYPE_DICTIONARY:
			return
		var source: Dictionary = document
		var containers: Array = []
		var private_state: Variant = source.get("privateState", null)
		if typeof(private_state) == TYPE_DICTIONARY:
			containers.append(private_state)
		var maps: Variant = source.get("maps", null)
		if typeof(maps) == TYPE_ARRAY:
			for map_object: Variant in maps:
				if typeof(map_object) == TYPE_DICTIONARY:
					containers.append(map_object)
		elif typeof(maps) == TYPE_DICTIONARY:
			var keys: Array = (maps as Dictionary).keys()
			keys.sort()
			for key: Variant in keys:
				var map_object: Variant = (maps as Dictionary)[key]
				if typeof(map_object) == TYPE_DICTIONARY:
					containers.append(map_object)
		for name: String in _projected_names():
			for container: Variant in containers:
				if (container as Dictionary).has(name):
					_present[name] = (container as Dictionary)[name]
					break

	## The projected names, collected from the two const tables in THIS script.
	##
	## Inlined rather than delegated to the outer script's static `field_names()`:
	## GDScript does not resolve an outer script's own static by bare name from
	## inside an inner class, so `DartsState.field_names()` fails to COMPILE with
	## "Identifier DartsState not declared in the current scope". The sibling
	## `godot-social-state` module records the same trap in `field()`. The const
	## tables themselves ARE reachable from the inner class, so both tables are
	## read here and cannot drift from `field_names()`.
	func _projected_names() -> Array:
		var out: Array = []
		for entry: Dictionary in DARTS_FIELDS:
			out.append(str(entry["name"]))
		for entry: Dictionary in HANDED_FIELDS:
			out.append(str(entry["name"]))
		return out

	## True when the document actually carried the key. An absent key reports
	## false, which is what keeps it distinct from a recorded `false` or `0`.
	func present(field_name: String) -> bool:
		return _present.has(field_name)

	## The recorded value, or `null` when absent.
	##
	## An absent field and a field recorded as `null` or `false` are distinguished
	## by `present()`; this accessor alone cannot tell them apart, by design.
	func value(field_name: String) -> Variant:
		return _present.get(field_name, null)

	## True when the recorded shot list is a non-empty array.
	##
	## Deliberately reports only SHAPE. It answers "did this document record any
	## shot", never "is this shot in the schedule" -- the second question has no
	## answer in the preserved server and inventing one is exactly what this line
	## refuses (design D4).
	func has_recorded_shots() -> bool:
		var shots: Variant = value("dartsBalloonsShot")
		return shots is Array and not (shots as Array).is_empty()

	## True when the document records a premium instant later than `now`.
	##
	## This is a COMPARISON OF A RECORDED VALUE AGAINST A CLOCK, not a derivation
	## of any rule: it is the same comparison `buy_premium_account` performs to
	## choose its arm (`time_now >= ts_premium`). No entitlement is inferred from
	## the answer, and no boolean premium state is produced.
	func premium_instant_is_future(now: int) -> bool:
		if not present("timeStampEndPremium"):
			return false
		var instant: Variant = value("timeStampEndPremium")
		if typeof(instant) != TYPE_INT and typeof(instant) != TYPE_FLOAT:
			return false
		return int(instant) > int(now)

	## The projected fields this document actually carries, in projection order.
	func present_names() -> Array:
		var out: Array = []
		for name: String in _projected_names():
			if _present.has(name):
				out.append(name)
		return out

	## The projected fields this document does not carry. Reported, never defaulted.
	func absent_names() -> Array:
		var out: Array = []
		for name: String in _projected_names():
			if not _present.has(name):
				out.append(name)
		return out
