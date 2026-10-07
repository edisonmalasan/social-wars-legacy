extends RefCounted
## Roster projection for OpenSpec `godot-friends`.
##
## ## What this module is, and what it refuses to be
##
## The deliver item is named `friends`. What the preserved server actually
## serves is the `neighbors` roster function (`sessions.py:191-221`) returning
## **every other loaded village, unconditionally** — a directory listing, not a
## social relationship. There is no friendship record anywhere in the eleven
## legacy modules: no add, no remove, no accept, no decline, no consent, no
## direction.
##
## So this module delivers a **roster** and refuses the relationship vocabulary.
## The refusal is carried structurally, not in prose, because prose cannot fail:
## see ABSENT_HELPERS and the delivered suite's three guards.
##
## ## The naming correction is the point, not an accident
##
## `godot-social-state` deliberately withheld the name `godot-friends` on an
## explicitly recorded premise — that the roster was absent. `docs/legacy-m11-
## friends.md` (PR #321) **measured that premise false**: `friends` has five
## whole-file and four code-only occurrences across the eleven legacy modules.
## The capability name is therefore the deliver item's committed name, and the
## correction has to be visible in the delivered surface rather than quietly
## corrected out of the record.
##
## ## Transport is already delivered; this is the projection (design D1)
##
## `/v0/bootstrap` embeds the real in-process `get_player_info()`, so the
## roster already rides the wire at `player_info.neighbors`. Measured at the
## Propose stage: five entries, eighteen keys each, every entry leaf-identical
## to the committed executed oracle. **No endpoint is added and
## `apps/compat-api/**` is untouched**, so the compat suite must remain at its
## 3077 baseline. What was undelivered is the typed projection, not transport.
##
## ## The `neighbors` token has two meanings here (recorded false attraction)
##
## A search for `neighbors` in the delivered client finds
## `boot_data.gd:607 var neighbors := 0` — the expansion **requirement**,
## owned and refused by `godot-building-expand`. This module is named
## `friends_roster` rather than `neighbors` for exactly that reason.
##
## ## Membership is a SET (design D3)
##
## The preserved order follows `os.listdir()` and is already recorded as
## environment-dependent in
## `tests/fixtures/godot-compatibility-boot/field-stability.json`. So this
## projection exposes **no index and no ordering**, only pid lookup and a
## count. A caller that needs an order must impose one itself, and no order is
## claimed here.
##
## ## Twelve carried plus six derived (design D4)
##
## Every entry is a deep copy of the other village's `playerInfo` — twelve keys
## — with six fields read from that village's `maps[0]`. `cash` is carried by
## `playerInfo` but `steel` is derived from `maps[0]`; the two sets are reported
## separately rather than merged into one field list, because which half came
## from where is exactly what a reader needs to know.
##
## ## The exclusion is a LITERAL, not a lookup (design D4)
##
## See EXCLUSION_RECORD. The count follows from the code — the eight committed
## village files, less the one never loaded, less the two excluded — and NOT
## from a file count. Deriving the pair from a filename pattern or a directory
## size would be an invention that happens to agree.

## The bootstrap envelope path at which the v0 Compatibility API nests the
## roster. The LEGACY fixture document carries `neighbors` at its **top level**,
## so the two shapes are recorded as distinct rather than assumed identical.
const ENVELOPE_PATH := ["player_info", "neighbors"]

## The key the roster itself lives under, once the envelope has been descended.
const ROSTER_KEY := "neighbors"

## The twelve `playerInfo` keys every entry carries, in committed order.
##
## Recorded verbatim from the committed executed capture rather than derived
## from a village, because a roster entry is a copy of `playerInfo` and nothing
## more.
const CARRIED_PLAYER_INFO_KEYS := [
	"cash", "completed_tutorial", "default_map", "last_logged_in",
	"map_names", "map_sizes", "name", "pic", "pid",
	"sp_ref_cat_install", "sp_ref_uid", "world_id",
]

## The six fields the preserved server reads from the other village's
## `maps[0]` and writes onto the entry.
##
## `steel` is here and `cash` is not, even though `playerInfo` carries `cash`.
## That asymmetry is the preserved server's behaviour and is reproduced rather
## than tidied.
const DERIVED_MAP_FIELDS := ["xp", "level", "gold", "wood", "oil", "steel"]

