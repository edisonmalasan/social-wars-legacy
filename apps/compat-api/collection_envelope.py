#!/usr/bin/env python3
"""Derivation of the legacy collection-completion envelope and the prize model.

M8 line 5 (``collection``), the **twelfth** state-mutating surface of
Compatibility API v0 and the **first one whose grant is derived entirely from
committed content**: ``command.complete_collection`` takes a collection id and a
print-only ``bought`` flag, looks the collection's prize up in the loaded
configuration with ``get_collection_prize`` (``get_game_config.py:170-175``),
grants every entry of that bag into ``map["store"]`` through
``engine.add_store_item`` (``engine.py:70-75``), and appends the id to
``privateState["collections"]`` when it is not already there
(``command.py:504-523``).  That is the **whole** branch, and this module is the
single place where that intent becomes the legacy batch envelope, so the
executed-legacy fixture capture (``capture_collection_fixture.py``) and the
Compatibility API ``POST /v0/collection`` endpoint are checked against *one*
derivation — exactly the arrangement the eleven delivered lines already use.

**The client sends a collection id and never what it receives (design D1).**
That is the whole point of this line: the *contents* of the grant come from the
committed ``collections`` table, so no prize, item id, or quantity is ever
accepted from a request.  Any such key is ignored, which is what makes the
endpoint's post-execution proof non-tautological — it compares the granted bag
against the **committed** prize, not against a client-supplied expectation.

The one-based index (design D3)
    ``get_collection_prize`` does ``index = max(0, collection - 1)`` and then
    bounds-checks ``index < len(collections)``.  The ``collection - 1`` implies a
    **1-based** collection id, and the clamp is then reported for what it is: a
    clamp **below** the requested index, so **every** id ``<= 1`` — id ``0`` and
    every negative id — resolves to index ``0`` and therefore to the **same**
    committed prize as id ``1``.  This module reports that alias rather than
    treating id ``0`` as a distinct collection (see :data:`INDEX_RULE`,
    :data:`ALIAS_RULE`, and :data:`REJECTED_ALTERNATIVE`).

    The 1-based reading is recorded as **derived-provisional** with the
    zero-based alternative retained.  It is *corroborated by the data rather than
    merely plausible*: the stored ``config/main.json`` table carries its own
    native ``id`` column running ``'1'..'10'`` over ten **array positions**
    ``0..9``, so ``collection - 1`` maps that native id onto exactly its own
    position.  The rejected alternative — that the id space were the 0-based
    position — would make the whole committed table unreachable from any id a
    client can name, since the largest named id would select the second-to-last
    row and the last row would need id ``10``.

**No eligibility check exists, and none is implemented (design D2).**  Nothing
in the legacy source verifies that a collection's items were collected: the
committed ``item_ids`` requirement list is read by **no** branch at all, and
``privateState["collections"]`` is read in the completion branch only to decide
whether to append (``command.py:517``).  So a caller may name **any** of the ten
committed collections.  Adding a check would invent a rule the legacy server does
not have — the same refusal this project applied to ``unit_capacity``,
``training_time``, and the level curve's reward fields — and authoritative
validation belongs to a later server-authoritative milestone.

**No unit income, no cap semantics, and no experience are derived (design D5).**
The ``collect`` command is field-agnostic: the whole branch re-stamps the row's
slot-3 instant and does nothing else (``command.py:136-144``), and **no** branch
reads the item fields that would have to drive an income.  Measured over the ten
legacy root modules, ``collect_type``, ``collect_xp``, ``max_collects``,
``max_elem_vol``, and ``harvester`` have **zero** occurrences, and the single
quoted ``"collect"`` is the *branch name* at ``command.py:136``, never a field
read.  On top of that the committed content leaves nothing to derive: **0 of 429**
units record a positive ``collect``, and ``max_collects`` is ``0`` on **all 429**
units — so the cap ``building-collect`` deliberately refused has **no unit
analogue**.  ``collect_xp`` is non-zero on 427 units but is **never read**, and
the only command writing a placed row's ``attr["xp"]`` takes a **client-sent**
amount, which the delivered ``godot-unit-production`` requirement already
refuses; a collection must not reopen it.  ``harvester`` is recorded as what it
is: **not a committed content field at all** — the string occurs five times in
the stored configuration, every one of them a flag key inside the committed
``properties`` blob of unit ``1001`` Worker I, ``1039`` Worker II, ``1040``
Worker III, ``1041`` Worker IV, and ``1125`` Orc Worker, all five of which
record ``collect`` ``0``.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, and
    ``EnvelopeError`` — so every delivered derivation, its fixture, and its suite
    keeps passing untouched.  A collection completion has **no target cell and no
    footprint**, so ``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep
    the sibling modules' import shape identical (``expand_envelope`` and
    ``store_envelope`` do the same); nothing here validates a cell and that is
    not a gameplay claim.

The committed corpus target
    ``tests/saves/fresh-player.json`` records ``maps[0]["store"] == {}`` and
    ``privateState["collections"] == []``, so a completion **writes** the
    committed prize into the store and **appends** the id to the ledger: a real,
    observable, content-derived mutation with **no fabricated player state**.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  The batch carries **exactly
    one** command:
    ``[0, "complete_collection", [collection_id, 0], neutral]``.

The derived ``bought`` flag
    ``args[1]`` is read into ``bought`` and used in **one printed line only**
    (``command.py:520-523``): truthy prints ``Bought <name>``, falsy prints
    ``Completed <name>``.  Nothing is written, returned, or persisted, so the
    derivation sends ``0`` — the *completed* wording — and records that the
    choice is a **derivation**, not an observation: no executed-legacy evidence
    establishes which wording a real client produced.

No gameplay validation
    Legacy performs no ownership, state, or gameplay validation of any kind for
    this command.  It grants the committed prize to any caller, it appends the id
    to the ledger only when it is absent, and it does not care whether the
    collection's items were ever collected.  The one structural check the
    endpoint adds is **resolvability**: a collection id the committed table does
    not resolve to a row is refused before the dispatcher runs, because legacy's
    ``get_collection_prize`` returns ``None`` there and the branch's very next
    statement (``for key in prize``) raises ``TypeError`` — reporting that as a
    success would claim a grant that never happened.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

# One shared derivation.  The placement module is imported unchanged — nothing
# here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    GRID_EXTENT,
    data_field,
    in_grid,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# ------------------------------------------------------------- the command --
COMPLETE_COMMAND = "complete_collection"

# The legacy argument indexes the branch reads (``command.py:504-506``).  Both
# are positional; there is no keyword form and no third argument.
ARG_COLLECTION_ID = 0
ARG_BOUGHT = 1

# The derived ``bought`` flag: ``0`` is falsy, so the branch prints
# ``Completed <name>``.  It writes nothing anywhere.
DERIVED_BOUGHT = 0
BOUGHT_NOTE = (
    "args[1] is read into `bought` and used in ONE printed line only "
    "(command.py:520-523): truthy prints 'Bought <name>' and falsy prints "
    "'Completed <name>'. Nothing is written, returned, or persisted, so the "
    "derivation sends 0 — the COMPLETED wording — and the choice is recorded "
    "as DERIVED, never observed: no executed-legacy evidence establishes which "
    "wording a real client produced. The flag is therefore irrelevant to every "
    "post-execution proof on this route"
)

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The committed corpus target, pinned so a config or corpus drift fails a run
# instead of publishing a different fixture.
COMMITTED_COLLECTION_ID = 1
COMMITTED_COLLECTION_NAME = "Draggy Collection"
COMMITTED_PRIZE_ID = 1085
COMMITTED_PRIZE_QUANTITY = 1
COMMITTED_COLLECTION_COUNT = 10
COMMITTED_PLACEMENTS = 40
COMMITTED_RESOURCE_BEFORE = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}

# ------------------------------------------------------- the index contract --
#: The first collection id the one-based reading names, and the last one the
#: committed table resolves.  Recorded so a caller can state the reachable id
#: space without reading the table.
FIRST_COLLECTION_ID = 1
LAST_COLLECTION_ID = COMMITTED_COLLECTION_COUNT

INDEX_RULE = (
    "THE COLLECTION ID SPACE IS 1-BASED AND THE LOOKUP IS POSITIONAL. "
    "get_collection_prize (get_game_config.py:170-175) computes "
    "`index = max(0, collection - 1)`, bounds-checks `index < "
    "len(collections)` against the loaded configuration's `collections` LIST, "
    "and returns `json.loads(collections[index]['prize'])`. So the id a client "
    "names is one greater than the array position it selects. The 1-based "
    "reading is DERIVED-PROVISIONAL and is corroborated by the stored content "
    "rather than merely plausible: config/main.json stores ten rows whose own "
    "native `id` column runs '1'..'10' over the ten ARRAY POSITIONS 0..9, so "
    "`collection - 1` maps that native id onto exactly its own position. "
    "Nothing here is observed from the Flash client"
)

REJECTED_ALTERNATIVE = (
    "REJECTED: a 0-BASED id space, in which the id would BE the array position. "
    "It is rejected because it leaves the committed table unreachable: under "
    "0-based indexing the largest namable id would select the second-to-last "
    "row and the last committed collection (id '10' / Animal Collection, the "
    "only one granting a mounted unit) would need id 10 to reach. The retained "
    "alternative is kept visible here so a later reader can re-derive the "
    "choice rather than inherit it"
)

ALIAS_RULE = (
    "THE CLAMP IS AN ALIAS, REPORTED NOT HIDDEN. `max(0, collection - 1)` "
    "clamps BELOW the requested index, so EVERY collection id <= 1 — id 0 and "
    "every negative id — resolves to index 0 and therefore to the SAME committed "
    "prize as id 1 (Draggy Collection, unit 1085 Metal Draggy). In particular "
    "COLLECTION ID 0 AND COLLECTION ID 1 RESOLVE TO THE SAME PRIZE, and this "
    "contract never presents id 0 as a distinct collection. The alias is a "
    "recorded legacy-contract fact, NOT permission to widen the route: the "
    "grant contents stay content-derived, because the aliased ids all select a "
    "genuine committed row rather than manufacturing one"
)

#: The largest id the clamp leaves **unchanged**, i.e. the smallest id whose
#: ``collection - 1`` is already a non-negative index.  Collection id 1 is the
#: boundary: it is not clamped, while every id **below** it is.
UNCLAMPED_FLOOR = 1

#: The recorded refusals' machine codes.
REASON_INVALID_COLLECTION_ID = "invalid_collection_id"
REASON_UNKNOWN_COLLECTION_ID = "unknown_collection_id"
REASON_INVALID_PRIZE = "invalid_prize"

# --------------------------------------------------- the recorded absences --
NO_ELIGIBILITY_CHECK = (
    "NO ELIGIBILITY CHECK IS PERFORMED BY THE LEGACY SERVER AND NONE IS "
    "IMPLEMENTED HERE. get_collection_prize clamps the index and bounds-checks "
    "it against the committed table, and complete_collection (command.py:504-"
    "523) never looks at the caller's collection state: the only read of "
    "privateState['collections'] in the whole legacy source is the append-if-"
    "absent test at command.py:517, and the committed `item_ids` requirement "
    "list is read by NO branch at all. So a caller may name ANY of the ten "
    "committed collections and receives whatever that collection genuinely "
    "grants. Adding a check would invent a rule the legacy server does not have "
    "(design D2): the recorded absence of a check is a property of the legacy "
    "contract, not permission to invent one, and authoritative validation "
    "belongs to a later server-authoritative milestone"
)

NO_UNIT_INCOME = (
    "NO UNIT INCOME AND NO COLLECTION PAYOUT ARE DERIVED. The `collect` "
    "command is field-agnostic: the whole branch looks the row up, stamps "
    "item[3] with the wall clock, prints a name, and writes NOTHING else "
    "(command.py:136-144). Measured over the ten legacy root modules, "
    "`collect_type`, `collect_xp`, `max_collects`, `max_elem_vol`, and "
    "`harvester` have ZERO occurrences and the single quoted \"collect\" is the "
    "BRANCH NAME at command.py:136, never a field read — so all five committed "
    "collect fields have zero legacy consumers, the fourth and fifth such "
    "fields in this project after unit_capacity (M8 line 2), training_time "
    "(M8 line 4), and the level curve's unread reward fields (M7's XP line). "
    "On top of that the content leaves nothing to derive: 0 of 429 committed "
    "units record a positive `collect` (every one of them records 0), against "
    "51 of the 470 committed buildings. This contract therefore computes NO "
    "income, NO payout, and NO collection reward for a unit (design D5)"
)

NO_CAP_SEMANTICS = (
    "NO CAP SEMANTICS ARE INTERPRETED. `max_collects` is 0 on ALL 429 "
    "committed units, so there is NO committed unit cap to interpret at all: "
    "the cap the delivered building-collect line deliberately REFUSED (a "
    "non-zero committed cap, because nothing in the repository says whether it "
    "limits one collection, a daily total, or a lifetime output) has NO UNIT "
    "ANALOGUE. On buildings the field takes exactly three values (0 on 459, 25 "
    "on 9, 100 on 2) and is still read by no branch. The recorded ABSENCE is "
    "stated as an absence and never read as permission to set a threshold "
    "(design D5)"
)

NO_EXPERIENCE_AWARD = (
    "NO EXPERIENCE IS AWARDED, GRANTED, OR COMPUTED. `collect_xp` is never "
    "read: it is non-zero on 427 of the 429 committed units (0 on 2, 1 on 37, "
    "2 on 159, 3 on 211, 4 on 8, 5 on 12), and the only command that writes a "
    "placed row's attr['xp'] is `add_xp_unit` (command.py:322-343), which "
    "creates nothing and takes its amount from a CLIENT ARGUMENT — already "
    "refused by the delivered godot-unit-production requirement. A collection "
    "completion does not reopen that refusal: this contract awards nothing, "
    "and the committed corpus carries attr['xp'] on 0 of its 40 placed rows "
    "(design D5)"
)

HARVESTER_RECORD = (
    "harvester is NOT A COMMITTED CONTENT FIELD AT ALL. The string occurs "
    "exactly FIVE times in the stored configuration and every one of them is a "
    "flag key inside a committed `properties` blob, never a field of its own: "
    "unit 1001 Worker I, 1039 Worker II, 1040 Worker III, 1041 Worker IV, and "
    "1125 Orc Worker. All five record `collect` 0, so the 'harvester' set is "
    "disjoint from any positive collect amount — and it is also disjoint from "
    "the legacy source, which contains zero occurrences of the string. This "
    "corrects the committed investigation's framing of harvester as a "
    "committed item field carrying a positive value on five units: it is a "
    "properties flag on five units, with no value at all"
)

#: The three refusals, as one machine-readable list, in the order the delta's
#: requirement names them.
REFUSALS = (
    {
        "refusal": "unit_income",
        "implemented": False,
        "rule": NO_UNIT_INCOME,
    },
    {
        "refusal": "cap_semantics",
        "implemented": False,
        "rule": NO_CAP_SEMANTICS,
    },
    {
        "refusal": "experience_award",
        "implemented": False,
        "rule": NO_EXPERIENCE_AWARD,
    },
)

#: The three committed collect fields whose content is recorded and never
#: applied, with the measured per-domain coverage.  A reader who wants a payout
#: rule out of them must bring evidence the legacy contract does not contain.
COLLECT_FIELDS = (
    {
        "field": "collect",
        "legacy_reads": 0,
        "read_note": "the only quoted \"collect\" in the legacy source is the "
                     + "BRANCH NAME at command.py:136; there is no [\"collect\"] "
                     + "subscript and no .get(\"collect\") anywhere",
        "units_positive": 0,
        "units_of": 429,
        "units_carried": 429,
        "buildings_positive": 51,
        "buildings_of": 470,
        "buildings_carried": 470,
    },
    {
        "field": "collect_type",
        "legacy_reads": 0,
        "read_note": "zero occurrences across the ten legacy root modules",
        "units_positive": 0,
        "units_of": 429,
        "units_carried": 429,
        "buildings_positive": 0,
        "buildings_of": 470,
        "buildings_carried": 470,
        "note": "carried by every committed item and reading as a real "
                + "resource letter, so it looks like a rule; it has no consumer",
    },
    {
        "field": "collect_xp",
        "legacy_reads": 0,
        "read_note": "zero occurrences across the ten legacy root modules",
        "units_positive": 427,
        "units_of": 429,
        "units_carried": 429,
        "buildings_positive": 53,
        "buildings_of": 470,
        "buildings_carried": 470,
    },
    {
        "field": "max_collects",
        "legacy_reads": 0,
        "read_note": "zero occurrences across the ten legacy root modules",
        "units_positive": 0,
        "units_of": 429,
        "units_carried": 429,
        "buildings_positive": 11,
        "buildings_of": 470,
        "buildings_carried": 470,
        "note": "0 on every unit and on 459 of the 470 buildings (25 on 9, 100 "
                + "on 2); the non-zero building values are the caps "
                + "building-collect refuses to interpret",
    },
    {
        "field": "max_elem_vol",
        "legacy_reads": 0,
        "read_note": "zero occurrences across the ten legacy root modules",
        "units_positive": 5,
        "units_of": 429,
        "units_carried": 429,
        "buildings_positive": 39,
        "buildings_of": 470,
        "buildings_carried": 470,
    },
)

# ---------------------------------------------------- the acquisition route --
#: The **only** content-derived acquisition and row-entry route the legacy
#: server has.  It is the tenth of the eleven storage call sites the delivered
#: ``production`` line measured (``command.py:229, 263, 460, 479, 513, 716``
#: among them) and the **sole** one whose ids come from committed content; the
#: five that place a row on the map all take the id from a client argument or
#: off an existing garrison row.
CONTENT_DERIVED_ROUTES = (
    {
        "branch": COMPLETE_COMMAND,
        "site": "command.py:513",
        "call": "add_store_item",
        "input": "committed content: the collection's own `prize` bag",
        "classification": "content-derived",
        "implemented": True,
        "note": "the ONE route whose stored ids come from committed content: "
                + "`get_collection_prize(collection_id)` returns "
                + "`json.loads(collections[index]['prize'])` and the branch "
                + "stores every entry of it. This line implements this route "
                + "and no other",
    },
)

#: The routes recorded by the delivered `godot-unit-production` capability as
#: unvalidated client-sent lists, restated here so the classification is
#: auditable in one place.  **None is implemented by this line** and no request
#: is issued for any of them.
CLIENT_SUPPLIED_ROUTES = (
    {
        "branch": "buy_offer_pack",
        "site": "command.py:716",
        "input": "client args[1], a JSON array of ids",
        "classification": "client-supplied",
        "implemented": False,
        "note": "reads `package_id` and never uses it, then json.loads a "
                + "client-sent array with NO lookup into the committed "
                + "offer_packs table",
    },
    {
        "branch": "buy_stored_item_cash",
        "site": "command.py:479",
        "input": "client args[0], one id",
        "classification": "client-supplied",
        "implemented": False,
        "note": "the same shape with a single client-sent id stored with no "
                + "check at all",
    },
)

ACQUISITION_IMPLEMENTED = True
ACQUISITION_NOTE = (
    "EXACTLY ONE ACQUISITION ROUTE IS CONTENT-DERIVED AND IT IS THIS ONE. "
    "`complete_collection` stores ids that come out of the committed "
    "`collections` table, so the server decides what a caller receives; the two "
    "plausible unit sources recorded by the delivered godot-unit-production "
    "capability (`buy_offer_pack` and `buy_stored_item_cash`) are "
    "unvalidated CLIENT-SENT lists, and this line implements NEITHER of them, "
    "issues NO request for either, and treats no client-supplied item id, "
    "package id, or item list as authorising. That is the completion the "
    "production line's acquisition finding needed: the finding is COMPLETE, not "
    "contradicted — a committed unit IS obtainable, and only through this one "
    "route"
)

#: The route this endpoint does NOT offer, recorded because the naming
#: distinction is what a reader would otherwise miss: it appends an id and
#: grants NOTHING.
NOT_ACQUISITION = (
    "`unit_collections_completed` (command.py:482-489) calls "
    "engine.unit_collection_complete, which only APPENDS an id to "
    "privateState['unitCollectionsCompleted'] (engine.py:91-94) and grants "
    "nothing at all. It is a unit COLLECTION TRACKER, a different concept from "
    "the `collections` table this line completes, and it is not an acquisition "
    "route. The committed `unit_collection_categories` table (20 rows) is read "
    "by no branch either, and `collect_mission` (command.py:430) writes "
    "`idCurrentMission` and a timestamp and is unrelated to items"
)

__all__ = [
    "ACQUISITION_IMPLEMENTED",
    "ACQUISITION_NOTE",
    "ALIAS_RULE",
    "ARG_BOUGHT",
    "ARG_COLLECTION_ID",
    "BOUGHT_NOTE",
    "CLIENT_SUPPLIED_ROUTES",
    "COLLECT_FIELDS",
    "COMMITTED_COLLECTION_COUNT",
    "COMMITTED_COLLECTION_ID",
    "COMMITTED_COLLECTION_NAME",
    "COMMITTED_PLACEMENTS",
    "COMMITTED_PRIZE_ID",
    "COMMITTED_PRIZE_QUANTITY",
    "COMMITTED_RESOURCE_BEFORE",
    "COMPLETE_COMMAND",
    "CONTENT_DERIVED_ROUTES",
    "DERIVED_BOUGHT",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "FIRST_COLLECTION_ID",
    "GRID_EXTENT",
    "HARVESTER_RECORD",
    "INDEX_RULE",
    "LAST_COLLECTION_ID",
    "NOT_ACQUISITION",
    "NO_CAP_SEMANTICS",
    "NO_ELIGIBILITY_CHECK",
    "NO_EXPERIENCE_AWARD",
    "NO_UNIT_INCOME",
    "REASON_INVALID_COLLECTION_ID",
    "REASON_INVALID_PRIZE",
    "REASON_UNKNOWN_COLLECTION_ID",
    "REJECTED_ALTERNATIVE",
    "REFUSALS",
    "RESOURCE_VECTOR_SLOTS",
    "UNCLAMPED_FLOOR",
    "alias_of",
    "build_envelope",
    "clamped_index",
    "data_field",
    "expected_grant",
    "expected_ledger",
    "expected_store",
    "in_grid",
    "is_strict_int",
    "ledger_growth",
    "neutral_vector",
    "parse_data_field",
    "parse_prize",
    "payload_json",
    "prize_entries",
    "project_prize",
    "table_length",
    "table_row",
    "validate_collection_id",
    "validate_vector",
]


# ------------------------------------------------------------ the vocabulary --
def table_length(table: Any) -> int:
    """The committed ``collections`` table's length, or a refusal.

    ``-1`` is not a guess: the module refuses with
    :class:`EnvelopeError` ``invalid_prize`` when the loaded configuration
    carries no ``collections`` list at all, so an unreadable table is a named
    failure and never a table of zero rows.
    """
    if not isinstance(table, (list, tuple)):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "the loaded configuration's collections table is %s, not a list"
            % type(table).__name__,
        )
    return len(table)


def table_row(table: Any, index: int) -> Optional[Mapping[str, Any]]:
    """One committed collection row by **array position**, verbatim, or ``None``.

    ``None`` means exactly *"the committed table has no row at this position"* —
    the state legacy's ``index < len(collections)`` bounds-check also reports.
    A row that is not a mapping reaches the caller as ``None`` rather than being
    coerced, so a configuration drift fails closed instead of indexing into
    something unreadable.
    """
    if not isinstance(table, (list, tuple)):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "the loaded configuration's collections table is %s, not a list"
            % type(table).__name__,
        )
    if not is_strict_int(index) or index < 0 or index >= len(table):
        return None
    row = table[index]
    return row if isinstance(row, Mapping) else None


def validate_collection_id(collection_id: Any) -> int:
    """Check a client-supplied collection id structurally, or refuse it.

    Only a **strict** integer is legal.  A ``bool`` is an ``int`` in Python and
    would subtract as ``0`` or ``1``; a float would produce a fractional index
    that legacy's ``collections[index]`` would reject with a ``TypeError``; and a
    string would raise out of ``collection - 1`` itself.  All three are refused
    here so a shape legacy would crash on is answered with a named error before
    the dispatcher runs.
    """
    if not is_strict_int(collection_id):
        raise EnvelopeError(
            REASON_INVALID_COLLECTION_ID,
            "collection_id must be an integer, got %s" % type(collection_id).__name__,
        )
    return int(collection_id)


def clamped_index(collection_id: Any, table_size: Any) -> int:
    """The **one-based** index with the legacy clamp, as a plain integer.

    Reproduces ``max(0, collection - 1)`` exactly, for any integer id including
    ``0`` and every negative id.  The clamp is reported by :func:`project_prize`
    as an **alias** rather than silently absorbed here.
    """
    value = validate_collection_id(collection_id)
    if not is_strict_int(table_size):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "table_size must be an integer, got %s" % type(table_size).__name__,
        )
    return max(0, value - 1)


def is_aliased(collection_id: Any) -> bool:
    """Whether the legacy clamp actually moved this id's index.

    True exactly when ``collection_id < 1``, which is when ``collection - 1`` is
    **not** a non-negative index and ``max(0, ...)`` replaces it with ``0``.
    Collection id ``1`` is the boundary and is **not** clamped: ``1 - 1 == 0`` is
    already the index its own committed row sits at.  This is the
    machine-readable form of :data:`ALIAS_RULE`.
    """
    return validate_collection_id(collection_id) < FIRST_COLLECTION_ID


def alias_of(collection_id: Any) -> int:
    """The id a clamped id resolves to, i.e. ``1``.

    Every id at or below the clamp floor resolves to index ``0``, which is the
    first committed row — the one named by collection id ``1``.
    """
    validate_collection_id(collection_id)
    return FIRST_COLLECTION_ID if is_aliased(collection_id) else int(collection_id)


def parse_prize(raw: Any) -> Dict[str, int]:
    """The committed ``prize`` field as a ``{item id text: quantity}`` mapping.

    The stored configuration keeps ``prize`` as a **JSON-encoded string** and
    legacy calls ``json.loads`` on it (``get_game_config.py:174``), so the same
    decode happens here.  An already-parsed mapping is accepted too, which is
    what makes this usable against either representation.

    The bag is returned with its **keys as the committed strings** — ``"1085"``,
    never ``1085`` — because that is the form ``map["store"]`` is keyed by and
    the form the post-execution proof compares.  Quantities must be strict
    integers: ``add_store_item`` adds them, and a float or string would make the
    endpoint's "granted exactly the committed quantity" claim a comparison
    against a coerced number.  An empty bag is refused: every committed
    collection carries exactly one entry, so an empty one is a content drift,
    never a legitimate "grants nothing".
    """
    parsed = raw
    if isinstance(parsed, (str, bytes)):
        try:
            parsed = json.loads(parsed)
        except ValueError as error:
            raise EnvelopeError(
                REASON_INVALID_PRIZE,
                "the committed prize is not valid JSON: %s" % error,
            )
    if not isinstance(parsed, Mapping):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "the committed prize must decode to a JSON object, got %s"
            % type(parsed).__name__,
        )
    bag: Dict[str, int] = {}
    for key in parsed:
        amount = parsed[key]
        if not is_strict_int(amount):
            raise EnvelopeError(
                REASON_INVALID_PRIZE,
                "the committed prize quantity for %r is %r, not an integer"
                % (str(key), amount),
            )
        bag[str(key)] = int(amount)
    if not bag:
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "the committed prize is empty: every committed collection grants "
            "exactly one item, so an empty bag is a content drift",
        )
    return bag


# --------------------------------------------------------- derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D1/D5).

    A collection's price would be a **client-sent** delta:
    ``do_command`` applies the request's per-command vector before the branch
    (``command.py:40``, ``engine.py:251-271``), so any cost a client attached
    would be a client-trusted mint or burn.  The committed configuration records
    no completion price, so the only honest vector is the neutral one, and a
    fresh list is returned on every call so a caller can never mutate the
    derivation for the next one.  **No completion cost is claimed** in either
    direction — reproducing a client-sent price would invent an economy, and
    refusing to price a completion the legacy server prices not at all is the
    recorded boundary.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal here.  A positive entry would be a
    client-trusted **mint** and a negative one a client-trusted **burn** under
    legacy's ``max(current + delta, 0)`` clamp, and either would make the
    endpoint's "nothing moved" proof fail in a way that looks like a bug.
    Refusing anything but zero here is what forecloses the smuggling: the
    derivation cannot express it, so the endpoint cannot send it.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be an integer, got %r"
                % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d is %r: a completion moves no "
                "resource, so only the neutral all-zero vector is derivable"
                % (index, value),
            )
    return list(vector)


# -------------------------------------------------------- the prize model --
def prize_entries(prize: Any) -> List[Dict[str, Any]]:
    """The committed bag as a **sorted** list of ``{item_id, quantity}`` records.

    Sorted by the committed string item id so the projection is deterministic:
    ``map["store"]`` is a JSON object whose key order follows insertion, and an
    unsorted list would make the endpoint's response bytes depend on Python's
    dict ordering rather than on the content.  The values are the committed
    quantities **verbatim**.
    """
    bag = parse_prize(prize)
    return [
        {"item_id": key, "quantity": bag[key]}
        for key in sorted(bag, key=lambda text: int(text) if text.isdigit() else text)
    ]


def project_prize(table: Any, collection_id: Any) -> Dict[str, Any]:
    """The **read-only** projection of one collection id, verbatim.

    Returns
        ``{ok, reason, error, resolved, collection_id, requested_index, index,
        clamped, aliased, alias_of, name, id_column, prize, entries, item_count,
        quantity_total}``

    ``resolved`` is ``False`` — with ``collection_id`` **kept intact** — when the
    one-based index lands outside the committed table.  That is the
    unresolvable case, and the contract substitutes **nothing**: no default
    prize, no clamping to the last row, no dropped id.

    ``clamped`` records whether ``max(0, collection - 1)`` actually moved the
    requested index, and ``aliased`` records the stronger consequence recorded
    in :data:`ALIAS_RULE`: id ``0`` and every negative id resolve to the same
    committed prize as id ``1``.  ``alias_of`` names that id so no caller can
    present an aliased id as a distinct collection.

    Every committed value is reported **verbatim**: the row's own ``name``, its
    own native ``id`` column, and its ``prize`` bag with its committed string
    keys.  Nothing is scaled, rounded, defaulted, or reinterpreted.
    """
    try:
        value = validate_collection_id(collection_id)
    except EnvelopeError as failure:
        return {
            "ok": False,
            "reason": failure.code,
            "error": str(failure),
            "resolved": False,
            "collection_id": collection_id,
            "requested_index": None,
            "index": None,
            "clamped": False,
            "aliased": False,
            "alias_of": None,
            "name": "",
            "id_column": "",
            "prize": {},
            "entries": [],
            "item_count": 0,
            "quantity_total": 0,
        }
    size = table_length(table)
    requested = value - 1
    index = max(0, requested)
    aliased = index != requested
    row = table_row(table, index)
    if row is None:
        return {
            "ok": False,
            "reason": REASON_UNKNOWN_COLLECTION_ID,
            "error": "collection_id %d resolves to index %d, outside the "
                     % (value, index) + "%d-entry committed collections table"
                     % size,
            "resolved": False,
            "collection_id": value,
            "requested_index": requested,
            "index": index,
            "clamped": aliased,
            "aliased": aliased,
            "alias_of": FIRST_COLLECTION_ID if aliased else None,
            "name": "",
            "id_column": "",
            "prize": {},
            "entries": [],
            "item_count": 0,
            "quantity_total": 0,
        }
    try:
        entries = prize_entries(row.get("prize"))
    except EnvelopeError as failure:
        return {
            "ok": False,
            "reason": failure.code,
            "error": str(failure),
            "resolved": False,
            "collection_id": value,
            "requested_index": requested,
            "index": index,
            "clamped": aliased,
            "aliased": aliased,
            "alias_of": FIRST_COLLECTION_ID if aliased else None,
            "name": str(row.get("name", "")),
            "id_column": str(row.get("id", "")),
            "prize": {},
            "entries": [],
            "item_count": 0,
            "quantity_total": 0,
        }
    bag = {str(entry["item_id"]): int(entry["quantity"]) for entry in entries}
    return {
        "ok": True,
        "reason": "",
        "error": "",
        "resolved": True,
        "collection_id": value,
        "requested_index": requested,
        "index": index,
        "clamped": aliased,
        "aliased": aliased,
        "alias_of": FIRST_COLLECTION_ID if aliased else None,
        "name": str(row.get("name", "")),
        "id_column": str(row.get("id", "")),
        "prize": bag,
        "entries": entries,
        "item_count": len(bag),
        "quantity_total": sum(bag.values()),
    }


# ------------------------------------------------ the post-execution proofs --
def expected_store(before_store: Any, prize: Any) -> Dict[str, int]:
    """``map["store"]`` as the committed prize makes it, or a refusal.

    Reproduces ``engine.add_store_item`` (``engine.py:70-75``) for every entry:
    an absent key is **created with** the committed quantity, and a present key
    is **incremented** by it.  Keys the committed bag does not mention are copied
    through untouched — the branch writes nothing else into the storage.
    """
    bag = parse_prize(prize)
    if not isinstance(before_store, Mapping):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "the player's storage is %s, not a mapping" % type(before_store).__name__,
        )
    out: Dict[str, int] = {}
    for key in before_store:
        out[str(key)] = before_store[key]
    for key in sorted(bag, key=lambda text: int(text) if text.isdigit() else text):
        if key in out:
            if not is_strict_int(out[key]):
                raise EnvelopeError(
                    REASON_INVALID_PRIZE,
                    "the player's stored quantity for %r is %r, not an integer"
                    % (key, out[key]),
                )
            out[key] = int(out[key]) + bag[key]
        else:
            out[key] = bag[key]
    return out


def expected_ledger(before_ledger: Any, collection_id: Any) -> Dict[str, Any]:
    """The collection ledger the branch leaves behind, and whether it grew.

    Reproduces ``command.py:517-518`` exactly: the id is appended **only when it
    is absent**, so a completion of a collection already in the ledger appends
    nothing while still granting the prize again.  That idempotence of the ledger
    (paired with a non-idempotent grant) is a real legacy behaviour rather than
    an oversight, so it is reported rather than normalised away.

    ``entries`` keeps the committed values **verbatim** — the ids the save holds,
    including the fact that they are numbers rather than text — and never
    coerces or re-sorts them.
    """
    value = validate_collection_id(collection_id)
    if not isinstance(before_ledger, list):
        raise EnvelopeError(
            REASON_INVALID_PRIZE,
            "privateState['collections'] is %s, not a list"
            % type(before_ledger).__name__,
        )
    entries = list(before_ledger)
    appended = value not in entries
    if appended:
        entries.append(value)
    return {"entries": entries, "appended": appended}


def ledger_growth(before_ledger: Any, after_ledger: Any) -> Optional[str]:
    """The first way the persisted ledger diverges from the derivation, or None.

    The second half of the endpoint's post-execution proof, kept here so the
    capture tool, the endpoint, and the offline tests all compare against **one**
    derivation instead of three hand-written checks.
    """
    if not isinstance(before_ledger, list) or not isinstance(after_ledger, list):
        return "privateState['collections'] is not a list on one side of the check"
    if len(after_ledger) < len(before_ledger):
        return "the collection ledger shrank from %d to %d entries" % (
            len(before_ledger),
            len(after_ledger),
        )
    for position, entry in enumerate(before_ledger):
        if after_ledger[position] != entry:
            return "collection ledger entry %d changed from %r to %r" % (
                position,
                entry,
                after_ledger[position],
            )
    appended = after_ledger[len(before_ledger):]
    if len(appended) > 1:
        return ("the collection ledger grew by %d entries (%r); the branch "
                "appends at most one" % (len(appended), appended))
    if appended and appended[0] in before_ledger:
        return ("the collection ledger appended %r, which it already held"
                % (appended[0],))
    return None


def expected_grant(
    before_store: Any,
    after_store: Any,
    prize: Any,
    collection_id: Any = None,
    before_ledger: Any = None,
    after_ledger: Any = None,
) -> Optional[str]:
    """The first way the persisted state diverges from the derivation, or None.

    The whole post-execution proof, as one pure comparison: the granted **id and
    quantity must equal the committed prize bag exactly** for every committed
    entry, **no other stored key may move**, and — when ``collection_id`` is
    given — the collection ledger must match :func:`expected_ledger` for **that**
    id: growing by exactly one appended id, or by nothing at all when the id was
    already there.

    Both halves are *value* comparisons against the **committed** bag.  That is
    what makes the proof non-tautological: it never compares the grant with a
    client-supplied expectation, so a client that sends ``prize``, ``item_id``, or
    ``quantity`` cannot make a wrong grant pass.

    The ledger halves are optional (``None`` skips them, and
    ``ledger_growth`` alone still runs when either side is a list) so the same
    function serves the capture tool's storage-only check and the endpoint's full
    two-part check.
    """
    expected = expected_store(before_store, prize)
    if not isinstance(after_store, Mapping):
        return "the player's storage is %s, not a mapping" % type(after_store).__name__
    after = {str(key): after_store[key] for key in after_store}
    bag = parse_prize(prize)
    numeric = lambda text: (  # noqa: E731 - a local sort key, not a public rule
        int(text) if str(text).isdigit() else str(text)
    )
    for key in sorted(expected, key=numeric):
        if key not in after:
            return ("the committed prize id %r is absent from the storage after "
                    "the completion" % (key,))
        if after[key] != expected[key]:
            return ("stored item %r is %r after the completion, not the derived "
                    "%r (the committed prize grants %r)"
                    % (key, after[key], expected[key], bag.get(key)))
    for key in sorted(after, key=numeric):
        if key in expected:
            continue
        before_value = before_store.get(key) if isinstance(before_store, Mapping) else None
        if after[key] != before_value:
            return ("the completion moved stored item %r from %r to %r, which "
                    "the committed prize never mentions"
                    % (key, before_value, after[key]))
    if before_ledger is None or after_ledger is None:
        return None
    divergence = ledger_growth(before_ledger, after_ledger)
    if divergence is not None:
        return divergence
    if collection_id is None:
        return None
    derived = expected_ledger(before_ledger, collection_id)
    if list(after_ledger) != derived["entries"]:
        return ("the collection ledger is %r after the completion, not the "
                "derived %r" % (list(after_ledger), derived["entries"]))
    return None


# ------------------------------------------------------------ the envelope --
def build_envelope(collection_id: Any, ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one collection completion.

    ``collection_id`` is the **only** client-supplied value in the whole intent,
    and the batch carries **exactly one** command and a **neutral** vector
    (design D1/D5): no prize, no item id, no quantity, no price, and no resource
    delta is expressed here, because none is derivable and none is accepted from
    a client.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread
    by legacy code, so parity normalizes it).  Raises :class:`EnvelopeError` with
    ``invalid_collection_id``, ``invalid_vector``, or ``invalid_timestamp``.
    Whether the named collection was earned, and what a completion costs, are the
    client's business by design D2/D5.
    """
    value = validate_collection_id(collection_id)
    checked = validate_vector(neutral_vector())
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
        "commands": [[0, COMPLETE_COMMAND, [value, DERIVED_BOUGHT], checked]],
    }