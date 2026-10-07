extends RefCounted
## Typed, read-only projection of the dead-hero ledger (OpenSpec
## `godot-unit-behaviors` "The dead-hero ledger is projected, and the gates are
## named" / "The three-door command inventory records which command reaches the
## ledger" / "No syringe cost, and the committed syringes field is content
## only" / "No combat is resolved, and no placement validation is invented" /
## "No executed-legacy behaviour fixture is claimed" / "Unit-behaviour evidence
## and claim limits", design D1-D8).
##
## ## What this module is, and what it deliberately is NOT
##
## Unlike the three refusal lines before it (`production_flow.gd`,
## `unit_movement.gd`, `unit_animations.gd`), **this line delivers a
## mechanism**: `privateState["deadHeroes"]` is a string-keyed count per item
## id, and three dispatcher branches reach it.  This module projects that
## ledger, names **both** of the increment gates the legacy helper evaluates
## and **no third**, records the increment/decrement shapes and the
## **delete-at-zero** rule verbatim, and inventories the three doors.
##
## ## The counts are reported verbatim and none is derived from another (D1)
##
## `project_ledger()` keeps each recorded string item id with its recorded
## count **exactly as recorded**: no threshold, no cap, no clamp, and no count
## derived from a committed `syringes` value.  `expected_ledger()` reproduces
## `engine.resurrect_hero` (`engine.py:172-181`) exactly — an absent key is a
## silent no-op, a count of `1` **deletes** the key rather than storing a zero,
## and a count above `1` decrements and keeps the key.
##
## ## An unresolvable ledger is REFUSED with its recorded state intact (D1)
##
## An absent ledger, a non-object ledger, a **non-string key**, and a
## **non-integer count** are each reported `ok: false` / `resolvable: false`
## with a named reason, `entries` empty, and every OTHER recorded fact — the
## recorded type, whether the key was present, and the recorded keys — still
## reported beside the refusal.  Nothing is ever defaulted to an empty ledger
## presented as a resolved one.
##
## ## BOTH gates are named with their source lines, and no third is invented
##
## `GATES` records exactly the two conditions `engine.push_dead_unit`
## (`engine.py:149-170`) evaluates: the dying row's **player team 1**
## (`engine.py:151`) and its committed `resurrectable > 0`
## (`engine.py:159,162`).  `GATE_COUNT` is asserted as 2 by the suite, so a
## third eligibility rule fails the run rather than appearing quietly later.
##
## ## `kill` reaches NOTHING, and that is the finding (D2)
##
## Of the dispatcher's 63 named branches, **three** are inventoried and **two**
## reach the ledger: `sell` reaches it only behind the `reason == "KILL"` guard
## and only through the `push_dead_unit` **engine helper**, and `resurrect_hero`
## decrements it.  `kill` deletes the row and **never** touches the ledger, so
## a combat kill records no death.  `ENGINE_HELPERS` records the two helpers
## separately so the named-branch count and the ledger-reaching count stay
## distinguishable.
##
## ## No syringe cost, no combat, and no placement validation (D3/D5)
##
## `syringes` is committed on all 429 units with **6** distinct values and has
## **zero** legacy consumers, so **no syringe cost is ever charged and no stored
## resource moves** — `used_syringe` is bound from `args[4]` and **discarded**
## (`command.py:630`).  The seven committed combat fields each measure **zero**
## legacy consumers, so no damage, outcome, defence, hit chance, or life
## arithmetic is derived from any of them.  The legacy branch re-places the row
## with **no** occupancy, bounds, type, or terrain check, and this module
## reproduces that absence rather than filling it.
##
## ## Purity
##
## This module holds no node, no clock, no request, and no transport, and reads
## nothing from disk, so the same functions serve the client, the hermetic suite,
## and the deterministic report.

# ---------------------------------------------------------------------------
# The ledger's own save location and shape (design D1)
# ---------------------------------------------------------------------------

## The committed player-state key the ledger lives under, and the ledger's own
## key inside it (`engine.push_dead_unit`, `engine.py:163`).
const PRIVATE_STATE_KEY := "privateState"
const LEDGER_KEY := "deadHeroes"

## The ledger is a **string-keyed count per item id**: `deadHeroes[str(item_id)]`
## (`engine.py:164-167`).  Both halves are load-bearing — the helper writes
## `str(item[0])` and reads `str(item)` — so an integer-keyed reading is a
## different shape, not a tolerated one.
const LEDGER_SHAPE := ("A STRING-KEYED COUNT PER ITEM ID. push_dead_unit writes "
	+ "deadHeroes[str(item[0])] and creates the key at 1 when it is absent; "
	+ "resurrect_hero reads str(item), so both halves of the shape are "
	+ "load-bearing and an integer-keyed reading is a different shape, not a "
	+ "tolerated one")

## The migration, recorded and never treated as gameplay: `version.py:26-30`
## initialises the key to `None` and coerces a non-object to `{}`.  No branch
## ever creates the key, so a save that never held it receives an empty ledger
## from the migration rather than from gameplay.
const LEDGER_MIGRATION_NOTE := ("privateState['deadHeroes'] is initialised to "
	+ "None and then coerced to {} by version.py:26-30 ('Applied hospital "
	+ "fix'). That is a SAVE MIGRATION, not behaviour: no branch ever creates "
	+ "the key, so a save that never held it receives an empty ledger from the "
	+ "migration rather than from gameplay. Recorded, never treated as a rule")

## The recorded increment shape, verbatim from `engine.py:163-168`.
const INCREMENT_SHAPE := ("deadHeroes[str(item_id)] += 1 when the key is "
	+ "already present, and deadHeroes[str(item_id)] = 1 when it is absent — the "
	+ "key is CREATED AT 1, never at 0 and never pre-seeded (engine.py:164-167)")

## The recorded decrement shape, verbatim from `engine.py:177-181`.
const DECREMENT_SHAPE := ("num_heroes = deadHeroes[itemstr] - 1; if num_heroes "
	+ "<= 0 the key is DELETED, else deadHeroes[itemstr] -= 1 "
	+ "(engine.py:177-181). An item id the ledger does not hold is a SILENT "
	+ "NO-OP: the helper returns before touching anything (engine.py:175-176)")

## The delete-at-zero rule, stated as the contract it is.
const DELETE_AT_ZERO := ("REACHING ZERO DELETES THE KEY; IT NEVER STORES A ZERO. "
	+ "engine.resurrect_hero computes num_heroes = count - 1 and, when that is "
	+ "not greater than zero, executes `del deadHeroes[itemstr]` "
	+ "(engine.py:178-179). A ledger holding key: 0 is a state the legacy "
	+ "helpers cannot produce, so a post-execution proof that finds one is a "
	+ "failure, not a zero (design D1)")

## The fail-closed reasons this projection can produce, and no sixth.
const REASON_LEDGER_ABSENT := "ledger_absent"
const REASON_LEDGER_NOT_OBJECT := "ledger_not_object"
const REASON_KEY_NOT_TEXT := "ledger_key_not_text"
const REASON_COUNT_NOT_INTEGER := "ledger_count_not_integer"