## The recorded entry width, taken from the built key list rather than typed,
## so a table edit cannot leave a stale count beside it.
##
## Deliberately NOT the sum of the two table sizes. Adding two committed counts
## is arithmetic on committed values, which is exactly what this module's
## ordering/arithmetic guard refuses to contain (design D3) — and the count
## has no consumer that a sum would serve better.
static func entry_key_count() -> int:
	return entry_key_names().size()


## Every entry key name, carried half then derived half, as a set.
static func entry_key_names() -> Array:
	var out: Array = []
	for name: Variant in CARRIED_PLAYER_INFO_KEYS:
		out.append(str(name))
	for name: Variant in DERIVED_MAP_FIELDS:
		out.append(str(name))
	return out


## True when a key is part of the carried half of an entry.
static func is_carried_key(name: String) -> bool:
	return CARRIED_PLAYER_INFO_KEYS.has(name)


## True when a key is part of the derived half of an entry.
static func is_derived_key(name: String) -> bool:
	return DERIVED_MAP_FIELDS.has(name)


## The two-pid literal exclusion, its recorded reason, the alternative that was
## measured and rejected, and the scope each of the two exclusion rules applies
## to. The two rules live in **different** scopes and are therefore reported
## separately: a static village that happens to carry your own pid is NOT
## excluded, because the self-exclusion runs in the saves loop only.
const EXCLUSION_RECORD := {
	"excluded_pids": ["100000030", "100000031"],
	"excluded_pids_are_literals": true,
	"reason": "sessions.py:173-174 and :196-197 hardcode both pids as string "
		+ "literals. The committed comment `# general Mike` is the only "
		+ "statement anywhere of what they are, and nothing in config/ or in "
		+ "the normalized content package names them. There is therefore "
		+ "nothing to derive the pair FROM.",
	"rejected_alternative": "deriving the exclusion from content - matching "
		+ "a village file-name pattern, or treating initial.json as the only "
		+ "unloaded file and taking the directory size as the roster size. "
		+ "The count follows from the CODE (every villages/*.json except "
		+ "initial.json, minus the literal pair), not from the eight files "
		+ "on disk. A derivation from a file count is an invention that "
		+ "happens to agree with the corpus today.",
	"static_loop_rule": "the two-pid literal pair, applied to the loaded "
		+ "static-village loop ONLY",
	"saves_loop_rule": "the requesting player's own pid, applied to the "
		+ "saves loop ONLY",
	"uid_use": "the legacy local that names the recording player is read only "
		+ "by the saves-loop self-exclusion; it is never compared against a "
		+ "static village",
	"derived_from_file_count": false,
}


## The excluded pids, read through the record rather than transcribed.
static func excluded_pids() -> Array:
	var out: Array = []
	for pid: Variant in (EXCLUSION_RECORD["excluded_pids"] as Array):
		out.append(str(pid))
	return out


## True when a static-village pid is excluded by the literal pair.
##
## Reports the filter itself, and nothing else: it does not count villages, not
## consult a directory, and not infer anything from a name.
static func is_excluded_static_pid(pid: String) -> bool:
	return excluded_pids().has(pid)


## True when a saves-loop pid survives the self-exclusion.
static func is_saves_loop_member(pid: String, self_pid: String) -> bool:
	return pid != self_pid


## The two roster channels the preserved server serves, reported side by side
## and **never deduplicated** (design D6).
##
## They are near-duplicate functions that were not derived from one another, and
## they genuinely disagree: one carries six economy fields and one carries
## none. A shared RosterEntry type parameterised by channel would assert a
## derivation the source does not show, so only membership is common — and
## membership is reported as a comparison, not factored into a type.
const CHANNELS := [
	{
		"channel": "bootstrap_roster",
		"function": "neighbors",
		"source": "sessions.py:191-221",
		"transport": "Compatibility API /v0/bootstrap, at player_info.neighbors",
		"entry_field_count": 18,
		"entry_fields": "twelve carried playerInfo keys plus six maps[0]-derived",
		"carries_economy": true,
		"carries_private_state": false,
		"delivered": true,
		"executed_evidence": "tests/fixtures/godot-compatibility-boot/steps/"
			+ "get_player_info/response.body",
	},
	{
		"channel": "flashvar_roster",
		"function": "fb_friends_str",
		"source": "sessions.py:168-189",
		# The literal attribute name is spelled out in prose here rather than
		# quoted: `test_town_gate.gd`'s RUNTIME_NEEDLES and
		# `test_project_scope.gd`'s FORBIDDEN table both forbid the Flash
		# variable-name literal in ANY project file, so quoting it would fail a
		# no-Flash gate by existing. The citation below is what a reader needs
		# to check the claim, and neither gate is relaxed to permit the quote.
		"transport": "a Flash client embed variable, attribute name at "
			+ "templates/play.html:99 and served by server.py:91",
		"entry_field_count": 2,
		"entry_fields": "uid and pic_square",
		"carries_economy": false,
		"carries_private_state": false,
		"delivered": false,
		"delivered_because": "a Flash client embed variable is not a "
			+ "modern-runtime surface; AGENTS.md requires the modern client to "
			+ "depend on GameApi and never on a Flash client embed variable",
		"executed_evidence": "tests/fixtures/godot-compatibility-boot/steps/"
			+ "play_page/response.body",
	},
]

