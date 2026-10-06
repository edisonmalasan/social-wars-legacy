extends RefCounted
## Social-state projection for OpenSpec `godot-social-state`.
##
## ## This line delivers a REFUSAL (design D1)
##
## What is delivered is a typed, read-only projection of the social state a
## committed save actually carries. The committed investigation
## `docs/legacy-m11-social.md` (PR #309, corrected in #310) measured nineteen
## social state fields, and the suite RE-DERIVES this number on every run:
## **twelve of them have zero occurrences of any kind** across all eleven
## legacy modules - no read, no write, no mention.
##
## **Nineteen MEASURED, seventeen SOCIAL (corrected by `godot-darts`)**
##
## The `godot-darts` change measured two of these fields and found that neither is
## social: `timeStampEndPremium` is a paid-purchase instant whose value the server
## DERIVES from a committed schedule, and `crossPromotionsFinished` is a
## cross-promotion flag. This module therefore no longer calls all nineteen
## "social". The census is unaffected -- it measures *occurrence*, not ownership --
## so the pinned `ZERO_OCCURRENCE_FIELDS` still contains `crossPromotionsFinished`
## and the re-derived set must still equal the pinned set. What changed is the
## field set's *description*, and `timeStampEndPremium`'s recorded description,
## which asserted a single client-sent write where `command.py:612-623` performs
## two server-derived ones. See `FOREIGN_FIELDS`, and note the verification in
## `test_social_state.gd`'s hand-off check.
##
## The committed investigation and the original proposal both said THIRTEEN,
## counting `questsRank` in the group. That was wrong: `admin_set_quest_rank`
## both READS and WRITES it, so the field is in the read-and-written group and
## the zero-occurrence group is twelve. The census counts identifier tokens and
## quoted subscripts as two separate forms for exactly this reason (see
## `ZERO_OCCURRENCE_FIELDS`). The prose was corrected to match the measurement
## rather than the measurement bent to match the prose.
##
## That is the finding this capability exists to record. It is emphatically NOT a
## claim that friends, visits, scores, or social rewards work, and NOT a claim
## that the server never had them: the Flash client may have held them entirely
## client-side, which would leave no server branch ever to exist. That question is
## **unverifiable from the preserved oracle**.
##
## ## An absent field is ABSENT, never empty (design D4)
##
## All thirty-three committed documents carry all nineteen keys today, so a
## missing key means a document shape this capability has never observed. Every
## accessor therefore reports absence and **never** substitutes that field's
## recorded uniform value. Folding "absent" into "empty" would hide precisely the
## case worth seeing.
##
## ## Uniform emptiness is reported, never read as a relationship (design D3)
##
## Twelve of the write-less fields hold exactly ONE value across all
## thirty-three documents - `null`, `{}`, `[]`, or `0`. That value and its
## document count are reported verbatim. `neighbor_assists` holding `{}` is
## reported as "recorded value, 33 of 33 documents"; it is **not** reported as
## "this player has no assists", because that is a reading of an empty container
## and the corpus cannot distinguish "never used" from "reset".
##
## ## The census is re-derived every run, never inherited (design D2)
##
## `ZERO_OCCURRENCE_FIELDS` is a pinned expectation, but the delivered suite
## recomputes the group from the committed legacy sources on **every run** and
## requires the recomputed set to equal the pinned one in both directions. A
## legacy edit that adds or removes an occurrence fails the run rather than
## silently contradicting the delivered claim. A suite that merely asserted `13`
## would let the number rot.
##
## ## The one real writer is recorded, not reproduced (design D5)
##
## `set_resource_allies` (`command.py:637`) writes
## `map["resourceAlliesMarket"] = resource` from **client-sent `args[0]`**, and
## separately stamps the addressed row's `item[3]` with `time_now` before calling
## `finish_si`. Both effects are recorded verbatim below. **No endpoint, route,
## or intent is delivered for either.** The row-instant stamp is reported with
## **no semantics derived**: no reader of `item[3]` is claimed, and inventing one
## would be exactly the kind of guess this project records as invention.
##
## `godot-building-move` already owns the type-agnostic, client-coordinated
## coordinate write; re-deriving it here would duplicate a surface owned
## elsewhere, so this capability only records that it is not owned here.
##
## ## Content tables are NOT projected (design D1, D6)
##
## `neighbor_assists`, `findable_items`, and `social_items` are owned by
## `social-tables-normalization`, which classifies them as recorded display data
## and amounts rather than implemented behaviour. This module projects **state
## only**. No reward is decoded, no coin value is charged, no worker or worker
## cost is selected, and no assist task or eligibility window is derived.
##
## ## Anti-invention guards (design D7)
##
## `ABSENT_HELPERS` names every helper this module therefore does not provide. The
## delivered suite compares this module's **whole static-function inventory**
## against a pinned list, so a friend-level, assist-reward, visit, score, or
## relationship helper fails the suite wherever it is added. The match is
## case-insensitive and **substring-based**, because an exact-name check was
## measured in this project to miss a suffixed helper wearing a reserved name.
##
## Additionally the suite asserts this module contains **no comparison of one
## committed social value against another** - no rule may be built out of the
## recorded values. Both guards are proven by injection before acceptance: a guard
## never demonstrated failing is not a guard.

