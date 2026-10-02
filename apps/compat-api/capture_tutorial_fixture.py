#!/usr/bin/env python3
"""Capture the executed-legacy tutorial fixture: two rounds, one flag, two vectors.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, collect, expand, level, queue,
collection, research, and quest captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of every already committed fixture directory.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Runs **two** disposable rounds.  Two are required rather than one, and the
   reason is the corpus: ``completed_tutorial`` is ``0`` in the seed and ``1``
   after any completing step, so the only step that exercises the ``0 -> 1``
   transition can run **once per disposable copy**.  Folding both into a single
   server would silently capture a second ``1 -> 1`` rewrite instead.
4. Per round: builds a disposable copy under the system temp root (root
   ``*.py``, ``config/``, ``mods/``, ``villages/``, ``templates/`` and
   ``saves/`` seeded from ``tests/saves/fresh-player.json``), starts the REAL
   legacy server (``python -B server.py`` in the disposable copy), waits for
   loopback readiness, executes the round's recorded requests, and tears the
   server down again — proving the port is released each time.

   ==========  ==========================  ==========================
   round        recorded steps               purpose
   ==========  ==========================  ==========================
   ``neutral``  ``login_post``,              THE PARITY TRANSACTION: the
               ``command_tutorial_15``,      derived neutral vector moves
               ``command_tutorial_15_        nothing and the flag flips
               again``                       ``0 -> 1``; the repeat shows the
                                             rewrite is idempotent
   ``minting``  ``login_post``,              THE PROOF ANCHOR: one request
               ``command_tutorial_15_        moves ALL SEVEN stored
               minting``                      resources **and** the flag, so
                                             "nothing moved" is not a tautology
   ==========  ==========================  ==========================

5. Executes **one** executed-legacy probe, in the ``minting`` round, recorded in
   the manifest rather than as a step: the same client ladder on a
   **non-completing** step (``24``, the hole's upper edge), which moves the same
   seven resources with the flag untouched.  That separates the two effects —
   completion moves the flag, the client vector moves resources — and it is what
   shows the ladder's effect is a property of the vector rather than of the
   completing branch.
6. Verifies each round structurally **before** publishing: the login step left
   the save byte-identical, the flag reached exactly the expected value, every
   placement row is byte-identical with the count unmoved, ``store`` and the whole
   ``privateState`` are untouched, and every stored resource moved by **exactly**
   the derived delta under legacy's ``max(current + delta, 0)``.
7. Tears both servers down, removes both disposable copies, and re-checks
   containment.

Exit codes
    0     success
    2     environment (wrong interpreter, missing seed, bad ``--out``)
    3     port 5055 busy
    4     server failed to start, or a server did not stop
    5     a request failed, or the executed save contradicts the derivation
    6     containment violation (working-tree bytes changed, a committed fixture
           directory changed, or the disposable corpus saves changed during
           server startup / login)
    7     fixture write failure

Why two rounds and not a probe
    The minting transaction is not a probe.  It is the evidence that makes the
    endpoint's post-execution proof non-tautological, so it is recorded as a
    step with its own before/after saves; the ``24`` decline is the probe,
    because it is corroboration rather than the anchor.

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_tutorial_fixture.py

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
import tutorial_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-tutorial"

CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# --------------------------------------------------------------- committed --
FIXTURE_EXPECTED_FLAG_BEFORE = 0
FIXTURE_EXPECTED_FLAG_AFTER = 1
FIXTURE_EXPECTED_PLACEMENTS = 40

FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
FIXTURE_EXPECTED_VECTOR: List[int] = [0] * tutorial_envelope.RESOURCE_VECTOR_SLOTS

# The client ladder the committed investigation executed against this very
# command.  Slot 0 is the legacy vector's ``unknown``, which
# ``engine.apply_resources`` reads and DISCARDS (``engine.py:253``), so the
# ladder's 101 must NOT appear among the changed leaves -- that absence is
# itself part of the evidence and is asserted.
FIXTURE_MINTING_VECTOR: List[int] = list(tutorial_envelope.MINTING_LADDER)
FIXTURE_MINTING_STEP = tutorial_envelope.MINTING_STEP
FIXTURE_HOLE_EDGE_STEP = tutorial_envelope.GATE_HOLE_HIGH

TARGET_RULE = (
    "the tutorial completion flag, playerInfo.completed_tutorial, on the "
    "committed fresh-player corpus: the seed records 0, and the gate "
    "'tutorial_step >= 25 or tutorial_step == 15' completes on 15. The step "
    "is CLIENT INTENT and the completion is DERIVED SERVER-SIDE by applying "
    "that gate (design D2). The vector is NEUTRAL: no committed tutorial "
    "reward of any kind exists, so the only derivable vector moves nothing "
    "(design D4)"
)

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
)

# The one executed-legacy probe this capture runs itself, in the minting round,
# after that round's recorded step and on the same live server.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "does the client-sent resource ladder move balances because the "
            "tutorial COMPLETED, or because the client sent it?"
        ),
        "commands": [
            "complete_tutorial([24]) with the CLIENT-SENT vector "
            "[101, 3, 7, 11, 13, 17, 19, 23]",
        ],
        "step": FIXTURE_HOLE_EDGE_STEP,
        "step_in_gate_hole": True,
        "gate_satisfied": False,
        "flag_before": FIXTURE_EXPECTED_FLAG_AFTER,
        "flag_after": FIXTURE_EXPECTED_FLAG_AFTER,
        "resources_moved": 7,
        "changed_leaves": 7,
        "response": '{"result":"success"}',
        "established": (
            "24 is the UPPER EDGE of the nine-value hole (16..24 inclusive), so "
            "the branch declines: it prints nothing about completion and leaves "
            "playerInfo.completed_tutorial alone. The same ladder still moves all "
            "seven stored resources, because apply_resources runs BEFORE the "
            "branch (command.py:40; engine.py:251-271)"
        ),
        "why_it_matters": (
            "this separates the two effects the recorded steps show together. "
            "Without it, the minting round's eight changed leaves could be read "
            "as 'completing the tutorial mints resources'. With it, the ladder "
            "moves resources on a DECLINING step, so the movement belongs to the "
            "client-sent vector and the flag flip belongs to the gate -- which "
            "is exactly the separation the endpoint's two-part proof asserts"
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

# The two vector slots stored OUTSIDE ``maps[0]``, so the map-scoped
# "nothing but a resource slot moved" checks must exempt them too.  Both are
# verified by VALUE under the clamp in the money check, never here.
# engine.apply_resources: save["playerInfo"]["cash"] at engine.py:267 and
# save["privateState"]["mana"] at engine.py:268.
VECTOR_SLOT_OUTSIDE_MAP = {"playerInfo": "cash", "privateState": "mana"}

# Where each of the seven stored resources actually lives in the save, as the
# JSON pointer ``leaf_differences`` reports it.  Only five are map fields;
# naming all seven explicitly keeps the minting round's leaf assertion honest
# instead of assuming every resource sits under ``/maps/0``.
RESOURCE_LEAF_POINTERS = {
    "xp": "/maps/0/xp",
    "gold": "/maps/0/gold",
    "wood": "/maps/0/wood",
    "oil": "/maps/0/oil",
    "steel": "/maps/0/steel",
    "cash": "/playerInfo/cash",
    "mana": "/privateState/mana",
}

# Every other map field a tutorial step must leave byte-identical, enforced for
# the WHOLE key set as well, so a field this tool does not name cannot move.
MAP_FIELDS_THAT_MUST_NOT_MOVE = (
    "id",
    "items",
    "store",
    "xp",
    "gold",
    "wood",
    "oil",
    "steel",
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
    "level",
)

# The ONE field the branch owns.  It lives in the save-level ``playerInfo``
# record, NOT in ``maps[0]`` -- the first delivered line to write outside the
# map -- and ``maps[0]`` has no such key at all.
FLAG_FIELD = tutorial_envelope.FLAG_KEY
FLAG_RECORD = tutorial_envelope.PLAYER_INFO_RECORD

# ------------------------------------------------------------------ plan ----
# Two rounds because the corpus records ``0`` once per disposable copy.  Each
# round names its own expected outcome so the check is data-driven rather than
# branched in code.
ROUND_PLAN: Tuple[Dict[str, Any], ...] = (
    {
        "round": "neutral",
        "purpose": (
            "the parity transaction: the derived NEUTRAL vector moves nothing "
            "and the gate flips the flag 0 -> 1"
        ),
        "steps": (
            {
                "name": "command_tutorial_15",
                "step": FIXTURE_MINTING_STEP,
                "vector": FIXTURE_EXPECTED_VECTOR,
                "expect_flag": FIXTURE_EXPECTED_FLAG_AFTER,
                "expect_resources_moved": 0,
                "note": (
                    "THE RECORDED TRANSACTION. command.php form (USERID, "
                    "user_key, language, data) with the derived "
                    "<64-hex>;<json> envelope carrying exactly one command: a "
                    "complete_tutorial whose single argument is the CLIENT'S "
                    "STEP, sent as INTENT and never as an outcome. Completion "
                    "is DERIVED SERVER-SIDE by applying the committed gate "
                    "'tutorial_step >= 25 or tutorial_step == 15' to that step "
                    "(design D2). The resources_changed is the NEUTRAL VECTOR "
                    "[0, 0, 0, 0, 0, 0, 0, 0] because no committed tutorial "
                    "reward of any kind exists (design D4). What is ESTABLISHED: "
                    "the branch writes playerInfo.completed_tutorial = 1 and "
                    "nothing else, and the 8-slot vector is applied verbatim "
                    "before it under the max(..., 0) clamp. What is DERIVED: "
                    "that the Flash client ever sends this shape, or counts "
                    "steps this way. user_key is redacted in this record; "
                    "accessToken is the crafted empty placeholder, never a token."
                ),
            },
            {
                "name": "command_tutorial_15_again",
                "step": FIXTURE_MINTING_STEP,
                "vector": FIXTURE_EXPECTED_VECTOR,
                "expect_flag": FIXTURE_EXPECTED_FLAG_AFTER,
                "expect_resources_moved": 0,
                "note": (
                    "the SAME request a second time, recorded to establish that "
                    "the write is IDEMPOTENT: the branch assigns 1 over 1, so "
                    "the save is byte-identical and ZERO leaves change. This is "
                    "the executed counterpart of the endpoint's "
                    "already-complete refusal -- legacy answers success and "
                    "changes nothing rather than erroring"
                ),
            },
        ),
    },
    {
        "round": "minting",
        "purpose": (
            "the proof anchor: ONE request moves all seven stored resources AND "
            "the flag, so the endpoint's 'nothing moved' proof is not a "
            "tautology"
        ),
        "steps": (
            {
                "name": "command_tutorial_15_minting",
                "step": FIXTURE_MINTING_STEP,
                "vector": FIXTURE_MINTING_VECTOR,
                "expect_flag": FIXTURE_EXPECTED_FLAG_AFTER,
                "expect_resources_moved": 7,
                "note": (
                    "the PROOF ANCHOR, and the transaction the endpoint REFUSES "
                    "to reproduce. The step and the completing gate are exactly "
                    "as in the neutral round; only the CLIENT-SENT ladder "
                    "differs: [101, 3, 7, 11, 13, 17, 19, 23]. Legacy adds each "
                    "slot to the stored balance as max(current + delta, 0), so "
                    "this single request moves all seven stored resources "
                    "alongside the flag -- eight changed leaves. Slot 0's 101 is "
                    "the vector's 'unknown', which apply_resources reads and "
                    "DISCARDS (engine.py:253), so it must NOT appear among the "
                    "changed leaves; that absence is asserted, not assumed. "
                    "This is the evidence that makes the endpoint's "
                    "post-execution proof non-tautological (design D4): without "
                    "it, 'no stored resource moved' would be vacuously true of a "
                    "command that provably can move all seven"
                ),
            },
        ),
    },
)


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The committed configuration document, or a refusal.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module.
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


def measure_content_absence() -> Dict[str, Any]:
    """Count ``tutorial`` in the committed content, at any depth.

    The contract rests on there being **no** committed tutorial content: no step
    list, no step count, no gate definition, no tutorial text, no reward.  That
    absence is the reason the derivation refuses to invent any of them, so it is
    measured here against the real files and a corpus drift fails the run.
    """
    document = config_document()
    total = 0
    paths: List[str] = []

    def walk(node: Any, path: str) -> None:
        nonlocal total
        if isinstance(node, dict):
            for key in sorted(node):
                walk(key, "%s/<key>" % path)
                walk(node[key], "%s/%s" % (path, key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, "%s/%d" % (path, index))
        elif isinstance(node, str) and "tutorial" in node.lower():
            total += 1
            paths.append(path)

    walk(document, "")
    normalized_dir = REPO_ROOT / "packages" / "game-content" / "normalized"
    normalized_total = 0
    for path in sorted(normalized_dir.glob("*.json")):
        body = path.read_text(encoding="utf-8", errors="replace").lower()
        normalized_total += body.count("tutorial")
    return {
        "config_main_occurrences": total,
        "config_main_paths": paths,
        "normalized_package_occurrences": normalized_total,
        "total": total + normalized_total,
    }


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
    like a logged-in client); only the *record* is redacted — it is an ephemeral
    token value of a dead disposable server, it can never be replayed (tutorial
    parity works from the intent, not over HTTP), and redacting it keeps reruns
    byte-stable for these fields.
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
    envelope = tutorial_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return tutorial_envelope.data_field(envelope)


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


def flag_of(document: Dict[str, Any]) -> Any:
    """``save["playerInfo"]["completed_tutorial"]`` — the one field the branch owns."""
    record = document.get(FLAG_RECORD)
    if not isinstance(record, dict) or FLAG_FIELD not in record:
        raise CaptureError(
            EXIT_REQUEST,
            "the save has no %s.%s, so the tutorial flag cannot be read"
            % (FLAG_RECORD, FLAG_FIELD),
        )
    return record[FLAG_FIELD]


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
    step_root: Path,
    name: str,
    result: Dict[str, Any],
    body: bytes,
    before: Dict[str, Any],
    after: Dict[str, Any],
    form: Dict[str, str],
    note: str,
) -> Dict[str, Any]:
    """Write one step's request/before/response/after records (full saves).

    ``step_root`` is the directory that will CONTAIN this step, so the two
    disposable rounds cannot collide on a shared ``login_post`` name.
    """
    step_dir = step_root / name
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


# --------------------------------------------------------- derived batches ---
def build_step_envelope(
    step: int,
    vector: List[int],
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """The derived batch for one ``complete_tutorial`` command.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.

    The neutral vector is the only one the derivation will normally emit, but a
    client ladder is accepted here **directly** (``validate_vector`` is bypassed
    on purpose) so the capture can record what legacy actually does with one.
    That bypass is confined to this function and is the reason the minting round
    exists; the endpoint never takes a client vector at all.
    """
    if ts is None:
        envelope = tutorial_envelope.build_envelope(step)
    else:
        envelope = tutorial_envelope.build_envelope(step, vector=vector, ts=ts)
        envelope["commands"][0][3] = list(vector)
    if ts is None:
        # The neutral path already carries the neutral vector; the minting path
        # substitutes the recorded ladder, deliberately and only here.
        envelope["commands"][0][3] = list(vector)
    return envelope


def verify_envelope(
    envelope: Dict[str, Any],
    step: int,
    vector: List[int],
    require_completing: bool = True,
) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    ``require_completing`` is False only for the probe, whose whole point is to
    send a step the gate **declines** so the client vector's effect can be
    observed on a non-completing branch.
    """
    if sorted(envelope) != sorted(tutorial_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a tutorial batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != tutorial_envelope.COMPLETE_TUTORIAL_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (tutorial_envelope.COMPLETE_TUTORIAL_COMMAND, entry[1]),
        )
    if entry[2] != [step]:
        raise CaptureError(
            EXIT_REQUEST,
            "complete_tutorial args must be [%d], got %r" % (step, entry[2]),
        )
    if len(entry[2]) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "complete_tutorial takes exactly one positional argument "
            "(command.py:61), got %r" % (entry[2],),
        )
    if entry[3] != list(vector):
        raise CaptureError(
            EXIT_REQUEST,
            "the derived vector drifted: %r (expected %r)" % (entry[3], vector),
        )
    if len(entry[3]) != tutorial_envelope.RESOURCE_VECTOR_SLOTS:
        raise CaptureError(
            EXIT_REQUEST,
            "the resource vector must carry %d slots, got %r"
            % (tutorial_envelope.RESOURCE_VECTOR_SLOTS, entry[3]),
        )
    # The step must satisfy the committed gate, or the recorded flag flip would
    # be unexplainable by the derivation.
    if require_completing and not tutorial_envelope.gate_satisfied(step):
        raise CaptureError(
            EXIT_REQUEST,
            "recorded step %d does not satisfy the committed gate, so it cannot "
            "complete the tutorial" % step,
        )
    if not require_completing and tutorial_envelope.gate_satisfied(step):
        raise CaptureError(
            EXIT_REQUEST,
            "probe step %d satisfies the gate, so it cannot demonstrate that the "
            "client vector moves resources independently of completion" % step,
        )