# ---------------------------------------------------------------------------
# Both gates, and the machine-readable form of "no third" (design D1)
# ---------------------------------------------------------------------------

const GATE_TEAM := {
	"gate": "player_team_one",
	"checks": "the dying row's slot 7 (player) equals 1",
	"source": "engine.py:151 (push_dead_unit)",
	"committed": true,
	"note": "push_dead_unit returns False when item[7] != 1, so a row on "
		+ "another team never enters the ledger no matter how resurrectable its "
		+ "committed properties say it is",
}

const GATE_RESURRECTABLE := {
	"gate": "resurrectable_positive",
	"checks": "the committed properties object carries resurrectable AND "
		+ "int(resurrectable) > 0",
	"source": "engine.py:159,162 (push_dead_unit)",
	"committed": true,
	"note": "push_dead_unit returns False when the flag is ABSENT "
		+ "(engine.py:159-160) and when it is present but not greater than zero "
		+ "(engine.py:162), so an absent flag is a REFUSAL, never a zero",
}

## Both gates, in the helper's own order.
const GATES := [GATE_TEAM, GATE_RESURRECTABLE]

## The count the table above fixes. Asserted by the suite so a third gate
## cannot be added without failing the run.
const GATE_COUNT := 2

const NO_THIRD_GATE := ("EXACTLY TWO GATES EXIST AND NO THIRD IS INVENTED. "
	+ "push_dead_unit (engine.py:149-170) performs two checks and no more: the "
	+ "row's player team (engine.py:151) and the committed resurrectable flag "
	+ "(engine.py:159,162). Everything else a reader might expect is absent "
	+ "from the helper: no level check, no cost check, no capacity check, no "
	+ "cooldown, no per-type check, and no check that the row is a unit rather "
	+ "than a building. Adding any of them here would make this client STRICTER "
	+ "than the legacy server, which is a parity break in the opposite "
	+ "direction from the usual risk (design D1)")

## The committed player team the increment gate names.
const PLAYER_TEAM := 1

## The committed `properties` flag the increment gate names, read from the RAW
## configuration string by the legacy helper.
const RESURRECTABLE_FLAG := "resurrectable"
const PROPERTIES_FIELD := "properties"

## How the legacy helper reads the flag: through `get_attribute_from_item_id`
## and then `json.loads(properties)` (`engine.py:154-162`). The committed
## normalized package stores `properties` as an **object** instead — the R2
## coercion boundary M8 line 1 recorded — so the two agree on *values* and
## never on *representation*.
const RAW_PROPERTIES_NOTE := ("BOTH LEGACY READS GO THROUGH "
	+ "get_attribute_from_item_id(...) THEN json.loads(properties), so the "
	+ "server reads the RAW configuration STRING while the committed normalized "
	+ "package stores properties as an OBJECT (engine.py:154-162). That is the "
	+ "R2 coercion boundary M8 line 1 recorded: the legacy reads are not "
	+ "against the committed normalized bytes, and the two agree on VALUES, "
	+ "never on representation")

# ---------------------------------------------------------------------------
# The three-door inventory (design D2)
# ---------------------------------------------------------------------------

## Every command that reaches or bypasses the ledger, with an explicit
## `reaches_ledger` statement and what else it mutates.  The suite re-derives
## the branch names out of `command.py` and compares both the set and the
## count, so a future dispatcher edit fails the run.
const COMMAND_INVENTORY := [
	{
		"command": "kill",
		"kind": "dispatcher-branch",
		"source": "command.py:169-181",
		"reaches_ledger": false,
		"effect": "looks the row up, deletes it, and prints; it NEVER touches "
			+ "privateState['deadHeroes'], so a combat kill records no death in "
			+ "the ledger",
		"mutates_also": "map['items']: the addressed row is deleted",
	},
	{
		"command": "sell",
		"kind": "dispatcher-branch",
		"source": "command.py:149-167",
		"reaches_ledger": true,
		"guard": "reason == 'KILL'",
		"through": "push_dead_unit (engine helper, engine.py:149-170)",
		"effect": "calls push_dead_unit ONLY when the reason is the combat "
			+ "reason, which increments deadHeroes[str(item_id)] by one, creating "
			+ "the key at 1, subject to BOTH gates",
		"mutates_also": "map['items']: the addressed row is deleted",
		"closed_in_practice": "the delivered godot-building-sell capability "
			+ "derives its own sell reason and accepts none from the client, so "
			+ "the KILL guard is closed in practice while remaining open in the "
			+ "source. That recorded claim is CORRECT AND UNCHANGED: this guard "
			+ "is the ONLY door into the dead-hero ledger",
	},
	{
		"command": "resurrect_hero",
		"kind": "dispatcher-branch",
		"source": "command.py:625-635",
		"reaches_ledger": true,
		"through": "resurrect_hero (engine helper, engine.py:172-181)",
		"effect": "decrements deadHeroes[str(item_id)] and DELETES the key when "
			+ "the count reaches zero",
		"mutates_also": "map['items']: map_add_item re-places the row at "
			+ "CLIENT-SUPPLIED index/x/y with no occupancy, bounds, type, or "
			+ "terrain check (engine.py:8-31)",
		"discarded_argument": "args[4], used_syringe, is READ and DISCARDED",
	},
]

## The engine helpers, recorded separately so the named-branch count and the
## ledger-reaching command count stay distinguishable: `push_dead_unit` is an
## ENGINE HELPER, not a dispatcher branch, which is what keeps those two counts
## separately meaningful.
const ENGINE_HELPERS := [
	{
		"helper": "push_dead_unit",
		"source": "engine.py:149-170",
		"is_dispatcher_branch": false,
		"effect": "the increment, behind both gates",
	},
	{
		"helper": "resurrect_hero",
		"source": "engine.py:172-181",
		"is_dispatcher_branch": false,
		"effect": "the decrement, deleting the key at zero",
	},
]

## The 63 named dispatcher branches the committed catalog records.  The suite
## re-derives this set out of `command.py` and compares it against this list
## **and** the count, so a new branch fails the run rather than being read as an
## unrecorded death door.
const NAMED_BRANCH_COUNT := 63

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

## The two branches that reach the ledger, and the one that bypasses it.
const LEDGER_REACHING_COMMANDS := ["sell", "resurrect_hero"]
const LEDGER_REACHING_COMMAND_COUNT := 2
const BRANCHES_THAT_BYPASS_LEDGER := ["kill"]

## The three commands the inventory names, as a closed set the suite asserts.
const INVENTORY_COMMANDS := ["kill", "sell", "resurrect_hero"]

