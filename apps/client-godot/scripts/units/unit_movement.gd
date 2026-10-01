extends RefCounted
## Typed, read-only placement projection for a unit row (OpenSpec
## `godot-unit-movement` "A unit row's placement is projected, never derived" /
## "Committed movement fields are content, not rules" / "The movement-command
## inventory classifies what each command does and does not check" / "The row
## instant is client-writable, and no readiness is derived from it" / "Movement
## is content, not a server operation" / "No executed-legacy movement fixture is
## claimed" / "Unit-movement evidence and claim limits", design D1-D7).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy server has **no movement rule**. The single command that moves a
## row — `move` — rewrites the row's two coordinate slots to client-supplied
## values and does nothing else: no type check, no occupancy check, no bounds
## check, no terrain check, and no use of a speed or a path. It is
## **type-agnostic** and it **already ships** as M7's `godot-building-move`, so
## there is no new server behaviour for this line to add and no unit-specific
## movement command to reproduce.
##
## What is deliverable is therefore a **placement projection** reporting what
## the row and its committed content actually say, plus the **inventory** and
## **refusals** that make the absence auditable (design D1). This is not a stub:
## `velocity` is non-zero on **every one of the 429** committed unit
## definitions and is read by **no** legacy branch, so it is exactly the field a
## later line would reach for to build a travel-time model — with
## `fast_forward`'s **client-writable** instant as its clock. This record closes
## that door with the evidence attached, which is the same shape as the
## delivered `godot-unit-production` refusal.
##
## ## The projection reports the placement and NOTHING derived from it (D1/D4)
##
## `evaluate()` is the one entry point. It reports the row's **committed** cell
## coordinates, its orientation, its recorded row instant, and — read from the
## committed definition it is handed — its committed `velocity`, `width`,
## `height`, and `elevation`, each **verbatim**. It computes **no** value from
## another: no coordinate from a velocity, no offset from a footprint, no
## position from an elevation, and no intermediate position between two
## instants. `ABSENT_HELPERS` names every helper it therefore does not provide,
## and the suite asserts this module's **whole function inventory** against a
## pinned list, so a travel-time, path, terrain, occupancy, bounds, readiness,
## interpolation, or animation helper fails the delivered suite rather than
## appearing quietly later.
##
## ## An unresolvable row is REFUSED with its recorded state intact (D1)
##
## A row that is not a row, or one whose committed coordinates are absent or
## malformed, produces **no placement**: `cell_x` and `cell_y` are `null` —
## never a defaulted origin — and the untouched recorded slots travel beside
## them in `cell_recorded`, so a caller can never mistake a refusal for a row
## standing at (0, 0). The same rule holds one slot out: a malformed
## orientation is reported **absent**, never as a committed zero.
##
## ## The row shape is delegated, never restated (D6 / the instances delta)
##
## The slot indices and the committed row-slot count are read from
## `unit_instance.gd`, which owns the row. This capability owns only the
## placement *view* of it — the cell, the orientation, and the committed
## footprint — so the two cannot drift. It deliberately does **not** call the
## instance's whole-row validator: that gate owns slots this projection does not
## read (the item id and the player team), and borrowing it would make a row
## unresolvable here for a reason that is not about its placement. The
## projection is **type-agnostic**, exactly as the only legacy coordinate writer
## is: `move` never checks a row's committed type, so gating on one here would
## invent a rule the legacy contract does not have.
##
## ## The committed movement fields are CONTENT, never rules (D2)
##
## `velocity`, `width`, `height`, and `elevation` are **read by no legacy
## branch at all** — measured as **zero occurrences** of each string across the
## seven legacy root modules. They are reported **verbatim** so a reader can see
## what the content says, and the recorded fact is what stops the value being
## mistaken for a rule. **No** velocity-based travel time, **no** path, **no**
## terrain or elevation interaction, **no** occupancy rule, **no** bounds rule,
## **no** readiness, and **no** interpolation is derived from any of them.
## `velocity` is the **sixth** committed content field in this project with no
## legacy consumer, and the five already recorded are named beside it.
##
## ## The movement-command inventory, classified (D3)
##
## The useful content is not the list of names but the **classification**:
## `move` is **type-agnostic, already delivered, and checks nothing**;
## `orient` is a plain client-supplied slot write; `pop_unit` is the only other
## command that writes coordinates and it **overwrites** the popped row's item
## id with the client's; and `fast_forward` is the **client-writable instant**.
## A reader who saw only "a `move` command exists" might assume a movement rule
## exists; a reader who sees "it is type-agnostic, it ships as
## `godot-building-move`, and it checks nothing" does not. **This capability
## implements none of them.**
##
## ## The row instant is an OPAQUE recorded value (D4)
##
## `fast_forward` subtracts a **client-supplied** `seconds` from **every** row's
## recorded instant (`command.py:934`) **and** from every row's queue start
## instant `attr["ts"]` (`command.py:939`). The row instant is therefore
## **client-writable**, which is the concrete reason a readiness rule derived
## from it would be an invented rule and not a reproduction: a client can
## rewrite it. `evaluate()` reports it verbatim and computes **no** elapsed time,
## no remaining time, and no readiness from it.
##
## ## The tile geometry stays a gap, never an assumed geometry
##
## The legacy SWF's `TILE_SIZE`, `EI_TILE_HEIGHT_PIXELS`, and grid dimensions
## were **never extracted** — the recorded M6 evidence gap. With `elevation`
## unread server-side and no committed tile geometry, **no** terrain-aware
## movement could be derived from either source even if a rule were invented;
## the absence is recorded here rather than filled with an assumed geometry.
##
## ## Purity
##
## This module holds no node, no clock, no request, and no transport, and it
## reads the content package through **no** preload beyond the delivered
## instance model whose slot indices it shares: every committed number arrives
## as a parameter, so the same functions serve the client, the hermetic suite,
## and the deterministic report.

## The delivered instance model, read for its **row slot indices only**. This
## capability owns the placement *view*; that module owns the row.
const UnitInstance = preload("res://scripts/units/unit_instance.gd")

# ---------------------------------------------------------------------------
# The row's placement slots, delegated and never restated
# ---------------------------------------------------------------------------

## The committed row shape and the four slots a placement reads, taken from the
## module that owns the row. Re-declaring them here would be the second
## definition that could drift.
const ROW_SLOTS := UnitInstance.ROW_SLOTS
const SLOT_CELL_X := UnitInstance.SLOT_CELL_X
const SLOT_CELL_Y := UnitInstance.SLOT_CELL_Y
const SLOT_ROW_INSTANT := UnitInstance.SLOT_ROW_INSTANT
const SLOT_ORIENTATION := UnitInstance.SLOT_ORIENTATION

## The exact-integer range the pinned engine's JSON transport can carry without
## loss. A committed integer outside it is refused rather than rounded.
const MAX_INTEGER := 9007199254740992.0

## The two structural refusals this projection can produce, and no third: a row
## that is not a committed row, and a row whose committed coordinates cannot be
## read. Both are **fail-closed** — `ok` false, no placement, and the recorded
## state kept intact beside the refusal.
const REASON_INVALID_ROW := "invalid_row"
const REASON_UNRESOLVABLE_CELL := "unresolvable_cell"

## The reason a committed definition this projection was handed is not an
## object. It is a **named absence** of the four committed fields rather than an
## error about the row: the placement still resolves, and the footprint is
## reported absent.
const REASON_INVALID_DEFINITION := "invalid_definition"

# ---------------------------------------------------------------------------
# The placement fields, one by one, with their source (design D1)
# ---------------------------------------------------------------------------

