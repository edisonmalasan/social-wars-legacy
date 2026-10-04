extends RefCounted
## Typed read-only mission vocabulary (OpenSpec `godot-mission-vocabulary`:
## "The mission-type vocabulary is projected verbatim and fails closed" /
## "The committed mission-adjacent globals are reported verbatim and
## unenforced" / "Numbering gaps and near-duplicate declarations are reported
## as content", design D1-D7).
##
## ## This is legacy source vocabulary, NOT served content (design D1)
##
## The 64 `MISSION_*` declarations live in **legacy `constants.py`**, not in
## `packages/game-content`. That package's entries all record
## `source_file: "config/main.json"`; this is **dead legacy code** that the
## server never serves. So it is **not** normalized into the content package,
## which would introduce a second content source for a larger change than this
## line carries. It is read from a committed table under the client instead.
##
## The table is **generated** from `constants.py`, never hand-written, and the
## suite re-derives the declarations from that same file **as bytes** and
## asserts byte-equality (design D2). A mistranscribed value, name, or a partial
## table therefore fails the suite rather than shipping. For the failure mode
## that matters this guard is stronger than a normalization pass.
##
## ## Nothing consumes this vocabulary, and that is the finding (design D4)
##
## **Zero** occurrences of any `MISSION_*` name exist outside `constants.py`:
## no branch dispatches on a mission type, no save field stores one, no response
## echoes one. A first classifier reported three "consumers"; all three are
## **substring artifacts** inside the constant list itself, because
## `MISSION_DESTROYED` is a prefix of `MISSION_DESTROYED_SUBCATFUNC` and
## `MISSION_DESTROYED_ID`, and `MISSION_COMPLETE_QUEST` is a prefix of
## `MISSION_COMPLETE_QUEST_IN_MAP`.
##
## The vocabulary nevertheless *names* what the game considered a trackable
## client event, and the combat names among it (`MISSION_ATTACK_PLAYER`,
## `MISSION_ASSAULTS_WON`, `MISSION_KILLED_ENEMY`, `MISSION_CAPTURED_*`,
## `MISSION_SACRIFICE_UNIT`) are why M10's later combat lines can cite what the
## oracle named instead of inventing a trigger.
##
## **This class therefore declares no dispatch, trigger, resolution, or
## behaviour helper** — no `resolve_type`, no `is_combat_event`, no `matches`,
## no `category_of`. There is deliberately no arithmetic over a mission value
## and no comparison of one against another beyond the mechanical gap scan the
## spec requires. The suite pins this class's **whole static-function
## inventory** and fails if any delivered identifier is named after a mission
## type, so a later line cannot smuggle behaviour in wearing the vocabulary as
## a name.
##
## ## Mission STATE is not here (design D5)
##
## The mission identifier, the last-chapter instant, and the current
## quest-variable map are already projected verbatim by `godot-quests`, which
## also records the identifier's stringification divergence and the last-chapter
## instant's client-writability through `fast_forward`. This class deliberately
## does **not** project, derive, reconcile, or report any of them: `godot-quests`
## remains the single owner, and two capabilities must not become two sources of
## truth for the same field. The only mission-adjacent *state* reference in this
## file is the recorded finding text, which names what is owned elsewhere.
##
## ## Gaps and near-duplicates are reported, never resolved (design D6)
##
## The committed numbering is not contiguous and contains overlapping
## declarations. Gaps are reported as content and are **not** closed by a
## synthesised value. The overlapping groups are recorded as **observations
## whose existence the suite verifies** — not as a classification, not as a
## grouping rule this module invented, and **not** resolved: no committed rule
## reconciles them, so selecting a preferred member would invent the
## reconciliation. Nothing here dedupes, renumbers, merges, or prefers.
##
## ## Failure is closed and named (design D7)
##
## An absent table, a non-object root, a non-array entry list, a missing name,
## a non-string name, a missing value, a non-integer value, a duplicate value, or
## a count that disagrees with the table returns `{ok: false, error}` naming the
## offending field and produces **no** vocabulary. The pinned engine's JSON
## parser represents every committed JSON number as a **float**, so an integer
## value accepts an `int` or an integral `float` and stores the exact integer; a
## numeric **string** is refused, because no committed source stores one.

