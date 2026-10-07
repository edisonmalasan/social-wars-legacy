extends RefCounted
## Socially-In-Construction assist-state projection for OpenSpec
## `godot-construction-assist`.
##
## ## What this line delivers, and what the finding is
##
## M11's `social rewards` deliver item is classified in `docs/legacy-m11-social.md`
## section 7 as **"Content committed, behaviour absent"**. That measurement is
## REPRODUCED and true of the three tables, and it is FALSE of the deliver item.
## The preserved server holds a social-assistance state machine that none of
## those tables mention: the map-row attribute-bag key `si`.
##
## **The token's expansion is not inferred.** `engine.py:19` states it verbatim:
##
##     # enable SI (Socially In Construction), because the game expects it
##
## The trailing clause is recorded rather than dropped. It is the author's own
## admission that the mechanism is a client-display concession rather than
## gameplay, and that is the single most informative sentence in the surface.
##
## ## The surface is the INVERSE of the deliver item's name
##
## The list records **who filled each assist slot**, and the only value any
## writer ever appends is the integer `0`. `engine.py:142` says so:
##
##     attr["si"].append(0) # 0 is for buying instead of hiring friends
##
## So the list records a **paid substitute for a friend**. The friend arm has
## **no writer anywhere**: zero occurrences of a non-`0` write path across all
## eleven legacy modules under six counting rules, corroborated by the committed
## corpus holding 7 elements totalling exactly ONE distinct value.
##
## ## A refused ability, not a decoded value
##
## No reward is granted, no resource is charged, no element is decoded, and the
## `0` sentinel's meaning is a QUOTED comment rather than a recovered encoding.
## The capability is named `godot-construction-assist` rather than
## `godot-social-rewards` on the same recorded reason that withheld
## `godot-friends`: naming a capability after a surface the measurement
## disproves would claim exactly what does not exist.
##
## ## No route, and that is a decision (design D1)
##
## `attr["si"]` already reaches the client: `town_state.gd` reads the row
## attribute bag from map-row slot 6 and carries the key through verbatim, so
## `/v0/bootstrap` serves it. A projection therefore needs no new transport, and
## `apps/compat-api/**` is untouched - which makes the compatibility suite's
## baseline a VERIFIED figure for this line rather than a skipped check.
##
## ## The committed gate is REFERENCED, not reimplemented (design D5, D6)
##
## `godot-stored-item-placement` derives the bag at placement from the committed
## `properties.friend_assistable` flag, and owns that derivation. This module
## reports the gate's recorded shape and never re-derives, normalizes or coerces
## it. The encoding matters: the normalized package stores `properties` flags as
## STRINGS, so a consumer comparing the value against an integer reads EVERY
## carrier as false.

## The map-row attribute-bag slot holding the row's attribute dictionary.
## `town_state.gd` reads it from the same slot.
const ATTR_BAG_SLOT := 6

## The recorded attribute-bag key. Named as the recorded token, not as an
## expansion of it - `TOKEN_EXPANSION_SOURCE` below carries the expansion.
const ATTR_ASSIST_KEY := "si"

## The quoted source line establishing the expansion, read from `engine.py:19`.
## Quoted rather than paraphrased, because the clause after the comma is the
## finding and a paraphrase would drop it.
const TOKEN_EXPANSION_SOURCE := \
	"# enable SI (Socially In Construction), because the game expects it"
const TOKEN_EXPANSION_FILE := "engine.py:19"
const TOKEN_EXPANSION := "Socially In Construction"

## The trailing clause, recorded separately so a reader cannot miss it by
## reading only the expansion.
const TOKEN_EXPANSION_CONCESSION := "because the game expects it"

## The ONLY value any writer ever appends, and the comment that fixes its
## meaning. The value is recorded; the meaning is quoted. Neither is decoded.
const SENTINEL_VALUE := 0
const SENTINEL_COMMENT_SOURCE := \
	"attr[\"si\"].append(0) # 0 is for buying instead of hiring friends"
const SENTINEL_COMMENT_FILE := "engine.py:142"