## Storage locations a measured field can live in.
const STORE_PRIVATE := "privateState"
const STORE_MAP := "maps[]"

## The nineteen measured social state fields, in the investigation's order.
##
## `zero_occurrence` is the recorded census result - true when the field has no
## occurrence of any kind across the eleven legacy modules. `written_by` is empty
## for a field nothing writes. `recorded_value` is the single value the corpus
## holds for it, and `documents` how many documents hold it.
##
## Declared as Dictionaries rather than objects so the table is a plain constant
## the suite can compare directly, matching `unit_movement.gd`'s
## `PLACEMENT_FIELDS` convention.
const FIELDS := [
	{
		"name": "friendsHelpedCoveredItem", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": null, "documents": 33,
		"note": "uniformly null; the only field whose name promises a friend count",
	},
	{
		"name": "neighborAssists", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": {}, "documents": 33,
		"note": "committed rewards are owned by social-tables-normalization",
	},
	{
		"name": "receivedAssists", "store": STORE_MAP,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": {}, "documents": 33,
		"note": "a map key, carried and never written",
	},
	{
		"name": "resourceAlliesMarket", "store": STORE_MAP,
		"zero_occurrence": false, "written_by": ["set_resource_allies"],
		"readers": [], "recorded_value": null, "documents": 33,
		"note": "written from a client-sent argument; NOT reproduced here",
	},
	{
		"name": "firstTimeAlliance", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": null, "documents": 33, "note": "uniformly null",
	},

	{
		"name": "helpMap", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": [], "documents": 33, "note": "uniformly empty",
	},
	{
		"name": "attacksSent", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": [], "documents": 33, "note": "uniformly empty",
	},
	{
		"name": "attacksReceived", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": [], "documents": 33, "note": "uniformly empty",
	},
	{
		"name": "attacksPack", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": 0, "documents": 33, "note": "uniformly zero",
	},
	{
		"name": "spyings", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": [], "documents": 33, "note": "uniformly empty",
	},
	{
		"name": "spyingsPack", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": 0, "documents": 33, "note": "uniformly zero",
	},
	{
		"name": "publishedOpenGraphUnit", "store": STORE_PRIVATE,
		"zero_occurrence": false, "written_by": ["rt_open_graph_unit"],
		"readers": [], "recorded_value": [], "documents": 33,
		"note": "a social-publish list, not a friends list",
	},
	{
		"name": "marketPlaceFirstTime", "store": STORE_PRIVATE,
		"zero_occurrence": false, "written_by": ["first_time_marketplace"],
		"readers": [], "recorded_value": false, "documents": 33,
		"note": "set True unconditionally by its branch",
	},
	{
		"name": "questsRank", "store": STORE_PRIVATE,
		"zero_occurrence": false, "written_by": ["admin_set_quest_rank"],
		"readers": ["admin_set_quest_rank"], "recorded_value": 0, "documents": 33,
		"note": "READ AND WRITTEN by one branch; an identifier-only census "
			+ "miscounted it as zero-occurrence (design D9)",
	},
	{
		"name": "numTradesDone", "store": STORE_MAP,
		"zero_occurrence": false, "written_by": ["trade_resource"],
		"readers": [], "recorded_value": 0, "documents": 33,
		"note": "a market trade counter",
	},
	{
		"name": "resourcesTraded", "store": STORE_MAP,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": {}, "documents": 33, "note": "uniformly empty",
	},
	{
		"name": "timestampLastTrade", "store": STORE_MAP,
		"zero_occurrence": false, "written_by": ["trade_resource", "fast_forward"],
		"readers": [], "recorded_value": 0, "documents": 33,
		"note": "fast_forward subtracts a client-supplied second count from it",
	},
	{
		"name": "timeStampEndPremium", "store": STORE_PRIVATE,
		"zero_occurrence": false, "written_by": ["buy_premium_account"],
		"readers": [], "recorded_value": 0, "documents": 33,
		"foreign_to": "godot-darts",
		"note": "NOT SOCIAL and NOT client-sent: this was recorded here as "
			+ "\"a single instant write\" by a client-sent branch, and both halves "
			+ "were wrong. command.py:612-623 writes it TWICE -- :619 on the set "
			+ "arm, :622 on the extend arm -- and the value is derived SERVER-side "
			+ "from the committed PREMIUM_ACCOUNTS schedule via "
			+ "get_game_config.get_premium_days (get_game_config.py:181-189). "
			+ "Corrected by the godot-darts change; see FOREIGN_FIELDS.",
	},
	{
		"name": "crossPromotionsFinished", "store": STORE_PRIVATE,
		"zero_occurrence": true, "written_by": [], "readers": [],
		"recorded_value": [], "documents": 33,
		"foreign_to": "godot-darts",
		"note": "NOT SOCIAL: a cross-promotion flag, not a social fact. Still "
			+ "zero-occurrence -- the census is about occurrence and is unchanged "
			+ "by the re-filing. Foreign ownership is in FOREIGN_FIELDS.",
	},
]