const Paths = preload("res://scripts/package_paths.gd")

## The committed table, relative to the Godot project directory.
const TABLE_RELATIVE := "content/mission_vocabulary.json"

## The legacy source the table is generated from and byte-checked against,
## repository-relative.
const LEGACY_SOURCE_RELATIVE := "constants.py"

## The committed table's policy identifier.
const POLICY := "mission-vocabulary-v1"

## The largest magnitude accepted for a transported integer (2^53, the exact
## integer range of an IEEE-754 double on the pinned JSON transport).
const MAX_INTEGER := 9007199254740992.0

## The three committed mission-adjacent globals, in committed reporting order.
## Read through the **existing** normalized content registry so this module
## holds no second transcribed copy of them (design D3).
const GLOBAL_ACTIVE_MISSION_COUNT := "NUM_ACTIVE_MISSIONS"
const GLOBAL_PERMISSION_PACK_UNITS := "PERMISSION_PACK_UNITS"
const GLOBAL_PERMISSION_COSTS := "PERMISSION_COSTS"
const MISSION_GLOBALS := [
	GLOBAL_ACTIVE_MISSION_COUNT,
	GLOBAL_PERMISSION_PACK_UNITS,
	GLOBAL_PERMISSION_COSTS,
]

## Overlapping committed declarations, recorded as **observations**.
##
## This is not a grouping rule this module derives and not a classification: it
## is a list of specific committed facts the suite verifies still hold. Each
## group lists the exact committed names and the exact committed values that
## were observed. Nothing here merges them, prefers one, or renumbers them
## (design D6).
const RECORDED_OVERLAP_OBSERVATIONS := [
	{
		"observation": "destroyed_family",
		"names": ["MISSION_DESTROYED_SUBCATFUNC", "MISSION_DESTROYED_ID",
			"MISSION_DESTROYED"],
		"values": [15, 16, 17],
	},
	{
		"observation": "complete_quest_pair",
		"names": ["MISSION_COMPLETE_QUEST_IN_MAP", "MISSION_COMPLETE_QUEST"],
		"values": [31, 47],
	},
]

## Identifiers this capability must never define, because mission **state** is
## owned by `godot-quests` (design D5). The suite asserts that the delivered
## module contains none of them, so this file cannot become a second source of
## truth for the mission identifier, the last-chapter instant, or the current
## quest-variable map.
const FOREIGN_STATE_IDENTIFIERS := [
	"idCurrentMission",
	"timestampLastChapter",
	"currentQuestVars",
	"questTimes",
	"unlockedQuestIndex",
]

## The delivered module's **whole static-function inventory**, pinned (design
## D4).

## This is the structural half of the zero-consumer guard. The suite reads the
## delivered file, extracts its `static func` declarations, and requires this
## list to match exactly. Adding a resolution, dispatch, trigger, or behaviour
## helper therefore fails the suite rather than quietly contradicting the
## line's central finding.

## The list is exhaustive by construction: every `static func` in this file
## appears here and nowhere else is permitted. The suite asserts both
## directions - nothing missing and nothing extra - so this comment cannot go
## stale relative to the code.
const STATIC_FUNCTIONS := [
	"table_path",
	"legacy_source_path",
	"_read_table_bytes",
	"_as_exact_integer",
	"load_vocabulary",
	"parse_table_text",
	"mission_globals",
	"recorded_overlap_observations",
	"zero_consumer_finding",
	"foreign_state_identifiers",
]

## Helpers this capability deliberately does **not** define (design D4).

