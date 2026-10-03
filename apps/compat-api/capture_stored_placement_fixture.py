#!/usr/bin/env python3
"""Capture the executed-legacy stored-placement fixture (contained).

Milestone M9 line 3 (``stored-item-placement``), design D1-D7.  Four recorded
transactions plus four executed probes against a disposable corpus over
``127.0.0.1:5055``.

What this capture is for
------------------------
The delivered ``godot-unit-collection`` line recorded the **grant** of a
committed collection prize into ``maps[0]["store"]`` and named the rest of the
round trip -- ``store`` -> map row -- a carried follow-up.  This capture is that
follow-up.  It is therefore the **first executed-legacy evidence that a unit
acquired from committed content reaches the map**, and it closes
``unit-collection``'s own recorded gap rather than merely adding a new one.

Why the seed route matters
--------------------------
The committed corpus records ``maps[0]["store"] == {}``, so a placement fixture
would have nothing to place.  Three routes exist to seed it and only one is
content-derived (``docs/legacy-stored-unit-placement.md`` section 5.1):

| route | client input | used here |
| --- | --- | --- |
| ``store_add_items`` | an arbitrary id list | **probes only**, never a recorded step |
| a hand-edited seed save | none | **forbidden** -- a fabricated corpus |
| ``complete_collection`` | a collection **id** | **yes** -- the prize comes from the committed table |

Every recorded step of this fixture is therefore content-derived, and no
client-sent item id list appears in a recorded transaction anywhere.

The four recorded transactions
------------------------------
1. ``login_post`` -- session fidelity; the corpus must stay byte-identical.
2. ``command_complete_collection`` with id ``1``, whose committed prize is
   exactly ``{"1085": 1}`` (unit 1085, Metal Draggy).
3. ``command_place_stored_item`` ``[41, 1085, 58, 47, 1, 0, 0, 0]`` -- the
   **derived** map slot, the derived cell, and a neutral vector.
4. ``command_complete_collection`` with id ``2``, whose committed prize is
   ``{"1062": 1}`` (unit 1062, MegaBot).
5. ``command_sell_stored_item`` ``[1062]`` -- the storage sale.

A MEASURED CORRECTION to this change's own task text
---------------------------------------------------
The task text predicted the placement would change **exactly two leaves**, "the
new row and the store key".  That number is correct for the committed
investigation, which seeded with ``store_add_items`` -- a route that appends to
``privateState["boughtUnits"]`` *at the same time* (``command.py:264``), so the
ledger already held ``1085`` and ``bought_unit_add``'s append-if-absent test
(``command.py:246`` / ``engine.py:86-89``) left it alone.

Seeding with the content-derived route instead makes the third write
**observable**: ``complete_collection`` appends to
``privateState["collections"]``, never to ``boughtUnits``, so ``boughtUnits`` is
still empty when the placement runs and the placement appends ``1085`` itself.
The executed placement therefore changes **exactly three** leaves:

    /maps/0/items/41
    /maps/0/store/1085
    /privateState/boughtUnits

Two of them are under ``maps[0]`` -- the row and the store key -- which is the
"exactly two" claim at map scope.  The capture pins **both** statements and the
manifest records the correction rather than hiding it.  No conclusion of the
investigation changes; the extra write is the very ``bought_unit_add`` call the
investigation read in the source (``command.py:246``) and could not see in the
state because its own seed had already performed it.

The four executed probes (all deliberate DIVERGENCES, never parity)
--------------------------------------------------------------------
1. placing unit ``1071``, which was **never stored** -- ``not_in_storage``;
2. placing onto map key ``1``, an **existing row** -- ``slot_occupied``;
3. placing id ``999999``, which resolves to **no committed definition** --
   ``unknown_item_id``;
4. placing at cell ``(250, -3)``, far outside the derived grid -- recorded, NOT
   refused, because it is the already-recorded M6 tile-to-cell geometry gap.

Every one of them answers ``{"result":"success"}`` with status 200 in the legacy
server, which is exactly why the modern endpoint refuses three of them and
records the fourth instead of inventing a bound.

Exit codes (identical to the sixteen delivered captures)
=======================================================
0    Success
1    Unexpected/unclassified error
2    Environment or precondition failure (including a refused derivation)
3    Port conflict: 127.0.0.1:5055 already in use
4    Legacy server failed to start, crashed, or the port stayed busy
5    A legacy request failed, returned an unexpected status, or the executed
     transaction did not match the derived envelope
6    Containment violation (working-tree bytes changed, a committed fixture
     directory changed, or the disposable corpus saves changed during server
     startup / login)
7    Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_stored_placement_fixture.py

where ``python`` denotes the pinned CPython 3.9.13 executable
(``C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe``).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collection_envelope  # noqa: E402
import placement_envelope  # noqa: E402
import stored_placement_envelope as envelope  # noqa: E402
from capture_legacy_fixtures import (  # noqa: E402
    DYNAMIC_ROOT,
    EXIT_CONTAINMENT,
    EXIT_ENVIRONMENT,
    EXIT_PORT_BUSY,
    EXIT_REQUEST,
    EXIT_SERVER,
    EXIT_WRITE,
    FRESH_PLAYER_SAVE,
    GAME_VERSION,
    LANGUAGE,
    LEGACY_HOST,
    LEGACY_PORT,
    REPO_ROOT,
    USER_KEY,
    CaptureError,
    build_disposable,
    clear_previous_fixtures,
    containment_snapshot,
    dir_group_record,
    extract_session_cookie,
    http_request,
    iso_now,
    port_is_free,
    read_tail,
    save_group_record,
    snapshot_combined,
    start_server,
    stop_server,
    wait_ready,
    write_bytes,
    write_json,
)
from hashing import sha256_bytes  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-stored-item-placement"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a corpus
# and initialize live legacy state).
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# ---------------------------------------------------------------- the pins --
SEED_COLLECTION_ID = collection_envelope.COMMITTED_COLLECTION_ID
SEED_PRIZE_ID = envelope.COMMITTED_PRIZE_ID
SEED_PRIZE_QUANTITY = envelope.COMMITTED_PRIZE_QUANTITY
SELL_COLLECTION_ID = envelope.COMMITTED_SELL_COLLECTION_ID
SELL_ITEM_ID = envelope.COMMITTED_SELL_ITEM_ID
SELL_PRIZE = dict(envelope.COMMITTED_SELL_PRIZE)
DERIVED_SLOT = envelope.COMMITTED_DERIVED_SLOT
RECORDED_CELL = envelope.COMMITTED_CELL
RECORDED_ORIENTATION = envelope.COMMITTED_ORIENTATION
UNSTORED_ITEM_ID = envelope.RECORDED_UNSTORED_ITEM_ID
UNKNOWN_ITEM_ID = envelope.RECORDED_UNKNOWN_ITEM_ID
OCCUPIED_SLOT = envelope.RECORDED_OCCUPIED_SLOT
OCCUPIED_CELL = (61, 47)
OUT_OF_GRID_CELL = envelope.RECORDED_OUT_OF_GRID_CELL
UNSTORED_CELL = (60, 47)
UNKNOWN_CELL = (66, 47)
# The id probe 2 overwrites index 1 with.  It is deliberately NOT a collection
# prize: `store_add_items` is used to hold it, which is the route the design
# defers and permits in probes only.
OCCUPIED_ITEM_ID = 1055

FIXTURE_EXPECTED_PLACEMENTS = envelope.COMMITTED_PLACEMENTS
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = dict(
    envelope.COMMITTED_RESOURCE_BEFORE
)

ITEMS_FIELD = "items"
STORE_FIELD = "store"
LEDGER_FIELD = "boughtUnits"
COLLECTIONS_FIELD = "collections"

ROW_POINTER = "/maps/0/items/%d" % DERIVED_SLOT
STORE_KEY_POINTER = "/maps/0/store/%d" % SEED_PRIZE_ID
LEDGER_POINTER = "/privateState/boughtUnits"
SELL_STORE_KEY_POINTER = "/maps/0/store/%d" % SELL_ITEM_ID

# The measured changed-leaf set of the placement, pinned leaf by leaf.  The
# container path of a list that GREW is the list itself, because
# ``leaf_differences`` only walks element-wise when the lengths match; this is
# the same convention the collection capture documents.
PLACEMENT_CHANGED_LEAVES = [ROW_POINTER, STORE_KEY_POINTER, LEDGER_POINTER]
# ... of which exactly two are map-level writes.
PLACEMENT_MAP_CHANGED_LEAVES = [ROW_POINTER, STORE_KEY_POINTER]
SALE_CHANGED_LEAVES = [SELL_STORE_KEY_POINTER]

TARGET_RULE = (
    "the committed fresh-player corpus records maps[0]['store'] == {} and "
    "privateState['boughtUnits'] == [], so a placement fixture has nothing to "
    "place unless the seed route is chosen deliberately. Collection 1 is chosen "
    "because its committed prize is exactly {'1085': 1} (unit 1085 Metal Draggy) "
    "and collection 2 because its committed prize is exactly {'1062': 1} (unit "
    "1062 MegaBot): both seeds are therefore CONTENT-DERIVED, no client-sent "
    "item id list appears in any recorded transaction, and no player state is "
    "fabricated"
)

PROBE_SETUP_NOTE = (
    "two `store_add_items` batches seed the two probes that need an item in "
    "storage. That branch is an UNVALIDATED client-sent item list "
    "(command.py:258-266) and is deliberately deferred by this change's design, "
    "so it is used for PROBE PREPARATION only and never in a recorded "
    "transaction. Probe 2's seed id 1055 is not a collection prize"
)

# Committed fixtures that must be byte-identical across this run: every already
# committed `godot-*` fixture directory.
PROTECTED_FIXTURES = (
    ("tests/fixtures/godot-compatibility-boot", "godot-compatibility-boot"),
    ("tests/fixtures/godot-building-placement", "godot-building-placement"),
    ("tests/fixtures/godot-item-purchase", "godot-item-purchase"),
    ("tests/fixtures/godot-building-move", "godot-building-move"),
    ("tests/fixtures/godot-building-sell", "godot-building-sell"),
    ("tests/fixtures/godot-building-store", "godot-building-store"),
    ("tests/fixtures/godot-building-upgrade", "godot-building-upgrade"),
    ("tests/fixtures/godot-building-construction", "godot-building-construction"),
    ("tests/fixtures/godot-building-collect", "godot-building-collect"),
    ("tests/fixtures/godot-building-expand", "godot-building-expand"),
    ("tests/fixtures/godot-building-xp", "godot-building-xp"),
    ("tests/fixtures/godot-unit-queues", "godot-unit-queues"),
    ("tests/fixtures/godot-unit-collection", "godot-unit-collection"),
    ("tests/fixtures/godot-research", "godot-research"),
    ("tests/fixtures/godot-quests", "godot-quests"),
    ("tests/fixtures/godot-tutorial", "godot-tutorial"),
)

# The executed-legacy probes this capture runs itself, after the recorded steps
# and on the same live server.  They are recorded in the manifest rather than as
# steps because they are evidence for the contract's GUARANTEES, not recorded
# transactions of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "modern_refusal": envelope.REASON_NOT_IN_STORAGE,
        "question": (
            "what does the legacy server do when the client places a committed "
            "unit it never acquired?"
        ),
        "commands": [
            "place_stored_item([%d, %d, %d, %d, 1, 0, 0, 0]) with an EMPTY store"
            % (envelope.COMMITTED_DERIVED_SLOT + 1, UNSTORED_ITEM_ID,
               UNSTORED_CELL[0], UNSTORED_CELL[1]),
        ],
        "established": (
            "`remove_store_item`'s conditional (`if itemstr in map['store']`, "
            "engine.py:78-79) makes an absent item a SILENT NO-OP, and the branch "
            "then places the row and appends the id to boughtUnits anyway "
            "(command.py:244-246)"
        ),
        "modern_rule": (
            "the endpoint refuses not_in_storage with 409 and changes nothing, "
            "because a modern client must never be able to place a unit it does "
            "not own. Item %d is a real committed placeable unit, so 'never "
            "stored' and 'unknown id' are two DISTINCT refusals, not one check "
            "under two spellings" % UNSTORED_ITEM_ID
        ),
        "why_it_matters": (
            "it is the executed evidence for the not_in_storage refusal. Without "
            "it the refusal could be vacuously true, because the committed "
            "corpus can never place an item that is also absent from storage"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 2,
        "modern_refusal": envelope.REASON_SLOT_OCCUPIED,
        "question": (
            "what does the legacy server do when the client names a map key an "
            "existing row already holds?"
        ),
        "commands": [
            "store_add_items([[%d]])" % OCCUPIED_ITEM_ID,
            "place_stored_item([%d, %d, %d, %d, 1, 0, 0, 0]) -- index %d holds "
            "the Command Center" % (OCCUPIED_SLOT, OCCUPIED_ITEM_ID,
                                    OCCUPIED_CELL[0], OCCUPIED_CELL[1],
                                    OCCUPIED_SLOT),
        ],
        "established": (
            "`map['items'][str(index)] = [...]` is a plain ASSIGNMENT with no "
            "occupancy test (engine.py:31): the existing row is DESTROYED, the "
            "row COUNT does not change, and the server answers success with no "
            "resource movement. This is the most serious of the four vectors and "
            "the one a two-part post-state proof must be built to catch, because "
            "a count-based check cannot see it"
        ),
        "modern_rule": (
            "the endpoint never accepts a slot at all -- it derives the smallest "
            "absent positive integer -- and the named inverse `slot_occupied` is "
            "a 409 guard against the derived slot itself colliding. The typed "
            "client cannot reach that guard on an honest save, which is why the "
            "endpoint suite exercises it against an injected key-view conflict"
        ),
        "why_it_matters": (
            "it is the executed evidence that a placement proof must compare "
            "VALUES and not counts: this probe changes five leaves and zero of "
            "them is a key-set change"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 3,
        "modern_refusal": envelope.REASON_UNKNOWN_ITEM_ID,
        "question": (
            "what does the legacy server do when the client names an id that "
            "resolves to no committed definition anywhere?"
        ),
        "commands": [
            "place_stored_item([%d, %d, %d, %d, 1, 0, 0, 0])"
            % (envelope.COMMITTED_DERIVED_SLOT + 6, UNKNOWN_ITEM_ID,
               UNKNOWN_CELL[0], UNKNOWN_CELL[1]),
        ],
        "established": (
            "id %d is in no normalized table and in no config section; "
            "`get_attribute_from_item_id` returns nothing for it, so the row is "
            "placed with an EMPTY attribute bag and the id is appended to "
            "boughtUnits as a purchased unit" % UNKNOWN_ITEM_ID
        ),
        "modern_rule": (
            "the endpoint resolves the id against the loaded committed "
            "configuration first and refuses unknown_item_id with 409, because a "
            "row for an unresolvable id would be derived from no committed "
            "content at all. This is a DIFFERENT refusal from item_not_placeable, "
            "which fires on a row that resolves but carries neither derived "
            "field; the split is measured unreachable from the other on the "
            "committed content (0 of 778 loaded rows and 0 of 900 normalized "
            "items fail the second)"
        ),
        "why_it_matters": (
            "it is the executed evidence for the content-resolution refusal, and "
            "it shows the legacy server happily manufactures a row for an id no "
            "table has ever heard of"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 4,
        "modern_refusal": None,
        "question": (
            "does the legacy server validate the target cell against any grid?"
        ),
        "commands": [
            "store_add_items([[%d]])" % SEED_PRIZE_ID,
            "place_stored_item([%d, %d, %d, %d, 1, 0, 0, 0])"
            % (envelope.COMMITTED_DERIVED_SLOT + 2, SEED_PRIZE_ID,
               OUT_OF_GRID_CELL[0], OUT_OF_GRID_CELL[1]),
        ],
        "established": (
            "cell (%d, %d) is stored VERBATIM on the row, outside the derived "
            "0..99 grid on both axes, and the server answers success. There is "
            "no bounds check and no cell-occupancy check anywhere on this path"
            % (OUT_OF_GRID_CELL[0], OUT_OF_GRID_CELL[1])
        ),
        "modern_rule": (
            "RECORDED, NOT REFUSED. Refusing it would fabricate a bound the "
            "oracle does not have: tile-to-cell geometry is the already-recorded "
            "M6 gap and needs new evidence, not a derivation. The endpoint "
            "therefore stores the cell verbatim and reports "
            "`geometry.bounds_refused == false` in every success response, which "
            "makes the gap mechanical rather than an oversight. Authoritative "
            "bounds validation belongs to Server v1 / M13"
        ),
        "why_it_matters": (
            "it is the fourth recorded probe and the only one the endpoint does "
            "NOT refuse, so recording it is what keeps the refusal list honest: "
            "three deliberate divergences and one recorded gap"
        ),
        "executed_in_this_capture": True,
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5,
                         "cash": 6, "mana": 7}

# The map fields that hold a slot of the 8-slot vector.  ``cash`` and ``mana``
# live outside the map (``playerInfo`` / ``privateState``), so they are absent
# here by construction.
MAP_RESOURCE_FIELDS = ("xp", "gold", "wood", "oil", "steel")


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The stored legacy configuration, or a refusal.

    Read directly from the repository (never by importing a legacy module: doing
    so would chdir into a corpus and initialize live legacy state).
    """
    try:
        with CONFIG_MAIN.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "cannot read the committed configuration %s: %s" % (CONFIG_MAIN, error),
        )
    if not isinstance(document, dict):
        raise CaptureError(
            EXIT_ENVIRONMENT, "the committed configuration is not a JSON object"
        )
    return document


