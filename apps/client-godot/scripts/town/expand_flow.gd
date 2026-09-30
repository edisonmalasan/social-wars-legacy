extends RefCounted
## Pure evaluation helpers for the expansion flow (building-expand, spec
## "Expansion flow"): the committed expansion schedule, whether an id is
## purchasable at all, the DEBIT that id's own committed row derives, whether
## the balances cover it, the refusal reasons, and the readout text. No nodes,
## no I/O, no requests, and **no clock of its own** — the schedule is always a
## parameter — so the town view and its suite consume the same functions,
## exactly as `collection_flow.gd` and `construction_flow.gd` serve the
## delivered flows (design D7).
##
## ## The committed schedule, and its id space
##
## `expansion_prices` is **98 POSITIONAL entries with no stable id**: the INDEX
## is the expansion id, so the addressable range is `0..97`. Indexes `0..3` are
## all-zero — the free rows. 94 of the 98 rows record a **positive** `neighbors`
## or `inventory_qte` requirement, and because nothing any delivered surface can
## read evaluates either, the only purchasable entries in the whole table are
## the free indexes `0..3`. That is a committed fact this module mirrors rather
## than computes: `is_purchasable()` refuses a requirement-blocked row by name
## instead of deriving a rule nobody can evaluate.
##
## The corpus consequence is stated rather than hidden: **every id the fresh
## corpus owns (`35, 36, 45, 46`) sits in that refused set**, so the readout
## shows them as owned-and-not-repurchasable and never offers them.
##
## ## What is established and what is derived
##
## **Established** by committed legacy source, executed-legacy evidence, and
## committed asset evidence: the `expand` branch takes one positional argument
## and appends `int(expansion)` to `map["expansions"]`, writing **nothing
## else** (`command.py:211-216`); the price is entirely client-sent and applied
## verbatim per resource as `max(current + delta, 0)` before the branch runs
## (`engine.py:251-271`); **the clamp is reachable** — a client-sent gold debit
## larger than the balance landed on `0`; and the server **cannot arbitrate the
## id space** — an out-of-range id, a duplicate, and a negative id all answered
## success. The expansion price's gold component is named `gold` by the client's
## OWN committed assets `expansion_gold.jpg` / `expansion_cash.jpg`, which is
## what settles the schedule's `coins` field onto the server's gold slot.
##
## **Derived-provisional** (design D1/D2/D3/D6, never observed from the Flash
## client, because no legacy branch reads any of it):
##   * D1 the id-space indexing — the price is the id's own row in the
##     positional table. The server offers no evidence to arbitrate (see the
##     probe above), so the reading rests on the corpus's own
##     `[35, 36, 45, 46]` being a valid index into THIS table, neither a valid
##     four-entry `town_prices` index nor a level set. The claim is "the price
##     the committed table assigns to that id", never "the price a coherent
##     player pays" — and a level-1 fresh player owning four saturated-price
##     expansions is NOT a coherent game state, which is a reason to distrust
##     the reading rather than to accept it;
##   * D2 the debit's SIGN and SHAPE — `[0, 0, -C, 0, 0, 0, -K, 0]` for a row
##     priced `coins C, cash K`, and the all-zero vector for a free row;
##   * D3 the requirements refusal — a positive `neighbors` or
##     `inventory_qte` fails closed rather than being evaluated under an
##     invented rule;
##   * D6 the affordability refusal — an uncovered balance is refused rather
##     than reproduced as the clamp, so a partially applied debit can never be
##     mistaken for a correct one.
##
## ## What is deliberately absent
##
## **No land, grid, cell, footprint, or placement-bound behavior is derived,
## read, or claimed.** The committed evidence establishes the vocabulary — an
## expansion is a purchasable *tile*, bought through a popup, priced in gold and
## cash — but the tile → cell geometry is a **known evidence gap**: the committed
## SWF inspection is symbols-and-tags only and its own scope statement disclaims
## timeline semantics, script behavior, and rendering. This module therefore
## changes no cell and no bound; it only decides what the client would ASK
## about and what it would DISPLAY, while the service owns execution and the
## response owns the ledger and the balances.
##
## Server-authoritative validation, the neighbour/inventory requirement
## IMPLEMENTATIONS, `map_sizes`, and the town-versus-map schedule
## disambiguation beyond what the corpus decides are out of scope.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The committed schedule's entry count (98 POSITIONAL rows, no stable id —
## the index IS the id, design D1).
const SCHEDULE_ENTRIES := 98
## The addressable id range: the schedule's own positional indexes.
const FIRST_ID := 0
const LAST_ID := 97
## The last FREE index. Indexes `0..3` are all-zero, and under design D3 they
## are also the ONLY purchasable entries in the whole committed table — 94 of
## the 98 rows record a positive requirement.
const FIRST_FREE_ID := 0
const LAST_FREE_ID := 3
## The derived DEBIT's fixed width: the legacy eight-slot `resources_changed`
## `[unknown, xp, gold, wood, oil, steel, cash, mana]`.
const VECTOR_SLOTS := BootData.EXPAND_VECTOR_SLOTS
## The two slots an expansion price fills: the schedule's gold-named field
## into `gold` and its `cash` field into `cash`.
const GOLD_SLOT := BootData.EXPAND_GOLD_SLOT
const CASH_SLOT := BootData.EXPAND_CASH_SLOT
## The six slots an expansion debit can never fill (design D2).
const ALWAYS_ZERO_SLOTS := BootData.EXPAND_ALWAYS_ZERO_SLOTS
## The four fields a committed row records, in the fixed order the summary and
## the saturation record use.
const PRICE_FIELDS := ["coins", "cash", "neighbors", "inventory_qte"]
## The two fields that are PRICES rather than requirements, and the resource
## each pays. The gold naming is established by the client's own committed
## assets; the sign and shape are derived.
const DEBIT_FIELDS := [
	["field", "coins", "resource", "gold", "slot", GOLD_SLOT],
	["field", "cash", "resource", "cash", "slot", CASH_SLOT],
]
## The two fields that are REQUIREMENTS. Nothing this stack can read evaluates
## either, so a positive value is a refusal (design D3).
const REQUIREMENT_FIELDS := ["neighbors", "inventory_qte"]
## The sentinel a "no next purchasable entry" lookup returns. Never `0`: index 0
## is a real, free, purchasable id, and confusing "none" with it would offer an
## expansion that does not exist.
const NO_EXPANSION := -1
## No id is purchasable under this reason.
const REASON_NOT_PURCHASABLE := "not_a_purchasable_expansion"
## The player's own ledger already contains the id.
const REASON_ALREADY_EXPANDED := "already_expanded"
## The addressed committed row records a requirement nothing can evaluate.
const REASON_REQUIREMENTS_UNMET := "expansion_requirements_unmet"
## A stored balance does not cover the derived debit.
const REASON_INSUFFICIENT_RESOURCES := "insufficient_resources"
## No committed schedule, or one the content package cannot describe.
const REASON_UNREADABLE_SCHEDULE := "unreadable_schedule"
## No state at all — the structural rejection, which is an error rather than a
## verdict.
const REASON_NO_SELECTION := "no_selection"