## The inventory as the evidence report records it, read from this module's own
## tables so the report cannot describe a contract the code does not hold.
static func inventory_record() -> Dictionary:
	return {
		"command_inventory": (COMMAND_INVENTORY as Array).duplicate(true),
		"engine_helpers": (ENGINE_HELPERS as Array).duplicate(true),
		"inventory_commands": (INVENTORY_COMMANDS as Array).duplicate(),
		"ledger_reaching_commands": (LEDGER_REACHING_COMMANDS as Array)
			.duplicate(),
		"ledger_reaching_command_count": LEDGER_REACHING_COMMAND_COUNT,
		"branches_that_bypass_ledger": (BRANCHES_THAT_BYPASS_LEDGER as Array)
			.duplicate(),
		"named_branch_count": NAMED_BRANCH_COUNT,
		"push_dead_unit_is_a_branch": false,
		"kill_reaches_ledger": false,
		"sell_guard": "reason == 'KILL'",
		"resurrect_hero_discarded_argument": "args[4] (used_syringe)",
	}

# ---------------------------------------------------------------------------
# The committed behavioural fields (design D2/D3)
# ---------------------------------------------------------------------------

## The committed behavioural fields with **zero** legacy consumers across the
## seven legacy root modules, each with its MEASURED number of distinct
## committed values across the 429 committed unit definitions.  Reported as
## CONTENT ONLY.
##
## MEASURED CORRECTION against `docs/legacy-unit-behaviors.md`: that record
## says "twenty" of "twenty-two" behavioural committed fields have zero legacy
## consumers and then **names twenty-one** of them.  The named list is
## authoritative — it is countable, and every one of its twenty-one entries
## measures **zero** — so the field count was **21**, and with the two fields
## that DO have consumers the behavioural total was **23**, not 22.  The
## rejected figures are retained below rather than dropped, and every figure
## here is re-measured by the suite in the same run.
##
## LATER AMENDMENT by `godot-construction-assist`: 21 -> 22, and 23 -> 24,
## because one further field (`giftable`) was measured to qualify and had been
## MISSED.  That is a correction to the earlier measurement, not a rescope, and
## the pre-amendment figure is retained below so the chain stays auditable.
const ZERO_CONSUMER_FIELDS := [
	{"field": "attack", "legacy_reads": 0, "unit_distinct": 131},
	{"field": "attack_interval", "legacy_reads": 0, "unit_distinct": 12},
	{"field": "attack_range", "legacy_reads": 0, "unit_distinct": 14},
	{"field": "best_against", "legacy_reads": 0, "unit_distinct": 5},
	{"field": "best_against_mult", "legacy_reads": 0, "unit_distinct": 5},
	{"field": "defense", "legacy_reads": 0, "unit_distinct": 1},
	{"field": "life", "legacy_reads": 0, "unit_distinct": 150},
	{"field": "velocity", "legacy_reads": 0, "unit_distinct": 11},
	{"field": "collect_type", "legacy_reads": 0, "unit_distinct": 2},
	{"field": "collect_xp", "legacy_reads": 0, "unit_distinct": 6},
	{"field": "max_collects", "legacy_reads": 0, "unit_distinct": 1},
	{"field": "syringes", "legacy_reads": 0, "unit_distinct": 6},
	{"field": "volume", "legacy_reads": 0, "unit_distinct": 3},
	{"field": "training_time", "legacy_reads": 0, "unit_distinct": 1},
	{"field": "unit_capacity", "legacy_reads": 0, "unit_distinct": 3},
	{"field": "expiration", "legacy_reads": 0, "unit_distinct": 1},
	{"field": "population", "legacy_reads": 0, "unit_distinct": 5},
	{"field": "min_level", "legacy_reads": 0, "unit_distinct": 21},
	{"field": "activation", "legacy_reads": 0, "unit_distinct": 1},
	{"field": "gift_level", "legacy_reads": 0, "unit_distinct": 8,
		"building_distinct": 11},
	{"field": "build_time", "legacy_reads": 0, "unit_distinct": 2},
	# ADDED by `godot-construction-assist`, which measured the gift fields over
	# the committed content.  `gift_level` was ALREADY here (units-only) and is
	# COMPLETED with its buildings side; `giftable` was in NO census and is added.
	{"field": "giftable", "legacy_reads": 0, "unit_distinct": 2,
		"building_distinct": 2},
]

## The census is over the seven legacy modules, which is scope-free: a field
## qualifies if NOTHING reads it, whichever domain carries it. So `giftable`
## BELONGS in the table and its absence was a gap, not a decision -- the gap is
## recorded here because the amendment changed the count from 21 to 22 and a
## silently-changed pin is how a census rots.
##
## `legacy_reads: 0` for both gift fields is MEASURED, not asserted: zero
## whole-file occurrences and zero whole-word occurrences of either name across
## all seven modules above.
##
## The `building_distinct` column exists ONLY on the two rows
## `godot-construction-assist` measured. It is deliberately partial, and
## `BUILDING_MEASURED_FIELD_COUNT` pins the size of that partial set so it
## cannot quietly grow into a claim of full buildings-side coverage.
const BUILDING_MEASURED_FIELDS := ["gift_level", "giftable"]
const BUILDING_MEASURED_FIELD_COUNT := 2

## Zero-consumer fields, and the correction chain that produced each figure.
##
## The `_RECORDED` constants hold the investigation's REJECTED figures; the
## pre-amendment measurement is kept beside them so the chain reads
## investigation 20 -> measured 21 -> amended 22, rather than the amendment
## silently replacing a measurement a reader might still quote.
const ZERO_CONSUMER_COUNT := 22
const ZERO_CONSUMER_COUNT_PRE_AMEND := 21
const ZERO_CONSUMER_COUNT_RECORDED := 20
const BEHAVIOURAL_FIELD_COUNT := 24
const BEHAVIOURAL_FIELD_COUNT_RECORDED := 22

## The seven committed combat fields, as a closed set so "no combat is
## resolved" is checkable against a list rather than a phrase.
const COMBAT_FIELDS := [
	"attack", "defense", "life", "attack_interval", "attack_range",
	"best_against", "best_against_mult",
]
const COMBAT_FIELD_COUNT := 7

## The legacy root modules the zero-consumer claim is measured over.  A missing
## one is a **failure** in the suite, never a silently smaller search.
const SEARCHED_MODULES := ["command.py", "engine.py", "sessions.py", "server.py",
	"constants.py", "get_game_config.py", "version.py"]

## The committed domain sizes the distributions below are measured over.
const UNIT_COUNT := 429
const BUILDING_COUNT := 470

## The measured committed distribution of the two fields this line reads, so
## the eligibility it enforces is anchored in content rather than asserted.
##
## MEASURED CORRECTION against `docs/legacy-unit-behaviors.md`: that record
## reports `clicks_to_build` as "429 of 429 units, **3 distinct**".  Measured
## over the committed package the field takes **two** distinct values in total
## (`0` and `1`) and only **one** of them over the units, which is `0` on all
## 429.  The third value the record counts is not in the content: the buildings
## take `0` on 172 and `1` on 298, and the single committed special (id `925`,
## committed type `l`, "Expandable Land") is the 299th row with `1`.  The
## rejected figure is retained rather than quietly dropped.
const RESURRECTABLE_UNITS_POSITIVE := 426
const RESURRECTABLE_UNITS_OF := 429
const RESURRECTABLE_UNITS_ABSENT := 3
const RESURRECTABLE_BUILDINGS_POSITIVE := 0
const RESURRECTABLE_BUILDINGS_OF := 470
const RESURRECTABLE_UNIT_VALUE := "1"
const SYRINGES_UNIT_VALUES := {"0": 2, "1": 120, "2": 48, "3": 256, "4": 1, "5": 2}
const SYRINGES_UNIT_DISTINCT := 6
const SYRINGES_BUILDING_VALUES := {"0": 470}
const CLICKS_TO_BUILD_UNIT_VALUES := {"0": 429}
const CLICKS_TO_BUILD_BUILDING_VALUES := {"0": 172, "1": 298}
const CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT := 2
const CLICKS_TO_BUILD_DISTINCT_RECORDED := 3