## The measured absence of the friend arm. Six counting rules over all eleven
## legacy modules; see `FRIEND_ARM_CONSUMERS` for the columns.
const FRIEND_ARM_RULES := [
	"whole-file occurrences",
	"whole-file distinct lines",
	"code-only occurrences",
	"code-only distinct lines",
	"exact identifier tokens",
	"quoted-access form",
]
const FRIEND_ARM_MODULES := 11
const FRIEND_ARM_CONSUMERS := [0, 0, 0, 0, 0, 0]
const LEGACY_MODULE_COUNT := 11

## The committed gate, reported verbatim and never reimplemented.
const GATE_FIELD := "friend_assistable"
const GATE_SOURCE := "properties.friend_assistable"
const GATE_CONSUMER_SITE := "engine.py:22-23"
const GATE_FLAG_STRING := "1"
const GATE_BUILDINGS_CARRIED := 26
const GATE_BUILDINGS_TOTAL := 470
const GATE_UNITS_CARRIED := 0
const GATE_UNITS_TOTAL := 429
const GATE_SPECIAL_CARRIED := 0
const GATE_SPECIAL_TOTAL := 1
const GATE_SPECIAL_FILE := "packages/game-content/normalized/specials.json"

## The three places the recorded key is created or removed, with the value each
## one writes. Recorded because the WRITTEN VALUE differs by writer, and that
## difference is what makes "absent" and "empty" different recorded states:
## `map_add_item` seeds an EMPTY list at placement, `buy_si_help` seeds `[ 0 ]`
## and then appends `0`, and `finish_si` deletes the key. A row therefore has no
## key only when it was never gated, never bought into, or was finished.
const BAG_WRITERS := [
	{"writer": "map_add_item", "site": "engine.py:24",
		"recorded_source": "attr[\"si\"] = []",
		"writes": "an empty list", "charges": false, "grants": false,
		"gate_checked": true},
	{"writer": "buy_si_help", "site": "engine.py:139-140, engine.py:142",
		"recorded_sources": ["attr[\"si\"] = [ 0 ]",
			"attr[\"si\"].append(0) # 0 is for buying instead of hiring friends"],
		"writes": "the integer 0", "charges": false, "grants": false,
		"gate_checked": false},
	{"writer": "finish_si", "site": "engine.py:147",
		"recorded_source": "del attr[\"si\"]",
		"writes": "nothing; the key is removed", "charges": false,
		"grants": false, "gate_checked": false},
]
const BAG_WRITER_COUNT := 3

## Why the string encoding is reported rather than assumed. The committed value is
## the STRING `"1"`, and it is read correctly in both places that read it: the
## legacy consumer wraps it in `int()` at `engine.py:23`, and the owning
## delivered derivation coerces it the same way through its own
## `_committed_int`. So this module records a hazard it does **not** introduce --
## a consumer comparing the raw value against an integer would read every carrier
## as false -- and names the owning capability as the place that coercion lives,
## rather than claiming a fault that is not present.
const GATE_ENCODING_NOTE := \
	"the normalized package stores properties flags as strings; both the "\
	+ "legacy int() at engine.py:23 and the owning delivered coercion read "\
	+ "the string correctly, while a consumer comparing the raw value against "\
	+ "an integer would read every carrier as false"

## The three refusals, each with a distinct code. Only shapes whose MEANING is
## unreadable are refused; an unexpected ELEMENT type is not among them, because
## element types are reported verbatim and inventing a type rule would refuse
## recorded data.
const REFUSAL_CODES := {
	"row_not_a_list": "the map row is not a list",
	"bag_slot_absent": "the row carries no attribute-bag slot",
	"bag_not_an_object": "the recorded attribute bag is not an object",
	"assist_value_not_a_list": "the recorded value of `si` is not a list",
}

## The recorded precondition of both dedicated dispatchers: only the addressed
## map slot must resolve. No flag, type or team check exists. Recorded, NOT
## enforced - enforcing the flag client-side would refuse two committed corpus
## rows, and the preserved branch has no such check.
const DISPATCH_PRECONDITION := \
	"the addressed map slot resolves to a row; no friend_assistable, type or " \
	+ "team check exists in either dedicated branch"
const DISPATCH_PRECONDITION_ENFORCED := false

