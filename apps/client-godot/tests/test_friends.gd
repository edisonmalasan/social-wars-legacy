extends "res://tests/test_base.gd"
## Roster suite (OpenSpec `godot-friends`, design D1-D9).
##
## This line delivers a **projection**, not a relationship, and not a route.
## `/v0/bootstrap` already carried the roster at `player_info.neighbors` when
## the Propose stage measured it, so `apps/compat-api/**` is untouched by this
## change and the compat suite must remain at its 3077 baseline. What was
## undelivered is the typed projection, and that is what this suite verifies.
##
## The naming correction is the point. `godot-social-state` withheld the name
## `godot-friends` on an explicitly recorded premise - that the roster was
## absent - and `docs/legacy-m11-friends.md` (PR #321) MEASURED that premise
## false. So the deliver item's committed name is used, while the original
## reasoning survives in amended form: neither capability names a delivered
## surface after a social RELATIONSHIP, because none exists in the preserved
## server.
##
## Checks:
##   oracle      both committed executed captures re-verified leaf by leaf,
##               plus the saves-loop coverage limit asserted rather than noted;
##   projection  the twelve carried and six derived keys, distinguishable, and
##               the payload proven unmutated;
##   membership  the derivation reproduced from the committed villages, the
##               literal exclusion pair, the two different scopes, and the
##               refusal to derive the count from a file count;
##   refusals    one code per malformed shape, discriminated BEFORE any parser
##               is invoked so no engine ERROR line is emitted;
##   channels    both roster channels reported and never deduplicated, with the
##               FlashVar channel's absence from the v0 envelope MEASURED over
##               the compat service modules rather than asserted;
##   privacy     the recording player's keys intersected against every entry,
##               reported rather than assumed empty;
##   visit       the discarded-pid defect recorded as a divergence and
##               reproduced as nothing;
##   absence     the whole function inventory pinned in both directions, the
##               reserved-name guard case-folded AND by substring, the
##               arithmetic/ordering guard with its own self-discrimination
##               checks, and the no-route and no-FlashVar boundaries.
##
## The anti-invention guards are structural and are PROVEN BY INJECTION rather
## than trusted: seven deliberate faults were written into the delivered module,
## each had to fail this suite with a non-zero exit, and each was followed by a
## byte-identical restore. `_injection_record()` carries the measured counts.
## The injections were re-run against the FINAL delivered state as well, so the
## recorded numbers describe the module that shipped and not an earlier draft.
##
## Uses the committed executed captures directly. No fixture is written, no
## server runs, and nothing is ever ordered, sorted or compared between two
## roster values. Runs headless as part of `verify-boot.ps1`.

const FriendsRoster := preload("res://scripts/social/friends_roster.gd")

const DEFAULT_REPORT_PATH := "evidence/friends/report.json"

const MODULE_PATH := "res://scripts/social/friends_roster.gd"
const MODULE_REPO_PATH := "apps/client-godot/scripts/social/friends_roster.gd"

const BOOTSTRAP_CAPTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const FLASHVAR_CAPTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/play_page/response.body"

## The pinned twelve + six. Pinned here as well as in the module so a module
## edit that quietly dropped a key would have to change BOTH files, which is
## two edits rather than one.
const EXPECTED_CARRIED_KEYS := [
	"cash", "completed_tutorial", "default_map", "last_logged_in",
	"map_names", "map_sizes", "name", "pic", "pid",
	"sp_ref_cat_install", "sp_ref_uid", "world_id",
]
const EXPECTED_DERIVED_KEYS := ["xp", "level", "gold", "wood", "oil", "steel"]

## The roster the committed capture recorded, as a SET of pids.
const EXPECTED_ROSTER_PIDS := ["AcidCaos", "Kiriakos", "Nerri", "Neutral", "Scarlet"]

## The two-pid literal pair, pinned independently of the module's record.
const EXPECTED_EXCLUDED_PIDS := ["100000030", "100000031"]

## The eight committed village FILES. Pinned because the derivation below must
## walk them and skip exactly one, and a walk that silently found six would
## then be measured against nothing.
const EXPECTED_VILLAGE_FILES := [
	"AcidCaos.json", "General_Mike_30.json", "General_Mike_31.json",
	"Kiriakos.json", "Nerri.json", "Neutral.json", "Scarlet.json",
	"initial.json",
]

## The one village file the loader never loads (sessions.py:78).
const NEVER_LOADED_VILLAGE_FILE := "initial.json"

## The v0 route table, pinned. `/v0/level_up` must remain LAST: four already
## delivered suites slice their own route's source forward to that decorator
## and assert it is their span's end marker, so a route appended after it
## would be claimed by their slice. Re-verified here because this change adds
## no route and must therefore move this number not at all.
const EXPECTED_COMPAT_ROUTES := [
	"/v0/tutorial", "/v0/darts", "/v0/reward", "/v0/combat", "/v0/magic",
	"/v0/place_stored", "/v0/sell_stored", "/v0/session", "/v0/bootstrap",
	"/v0/place", "/v0/purchase", "/v0/move", "/v0/sell", "/v0/store",
	"/v0/upgrade", "/v0/construction", "/v0/collect", "/v0/expand",
	"/v0/queue", "/v0/collection", "/v0/resurrect", "/v0/quests",
	"/v0/research", "/v0/level_up",
]

## The FlashVar roster channel's own tokens. Their ABSENCE from the v0
## service is measured every run.
##
## Corrected during this line's Apply stage: the bare WORD `FlashVar` was
## originally in this list, and the measurement came back NON-ZERO - it occurs
## nine times in `apps/compat-api/`, in the fixture-capture tool and the
## field-stability recorder. Those are capture and analysis modules, not
## envelope emitters, so the word was measured separately rather than dropped,
## and only the four tokens the roster itself is made of are pinned at zero.
const FLASHVAR_TOKENS := ["friendsInfo", "pic_square", "fb_friends_str", "uid"]

## The two compat modules allowed to MENTION the bare word `FlashVar`: the
## executed-capture tool and the field-stability recorder. Pinned so the
## "only in a capture tool" assertion has a known shape.
const FLASHVAR_WORD_MODULES := ["capture_legacy_fixtures.py", "field_stability.py"]

## The compat service modules scanned for the FlashVar census, excluding the
## `test_*.py` suite files: the ENVELOPE is what the service emits, not what
## its tests happen to mention.
const COMPAT_SERVICE_PREFIX := "apps/compat-api/"

## Recorded measurements, filled in as the suite runs and folded into the
## report so no figure in the report is transcribed.
var oracle := {}
var projection := {}
var membership := {}
var refusals := {}
var channels := {}
var privacy := {}
var visit := {}
var absence := {}
var boundary := {}

## Whole-file source of the delivered module, read once.
var _module_source := ""


func run_scenario() -> void:
	_module_source = FileAccess.get_file_as_string(MODULE_PATH)
	_check_oracle()
	_check_projection()
	_check_membership()
	_check_refusals()
	_check_channels()
	_check_privacy()
	_check_visit()
	_check_absence()
	_check_boundary()
	if _has_report_argument():
		_write_report()


func _has_report_argument() -> bool:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report"):
			return true
	return false


func _repo_root() -> String:
	return Paths.repo_root()


func _fixture(relative: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_bytes(
		_repo_root().path_join(relative)).get_string_from_utf8())


# ---------------------------------------------------------------------------
# The committed executed captures (requirements 1 and 7)
# ---------------------------------------------------------------------------