## The committed schedule's own size, or -1 when the value is not a usable
## positional table. An explicit sentinel, never a guessed zero: a schedule that
## cannot be counted cannot range-check an id.
static func schedule_size(schedule: Variant) -> int:
	if not (schedule is Array) or (schedule as Array).is_empty():
		return -1
	return (schedule as Array).size()


## One committed schedule row -> `{ok, error, row}` with the row's four fields
## as non-negative integers, or `row: {}` when the id is outside the schedule
## or the row cannot be described. Nothing is defaulted and nothing is coerced:
## the JSON transport widens the numbers to floats on the pinned engine, so an
## integral float is a valid cost, and anything else fails closed.
static func price_of(schedule: Variant, expansion_id: int) -> Dictionary:
	var size := schedule_size(schedule)
	if size < 0:
		return _price_reject(REASON_UNREADABLE_SCHEDULE,
			"the committed expansion schedule is not a positional table")
	if expansion_id < FIRST_ID or expansion_id >= size:
		return _price_reject(REASON_NOT_PURCHASABLE,
			"the committed expansion schedule prices no id %d (it holds %d "
			% [expansion_id, size] + "rows, indexes %d..%d)"
			% [FIRST_ID, size - 1])
	var raw: Variant = (schedule as Array)[expansion_id]
	if not (raw is Dictionary):
		return _price_reject(REASON_UNREADABLE_SCHEDULE,
			"the committed expansion schedule produced no row for id %d"
			% expansion_id)
	var amounts := {}
	for field: String in PRICE_FIELDS:
		var value: Variant = BootData._parse_int((raw as Dictionary).get(field))
		if value == null or int(value) < 0:
			return _price_reject(REASON_UNREADABLE_SCHEDULE,
				"the committed row for id %d resolves no non-negative %s"
				% [expansion_id, field])
		amounts[field] = int(value)
	return {"ok": true, "error": "", "row": amounts}