## Ownership, asserted rather than assumed, so a rename on either side fails.
const OWNERSHIP := {
	"gate_derivation": {
		"owner": "godot-stored-item-placement",
		"owns": "the attribute-bag derivation at placement",
		"here": "referenced, never reimplemented",
	},
	"state_fields": {
		"owner": "godot-social-state",
		"owns": "the persisted social state fields and the recorded instant "
			+ "stamp at command.py:643",
		"here": "named as owner, not re-recorded",
	},
	"content_tables": {
		"owner": "social-tables-normalization",
		"owns": "neighbor_assists, findable_items and social_items",
		"here": "uniformity census only; NO content row is projected",
	},
	"gift_census": {
		"owner": "godot-unit-behaviors",
		"owns": "the units-only gift_level census row",
		"here": "completed with the buildings side, plus a giftable row",
	},
}

## The reward-schedule uniformity census. This is a CENSUS, not a projection:
## it states that each schedule holds exactly one distinct value, which is the
## reason nothing here decodes a reward - a schedule carrying a single value
## cannot distinguish a rule from a constant. It names no entry, no id and no
## display string, because the owning capability projects those rows.
const REWARD_CENSUS := [
	{"table": "neighbor_assists", "field": "reward", "entries": 5,
		"distinct_values": 1, "decoded": false},
	{"table": "findable_items", "field": "coins", "entries": 10,
		"distinct_values": 1, "decoded": false},
]

## Two further committed fields with zero legacy consumers. NO ORDINAL is
## claimed for either: earlier lines named successive discoveries "the sixth",
## "the seventh", "the ninth" and "the tenth", each over a DIFFERENT scope, and
## no single reconciled census of zero-consumer committed fields exists in this
## repository. Assigning a number here would repeat the defect
## `godot-unit-behaviors` was corrected for.
const GIFT_FIELDS := [
	{"field": "giftable", "consumers": [0, 0, 0, 0, 0, 0],
		"carried_on": "470 buildings + 429 units + 1 special",
		"recorded_type": "int", "distribution":
			"1 on 20 buildings and 10 units",
		"already_in_a_census": false,
		"note": "in NO census in this repository before this line; added here "
			+ "as a recorded row rather than left as a gap"},
	{"field": "gift_level", "consumers": [0, 0, 0, 0, 0, 0],
		"carried_on": "470 buildings + 429 units + 1 special",
		"recorded_type": "int", "distribution":
			"spans 0..10 over buildings and 0..40 over units, so it is not "
			+ "a constant",
		"already_in_a_census": true,
		"note": "godot-unit-behaviors records a units-only row; this line "
			+ "COMPLETES that census with the buildings side rather than "
			+ "duplicating or replacing it"},
]
const GIFT_ORDINAL_CLAIMED := false

## No branch among the 63 named is named for a gift, so the existing
## `godot-social-state` reason "no gift command exists" REMAINS TRUE while
## being incomplete: the two fields above exist and are read by nothing.
const GIFT_COMMAND_EXISTS := false
const GIFT_REFUSAL_NOTE := \
	"the two gift fields are committed and read by nothing; no gifting " \
	+ "threshold, comparison, rule or interface is derived from either"

## The canonical corpus, an explicit allow-list. A naive directory walk swept
## fixture step documents and a build cache into this line's denominators before,
## so a new document is opted into and never swept up.
const CANONICAL_CORPUS := [
	"villages/AcidCaos.json",
	"villages/General_Mike_30.json",
	"villages/General_Mike_31.json",
	"villages/Kiriakos.json",
	"villages/Nerri.json",
	"villages/Neutral.json",
	"villages/Scarlet.json",
	"villages/initial.json",
	"tests/saves/fresh-player.json",
	"tests/saves/fresh-player-pre-migration.json",
]
const CANONICAL_CORPUS_COUNT := 10

## What the allow-list deliberately excludes, recorded so the exclusion is an
## assertion rather than an accident.
const EXCLUDED_FROM_CORPUS := [
	{"excluded": "tests/fixtures", "reason": "fixture step documents are "
		+ "recorded evidence of a transaction, not canonical save documents"},
	{"excluded": "apps/client-godot/.godot", "reason": "a Godot build cache"},
	{"excluded": "villages/quest", "reason": "quest documents of a different "
		+ "shape, not placed-row saves"},
	{"excluded": "tests/saves/manifest.json", "reason": "a manifest of saves, "
		+ "not a save"},
]