## Every field the placement reports, with the row slot or committed field it is
## read from and whether it is a **row** value or **committed content**. This is
## the machine-readable form of "each reported verbatim", and the suite asserts
## that no two fields share a source, which is the structural form of "no value
## is derived from another": a derived field would have to name its source's
## field as well as its own.
const PLACEMENT_FIELDS := [
	{
		"name": "cell_x",
		"source": "row slot 1 (x)",
		"source_kind": "row",
		"slot": SLOT_CELL_X,
		"committed_field": "",
		"verbatim": true,
		"note": "the row's own cell x coordinate, exactly as committed",
	},
	{
		"name": "cell_y",
		"source": "row slot 2 (y)",
		"source_kind": "row",
		"slot": SLOT_CELL_Y,
		"committed_field": "",
		"verbatim": true,
		"note": "the row's own cell y coordinate, exactly as committed",
	},
	{
		"name": "orientation",
		"source": "row slot 4 (orientation)",
		"source_kind": "row",
		"slot": SLOT_ORIENTATION,
		"committed_field": "",
		"verbatim": true,
		"note": "the row's committed orientation code, verbatim; no rotation, "
			+ "facing, or turning rule is applied to it",
	},
	{
		"name": "row_instant",
		"source": "row slot 3 (timestamp)",
		"source_kind": "row",
		"slot": SLOT_ROW_INSTANT,
		"committed_field": "",
		"verbatim": true,
		"note": "OPAQUE. Reported verbatim and treated as a recorded value only: "
			+ "no elapsed time, no remaining time, and no readiness is computed "
			+ "from it, because fast_forward lets a client rewrite it",
	},
	{
		"name": "velocity",
		"source": "committed definition field 'velocity'",
		"source_kind": "committed-content",
		"slot": -1,
		"committed_field": "velocity",
		"verbatim": true,
		"note": "CONTENT ONLY. Positive on all 429 committed units and read by "
			+ "NO legacy branch; no travel time, speed, or duration is derived "
			+ "from it",
	},
	{
		"name": "width",
		"source": "committed definition field 'width'",
		"source_kind": "committed-content",
		"slot": -1,
		"committed_field": "width",
		"verbatim": true,
		"note": "CONTENT ONLY. Reported as a committed number; no offset, "
			+ "rectangle, or covered cell is computed from it here",
	},
	{
		"name": "height",
		"source": "committed definition field 'height'",
		"source_kind": "committed-content",
		"slot": -1,
		"committed_field": "height",
		"verbatim": true,
		"note": "CONTENT ONLY. Reported as a committed number; no offset, "
			+ "rectangle, or covered cell is computed from it here",
	},
	{
		"name": "elevation",
		"source": "committed definition field 'elevation'",
		"source_kind": "committed-content",
		"slot": -1,
		"committed_field": "elevation",
		"verbatim": true,
		"note": "CONTENT ONLY. Reported as a committed number; no position is "
			+ "computed from it and no terrain interaction is derived, partly "
			+ "because the legacy tile geometry was never extracted",
	},
]

## The count the table above fixes, asserted by the suite so a fourth row field
## or a fourth committed field cannot be added without failing the run.
const PLACEMENT_FIELD_COUNT := 8

## How many of the placement fields are read from the ROW and how many from the
## committed definition. Recorded separately because "the footprint and the
## velocity are content, the cell and the orientation are the row's own" is the
## distinction that keeps this capability from becoming a content reader with a
## row attached.
const PLACEMENT_ROW_FIELD_COUNT := 4
const PLACEMENT_CONTENT_FIELD_COUNT := 4

## The refusals, stated as the contract they are. The first is the row shape;
## the second is the fail-closed cell path, and both say the same thing about
## the origin: it is never substituted.
const CELL_REFUSAL := ("A ROW WHOSE COMMITTED COORDINATES ARE ABSENT OR MALFORMED "
	+ "IS REPORTED AS UNRESOLVABLE WITH ITS RECORDED STATE INTACT, AND IS NEVER "
	+ "DEFAULTED TO THE ORIGIN. No legacy branch can produce such a row - move "
	+ "writes client-supplied coordinates into it whatever they are - so this is "
	+ "the client failing closed on untrusted input, not a legacy rule. cell_x "
	+ "and cell_y are reported as null beside the UNTOUCHED recorded slots in "
	+ "cell_recorded, so (0, 0) can never be mistaken for a resolved cell "
	+ "(design D1)")

const NO_DERIVATION := ("NO VALUE IN THIS PROJECTION IS DERIVED FROM ANOTHER. A "
	+ "coordinate is never computed from a velocity, no offset is computed from "
	+ "a footprint, no position is computed from an elevation, and no "
	+ "intermediate position is computed between two instants. The suite proves "
	+ "it structurally in three ways: each reported field names its own source "
	+ "and no two fields share one, a definition carrying an absurd velocity, "
	+ "footprint, and elevation leaves the reported cell untouched, and the "
	+ "same row stamped at two different instants differs in the reported "
	+ "instant and in nothing else (design D1)")

## Whether this projection gates on the row's committed item type. `false`,
## and deliberately so: `move` — the only legacy command that writes a row's
## coordinates — performs **no** type check, so a type gate here would be a rule
## the legacy contract does not have.
const TYPE_AGNOSTIC := true
const TYPE_AGNOSTIC_NOTE := ("THE PLACEMENT PROJECTION IS TYPE-AGNOSTIC, EXACTLY "
	+ "AS THE ONLY LEGACY COORDINATE WRITER IS. move never reads the addressed "
	+ "row's committed item type, so it would rewrite a unit row's coordinates "
	+ "exactly as it rewrites a building's. Gating this projection on committed "
	+ "type 'u' would therefore invent a rule the legacy server does not have, "
	+ "so the delivered use is the unit row and the projection itself refuses "
	+ "nothing about a row's type")

# ---------------------------------------------------------------------------
# The committed movement fields: content only (design D2)
# ---------------------------------------------------------------------------

## The committed field name this capability reports a velocity for, named apart
## so a reader sees the reported value and the field it came from as two facts.
const VELOCITY_FIELD := "velocity"

## The four committed fields this capability reports as content, in the delta's
## order. `velocity` leads because it is the sharpest instance in the project.
const MOVEMENT_FIELDS := [VELOCITY_FIELD, "width", "height", "elevation"]

## The committed footprint trio, named apart from the velocity because the two
## are read from the same definition and refused for the same reason, while only
## one of them could be mistaken for a speed.
const FOOTPRINT_FIELDS := ["width", "height", "elevation"]

## The measured consumer count of every one of the four. It is **zero** for all
## of them: measured as the number of occurrences of each string across the
## seven legacy root modules, with no occurrence in any of them.
const MOVEMENT_FIELD_CONSUMER_COUNT := 0

## The seven legacy root modules the zero-consumer claim is measured over, in
## the committed module set. The suite re-derives all seven figures from these
## bytes, so the claim cannot drift from the source.
const SEARCHED_MODULES := ["command.py", "engine.py", "sessions.py",
	"server.py", "constants.py", "get_game_config.py", "version.py"]

## The four movement-adjacent committed fields the delivered
## `godot-unit-instances` and `godot-unit-definitions` lines did not own, carried
## here because the zero-consumer fact is the same measurement over the same
## seven modules. The suite measures all seven figures independently; only the
## four this capability reports get the `MOVEMENT_FIELDS_REFUSAL` attached.
const SIBLING_ZERO_CONSUMER_FIELDS := ["max_elem_vol", "attack_range",
	"ft_flying", "ft_ground"]

## The refusal, stated as the contract it is.
const MOVEMENT_FIELDS_REFUSAL := ("THE COMMITTED velocity, width, height, AND "
	+ "elevation ARE CONTENT, NEVER RULES. All FOUR have ZERO legacy consumers: "
	+ "measured as occurrences of each string across command.py, engine.py, "
	+ "sessions.py, server.py, constants.py, get_game_config.py, and version.py, "
	+ "each is ZERO, in every one of the seven modules. So NO velocity-based "
	+ "travel time, NO path, NO terrain or elevation interaction, NO occupancy "
	+ "rule, NO bounds rule, NO readiness, and NO interpolation is derived from "
	+ "any of them, and this module provides no helper that would (design D2/D4)")

## The committed distribution, reported as **content** and measured by the suite
## from the verified registry rather than trusted from this sentence.
const MOVEMENT_FIELDS_COVERAGE := ("velocity is positive on ALL 429 committed "
	+ "units - the sharpest case in this project, because a field that looks "
	+ "exactly like a movement rule is read by nothing - and on 145 of the 470 "
	+ "committed buildings, taking exactly three values there (0 on 325, 1 on "
	+ "138, 3 on 7). width, height, and elevation are positive on all 429 units "
	+ "and all 470 buildings, and on every unit the trio takes the SINGLE value "
	+ "1, so the committed unit footprint is uniformly one cell square with "
	+ "elevation 1: a footprint that needs no geometry to be reported. The "
	+ "coverage is reported for reference ONLY: no legacy branch reads any of "
	+ "these fields, so no rule may be derived from it (design D2)")

