extends Node2D
## The town view (OpenSpec `godot-town-rendering`, design D3-D9).
##
## Renders one typed town state into one isometric coordinate space: the
## legacy terrain stretched over the projection's world rectangle, every
## saved placement as a depth-sorted object at its saved cell, the
## authoritative resource HUD on the UI foundation's slot, a bounded
## camera framed on the town, and press-to-cell selection. The view reads
## only the typed state — no raw transport payload reaches presentation
## (spec: "Presentation code SHALL receive only the typed state").
##
## Placement mode (building-placement, spec "Placement flow"): a build
## picker over the fail-closed placement catalog, a footprint preview at
## the inverse-projected cell with valid/invalid highlighting, and a
## confirm that sends exactly one intent through GameApi and applies
## only the authoritative response — new object in depth order, HUD
## resources from the response — while every failure surfaces an
## explicit error with no state change. Selection and placement share
## the left press: the open picker routes it to the preview, otherwise
## to selection (design D10).
##
## Shop mode (building-purchase, spec "Purchase flow"): a shop panel in
## its OWN UI-foundation slot over the same fail-closed catalog parse,
## offering store-listed, cash-priced, level-eligible entries with their
## price against current cash, a storage readout of the typed state's
## storage (resolved content name when one exists, the raw item id
## otherwise), and a confirm that sends exactly one intent through GameApi
## and applies only the authoritative response — the response's storage
## mapping replaces the state's through the shared parser, HUD resources
## take the response's values — while an unaffordable price is refused
## locally with no request and every failure surfaces an explicit error
## with no state change. The shop sits BESIDE the picker, never inside it
## (design D8): separate slot, separate selection, and the picker's
## preview/overlay state is untouched.
##
## Fail-closed whole view (design D9): a failed build enters an explicit
## error state that names the failure and clears any partial view —
## never a silently blank or partially drawn town. Camera bounds are
## optional and fail-closed when set (design D1); an unset camera keeps
## the M5 foundation behavior byte-for-byte.
##
## Capture (design D9): `--town-capture=<path>` in a windowed session
## resizes to the authentic legacy stage (1400x600), frames the camera on
## the recorded focus position, writes the PNG, and quits — the
## transition-and-first-render evidence step. Headless sessions build and
## expose records only; they never capture (capture stays windowed-only).
##
## Report (design D10 step 3, task 8.3): a headless
## `town.tscn --town-report` run rebuilds both town views from the
## committed inputs (the fake GameApi's bootstrap fixtures — exactly one
## bootstrap request — and the preserved slice village), observes the
## structural records, writes the deterministic evidence report
## (`evidence/town/report.json`; `--town-report=<path>` redirects it),
## and quits. The report carries stable inputs, digests, constants,
## counts, and observed state only — no timestamps or run-varying
## provenance — so reruns are byte-identical. Any failure prints an
## explicit `[town] report state=error` marker and exits 1.
##
## The placement, purchase, and move evidence steps mirror that pattern
## exactly one level down: `--placement-capture=<path>` /
## `--purchase-capture=<path>` / `--move-capture=<path>` /
## `--sell-capture=<path>` / `--store-capture=<path>` drive their flow
## (picker / shop / selection-then-move / selection-then-sell /
## selection-then-store) before the
## frame is written, and `--placement-report=<path>` /
## `--purchase-report=<path>` / `--move-report=<path>` /
## `--sell-report=<path>` / `--store-report=<path>` write their deterministic
## `placement-report-v1` / `purchase-report-v1` / `move-report-v1` /
## `sell-report-v1` / `store-report-v1` reports.
##
## Move mode (building-move, spec "Move flow"): a move surface in its OWN
## UI-foundation slot, armed from the delivered selection path — selecting a
## placed building that has an addressable legacy key offers a `Move`
## action, and pressing it arms the move. The armed surface reuses the
## existing footprint preview over the shared iso projection with the moving
## building's own cells excluded from the occupancy check, a confirm that
## sends exactly one intent through GameApi, and an apply that trusts only
## the authoritative response: the same rendered object repositioned at the
## response's cell and re-sorted in depth order, the typed row replaced by
## the response's persisted entry, HUD resources from the response — with
## every write rolled back if any step fails. Invalid targets and the
## building's current cell are refused locally with an explicit reason and
## NO request (design D5: the client owns the gameplay rules the legacy
## server never enforced). The move requires no purchase.
##
## Sell mode (building-sell, spec "Sell flow"): a second mode on the SAME
## delivered selection-driven surface — selecting a placed building that has
## an addressable legacy key offers a `Sell` action beside the `Move` one,
## and pressing it arms the sale. The armed surface reuses that panel's
## status line and its confirm/cancel row in a second mode (design D8: a
## sell has no grid target, and a third panel would duplicate the selection
## affordance for no behavioral gain): the confirm names the building and
## sends exactly one `GameApi.sell_building()` intent, cancellation sends
## nothing and leaves the town byte-identical, and success applies only the
## authoritative response — the selected typed placement removed, its
## rendered object freed, the remaining objects keeping the committed depth
## order, HUD resources and XP from the response — with every write rolled
## back if any step fails (design D9). A placement with no addressable
## legacy key is refused with the move flow's own explicit reason. The
## derived price vector is NEUTRAL, so a sale claims NO refund.
##
## Store mode (building-store, spec "Store flow"): a THIRD mode on the SAME
## delivered selection-driven surface — beside `Move` and `Sell`, exactly one
## of the three can be armed at a time — so selecting a placed building that
## has an addressable legacy key offers a `Store` action, and pressing it
## arms the store. The armed surface reuses that panel's status line and its
## confirm/cancel row in a third, TARGETLESS mode (design D7: a store has no
## grid cell and no preview, and a fourth panel would duplicate the
## selection affordance): the confirm names the building and reports where it
## will land (its item id in the player's storage) and sends exactly one
## `GameApi.store_building()` intent, cancellation sends nothing and leaves
## the town byte-identical, and success applies only the authoritative
## response — the selected typed placement removed, its rendered object
## freed, the remaining objects keeping the committed depth order, the typed
## storage replaced through the SAME fail-closed `TownState` parser the
## payload parse and the purchase apply use, the storage readout re-rendered
## from it, and the HUD resources and XP from the response — with every write
## snapshotted and rolled back if any step fails (design D8). A placement
## with no addressable legacy key is refused with the move flow's own
## explicit reason, and a selection that no longer names the armed building
## is refused by name rather than silently re-targeted. The derived price
## vector is NEUTRAL, so a store claims NO cost and NO capacity rule, and it
## writes NO bought-units bookkeeping — the legacy branch does not, and this
## reproduces that exactly. This line only moves a building INTO storage:
## stored items are not yet playable and `place_stored_item` remains open.

const Iso = preload("res://scripts/town/iso.gd")
const TownState = preload("res://scripts/town/town_state.gd")
const TownObject = preload("res://scripts/town/town_object.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")
const TownHud = preload("res://scripts/town/town_hud.gd")
const TownTerrain = preload("res://scripts/town/town_terrain.gd")
const CameraControls = preload("res://scripts/camera_controls.gd")
const UiFoundation = preload("res://scripts/ui_foundation.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")
const Paths = preload("res://scripts/package_paths.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")
const PlacementFlow = preload("res://scripts/town/placement_flow.gd")
const ShopFlow = preload("res://scripts/town/shop_flow.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")

## Report-mode inputs and captures (repository-relative paths; the
## fixture paths mirror the fake GameApi's own committed constants and
## the slice scene's preserved village).
const REPORT_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const REPORT_BOOTSTRAP := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const REPORT_VILLAGE := "villages/Scarlet.json"
const REPORT_CAPTURE_PLAYER := \
	"apps/client-godot/evidence/town/town-player.png"
const REPORT_CAPTURE_SLICE := "apps/client-godot/evidence/town/town-slice.png"
## Default report destination for the bare `--town-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_REPORT_PATH := "evidence/town/report.json"

## Placement evidence (building-placement, design D11): the executed-
## legacy placement fixture the parity suite replays and the committed
## fake capture the placement report points at (repository-relative).
const REPORT_PLACEMENT_REQUEST := \
	"tests/fixtures/godot-building-placement/steps/command_buy/request.json"
const REPORT_PLACEMENT_RESPONSE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/response.body"
const REPORT_PLACEMENT_AFTER := \
	"tests/fixtures/godot-building-placement/steps/command_buy/after.json"
const REPORT_CAPTURE_PLACEMENT := \
	"apps/client-godot/evidence/placement/placement.png"
## Purchase evidence (building-purchase, design D9): the executed-legacy
## purchase fixture the parity suite replays and the committed fake capture
## the purchase report points at (repository-relative).
const REPORT_PURCHASE_REQUEST := "tests/fixtures/godot-item-purchase/steps/" \
	+ "command_buy_stored_item_cash/request.json"
const REPORT_PURCHASE_RESPONSE := "tests/fixtures/godot-item-purchase/steps/" \
	+ "command_buy_stored_item_cash/response.body"
const REPORT_PURCHASE_AFTER := "tests/fixtures/godot-item-purchase/steps/" \
	+ "command_buy_stored_item_cash/after.json"
const REPORT_CAPTURE_PURCHASE := \
	"apps/client-godot/evidence/purchase/purchase.png"
## Default purchase report destination for the bare `--purchase-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_PURCHASE_REPORT_PATH := "evidence/purchase/report.json"
## The single placement intent the placement evidence records: one House I
## at (51, 39), orientation 0 — the executed-legacy fixture's transaction,
## driven through the same picker flow a player uses.
const PLACEMENT_INTENT_ITEM := 1
const PLACEMENT_INTENT_CELL := Vector2i(51, 39)
const PLACEMENT_INTENT_ORIENTATION := 0
## The single purchase intent the purchase evidence records: one Victory
## Arch (item 105) for the fresh player's exactly-5 cash — the
## executed-legacy fixture's transaction, driven through the same shop flow
## a player uses.
const PURCHASE_INTENT_ITEM := 105
## Move evidence (building-move, design D9): the executed-legacy move
## fixture the parity suite replays and the committed fake capture the move
## report points at (repository-relative).
const REPORT_MOVE_REQUEST := \
	"tests/fixtures/godot-building-move/steps/command_move/request.json"
const REPORT_MOVE_RESPONSE := \
	"tests/fixtures/godot-building-move/steps/command_move/response.body"
const REPORT_MOVE_AFTER := \
	"tests/fixtures/godot-building-move/steps/command_move/after.json"
const REPORT_CAPTURE_MOVE := \
	"apps/client-godot/evidence/building-move/building-move.png"
## Default move report destination for the bare `--move-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_MOVE_REPORT_PATH := "evidence/building-move/report.json"
## The single move intent the move evidence records: Turret I (item 22) at
## legacy map key 11, from its saved cell (58,48) to (58,47) — the
## executed-legacy fixture's transaction, driven through the same
## selection -> arm -> preview -> confirm flow a player uses. The target is
## the fixture's documented derived rule (the Manhattan-nearest free
## one-step neighbour, ties broken row-major).
const MOVE_INTENT_INDEX := 11
const MOVE_INTENT_ITEM := 22
const MOVE_INTENT_FROM := Vector2i(58, 48)
const MOVE_INTENT_TO := Vector2i(58, 47)
## Sell evidence (building-sell, design D10): the executed-legacy sell
## fixture the parity suite replays and the committed fake capture the sell
## report points at (repository-relative).
const REPORT_SELL_REQUEST := \
	"tests/fixtures/godot-building-sell/steps/command_sell/request.json"
const REPORT_SELL_RESPONSE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/response.body"
const REPORT_SELL_AFTER := \
	"tests/fixtures/godot-building-sell/steps/command_sell/after.json"
const REPORT_CAPTURE_SELL := \
	"apps/client-godot/evidence/building-sell/building-sell.png"
## Default sell report destination for the bare `--sell-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_SELL_REPORT_PATH := "evidence/building-sell/report.json"
## The single sell intent the sell evidence records: Turret I (item 22) at
## legacy map key 20, anchored at (41,48) — the executed-legacy fixture's
## transaction, driven through the same selection -> arm -> confirm flow a
## player uses. It is the fixture's second Turret I in map-slot order, so
## this evidence differs from the move fixture's slot 11 and the two stay
## independently readable.
const SELL_INTENT_INDEX := 20
const SELL_INTENT_ITEM := 22
const SELL_INTENT_CELL := Vector2i(41, 48)
## Store evidence (building-store, design D9): the executed-legacy store
## fixture the parity suite replays and the committed fake capture the store
## report points at (repository-relative).
const REPORT_STORE_REQUEST := \
	"tests/fixtures/godot-building-store/steps/command_store_item/request.json"
const REPORT_STORE_RESPONSE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/response.body"
const REPORT_STORE_AFTER := \
	"tests/fixtures/godot-building-store/steps/command_store_item/after.json"
const REPORT_CAPTURE_STORE := \
	"apps/client-godot/evidence/building-store/building-store.png"
## Default store report destination for the bare `--store-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_STORE_REPORT_PATH := "evidence/building-store/report.json"
## The single store intent the store evidence records: the Tree decoration
## (item 905) at legacy map key 2, anchored at (53,39) — the
## executed-legacy fixture's transaction, driven through the same
## selection -> arm -> confirm flow a player uses. The fixture's slot differs
## from the move fixture's 11 and the sell fixture's 20, so the three
## fixtures stay independently readable.
const STORE_INTENT_INDEX := 2
const STORE_INTENT_ITEM := 905
const STORE_INTENT_CELL := Vector2i(53, 39)
## Default placement report destination for the bare
## `--placement-report` flag (project-relative, resolved against the
## project directory).
const DEFAULT_PLACEMENT_REPORT_PATH := "evidence/placement/report.json"
## The recorded projection evidence gap (README "Isometric projection
## constants"): the legacy SWF's static iso-engine identifiers exist as
## ABC strings but their numeric values were never extracted.
const EVIDENCE_GAP := "the legacy SWF's static iso-engine identifiers " \
	+ "(TILE_SIZE, EI_TILE_HEIGHT_PIXELS, gridWidth/Height, numCols/numRows) " \
	+ "were never extracted; pixel parity with the Flash client is not claimed"
## The spec's five explicit non-claims ("Town evidence and claim limits").
## The runtime tokens in the first claim are assembled from fragments:
## the project-scope suite scans this file's bytes for their literal
## forms, and this file never spells them out.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"no pixel-parity oracle against the legacy client exists",
	"projection constants are derived and provisional",
	"thumbnail presentation is provisional pending further conversions",
	"authentic unit rendering is proven via the slice scene because "
		+ "the live fresh save contains no unit placements",
]

## The placement evidence's explicit non-claims (spec "Evidence and
## claim limits"): the five required claims, the fake-capture pointer
## design D11 demands, and the derived client-only validation split.
## The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as NON_CLAIMS above.
const PLACEMENT_NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the price vector, envelope placeholders, and slot choice are "
		+ "derived, never observed from the Flash client",
	"parity covers one recorded transaction against the fresh-player "
		+ "corpus, not progressed players",
	"insufficient resources reproduce legacy clamping, not rejection",
	"no pixel-parity oracle against the legacy client exists",
	"the capture runs the fake GameApi implementation; real-execution "
		+ "parity is established by the fixture-replay tests and the "
		+ "verify-boot placement live phase",
	"occupancy and grid-bounds rules are derived (Flash-unobservable) "
		+ "and enforced client-side only; the endpoint enforces "
		+ "structural input validity",
]

## The purchase evidence's explicit non-claims (spec "Purchase evidence and
## claim limits"): the five carried-forward claims, the cash-only
## derivation and command-choice claim design D9 adds, the storage
## display-only limit, the client-owned validation split, and the
## fake-capture pointer. The runtime tokens in the first claim are assembled
## from fragments for the same project-scope reason as above.
const PURCHASE_NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the legacy command choice and the cash-only price derivation are "
		+ "derived, never observed from the Flash client",
	"parity covers one recorded transaction against the fresh-player "
		+ "corpus, not progressed players",
	"insufficient cash reproduces legacy clamping, not rejection",
	"storage is display-only here: no placing from or selling out of "
		+ "storage",
	"no pixel-parity oracle against the legacy client exists",
	"the capture runs the fake GameApi implementation; real-execution "
		+ "parity is established by the fixture-replay tests and the "
		+ "verify-boot purchase-live phase",
	"the level gate and cash affordability are derived (Flash-"
		+ "unobservable) and enforced client-side only; the endpoint "
		+ "enforces structural input validity",
]

## The move evidence's explicit non-claims (spec "Move evidence and claim
## limits"): the carried-forward claims, the derived argument values, the
## arguments legacy discards, the neutral price vector, the one-transaction
## parity scope, the client-only validation split, the no-pixel-parity
## claim, and the fake-capture pointer. The runtime tokens in the first
## claim are assembled from fragments for the same project-scope reason as
## the lists above.
const MOVE_NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the command's argument values, the arguments the legacy branch "
		+ "discards, and the neutral price vector are derived, never "
		+ "observed from the Flash client; no claim is made about what "
		+ "moving costs in the legacy client",
	"parity covers one recorded transaction against the fresh-player "
		+ "corpus, not progressed players",
	"occupancy, the no-op cell, and grid-bounds rules are enforced "
		+ "client-side only; the endpoint enforces structural input "
		+ "validity and no server-authoritative validation exists",
	"no pixel-parity oracle against the legacy client exists",
	"the capture runs the fake GameApi implementation; real-execution "
		+ "parity is established by the fixture-replay tests and the "
		+ "verify-boot move-live phase",
]

## The sell evidence's explicit non-claims (spec "Sell evidence and claim
## limits"): the carried-forward claims, the derived reason and neutral
## price vector, the NO-REFUND claim limit design D2 and D10 add, the
## unreachable combat reason, the one-transaction parity scope, the
## client-only validation split, the no-pixel-parity claim, and the
## fake-capture pointer. The runtime tokens in the first claim are
## assembled from fragments for the same project-scope reason as the lists
## above.
const SELL_NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the derived sell reason and the neutral price vector are derived, "
		+ "never observed from the Flash client",
	"no refund is claimed: the committed configuration records no "
		+ "building-sale refund rule and the legacy refund travels in "
		+ "client-sent resource deltas this contract refuses to accept; a "
		+ "sale removes the building and changes no balance",
	"the legacy combat reason that would route a row through the "
		+ "resurrectable-unit path is never reached: the endpoint accepts "
		+ "no reason from the client, so only the derived empty log label "
		+ "is sent",
	"parity covers one recorded transaction against the fresh-player "
		+ "corpus, not progressed players",
	"sellability and addressability are client-side rules only; the "
		+ "endpoint enforces structural input validity and no "
		+ "server-authoritative validation exists",
	"no pixel-parity oracle against the legacy client exists",
	"the capture runs the fake GameApi implementation; real-execution "
		+ "parity is established by the fixture-replay tests and the "
		+ "verify-boot sell-live phase",
]