## The serialization detail recorded so it is not mistaken for a contract: the
## captured FlashVar JSON lists `pic_square` before `uid` although
## `fb_friends_str` assigns `uid` first. That is the template's JSON writer, not
## a field-order guarantee, so neither channel's key order is claimed here.
const CHANNEL_FIELD_ORDER_NOT_A_CONTRACT := {
	"flashvar_capture_lists": ["pic_square", "uid"],
	"flashvar_function_assigns": ["uid", "pic_square"],
	"cause": "the template's JSON serializer, not the branch",
	"claimed": false,
}


## The visit surface, recorded as a **divergence not reproduced** and delivered
## as nothing at all (design D8).
##
## `get_neighbor_info` (`server.py:155-182`) is reached by three of four
## branches of one route, but no committed fixture exercises a visit. The
## general-Mike branch tests membership in the literal pair and then passes the
## FIRST pid for both, so requesting the second returns the first's data.
## Passing the requested pid would be a **correction**, and this project records
## a corrected server as a divergence rather than as parity.
const VISIT_DIVERGENCE := {
	"delivered": false,
	"surface": "get_neighbor_info, server.py:155-182",
	"discarded_pid_branch": "branch 2 tests membership in the two-pid pair and "
		+ "then passes the literal 100000030 for BOTH, so requesting 100000031 "
		+ "returns 100000030's data",
	"discarded_pid_reproduced": false,
	"why_not": "reproducing it would reproduce a defect; correcting it would "
		+ "be a divergence presented as parity",
	"failure_mode": "returns the empty string with HTTP 200 on failure, not an "
		+ "error object, so a typed client that parses it fails closed",
	"private_state_exposure": "a visit returns the visited player's COMPLETE "
		+ "privateState, which is the opposite of the roster and is recorded "
		+ "as the preserved server's behaviour rather than delivered",
	"map_number_default": "0 when map is falsy, so map=0 and an absent map are "
		+ "indistinguishable; a negative or out-of-range map is unguarded",
	"committed_visit_fixture": false,
	"prefix_is_not_identity": "branch 3 is user.startswith(100000), a ROUTING "
		+ "convention, independent of the quest membership test; no claim is "
		+ "made that the prefix identifies a quest map",
	"world_or_leaderboard_derived": false,
}


## The coverage limit of the executed evidence, asserted rather than noted.
##
## Both roster channels are backed by committed executed-legacy captures, which
## this line re-verifies leaf by leaf rather than re-deriving. But both captures
## ran with **no saves directory**, so the "other players" loop contributed
## nothing and every recorded observation is static-villages-only. The saves half
## of either channel is exercised here over crafted input only, and is recorded
## as crafted and never as executed parity.
const EXECUTED_EVIDENCE := {
	"bootstrap_roster_capture": "tests/fixtures/godot-compatibility-boot/steps/"
		+ "get_player_info/response.body",
	"flashvar_roster_capture": "tests/fixtures/godot-compatibility-boot/steps/"
		+ "play_page/response.body",
	"new_capture_fabricated": false,
	"saves_loop_half_exercised": false,
	"saves_loop_coverage_limit": "the committed captures ran with no saves "
		+ "directory, so the saves-loop half of BOTH channels has NO executed "
		+ "evidence and the recorded roster is static-villages-only",
	"visit_arm_covered": false,
	"order_covered": false,
	"order_limit": "the served order follows os.listdir() and is already "
		+ "recorded as environment-dependent; membership, entry count, carried "
		+ "key set and derived values are covered, and order is not",
}