## The five committed fields in this project already recorded as having no
## legacy consumer, and `velocity` is the sixth. The precedent is what makes
## this refusal a rule rather than a preference: recording the field and
## refusing to invent a rule from it has now been done five times.
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
]

## The committed content package this capability reads its footprint and
## velocity values out of. Named so a reader knows where a reported number came
## from, and so the manifest digests remain the gate on it.
const UNITS_FILE := "packages/game-content/normalized/units.json"
const BUILDINGS_FILE := "packages/game-content/normalized/buildings.json"

# ---------------------------------------------------------------------------
# The movement-command inventory (design D3)
# ---------------------------------------------------------------------------

## The four legacy commands this inventory records: the three that write a
## row's placement and the adjacent time command that makes the row's instant
## client-writable. Every entry states what the command **checks** and what it
## does **not**, because the second half is the whole finding. Nothing here is
## implemented.
const MOVEMENT_COMMANDS := [
	{
		"command": "move",
		"site": "command.py:119-134",
		"kind": "coordinate-writer",
		"writes": "row slot 1 (x) and row slot 2 (y), from client arguments, "
			+ "verbatim and with no transformation",
		"checks": "that the addressed row exists: map_get_item returns a falsy "
			+ "row and the branch prints 'Error: item not found.' and returns "
			+ "(command.py:127-129)",
		"does_not_check": [
			"the addressed row's committed item type - the row may be a unit, a "
				+ "building, or anything else, and the branch never reads the type",
			"occupancy: no other row's cells are examined, so a move may land on "
				+ "an occupied cell",
			"bounds: no grid, map size, or cell range is consulted, so a move may "
				+ "land outside any grid",
			"terrain: no tile, elevation, or footprint is consulted",
			"speed or duration: no velocity, no distance, and no elapsed time is "
				+ "read, so a move consumes no time and travels no speed",
			"cost: no price, resource, or ownership check of any kind",
		],
		"type_agnostic": true,
		"already_delivered_as": "godot-building-move",
		"arguments": [
			"args[0] item_index - the addressed row's map key",
			"args[1] x - written to slot 1",
			"args[2] y - written to slot 2",
			"args[3] frame - READ AND UNUSED (command.py:123)",
			"args[4] string - READ AND UNUSED (command.py:124)",
		],
		"unused_arguments": ["frame (args[3])", "string (args[4])"],
		"implemented_here": false,
		"note": "this is the ONLY branch in the committed source that moves an "
			+ "existing row between cells, and it is a map write plus a print. It "
			+ "already ships as M7's godot-building-move, which recorded the two "
			+ "unused arguments and the client-side-only occupancy and bounds "
			+ "rules. This line references that capability and reimplements "
			+ "nothing",
	},
	{
		"command": "orient",
		"site": "command.py:198-207",
		"kind": "orientation-writer",
		"writes": "row slot 4 (orientation), as int(orientation) - the ONE "
			+ "coercion anywhere in the movement surface, and it is the legacy's",
		"checks": "that the addressed row exists: map_get_item returns a falsy "
			+ "row and the branch prints 'Error: item not found.' and returns "
			+ "(command.py:203-205)",
		"does_not_check": [
			"that the value is a valid orientation: any client value that int() "
				+ "accepts is written, so an unaddressable orientation is stored",
			"a range, an angle, or a snap: no rotation rule of any kind is applied",
			"terrain, occupancy, or bounds",
			"cost, ownership, or elapsed time",
		],
		"type_agnostic": true,
		"already_delivered_as": "",
		"arguments": [
			"args[0] item_index - the addressed row's map key",
			"args[1] orientation - written to slot 4 through int()",
		],
		"unused_arguments": [],
		"implemented_here": false,
		"note": "a PLAIN client-supplied slot write: the only writer of slot 4 in "
			+ "the whole committed source. This projection therefore reports the "
			+ "orientation verbatim and applies no rotation, facing, or turning "
			+ "rule to it",
	},
	{
		"command": "pop_unit",
		"site": "command.py:383-408, with engine.pop_unit at engine.py:58-68 "
			+ "and engine.map_add_item_from_item at engine.py:33-34",
		"kind": "coordinate-writer",
		"writes": "row slot 0 (item), slot 1 (x), slot 2 (y), and slot 7 "
			+ "(player team), then re-inserts the row under the client-sent map "
			+ "key index_unit - the ONLY other command that writes coordinates, "
			+ "and it OVERWRITES the popped row's committed item with the client's",
		"checks": "that the addressed building row exists (command.py:392-395) "
			+ "and that a garrison row matching the client item id is present "
			+ "(engine.py:58-68), printing and returning when either is absent",
		"does_not_check": [
			"that the client item id matches the row it pops: engine.pop_unit "
				+ "matches on that same client id, and command.py:403 then writes "
				+ "it back, so the check is self-confirming and the popped row's "
				+ "own committed item is lost",
			"that the popped row is a unit, that the placed row is free, that the "
				+ "cell is within bounds, or that the terrain admits it",
			"speed, duration, path, or cost",
		],
		"type_agnostic": false,
		"already_delivered_as": "",
		"arguments": [
			"args[0] index_building - the garrison host row's map key",
			"args[1] index_unit - the map key the popped row is re-inserted "
				+ "under (command.py:408, via engine.py:33-34), so it is READ, "
				+ "not unused",
			"args[2] item_id - the garrison match AND the written slot 0",
			"args[3] x - written to slot 1",
			"args[4] y - written to slot 2",
			"args[5] playerID - the written slot 7 (team)",
			"args[6] unknown - UNUSED",
		],
		"unused_arguments": ["unknown (args[6])"],
		"implemented_here": false,
		"note": "a row LEAVING a garrison is placed on the map at client-supplied "
			+ "coordinates with its item overwritten. It is recorded here so the "
			+ "inventory of coordinate writers is complete and so its item "
			+ "overwrite stays visible; this line implements no part of it",
	},
	{
		"command": "fast_forward",
		"site": "command.py:905-946",
		"kind": "time-writer",
		"writes": "EVERY row's slot-3 instant (command.py:934) and every row's "
			+ "attr['ts'] queue start instant (command.py:939), both backwards "
			+ "by a CLIENT-SUPPLIED number of seconds",
		"checks": "nothing: the branch performs no validation of any kind",
		"does_not_check": [
			"that the requested shift is sane, bounded, or authorised: any "
				+ "client value is applied",
			"the sign: a negative seconds shifts every instant FORWARD as "
				+ "symmetrically as a positive one shifts it back",
			"whether any row's shifted instant is meaningful, because nothing "
				+ "evaluates one",
		],
		"type_agnostic": true,
		"already_delivered_as": "",
		"arguments": [
			"args[0] seconds - the CLIENT-SUPPLIED shift applied to every row's "
				+ "instant and queue start instant",
		],
		"unused_arguments": [],
		"implemented_here": false,
		"note": "it has NO observable effect, and that is the finding rather than "
			+ "a defect: because no legacy branch evaluates a row's elapsed time, "
			+ "shifting the instant changes no outcome. It is recorded because it "
			+ "is the CLIENT-WRITABLE INSTANT a client-side readiness check would "
			+ "trust - precisely the invented rule the delivered "
			+ "godot-unit-production capability refuses. Beyond the rows it also "
			+ "shifts the map's four timestamps, the private-state timestamps, "
			+ "every research timer, and every quest time",
	},
]

## The closed count of the inventory, and the count that carries the finding.
const COMMAND_COUNT := 4
## The commands whose kind is `coordinate-writer`, by name: exactly two, and
## that is the whole set of committed coordinate writes.
const COORDINATE_WRITERS := ["move", "pop_unit"]
const COORDINATE_WRITER_COUNT := 2

## The measured number of **assignments** to a row's slots 0, 1, or 2 across the
## seven legacy root modules, and the lines they sit on. It is **five**, not six:
## see `INVESTIGATION_CORRECTIONS` below.
const SLOT_0_2_WRITE_COUNT := 5
const SLOT_0_2_WRITE_LINES := ["command.py:132", "command.py:133",
	"command.py:403", "command.py:404", "command.py:405"]

## The dispatcher's whole named-branch count, so a reader can see that the four
## recorded commands are four of a closed set of 63 and that no fifth
## movement-named branch is hiding in the remaining 59.
const NAMED_BRANCH_COUNT := 63

