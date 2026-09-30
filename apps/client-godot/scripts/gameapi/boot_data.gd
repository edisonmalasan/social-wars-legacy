extends RefCounted
## Typed boot data crossing the GameApi boundary (design D5, spec
## "GameApi abstraction").
##
## The `PlacementResult` class serves BOTH mutating map commands: the
## placement command and the move command answer with the identical
## authoritative superset — the legacy result, the persisted eight-field
## placement entry re-read from the save, and the current resources — so
## one result class and one parse function back both (building-move
## design D4). Nothing about the row distinguishes the two; only the
## request contract and the endpoint path differ.
##
## The sell command needs its own result class for one reason only: its
## eight-field row is the one AS READ BEFORE EXECUTION (building-sell
## design D5), because the persisted save no longer holds it and
## reconstructing it afterwards would be fabrication. `SellResult` reuses
## the very same typed entry class (`Placement`) for that row, so the
## shape is never duplicated — only the envelope and the parse function
## are the command's own.
##
## The store command needs its own result class for the same one reason
## (`removed` is the pre-execution row), plus the FULL post-execution
## storage mapping, which names the other half of the move
## (building-store design D4): `StoreResult` therefore reuses the typed
## entry class for `removed` AND the very same storage parser the
## purchase response uses for `store`, so the storage mapping can never
## be read by two rule sets.
##
## The upgrade command needs its own result class because its response is
## TWO-SIDED and both sides are the same shape: the row AS READ BEFORE
## EXECUTION (`removed`, the very row the client named) and the row re-read
## from the save after execution (`upgraded`). Nothing in the envelope
## distinguishes the sides but the key, so both go through the one typed
## entry parser every other response uses — a row can never be read with
## two rule sets (building-upgrade design D5). The upgraded row's timestamp
## is the documented time-dependent field (the purchase half stamps a fresh
## wall-clock epoch), so no test asserts it by value.
##
## The construction command needs its own result class because its three
## actions share ONE envelope that is two-sided and adds the action the
## service resolved: the row AS READ BEFORE EXECUTION (`previous`, the very
## row the client named) and the row re-read from the save after execution
## (`row`, carrying the countdown, the click counter, or neither). Both sides
## are the same shape, so both go through the one typed entry parser every
## other response uses — a row can never be read with two rule sets
## (building-construction design D3/D5). The row's start instant is the
## documented time-dependent field (legacy stamps it with `time_now()`), so no
## test asserts it by value.
##
## The collect command needs its own result class for three reasons the
## construction class cannot absorb: its response is TWO-SIDED and both sides
## are the same shape (`previous`, the row as read before execution, and
## `row`, the row re-read after it — a collection rewrites one row in place,
## exactly as a construction does, so both go through the one shared entry
## parser every other response uses, a row can never be read with two rule
## sets), and it is the FIRST delivered line whose resource vector is
## deliberately NOT neutral: the service derives a content-derived eight-slot
## `payout` from the addressed item's committed income fields and the committed
## collection ladder, and reports the `tier` that payout came from plus the
## `reference_time` the elapsed time was computed against (building-collect
## design D1/D7/D8). The client's balances and experience come from the
## response's `resources`, never from the payout and never from its own
## arithmetic, so the two disagreeing is detectable rather than silent.
##
## `row.timestamp` is again the documented time-dependent field (legacy stamps
## the collection instant with `time_now()`), so it and `reference_time` are
## asserted as positive integers and never by value.
##
## The expand command needs its own result class for four reasons the collect
## class cannot absorb: its response is TWO-SIDED and both sides are the same
## shape (`expansions_before`, the owned ledger the service READ before
## execution, and `expansions_after`, the same ledger re-read after it — the
## legacy branch is a bare append, so the two differ by exactly one entry at the
## end), and it is the SECOND delivered line whose resource vector is
## deliberately NOT neutral: the service derives a content-derived eight-slot
## **debit** from the addressed id's own committed row in the 98-entry
## positional expansion schedule and reports that committed row verbatim as
## `price` (building-expand design D1/D2/D5). The client's balances come from
## the response's `resources` and its owned ledger from the response's
## `expansions_after`, never from the debit and never from its own arithmetic,
## so the two disagreeing is detectable rather than silent — the response-wins
## rule the collect line also carries.
##
## The level-up command needs its own result class, and its own `LevelCurve`
## block, for four reasons no earlier class can absorb. First, the response is
## the only delivered one whose **target is derived server-side**: the client
## sends a save identity and nothing else, the service derives the level the
## committed curve implies for the stored experience, and both the derived level
## and the recorded level BEFORE execution are reported so the client can see
## what the service decided (building-xp design D3). Second, the recorded level
## is re-read after execution as `level_after` and the service REQUIRES it to
## equal the derived level, so the two-sided shape the expand class carries is
## here a level rather than a ledger. Third, the curve block's `next_level`,
## `next_name`, `next_exp_required`, and `remaining` are **genuinely nullable**
## — at the curve's top level there is no next level, and the spec requires that
## to be reported rather than turned into a sentinel value. Fourth, the curve
## block carries design D1's three machine-readable constants, which this parser
## CHECKS against its own copies: a response reporting a different index base
## would be describing a different curve interpretation, and adopting it
## silently is exactly the off-by-one the line exists to prevent. The committed
## `reward_type` / `reward_amount` are **deliberately absent** from `LevelCurve`:
## no legacy branch reads either, so their structural absence is the statement
## that no reward is paid or displayed (design D7).
##
## `server_time` is the documented time-dependent field here (the legacy
## dispatcher stamps the wall clock into the envelope), so it is asserted as a
## positive integer and never by value. Nothing in the expand response is
## otherwise time-dependent: the legacy branch writes an int the client sent.
##
## Presentation code never receives raw transport dictionaries: every
## GameApi operation returns one of the result classes below, and the two
## legacy JSON payloads (game config, player info) are wrapped in payload
## classes that only the API layer unpacks. The parse functions are shared
## by both implementations, so `FakeApi` and `LegacyV0Api` produce the same
## typed shapes by construction (spec: "Boot offline with the fake
## implementation").

## The v0 protocol identifier every envelope must carry.
const PROTOCOL := "compat-v0"

## The closed action vocabulary of the v0 construction endpoint (building-
## construction design D2). These are the endpoint's OWN outcome names, NOT
## legacy command names: the client chooses an outcome and the service chooses
## the legacy command. The set is closed and echoed exactly as sent, so a
## response naming anything else is a `bad_response`, never a guess.
const CONSTRUCTION_ACTIONS := ["start", "click", "finish"]


## One saved village exactly as the v0 session list reports it.
class SaveInfo:
	extends RefCounted
	var id := ""
	var name := ""
	var xp := 0
	var level := 0