## The store evidence's explicit non-claims (spec "Store evidence and claim
## limits"): the carried-forward claims, the derived argument value and
## neutral vector, the NO-COST and NO-CAPACITY limits design D2 and D9 add,
## the deliberately unwritten bought-units list, the one-way trip design D9
## names, the one-transaction parity scope, the client-only validation split,
## the no-pixel-parity claim, and the fake-capture pointer. The runtime
## tokens in the first claim are assembled from fragments for the same
## project-scope reason as the lists above.
const STORE_NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the command's argument value and the neutral price vector are derived, "
		+ "never observed from the Flash client",
	"no storing cost and no capacity rule are claimed: the committed "
		+ "configuration records neither and the legacy server has no "
		+ "capacity check, so the neutral vector is a derivation boundary, "
		+ "not a claim about the legacy client",
	"the bought-units list is deliberately not written by the legacy branch "
		+ "(it calls no bookkeeping helper), and that is reproduced exactly "
		+ "rather than fixed",
	"this line only moves a building into storage: stored items are not yet "
		+ "playable, and the reverse legacy command (taking a stored item "
		+ "back onto the map) remains open",
	"parity covers one recorded transaction against the fresh-player "
		+ "corpus, not progressed players",
	"storability and addressability are client-side rules only; the "
		+ "endpoint enforces structural input validity and no "
		+ "server-authoritative validation exists",
	"no pixel-parity oracle against the legacy client exists",
	"the capture runs the fake GameApi implementation; real-execution "
		+ "parity is established by the fixture-replay tests and the "
		+ "verify-boot store-live phase",
]

## View states (spec: never claim a rendered town without one).
const STATE_EMPTY := "empty"
const STATE_BUILT := "built"
const STATE_ERROR := "error"

## Authentic legacy stage used for capture evidence (Basesec 1400x600).
const CAPTURE_SIZE := Vector2i(1400, 600)

## UI-foundation slot the build picker occupies (spec: "a build picker
## over a placement catalog").
const SLOT_PLACEMENT := "placement"
## UI-foundation slot the shop occupies (spec: "a shop surface over a
## fail-closed catalog"). Beside the picker, never inside it (design D8):
## the two surfaces own separate slots, entries, and lifecycle.
const SLOT_SHOP := "shop"
## UI-foundation slot the move surface occupies (building-move, design D8).
## Its OWN slot beside the picker and the shop: the move's flow, selection,
## and preview state are never the picker's or the shop's, and neither
## delivered surface is modified by it.
const SLOT_MOVE := "move"
## Picker panel width in pixels (provisional presentation — no legacy
## picker layout has been captured).
const PLACEMENT_PANEL_WIDTH := 300.0
## Shop panel width in pixels (provisional presentation for the same
## reason).
const SHOP_PANEL_WIDTH := 300.0
## Move panel width in pixels (provisional presentation for the same
## reason).
const MOVE_PANEL_WIDTH := 300.0
## The storage readout's indicator lines: the payload carried no storage
## field at all (design D7 — the missing field is named, never presented as
## an empty inventory), and the payload carried a storage object with no
## entries (a real, observed empty storage).
const MISSING_STORAGE_TEXT := "[missing: %s]"
const EMPTY_STORAGE_TEXT := "(empty)"

## The typed town state handed to this view (read-only by contract).
var state: Variant = null
## True once terrain, objects, camera bounds, and HUD are all committed.
var build_ok := false
## View state: empty -> built, or empty -> error with a named failure.
var view_state := STATE_EMPTY
## Why the build failed when view_state is STATE_ERROR.
var build_error := ""
## Town object nodes in committed draw order (non-decreasing depth).
var objects: Array = []
## Committed selection (town object node or null).
var selected: Variant = null

## Placement flow (building-placement, spec "Placement flow"). The
## {ok, error, catalog} catalog envelope committed by the boot handoff —
## null when no caller provided one (the slice scene never does), so
## placement stays unavailable behind an explicit error rather than a
## fabricated entry.
var placement_catalog_result: Variant = null
## The last placement failure ("" until one occurs; cleared on entry and
## after the next success) — the explicit error the spec requires.
var placement_error := ""
var _placement_active := false
## The selected picker entry (PlacementCatalog.Entry or null).
var _placement_entry: Variant = null
## The committed preview evaluation ({ok, error, valid, reason, cells,
## cost}); empty while no target is committed.
var _placement_evaluation: Dictionary = {}
var _placement_cell := Vector2i.ZERO
## The picker's status label (null while no panel is built).
var _placement_status: Variant = null

## Purchase flow (building-purchase, spec "Purchase flow"). The shop is a
## surface BESIDE the picker, never inside it (design D8): it owns its own
## UI-foundation slot, its own entry selection, and its own status line, and
## it never touches the picker's selection, preview, or overlay state. The
## catalog envelope is the same fail-closed parse the boot handoff performs
## (handed to both surfaces); a failed catalog leaves the shop unavailable
## behind an explicit error rather than a fabricated entry or a guessed
## price.
var shop_catalog_result: Variant = null
## The last purchase failure ("" until one occurs; cleared on entry and
## after the next success) — the explicit error the spec requires.
var shop_error := ""
var _shop_active := false
## The selected shop entry (PlacementCatalog.Entry or null).
var _shop_entry: Variant = null
## The shop's status label (null while no panel is built).
var _shop_status: Variant = null
## The storage readout container (null while no panel is built).
var _shop_storage: Variant = null

## Move flow (building-move, spec "Move flow"). The surface is BESIDE the
## picker and the shop (design D8): it owns its own UI-foundation slot, its
## own status line, and its own preview evaluation, and it never touches the
## picker's or the shop's state. It is ARMED FROM THE SELECTION PATH
## (design D8): selecting an addressable placed building offers a `Move`
## action, and pressing it enters move mode with that building's footprint
## previewed through the same iso projection and `placement_preview`
## overlay the picker uses — with the moving building's own cells excluded
## from the occupancy check.
var move_error := ""
var _move_active := false
## The placement being moved (TownState.Placement or null). The
## SAME instance the state holds, so the pure helper's identity-based
## exclusion of its own cells stays correct.
var _move_placement: Variant = null
## The committed preview evaluation ({ok, error, valid, reason, cells, …});
## empty while no target is committed.
var _move_evaluation: Dictionary = {}
var _move_cell := Vector2i.ZERO
## The move panel's status label (null while no panel is built).
var _move_status: Variant = null

## Sell flow (building-sell, spec "Sell flow"). The surface is NOT a third
## panel: it is a second mode of the SAME selection-driven move surface
## (design D8), so it owns no slot, no preview, and no grid target — only
## its own armed state, the placement being sold, and the explicit failure
## the spec requires. The move mode, its preview, and its confirm state
## machine are untouched.
var sell_error := ""
var _sell_active := false
## The placement being sold (TownState.Placement or null). The SAME instance
## the state holds, so the apply removes exactly the row the player chose.
var _sell_placement: Variant = null

## Store flow (building-store, spec "Store flow"). The surface is not a
## fourth panel: it is a THIRD mode of the SAME selection-driven surface
## (design D7), so it owns no slot, no preview, and no grid target — only its
## own armed state, the placement being stored, and the explicit failure the
## spec requires. The move and sell modes, their previews, and their confirm
## state machines are untouched.
var store_error := ""
var _store_active := false
## The placement being stored (TownState.Placement or null). The SAME
## instance the state holds, so the apply removes exactly the row the player
## chose.
var _store_placement: Variant = null

## Visual hierarchy + texture caches (shared across rebuilds of this view).
var _visuals := TownVisuals.new()
## The committed HUD builder once attached.
var _hud: Variant = null
## Explicit registry injection (tests' failure scenario); null = autoload.
var _registry: Variant = null
## Capture mode: absolute PNG path, empty when not capturing.
var _capture_path := ""
var _capture_started := false
## True when the capture flag was `--placement-capture=` (design D11):
## the picker flow runs before the capture so the frame shows the town
## containing the placed building.
var _placement_capture := false
## True when the capture flag was `--purchase-capture=` (design D9): the
## shop flow runs before the capture so the frame shows the town whose
## storage readout carries the purchased item.
var _purchase_capture := false
## True when the capture flag was `--move-capture=` (building-move, design
## D9): the move flow runs before the capture so the frame shows the town
## containing the building at its new cell.
var _move_capture := false
## True when the capture flag was `--sell-capture=` (building-sell, design
## D10): the sell flow runs before the capture so the frame shows the town
## WITHOUT the sold building.
var _sell_capture := false
## True when the capture flag was `--store-capture=` (building-store, design
## D9): the store flow runs before the capture so the frame shows the town
## WITHOUT the stored building and with its storage readout carrying the
## stored item.
var _store_capture := false

@onready var terrain: TownTerrain = $Terrain
@onready var objects_layer: Node2D = $Objects
@onready var camera: CameraControls = $Camera
@onready var ui: UiFoundation = $Ui
@onready var error_label: Label = $Ui/ErrorLabel


func _ready() -> void:
	var report_path := _report_path_arg()
	# Report mode belongs to the town scene's own script: the nested slice
	# is a subclass instance sharing this process's user arguments, and
	# must fall through to its committed-state build instead of
	# re-entering the report flow (which would rebuild the player save a
	# second time from within the slice).
	if not report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_town_report(report_path)
		return
	# The placement report shares the scene-own-script gate: the nested
	# slice instance runs this same `_ready` and must fall through to its
	# committed-state build instead of entering either report flow.
	var placement_report_path := _placement_report_path_arg()
	if not placement_report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_placement_report(placement_report_path)
		return
	# The purchase report shares the same scene-own-script gate: the nested
	# slice instance must fall through to its committed-state build instead
	# of re-entering the report flow (which would re-run the purchase).
	var purchase_report_path := _purchase_report_path_arg()
	if not purchase_report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_purchase_report(purchase_report_path)
		return
	# The move report shares the same scene-own-script gate: the nested slice
	# instance must fall through to its committed-state build instead of
	# re-entering any report flow.
	var move_report_path := _move_report_path_arg()
	if not move_report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_move_report(move_report_path)
		return
	# The sell report shares that gate for the same reason.
	var sell_report_path := _sell_report_path_arg()
	if not sell_report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_sell_report(sell_report_path)
		return
	# The store report shares that gate for the same reason.
	var store_report_path := _store_report_path_arg()
	if not store_report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_store_report(store_report_path)
		return
	_capture_path = _user_arg("--town-capture=")
	_purchase_capture = false
	_move_capture = false
	_sell_capture = false
	_store_capture = false
	if _capture_path.is_empty():
		_capture_path = _user_arg("--placement-capture=")
		_placement_capture = not _capture_path.is_empty()
	if _capture_path.is_empty():
		_capture_path = _user_arg("--purchase-capture=")
		_purchase_capture = not _capture_path.is_empty()
	if _capture_path.is_empty():
		_capture_path = _user_arg("--move-capture=")
		_move_capture = not _capture_path.is_empty()
	if _capture_path.is_empty():
		_capture_path = _user_arg("--sell-capture=")
		_sell_capture = not _capture_path.is_empty()
	if _capture_path.is_empty():
		_capture_path = _user_arg("--store-capture=")
		_store_capture = not _capture_path.is_empty()
	if state != null:
		build()
	_maybe_start_capture()


## Hands the typed state to this view. Builds immediately when already in
## the tree; otherwise the state is committed and built at `_ready` (both
## instantiation orders are supported). Returns the build result.
func set_town_state(town_state: Variant) -> Dictionary:
	state = town_state
	if not is_inside_tree():
		return {"ok": true, "error": "", "deferred": true}
	return build()


## Injects a ContentRegistry (tests' failure scenario). Null restores the
## autoload default at the next build.
func set_registry(registry: Variant) -> void:
	_registry = registry


## Builds the whole view from the committed state. Fail-closed: any
## failure maps to the explicit error state and clears partial views.
func build() -> Dictionary:
	_reset_view()
	if state == null:
		return _enter_error("[town] build rejected: state_missing")
	var registry: RegistryScript = get_node_or_null("/root/ContentRegistry") \
		if _registry == null else _registry
	if registry == null:
		return _enter_error("[town] build rejected: content_registry_unavailable")
	var terrain_result: Dictionary = terrain.build(registry)
	if not bool(terrain_result.get("ok", false)):
		return _enter_error(str(terrain_result.get("error", "")))
	# Depth-sorted draw order with a deterministic tie-break:
	# depth, then grid y, then grid x, then save order (design D8).
	var sorted: Array = state.placements.duplicate()
	sorted.sort_custom(_depth_less)
	for placement in sorted:
		var visual: Dictionary = _visuals.resolve(placement, registry)
		var object := TownObject.new()
		object.setup(placement, _visuals, visual)
		objects_layer.add_child(object)
		objects.append(object)
	var bounds: Dictionary = camera.set_world_bounds(Iso.world_rect())
	if not bool(bounds.get("ok", false)):
		return _enter_error(str(bounds.get("error", "")))
	camera.position = _focus_position()
	_hud = TownHud.new()
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		return _enter_error(str(hud_result.get("error", "")))
	view_state = STATE_BUILT
	build_error = ""
	build_ok = true
	_maybe_start_capture()
	return {"ok": true, "error": ""}


## Commits a selection from a world-space pointer press: converts the
## press to a cell (out-of-ground clears), picks the depth-topmost object
## under it (the last in draw order wins), and highlights it. Rejects
## non-finite presses and unbuilt views without changing selection.
func handle_pointer_press(world_point: Vector2) -> Dictionary:
	if view_state != STATE_BUILT:
		return {"ok": false, "error": "[town] selection rejected: town_not_built"}
	if not world_point.is_finite():
		return {"ok": false,
			"error": "[town] selection rejected: non_finite_press"}
	var grid: Dictionary = Iso.screen_to_grid(world_point)
	if not bool(grid.get("ok", false)):
		_commit_selection(null)
		return {"ok": true, "error": "", "cleared": true, "cell": Vector2i.ZERO}
	var cell: Vector2i = grid["cell"]
	var hit: Variant = null
	for object in objects:
		if object.contains_cell(cell):
			hit = object  # later in draw order = higher in isometric depth
	_commit_selection(hit)
	return {
		"ok": true,
		"error": "",
		"cleared": hit == null,
		"cell": cell,
		"legacy_id": -1 if hit == null else int(hit.legacy_id),
	}


## The committed selection (town object node or null).
func selection() -> Variant:
	return selected


## The selected placement's legacy id (-1 when the selection is empty).
func selection_legacy_id() -> int:
	return -1 if selected == null else int(selected.legacy_id)


## The committed HUD builder once attached (null before a build).
func hud() -> Variant:
	return _hud


## Count of committed objects by chosen visual source (evidence field).
func object_counts_by_source() -> Dictionary:
	var counts := {}
	for object in objects:
		var source := str(object.visual_source)
		counts[source] = int(counts.get(source, 0)) + 1
	return counts


# ---------------------------------------------------------------------------
# Placement flow (building-placement, spec "Placement flow")
# ---------------------------------------------------------------------------


## Commits the typed catalog envelope handed by the boot handoff (or a
## test). Pure state: no view effects — `enter_placement` consumes it.
func set_placement_catalog(result: Dictionary) -> void:
	placement_catalog_result = result


## The picker's entries for the loaded level (store-listed buildings
## the level allows, payload order). Empty while the catalog is
## unavailable — never fabricated.
func placement_catalog_entries() -> Array:
	var catalog: Variant = _placement_catalog()
	if catalog == null or state == null:
		return []
	return PlacementCatalog.picker_entries(catalog, state.summary.level)


## True while the build picker is open.
func placement_active() -> bool:
	return _placement_active


## The selected picker entry (PlacementCatalog.Entry or null).
func placement_entry() -> Variant:
	return _placement_entry


## True while the footprint overlay displays a committed target.
func placement_preview_shown() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.is_shown()


## The overlay's committed cells (anchor order; [] when hidden).
func placement_preview_cells() -> Array:
	var preview: Variant = _placement_preview()
	return [] if preview == null else preview.cells


## The overlay's committed validity (false while hidden).
func placement_preview_valid() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.target_valid


## Opens the build picker over the catalog (spec: "the player opens the
## build picker"). Fail-closed: unbuilt view, missing or failed catalog,
## or an already-open picker rejects with an explicit error naming the
## condition; a successful open resets mode-local selection/target and
## commits the panel into the UI foundation's slot.
func enter_placement() -> Dictionary:
	if view_state != STATE_BUILT:
		return _placement_reject("town_not_built",
			"the town view is not built")
	if _placement_active:
		return _placement_reject("placement_already_active",
			"the build picker is already open")
	if not (placement_catalog_result is Dictionary):
		return _placement_reject("placement_unavailable",
			"the placement catalog was never provided")
	if not bool((placement_catalog_result as Dictionary).get("ok", false)):
		return _placement_reject("placement_unavailable",
			"the placement catalog failed to parse: %s"
			% str((placement_catalog_result as Dictionary).get("error", "")))
	var entries := placement_catalog_entries()
	var panel := _build_placement_panel(entries)
	if not bool(panel.get("ok", false)):
		return _placement_reject("placement_panel",
			str(panel.get("error", "")))
	_placement_active = true
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	placement_error = ""
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and not ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, true)
	_set_placement_status("pick a building (%d available at level %d)"
		% [entries.size(), state.summary.level])
	return {"ok": true, "error": "", "entries": entries.size()}


## Selects one picker entry (spec: "chooses a store-listed building
## their level allows"). An id the catalog lacks names the id; an id the
## level gate withholds names the gate — never offered, never guessed.
## A committed target re-evaluates against the new pick's cost.
func pick_placement(item_id: int) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	var chosen: Variant = null
	for entry: Variant in placement_catalog_entries():
		if entry is PlacementCatalog.Entry and entry.id == item_id:
			chosen = entry
			break
	if chosen == null:
		if PlacementCatalog.find_entry(_placement_catalog(),
				item_id) == null:
			return _placement_reject("unknown_item_id",
				"no catalog entry with id %d" % item_id)
		return _placement_reject("item_not_available",
			"item %d is not store-listed at level %d"
			% [item_id, state.summary.level])
	_placement_entry = chosen
	_set_placement_status("%s %dx%d | cost: %s" % [chosen.name,
		chosen.width, chosen.height,
		PlacementFlow.cost_against_text(state, chosen.costs)])
	if not _placement_evaluation.is_empty():
		preview_placement_cell(_placement_cell)
	return {"ok": true, "error": "", "item_id": item_id}


## Commits a preview target (spec: "a footprint preview at the
## inverse-projected cell"): the overlay shows the footprint colored by
## validity, the status names the reason while invalid, and the
## evaluation is returned for assertions. Invalid targets are shown and
## marked — never sent.
func preview_placement_cell(cell: Vector2i) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if _placement_entry == null:
		return _placement_reject("placement_no_selection",
			"no building is selected")
	var evaluation: Dictionary = PlacementFlow.preview(state,
		_placement_entry, cell)
	if not bool(evaluation.get("ok", false)):
		return _placement_reject("preview_unavailable",
			str(evaluation.get("error", "")))
	_placement_cell = cell
	_placement_evaluation = evaluation
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.show_cells(evaluation["cells"], bool(evaluation["valid"]))
	var target := "%s at (%d, %d)" % [_placement_entry.name, cell.x,
		cell.y]
	var cost := PlacementFlow.cost_against_text(state, evaluation["cost"])
	if bool(evaluation["valid"]):
		_set_placement_status("%s | cost: %s" % [target, cost])
	else:
		_set_placement_status("%s | invalid: %s | cost: %s"
			% [target, str(evaluation["reason"]), cost])
	return evaluation


## Left press in placement mode: converts to a cell and previews it; a
## press off the ground drops the target (the selection path clears the
## same way) without leaving the mode.
func handle_placement_press(world_point: Vector2) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if not world_point.is_finite():
		return _placement_reject("non_finite_press",
			"the press is not finite")
	var grid: Dictionary = Iso.screen_to_grid(world_point)
	if not bool(grid.get("ok", false)):
		_placement_cell = Vector2i.ZERO
		_placement_evaluation = {}
		var overlay: Variant = _placement_preview()
		if overlay != null:
			overlay.clear()
		_set_placement_status("no target")
		return {"ok": true, "error": "", "cleared": true}
	return preview_placement_cell(grid["cell"])