## The refusal codes, one per malformed shape, so a refusal says WHICH shape
## failed instead of failing as an empty roster.
##
## Discriminated on shape before any value is read, and never by invoking a
## parser on a malformed document: `JSON.parse_string` emits an engine ERROR
## line for input it cannot parse, and `verify-boot.ps1` treats any line
## beginning `ERROR:` as a script error, so a refusal test that fed the parser a
## bad document would fail the whole battery while the suite itself passed.
const REFUSAL_CODES := {
	"payload_not_a_map": "the bootstrap player_info payload is not a map, so "
		+ "there is no roster location at all",
	"roster_absent": "the payload is a map with no neighbors key; a renamed "
		+ "service key lands here instead of yielding an empty roster",
	"roster_not_a_list": "the neighbors value is present but is not a list",
	"entry_not_an_object": "one roster entry is not a map, so the entry's "
		+ "carried and derived halves cannot be told apart",
}


## The relationship-shape tokens the committed investigation measured at ZERO
## code-only consumers across all eleven legacy modules, with the committed
## corpus value each one holds. Recorded as the BASIS of this module's
## refusals: membership is total, so nothing can select or remove it.
const RELATIONSHIP_TOKEN_CENSUS := [
	{"token": "neighborAssists", "code_only_occurrences": 0,
		"lives_at": "privateState.neighborAssists", "corpus_value": "{}",
		"corpus_documents": 33},
	{"token": "receivedAssists", "code_only_occurrences": 0,
		"lives_at": "maps[0].receivedAssists", "corpus_value": "{}",
		"corpus_documents": 33},
	{"token": "resourcesTraded", "code_only_occurrences": 0,
		"lives_at": "maps[0].resourcesTraded", "corpus_value": "{}",
		"corpus_documents": 33},
	{"token": "friendsHelpedCoveredItem", "code_only_occurrences": 0,
		"lives_at": "privateState.friendsHelpedCoveredItem",
		"corpus_value": "null", "corpus_documents": 33},
	{"token": "firstTimeAlliance", "code_only_occurrences": 0,
		"lives_at": "privateState.firstTimeAlliance", "corpus_value": "null",
		"corpus_documents": 33},
	{"token": "helpMap", "code_only_occurrences": 0,
		"lives_at": "privateState.helpMap", "corpus_value": "[]",
		"corpus_documents": 33},
	{"token": "assist", "code_only_occurrences": 0, "lives_at": "-",
		"corpus_value": "-", "corpus_documents": 0},
	{"token": "assists", "code_only_occurrences": 0, "lives_at": "-",
		"corpus_value": "-", "corpus_documents": 0},
	{"token": "helped", "code_only_occurrences": 0, "lives_at": "-",
		"corpus_value": "-", "corpus_documents": 0},
]


## What membership IS, recorded so the roster is not read as a relationship.
const MEMBERSHIP_RECORD := {
	"total": true,
	"unconditional": true,
	"directional": false,
	"consent_required": false,
	"lifecycle": "none: no add, no remove, no pending, no accepted",
	"selectable": false,
	"social_tables_reconciled": false,
	"why_not_reconciled": "the three committed social tables have 41 entries "
		+ "and ZERO legacy consumers, so there is nothing to reconcile a "
		+ "roster against; they are owned by godot-social-state",
	"flash_client_behaviour": "unverifiable from this oracle - absence of a "
		+ "server-side relationship says nothing about what the SWF held, "
		+ "which may have been entirely client-side",
}


## The ownership hand-off from `godot-social-state`, recorded so the corrected
## premise cannot drift back.
##
## That capability measured its own premise false: it had withheld the name
## `godot-friends` on the ground that the roster was absent. The roster is not
## absent, so the name is now used - while the ORIGINAL reasoning survives in
## amended form, because neither capability names a delivered surface after a
## social RELATIONSHIP.
const HANDOFF := {
	"owner_of_roster": "godot-friends",
	"owner_of_persisted_social_state": "godot-social-state",
	"original_premise": "a capability named godot-friends would claim exactly "
		+ "what this one measures to be absent",
	"premise_status": "measured FALSE by docs/legacy-m11-friends.md",
	"measuring_figures": "friends has 5 whole-file and 4 code-only occurrences "
		+ "across the eleven legacy modules, all 4 code-only in sessions.py",
	"surviving_reasoning": "neither capability names a surface after a social "
		+ "relationship, because none exists in the preserved server",
	"roster_entry_is_private_state": false,
	"moved_state_fields": 0,
}