## The one movement-named dispatcher branch in the whole committed source. The
## suite re-derives the named-branch set and matches this against every name
## carrying a movement, orientation, route, or path stem.
const MOVEMENT_NAMED_BRANCHES := ["move", "orient"]

## The finding the inventory exists to make checkable, and which is why the
## deliverable is a projection rather than a mechanism.
const NO_UNIT_SPECIFIC_COMMAND := ("NO UNIT-SPECIFIC MOVEMENT COMMAND EXISTS IN "
	+ "THE LEGACY SOURCE, AND NONE IS INVENTED HERE. Across command.py, "
	+ "engine.py, sessions.py, server.py, constants.py, get_game_config.py, and "
	+ "version.py there are exactly FIVE assignments to a row's slots 0, 1, or 2 "
	+ "- command.py:132 and 133 (move) and command.py:403, 404, and 405 "
	+ "(pop_unit) - and therefore exactly TWO branches that write coordinates, "
	+ "both inventoried above. Of the dispatcher's 63 named branches, only move "
	+ "and orient carry a movement or orientation name. move is TYPE-AGNOSTIC, "
	+ "checks nothing beyond the row's existence, and ALREADY SHIPS as "
	+ "godot-building-move, so this capability adds NO new server behaviour and "
	+ "reimplements nothing; pop_unit writes coordinates only when a row leaves a "
	+ "garrison and overwrites the item it pops. There is no move_unit, no "
	+ "step, no path, no arrive, and no movement command of any other kind "
	+ "(design D3/D6)")

## The two measured figures the committed investigation record got wrong or
## under-specified, recorded here with the rejected alternative retained rather
## than silently corrected. The suite re-measures both, so a future edit of
## either claim fails the run instead of drifting.
const INVESTIGATION_CORRECTIONS := [
	{
		"figure": "the number of writes to a row's slots 0-2 across the seven "
			+ "legacy modules",
		"investigation_states": 6,
		"measured": SLOT_0_2_WRITE_COUNT,
		"lines_measured": SLOT_0_2_WRITE_LINES,
		"why": "the investigation's third table row cites engine.py:62 as "
			+ "'item[0] = ...', but that line is `if item[0] == item_id:` - a "
			+ "COMPARISON inside engine.pop_unit's garrison scan, not an "
			+ "assignment. Measured over the same seven modules with an "
			+ "assignment pattern that excludes '==', the count is FIVE",
		"what_is_unaffected": "the investigation's actual conclusion is "
			+ "CORRECT and independently re-measured: exactly TWO branches write "
			+ "coordinates (move and pop_unit), and orient is the only writer of "
			+ "slot 4",
	},
	{
		"figure": "the committed units carrying the properties flag ft_flying",
		"investigation_states": 135,
		"measured": 137,
		"measured_values": {"0": 2, "1": 135},
		"measured_value_type": "string: the normalized package carries the flag "
			+ "as the string '1' or the string '0', never as a boolean",
		"lines_measured": [],
		"why": "measured from the verified registry's units domain, the key is "
			+ "PRESENT on 137 of the 429 committed units, and its committed value "
			+ "reads '1' on 135 of them and '0' on 2 (id 1357, Bonecrusha' Drone). "
			+ "So the investigation's 135 is the count of units whose flag reads "
			+ "'1' and two further units carry the key as '0'; an earlier draft of "
			+ "this record wrongly reported 137 as a boolean-true count with no "
			+ "false value present, which measurement contradicts",
		"what_is_unaffected": "ft_flying is one of the four sibling "
			+ "zero-consumer fields recorded for reference, not one of the four "
			+ "fields this capability reports as content, and its zero-consumer "
			+ "status is unaffected: the string occurs in none of the seven "
			+ "legacy modules",
	},
]

# ---------------------------------------------------------------------------
# The client-writable instant (design D4)
# ---------------------------------------------------------------------------

## The whole client-writable instant finding, as the evidence report records it.
## Read from this module's own constant so the report cannot describe a contract
## the code does not hold.
const INSTANT_RECORD := {
	"command": "fast_forward",
	"site": "command.py:905-946",
	"seconds_source": "client args[0], with no validation of any kind",
	"row_instant_write": "command.py:934 - data[3] = max(0, data[3] - seconds) "
		+ "for EVERY row in map['items']",
	"queue_start_instant_write": "command.py:939 - data[6]['ts'] = max(0, "
		+ "data[6]['ts'] - seconds) for every row whose bag carries 'ts'",
	"clamp": "max(0, ...) on both, so a shifted instant can never go negative "
		+ "and a large enough shift simply reads as zero",
	"other_instants_shifted": [
		"map['timestamp'] (910)",
		"map['timestampLastChapter'] (911)",
		"map['timestampLastTreasure'] (912)",
		"map['timestampLastTrade'] (913)",
		"privateState['timestampLastBonus'] (914)",
		"privateState['timestampLastAllianceBonus'] (916)",
		"privateState['timeStampDartsNewFree'] (918)",
		"privateState['tsAttacksReset'] (919)",
		"privateState['tsSpyingsReset'] (920)",
		"every research timer in privateState['timeStampDoResearch'] (926-928)",
		"every quest time in map['questTimes'] (943-944)",
	],
	"client_writable": true,
	"observable_effect": "NONE, and that is the finding: because no legacy "
		+ "branch evaluates a row's elapsed time, shifting the instant changes no "
		+ "outcome. It is recorded because it is the input a client-side "
		+ "readiness check would trust",
	"treated_as": "an opaque recorded value",
	"derived_from_it": false,
	"rule": "THE ROW INSTANT IS CLIENT-WRITABLE, SO NO READINESS IS DERIVED "
		+ "FROM IT. fast_forward subtracts a client-supplied number of seconds "
		+ "from every row's recorded instant AND from every row's queue start "
		+ "instant, which means a client can rewrite both. The placement "
		+ "projection therefore reports the instant verbatim as an OPAQUE "
		+ "RECORDED VALUE and computes no elapsed time, no remaining time, and "
		+ "no readiness from it, consistent with the delivered "
		+ "godot-unit-queues and godot-unit-production refusals (design D4)",
}

## The two constant answers the projection can give about a row's instant, and
## no third. A boolean here would be a rule the legacy server cannot supply.
const INSTANT_TREATMENT := "opaque-recorded-value"

# ---------------------------------------------------------------------------
# The tile-geometry gap (the recorded M6 evidence gap)
# ---------------------------------------------------------------------------

## Recorded rather than filled. Nothing here implements terrain or an elevation
## interaction, and the committed absence of a tile geometry is stated instead
## of replaced with an assumed one.
const TILE_GEOMETRY_GAP := ("THE LEGACY TILE GEOMETRY WAS NEVER EXTRACTED, AND IT "
	+ "STAYS A GAP. The delivered M6 town work recorded that the legacy SWF's "
	+ "TILE_SIZE, EI_TILE_HEIGHT_PIXELS, and grid dimensions were never "
	+ "extracted from the Flash client, so pixel parity with it is not claimed. "
	+ "Because `elevation` is read by no legacy branch AND the tile geometry is "
	+ "unrecorded, NO terrain-aware movement could be derived from either source "
	+ "even if a rule were invented: this line implements none and fills the gap "
	+ "with no assumed geometry (design D2)")

# ---------------------------------------------------------------------------
# Movement is content, not a server operation (design D5)
# ---------------------------------------------------------------------------

## Declared false, and stated as the contract it is.
const MOVEMENT_IMPLEMENTED := false
const MOVEMENT_OPERATION_NOTE := ("UNIT MOVEMENT IS CONTENT, NOT A SERVER "
	+ "OPERATION. The placement, the committed footprint, and the committed "
	+ "velocity are all read from the committed content package and the committed "
	+ "row already in hand, so there is no intent to send, no route to add, and "
	+ "nothing to authorise: NO compatibility API endpoint is added, NO client "
	+ "intent is issued, and NO persistence behaviour changes, which is why the "
	+ "compatibility test suite stays green UNCHANGED. The only legacy command "
	+ "that moves a row is already delivered by godot-building-move and is "
	+ "referenced here, never reimplemented (design D5/D6)")

