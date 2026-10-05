extends Node
## `FakeApi` — GameApi implementation over the committed v0 fixtures (design
## D5, spec "Boot offline with the fake implementation").
##
## Reads only the committed executed-legacy fixture files under
## `tests/fixtures/godot-compatibility-boot/`, for placement under
## `tests/fixtures/godot-building-placement/`, for purchase under
## `tests/fixtures/godot-item-purchase/`, for move under
## `tests/fixtures/godot-building-move/`, for sell under
## `tests/fixtures/godot-building-sell/`, and for store under
## `tests/fixtures/godot-building-store/`, for upgrade under
## `tests/fixtures/godot-building-upgrade/`, for construction under
## `tests/fixtures/godot-building-construction/`, and for collection under
## `tests/fixtures/godot-building-collect/`, and for expansion under
## `tests/fixtures/godot-building-expand/`, and for level under
## `tests/fixtures/godot-building-xp/` at the repository root: no
## process, no server, no socket. It synthesizes the documented v0 envelopes
## from those files and parses them with the same `BootData` functions the
## live implementation uses, so both implementations yield identical typed
## shapes by construction.
##
## `place_building()` additionally applies the documented placement
## semantics in memory (design D8): legacy cost map with the `max(…, 0)`
## clamp, smallest free slot, `engine.map_add_item` entry construction —
## over the committed placement-fixture state, deterministically (the entry
## timestamp is the fixture's recorded epoch; the fake never reads the
## wall clock). `purchase_item()` applies the documented purchase semantics
## in memory (design D9) over the committed purchase-fixture state with the
## same determinism (its `server_time` is the fixture's recorded epoch, not
## the wall clock). `move_building()` applies the documented move semantics
## in memory over the committed move-fixture state with that same
## determinism, `sell_building()` deletes exactly the row its intent
## names from the committed sell-fixture state with it, and
## `store_building()` pops exactly the row its intent names from the
## committed store-fixture state and increments that item's storage entry
## with it, and `upgrade_building()` replaces exactly the row its intent
## names in place — same key, same cell, the target tier derived from the
## fixture's own item reference, the fresh row's timestamp pinned to the
## capture's recorded epoch — and appends that tier to the bought-units list,
## and `build_construction()` applies the matching in-place attribute-bag
## mutation per action over the committed construction-fixture state (a start
## re-stamps the row's start instant and records the derived countdown, a click
## raises the click counter, a completion deletes it), reporting the capture's
## recorded epoch as the re-stamp so the double never reads the wall clock, and
## `collect_income()` applies the matching in-place collection rule over the
## committed collect-fixture state (the addressed row's collection instant
## re-stamped, and the content-derived payout applied to exactly the named
## resource slot and the experience under legacy's `max(current + delta, 0)`
## clamp), reporting the capture's recorded epoch as both its re-stamp and its
## `reference_time` so the derived rung is deterministic too. This is the
## FIRST double whose derived resource vector is deliberately NOT neutral, and
## its payout is derived-provisional exactly like the service's: the amount
## formula, the experience scaling, the sub-first-rung refusal, the cap
## refusal, and the resource-type mapping are all derivations that no legacy
## branch reads. `expand_town()` applies the matching in-place rule over the
## committed expand fixture — the addressed id's own committed row in the
## fixture's loaded `expansion_prices` schedule turned into a DEBIT, applied to
## exactly the named slots under legacy's `max(current + delta, 0)` clamp, and
## the id appended AT THE END of the player's owned ledger with every existing
## entry unchanged, in order, and never deduplicated — so this is the SECOND
## double whose derived vector is not neutral and the first whose vector is a
## debit. Its debit is derived-provisional exactly like the service's: the
## id-space indexing, the requirements refusal, the affordability refusal, and
## the debit's sign and shape are all derivations no legacy branch reads.
## `level_up_town()` applies the matching in-place rule over the committed
## level fixture: the level the fixture's OWN loaded `levels` schedule implies
## for the stored experience — resolved through the one named one-based
## conversion that mirrors the service's — written into the recorded level and
## NOTHING else, because a level change moves no resource (design D5) and no
## legacy branch reads the curve's reward fields (design D7). It is therefore
## the THIRD double with a deliberately NEUTRAL vector, and its index-base
## interpretation is derived-provisional exactly like the service's: the
## one-based reading is derived and the zero-based reading is rejected by the
## committed corpus.
## `push_queue_unit_town()` / `pop_queue_unit_town()` apply the legacy queue
## branches' own recorded effects over the committed executed queue fixture: the
## addressed row's ATTRIBUTE BAG is the only thing either writes — the push sets
## `nu` to `(nu + 1)` (or `1`) and stamps `ts` with the fixture's committed
## instant, the pop decrements and re-stamps, and a decrement to zero deletes
## `nu`, `ts`, and `ui` TOGETHER — and NOTHING else moves: no placement count, no
## storage, no bookkeeping, no private state, and no balance, because a queue
## moves no resource (design D4/D5). It is therefore the FOURTH double with a
## deliberately NEUTRAL vector. It applies **no** producer, duration, level, or
## count check (the three legacy branches validate nothing and the recorded
## absence is not permission), it **caps nothing** (the engine sets no bound),
## and it **creates no unit**: no legacy command completes a queue or
## materialises one, so this double can never be read as evidence that a queue
## finishes (design D1/D2).
## Parity against
## executed legacy is owned exclusively by
## the compat fixture-replay tests; this double exists so the client flow can
## be tested hermetically and is NEVER itself a parity oracle.
##
## `resurrect_hero_town()` starts from the **committed corpus save** rather than
## a `before.json` fixture, which makes it the only double that does: this line
## has NO executed-legacy fixture by construction, because `resurrectable` is a
## UNIT-ONLY committed flag, the corpus places only buildings, and its ledger is
## present and `{}` (design D4).  It applies the legacy decrement with the
## **delete-at-zero** rule, re-places the row at the derived key and cell with
## **no** occupancy, bounds, type, or terrain check, and moves **no** resource —
## `used_syringe` is bound from `args[4]` and DISCARDED, so the revival is free
## (design D3/D5).  It is therefore another double with a deliberately NEUTRAL
## vector — the file numbers only the three most recent ones, so no ordinal is
## claimed here — and its in-memory ledger seed is **documented and throwaway**
## rather than a committed write.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const Paths = preload("res://scripts/package_paths.gd")
const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BehaviorFlow = preload("res://scripts/units/behavior_flow.gd")
const CombatFlow = preload("res://scripts/units/combat_flow.gd")
const MagicFlow = preload("res://scripts/units/magic_flow.gd")
const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")
const StoredItemFlow = preload("res://scripts/units/stored_item_flow.gd")

const SAVE_LIST_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const GAME_CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"
const PLAYER_INFO_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const PLACEMENT_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/before.json"
const PLACEMENT_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/after.json"
## The executed-legacy purchase fixture's before-state (which equals the
## fresh-player corpus the boot fixtures carry): the double's starting save.
const PURCHASE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/before.json"
## The same fixture's after-state, recorded by the real legacy server. It is
## read (never written) purely to assert the double reproduces the executed
## transaction; the in-memory apply never writes a file.
const PURCHASE_AFTER_FIXTURE := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/after.json"
## The executed-legacy move fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `move_building()`.
const MOVE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-move/steps/command_move/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `move` (Turret I at map slot 11, `(58,48)` -> `(58,47)`).
## Read (never written) so a malformed capture cannot leave the double
## running on an inconsistent oracle.
const MOVE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-move/steps/command_move/after.json"
## The executed-legacy sell fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `sell_building()`.
const SELL_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `sell` (Turret I at map slot 20, anchored at `(41,48)`,
## whose key is absent afterwards while every other row and every resource
## is byte-identical). Read (never written) so a malformed capture cannot
## leave the double running on an inconsistent oracle.
const SELL_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/after.json"
## The executed-legacy store fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `store_building()`.
const STORE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `store_item` (the Tree decoration at map slot 2, anchored at
## `(53,39)`, whose key is absent afterwards while its id `905` appears in
## the storage mapping with quantity 1). Read (never written) so a malformed
## capture cannot leave the double running on an inconsistent oracle.
const STORE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/after.json"
## The executed-legacy upgrade fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `upgrade_building()`.
const UPGRADE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed two-command upgrade (the Wall I at map slot 12, anchored at
## (45,49), REPLACED IN PLACE by the Wall II at the same key and cell). Read
## (never written) so a malformed capture cannot leave the double running on
## an inconsistent oracle; its recorded wall-clock timestamp of the new row
## is the deterministic epoch this double stamps.
const UPGRADE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/after.json"
## The executed-legacy construction fixture's before-state (which again equals
## the fresh-player corpus the boot fixtures carry): the double's starting save
## for `build_construction()`.
const CONSTRUCTION_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-construction/steps/command_construction/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed construction (the Turret I at map slot 11, anchored at `(58,48)`,
## whose row gains the recorded countdown and the raised click counter while
## every other row and every resource is byte-identical). Read (never written)
## so a malformed capture cannot leave the double running on an inconsistent
## oracle, and for its recorded wall-clock start instant — the deterministic
## epoch a start re-stamps with.
const CONSTRUCTION_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-construction/steps/command_construction/after.json"
## The executed-legacy collect fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `collect_income()`.
const COLLECT_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-collect/steps/command_collect/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed `collect` (the Tree decoration at map slot 2, anchored at
## `(53,39)`, whose row carries a re-stamped collection instant while the
## derived payout lands in exactly two resource slots and every other row,
## the storage, the private state, and the player info are byte-identical).
## Read (never written) so a malformed capture cannot leave the double running
## on an inconsistent oracle, and for its recorded wall-clock collection
## instant — the deterministic epoch this double re-stamps with and the
## deterministic `reference_time` it derives the rung against.
const COLLECT_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-collect/steps/command_collect/after.json"
## The executed-legacy expand fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save for
## `expand_town()`.
const EXPAND_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-expand/steps/command_expand/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed `expand` (the ledger `[35, 36, 45, 46]` gaining exactly one appended
## `0` at the end while all 40 items, the level, the storage, the private
## state, the player info, and all seven resources are byte-identical). Read
## (never written) so a malformed capture cannot leave the double running on an
## inconsistent oracle.
const EXPAND_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-expand/steps/command_expand/after.json"
## The executed-legacy level fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save for
## `level_up_town()`, recording `level 1` and `xp 4`.
const LEVEL_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-xp/steps/command_level_up/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed `level_up`. **It records the same level as the before-state**, and
## that is not a capture defect: at the committed corpus the level the committed
## curve derives for `xp 4` IS 1, so the executed `level_up(1)` rewrote an
## identical value and every byte of the save is unchanged. The committed
## execution is therefore itself the evidence for the endpoint's
## `level_already_current` refusal. Read (never written) so a malformed capture
## cannot leave the double running on an inconsistent oracle, and validated
## against the before-state so the double only runs on a level-only capture.
const LEVEL_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-xp/steps/command_level_up/after.json"
## The executed-legacy queue fixture's before-state for the **push**: the
## committed fresh-player corpus, whose Command Center at map key 1 carries an
## **empty** attribute bag. Read (never written) as the double's starting save
## for both queue intents.
const QUEUE_PUSH_BEFORE_FIXTURE := \
	"tests/fixtures/godot-unit-queues/steps/command_push_queue_unit/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed `push_queue_unit`: the addressed row's bag gains `nu` = 1 and a
## stamped `ts`, and **nothing else in the save changes**. Read (never written)
## and validated against the before-state, so a capture that is not this
## transaction cannot leave the double running on an inconsistent oracle.
const QUEUE_PUSH_AFTER_FIXTURE := \
	"tests/fixtures/godot-unit-queues/steps/command_push_queue_unit/after.json"
## The executed-legacy queue fixture's before-state for the **pop**: the corpus
## as the push left it, with `nu` = 1 and a stamped `ts` at map key 1. It is
## compared against the push's after-state so the double runs the pair as one
## recorded transaction rather than two unrelated ones.
const QUEUE_POP_BEFORE_FIXTURE := \
	"tests/fixtures/godot-unit-queues/steps/command_pop_queue_unit/before.json"
## The same fixture's after-state — the record of the one executed
## `pop_queue_unit`: the count reached zero and the **three-key teardown** deleted
## `nu`, `ts`, and `ui` together, so the bag is empty again and every stored
## resource, every other row, the storage, the private state, and the player info
## are byte-identical. Read (never written) and validated the same way.
const QUEUE_POP_AFTER_FIXTURE := \
	"tests/fixtures/godot-unit-queues/steps/command_pop_queue_unit/after.json"
## The executed-legacy collection fixture's before-state: the committed
## fresh-player corpus, whose `maps[0]["store"]` is `{}` and whose
## `privateState["collections"]` is `[]`. Read (never written) as the double's
## starting save for the completion intent.
const COLLECTION_BEFORE_FIXTURE := \
	"tests/fixtures/godot-unit-collection/steps/command_complete_collection/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed `complete_collection`: collection 1's committed prize written into the
## empty storage, **exactly one** id appended to the empty ledger, and **no**
## stored resource moved. Read (never written) and validated against the
## before-state, so a capture that is not this transaction cannot leave the
## double running on an inconsistent oracle.
const COLLECTION_AFTER_FIXTURE := \
	"tests/fixtures/godot-unit-collection/steps/command_complete_collection/after.json"

## The captured corpus for the storage round trip (stored-item-placement design
## D1). The capture CHAINED `complete_collection(1)` to seed storage, because it
## is the only content-derived route that can put an id into `maps[0]["store"]`,
## so this before-state already carries the committed prize `{"1085": 1}` and an
## empty ledger against 40 placements -- keys 1..40, so the first derived slot
## is 41.
const STORED_PLACE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-stored-item-placement/steps/command_place_stored_item/before.json"
## The same capture's after-state -- the real legacy server's record of the one
## executed placement: unit `1085` at map key 41 and cell (58, 47), the storage
## entry removed, the id appended to the ledger, **no** stored resource moved,
## and the row's slot-3 instant a wall-clock reading the double reuses as its
## epoch rather than reading the clock itself.
const STORED_PLACE_AFTER_FIXTURE := \
	"tests/fixtures/godot-stored-item-placement/steps/command_place_stored_item/after.json"
## The committed collection id and prize the double validates the executed
## fixture against: id 1 "Draggy Collection" grants unit `1085` with quantity
## `1`. These are the **committed content's** values, and they are duplicated
## here (rather than imported) so this module keeps no dependency on the units
## model — the double validates committed BYTES, and the projection that reads
## them is `collection_prize.gd`'s job.
const COLLECTION_FIXTURE_ID := 1
const COLLECTION_EXPECTED_PRIZE := {"1085": 1}

## The research fixture's FIRST recorded step's before-state: the committed
## fresh-player corpus, whose three research counters are each `[0, 0]`. It is
## the ONLY fixture the research double reads, because the recorded set is eight
## steps of ONE transaction and every step after the first starts from the
## previous step's after-state — so the double derives each step's effect from
## the shared branch record instead of replaying the recording (design D1/D8).
const RESEARCH_BEFORE_FIXTURE := \
	"tests/fixtures/godot-research/steps/command_next_research_step_track_0/before.json"

## The ONLY fixture the quest double reads, for the same reason: the recorded set
## is six steps of ONE transaction and every step after the first starts from the
## previous step's after-state - so the double derives each step's effect from the
## shared branch record instead of replaying the recording (quest design D1/D2).
const QUEST_BEFORE_FIXTURE := \
	"tests/fixtures/godot-quests/steps/command_set_goals/before.json"
## The recorded after-state of that same first step, read for the two wall-clock
## stamps the double must reproduce deterministically: the step branch never
## stamps a clock here, so the double reuses the instant the capture recorded.
const QUEST_AFTER_FIXTURE := \
	"tests/fixtures/godot-quests/steps/command_set_goals/after.json"
## The recorded after-state of the chapter step, whose stamped instant the double
## reuses for the same reason.
const QUEST_CHAPTER_FIXTURE := \
	"tests/fixtures/godot-quests/steps/command_collect_mission/after.json"
## The recorded after-state of the end-quest step, for the same reason.
const QUEST_TIME_FIXTURE := \
	"tests/fixtures/godot-quests/steps/command_end_quest/after.json"

## The tutorial double's four fixtures. It reads the **neutral** round only,
## because the neutral round is the parity transaction: the derived NEUTRAL vector
## moves nothing and the committed gate flips the flag `0 -> 1` (tutorial design
## D1/D2). The minting round is read as the **anchor** for the endpoint's second
## proof half and is deliberately never reproduced, so its presence here is a
## pinned path the suite asserts rather than a state this double replays.
const TUTORIAL_BEFORE_FIXTURE := \
	"tests/fixtures/godot-tutorial/steps/neutral/command_tutorial_15/before.json"
## The recorded after-state of the completing step: the same save with
## `playerInfo.completed_tutorial` at the committed post-value.
const TUTORIAL_AFTER_FIXTURE := \
	"tests/fixtures/godot-tutorial/steps/neutral/command_tutorial_15/after.json"
## The recorded after-state of the **repeat** step, which the gate declines
## because the flag is already at the post-value: byte-identical to the
## completing step's after-state, which is what makes the no-op provable.
const TUTORIAL_REPEAT_AFTER_FIXTURE := \
	"tests/fixtures/godot-tutorial/steps/neutral/command_tutorial_15_again/after.json"
## The minting round's recorded after-state, read (never written) only to prove
## the committed capture really did move all seven balances -- so the double's own
## "nothing moved" answer is checked against an oracle rather than asserted.
const TUTORIAL_MINTING_AFTER_FIXTURE := \
	"tests/fixtures/godot-tutorial/steps/minting/command_tutorial_15_minting/after.json"

## Anchor grid extent the v0 endpoint validates against (anchors 0..99;
## footprints may extend past the edge — design D5). Must match
## `Iso.GRID_EXTENT` (M6) and the endpoint's `GRID_EXTENT`.
const GRID_EXTENT := 100

## config `costs` key -> stored resource slot of the legacy 8-slot vector
## `[unknown, xp, gold, wood, oil, steel, cash, mana]` (design D4; mirrors
## `placement_envelope.COST_SLOTS`, which maps the same keys to indices).
const COST_RESOURCES := {
	"g": "gold", "w": "wood", "o": "oil", "s": "steel", "c": "cash",
}
## The stored resource slots `apply_resources` writes (legacy slot 0
## `unknown` has no stored value; `xp`/`mana` are stored but have no
## config cost key).
const RESOURCE_KEYS := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

## The committed collection ladder (building-collect design D1): the
## `COLLECT_MINUTES` / `COLLECT_MULTIPLIER` pair of the loaded configuration's
## `globals`, recorded here as the ONE ladder this double derives rungs from.
## The committed thresholds are MINUTES while a row's recorded instant is Unix
## SECONDS, so the comparison converts through the single named constant below
## (the compat module's `SECONDS_PER_COMMITTED_MINUTE`, the same 60) — reading
## the raw minutes against a Unix-second elapsed time would pay the TOP rung
## within five *seconds*, which is the bug the compat side found and fixed.
const COLLECT_LADDER_MINUTES := [5, 60, 240, 480]
const COLLECT_LADDER_MULTIPLIERS := [0.25, 1.0, 2.0, 3.0]
## The one place the committed ladder's unit is converted.
const SECONDS_PER_COMMITTED_MINUTE := 60
## The committed `collect_type` vocabulary -> its slot in the eight-slot
## legacy `resources_changed` vector `[unknown, xp, gold, wood, oil, steel,
## cash, mana]` (design D6). The unread `unknown` slot 0 and the never-produced
## `mana` slot 7 are always zero because no item records a mana collect type;
## a type outside this closed set is refused with `unknown_collect_type`
## rather than coerced.
const COLLECT_RESOURCE_SLOTS := {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6}
## The experience slot of the same vector (slot 1).
const COLLECT_EXPERIENCE_SLOT := 1
## The two slots this derivation can never fill (design D6).
const COLLECT_ALWAYS_ZERO_SLOTS := [0, 7]
## The committed `expansion_prices` schedule key in the loaded configuration:
## 98 POSITIONAL rows with no stable id, so the INDEX is the expansion id
## (building-expand design D1, derived). The row is carried verbatim.
const EXPANSION_PRICES_KEY := "expansion_prices"
## The four fields a committed expansion price row records. `neighbors` and
## `inventory_qte` are REQUIREMENTS, not prices: nothing any delivered surface
## can read evaluates either, so a positive value is refused rather than paid
## under an invented requirement rule (design D3).
const EXPANSION_PRICE_FIELDS := ["coins", "cash", "neighbors", "inventory_qte"]
## The two fields of a committed row this derivation turns into a DEBIT, and
## the resource each pays: the schedule's gold-named field into `gold` and its
## `cash` field into `cash`. The gold naming is ESTABLISHED by the client's own
## committed assets `expansion_gold.jpg` / `expansion_cash.jpg` (design D2);
## the sign and shape of the vector are DERIVED.
const EXPANSION_DEBIT_FIELDS := [
	["field", "coins", "resource", "gold", "slot", BootData.EXPAND_GOLD_SLOT],
	["field", "cash", "resource", "cash", "slot", BootData.EXPAND_CASH_SLOT],
]
## The committed schedule's expected size (98 POSITIONAL rows, no stable id —
## the index IS the id, design D1). Used by the double only to bound the
## executed fixture's appended id; the ADDRESSABLE range itself is read from
## the loaded configuration in `expand_town()`, so a content change fails
## closed there instead of being half-adopted here.
const EXPANSION_SCHEDULE_ENTRIES := 98
## The committed level curve key in the loaded configuration
## (`config/main.json` -> `levels`): 100 POSITIONAL entries with no stable
## stored id, so the index is a POSITION and the stored level resolves to it
## through the one named one-based conversion below (building-xp design D1,
## derived). The row is never rewritten and the reward fields are never read.
const LEVELS_KEY := "levels"
## The committed curve's expected size (100 POSITIONAL entries). Used by the
## double only to bound the derived level; the ADDRESSABLE range itself is read
## from the loaded configuration in `level_up_town()`, so a content change fails
## closed there instead of being half-adopted here.
const LEVEL_SCHEDULE_ENTRIES := 100
## The ONE named one-based schedule conversion, mirroring the Compatibility API
## v0 module's equally named `level_envelope.entry_index_for_level` (design D1).
## Stored level *n* is `levels[n - 1]`: the index base is **one-based**, the
## interpretation is **derived-provisional**, and the **rejected** alternative is
## the **zero-based** reading, which the committed corpus contradicts — at
## `xp 4` it implies level 0 while the save records level 1, so a player with 4
## experience would be recorded as level 1 while the curve says level 1 begins
## at 40 experience. Guessing zero-based would shift every level in the game by
## one. The edges refuse gracefully and never raise: a level below 1, a level
## above the curve, and a non-integer all return `LEVEL_NO_INDEX`.
const LEVEL_INDEX_BASE := BootData.LEVEL_INDEX_BASE
const LEVEL_DERIVATION_STATUS := BootData.LEVEL_DERIVATION_STATUS
const LEVEL_REJECTED_ALTERNATIVE := BootData.LEVEL_REJECTED_ALTERNATIVE
## The conversion's "no such entry" sentinel. Never `0`: index 0 is the curve's
## real first entry, and confusing "none" with it would advance a player to the
## wrong level.
const LEVEL_NO_INDEX := -1
## The curve's first threshold, and the committed corpus's own experience and
## recorded level. Together they are the evidence for the one-based reading.
const LEVEL_FLOOR := 0
const LEVEL_CORPUS_XP := 4
const LEVEL_CORPUS_LEVEL := 1

## The three committed production-queue keys and the row slot they live in,
## mirroring `unit_queue.gd` (established, `engine.py:183-213` and
## `engine.py:31`). They are repeated here rather than imported so this module
## keeps no dependency on the units model: the double writes committed BYTES, and
## the projection that reads them is the model's job.
const QUEUE_KEY_COUNT := "nu"
const QUEUE_KEY_START := "ts"
const QUEUE_KEY_UNIT_ID := "ui"
const QUEUE_ATTR_SLOT := 6
## The committed number of slots a legacy map row has — the only row length the
## fixture may carry.
const QUEUE_ROW_SLOTS := 8
## The committed corpus's real placed training producer: **id 26, Command
## Center, at map key 1**, with an EMPTY attribute bag and `training_time` 5. The
## double validates the executed fixture against exactly this row, so a capture
## taken somewhere else fails closed instead of producing a different double.
const QUEUE_TARGET_MAP_KEY := 1
const QUEUE_TARGET_KEY := "1"
const QUEUE_TARGET_ITEM := 26
## The start instant the double stamps — READ FROM the committed executed push,
## never from a clock and never from a hard-coded literal. The legacy branch
## stamps `timestamp_now()`, so the committed fixture is the only authority for
## that value; reading it here means a re-capture of the fixture moves the
## double with it instead of silently disagreeing (design D8).

var _save_list_doc: Dictionary = {}
var _config_payload: Dictionary = {}
var _player_info_payload: Dictionary = {}
var _config_items: Dictionary = {}
var _load_error := ""
var _loaded := false

# Mutable in-memory placement state (design D8): one save, replaced only
# by successful placements inside this process. Never written anywhere.
var _placement_state: Dictionary = {}
var _placement_pid := ""
var _placement_epoch := 0
var _placement_loaded := false
var _placement_error := ""

# Mutable in-memory purchase state (design D9): one save, replaced only by
# successful purchases inside this process. Never written anywhere.
var _purchase_state: Dictionary = {}
var _purchase_pid := ""
var _purchase_loaded := false
var _purchase_error := ""

# Mutable in-memory move state (building-move design D8): one save, replaced
# only by successful moves inside this process. Never written anywhere.
var _move_state: Dictionary = {}
var _move_pid := ""
var _move_loaded := false
var _move_error := ""

# Mutable in-memory sell state (building-sell design D8): one save, with rows
# removed only by successful sales inside this process. Never written
# anywhere.
var _sell_state: Dictionary = {}
var _sell_pid := ""
var _sell_loaded := false
var _sell_error := ""

# Mutable in-memory store state (building-store design D8): one save, with
# rows popped only by successful stores and storage entries incremented
# only by them inside this process. Never written anywhere.
var _store_state: Dictionary = {}
var _store_pid := ""
var _store_loaded := false
var _store_error := ""

# Mutable in-memory upgrade state (building-upgrade design D8): one save, with
# exactly one row replaced in place and at most one bought-units append per
# successful upgrade inside this process. Never written anywhere.
var _upgrade_state: Dictionary = {}
var _upgrade_pid := ""
## The capture's recorded wall-clock epoch of the fresh row the executed
## upgrade wrote — the deterministic stamp this double reuses (it never reads
## the wall clock, exactly as the placement double reuses the placement
## capture's epoch).
var _upgrade_epoch := 0
var _upgrade_loaded := false
var _upgrade_error := ""

# Mutable in-memory construction state (building-construction design D8): one
# save, whose addressed row is mutated in place by the matching legacy
# attribute-bag rule and by nothing else. Never written anywhere.
var _construction_state: Dictionary = {}
var _construction_pid := ""
## The capture's recorded wall-clock start instant of the one construction the
## executed transaction performed — the deterministic stamp a start re-stamps
## the addressed row with (the double never reads the wall clock, exactly as
## the placement and upgrade doubles reuse their captures' epochs).
var _construction_epoch := 0
var _construction_loaded := false
var _construction_error := ""

# Mutable in-memory collection state (building-collect design D8): one save,
# whose addressed row is mutated in place by the matching legacy collection
# rule — and by nothing else — with the derived payout applied under legacy's
# `max(current + delta, 0)` clamp. Never written anywhere.
var _collect_state: Dictionary = {}
var _collect_pid := ""
## The capture's recorded wall-clock collection instant of the one collection
## the executed transaction performed — the deterministic stamp a collection
## re-stamps the addressed row with AND the deterministic `reference_time` the
## derived rung is computed against, so the double never reads the wall clock
## and the reached rung is the same in every run (the committed corpus records
## `item[3] == 0` for every row, so the elapsed time is unbounded and the top
## rung applies, exactly as the executed fixture records).
var _collect_epoch := 0
var _collect_loaded := false
var _collect_error := ""

# Mutable in-memory expansion state (building-expand design D8): one save, whose
# owned-expansions ledger grows by exactly one appended id per successful
# expansion inside this process and whose balances carry the derived debit
# applied under legacy's `max(current + delta, 0)` clamp. Never written
# anywhere. The ledger is kept EXACTLY as the save holds it: never reordered,
# never deduplicated, never normalized — the committed corpus's own
# `[35, 36, 45, 46]` is incoherent under the chosen schedule and is tolerated
# verbatim.
var _expand_state: Dictionary = {}
var _expand_pid := ""
var _expand_loaded := false
var _expand_error := ""
## The double's own backup of the schedule rows a test stubbed in memory, so a
## refusal the committed table cannot produce (an unaffordable PRICE, which
## design D3's requirements rule leaves unreachable from committed content) is
## reachable offline — and so a later check can read the REAL row again. The
## committed fixture and the committed configuration are never written: this
## lives entirely in this process's memory.
var _expand_schedule_backup: Dictionary = {}

# Mutable in-memory level state (building-xp design D8): one save, whose
# recorded level is written to the level the committed curve derives and
# NOTHING else — a level change moves no resource, so no balance is ever
# mutated and the derived vector is the neutral one. Never written anywhere.
var _level_state: Dictionary = {}
var _level_pid := ""
var _level_loaded := false
var _level_error := ""
## The double's own backup of the curve thresholds a test stubbed in memory, so
## a refusal the committed curve cannot produce (a curve whose FLOOR sits above
## the stored experience, so no level is derivable at all) is reachable offline —
## and so a later check can read the REAL committed ladder again. The committed
## fixture and the committed configuration are never written: this lives entirely
## in this process's memory.
var _level_schedule_backup: Dictionary = {}

# Mutable in-memory production-queue state (unit-queues design D8): one save,
# whose addressed row's ATTRIBUTE BAG is the only thing a push or a pop writes
# — a queue moves no resource, so no balance is ever mutated and the derived
# vector is the neutral one. Never written anywhere.
var _queue_state: Dictionary = {}
var _queue_pid := ""
var _queue_loaded := false
var _queue_error := ""
# Mutable in-memory collection state (unit-collection design D8): one save, whose
# storage gains the committed prize and whose collection ledger gains at most one
# id per successful completion inside this process. Never written anywhere. The
# `table` entry carries the committed collections table the captured config
# payload holds, so the grant is derived from the same content the live service
# reads rather than from a second copy of it.
var _collection_state: Dictionary = {}
var _collection_pid := ""
var _collection_loaded := false
var _collection_error := ""
# Mutable in-memory storage state (stored-item-placement design D8): one save,
# whose `maps[0]["store"]` loses exactly one unit of stock per successful
# placement or sale, whose placements gain exactly one derived row per placement,
# and whose purchase ledger gains at most one id per placement — and whose seven
# balances NEVER move, because placing a stored item is free and a sale credits
# nothing. `placed_key`/`placed_item_id` record what the executed capture placed,
# so the double can answer "is this the captured transaction?" without guessing.
var _stored_state: Dictionary = {}
var _stored_pid := ""
var _stored_loaded := false
var _stored_error := ""
var _stored_epoch_value := 0
# Mutable in-memory dead-hero state (unit-behaviors design D8): one save, whose
# placement row at the addressed cell is REPLACED by the derived revived item id
# and whose ledger loses exactly one entry per successful revival under the
# delete-at-zero rule — and whose seven balances never move, because a revival
# moves no resource. Never written anywhere. This is the ONLY double that starts
# from the committed corpus save rather than a `before.json` fixture, because
# this line has NO executed-legacy fixture by construction (design D4).
var _behavior_state: Dictionary = {}
var _behavior_pid := ""
var _behavior_loaded := false
var _behavior_error := ""
# The research double's mutable process state: the three committed two-entry
# counters, the seven balances it reports unchanged, and the recorded stamp. Never
# written anywhere.
var _research_state: Dictionary = {}
var _research_pid := ""
var _research_loaded := false
var _research_error := ""
## The research instant the committed executed capture recorded, read out of that
## capture before any expectation is built. It is the only authority for the value
## the step branch stamps: the double never reads a clock (design D8).
var _research_stamp := 0

# The quest double's mutable process state: the seven committed quest fields, the
# seven balances it reports unchanged, and the two recorded wall-clock stamps.
# Never written anywhere.
var _quest_state: Dictionary = {}
var _quest_pid := ""
var _quest_loaded := false
var _quest_error := ""
var _quest_chapter_stamp := 0
var _quest_time_stamp := 0

# The tutorial double's mutable process state: the ONE committed flag, the seven
# balances it reports unchanged, and the recorded minting-round balances it reads
# as the anchor for its own "nothing moved" answer. Never written anywhere: a
# tutorial completion moves a flag and no balance.
var _tutorial_state: Dictionary = {}
var _tutorial_pid := ""
var _tutorial_loaded := false
var _tutorial_error := ""
## The start instant the committed executed push stamped, read out of that
## capture before any expectation is built. It is the only authority for the
## value the branch stamps: the double never reads a clock (design D8).
var _queue_fixture_stamp := 0


## The session envelope synthesized from the committed fixtures.
func list_sessions() -> BootData.SaveListResult:
	if not _ensure_loaded():
		return BootData.save_list_failure("fixture_unreadable", _load_error)
	return BootData.parse_save_list(_session_envelope())


## Bootstrap envelope synthesized from the committed fixtures; structured
## errors for empty and unknown save ids match the live service's codes.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	if user_id.strip_edges() == "":
		return BootData.bootstrap_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return BootData.bootstrap_failure("fixture_unreadable", _load_error)
	if not _fixture_names(user_id):
		return BootData.bootstrap_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var envelope := _session_envelope()
	envelope["config"] = _config_payload
	envelope["player_info"] = _player_info_payload
	return BootData.parse_bootstrap(envelope, user_id)


## The fake never resolves an endpoint (scope test: only the legacy-v0
## implementation may reference one).
func resolved_endpoint() -> String:
	return "fake fixtures, offline"


## Deterministic in-memory placement double (design D8): the documented
## semantics — legacy cost map with the `max(…, 0)` clamp, smallest free
## slot, `engine.map_add_item` entry construction for player team 1
## (`si` from `properties.friend_assistable`, `nc` from `clicks_to_build`),
## and `engine.bought_unit_add` bookkeeping — applied over the committed
## placement-fixture state, mutating only this process. No process, no
## server, no socket; parity against executed legacy is owned exclusively
## by the compat fixture-replay tests.
##
## Structural failures mirror the v0 endpoint's codes (design D5): unknown
## save / empty id, unknown item id, anchor outside the shared grid.
## Everything else — occupancy, affordability — is gameplay validation the
## client owns, exactly as the endpoint leaves it unenforced; costs clamp
## at zero instead of rejecting, preserving legacy behavior.
func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	if user_id.strip_edges() == "":
		return _place_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _place_failure("fixture_unreadable", _load_error)
	if not _ensure_placement_loaded():
		return _place_failure("fixture_unreadable", _placement_error)
	if user_id != _placement_pid:
		return _place_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return _place_failure("unknown_item_id",
			"no config item with id %d" % item_id)
	if x < 0 or x >= GRID_EXTENT or y < 0 or y >= GRID_EXTENT:
		return _place_failure("invalid_coordinates",
			"x and y must be integers with anchors inside the 0..%d town grid"
			% (GRID_EXTENT - 1))
	var costs: Variant = _derive_costs(item)
	if costs == null:
		# The endpoint answers 500 internal_error for the same unresolvable
		# committed config (design D4); the fake mirrors its code.
		return _place_failure("internal_error",
			"config costs not derivable for item %d" % item_id)
	var attr: Variant = _entry_attr(item)
	if attr == null:
		return _place_failure("internal_error",
			"config properties not derivable for item %d" % item_id)
	# Legacy do_command order for `buy`: resources first (clamped), then
	# boughtUnits bookkeeping, then the entry — all in memory only.
	var resources := _resources_dict()
	for resource: String in costs:
		resources[resource] = maxi(
			int(resources[resource]) - int(costs[resource]), 0)
	var entry := [item_id, x, y, _placement_epoch, orientation, [], attr, 1]
	_placement_state["items"][str(_next_free_slot())] = entry
	for resource: String in RESOURCE_KEYS:
		_placement_state[resource] = int(resources[resource])
	var bought: Array = _placement_state["bought_units"]
	if not bought.has(item_id):
		bought.append(item_id)
	# Same envelope shape the service returns; the shared parser yields
	# the typed result (identical shapes by construction, design D5).
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"result": "success",
		"placement": entry,
		"resources": resources,
	})


## Deterministic in-memory purchase double (design D9): the documented
## semantics of the unchanged legacy `buy_stored_item_cash` branch — the
## item's own config `costs` as a **cash-only** price, the pre-dispatch
## `apply_resources` clamp `max(…, 0)`, `engine.add_store_item` incrementing
## `map["store"][str(item_id)]`, and `engine.bought_unit_add` appending the
## id when absent — applied over the committed purchase fixture's
## before-state, mutating only this process. No process, no server, no
## socket; parity against executed legacy is owned exclusively by the compat
## fixture-replay tests.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result plus the FULL storage mapping and the current resources, so the
## client needs no arithmetic for pre-existing contents (design D4).
##
## Structural failures mirror the endpoint's codes (design D5): unknown
## save / empty id, unknown item id, an item whose config price is not a
## cash price (`costs_not_cash`), and an unresolvable committed config
## (`internal_error`, 500 exactly as the endpoint answers the same input).
## Affordability is gameplay validation the client owns: like the endpoint,
## the double clamps cash at zero instead of rejecting, preserving legacy
## behavior (design D5).
func purchase_item(user_id: String, item_id: int) -> BootData.PurchaseResult:
	if user_id.strip_edges() == "":
		return _purchase_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _purchase_failure("fixture_unreadable", _load_error)
	if not _ensure_purchase_loaded():
		return _purchase_failure("fixture_unreadable", _purchase_error)
	if user_id != _purchase_pid:
		return _purchase_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return _purchase_failure("unknown_item_id",
			"no config item with id %d" % item_id)
	var price: Variant = _cash_price(item as Dictionary)
	if price == null:
		# Unresolvable committed config: the endpoint answers 500
		# internal_error for it (design D2); the fake mirrors that code.
		return _purchase_failure("internal_error",
			"config costs not derivable for item %d" % item_id)
	if int(price) < 0:
		# The price resolves but is not a cash price (design D2's
		# `costs_not_cash`, 400): the client should not have offered it.
		return _purchase_failure("costs_not_cash",
			"item %d is not priced in cash alone" % item_id)
	# Legacy do_command order for `buy_stored_item_cash`: the pre-dispatch
	# resource application (clamped), then `boughtUnits` bookkeeping, then
	# the storage increment — all in memory only.
	_purchase_state["cash"] = maxi(int(_purchase_state["cash"]) - int(price), 0)
	_purchase_state["store"][str(item_id)] = \
		int(_purchase_state["store"].get(str(item_id), 0)) + 1
	var bought: Array = _purchase_state["bought_units"]
	if not bought.has(item_id):
		bought.append(item_id)
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_purchase({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"store": (_purchase_state["store"] as Dictionary).duplicate(),
		"resources": _purchase_resources(),
	})


## Deterministic in-memory move double (building-move design D8): the
## documented semantics of the unchanged legacy `move` branch — resolve the
## row with the item's map index, write ONLY `item[1] = x` and `item[2] = y`
## in place, apply the pre-dispatch resource vector (the derived vector is
## NEUTRAL, so every stored resource is unchanged), and add, remove, and
## re-key nothing — applied over the committed move fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result, the PERSISTED eight-field row re-read after the write, and the
## current resources — byte-for-byte the shape `place_building()` returns,
## so the client reuses one typed result class and one parse function
## (design D4).
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), and coordinates
## outside the shared grid (`invalid_coordinates`). Everything else —
## occupancy, the no-op cell, ownership — is gameplay validation the client
## owns, exactly as the endpoint leaves it unenforced; this double never
## invents a gate the legacy server does not have, and never accepts a
## client-sent price.
func move_building(user_id: String, item_index: int, x: int,
		y: int) -> BootData.PlacementResult:
	if user_id.strip_edges() == "":
		return _move_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _move_failure("fixture_unreadable", _load_error)
	if not _ensure_move_loaded():
		return _move_failure("fixture_unreadable", _move_error)
	if user_id != _move_pid:
		return _move_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if x < 0 or x >= GRID_EXTENT or y < 0 or y >= GRID_EXTENT:
		return _move_failure("invalid_coordinates",
			"x and y must be integers with anchors inside the 0..%d town grid"
			% (GRID_EXTENT - 1))
	var row: Variant = (_move_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _move_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# Legacy do_command order for `move`: the pre-dispatch
	# `apply_resources` (clamped) first, then the two in-place coordinate
	# writes. The derived vector is all zeros, so the clamp never rewrites
	# a value and the resources below are the state's own.
	var resources := _move_resources()
	var entry: Array = (row as Array).duplicate()
	entry[1] = x
	entry[2] = y
	(_move_state["items"] as Dictionary)[str(item_index)] = entry
	# Same envelope shape the service returns; the shared parser yields
	# the typed result (identical shapes by construction, design D4).
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"placement": entry,
		"resources": resources,
	})


## Deterministic in-memory sell double (building-sell design D8): the
## documented semantics of the unchanged legacy `sell` branch — resolve the
## row with the item's map index, apply the pre-dispatch resource vector
## (the derived vector is NEUTRAL, so every stored resource is unchanged),
## and delete that row and NOTHING else (no re-keying, no storage write, no
## bookkeeping) — applied over the committed sell fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result, the eight-field row AS IT WAS READ BEFORE EXECUTION (design D5 —
## the save no longer holds it, and reconstructing it afterwards would be
## fabrication), and the current resources.
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op early return is never reported as a success), and
## an unreadable fixture (`fixture_unreadable`). Ownership, price, and
## refund are gameplay/economic concerns this contract refuses: the derived
## price vector is neutral, so the double accepts no refund from any caller
## and claims none.
func sell_building(user_id: String, item_index: int) -> BootData.SellResult:
	if user_id.strip_edges() == "":
		return _sell_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _sell_failure("fixture_unreadable", _load_error)
	if not _ensure_sell_loaded():
		return _sell_failure("fixture_unreadable", _sell_error)
	if user_id != _sell_pid:
		return _sell_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_sell_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _sell_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# The pre-execution row: read first, then the one write the branch
	# performs (the delete). Nothing else is touched — no re-keying, no
	# storage, no bookkeeping — exactly as the executed fixture records.
	var removed: Array = (row as Array).duplicate()
	(_sell_state["items"] as Dictionary).erase(str(item_index))
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_sell({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"resources": _sell_resources(),
	})


## Deterministic in-memory store double (building-store design D8): the
## documented semantics of the unchanged legacy `store_item` branch — resolve
## the row with the item's map index, read that row AS IT IS BEFORE the
## writes, apply the pre-dispatch resource vector (the derived vector is
## NEUTRAL, so every stored resource is unchanged), pop exactly that row,
## and increment `map["store"][str(item_id)]` by legacy's default quantity
## of exactly 1 — applied over the committed store fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
## Exactly two writes land, together: the pop and the storage increment, and
## nothing else is touched (no re-keying, no storage rule of its own, and —
## faithfully — no bought-units bookkeeping, because the legacy branch
## deliberately calls no `bought_unit_add`).
##
## The response mirrors the v0 endpoint's two-sided superset (design D4): the
## legacy result, the eight-field row AS IT WAS READ BEFORE EXECUTION (the
## save no longer holds it, and reconstructing it afterwards would be
## fabrication), the FULL post-execution storage mapping (in the very shape
## and through the very parser the purchase response uses), and the current
## resources — so the client performs no arithmetic for pre-existing
## contents.
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent early return is never reported as a success), and an
## unreadable fixture (`fixture_unreadable`). Ownership, price, quantity,
## and capacity are gameplay/economic concerns this contract refuses: the
## derived vector is neutral, so the double accepts no cost, no quantity,
## and no capacity from any caller and claims none.
func store_building(user_id: String,
		item_index: int) -> BootData.StoreResult:
	if user_id.strip_edges() == "":
		return _store_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _store_failure("fixture_unreadable", _load_error)
	if not _ensure_store_loaded():
		return _store_failure("fixture_unreadable", _store_error)
	if user_id != _store_pid:
		return _store_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_store_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _store_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# Legacy do_command order for `store_item`: the pre-dispatch
	# `apply_resources` (clamped) runs first — and the derived vector is all
	# zeros, so the clamp never rewrites a value and the resources below are
	# the state's own — then the row read, the pop, and the storage
	# increment. This double deliberately writes NO bought-units bookkeeping,
	# exactly as the executed fixture records.
	var removed: Array = (row as Array).duplicate()
	(_store_state["items"] as Dictionary).erase(str(item_index))
	(_store_state["store"] as Dictionary)[str(int(removed[0]))] = \
		int((_store_state["store"] as Dictionary).get(
			str(int(removed[0])), 0)) + 1
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_store({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"store": (_store_state["store"] as Dictionary).duplicate(),
		"resources": _store_resources(),
	})


