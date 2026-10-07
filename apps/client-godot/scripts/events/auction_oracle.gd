extends RefCounted
## Recorded legacy auction-house behaviour for OpenSpec `godot-auction-schedule`.
##
## ## This module contains NO behaviour at all
##
## Every item below is a **recorded fact about the preserved source**, carried so
## the refusals in `auction_schedule.gd` can be read with their evidence. Nothing
## here is executed, and nothing here implements the branch it describes. There
## is no function in this file that mutates a document, reads a clock, or decides
## an outcome.
##
## ## The wording scope, stated here because it governs the whole surface
##
## The census below says a state key has "**no server-side reader**". It does not
## say the key is inert, and it is not entitled to: every one of these keys is
## serialised to the wire by the disabled routes, so the Flash client may have
## read all of them. Absence of a reader in the preserved server is a statement
## about the preserved server. `test_auction_schedule.gd` scans both delivered
## modules and fails if the unscoped words ever appear here.
##
## ## Two independent reasons the surface never ran, and only one of them is
## ## the commented-out import
##
## The finding that shapes this capability is a live defect in the preserved
## source: the class guards on one file and then reads a different one. On a
## machine holding the committed config and no leftover state document,
## construction raises `FileNotFoundError`. That is reason one, and it is a
## property of the module rather than of the wiring.
##
## Reason two is the commented-out import and its three commented-out routes,
## which is what the phrase "the auction house is switched off" actually refers
## to. The two are independent: repairing only the commented import would still
## raise on construction, and repairing only the constructor would still leave
## three unreachable routes. Recording only the second reason would make the
## first one look like a wiring choice, which is exactly the misreading a later
## implementer would act on -- "helpfully make it construct" -- and end up
## claiming parity with a system that could never run.
##
## ## The containment note that decided the normalization route
##
## Construction calls `os.makedirs` on a path resolved from a `.` base, so merely
## **importing** the module creates an `auctions/` directory relative to the
## process working directory. Reading committed content therefore never imports
## it, and the builder resolves unit names through the normalized items package
## instead. `auction_schedule.gd` reads only through the registry for the same
## reason.

## The recorded bootstrap defect, with both line numbers and both reasons.
const BOOTSTRAP_DEFECT := {
	"constructible": false,
	"guard_site": "auctions.py:32",
	"guard_tests": "FILE_AH_CONFIG",
	"guard_target": "the committed standalone config document",
	"guard_target_present": true,
	"read_site": "auctions.py:33",
	"read_name": "FILE_AH_STATE",
	"read_target": "the state document in the runtime auctions directory",
	"read_target_present": false,
	"makedirs_site": "auctions.py:30-31",
	"makedirs_path": "resolved from a \".\" base, so relative to the process "
		+ "working directory",
	"raised": "FileNotFoundError",
	"failure_cause": "the guard tests one file and the load reads a different "
		+ "one, so the branch that reads the state document is entered "
		+ "whenever the config exists and the state document does not",
	"inertness_reasons": [
		{
			"reason": "the constructor reads a file it did not test for",
			"site": "auctions.py:32-33",
			"independent_of_the_wiring": true,
			"why_it_matters": "repairing the commented import alone would still "
				+ "raise, so this is a defect in the module and not a choice "
				+ "about the wiring",
		},
		{
			"reason": "the module import and all three routes are commented out",
			"site": "server.py:28-29, :186, :217, :248",
			"independent_of_the_wiring": false,
			"why_it_matters": "this is what \"switched off\" refers to, but it "
				+ "is a second and separate reason; recording only this one "
				+ "would hide the defect",
		},
	],
	"repaired_here": false,
	"state_document_created_here": false,
	"why_not_repaired": "a client that bootstrapped successfully would be "
		+ "implementing something the original never did, and presenting it as "
		+ "parity would be false",
}