const CLICKS_TO_BUILD_CORRECTION := ("CORRECTION, MEASURED AGAINST THE "
	+ "COMMITTED INVESTIGATION: that record reports clicks_to_build as '429 of "
	+ "429 units, 3 distinct'. Measured over the committed content package the "
	+ "field takes TWO distinct values in total (0 and 1) and only ONE of them "
	+ "over the units, which is 0 on all 429. The buildings take 0 on 172 and 1 "
	+ "on 298; the 299th row carrying 1 is the single committed SPECIAL (id "
	+ "925, committed type 'l', Expandable Land), which is neither a unit nor a "
	+ "building. The recorded 3 is retained beside the measured 2 so a later "
	+ "reader can re-derive the choice")

## The two behavioural committed fields that DO have legacy consumers, as one
## countable record.  `resurrectable` is the FIRST committed field in this
## project whose legacy consumer is a MUTATION OF PRIVATE STATE rather than a
## read, and that is the reason this line delivers a mechanism rather than a
## refusal.
const CONSUMED_BEHAVIOURAL_FIELDS := [
	{
		"field": RESURRECTABLE_FLAG,
		"kind": "properties flag",
		"legacy_reads": 2,
		"source": "engine.py:159,162 (push_dead_unit)",
		"units_positive": RESURRECTABLE_UNITS_POSITIVE,
		"units_of": RESURRECTABLE_UNITS_OF,
		"buildings_positive": RESURRECTABLE_BUILDINGS_POSITIVE,
		"buildings_of": RESURRECTABLE_BUILDINGS_OF,
		"note": "the FIRST committed field in this project whose legacy "
			+ "consumer is a MUTATION OF PRIVATE STATE rather than a read, and "
			+ "the reason this line delivers a mechanism rather than a refusal",
	},
	{
		"field": "clicks_to_build",
		"kind": "top-level item field",
		"legacy_reads": 1,
		"source": "engine.py:26 (map_add_item)",
		"units_distinct": 1,
		"units_distinct_recorded": CLICKS_TO_BUILD_DISTINCT_RECORDED,
		"unit_values": CLICKS_TO_BUILD_UNIT_VALUES,
		"building_values": CLICKS_TO_BUILD_BUILDING_VALUES,
		"note": "seeds attr['nc'] = 0 on a fresh team-1 placement when positive; "
			+ "that counter is owned by godot-building-construction and is "
			+ "referenced here, never reimplemented",
	},
]

const UNIT_ONLY_NOTE := ("resurrectable is a UNIT-ONLY committed flag: it is "
	+ "positive on 426 of the 429 committed unit definitions and on 0 of the "
	+ "470 committed building definitions, and it is carried by none of them, "
	+ "so it never appears on a building at all. That is why the committed "
	+ "corpus - which places only buildings - holds no resurrectable row, and "
	+ "why a one-shot executed-legacy fixture is impossible here without first "
	+ "manufacturing a unit row")

## Every behavioural `properties` flag on the committed unit definitions with
## its measured positive count.  All of them have zero legacy consumers.
const UNIT_PROPERTY_FLAGS := [
	{"flag": "animal", "positive": 2},
	{"flag": "bulldozable", "positive": 424},
	{"flag": "fireman", "positive": 1},
	{"flag": "ft_armored", "positive": 157},
	{"flag": "ft_building", "positive": 2},
	{"flag": "ft_flying", "positive": 135},
	{"flag": "ft_ground", "positive": 134},
	{"flag": "harvester", "positive": 5},
	{"flag": "healer", "positive": 3},
	{"flag": "human", "positive": 126},
	{"flag": "mechanic", "positive": 301},
	{"flag": "resurrectable", "positive": 426},
	{"flag": "seeStealthUnits", "positive": 427},
	{"flag": "waterborne", "positive": 2},
	{"flag": "worker", "positive": 5},
]
const UNIT_PROPERTY_FLAG_COUNT := 15

## The three units that carry NO `resurrectable` key at all, named so the
## "426 of 429" figure's other three rows are visible rather than averaged
## away.  The flag's ABSENCE is a refusal in the legacy helper
## (`engine.py:159-160`), never a zero.
const UNITS_WITHOUT_RESURRECTABLE := ["923", "933", "1176"]

# ---------------------------------------------------------------------------
# The refusals (design D3/D5)
# ---------------------------------------------------------------------------

const NO_SYRINGE_COST := ("NO SYRINGE COST IS CHARGED AND NO STORED RESOURCE "
	+ "MOVES. `used_syringe` is bound from args[4] (command.py:630) and is NEVER "
	+ "READ AGAIN anywhere in the branch, so it is DISCARDED, and the committed "
	+ "`syringes` field it would be paid in has ZERO occurrences across the "
	+ "seven legacy modules, so the legacy server charges nothing. Charging one "
	+ "would invent an economy the repository does not contain. The no-cost "
	+ "claim is proved by the endpoint's 'every stored resource is unchanged' "
	+ "half, which compares the FULL resource set rather than a subset")

const SYRINGE_DISCARD_NOTE := ("args[4] is bound to the local `used_syringe` "
	+ "(command.py:630) and is NEVER READ AGAIN anywhere in the branch, so the "
	+ "value is inert and is DISCARDED. The committed counterpart is the item's "
	+ "own `syringes` field, which is carried by all 429 committed units and all "
	+ "470 committed buildings, takes 6 distinct values over the units, and has "
	+ "ZERO occurrences across the seven legacy modules. The response NEVER "
	+ "ECHOES the discarded argument")

const NO_COMBAT := ("NO COMBAT IS RESOLVED OF ANY KIND. attack, defense, life, "
	+ "attack_interval, attack_range, best_against, and best_against_mult each "
	+ "have ZERO legacy consumers, so the committed numbers are CONTENT and "
	+ "never rules: this contract computes no damage, no attack outcome, no "
	+ "defence application, no hit chance, and no life or interval arithmetic, "
	+ "and a reader who wanted a combat model out of them must bring evidence "
	+ "the legacy contract does not contain. The ledger's own two-sided counter "
	+ "is the WHOLE death model the server has")

const NO_PLACEMENT_VALIDATION := ("NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN "
	+ "VALIDATION IS ADDED TO THE REVIVED PLACEMENT. The legacy branch "
	+ "re-places the row through engine.map_add_item (engine.py:8-31) with no "
	+ "such check, and this client reproduces that absence rather than filling "
	+ "it: inventing an occupancy check here would make this client STRICTER "
	+ "than the legacy server. The gap is recorded as a Server v1 / M13 "
	+ "requirement, exactly as godot-building-move, godot-building-place, and "
	+ "godot-building-upgrade already do")

