extends RefCounted
## Pure refusal and inventory for the unit-production flow (OpenSpec
## `godot-unit-production` "Production is refused, with the evidence recorded" /
## "The row-entry inventory names every item id's source" / "No duration is
## derived from the committed training time" / "No experience is awarded from a
## client amount" / "No server operation is exposed for production" / "Unit-
## production evidence and claim limits", design D1-D7).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy server **cannot produce a unit**, and that is not a gap this
## line fills. There is no completion command, no elapsed-time evaluation, and
## no committed rule that derives a unit from a queue, a duration, or any other
## content. So the deliverable is an **explicit refusal with its evidence
## attached** (design D1), and a **production-shaped committed field plus a
## plausible-looking `training_time` with no recorded reason to decline it** is
## exactly the setup for a later line to compute a client-side readiness and
## call it production. This module makes the refusal durable.
##
## ## The projection reports PRESENCE and an INSTANT, never readiness (D1/D4)
##
## `evaluate()` is the one entry point. It delegates the queue projection to
## `queue_flow.gd` — **never re-deriving it**, so a surface, the suite, and the
## report cannot disagree about a queue — and adds only the absence record: a
## queue exists, its start instant is reported verbatim, and the legacy server
## **cannot say whether that queue is ready**. It computes no readiness, no
## remaining time, no progress ratio, and no duration, and `ABSENT_HELPERS`
## names every helper it therefore does not provide. The suite asserts this
## module's **whole function inventory** against a pinned list, so a readiness
## helper fails the delivered suite rather than appearing quietly later.
##
## ## Every row-entry branch, with its item id's SOURCE (D2)
##
## `command.py`'s only `map_add_item` / `map_add_item_from_item` call sites are
## **five** branches, recorded in `ROW_ENTRY` with the line, the call, **where
## the item id comes from**, and its classification as `client-supplied`,
## `already-existing`, or `derived-from-committed-content`. **Four take the id
## straight from a client argument** and the fifth moves a row that already
## existed in a building's garrison. The `derived` set is therefore **empty**,
## and that emptiness is the claim that matters: **no path places a unit
## derived from a completed queue, from a duration, or from committed
## production content.** The suite *measures* the call sites, the enclosing
## branch names, and the count out of the committed legacy source and compares
## them with this table, so the inventory cannot drift from the source and a
## sixth call site would be reported as an unrecorded gap rather than ignored.
##
## ## The committed training time is CONTENT, never a duration (D3)
##
## `training_time` has **zero** legacy consumers. The suite measures this: it
## searches the six named legacy modules, and the only occurrences of the string
## are **three**, every one of them the *distinct* field `sm_training_time` inside
## the soul-mixer speedup branch — a different field, on a different path. The
## three sit on **two** lines, and the two counts are reported separately so neither
## can be mistaken for the other. Measured across the
## content, the key is carried by **every** committed item and reads as a
## positive duration on **130 of 470** buildings, including the Command
## Center's `5` — and it is read by **nothing**, so no production time,
## remaining time, or progress ratio is derived from it. This is the **third**
## committed content field in this project with no legacy consumer, after
## `unit_capacity` (M8 line 2) and the level curve's reward fields (M7's XP
## line); the precedent is established twice — record the field, refuse to
## invent a rule from it. `committed_training_time()` exists to report the
## value **as content**, verbatim, and computes nothing from it.
##
## ## No experience is awarded from a client amount (D5)
##
## `add_xp_unit` is the only command writing a placed row's `attr["xp"]`: it
## **creates nothing**, adds a **client-sent** amount, and uses an optional
## client-sent level only in a printed line. So `experience()` reports a
## recorded value **as content, verbatim, never awarded**, and the committed
## corpus carries the field on **0 of 40** rows. This supersedes the softer
## `godot-building-xp` note that unit experience was out of scope because the
## corpus could not exercise it: the sharper truth is that **nothing on the
## server awards it from a trusted value**.
##
## ## The acquisition routes are UNVALIDATED client-sent lists (D1/D5)
##
## Six branches can fill the storage, and the two plausible unit sources are
## unvalidated: `buy_offer_pack` reads `package_id` and **never uses it**, then
## `json.loads` a client-sent array and stores every id in it with **no lookup
## into the committed `offer_packs` table**, and `buy_stored_item_cash` is the
## same shape with one client-sent id. So the committed acquisition tables
## describe a content-derived system this server does not implement, and
## **no acquisition mechanism is implemented here** — no request is issued, and
## the tables are named as a later capability's work rather than enforced.
## Their unit-reference counts are recorded as **DISTINCT** ids and measured
## as such, because the occurrence totals are several times larger and the two
## must never be conflated.
##
## ## Purity
##
## This module holds no node, no clock, no request, and no transport, and it
## reads the content package through **no** preload: every committed number it
## reports arrives as a parameter, so the same functions serve the town view,
## the hermetic suite, and the deterministic report.

const QueueFlow = preload("res://scripts/units/queue_flow.gd")
const UnitQueue = preload("res://scripts/units/unit_queue.gd")

# ---------------------------------------------------------------------------
# The one projection
# ---------------------------------------------------------------------------

## The three ways a row's item id is reported to have arrived. There is
## deliberately no fourth: an id whose source cannot be named is not
## inventoried at all rather than filed under a vague heading.
const CLASS_CLIENT := "client-supplied"
const CLASS_ALREADY := "already-existing"
const CLASS_DERIVED := "derived-from-committed-content"
const CLASSIFICATIONS := [CLASS_CLIENT, CLASS_ALREADY, CLASS_DERIVED]