## The three commented-out routes and the commented import, each with the file
## and line it was measured at. These are the absence of a request path.
const ROUTE_RECORDS := [
	{"kind": "import", "site": "server.py:28-29",
		"commented": true, "reachable": false,
		"what": "the module import and the single construction call"},
	{"kind": "list", "site": "server.py:186",
		"commented": true, "reachable": false,
		"what": "the list route returning every auction"},
	{"kind": "detail", "site": "server.py:217",
		"commented": true, "reachable": false,
		"what": "the detail route returning one auction"},
	{"kind": "bid", "site": "server.py:248",
		"commented": true, "reachable": false,
		"what": "the bid route writing a bid"},
]

## The recorded expiry semantics, reported verbatim and implemented not at all.
##
## The two boundaries were measured on both sides of the grace by sweeping
## across `endDate` itself and `endDate + 60`; an earlier sweep that stopped one
## second early reported that an auction with a bidder never expires, and that
## instrument was wrong rather than the module.
const EXPIRY_SEMANTICS := {
	"test_site": "auctions.py:119",
	"comparison": "strictly greater than endDate",
	"no_bidder_boundary_offset_seconds": 1,
	"one_bidder_boundary_offset_seconds": 60,
	"grace_gate": "the grace is gated on at least one recorded bidder",
	"round_reset_literal": 1,
	"round_reset_site": "auctions.py:138",
	"round_read_anywhere": false,
	"expired_round_count": {
		"site": "auctions.py:127",
		"computed": true,
		"used": false,
		"note": "only the remainder reaches the new begin instant, so five "
			+ "elapsed rounds produce one auction and the count itself is "
			+ "discarded",
	},
	"implemented_here": false,
	"offered_to_a_player": false,
	"why_not": "nothing evaluates elapsed time and there is no request path "
		+ "through which a player could observe, wait for or act on a boundary",
}

## The client-dictated behaviours, each refused and each labelled a DIVERGENCE
## from the preserved branch rather than parity with it.
##
## Reproducing any of these would be the pattern `AGENTS.md` names as "Bad": the
## client dictates an authoritative outcome.
const CLIENT_DICTATED_REFUSALS := [
	{
		"id": "unvalidated_bid",
		"behaviour": "the stored current price is a pure function of the "
			+ "client-sent bid amount",
		"site": "auctions.py:199",
		"expression": "the client-sent amount plus the committed increment",
		"comparison_operators_against_price_fields": 0,
		"measured": [
			{"client_sent": 1, "price_before": 5000, "price_after": 1001,
				"note": "the price went DOWN by 3999"},
			{"client_sent": 0, "price_before": 5000, "price_after": 1000},
			{"client_sent": -5000, "price_before": 5000, "price_after": -4000},
			{"client_sent": 1000000000, "price_before": 5000,
				"price_after": 1000001000},
		],
		"divergence": true,
		"parity": false,
		"why_refused": "reproducing a client-dictated price is the anti-pattern "
			+ "this project exists to refuse",
	},
	{
		"id": "client_sent_completion_flag",
		"behaviour": "the winner field appears only when a client-sent flag is "
			+ "truthy, and then only for the user asked about",
		"site": "auctions.py:174-176",
		"comparison_operators_against_price_fields": 0,
		"divergence": true,
		"parity": false,
		"why_refused": "a client flag deciding an authoritative outcome is not "
			+ "reproduced; the record names the branch and stops",
	},
	{
		"id": "no_amount_compares_another",
		"behaviour": "no bid amount is ever compared with any other amount",
		"site": "auctions.py:160-176",
		"comparison_operators_against_price_fields": 0,
		"measured": "with two bids of 100 and 99999, the answer for the low "
			+ "bidder is not winning and the answer for the high bidder is "
			+ "winning, decided by list position and not by amount",
		"divergence": true,
		"parity": false,
		"why_refused": "no winner is derived from amounts, so no ranking helper "
			+ "is delivered",
	},
	{
		"id": "unconditional_win_flag",
		"behaviour": "the win flag is the literal 1 for every auction and every "
			+ "user",
		"site": "auctions.py:164",
		"comparison_operators_against_price_fields": 0,
		"divergence": true,
		"parity": false,
		"why_refused": "a constant carrying no information is reported as a "
			+ "measurement and is not projected as a per-auction value",
	},
	{
		"id": "silent_no_op_on_unknown_key",
		"behaviour": "a bid naming an auction that does not exist changes "
			+ "nothing and raises nothing, and the route would still have "
			+ "answered success",
		"site": "auctions.py:181",
		"comparison_operators_against_price_fields": 0,
		"divergence": true,
		"parity": false,
		"why_refused": "an authoritative write that silently succeeds is a "
			+ "server-side gap, and reproducing it is not parity",
	},
	{
		"id": "client_round_never_read",
		"behaviour": "a client-sent round value is accepted and never read",
		"site": "auctions.py:180",
		"comparison_operators_against_price_fields": 0,
		"divergence": true,
		"parity": false,
		"why_refused": "there is no round counter, so no round input is "
			+ "modelled",
	},
]