## The pinned zero-occurrence census: fields with no occurrence of any kind.
##
## Pinned as an expectation the suite RE-DERIVES each run (D2), never as a number
## taken on trust.
const ZERO_OCCURRENCE_FIELDS := [
	"friendsHelpedCoveredItem", "neighborAssists", "receivedAssists",
	"firstTimeAlliance", "helpMap", "attacksSent", "attacksReceived",
	"attacksPack", "spyings", "spyingsPack",
	"resourcesTraded", "crossPromotionsFinished",
]

## The one branch that both reads and writes a measured field.
##
## Recorded here because the census caught a defect while building this line: an
## identifier-only count scored `questsRank` as zero-occurrence, since the
## comment-stripping lexer erases the `privateState["questsRank"]` form the branch
## actually uses. `command.py:745-750` reads and writes it, so it belongs to
## neither the zero group nor the written-only group.
const READ_AND_WRITTEN := {"questsRank": "admin_set_quest_rank"}

## The eleven legacy modules the census is measured over.
const LEGACY_MODULES := [
	"auctions.py", "bundle.py", "command.py", "constants.py", "engine.py",
	"get_game_config.py", "get_player_info.py",
	"legacy_command_recorder.py", "server.py", "sessions.py", "version.py",
]

## The one real social-state writer, recorded verbatim and NOT reproduced.
##
## `client_sent_argument` names the argument the legacy branch writes straight
## through - the untrusted pattern `AGENTS.md` names as "Bad". No route in this
## capability performs either write.
const RECORDED_WRITERS := [{
	"branch": "set_resource_allies",
	"source": "command.py:637",
	"target": "maps[]/resourceAlliesMarket",
	"client_sent_argument": "args[0]",
	"effects": [
		"writes the market resource from a client-sent value",
		"stamps the addressed row's item[3] with time_now",
		"calls finish_si on the addressed row",
	],
	"semantics_derived": false,
	"reproduced": false,
	"note": "item[3] is reported verbatim; no reader of item[3] is claimed.",
}]