## Sends exactly one placement intent (spec: "a confirm that sends
## exactly one intent") and applies only the authoritative response.
## Nothing is sent unless the mode, a selection, and a valid target are
## committed: an invalid target, a missing session, or a missing API
## rejects locally with the explicit error and no request. A structured
## or transport failure surfaces its code with no state change (design
## D7). Awaits the GameApi call.
func confirm_placement() -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if _placement_entry == null:
		return _placement_reject("placement_no_selection",
			"no building is selected")
	if _placement_evaluation.is_empty():
		return _placement_reject("placement_no_target",
			"no preview target is committed")
	if not bool(_placement_evaluation.get("valid", false)):
		return _placement_reject("invalid_target",
			"the preview at (%d, %d) is %s" % [_placement_cell.x,
				_placement_cell.y,
				str(_placement_evaluation.get("reason", ""))])
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _placement_reject("session_unavailable",
			"no active save to place into")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _placement_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	var response: Variant = await api.place_building(session.user_id(),
		_placement_entry.id, _placement_cell.x, _placement_cell.y, 0)
	if not (response is BootData.PlacementResult):
		return _placement_reject("bad_response",
			"GameApi returned no typed placement result")
	var typed: BootData.PlacementResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit
		# error names the code and message, nothing was applied.
		placement_error = "[town] placement failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_placement_status(placement_error)
		return {"ok": false, "error": placement_error,
			"code": typed.error_code}
	var applied: Dictionary = _apply_placement(typed)
	if not bool(applied.get("ok", false)):
		return _placement_reject("apply_failed",
			str(applied.get("error", "")))
	placement_error = ""
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	_set_placement_status("placed %s at (%d, %d)" % [
		_placement_entry.name, typed.placement.x, typed.placement.y])
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (design D7): the typed entry
## becomes a depth-sorted object at its cell, the stored resources and
## XP take the response's values (never a computed delta), and the HUD
## re-attaches to read them. Pre-checks run before any mutation; the
## only post-mutation failure — a rejected HUD re-attach — rolls every
## write back, so a failed apply changes nothing.
func _apply_placement(result: BootData.PlacementResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	var registry: RegistryScript = get_node_or_null("/root/ContentRegistry") \
		if _registry == null else _registry
	if registry == null:
		return {"ok": false,
			"error": "the ContentRegistry autoload is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	var entry: BootData.Placement = result.placement
	var resources: BootData.Resources = result.resources
	if entry == null or resources == null:
		return {"ok": false, "error": "the placement response is incomplete"}
	var placement := TownState.Placement.new()
	placement.item = entry.item_id
	placement.cell = Vector2i(entry.x, entry.y)
	placement.timestamp = entry.timestamp
	placement.orientation = entry.orientation
	placement.store = entry.store
	placement.attr = entry.attr
	placement.player = entry.player
	placement.raw = [entry.item_id, entry.x, entry.y, entry.timestamp,
		entry.orientation, entry.store, entry.attr, entry.player]
	placement.order = state.placements.size()
	TownState._resolve_content(placement, registry)
	var previous := {
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"energy": state.resources.energy,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	state.placements.append(placement)
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var visual: Dictionary = _visuals.resolve(placement, registry)
	var object := TownObject.new()
	object.setup(placement, _visuals, visual)
	# Insert where the depth comparator puts it, so the committed draw
	# order stays sorted exactly as a full rebuild would produce it.
	var index := objects.size()
	for i in range(objects.size()):
		if _depth_less(placement, objects[i].placement):
			index = i
			break
	objects.insert(index, object)
	objects_layer.add_child(object)
	objects_layer.move_child(object, index)
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back: a failed apply changes nothing.
		state.placements.remove_at(state.placements.size() - 1)
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		objects.remove_at(index)
		objects_layer.remove_child(object)
		object.free()
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The response supplies values the payload may have lacked.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	return {"ok": true, "error": ""}


## Closes the picker without sending anything: mode-local selection,
## target, and overlay drop, the slot hides, and the town state,
## selection, and resources stay byte-identical.
func cancel_placement() -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	_placement_active = false
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)
	_set_placement_status("placement closed")
	return {"ok": true, "error": "", "cancelled": true}


## Builds the picker into the UI-foundation slot (registered once,
## contents replaced per open — the HUD attach precedent). The panel is
## hidden while building; `enter_placement` shows it once committed.
## Fail-closed envelope: a rejected registration or missing slot root
## returns {ok:false} and commits no visible panel.
func _build_placement_panel(entries: Array) -> Dictionary:
	if ui == null:
		return {"ok": false, "error": "the UI foundation is unavailable"}
	if not ui.has_slot(SLOT_PLACEMENT):
		var registration: Dictionary = ui.register_slot(SLOT_PLACEMENT)
		if not bool(registration.get("ok", false)):
			return {"ok": false,
				"error": str(registration.get("error", "rejected"))}
	if ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)
	var root: Control = ui.slot_root(SLOT_PLACEMENT)
	if root == null:
		return {"ok": false,
			"error": "the placement slot root is unavailable"}
	for child in root.get_children():
		root.remove_child(child)
		child.free()
	_placement_status = null
	var panel := VBoxContainer.new()
	panel.name = "picker"
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -PLACEMENT_PANEL_WIDTH
	panel.offset_right = -8.0
	panel.offset_top = 8.0
	panel.offset_bottom = -8.0
	panel.add_theme_constant_override("separation", 2)
	root.add_child(panel)
	var title := Label.new()
	title.text = "Build"
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(title)
	panel.add_child(title)
	for entry: Variant in entries:
		if not (entry is PlacementCatalog.Entry):
			continue
		var typed: PlacementCatalog.Entry = entry
		var button := Button.new()
		button.name = "item_%d" % typed.id
		button.text = "%s  %dx%d  %s" % [typed.name, typed.width,
			typed.height, PlacementFlow.cost_text(typed.costs)]
		button.pressed.connect(_on_placement_pick.bind(typed.id))
		panel.add_child(button)
	var status := Label.new()
	status.name = "status"
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(status)
	panel.add_child(status)
	_placement_status = status
	var row := HBoxContainer.new()
	row.name = "actions"
	var confirm := Button.new()
	confirm.name = "confirm"
	confirm.text = "Place"
	confirm.pressed.connect(_on_placement_confirm)
	row.add_child(confirm)
	var cancel := Button.new()
	cancel.name = "cancel"
	cancel.text = "Cancel"
	cancel.pressed.connect(_on_placement_cancel)
	row.add_child(cancel)
	panel.add_child(row)
	return {"ok": true, "error": ""}


## Writes the picker status line (no-op before a panel exists).
func _set_placement_status(text: String) -> void:
	if _placement_status != null and is_instance_valid(_placement_status):
		(_placement_status as Label).text = text


## Provisional label styling: white text with a dark shadow, matching
## the HUD's readable-over-terrain treatment.
func _style_placement_label(label: Label) -> void:
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_shadow_color",
		Color(0, 0, 0, 0.85))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)


## The typed catalog envelope's catalog (null when absent or failed).
func _placement_catalog() -> Variant:
	if not (placement_catalog_result is Dictionary):
		return null
	var envelope := placement_catalog_result as Dictionary
	if not bool(envelope.get("ok", false)):
		return null
	return envelope.get("catalog")


## The footprint overlay node (null in scenes that wire no placement
## layer — the flow never opens there because no catalog is committed).
func _placement_preview() -> Variant:
	return get_node_or_null("Placement")


## The house failure envelope: records the explicit error naming the
## code and condition, shows it in the picker status when open, and
## returns {ok:false} without touching town state, selection, or
## resources.
func _placement_reject(code: String, message: String) -> Dictionary:
	placement_error = "[town] placement rejected: %s: %s" % [code, message]
	_set_placement_status(placement_error)
	return {"ok": false, "error": placement_error, "code": code}


## Picker button wiring: a press picks that entry.
func _on_placement_pick(item_id: int) -> void:
	pick_placement(item_id)


## Picker button wiring: confirm sends (awaits the one intent).
func _on_placement_confirm() -> void:
	await confirm_placement()


## Picker button wiring: cancel closes with no request.
func _on_placement_cancel() -> void:
	cancel_placement()


# ---------------------------------------------------------------------------
# Purchase flow (building-purchase, spec "Purchase flow")
# ---------------------------------------------------------------------------


## Commits the typed catalog envelope handed by the boot handoff (or a
## test) to the SHOP surface. Pure state: no view effects — `enter_shop`
## consumes it. The boot handoff hands the very same envelope it hands the
## placement picker (one fail-closed parse, two consumers, no second
## config request).
func set_shop_catalog(result: Dictionary) -> void:
	shop_catalog_result = result


## The shop's entries for the loaded level: store-listed entries the level
## allows whose config price is a cash price, payload order (11 at level 1
## of the fresh save). Empty while the catalog is unavailable — never
## fabricated, never a guessed price.
func shop_catalog_entries() -> Array:
	var catalog: Variant = _shop_catalog()
	if catalog == null or state == null:
		return []
	return ShopFlow.shop_entries(catalog, state.summary.level)


## True while the shop is open.
func shop_active() -> bool:
	return _shop_active


## The selected shop entry (PlacementCatalog.Entry or null).
func shop_entry() -> Variant:
	return _shop_entry


## The storage readout lines currently rendered: one per stored item, the
## explicit missing-field indicator when the payload carried no storage, or
## the empty-storage indicator. A resolved content name when ContentRegistry
## knows the id, the raw item id otherwise — never a guessed name
## (design D7).
func storage_rows() -> Array:
	var rows: Array = storage_texts()
	rows.sort()
	return rows


## Opens the shop over the catalog (spec: "the player opens the shop
## surface"). Fail-closed: an unbuilt view, a missing or failed catalog, or
## an already-open shop rejects with an explicit error naming the
## condition; a successful open resets the mode-local selection, commits
## the panel into its own UI-foundation slot, and renders the storage
## readout.
func enter_shop() -> Dictionary:
	if view_state != STATE_BUILT:
		return _shop_reject("town_not_built", "the town view is not built")
	if _shop_active:
		return _shop_reject("shop_already_active", "the shop is already open")
	if not (shop_catalog_result is Dictionary):
		return _shop_reject("shop_unavailable",
			"the shop catalog was never provided")
	if not bool((shop_catalog_result as Dictionary).get("ok", false)):
		return _shop_reject("shop_unavailable",
			"the shop catalog failed to parse: %s"
			% str((shop_catalog_result as Dictionary).get("error", "")))
	var entries := shop_catalog_entries()
	var panel := _build_shop_panel(entries)
	if not bool(panel.get("ok", false)):
		return _shop_reject("shop_panel", str(panel.get("error", "")))
	_shop_active = true
	_shop_entry = null
	shop_error = ""
	if ui != null and ui.has_slot(SLOT_SHOP) \
			and not ui.is_slot_visible(SLOT_SHOP):
		ui.set_slot_visible(SLOT_SHOP, true)
	_set_shop_status("pick an item to buy (%d available at level %d)"
		% [entries.size(), state.summary.level])
	_render_storage()
	return {"ok": true, "error": "", "entries": entries.size()}


## Selects one shop entry (spec: "chooses a store-listed, cash-priced item
## their level allows"). An id the catalog lacks names the id; an id the
## level gate or the cash-price rule withholds names that gate — never
## offered, never guessed, never priced.
func pick_shop_item(item_id: int) -> Dictionary:
	if not _shop_active:
		return _shop_reject("shop_not_active", "the shop is not open")
	var chosen: Variant = null
	for entry: Variant in shop_catalog_entries():
		if entry is PlacementCatalog.Entry and entry.id == item_id:
			chosen = entry
			break
	if chosen == null:
		return _shop_reject(_withheld_reason(item_id),
			_withheld_detail(item_id))
	_shop_entry = chosen
	var evaluation: Dictionary = ShopFlow.evaluate(state, chosen)
	if bool(evaluation.get("ok", false)) \
			and not bool(evaluation.get("purchasable", true)):
		# Not a rejection: the entry is offered, the price is simply
		# currently unaffordable. The refusal text is shown so the player
		# can read why, and the confirm will refuse with no request.
		_set_shop_status("%s | %s" % [chosen.name,
			ShopFlow.refusal_text(evaluation)])
	else:
		_set_shop_status("%s | price: %s" % [chosen.name,
			ShopFlow.price_against_cash_text(state, chosen)])
	return {"ok": true, "error": "", "item_id": item_id}