## The committed bid price, reported as a committed price with no consumer
## rather than as a charge.
##
## The resource-token census below is recorded under BOTH counting rules, and the
## two disagree on exactly one token. A raw substring scan finds three matches for
## the experience token, and every one of them sits inside the word `expired`; a
## whole-word scan finds none. Recording only the substring figure would have
## reported that this module references player experience, which is the opposite
## of the finding.
const BET_PRICE_RECORD := {
	"committed_on_every_entry": true,
	"committed_value": 2,
	"written_at": ["auctions.py:97", "auctions.py:137"],
	"charged": false,
	"resources_debited": 0,
	"server_side_readers": 0,
	"resource_tokens_searched": ["gold", "coins", "cash", "wood", "steel",
		"oil", "xp", "mana", "energy", "cost", "apply_resources"],
	"resource_token_whole_word_occurrences": 0,
	"price_token_occurrences_whole_word": 4,
	"price_occurrences_raw_substring": 9,
	"why_those_two_price_figures_differ": "the raw matches include the longer "
		+ "committed identifiers carrying the word inside them, so only four are "
		+ "the token on its own",
	"the_one_token_whose_rules_disagree": "the experience token has zero "
		+ "whole-word matches and three raw matches, all inside the word "
		+ "`expired`",
	"structurally_identical_to": "the committed premium amount recorded by "
		+ "godot-darts: a committed price with zero consumers",
	"the_difference_is_recorded": "the premium branch discards a client-sent "
		+ "price; this module ignores a committed one. Either way the resource "
		+ "vector is client-controlled and nothing is validated",
	"ordinal_claimed": false,
	"why_no_ordinal": "four earlier lines each numbered zero-consumer committed "
		+ "fields over a different scope and no reconciled census of them exists "
		+ "in the repository",
	"projected_as": "the committed column, verbatim, so a reader can see what "
		+ "the config declares without any charge being implied",
}

## The phrase this surface uses instead, and where the unscoped words are named.
##
## The two words this surface is forbidden to use are deliberately NOT spelled
## here. A guard that scans both delivered modules for them cannot live in a file
## that contains them, so the forbidden list belongs to the suite, which is not
## scanned -- the same shape `godot-construction-assist` recorded when its own
## absence inventory tripped its raw-source guard. Naming the constraint here
## would have made the constraint unenforceable.
const WORDING_SCOPE := {
	"required_phrase": "no server-side reader",
	"forbidden_words_declared_by": "test_auction_schedule.gd",
	"scanned_over": ["auction_schedule.gd", "auction_oracle.gd"],
	"why": "every state key is serialised to the wire by the disabled routes, "
		+ "so the Flash client may have read all of them. Absence of a reader "
		+ "in the preserved server is a statement about the preserved server "
		+ "and nothing more",
	"enforced_by": "test_auction_schedule.gd, over both delivered modules",
}

