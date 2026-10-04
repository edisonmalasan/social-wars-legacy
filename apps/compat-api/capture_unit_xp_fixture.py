#!/usr/bin/env python3
"""Capture the executed-legacy unit-experience fixture: ``add_xp_unit``.

Contract: ``docs/legacy-unit-xp.md`` (OpenSpec change
``unit-experience-evidence``, task group 2).  Read that record for the
measurements; this module executes them and refuses to publish unless every
one reproduces.

What this does, in order (harness shared with the boot, level, placement,
purchase, move, sell, store, upgrade, construction, collect, expand, quest,
research, tutorial, queue, collection, and stored-placement captures):

1. Verifies the parent interpreter is CPython 3.9 and that the **village seed**
   exists, and takes the working-tree containment snapshot before anything runs
   — plus a digest snapshot of every already-committed fixture directory, which
   must be byte-identical after the run.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. For **each** transaction: builds its own disposable copy, seeds it from
   ``villages/AcidCaos.json``, starts the REAL legacy server, performs the
   login step, executes the crafted ``<64-hex>;<json>`` ``data`` envelope
   carrying exactly **one** ``add_xp_unit`` command, and stops the server.

   **One server per transaction is not an optimisation, it is the only correct
   shape.**  ``sessions.load_saves()`` caches the corpus in a module global at
   import time, so the running server never re-reads the save file from disk.
   Restoring the seed between probes on one server therefore leaves the *in
   memory* corpus already mutated and silently produces a different result. The
   investigation that established this contract lost its first twelve probes to
   exactly that, which is why it is written into the design rather than left as
   folklore.
4. Verifies every transaction structurally **before** publishing anything: the
   login step left the save byte-identical, the recorded HTTP status is the
   expected one, the recorded response body is the legacy
   ``{"result": "success"}`` for every succeeding transaction, the addressed
   row's attribute bag moved exactly as the contract states, the recomputed
   whole-document leaf diff equals the claimed changed-leaf set, the placed-row
   count is unchanged, **every stored resource is byte-identical**, and no other
   leaf anywhere in the save moved.
5. Re-checks containment, stops everything, and only then publishes the staged
   fixture into the repository.

What this fixture establishes, and what it deliberately does not:

* **ESTABLISHED** — the branch's two arms, its argument positions, the missing-row
  early return that still answers success, the absence of any clamp on a
  negative gain, the absence of any bound on the amount, a persisted float,
  type-agnosticism onto a building row, the persisted-string arm versus the
  raising increment arm, ``True`` worth exactly +1, and the third argument's
  **display-only** nature (identical post-state and identical leaf set, a
  different printed line).
* **DERIVED-PROVISIONAL** — that the two- and three-argument forms are
  *interchangeable* because their stored effects were measured equal; and the
  choice of ``AcidCaos.json`` as the disposable seed, which is recorded so a
  rerun reproduces the committed bytes.
* **NOT ESTABLISHED, AND NOT CLAIMED** — any award schedule. The amount is
  ``args[1]`` with no validation of any kind, and the committed per-unit
  experience field is refuted as its source by three independent measurements.
  This fixture therefore **does not** license an endpoint, and it is committed
  as evidence about an oracle, not as a client intent.

No Flash, Ruffle, ActionScript, or browser executes. Every network call is
loopback to ``127.0.0.1:5055``.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.version_info[:2] != (3, 9):
    sys.stderr.write(
        "capture: pinned interpreter is CPython 3.9, this is %d.%d\n"
        % sys.version_info[:2]
    )
    raise SystemExit(2)

from capture_legacy_fixtures import (  # noqa: E402
    CaptureError,
    DYNAMIC_ROOT,
    EXIT_CONTAINMENT,
    EXIT_ENVIRONMENT,
    EXIT_OK,
    EXIT_PORT_BUSY,
    EXIT_REQUEST,
    EXIT_SERVER,
    GAME_VERSION,
    LANGUAGE,
    LEGACY_HOST,
    LEGACY_PORT,
    REPO_ROOT,
    USER_KEY,
    build_disposable,
    canonical_digest,
    containment_snapshot,
    extract_session_cookie,
    http_request,
    iso_now,
    port_is_free,
    read_tail,
    save_group_record,
    sha256_bytes,
    sha256_file,
    snapshot_combined,
    start_server,
    stop_server,
    wait_ready,
    write_bytes,
    write_json,
)
from placement_envelope import (  # noqa: E402
    ENVELOPE_KEYS,
    EnvelopeError,
    data_field,
    parse_data_field,
    payload_json,
)

# --- This line's own constants ---------------------------------------------

SCHEMA = "unit-experience-fixture-v1"

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-unit-experience"

# The disposable seed.  DESIGN D3 / investigation section 4a: this is the
# smallest of the five committed save documents carrying ``attr["xp"]`` by
# placed-row count (319, against 569 / 367 / 549 / 576), and it carries 36 rows
# **with** the key and 283 **without** it — including 12 unit rows with an empty
# bag and 271 building rows — so both arms and both row kinds are exercisable
# from one authentic, committed, progressed save with no fabricated player
# state.  The choice is recorded so a rerun reproduces the committed bytes; any
# other of the five would also have worked.
SEED_SAVE = REPO_ROOT / "villages" / "AcidCaos.json"

# Pinned so the recorded ``data`` field is byte-stable across reruns.  ``ts`` is
# parsed and then **never read** by the legacy dispatcher, exactly as on the
# stored-placement capture; this is the same convention, not a new one.
FIXTURE_TS = 1700000000

# The single legacy command this deliver line executes (established,
# command.py:322-343; the ``add_xp_unit`` row of docs/legacy-protocol/commands.json).
ADD_XP_UNIT_COMMAND = "add_xp_unit"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).  Every batch here is
# NEUTRAL: the amount a player earns is ``args[1]`` on the branch, and putting a
# second, independent client-sent amount on the same request would make the
# "no stored resource moved" proof ambiguous rather than strong.
NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

# The seven stored resource slots with their save locations, exactly as
# engine.apply_resources reads and writes them (engine.py:251-271).  Note the
# three different owners: five on the map, ``cash`` on playerInfo and ``mana``
# on privateState -- getting that wrong would silently read a missing key.
# ``energy`` is deliberately absent: nothing in the legacy source ever writes
# it, so including it would make the "unchanged" proof cover a value this
# branch cannot move.
RESOURCE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
}

# Corpus facts about the seed, verified before anything executes.  These are
# assertions about the committed document, not derived values.
SEED_EXPECTED_ROWS = 319
SEED_EXPECTED_ROWS_WITH_XP = 36
SEED_EXPECTED_PID = "AcidCaos"

# The addressed map keys, verified in the seed before anything executes.
TARGET_EXISTING = "772"      # item 1007, attr {"xp": 23}
TARGET_EMPTY_BAG = "1783"    # item 1050, attr {}
TARGET_BUILDING = "3"        # item 23 (Wall I), attr {}
TARGET_ABSENT = "999999"     # not a key in the committed corpus

# The recorded transactions.  ``expect_attr_*`` are compared with an exact
# type-aware equality so that ``{"xp": 23}`` and ``{"xp": True}`` can never be
# confused -- which matters, because ``True + 5`` is ``6`` in the legacy code,
# so a boolean genuinely reaches the field as an experience value and a
# value-only projection would be right by accident.
TRANSACTIONS: List[Dict[str, Any]] = [
    {
        "name": "increment_existing",
        "args": [TARGET_EXISTING, 5],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 28},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "The increment arm: the key already carries the field, so the "
            "branch executes attr['xp'] += args[1] and nothing else. Exactly "
            "one leaf moves and no stored resource moves."
        ),
    },
    {
        "name": "assign_absent_key",
        "args": [TARGET_EMPTY_BAG, 7],
        "expect_status": 200,
        "expect_attr_before": {},
        "expect_attr_after": {"xp": 7},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EMPTY_BAG],
        "note": (
            "The assign arm: the row's bag is empty, so the branch writes "
            "attr['xp'] = args[1] and persists it. This is the arm that can "
            "persist a non-integer, which is why the delivered projection "
            "classifies the recorded value's kind."
        ),
    },
    {
        "name": "missing_row",
        "args": [TARGET_ABSENT, 5],
        "expect_status": 200,
        "expect_attr_before": None,
        "expect_attr_after": None,
        "expect_changed": [],
        "note": (
            "An unaddressable map key hits map_get_item's falsy branch, prints "
            "'Error: item not found.' and RETURNS -- and the server still "
            "answers the legacy success result. A client cannot distinguish "
            "this outcome from a real award by the response alone."
        ),
    },
    {
        "name": "negative_no_clamp",
        "args": [TARGET_EXISTING, -1000],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": -977},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "A negative gain is NOT clamped. This is the sharp asymmetry with "
            "engine.apply_resources, which applies every vector slot through "
            "max(..., 0); this branch does no arithmetic on the gain at all, "
            "so a client-sent negative persists a negative accumulator."
        ),
    },
    {
        "name": "zero_amount",
        "args": [TARGET_EXISTING, 0],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 23},
        "expect_changed": [],
        "note": (
            "A zero gain leaves the document byte-identical while still "
            "answering success and still printing. Recorded so the "
            "'exactly one leaf moved' claim is not read as 'the field always "
            "changes'."
        ),
    },
    {
        "name": "unbounded_amount",
        "args": [TARGET_EXISTING, 1000000000000],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 1000000000023},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "No bound of any kind on the amount: a client-sent 10**12 persists "
            "verbatim. Unusable as an economy, which is one of the three "
            "independent reasons this line delivers evidence and not a route."
        ),
    },
    {
        "name": "float_amount_persisted",
        "args": [TARGET_EXISTING, 2.5],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 25.5},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "A float gain persists as a float. The delivered projection "
            "reports the value verbatim and never rounds it, because rounding "
            "would destroy the very fact this records."
        ),
    },
    {
        "name": "building_row_type_agnostic",
        "args": [TARGET_BUILDING, 11],
        "expect_status": 200,
        "expect_attr_before": {},
        "expect_attr_after": {"xp": 11},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_BUILDING],
        "note": (
            "The branch is TYPE-AGNOSTIC: it accepts a building row exactly as "
            "it accepts a unit row and stores unit experience on it. The same "
            "is true of the one writer of this field anywhere in the legacy "
            "source. There is no unit type check and no unit-only key space."
        ),
    },
    {
        "name": "level_argument_ignored",
        "args": [TARGET_EXISTING, 5, 9],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 28},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "The third argument, paired with increment_existing which sends the "
            "same first two. Post-state, resource state and changed-leaf set "
            "are IDENTICAL; only the printed line differs, because the third "
            "argument is read into a local, truthiness-tested, and then used "
            "only inside an f-string. Its stored effect is nil -- established "
            "by this pair, not asserted from reading the branch."
        ),
    },
    {
        "name": "string_amount_increment_fails",
        "args": [TARGET_EXISTING, "5"],
        "expect_status": 500,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 23},
        "expect_changed": [],
        "note": (
            "The increment arm against a string gain: 23 + '5' raises TypeError "
            "and the request ends HTTP 500. Nothing is written. The two arms "
            "are ASYMMETRIC on type, and this is the half that raises."
        ),
    },
    {
        "name": "string_amount_assign_persisted",
        "args": [TARGET_EMPTY_BAG, "5"],
        "expect_status": 200,
        "expect_attr_before": {},
        "expect_attr_after": {"xp": "5"},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EMPTY_BAG],
        "note": (
            "The assign arm against the SAME string gain, and it PERSISTS the "
            "string. So one request can poison a save: every later increment "
            "against that row then raises. This is the reachable state the "
            "delivered projection's recorded_kind classification exists to "
            "make visible instead of readable as an integer."
        ),
    },
    {
        "name": "bool_amount_increments_as_one",
        "args": [TARGET_EXISTING, True],
        "expect_status": 200,
        "expect_attr_before": {"xp": 23},
        "expect_attr_after": {"xp": 24},
        "expect_changed": ["/maps/0/items/%s/6/xp" % TARGET_EXISTING],
        "note": (
            "A boolean gain is worth exactly +1, because the branch does "
            "arithmetic on it. This is why bool is a separate member of the "
            "delivered projection's closed classification vocabulary and not "
            "folded into int: a projection reporting bool as int would be "
            "right by accident and wrong by reason."
        ),
    },
]

RECORDED_STEPS = tuple("txn_%s" % entry["name"] for entry in TRANSACTIONS)

# Already-committed fixture directories whose bytes this run must not change.
PROTECTED_FIXTURES = (
    "godot-compatibility-boot",
    "godot-building-collect",
    "godot-building-construction",
    "godot-building-expand",
    "godot-building-move",
    "godot-building-placement",
    "godot-building-sell",
    "godot-building-store",
    "godot-building-upgrade",
    "godot-building-xp",
    "godot-item-purchase",
    "godot-quests",
    "godot-research",
    "godot-stored-item-placement",
    "godot-tutorial",
    "godot-unit-collection",
    "godot-unit-queues",
)


# --- helpers ---------------------------------------------------------------


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that refuses to conflate ``1``, ``1.0`` and ``True``.

    ``==`` would call all three equal, and this fixture's entire point is that
    the legacy server persists whatever it is handed.  ``bool`` is checked
    before ``int`` because ``isinstance(True, int)`` is true.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, int) or isinstance(right, int):
        if isinstance(left, int) and isinstance(right, int):
            return left == right
        return False
    if isinstance(left, float) or isinstance(right, float):
        if isinstance(left, float) and isinstance(right, float):
            return left == right
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        if sorted(left) != sorted(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    return left == right


def leaf_items(document: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Every leaf of a JSON document as sorted ``(json pointer path, value)``."""
    out: List[Tuple[str, Any]] = []
    if isinstance(document, dict):
        for key in sorted(document):
            out.extend(leaf_items(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            out.extend(leaf_items(value, "%s/%d" % (prefix, index)))
    else:
        out.append((prefix, document))
    return out


def canonical_state_sha(document: Any) -> str:
    """Whole-document digest over every leaf, order-independent."""
    return canonical_digest([(path, payload_json(value)) for path, value in leaf_items(document)])


def leaf_diff(before: Any, after: Any) -> List[Tuple[str, Any, Any, Any]]:
    """``(path, present_before, before_value, present_after, after_value)`` set."""
    before_map = {path: (True, value) for path, value in leaf_items(before)}
    after_map = {path: (True, value) for path, value in leaf_items(after)}
    out: List[Tuple[str, Any, Any, Any]] = []
    for path in sorted(set(before_map) | set(after_map)):
        in_before = before_map.get(path)
        in_after = after_map.get(path)
        left = in_before[1] if in_before else None
        right = in_after[1] if in_after else None
        if in_before is None or in_after is None or not typed_equal(left, right):
            out.append((path, in_before is not None, left, in_after is not None, right))
    return out


def diff_payload(diff: List[Tuple[str, Any, Any, Any]]) -> List[Dict[str, Any]]:
    """JSON-safe form of :func:`leaf_diff`, so the fixture is reviewable."""
    return [
        {
            "path": path,
            "present_before": bool(in_before),
            "before": left,
            "present_after": bool(in_after),
            "after": right,
        }
        for path, in_before, left, in_after, right in diff
    ]


def unchanged_leaves_sha(document: Any, changed_paths: List[str]) -> str:
    """Digest over EVERY leaf whose path is not in ``changed_paths``.

    This is the load-bearing half of the "exactly one leaf moved" proof: it is
    what makes the claim mechanical rather than a statement about the addressed
    row alone.
    """
    excluded = set(changed_paths)
    return canonical_digest(
        [
            (path, payload_json(value))
            for path, value in leaf_items(document)
            if path not in excluded
        ]
    )


def stored_resources(document: Dict[str, Any]) -> Dict[str, Any]:
    """The seven stored resource slots, read at their established locations."""
    out: Dict[str, Any] = {}
    for name, location in RESOURCE_SLOTS.items():
        cursor: Any = document
        try:
            for step in location:
                cursor = cursor[step]
            out[name] = cursor
        except (KeyError, IndexError, TypeError):
            raise CaptureError(
                EXIT_REQUEST,
                "seed save has no %s resource slot at %r" % (name, "/".join(location)),
            )
    return out


def map_row(document: Dict[str, Any], key: str) -> Any:
    """The addressed map row, or ``None`` when the key is not in the corpus."""
    try:
        return document["maps"][0]["items"][key]
    except (KeyError, IndexError, TypeError):
        return None


def row_attr(document: Dict[str, Any], key: str) -> Any:
    """Slot 6 of the addressed row, or ``None`` when the row is absent."""
    row = map_row(document, key)
    if row is None:
        return None
    if not isinstance(row, list) or len(row) < 7:
        raise CaptureError(
            EXIT_REQUEST, "map row %s is not an 8-slot row: %r" % (key, row)
        )
    return row[6]


def placed_row_count(document: Dict[str, Any]) -> int:
    try:
        return len(document["maps"][0]["items"])
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "save has no maps[0].items: %s" % error)


def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    return {key: (REDACTED if key in SENSITIVE_FORM_KEYS else value) for key, value in form.items()}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value) for key, value in headers.items()}