# -------------------------------------------------------- transaction check --
def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
    expect_flag: Any,
    expect_resources_moved: int,
    require_completing: bool = True,
) -> Dict[str, Any]:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the sent vector under the
    legacy rules, in the order legacy applies them: ``engine.apply_resources``
    (``engine.py:251-271``) runs **before** the branch (``command.py:40``) and
    applies the 8-slot vector verbatim, per resource, as
    ``max(current + delta, 0)``; ``command.complete_tutorial``
    (``command.py:60-66``) then, when the gate fires, assigns ``1`` to
    ``playerInfo["completed_tutorial"]`` and returns.

    Any mismatch means the capture would publish a fixture that contradicts its
    own derivation, so the run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_step = entry[2][0]
        sent_vector = list(entry[3])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope shape unexpected: %s" % error)

    map_before = before["maps"][0]
    map_after = after["maps"][0]

    # --- the flag, under the committed gate ---------------------------------
    # The SEED value is pinned by verify_seed(), not here: this function checks
    # the TRANSITION, and the neutral round's second step legitimately begins
    # from the flag its own first step wrote.
    flag_before = flag_of(before)
    flag_after = flag_of(after)
    if flag_after != expect_flag:
        raise CaptureError(
            EXIT_REQUEST,
            "%s.%s is %r after execution, not the expected %r"
            % (FLAG_RECORD, FLAG_FIELD, flag_after, expect_flag),
        )
    if require_completing and not tutorial_envelope.gate_satisfied(sent_step):
        raise CaptureError(
            EXIT_REQUEST, "sent step %r does not satisfy the gate" % sent_step,
        )
    if not require_completing and tutorial_envelope.gate_satisfied(sent_step):
        raise CaptureError(
            EXIT_REQUEST,
            "probe step %r satisfies the gate, so it cannot isolate the client "
            "vector's effect" % sent_step,
        )
    flag_moved = flag_before != flag_after

    # --- the flag lives OUTSIDE the map, and maps[0] has no such key -------
    if FLAG_FIELD in map_before or FLAG_FIELD in map_after:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0] carries %r, but the flag is a save-level playerInfo field "
            "and the map must never gain it" % FLAG_FIELD,
        )

    # --- the placements: none is added, removed, or changed.
    items_before = map_before["items"]
    items_after = map_after["items"]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if len(items_before) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_REQUEST,
            "before-state placement count is %d (expected %d)"
            % (len(items_before), FIXTURE_EXPECTED_PLACEMENTS),
        )
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].item keys changed; a tutorial step places nothing"
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS),
        )
    for other in items_before:
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; a tutorial step rewrites no placement at all"
                % other,
            )

    # --- the storage.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; a tutorial step stores nothing")

    # --- the whole map key set, so a field this tool does not name cannot move.
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a tutorial step adds or "
            "removes nothing" % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field in MAP_RESOURCE_FIELDS:
            # Resource slots are checked by value below, under the clamp.
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the branch writes only %s.%s"
                % (field, FLAG_RECORD, FLAG_FIELD),
            )
    for field in MAP_FIELDS_THAT_MUST_NOT_MOVE:
        if field in map_before and field not in map_after:
            raise CaptureError(EXIT_REQUEST, "maps[0].%s was removed" % field)

    # --- the private state: nothing but the vector's own mana slot may move.
    # ``mana`` is stored here (engine.py:268) and IS slot 7 of the vector, so it
    # is deliberately exempted from this equality check and is instead verified
    # by VALUE under the max(..., 0) clamp in the money check below.  Asserting
    # it unchanged here would be asserting that the ladder cannot mint mana.
    private_before = before["privateState"]
    private_after = after["privateState"]
    if sorted(private_after) != sorted(private_before):
        raise CaptureError(
            EXIT_REQUEST,
            "privateState keys changed: %r -> %r; no complete_tutorial branch "
            "adds or removes one" % (sorted(private_before), sorted(private_after)),
        )
    for name in sorted(private_before):
        if name == VECTOR_SLOT_OUTSIDE_MAP["privateState"]:
            continue
        if private_after[name] != private_before[name]:
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; the branch writes only the flag and "
                "apply_resources moves only the vector's own slots" % name,
            )

    # --- the player info, field by field: only the flag and the vector's cash
    # slot may differ.  ``cash`` is stored in playerInfo (engine.py:267) and is
    # slot 6 of the vector, so it is verified by value below, not here.
    info_before = before["playerInfo"]
    info_after = after["playerInfo"]
    if sorted(info_after) != sorted(info_before):
        raise CaptureError(
            EXIT_REQUEST,
            "playerInfo keys changed: %r -> %r; the branch assigns one existing key"
            % (sorted(info_before), sorted(info_after)),
        )
    for name in sorted(info_before):
        if name in (FLAG_FIELD, VECTOR_SLOT_OUTSIDE_MAP["playerInfo"]):
            continue
        if info_after[name] != info_before[name]:
            raise CaptureError(
                EXIT_REQUEST,
                "playerInfo.%s changed; the branch writes only the flag" % name,
            )

    # --- the money: every stored resource must have moved by EXACTLY the sent
    # vector under legacy's max(current + delta, 0).  For the neutral vector
    # that is no movement at all; for the minting ladder it is a real mint.
    resources_before = resources_of(before)
    resources_after = resources_of(after)
    moved: List[str] = []
    for name, slot in sorted(RESOURCE_VECTOR_SLOTS.items()):
        delta = sent_vector[slot]
        expected = max(resources_before[name] + delta, 0)
        if resources_after[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "%s is %r after execution, not the expected %r "
                "(before %r + slot %d delta %r under the max(..., 0) clamp)"
                % (name, resources_after[name], expected, resources_before[name],
                   slot, delta),
            )
        if resources_after[name] != resources_before[name]:
            moved.append(name)
    if len(moved) != expect_resources_moved:
        raise CaptureError(
            EXIT_REQUEST,
            "%d stored resource(s) moved (%s), expected %d"
            % (len(moved), moved, expect_resources_moved),
        )

    # Slot 0 is the vector's ``unknown``: engine.py:253 reads and DISCARDS it,
    # so it must never appear as a stored change.
    if sent_vector[0] != 0:
        unknown_targets = [
            name for name, slot in RESOURCE_VECTOR_SLOTS.items() if slot == 0
        ]
        if unknown_targets:
            raise CaptureError(
                EXIT_REQUEST,
                "slot 0 must not map to a stored resource, but it maps to %r"
                % unknown_targets,
            )

    leaves = leaf_differences(before, after)
    flag_leaf = "/%s/%s" % (FLAG_RECORD, FLAG_FIELD)
    if flag_moved and flag_leaf not in leaves:
        raise CaptureError(
            EXIT_REQUEST,
            "the flag moved but its leaf %r is absent from the recorded diff %r"
            % (flag_leaf, leaves),
        )
    return {
        "flag_before": flag_before,
        "flag_after": flag_after,
        "flag_moved": flag_moved,
        "resources_before": resources_before,
        "resources_after": resources_after,
        "resources_moved": moved,
        "resources_moved_count": len(moved),
        "changed_leaves": leaves,
        "changed_leaf_count": len(leaves),
    }


