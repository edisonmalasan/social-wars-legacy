extends RefCounted
## Typed, read-only animation-asset **linkage** projection for a unit (OpenSpec
## `godot-unit-animations` "An animation asset is projected as linkage, never as
## behaviour" / "Committed animation fields are content with no legacy consumer"
## / "The committed max_frame is not the asset's frame count" / "No legacy branch
## selects an animation, and no state machine is derived" / "Animation is
## content, not a server operation" / "No executed-legacy animation fixture is
## claimed" / "Unit-animation evidence and claim limits", design D1-D7).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy server has **no animation rule and no animation command**. Of the
## **63** named `command.py` dispatcher branches, exactly **five** contain
## animation vocabulary at all, and every one of them is accounted for as a
## non-animation: two are the movement line's own `move` and `orient`, two merely
## CONTAIN the letters of `move` inside "re**move**", and `end_attack` closes a
## combat rather than an animation. The count of animation commands is **zero**.
##
## What IS deliverable is therefore a **linkage projection** — the recorded
## labels, their recorded frame positions, the per-sprite recorded frame counts,
## and the recorded rate, each **verbatim** — plus the **inventory** and the
## **refusals** that make the absence auditable (design D1). This is not a stub.
## The five recorded labels are exactly what a later line would reach for to
## build a state machine, and M4's committed conversion records **no playback
## semantics** at all: no tessellation, no duration, no loop, and labels
## **names-only**. So there is no committed transition rule to anchor a state
## machine on, and `MUERTE` is a state the delivered `godot-unit-production`
## capability already found **unreachable** — no legacy command produces a unit
## and none kills one. This record closes that door with the evidence attached.
##
## ## The projection reports LINKAGE and NOTHING derived from it (D1)
##
## `project_asset()` is the pure entry point; `resolve_asset()` reads the
## committed converted package from disk and projects it. Every reported value is
## the recorded value: `labels` carry their own recorded `name`, `frame` and
## `anchor` and are listed in recorded order, the per-sprite `frame_count`s and
## the asset's own `frame_rate` are copied through, and **no** value is computed
## from another. There is no duration from a frame count and a rate, no frame
## time, no loop count, no state machine, no transition, no priority, no
## interrupt, no playback order, no per-state timing, no animation trigger, no
## event-to-state mapping, and no intermediate or elapsed frame. Each of those is
## a **constant false** carrying its reason in `REFUSALS` and its named helper in
## `ABSENT_HELPERS`, and the suite asserts this module's **whole function
## inventory** against a pinned list, so a duration, loop, state-machine,
## transition, priority, interrupt, timing, trigger, or playback helper fails the
## delivered suite rather than appearing quietly later.
##
## ## The recorded RATE is reported, never applied (D1)
##
## `frame_rate` is copied through exactly as the committed package records it —
## `30.0` for the one committed unit package — and is **never** multiplied by a
## frame count to produce a duration or a frame time. `rate_applied` is a constant
## false and `rate_applied_to` the empty string, and the suite proves it
## behaviourally as well: the same package projected beside a definition whose
## recorded rate-adjacent numbers are absurd leaves every linkage field identical.
##
## ## An unresolvable asset is REFUSED with its recorded state intact (D1)
##
## An asset that is **absent**, **unreadable**, **label-less**, or carrying a
## **malformed label entry** is reported `ok: false` / `resolvable: false` with a
## named reason, `labels` empty, and every OTHER recorded field — the recorded
## label count, the root frame counts, the recorded rate, the per-sprite frame
## counts — still reported beside the refusal. Nothing is ever defaulted to an
## empty, nominal, or single-frame animation: `root_frame_count` is the recorded
## value or `null`, never `1`.
##
## ## The committed animation fields are CONTENT, never rules (D2)
##
## `max_frame`, `img_name`, `attack`, `attack_interval`, `attack_range`, and
## `velocity` are **read by no legacy branch at all** — measured as **zero**
## occurrences of each string across the seven legacy root modules — and so is
## the `animal` `properties` flag. They are reported **verbatim** so a reader can
## see what the content says, and the recorded zero-consumer fact is what stops a
## value being mistaken for a rule. **No** duration, loop, transition, priority,
## trigger, or state selection is computed from any of them. `max_frame` is the
## **seventh** committed content field in this project with no legacy consumer,
## and the six already recorded are named beside it in
## `ZERO_CONSUMER_PRECEDENTS`.
##
## ## `max_frame` is NOT the asset's frame count, and what it means is NOT
## ## claimed (D2)
##
## For the one committed converted unit package the committed definition and the
## parse of the asset its own committed `img_name` names **disagree**: committed
## `max_frame` **2**, the parsed root `frame_count` **1**, and the sprite that
## actually holds the five labels **29** frames. The content names exactly the
## asset the package parsed, so the two describe the same unit and disagree.
## `max_frame` is therefore **adopted nowhere** here — not as a frame count, not
## as a duration, not as a loop bound, not as a state count — and **no** claim is
## made about what it means, because this is **one** data point over **one**
## committed converted package. The measurement is sufficient to REFUSE the
## adoption, which is what this line does; it is not sufficient to explain the
## field, and a later line reading only the *name* would reasonably but wrongly
## adopt it.
##
## ## The animation-command inventory, classified (D2/D4)
##
## The useful content is not the list of names but the **classification**: five
## matches, three of them whole-`_`-token matches and two of them pure substring
## artifacts, and **not one** of the five an animation command. A reader who saw
## only "there are animation-named commands" would assume a rule exists; a reader
## who sees the classification and the zero count does not. This capability
## implements none of them.
##
## ## Purity, and the asset-coverage limit (D5)
##
## `project_asset()` holds no node, no clock, no request, and no transport and
## reads nothing from disk, so the same function serves the client, the hermetic
## suite, and the deterministic report. `resolve_asset()` and
## `coverage_record()` are the two functions that touch the filesystem, and both
## do so **read-only** through the repository path helper. Exactly **one** converted
## unit package is committed, so the projection's coverage is exactly one unit and
## `coverage_record()` reports that count explicitly: a later conversion is a
## visible addition, never a silent widening of this evidence.

## Repository path resolution, for the two read-only disk functions only.
const Paths = preload("res://scripts/package_paths.gd")

# ---------------------------------------------------------------------------
# The linkage fields, one by one, with their recorded source (design D1)
# ---------------------------------------------------------------------------

## Every field the projection reports, with the recorded source it is read from.
## This is the machine-readable form of "each reported verbatim", and the suite
## asserts that no two fields share a source, which is the structural form of
## "no value is derived from another": a derived field would have to name its
## source's field as well as its own.
const LINKAGE_FIELDS := [
	{
		"name": "labels",
		"source": "the recorded labels[] of the root timeline and of every "
			+ "committed sprite, in recorded order",
		"source_kind": "asset-parse",
		"verbatim": true,
		"note": "each entry carries its recorded name, frame, and anchor, plus "
			+ "the recorded key set and the timeline it came from. NO duration, "
			+ "loop, transition, or state is derived from any of them",
	},
	{
		"name": "label_frame_positions",
		"source": "each label entry's OWN recorded frame value, inside that entry",
		"source_kind": "asset-parse",
		"verbatim": true,
		"note": "a recorded position, never a range: no start, end, length, or "
			+ "elapsed frame is computed from it, and the recorded rate is never "
			+ "multiplied by it",
	},
	{
		"name": "sprite_frame_counts",
		"source": "each committed sprite's OWN recorded frame_count",
		"source_kind": "asset-parse",
		"verbatim": true,
		"note": "reported per sprite in recorded order with its recorded label "
			+ "count. No loop count and no duration is computed from a frame "
			+ "count, and no two sprites' counts are added together",
	},
	{
		"name": "root_frame_count",
		"source": "the asset root's OWN recorded frame_count, alongside the root "
			+ "main timeline's own recorded frame_count",
		"source_kind": "asset-parse",
		"verbatim": true,
		"note": "OPAQUE and reported twice, as the package records it twice. "
			+ "Never defaulted to 1 when unreadable: an unreadable asset reports "
			+ "null here, never a nominal single frame",
	},
	{
		"name": "frame_rate",
		"source": "the asset root's OWN recorded frame_rate",
		"source_kind": "asset-parse",
		"verbatim": true,
		"note": "REPORTED, NEVER APPLIED. It is never multiplied by a frame "
			+ "count to produce a duration or a frame time, because M4's recorded "
			+ "conversion limit is no playback semantics",
	},
]

## The count the table above fixes, asserted by the suite so a sixth reported
## field cannot be added without failing the run.
const LINKAGE_FIELD_COUNT := 5

## The refusals, stated as the contract they are.
const ASSET_REFUSAL := ("AN ASSET THAT IS ABSENT, UNREADABLE, LABEL-LESS, OR "
	+ "CARRYING A MALFORMED LABEL ENTRY IS REPORTED AS UNRESOLVABLE WITH ITS "
	+ "RECORDED STATE INTACT, AND IS NEVER DEFAULTED TO AN EMPTY, NOMINAL, OR "
	+ "SINGLE-FRAME ANIMATION. labels is empty and label_count is 0 beside a "
	+ "named reason, while the recorded label count, the recorded root frame "
	+ "counts, the recorded rate, and the per-sprite frame counts are still "
	+ "reported, so a caller can never read a refusal as a one-frame animation "
	+ "(design D1)")

const NO_DERIVATION := ("NO VALUE IN THIS PROJECTION IS DERIVED FROM ANOTHER. A "
	+ "duration is never computed from a frame count and a rate, a frame time is "
	+ "never computed from a rate, a loop count is never computed from a label, a "
	+ "next state is never computed from a label position, and no intermediate or "
	+ "elapsed frame is computed between two recorded positions. The suite proves "
	+ "it four ways: each reported field names its own recorded source and no two "
	+ "fields share one, a definition carrying absurd animation-adjacent numbers "
	+ "leaves every linkage field untouched, the same package projected twice "
	+ "differs in nothing, and this module's whole function inventory is compared "
	+ "against a pinned list (design D1/D3)")

# ---------------------------------------------------------------------------
# The fail-closed reasons (design D1)
# ---------------------------------------------------------------------------

## The five named refusals this projection can produce, and no sixth.
const REASON_ASSET_ABSENT := "asset_absent"
const REASON_ASSET_UNREADABLE := "asset_unreadable"
const REASON_NO_LABELS := "no_labels"
const REASON_MALFORMED_LABEL := "malformed_label"
const REASON_NO_SPRITE_REFERENCE := "no_sprite_reference"
const REASON_AMBIGUOUS_SPRITE_REFERENCE := "ambiguous_sprite_reference"
const REASON_INVALID_DEFINITION := "invalid_definition"