## The boot summary the boot scene displays (name, level, xp), derived from
## the save entry of the bootstrapped user id.
class PlayerSummary:
	extends RefCounted
	var user_id := ""
	var name := ""
	var level := 0
	var xp := 0


## Legacy `get_game_config()` payload: a Dictionary only because the legacy
## payload itself is one; opaque to presentation code.
class ConfigPayload:
	extends RefCounted
	var raw: Dictionary = {}


## Legacy `get_player_info()` payload: opaque like the config, except the
## player's display name, which is typed for convenience.
class PlayerInfoPayload:
	extends RefCounted
	var raw: Dictionary = {}
	var player_name := ""


## Result of `list_sessions()`.
class SaveListResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	var server_time := 0
	## Array of `SaveInfo`.
	var saves: Array[SaveInfo] = []
	var error_code := ""
	var error_message := ""


## Result of `get_bootstrap()`: the session envelope plus the typed summary
## and the two wrapped legacy payloads.
class BootstrapResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	var server_time := 0
	## Array of `SaveInfo`.
	var saves: Array[SaveInfo] = []
	var summary: PlayerSummary = null
	var config: ConfigPayload = null
	var player_info: PlayerInfoPayload = null
	var error_code := ""
	var error_message := ""


## One persisted placement entry exactly as the v0 service reports it — the
## legacy eight-field array (item, x, y, timestamp, orientation, store,
## attr, player) written by `engine.map_add_item`.
class Placement:
	extends RefCounted
	var item_id := 0
	var x := 0
	var y := 0
	## Wall-clock seconds the legacy server stamped when the entry was
	## written: a time-dependent field, so tests assert positivity and
	## identity with the fixture epoch, never a fixed value.
	var timestamp := 0
	var orientation := 0
	## Legacy `store` / `attr` structures — opaque to presentation code,
	## carried in canonical legacy form (integral numbers as `int`, since
	## the JSON transport widens them on the pinned engine while the legacy
	## save stores ints; see `_canonicalize`).
	var store: Array = []
	var attr: Dictionary = {}
	var player := 0


## Authoritative post-application resources a placement response carries —
## the seven stored slots of the legacy resource vector (its unread
## `unknown` slot 0 has no stored value). The client applies only these
## values; it never computes its own delta (design D7).
class Resources:
	extends RefCounted
	var xp := 0
	var gold := 0
	var wood := 0
	var oil := 0
	var steel := 0
	var cash := 0
	var mana := 0


## Result of `place_building()`: the legacy result plus the authoritative
## superset (design D7), or a structured failure with no partial payload.
class PlacementResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	## The legacy result string ("success"); "" on failure.
	var result := ""
	var placement: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `purchase_item()`: the legacy result plus the authoritative
## superset (design D4) — the FULL post-execution storage mapping
## (`{str(item_id): int}`) and the same `Resources` object the placement
## response carries — or a structured failure with no partial payload. The
## client replaces its storage view and its resource values from these
## fields verbatim; it never computes a delta (design D7 carry-forward).
class PurchaseResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The whole storage mapping: string item id -> integer quantity. Quantity
	## `0` is preserved (observed in real saves) and an id the content package
	## cannot resolve is carried verbatim, never dropped.
	var store: Dictionary = {}
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `sell_building()`: the legacy result plus the authoritative
## superset (building-sell design D5) — the eight-field row AS READ BEFORE
## EXECUTION (the authoritative record of exactly what the client asked
## to remove; the persisted save no longer holds it) and the current
## resources — or a structured failure with no partial payload. The
## removed row reuses the typed `Placement` entry class, so the shape is
## never duplicated. The client removes the selected typed placement and
## frees its rendered object on success, and never computes a resource
## delta: the derived price vector is NEUTRAL, so a sale claims no refund.
class SellResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The removed row exactly as it was read before execution.
	var removed: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `store_building()`: the legacy result plus the two-sided
## authoritative superset (building-store design D4) — the eight-field row
## AS READ BEFORE EXECUTION (the persisted save no longer holds it, and
## reconstructing it afterwards would be fabrication) AND the FULL
## post-execution storage mapping (`{str(item_id): int}`, the very shape
## `PurchaseResult.store` carries, parsed by the very same helper) plus the
## current resources — or a structured failure with no partial payload.
## The client removes the selected typed placement, frees its rendered
## object, replaces its storage view from `store` through the shared
## `TownState` storage parser, and takes the resource values verbatim: the
## derived price vector is NEUTRAL, so a store claims no cost and no
## capacity rule, and it deliberately writes no bought-units bookkeeping.
class StoreResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The removed row exactly as it was read before execution.
	var removed: Placement = null
	## The whole post-execution storage mapping: string item id -> integer
	## quantity, in the same shape and through the same parser the
	## purchase response uses (one storage rule, three entry points).
	var store: Dictionary = {}
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `list_sessions()` (never a partial payload).
static func save_list_failure(code: String, message: String) -> SaveListResult:
	var result := SaveListResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `get_bootstrap()` (never a partial payload).
static func bootstrap_failure(code: String, message: String) -> BootstrapResult:
	var result := BootstrapResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `place_building()` (never a partial payload).
static func placement_failure(code: String, message: String) -> PlacementResult:
	var result := PlacementResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `purchase_item()` (never a partial payload).
static func purchase_failure(code: String, message: String) -> PurchaseResult:
	var result := PurchaseResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `sell_building()` (never a partial payload).
static func sell_failure(code: String, message: String) -> SellResult:
	var result := SellResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `store_building()` (never a partial payload).
static func store_failure(code: String, message: String) -> StoreResult:
	var result := StoreResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Result of `upgrade_building()`: the legacy result plus the two-sided
## authoritative superset (building-upgrade design D5) — the eight-field row
## AS READ BEFORE EXECUTION (`removed`, the row the client asked to replace)
## AND the same eight-field row RE-READ FROM THE SAVE after execution
## (`upgraded`, holding the derived target tier at the same key and cell) —
## plus the current resources — or a structured failure with no partial
## payload. The client replaces the selected typed placement's row with
## `upgraded`, keeps the placement's own legacy key, cell, and depth order,
## and takes the resource values verbatim: the derived vector is NEUTRAL, so
## an upgrade claims NO cost of any kind, and the `{"nc": 0}` construction
## counter the purchase half seeds is reported as it arrives and deliberately
## NOT consumed (the construction-timer line owns it).
class UpgradeResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The row exactly as it was read before execution.
	var removed: Placement = null
	## The row re-read from the save after execution (the target tier at the
	## same key and cell, with a fresh timestamp and the purchase half's
	## attribute seed).
	var upgraded: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `upgrade_building()` (never a partial payload).