## The state-key reader census, recorded with its scope and its source.
##
## This table is TRANSCRIBED from the committed investigation's AST census and is
## not re-derived here: distinguishing a write from a comparison needs a parse
## tree, which no GDScript scanner here produces. The suite therefore verifies
## that every key name below really does occur in the recorded source -- a
## measurement of the transcription -- and says plainly in the evidence report
## that the read/write classification itself is inherited, not measured.
const SERVER_SIDE_READER_CENSUS := {
	"scope": "reads are counted inside the one module; every key is serialised "
		+ "to the wire by the disabled routes",
	"source": "docs/legacy-m11-event-systems.md section 8",
	"classification": "transcribed, not re-derived by this suite",
	"keys_total": 21,
	"with_intra_module_reader": 5,
	"with_no_server_side_reader": 16,
	"read": ["beginDate", "betUsers", "endDate", "idUnit", "isWinning"],
	"no_server_side_reader": [
		"beginPrice", "betDetail", "betPrice", "betUsersPrev", "betWinner",
		"bidders", "currentPrice", "finished", "isPrivate", "level",
		"prevRoundBidders", "priceIncrement", "round", "userRounds", "uuid",
		"won",
	],
	"round_residue": ["betUsersPrev", "prevRoundBidders", "userRounds"],
	"round_residue_note": "created, cleared on every expiry, and read by "
		+ "nothing: the residue of a round system that was never written, which "
		+ "is why they are recorded here rather than projected",
}

## The two terms that make this surface unique in the preserved source.
##
## BOTH counting rules are recorded, because the two disagree and a single
## figure would have been a measurement of whichever rule the author happened to
## apply. This is the third recorded instance of the substring-versus-token
## defect class in this project, after `engine.py:62` and `bet\["idUnit"\]`.
##
## For the second term the WHOLE-WORD count is zero: all three raw matches sit
## inside `expired` and `count_expired`. The recorded figure of three is a raw
## substring count. For the first term the two rules agree at one.
##
## The conclusion is unaffected, because the claim that matters -- that neither
## term occurs anywhere OUTSIDE this module -- holds under both rules.
const TERM_RECORD := {
	"interval": {
		"raw_substring_occurrences": 1,
		"whole_word_occurrences": 1,
		"distinct_lines": 1,
		"site": "auctions.py:76",
		"outside_module_raw": 0,
		"outside_module_whole_word": 0,
		"rules_agree": true,
	},
	"expire": {
		"raw_substring_occurrences": 3,
		"whole_word_occurrences": 0,
		"distinct_lines": 3,
		"sites": ["auctions.py:126", "auctions.py:127", "auctions.py:148"],
		"why_they_differ": "every raw match sits inside the words `expired` and "
			+ "`count_expired`, so a token scan finds none of them",
		"outside_module_raw": 0,
		"outside_module_whole_word": 0,
		"rules_agree": false,
		"recorded_investigation_figure": 3,
		"recorded_figure_is_a": "raw substring count",
	},
	"modules_scanned": 11,
	"conclusion": "this is the only interval- or expiry-driven system in the "
		+ "preserved source, so this capability must not re-open the "
		+ "time-dependent surfaces other lines already own",
	"why_the_distinction_is_recorded_rather_than_flattened": "reporting three "
		+ "without the rule would invite a reader to repeat the substring scan "
		+ "and to conclude the module names an expiry operation, which it does "
		+ "not; reporting zero alone would contradict a figure the committed "
		+ "investigation states as three",
}

## The three round-history fields and why none is projected.
const ROUND_HISTORY := [
	{"field": "betUsersPrev", "projected": false,
		"why": "written and cleared, with no server-side reader"},
	{"field": "prevRoundBidders", "projected": false,
		"why": "written and cleared, with no server-side reader"},
	{"field": "userRounds", "projected": false,
		"why": "written and cleared, with no server-side reader"},
]

