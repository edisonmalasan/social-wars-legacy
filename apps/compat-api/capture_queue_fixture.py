#!/usr/bin/env python3
"""Capture the executed-legacy production-queue fixture: one push, one pop.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, collect, expand, and level captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, upgrade, construction, collect, and expand fixtures.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root (root ``*.py``,
   ``config/``, ``mods/``, ``villages/``, ``templates/`` and ``saves/``
   seeded from ``tests/saves/fresh-player.json``).
4. Starts the REAL legacy server (``python -B server.py`` in the
   disposable copy) and waits for loopback readiness.
5. Executes three recorded legacy requests, recording full canonical
   before/after save JSON plus the response for each step:

   * ``POST /``                       — login form (session cookie, as a
     logged-in Flash client would send; 302, save unchanged)
   * ``POST .../command.php``         — the crafted ``<64-hex>;<json>``
     ``data`` envelope carrying exactly **one** command —
     ``[0,"push_queue_unit",[1],[0,0,0,0,0,0,0,0]]`` on map key **1**
   * ``POST .../command.php``         — the same envelope carrying
     ``[0,"pop_queue_unit",[1],[0,0,0,0,0,0,0,0]]`` on the same key

6. Verifies each transaction structurally before publishing: the login step left
   the save byte-identical, the push set ``nu`` and ``ts`` on the addressed row's
   attribute bag and changed nothing else, the pop removed both together, the
   placement count and all 40 rows are byte-identical, ``store`` /
   ``privateState`` / ``playerInfo`` and every **other** map field are
   unchanged, and **every one of the seven stored resources is unchanged**
   because the derived vector is neutral.
7. Runs one **executed-legacy probe** against the same live server, after the
   recorded steps and on the same disposable copy, which is recorded in the
   manifest rather than as a step: ``push_queue_unit([1])`` carrying a
   client-sent ``[0, 500, 0, 0, 0, 0, 0, 0]`` vector.  It establishes the fact
   the endpoint's neutral vector and its second proof half exist for: the branch
   moves a balance when — and only when — a client sends one, so proving that
   *nothing* moved is a real check and not a tautology.
8. Stops the server, re-checks the working-tree containment snapshot and the
   ten committed fixture digests, discards the disposable copy, and writes the
   fixtures under ``--out`` (default: ``tests/fixtures/godot-unit-queues/``).

What this fixture does and does not show, stated up front
    The recorded pair targets the committed corpus's **real placed training
    producer**: ``maps[0].items["1"]`` is ``[26, 51, 41, 0, 0, [], {}, 1]`` —
    **id 26, Command Center**, ``training_time`` 5, ``min_level`` 1,
    ``group_type`` ``COMMAND_CENTER`` — with an **empty** attribute bag.  **No
    player state was fabricated**: the pair is exercisable against the corpus as
    committed, which is the first time an M8 line can say so.

    **No completion was captured, because no completion command exists.**  The
    dispatcher has 63 named branches and the ``complete_*`` family is exactly
    ``complete_collection``, ``complete_goal``, and ``complete_tutorial``.  There
    is no command that completes a queue and no command that materialises a unit
    from one, and every occurrence of ``attr["ts"]`` in the legacy source is a
    **write** or a **deletion**.  So this fixture evidences a push and a pop
    **only**: it says nothing about a finished queue, and that gap is on the
    record here and in the manifest rather than left for a reader to find.

    The only time-dependent value in the recorded **state** is the push's ``ts``
    stamp: ``push_queue_unit`` writes the wall clock (``engine.py:189``), so the
    stamp appears in the push step's after-state and in the pop step's
    before-state.  The pop's after-state carries no ``ts`` at all — the
    three-key teardown removed it — and is therefore the **seed** byte-for-byte,
    which is the strongest round-trip statement this pair can make.

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

Containment (same contract as the ten delivered captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The ten committed
  fixture directories are digest-pinned for the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the ten delivered capture harnesses):

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

    python -B apps/compat-api/capture_queue_fixture.py

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
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queue_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-unit-queues"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a corpus
# and initialize live legacy state).
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The committed corpus target, pinned here AND cross-checked against the real
# configuration and the real save below, so a drift fails the run instead of
# publishing a different fixture.
FIXTURE_MAP_KEY = queue_envelope.COMMITTED_MAP_KEY
FIXTURE_ITEM_ID = queue_envelope.COMMITTED_ITEM_ID
FIXTURE_ITEM_NAME = queue_envelope.COMMITTED_ITEM_NAME
FIXTURE_TRAINING_TIME = queue_envelope.COMMITTED_TRAINING_TIME
FIXTURE_MIN_LEVEL = queue_envelope.COMMITTED_MIN_LEVEL
FIXTURE_GROUP_TYPE = queue_envelope.COMMITTED_GROUP_TYPE
FIXTURE_CELL = [51, 41]
FIXTURE_EXPECTED_VECTOR: List[int] = [0] * queue_envelope.RESOURCE_VECTOR_SLOTS
FIXTURE_EXPECTED_PLACEMENTS = queue_envelope.COMMITTED_PLACEMENTS
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = dict(
    queue_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    queue_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    name: 0 for name in queue_envelope.COMMITTED_RESOURCE_BEFORE
}
FIXTURE_EXPECTED_INCREASED_POPULATION = 0
FIXTURE_EXPECTED_MAP_SIZES_PRESENT = False
TARGET_RULE = (
    "the committed corpus's own REAL placed training producer: maps[0].items['1'] "
    "is [26, 51, 41, 0, 0, [], {}, 1] — id 26, Command Center, training_time 5, "
    "min_level 1, group_type COMMAND_CENTER — with an EMPTY attribute bag. Both "
    "queue commands are therefore exercisable against the corpus as committed, "
    "with NO fabricated player state, which is what makes this the first M8 line "
    "that can own a real executed-legacy queue fixture. The map key is the legacy "
    "map index the branches read as args[0] and nothing more"
)

# Committed fixtures that must be byte-identical across this run.
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
)

# The executed-legacy probe this capture runs itself, after the recorded steps and
# on the same live server.  It is recorded in the manifest rather than as a step
# because it is evidence for the derivation's guarantees, not a recorded
# transaction of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does a queue command actually write, and what happens when the "
            "client-sent resource vector is not neutral?"
        ),
        "commands": [
            'push_queue_unit([1]) with a CLIENT-SENT vector '
            '[0, 500, 0, 0, 0, 0, 0, 0]',
        ],
        "attr_after": "nu incremented from absent to 1 and ts stamped with the "
        "server clock; nothing else in the row changed",
        "xp_before": 4,
        "xp_after": 504,
        "changed_top_level_map_keys": ["items", "xp"],
        "other_resources": "gold 2000, wood 2000, oil 2000, steel 2000, "
        "playerInfo.cash 5 and privateState.mana 0 all unchanged",
        "response": '{"result":"success"}',
        "established": (
            "the branch writes ONLY the addressed row's attribute bag "
            "(command.py:676-685 -> engine.py:183-189): nu is set to 1 when "
            "absent and incremented when present, and ts is stamped with "
            "timestamp_now(). The experience move is entirely client-sent: "
            "apply_resources runs BEFORE the branch (command.py:40; "
            "engine.py:251-271) and applies the 8-slot vector verbatim per "
            "resource as max(current + delta, 0)"
        ),
        "why_it_matters": (
            "this is the executed evidence for the derived NEUTRAL vector and "
            "for the endpoint's second post-execution proof half. A queue "
            "command that carried a non-zero vector would move a balance "
            "through this very branch, so proving after execution that EVERY "
            "stored resource is unchanged is what distinguishes a correct queue "
            "intent from a resource-minting exploit wearing its clothes (design "
            "D4). Without probe 1 the 'nothing moved' proof would be a "
            "tautology"
        ),
        "executed_in_this_capture": True,
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_push_queue_unit", "command_pop_queue_unit")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5,
                         "cash": 6, "mana": 7}

# The map fields that hold a slot of the 8-slot vector.  ``cash`` and ``mana``
# live outside the map (``playerInfo`` / ``privateState``), so they are absent
# here by construction.
MAP_RESOURCE_FIELDS = ("xp", "gold", "wood", "oil", "steel")

# Every other map field the executed transactions must leave byte-identical,
# named explicitly so the pre-publish check is readable, and then enforced for
# the **whole** key set (including the fields the corpus does not record).
MAP_FIELDS_THAT_MUST_NOT_MOVE = (
    "id",
    "store",
    "level",
    "currentQuestVars",
    "expirableUnitsTime",
    "idCurrentMission",
    "idCurrentTreasure",
    "increasedPopulation",
    "numTradesDone",
    "questTimes",
    "race",
    "receivedAssists",
    "resourceAlliesMarket",
    "resourcesTraded",
    "skin",
    "timestamp",
    "timestampLastChapter",
    "timestampLastTrade",
    "timestampLastTreasure",
    "world_id",
    "expansions",
)

# The one map field the queue branches own through their row: ``items``.  It is
# the transaction's subject and the only field a queue command may write.
ITEMS_FIELD = "items"
# The JSON-pointer prefix of the addressed row's attribute bag.
ROW_ATTR_POINTER = "/maps/0/items/%d/6" % FIXTURE_MAP_KEY


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The committed configuration document, or a refusal.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (see :data:`CONFIG_MAIN`).
    """
    try:
        document = json.loads(CONFIG_MAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    if not isinstance(document, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the committed config is not an object")
    return document


def config_item(item_id: int) -> Dict[str, Any]:
    """The committed item row for ``item_id``, or a refusal.

    Read from the **stored** configuration (which resolves far fewer items than
    the normalized package, because the legacy loader applies its own dedup and
    patch pipeline) and coerced exactly as the legacy accessor coerces it, so
    the pinned ``training_time`` / ``min_level`` figures are the ones the
    running server itself would read.
    """
    for row in config_document().get("items", []):
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get("id", -1)) != int(item_id):
                continue
        except (TypeError, ValueError):
            continue
        return row
    raise CaptureError(
        EXIT_ENVIRONMENT,
        "the committed config resolves no item %d" % item_id,
    )


def _config_int(item_id: int, field: str) -> int:
    raw = config_item(item_id).get(field)
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed config's item %d records a non-integer %s (%r)"
            % (item_id, field, raw),
        )


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
    replayed (queue parity works from the intent, not over HTTP), and
    redacting it keeps reruns byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact
    sent bytes; this keeps the record secret-free even if that placeholder ever
    changes.
    """
    envelope = queue_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return queue_envelope.data_field(envelope)


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


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven stored resource values the legacy code maintains."""
    first_map = document["maps"][0]
    return {
        "xp": first_map["xp"],
        "gold": first_map["gold"],
        "wood": first_map["wood"],
        "oil": first_map["oil"],
        "steel": first_map["steel"],
        "cash": document["playerInfo"]["cash"],
        "mana": document["privateState"]["mana"],
    }