# ------------------------------------------------------------------ steps ---
def post_command(
    envelope: Dict[str, Any],
    cookie: str,
    pid: str,
) -> Dict[str, Any]:
    """POST one derived batch to the disposable legacy command endpoint."""
    return http_request(
        LEGACY_PORT,
        "POST",
        DYNAMIC_ROOT + "/command.php",
        form={
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": tutorial_envelope.data_field(envelope),
        },
        cookie=cookie,
        timeout=30.0,
    )


def verify_seed(before: Dict[str, Any], where: str) -> None:
    """Pin the committed corpus facts the whole fixture depends on."""
    if flag_of(before) != FIXTURE_EXPECTED_FLAG_BEFORE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "%s: %s.%s is %r, not the committed %r"
            % (where, FLAG_RECORD, FLAG_FIELD, flag_of(before),
               FIXTURE_EXPECTED_FLAG_BEFORE),
        )
    resources = resources_of(before)
    if resources != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "%s: resources are %r, not the committed %r"
            % (where, resources, FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    if len(before["maps"][0]["items"]) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "%s: placement count is %d, not the committed %d"
            % (where, len(before["maps"][0]["items"]), FIXTURE_EXPECTED_PLACEMENTS),
        )


def login(save_path: Path, pid: str, out_dir: Path, round_name: str) -> str:
    """The login step; returns the session cookie and records the step.

    Recorded as ``steps/<round>/login_post`` so the two rounds keep distinct,
    self-describing step directories rather than colliding on one name.
    """
    before = canonical_save(save_path)
    login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
    result = http_request(LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0)
    if result["status"] != 302:
        raise CaptureError(
            EXIT_REQUEST, "login_post: expected HTTP 302, got %r" % result["status"],
        )
    after = canonical_save(save_path)
    if save_bytes_sha(before) != save_bytes_sha(after):
        raise CaptureError(
            EXIT_CONTAINMENT,
            "login_post mutated the disposable corpus save; the login step must "
            "leave it byte-identical",
        )
    body = result.pop("body")
    cookie = extract_session_cookie(result)
    write_step(
        out_dir / "steps" / round_name,
        "login_post",
        result,
        body,
        before,
        after,
        login_form,
        "Login form (USERID + GAMEVERSION) exactly as the boot, placement, "
        "purchase, move, sell, store, upgrade, construction, collect, expand, "
        "level, queue, collection, research, and quest captures send it; recorded "
        "for session fidelity — command.php performs no session validation. "
        "user_key would be redacted if present.",
    )
    return cookie