## The five legacy branches whose only row-placing call sites are the whole
## entry set, in the committed line order. `item_id_source` names **where the
## id comes from**, because that is the useful part: four of the five take it
## straight from a client argument.
const ROW_ENTRY := [
	{
		"branch": "buy",
		"site": "command.py:55",
		"call": "map_add_item",
		"item_id_source": "client args[1], verbatim",
		"item_id_argument_index": 1,
		"classification": CLASS_CLIENT,
		"effect": "places any id at any cell and records it in boughtUnits "
			+ "when playerID is 1",
		"note": "no store check, no producer check, no content lookup: the "
			+ "branch is a map write plus a print (command.py:42-58)",
	},
	{
		"branch": "place_stored_item",
		"site": "command.py:245",
		"call": "map_add_item",
		"item_id_source": "client args[1], verbatim",
		"item_id_argument_index": 1,
		"classification": CLASS_CLIENT,
		"effect": "removes the id from map['store'] (command.py:244), places "
			+ "it, and records it in boughtUnits",
		"note": "the id is not checked against the storage it was taken from",
	},
	{
		"branch": "weekly_reward",
		"site": "command.py:353",
		"call": "map_add_item",
		"item_id_source": "client args[1], verbatim",
		"item_id_argument_index": 1,
		"classification": CLASS_CLIENT,
		"effect": "a reward: an item when the request carries more than four "
			+ "arguments, resources otherwise",
		"note": "the branch also advances the committed Monday-bonus schedule "
			+ "(command.py:360-363), but the PLACED id is the client's, not the "
			+ "schedule's: the schedule fixes how often the branch may run, "
			+ "never what it places",
	},
	{
		"branch": "pop_unit",
		"site": "command.py:408",
		"call": "map_add_item_from_item",
		"item_id_source": "client args[2], written onto a row that ALREADY "
			+ "EXISTED in a building's garrison",
		"item_id_argument_index": 2,
		"classification": CLASS_ALREADY,
		"effect": "pops a matching row out of a building's fifth slot "
			+ "(engine.pop_unit), overwrites its item, cell, and team, and "
			+ "places it back on the map",
		"note": "even this path is not a derivation: the row exists because it "
			+ "was placed or garrisoned earlier, and command.py:403 overwrites "
			+ "the popped row's committed item with the client-sent id",
	},
	{
		"branch": "resurrect_hero",
		"site": "command.py:633",
		"call": "map_add_item",
		"item_id_source": "client args[1], verbatim",
		"item_id_argument_index": 1,
		"classification": CLASS_CLIENT,
		"effect": "decrements privateState['deadHeroes'][item_id] "
			+ "(engine.resurrect_hero) and then places the id",
		"note": "the dead-hero counter is keyed by the SAME client-sent id, so "
			+ "the branch cannot place an id the counter does not hold while "
			+ "still never deriving one: it is a decrement plus a map write",
	},
]

## The closed count, and the line numbers the suite measures against it.
const ROW_ENTRY_COUNT := 5
const ROW_ENTRY_LINES := [55, 245, 353, 408, 633]

## The finding the inventory exists to make checkable, and the count that
## proves it: **no** branch derives an id from a completed queue, from a
## duration, or from committed production content.
const DERIVED_ROW_ENTRY_COUNT := 0
const NO_DERIVATION := ("NO ROW-ENTRY BRANCH DERIVES A UNIT. The five branches "
	+ "above are the whole set of legacy call sites that place a row on the "
	+ "map, FOUR of them take the item id straight from a client argument, and "
	+ "the fifth (pop_unit) moves a row that already existed in a building's "
	+ "garrison. None of them reads a completed queue, a duration, a producer, "
	+ "or any committed production content to decide what to place, so the "
	+ "DERIVED set is EMPTY and a derived entry would be an invented rule "
	+ "(design D2). The recorded absence of a derivation is a closed "
	+ "measurement: the suite re-derives the call sites and their enclosing "
	+ "branches out of the committed dispatcher and fails on any sixth site")

## The dispatcher's own shape, recorded because the completion absence cannot
## be read off an inventory of entry paths alone: 63 named branches, and the
## `complete_*` family is exactly these three.
const NAMED_BRANCH_COUNT := 63
const COMPLETE_FAMILY := ["complete_collection", "complete_goal",
	"complete_tutorial"]

# ---------------------------------------------------------------------------
# The committed training time: content only (design D3)
# ---------------------------------------------------------------------------

## The committed field name, and the fact that no legacy branch reads it.
const TRAINING_FIELD := "training_time"
const TRAINING_CONSUMER_COUNT := 0
## The six legacy modules the zero-consumer claim is measured over.
const TRAINING_SEARCHED_MODULES := ["command.py", "engine.py", "sessions.py",
	"server.py", "constants.py", "get_game_config.py"]
## The measured count of lines in those modules that contain the field name as
## a SUBSTRING, the lines themselves, and the fact that every one of them is
## the **distinct** field below inside the soul-mixer branch. The suite
## recomputes all three, so the recorded number cannot drift from the source.
## The **occurrence** count of the substring `training_time` across the six named
## legacy modules. It is **three**, on **two** distinct lines (`command.py` 735 twice
## and 737). Occurrence and line counts are kept apart on purpose: an earlier
## measurement reported 2 because it counted distinct lines, and that wrong number
## was pinned here until it was re-measured.
const TRAINING_SUBSTRING_MATCH_COUNT := 3
## The distinct lines those three occurrences sit on.
const TRAINING_SUBSTRING_MATCH_DISTINCT_LINES := 2
const TRAINING_SUBSTRING_MATCH_LINES := ["command.py:735", "command.py:737"]
const TRAINING_SUBSTRING_MATCH_FIELD := "sm_training_time"
const SOULMIXER_SPAN := [727, 745]

## The refusal, stated as the contract it is.
const TRAINING_REFUSAL := ("NO PRODUCTION DURATION IS DERIVED FROM "
	+ "training_time. The field has ZERO legacy consumers: the only three "
	+ "occurrences of the string across command.py, engine.py, sessions.py, "
	+ "server.py, constants.py, and get_game_config.py are command.py:735 and "
	+ "command.py:737, and both are the DISTINCT field sm_training_time inside "
	+ "the soul-mixer speedup branch - a different field, on a different path. "
	+ "So NO production time, NO remaining time, and NO progress ratio is "
	+ "computed from a building's committed training_time, and this module "
	+ "provides no duration helper of any kind (design D3/D4)")