## Every helper this module therefore does not provide.
##
## Matched case-insensitively and by SUBSTRING, because an exact-name check was
## measured in this project to miss a suffixed helper wearing a reserved name.
## `absent_because` records the measured reason for each, so the inventory
## cannot be padded with a name nobody can justify.
const ABSENT_HELPERS := [
	{"helper": "friend_of", "absent_because":
		"membership is total and unconditional; nothing selects a subset"},
	{"helper": "friendship_state", "absent_because":
		"no friendship record exists in any of the eleven legacy modules"},
	{"helper": "friend_request", "absent_because":
		"no friend command exists among the 63 named dispatcher branches"},
	{"helper": "accept_friend", "absent_because":
		"nothing is pending, because nothing is ever requested"},
	{"helper": "decline_friend", "absent_because":
		"there is no consent step to decline"},
	{"helper": "add_friend", "absent_because":
		"membership is a loop over every loaded village, not an insertion"},
	{"helper": "remove_friend", "absent_because":
		"no branch removes a village from the roster"},
	{"helper": "friendship_level", "absent_because":
		"friendsHelpedCoveredItem has zero occurrences and is uniformly null "
		+ "in 33 of 33 documents"},
	{"helper": "select_from_roster", "absent_because":
		"no roster entry is selectable; the projection exposes no index"},
	{"helper": "consent_of", "absent_because":
		"no consent or opt-out field is read by anything"},
	{"helper": "assist_neighbor", "absent_because":
		"neighborAssists has zero code-only occurrences and is uniformly {} "
		+ "in 33 of 33 documents"},
	{"helper": "gift_to", "absent_because":
		"no gift command exists in the dispatcher"},
	{"helper": "ally_of", "absent_because":
		"resourceAlliesMarket is a client-sent market resource, not a set of "
		+ "allies; no reader is claimed and it is owned by godot-social-state"},
	{"helper": "mutual_of", "absent_because":
		"the roster is not directional, so no two entries can be compared"},
	{"helper": "roster_order", "absent_because":
		"the preserved order follows os.listdir() and is already recorded as "
		+ "environment-dependent; no order is asserted or derived"},
	{"helper": "position_of", "absent_because":
		"the projection exposes no index, so no position can be read"},
	{"helper": "sort_roster", "absent_because":
		"ordering committed roster values would invent a rule the corpus "
		+ "cannot support"},
	{"helper": "best_neighbor", "absent_because":
		"comparing two roster entries by any field would be a rule nothing "
		+ "in the preserved server states"},
	{"helper": "closest_neighbor", "absent_because":
		"no distance, rank or score over roster entries exists anywhere"},
	{"helper": "rank_of", "absent_because":
		"there is zero arithmetic on any score-like value in the dispatcher"},
	{"helper": "visit_neighbor", "absent_because":
		"no committed fixture exercises a visit and the branch discards the "
		+ "requested pid; recorded in VISIT_DIVERGENCE and delivered as nothing"},
	{"helper": "visit_state", "absent_because":
		"world_id and worldChange are carried but never read; no visit "
		+ "concept is derived"},
	{"helper": "neighbor_session", "absent_because":
		"the legacy resolver reaches saves then quests then villages and "
		+ "returns None; it is a session resolver, not a roster concept"},
	{"helper": "world_of", "absent_because":
		"world_id is carried in 33 of 33 documents with zero occurrences"},
	{"helper": "leaderboard_of", "absent_because":
		"the token occurs zero times across all eleven legacy modules"},
	{"helper": "flashvar_channel", "absent_because":
		"the friendsInfo FlashVar is a preserved-client transport, not a "
		+ "modern-runtime surface; its content is reported, not delivered"},
]


## No endpoint, route, or intent is delivered for the roster (design D1).
##
## `/v0/bootstrap` already serves it. An empty list is the load-bearing value
## here: any future route addition must make this fail rather than slip past it.
const DELIVERED_ROUTES := []