def config_item(item_id: int) -> Optional[Dict[str, Any]]:
    """The stored configuration row for ``item_id``, or ``None``."""
    for row in config_document().get("items", []):
        if isinstance(row, dict) and str(row.get("id")) == str(item_id):
            return row
    return None


def config_name(item_id: int) -> str:
    """The stored item's committed name, or ``""``."""
    row = config_item(item_id)
    return str(row.get("name", "")) if row else ""


def config_type(item_id: int) -> str:
    """The stored item's committed ``type`` (``u``/``b``/``l``), or ``""``."""
    row = config_item(item_id)
    return str(row.get("type", "")) if row else ""


def committed_pair(item_id: int) -> Tuple[Any, Any]:
    """The raw ``(clicks_to_build, properties)`` pair the derivation reads.

    Read from the RAW stored configuration, because that is the representation
    ``engine.map_add_item`` parses (``json.loads(properties)`` at engine.py:21),
    so the capture's verification compares against exactly what legacy read.
    """
    row = config_item(item_id)
    if row is None:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed configuration carries no item row for id %d" % item_id,
        )
    return (row.get(envelope.CLICK_TO_BUILD_FIELD),
            row.get(envelope.PROPERTIES_FIELD))


# ------------------------------------------------------------ sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact sent
    bytes; this keeps the record secret-free even if that placeholder ever
    changes.  The field is rebuilt with
    :func:`placement_envelope.data_field`, so the digest stays valid against the
    recorded payload and a reader can verify it.
    """
    batch = placement_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if batch.get(key):
            batch[key] = REDACTED
            changed = True
    if not changed:
        return data
    return placement_envelope.data_field(batch)


# ----------------------------------------------------------------- records --
def canonical_save(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise CaptureError(EXIT_REQUEST, "the persisted save is not a JSON object")
    return document


def save_bytes_sha(document: Dict[str, Any]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return sha256_bytes(payload)


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven stored resource values the legacy code maintains."""
    return {
        "xp": int(document["maps"][0]["xp"]),
        "gold": int(document["maps"][0]["gold"]),
        "wood": int(document["maps"][0]["wood"]),
        "oil": int(document["maps"][0]["oil"]),
        "steel": int(document["maps"][0]["steel"]),
        "cash": int(document["playerInfo"]["cash"]),
        "mana": int(document["privateState"]["mana"]),
    }


