#!/usr/bin/env python3
"""Capture the executed-legacy combat-action fixture: ``end_attack`` and both kills.

Contract: ``docs/legacy-m10-combat.md`` (OpenSpec change ``combat-actions``,
task group 2).  Read that record for the measurements; this module executes them
and refuses to publish unless every one reproduces.

Thirteen transactions across **two** committed village documents and **one
disposable legacy server each**.  The two seeds are not interchangeable, and
that is the reason this capture needs more than one:

* ``villages/AcidCaos.json`` -- 319 placed rows, **48** eligible unit rows, and an
  **empty** ``deadHeroes`` ledger.  Used for every transaction whose finding is a
  **destruction**: it is the only committed document where the ledger's
  key-creation branch and the "first eligible row" selection are both observable
  from nothing.
* ``villages/Neutral.json`` -- 549 placed rows, **87** eligible unit rows, and a
  **28**-key ledger.  Used for every transaction whose finding is a **ledger
  increment**: it is the only committed document where the key already exists, so
  ``before -> before + 1`` is observable rather than inferred.

**One server per transaction is not an optimisation, it is the only correct
shape.**  ``sessions.load_saves()`` caches the corpus in a module global at
import time, so a running server never re-reads the save file from disk.
Restoring the seed between probes on one server therefore leaves the *in memory*
corpus already mutated and silently produces a different result -- the
investigation that established this contract lost its first probes to exactly
that, which is why it is written into the design rather than left as folklore.

What this fixture establishes, and what it deliberately does not:

* **ESTABLISHED** -- that the branch derives its destruction count as
  ``max(0, unit[2] - unit[3])`` on two client numbers; that the count is applied
  **per tuple element** by a ``while qty > 0`` loop whose apparent safety is
  **exhaustion of matches, not a check**; that a row is selected by **item id
  plus a truthy team** and popped in the save's own **recorded map-key order**;
  that the ledger increment is behind **exactly two** committed gates; that
  ``kill`` deletes a row and **never** touches the ledger; and that ``kill_iid``
  contains no write statement at all.
* **ESTABLISHED, AND THE POINT OF DESIGN D3** -- that the branch's two unguarded
  absent-value dereferences sit on **opposite sides** of its write loop: omitting
  ``attacker_units`` raises before the loop is reached, while omitting ``victim``
  raises after ``map_lose_item`` already ran.  The **persisted** effect is the
  same either way, and a third transaction shows why: ``command.py`` dispatches
  the whole batch first and calls ``save_session`` only afterwards
  (``command.py:30,32``), so an exception **discards every mutation the batch
  made**.  The failure mode is a **discarded** save, not a partially applied one,
  and the persistence boundary is the **batch**, not the command.
* **A THIRD GUARD, FOUND BY MEASUREMENT** -- an **empty** blob short-circuits at
  ``command.py:818``'s ``if not response:`` with a success response and no change,
  so the very key that raises when the blob is non-empty is answered with
  *success* when the blob is empty.
* **A RECORDED DIVERGENCE** -- one transaction sends a client-computed count of
  two and the oracle destroys **two** rows where this capability derives
  **exactly one**.  It is recorded in the manifest as a divergence field, never as
  parity, and the capture asserts the difference rather than asserting parity.
* **NOT ESTABLISHED, AND NOT CLAIMED** -- any combat rule.  Nothing here resolves
  damage, health, defence, hit chance, an attack outcome, a mission, or a reward;
  every one of those committed fields measures zero legacy consumers.

No Flash, Ruffle, ActionScript, or browser executes.  Every network call is
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

SCHEMA = "combat-actions-fixture-v1"

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-combat-actions"

# The two disposable seeds, and why each exists.  ``verify_seed`` asserts every
# figure below against the committed document before a single server starts, so a
# corpus change fails loudly at environment exit rather than producing a
# plausible-looking wrong fixture.
SEED_DESTRUCTION = REPO_ROOT / "villages" / "AcidCaos.json"
SEED_LEDGER = REPO_ROOT / "villages" / "Neutral.json"

SEED_DESTRUCTION_PID = "AcidCaos"
SEED_DESTRUCTION_ROWS = 319
SEED_DESTRUCTION_UNIT_ROWS = 48
SEED_LEDGER_PID = "Neutral"
SEED_LEDGER_ROWS = 549
SEED_LEDGER_UNIT_ROWS = 87
SEED_LEDGER_KEYS = 28

# Pinned so the recorded ``data`` field is byte-stable across reruns.  ``ts`` is
# parsed and then **never read** by the legacy dispatcher, exactly as on the
# stored-placement and unit-experience captures.
FIXTURE_TS = 1700000000

# The three legacy commands this deliver line executes (established:
# command.py:808-885, 169-181, 183-187).
END_ATTACK_COMMAND = "end_attack"
KILL_COMMAND = "kill"
KILL_IID_COMMAND = "kill_iid"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).  Every batch here is
# NEUTRAL and always will be: no combat branch writes a resource, so a non-zero
# slot could only be a client-sent mint, and putting one on the same request as
# the combat finding would make the "no stored resource moved" proof ambiguous
# rather than strong.
NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]

# The derived ``victim`` the branch's final print reads a name out of
# (command.py:874).  The branch does `if "name" in victim`, so a payload omitting
# ``victim`` entirely leaves it None and raises TypeError -- which is precisely
# what transaction ``resolve_absent_victim`` records.
DERIVED_VICTIM_NAME = "derived"

# Item 1020 in ``AcidCaos.json`` is the **order-discriminating** choice.  Its
# seven eligible rows stand at map keys, in the save's own RECORDED order:
#   2425, 1022, 898, 3151, 3423, 897, 6627
# The first recorded key is **2425** while the numeric minimum is **897**.  A
# single-destruction transaction therefore removes 2425 under the recorded order
# the helper iterates and 897 under a sorted order -- so this one transaction
# makes "first by recorded map-key order" a claim about insertion order instead of
# a claim that happens to coincide with sorting.  It is the reason this capture
# needs a progressed save at all.
ORDER_ITEM_ID = 1020
ORDER_ELIGIBLE_KEYS_RECORDED = ["2425", "1022", "898", "3151", "3423", "897", "6627"]
ORDER_FIRST_RECORDED = "2425"
ORDER_NUMERIC_MIN = "897"

# Item 1034 in ``Neutral.json`` is the **ledger-increment** choice: 24 eligible
# rows and a ledger entry that already reads 4, so the transaction observes
# ``4 -> 5`` rather than the key-creation branch.
LEDGER_ITEM_ID = 1034
LEDGER_KEY_BEFORE = 4
LEDGER_ELIGIBLE_COUNT = 24
LEDGER_FIRST_KEY = "37521"

# Item 1023 in ``Neutral.json`` is the **ledger-key-creation** choice: three
# eligible rows and NO ledger entry, so the transaction observes the key being
# created at 1 and the key count moving 28 -> 29.
CREATE_ITEM_ID = 1023
CREATE_FIRST_KEY = "20239"
CREATE_ELIGIBLE_COUNT = 3

# Item 923 is a committed **unit** legacy_id carrying no placed row in either
# seed, which makes the "the oracle had nothing to destroy" transaction genuine
# rather than an identity no document ever used.
ABSENT_ITEM_ID = 923

# A committed unit row in AcidCaos (item 1076, key 1639) used by ``kill``, and an
# item id the same row carries, used by ``kill_iid``.
KILL_MAP_KEY = 1639
KILL_ROW_ITEM_ID = 1076
KILL_IID_ITEM_ID = 1076

# Not a key in either committed corpus.
KILL_ABSENT_MAP_KEY = 999999

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

# The seven stored resource slots with their save locations, exactly as
# engine.apply_resources reads and writes them (engine.py:251-271).  Note the
# three different owners: five on the map, ``cash`` on playerInfo and ``mana``
# on privateState -- getting that wrong would silently read a missing key.
RESOURCE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
}

# The save location of the dead-hero ledger.
LEDGER_LOCATION = ("privateState", "deadHeroes")

# Already-committed fixture directories whose bytes this run must not change.
PROTECTED_FIXTURES = (
    "godot-building-collect",
    "godot-building-construction",
    "godot-building-expand",
    "godot-building-move",
    "godot-building-placement",
    "godot-building-sell",
    "godot-building-store",
    "godot-building-upgrade",
    "godot-building-xp",
    "godot-compatibility-boot",
    "godot-item-purchase",
    "godot-quests",
    "godot-research",
    "godot-stored-item-placement",
    "godot-tutorial",
    "godot-unit-collection",
    "godot-unit-experience",
    "godot-unit-queues",
)


# --- the recorded transactions ---------------------------------------------
# Every row is CRAFTED and CLIENT-SUPPLIED on purpose: ``attacker_units`` is the
# one key the legacy branch uses for anything, so crafting it is the finding, not
# an oversight.  What the modern endpoint does with it is a different, refused
# question.
#
# ``expect`` is the oracle's own post-state, recomputed and asserted.  ``modern``
# states what this capability derives instead, and where the two differ the
# transaction is marked ``divergence`` -- never ``parity``.
TRANSACTIONS: List[Dict[str, Any]] = [
    {
        "name": "resolve_first_by_recorded_order",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "units": [[ORDER_ITEM_ID, 0, 1, 0]],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": [ORDER_FIRST_RECORDED],
        "expect_ledger": {str(ORDER_ITEM_ID): 1},
        "expect_rows_after": SEED_DESTRUCTION_ROWS - 1,
        "modern_derives_removed_keys": [ORDER_FIRST_RECORDED],
        "modern_derives_ledger": {str(ORDER_ITEM_ID): 1},
        "parity": True,
        "note": (
            "The whole selection rule in one transaction. The blob names only an "
            "item identity, the helper matches slot 0 == 1020 AND a truthy slot 7, "
            "and it pops the FIRST match in the save's own recorded map-key order "
            "-- key 2425, not the numeric minimum 897. That difference is the "
            "point: an implementation that sorted would remove 897 and still "
            "produce a plausible-looking fixture. The ledger key is CREATED at 1 "
            "by the committed resurrectable gate."
        ),
    },
    {
        "name": "resolve_absent_attacker_units",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "raw_payload": '{"win":true}',
        "victim": False,
        "expect_status": 500,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "raises_before_write": True,
        "note": (
            "A NON-EMPTY blob with no attacker_units reaches the `for unit in "
            "attacker_units` line at command.py:866 with attacker_units still None "
            "-- `if \"attacker_units\" in response:` was false, so the local kept "
            "its None default -- and iterating None raises TypeError. The response "
            "is HTTP 500 and the save is byte-identical, because the raise lands "
            "BEFORE map_lose_item is reached. This is the first of the branch's two "
            "unguarded absent-value dereferences and the reason the delivered "
            "endpoint's refusals are indistinguishable from this one by state."
        ),
    },
    {
        "name": "resolve_empty_payload",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "raw_payload": "{}",
        "victim": False,
        "expect_status": 200,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "note": (
            "A THIRD guard, found by measurement rather than by reading the branch: "
            "an EMPTY blob short-circuits at command.py:818's `if not response:` "
            "before the write loop is ever reached, printing 'Error: Failed to "
            "parse command.' and RETURNING -- so the same omitted key that raises "
            "when the blob is non-empty is answered with SUCCESS when the blob is "
            "empty. Three different responses, three different amounts of damage: "
            "empty blob -> success and no change; non-empty blob without "
            "attacker_units -> 500 and no change; non-empty blob without victim -> "
            "500 WITH the row destroyed and the ledger incremented."
        ),
    },
    {
        "name": "resolve_absent_victim",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "units": [[ORDER_ITEM_ID, 0, 1, 0]],
        "victim": False,
        "expect_status": 500,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "raises_after_in_memory_write": True,
        "note": (
            "The second unguarded absent-value dereference, and the one that sits "
            "AFTER the write loop in SOURCE order: the rows are gone from the "
            "in-memory save and the ledger has been incremented by the time "
            "command.py:874's `if \"name\" in victim` raises TypeError on None. The "
            "persisted save is nevertheless BYTE-IDENTICAL, and that is the real "
            "finding: command.py dispatches the whole batch first and calls "
            "save_session only after the loop (command.py:30,32), so an exception "
            "anywhere in the batch skips persistence and discards EVERY mutation "
            "the batch made. Recorded here rather than asserted from the source, "
            "and paired with resolve_batch_discarded_on_raise, which shows the same "
            "discard with a SECOND command that would otherwise have persisted."
        ),
    },
    {
        "name": "resolve_batch_discarded_on_raise",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "extra_batch": {
            "command": END_ATTACK_COMMAND,
            "raw_payload": '{"win":true}',
            "victim": False,
        },
        "units": [[ORDER_ITEM_ID, 0, 1, 0]],
        "victim": True,
        "expect_status": 500,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "raises_after_in_memory_write": True,
        "note": (
            "A TWO-COMMAND batch whose FIRST command is valid and destroys a row, "
            "and whose SECOND raises. The in-memory save is mutated twice over and "
            "the client gets HTTP 500 -- yet the persisted save is still "
            "byte-identical, because save_session runs only after the dispatch loop "
            "completes. This is the sharper statement of the same fact: the failure "
            "mode is NOT a partially applied save, it is a DISCARDED one, and it "
            "discards the whole batch rather than the failing command alone."
        ),
    },
    {
        "name": "resolve_empty_attacker_units",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "units": [],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "note": (
            "An EMPTY attacker_units list means the loop body never runs: no row "
            "is destroyed and the ledger does not move, while the server still "
            "answers success and still prints its final battle line. Recorded so "
            "'a resolve removes a row' is not read as unconditional -- the oracle "
            "answers the same success for a request that names nothing."
        ),
    },
    {
        "name": "client_dictated_count_two",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "units": [[ORDER_ITEM_ID, 0, 3, 1]],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": ["2425", "1022"],
        "expect_ledger": {str(ORDER_ITEM_ID): 2},
        "expect_rows_after": SEED_DESTRUCTION_ROWS - 2,
        "modern_derives_removed_keys": [ORDER_FIRST_RECORDED],
        "modern_derives_ledger": {str(ORDER_ITEM_ID): 1},
        "parity": False,
        "divergence": (
            "THE CENTRAL DIVERGENCE, MEASURED. The client sent A=3 and B=1, so "
            "the oracle computed max(0, 3 - 1) == 2 and destroyed TWO rows, "
            "incrementing the ledger twice. This capability destroys EXACTLY ONE "
            "row and increments once. Reproducing the subtraction would make this "
            "server a pass-through for a client-computed casualty figure, which is "
            "the AGENTS.md Bad pattern. The oracle's apparent safety is EXHAUSTION "
            "OF MATCHES, not a check: engine.py:218-227 loops `while qty > 0` and "
            "returns the moment one pass finds no match, so a client asking for a "
            "thousand removes a thousand while any match remains."
        ),
        "note": (
            "This is the transaction that measures the design D1/D2 decision "
            "instead of asserting it. It also shows the increment is PER POPPED "
            "ROW, not per request: one request, one tuple, two ledger counts."
        ),
    },
    {
        "name": "resolve_no_eligible_row",
        "seed": "destruction",
        "command": END_ATTACK_COMMAND,
        "units": [[ABSENT_ITEM_ID, 0, 1, 0]],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "modern_refuses": "no_eligible_row",
        "note": (
            "Item 923 is a committed unit legacy_id with no placed row in this "
            "document, so map_lose_item finds nothing and RETURNS while the server "
            "still answers success -- the exhaustion path, reached from the front "
            "instead of from inside a loop. The delivered endpoint refuses it "
            "instead of reproducing it, which is a recorded divergence from the "
            "response and a parity match from the state."
        ),
        "printed_but_destroyed_nothing": True,
    },
    {
        "name": "kill_unit_row",
        "seed": "destruction",
        "command": KILL_COMMAND,
        "args": [KILL_MAP_KEY, 0],
        "expect_status": 200,
        "expect_removed_keys": [str(KILL_MAP_KEY)],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS - 1,
        "modern_derives_removed_keys": [str(KILL_MAP_KEY)],
        "modern_derives_ledger": {},
        "parity": True,
        "note": (
            "kill deletes the addressed row by MAP KEY -- not by item identity -- "
            "and NEVER touches the ledger. The seed's ledger is empty, so this "
            "transaction cannot by itself prove the non-participation; that claim "
            "rests on the branch holding no reference to "
            "privateState['deadHeroes'] and no call to push_dead_unit at all, which "
            "is a property of the source rather than an observation of one request."
        ),
    },
    {
        "name": "kill_missing_row",
        "seed": "destruction",
        "command": KILL_COMMAND,
        "args": [KILL_ABSENT_MAP_KEY, 0],
        "expect_status": 200,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "modern_refuses": "unaddressable_row",
        "note": (
            "An unaddressable map key hits map_get_item's falsy branch, prints "
            "'Error: item not found.' and RETURNS -- and the server still answers "
            "the legacy success result. A client cannot distinguish this from a "
            "real deletion by the response alone. The delivered endpoint refuses it "
            "instead, which is a recorded divergence and not parity."
        ),
    },
    {
        "name": "kill_iid_no_op",
        "seed": "destruction",
        "command": KILL_IID_COMMAND,
        "args": [KILL_IID_ITEM_ID, 0],
        "expect_status": 200,
        "expect_removed_keys": [],
        "expect_ledger": {},
        "expect_rows_after": SEED_DESTRUCTION_ROWS,
        "modern_derives_removed_keys": [],
        "modern_derives_ledger": {},
        "parity": True,
        "note": (
            "kill_iid's ENTIRE BODY is one print (command.py:183-187): it contains "
            "no write statement at all, so nothing can move. That is a stronger "
            "statement than any single request showing no change, and it is why "
            "this line delivers the command as a proven no-op rather than refusing "
            "it. Its INTENT is unknown -- nothing observes whether a real client "
            "sent it."
        ),
    },
    {
        "name": "ledger_increment_existing",
        "seed": "ledger",
        "command": END_ATTACK_COMMAND,
        "units": [[LEDGER_ITEM_ID, 0, 1, 0]],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": [LEDGER_FIRST_KEY],
        "expect_ledger": {str(LEDGER_ITEM_ID): LEDGER_KEY_BEFORE + 1},
        "expect_ledger_keys_after": SEED_LEDGER_KEYS,
        "expect_rows_after": SEED_LEDGER_ROWS - 1,
        "modern_derives_removed_keys": [LEDGER_FIRST_KEY],
        "modern_derives_ledger": {str(LEDGER_ITEM_ID): LEDGER_KEY_BEFORE + 1},
        "parity": True,
        "note": (
            "The increment branch, on the only committed document where the ledger "
            "key ALREADY EXISTS. Item 1034 reads 4 and becomes 5, while all 28 "
            "ledger keys survive -- so the count moved without the key count "
            "moving, which is the pair that distinguishes an increment from a "
            "creation. 24 eligible rows exist and exactly one is destroyed."
        ),
    },
    {
        "name": "ledger_key_created",
        "seed": "ledger",
        "command": END_ATTACK_COMMAND,
        "units": [[CREATE_ITEM_ID, 0, 1, 0]],
        "victim": True,
        "expect_status": 200,
        "expect_removed_keys": [CREATE_FIRST_KEY],
        "expect_ledger": {str(CREATE_ITEM_ID): 1},
        "expect_ledger_keys_after": SEED_LEDGER_KEYS + 1,
        "expect_rows_after": SEED_LEDGER_ROWS - 1,
        "modern_derives_removed_keys": [CREATE_FIRST_KEY],
        "modern_derives_ledger": {str(CREATE_ITEM_ID): 1},
        "parity": True,
        "note": (
            "The creation branch on the SAME document: item 1023 has three "
            "eligible rows and no ledger entry, so the key is created at 1 and the "
            "key count moves 28 -> 29 with every existing entry preserved, in "
            "order, and not deduplicated. Together with ledger_increment_existing "
            "this is what makes 'the ledger moved' a value-level claim rather than "
            "a key-count coincidence."
        ),
    },
]

RECORDED_STEPS = tuple("txn_%s" % entry["name"] for entry in TRANSACTIONS)


# --- helpers ---------------------------------------------------------------


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that refuses to conflate ``1``, ``1.0`` and ``True``.

    ``==`` would call all three equal, and this fixture's point is that the
    legacy server persists whatever it is handed.  ``bool`` is checked before
    ``int`` because ``isinstance(True, int)`` is true.
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
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
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
    return canonical_digest(
        [(path, payload_json(value)) for path, value in leaf_items(document)]
    )


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

    This is the load-bearing half of the "only the claimed leaves moved" proof:
    it is what makes the claim mechanical rather than a statement about the
    destroyed row alone.
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
                "save has no %s resource slot at %r" % (name, "/".join(location)),
            )
    return out


def placed_row_count(document: Dict[str, Any]) -> int:
    try:
        return len(document["maps"][0]["items"])
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "save has no maps[0].items: %s" % error)


def read_at(document: Dict[str, Any], location: Tuple[str, ...]) -> Any:
    """The value at a save location, or the sentinel string ``"<absent>"``."""
    cursor: Any = document
    for step in location:
        if not isinstance(cursor, dict) or step not in cursor:
            return "<absent>"
        cursor = cursor[step]
    return cursor


def recorded_ledger(document: Dict[str, Any]) -> Dict[str, int]:
    """``privateState['deadHeroes']`` as a fresh ``{string key: int}`` map."""
    ledger = read_at(document, LEDGER_LOCATION)
    if ledger == "<absent>":
        return {}
    if not isinstance(ledger, dict):
        raise CaptureError(EXIT_REQUEST, "deadHeroes is %r, not an object" % (ledger,))
    return {str(key): value for key, value in ledger.items()}


def map_keys_in_recorded_order(document: Dict[str, Any]) -> List[str]:
    """Every placed map key in the save's own recorded (insertion) order.

    This is the order ``for index in map_items`` walks, and therefore the order
    ``map_lose_item`` pops from.  It is **not** a sort: the committed seeds
    contain out-of-order insertions, which is the whole reason
    ``resolve_first_by_recorded_order`` exists.
    """
    try:
        return [str(key) for key in document["maps"][0]["items"]]
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "save has no maps[0].items: %s" % error)


def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value) for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value) for key, value in headers.items()
    }


def sanitize_envelope_data(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The live request always sends the real bytes; only the record is redacted.
    ``ts`` is deliberately NOT redacted -- it is pinned to a constant, which is
    what makes the recorded field byte-stable.
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


def combat_payload(
    units: Optional[List[Any]] = None, victim: bool = True, raw: Optional[str] = None
) -> str:
    """The crafted client blob ``end_attack`` parses out of ``args[0]``.

    ``raw`` sends verbatim text, which is how the two absent-value transactions
    exercise the branch's own unguarded dereferences instead of a shape this
    helper would normalise away.
    """
    if raw is not None:
        return raw
    blob: Dict[str, Any] = {}
    if units is not None:
        blob["attacker_units"] = [list(unit) for unit in units]
    if victim:
        blob["victim"] = {"name": DERIVED_VICTIM_NAME}
    return payload_json(blob)


def build_envelope(pairs: List[Tuple[str, List[Any]]]) -> Dict[str, Any]:
    """Derive the six-key batch envelope carrying the transaction's commands.

    The commands' own arguments are the **crafted, client-supplied** ones under
    test -- which is the whole problem.  ``end_attack`` reads its blob out of
    ``args[0]`` with no validation of any kind, so this function does no checking
    beyond the batch shape.  The resource vector is NEUTRAL and always will be:
    see :data:`NEUTRAL_VECTOR`.

    The batch envelope's keys are the shared protocol primitives, imported
    unchanged from the root envelope module; nothing here reimplements them.
    """
    envelope = {
        "first_number": 0,
        "publishActions": [],
        "ts": FIXTURE_TS,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [0, command, list(arguments), list(NEUTRAL_VECTOR)]
            for command, arguments in pairs
        ],
    }
    if sorted(envelope) != sorted(ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "batch envelope keys drifted from the shared protocol: %r"
            % (sorted(envelope),),
        )
    return envelope


def verify_envelope(envelope: Dict[str, Any], pairs: List[Tuple[str, List[Any]]]) -> None:
    """Refuse a batch this line does not intend to record."""
    try:
        parsed = parse_data_field(data_field(envelope))
    except EnvelopeError as error:
        raise CaptureError(EXIT_REQUEST, "crafted envelope is malformed: %s" % error)
    commands = parsed.get("commands")
    if not isinstance(commands, list) or len(commands) != len(pairs):
        raise CaptureError(
            EXIT_REQUEST,
            "batch must carry exactly %d commands, got %r" % (len(pairs), commands)
        )
    for entry, (command, _arguments) in zip(commands, pairs):
        if not isinstance(entry, list) or len(entry) != 4:
            raise CaptureError(
                EXIT_REQUEST, "command must be a 4-element list, got %r" % (entry,)
            )
        if entry[1] != command:
            raise CaptureError(
                EXIT_REQUEST, "command is %r, not %r" % (entry[1], command)
            )
        if entry[3] != NEUTRAL_VECTOR:
            raise CaptureError(
                EXIT_REQUEST,
                "resource vector is %r, not the neutral %r" % (entry[3], NEUTRAL_VECTOR),
            )


def command_arguments(entry: Dict[str, Any]) -> List[Tuple[str, List[Any]]]:
    """The ordered ``(command, args)`` pairs this transaction dispatches.

    One pair for every transaction except ``resolve_batch_discarded_on_raise``,
    which appends a SECOND command that raises -- the only way to observe whether
    persistence is per command or per batch.
    """
    pairs: List[Tuple[str, List[Any]]] = []
    command = str(entry["command"])
    if command == END_ATTACK_COMMAND:
        blob = combat_payload(
            units=entry.get("units"),
            victim=bool(entry.get("victim", True)),
            raw=entry.get("raw_payload"),
        )
        # args[1] is bound to the local `unknown` and NEVER read by the branch
        # (command.py:810).  It is sent as 0 and the fixture does not claim
        # anything about it.
        pairs.append((command, [blob, 0]))
    else:
        pairs.append((command, list(entry["args"])))

    extra = entry.get("extra_batch")
    if extra is not None:
        extra_command = str(extra["command"])
        if extra_command != END_ATTACK_COMMAND:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "extra_batch only supports end_attack, got %r" % (extra_command,)
            )
        pairs.append(
            (
                extra_command,
                [
                    combat_payload(
                        units=extra.get("units"),
                        victim=bool(extra.get("victim", True)),
                        raw=extra.get("raw_payload"),
                    ),
                    0,
                ],
            )
        )
    return pairs


def eligible_keys(document: Dict[str, Any], item_id: int) -> List[str]:
    """The rows ``map_lose_item`` would consider, in the order it would pop them.

    Eligibility is exactly the helper's own two conditions (engine.py:221) and the
    order is the save's own recorded map-key order.
    """
    out: List[str] = []
    items = document["maps"][0]["items"]
    for key in items:
        row = items[key]
        if not isinstance(row, list) or len(row) != 8:
            continue
        if row[0] != item_id:
            continue
        if not row[7]:
            continue
        out.append(str(key))
    return out


def verify_seed(seed: Dict[str, Any], which: str) -> Dict[str, Any]:
    """Assert the committed corpus really carries what this fixture assumes.

    Every figure here is a property of the committed document and is checked
    before anything executes, so a corpus change fails loudly at environment exit
    rather than producing a plausible-looking wrong fixture.
    """
    items = seed["maps"][0]["items"]
    ledger = recorded_ledger(seed)
    recorded_order = map_keys_in_recorded_order(seed)
    order_eligible = eligible_keys(seed, ORDER_ITEM_ID)

    census: Dict[str, Any] = {
        "which": which,
        "pid": str(seed["playerInfo"]["pid"]),
        "placed_rows": placed_row_count(seed),
        "ledger_keys": len(ledger),
        "ledger_is_empty": not ledger,
        "recorded_map_key_order_is_sorted": recorded_order == sorted(recorded_order, key=int),
        "state_sha256": canonical_state_sha(seed),
    }

    if which == "destruction":
        census["order_item_id"] = ORDER_ITEM_ID
        census["order_eligible_keys_recorded"] = order_eligible
        census["order_first_recorded"] = order_eligible[0] if order_eligible else None
        census["order_numeric_min"] = min(order_eligible, key=int) if order_eligible else None
        census["order_rows_discriminating"] = (
            order_eligible[0] != min(order_eligible, key=int) if order_eligible else False
        )
        census["kill_row_item_id"] = (
            seed["maps"][0]["items"][str(KILL_MAP_KEY)][0]
            if str(KILL_MAP_KEY) in items
            else None
        )
        census["kill_absent_key_present"] = str(KILL_ABSENT_MAP_KEY) in items
        census["absent_item_id_rows"] = len(eligible_keys(seed, ABSENT_ITEM_ID))

        if census["pid"] != SEED_DESTRUCTION_PID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "seed pid is %r, not the pinned %r" % (census["pid"], SEED_DESTRUCTION_PID),
            )
        if census["placed_rows"] != SEED_DESTRUCTION_ROWS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "seed carries %d placed rows, not the pinned %d"
                % (census["placed_rows"], SEED_DESTRUCTION_ROWS),
            )
        if not census["ledger_is_empty"]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the destruction seed's ledger is no longer empty (%d keys), so the "
                "key-CREATION branch would no longer be observable from nothing"
                % census["ledger_keys"],
            )
        if order_eligible != ORDER_ELIGIBLE_KEYS_RECORDED:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d's eligible rows stand at %r in recorded order, not the "
                "pinned %r -- the order-discriminating transaction no longer tests "
                "recorded order"
                % (ORDER_ITEM_ID, order_eligible, ORDER_ELIGIBLE_KEYS_RECORDED),
            )
        if not census["order_rows_discriminating"]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d's first recorded eligible key is %r, which is also its "
                "numeric minimum %r: a sorted implementation would now produce the "
                "same answer, so the transaction no longer discriminates"
                % (
                    ORDER_ITEM_ID,
                    order_eligible[0],
                    min(order_eligible, key=int),
                ),
            )
        if census["kill_row_item_id"] != KILL_ROW_ITEM_ID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "map key %d carries item %r, not the pinned %r"
                % (KILL_MAP_KEY, census["kill_row_item_id"], KILL_ROW_ITEM_ID),
            )
        if census["kill_absent_key_present"]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed corpus now contains map key %s, so the missing-row "
                "transaction would not test a missing row" % KILL_ABSENT_MAP_KEY,
            )
        if census["absent_item_id_rows"] != 0:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d now has %d placed rows, so the no-eligible-row transaction "
                "would not test an absent row"
                % (ABSENT_ITEM_ID, census["absent_item_id_rows"]),
            )
        return census

    if which == "ledger":
        census["ledger_item_id"] = LEDGER_ITEM_ID
        census["ledger_item_count_before"] = ledger.get(str(LEDGER_ITEM_ID), "<absent>")
        census["ledger_item_eligible_keys"] = len(eligible_keys(seed, LEDGER_ITEM_ID))
        census["ledger_item_first_key"] = (
            eligible_keys(seed, LEDGER_ITEM_ID) or [None]
        )[0]
        census["create_item_id"] = CREATE_ITEM_ID
        census["create_item_count_before"] = ledger.get(str(CREATE_ITEM_ID), "<absent>")
        census["create_item_eligible_keys"] = len(eligible_keys(seed, CREATE_ITEM_ID))
        census["create_item_first_key"] = (eligible_keys(seed, CREATE_ITEM_ID) or [None])[0]

        if census["pid"] != SEED_LEDGER_PID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "seed pid is %r, not the pinned %r" % (census["pid"], SEED_LEDGER_PID),
            )
        if census["placed_rows"] != SEED_LEDGER_ROWS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "seed carries %d placed rows, not the pinned %d"
                % (census["placed_rows"], SEED_LEDGER_ROWS),
            )
        if census["ledger_keys"] != SEED_LEDGER_KEYS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the ledger seed carries %d ledger keys, not the pinned %d"
                % (census["ledger_keys"], SEED_LEDGER_KEYS),
            )
        if census["ledger_item_count_before"] != LEDGER_KEY_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "ledger[%r] is %r, not the pinned %r, so the INCREMENT branch would "
                "not be observable"
                % (LEDGER_ITEM_ID, census["ledger_item_count_before"], LEDGER_KEY_BEFORE),
            )
        if census["ledger_item_eligible_keys"] != LEDGER_ELIGIBLE_COUNT:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d has %d eligible rows, not the pinned %d"
                % (LEDGER_ITEM_ID, census["ledger_item_eligible_keys"], LEDGER_ELIGIBLE_COUNT),
            )
        if census["ledger_item_first_key"] != LEDGER_FIRST_KEY:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d's first recorded eligible key is %r, not the pinned %r"
                % (LEDGER_ITEM_ID, census["ledger_item_first_key"], LEDGER_FIRST_KEY),
            )
        if census["create_item_count_before"] != "<absent>":
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "ledger[%r] already exists at %r, so the CREATION branch would not "
                "be observable"
                % (CREATE_ITEM_ID, census["create_item_count_before"]),
            )
        if census["create_item_eligible_keys"] != CREATE_ELIGIBLE_COUNT:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d has %d eligible rows, not the pinned %d"
                % (CREATE_ITEM_ID, census["create_item_eligible_keys"], CREATE_ELIGIBLE_COUNT),
            )
        if census["create_item_first_key"] != CREATE_FIRST_KEY:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "item %d's first recorded eligible key is %r, not the pinned %r"
                % (CREATE_ITEM_ID, census["create_item_first_key"], CREATE_FIRST_KEY),
            )
        return census

    raise CaptureError(EXIT_ENVIRONMENT, "unknown seed selector %r" % (which,))


def verify_transaction(
    entry: Dict[str, Any],
    before: Dict[str, Any],
    after: Dict[str, Any],
    status: int,
) -> Dict[str, Any]:
    """Structurally verify one executed transaction, or refuse to publish.

    Returns the machine-readable facts the manifest records.
    """
    name = str(entry["name"])
    if status != int(entry["expect_status"]):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: expected HTTP %d, got %d" % (name, entry["expect_status"], status),
        )

    # The removed keys, derived from the BEFORE document rather than asserted as a
    # literal, so the fixture states the rule and the capture checks it applies.
    if str(entry["command"]) == KILL_COMMAND:
        expected_removed = [str(int(entry["args"][0]))]
        if str(int(entry["args"][0])) not in map_keys_in_recorded_order(before):
            expected_removed = []
    elif str(entry["command"]) == KILL_IID_COMMAND:
        expected_removed = []
    else:
        expected_removed = list(entry["expect_removed_keys"])

    items_before = before["maps"][0]["items"]
    items_after = after["maps"][0]["items"]
    actually_removed = [
        key for key in items_before if str(key) not in set(map_keys_in_recorded_order(after))
    ]
    if sorted(actually_removed) != sorted(expected_removed):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the oracle removed rows %r, not the expected %r"
            % (name, sorted(actually_removed), sorted(expected_removed)),
        )
    if list(entry["expect_removed_keys"]) != actually_removed:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the oracle removed rows in the order %r, but the pinned expectation "
            "lists %r -- recorded-order assertions are order-sensitive on purpose"
            % (
                name,
                actually_removed,
                list(entry["expect_removed_keys"]),
            ),
        )

    rows_before = placed_row_count(before)
    rows_after = placed_row_count(after)
    if rows_after != int(entry["expect_rows_after"]):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: placed-row count is %d, not the expected %d (was %d)"
            % (name, rows_after, entry["expect_rows_after"], rows_before),
        )

    ledger_before = recorded_ledger(before)
    ledger_after = recorded_ledger(after)
    for key, value in entry["expect_ledger"].items():
        if not typed_equal(ledger_after.get(key, "<absent>"), value):
            raise CaptureError(
                EXIT_REQUEST,
                "%s: ledger[%r] is %r after the call, not the expected %r"
                % (name, key, ledger_after.get(key, "<absent>"), value),
            )
    expected_keys = entry.get("expect_ledger_keys_after")
    if expected_keys is not None and len(ledger_after) != int(expected_keys):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the ledger holds %d keys after the call, not the expected %d"
            % (name, len(ledger_after), expected_keys),
        )
    if not entry["expect_removed_keys"] and ledger_before != ledger_after:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the ledger moved %r -> %r while no row was destroyed, which "
            "contradicts the branch's only ledger writer" % (name, ledger_before, ledger_after),
        )

    diff = leaf_diff(before, after)
    changed_paths = [item[0] for item in diff]
    removed_paths = {
        path for path in changed_paths if path.startswith("/maps/0/items/")
    }
    ledger_prefix = "/privateState/deadHeroes/"
    ledger_paths = {
        path for path in changed_paths if path.startswith(ledger_prefix)
    }
    other_paths = set(changed_paths) - removed_paths - ledger_paths
    if other_paths:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: leaves outside the destroyed rows and the ledger also moved: %r"
            % (name, sorted(other_paths)),
        )

    # Nothing outside the claimed paths moved.  This is what makes "only the
    # claimed leaves moved" mechanical over the whole document.
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
                "%s: stored resource %s moved %r -> %r under a NEUTRAL vector, so "
                "this branch is not resource-neutral"
                % (name, key, resources_before[key], resources_after[key]),
            )

    return {
        "name": name,
        "seed": entry["seed"],
        "command": entry["command"],
        "status": status,
        "expected_status": int(entry["expect_status"]),
        "crafted_units": entry.get("units"),
        "crafted_args": entry.get("args"),
        "victim_supplied": bool(entry.get("victim", True)),
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": len(actually_removed),
        "removed_keys": actually_removed,
        "expected_removed_keys": list(entry["expect_removed_keys"]),
        "ledger_before": ledger_before,
        "ledger_after": ledger_after,
        "ledger_keys_before": len(ledger_before),
        "ledger_keys_after": len(ledger_after),
        "ledger_moved": ledger_before != ledger_after,
        "changed_leaf_count": len(changed_paths),
        "changed_leaves": diff_payload(diff),
        "state_sha256_before": canonical_state_sha(before),
        "state_sha256_after": canonical_state_sha(after),
        "unchanged_leaves_sha256_before": unchanged_leaves_sha(before, changed_paths),
        "unchanged_leaves_sha256_after": unchanged_leaves_sha(after, changed_paths),
        "resources_before": resources_before,
        "resources_after": resources_after,
        "resource_neutral": True,
        "parity_with_delivered_endpoint": bool(entry["parity"]),
        "modern_derives_removed_keys": entry["modern_derives_removed_keys"],
        "modern_derives_ledger": entry["modern_derives_ledger"],
    }


def printed_branch_lines(stdout_path: Path, command: str) -> List[str]:
    """Every printed line the branch itself emitted, in order.

    These lines are evidence, not decoration: the destruction count the oracle
    computed is visible ONLY here, because the branch reports it in a print and
    nowhere in its stored state beyond the rows it removed.  The client-count
    divergence is therefore readable directly in this list.

    The match is on the **command name inside the dispatcher's own trace line**,
    which was found to be the only filter that catches every branch print.
    """
    try:
        text = stdout_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    marker = "COMMAND: %s(" % command
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if marker in stripped:
            out.append(stripped)
    return out


def printed_destruction_counts(lines: List[str]) -> List[int]:
    """The destruction counts the branch printed, extracted from its own line.

    Only this line's own ``Lost <n>`` form counts, and an unparsable line is
    simply absent from the result rather than coerced -- a printed count the
    capture cannot read must not be reported as a count of zero.
    """
    out: List[int] = []
    for line in lines:
        body = line
        index = body.find("Lost ")
        if index < 0:
            continue
        token = body[index + len("Lost ") :].split(" ", 1)[0]
        if token.isdigit():
            out.append(int(token))
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

    Deliberately the same scope as the shared harness's
    ``clear_previous_fixtures`` -- ``steps/`` and ``capture-manifest.json`` only.
    A wholesale directory replace silently deletes the README on every rerun, and
    the README carries prose and measured figures no run can regenerate.
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

    for path in (SEED_DESTRUCTION, SEED_LEDGER):
        if not path.is_file():
            print("capture: missing village seed save: %s" % path, file=sys.stderr)
            return EXIT_ENVIRONMENT
    seeds: Dict[str, Dict[str, Any]] = {}
    for which, path in (("destruction", SEED_DESTRUCTION), ("ledger", SEED_LEDGER)):
        seed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(seed, dict):
            print("capture: village seed is not a JSON object: %s" % path, file=sys.stderr)
            return EXIT_ENVIRONMENT
        seeds[which] = seed

    # Assert the committed corpora really carry what this fixture assumes, before
    # a single server starts.
    censuses = {which: verify_seed(doc, which) for which, doc in seeds.items()}

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
    pre_seed_sha = {
        "destruction": sha256_file(SEED_DESTRUCTION),
        "ledger": sha256_file(SEED_LEDGER),
    }

    staging = Path(tempfile.mkdtemp(prefix="compat-combat-capture-staging-"))
    summaries: List[Dict[str, Any]] = []
    transcript: List[Dict[str, Any]] = []
    disposables: List[Path] = []

    print(
        "capture: seeds destruction=%s (%d rows, empty ledger) ledger=%s (%d rows, "
        "%d ledger keys)"
        % (
            SEED_DESTRUCTION.name,
            censuses["destruction"]["placed_rows"],
            SEED_LEDGER.name,
            censuses["ledger"]["placed_rows"],
            censuses["ledger"]["ledger_keys"],
        )
    )
    print(
        "capture: item %d's first RECORDED eligible row is %s while its numeric "
        "minimum is %s -- this is what makes the order claim testable"
        % (
            ORDER_ITEM_ID,
            censuses["destruction"]["order_first_recorded"],
            censuses["destruction"]["order_numeric_min"],
        )
    )
    print(
        "capture: %d transactions, ONE disposable server each "
        "(sessions.load_saves() caches the corpus in memory at import, so a "
        "restored seed file is not enough)" % len(TRANSACTIONS)
    )

    try:
        for entry in TRANSACTIONS:
            name = str(entry["name"])
            which = str(entry["seed"])
            seed_save = SEED_DESTRUCTION if which == "destruction" else SEED_LEDGER
            step_dir = staging / "steps" / ("txn_%s" % name)
            disposable: Optional[Path] = None
            process = None
            stdout_path = None
            try:
                disposable, pid, seed_sha = build_disposable(
                    Path(tempfile.gettempdir()), seed_save
                )
                disposables.append(disposable)
                saves_dir = disposable / "saves"
                seed_group = save_group_record(saves_dir)
                if seed_sha != pre_seed_sha[which]:
                    raise CaptureError(
                        EXIT_ENVIRONMENT,
                        "%s: the seeded save digest %r differs from the committed "
                        "seed's %r" % (name, seed_sha, pre_seed_sha[which]),
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
                        "%s: the corpus changed during server startup, so the server "
                        "is not reading the committed seed" % name,
                    )

                # --- login, exactly as a logged-in Flash client would -------
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
                if canonical_state_sha(after_login) != canonical_state_sha(seeds[which]):
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the login step changed the corpus, so it is not a "
                        "neutral session step" % name,
                    )

                # --- the one combat batch ----------------------------------
                before = json.loads(save_path.read_text(encoding="utf-8"))
                pairs = command_arguments(entry)
                envelope = build_envelope(pairs)
                verify_envelope(envelope, pairs)
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

                facts = verify_transaction(entry, before, after, status)

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

                lines = printed_branch_lines(stdout_path, str(entry["command"]))
                counts = printed_destruction_counts(lines)
                facts["printed_branch_lines"] = lines
                facts["printed_destruction_counts"] = counts
                facts["note"] = entry["note"]
                if entry.get("divergence"):
                    facts["divergence"] = entry["divergence"]
                if entry.get("modern_refuses"):
                    facts["delivered_endpoint_refusal"] = entry["modern_refuses"]

                # The printed count is the ONLY place the oracle's computed destruction count is
                # visible at all, and it is NOT a count of what it destroyed.  The
                # print at command.py:871 runs BEFORE map_lose_item at 872 and is
                # not conditional on it, so `Lost N` reports the count the client
                # asked for -- proven here by resolve_no_eligible_row, which prints
                # "Lost 1" while removing nothing.
                #
                # Three consequences, each asserted rather than assumed:
                #   1. the printed count ALWAYS equals the client's own
                #      max(0, A - B), which is what makes the client-dictated
                #      count readable from the transcript alone;
                #   2. rows removed is AT MOST the printed count, because
                #      map_lose_item stops on exhaustion;
                #   3. the two are EQUAL on a succeeding transaction only when
                #      enough matches existed.
                expected_count: Optional[int] = None
                if entry.get("units"):
                    expected_count = max(
                        0, int(entry["units"][0][2]) - int(entry["units"][0][3])
                    )
                if len(counts) == 1 and counts[0] != expected_count:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the branch printed a destruction count of %d, which "
                        "is not max(0, A - B) = %d for the crafted tuple"
                        % (name, counts[0], expected_count),
                    )
                if counts and len(counts) == 1:
                    if facts["rows_removed"] > counts[0]:
                        raise CaptureError(
                            EXIT_REQUEST,
                            "%s: %d rows disappeared for a printed request of %d, "
                            "so map_lose_item over-deleted"
                            % (name, facts["rows_removed"], counts[0]),
                        )
                    facts["printed_requested_count"] = counts[0]
                    facts["exhaustion_shortfall"] = counts[0] - facts["rows_removed"]
                if len(counts) == 1 and status != 200:
                    facts["in_memory_destruction_printed"] = counts[0]
                    facts["in_memory_destruction_persisted"] = False
                    facts["in_memory_vs_persisted_disagreement"] = (
                        "The branch printed a destruction of %d and performed it "
                        "against the in-memory save, while the persisted save "
                        "moved %d rows. Persistence runs after the whole dispatch "
                        "loop (command.py:30,32), so the exception discarded it."
                        % (counts[0], facts["rows_removed"])
                    )
                    if not entry.get("raises_after_in_memory_write"):
                        raise CaptureError(
                            EXIT_REQUEST,
                            "%s: failed with a printed destruction of %d but is not "
                            "marked raises_after_in_memory_write, so this fixture "
                            "would claim a discard it never established"
                            % (name, counts[0]),
                        )

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
                    "seed_save": seed_save.name,
                    "note": (
                        "Exact client request bytes are reconstructed from this "
                        "record; Host is set explicitly, no User-Agent header is "
                        "sent. The batch's arguments ARE the crafted, "
                        "client-supplied values under test -- that is the finding, "
                        "not an oversight. The resource vector is NEUTRAL. ts is "
                        "pinned to a constant so this record is byte-stable; legacy "
                        "parses it and never reads it. user_key is redacted; "
                        "accessToken is the crafted empty placeholder, never a "
                        "token value."
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
                # and because a login that changes nothing is worth recording once
                # rather than thirteen times.  Its neutrality is asserted for every
                # transaction above, so the elision loses no evidence.
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
                        "seed_save": seed_save.name,
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
                    write_json(login_dir / "before.json", seeds[which])
                    write_json(login_dir / "response.meta.json", login_response_record)
                    write_bytes(login_dir / "response.body", login_body)
                    write_json(login_dir / "after.json", after_login)

                summaries.append(facts)
                transcript.append(
                    {
                        "name": name,
                        "seed": which,
                        "disposable_pid_read_from_document": pid,
                        "seed_sha256": seed_sha,
                        "printed_branch_lines": lines,
                        "printed_destruction_counts": counts,
                    }
                )
                print(
                    "capture: %-32s status=%-3d rows %d -> %d (removed %s), ledger "
                    "keys %d -> %d, parity=%s"
                    % (
                        name,
                        status,
                        facts["rows_before"],
                        facts["rows_after"],
                        facts["removed_keys"],
                        facts["ledger_keys_before"],
                        facts["ledger_keys_after"],
                        facts["parity_with_delivered_endpoint"],
                    )
                )
                for line in lines:
                    print("capture:   printed | %s" % line)
            finally:
                if process is not None:
                    server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
                    if server_error:
                        raise CaptureError(EXIT_SERVER, "%s: %s" % (name, server_error))

        # --- the recorded divergence, asserted as a PAIR --------------------
        by_name = {str(item["name"]): item for item in summaries}
        one = by_name.get("resolve_first_by_recorded_order")
        two = by_name.get("client_dictated_count_two")
        if one is None or two is None:
            raise CaptureError(EXIT_REQUEST, "the divergence-pair transactions are missing")
        divergence = {
            "compared": ["resolve_first_by_recorded_order", "client_dictated_count_two"],
            "oracle_rows_removed_one": one["rows_removed"],
            "oracle_rows_removed_two": two["rows_removed"],
            "oracle_printed_counts": [
                one["printed_destruction_counts"],
                two["printed_destruction_counts"],
            ],
            "modern_derives_rows_removed": 1,
            "same_crafted_identity": (
                one["crafted_units"][0][0] == two["crafted_units"][0][0]
            ),
            "parity_claimed": False,
        }
        if divergence["oracle_rows_removed_one"] != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the single-destruction transaction removed %d rows, not one"
                % divergence["oracle_rows_removed_one"],
            )
        if divergence["oracle_rows_removed_two"] != 2:
            raise CaptureError(
                EXIT_REQUEST,
                "the client-dictated-count transaction removed %d rows, not the two "
                "its own max(0, A - B) computed: the central divergence is not "
                "reproducing, so the fixture would understate it"
                % divergence["oracle_rows_removed_two"],
            )
        if not divergence["same_crafted_identity"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the divergence pair addresses different item identities, so the "
                "difference is not attributable to the count: %r" % (divergence,)
            )
        print(
            "capture: divergence MEASURED -- the oracle removed %d and %d rows from "
            "the same identity while this capability derives exactly one"
            % (
                divergence["oracle_rows_removed_one"],
                divergence["oracle_rows_removed_two"],
            )
        )

        # --- the persistence boundary, asserted as a TRIPLE ----------------
        # The two absent-value dereferences sit on OPPOSITE SIDES of the write
        # loop in source order, and a THIRD transaction shows the persisted effect
        # is the same either way -- because save_session runs only after the whole
        # dispatch loop, so a raise discards the entire batch.  Asserting the
        # third is what stops the first two from being read as "partially applied".
        before_raise = by_name.get("resolve_absent_attacker_units")
        after_raise = by_name.get("resolve_absent_victim")
        batch_raise = by_name.get("resolve_batch_discarded_on_raise")
        if before_raise is None or after_raise is None or batch_raise is None:
            raise CaptureError(EXIT_REQUEST, "the persistence-boundary transactions are missing")
        bracket = {
            "compared": [
                "resolve_absent_attacker_units",
                "resolve_absent_victim",
                "resolve_batch_discarded_on_raise",
            ],
            "before_rows_removed": before_raise["rows_removed"],
            "after_rows_removed": after_raise["rows_removed"],
            "batch_rows_removed": batch_raise["rows_removed"],
            "before_state_unchanged": (
                before_raise["state_sha256_before"] == before_raise["state_sha256_after"]
            ),
            "after_state_unchanged": (
                after_raise["state_sha256_before"] == after_raise["state_sha256_after"]
            ),
            "batch_state_unchanged": (
                batch_raise["state_sha256_before"] == batch_raise["state_sha256_after"]
            ),
            "all_three_failed_with": 500,
            "in_memory_mutation_happened": True,
            "in_memory_mutation_evidence": (
                "The absent-victim and batch transactions both reach "
                "map_lose_item BEFORE their raise, so the in-memory save was "
                "mutated; the recorded state does not move because "
                "save_session(command.py:32) runs only after the dispatch loop "
                "completes, and an exception skips it. The persistence boundary "
                "is therefore the BATCH, not the command."
            ),
            "consequence_for_this_capability": (
                "A refused combat request must leave the persisted document "
                "byte-identical, which it does; but the reason is the batch "
                "boundary rather than a check inside the branch, so a delivered "
                "endpoint that dispatched a partial batch would differ. Every "
                "check here resolves before dispatch, which makes the refusal "
                "indistinguishable from the oracle's by persisted state."
            ),
        }
        if bracket["before_rows_removed"] != 0 or not bracket["before_state_unchanged"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the absent-attacker_units transaction did NOT leave the save "
                "untouched: %r" % (bracket,)
            )
        if bracket["after_rows_removed"] != 0 or not bracket["after_state_unchanged"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the absent-victim transaction moved the persisted save (%d rows, "
                "unchanged=%s): the batch-discard finding does not reproduce and the "
                "ordering guarantee's stated basis is wrong"
                % (bracket["after_rows_removed"], bracket["after_state_unchanged"]),
            )
        if bracket["batch_rows_removed"] != 0 or not bracket["batch_state_unchanged"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the two-command batch transaction moved the persisted save (%d "
                "rows, unchanged=%s): persistence is not per batch, so the "
                "discard finding is not established: %r"
                % (
                    bracket["batch_rows_removed"],
                    bracket["batch_state_unchanged"],
                    bracket,
                ),
            )
        # The positive proof that the in-memory mutation really happened: the
        # branch PRINTED a destruction while the persisted save did not move.
        # Without this, "the save was untouched" would be equally consistent with
        # the branch never having destroyed anything.
        bracket["printed_but_not_persisted"] = {
            "resolve_absent_victim": {
                "printed": after_raise.get("in_memory_destruction_printed"),
                "persisted_rows_removed": after_raise["rows_removed"],
            },
            "resolve_batch_discarded_on_raise": {
                "printed": batch_raise.get("in_memory_destruction_printed"),
                "persisted_rows_removed": batch_raise["rows_removed"],
            },
        }
        if after_raise.get("in_memory_destruction_printed") != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the absent-victim transaction printed %r destroyed, not the "
                "expected 1: without a printed destruction the discard finding has "
                "no positive evidence and the in-memory mutation never happened"
                % (after_raise.get("in_memory_destruction_printed"),)
            )
        if batch_raise.get("in_memory_destruction_printed") != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the batch transaction printed %r destroyed, not the expected 1"
                % (batch_raise.get("in_memory_destruction_printed"),)
            )
        print(
            "capture: persistence boundary established -- a raise on either side of "
            "the write loop, and after a VALID first command in the same batch, "
            "leaves the persisted save byte-identical"
        )

        no_eligible = by_name.get("resolve_no_eligible_row")
        if no_eligible is None:
            raise CaptureError(EXIT_REQUEST, "the exhaustion transaction is missing")
        if no_eligible["rows_removed"] != 0:
            raise CaptureError(
                EXIT_REQUEST,
                "the no-eligible-row transaction removed %d rows"
                % no_eligible["rows_removed"],
            )
        if no_eligible.get("printed_requested_count") != 1 or no_eligible.get(
            "exhaustion_shortfall"
        ) != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the no-eligible-row transaction printed %r and destroyed %d rows, "
                "so the exhaustion finding is not established: %r"
                % (
                    no_eligible.get("printed_requested_count"),
                    no_eligible["rows_removed"],
                    no_eligible.get("printed_branch_lines"),
                ),
            )
            raise CaptureError(
                EXIT_REQUEST,
                "%s: destroyed %d of a requested %d without being marked as the "
                "exhaustion case, so an unrecorded shortfall would ship as a "
                "normal transaction"
                % (name, facts["rows_removed"], facts["printed_requested_count"]),
            )
        print(
            "capture: exhaustion established -- the branch printed a requested "
            "destruction of 1 while removing nothing, so its printed count reports "
            "what it was ASKED for rather than what it did"
        )

        # --- the recorded-order discriminator, asserted ---------------------
        destruction_census = censuses["destruction"]
        order = {
            "item_id": ORDER_ITEM_ID,
            "eligible_keys_recorded": ORDER_ELIGIBLE_KEYS_RECORDED,
            "first_recorded": ORDER_FIRST_RECORDED,
            "numeric_min": ORDER_NUMERIC_MIN,
            "row_removed_by_the_oracle": one["removed_keys"],
            "row_a_sorted_implementation_would_remove": ORDER_NUMERIC_MIN,
            "recorded_order_discriminates": ORDER_FIRST_RECORDED != ORDER_NUMERIC_MIN,
        }
        if order["row_removed_by_the_oracle"] != [ORDER_FIRST_RECORDED]:
            raise CaptureError(
                EXIT_REQUEST,
                "the oracle removed %r, not the first RECORDED eligible row %r: the "
                "recorded-order claim does not reproduce"
                % (order["row_removed_by_the_oracle"], ORDER_FIRST_RECORDED),
            )
        if ORDER_FIRST_RECORDED == ORDER_NUMERIC_MIN:
            raise CaptureError(
                EXIT_REQUEST,
                "the recorded order no longer discriminates from a sort, so this "
                "claim is untestable",
            )
        if destruction_census["recorded_map_key_order_is_sorted"]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the destruction seed's recorded map-key order is now sorted, so the "
                "order claim cannot be distinguished from a sort",
            )
        print(
            "capture: recorded-order discriminator holds -- removed %s, a sorted "
            "implementation would have removed %s"
            % (ORDER_FIRST_RECORDED, ORDER_NUMERIC_MIN)
        )

        # --- WHERE THE ORDER OF RECORD LIVES, measured from the files -------
        # `write_json` (capture_legacy_fixtures.py:457) serialises every fixture
        # document with `sort_keys=True`, so a snapshot's `items` keys are in
        # LEXICOGRAPHIC order, not the save's own insertion order.  The oracle
        # never saw a snapshot: it walked the in-memory save, whose order is the
        # committed document's.  That makes the two orders genuinely different and
        # makes the recorded snapshots the WRONG place to read the selection
        # order from -- a replay suite that reset the corpus from `before.json`
        # would be replaying against the sorted order and would remove 1022
        # instead of 2425 while still matching the recorded document.
        #
        # This is recorded here, from the published files, rather than left as a
        # trap: the discriminator above is measured from the committed document
        # and this block proves the two orders really are different, so the
        # recorded order claim cannot be silently satisfied by the sort.
        snapshot_document = json.loads(
            (staging / "steps" / ("txn_%s" % TRANSACTIONS[0]["name"]) / "before.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot_order = list(snapshot_document["maps"][0]["items"])
        committed_order = list(
            json.loads(SEED_DESTRUCTION.read_text(encoding="utf-8"))["maps"][0]["items"]
        )
        snapshot_eligible = eligible_keys(snapshot_document, ORDER_ITEM_ID)
        snapshot_first = snapshot_eligible[0] if snapshot_eligible else None
        if snapshot_order != sorted(snapshot_order):
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the recorded snapshot's item keys are NOT lexicographic, so the "
                "shared writer's sort_keys no longer explains the difference and "
                "the note below would name the wrong cause",
            )
        if snapshot_order == committed_order:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the recorded snapshot and the committed seed now agree on item-key "
                "order, so this capture's recorded order IS the snapshot order and "
                "the note below is wrong",
            )
        if snapshot_first == ORDER_FIRST_RECORDED:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the snapshot order's first eligible row is %r, the same answer the "
                "recorded order gives: the recorded order no longer discriminates "
                "from the snapshot's sorted order"
                % snapshot_first,
            )
        order_of_record = {
            "writer_sorts_keys": True,
            "writer": "capture_legacy_fixtures.py:457 write_json -> json.dump(..., sort_keys=True)",
            "order_of_record": (
                "the COMMITTED VILLAGE DOCUMENT (villages/AcidCaos.json), whose "
                "`items` insertion order is what the oracle's in-memory save "
                "carried. before.json/after.json are NOT the order of record."
            ),
            "snapshot_order_differs_from_committed_order": snapshot_order != committed_order,
            "snapshot_order_is_lexicographic": snapshot_order == sorted(snapshot_order),
            "committed_order_is_lexicographic": committed_order == sorted(committed_order),
            "committed_order_first_three_keys": committed_order[:3],
            "snapshot_order_first_three_keys": snapshot_order[:3],
            "committed_order_eligible_keys": ORDER_ELIGIBLE_KEYS_RECORDED,
            "snapshot_order_eligible_keys": snapshot_eligible,
            "first_eligible_committed_order": ORDER_ELIGIBLE_KEYS_RECORDED[0]
            if ORDER_ELIGIBLE_KEYS_RECORDED
            else None,
            "first_eligible_snapshot_order": snapshot_first,
            "row_the_oracle_actually_removed": one["removed_keys"],
            "consequence_for_a_replay": (
                "A replay suite must rebuild the disposable corpus from the "
                "COMMITTED village document, not from before.json. Resetting from "
                "before.json replays against the sorted order, which removes %s "
                "instead of %s, and the resulting document still compares equal "
                "leaf for leaf -- so the mis-ordering would be invisible to a "
                "document diff and would silently invalidate the order claim."
                % (snapshot_first, ORDER_FIRST_RECORDED)
            ),
            "diff_is_order_insensitive": (
                "The harness's json_diff walks keys rather than positions, so the "
                "sorted snapshot compares equal to the unsorted document. That is "
                "why this is measured here instead of being assumed harmless."
            ),
        }
        print(
            "capture: order of record measured -- the committed document's first "
            "eligible row is %s, the snapshot's is %s, and the oracle removed %s"
            % (
                order_of_record["first_eligible_committed_order"],
                snapshot_first,
                one["removed_keys"],
            )
        )

        # --- containment, before publishing anything -----------------------
        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        post_fixtures = protected_fixture_snapshot()
        post_seed_sha = {
            "destruction": sha256_file(SEED_DESTRUCTION),
            "ledger": sha256_file(SEED_LEDGER),
        }

        if pre_combined != post_combined:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree containment changed:\n  before %s\n  after  %s"
                % (pre_combined, post_combined),
            )
        if pre_seed_sha != post_seed_sha:
            raise CaptureError(
                EXIT_CONTAINMENT, "a committed village seed changed during the run"
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
                "a working-tree saves/ directory exists; the run wrote outside its "
                "disposable",
            )

        # --- the manifest ---------------------------------------------------
        divergences = [item for item in summaries if not item["parity_with_delivered_endpoint"]]
        manifest = {
            "schema": SCHEMA,
            "captured_at_utc": iso_now(),
            "purpose": (
                "Executed-legacy evidence for the combat-action surface: "
                "end_attack (command.py:808-885), kill (169-181) and kill_iid "
                "(183-187). It records what the ORACLE does, including the two "
                "behaviours this capability deliberately does NOT reproduce: a "
                "client-dictated destruction count, and a partially applied save on "
                "an error response."
            ),
            "invocation": "python -B apps/compat-api/capture_combat_fixture.py",
            "interpreter": "CPython %d.%d (pinned)" % sys.version_info[:2],
            "server": {
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "process": "python -B server.py inside each disposable",
                "starts": len(TRANSACTIONS),
                "one_per_transaction": True,
                "one_per_transaction_reason": (
                    "sessions.load_saves() caches the corpus in a module global at "
                    "import, so a running server never re-reads the seed file. "
                    "Restoring the seed between probes on one server leaves the "
                    "in-memory corpus already mutated and silently produces a "
                    "different result."
                ),
                "debug": False,
                "debug_note": (
                    "server.py runs app.run(..., debug=False), so a failing request "
                    "answers the framework's plain error page with no traceback and "
                    "no absolute path. The capture asserts the body does not leak "
                    "the disposable path before committing it."
                ),
                "env_extra": {"PYTHONUNBUFFERED": "1"},
                "env_extra_note": (
                    "Set for THIS capture's child processes only, via a defaulted "
                    "parameter on start_server. child_environment() is untouched, so "
                    "no existing capture's log changes. The printed lines are "
                    "evidence -- the destruction count the oracle computed is "
                    "visible nowhere else -- and block buffering would lose them "
                    "when the harness reaps the child."
                ),
            },
            "seeds": {
                "why_two": (
                    "The destruction seed's ledger is EMPTY, so the key-CREATION "
                    "branch and the first-eligible-row selection are both observable "
                    "from nothing. The ledger seed's ledger holds 28 keys, so the "
                    "INCREMENT branch (4 -> 5) is observable instead. Neither "
                    "document exercises both, so neither is optional."
                ),
                "destruction": {
                    "path": str(SEED_DESTRUCTION.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "sha256": pre_seed_sha["destruction"],
                    "pid_read_from_document": SEED_DESTRUCTION_PID,
                    "choice_status": "derived-provisional",
                    "choice_reason": (
                        "It is the only committed document whose deadHeroes ledger is "
                        "empty while carrying eligible unit rows, so both the "
                        "key-creation branch and the recorded-order selection are "
                        "observable from nothing. It also contains the only item "
                        "whose first RECORDED eligible row is not its numeric "
                        "minimum, which is what makes the order claim testable."
                    ),
                    "census": censuses["destruction"],
                },
                "ledger": {
                    "path": str(SEED_LEDGER.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "sha256": pre_seed_sha["ledger"],
                    "pid_read_from_document": SEED_LEDGER_PID,
                    "choice_status": "derived-provisional",
                    "choice_reason": (
                        "It carries a 28-key ledger, so the increment branch is "
                        "observable as a count that moves while the KEY COUNT does "
                        "not -- a pair the key-creation branch cannot produce. It "
                        "also holds an item with eligible rows and NO ledger entry, "
                        "so both ledger arms run from one document."
                    ),
                    "census": censuses["ledger"],
                },
                "pid_note": (
                    "Read from playerInfo.pid in the document, never derived from "
                    "the filename stem: for three of the eight committed village "
                    "saves the two disagree, and for initial.json the pid is null, "
                    "which build_disposable refuses loudly rather than writing a "
                    "'None.save.json'."
                ),
            },
            "batch_shape": {
                "commands": [END_ATTACK_COMMAND, KILL_COMMAND, KILL_IID_COMMAND],
                "resource_vector": list(NEUTRAL_VECTOR),
                "vector_status": "neutral by construction, every transaction",
                "ts": FIXTURE_TS,
                "ts_note": (
                    "Pinned to a constant, as on the stored-placement and "
                    "unit-experience captures. The dispatcher parses it and never "
                    "reads it."
                ),
                "arguments": (
                    "CRAFTED AND CLIENT-SUPPLIED. end_attack's args[0] is the client "
                    "blob, read with json.loads and no validation of any kind; "
                    "args[1] is bound to the local `unknown` and never read. kill "
                    "and kill_iid take [subject, reason], and each branch uses its "
                    "reason only inside a print."
                ),
            },
            "recorded_steps": list(RECORDED_STEPS) + ["login_post"],
            "login_step": (
                "Performed once per server (%d times) and recorded once, from the "
                "first transaction. Its neutrality is asserted for EVERY "
                "transaction, so the elision loses no evidence." % len(TRANSACTIONS)
            ),
            "transactions": summaries,
            "established": [
                "The destruction count is max(0, unit[2] - unit[3]) on two numbers "
                "the CLIENT supplies (command.py:868), labelled only 'A' and 'B' in "
                "the committed source, with nothing establishing what they mean.",
                "That count is applied PER POPPED ROW: one request carrying one "
                "tuple with A=3, B=1 incremented the ledger twice and removed two "
                "rows.",
                "The oracle's safety against over-deletion is EXHAUSTION OF "
                "MATCHES, not a check: engine.py:218-227 loops `while qty > 0` and "
                "returns the moment one pass finds no match.",
                "A row is selected by item id (slot 0) plus a TRUTHY team (slot 7) "
                "-- engine.py:221 -- and popped in the save's own RECORDED map-key "
                "order, which is not a sort: item 1020's first recorded eligible "
                "row is 2425 while its numeric minimum is 897, and the oracle "
                "removed 2425.",
                "The ledger increment is behind EXACTLY TWO committed gates: player "
                "team 1 (engine.py:151) and a committed resurrectable flag greater "
                "than zero (engine.py:159,162). An absent flag is a refusal, never a "
                "zero.",
                "Both ledger arms are reachable and distinct: a count that moves "
                "while the key count does not (4 -> 5, 28 keys), and a key created "
                "at 1 (28 -> 29 keys).",
                "kill deletes a row BY MAP KEY and the branch contains no reference "
                "to privateState['deadHeroes'] and no call to push_dead_unit at all.",
                "kill_iid contains NO WRITE STATEMENT AT ALL -- its entire body is "
                "one print -- so nothing can move and no request can change that.",
                "The branch's two unguarded absent-value dereferences sit on "
                "OPPOSITE SIDES of its write loop: an omitted attacker_units raises "
                "at command.py:866 before the loop body runs, an omitted victim "
                "raises at command.py:874 after map_lose_item already ran -- and the "
                "server answers HTTP 500 in both cases.",
                "The PERSISTED state is byte-identical in both cases anyway, and a "
                "two-command batch whose first command is valid shows why: "
                "command.py dispatches the whole batch before calling save_session "
                "(command.py:30,32), so an exception discards EVERY mutation the "
                "batch made. The failure mode is a DISCARDED save rather than a "
                "partially applied one, and the persistence boundary is the BATCH.",
                "A third guard, found by measurement: an EMPTY blob short-circuits "
                "at command.py:818's `if not response:` and answers SUCCESS with no "
                "change, so the key that raises against a non-empty blob is "
                "answered successfully against an empty one.",
                "Under a NEUTRAL vector, EVERY stored resource is byte-identical in "
                "all thirteen transactions, and the only leaves that ever move belong "
                "to a destroyed row or to the ledger.",
            ],
            "divergences": {
                "count": len(divergences),
                "recorded_not_narrowed": True,
                "central": divergence,
                "persistence_boundary": bracket,
                "transactions": [
                    {
                        "name": item["name"],
                        "oracle_rows_removed": item["rows_removed"],
                        "oracle_ledger_after": item["ledger_after"],
                        "modern_derives_rows_removed": len(
                            item["modern_derives_removed_keys"]
                        ),
                        "modern_derives_ledger": item["modern_derives_ledger"],
                        "divergence": item.get("divergence"),
                        "delivered_endpoint_refusal": item.get(
                            "delivered_endpoint_refusal"
                        ),
                    }
                    for item in divergences
                ],
                "why_not_narrowed": (
                    "Narrowing either would require a combat rule the preserved "
                    "source does not contain. The client-computed count has no "
                    "committed meaning, and the ordering difference would require "
                    "inventing a pre-write validation the legacy branch does not "
                    "perform."
                ),
            },
            "recorded_order_discriminator": order,
            "order_of_record": order_of_record,
            "derived_provisional": [
                "That the recorded map-key order -- rather than a sort -- is the "
                "selection order. It rests on `for index in map_items` walking the "
                "save's own insertion order plus the committed corpus's "
                "out-of-order insertions, and the oracle's removal of 2425 rather "
                "than 897 measures it end to end.",
                "The choice of villages/AcidCaos.json and villages/Neutral.json as "
                "the two disposable seeds, recorded so a rerun reproduces the "
                "committed bytes.",
                "That the `reason` argument of kill and kill_iid has no stored "
                "effect: each branch uses it only inside an f-string.",
            ],
            "not_claimed": [
                "Any combat rule. Damage, health, defence, hit chance, attack "
                "outcome, life and interval arithmetic are NOT resolved or claimed: "
                "attack, defense, life, attack_interval, attack_range, best_against, "
                "best_against_mult and velocity each measure zero legacy consumers, "
                "so the committed numbers are content and never rules.",
                "Any mission dispatch, resolution, completion, or reward. The mission "
                "vocabulary stays owned by godot-mission-vocabulary.",
                "Any honour, reward, or resource movement. honour, resources, "
                "resources_victim and townhall_gold are read and discarded, and every "
                "transaction ran under a neutral vector and moved nothing.",
                "Any occupancy, bounds, type, or terrain validation. map_lose_item "
                "tests only the item id and the team's truthiness, and this contract "
                "reproduces that absence rather than filling it.",
                "The team asymmetry between map_lose_item's truthy-team acceptance "
                "and push_dead_unit's team-one requirement as something exercised: "
                "it is recorded, not exercised and not refused, because every one of "
                "the 441 committed unit rows is on team one.",
                "That the modern endpoint reproduces the oracle's destruction "
                "COUNT. It does not, by design, and the manifest records the "
                "difference rather than reporting parity by omission.",
                "Anything about what the real Flash client sent. The client was never "
                "executed: every payload here is crafted.",
                "Any partially applied save. The oracle never persists one: a raise "
                "anywhere in a batch skips save_session, so the recorded state is "
                "byte-identical on every failing transaction here.",
            ],
            "time_dependent_fields": {
                "request_captured_at_utc": (
                    "Recorded per step and necessarily volatile; it is the only field "
                    "in this fixture that changes between reruns, which is why "
                    "'byte-identical rerun' is claimed for the transaction records, "
                    "states and manifest body, not for these two fields."
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
                    "Each disposable is removed by the harness's own finally block; "
                    "the fixture is staged OUTSIDE the working tree and published "
                    "only after every check passed, so a failed run writes nothing "
                    "into the repository."
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