static func upgrade_failure(code: String, message: String) -> UpgradeResult:
	var result := UpgradeResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Result of `build_construction()`: the legacy result plus the two-sided
## authoritative superset and the action the service resolved
## (building-construction design D3/D5) — the eight-field row AS READ BEFORE
## EXECUTION (`previous`, the row the client named) AND the same row RE-READ
## FROM THE SAVE after execution (`row`, carrying the recorded countdown, the
## raised click counter, or neither) — plus the current resources.
##
## The resolved `action` is echoed exactly as the service received it, so the
## client renders the same vocabulary it sent. The derived vector is NEUTRAL,
## so a construction claims **NO building cost of any kind**: the committed
## configuration records no price for building, and the global that does
## (`BUILD_SPEEDUP_PRICING`) prices a speedup, which is out of scope.
##
## `row.timestamp` is the documented time-dependent field: a start re-stamps
## it with the wall clock, so it is asserted as a positive integer and never
## by value.
class ConstructionResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The row exactly as it was read before execution.
	var previous: Placement = null
	## The row re-read from the save after execution.
	var row: Placement = null
	## The action the service resolved, echoed from the closed vocabulary
	## ("start", "click", "finish"); "" on failure.
	var action := ""
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `build_construction()` (never a partial payload).
static func construction_failure(code: String,
		message: String) -> ConstructionResult:
	var result := ConstructionResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## The derived collection payout's fixed width: the legacy eight-slot
## `resources_changed` vector `[unknown, xp, gold, wood, oil, steel, cash,
## mana]`. The service never sends anything else, so a vector of another
## length is a `bad_response` rather than a pad.
const COLLECT_VECTOR_SLOTS := 8


## Result of `collect_income()`: the legacy result plus the two-sided
## authoritative superset and the content-derived payout with the rung it came
## from (building-collect design D7/D8) — the eight-field row AS READ BEFORE
## EXECUTION (`previous`, the row the client named) AND the same row RE-READ
## FROM THE SAVE after execution (`row`, carrying the re-stamped collection
## instant) — plus the derived `payout`, the `tier` that payout was derived
## for, the `reference_time` the elapsed time was computed against, and the
## current resources.
##
## **Every number in `payout` and `tier` is derived-provisional**, never
## observed from the Flash client: the amount formula (committed `collect`
## scaled by the reached rung's committed multiplier), the experience scaling
## (`collect_xp` by the same rung), the sub-first-rung refusal, the cap
## refusal, and the resource-type mapping are all derivations (design D1-D6).
## The claim is "a payout that grows in four committed rungs, derived from the
## item's committed income fields" — never any specific amount the legacy
## client pays.
##
## The client applies `resources` verbatim and treats `payout` as a read-only
## record of what the service derived: the response always wins over the
## client's own arithmetic, even when the two disagree.
class CollectResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The row exactly as it was read before execution.
	var previous: Placement = null
	## The row re-read from the save after execution, carrying the re-stamped
	## collection instant (the documented time-dependent field).
	var row: Placement = null
	## The derived eight-slot `resources_changed` vector the service applied,
	## `[unknown, xp, gold, wood, oil, steel, cash, mana]`. Slots 0 (`unknown`,
	## unread) and 7 (`mana`, never produced) are always zero (design D6).
	## Read-only evidence: the client never applies this vector itself.
	var payout: Array = []
	## The committed ladder rung the payout was derived for, 0-based; -1 on
	## failure. Clamped at the top rung — the service never extrapolates.
	var tier := -1
	## The instant the elapsed time (and therefore the rung) was computed
	## against. The client's readout evaluates against THIS value rather than
	## its own clock, which is what keeps the deterministic report
	## byte-identical across reruns. Wall-clock dependent: asserted as a
	## positive integer, never by value.
	var reference_time := 0
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `collect_income()` (never a partial payload).
static func collect_failure(code: String, message: String) -> CollectResult:
	var result := CollectResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## The derived expansion **debit**'s fixed width: the legacy eight-slot
## `resources_changed` vector `[unknown, xp, gold, wood, oil, steel, cash,
## mana]`. The expansion price names exactly two of those slots (the schedule's
## gold-named field and its cash field), so the other six are always zero.
const EXPAND_VECTOR_SLOTS := 8
## The six slots an expansion debit can never fill: slot 0 is unread by every
## legacy branch, slot 1 is experience, and slots 3/4/5/7 are wood/oil/steel
## and mana, none of which the committed expansion schedule names.
const EXPAND_ALWAYS_ZERO_SLOTS := [0, 1, 3, 4, 5, 7]
## The two slots a priced expansion's debit fills: the schedule's gold-named
## field into `gold` (slot 2) and its `cash` field into `cash` (slot 6). The
## gold naming is **established** by the client's own committed asset names
## `expansion_gold.jpg` / `expansion_cash.jpg`; the slot numbers are the
## server's own ordering (building-expand design D2).
const EXPAND_GOLD_SLOT := 2
const EXPAND_CASH_SLOT := 6


## One committed expansion price row exactly as the v0 endpoint reports it
## verbatim: the 98-entry positional `expansion_prices` schedule's four
## fields. **No stable id exists in the committed table** — the index IS the id
## (design D1, derived) — so the row itself carries no identifier and the
## caller pairs it with the id it addressed.
##
## `neighbors` and `inventory_qte` are requirements, not prices. Nothing any
## delivered surface can read evaluates either, so a row recording a positive
## value is REFUSED by the endpoint with `expansion_requirements_unmet`
## (design D3) — the row is still carried verbatim on success, where both are
## necessarily zero.
class ExpansionPrice:
	extends RefCounted
	var coins := 0
	var cash := 0
	var neighbors := 0
	var inventory_qte := 0