## Sends exactly one purchase intent (spec: "a purchase confirm that sends
## exactly one intent") and applies only the authoritative response.
## Nothing is sent unless the surface, a selection, an affordable price, an
## active session, and a registered API are all committed: an unaffordable
## price, a missing session, or a missing API rejects locally with the
## explicit error and no request. A structured or transport failure surfaces
## its code with no state change (design D7). Awaits the GameApi call.
func confirm_purchase() -> Dictionary:
	if not _shop_active:
		return _shop_reject("shop_not_active", "the shop is not open")
	if _shop_entry == null:
		return _shop_reject("shop_no_selection", "no shop entry is selected")
	var evaluation: Dictionary = ShopFlow.evaluate(state, _shop_entry)
	if not bool(evaluation.get("ok", false)):
		return _shop_reject("shop_evaluation",
			str(evaluation.get("error", "")))
	if not bool(evaluation.get("purchasable", false)):
		# The client owns affordability (design D5): refuse locally, send
		# nothing, and name the reason with the two numbers it compares.
		return _shop_reject("not_purchasable",
			ShopFlow.refusal_text(evaluation))
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _shop_reject("session_unavailable",
			"no active save to buy into")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _shop_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	var response: Variant = await api.purchase_item(session.user_id(),
		int(_shop_entry.id))
	if not (response is BootData.PurchaseResult):
		return _shop_reject("bad_response",
			"GameApi returned no typed purchase result")
	var typed: BootData.PurchaseResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit
		# error names the code and message, nothing was applied.
		shop_error = "[town] purchase failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_shop_status(shop_error)
		return {"ok": false, "error": shop_error, "code": typed.error_code}
	var applied: Dictionary = _apply_purchase(typed)
	if not bool(applied.get("ok", false)):
		return _shop_reject("apply_failed", str(applied.get("error", "")))
	shop_error = ""
	var quantity := int(state.storage.get(str(int(_shop_entry.id)), 0))
	_set_shop_status("bought %s (x%d in storage)" % [_shop_entry.name, quantity])
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (design D4/D7): the typed storage
## mapping replaces the state's storage through the SAME fail-closed parser
## the payload parse used (never a computed delta, never a partial write),
## the stored resources and XP take the response's values verbatim, the
## storage readout and the HUD re-render from them, and the fields the
## response supplies are no longer missing. Pre-checks run before any
## mutation; the only post-mutation failure — a rejected HUD re-attach —
## rolls every write back, so a failed apply changes nothing.
func _apply_purchase(result: BootData.PurchaseResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	var resources: BootData.Resources = result.resources
	if resources == null:
		return {"ok": false, "error": "the purchase response is incomplete"}
	# The response's storage is read with the payload's own parser: one
	# rule set, so a response can never be interpreted differently than
	# the save it replaces.
	var storage: Dictionary = TownState.storage_of(result.store)
	if not bool(storage.get("ok", false)):
		return {"ok": false, "error": str(storage.get("error", ""))}
	var previous := {
		"storage": (state.storage as Dictionary).duplicate(),
		"missing": (state.missing as Array).duplicate(),
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	state.storage = (storage["storage"] as Dictionary).duplicate()
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back: a failed apply changes nothing.
		state.storage = previous["storage"]
		state.missing = previous["missing"]
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		_render_storage()
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The response supplies values the payload may have lacked.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	state.missing.erase(TownState.STORAGE_MISSING_KEY)
	_render_storage()
	return {"ok": true, "error": ""}


## Closes the shop without sending anything: the mode-local selection
## drops, the slot hides, and the town state, selection, and resources stay
## byte-identical.
func cancel_shop() -> Dictionary:
	if not _shop_active:
		return _shop_reject("shop_not_active", "the shop is not open")
	_shop_active = false
	_shop_entry = null
	if ui != null and ui.has_slot(SLOT_SHOP) \
			and ui.is_slot_visible(SLOT_SHOP):
		ui.set_slot_visible(SLOT_SHOP, false)
	_set_shop_status("shop closed")
	return {"ok": true, "error": "", "cancelled": true}


## Builds the shop into its own UI-foundation slot (registered once,
## contents replaced per open — the picker/HUD attach precedent). The panel
## is hidden while building; `enter_shop` shows it once committed.
## Fail-closed envelope: a rejected registration or missing slot root
## returns {ok:false} and commits no visible panel.
func _build_shop_panel(entries: Array) -> Dictionary:
	if ui == null:
		return {"ok": false, "error": "the UI foundation is unavailable"}
	if not ui.has_slot(SLOT_SHOP):
		var registration: Dictionary = ui.register_slot(SLOT_SHOP)
		if not bool(registration.get("ok", false)):
			return {"ok": false,
				"error": str(registration.get("error", "rejected"))}
	if ui.is_slot_visible(SLOT_SHOP):
		ui.set_slot_visible(SLOT_SHOP, false)
	var root: Control = ui.slot_root(SLOT_SHOP)
	if root == null:
		return {"ok": false, "error": "the shop slot root is unavailable"}
	for child in root.get_children():
		root.remove_child(child)
		child.free()
	_shop_status = null
	_shop_storage = null
	var panel := VBoxContainer.new()
	panel.name = "shop"
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -SHOP_PANEL_WIDTH
	panel.offset_right = -8.0
	panel.offset_top = 8.0
	panel.offset_bottom = -8.0
	panel.add_theme_constant_override("separation", 2)
	root.add_child(panel)
	var title := Label.new()
	title.name = "title"
	title.text = "Shop"
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(title)
	panel.add_child(title)
	for entry: Variant in entries:
		if not (entry is PlacementCatalog.Entry):
			continue
		var typed: PlacementCatalog.Entry = entry
		var button := Button.new()
		button.name = "item_%d" % typed.id
		button.text = "%s  %s" % [typed.name, ShopFlow.price_text(typed)]
		button.tooltip_text = ShopFlow.price_against_cash_text(state, typed)
		button.pressed.connect(_on_shop_pick.bind(typed.id))
		panel.add_child(button)
	var storage_title := Label.new()
	storage_title.name = "storage"
	storage_title.text = "Storage"
	storage_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(storage_title)
	panel.add_child(storage_title)
	var storage_box := VBoxContainer.new()
	storage_box.name = "storage_entries"
	storage_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	storage_box.add_theme_constant_override("separation", 1)
	panel.add_child(storage_box)
	_shop_storage = storage_box
	var status := Label.new()
	status.name = "status"
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(status)
	panel.add_child(status)
	_shop_status = status
	var row := HBoxContainer.new()
	row.name = "actions"
	var confirm := Button.new()
	confirm.name = "confirm"
	confirm.text = "Buy"
	confirm.pressed.connect(_on_shop_confirm)
	row.add_child(confirm)
	var cancel := Button.new()
	cancel.name = "cancel"
	cancel.text = "Cancel"
	cancel.pressed.connect(_on_shop_cancel)
	row.add_child(cancel)
	panel.add_child(row)
	return {"ok": true, "error": ""}


## Re-renders the storage readout in place (one label per row, the
## indicator lines included), leaving the entry buttons and the status
## label untouched. A no-op before a panel exists.
func _render_storage() -> void:
	if _shop_storage == null or not is_instance_valid(_shop_storage):
		return
	var box := _shop_storage as VBoxContainer
	for child in box.get_children():
		box.remove_child(child)
		child.free()
	for text: String in storage_rows():
		var row := Label.new()
		row.name = "storage_entry"
		row.text = text
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_style_placement_label(row)
		box.add_child(row)


## The readout lines in a stable order: the indicator lines while the state
## carries no storage, else one line per stored item sorted by the numeric
## item id. A resolved content name when ContentRegistry knows the id, the
## raw id otherwise — never a guessed name. Quantity `0` is shown as
## stored (it occurs in real saves), never hidden.
func storage_texts() -> Array:
	if state == null:
		return [MISSING_STORAGE_TEXT]
	if state.missing.has(TownState.STORAGE_MISSING_KEY):
		return [MISSING_STORAGE_TEXT % TownState.STORAGE_MISSING_KEY]
	var ids := _storage_ids(state.storage)
	if ids.is_empty():
		return [EMPTY_STORAGE_TEXT]
	var registry: RegistryScript = get_node_or_null("/root/ContentRegistry") \
		if _registry == null else _registry
	var lines: Array = []
	for id_text: String in ids:
		lines.append(_storage_row(int(id_text),
			int(state.storage[id_text]), registry))
	return lines


## One readout line: the resolved content name and its quantity, or the
## raw item id with an explicit unresolved marker.
func _storage_row(item_id: int, quantity: int, registry: Variant) -> String:
	var name := TownState.content_name(item_id, registry)
	if name == "":
		return "item %d  x%d  (name unresolved)" % [item_id, quantity]
	return "%s  x%d  (item %d)" % [name, quantity, item_id]


## The storage keys as digit strings in ascending numeric order, so the
## readout (and the evidence report) are deterministic regardless of the
## payload's key order.
func _storage_ids(storage: Dictionary) -> Array:
	var ids: Array = []
	for key: Variant in storage:
		ids.append(str(key))
	ids.sort_custom(func(a: String, b: String) -> bool: return int(a) < int(b))
	return ids


## Writes the shop status line (no-op before a panel exists).
func _set_shop_status(text: String) -> void:
	if _shop_status != null and is_instance_valid(_shop_status):
		(_shop_status as Label).text = text


## The shop catalog envelope's catalog (null when absent or failed).
func _shop_catalog() -> Variant:
	if not (shop_catalog_result is Dictionary):
		return null
	var envelope := shop_catalog_result as Dictionary
	if not bool(envelope.get("ok", false)):
		return null
	return envelope.get("catalog")


## Why an id the shop did not offer is withheld: an id the catalog lacks, an
## entry the level gate withholds, or an entry this command cannot price in
## cash (design D2's derivation boundary, not a gameplay rule).
func _withheld_reason(item_id: int) -> String:
	var entry: Variant = PlacementCatalog.find_entry(_shop_catalog(), item_id)
	if entry == null:
		return "unknown_item_id"
	return "item_not_available"


## The explicit message for a withheld id (naming the id and the gate).
func _withheld_detail(item_id: int) -> String:
	var entry: Variant = PlacementCatalog.find_entry(_shop_catalog(), item_id)
	if entry == null:
		return "no catalog entry with id %d" % item_id
	if not entry.in_store:
		return "item %d is not store-listed" % item_id
	if int(entry.min_level) > int(state.summary.level):
		return "item %d is not available at level %d" % [
			item_id, int(state.summary.level)]
	return "item %d is not priced in cash, so this shop cannot buy it" \
		% item_id


## The house shop failure envelope: records the explicit error naming the
## code and condition, shows it in the shop status when open, and returns
## {ok:false} without touching town state, storage, or resources.
func _shop_reject(code: String, message: String) -> Dictionary:
	shop_error = "[town] purchase rejected: %s: %s" % [code, message]
	_set_shop_status(shop_error)
	return {"ok": false, "error": shop_error, "code": code}


# ---------------------------------------------------------------------------
# Move flow (building-move, spec "Move flow")
# ---------------------------------------------------------------------------


## True while the move surface is armed.
func move_active() -> bool:
	return _move_active


## The placement the armed move targets (TownState.Placement or null).
func move_placement() -> Variant:
	return _move_placement


## The addressable index the armed move names (-1 when unaddressable or
## unarmed) — the item index a move intent carries.
func move_slot() -> int:
	if _move_placement == null:
		return TownState.NO_SLOT
	return int(_move_placement.slot)


## The overlay's committed cells for the armed move (anchor order; [] when
## hidden).
func move_preview_cells() -> Array:
	var preview: Variant = _placement_preview()
	return [] if preview == null else preview.cells


## The overlay's committed validity for the armed move (false while hidden).
func move_preview_valid() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.target_valid


## True while a footprint preview is displayed for the armed move.
func move_preview_shown() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.is_shown()


## The armed move's committed evaluation (empty while no target is
## committed) — the same evaluation the confirm reads.
func move_evaluation() -> Dictionary:
	return _move_evaluation


## True when the current selection is a placed building a move intent can
## name (spec "Placements carry their legacy key": an unaddressable key is
## never coerced, so it is never offered). False with no selection.
func move_selection_available() -> bool:
	if selected == null or not (selected is TownObject):
		return false
	var object: TownObject = selected
	return TownState.is_addressable(object.placement)


## Arms the move on the current selection (spec "the player selects a placed
## building, arms the move"). Fail-closed: an unbuilt view, no selection, a
## selection that is not a placement, an unaddressable legacy key, an
## already-armed move, or a missing panel each reject with an explicit error
## naming the condition; a successful arm resets the mode-local target,
## previews the building's CURRENT footprint through the shared overlay (so
## the player sees what is being moved), and commits the panel into its own
## UI-foundation slot.
##
## It is armed from the selection path only (design D8) and adds no state
## and no request: nothing leaves the client until a confirm.
func arm_move() -> Dictionary:
	if view_state != STATE_BUILT:
		return _move_reject("town_not_built", "the town view is not built")
	if _move_active:
		return _move_reject("move_already_active", "the move is already armed")
	if _sell_active:
		# The modes share one selection-driven surface and never stack
		# (building-sell design D8, extended by building-store design D7).
		# Unreachable in the delivered move flow, which never arms a sale or
		# a store.
		return _move_reject("sell_already_active",
			"a sale is armed; cancel it before moving")
	if _store_active:
		# The same one-surface rule for the third mode: a store is armed, so
		# a move is refused by name rather than silently re-targeting it.
		return _move_reject("store_already_active",
			"a store is armed; cancel it before moving")
	if selected == null:
		return _move_reject("move_no_selection",
			"no placed building is selected")
	if not (selected is TownObject):
		return _move_reject("move_no_selection",
			"the selection is not a placed building")
	var object: TownObject = selected
	var placement: Variant = object.placement
	if not (placement is TownState.Placement):
		return _move_reject("move_no_selection",
			"the selected object carries no typed placement")
	if not TownState.is_addressable(placement):
		# Design D7: refused by name. The index is never coerced, because a
		# coerced index would address a different row.
		return _move_reject(MoveFlow.REASON_UNADDRESSABLE,
			"the selected placement's save key '%s' is not a positive integer"
			% str(placement.slot_key))
	_move_active = true
	_move_placement = placement
	_move_evaluation = {}
	_move_cell = Vector2i.ZERO
	move_error = ""
	var panel := _build_move_panel(true)
	if not bool(panel.get("ok", false)):
		return _move_reject("move_panel", str(panel.get("error", "")))
	var overlay: Variant = _placement_preview()
	if overlay != null:
		# The building's current footprint, so the armed state shows what is
		# being moved before any target is committed.
		overlay.show_cells(MoveFlow.footprint_cells(placement.cell,
			placement.footprint), true)
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and not ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, true)
	_refresh_move_panel()
	return {"ok": true, "error": "", "slot": int(placement.slot),
		"item": int(placement.item)}


## The selection-path `Move` action (design D8). Selecting a placed building
## that has an addressable legacy key offers a `Move` button in the move
## surface's own slot; pressing it arms the move. Fail-closed and purely
## presentational: an unbuilt view, or a selection the move flow refuses,
## disables the action and names the reason rather than hiding the state, so
## a player learns why an unaddressable row cannot be moved (design D7). It
## adds no state and no request of its own and never alters the delivered
## selection behavior.
func refresh_move_action() -> Dictionary:
	if view_state != STATE_BUILT or ui == null:
		return _move_reject("town_not_built", "the town view is not built")
	var panel := _build_move_panel(false)
	if not bool(panel.get("ok", false)):
		return _move_reject("move_panel", str(panel.get("error", "")))
	_refresh_move_panel()
	if not _move_active and selected != null:
		ui.set_slot_visible(SLOT_MOVE, true)
	return {"ok": true, "error": ""}


## Renders the move panel's current state into its committed controls (the
## selection line, the status line, the three selection-path actions' states,
## and the shared confirm row) so the panel text always names the live
## selection. A no-op while no panel is built.
##
## The panel carries ALL THREE modes of this selection-driven surface (design
## D8, extended by building-store design D7): `Move`, `Sell`, and `Store` are
## armed from the same selection, exactly one of them can be armed at a time,
## and the single confirm row names whichever mode is armed. The move arming,
## its preview, and its target requirements are untouched by the other two,
## and the sell arming is untouched by the store.
func _refresh_move_panel() -> void:
	var arm_button: Variant = _move_panel_button("move")
	if arm_button is Button:
		var available := move_selection_available()
		(arm_button as Button).disabled = _move_active or _sell_active \
			or _store_active or not available
		(arm_button as Button).text = "Move" if available \
			else "Move (unavailable)"
	var sell_button: Variant = _move_panel_button("sell")
	if sell_button is Button:
		var sell_available := sell_selection_available()
		(sell_button as Button).disabled = _sell_active or _move_active \
			or _store_active or not sell_available
		(sell_button as Button).text = "Sell" if sell_available \
			else "Sell (unavailable)"
	var store_button: Variant = _move_panel_button("store")
	if store_button is Button:
		var store_available := store_selection_available()
		(store_button as Button).disabled = _store_active or _move_active \
			or _sell_active or not store_available
		(store_button as Button).text = "Put in storage" if store_available \
			else "Put in storage (unavailable)"
	var confirm_button: Variant = _move_panel_button("confirm")
	if confirm_button is Button:
		# A sale and a store have no grid target, so their confirm is offered
		# as soon as the mode is armed; a move's only once a valid target is
		# committed (the move suite's own gate, unchanged).
		(confirm_button as Button).visible = _move_active or _sell_active \
			or _store_active
		(confirm_button as Button).text = "Sell" if _sell_active \
			else ("Put in storage" if _store_active else "Move here")
	if _move_status == null or not is_instance_valid(_move_status):
		return
	if _store_active:
		if _store_placement is TownState.Placement:
			_set_move_status("armed: store %s (save key %d) from (%d, %d) "
				% [_move_label(_store_placement), int(_store_placement.slot),
					_store_placement.cell.x, _store_placement.cell.y]
				+ "-> storage | cost: none claimed, capacity: none claimed")
		return
	if _sell_active:
		if _sell_placement is TownState.Placement:
			_set_move_status("armed: sell %s (save key %d) at (%d, %d) "
				% [_move_label(_sell_placement), int(_sell_placement.slot),
					_sell_placement.cell.x, _sell_placement.cell.y]
				+ "| refund: none claimed")
		return
	if not _move_active:
		if selected == null:
			_set_move_status("select a placed building to move it")
		elif not move_selection_available():
			var chosen: Variant = selected.placement
			_set_move_status("not movable: save key '%s' is not a positive "
				% str(chosen.slot_key)
				+ "integer, so no move can name this row")
		else:
			_set_move_status("selected %s (save key %d): press Move"
				% [_move_label(selected.placement),
					int(selected.placement.slot)])
		return
	if _move_placement is TownState.Placement:
		_set_move_status("armed: %s (save key %d) at (%d, %d) | free: no price"
			% [_move_label(_move_placement), int(_move_placement.slot),
				_move_placement.cell.x, _move_placement.cell.y])


## The named button anywhere inside the move panel (the action row nests the
## arm/confirm/cancel trio), or null.
func _move_panel_button(button_name: String) -> Variant:
	if ui == null or not ui.has_slot(SLOT_MOVE):
		return null
	var root: Control = ui.slot_root(SLOT_MOVE)
	if root == null or root.get_child_count() == 0:
		return null
	return _named_button(root.get_child(0) as Node, button_name)


## The named button inside one panel subtree, or null.
func _named_button(panel: Node, button_name: String) -> Variant:
	for child: Variant in panel.get_children():
		if child is Button and String((child as Button).name) == button_name:
			return child
		if child is Node:
			var nested: Variant = _named_button(child as Node, button_name)
			if nested != null:
				return nested
	return null


## Commits a preview target (spec "previews a free in-grid cell ... with a
## footprint preview"): the overlay shows the footprint colored by validity
## — with the moving building's own cells excluded from occupancy, so a
## target overlapping only itself stays valid — the status names the reason
## while invalid, and the evaluation is returned for assertions. Invalid
## targets are shown and marked, never sent.
func preview_move_cell(cell: Vector2i) -> Dictionary:
	if not _move_active:
		return _move_reject("move_not_active", "the move is not armed")
	if _move_placement == null:
		return _move_reject("move_no_selection", "no building is selected")
	var evaluation: Dictionary = MoveFlow.preview(state, _move_placement, cell)
	if not bool(evaluation.get("ok", false)):
		return _move_reject("preview_unavailable",
			str(evaluation.get("error", "")))
	_move_cell = cell
	_move_evaluation = evaluation
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.show_cells(evaluation["cells"], bool(evaluation["valid"]))
	var target := "%s at (%d, %d)" % [_move_label(_move_placement), cell.x,
		cell.y]
	if bool(evaluation["valid"]):
		_set_move_status("move: %s | free: no price" % target)
	else:
		_set_move_status("move: %s | invalid: %s"
			% [target, MoveFlow.refusal_text(evaluation)])
	return evaluation


## Left press in move mode: converts to a cell and previews it; a press off
## the ground drops the target without leaving the mode (the selection path
## clears the same way).
func handle_move_press(world_point: Vector2) -> Dictionary:
	if not _move_active:
		return _move_reject("move_not_active", "the move is not armed")
	if not world_point.is_finite():
		return _move_reject("non_finite_press", "the press is not finite")
	var grid: Dictionary = Iso.screen_to_grid(world_point)
	if not bool(grid.get("ok", false)):
		_move_cell = Vector2i.ZERO
		_move_evaluation = {}
		var overlay: Variant = _placement_preview()
		if overlay != null:
			overlay.clear()
		_set_move_status("no target")
		return {"ok": true, "error": "", "cleared": true}
	return preview_move_cell(grid["cell"])


## Sends exactly one move intent (spec "confirms exactly one intent") and
## applies only the authoritative response. Nothing is sent unless the mode,
## a selected placement, a valid target, an active session, and a registered
## API are all committed: an invalid target, a missing session, or a missing
## API rejects locally with the explicit error and NO request (design D5 —
## these are the gameplay rules the client owns). A structured or transport
## failure surfaces its code with nothing moved. Awaits the GameApi call.
func confirm_move() -> Dictionary:
	if not _move_active:
		return _move_reject("move_not_active", "the move is not armed")
	if _move_placement == null:
		return _move_reject("move_no_selection", "no building is selected")
	if _move_evaluation.is_empty():
		return _move_reject("move_no_target",
			"no preview target is committed")
	if not bool(_move_evaluation.get("valid", false)):
		return _move_reject("invalid_target",
			MoveFlow.refusal_text(_move_evaluation))
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _move_reject("session_unavailable",
			"no active save to move in")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _move_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	# The intent carries the legacy index and the target cell and nothing
	# else — no price, no orientation, no resource delta (design D3).
	var response: Variant = await api.move_building(session.user_id(),
		int(_move_placement.slot), _move_cell.x, _move_cell.y)
	if not (response is BootData.PlacementResult):
		return _move_reject("bad_response",
			"GameApi returned no typed placement result")
	var typed: BootData.PlacementResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit
		# error names the code and message, nothing was applied.
		move_error = "[town] move failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_move_status(move_error)
		return {"ok": false, "error": move_error, "code": typed.error_code}
	var applied: Dictionary = _apply_move(typed)
	if not bool(applied.get("ok", false)):
		return _move_reject("apply_failed", str(applied.get("error", "")))
	move_error = ""
	_move_evaluation = {}
	_move_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	_set_move_status("moved %s to (%d, %d)" % [_move_label(_move_placement),
		typed.placement.x, typed.placement.y])
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (design D4/D7): the SAME rendered
## object is repositioned to the response's cell and re-sorted with the
## existing depth comparator, the typed row is replaced by the response's
## persisted eight-field entry, and the stored resources and XP take the
## response's values (never a computed delta) with the HUD re-attached. The
## placement count never changes: a move rewrites one row in place. Pre-
## checks run before any mutation; the only post-mutation failure — a
## rejected HUD re-attach — rolls EVERY write back (cell, row, resources,
## XP, and the object's draw order), so a failed apply changes nothing.
func _apply_move(result: BootData.PlacementResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	if _move_placement == null \
			or not (_move_placement is TownState.Placement):
		return {"ok": false, "error": "no typed placement is being moved"}
	var entry: BootData.Placement = result.placement
	var resources: BootData.Resources = result.resources
	if entry == null or resources == null:
		return {"ok": false, "error": "the move response is incomplete"}
	var placement: TownState.Placement = _move_placement
	if not (placement in state.placements):
		return {"ok": false,
			"error": "the moving placement is not part of the town state"}
	# The object to reposition: the rendered node of THIS placement, found by
	# identity so the very object the player selected is the one moved.
	var object: Variant = null
	for candidate: Variant in objects:
		if candidate != null and candidate.placement == placement:
			object = candidate
			break
	if object == null:
		return {"ok": false,
			"error": "the moving placement has no rendered object"}
	var previous := {
		"cell": placement.cell,
		"raw": placement.raw.duplicate(),
		"timestamp": placement.timestamp,
		"orientation": placement.orientation,
		"store": placement.store,
		"attr": placement.attr,
		"player": placement.player,
		"object_cell": object.cell,
		"order": (objects as Array).duplicate(),
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	# The response's persisted entry replaces the typed row verbatim; the
	# legacy key, save order, and resolved content are the placement's own —
	# a move rewrites coordinates, never identity.
	placement.item = entry.item_id
	placement.cell = Vector2i(entry.x, entry.y)
	placement.timestamp = entry.timestamp
	placement.orientation = entry.orientation
	placement.store = entry.store
	placement.attr = entry.attr
	placement.player = entry.player
	placement.raw = [entry.item_id, entry.x, entry.y, entry.timestamp,
		entry.orientation, entry.store, entry.attr, entry.player]
	# The same object repositions: its rendered node moves to the response's
	# footprint rect and it is re-sorted into the committed draw order with
	# the existing depth comparator (design D8's rollback structure, applied
	# to a move).
	object.cell = placement.cell
	object.position = Iso.footprint_rect(placement.cell,
		object.footprint.x, object.footprint.y).position
	_resort_objects()
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back: a failed apply changes nothing.
		placement.cell = previous["cell"]
		placement.raw = previous["raw"]
		placement.timestamp = previous["timestamp"]
		placement.orientation = previous["orientation"]
		placement.store = previous["store"]
		placement.attr = previous["attr"]
		placement.player = previous["player"]
		object.cell = previous["object_cell"]
		object.position = Iso.footprint_rect(object.cell, object.footprint.x,
			object.footprint.y).position
		objects = previous["order"]
		_sync_object_order()
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The response supplies values the payload may have lacked.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	return {"ok": true, "error": ""}


## Closes the armed move without sending anything: mode-local selection,
## target, and overlay drop, the slot hides, and the town state, the
## committed selection, and the resources stay byte-identical.
func cancel_move() -> Dictionary:
	if not _move_active:
		return _move_reject("move_not_active", "the move is not armed")
	_move_active = false
	_move_placement = null
	_move_evaluation = {}
	_move_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, false)
	_set_move_status("move closed")
	return {"ok": true, "error": "", "cancelled": true}


## Builds the move panel into its OWN UI-foundation slot (registered once,
## contents replaced per arm — the picker/shop/HUD attach precedent). The
## panel is hidden while building; `arm_move` shows it once committed.
## Fail-closed envelope: a rejected registration or missing slot root
## returns {ok:false} and commits no visible panel.
func _build_move_panel(armed: bool) -> Dictionary:
	if ui == null:
		return {"ok": false, "error": "the UI foundation is unavailable"}
	if not ui.has_slot(SLOT_MOVE):
		var registration: Dictionary = ui.register_slot(SLOT_MOVE)
		if not bool(registration.get("ok", false)):
			return {"ok": false,
				"error": str(registration.get("error", "rejected"))}
	if ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, false)
	var root: Control = ui.slot_root(SLOT_MOVE)
	if root == null:
		return {"ok": false, "error": "the move slot root is unavailable"}
	for child in root.get_children():
		root.remove_child(child)
		child.free()
	_move_status = null
	var panel := VBoxContainer.new()
	panel.name = "move"
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -MOVE_PANEL_WIDTH
	panel.offset_right = -8.0
	panel.offset_top = 8.0
	panel.offset_bottom = -8.0
	panel.add_theme_constant_override("separation", 2)
	root.add_child(panel)
	var title := Label.new()
	title.name = "title"
	title.text = "Move"
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(title)
	panel.add_child(title)
	var selection := Label.new()
	selection.name = "selection"
	selection.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	selection.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(selection)
	panel.add_child(selection)
	# The move requires NO purchase (spec "Moving SHALL NOT require or
	# perform a purchase"), so the panel states the derived neutral price
	# rather than showing one. `_refresh_move_panel` rewrites this line from
	# the live selection; the initial text names the armed placement when
	# there is one, and the selection instruction otherwise. A sale states
	# the same boundary on its side: the derived price vector is neutral, so
	# NO refund is claimed (building-sell design D2). A store states it too:
	# the derived vector is neutral and the committed configuration records
	# no storing price, so NO cost and NO capacity rule are claimed
	# (building-store design D2/D9).
	if _store_active:
		selection.text = "storing: %s | cost: none claimed, capacity: none " \
			% _move_label(_store_placement) + "claimed (derived, never observed)"
	elif _sell_active:
		selection.text = "selling: %s | refund: none claimed (derived, " \
			% _move_label(_sell_placement) + "never observed)"
	elif not armed:
		selection.text = "select a placed building to move it"
	else:
		selection.text = "moving: %s | price: free (derived, never observed)" \
			% _move_label(_move_placement)
	var status := Label.new()
	status.name = "status"
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(status)
	panel.add_child(status)
	_move_status = status
	var row := HBoxContainer.new()
	row.name = "actions"
	# The selection-path arm actions (design D8, extended by building-store
	# design D7): a `Move`, a `Sell`, and a `Put in storage` button the
	# player presses after selecting a placed building. All three belong to
	# this one selection-driven surface, and exactly one of them can be
	# armed at a time.
	var arm := Button.new()
	arm.name = "move"
	arm.text = "Move"
	arm.pressed.connect(_on_move_action)
	row.add_child(arm)
	var sell := Button.new()
	sell.name = "sell"
	sell.text = "Sell"
	sell.pressed.connect(_on_sell_action)
	row.add_child(sell)
	var store := Button.new()
	store.name = "store"
	store.text = "Put in storage"
	store.pressed.connect(_on_store_action)
	row.add_child(store)
	# The confirm exists only while armed: unarmed, the surface offers the
	# arm actions alone, so no confirm can be pressed before a target (or,
	# for a sale or a store, before a building is armed). It serves ALL THREE
	# modes and dispatches to whichever one is armed (design D7).
	var confirm := Button.new()
	confirm.name = "confirm"
	confirm.text = "Sell" if _sell_active \
		else ("Put in storage" if _store_active else "Move here")
	confirm.pressed.connect(_on_surface_confirm)
	row.add_child(confirm)
	if not armed and not _sell_active and not _store_active:
		confirm.visible = false
	var cancel := Button.new()
	cancel.name = "cancel"
	cancel.text = "Cancel"
	cancel.pressed.connect(_on_surface_cancel)
	row.add_child(cancel)
	panel.add_child(row)
	return {"ok": true, "error": ""}


## Writes the move panel's status line (no-op before a panel exists).
func _set_move_status(text: String) -> void:
	if _move_status != null and is_instance_valid(_move_status):
		(_move_status as Label).text = text


## The moving placement's display label: the resolved content name when one
## exists, the raw legacy id otherwise (never a guessed name).
func _move_label(placement: Variant) -> String:
	if placement == null or not (placement is TownState.Placement):
		return "the selected building"
	var typed: TownState.Placement = placement
	if typed.name != "":
		return "%s (item %d)" % [typed.name, int(typed.item)]
	return "item %d" % int(typed.item)


## The house move failure envelope: records the explicit error naming the
## code and condition, shows it in the move status when armed, and returns
## {ok:false} without touching town state, selection, resources, or the
## committed draw order.
func _move_reject(code: String, message: String) -> Dictionary:
	move_error = "[town] move rejected: %s: %s" % [code, message]
	_set_move_status(move_error)
	return {"ok": false, "error": move_error, "code": code}


## Re-sorts the committed draw order with the existing depth comparator
## (depth, then grid y, then grid x, then save order) and syncs the
## objects layer's child order to it, so the rendered z-order stays exactly
## what a full rebuild would produce after the move.
func _resort_objects() -> void:
	objects.sort_custom(_object_depth_less)
	_sync_object_order()


## The objects layer's children follow the committed `objects` order.
func _sync_object_order() -> void:
	for index in range(objects.size()):
		objects_layer.move_child(objects[index], index)


## Depth comparator over rendered objects (the town build's `_depth_less`
## applied to each object's placement, so one rule orders both the build
## and the move).
func _object_depth_less(a: Variant, b: Variant) -> bool:
	return _depth_less(a.placement, b.placement)


## The shared confirm row (design D8, extended by building-store design D7):
## one button serves all three modes of this selection-driven surface, so its
## press dispatches to whichever mode is armed. With no mode armed the button
## is hidden, so a bare press can never reach an intent.
func _on_surface_confirm() -> void:
	if _store_active:
		await confirm_store()
		return
	if _sell_active:
		await confirm_sell()
		return
	await confirm_move()


## The shared cancel row (design D8, extended by building-store design D7):
## the same dispatch, no request either way.
func _on_surface_cancel() -> void:
	if _store_active:
		cancel_store()
		return
	if _sell_active:
		cancel_sell()
		return
	cancel_move()


## The selection-path `Move` action (design D8): selecting an addressable
## placed building offers this action, and pressing it arms the move. It is
## a pure wiring step over `arm_move` — no state, no request of its own —
## so the delivered selection behavior is unchanged: the press that
## selected the building is the delivered one, and this action only arms.
func _on_move_action() -> void:
	arm_move()


# ---------------------------------------------------------------------------
# Sell flow (building-sell, spec "Sell flow")
# ---------------------------------------------------------------------------


## True while the sale is armed.
func sell_active() -> bool:
	return _sell_active


## The placement the armed sale targets (TownState.Placement or null).
func sell_placement() -> Variant:
	return _sell_placement


## The addressable index the armed sale names (-1 when unaddressable or
## unarmed) — the item index a sell intent carries.
func sell_slot() -> int:
	if _sell_placement == null:
		return TownState.NO_SLOT
	return int(_sell_placement.slot)


## True when the current selection is a placed building a sell intent can
## name. The addressability rule is the move flow's own, read from the same
## one predicate — a legacy key that is not a positive integer is refused by
## name, never coerced (design D7 carried forward).
func sell_selection_available() -> bool:
	if selected == null or not (selected is TownObject):
		return false
	var object: TownObject = selected
	return TownState.is_addressable(object.placement)


## Arms the sale on the current selection (spec "the player selects a placed
## building, chooses the sell action, and confirms"). Fail-closed: an
## unbuilt view, no selection, a selection that is not a placement, an
## unaddressable legacy key, an already-armed sale, an armed move, or a
## missing panel each reject with an explicit error naming the condition. It
## adds no state and no request of its own: nothing leaves the client until
## a confirm, and a sale has no grid target, so no preview is shown.
func arm_sell() -> Dictionary:
	if view_state != STATE_BUILT:
		return _sell_reject("town_not_built", "the town view is not built")
	if _sell_active:
		return _sell_reject("sell_already_active", "the sale is already armed")
	if _move_active:
		return _sell_reject("move_already_active",
			"a move is armed; cancel it before selling")
	if _store_active:
		# The three modes of this one surface never stack (building-store
		# design D7), so a store in progress refuses the sale by name.
		return _sell_reject("store_already_active",
			"a store is armed; cancel it before selling")
	if selected == null:
		return _sell_reject("sell_no_selection",
			"no placed building is selected")
	if not (selected is TownObject):
		return _sell_reject("sell_no_selection",
			"the selection is not a placed building")
	var object: TownObject = selected
	var placement: Variant = object.placement
	if not (placement is TownState.Placement):
		return _sell_reject("sell_no_selection",
			"the selected object carries no typed placement")
	if not TownState.is_addressable(placement):
		# The move flow's own explicit reason (spec "A placement with no
		# addressable legacy key SHALL be refused with the same explicit
		# reason the move flow already uses"). The index is never coerced,
		# because a coerced index would name a different row.
		return _sell_reject(MoveFlow.REASON_UNADDRESSABLE,
			"the selected placement's save key '%s' is not a positive integer"
			% str(placement.slot_key))
	_sell_active = true
	_sell_placement = placement
	sell_error = ""
	var panel := _build_move_panel(true)
	if not bool(panel.get("ok", false)):
		return _sell_reject("sell_panel", str(panel.get("error", "")))
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and not ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, true)
	_refresh_move_panel()
	return {"ok": true, "error": "", "slot": int(placement.slot),
		"item": int(placement.item)}