## Whether a unit is placed or moved by this line. False, twice over: nothing is
## placed (a placement is the M7 building-placement line's work, and a unit
## placement is still undelivered), and nothing is moved.
const UNIT_PLACED := false
const UNIT_MOVED := false

## Why no executed-legacy fixture was captured — the stronger of the two
## available reasons, stated so it cannot be read as a corpus limitation.
const FIXTURE_NOT_CAPTURED := ("NO EXECUTED-LEGACY MOVEMENT FIXTURE WAS CAPTURED, "
	+ "AND THE REASON IS THE STRONGER ONE: there is NO unit-specific movement "
	+ "behaviour TO CAPTURE, not merely a corpus that could not exercise it. "
	+ "There is no movement rule, no movement command, and no unit row in the "
	+ "committed corpus (40 rows across 11 distinct ids, every one of committed "
	+ "type 'b'), so a fixture here would have to fabricate the state it claims "
	+ "to observe. The move command that DOES exist is already delivered, with "
	+ "its own executed-legacy fixture under tests/fixtures/godot-building-move/ "
	+ "and its own windowed capture and report under "
	+ "apps/client-godot/evidence/building-move/ - and that command's fixture is "
	+ "about a BUILDING row being rewritten, which is the same type-agnostic "
	+ "write a unit row would receive, not movement")

# ---------------------------------------------------------------------------
# The helpers this module deliberately does NOT provide (design D4)
# ---------------------------------------------------------------------------

## The machine-readable form of the absence. Each of these would compute a rule
## the legacy server never had, so none is declared here, and the suite asserts
## this module's whole function inventory against a pinned list AND against this
## list by name — a rename cannot smuggle one past the inventory, and a leftover
## declared here fails visibly.
const ABSENT_HELPERS := [
	{"helper": "travel_time", "absent_because":
		"the committed velocity has zero legacy consumers, so a duration "
		+ "derived from it would invent the rule this line records as absent"},
	{"helper": "speed", "absent_because":
		"no legacy branch reads velocity at all, so there is no committed speed "
		+ "for anything to report as one"},
	{"helper": "distance", "absent_because":
		"no legacy branch computes a distance and the tile geometry was never "
		+ "extracted, so there is no committed distance function to reproduce"},
	{"helper": "path", "absent_because":
		"move writes a destination in a single assignment; no legacy branch "
		+ "plans, stores, or follows a route"},
	{"helper": "find_path", "absent_because":
		"the same absence: there is no committed search to reproduce, and the "
		+ "grid a path would search is the unrecorded tile geometry"},
	{"helper": "terrain_at", "absent_because":
		"the legacy SWF's tile geometry was never extracted, so no terrain "
		+ "lookup is possible from committed evidence"},
	{"helper": "elevation_offset", "absent_because":
		"elevation is read by no legacy branch, so no position may be computed "
		+ "from it, and no committed projection exists to copy"},
	{"helper": "footprint_cells", "absent_because":
		"footprint GEOMETRY belongs to the delivered town placement and move "
		+ "flows, which own it for every item; this module reports the "
		+ "committed numbers verbatim and computes no cell from them, which the "
		+ "measured uniform 1x1 unit footprint makes unnecessary anyway"},
	{"helper": "is_occupied", "absent_because":
		"move performs no occupancy check, and the delivered building-move flow "
		+ "records its occupancy rule as CLIENT-SIDE ONLY with no "
		+ "server-authoritative validation behind it"},
	{"helper": "in_bounds", "absent_because":
		"move performs no bounds check and consults no grid size; the delivered "
		+ "building-move flow's 0..99 grid is a client-side convention of that "
		+ "surface, not a committed legacy rule"},
	{"helper": "is_arrived", "absent_because":
		"nothing in the legacy source can answer whether a row has arrived: no "
		+ "command completes a journey and nothing evaluates elapsed time"},
	{"helper": "is_ready", "absent_because":
		"the row instant is client-writable through fast_forward, so a readiness "
		+ "answer computed here would trust a value the client can rewrite"},
	{"helper": "elapsed", "absent_because":
		"no legacy branch evaluates elapsed time; every occurrence of a row "
		+ "instant is a write or a deletion, and the one reader is the "
		+ "soul-mixer speedup, which is not a movement path"},
	{"helper": "interpolate", "absent_because":
		"no legacy branch computes an intermediate position, and the only two "
		+ "instants this projection could interpolate between are both "
		+ "client-writable through fast_forward"},
	{"helper": "position_at", "absent_because":
		"the same absence as interpolate, stated as a reader: asking this "
		+ "projection for a position at a moment would be asking for a rule the "
		+ "legacy server never had"},
	{"helper": "rotate_to", "absent_because":
		"orient is a plain client-supplied slot write with no rotation rule, so "
		+ "no facing, turning, or shortest-arc computation may be added here"},
	{"helper": "animate_move", "absent_because":
		"animation is a separate later line, and the M4 converted unit package "
		+ "establishes asset and timeline LINKAGE only, never playback "
		+ "correctness or gameplay behaviour"},
	{"helper": "apply_velocity", "absent_because":
		"the committed velocity is content only: reporting it is the whole "
		+ "contract, and applying it would be the invented rule the zero-"
		+ "consumer measurement exists to prevent"},
]

# ---------------------------------------------------------------------------
# The evidence's non-claims
# ---------------------------------------------------------------------------

## Every non-claim the delta's evidence requirement names. The runtime tokens in
## the first claim are assembled from fragments for the same project-scope
## reason as in `production_flow.gd` and `unit_queue.gd`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO VELOCITY-BASED TRAVEL TIME, PATH, TERRAIN OR ELEVATION INTERACTION, "
		+ "OCCUPANCY, BOUNDS, READINESS, OR INTERPOLATION IS IMPLEMENTED: each is "
		+ "a recorded refusal with its reason attached, not an omission",
	"THE COMMITTED MOVEMENT FIELDS ARE READ BY NO LEGACY BRANCH and are "
		+ "reported as CONTENT ONLY: velocity, width, height, and elevation each "
		+ "have zero occurrences across the seven legacy modules",
	"NO UNIT-SPECIFIC MOVEMENT COMMAND EXISTS IN THE LEGACY SOURCE AND NONE WAS "
		+ "INVENTED: exactly two branches write coordinates and the one that "
		+ "moves an existing row is type-agnostic, already delivered, and checks "
		+ "nothing",
	"NO UNIT IS PLACED OR MOVED, and the committed corpus holds NO unit row: "
		+ "40 rows across 11 distinct ids, every one of committed type 'b'",
	"NO EXECUTED-LEGACY FIXTURE WAS CAPTURED, and the reason is the absence of "
		+ "behaviour rather than only the corpus's missing unit row; the move "
		+ "command that does exist is already delivered with its own fixture",
	"NO ANIMATION IS IMPLEMENTED: the converted unit package establishes asset "
		+ "and timeline linkage only, never playback correctness",
	"NO PIXEL PARITY IS CLAIMED and the legacy tile geometry remains a recorded "
		+ "gap, never an assumed one",
	"no windowed capture is claimed: nothing is rendered and no unit exists to "
		+ "render",
	"NO ENDPOINT AND NO CLIENT INTENT: unit movement is committed content read "
		+ "through the content registry, so the compatibility suite stays green "
		+ "unchanged",
	"godot-building-move is REFERENCED, never reimplemented: this line adds the "
		+ "unit placement VIEW and the recorded facts about the command, and "
		+ "touches no endpoint, flow, or evidence of that line",
	"a reader who wanted a travel-time or terrain rule out of the reported "
		+ "content must bring evidence the legacy contract does not contain",
]

## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and check,
## and every derived fact states what it is derived from. Nothing here names a
## runtime; the runtime names live in `NON_CLAIMS`.
const PROVENANCE := {
	"established": [
		{"fact": "move rewrites a row's slots 1 and 2 from client arguments and "
			+ "performs no type, occupancy, bounds, terrain, or speed check; its "
			+ "args[3] frame and args[4] string are read and unused",
			"evidence": "command.py:119-134, the whole branch; the suite "
				+ "re-derives the branch name, its five argument reads, its two "
				+ "assignments, and the two unused arguments out of the committed "
				+ "dispatcher"},
		{"fact": "exactly FIVE assignments to a row's slots 0-2 exist across the "
			+ "seven legacy root modules, and therefore exactly TWO branches "
			+ "write coordinates: move, and pop_unit",
			"evidence": "command.py:132, 133, 403, 404, 405, measured with an "
				+ "assignment pattern that excludes '==' over command.py, "
				+ "engine.py, sessions.py, server.py, constants.py, "
				+ "get_game_config.py, and version.py"},
		{"fact": "pop_unit overwrites the popped row's committed item with the "
			+ "client-sent id, so its garrison match check is self-confirming",
			"evidence": "command.py:397-405 against engine.py:58-68, where the "
				+ "popped row is matched on the same client id that is then "
				+ "written back into its slot 0"},
		{"fact": "orient is a plain client-supplied slot-4 write and the only "
			+ "writer of slot 4 in the committed source",
			"evidence": "command.py:198-207, and a measurement of every "
				+ "assignment to slot 4 across the seven modules"},
		{"fact": "fast_forward subtracts a client-supplied seconds from every "
			+ "row's slot-3 instant and every row's attr['ts'], and validates "
			+ "nothing",
			"evidence": "command.py:905-946, in particular 934 and 939"},
		{"fact": "velocity, width, height, elevation, max_elem_vol, "
			+ "attack_range, ft_flying, and ft_ground each have ZERO occurrences "
			+ "across the seven legacy root modules",
			"evidence": "a substring search per field over command.py, engine.py, "
				+ "sessions.py, server.py, constants.py, get_game_config.py, and "
				+ "version.py, which the suite repeats for all eight fields"},
		{"fact": "velocity is positive on all 429 committed units and on 145 of "
			+ "the 470 committed buildings, taking exactly three building values",
			"evidence": "the committed normalized content package, measured by "
				+ "the suite through the verified registry"},
		{"fact": "the committed unit footprint is uniform: width, height, and "
			+ "elevation are positive on all 429 units and the trio takes the "
			+ "single value 1 on every one of them",
			"evidence": "the same measured content package; a footprint needing "
				+ "no geometry is a measurement, not an assumption"},
		{"fact": "the dispatcher has 63 named branches, and only move and orient "
			+ "carry a movement or orientation name",
			"evidence": "command.py's own if/elif chain, measured by the suite, "
				+ "which compares the measured names against "
				+ "MOVEMENT_NAMED_BRANCHES"},
		{"fact": "the committed corpus places 40 rows across 11 distinct item "
			+ "ids, all of committed type 'b', with an empty storage, an empty "
			+ "inventory, and 40 empty attribute bags",
			"evidence": "tests/saves/fresh-player.json, measured by the suite"},
		{"fact": "the legacy SWF's tile geometry was never extracted, so pixel "
			+ "parity with the Flash client is not claimed",
			"evidence": "the recorded M6 town-vertical-slice evidence gap, "
				+ "restated here and implemented not at all"},
	],
	"derived": [
		{"fact": "the line's deliverable is a placement projection plus an "
			+ "auditable refusal rather than a movement mechanism",
			"evidence": "derived (design D1): with no movement rule, no "
				+ "movement-named command, and no unit row in the corpus, any "
				+ "mechanism would be invented, while a velocity positive on "
				+ "every unit definition is the specific trap this record closes"},
		{"fact": "the movement-command inventory belongs to this line rather "
			+ "than to a later animation line",
			"evidence": "derived (design D3): the classification is what makes "
				+ "the absence auditable rather than asserted, so it had to "
				+ "arrive with the refusal it supports. Its scope is closed over "
				+ "the committed legacy source, and a later line extends it "
				+ "explicitly"},
		{"fact": "no endpoint is warranted while no server-derived movement "
			+ "exists",
			"evidence": "derived (design D5): there is no intent to send and "
				+ "nothing to authorise, so the compatibility test suite stays "
				+ "green unchanged, exactly as M8 lines 1, 2, and 4 concluded"},
		{"fact": "the placement projection is type-agnostic",
			"evidence": "derived from an ESTABLISHED fact: move - the only "
				+ "command that moves an existing row - never reads the "
				+ "addressed row's committed type, so a type gate here would be "
				+ "a rule the legacy contract does not have. The delivered USE "
				+ "is the unit row; the projection itself refuses nothing about "
				+ "a row's type"},
		{"fact": "the placement view reads its slot indices from the instance "
			+ "model rather than re-deriving the row shape",
			"evidence": "derived (D6 and the godot-unit-instances delta): the "
				+ "instance capability owns the row and this one owns the "
				+ "placement reading of it, so a shared index is the only way "
				+ "the two cannot drift"},
	],
}


# ---------------------------------------------------------------------------
# The one projection
# ---------------------------------------------------------------------------


## The whole placement evaluation for one row, and the ONLY entry point a
## surface uses. Returns
##   `{ok, reason, error, resolvable, cell_x, cell_y, cell_recorded,
##     cell_x_present, cell_y_present, orientation, orientation_present,
## row_instant, instant_treatment, instant_derived, row_slots,
##     definition_supplied, definition_type, footprint, velocity,
##     movement_fields, travel_time_computed, path_computed,
##     terrain_interaction, occupancy_enforced, bounds_enforced, readiness,
##     readiness_reason, animation_implemented, request_issued, readout}`.
##
## Every committed value is reported **verbatim**. Nothing is computed from
## another value, and the six absence flags are **constant false** carrying the
## recorded reason beside them, so no caller can mistake this projection for a
## movement rule. A row whose committed coordinates cannot be read produces
## `ok: false` with `cell_x` and `cell_y` `null` — never the origin — and the
## untouched recorded slots in `cell_recorded` (design D1/D4).
##
## `definition` is the row's already-resolved committed definition, handed in
## by the caller; this module never resolves content itself, so the
## static/instance boundary stays one-way. A `definition` that is not an object
## is a **named absence** of the four committed movement fields, never a reason
## to refuse a placement.
static func evaluate(row: Variant, definition: Variant = null) -> Dictionary:
	var footprint: Dictionary = committed_footprint(definition)
	var supplied := definition is Dictionary
	var velocity: Variant = committed_velocity(definition)
	var header := {
		"row_slots": ROW_SLOTS,
		"definition_supplied": supplied,
		"definition_type": str((definition as Dictionary).get("type", ""))
			if supplied else "",
		"footprint": footprint,
		"velocity": velocity,
		"movement_fields": (MOVEMENT_FIELDS as Array).duplicate(),
	}
	if not (row is Array):
		return _reject(REASON_INVALID_ROW,
			"the addressed row is %s, not a committed map row"
				% _type_name(row), header, [null, null])
	var cells: Array = row as Array
	if cells.size() != ROW_SLOTS:
		return _reject(REASON_INVALID_ROW,
			"the addressed row has %d slots, not the committed %d"
				% [cells.size(), ROW_SLOTS], header,
			[cells[SLOT_CELL_X] if cells.size() > SLOT_CELL_X else null,
				cells[SLOT_CELL_Y] if cells.size() > SLOT_CELL_Y else null])
	var cell_x: Variant = _integer(cells[SLOT_CELL_X])
	var cell_y: Variant = _integer(cells[SLOT_CELL_Y])
	if cell_x == null or cell_y == null:
		# Fail closed: the recorded slots travel UNTOUCHED beside the refusal,
		# so a caller can never read a defaulted origin as a resolved cell.
		var refused := _reject(REASON_UNRESOLVABLE_CELL,
			"the addressed row's committed coordinates are not readable "
			+ "(slot 1 is %s, slot 2 is %s)"
			% [_type_name(cells[SLOT_CELL_X]),
				_type_name(cells[SLOT_CELL_Y])],
			header, [cells[SLOT_CELL_X], cells[SLOT_CELL_Y]])
		refused["row_instant"] = _opaque_instant(cells)
		refused["orientation"] = _orientation_or_null(cells)
		refused["orientation_present"] = refused["orientation"] != null
		return refused
	var orientation: Variant = _orientation_or_null(cells)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"resolvable": true,
		"cell_x": cell_x,
		"cell_y": cell_y,
		"cell_recorded": [cells[SLOT_CELL_X], cells[SLOT_CELL_Y]],
		"cell_x_present": true,
		"cell_y_present": true,
		"orientation": orientation,
		"orientation_present": orientation != null,
		"row_instant": _opaque_instant(cells),
		"instant_treatment": INSTANT_TREATMENT,
		"instant_derived": false,
		"row_slots": cells.size(),
		"definition_supplied": supplied,
		"definition_type": str((definition as Dictionary).get("type", ""))
			if supplied else "",
		"footprint": footprint,
		"velocity": velocity,
		"movement_fields": (MOVEMENT_FIELDS as Array).duplicate(),
		"travel_time_computed": false,
		"path_computed": false,
		"terrain_interaction": false,
		"occupancy_enforced": false,
		"bounds_enforced": false,
		"readiness": READINESS_UNKNOWN,
		"readiness_reason": CANNOT_SAY_MOVED,
		"animation_implemented": false,
		"request_issued": false,
		"cell_refusal": CELL_REFUSAL,
		"no_derivation": NO_DERIVATION,
		"readout": readout_text({
			"ok": true,
			"resolvable": true,
			"cell_x": cell_x,
			"cell_y": cell_y,
			"orientation": orientation,
			"orientation_present": orientation != null,
			"row_instant": _opaque_instant(cells),
			"footprint": footprint,
			"velocity": velocity,
			"readiness": READINESS_UNKNOWN,
			"readiness_reason": CANNOT_SAY_MOVED,
		}),
	}