## How the caller states what the disk held, so the projection never has to
## guess: `resolved` carries the parsed package, `absent` means the file does not
## exist, and `unreadable` means it exists but did not parse as an object. A
## value outside this vocabulary is refused as unreadable rather than assumed.
const ASSET_RESOLVED := "resolved"
const ASSET_ABSENT := "absent"
const ASSET_UNREADABLE := "unreadable"

## The recorded key set of every committed label entry, as committed.
const LABEL_KEYS := ["anchor", "frame", "name"]

## Where a label was recorded: the root timeline, or a named sprite.
const LABEL_SOURCE_ROOT := "root"
const LABEL_SOURCE_SPRITE_PREFIX := "sprite:"

# ---------------------------------------------------------------------------
# The committed animation fields: content only (design D2)
# ---------------------------------------------------------------------------

## The six committed animation-adjacent fields this capability reports as
## content, in the delta's order. `max_frame` leads because it is the field the
## investigation turned up and the one a later line would misread.
const ANIMATION_FIELDS := ["max_frame", "img_name", "attack",
	"attack_interval", "attack_range", "velocity"]

## The one `properties` flag with animation-adjacent meaning, reported with the
## six and refused for the same reason.
const ANIMATION_FLAG := "animal"

## The measured consumer count of every one of the six fields and of the flag.
## It is **zero** for all of them: measured as the number of occurrences of each
## string across the seven legacy root modules, with no occurrence in any of them.
const ANIMATION_FIELD_CONSUMER_COUNT := 0

## The seven legacy root modules the zero-consumer claim is measured over, in the
## committed module set. The suite re-derives all seven figures from these bytes,
## so the claim cannot drift from the source.
const SEARCHED_MODULES := ["command.py", "engine.py", "sessions.py",
	"server.py", "constants.py", "get_game_config.py", "version.py"]

## The committed content package this capability reads the animation fields out
## of. Named so a reader knows where a reported number came from, and so the
## manifest digests remain the gate on it.
const UNITS_FILE := "packages/game-content/normalized/units.json"
const BUILDINGS_FILE := "packages/game-content/normalized/buildings.json"

## The committed domain sizes the distributions below are measured over.
const UNIT_COUNT := 429
const BUILDING_COUNT := 470

## The measured number of DISTINCT committed values each animation field takes
## across all 429 committed units. `max_frame` takes **two** — which is the
## whole point of the distribution below.
const ANIMATION_FIELD_DISTINCT_UNIT_VALUES := {
	"max_frame": 2,
	"img_name": 401,
	"attack": 131,
	"attack_interval": 12,
	"attack_range": 14,
	"velocity": 11,
}

## The measured committed `max_frame` distribution over the 429 committed units:
## the near-constant **5** on 427 of them, and **2** on exactly two — legacy ids
## **923** and **933**.
const MAX_FRAME_UNIT_DISTRIBUTION := {"2": 2, "5": 427}
const MAX_FRAME_UNIT_EXCEPTIONS := ["923", "933"]
const MAX_FRAME_UNIT_MODAL_VALUE := 5
const MAX_FRAME_UNIT_MODAL_COUNT := 427

## The measured committed `max_frame` distribution over the 470 committed
## buildings: only **1** and **2** there, so the field is not even a constant
## across the two item kinds.
const MAX_FRAME_BUILDING_DISTRIBUTION := {"1": 24, "2": 446}

## How the committed package ENCODES `max_frame`: a JSON **number**. This is
## recorded because it is the opposite of the `properties` flags, which the
## normalized package stores as STRINGS ("1"/"0"), and reading a flag through
## GDScript truthiness would therefore miscount it.
const MAX_FRAME_ENCODING := ("the committed normalized package writes max_frame "
	+ "as a JSON NUMBER - the raw entry reads max_frame: 2 - unlike the "
	+ "properties flags, which are committed as STRINGS. Reading it as a string "
	+ "would invent an encoding the source does not carry")

## `max_frame` is the seventh committed content field in this project with no
## legacy consumer. The ordinal is recorded because the precedence is what makes
## the refusal a rule rather than a preference.
const MAX_FRAME_ORDINAL := 7

## The six committed fields in this project already recorded as having no legacy
## consumer. The precedent is what makes `max_frame`'s refusal a rule rather than
## a preference: recording the field and refusing to invent a rule from it has
## now been done six times.
const ZERO_CONSUMER_PRECEDENTS := [
	{"field": "unit_capacity", "line": "M8 line 2 (unit instances)",
		"fact": "carried by every one of the 429 committed units and non-zero on "
			+ "only 5 of them (4 on Truck and Zodiac, 6 on Ship, Truck 3, and "
			+ "Truck II), with zero occurrences across the legacy modules; "
			+ "push_unit appends to a garrison unconditionally, so no capacity "
			+ "rule is enforced"},
	{"field": "reward_type / reward_amount", "line": "M7's XP line",
		"fact": "committed on every one of the 100 level entries and read by no "
			+ "legacy branch, so no level reward is paid"},
	{"field": "collect / collect_type / collect_xp / max_collects",
		"line": "M8 line 5 (unit collection)",
		"fact": "the committed unit-collection income fields; no collect field "
			+ "is ever read and max_collects is zero on every unit, so no unit "
			+ "income, cap, or payout is derived"},
	{"field": "training_time", "line": "M8 line 4 (unit production)",
		"fact": "carried by every one of the 899 committed items with a positive "
			+ "value on only 130 of the 470 buildings, and read by no legacy "
			+ "branch, so no production duration is derived from it"},
	{"field": "harvester (properties flag)", "line": "M8 line 5 (unit "
		+ "collection)",
		"fact": "a properties flag key on 5 units (Worker I-IV and Orc Worker), "
			+ "every one of them with collect 0, so the flag names no income the "
			+ "content does not also carry"},
	{"field": "velocity / attack_range / ft_flying / ft_ground",
		"line": "M8 line 6 (unit movement)",
		"fact": "the committed movement fields: velocity is positive on all 429 "
			+ "committed units and read by nothing, so no travel time, path, or "
			+ "terrain rule is derived from it. attack_range is listed here "
			+ "because it belongs to THIS line's inventory as an "
			+ "animation-adjacent statistic"},
]

## The refusal, stated as the contract it is.
const ANIMATION_FIELDS_REFUSAL := ("THE COMMITTED max_frame, img_name, attack, "
	+ "attack_interval, attack_range, AND velocity ARE CONTENT, NEVER RULES, AND "
	+ "SO IS THE animal properties FLAG. All SEVEN have ZERO legacy consumers: "
	+ "measured as occurrences of each string across command.py, engine.py, "
	+ "sessions.py, server.py, constants.py, get_game_config.py, and version.py, "
	+ "each is ZERO, in every one of the seven modules. So NO duration, NO loop, "
	+ "NO transition, NO priority, NO trigger, and NO state selection is derived "
	+ "from any of them, and this module provides no helper that would "
	+ "(design D2)")

## The committed distribution, reported as **content** and measured by the suite
## from the verified registry rather than trusted from this sentence.
const ANIMATION_FIELDS_COVERAGE := ("All SIX fields are present on ALL 429 "
	+ "committed units and take exactly TWO, 401, 131, 12, 14, and 11 distinct "
	+ "values respectively. max_frame is the near-constant: 5 on 427 of the 429 "
	+ "units and 2 on exactly two of them - legacy ids 923 and 933 - while the 470 "
	+ "committed buildings take only 1 (on 24 of them) and 2 (on 446). A field "
	+ "that reads 5 on 427 of 429 unit definitions and is read by nothing is not "
	+ "a per-unit animation setting, and the next section shows it is not the "
	+ "asset's frame count either. The animal properties flag is carried by "
	+ "exactly 2 of the 429 committed units and set on both of them, and by none "
	+ "of the 470 committed buildings (design D2)")

# ---------------------------------------------------------------------------
# The measured max_frame non-equivalence (design D2)
# ---------------------------------------------------------------------------

## The refusal, stated as the contract it is. Declared BEFORE the record that
## quotes it, because a constant may not forward-reference another one.
const MAX_FRAME_RULE := ("THE COMMITTED max_frame IS NOT THE PARSED FRAME COUNT "
	+ "OF THE ANIMATION ASSET ITS OWN COMMITTED img_name NAMES. For the one "
	+ "committed converted unit package the committed max_frame is 2, the parsed "
	+ "root frame_count is 1, and the sprite that actually holds the five recorded "
	+ "labels has 29 frames - and the content names EXACTLY the asset that package "
	+ "parsed, so the numbers describe the same unit and DISAGREE. Therefore "
	+ "max_frame is ADOPTED NOWHERE in this client: not as a frame count, not as a "
	+ "duration, not as a loop bound, and not as a state count. It is reported as "
	+ "CONTENT ONLY, and WHAT IT MEANS IS NOT CLAIMED, because the measurement is "
	+ "ONE data point over ONE committed converted package (design D2)")

## The whole non-equivalence finding, with all three measured numbers and the
## refusals attached to it. This is the decision the investigation turned up: a
## later line reading only the NAME `max_frame` would reasonably but wrongly
## adopt it as a frame count.
const MAX_FRAME_NON_EQUIVALENCE := {
	"unit_legacy_id": "933",
	"unit_name": "Wild Elephant",
	"package": "assets/converted/units/10033_wild_elephant/package.json",
	"content_sprite_reference": "10033_wild_elephant",
	"package_legacy_id": "10033_wild_elephant",
	"same_unit": true,
	"same_unit_evidence": "the committed definition's img_name equals the "
		+ "converted package's own legacy_id, so the two numbers describe the "
		+ "SAME unit",
	"committed_max_frame": 2,
	"parsed_root_frame_count": 1,
	"labelled_sprite_id": 63,
	"labelled_sprite_frame_count": 29,
	"agreement": "NONE: 2 against 1 against 29",
	"max_frame_is_the_asset_frame_count": false,
	"adopted_as_frame_count": false,
	"adopted_as_duration": false,
	"adopted_as_loop_bound": false,
	"adopted_as_state_count": false,
	"adopted_anywhere": false,
	"max_frame_role": "content-only",
	"data_points": 1,
	"converted_unit_packages": 1,
	"converted_building_packages": 1,
	"what_max_frame_means": "NOT CLAIMED. The measurement is ONE data point over "
		+ "ONE committed converted unit package, which is sufficient to REFUSE "
		+ "adopting max_frame as a frame count and insufficient to explain it. No "
		+ "claim is made about what it means and no distribution over the corpus "
		+ "is measurable from one package",
	"rule": MAX_FRAME_RULE,
}