## Sends exactly one sell intent (spec "a confirm that sends exactly one
## intent") and applies only the authoritative response. Nothing is sent
## unless the sale is armed, the armed building is still the committed
## selection and addressable, an active session exists, and the API is
## registered: each missing condition rejects locally with the explicit
## error and NO request. A structured or transport failure surfaces its
## code with the building still on the map and no resource changed. Awaits
## the GameApi call.
##
## The intent carries the legacy index and nothing else — no price, no
## refund, no reason, no resource delta (design D3).
func confirm_sell() -> Dictionary:
	if not _sell_active:
		return _sell_reject("sell_not_active", "the sale is not armed")
	if _sell_placement == null \
			or not (_sell_placement is TownState.Placement):
		return _sell_reject("sell_no_selection", "no building is being sold")
	if not TownState.is_addressable(_sell_placement):
		return _sell_reject(MoveFlow.REASON_UNADDRESSABLE,
			"the armed placement's save key '%s' is not a positive integer"
			% str(_sell_placement.slot_key))
	if selected == null or not (selected is TownObject) \
			or (selected as TownObject).placement != _sell_placement:
		# A press while the sale is armed can move the selection (a sale has
		# no grid target, so it does not own the press the way an armed move
		# does). Selling something other than the committed selection is
		# refused by name rather than guessed.
		return _sell_reject("sell_selection_changed",
			"the selection no longer names the armed building; "
			+ "cancel and press Sell again")
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _sell_reject("session_unavailable",
			"no active save to sell from")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _sell_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	var response: Variant = await api.sell_building(session.user_id(),
		int(_sell_placement.slot))
	if not (response is BootData.SellResult):
		return _sell_reject("bad_response",
			"GameApi returned no typed sell result")
	var typed: BootData.SellResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit
		# error names the code and message, nothing was applied.
		sell_error = "[town] sell failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_move_status(sell_error)
		return {"ok": false, "error": sell_error, "code": typed.error_code}
	# The label is read BEFORE the apply, which releases the armed placement.
	var label := _move_label(_sell_placement)
	var applied: Dictionary = _apply_sell(typed)
	if not bool(applied.get("ok", false)):
		return _sell_reject("apply_failed", str(applied.get("error", "")))
	sell_error = ""
	_sell_active = false
	_sell_placement = null
	_set_move_status("sold %s | refund: none claimed" % label)
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (building-sell design D9): the typed
## placement leaves the state and its rendered object is freed, the
## REMAINING objects keep the committed depth order a removal preserves
## (nothing is re-sorted, because removing one element from a sorted list
## leaves it sorted), and the stored resources and XP take the response's
## values (never a computed delta) with the HUD re-attached.
##
## Everything the apply touches is snapshotted FIRST — the placement's index
## in the state (which restores the placement itself, never mutated), the
## object's index in the draw order, the object itself, the committed
## selection, the resource bag and XP, and the missing-field list — so the
## only post-mutation failure (a rejected HUD re-attach) restores every one of
## them from the snapshot, including re-attaching the object that was
## detached but NOT yet freed. A failed apply therefore leaves the building
## on the map exactly as before.
func _apply_sell(result: BootData.SellResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	if _sell_placement == null \
			or not (_sell_placement is TownState.Placement):
		return {"ok": false, "error": "no typed placement is being sold"}
	var removed: BootData.Placement = result.removed
	var resources: BootData.Resources = result.resources
	if removed == null or resources == null:
		return {"ok": false, "error": "the sell response is incomplete"}
	var placement: TownState.Placement = _sell_placement
	var placement_index: int = state.placements.find(placement)
	if placement_index < 0:
		return {"ok": false,
			"error": "the sold placement is not part of the town state"}
	# The object to remove: the rendered node of THIS placement, found by
	# identity so the very object the player selected is the one freed.
	var object: Variant = null
	var object_index := -1
	for i in range(objects.size()):
		var candidate: Variant = objects[i]
		if candidate != null and candidate.placement == placement:
			object = candidate
			object_index = i
			break
	if object == null:
		return {"ok": false,
			"error": "the sold placement has no rendered object"}
	var previous := {
		"placement_index": placement_index,
		"object_index": object_index,
		"selected": selected,
		"missing": (state.missing as Array).duplicate(),
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	# The response supplies values the payload may have lacked, so those keys
	# are no longer missing; the snapshot restores them verbatim on rollback.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	state.placements.remove_at(placement_index)
	objects.remove_at(object_index)
	objects_layer.remove_child(object)
	if selected == object:
		selected = null
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back from the snapshot alone: a failed apply
		# changes nothing, and the building is back on the map at its own
		# index with its own object re-attached.
		state.placements.insert(int(previous["placement_index"]), placement)
		state.missing = previous["missing"]
		objects.insert(int(previous["object_index"]), object)
		objects_layer.add_child(object)
		objects_layer.move_child(object, int(previous["object_index"]))
		selected = previous["selected"]
		if selected != null and is_instance_valid(selected as Node):
			(selected as TownObject).set_selected(true)
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The removal is committed: the object is detached and nothing else can
	# fail, so it is freed now (never before the last fallible step, so a
	# rollback could re-attach it).
	object.free()
	return {"ok": true, "error": ""}


## Closes the armed sale without sending anything: the mode-local placement
## drops, the slot hides, and the town state, the committed selection, and
## the resources stay byte-identical.
func cancel_sell() -> Dictionary:
	if not _sell_active:
		return _sell_reject("sell_not_active", "the sale is not armed")
	_sell_active = false
	_sell_placement = null
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, false)
	_set_move_status("sale closed")
	return {"ok": true, "error": "", "cancelled": true}


## The house sell failure envelope: records the explicit error naming the
## code and condition, shows it in the surface's status line, and returns
## {ok:false} without touching town state, selection, resources, or the
## committed draw order.
func _sell_reject(code: String, message: String) -> Dictionary:
	sell_error = "[town] sell rejected: %s: %s" % [code, message]
	_set_move_status(sell_error)
	return {"ok": false, "error": sell_error, "code": code}


## The selection-path `Sell` action (design D8): selecting an addressable
## placed building offers this action beside `Move`, and pressing it arms
## the sale. It is a pure wiring step over `arm_sell` — no state, no request
## of its own — so the delivered selection behavior is unchanged.
func _on_sell_action() -> void:
	arm_sell()


# ---------------------------------------------------------------------------
# Store flow (building-store, spec "Store flow")
# ---------------------------------------------------------------------------


## True while the store is armed.
func store_active() -> bool:
	return _store_active


## The placement the armed store targets (TownState.Placement or null).
func store_placement() -> Variant:
	return _store_placement


## The addressable index the armed store names (-1 when unaddressable or
## unarmed) — the item index a store intent carries.
func store_slot() -> int:
	if _store_placement == null:
		return TownState.NO_SLOT
	return int(_store_placement.slot)


## True when the current selection is a placed building a store intent can
## name. The addressability rule is the move flow's own, read from the same
## one predicate — a legacy key that is not a positive integer is refused by
## name, never coerced (design D7 carried forward from building-move).
func store_selection_available() -> bool:
	if selected == null or not (selected is TownObject):
		return false
	var object: TownObject = selected
	return TownState.is_addressable(object.placement)


## Arms the store on the current selection (spec "the player selects a
## placed building, chooses the store action, and confirms"). Fail-closed: an
## unbuilt view, no selection, a selection that is not a placement, an
## unaddressable legacy key, an already-armed store, an armed move, an armed
## sale, or a missing panel each reject with an explicit error naming the
## condition. It adds no state and no request of its own: nothing leaves the
## client until a confirm, and a store has no grid target, so no preview is
## shown (design D7).
func arm_store() -> Dictionary:
	if view_state != STATE_BUILT:
		return _store_reject("town_not_built", "the town view is not built")
	if _store_active:
		return _store_reject("store_already_active",
			"the store is already armed")
	if _move_active:
		return _store_reject("move_already_active",
			"a move is armed; cancel it before storing")
	if _sell_active:
		return _store_reject("sell_already_active",
			"a sale is armed; cancel it before storing")
	if selected == null:
		return _store_reject("store_no_selection",
			"no placed building is selected")
	if not (selected is TownObject):
		return _store_reject("store_no_selection",
			"the selection is not a placed building")
	var object: TownObject = selected
	var placement: Variant = object.placement
	if not (placement is TownState.Placement):
		return _store_reject("store_no_selection",
			"the selected object carries no typed placement")
	if not TownState.is_addressable(placement):
		# The move flow's own explicit reason, which the sell flow already
		# reuses (spec: "A placement with no addressable legacy key SHALL be
		# refused with the same explicit reason the move flow already uses").
		# The index is never coerced, because a coerced index would name a
		# different row.
		return _store_reject(MoveFlow.REASON_UNADDRESSABLE,
			"the selected placement's save key '%s' is not a positive integer"
			% str(placement.slot_key))
	_store_active = true
	_store_placement = placement
	store_error = ""
	var panel := _build_move_panel(true)
	if not bool(panel.get("ok", false)):
		return _store_reject("store_panel", str(panel.get("error", "")))
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and not ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, true)
	_refresh_move_panel()
	return {"ok": true, "error": "", "slot": int(placement.slot),
		"item": int(placement.item)}