## Project a bootstrap `player_info` payload.
##
## `payload` is `PlayerInfoPayload.raw` — an opaque Dictionary at
## `boot_data.gd:190`. The roster is read from `payload[ROSTER_KEY]`, so the
## caller must hand over the DESCENDED payload: the legacy fixture document
## nests `neighbors` at its top level while the v0 envelope nests it at
## `player_info.neighbors`. Handing over the whole envelope is therefore not a
## silent empty roster — it is the explicit `roster_absent` refusal.
static func project(payload: Variant = null) -> RosterProjection:
	return RosterProjection.new(payload)


## One roster entry: the carried `playerInfo` half and the derived `maps[0]`
## half, kept apart because which half came from where is what a reader needs.
##
## Read-only throughout. There is no setter, no index and no ordering accessor.
class RosterEntry extends RefCounted:
	var _pid: String = ""
	var _carried: Dictionary = {}
	var _derived: Dictionary = {}
	## The entry map exactly as the service sent it, held by reference and
	## never written through. Kept so the privateState intersection below can
	## be a MEASUREMENT rather than a tautology.
	var _raw: Dictionary = {}

	func _init(entry_map: Dictionary) -> void:
		_raw = entry_map
		for name: Variant in CARRIED_PLAYER_INFO_KEYS:
			var key: String = str(name)
			if entry_map.has(key):
				_carried[key] = entry_map[key]
		for name: Variant in DERIVED_MAP_FIELDS:
			var key2: String = str(name)
			if entry_map.has(key2):
				_derived[key2] = entry_map[key2]
		_pid = str(_carried.get("pid", _derived.get("pid", "")))

	## The entry's own pid, from the carried `playerInfo` half.
	func pid() -> String:
		return _pid

	## Every key this entry carries, carried half then derived half.
	func key_names() -> Array:
		var out: Array = []
		for name: Variant in CARRIED_PLAYER_INFO_KEYS:
			if _carried.has(str(name)):
				out.append(str(name))
		for name2: Variant in DERIVED_MAP_FIELDS:
			if _derived.has(str(name2)):
				out.append(str(name2))
		return out

	## How many keys the entry really carries, which the committed capture
	## records as eighteen and which a renamed or dropped key would change.
	func key_count() -> int:
		return key_names().size()

	## True when this entry carries the named key, in either half.
	func has_key(name: String) -> bool:
		return _carried.has(name) or _derived.has(name)

	## Every key the entry's own map really carries, whether or not either
	## declared half names it, sorted.
	##
	## This is what makes `private_state_key_intersection` a measurement rather
	## than a tautology. `key_names()` reports only the eighteen declared names,
	## so intersecting THAT against the recording player's document would be
	## empty by construction - the projection could not widen without widening
	## the tables first, which is exactly the edit this has to catch. Reading
	## the entry's real keys means a key the projection does not declare still
	## shows up here, so a roster that began carrying a private progress key
	## is caught by the intersection instead of being invisible to it.
	func all_key_names() -> Array:
		var out: Array = []
		for key: Variant in _raw.keys():
			out.append(str(key))
		out.sort()
		return out

	## A carried `playerInfo` value, or `null` when this entry did not carry it.
	func carried(name: String) -> Variant:
		return _carried.get(name, null)

	## A derived `maps[0]` value, or `null` when this entry does not carry it.
	func derived(name: String) -> Variant:
		return _derived.get(name, null)

	## The carried half's key names this entry really has.
	func carried_key_names() -> Array:
		var out: Array = []
		for name: Variant in CARRIED_PLAYER_INFO_KEYS:
			if _carried.has(str(name)):
				out.append(str(name))
		return out

	## The derived half's key names this entry really has.
	func derived_key_names() -> Array:
		var out: Array = []
		for name: Variant in DERIVED_MAP_FIELDS:
			if _derived.has(str(name)):
				out.append(str(name))
		return out

	## The one-field view: which half a key came from, its recorded value, and
	## whether the entry really carried it. An absent key stays distinguishable
	## from a key recorded as `null`, and no uniform corpus value is ever
	## substituted for a missing one.
	func field(name: String) -> Variant:
		var in_carried: bool = _carried.has(name)
		var in_derived: bool = _derived.has(name)
		return {
			"name": name,
			"origin": "carried_player_info" if in_carried else (
				"derived_from_maps_0" if in_derived else "absent"),
			"present": in_carried or in_derived,
			"recorded_value": _carried.get(name, _derived.get(name, null)),
		}