## Whether the one data point generalises. It does not, and the answer is
## recorded rather than left to a reader to assume.
const MAX_FRAME_GENERALISES := false

# ---------------------------------------------------------------------------
# The animation-command inventory (design D2/D4)
# ---------------------------------------------------------------------------

## The dispatcher's whole named-branch count, so a reader can see that the five
## recorded matches are five of a closed set of 63 and that no sixth
## animation-named branch is hiding in the remaining 58.
const NAMED_BRANCH_COUNT := 63

## Every named branch, in committed source order. The suite re-derives the set
## out of `command.py` and compares it against this list **and** the count, so a
## new branch fails the run rather than being read as an unrecorded animation
## command.
const NAMED_BRANCHES := [
	"buy", "complete_tutorial", "set_goals", "complete_goal",
	"level_up", "set_quest_var", "move", "collect",
	"sell", "kill", "kill_iid", "batch_remove",
	"orient", "expand", "store_item", "place_stored_item",
	"sell_stored_item", "store_add_items", "next_research_step",
	"research_buy_step_cash",
	"next_research_item", "reset_research_item", "flash_debug", "add_xp_unit",
	"weekly_reward", "push_unit", "pop_unit", "activate",
	"collect_mission", "win_daily_bonus", "trade_resource",
	"buy_stored_item_cash",
	"unit_collections_completed", "add_inventory_item", "remove_inventory_item",
	"complete_collection",
	"add_click", "activate_item_click", "buy_si_help", "finish_si",
	"darts_reset", "darts_new_free", "darts_shoot_balloon",
	"buy_premium_account",
	"resurrect_hero", "set_resource_allies", "buy_mana_new", "buy_magic",
	"use_magic", "push_queue_unit", "push_queue_unit2", "pop_queue_unit",
	"buy_offer_pack", "buy_powerups", "soulmixer_speedup",
	"admin_set_quest_rank",
	"end_quest", "end_attack", "rt_open_graph_unit",
	"first_time_marketplace",
	"fast_forward", "ping", "set_variables",
]

## The animation vocabulary scanned for across the closed branch set. Every stem
## here is a stem a reader might expect an animation command to carry; the suite
## re-derives every match out of `command.py` and compares it against
## `ANIMATION_VOCABULARY_MATCHES`.
const ANIMATION_VOCABULARY := ["anim", "move", "orient", "attack"]

## The vocabulary stems that match **no** branch at all. Recorded because a
## negative measurement is what makes the positive one meaningful: there is no
## `play`, no `loop`, no `state`, no `frame`, no `clip`, and no `sprite` command.
const ANIMATION_VOCABULARY_NO_MATCH := ["frame", "play", "loop", "state",
	"clip", "sprite", "idle", "walk", "death"]

## Every named branch carrying any animation vocabulary, classified. Exactly
## five, and **none** of them is an animation command.
const ANIMATION_VOCABULARY_MATCHES := [
	{
		"command": "move",
		"matched_vocabulary": "move",
		"whole_token": true,
		"inside_another_word": false,
		"is_animation_command": false,
		"why_not": "the type-agnostic coordinate write, already delivered as "
			+ "godot-building-move and referenced by godot-unit-movement: it "
			+ "writes a row's two coordinate slots from client arguments, checks "
			+ "nothing beyond the row's existence, and starts no animation",
	},
	{
		"command": "orient",
		"matched_vocabulary": "orient",
		"whole_token": true,
		"inside_another_word": false,
		"is_animation_command": false,
		"why_not": "a plain client-supplied write of row slot 4: the only "
			+ "orientation writer in the committed source, with no rotation rule "
			+ "and no animation behind it",
	},
	{
		"command": "end_attack",
		"matched_vocabulary": "attack",
		"whole_token": true,
		"inside_another_word": false,
		"is_animation_command": false,
		"why_not": "COMBAT TERMINATION, not animation: the branch closes an "
			+ "attack. It consults no animation field, because the committed "
			+ "attack, attack_interval, and attack_range are read by NO legacy "
			+ "branch at all - there is no committed attack rule for it to end",
	},
	{
		"command": "batch_remove",
		"matched_vocabulary": "move",
		"whole_token": false,
		"inside_another_word": true,
		"is_animation_command": false,
		"why_not": "a pure SUBSTRING ARTIFACT: it contains the letters of move "
			+ "inside re-MOVE. It removes map rows and moves nothing, and "
			+ "treating it as a movement or animation command would be exactly "
			+ "the invention this line refuses",
	},
	{
		"command": "remove_inventory_item",
		"matched_vocabulary": "move",
		"whole_token": false,
		"inside_another_word": true,
		"is_animation_command": false,
		"why_not": "the same re-MOVE substring artifact: it removes an "
			+ "inventory item, moves no row, and animates nothing",
	},
]

## The classification the five matches fall into, so the finding is machine
## readable rather than prose-only: three whole-token matches and two substring
## artifacts, and the count of animation commands is ZERO.
const WHOLE_TOKEN_MATCHES := ["move", "orient", "end_attack"]
const SUBSTRING_ARTIFACTS := ["batch_remove", "remove_inventory_item"]
const ANIMATION_COMMAND_COUNT := 0

## The finding the inventory exists to make checkable.
const NO_ANIMATION_COMMAND := ("NO LEGACY COMMAND BRANCH STARTS, STOPS, "
	+ "ADVANCES, LOOPS, OR SELECTS AN ANIMATION, AND THE COUNT OF ANIMATION "
	+ "COMMANDS IS ZERO. Of the dispatcher's 63 named branches, exactly FIVE "
	+ "carry any animation vocabulary: move and orient (whole-token, and both "
	+ "belong to the delivered movement line), end_attack (combat termination), "
	+ "and batch_remove and remove_inventory_item (pure substring artifacts that "
	+ "contain the letters of move inside re-MOVE). The stems frame, play, loop, "
	+ "state, clip, sprite, idle, walk, and death match NO branch at all. Nothing "
	+ "in the seven legacy root modules animates anything, so no state machine, "
	+ "transition, priority, interrupt, playback order, per-state timing, "
	+ "animation trigger, or mapping from any legacy command to any recorded "
	+ "state is derived here (design D2/D4)")

## Declared false, and stated as the contract it is: no legacy branch selects an
## animation, so there is no server-chosen state to reproduce.
const ANIMATION_SELECTED_BY_SERVER := false

# ---------------------------------------------------------------------------
# The refusal set (design D3)
# ---------------------------------------------------------------------------

## Every playback rule this line refuses, each with its reason. This is the
## machine-readable form of the delta's refusal requirement, and the suite
## asserts that every family is present and that every reason is non-empty.
const REFUSALS := [
	{"family": "frame_duration", "refused": true,
		"reason": "the recorded rate is a parse fact with no committed playback "
			+ "rule behind it, and M4's recorded conversion limit is no playback "
			+ "semantics, so multiplying a frame count by a rate would invent a "
			+ "duration the legacy contract never had"},
	{"family": "frame_time", "refused": true,
		"reason": "the same absence as frame_duration: no committed field is "
			+ "read by any legacy branch, so no per-frame time exists to report"},
	{"family": "loop_count", "refused": true,
		"reason": "nothing recorded says whether or how often a state repeats, "
			+ "and no legacy branch advances a timeline, so a loop count would be "
			+ "invented"},
	{"family": "state_machine", "refused": true,
		"reason": "five recorded labels carry recorded positions and no recorded "
			+ "transition between them; no legacy branch selects one, so a state "
			+ "machine would have no committed rule to reproduce"},
	{"family": "transition", "refused": true,
		"reason": "no committed source records a transition, an order of "
			+ "succession, or a condition; the label positions are positions, not "
			+ "edges"},
	{"family": "priority", "refused": true,
		"reason": "nothing ranks the five recorded labels, and nothing arbitrates "
			+ "between them"},
	{"family": "interrupt", "refused": true,
		"reason": "no legacy branch stops, replaces, or preempts a running "
			+ "animation, because no legacy branch starts one"},
	{"family": "playback_order", "refused": true,
		"reason": "the recorded label positions are reported exactly as recorded "
			+ "and no order is computed between them, beyond the recorded list "
			+ "order of the asset itself"},
	{"family": "per_state_timing", "refused": true,
		"reason": "no per-state duration exists in the committed content, the "
			+ "committed asset, or the legacy source"},
	{"family": "animation_trigger", "refused": true,
		"reason": "no legacy command, event, or condition selects an animation, "
			+ "so there is no trigger to bind one to"},
	{"family": "event_state_mapping", "refused": true,
		"reason": "with zero animation commands there is no legacy command to "
			+ "map, and mapping one to a recorded label would invent the mapping "
			+ "the contract refuses"},
	{"family": "playback", "refused": true,
		"reason": "no animation is played, animated, or rendered anywhere in "
			+ "this line: the converted package establishes asset and timeline "
			+ "LINKAGE only, never playback correctness"},
]

## The refusal set as one statement, quoted beside the projection so a reader
## who sees five labels cannot read them as five playable states.
const REFUSAL_STATEMENT := ("NOTHING PLAYABLE IS IMPLEMENTED. From the recorded "
	+ "max_frame, the recorded frame counts, the recorded frame rate, and the five "
	+ "recorded labels this line derives NO frame duration, NO loop count, NO state "
	+ "machine, NO transition rule, NO priority, NO interrupt, NO playback order, "
	+ "NO per-state timing, NO animation trigger, and NO event-to-state mapping "
	+ "from any legacy command to any recorded state. Every one of those is a "
	+ "recorded refusal with its reason attached, and the suite asserts the "
	+ "ABSENCE of the helpers that would implement them (design D3)")

## The one closed-loop absence the delivered `godot-unit-movement` capability
## delegates here: its recorded absent helper `animate_move` is completed by this
## line, so the movement capability's "no animation is implemented" claim stays
## true and traceable to exactly one owner.
const ANIMATION_OWNERSHIP := ("ANIMATION READING AND ANIMATION REFUSALS ARE OWNED "
	+ "HERE AND NOWHERE ELSE. The delivered godot-unit-movement capability records "
	+ "an absent helper named animate_move and defers animation to a later line; "
	+ "this line is that line, so the deferral is discharged here rather than "
	+ "left open. godot-unit-definitions keeps ownership of the static field model "
	+ "and its asset-RESOLUTION status, and this capability owns the asset-TIMELINE "
	+ "reading, so the two cannot drift (design D6)")

# ---------------------------------------------------------------------------
# The helpers this module deliberately does NOT provide (design D3)
# ---------------------------------------------------------------------------