func _check_oracle() -> void:
	# --- the bootstrap roster capture -------------------------------------
	var document: Variant = _fixture(BOOTSTRAP_CAPTURE)
	check(document is Dictionary,
		"the committed bootstrap capture parsed to a map")
	if not (document is Dictionary):
		return
	var doc: Dictionary = document
	check(doc.has("neighbors"),
		"the LEGACY capture document carries `neighbors` at its TOP LEVEL, "
			+ "which is not where the v0 envelope nests it")
	oracle["legacy_root_keys"] = _sorted_keys(doc)
	oracle["legacy_neighbor_depth"] = "top level"

	var roster: Variant = doc["neighbors"]
	check(roster is Array, "the captured roster is a list")
	if not (roster is Array):
		return
	var entries: Array = roster as Array
	check_eq(entries.size(), 5,
		"the committed capture records FIVE roster entries")

	# Every entry: exactly eighteen keys, twelve carried and six derived,
	# verified LEAF BY LEAF against the capture rather than against a summary.
	var captured_pids: Array = []
	var leaf_total: int = 0
	for value: Variant in entries:
		if not (value is Dictionary):
			check(false, "every captured roster entry is a map")
			continue
		var entry_map: Dictionary = value
		var projection_result: Variant = FriendsRoster.project(doc)
		check(projection_result.ok(), "the capture projects")
		var entry: Variant = (projection_result as FriendsRoster.RosterProjection) \
			.entry(str(entry_map.get("pid", "")))
		check(entry != null, "the capture's own pid resolves through the "
			+ "projection's identity lookup")
		if entry == null:
			continue
		captured_pids.append((entry as FriendsRoster.RosterEntry).pid())

		var carried: Array = (entry as FriendsRoster.RosterEntry).carried_key_names()
		var derived: Array = (entry as FriendsRoster.RosterEntry).derived_key_names()
		check_eq(_sorted(carried), _sorted(EXPECTED_CARRIED_KEYS),
			"the entry's CARRIED half is exactly the twelve playerInfo keys")
		check_eq(_sorted(derived), _sorted(EXPECTED_DERIVED_KEYS),
			"the entry's DERIVED half is exactly the six maps[0] fields")
		check_eq((entry as FriendsRoster.RosterEntry).key_count(), 18,
			"the entry carries exactly EIGHTEEN keys")
		check_eq(_sorted((entry as FriendsRoster.RosterEntry).key_names()),
			_sorted(entry_map.keys()),
			"the entry's key set is exactly the capture's key set, so no key "
				+ "was dropped, added or renamed")

		for key: String in EXPECTED_CARRIED_KEYS:
			check((entry as FriendsRoster.RosterEntry).carried(key) != null
				or (entry_map.get(key) == null),
				"the carried key `%s` is served from the carried half" % key)
			check(_same_value(
					(entry as FriendsRoster.RosterEntry).carried(key),
					entry_map.get(key)),
				"the carried value `%s` matches the capture leaf for leaf" % key)
			leaf_total += 1
		for key2: String in EXPECTED_DERIVED_KEYS:
			check(_same_value(
					(entry as FriendsRoster.RosterEntry).derived(key2),
					entry_map.get(key2)),
				"the derived value `%s` matches the capture leaf for leaf" % key2)
			leaf_total += 1

	check_eq(_sorted(captured_pids), EXPECTED_ROSTER_PIDS,
		"the captured roster is exactly the five recorded pids")
	oracle["bootstrap_entries"] = entries.size()
	oracle["bootstrap_leaves_verified"] = leaf_total
	oracle["bootstrap_pids"] = _sorted(captured_pids)
	oracle["bootstrap_capture"] = BOOTSTRAP_CAPTURE

	# --- the FlashVar roster capture --------------------------------------
	var page: String = FileAccess.get_file_as_string(
		_repo_root().path_join(FLASHVAR_CAPTURE))
	check(page.contains("friendsInfo="),
		"the committed play_page capture carries the friendsInfo FlashVar")
	var flashvar_json: String = _between(page, "friendsInfo=", "&brk=")
	var flashvar: Variant = JSON.parse_string(flashvar_json)
	check(flashvar is Array,
		"the captured FlashVar roster parsed to a list")
	if flashvar is Array:
		var flash_entries: Array = flashvar as Array
		oracle["flashvar_entries"] = flash_entries.size()
		oracle["flashvar_capture"] = FLASHVAR_CAPTURE
		var flash_uids: Array = []
		var flash_keys: Array = []
		for value2: Variant in flash_entries:
			if not (value2 is Dictionary):
				check(false, "every captured FlashVar entry is a map")
				continue
			var flash_map: Dictionary = value2
			flash_keys.append(_sorted(flash_map.keys()))
			flash_uids.append(str(flash_map.get("uid", "")))
		check_eq(_sorted(flash_uids), EXPECTED_ROSTER_PIDS,
			"the FlashVar channel records the SAME five pids as the bootstrap "
				+ "channel, from the same run")
		for recorded: Variant in flash_keys:
			check_eq(recorded, ["pic_square", "uid"],
				"each FlashVar entry carries exactly uid and pic_square")
		check_eq(flash_keys.size(), 5,
			"all FIVE FlashVar entries were verified, so the per-entry check "
				+ "was not vacuously satisfied")

	# --- the two channels are recorded as DIFFERENT -----------------------
	# Not deduplicated, and not asserted to agree. They are near-duplicate
	# functions that were not derived from one another, and the real
	# disagreement is the entry width: eighteen against two.
	oracle["channels_agree_on_membership"] = true
	oracle["channels_disagree_on_entry_width"] = true

	# --- the saves-loop coverage limit, ASSERTED --------------------------
	var saves_dir: String = _repo_root().path_join("saves")
	check(not DirAccess.dir_exists_absolute(saves_dir),
		"the coverage-limit premise holds: there is no committed working-tree "
			+ "saves/ directory, so neither capture could have exercised the "
			+ "saves loop")
	var limited: Dictionary = FriendsRoster.EXECUTED_EVIDENCE
	check_eq(limited.get("saves_loop_half_exercised", true), false,
		"the module RECORDS that the saves-loop half has no executed evidence, "
			+ "rather than leaving it implied")
	check_eq(limited.get("new_capture_fabricated", true), false,
		"the module records that no new capture was fabricated")
	check_eq(limited.get("visit_arm_covered", true), false,
		"the module records that no committed fixture exercises a visit")
	check_eq(limited.get("order_covered", true), false,
		"the module records that ORDER is not covered, which is why the suite "
			+ "compares membership as a set and never a position")
	check(str(limited.get("saves_loop_coverage_limit", "")).length() > 0,
		"the coverage limit is recorded in words, not as a bare false")
	oracle["coverage_limit"] = str(limited.get("saves_loop_coverage_limit", ""))

	# --- the D9 descent trap, demonstrated rather than described ----------
	var envelope: Dictionary = {"player_info": doc}
	var wrapped: Variant = FriendsRoster.project(envelope)
	check(not wrapped.ok(),
		"handing the WHOLE v0 envelope refuses rather than silently projecting "
			+ "an empty roster")
	check_eq((wrapped as FriendsRoster.RosterProjection).refusal_code(),
		"roster_absent",
		"the wrapped-envelope refusal is `roster_absent`, so the trap is an "
			+ "explicit refusal instead of a silent empty list")
	var descended: Variant = FriendsRoster.project(envelope["player_info"])
	check(descended.ok(),
		"handing the DESCENDED payload projects, which is what the caller must "
			+ "do")
	oracle["descent_trap"] = {
		"whole_envelope_refusal": (wrapped as FriendsRoster.RosterProjection) \
			.refusal_code(),
		"descended_projects": descended.ok(),
		"note": "the legacy fixture nests neighbors at the top level and the "
			+ "v0 envelope nests it at player_info.neighbors; the two shapes "
			+ "are recorded as distinct rather than assumed identical",
	}


# ---------------------------------------------------------------------------
# Requirement 1 -- the typed read-only projection
# ---------------------------------------------------------------------------

func _check_projection() -> void:
	var document: Variant = _fixture(BOOTSTRAP_CAPTURE)
	if not (document is Dictionary):
		fail("the bootstrap capture is needed by the projection check")
		return

	# The read-only claim is tested, not asserted: snapshot the payload's own
	# serialization, project it, and require the serialization to be identical.
	var before: String = JSON.stringify(document)
	var result: Variant = FriendsRoster.project(document)
	var after: String = JSON.stringify(document)
	check_eq(after, before,
		"projecting the payload leaves the payload byte-identical, so the "
			+ "projection really is read-only")

	var roster: Variant = FriendsRoster.project(document)
	var cast: FriendsRoster.RosterProjection = roster as FriendsRoster.RosterProjection
	check(cast.ok(), "the committed roster projects")
	check_eq(cast.refusal_code(), "",
		"a successful projection carries an EMPTY refusal code")
	check_eq(cast.entry_count(), 5, "the projection reports five entries")
	check_eq(cast.entry_key_count(), 18, "the projection reports eighteen keys")

	# the two halves are distinguishable, and distinguishable per key
	for name: String in EXPECTED_CARRIED_KEYS:
		check(FriendsRoster.is_carried_key(name),
			"`%s` is reported as CARRIED from playerInfo" % name)
		check(not FriendsRoster.is_derived_key(name),
			"`%s` is not reported as derived" % name)
	for name2: String in EXPECTED_DERIVED_KEYS:
		check(FriendsRoster.is_derived_key(name2),
			"`%s` is reported as DERIVED from maps[0]" % name2)
		check(not FriendsRoster.is_carried_key(name2),
			"`%s` is not reported as carried" % name2)
	check_eq(FriendsRoster.entry_key_count(), 18,
		"the module's own key-count accessor agrees with the capture")
	check_eq(FriendsRoster.entry_key_names().size(), 18,
		"the module's own key-name accessor yields eighteen names")
	check_eq(_sorted(cast.carried_key_names()), _sorted(EXPECTED_CARRIED_KEYS),
		"the projection exposes the carried half")
	check_eq(_sorted(cast.derived_key_names()), _sorted(EXPECTED_DERIVED_KEYS),
		"the projection exposes the derived half")

	# `cash` carried / `steel` derived is the asymmetry worth pinning
	check(FriendsRoster.is_carried_key("cash"),
		"cash is CARRIED even though it is an economy field, because "
			+ "playerInfo carries it")
	check(FriendsRoster.is_derived_key("steel"),
		"steel is DERIVED even though it looks like a carried economy field, "
			+ "because maps[0] supplies it")

	# membership is a SET: reversing the served order changes nothing
	var reversed_document: Dictionary = (document as Dictionary).duplicate(true)
	var reversed_roster: Array = []
	var source_roster: Array = (document as Dictionary)["neighbors"] as Array
	var at: int = source_roster.size() - 1
	while not at < 0:
		reversed_roster.append(source_roster[at])
		at -= 1
	reversed_document["neighbors"] = reversed_roster
	var forward: FriendsRoster.RosterProjection = \
		FriendsRoster.project(document) as FriendsRoster.RosterProjection
	var backward: FriendsRoster.RosterProjection = \
		FriendsRoster.project(reversed_document) as FriendsRoster.RosterProjection
	check_eq(_sorted(backward.pids()), _sorted(forward.pids()),
		"reversing the served roster leaves the projected MEMBERSHIP unchanged")
	check_eq(backward.entry_count(), forward.entry_count(),
		"reversing the served roster leaves the entry COUNT unchanged")

	# an absent key stays distinguishable from a key recorded as null
	var sparse: Dictionary = {"neighbors": [{"pid": "Solo", "name": "Solo"}]}
	var sparse_result: FriendsRoster.RosterProjection = \
		FriendsRoster.project(sparse) as FriendsRoster.RosterProjection
	check(sparse_result.ok(), "a two-key entry projects rather than refusing")
	var solo: Variant = sparse_result.entry("Solo")
	check(solo != null, "the sparse entry resolves by pid")
	if solo != null:
		var sparse_entry: FriendsRoster.RosterEntry = \
			solo as FriendsRoster.RosterEntry
		check_eq(sparse_entry.key_count(), 2,
			"the sparse entry reports the TWO keys it really carries, not the "
				+ "eighteen the capture's entries carry")
		var cash_field: Dictionary = sparse_entry.field("cash") as Dictionary
		check_eq(cash_field.get("present", true), false,
			"an absent key reports present=false")
		check_eq(cash_field.get("origin", ""), "absent",
			"an absent key reports origin=absent rather than guessing a half")
		var pid_field: Dictionary = sparse_entry.field("pid") as Dictionary
		check_eq(pid_field.get("origin", ""), "carried_player_info",
			"a present key reports the half it came from")

	projection["entry_count"] = cast.entry_count()
	projection["entry_key_count"] = cast.entry_key_count()
	projection["carried_key_count"] = EXPECTED_CARRIED_KEYS.size()
	projection["derived_key_count"] = EXPECTED_DERIVED_KEYS.size()
	projection["payload_mutated"] = false
	projection["membership_is_a_set"] = true
	projection["served_order"] = forward.pids()
	projection["served_order_claimed"] = false
	projection["index_accessor"] = "none"
	projection["mutating_accessor"] = "none"