## The three refusals, as one machine-readable list, in the delta's order.
const REFUSALS := [
	{"refusal": "syringe_cost", "implemented": false, "rule": NO_SYRINGE_COST},
	{"refusal": "combat_resolution", "implemented": false, "rule": NO_COMBAT},
	{"refusal": "placement_validation", "implemented": false,
		"rule": NO_PLACEMENT_VALIDATION},
]
const REFUSAL_COUNT := 3

## `clicks_to_build` is REFERENCED and NOT REIMPLEMENTED (design D6).
const CLICKS_TO_BUILD_BOUNDARY := ("clicks_to_build is REFERENCED AND NOT "
	+ "REIMPLEMENTED. Its single legacy read is engine.py:26, inside "
	+ "map_add_item, where a positive value seeds attr['nc'] = 0 on a freshly "
	+ "placed team-1 row (engine.py:27-29). That counter is the "
	+ "construction-click counter already reported and deliberately not "
	+ "consumed by the delivered godot-building-construction capability, which "
	+ "owns it. This line records the relationship and reimplements nothing: the "
	+ "re-placement is executed by the UNCHANGED legacy map_add_item. Note also "
	+ "that the committed clicks_to_build is 0 on ALL 429 unit definitions, so a "
	+ "revived UNIT never seeds the counter at all - a measurement, not an "
	+ "assumption")

## The death/resurrection pairing is DERIVED, never asserted.
const DERIVED_PAIRING := ("THE DEATH/RESURRECTION PAIRING IS DERIVED, NOT "
	+ "ASSERTED. push_dead_unit and resurrect_hero are complementary and share "
	+ "privateState['deadHeroes'], but no comment and no dispatch path asserts "
	+ "that they are a pair: the legacy author's own comment on the increment "
	+ "says only 'Tries to push item to deadHeroes if it is ressurectable and "
	+ "on player team' (engine.py:150). Nothing in this client asserts the "
	+ "pairing as a server guarantee either")

## No executed-legacy fixture was captured, and WHY — a corpus limitation with
## a named cause, NOT the refusal lines' absence of behaviour.
const FIXTURE_NOT_CAPTURED := ("NO EXECUTED-LEGACY BEHAVIOUR FIXTURE WAS "
	+ "CAPTURED, AND THE REASON IS A CORPUS LIMITATION WITH A NAMED CAUSE - "
	+ "NOT, as on the three refusal lines before this one, the absence of "
	+ "behaviour. resurrectable is a UNIT-ONLY committed flag (positive on 426 "
	+ "of 429 units, on 0 of 470 buildings), the committed corpus places ONLY "
	+ "buildings across 40 rows and 40 distinct cells, so 0 of its placed rows "
	+ "are resurrectable and it places NO unit row at all, and its "
	+ "privateState['deadHeroes'] is present and {}. Capturing one would "
	+ "require MANUFACTURING A UNIT ROW first, which the delivered "
	+ "godot-unit-instances capability already refused and recorded as the right "
	+ "call. No unit row was manufactured in the committed corpus or in any "
	+ "delivered fixture directory (design D4)")

## The helpers this module deliberately does NOT provide (design D3/D5).  Each
## would compute a rule the legacy server never had, and the suite compares this
## module's whole static-function inventory against a pinned list AND against
## this list by name.
const ABSENT_HELPERS := [
	{"helper": "syringe_cost", "absent_because":
		"`syringes` has zero legacy consumers, so the legacy server charges "
		+ "nothing; a cost computed from it would invent an economy the "
		+ "repository does not contain"},
	{"helper": "charge_revive", "absent_because":
		"the same absence as syringe_cost, stated as the verb a caller would "
		+ "reach for"},
	{"helper": "resolve_damage", "absent_because":
		"none of the seven committed combat fields has a legacy consumer, so "
		+ "there is no committed damage rule to resolve"},
	{"helper": "apply_attack", "absent_because":
		"the same absence as resolve_damage: `attack` and `attack_interval` are "
		+ "content with zero consumers"},
	{"helper": "defend", "absent_because":
		"`defense` is a constant 1 on all 429 committed units and is read by no "
		+ "branch, so there is nothing to apply"},
	{"helper": "hit_chance", "absent_because":
		"no committed field records a probability and no branch draws a "
		+ "random number"},
	{"helper": "is_occupied", "absent_because":
		"the legacy resurrect_hero branch re-places the row with no occupancy "
		+ "check, so a stricter client would be a parity break in the opposite "
		+ "direction"},
	{"helper": "in_bounds", "absent_because":
		"the same absence as is_occupied, for the cell bounds the branch never "
		+ "checks"},
	{"helper": "terrain_at", "absent_because":
		"the same absence as is_occupied, for the terrain the branch never "
		+ "reads"},
	{"helper": "is_type_allowed", "absent_because":
		"the branch checks no item type: it re-places whatever item id the "
		+ "caller named"},
	{"helper": "revive_count_cap", "absent_because":
		"the engine sets no bound on the ledger, and a recorded absence is not "
		+ "permission to add one"},
	{"helper": "revive_cooldown", "absent_because":
		"no legacy branch reads a clock for a revival, so there is no committed "
		+ "cooldown to reproduce"},
]

## The evidence's non-claims (spec "Unit-behaviour evidence and claim
## limits").  The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in the delivered refusal modules.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed, and no network was used in the hermetic suite",
	"NO SYRINGE COST IS CHARGED AND NO STORED RESOURCE MOVES: `used_syringe` is "
		+ "read from args[4] and DISCARDED, and the committed `syringes` field "
		+ "has zero legacy consumers",
	"NO COMBAT IS RESOLVED: attack, defense, life, attack_interval, "
		+ "attack_range, best_against, and best_against_mult each have zero "
		+ "legacy consumers and are content, never rules",
	"NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED to the revived "
		+ "placement, which reproduces the legacy branch's recorded absence "
		+ "rather than filling it",
	"THE DEATH/RESURRECTION PAIRING IS DERIVED: the two legacy helpers are "
		+ "complementary and share the ledger, but nothing in the source asserts "
		+ "that they are a pair",
	"`clicks_to_build` IS REFERENCED AND NOT REIMPLEMENTED: its consumer is the "
		+ "construction-click counter owned by godot-building-construction",
	"NO EXECUTED-LEGACY BEHAVIOUR FIXTURE WAS CAPTURED, and the reason is the "
		+ "corpus holding no resurrectable row - a corpus limitation with a named "
		+ "cause, NOT the refusal lines' absence of behaviour",
	"NO UNIT ROW WAS MANUFACTURED in the committed corpus or in any delivered "
		+ "fixture directory",
	"NO UNIT IS REVIVED AGAINST THE COMMITTED CORPUS: its ledger is present and "
		+ "empty and 0 of its 40 placed rows are resurrectable",
	"THE ZERO-CONSUMER FIELD COUNT IS 21, NOT THE 20 the committed "
		+ "investigation states: that record names twenty-one fields and every "
		+ "one of them measures zero, so the behavioural total is 23, not 22",
	"`clicks_to_build` TAKES TWO DISTINCT VALUES OVER THE COMMITTED CONTENT, NOT "
		+ "the three the committed investigation states",
	"no pixel parity is claimed, and the recorded M6 tile-geometry gap is "
		+ "unchanged and never assumed",
	"no windowed capture is claimed: nothing is rendered and no revived unit is "
		+ "drawn",
	"NO COVERAGE IS MANUFACTURED: the content package, the committed saves, and "
		+ "the delivered fixture directories stay byte-identical",
]