def run_round(
    plan: Dict[str, Any],
    tmp_parent: Path,
    out_dir: Path,
    keep_disposable: bool,
) -> Dict[str, Any]:
    """Build, run, verify, and tear down one disposable round.

    Returns the round's record.  The disposable copy is removed on every exit
    path except ``--keep-disposable``, and the port is proven free again.

    Step records are written straight into ``out_dir`` because the disposable
    copy — which holds the live corpus save the steps are compared against — is
    deleted on teardown.  Each round writes under ``steps/<round>/``, so the
    two rounds cannot collide and each is self-describing.
    """
    name = plan["round"]
    disposable, pid, seed_sha = build_disposable(tmp_parent)
    process = None
    try:
        saves_dir = disposable / "saves"
        save_path = saves_dir / ("%s.save.json" % pid)
        seed_group = save_group_record(saves_dir)

        process, stdout_path, stderr_path = start_server(disposable)
        if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
            raise CaptureError(
                EXIT_SERVER,
                "round %s: the legacy server did not become ready on %s:%d\n%s"
                % (name, LEGACY_HOST, LEGACY_PORT, read_tail(stderr_path)),
            )
        startup_record = save_group_record(saves_dir)
        if startup_record["sha256"] != seed_group["sha256"]:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "round %s: server startup rewrote the seeded corpus saves (%s -> %s)"
                % (name, seed_group["sha256"], startup_record["sha256"]),
            )

        verify_seed(canonical_save(save_path), "round %s" % name)
        cookie = login(save_path, pid, out_dir, name)

        summaries: List[Dict[str, Any]] = []
        outcomes: List[Dict[str, Any]] = []
        for step_plan in plan["steps"]:
            before = canonical_save(save_path)
            envelope = build_step_envelope(step_plan["step"], list(step_plan["vector"]))
            verify_envelope(envelope, step_plan["step"], list(step_plan["vector"]))
            result = post_command(envelope, cookie, pid)
            if result["status"] != 200:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s: expected HTTP 200, got %r" % (step_plan["name"], result["status"]),
                )
            after = canonical_save(save_path)
            body = result.pop("body")
            try:
                payload = json.loads(body.decode("utf-8"))
            except ValueError as error:
                raise CaptureError(
                    EXIT_REQUEST, "%s: response is not JSON: %s" % (step_plan["name"], error),
                )
            if payload != {"result": "success"}:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s: response is not the legacy {\"result\": \"success\"}: %r"
                    % (step_plan["name"], payload),
                )
            outcome = verify_transaction(
                before, after, envelope, step_plan["expect_flag"],
                step_plan["expect_resources_moved"],
            )
            write_step(
                out_dir / "steps" / name, step_plan["name"], result, body, before,
                after,
                {
                    "USERID": pid,
                    "user_key": USER_KEY,
                    "language": LANGUAGE,
                    "data": tutorial_envelope.data_field(envelope),
                },
                step_plan["note"],
            )
            summaries.append({"name": step_plan["name"], "step": step_plan["step"],
                              "vector": list(step_plan["vector"])})
            outcomes.append(outcome)

        # --- the one executed-legacy probe, in the minting round only --------
        probe_record: Optional[Dict[str, Any]] = None
        if name == "minting":
            probe_record = run_probe(save_path, pid, cookie)

        stop_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
        process = None
        if stop_error:
            raise CaptureError(EXIT_SERVER, "round %s: %s" % (name, stop_error))

        return {
            "round": name,
            "purpose": plan["purpose"],
            "seed_save_sha256": seed_sha,
            "steps": summaries,
            "outcomes": outcomes,
            "probe": probe_record,
            "server_stdout_tail": read_tail(stdout_path, 1200),
            "server_stderr_tail": read_tail(stderr_path, 1200),
        }
    finally:
        if process is not None:
            try:
                stop_server(process, LEGACY_HOST, LEGACY_PORT)
            except Exception:  # noqa: BLE001 - teardown must not mask the cause
                pass
        if keep_disposable:
            print("capture: round %s: keeping disposable at %s" % (name, disposable))
        else:
            shutil.rmtree(disposable, ignore_errors=True)