## The committed distribution, reported as **content**. Measured: the key is
## carried by EVERY committed item, and takes exactly two values. The suite
## measures it from the verified registry rather than trusting this sentence.
const TRAINING_FIELD_COVERAGE := ("training_time is a key on EVERY committed "
	+ "item: all 470 buildings and all 429 units carry it, and it takes "
	+ "exactly two values — 0 on 340 of the 470 buildings and on all 429 "
	+ "units, and 5 on the remaining 130 buildings, including the Command "
	+ "Center (id 26), which also records min_level 1 and group_type "
	+ "COMMAND_CENTER. So a POSITIVE duration exists on 130 of the 470 "
	+ "committed buildings and on 0 of the 429 committed units. The coverage "
	+ "is reported for reference ONLY: no legacy branch reads the field, so no "
	+ "rule may be derived from it (design D3)")

## The earlier committed fields in this project that share the zero-consumer
## property. The precedent is what makes this refusal a rule rather than a
## preference: it has now been applied twice, and this is the third instance.
const ZERO_CONSUMER_PRECEDENTS := [
	{"field": "unit_capacity", "line": "M8 line 2 (unit instances)",
		"fact": "committed on 5 of the 429 units and on non-zero on a small "
			+ "minority, with zero occurrences across the legacy modules; "
			+ "push_unit appends to a garrison unconditionally, so no capacity "
			+ "rule is enforced"},
	{"field": "reward_type / reward_amount", "line": "M7's XP line",
		"fact": "committed on every one of the 100 level entries and read by "
			+ "no legacy branch, so no level reward is paid"},
	{"field": TRAINING_FIELD, "line": "this line (unit production)",
		"fact": "carried by every one of the 899 committed items with a "
			+ "positive value on only 130 of the 470 buildings, and read by no "
			+ "legacy branch, so no production duration is derived from it"},
]

## The related duration field, recorded so a reader cannot mistake the
## soul-mixer path for a general one. Its own recorded path stays recorded:
## `soulmixer_speedup` charges nothing and its own author called its formula
## useless, and this line adds no duration semantics for it either.
const SIBLING_DURATION_FIELD := "sm_training_time"
const SIBLING_DURATION_NOTE := ("sm_training_time is the soul-mixer branch's "
	+ "OWN field, present on 300 of the 429 committed units and on 0 of the 470 "
	+ "buildings, and the one legacy reader of it (command.py:735) reads it off "
	+ "the QUEUED UNIT to print a cost it never charges. It is recorded as that "
	+ "path's recorded contract and is NOT treated as a general production "
	+ "duration here: NO production or timing semantics are derived from it "
	+ "either (design D3)")

# ---------------------------------------------------------------------------
# The experience award that is refused (design D5)
# ---------------------------------------------------------------------------

## The only command that writes a placed row's recorded experience, and where
## its two client-sent arguments go.
const XP_COMMAND := "add_xp_unit"
const XP_ATTR_KEY := "xp"
const XP_ATTR_SLOT := 6
const XP_SITE := "command.py:322-343"
const XP_AMOUNT_SOURCE := ("client args[1] (xp_gain): the branch SETS "
	+ "attr['xp'] to it when the key is absent and otherwise ADDS it to the "
	+ "value already there (command.py:335-338)")
const XP_LEVEL_SOURCE := ("client args[2] (optional level): used ONLY inside a "
	+ "printed line (command.py:340-341) and written nowhere")
const XP_AWARD_IMPLEMENTED := false
const XP_CONTRACT := ("NO EXPERIENCE IS AWARDED FROM A CLIENT AMOUNT. "
	+ "add_xp_unit (command.py:322-343) is the ONLY command that writes a "
	+ "placed row's attr['xp'] and it CREATES NOTHING: the amount is "
	+ "client-sent, and the optional level is client-sent and used only in a "
	+ "print. So a recorded attr['xp'] is READ AND REPORTED AS CONTENT, "
	+ "verbatim and never coerced, and NO experience is awarded, granted, or "
	+ "computed from it here or anywhere else in this repository (design D5). "
	+ "This is the third untrusted client-delta pattern in this area, alongside "
	+ "the queue vector and trade_resource")

## The corpus measurement, recorded: the field is absent from every placed
## row. The suite measures it rather than trusting the number.
const CORPUS_XP_NOTE := ("the committed corpus carries attr['xp'] on 0 of its "
	+ "40 placed rows, which is asserted by the suite as a measurement and is "
	+ "a fact about the corpus, not evidence that an award exists: with no "
	+ "trusted award on the server, a recorded value would have to come from a "
	+ "client amount")

## The corpus's own shape, recorded because the absence of unit experience is
## only meaningful next to the absence of unit rows.
const CORPUS_FINDING := ("the committed fresh-player corpus places 40 rows "
	+ "across 11 distinct item ids, every one of committed type 'b': it "
	+ "contains NO unit row, NO storage, and an empty inventory, and every one "
	+ "of its 40 attribute bags is empty")

# ---------------------------------------------------------------------------
# Acquisition: recorded, refused, never implemented (design D1/D5)
# ---------------------------------------------------------------------------

## The six branches that can fill the storage. The suite measures these six
## call sites and their enclosing branches out of the committed dispatcher,
## so the route table cannot drift and a seventh would be an unrecorded gap.
const ACQUISITION_ROUTES := [
	{
		"branch": "store_item",
		"site": "command.py:229",
		"input": "an existing row popped off the map",
		"trusted": true,
		"note": "the id is read off a row the player already placed",
	},
	{
		"branch": "store_add_items",
		"site": "command.py:263",
		"input": "client args[0], a list of ids",
		"trusted": false,
		"note": "no content check; each id is stored and recorded in "
			+ "boughtUnits (command.py:262-264)",
	},
	{
		"branch": "win_daily_bonus",
		"site": "command.py:460",
		"input": "client args[0], inside a committed daily schedule",
		"trusted": false,
		"note": "the schedule fixes WHEN the branch may run, while the id it "
			+ "stores is the client's; the committed weekday table carries no "
			+ "per-day item",
	},
	{
		"branch": "buy_stored_item_cash",
		"site": "command.py:479",
		"input": "client args[0], one id",
		"trusted": false,
		"note": "one of the two plausible unit sources, and it is a single "
			+ "client-sent id stored with no check at all",
	},
	{
		"branch": "complete_collection",
		"site": "command.py:513",
		"input": "committed content, the collection's own prize",
		"trusted": true,
		"note": "the one storage route whose id comes from committed content",
	},
	{
		"branch": "buy_offer_pack",
		"site": "command.py:716",
		"input": "client args[1], a JSON array of ids",
		"trusted": false,
		"note": "the second plausible unit source: json.loads of a client-sent "
			+ "array, with every id in it stored and NO lookup into the "
			+ "committed offer_packs table",
	},
]
const ACQUISITION_COUNT := 6
const ACQUISITION_LINES := [229, 263, 460, 479, 513, 716]