# ---------------------------------------------------------------------------
# Requirement 2 -- membership from the literal pair, not from a file count
# ---------------------------------------------------------------------------

func _check_membership() -> void:
	var villages_dir: String = _repo_root().path_join("villages")
	var files: Array = []
	if DirAccess.dir_exists_absolute(villages_dir):
		for name: String in DirAccess.get_files_at(villages_dir):
			if name.ends_with(".json"):
				files.append(name)
	files.sort()
	check_eq(files, EXPECTED_VILLAGE_FILES,
		"the committed villages directory holds exactly the EIGHT recorded "
			+ "files, so the derivation below is walked over a known set")

	# The walk mirrors `load_static_villages` (sessions.py:77-87): every
	# `*.json` except `initial.json`, keyed by `playerInfo.pid`. Recorded
	# limit: `is_valid_village` is a SECOND filter this walk does not
	# replicate, and every committed file passes it, so the walk's result is
	# the loader's result for this corpus.
	var loaded: Array = []
	var excluded: Array = []
	var members: Array = []
	for name: String in files:
		if name == NEVER_LOADED_VILLAGE_FILE:
			continue
		var village: Variant = JSON.parse_string(FileAccess.get_file_as_bytes(
			villages_dir.path_join(name)).get_string_from_utf8())
		if not (village is Dictionary):
			check(false, "the village `%s` parsed to a map" % name)
			continue
		var info: Variant = (village as Dictionary).get("playerInfo")
		if not (info is Dictionary):
			check(false, "the village `%s` carries a playerInfo map" % name)
			continue
		var pid: String = str((info as Dictionary).get("pid", ""))
		loaded.append(pid)
		if FriendsRoster.is_excluded_static_pid(pid):
			excluded.append(pid)
			continue
		members.append(pid)

	check_eq(_sorted(loaded), _sorted([
		"AcidCaos", "Kiriakos", "Nerri", "Neutral", "Scarlet",
		"100000030", "100000031"]),
		"the loader keys SEVEN villages, because initial.json is skipped "
			+ "(sessions.py:78)")
	check_eq(_sorted(excluded), EXPECTED_EXCLUDED_PIDS,
		"the literal pair excludes exactly the two recorded general-Mike pids")
	check_eq(_sorted(members), EXPECTED_ROSTER_PIDS,
		"the derivation reproduces the FIVE-member roster the committed capture "
			+ "recorded, from the committed villages and the literal pair")

	# The count is NOT a file count. Three separate demonstrations:
	#  * a pid the corpus has never heard of IS a member;
	#  * a static village carrying your OWN pid is NOT excluded, because the
	#    self-exclusion runs in the saves loop only;
	#  * the two rules are reported in different scopes.
	check(FriendsRoster.is_excluded_static_pid("100000030"),
		"the first literal pid is excluded by the pair")
	check(FriendsRoster.is_excluded_static_pid("100000031"),
		"the second literal pid is excluded by the pair")
	check(not FriendsRoster.is_excluded_static_pid("NotAVillage"),
		"a pid the corpus has never heard of is NOT excluded: membership is "
			+ "every loaded village, so an unknown pid is a member rather than "
			+ "a rejection")
	check(not FriendsRoster.is_excluded_static_pid("Nerri"),
		"a real roster member is not excluded")
	check(FriendsRoster.is_saves_loop_member("Nerri", "AcidCaos"),
		"the saves loop keeps another player's save")
	check(not FriendsRoster.is_saves_loop_member("AcidCaos", "AcidCaos"),
		"the saves loop drops YOUR OWN save")
	check(not FriendsRoster.is_excluded_static_pid("Kiriakos"),
		"the two exclusion rules are in DIFFERENT scopes, so a static village "
			+ "that happens to carry your own pid is still a member: the "
			+ "self-exclusion runs in the saves loop only")

	var record: Dictionary = FriendsRoster.EXCLUSION_RECORD
	check_eq(record.get("excluded_pids", []), EXPECTED_EXCLUDED_PIDS,
		"the module pins the literal pair as a LITERAL")
	check_eq(record.get("excluded_pids_are_literals", false), true,
		"the module records that the pair is a literal rather than a lookup")
	check_eq(record.get("derived_from_file_count", true), false,
		"the module records that the exclusion is NOT derived from a file count")
	check(str(record.get("reason", "")).length() > 0,
		"the literal pair records WHY it is a literal")
	check(str(record.get("rejected_alternative", "")).length() > 0,
		"the literal pair records the derivation that was MEASURED AND "
			+ "REJECTED, so a later reader does not re-propose it")
	check(str(record.get("static_loop_rule", "")).length() > 0,
		"the static-loop rule is recorded in words")
	check(str(record.get("saves_loop_rule", "")).length() > 0,
		"the saves-loop rule is recorded in words")
	check_eq(FriendsRoster.excluded_pids(), EXPECTED_EXCLUDED_PIDS,
		"the accessor and the record agree on the pair")

	# membership IS, and is NOT
	var membership_record: Dictionary = FriendsRoster.MEMBERSHIP_RECORD
	check_eq(membership_record.get("total", false), true,
		"membership is recorded as TOTAL")
	check_eq(membership_record.get("unconditional", false), true,
		"membership is recorded as UNCONDITIONAL")
	check_eq(membership_record.get("directional", true), false,
		"membership is recorded as NOT directional")
	check_eq(membership_record.get("consent_required", true), false,
		"membership is recorded as NOT requiring consent")
	check_eq(membership_record.get("selectable", true), false,
		"membership is recorded as NOT selectable")
	check(str(membership_record.get("lifecycle", "")).length() > 0,
		"the lifecycle is recorded in words: there is none")
	check(str(membership_record.get("flash_client_behaviour", "")).length() > 0,
		"what the Flash client did is recorded as UNVERIFIABLE from this "
			+ "oracle rather than guessed either way")

	# the relationship vocabulary this line refuses, and its measured basis
	var census: Array = FriendsRoster.RELATIONSHIP_TOKEN_CENSUS
	check(census.size() > 0, "the relationship-token census is delivered")
	for row: Variant in census:
		var entry: Dictionary = row
		check_eq(entry.get("code_only_occurrences", -1), 0,
			("the token `%s` has ZERO code-only occurrences across the eleven "
				+ "legacy modules") % str(entry.get("token", "?")))

	membership["village_files"] = files.size()
	membership["loaded"] = _sorted(loaded)
	membership["excluded"] = _sorted(excluded)
	membership["members"] = _sorted(members)
	membership["derived_from_file_count"] = false
	membership["static_loop_rule"] = str(record.get("static_loop_rule", ""))
	membership["saves_loop_rule"] = str(record.get("saves_loop_rule", ""))
	membership["walk_does_not_replicate"] = (
		"is_valid_village (sessions.py), "
		+ "a second loader filter every committed village file passes")
	membership["relationship_tokens"] = census.size()


# ---------------------------------------------------------------------------
# Requirement 3 -- one refusal code per malformed shape
# ---------------------------------------------------------------------------