## The established-versus-derived provenance split this line reports as its own
## section.  Every established fact names the evidence a reader can go and
## check, and every derived fact states what it is derived from.
const PROVENANCE := {
	"established": [
		{"fact": "privateState['deadHeroes'] is a string-keyed count per item "
			+ "id, written as deadHeroes[str(item[0])] and read as str(item)",
			"evidence": "engine.py:163-181, re-measured by the suite"},
		{"fact": "push_dead_unit is an ENGINE HELPER and not a dispatcher "
			+ "branch, and it performs exactly two checks",
			"evidence": "engine.py:149-170 against the dispatcher's own 63 "
				+ "branches, both re-derived by the suite"},
		{"fact": "the two gates are the row's player team (engine.py:151) and "
			+ "the committed resurrectable flag being greater than zero "
			+ "(engine.py:159,162)",
			"evidence": "the same two lines, and the suite compares GATES "
				+ "against them by name"},
		{"fact": "kill deletes the row and never touches the ledger",
			"evidence": "command.py:169-181, whose whole body is the lookup, "
				+ "the delete, and the print"},
		{"fact": "sell reaches the ledger only behind reason == 'KILL' and only "
			+ "through the engine helper",
			"evidence": "command.py:158-160 against the recorded reason codes"},
		{"fact": "resurrect_hero decrements the ledger, DELETES the key at zero, "
			+ "re-places the row at client-supplied index/x/y, and DISCARDS "
			+ "args[4]",
			"evidence": "command.py:625-635 against engine.py:172-181 and "
				+ "engine.py:8-31"},
		{"fact": "the zero-consumer count is 21 and every one of them measures "
			+ "zero occurrences across the seven legacy root modules",
			"evidence": "a quoted-token search per field over command.py, "
				+ "engine.py, sessions.py, server.py, constants.py, "
				+ "get_game_config.py, and version.py, which the suite repeats"},
		{"fact": "resurrectable is positive on 426 of the 429 committed units, "
			+ "carried by 426 of them, and on 0 of the 470 committed buildings",
			"evidence": "the committed normalized content package, measured by "
				+ "the suite through the verified registry"},
		{"fact": "syringes takes 6 distinct values over the units and 0 is the "
			+ "only value over the buildings",
			"evidence": "the same measured content package"},
		{"fact": "clicks_to_build is 0 on all 429 committed units and takes "
			+ "exactly two distinct values over the content",
			"evidence": "the same measured content package, over both the "
				+ "units and the buildings domains"},
		{"fact": "the committed corpus records deadHeroes == {}, places 40 rows "
			+ "across 40 distinct cells, and every one of them is a committed "
			+ "building",
			"evidence": "tests/saves/fresh-player.json, measured by the suite "
				+ "and resolved against the verified registry"},
	],
	"derived": [
		{"fact": "the line's deliverable is a mechanism rather than a refusal",
			"evidence": "derived (design D1): with a real two-sided counter "
				+ "gated on committed content, delivering a refusal would leave a "
				+ "server mutation unimplemented while the committed flag sits on "
				+ "426 of 429 unit definitions looking like dead content"},
		{"fact": "the zero-consumer field count is 21, not the 20 the committed "
			+ "investigation states",
			"evidence": "derived from an ESTABLISHED count: that record says "
				+ "\"twenty of twenty-two\" and then NAMES twenty-one fields, and "
				+ "every one of the twenty-one measures zero. The named list is "
				+ "countable and the prose is not, so the count follows the list"},
		{"fact": "clicks_to_build takes two distinct values over the content, "
			+ "not the three the committed investigation states",
			"evidence": "derived from THREE ESTABLISHED measurements: 0 on all "
				+ "429 units, {0: 172, 1: 298} over the 470 buildings, and the "
				+ "single committed special (id 925) as the 299th row with 1. The "
				+ "recorded 3 is retained in CLICKS_TO_BUILD_CORRECTION"},
		{"fact": "sell(KILL) and resurrect_hero are intended as a "
			+ "death/resurrection pair",
			"evidence": "derived and WEAK: the two functions are complementary "
				+ "and the ledger is shared, but no comment and no dispatch path "
				+ "asserts the pairing, and nothing checks that the revived row "
				+ "is the unit that died"},
		{"fact": "the revived placement's cell/key resolution is a server "
				+ "concern",
			"evidence": "derived (design D2/D5): the legacy branch takes index, "
				+ "item_id, x, and y all from the client, which is the untrusted "
				+ "pattern godot-building-move and godot-building-collect "
				+ "already record; the compatibility service therefore derives "
				+ "the key and the item id server-side and the client sends only "
				+ "a cell"},
	],
}


# ---------------------------------------------------------------------------
# The one projection (design D1)
# ---------------------------------------------------------------------------


## The **read-only** projection of `privateState["deadHeroes"]`, verbatim.
##
## Returns
##   `{ok, reason, error, resolvable, entries, entry_count, total,
##   recorded_present, recorded_type, recorded_keys}`
##
## `entries` keeps each recorded **string** item id with its recorded count
## **exactly as recorded** — no threshold, no cap, no clamp, and no count
## derived from another, and never one derived from a committed `syringes`
## value.
##
## The projection is **fail-closed**.  An absent ledger, a non-object ledger, a
## non-string key, and a non-integer count are each reported `ok: false` /
## `resolvable: false` with `entries` empty, so an unresolvable ledger can
## never be read as an empty one.  The recorded keys are still reported, because
## "which keys are present" is a fact even when a value is unreadable.
static func project_ledger(raw: Variant) -> Dictionary:
	var header := {
		"ok": false,
		"reason": "",
		"error": "",
		"resolvable": false,
		"entries": [],
		"entry_count": 0,
		"total": 0,
		"recorded_present": raw != null,
		"recorded_type": _type_name(raw),
		"recorded_keys": [],
	}
	if raw == null:
		header["reason"] = REASON_LEDGER_ABSENT
		header["error"] = ("privateState['deadHeroes'] is ABSENT (null): a save "
			+ "that never held the key receives an empty ledger from the "
			+ "version.py migration, never from gameplay, so this is reported "
			+ "UNRESOLVABLE rather than presented as an empty ledger that was "
			+ "resolved")
		return header
	if not (raw is Dictionary):
		header["reason"] = REASON_LEDGER_NOT_OBJECT
		header["error"] = ("privateState['deadHeroes'] is %s, not a JSON "
			% _type_name(raw)
			+ "object, so it is not a string-keyed count per item id")
		return header
	var source: Dictionary = raw
	var keys: Array = source.keys()
	keys.sort_custom(func(one: Variant, two: Variant) -> bool:
		return str(one) < str(two))
	for key: Variant in keys:
		if not (key is String):
			header["reason"] = REASON_KEY_NOT_TEXT
			header["error"] = ("the ledger key %s is %s, not the text of an "
				% [str(key), _type_name(key)]
				+ "item id: the ledger is a STRING-keyed count per item id")
			return header
	header["recorded_keys"] = keys.duplicate()
	var entries: Array = []
	var total := 0
	for key: String in keys:
		var value: Variant = source[key]
		if not _whole_number(value):
			header["reason"] = REASON_COUNT_NOT_INTEGER
			header["error"] = ("the ledger count for item id %s is %s (%s), not "
				% [str(key), str(value), _type_name(value)]
				+ "an integer; the legacy helpers add and subtract it directly, "
				+ "so a non-integer is unreadable rather than coercible")
			return header
		var count := int(value)
		entries.append({"item_id": key, "count": count})
		total += count
	header["ok"] = true
	header["resolvable"] = true
	header["entries"] = entries
	header["entry_count"] = entries.size()
	header["total"] = total
	return header