## The recorded corpus figures, re-derived per run by the suite rather than
## pinned, so a committed save change fails the suite instead of silently
## contradicting it.
const PLACED_ROWS_RECORDED := 3372
const SI_ROWS_RECORDED := 53
const SI_NON_EMPTY_ROWS := 3
const SI_ELEMENTS_TOTAL := 7
const SI_DISTINCT_ELEMENT_VALUES := 1
const SI_DOCUMENTS_PRESENT := 5

## The reconciliation facts. `si` does NOT imply the committed gate in either
## direction, and both directions are measured.
##
## The second fact was first recorded as `"count": 4, "ids": [4, 12]`: four is
## the ROW count while `[4, 12]` are the placed IDS, so one `count` field beside
## an `ids` list mixed two different units. A note on the first fact was also
## simply FALSE -- it called ids 61 and 75 "the corpus's ONLY non-empty lists",
## while gated id 9 carries `[0, 0, 0]` as well. Both defects are corrected
## here and the decomposition is stated per unit, so the same conflation cannot
## recur.
const RECONCILIATION := [
	{"fact": "rows_carrying_si_on_ids_without_the_gate",
		"ids": [61, 75], "id_count": 2, "of_si_rows": 53,
		"values": [[0, 0], [0, 0]],
		"note": "the ONLY non-empty lists on ids WITHOUT the gate. They are "
			+ "NOT the corpus's only non-empty lists: gated id 9 carries "
			+ "[0, 0, 0], so three rows are non-empty in total. An earlier "
			+ "recorded note claimed otherwise and was false"},
	{"fact": "gate_positive_ids_with_no_si",
		"ids": [4, 5, 12, 167, 184, 202, 219, 247, 274, 296],
		"id_count": 10, "of": 26,
		"note": "ten of the twenty-six gate-positive ids carry no si at all, so "
			+ "the presence of the key is not evidence of assistability"},
	{"fact": "of_those_actually_placed", "ids": [4, 12], "id_count": 2,
		"rows": {"4": 1, "12": 3}, "row_count": 4,
		"note": "only two of the ten are placed at all, covering four rows; the "
			+ "remaining eight were never placed, which is the next fact"},
	{"fact": "gate_positive_ids_never_placed",
		"ids": [5, 167, 184, 202, 219, 247, 274, 296],
		"id_count": 8, "of": 26,
		"note": "committing to the table is not the same as being placed"},
]

## Candidate explanations for the reconciliation gaps, recorded as CANDIDATES.
## Nothing in the preserved source performs either, so neither is a
## measurement.
const RECONCILIATION_CANDIDATES := [
	{"candidate": "buy_si_help has no gate check, so two appends on an "
		+ "ungated row produce exactly [0, 0]",
		"measured": false},
	{"candidate": "map_add_item_from_item bypasses the gate entirely",
		"measured": false},
]
const RECONCILIATION_MEASURED := false
const RECONCILIATION_CONCLUSION := \
	"the presence of the key does not reliably indicate the committed gate, and " \
	+ "the corpus proves that in both directions"