def sanitize_envelope_data(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The live request always sends the real bytes; only the record is redacted,
    so the fixture stays secret-free even if the crafted empty placeholder ever
    changes.  ``ts`` is deliberately NOT redacted -- it is pinned to a constant,
    which is what makes the recorded field byte-stable.
    """
    envelope = parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return data_field(envelope)


def build_envelope(args: List[Any]) -> Dict[str, Any]:
    """Derive the six-key batch envelope carrying exactly one command.

    The command's own arguments are the **crafted, client-supplied** ones under
    test -- which is the whole problem.  ``args[0]`` and ``args[1]`` are read
    straight out of this batch by the legacy branch with no validation, so this
    function does no checking beyond the batch shape.  The resource vector is
    NEUTRAL and always will be: see :data:`NEUTRAL_VECTOR`.

    The batch envelope's keys are the shared protocol primitives, imported
    unchanged from the root envelope module; nothing here reimplements them.
    """
    if len(args) < 2:
        raise CaptureError(
            EXIT_REQUEST,
            "add_xp_unit needs at least an index and an amount, got %r" % (args,),
        )
    envelope = {
        "first_number": 0,
        "publishActions": [],
        "ts": FIXTURE_TS,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, ADD_XP_UNIT_COMMAND, list(args), list(NEUTRAL_VECTOR)]],
    }
    if sorted(envelope) != sorted(ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "batch envelope keys drifted from the shared protocol: %r" % (sorted(envelope),),
        )
    return envelope


def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Refuse a batch this line does not intend to record."""
    try:
        parsed = parse_data_field(data_field(envelope))
    except EnvelopeError as error:
        raise CaptureError(EXIT_REQUEST, "crafted envelope is malformed: %s" % error)
    commands = parsed.get("commands")
    if not isinstance(commands, list) or len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST, "batch must carry exactly one command, got %r" % (commands,)
        )
    command = commands[0]
    if not isinstance(command, list) or len(command) != 4:
        raise CaptureError(
            EXIT_REQUEST, "command must be a 4-element list, got %r" % (command,)
        )
    if command[1] != ADD_XP_UNIT_COMMAND:
        raise CaptureError(EXIT_REQUEST, "command is %r, not %r" % (command[1], ADD_XP_UNIT_COMMAND))
    if command[3] != NEUTRAL_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "resource vector is %r, not the neutral %r" % (command[3], NEUTRAL_VECTOR),
        )