## The four other written fields and the branch that writes each.
##
## `timeStampEndPremium` remains mapped here because that branch really does write
## it, but the mapping is NOT a claim of social ownership: the field is foreign
## (see FOREIGN_FIELDS) and the recorded value is server-derived, not client-sent.
const OTHER_WRITTEN_FIELDS := {
	"publishedOpenGraphUnit": "rt_open_graph_unit",
	"marketPlaceFirstTime": "first_time_marketplace",
	"numTradesDone": "trade_resource",
	"timestampLastTrade": "trade_resource",
	"timeStampEndPremium": "buy_premium_account",
}

## Measured fields that are NOT social state, and the capability that owns them.
##
## Recorded by the `godot-darts` change, which measured both fields and found that
## neither is a social fact. Until then this capability called all nineteen of its
## measured fields "social", and for `timeStampEndPremium` it also recorded the
## branch as writing a single client-sent instant -- which is wrong twice over:
## `command.py:612-623` writes the instant twice, once per arm, from a
## **server-derived** value.
##
## The fields stay PRESENT in `FIELDS` and, for `crossPromotionsFinished`, stay in
## `ZERO_OCCURRENCE_FIELDS`. The census measures *occurrence*; this table measures
## *ownership*, and re-filing a field must not silently change a census result. So
## the nineteen measured fields remain nineteen and the re-derived census still has
## to equal the pinned set -- while the field set is now described honestly as
## **seventeen social fields plus two foreign ones**.
##
## `owner` is verified, not asserted: the suite requires the named capability to
## exist AND to project both fields, so this hand-off cannot rot into an orphan.
const FOREIGN_FIELDS := [
	{
		"name": "timeStampEndPremium",
		"owner": "godot-darts",
		"why_not_social": "a paid-purchase instant with a server-derived "
			+ "duration, not a social fact",
		"still_measured_here": true,
		"corrected_claim": "was recorded as \"a single instant write\" from a "
			+ "client-sent argument; it is two writes (command.py:619 and :622) "
			+ "from a committed schedule",
	},
	{
		"name": "crossPromotionsFinished",
		"owner": "godot-darts",
		"why_not_social": "a cross-promotion flag, uniformly empty and never "
			+ "read or written by any of the eleven legacy modules",
		"still_measured_here": true,
		"corrected_claim": "was filed as social state; the census result "
			+ "(zero-occurrence) is unchanged and remains true",
	},
]

## The number of measured fields that ARE social state, derived rather than typed.
##
## Kept as a function so the count cannot drift from `FIELDS` minus
## `FOREIGN_FIELDS`. A hand-written 17 beside a nineteen-field table is exactly the
## kind of pair that goes stale.
static func social_field_names() -> Array:
	var foreign: Array = foreign_field_names()
	var out: Array = []
	for entry: Dictionary in FIELDS:
		var field_name: String = str(entry["name"])
		if not foreign.has(field_name):
			out.append(field_name)
	return out


## The measured fields declared foreign to this capability.
static func foreign_field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in FOREIGN_FIELDS:
		out.append(str(entry["name"]))
	return out


## The capability that owns a foreign field, or `""` when the name is not foreign.
static func foreign_owner_of(field_name: String) -> String:
	for entry: Dictionary in FOREIGN_FIELDS:
		if str(entry["name"]) == field_name:
			return str(entry["owner"])
	return ""

## Save keys carried by every document and read by nothing in the server.
##
## Reported as carried-but-never-read (visits/score requirements). No world, visit,
## or leaderboard concept is derived from either.
const WORLD_KEYS := ["world_id", "worldChange"]

## Near-misses that were checked and REJECTED, recorded so they are not re-counted
## as scores by a later line.
const REJECTED_SCORE_READINGS := [
	{"token": "lost", "actual": "local unit-loss counter",
		"source": "command.py:792, command.py:868"},
	{"token": "won", "actual": "auction-bet result", "source": "auctions.py:164"},
]

