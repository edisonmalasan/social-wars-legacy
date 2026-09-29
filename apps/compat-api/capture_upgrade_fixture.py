#!/usr/bin/env python3
"""Capture the executed-legacy upgrade fixture: one real two-command batch.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, and store captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, and store fixtures.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root (root ``*.py``,
   ``config/``, ``mods/``, ``villages/``, ``templates/`` and ``saves/``
   seeded from ``tests/saves/fresh-player.json``).
4. Starts the REAL legacy server (``python -B server.py`` in the
   disposable copy) and waits for loopback readiness.
5. Executes two legacy requests, recording full canonical before/after
   save JSON plus the response for each step:

   * ``POST /``                       — login form (session cookie, as a
     logged-in Flash client would send; 302, save unchanged)
   * ``POST .../command.php``         — the crafted ``<64-hex>;<json>``
     ``data`` envelope carrying exactly the **two** derived commands —
     ``[0,"sell",[index,"UPGR"],zeros]`` then
     ``[0,"buy",[index,target,x,y,player,orientation,0,""],zeros]`` — as
     produced by :mod:`upgrade_envelope`

   The fixture upgrade is the Wall I (item id 23, 1x1) at map slot ``12``,
   anchored at ``(45,49)`` in the fresh-player corpus, upgraded to the Wall II
   (item id 24) its config's ``upgrades_to`` names.  Slot ``12`` is a wall
   segment, distinct from the move fixture's slot 11 (Turret I), the sell
   fixture's slot 20 (Turret I), and the store fixture's slot 2 (Tree), so
   every delivered fixture stays independently readable.
6. Verifies the transaction structurally before publishing: the login step
   left the save byte-identical, the upgrade step mutated it, the row at key
   ``"12"`` **still exists** afterwards holding the target item id ``24`` at
   the **same cell** ``(45,49)``, its new ``timestamp`` is a fresh wall-clock
   stamp, its ``attr`` is the click-to-build seed ``{"nc": 0}``, the placement
   count stays ``40`` (the key is reused, nothing is added or removed),
   ``privateState.boughtUnits`` becomes ``[24]``, every other row, the storage
   mapping, the rest of ``privateState`` (including ``deadHeroes`` — the
   reason is ``"UPGR"``, never ``"KILL"``), ``playerInfo``, every other map
   field, and all seven resources are unchanged (the derived vectors are
   neutral).  The recorded request itself is pinned: exactly two commands, in
   the forced order, with the committed reason and both neutral vectors.
7. Stops the server, re-checks the working-tree containment snapshot and the
   committed boot/placement/purchase/move/sell/store fixture digests,
   discards the disposable copy, and writes the fixtures under ``--out``
   (default: ``tests/fixtures/godot-building-upgrade/``).

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

Containment (same contract as the boot, placement, purchase, move, sell, and
store captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The committed boot,
  placement, purchase, move, sell, and store fixtures are digest-pinned for
  the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the boot, placement, purchase, move, sell, and store
capture harnesses):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed, returned an unexpected status, or the
      executed transaction did not match the derived envelope
6     Containment violation (working-tree bytes changed, a committed fixture
      directory changed, or the disposable corpus saves changed during
      server startup / login)
7     Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_upgrade_fixture.py

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
import upgrade_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-upgrade"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a
# corpus and initialize live legacy state).  The resolved target tier is read
# from it here and pinned against FIXTURE_TARGET_ITEM_ID.
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# ``upgrades_to`` sentinels that mean "no path", copied from the normalized
# content package's own rule (packages/game-content/tools/build_items.py:
# RELATION_NONE at line 66, applied by validate_relations at 546-557).
RELATION_NONE = (-1, 0)

# The fixture upgrade intent (verified against the committed config and fresh
# save: slot "12" holds [23, 45, 49, 0, 0, [], {}, 1] and the config's
# upgrades_to for item 23 is "24").
FIXTURE_ITEM_INDEX = 12
FIXTURE_ITEM_ID = 23  # Wall I: 1x1 building, the row this fixture replaces
FIXTURE_ITEM_NAME = "Wall I"
FIXTURE_TARGET_ITEM_ID = 24  # Wall II: the item upgrades_to names
FIXTURE_TARGET_ITEM_NAME = "Wall II"
FIXTURE_X = 45
FIXTURE_Y = 49
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 40  # the key is reused: nothing is added
FIXTURE_EXPECTED_BOUGHT_UNITS_BEFORE: List[int] = []
FIXTURE_EXPECTED_BOUGHT_UNITS_AFTER: List[int] = [24]
# The click-to-build seed engine.map_add_item writes for a player-owned item
# whose config has clicks_to_build > 0 (engine.py:25-29).  Wall II's is "1",
# so the upgraded row carries attr {"nc": 0}: the building is present and
# unfinished, and consuming the counter belongs to the construction-timers
# deliver line (design D5 / non-goals).
FIXTURE_EXPECTED_ATTR_AFTER: Dict[str, int] = {"nc": 0}
TARGET_RULE = (
    "the Wall I (item id 23) at map slot 12 anchored at (45,49) in the "
    "committed fresh save, upgraded to the Wall II (item id 24) its config "
    "upgrades_to names — a wall segment, so this fixture's target differs from "
    "the move fixture's slot 11, the sell fixture's slot 20, and the store "
    "fixture's slot 2 and every delivered fixture stays independently "
    "readable; the buy half reuses the row's own key and cell, so an upgrade "
    "has no target cell of its own"
)

# Committed fixtures that must be byte-identical across this run.
PROTECTED_FIXTURES = (
    ("tests/fixtures/godot-compatibility-boot", "godot-compatibility-boot"),
    ("tests/fixtures/godot-building-placement", "godot-building-placement"),
    ("tests/fixtures/godot-item-purchase", "godot-item-purchase"),
    ("tests/fixtures/godot-building-move", "godot-building-move"),
    ("tests/fixtures/godot-building-sell", "godot-building-sell"),
    ("tests/fixtures/godot-building-store", "godot-building-store"),
)

# The reverse-order negative oracle, recorded from the executed legacy probe
# documented in the change design (Context, probe 2).  It is *not* re-executed
# by this tool: it describes what the real server answers for the same two
# commands in the opposite order, which is why legacy's success status is not
# evidence of an upgrade and why the endpoint proves the post-state.
NEGATIVE_ORACLE: Dict[str, Any] = {
    "what": (
        "the same two derived commands sent in the reverse order — buy first, "
        "sell second — against the same fresh-player corpus"
    ),
    "envelope_commands": [
        [0, "buy", [12, 24, 45, 49, 1, 0, 0, ""], [0, 0, 0, 0, 0, 0, 0, 0]],
        [0, "sell", [12, "UPGR"], [0, 0, 0, 0, 0, 0, 0, 0]],
    ],
    "response_body": '{"result": "success"}',
    "http_status": 200,
    "placement_count_before": 40,
    "placement_count_after": 39,
    "key_12_afterwards": "absent — the building is destroyed, not upgraded",
    "bought_units_after": [24],
    "consequence": (
        "legacy answers 200 {\"result\":\"success\"} for a batch that DELETES "
        "the building, so the command order is forced (sell first) and a "
        "success status is not evidence of an upgrade; the Compatibility API "
        "v0 endpoint therefore proves the post-state with three facts — the key "
        "still exists, its item id equals the derived target tier, and its cell "
        "equals the pre-execution cell — and fails closed with internal_error "
        "otherwise"
    ),
    "evidence": (
        "executed-legacy probe recorded in the change design (Context, "
        "probe 2); re-derived offline against the unchanged legacy dispatcher "
        "by apps/compat-api/tests/test_upgrade_endpoint.py"
    ),
}

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_upgrade")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5}


# ------------------------------------------------------------ target tier ---
def config_upgrade_reference(item_id: int) -> Optional[int]:
    """The committed configuration's next tier for ``item_id``, or ``None``.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (see :data:`CONFIG_MAIN`), and resolved with exactly the rule
    :meth:`compat_legacy.LegacyBoot.item_upgrade_to` uses server-side: a
    missing reference, the ``-1`` / ``0`` sentinels, a non-integer value, and
    an id the item set does not resolve all mean **no path**.
    """
    try:
        document = json.loads(CONFIG_MAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    known: Dict[int, Dict[str, Any]] = {}
    for entry in document.get("items") or []:
        try:
            known[int(entry["id"])] = entry
        except (KeyError, TypeError, ValueError):
            continue
    item = known.get(item_id)
    if item is None:
        return None
    raw = item.get("upgrades_to")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        reference = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if reference in RELATION_NONE or reference not in known:
        return None
    return reference


# ------------------------------------------------------------ sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    """Redact secret-valued form fields before recording."""
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact the disposable server's session cookie from recorded headers.

    The live request always sends the real cookie (the login step must behave
    like a logged-in client); only the *record* is redacted — it is an
    ephemeral token value of a dead disposable server, it can never be
    replayed (upgrade parity works from the intent, not over HTTP), and
    redacting it keeps reruns byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact
    sent bytes; this keeps the record secret-free even if that placeholder
    ever changes.
    """
    envelope = upgrade_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return upgrade_envelope.data_field(envelope)