## Every helper this module therefore does not provide (design D7). Matched
## case-insensitively and by SUBSTRING, so a suffixed helper wearing one of
## these names is still caught. `absent_because` records the measured reason for
## each, so the inventory cannot be padded with a name nobody can justify.
const ABSENT_HELPERS := [
	{"helper": "assist_reward", "absent_because":
		"the append branch makes no resource application and no grant"},
	{"helper": "assist_payout", "absent_because":
		"no stored resource moves on either recorded branch"},
	{"helper": "assist_progress", "absent_because":
		"nothing reads a value or compares two of them"},
	{"helper": "assist_ratio", "absent_because":
		"no denominator exists to divide by"},
	{"helper": "assist_complete", "absent_because":
		"no branch tests an element against anything"},
	{"helper": "friend_assist", "absent_because":
		"the friend arm has zero consumers under six counting rules over "
		+ "eleven modules"},
	{"helper": "friend_contribution", "absent_because":
		"no writer appends anything but the paid sentinel"},
	{"helper": "hired_friend", "absent_because":
		"engine.py:142 names the sole value as buying INSTEAD of hiring"},
	{"helper": "assist_eligibility", "absent_because":
		"no window, cooldown or level gate exists to derive"},
	{"helper": "assist_charge", "absent_because":
		"the append branch charges nothing"},
	{"helper": "assist_refund", "absent_because":
		"the delete branch removes one key and nothing else"},
	{"helper": "decode_sentinel", "absent_because":
		"the 0 meaning is a quoted comment, not a recovered encoding"},
	{"helper": "gift_threshold", "absent_because":
		"gift_level has zero consumers, so no comparison is derivable"},
	{"helper": "gift_send", "absent_because":
		"no branch among the 63 named is named for a gift"},
	{"helper": "assist_window", "absent_because":
		"no eligibility window or cooldown exists"},
]

## No endpoint, route, or intent is delivered (design D1). A client affordance
## for a transaction that grants nothing and charges nothing is the surface this
## capability exists to refuse.
const DELIVERED_ROUTES := []
const DELIVERED_INTENTS := []


## The recorded attribute-bag key.
static func assist_key() -> String:
	return ATTR_ASSIST_KEY


## The recorded refusals, so the suite can assert the closed set rather than
## whatever the code happens to branch on.
static func refusal_codes() -> Array:
	var out: Array = []
	for code: Variant in (REFUSAL_CODES as Dictionary).keys():
		out.append(str(code))
	out.sort()
	return out


## One recorded refusal's description, or `""` for an unrecorded code.
static func refusal_reason(code: String) -> String:
	return str((REFUSAL_CODES as Dictionary).get(code, ""))


## The committed gate's recorded shape, reported and never reimplemented.
static func gate_record() -> Dictionary:
	return {
		"field": GATE_FIELD,
		"source": GATE_SOURCE,
		"consumer_site": GATE_CONSUMER_SITE,
		"flag_value": GATE_FLAG_STRING,
		"flag_value_type": "String",
		"buildings_carried": GATE_BUILDINGS_CARRIED,
		"buildings_total": GATE_BUILDINGS_TOTAL,
		"units_carried": GATE_UNITS_CARRIED,
		"units_total": GATE_UNITS_TOTAL,
		"special_carried": GATE_SPECIAL_CARRIED,
		"special_total": GATE_SPECIAL_TOTAL,
		"encoding_note": GATE_ENCODING_NOTE,
		"reimplemented_here": false,
		"owner": str((OWNERSHIP["gate_derivation"] as Dictionary)["owner"]),
	}


## The quoted expansion of the recorded key.
static func token_expansion() -> Dictionary:
	return {
		"key": ATTR_ASSIST_KEY,
		"expansion": TOKEN_EXPANSION,
		"expansion_inferred": false,
		"quoted_source": TOKEN_EXPANSION_SOURCE,
		"source_file": TOKEN_EXPANSION_FILE,
		"concession": TOKEN_EXPANSION_CONCESSION,
	}


## The sentinel, its value and the quoted comment fixing its meaning.
static func sentinel_record() -> Dictionary:
	return {
		"value": SENTINEL_VALUE,
		"quoted_source": SENTINEL_COMMENT_SOURCE,
		"source_file": SENTINEL_COMMENT_FILE,
		"decoded": false,
		"means": "a paid substitute for a friend",
		"friend_arm_writers": 0,
		"consumer_counts": FRIEND_ARM_CONSUMERS.duplicate(),
		"consumer_rules": FRIEND_ARM_RULES.duplicate(),
		"modules": FRIEND_ARM_MODULES,
	}


## The two committed gift fields with their zero-consumer measurement.
static func gift_field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in GIFT_FIELDS:
		out.append(str(entry["field"]))
	return out


## One gift field's recorded row, or `null` when the name was not measured.
static func gift_field_record(field_name: String) -> Variant:
	for entry: Dictionary in GIFT_FIELDS:
		if str(entry["field"]) == field_name:
			return entry
	return null