## The roster projection: an unordered set of entries plus its refusal state.
##
## Holds no mutating accessor and no mutating path — this capability adds no
## route (design D1), so there is nothing here a caller could write through.
class RosterProjection extends RefCounted:
	var _ok: bool = false
	var _code: String = ""
	var _message: String = ""
	var _entries: Array = []

	func _init(payload: Variant = null) -> void:
		if typeof(payload) != TYPE_DICTIONARY:
			_refuse("payload_not_a_map")
			return
		var source: Dictionary = payload
		if not source.has(ROSTER_KEY):
			_refuse("roster_absent")
			return
		var roster: Variant = source[ROSTER_KEY]
		if typeof(roster) != TYPE_ARRAY:
			_refuse("roster_not_a_list")
			return
		var built: Array = []
		for value: Variant in (roster as Array):
			if typeof(value) != TYPE_DICTIONARY:
				_refuse("entry_not_an_object")
				return
			built.append(RosterEntry.new(value))
		_entries = built
		_ok = true

	func _refuse(code: String) -> void:
		_ok = false
		_code = code
		_message = str((REFUSAL_CODES as Dictionary).get(code, ""))

	## True when the roster projected; false on every refusal.
	func ok() -> bool:
		return _ok

	## The refusal code, or `""` when the projection succeeded.
	func refusal_code() -> String:
		return _code

	## Why this shape failed, in the module's own words.
	func refusal_message() -> String:
		return _message

	## How many entries the roster holds. A count, never an index.
	func entry_count() -> int:
		return _entries.size()

	## Every entry's pid, in the order the service served them.
	##
	## The order is reported for convenience and is **NOT** claimed: it follows
	## `os.listdir()` and is already recorded as environment-dependent.
	func pids() -> Array:
		var out: Array = []
		for entry: Variant in _entries:
			out.append((entry as RosterEntry).pid())
		return out

	## True when the roster contains this pid.
	func has_pid(pid: String) -> bool:
		return entry(pid) != null

	## The entry with this pid, or `null`. Lookup by identity, never by index.
	func entry(pid: String) -> Variant:
		for candidate: Variant in _entries:
			if (candidate as RosterEntry).pid() == pid:
				return candidate
		return null

	## The carried half's key names, taken from the first entry that projects.
	##
	## Reported as one roster-wide list because the committed capture records
	## all five entries carrying the same eighteen keys; a roster whose entries
	## disagreed would show a shorter list here rather than being hidden.
	func carried_key_names() -> Array:
		if _entries.is_empty():
			return []
		return (_entries[0] as RosterEntry).carried_key_names()

	## The derived half's key names, on the same terms as the carried half.
	func derived_key_names() -> Array:
		if _entries.is_empty():
			return []
		return (_entries[0] as RosterEntry).derived_key_names()

	## Every key name the first entry carries, in one list.
	func entry_key_names() -> Array:
		if _entries.is_empty():
			return []
		return (_entries[0] as RosterEntry).key_names()

	## How many keys the first entry carries.
	func entry_key_count() -> int:
		if _entries.is_empty():
			return 0
		return (_entries[0] as RosterEntry).key_count()

	## Per-entry intersection of this roster's keys against the RECORDING
	## player's own keys, reported rather than asserted empty.
	##
	## `recording_private_state` is the recording player's `privateState` map.
	## Each row is one entry's pid with the keys the two documents share. The
	## committed capture records an EMPTY intersection for all five entries,
	## and this reports what was actually found instead of assuming it — read
	## over each entry's REAL keys (see `all_key_names()`), so the emptiness is
	## a measurement of the served data rather than a consequence of the
	## eighteen-key table.
	func private_state_key_intersection(recording_private_state: Variant) -> Array:
		var recording_keys: Array = []
		if typeof(recording_private_state) == TYPE_DICTIONARY:
			recording_keys = (recording_private_state as Dictionary).keys()
		var out: Array = []
		for entry: Variant in _entries:
			var shared: Array = []
			for name: String in (entry as RosterEntry).all_key_names():
				if recording_keys.has(name):
					shared.append(name)
			out.append({
				"pid": (entry as RosterEntry).pid(),
				"shared": shared,
			})
		return out

	## True when any entry shares a key with the recording player's document.
	##
	## Reported as a measured consequence of the intersection above rather than
	## as an independently asserted absence.
	func leaks_recording_private_state(recording_private_state: Variant) -> bool:
		for row: Variant in private_state_key_intersection(recording_private_state):
			if ((row as Dictionary)["shared"] as Array).size() != 0:
				return true
		return false