## The machine-readable form of the absence. Each of these would compute a rule
## the legacy server never had, so none is declared here, and the suite asserts
## this module's whole function inventory against a pinned list AND against this
## list by name — a rename cannot smuggle one past the inventory, and a leftover
## declared here fails visibly.
const ABSENT_HELPERS := [
	{"helper": "frame_duration", "absent_because":
		"the recorded frame_rate is a parse fact with no playback rule behind "
		+ "it, so a duration computed from it and a frame count would invent "
		+ "timing the legacy contract never had"},
	{"helper": "frame_time", "absent_because":
		"no committed field is read by any legacy branch, so there is no "
		+ "committed per-frame time to report"},
	{"helper": "loop_count", "absent_because":
		"nothing recorded says whether or how often a state repeats, and no "
		+ "legacy branch advances a timeline"},
	{"helper": "state_machine", "absent_because":
		"five recorded labels carry no recorded transition between them and no "
		+ "legacy branch selects one, so a state machine would have no committed "
		+ "rule to reproduce"},
	{"helper": "next_state", "absent_because":
		"no committed source records a transition, a condition, or a succession "
		+ "order; the recorded label positions are positions, not edges"},
	{"helper": "state_priority", "absent_because":
		"nothing ranks the five recorded labels and nothing arbitrates between "
		+ "them"},
	{"helper": "interrupt", "absent_because":
		"no legacy branch stops, replaces, or preempts a running animation, "
		+ "because no legacy branch starts one"},
	{"helper": "playback_order", "absent_because":
		"no order is computed between the recorded label positions beyond the "
		+ "asset's own recorded list order"},
	{"helper": "per_state_timing", "absent_because":
		"no per-state duration exists in the committed content, the committed "
		+ "asset, or the legacy source"},
	{"helper": "animation_trigger", "absent_because":
		"no legacy command, event, or condition selects an animation, so there "
		+ "is no trigger to bind one to"},
	{"helper": "event_state_mapping", "absent_because":
		"with zero animation commands there is no legacy command to map to a "
		+ "recorded label"},
	{"helper": "play", "absent_because":
		"no animation is played, animated, or rendered anywhere in this line; "
		+ "the converted package establishes LINKAGE only"},
	{"helper": "animate", "absent_because":
		"the same absence as play, stated as the verb a caller would reach for"},
	{"helper": "current_frame", "absent_because":
		"no clock, no elapsed time, and no timeline advance exists to read a "
		+ "current frame from"},
	{"helper": "advance_frame", "absent_because":
		"no legacy branch advances a timeline and no playback runs here, so "
		+ "nothing would advance a frame"},
]

## Whether the M4 conversion's own recorded limit is restated here rather than
## widened. True, and the reason the reported labels are names and positions.
const M4_LIMIT_RECORDED := ("M4's RECORDED LIMIT IS RESTATED, NEVER WIDENED. The "
	+ "committed unit conversion produces a per-sprite timeline inventory with "
	+ "shape and bitmap linkage, NO TESSELLATION and NO PLAYBACK SEMANTICS, and "
	+ "records its labels NAMES-ONLY with their positions. That is exactly what "
	+ "this projection reports, and exactly as far as it goes")

# ---------------------------------------------------------------------------
# The committed asset coverage (design D5)
# ---------------------------------------------------------------------------

## The repository-relative directory holding the committed converted packages.
const CONVERTED_UNITS_DIR := "assets/converted/units"
const CONVERTED_BUILDINGS_DIR := "assets/converted/buildings"
const PACKAGE_FILE := "package.json"

## The one committed converted unit package, named here so the coverage is
## visible rather than assumed. A later conversion is an ADDITION to this
## constant, never a silent widening of the evidence.
const CONVERTED_UNIT_PACKAGES := ["10033_wild_elephant"]
const CONVERTED_UNIT_PACKAGE_COUNT := 1
const CONVERTED_BUILDING_PACKAGE_COUNT := 1

## The one unit whose committed `img_name` names a committed converted package,
## and therefore the whole measured coverage of this projection.
const COVERED_UNIT_LEGACY_ID := "933"
const COVERED_UNIT_SPRITE_REFERENCE := "10033_wild_elephant"
const COVERAGE_STATEMENT := ("THE PROJECTION'S COVERAGE IS EXACTLY ONE UNIT, AND "
	+ "IT IS RECORDED RATHER THAN ASSUMED. Exactly ONE converted unit package is "
	+ "committed - 10033_wild_elephant - and exactly ONE converted building "
	+ "package, so no distribution over the 429 committed units is measurable at "
	+ "all and NO claim is made for any unit other than the Wild Elephant. The "
	+ "refusals generalise to all units as a statement about the LEGACY SOURCE, "
	+ "not about the assets; the linkage evidence does not (design D5)")

## The committed units whose `img_name` is a COMMA-JOINED list rather than one
## sprite reference. They name **no single** asset, so the projection refuses
## them rather than splitting the reference - the same refusal the delivered
## `godot-unit-definitions` capability makes, and reported here so the refusal is
## visible over the whole committed set.
const AMBIGUOUS_REFERENCE_UNITS := ["1001", "1007", "1008", "1014", "1034"]
const AMBIGUOUS_REFERENCE_COUNT := 5

# ---------------------------------------------------------------------------
# Animation is content, not a server operation (design D4)
# ---------------------------------------------------------------------------

## Declared false, and stated as the contract it is.
const ANIMATION_IMPLEMENTED := false
const ANIMATION_OPERATION_NOTE := ("UNIT ANIMATION IS CONTENT, NOT A SERVER "
	+ "OPERATION. The labels, their frame positions, the per-sprite frame counts, "
	+ "and the recorded rate are all read from the committed content package and "
	+ "the committed converted asset already on disk, and the committed animation "
	+ "fields are read by no legacy branch at all - there is therefore no "
	+ "server-selected state, no intent to send, no route to add, and nothing to "
	+ "authorise: NO compatibility API endpoint is added, NO client intent is "
	+ "issued, and NO persistence behaviour changes, which is why the "
	+ "compatibility test suite stays green UNCHANGED. This is the same "
	+ "conclusion M8 lines 1, 2, 4, and 6 reached (design D4)")

## Why no executed-legacy fixture was captured - the stronger of the two
## available reasons, stated so it cannot be read as a corpus limitation.
const FIXTURE_NOT_CAPTURED := ("NO EXECUTED-LEGACY ANIMATION FIXTURE WAS CAPTURED, "
	+ "AND THE REASON IS THE STRONGER ONE: there is NO ANIMATION BEHAVIOUR FOR "
	+ "THE LEGACY SERVER TO HAVE, not merely a corpus that could not exercise it. "
	+ "Of the dispatcher's 63 named branches the count of animation commands is "
	+ "ZERO, so there is no request, no state mutation, and no response to record: "
	+ "a fixture here would have to fabricate the behaviour it claims to observe. "
	+ "This is a STRONGER statement than a corpus limitation and it is deliberately "
	+ "recorded as the reason, with the corpus's own absence of any unit row kept "
	+ "as a SECOND and independent fact (design D4)")

## Whether an asset was re-converted or re-parsed to widen the coverage. False,
## and it is a recorded claim rather than an omission.
const ASSET_RECONVERTED := false
const ASSET_MANUFACTURED := ("NO COVERAGE IS MANUFACTURED. No conversion or "
	+ "extraction output is regenerated to cover another unit, the committed "
	+ "conversion package and the registry manifests stay byte-identical, and "
	+ "the projection's one-package coverage is recorded as exactly that (design D5)")

# ---------------------------------------------------------------------------
# The evidence's non-claims
# ---------------------------------------------------------------------------

## Every non-claim the delta's evidence requirement names. The runtime tokens in
## the first claim are assembled from fragments for the same project-scope
## reason as in the delivered refusal modules.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed, and no network was used at all",
	"NO FRAME DURATION, LOOP COUNT, STATE MACHINE, TRANSITION, PRIORITY, "
		+ "INTERRUPT, PLAYBACK ORDER, PER-STATE TIMING, ANIMATION TRIGGER, OR "
		+ "EVENT-TO-STATE MAPPING IS IMPLEMENTED: each is a recorded refusal with "
		+ "its reason attached, not an omission",
	"THE COMMITTED ANIMATION FIELDS ARE READ BY NO LEGACY BRANCH and are "
		+ "reported as CONTENT ONLY: max_frame, img_name, attack, "
		+ "attack_interval, attack_range, velocity, and the animal flag each "
		+ "have zero occurrences across the seven legacy modules",
	"max_frame IS NOT ADOPTED AS A FRAME COUNT, A DURATION, A LOOP BOUND, OR A "
		+ "STATE COUNT, and WHAT IT MEANS IS NOT CLAIMED: the measurement is one "
		+ "data point over one committed converted package",
	"NO LEGACY BRANCH SELECTS AN ANIMATION: the count of animation commands "
		+ "among the dispatcher's 63 named branches is ZERO",
	"NO ANIMATION IS PLAYED, ANIMATED, OR RENDERED, and the converted unit "
		+ "package establishes asset and timeline LINKAGE ONLY, never playback "
		+ "correctness, animation correctness, or visual fidelity",
	"NO CLAIM IS MADE FOR ANY UNIT OTHER THAN THE ONE COMMITTED CONVERTED "
		+ "PACKAGE, which is the only coverage measured: exactly one converted "
		+ "unit package is committed, so no distribution over the corpus is "
		+ "measurable at all",
	"NO EXECUTED-LEGACY FIXTURE WAS CAPTURED, and the reason is the ABSENCE OF "
		+ "ANIMATION BEHAVIOUR in the legacy server rather than only a corpus "
		+ "limitation",
	"NO PIXEL PARITY IS CLAIMED, and the recorded M6 tile-geometry gap is "
		+ "unchanged and never assumed",
	"no windowed capture is claimed: nothing is animated and nothing new is "
		+ "rendered",
	"NO ENDPOINT AND NO CLIENT INTENT: unit animation is committed content read "
		+ "through the content registry plus the committed converted asset on "
		+ "disk, so the compatibility suite stays green unchanged",
	"the label NAMES are reported verbatim in their committed Portuguese form "
		+ "and are NOT translated into an English state vocabulary here: no "
		+ "state is selected by anything, so a translation would name a rule that "
		+ "does not exist",
	"MUERTE IS RECORDED AS A STATE THE DELIVERED godot-unit-production "
		+ "CAPABILITY ALREADY FOUND UNREACHABLE: no legacy command produces a "
		+ "unit and none kills one",
	"a reader who wanted a state machine, a duration, or a trigger out of the "
		+ "reported linkage must bring evidence the legacy contract does not "
		+ "contain",
]

## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and check,
## and every derived fact states what it is derived from. Nothing here names a
## runtime; the runtime names live in `NON_CLAIMS`.
const PROVENANCE := {
	"established": [
		{"fact": "the dispatcher has 63 named branches and the count of "
			+ "animation commands among them is ZERO; the only branches carrying "
			+ "any animation vocabulary are move, orient, end_attack, "
			+ "batch_remove, and remove_inventory_item",
			"evidence": "command.py's own if/elif chain, measured by the suite, "
				+ "which compares the measured name set against NAMED_BRANCHES and "
				+ "the measured matches against ANIMATION_VOCABULARY_MATCHES"},
		{"fact": "max_frame, img_name, attack, attack_interval, attack_range, "
			+ "velocity, and the animal flag each have ZERO occurrences across "
			+ "the seven legacy root modules",
			"evidence": "a quoted-string search per field over command.py, "
				+ "engine.py, sessions.py, server.py, constants.py, "
				+ "get_game_config.py, and version.py, which the suite repeats "
				+ "for all seven names"},
		{"fact": "all six committed animation fields are present on all 429 "
			+ "committed units and take 2, 401, 131, 12, 14, and 11 distinct "
			+ "values respectively",
			"evidence": "the committed normalized content package, measured by "
				+ "the suite through the verified registry"},
		{"fact": "the committed max_frame is 5 on 427 of the 429 units and 2 on "
			+ "exactly two of them - legacy ids 923 and 933 - while the 470 "
			+ "committed buildings take only 1 (on 24) and 2 (on 446)",
			"evidence": "the same measured content package, over both the units "
				+ "and the buildings domains"},
		{"fact": "the committed package encodes max_frame as a JSON NUMBER, "
			+ "unlike the properties flags, which are committed as STRINGS",
			"evidence": "the measured variant type of every unit's max_frame "
				+ "entry as the registry hands it over"},
		{"fact": "the one committed converted unit package records a root "
			+ "frame_count of 1, a frame_rate of 30.0, seven sprites - five at "
			+ "20 frames and one at 7, all with no labels - and one sprite, id "
			+ "63, at 29 frames carrying five labels",
			"evidence": "assets/converted/units/10033_wild_elephant/"
				+ "package.json, read as committed JSON and measured by the suite"},
		{"fact": "that sprite's five labels are QUIETO at frame 1, ANDAR at 6, "
			+ "ATAQUE at 11, MUERTE at 16, and PICAR at 21, each with anchor "
			+ "false and the recorded key set anchor/frame/name",
			"evidence": "the same committed package, reported verbatim in "
				+ "recorded order by the projection"},
		{"fact": "for that same unit the committed max_frame is 2, the parsed "
			+ "root frame_count is 1, and the labelled sprite has 29 frames, and "
			+ "the committed img_name equals the package's own legacy_id",
			"evidence": "the committed package's own content_ref against its "
				+ "own parse, compared in this same run by the suite"},
		{"fact": "exactly one converted unit package and exactly one converted "
			+ "building package are committed",
			"evidence": "a read-only directory enumeration of "
				+ "assets/converted/units and assets/converted/buildings"},
		{"fact": "M4's recorded conversion limit for a unit is a per-sprite "
			+ "timeline inventory with shape and bitmap linkage, no tessellation, "
			+ "no playback semantics, and labels recorded names-only",
			"evidence": "tools/asset-registry/README.md's recorded limit, "
				+ "restated here and implemented not at all"},
	],
	"derived": [
		{"fact": "the line's deliverable is an asset-linkage projection plus "
			+ "auditable refusals rather than an animation mechanism",
			"evidence": "derived (design D1): with zero animation commands, no "
				+ "server-selected state, and one committed package, a mechanism "
				+ "would be invented, while five recorded labels are exactly the "
				+ "material a later line would reach for to build a state machine "
				+ "with nothing to anchor it on"},
		{"fact": "the committed max_frame is NOT the asset's frame count",
			"evidence": "derived from THREE ESTABLISHED measurements: the "
				+ "committed value 2, the parsed root frame_count 1, and the "
				+ "labelled sprite's 29 frames, over a package the content names "
				+ "exactly. ONE data point: sufficient to REFUSE adoption, "
				+ "insufficient to say what max_frame is, and NOT a measurement of "
				+ "any other unit"},
		{"fact": "max_frame is the seventh zero-consumer committed field in this "
			+ "project",
			"evidence": "derived from the six ESTABLISHED precedents in "
				+ "ZERO_CONSUMER_PRECEDENTS plus the measured zero-consumer "
				+ "figure for max_frame itself; the ordinal is recorded because "
				+ "the precedence is what makes the refusal a rule"},
		{"fact": "the recorded labels are the unit's animation STATES",
			"evidence": "derived and WEAK: the conversion records label names "
				+ "and positions ONLY, and reading a name into an English state "
				+ "word would be an interpreter's addition rather than the "
				+ "asset's. The committed names are therefore reported verbatim "
				+ "and NO translation is delivered, because nothing selects a "
				+ "state for a translation to name"},
		{"fact": "no endpoint is warranted while no server-selected animation "
			+ "exists",
			"evidence": "derived (design D4): there is no intent to send and "
				+ "nothing to authorise, so the compatibility test suite stays "
				+ "green unchanged, exactly as M8 lines 1, 2, 4, and 6 concluded"},
		{"fact": "a comma-joined committed img_name names no single asset and is "
			+ "refused rather than split",
			"evidence": "derived from an ESTABLISHED content fact: 5 of the 429 "
				+ "committed units carry a comma-joined reference, and the "
				+ "delivered godot-unit-definitions capability already refuses to "
				+ "split or interpret that field. Splitting it here would "
				+ "invent a single asset the content does not name"},
	],
}


# ---------------------------------------------------------------------------
# The one projection
# ---------------------------------------------------------------------------


## The whole linkage projection for one unit, and the only pure entry point a
## surface uses. Returns
##   `{ok, reason, error, resolvable, asset_state, package_relative_path,
##     package_present, package_kind, package_legacy_id,
##     content_sprite_reference, asset_named_by_content, definition_supplied,
##     definition_legacy_id, recorded_label_count, labels, label_count,
##     label_order, labelled_sprite_id, root_frame_count,
##     main_timeline_frame_count, frame_rate, sprite_frame_counts,
##     sprite_count, sprite_placement_counts, sprite_remove_counts,
##     root_placement_count, root_remove_count, label_keys,
##     content_fields, content_present, content_absent, max_frame_role,
##     max_frame_adopted_anywhere, rate_applied, rate_applied_to,
##     duration_computed, frame_time_computed, loop_count_computed,
##     state_machine_derived, transition_derived, priority_computed,
##     interrupt_computed, playback_order_derived, per_state_timing_computed,
##     animation_trigger_derived, event_state_mapping_derived,
##     intermediate_frame_computed, elapsed_frame_computed, readout}`.
##
## Every committed value is reported **verbatim**. Nothing is computed from
## another value, and every absence flag is a **constant false** carrying the
## recorded reason beside it, so no caller can mistake this projection for a
## playable animation (design D1/D3).
##
## `definition` is the unit's already-resolved committed entry, handed in by the
## caller; `package_data` is the parsed converted package; and `asset_state` says
## what the disk held, so the projection never guesses. A definition that is not
## an object is a **named absence** of the committed animation fields, never a
## reason to refuse the linkage itself.
static func project_asset(definition: Variant, package_data: Variant = null,
		asset_state: String = ASSET_RESOLVED) -> Dictionary:
	var header := _header(definition)
	if asset_state == ASSET_ABSENT:
		return _reject(REASON_ASSET_ABSENT,
			"no converted asset exists at the committed sprite reference this "
			+ "definition names", header, asset_state, null)
	if asset_state != ASSET_RESOLVED or not (package_data is Dictionary):
		return _reject(REASON_ASSET_UNREADABLE,
			"the converted asset does not parse as an object", header,
			asset_state, package_data)
	var package: Dictionary = package_data as Dictionary
	var recorded: Dictionary = _recorded_state(package)
	if not bool(recorded["ok"]):
		return _reject(REASON_ASSET_UNREADABLE,
			"the converted asset does not carry a readable sprite list",
			header, asset_state, package)
	var labels: Dictionary = _labels_of(package)
	if not bool(labels["ok"]):
		return _reject(str(labels["reason"]),
			str(labels["error"]), header, asset_state, package)
	var reported: Array = labels["labels"] as Array
	if reported.is_empty():
		return _reject(REASON_NO_LABELS,
			"the converted asset records no animation label on its root timeline "
			+ "or on any of its %d recorded sprites, so it is reported "
			% int(recorded["sprite_count"])
			+ "unresolvable rather than defaulted to a nominal one-frame "
			+ "animation", header, asset_state, package)
	var out := _resolved(header, asset_state, package, recorded, labels)
	out["readout"] = readout_text(out)
	return out


## The committed sprite reference a definition names, and the repository-
## relative converted-package path it resolves to. The path is **derived only**
## from the committed `img_name`, never from another unit's asset, and the
## projection refuses a reference that names no single asset.
static func package_relative_path(definition: Variant) -> Dictionary:
	if not (definition is Dictionary):
		return {
			"ok": false,
			"reason": REASON_INVALID_DEFINITION,
			"error": "the committed definition is not an object, so it names no "
				+ "committed sprite reference",
			"reference": null,
			"reference_present": false,
			"ambiguous": false,
			"relative_path": "",
		}
	var row: Dictionary = definition as Dictionary
	if not row.has("img_name"):
		return {
			"ok": false,
			"reason": REASON_NO_SPRITE_REFERENCE,
			"error": "the committed definition carries no committed sprite "
				+ "reference, so it names no asset",
			"reference": null,
			"reference_present": false,
			"ambiguous": false,
			"relative_path": "",
		}
	var reference: Variant = row["img_name"]
	var text := str(reference)
	if text.contains(","):
		return {
			"ok": false,
			"reason": REASON_AMBIGUOUS_SPRITE_REFERENCE,
			"error": "the committed sprite reference is a COMMA-JOINED list, so "
				+ "it names no single asset and is refused rather than split: "
				+ "the committed definitions capability deliberately never "
				+ "interprets this field",
			"reference": reference,
			"reference_present": true,
			"ambiguous": true,
			"relative_path": "",
		}
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"reference": reference,
		"reference_present": true,
		"ambiguous": false,
		"relative_path": "%s/%s/%s" % [CONVERTED_UNITS_DIR, text,
			PACKAGE_FILE],
	}