## The requirement fields a committed row records at a POSITIVE value — the two
## this contract refuses rather than invents (design D3). Fixed order
## (`neighbors` first) so a refusal message is byte-deterministic.
static func unmet_requirements(row: Dictionary) -> Array:
	var unmet: Array = []
	for field: String in REQUIREMENT_FIELDS:
		if int(row.get(field, 0)) > 0:
			unmet.append(field)
	return unmet


## The derived eight-slot DEBIT for one committed row (design D2): the row's
## gold-named cost NEGATED into the gold slot, its cash cost negated into the
## cash slot, and the six slots no expansion price names left zero. A row
## costing nothing derives the ALL-ZERO vector, which is legal — the committed
## free rows `0..3` exist. A fresh vector on every call, so a caller can never
## mutate the derivation for the next one. `null` when the row is unusable.
static func debit_for(row: Variant) -> Variant:
	if not (row is Dictionary):
		return null
	var debit: Array = []
	debit.resize(VECTOR_SLOTS)
	for index in range(VECTOR_SLOTS):
		debit[index] = 0
	for entry: Array in DEBIT_FIELDS:
		var cost: Variant = BootData._parse_int(
			(row as Dictionary).get(str(entry[1])))
		if cost == null or int(cost) < 0:
			return null
		debit[int(entry[5])] = -int(cost)
	for index: int in ALWAYS_ZERO_SLOTS:
		debit[index] = 0
	return debit


## The two resources a vector can move, and the balance each is checked
## against, in a fixed order so a refusal message is deterministic. Each row is
## `{"resource": <BootData.Resources field name>, "slot": <vector index>}`.
static func payable_slots() -> Array:
	var rows: Array = []
	for entry: Array in DEBIT_FIELDS:
		rows.append({"resource": str(entry[3]), "slot": int(entry[5])})
	return rows


## True when every payable slot's balance covers its (non-positive) debit.
## `resources` is keyed by the `BootData.Resources` FIELD names (`gold`,
## `cash`, …) — the town view translates the HUD's own name for the gold slot
## (`coins`) at the one place it reads it, so this module never learns the HUD's
## vocabulary. A balance that does not cover the debit is a refusal (design
## D6), never a silent partial charge.
static func can_afford(debit: Variant, resources: Variant) -> bool:
	if not (debit is Array) or (debit as Array).size() != VECTOR_SLOTS:
		return false
	if not (resources is Dictionary):
		return false
	for entry: Dictionary in payable_slots():
		var slot: int = int(entry["slot"])
		var delta: int = int((debit as Array)[slot])
		if delta == 0:
			continue
		var balance: Variant = BootData._parse_int(
			(resources as Dictionary).get(str(entry["resource"])))
		if balance == null or int(balance) + delta < 0:
			return false
	return true


## The first resource whose balance does not cover the debit, or "" when every
## balance covers it — the name a refusal message quotes, in a fixed order.
static func unaffordable_resource(debit: Variant,
		resources: Variant) -> String:
	if not (debit is Array) or (debit as Array).size() != VECTOR_SLOTS:
		return "the derived debit"
	if not (resources is Dictionary):
		return "the player's balances"
	for entry: Dictionary in payable_slots():
		var slot: int = int(entry["slot"])
		var delta: int = int((debit as Array)[slot])
		if delta == 0:
			continue
		var balance: Variant = BootData._parse_int(
			(resources as Dictionary).get(str(entry["resource"])))
		if balance == null or int(balance) + delta < 0:
			return str(entry["resource"])
	return ""