def run_probe(save_path: Path, pid: str, cookie: str) -> Dict[str, Any]:
    """Execute probe 1: the client ladder on a NON-COMPLETING step."""
    probe = PROBES[0]
    step = probe["step"]
    if tutorial_envelope.gate_satisfied(step):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "probe step %d no longer sits in the gate's hole; the probe's whole "
            "point is that it declines" % step,
        )
    if step not in tutorial_envelope.gate_hole_steps():
        raise CaptureError(
            EXIT_ENVIRONMENT, "probe step %d is not one of the recorded hole steps" % step,
        )
    before = canonical_save(save_path)
    envelope = build_step_envelope(step, FIXTURE_MINTING_VECTOR)
    verify_envelope(envelope, step, FIXTURE_MINTING_VECTOR, require_completing=False)
    result = post_command(envelope, cookie, pid)
    if result["status"] != 200:
        raise CaptureError(
            EXIT_REQUEST, "probe 1: expected HTTP 200, got %r" % result["status"],
        )
    after = canonical_save(save_path)
    outcome = verify_transaction(
        before, after, envelope, FIXTURE_EXPECTED_FLAG_AFTER,
        probe["resources_moved"], require_completing=False,
    )
    if outcome["flag_moved"]:
        raise CaptureError(
            EXIT_REQUEST, "probe 1: the flag moved on a declining step",
        )
    leaves = outcome["changed_leaves"]
    if len(leaves) != probe["changed_leaves"]:
        raise CaptureError(
            EXIT_REQUEST,
            "probe 1: %d changed leaves, expected %d (%r)"
            % (len(leaves), probe["changed_leaves"], leaves),
        )
    recorded = dict(probe)
    recorded["observed"] = outcome
    return recorded