def leaf_differences(before: Any, after: Any) -> List[str]:
    """Every JSON pointer whose value differs between two documents."""
    collected: List[str] = []

    def walk(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                child = "%s/%s" % (path, key)
                if key not in left or key not in right:
                    collected.append(child)
                else:
                    walk(left[key], right[key], child)
            return
        if isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                collected.append(path)
                return
            for index, (one, two) in enumerate(zip(left, right)):
                walk(one, two, "%s/%d" % (path, index))
            return
        if left != right:
            collected.append(path)

    walk(before, after, "")
    return collected


def request_record(
    result: Dict[str, Any],
    form: Dict[str, str],
    note: str,
) -> Dict[str, Any]:
    """The recorded request: exact sent bytes except redacted secrets."""
    recorded_form = sanitize_form(dict(form))
    if "data" in recorded_form:
        recorded_form["data"] = sanitize_data_field(form["data"])
    return {
        "captured_at_utc": iso_now(),
        "method": result["method"],
        "target": result["target"],
        "path": result["path"],
        "query": result["query"],
        "form": recorded_form,
        "headers_sent": sanitize_headers(result["headers_sent"]),
        "scheme": "http",
        "host": LEGACY_HOST,
        "port": LEGACY_PORT,
        "note": note,
    }


def response_record(result: Dict[str, Any], body: bytes) -> Dict[str, Any]:
    return {
        "status": result["status"],
        "reason": result["reason"],
        "headers": sanitize_headers(result["response_headers"]),
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "captured_at_utc": iso_now(),
    }


def write_step(
    staging: Path,
    name: str,
    result: Dict[str, Any],
    body: bytes,
    before: Dict[str, Any],
    after: Dict[str, Any],
    form: Dict[str, str],
    note: str,
) -> Dict[str, Any]:
    """Write one step's request/before/response/after records (full saves)."""
    step_dir = staging / "steps" / name
    write_json(step_dir / "request.json", request_record(result, form, note))
    write_json(step_dir / "before.json", before)
    write_bytes(step_dir / "response.body", body)
    write_json(step_dir / "response.meta.json", response_record(result, body))
    write_json(step_dir / "after.json", after)
    return {
        "name": name,
        "method": result["method"],
        "path": result["path"],
        "target": result["target"],
        "status": result["status"],
        "response_bytes": len(body),
        "response_sha256": sha256_bytes(body),
        "save_before_sha256": save_bytes_sha(before),
        "save_after_sha256": save_bytes_sha(after),
        "save_unchanged_by_call": save_bytes_sha(before) == save_bytes_sha(after),
    }


def command_form(pid: str, data: str) -> Dict[str, str]:
    return {
        "USERID": pid,
        "user_key": USER_KEY,
        "language": LANGUAGE,
        "data": data,
    }


def send_command(
    pid: str, cookie: str, batch: Dict[str, Any], label: str
) -> Tuple[Dict[str, Any], bytes]:
    """POST one derived batch to ``command.php`` and require status 200."""
    form = command_form(pid, placement_envelope.data_field(batch))
    result = http_request(
        LEGACY_PORT,
        "POST",
        DYNAMIC_ROOT + "/command.php",
        form=dict(form),
        cookie=cookie,
        timeout=30.0,
    )
    if result["status"] != 200:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: expected HTTP 200, got %r" % (label, result["status"]),
        )
    body = result.pop("body")
    if json.loads(body.decode("utf-8")) != {"result": "success"}:
        raise CaptureError(
            EXIT_REQUEST,
            "%s response is not the legacy success result: %r" % (label, body),
        )
    return result, body


# --------------------------------------------------------- derived batches --
def build_seed_envelope(collection_id: int, ts: Optional[int] = None) -> Dict[str, Any]:
    """The content-derived seed: one ``complete_collection`` for a collection id.

    Built from the shared collection module rather than hand-written, so the
    captured request cannot drift from the branch the delivered
    ``godot-unit-collection`` line already parity-tested.
    """
    return collection_envelope.build_envelope(collection_id=collection_id, ts=ts)


def build_store_add_envelope(item_id: int, ts: Optional[int] = None) -> Dict[str, Any]:
    """The deferred, unvalidated grant used for PROBE PREPARATION only.

    Crafted here rather than through a derivation precisely because no
    derivation exists for it: ``store_add_items`` takes an arbitrary client-sent
    id list (``command.py:258-266``), which is the acquisition anti-pattern
    ``godot-unit-production`` recorded and which this change defers.
    """
    if ts is None:
        ts = 1700000000
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, "store_add_items", [[item_id]], envelope.neutral_vector()]],
    }


def verify_seed_target(
    before: Dict[str, Any], collection_id: int, expected_prize: Dict[str, int]
) -> Dict[str, Any]:
    """The committed collection row behind one seed, read from the real config.

    Read from the stored configuration the running server itself loads, so the
    recorded grant is the one legacy itself reads -- never a value this tool
    assumed.
    """
    table = config_document().get("collections")
    if not isinstance(table, list):
        raise CaptureError(
            EXIT_ENVIRONMENT, "the committed configuration carries no collections table"
        )
    projected = collection_envelope.project_prize(table, collection_id)
    if not bool(projected.get("ok", False)):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "collection id %d does not resolve in the committed configuration: %s"
            % (collection_id, projected.get("error", "")),
        )
    if projected["prize"] != expected_prize:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed collection %d grants %r, not the pinned %r"
            % (collection_id, projected["prize"], expected_prize),
        )
    return {
        "collection_id": collection_id,
        "name": str(projected["name"]),
        "prize": projected["prize"],
        "index_rule": collection_envelope.INDEX_RULE,
    }


def verify_target(before: Dict[str, Any]) -> None:
    """The corpus's own storage target, verified against the real config."""
    store = before["maps"][0].get(STORE_FIELD)
    if store != {}:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's storage is %r, not the committed {}; the fixture "
            "assumes an EMPTY storage so the seed grant is an observable write"
            % (store,),
        )
    if before["privateState"].get(LEDGER_FIELD) != []:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save already records bought units %r; a placement appends "
            "to this ledger, so the fixture requires it empty"
            % (before["privateState"].get(LEDGER_FIELD),),
        )
    if before["privateState"].get(COLLECTIONS_FIELD) != []:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's collection ledger is %r, not the committed []; the "
            "fixture assumes an EMPTY ledger" % (
                before["privateState"].get(COLLECTIONS_FIELD),
            ),
        )
    if resources_of(before) != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's resources are %r, not the committed %r"
            % (resources_of(before), FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    items = before["maps"][0][ITEMS_FIELD]
    if len(items) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save holds %d placements, not the pinned %d"
            % (len(items), FIXTURE_EXPECTED_PLACEMENTS),
        )
    for index in range(1, FIXTURE_EXPECTED_PLACEMENTS + 1):
        if str(index) not in items:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save holds no placement at map key %d; the derived "
                "slot rule (smallest absent positive integer) and every recorded "
                "leaf pointer assume contiguous keys 1..%d"
                % (index, FIXTURE_EXPECTED_PLACEMENTS),
            )
    if list(items[str(OCCUPIED_SLOT)]) != list(envelope.RECORDED_OCCUPIED_ROW):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "placement %d is %r, not the recorded Command Center row %r that "
            "probe 2 overwrites" % (
                OCCUPIED_SLOT, items[str(OCCUPIED_SLOT)],
                list(envelope.RECORDED_OCCUPIED_ROW),
            ),
        )
    verify_seed_target(before, SEED_COLLECTION_ID, {str(SEED_PRIZE_ID): SEED_PRIZE_QUANTITY})
    verify_seed_target(before, SELL_COLLECTION_ID, SELL_PRIZE)
    for item_id in (SEED_PRIZE_ID, SELL_ITEM_ID):
        if config_type(item_id) != "u":
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "committed prize id %d has type %r, not 'u'; both recorded seeds "
                "are UNIT prizes and this line is the unit-placement round trip"
                % (item_id, config_type(item_id)),
            )
    if envelope.committed_item(config_document().get("items"), UNSTORED_ITEM_ID) is None:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "probe 1's id %d is not a committed item; 'never stored' and 'unknown "
            "id' are two distinct refusals and the probe needs the first"
            % UNSTORED_ITEM_ID,
        )
    if envelope.committed_item(config_document().get("items"), UNKNOWN_ITEM_ID) is not None:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "probe 3's id %d unexpectedly resolves in the committed "
            "configuration" % UNKNOWN_ITEM_ID,
        )