def verify_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Assert the committed seed really carries what this fixture assumes.

    Every figure here is a property of the committed document and is checked
    before anything executes, so a corpus change fails loudly at environment
    exit rather than producing a plausible-looking wrong fixture.
    """
    census = {
        "pid": str(seed["playerInfo"]["pid"]),
        "placed_rows": placed_row_count(seed),
        "rows_carrying_attr_xp": sum(
            1
            for row in seed["maps"][0]["items"].values()
            if isinstance(row[6], dict) and "xp" in row[6]
        ),
        "target_existing_row": map_row(seed, TARGET_EXISTING),
        "target_empty_bag_row": map_row(seed, TARGET_EMPTY_BAG),
        "target_building_row": map_row(seed, TARGET_BUILDING),
        "target_absent_present": map_row(seed, TARGET_ABSENT) is not None,
        "state_sha256": canonical_state_sha(seed),
    }
    if census["pid"] != SEED_EXPECTED_PID:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "seed pid is %r, not the pinned %r" % (census["pid"], SEED_EXPECTED_PID),
        )
    if census["placed_rows"] != SEED_EXPECTED_ROWS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "seed carries %d placed rows, not the pinned %d"
            % (census["placed_rows"], SEED_EXPECTED_ROWS),
        )
    if census["rows_carrying_attr_xp"] != SEED_EXPECTED_ROWS_WITH_XP:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "seed carries attr['xp'] on %d rows, not the pinned %d"
            % (census["rows_carrying_attr_xp"], SEED_EXPECTED_ROWS_WITH_XP),
        )
    if census["target_absent_present"]:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed corpus now contains map key %s, so the missing-row "
            "transaction would not test a missing row" % TARGET_ABSENT,
        )
    for name, key in (
        ("target_existing_row", TARGET_EXISTING),
        ("target_empty_bag_row", TARGET_EMPTY_BAG),
        ("target_building_row", TARGET_BUILDING),
    ):
        if census[name] is None:
            raise CaptureError(
                EXIT_ENVIRONMENT, "seed has no map row for key %s" % key
            )
    return census


def verify_transaction(
    name: str,
    args: List[Any],
    before: Dict[str, Any],
    after: Dict[str, Any],
    expect_status: int,
    expect_attr_before: Any,
    expect_attr_after: Any,
    expect_changed: List[str],
    status: int,
) -> Dict[str, Any]:
    """Structurally verify one executed transaction, or refuse to publish.

    Returns the machine-readable facts the manifest records.
    """
    if status != expect_status:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: expected HTTP %d, got %d" % (name, expect_status, status),
        )

    index_key = str(args[0])
    diff = leaf_diff(before, after)
    changed_paths = [entry[0] for entry in diff]
    if changed_paths != sorted(expect_changed):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: changed leaf set is %r, not %r"
            % (name, changed_paths, sorted(expect_changed)),
        )

    # Nothing outside the claimed paths moved.  This is what makes "exactly one
    # leaf" a mechanical claim about the whole 2322-leaf document.
    if unchanged_leaves_sha(before, changed_paths) != unchanged_leaves_sha(after, changed_paths):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: a leaf outside the claimed changed set also moved" % name,
        )

    resources_before = stored_resources(before)
    resources_after = stored_resources(after)
    for key in sorted(RESOURCE_SLOTS):
        if not typed_equal(resources_before[key], resources_after[key]):
            raise CaptureError(
                EXIT_REQUEST,
                "%s: stored resource %s moved %r -> %r under a NEUTRAL vector, "
                "so this branch is not resource-neutral" % (name, key, resources_before[key], resources_after[key]),
            )

    rows_before = placed_row_count(before)
    rows_after = placed_row_count(after)
    if rows_before != rows_after:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: placed-row count moved %d -> %d" % (name, rows_before, rows_after),
        )

    attr_before = row_attr(before, index_key)
    attr_after = row_attr(after, index_key)
    if not typed_equal(attr_before, expect_attr_before):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the addressed row's bag was %r, not the expected %r"
            % (name, attr_before, expect_attr_before),
        )
    if not typed_equal(attr_after, expect_attr_after):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the addressed row's bag became %r, not the expected %r"
            % (name, attr_after, expect_attr_after),
        )

    return {
        "name": name,
        "args": args,
        "status": status,
        "expected_status": expect_status,
        "addressed_map_key": index_key,
        "attr_before": attr_before,
        "attr_after": attr_after,
        "changed_leaf_count": len(changed_paths),
        "changed_leaves": diff_payload(diff),
        "state_sha256_before": canonical_state_sha(before),
        "state_sha256_after": canonical_state_sha(after),
        "unchanged_leaves_sha256_before": unchanged_leaves_sha(before, changed_paths),
        "unchanged_leaves_sha256_after": unchanged_leaves_sha(after, changed_paths),
        "placed_rows": rows_after,
        "resources_before": resources_before,
        "resources_after": resources_after,
        "resource_neutral": True,
    }


def printed_branch_lines(stdout_path: Path) -> List[str]:
    """Every printed line the branch itself emitted, in order.

    These lines are evidence, not decoration: the third argument's display-only
    nature is visible only here, because the two- and three-argument forms are
    indistinguishable in the state and distinguishable only in the output.  They
    are recorded verbatim and never parsed.

    The match is on the **command name inside the dispatcher's own trace line**,
    which was found to be the only filter that catches every branch print.  An
    earlier filter matched on a trailing ``xp``, which silently dropped the
    three-argument form's line (``... +5xp BOUGHT LEVEL UP -> 9``) -- that is,
    it dropped the single line this method exists to record.
    """
    try:
        text = stdout_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    marker = "COMMAND: %s(" % ADD_XP_UNIT_COMMAND
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if marker in stripped:
            out.append(stripped)
    return out


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    out: Dict[str, Dict[str, object]] = {}
    for name in PROTECTED_FIXTURES:
        path = REPO_ROOT / "tests" / "fixtures" / name
        entries: List[Tuple[str, str]] = []
        count = 0
        if path.is_dir():
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    entries.append((str(item.relative_to(path)), sha256_file(item)))
                    count += 1
        out[name] = {"files": count, "sha256": canonical_digest(entries)}
    return out


def publish(staging: Path, out_dir: Path) -> None:
    """Replace this command's own outputs, preserving the hand-authored README.

    Deliberately the same scope as the shared harness's ``clear_previous_fixtures``
    -- ``steps/`` and ``capture-manifest.json`` only.  A wholesale directory
    replace was the first thing tried here and it silently deleted the README on
    every rerun: the README carries prose and measured figures that no run can
    regenerate, so wiping it would make the fixture unreproducible in the one way
    that matters most.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("steps", "capture-manifest.json"):
        target = out_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    shutil.copytree(staging / "steps", out_dir / "steps")
    shutil.copy2(staging / "capture-manifest.json", out_dir / "capture-manifest.json")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="fixture output directory (default: %(default)s)",
    )
    args_ns = parser.parse_args(argv)
    out_dir: Path = args_ns.out

    if not SEED_SAVE.is_file():
        print("capture: missing village seed save: %s" % SEED_SAVE, file=sys.stderr)
        return EXIT_ENVIRONMENT

    seed = json.loads(SEED_SAVE.read_text(encoding="utf-8"))
    if not isinstance(seed, dict):
        print("capture: village seed is not a JSON object: %s" % SEED_SAVE, file=sys.stderr)
        return EXIT_ENVIRONMENT

    # Assert the committed corpus really carries what this fixture assumes,
    # before a single server starts.  A corpus change must fail at environment
    # exit rather than produce a plausible-looking wrong fixture.
    census = verify_seed(seed)

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
    pre_seed_sha = sha256_file(SEED_SAVE)

    staging = Path(tempfile.mkdtemp(prefix="compat-unit-xp-capture-staging-"))
    summaries: List[Dict[str, Any]] = []
    transcript: List[Dict[str, Any]] = []
    disposables: List[Path] = []

    print(
        "capture: seed %s (pid %s, %d placed rows)"
        % (SEED_SAVE.name, seed["playerInfo"]["pid"], len(seed["maps"][0]["items"]))
    )
    print(
        "capture: %d transactions, ONE disposable server each "
        "(sessions.load_saves() caches the corpus in memory at import, so a "
        "restored seed file is not enough)" % len(TRANSACTIONS)
    )

    try:
        for entry in TRANSACTIONS:
            name = entry["name"]
            step_dir = staging / "steps" / ("txn_%s" % name)
            disposable: Optional[Path] = None
            process = None
            stdout_path = None
            try:
                disposable, pid, seed_sha = build_disposable(
                    Path(tempfile.gettempdir()), SEED_SAVE
                )
                disposables.append(disposable)
                saves_dir = disposable / "saves"
                seed_group = save_group_record(saves_dir)
                if seed_sha != pre_seed_sha:
                    raise CaptureError(
                        EXIT_ENVIRONMENT,
                        "%s: the seeded save digest %r differs from the committed "
                        "seed's %r" % (name, seed_sha, pre_seed_sha),
                    )

                process, stdout_path, stderr_path = start_server(
                    disposable, {"PYTHONUNBUFFERED": "1"}
                )
                if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
                    raise CaptureError(
                        EXIT_SERVER,
                        "%s: legacy server did not become ready (exit=%s)\n"
                        "--- stdout ---\n%s\n--- stderr ---\n%s"
                        % (
                            name,
                            process.poll(),
                            read_tail(stdout_path),
                            read_tail(stderr_path),
                        ),
                    )

                save_path = saves_dir / ("%s.save.json" % pid)
                startup_group = save_group_record(saves_dir)
                if startup_group["sha256"] != seed_group["sha256"]:
                    raise CaptureError(
                        EXIT_ENVIRONMENT,
                        "%s: the corpus changed during server startup, so the "
                        "server is not reading the committed seed" % name,
                    )

                # --- login, exactly as a logged-in Flash client would ------
                login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
                login_result = http_request(
                    LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0
                )
                if login_result["status"] != 302:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: login expected HTTP 302, got %r"
                        % (name, login_result["status"]),
                    )
                cookie = extract_session_cookie(login_result)
                login_body = login_result.pop("body")
                after_login = json.loads(save_path.read_text(encoding="utf-8"))
                if canonical_state_sha(after_login) != canonical_state_sha(seed):
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the login step changed the corpus, so it is not a "
                        "neutral session step" % name,
                    )

                # --- the one add_xp_unit batch -----------------------------
                before = json.loads(save_path.read_text(encoding="utf-8"))
                envelope = build_envelope(list(entry["args"]))
                verify_envelope(envelope)
                form = {
                    "USERID": pid,
                    "user_key": USER_KEY,
                    "language": LANGUAGE,
                    "data": data_field(envelope),
                }
                result = http_request(
                    LEGACY_PORT,
                    "POST",
                    DYNAMIC_ROOT + "/command.php",
                    form=dict(form),
                    cookie=cookie,
                    timeout=30.0,
                )
                status = int(result["status"])
                body = result.pop("body")
                after = json.loads(save_path.read_text(encoding="utf-8"))

                facts = verify_transaction(
                    name,
                    list(entry["args"]),
                    before,
                    after,
                    int(entry["expect_status"]),
                    entry["expect_attr_before"],
                    entry["expect_attr_after"],
                    list(entry["expect_changed"]),
                    status,
                )

                if status == 200:
                    payload = json.loads(body.decode("utf-8"))
                    if payload != {"result": "success"}:
                        raise CaptureError(
                            EXIT_REQUEST,
                            "%s: response is not the legacy success result: %r"
                            % (name, payload),
                        )
                    facts["response_payload"] = payload
                else:
                    # A failing request answers the framework's plain error page.
                    # server.py runs with debug=False, so the body carries no
                    # traceback and no absolute path -- which is what makes this
                    # record byte-stable.  Asserted, not assumed.
                    text = body.decode("utf-8", errors="replace")
                    if str(disposable) in text:
                        raise CaptureError(
                            EXIT_REQUEST,
                            "%s: the error body leaks the disposable path, so it "
                            "cannot be committed verbatim" % name,
                        )
                    facts["response_payload"] = None
                    facts["failure_body_sha256"] = sha256_bytes(body)
                    facts["failure_is_framework_error_page"] = True

                lines = printed_branch_lines(stdout_path)
                facts["printed_branch_lines"] = lines
                facts["note"] = entry["note"]

                # --- write the step ------------------------------------------
                request_record = {
                    "captured_at_utc": iso_now(),
                    "method": result["method"],
                    "target": result["target"],
                    "path": result["path"],
                    "query": result["query"],
                    "form": {
                        key: (
                            sanitize_envelope_data(value)
                            if key == "data"
                            else (REDACTED if key in SENSITIVE_FORM_KEYS else value)
                        )
                        for key, value in (result["form"] or {}).items()
                    },
                    "headers_sent": sanitize_headers(result["headers_sent"]),
                    "scheme": "http",
                    "host": LEGACY_HOST,
                    "port": LEGACY_PORT,
                    "seed_save": SEED_SAVE.name,
                    "note": (
                        "Exact client request bytes are reconstructed from this "
                        "record; Host is set explicitly, no User-Agent header is "
                        "sent. The batch's arguments ARE the crafted, "
                        "client-supplied values under test -- that is the "
                        "finding, not an oversight. The resource vector is "
                        "NEUTRAL. ts is pinned to a constant so this record is "
                        "byte-stable; legacy parses it and never reads it. "
                        "user_key is redacted; accessToken is the crafted empty "
                        "placeholder, never a token value."
                    ),
                }
                response_record = {
                    "status": status,
                    "reason": result["reason"],
                    "headers": sanitize_headers(result["response_headers"]),
                    "body_bytes": len(body),
                    "body_sha256": sha256_bytes(body),
                    "captured_at_utc": iso_now(),
                }
                write_json(step_dir / "request.json", request_record)
                write_json(step_dir / "before.json", before)
                write_json(step_dir / "response.meta.json", response_record)
                write_bytes(step_dir / "response.body", body)
                write_json(step_dir / "after.json", after)
                write_json(step_dir / "transaction.json", facts)

                # The login step is recorded once, from the first transaction
                # only, because a fresh server means a fresh login for each --
                # and because a login that changes nothing is worth recording
                # once rather than twelve times.  Its neutrality is asserted for
                # every transaction above, so the elision loses no evidence.
                if name == TRANSACTIONS[0]["name"]:
                    login_request_record = {
                        "captured_at_utc": iso_now(),
                        "method": login_result["method"],
                        "target": login_result["target"],
                        "path": login_result["path"],
                        "query": login_result["query"],
                        "form": sanitize_form(login_result["form"] or {}),
                        "headers_sent": sanitize_headers(login_result["headers_sent"]),
                        "scheme": "http",
                        "host": LEGACY_HOST,
                        "port": LEGACY_PORT,
                        "note": (
                            "Session fidelity only. This step leaves the corpus "
                            "byte-identical, which the capture asserts for EVERY "
                            "transaction even though only this one is recorded."
                        ),
                    }
                    login_response_record = {
                        "status": int(login_result["status"]),
                        "reason": login_result["reason"],
                        "headers": sanitize_headers(login_result["response_headers"]),
                        "body_bytes": len(login_body),
                        "body_sha256": sha256_bytes(login_body),
                        "captured_at_utc": iso_now(),
                    }
                    login_dir = staging / "steps" / "login_post"
                    write_json(login_dir / "request.json", login_request_record)
                    write_json(login_dir / "before.json", seed)
                    write_json(login_dir / "response.meta.json", login_response_record)
                    write_bytes(login_dir / "response.body", login_body)
                    write_json(login_dir / "after.json", after_login)

                summaries.append(facts)
                transcript.append(
                    {
                        "name": name,
                        "disposable_pid_read_from_document": pid,
                        "seed_sha256": seed_sha,
                        "printed_branch_lines": lines,
                    }
                )
                print(
                    "capture: %-34s status=%-3d attr %s -> %s, changed leaves %d"
                    % (
                        name,
                        status,
                        json.dumps(facts["attr_before"], sort_keys=True),
                        json.dumps(facts["attr_after"], sort_keys=True),
                        facts["changed_leaf_count"],
                    )
                )
                for line in lines:
                    print("capture:   printed | %s" % line)
            finally:
                if process is not None:
                    server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
                    if server_error:
                        raise CaptureError(EXIT_SERVER, "%s: %s" % (name, server_error))

        # --- the display-only proof, asserted as a PAIR -------------------
        by_name = {entry["name"]: entry for entry in summaries}
        two = by_name.get("increment_existing")
        three = by_name.get("level_argument_ignored")
        if two is None or three is None:
            raise CaptureError(EXIT_REQUEST, "the argument-pair transactions are missing")
        pair = {
            "compared": ["increment_existing", "level_argument_ignored"],
            "same_attr_after": typed_equal(two["attr_after"], three["attr_after"]),
            "same_changed_leaves": two["changed_leaves"] == three["changed_leaves"],
            "same_state_sha256": two["state_sha256_after"] == three["state_sha256_after"],
            "printed_lines_differ": (
                two["printed_branch_lines"] != three["printed_branch_lines"]
            ),
            "printed_two": two["printed_branch_lines"],
            "printed_three": three["printed_branch_lines"],
        }
        if not (pair["same_attr_after"] and pair["same_changed_leaves"] and pair["same_state_sha256"]):
            raise CaptureError(
                EXIT_REQUEST,
                "the two- and three-argument forms did NOT produce identical "
                "post-states, so the third argument is not established as "
                "display-only: %r" % (pair,),
            )
        if not pair["printed_lines_differ"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the two- and three-argument forms printed identically, so the "
                "recorded difference cannot be demonstrated: %r" % (pair,),
            )
        print(
            "capture: third argument established display-only -- identical "
            "post-state and leaf set, differing printed line"
        )

        # --- containment, before publishing anything ----------------------
        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        post_fixtures = protected_fixture_snapshot()
        post_seed_sha = sha256_file(SEED_SAVE)

        if pre_combined != post_combined:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree containment changed:\n  before %s\n  after  %s"
                % (pre_combined, post_combined),
            )
        if pre_seed_sha != post_seed_sha:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "the committed village seed changed during the run",
            )
        changed_fixtures = sorted(
            name
            for name in PROTECTED_FIXTURES
            if pre_fixtures[name] != post_fixtures[name]
        )
        if changed_fixtures:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "already-committed fixtures changed during the run: %r" % (changed_fixtures,),
            )
        working_tree_saves = REPO_ROOT / "saves"
        if working_tree_saves.exists():
            raise CaptureError(
                EXIT_CONTAINMENT,
                "a working-tree saves/ directory exists; the run wrote outside "
                "its disposable",
            )

        # --- the manifest -------------------------------------------------
        manifest = {
            "schema": SCHEMA,
            "captured_at_utc": iso_now(),
            "purpose": (
                "Executed-legacy evidence for the single add_xp_unit branch "
                "(command.py:322-343). It records what the ORACLE does. It does "
                "NOT license a modern endpoint: the amount is a client argument "
                "with no validation, and the committed per-unit experience "
                "field is refuted as its source by three independent "
                "measurements (docs/legacy-unit-xp.md)."
            ),
            "invocation": "python -B apps/compat-api/capture_unit_xp_fixture.py",
            "interpreter": "CPython %d.%d (pinned)" % sys.version_info[:2],
            "server": {
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "process": "python -B server.py inside each disposable",
                "starts": len(TRANSACTIONS),
                "one_per_transaction": True,
                "one_per_transaction_reason": (
                    "sessions.load_saves() caches the corpus in a module global "
                    "at import, so a running server never re-reads the seed "
                    "file. Restoring the seed between probes on one server "
                    "leaves the in-memory corpus already mutated and silently "
                    "produces a different result."
                ),
                "debug": False,
                "debug_note": (
                    "server.py runs app.run(..., debug=False), so a failing "
                    "request answers the framework's plain error page with no "
                    "traceback and no absolute path. The capture asserts the "
                    "body does not leak the disposable path before committing "
                    "it."
                ),
                "env_extra": {"PYTHONUNBUFFERED": "1"},
                "env_extra_note": (
                    "Set for THIS capture's child processes only, via a "
                    "defaulted parameter on start_server. child_environment() "
                    "is untouched, so no existing capture's log changes. The "
                    "printed lines below are evidence -- the third argument's "
                    "display-only nature is visible nowhere else -- and block "
                    "buffering would lose them when the harness reaps the child."
                ),
            },
            "seed": {
                "path": str(SEED_SAVE.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": pre_seed_sha,
                "pid_read_from_document": SEED_EXPECTED_PID,
                "pid_note": (
                    "Read from playerInfo.pid in the document, never derived "
                    "from the filename stem: for three of the eight committed "
                    "village saves the two disagree, and for initial.json the "
                    "pid is null, which build_disposable refuses loudly rather "
                    "than writing a 'None.save.json'."
                ),
                "choice_status": "derived-provisional",
                "choice_reason": (
                    "Smallest of the five committed save documents carrying "
                    "attr['xp'] by placed-row count (319, against 569 / 367 / "
                    "549 / 576), and it carries 36 rows WITH the key and 283 "
                    "without it, including 12 unit rows with an empty bag and "
                    "271 building rows -- so both arms and both row kinds are "
                    "exercisable from one authentic committed save. Any other "
                    "of the five would also have worked; recorded so a rerun "
                    "reproduces the committed bytes."
                ),
                "census": census,
            },
            "batch_shape": {
                "command": ADD_XP_UNIT_COMMAND,
                "command_source": "command.py:322-343",
                "resource_vector": list(NEUTRAL_VECTOR),
                "vector_status": "neutral by construction, every transaction",
                "ts": FIXTURE_TS,
                "ts_note": (
                    "Pinned to a constant, as on the stored-placement capture. "
                    "The dispatcher parses it and never reads it."
                ),
                "arguments": (
                    "CRAFTED AND CLIENT-SUPPLIED. args[0] is the map key and "
                    "args[1] is the gain; the branch reads both with no "
                    "validation of any kind, not even int()."
                ),
            },
            "recorded_steps": list(RECORDED_STEPS) + ["login_post"],
            "login_step": (
                "Performed once per server (twelve times) and recorded once, "
                "from the first transaction. Its neutrality is asserted for "
                "EVERY transaction, so the elision loses no evidence."
            ),
            "transactions": summaries,
            "third_argument_pair": pair,
            "established": [
                "The two write arms: attr['xp'] += args[1] when the key is "
                "present, attr['xp'] = args[1] when it is absent.",
                "args[0] is the map key, args[1] is the gain, args[2] is "
                "optional; none is validated, not even with int().",
                "An unaddressable map key hits the falsy-item early return, "
                "prints an error and RETURNS -- and the server still answers "
                "the legacy success result.",
                "No clamp on a negative gain (unlike engine.apply_resources' "
                "max(..., 0)) and no bound on the amount.",
                "A float gain persists as a float.",
                "The branch is TYPE-AGNOSTIC: a building row accepts and "
                "stores unit experience exactly as a unit row does.",
                "The two arms are ASYMMETRIC on type: the assign arm persists "
                "a string, the increment arm raises TypeError against one.",
                "True is worth exactly +1, because the branch does arithmetic "
                "on the gain.",
                "The third argument has NIL stored effect: identical "
                "post-state, identical resource state and identical changed-leaf "
                "set, with a different printed line.",
                "Under a NEUTRAL vector, exactly one leaf moves on success and "
                "no stored resource moves at all.",
            ],
            "derived_provisional": [
                "That the two- and three-argument forms are INTERCHANGEABLE, "
                "because their stored effects were measured equal; the branch "
                "source shows a truthiness test feeding only an f-string.",
                "The choice of villages/AcidCaos.json as the disposable seed.",
            ],
            "not_claimed": [
                "Any award schedule, unit level, threshold, or per-unit "
                "experience source. No committed per-unit level schedule "
                "exists, and the committed units[].xp field is refuted as the "
                "award by three independent measurements.",
                "That the amounts recorded here are what a player earns. They "
                "are what a CLIENT SENT and the server accepted.",
                "Any resource movement. Every transaction ran under a neutral "
                "vector and moved nothing.",
                "Any server-authoritative validation. None exists: the branch "
                "has no range check, no bound, no type check, and no membership "
                "test.",
                "That this fixture implies a route. It does not, and the "
                "compat-side guard asserts that no unit-experience route is "
                "answered and no award helper exists.",
            ],
            "time_dependent_fields": {
                "request_captured_at_utc": (
                    "Recorded per step and necessarily volatile; it is the only "
                    "field in this fixture that changes between reruns, which "
                    "is why 'byte-identical rerun' is claimed for the "
                    "transaction records, states and manifest body, not for "
                    "these two fields."
                ),
                "captured_at_utc": "Same, in this manifest.",
                "ts": "Pinned to a constant, so not volatile.",
            },
            "containment": {
                "combined_before": pre_combined,
                "combined_after": post_combined,
                "identical": pre_combined == post_combined,
                "groups": sorted(pre_groups),
                "seed_sha256_before": pre_seed_sha,
                "seed_sha256_after": post_seed_sha,
                "working_tree_saves_absent": True,
                "protected_fixtures": sorted(PROTECTED_FIXTURES),
                "protected_fixtures_unchanged": True,
            },
            "cleanup": {
                "disposables": len(disposables),
                "note": (
                    "Each disposable is removed by the harness's own finally "
                    "block; the fixture is staged OUTSIDE the working tree and "
                    "published only after every check passed, so a failed run "
                    "writes nothing into the repository."
                ),
            },
            "transcript": transcript,
            "exit_code": EXIT_OK,
        }
        write_json(staging / "capture-manifest.json", manifest)
        publish(staging, out_dir)
        print("capture: fixture published to %s" % out_dir)
        print("capture: containment %s before and after (identical)" % pre_combined[:16])
        return EXIT_OK
    except CaptureError as error:
        print("capture: %s" % error, file=sys.stderr)
        return error.exit_code
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        for path in disposables:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())