## The single sentence a reader is owed the moment they ask whether this row
## has moved or arrived. There is deliberately no second value: a boolean here
## would be a rule the legacy server cannot supply.
const READINESS_UNKNOWN := "unknown-and-uncomputable"
const CANNOT_SAY_MOVED := ("the legacy server CANNOT SAY whether a row has moved, "
	+ "arrived, or how long a move would take: no command completes a journey, "
	+ "no branch reads velocity, and the row's instant is client-writable "
	+ "through fast_forward")

## Every field the placement reports, with its own source and the commitment
## that it is verbatim, as a fresh deep copy a caller may keep and mutate.
static func placement_field_inventory() -> Array:
	return (PLACEMENT_FIELDS as Array).duplicate(true)

## The reported field names in committed table order.
static func placement_field_names() -> Array:
	var out: Array = []
	for entry: Dictionary in PLACEMENT_FIELDS:
		out.append(str(entry["name"]))
	return out


# ---------------------------------------------------------------------------
# The committed movement fields as content (design D2)
# ---------------------------------------------------------------------------


## One committed definition's committed `velocity`, **verbatim, as content**.
## Returns the value exactly as the committed entry holds it, or `null` when the
## entry carries no such field — a named absence, never a substituted zero. It
## reads that one field and nothing else, and it computes no travel time, no
## speed, and no duration from what it returns: the refusal is the function's
## whole contract.
static func committed_velocity(entry: Variant) -> Variant:
	if not (entry is Dictionary):
		return null
	if not (entry as Dictionary).has(VELOCITY_FIELD):
		return null
	return (entry as Dictionary)[VELOCITY_FIELD]


## One committed definition's committed footprint, **verbatim, as content**.
## Returns
##   `{ok, reason, error, width, height, elevation, present, absent}`
##
## Each of the three values is the committed number exactly as the entry holds
## it, with `present` and `absent` naming which keys the entry actually carries —
## so a definition missing a key is distinguishable from one committing a zero.
## No cell, rectangle, offset, or position is computed from any of them: the
## footprint **geometry** belongs to the delivered town placement and move flows.
static func committed_footprint(entry: Variant) -> Dictionary:
	if not (entry is Dictionary):
		return {
			"ok": false,
			"reason": REASON_INVALID_DEFINITION,
			"error": "the committed definition is %s, not an object, so all four "
				% _type_name(entry)
				+ "committed movement fields are ABSENT from it (a named absence, "
				+ "never a committed zero) and none is substituted",
			"width": null,
			"height": null,
			"elevation": null,
			"present": [],
			"absent": (FOOTPRINT_FIELDS as Array).duplicate(),
		}
	var present: Array = []
	var absent: Array = []
	var out := {
		"ok": true,
		"reason": "",
		"error": "",
		"width": null,
		"height": null,
		"elevation": null,
		"present": present,
		"absent": absent,
	}
	for field: String in FOOTPRINT_FIELDS:
		if (entry as Dictionary).has(field):
			present.append(field)
			out[field] = (entry as Dictionary)[field]
		else:
			absent.append(field)
	return out


## How the readout renders one committed movement field: the value, immediately
## followed by the refusal, so a reader who sees the number cannot mistake it
## for a rule this client would honour.
static func movement_field_note(field: String, value: Variant) -> String:
	if not MOVEMENT_FIELDS.has(field):
		return ""
	if value == null:
		return ("%s: absent from this definition (a named absence, never a "
			% field
			+ "zero) and read by no legacy branch either")
	return ("%s: %s — recorded as CONTENT ONLY, never used as a speed, a "
			% [field, str(value)]
			+ "duration, or a position, because no legacy branch reads it")


## The whole content-only refusal as the evidence report records it, read from
## this module's own constants so the report cannot describe a contract the code
## does not hold. `distribution_measured` is filled in by the suite from the
## verified registry in the same run.
static func movement_fields_record() -> Dictionary:
	return {
		"fields": (MOVEMENT_FIELDS as Array).duplicate(),
		"footprint_fields": (FOOTPRINT_FIELDS as Array).duplicate(),
		"reported_as_content_only": true,
		"used_as_a_rule": false,
		"consumer_count": MOVEMENT_FIELD_CONSUMER_COUNT,
		"consumer_count_per_field": _consumer_counts(),
		"searched_modules": (SEARCHED_MODULES as Array).duplicate(),
		"rule": MOVEMENT_FIELDS_REFUSAL,
		"coverage": MOVEMENT_FIELDS_COVERAGE,
		"zero_consumer_precedents": (ZERO_CONSUMER_PRECEDENTS as Array)
			.duplicate(true),
		"sibling_zero_consumer_fields": (SIBLING_ZERO_CONSUMER_FIELDS as Array)
			.duplicate(),
		"units_file": UNITS_FILE,
		"buildings_file": BUILDINGS_FILE,
		"travel_time_computed": false,
		"path_computed": false,
		"terrain_interaction": false,
		"elevation_interaction": false,
		"occupancy_enforced": false,
		"bounds_enforced": false,
		"tile_geometry_gap": TILE_GEOMETRY_GAP,
		"distribution_measured": {
			"units": {},
			"buildings": {},
			"sibling_fields": {},
		},
	}


# ---------------------------------------------------------------------------
# The movement-command inventory (design D3)
# ---------------------------------------------------------------------------


## Every inventoried legacy command with what it checks and what it does not,
## as a fresh deep copy a caller may keep and mutate — so a report reads this
## module's own table rather than restating it.
static func movement_commands() -> Array:
	return (MOVEMENT_COMMANDS as Array).duplicate(true)


## The inventoried command names in committed line order.
static func movement_command_names() -> Array:
	var out: Array = []
	for entry: Dictionary in MOVEMENT_COMMANDS:
		out.append(str(entry["command"]))
	return out


## The commands whose kind is `coordinate-writer`, by name — the complete set of
## committed writes to a row's slots 1 and 2. Exactly two, and the answer is the
## inventory's whole point.
static func coordinate_writers() -> Array:
	var out: Array = []
	for entry: Dictionary in MOVEMENT_COMMANDS:
		if str(entry["kind"]) == "coordinate-writer":
			out.append(str(entry["command"]))
	return out


## The finding the inventory exists to make checkable, verbatim.
static func no_unit_specific_command() -> String:
	return NO_UNIT_SPECIFIC_COMMAND


## The two measured corrections against the committed investigation record, with
## the rejected figure retained beside the measured one.
static func investigation_corrections() -> Array:
	return (INVESTIGATION_CORRECTIONS as Array).duplicate(true)