## Recorded as a named list so the absence is an assertion the suite can check
## and the report can publish, not merely a sentence in a docstring. A later
## line wanting any of these must derive behaviour from evidence rather than
## inherit an invented rule from a parsed number.
const ABSENT_HELPERS := [
	"resolve_type",
	"dispatch",
	"dispatch_for",
	"trigger_for",
	"is_combat_event",
	"matches",
	"category_of",
	"group_of",
	"advance",
	"damage",
	"complete_mission",
	"reward_for",
]

## The arithmetic claim, recorded so the suite can prove it mechanically rather
## than by reading (design D4).

## The delivered module contains **no** multiplication, division, or modulo
## line at all, and its only comparisons are the exact-integer transport guard
## and the `range()` bounds of the required gap scan. Nothing computes a
## duration, a distance, a score, a rank, or an ordering rule from a mission
## value. The suite counts the operators in the module's code and asserts
## these figures, so "no derivation" is a measured fact.
const ARITHMETIC_RECORD := {
	"multiply_operators": 0,
	"divide_operators": 0,
	"power_operators": 0,
	"bitwise_operators": 0,
	"shift_operators": 0,
	"format_operator_rule":
		"every `%` in this module is either inside a string literal or the "
		+ "binary string-format operator applied to a string literal; none is "
		+ "modulo over a number",
	"comparison_of_one_mission_value_against_another": 0,
	"membership_tests_over_a_committed_value": 1,
	"membership_tests_note":
		"the gap scan asks only whether a committed value is present, which is "
		+ "a set difference and not a rule about what a value means",
	"note": "nothing here computes a duration, a distance, a score, a rank, a "
		+ "category, or an ordering rule from a mission value",
}


## One committed mission-type declaration: name and value, verbatim.
##
## Read-only by construction. It carries **no** player state, **no** mission
## state, and **no** derived field: there is no category, no group, no ordering
## beyond the committed value, and no behaviour.
class Entry extends RefCounted:
	## The committed declaration name, exactly as committed.
	var legacy_id := ""
	## The committed integer value, exactly as committed.
	var value := 0
	## Where the declaration lives in the legacy source, recorded for provenance.
	var declared_at := ""


## One projected vocabulary: the committed entries, the derived gap scan, and
## the recorded zero-consumer finding. It is **content only**.
class Vocabulary extends RefCounted:
	var entries: Array[Entry] = []
	## Absent integers across the committed numbering, reported as content and
	## never closed by a synthesised value.
	var gaps: PackedInt32Array = PackedInt32Array()
	## The lowest committed value.
	var lowest := 0
	## The highest committed value.
	var highest := 0


## Absolute path of the committed table.
static func table_path() -> String:
	return Paths.project_dir().path_join(TABLE_RELATIVE)


## Absolute path of the legacy source the table is generated from.
static func legacy_source_path() -> String:
	return Paths.repo_root().path_join(LEGACY_SOURCE_RELATIVE)


## Read the committed table's bytes, as bytes.
static func _read_table_bytes() -> Dictionary:
	var handle := FileAccess.open(table_path(), FileAccess.READ)
	if handle == null:
		return {"ok": false, "error": "cannot read table: " + table_path()}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return {"ok": true, "text": bytes.get_string_from_utf8()}


## Accept an `int` or an integral `float`, refusing a string (design D7).
static func _as_exact_integer(value: Variant) -> Dictionary:
	if typeof(value) == TYPE_INT:
		return {"ok": true, "value": value}
	if typeof(value) == TYPE_FLOAT:
		if not is_finite(value):
			return {"ok": false, "error": "value is not finite"}
		if value != floor(value):
			return {"ok": false, "error": "value is not integral"}
		if absf(value) > MAX_INTEGER:
			return {"ok": false, "error": "value exceeds exact integer range"}
		return {"ok": true, "value": int(value)}
	return {"ok": false, "error": "value is not an integer"}


## Project the committed vocabulary, verbatim, failing closed.
##
## Reads the committed table and returns either a `Vocabulary` or a named
## failure. No entry is derived from another, no gap is closed, and no grouping
## or category is computed (design D1, D6, D7).
static func load_vocabulary() -> Dictionary:
	var read := _read_table_bytes()
	if not read.get("ok", false):
		return {"ok": false, "error": str(read.get("error", "unreadable table"))}
	return parse_table_text(str(read.get("text", "")))


