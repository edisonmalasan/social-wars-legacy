extends RefCounted
## Pure evaluation, inventory, and refusals for the unit-collection flow
## (OpenSpec `godot-unit-collection` "One route is content-derived and the rest
## are client-supplied" / "Collection eligibility is not checked, and that gap
## is recorded" / "No unit income, no cap semantics, and no experience award" /
## "The completion intent carries only an identifier" / "Unit-collection evidence
## and claim limits", design D1-D7).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy server **can** grant a committed prize, so this line is not a bare
## refusal like `production_flow.gd`.  What it delivers is the **projection**
## (`collection_prize.gd`, **delegated** and never re-derived), the
## **acquisition-path inventory** with each route classified, the **two authority
## gaps** recorded as content, and **three refusals** stated as contract.  It
## provides **no** payout helper, **no** cap helper, and **no** experience-award
## helper, and `ABSENT_HELPERS` names each one that does not exist together with
## the legacy fact that makes its absence mandatory.  The suite asserts this
## module's **whole function inventory** against a pinned list, so any of them
## fails the delivered suite wherever it is added.
##
## ## Every acquisition route, with its CLASSIFICATION (D4)
##
## `ACQUISITION_ROUTES` records each route that can put an id into the storage or
## onto the map, with the **source of that id** and an explicit
## `content-derived` / `client-supplied` / `already-existing` classification.
## **`complete_collection` is the sole `content-derived` route** — the only
## legacy branch whose stored ids come out of committed content — and that is
## the fact that **completes** the delivered `godot-unit-production` acquisition
## finding rather than amending it: a committed unit IS obtainable, and only
## through this one route.  The suite measures the recorded call sites out of the
## committed legacy dispatcher, so the inventory cannot drift from the source and
## an unrecorded site would be reported as a gap rather than ignored.
##
## No client-supplied route is implemented and **no request is issued** for any
## of them: `request_issued` is a constant `false`, and the recorded routes are
## inventory, not intent.
##
## ## The two authority gaps are RECORDED, not fixed (D2)
##
## Nothing in the legacy source verifies that a collection was earned: the
## committed `item_ids` requirement list is read by **no** branch at all, and the
## ledger is read only to decide whether to append.  So a caller may name **any**
## of the ten committed collections.  The one-based index additionally makes
## **ids 0 and 1 alias**.  Both are stated as **legacy-contract facts** and
## neither is smoothed over: adding an eligibility check would invent a rule the
## legacy server does not have — the same refusal this project applied to
## `unit_capacity`, `training_time`, and the level curve's reward fields — and
## authoritative validation belongs to a later server-authoritative milestone.
##
## ## The three refusals, each with its recorded reason (D5)
##
## **No unit income**: no committed unit records a positive `collect` (0 of 429,
## against 51 of the 470 buildings) and **no** collect field is read by the legacy
## server — the `collect` command re-stamps the row's slot-3 instant and does
## nothing else.  **No cap semantics**: `max_collects` is `0` on **all 429** units,
## so the cap `building-collect` deliberately refused has **no unit analogue** and
## there is no threshold to interpret.  **No experience award**: `collect_xp` is
## never read and the only command writing a placed row's `attr["xp"]` takes a
## **client-sent** amount, which the delivered `godot-unit-production` requirement
## already refuses — a collection must not reopen it.
##
## ## `harvester` is NOT a committed field (the measured correction)
##
## The committed investigation recorded "the 5 harvester units".  Measured, the
## string `harvester` is **not a committed item field at all**: it occurs five
## times in the stored configuration and every one of them is a flag key inside a
## committed `properties` blob — units `1001` Worker I, `1039` Worker II, `1040`
## Worker III, `1041` Worker IV, `1125` Orc Worker — all five recording `collect`
## `0`, and it has zero occurrences in the legacy source besides.  The
## "disjoint from any positive collect" conclusion survives; the framing as a
## field with a value does not.
##
## ## Purity
##
## This module holds no node, no clock, no request, and no transport, and it
## preloads **only** the read-only `collection_prize.gd` projection: every
## committed number it reports arrives as a parameter, so the same functions
## serve the town view, the hermetic suite, and the deterministic report.

const CollectionPrize = preload("res://scripts/units/collection_prize.gd")

# ---------------------------------------------------------------------------
# The acquisition inventory (design D4)
# ---------------------------------------------------------------------------

## The closed classification vocabulary.  There is deliberately no fourth
## heading: an id whose source cannot be named is not inventoried at all rather
## than filed under a vague label.
const CLASS_CONTENT := "content-derived"
const CLASS_CLIENT := "client-supplied"
const CLASS_EXISTING := "already-existing"
const CLASSIFICATIONS := [CLASS_CONTENT, CLASS_CLIENT, CLASS_EXISTING]

## The command this line's route derives, named once so the inventory, the
## projection, and the endpoint cannot disagree about it.
const COMPLETE_COMMAND := "complete_collection"