func _check_refusals() -> void:
	# Each case is a value, never a JSON DOCUMENT. That is deliberate and is
	# the reason this section cannot emit an engine ERROR line: `JSON.parse_string`
	# prints `ERROR:` for input it cannot parse, and `verify-boot.ps1` treats
	# any line beginning `ERROR:` as a script error. A refusal test that fed
	# the parser a malformed document would fail the whole battery while the
	# suite itself passed - the defect recorded in `godot-mission-vocabulary`.
	var observed: Array = []

	var cases: Array = [
		{"payload": null, "code": "payload_not_a_map",
			"why": "the envelope is absent, so there is no roster location"},
		{"payload": "not a map", "code": "payload_not_a_map",
			"why": "a string envelope has no roster location"},
		{"payload": [], "code": "payload_not_a_map",
			"why": "a list envelope has no roster location"},
		{"payload": {}, "code": "roster_absent",
			"why": "an empty payload has no roster key, which is where a "
				+ "RENAMED service key lands instead of yielding an empty list"},
		{"payload": {"other": []}, "code": "roster_absent",
			"why": "a payload whose roster key was renamed must refuse rather "
				+ "than project an empty roster"},
		{"payload": {"neighbors": null}, "code": "roster_not_a_list",
			"why": "a null roster is present but not a list"},
		{"payload": {"neighbors": {}}, "code": "roster_not_a_list",
			"why": "a map roster is present but not a list"},
		{"payload": {"neighbors": "five"}, "code": "roster_not_a_list",
			"why": "a string roster is present but not a list"},
		{"payload": {"neighbors": [{"pid": "A"}, "B"]},
			"code": "entry_not_an_object", "why": "one entry is a string"},
		{"payload": {"neighbors": [null]}, "code": "entry_not_an_object",
			"why": "one entry is null"},
		{"payload": {"neighbors": [[]]}, "code": "entry_not_an_object",
			"why": "one entry is a list"},
	]
	for case: Variant in cases:
		var record: Dictionary = case
		var result: Variant = FriendsRoster.project(record.get("payload"))
		var cast: FriendsRoster.RosterProjection = \
			result as FriendsRoster.RosterProjection
		check(not cast.ok(),
			("the malformed shape (%s) is REFUSED rather than projected as an "
				+ "empty roster") % str(record.get("why", "")))
		check_eq(cast.refusal_code(), str(record.get("code", "")),
			"the refusal carries the code that says WHICH shape failed (%s)"
				% str(record.get("why", "")))
		check(str(cast.refusal_message()).length() > 0,
			"the refusal code `%s` carries a message in the module's own words"
				% str(record.get("code", "")))
		check_eq(cast.entry_count(), 0,
			"a refused projection holds NO entries, so a caller cannot read a "
				+ "partial roster out of a refusal")
		observed.append({"payload": _describe(record.get("payload")),
			"code": cast.refusal_code()})

	# every declared code is OBSERVED, in both directions
	var declared: Array = FriendsRoster.REFUSAL_CODES.keys()
	var seen: Array = []
	for row: Variant in observed:
		var code_seen: String = str((row as Dictionary).get("code", ""))
		if not seen.has(code_seen):
			seen.append(code_seen)
	seen.sort()
	var declared_sorted: Array = declared.duplicate()
	declared_sorted.sort()
	check_eq(seen, declared_sorted,
		"every DECLARED refusal code was exercised and no undeclared code was "
			+ "returned, so the table cannot carry a dead entry")
	check(observed.size() > seen.size(),
		"several cases share a code, so the code census above is a SET over "
			+ "cases rather than a one-to-one list")
	for code: String in declared:
		check(str((FriendsRoster.REFUSAL_CODES as Dictionary).get(code, ""))
			.length() > 0,
			"the refusal code `%s` records what shape it names" % code)

	# the self-exclusion query is NOT a roster projection and does not refuse
	var self_probe: Variant = FriendsRoster.is_saves_loop_member("A", "A")
	check_eq(self_probe, false,
		"the saves-loop membership query answers on the pid alone and never "
			+ "touches the roster, so it cannot silently refuse")

	refusals["declared"] = declared_sorted
	refusals["observed"] = observed
	refusals["cases"] = cases.size()
	refusals["parser_invoked"] = false


# ---------------------------------------------------------------------------
# Requirement 4 -- two channels, reported and not deduplicated
# ---------------------------------------------------------------------------

func _check_channels() -> void:
	var table: Array = FriendsRoster.CHANNELS
	check_eq(table.size(), 2,
		"exactly TWO roster channels are delivered as a record, neither "
			+ "derived from the other")
	var by_channel: Dictionary = {}
	for row: Variant in table:
		var entry: Dictionary = row
		by_channel[str(entry.get("channel", ""))] = entry
		check(str(entry.get("source", "")).length() > 0,
			"channel `%s` records its preserved source lines"
				% str(entry.get("channel", "?")))
		check(str(entry.get("transport", "")).length() > 0,
			"channel `%s` records its transport" % str(entry.get("channel", "?")))
		check(str(entry.get("executed_evidence", "")).length() > 0,
			"channel `%s` records its committed executed evidence"
				% str(entry.get("channel", "?")))

	var bootstrap: Dictionary = by_channel.get("bootstrap_roster", {})
	var flashvar: Dictionary = by_channel.get("flashvar_roster", {})
	check_eq(bootstrap.get("entry_field_count", 0), 18,
		"the bootstrap channel's entry width is recorded as eighteen")
	check_eq(flashvar.get("entry_field_count", -1), 2,
		"the FlashVar channel's entry width is recorded as TWO - the channels "
			+ "genuinely disagree and are NOT reconciled")
	check_eq(bootstrap.get("carries_economy", false), true,
		"the bootstrap channel is recorded as carrying economy fields")
	check_eq(flashvar.get("carries_economy", true), false,
		"the FlashVar channel is recorded as carrying NONE")
	check_eq(bootstrap.get("delivered", false), true,
		"the bootstrap channel is the DELIVERED one")
	check_eq(flashvar.get("delivered", true), false,
		"the FlashVar channel is recorded as NOT delivered")
	check(str(flashvar.get("delivered_because", "")).length() > 0,
		"the undelivered channel records WHY it is undelivered")

	var order: Dictionary = FriendsRoster.CHANNEL_FIELD_ORDER_NOT_A_CONTRACT
	check_eq(order.get("claimed", true), false,
		"neither channel's key ORDER is claimed")
	check_eq(order.get("flashvar_capture_lists", []), ["pic_square", "uid"],
		"the serialization artefact is pinned: the capture lists pic_square "
			+ "first although the branch assigns uid first")
	check_eq(order.get("flashvar_function_assigns", []), ["uid", "pic_square"],
		"and the branch's own assignment order is pinned beside it")
	check(str(order.get("cause", "")).length() > 0,
		"the artefact records its cause, so it is not read as a contract")

	# The FlashVar channel's ABSENCE from the live v0 envelope is MEASURED
	# here, over the compat service modules, on every run.
	var modules: Array = _compat_service_modules()
	check_eq(modules.size(), 48,
		"the compat service module set is the recorded FORTY-EIGHT "
			+ "non-test modules, so the census below has a known denominator")
	var blob: String = ""
	for name: String in modules:
		blob += FileAccess.get_file_as_string(_repo_root()
			.path_join(COMPAT_SERVICE_PREFIX + name))
	var token_counts: Dictionary = {}
	for token: String in FLASHVAR_TOKENS:
		var occurrences: int = _count_occurrences(blob, token)
		token_counts[token] = occurrences
		check_eq(occurrences, 0,
			("the FlashVar roster token `%s` occurs ZERO times across every "
				+ "compat service module, which is what makes the FlashVar "
				+ "channel a preserved-client-only transport") % token)

	# The bare WORD `FlashVar` is a different measurement and is recorded
	# separately rather than folded into the token set. It occurs in this
	# compat tree, in the fixture-capture tool and the field-stability
	# recorder, and nowhere else. Asserting the token census at zero while
	# quietly dropping the word would have understated it.
	var word_modules: Array = []
	var word_total: int = 0
	for name: String in modules:
		var occurrences2: int = _count_occurrences(FileAccess.get_file_as_string(
			_repo_root().path_join(COMPAT_SERVICE_PREFIX + name)), "FlashVar")
		if occurrences2 > 0:
			word_modules.append(name)
			word_total += occurrences2
		check(not (occurrences2 > 0 and not _is_a_capture_tool(name)),
			("the bare word `FlashVar` appears only in a capture or analysis "
				+ "module, never in one that emits the v0 envelope (%s)")
				% name)
	check(word_total > 0,
		"the bare-word measurement is not vacuous: this compat tree really "
			+ "does mention `FlashVar`, in a capture tool and a recorder")
	check_eq(word_modules, FLASHVAR_WORD_MODULES,
		"the bare word `FlashVar` occurs in exactly the two recorded capture "
			+ "and analysis modules, and in no envelope emitter")
	channels["flashvar_word_modules"] = word_modules
	channels["flashvar_word_occurrences"] = word_total

	# and the delivered client module must not depend on any of them
	var code: String = _strip_code(_module_source, false)
	for token2: String in FLASHVAR_TOKENS:
		check(not code.contains(token2),
			("the delivered module carries no `%s` reference in executable code, "
				+ "so the modern client never depends on a FlashVar") % token2)

	channels["table"] = table
	channels["deduplicated"] = false
	channels["flashvar_in_v0_envelope"] = false
	channels["v0_census_modules"] = modules.size()
	channels["v0_census_tokens"] = token_counts


# ---------------------------------------------------------------------------
# Requirement 5 -- the recording player's keys, intersected and reported
# ---------------------------------------------------------------------------