# ------------------------------------------------------------------- main ---
def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest every already committed fixture directory."""
    record: Dict[str, Dict[str, object]] = {}
    for relative, label in PROTECTED_FIXTURES:
        directory = REPO_ROOT / relative
        if not directory.is_dir():
            raise CaptureError(
                EXIT_ENVIRONMENT, "missing committed fixture directory: %s" % relative
            )
        record[label] = dir_group_record(directory)
    return record


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy tutorial fixture "
        "(contained, loopback only, two disposable rounds)."
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="fixture output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-disposable",
        action="store_true",
        help="do not delete the disposable copies (for debugging only)",
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

    content_absence = measure_content_absence()
    if content_absence["total"] != tutorial_envelope.COMMITTED_CONTENT_OCCURRENCES:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed content now holds %d 'tutorial' occurrence(s), not the "
            "recorded zero (%r); the recorded absence this line rests on no "
            "longer holds" % (content_absence["total"], content_absence),
        )

    clear_previous_fixtures(out_dir)
    staging_parent = Path(tempfile.mkdtemp(prefix="socialwars-tutorial-"))
    tmp_parent = staging_parent
    rounds: List[Dict[str, Any]] = []
    try:
        for plan in ROUND_PLAN:
            record = run_round(plan, tmp_parent, out_dir, args.keep_disposable)
            rounds.append(record)
            print(
                "capture: round %s ok: %s"
                % (
                    record["round"],
                    ", ".join(
                        "%s: flag %r->%r moved=%d leaves=%d"
                        % (
                            step["name"],
                            outcome["flag_before"],
                            outcome["flag_after"],
                            outcome["resources_moved_count"],
                            outcome["changed_leaf_count"],
                        )
                        for step, outcome in zip(record["steps"], record["outcomes"])
                    ),
                )
            )
    except CaptureError as error:
        print("capture: failed: %s" % error, file=sys.stderr)
        return error.exit_code
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)

    # --- cross-round assertions -------------------------------------------
    neutral = next(r for r in rounds if r["round"] == "neutral")
    minting = next(r for r in rounds if r["round"] == "minting")

    # The parity transaction: the flag moved and NOTHING else did.
    parity = neutral["outcomes"][0]
    if parity["resources_moved_count"] != 0:
        raise CaptureError(
            EXIT_REQUEST, "the neutral round moved resources: %r"
            % parity["resources_moved"]
        )
    if not parity["flag_moved"]:
        raise CaptureError(EXIT_REQUEST, "the neutral round did not move the flag")
    if parity["changed_leaf_count"] != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "the parity transaction changed %d leaves, expected exactly the flag: %r"
            % (parity["changed_leaf_count"], parity["changed_leaves"]),
        )
    if parity["changed_leaves"] != ["/%s/%s" % (FLAG_RECORD, FLAG_FIELD)]:
        raise CaptureError(
            EXIT_REQUEST,
            "the parity transaction's changed leaves are %r, expected only the "
            "flag leaf" % parity["changed_leaves"],
        )

    # The idempotent repeat: zero leaves.
    repeat = neutral["outcomes"][1]
    if repeat["changed_leaf_count"] != 0:
        raise CaptureError(
            EXIT_REQUEST,
            "the repeat wrote %r; the flag assignment must be idempotent"
            % repeat["changed_leaves"],
        )

    # The proof anchor: ONE request moved all seven resources AND the flag, and
    # the discarded slot 0 is absent from the diff.
    anchor = minting["outcomes"][0]
    if anchor["resources_moved_count"] != tutorial_envelope.MINTING_RESOURCES_MOVED:
        raise CaptureError(
            EXIT_REQUEST,
            "the minting transaction moved %d resource(s), not the recorded %d: %r"
            % (anchor["resources_moved_count"],
               tutorial_envelope.MINTING_RESOURCES_MOVED, anchor["resources_moved"]),
        )
    if not anchor["flag_moved"]:
        raise CaptureError(
            EXIT_REQUEST, "the minting transaction did not move the flag",
        )
    if anchor["changed_leaf_count"] != tutorial_envelope.MINTING_CHANGED_LEAVES:
        raise CaptureError(
            EXIT_REQUEST,
            "the minting transaction changed %d leaves, not the recorded %d: %r"
            % (anchor["changed_leaf_count"], tutorial_envelope.MINTING_CHANGED_LEAVES,
               anchor["changed_leaves"]),
        )
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        leaf = RESOURCE_LEAF_POINTERS[name]
        if leaf not in anchor["changed_leaves"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the minting transaction did not change %s (%r); the ladder's slot "
                "for it should have moved the stored balance, changed leaves %r"
                % (name, leaf, anchor["changed_leaves"]),
            )
    if any("101" in leaf for leaf in anchor["changed_leaves"]):
        raise CaptureError(
            EXIT_REQUEST,
            "the discarded vector slot 0 leaked into the changed leaves %r"
            % anchor["changed_leaves"],
        )

    # --- publish ------------------------------------------------------------
    manifest: Dict[str, Any] = {
        "fixture": "godot-tutorial",
        "schema": "tutorial-fixture-v1",
        "executed_at_utc": iso_now(),
        "legacy": {
            "host": LEGACY_HOST,
            "port": LEGACY_PORT,
            "dynamic_root": DYNAMIC_ROOT,
            "game_version": GAME_VERSION,
            "language": LANGUAGE,
        },
        "interpreter": sys.version.split()[0],
        "why_two_rounds": (
            "playerInfo.completed_tutorial is 0 in the seed and 1 after any "
            "completing step, so the 0 -> 1 transition is exercisable exactly "
            "ONCE per disposable copy. Two rounds are therefore required, not "
            "stylistic: folding both into one server would silently record a "
            "1 -> 1 rewrite instead of the transition the fixture is about"
        ),
        "rounds": [
            {
                "round": record["round"],
                "purpose": record["purpose"],
                "seed_save_sha256": record["seed_save_sha256"],
                "steps": record["steps"],
                "outcomes": record["outcomes"],
                "probe": record["probe"],
            }
            for record in rounds
        ],
        "target": {
            "flag_record": FLAG_RECORD,
            "flag_key": FLAG_FIELD,
            "flag_before": FIXTURE_EXPECTED_FLAG_BEFORE,
            "flag_after": FIXTURE_EXPECTED_FLAG_AFTER,
            "placements": FIXTURE_EXPECTED_PLACEMENTS,
            "resources_before": FIXTURE_EXPECTED_RESOURCE_BEFORE,
            "neutral_vector": FIXTURE_EXPECTED_VECTOR,
            "minting_vector": FIXTURE_MINTING_VECTOR,
            "target_rule": TARGET_RULE,
            "fabricated_state": False,
            "the_map_has_no_such_key": True,
        },
        "gate": tutorial_envelope.gate_record(),
        "parity": {
            "neutralization": (
                "the parity transaction compares by VALUE with NO clock "
                "normalization: the derived flag, the unchanged placement count, "
                "the byte-identical placements, the byte-identical store, the "
                "byte-identical privateState, every other playerInfo field, and "
                "all seven stored resources. The ONLY wall-clock field, the "
                "request's envelope ts, is recorded but not compared, because it "
                "is the current time at capture"
            ),
            "minting_transaction_recorded_not_reproduced": (
                "the minting transaction is recorded as a step and is the anchor "
                "for the endpoint's second proof half. The endpoint REFUSES to "
                "reproduce it: its derived vector is neutral by construction, so "
                "it cannot express the ladder at all"
            ),
            "parity_covers": (
                "ONE parity transaction against the fresh-player corpus, which is "
                "the only save with completed_tutorial 0 outside the "
                "new-player template village. No progressed-player save exists "
                "with the flag at any other value, and none can: the step is "
                "never persisted, so a mid-tutorial save is unrepresentable"
            ),
        },
        "absences": {
            "committed_tutorial_content": content_absence,
            "committed_content_occurrences": tutorial_envelope.COMMITTED_CONTENT_OCCURRENCES,
            "no_reward_paid": True,
            "no_step_persisted": True,
            "stored_step_introduced": False,
            "gate_bounds_added": False,
            "legacy_raising_shapes_reproduced": False,
            "legacy_raising_shapes": list(tutorial_envelope.LEGACY_RAISING_SHAPES),
            "raising_shapes_divergence": (
                "the three input shapes legacy answers with an unhandled HTTP "
                "500 are REFUSED here with named codes, an empty payload, and no "
                "state change. This is the line's one deliberate divergence, "
                "confined to failure handling: for every step legacy ACCEPTS the "
                "state transition is identical"
            ),
            "flag_readers_in_legacy": tutorial_envelope.FLAG_READER_COUNT,
            "flag_writer_lines": list(tutorial_envelope.FLAG_WRITER_LINES),
            "flag_reaches_client_via": (
                "get_player_info.py:%d includes the whole playerInfo dict "
                "wholesale, by dict inclusion and not by any server-side naming "
                "of the field"
                % tutorial_envelope.FLAG_CLIENT_VIA_WHOLE_DICT_LINE
            ),
        },
        "probes": PROBES,
        "known_limits": [
            "no mid-tutorial save exists and none can be represented: the step "
            "is a local and is never persisted, so the corpus records 0 (the "
            "new-player template) or 1 and nothing in between",
            "no reward is paid and no stored resource moves in the parity "
            "transaction, because zero committed tutorial content exists",
            "no gate bound is added: legacy has neither an upper nor a lower "
            "bound and no type check, and a bound it does not have would be an "
            "invented rule (Server v1 / M13)",
            "no pixel parity and no windowed capture: nothing is rendered here",
            "the request's exact shape is DERIVED; its effect is ESTABLISHED. No "
            "Flash client was executed and none exists to execute",
            "the boundary arithmetic is pinned by the committed replay-harness "
            "test against a STUB oracle; this capture adds the executed-legacy "
            "fixture beside it rather than claiming that coverage as new",
        ],
    }
    try:
        write_json(out_dir / "capture-manifest.json", manifest)
    except OSError as error:
        print("capture: could not write the manifest: %s" % error, file=sys.stderr)
        return EXIT_WRITE

    # --- every recorded step must be on disk --------------------------------
    for record in rounds:
        for step in record["steps"]:
            step_dir = out_dir / "steps" / record["round"] / step["name"]
            for member in ("request.json", "before.json", "response.body",
                           "response.meta.json", "after.json"):
                if not (step_dir / member).is_file():
                    raise CaptureError(
                        EXIT_WRITE,
                        "round %s: step %s is missing %s"
                        % (record["round"], step["name"], member),
                    )
        login_dir = out_dir / "steps" / record["round"] / "login_post"
        if not (login_dir / "request.json").is_file():
            raise CaptureError(
                EXIT_WRITE, "round %s: login_post was not published" % record["round"]
            )

    post_groups = containment_snapshot()
    post_combined = snapshot_combined(post_groups)
    post_fixtures = protected_fixture_snapshot()
    for label, before in pre_fixtures.items():
        after = post_fixtures[label]
        if before["sha256"] != after["sha256"]:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "committed fixture %s changed during this capture (%s -> %s)"
                % (label, before["sha256"], after["sha256"]),
            )
    if pre_combined != post_combined:
        raise CaptureError(
            EXIT_CONTAINMENT,
            "working-tree bytes changed during this capture:\n%s"
            % post_combined,
        )
    if not port_is_free(LEGACY_HOST, LEGACY_PORT):
        raise CaptureError(
            EXIT_CONTAINMENT,
            "port %s:%d is still in use after teardown" % (LEGACY_HOST, LEGACY_PORT),
        )

    print(
        "capture: wrote %s (%d rounds, %d recorded steps, %d probe(s)); "
        "containment UNCHANGED"
        % (
            out_dir,
            len(rounds),
            sum(len(record["steps"]) for record in rounds),
            len(PROBES),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())