## Every legacy branch that can put an item id into the storage or onto the map,
## with **where that id comes from**, in the committed line order.  The suite
## re-derives these call sites and their enclosing branches out of the committed
## dispatcher and fails on any unrecorded site.
const ACQUISITION_ROUTES := [
	{
		"branch": "store_item",
		"site": "command.py:229",
		"call": "add_store_item",
		"input": "an existing row popped off the map",
		"classification": CLASS_EXISTING,
		"implemented": false,
		"note": "the id is read off a row the player already placed, so it is "
			+ "already-owned rather than granted",
	},
	{
		"branch": "store_add_items",
		"site": "command.py:263",
		"call": "add_store_item",
		"input": "client args[0], a list of ids",
		"classification": CLASS_CLIENT,
		"implemented": false,
		"note": "no content check; each id is stored and recorded in boughtUnits",
	},
	{
		"branch": "win_daily_bonus",
		"site": "command.py:460",
		"call": "add_store_item",
		"input": "client args[0], inside a committed daily schedule",
		"classification": CLASS_CLIENT,
		"implemented": false,
		"note": "the schedule fixes WHEN the branch may run; the id it stores is "
			+ "the client's, and the committed weekday table carries no per-day item",
	},
	{
		"branch": "buy_stored_item_cash",
		"site": "command.py:479",
		"call": "add_store_item",
		"input": "client args[0], one id",
		"classification": CLASS_CLIENT,
		"implemented": false,
		"note": "one of the two plausible unit sources, and a single client-sent "
			+ "id stored with no check at all",
	},
	{
		"branch": COMPLETE_COMMAND,
		"site": "command.py:513",
		"call": "add_store_item",
		"input": "committed content: the collection's own `prize` bag",
		"classification": CLASS_CONTENT,
		"implemented": true,
		"note": "THE ONLY content-derived route: the branch stores every entry of "
			+ "`json.loads(collections[max(0, collection - 1)]['prize'])`, so the "
			+ "server decides what the caller receives. This line implements this "
			+ "route and no other",
	},
	{
		"branch": "buy_offer_pack",
		"site": "command.py:716",
		"call": "add_store_item",
		"input": "client args[1], a JSON array of ids",
		"classification": CLASS_CLIENT,
		"implemented": false,
		"note": "the second plausible unit source: json.loads of a client-sent "
			+ "array, with every id in it stored and NO lookup into the committed "
			+ "offer_packs table",
	},
]

## The command this line's route derives, named once so the inventory, the
## projection, and the endpoint cannot disagree about it.

## The closed count, and the line numbers the suite measures against it.
const ACQUISITION_ROUTE_COUNT := 6
const ACQUISITION_ROUTE_LINES := [229, 263, 460, 479, 513, 716]

## The finding the inventory exists to make checkable, and the count that proves
## it: **exactly one** route is content-derived.
const CONTENT_DERIVED_ROUTE_COUNT := 1
const NO_DERIVATION := ("EXACTLY ONE ACQUISITION ROUTE IS CONTENT-DERIVED AND IT "
	+ "IS complete_collection. Of the six branches that can put an id into the "
	+ "storage, FOUR take the id straight from a client argument and one moves an "
	+ "id off a row the player already placed; only complete_collection stores ids "
	+ "that come out of committed content, because its grant is "
	+ "`json.loads(collections[max(0, collection - 1)]['prize'])`. So a committed "
	+ "unit IS obtainable, and only through this one route. That COMPLETES the "
	+ "delivered godot-unit-production acquisition finding rather than amending "
	+ "it: the two client-supplied unit sources it recorded remain unusable, and "
	+ "the content-derived route it did not find is named here (design D4)")

## The recorded absence, and the reason the gap is named rather than fixed.
const NO_ELIGIBILITY_CHECK := ("NO COLLECTION ELIGIBILITY IS CHECKED, BY THE "
	+ "LEGACY SERVER OR BY THIS CLIENT. The committed lookup clamps the index and "
	+ "bounds-checks it against the committed table, and the completion branch "
	+ "never looks at the caller's collection state: the only read of "
	+ "privateState['collections'] in the whole legacy source is the "
	+ "append-if-absent test, and the committed `item_ids` requirement list is "
	+ "read by NO branch at all. A caller may therefore name ANY of the ten "
	+ "committed collections and receives whatever that collection genuinely "
	+ "grants. Adding a check would invent a rule the legacy server does not have "
	+ "(design D2) — the same refusal this project applied to unit_capacity, "
	+ "training_time, and the level curve's reward fields — and authoritative "
	+ "validation belongs to a later server-authoritative milestone. What a caller "
	+ "CANNOT do is choose the contents")

## The second authority gap, reported rather than absorbed.
const INDEX_ALIAS_GAP := ("THE INDEX ALIAS IS A SECOND AUTHORITY GAP, REPORTED "
	+ "NOT HIDDEN. The legacy lookup's `max(0, collection - 1)` clamp means "
	+ "COLLECTION ID 0 AND COLLECTION ID 1 RESOLVE TO THE SAME PRIZE, as does "
	+ "every negative id. The grant CONTENTS stay content-derived even through the "
	+ "alias, because a clamped id selects a genuine committed row rather than "
	+ "manufacturing one; what the alias adds is a second spelling for a "
	+ "collection the caller did not name. The projection reports `clamped`, "
	+ "`aliased`, and `alias_of` on every answer so no caller can present id 0 as "
	+ "a distinct collection")