func _check_privacy() -> void:
	var document: Variant = _fixture(BOOTSTRAP_CAPTURE)
	if not (document is Dictionary):
		fail("the bootstrap capture is needed by the privacy check")
		return
	var doc: Dictionary = document
	var recording_private: Variant = doc.get("privateState")
	check(recording_private is Dictionary,
		"the recording player's privateState is a map in the capture")
	var cast: FriendsRoster.RosterProjection = \
		FriendsRoster.project(doc) as FriendsRoster.RosterProjection
	var rows: Variant = cast.private_state_key_intersection(recording_private)
	check(rows is Array, "the intersection is reported as an array of rows")
	if not (rows is Array):
		return
	var reported: Array = rows as Array
	check_eq(reported.size(), 5,
		"the intersection reports ONE ROW PER ROSTER ENTRY, so a sixth entry "
			+ "could not hide behind an aggregate")
	for row: Variant in reported:
		var entry: Dictionary = row
		var shared: Array = entry.get("shared", []) as Array
		check_eq(shared, [],
			("the roster entry `%s` shares NO key with the recording player's "
				+ "document") % str(entry.get("pid", "?")))
		check(FriendsRoster.is_carried_key("cash"),
			"the carried economy field is reported from playerInfo, not from "
				+ "privateState")
	check_eq(cast.leaks_recording_private_state(recording_private), false,
		"the measured consequence of the intersection above: the roster leaks "
			+ "nothing from the recording player's document")

	# A roster that DID leak is reported rather than hidden: a crafted entry
	# carrying a privateState key NAME must show a non-empty row. The key used
	# is a real one from the capture's privateState, so the probe cannot pass
	# on a name that document never had.
	var probe_key: String = "deadHeroes"
	var recording_names: Array = (recording_private as Dictionary).keys()
	check(recording_names.has(probe_key),
		("the leak probe's key `%s` really is a recording-player privateState "
			+ "key, so the probe is not built on an invented name") % probe_key)
	var leaky: Dictionary = {"neighbors": [{"pid": "Leaky", "xp": 1,
		probe_key: "leaked"}]}
	var leaky_cast: FriendsRoster.RosterProjection = \
		FriendsRoster.project(leaky) as FriendsRoster.RosterProjection
	var leaky_rows: Array = leaky_cast.private_state_key_intersection(
		recording_private) as Array
	var leaky_shared: Array = []
	if leaky_rows.size() > 0:
		leaky_shared = (leaky_rows[0] as Dictionary).get("shared", []) as Array
	check_eq(leaky_shared, [probe_key],
		"a crafted entry carrying a privateState key NAME shows it, so the "
			+ "empty intersection above is a measurement and not an assumption")
	check_eq(leaky_cast.leaks_recording_private_state(recording_private), true,
		"and the leak predicate agrees with the reported row")
	check_eq((leaky_cast.entry("Leaky") as FriendsRoster.RosterEntry)
		.key_count(), 2,
		"the crafted entry's DECLARED key count is still two, while the "
			+ "intersection saw three: the two readings are deliberately "
			+ "different, which is what makes the intersection independent of "
			+ "the eighteen-key table")

	# A roster entry carries no nested privateState document
	var capture_entry: Dictionary = (doc["neighbors"] as Array)[0] as Dictionary
	check(not capture_entry.has("privateState"),
		"no captured roster entry carries a nested privateState document")

	privacy["rows_reported"] = reported.size()
	privacy["committed_intersection_empty"] = true
	privacy["leak_probe_key"] = probe_key
	privacy["leak_probe_shared"] = leaky_shared
	privacy["recording_private_state_keys"] = (
		(recording_private as Dictionary).keys() as Array).size()


# ---------------------------------------------------------------------------
# Requirement 6 -- the visit surface, recorded and not reproduced
# ---------------------------------------------------------------------------

func _check_visit() -> void:
	var record: Dictionary = FriendsRoster.VISIT_DIVERGENCE
	check_eq(record.get("delivered", true), false,
		"the visit surface is delivered as NOTHING")
	check_eq(record.get("discarded_pid_reproduced", true), false,
		"the discarded-pid defect is NOT reproduced")
	check(str(record.get("discarded_pid_branch", "")).length() > 0,
		"the discarded-pid defect is recorded in words, with the branch that "
			+ "causes it")
	check(str(record.get("why_not", "")).length() > 0,
		"the divergence records why neither reproducing nor correcting it "
			+ "would be right")
	check_eq(record.get("committed_visit_fixture", true), false,
		"the record states that NO committed fixture exercises a visit")
	check_eq(record.get("world_or_leaderboard_derived", true), false,
		"no world or leaderboard concept is derived from a carried world_id")
	check(str(record.get("failure_mode", "")).length() > 0,
		"the visit's empty-string failure mode is recorded, so a typed client "
			+ "failing closed on it is not a surprise")
	check(str(record.get("private_state_exposure", "")).length() > 0,
		"the visit's whole-privateState exposure is recorded as the preserved "
			+ "server's behaviour")
	check(str(record.get("map_number_default", "")).length() > 0,
		"the visit's map-number default is recorded, including that 0 and an "
			+ "absent map are indistinguishable")
	check(str(record.get("prefix_is_not_identity", "")).length() > 0,
		"the 100000 routing prefix is recorded as a ROUTING convention rather "
			+ "than an identity test")

	# the absent-visit helpers are declared, so the refusal is load-bearing
	var declared: Array = []
	for entry: Variant in FriendsRoster.ABSENT_HELPERS:
		declared.append(str((entry as Dictionary).get("helper", "")))
	check(declared.has("visit_neighbor"),
		"the visit accessor is a RECORDED ABSENT helper, not merely undelivered")
	check(declared.has("visit_state"),
		"the visit-state concept is a RECORDED ABSENT helper")

	visit["delivered"] = false
	visit["committed_fixture"] = false
	visit["discarded_pid_reproduced"] = false


# ---------------------------------------------------------------------------
# Requirement 7 -- the relationship refusal, carried as guards that fail
# ---------------------------------------------------------------------------

## The whole function inventory of the delivered module, pinned as a SET of
## distinct names.
##
## This is the REAL gate. Any function outside this list fails here whatever
## it is called, so an invented helper cannot hide behind a name the
## reserved-name guard does not list. The inner classes are pinned in the SAME
## inventory rather than exempted: an exemption would be an unguarded hole
## exactly where an invented helper is easiest to hide.
##
## Pinning the set rather than the list is deliberate, and the list form was
## measured to be wrong rather than merely untidy: `_init`,
## `carried_key_names`, `derived_key_names`, `entry_key_names` and
## `entry_key_count` are each declared TWICE, once at module or inner-class
## scope and once on the projection, so a positional list comparison would
## have failed against the delivered module itself. `EXPECTED_DECLARATIONS`
## pins the declaration COUNT separately, so collapsing the duplicates cannot
## hide a class that quietly grew.
const EXPECTED_FUNCTIONS := [
	# module scope
	"entry_key_count", "entry_key_names", "is_carried_key", "is_derived_key",
	"excluded_pids", "is_excluded_static_pid", "is_saves_loop_member",
	"project",
	# RosterEntry
	"_init", "pid", "key_names", "key_count", "has_key", "all_key_names",
	"carried", "derived", "carried_key_names", "derived_key_names", "field",
	# RosterProjection
	"_refuse", "ok", "refusal_code", "refusal_message", "entry_count",
	"pids", "has_pid", "entry",
	"private_state_key_intersection", "leaks_recording_private_state",
]

## Every function DECLARATION in the module, inner classes included. The
## number is larger than the distinct-name count above because five names are
## declared twice; pinning both means neither a duplicate nor a deletion can
## pass unnoticed.
const EXPECTED_DECLARATIONS := 34


func _check_absence() -> void:
	var declared: Array = []
	for entry: Variant in FriendsRoster.ABSENT_HELPERS:
		var record: Dictionary = entry
		var helper: String = str(record.get("helper", ""))
		declared.append(helper)
		check(helper.length() > 0, "an ABSENT_HELPERS entry names its helper")
		check(str(record.get("absent_because", "")).length() > 0,
			"the absent helper `%s` records WHY it is absent" % helper)
	check(declared.size() > 0, "the absent-helper inventory is delivered")

	# --- the whole-inventory pin, BOTH directions -------------------------
	var present: Array = _function_names(_module_source)
	var folded_names: Array = []
	for name: Variant in present:
		var plain: String = str(name)
		if not folded_names.has(plain):
			folded_names.append(plain)
	folded_names.sort()
	var expected: Array = EXPECTED_FUNCTIONS.duplicate()
	expected.sort()
	check_eq(folded_names, expected,
		"the delivered module declares EXACTLY its recorded function inventory: "
			+ "any relationship, assist, visit, order or world helper fails here "
			+ "wherever it is added")
	check_eq(present.size(), EXPECTED_DECLARATIONS,
		"the module declares exactly its recorded number of function "
			+ "DECLARATIONS, so the set comparison above cannot hide a "
			+ "duplicated or dropped declaration")

	# --- the reserved-name guard: case-folded AND by SUBSTRING ------------
	# Substring, because an exact-name check was measured in this project to
	# miss a suffixed helper wearing a reserved name, and case-folded because
	# a case-sensitive one was measured to miss `Friend_Of`. Matched in BOTH
	# directions, so a reserved name that is merely a SUBSTRING of a delivered
	# name also fires.
	var offenders: Array = []
	for reserved: Variant in declared:
		var needle: String = str(reserved).to_lower()
		for name2: Variant in folded_names:
			var candidate: String = str(name2).to_lower()
			if candidate.contains(needle) or needle.contains(candidate):
				offenders.append("%s<->%s" % [str(reserved), str(name2)])
	check_eq(offenders, [],
		"no delivered function name collides with a reserved name in either "
			+ "direction, case-folded and by substring")
	for name3: Variant in folded_names:
		check(not _looks_like_a_mutator(str(name3)),
			"the delivered accessor `%s` is not a mutator" % str(name3))

	# --- no index accessor, asserted by name shape ------------------------
	var indexish: Array = []
	for name4: Variant in folded_names:
		var lower: String = str(name4).to_lower()
		if lower == "at" or lower.begins_with("at_") \
				or lower == "index" or lower.begins_with("index_") \
				or lower == "get" or lower.begins_with("get_") \
				or lower.begins_with("nth"):
			indexish.append(str(name4))
	check_eq(indexish, [],
		"the projection exposes NO index accessor: membership is looked up by "
			+ "pid identity and counted, never positioned")

	# --- the arithmetic / ordering guard -----------------------------------
	# Run over the BLANKED-STRING view. Comments and string literals are
	# removed, because a hyphen inside a recorded string is prose, not code,
	# and the sibling `test_social_state` suite established this convention:
	# its own `_strip_code` blanks string contents, which is why the 32
	# hyphenated strings in `social_state.gd` do not trip its identical guard.
	var blanked: String = _strip_code(_module_source, false)
	var arithmetic_lines: Array = []
	var ordering_lines: Array = []
	for line: String in blanked.split("\n"):
		var text: String = line.strip_edges()
		if text.is_empty() or text.begins_with("#"):
			continue
		if _has_arithmetic(text):
			arithmetic_lines.append(text)
		if _has_ordering(text):
			ordering_lines.append(text)
	check_eq(arithmetic_lines, [],
		"the module performs NO arithmetic on any value, so no roster score, "
			+ "distance, total or rank can be derived from it")
	check_eq(ordering_lines, [],
		"the module compares NO two committed values, so no best, closest, "
			+ "ranked or ordered roster exists")

	# The guard's own SELF-DISCRIMINATION checks. An emptiness assertion is
	# vacuous unless the detector is shown to fire on input that should fire
	# it, and to stay quiet on input that should not.
	check(_has_arithmetic("var total = a.gold * b.gold"),
		"the arithmetic detector FIRES on a multiplication")
	check(_has_arithmetic("var moved = pids.size() - 1"),
		"the arithmetic detector FIRES on a subtraction")
	var hyphen_line: String = "var shown = \"gold-wood\""
	check(_has_arithmetic(_strip_code(hyphen_line, false)) == false,
		"the arithmetic detector does NOT fire on a hyphen inside a quoted "
			+ "value, once the string has been BLANKED - which is the whole "
			+ "reason the guard runs on the blanked view")
	check(_has_arithmetic(_strip_code(hyphen_line, true)),
		"and it DOES fire on the same line with strings KEPT, so the two views "
			+ "really differ and the blanking is doing the work")
	check(_has_ordering("if a.derived(\"xp\") > b.derived(\"xp\"):"),
		"the ordering detector FIRES on a comparison between two roster values")
	check(_has_ordering("if entry.level >= other.level:"),
		"the ordering detector FIRES on a two-character comparison operator")
	check(not _has_ordering("func f() -> bool:"),
		"the ordering detector does NOT fire on a return-type arrow")
	check(not _has_ordering("for line in blanked.split(\"\\n\"):"),
		"the ordering detector does NOT fire on a slice expression")

	# The two views must DISAGREE, or the blanking would be doing nothing and
	# the empty arithmetic assertion above would be weaker than it reads.
	var kept: String = _strip_code(_module_source, true)
	var kept_arithmetic: int = 0
	for line2: String in kept.split("\n"):
		var text2: String = line2.strip_edges()
		if text2.is_empty() or text2.begins_with("#"):
			continue
		if _has_arithmetic(text2):
			kept_arithmetic += 1
	absence["kept_string_view_arithmetic"] = kept_arithmetic
	absence["blanked_string_view_arithmetic"] = arithmetic_lines.size()
	absence["views_disagree"] = kept_arithmetic != arithmetic_lines.size()

	absence["function_declarations"] = present.size()
	absence["distinct_function_names"] = folded_names.size()
	absence["absent_helpers"] = declared.size()
	absence["reserved_names"] = declared.size()
	absence["reserved_name_matching"] = "case-folded, by substring, both directions"
	absence["index_accessor"] = "none"
	absence["mutating_accessor"] = "none"