## Why no executed-legacy fixture is delivered, stated as a decision.
const FIXTURE_REFUSAL := {
	"delivered": false,
	"reason": "the behaviour has no request path",
	"not_a_corpus_limitation": true,
	"why_not_a_corpus_limitation": "the blocker is not that the corpus lacks an "
		+ "auction instance; it is that all three routes and the import are "
		+ "commented out, so no client ever made the transaction",
	"what_a_fixture_would_require": "constructing the class directly against a "
		+ "hand-seeded state document, which is not a transaction any client made",
	"why_that_would_mislead": "it would present a surface that could never run "
		+ "as one that served requests, and it would license a round trip the "
		+ "client does not have",
	"the_rejected_route": "enabling the commented-out routes to obtain a "
		+ "genuine capture would modify legacy behaviour to make a modern test "
		+ "easier, which the repository rules forbid",
	"investigation_figures_are_not_a_capture": "every figure in the committed "
		+ "investigation came from such a constructed precondition and is "
		+ "labelled as constructed at each step; they are evidence about the "
		+ "module's logic and are not carried forward as a fixture",
}

## The one document the corpus census excludes BY NAME, with the measurement
## that makes the exclusion load-bearing rather than ceremonial.
##
## This record deliberately carries the excluded document's identity and its
## reason, but NOT the corpus allow-list itself. The allow-list is owned by the
## suite, because the census walks a caller-supplied list and is proven by
## injection to honour that argument; an allow-list held here would be a second
## source of truth for the same walk. The suite therefore cross-checks the
## `document` field below against its own allow-list, which is a real check
## across two owners rather than a constant compared with itself.
const CORPUS_EXCLUSION := {
	"document": "tests/saves/manifest.json",
	"reason": "an index of sources and fixtures, not a save",
	"load_bearing": true,
	"why_it_is_load_bearing": "the document DOES carry the auction term in "
		+ "raw occurrences, so a directory walk would have reported a carrying "
		+ "document that is not a save at all; excluding it by name is what "
		+ "makes the recorded zero-of-ten figure mean what it says",
	"identified_as_an_index_by": "its own shape: it carries `sources` and "
		+ "`fixtures` indexes and none of `maps`, `privateState` or `playerInfo`",
	"measured_by": "test_auction_schedule.gd, against the committed bytes",
}

## The state-document boundary, restated as a delivered constant.
const STATE_DOCUMENT_BOUNDARY := {
	"created_here": false,
	"defaulted_here": false,
	"repaired_here": false,
	"write_path_here": false,
	"why": "the constructor cannot read the state document it wants, and a "
		+ "client that supplied one would be implementing a bootstrap the "
		+ "original never had",
	"enforced_by": "test_auction_schedule.gd, as an asserted absence",
}

## The delivered routes, actions and flows, all empty (design D5).
const DELIVERED_ROUTES := []
const DELIVERED_ACTIONS := []
const DELIVERED_FLOWS := []
const DELIVERED_LIVE_PHASES := []

## The whole bootstrap record, for a caller that wants one value.
static func bootstrap_record() -> Dictionary:
	return BOOTSTRAP_DEFECT.duplicate(true)


## The expiry record, for a caller that wants one value.
static func expiry_record() -> Dictionary:
	return EXPIRY_SEMANTICS.duplicate(true)


## Every client-dictated refusal's recorded identifier, in recorded order.
static func refusal_ids() -> Array:
	var out: Array = []
	for entry: Dictionary in CLIENT_DICTATED_REFUSALS:
		out.append(str(entry["id"]))
	return out


## One client-dictated refusal's record, or `null` when the id is unknown.
static func refusal_record(refusal_id: String) -> Variant:
	for entry: Dictionary in CLIENT_DICTATED_REFUSALS:
		if str(entry["id"]) == refusal_id:
			return entry
	return null


## The count of client-dictated refusals the suite must see, reported rather
## than assumed so a truncated list cannot read as a complete census.
static func refusal_count() -> int:
	return CLIENT_DICTATED_REFUSALS.size()