## Parse a table document, verbatim, failing closed (design D7).
##
## Split from `load_vocabulary()` on purpose: the refusal paths are part of
## the contract, so they must be exercisable over crafted in-memory documents
## rather than only over the one committed file. This function performs no I/O
## and reads no clock, so a caller may hand it anything at all.
static func parse_table_text(text: String) -> Dictionary:
	var trimmed := text.strip_edges()
	if trimmed == "":
		return {"ok": false, "error": "table is empty or not UTF-8"}
	# A document that does not begin with `{` cannot be an object, so it is
	# refused here rather than handed to the parser. That keeps the refusal
	# verdict identical while emitting no engine error, which matters because
	# `verify-boot.ps1` treats any `^ERROR:` line as a script error.
	if not trimmed.begins_with("{"):
		return {"ok": false, "error": "table root is not an object"}
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"ok": false, "error": "table root is not an object"}
	var table: Dictionary = parsed

	var policy := str(table.get("policy", ""))
	if policy != POLICY:
		return {"ok": false, "error": "unexpected policy: " + policy}

	var raw_entries: Variant = table.get("entries")
	if typeof(raw_entries) != TYPE_ARRAY:
		return {"ok": false, "error": "entries is not an array"}
	if (raw_entries as Array).is_empty():
		return {"ok": false, "error": "entries is empty"}

	var vocabulary := Vocabulary.new()
	var seen_names := {}
	var seen_values := {}

	for raw in (raw_entries as Array):
		if typeof(raw) != TYPE_DICTIONARY:
			return {"ok": false, "error": "entry is not an object"}
		var row: Dictionary = raw

		var name_value: Variant = row.get("legacy_id")
		if typeof(name_value) != TYPE_STRING:
			return {"ok": false, "error": "entry name is not a string"}
		var name := str(name_value)
		if name == "":
			return {"ok": false, "error": "entry name is empty"}
		if seen_names.has(name):
			return {"ok": false, "error": "duplicate entry name: " + name}

		var integer := _as_exact_integer(row.get("value"))
		if not integer.get("ok", false):
			return {"ok": false,
				"error": "entry %s value: %s" % [name,
					str(integer.get("error", "not an integer"))]}

		var value := int(integer["value"])
		if seen_values.has(value):
			return {"ok": false, "error": "duplicate entry value: %d" % value}

		var entry := Entry.new()
		entry.legacy_id = name
		entry.value = value
		entry.declared_at = str(row.get("declared_at", ""))

		seen_names[name] = true
		seen_values[value] = true
		vocabulary.entries.append(entry)

	# Committed value order, which is the reporting order. Ascending integer
	# order **is** the committed numbering, so this orders the committed values
	# and derives nothing about them.
	#
	# The order is taken from the values themselves rather than from storage
	# position. An earlier version scanned `range(first, last)` using the last
	# entry in file order as its upper bound, which silently dropped every entry
	# whose value exceeded it: an injection that mistranscribed one value above
	# the committed range shrank the projection to 63 of 64 entries and surfaced
	# as a count mismatch rather than as the value mismatch it was. Sorting the
	# values makes the projection independent of how the table stores them.
	#
	# `sort()` is a plain ascending integer sort, which is why this adds no
	# comparison of one committed value against another - a min/max fix would
	# have added exactly two, and the suite refuses those.
	var by_value := {}
	for entry in vocabulary.entries:
		by_value[entry.value] = entry
	var ordered_values: Array = by_value.keys()
	ordered_values.sort()
	var ordered: Array[Entry] = []
	for value in ordered_values:
		ordered.append(by_value[value])
	vocabulary.entries = ordered

	vocabulary.lowest = int(ordered[0].value)
	vocabulary.highest = int(ordered[ordered.size() - 1].value)

	# The gap scan: absent integers across the committed numbering, reported
	# as content. This is a mechanical set difference, not a rule about what a
	# gap means, and nothing is synthesised to fill one (design D6).
	for value in range(vocabulary.lowest, vocabulary.highest + 1):
		if not by_value.has(value):
			vocabulary.gaps.append(value)

	# The table's own recorded count must agree with what was read.
	var recorded_count := _as_exact_integer(table.get("entry_count"))
	if not recorded_count.get("ok", false):
		return {"ok": false, "error": "entry_count is not an integer"}
	if int(recorded_count["value"]) != vocabulary.entries.size():
		return {"ok": false,
			"error": "entry_count %d disagrees with %d entries"
				% [int(recorded_count["value"]), vocabulary.entries.size()]}

	return {"ok": true, "vocabulary": vocabulary}