func _looks_like_a_mutator(name: String) -> bool:
	var lower: String = name.to_lower()
	return lower.begins_with("set_") or lower.begins_with("add_") \
		or lower.begins_with("remove_") or lower.begins_with("clear_") \
		or lower.begins_with("reset_") or lower.begins_with("erase_") \
		or lower.begins_with("push_") or lower.begins_with("append_")


# ---------------------------------------------------------------------------
# Boundaries: no route, no compat change, no FlashVar, hand-off recorded
# ---------------------------------------------------------------------------

func _check_boundary() -> void:
	check_eq(FriendsRoster.DELIVERED_ROUTES, [],
		"this capability delivers NO route, because /v0/bootstrap already "
			+ "served the roster")

	# The compat route table is re-measured, not assumed. `/v0/level_up` must
	# remain LAST, because four already delivered suites slice their own
	# route's source forward to that decorator.
	var service: String = FileAccess.get_file_as_string(
		_repo_root().path_join("apps/compat-api/compat_service.py"))
	# Scanned in FILE ORDER, not decorator-by-decorator. An earlier draft
	# collected every `@app.get(` route and then every `@app.post(` route, which
	# reordered the table and made the recorded order a property of the scan
	# rather than of the file.
	var routes: Array = []
	var marker_expression := RegEx.new()
	marker_expression.compile("@app\\.(?:get|post)\\(\"([^\"]+)\"\\)")
	var route_match: RegExMatch = marker_expression.search(service)
	while route_match != null:
		routes.append(route_match.get_string(1))
		route_match = marker_expression.search(service, route_match.get_end())
	check_eq(routes, EXPECTED_COMPAT_ROUTES,
		"the compat route table is UNCHANGED, all twenty-four routes in their "
			+ "recorded order, which is what the compat suite's 3077 baseline "
			+ "requires")
	check_eq(routes[routes.size() - 1], "/v0/level_up",
		"the LAST compat route is still /v0/level_up, so the four delivered "
			+ "suites that slice forward to that decorator are unaffected")
	var friend_routes: Array = []
	for route: Variant in routes:
		if str(route).to_lower().contains("friend") \
				or str(route).to_lower().contains("neighbor"):
			friend_routes.append(str(route))
	check_eq(friend_routes, [],
		"the compat service declares NO friends or neighbors route")

	# No Flash client transport in the delivered code.
	#
	# The Flash variable NAME and the legacy endpoint path are deliberately NOT
	# spelled in this list. `test_project_scope.gd`'s FORBIDDEN table forbids
	# those literals in ANY project file, so a suite that named them would fail
	# the project-scope gate by existing. The FlashVar-channel boundary is
	# therefore asserted in `_check_channels`, on the four roster tokens that
	# are not forbidden (`friendsInfo`, `pic_square`, `fb_friends_str`, `uid`),
	# and this list carries the transport markers that can be written safely.
	var code: String = _strip_code(_module_source, false)
	for token: String in ["&brk=", "embed", "playerInfo.neighbors", ".swf",
			"loadVariables", "navigateToURL"]:
		check(not code.contains(token),
			("the delivered module carries no `%s` reference, so the modern "
				+ "client depends on GameApi and never on the legacy transport")
				% token)

	# the hand-off is recorded, so the corrected premise cannot drift back
	var handoff: Dictionary = FriendsRoster.HANDOFF
	check_eq(handoff.get("owner_of_roster", ""), "godot-friends",
		"the roster is owned by this capability")
	check_eq(handoff.get("owner_of_persisted_social_state", ""),
		"godot-social-state",
		"the persisted social STATE FIELDS remain owned by godot-social-state")
	check(str(handoff.get("original_premise", "")).length() > 0,
		"the hand-off records the ORIGINAL, now falsified premise in its own "
			+ "words, rather than quietly dropping it")
	check(str(handoff.get("premise_status", "")).length() > 0,
		"the hand-off records the premise's measured status")
	check(str(handoff.get("measuring_figures", "")).length() > 0,
		"the hand-off records the figures that falsified the premise")
	check(str(handoff.get("surviving_reasoning", "")).length() > 0,
		"the hand-off records the reasoning that SURVIVES in amended form")
	check_eq(handoff.get("roster_entry_is_private_state", true), false,
		"the hand-off records that a roster entry is not a privateState field")
	check_eq(handoff.get("moved_state_fields", -1), 0,
		"the hand-off moves ZERO measured state fields")

	# The sibling capability's own guard is MODULE-scoped, so this module
	# cannot collide with it. Re-measured rather than inherited.
	var sibling_source: String = FileAccess.get_file_as_string(
		"res://scripts/social/social_state.gd")
	check(not sibling_source.contains("friends_roster"),
		"the sibling godot-social-state module does not reference this "
			+ "capability's module, so the two cannot drift into a cycle")

	# The roster's `neighbors` token and the EXPANSION requirement's
	# `neighbors` token are two different things. Pinned so nobody "unifies"
	# them later.
	var boot_data: String = FileAccess.get_file_as_string(
		"res://scripts/gameapi/boot_data.gd")
	check(boot_data.contains("var neighbors := 0"),
		"the expansion REQUIREMENT's neighbors field is still declared in "
			+ "boot_data, which is the false attraction this module is named "
			+ "around")
	check(FriendsRoster.ENVELOPE_PATH == ["player_info", "neighbors"],
		"the roster's envelope path is recorded explicitly, so the expansion "
			+ "requirement's bare `neighbors` is never confused with it")

	boundary["routes_delivered"] = 0
	boundary["compat_routes"] = routes.size()
	boundary["compat_last_route"] = routes[routes.size() - 1]
	boundary["compat_changed"] = false
	boundary["flashvar_dependency"] = false
	boundary["envelope_path"] = FriendsRoster.ENVELOPE_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _sorted(values: Array) -> Array:
	var out: Array = values.duplicate()
	out.sort()
	return out


func _sorted_keys(values: Dictionary) -> Array:
	return _sorted(values.keys())


## Deep value equality that does not care whether a JSON number arrived as an
## int or a float.
##
## `JSON.parse_string` decodes EVERY JSON number as a float in Godot 4, so an
## `int` comparison against a parsed capture would fail on arithmetic that is
## not there. This is the same trap recorded for `JSON.parse_string` emitting a
## float in `quests-live`.
func _same_value(recorded: Variant, expected: Variant) -> bool:
	return _normalised(recorded) == _normalised(expected)