## Why no executed-legacy fixture accompanies this capability (D8).
const FIXTURE_ABSENCE := {
	"fixture_delivered": false,
	"reason": "no social command exists to capture, and the corpus holds no "
		+ "populated social field",
	"fabricated_precondition": false,
}

## Content tables this capability does NOT project, and their owner.
const CONTENT_BOUNDARY := {
	"owner": "social-tables-normalization",
	"tables": ["neighbor_assists", "findable_items", "social_items"],
	"reward_decoded": false,
	"coin_charged": false,
	"worker_selected": false,
	"eligibility_derived": false,
}

## Every helper this module therefore does not provide (design D7).
##
## Matched case-insensitively and by SUBSTRING, so a suffixed helper wearing one
## of these names is still caught. `absent_because` records the measured reason
## for each, so the inventory cannot be padded with a name nobody can justify.
const ABSENT_HELPERS := [
	{"helper": "assist_reward", "absent_because":
		"neighbor_assists reward is committed content owned by "
		+ "social-tables-normalization and has zero legacy consumers"},
	{"helper": "assist_task", "absent_because":
		"no legacy branch reads a neighbor_assists task; the field has zero "
		+ "occurrences across all eleven modules"},
	{"helper": "assist_window", "absent_because":
		"no eligibility, cooldown, or window rule exists to derive"},
	{"helper": "friend_level", "absent_because":
		"friendsHelpedCoveredItem has zero occurrences and is uniformly null in "
		+ "33 of 33 documents"},
	{"helper": "friend_state", "absent_because":
		"no branch writes or reads any friend field"},
	{"helper": "friend_request", "absent_because":
		"no friend command exists among the 63 named branches"},
	{"helper": "visit_state", "absent_because":
		"no visit token occurs in any legacy module; world_id and worldChange are "
		+ "carried but never read"},
	{"helper": "visit_map", "absent_because":
		"no surface addresses another player's map"},
	{"helper": "neighbor_map", "absent_because":
		"neighborAssists is uniformly {} and has zero occurrences"},
	{"helper": "social_reward", "absent_because":
		"all 41 committed social content entries have zero legacy consumers"},
	{"helper": "social_action", "absent_because":
		"no branch dispatches on a social item"},
	{"helper": "score_for", "absent_because":
		"there is zero arithmetic on any score-like value in the dispatcher"},
	{"helper": "leaderboard", "absent_because":
		"the token occurs zero times across all eleven modules"},
	{"helper": "ranking", "absent_because":
		"the token occurs zero times; questsRank is read by admin_set_quest_rank "
		+ "and never written, which is not a ranking"},
	{"helper": "allies_of", "absent_because":
		"resourceAlliesMarket is a client-sent market resource, not a set of "
		+ "allies; no reader is claimed"},
	{"helper": "gift_to", "absent_because": "no gift command exists"},
	{"helper": "invite_state", "absent_because":
		"no invite token occurs in any legacy module"},
	{"helper": "relationship", "absent_because":
		"an empty container is reported verbatim and never read as a "
		+ "relationship count"},
	{"helper": "cooperation", "absent_because":
		"no cooperation command or state exists"},
	{"helper": "spy_on", "absent_because":
		"spyings and spyingsPack have zero occurrences and are uniformly empty "
		+ "and zero in 33 of 33 documents"},
	{"helper": "attack_pack_for", "absent_because":
		"attacksPack has zero occurrences and is uniformly 0"},
	{"helper": "receive_assist", "absent_because":
		"receivedAssists is uniformly {} with zero occurrences"},
	{"helper": "send_assist", "absent_because":
		"no branch writes an outgoing assist"},
	{"helper": "help_reward", "absent_because":
		"neighbor_assists rewards are owned by social-tables-normalization and "
		+ "are not decoded here"},
	{"helper": "populate_example", "absent_because":
		"the corpus holds no populated social field and this capability "
		+ "synthesizes none"},
]

## No endpoint, route, or intent is delivered (D5, D8).
const DELIVERED_ROUTES := []


## The projected field names, in the investigation's order.
static func field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in FIELDS:
		out.append(str(entry["name"]))
	return out