# -------------------------------------------------------- transaction check --
def verify_placement(
    before: Dict[str, Any],
    after: Dict[str, Any],
    batch: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed placement matches the derivation.

    Everything is checked through the SAME shared derivation the two endpoints
    import, so the capture cannot publish a fixture that contradicts the
    service.  Any mismatch fails the run with exit 5 rather than recording it.
    """
    entry = batch["commands"][0]
    if entry[1] != envelope.PLACE_COMMAND:
        raise CaptureError(
            EXIT_REQUEST, "the placement command must be %r" % envelope.PLACE_COMMAND
        )
    sent_slot, sent_item, sent_x, sent_y = entry[2][0], entry[2][1], entry[2][2], entry[2][3]
    if entry[3] != envelope.neutral_vector():
        raise CaptureError(
            EXIT_REQUEST,
            "the derived vector drifted from the NEUTRAL one: %r"
            % (entry[3],),
        )
    if sent_item != SEED_PRIZE_ID or (sent_x, sent_y) != RECORDED_CELL:
        raise CaptureError(
            EXIT_REQUEST,
            "the recorded placement carries (%r, %r, %r), not the pinned "
            "(%d, %d, %d)" % (sent_slot, sent_item, sent_x, sent_y, sent_slot,
                              SEED_PRIZE_ID, RECORDED_CELL[0], RECORDED_CELL[1]),
        )
    derived_slot = envelope.resolve_slot(before["maps"][0][ITEMS_FIELD])
    if sent_slot != derived_slot:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the sent slot %r is not the DERIVED smallest absent positive "
            "integer %r; the slot rule must be reproduced, not restated"
            % (sent_slot, derived_slot),
        )
    clicks_to_build, properties = committed_pair(SEED_PRIZE_ID)
    divergence = envelope.divergence_place(
        before["maps"][0][STORE_FIELD],
        after["maps"][0][STORE_FIELD],
        before["privateState"][LEDGER_FIELD],
        after["privateState"][LEDGER_FIELD],
        after["maps"][0][ITEMS_FIELD].get(str(derived_slot)),
        SEED_PRIZE_ID,
        RECORDED_CELL[0],
        RECORDED_CELL[1],
        RECORDED_ORIENTATION,
        clicks_to_build,
        properties,
    )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed placement did not carry the derived row: %s" % divergence,
        )
    row = after["maps"][0][ITEMS_FIELD][str(derived_slot)]
    if row[envelope.ROW_SLOT_ATTR] != {}:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "committed unit %d derived attribute bag %r, not the documented {}: "
            "0 of 429 units record a positive clicks_to_build and 0 of 429 "
            "record friend_assistable > 0" % (SEED_PRIZE_ID,
                                              row[envelope.ROW_SLOT_ATTR]),
        )
    if row[envelope.ROW_SLOT_PLAYER] != envelope.DERIVED_PLAYER_TEAM:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the placed row records player team %r, not the documented 1"
            % (row[envelope.ROW_SLOT_PLAYER],),
        )
    changed = leaf_differences(before, after)
    if changed != PLACEMENT_CHANGED_LEAVES:
        raise CaptureError(
            EXIT_REQUEST,
            "the recorded placement must differ from its own before-state at "
            "exactly %r, got %r" % (PLACEMENT_CHANGED_LEAVES, changed),
        )
    if [leaf for leaf in changed if leaf.startswith("/maps/0/")] != \
            PLACEMENT_MAP_CHANGED_LEAVES:
        raise CaptureError(
            EXIT_REQUEST,
            "the placement must change exactly two MAP-level leaves %r, got %r"
            % (PLACEMENT_MAP_CHANGED_LEAVES, changed),
        )
    assert_no_other_movement(before, after, allow=(
        STORE_FIELD, ITEMS_FIELD, LEDGER_FIELD,
    ))
    return {
        "command": envelope.PLACE_COMMAND,
        "map_key": derived_slot,
        "item_id": SEED_PRIZE_ID,
        "cell": [RECORDED_CELL[0], RECORDED_CELL[1]],
        "orientation": RECORDED_ORIENTATION,
        "row": list(row),
        "row_slots": envelope.ROW_SLOTS,
        "row_pointer": ROW_POINTER,
        "attr": list(row[envelope.ROW_SLOT_ATTR]),
        "attr_rule": envelope.ATTR_RULE,
        "attr_derived_from": envelope.attr_derived_from(row[envelope.ROW_SLOT_ATTR]),
        "player": row[envelope.ROW_SLOT_PLAYER],
        "store_before": dict(before["maps"][0][STORE_FIELD]),
        "store_after": dict(after["maps"][0][STORE_FIELD]),
        "ledger_before": list(before["privateState"][LEDGER_FIELD]),
        "ledger_after": list(after["privateState"][LEDGER_FIELD]),
        "ledger_rule": envelope.LEDGER_RULE,
        "placements_before": len(before["maps"][0][ITEMS_FIELD]),
        "placements_after": len(after["maps"][0][ITEMS_FIELD]),
        "changed_leaves": changed,
        "changed_map_leaves": PLACEMENT_MAP_CHANGED_LEAVES,
    }


def verify_sale(
    before: Dict[str, Any],
    after: Dict[str, Any],
    batch: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed sale matches the derivation."""
    entry = batch["commands"][0]
    if entry[1] != envelope.SELL_COMMAND:
        raise CaptureError(
            EXIT_REQUEST, "the sale command must be %r" % envelope.SELL_COMMAND
        )
    if entry[2] != [SELL_ITEM_ID]:
        raise CaptureError(
            EXIT_REQUEST,
            "sell_stored_item takes exactly one argument, got %r" % (entry[2],),
        )
    if entry[3] != envelope.neutral_vector():
        raise CaptureError(
            EXIT_REQUEST,
            "the derived sale vector drifted from the NEUTRAL one: %r" % (entry[3],),
        )
    divergence = envelope.divergence_sell(
        before["maps"][0][STORE_FIELD],
        after["maps"][0][STORE_FIELD],
        before["privateState"][LEDGER_FIELD],
        after["privateState"][LEDGER_FIELD],
        SELL_ITEM_ID,
        before["maps"][0][ITEMS_FIELD],
        after["maps"][0][ITEMS_FIELD],
    )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST, "the executed sale diverged from the derivation: %s"
            % divergence,
        )
    changed = leaf_differences(before, after)
    if changed != SALE_CHANGED_LEAVES:
        raise CaptureError(
            EXIT_REQUEST,
            "the recorded sale must differ from its own before-state at exactly "
            "the one storage key %r, got %r" % (SALE_CHANGED_LEAVES, changed),
        )
    assert_no_other_movement(before, after, allow=(STORE_FIELD,))
    return {
        "command": envelope.SELL_COMMAND,
        "item_id": SELL_ITEM_ID,
        "store_before": dict(before["maps"][0][STORE_FIELD]),
        "store_after": dict(after["maps"][0][STORE_FIELD]),
        "ledger_before": list(before["privateState"][LEDGER_FIELD]),
        "ledger_after": list(after["privateState"][LEDGER_FIELD]),
        "quantity_consumed": envelope.QUANTITY,
        "quantity_rule": envelope.QUANTITY_RULE,
        "credited": False,
        "refund": None,
        "no_refund_note": envelope.NO_REFUND_NOTE,
        "placements_before": len(before["maps"][0][ITEMS_FIELD]),
        "placements_after": len(after["maps"][0][ITEMS_FIELD]),
        "changed_leaves": changed,
    }