## A projected ledger's entries under their own keys, or `{}` when the ledger is
## unresolvable — so an unresolvable projection can never be mistaken for a
## genuinely empty ledger by a caller that ignores the refusal.
static func ledger_entries(raw: Variant) -> Dictionary:
	var projection := project_ledger(raw)
	var out := {}
	if not bool(projection.get("ok", false)):
		return out
	for entry: Dictionary in projection.get("entries", []):
		out[str(entry["item_id"])] = int(entry["count"])
	return out


## The ledger the decrement leaves behind, with the **delete-at-zero** rule,
## reproducing `engine.resurrect_hero` (`engine.py:172-181`) exactly:
##
##   * an item id the ledger does not hold is a **silent no-op** — the helper
##     returns before touching anything — so `removed` is `false`;
##   * a count of `1` decrements to zero and the key is **DELETED**, never
##     stored as a zero;
##   * a count above `1` decrements and the key stays.
##
## No threshold, no cap, and no clamp beyond the recorded `<= 0` test.
static func expected_ledger(raw: Variant, item_id: Variant) -> Dictionary:
	var out := {
		"entries": {},
		"item_id": "",
		"present_before": false,
		"count_before": 0,
		"count_after": 0,
		"removed": false,
		"resolvable": false,
	}
	if not _whole_number(item_id):
		out["reason"] = REASON_COUNT_NOT_INTEGER
		out["error"] = "item_id must be an integer to address the ledger"
		return out
	var before := ledger_entries(raw)
	var projection := project_ledger(raw)
	if not bool(projection.get("ok", false)):
		out["reason"] = str(projection.get("reason", ""))
		out["error"] = str(projection.get("error", ""))
		return out
	var key := str(int(item_id))
	out["resolvable"] = true
	out["item_id"] = key
	var entries: Dictionary = before.duplicate()
	var present := entries.has(key)
	var count_before := int(entries.get(key, 0))
	var count_after := count_before - 1
	var removed := false
	if present:
		if count_after <= 0:
			entries.erase(key)
			removed = true
		else:
			entries[key] = count_after
	out["entries"] = entries
	out["present_before"] = present
	out["count_before"] = count_before
	out["count_after"] = maxi(0, count_after)
	out["removed"] = removed
	return out


## The ledger the increment leaves behind, reproducing `engine.push_dead_unit`'s
## recorded shape (`engine.py:164-167`): the count is raised by one and the key
## is **created at 1** when it is absent.  Both gates are the CALLER's to apply
## and neither is evaluated here — this module names them in `GATES` and
## reimplements neither, because the gate a helper evaluates is the gate the
## helper evaluates.
static func expected_increment(raw: Variant, item_id: Variant) -> Dictionary:
	var out := {
		"entries": {},
		"item_id": "",
		"present_before": false,
		"count_before": 0,
		"count_after": 0,
		"created": false,
		"resolvable": false,
	}
	if not _whole_number(item_id):
		out["reason"] = REASON_COUNT_NOT_INTEGER
		out["error"] = "item_id must be an integer to address the ledger"
		return out
	var projection := project_ledger(raw)
	if not bool(projection.get("ok", false)):
		out["reason"] = str(projection.get("reason", ""))
		out["error"] = str(projection.get("error", ""))
		return out
	var entries := ledger_entries(raw)
	var key := str(int(item_id))
	out["resolvable"] = true
	out["item_id"] = key
	out["present_before"] = entries.has(key)
	out["count_before"] = int(entries.get(key, 0))
	if entries.has(key):
		out["count_after"] = int(entries[key]) + 1
		entries[key] = int(entries[key]) + 1
	else:
		out["created"] = true
		out["count_after"] = 1
		entries[key] = 1
	out["entries"] = entries
	return out


## Both gates, in the helper's own order, as fresh records a caller may keep and
## mutate.
static func gates() -> Array:
	return (GATES as Array).duplicate(true)


## Whether this projection's recorded gates number exactly `GATE_COUNT` — the
## machine-readable form of "no third gate is invented", so a caller can assert
## it without re-reading the table.
static func gate_count() -> int:
	return (GATES as Array).size()


## The three-door inventory as fresh records a caller may keep and mutate.
static func command_inventory() -> Array:
	return (COMMAND_INVENTORY as Array).duplicate(true)


## The two engine helpers, recorded separately from the branches.
static func engine_helpers() -> Array:
	return (ENGINE_HELPERS as Array).duplicate(true)


## The named branches that reach the ledger, in committed source order.
static func ledger_reaching_commands() -> Array:
	return (LEDGER_REACHING_COMMANDS as Array).duplicate()


## One committed definition's `properties.resurrectable`, or `null` when it
## carries none or is unreadable.  `null` is the **refusal** the legacy helper
## applies to an absent flag (`engine.py:159-160`), never a zero.
##
## Both representations are accepted: the legacy helper `json.loads`es the RAW
## configuration **string** (`engine.py:154-158`) while the committed normalized
## package stores `properties` as an **object** — the R2 coercion boundary M8
## line 1 recorded.  The committed flag is a **string** in the normalized
## package, so it is converted **explicitly**: a non-empty String is truthy in
## GDScript, and `int(value or 0)` would collapse the committed `"0"` to the
## integer one.
static func committed_resurrectable(properties: Variant) -> Variant:
	var decoded: Variant = properties
	if decoded is String:
		var parser := JSON.new()
		if parser.parse(str(decoded)) != OK:
			return null
		decoded = parser.data
	if not (decoded is Dictionary):
		return null
	var flags: Dictionary = decoded
	if not flags.has(RESURRECTABLE_FLAG):
		return null
	var raw: Variant = flags[RESURRECTABLE_FLAG]
	if raw is String:
		var text := str(raw).strip_edges()
		if not text.is_valid_int():
			return null
		return int(text)
	if not _whole_number(raw):
		return null
	return int(raw)