## Whether the id may be purchased AT ALL, given the player's committed ledger:
## `{ok, purchasable, reason, error, row, debit}`. It covers the three
## non-economic conditions, in this order:
##   * `not_a_purchasable_expansion`  the id is outside the schedule's
##     `0..size-1` range, or the schedule itself is unreadable. The executed
##     probe showed the legacy server accepts `999` and `-1` alike, so this
##     bound is REQUIRED rather than defensive (design D1);
##   * `already_expanded`            the player's own ledger already contains the
##     id. The legacy server neither orders nor deduplicates the ledger — a
##     duplicate `expand(35)` answered success — so a repeat would corrupt the
##     only ledger this line maintains;
##   * `expansion_requirements_unmet` the addressed row records a positive
##     `neighbors` or `inventory_qte`, and nothing this stack can read evaluates
##     either (design D3).
## Affordability is NOT decided here: it is a separate predicate, because the
## readout must show a purchasable-but-unaffordable entry differently from an
## unpurchasable one. `evaluate()` is the single entry point that applies both.
static func is_purchasable(schedule: Variant, expansion_id: int,
		owned: Variant) -> Dictionary:
	var priced := price_of(schedule, expansion_id)
	if not bool(priced.get("ok", false)):
		return {"ok": true, "purchasable": false, "reason": str(
			priced.get("reason", REASON_UNREADABLE_SCHEDULE)),
			"error": str(priced.get("error", "")), "row": {}, "debit": []}
	var row: Dictionary = priced["row"]
	if _owned_contains(owned, expansion_id):
		return {"ok": true, "purchasable": false,
			"reason": REASON_ALREADY_EXPANDED,
			"error": "expansion %d is already in this player's " % expansion_id
				+ "owned-expansions list", "row": row, "debit": []}
	var unmet := unmet_requirements(row)
	if not unmet.is_empty():
		return {"ok": true, "purchasable": false,
			"reason": REASON_REQUIREMENTS_UNMET,
			"error": "expansion %d records %s requirements, and nothing this "
				% [expansion_id, " and ".join(unmet)]
				+ "client can read evaluates them",
			"row": row, "debit": []}
	var debit: Variant = debit_for(row)
	if debit == null:
		return {"ok": true, "purchasable": false,
			"reason": REASON_UNREADABLE_SCHEDULE,
			"error": "the committed row for id %d derives no debit"
				% expansion_id, "row": row, "debit": []}
	return {"ok": true, "purchasable": true, "reason": "", "error": "",
		"row": row, "debit": debit}


## The next purchasable entry after everything the player already owns:
## `{ok, id, row, debit, reason, error}` with `id == NO_EXPANSION` when the
## whole schedule is exhausted. It scans the schedule in its OWN positional
## order, so the answer is the lowest purchasable index the ledger does not
## already contain — deterministic, and never a guess about which tile a player
## "should" buy next.
static func next_purchasable(schedule: Variant, owned: Variant) -> Dictionary:
	var size := schedule_size(schedule)
	if size < 0:
		return {"ok": false, "id": NO_EXPANSION, "row": {}, "debit": [],
			"reason": REASON_UNREADABLE_SCHEDULE,
			"error": "the committed expansion schedule is not a positional "
				+ "table"}
	for id in range(maxi(size, 0)):
		var verdict := is_purchasable(schedule, id, owned)
		if not bool(verdict.get("purchasable", false)):
			continue
		return {"ok": true, "id": id, "row": (verdict["row"] as Dictionary)
			.duplicate(), "debit": (verdict["debit"] as Array).duplicate(),
			"reason": "", "error": ""}
	return {"ok": true, "id": NO_EXPANSION, "row": {}, "debit": [],
		"reason": REASON_NOT_PURCHASABLE,
		"error": "the player's ledger already contains every purchasable entry "
			+ "the committed schedule has"}