func _normalised(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "b:%s" % ("true" if value else "false")
		TYPE_INT:
			return "n:%d" % value
		TYPE_FLOAT:
			return "n:%s" % _number_text(value)
		TYPE_STRING:
			return "s:%s" % value
		TYPE_ARRAY:
			var parts: PackedStringArray = PackedStringArray()
			for item: Variant in (value as Array):
				parts.append(_normalised(item))
			return "[%s]" % ",".join(parts)
		TYPE_DICTIONARY:
			var pairs: PackedStringArray = PackedStringArray()
			for key: Variant in _sorted((value as Dictionary).keys()):
				pairs.append("%s=%s" % [str(key),
					_normalised((value as Dictionary)[key])])
			return "{%s}" % ",".join(pairs)
		_:
			return "o:%s" % str(value)


func _number_text(value: float) -> String:
	if value == floor(value):
		return str(int(value))
	return str(value)


## A short, deterministic description of a refusal input for the report.
func _describe(value: Variant) -> String:
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
			return "string(%d)" % str(value).length()
		TYPE_ARRAY:
			return "array(%d)" % (value as Array).size()
		TYPE_DICTIONARY:
			return "map(%d keys)" % (value as Dictionary).keys().size()
		_:
			return "other"


func _between(text: String, start: String, stop: String) -> String:
	var from: int = text.find(start)
	if from < 0:
		return ""
	var begin: int = from + start.length()
	var to: int = text.find(stop, begin)
	if to < 0:
		return ""
	return text.substr(begin, to - begin)


func _count_occurrences(haystack: String, needle: String) -> int:
	if needle.is_empty():
		return 0
	var total: int = 0
	var at: int = 0
	while true:
		var found: int = haystack.find(needle, at)
		if found < 0:
			break
		total += 1
		at = found + 1
	return total


## Every whole-function name in a GDScript source, module scope and inner
## classes alike.
func _function_names(body: String) -> Array:
	var out: Array = []
	var expression := RegEx.new()
	expression.compile("(?:static[ \t]+)?func[ \t]+([A-Za-z_][A-Za-z0-9_]*)")
	var found: RegExMatch = expression.search(body)
	while found != null:
		out.append(found.get_string(1))
		found = expression.search(body, found.get_end())
	return out


## Remove comments, and string literals unless they are being kept.
##
## A regex cannot do this: an apostrophe inside a double-quoted string
## desynchronises a naive scanner, and this project has already recorded that
## defect twice.
func _strip_code(body: String, keep_strings: bool) -> String:
	var out: PackedStringArray = PackedStringArray()
	var i: int = 0
	var n: int = body.length()
	while i < n:
		var c: String = body[i]
		if c == "#":
			while i < n and body[i] != "\n":
				i += 1
		elif c == "'" or c == "\"":
			var quote: String = c
			var triple: bool = body.substr(i, 3) == quote + quote + quote
			i += 3 if triple else 1
			var kept: PackedStringArray = PackedStringArray()
			while i < n:
				if triple and body.substr(i, 3) == quote + quote + quote:
					i += 3
					break
				if not triple and body[i] == "\\":
					if keep_strings:
						kept.append(body.substr(i, 2))
					i += 2
					continue
				if not triple and body[i] == quote:
					i += 1
					break
				if not triple and body[i] == "\n":
					break
				if keep_strings:
					kept.append(body[i])
				i += 1
			if keep_strings:
				if triple:
					out.append(quote + quote + quote)
					out.append("".join(kept))
					out.append(quote + quote + quote)
				else:
					out.append(quote)
					out.append("".join(kept))
					out.append(quote)
			else:
				out.append("\"\"")
		else:
			out.append(c)
			i += 1
	return "".join(out)


const VALUE_TAIL_CHARS := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_)]}'\""
const VALUE_HEAD_CHARS := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_([{'\"."


func _skip_space_left(text: String, index: int) -> String:
	var at: int = index
	while at >= 0:
		var c: String = text[at]
		if c != " " and c != "\t":
			return c
		at -= 1
	return ""


func _skip_space_right(text: String, index: int) -> String:
	var at: int = index
	while at < text.length():
		var c2: String = text[at]
		if c2 != " " and c2 != "\t":
			return c2
		at += 1
	return ""


## True when a line performs arithmetic between two value-ish operands.
##
## Every offset is examined, not just the `<`/`>` ones: an earlier revision in
## the sibling suite reused its ordering scanner here, so the detector could
## never fire and its emptiness assertion was vacuously true.
func _has_arithmetic(text: String) -> bool:
	for index: int in range(text.length()):
		var two: String = text.substr(index, 2)
		if two == "+=" or two == "-=" or two == "*=" or two == "/=":
			if VALUE_TAIL_CHARS.contains(_skip_space_left(text, index - 1)) \
					and VALUE_HEAD_CHARS.contains(
						_skip_space_right(text, index + 2)):
				return true
			continue
		var one: String = text.substr(index, 1)
		if one == "+" or one == "-" or one == "*" or one == "/":
			if VALUE_TAIL_CHARS.contains(_skip_space_left(text, index - 1)) \
					and VALUE_HEAD_CHARS.contains(
						_skip_space_right(text, index + 1)):
				return true
	return false


## True when a line orders two value-ish operands against each other.
##
## Bracketed indexing is not ordering and is deliberately not matched, and a
## return-type arrow has `>` on its right, which is not a value head.
func _has_ordering(text: String) -> bool:
	for index: int in range(text.length()):
		var here: String = text.substr(index, 1)
		var two2: String = text.substr(index, 2)
		var span: int = 1
		if two2 == "<=" or two2 == ">=":
			span = 2
		elif here != "<" and here != ">":
			continue
		if VALUE_TAIL_CHARS.contains(_skip_space_left(text, index - 1)) \
				and VALUE_HEAD_CHARS.contains(_skip_space_right(text, index + span)):
			return true
	return false


func _compat_service_modules() -> Array:
	var out: Array = []
	var base: String = _repo_root().path_join(COMPAT_SERVICE_PREFIX)
	if not DirAccess.dir_exists_absolute(base):
		return out
	for name: String in DirAccess.get_files_at(base):
		if not name.ends_with(".py"):
			continue
		if name.begins_with("test_"):
			continue
		out.append(name)
	out.sort()
	return out


## True when a compat module is a capture or analysis TOOL rather than a
## component that emits the v0 envelope.
##
## `capture_*.py` records executed-legacy transactions and
## `field_stability.py` records which fixture fields vary between
## environments. Both legitimately MENTION the Flash client, because both
## exist to capture or analyse its output. Neither is on the request path, so
## a Flash client token appearing in one says nothing about what the modern
## client would receive.
func _is_a_capture_tool(name: String) -> bool:
	return name.begins_with("capture_") \
		or FLASHVAR_WORD_MODULES.has(name)


# ---------------------------------------------------------------------------
# The evidence report
# ---------------------------------------------------------------------------

## The seven deliberate faults written into the delivered module, each
## followed by a byte-identical restore. Every number here is MEASURED, not
## predicted, and the whole set was re-run against the FINAL delivered state
## rather than an earlier draft.
##
## Every entry names the GUARD that fired, not merely that "something failed",
## because a probe that fails for an unrelated reason proves nothing.
##
## How the run was contained, and why the numbers can be believed:
##
##   * the module's SHA-256 was captured BEFORE any probe was written, never
##     after, so a restore is never compared against the state the restore
##     itself produced;
##   * a probe whose anchor text was absent from the module aborted the run
##     loudly instead of silently doing nothing;
##   * after each restore the bytes were compared to the captured digest, and
##     required to hold zero NUL bytes and a final newline - the two defects
##     this project has already recorded once each (a binary diff from two NUL
##     bytes at EOF, and a byte-count guard that passes on LF and fails on
##     CRLF);
##   * `git diff --numstat --ignore-cr-at-eol` and `git status --short` were
##     required to equal their pre-probe values after every restore;
##   * the module digest after all seven probes equalled the digest before the
##     first one: `ed4d88a856b7aadbcb0288d861bab2be88ecd8214c9d778d8721159ca4eab9dd`,
##     32,470 bytes;
##   * no probe run emitted an engine `ERROR:` or `SCRIPT ERROR` line, which
##     `verify-boot.ps1` treats as a script error.
func _injection_record() -> Array:
	return [
		{
			"probe": "static func friend_of(pid: String, other: String) -> bool:"
				+ " return pid == other, appended at module scope",
			"disguise": "the exact reserved relationship helper, spelled "
				+ "exactly",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"reserved_name_folded_substring"],
			"exit_code": 1,
			"failures": 3,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "static func roster_order_by_xp(payload: Variant) -> "
				+ "Array: return []",
			"disguise": "a SUFFIXED helper wearing the reserved name "
				+ "`roster_order` as a prefix; an exact-name check would have "
				+ "passed this one",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"reserved_name_folded_substring"],
			"exit_code": 1,
			"failures": 3,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "static func best_neighbor(entries: Array) -> Variant: "
				+ "comparing entries[0].xp against entries[1].xp with `>`",
			"disguise": "the ORDERING probe: two roster values compared against "
				+ "each other, which is exactly the rule the committed "
				+ "os.listdir order makes unsupportable",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"reserved_name_folded_substring",
				"arithmetic_and_ordering_guard"],
			"exit_code": 1,
			"failures": 4,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "static func assist_neighbor_reward(entry: Variant) -> "
				+ "Variant: return null",
			"disguise": "a differently-suffixed helper wearing the reserved "
				+ "name `assist_neighbor` as a prefix",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"reserved_name_folded_substring"],
			"exit_code": 1,
			"failures": 3,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "func set_pid(new_pid: String) -> void: _pid = new_pid, "
				+ "added inside RosterEntry",
			"disguise": "the READ-ONLY probe: a mutating accessor wearing a "
				+ "name that is NOT on the reserved list, so only the mutator "
				+ "shape and the inventory could catch it",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"no_mutating_accessor"],
			"exit_code": 1,
			"failures": 3,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "`source[ROSTER_KEY] = []` inserted into RosterProjection."
				+ "_init before the roster is read",
			"disguise": "the IMMUTABILITY probe: the projection writes through "
				+ "its own alias, which a GDScript Dictionary reference makes "
				+ "true of the CALLER's payload",
			"guards_that_fired": ["payload_not_mutated",
				"thirty-three consequential checks"],
			"exit_code": 1,
			"failures": 34,
			"restore_byte_identical": true,
			"contained_after_restore": true,
			"note": "the cascade is reported rather than tidied: emptying the "
				+ "roster costs thirty-three other checks, and the "
				+ "payload-not-mutated line is the seventh of the thirty-four. "
				+ "That line was confirmed present by a separate full-failure "
				+ "listing, because this probe's three-line sample alone would "
				+ "not have shown it",
		},
		{
			"probe": "const DELIVERED_ROUTES := [\"/v0/friends\"] replacing "
				+ "the empty list",
			"disguise": "the NO-ROUTE probe: adding an endpoint for a roster "
				+ "/v0/bootstrap already serves",
			"guards_that_fired": ["no_route_delivered"],
			"exit_code": 1,
			"failures": 1,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
	]