## The two authority gaps as one machine-readable list, in the order the delta's
## requirement names them.
const AUTHORITY_GAPS := [
	{"gap": "no_eligibility_check", "fixed": false, "rule": NO_ELIGIBILITY_CHECK},
	{"gap": "index_alias", "fixed": false, "rule": INDEX_ALIAS_GAP},
]

# ---------------------------------------------------------------------------
# The three refusals (design D5)
# ---------------------------------------------------------------------------

## No unit income is derived, because none is derivable.
const NO_UNIT_INCOME := ("NO UNIT INCOME AND NO COLLECTION PAYOUT ARE DERIVED. "
	+ "The legacy `collect` command is field-agnostic: the whole branch looks the "
	+ "row up, stamps item[3] with the wall clock, prints a name, and writes "
	+ "NOTHING else — it never reads the item's collect, collect_type, "
	+ "collect_xp, max_collects, max_elem_vol, or harvester. Measured across the "
	+ "ten legacy root modules, collect_type, collect_xp, max_collects, "
	+ "max_elem_vol, and harvester have ZERO occurrences and the single quoted "
	+ "\"collect\" is the BRANCH NAME, never a field read — so all five committed "
	+ "collect fields have zero legacy consumers. On the content side there is "
	+ "nothing to derive either: 0 of 429 committed units record a positive "
	+ "`collect` (every one of them records 0), against 51 of the 470 committed "
	+ "buildings. So this contract computes NO income, NO payout, and NO "
	+ "collection reward for a unit, and provides no payout helper of any kind")

## No cap semantics are interpreted, because none exist on a unit.
const NO_CAP_SEMANTICS := ("NO UNIT COLLECTION CAP IS INTERPRETED. "
	+ "`max_collects` is 0 on ALL 429 committed units, so there is NO committed "
	+ "unit cap to interpret at all: the cap the delivered building-collect line "
	+ "deliberately REFUSED — a non-zero committed cap, because nothing in the "
	+ "repository says whether it limits one collection, a daily total, or a "
	+ "building's lifetime output — has NO UNIT ANALOGUE. On buildings the field "
	+ "takes exactly three values (0 on 459, 25 on 9, 100 on 2) and is read by no "
	+ "branch either. The recorded ABSENCE is stated as an absence and never read "
	+ "as permission to set a threshold (design D5)")

## No experience is awarded, because no trusted award exists to reproduce.
const NO_EXPERIENCE_AWARD := ("NO EXPERIENCE IS AWARDED, GRANTED, OR COMPUTED. "
	+ "`collect_xp` is never read: it is non-zero on 427 of the 429 committed "
	+ "units (0 on 2, 1 on 37, 2 on 159, 3 on 211, 4 on 8, 5 on 12), and the only "
	+ "command that writes a placed row's attr['xp'] is `add_xp_unit`, which "
	+ "creates nothing and takes its amount from a CLIENT ARGUMENT — already "
	+ "refused by the delivered godot-unit-production requirement. A collection "
	+ "completion does not reopen that refusal, and the committed corpus carries "
	+ "attr['xp'] on 0 of its 40 placed rows (design D5)")

## The measured correction to the committed investigation's `harvester` figure.
const HARVESTER_RECORD := ("harvester is NOT A COMMITTED CONTENT FIELD AT ALL. "
	+ "The string occurs exactly FIVE times in the stored configuration and every "
	+ "one of them is a flag key inside a committed `properties` blob, never a "
	+ "field of its own: unit 1001 Worker I, 1039 Worker II, 1040 Worker III, "
	+ "1041 Worker IV, and 1125 Orc Worker. All five record `collect` 0, so the "
	+ "'harvester' set is disjoint from any positive collect amount — and it is "
	+ "also disjoint from the legacy source, which contains ZERO occurrences of "
	+ "the string outside the committed configuration itself. This CORRECTS the "
	+ "committed investigation's framing of harvester as a committed item field "
	+ "carrying a positive value on five units")

## The three refusals as one machine-readable list, in the order the delta names
## them.
const REFUSALS := [
	{"refusal": "unit_income", "implemented": false, "rule": NO_UNIT_INCOME},
	{"refusal": "cap_semantics", "implemented": false, "rule": NO_CAP_SEMANTICS},
	{"refusal": "experience_award", "implemented": false,
		"rule": NO_EXPERIENCE_AWARD},
]