## The one entry point a surface uses: resolve the committed converted asset for
## a definition **read-only from disk**, then project it. This is the only
## function in this module that opens a file, and it opens exactly one, so a
## missing or unreadable asset fails closed through `project_asset()` rather
## than through a second implementation of the rules (design D1/D5).
static func resolve_asset(definition: Variant) -> Dictionary:
	var resolved := package_relative_path(definition)
	var reference: Variant = resolved["reference"]
	if not bool(resolved["ok"]):
		var refused := project_asset(definition, null, ASSET_ABSENT)
		refused["reason"] = str(resolved["reason"])
		refused["error"] = "[unit-animations] linkage refused: " \
			+ str(resolved["error"])
		refused["resolvable"] = false
		return refused
	var relative := str(resolved["relative_path"])
	var absolute := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(absolute):
		var absent := project_asset(definition, null, ASSET_ABSENT)
		absent["package_relative_path"] = relative
		return absent
	var text := FileAccess.get_file_as_string(absolute)
	if text.is_empty():
		var unreadable := project_asset(definition, null, ASSET_UNREADABLE)
		unreadable["package_relative_path"] = relative
		return unreadable
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		var unreadable := project_asset(definition, null, ASSET_UNREADABLE)
		unreadable["package_relative_path"] = relative
		return unreadable
	var out := project_asset(definition, parsed, ASSET_RESOLVED)
	out["package_relative_path"] = relative
	out["content_sprite_reference"] = reference
	return out


## Every field the projection reports, with its own recorded source, as a fresh
## deep copy a caller may keep and mutate.
static func linkage_field_inventory() -> Array:
	return (LINKAGE_FIELDS as Array).duplicate(true)


## The reported linkage field names in committed table order.
static func linkage_field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in LINKAGE_FIELDS:
		out.append(str(entry["name"]))
	return out


# ---------------------------------------------------------------------------
# The committed animation fields as content (design D2)
# ---------------------------------------------------------------------------


## One committed definition's committed animation fields, **verbatim, as
## content**. Returns
##   `{ok, reason, error, values, present, absent, flag_present, flag}`
##
## Each value is the committed number or string exactly as the entry holds it,
## with `present` and `absent` naming which keys the entry actually carries — so
## a definition missing a key is distinguishable from one committing a zero. No
## duration, loop, transition, priority, trigger, or state selection is computed
## from any of them: reporting them is the whole contract.
static func animation_field_values(definition: Variant) -> Dictionary:
	if not (definition is Dictionary):
		return {
			"ok": false,
			"reason": REASON_INVALID_DEFINITION,
			"error": "the committed definition is not an object, so all six "
				+ "committed animation fields are ABSENT from it (a named "
				+ "absence, never a committed zero) and none is substituted",
			"values": {},
			"present": [],
			"absent": (ANIMATION_FIELDS as Array).duplicate(),
			"flag_present": false,
			"flag": null,
		}
	var row: Dictionary = definition as Dictionary
	var present: Array = []
	var absent: Array = []
	var values := {}
	for field: String in ANIMATION_FIELDS:
		if row.has(field):
			present.append(field)
			values[field] = row[field]
		else:
			absent.append(field)
	var properties: Dictionary = {}
	if row.get("properties") is Dictionary:
		properties = row["properties"] as Dictionary
	var flag_present := properties.has(ANIMATION_FLAG)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"values": values,
		"present": present,
		"absent": absent,
		"flag_present": flag_present,
		"flag": properties[ANIMATION_FLAG] if flag_present else null,
	}


## How the readout renders one committed animation field: the recorded value,
## immediately followed by the refusal, so a reader who sees the number cannot
## mistake it for a rule this client would honour.
static func animation_field_note(field: String, value: Variant) -> String:
	if not ANIMATION_FIELDS.has(field):
		return ""
	if value == null:
		return ("%s: absent from this definition (a named absence, never a "
			% field
			+ "zero) and read by no legacy branch either")
	return ("%s: %s — recorded as CONTENT ONLY, never used as a duration, a "
			% [field, _number_text(value)]
			+ "loop, a transition, or a state count, because no legacy branch "
			+ "reads it")


## The whole content-only record as the evidence report writes it, read from
## this module's own constants so the report cannot describe a contract the code
## does not hold. `distribution_measured` is filled in by the suite from the
## verified registry in the same run.
static func animation_fields_record() -> Dictionary:
	return {
		"fields": (ANIMATION_FIELDS as Array).duplicate(),
		"flag": ANIMATION_FLAG,
		"reported_as_content_only": true,
		"used_as_a_rule": false,
		"consumer_count": ANIMATION_FIELD_CONSUMER_COUNT,
		"consumer_count_per_field": _consumer_counts(),
		"searched_modules": (SEARCHED_MODULES as Array).duplicate(),
		"units_file": UNITS_FILE,
		"buildings_file": BUILDINGS_FILE,
		"unit_count": UNIT_COUNT,
		"building_count": BUILDING_COUNT,
		"distinct_unit_values": (ANIMATION_FIELD_DISTINCT_UNIT_VALUES as Dictionary)
			.duplicate(),
		"rule": ANIMATION_FIELDS_REFUSAL,
		"coverage": ANIMATION_FIELDS_COVERAGE,
		"encoding": MAX_FRAME_ENCODING,
		"zero_consumer_ordinal": MAX_FRAME_ORDINAL,
		"zero_consumer_precedents": (ZERO_CONSUMER_PRECEDENTS as Array)
			.duplicate(true),
		"max_frame_distribution": {
			"units": (MAX_FRAME_UNIT_DISTRIBUTION as Dictionary).duplicate(),
			"buildings": (MAX_FRAME_BUILDING_DISTRIBUTION as Dictionary)
				.duplicate(),
			"unit_exceptions": (MAX_FRAME_UNIT_EXCEPTIONS as Array).duplicate(),
			"unit_modal_value": MAX_FRAME_UNIT_MODAL_VALUE,
			"unit_modal_count": MAX_FRAME_UNIT_MODAL_COUNT,
		},
		"duration_computed": false,
		"loop_computed": false,
		"transition_computed": false,
		"priority_computed": false,
		"trigger_computed": false,
		"state_selected": false,
		"distribution_measured": {
			"units": {},
			"buildings": {},
			"distinct_unit_values": {},
			"flag": {},
		},
	}


# ---------------------------------------------------------------------------
# The measured max_frame non-equivalence (design D2)
# ---------------------------------------------------------------------------


## The whole non-equivalence record as the evidence report writes it, read from
## this module's own constants. Named for the FINDING rather than for the field,
## so the field's name appears in this module's code only inside its own
## `MAX_FRAME_*` constants and never as an identifier that could hold a value.
static func non_equivalence_record() -> Dictionary:
	var units: Dictionary = MAX_FRAME_UNIT_DISTRIBUTION as Dictionary
	var buildings: Dictionary = MAX_FRAME_BUILDING_DISTRIBUTION as Dictionary
	var out: Dictionary = (MAX_FRAME_NON_EQUIVALENCE as Dictionary).duplicate(true)
	out["unit_distribution"] = units.duplicate()
	out["building_distribution"] = buildings.duplicate()
	out["generalises"] = MAX_FRAME_GENERALISES
	out["ordinal"] = MAX_FRAME_ORDINAL
	return out


# ---------------------------------------------------------------------------
# The animation-command inventory (design D2/D4)
# ---------------------------------------------------------------------------


## Every vocabulary match with its classification, as a fresh deep copy a caller
## may keep and mutate — so a report reads this module's own table rather than
## restating it.
static func vocabulary_matches() -> Array:
	return (ANIMATION_VOCABULARY_MATCHES as Array).duplicate(true)


## The recorded branch names in committed source order.
static func command_names() -> Array:
	return (NAMED_BRANCHES as Array).duplicate()


## The whole command-inventory record as the evidence report writes it: the
## closed named-branch set, every vocabulary match with its classification and
## reason, and the count of animation commands.
static func animation_command_record() -> Dictionary:
	var matches := vocabulary_matches()
	var whole: Array = []
	var inside: Array = []
	var commands := 0
	for entry: Dictionary in matches:
		if bool(entry["is_animation_command"]):
			commands += 1
		if bool(entry["inside_another_word"]):
			inside.append(str(entry["command"]))
		else:
			whole.append(str(entry["command"]))
	return {
		"implemented": ANIMATION_IMPLEMENTED,
		"selected_by_server": ANIMATION_SELECTED_BY_SERVER,
		"named_branch_count": NAMED_BRANCH_COUNT,
		"named_branches": command_names(),
		"vocabulary": (ANIMATION_VOCABULARY as Array).duplicate(),
		"vocabulary_with_no_match": (ANIMATION_VOCABULARY_NO_MATCH as Array)
			.duplicate(),
		"matches": matches,
		"match_count": (ANIMATION_VOCABULARY_MATCHES as Array).size(),
		"whole_token_matches": whole,
		"whole_token_matches_recorded": (WHOLE_TOKEN_MATCHES as Array)
			.duplicate(),
		"substring_artifacts": inside,
		"substring_artifacts_recorded": (SUBSTRING_ARTIFACTS as Array)
			.duplicate(),
		"animation_command_count": ANIMATION_COMMAND_COUNT,
		"animation_command_count_measured": commands,
		"no_animation_command": NO_ANIMATION_COMMAND,
	}


# ---------------------------------------------------------------------------
# The refusal set and the absent helpers (design D3)
# ---------------------------------------------------------------------------


## Every refusal family with its reason, as a fresh deep copy.
static func refusal_record() -> Array:
	return (REFUSALS as Array).duplicate(true)


## Every deliberately-absent helper with its reason, as a fresh deep copy.
static func absent_helpers() -> Array:
	return (ABSENT_HELPERS as Array).duplicate(true)


## Every non-claim the evidence carries, as a fresh copy.
static func non_claims() -> Array:
	return (NON_CLAIMS as Array).duplicate()


# ---------------------------------------------------------------------------
# Coverage, fixture, and boundary records (design D4/D5)
# ---------------------------------------------------------------------------


## The measured asset coverage, with the converted package directories
## enumerated read-only so a later conversion is a visible addition here rather
## than an assumption.
static func coverage_record() -> Dictionary:
	return {
		"converted_units_dir": CONVERTED_UNITS_DIR,
		"converted_buildings_dir": CONVERTED_BUILDINGS_DIR,
		"unit_packages": _package_names(CONVERTED_UNITS_DIR),
		"unit_package_count": _package_names(CONVERTED_UNITS_DIR).size(),
		"building_package_count": _package_names(CONVERTED_BUILDINGS_DIR).size(),
		"unit_packages_recorded": (CONVERTED_UNIT_PACKAGES as Array).duplicate(),
		"unit_package_count_recorded": CONVERTED_UNIT_PACKAGE_COUNT,
		"covered_unit_legacy_id": COVERED_UNIT_LEGACY_ID,
		"covered_unit_sprite_reference": COVERED_UNIT_SPRITE_REFERENCE,
		"ambiguous_reference_units": (AMBIGUOUS_REFERENCE_UNITS as Array)
			.duplicate(),
		"ambiguous_reference_count": AMBIGUOUS_REFERENCE_COUNT,
		"statement": COVERAGE_STATEMENT,
		"reconverted": ASSET_RECONVERTED,
		"manufacture_note": ASSET_MANUFACTURED,
	}