## Whether a committed `resurrectable` value passes the second gate — the
## machine-readable form of `int(properties["resurrectable"]) > 0`
## (`engine.py:162`).  An **absent** flag is a refusal, which is why `null` is
## never coerced to a number here.
static func passes_resurrectable_gate(flag: Variant) -> bool:
	if flag == null:
		return false
	return int(flag) > 0


## Whether a dying row's recorded player slot passes the first gate — the
## machine-readable form of `if item[7] != 1: return False` (`engine.py:151`).
## Slot 7 is the committed `player` slot of `engine.map_add_item`'s row
## (`engine.py:31`).
static func passes_team_gate(player_slot: Variant) -> bool:
	if not _whole_number(player_slot):
		return false
	return int(player_slot) == PLAYER_TEAM


## The committed content record as the evidence report reads it: the
## zero-consumer table with its measured counts, the two consumed fields, both
## committed distributions, both gates, and the corrections.
static func field_record() -> Dictionary:
	return {
		"zero_consumer_fields": (ZERO_CONSUMER_FIELDS as Array).duplicate(true),
		"zero_consumer_count": ZERO_CONSUMER_COUNT,
		"zero_consumer_count_recorded": ZERO_CONSUMER_COUNT_RECORDED,
		"behavioural_field_count": BEHAVIOURAL_FIELD_COUNT,
		"behavioural_field_count_recorded": BEHAVIOURAL_FIELD_COUNT_RECORDED,
		"combat_fields": (COMBAT_FIELDS as Array).duplicate(),
		"combat_field_count": COMBAT_FIELD_COUNT,
		"consumed_behavioural_fields": (CONSUMED_BEHAVIOURAL_FIELDS as Array)
			.duplicate(true),
		"searched_modules": (SEARCHED_MODULES as Array).duplicate(),
		"unit_count": UNIT_COUNT,
		"building_count": BUILDING_COUNT,
		"resurrectable": {
			"units_positive": RESURRECTABLE_UNITS_POSITIVE,
			"units_of": RESURRECTABLE_UNITS_OF,
			"units_absent": RESURRECTABLE_UNITS_ABSENT,
			"units_absent_ids": (UNITS_WITHOUT_RESURRECTABLE as Array).duplicate(),
			"unit_value": RESURRECTABLE_UNIT_VALUE,
			"buildings_positive": RESURRECTABLE_BUILDINGS_POSITIVE,
			"buildings_of": RESURRECTABLE_BUILDINGS_OF,
			"unit_only": true,
			"note": UNIT_ONLY_NOTE,
		},
		"syringes": {
			"unit_values": SYRINGES_UNIT_VALUES,
			"unit_distinct": SYRINGES_UNIT_DISTINCT,
			"building_values": SYRINGES_BUILDING_VALUES,
			"legacy_reads": 0,
			"content_only": true,
		},
		"clicks_to_build": {
			"unit_values": CLICKS_TO_BUILD_UNIT_VALUES,
			"building_values": CLICKS_TO_BUILD_BUILDING_VALUES,
			"distinct_over_content": CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT,
			"distinct_recorded": CLICKS_TO_BUILD_DISTINCT_RECORDED,
			"legacy_reads": 1,
			"boundary": CLICKS_TO_BUILD_BOUNDARY,
			"correction": CLICKS_TO_BUILD_CORRECTION,
		},
		"unit_property_flags": (UNIT_PROPERTY_FLAGS as Array).duplicate(true),
		"unit_property_flag_count": UNIT_PROPERTY_FLAG_COUNT,
		"raw_properties": RAW_PROPERTIES_NOTE,
	}


## The three refusals, the absent helpers, the corpus limitation, the derived
## pairing, and the migration — everything the delta's refusal requirements ask
## the evidence to carry.
static func refusal_record() -> Dictionary:
	return {
		"refusals": (REFUSALS as Array).duplicate(true),
		"absent_helpers": (ABSENT_HELPERS as Array).duplicate(true),
		"syringe_charge": 0,
		"resource_moved": false,
		"syringe_discarded": true,
		"syringe_discard_note": SYRINGE_DISCARD_NOTE,
		"combat_resolved": false,
		"placement_validated": false,
		"clicks_to_build_reimplemented": false,
		"pairing": DERIVED_PAIRING,
		"fixture_not_captured": FIXTURE_NOT_CAPTURED,
		"ledger_migration": LEDGER_MIGRATION_NOTE,
		"no_third_gate": NO_THIRD_GATE,
	}


## The whole recorded ledger contract, as the evidence report reads it.
static func ledger_record(projection: Dictionary) -> Dictionary:
	return {
		"private_state_key": PRIVATE_STATE_KEY,
		"ledger_key": LEDGER_KEY,
		"shape": LEDGER_SHAPE,
		"increment_shape": INCREMENT_SHAPE,
		"decrement_shape": DECREMENT_SHAPE,
		"delete_at_zero": DELETE_AT_ZERO,
		"projection": projection,
		"gates": gates(),
		"gate_count": gate_count(),
		"no_third_gate": NO_THIRD_GATE,
		"refusal_recorded": (REFUSALS as Array).size(),
	}


## Display: the ledger readout a surface shows, with every recorded absence in
## the same breath so an unresolvable ledger never reads as an empty one.
static func readout_text(projection: Dictionary) -> String:
	var parts: Array = []
	if not bool(projection.get("ok", false)):
		parts.append("ledger unresolvable (%s): %s"
			% [str(projection.get("reason", "")),
				str(projection.get("error", ""))])
	else:
		var entries: Array = projection.get("entries", [])
		if entries.is_empty():
			parts.append("no dead unit recorded (the ledger is empty)")
		for entry: Dictionary in entries:
			parts.append("%s: %d" % [str(entry["item_id"]), int(entry["count"])])
	parts.append("reaching zero DELETES the key, never stores a zero")
	parts.append("two gates and no third: player team 1, and committed "
		+ "resurrectable greater than zero")
	parts.append("kill never reaches this ledger; sell reaches it only behind "
		+ "the KILL reason")
	parts.append("no syringe cost and no resource moves; no combat is resolved; "
		+ "the revived placement is not validated")
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


## Whether a value is a whole number the legacy helpers could add to.  The
## pinned engine's JSON parser widens every committed number to a float, so an
## integral float is accepted and nothing else is: a non-integer count is
## **unreadable** rather than coercible, and coercing it would invent a ledger
## the save does not hold.
static func _whole_number(value: Variant) -> bool:
	if value is bool:
		return false
	if value is int:
		return true
	if value is float:
		var number := float(value)
		return number == floor(number) and not is_inf(number) and not is_nan(number)
	return false


## The recorded type of a value as a readable name, so a refusal can say what
## the ledger actually held rather than only that it was wrong.
static func _type_name(value: Variant) -> String:
	if value == null:
		return "null"
	if value is bool:
		return "boolean"
	if value is int:
		return "int"
	if value is float:
		return "float"
	if value is String:
		return "String"
	if value is Array:
		return "Array"
	if value is Dictionary:
		return "Dictionary"
	return type_string(typeof(value))