## Sends exactly one store intent (spec "a confirm that sends exactly one
## intent") and applies only the authoritative response. Nothing is sent
## unless the store is armed, the armed building is still the committed
## selection and addressable, an active session exists, and the API is
## registered: each missing condition rejects locally with the explicit error
## and NO request. A structured or transport failure surfaces its code with
## the building still on the map, the storage unchanged, and no resource
## changed. Awaits the GameApi call.
##
## The intent carries the legacy index and nothing else — no price, no
## quantity, no capacity, no resource delta (design D3).
func confirm_store() -> Dictionary:
	if not _store_active:
		return _store_reject("store_not_active", "the store is not armed")
	if _store_placement == null \
			or not (_store_placement is TownState.Placement):
		return _store_reject("store_no_selection",
			"no building is being stored")
	if not TownState.is_addressable(_store_placement):
		return _store_reject(MoveFlow.REASON_UNADDRESSABLE,
			"the armed placement's save key '%s' is not a positive integer"
			% str(_store_placement.slot_key))
	if selected == null or not (selected is TownObject) \
			or (selected as TownObject).placement != _store_placement:
		# A press while the store is armed can move the selection (a store
		# owns no grid target, so it does not own the press the way an armed
		# move does). Storing something other than the committed selection is
		# refused by name rather than guessed.
		return _store_reject("store_selection_changed",
			"the selection no longer names the armed building; "
			+ "cancel and press Put in storage again")
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _store_reject("session_unavailable",
			"no active save to store from")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _store_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	var response: Variant = await api.store_building(session.user_id(),
		int(_store_placement.slot))
	if not (response is BootData.StoreResult):
		return _store_reject("bad_response",
			"GameApi returned no typed store result")
	var typed: BootData.StoreResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit error
		# names the code and message, nothing was applied.
		store_error = "[town] store failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_move_status(store_error)
		return {"ok": false, "error": store_error, "code": typed.error_code}
	# The label and the landing item are read BEFORE the apply, which
	# releases the armed placement.
	var label := _move_label(_store_placement)
	var quantity := 0
	if typed.removed != null:
		quantity = int(typed.store.get(str(int(typed.removed.item_id)), 0))
	var applied: Dictionary = _apply_store(typed)
	if not bool(applied.get("ok", false)):
		return _store_reject("apply_failed", str(applied.get("error", "")))
	store_error = ""
	_store_active = false
	_store_placement = null
	_set_move_status("stored %s (x%d in storage) | one-way in this change"
		% [label, quantity])
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (building-store design D8): the typed
## placement leaves the state and its rendered object is freed, the REMAINING
## objects keep the committed depth order a removal preserves (nothing is
## re-sorted, because removing one element from a sorted list leaves it
## sorted), the typed storage mapping is replaced through the SAME fail-closed
## `TownState` parser the payload parse and the purchase apply use (never a
## computed delta, never a partial write, never a locally incremented
## quantity), the storage readout re-renders from it, and the stored resources
## and XP take the response's values (never a computed delta) with the HUD
## re-attached.
##
## Everything the apply touches is snapshotted FIRST — the placement's index
## in the state (which restores the placement itself, never mutated), the
## object's index in the draw order, the object itself, the committed
## selection, the storage mapping, the readout's own state, the missing-field
## list, the resource bag, and the XP — so the only post-mutation failure (a
## rejected HUD re-attach) restores every one of them from the snapshot,
## including re-attaching the object that was detached but NOT yet freed. A
## failed apply therefore leaves the building on the map, the storage view,
## the readout, and the HUD exactly as before.
func _apply_store(result: BootData.StoreResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	if _store_placement == null \
			or not (_store_placement is TownState.Placement):
		return {"ok": false, "error": "no typed placement is being stored"}
	var removed: BootData.Placement = result.removed
	var resources: BootData.Resources = result.resources
	if removed == null or resources == null:
		return {"ok": false, "error": "the store response is incomplete"}
	var placement: TownState.Placement = _store_placement
	var placement_index: int = state.placements.find(placement)
	if placement_index < 0:
		return {"ok": false,
			"error": "the stored placement is not part of the town state"}
	# The object to remove: the rendered node of THIS placement, found by
	# identity so the very object the player selected is the one freed.
	var object: Variant = null
	var object_index := -1
	for i in range(objects.size()):
		var candidate: Variant = objects[i]
		if candidate != null and candidate.placement == placement:
			object = candidate
			object_index = i
			break
	if object == null:
		return {"ok": false,
			"error": "the stored placement has no rendered object"}
	# The response's storage is read with the payload's own parser: one rule
	# set, so a response can never be interpreted differently than the save
	# it replaces. A rejected mapping fails BEFORE any mutation.
	var storage: Dictionary = TownState.storage_of(result.store)
	if not bool(storage.get("ok", false)):
		return {"ok": false, "error": str(storage.get("error", ""))}
	var previous := {
		"placement_index": placement_index,
		"object_index": object_index,
		"selected": selected,
		"storage": (state.storage as Dictionary).duplicate(),
		"missing": (state.missing as Array).duplicate(),
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	# The response supplies values the payload may have lacked, so those keys
	# are no longer missing; the snapshot restores them verbatim on rollback.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	state.missing.erase(TownState.STORAGE_MISSING_KEY)
	state.placements.remove_at(placement_index)
	objects.remove_at(object_index)
	objects_layer.remove_child(object)
	if selected == object:
		selected = null
	state.storage = (storage["storage"] as Dictionary).duplicate()
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back from the snapshot alone: a failed apply
		# changes nothing, and the building is back on the map at its own
		# index with its own object re-attached.
		state.placements.insert(int(previous["placement_index"]), placement)
		objects.insert(int(previous["object_index"]), object)
		objects_layer.add_child(object)
		objects_layer.move_child(object, int(previous["object_index"]))
		selected = previous["selected"]
		if selected != null and is_instance_valid(selected as Node):
			(selected as TownObject).set_selected(true)
		state.storage = previous["storage"]
		state.missing = previous["missing"]
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		_render_storage()
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The removal is committed: the object is detached and nothing else can
	# fail, so it is freed now (never before the last fallible step, so a
	# rollback could re-attach it).
	object.free()
	# The readout is re-rendered from the state's own mapping (the purchase
	# apply's precedent), so the player sees the stored item at once.
	_render_storage()
	return {"ok": true, "error": ""}


## Closes the armed store without sending anything: the mode-local placement
## drops, the slot hides, and the town state, the storage view, the readout,
## the committed selection, and the resources stay byte-identical.
func cancel_store() -> Dictionary:
	if not _store_active:
		return _store_reject("store_not_active", "the store is not armed")
	_store_active = false
	_store_placement = null
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, false)
	_set_move_status("store closed")
	return {"ok": true, "error": "", "cancelled": true}


## The house store failure envelope: records the explicit error naming the
## code and condition, shows it in the surface's status line, and returns
## {ok:false} without touching town state, storage, readout, selection,
## resources, or the committed draw order.
func _store_reject(code: String, message: String) -> Dictionary:
	store_error = "[town] store rejected: %s: %s" % [code, message]
	_set_move_status(store_error)
	return {"ok": false, "error": store_error, "code": code}


## The selection-path `Store` action (building-store design D7): selecting an
## addressable placed building offers this action beside `Move` and `Sell`,
## and pressing it arms the store. It is a pure wiring step over `arm_store` —
## no state, no request of its own — so the delivered selection behavior is
## unchanged.
func _on_store_action() -> void:
	arm_store()


## Shop button wiring: a press selects that entry.
func _on_shop_pick(item_id: int) -> void:
	pick_shop_item(item_id)


## Shop button wiring: confirm sends (awaits the one intent).
func _on_shop_confirm() -> void:
	await confirm_purchase()


## Shop button wiring: cancel closes with no request.
func _on_shop_cancel() -> void:
	cancel_shop()


## Left press -> placement preview while the build picker is open,
## otherwise -> selection. The camera's drag handling is independent
## (design D7/D8: the press selects or previews, motion pans, the press
## is not consumed by either owner).
func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.pressed and button.button_index == MOUSE_BUTTON_LEFT:
			if _placement_active:
				handle_placement_press(get_global_mouse_position())
			elif _move_active:
				# Move mode owns the press exactly as placement mode does
				# (design D8); the picker's routing is untouched.
				handle_move_press(get_global_mouse_position())
			else:
				handle_pointer_press(get_global_mouse_position())


## Clears every committed view fragment (objects, selection, HUD labels,
## error display, and the placement mode) without touching the committed
## state.
func _reset_view() -> void:
	for child in objects_layer.get_children():
		objects_layer.remove_child(child)
		child.free()
	objects = []
	selected = null
	_hud = null
	build_ok = false
	view_state = STATE_EMPTY
	if error_label != null:
		error_label.visible = false
		error_label.text = ""
	# A rebuild drops the placement mode with the rest of the view: no
	# stale picker, target, overlay, or status survives a fresh build. The
	# shop drops with it, in its own right (design D8): the two surfaces
	# never share mode state.
	_placement_active = false
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	_placement_status = null
	var overlay: Variant = get_node_or_null("Placement")
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)
	_shop_active = false
	_shop_entry = null
	_shop_status = null
	_shop_storage = null
	if ui != null and ui.has_slot(SLOT_SHOP) \
			and ui.is_slot_visible(SLOT_SHOP):
		ui.set_slot_visible(SLOT_SHOP, false)
	# The move drops with the rest of the view, in its own right (design
	# D8): a rebuild never leaves a stale armed move, target, overlay, or
	# status behind, and the picker's and the shop's slots are untouched.
	# The armed sale drops with it, in its own right (building-sell design
	# D8): a rebuild never leaves a stale armed sale behind either.
	_move_active = false
	_move_placement = null
	_move_evaluation = {}
	_move_cell = Vector2i.ZERO
	_move_status = null
	_sell_active = false
	_sell_placement = null
	# The armed store drops with the rest of the view, in its own right
	# (building-store design D7): a rebuild never leaves a stale armed store
	# behind either.
	_store_active = false
	_store_placement = null
	if ui != null and ui.has_slot(SLOT_MOVE) \
			and ui.is_slot_visible(SLOT_MOVE):
		ui.set_slot_visible(SLOT_MOVE, false)


## Enters the explicit error state: names the failure on the view, keeps
## the view cleared of partial renders, and returns the failed envelope.
## The failure is printed as an explicit stdout marker rather than an
## engine error line: expected fail-closed rejections follow the boot
## scene's `state=error` marker convention, while the verification
## harnesses treat engine `ERROR:` lines as fatal.
func _enter_error(message: String) -> Dictionary:
	_reset_view()
	view_state = STATE_ERROR
	build_error = message
	build_ok = false
	print("[town] state=error message=", message)
	if error_label != null:
		error_label.text = message
		error_label.visible = true
	return {"ok": false, "error": message}


## Camera framing focus: the mean of the footprint rect centers — a
## deterministic point of the committed state (recorded as the capture
## position), clamped defensively into the world bounds.
func _focus_position() -> Vector2:
	var rect := Iso.world_rect()
	if objects.is_empty():
		return rect.get_center()
	var sum := Vector2.ZERO
	for object in objects:
		var footprint: Rect2 = object.footprint_rect()
		sum += footprint.position + footprint.size * 0.5
	return (sum / float(objects.size())).clamp(
		rect.position, rect.position + rect.size)


## Selection commit: exactly zero or one highlighted object.
func _commit_selection(object: Variant) -> void:
	if selected != null and selected != object:
		selected.set_selected(false)
	selected = object
	if object != null:
		object.set_selected(true)
	# Design D8: the selection is what arms this surface, so a committed
	# selection refreshes its `Move`, `Sell`, and `Store` actions. It is
	# presentational only — the selection itself, its highlight, and the
	# picker's routing are exactly as delivered, and arming still requires a
	# separate press. An armed mode is never refreshed: it already names the
	# placement it will act on, and `confirm_sell` / `confirm_store` refuse a
	# changed selection by name instead of silently re-targeting.
	if not _move_active and not _sell_active and not _store_active \
			and view_state == STATE_BUILT:
		refresh_move_action()


## Isometric depth order with the documented deterministic tie-break:
## depth, then grid y, then grid x, then save order.
static func _depth_less(a: Variant, b: Variant) -> bool:
	var depth_a := Iso.depth_key(a.cell)
	var depth_b := Iso.depth_key(b.cell)
	if depth_a != depth_b:
		return depth_a < depth_b
	if a.cell.y != b.cell.y:
		return a.cell.y < b.cell.y
	if a.cell.x != b.cell.x:
		return a.cell.x < b.cell.x
	return int(a.order) < int(b.order)


## Starts the windowed capture exactly once, only after a built view
## (a failed build shows its error instead of capturing evidence).
func _maybe_start_capture() -> void:
	if _capture_path.is_empty() or _capture_started:
		return
	if DisplayServer.get_name() == "headless":
		return
	if not build_ok:
		return
	_capture_started = true
	if _store_capture:
		_capture_store_and_quit()
		return
	if _move_capture:
		_capture_move_and_quit()
		return
	if _sell_capture:
		_capture_sell_and_quit()
		return
	if _purchase_capture:
		_capture_purchase_and_quit()
		return
	if _placement_capture:
		_capture_placement_and_quit()
		return
	_capture_and_quit()


## Design D9 step: first rendered frame -> resize to the authentic stage
## -> frame the camera on the recorded focus -> capture -> write -> quit.
func _capture_and_quit() -> void:
	await RenderingServer.frame_post_draw
	get_window().size = CAPTURE_SIZE
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null:
		push_error("[town] capture failed: viewport image unavailable")
		get_tree().quit(1)
		return
	if image.get_size() != CAPTURE_SIZE:
		push_error("[town] capture failed: expected %sx%s, got %sx%s" % [
			CAPTURE_SIZE.x, CAPTURE_SIZE.y,
			image.get_size().x, image.get_size().y])
		get_tree().quit(1)
		return
	var directory := _capture_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var save_error := image.save_png(_capture_path)
	if save_error != OK:
		push_error("[town] capture failed: save error %s" % save_error)
		get_tree().quit(1)
		return
	print("[town] capture written: %s (%sx%s)" % [
		_capture_path, image.get_size().x, image.get_size().y])
	get_tree().quit(0)


## Placement capture (design D11): drives exactly one confirmed intent
## through the same picker flow a player uses — enter, pick, preview,
## confirm — and then captures the town containing the placed building.
## Any failed step prints an explicit marker and exits 1 instead of
## capturing a town that never received the building.
func _capture_placement_and_quit() -> void:
	var entered: Dictionary = enter_placement()
	if not bool(entered.get("ok", false)):
		_placement_capture_fail("enter", str(entered.get("error", "")))
		return
	var picked: Dictionary = pick_placement(PLACEMENT_INTENT_ITEM)
	if not bool(picked.get("ok", false)):
		_placement_capture_fail("pick", str(picked.get("error", "")))
		return
	var preview: Dictionary = preview_placement_cell(PLACEMENT_INTENT_CELL)
	if not bool(preview.get("valid", false)):
		_placement_capture_fail("preview", str(preview.get("reason", "")))
		return
	var confirmed: Dictionary = await confirm_placement()
	if not bool(confirmed.get("ok", false)):
		_placement_capture_fail("confirm", str(confirmed.get("error", "")))
		return
	print("[town] placement-capture applied item=%d cell=(%d, %d) objects=%d" % [
		PLACEMENT_INTENT_ITEM, PLACEMENT_INTENT_CELL.x,
		PLACEMENT_INTENT_CELL.y, objects.size()])
	_capture_and_quit()


## A named placement-capture failure: explicit marker + exit 1, so a
## failed flow never leaves an open window or a misleading frame.
func _placement_capture_fail(step: String, detail: String) -> void:
	print("[town] placement-capture state=error step=%s detail=%s" % [
		step, detail])
	get_tree().quit(1)


## Purchase capture (design D9): drives exactly one confirmed intent
## through the same shop flow a player uses — enter, pick, confirm — and
## then captures the town whose storage readout carries the purchased item.
## Any failed step prints an explicit marker and exits 1 instead of
## capturing a town that never received the item.
func _capture_purchase_and_quit() -> void:
	var entered: Dictionary = enter_shop()
	if not bool(entered.get("ok", false)):
		_purchase_capture_fail("enter", str(entered.get("error", "")))
		return
	var picked: Dictionary = pick_shop_item(PURCHASE_INTENT_ITEM)
	if not bool(picked.get("ok", false)):
		_purchase_capture_fail("pick", str(picked.get("error", "")))
		return
	var confirmed: Dictionary = await confirm_purchase()
	if not bool(confirmed.get("ok", false)):
		_purchase_capture_fail("confirm", str(confirmed.get("error", "")))
		return
	print("[town] purchase-capture applied item=%d storage=%s" % [
		PURCHASE_INTENT_ITEM, JSON.stringify(_storage_record())])
	_capture_and_quit()


## A named purchase-capture failure: explicit marker + exit 1, so a failed
## flow never leaves an open window or a misleading frame.
func _purchase_capture_fail(step: String, detail: String) -> void:
	print("[town] purchase-capture state=error step=%s detail=%s" % [
		step, detail])
	get_tree().quit(1)


## Move capture (building-move, design D9): drives exactly one confirmed
## intent through the same flow a player uses — select the recorded
## building, arm the move, preview the recorded target, confirm — and then
## captures the town containing the building at its new cell. Any failed
## step prints an explicit marker and exits 1 instead of capturing a town
## that never received the move.
func _capture_move_and_quit() -> void:
	var object: Variant = _object_for_cell(MOVE_INTENT_FROM)
	if object == null:
		_move_capture_fail("select",
			"no rendered object at the recorded cell (%d, %d)"
			% [MOVE_INTENT_FROM.x, MOVE_INTENT_FROM.y])
		return
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(object.cell))
	if not bool(pressed.get("ok", false)):
		_move_capture_fail("select", str(pressed.get("error", "")))
		return
	if selection() != object:
		_move_capture_fail("select",
			"the press at (%d, %d) did not select the recorded building"
			% [MOVE_INTENT_FROM.x, MOVE_INTENT_FROM.y])
		return
	var armed: Dictionary = arm_move()
	if not bool(armed.get("ok", false)):
		_move_capture_fail("arm", str(armed.get("error", "")))
		return
	var preview: Dictionary = preview_move_cell(MOVE_INTENT_TO)
	if not bool(preview.get("valid", false)):
		_move_capture_fail("preview", str(preview.get("reason", "")))
		return
	var confirmed: Dictionary = await confirm_move()
	if not bool(confirmed.get("ok", false)):
		_move_capture_fail("confirm", str(confirmed.get("error", "")))
		return
	print("[town] move-capture applied item_index=%d cell=(%d, %d) objects=%d" % [
		int(armed.get("slot", -1)), MOVE_INTENT_TO.x, MOVE_INTENT_TO.y,
		objects.size()])
	_capture_and_quit()


## A named move-capture failure: explicit marker + exit 1, so a failed flow
## never leaves an open window or a misleading frame.
func _move_capture_fail(step: String, detail: String) -> void:
	print("[town] move-capture state=error step=%s detail=%s" % [
		step, detail])
	get_tree().quit(1)