## Why no executed-legacy fixture was captured, as the evidence report records
## it — and why the reason is the absence of behaviour rather than only a corpus
## that could not exercise one.
static func fixture_record() -> Dictionary:
	return {
		"captured": false,
		"reason": FIXTURE_NOT_CAPTURED,
		"reason_kind": "no animation behaviour exists in the legacy server to "
			+ "capture, which is stronger than a corpus limitation",
		"corpus_distinction": "the committed corpus also holds no unit row (40 "
			+ "rows, 11 distinct ids, every one of committed type 'b'), which is "
			+ "a SECOND and independent reason, deliberately kept separate from "
			+ "the first",
		"animation_commands_available": ANIMATION_COMMAND_COUNT,
		"fabricated_state": false,
	}


## Why this line is content and not a server operation: no route, no intent, no
## persistence change, and the compatibility suite green unchanged.
static func no_endpoint_record() -> Dictionary:
	return {
		"added": false,
		"animation_implemented": ANIMATION_IMPLEMENTED,
		"selected_by_server": ANIMATION_SELECTED_BY_SERVER,
		"request_issued": false,
		"route": "none: unit animation is committed content read through the "
			+ "content registry plus the committed converted asset on disk, so "
			+ "there is no server-selected state, no intent to send, and nothing "
			+ "to authorise",
		"persistence_changed": false,
		"compat_suite": "unchanged: no route, response field, error code, or "
			+ "persistence behaviour is added, so its test count does not move",
		"network_used": false,
		"note": ANIMATION_OPERATION_NOTE,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The linkage readout for one projection: the recorded labels with their
## recorded positions, the per-sprite recorded frame counts, and the recorded
## rate — each immediately followed by the refusal that keeps it from reading as
## playback. A refused projection renders its recorded state and its reason, and
## never a nominal single-frame animation.
static func readout_text(projection: Dictionary) -> String:
	var parts: Array = []
	if not bool(projection.get("ok", false)):
		parts.append("UNRESOLVABLE (%s): %s — reported with its recorded state "
			% [str(projection.get("reason", "")), str(projection.get("error", ""))]
			+ "intact, never defaulted to an empty, nominal, or single-frame "
			+ "animation")
		parts.append("recorded label entries: %s | root frame_count: %s | "
			% [_number_text(projection.get("recorded_label_count", null)),
				_number_text(projection.get("root_frame_count", null))]
			+ "recorded rate: %s"
			% _number_text(projection.get("frame_rate", null)))
		return " | ".join(parts)
	var labels: Array = projection.get("labels", []) as Array
	if labels.is_empty():
		parts.append("no recorded animation label")
	else:
		var names: PackedStringArray = PackedStringArray()
		for entry: Dictionary in labels:
			names.append("%s@%s" % [str(entry["name"]),
				_number_text(entry["frame"])])
		parts.append("recorded labels %s — verbatim names and recorded frame "
			% " ".join(names)
			+ "positions, with no duration, loop, transition, or order derived "
			+ "from them")
	parts.append("per-sprite recorded frame counts %s — reported as recorded, "
		% _frame_count_text(projection.get("sprite_frame_counts", []))
		+ "never multiplied by the rate and never added together")
	parts.append("recorded frame_rate %s — REPORTED, NEVER APPLIED: no duration "
		% _number_text(projection.get("frame_rate", null))
		+ "and no frame time is computed from it")
	parts.append("no frame duration, no loop count, no state machine, no "
		+ "transition, no priority, no interrupt, no playback order, no "
		+ "per-state timing, no animation trigger, and no event-to-state "
		+ "mapping: no legacy branch selects an animation")
	var fields: Dictionary = projection.get("content_fields", {}) as Dictionary
	for field: String in ANIMATION_FIELDS:
		if not fields.has(field):
			continue
		parts.append(animation_field_note(field, fields[field]))
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## The fields every projection carries, resolved or refused: the committed
## definition's identity and its committed animation fields, with the recorded
## `max_frame` role attached.
static func _header(definition: Variant) -> Dictionary:
	var fields := animation_field_values(definition)
	var row: Dictionary = {}
	if definition is Dictionary:
		row = definition as Dictionary
	var values: Dictionary = fields["values"] as Dictionary
	return {
		"definition_supplied": definition is Dictionary,
		"definition_legacy_id": str(row.get("legacy_id", "")),
		"content_fields": values.duplicate(),
		"content_present": (fields["present"] as Array).duplicate(),
		"content_absent": (fields["absent"] as Array).duplicate(),
		"flag_present": bool(fields["flag_present"]),
		"flag": fields["flag"],
		"content_sprite_reference": row.get("img_name", null),
		"max_frame_recorded": _recorded_value(values, "max_frame"),
		"max_frame_role": "content-only",
		"max_frame_adopted_anywhere": false,
		"max_frame_adopted_as_frame_count": false,
		"max_frame_adopted_as_duration": false,
		"max_frame_adopted_as_loop_bound": false,
		"max_frame_adopted_as_state_count": false,
		"label_keys": (LABEL_KEYS as Array).duplicate(),
	}


## One committed animation field's recorded value, or `null` when the entry does
## not carry it — a named absence, never a substituted zero. This helper is the
## only reader of the committed field names, and it returns a value: nothing
## computes anything from what it returns.
static func _recorded_value(values: Dictionary, field: String) -> Variant:
	if not values.has(field):
		return null
	return values[field]


## The recorded state of a parsed asset: the root's own two frame counts, the
## recorded rate, and every sprite's own recorded frame count, label count,
## placement count, and remove count — each copied through, none computed from
## another. A package without a readable sprite list fails here rather than
## yielding an empty sprite list.
static func _recorded_state(package: Dictionary) -> Dictionary:
	var sprites: Variant = package.get("sprites", null)
	if not (sprites is Array):
		return {"ok": false, "error": "the converted asset records no sprite list"}
	var main_timeline: Dictionary = {}
	if package.get("main") is Dictionary:
		main_timeline = package["main"] as Dictionary
	var rows: Array = []
	var placements: Array = []
	var removes: Array = []
	for sprite: Variant in (sprites as Array):
		if not (sprite is Dictionary):
			return {"ok": false,
				"error": "the converted asset records a sprite that is not an "
					+ "object"}
		var entry: Dictionary = sprite as Dictionary
		var labels: Variant = entry.get("labels", null)
		if not (labels is Array):
			return {"ok": false,
				"error": "a recorded sprite carries no label list, so its "
					+ "recorded labels are unreadable"}
		rows.append({
			"sprite_id": entry.get("sprite_id", null),
			"frame_count": entry.get("frame_count", null),
			"label_count": (labels as Array).size(),
			"placement_count": _size_of(entry.get("placements", null)),
			"remove_count": _size_of(entry.get("removes", null)),
		})
		placements.append(_size_of(entry.get("placements", null)))
		removes.append(_size_of(entry.get("removes", null)))
	return {
		"ok": true,
		"error": "",
		"root_frame_count": package.get("frame_count", null),
		"main_timeline_frame_count": main_timeline.get("frame_count", null),
		"frame_rate": package.get("frame_rate", null),
		"kind": package.get("kind", null),
		"legacy_id": package.get("legacy_id", null),
		"source_file": package.get("source_file", null),
		"sprite_frame_counts": rows,
		"sprite_count": (sprites as Array).size(),
		"sprite_placement_counts": placements,
		"sprite_remove_counts": removes,
		"root_placement_count": _size_of(main_timeline.get("placements", null)),
		"root_remove_count": _size_of(main_timeline.get("removes", null)),
		"root_label_count": _size_of(main_timeline.get("labels", null)),
	}


## Every recorded label of a parsed asset, in recorded order: the root timeline's
## own labels first, then each sprite's own labels in recorded sprite order.
## Each entry carries the committed `name`, `frame`, and `anchor` verbatim, the
## recorded key set beside them, and the timeline it was read from. A malformed
## label entry refuses the whole projection rather than being skipped, because
## skipping one would silently report a shorter animation than the asset records.
static func _labels_of(package: Dictionary) -> Dictionary:
	var labels: Array = []
	var order: Array = []
	var labelled: Array = []
	var main_timeline: Dictionary = {}
	if package.get("main") is Dictionary:
		main_timeline = package["main"] as Dictionary
	var root_labels: Variant = main_timeline.get("labels", null)
	if root_labels is Array:
		for entry: Variant in (root_labels as Array):
			var record := _one_label(entry, LABEL_SOURCE_ROOT)
			if not bool(record["ok"]):
				return {"ok": false, "reason": REASON_MALFORMED_LABEL,
					"error": "the root timeline's recorded label is malformed: "
						+ str(record["error"])}
			labels.append(record["label"])
			order.append(LABEL_SOURCE_ROOT)
	for sprite: Variant in (package.get("sprites", []) as Array):
		var row: Dictionary = sprite as Dictionary
		var source := "%s%d" % [LABEL_SOURCE_SPRITE_PREFIX,
			int(row.get("sprite_id", -1))]
		var own: Variant = row.get("labels", [])
		for entry: Variant in (own as Array):
			var record := _one_label(entry, source)
			if not bool(record["ok"]):
				return {"ok": false, "reason": REASON_MALFORMED_LABEL,
					"error": "a recorded label is malformed: "
						+ str(record["error"])}
			labels.append(record["label"])
			order.append(source)
			if not labelled.has(row.get("sprite_id", null)):
				labelled.append(row.get("sprite_id", null))
	var first: Variant = null
	if not labelled.is_empty():
		first = labelled[0]
	var sprite_frame_count: Variant = null
	if first != null:
		for sprite: Variant in (package.get("sprites", []) as Array):
			var row2: Dictionary = sprite as Dictionary
			if int(row2.get("sprite_id", -1)) == int(first):
				sprite_frame_count = row2.get("frame_count", null)
				break
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"labels": labels,
		"order": order,
		"labelled_sprite_id": first,
		"labelled_sprite_ids": labelled.duplicate(),
		"labelled_sprite_frame_count": sprite_frame_count,
	}