def assert_no_other_movement(
    before: Dict[str, Any], after: Dict[str, Any], allow: Tuple[str, ...]
) -> None:
    """Every stored resource, every other row, and the whole key set, checked.

    ``allow`` names the map / private-state fields the transaction is EXPECTED to
    move; everything else must be byte-identical, including the fields this tool
    never names, so a field that moves cannot slip past.
    """
    map_before = before["maps"][0]
    map_after = after["maps"][0]
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r"
            % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field in allow or field in MAP_RESOURCE_FIELDS:
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the branch writes only %s"
                % (field, ", ".join(allow)),
            )
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if name in allow:
            continue
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; the branch writes only %s"
                % (name, ", ".join(allow)),
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST, "playerInfo changed; the branch writes none of it"
        )
    if resources_of(after) != resources_of(before):
        raise CaptureError(
            EXIT_REQUEST,
            "a stored resource moved %r -> %r; the derived vector is NEUTRAL and "
            "this branch charges and credits nothing"
            % (resources_of(before), resources_of(after)),
        )


# ------------------------------------------------------------ probe checking --
def verify_probe(
    before: Dict[str, Any],
    after: Dict[str, Any],
    batch: Dict[str, Any],
) -> Dict[str, Any]:
    """The observed facts of one executed probe, with no expectation imposed.

    A probe records what the legacy server DID. It is never compared against the
    modern derivation -- the whole point is that the two disagree -- so this
    function asserts only structural well-formedness plus the facts the
    investigation names, and returns everything else it saw.
    """
    if len(batch["commands"]) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "every probe batch must carry exactly one command, got %d"
            % len(batch["commands"]),
        )
    entry = batch["commands"][0]
    map_before = before["maps"][0]
    map_after = after["maps"][0]
    items_before = map_before[ITEMS_FIELD]
    items_after = map_after[ITEMS_FIELD]
    return {
        "sent_command": entry[1],
        "sent_args": list(entry[2]),
        "sent_vector": list(entry[3]),
        "store_before": dict(map_before[STORE_FIELD]),
        "store_after": dict(map_after[STORE_FIELD]),
        "ledger_before": list(before["privateState"][LEDGER_FIELD]),
        "ledger_after": list(after["privateState"][LEDGER_FIELD]),
        "placement_count_before": len(items_before),
        "placement_count_after": len(items_after),
        "map_key_set_changed": sorted(items_before) != sorted(items_after),
        "changed_leaves": leaf_differences(before, after),
        "resources_before": resources_of(before),
        "resources_after": resources_of(after),
        "player_info_unchanged": after["playerInfo"] == before["playerInfo"],
    }


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(EXIT_REQUEST, "probe: %s" % message)


def verify_probe_one(facts: Dict[str, Any]) -> None:
    """Probe 1 -- a unit the player never acquired is placed anyway."""
    expect(facts["store_before"] == {}, "the store must be EMPTY before probe 1")
    expect(facts["store_after"] == {},
           "the store must be UNCHANGED, because remove_store_item's conditional "
           "made the decrement a no-op; got %r" % (facts["store_after"],))
    expect(facts["placement_count_after"] == facts["placement_count_before"] + 1,
           "the row count must grow by one")
    expect(facts["ledger_after"] == facts["ledger_before"] + [UNSTORED_ITEM_ID],
           "the ledger must grow by exactly one id: %r -> %r"
           % (facts["ledger_before"], facts["ledger_after"]))
    expect("/maps/0/items/%d" % (envelope.COMMITTED_DERIVED_SLOT + 1)
           in facts["changed_leaves"],
           "the new row must be one of the changed leaves: %r"
           % (facts["changed_leaves"],))
    expect(facts["resources_before"] == facts["resources_after"],
           "no stored resource may move")


def verify_probe_two(facts: Dict[str, Any]) -> None:
    """Probe 2 -- a named occupied index silently destroys an existing row."""
    expect(facts["placement_count_after"] == facts["placement_count_before"],
           "the row COUNT must be unchanged, which is what makes this invisible "
           "to any count-based check")
    expect(not facts["map_key_set_changed"],
           "no map key may be added or removed")
    row = facts["changed_leaves"]
    for index in range(0, 4):
        expect("/maps/0/items/%d/%d" % (OCCUPIED_SLOT, index) in row,
               "row slot %d must be one of the changed leaves: %r" % (index, row))
    expect("/maps/0/store/%d" % OCCUPIED_ITEM_ID in row,
           "the storage key must be one of the changed leaves: %r" % (row,))
    expect(facts["resources_before"] == facts["resources_after"],
           "no stored resource may move")


def verify_probe_three(facts: Dict[str, Any]) -> None:
    """Probe 3 -- an id no table has ever heard of is placed with an empty bag."""
    expect(facts["placement_count_after"] == facts["placement_count_before"] + 1,
           "the row count must grow by one")
    expect(facts["ledger_after"] == facts["ledger_before"] + [UNKNOWN_ITEM_ID],
           "the ledger must grow by exactly one id: %r -> %r"
           % (facts["ledger_before"], facts["ledger_after"]))
    expect(facts["resources_before"] == facts["resources_after"],
           "no stored resource may move")


def verify_probe_four(facts: Dict[str, Any]) -> None:
    """Probe 4 -- the out-of-grid cell is stored verbatim, with no bounds check."""
    expect(facts["placement_count_after"] == facts["placement_count_before"] + 1,
           "the row count must grow by one")
    expect(facts["store_after"] == {}, "the stored unit must have been consumed")
    expect(facts["ledger_before"] == facts["ledger_after"],
           "the ledger must be unchanged, because %d was already present"
           % SEED_PRIZE_ID)
    expect(facts["resources_before"] == facts["resources_after"],
           "no stored resource may move")