## Sell capture (building-sell, design D10): drives exactly one confirmed
## intent through the same flow a player uses — select the recorded building,
## arm the sale, confirm — and then captures the town WITHOUT the sold
## building. Any failed step prints an explicit marker and exits 1 instead
## of capturing a town that still carries it.
func _capture_sell_and_quit() -> void:
	var object: Variant = _object_for_cell(SELL_INTENT_CELL)
	if object == null:
		_sell_capture_fail("select",
			"no rendered object at the recorded cell (%d, %d)"
			% [SELL_INTENT_CELL.x, SELL_INTENT_CELL.y])
		return
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(object.cell))
	if not bool(pressed.get("ok", false)):
		_sell_capture_fail("select", str(pressed.get("error", "")))
		return
	if selection() != object:
		_sell_capture_fail("select",
			"the press at (%d, %d) did not select the recorded building"
			% [SELL_INTENT_CELL.x, SELL_INTENT_CELL.y])
		return
	var armed: Dictionary = arm_sell()
	if not bool(armed.get("ok", false)):
		_sell_capture_fail("arm", str(armed.get("error", "")))
		return
	var confirmed: Dictionary = await confirm_sell()
	if not bool(confirmed.get("ok", false)):
		_sell_capture_fail("confirm", str(confirmed.get("error", "")))
		return
	print("[town] sell-capture applied item_index=%d cell=(%d, %d) objects=%d" % [
		int(armed.get("slot", -1)), SELL_INTENT_CELL.x, SELL_INTENT_CELL.y,
		objects.size()])
	_capture_and_quit()


## A named sell-capture failure: explicit marker + exit 1, so a failed flow
## never leaves an open window or a misleading frame.
func _sell_capture_fail(step: String, detail: String) -> void:
	print("[town] sell-capture state=error step=%s detail=%s" % [
		step, detail])
	get_tree().quit(1)


## Store capture (building-store, design D9): drives exactly one confirmed
## intent through the same flow a player uses — select the recorded
## building, arm the store, confirm — and then captures the town WITHOUT the
## stored building, with its storage readout carrying the stored item. Any
## failed step prints an explicit marker and exits 1 instead of capturing a
## town that still shows the building on the map.
func _capture_store_and_quit() -> void:
	# The shop is opened first so its storage READOUT is on screen: a store
	# re-renders that readout from the response's mapping, and the frame must
	# show the stored item in the player's storage (the purchase capture's
	# own reason for opening the shop, reused here).
	var entered_shop: Dictionary = enter_shop()
	if not bool(entered_shop.get("ok", false)):
		_store_capture_fail("shop", str(entered_shop.get("error", "")))
		return
	var object: Variant = _object_for_cell(STORE_INTENT_CELL)
	if object == null:
		_store_capture_fail("select",
			"no rendered object at the recorded cell (%d, %d)"
			% [STORE_INTENT_CELL.x, STORE_INTENT_CELL.y])
		return
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(object.cell))
	if not bool(pressed.get("ok", false)):
		_store_capture_fail("select", str(pressed.get("error", "")))
		return
	if selection() != object:
		_store_capture_fail("select",
			"the press at (%d, %d) did not select the recorded building"
			% [STORE_INTENT_CELL.x, STORE_INTENT_CELL.y])
		return
	var armed: Dictionary = arm_store()
	if not bool(armed.get("ok", false)):
		_store_capture_fail("arm", str(armed.get("error", "")))
		return
	var confirmed: Dictionary = await confirm_store()
	if not bool(confirmed.get("ok", false)):
		_store_capture_fail("confirm", str(confirmed.get("error", "")))
		return
	print("[town] store-capture applied item_index=%d cell=(%d, %d) objects=%d "
		% [int(armed.get("slot", -1)), STORE_INTENT_CELL.x,
			STORE_INTENT_CELL.y, objects.size()]
		+ "storage=%s" % JSON.stringify(_storage_record()))
	_capture_and_quit()


## A named store-capture failure: explicit marker + exit 1, so a failed flow
## never leaves an open window or a misleading frame.
func _store_capture_fail(step: String, detail: String) -> void:
	print("[town] store-capture state=error step=%s detail=%s" % [
		step, detail])
	get_tree().quit(1)


## The depth-topmost rendered object covering a cell (the same rule the
## press path applies: the last object in draw order wins), or null.
func _object_for_cell(cell: Vector2i) -> Variant:
	var hit: Variant = null
	for object: Variant in objects:
		if object != null and object.contains_cell(cell):
			hit = object
	return hit


## Reads a `--<prefix><value>` user argument (boot/gd precedent).
static func _user_arg(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


# ---------------------------------------------------------------------------
# Evidence report (M6 design D10 step 3, task 8.3; placement design D11)
# ---------------------------------------------------------------------------

## The report output path from the user arguments: `--town-report=<path>`
## (relative paths resolve against the project directory), the bare
## `--town-report` flag's default evidence path, or "" when absent.
func _report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--town-report":
			return Paths.project_dir().path_join(DEFAULT_REPORT_PATH)
		if argument.begins_with("--town-report="):
			var value := argument.trim_prefix("--town-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the report flow and quits with the documented exit code: 0 when
## the deterministic report is written, 1 with an explicit marker naming
## the first failed step.
func _write_town_report(report_path: String) -> void:
	var problem: String = await _report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole report and writes it; returns "" on success or the
## first failure as an explicit message. Both views rebuild from the
## committed inputs here: the player save through the fake GameApi
## (exactly one bootstrap request, observed by the facade's counter) and
## the slice village through the slice scene — the same inputs the
## windowed captures consumed.
func _report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var boot: Variant = await api.get_bootstrap(str(sessions.saves[0].id))
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	# Player town: this very scene rebuilds from the typed state.
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] player town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] player town rendered no objects"
	var probe: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(objects[0].cell))
	if not bool(probe.get("ok", false)):
		return "[report] player selection probe rejected: %s" \
			% probe.get("error", "")
	var player_records: Dictionary = _town_records(self)
	# Slice town: the preserved village through the same components. The
	# tree is still setting up children while this scene's _ready runs, so
	# yield one frame before attaching the slice to the root.
	var slice_scene: PackedScene = load("res://scenes/town_slice.tscn")
	if slice_scene == null:
		return "[report] slice scene failed to load"
	var slice: Node2D = slice_scene.instantiate()
	await get_tree().process_frame
	get_tree().root.add_child(slice)
	if str(slice.view_state) != "built":
		var slice_error := str(slice.build_error)
		slice.free()
		return "[report] slice town failed to build: %s" % slice_error
	if slice.objects.is_empty():
		slice.free()
		return "[report] slice town rendered no objects"
	var slice_probe: Dictionary = slice.handle_pointer_press(
		Iso.grid_to_screen(slice.objects[0].cell))
	if not bool(slice_probe.get("ok", false)):
		slice.free()
		return "[report] slice selection probe rejected: %s" \
			% slice_probe.get("error", "")
	var slice_records: Dictionary = _town_records(slice)
	slice.free()
	return _write_report_file(report_path, {
		"schema": "town-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"slice_village": _digest_record(REPORT_VILLAGE),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"player_town": player_records,
		"slice_town": slice_records,
		"captures": {
			"town-player.png": _digest_record(REPORT_CAPTURE_PLAYER),
			"town-slice.png": _digest_record(REPORT_CAPTURE_SLICE),
		},
		"non_claims": NON_CLAIMS,
	})


## The observed structural records for one built view (spec: counts by
## chosen visual source, HUD values, selection/camera state).
func _town_records(view: Variant) -> Dictionary:
	var camera: Variant = view.camera
	var bounds: Rect2 = camera.world_bounds()
	var hud: Variant = view.hud()
	return {
		"objects": int(view.objects.size()),
		"counts_by_visual_source": view.object_counts_by_source(),
		"hud": hud.displayed_fields(),
		"selection_legacy_id": int(view.selection_legacy_id()),
		"camera": {
			"world_bounds_committed": bool(camera.has_world_bounds()),
			"world_bounds": [bounds.position.x, bounds.position.y,
				bounds.size.x, bounds.size.y],
			"position": [camera.position.x, camera.position.y],
			"zoom_level": int(camera.zoom_level()),
			"zoom_factor": float(camera.zoom_factor()),
		},
	}


## The committed projection constants with their derivation status and
## the recorded evidence gap (spec: "the committed projection constants
## and their derivation status").
func _constants_record() -> Dictionary:
	var world := Iso.world_rect()
	return {
		"tile_width": Iso.TILE_WIDTH,
		"tile_height": Iso.TILE_HEIGHT,
		"grid_extent": Iso.GRID_EXTENT,
		"origin_x": Iso.ORIGIN_X,
		"origin_y": Iso.ORIGIN_Y,
		"world_rect": [world.position.x, world.position.y,
			world.size.x, world.size.y],
		"derivation_status": "derived-provisional",
		"evidence_gap": EVIDENCE_GAP,
	}


## One input/capture record: the repository-relative path plus its
## SHA-256. A missing file records an empty digest fail-closed instead of
## inventing one (the committed captures are inputs to the report).
func _digest_record(relative: String) -> Dictionary:
	if relative.is_empty():
		return {"path": "", "sha256": ""}
	var absolute := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(absolute):
		return {"path": relative, "sha256": ""}
	return {"path": relative, "sha256": Paths.file_sha256(absolute)}


## The island image's repository-relative runtime path (a rendered input
## of both views), resolved through ContentRegistry asset resolution.
func _terrain_runtime(registry: Variant) -> String:
	var asset: Dictionary = registry.resolve_asset(
		TownTerrain.TERRAIN_KIND, TownTerrain.TERRAIN_REF)
	if not bool(asset.get("found", false)):
		return ""
	var entry: Variant = asset.get("entry")
	if not (entry is Dictionary):
		return ""
	return str(entry.get("runtime", ""))


## Serializes the report deterministically (sorted keys, tab indent, no
## timestamps or run-varying provenance) and writes it, creating the
## destination directory when needed.
func _write_report_file(report_path: String, report: Dictionary) -> String:
	var json := JSON.stringify(report, "\t", true) + "\n"
	var directory := report_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		var made: int = DirAccess.make_dir_recursive_absolute(directory)
		if made != OK:
			return "[report] cannot create %s (error %s)" % [directory, made]
	var file := FileAccess.open(report_path, FileAccess.WRITE)
	if file == null:
		return "[report] cannot write %s: %s" % [
			report_path, error_string(FileAccess.get_open_error())]
	file.store_string(json)
	file.close()
	return ""


# ---------------------------------------------------------------------------
# Placement evidence report (building-placement, design D11)
# ---------------------------------------------------------------------------

## The placement report output path from the user arguments:
## `--placement-report=<path>` (relative paths resolve against the
## project directory), the bare `--placement-report` flag's default
## evidence path, or "" when absent.
func _placement_report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--placement-report":
			return Paths.project_dir().path_join(
				DEFAULT_PLACEMENT_REPORT_PATH)
		if argument.begins_with("--placement-report="):
			var value := argument.trim_prefix("--placement-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the placement report flow and quits with the documented exit
## code: 0 when the deterministic report is written, 1 with an explicit
## marker naming the first failed step (the town-report pattern).
func _write_placement_report(report_path: String) -> void:
	var problem: String = await _placement_report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] placement-report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] placement-report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole placement report (design D11): the bootstrap
## payload in hand parses fail-closed (exactly one bootstrap request,
## no second config call), the town builds from the committed save, one
## House I intent runs through the same picker flow a player uses
## (entry, pick, preview, confirm against the fake implementation), and
## the structural report records intent, before/after counts and
## resources, input digests, the projection constants pointer, the fake
## capture pointer, and every required non-claim. Returns "" on success
## or the first failure as an explicit message.
func _placement_report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var session: Variant = get_node_or_null("/root/Session")
	if session == null:
		return "[report] Session is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var pid := str(sessions.saves[0].id)
	var boot: Variant = await api.get_bootstrap(pid)
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var config: BootData.ConfigPayload = boot.config
	if config == null:
		return "[report] bootstrap carried no config"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] town rendered no objects"
	# The session the confirm needs: a real launch activates it during
	# boot, while this headless report flow commits it here.
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	if not bool(activation.get("ok", false)):
		return "[report] session activation failed: %s" \
			% activation.get("error", "")
	var placements_before: int = state.placements.size()
	var objects_before: int = objects.size()
	var resources_before := _report_resources()
	# The catalog derives from the payload in hand — the same
	# fail-closed parse the boot handoff performs (no second bootstrap).
	var catalog: Dictionary = PlacementCatalog.parse(config.raw)
	if not bool(catalog.get("ok", false)):
		return "[report] placement catalog rejected: %s" % catalog.get("error", "")
	set_placement_catalog(catalog)
	var entered: Dictionary = enter_placement()
	if not bool(entered.get("ok", false)):
		return "[report] placement entry rejected: %s" % entered.get("error", "")
	var picked: Dictionary = pick_placement(PLACEMENT_INTENT_ITEM)
	if not bool(picked.get("ok", false)):
		return "[report] placement pick rejected: %s" % picked.get("error", "")
	var preview: Dictionary = preview_placement_cell(PLACEMENT_INTENT_CELL)
	if not bool(preview.get("valid", false)):
		return "[report] placement preview rejected: %s" % preview.get("reason", "")
	var confirmed: Dictionary = await confirm_placement()
	if not bool(confirmed.get("ok", false)):
		return "[report] placement confirm failed: %s" % confirmed.get("error", "")
	if state.placements.size() != placements_before + 1:
		return "[report] placement did not add exactly one entry " \
			+ "(before=%d after=%d)" % [placements_before,
			state.placements.size()]
	if objects.size() != objects_before + 1:
		return "[report] placement did not add exactly one object " \
			+ "(before=%d after=%d)" % [objects_before, objects.size()]
	return _write_report_file(report_path, {
		"schema": "placement-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"placement_requests": int(api.placement_requests),
		"intent": {
			"user_id": pid,
			"item_id": PLACEMENT_INTENT_ITEM,
			"x": PLACEMENT_INTENT_CELL.x,
			"y": PLACEMENT_INTENT_CELL.y,
			"orientation": PLACEMENT_INTENT_ORIENTATION,
		},
		"counts": {
			"placements_before": placements_before,
			"placements_after": state.placements.size(),
			"objects_before": objects_before,
			"objects_after": objects.size(),
		},
		"resources": {
			"before": resources_before,
			"after": _report_resources(),
		},
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"placement_request": _digest_record(REPORT_PLACEMENT_REQUEST),
			"placement_response": _digest_record(REPORT_PLACEMENT_RESPONSE),
			"placement_after": _digest_record(REPORT_PLACEMENT_AFTER),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"capture": _placement_capture_record(),
		"non_claims": PLACEMENT_NON_CLAIMS,
	})


## The resource/XP snapshot the placement report records before and
## after the intent: the typed state's own fields (the same values the
## HUD reads), never computed deltas.
func _report_resources() -> Dictionary:
	return {
		"cash": int(state.resources.cash),
		"coins": int(state.resources.coins),
		"energy": int(state.resources.energy),
		"mana": int(state.resources.mana),
		"oil": int(state.resources.oil),
		"steel": int(state.resources.steel),
		"wood": int(state.resources.wood),
		"xp": int(state.summary.xp),
	}


## The fake-capture pointer (design D11): the committed windowed capture
## with its digest plus the plain statement of what it proves — so no
## reader can mistake the screenshot for executed-legacy proof.
func _placement_capture_record() -> Dictionary:
	var record := _digest_record(REPORT_CAPTURE_PLACEMENT)
	record["implementation"] = "fake GameApi (a deterministic test " \
		+ "double, not a parity oracle)"
	record["parity_pointer"] = "real-execution parity is established " \
		+ "by the fixture-replay tests and the verify-boot placement " \
		+ "live phase"
	return record


# ---------------------------------------------------------------------------
# Purchase evidence report (building-purchase, design D9)
# ---------------------------------------------------------------------------


## The purchase report output path from the user arguments:
## `--purchase-report=<path>` (relative paths resolve against the project
## directory), the bare `--purchase-report` flag's default evidence path,
## or "" when absent.
func _purchase_report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--purchase-report":
			return Paths.project_dir().path_join(
				DEFAULT_PURCHASE_REPORT_PATH)
		if argument.begins_with("--purchase-report="):
			var value := argument.trim_prefix("--purchase-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the purchase report flow and quits with the documented exit code:
## 0 when the deterministic report is written, 1 with an explicit marker
## naming the first failed step (the town/placement report pattern).
func _write_purchase_report(report_path: String) -> void:
	var problem: String = await _purchase_report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] purchase-report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] purchase-report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole purchase report (design D9): the bootstrap payload in
## hand parses fail-closed (exactly one bootstrap request, no second config
## call), the town builds from the committed save, one Victory Arch intent
## runs through the same shop flow a player uses (enter, pick, confirm
## against the fake implementation), and the structural report records the
## intent, the storage and resource before/after values, the request
## counts, input digests, the projection constants pointer, the fake
## capture pointer, and every required non-claim. Returns "" on success or
## the first failure as an explicit message.
func _purchase_report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var session: Variant = get_node_or_null("/root/Session")
	if session == null:
		return "[report] Session is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var pid := str(sessions.saves[0].id)
	var boot: Variant = await api.get_bootstrap(pid)
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var config: BootData.ConfigPayload = boot.config
	if config == null:
		return "[report] bootstrap carried no config"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] town rendered no objects"
	# The session the confirm needs: a real launch activates it during
	# boot, while this headless report flow commits it here.
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	if not bool(activation.get("ok", false)):
		return "[report] session activation failed: %s" \
			% activation.get("error", "")
	var storage_before: Dictionary = _storage_record()
	var resources_before: Dictionary = _report_resources()
	# The catalog derives from the payload in hand — the same fail-closed
	# parse the boot handoff performs (no second bootstrap).
	var catalog: Dictionary = PlacementCatalog.parse(config.raw)
	if not bool(catalog.get("ok", false)):
		return "[report] shop catalog rejected: %s" % catalog.get("error", "")
	set_shop_catalog(catalog)
	var entries_before: int = shop_catalog_entries().size()
	if entries_before == 0:
		return "[report] the shop offered no entry at level %d" \
			% int(state.summary.level)
	var entered: Dictionary = enter_shop()
	if not bool(entered.get("ok", false)):
		return "[report] shop entry rejected: %s" % entered.get("error", "")
	var picked: Dictionary = pick_shop_item(PURCHASE_INTENT_ITEM)
	if not bool(picked.get("ok", false)):
		return "[report] shop pick rejected: %s" % picked.get("error", "")
	var confirmed: Dictionary = await confirm_purchase()
	if not bool(confirmed.get("ok", false)):
		return "[report] purchase confirm failed: %s" % confirmed.get("error", "")
	var storage_after: Dictionary = _storage_record()
	if int(storage_after.get(str(PURCHASE_INTENT_ITEM), 0)) != 1:
		return "[report] the purchase did not land in storage (got %s)" \
			% JSON.stringify(storage_after)
	return _write_report_file(report_path, {
		"schema": "purchase-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"purchase_requests": int(api.purchase_requests),
		"intent": {
			"user_id": pid,
			"item_id": PURCHASE_INTENT_ITEM,
		},
		"shop_entries_at_level": entries_before,
		"storage": {
			"before": storage_before,
			"after": storage_after,
		},
		"resources": {
			"before": resources_before,
			"after": _report_resources(),
		},
		"readout": storage_texts(),
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"purchase_request": _digest_record(REPORT_PURCHASE_REQUEST),
			"purchase_response": _digest_record(REPORT_PURCHASE_RESPONSE),
			"purchase_after": _digest_record(REPORT_PURCHASE_AFTER),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"capture": _purchase_capture_record(),
		"non_claims": PURCHASE_NON_CLAIMS,
	})


## The storage snapshot the purchase report records before and after the
## intent: the typed state's own mapping, exactly as the readout renders it
## (never computed deltas).
func _storage_record() -> Dictionary:
	var record := {}
	if state == null:
		return record
	for key: Variant in state.storage:
		record[str(key)] = int(state.storage[key])
	return record