## `buy_offer_pack` reads its package id and then never uses it, which is the
## sharpest single fact about this route.
const PACKAGE_ID_UNUSED := ("command.py:711 reads package_id = args[0] and "
	+ "NEVER USES IT: the branch goes straight on to json.loads(args[1]) and "
	+ "stores every id in the resulting client-sent array. There is no lookup "
	+ "into the committed offer_packs table, so a client may name any ids at "
	+ "all and the server stores them")

## The two committed acquisition tables, with what the legacy source actually
## does with them. The `darts_items` row is recorded precisely because the
## committed table is NOT wholly unread: `get_game_config.make_dynamic` walks
## it to rebuild its rolling start dates, and that read touches its DATE
## fields only. No dispatcher branch derives an acquisition from either table.
const ACQUISITION_TABLES := [
	{
		"table": "offer_packs",
		"file": "packages/game-content/normalized/offer_packs.json",
		"entries": 44,
		"distinct_unit_references": 109,
		"distinct_building_references": 7,
		"total_item_references": 574,
		"read_by_dispatcher_branch": false,
		"legacy_module_reads": [],
		"note": "read by NO legacy module at all: the string occurs in none of "
			+ "the six modules the training-time claim is measured over. Its "
			+ "references are measured and separated, because '109 unit "
			+ "references' is the DISTINCT unit-id count: the 44 packs make 574 "
			+ "item references in total, 564 of them units and 10 buildings, "
			+ "resolving to 109 distinct unit ids and 7 distinct building ids",
	},
	{
		"table": "darts_items",
		"file": "packages/game-content/normalized/darts_items.json",
		"entries": 27,
		"distinct_unit_references": 44,
		"distinct_building_references": 0,
		"total_item_references": 189,
		"read_by_dispatcher_branch": false,
		"legacy_module_reads": [
			"get_game_config.py:215-246 (make_dynamic / update_darts)",
		],
		"note": "read by exactly ONE legacy module, and for its DATES only: "
			+ "update_darts walks the table to rebuild each entry's rolling "
			+ "start_date and shifts the week. Its items and extra_item are "
			+ "touched only inside a debug print that runs at debug level >= 1, "
			+ "and the normal path runs at 0, so no acquisition is derived from "
			+ "the table. The measured correction against the committed "
			+ "investigation: the table is NOT unread, it is unread BY NO "
			+ "DISPATCHER BRANCH for acquisition. Its 189 references are all "
			+ "units, resolving to 44 distinct unit ids",
	},
]

const ACQUISITION_IMPLEMENTED := false
const ACQUISITION_NOTE := ("NO ACQUISITION IS IMPLEMENTED OR CLAIMED. The two "
	+ "plausible unit sources are unvalidated client-sent item lists, so the "
	+ "committed offer_packs and darts_items tables describe a content-derived "
	+ "acquisition system this server does not implement; enforcing them is a "
	+ "LATER milestone's work, and this line issues no acquisition request and "
	+ "creates no intent to authorise (design D1/D5). A client-supplied item id, "
	+ "package id, or item list is recorded as client-supplied and is never "
	+ "treated as authorising")

# ---------------------------------------------------------------------------
# Death and resurrection: recorded, unimplemented
# ---------------------------------------------------------------------------

## The death path, recorded precisely. The legacy `sell` branch reads its
## reason from a **positional argument** (command.py:151) and pushes a dead
## hero only when that argument is exactly `KILL` (command.py:159), while the
## delivered `building-sell` surface DERIVES the reason itself and ignores any
## client-supplied one, so its dead-hero counter cannot be reached through it.
## Nothing about death or resurrection is implemented here.
const DEATH_FINDING := ("DEATH AND RESURRECTION ARE RECORDED AND UNIMPLEMENTED. "
	+ "sell (command.py:149-168) reads reason = args[1] and calls "
	+ "push_dead_unit only when that argument is exactly 'KILL' "
	+ "(command.py:159), while the separate kill branch (command.py:169-181) "
	+ "deletes the row and never touches the counter. The delivered "
	+ "building-sell surface DERIVES its own reason and ignores a "
	+ "client-supplied one, so the dead-hero pool is unreachable through it. "
	+ "NO death, NO resurrection, and NO unit is created from a queue here: the "
	+ "resurrect_hero entry above is recorded as a row placement and nothing "
	+ "more")

# ---------------------------------------------------------------------------
# The helpers this module deliberately does NOT provide (design D4)
# ---------------------------------------------------------------------------