## The committed collect fields, with their measured legacy-read count and
## per-domain positive count.  These are reported as **content** and applied as
## **no** rule, because a reader who wants a payout out of them must bring
## evidence the legacy contract does not contain.  The suite re-measures every
## figure from the verified registry and the committed legacy source.
const COLLECT_FIELDS := [
	{"field": "collect", "legacy_reads": 0, "units_positive": 0, "units_of": 429,
		"units_carried": 429, "buildings_positive": 51, "buildings_of": 470,
		"buildings_carried": 470,
		"note": "the only quoted \"collect\" in the legacy source is the BRANCH "
			+ "NAME; there is no [\"collect\"] subscript and no .get(\"collect\") "
			+ "anywhere"},
	{"field": "collect_type", "legacy_reads": 0, "units_positive": 0,
		"units_of": 429, "units_carried": 429, "buildings_positive": 0,
		"buildings_of": 470, "buildings_carried": 470,
		"note": "the ONE committed collect field that is not a number: it reads as a resource letter (`g` on 427 of the 429 units and 425 of the 470 "
			+ "buildings, with w/o/s/c on the rest), so it is measured by how many "
			+ "entries CARRY it rather than by a positive count. That it looks "
			+ "exactly like a rule and has no consumer at all is the point"},
	{"field": "collect_xp", "legacy_reads": 0, "units_positive": 427,
		"units_of": 429, "units_carried": 429, "buildings_positive": 53,
		"buildings_of": 470, "buildings_carried": 470,
		"note": "carried by every committed item and non-zero on 427 units and "
			+ "53 buildings, and never read by any branch"},
	{"field": "max_collects", "legacy_reads": 0, "units_positive": 0,
		"units_of": 429, "units_carried": 429, "buildings_positive": 11,
		"buildings_of": 470, "buildings_carried": 470,
		"note": "0 on every unit and on 459 of the 470 buildings (25 on 9, 100 on "
			+ "2); the non-zero building values are the caps building-collect "
			+ "refuses to interpret"},
	{"field": "max_elem_vol", "legacy_reads": 0, "units_positive": 5,
		"units_of": 429, "units_carried": 429, "buildings_positive": 39,
		"buildings_of": 470, "buildings_carried": 470},
]

## The earlier committed fields in this project that share the zero-consumer
## property.  The precedent is what makes this refusal a rule rather than a
## preference: it has now been applied three times.
const ZERO_CONSUMER_PRECEDENTS := [
	{"field": "unit_capacity", "line": "M8 line 2 (unit instances)",
		"fact": "committed on 5 of the 429 units and read by no legacy branch, "
			+ "so no capacity rule is enforced"},
	{"field": "reward_type / reward_amount", "line": "M7's XP line",
		"fact": "committed on every one of the 100 level entries and read by no "
			+ "legacy branch, so no level reward is paid"},
	{"field": "training_time", "line": "M8 line 4 (unit production)",
		"fact": "carried by every one of the 899 committed items and read by no "
			+ "legacy branch, so no production duration is derived from it"},
]

## The two different "collection" concepts, kept apart on purpose.
const NOT_ACQUISITION := ("`unit_collections_completed` only APPENDS an id to "
	+ "privateState['unitCollectionsCompleted'] and grants NOTHING, so it is a "
	+ "unit COLLECTION TRACKER, a different concept from the `collections` table "
	+ "this line completes, and it is not an acquisition route. The committed "
	+ "unit_collection_categories table (20 rows) is read by no branch either, "
	+ "and `collect_mission` writes idCurrentMission and a timestamp and is "
	+ "unrelated to items")

## The stored-item placement step, recorded and **not** delivered (design D6).
const STORED_ITEM_FOLLOW_UP := ("THE STORED-ITEM PLACEMENT STEP IS NOT "
	+ "DELIVERED HERE. complete_collection -> map['store'] -> place_stored_item "
	+ "is a two-step, fully committed, server-derived path by which a unit enters "
	+ "a town, and this line records and delivers ONLY the first step. The round "
	+ "trip is a SEPARATE carried follow-up, so the executed-legacy fixture "
	+ "evidences a committed GRANT INTO STORAGE and NOT a unit placed on the map: "
	+ "the placement count is unchanged at 40 and no map row is written (design "
	+ "D6). Nothing in this repository places a granted unit")

## The committed corpus measurement, recorded because the "observable write"
## claim depends on it.
const CORPUS_FINDING := ("the committed fresh-player corpus records "
	+ "maps[0]['store'] == {} and privateState['collections'] == [], so a "
	+ "completion WRITES the committed prize and APPENDS the id — a real, "
	+ "observable, content-derived mutation with NO fabricated player state. It "
	+ "places 40 rows across 11 distinct item ids, every one of committed type "
	+ "'b', so it contains NO unit row, and all 40 attribute bags are empty")

# ---------------------------------------------------------------------------
# The completion intent (design D1)
# ---------------------------------------------------------------------------

## The wire contract of the completion intent: **only** a player identifier and
## a collection id.  There is deliberately no parameter through which a client
## could dictate a prize, an item id, a quantity, or a price.
const INTENT_KEYS := ["user_id", "collection_id"]
const INTENT_IGNORED_KEYS := [
	"prize", "item_id", "quantity", "item", "grant", "cost", "price",
	"cashPrice", "resources_changed", "vector", "resources",
]
const INTENT_NOTE := ("THE COMPLETION INTENT CARRIES ONLY AN IDENTIFIER. The "
	+ "request is {user_id, collection_id} and nothing else: no prize, item id, "
	+ "quantity, price, or resource delta is accepted, and every such key is "
	+ "IGNORED by the service. The grant is looked up in the committed "
	+ "collections table, so the server decides what the caller receives and a "
	+ "client-supplied expectation can never become the post-execution proof "
	+ "(design D1)")