## The recorded precondition of the dedicated dispatchers, and whether this
## module enforces it. It does not, and the reason is a corpus fact.
static func dispatch_precondition() -> Dictionary:
	return {
		"precondition": DISPATCH_PRECONDITION,
		"enforced_here": DISPATCH_PRECONDITION_ENFORCED,
		"why_not": "enforcing the gate would refuse two committed corpus rows, "
			+ "and the preserved branch has no such check",
	}


## Project one placed map row's assist state.
##
## The returned object reports `present()` false for a row whose bag carries no
## key, which is a DIFFERENT recorded state from a row carrying an empty list:
## `buy_si_help` creates the key lazily and `finish_si` deletes it, so the two
## are produced by different branches.
static func project(row: Variant) -> AssistProjection:
	return AssistProjection.new(row)


## The read-only projection over one placed map row.
##
## Nothing is written back. This module delivers no route and no intent
## (design D1), so there is no mutating path to guard - and the caller owns the
## payload even if a future caller tried.
class AssistProjection extends RefCounted:
	var _refusal: String = ""
	var _message: String = ""
	var _present: bool = false
	var _length: int = -1
	var _elements: Array = []

	func _init(row: Variant) -> void:
		if typeof(row) != TYPE_ARRAY:
			_refuse("row_not_a_list", "the map row is not a list")
			return
		var slots: Array = row
		if slots.size() <= ATTR_BAG_SLOT:
			_refuse("bag_slot_absent",
				"the row carries no attribute-bag slot at index %d"
					% ATTR_BAG_SLOT)
			return
		var bag: Variant = slots[ATTR_BAG_SLOT]
		if typeof(bag) != TYPE_DICTIONARY:
			_refuse("bag_not_an_object",
				"the recorded attribute bag is not an object")
			return
		var recorded: Dictionary = bag
		if not recorded.has(ATTR_ASSIST_KEY):
			_present = false
			_length = -1
			_elements = []
			return
		var value: Variant = recorded[ATTR_ASSIST_KEY]
		if typeof(value) != TYPE_ARRAY:
			_refuse("assist_value_not_a_list",
				"the recorded value of `%s` is %s, not a list"
					% [ATTR_ASSIST_KEY, type_string(typeof(value))])
			return
		var source: Array = value
		_present = true
		_length = source.size()
		var copied: Array = []
		for element: Variant in source:
			copied.append({
				"value": element,
				# Reported verbatim. A JSON integer decodes to a float under
				# this engine, so the engine-observed type is published
				# beside the CPython recorded type rather than one being
				# presented as the other.
				"engine_type": type_string(typeof(element)),
				"type_record": _element_type_record(element),
			})
		_elements = copied

	func _refuse(code: String, message: String) -> void:
		_refusal = code
		_message = message
		_present = false
		_length = -1
		_elements = []

	## Whether the recorded state is readable at all.
	func resolvable() -> bool:
		return _refusal.is_empty()

	## The distinct refusal code, or `""` when the state resolved.
	func refusal_code() -> String:
		return _refusal

	## The recorded state that travelled untouched beside the refusal.
	func refusal_message() -> String:
		return _message

	## Whether the recorded bag carries the key. A resolved row with no key is
	## NOT an empty list.
	func present() -> bool:
		return _present

	## The recorded list length, or `-1` when no length is readable.
	func recorded_length() -> int:
		return _length

	## Each element's value and type, verbatim. Never decoded, never compared.
	func element_records() -> Array:
		return _elements.duplicate()

	## Whether the recorded list is readable and carries nothing.
	func is_empty_list() -> bool:
		return _present and _length == 0

	## The recorded type of one element, as this engine sees it.
	##
	## Named for what it returns rather than for what it sounds like: this is
	## the engine-observed type, not a recovered CPython type. A JSON integer
	## decodes to a float here, so an integral float is reported with that
	## difference stated instead of being silently presented as an `int`.
	func _element_type_record(value: Variant) -> String:
		var engine: String = type_string(typeof(value))
		if engine == "float" and is_equal_approx(value, round(value)):
			return "int (decoded as float by this engine)"
		return engine