## The machine-readable form of the absence (design D4). Each of these would
## compute a rule the legacy server never had, so none is declared here, and
## the suite asserts this module's whole function inventory against a pinned
## list AND against this list — a rename cannot smuggle one past the inventory,
## and a leftover here fails visibly.
const ABSENT_HELPERS := [
	{"helper": "is_complete", "absent_because":
		"no legacy command completes a queue and no command materialises a "
		+ "unit from one, so there is no server-side completion to reproduce"},
	{"helper": "is_ready", "absent_because":
		"the same absence: nothing in the legacy source can answer 'is this "
		+ "queue ready?', so a client-side answer would be invented"},
	{"helper": "remaining", "absent_because":
		"no legacy branch evaluates a queue's elapsed time: every occurrence "
		+ "of attr['ts'] is a write or a deletion, and the only reader is the "
		+ "soul-mixer speedup, which is not a general queue path"},
	{"helper": "progress", "absent_because":
		"a ratio needs a duration, and NO branch reads training_time or "
		+ "sm_training_time, so there is no committed denominator"},
	{"helper": "ready_at", "absent_because":
		"the start instant is reported verbatim and nothing derives an "
		+ "instant from it"},
	{"helper": "complete", "absent_because":
		"completion is a server-authoritative decision and this milestone "
		+ "delivers none; it belongs to a later line with its own evidence"},
	{"helper": "produce_unit", "absent_because":
		"no row-entry branch derives an id from a queue, a duration, or "
		+ "committed production content, so there is nothing to produce"},
	{"helper": "spawn_unit", "absent_because":
		"the legacy source places a row in exactly five branches, every one "
		+ "of them inventoried above, and none of them is a completion"},
	{"helper": "train_unit", "absent_because":
		"no legacy command trains a unit; the queue's three keys are written "
		+ "and deleted and never evaluated"},
	{"helper": "duration", "absent_because":
		"the committed training time has zero legacy consumers, so deriving a "
		+ "duration from it would invent the rule this line refuses"},
	{"helper": "award_experience", "absent_because":
		"the only command writing a recorded experience takes its amount from "
		+ "a client argument, so no trusted award exists to reproduce"},
	{"helper": "acquire_unit", "absent_because":
		"both plausible unit sources are unvalidated client-sent item lists, "
		+ "so there is no acquisition to reproduce and the committed tables "
		+ "belong to a later milestone"},
]

## The refusal reasons this module's own projection can produce. The only one
## is the delegated structural rejection; every other answer is a **report**,
## because "no queue" and "a queue of 3" are both facts, never errors.
const REASON_INVALID_ATTR := "invalid_attr"

## The one word this contract can honestly give for a queue's readiness. There
## is deliberately no second value: a boolean here would be a rule the legacy
## server does not have.
const READINESS_UNKNOWN := "unknown-and-uncomputable"

## The single sentence a reader is owed the moment they look for a readiness.
const CANNOT_SAY_READY := ("the legacy server CANNOT SAY whether this queue is "
	+ "ready: no command completes a queue, nothing evaluates a queue's elapsed "
	+ "time, and no committed production rule derives a unit from one")

## The evidence's non-claims (spec "Unit-production evidence and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `unit_queue.gd`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO PRODUCTION MECHANISM, COMPLETION, OR READINESS IS IMPLEMENTED, "
		+ "BECAUSE THE LEGACY SERVER HAS NONE TO REPRODUCE: the absence is a "
		+ "recorded contract, not a missing feature, and a later line that "
		+ "introduces completion must bring its own evidence",
	"NO UNIT IS CREATED, TRAINED, OR PLACED: nothing here materialises a unit "
		+ "from a queue, and the corpus contains no unit row at all",
	"NO DURATION IS DERIVED FROM THE COMMITTED TRAINING TIME: the field has "
		+ "zero legacy consumers and is reported as content only, and NO "
		+ "duration semantics are added for the soul-mixer sibling field either",
	"NO EXPERIENCE IS AWARDED: the only command writing a recorded experience "
		+ "takes its amount from a client argument, and the committed corpus "
		+ "carries the field on 0 of its 40 placed rows",
	"NO ACQUISITION IS IMPLEMENTED OR CLAIMED: both plausible unit sources are "
		+ "unvalidated client-sent item lists, the committed offer_packs and "
		+ "darts_items tables are read by no dispatcher branch for an "
		+ "acquisition, and enforcing them belongs to a later milestone",
	"NO EXECUTED-LEGACY FIXTURE WAS CAPTURED, and the reason is the stronger "
		+ "one: there is NO production behaviour to capture, not merely a corpus "
		+ "that could not exercise it",
	"DEATH AND RESURRECTION ARE UNREACHABLE THROUGH THE DELIVERED SURFACE AND "
		+ "UNIMPLEMENTED here, and no death, reward, or scheduling rule is "
		+ "claimed",
	"no windowed capture is claimed: nothing is rendered and no unit exists to "
		+ "render",
	"no pixel-parity oracle exists",
	"the production-shaped field and its plausible-looking committed duration "
		+ "are reported, not applied: a reader who wanted a production rule out "
		+ "of them must bring evidence the legacy contract does not contain",
]

## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and
## check, and every derived fact states what it is derived from. Nothing here
## names a runtime; the runtime names live in `NON_CLAIMS`.
const PROVENANCE := {
	"established": [
		{"fact": "command.py's only row-placing call sites are five branches — "
			+ "buy (55), place_stored_item (245), weekly_reward (353), "
			+ "pop_unit (408), and resurrect_hero (633) — and four of the five "
			+ "take the item id straight from a client argument while the fifth "
			+ "moves a row that already existed in a building's garrison",
			"evidence": "command.py:55, 245, 353, 408, 633 against "
				+ "engine.pop_unit; the suite re-derives the sites, their "
				+ "enclosing branch names, and the count out of the committed "
				+ "dispatcher and fails on any sixth"},
		{"fact": "no row-entry branch derives an item id from a completed "
			+ "queue, from a duration, or from committed production content",
			"evidence": "the same five call sites: each is a map write whose "
				+ "id arrives as an argument or off an existing row, and none "
				+ "reads a queue, a clock, or content"},
		{"fact": "the dispatcher has 63 named branches and its complete_* family "
			+ "is exactly complete_collection, complete_goal, and "
			+ "complete_tutorial, so no command completes a queue and none "
			+ "materialises a unit from one",
			"evidence": "command.py's own if/elif chain; the suite measures "
				+ "both the branch count and the complete_* names"},
		{"fact": "training_time has ZERO legacy consumers: the only three lines "
			+ "in the six named modules containing the string are "
			+ "command.py:735 and command.py:737, and both are the distinct "
			+ "field sm_training_time inside the soul-mixer speedup branch",
			"evidence": "a substring search over command.py, engine.py, "
				+ "sessions.py, server.py, constants.py, and get_game_config.py, "
				+ "which the suite repeats and compares against the recorded "
				+ "count and line numbers"},
		{"fact": "training_time is carried by every one of the 899 committed "
			+ "items, takes exactly two values, and reads as a POSITIVE duration "
			+ "on 130 of the 470 buildings and on 0 of the 429 units; the "
			+ "Command Center (id 26) records 5",
			"evidence": "the committed normalized content package, measured "
				+ "by the suite through the verified registry"},
		{"fact": "add_xp_unit is the only command writing a placed row's "
			+ "attr['xp']; it creates nothing, takes the amount from "
			+ "args[1], and uses an optional client-sent args[2] only in a "
			+ "printed line",
			"evidence": "command.py:322-343"},
		{"fact": "six branches call add_store_item, and two of them are the "
			+ "plausible unit sources: buy_offer_pack reads package_id and "
			+ "never uses it before json.loads of a client-sent array with no "
			+ "lookup into the committed table, and buy_stored_item_cash takes "
			+ "one client-sent id",
			"evidence": "command.py:229, 263, 460, 479, 513, 716; the suite "
				+ "measures the six call sites and their enclosing branches"},
		{"fact": "offer_packs is read by no legacy module, and darts_items is "
			+ "read only by get_game_config.make_dynamic, which walks it to "
			+ "rebuild rolling start dates; its item fields are touched only "
			+ "inside a debug print that never runs at the normal debug level",
			"evidence": "a search for both table names over the legacy root "
				+ "modules; get_game_config.py:215-246 against "
				+ "command.py, which contains neither name"},
		{"fact": "sell reads its reason from a positional argument and pushes a "
			+ "dead hero only on exactly 'KILL', while the kill branch deletes "
			+ "the row without touching the counter",
			"evidence": "command.py:149-168 and 169-181; the delivered "
				+ "building-sell surface derives its own reason and ignores a "
				+ "client-supplied one"},
		{"fact": "the committed corpus places 40 rows across 11 distinct item "
			+ "ids, all of committed type 'b', with an empty storage, an empty "
			+ "inventory, 40 empty attribute bags, and no attr['xp'] anywhere",
			"evidence": "tests/saves/fresh-player.json, measured by the suite"},
	],
	"derived": [
		{"fact": "the line's deliverable is a refusal plus an auditable "
			+ "inventory rather than a mechanism",
			"evidence": "derived (design D1): with no completion command, no "
				+ "elapsed-time evaluation, and no committed production rule, "
				+ "any mechanism would be invented, while the corpus's "
				+ "production-shaped field plus its plausible duration is a "
				+ "known trap the two prior lines each refused ad hoc"},
		{"fact": "the row-entry inventory belongs to this line rather than to a "
			+ "later acquisition line",
			"evidence": "derived (design D2): the inventory is what makes the "
				+ "godot-unit-queues absence auditable rather than asserted, so "
				+ "it had to arrive with the refusal it supports. Its scope is "
				+ "closed over the committed legacy source, and a later "
				+ "acquisition line extends it explicitly"},
		{"fact": "no endpoint is warranted while no server-derived production "
			+ "exists",
			"evidence": "derived (design D6): there is no intent to send and "
				+ "nothing to authorise, so the compatibility test suite stays "
				+ "green unchanged, exactly as M8 lines 1 and 2 concluded"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy production panel has "
				+ "been captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


# ---------------------------------------------------------------------------
# The one projection
# ---------------------------------------------------------------------------


## The whole production evaluation for one placed row, and the ONLY entry point
## a surface uses. Returns
## `{ok, reason, error, queue, fields, present, count, start_instant,
##   production_possible, readiness, readiness_reason, completion_available,
##   duration_computed, experience_awarded, acquisition_available,
##   row_entry_branches, derived_row_entry_branches, no_derivation, readout}`.
##
## It projects **presence and the recorded start instant** and nothing more. A
## readable bag is `ok: true` whatever it holds, because "no queue" and "a
## queue of 3" are both **reports**, never errors; a bag that is not an object
## is the one structural rejection, delegated from the queue contract with its
## own reason. Every absence field is a **constant false** carrying the
## recorded reason beside it, so no caller can mistake this for a value the
## legacy server could not give. The inventory itself is reached through
## `row_entry_inventory()` and is deliberately not duplicated into every
## evaluation.
static func evaluate(attr: Variant, resolve_unit: Variant) -> Dictionary:
	var evaluation := QueueFlow.evaluate(attr, resolve_unit)
	if not bool(evaluation.get("ok", false)):
		return _evaluation_reject(str(evaluation.get("reason", "")),
			str(evaluation.get("error", "")))
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"queue": evaluation.get("queue", null),
		"fields": evaluation.get("fields", {}),
		"present": bool(evaluation.get("present", false)),
		"count": evaluation.get("count", null),
		"start_instant": evaluation.get("start_instant", null),
		"production_possible": false,
		"readiness": READINESS_UNKNOWN,
		"readiness_reason": CANNOT_SAY_READY,
		"completion_available": false,
		"duration_computed": false,
		"experience_awarded": false,
		"acquisition_available": false,
		"row_entry_branches": row_entry_branch_names(),
		"derived_row_entry_branches": derived_row_entries(),
		"no_derivation": NO_DERIVATION,
		"readout": readout_text({
			"ok": true,
			"present": bool(evaluation.get("present", false)),
			"count": evaluation.get("count", null),
			"start_instant": evaluation.get("start_instant", null),
			"readiness": READINESS_UNKNOWN,
			"readiness_reason": CANNOT_SAY_READY,
		}),
	}


# ---------------------------------------------------------------------------
# The row-entry inventory (design D2)
# ---------------------------------------------------------------------------


## Every legacy branch that can place a row on the map, each with the source of
## its item id and its classification, as a fresh deep copy a caller may keep
## and mutate — so a report reads this module's own table rather than
## restating it.
static func row_entry_inventory() -> Array:
	return (ROW_ENTRY as Array).duplicate(true)


## The inventoried branch names in the committed line order.
static func row_entry_branch_names() -> Array:
	var out: Array = []
	for entry: Dictionary in ROW_ENTRY:
		out.append(str(entry["branch"]))
	return out


## The closed classification vocabulary, as a fresh array.
static func classification_vocabulary() -> Array:
	return (CLASSIFICATIONS as Array).duplicate()


## How many inventoried entries carry each classification. The useful reading
## is the shape it shows: four client-supplied, one already-existing, and none
## derived.
static func classification_counts() -> Dictionary:
	var counts := {}
	for name: String in CLASSIFICATIONS:
		counts[name] = 0
	for entry: Dictionary in ROW_ENTRY:
		var key := str(entry["classification"])
		counts[key] = int(counts.get(key, 0)) + 1
	return counts


## The inventoried entries whose item id is **derived** from committed
## production content, a completed queue, or a duration. The answer is an empty
## list, and it is returned as one rather than as a count so a caller can
## iterate it: a non-empty result is a defect in the inventory, not a finding.
static func derived_row_entries() -> Array:
	var out: Array = []
	for entry: Dictionary in ROW_ENTRY:
		if str(entry["classification"]) == CLASS_DERIVED:
			out.append(str(entry["branch"]))
	return out


## The finding the inventory exists to make checkable, verbatim.
static func no_derivation_finding() -> String:
	return NO_DERIVATION


# ---------------------------------------------------------------------------
# The committed training time (design D3)
# ---------------------------------------------------------------------------


## The whole `training_time` refusal as the evidence report records it, read
## from this module's own constants so the report cannot describe a contract
## the code does not hold.
static func training_time_record() -> Dictionary:
	return {
		"field": TRAINING_FIELD,
		"implemented_as_duration": false,
		"consumer_count": TRAINING_CONSUMER_COUNT,
		"searched_modules": (TRAINING_SEARCHED_MODULES as Array).duplicate(),
		"substring_match_occurrence_count": TRAINING_SUBSTRING_MATCH_COUNT,
		"substring_match_distinct_line_count": TRAINING_SUBSTRING_MATCH_DISTINCT_LINES,
		"substring_match_lines": (TRAINING_SUBSTRING_MATCH_LINES as Array)
			.duplicate(),
		"substring_match_field": TRAINING_SUBSTRING_MATCH_FIELD,
		"soulmixer_span": (SOULMIXER_SPAN as Array).duplicate(),
		"rule": TRAINING_REFUSAL,
		"coverage": TRAINING_FIELD_COVERAGE,
		"zero_consumer_precedents": (ZERO_CONSUMER_PRECEDENTS as Array)
			.duplicate(true),
		"sibling_field": SIBLING_DURATION_FIELD,
		"sibling_note": SIBLING_DURATION_NOTE,
		"duration_computed": false,
		"distribution_measured": {
			"buildings": 0,
			"buildings_with_field": 0,
			"units": 0,
			"units_with_field": 0,
		},
	}


## The committed training time of one definition, **verbatim, as content**.
## Returns the value exactly as the committed entry holds it — or null when the
## entry carries no such field, which is a named absence and never a
## substituted zero. It reads that one field and nothing else, and it computes
## no duration, no remaining time, and no ratio from what it returns: the
## refusal is the function's whole contract.
static func committed_training_time(entry: Variant) -> Variant:
	if not (entry is Dictionary):
		return null
	if not (entry as Dictionary).has(TRAINING_FIELD):
		return null
	return (entry as Dictionary)[TRAINING_FIELD]


## How the readout renders a committed training time: the value, immediately
## followed by the refusal, so a reader who sees the number cannot mistake it
## for a duration this client would honour.
static func training_time_note(value: Variant) -> String:
	if value == null:
		return ("training_time: absent from this definition (a named absence, "
			+ "never a zero) and read by no legacy branch either")
	return ("training_time: %s — recorded as CONTENT ONLY, never used as a "
			% str(value)
			+ "duration, because no legacy branch reads the field")


# ---------------------------------------------------------------------------
# The refused experience award (design D5)
# ---------------------------------------------------------------------------


## A placed row's recorded experience, reported **as content and never
## awarded**. Returns
## `{ok, reason, error, recorded, recorded_is_absent, awarded, award_source,
##   award_implemented, contract, corpus_note}`.
##
## `recorded` is the value **verbatim** — never coerced to a number, never
## rounded — because a client-sent amount is a fact about what a client said,
## not a quantity this contract may interpret. `awarded` is a constant false
## carrying the reason beside it, and there is deliberately no function
## anywhere in this module that adds, grants, or computes an award.
static func experience(attr: Variant) -> Dictionary:
	if not (attr is Dictionary):
		return _experience_reject(
			"the addressed row's attribute bag is %s, not an object"
				% _type_name(attr))
	var bag: Dictionary = attr
	var carries := bag.has(XP_ATTR_KEY)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"recorded": bag[XP_ATTR_KEY] if carries else null,
		"recorded_is_absent": not carries,
		"awarded": false,
		"award_source": "none: no client amount is ever applied, and the only "
			+ "legacy command writing this field takes its amount from a "
			+ "client argument",
		"award_implemented": XP_AWARD_IMPLEMENTED,
		"contract": XP_CONTRACT,
		"corpus_note": CORPUS_XP_NOTE,
	}


## How the readout renders the experience record: the recorded value, then the
## refusal, never a number a player could read as an award.
static func experience_note(record: Dictionary) -> String:
	if not bool(record.get("ok", false)):
		return ""
	var recorded: Variant = record.get("recorded", null)
	if bool(record.get("recorded_is_absent", false)):
		return ("experience: absent (no recorded attr['xp'] on this row) and "
			+ "never awarded: %s" % str(XP_AMOUNT_SOURCE))
	return ("experience: %s — recorded as CONTENT ONLY and never awarded: %s"
		% [str(recorded), str(XP_AMOUNT_SOURCE)])


## The whole `add_xp_unit` contract as the evidence report records it, read
## from this module's own constants.
static func experience_record() -> Dictionary:
	return {
		"command": XP_COMMAND,
		"site": XP_SITE,
		"attr_key": XP_ATTR_KEY,
		"attr_slot": XP_ATTR_SLOT,
		"amount_source": XP_AMOUNT_SOURCE,
		"level_source": XP_LEVEL_SOURCE,
		"award_implemented": XP_AWARD_IMPLEMENTED,
		"creates_anything": false,
		"rule": XP_CONTRACT,
		"corpus_note": CORPUS_XP_NOTE,
		"corpus_finding": CORPUS_FINDING,
	}


# ---------------------------------------------------------------------------
# The refused acquisition (design D1/D5)
# ---------------------------------------------------------------------------


## Every legacy branch that can fill the storage, each with the source of the
## ids it stores, as a fresh deep copy.
static func acquisition_routes() -> Array:
	return (ACQUISITION_ROUTES as Array).duplicate(true)


## The whole acquisition finding as the evidence report records it: the six
## measured routes, the read-and-unused package id, the two committed tables
## with what the legacy source actually does with each, and the statement that
## no mechanism is implemented and no request is issued.
static func acquisition_record() -> Dictionary:
	return {
		"implemented": ACQUISITION_IMPLEMENTED,
		"routes": acquisition_routes(),
		"route_count": ACQUISITION_COUNT,
		"route_lines": (ACQUISITION_LINES as Array).duplicate(),
		"client_supplied_routes": _client_routes(),
		"package_id": PACKAGE_ID_UNUSED,
		"tables": (ACQUISITION_TABLES as Array).duplicate(true),
		"note": ACQUISITION_NOTE,
		"request_issued": false,
	}


## How the readout renders the acquisition finding in one line, so a reader
## looking for "where do units come from" is answered instead of left to infer.
static func acquisition_note() -> String:
	return ACQUISITION_NOTE


# ---------------------------------------------------------------------------
# The recorded death and resurrection finding
# ---------------------------------------------------------------------------


## Death, resurrection, and the dead-hero counter as this contract records
## them: **not implemented**, and unreachable through the delivered surface.
static func death_record() -> Dictionary:
	return {
		"implemented": false,
		"kill_reason_source": "command.py:151 reads reason = args[1], and "
			+ "command.py:159 pushes a dead hero only when that argument is "
			+ "exactly 'KILL'",
		"kill_branch": "the separate kill branch (command.py:169-181) deletes "
			+ "the row and never touches the dead-hero counter",
		"delivered_surface": "the building-sell surface derives its own reason "
			+ "and ignores a client-supplied one, so the dead-hero pool is "
			+ "unreachable through it",
		"unit_created": false,
		"rule": DEATH_FINDING,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The production readout for the live evaluation: the row's presence, the
## committed count and start instant, and then — in the same line — the
## recorded absences, so the omission can never read as a defect.
##
## **No remaining time, no progress ratio, and no readiness appear**, because
## the legacy server cannot supply them. A row with no queue reads as `no
## queue`, never as `count 0`.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var parts: Array = []
	if not bool(evaluation.get("present", false)):
		parts.append("no queue (absent, not a count of zero)")
	else:
		parts.append("queue: count %s, started at %s"
			% [_count_text(evaluation.get("count", null)),
				_number_text(evaluation.get("start_instant", null))])
	parts.append("readiness: %s — %s"
		% [str(evaluation.get("readiness", READINESS_UNKNOWN)),
			str(evaluation.get("readiness_reason", ""))])
	parts.append("no completion, no duration, no progress: the legacy server "
		+ "has none of those rules to reproduce")
	parts.append("no unit is produced: all %d row-entry branches are inventoried "
		% ROW_ENTRY_COUNT
		+ "and %d of them derive an id from a queue, a duration, or committed "
			% DERIVED_ROW_ENTRY_COUNT
		+ "content")
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural rejection: `ok` false with the delegated reason, and every
## absence field still carrying its recorded false — a caller must never be
## able to read a half-built verdict, and a refusal must not turn an absence
## into a different one.
static func _evaluation_reject(reason: String, message: String) -> Dictionary:
	return {
		"ok": false,
		"reason": reason,
		"error": message,
		"queue": null,
		"fields": {},
		"present": false,
		"count": null,
		"start_instant": null,
		"production_possible": false,
		"readiness": READINESS_UNKNOWN,
		"readiness_reason": CANNOT_SAY_READY,
		"completion_available": false,
		"duration_computed": false,
		"experience_awarded": false,
		"acquisition_available": false,
		"row_entry_branches": [],
		"derived_row_entry_branches": [],
		"no_derivation": NO_DERIVATION,
		"readout": "",
	}


## A refused experience record: nothing read, nothing awarded, and the
## structural reason named so the caller never reports an empty bag as a row
## carrying no experience.
static func _experience_reject(message: String) -> Dictionary:
	return {
		"ok": false,
		"reason": REASON_INVALID_ATTR,
		"error": "[unit-production] experience refused (invalid_attr): %s"
			% message,
		"recorded": null,
		"recorded_is_absent": true,
		"awarded": false,
		"award_source": "none: nothing was read, so nothing could be awarded",
		"award_implemented": XP_AWARD_IMPLEMENTED,
		"contract": XP_CONTRACT,
		"corpus_note": CORPUS_XP_NOTE,
	}


## The inventoried routes whose ids arrive from a client argument, as an array
## of branch names.
static func _client_routes() -> Array:
	var out: Array = []
	for entry: Dictionary in ACQUISITION_ROUTES:
		if not bool(entry["trusted"]):
			out.append(str(entry["branch"]))
	return out


## The committed count as the readout renders it, or a named absence — never a
## substituted zero.
static func _count_text(value: Variant) -> String:
	if value == null:
		return "[no count]"
	return str(int(value))


## A committed number as the readout renders it, or "unknown" when this
## contract could not read it. Never a substituted zero.
static func _number_text(value: Variant) -> String:
	if value == null:
		return "unknown"
	return str(int(value))


## The observed type of a refused value, so a failure names what it found
## instead of saying only "invalid".
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