def leaf_differences(before: Any, after: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ."""

    def walk(one: Any, other: Any, path: str) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                child = "%s/%s" % (path, key)
                if key not in one or key not in other:
                    collected.append(child)
                    continue
                walk(one[key], other[key], child)
        elif isinstance(one, list) and isinstance(other, list):
            for index in range(max(len(one), len(other))):
                child = "%s/%d" % (path, index)
                if index >= len(one) or index >= len(other):
                    collected.append(child)
                    continue
                walk(one[index], other[index], child)
        elif one != other:
            collected.append(path or "/")

    collected: List[str] = []
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


# --------------------------------------------------------- derived batches --
def build_push_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded push batch: one ``push_queue_unit`` with the neutral vector.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.
    """
    envelope = queue_envelope.build_envelope(
        map_key=FIXTURE_MAP_KEY, action=queue_envelope.ACTION_PUSH, ts=ts
    )
    verify_envelope(envelope, queue_envelope.ACTION_PUSH)
    return envelope


def build_pop_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded pop batch: one ``pop_queue_unit`` with the neutral vector."""
    envelope = queue_envelope.build_envelope(
        map_key=FIXTURE_MAP_KEY, action=queue_envelope.ACTION_POP, ts=ts
    )
    verify_envelope(envelope, queue_envelope.ACTION_POP)
    return envelope


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any], action: str) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its **map-index-only** argument list, and its
    **neutral** vector are the derived contract (design D2/D4); that a real
    client sends exactly this is **derived** too, because no legacy branch reads
    any content behind it.  All of it is pinned here against the committed
    config and fresh save instead, and any drift fails the run rather than
    silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(queue_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a queue batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != queue_envelope.ACTION_COMMANDS[action]:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (queue_envelope.ACTION_COMMANDS[action], entry[1]),
        )
    if entry[2] != [FIXTURE_MAP_KEY]:
        raise CaptureError(
            EXIT_REQUEST,
            "args must be [%d] — the map index is the queue commands' ONLY "
            "argument" % FIXTURE_MAP_KEY,
        )
    if len(entry[2]) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a queue command takes exactly one positional argument, got %r"
            % (entry[2],),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived neutral vector drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR),
        )
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying:
        raise CaptureError(
            EXIT_REQUEST,
            "the queue vector must be neutral, got slots %r" % (paying,),
        )


def verify_target(before: Dict[str, Any]) -> None:
    """The corpus's own queue target, verified against the real config."""
    row = before["maps"][0][ITEMS_FIELD].get(str(FIXTURE_MAP_KEY))
    if not isinstance(row, list) or len(row) != 8:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed corpus has no eight-field row at map key %d"
            % FIXTURE_MAP_KEY,
        )
    if row[0] != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the row at map key %d holds item %r, not the pinned %d"
            % (FIXTURE_MAP_KEY, row[0], FIXTURE_ITEM_ID),
        )
    if [row[1], row[2]] != FIXTURE_CELL:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the row at map key %d sits at %r, not the pinned %r"
            % (FIXTURE_MAP_KEY, [row[1], row[2]], FIXTURE_CELL),
        )
    if row[6] != {}:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the row at map key %d already carries the attribute bag %r; the "
            "fixture assumes an EMPTY bag" % (FIXTURE_MAP_KEY, row[6]),
        )
    if resources_of(before) != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's resources are %r, not the committed %r"
            % (resources_of(before), FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    if before["maps"][0]["store"] != {}:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's storage is not empty; the fixture assumes %r"
            % (before["maps"][0]["store"],),
        )
    if len(before["maps"][0][ITEMS_FIELD]) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save holds %d placements, not the pinned %d"
            % (len(before["maps"][0][ITEMS_FIELD]), FIXTURE_EXPECTED_PLACEMENTS),
        )
    # The committed content behind the target, read from the stored config the
    # running server itself loads, so the pinned training_time / min_level are
    # the ones legacy would read.
    item = config_item(FIXTURE_ITEM_ID)
    if str(item.get("name")) != FIXTURE_ITEM_NAME:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed config's item %d is named %r, not the pinned %r"
            % (FIXTURE_ITEM_ID, item.get("name"), FIXTURE_ITEM_NAME),
        )
    if _config_int(FIXTURE_ITEM_ID, "training_time") != FIXTURE_TRAINING_TIME:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed config's item %d records a training_time other than "
            "the pinned %d" % (FIXTURE_ITEM_ID, FIXTURE_TRAINING_TIME),
        )
    if _config_int(FIXTURE_ITEM_ID, "min_level") != FIXTURE_MIN_LEVEL:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed config's item %d records a min_level other than the "
            "pinned %d" % (FIXTURE_ITEM_ID, FIXTURE_MIN_LEVEL),
        )
    if str(item.get("group_type")) != FIXTURE_GROUP_TYPE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed config's item %d records group_type %r, not the "
            "pinned %r" % (FIXTURE_ITEM_ID, item.get("group_type"), FIXTURE_GROUP_TYPE),
        )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    action: str,
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived neutral
    vector under the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the
    branch (``command.py:40``) and applies the 8-slot vector verbatim, per
    resource, as ``max(current + delta, 0)``; the queue helper then writes only
    the addressed row's attribute bag.  Any mismatch means the capture would
    publish a fixture that contradicts its own derivation, so the run fails with
    exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_map_key = entry[2][0]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    if sent_map_key != FIXTURE_MAP_KEY:
        raise CaptureError(
            EXIT_REQUEST,
            "the sent map key %r is not the pinned %d" % (sent_map_key, FIXTURE_MAP_KEY),
        )

    # --- the subject: the derived attribute bag, through ONE derivation shared
    # with the endpoint (so the capture and the service cannot disagree).
    before_attr = map_before[ITEMS_FIELD][str(FIXTURE_MAP_KEY)][6]
    after_attr = map_after[ITEMS_FIELD][str(FIXTURE_MAP_KEY)][6]
    try:
        derived = queue_envelope.derived_queue(before_attr, action)
    except queue_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_REQUEST, "the queue derivation does not resolve: [%s] %s" % (error.code, error)
        )
    divergence = queue_envelope.expected_attr(before_attr, action, after_attr)
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed %s did not produce the derived queue result: %s"
            % (action, divergence),
        )
    projection = queue_envelope.project_queue(after_attr)

    # --- the placements: none is added, removed, or changed besides the
    # addressed row's own attribute bag.
    items_before = map_before[ITEMS_FIELD]
    items_after = map_after[ITEMS_FIELD]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].item keys changed; a queue command adds and removes none",
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS),
        )
    for other in items_before:
        if str(other) == str(FIXTURE_MAP_KEY):
            continue
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; a queue command rewrites no other row"
                % other,
            )
    addressed_after = items_after[str(FIXTURE_MAP_KEY)]
    if [addressed_after[0], addressed_after[1], addressed_after[2]] != [
        FIXTURE_ITEM_ID,
        FIXTURE_CELL[0],
        FIXTURE_CELL[1],
    ]:
        raise CaptureError(
            EXIT_REQUEST,
            "the addressed row's identity or cell changed: %r" % (addressed_after[:3],),
        )

    # --- the other map scalars.
    if map_after["increasedPopulation"] != FIXTURE_EXPECTED_INCREASED_POPULATION:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].increasedPopulation is %r, not the committed %r"
            % (
                map_after["increasedPopulation"],
                FIXTURE_EXPECTED_INCREASED_POPULATION,
            ),
        )
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; a queue stores nothing")
    if ("map_sizes" in map_after) != FIXTURE_EXPECTED_MAP_SIZES_PRESENT:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].map_sizes presence changed (before: %s, after: %s); the "
            "committed corpus does not record the field and a queue command must "
            "never create it" % ("map_sizes" in map_before, "map_sizes" in map_after),
        )

    # --- the whole key set, so a field this tool does not name cannot move
    # either (this is what enforces ``map_sizes`` staying absent).
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a queue command writes "
            "one row's attribute bag and adds or removes nothing"
            % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field == ITEMS_FIELD:
            continue
        if field in MAP_RESOURCE_FIELDS:
            # The map's own resource fields are the client-sent vector's
            # territory; they are checked by value below.
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the queue helpers write only the addressed "
                "row's attribute bag" % field,
            )
    for field in MAP_FIELDS_THAT_MUST_NOT_MOVE:
        if field in map_before and field not in map_after:
            raise CaptureError(EXIT_REQUEST, "maps[0].%s was removed" % field)

    # --- the private state and the player info.
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; no queue branch writes it" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST,
            "playerInfo changed; the queue branches write none of it",
        )

    # --- the money: every stored resource must have moved by EXACTLY the
    # derived neutral vector under legacy's max(current + delta, 0).  For a
    # queue command that is no movement at all; the value-level half of design
    # D4's post-execution proof, asserted here against the executed legacy
    # server itself.
    total = list(entry[3])
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        delta = total[RESOURCE_VECTOR_SLOTS[name]]
        if delta != FIXTURE_EXPECTED_RESOURCE_DELTA[name]:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived vector for %s is %r, not the documented %r"
                % (name, delta, FIXTURE_EXPECTED_RESOURCE_DELTA[name]),
            )
        current = before_resources[name]
        expected = max(current + delta, 0)
        if after_resources[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (name, current, after_resources[name], expected),
            )
    if after_resources != FIXTURE_EXPECTED_RESOURCE_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "the after-state resources %r are not the documented %r"
            % (after_resources, FIXTURE_EXPECTED_RESOURCE_AFTER),
        )
    return {
        "action": action,
        "command": derived["command"],
        "attr_before": dict(before_attr),
        "attr_after": dict(after_attr),
        "derived": derived,
        "projection_after": projection,
        "changed_row_pointer": ROW_ATTR_POINTER,
        "changed_leaves": leaf_differences(before, after),
    }