## Result of `expand_town()`: the legacy result plus the two-sided
## authoritative superset and the content-derived debit with the committed
## schedule row it came from (building-expand design D5/D8) — the owned ledger
## AS READ BEFORE EXECUTION (`expansions_before`, the service's own
## pre-execution read) and the SAME ledger RE-READ FROM THE SAVE after
## execution (`expansions_after`, carrying the appended id at the end with
## every existing entry unchanged, in order, and never deduplicated), plus the
## derived `debit`, the committed `price` row, and the current resources — or a
## structured failure with no partial payload.
##
## The owned lists are typed as plain `Array` of integers rather than a
## dedicated class because they ARE the save's own list, verbatim: this
## contract never reorders, rewrites, normalizes, or deduplicates the ids it
## finds there (the committed corpus's own `[35, 36, 45, 46]` is incoherent
## under the chosen schedule and is tolerated exactly as recorded).
##
## The client applies `resources` and `expansions_after` verbatim and treats
## `debit` and `price` as a read-only record of what the service derived: the
## response always wins over the client's own arithmetic, even when the two
## disagree. The debit's SIGN and SHAPE are derived (design D2) — never
## observed from the Flash client.
class ExpandResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The player's owned-expansions ledger exactly as the service read it
	## BEFORE execution, in the save's own order.
	var expansions_before: Array = []
	## The same ledger RE-READ from the save AFTER execution: the sent id
	## appended once at the end, every existing entry unchanged and in order.
	var expansions_after: Array = []
	## The derived eight-slot `debit` the service applied,
	## `[unknown, xp, gold, wood, oil, steel, cash, mana]`. Every entry is `0`
	## or negative; the six slots in `EXPAND_ALWAYS_ZERO_SLOTS` are always
	## zero. Read-only evidence: the client never applies this vector itself.
	var debit: Array = []
	## The committed schedule row the service priced, verbatim.
	var price: ExpansionPrice = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `expand_town()` (never a partial payload).
static func expand_failure(code: String, message: String) -> ExpandResult:
	var result := ExpandResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Design D1, recorded in machine-readable form so the typed result, the client
## model, the tests, and the structural report all state the same three facts.
## They mirror the Compatibility API v0 module's own constants of the same names
## (`apps/compat-api/level_envelope.py`, read-only here). The interpretation is
## **derived-provisional**; the **rejected** alternative is the **zero-based**
## reading, which the committed corpus contradicts (a player with 4 experience
## is recorded as level 1 while the zero-based curve says level 1 begins at 40).
const LEVEL_INDEX_BASE := "one-based"
const LEVEL_DERIVATION_STATUS := "derived-provisional"
const LEVEL_REJECTED_ALTERNATIVE := "zero-based"


## The committed curve facts one level-up response reports, verbatim
## (building-xp design D5/D8). Every level here was resolved by the service
## through the ONE named conversion, so the client never re-derives any of them:
## it displays the service's own view of the curve it used.
##
## The nullable fields are **genuinely nullable**, not sentinels: at the curve's
## top level there is no next level, and the spec requires that to be reported
## rather than turned into a value. `next_level`, `next_name`,
## `next_exp_required`, and `remaining` are therefore `null` at the top and an
## integer / non-empty string / non-negative integer / non-negative integer
## below it. `entry_name` is null only when the committed entry records no name
## at all, which the readout renders as a **named absence** and never as a
## placeholder.
##
## `reward_type` and `reward_amount` are **deliberately absent from this class**:
## the committed curve carries them and no legacy branch reads either, so paying
## or displaying one would invent an economy. Their absence from the typed
## result is the structural statement of that decision (design D7).
class LevelCurve:
	extends RefCounted
	## The committed curve's entry count (100).
	var entries := 0
	## Design D1's three constants, echoed so the client can display the
	## interpretation the service used rather than assuming one.
	var index_base := ""
	var derivation_status := ""
	var rejected_alternative := ""
	## The DERIVED level's OWN committed entry: its label and its threshold.
	var entry_name: Variant = null
	var entry_exp_required := 0
	## The level AFTER the derived one, or null at the curve's top level.
	var next_level: Variant = null
	var next_name: Variant = null
	var next_exp_required: Variant = null
	## The experience still needed to reach the next level, or null at the top.
	var remaining: Variant = null
	## The stored experience the derivation read (the vector's slot 1).
	var xp := 0


## Result of `level_up_town()`: the legacy result plus the authoritative
## recorded-level superset and the committed curve facts the service used
## (building-xp design D3/D5/D8) — the **derived** level, the recorded level as
## read BEFORE execution (`level_before`), and the SAME field RE-READ FROM THE
## SAVE after execution (`level_after`, which the service requires to equal the
## derived level) — plus the `curve` block and the current `resources` — or a
## structured failure with no partial payload.
##
## **No stored resource is expected to move**: a level change is dispatched like
## every other command with a client-sent vector, and the service's second
## post-execution proof half requires every stored resource to be **unchanged**,
## which is what forecloses a client smuggling a non-neutral vector through this
## command. The `resources` are therefore reported for the readout's benefit and
## the client's own arithmetic is never applied to them.
##
## The client applies `level_after` and `resources` **verbatim** and treats the
## `curve` block as a read-only record of what the service derived: the response
## always wins over the client's own model, even when the two disagree — so a
## wrong client-side derivation can never be silently compounded (the spec's
## response-wins rule).
class LevelUpResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The level the committed curve implies for the stored experience, derived
	## SERVER-SIDE. The client never supplies it and never trusts its own.
	var derived_level := -1
	## The recorded level as the service read it BEFORE execution, and the same
	## field re-read AFTER it.
	var level_before := -1
	var level_after := -1
	## The committed curve facts the service used.
	var curve: LevelCurve = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `level_up_town()` (never a partial payload).
static func level_up_failure(code: String, message: String) -> LevelUpResult:
	var result := LevelUpResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses a v0 level-up envelope — success or structured error — into the typed
## result, fail-closed in both directions (spec "A structured failure carries no
## partial payload"). The rules mirror `parse_expand()`: the envelope must be a
## JSON object reporting `ok: true`, the protocol must be the v0 one, the legacy
## result string must be `success`, the three level integers must be present and
## non-negative, the `curve` block must carry the three design-D1 constants
## verbatim plus a readable derived entry, and `resources` must be the seven
## non-negative integers every other response carries.
##
## The response is the AUTHORITATIVE record of what the service did; nothing
## here re-derives a level, a name, or a threshold from the curve.
static func parse_level_up(payload: Variant) -> LevelUpResult:
	if not (payload is Dictionary):
		return level_up_failure("bad_response",
			"response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _level_up_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return level_up_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return level_up_failure("bad_response",
			"level_up response did not report the legacy success result")
	var levels := {}
	for field in ["derived_level", "level_before", "level_after"]:
		var value: Variant = _parse_int(envelope.get(field))
		if value == null or int(value) < 0:
			return level_up_failure("bad_response",
				"the level-up response carries no non-negative %s" % field)
		levels[field] = int(value)
	var curve := _parse_level_curve(envelope.get("curve"))
	if curve == null:
		return level_up_failure("bad_response",
			"the level-up response carries no readable committed curve block")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return level_up_failure("bad_response",
			"level_up response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return level_up_failure("bad_response",
			"level_up resources are not seven non-negative integers")
	var result := LevelUpResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return level_up_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.derived_level = int(levels["derived_level"])
	result.level_before = int(levels["level_before"])
	result.level_after = int(levels["level_after"])
	result.curve = curve
	result.resources = resources
	return result