## Deterministic in-memory upgrade double (building-upgrade design D8): the
## documented semantics of the unchanged legacy pair the service derives —
## read the row the intent names AS IT IS BEFORE the writes, apply the
## pre-dispatch resource vector (the derived vector is NEUTRAL, so every
## stored resource is unchanged), and then replace that row IN PLACE at the
## same key with a FRESH row for the target tier at the same cell, the same
## orientation, and the same player field: a new timestamp, `store: []`, and
## the `{"nc": 0}` attribute seed the config's `clicks_to_build > 0` rule
## produces (design D5) — plus the purchase half's bought-units append,
## which records the target tier only when it is not already listed. Applied
## over the committed upgrade fixture's before-state, mutating only this
## process. No process, no server, no socket; parity against executed legacy
## is owned exclusively by the compat fixture-replay tests, so this double is
## a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's two-sided superset (design D5): the
## legacy result, the row AS IT WAS READ BEFORE EXECUTION, the row re-read
## from the save after execution, and the current resources — so the client
## needs no arithmetic of its own and never restamps a row locally.
##
## Structural failures mirror the endpoint's codes (design D3/D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), a placement whose
## item has no resolvable next tier (`no_upgrade_path` — the endpoint's 400,
## answered before the dispatcher runs so an un-upgradeable building is never
## reduced to a bare sale), and an unreadable fixture (`fixture_unreadable`).
## Level gating, a daily-upgrade limit, and a space check are legacy-client
## rules the repository cannot reproduce and this change deliberately does not
## implement (design D6) — the same derived vector claims no upgrade cost, and
## the same key and cell are reused, so there is no space question.
func upgrade_building(user_id: String,
		item_index: int) -> BootData.UpgradeResult:
	if user_id.strip_edges() == "":
		return _upgrade_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _upgrade_failure("fixture_unreadable", _load_error)
	if not _ensure_upgrade_loaded():
		return _upgrade_failure("fixture_unreadable", _upgrade_error)
	if user_id != _upgrade_pid:
		return _upgrade_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_upgrade_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _upgrade_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	var source: Array = row as Array
	# The target tier comes from the committed configuration's `upgrades_to`
	# reference, never from the caller (design D2) — the same rule the
	# endpoint applies, down to the `-1`/`0` and unresolvable sentinels.
	var target: Variant = _upgrade_target(int(source[0]))
	if target == null:
		# The endpoint answers 400 no_upgrade_path for the same input, before
		# the dispatcher runs, so a building that cannot be upgraded is never
		# reduced to a bare sale (design D3).
		return _upgrade_failure("no_upgrade_path",
			"item %d has no resolvable next tier in the configuration"
			% int(source[0]))
	var target_item: Dictionary = target
	# The fresh row's attribute rules come from the TARGET's own config; an
	# unresolvable committed config fails closed BEFORE any mutation (the
	# endpoint answers 500 internal_error for the same input, and the fake
	# mirrors that code — the placement double's precedent).
	var attr: Variant = _entry_attr(target_item)
	if attr == null:
		return _upgrade_failure("internal_error",
			"config properties not derivable for item %d"
			% int(target_item["id"]))
	# The pre-execution row: read first, then the one write the pair performs
	# (the in-place replacement). Nothing else is touched — no re-keying, no
	# storage, no resource delta — exactly as the executed fixture records.
	var removed: Array = source.duplicate()
	# The purchase half writes a FRESH row at the SAME key and cell: the
	# row's own cell, orientation, and player are reused, the timestamp is
	# the deterministic fixture epoch, and `store` plus the configuration's
	# attribute rules are rebuilt from the target's own config (design D5).
	var entry := [int(target_item["id"]), int(source[1]), int(source[2]),
		_upgrade_epoch, int(source[4]), [], attr, int(source[7])]
	(_upgrade_state["items"] as Dictionary)[str(item_index)] = entry
	# `engine.bought_unit_add` appends the item only when it is not already
	# listed, so re-upgrading into an already-bought tier leaves the list
	# alone (the fixture records `[]` -> `[24]`).
	var bought: Array = _upgrade_state["bought_units"]
	if not bought.has(int(target_item["id"])):
		bought.append(int(target_item["id"]))
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_upgrade({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"upgraded": entry,
		"resources": _upgrade_resources(),
	})