def build_probe_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The probe's batch: one ``push_queue_unit`` with a client-sent vector.

    Crafted by hand rather than through the derivation, because the whole point
    is the vector the derivation **refuses** to express:
    :func:`queue_envelope.validate_vector` would reject it, which is exactly the
    guarantee the probe makes concrete.
    """
    if ts is None:
        ts = 1700000000
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [
                0,
                queue_envelope.PUSH_COMMAND,
                [FIXTURE_MAP_KEY],
                [0, 500, 0, 0, 0, 0, 0, 0],
            ]
        ],
    }


def verify_probe_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof for the executed probe, returning its observed facts.

    The probe is the executed evidence for the derived neutral vector and the
    endpoint's "nothing moved" proof: a **client-sent** non-zero slot moves a
    balance through this very branch.  So the probe asserts exactly that — the
    sent experience moved by exactly the sent delta, and every other stored
    resource and every other field is untouched.
    """
    try:
        entry = envelope["commands"][0]
        sent_vector = list(entry[3])
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "probe envelope/save shape unexpected: %s" % error)
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        expected = max(before_resources[name] + sent_vector[RESOURCE_VECTOR_SLOTS[name]], 0)
        if after_resources[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "probe: resource %s went %r -> %r, not the sent-delta %r"
                % (name, before_resources[name], after_resources[name], expected),
            )
    for field in sorted(set(map_before) | set(map_after)):
        if field in MAP_RESOURCE_FIELDS:
            # The map's own resource fields are the client-sent vector's
            # territory and were already checked by value above; cash and mana
            # live outside the map entirely.
            continue
        if field == ITEMS_FIELD:
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "probe: maps[0].%s changed, but the branch writes only the "
                "addressed row's attribute bag (the experience move is the "
                "client-sent vector)" % field,
            )
    return {
        "attr_after": dict(
            map_after[ITEMS_FIELD][str(FIXTURE_MAP_KEY)][6]
        ),
        "xp_before": before_resources["xp"],
        "xp_after": after_resources["xp"],
        "changed_top_level_map_keys": [
            field
            for field in sorted(set(map_before) | set(map_after))
            if map_after.get(field) != map_before.get(field)
        ],
        "leaf_differences": leaf_differences(before, after),
        "resources_before": before_resources,
        "resources_after": after_resources,
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
        description="Capture the executed-legacy production-queue fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-queue-capture-staging-"))
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
        transactions: List[Dict[str, Any]] = []
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
                "Login form (USERID + GAMEVERSION) exactly as the ten delivered "
                "captures send it; recorded for session fidelity — command.php "
                "performs no session validation. user_key would be redacted if "
                "present.",
            )
        )

        # --- step 2: the push ------------------------------------------------
        before_push = canonical_save(save_path)
        if save_bytes_sha(before_push) != save_bytes_sha(before_login):
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the corpus changed between the login and the push step",
            )
        push_envelope = build_push_envelope()
        push_data = queue_envelope.data_field(push_envelope)
        push_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": push_data,
        }
        push_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(push_form),
            cookie=cookie,
            timeout=30.0,
        )
        if push_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_push_queue_unit: expected HTTP 200, got %r"
                % push_result["status"],
            )
        after_push = canonical_save(save_path)
        push_body = push_result.pop("body")
        push_note = (
            "command.php form (USERID, user_key, language, data) with the "
            "derived <64-hex>;<json> envelope carrying exactly one command: "
            "[[0,\"push_queue_unit\",[1],[0,0,0,0,0,0,0,0]]] against map key 1 "
            "— the committed corpus's real placed training producer, id 26 "
            "Command Center, with an empty attribute bag. The map index is the "
            "command's ONLY argument; no cost, duration, training time, count, "
            "readiness, or outcome is sent, and the resources_changed is the "
            "NEUTRAL vector because a queue's price is a client-sent delta "
            "(do_command applies it before the branch). The branch's own effect "
            "— nu set to 1 and ts stamped — and the ABSENCE of any validation "
            "(no producer check, no training_time, no min_level, no count bound) "
            "are ESTABLISHED. user_key is redacted in this record; accessToken "
            "is the crafted empty placeholder, never a token value."
        )
        summaries.append(
            write_step(
                staging,
                "command_push_queue_unit",
                push_result,
                push_body,
                before_push,
                after_push,
                push_form,
                push_note,
            )
        )
        push_facts = verify_transaction(
            before_push, after_push, queue_envelope.ACTION_PUSH, push_envelope
        )
        if json.loads(push_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_push_queue_unit response is not the legacy "
                '{"result": "success"}: %r' % (push_body,),
            )

        # --- step 3: the pop ------------------------------------------------
        before_pop = canonical_save(save_path)
        pop_envelope = build_pop_envelope()
        pop_data = queue_envelope.data_field(pop_envelope)
        pop_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": pop_data,
        }
        pop_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(pop_form),
            cookie=cookie,
            timeout=30.0,
        )
        if pop_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_pop_queue_unit: expected HTTP 200, got %r"
                % pop_result["status"],
            )
        after_pop = canonical_save(save_path)
        pop_body = pop_result.pop("body")
        pop_note = (
            "command.php form (USERID, user_key, language, data) with the "
            "derived <64-hex>;<json> envelope carrying exactly one command: "
            "[[0,\"pop_queue_unit\",[1],[0,0,0,0,0,0,0,0,0]]] against the same "
            "map key 1, immediately after the push, so the row carries "
            "nu 1 and the decrement reaches zero. The recorded effect is the "
            "THREE-KEY TEARDOWN: nu, ts, and ui are deleted TOGETHER "
            "(engine.py:198-204), which no inspection of the dispatcher would "
            "reveal. The map index is the only argument and the vector is "
            "NEUTRAL, exactly as for the push. This step is a POP, not a "
            "COMPLETION: the legacy server has no command that completes a "
            "queue, and nothing server-side turns a queue into a unit. user_key "
            "is redacted in this record; accessToken is the crafted empty "
            "placeholder, never a token value."
        )
        summaries.append(
            write_step(
                staging,
                "command_pop_queue_unit",
                pop_result,
                pop_body,
                before_pop,
                after_pop,
                pop_form,
                pop_note,
            )
        )
        pop_facts = verify_transaction(
            before_pop, after_pop, queue_envelope.ACTION_POP, pop_envelope
        )
        if json.loads(pop_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_pop_queue_unit response is not the legacy success "
                "result: %r" % (pop_body,),
            )
        # The pop's after-state has no ts at all, so that step's recorded state
        # carries no time-dependent leaf: its before and after are byte-identical.
        pop_leaf_diff = leaf_differences(before_pop, after_pop)
        # The three-key teardown restores the row's bag, so the pop step's
        # AFTER-state is the **seed** byte-for-byte — the strongest round-trip
        # statement this pair can make, and the reason the pair needs no
        # fabricated state to begin with.
        if save_bytes_sha(after_pop) != save_bytes_sha(before_login):
            raise CaptureError(
                EXIT_REQUEST,
                "the three-key teardown was expected to restore the addressed "
                "row's attribute bag, so the pop step's after-state must be the "
                "seed byte-for-byte; it differs at %r"
                % (leaf_differences(before_login, after_pop),),
            )
        if pop_leaf_diff != ["%s/nu" % ROW_ATTR_POINTER, "%s/ts" % ROW_ATTR_POINTER]:
            raise CaptureError(
                EXIT_REQUEST,
                "the pop step must differ from its own before-state at exactly "
                "the two keys the teardown removes, got %r" % (pop_leaf_diff,),
            )
        transactions.append(push_facts)
        transactions.append(pop_facts)

        # --- the executed-legacy probe (not a recorded step) ---------------
        probe_envelope = build_probe_envelope()
        probe_data = queue_envelope.data_field(probe_envelope)
        probe_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": probe_data,
        }
        before_probe = canonical_save(save_path)
        probe_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(probe_form),
            cookie=cookie,
            timeout=30.0,
        )
        if probe_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "probe: expected HTTP 200, got %r" % probe_result["status"],
            )
        probe_body = probe_result.pop("body")
        after_probe = canonical_save(save_path)
        probe_facts = verify_probe_transaction(before_probe, after_probe, probe_envelope)
        if json.loads(probe_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe response is not the legacy success result: %r" % (probe_body,),
            )
        probe_record = dict(PROBES[0])
        probe_record.update(probe_facts)
        print(
            "capture: probe attr %r, xp %r -> %r, changed map keys %r"
            % (
                probe_facts["attr_after"],
                probe_facts["xp_before"],
                probe_facts["xp_after"],
                probe_facts["changed_top_level_map_keys"],
            )
        )

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
        resources_after = resources_of(after_pop)
        manifest = {
            "schema": "godot-unit-queues/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for a legacy "
                "production-queue push followed by a pop on the committed "
                "corpus's own real placed training producer; the "
                "executed-legacy parity oracle for the Compatibility API v0 "
                "queue endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_queue_fixture.py"
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
                "push": True,
                "pop": True,
                "completion": False,
                "completion_captured": False,
                "completion_command_exists": False,
                "note": (
                    "A PUSH and a POP were captured, and NO COMPLETION WAS "
                    "CAPTURED — because the legacy server has no completion "
                    "command at all. The dispatcher has 63 named branches and "
                    "the complete_* family is exactly complete_collection, "
                    "complete_goal, and complete_tutorial; no command completes "
                    "a queue and no command materialises a unit from one. Every "
                    "occurrence of attr['ts'] in the legacy source is a WRITE "
                    "(engine.py:189, engine.py:198) or a DELETION "
                    "(engine.py:202), so there is no server-side elapsed-time "
                    "evaluation either and no readiness rule to reproduce. This "
                    "fixture therefore evidences a push and a pop ONLY and says "
                    "nothing about a finished queue; the missing completion is on "
                    "the record here rather than left for a reader to find"
                ),
                "no_server_side_completion": {
                    "dispatcher_named_branches": 63,
                    "complete_family": [
                        "complete_collection",
                        "complete_goal",
                        "complete_tutorial",
                    ],
                    "queue_completion_command": None,
                    "unit_materialising_command": None,
                    "attr_ts_uses": {
                        "writes": ["engine.py:189", "engine.py:198"],
                        "deletions": ["engine.py:202"],
                        "readers": ["command.py:733 (soulmixer_speedup only, and "
                                    "not a general queue path)"],
                    },
                    "consequence": "a queue can be pushed and popped and nothing "
                    "server-side ever finishes it; the production line owns that "
                    "missing completion as its finding, and this line refuses to "
                    "invent a readiness rule the legacy server does not have",
                },
            },
            "target": {
                "map_key": FIXTURE_MAP_KEY,
                "item_id": FIXTURE_ITEM_ID,
                "item_name": FIXTURE_ITEM_NAME,
                "training_time": FIXTURE_TRAINING_TIME,
                "min_level": FIXTURE_MIN_LEVEL,
                "group_type": FIXTURE_GROUP_TYPE,
                "cell": FIXTURE_CELL,
                "row_before": before_login["maps"][0][ITEMS_FIELD][
                    str(FIXTURE_MAP_KEY)
                ],
                "attr_before": before_login["maps"][0][ITEMS_FIELD][
                    str(FIXTURE_MAP_KEY)
                ][6],
                "fabricated_state": False,
                "target_rule": TARGET_RULE,
            },
            "intent": {
                "map_key_sent": FIXTURE_MAP_KEY,
                "map_key_rule": "the legacy map index is the queue commands' ONLY "
                "argument (command.py:677, command.py:700); no producer, "
                "duration, count, readiness, or outcome is accepted, and the "
                "extra keys a client might add are ignored",
                "vector_rule": "NO queue cost is claimed or implemented (design "
                "D4): a queue's price would be a CLIENT-SENT delta, because "
                "do_command applies the request's per-command vector before the "
                "branch (command.py:40; engine.py:251-271) as "
                "max(current + delta, 0). The derived vector is NEUTRAL and the "
                "endpoint's second post-execution proof half requires every "
                "stored resource to be UNCHANGED",
                "derived": {
                    "push": {
                        "command": push_envelope["commands"][0][1],
                        "args": push_envelope["commands"][0][2],
                        "resources_changed": push_envelope["commands"][0][3],
                    },
                    "pop": {
                        "command": pop_envelope["commands"][0][1],
                        "args": pop_envelope["commands"][0][2],
                        "resources_changed": pop_envelope["commands"][0][3],
                    },
                    "vector_is_neutral": True,
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(push_envelope),
                    "commands_per_batch": 1,
                },
                "command_contract": [
                    {
                        "command": record["command"],
                        "args": record["args"],
                        "effect": record["effect"],
                        "source": record["source"],
                        "validation": record["validation"],
                        "offered_by_the_endpoint": record["offered"],
                        **(
                            {"why_not_offered": record["why_not_offered"]}
                            if "why_not_offered" in record
                            else {}
                        ),
                    }
                    for record in queue_envelope.COMMANDS
                ],
                "no_validation": queue_envelope.NO_VALIDATION,
                "no_elapsed_time": queue_envelope.NO_ELAPSED_TIME,
                "teardown": queue_envelope.TEARDOWN,
                "speedup_contract": {
                    "recorded": True,
                    "implemented": False,
                    "precondition": "ts AND ui in the addressed row's attribute "
                    "bag; the legacy branch raises KeyError without either",
                    "duration_source": "the QUEUED UNIT's sm_training_time, not "
                    "the building's training_time",
                    "unit_reading": "SECONDS (the cost divides by an hour)",
                    "cost_formula": queue_envelope.SPEEDUP_COST_FORMULA,
                    "charges_anything": False,
                    "teardown": "sets ts = 0 so a later refresh sees no timer",
                    "author_verdict": "Quite useless cost calculation for "
                    "understanding it (command.py:732)",
                    "field_coverage": queue_envelope.SPEEDUP_FIELD_COVERAGE,
                    "refusal_instead_of_a_crash": queue_envelope.REFUSAL_NOTE,
                    "endpoint_action": "none: this endpoint offers no speedup "
                    "intent at all",
                },
                "status": "established: the three branches' exact argument lists "
                "and effects, the ABSENCE of any validation among them, that "
                "every attr['ts'] use is a write or a deletion except "
                "soulmixer_speedup's read, that branch's four lines and its "
                "comment, the 63-branch dispatcher and the absence of any "
                "queue-completion command, apply_resources running before "
                "dispatch with a request-supplied vector, the committed "
                "sm_training_time coverage, and the resulting states of these "
                "two executed transactions. DERIVED and never observed from the "
                "Flash client: that a real client sends exactly these two "
                "batches, and that the derived vectors are neutral. The claim is "
                "about what the legacy server does with a map index, NEVER about "
                "what a Flash client sent, and no cost, timer, readiness, "
                "completion, or produced unit is claimed",
            },
            "probes": [probe_record],
            "transactions": transactions,
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "map_key": FIXTURE_MAP_KEY,
                "placement_count_before": len(before_login["maps"][0][ITEMS_FIELD]),
                "placement_count_after": len(after_pop["maps"][0][ITEMS_FIELD]),
                "map_sizes_present_before": "map_sizes" in before_login["maps"][0],
                "map_sizes_present_after": "map_sizes" in after_pop["maps"][0],
                "increased_population_before": before_login["maps"][0][
                    "increasedPopulation"
                ],
                "increased_population_after": after_pop["maps"][0][
                    "increasedPopulation"
                ],
                "store_after": after_pop["maps"][0]["store"],
                "bought_units_before": before_login["privateState"]["boughtUnits"],
                "bought_units_after": after_pop["privateState"]["boughtUnits"],
                "dead_heroes_after": after_pop["privateState"]["deadHeroes"],
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "other_rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "map_key_set_unchanged": True,
                "private_state_unchanged": True,
                "player_info_unchanged": True,
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) only bites when a "
                "delta would drive a balance below zero; the derived vector is the "
                "NEUTRAL all-zero vector, so no balance moves at all and the clamp "
                "is never exercised by this fixture. That the vector really is "
                "client-sent and really would move a balance through this very "
                "branch is established by probe 1 above",
                "unit_produced": False,
                "unit_note": "NO unit is created, trained, spawned, or placed by "
                "either captured command. The legacy server has no command that "
                "materialises a unit from a queue, so a captured push is not a "
                "captured production",
                "readiness_computed": False,
                "readiness_note": "NO readiness, remaining time, or progress ratio "
                "is computed anywhere in this contract, because the legacy server "
                "evaluates no queue's elapsed time (design D1/D2)",
                "count_bound_applied": False,
                "count_bound_note": "NO maximum count is applied: the engine sets "
                "none, and a documented absence is not a licence to invent a cap "
                "(design D5)",
                "queue_writes": [
                    "engine.apply_resources applies the derived NEUTRAL vector on "
                    "the single command with max(..., 0) per resource, BEFORE the "
                    "branch (command.py:40; engine.py:251-271)",
                    "engine.push_queue_unit sets attr['nu'] to 1 when absent and "
                    "increments it when present, and stamps attr['ts'] with "
                    "timestamp_now() (engine.py:183-189) — nothing else",
                    "engine.pop_queue_unit returns without writing anything when "
                    "attr['nu'] is absent, otherwise decrements, re-stamps "
                    "attr['ts'] on a partial decrement, and at zero DELETES "
                    "attr['nu'], attr['ts'], and attr['ui'] together "
                    "(engine.py:191-204) — nothing else",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE and the recorded RESPONSE carry exactly "
                    "ONE time-dependent VALUE, appearing in exactly two files: "
                    "push_queue_unit stamps attr['ts'] with the wall clock "
                    "(engine.py:189), so that stamp is in the push step's "
                    "after.json and in the pop step's before.json — the latter "
                    "because the pop runs after the push, on the row the push "
                    "queued. The pop step's AFTER-state carries no stamp at all, "
                    "because the three-key teardown removed it: that after-state "
                    "is the seed byte-for-byte. The leaves below are the whole "
                    "record-metadata and envelope-clock surface, and the claim is "
                    "machine-checkable: a leaf-level diff of two consecutive runs "
                    "must differ at exactly these paths and nowhere else"
                ),
                "state_leaves": [
                    ROW_ATTR_POINTER + "/ts in steps/command_push_queue_unit/"
                    "after.json (and therefore that whole row's serialization, "
                    "because the digest covers the payload)",
                    ROW_ATTR_POINTER + "/ts in steps/command_pop_queue_unit/"
                    "before.json (the same stamp, read by the pop's own "
                    "derivation)",
                ],
                "stable_state_leaves": [
                    "steps/command_push_queue_unit/before.json is byte-stable",
                    "steps/command_pop_queue_unit/after.json is byte-stable AND "
                    "equal to the seed, because the teardown removed the queue",
                    "the login step's before.json and after.json are both "
                    "byte-stable and identical to each other",
                ],
                "leaves": [
                    "/captured_at_utc in steps/login_post/request.json",
                    "/captured_at_utc in steps/login_post/response.meta.json",
                    "/captured_at_utc in steps/command_push_queue_unit/request.json",
                    "/captured_at_utc in steps/command_push_queue_unit/response.meta.json",
                    "/captured_at_utc in steps/command_pop_queue_unit/request.json",
                    "/captured_at_utc in steps/command_pop_queue_unit/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in steps/login_post/response.meta.json",
                    "/headers/Date in steps/command_push_queue_unit/response.meta.json",
                    "/headers/Date in steps/command_pop_queue_unit/response.meta.json",
                    "the envelope ts inside each command step's request.json "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                ],
                "stable_by_derivation": (
                    "the pushed count, the three-key teardown, every placement "
                    "count, and all seven stored resources are byte-stable "
                    "because the derivation is fixed: a push always derives count "
                    "1 on a row whose bag is empty, a pop at that count always "
                    "tears the three keys down, and the derived vectors are "
                    "neutral. Only the wall-clock instant the branch stamps is "
                    "not derivable, and it is compared by SHAPE (a strict integer, "
                    "not earlier than the pre-execution one) rather than by value"
                ),
                "documented_normalization": (
                    "queue parity applies NO clock normalization: the recorded "
                    "count is compared by value (exactly the derived count), the "
                    "three-key teardown is compared by presence, every key the "
                    "branch does not own is compared by value, and every stored "
                    "resource is compared by value (exactly unchanged, because the "
                    "derived vector is neutral). The ONLY comparison that is not "
                    "by value is the start instant, which is checked for being a "
                    "strict integer and for NOT moving backwards: "
                    "engine.timestamp_now has one-second resolution, so two "
                    "commands inside one second legitimately stamp the same "
                    "value and a 'strictly later' rule would refuse a correct "
                    "transaction. The branch's own ts stamp is the only clock in "
                    "the recorded state"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, construction, "
                    "collect, and expand fixtures are digest-pinned for the same "
                    "reason."
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
                "capture:   %-28s %s %s -> %d (%d bytes, save unchanged: %s)"
                % (
                    summary["name"],
                    summary["method"],
                    summary["target"],
                    summary["status"],
                    summary["response_bytes"],
                    summary["save_unchanged_by_call"],
                )
            )
        for facts in transactions:
            print(
                "capture: %s via %s: attr %r -> %r, projection %r"
                % (
                    facts["action"],
                    facts["command"],
                    facts["attr_before"],
                    facts["attr_after"],
                    facts["projection_after"],
                )
            )
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

    except queue_envelope.EnvelopeError as error:
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