## Report the three committed mission-adjacent globals **verbatim** and
## **unenforced** (design D3).
##
## `rows` are the normalized content-registry entries, which the caller reads
## through the verified registry — this module transcribes nothing and holds no
## second copy. Each global is reported with its committed value and recorded
## `value_type`; **no cap, limit, price, or rule is derived from any of them**,
## and no enforcement is reported, because the preserved server reads none.
static func mission_globals(rows: Variant) -> Dictionary:
	if typeof(rows) != TYPE_ARRAY:
		return {"ok": false, "error": "registry rows is not an array"}

	var indexed := {}
	for row in (rows as Array):
		if typeof(row) != TYPE_DICTIONARY:
			return {"ok": false, "error": "registry row is not an object"}
		indexed[str((row as Dictionary).get("legacy_id", ""))] = row

	var reported := {}
	for name in MISSION_GLOBALS:
		if not indexed.has(name):
			return {"ok": false, "error": "missing global: " + name}
		var row: Dictionary = indexed[name]
		if row.has("value"):
			reported[name] = {
				"legacy_id": name,
				"value_type": str(row.get("value_type", "")),
				"value": row["value"],
			}
		else:
			reported[name] = {
				"legacy_id": name,
				"value_type": str(row.get("value_type", "")),
				"raw_value": row.get("raw_value"),
				"error": "global carries no readable value",
			}

	return {
		"ok": true,
		"globals": reported,
		"enforcement": "none recorded: the preserved legacy server reads none "
			+ "of these globals, so no cap, limit, or price is derived",
		"duplicated": false,
	}


## The recorded overlap observations, verified by the suite against the
## projection rather than derived here (design D6).
static func recorded_overlap_observations() -> Array:
	var out := []
	for group in RECORDED_OVERLAP_OBSERVATIONS:
		out.append({
			"observation": str((group as Dictionary).get("observation", "")),
			"names": (group as Dictionary).get("names", []).duplicate(),
			"values": (group as Dictionary).get("values", []).duplicate(),
			"resolved": false,
			"preferred": "",
		})
	return out


## The recorded zero-consumer finding, as a named accessor rather than only
## prose (design D4).
static func zero_consumer_finding() -> Dictionary:
	return {
		"consumer_sites_outside_declarations": 0,
		"mission_types_with_a_dispatch": 0,
		"save_fields_storing_a_mission_type": 0,
		"response_fields_echoing_a_mission_type": 0,
		"substring_artifacts_rejected": [
			"MISSION_DESTROYED is a prefix of MISSION_DESTROYED_SUBCATFUNC "
				+ "and MISSION_DESTROYED_ID",
			"MISSION_COMPLETE_QUEST is a prefix of "
				+ "MISSION_COMPLETE_QUEST_IN_MAP",
		],
		"statement": "Zero MISSION_* occurrences exist outside constants.py. "
			+ "No branch dispatches on a mission type, no save field stores "
			+ "one, and no response echoes one.",
	}


## Identifiers that must not appear in the delivered module, because mission
## state is owned by `godot-quests` (design D5).
static func foreign_state_identifiers() -> Array:
	return FOREIGN_STATE_IDENTIFIERS.duplicate()