## The response's `curve` block -> typed `LevelCurve`; null when the value is not
## an object carrying the documented facts. Every level in the block was already
## resolved by the service through the one named conversion, so the parser only
## checks the SHAPE and never re-derives a value.
##
## The three design-D1 constants are checked against this module's own copies:
## a response that reported a different index base would be describing a
## different curve interpretation, and silently adopting it is exactly the
## off-by-one this line exists to prevent. The nullable fields accept only null
## (the curve's top level) or a well-typed value, so a partially populated block
## fails closed instead of reading as a completed curve.
static func _parse_level_curve(value: Variant) -> LevelCurve:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for field in ["index_base", "derivation_status", "rejected_alternative"]:
		if not (source.get(field) is String):
			return null
	if str(source["index_base"]) != LEVEL_INDEX_BASE:
		return null
	if str(source["derivation_status"]) != LEVEL_DERIVATION_STATUS:
		return null
	if str(source["rejected_alternative"]) != LEVEL_REJECTED_ALTERNATIVE:
		return null
	var entries: Variant = _parse_int(source.get("entries"))
	if entries == null or int(entries) <= 0:
		return null
	var threshold: Variant = _parse_int(source.get("entry_exp_required"))
	if threshold == null or int(threshold) < 0:
		return null
	var xp: Variant = _parse_int(source.get("xp"))
	if xp == null or int(xp) < 0:
		return null
	var curve := LevelCurve.new()
	curve.entries = int(entries)
	curve.index_base = str(source["index_base"])
	curve.derivation_status = str(source["derivation_status"])
	curve.rejected_alternative = str(source["rejected_alternative"])
	curve.entry_exp_required = int(threshold)
	curve.xp = int(xp)
	# A name is a LABEL: a null entry_name is the committed entry recording no
	# name, which the readout renders as a named absence. A non-string is a
	# malformed response and fails closed.
	if source.get("entry_name") != null and not (source.get("entry_name")
			is String):
		return null
	curve.entry_name = source.get("entry_name")
	# The three next-level facts are all-or-nothing: either there is a next
	# level and every one of them is a well-typed value, or the curve has
	# ended and all three are null. A partially populated block is a shape this
	# contract does not carry.
	var nullable := {}
	for field in ["next_level", "next_name", "next_exp_required", "remaining"]:
		nullable[field] = source.get(field)
	var present := 0
	for field in nullable:
		if nullable[field] != null:
			present += 1
	if present != 0 and present != nullable.size():
		return null
	if present == nullable.size():
		var next_level: Variant = _parse_int(nullable["next_level"])
		var next_threshold: Variant = _parse_int(nullable["next_exp_required"])
		var remaining: Variant = _parse_int(nullable["remaining"])
		if next_level == null or int(next_level) < 0:
			return null
		if next_threshold == null or int(next_threshold) < 0:
			return null
		if remaining == null or int(remaining) < 0:
			return null
		if not (nullable["next_name"] is String) \
				or str(nullable["next_name"]).is_empty():
			return null
		curve.next_level = int(next_level)
		curve.next_exp_required = int(next_threshold)
		curve.remaining = int(remaining)
		curve.next_name = str(nullable["next_name"])
	return curve


## Structured error fields of a failed level-up envelope (code + message) — the
## same one envelope rule the other nine commands use, so a code the service
## named (`level_already_current`, `xp_below_threshold`, `missing_user_id`,
## `invalid_user_id`, `unknown_user_id`, `invalid_payload`, `internal_error`, …)
## reaches the client unchanged.
static func _level_up_error(envelope: Dictionary) -> LevelUpResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return level_up_failure(code, message)


## Parses any v0 session envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed fixtures) and `LegacyV0Api` (which decodes the HTTP body).
static func parse_save_list(payload: Variant) -> SaveListResult:
	if not (payload is Dictionary):
		return save_list_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _save_list_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return save_list_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	var raw_saves: Variant = envelope.get("saves")
	if not (raw_saves is Array):
		return save_list_failure("bad_response", "envelope carries no saves array")
	var saves: Array[SaveInfo] = []
	for entry in raw_saves:
		var parsed := _parse_save(entry)
		if parsed == null:
			return save_list_failure("bad_response", "a save entry is malformed")
		saves.append(parsed)
	var server_time := _parse_epoch(envelope.get("server_time"))
	if server_time < 0:
		return save_list_failure("bad_response", "server_time is not a number")
	var result := SaveListResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = server_time
	result.saves = saves
	return result


## Parses a v0 bootstrap envelope into the typed result, deriving the player
## summary from the save entry that names `user_id`.
static func parse_bootstrap(payload: Variant, user_id: String) -> BootstrapResult:
	var list := parse_save_list(payload)
	if not list.ok:
		return bootstrap_failure(list.error_code, list.error_message)
	var envelope: Dictionary = payload
	var config_raw: Variant = envelope.get("config")
	if not (config_raw is Dictionary):
		return bootstrap_failure("bad_response", "bootstrap carries no config object")
	var player_raw: Variant = envelope.get("player_info")
	if not (player_raw is Dictionary):
		return bootstrap_failure("bad_response", "bootstrap carries no player_info object")
	var summary := summary_for(list.saves, user_id)
	if summary == null:
		return bootstrap_failure("summary_unavailable",
			"the session list has no save for user_id '%s'" % user_id)
	var result := BootstrapResult.new()
	result.ok = true
	result.protocol = list.protocol
	result.game_version = list.game_version
	result.server_time = list.server_time
	result.saves = list.saves
	result.summary = summary
	result.config = ConfigPayload.new()
	result.config.raw = config_raw
	result.player_info = PlayerInfoPayload.new()
	result.player_info.raw = player_raw
	result.player_info.player_name = _player_name(player_raw)
	return result


## Parses a v0 placement envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from
## the committed placement fixture after applying the documented in-memory
## semantics) and `LegacyV0Api` (which decodes the HTTP body), so both
## implementations yield the same typed shape by construction.
static func parse_placement(payload: Variant) -> PlacementResult:
	if not (payload is Dictionary):
		return placement_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _placement_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return placement_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return placement_failure("bad_response",
			"placement response did not report the legacy success result")
	var placement := _parse_placement_entry(envelope.get("placement"))
	if placement == null:
		return placement_failure("bad_response",
			"placement entry is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return placement_failure("bad_response",
			"placement response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return placement_failure("bad_response",
			"placement resources are not seven non-negative integers")
	var result := PlacementResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.result = "success"
	result.placement = placement
	result.resources = resources
	return result