## The post-execution proof, as the client records it.
const PROOF_NOTE := ("THE POST-EXECUTION PROOF IS CONTENT-DERIVED, which is what "
	+ "makes it non-tautological. The granted id AND quantity are compared with "
	+ "the COMMITTED prize bag and no other stored key may move, while the "
	+ "collection ledger must match the derived one — exactly one appended id "
	+ "when the id was absent, or NOTHING appended when it was already there, "
	+ "because the legacy append is IF-ABSENT. Every stored resource is "
	+ "unchanged as well, because the derived vector is neutral. Either half "
	+ "failing is a reported failure, not a success")

# ---------------------------------------------------------------------------
# The helpers this module deliberately does NOT provide (design D5)
# ---------------------------------------------------------------------------

## The machine-readable form of the absences.  Each of these would compute a
## rule the legacy server never had, so none is declared here, and the suite
## asserts this module's whole function inventory against a pinned list AND
## against this list — a rename cannot smuggle one past the inventory, and a
## leftover here fails visibly.
const ABSENT_HELPERS := [
	{"helper": "income", "absent_because":
		"the legacy `collect` command re-stamps the row's slot-3 instant and "
		+ "writes nothing else, so it reads no collect field; and 0 of the 429 "
		+ "committed units record a positive `collect`, so there is nothing to "
		+ "derive from the content either"},
	{"helper": "payout", "absent_because":
		"a collection completion has no committed price and no committed income, "
		+ "so any payout would be a figure this repository cannot source"},
	{"helper": "reward", "absent_because":
		"the committed prize IS the grant, and it is already reported verbatim by "
		+ "the projection; a second 'reward' shape would be a second answer"},
	{"helper": "collection_cap", "absent_because":
		"`max_collects` is 0 on all 429 committed units, so the cap "
		+ "building-collect refuses has no unit analogue and inventing one would "
		+ "fabricate a threshold"},
	{"helper": "limit", "absent_because":
		"no legacy branch bounds a collection, a grant, or a ledger, and a "
		+ "recorded absence is not permission to add one"},
	{"helper": "threshold", "absent_because":
		"no committed unit cap exists, so there is no committed threshold to "
		+ "read; the delivered building-collect ladder belongs to that capability"},
	{"helper": "experience_award", "absent_because":
		"`collect_xp` is never read and the only command writing a placed row's "
		+ "attr['xp'] takes a client-sent amount, already refused by the "
		+ "godot-unit-production requirement"},
	{"helper": "grant_xp", "absent_because":
		"the same absence as experience_award: a collection must not reopen a "
		+ "refusal an earlier capability established"},
	{"helper": "eligible", "absent_because":
		"the legacy server verifies NOTHING about whether a collection was "
		+ "earned, and adding a check would invent a rule it does not have "
		+ "(design D2)"},
	{"helper": "check_eligibility", "absent_because":
		"the same absence as eligible; the gap is RECORDED in AUTHORITY_GAPS "
		+ "instead"},
	{"helper": "place_stored_item", "absent_because":
		"the stored-item round trip is a SEPARATE carried follow-up, so this line "
		+ "records the grant and places nothing (design D6)"},
]

## The evidence's non-claims (spec "Unit-collection evidence and claim limits").
## The runtime tokens in the first claim are assembled from fragments for the
## same project-scope reason as in `production_flow.gd`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO UNIT INCOME, COLLECTION PAYOUT, CAP SEMANTICS, OR EXPERIENCE AWARD IS "
		+ "IMPLEMENTED: the legacy server reads no collect field, 0 of 429 units "
		+ "record a positive collect, max_collects is 0 on every unit, and "
		+ "collect_xp is never read",
	"NO COLLECTION ELIGIBILITY IS CHECKED, and a caller may name ANY of the ten "
		+ "committed collections: the committed item_ids requirement list is read "
		+ "by no branch at all, so the gap is recorded rather than fixed",
	"COLLECTION IDS 0 AND 1 ALIAS, as does every negative id: the legacy clamp "
		+ "resolves them all to the same committed prize, and the projection "
		+ "reports that rather than presenting id 0 as distinct",
	"NO CLIENT-SUPPLIED ACQUISITION ROUTE IS IMPLEMENTED and no request is "
		+ "issued for any of them: complete_collection is the sole content-derived "
		+ "route and the only one this line delivers",
	"THE STORED-ITEM PLACEMENT STEP IS NOT DELIVERED, so the fixture evidences a "
		+ "grant into storage and NOT a unit placed on the map",
	"NO UNIT IS PLACED OR GARRISONED by this change: the placement count is "
		+ "unchanged and no map row is written",
	"no windowed capture is claimed: nothing is rendered and no unit is drawn",
	"no pixel-parity oracle against the legacy client exists",
	"the one-based index is derived-provisional and the zero-based alternative is "
		+ "retained; the corpus confirms the one-based reading empirically, and the "
		+ "prize is the committed content, NEVER what the Flash client displayed",
]