# ----------------------------------------------------------------- records --
def canonical_save(path: Path) -> Dict[str, Any]:
    """Full parsed save document from a corpus save file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "could not read corpus save %s: %s" % (path, error))
    if not isinstance(document, dict):
        raise CaptureError(EXIT_REQUEST, "corpus save is not a JSON object: %s" % path)
    return document


def save_bytes_sha(document: Dict[str, Any]) -> str:
    """SHA-256 of the canonical serialization used for fixture records."""
    return sha256_bytes(
        json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True).encode("utf-8")
    )


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


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The two commands, their order, and their argument values are the executed
    contract (design D1/D2); the Flash client is never executed, so the buy
    half's ``orientation`` / ``playerID`` / ``unknown`` / ``reason`` values and
    the neutral price vectors are **derived-provisional** (design D4).  They are
    pinned here against the committed config and fresh save instead, and any
    drift fails the run rather than silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(upgrade_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 2:
        raise CaptureError(
            EXIT_REQUEST,
            "an upgrade batch must carry exactly two commands, got %d" % len(commands),
        )

    sell_entry, buy_entry = commands
    if sell_entry[0] != 0 or buy_entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on both commands")
    if sell_entry[1] != upgrade_envelope.SELL_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the first command must be %r, got %r"
            % (upgrade_envelope.SELL_COMMAND, sell_entry[1]),
        )
    if buy_entry[1] != upgrade_envelope.BUY_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the second command must be %r, got %r"
            % (upgrade_envelope.BUY_COMMAND, buy_entry[1]),
        )

    expected_sell_args = [FIXTURE_ITEM_INDEX, upgrade_envelope.UPGRADE_REASON]
    if sell_entry[2] != expected_sell_args:
        raise CaptureError(
            EXIT_REQUEST,
            "sell args must be %r, got %r" % (expected_sell_args, sell_entry[2]),
        )
    if sell_entry[2][1] != upgrade_envelope.UPGRADE_REASON:
        raise CaptureError(
            EXIT_REQUEST,
            "the committed upgrade reason must be %r, got %r"
            % (upgrade_envelope.UPGRADE_REASON, sell_entry[2][1]),
        )
    expected_buy_args = [
        FIXTURE_ITEM_INDEX,
        FIXTURE_TARGET_ITEM_ID,
        FIXTURE_X,
        FIXTURE_Y,
        1,  # the replaced row's player team
        0,  # the replaced row's orientation
        upgrade_envelope.DEFAULT_UNKNOWN,
        upgrade_envelope.BUY_REASON,
    ]
    if buy_entry[2] != expected_buy_args:
        raise CaptureError(
            EXIT_REQUEST,
            "buy args must be %r, got %r" % (expected_buy_args, buy_entry[2]),
        )
    for label, entry in (("sell", sell_entry), ("buy", buy_entry)):
        if entry[3] != FIXTURE_EXPECTED_VECTOR:
            raise CaptureError(
                EXIT_REQUEST,
                "%s derived neutral resource vector drifted: %r (expected %r)"
                % (label, entry[3], FIXTURE_EXPECTED_VECTOR),
            )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived vectors
    under the legacy rules, in the order legacy applies them: ``command.sell``
    deletes exactly the addressed row with ``engine.map_delete_item``
    (``command.py:162``, ``engine.py:48-52``); ``command.buy`` records the
    bought unit with ``bought_unit_add`` (``command.py:52-53``) and writes a
    **fresh** row with ``engine.map_add_item`` (``command.py:55``,
    ``engine.py:8-31``) — a wall-clock ``timestamp``, ``store []``, and, for a
    player-owned item with ``clicks_to_build > 0``, ``attr {"nc": 0}``.  The
    replaced row's ``timestamp``, ``store``, and ``attr`` are **not** carried
    over, and that is reproduced rather than "fixed" (design D5).
    ``engine.apply_resources`` (``engine.py:251-271``) applies the neutral
    vectors with a per-slot ``max(..., 0)``, once per command.  The committed
    reason is not ``"KILL"``, so ``push_dead_unit`` never runs and the rest of
    ``privateState`` must stand.  Any mismatch means the capture would publish
    a fixture that contradicts its own derivation, so the run fails with
    exit 5.
    """
    try:
        sell_entry, buy_entry = envelope["commands"]
        key = str(buy_entry[2][0])
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    items_before = map_before["items"]
    items_after = map_after["items"]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if len(items_before) != FIXTURE_EXPECTED_PLACEMENTS_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "before-state placement count is %d (expected %d)"
            % (len(items_before), FIXTURE_EXPECTED_PLACEMENTS_BEFORE),
        )

    row_before = items_before.get(key)
    if not isinstance(row_before, list):
        raise CaptureError(
            EXIT_REQUEST, "no placement row at index %s to upgrade" % key
        )
    if len(row_before) != 8:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is not an eight-field entry" % key,
        )
    if int(row_before[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "replaced row is item %r, not the fixture item %d"
            % (row_before[0], FIXTURE_ITEM_ID),
        )
    if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "replaced row is anchored at %r, not the documented %r"
            % ([row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
        )

    # The pair replaces the row in place: the key must survive, hold the
    # derived target tier, and sit at the very same cell.
    if key not in items_after:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is absent after the upgrade; the reverse "
            "command order produces exactly this outcome and destroys the "
            "building" % key,
        )
    row_after = items_after[key]
    if not isinstance(row_after, list) or len(row_after) != 8:
        raise CaptureError(
            EXIT_REQUEST, "the upgraded row is not an eight-field entry"
        )
    if int(row_after[0]) != FIXTURE_TARGET_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "upgraded row holds item %r, not the derived target tier %d"
            % (row_after[0], FIXTURE_TARGET_ITEM_ID),
        )
    if [row_after[1], row_after[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "upgraded row is anchored at %r, not the pre-execution cell %r"
            % ([row_after[1], row_after[2]], [FIXTURE_X, FIXTURE_Y]),
        )
    # The fresh row's wall-clock timestamp: the one documented time-dependent
    # value in the recorded state.
    stamp = row_after[3]
    if not isinstance(stamp, int) or isinstance(stamp, bool) or stamp <= 0:
        raise CaptureError(
            EXIT_REQUEST, "the upgraded row's timestamp is not a wall-clock stamp: %r" % (stamp,)
        )
    if stamp < row_before[3]:
        raise CaptureError(
            EXIT_REQUEST,
            "the upgraded row's timestamp %r predates the replaced row's %r; "
            "map_add_item stamps the current time" % (stamp, row_before[3]),
        )
    # The fresh row's remaining fields, and the fact that the replaced row's
    # store / attr are NOT carried over.
    if row_after[4] != row_before[4]:
        raise CaptureError(
            EXIT_REQUEST,
            "orientation changed %r -> %r; the fixture row's orientation is 0"
            % (row_before[4], row_after[4]),
        )
    if row_after[5] != []:
        raise CaptureError(
            EXIT_REQUEST, "the upgraded row carries a stored-unit payload: %r" % (row_after[5],)
        )
    if row_after[6] != FIXTURE_EXPECTED_ATTR_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "the upgraded row's attr is %r, not the click-to-build seed %r "
            "(engine.py:25-29)" % (row_after[6], FIXTURE_EXPECTED_ATTR_AFTER),
        )
    if row_after[7] != row_before[7]:
        raise CaptureError(
            EXIT_REQUEST,
            "the player team changed %r -> %r; the buy half reuses the row's own"
            % (row_before[7], row_after[7]),
        )

    # The key is reused, so no placement is added or removed.
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].item keys changed; the pair reuses one key and adds none",
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS_AFTER),
        )

    # Every other row is byte-identical: the pair writes exactly one entry.
    for other in items_before:
        if other == key:
            continue
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; an upgrade rewrites only the row it "
                "replaces" % other,
            )

    # Legacy apply_resources: max(current + delta, 0) per slot, applied once
    # per command.  Both derived vectors are neutral, so no resource may move.
    total = [
        sum(entry[3][slot] for entry in envelope["commands"])
        for slot in range(upgrade_envelope.RESOURCE_VECTOR_SLOTS)
    ]
    for key_name, index in sorted(RESOURCE_VECTOR_SLOTS.items()):
        current = map_before[key_name]
        expected = max(current + total[index], 0)
        observed = map_after[key_name]
        if observed != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (key_name, current, observed, expected),
            )
    expected_cash = max(before["playerInfo"]["cash"] + total[6], 0)
    if after["playerInfo"]["cash"] != expected_cash:
        raise CaptureError(
            EXIT_REQUEST,
            "cash changed unexpectedly: %r -> %r (expected %r)"
            % (before["playerInfo"]["cash"], after["playerInfo"]["cash"], expected_cash),
        )
    if after["privateState"]["mana"] != max(before["privateState"]["mana"] + total[7], 0):
        raise CaptureError(
            EXIT_REQUEST,
            "mana changed unexpectedly: %r -> %r"
            % (before["privateState"]["mana"], after["privateState"]["mana"]),
        )

    # An upgrade stores nothing.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; an upgrade stores never")
    # The purchase half records the new tier in the bought-units list
    # (command.py:52-53, playerID == 1); nothing else in privateState moves,
    # and in particular deadHeroes stands because the reason is "UPGR", never
    # "KILL" (push_dead_unit is unreachable).  Legacy's bought_unit_add
    # (engine.py:86-89) appends only when the item is not already listed, so
    # the expected list is that rule applied to the before-state -- on the
    # committed corpus, which starts empty, that is a plain [24].
    private_before = before["privateState"]
    private_after = after["privateState"]
    bought_before = private_before["boughtUnits"]
    expected_bought = (
        list(bought_before)
        if FIXTURE_TARGET_ITEM_ID in bought_before
        else list(bought_before) + [FIXTURE_TARGET_ITEM_ID]
    )
    if private_after["boughtUnits"] != expected_bought:
        raise CaptureError(
            EXIT_REQUEST,
            "boughtUnits is %r, expected %r (the buy half records the target "
            "tier with bought_unit_add)"
            % (private_after["boughtUnits"], expected_bought),
        )
    if private_after["boughtUnits"] != FIXTURE_EXPECTED_BOUGHT_UNITS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "boughtUnits is %r, not the documented %r"
            % (private_after["boughtUnits"], FIXTURE_EXPECTED_BOUGHT_UNITS_AFTER),
        )
    for name in sorted(set(private_before) | set(private_after)):
        if name == "boughtUnits":
            continue
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; only boughtUnits may move, and the "
                "committed reason must not reach push_dead_unit" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(EXIT_REQUEST, "playerInfo changed; neither command writes any of it")
    for field in sorted(set(map_before) | set(map_after)):
        if field in ("items", "store", "xp", "gold", "wood", "oil", "steel"):
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the pair writes only the replaced row" % field,
            )


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    return {
        label: dir_group_record(REPO_ROOT / relative, relative)
        for relative, label in PROTECTED_FIXTURES
    }


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy upgrade fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-upgrade-capture-staging-"))
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
                "Login form (USERID + GAMEVERSION) exactly as the boot, "
                "placement, purchase, move, sell, and store captures send it; "
                "recorded for session fidelity — command.php performs no "
                "session validation. user_key would be redacted if present.",
            )
        )

        # --- derive the upgrade envelope from the before-state -------------
        before_upgrade = canonical_save(save_path)
        row_before = before_upgrade["maps"][0]["items"].get(str(FIXTURE_ITEM_INDEX))
        if not isinstance(row_before, list) or len(row_before) != 8:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save has no eight-field row at index %d"
                % FIXTURE_ITEM_INDEX,
            )
        if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save anchors index %d at %r, not the documented %r"
                % (
                    FIXTURE_ITEM_INDEX,
                    [row_before[1], row_before[2]],
                    [FIXTURE_X, FIXTURE_Y],
                ),
            )
        if int(row_before[0]) != FIXTURE_ITEM_ID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's index %d holds item %r, not %d"
                % (FIXTURE_ITEM_INDEX, row_before[0], FIXTURE_ITEM_ID),
            )
        if before_upgrade["maps"][0]["store"] != {}:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's storage is not empty; the fixture assumes %r"
                % (before_upgrade["maps"][0]["store"],),
            )
        # The target tier is resolved from the committed configuration, never
        # hardcoded into the request; the pinned constant is only the
        # cross-check that fails the run if the committed config drifts.
        resolved_target = config_upgrade_reference(FIXTURE_ITEM_ID)
        if resolved_target != FIXTURE_TARGET_ITEM_ID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's next tier to %r, "
                "not the pinned %d"
                % (FIXTURE_ITEM_ID, resolved_target, FIXTURE_TARGET_ITEM_ID),
            )
        envelope = upgrade_envelope.build_envelope(
            item_index=FIXTURE_ITEM_INDEX,
            target_item_id=FIXTURE_TARGET_ITEM_ID,
            x=row_before[1],
            y=row_before[2],
            player=row_before[7],
            orientation=row_before[4],
        )
        verify_envelope(envelope)
        data = upgrade_envelope.data_field(envelope)
        upgrade_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the two-command upgrade batch -------------------------
        upgrade_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(upgrade_form),
            cookie=cookie,
            timeout=30.0,
        )
        if upgrade_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_upgrade: expected HTTP 200, got %r" % upgrade_result["status"],
            )
        after_upgrade = canonical_save(save_path)
        if save_bytes_sha(before_upgrade) == save_bytes_sha(after_upgrade):
            raise CaptureError(
                EXIT_REQUEST,
                "command_upgrade did not persist any save change; refusing to "
                "publish a non-transaction fixture",
            )
        body = upgrade_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_upgrade",
                upgrade_result,
                body,
                before_upgrade,
                after_upgrade,
                upgrade_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly two "
                "commands in the forced order: a sell whose two arguments are "
                "the legacy map index and the committed upgrade reason "
                "(constants.py:970 SELL_REASON_UPGRADE, derived server-side and "
                "never client-chosen, so no client can claim the combat KILL "
                "reason), then a buy whose eight arguments are the same key, the "
                "target tier the committed configuration's upgrades_to names, "
                "the row's own cell and orientation, the row's own player team, "
                "and the two documented placeholders legacy discards; both "
                "commands carry the neutral all-zero resources_changed vector "
                "(no upgrade cost is claimed); user_key is redacted in this "
                "record; accessToken is the crafted empty placeholder, never a "
                "token value.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_upgrade, after_upgrade, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_upgrade response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
            )
        row_after = after_upgrade["maps"][0]["items"][str(FIXTURE_ITEM_INDEX)]

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

        sell_entry, buy_entry = envelope["commands"]
        manifest = {
            "schema": "godot-building-upgrade/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "two-command upgrade transaction; the executed-legacy parity "
                "oracle for the Compatibility API v0 upgrade endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_upgrade_fixture.py"
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
            "intent": {
                "item_index": FIXTURE_ITEM_INDEX,
                "item_id": FIXTURE_ITEM_ID,
                "item_name": FIXTURE_ITEM_NAME,
                "target_item_id": FIXTURE_TARGET_ITEM_ID,
                "target_item_name": FIXTURE_TARGET_ITEM_NAME,
                "from_cell": [FIXTURE_X, FIXTURE_Y],
                "to_cell": [FIXTURE_X, FIXTURE_Y],
                "target_rule": TARGET_RULE,
                "bounds_rule": "not applicable: an upgrade has no target cell of "
                "its own — the buy half reuses the replaced row's own cell, so "
                "the only grid input is that recorded anchor",
                "derived": {
                    "command_order": [upgrade_envelope.SELL_COMMAND, upgrade_envelope.BUY_COMMAND],
                    "sell": {
                        "command": sell_entry[1],
                        "args": sell_entry[2],
                        "reason": sell_entry[2][1],
                        "reason_status": "established from committed legacy source: "
                        "constants.py:970 SELL_REASON_UPGRADE = \"UPGR\", the "
                        "committed value; derived server-side, so no client can "
                        'claim another reason and in particular cannot claim "KILL" '
                        "and reach push_dead_unit",
                        "resources_changed": sell_entry[3],
                    },
                    "buy": {
                        "command": buy_entry[1],
                        "args": buy_entry[2],
                        "key_and_cell_status": "established from committed legacy "
                        "source: buy takes its map key and cell from the client "
                        "(command.py:42-58 -> engine.map_add_item(map, "
                        "item_index, item_id, x, y, ...)), which is how the pair "
                        "reuses the very same key and cell",
                        "orientation_player_unknown_reason_status": "derived, "
                        "never observed from the Flash client: the buy half's "
                        "orientation and playerID come from the replaced row, and "
                        "unknown=0 / reason=\"\" are the documented placeholders "
                        "legacy binds and discards",
                        "resources_changed": buy_entry[3],
                    },
                    "target_tier_status": "established from committed legacy "
                    "source: the item's own upgrades_to (config/main.json), "
                    "resolved with the documented -1/0-and-unresolvable-means-none "
                    "rule (packages/game-content/tools/build_items.py:547-550); "
                    "never client-supplied",
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "status": "established: the composed pair, its order, the "
                    "UPGR reason, the client-supplied key and cell of buy, the "
                    "fresh-row semantics of engine.map_add_item, and the "
                    "bought_unit_add record — all from committed legacy source, "
                    "and the resulting state from this executed transaction. "
                    "derived and never observed from the Flash client: that the "
                    "Flash client sends exactly this pair, the buy half's "
                    "orientation / player / unknown / reason values, and the "
                    "price vector. The committed configuration records no "
                    "upgrade price anywhere, so both derived vectors are neutral "
                    "and NO upgrade cost is claimed",
                },
            },
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "replaced_row_before": list(row_before),
                "upgraded_row_after": list(row_after),
                "entry_field_order": [
                    "item", "x", "y", "timestamp", "orientation", "store", "attr", "player",
                ],
                "placement_count_before": len(before_upgrade["maps"][0]["items"]),
                "placement_count_after": len(after_upgrade["maps"][0]["items"]),
                "key_reused": str(FIXTURE_ITEM_INDEX),
                "store_after": after_upgrade["maps"][0]["store"],
                "bought_units_before": before_upgrade["privateState"]["boughtUnits"],
                "bought_units_after": after_upgrade["privateState"]["boughtUnits"],
                "dead_heroes_after": after_upgrade["privateState"]["deadHeroes"],
                "resources_after": {
                    "xp": after_upgrade["maps"][0]["xp"],
                    "gold": after_upgrade["maps"][0]["gold"],
                    "wood": after_upgrade["maps"][0]["wood"],
                    "oil": after_upgrade["maps"][0]["oil"],
                    "steel": after_upgrade["maps"][0]["steel"],
                    "cash": after_upgrade["playerInfo"]["cash"],
                    "mana": after_upgrade["privateState"]["mana"],
                },
                "other_rows_unchanged": True,
                "private_state_unchanged_beside_bought_units": True,
                "player_info_unchanged": True,
                "upgrade_cost_claimed": False,
                "premium_upgrade_costs_used": False,
                "fresh_row_semantics": (
                    "engine.map_add_item writes a fresh eight-field row: a new "
                    "wall-clock timestamp, store [], and attr {\"nc\": 0} because "
                    "the target's config has clicks_to_build > 0 (engine.py:25-29) "
                    "— the construction counter the construction-timers deliver "
                    "line will consume. The replaced row's timestamp, store, and "
                    "attr are NOT carried over, and this change reproduces that "
                    "exactly rather than fixing it (design D5)"
                ),
                "state_writes": [
                    "command.sell deletes exactly the addressed row with "
                    "engine.map_delete_item (command.py:162; engine.py:48-52) "
                    "and writes nothing else",
                    "the committed reason is 'UPGR', never 'KILL', so "
                    "push_dead_unit never runs and the rest of privateState "
                    "(deadHeroes included) stands",
                    "command.buy with playerID == 1 records the target tier with "
                    "bought_unit_add (command.py:52-53; engine.py:86-89 appends only "
                    "when the item is not already listed), so boughtUnits gains the "
                    "new tier",
                    "command.buy writes a fresh row at the same key and cell "
                    "with engine.map_add_item (command.py:55; engine.py:8-31)",
                    "engine.apply_resources applies the derived neutral delta on "
                    "both commands with max(..., 0), so no resource changes",
                ],
            },
            "negative_oracle": NEGATIVE_ORACLE,
            "time_dependent_fields": {
                "rule": (
                    "every other leaf of every committed file is byte-identical "
                    "across reruns; the leaves below are the whole documented "
                    "time-dependent surface and were verified by a leaf-level "
                    "diff of two consecutive runs (11 differing leaves in "
                    "total, every one of them named here)"
                ),
                "leaves": [
                    "/captured_at_utc in every request.json and response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in both response.meta.json files",
                    "the envelope ts inside command_upgrade/request.json's "
                    "/form/data (and therefore that field's sha256 digest), "
                    "because ts is the current time",
                    "the upgraded row's wall-clock timestamp: "
                    "/maps/0/items/%d/3 in command_upgrade/after.json, and the "
                    "two manifest leaves derived from it — "
                    "/transaction/upgraded_row_after/3 and "
                    "/transaction/steps/1/save_after_sha256" % FIXTURE_ITEM_INDEX,
                ],
                "documented_normalization": (
                    "upgrade parity compares the new row's timestamp as a "
                    "positive integer greater than the replaced row's, never by "
                    "value: legacy stamps it with timestamp_now() and no clock "
                    "field is otherwise written"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, and store fixtures are "
                    "digest-pinned for the same reason."
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
                "capture:   %-18s %s %s -> %d (%d bytes, save unchanged: %s)"
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
            "capture: derived commands %s%s then %s%s, both resources %s"
            % (
                sell_entry[1],
                sell_entry[2],
                buy_entry[1],
                buy_entry[2],
                FIXTURE_EXPECTED_VECTOR,
            )
        )
        print(
            "capture: slot %d (%s) cell %r replaced in place by %d (%s), "
            "placements %d -> %d, store %r, boughtUnits %r -> %r, deadHeroes %r"
            % (
                FIXTURE_ITEM_INDEX,
                FIXTURE_ITEM_NAME,
                [row_before[1], row_before[2]],
                FIXTURE_TARGET_ITEM_ID,
                FIXTURE_TARGET_ITEM_NAME,
                len(before_upgrade["maps"][0]["items"]),
                len(after_upgrade["maps"][0]["items"]),
                after_upgrade["maps"][0]["store"],
                before_upgrade["privateState"]["boughtUnits"],
                after_upgrade["privateState"]["boughtUnits"],
                after_upgrade["privateState"]["deadHeroes"],
            )
        )
        print(
            "capture: upgraded row %r (timestamp is the documented "
            "time-dependent field)" % (list(row_after),)
        )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except upgrade_envelope.EnvelopeError as error:
        print(
            "capture: FAILED: could not derive the envelope: [%s] %s"
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