## The fields recorded as having zero occurrences of any kind.
static func zero_occurrence_names() -> Array:
	return (ZERO_OCCURRENCE_FIELDS as Array).duplicate()


## The store a measured field lives in, or `""` when the name was not measured.
##
## An unmeasured name yields no store rather than a guessed one.
static func store_of(field_name: String) -> String:
	for entry: Dictionary in FIELDS:
		if str(entry["name"]) == field_name:
			return str(entry["store"])
	return ""


## One measured field's record, or `null` when the name was not measured.
##
## Returns `null` rather than a synthesised entry, so an unmeasured name cannot
## be mistaken for a measured one.
static func field_record(field_name: String) -> Variant:
	for entry: Dictionary in FIELDS:
		if str(entry["name"]) == field_name:
			return entry
	return null


## Project a committed save document.
##
## The returned object's `present_names()` reports which measured keys the
## document actually carried; a key it did not carry is **absent**, never
## defaulted to that field's recorded uniform value.
static func project(document: Variant = null) -> SocialProjection:
	return SocialProjection.new(document)


## The read-only projection over one committed save document.
##
## Nothing is written back: this capability has no endpoint and no route
## (design D8), so there is no mutating path to guard.
class SocialProjection extends RefCounted:
	var _present: Dictionary = {}

	func _init(document: Variant = null) -> void:
		if typeof(document) != TYPE_DICTIONARY:
			return
		var source: Dictionary = document
		var containers: Array = []
		var private_state: Variant = source.get(STORE_PRIVATE, null)
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
		for entry: Dictionary in FIELDS:
			var field_name: String = str(entry["name"])
			for container: Variant in containers:
				if (container as Dictionary).has(field_name):
					_present[field_name] = (container as Dictionary)[field_name]
					break

	## True when the document actually carried the key. An absent key is
	## reported false, which is what keeps it distinct from a recorded `null`.
	func present(field_name: String) -> bool:
		return _present.has(field_name)

	## The recorded value of a field, or `null` when absent.
	##
	## An absent field and a field recorded as `null` are distinguished by
	## `present()`; this accessor alone cannot tell them apart, by design.
	func value(field_name: String) -> Variant:
		return _present.get(field_name, null)

	## The one-field view: what this document recorded, beside the field's own
	## committed uniform value.
	##
	## Returns `null` for a name that is not a measured field, never a
	## synthesized entry. For a measured field it returns a dictionary of three
	## separate columns:
	##
	##   - `present`         whether the document really carried the key
	##   - `recorded_value`  what the document recorded, `null` when absent
	##   - `committed_value` the uniform value the field has ACROSS the corpus
	##
	## The committed uniform is a **separate column** and is never substituted
	## for a missing key. That separation is the load-bearing part: the 19
	## measured fields are uniform across documents, which is a fact about the
	## corpus, not a default this projection may fill in. An absent key must
	## stay distinguishable from a key recorded as `{}` or `0`.
	func field(field_name: String) -> Variant:
		# The lookup is inlined rather than delegated to the outer script's
		# static `field_record()`: GDScript does not resolve an outer static by
		# bare name from inside an inner class, so the call failed to compile.
		# Both read the same `FIELDS` table, so they cannot drift.
		var matched: Variant = null
		for entry: Dictionary in FIELDS:
			if str(entry["name"]) == field_name:
				matched = entry
				break
		if matched == null:
			return null
		return {
			"present": _present.has(field_name),
			"recorded_value": _present.get(field_name, null),
			"committed_value": (matched as Dictionary).get("recorded_value", null),
		}

	## The fields this document actually carries, in measured order.
	func present_names() -> Array:
		var out: Array = []
		for entry: Dictionary in FIELDS:
			var field_name: String = str(entry["name"])
			if _present.has(field_name):
				out.append(field_name)
		return out

	## The fields this document does not carry. Reported rather than defaulted.
	func absent_names() -> Array:
		var out: Array = []
		for entry: Dictionary in FIELDS:
			var field_name: String = str(entry["name"])
			if not _present.has(field_name):
				out.append(field_name)
		return out