## The evidence's provenance split.  Every established fact names the evidence a
## reader can go and check; every derived fact states what it is derived from.
const PROVENANCE := {
	"established": [
		{"fact": "the completion branch grants the committed prize into "
			+ "map['store'] through add_store_item and appends the collection id "
			+ "to privateState['collections'] when it is absent",
			"evidence": "command.py:504-523 against engine.py:70-75 and "
				+ "get_game_config.py:170-175; the executed-legacy fixture records "
				+ "one such transaction"},
		{"fact": "the ten committed collections, their committed names, their "
			+ "committed prizes, and that SIX grant a unit while FOUR grant a "
			+ "building, with ten distinct item ids between them",
			"evidence": "the committed normalized content package, measured by "
				+ "the suite through the verified registry; the executed fixture "
				+ "confirms collection 1's unit 1085 empirically"},
		{"fact": "the one-based index with the legacy clamp: `max(0, collection - "
			+ "1)` against a positional list, so id 0 and every negative id "
			+ "resolve to index 0 and therefore to id 1's prize",
			"evidence": "get_game_config.py:170-175; the suite computes the "
				+ "expression independently over ids -9999..99"},
		{"fact": "no eligibility check exists: the committed `item_ids` "
			+ "requirement list is read by NO branch, and the ledger is read only "
			+ "by the append-if-absent test",
			"evidence": "a search for the quoted token over the ten legacy root "
				+ "modules, plus command.py:517-518; executed-legacy probe 2 "
				+ "completed collection 10 with none of its five items present"},
		{"fact": "the `collect` command re-stamps the row's slot-3 instant and "
			+ "writes nothing else, and collect_type, collect_xp, max_collects, "
			+ "max_elem_vol, and harvester have zero occurrences in the legacy "
			+ "source",
			"evidence": "command.py:136-144; a substring search over the ten "
				+ "legacy root modules, which the suite repeats"},
		{"fact": "0 of 429 committed units record a positive `collect` (against "
			+ "51 of 470 buildings), and max_collects is 0 on all 429 units",
			"evidence": "the committed normalized content package, measured by "
				+ "the suite through the verified registry"},
		{"fact": "collect_xp is non-zero on 427 of 429 units and is never read; "
			+ "the only command writing a placed row's attr['xp'] takes a "
			+ "client-sent amount",
			"evidence": "command.py:322-343 against the committed content "
				+ "distribution, both measured by the suite"},
		{"fact": "the string `harvester` is not a committed item field at all: it "
			+ "occurs five times in the stored configuration, every one a flag "
			+ "key inside a committed properties blob, on units 1001, 1039, 1040, "
			+ "1041, and 1125, all of which record collect 0",
			"evidence": "the suite re-measures the five occurrences and "
				+ "resolves each carrying item against the verified registry; this "
				+ "CORRECTS the committed investigation's '5 harvester units' "
				+ "framing"},
		{"fact": "exactly one of the six storage-filling branches is "
			+ "content-derived, and it is complete_collection",
			"evidence": "command.py:229, 263, 460, 479, 513, 716; the suite "
				+ "re-derives the call sites and their enclosing branches"},
		{"fact": "unit_collections_completed only appends an id and grants "
			+ "nothing; unit_collection_categories is read by no branch",
			"evidence": "command.py:482-489 against engine.py:91-94"},
		{"fact": "the committed corpus records an empty storage and an empty "
			+ "collection ledger, places 40 rows across 11 distinct ids all of "
			+ "committed type 'b', and carries 40 empty attribute bags",
			"evidence": "tests/saves/fresh-player.json, measured by the suite and "
				+ "by the executed-legacy capture"},
	],
	"derived": [
		{"fact": "the index space is one-based",
			"evidence": "derived-provisional (design D3), corroborated by the "
				+ "committed content rather than merely plausible: the table's own "
				+ "native id column runs \"1\"..\"10\" over the ten array "
				+ "positions 0..9, and the zero-based reading would leave the last "
				+ "collection unreachable; the rejected alternative is retained in "
				+ "REJECTED_ALTERNATIVE"},
		{"fact": "complete_collection is the project's only content-derived unit "
			+ "acquisition route",
			"evidence": "derived (design D4): the inventory classifies all six "
				+ "storage routes and names this one, which COMPLETES the "
				+ "godot-unit-production acquisition finding instead of amending "
				+ "it"},
		{"fact": "the stored-item round trip belongs to a later line rather than "
			+ "to this one",
			"evidence": "derived (design D6): the fixture stops at the grant so "
				+ "this line's scope is one transaction, and the residual is "
				+ "recorded rather than quietly delivered"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy collection panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


# ---------------------------------------------------------------------------
# The one evaluation
# ---------------------------------------------------------------------------


## The whole collection evaluation for one collection id, and the ONLY entry
## point a surface uses. Returns
## `{ok, reason, error, prize, resolved, collection_id, index, clamped, aliased,
##   alias_of, name, entries, unit_count, building_count, unclassified_count,
##   grantable, eligibility_checked, income_derived, cap_interpreted,
##   experience_awarded, unit_placed, content_derived_routes, client_supplied_
##   routes, index_note, readout}`.
##
## The prize projection is **delegated** to `collection_prize.gd` and never
## re-derived, so a surface, the suite, and the report cannot disagree about a
## collection by a key.  Every absence field is a **constant false** carrying the
## recorded reason beside it, so no caller can mistake this for a value the
## legacy server could not give.
static func evaluate(collection_id: Variant, registry_row: Variant,
		registry_ids: Variant) -> Dictionary:
	var projection: Dictionary = CollectionPrize.resolve(
		collection_id, registry_row, registry_ids)
	var resolved := bool(projection.get("resolved", false))
	var base := {
		"ok": true,
		"reason": str(projection.get("reason", "")),
		"error": str(projection.get("error", "")),
		"prize": projection,
		"resolved": resolved,
		"collection_id": projection.get("collection_id", null),
		"index": projection.get("index", -1),
		"clamped": bool(projection.get("clamped", false)),
		"aliased": bool(projection.get("aliased", false)),
		"alias_of": projection.get("alias_of", -1),
		"name": str(projection.get("name", "")),
		"entries": projection.get("entries", []),
		"unit_count": int(projection.get("unit_count", 0)),
		"building_count": int(projection.get("building_count", 0)),
		"unclassified_count": int(projection.get("unclassified_count", 0)),
		"grantable": resolved,
		"eligibility_checked": false,
		"eligibility": NO_ELIGIBILITY_CHECK,
		"alias_gap": INDEX_ALIAS_GAP,
		"income_derived": false,
		"cap_interpreted": false,
		"experience_awarded": false,
		"unit_placed": false,
		"stored_item_placement_delivered": false,
		"content_derived_routes": content_derived_routes(),
		"client_supplied_routes": client_supplied_routes(),
		"no_derivation": NO_DERIVATION,
		"index_note": CollectionPrize.index_note(projection),
	}
	base["readout"] = readout_text(base)
	return base


# ---------------------------------------------------------------------------
# The acquisition inventory (design D4)
# ---------------------------------------------------------------------------


## Every inventoried acquisition route, as a fresh deep copy a caller may keep
## and mutate — so a report reads this module's own table rather than restating
## it.
static func acquisition_routes() -> Array:
	return (ACQUISITION_ROUTES as Array).duplicate(true)


## The inventoried route names in the committed line order.
static func acquisition_route_names() -> Array:
	var out: Array = []
	for entry: Dictionary in ACQUISITION_ROUTES:
		out.append(str(entry["branch"]))
	return out


## The closed classification vocabulary, as a fresh array.
static func classification_vocabulary() -> Array:
	return (CLASSIFICATIONS as Array).duplicate()


## How many inventoried routes carry each classification.  The useful reading is
## the shape it shows: one content-derived, four client-supplied, and one
## already-existing.
static func classification_counts() -> Dictionary:
	var counts := {}
	for name: String in CLASSIFICATIONS:
		counts[name] = 0
	for entry: Dictionary in ACQUISITION_ROUTES:
		var key := str(entry["classification"])
		counts[key] = int(counts.get(key, 0)) + 1
	return counts


## The inventoried routes whose id comes from **committed content** — the answer
## is a one-element list, and it is returned as one rather than as a count so a
## caller can iterate it.
static func content_derived_routes() -> Array:
	var out: Array = []
	for entry: Dictionary in ACQUISITION_ROUTES:
		if str(entry["classification"]) == CLASS_CONTENT:
			out.append(str(entry["branch"]))
	return out


## The inventoried routes whose id arrives from a **client argument**, as an
## array of branch names.  None of them is implemented and no request is issued
## for any of them.
static func client_supplied_routes() -> Array:
	var out: Array = []
	for entry: Dictionary in ACQUISITION_ROUTES:
		if str(entry["classification"]) == CLASS_CLIENT:
			out.append(str(entry["branch"]))
	return out


## The finding the inventory exists to make checkable, verbatim.
static func no_derivation_finding() -> String:
	return NO_DERIVATION


## The whole acquisition finding as the evidence report records it, including the
## statement that no request is issued for any recorded route.
static func acquisition_record() -> Dictionary:
	return {
		"count": ACQUISITION_ROUTE_COUNT,
		"lines": (ACQUISITION_ROUTE_LINES as Array).duplicate(),
		"routes": acquisition_routes(),
		"classifications": classification_vocabulary(),
		"classification_counts": classification_counts(),
		"content_derived_routes": content_derived_routes(),
		"content_derived_route_count": CONTENT_DERIVED_ROUTE_COUNT,
		"client_supplied_routes": client_supplied_routes(),
		"request_issued": false,
		"no_derivation": NO_DERIVATION,
		"not_an_acquisition_route": NOT_ACQUISITION,
	}


## How the readout renders the acquisition finding in one line, so a reader
## looking for "where do units come from" is answered instead of left to infer.
static func acquisition_note() -> String:
	return NO_DERIVATION


# ---------------------------------------------------------------------------
# The recorded gaps and refusals (design D2/D5)
# ---------------------------------------------------------------------------


## Both authority gaps, as the evidence report records them: each is a **fact**
## with its rule attached, and neither is marked fixed.
static func authority_gaps() -> Array:
	return (AUTHORITY_GAPS as Array).duplicate(true)


## The whole eligibility record, including what a caller CANNOT do — the grant
## contents stay content-derived even while eligibility is unchecked.
static func eligibility_record() -> Dictionary:
	return {
		"checked": false,
		"implemented_check": false,
		"rule": NO_ELIGIBILITY_CHECK,
		"alias_gap": INDEX_ALIAS_GAP,
		"caller_may_name_any_committed_collection": true,
		"caller_may_choose_the_grant": false,
		"item_ids_read_by_any_branch": false,
		"note": "what is recorded here is a property of the legacy contract, "
			+ "not a defect this line fixes: authoritative validation belongs to "
			+ "a later server-authoritative milestone",
	}


## The three refusals as the evidence report records them, read from this
## module's own constants so the report cannot describe a contract the code does
## not hold.
static func refusal_record() -> Dictionary:
	return {
		"refusals": (REFUSALS as Array).duplicate(true),
		"collect_fields": (COLLECT_FIELDS as Array).duplicate(true),
		"zero_consumer_precedents": (ZERO_CONSUMER_PRECEDENTS as Array)
			.duplicate(true),
		"harvester": HARVESTER_RECORD,
		"harvester_is_a_committed_field": false,
		"income_derived": false,
		"cap_interpreted": false,
		"experience_awarded": false,
		"award_helper_exists": false,
		"cap_helper_exists": false,
		"payout_helper_exists": false,
	}


## The completion intent's wire contract and its content-derived post-execution
## proof, as the evidence report records them.
static func intent_record() -> Dictionary:
	return {
		"keys": (INTENT_KEYS as Array).duplicate(),
		"ignored_keys": (INTENT_IGNORED_KEYS as Array).duplicate(),
		"note": INTENT_NOTE,
		"command": COMPLETE_COMMAND,
		"proof": PROOF_NOTE,
		"grant_is_content_derived": true,
		"grant_derived_from": "the committed collections table, through the "
			+ "service's own lookup — never from the request",
		"stored_item_placement_delivered": false,
		"stored_item_follow_up": STORED_ITEM_FOLLOW_UP,
	}


## The whole scope statement: what this line delivers, what it records, and the
## one step it deliberately stops short of.
static func scope_record() -> Dictionary:
	return {
		"delivered": [
			"the committed-prize projection with the one-based index and its alias",
			"the acquisition-path inventory with each route classified",
			"both authority gaps, recorded as contract facts",
			"three refusals, each with its recorded reason",
			"the guarded completion intent and its content-derived proof",
		],
		"not_delivered": [
			"any unit income, collection payout, cap semantics, or experience "
				+ "award",
			"any collection eligibility check",
			"any client-supplied acquisition route",
			"the stored-item placement step, so no unit is placed or garrisoned",
			"no production, movement, animation, or behaviour — each is a later "
				+ "M8 line or a later milestone",
		],
		"first_of_its_kind": "the project's FIRST content-derived, "
			+ "server-authoritative unit acquisition",
		"completes": "the godot-unit-production acquisition finding, rather than "
			+ "amending it",
		"corpus": CORPUS_FINDING,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The collection readout: what the committed prize is, the index resolution with
## its alias stated, and — in the same breath — every recorded absence, so the
## omission can never read as a defect.
##
## **No income, no cap, and no experience appear**, because the legacy server
## cannot supply them. An unresolvable id reads as a named absence, never as an
## empty grant.
static func readout_text(evaluation: Dictionary) -> String:
	var parts: Array = []
	if not bool(evaluation.get("resolved", false)):
		parts.append("%s (collection id %s: %s)" % [
			CollectionPrize.UNRESOLVABLE_TEXT,
			str(evaluation.get("collection_id", "?")),
			str(evaluation.get("reason", "")),
		])
	else:
		var entries: Array = evaluation.get("entries", [])
		if entries.is_empty():
			parts.append("no prize entry")
		for entry: Dictionary in entries:
			parts.append(CollectionPrize.entry_note(entry))
	parts.append(str(evaluation.get("index_note", "")))
	parts.append("one content-derived acquisition route ("
		+ str(COMPLETE_COMMAND)
		+ "); no client-supplied route is implemented and no request is "
		+ "issued for any of them")
	parts.append("no eligibility check: a caller may name any of the ten "
		+ "committed collections, and the grant stays content-derived")
	parts.append("no unit income, no cap, and no experience: no committed unit "
		+ "records a positive collect and max_collects is 0 on every unit")
	parts.append("the unit goes into storage only: the stored-item placement "
		+ "step is a separate carried follow-up")
	return " | ".join(parts)