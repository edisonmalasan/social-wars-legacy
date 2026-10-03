#!/usr/bin/env python3
"""Derivation of the legacy ``place_stored_item`` / ``sell_stored_item`` commands.

The storage round trip (`docs/legacy-stored-unit-placement.md`, PR #271, measured
by 24 executed-legacy probe transactions).  This module is the **single place**
where a storage placement or sale intent becomes the legacy batch envelope and
where the post-execution state is derived, so the executed-legacy capture
(`capture_stored_placement_fixture.py`) and the Compatibility API v0 endpoints
`POST /v0/place_stored` / `POST /v0/sell_stored` are checked against *one*
derivation -- exactly the arrangement the eleven delivered lines use.

The two branches (`command.py:233-256`)
---------------------------------------
    elif cmd == "place_stored_item":          # command.py:233-248
        item_index = args[0]
        item_id    = args[1]
        x          = args[2]
        y          = args[3]
        playerID   = args[4]      # read, NEVER used
        orientation = args[5]
        unknown_autoactivable_bool = args[6]   # read, NEVER used
        unknown_imgIndex = args[7]             # read, NEVER used
        remove_store_item(map, item_id)                  # engine.py:77-84
        map_add_item(map, item_index, item_id, x, y, orientation=orientation)
        bought_unit_add(save, item_id)                   # engine.py:86-89

    elif cmd == "sell_stored_item":           # command.py:250-256
        item_id = args[0]
        remove_store_item(map, item_id)                  # and NOTHING else

Shared derivation (design D2/D3/D5)
------------------------------------
``item_index`` is **never** accepted from a client.  The endpoint derives it as the
smallest positive integer absent from the map's placements -- which is exactly
`placement_envelope.next_free_slot`, already shipped by the placement line, so it
is **reused unchanged** rather than re-implemented.

The row is server-owned in five of its eight slots.  `engine.map_add_item`
(`engine.py:8-31`) writes

    [item_id, x, y, int(time.time()), orientation, [], attr, 1]

so the instant is the **server clock**, slot 5 is **always** an empty garrison
list, and slot 7 is **always** player team `1` because `place_stored_item` never
passes `playerID` on (measured: `args[4] playerID = 3` produced a row whose slot 7
is `1`).  `attr` is a pure function of two committed fields, ported once here:

    properties = get_attribute_from_item_id(item, "properties")
    if properties:                                   # raw JSON-encoded STRING
        properties = json.loads(properties)
        if "friend_assistable" in properties:
            if int(properties["friend_assistable"]) > 0:
                attr["si"] = []
    click_to_build = get_attribute_from_item_id(item, "clicks_to_build")
    if click_to_build:
        if int(click_to_build) > 0:
            attr["nc"] = 0

Measured over the whole committed content: **0 of 429** units carry either field
and **0 of 429** record a positive one, against **26 of 470** and **298 of 470**
buildings.  So `attr` is always `{}` for a unit -- which is why the delivered
prize, Metal Draggy `1085`, places with an empty bag, and why the four **building**
collection prizes all seed `{"nc": 0}`.

**No price exists and none moves** (design D5).  All 24 probe transactions left
every stored resource byte-identical and the branch reads the client's resource
vector nowhere, so the derived vector is the neutral all-zero one.  The sale half
is stronger still: it credits **nothing at all**, and its entire effect is one
store key disappearing.

**One operation consumes exactly one** (design D7).  `remove_store_item`'s
default `quantity=1` is the only quantity the branch exposes, and no quantity
argument exists in either contract -- so a client cannot ask to place or sell two
copies.

**`boughtUnits` counts DISTINCT ids, never units held.**  `bought_unit_add`
(`engine.py:86-89`) is append-if-absent, measured twice: re-storing an id already
in the ledger left the ledger length unchanged, and two placements of one stored id
produced two rows and **one** ledger entry.

The four refusals (design D4) -- all deliberate DIVERGENCES
-----------------------------------------------------------
Every one of these is answered `{"result": "success"}` by the legacy server, and
every one was confirmed by execution.  They are refused here because each destroys
or duplicates player state, and a response indistinguishable from a real placement
is worse than an error.

``not_in_storage``
    `remove_store_item`'s `if itemstr in map["store"]` conditional makes an absent
    item a **silent no-op**: probe 1 #5 placed `1071`, which was never stored, and
    the row appeared, `boughtUnits` grew, and the server answered success.
``slot_occupied``
    `map["items"][str(index)] = [...]` is an **assignment with no occupancy test**.
    Probe 1 #6 wrote over the Command Center at index 1: five leaves rewritten,
    the row **count unchanged**, no error.  A placed building destroyed invisibly.
``unknown_item_id``
    `get_item_from_id` returns `None` for an id in no loaded table.  Probe 1 #14
    placed `999999` with an empty `attr` and appended it to `boughtUnits`.
``item_not_placeable``
    The row exists but carries **neither** `properties` nor `clicks_to_build`, so
    `get_attribute_from_item_id` yields nothing for both and `map_add_item` can
    derive nothing from it.  Measured: **0 of 778** loaded rows and **0 of 900**
    normalized items lack either field, so this refusal is **unreachable through
    the committed corpus** and is exercised only against an in-memory row -- the
    same precedent the construction line set for ``no_build_time``.

Recorded, NOT refused: bounds (design D4)
-----------------------------------------
`place_stored_item [43, 1085, 250, -3, ...]` stored `(250, -3)` verbatim and
`item_index 999999` became a map key (probe 2 #8 and #10).  That is the
**already-recorded M6 tile-to-cell geometry gap**: bounds and cell occupancy are
client-side rules with no server-authoritative validation anywhere in the legacy
source, closing the gap needs new *evidence* rather than a derivation, and
inventing a `0..99` bound here would fabricate a rule the oracle does not have.
`slot_occupied` is not a contradiction of that: it destroys an **existing** row and
is invisible to any count-based check, which is a different and more serious
failure than an out-of-range coordinate that damages nothing.  ``building-move``,
``building-sell`` and ``building-store`` all made the same call for the same
reason, and **no bounds helper exists in this module** -- the suite asserts that
absence mechanically.

Divergences and derived values (never observed)
-----------------------------------------------
* The **four refusals** are deliberate divergences; the legacy server succeeds in
  all four cases.
* The **neutral 8-slot vector** is derived-provisional: the branch never reads it.
* ``orientation`` is a verbatim passthrough, and ``map_add_item`` defaults it to 0.
* That a real Flash client sends exactly these batches is **never observed** (Flash
  is never executed), exactly as for every other line in this project.

Envelope keys
-------------
Exactly the six keys `command()` parses (`docs/legacy-protocol/commands.md`), with
`ts` the current time (or a supplied one) and the other four as documented
placeholders.  All five non-`commands` fields are parsed and then unread by legacy
code, so a time-dependent `ts` has no behavioural effect and parity normalizes it.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

# Design D2: one shared derivation.  The placement module is imported unchanged
# -- nothing here is renamed, moved, or re-implemented, and `next_free_slot` IS
# the slot rule (design D2) rather than a second copy of it.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    GRID_EXTENT,
    data_field,
    in_grid,
    is_strict_int,
    next_free_slot,
    parse_data_field,
    payload_json,
)

# ------------------------------------------------------------- the commands --
PLACE_COMMAND = "place_stored_item"
SELL_COMMAND = "sell_stored_item"

# The eight legacy argument indexes `place_stored_item` reads (command.py:234-241).
ARG_SLOT = 0
ARG_ITEM_ID = 1
ARG_X = 2
ARG_Y = 3
ARG_PLAYER_ID = 4
ARG_ORIENTATION = 5
ARG_UNKNOWN_AUTOACTIVABLE = 6
ARG_UNKNOWN_IMG_INDEX = 7
PLACE_ARGUMENT_COUNT = 8

# `sell_stored_item` reads exactly one positional argument (command.py:251).
SELL_ARG_ITEM_ID = 0
SELL_ARGUMENT_COUNT = 1

# The three arguments the placement branch reads and NEVER uses, each on exactly
# one line of the branch -- its own assignment.  Measured over the 16-line branch
# with comments stripped: `playerID` on 238 only, `unknown_autoactivable_bool` on
# 240 only, `unknown_imgIndex` on 241 only.  `playerID` is the consequential one:
# it is the row's player team, and the branch does not pass it on, so the row is
# ALWAYS team 1 (measured: args[4] = 3 produced a row whose slot 7 is 1).
DISMISSED_ARGUMENTS = (
    {
        "index": ARG_PLAYER_ID,
        "name": "playerID",
        "line": 238,
        "would_be": "the row's player team (slot 7)",
        "note": "read and never passed to map_add_item, so the committed team is "
                "always 1 whatever a client sends -- the same read-but-unused shape "
                "as M7's move `frame`/`string` and M8's `used_syringe`",
    },
    {
        "index": ARG_UNKNOWN_AUTOACTIVABLE,
        "name": "unknown_autoactivable_bool",
        "line": 240,
        "would_be": "unknown; it writes nothing",
        "note": "read and never used",
    },
    {
        "index": ARG_UNKNOWN_IMG_INDEX,
        "name": "unknown_imgIndex",
        "line": 241,
        "would_be": "unknown; the legacy source's own comment says 'one of these "
                    "might be timestamp', and the committed row's slot 3 is the "
                    "SERVER clock (engine.py:13-14), so a client-sent value there "
                    "is discarded",
        "note": "read and never used",
    },
)

# --------------------------------------------------------------- the row ----
# `engine.map_add_item` (engine.py:8-31) writes exactly eight slots.
ROW_SLOTS = 8
ROW_SLOT_ITEM = 0
ROW_SLOT_X = 1
ROW_SLOT_Y = 2
ROW_SLOT_TIMESTAMP = 3
ROW_SLOT_ORIENTATION = 4
ROW_SLOT_STORE = 5
ROW_SLOT_ATTR = 6
ROW_SLOT_PLAYER = 7

# Slot 7 is `map_add_item`'s own `player` default and the only value this branch
# can reach, because it never passes `playerID`.
DERIVED_PLAYER_TEAM = 1
# Slot 5 is always an empty garrison list (engine.py:11-12).
DERIVED_GARRISON: List[Any] = []
# `map_add_item`'s own orientation default; the branch passes a passthrough.
DERIVED_ORIENTATION = 0

ROW_DERIVATION = (
    "the row is server-owned in FIVE of its eight slots: item_id, x and y come "
    "from the client's cell intent, orientation is a verbatim passthrough, and "
    "the instant is the SERVER clock (int(time.time()), engine.py:13-14), the "
    "garrison is ALWAYS an empty list (engine.py:11-12), the attribute bag is "
    "derived from committed content, and the player team is ALWAYS 1 because "
    "place_stored_item never passes the client-sent playerID on (command.py:238 "
    "reads it, command.py:245 does not pass it)"
)

# ------------------------------------------------------- the attribute bag ---
PROPERTIES_FIELD = "properties"
CLICK_TO_BUILD_FIELD = "clicks_to_build"
FRIEND_ASSISTABLE_FLAG = "friend_assistable"
# The two keys `map_add_item`'s player == 1 block can write, in the order the
# legacy block writes them.
ATTR_ASSIST_KEY = "si"
ATTR_CLICKS_KEY = "nc"
# The closed vocabulary of the derived bag.  `ABSENT_HELPERS` below names what is
# deliberately NOT in it.
ATTR_KEYS = (ATTR_ASSIST_KEY, ATTR_CLICKS_KEY)

# The only three states of the derived bag: a unit (neither key), a building that
# needs build clicks, and a friend-assistable building.  Measured: 0 of 429 units
# reach either key.
ATTR_RULE = (
    "attr is a PURE FUNCTION of two committed item fields and never a client "
    "input: `si` (an empty friend-assist list) when "
    "properties.friend_assistable > 0, and `nc` (a build-click counter seeded at "
    "zero) when clicks_to_build > 0. The port is exact -- `map_add_item` reads "
    "properties through get_attribute_from_item_id and then json.loads it, tests "
    "TRUTHINESS of the raw string first (so an empty properties blob yields no "
    "`si`), and only then tests int() > 0 on each value. NO DERIVATION FUNCTION IN "
    "THIS MODULE ACCEPTS AN `attr`, A `player`, OR A `price` PARAMETER: "
    "derive_attr, expected_row, divergence_place and build_place_envelope all take "
    "the two committed FIELDS and derive the bag, so even the post-execution proof "
    "cannot be handed a bag and satisfied with it. The only two permitted "
    "exceptions are read-only comparisons -- attr_derived_from, the named INVERSE, "
    "which reports on a bag rather than producing one, and expected_storage_after's "
    "single quantity argument, whose default is this module's own QUANTITY constant "
    "and never a client value -- so 'the client cannot dictate the row's bag, its "
    "team, or any price' is MECHANICAL rather than a promise"
)

# The named INVERSE of `derive_attr`: which committed field produced each key.
# Asserted to round-trip across all 900 normalized items.
ATTR_SOURCE = {ATTR_ASSIST_KEY: "properties.friend_assistable",
               ATTR_CLICKS_KEY: "clicks_to_build"}
INVERSE_RULE = (
    "attr_derived_from() is the named inverse of derive_attr(): it reports the "
    "committed field each key was derived from, or nothing for an absent key. The "
    "round trip is asserted over all 900 normalized items (429 units + 470 "
    "buildings + 1 special) -- the inverse must name exactly the committed fields "
    "the forward derivation consumed -- so a renamed field or a dropped condition "
    "fails rather than passing silently"
)

# The measured distribution the derivation exists to reproduce.  Counted over the
# committed NORMALIZED package (the service reads the loaded raw configuration,
# whose `properties` is a JSON-encoded STRING and whose counts agree on values --
# the R2 coercion boundary M8 line 1 recorded).
COMMITTED_UNITS = 429
COMMITTED_BUILDINGS = 470
COMMITTED_SPECIAL = 1
COMMITTED_ITEMS = COMMITTED_UNITS + COMMITTED_BUILDINGS + COMMITTED_SPECIAL
COMMITTED_UNITS_WITH_CLICKS = 0
COMMITTED_UNITS_WITH_ASSIST = 0
COMMITTED_BUILDINGS_WITH_CLICKS = 298
COMMITTED_BUILDINGS_WITH_ASSIST = 26
COMMITTED_CONTENT_NOTE = (
    "MEASURED over the committed normalized package: 0 of 429 units record a "
    "positive clicks_to_build and 0 of 429 carry a friend_assistable flag at all, "
    "against 298 of 470 and 26 of 470 buildings. So `attr` is ALWAYS {} for a "
    "unit and is content-shaped only for buildings -- which is exactly why the "
    "six unit collection prizes all place with an empty bag and the four BUILDING "
    "prizes all seed {\"nc\": 0}"
)

# ------------------------------------------------- the slot / its inverse ----
SLOT_RULE = (
    "the map slot is DERIVED SERVER-SIDE as the smallest positive integer absent "
    "from the map's placements -- placement_envelope.next_free_slot, reused "
    "unchanged rather than re-implemented -- so a client cannot name a slot, "
    "cannot overwrite one, and cannot dictate the row. The committed fresh corpus "
    "places keys 1..40, so the first derived slot is 41"
)
SLOT_INVERSE_RULE = (
    "slot_occupied() is the named INVERSE of next_free_slot(): it reports whether "
    "one named slot is already present. resolve_slot() calls the derivation and "
    "then its own inverse, and REFUSES `slot_occupied` when the two disagree. "
    "That disagreement is unreachable through an honest corpus -- it is precisely "
    "why the guard is a second line of defence rather than the first -- and the "
    "suite exercises it against an in-memory corpus whose key view and occupancy "
    "view have been made to conflict"
)
REFUSAL_SLOT_OCCUPIED_NOTE = (
    "`map['items'][str(index)] = [...]` is an assignment with NO occupancy test "
    "(engine.py:31). Measured: writing over the Command Center at index 1 "
    "rewrote FIVE leaves, left the row COUNT unchanged, moved no resource, and "
    "the server answered success -- a placed building destroyed invisibly, and "
    "invisible to any count-based check, which is why the post-execution proof is "
    "two-part and why this refusal exists at all"
)

# ------------------------------------------------------------- refusals -----
REASON_NOT_IN_STORAGE = "not_in_storage"
REASON_SLOT_OCCUPIED = "slot_occupied"
REASON_UNKNOWN_ITEM_ID = "unknown_item_id"
REASON_ITEM_NOT_PLACEABLE = "item_not_placeable"
REASON_UNRESOLVABLE_STORAGE = "unresolvable_storage"

# Structural (never a gameplay rule): the request must be a JSON object carrying a
# strict-integer item id, two integer coordinates, and an optional integer
# orientation.
REASON_INVALID_ITEM_ID = "invalid_item_id"
REASON_INVALID_COORDINATES = "invalid_coordinates"
REASON_INVALID_ORIENTATION = "invalid_orientation"

# The four gameplay refusals, as one machine-readable list, in the order the
# delta's requirement names them.  `legacy` is what the real server answers.
REFUSALS = (
    {
        "refusal": REASON_NOT_IN_STORAGE,
        "implemented": True,
        "status": 409,
        "legacy": "places the row anyway and answers success (probe 1 #5: item "
                  "1071 was never stored, rows 41 -> 42, the store UNCHANGED, "
                  "boughtUnits grew, {\"result\": \"success\"})",
        "divergence": True,
        "why": "duplicates an unacquired unit onto the map and records it as "
               "bought. `remove_store_item`'s `if itemstr in map[\"store\"]` "
               "conditional (engine.py:78) makes an absent item a silent no-op, "
               "and that conditional is the whole cause",
    },
    {
        "refusal": REASON_SLOT_OCCUPIED,
        "implemented": True,
        "status": 409,
        "legacy": "overwrites the existing row and answers success (probe 1 #6: "
                  "index 1's Command Center [26,51,41,0,0,[],{},1] was replaced, "
                  "FIVE leaves rewritten, row count unchanged)",
        "divergence": True,
        "why": "destroys a placed building invisibly. `map_add_item` assigns with "
               "no occupancy test (engine.py:31)",
    },
    {
        "refusal": REASON_UNKNOWN_ITEM_ID,
        "implemented": True,
        "status": 409,
        "legacy": "places the row with an empty attr, appends the id to "
                  "boughtUnits, and answers success (probe 1 #14: 999999 is in no "
                  "normalized table and in no config section)",
        "divergence": True,
        "why": "a row nothing can render, price, or resolve. "
               "`get_item_from_id` returns None and `get_attribute_from_item_id` "
               "therefore yields nothing for either derived field",
    },
    {
        "refusal": REASON_ITEM_NOT_PLACEABLE,
        "implemented": True,
        "status": 409,
        "legacy": "n/a -- unreached: 0 of 778 loaded rows and 0 of 900 normalized "
                  "items lack BOTH committed fields",
        "divergence": True,
        "why": "the row exists but carries neither `properties` nor "
               "`clicks_to_build`, so `get_attribute_from_item_id` yields nothing "
               "for either and the placement would write a row derived from no "
               "committed content at all. Unreachable through the committed "
               "corpus, so it is exercised only against an in-memory row -- the "
               "same precedent `no_build_time` set on the construction line",
    },
)
REFUSAL_COUNT = len(REFUSALS)

# --------------------------------------------- recorded, NOT refused ---------
GEOMETRY_GAP = (
    "GRID BOUNDS AND CELL OCCUPANCY ARE RECORDED, NOT REFUSED. place_stored_item "
    "[43, 1085, 250, -3, ...] stored (250, -3) verbatim and `item_index` 999999 "
    "became a map key (probe 2 #8 and #10). That is the ALREADY-RECORDED M6 "
    "tile-to-cell geometry gap: bounds and occupancy are client-side rules with no "
    "server-authoritative validation anywhere in the legacy source. Closing it "
    "needs new EVIDENCE, not a derivation, and inventing a 0..99 bound here would "
    "fabricate a rule the oracle does not have. `slot_occupied` is not a "
    "contradiction of this: it destroys an EXISTING row and is invisible to any "
    "count-based check, which is a different and more serious failure than an "
    "out-of-range coordinate that damages nothing. building-move, building-sell "
    "and building-store all made the same call for the same reason. NO BOUNDS "
    "HELPER EXISTS IN THIS MODULE, and the suites assert that absence mechanically"
)
CELL_OCCUPANCY_GAP = (
    "CELL OCCUPANCY IS NOT CHECKED EITHER: no branch reads any neighbouring row "
    "and no committed content records a footprint-aware derivation, so a placement "
    "may overlap an existing row's cells. The 2x2 General Sculpture prize (136) and "
    "the 3x3 Fountain prize (106) need footprint-aware cell derivation, which is "
    "blocked on the same M6 gap; this line ships on the 1x1 Metal Draggy prize and "
    "records the rest"
)

# The deliberate client-side rules the flow relies on, reported as such.
ADDRESSABILITY = (
    "ADDRESSABILITY AND STORABILITY ARE CLIENT-SIDE RULES. The flow offers a "
    "placement only for an item the player's own storage records and a sale only "
    "for an item it still holds; the service adds no ownership, capacity, or "
    "eligibility rule beyond the four refusals, because the committed save records "
    "none and adding one would invent it"
)
NO_CAPACITY_RULE = (
    "NO CAPACITY, EXPIRY, VALUE, OR PRICE RULE EXISTS. The committed save records "
    "storage as plain {item id: count} integers with no limit, no expiry, and no "
    "ownership rule anywhere in the committed configuration, and the legacy server "
    "has no capacity check on this path. Storage is NOT a purchase inventory and no "
    "entry carries a refund"
)
NO_REFUND_NOTE = (
    "SELLING CREDITS NOTHING. `sell_stored_item` (command.py:250-256) reads one "
    "argument, calls `remove_store_item`, and prints -- no `map[\"gold\"]`, no "
    "`apply_resources`, no return value. Measured over two executed sales: EXACTLY "
    "ONE changed leaf, the store key, with no row added, no boughtUnits entry "
    "written or removed, and no resource credited. A sale is therefore a pure "
    "storage decrement, and the client must present it as crediting nothing"
)
NO_STOCK_RULE = (
    "`store_add_items` (command.py:258-266) is OUT OF SCOPE: it is an unvalidated "
    "client-sent item id list that grants into storage, which `godot-unit-"
    "production` already recorded as an acquisition anti-pattern. It is used in "
    "the fixture's PROBES only as a seeding device and is delivered not at all, so "
    "the fixture's own precondition is established by the content-derived "
    "`complete_collection` instead"
)

# One operation consumes exactly one (measured: probe 1 #7-#8).
QUANTITY = 1
QUANTITY_RULE = (
    "ONE OPERATION CONSUMES EXACTLY ONE UNIT OF STOCK. "
    "`remove_store_item(map, item)` is called without its third argument "
    "(engine.py:77), so legacy's default quantity is exactly 1, and NEITHER "
    "contract carries a quantity: a client cannot place or sell two copies, and "
    "cannot guess a parameter the branch would ignore"
)
LEDGER_RULE = (
    "`boughtUnits` COUNTS DISTINCT IDS, NEVER UNITS HELD. `bought_unit_add` "
    "(engine.py:86-89) is append-if-absent, measured twice: re-storing an id the "
    "ledger already held left its length unchanged, and two placements of one "
    "stored id produced TWO rows, TWO stock decrements, and ONE ledger entry"
)
TIMESTAMP_NOTE = (
    "the placed row's slot 3 is a WALL-CLOCK reading (`int(time.time())`, "
    "engine.py:13-14), so a fixture's after.json is NOT byte-stable across reruns "
    "and the capture's documented time-dependent field list gains this entry"
)

# ---------------------------------------------- the committed corpus pins ----
# Pinned so a config or corpus drift fails a run instead of publishing a
# different fixture.  Each is cross-checked against the real configuration and the
# real save at run time.
# The seed route is REUSED, not re-derived: `collection_envelope` already owns the
# one-based collection index (get_collection_prize computes `max(0, id - 1)`), the
# 0-and-1 alias, and these two committed pins, so they are imported unchanged and
# re-asserted by the suites rather than restated here.
from collection_envelope import (  # noqa: F401
    COMMITTED_COLLECTION_ID,
    COMMITTED_COLLECTION_NAME,
    COMMITTED_COLLECTION_COUNT,
)

COMMITTED_PRIZE_ID = 1085
COMMITTED_PRIZE_QUANTITY = 1
COMMITTED_PLACEMENTS = 40
COMMITTED_DERIVED_SLOT = 41
COMMITTED_CELL = (58, 47)
COMMITTED_ORIENTATION = 0
COMMITTED_RESOURCE_BEFORE = {
    "xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
    "cash": 5, "mana": 0,
}
# A second committed item the sale transaction needs, seeded through the SAME
# content-derived route: collection 2, whose committed prize is exactly
# ``{"1062": 1}``.  Both pins are re-asserted against the loaded configuration by
# the capture and by the endpoint, so a content drift fails loudly.
COMMITTED_SELL_COLLECTION_ID = 2
COMMITTED_SELL_ITEM_ID = 1062
COMMITTED_SELL_PRIZE = {str(COMMITTED_SELL_ITEM_ID): COMMITTED_PRIZE_QUANTITY}
# The id the investigation's third vector used, recorded here so the capture's
# probe cannot drift from the record it was measured by.
RECORDED_UNKNOWN_ITEM_ID = 999999
# The recorded out-of-grid probe cell.
RECORDED_OUT_OF_GRID_CELL = (250, -3)
# The recorded occupied-index probe: the Command Center at map key 1.
RECORDED_OCCUPIED_SLOT = 1
RECORDED_OCCUPIED_ROW = [26, 51, 41, 0, 0, [], {}, 1]
# The recorded never-stored probe id (probe 1 #5).
RECORDED_UNSTORED_ITEM_ID = 1071

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The closed intent vocabulary.  Anything a client sends beyond these keys is
# ignored server-side, exactly as a client-supplied amount or price is ignored on
# the collect, expand, level-up, collection, and revival routes.
PLACE_INTENT_KEYS = ("user_id", "item_id", "x", "y", "orientation")
PLACE_INTENT_REQUIRED_KEYS = ("user_id", "item_id", "x", "y")
SELL_INTENT_KEYS = ("user_id", "item_id")
PLACE_INTENT_IGNORED_KEYS = (
    "attr", "attribute", "autoactivable", "bought", "cost", "costs", "count",
    "img_index", "index", "item_index", "map_key", "orientation_flag", "placement",
    "player", "playerID", "player_id", "price", "quantity", "reason", "refund",
    "resources_changed", "row", "slot", "team", "timestamp", "value", "vector",
)
SELL_INTENT_IGNORED_KEYS = (
    "attr", "cash", "cost", "costs", "count", "gold", "index", "item_index",
    "map_key", "orientation", "player", "player_id", "price", "quantity", "reason",
    "refund", "resources_changed", "row", "slot", "team", "value", "vector", "x", "y",
)
INTENT_NOTE = (
    "THE PLACEMENT INTENT CARRIES A PLAYER, A STORED ITEM ID, AND A TARGET CELL. "
    "It never carries a map slot, a row, an attribute bag, a player team, a stored "
    "count, or a price -- every one of those is derived from committed content on "
    "the server. The SALE INTENT CARRIES A PLAYER AND A STORED ITEM ID and nothing "
    "else: no price, no refund, no quantity"
)

# What this module deliberately does NOT expose.  Each of these would compute a
# rule the legacy server never had, so none is declared here.  The suites assert
# this module's whole function inventory against a pinned list AND against this
# list -- a rename cannot smuggle one past the inventory, and a leftover here fails
# visibly.
ABSENT_HELPERS = (
    ("bounds", "grid bounds and cell occupancy are the recorded M6 geometry gap "
               "(GEOMETRY_GAP); no bound is derived and none is invented"),
    ("in_bounds", "as `bounds`: inventing a 0..99 rule the oracle does not have "
                  "would fabricate behaviour"),
    ("grid_bounds", "as `bounds`"),
    ("footprint", "footprint-aware cell derivation is blocked on the same M6 gap "
                  "(CELL_OCCUPANCY_GAP); the line ships on the 1x1 prize"),
    ("footprint_cells", "as `footprint`"),
    ("overlaps", "no branch reads a neighbouring row and no committed content "
                 "records one, so no overlap rule exists to reproduce"),
    ("capacity", "NO_CAPACITY_RULE: the legacy server has no capacity check on "
                 "this path and the committed save records no limit"),
    ("storage_limit", "as `capacity`"),
    ("expiry", "no committed field records a storage expiry"),
    ("expire", "as `expiry`"),
    ("price", "NO PRICE EXISTS: all 24 executed transactions left every stored "
              "resource byte-identical and the branch reads the client's vector "
              "nowhere"),
    ("refund", "NO_REFUND_NOTE: the sale branch credits NOTHING AT ALL -- its "
               "entire effect is one store key disappearing"),
    ("refund_value", "as `refund`"),
    ("reward", "no committed content records a sale value and the legacy branch "
               "pays none"),
    ("value", "as `reward`"),
    ("cost", "as `price`"),
    ("grant", "as `price`"),
    ("store_add_items", "NO_STOCK_RULE: an unvalidated client-sent item id list "
                        "that grants into storage, recorded as an acquisition "
                        "anti-pattern by godot-unit-production"),
    ("add_items", "as `store_add_items`"),
    ("acceptance", "the legacy server has no acceptance test and authoring one "
                   "would invent a rule"),
    ("eligible", "no branch verifies a stored item may be placed or sold beyond "
                 "the four refusals"),
)

__all__ = [
    "ENVELOPE_KEYS", "EnvelopeError", "GRID_EXTENT", "RESOURCE_VECTOR_SLOTS",
    "PLACE_COMMAND", "SELL_COMMAND", "PLACE_ARGUMENT_COUNT",
    "SELL_ARGUMENT_COUNT", "DERIVED_PLAYER_TEAM", "DERIVED_ORIENTATION",
    "ROW_SLOTS", "ROW_SLOT_ITEM", "ROW_SLOT_X", "ROW_SLOT_Y",
    "ROW_SLOT_TIMESTAMP", "ROW_SLOT_ORIENTATION", "ROW_SLOT_STORE",
    "ROW_SLOT_ATTR", "ROW_SLOT_PLAYER", "ATTR_KEYS", "ATTR_CLICKS_KEY",
    "ATTR_ASSIST_KEY", "REFUSALS", "REFUSAL_COUNT", "REASON_NOT_IN_STORAGE",
    "REASON_SLOT_OCCUPIED", "REASON_UNKNOWN_ITEM_ID",
    "REASON_ITEM_NOT_PLACEABLE", "REASON_UNRESOLVABLE_STORAGE",
    "ABSENT_HELPERS", "QUANTITY", "data_field", "in_grid", "is_strict_int",
    "next_free_slot", "parse_data_field", "payload_json",
    "COMMITTED_COLLECTION_ID", "COMMITTED_COLLECTION_NAME",
    "COMMITTED_COLLECTION_COUNT",
    "attr_derived_from", "build_place_envelope", "build_sell_envelope",
    "committed_item", "derive_attr", "divergence_place", "divergence_sell",
    "expected_ledger", "expected_row", "expected_storage_after",
    "is_placeable", "neutral_vector", "project_storage", "resolve_slot",
    "slot_occupied", "store_count", "validate_item_id", "validate_orientation",
    "validate_coordinates",
]


# ------------------------------------------------------------ the neutral ----
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D5).

    A fresh list every call so a caller can never mutate the derivation for the
    next one.  This is the same boundary the store, move, sell, collection, and
    revival lines took: the committed configuration records no placing or selling
    price, a client-sent delta would let any client mint resources through this
    very branch (``apply_resources`` runs BEFORE the branch, command.py:40), and
    the post-execution proof requires every stored resource to be UNCHANGED.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


# ------------------------------------------------------- committed content --
def committed_item(table: Any, item_id: Any) -> Optional[Dict[str, Any]]:
    """One committed item row for ``item_id``, verbatim, or ``None``.

    ``table`` is the loaded legacy configuration's ``items`` list -- the bytes
    ``get_item_from_id`` reads (``get_game_config.py:117-125``), so ``properties``
    is a raw JSON-encoded **string** here and the derivation must read that
    representation.  Located by the row's own native ``id`` column, last match
    wins, reproducing the id-to-position index's own behaviour.  Ids are unique
    across the loaded set (measured: 778 distinct ids over 778 rows), so there is
    nothing to disambiguate.  ``None`` is the ``unknown_item_id`` refusal.
    """
    if not isinstance(table, list):
        return None
    found: Optional[Dict[str, Any]] = None
    for row in table:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get("id")) != int(item_id):
                continue
        except (TypeError, ValueError):
            continue
        found = row
    return dict(found) if found is not None else None


def is_placeable(row: Optional[Mapping[str, Any]]) -> bool:
    """Whether ``map_add_item`` could derive anything at all from ``row``.

    The machine-readable form of the ``item_not_placeable`` refusal: a row that
    carries **neither** ``properties`` nor ``clicks_to_build`` yields ``None``
    from ``get_attribute_from_item_id`` for both, so ``map_add_item``'s
    ``player == 1`` block writes nothing and the placement would be a row derived
    from no committed content at all.  Measured over the committed content: **0 of
    778** loaded rows and **0 of 900** normalized items fail this, so the refusal
    is unreachable through the committed corpus and is exercised only against an
    in-memory row.
    """
    if row is None:
        return False
    return bool(row.get(PROPERTIES_FIELD)) or bool(row.get(CLICK_TO_BUILD_FIELD))


# --------------------------------------------------------- the attr mirror --
def _committed_int(value: Any, field: str) -> int:
    """``int(value)`` under the legacy rules, failing closed rather than raising.

    Legacy calls ``int(...)`` directly, so a non-numeric committed value raises
    ``ValueError`` inside the dispatcher and the batch is persisted as a failure.
    Deriving it here must therefore be a **named refusal** rather than an
    exception: a half-derived bag would be a fabricated row.
    """
    if isinstance(value, bool):
        raise EnvelopeError("item_field_invalid",
                            "committed %s is a boolean" % field)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != int(value):
            raise EnvelopeError("item_field_invalid",
                                "committed %s is not a whole number" % field)
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            raise EnvelopeError(
                "item_field_invalid",
                "committed %s %r is not an integer" % (field, value),
            )
    raise EnvelopeError(
        "item_field_invalid",
        "committed %s is a %s, which legacy's int() cannot read"
        % (field, type(value).__name__),
    )


def _decode_properties(properties: Any) -> Optional[Mapping[str, Any]]:
    """``json.loads`` the RAW committed properties blob, or ``None``.

    Legacy reads the field through ``get_attribute_from_item_id`` and tests its
    **TRUTHINESS** first, so an absent or empty blob skips the whole ``si``
    branch.  The committed normalized package stores the same values as an
    **object** instead -- the R2 coercion boundary M8 line 1 recorded -- so both
    representations are accepted here and neither is re-implemented.
    """
    if properties is None:
        return None
    if isinstance(properties, Mapping):
        return properties if properties else None
    if isinstance(properties, str):
        if properties.strip() == "":
            return None
        try:
            decoded = json.loads(properties)
        except ValueError as error:
            raise EnvelopeError("item_properties_invalid",
                                "committed properties is not valid JSON: %s" % error)
        if not isinstance(decoded, Mapping):
            raise EnvelopeError(
                "item_properties_invalid",
                "committed properties decodes to a %s, not an object"
                % type(decoded).__name__,
            )
        return decoded if decoded else None
    raise EnvelopeError(
        "item_properties_invalid",
        "committed properties is a %s" % type(properties).__name__,
    )


def derive_attr(clicks_to_build: Any, properties: Any) -> Dict[str, Any]:
    """The row's attribute bag, derived from two committed fields alone.

    An exact port of ``engine.map_add_item``'s ``player == 1`` block
    (``engine.py:19-31``) for the team this branch can only reach.  ``si`` is
    written before ``nc``, matching the legacy statement order.  No client input
    reaches this function and none can: no helper in this module accepts an
    ``attr`` or a ``player`` argument.

    Raises :class:`EnvelopeError` with ``item_properties_invalid`` or
    ``item_field_invalid`` when the committed values cannot be read the way
    legacy's ``int()`` reads them, so a malformed committed field fails closed
    instead of producing a half-derived row.
    """
    attr: Dict[str, Any] = {}
    decoded = _decode_properties(properties)
    if decoded is not None and FRIEND_ASSISTABLE_FLAG in decoded:
        if _committed_int(decoded[FRIEND_ASSISTABLE_FLAG],
                          "properties.%s" % FRIEND_ASSISTABLE_FLAG) > 0:
            attr[ATTR_ASSIST_KEY] = []
    if clicks_to_build:
        if _committed_int(clicks_to_build, CLICK_TO_BUILD_FIELD) > 0:
            attr[ATTR_CLICKS_KEY] = 0
    return attr


def attr_derived_from(attr: Any) -> List[str]:
    """The named inverse of :func:`derive_attr`: which committed field made each key.

    Reports the committed field names in the legacy write order, so the round trip
    is checkable: an absent key contributes nothing, and a key that is not part of
    the closed derived vocabulary is reported rather than silently accepted.
    """
    if not isinstance(attr, Mapping):
        raise EnvelopeError("attr_invalid",
                            "attr is a %s, not an object" % type(attr).__name__)
    reported: List[str] = []
    for key in ATTR_KEYS:
        if key in attr:
            reported.append(ATTR_SOURCE[key])
    for key in attr:
        if key not in ATTR_KEYS:
            reported.append("unknown:%s" % key)
    return reported


# ----------------------------------------------------------- the slot rule ---
def slot_occupied(items: Mapping[Any, Any], slot: Any) -> bool:
    """Whether ``slot`` already names a row -- the named inverse of the derivation.

    Legacy map keys are ``str(index)`` written by ``engine.map_add_item``; keys
    that do not parse as an integer cannot collide with a numeric slot string and
    are ignored (documented, never observed in a real save).
    """
    if not is_strict_int(slot) or int(slot) < 1:
        raise EnvelopeError("invalid_slot",
                            "a map slot must be a positive integer, got %r" % (slot,))
    return str(int(slot)) in items


def resolve_slot(items: Mapping[Any, Any]) -> int:
    """The derived map slot, with its own inverse applied as a second guard.

    Derives the smallest positive integer absent from ``items`` (the reused
    :func:`placement_envelope.next_free_slot`) and then REFUSES ``slot_occupied``
    if that very slot is present.  The two can only disagree on a corpus whose
    key view and occupancy view conflict -- which is exactly the state the refusal
    exists to catch, and which the suite manufactures in memory.
    """
    slot = next_free_slot(items)
    if slot_occupied(items, slot):
        raise EnvelopeError(
            REASON_SLOT_OCCUPIED,
            "the derived map slot %d already names a row; placing there would "
            "destroy it silently, because engine.map_add_item assigns with no "
            "occupancy test (engine.py:31)" % slot,
        )
    return slot


# ------------------------------------------------------------ input shape ---
def validate_item_id(item_id: Any) -> int:
    """A strict-integer stored item id."""
    if not is_strict_int(item_id):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "item_id must be an integer, got %s" % type(item_id).__name__,
        )
    return int(item_id)


def validate_coordinates(x: Any, y: Any) -> "tuple":
    """Two integer cell coordinates, and **nothing else**.

    Deliberately **no bound**: an out-of-range or negative cell is the recorded
    M6 geometry gap (GEOMETRY_GAP), so this validates the *shape* only and a
    caller must not read acceptance as an in-grid claim.
    """
    if not is_strict_int(x) or not is_strict_int(y):
        raise EnvelopeError(
            REASON_INVALID_COORDINATES,
            "x and y must be integers, got %s/%s"
            % (type(x).__name__, type(y).__name__),
        )
    return (int(x), int(y))


def validate_orientation(orientation: Any) -> int:
    """The orientation passthrough. No range rule: legacy never bounds one."""
    if not is_strict_int(orientation):
        raise EnvelopeError(
            REASON_INVALID_ORIENTATION,
            "orientation must be an integer, got %s" % type(orientation).__name__,
        )
    return int(orientation)


# ------------------------------------------------- the storage projection ----
def project_storage(store: Any, ledger: Any) -> Dict[str, Any]:
    """The player's storage and purchase ledger, reported verbatim or refused.

    Reads the map-level record ``maps[0]["store"]`` together with
    ``privateState["boughtUnits"]`` and reports each stored item's committed count
    and the ledger's contents **exactly as recorded** -- order, duplicates, and
    all.  It derives **no** capacity, stacking limit, expiry, value, or price,
    because the committed save records none (NO_CAPACITY_RULE), and it never
    recomputes, normalises, or omits a count.

    Fails closed, changing no value, when the store is absent or not a mapping,
    when a count is not an integer, or when the ledger is present but not a list.
    The recorded values it *could* read are reported beside the refusal so a
    reader sees what it saw.
    """
    result: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "entries": [],
        "counts": {},
        "total_units": 0,
        "distinct_ids": 0,
        "ledger": None,
        "ledger_distinct_ids": 0,
        "ledger_is_list": isinstance(ledger, list),
        "store_is_mapping": isinstance(store, Mapping),
        "capacity": None,
        "expiry": None,
        "value": None,
        "price": None,
        "note": NO_CAPACITY_RULE,
    }
    if not isinstance(store, Mapping):
        result["reason"] = REASON_UNRESOLVABLE_STORAGE
        result["error"] = (
            "maps[0]['store'] is %s, not a mapping; the storage is unresolvable "
            "and no entry is invented, defaulted, or dropped"
            % type(store).__name__
        )
        if isinstance(ledger, list):
            result["ledger"] = list(ledger)
            result["ledger_distinct_ids"] = len(_distinct(ledger))
        return result
    counts: Dict[str, int] = {}
    for key in store:
        value = store[key]
        if not is_strict_int(value):
            result["reason"] = REASON_UNRESOLVABLE_STORAGE
            result["error"] = (
                "stored item %r holds %s, not an integer count; the storage is "
                "unresolvable and no entry is invented, defaulted, or dropped"
                % (key, type(value).__name__)
            )
            result["counts"] = dict(counts)
            if isinstance(ledger, list):
                result["ledger"] = list(ledger)
                result["ledger_distinct_ids"] = len(_distinct(ledger))
            return result
        counts[str(key)] = int(value)
    if ledger is not None and not isinstance(ledger, list):
        result["reason"] = REASON_UNRESOLVABLE_STORAGE
        result["error"] = (
            "privateState['boughtUnits'] is %s, not a list; the storage is "
            "unresolvable and no entry is invented, defaulted, or dropped"
            % type(ledger).__name__
        )
        result["counts"] = counts
        return result
    entries = [
        {"item_id": key, "count": counts[key]}
        for key in sorted(counts, key=lambda text: (int(text) if text.isdigit() else 0, text))
    ]
    result["ok"] = True
    result["entries"] = entries
    result["counts"] = counts
    result["total_units"] = sum(counts.values())
    result["distinct_ids"] = len(counts)
    result["ledger"] = list(ledger) if isinstance(ledger, list) else None
    if isinstance(ledger, list):
        result["ledger_distinct_ids"] = len(_distinct(ledger))
    return result


def _distinct(entries: Sequence[Any]) -> List[Any]:
    """Distinct entries in first-appearance order -- never sorted, never merged."""
    seen: List[Any] = []
    for entry in entries:
        if entry not in seen:
            seen.append(entry)
    return seen


def store_count(store: Any, item_id: Any) -> int:
    """The committed count for one stored item, or ``0`` when it is absent.

    ``0`` is the *absent* reading and never a stored zero: ``remove_store_item``
    DELETES the key when the remaining quantity is not positive
    (``engine.py:80-83``), so a real store holds no zero entry.
    """
    if not isinstance(store, Mapping):
        raise EnvelopeError(
            REASON_UNRESOLVABLE_STORAGE,
            "maps[0]['store'] is a %s, not a mapping" % type(store).__name__,
        )
    value = store.get(str(item_id))
    if value is None:
        return 0
    if not is_strict_int(value):
        raise EnvelopeError(
            REASON_UNRESOLVABLE_STORAGE,
            "stored item %r holds %s, not an integer count"
            % (item_id, type(value).__name__),
        )
    return int(value)


def expected_storage_after(before: Any, after: Any, item_id: Any,
                           quantity: int = QUANTITY) -> Optional[str]:
    """The first way a storage result diverges from the derived decrement, or None.

    The whole value-level half of both post-execution proofs: the named item's
    count must fall by **exactly** ``quantity``, the key must be **gone** when
    that reaches zero (``engine.remove_store_item`` deletes it), and **no other
    stored key may move**.

    This is a comparison against the before-state and the derived quantity, never
    against anything a client sent, which is what makes it non-tautological.
    """
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return "the storage is a %s/%s, not a mapping" % (
            type(before).__name__, type(after).__name__,
        )
    count_before = store_count(before, item_id)
    count_after = store_count(after, item_id)
    if count_before == 0:
        return ("stored item %r was not in storage before the operation, so its "
                "count cannot fall by %d" % (item_id, quantity))
    if count_after != count_before - quantity:
        if count_after == 0:
            return ("stored item %r holds %d after the operation, not the derived "
                    "%d (the key must survive a count above zero)"
                    % (item_id, count_after, count_before - quantity))
        return ("stored item %r holds %d after the operation, not the derived %d"
                % (item_id, count_after, count_before - quantity))
    if count_after == 0 and str(item_id) in after:
        return ("stored item %r still holds a key after reaching zero; "
                "engine.remove_store_item DELETES it (engine.py:80-83)"
                % (item_id,))
    for key in set(before) | set(after):
        if str(key) == str(item_id):
            continue
        if before.get(key) != after.get(key):
            return ("stored item %r moved %r -> %r, which the operation never "
                    "mentions" % (key, before.get(key), after.get(key)))
    return None


def expected_ledger(before: Any, item_id: Any) -> List[Any]:
    """``boughtUnits`` after a placement: append-if-absent, verbatim.

    The ledger counts **distinct ids, never units held** (LEDGER_RULE): an id
    already present leaves the ledger byte-identical, which is what makes the
    endpoint's ledger half non-tautological -- an append-if-absent that always
    appended would look identical the first time.
    """
    if before is None:
        return [item_id]
    if not isinstance(before, list):
        raise EnvelopeError(
            REASON_UNRESOLVABLE_STORAGE,
            "privateState['boughtUnits'] is a %s, not a list"
            % type(before).__name__,
        )
    entries = list(before)
    if item_id not in entries:
        entries.append(item_id)
    return entries


def expected_row(item_id: Any, x: Any, y: Any, timestamp: Any,
                 orientation: Any = DERIVED_ORIENTATION,
                 clicks_to_build: Any = None,
                 properties: Any = None) -> List[Any]:
    """The eight-slot row ``engine.map_add_item`` writes, in its own field order.

    ``[item_id, x, y, timestamp, orientation, [], attr, 1]`` -- the instant is the
    server clock, slot 5 is always an empty garrison list, slot 7 is always player
    team 1, and the attribute bag is **derived** from the two committed fields
    rather than received.  Taking ``clicks_to_build`` and ``properties`` instead
    of a finished ``attr`` is what keeps ATTR_RULE's "no helper accepts an
    ``attr``" claim true of this function as well as of the envelope builders, and
    it is what makes the comparison a derivation rather than a restatement of the
    caller's own input.
    """
    if not is_strict_int(timestamp) or int(timestamp) < 0:
        raise EnvelopeError("invalid_timestamp",
                            "the row instant must be a non-negative integer")
    return [
        int(item_id),
        int(x),
        int(y),
        int(timestamp),
        int(orientation),
        list(DERIVED_GARRISON),
        derive_attr(clicks_to_build, properties),
        DERIVED_PLAYER_TEAM,
    ]


# ------------------------------------------------ the post-execution proofs --
def divergence_place(
    store_before: Any,
    store_after: Any,
    ledger_before: Any,
    ledger_after: Any,
    row_after: Any,
    item_id: Any,
    x: Any,
    y: Any,
    orientation: Any = DERIVED_ORIENTATION,
    clicks_to_build: Any = None,
    properties: Any = None,
    timestamp: Any = None,
) -> Optional[str]:
    """The first way a placement's post-state diverges from the derivation, or None.

    **Two parts**, and the second is the one that cannot be satisfied vacuously:

    1. the stored count fell by exactly one (delegated to
       :func:`expected_storage_after`), which the sale's own proof shows a
       decrement can really happen;
    2. the row is present at the derived slot carrying the **derived** ``attr`` and
       the derived player team ``1`` -- the four executed probes each show the row
       can come out **different** from what a client asks for, so this half is a
       real constraint rather than a restatement of the request.  The bag is
       derived here from the two committed fields rather than received, so the
       comparison cannot be satisfied by handing it the row's own bag.

    The ledger is checked separately by :func:`expected_ledger`: it must equal the
    append-if-absent result exactly.
    """
    storage = expected_storage_after(store_before, store_after, item_id)
    if storage is not None:
        return storage
    if not isinstance(row_after, list) or len(row_after) != ROW_SLOTS:
        return ("the derived map slot holds %r, not the committed %d-slot row"
                % (row_after, ROW_SLOTS))
    if row_after[ROW_SLOT_ITEM] != int(item_id):
        return ("the placed row's item slot is %r, not the stored %r"
                % (row_after[ROW_SLOT_ITEM], item_id))
    if row_after[ROW_SLOT_X] != int(x) or row_after[ROW_SLOT_Y] != int(y):
        return ("the placed row records cell (%r, %r), not the derived (%r, %r)"
                % (row_after[ROW_SLOT_X], row_after[ROW_SLOT_Y], x, y))
    if row_after[ROW_SLOT_ORIENTATION] != int(orientation):
        return ("the placed row records orientation %r, not the derived %r"
                % (row_after[ROW_SLOT_ORIENTATION], orientation))
    if row_after[ROW_SLOT_STORE] != list(DERIVED_GARRISON):
        return ("the placed row's garrison slot is %r, not the derived empty list"
                % (row_after[ROW_SLOT_STORE],))
    if row_after[ROW_SLOT_PLAYER] != DERIVED_PLAYER_TEAM:
        return ("the placed row records player team %r, not the derived %d: the "
                "legacy branch never passes the client-sent playerID on"
                % (row_after[ROW_SLOT_PLAYER], DERIVED_PLAYER_TEAM))
    expected_attr = derive_attr(clicks_to_build, properties)
    if row_after[ROW_SLOT_ATTR] != expected_attr:
        return ("the placed row's attribute bag is %r, not the derived %r"
                % (row_after[ROW_SLOT_ATTR], expected_attr))
    if timestamp is not None and row_after[ROW_SLOT_TIMESTAMP] != timestamp:
        return ("the placed row records instant %r, not the derived %r"
                % (row_after[ROW_SLOT_TIMESTAMP], timestamp))
    if not is_strict_int(row_after[ROW_SLOT_TIMESTAMP]) or \
            int(row_after[ROW_SLOT_TIMESTAMP]) < 1:
        return ("the placed row's instant is %r, not a positive wall-clock "
                "reading" % (row_after[ROW_SLOT_TIMESTAMP],))
    try:
        derived_ledger = expected_ledger(ledger_before, item_id)
    except EnvelopeError as failure:
        return failure.code + ": " + str(failure)
    if list(ledger_after or []) != derived_ledger:
        return ("the purchase ledger is %r after the placement, not the derived "
                "append-if-absent %r" % (list(ledger_after or []), derived_ledger))
    return None


def divergence_sell(
    store_before: Any,
    store_after: Any,
    ledger_before: Any,
    ledger_after: Any,
    item_id: Any,
    items_before: Any,
    items_after: Any,
) -> Optional[str]:
    """The first way a sale's post-state diverges from the derivation, or None.

    One part, and it is the whole claim: the stored count fell by exactly one and
    **no other stored key moved**, **no placement was added or removed or
    changed**, and **the purchase ledger stands byte-identical** -- the sale branch
    calls ``remove_store_item`` and nothing else (NO_REFUND_NOTE), so the ledger
    is deliberately *not* touched and asserting it was would be asserting a bug.
    """
    storage = expected_storage_after(store_before, store_after, item_id)
    if storage is not None:
        return storage
    if list(ledger_after if ledger_after is not None else []) != \
            list(ledger_before if ledger_before is not None else []):
        return ("the purchase ledger moved %r -> %r; sell_stored_item writes only "
                "the storage key and never touches boughtUnits"
                % (list(ledger_before or []), list(ledger_after or [])))
    if not isinstance(items_before, Mapping) or not isinstance(items_after, Mapping):
        return "the placements are a %s/%s, not a mapping" % (
            type(items_before).__name__, type(items_after).__name__,
        )
    if sorted(items_after, key=str) != sorted(items_before, key=str):
        return ("the placement keys changed %r -> %r; a sale adds and removes none"
                % (sorted(items_before, key=str), sorted(items_after, key=str)))
    for key in items_before:
        if items_after[key] != items_before[key]:
            return ("placement row %r changed; a sale touches no placement" % key)
    return None


# ------------------------------------------------------------ the envelopes --
def build_place_envelope(
    item_id: Any,
    x: Any,
    y: Any,
    items: Mapping[Any, Any],
    orientation: Any = DERIVED_ORIENTATION,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``place_stored_item``.

    The **slot is derived here**, never accepted: ``items`` is
    ``save["maps"][0]["items"]`` as loaded before execution, and the derivation is
    the reused ``next_free_slot`` with its own ``slot_occupied`` inverse applied
    (design D2/D4).  The three dismissed arguments are sent as documented
    placeholders so the recorded batch has the branch's real argument *shape*
    while proving they are read and discarded: ``playerID`` is ``1`` because the
    row's team is always ``1``, and the two unknown booleans/integer are ``0``.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread by
    legacy code, so parity normalizes it).
    """
    value = validate_item_id(item_id)
    cell = validate_coordinates(x, y)
    facing = validate_orientation(orientation)
    slot = resolve_slot(items)
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    args = [
        slot,
        value,
        cell[0],
        cell[1],
        DERIVED_PLAYER_TEAM,
        facing,
        0,
        0,
    ]
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, PLACE_COMMAND, args, neutral_vector()]],
    }


def build_sell_envelope(
    item_id: Any, ts: Optional[int] = None
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``sell_stored_item``.

    One argument, one leaf, **no refund**: the branch reads ``args[0]`` and calls
    ``remove_store_item``, so there is no quantity, no price, and nothing else to
    send.  The neutral vector is the same boundary the placement half takes.
    """
    value = validate_item_id(item_id)
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, SELL_COMMAND, [value], neutral_vector()]],
    }