def probe_seeded_add(
    pid: str, cookie: str, save_path: Path, item_id: int,
    setup: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """One ``store_add_items`` probe-preparation batch, fully recorded."""
    batch = build_store_add_envelope(item_id)
    before = canonical_save(save_path)
    _result, body = send_command(pid, cookie, batch, "store_add_items probe setup")
    after = canonical_save(save_path)
    record = verify_probe(before, after, batch)
    setup.append({
        "item_id": item_id,
        "store_before": record["store_before"],
        "store_after": record["store_after"],
        "changed_leaves": record["changed_leaves"],
        "note": PROBE_SETUP_NOTE,
        "response_sha256": sha256_bytes(body),
    })
    return record


def probe_batch(command: str, args: List[Any]) -> Dict[str, Any]:
    """A hand-built one-command probe batch with a PINNED envelope timestamp.

    Every probe batch pins ``ts`` to a constant rather than the current time, so
    the probe records are byte-stable across reruns and the only volatile value
    in this fixture is the one the manifest documents: the placed row's instant.
    """
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": 1700000000,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, command, list(args), envelope.neutral_vector()]],
    }


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    return {
        label: dir_group_record(REPO_ROOT / relative, relative)
        for relative, label in PROTECTED_FIXTURES
    }


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy stored-placement fixture "
        "(contained, loopback only)."
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="fixture output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-disposable",
        action="store_true",
        help="do not delete the disposable copy (for debugging only)",
    )
    args = parser.parse_args(argv)

    if sys.version_info[:2] != (3, 9):
        print(
            "capture: refused: this command must run under CPython 3.9.x "
            "(pinned baseline); got %s" % sys.version.split()[0],
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT
    if not FRESH_PLAYER_SAVE.is_file():
        print("capture: missing seed save: %s" % FRESH_PLAYER_SAVE, file=sys.stderr)
        return EXIT_ENVIRONMENT

    out_dir = Path(args.out).resolve()
    if REPO_ROOT not in out_dir.parents:
        print(
            "capture: --out must be strictly inside the repository: %s" % out_dir,
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT

    if not port_is_free(LEGACY_HOST, LEGACY_PORT):
        print(
            "capture: port conflict: %s:%d is already in use; refusing to start "
            "the legacy server" % (LEGACY_HOST, LEGACY_PORT),
            file=sys.stderr,
        )
        return EXIT_PORT_BUSY

    pre_groups = containment_snapshot()
    pre_combined = snapshot_combined(pre_groups)
    pre_fixtures = protected_fixture_snapshot()

    # Fixtures are staged OUTSIDE the working tree and published only after
    # every check passed, so a failed run writes nothing into the repo.
    staging = Path(tempfile.mkdtemp(prefix="compat-stored-placement-staging-"))
    disposable: Optional[Path] = None
    process = None
    try:
        disposable, pid, seed_sha = build_disposable(Path(tempfile.gettempdir()))
        saves_dir = disposable / "saves"
        seed_group = save_group_record(saves_dir)
        print("capture: disposable copy: %s" % disposable)
        print("capture: starting legacy server on %s:%d ..." % (LEGACY_HOST, LEGACY_PORT))
        process, stdout_path, stderr_path = start_server(disposable)
        if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
            raise CaptureError(
                EXIT_SERVER,
                "legacy server did not become ready (exit=%s)\n--- stdout ---\n%s"
                "\n--- stderr ---\n%s"
                % (process.poll(), read_tail(stdout_path), read_tail(stderr_path)),
            )
        print("capture: legacy server ready (pid %d)" % process.pid)

        startup_record = save_group_record(saves_dir)
        if startup_record["sha256"] != seed_group["sha256"]:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "server startup rewrote the seeded corpus saves (group %s -> %s)"
                % (seed_group["sha256"], startup_record["sha256"]),
            )

        summaries: List[Dict[str, Any]] = []
        save_path = saves_dir / ("%s.save.json" % pid)

        # --- step 1: login (session cookie, save must stay identical) ------
        before_login = canonical_save(save_path)
        verify_target(before_login)
        login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
        login_result = http_request(
            LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0
        )
        if login_result["status"] != 302:
            raise CaptureError(
                EXIT_REQUEST,
                "login_post: expected HTTP 302, got %r" % login_result["status"],
            )
        after_login = canonical_save(save_path)
        if save_bytes_sha(before_login) != save_bytes_sha(after_login):
            raise CaptureError(
                EXIT_CONTAINMENT,
                "login_post mutated the disposable corpus save; the login step "
                "must leave it byte-identical",
            )
        body = login_result.pop("body")
        cookie = extract_session_cookie(login_result)
        summaries.append(
            write_step(
                staging,
                "login_post",
                login_result,
                body,
                before_login,
                after_login,
                login_form,
                "Login form (USERID + GAMEVERSION) exactly as the sixteen "
                "delivered captures send it; recorded for session fidelity -- "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- step 2: the content-derived seed ------------------------------
        before_seed = canonical_save(save_path)
        seed_batch = build_seed_envelope(SEED_COLLECTION_ID)
        seed_note = (
            "command.php form (USERID, user_key, language, data) with the "
            "derived <64-hex>;<json> envelope carrying exactly one command: "
            "[[0,\"complete_collection\",[1,0],[0,0,0,0,0,0,0,0]]]. This is the "
            "CONTENT-DERIVED SEED of the whole line: the client names WHICH "
            "collection and the server looks up WHAT it grants in the committed "
            "`collections` table (get_collection_prize: index = max(0, "
            "collection - 1), then json.loads(collections[index]['prize'])), so "
            "no item id, quantity, or price is sent and the resource vector is "
            "NEUTRAL because a completion's price would be a client-sent delta "
            "(apply_resources runs before the branch). The grant writes "
            "map['store'] and privateState['collections'] and NOTHING ELSE -- in "
            "particular NOT privateState['boughtUnits'], which is why the "
            "placement below performs that write itself. user_key is redacted; "
            "accessToken is the crafted empty placeholder."
        )
        seed_result, seed_body = send_command(pid, cookie, seed_batch, "command_complete_collection")
        after_seed = canonical_save(save_path)
        summaries.append(
            write_step(
                staging, "command_complete_collection", seed_result, seed_body,
                before_seed, after_seed, command_form(
                    pid, placement_envelope.data_field(seed_batch)
                ), seed_note,
            )
        )
        grant = collection_envelope.expected_grant(
            before_seed["maps"][0][STORE_FIELD],
            after_seed["maps"][0][STORE_FIELD],
            {str(SEED_PRIZE_ID): SEED_PRIZE_QUANTITY},
            collection_id=SEED_COLLECTION_ID,
            before_ledger=before_seed["privateState"][COLLECTIONS_FIELD],
            after_ledger=after_seed["privateState"][COLLECTIONS_FIELD],
        )
        if grant is not None:
            raise CaptureError(
                EXIT_REQUEST,
                "the executed seed did not produce the committed grant: %s" % grant,
            )
        if after_seed["privateState"][LEDGER_FIELD] != []:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the seed wrote privateState['boughtUnits'] = %r; the collection "
                "branch appends only to privateState['collections'], and the "
                "fixture's placement must be the writer of the ledger"
                % (after_seed["privateState"][LEDGER_FIELD],),
            )
        print("capture: complete_collection seed store %r, collections %r"
              % (after_seed["maps"][0][STORE_FIELD],
                 after_seed["privateState"][COLLECTIONS_FIELD]))

        # --- step 3: the placement -----------------------------------------
        before_place = canonical_save(save_path)
        place_batch = envelope.build_place_envelope(
            item_id=SEED_PRIZE_ID,
            x=RECORDED_CELL[0],
            y=RECORDED_CELL[1],
            items=before_place["maps"][0][ITEMS_FIELD],
            orientation=RECORDED_ORIENTATION,
        )
        place_note = (
            "command.php form carrying exactly one command: "
            "[[0,\"place_stored_item\",[41,1085,58,47,1,0,0,0],[0,0,0,0,0,0,0,0]]] "
            "-- the DERIVED map slot (the smallest positive integer absent from "
            "maps[0]['items']), the committed prize id, the derived cell, the "
            "server's own team, the orientation, and the two placeholders the "
            "branch reads and discards. NOTHING about the row is accepted from "
            "the client except item id, cell and orientation: the instant is the "
            "server clock (engine.timestamp_now), the garrison slot is always "
            "[] (engine.py:11-12), the team is always 1 (command.py:238 reads "
            "args[4] and command.py:245 never passes it on), and the attribute "
            "bag is derived from the item's committed clicks_to_build and "
            "properties.friend_assistable (engine.py:15-29) -- for a unit both are "
            "empty, so the bag is {}. The vector is NEUTRAL: this branch charges "
            "nothing, and a client-sent delta would move a balance because "
            "apply_resources runs BEFORE the branch (command.py:40)."
        )
        place_result, place_body = send_command(pid, cookie, place_batch, "command_place_stored_item")
        after_place = canonical_save(save_path)
        summaries.append(
            write_step(
                staging, "command_place_stored_item", place_result, place_body,
                before_place, after_place,
                command_form(pid, placement_envelope.data_field(place_batch)),
                place_note,
            )
        )
        placement = verify_placement(before_place, after_place, place_batch)
        print("capture: place_stored_item -> slot %d row %r, store %r -> %r, "
              "ledger %r -> %r, changed leaves %r"
              % (placement["map_key"], placement["row"],
                 placement["store_before"], placement["store_after"],
                 placement["ledger_before"], placement["ledger_after"],
                 placement["changed_leaves"]))

        # --- step 4: the second content-derived seed -----------------------
        before_sell_seed = canonical_save(save_path)
        sell_seed_batch = build_seed_envelope(SELL_COLLECTION_ID)
        sell_seed_result, sell_seed_body = send_command(
            pid, cookie, sell_seed_batch, "command_complete_collection (2)"
        )
        after_sell_seed = canonical_save(save_path)
        summaries.append(
            write_step(
                staging, "command_complete_collection_2", sell_seed_result,
                sell_seed_body, before_sell_seed, after_sell_seed,
                command_form(pid, placement_envelope.data_field(sell_seed_batch)),
                "The second content-derived seed, collection 2 whose committed "
                "prize is exactly {\"1062\": 1} (unit 1062 MegaBot). It exists so "
                "the sale below disposes of an id the ledger has never seen and "
                "the placement has never placed, which is what makes the sale "
                "step's 'the ledger is untouched' half observable rather than "
                "trivially true for an id that was already placed.",
            )
        )
        sell_grant = collection_envelope.expected_grant(
            before_sell_seed["maps"][0][STORE_FIELD],
            after_sell_seed["maps"][0][STORE_FIELD],
            SELL_PRIZE,
            collection_id=SELL_COLLECTION_ID,
            before_ledger=before_sell_seed["privateState"][COLLECTIONS_FIELD],
            after_ledger=after_sell_seed["privateState"][COLLECTIONS_FIELD],
        )
        if sell_grant is not None:
            raise CaptureError(
                EXIT_REQUEST,
                "the executed second seed did not produce the committed grant: %s"
                % sell_grant,
            )
        if SELL_ITEM_ID in after_sell_seed["privateState"][LEDGER_FIELD]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "unit %d is already in boughtUnits after the second seed; the "
                "sale step's ledger half would then be trivially true"
                % SELL_ITEM_ID,
            )

        # --- step 5: the sale ----------------------------------------------
        before_sell = canonical_save(save_path)
        sell_batch = envelope.build_sell_envelope(SELL_ITEM_ID)
        sell_note = (
            "command.php form carrying exactly one command: "
            "[[0,\"sell_stored_item\",[1062],[0,0,0,0,0,0,0,0]]] -- ONE argument "
            "and nothing else. The branch reads args[0] and calls "
            "remove_store_item with its default quantity=1 (command.py:250-255), "
            "so there is no quantity, no price, and no refund to send. The "
            "executed result changes EXACTLY ONE leaf, the storage key, because "
            "remove_store_item DELETES the key when the remaining quantity is "
            "not positive (engine.py:80-83): no row is added, no boughtUnits "
            "entry is written or removed, and NO resource is credited. The vector "
            "is NEUTRAL, and a 'sale' that credited anything would be a "
            "client-sent delta applied before the branch."
        )
        sell_result, sell_body = send_command(pid, cookie, sell_batch, "command_sell_stored_item")
        after_sell = canonical_save(save_path)
        summaries.append(
            write_step(
                staging, "command_sell_stored_item", sell_result, sell_body,
                before_sell, after_sell,
                command_form(pid, placement_envelope.data_field(sell_batch)),
                sell_note,
            )
        )
        sale = verify_sale(before_sell, after_sell, sell_batch)
        print("capture: sell_stored_item -> store %r -> %r, changed leaves %r"
              % (sale["store_before"], sale["store_after"], sale["changed_leaves"]))

        # --- the executed-legacy probes (not recorded steps) ----------------
        probe_records: List[Dict[str, Any]] = []
        setup_records: List[Dict[str, Any]] = []

        def run_probe(
            index: int, batch: Dict[str, Any], label: str, verifier: Any
        ) -> Dict[str, Any]:
            before_probe = canonical_save(save_path)
            _result, probe_body = send_command(pid, cookie, batch, label)
            after_probe = canonical_save(save_path)
            facts = verify_probe(before_probe, after_probe, batch)
            verifier(facts)
            record = dict(PROBES[index - 1])
            record.update(facts)
            record["response"] = probe_body.decode("utf-8")
            record["response_sha256"] = sha256_bytes(probe_body)
            record["classification"] = "divergence"
            record["parity"] = False
            probe_records.append(record)
            print("capture: probe %d (%s) changed leaves %r"
                  % (index, label, facts["changed_leaves"]))
            return record

        # Probe 1: a committed unit the player never acquired, with an empty store.
        run_probe(
            1,
            probe_batch(envelope.PLACE_COMMAND,
                        [envelope.COMMITTED_DERIVED_SLOT + 1, UNSTORED_ITEM_ID,
                         UNSTORED_CELL[0], UNSTORED_CELL[1], 1, 0, 0, 0]),
            "probe 1 place_stored_item (never stored)", verify_probe_one,
        )

        # Probe 4 needs the seeded prize back in storage.  Its id is already in
        # the ledger, so the ledger half of the probe is the observable one.
        setup_records.append(
            probe_seeded_add(pid, cookie, save_path, SEED_PRIZE_ID, setup_records)
        )
        run_probe(
            4,
            probe_batch(envelope.PLACE_COMMAND,
                        [envelope.COMMITTED_DERIVED_SLOT + 2, SEED_PRIZE_ID,
                         OUT_OF_GRID_CELL[0], OUT_OF_GRID_CELL[1], 1, 0, 0, 0]),
            "probe 4 place_stored_item (out of grid)", verify_probe_four,
        )

        # Probe 3: an id that resolves to no committed definition anywhere.
        run_probe(
            3,
            probe_batch(envelope.PLACE_COMMAND,
                        [envelope.COMMITTED_DERIVED_SLOT + 6, UNKNOWN_ITEM_ID,
                         UNKNOWN_CELL[0], UNKNOWN_CELL[1], 1, 0, 0, 0]),
            "probe 3 place_stored_item (unknown id)", verify_probe_three,
        )

        # Probe 2: a NAMED occupied index, which the modern endpoint can never be
        # sent, because it derives the slot instead of accepting one.
        setup_records.append(
            probe_seeded_add(pid, cookie, save_path, OCCUPIED_ITEM_ID, setup_records)
        )
        run_probe(
            2,
            probe_batch(envelope.PLACE_COMMAND,
                        [OCCUPIED_SLOT, OCCUPIED_ITEM_ID,
                         OCCUPIED_CELL[0], OCCUPIED_CELL[1], 1, 0, 0, 0]),
            "probe 2 place_stored_item (occupied index)", verify_probe_two,
        )

        # The recorded probe order is the manifest order, not the run order.
        probe_records.sort(key=lambda record: record["probe"])

        # --- stop the server before any containment re-check ---------------
        server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
        process = None
        if server_error:
            raise CaptureError(EXIT_SERVER, server_error)
        print("capture: legacy server stopped; port %d free again" % LEGACY_PORT)

        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        if post_groups != pre_groups:
            changed = sorted(
                name
                for name in set(pre_groups) | set(post_groups)
                if pre_groups.get(name) != post_groups.get(name)
            )
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree bytes changed during the run: %s" % ", ".join(changed),
            )

        post_fixtures = protected_fixture_snapshot()
        if post_fixtures != pre_fixtures:
            changed = sorted(
                label
                for label in set(pre_fixtures) | set(post_fixtures)
                if pre_fixtures.get(label) != post_fixtures.get(label)
            )
            raise CaptureError(
                EXIT_CONTAINMENT,
                "committed fixtures changed during the run: %s" % ", ".join(changed),
            )

        if not args.keep_disposable and disposable is not None:
            shutil.rmtree(disposable, ignore_errors=False)
            disposable = None

        resources_before = resources_of(before_login)
        resources_after = resources_of(after_sell)
        manifest = {
            "schema": "godot-stored-item-placement/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for a legacy "
                "place_stored_item and a legacy sell_stored_item on the committed "
                "corpus, both seeded by the CONTENT-DERIVED complete_collection "
                "branch; the executed-legacy parity oracle for the Compatibility "
                "API v0 place_stored and sell_stored endpoints and the FIRST "
                "executed evidence that a unit acquired from committed content "
                "reaches the map."
            ),
            "invocation": "python -B apps/compat-api/capture_stored_placement_fixture.py"
            + ("" if not argv else " " + " ".join(argv)),
            "executed_at_utc": iso_now(),
            "exit_code": 0,
            "interpreter": {
                "executable": sys.executable,
                "version": sys.version,
                "requirement": "CPython 3.9.x (pinned baseline for this change)",
            },
            "server": {
                "command": [sys.executable, "-B", "server.py"],
                "cwd": "<disposable copy under the system temp root>",
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "readiness": "TCP connect loop on 127.0.0.1:%d (no extra HTTP request)"
                % LEGACY_PORT,
                "stopped_by": "taskkill /T /F <pid>, wait, then port-free re-check",
                "output_logs": "server.stdout.log / server.stderr.log inside the "
                "disposable copy (removed with the copy; not committed)",
                "port_free_before_start": True,
                "port_free_after_stop": True,
                "command_recorder_env": "SOCIALWARS_COMMAND_RECORD_DIR stripped from child",
            },
            "corpus": {
                "seed": {
                    "path": "tests/saves/fresh-player.json",
                    "file_sha256": seed_sha,
                    "saves_group_sha256_before_server_start": seed_group["sha256"],
                },
                "seeded_as": "saves/<pid>.save.json in the disposable copy",
                "startup_preserved_seed": True,
                "login_preserved_seed": True,
                "pid": pid,
            },
            "captured": {
                "stored_item_placement": True,
                "closes_unit_collection_followup": True,
                "note": (
                    "A place_stored_item WAS captured, and this is the round trip "
                    "the delivered unit-collection line recorded as a carried "
                    "follow-up: complete_collection -> map['store'] -> "
                    "place_stored_item -> a map row. The placement count grows "
                    "40 -> 41 across the recorded placement, unit 1085 appears "
                    "on the map, and the id is written into boughtUnits"
                ),
            },
            "target": {
                "store_before": before_login["maps"][0][STORE_FIELD],
                "ledger_before": before_login["privateState"][LEDGER_FIELD],
                "collections_before": before_login["privateState"][COLLECTIONS_FIELD],
                "placement_count_before": len(before_login["maps"][0][ITEMS_FIELD]),
                "fabricated_state": False,
                "target_rule": TARGET_RULE,
                "seed_collection": verify_seed_target(
                    before_login, SEED_COLLECTION_ID,
                    {str(SEED_PRIZE_ID): SEED_PRIZE_QUANTITY},
                ),
                "seed_prize_item_name": config_name(SEED_PRIZE_ID),
                "seed_prize_item_type": config_type(SEED_PRIZE_ID),
                "sell_collection": verify_seed_target(
                    before_login, SELL_COLLECTION_ID, SELL_PRIZE,
                ),
                "sell_prize_item_name": config_name(SELL_ITEM_ID),
                "sell_prize_item_type": config_type(SELL_ITEM_ID),
                "seed_route": "complete_collection (content-derived); "
                    "store_add_items is used for probe preparation only",
            },
            "placement": dict(placement, **{
                "derivation": envelope.ROW_DERIVATION,
                "slot_rule": envelope.SLOT_RULE,
                "slot_inverse_rule": envelope.SLOT_INVERSE_RULE,
                "row_slots": envelope.ROW_SLOTS,
                "dismissed_arguments": [dict(entry) for entry in envelope.DISMISSED_ARGUMENTS],
                "intent_keys": list(envelope.PLACE_INTENT_KEYS),
                "intent_ignored_keys": list(envelope.PLACE_INTENT_IGNORED_KEYS),
                "intent_note": envelope.INTENT_NOTE,
                "vector_rule": "NEUTRAL by necessity: this branch charges "
                    "nothing, and a client-sent delta would move a balance because "
                    "engine.apply_resources runs BEFORE the branch "
                    "(command.py:40; engine.py:251-271)",
            }),
            "sale": dict(sale, **{
                "intent_keys": list(envelope.SELL_INTENT_KEYS),
                "intent_ignored_keys": list(envelope.SELL_INTENT_IGNORED_KEYS),
                "vector_rule": "NEUTRAL by necessity: a sale credits NOTHING, so "
                    "every stored resource must be unchanged after execution",
            }),
            "changed_leaf_correction": {
                "task_text_predicted": "exactly two leaves, the new row and the "
                    "store key",
                "measured": list(PLACEMENT_CHANGED_LEAVES),
                "measured_map_scoped": list(PLACEMENT_MAP_CHANGED_LEAVES),
                "cause": (
                    "the committed investigation seeded with store_add_items, which "
                    "calls bought_unit_add in the SAME batch (command.py:264), so "
                    "its ledger already held the id and the placement's own "
                    "append-if-absent (command.py:246; engine.py:86-89) left the "
                    "ledger alone. Seeding with the CONTENT-DERIVED "
                    "complete_collection instead -- which appends to "
                    "privateState['collections'] and never to boughtUnits -- makes "
                    "that third write observable. The number is therefore THREE "
                    "for the whole document and TWO at map scope, and no "
                    "conclusion of the investigation changes"
                ),
            },
            "refusals": [dict(entry) for entry in envelope.REFUSALS],
            "geometry_gap": envelope.GEOMETRY_GAP,
            "cell_occupancy_gap": envelope.CELL_OCCUPANCY_GAP,
            "no_capacity_rule": envelope.NO_CAPACITY_RULE,
            "no_stock_rule": envelope.NO_STOCK_RULE,
            "probe_setup": {
                "note": PROBE_SETUP_NOTE,
                "batches": setup_records,
            },
            "probes": probe_records,
            "recorded_steps": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "placement_count_before": len(before_login["maps"][0][ITEMS_FIELD]),
                "placement_count_after": len(after_sell["maps"][0][ITEMS_FIELD]),
                "store_before": before_login["maps"][0][STORE_FIELD],
                "store_after": after_sell["maps"][0][STORE_FIELD],
                "ledger_before": before_login["privateState"][LEDGER_FIELD],
                "ledger_after": after_sell["privateState"][LEDGER_FIELD],
                "collections_before": before_login["privateState"][COLLECTIONS_FIELD],
                "collections_after": after_sell["privateState"][COLLECTIONS_FIELD],
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "other_rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "map_key_set_grew_by_one": True,
                "private_state_unchanged_except_ledgers": True,
                "player_info_unchanged": True,
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) only bites when a "
                    "delta would drive a balance below zero; BOTH derived vectors "
                    "are the NEUTRAL all-zero vector, so no balance moves at all "
                    "and the clamp is never exercised by this fixture. That the "
                    "vector really is client-sent is established by the "
                    "delivered godot-unit-collection probe 1, which moved 500 "
                    "experience through the very same branch",
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE carries exactly ONE time-dependent value "
                    "and it is the placed row's slot 3: int(time.time()) taken "
                    "inside engine.map_add_item (engine.py:5-6 via engine.py:13-14). "
                    "Every other state leaf is byte-stable. The SALE carries no "
                    "time-dependent value of its own -- it writes one storage key "
                    "and touches no clock -- but its before/after documents still "
                    "CONTAIN the placed row, so they move with it"
                ),
                "state_leaf": "/maps/0/items/%d/3" % DERIVED_SLOT,
                "state_leaf_documents": [
                    "steps/command_place_stored_item/after.json",
                    "steps/command_complete_collection_2/before.json",
                    "steps/command_complete_collection_2/after.json",
                    "steps/command_sell_stored_item/before.json",
                    "steps/command_sell_stored_item/after.json",
                ],
                "stable_state_leaves": [
                    "every other leaf of all five recorded save documents; a "
                    "leaf-level diff of two consecutive runs differs at exactly "
                    "/maps/0/items/41/3 in each of the five documents listed above "
                    "and nowhere else",
                    "the login step's before.json and after.json are both "
                    "byte-stable and identical to each other",
                    "steps/command_complete_collection/after.json is byte-stable: "
                    "it precedes the placement, so no placed row exists in it",
                    "the seeded save's own instant values are the SEED file's, "
                    "copied verbatim and never rewritten by these branches",
                    "every response.body is the 21-byte legacy success string",
                ],
                "leaves": [
                    "/executed_at_utc in capture-manifest.json",
                    "/captured_at_utc in every steps/*/request.json",
                    "/captured_at_utc in every steps/*/response.meta.json",
                    "/headers/Date in every steps/*/response.meta.json",
                    "/placement/row/3 in capture-manifest.json, which echoes the "
                    "recorded row",
                    "the envelope ts inside each RECORDED command step's "
                    "request.json /form/data (and therefore that whole field's "
                    "string, because the digest covers the payload), since ts is "
                    "the current time",
                    "every save_after_sha256 / save_before_sha256 whose document "
                    "is listed in state_leaf_documents -- that is, the "
                    "command_place_stored_item step's save_after_sha256 and both "
                    "digests of the command_complete_collection_2 and "
                    "command_sell_stored_item steps, whose documents carry the "
                    "placed row",
                ],
                "probe_batches_are_stable": (
                    "the four probe batches and the two store_add_items "
                    "preparation batches pin ts to 1700000000 instead of the "
                    "current time, so their recorded bytes carry no wall clock. "
                    "The probe records are also never written as step documents, "
                    "so no probe save appears in this fixture at all; the probe "
                    "facts are recorded inside the manifest"
                ),
                "stable_by_derivation": (
                    "the derived slot, the cell, the orientation, the empty "
                    "garrison, the team, the attribute bag, the appended ledger "
                    "id, the placement count, and all seven stored resources are "
                    "byte-stable because each is either a fixed constant or a "
                    "pure function of committed content"
                ),
                "documented_normalization": (
                    "stored-placement parity applies NO clock normalization: the "
                    "row is compared slot by slot with slot 3 EXCLUDED, and that "
                    "exclusion is asserted to be the ONLY excluded slot. Every "
                    "other slot, the storage key, the ledger entry by entry, and "
                    "every stored resource by value are compared with no "
                    "normalization at all. The instant itself is checked to be a "
                    "positive wall-clock reading and is otherwise never compared"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The sixteen already committed "
                    "fixture directories are digest-pinned for the same reason."
                ),
                "pre_run": pre_groups,
                "post_run": post_groups,
                "pre_combined_sha256": pre_combined,
                "post_combined_sha256": post_combined,
                "protected_fixtures": {
                    "paths": [relative for relative, _label in PROTECTED_FIXTURES],
                    "pre_run": pre_fixtures,
                    "post_run": post_fixtures,
                    "identical": True,
                },
                "identical": True,
                "working_tree_saves_unchanged": True,
                "fixture_output": str(out_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
                "only_working_tree_writes": "fixture files under --out",
                "disposable_copy_removed": args.keep_disposable is False,
                "loopback_only": True,
                "no_flash_browser_external_network": True,
            },
            "cleanup": {
                "disposable_removed_before_manifest_write": args.keep_disposable is False,
                "server_stopped_within_run": True,
            },
        }

        try:
            write_json(staging / "capture-manifest.json", manifest)
            out_dir.mkdir(parents=True, exist_ok=True)
            clear_previous_fixtures(out_dir)
            shutil.move(str(staging / "steps"), str(out_dir / "steps"))
            shutil.move(
                str(staging / "capture-manifest.json"),
                str(out_dir / "capture-manifest.json"),
            )
        except OSError as error:
            raise CaptureError(EXIT_WRITE, "could not write fixtures: %s" % error)

        print("capture: wrote %d step fixtures to %s" % (len(summaries), out_dir))
        for summary in summaries:
            print(
                "capture:   %-32s %s %s -> %d (%d bytes, save unchanged: %s)"
                % (
                    summary["name"],
                    summary["method"],
                    summary["target"],
                    summary["status"],
                    summary["response_bytes"],
                    summary["save_unchanged_by_call"],
                )
            )
        print(
            "capture: place_stored_item via %s: slot %d, row %r, store %r -> %r, "
            "changed leaves %r"
            % (
                placement["command"], placement["map_key"], placement["row"],
                placement["store_before"], placement["store_after"],
                placement["changed_leaves"],
            )
        )
        print(
            "capture: sell_stored_item via %s: store %r -> %r, changed leaves %r"
            % (
                sale["command"], sale["store_before"], sale["store_after"],
                sale["changed_leaves"],
            )
        )
        print("capture: placement count %d -> %d"
              % (placement["placements_before"], placement["placements_after"]))
        for name in sorted(resources_before):
            print(
                "capture:   %-5s %d -> %d (delta %+d)"
                % (
                    name,
                    resources_before[name],
                    resources_after[name],
                    resources_after[name] - resources_before[name],
                )
            )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except envelope.EnvelopeError as error:
        print(
            "capture: FAILED: could not derive the envelope: [%s] %s"
            % (error.code, error),
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT
    except collection_envelope.EnvelopeError as error:
        print(
            "capture: FAILED: could not derive the seed envelope: [%s] %s"
            % (error.code, error),
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT
    except CaptureError as error:
        print("capture: FAILED: %s" % error, file=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        print("capture: interrupted", file=sys.stderr)
        return 130
    finally:
        if process is not None:
            leftover = stop_server(process, LEGACY_HOST, LEGACY_PORT)
            if leftover:
                print("capture: stop problem: %s" % leftover, file=sys.stderr)
        if disposable is not None and not args.keep_disposable:
            shutil.rmtree(disposable, ignore_errors=True)
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