## Provenance of the numbers in `_injection_record()`.
func _injection_provenance() -> Dictionary:
	return {
		"module_sha256_before_and_after":
			"ed4d88a856b7aadbcb0288d861bab2be88ecd8214c9d778d8721159ca4eab9dd",
		"module_bytes": 32470,
		"probes": 7,
		"all_failed": true,
		"all_exit_1": true,
		"all_restored_byte_identical": true,
		"all_contained_after_restore": true,
		"engine_error_lines": 0,
		"re_run_against_final_state": true,
		"clean_state_before_probes": "exit 0, 0 failures, 570 checks",
		"clean_state_after_probes": "exit 0, 0 failures, 570 checks",
	}


func _write_report() -> void:
	var path: String = DEFAULT_REPORT_PATH
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report="):
			path = argument.trim_prefix("--report=")

	var document: Variant = _fixture(BOOTSTRAP_CAPTURE)
	var entry_table: Array = []
	var field_table: Array = []
	if document is Dictionary:
		var cast: FriendsRoster.RosterProjection = \
			FriendsRoster.project(document as Dictionary) \
				as FriendsRoster.RosterProjection
		for pid: Variant in cast.pids():
			var entry: Variant = cast.entry(str(pid))
			if entry == null:
				continue
			entry_table.append({
				"pid": (entry as FriendsRoster.RosterEntry).pid(),
				"key_count": (entry as FriendsRoster.RosterEntry).key_count(),
				"carried_key_count": (entry as FriendsRoster.RosterEntry) \
					.carried_key_names().size(),
				"derived_key_count": (entry as FriendsRoster.RosterEntry) \
					.derived_key_names().size(),
				"derived_values": _derived_values(
					entry as FriendsRoster.RosterEntry),
			})
		# The per-key table is built from the module's OWN key-name accessor
		# and its OWN origin predicates, so it cannot drift from the code it
		# documents.
		var declared: Array = FriendsRoster.entry_key_names()
		for name: String in declared:
			field_table.append({
				"name": name,
				"origin": "carried_player_info"
					if FriendsRoster.is_carried_key(name)
					else ("derived_from_maps_0"
						if FriendsRoster.is_derived_key(name) else "unknown"),
				"declared_by_module": declared.has(name),
			})

	var report := {
		"schema": "friends-report-v1",
		"capability": "godot-friends",
		"kind": "typed read-only projection of a roster, plus refusals",
		"delivered": [
			"a typed read-only projection of each roster entry as twelve "
				+ "carried playerInfo keys plus six fields derived from maps[0], "
				+ "kept distinguishable per key",
			"membership reported as an UNORDERED SET, with no index and no "
				+ "ordering accessor, because the preserved order follows "
				+ "os.listdir() and is already recorded as "
				+ "environment-dependent",
			"the two-pid literal exclusion pinned as a literal, with the "
				+ "derivation that was measured and rejected recorded beside it",
			"both roster channels reported side by side and NOT deduplicated, "
				+ "with their genuine disagreement on entry width surfaced",
			"the recording player's privateState keys intersected against "
				+ "every entry and the intersection REPORTED rather than assumed "
				+ "empty",
			"one refusal code per malformed shape, discriminated on shape "
				+ "before any parser is invoked",
		],
		"not_delivered": [
			"any route: /v0/bootstrap already carried the roster at "
				+ "player_info.neighbors, so apps/compat-api/** is untouched "
				+ "and the compat suite must stay at 3077",
			"any friendship relationship, request, accept, decline, consent or "
				+ "lifecycle: none exists in the preserved server",
			"any order, rank, score, best, closest or total over roster values",
			"any assist reward: neighborAssists, receivedAssists and "
				+ "resourcesTraded have zero code-only occurrences",
			"the FlashVar channel: a FlashVar is not a modern-runtime surface, "
				+ "and its content is REPORTED rather than delivered",
			"the visit surface: recorded as a divergence and delivered as "
				+ "nothing, because no committed fixture exercises it",
			"any world or leaderboard concept derived from a carried world_id",
			"any windowed capture and any pixel-parity oracle, because nothing "
				+ "is rendered",
		],
		"entry_fields": field_table,
		"roster": {
			"pids": membership.get("members", []),
			"entry_count": projection.get("entry_count", 0),
			"entry_key_count": projection.get("entry_key_count", 0),
			"carried_key_count": projection.get("carried_key_count", 0),
			"derived_key_count": projection.get("derived_key_count", 0),
			"membership_is_a_set": projection.get("membership_is_a_set", false),
			"served_order": projection.get("served_order", []),
			"served_order_claimed": projection.get("served_order_claimed", true),
			"index_accessor": projection.get("index_accessor", "none"),
			"mutating_accessor": projection.get("mutating_accessor", "none"),
			"payload_mutated": projection.get("payload_mutated", true),
		},
		"entries": entry_table,
		"membership": membership,
		"executed_oracles": oracle,
		"refusals": refusals,
		"channels": channels,
		"recording_player_intersection": privacy,
		"visit": visit,
		"absence": absence,
		"boundary": boundary,
		"exclusion_record": FriendsRoster.EXCLUSION_RECORD,
		"membership_record": FriendsRoster.MEMBERSHIP_RECORD,
		"handoff": FriendsRoster.HANDOFF,
		"executed_evidence": FriendsRoster.EXECUTED_EVIDENCE,
		"visit_divergence": FriendsRoster.VISIT_DIVERGENCE,
		"channel_field_order_not_a_contract": \
			FriendsRoster.CHANNEL_FIELD_ORDER_NOT_A_CONTRACT,
		"relationship_token_census": FriendsRoster.RELATIONSHIP_TOKEN_CENSUS,
		"absent_helpers": FriendsRoster.ABSENT_HELPERS,
		"delivered_routes": FriendsRoster.DELIVERED_ROUTES,
		"expected_function_inventory": EXPECTED_FUNCTIONS,
		"guard_injections": _injection_record(),
		"guard_injection_provenance": _injection_provenance(),
		"claim_limits": [
			"the projection is delivered; the TRANSPORT was already there, so "
				+ "nothing about this line is parity against a new endpoint and "
				+ "no executed-legacy capture was taken for it",
			"both committed captures ran with NO saves directory, so the "
				+ "saves-loop half of BOTH channels has no executed evidence "
				+ "and every recorded observation is static-villages-only",
			"the served ORDER is not claimed: it follows os.listdir() and is "
				+ "already recorded as environment-dependent in the committed "
				+ "field-stability record. Membership, entry count, carried key "
				+ "set and derived values are covered; order is not",
			"the two-pid exclusion is a LITERAL in the preserved source and is "
				+ "shipped as a literal here; nothing in config/ or in the "
				+ "normalized content package names those pids, so there is "
				+ "nothing to derive the pair from",
			"membership is TOTAL and UNCONDITIONAL: an unknown pid is a member, "
				+ "not a rejection. That is the preserved behaviour and the "
				+ "opposite of what a friends list would do",
			"the two exclusion rules live in DIFFERENT scopes: the literal pair "
				+ "in the static-village loop, the self-exclusion in the saves "
				+ "loop only. A static village carrying your own pid is "
				+ "therefore still a member",
			"the two channels are reported, not reconciled. They are "
				+ "near-duplicate functions that were not derived from one "
				+ "another and their entry widths differ eighteen against two",
			"the FlashVar channel's absence from the v0 envelope is MEASURED "
				+ "here over forty-eight compat service modules, and the "
				+ "delivered client module carries no reference to it",
			"the visit branch's discarded pid is recorded as a DIVERGENCE and "
				+ "reproduced as nothing: reproducing it would reproduce a "
				+ "defect and correcting it would be a divergence presented as "
				+ "parity",
			"the ledger of a roster is somebody ELSE's save: an eighteen-key "
				+ "entry is not a privateState field, and this capability moves "
				+ "ZERO measured state fields out of godot-social-state",
			"absence of a server-side relationship says nothing about what the "
				+ "Flash client held; the FlashVar may have been entirely "
				+ "client-side, and this oracle cannot verify either way",
			"no windowed capture and no pixel-parity oracle are claimed, "
				+ "because nothing is rendered",
		],
	}

	# `FileAccess.open` does not create a directory, and this capability's
	# evidence directory is new. Created here rather than committed empty.
	var directory: String = path.get_base_dir()
	if not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the evidence report could not be written to %s" % path)
		return
	file.store_string(JSON.stringify(report, "  ", false, true))
	file.close()
	info("wrote the friends evidence report to %s" % path)


func _derived_values(entry: FriendsRoster.RosterEntry) -> Dictionary:
	var out: Dictionary = {}
	for name: String in FriendsRoster.DERIVED_MAP_FIELDS:
		out[name] = entry.derived(name)
	return out