## Parses a v0 purchase envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed purchase fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction.
static func parse_purchase(payload: Variant) -> PurchaseResult:
	if not (payload is Dictionary):
		return purchase_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _purchase_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return purchase_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return purchase_failure("bad_response",
			"purchase response did not report the legacy success result")
	var store: Variant = _parse_store(envelope.get("store"))
	if store == null:
		return purchase_failure("bad_response",
			"purchase store is not a string-item-id to integer-quantity map")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return purchase_failure("bad_response",
			"purchase response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return purchase_failure("bad_response",
			"purchase resources are not seven non-negative integers")
	var result := PurchaseResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return purchase_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.store = store
	result.resources = resources
	return result


## Parses a v0 sell envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from
## the committed sell fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. The
## removed row goes through the SAME fail-closed entry parser the
## placement response uses, so a row can never be read with two rules.
static func parse_sell(payload: Variant) -> SellResult:
	if not (payload is Dictionary):
		return sell_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _sell_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return sell_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return sell_failure("bad_response",
			"sell response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return sell_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return sell_failure("bad_response",
			"sell response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return sell_failure("bad_response",
			"sell resources are not seven non-negative integers")
	var result := SellResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return sell_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.resources = resources
	return result


## Parses a v0 store envelope — success or structured error — into the typed
## result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed store fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. The
## removed row goes through the SAME fail-closed entry parser the placement
## and sell responses use, and the storage mapping through the SAME parser
## the purchase response uses (design D4): one row rule, one storage rule.
static func parse_store(payload: Variant) -> StoreResult:
	if not (payload is Dictionary):
		return store_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _store_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return store_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return store_failure("bad_response",
			"store response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return store_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var store: Variant = _parse_store(envelope.get("store"))
	if store == null:
		return store_failure("bad_response",
			"store mapping is not a string-item-id to integer-quantity map")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return store_failure("bad_response",
			"store response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return store_failure("bad_response",
			"store resources are not seven non-negative integers")
	var result := StoreResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return store_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.store = store
	result.resources = resources
	return result


## Parses a v0 upgrade envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed upgrade fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. BOTH rows
## go through the SAME fail-closed entry parser the placement, sell, and
## store responses use (design D5): one row rule, five entry points.
static func parse_upgrade(payload: Variant) -> UpgradeResult:
	if not (payload is Dictionary):
		return upgrade_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _upgrade_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return upgrade_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return upgrade_failure("bad_response",
			"upgrade response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return upgrade_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var upgraded := _parse_placement_entry(envelope.get("upgraded"))
	if upgraded == null:
		return upgrade_failure("bad_response",
			"upgraded row is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return upgrade_failure("bad_response",
			"upgrade response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return upgrade_failure("bad_response",
			"upgrade resources are not seven non-negative integers")
	var result := UpgradeResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return upgrade_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.upgraded = upgraded
	result.resources = resources
	return result


## Parses a v0 construction envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed construction fixture after applying the documented in-memory
## semantics) and `LegacyV0Api` (which decodes the HTTP body), so both
## implementations yield the same typed shape by construction. BOTH rows go
## through the SAME fail-closed entry parser the placement, sell, store, and
## upgrade responses use (design D3/D5): one row rule, six entry points. The
## resolved action must name the closed vocabulary (design D2), so a response
## echoing an unknown value is a `bad_response` rather than a guess.
static func parse_construction(payload: Variant) -> ConstructionResult:
	if not (payload is Dictionary):
		return construction_failure("bad_response",
			"response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _construction_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return construction_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return construction_failure("bad_response",
			"construction response did not report the legacy success result")
	var previous := _parse_placement_entry(envelope.get("previous"))
	if previous == null:
		return construction_failure("bad_response",
			"previous row is not the legacy eight-field array")
	var row := _parse_placement_entry(envelope.get("row"))
	if row == null:
		return construction_failure("bad_response",
			"post-execution row is not the legacy eight-field array")
	var action := str(envelope.get("action", ""))
	if not CONSTRUCTION_ACTIONS.has(action):
		return construction_failure("bad_response",
			"action '%s' is outside the documented construction set" % action)
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return construction_failure("bad_response",
			"construction response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return construction_failure("bad_response",
			"construction resources are not seven non-negative integers")
	var result := ConstructionResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return construction_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.previous = previous
	result.row = row
	result.action = action
	result.resources = resources
	return result


## Parses a v0 collect envelope — success or structured error — into the typed
## result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed collect fixture after applying the documented in-memory
## semantics) and `LegacyV0Api` (which decodes the HTTP body), so both
## implementations yield the same typed shape by construction. BOTH rows go
## through the SAME fail-closed entry parser the placement, sell, store,
## upgrade, and construction responses use (design D3/D5): one row rule, seven
## entry points.
##
## Fail-closed throughout: a payout that is not the documented eight
## non-negative integers, a tier outside the committed ladder, a
## `reference_time` that is not a non-negative epoch, or resources that are
## not seven non-negative integers each answer `bad_response` rather than a
## partially trusted payload. The wall-clock-dependent fields (`server_time`,
## `row.timestamp`, `reference_time`) are shape-checked, never value-checked.
static func parse_collect(payload: Variant) -> CollectResult:
	if not (payload is Dictionary):
		return collect_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _collect_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return collect_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return collect_failure("bad_response",
			"collect response did not report the legacy success result")
	var previous := _parse_placement_entry(envelope.get("previous"))
	if previous == null:
		return collect_failure("bad_response",
			"previous row is not the legacy eight-field array")
	var row := _parse_placement_entry(envelope.get("row"))
	if row == null:
		return collect_failure("bad_response",
			"post-execution row is not the legacy eight-field array")
	var payout: Variant = _parse_payout(envelope.get("payout"))
	if payout == null:
		return collect_failure("bad_response",
			"collect payout is not eight non-negative integers")
	var tier := _parse_epoch(envelope.get("tier"))
	if tier < 0 or tier >= COLLECT_VECTOR_SLOTS:
		# Four committed rungs today; the bound is the vector width so a
		# content change that lengthens the ladder fails closed here instead
		# of reaching the client as an unbounded multiplier.
		return collect_failure("bad_response",
			"tier is not an index inside the committed ladder")
	var reference_time := _parse_epoch(envelope.get("reference_time"))
	if reference_time < 0:
		return collect_failure("bad_response",
			"reference_time is not a non-negative epoch")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return collect_failure("bad_response",
			"collect response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return collect_failure("bad_response",
			"collect resources are not seven non-negative integers")
	var result := CollectResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return collect_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.previous = previous
	result.row = row
	result.payout = payout
	result.tier = tier
	result.reference_time = reference_time
	result.resources = resources
	return result


## Parses a v0 expand envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed expand fixture after applying the documented in-memory semantics)
## and `LegacyV0Api` (which decodes the HTTP body), so both implementations
## yield the same typed shape by construction (design D5).
##
## Fail-closed throughout: an owned list that is not an array of integers, a
## debit that is not exactly eight non-positive integers (or that fills one of
## the six slots the committed schedule never names), a price row that is not
## four non-negative integers, and resources that are not seven non-negative
## integers each answer `bad_response` rather than a partially trusted payload.
## The wall-clock-dependent `server_time` is shape-checked, never
## value-checked.
static func parse_expand(payload: Variant) -> ExpandResult:
	if not (payload is Dictionary):
		return expand_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _expand_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return expand_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return expand_failure("bad_response",
			"expand response did not report the legacy success result")
	var before: Variant = _parse_expansion_ids(envelope.get("expansions_before"))
	if before == null:
		return expand_failure("bad_response",
			"the pre-execution owned list is not an array of integers")
	var after: Variant = _parse_expansion_ids(envelope.get("expansions_after"))
	if after == null:
		return expand_failure("bad_response",
			"the post-execution owned list is not an array of integers")
	var debit: Variant = _parse_expand_debit(envelope.get("debit"))
	if debit == null:
		return expand_failure("bad_response",
			"the expand debit is not eight non-positive integers with six "
			+ "unfilled slots")
	var price := _parse_expansion_price(envelope.get("price"))
	if price == null:
		return expand_failure("bad_response",
			"the expand price is not four non-negative integers")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return expand_failure("bad_response",
			"expand response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return expand_failure("bad_response",
			"expand resources are not seven non-negative integers")
	var result := ExpandResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return expand_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.expansions_before = before
	result.expansions_after = after
	result.debit = debit
	result.price = price
	result.resources = resources
	return result


## One owned-expansions ledger -> its integer ids in the save's own order, or
## null when the value is not an array of integers. Entries are canonicalized
## to `int` (the JSON transport widens them on the pinned engine, and Array
## equality is type-strict there) — only the representation is normalized, never
## the value, and NEVER the order, the length, or the multiplicity: the legacy
## branch neither orders nor deduplicates, so a repeat is a real ledger entry
## and this parser keeps it. A negative entry is tolerated for the same reason a
## negative id was accepted by the executed probe: the ledger is the save's own
## data, and this contract reports it rather than repairing it.
static func _parse_expansion_ids(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var ids: Array = []
	for element: Variant in (value as Array):
		var id: Variant = _parse_int(element)
		if id == null:
			return null
		ids.append(int(id))
	return ids


## The derived eight-slot expansion debit, or null when it is not exactly eight
## non-positive integers with the six unfilled slots at zero. A POSITIVE entry
## is not a shape this contract carries: a price is a debit, and an entry that
## would credit a resource is refused rather than trusted (it would be a mint,
## and the endpoint's own value-level post-state proof exists to catch exactly
## that).
static func _parse_expand_debit(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var raw: Array = value
	if raw.size() != EXPAND_VECTOR_SLOTS:
		return null
	var debit: Array = []
	for element: Variant in raw:
		var amount: Variant = _parse_int(element)
		if amount == null or int(amount) > 0:
			return null
		debit.append(int(amount))
	for index: int in EXPAND_ALWAYS_ZERO_SLOTS:
		if int(debit[index]) != 0:
			return null
	return debit


## One committed expansion price row -> typed `ExpansionPrice`; null when the
## value is not an object carrying exactly four non-negative integer fields. A
## negative cost is not a shape this contract carries: the schedule prices an
## expansion, and a negative price would be a credit.
static func _parse_expansion_price(value: Variant) -> ExpansionPrice:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var amounts := {}
	for field in ["coins", "cash", "neighbors", "inventory_qte"]:
		if not source.has(field):
			return null
		var amount: Variant = _parse_int(source[field])
		if amount == null or int(amount) < 0:
			return null
		amounts[field] = int(amount)
	var price := ExpansionPrice.new()
	price.coins = amounts["coins"]
	price.cash = amounts["cash"]
	price.neighbors = amounts["neighbors"]
	price.inventory_qte = amounts["inventory_qte"]
	return price


## The derived eight-slot payout vector, or null when it is not exactly eight
## non-negative integers. Entries are canonicalized to `int` (the JSON
## transport widens them on the pinned engine, and Dictionary equality is
## type-strict there) — only the representation is normalized, never the
## value. A negative entry is not a shape this contract carries: the income is
## always a credit, and the service refuses to derive anything else.
static func _parse_payout(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var raw: Array = value
	if raw.size() != COLLECT_VECTOR_SLOTS:
		return null
	var vector: Array = []
	for element: Variant in raw:
		var amount: Variant = _parse_int(element)
		if amount == null or int(amount) < 0:
			return null
		vector.append(int(amount))
	return vector


## The storage mapping -> `{str(item_id): int}` with integral floats
## canonicalized to ints (the JSON transport widens them on the pinned engine
## while Dictionary equality is type-strict there — the same tolerance
## `_parse_placement_entry` documents). Null when a value is not a
## non-negative integer: quantities are counts, and a negative or fractional
## quantity is not a shape this contract carries.
static func _parse_store(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var store := {}
	for key: Variant in (value as Dictionary):
		var id: Variant = _store_key(key)
		if id == null:
			return null
		var quantity: Variant = _parse_int((value as Dictionary)[key])
		if quantity == null or int(quantity) < 0:
			return null
		store[str(int(id))] = int(quantity)
	return store


## One storage key -> its non-negative integer item id, or null when the
## key is not an item id. Legacy `engine.add_store_item` writes
## `map["store"][str(item_id)]`, so a digit string is the documented shape
## and the JSON transport always yields one; an int key is accepted and
## canonicalized to the same string form so both implementations produce
## identical typed shapes. Nothing else is coerced.
static func _store_key(key: Variant) -> Variant:
	if key is String:
		var text := str(key)
		if text.is_empty() or text.length() > 16:
			return null
		for character in text:
			if character < "0" or character > "9":
				return null
		return text.to_int()
	var parsed: Variant = _parse_int(key)
	if parsed == null or int(parsed) < 0:
		return null
	return parsed


## Summary for one save id, or null when the list does not name it.
static func summary_for(saves: Array[SaveInfo], user_id: String) -> PlayerSummary:
	for save in saves:
		if save.id == user_id:
			var summary := PlayerSummary.new()
			summary.user_id = save.id
			summary.name = save.name
			summary.level = save.level
			summary.xp = save.xp
			return summary
	return null


## Extracts `playerInfo.name` from the legacy player-info payload.
static func _player_name(payload: Dictionary) -> String:
	var info: Variant = payload.get("playerInfo")
	if info is Dictionary:
		var typed: Dictionary = info
		return str(typed.get("name", ""))
	return ""


## Save entry -> SaveInfo, or null when the entry is malformed.
static func _parse_save(entry: Variant) -> SaveInfo:
	if not (entry is Dictionary):
		return null
	var typed: Dictionary = entry
	var id: Variant = typed.get("id")
	var name: Variant = typed.get("name")
	if not (id is String) or not (name is String):
		return null
	var xp := _parse_number(typed.get("xp"))
	var level := _parse_number(typed.get("level"))
	if xp < 0 or level < 0:
		return null
	var save := SaveInfo.new()
	save.id = id
	save.name = name
	save.xp = xp
	save.level = level
	return save


## Non-negative integer from an int or float transport value; -1 otherwise.
static func _parse_number(value: Variant) -> int:
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed < 0.0 or typed != floor(typed):
			return -1
		return int(typed)
	return -1


## Epoch seconds from an int or float transport value; -1 otherwise.
static func _parse_epoch(value: Variant) -> int:
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed < 0.0:
			return -1
		return int(typed)
	return -1


## Structured error fields of a failed envelope (code + message).
static func _save_list_error(envelope: Dictionary) -> SaveListResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return save_list_failure(code, message)


## Structured error fields of a failed placement envelope (code + message).
static func _placement_error(envelope: Dictionary) -> PlacementResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return placement_failure(code, message)


## Structured error fields of a failed purchase envelope (code + message).
static func _purchase_error(envelope: Dictionary) -> PurchaseResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return purchase_failure(code, message)


## Structured error fields of a failed sell envelope (code + message).
static func _sell_error(envelope: Dictionary) -> SellResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return sell_failure(code, message)


## Structured error fields of a failed store envelope (code + message).
static func _store_error(envelope: Dictionary) -> StoreResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return store_failure(code, message)


## Structured error fields of a failed upgrade envelope (code + message) —
## the same one envelope rule the other five commands use, so a code the
## service named (`no_upgrade_path`, `unknown_item_index`,
## `internal_error`, …) reaches the client unchanged.
static func _upgrade_error(envelope: Dictionary) -> UpgradeResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return upgrade_failure(code, message)


## Structured error fields of a failed construction envelope (code + message)
## — the same one envelope rule the other six commands use, so a code the
## service named (`no_build_time`, `unknown_item_index`, `invalid_action`,
## `internal_error`, …) reaches the client unchanged.
static func _construction_error(envelope: Dictionary) -> ConstructionResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return construction_failure(code, message)


## Structured error fields of a failed collect envelope (code + message) — the
## same one envelope rule the other seven commands use, so a code the service
## named (`too_early`, `capped_collection`, `unknown_collect_type`,
## `no_income`, `construction_in_progress`, `unknown_item_index`,
## `internal_error`, …) reaches the client unchanged.
static func _collect_error(envelope: Dictionary) -> CollectResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return collect_failure(code, message)


## Structured error fields of a failed expand envelope (code + message) — the
## same one envelope rule the other eight commands use, so a code the service
## named (`unknown_expansion_id`, `already_expanded`,
## `expansion_requirements_unmet`, `insufficient_resources`,
## `invalid_expansion_id`, `missing_expansion_id`, `internal_error`, …) reaches
## the client unchanged.
static func _expand_error(envelope: Dictionary) -> ExpandResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return expand_failure(code, message)


## Eight-field legacy entry -> typed `Placement`; null when malformed
## (wrong shape, non-integer fields, or a negative coordinate/timestamp).
static func _parse_placement_entry(value: Variant) -> Placement:
	if not (value is Array):
		return null
	var raw: Array = value
	if raw.size() != 8:
		return null
	var item_id: Variant = _parse_int(raw[0])
	var x: Variant = _parse_int(raw[1])
	var y: Variant = _parse_int(raw[2])
	var timestamp: Variant = _parse_int(raw[3])
	var orientation: Variant = _parse_int(raw[4])
	var player: Variant = _parse_int(raw[7])
	if item_id == null or x == null or y == null or timestamp == null \
			or orientation == null or player == null:
		return null
	if int(item_id) < 0 or int(x) < 0 or int(y) < 0 or int(timestamp) < 0:
		return null
	if not (raw[5] is Array) or not (raw[6] is Dictionary):
		return null
	var placement := Placement.new()
	placement.item_id = int(item_id)
	placement.x = int(x)
	placement.y = int(y)
	placement.timestamp = int(timestamp)
	placement.orientation = int(orientation)
	placement.store = _canonicalize(raw[5])
	placement.attr = _canonicalize(raw[6])
	placement.player = int(player)
	return placement


## The seven stored resource slots -> typed `Resources`; null when any
## slot is missing or not a non-negative integer (legacy clamps them at
## zero on the server, so a negative value cannot come from the service).
static func _parse_resources(value: Dictionary) -> Resources:
	var amounts := {}
	for key in ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]:
		if not value.has(key):
			return null
		var amount: Variant = _parse_int(value[key])
		if amount == null or int(amount) < 0:
			return null
		amounts[key] = int(amount)
	var resources := Resources.new()
	resources.xp = amounts["xp"]
	resources.gold = amounts["gold"]
	resources.wood = amounts["wood"]
	resources.oil = amounts["oil"]
	resources.steel = amounts["steel"]
	resources.cash = amounts["cash"]
	resources.mana = amounts["mana"]
	return resources


## Integer from an int or an integral float; null otherwise. The JSON
## transport parses every number as float on the pinned engine (probed on
## Godot 4.7.2: `typeof(JSON.parse_string("5"))` is float), so both
## integer forms are accepted — the same tolerance `_parse_number`
## documents for save values. Out-of-range magnitudes, NaN, and infinity
## are rejected.
static func _parse_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and absf(typed) <= 9007199254740992.0:
			return int(typed)
	return null


## Canonical legacy form of a nested `store`/`attr` structure: every
## integral float becomes `int`, because the JSON transport widens the
## legacy save's ints to floats on the pinned engine while Dictionary
## equality is type-strict there (probed: `{"nc": 0} == {"nc": 0.0}` is
## false). Without this, the two implementations would report the same
## persisted entry with different value types. Non-integral floats,
## strings, booleans, and null pass through untouched — only the
## representation is normalized, never the value.
static func _canonicalize(value: Variant) -> Variant:
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and absf(typed) <= 9007199254740992.0:
			return int(typed)
		return typed
	if value is Dictionary:
		var out := {}
		for key: Variant in value:
			out[key] = _canonicalize(value[key])
		return out
	if value is Array:
		var out: Array = []
		for element: Variant in value:
			out.append(_canonicalize(element))
		return out
	return value