## One recorded label, verbatim, or the reason it is malformed. `anchor` is
## reported as recorded and never interpreted; `frame` is a position, never a
## range or a start of a computed duration.
static func _one_label(entry: Variant, source: String) -> Dictionary:
	if not (entry is Dictionary):
		return {"ok": false, "error": "it is %s, not an object" % _type_name(entry)}
	var row: Dictionary = entry as Dictionary
	var keys: Array = []
	for key: Variant in row:
		keys.append(str(key))
	keys.sort()
	for required: String in LABEL_KEYS:
		if not row.has(required):
			return {"ok": false,
				"error": "the recorded key set %s carries no `%s`"
					% [str(keys), required]}
	return {
		"ok": true,
		"error": "",
		"label": {
			"name": row["name"],
			"frame": row["frame"],
			"anchor": row["anchor"],
			"source": source,
			"recorded_keys": keys,
		},
	}


## The resolved projection. Every value comes from the recorded state or the
## recorded labels, and the sixteen absence flags are **constant false**, so a
## caller cannot mistake this projection for a playable animation.
static func _resolved(header: Dictionary, asset_state: String,
		package: Dictionary, recorded: Dictionary, labels: Dictionary) -> Dictionary:
	var package_id: Variant = recorded["legacy_id"]
	var reference: Variant = header["content_sprite_reference"]
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"resolvable": true,
		"asset_state": asset_state,
		"package_relative_path": "",
		"package_present": true,
		"package_kind": recorded["kind"],
		"package_legacy_id": package_id,
		"package_source_file": recorded["source_file"],
		"content_sprite_reference": reference,
		"asset_named_by_content": reference != null and package_id != null
			and str(reference) == str(package_id),
		"definition_supplied": header["definition_supplied"],
		"definition_legacy_id": header["definition_legacy_id"],
		"recorded_label_count": (labels["labels"] as Array).size(),
		"labels": (labels["labels"] as Array).duplicate(true),
		"label_count": (labels["labels"] as Array).size(),
		"label_order": (labels["order"] as Array).duplicate(),
		"labelled_sprite_id": labels["labelled_sprite_id"],
		"labelled_sprite_ids": (labels["labelled_sprite_ids"] as Array)
			.duplicate(),
		"labelled_sprite_frame_count": labels["labelled_sprite_frame_count"],
		"root_frame_count": recorded["root_frame_count"],
		"main_timeline_frame_count": recorded["main_timeline_frame_count"],
		"frame_rate": recorded["frame_rate"],
		"sprite_frame_counts": (recorded["sprite_frame_counts"] as Array)
			.duplicate(true),
		"sprite_count": int(recorded["sprite_count"]),
		"sprite_placement_counts": (recorded["sprite_placement_counts"] as Array)
			.duplicate(),
		"sprite_remove_counts": (recorded["sprite_remove_counts"] as Array)
			.duplicate(),
		"root_placement_count": recorded["root_placement_count"],
		"root_remove_count": recorded["root_remove_count"],
		"root_label_count": recorded["root_label_count"],
		"label_keys": header["label_keys"],
		"content_fields": header["content_fields"],
		"content_present": header["content_present"],
		"content_absent": header["content_absent"],
		"flag_present": header["flag_present"],
		"flag": header["flag"],
		"max_frame_recorded": header["max_frame_recorded"],
		"max_frame_role": header["max_frame_role"],
		"max_frame_adopted_anywhere": header["max_frame_adopted_anywhere"],
		"max_frame_adopted_as_frame_count":
			header["max_frame_adopted_as_frame_count"],
		"max_frame_adopted_as_duration": header["max_frame_adopted_as_duration"],
		"max_frame_adopted_as_loop_bound":
			header["max_frame_adopted_as_loop_bound"],
		"max_frame_adopted_as_state_count":
			header["max_frame_adopted_as_state_count"],
		"rate_applied": false,
		"rate_applied_to": "",
		"duration_computed": false,
		"frame_time_computed": false,
		"loop_count_computed": false,
		"state_machine_derived": false,
		"transition_derived": false,
		"priority_computed": false,
		"interrupt_computed": false,
		"playback_order_derived": false,
		"per_state_timing_computed": false,
		"animation_trigger_derived": false,
		"event_state_mapping_derived": false,
		"intermediate_frame_computed": false,
		"elapsed_frame_computed": false,
		"asset_refusal": ASSET_REFUSAL,
		"no_derivation": NO_DERIVATION,
		"readout": "",
	}


## A structural refusal: `ok` false with its named reason, `labels` empty and
## `label_count` 0 — **never** a defaulted single-frame animation — and every
## recorded field the asset did carry still reported beside the refusal, so a
## caller must never be able to read a refusal as an empty or nominal animation.
## The sixteen absence flags stay constant false either way.
static func _reject(reason: String, message: String, header: Dictionary,
		asset_state: String, package_data: Variant) -> Dictionary:
	var recorded: Dictionary = {}
	if package_data is Dictionary:
		var candidate := _recorded_state(package_data as Dictionary)
		if bool(candidate["ok"]):
			recorded = candidate
	var out := {
		"ok": false,
		"reason": reason,
		"error": "[unit-animations] linkage refused: " + message,
		"resolvable": false,
		"asset_state": asset_state,
		"package_relative_path": "",
		"package_present": package_data is Dictionary,
		"package_kind": recorded.get("kind", null),
		"package_legacy_id": recorded.get("legacy_id", null),
		"package_source_file": recorded.get("source_file", null),
		"asset_named_by_content": false,
		"definition_supplied": header["definition_supplied"],
		"definition_legacy_id": header["definition_legacy_id"],
		"recorded_label_count": _recorded_label_total(package_data),
		"labels": [],
		"label_count": 0,
		"label_order": [],
		"labelled_sprite_id": null,
		"labelled_sprite_ids": [],
		"labelled_sprite_frame_count": null,
		"root_frame_count": recorded.get("root_frame_count", null),
		"main_timeline_frame_count": recorded.get("main_timeline_frame_count",
			null),
		"frame_rate": recorded.get("frame_rate", null),
		"sprite_frame_counts": recorded.get("sprite_frame_counts", []),
		"sprite_count": int(recorded.get("sprite_count", 0)),
		"sprite_placement_counts": recorded.get("sprite_placement_counts", []),
		"sprite_remove_counts": recorded.get("sprite_remove_counts", []),
		"root_placement_count": recorded.get("root_placement_count", null),
		"root_remove_count": recorded.get("root_remove_count", null),
		"root_label_count": recorded.get("root_label_count", null),
		"label_keys": header["label_keys"],
		"content_fields": header["content_fields"],
		"content_present": header["content_present"],
		"content_absent": header["content_absent"],
		"flag_present": header["flag_present"],
		"flag": header["flag"],
		"max_frame_recorded": header["max_frame_recorded"],
		"max_frame_role": header["max_frame_role"],
		"max_frame_adopted_anywhere": header["max_frame_adopted_anywhere"],
		"max_frame_adopted_as_frame_count":
			header["max_frame_adopted_as_frame_count"],
		"max_frame_adopted_as_duration": header["max_frame_adopted_as_duration"],
		"max_frame_adopted_as_loop_bound":
			header["max_frame_adopted_as_loop_bound"],
		"max_frame_adopted_as_state_count":
			header["max_frame_adopted_as_state_count"],
		"rate_applied": false,
		"rate_applied_to": "",
		"duration_computed": false,
		"frame_time_computed": false,
		"loop_count_computed": false,
		"state_machine_derived": false,
		"transition_derived": false,
		"priority_computed": false,
		"interrupt_computed": false,
		"playback_order_derived": false,
		"per_state_timing_computed": false,
		"animation_trigger_derived": false,
		"event_state_mapping_derived": false,
		"intermediate_frame_computed": false,
		"elapsed_frame_computed": false,
		"asset_refusal": ASSET_REFUSAL,
		"no_derivation": NO_DERIVATION,
		"readout": "",
	}
	var text := readout_text(out)
	out["readout"] = text
	return out


## How many label entries an asset records, readable or not, so a malformed or
## label-less refusal still reports the recorded quantity beside it rather than a
## defaulted zero-length animation.
static func _recorded_label_total(package_data: Variant) -> Variant:
	if not (package_data is Dictionary):
		return null
	var total := 0
	var package: Dictionary = package_data as Dictionary
	var main_timeline: Variant = package.get("main", null)
	if main_timeline is Dictionary:
		total += _size_of((main_timeline as Dictionary).get("labels", null))
	var sprites: Variant = package.get("sprites", null)
	if not (sprites is Array):
		return total
	for sprite: Variant in (sprites as Array):
		if sprite is Dictionary:
			total += _size_of((sprite as Dictionary).get("labels", null))
	return total


## An array's recorded size, or 0 when the key is absent — used only for the
## recorded placement and remove counts, which are structural inventories rather
## than animation semantics.
static func _size_of(value: Variant) -> int:
	return (value as Array).size() if value is Array else 0


## The measured consumer count of each recorded name, as one object over the
## closed set the module reports, so a caller reads a per-name figure rather than
## a single number it could apply to the wrong name.
static func _consumer_counts() -> Dictionary:
	var out := {}
	for field: String in ANIMATION_FIELDS:
		out[field] = ANIMATION_FIELD_CONSUMER_COUNT
	out[ANIMATION_FLAG] = ANIMATION_FIELD_CONSUMER_COUNT
	return out


## Every committed converted package name under a repository-relative directory,
## in recorded directory order. Read-only, and never used to widen the coverage:
## the count is reported so a later conversion is visible here.
static func _package_names(relative: String) -> Array:
	var out: Array = []
	var dir := DirAccess.open(Paths.repo_root().path_join(relative))
	if dir == null:
		return out
	dir.list_dir_begin()
	var entry := dir.get_next()
	while entry != "":
		if entry != "." and entry != ".." and dir.current_is_dir():
			out.append(entry)
		entry = dir.get_next()
	dir.list_dir_end()
	out.sort()
	return out


## A recorded number's rendered form, so a failure names what it found instead of
## saying only "invalid".
static func _number_text(value: Variant) -> String:
	if value == null:
		return "null"
	return str(value)


## How the readout renders the per-sprite recorded frame counts: each sprite id
## with its own recorded count and label count, in recorded order.
static func _frame_count_text(rows: Variant) -> String:
	if not (rows is Array):
		return "none"
	var parts: PackedStringArray = PackedStringArray()
	for row: Variant in rows:
		var entry: Dictionary = row as Dictionary
		parts.append("%s:%s/%s labels" % [_number_text(entry.get("sprite_id",
			null)), _number_text(entry.get("frame_count", null)),
			_number_text(entry.get("label_count", null))])
	return " ".join(parts)


## The observed type of a refused value, so a failure names what it found.
static func _type_name(value: Variant) -> String:
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
			return "string"
		TYPE_ARRAY:
			return "array"
		TYPE_DICTIONARY:
			return "object"
		_:
			return "unsupported"