## Evaluates one id against the committed schedule, the player's committed
## ledger, and the committed balances, and returns
## `{ok, reason, error, id, row, debit, affordable, offers, owned_count}`.
##
## The refusals, in evaluation order:
##   * `not_a_purchasable_expansion`   out of the schedule's range, or the
##     schedule unreadable (design D1);
##   * `already_expanded`              the ledger already holds the id;
##   * `expansion_requirements_unmet`  the row records an unevaluable
##     requirement (design D3);
##   * `insufficient_resources`        a balance does not cover the derived
##     debit (design D6).
##
## A REFUSAL returns `{ok: true, reason: <one of the above>}` — the evaluation
## itself succeeded and what it found is a verdict, exactly as
## `collection_flow.gd` reports its refusals. Only a structural rejection (no
## schedule, no ledger) returns `{ok: false}`, and that one is an error rather
## than a verdict. `offers_expand()` is the single predicate a caller uses to
## ask "may I confirm this?", and it is false for every refusal.
static func evaluate(schedule: Variant, owned: Variant, resources: Variant,
		expansion_id: int) -> Dictionary:
	var evaluation := {
		"ok": true,
		"reason": "",
		"error": "",
		"id": expansion_id,
		"row": {},
		"debit": [],
		"affordable": false,
		"offers": false,
		"owned_count": _owned_size(owned),
	}
	var verdict := is_purchasable(schedule, expansion_id, owned)
	if not bool(verdict.get("purchasable", false)):
		evaluation["reason"] = str(verdict.get("reason",
			REASON_NOT_PURCHASABLE))
		evaluation["error"] = str(verdict.get("error", ""))
		return evaluation
	evaluation["row"] = (verdict["row"] as Dictionary).duplicate()
	evaluation["debit"] = (verdict["debit"] as Array).duplicate()
	if not can_afford(verdict["debit"], resources):
		evaluation["reason"] = REASON_INSUFFICIENT_RESOURCES
		evaluation["error"] = ("expansion %d needs %s, and this player does not "
			% [expansion_id, debit_text(verdict["debit"])]
			+ "hold it: " + unaffordable_resource(verdict["debit"], resources)
			+ " is short")
		return evaluation
	evaluation["affordable"] = true
	evaluation["offers"] = true
	return evaluation


## True when the evaluation offers an expansion this client may confirm. Every
## refusal and every structural rejection offers nothing.
static func offers_expand(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false)) \
		and str(evaluation.get("reason", "")) == "" \
		and (evaluation.get("debit", []) as Array).size() == VECTOR_SLOTS


## The derived debit as the confirm and the readout name it: the amounts and
## resources it charges, e.g. `"2500 gold, 5 cash"`. A FREE row reads `"free"`
## — the derived vector is the all-zero one, and saying so is more honest than
## printing an empty list. Every part of the text is **derived**, and the
## confirm says so where it is shown.
static func debit_text(debit: Variant) -> String:
	if not (debit is Array) or (debit as Array).size() != VECTOR_SLOTS:
		return ""
	var charged: Array = []
	for entry: Dictionary in payable_slots():
		var slot: int = int(entry["slot"])
		var amount: int = int((debit as Array)[slot])
		if amount != 0:
			charged.append("%d %s" % [-amount, str(entry["resource"])])
	if charged.is_empty():
		return "free"
	return ", ".join(charged)


## The player's own ledger as the readout names it, verbatim and in the save's
## own order: `"35, 36, 45, 46"`, or `"(none)"` for an empty ledger. The empty
## form is deliberately distinct from a MISSING ledger, which the readout names
## as missing rather than presenting as "this player owns nothing".
static func owned_text(owned: Variant) -> String:
	if not (owned is Array) or (owned as Array).is_empty():
		return "(none)"
	var parts: Array = []
	for entry: Variant in (owned as Array):
		parts.append(str(int(entry)))
	return ", ".join(parts)


## The explicit refusal text for an evaluation that offers no expansion: the
## reason plus what the player needs to know, so no rejection is ever a bare
## word. Returns "" while an expansion is offered.
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if offers_expand(evaluation):
		return ""
	var id := int(evaluation.get("id", NO_EXPANSION))
	match str(evaluation.get("reason", "")):
		REASON_NOT_PURCHASABLE:
			return "not purchasable: no committed schedule row prices id %d" % id
		REASON_ALREADY_EXPANDED:
			return "not purchasable: id %d is already owned" % id
		REASON_REQUIREMENTS_UNMET:
			return ("not purchasable: id %d records a neighbour or inventory "
				% id + "requirement nothing this client can read")
		REASON_INSUFFICIENT_RESOURCES:
			return "not purchasable: id %d is not affordable yet (%s)" % [
				id, str(evaluation.get("error", "insufficient resources"))]
		REASON_UNREADABLE_SCHEDULE:
			return "not purchasable: the committed schedule is unreadable"
	return "not purchasable"