## The fake-capture pointer (design D9): the committed windowed capture
## with its digest plus the plain statement of what it proves — so no
## reader can mistake the screenshot for executed-legacy proof.
func _purchase_capture_record() -> Dictionary:
	var record := _digest_record(REPORT_CAPTURE_PURCHASE)
	record["implementation"] = "fake GameApi (a deterministic test " \
		+ "double, not a parity oracle)"
	record["parity_pointer"] = "real-execution parity is established " \
		+ "by the fixture-replay tests and the verify-boot purchase " \
		+ "live phase"
	return record


# ---------------------------------------------------------------------------
# Move evidence report (building-move, design D9)
# ---------------------------------------------------------------------------


## The move report output path from the user arguments:
## `--move-report=<path>` (relative paths resolve against the project
## directory), the bare `--move-report` flag's default evidence path, or ""
## when absent.
func _move_report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--move-report":
			return Paths.project_dir().path_join(DEFAULT_MOVE_REPORT_PATH)
		if argument.begins_with("--move-report="):
			var value := argument.trim_prefix("--move-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the move report flow and quits with the documented exit code: 0 when
## the deterministic report is written, 1 with an explicit marker naming the
## first failed step (the town/placement/purchase report pattern).
func _write_move_report(report_path: String) -> void:
	var problem: String = await _move_report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] move-report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] move-report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole move report (design D9): the bootstrap payload in hand
## parses fail-closed (exactly one bootstrap request, no second config
## call), the town builds from the committed save, the recorded building is
## selected and one move intent runs through the same flow a player uses
## (select, arm, preview, confirm against the fake implementation), and the
## structural report records the intent, the building's cell before and
## after, the placement/object counts, the resources, the request counts,
## input digests, the projection constants pointer, the fake capture
## pointer, and every required non-claim. Returns "" on success or the first
## failure as an explicit message.
func _move_report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var session: Variant = get_node_or_null("/root/Session")
	if session == null:
		return "[report] Session is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var pid := str(sessions.saves[0].id)
	var boot: Variant = await api.get_bootstrap(pid)
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] town rendered no objects"
	# The session the confirm needs: a real launch activates it during boot,
	# while this headless report flow commits it here.
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	if not bool(activation.get("ok", false)):
		return "[report] session activation failed: %s" \
			% activation.get("error", "")
	var moving: Variant = _placement_for_slot(MOVE_INTENT_INDEX)
	if moving == null:
		return "[report] no placement carries the recorded legacy key %d" \
			% MOVE_INTENT_INDEX
	if moving.cell != MOVE_INTENT_FROM:
		return "[report] the recorded building sits at (%d, %d), not (%d, %d)" \
			% [moving.cell.x, moving.cell.y, MOVE_INTENT_FROM.x,
				MOVE_INTENT_FROM.y]
	if int(moving.item) != MOVE_INTENT_ITEM:
		return "[report] the recorded building is item %d, not %d" \
			% [int(moving.item), MOVE_INTENT_ITEM]
	var placements_before: int = state.placements.size()
	var objects_before: int = objects.size()
	var resources_before: Dictionary = _report_resources()
	var row_before := _typed_row(moving.raw)
	# The player's own selection path: press the recorded building's cell,
	# then arm, preview the recorded target, and confirm. Nothing here
	# bypasses the flow a player uses.
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(MOVE_INTENT_FROM))
	if not bool(pressed.get("ok", false)):
		return "[report] selection probe rejected: %s" % pressed.get("error", "")
	if selection_legacy_id() != MOVE_INTENT_ITEM:
		return "[report] the press did not select item %d (selected %d)" \
			% [MOVE_INTENT_ITEM, selection_legacy_id()]
	var armed: Dictionary = arm_move()
	if not bool(armed.get("ok", false)):
		return "[report] move arm rejected: %s" % armed.get("error", "")
	if int(armed.get("slot", -1)) != MOVE_INTENT_INDEX:
		return "[report] the armed move names key %d, not %d" \
			% [int(armed.get("slot", -1)), MOVE_INTENT_INDEX]
	var preview: Dictionary = preview_move_cell(MOVE_INTENT_TO)
	if not bool(preview.get("valid", false)):
		return "[report] move preview rejected: %s" % preview.get("reason", "")
	var confirmed: Dictionary = await confirm_move()
	if not bool(confirmed.get("ok", false)):
		return "[report] move confirm failed: %s" % confirmed.get("error", "")
	# A move rewrites one row in place: the counts must be unchanged, and the
	# row must now carry the target cell and nothing else new.
	if state.placements.size() != placements_before:
		return "[report] the move changed the placement count " \
			+ "(before=%d after=%d)" % [placements_before,
				state.placements.size()]
	if objects.size() != objects_before:
		return "[report] the move changed the object count " \
			+ "(before=%d after=%d)" % [objects_before, objects.size()]
	if moving.cell != MOVE_INTENT_TO:
		return "[report] the building did not land at (%d, %d) (got (%d, %d))" \
			% [MOVE_INTENT_TO.x, MOVE_INTENT_TO.y, moving.cell.x,
				moving.cell.y]
	return _write_report_file(report_path, {
		"schema": "move-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"move_requests": int(api.move_requests),
		"intent": {
			"user_id": pid,
			"item_index": MOVE_INTENT_INDEX,
			"x": MOVE_INTENT_TO.x,
			"y": MOVE_INTENT_TO.y,
		},
		"moved_building": {
			"legacy_id": int(moving.item),
			"slot": int(moving.slot),
			"name": str(moving.name),
			"cell_before": [MOVE_INTENT_FROM.x, MOVE_INTENT_FROM.y],
			"cell_after": [moving.cell.x, moving.cell.y],
			"row_before": row_before,
			"row_after": _typed_row(moving.raw),
		},
		"counts": {
			"placements_before": placements_before,
			"placements_after": state.placements.size(),
			"objects_before": objects_before,
			"objects_after": objects.size(),
		},
		"resources": {
			"before": resources_before,
			"after": _report_resources(),
		},
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"move_request": _digest_record(REPORT_MOVE_REQUEST),
			"move_response": _digest_record(REPORT_MOVE_RESPONSE),
			"move_after": _digest_record(REPORT_MOVE_AFTER),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"capture": _move_capture_record(),
		"non_claims": MOVE_NON_CLAIMS,
	})


## One persisted eight-field row in the canonical typed form the report
## records: the JSON transport widens the save's ints to floats on the
## pinned engine, and a report whose before/after rows differ only by
## `58` vs `58.0` would hide the actual change. Every integral number
## becomes an `int`; the nested `store`/`attr` structures pass through
## untouched, so only the representation is normalized, never the value.
func _typed_row(value: Variant) -> Array:
	var row: Array = []
	if not (value is Array):
		return row
	for element: Variant in (value as Array):
		if element is int or element is float:
			row.append(int(element) if float(element) == floor(
				float(element)) else element)
		else:
			row.append(element)
	return row


## The committed placement carrying the given addressable legacy key, or
## null when the save names no such row (fail-closed, never a substitute).
func _placement_for_slot(slot: int) -> Variant:
	if state == null:
		return null
	for placement: Variant in state.placements:
		if placement != null and int(placement.slot) == slot:
			return placement
	return null


## The fake-capture pointer (design D9): the committed windowed capture with
## its digest plus the plain statement of what it proves — so no reader can
## mistake the screenshot for executed-legacy proof.
func _move_capture_record() -> Dictionary:
	var record := _digest_record(REPORT_CAPTURE_MOVE)
	record["implementation"] = "fake GameApi (a deterministic test " \
		+ "double, not a parity oracle)"
	record["parity_pointer"] = "real-execution parity is established " \
		+ "by the fixture-replay tests and the verify-boot move-live phase"
	return record


# ---------------------------------------------------------------------------
# Sell evidence report (building-sell, design D10)
# ---------------------------------------------------------------------------


## The sell report output path from the user arguments:
## `--sell-report=<path>` (relative paths resolve against the project
## directory), the bare `--sell-report` flag's default evidence path, or ""
## when absent.
func _sell_report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--sell-report":
			return Paths.project_dir().path_join(DEFAULT_SELL_REPORT_PATH)
		if argument.begins_with("--sell-report="):
			var value := argument.trim_prefix("--sell-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the sell report flow and quits with the documented exit code: 0 when
## the deterministic report is written, 1 with an explicit marker naming the
## first failed step (the town/placement/purchase/move report pattern).
func _write_sell_report(report_path: String) -> void:
	var problem: String = await _sell_report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] sell-report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] sell-report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole sell report (design D10): the bootstrap payload in hand
## parses fail-closed (exactly one bootstrap request, no second config call),
## the town builds from the committed save, the recorded building is selected
## and one sell intent runs through the same flow a player uses (select, arm,
## confirm against the fake implementation), and the structural report records
## the intent, the removed building's row and cell, the placement/object
## counts, the resources, the request counts, input digests, the projection
## constants pointer, the fake capture pointer, and every required non-claim.
## Returns "" on success or the first failure as an explicit message.
func _sell_report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var session: Variant = get_node_or_null("/root/Session")
	if session == null:
		return "[report] Session is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var pid := str(sessions.saves[0].id)
	var boot: Variant = await api.get_bootstrap(pid)
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] town rendered no objects"
	# The session the confirm needs: a real launch activates it during boot,
	# while this headless report flow commits it here.
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	if not bool(activation.get("ok", false)):
		return "[report] session activation failed: %s" \
			% activation.get("error", "")
	var sold: Variant = _placement_for_slot(SELL_INTENT_INDEX)
	if sold == null:
		return "[report] no placement carries the recorded legacy key %d" \
			% SELL_INTENT_INDEX
	if sold.cell != SELL_INTENT_CELL:
		return "[report] the recorded building sits at (%d, %d), not (%d, %d)" \
			% [sold.cell.x, sold.cell.y, SELL_INTENT_CELL.x,
				SELL_INTENT_CELL.y]
	if int(sold.item) != SELL_INTENT_ITEM:
		return "[report] the recorded building is item %d, not %d" \
			% [int(sold.item), SELL_INTENT_ITEM]
	var placements_before: int = state.placements.size()
	var objects_before: int = objects.size()
	var resources_before: Dictionary = _report_resources()
	var row_before := _typed_row(sold.raw)
	# The player's own selection path: press the recorded building's cell,
	# arm the sale, and confirm. Nothing here bypasses the flow a player uses.
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(SELL_INTENT_CELL))
	if not bool(pressed.get("ok", false)):
		return "[report] selection probe rejected: %s" % pressed.get("error", "")
	if selection_legacy_id() != SELL_INTENT_ITEM:
		return "[report] the press did not select item %d (selected %d)" \
			% [SELL_INTENT_ITEM, selection_legacy_id()]
	var armed: Dictionary = arm_sell()
	if not bool(armed.get("ok", false)):
		return "[report] sell arm rejected: %s" % armed.get("error", "")
	if int(armed.get("slot", -1)) != SELL_INTENT_INDEX:
		return "[report] the armed sale names key %d, not %d" \
			% [int(armed.get("slot", -1)), SELL_INTENT_INDEX]
	var confirmed: Dictionary = await confirm_sell()
	if not bool(confirmed.get("ok", false)):
		return "[report] sell confirm failed: %s" % confirmed.get("error", "")
	# A sale removes exactly one row: the counts must fall by one, and the
	# recorded key must be gone from the typed state.
	if state.placements.size() != placements_before - 1:
		return "[report] the sale did not remove exactly one placement " \
			+ "(before=%d after=%d)" % [placements_before,
				state.placements.size()]
	if objects.size() != objects_before - 1:
		return "[report] the sale did not remove exactly one object " \
			+ "(before=%d after=%d)" % [objects_before, objects.size()]
	if _placement_for_slot(SELL_INTENT_INDEX) != null:
		return "[report] the sold placement is still addressable by key %d" \
			% SELL_INTENT_INDEX
	return _write_report_file(report_path, {
		"schema": "sell-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"sell_requests": int(api.sell_requests),
		"intent": {
			"user_id": pid,
			"item_index": SELL_INTENT_INDEX,
		},
		"sold_building": {
			"legacy_id": int(sold.item),
			"slot": int(sold.slot),
			"name": str(sold.name),
			"cell": [SELL_INTENT_CELL.x, SELL_INTENT_CELL.y],
			"removed_row": row_before,
		},
		"counts": {
			"placements_before": placements_before,
			"placements_after": state.placements.size(),
			"objects_before": objects_before,
			"objects_after": objects.size(),
		},
		"resources": {
			"before": resources_before,
			"after": _report_resources(),
		},
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"sell_request": _digest_record(REPORT_SELL_REQUEST),
			"sell_response": _digest_record(REPORT_SELL_RESPONSE),
			"sell_after": _digest_record(REPORT_SELL_AFTER),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"capture": _sell_capture_record(),
		"non_claims": SELL_NON_CLAIMS,
	})


## The fake-capture pointer (building-sell design D10): the committed
## windowed capture with its digest plus the plain statement of what it
## proves — so no reader can mistake the screenshot for executed-legacy
## proof.
func _sell_capture_record() -> Dictionary:
	var record := _digest_record(REPORT_CAPTURE_SELL)
	record["implementation"] = "fake GameApi (a deterministic test " \
		+ "double, not a parity oracle)"
	record["parity_pointer"] = "real-execution parity is established " \
		+ "by the fixture-replay tests and the verify-boot sell-live phase"
	return record


# ---------------------------------------------------------------------------
# Store evidence report (building-store, design D9)
# ---------------------------------------------------------------------------


## The store report output path from the user arguments:
## `--store-report=<path>` (relative paths resolve against the project
## directory), the bare `--store-report` flag's default evidence path, or ""
## when absent.
func _store_report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--store-report":
			return Paths.project_dir().path_join(DEFAULT_STORE_REPORT_PATH)
		if argument.begins_with("--store-report="):
			var value := argument.trim_prefix("--store-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the store report flow and quits with the documented exit code: 0 when
## the deterministic report is written, 1 with an explicit marker naming the
## first failed step (the town/placement/purchase/move/sell report pattern).
func _write_store_report(report_path: String) -> void:
	var problem: String = await _store_report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] store-report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] store-report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole store report (design D9): the bootstrap payload in hand
## parses fail-closed (exactly one bootstrap request, no second config call),
## the town builds from the committed save, the recorded building is selected
## and one store intent runs through the same flow a player uses (select, arm,
## confirm against the fake implementation), and the structural report records
## the intent, the stored building's row and cell, the storage mapping and
## placement/object counts before and after, the resources, the request
## counts, input digests, the projection constants pointer, the fake capture
## pointer, and every required non-claim. Returns "" on success or the first
## failure as an explicit message.
func _store_report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var session: Variant = get_node_or_null("/root/Session")
	if session == null:
		return "[report] Session is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var pid := str(sessions.saves[0].id)
	var boot: Variant = await api.get_bootstrap(pid)
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] town rendered no objects"
	# The session the confirm needs: a real launch activates it during boot,
	# while this headless report flow commits it here.
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	if not bool(activation.get("ok", false)):
		return "[report] session activation failed: %s" \
			% activation.get("error", "")
	var stored: Variant = _placement_for_slot(STORE_INTENT_INDEX)
	if stored == null:
		return "[report] no placement carries the recorded legacy key %d" \
			% STORE_INTENT_INDEX
	if stored.cell != STORE_INTENT_CELL:
		return "[report] the recorded building sits at (%d, %d), not (%d, %d)" \
			% [stored.cell.x, stored.cell.y, STORE_INTENT_CELL.x,
				STORE_INTENT_CELL.y]
	if int(stored.item) != STORE_INTENT_ITEM:
		return "[report] the recorded building is item %d, not %d" \
			% [int(stored.item), STORE_INTENT_ITEM]
	var placements_before: int = state.placements.size()
	var objects_before: int = objects.size()
	var storage_before: Dictionary = _storage_record()
	var resources_before: Dictionary = _report_resources()
	var row_before := _typed_row(stored.raw)
	# The player's own selection path: press the recorded building's cell,
	# arm the store, and confirm. Nothing here bypasses the flow a player
	# uses.
	var pressed: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(STORE_INTENT_CELL))
	if not bool(pressed.get("ok", false)):
		return "[report] selection probe rejected: %s" % pressed.get("error", "")
	if selection_legacy_id() != STORE_INTENT_ITEM:
		return "[report] the press did not select item %d (selected %d)" \
			% [STORE_INTENT_ITEM, selection_legacy_id()]
	var armed: Dictionary = arm_store()
	if not bool(armed.get("ok", false)):
		return "[report] store arm rejected: %s" % armed.get("error", "")
	if int(armed.get("slot", -1)) != STORE_INTENT_INDEX:
		return "[report] the armed store names key %d, not %d" \
			% [int(armed.get("slot", -1)), STORE_INTENT_INDEX]
	var confirmed: Dictionary = await confirm_store()
	if not bool(confirmed.get("ok", false)):
		return "[report] store confirm failed: %s" % confirmed.get("error", "")
	# A store removes exactly one row: the counts must fall by one, the
	# recorded key must be gone from the typed state, and the item's id must
	# have landed in the storage mapping with the response's quantity.
	if state.placements.size() != placements_before - 1:
		return "[report] the store did not remove exactly one placement " \
			+ "(before=%d after=%d)" % [placements_before,
				state.placements.size()]
	if objects.size() != objects_before - 1:
		return "[report] the store did not remove exactly one object " \
			+ "(before=%d after=%d)" % [objects_before, objects.size()]
	if _placement_for_slot(STORE_INTENT_INDEX) != null:
		return "[report] the stored placement is still addressable by key %d" \
			% STORE_INTENT_INDEX
	var storage_after: Dictionary = _storage_record()
	if int(storage_after.get(str(STORE_INTENT_ITEM), 0)) != 1:
		return "[report] the stored building did not land in storage (got %s)" \
			% JSON.stringify(storage_after)
	return _write_report_file(report_path, {
		"schema": "store-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"store_requests": int(api.store_requests),
		"intent": {
			"user_id": pid,
			"item_index": STORE_INTENT_INDEX,
		},
		"stored_building": {
			"legacy_id": int(stored.item),
			"slot": int(stored.slot),
			"name": str(stored.name),
			"cell": [STORE_INTENT_CELL.x, STORE_INTENT_CELL.y],
			"removed_row": row_before,
		},
		"storage": {
			"before": storage_before,
			"after": storage_after,
		},
		"readout": storage_texts(),
		"counts": {
			"placements_before": placements_before,
			"placements_after": state.placements.size(),
			"objects_before": objects_before,
			"objects_after": objects.size(),
		},
		"resources": {
			"before": resources_before,
			"after": _report_resources(),
		},
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"store_request": _digest_record(REPORT_STORE_REQUEST),
			"store_response": _digest_record(REPORT_STORE_RESPONSE),
			"store_after": _digest_record(REPORT_STORE_AFTER),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"capture": _store_capture_record(),
		"non_claims": STORE_NON_CLAIMS,
	})


## The fake-capture pointer (building-store design D9): the committed
## windowed capture with its digest plus the plain statement of what it
## proves — so no reader can mistake the screenshot for executed-legacy
## proof.
func _store_capture_record() -> Dictionary:
	var record := _digest_record(REPORT_CAPTURE_STORE)
	record["implementation"] = "fake GameApi (a deterministic test " \
		+ "double, not a parity oracle)"
	record["parity_pointer"] = "real-execution parity is established " \
		+ "by the fixture-replay tests and the verify-boot store-live phase"
	return record