## Deterministic in-memory construction double (building-construction design
## D8): the documented semantics of the three unchanged legacy branches the
## service derives — read the row the intent names AS IT IS BEFORE the writes,
## apply the pre-dispatch resource vector (the derived vector is NEUTRAL, so
## every stored resource is unchanged), and then mutate ONLY that row's
## timestamp and attribute bag, in place, at the same key and cell:
## a `start` re-stamps the start instant and records the derived countdown,
## a `click` raises the click counter (seeding it to `1` when absent), and a
## `finish` deletes the counter and writes nothing else (design D5/D6). The
## start duration comes from the addressed item's committed `build_time` in
## the loaded configuration — never from the caller, exactly the rule the
## endpoint applies — and the re-stamp reuses the capture's recorded epoch, so
## the double never reads the wall clock. No clearing branch is implemented or
## reachable: legacy's `activate` with a non-positive duration would DESTROY
## the whole attribute bag, so the endpoint refuses such a row and this double
## mirrors that refusal (design D6). Applied over the committed construction
## fixture's before-state, mutating only this process. No process, no server,
## no socket; parity against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's two-sided superset (design D3/D5):
## the legacy result, the row AS IT WAS READ BEFORE EXECUTION, the row
## RE-READ from the save after execution, the resolved action echoed from the
## closed vocabulary, and the current resources.
##
## Structural failures mirror the endpoint's codes (design D3): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), an action outside the
## documented set (`invalid_action`), a `start` on a row whose item has no
## resolvable positive committed build time (`no_build_time` — the endpoint's
## 400, answered before the dispatcher runs so an unbuildable row is never
## handed a coerced or clearing duration), and an unreadable fixture
## (`fixture_unreadable`). Ownership, whether a build may start on a row that
## already carries construction state, the click threshold, and price are
## gameplay/economic concerns this contract refuses: no branch compares the
## counter with `clicks_to_build`, the derived vector is neutral, and this
## double accepts no duration, no price, and no resource delta from any caller.
func build_construction(user_id: String, item_index: int,
		action: String) -> BootData.ConstructionResult:
	if user_id.strip_edges() == "":
		return _construction_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _construction_failure("fixture_unreadable", _load_error)
	if not _ensure_construction_loaded():
		return _construction_failure("fixture_unreadable", _construction_error)
	if user_id != _construction_pid:
		return _construction_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# The action is validated BEFORE the index is resolved, the endpoint's own
	# order: the request shape is checked first, then the corpus.
	if not BootData.CONSTRUCTION_ACTIONS.has(action):
		return _construction_failure("invalid_action",
			"action must be one of %s" % ", ".join(
				BootData.CONSTRUCTION_ACTIONS))
	var row: Variant = (_construction_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before executing
		# (design D3), so a stale or unknown index is a structured failure with
		# no mutation, never a silent success.
		return _construction_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	var source: Array = row as Array
	# Copies: the three branches mutate this row's attribute bag IN PLACE
	# (legacy's own code writes `item[6]["cp"]`, `item[6]["nc"]`, and deletes
	# `item[6]["nc"]` on the very dict the save holds), so a shallow row copy
	# would still alias the live bag and the "before" row would report the
	# after-state. The bag is therefore copied separately, exactly as the
	# endpoint does before it hands the row to the dispatcher.
	var previous: Array = source.duplicate()
	previous[6] = (source[6] as Dictionary).duplicate()
	var entry: Array = source.duplicate()
	entry[6] = (source[6] as Dictionary).duplicate()
	var attr: Dictionary = entry[6] as Dictionary
	# Legacy do_command order for each branch: the pre-dispatch
	# `apply_resources` runs first — and the derived vector is all zeros, so
	# the clamp never rewrites a value and the resources below are the state's
	# own — then the row read, then the one in-place write that branch performs.
	var duration: int = 0
	if action == BootData.CONSTRUCTION_ACTIONS[0]:
		# The start duration comes from committed content alone (design D2/D3).
		# An unresolvable, non-integer, or non-positive committed build time
		# fails closed with the endpoint's own 400 rather than being coerced:
		# a zero duration would make legacy CLEAR the whole attribute bag.
		var derived: Variant = _construction_build_time(int(entry[0]))
		if derived == null:
			return _construction_failure("no_build_time",
				"item %d has no resolvable positive committed build time"
				% int(entry[0]))
		duration = int(derived)
		entry[3] = _construction_epoch
		attr["cp"] = duration
	elif action == BootData.CONSTRUCTION_ACTIONS[1]:
		attr["nc"] = int(attr.get("nc", 0)) + 1
	else:
		attr.erase("nc")
	# The pre-execution row was read first (above), then the one write the
	# branch performs. Nothing else is touched — no re-keying, no storage, no
	# bought-units bookkeeping, no resource delta — exactly as the executed
	# fixture records.
	(_construction_state["items"] as Dictionary)[str(item_index)] = entry
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_construction({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"previous": previous,
		"row": entry,
		"action": action,
		"resources": _construction_resources(),
	})


## Deterministic in-memory collection double (building-collect design D8): the
## documented semantics of the unchanged legacy `collect` branch — resolve the
## row with the item's map index, read that row AS IT IS BEFORE the writes,
## apply the pre-dispatch resource vector (which is the DERIVED payout, not a
## neutral one — the first delivered line whose vector is not deliberately
## zero) per resource as `max(current + delta, 0)`, and re-stamp ONLY that
## row's collection instant in place, at the same key and cell — applied over
## the committed collect fixture's before-state, mutating only this process.
## No process, no server, no socket; parity against executed legacy is owned
## exclusively by the compat fixture-replay tests, so this double is a test
## fixture, never an oracle.
##
## The payout is derived from the FIXTURE'S OWN committed configuration and
## the addressed row's pre-execution instant, never from the caller (design
## D7): the amount from the item's committed `collect`, the resource from its
## committed `collect_type`, the experience from its committed `collect_xp`,
## each scaled by the committed multiplier of the rung the elapsed time has
## reached, with the unread `unknown` slot 0 and the never-produced `mana`
## slot 7 left zero. **Every one of those rules is derived-provisional**
## (design D1/D2/D6): no legacy branch reads the ladder, so the claim is
## "a payout that grows in four committed rungs", never any specific amount
## the legacy client pays.
##
## The response mirrors the v0 endpoint's superset (design D8): the legacy
## result, the row AS IT WAS READ BEFORE EXECUTION, the row RE-READ from the
## save after execution, the derived payout with the rung it came from, the
## reference instant that rung was computed against, and the current
## resources — so the client needs no arithmetic of its own and never restamps
## a row locally.
##
## Structural failures mirror the endpoint's codes (design D7): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), an item whose
## committed amount is zero (`no_income`), a non-zero committed cap
## (`capped_collection` — refused, never interpreted, because nothing in the
## repository says what a non-zero cap limits), a resource type outside the
## committed set (`unknown_collect_type`), a row carrying construction state
## (`construction_in_progress` — the two-layer refusal the executed probe
## forced), a row that has reached no committed rung yet (`too_early` — no
## sub-first-rung amount is ever derived), and an unreadable fixture
## (`fixture_unreadable`). Ownership, price, and cap semantics are gameplay /
## economic concerns this contract refuses: this double accepts no amount, no
## resource, no tier, no time, and no resource delta from any caller.
func collect_income(user_id: String,
		item_index: int) -> BootData.CollectResult:
	if user_id.strip_edges() == "":
		return _collect_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _collect_failure("fixture_unreadable", _load_error)
	if not _ensure_collect_loaded():
		return _collect_failure("fixture_unreadable", _collect_error)
	if user_id != _collect_pid:
		return _collect_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_collect_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before executing
		# (design D7), so a stale or unknown index is a structured failure with
		# no mutation, never a silent success.
		return _collect_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	var source: Array = row as Array
	# Design D5 comes FIRST, exactly as the endpoint orders it: the shared
	# `item[3]` field is a construction start instant OR a collection instant,
	# and the executed probe shows a collection on a row under construction
	# overwrites the build's start instant while the countdown survives — while
	# legacy reports success. The refusal is therefore made BEFORE any payout is
	# derived, in this layer and in the service, so a client that ignores the
	# client-side rule still cannot corrupt the timers the delivered
	# construction line depends on.
	var attr: Variant = source[6]
	if attr is Dictionary:
		for key in ["cp", "nc"]:
			if (attr as Dictionary).has(key):
				return _collect_failure("construction_in_progress",
					"the placement at index %d is under construction (attr['%s'] "
					% [item_index, key]
					+ "= %s); collecting it would overwrite the build's start "
					% str((attr as Dictionary)[key])
					+ "instant")
	elif attr != {} and attr != null:
		# An unusable attribute bag is an unresolvable committed state, not a
		# gameplay verdict: the endpoint answers 500 internal_error for it, and
		# the double mirrors that code.
		return _collect_failure("internal_error",
			"the addressed placement carries no readable attribute bag")
	# The committed income fields of the addressed item, read from the
	# FIXTURE'S OWN loaded configuration — never from the caller. An
	# unresolvable, non-integer, or negative amount fails closed with the
	# endpoint's own code rather than being coerced.
	var amount: Variant = _collect_amount(int(source[0]))
	if amount == null or int(amount) <= 0:
		# The endpoint answers 409 no_income for a zero or unresolvable amount
		# BEFORE the dispatcher runs, so a building that produces nothing is
		# never handed a zero payout dressed as a success.
		return _collect_failure("no_income",
			"item %d records no committed collection income" % int(source[0]))
	# Design D4: a non-zero committed cap is REFUSED, never interpreted.
	var cap: Variant = _collect_cap(int(source[0]))
	if cap == null or int(cap) != 0:
		return _collect_failure("capped_collection",
			"item %d records a committed collection cap of %s, and this "
			% [int(source[0]), str(cap)]
			+ "contract implements only the uncapped 0")
	var resource_type: Variant = _collect_resource_type(int(source[0]))
	if not (resource_type is String) \
			or not COLLECT_RESOURCE_SLOTS.has(str(resource_type)):
		# Design D6: a type outside the committed five is refused, never
		# coerced, so a content change can never pay the wrong resource.
		return _collect_failure("unknown_collect_type",
			"item %d records a collection type outside the committed set"
			% int(source[0]))
	var experience: Variant = _collect_experience(int(source[0]))
	if experience == null or int(experience) < 0:
		return _collect_failure("no_income",
			"item %d has no resolvable committed collection experience"
			% int(source[0]))
	# The rung is derived against the DETERMINISTIC reference instant (the
	# capture's own recorded epoch), never the wall clock, so the same intent
	# always reaches the same rung.
	var reference_time: int = _collect_epoch
	var elapsed: int = reference_time - int(source[3])
	if elapsed < 0:
		return _collect_failure("too_early",
			"the row's recorded collection instant lies after the reference "
			+ "instant, so no elapsed time can be derived from it")
	var tier: int = _collect_tier_for(elapsed)
	if tier < 0:
		# Design D3: below the first committed rung nothing is derived and
		# nothing is offered — the `0.25` multiplier never produces a
		# speculative payout.
		return _collect_failure("too_early",
			"the row has reached no committed collection rung yet (elapsed "
			+ "%d s, first rung at %d s)" % [elapsed,
				_collect_threshold_seconds(0)])
	var payout: Variant = _collect_payout_for(int(amount), int(experience),
		str(resource_type), tier)
	if payout == null:
		return _collect_failure("internal_error",
			"the committed collection ladder does not resolve for item %d"
			% int(source[0]))
	# The pre-execution row is read first (above), then the two writes the
	# branch performs: the pre-dispatch resource application and the single
	# in-place write of the collection instant. Nothing else is touched — no
	# re-keying, no storage, no bought-units bookkeeping, no attribute bag.
	var previous: Array = source.duplicate()
	previous[6] = (source[6] as Dictionary).duplicate()
	var entry: Array = source.duplicate()
	entry[3] = _collect_epoch
	for resource: String in RESOURCE_KEYS:
		var slot: int = _collect_slot_of(resource)
		var delta: int = int(payout[slot])
		if delta != 0:
			_collect_state[resource] = maxi(
				int(_collect_state[resource]) + delta, 0)
	(_collect_state["items"] as Dictionary)[str(item_index)] = entry
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return BootData.parse_collect({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"previous": previous,
		"row": entry,
		"payout": payout,
		"tier": tier,
		"reference_time": reference_time,
		"resources": _collect_resources(),
	})


## Deterministic in-memory expansion double (building-expand design D8): the
## documented semantics of the unchanged legacy `expand` branch — read the
## player's owned-expansions ledger, apply the pre-dispatch resource vector
## (which is the DERIVED DEBIT, not a neutral one) per resource as
## `max(current + delta, 0)`, and append the addressed id AT THE END of that
## ledger, changing nothing else — applied over the committed expand fixture's
## before-state, mutating only this process. No process, no server, no socket;
## parity against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The debit is derived from the FIXTURE'S OWN loaded configuration and the
## player's committed ledger, never from the caller (design D1/D2): the price
## from the addressed id's own row in the 98-entry positional
## `expansion_prices` schedule, the schedule's gold-named field into `gold` and
## its `cash` field into `cash`, both negated, and the six slots no expansion
## price names left zero. A row costing nothing derives the ALL-ZERO vector,
## which is legal — the committed free rows `0..3` exist and are the only
## purchasable entries under the requirements rule.
##
## The response mirrors the v0 endpoint's two-sided superset (design D5): the
## legacy result, the owned ledger AS READ BEFORE EXECUTION, the SAME ledger
## re-read from the state after the append, the derived debit, the committed
## schedule row used, and the current resources — so the client needs no
## arithmetic of its own and never appends an id locally.
##
## Structural failures mirror the endpoint's codes (design D5/D7): unknown or
## empty save id, a negative expansion id (`invalid_expansion_id` — a negative
## index would otherwise resolve the schedule's LAST row, pricing a negative
## id from a positive one), an id the committed schedule does not price
## (`unknown_expansion_id`), an id the player's ledger already contains
## (`already_expanded` — the legacy server neither orders nor deduplicates the
## ledger, so a repeat would corrupt it), a row recording a positive
## `neighbors` or `inventory_qte` requirement (`expansion_requirements_unmet`),
## a balance that does not cover the derived debit
## (`insufficient_resources` — refused rather than reproduced as the clamp, so
## a partially applied debit can never be mistaken for a correct one), an
## unreadable fixture (`fixture_unreadable`), and a ledger the service cannot
## reason about (`internal_error`).
##
## Ownership of the id space, the requirement semantics, and any server-
## authoritative validation are out of scope: this double accepts NO amount,
## NO price, NO requirement flag, and NO resource delta from any caller, and it
## makes no claim that any area of the town becomes buildable.
func expand_town(user_id: String,
		expansion_id: int) -> BootData.ExpandResult:
	if user_id.strip_edges() == "":
		return _expand_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _expand_failure("fixture_unreadable", _load_error)
	if not _ensure_expand_loaded():
		return _expand_failure("fixture_unreadable", _expand_error)
	if user_id != _expand_pid:
		return _expand_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# Design D1: the committed schedule's id space is its POSITIONAL index,
	# `0..size-1`. A negative id is a structurally unresolvable value, not an
	# out-of-range one: Python would resolve `-1` to the schedule's last row,
	# pricing a negative id from a positive one.
	if expansion_id < 0:
		return _expand_failure("invalid_expansion_id",
			"expansion_id must not be negative, got %d" % expansion_id)
	var owned: Array = _expand_state["expansions"] as Array
	for entry: Variant in owned:
		if not (entry is int) and not (entry is float):
			# The service cannot reason about a ledger entry that is not an
			# integer, and repairing it would be fabrication: fail closed.
			return _expand_failure("internal_error",
				"the owned-expansions ledger carries an entry this service "
				+ "cannot reason about")
	var schedule: Variant = _config_payload.get(EXPANSION_PRICES_KEY)
	if not (schedule is Array) or (schedule as Array).is_empty():
		# A schedule the loaded configuration cannot produce is a server-side
		# content failure, never a client value (design D5).
		return _expand_failure("internal_error",
			"the committed expansion schedule does not resolve")
	var size := (schedule as Array).size()
	if expansion_id >= size:
		# The executed probe showed legacy accepts 999, -1, and a duplicate
		# alike, so the range guard is REQUIRED, not defensive.
		return _expand_failure("unknown_expansion_id",
			"the committed expansion schedule has no price row for id %d "
			% expansion_id + "(it holds %d rows, indexes 0..%d)"
			% [size, size - 1])
	if owned.has(expansion_id):
		return _expand_failure("already_expanded",
			"expansion %d is already in this player's owned-expansions list"
			% expansion_id)
	var row: Variant = (schedule as Array)[expansion_id]
	if not (row is Dictionary):
		return _expand_failure("internal_error",
			"the committed expansion schedule produced no row for id %d"
			% expansion_id)
	var price: Variant = _expand_price_row(row as Dictionary)
	if price == null:
		return _expand_failure("internal_error",
			"the committed expansion schedule's row for id %d is not four "
			% expansion_id + "non-negative integers")
	# Design D3: an unevaluable requirement is REFUSED, never invented.
	var unmet: Array = _expand_unmet_requirements(price)
	if not unmet.is_empty():
		return _expand_failure("expansion_requirements_unmet",
			"expansion %d records %s requirements, and nothing this service "
			% [expansion_id, " and ".join(unmet)]
			+ "can read evaluates them")
	var debit: Array = _expand_debit_for(price)
	# Design D6: refuse an unaffordable balance rather than reproduce the
	# clamp, so the resulting post-state is unambiguous.
	for entry: Array in EXPANSION_DEBIT_FIELDS:
		var delta: int = debit[int(entry[5])]
		if delta == 0:
			continue
		var resource := str(entry[3])
		if int(_expand_state[resource]) + delta < 0:
			return _expand_failure("insufficient_resources",
				"expansion %d costs %d %s and this player holds %d; the "
				% [expansion_id, -delta, resource,
					int(_expand_state[resource])]
				+ "derived debit would leave a negative balance")
	# The pre-execution ledger is read FIRST (above), then the two writes the
	# branch performs: the pre-dispatch resource application and the single
	# append. Nothing else is touched — no item, no level, no storage, no
	# bought-units bookkeeping, no private state — exactly as the executed
	# fixture records.
	for entry: Array in EXPANSION_DEBIT_FIELDS:
		var slot: int = int(entry[5])
		var delta: int = debit[slot]
		if delta != 0:
			_expand_state[str(entry[3])] = maxi(
				int(_expand_state[str(entry[3])]) + delta, 0)
	owned.append(expansion_id)
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_expand({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"expansions_before": (owned.slice(0, owned.size() - 1) as Array)
			.duplicate(),
		"expansions_after": owned.duplicate(),
		"debit": debit,
		"price": price,
		"resources": _expand_resources(),
	})


## Structured failure in the service's error envelope shape, parsed by the same
## shared parser the live implementation uses.
func _expand_failure(code: String, message: String) -> BootData.ExpandResult:
	return BootData.parse_expand({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed expand fixture's before-state into mutable process state
## (once). Structural failures are named with the offending field; the boot,
## placement, purchase, move, sell, store, upgrade, construction, and collect
## fixtures' error state is untouched (independent sinks).
func _ensure_expand_loaded() -> bool:
	if _expand_loaded:
		return _expand_error == ""
	_expand_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(EXPAND_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_expand_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(EXPAND_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_expand_error = str(after_sink["error"])
		return false
	return _init_expand_state(before)


## Validates the expand fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails closed
## instead of crashing the double. **Only the ledger and the seven stored
## balances are kept**: the executed expansion writes nothing else (not
## `items`, not `level`, not `store`, not `privateState`, not the rest of
## `playerInfo`), so keeping more would be inventing state this line never
## touches. The after-state is validated to hold exactly the documented
## transaction — the ledger grown by one entry equal to the sent id, appended
## at the end, with every existing entry unchanged and in order, and every
## stored resource unchanged — so a capture that is not the transaction this
## double reproduces fails closed here.
func _init_expand_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_expand_error = "expand fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_expand_error = "expand fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var owned: Variant = map.get("expansions")
	if not (owned is Array):
		_expand_error = "expand fixture before state carries no expansions list"
		return false
	var typed_owned: Array = []
	for entry: Variant in (owned as Array):
		var id: Variant = BootData._parse_int(entry)
		if id == null:
			_expand_error = "the fixture's owned-expansions ledger carries a " \
				+ "non-integer entry"
			return false
		typed_owned.append(int(id))
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)) or int(value) < 0:
			_expand_error = "expand fixture before state lacks map %s" % key
			return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_expand_error = "expand fixture before state lacks playerInfo/privateState"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or int(mana) < 0:
		_expand_error = "expand fixture before state lacks save fields"
		return false
	# The executed transaction must be exactly what the double reproduces: the
	# ledger grew by ONE entry, at the END, equal to the sent id, and every
	# stored balance is unchanged (the committed row is free, so the derived
	# debit is the all-zero vector).
	var after_sink := {"error": ""}
	var after := _read_json_into(EXPAND_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_expand_error = str(after_sink["error"])
		return false
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty() \
			or not ((after_maps as Array)[0] is Dictionary):
		_expand_error = "expand fixture after state carries no first map"
		return false
	var after_map: Dictionary = (after_maps as Array)[0] as Dictionary
	var after_owned: Variant = after_map.get("expansions")
	if not (after_owned is Array) \
			or (after_owned as Array).size() != typed_owned.size() + 1:
		_expand_error = "expand fixture after state must append exactly one id"
		return false
	for index in range(typed_owned.size()):
		if int((after_owned as Array)[index]) != int(typed_owned[index]):
			_expand_error = "expand fixture after state reordered or changed " \
				+ "an existing ledger entry"
			return false
	var appended: Variant = BootData._parse_int((after_owned as Array)[
		(after_owned as Array).size() - 1])
	if appended == null or int(appended) < 0 \
			or int(appended) >= EXPANSION_SCHEDULE_ENTRIES:
		_expand_error = "expand fixture after state appended no priced id"
		return false
	_expand_state = {
		"expansions": typed_owned,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_expand_pid = pid
	return true


## One committed schedule row -> the four non-negative integers the service
## prices, or null when the loaded configuration cannot produce them. JSON
## transports numbers as floats on the pinned engine, so integral floats are
## valid costs. Nothing is defaulted and nothing is coerced: a row the schedule
## cannot describe fails closed with the endpoint's own code.
func _expand_price_row(row: Dictionary) -> Variant:
	var amounts := {}
	for field: String in EXPANSION_PRICE_FIELDS:
		var value: Variant = BootData._parse_int(row.get(field))
		if value == null or int(value) < 0:
			return null
		amounts[field] = int(value)
	return amounts


## The requirement fields a committed row records at a POSITIVE value — the
## two this contract refuses rather than invents (design D3). Order is fixed
## (neighbors first) so a refusal message is deterministic.
func _expand_unmet_requirements(price: Dictionary) -> Array:
	var unmet: Array = []
	for field in ["neighbors", "inventory_qte"]:
		if int(price.get(field, 0)) > 0:
			unmet.append(field)
	return unmet


## The derived eight-slot DEBIT for one committed row (design D2): the row's
## gold-named cost negated into the gold slot, its cash cost negated into the
## cash slot, and the six slots no expansion price names left zero. A fresh
## vector on every call, so a caller can never mutate the derivation for the
## next one.
func _expand_debit_for(price: Dictionary) -> Array:
	var debit: Array = []
	debit.resize(BootData.EXPAND_VECTOR_SLOTS)
	for index in range(BootData.EXPAND_VECTOR_SLOTS):
		debit[index] = 0
	for entry: Array in EXPANSION_DEBIT_FIELDS:
		debit[int(entry[5])] = -int(price.get(str(entry[1]), 0))
	for index: int in BootData.EXPAND_ALWAYS_ZERO_SLOTS:
		debit[index] = 0
	return debit


## The seven stored resource values of the in-memory expansion state, after the
## derived debit has been applied under legacy's `max(current + delta, 0)`
## clamp. Reported verbatim as the response's authoritative `resources`: the
## client takes these values and never applies the debit itself.
func _expand_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_expand_state[key])
	return resources


# --- level-up double (building-xp design D8) -------------------------------


## One level-up intent (the save identity and NOTHING else) over the committed
## executed-legacy level fixture. The intent carries no level, no experience, no
## threshold, and no reward: the target is DERIVED here, from the fixture's OWN
## loaded `levels` schedule and the stored experience, through the one named
## one-based conversion (design D3) — the same shape the real service derives, so
## both implementations answer the same intent identically.
##
## The refusals mirror the endpoint's own, in the endpoint's order (design D4):
## the save-identity codes first (`missing_user_id`, `unknown_user_id`), then
## `level_already_current` when the recorded level already equals the derived
## one, then `xp_below_threshold` when the recorded level has no entry in the
## curve or the stored experience cannot reach that level's own committed
## threshold. **At the committed corpus the derived level IS the recorded one**
## (`xp 4` places level 1 and the save records level 1), so the corpus is
## self-consistent under the one-based reading and this intent is refused — which
## is exactly what the executed fixture records.
##
## On success the ONLY write is the recorded level: a level change moves no
## resource, so the derived vector is the neutral one and every stored balance
## is reported unchanged (design D5).
func level_up_town(user_id: String) -> BootData.LevelUpResult:
	if user_id.strip_edges() == "":
		return _level_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _level_failure("fixture_unreadable", _load_error)
	if not _ensure_level_loaded():
		return _level_failure("fixture_unreadable", _level_error)
	if user_id != _level_pid:
		return _level_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var curve: Variant = _level_schedule()
	if curve == null or (curve as Array).is_empty():
		# A curve the loaded configuration cannot produce is a server-side
		# content failure, never a client value (design D5).
		return _level_failure("internal_error",
			"the committed level curve does not resolve")
	var thresholds: Variant = _level_thresholds(curve)
	if thresholds == null:
		return _level_failure("internal_error",
			"the committed level curve records no strictly increasing "
			+ "exp_required ladder")
	var ladder: Array = thresholds
	var xp := int(_level_state["xp"])
	var recorded := int(_level_state["level"])
	var derived: Variant = _level_derived_for(xp, ladder)
	if derived == null:
		# The curve's floor sits above this player's experience, so NO level is
		# derivable. A content/state failure, never a value this contract may
		# round into place.
		return _level_failure("internal_error",
			"the committed level curve begins at %d experience and this player "
			% int(ladder[0]) + "has %d" % xp)
	# Design D4, first refusal: there is nothing to do. Answered BEFORE any
	# write, which is what keeps an already-consistent level from being rewritten
	# as a transaction.
	if recorded == int(derived):
		return _level_failure("level_already_current",
			"the recorded level is already %d, which is the level the committed "
			% int(derived)
			+ "curve derives for %d stored experience" % xp)
	# Design D4, second refusal, and design D2's reported disagreement: the
	# recorded level sits above what the stored experience supports, so no
	# advancement is derivable. Reported with both values and the threshold that
	# separates them; never reconciled, never paid for.
	var recorded_index: Variant = _level_entry_index(recorded,
		(curve as Array).size())
	if recorded_index == null:
		return _level_failure("xp_below_threshold",
			"the recorded level %d has no entry in the committed curve (which "
			% recorded + "holds %d levels), so the stored experience %d cannot "
			% [(curve as Array).size(), xp] + "be checked against it")
	var recorded_threshold: Variant = _level_row_threshold(curve,
		int(recorded_index))
	if recorded_threshold == null:
		return _level_failure("internal_error",
			"the committed level curve holds no readable entry for level %d"
			% recorded)
	if xp < int(recorded_threshold):
		return _level_failure("xp_below_threshold",
			"the stored experience %d cannot reach the recorded level %d, whose "
			% [xp, recorded] + "committed threshold is %d; the committed curve "
			% int(recorded_threshold) + "derives level %d" % int(derived))
	# The ONE write the branch performs: `map["level"] = new_level` with the
	# DERIVED level. No placement, no storage, no bought-units bookkeeping, no
	# private state, and — because a level change moves no resource — no
	# balance (design D5).
	_level_state["level"] = int(derived)
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return BootData.parse_level_up({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"derived_level": int(derived),
		"level_before": recorded,
		"level_after": int(_level_state["level"]),
		"curve": _level_curve_block(curve, ladder, xp),
		"resources": _level_resources(),
	})


## Structured failure in the service's error envelope shape, parsed by the same
## shared parser the live implementation uses.
func _level_failure(code: String, message: String) -> BootData.LevelUpResult:
	return BootData.parse_level_up({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed level fixture's before-state into mutable process state
## (once). Structural failures are named with the offending field; every other
## double's error state is untouched (independent sinks).
func _ensure_level_loaded() -> bool:
	if _level_loaded:
		return _level_error == ""
	_level_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(LEVEL_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_level_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(LEVEL_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_level_error = str(after_sink["error"])
		return false
	return _init_level_state(before)


## Validates the level fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails closed
## instead of crashing the double. **Only the recorded level and the seven
## stored balances are kept**: the executed level-up writes nothing else (not
## `items`, not `store`, not `boughtUnits`, not `privateState`, not the rest of
## `playerInfo`), so keeping more would be inventing state this line never
## touches.
##
## The after-state is validated to hold exactly the documented transaction — the
## recorded level UNCHANGED (at the committed corpus the derived level already
## equals the recorded one, so the executed `level_up` rewrote an identical
## value) and every stored balance unchanged — so a capture that is not the
## transaction this double reproduces fails closed here.
func _init_level_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_level_error = "level fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_level_error = "level fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var level: Variant = BootData._parse_int(map.get("level"))
	if level == null or int(level) < 0:
		_level_error = "level fixture before state lacks map level"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if value == null or int(value) < 0:
			_level_error = "level fixture before state lacks map %s" % key
			return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_level_error = "level fixture before state lacks playerInfo/privateState"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_level_error = "level fixture before state lacks save fields"
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(LEVEL_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_level_error = str(after_sink["error"])
		return false
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty() \
			or not ((after_maps as Array)[0] is Dictionary):
		_level_error = "level fixture after state carries no first map"
		return false
	var after_map: Dictionary = (after_maps as Array)[0] as Dictionary
	var after_level: Variant = BootData._parse_int(after_map.get("level"))
	if after_level == null or int(after_level) != int(level):
		_level_error = ("the executed level fixture must record the SAME level "
			+ "before and after: at the committed corpus the derived level "
			+ "already equals the recorded one, so the executed level_up "
			+ "rewrote an identical value")
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var moved: Variant = BootData._parse_int(after_map.get(key))
		if moved == null or int(moved) != int(map.get(key)):
			_level_error = "the executed level fixture moved map %s" % key
			return false
	if (after as Dictionary).get("playerInfo") != before.get("playerInfo") \
			or (after as Dictionary).get("privateState") != before.get(
				"privateState"):
		_level_error = "the executed level fixture moved the player info or " \
			+ "the private state"
		return false
	_level_state = {
		"level": int(level),
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_level_pid = str(pid)
	return true


## The ONE named one-based schedule conversion, mirroring the service's equally
## named `level_envelope.entry_index_for_level` (design D1): stored level *n* is
## entry *n* minus one. The interpretation is **derived-provisional** and the
## **rejected** alternative is the **zero-based** reading, which the committed
## corpus contradicts (`xp 4` implies level 0 there while the save records
## level 1). A level below 1, a level above the curve, and a non-integer all
## return `LEVEL_NO_INDEX`; nothing raises, and nothing coerces.
func _level_entry_index(level: int, entries: int) -> Variant:
	if level < 1:
		return LEVEL_NO_INDEX
	if entries > 0 and level > entries:
		return LEVEL_NO_INDEX
	return level - 1


## The committed curve's `exp_required` ladder in committed positional order,
## read verbatim, or null when the loaded configuration cannot describe a
## strictly increasing non-negative ladder. Nothing is rebalanced, smoothed, or
## interpolated (design D7), so a content drift fails closed here rather than
## producing a silently different level model.
func _level_thresholds(curve: Array) -> Variant:
	var thresholds: Array = []
	for position in range(curve.size()):
		var row: Variant = curve[position]
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
	if thresholds.is_empty():
		return null
	return thresholds


## The level the committed curve implies for a stored experience: the highest
## level whose threshold the experience meets, resolved through the one named
## conversion. Null when the curve's floor sits above the experience, when the
## experience is not a non-negative integer, or when the ladder is unreadable.
func _level_derived_for(xp: int, thresholds: Array) -> Variant:
	if xp < 0:
		return null
	if xp < int(thresholds[0]):
		return null
	var index := 0
	for position in range(thresholds.size()):
		if xp >= int(thresholds[position]):
			index = position
		else:
			break
	return index + 1


## One committed curve entry's non-negative `exp_required`, or null. The
## position is a POSITION, never a level: a caller that wants a level resolves
## it through the one named conversion first.
func _level_row_threshold(curve: Array, position: int) -> Variant:
	if position < 0 or position >= curve.size():
		return null
	var row: Variant = curve[position]
	if not (row is Dictionary):
		return null
	var value: Variant = BootData._parse_int((row as Dictionary).get(
		"exp_required"))
	if value == null or int(value) < 0:
		return null
	return int(value)


## One committed curve entry's `name`, or null when the entry records none. A
## name is a **label, not an identifier** (44 distinct names over 100 entries),
## so it is read for display only and never used to resolve a level. The reward
## fields are deliberately NEVER read: no legacy branch reads them, so paying
## or showing one would invent an economy (design D7).
func _level_row_name(curve: Array, level: int) -> Variant:
	var index: Variant = _level_entry_index(level, curve.size())
	if index == null or int(index) == LEVEL_NO_INDEX:
		return null
	var row: Variant = curve[int(index)]
	if not (row is Dictionary):
		return null
	var value: Variant = (row as Dictionary).get("name")
	if not (value is String) or str(value).is_empty():
		return null
	return str(value)


## The committed curve the double derives from: the fixture's OWN loaded
## configuration, read at its positional index and never through a level — the
## same separation the service keeps, so a caller's own arithmetic can never
## index the curve.
func _level_schedule() -> Variant:
	return _config_payload.get(LEVELS_KEY)


## The response's `curve` block: the committed facts the service used, with every
## level resolved through the one named conversion. The `next_*` fields and
## `remaining` are **null at the curve's top level** rather than a sentinel value,
## because "there is no next level" is a reported state and not an error.
func _level_curve_block(curve: Array, thresholds: Array, xp: int) -> Dictionary:
	var derived: int = int(_level_derived_for(xp, thresholds))
	# The next level is resolved through the one named conversion and reported as
	# a LEVEL, never as the conversion's positional index: the two differ by
	# exactly the index base D1 settles, so reporting the index here would be the
	# off-by-one this line exists to prevent.
	var following_index: Variant = _level_entry_index(derived + 1, curve.size())
	var following: Variant = null
	if following_index != null and int(following_index) != LEVEL_NO_INDEX:
		following = int(following_index) + 1
	var next_threshold: Variant = null
	var next_name: Variant = null
	var remaining: Variant = null
	if following != null:
		var own_index: Variant = _level_entry_index(int(following), curve.size())
		if own_index != null and int(own_index) != LEVEL_NO_INDEX:
			next_threshold = _level_row_threshold(curve, int(own_index))
			next_name = _level_row_name(curve, int(following))
			if next_threshold != null:
				var left := int(next_threshold) - xp
				remaining = left if left > 0 else 0
	return {
		"entries": curve.size(),
		"index_base": LEVEL_INDEX_BASE,
		"derivation_status": LEVEL_DERIVATION_STATUS,
		"rejected_alternative": LEVEL_REJECTED_ALTERNATIVE,
		"entry_name": _level_row_name(curve, derived),
		"entry_exp_required": int(_level_row_threshold(curve,
			_level_entry_index(derived, curve.size()))),
		"next_level": following,
		"next_name": next_name,
		"next_exp_required": next_threshold,
		"remaining": remaining,
		"xp": xp,
	}


## The seven stored resource values of the in-memory level state, reported
## verbatim as the response's authoritative `resources`. A level-up moves none of
## them, so these are the same values the intent started from — which is the
## strongest form of the "nothing moved" proof the endpoint requires.
func _level_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_level_state[key])
	return resources


# --- production-queue double (unit-queues design D8) ------------------------


## One production-queue **push** intent (the save identity and the target row's
## key, and NOTHING else) over the committed executed-legacy queue fixture. The
## intent carries no count, no cost, no duration, no training time, and no
## readiness: the **action** names the outcome and the double applies the legacy
## branch's own recorded effect — `nu` becomes `(nu + 1)` when present and `1`
## when absent, and `ts` is stamped with a **fixture** instant (never the wall
## clock, so the double stays deterministic).
##
## **No producer, duration, level, or count check is applied** (design D5): the
## three legacy branches validate nothing and the recorded absence of validation
## is not permission to add one here, so any readable row may be queued, an
## already-queued row may be queued again, and the count is **never** capped.
##
## The refusals mirror the endpoint's own, in the endpoint's order (design D4):
## the save-identity codes first (`missing_user_id`, `unknown_user_id`), then
## `invalid_map_key`, then `unknown_map_key` — the endpoint resolves the key
## against the save **before** deriving, because legacy's missing-item path
## returns early **while the batch still persists**, so accepting one here would
## report a queue change that never happened.
##
## On success the ONLY write is the addressed row's attribute bag: no placement
## count, no storage, no bought-units bookkeeping, no private state, and —
## because a queue moves no resource — no balance (design D4/D5).
func push_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	return _queue_intent(user_id, map_key, "push")


## One production-queue **pop** intent under the same contract. The branch's own
## rules are the whole effect: with `nu` **absent** it returns without writing
## anything — an **inert recorded no-op** the endpoint answers `success` to — and
## otherwise it decrements, re-stamping `ts` on a partial decrement and
## **deleting `nu`, `ts`, and `ui` together** at zero.
func pop_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	return _queue_intent(user_id, map_key, "pop")


## The one place both queue intents run, so the wire contract, the refusal order,
## and the recorded effect can never drift between the push and the pop.
func _queue_intent(user_id: String, map_key: int,
		action: String) -> BootData.QueueResult:
	if user_id.strip_edges() == "":
		return _queue_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _queue_failure("fixture_unreadable", _load_error)
	if not _ensure_queue_loaded():
		return _queue_failure("fixture_unreadable", _queue_error)
	if user_id != _queue_pid:
		return _queue_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if map_key < 0:
		return _queue_failure("invalid_map_key",
			"map_key must be an integer, got %d" % map_key)
	if not (_queue_state["rows"] as Dictionary).has(str(map_key)):
		return _queue_failure("unknown_map_key",
			"no placement with key %d in this save's map" % map_key)
	var key := str(map_key)
	var before_row: Variant = ((_queue_state["rows"] as Dictionary)[key]
		as Array).duplicate(true)
	var before_attr: Dictionary = before_row[QUEUE_ATTR_SLOT] as Dictionary
	var effect := _queue_effect(before_attr, action)
	if not bool(effect.get("ok", false)):
		# A server-side shape failure of the addressed row's bag: legacy would
		# raise out of its helper, and the endpoint answers internal_error.
		return _queue_failure("internal_error", str(effect.get("error", "")))
	var after_attr: Dictionary = (before_attr as Dictionary).duplicate(true)
	if bool(effect.get("no_op", false)):
		# engine.py:193-194: nothing at all is written. That is a SUCCESS.
		after_attr = (before_attr as Dictionary).duplicate(true)
	else:
		for removed: String in (effect.get("removed", []) as Array):
			after_attr.erase(removed)
		for written: String in (effect.get("written", []) as Array):
			after_attr[written] = _queue_stamp_for(written, effect)
	var after_row: Variant = before_row.duplicate(true)
	(after_row as Array)[QUEUE_ATTR_SLOT] = after_attr
	(_queue_state["rows"] as Dictionary)[key] = after_row
	# The same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return BootData.parse_queue({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"action": action,
		"map_key": map_key,
		"previous": before_row,
		"row": after_row,
		"queue": _queue_block(after_attr),
		"resources": _queue_resources(),
	})


## Structured failure in the service's error envelope shape, parsed by the same
## shared parser the live implementation uses.
func _queue_failure(code: String, message: String) -> BootData.QueueResult:
	return BootData.parse_queue({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The recorded legacy effect of one queue command on a bag — DERIVED here, never
## read from a response. Returns
##   `{ok, error, removed, written, count, stamp, no_op, teardown}`
##
## The count is exact (`(nu + 1)`, `1`, or `nu - 1`); the start instant is a
## **fixture** value because the branch stamps the wall clock and the double
## never reads one (design D8), which keeps every run byte-identical. Every bag
## key the branch does **not** own is left in place by construction, because
## this function returns the keys to remove and the keys to write and nothing
## else touches the bag.
func _queue_effect(before_attr: Dictionary, action: String) -> Dictionary:
	var empty := {
		"ok": true, "error": "", "removed": [] as Array, "written": [] as Array,
		"count": null, "stamp": 0, "no_op": false, "teardown": false,
	}
	if action == "push":
		var count: Variant = before_attr.get(QUEUE_KEY_COUNT, null)
		if count != null and not (count is int):
			return {
				"ok": false,
				"error": "the addressed row's %r is %r, not an integer"
					% [QUEUE_KEY_COUNT, count],
			}
		return {
			"ok": true, "error": "", "removed": [] as Array,
			"written": [QUEUE_KEY_COUNT, QUEUE_KEY_START],
			"count": (int(count) + 1) if count != null else 1,
			"stamp": _queue_stamp_value(), "no_op": false, "teardown": false,
		}
	# pop
	if not before_attr.has(QUEUE_KEY_COUNT):
		# engine.py:193-194: the helper returns without writing anything.
		return {
			"ok": true, "error": "", "removed": [] as Array,
			"written": [] as Array, "count": null, "stamp": 0,
			"no_op": true, "teardown": false,
		}
	var current: Variant = before_attr.get(QUEUE_KEY_COUNT)
	if not (current is int) or int(current) < 0:
		return {
			"ok": false,
			"error": "the addressed row's %r is %r, not a non-negative count"
				% [QUEUE_KEY_COUNT, current],
		}
	if int(current) - 1 > 0:
		return {
			"ok": true, "error": "", "removed": [] as Array,
			"written": [QUEUE_KEY_COUNT, QUEUE_KEY_START],
			"count": int(current) - 1, "stamp": _queue_stamp_value(),
			"no_op": false, "teardown": false,
		}
	# The three-key teardown: nu, ts, and ui die TOGETHER (engine.py:198-204).
	return {
		"ok": true, "error": "",
		"removed": [QUEUE_KEY_COUNT, QUEUE_KEY_START, QUEUE_KEY_UNIT_ID],
		"written": [] as Array, "count": null, "stamp": 0,
		"no_op": false, "teardown": true,
	}


## The value one written key takes: the derived count for `nu`, the fixture
## instant for `ts`. The two are distinguished by name, so a future key cannot be
## written with the count by accident.
func _queue_stamp_for(key: String, effect: Dictionary) -> Variant:
	if key == QUEUE_KEY_START:
		return int(effect.get("stamp", 0))
	return int(effect.get("count", 0))


## The start instant a queue stamp takes in the double. The legacy branch stamps
## `timestamp_now()`, which the double deliberately never reads: it reuses the
## instant the committed executed push recorded, so an offline run is
## deterministic and byte-identical. No elapsed-time rule is computed from it
## either way — the legacy server has none (design D1/D2).
func _queue_stamp_value() -> int:
	return int(_queue_state.get("stamp", 0))


## The double's own committed queue facts as the response's authoritative
## `queue` block, mirroring the service's `project_queue`: the three committed
## keys **verbatim**, a named absence rather than a zero, and the service's own
## `absent_is_absent` statement. `ui` is reported verbatim and is never coerced
## (design D7).
func _queue_block(attr: Dictionary) -> Dictionary:
	var carried: Array = []
	for key: String in [QUEUE_KEY_COUNT, QUEUE_KEY_START, QUEUE_KEY_UNIT_ID]:
		if attr.has(key):
			carried.append(key)
	return {
		"present": not carried.is_empty(),
		"count": attr.get(QUEUE_KEY_COUNT, null),
		"start_instant": attr.get(QUEUE_KEY_START, null),
		"queued_unit_id": attr.get(QUEUE_KEY_UNIT_ID, null),
		"keys": carried,
		"absent_is_absent": true,
	}


## The seven stored resource values of the in-memory queue state, reported
## verbatim as the response's authoritative `resources`. A queue moves none of
## them, so these are the same values the intent started from — the strongest
## form of the "nothing moved" proof the endpoint requires (design D4).
func _queue_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_queue_state[key])
	return resources


## Loads the committed queue fixture's before-state into mutable process state
## (once). Structural failures are named with the offending field; every other
## double's error state is untouched (independent sinks).
func _ensure_queue_loaded() -> bool:
	if _queue_loaded:
		return _queue_error == ""
	_queue_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(QUEUE_PUSH_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_queue_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	var push_after := _read_json_into(QUEUE_PUSH_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_queue_error = str(after_sink["error"])
		return false
	if not _read_queue_stamp(push_after):
		return false
	if not _init_queue_state(before):
		return false
	if not _validate_queue_push_after(push_after):
		return false
	# The pop pair is validated as ONE transaction with the push: its
	# before-state must be the push's after-state, so the two steps cannot drift
	# into unrelated captures, and its after-state must be the teardown result.
	var pop_before_sink := {"error": ""}
	var pop_before := _read_json_into(QUEUE_POP_BEFORE_FIXTURE, pop_before_sink)
	if str(pop_before_sink["error"]) != "":
		_queue_error = str(pop_before_sink["error"])
		return false
	var pop_after_sink := {"error": ""}
	var pop_after := _read_json_into(QUEUE_POP_AFTER_FIXTURE, pop_after_sink)
	if str(pop_after_sink["error"]) != "":
		_queue_error = str(pop_after_sink["error"])
		return false
	return _validate_queue_pop_after(pop_before, pop_after)


## Reads the start instant the committed executed push stamped, so the double's
## own stamp is the capture's value rather than a literal: the legacy branch
## stamps `timestamp_now()`, so the capture is the only authority, and a
## re-capture must move the double with it rather than silently disagree.
## No elapsed-time rule is computed from the value either way (design D1/D2).
func _read_queue_stamp(push_after: Dictionary) -> bool:
	var items: Variant = (push_after.get("maps", []) as Array)[0].get("items", {})
	var row: Variant = (items as Dictionary).get(QUEUE_TARGET_KEY, null)
	if not (row is Array) or (row as Array).size() != QUEUE_ROW_SLOTS:
		_queue_error = "queue fixture push after state carries no row at map key %s" \
			% QUEUE_TARGET_KEY
		return false
	var bag: Variant = (row as Array)[QUEUE_ATTR_SLOT]
	var stamp: Variant = BootData._parse_int((bag as Dictionary).get(
		QUEUE_KEY_START, null))
	if stamp == null or int(stamp) <= 0:
		_queue_error = ("the executed queue push recorded no start instant at "
			+ "map key %s: the branch stamps one, so this is a fixture defect"
			% QUEUE_TARGET_KEY)
		return false
	_queue_fixture_stamp = int(stamp)
	return true


## Validates the queue fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails closed
## instead of crashing the double. **Only the placement map and the seven stored
## balances are kept**: a push and a pop write nothing else (not the storage,
## not `boughtUnits`, not `privateState`, not the rest of `playerInfo`), so
## keeping more would be inventing state this line never touches.
##
## Every row is kept as a **copy**, keyed by its committed string map key, so an
## addressed row's `attr` bag can be rewritten without touching any other row —
## which is what the endpoint's own "every other row byte-identical" proof
## depends on, and what makes a refused intent leave the corpus untouched.
func _init_queue_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_queue_error = "queue fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_queue_error = "queue fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary) or (items as Dictionary).is_empty():
		_queue_error = "queue fixture before state carries no placement map"
		return false
	var rows: Dictionary = {}
	for key: Variant in (items as Dictionary).keys():
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != QUEUE_ROW_SLOTS:
			_queue_error = "queue fixture row %s is not an eight-field row" \
				% str(key)
			return false
		if not ((row as Array)[QUEUE_ATTR_SLOT] is Dictionary):
			_queue_error = "queue fixture row %s carries a non-object attr bag" \
				% str(key)
			return false
		rows[str(key)] = (row as Array).duplicate(true)
	if not rows.has(str(QUEUE_TARGET_MAP_KEY)):
		_queue_error = ("queue fixture before state carries no placement at "
			+ "map key %d" % QUEUE_TARGET_MAP_KEY)
		return false
	for name in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(name)
		if value == null or int(value) < 0:
			_queue_error = "queue fixture before state lacks map %s" % name
			return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_queue_error = "queue fixture before state lacks playerInfo/privateState"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_queue_error = "queue fixture before state lacks save fields"
		return false
	_queue_state = {
		"rows": rows,
		"stamp": _queue_fixture_stamp,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_queue_pid = str(pid)
	return true


## Validates the executed **push** against the double's in-memory state: the
## addressed row's bag gained `nu` = 1 and a stamped `ts`, every other key it
## carried is untouched, **every other row is byte-identical**, and every stored
## resource is byte-identical. A capture that is not this transaction fails
## closed here rather than producing a differently-behaving double.
func _validate_queue_push_after(push_after: Dictionary) -> bool:
	var rows: Variant = (_queue_state["rows"] as Dictionary).duplicate(true)
	var target: Variant = rows[QUEUE_TARGET_KEY]
	(target as Array)[QUEUE_ATTR_SLOT] = {
		QUEUE_KEY_COUNT: 1,
		QUEUE_KEY_START: int(_queue_state["stamp"]),
	}
	rows[QUEUE_TARGET_KEY] = target
	return _queue_after_matches(push_after, rows, "push")


## Validates the executed **pop** against the double's in-memory state: the
## pop's before-state is the push's after-state (so the pair runs as ONE recorded
## transaction), and the pop's after-state is the push's before-state again — the
## **three-key teardown** returned the bag to empty, leaving every other row and
## every stored resource byte-identical.
func _validate_queue_pop_after(pop_before: Dictionary,
		pop_after: Dictionary) -> bool:
	var queued: Dictionary = (_queue_state["rows"] as Dictionary).duplicate(true)
	var target: Variant = queued[QUEUE_TARGET_KEY]
	(target as Array)[QUEUE_ATTR_SLOT] = {
		QUEUE_KEY_COUNT: 1,
		QUEUE_KEY_START: int(_queue_state["stamp"]),
	}
	queued[QUEUE_TARGET_KEY] = target
	if not _queue_rows_match(pop_before, queued,
			"the pop's before state"):
		return false
	queued[QUEUE_TARGET_KEY] = _queue_original_target()
	return _queue_after_matches(pop_after, queued, "pop")


## The double's own documented teardown result for the addressed row: the bag
## **empty again**, which is what the executed pop recorded.
func _queue_original_target() -> Variant:
	var row: Variant = ((_queue_state["rows"] as Dictionary)[QUEUE_TARGET_KEY]
		as Array).duplicate(true)
	(row as Array)[QUEUE_ATTR_SLOT] = {}
	return row


## Whether one committed after-state holds exactly the double's own expectation:
## the same placement map, and all seven stored resources unchanged. A resource
## the executed legacy transaction moved is a fixture defect, not a rule to
## adopt, so it fails closed.
func _queue_after_matches(after: Dictionary, rows: Dictionary,
		label: String) -> bool:
	var maps: Variant = after.get("maps")
	if not (maps is Array) or (maps as Array).is_empty() \
			or not ((maps as Array)[0] is Dictionary):
		_queue_error = "queue fixture %s after state carries no first map" % label
		return false
	var map: Dictionary = (maps as Array)[0] as Dictionary
	if not _queue_rows_match(after, rows, "the %s after state" % label):
		return false
	var info: Variant = after.get("playerInfo")
	var priv: Variant = after.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_queue_error = "queue fixture %s after state lacks the save fields" \
			% label
		return false
	var stored := {
		"xp": map.get("xp"), "gold": map.get("gold"), "wood": map.get("wood"),
		"oil": map.get("oil"), "steel": map.get("steel"),
		"cash": (info as Dictionary).get("cash"),
		"mana": (priv as Dictionary).get("mana"),
	}
	for name: String in RESOURCE_KEYS:
		if int(stored[name]) != int(_queue_state[name]):
			_queue_error = ("the executed %s moved the %s balance, which no queue "
				% [label, name] + "command does: the double refuses to reproduce "
				+ "a fixture that is not the recorded transaction")
			return false
	return true


## Whether one committed save's placement map equals the double's own expectation,
## row by row, so an unaddressed row changing is a failure rather than an
## unreported difference.
func _queue_rows_match(document: Dictionary, rows: Dictionary,
		label: String) -> bool:
	var maps: Variant = document.get("maps")
	if not (maps is Array) or (maps as Array).is_empty() \
			or not ((maps as Array)[0] is Dictionary):
		_queue_error = "%s carries no first map" % label
		return false
	var items: Variant = ((maps as Array)[0] as Dictionary).get("items")
	if not (items is Dictionary):
		_queue_error = "%s carries no placement map" % label
		return false
	if (items as Dictionary).size() != rows.size():
		_queue_error = ("%s holds %d placements, not the committed %d"
			% [label, (items as Dictionary).size(), rows.size()])
		return false
	var differing: Array = []
	for key: Variant in rows.keys():
		if not (items as Dictionary).has(key) \
				or _queue_normalize((items as Dictionary)[key]) \
					!= _queue_normalize(rows[key]):
			differing.append(str(key))
	if not differing.is_empty():
		_queue_error = "%s changed row(s) %s, which this queue transaction " \
			% [label, ", ".join(PackedStringArray(differing))] \
			+ "never writes"
		return false
	return true


## The pinned engine's JSON parser widens every committed number to a float, so
## both sides of a fixture comparison are normalised to integers first: a
## captured `1.0` and the derived `1` are the same committed value, and
## comparing them raw would report a difference no save ever had.
func _queue_normalize(value: Variant) -> Variant:
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_queue_normalize(entry))
		return list
	if value is Dictionary:
		var bag := {}
		for key: Variant in (value as Dictionary).keys():
			bag[key] = _queue_normalize((value as Dictionary)[key])
		return bag
	return value


## One collection-completion intent under the **same** contract the live
## implementation sends: the save identity and a collection id, and nothing else.
##
## The double is deterministic and in-memory: it reads the committed
## executed-legacy collection fixture's before-state (whose ``maps[0]["store"]``
## is ``{}`` and whose ``privateState["collections"]`` is ``[]``), derives the
## prize from the **committed** ``collections`` table carried by the captured
## ``config.json`` payload — the same payload the placement and purchase doubles
## already index — and grants **exactly** that bag, appending exactly one
## ledger id when it is absent.  It never reads a wall clock and never writes a
## file, so every run is byte-identical.
##
## The refusals mirror the endpoint's own, in the endpoint's order (design D1/D2):
## the save-identity codes first, then ``invalid_collection_id`` for anything
## that is not a strict integer, then ``unknown_collection_id`` for an id the
## committed table does not resolve.  A **negative** or zero id is NOT refused:
## the legacy clamp resolves it to index 0, so it is answered with collection
## 1's grant and ``aliased: true``, exactly as the service answers it.
func complete_collection_town(user_id: String,
		collection_id: int) -> BootData.CollectionResult:
	if user_id.strip_edges() == "":
		return _collection_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_collection_loaded():
		return _collection_failure("fixture_unreadable", _collection_error)
	if user_id != _collection_pid:
		return _collection_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var projection := _collection_prize(collection_id)
	if not bool(projection.get("resolved", false)):
		var code := str(projection.get("reason", ""))
		if code == "invalid_collection_id":
			return _collection_failure(code, str(projection.get("error", "")))
		return _collection_failure("unknown_collection_id",
			str(projection.get("error", "")))
	var before_store: Dictionary = (_collection_state["store"] as Dictionary) \
		.duplicate(true)
	var before_ledger: Array = (_collection_state["ledger"] as Array) \
		.duplicate(true)
	var bag: Dictionary = projection["prize"]
	var after_store: Dictionary = before_store.duplicate(true)
	for key: Variant in bag.keys():
		var id_text := str(key)
		var quantity := int(bag[key])
		after_store[id_text] = int(after_store.get(id_text, 0)) + quantity
	var after_ledger: Array = before_ledger.duplicate(true)
	var appended := not after_ledger.has(collection_id)
	if appended:
		after_ledger.append(collection_id)
	_collection_state["store"] = after_store
	_collection_state["ledger"] = after_ledger
	var entries: Array = []
	for key: Variant in _collection_sorted_keys(bag):
		entries.append({"item_id": str(key), "quantity": int(bag[key])})
	var first: Dictionary = entries[0]
	# The same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return BootData.parse_collection({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"collection_id": collection_id,
		"grant": {
			"command": "complete_collection",
			"item_id": str(first["item_id"]),
			"quantity": int(first["quantity"]),
			"item_count": entries.size(),
			"quantity_total": _collection_total(bag),
			"derived_from": "the committed collections table: the service looks "
				+ "up what the named collection grants and accepts no prize, item "
				+ "id, or quantity from the client",
		},
		"prize": {
			"name": str(projection["name"]),
			"id_column": str(projection["id_column"]),
			"bag": bag.duplicate(true),
			"entries": entries,
		},
		"index": {
			"base": "one-based",
			"derivation_status": "derived-provisional",
			"rejected_alternative": "zero-based",
			"rule": "index = max(0, collection - 1) over the committed table",
			"alias_rule": "collection id 0 and collection id 1 resolve to the "
				+ "same committed prize, as does every negative id",
			"requested": int(projection["requested_index"]),
			"resolved": int(projection["index"]),
			"clamped": bool(projection["clamped"]),
			"aliased": bool(projection["aliased"]),
			"alias_of": (int(projection["alias_of"])
				if int(projection["alias_of"]) >= 0 else null),
		},
		"eligibility": {
			"checked": false,
			"rule": "NO ELIGIBILITY CHECK: the legacy server verifies nothing "
				+ "about whether a collection was earned, and the committed "
				+ "item_ids requirement list is read by no branch at all",
		},
		"store_before": before_store,
		"store_after": after_store,
		"ledger_before": before_ledger,
		"ledger_after": after_ledger,
		"ledger_appended": appended,
		"refusals": [
			{"refusal": "unit_income", "implemented": false,
				"rule": "no committed unit records a positive collect"},
			{"refusal": "cap_semantics", "implemented": false,
				"rule": "max_collects is 0 on every committed unit"},
			{"refusal": "experience_award", "implemented": false,
				"rule": "collect_xp is never read and the only writer takes a "
					+ "client-sent amount"},
		],
		"resources": _collection_resources(),
	})


## Structured failure in the service's error envelope shape, parsed by the same
## shared parser the live implementation uses.
func _collection_failure(code: String, message: String) -> BootData.CollectionResult:
	return BootData.parse_collection({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The double's own committed-prize projection: the one-based index with the
## legacy clamp, the committed row's name and native id column, and the committed
## prize bag — derived from the SAME table the live service reads, so the two
## implementations cannot disagree about what a collection grants.
func _collection_prize(collection_id: Variant) -> Dictionary:
	var table: Array = _collection_state["table"] as Array
	var unknown := func(id: int) -> Dictionary:
		var index := maxi(0, id - 1)
		return {
			"resolved": false,
			"reason": "unknown_collection_id",
			"error": "collection_id %d resolves to index %d, outside the "
				% [id, index] + "%d-entry committed collections table" % table.size(),
			"collection_id": id,
			"requested_index": id - 1,
			"index": index,
			"clamped": index != id - 1,
			"aliased": index != id - 1,
			"alias_of": 1 if index != id - 1 else -1,
			"name": "",
			"id_column": "",
			"prize": {},
		}
	if typeof(collection_id) != TYPE_INT or typeof(collection_id) == TYPE_BOOL:
		return {
			"resolved": false,
			"reason": "invalid_collection_id",
			"error": "collection_id must be an integer",
			"collection_id": collection_id,
			"requested_index": -1,
			"index": -1,
			"clamped": false,
			"aliased": false,
			"alias_of": -1,
			"name": "",
			"id_column": "",
			"prize": {},
		}
	var index := maxi(0, int(collection_id) - 1)
	if index >= table.size():
		return unknown.call(int(collection_id))
	var row: Dictionary = table[index]
	# The captured config keeps `prize` exactly as the legacy server reads it —
	# a JSON-encoded STRING — so it is decoded here the same way
	# `get_collection_prize` decodes it.  An already-parsed object is accepted
	# too, so the double runs against either representation.
	var decoded: Variant = row.get("prize", null)
	if decoded is String:
		var parser := JSON.new()
		decoded = parser.data if parser.parse(str(decoded)) == OK else null
	if not (decoded is Dictionary):
		return unknown.call(int(collection_id))
	var bag := {}
	for key: Variant in (decoded as Dictionary).keys():
		bag[str(key)] = int((decoded as Dictionary)[key])
	return {
		"resolved": not bag.is_empty(),
		"reason": "" if not bag.is_empty() else "unknown_collection_id",
		"error": "" if not bag.is_empty() else ("collection %d grants nothing"
			% int(collection_id)),
		"collection_id": int(collection_id),
		"requested_index": int(collection_id) - 1,
		"index": index,
		"clamped": index != int(collection_id) - 1,
		"aliased": index != int(collection_id) - 1,
		"alias_of": 1 if index != int(collection_id) - 1 else -1,
		"name": str(row.get("name", "")),
		"id_column": str(row.get("id", "")),
		"prize": bag,
	}


## The committed prize bag's keys in a deterministic numeric order, so the
## double's response bytes never depend on a dictionary's iteration order.
func _collection_sorted_keys(bag: Dictionary) -> Array:
	var keys: Array = bag.keys()
	keys.sort_custom(func(a: Variant, b: Variant) -> bool:
		return int(a) < int(b))
	return keys


## The bag's total committed quantity.
func _collection_total(bag: Dictionary) -> int:
	var total := 0
	for key: Variant in bag.keys():
		total += int(bag[key])
	return total


## The seven stored resource values of the in-memory collection state, reported
## verbatim as the response's authoritative `resources`. A completion moves none
## of them, so these are the same values the intent started from — the strongest
## form of the "nothing moved" proof the endpoint requires (design D5).
func _collection_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_collection_state[key])
	return resources


## Loads the committed collection fixture's before-state and the committed
## `collections` table into mutable process state (once). Structural failures are
## named with the offending field; every other double's error state is untouched
## (independent sinks).
##
## The table comes from the **captured config payload** the double already reads
## for placement and purchase — not from a separate file and not from the
## repository working tree — so the double runs on exactly the content the
## executed fixture was captured against.
func _ensure_collection_loaded() -> bool:
	if _collection_loaded:
		return _collection_error == ""
	_collection_loaded = true
	# The committed collections table is read out of the SAME captured
	# config payload the placement and purchase doubles already index, so
	# the base fixtures must be loaded first — independently of them, so
	# this double's failure cannot hide behind another's.
	if not _ensure_loaded():
		_collection_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(COLLECTION_BEFORE_FIXTURE, sink)
	if str(sink["error"]) != "":
		_collection_error = str(sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot leave
	# the double running on an inconsistent oracle.
	var after := _read_json_into(COLLECTION_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_collection_error = str(after_sink["error"])
		return false
	var table: Variant = _config_payload.get("collections")
	if not (table is Array) or (table as Array).is_empty():
		_collection_error = ("the captured config carries no collections table: "
			+ GAME_CONFIG_FIXTURE)
		return false
	var store: Variant = (before.get("maps", []) as Array)[0].get("store", null)
	if not (store is Dictionary):
		_collection_error = ("the collection fixture before state carries no "
			+ "maps[0].store object")
		return false
	var ledger: Variant = (before.get("privateState", {}) as Dictionary).get(
		"collections", null)
	if not (ledger is Array):
		_collection_error = ("the collection fixture before state carries no "
			+ "privateState['collections'] list")
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_collection_error = "the collection fixture before state lacks playerInfo"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_collection_error = "the collection fixture before state lacks save fields"
		return false
	var first_map: Dictionary = (before.get("maps", []) as Array)[0] as Dictionary
	var resources := {}
	for name: String in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = first_map.get(name)
		if value == null or int(value) < 0:
			_collection_error = "the collection fixture before state lacks map %s" \
				% name
			return false
		resources[name] = int(value)
	resources["cash"] = int(cash)
	resources["mana"] = int(mana)
	if not _validate_collection_after(after, store, ledger, resources):
		return false
	resources["store"] = (store as Dictionary).duplicate(true)
	resources["ledger"] = (ledger as Array).duplicate(true)
	resources["table"] = (table as Array).duplicate(true)
	_collection_state = resources
	_collection_pid = str(pid)
	return true


## Validates the executed fixture against the double's own starting state: the
## recorded completion wrote **exactly** the committed prize of collection 1 into
## the empty storage and appended **exactly one** id to the empty ledger, and
## **no stored resource moved**. A capture that is not this transaction fails
## closed here rather than producing a differently-behaving double.
func _validate_collection_after(after: Dictionary, store: Variant, ledger: Variant,
		resources: Dictionary) -> bool:
	var first_map: Variant = (after.get("maps", []) as Array)[0]
	if not (first_map is Dictionary):
		_collection_error = "the collection fixture after state carries no first map"
		return false
	var after_store: Variant = (first_map as Dictionary).get("store", null)
	var after_ledger: Variant = (after.get("privateState", {}) as Dictionary).get(
		"collections", null)
	if not (after_store is Dictionary) or not (after_ledger is Array):
		_collection_error = ("the collection fixture after state carries no store "
			+ "or ledger")
		return false
	var expected_store: Dictionary = (store as Dictionary).duplicate(true)
	for key: Variant in COLLECTION_EXPECTED_PRIZE.keys():
		expected_store[str(key)] = int(COLLECTION_EXPECTED_PRIZE[key])
	if _collection_normalize(after_store) != expected_store:
		_collection_error = ("the executed completion wrote %r, not the committed "
			% [after_store] + "prize %r" % expected_store)
		return false
	if _collection_normalize(after_ledger) != [COLLECTION_FIXTURE_ID]:
		_collection_error = ("the executed completion left the collection ledger "
			+ "%r, not [%d]" % [after_ledger, COLLECTION_FIXTURE_ID])
		return false
	for name: String in RESOURCE_KEYS:
		if _collection_resource_of(after, name) != int(resources[name]):
			_collection_error = ("the executed completion moved the %s balance, "
				% name + "which no collection completion does")
			return false
	return true


## One stored resource of a captured save, as an integer.
func _collection_resource_of(document: Dictionary, name: String) -> int:
	var first_map: Dictionary = (document.get("maps", []) as Array)[0] as Dictionary
	match name:
		"cash":
			return int((document.get("playerInfo", {}) as Dictionary).get("cash", 0))
		"mana":
			return int((document.get("privateState", {}) as Dictionary).get(
				"mana", 0))
		_:
			return int(first_map.get(name, 0))


## The pinned engine's JSON parser widens every committed number to a float, so
## both sides of a fixture comparison are normalised to integers first.
func _collection_normalize(value: Variant) -> Variant:
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_collection_normalize(entry))
		return list
	if value is Dictionary:
		var bag := {}
		for key: Variant in (value as Dictionary).keys():
			bag[key] = _collection_normalize((value as Dictionary)[key])
		return bag
	return value


func _ensure_loaded() -> bool:
	if _loaded:
		return _load_error == ""
	_loaded = true
	_save_list_doc = _read_json(SAVE_LIST_FIXTURE)
	if _load_error == "":
		_config_payload = _read_json(GAME_CONFIG_FIXTURE)
	if _load_error == "":
		_player_info_payload = _read_json(PLAYER_INFO_FIXTURE)
	if _load_error == "" and not (_save_list_doc.get("saves") is Array):
		_load_error = "fixture save list carries no saves array: " \
			+ SAVE_LIST_FIXTURE
	if _load_error == "" and not (_config_payload.get("items") is Array):
		_load_error = "fixture config carries no items array: " \
			+ GAME_CONFIG_FIXTURE
	if _load_error == "":
		_index_config_items()
	return _load_error == ""


## One-time item-id -> item index over the committed config (900 entries),
## so placement lookups never re-scan the payload.
func _index_config_items() -> void:
	_config_items = {}
	for item: Variant in _config_payload.get("items", []):
		if item is Dictionary:
			var id := str((item as Dictionary).get("id", ""))
			if id != "":
				_config_items[id] = item


func _session_envelope() -> Dictionary:
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (the field-stability record lists
		# server_time as time-dependent, so tests never compare its value).
		"server_time": _fixture_server_time(),
		"saves": _save_list_doc.get("saves", []),
	}


## Fixture-derived epoch: `player_info.timestamp` of the captured response.
func _fixture_server_time() -> int:
	var value := BootData._parse_epoch(_player_info_payload.get("timestamp"))
	if value < 0:
		return 0
	return value


func _fixture_names(user_id: String) -> bool:
	for entry in _save_list_doc.get("saves", []):
		if entry is Dictionary and str(entry.get("id", "")) == user_id:
			return true
	return false


# --- placement double (design D8) ------------------------------------------

## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _place_failure(code: String, message: String) -> BootData.PlacementResult:
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed placement fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot
## fixtures' error state is untouched (independent sinks).
func _ensure_placement_loaded() -> bool:
	if _placement_loaded:
		return _placement_error == ""
	_placement_loaded = true
	var before_sink := {"error": ""}
	var after_sink := {"error": ""}
	var before := _read_json_into(PLACEMENT_BEFORE_FIXTURE, before_sink)
	var after := _read_json_into(PLACEMENT_AFTER_FIXTURE, after_sink)
	if str(before_sink["error"]) != "":
		_placement_error = str(before_sink["error"])
		return false
	if str(after_sink["error"]) != "":
		_placement_error = str(after_sink["error"])
		return false
	return _init_placement_state(before, after)


## Validates both fixture documents and builds the in-memory save state.
## Every consumed field is checked, so a malformed fixture fails closed
## instead of crashing the double.
func _init_placement_state(before: Dictionary, after: Dictionary) -> bool:
	var before_map: Variant = _first_map(before, "before")
	if before_map == null:
		return false
	var after_map: Variant = _first_map(after, "after")
	if after_map == null:
		return false
	var items: Variant = (before_map as Dictionary).get("items")
	if not (items is Dictionary):
		_placement_error = "placement fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_placement_error = "placement fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (before_map as Dictionary).get(key)
		if not (value is int or value is float):
			_placement_error = "placement fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_placement_error = "placement fixture before state lacks save fields"
		return false
	# The after-state must add exactly one entry — the capture's placement;
	# its recorded wall-clock timestamp becomes the fake's entry epoch, so
	# the double never reads the wall clock (deterministic by construction).
	var after_items: Variant = (after_map as Dictionary).get("items")
	if not (after_items is Dictionary):
		_placement_error = "placement fixture after state carries no items map"
		return false
	var added: Array = []
	for key: Variant in (after_items as Dictionary):
		if not (items as Dictionary).has(str(key)):
			added.append(str(key))
	if added.size() != 1:
		_placement_error = ("placement fixture after state must add exactly "
			+ "one entry, found %d") % added.size()
		return false
	var entry: Variant = (after_items as Dictionary).get(added[0])
	if not (entry is Array) or (entry as Array).size() != 8:
		_placement_error = "placement fixture after entry is not the eight-field array"
		return false
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) < 0 \
			or float(stamp) != floor(float(stamp)):
		_placement_error = "placement fixture entry timestamp is not a non-negative integer"
		return false
	_placement_state = {
		"items": (items as Dictionary).duplicate(true),
		"xp": int((before_map as Dictionary).get("xp")),
		"gold": int((before_map as Dictionary).get("gold")),
		"wood": int((before_map as Dictionary).get("wood")),
		"oil": int((before_map as Dictionary).get("oil")),
		"steel": int((before_map as Dictionary).get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"bought_units": (bought as Array).duplicate(),
	}
	_placement_pid = pid
	_placement_epoch = int(stamp)
	return true


## `save["maps"][0]` of a fixture document, or null (with the error named).
func _first_map(doc: Dictionary, label: String) -> Variant:
	var maps: Variant = doc.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_placement_error = "placement fixture %s state carries no maps array" % label
		return null
	if not ((maps as Array)[0] is Dictionary):
		_placement_error = "placement fixture %s state first map is not an object" % label
		return null
	return (maps as Array)[0]


# --- move double (building-move design D8) ----------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _move_failure(code: String, message: String) -> BootData.PlacementResult:
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed move fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, and purchase fixtures' error state is untouched
## (independent sinks).
func _ensure_move_loaded() -> bool:
	if _move_loaded:
		return _move_error == ""
	_move_loaded = true
	# The pair is read through explicit sinks (the placement pair's
	# precedent), so a malformed capture fails this surface closed without
	# touching the boot, placement, or purchase error state.
	var before_sink := {"error": ""}
	var before := _read_json_into(MOVE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_move_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(MOVE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_move_error = str(after_sink["error"])
		return false
	return _init_move_state(before)


## Validates the move fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it.
func _init_move_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_move_error = "move fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_move_error = "move fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_move_error = "move fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_move_error = "move fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_move_error = "move fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_move_error = "move fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the move's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_move_error = "move fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_move_error = "move fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	_move_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_move_pid = pid
	return true


## The seven stored resource values of the in-memory move state. A move
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta.
func _move_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_move_state[key])
	return resources


# --- sell double (building-sell design D8) ----------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _sell_failure(code: String, message: String) -> BootData.SellResult:
	return BootData.parse_sell({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed sell fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, purchase, and move fixtures' error state is untouched
## (independent sinks).
func _ensure_sell_loaded() -> bool:
	if _sell_loaded:
		return _sell_error == ""
	_sell_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(SELL_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_sell_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(SELL_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_sell_error = str(after_sink["error"])
		return false
	return _init_sell_state(before)


## Validates the sell fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it — and the one
## write a sale performs is the one delete that branch performs.
func _init_sell_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_sell_error = "sell fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_sell_error = "sell fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_sell_error = "sell fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_sell_error = "sell fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_sell_error = "sell fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_sell_error = "sell fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the sell's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_sell_error = "sell fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_sell_error = "sell fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	_sell_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_sell_pid = pid
	return true


## The seven stored resource values of the in-memory sell state. A sell
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta, and no refund is
## claimed.
func _sell_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_sell_state[key])
	return resources


# --- store double (building-store design D8) --------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _store_failure(code: String, message: String) -> BootData.StoreResult:
	return BootData.parse_store({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed store fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, purchase, move, and sell fixtures' error state is
## untouched (independent sinks).
func _ensure_store_loaded() -> bool:
	if _store_loaded:
		return _store_error == ""
	_store_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(STORE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_store_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(STORE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_store_error = str(after_sink["error"])
		return false
	return _init_store_state(before)


## Validates the store fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it — and the two
## writes a store performs are the one pop and the one storage increment
## that branch performs. The storage mapping is read with the same rules the
## endpoint's response carries, so pre-existing entries are never coerced.
func _init_store_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_store_error = "store fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_store_error = "store fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_store_error = "store fixture before state carries no items map"
		return false
	var store: Variant = map.get("store")
	if not (store is Dictionary):
		_store_error = "store fixture before state carries no store map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_store_error = "store fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_store_error = "store fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_store_error = "store fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the store's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_store_error = "store fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_store_error = "store fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# Quantities are counts and keys are item ids: the same shapes the
	# endpoint's storage mapping and the shared parser accept.
	var typed_store := {}
	for key: Variant in (store as Dictionary):
		var id: Variant = BootData._parse_int(key)
		var quantity: Variant = BootData._parse_int(
			(store as Dictionary)[key])
		if id == null or quantity == null or int(id) < 0 or int(quantity) < 0:
			_store_error = "store fixture before state has an invalid store entry"
			return false
		typed_store[str(int(id))] = int(quantity)
	_store_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"store": typed_store,
	}
	_store_pid = pid
	return true


## The seven stored resource values of the in-memory store state. A store
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta, and no storing cost
## is claimed.
func _store_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_store_state[key])
	return resources


# --- upgrade double (building-upgrade design D8) ----------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _upgrade_failure(code: String, message: String) -> BootData.UpgradeResult:
	return BootData.parse_upgrade({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The committed configuration's next tier for one item id, or null when the
## item has no upgrade path. The reference is `upgrades_to`, resolved with the
## documented `-1`/`0`-and-unresolvable-means-none rule (design D2), against
## the same one item index the placement and purchase doubles read — so the
## double derives the target tier exactly the way the endpoint does, and never
## from the caller.
func _upgrade_target(item_id: int) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	var reference: Variant = _config_reference(
		(item as Dictionary).get("upgrades_to"))
	if reference == null or int(reference) <= 0:
		return null
	var target: Variant = _config_items.get(str(int(reference)))
	if not (target is Dictionary):
		return null
	return target


## The committed configuration's string-encoded numeric reference -> its
## integer value, or null when the field is absent or is not an integer at
## all. `upgrades_to` is a STRING in the committed payload (`"24"`, `"-1"`)
## exactly as `costs` is, and the endpoint coerces it the same way
## (`compat_legacy.item_upgrade_to`: `int(str(raw).strip())`), so a
## whitespace-trimmed signed digit string is the documented shape. Nothing
## else is ever coerced — a non-numeric reference is simply no path.
static func _config_reference(value: Variant) -> Variant:
	if value == null:
		return null
	if value is int or value is float:
		return BootData._parse_int(value)
	if not (value is String):
		return null
	var text := str(value).strip_edges()
	if text.is_empty() or text.length() > 16:
		return null
	var digits := text
	if digits.begins_with("-") or digits.begins_with("+"):
		digits = digits.substr(1)
	if digits.is_empty():
		return null
	for character in digits:
		if character < "0" or character > "9":
			return null
	return text.to_int()


## Loads the committed upgrade fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot,
## placement, purchase, move, sell, and store fixtures' error state is
## untouched (independent sinks).
func _ensure_upgrade_loaded() -> bool:
	if _upgrade_loaded:
		return _upgrade_error == ""
	_upgrade_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(UPGRADE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_upgrade_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(UPGRADE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_upgrade_error = str(after_sink["error"])
		return false
	return _init_upgrade_state(before, after)


## Validates the upgrade fixture's before- and after-states and builds the
## in-memory save state. Every consumed field is checked, so a malformed
## fixture fails closed instead of crashing the double. The placements are
## kept as the save's own `items` map keyed by their legacy index, so an index
## resolves exactly as `engine.map_get_item(map, index)` resolves it — and the
## one write an upgrade performs is the one in-place row replacement that pair
## performs. The after-state is read for its recorded wall-clock epoch: the
## key is REUSED, so the double takes the epoch of the row the capture wrote
## rather than naming a key (which is the placement double's job, not this
## one's).
func _init_upgrade_state(before: Dictionary, after: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_upgrade_error = "upgrade fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_upgrade_error = "upgrade fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_upgrade_error = "upgrade fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_upgrade_error = "upgrade fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_upgrade_error = "upgrade fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_upgrade_error = "upgrade fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the upgrade's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_upgrade_error = "upgrade fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_upgrade_error = "upgrade fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# The executed pair REUSES its key, so the after-state carries exactly as
	# many placements as the before-state; anything else means the capture is
	# not the transaction this double reproduces. Exactly one row differs, and
	# its recorded wall-clock timestamp is the deterministic epoch.
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty():
		_upgrade_error = "upgrade fixture after state carries no maps array"
		return false
	if not ((after_maps as Array)[0] is Dictionary):
		_upgrade_error = "upgrade fixture after state first map is not an object"
		return false
	var after_items: Variant = ((after_maps as Array)[0] as Dictionary).get(
		"items")
	if not (after_items is Dictionary):
		_upgrade_error = "upgrade fixture after state carries no items map"
		return false
	if (after_items as Dictionary).size() != typed_items.size():
		_upgrade_error = ("upgrade fixture after state must reuse the same "
			+ "placement keys, found %d against %d") % [
			(after_items as Dictionary).size(), typed_items.size()]
		return false
	var replaced: Array = []
	for key: String in typed_items:
		if not (after_items as Dictionary).has(key):
			_upgrade_error = ("upgrade fixture after state dropped key %s "
				% key + "(an upgrade must reuse its key)")
			return false
		if (after_items as Dictionary)[key] != typed_items[key]:
			replaced.append(key)
	if replaced.size() != 1:
		_upgrade_error = ("upgrade fixture after state must replace exactly "
			+ "one row in place, found %d") % replaced.size()
		return false
	var entry: Variant = (after_items as Dictionary)[replaced[0]]
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) <= 0 \
			or float(stamp) != floor(float(stamp)):
		_upgrade_error = "upgrade fixture fresh row timestamp is not a positive integer"
		return false
	_upgrade_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"bought_units": (bought as Array).duplicate(),
	}
	_upgrade_pid = pid
	_upgrade_epoch = int(stamp)
	return true


## The seven stored resource values of the in-memory upgrade state. An upgrade
## derives a neutral vector (design D4), so these are the state's own values —
## reported verbatim, never a computed delta, and no upgrade cost is claimed.
func _upgrade_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_upgrade_state[key])
	return resources


# --- construction double (building-construction design D8) -------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _construction_failure(code: String,
		message: String) -> BootData.ConstructionResult:
	return BootData.parse_construction({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The addressed item's committed construction duration, or null when the
## loaded configuration cannot supply a POSITIVE one. The reference is the
## item's `build_time`, string-encoded in the committed payload exactly as
## `costs` and `upgrades_to` are, and coerced with the SAME rule the upgrade
## double reads `upgrades_to` with — so the double derives the countdown from
## committed content, never from the caller, exactly the way the endpoint does
## (`compat_legacy.item_build_time`). A non-positive value is refused rather
## than coerced: legacy's `activate` with such a duration would CLEAR the
## addressed row's whole attribute bag, destroying the click counter and any
## friend-assist entries (design D6), which is why this double exposes no
## cancel action and never sends one.
func _construction_build_time(item_id: int) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	var seconds: Variant = _config_reference((item as Dictionary).get("build_time"))
	if seconds == null or int(seconds) <= 0:
		return null
	return seconds


## Loads the committed construction fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot,
## placement, purchase, move, sell, store, and upgrade fixtures' error state is
## untouched (independent sinks).
func _ensure_construction_loaded() -> bool:
	if _construction_loaded:
		return _construction_error == ""
	_construction_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(CONSTRUCTION_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_construction_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(CONSTRUCTION_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_construction_error = str(after_sink["error"])
		return false
	return _init_construction_state(before, after)


## Validates the construction fixture's before- and after-states and builds
## the in-memory save state. Every consumed field is checked, so a malformed
## fixture fails closed instead of crashing the double. The placements are
## kept as the save's own `items` map keyed by their legacy index, so an index
## resolves exactly as `engine.map_get_item(map, index)` resolves it — and the
## only writes a construction performs are the one row's timestamp and
## attribute bag. The after-state is read for its recorded wall-clock start
## instant: the key is REUSED, so the double takes the epoch of the row the
## capture stamped rather than naming a key (which is the placement double's
## job, not this one's).
func _init_construction_state(before: Dictionary, after: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_construction_error = \
			"construction fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_construction_error = \
			"construction fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_construction_error = \
			"construction fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_construction_error = \
			"construction fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_construction_error = \
				"construction fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_construction_error = \
			"construction fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the construction's own resolution
	# depends on); an unusable key is a malformed capture, never a coerced
	# index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_construction_error = "construction fixture placement key '%s' is " \
				% str(key) + "not a positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_construction_error = "construction fixture placement '%s' is not " \
				% str(key) + "the eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# The executed pair REUSES its key, so the after-state carries exactly as
	# many placements as the before-state; anything else means the capture is
	# not the transaction this double reproduces. Exactly one row differs, and
	# its recorded wall-clock start instant is the deterministic epoch.
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty():
		_construction_error = \
			"construction fixture after state carries no maps array"
		return false
	if not ((after_maps as Array)[0] is Dictionary):
		_construction_error = \
			"construction fixture after state first map is not an object"
		return false
	var after_items: Variant = ((after_maps as Array)[0] as Dictionary).get(
		"items")
	if not (after_items is Dictionary):
		_construction_error = \
			"construction fixture after state carries no items map"
		return false
	if (after_items as Dictionary).size() != typed_items.size():
		_construction_error = ("construction fixture after state must reuse "
			+ "the same placement keys, found %d against %d") % [
			(after_items as Dictionary).size(), typed_items.size()]
		return false
	var constructed: Array = []
	for key: String in typed_items:
		if not (after_items as Dictionary).has(key):
			_construction_error = ("construction fixture after state dropped "
				+ "key %s (a construction must reuse its key)") % key
			return false
		if (after_items as Dictionary)[key] != typed_items[key]:
			constructed.append(key)
	if constructed.size() != 1:
		_construction_error = ("construction fixture after state must mutate "
			+ "exactly one row in place, found %d") % constructed.size()
		return false
	var entry: Variant = (after_items as Dictionary)[constructed[0]]
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) <= 0 \
			or float(stamp) != floor(float(stamp)):
		_construction_error = \
			"construction fixture stamped start time is not a positive integer"
		return false
	_construction_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_construction_pid = pid
	_construction_epoch = int(stamp)
	return true


## The seven stored resource values of the in-memory construction state. A
## construction derives a neutral vector (design D4), so these are the state's
## own values — reported verbatim, never a computed delta, and no building cost
## is claimed.
func _construction_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_construction_state[key])
	return resources


# --- collect double (building-collect design D8) ------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _collect_failure(code: String, message: String) -> BootData.CollectResult:
	return BootData.parse_collect({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed collect fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot, placement,
## purchase, move, sell, store, upgrade, and construction fixtures' error
## state is untouched (independent sinks).
func _ensure_collect_loaded() -> bool:
	if _collect_loaded:
		return _collect_error == ""
	_collect_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(COLLECT_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_collect_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(COLLECT_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_collect_error = str(after_sink["error"])
		return false
	return _init_collect_state(before, after)


## Validates the collect fixture's before- and after-states and builds the
## in-memory save state. Every consumed field is checked, so a malformed
## fixture fails closed instead of crashing the double. The placements are kept
## as the save's own `items` map keyed by their legacy index, so an index
## resolves exactly as `engine.map_get_item(map, index)` resolves it — and the
## only writes a collection performs are the addressed row's collection instant
## and the pre-dispatch resource application. The after-state is read for its
## recorded wall-clock collection instant: the key is REUSED, so the double
## takes the epoch of the row the capture re-stamped rather than naming a key
## (which is the placement double's job, not this one's).
func _init_collect_state(before: Dictionary, after: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_collect_error = "collect fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_collect_error = "collect fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_collect_error = "collect fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_collect_error = \
			"collect fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_collect_error = "collect fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_collect_error = "collect fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the collection's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_collect_error = "collect fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_collect_error = "collect fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# The executed collection REUSES its key, so the after-state carries exactly
	# as many placements as the before-state; anything else means the capture is
	# not the transaction this double reproduces. Exactly one row differs, and
	# its recorded wall-clock collection instant is the deterministic epoch.
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty():
		_collect_error = "collect fixture after state carries no maps array"
		return false
	if not ((after_maps as Array)[0] is Dictionary):
		_collect_error = \
			"collect fixture after state first map is not an object"
		return false
	var after_items: Variant = ((after_maps as Array)[0] as Dictionary).get(
		"items")
	if not (after_items is Dictionary):
		_collect_error = "collect fixture after state carries no items map"
		return false
	if (after_items as Dictionary).size() != typed_items.size():
		_collect_error = ("collect fixture after state must reuse the same "
			+ "placement keys, found %d against %d") % [
			(after_items as Dictionary).size(), typed_items.size()]
		return false
	var collected: Array = []
	for key: String in typed_items:
		if not (after_items as Dictionary).has(key):
			_collect_error = ("collect fixture after state dropped key %s " \
				% key + "(a collection must reuse its key)")
			return false
		if (after_items as Dictionary)[key] != typed_items[key]:
			collected.append(key)
	if collected.size() != 1:
		_collect_error = ("collect fixture after state must mutate exactly one "
			+ "row in place, found %d") % collected.size()
		return false
	var entry: Variant = (after_items as Dictionary)[collected[0]]
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) <= 0 \
			or float(stamp) != floor(float(stamp)):
		_collect_error = \
			"collect fixture collection instant is not a positive integer"
		return false
	_collect_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_collect_pid = pid
	_collect_epoch = int(stamp)
	return true


## The seven stored resource values of the in-memory collection state, after
## the derived payout has been applied under legacy's `max(current + delta, 0)`
## clamp. Reported verbatim as the response's authoritative `resources`: the
## client takes these values and never applies the payout itself.
func _collect_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_collect_state[key])
	return resources


## The addressed item's committed collection amount (`collect`), or null when
## the loaded configuration cannot supply a non-negative integer. The field is
## STRING-encoded in the committed payload exactly as `build_time` and
## `upgrades_to` are, and is coerced with the SAME shared rule — so the double
## derives the amount from committed content, never from the caller, exactly
## the way the endpoint does (`compat_legacy.item_collect_amount`).
func _collect_amount(item_id: int) -> Variant:
	return _collect_income_field(item_id, "collect")


## The addressed item's committed collection experience (`collect_xp`), with
## the same coercion and the same null-on-unresolvable rule.
func _collect_experience(item_id: int) -> Variant:
	return _collect_income_field(item_id, "collect_xp")


## The addressed item's committed collection cap (`max_collects`), with the
## same coercion. Only `0` is implemented by design D4; a non-zero value is
## refused with `capped_collection` rather than interpreted.
func _collect_cap(item_id: int) -> Variant:
	return _collect_income_field(item_id, "max_collects")


## The addressed item's committed collection resource type (`collect_type`),
## verbatim: the committed value is a single character from the closed set
## `g` / `w` / `o` / `s` / `c`, and nothing is coerced or defaulted (design
## D6). `null` when the item is not in the loaded configuration at all.
func _collect_resource_type(item_id: int) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	return str((item as Dictionary).get("collect_type", ""))


## One string-encoded committed income field of an item -> its non-negative
## integer value, or null when the field is absent, not an integer at all, or
## negative. Nothing is defaulted: a committed configuration that cannot
## describe the income fails closed with the endpoint's own refusal code.
func _collect_income_field(item_id: int, field: String) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	var value: Variant = _config_reference((item as Dictionary).get(field))
	if value == null or int(value) < 0:
		return null
	return value


## One committed ladder rung's threshold in SECONDS, through the single named
## unit constant (design D1/D3). The committed ladder is in minutes while a
## row's recorded instant is Unix seconds: comparing the two directly would
## make the five-minute rung read as five *seconds* and pay the TOP rung within
## the first seconds of a build, which is the bug the compat side found and
## corrected. A tier outside the committed ladder is refused (0) rather than
## extrapolated.
func _collect_threshold_seconds(tier: int) -> int:
	if tier < 0 or tier >= COLLECT_LADDER_MINUTES.size():
		return 0
	return int(COLLECT_LADDER_MINUTES[tier]) * SECONDS_PER_COMMITTED_MINUTE


## The highest committed rung an elapsed time has reached, CLAMPED at the top
## rung (design D1: never extrapolated), or -1 when no rung is reached
## (design D3: the caller fails closed with `too_early` instead of deriving a
## sub-first-rung amount from the `0.25` multiplier).
func _collect_tier_for(elapsed_seconds: int) -> int:
	var reached: int = -1
	for index in range(COLLECT_LADDER_MINUTES.size()):
		if elapsed_seconds >= _collect_threshold_seconds(index):
			reached = index
	return reached


## The derived eight-slot payout vector for one collection (design D1/D2/D6),
## or null when the committed ladder or the resource type does not resolve. The
## amount lands in the slot its committed resource type names and the experience
## in the experience slot, each scaled by the reached rung's committed
## multiplier and rounded half-up so a fractional product can never put a float
## on the legacy vector; the unread `unknown` slot 0 and the never-produced
## `mana` slot 7 stay zero.
func _collect_payout_for(amount: int, experience: int, resource_type: String,
		tier: int) -> Variant:
	if tier < 0 or tier >= COLLECT_LADDER_MULTIPLIERS.size():
		return null
	var slot: Variant = COLLECT_RESOURCE_SLOTS.get(resource_type)
	if slot == null:
		return null
	var multiplier: float = float(COLLECT_LADDER_MULTIPLIERS[tier])
	# The vector starts at ALL ZEROS, not at nulls: a slot this derivation
	# does not fill is a zero on the legacy vector, never a hole.
	var vector: Array = []
	vector.resize(BootData.COLLECT_VECTOR_SLOTS)
	for index in range(BootData.COLLECT_VECTOR_SLOTS):
		vector[index] = 0
	vector[COLLECT_EXPERIENCE_SLOT] = _collect_scale(experience, multiplier)
	vector[int(slot)] = _collect_scale(amount, multiplier)
	for index: int in COLLECT_ALWAYS_ZERO_SLOTS:
		vector[index] = 0
	return vector


## A rung-scaled amount, rounded to a whole resource (half-up). The committed
## multipliers are `0.25`, `1`, `2`, and `3`, so every committed product of a
## committed amount is already an integer (`20 x 0.25 = 5`); the rounding
## exists so a future fractional multiplier can never put a float on the
## legacy vector — the Tree's `collect_xp` of 1 at the quarter rung pays `0`.
func _collect_scale(value: int, multiplier: float) -> int:
	var scaled := float(value) * multiplier
	if scaled <= 0.0:
		return 0
	if scaled == floor(scaled):
		return int(scaled)
	return int(scaled + 0.5)


## A stored resource name -> its index in the eight-slot legacy vector, or -1
## for a name the vector has no slot for (never a guessed index).
static func _collect_slot_of(resource: String) -> int:
	match resource:
		"xp":
			return COLLECT_EXPERIENCE_SLOT
		"gold":
			return 2
		"wood":
			return 3
		"oil":
			return 4
		"steel":
			return 5
		"cash":
			return 6
		"mana":
			return 7
	return -1


# --- purchase double (design D9) --------------------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _purchase_failure(code: String, message: String) -> BootData.PurchaseResult:
	return BootData.parse_purchase({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed purchase fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot and placement fixtures' error state is untouched (independent sinks).
func _ensure_purchase_loaded() -> bool:
	if _purchase_loaded:
		return _purchase_error == ""
	_purchase_loaded = true
	var before := _read_json_into(PURCHASE_BEFORE_FIXTURE, {"error": ""})
	var sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(PURCHASE_AFTER_FIXTURE, sink)
	if str(sink["error"]) != "":
		_purchase_error = str(sink["error"])
		return false
	return _init_purchase_state(before)


## Validates the purchase fixture's before-state and builds the in-memory
## save state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double.
func _init_purchase_state(before: Dictionary) -> bool:
	var before_map: Variant = _purchase_first_map(before)
	if before_map == null:
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_purchase_error = "purchase fixture before state lacks playerInfo/privateState"
		return false
	var store: Variant = (before_map as Dictionary).get("store")
	if not (store is Dictionary):
		_purchase_error = "purchase fixture before state carries no store map"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (before_map as Dictionary).get(key)
		if not (value is int or value is float) or float(value) != floor(float(value)):
			_purchase_error = "purchase fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_purchase_error = "purchase fixture before state lacks save fields"
		return false
	# Quantities are counts: every entry must be a non-negative integer, and
	# every key an item id — the same shapes the endpoint's storage mapping
	# and the shared parser accept.
	var typed_store := {}
	for key: Variant in (store as Dictionary):
		var id: Variant = BootData._parse_int(key)
		var quantity: Variant = BootData._parse_int((store as Dictionary)[key])
		if id == null or quantity == null or int(id) < 0 or int(quantity) < 0:
			_purchase_error = "purchase fixture before state has an invalid store entry"
			return false
		typed_store[str(int(id))] = int(quantity)
	_purchase_state = {
		"xp": int((before_map as Dictionary).get("xp")),
		"gold": int((before_map as Dictionary).get("gold")),
		"wood": int((before_map as Dictionary).get("wood")),
		"oil": int((before_map as Dictionary).get("oil")),
		"steel": int((before_map as Dictionary).get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"store": typed_store,
		"bought_units": (bought as Array).duplicate(),
	}
	_purchase_pid = pid
	return true


## `save["maps"][0]` of the purchase fixture, or null (with the error named).
func _purchase_first_map(doc: Dictionary) -> Variant:
	var maps: Variant = doc.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_purchase_error = "purchase fixture before state carries no maps array"
		return null
	if not ((maps as Array)[0] is Dictionary):
		_purchase_error = "purchase fixture before state first map is not an object"
		return null
	return (maps as Array)[0]


## The cash price of an item from its config `costs` attribute, or null when
## the committed config cannot be mapped at all (the endpoint's
## `costs_invalid` -> 500 case). A negative return marks the
## `costs_not_cash` case: the price resolves but is absent, empty, another
## resource, or a mix — this command's price is then not derivable and the
## endpoint answers 400 (design D2).
func _cash_price(item: Dictionary) -> Variant:
	var costs: Variant = _derive_costs(item)
	if costs == null:
		return null
	if (costs as Dictionary).size() != 1 \
			or not (costs as Dictionary).has("cash"):
		return -1
	return int((costs as Dictionary)["cash"])


## The seven stored resource values of the in-memory purchase state.
func _purchase_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_purchase_state[key])
	return resources


## Resource amounts from the config `costs` attribute — the legacy cost
## map (design D4; mirrors `placement_envelope.cost_vector`): keys
## `g/w/o/s/c` onto stored resources, one Dictionary; `{}` for a free item;
## `null` when the committed config cannot be mapped (unknown key or
## non-integer amount — the endpoint fails closed with 500 for the same
## input, and the fake mirrors that code). JSON transports numbers as
## floats on the pinned engine, so integral floats are valid amounts.
func _derive_costs(item: Dictionary) -> Variant:
	var raw: Variant = item.get("costs")
	if raw == null:
		return {}
	var source: Variant = raw
	if source is String:
		if str(source) == "":
			return {}
		source = JSON.parse_string(str(source))
		if source == null:
			return null
	if not (source is Dictionary):
		return null
	var costs := {}
	for key: Variant in source:
		var resource: Variant = COST_RESOURCES.get(str(key))
		if resource == null:
			return null
		var amount: Variant = source[key]
		if amount is float and float(amount) != floor(float(amount)):
			return null
		if not (amount is int or amount is float):
			return null
		costs[str(resource)] = int(amount)
	return costs


## Legacy `engine.map_add_item` attr rules for player team 1: `si` when
## `properties.friend_assistable > 0` (friends assist while it builds) and
## `nc` when `clicks_to_build > 0` (neighbor clicks). A non-empty
## `properties` value that is not valid JSON fails closed (`null`) — the
## legacy dispatcher raises on the same input and the endpoint answers
## 500; the committed config carries only valid JSON objects or "".
func _entry_attr(item: Dictionary) -> Variant:
	var attr := {}
	var raw: Variant = item.get("properties")
	if raw is String and str(raw) != "":
		var properties: Variant = JSON.parse_string(str(raw))
		if properties == null:
			return null
		if properties is Dictionary:
			var friend: Variant = (properties as Dictionary).get(
				"friend_assistable", 0)
			if int(friend) > 0:
				attr["si"] = []
	var clicks: Variant = item.get("clicks_to_build", 0)
	if int(clicks) > 0:
		attr["nc"] = 0
	return attr


## Smallest positive integer absent from the items map (design D4; mirrors
## `placement_envelope.next_free_slot`). Keys that are not integer strings
## cannot collide with a numeric slot and are ignored.
func _next_free_slot() -> int:
	var used := {}
	for key: Variant in _placement_state["items"]:
		var text := str(key)
		if text.is_valid_int():
			used[int(text)] = true
	var slot := 1
	while used.has(slot):
		slot += 1
	return slot


## The seven stored resource values of the in-memory state.
func _resources_dict() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_placement_state[key])
	return resources


func _read_json(relative: String) -> Dictionary:
	var sink := {"error": ""}
	var doc := _read_json_into(relative, sink)
	if str(sink["error"]) != "":
		_load_error = str(sink["error"])
	return doc


## Shared fixture reader with an independent error sink: the boot,
## placement, and purchase fixtures fail closed under their own error codes
## without poisoning the other surfaces' state.
func _read_json_into(relative: String, sink: Dictionary) -> Dictionary:
	var path := Paths.repo_root().path_join(relative)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		sink["error"] = "cannot read fixture: " + path
		return {}
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	if parser.parse(text) != OK:
		sink["error"] = "fixture is not valid JSON: %s (line %d)" \
			% [path, parser.get_error_line()]
		return {}
	if not (parser.data is Dictionary):
		sink["error"] = "fixture is not a JSON object: " + path
		return {}
	var typed: Dictionary = parser.data
	return typed


# --- dead-hero resurrection double (unit-behaviors design D8) ----------------

## The committed corpus save this double starts from: the **same** committed
## bytes every other double's `before.json` fixture carries (they compare
## byte-identical to it).  It is read, never written.
##
## This is the ONLY double that reads the committed corpus save directly rather
## than a fixture under `tests/fixtures/`, and the reason is the line's own
## named cause (design D4): `resurrectable` is a UNIT-ONLY committed flag and
## the corpus places only buildings, so **no executed-legacy resurrection fixture
## exists** and none was fabricated.  The double therefore has nothing executed
## to reproduce, and it is NEVER a parity oracle — parity against executed legacy
## is owned exclusively by the compat fixture-replay tests.
const BEHAVIOR_CORPUS_SAVE := "tests/saves/fresh-player.json"

## The in-memory ledger the double starts from, mirroring the live phase's
## opt-in `COMPAT_SEED_DEAD_HEROES` seed so the two implementations can be
## compared against each other.  It is a **documented, in-memory** seed of the
## THROWAWAY state the live phase seeds its disposable corpus copy with, never a
## write to any committed save, and it exists because the committed corpus's own
## ledger is present and `{}`.
const BEHAVIOR_SEED := {"1001": 1}

## The committed item id the seed names, and the corpus cell the double's own
## positive path addresses.  Both are read out of the committed bytes at run
## time rather than trusted from this sentence.
const BEHAVIOR_SEED_ITEM_ID := 1001

# --- magic-counter double state (godot-damage) --------------------------------

## The same committed corpus save the behaviour double reads, read through an
## INDEPENDENT sink: this double must not depend on another double's failure state
## or inherit a ledger it never seeded.
const MAGIC_CORPUS_SAVE := "tests/saves/fresh-player.json"

## The captured configuration's magic table. Named here so the lookup names no
## string literal of its own.
const MAGICS_KEY := "magics"

## **Eight** stored resource slots, not the seven `RESOURCE_KEYS` lists. Six live
## on the map, `cash` lives on the player info, and `mana`/`energy` live in private
## state -- and `energy` is stored by no legacy branch at all, which is why the
## seven-slot accessor omits it while the document keeps it. Comparing a subset
## would make the no-price claim weaker than the measurement that established it.
const MAGIC_RESOURCE_KEYS := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana", "energy"]

## Mutable process state for the magic double: the eight resource slots plus the
## ledger under `"ledger"`.
var _magic_state: Dictionary = {}
var _magic_pid := ""
var _magic_error := ""
var _magic_loaded := false

## The ledger the double's projection reports when the state is unresolvable:
## never a substituted entry.
const BEHAVIOR_UNRESOLVABLE := "unresolvable_ledger"


## One revival intent under the **same** contract the live implementation sends:
## the save identity and a cell, and nothing else.
##
## The double is deterministic and in-memory: it reads the committed corpus
## save, resolves the addressed cell against that save's own placement rows,
## derives the revived item id from its **own in-memory ledger**, applies the
## legacy decrement with the **delete-at-zero** rule, and re-places the row at
## the derived key and cell with no occupancy, bounds, type, or terrain check —
## the recorded absence, not an omitted one.  It never reads a wall clock: the
## re-placed row's timestamp is the boot fixture's recorded epoch, exactly as
## every other double stamps its own writes.
##
## Both gates are evaluated in the helper's own order and **no third**: the row
## that stands at the addressed cell must be on player team 1, and the resolved
## ledger entry's own committed `resurrectable` must be greater than zero.  The
## gate is applied to the LEDGER ENTRY's item rather than to the row, because
## the revived row is not on the map — which is why the response reports the
## resolved entry's committed flag beside it.
func resurrect_hero_town(user_id: String, x: int,
		y: int) -> BehaviorFlow.ResurrectResult:
	if user_id.strip_edges() == "":
		return BehaviorFlow.resurrect_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_behavior_loaded():
		return BehaviorFlow.resurrect_failure("fixture_unreadable",
			_behavior_error)
	if user_id != _behavior_pid:
		return BehaviorFlow.resurrect_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var target: Dictionary = _behavior_resolve(x, y)
	if not bool(target.get("ok", false)):
		return BehaviorFlow.resurrect_failure(str(target.get("reason", "")),
			str(target.get("error", "")))
	var map_key := int(target["map_key"])
	var item_id := int(target["item_id"])
	var ledger_before: Dictionary = (_behavior_state["ledger"] as Dictionary) \
		.duplicate(true)
	var derived: Dictionary = UnitBehaviors.expected_ledger(ledger_before, item_id)
	if not bool(derived.get("resolvable", false)):
		return BehaviorFlow.resurrect_failure("invalid_ledger",
			str(derived.get("error", "")))
	var ledger_after: Dictionary = (derived["entries"] as Dictionary) \
		.duplicate(true)
	var rows: Dictionary = (_behavior_state["rows"] as Dictionary).duplicate(true)
	var placement_before: Array = (rows[str(map_key)] as Array).duplicate(true)
	var placement_after: Array = _behavior_replacement(placement_before, item_id)
	rows[str(map_key)] = placement_after
	# Nothing else moves: no balance, no storage, no ledger beyond the derived
	# decrement, and no other row.  A revival moves no resource (design D3).
	_behavior_state["rows"] = rows
	_behavior_state["ledger"] = ledger_after
	# The same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return BehaviorFlow.parse_resurrect({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"map_key": map_key,
		"item_id": item_id,
		"count_before": int(derived["count_before"]),
		"count_after": int(derived["count_after"]),
		"removed": bool(derived["removed"]),
		"cell": [int(x), int(y)],
		"occupant_item_id": int(placement_before[0]),
		"committed_resurrectable": int(target["committed_resurrectable"]),
		"committed_syringes": int(target["committed_syringes"]),
		"gates": UnitBehaviors.gates(),
		"ledger_before": _behavior_ledger_entries(ledger_before),
		"ledger_after": _behavior_ledger_entries(ledger_after),
		"placement_before": placement_before,
		"placement_after": placement_after,
		"syringe": {
			"charged": 0,
			"discarded_argument": 0,
			"echoed": false,
			"committed_syringes_reported_as_content_only":
				int(target["committed_syringes"]),
			"note": UnitBehaviors.SYRINGE_DISCARD_NOTE,
			"rule": UnitBehaviors.NO_SYRINGE_COST,
		},
		"resolution": {
			"rule": "the cell chooses WHERE the revival lands and the ledger "
				+ "chooses WHAT is revived; neither is ever taken from the "
				+ "client",
			"derivation_status": "derived",
		},
		"clicks_to_build": UnitBehaviors.CLICKS_TO_BUILD_BOUNDARY,
		"refusals": (UnitBehaviors.REFUSALS as Array).duplicate(true),
		"no_third_gate": UnitBehaviors.NO_THIRD_GATE,
		"resources": _behavior_resources(),
	})


## The double's own cell resolution and both gates, in the helper's order.  Zero
## rows at the addressed cell is a refusal and more than one is a refusal rather
## than an invented tie-break; an unresolvable or absent ledger is a refusal; and
## a resolved entry whose committed `resurrectable` is absent or not greater than
## zero is a refusal.
func _behavior_resolve(x: int, y: int) -> Dictionary:
	var out := {
		"ok": false,
		"reason": "",
		"error": "",
		"map_key": -1,
		"item_id": -1,
		"committed_resurrectable": 0,
		"committed_syringes": 0,
	}
	if x < 0 or y < 0 or x >= GRID_EXTENT or y >= GRID_EXTENT:
		out["reason"] = "invalid_cell"
		out["error"] = ("the addressed cell (%d, %d) is outside the 0..%d town "
			% [x, y, GRID_EXTENT - 1] + "grid")
		return out
	var rows: Dictionary = _behavior_state["rows"]
	var matches: Array = []
	for key: Variant in rows.keys():
		var row: Variant = rows[key]
		if not (row is Array) or (row as Array).size() != 8:
			continue
		if int((row as Array)[1]) == x and int((row as Array)[2]) == y:
			matches.append(str(key))
	matches.sort_custom(func(one: Variant, two: Variant) -> bool:
		return int(one) < int(two))
	if matches.is_empty():
		out["reason"] = "unresolvable_cell"
		out["error"] = ("no placement row records the cell (%d, %d), so the "
			% [x, y] + "addressed cell resolves to no revival target")
		return out
	if matches.size() > 1:
		out["reason"] = "ambiguous_cell"
		out["error"] = ("%d placement rows record the cell (%d, %d) and the "
			% [matches.size(), x, y]
			+ "legacy contract records no tie-break between them")
		return out
	var map_key := int(matches[0])
	var occupant: Array = rows[str(map_key)]
	# Gate one, in the helper's own order: the row that stands there must be on
	# player team 1 (`engine.py:151`).
	if not UnitBehaviors.passes_team_gate(int(occupant[7])):
		out["reason"] = "not_resurrectable"
		out["error"] = ("map key %d stands on player team %d, not %d: gate one "
			% [map_key, int(occupant[7]), UnitBehaviors.PLAYER_TEAM]
			+ "refuses it (engine.py:151)")
		return out
	var projection: Dictionary = UnitBehaviors.project_ledger(
		_behavior_state["ledger"])
	if not bool(projection.get("ok", false)):
		out["reason"] = "invalid_ledger"
		out["error"] = str(projection.get("error", ""))
		return out
	var entries: Dictionary = UnitBehaviors.ledger_entries(
		_behavior_state["ledger"])
	if entries.is_empty():
		out["reason"] = "unresolvable_ledger_entry"
		out["error"] = ("the player's deadHeroes ledger is EMPTY, so the cell "
			+ "(%d, %d) resolves to nothing to revive" % [x, y])
		return out
	if entries.size() > 1:
		out["reason"] = "ambiguous_ledger"
		out["error"] = ("the ledger holds %d entries and the legacy contract "
			% entries.size()
			+ "records no rule for choosing between them from a cell")
		return out
	var item_id := int(entries.keys()[0])
	var committed: Dictionary = _behavior_item(item_id)
	var flag: Variant = UnitBehaviors.committed_resurrectable(
		committed.get(UnitBehaviors.PROPERTIES_FIELD))
	if not UnitBehaviors.passes_resurrectable_gate(flag):
		out["reason"] = "not_resurrectable"
		out["error"] = ("the resolved ledger entry names item id %d, whose "
			% item_id
			+ "committed resurrectable is absent or not greater than zero: "
			+ "gate two refuses it (engine.py:159,162)")
		return out
	out["ok"] = true
	out["map_key"] = map_key
	out["item_id"] = item_id
	out["committed_resurrectable"] = int(flag)
	out["committed_syringes"] = int(committed.get("syringes", 0))
	return out


## The re-placed row, reproducing `engine.map_add_item`'s own construction
## (`engine.py:8-31`) with **no** occupancy, bounds, type, or terrain check —
## the recorded absence, not an omitted one.  The revived unit's committed
## `clicks_to_build` is 0, so the `{"nc": 0}` counter is **not** seeded, and its
## `friend_assistable` is absent, so `si` is not either; the attribute bag stays
## empty, which is a measurement rather than an assumption.
func _behavior_replacement(before: Array, item_id: int) -> Array:
	return [
		item_id,
		int(before[1]),
		int(before[2]),
		# Deterministic: the boot fixture's recorded epoch, never the clock.
		_fixture_server_time(),
		int(before[4]),
		(before[5] as Array).duplicate(true),
		{},
		UnitBehaviors.PLAYER_TEAM,
	]


## The projected ledger as the response's `[{item_id, count}]` entries, sorted
## by item id so the bytes never depend on a dictionary's iteration order.
func _behavior_ledger_entries(ledger: Dictionary) -> Array:
	var out: Array = []
	var keys: Array = ledger.keys()
	keys.sort_custom(func(one: Variant, two: Variant) -> bool:
		return int(one) < int(two))
	for key: Variant in keys:
		out.append({"item_id": str(key), "count": int(ledger[key])})
	return out


## One committed item id's raw configuration row, read out of the SAME captured
## config payload the placement and purchase doubles already index — so the
## double reads `properties` in exactly the representation `push_dead_unit`
## reads it in (a raw JSON **string**), and the two implementations cannot
## disagree about a gate.
func _behavior_item(item_id: int) -> Dictionary:
	var items: Variant = _config_payload.get("items")
	if not (items is Array):
		return {}
	for row: Variant in items as Array:
		if not (row is Dictionary):
			continue
		var candidate: Dictionary = row
		if str(_id_text(candidate.get("id"))) != str(item_id):
			continue
		return candidate.duplicate(true)
	return {}


## One committed item id as the text the committed row records it by: the
## captured configuration carries `id` as a STRING, so a numeric form is
## normalised rather than compared against a float.
func _id_text(value: Variant) -> String:
	if value is String:
		return str(value).strip_edges()
	var parsed: Variant = BootData._parse_int(value)
	if parsed == null:
		return str(value)
	return str(int(parsed))


## The seven stored resource values of the in-memory behaviour state, reported
## verbatim as the response's authoritative `resources`.  A revival moves none of
## them, so these are the values the intent started from — the strongest form of
## the "nothing moved" proof the endpoint requires (design D3).
func _behavior_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_behavior_state[key])
	return resources


## Loads the committed corpus save into mutable process state (once), applying
## the documented in-memory ledger seed.  Structural failures are named with the
## offending field; every other double's error state is untouched (independent
## sinks).
func _ensure_behavior_loaded() -> bool:
	if _behavior_loaded:
		return _behavior_error == ""
	_behavior_loaded = true
	# The captured config payload must be loaded first because gate two reads
	# the committed `properties` out of it — independently of the other
	# doubles, so this double's failure cannot hide behind another's.
	if not _ensure_loaded():
		_behavior_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(BEHAVIOR_CORPUS_SAVE, sink)
	if str(sink["error"]) != "":
		_behavior_error = str(sink["error"])
		return false
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_behavior_error = "the committed corpus save carries no first map"
		return false
	var first_map: Variant = (maps as Array)[0]
	if not (first_map is Dictionary):
		_behavior_error = "the committed corpus save's first map is not an object"
		return false
	var rows: Variant = (first_map as Dictionary).get("items")
	if not (rows is Dictionary) or (rows as Dictionary).is_empty():
		_behavior_error = "the committed corpus save carries no placement map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_behavior_error = "the committed corpus save lacks playerInfo/privateState"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_behavior_error = "the committed corpus save lacks save fields"
		return false
	var resources := {}
	for name: String in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (first_map as Dictionary).get(name)
		if value == null or int(value) < 0:
			_behavior_error = "the committed corpus save lacks map %s" % name
			return false
		resources[name] = int(value)
	resources["cash"] = int(cash)
	resources["mana"] = int(mana)
	var state := resources
	state["rows"] = (rows as Dictionary).duplicate(true)
	# The committed corpus ledger is present and `{}`; the double's documented
	# in-memory seed replaces it for the duration of this process only, and no
	# committed byte is written.
	state["ledger"] = BEHAVIOR_SEED.duplicate(true)
	_behavior_state = state
	_behavior_pid = str(pid)
	return true


# --- combat double (godot-combat-actions design D8) ----------------------------


## The recorded `response.body` files of the committed combat fixture are the
## **legacy** `{"result": "success"}` shape, so no captured answer can seed this
## double —" exactly the recorded absence the stored-placement line also carries.
## The double is therefore built the way the revival double is: from the
## committed corpus save, the shared projection in `combat_flow.gd`, and the
## shared ledger increment in `unit_behaviors.gd`, with no clock and no server.
##
## It is NEVER a parity oracle.  Parity against executed legacy is owned
## exclusively by `apps/compat-api/tests/test_combat_parity.py`.
##
## The committed corpus places **zero** unit rows, so a `resolve` against it
## answers `no_eligible_row` -- which is the honest answer, not a limitation
## worked around.  A positive `resolve` is unreachable from the committed corpus
## for the same reason `combat-live` cannot prove one; the hermetic suite proves
## it over crafted in-memory input instead.
func combat_town(user_id: String, action: Variant,
		addressing: Variant) -> CombatFlow.CombatResult:
	if user_id.strip_edges() == "":
		return CombatFlow.combat_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_behavior_loaded():
		return CombatFlow.combat_failure("fixture_unreadable", _behavior_error)
	if user_id != _behavior_pid:
		return CombatFlow.combat_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# The design-D2 refusal and the addressing typing both resolve HERE, before
	# the double reads a single placement row —" the same order the live service
	# uses, so a request that names a destruction count never even reaches the
	# player's state in either implementation.
	var intent := CombatFlow.build_intent(user_id, action, addressing)
	if not bool(intent.get("ok", false)):
		return CombatFlow.combat_failure(str(intent.get("reason", "")),
			str(intent.get("error", "")))
	var rows: Dictionary = (_behavior_state["rows"] as Dictionary).duplicate(true)
	var ledger_before: Dictionary = (_behavior_state["ledger"] as Dictionary) \
		.duplicate(true)
	var projection: Dictionary = CombatFlow.project_combat(
		rows, ledger_before, str(action), addressing,
		func(item_id: int) -> Variant: return _behavior_item(item_id))
	if not bool(projection.get("ok", false)):
		return CombatFlow.combat_failure(str(projection.get("reason", "")),
			str(projection.get("error", "")))

	# --- the write step: exactly one row, and only the derived one ------------
	# `kill_iid` is a proven no-op, so it carries NO eligible set and NO derived
	# key at all; the emptiness is the result, not a missing value.
	var eligible: Dictionary = {}
	if projection.get("eligible") is Dictionary:
		eligible = projection.get("eligible")
	var derived_key := str(eligible.get("addressed_key", ""))
	var destruction := int(projection.get("destruction", 0))
	var rows_before := rows.size()
	var changed: Array = []
	if destruction == 1:
		rows.erase(derived_key)
		changed.append("/maps/0/items/%s" % derived_key)
	var rows_after := rows.size()

	# --- the ledger, by `engine.push_dead_unit`'s own two arms ---------------
	var ledger_after: Dictionary = ledger_before.duplicate(true)
	var derived_ledger: Dictionary = projection.get("ledger_after") as Dictionary
	if bool(projection.get("ledger_written", false)):
		var item_text := str(derived_ledger.get("item_id"))
		if bool(derived_ledger.get("present_before", false)):
			# `+=` on a present key leaves its recorded position alone.
			ledger_after[item_text] = int(ledger_after.get(item_text, 0)) \
				+ int(derived_ledger.get("count_after", 1))
		else:
			# `= 1` on an absent key appends (engine.py:164-167).
			ledger_after[item_text] = 1
		changed.append("/privateState/deadHeroes/%s" % item_text)

	_behavior_state["rows"] = rows
	_behavior_state["ledger"] = ledger_after

	# Nothing else moves: the branch resolves no resource and the derived vector
	# is the neutral all-zero one, so the reported set is what the intent started
	# from —" the strongest form of the "no honour, no reward, no cost" proof.
	return CombatFlow.parse_combat(CombatFlow.build_response(
		action,
		addressing,
		projection,
		{
			"ledger_after": ledger_after,
			"rows_before": rows_before,
			"rows_after": rows_after,
			"changed": changed,
			"resources": _behavior_resources(),
			# Deterministic: the boot fixture's recorded epoch, never the clock.
			"server_time": _fixture_server_time(),
			"game_version": str(_save_list_doc.get("game_version", "")),
		}))


# --- magic-counter double (godot-damage) --------------------------------------


## One magic-counter intent under the **same** contract the live implementation
## sends: the save identity, a CLOSED action, and the magic identity -- nothing
## else. No counter value, no delta, no cap, no price, and no damage magnitude is
## accepted or expressible, because `MagicFlow.build_magic_intent()` assembles
## exactly `MagicFlow.BODY_KEY_COUNT` keys.
##
## The double is deterministic and in-memory. It reads the committed corpus save
## (`tests/saves/fresh-player.json`, whose `privateState.magics` is `{}`), derives
## the transition from the shared projection in `magic_flow.gd`, and applies the
## **recorded legacy arm** to its own ledger rather than the derived transition --
## because that is what the unchanged dispatcher does, and a double that stored
## the derived value would report a state the oracle never produced.
##
## It is NEVER a parity oracle. Parity against executed legacy is owned
## exclusively by `apps/compat-api/tests/test_magic_*.py`.
##
## ## The first request reproduces the recorded divergence, deliberately
##
## With an **absent** key the unchanged branch takes its `else` arm and writes the
## key at **zero**, while the derived transition reads absent as zero charges and
## increments it. So the first answer reports `matches_derived` **false**, and
## that is the expected result rather than a limitation worked around.
func magic_town(user_id: String, action: Variant,
		magic_id: Variant) -> MagicFlow.MagicResult:
	if user_id.strip_edges() == "":
		return MagicFlow.magic_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_magic_loaded():
		return MagicFlow.magic_failure("fixture_unreadable", _magic_error)
	if user_id != _magic_pid:
		return MagicFlow.magic_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# The identity typing and the closed action both resolve HERE, before the
	# double reads a single ledger key -- the same order the live service uses,
	# so a request naming no spell never reaches the player's state in either
	# implementation.
	var intent := MagicFlow.build_magic_intent(user_id, action, magic_id)
	if not bool(intent.get("ok", false)):
		return MagicFlow.magic_failure(str(intent.get("reason", "")),
			str(intent.get("error", "")))
	var ledger: Dictionary = (_magic_state["ledger"] as Dictionary) \
		.duplicate(true)
	var projection: Dictionary = MagicFlow.project_magic(
		ledger, action, magic_id,
		func(value: int) -> Variant: return _magic_entry(value))
	if not bool(projection.get("ok", false)):
		return MagicFlow.magic_failure(str(projection.get("reason", "")),
			str(projection.get("error", "")))

	# --- the write step: exactly one ledger entry, by the RECORDED arm --------
	var key := str(projection.get("ledger_key", ""))
	var recorded := MagicFlow.legacy_recorded_after(action,
		int(projection.get("counter_before", 0)),
		bool(projection.get("counter_present", false)),
		int(projection.get("cap", MagicFlow.COUNTER_CAP)))
	if not bool(recorded.get("ok", false)):
		return MagicFlow.magic_failure(str(recorded.get("reason", "")),
			str(recorded.get("error", "")))
	# A present key keeps its recorded position; a created key is appended, which
	# is what `+=` and a bare assignment each do to the document.
	ledger[key] = int(recorded.get("after", 0))
	_magic_state["ledger"] = ledger
	var changed: Array = ["/privateState/magics/%s" % key]

	# Nothing else moves: the branch resolves no resource, so the reported set is
	# what the intent started from -- the strongest form of the no-price proof.
	return MagicFlow.parse_magic(MagicFlow.build_magic_response(
		action, magic_id, projection,
		{
			"ledger_after": ledger,
			"changed": changed,
			"resources": _magic_resources(),
			# Deterministic: the boot fixture's recorded epoch, never the clock.
			"server_time": _fixture_server_time(),
			"game_version": str(_save_list_doc.get("game_version", "")),
		}))


## One committed magic from the captured configuration, or null.
##
## The captured row's `id` is normalised through `_id_text()` rather than
## compared as a number, because the committed package records every `legacy_id`
## as a **string** while this fixture's raw capture holds an integer -- and a
## comparison that happened to work on one form would be a second, unrelated
## assumption rather than a rule.
func _magic_entry(magic_id: int) -> Variant:
	var table: Variant = _config_payload.get(MAGICS_KEY)
	if not (table is Array):
		return null
	for row: Variant in table as Array:
		if not (row is Dictionary):
			continue
		var candidate: Dictionary = row
		if _id_text(candidate.get("id")) != str(magic_id):
			continue
		return candidate.duplicate(true)
	return null


## All **eight** stored resource slots of the in-memory magic state, reported
## verbatim. Eight rather than seven, because `privateState['energy']` is stored
## by no legacy branch and so is absent from the seven-slot accessor while present
## in the document; the no-price proof compares every slot.
func _magic_resources() -> Dictionary:
	var out := {}
	for key: String in MAGIC_RESOURCE_KEYS:
		out[key] = int(_magic_state[key])
	return out


## Loads the committed corpus save's magic state into mutable process state
## (once).  An **independent sink** from the behaviour double, so this double's
## failure cannot hide behind another's -- and a failure in either cannot be
## mistaken for a clean ledger.
func _ensure_magic_loaded() -> bool:
	if _magic_loaded:
		return _magic_error == ""
	_magic_loaded = true
	if not _ensure_loaded():
		_magic_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(MAGIC_CORPUS_SAVE, sink)
	if str(sink["error"]) != "":
		_magic_error = str(sink["error"])
		return false
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_magic_error = "the committed corpus save carries no first map"
		return false
	var first_map: Variant = (maps as Array)[0]
	if not (first_map is Dictionary):
		_magic_error = "the committed corpus save's first map is not an object"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_magic_error = "the committed corpus save lacks playerInfo/privateState"
		return false
	var map_body: Dictionary = first_map
	var player_body: Dictionary = info
	var private_body: Dictionary = priv
	# The ledger must be readable BEFORE anything is seeded from it: an
	# unreadable ledger is the service's `invalid_ledger` refusal, and defaulting
	# it here would turn a server-side precondition into a silent create.
	var ledger_projection := MagicFlow.project_ledger(
		private_body.get(MagicFlow.LEDGER_KEY))
	if not bool(ledger_projection.get("ok", false)):
		_magic_error = str(ledger_projection.get("error", ""))
		return false
	var missing: Array = []
	for key: String in MAGIC_RESOURCE_KEYS:
		var source: Variant = map_body
		if key == "cash":
			source = player_body
		elif key == "mana" or key == "energy":
			source = private_body
		if not source.has(key):
			missing.append(key)
			continue
		_magic_state[key] = int(source[key])
	if not missing.is_empty():
		_magic_error = ("the committed corpus save lacks the stored resource "
			+ str(missing))
		return false
	_magic_state["ledger"] = \
		(private_body[MagicFlow.LEDGER_KEY] as Dictionary).duplicate(true)
	_magic_pid = str(player_body.get("pid", ""))
	if _magic_pid == "":
		_magic_error = "the committed corpus save records no playerInfo pid"
		return false
	return true


# --- research double (godot-research design D8) ------------------------------


## One research-track intent under the **same** contract the live implementation
## sends: the save identity, a CLOSED action, and the research track — nothing
## else.  No counter value, no research instant, and no cash amount is accepted
## or expressible.
##
## The double is deterministic and in-memory: it reads the recorded fixture's
## FIRST before-state (the committed fresh-player corpus, whose three counters
## are each `[0, 0]`), derives each branch's effect from
## `ResearchFlow.BRANCHES` — the same record the service applies — and stamps
## the research instant with a **fixture** value rather than a wall clock, so
## every run is byte-identical.  The recording is eight steps of ONE transaction
## and every step after the first starts from the previous step's after-state,
## so the double derives each step rather than replaying the file; the executed
## parity against legacy is owned exclusively by the compat fixture-replay tests
## and this double is never a parity oracle.
##
## **No stored resource moves** (design D3): the derived vector is neutral, so
## the seven balances are the same values the intent started from.  The double
## also moves **nothing else** — no placement, no storage, no ledger.
##
## The refusals mirror the endpoint's own, in the endpoint's order: the
## save-identity codes first, then ``invalid_action`` for anything outside the
## closed four-action set, then ``invalid_track`` for a track the two-entry
## vector cannot address, and ``unresolvable_research_state`` for a state whose
## counters are absent, not lists, the wrong length, non-integer, or negative.
func advance_research_town(user_id: String, action: String,
		track: int) -> ResearchFlow.ResearchResult:
	if user_id.strip_edges() == "":
		return ResearchFlow.result_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_research_loaded():
		return ResearchFlow.result_failure("fixture_unreadable",
			_research_error)
	if user_id != _research_pid:
		return ResearchFlow.result_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if not ResearchFlow.is_action(action):
		return ResearchFlow.result_failure("invalid_action",
			"action must be one of %s" % ", ".join(
				PackedStringArray(ResearchFlow.ACTIONS)))
	if not ResearchFlow.is_track(track):
		return ResearchFlow.result_failure("invalid_track",
			"track must be an integer in 0..%d, got %d"
				% [ResearchFlow.TRACK_COUNT - 1, track])
	var before: Dictionary = _research_counters()
	var effect := _research_effect(before, action, track)
	if not bool(effect.get("ok", false)):
		return ResearchFlow.result_failure(
			str(effect.get("code", "internal_error")), str(effect.get("error", "")))
	var after: Dictionary = (before as Dictionary).duplicate(true)
	for key: String in (effect["written"] as Array):
		after[key] = (effect["counters"] as Dictionary)[key]
	_research_state["counters"] = after
	# The same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D8).
	return ResearchFlow.parse_result({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"action": action,
		"track": int(track),
		"command": str(effect["command"]),
		"derived": {
			"step": int((effect["counters"] as Dictionary)[ResearchFlow.KEY_STEP][
				int(track)]),
			"item": int((effect["counters"] as Dictionary)[ResearchFlow.KEY_ITEM][
				int(track)]),
			# The step branch stamps the wall clock, so its value is NOT
			# derivable and the typed result carries a null there exactly as the
			# service does.
			"instant": (null if bool(effect["stamps_instant"])
				else int((effect["counters"] as Dictionary)[
					ResearchFlow.KEY_INSTANT][int(track)])),
			"stamps_instant": bool(effect["stamps_instant"]),
			"paired_reset": bool(effect["paired_reset"]),
			"written": (effect["written"] as Array).duplicate(),
			"untouched_counters": (effect["untouched"] as Array).duplicate(),
		},
		"previous": _research_block(before),
		"counters": _research_counters_block(after),
		"research": _research_block(after),
		"tracks": _research_track_ids(),
		"tracks_source": (ResearchFlow.TRACKS as Array).duplicate(true),
		"cash_charged": 0,
		"cash_argument_ignored": true,
		"price_computed": false,
		"fast_forward_offered": false,
		"resources": _research_resources(),
	})


## The recorded legacy effect of one research branch on one track — DERIVED from
## `ResearchFlow.BRANCHES` and the double's own before-state, never read from a
## response.  Returns ``{ok, error, code, command, counters, written,
## untouched, stamps_instant, paired_reset}``.
##
## The step and item values are exact; the INSTANT is a **fixture** value because
## the branch stamps the wall clock and the double never reads one (design D8),
## which keeps every run byte-identical.  The derived record also names every
## counter the branch does **NOT** write, so nothing else in the vector can be
## touched by construction.
func _research_effect(before: Dictionary, action: String,
		track: int) -> Dictionary:
	var index := int(track)
	var record: Dictionary = ResearchFlow.BRANCHES[_research_branch_index(action)]
	var written: Array = (record["counters_written"] as Array).duplicate()
	var step := int((before[ResearchFlow.KEY_STEP] as Array)[index])
	var item := int((before[ResearchFlow.KEY_ITEM] as Array)[index])
	var instant := int((before[ResearchFlow.KEY_INSTANT] as Array)[index])
	var stamps_instant := bool(record["stamps_instant"])
	var expected: Array = []
	# The effect is keyed on the recorded COMMAND, not on the action name, and
	# every write is cross-checked against the record's own `counters_written` —
	# so a fifth branch or a changed effect fails closed here instead of making
	# the double write something the service would not.
	match str(record["command"]):
		ResearchFlow.STEP_COMMAND:
			step = step + 1
			expected = [ResearchFlow.KEY_STEP, ResearchFlow.KEY_INSTANT]
		ResearchFlow.CASH_COMMAND:
			instant = 0
			expected = [ResearchFlow.KEY_INSTANT]
		ResearchFlow.ITEM_COMMAND:
			item = item + 1
			step = 0
			instant = 0
			expected = [ResearchFlow.KEY_ITEM, ResearchFlow.KEY_STEP,
				ResearchFlow.KEY_INSTANT]
		ResearchFlow.RESET_COMMAND:
			step = 0
			item = 0
			instant = 0
			expected = [ResearchFlow.KEY_ITEM, ResearchFlow.KEY_STEP,
				ResearchFlow.KEY_INSTANT]
		_:
			return {
				"ok": false,
				"code": "internal_error",
				"error": "the research double cannot apply the branch record for "
					% ("action '%s': a fifth branch reached it and this contract "
						% action + "refuses to guess"),
			}
	if expected != written:
		return {
			"ok": false,
			"code": "internal_error",
			"error": "the research double wrote %r, which the branch record for "
				% written + "'%s' does not" % str(record["command"]),
		}
	if stamps_instant:
		instant = _research_stamp_value()
	var counters: Dictionary = {
		ResearchFlow.KEY_STEP: (before[ResearchFlow.KEY_STEP] as Array).duplicate(),
		ResearchFlow.KEY_ITEM: (before[ResearchFlow.KEY_ITEM] as Array).duplicate(),
		ResearchFlow.KEY_INSTANT: (before[ResearchFlow.KEY_INSTANT] as Array)
			.duplicate(),
	}
	(counters[ResearchFlow.KEY_STEP] as Array)[index] = step
	(counters[ResearchFlow.KEY_ITEM] as Array)[index] = item
	(counters[ResearchFlow.KEY_INSTANT] as Array)[index] = instant
	var untouched: Array = []
	for key: String in ResearchFlow.COUNTERS:
		if not written.has(key):
			untouched.append(key)
	return {
		"ok": true,
		"error": "",
		"code": "",
		"command": str(record["command"]),
		"counters": counters,
		"written": written,
		"untouched": untouched,
		"stamps_instant": stamps_instant,
		"paired_reset": bool(record["paired_reset"]),
	}


## The index of one closed action inside the recorded branch table, or -1.
func _research_branch_index(action: String) -> int:
	var index := 0
	for record: Variant in ResearchFlow.BRANCHES:
		if str((record as Dictionary)["action"]) == action:
			return index
		index += 1
	return -1


## The instant a research stamp takes in the double.  The legacy branch stamps
## ``timestamp_now()``, which the double deliberately never reads: it reuses the
## instant the committed executed capture recorded, so an offline run is
## deterministic and byte-identical.  No elapsed-time rule is computed from it
## either way — the legacy server has none (design D1/D7).
func _research_stamp_value() -> int:
	return int(_research_state.get("stamp", 0))


## The double's own counters, as a fresh copy so a caller cannot mutate them.
func _research_counters() -> Dictionary:
	var out: Dictionary = {}
	for key: String in ResearchFlow.COUNTERS:
		out[key] = ((_research_state["counters"] as Dictionary)[key] as Array) \
			.duplicate()
	return out


## The three committed counter vectors, in the shape the response carries them.
func _research_counters_block(counters: Dictionary) -> Dictionary:
	var out: Dictionary = {"counters": {}}
	for key: String in ResearchFlow.COUNTERS:
		(out["counters"] as Dictionary)[key] = (counters[key] as Array).duplicate()
	return out


## The service's `research` projection for one vector: both tracks verbatim and
## an **empty** ``derived`` block, which is the machine-readable form of "nothing
## is computed from these counters".
func _research_block(counters: Dictionary) -> Dictionary:
	var rows: Array = []
	for index in range(ResearchFlow.TRACK_COUNT):
		rows.append({
			"track": index,
			"step": int((counters[ResearchFlow.KEY_STEP] as Array)[index]),
			"item": int((counters[ResearchFlow.KEY_ITEM] as Array)[index]),
			"instant": int((counters[ResearchFlow.KEY_INSTANT] as Array)[index]),
		})
	return {
		"track_count": ResearchFlow.TRACK_COUNT,
		"counters": _research_counters_block(counters)["counters"],
		"tracks": rows,
		"verbatim": true,
		"derived": {},
		"tracks_source": (ResearchFlow.TRACKS as Array).duplicate(true),
		"tracking_note": ResearchFlow.TRACK_RECORD_NOTE,
	}


## Both committed track indices, in committed order.
func _research_track_ids() -> Array:
	var out: Array = []
	for record: Variant in ResearchFlow.TRACKS:
		out.append(int((record as Dictionary)["track"]))
	return out


## The seven stored resource values of the in-memory research state, reported
## verbatim as the response's authoritative ``resources``.  A research action
## moves none of them, so these are the same values the intent started from —
## the strongest form of the "nothing moved" proof the endpoint requires
## (design D3).
func _research_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_research_state[key])
	return resources


## Loads the research fixture's first before-state into mutable process state
## (once), validating the committed research vector and the seven balances.
## Structural failures are named with the offending field; every other double's
## error state is untouched (independent sinks).
func _ensure_research_loaded() -> bool:
	if _research_loaded:
		return _research_error == ""
	_research_loaded = true
	# The boot fixtures must be loaded first: the double's response reports the
	# captured `game_version` and `server_time` from them, so without this the
	# double would answer with an empty version and a ZERO server time whenever
	# it is reached before any boot read.  Done independently of the other
	# doubles, so this double's failure cannot hide behind another's.
	if not _ensure_loaded():
		_research_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(RESEARCH_BEFORE_FIXTURE, sink)
	if str(sink["error"]) != "":
		_research_error = str(sink["error"])
		return false
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_research_error = "the research fixture before state carries no maps array"
		return false
	var first_map: Variant = (maps as Array)[0]
	if not (first_map is Dictionary):
		_research_error = ("the research fixture before state's first map is not "
			+ "an object")
		return false
	var items: Variant = (first_map as Dictionary).get("items")
	if not (items is Dictionary) or (items as Dictionary).is_empty():
		_research_error = "the research fixture before state carries no placement map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_research_error = ("the research fixture before state lacks "
			+ "playerInfo/privateState")
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_research_error = "the research fixture before state lacks save fields"
		return false
	var resources := {}
	for name: String in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (first_map as Dictionary).get(name)
		if value == null or int(value) < 0:
			_research_error = "the research fixture before state lacks map %s" % name
			return false
		resources[name] = int(value)
	resources["cash"] = int(cash)
	resources["mana"] = int(mana)
	var counters := {}
	for key: String in ResearchFlow.COUNTERS:
		var entries: Variant = (priv as Dictionary).get(key)
		if not (entries is Array) or (entries as Array).size() \
				!= ResearchFlow.TRACK_COUNT:
			_research_error = ("the research fixture before state's %s is not a "
				% key + "%d-entry vector") % ResearchFlow.TRACK_COUNT
			return false
		var row: Array = []
		for entry: Variant in entries as Array:
			var number: Variant = BootData._parse_int(entry)
			if number == null or int(number) < 0:
				_research_error = ("the research fixture before state's %s holds a "
					% key + "non-integer or negative entry")
				return false
			row.append(int(number))
		counters[key] = row
	# The committed corpus holds every research counter at its initial value, and
	# the double validates that rather than trusting this sentence: a capture that
	# is not the recorded transaction fails closed here.
	for key: String in ResearchFlow.COUNTERS:
		if (counters[key] as Array) != (ResearchFlow.CORPUS_VECTOR[key] as Array):
			_research_error = ("the research fixture before state's %s is %r, not "
				% [key, counters[key]] + "the committed %r"
				% (ResearchFlow.CORPUS_VECTOR[key]))
			return false
		# The placement map is read and never written: a research action moves no
		# placement row, so the double holds no copy of one at all.
	# The recorded wall-clock stamp the executed capture left behind, read from
	# its manifest so the double never reads a clock.
	_research_stamp = _research_recorded_stamp()
	var state := resources
	state["counters"] = counters
	state["stamp"] = _research_stamp
	_research_state = state
	_research_pid = str(pid)
	return true


## The research instant the committed executed capture recorded, read out of the
## recorded step's after-state — never pinned as a literal, so a re-capture moves
## the double with it.  `0` means the capture recorded none, which the branch
## always does for the step track.
func _research_recorded_stamp() -> int:
	var sink := {"error": ""}
	var after := _read_json_into(
		RESEARCH_BEFORE_FIXTURE.replace("/before.json", "/after.json"), sink)
	if str(sink["error"]) != "":
		return 0
	var priv: Variant = after.get("privateState")
	if not (priv is Dictionary):
		return 0
	var entries: Variant = (priv as Dictionary).get(ResearchFlow.KEY_INSTANT)
	if not (entries is Array) or (entries as Array).is_empty():
		return 0
	var number: Variant = BootData._parse_int((entries as Array)[0])
	if number == null or int(number) <= 0:
		return 0
	return int(number)

# --- quest double (godot-quests design D1/D2) ------------------------------


## One quest intent under the **same** contract the live implementation sends: the
## save identity, a CLOSED action, and the branch's own addressing under one fixed
## key — nothing else. No progress pair, no value, no difficulty, no outcome, and
## no unit list is accepted or expressible.
##
## The double is deterministic and in-memory: it reads the recorded fixture's
## FIRST before-state (the committed fresh-player corpus, whose quest state is at
## its initial value throughout) and derives each branch's effect from
## `QuestFlow.BRANCHES` — the same record the service applies — stamping the two
## wall-clock fields with the **recorded** instants the capture left behind rather
## than reading a clock, so every offline run is byte-identical. The recording is
## six steps of ONE transaction and every step after the first starts from the
## previous step's after-state, so the double derives each step rather than
## replaying the file; the executed parity against legacy is owned exclusively by
## the compat fixture-replay tests and this double is never a parity oracle.
##
## **No stored resource moves** (design D6): the derived vector is neutral, so the
## seven balances are the same values the intent started from. The double also
## moves **nothing else** — no placement, no storage, no dead-hero ledger, because
## the `end_quest` destruction count is REFUSED and the derived blob's unit list is
## empty (design D2).
##
## The refusals mirror the endpoint's own, in the endpoint's order: the
## save-identity codes first, then ``invalid_action`` for anything outside the
## closed six-action set, then the per-action addressing code, and
## ``unresolvable_quest_state`` for a state the projection cannot read.
func advance_quest_town(user_id: String, action: String,
		addressing: Variant) -> QuestFlow.QuestResult:
	if user_id.strip_edges() == "":
		return QuestFlow.result_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_quest_loaded():
		return QuestFlow.result_failure("fixture_unreadable", _quest_error)
	if user_id != _quest_pid:
		return QuestFlow.result_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if not QuestFlow.is_action(action):
		return QuestFlow.result_failure("invalid_action",
			"action must be one of %s" % ", ".join(
				PackedStringArray(QuestFlow.ACTIONS)))
	var reason := QuestFlow.addressing_reason(action, addressing)
	if reason != "":
		return QuestFlow.result_failure(reason,
			"the %s is not addressable: got %s" % [
				str((QuestFlow.ACTION_ADDRESSING as Dictionary)[str(action)]),
				addressing])
	if str(action) == QuestFlow.ACTION_SET_QUEST_VAR \
			and str(addressing) == QuestFlow.QUEST_VAR_IGNORED_KEY:
		return QuestFlow.result_failure("ignored_quest_var_key",
			("the legacy set_quest_var branch explicitly IGNORES %s "
				% QuestFlow.QUEST_VAR_IGNORED_KEY)
			+ "(command.py:91-95), so it is refused rather than persisted")
	var before := _quest_fields()
	var effect := _quest_effect(before, str(action), addressing)
	if not bool(effect.get("ok", false)):
		return QuestFlow.result_failure(
			str(effect.get("code", "internal_error")), str(effect.get("error", "")))
	_quest_state["fields"] = (effect["fields"] as Dictionary).duplicate(true)
	var after := _quest_fields()
	# The same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D2).
	return QuestFlow.parse_result({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"action": str(action),
		"addressing": addressing,
		"addressing_kind": str((QuestFlow.ACTION_ADDRESSING as Dictionary)[
			str(action)]),
		"command": str(effect["command"]),
		"derived": {
			"written": (effect["written"] as Array).duplicate(),
			"untouched": (effect["untouched"] as Array).duplicate(),
			"mutates": bool(effect["mutates"]),
			"stamps_instant": bool(effect["stamps_instant"]),
			"stamps_chapter": bool(effect["stamps_chapter"]),
			"progress_pair": (QuestFlow.DERIVED_PROGRESS as Array).duplicate(),
			"quest_var_value": QuestFlow.DERIVED_QUEST_VALUE,
			"difficulty": QuestFlow.DERIVED_DIFFICULTY,
			"wrapped_mission": (effect["wrapped_mission"] as Variant),
		},
		"previous": _quest_block(before),
		"quests": _quest_block(after),
		"quest_state": after.duplicate(true),
		"branches": (QuestFlow.BRANCHES as Array).duplicate(true),
		"branch_count": QuestFlow.BRANCH_COUNT,
		"writers": (QuestFlow.WRITERS as Array).duplicate(true),
		"writer_count": QuestFlow.WRITER_COUNT,
		"fast_forward_offered": false,
		"reward_paid": QuestFlow.REWARD_PAID,
		"reward_derived_from_content": false,
		"unlocked_quest_index": after[QuestFlow.KEY_UNLOCKED_INDEX],
		"unlocked_quest_index_written": false,
		"destruction": {
			"status": "REFUSED",
			"legacy_status": "DIVERGENCE, NOT PARITY",
			"client_supplied_units_ignored": true,
			"derived_units": 0,
			"placed_rows_before": QuestFlow.CORPUS_PLACEMENTS,
			"placed_rows_after": QuestFlow.CORPUS_PLACEMENTS,
			"placed_rows_byte_identical": true,
			"ledger_door": QuestFlow.LEDGER_DOOR.duplicate(true),
			"note": str((QuestFlow.REFUSED_DESTRUCTION as Dictionary)["reason"]),
		},
		# The blob belongs to the end_quest branch alone; the service sends None
		# for every other action and the typed parser refuses a blob on one.
		"end_quest_blob": _quest_blob(str(action), addressing)
			if str(action) == QuestFlow.ACTION_END_QUEST else null,
		"ignored_client_keys": (QuestFlow.INTENT_IGNORED_KEYS as Array).duplicate(),
		"persisted_client_values": [],
		"refusals": _quest_refusal_records(),
		"refused_destruction": QuestFlow.REFUSED_DESTRUCTION.duplicate(true),
		"migration": QuestFlow.MIGRATION.duplicate(true),
		"content_note": QuestFlow.CONTENT_RECORD_NOTE,
		"resources": _quest_resources(),
	})


## The recorded legacy effect of one quest branch — DERIVED from
## `QuestFlow.BRANCHES` and the double's own before-state, never read from a
## response. Returns ``{ok, error, code, command, fields, written, untouched,
## mutates, stamps_instant, stamps_chapter, wrapped_mission}``.
##
## The two wall-clock fields take a **recorded** instant the double reads out of
## the committed capture rather than a clock, so every offline run is
## byte-identical. The derived record also names every field the branch does
## **NOT** write, so nothing else in the state can be touched by construction, and
## the two TYPE facts are reproduced exactly: the mission identifier is written as
## a **string** (design D8) and the quest-variable map is self-healed from the
## corpus's recorded null.
func _quest_effect(before: Dictionary, action: String,
		addressing: Variant) -> Dictionary:
	var index := QuestFlow._action_index(action)
	if index < 0:
		return {
			"ok": false,
			"code": "internal_error",
			"error": "the quest double cannot apply a branch record for action "
				+ "'%s': it is outside the closed six-action set" % action,
		}
	var record: Dictionary = (QuestFlow.BRANCHES as Array)[index]
	var fields := (before as Dictionary).duplicate(true)
	var written: Array = []
	var stamps_instant := false
	var stamps_chapter := false
	var mutates := true
	var wrapped: Variant = null
	match str(record["command"]):
		QuestFlow.SET_GOALS_COMMAND:
			var goal_index := int(addressing)
			while goal_index >= (fields[QuestFlow.KEY_GOALS] as Array).size():
				(fields[QuestFlow.KEY_GOALS] as Array).append(null)
			(fields[QuestFlow.KEY_GOALS] as Array)[goal_index] = \
				(QuestFlow.DERIVED_PROGRESS as Array).duplicate()
			written = [QuestFlow.KEY_GOALS]
		QuestFlow.COMPLETE_GOAL_COMMAND:
			# NOTHING AT ALL: the branch resolves the title, prints it, returns.
			mutates = false
		QuestFlow.SET_QUEST_VAR_COMMAND:
			var name := str(addressing)
			if fields[QuestFlow.KEY_QUEST_VARS] == null:
				fields[QuestFlow.KEY_QUEST_VARS] = {}
			var variables: Dictionary = fields[QuestFlow.KEY_QUEST_VARS]
			variables[name] = QuestFlow.DERIVED_QUEST_VALUE
			written = [QuestFlow.KEY_QUEST_VARS]
			if name == QuestFlow.QUEST_VAR_ALIAS_KEY:
				fields[QuestFlow.KEY_MISSION] = QuestFlow.DERIVED_QUEST_VALUE
				written = [QuestFlow.KEY_QUEST_VARS, QuestFlow.KEY_MISSION]
		QuestFlow.COLLECT_MISSION_COMMAND:
			wrapped = QuestFlow.wrap_mission(addressing)
			fields[QuestFlow.KEY_MISSION] = str(wrapped)
			fields[QuestFlow.KEY_LAST_CHAPTER] = _quest_chapter_stamp
			stamps_chapter = true
			fields[QuestFlow.KEY_QUEST_VARS] = {}
			written = [QuestFlow.KEY_MISSION, QuestFlow.KEY_LAST_CHAPTER,
				QuestFlow.KEY_QUEST_VARS]
		QuestFlow.ADMIN_SET_QUEST_RANK_COMMAND:
			var ranks: Dictionary = fields[QuestFlow.KEY_RANKS]
			ranks[str(addressing)] = QuestFlow.DERIVED_DIFFICULTY
			written = [QuestFlow.KEY_RANKS]
		QuestFlow.END_QUEST_COMMAND:
			var times: Dictionary = fields[QuestFlow.KEY_QUEST_TIMES]
			times[str(addressing)] = _quest_time_stamp
			written = [QuestFlow.KEY_QUEST_TIMES]
			stamps_instant = true
		_:
			return {
				"ok": false,
				"code": "internal_error",
				"error": "the quest double cannot apply the branch record for "
					+ "'%s': a seventh branch reached it and this contract "
					% str(record["command"]) + "refuses to guess",
			}
	var expected: Array = (record["writes"] as Array).map(
		func(entry: Variant) -> String: return str(entry))
	# Every field the double ACTUALLY wrote must be named in the record's own
	# `writes`, so a changed effect fails closed here instead of making the double
	# write something the service would not.  The converse is deliberately not
	# asserted: two of the six branches name a field they write only
	# CONDITIONALLY (`idCurrentMission` for the `id` alias) or only in LEGACY
	# (the refused `map_lose_item` reach), so a record may name more than one
	# execution writes.
	for key: String in written as Array:
		var named := false
		for entry: String in expected:
			if _quest_field_for(entry) == key:
				named = true
				break
		if not named:
			return {
				"ok": false,
				"code": "internal_error",
				"error": "the quest double wrote %s, which the branch record for "
					% key + "'%s' does not name" % str(record["command"]),
			}
	var untouched: Array = []
	for key: String in QuestFlow.QUEST_FIELDS:
		if not (written as Array).has(key):
			untouched.append(key)
	return {
		"ok": true,
		"error": "",
		"code": "",
		"command": str(record["command"]),
		"fields": fields,
		"written": written,
		"untouched": untouched,
		"mutates": mutates,
		"stamps_instant": stamps_instant,
		"stamps_chapter": stamps_chapter,
		"wrapped_mission": wrapped,
	}


## One branch record's `writes` entry as the committed FIELD name it refers to,
## so the double can cross-check its derivation without duplicating the table.
func _quest_field_for(entry: String) -> String:
	if entry.begins_with("privateState[goals]"):
		return QuestFlow.KEY_GOALS
	if entry.begins_with("privateState[questsRank]"):
		return QuestFlow.KEY_RANKS
	if entry.begins_with("map[currentQuestVars]"):
		return QuestFlow.KEY_QUEST_VARS
	if entry.begins_with("map[questTimes]"):
		return QuestFlow.KEY_QUEST_TIMES
	if entry.begins_with("map[idCurrentMission]"):
		return QuestFlow.KEY_MISSION
	if entry.begins_with("map[timestampLastChapter]"):
		return QuestFlow.KEY_LAST_CHAPTER
	if entry.begins_with("privateState[unlockedQuestIndex]"):
		return QuestFlow.KEY_UNLOCKED_INDEX
	return entry


## The server-derived `end_quest` blob, or an empty record for every other action —
## matching the endpoint, which reports ``None`` there.
func _quest_blob(action: String, addressing: Variant) -> Dictionary:
	if action != QuestFlow.ACTION_END_QUEST:
		return {}
	return {
		"difficulty": QuestFlow.DERIVED_DIFFICULTY,
		"duration": QuestFlow.DERIVED_DURATION,
		"map": QuestFlow.DERIVED_MAP,
		"quest_id": int(addressing),
		# The refusal, in the exact shape the endpoint sends it: an EMPTY list,
		# so the legacy destruction loop iterates zero times (design D2).
		"units": [],
		"voluntary_end": QuestFlow.DERIVED_VOLUNTARY_END,
		"win": QuestFlow.DERIVED_WIN,
	}


## The refusal records, in the endpoint's own shape.
func _quest_refusal_records() -> Array:
	var out: Array = []
	for record: Variant in QuestFlow.REFUSALS:
		out.append({
			"refusal": str((record as Dictionary)["refusal"]),
			"implemented": bool((record as Dictionary)["implemented"]),
		})
	return out


## The double's own quest fields, as a fresh copy so a caller cannot mutate them.
func _quest_fields() -> Dictionary:
	return (_quest_state["fields"] as Dictionary).duplicate(true)


## The service's `quests` projection for one state: all seven fields verbatim, the
## recorded null flagged, and an **empty** ``derived`` block, which is the
## machine-readable form of "nothing is computed from these fields".
func _quest_block(fields: Dictionary) -> Dictionary:
	var block := fields.duplicate(true)
	block["resolvable"] = true
	block["reason"] = ""
	block["error"] = ""
	block["goals_null_entries"] = 0
	for entry: Variant in (fields[QuestFlow.KEY_GOALS] as Array):
		if entry == null:
			block["goals_null_entries"] = int(block["goals_null_entries"]) + 1
	block["quest_vars_is_null"] = fields[QuestFlow.KEY_QUEST_VARS] == null
	block["mission_is_string"] = fields[QuestFlow.KEY_MISSION] is String
	block["verbatim"] = true
	block["derived"] = {}
	block["quest_field_names"] = (QuestFlow.QUEST_FIELDS as Array).duplicate()
	block["reward_paid"] = QuestFlow.REWARD_PAID
	block["completion_state"] = null
	block["unlocked_quest_index_written"] = false
	return block


## The seven stored resource values of the in-memory quest state, reported
## verbatim as the response's authoritative ``resources``. A quest action moves
## none of them, so these are the values the intent started from — the strongest
## form of the "nothing moved" proof the endpoint requires (design D6).
func _quest_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_quest_state[key])
	return resources


## Loads the quest fixture's first before-state into mutable process state
## (once), validating the seven committed quest fields and the seven balances.
## Structural failures are named with the offending field; every other double's
## error state is untouched (independent sinks).
func _ensure_quest_loaded() -> bool:
	if _quest_loaded:
		return _quest_error == ""
	_quest_loaded = true
	# The boot fixtures must be loaded first: the double's response reports the
	# captured `game_version` and `server_time` from them, so without this the
	# double would answer with an empty version and a ZERO server time whenever
	# it is reached before any boot read.  Done independently of the other
	# doubles, so this double's failure cannot hide behind another's.
	if not _ensure_loaded():
		_quest_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(QUEST_BEFORE_FIXTURE, sink)
	if str(sink["error"]) != "":
		_quest_error = str(sink["error"])
		return false
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_quest_error = "the quest fixture before state carries no maps array"
		return false
	var first_map: Variant = (maps as Array)[0]
	if not (first_map is Dictionary):
		_quest_error = "the quest fixture before state's first map is not an object"
		return false
	var rows: Variant = (first_map as Dictionary).get("items")
	if not (rows is Dictionary) or (rows as Dictionary).is_empty():
		_quest_error = "the quest fixture before state carries no placement map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_quest_error = "the quest fixture before state lacks playerInfo/privateState"
		return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or cash == null or mana == null \
			or int(cash) < 0 or int(mana) < 0:
		_quest_error = "the quest fixture before state lacks save fields"
		return false
	var resources := {}
	for name: String in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (first_map as Dictionary).get(name)
		if value == null or int(value) < 0:
			_quest_error = "the quest fixture before state lacks map %s" % name
			return false
		resources[name] = int(value)
	resources["cash"] = int(cash)
	resources["mana"] = int(mana)
	var fields := {
		QuestFlow.KEY_GOALS: ((priv as Dictionary).get(QuestFlow.KEY_GOALS)
			as Array).duplicate(true),
		QuestFlow.KEY_RANKS: ((priv as Dictionary).get(QuestFlow.KEY_RANKS)
			as Dictionary).duplicate(true),
		QuestFlow.KEY_QUEST_VARS: _quest_copied_var(first_map),
		QuestFlow.KEY_QUEST_TIMES: ((first_map as Dictionary).get(
			QuestFlow.KEY_QUEST_TIMES) as Dictionary).duplicate(true),
		QuestFlow.KEY_MISSION: (first_map as Dictionary).get(QuestFlow.KEY_MISSION),
		QuestFlow.KEY_LAST_CHAPTER: int((first_map as Dictionary).get(
			QuestFlow.KEY_LAST_CHAPTER)),
		QuestFlow.KEY_UNLOCKED_INDEX: int((priv as Dictionary).get(
			QuestFlow.KEY_UNLOCKED_INDEX)),
	}
	# The committed corpus holds every quest field at its initial value, and the
	# double validates that rather than trusting this sentence: a capture that is
	# not the recorded transaction fails closed here.
	if (fields[QuestFlow.KEY_GOALS] as Array).size() \
			!= QuestFlow.CORPUS_GOALS_LENGTH:
		_quest_error = "the quest fixture before state's goals list holds %d " \
			% (fields[QuestFlow.KEY_GOALS] as Array).size() \
			+ "entries, not the committed %d" % QuestFlow.CORPUS_GOALS_LENGTH
		return false
	for entry: Variant in fields[QuestFlow.KEY_GOALS] as Array:
		if entry != null:
			_quest_error = ("the quest fixture before state's goals list holds a "
				+ "non-null entry: the committed corpus is ALL None")
			return false
	if fields[QuestFlow.KEY_QUEST_VARS] != null:
		_quest_error = ("the quest fixture before state's quest-variable map is "
			+ "not the committed recorded null")
		return false
	if fields[QuestFlow.KEY_MISSION] != QuestFlow.CORPUS_MISSION:
		_quest_error = ("the quest fixture before state's mission is %s, not the "
			% fields[QuestFlow.KEY_MISSION] + "committed integer %s" \
			% QuestFlow.CORPUS_MISSION)
		return false
	# The recorded wall-clock stamps the executed capture left behind, read out of
	# its own steps so the double never reads a clock (design D2/D8).
	_quest_chapter_stamp = _quest_recorded_stamp(QUEST_CHAPTER_FIXTURE,
		QuestFlow.KEY_LAST_CHAPTER)
	_quest_time_stamp = _quest_recorded_stamp(QUEST_TIME_FIXTURE,
		QuestFlow.KEY_LAST_CHAPTER)
	if _quest_chapter_stamp <= 0 or _quest_time_stamp <= 0:
		_quest_error = ("the quest fixture recorded no positive wall-clock stamp "
			+ "for the chapter or the quest time, so the double could not be "
			+ "deterministic")
		return false
	# The placement map is read and never written: a quest action moves no
	# placement row, so the double holds no copy of one at all.
	var state := resources
	state["fields"] = fields
	_quest_state = state
	_quest_pid = str(pid)
	return true


## The quest-variable map as a fresh copy, or `null` preserved as `null` — the
## committed corpus records this field as a recorded null and two branches
## self-heal it to a dict, which is a real shape fact rather than a defect.
func _quest_copied_var(first_map: Dictionary) -> Variant:
	var value: Variant = first_map.get(QuestFlow.KEY_QUEST_VARS)
	if value == null:
		return null
	return (value as Dictionary).duplicate(true)


## The wall-clock instant the committed executed capture recorded for one step,
## read out of that step's recorded after-state.  `0` means the capture recorded
## none, which the two stamping branches never do.
func _quest_recorded_stamp(fixture: String, field: String) -> int:
	var sink := {"error": ""}
	var after := _read_json_into(fixture, sink)
	if str(sink["error"]) != "":
		return 0
	var maps: Variant = after.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return 0
	var value: Variant = (maps as Array)[0].get(field)
	var number: Variant = BootData._parse_int(value)
	if number == null or int(number) <= 0:
		return 0
	return int(number)


# ---------------------------------------------------------------------------
# The tutorial double (OpenSpec `tutorial`, M9 line 3)
# ---------------------------------------------------------------------------


## One tutorial **step** intent from the committed executed-legacy fixture, for
## the offline hermetic runs.
##
## The step is **intent** and nothing else. This double takes exactly TWO
## parameters — the save identity and the step — so there is no channel through
## which a caller could send a completion flag, a reward, a price, or a resource
## vector: the gate is derived from the committed expression, the command is
## derived from the single legacy branch (`command.py:60-66`), and the NEUTRAL
## vector is the endpoint's, never a client's (tutorial design D2/D5).
##
## The double answers with the committed **neutral** round of
## `tests/fixtures/godot-tutorial/`, read into process state once:
##   * the first step whose gate fires moves the flag `0 -> 1` and nothing else —
##     the changed list is exactly the single flag leaf;
##   * a second step at the same value answers `already_completed` and changes
##     nothing, byte-identical to the completing step's recorded after-state,
##     which is what makes the no-op provable rather than asserted;
##   * any step the committed gate declines answers `gate_declined` and changes
##     nothing.
##
## **Both no-ops answer a typed success, never an error.** The legacy server
## answers `{"result": "success"}` and changes nothing in both, so reporting
## either as a failure would be a divergence with no evidence behind it.
##
## The refusals mirror the endpoint's, in the endpoint's order: the save-identity
## codes first, then `invalid_step` for anything the committed gate cannot
## compare, then `unresolvable_tutorial_state` for a save this projection cannot
## read.
##
## **The gate the double answers is not an echo of the client module**: it is
## compared against the committed capture manifest's own `gate` block at load
## time, so a drift between the two fails the double instead of being reflected
## in it. **The minting round is read as an ANCHOR and never reproduced**: the
## endpoint's second proof half requires every stored resource to be unchanged,
## and that claim is only meaningful because the committed capture really did move
## all seven — so the double loads that ladder and refuses to answer if the
## neutral round's unchanged balances are not a real subset of the transaction.
func complete_tutorial_town(user_id: String, step: int) -> TutorialFlow.TutorialResult:
	if user_id.strip_edges() == "":
		return TutorialFlow.result_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_tutorial_loaded():
		return TutorialFlow.result_failure("fixture_unreadable", _tutorial_error)
	if user_id != _tutorial_pid:
		return TutorialFlow.result_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if not TutorialFlow.is_step(step):
		return TutorialFlow.result_failure("invalid_step",
			("step must be an integer the committed gate can compare; got %s"
				% typeof(step)) + " (see gate %s)" % TutorialFlow.GATE_EXPRESSION)
	if not bool((_tutorial_state["flag"] as Dictionary).get("ok", false)):
		return TutorialFlow.result_failure("unresolvable_tutorial_state",
			("the fixture save records no readable %s.%s"
				% [TutorialFlow.PLAYER_INFO_RECORD, TutorialFlow.FLAG_KEY])
				+ " (found %s)" % str((_tutorial_state["flag"] as Dictionary)
					.get("reason", "")))
	var effect := _tutorial_effect(int(step))
	# The double DOES move its in-memory flag on a dispatch, because that is the
	# whole transaction: the legacy branch writes the save, so a second request
	# really does see the flag at its post-value and answers `already_completed`.
	# Without this the repeat branch would be unreachable offline and its
	# no-op-ness would be asserted rather than demonstrated. It is also
	# **monotonic** — nothing ever writes the flag back, which is why there is no
	# un-complete path to model.
	if bool((effect["block"] as Dictionary).get("dispatched", false)):
		(_tutorial_state["flag"] as Dictionary)["stored"] = \
			TutorialFlow.COMMITTED_FLAG_AFTER
		(_tutorial_state["flag"] as Dictionary)["completed"] = true
	return TutorialFlow.parse_result({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"tutorial": effect["block"],
		"gate": TutorialFlow.gate_record(),
		"changed": (effect["changed"] as Array).duplicate(),
		"resources": _tutorial_resources(),
		"anchor": (_tutorial_state["anchor"] as Dictionary).duplicate(true),
		"refusals": _tutorial_refusal_records(),
		"no_reward_paid": true,
		"stored_step_introduced": false,
	})


## The recorded legacy effect of one tutorial step — DERIVED from the committed
## gate and this double's own flag, never read from a response. Returns
## ``{block, changed}``.
##
## The three outcomes are the committed ones, in the endpoint's order: the flag
## already at the post-value answers `already_completed`, a step the gate declines
## answers `gate_declined`, and only a step the gate fires dispatches the write.
## Nothing else can move, because the only leaf the legacy branch writes is the
## flag — so the changed list is empty for both no-ops **by construction** rather
## than by assertion.
func _tutorial_effect(step: int) -> Dictionary:
	var stored := int((_tutorial_state["flag"] as Dictionary)["stored"])
	var verdict := TutorialFlow.gate_verdict(step)
	var no_op := ""
	if stored == TutorialFlow.COMMITTED_FLAG_AFTER:
		no_op = "already_completed"
	elif verdict == TutorialFlow.ARM_NONE:
		no_op = "gate_declined"
	var dispatched := no_op == ""
	var flag_after := stored
	if dispatched:
		flag_after = TutorialFlow.COMMITTED_FLAG_AFTER
	var block := {
		"command": TutorialFlow.COMPLETE_TUTORIAL_COMMAND,
		"step": step,
		"step_kind": "integer",
		"record": TutorialFlow.PLAYER_INFO_RECORD,
		"key": TutorialFlow.FLAG_KEY,
		"flag_before": stored,
		"flag_after": flag_after,
		"flag_moved": dispatched,
		"gate_satisfied": verdict != TutorialFlow.ARM_NONE,
		"gate_arm": verdict,
		"in_gate_hole": TutorialFlow.gate_hole_steps().has(step),
		"already_completed": stored == TutorialFlow.COMMITTED_FLAG_AFTER,
		"no_op_reason": no_op,
		"dispatched": dispatched,
		"resolvable": true,
		"completed": flag_after == TutorialFlow.COMMITTED_FLAG_AFTER,
		"stored": flag_after,
	}
	var changed: Array = []
	if dispatched:
		changed = ["/%s/%s" % [TutorialFlow.PLAYER_INFO_RECORD,
			TutorialFlow.FLAG_KEY]]
	return {"block": block, "changed": changed}


## The service's `tutorial` block for the committed post-state, as the response's
## authoritative value. Reported **verbatim** from the fixture, never recomputed.
func _tutorial_post_block() -> Dictionary:
	var stored := int((_tutorial_state["flag"] as Dictionary)["stored"])
	return {
		"record": TutorialFlow.PLAYER_INFO_RECORD,
		"key": TutorialFlow.FLAG_KEY,
		"stored": stored,
		"completed": stored == TutorialFlow.COMMITTED_FLAG_AFTER,
		"resolvable": true,
	}


## The seven stored resource values of the in-memory tutorial state, reported
## verbatim as the response's authoritative `resources`. A tutorial completion
## moves none of them, so these are the values the intent started from — the
## strongest form of the "nothing moved" proof the endpoint requires (design D5).
func _tutorial_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_tutorial_state[key])
	return resources


## The refusals this double can answer, as records, so a report can enumerate the
## closed set instead of restating it.
func _tutorial_refusal_records() -> Array:
	return [
		{"code": "missing_user_id", "when": "the identity is empty"},
		{"code": "unknown_user_id", "when": "the identity is not the fixture's"},
		{"code": "invalid_step", "when": "the committed gate cannot compare the "
			+ "step. Legacy RAISES on a string, a missing, and a null step and "
			+ "escapes as HTTP %d; this line REFUSES those three instead, which "
			% TutorialFlow.RAISING_STATUS
			+ "is its one deliberate divergence and is confined to failure "
			+ "handling"},
		{"code": "unresolvable_tutorial_state", "when": "the save records no "
			+ "readable %s.%s" % [TutorialFlow.PLAYER_INFO_RECORD,
				TutorialFlow.FLAG_KEY]},
	]


## Loads the tutorial fixture's neutral round into mutable process state (once),
## and validates it against the committed capture manifest.
func _ensure_tutorial_loaded() -> bool:
	if _tutorial_loaded:
		return _tutorial_error == ""
	_tutorial_loaded = true
	# The boot fixtures must be loaded first: the double's response reports the
	# captured `game_version` and `server_time` from them, so without this the
	# double would answer with an empty version and a ZERO server time whenever it
	# is reached before any boot read.  Done independently of the other doubles,
	# so this double's failure cannot hide behind another's.
	if not _ensure_loaded():
		_tutorial_error = _load_error
		return false
	# The capture manifest is the double's ORACLE: its `gate` block is compared
	# field by field against the client's committed mirror, so the two cannot
	# drift apart silently and the double's answer is never an echo.
	var manifest_sink := {"error": ""}
	var manifest := _read_json_into(TutorialFlow.CAPTURE_MANIFEST, manifest_sink)
	if str(manifest_sink["error"]) != "":
		_tutorial_error = str(manifest_sink["error"])
		return false
	var committed_gate: Variant = manifest.get("gate")
	if not (committed_gate is Dictionary):
		_tutorial_error = "the tutorial capture manifest carries no gate block"
		return false
	var mirror := TutorialFlow.gate_record()
	for field: String in mirror.keys():
		# Compared through the module's own helper, never with `str()`: this engine
		# decodes every JSON number as a float, so the manifest's integer 25 arrives
		# as 25.0 and a text comparison would refuse the genuine capture.
		if not TutorialFlow._gate_field_equal(
				(committed_gate as Dictionary).get(field), mirror.get(field)):
			_tutorial_error = ("the capture manifest's gate.%s is '%s', which "
				% [field, str((committed_gate as Dictionary).get(field, ""))]
				+ "contradicts the committed mirror this double answers with")
			return false
	var before_sink := {"error": ""}
	var before := _read_json_into(TUTORIAL_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_tutorial_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(TUTORIAL_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_tutorial_error = str(after_sink["error"])
		return false
	var repeat_sink := {"error": ""}
	var repeated := _read_json_into(TUTORIAL_REPEAT_AFTER_FIXTURE, repeat_sink)
	if str(repeat_sink["error"]) != "":
		_tutorial_error = str(repeat_sink["error"])
		return false
	var resources: Variant = _tutorial_balances(before)
	if resources == null:
		_tutorial_error = "the tutorial fixture before state lacks the seven " \
			+ "stored resources"
		return false
	var flag := TutorialFlow.project(before)
	if not bool(flag.get("ok", false)):
		_tutorial_error = ("the tutorial fixture before state is unresolvable: "
			+ str(flag.get("reason", "")))
		return false
	if int(flag["stored"]) != TutorialFlow.COMMITTED_FLAG_BEFORE:
		_tutorial_error = ("the tutorial fixture before state records %s = %d, "
			% [TutorialFlow.FLAG_KEY, int(flag["stored"])]
			+ "not the committed seed %d" % TutorialFlow.COMMITTED_FLAG_BEFORE)
		return false
	# The completing step's recorded after-state must be the SAME save with the
	# flag at the committed post-value, and must differ in nothing else. Compared
	# key by key rather than by digest so the failure names the key that drifted.
	var recorded_after := TutorialFlow.project(after)
	if not bool(recorded_after.get("ok", false)) \
			or int(recorded_after["stored"]) != TutorialFlow.COMMITTED_FLAG_AFTER:
		_tutorial_error = ("the tutorial fixture after state records %s = %s, "
			% [TutorialFlow.FLAG_KEY, str((recorded_after as Dictionary)
				.get("stored", ""))]
			+ "not the committed post-value %d"
			% TutorialFlow.COMMITTED_FLAG_AFTER)
		return false
	if _tutorial_balances(after) != resources:
		_tutorial_error = ("the tutorial fixture after state moves a stored "
			+ "balance, which the committed transaction does not do")
		return false
	# The repeat step answers nothing at all: its recorded after-state is the
	# completing step's own, so the no-op is proved by the capture rather than
	# asserted here.
	if repeated.get("playerInfo") != after.get("playerInfo"):
		_tutorial_error = ("the tutorial fixture's repeat step changed something, "
			+ "but the committed capture records it as a no-op")
		return false
	if _tutorial_balances(repeated) != resources:
		_tutorial_error = "the tutorial fixture's repeat step moved a balance"
		return false
	# The ANCHOR: the minting round really did move all seven. Read, never
	# reproduced — it exists so the double's "nothing moved" answer is checked
	# against an oracle rather than asserted, and so a caller can see the ladder
	# the NEUTRAL vector refuses.
	var minted_sink := {"error": ""}
	var minted := _read_json_into(TUTORIAL_MINTING_AFTER_FIXTURE, minted_sink)
	if str(minted_sink["error"]) != "":
		_tutorial_error = str(minted_sink["error"])
		return false
	var minted_balances: Variant = _tutorial_balances(minted)
	if minted_balances == null:
		_tutorial_error = "the tutorial fixture's minting round lacks balances"
		return false
	var ladder: Array = []
	for key: String in RESOURCE_KEYS:
		if int(minted_balances[key]) != int(resources[key]):
			ladder.append(key)
	if ladder.size() != RESOURCE_KEYS.size():
		_tutorial_error = ("the tutorial capture's minting round moved %d of %d "
			% [ladder.size(), RESOURCE_KEYS.size()]
			+ "balances, so the NEUTRAL vector's unchanged answer would be "
			+ "vacuous")
		return false
	var state: Dictionary = (resources as Dictionary).duplicate(true)
	state["flag"] = flag
	state["anchor"] = {
		"role": "the committed capture's client-sent ladder, read as the ANCHOR "
			+ "and deliberately never reproduced",
		"moved": ladder,
		"moved_count": ladder.size(),
		"minted_balances": minted_balances,
		"neutral_vector": (TutorialFlow.NEUTRAL_VECTOR as Array).duplicate(),
	}
	_tutorial_state = state
	_tutorial_pid = str((before.get("playerInfo") as Dictionary).get("pid", ""))
	return true


## The seven stored balances of one recorded save, or `null` when the document
## does not carry all seven as non-negative integers.
func _tutorial_balances(save: Dictionary) -> Variant:
	var maps: Variant = save.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return null
	var first: Variant = (maps as Array)[0]
	var info: Variant = save.get("playerInfo")
	var priv: Variant = save.get("privateState")
	if not (first is Dictionary) or not (info is Dictionary) \
			or not (priv is Dictionary):
		return null
	var balances := {}
	for key: String in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (first as Dictionary).get(key)
		if value == null or int(value) < 0:
			return null
		balances[key] = int(value)
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if cash == null or mana == null or int(cash) < 0 or int(mana) < 0:
		return null
	balances["cash"] = int(cash)
	balances["mana"] = int(mana)
	return balances
# --- stored-item placement double (stored-item-placement design D8) --------

## One stored-item placement intent in the double. The double is the SERVICE's
## stand-in, not the client's: it is the authority on its own storage, its own
## map slots, and its own committed content, so this is where the four refusals
## and the slot derivation live. `stored_item_flow.gd` mirrors the derivation
## and deliberately does NOT re-implement the refusals.
func place_stored_item_town(user_id: String, item_id: int, x: int,
		y: int) -> BootData.StoredPlacementResult:
	if user_id.strip_edges() == "":
		return _stored_placement_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_stored_loaded():
		return _stored_placement_failure("fixture_unreadable", _stored_error)
	if user_id != _stored_pid:
		return _stored_placement_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# The refusal ORDER matches the service exactly (compat_service.py:1562,
	# :1570, :1596): the two committed-content refusals come BEFORE the stock
	# check, because a row cannot be derived at all from an id the content does
	# not define -- so the honest complaint about the item precedes the honest
	# complaint about its stock.
	var committed: Variant = _config_items.get(str(item_id))
	if not (committed is Dictionary):
		return _stored_placement_failure("unknown_item_id",
			("item %d resolves to no committed definition, so nothing about a "
			% item_id)
			+ "row for it can be derived; the legacy server places one anyway "
			+ "with an empty attribute bag")
	var row_def: Dictionary = committed
	var derived := StoredItemFlow.derive_attr(row_def.get("clicks_to_build"),
		row_def.get("properties"))
	if not bool(derived["ok"]):
		return _stored_placement_failure(str(derived["code"]),
			str(derived["error"]))
	if not _stored_placeable(row_def):
		return _stored_placement_failure("item_not_placeable",
			("committed item %d carries neither properties nor clicks_to_build, "
			% item_id)
			+ "so the legacy derivation would write no attribute bag at all")
	var store: Dictionary = _stored_state["store"] as Dictionary
	var stock := StoredItemFlow.stored_count(store, item_id)
	if stock < 1:
		return _stored_placement_failure("not_in_storage",
			("item %d is not in storage; `remove_store_item`'s `if itemstr in "
			% item_id)
			+ "map[\"store\"]` conditional (engine.py:78) makes an absent item a "
			+ "silent no-op, and the legacy server places the row anyway")
	var items: Dictionary = _stored_state["items"] as Dictionary
	var slot := _stored_next_free_slot(items)
	if _stored_slot_occupied(items, slot):
		return _stored_placement_failure("slot_occupied",
			"derived map slot %d already names a row" % slot)
	var before_store := store.duplicate(true)
	var before_ledger: Array = (_stored_state["ledger"] as Array).duplicate(true)
	var attr: Dictionary = (derived["attr"] as Dictionary).duplicate(true)
	var row := [item_id, x, y, _stored_epoch(), StoredItemFlow.DERIVED_ORIENTATION,
		[], attr, StoredItemFlow.DERIVED_PLAYER]
	var after_store := before_store.duplicate(true)
	var key := str(item_id)
	var remaining := int(after_store.get(key, 0)) - StoredItemFlow.QUANTITY
	if remaining > 0:
		after_store[key] = remaining
	else:
		after_store.erase(key)
	var after_ledger: Array = before_ledger.duplicate(true)
	if not after_ledger.has(item_id):
		after_ledger.append(item_id)
	var after_items := items.duplicate(true)
	after_items[str(slot)] = row
	_stored_state["store"] = after_store
	_stored_state["ledger"] = after_ledger
	_stored_state["items"] = after_items
	return BootData.parse_stored_placement({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"placement": {
			"command": StoredItemFlow.PLACE_COMMAND,
			"item_id": item_id,
			"x": x,
			"y": y,
			"orientation": StoredItemFlow.DERIVED_ORIENTATION,
			"map_key": slot,
			"derived_from": "the server derives the map slot as the smallest "
				+ "positive integer absent from the map's placements and accepts "
				+ "no slot, row, attribute bag, player team, count or price from "
				+ "the client",
			"slot_rule": StoredItemFlow.SLOT_RULE,
			"row_derivation": StoredItemFlow.ROW_DERIVATION,
		},
		"row": {
			"slots": row.duplicate(true),
			"item_id": row[StoredItemFlow.ROW_SLOT_ITEM],
			"x": row[StoredItemFlow.ROW_SLOT_X],
			"y": row[StoredItemFlow.ROW_SLOT_Y],
			"timestamp": int(row[StoredItemFlow.ROW_SLOT_TIMESTAMP]),
			"orientation": row[StoredItemFlow.ROW_SLOT_ORIENTATION],
			"store": [],
			"attr": attr.duplicate(true),
			"player": StoredItemFlow.DERIVED_PLAYER,
			"attr_rule": StoredItemFlow.ATTR_RULE,
			"attr_derived_from": derived["fields"],
			"timestamp_note": StoredItemFlow.TIMESTAMP_NOTE,
		},
		"quantity": {
			"consumed": StoredItemFlow.QUANTITY,
			"count_before": stock,
			"count_after": stock - StoredItemFlow.QUANTITY,
			"rule": StoredItemFlow.QUANTITY_RULE,
		},
		"storage_before": before_store,
		"storage_after": after_store,
		"storage": StoredItemFlow.project_storage(after_store, after_ledger),
		"ledger_before": before_ledger,
		"ledger_after": after_ledger,
		"ledger_rule": StoredItemFlow.LEDGER_RULE,
		"refused": {"dismissed_arguments": []},
		"refusals": [],
		"geometry": {
			"bounds_refused": false,
			"cell_occupancy_refused": false,
			"note": StoredItemFlow.GEOMETRY_GAP,
			"occupancy_note": StoredItemFlow.CELL_OCCUPANCY_GAP,
		},
		"resources": _stored_resources(),
	})


## One stored-item sale intent in the double. The legacy branch's entire effect
## is one store key disappearing: no price, no refund, no quantity argument, and
## no return value, so `credited` is a recorded `false` and the post-execution
## proof requires every stored resource to be unchanged.
func sell_stored_item_town(user_id: String,
		item_id: int) -> BootData.StoredSaleResult:
	if user_id.strip_edges() == "":
		return _stored_sale_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_stored_loaded():
		return _stored_sale_failure("fixture_unreadable", _stored_error)
	if user_id != _stored_pid:
		return _stored_sale_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var store: Dictionary = _stored_state["store"] as Dictionary
	var stock := StoredItemFlow.stored_count(store, item_id)
	if stock < 1:
		return _stored_sale_failure("not_in_storage",
			"item %d is not in storage" % item_id)
	var before_store := store.duplicate(true)
	var before_ledger: Array = (_stored_state["ledger"] as Array).duplicate(true)
	var after_store := before_store.duplicate(true)
	var key := str(item_id)
	var remaining := int(after_store.get(key, 0)) - StoredItemFlow.QUANTITY
	if remaining > 0:
		after_store[key] = remaining
	else:
		after_store.erase(key)
	_stored_state["store"] = after_store
	return BootData.parse_stored_sell({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		"server_time": _fixture_server_time(),
		"result": "success",
		"sale": {
			"command": StoredItemFlow.SELL_COMMAND,
			"item_id": item_id,
			"credited": false,
			"refund": null,
			"note": StoredItemFlow.NO_REFUND_NOTE,
			"quantity_rule": StoredItemFlow.QUANTITY_RULE,
		},
		"quantity": {
			"consumed": StoredItemFlow.QUANTITY,
			"count_before": stock,
			"count_after": stock - StoredItemFlow.QUANTITY,
		},
		"storage_before": before_store,
		"storage_after": after_store,
		"storage": StoredItemFlow.project_storage(after_store, before_ledger),
		"ledger_before": before_ledger,
		"ledger_after": before_ledger.duplicate(true),
		"ledger_rule": StoredItemFlow.LEDGER_RULE,
		"resources": _stored_resources(),
	})


func _stored_placement_failure(code: String,
		message: String) -> BootData.StoredPlacementResult:
	return BootData.parse_stored_placement({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


func _stored_sale_failure(code: String,
		message: String) -> BootData.StoredSaleResult:
	return BootData.parse_stored_sell({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The SERVICE's placeability predicate, deliberately NOT mirrored into
## `stored_item_flow.gd`: a client-side copy would second-guess it and could
## disagree. 0 of 900 committed items fail this, so the refusal is unreachable
## through the committed corpus and is exercised only against an in-memory row.
func _stored_placeable(row_def: Dictionary) -> bool:
	var properties: Variant = row_def.get("properties")
	if properties is Dictionary and not (properties as Dictionary).is_empty():
		return true
	if properties is String and str(properties).strip_edges() != "":
		return true
	return bool(row_def.get("clicks_to_build"))


## The slot derivation the service owns: the smallest POSITIVE integer absent
## from the map's placements. Legacy map keys are `str(index)`, so a key that
## does not parse as an integer cannot collide with a numeric slot string.
func _stored_next_free_slot(items: Dictionary) -> int:
	var used := {}
	for key: Variant in items:
		var text := str(key)
		if text.is_valid_int():
			used[int(text)] = true
	var candidate := 1
	while used.has(candidate):
		candidate += 1
	return candidate


## The named inverse of the derivation, so the second line of defence is
## reachable rather than dead code.
func _stored_slot_occupied(items: Dictionary, slot: int) -> bool:
	return items.has(str(slot))


## The recorded capture's row instant, never the wall clock: the fixture is the
## oracle, so the double is deterministic by construction.
func _stored_epoch() -> int:
	return _stored_epoch_value


## The seven stored resources, unchanged: placing and selling both move none.
func _stored_resources() -> Dictionary:
	var out := {}
	for key: String in RESOURCE_KEYS:
		out[key] = int(_stored_state[key])
	return out


func _ensure_stored_loaded() -> bool:
	if _stored_loaded:
		return _stored_error == ""
	_stored_loaded = true
	# The committed items table is read out of the SAME captured config payload
	# the other doubles index, so the base fixtures must be loaded first --
	# independently of them, so this double's failure cannot hide behind
	# another's.
	if not _ensure_loaded():
		_stored_error = _load_error
		return false
	var sink := {"error": ""}
	var before := _read_json_into(STORED_PLACE_BEFORE_FIXTURE, sink)
	if str(sink["error"]) != "":
		_stored_error = str(sink["error"])
		return false
	# The after-state is read (never written) so a malformed capture cannot leave
	# the double running on an inconsistent oracle.
	var after_sink := {"error": ""}
	var after := _read_json_into(STORED_PLACE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_stored_error = str(after_sink["error"])
		return false
	return _init_stored_state(before, after)


## Validates both fixture documents and builds the in-memory storage state.
## Every consumed field is checked, so a malformed fixture fails closed instead
## of crashing the double.
func _init_stored_state(before: Dictionary, after: Dictionary) -> bool:
	var before_map: Variant = _first_map(before, "before")
	if before_map == null:
		_stored_error = "stored-placement fixture before state carries no map"
		return false
	var after_map: Variant = _first_map(after, "after")
	if after_map == null:
		_stored_error = "stored-placement fixture after state carries no map"
		return false
	var items: Variant = (before_map as Dictionary).get("items")
	var store: Variant = (before_map as Dictionary).get("store")
	if not (items is Dictionary) or not (store is Dictionary):
		_stored_error = "stored-placement fixture before state lacks items/store"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_stored_error = (
			"stored-placement fixture before state lacks playerInfo/privateState")
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (before_map as Dictionary).get(key)
		if not (value is int or value is float):
			_stored_error = "stored-placement fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var energy: Variant = (priv as Dictionary).get("energy")
	var ledger: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) \
			or not (energy is int or energy is float) or not (ledger is Array):
		_stored_error = "stored-placement fixture before state lacks save fields"
		return false
	# The after-state must add exactly one entry -- the capture's placement --
	# and its recorded wall-clock instant becomes the double's epoch, so the
	# double never reads the wall clock.
	var after_items: Variant = (after_map as Dictionary).get("items")
	if not (after_items is Dictionary):
		_stored_error = "stored-placement fixture after state carries no items map"
		return false
	var added: Array = []
	for key: Variant in (after_items as Dictionary):
		if not (items as Dictionary).has(str(key)):
			added.append(str(key))
	if added.size() != 1:
		_stored_error = ("stored-placement fixture after state must add exactly "
			+ "one entry, found %d") % added.size()
		return false
	var entry: Variant = (after_items as Dictionary).get(added[0])
	if not (entry is Array) or (entry as Array).size() != 8:
		_stored_error = (
			"stored-placement fixture after entry is not the eight-field array")
		return false
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) < 0 \
			or float(stamp) != floor(float(stamp)):
		_stored_error = (
			"stored-placement fixture entry timestamp is not a non-negative integer")
		return false
	_stored_state = {
		"items": (items as Dictionary).duplicate(true),
		"store": (store as Dictionary).duplicate(true),
		"ledger": (ledger as Array).duplicate(true),
		"xp": int((before_map as Dictionary).get("xp")),
		"gold": int((before_map as Dictionary).get("gold")),
		"wood": int((before_map as Dictionary).get("wood")),
		"oil": int((before_map as Dictionary).get("oil")),
		"steel": int((before_map as Dictionary).get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"energy": int(energy),
		"placed_key": added[0],
		"placed_item_id": int((entry as Array)[0]),
	}
	_stored_pid = pid
	_stored_epoch_value = int(stamp)
	return true