## The expansion readout for the selected map: the committed schedule's summary,
## the player's own owned ids, and the next purchasable entry with its derived
## cost and whether the balances cover it. Renders for ANY selected map — armed
## or not — so a player sees the ledger without arming anything, and sees it
## update from every authoritative response.
##
## `evaluation` is an `evaluate()` envelope for the id the readout is
## describing. The readout is DERIVED in every part it shows about a price: the
## amounts come from the client's own derivation of the committed row and are
## presented as derived, never as authoritative — the response is what actually
## moves a balance.
static func readout_text(evaluation: Dictionary, owned: Variant,
		summary: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var parts: Array = []
	parts.append("expansions: %d of %d schedule rows" % [
		int(summary.get("entries", 0)), int(summary.get("entries", 0))])
	parts.append("purchasable: %d" % int(summary.get("purchasable", 0)))
	parts.append("owned: %s" % owned_text(owned))
	var id := int(evaluation.get("id", NO_EXPANSION))
	if id == NO_EXPANSION:
		parts.append("next purchasable: none")
		return " | ".join(parts)
	parts.append("next purchasable: id %d" % id)
	parts.append("derived debit: %s (derived, never observed)"
		% debit_text(evaluation.get("debit", [])))
	parts.append("affordable: %s" % ("yes" if bool(
		evaluation.get("affordable", false)) else "no"))
	var refusal := refusal_text(evaluation)
	if refusal != "":
		parts.append(refusal)
	return " | ".join(parts)


## The action's own button label, so the confirm names the exact action it will
## send rather than a generic "Confirm".
static func expand_label() -> String:
	return "Expand"


## The committed schedule's summary as the readout and the evidence report
## record it: its entry count, its addressable id range, the FREE index range,
## how many of its rows are purchasable under the requirements rule, and the
## per-field saturation indexes (the first index at which each field reaches
## the value it holds through the last index).
##
## Every number is read from the schedule the caller passed, so a content
## change is recorded rather than contradicted. The saturation record is
## `SCHEDULE_ENTRIES` when a field never saturates (it already holds its final
## value at index 0) — an explicit value, never a guess.
static func schedule_summary(schedule: Variant) -> Dictionary:
	var size := schedule_size(schedule)
	if size < 0:
		return {"ok": false, "entries": 0, "first_id": FIRST_ID,
			"last_id": LAST_ID, "free_first_id": FIRST_FREE_ID,
			"free_last_id": LAST_FREE_ID, "purchasable": 0, "free": 0,
			"requirement_blocked": 0, "saturation": {}, "error":
				"the committed expansion schedule is not a positional table"}
	var purchasable := 0
	var free := 0
	for id in range(size):
		var priced := price_of(schedule, id)
		if not bool(priced.get("ok", false)):
			continue
		var row: Dictionary = priced["row"]
		if int(row.get("coins", 0)) == 0 and int(row.get("cash", 0)) == 0:
			free += 1
		if unmet_requirements(row).is_empty():
			purchasable += 1
	var saturation := {}
	for field: String in PRICE_FIELDS:
		var priced_last := price_of(schedule, size - 1)
		if not bool(priced_last.get("ok", false)):
			saturation[field] = size
			continue
		var final_value: int = int((priced_last["row"] as Dictionary)
			.get(field, 0))
		var index := size
		for id in range(size):
			var priced := price_of(schedule, id)
			if not bool(priced.get("ok", false)):
				continue
			if int((priced["row"] as Dictionary).get(field, 0)) == final_value:
				index = id
				break
		saturation[field] = index
	return {"ok": true, "entries": size, "first_id": FIRST_ID,
		"last_id": max(size - 1, FIRST_ID), "free_first_id": FIRST_FREE_ID,
		"free_last_id": LAST_FREE_ID, "purchasable": purchasable, "free": free,
		"requirement_blocked": size - purchasable, "saturation": saturation,
		"error": ""}


## The house price rejection: names the condition instead of deriving from it.
static func _price_reject(reason: String, message: String) -> Dictionary:
	return {"ok": false, "reason": reason,
		"error": "[expand] refused: " + message, "row": {}}


## True when the committed ledger contains the id. The ledger is read as the
## save holds it: any integer, in any order, with repeats kept, so a
## fractional or non-numeric entry simply never matches an integer id rather
## than being coerced into one.
static func _owned_contains(owned: Variant, expansion_id: int) -> bool:
	if not (owned is Array):
		return false
	for entry: Variant in (owned as Array):
		var id: Variant = BootData._parse_int(entry)
		if id != null and int(id) == expansion_id:
			return true
	return false


## How many entries the committed ledger carries, for the readout.
static func _owned_size(owned: Variant) -> int:
	if not (owned is Array):
		return 0
	return (owned as Array).size()