## The whole movement-contract record as the evidence report writes it: the four
## classified commands, the closed coordinate-writer set, the measured slot-0-2
## writes, the absent-mechanism statement, the absence of a unit-specific
## command, and the two corrections.
static func movement_command_record() -> Dictionary:
	return {
		"implemented": MOVEMENT_IMPLEMENTED,
		"command_count": COMMAND_COUNT,
		"commands": movement_commands(),
		"command_names": movement_command_names(),
		"coordinate_writers": coordinate_writers(),
		"coordinate_writer_count": COORDINATE_WRITER_COUNT,
		"slot_0_2_write_count": SLOT_0_2_WRITE_COUNT,
		"slot_0_2_write_lines": (SLOT_0_2_WRITE_LINES as Array).duplicate(),
		"named_dispatch_branches": NAMED_BRANCH_COUNT,
		"movement_named_branches": (MOVEMENT_NAMED_BRANCHES as Array).duplicate(),
		"type_agnostic": TYPE_AGNOSTIC,
		"type_agnostic_note": TYPE_AGNOSTIC_NOTE,
		"move_already_delivered_as": "godot-building-move",
		"move_reimplemented_here": false,
		"no_unit_specific_command": NO_UNIT_SPECIFIC_COMMAND,
		"corrections": investigation_corrections(),
		"note": MOVEMENT_OPERATION_NOTE,
	}


# ---------------------------------------------------------------------------
# The client-writable instant (design D4)
# ---------------------------------------------------------------------------


## The client-writable instant finding as the evidence report records it, read
## from this module's own constant.
static func instant_record() -> Dictionary:
	return (INSTANT_RECORD as Dictionary).duplicate(true)


# ---------------------------------------------------------------------------
# The no-fixture and no-mechanism records
# ---------------------------------------------------------------------------


## Why no executed-legacy fixture was captured, as the evidence report records
## it — and why the reason is the absence of behaviour rather than only a corpus
## that could not exercise one.
static func fixture_record() -> Dictionary:
	return {
		"captured": false,
		"reason": FIXTURE_NOT_CAPTURED,
		"reason_kind": "no unit-specific movement behaviour to capture, which is "
			+ "stronger than a corpus limitation",
		"corpus_distinction": "the committed corpus also holds no unit row "
			+ "(40 rows, 11 distinct ids, all committed type 'b'), which is a "
			+ "SECOND and independent reason, deliberately kept separate from the "
			+ "first",
		"existing_move_fixture": "the type-agnostic move command's own "
			+ "executed-legacy fixture is already delivered under "
			+ "tests/fixtures/godot-building-move/, with its windowed capture and "
			+ "deterministic report under "
			+ "apps/client-godot/evidence/building-move/ - and it records a "
			+ "BUILDING row's coordinates being rewritten, which is the same "
			+ "write a unit row would receive",
		"fabricated_row": false,
	}


## Why this line is content and not a server operation: no route, no intent, no
## persistence change, and the compatibility suite green unchanged.
static func no_endpoint_record() -> Dictionary:
	return {
		"added": false,
		"movement_implemented": MOVEMENT_IMPLEMENTED,
		"request_issued": false,
		"route": "none: unit movement is committed content read through the "
			+ "content registry plus the committed row already in hand, so there "
			+ "is no intent to send and nothing to authorise",
		"persistence_changed": false,
		"compat_suite": "unchanged: no route, response field, error code, or "
			+ "persistence behaviour is added, so its test count does not move",
		"unit_placed": UNIT_PLACED,
		"unit_moved": UNIT_MOVED,
		"building_move_referenced": "godot-building-move (M7), referenced and "
			+ "not reimplemented",
		"note": MOVEMENT_OPERATION_NOTE,
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The placement readout for one evaluation: the row's own cell and orientation,
## its opaque instant, and then the committed content **with the refusals in the
## same line** — so the absence of a travel time, a path, an occupancy rule, and
## a readiness can never read as a defect. A refused row renders nothing, and an
## absent footprint key renders as `absent`, never as a zero.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var parts: Array = []
	parts.append("cell (%s, %s) — the row's own committed coordinates, verbatim"
		% [_number_text(evaluation.get("cell_x", null)),
			_number_text(evaluation.get("cell_y", null))])
	if bool(evaluation.get("orientation_present", false)):
		parts.append("orientation %s — a plain committed slot-4 value, with no "
			% _number_text(evaluation.get("orientation", null))
			+ "rotation rule applied")
	else:
		parts.append("orientation absent (never defaulted to a committed zero)")
	parts.append("instant %s — an %s: no elapsed, remaining, or readiness is "
		% [_number_text(evaluation.get("row_instant", null)),
			INSTANT_TREATMENT]
		+ "computed from a value fast_forward lets a client rewrite")
	var footprint: Dictionary = evaluation.get("footprint", {}) as Dictionary
	for field: String in FOOTPRINT_FIELDS:
		var value: Variant = footprint.get(field, null)
		var rendered := "absent" if (footprint.get("absent", []) as Array).has(field) \
			else _number_text(value)
		parts.append("%s %s — committed content only, read by no legacy branch"
			% [field, rendered])
	var velocity: Variant = evaluation.get("velocity", null)
	parts.append("velocity %s — CONTENT ONLY on all 429 committed units and read "
		% ("absent" if velocity == null else _number_text(velocity))
		+ "by nothing, so no travel time and no speed is derived from it")
	parts.append("no travel time, no path, no terrain or elevation interaction, "
		+ "no occupancy or bounds rule, no interpolation: the legacy server has "
		+ "none of those rules to reproduce")
	parts.append("moveability: %s — %s" % [str(evaluation.get("readiness",
		READINESS_UNKNOWN)), str(evaluation.get("readiness_reason", ""))])
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural refusal: `ok` false with its named reason, `cell_x` and
## `cell_y` `null` — **never** the origin — the untouched recorded coordinate
## slots in `cell_recorded`, and every absence field still carrying its
## recorded false, so a caller must never be able to read a half-built
## placement or mistake a refusal for a row at (0, 0).
static func _reject(reason: String, message: String, header: Dictionary,
		recorded: Array) -> Dictionary:
	var out := {
		"ok": false,
		"reason": reason,
		"error": "[unit-movement] placement refused: " + message,
		"resolvable": false,
		"cell_x": null,
		"cell_y": null,
		"cell_recorded": recorded.duplicate(),
		"cell_x_present": false,
		"cell_y_present": false,
		"orientation": null,
		"orientation_present": false,
		"row_instant": null,
		"instant_treatment": INSTANT_TREATMENT,
		"instant_derived": false,
		"row_slots": int(header.get("row_slots", 0)),
		"definition_supplied": bool(header.get("definition_supplied", false)),
		"definition_type": str(header.get("definition_type", "")),
		"footprint": header.get("footprint", {}),
		"velocity": header.get("velocity", null),
		"movement_fields": (MOVEMENT_FIELDS as Array).duplicate(),
		"cell_refusal": CELL_REFUSAL,
		"no_derivation": NO_DERIVATION,
		"travel_time_computed": false,
		"path_computed": false,
		"terrain_interaction": false,
		"occupancy_enforced": false,
		"bounds_enforced": false,
		"readiness": READINESS_UNKNOWN,
		"readiness_reason": CANNOT_SAY_MOVED,
		"animation_implemented": false,
		"request_issued": false,
		"readout": "",
	}
	return out


## A row's slot-3 instant as an **opaque recorded value**, or `null` when the
## slot is unreadable. It is never differenced against a clock, never compared
## with a duration, and never turned into a remaining time — the refusal is this
## function's whole contract.
static func _opaque_instant(cells: Array) -> Variant:
	return _integer(cells[SLOT_ROW_INSTANT])


## A row's committed orientation, verbatim, or `null` when the slot carries
## something that is not a committed integer. An unreadable orientation is a
## **named absence**, never a defaulted zero and never the legacy's own
## `int(...)` coercion re-applied here.
static func _orientation_or_null(cells: Array) -> Variant:
	return _integer(cells[SLOT_ORIENTATION])


## The measured consumer count of each recorded field, as one object over the
## closed set the module reports, so a caller reads a per-field figure rather
## than a single number it could apply to the wrong field.
static func _consumer_counts() -> Dictionary:
	var out := {}
	for field: String in MOVEMENT_FIELDS:
		out[field] = MOVEMENT_FIELD_CONSUMER_COUNT
	return out


## A committed integer: an `int` or an integral `float` inside the transported
## exact-integer range. A numeric string fails closed, because coercing `"10"`
## to ten would invent a value the committed row does not carry.
static func _integer(value: Variant) -> Variant:
	if value is int:
		return int(value)
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number) \
				and absf(number) <= MAX_INTEGER:
			return int(number)
	return null


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


## How a committed number renders in the readout: the value, or an explicit
## absence marker that no zero could be mistaken for.
static func _number_text(value: Variant) -> String:
	if value == null:
		return "absent"
	return str(value)