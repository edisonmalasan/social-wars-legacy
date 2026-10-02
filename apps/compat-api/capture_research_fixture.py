#!/usr/bin/env python3
"""Capture the executed-legacy research fixture: four branches, two tracks.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, collect, expand, level, queue,
and collection captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, upgrade, construction, collect, expand, level, queue,
   and collection fixtures.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root (root ``*.py``,
   ``config/``, ``mods/``, ``villages/``, ``templates/`` and ``saves/``
   seeded from ``tests/saves/fresh-player.json``).
4. Starts the REAL legacy server (``python -B server.py`` in the
   disposable copy) and waits for loopback readiness.
5. Executes **ten** recorded legacy requests, recording full canonical
   before/after save JSON plus the response for each step:

   * ``POST /``               — login form (session cookie, as a logged-in Flash
     client would send; 302, save unchanged)
   * eight ``POST .../command.php`` steps carrying **exactly one** command each,
     covering **every one of the eight branch-track combinations**:

     ============ ================ ==============================================
     step          command           args
     ============ ================ ==============================================
     step_track_0  next_research_step   ``[0]``
     step_track_1  next_research_step   ``[1]``
     cash_track_0  research_buy_step_cash ``[0, 0]``
     cash_track_1  research_buy_step_cash ``[0, 1]``
     item_track_0  next_research_item   ``[0]``
     item_track_1  next_research_item   ``[1]``
     reset_track_0 reset_research_item  ``[0]``
     reset_track_1 reset_research_item  ``[1]``
     ============ ================ ==============================================

     The cash branch's argument list is ``[cash, track]`` and every other
     branch's is ``[track]`` — the shape the committed source fixes.  The
     captured ``cash`` is the module's derived ``0``, **not** a client price.
6. Verifies each transaction structurally before publishing: the login step left
   the save byte-identical; every step's persisted vector matches the **derived**
   result for its branch and track, with the item branch's **paired** step-and-
   instant reset and the cash branch's **instant-only** zeroing checked
   explicitly; the **unaddressed** track and every counter the branch does not
   write are byte-identical; the placement map, ``store``, the whole private
   state outside the three counters, ``playerInfo`` and every **other** map
   field are unchanged; and **every one of the seven stored resources is
   unchanged** because the derived vector is neutral.
7. Runs **three** **executed-legacy probes** against the same live server, after
   the recorded steps and on the same disposable copy, each recorded in the
   manifest rather than as a step:

   * **probe 1** ``research_buy_step_cash([250, 0])`` with a client-sent
     ``[0, 500, 0, 0, 0, 0, 0, 0]`` vector.  It establishes the fact the
     endpoint's neutral vector and its second proof half exist for, **and** the
     fact the cash branch's own price argument is discarded: the branch is handed
     ``cash = 250`` and ``playerInfo.cash`` does **not** move, while the
     client-sent experience slot does.
   * **probe 2** ``next_research_step([0])`` then ``fast_forward([60])``.  It
     establishes the **fourth writer** of the research instant: the instant
     moves back by exactly the client-supplied 60 seconds and the step/item
     counters are untouched by the fast-forward itself.
   * **probe 3** ``fast_forward([9999999999])``.  It establishes the
     ``max(0, …)`` **clamp** the same line applies, again with the step/item
     counters untouched.
8. Stops the server, re-checks the working-tree containment snapshot and the
   thirteen committed fixture digests, discards the disposable copy, and writes
   the fixtures under ``--out`` (default: ``tests/fixtures/godot-research/``).

What this fixture does and does not show, stated up front
    The recorded steps target the committed corpus's **own** research state:
    ``privateState.researchStepNumber``, ``privateState.researchItemNumber``, and
    ``privateState.timeStampDoResearch`` are each ``[0, 0]`` of length 2.  **No
    player state was fabricated** — every one of the four branches is
    exercisable against the corpus as committed, which is the contrast with M8
    line 8, where ``resurrectable`` is unit-only and no fixture existed.

    **The eight steps round-trip to the seed.**  Each branch and each track is
    exercised in a deliberate order, and the **last** step (``reset_research_item``
    on track 1) restores all three counters to ``[0, 0]``, so that step's
    after-state is the first step's before-state byte-for-byte.  That is the
    strongest round-trip statement this set can make and is asserted here.

    **No completion was captured, because no completion exists.**  All three
    counters are **write-only** in the legacy source, so there is no readiness
    rule, no remaining-time computation, and no unlock gate to capture.  The
    fixture evidences the four counter transitions and nothing else.

    The only time-dependent value in the recorded **state** is the step branch's
    instant stamp: ``next_research_step`` writes the wall clock
    (``command.py:272``), so that stamp appears in the two step steps'
    after-states and in the two cash steps' before-states.

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

Containment (same contract as the thirteen delivered captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The thirteen committed
  fixture directories are digest-pinned for the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the thirteen delivered capture harnesses):

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

    python -B apps/compat-api/capture_research_fixture.py

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
import research_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-research"

# The committed corpus's own research state, pinned here AND cross-checked
# against the real seed below, so a drift fails the run instead of publishing a
# different fixture.
FIXTURE_EXPECTED_VECTOR: Dict[str, List[int]] = {
    key: list(value) for key, value in research_envelope.COMMITTED_VECTOR.items()
}
FIXTURE_EXPECTED_PLACEMENTS = research_envelope.COMMITTED_PLACEMENTS
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = dict(
    research_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    research_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    name: 0 for name in research_envelope.COMMITTED_RESOURCE_BEFORE
}
FIXTURE_EXPECTED_VECTOR_SLOTS: List[int] = [0] * research_envelope.RESOURCE_VECTOR_SLOTS
#: The eight captured branch-track combinations, in the order they are executed.
#: Four branches times two tracks, and the suite asserts this count.
STEP_PLAN: List[Dict[str, Any]] = [
    {"name": "command_next_research_step_track_0",
     "action": research_envelope.ACTION_STEP, "track": 0},
    {"name": "command_next_research_step_track_1",
     "action": research_envelope.ACTION_STEP, "track": 1},
    {"name": "command_research_buy_step_cash_track_0",
     "action": research_envelope.ACTION_BUY_STEP_CASH, "track": 0},
    {"name": "command_research_buy_step_cash_track_1",
     "action": research_envelope.ACTION_BUY_STEP_CASH, "track": 1},
    {"name": "command_next_research_item_track_0",
     "action": research_envelope.ACTION_ITEM, "track": 0},
    {"name": "command_next_research_item_track_1",
     "action": research_envelope.ACTION_ITEM, "track": 1},
    {"name": "command_reset_research_item_track_0",
     "action": research_envelope.ACTION_RESET, "track": 0},
    {"name": "command_reset_research_item_track_1",
     "action": research_envelope.ACTION_RESET, "track": 1},
]
TARGET_RULE = (
    "the committed corpus's OWN research state: privateState.researchStepNumber, "
    "privateState.researchItemNumber, and privateState.timeStampDoResearch are "
    "each [0, 0] of length 2, and no one of the 40 placed rows carries a "
    "research counter anywhere. All four research branches are therefore "
    "exercisable against the corpus as committed, with NO fabricated player "
    "state, which is the contrast with M8 line 8 where no fixture existed at "
    "all. The track index is the legacy `_type` the four branches read from "
    "args[0] (args[1] for the cash branch) and nothing more"
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
    ("tests/fixtures/godot-building-xp", "godot-building-xp"),
    ("tests/fixtures/godot-unit-queues", "godot-unit-queues"),
    ("tests/fixtures/godot-unit-collection", "godot-unit-collection"),
)

# The executed-legacy probes this capture runs itself, after the recorded steps
# and on the same live server.  They are recorded in the manifest rather than as
# steps because they are evidence for the derivation's guarantees, not recorded
# transactions of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does research_buy_step_cash do with the CASH it is handed, and "
            "what happens when the client-sent resource vector is not neutral?"
        ),
        "commands": [
            'research_buy_step_cash([250, 0]) with a CLIENT-SENT vector '
            '[0, 500, 0, 0, 0, 0, 0, 0]',
        ],
        "established": (
            "the branch's own price argument is READ and DISCARDED: args[0] is "
            "bound to `cash` (command.py:277) and never used, so the branch is "
            "handed 250 and playerInfo.cash does not move at all. The experience "
            "move is entirely client-sent: apply_resources runs BEFORE the branch "
            "(command.py:40; engine.py:251-271) and applies the 8-slot vector "
            "verbatim per resource as max(current + delta, 0)"
        ),
        "why_it_matters": (
            "this is the executed evidence for the derived NEUTRAL vector and for "
            "the endpoint's second post-execution proof half, AND the executed "
            "evidence for the 'no research price is charged' claim: a research "
            "command that carried a non-zero vector would move a balance through "
            "this very branch, so proving after execution that EVERY stored "
            "resource is unchanged is what distinguishes a correct research "
            "intent from a resource-minting exploit wearing its clothes (design "
            "D3). Without probe 1 the 'nothing moved' proof would be a tautology"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 2,
        "question": (
            "is fast_forward really a writer of the research instant, and is the "
            "number of seconds it subtracts the client's?"
        ),
        "commands": [
            "next_research_step([0]) to stamp a fresh instant",
            "fast_forward([60]) with the client-supplied 60 seconds",
        ],
        "established": (
            "fast_forward (command.py:905) reads the instant at command.py:923 and "
            "writes every track's entry at command.py:927 as "
            "max(0, instant - seconds), where seconds = args[0] is CLIENT-SUPPLIED "
            "(command.py:906). The observed instant therefore moves back by exactly "
            "the sent number of seconds"
        ),
        "why_it_matters": (
            "this makes the research instant CLIENT-WRITABLE in the same way M8 "
            "line 6 found a row's instant client-writable, and it is the only "
            "elapsed-time input the research system has. It is RECORDED as a fourth "
            "writer and IMPLEMENTED NOT AT ALL: no fast-forward action, no "
            "fast-forward route, and no elapsed-time rule anywhere (design D7)"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 3,
        "question": "does the fast-forward decrement CLAMP at zero, as its source says?",
        "commands": ["fast_forward([9999999999]) with nine billion seconds"],
        "established": (
            "the write is max(0, instant - seconds) (command.py:927), so a "
            "client-supplied value far beyond the instant lands on exactly 0 "
            "rather than a negative instant. This is the ONLY clamp the four "
            "research branches have, and it belongs to fast_forward, not to them"
        ),
        "why_it_matters": (
            "it completes the fourth writer's recorded shape: subtraction AND clamp, "
            "both from a client-supplied number. It is also why no counter bound is "
            "invoked anywhere on this line: the one clamp that exists is in a "
            "branch this endpoint deliberately does not offer (design D6/D7)"
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

# The one map field the research branches never touch.
ITEMS_FIELD = "items"

# The JSON-pointer prefix of the addressed track's step counter.
STEP_POINTER = "/privateState/%s/0" % research_envelope.KEY_STEP


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The committed configuration document, or a refusal.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (importing one would chdir into a corpus and initialize live legacy
    state).
    """
    try:
        document = json.loads(
            (REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    if not isinstance(document, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the committed config is not an object")
    return document


def measure_content_absence() -> Dict[str, Any]:
    """Measure the research content findings from the committed bytes.

    This is the capture's own measurement of the facts design D4 rests on, and
    it is recorded in the manifest verbatim so the hermetic suite can compare
    its own independent measurement against it.  **No legacy module is imported
    and nothing is written**: both inputs are read straight from disk.
    """
    normalized_dir = REPO_ROOT / "packages" / "game-content" / "normalized"
    files = sorted(normalized_dir.glob("*.json"))
    per_file: Dict[str, int] = {}
    for path in files:
        count = path.read_text(encoding="utf-8").lower().count("research")
        if count:
            per_file[path.name] = count
    config_text = (REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
    document = config_document()
    research_keys: List[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key in node:
                child = "%s/%s" % (path, key)
                if "research" in str(key).lower():
                    research_keys.append(child)
                walk(node[key], child)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, "%s/%d" % (path, index))

    walk(document, "")
    return {
        "normalized_files": len(files),
        "normalized_files_containing_research": per_file,
        "normalized_files_containing_research_count": len(per_file),
        "config_top_level_keys": len(document),
        "config_keys_containing_research": sorted(research_keys),
        "config_keys_containing_research_count": len(research_keys),
        "config_bytes_containing_research": config_text.lower().count("research"),
        "note": research_envelope.CONTENT_ABSENCE,
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
    token value of a dead disposable server and redacting it keeps reruns
    byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact sent
    bytes; this keeps the record secret-free even if that placeholder ever
    changes.
    """
    envelope = research_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return research_envelope.data_field(envelope)


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


def vector_of(document: Dict[str, Any]) -> Dict[str, List[int]]:
    """The three committed research counter vectors, copied."""
    return research_envelope.snapshot_counters(document)


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
def build_step_envelope(track: int, action: str,
                        ts: Optional[int] = None) -> Dict[str, Any]:
    """One recorded branch's batch, built from the SHARED derivation.

    Built from ``research_envelope`` rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.
    """
    envelope = research_envelope.build_envelope(track=track, action=action, ts=ts)
    verify_envelope(envelope, track, action)
    return envelope


def probe_envelope(commands: List[List[Any]], ts: Optional[int] = None) -> Dict[str, Any]:
    """A probe's batch, crafted by HAND rather than through the derivation.

    The whole point of each probe is a value the derivation **refuses** to
    express — a client-supplied cash amount, a client-supplied non-neutral
    vector, or a fast-forward command — and
    :func:`research_envelope.validate_vector` would reject each of them, which is
    exactly the guarantee the probes make concrete.
    """
    if ts is None:
        ts = 1700000000
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [list(command) for command in commands],
    }


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any], track: int, action: str) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its argument list, and its **neutral** vector are the
    derived contract (design D2/D3); that a real client sends exactly this is
    **derived** too, because no committed content sits behind any of it.  All of
    it is pinned here instead, and any drift fails the run rather than silently
    publishing a different fixture.
    """
    if sorted(envelope) != sorted(research_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a research batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != research_envelope.ACTION_COMMANDS[action]:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (research_envelope.ACTION_COMMANDS[action], entry[1]),
        )
    expected_args = [track]
    if action == research_envelope.CASH_ACTION:
        expected_args = [research_envelope.DERIVED_CASH, track]
    if entry[2] != expected_args:
        raise CaptureError(
            EXIT_REQUEST,
            "args must be %r — the cash branch takes [cash, track] and every "
            "other branch takes [track]" % (expected_args,),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR_SLOTS:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived neutral vector drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR_SLOTS),
        )
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying:
        raise CaptureError(
            EXIT_REQUEST,
            "the research vector must be neutral, got slots %r" % (paying,),
        )


def verify_target(before: Dict[str, Any]) -> None:
    """The corpus's own research state, verified against the seed file."""
    vector = vector_of(before)
    if vector != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's research vector is %r, not the committed %r"
            % (vector, FIXTURE_EXPECTED_VECTOR),
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
    # No placed row carries a research counter anywhere: the counters live in
    # privateState, so this asserts the corpus really has no research row.
    for key, row in before["maps"][0][ITEMS_FIELD].items():
        if "research" in json.dumps(row).lower():
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "placement row %s mentions a research counter; the fixture "
                "assumes the corpus places none" % key,
            )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    action: str,
    track: int,
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived **neutral**
    vector under the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the branch
    (``command.py:40``) and applies the 8-slot vector verbatim, per resource, as
    ``max(current + delta, 0)``; the research branch then writes only the
    addressed track's entries of the three committed counters.  Any mismatch
    means the capture would publish a fixture that contradicts its own
    derivation, so the run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_track = entry[2][-1]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    if sent_track != track:
        raise CaptureError(
            EXIT_REQUEST,
            "the sent track %r is not the pinned %d" % (sent_track, track),
        )

    # --- the subject: the derived vector, through ONE derivation shared with
    # the endpoint (so the capture and the service cannot disagree).
    before_vector = vector_of(before)
    after_vector = vector_of(after)
    try:
        derived = research_envelope.derived_research(before_vector, track, action)
    except research_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_REQUEST,
            "the research derivation does not resolve: [%s] %s" % (error.code, error),
        )
    divergence = research_envelope.expected_state(
        before_vector, action, track, after_vector
    )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed %s on track %d did not produce the derived result: %s"
            % (action, track, divergence),
        )
    projection = research_envelope.project_research(after_vector)

    # --- the placements: a research command rewrites no row at all.
    items_before = map_before[ITEMS_FIELD]
    items_after = map_after[ITEMS_FIELD]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].items keys changed; a research command adds and removes none",
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
                "placement row %s changed; a research command rewrites no row" % other,
            )

    # --- the other map scalars.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; research stores nothing")
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a research command adds "
            "or removes nothing" % (sorted(map_before), sorted(map_after)),
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
                "maps[0].%s changed; a research branch writes only the private "
                "state counters" % field,
            )

    # --- the private state: the three counters by derivation, every other key
    # byte-identical.  (cash and mana live inside privateState/playerInfo and are
    # checked by value below, so they are skipped here by name.)
    private_before = before["privateState"]
    private_after = after["privateState"]
    if sorted(private_after) != sorted(private_before):
        raise CaptureError(
            EXIT_REQUEST,
            "privateState keys changed: %r -> %r; a research branch adds or "
            "removes nothing" % (sorted(private_before), sorted(private_after)),
        )
    for name in sorted(set(private_before) | set(private_after)):
        if name in research_envelope.COUNTERS:
            continue
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; a research branch writes only the three "
                "counters" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST, "playerInfo changed; the research branches write none of it"
        )

    # --- the money: every stored resource must have moved by EXACTLY the derived
    # neutral vector under legacy's max(current + delta, 0).  For a research
    # command that is no movement at all; the value-level half of design D3's
    # post-execution proof, asserted here against the executed legacy server.
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
        "track": track,
        "vector_before": before_vector,
        "vector_after": after_vector,
        "derived": {key: value for key, value in derived.items() if key != "before"},
        "projection_after": projection,
        "changed_leaves": leaf_differences(before, after),
        "unaddressed_track_unchanged": True,
        "untouched_counters_unchanged": True,
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
        description="Capture the executed-legacy research fixture "
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
    content = measure_content_absence()

    # Fixtures are staged OUTSIDE the working tree and published only after
    # every check passed, so a failed run writes nothing into the repo.
    staging = Path(tempfile.mkdtemp(prefix="compat-research-capture-staging-"))
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

        def post_command(envelope: Dict[str, Any], cookie: str) -> Dict[str, Any]:
            """POST one crafted batch and return the in-process result."""
            return http_request(
                LEGACY_PORT,
                "POST",
                DYNAMIC_ROOT + "/command.php",
                form={
                    "USERID": pid,
                    "user_key": USER_KEY,
                    "language": LANGUAGE,
                    "data": research_envelope.data_field(envelope),
                },
                cookie=cookie,
                timeout=30.0,
            )

        # --- step 0: login (session cookie, save must stay identical) --------
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
                "Login form (USERID + GAMEVERSION) exactly as the thirteen "
                "delivered captures send it; recorded for session fidelity — "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- the eight branch-track steps -----------------------------------
        states: List[Dict[str, Any]] = [after_login]
        for index, planned in enumerate(STEP_PLAN):
            before_step = canonical_save(save_path)
            envelope = build_step_envelope(planned["track"], planned["action"])
            form = {
                "USERID": pid,
                "user_key": USER_KEY,
                "language": LANGUAGE,
                "data": research_envelope.data_field(envelope),
            }
            result = post_command(envelope, cookie)
            if result["status"] != 200:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s: expected HTTP 200, got %r"
                    % (planned["name"], result["status"]),
                )
            after_step = canonical_save(save_path)
            step_body = result.pop("body")
            command = research_envelope.ACTION_COMMANDS[planned["action"]]
            note = (
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly one command: "
                "%s against research track %d. The track index is the legacy "
                "`_type` the branch reads from %s and nothing else; no counter "
                "value, no research instant, and no cash amount is sent, and the "
                "resources_changed is the NEUTRAL vector because a research price "
                "would be a CLIENT-SENT delta (do_command applies it before the "
                "branch) and no research price is committed at all. The branch's "
                "recorded effect is ESTABLISHED; the request's exact shape is "
                "DERIVED and never observed from the Flash client. user_key is "
                "redacted in this record; accessToken is the crafted empty "
                "placeholder, never a token value."
                % (json.dumps([[0, command, envelope["commands"][0][2],
                                envelope["commands"][0][3]]]),
                   planned["track"],
                   "args[1]" if planned["action"] == research_envelope.CASH_ACTION
                   else "args[0]")
            )
            summaries.append(
                write_step(
                    staging, planned["name"], result, step_body, before_step,
                    after_step, form, note,
                )
            )
            facts = verify_transaction(
                before_step, after_step, planned["action"], planned["track"], envelope
            )
            if json.loads(step_body.decode("utf-8")) != {"result": "success"}:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s response is not the legacy {\"result\": \"success\"}: %r"
                    % (planned["name"], step_body),
                )
            transactions.append(facts)
            states.append(after_step)
            print(
                "capture:   %-42s track=%d vector=%r"
                % (planned["name"], planned["track"], facts["vector_after"])
            )
            del index

        # --- the byte-exact round trip ---------------------------------------
        first_before = states[0]
        last_after = states[-1]
        if save_bytes_sha(last_after) != save_bytes_sha(first_before):
            raise CaptureError(
                EXIT_REQUEST,
                "the eight steps were planned to round-trip the corpus's research "
                "vector back to its initial state, so the LAST step's after-state "
                "must equal the FIRST step's before-state byte-for-byte; it "
                "differs at %r"
                % (leaf_differences(first_before, last_after),),
            )

        # --- probe 1: the cash branch's own price argument is discarded ------
        probe1 = probe_envelope([[
            0, research_envelope.CASH_COMMAND, [250, 0], [0, 500, 0, 0, 0, 0, 0, 0],
        ]])
        before_probe1 = canonical_save(save_path)
        probe1_result = post_command(probe1, cookie)
        if probe1_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST, "probe 1: expected HTTP 200, got %r"
                % probe1_result["status"],
            )
        probe1_body = probe1_result.pop("body")
        after_probe1 = canonical_save(save_path)
        if json.loads(probe1_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1 response is not the legacy success result: %r"
                % (probe1_body,),
            )
        probe1_facts = {
            "vector_before": vector_of(before_probe1),
            "vector_after": vector_of(after_probe1),
            "cash_argument_sent": 250,
            "cash_before": before_probe1["playerInfo"]["cash"],
            "cash_after": after_probe1["playerInfo"]["cash"],
            "cash_moved": after_probe1["playerInfo"]["cash"]
            - before_probe1["playerInfo"]["cash"],
            "xp_before": before_probe1["maps"][0]["xp"],
            "xp_after": after_probe1["maps"][0]["xp"],
            "other_resources": {
                name: after_probe1["maps"][0].get(name)
                for name in ("gold", "wood", "oil", "steel")
            },
            "other_resources_unchanged": all(
                after_probe1["maps"][0].get(name)
                == before_probe1["maps"][0].get(name)
                for name in ("gold", "wood", "oil", "steel")
            ),
            "changed_top_level_map_keys": [
                field
                for field in sorted(set(before_probe1["maps"][0]) | set(after_probe1["maps"][0]))
                if after_probe1["maps"][0].get(field) != before_probe1["maps"][0].get(field)
            ],
            "leaf_differences": leaf_differences(before_probe1, after_probe1),
        }
        if probe1_facts["cash_moved"] != 0:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1 was handed cash=250 by the branch's own argument and "
                "playerInfo.cash moved by %r; the branch is supposed to DISCARD "
                "it, and a moved balance would mean the capture is recording a "
                "different branch" % (probe1_facts["cash_moved"],),
            )
        if probe1_facts["xp_after"] != probe1_facts["xp_before"] + 500:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1's client-sent experience slot did not move by its "
                "sent delta (%r -> %r); the client-sent-vector evidence this "
                "probe exists for would be missing"
                % (probe1_facts["xp_before"], probe1_facts["xp_after"]),
            )

        # --- probe 2: fast_forward really writes the instant -----------------
        stamp_envelope = probe_envelope(
            [[0, research_envelope.STEP_COMMAND, [0], FIXTURE_EXPECTED_VECTOR_SLOTS]]
        )
        stamp_result = post_command(stamp_envelope, cookie)
        if stamp_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST, "probe 2 stamp: expected HTTP 200, got %r"
                % stamp_result["status"],
            )
        stamp_result.pop("body")
        before_probe2 = canonical_save(save_path)
        forward = probe_envelope([[0, research_envelope.FAST_FORWARD_COMMAND, [60],
                                  FIXTURE_EXPECTED_VECTOR_SLOTS]])
        probe2_result = post_command(forward, cookie)
        if probe2_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST, "probe 2: expected HTTP 200, got %r"
                % probe2_result["status"],
            )
        probe2_body = probe2_result.pop("body")
        after_probe2 = canonical_save(save_path)
        probe2_facts = {
            "seconds_sent": 60,
            "instant_before": before_probe2["privateState"][
                research_envelope.KEY_INSTANT][0],
            "instant_after": after_probe2["privateState"][
                research_envelope.KEY_INSTANT][0],
            "step_before": before_probe2["privateState"][
                research_envelope.KEY_STEP][0],
            "step_after": after_probe2["privateState"][
                research_envelope.KEY_STEP][0],
            "item_before": before_probe2["privateState"][
                research_envelope.KEY_ITEM][0],
            "item_after": after_probe2["privateState"][research_envelope.KEY_ITEM][0],
            "other_track_instant_unchanged":
                after_probe2["privateState"][research_envelope.KEY_INSTANT][1]
                == before_probe2["privateState"][research_envelope.KEY_INSTANT][1],
        }
        expected_instant = max(
            0, probe2_facts["instant_before"] - 60
        )
        if probe2_facts["instant_after"] != expected_instant:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2: the research instant is %r after fast_forward(60) from "
                "%r, not the expected %r; the recorded fourth writer would be "
                "wrong" % (probe2_facts["instant_after"],
                           probe2_facts["instant_before"], expected_instant),
            )
        for key in ("step", "item"):
            if probe2_facts["%s_after" % key] != probe2_facts["%s_before" % key]:
                raise CaptureError(
                    EXIT_REQUEST,
                    "probe 2: fast_forward changed the %s counter; it writes only "
                    "the research instant" % key,
                )
        if not probe2_facts["other_track_instant_unchanged"]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2: fast_forward changed the UNADDRESSED track's instant, "
                "which it does not",
            )

        # --- probe 3: the clamp ---------------------------------------------
        before_probe3 = canonical_save(save_path)
        clamp = probe_envelope([[0, research_envelope.FAST_FORWARD_COMMAND,
                                [9999999999], FIXTURE_EXPECTED_VECTOR_SLOTS]])
        probe3_result = post_command(clamp, cookie)
        if probe3_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST, "probe 3: expected HTTP 200, got %r"
                % probe3_result["status"],
            )
        probe3_body = probe3_result.pop("body")
        after_probe3 = canonical_save(save_path)
        probe3_facts = {
            "seconds_sent": 9999999999,
            "instant_before": before_probe3["privateState"][
                research_envelope.KEY_INSTANT][0],
            "instant_after": after_probe3["privateState"][
                research_envelope.KEY_INSTANT][0],
            "clamped": after_probe3["privateState"][
                research_envelope.KEY_INSTANT][0] == 0,
            "step_unchanged": after_probe3["privateState"][
                research_envelope.KEY_STEP][0]
            == before_probe3["privateState"][research_envelope.KEY_STEP][0],
            "item_unchanged": after_probe3["privateState"][
                research_envelope.KEY_ITEM][0]
            == before_probe3["privateState"][research_envelope.KEY_ITEM][0],
        }
        if not probe3_facts["clamped"]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 3: the instant is %r after fast_forward(9999999999) from "
                "%r, not the clamped 0"
                % (probe3_facts["instant_after"], probe3_facts["instant_before"]),
            )
        for body_name, body_bytes in (("probe 2", probe2_body), ("probe 3", probe3_body)):
            if json.loads(body_bytes.decode("utf-8")) != {"result": "success"}:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s response is not the legacy success result: %r"
                    % (body_name, body_bytes),
                )

        probe_records: List[Dict[str, Any]] = []
        for record, facts in zip(PROBES, (probe1_facts, probe2_facts, probe3_facts)):
            merged = dict(record)
            merged.update(facts)
            probe_records.append(merged)
        for record in probe_records:
            print(
                "capture: probe %d: %s"
                % (record["probe"],
                   json.dumps({k: v for k, v in record.items()
                               if k not in PROBES[record["probe"] - 1]}, sort_keys=True))
            )

        # --- stop the server before any containment re-check ----------------
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

        resources_before = resources_of(first_before)
        resources_after = resources_of(last_after)
        manifest = {
            "schema": "godot-research/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for the four "
                "legacy research branches over BOTH tracks - eight branch-track "
                "combinations - against the committed corpus's own research "
                "counters; the executed-legacy parity oracle for the "
                "Compatibility API v0 research endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_research_fixture.py"
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
                "next_research_step": True,
                "research_buy_step_cash": True,
                "next_research_item": True,
                "reset_research_item": True,
                "both_tracks": True,
                "combinations": len(transactions),
                "combination_count_expected": research_envelope.CAPTURED_COMBINATIONS,
                "completion": False,
                "completion_captured": False,
                "completion_command_exists": False,
                "readiness_captured": False,
                "note": (
                    "ALL FOUR research branches were captured on BOTH tracks - "
                    "eight branch-track combinations - and NO COMPLETION AND NO "
                    "READINESS WERE CAPTURED, because the legacy server has "
                    "neither. researchStepNumber has 3 sites and researchItemNumber "
                    "2, every one of them a WRITE, and the single read of "
                    "timeStampDoResearch outside its own branches is "
                    "command.py:923 inside fast_forward, which is itself a write. "
                    "Nothing anywhere reads a research counter to decide anything, "
                    "so there is no server-side completion rule, no readiness "
                    "rule, no remaining-time computation, and no unlock gate to "
                    "reproduce. This fixture evidences the four counter "
                    "transitions ONLY"
                ),
                "no_server_side_completion": {
                    "research_step_sites": 3,
                    "research_step_sites_all_writes": True,
                    "research_item_sites": 2,
                    "research_item_sites_all_writes": True,
                    "research_instant_sites": 5,
                    "research_instant_writers": [
                        entry["source"] for entry in research_envelope.INSTANT_WRITERS
                    ],
                    "instant_writer_count": research_envelope.INSTANT_WRITER_COUNT,
                    "fast_forward_is_a_research_branch": False,
                    "fast_forward_seconds_client_supplied": True,
                    "research_completion_command": None,
                    "research_readiness_command": None,
                    "consequence": "a research track can be advanced and reset and "
                    "nothing server-side ever decides whether a step is ready; "
                    "this line refuses to invent a readiness rule the legacy server "
                    "does not have (design D1)",
                },
            },
            "target": {
                "counters": sorted(research_envelope.COUNTERS),
                "vector_before": FIXTURE_EXPECTED_VECTOR,
                "track_count": research_envelope.TRACK_COUNT,
                "placement_count": FIXTURE_EXPECTED_PLACEMENTS,
                "fabricated_state": False,
                "rows_carrying_a_research_counter": 0,
                "target_rule": TARGET_RULE,
            },
            "intent": {
                "track_sent": [planned["track"] for planned in STEP_PLAN],
                "track_rule": "the track index is the legacy `_type` the four "
                "branches read from args[0] - args[1] for the cash branch - and "
                "NOTHING else; no counter value, no research instant, and no cash "
                "amount is accepted from a client, and every extra key is ignored",
                "cash_rule": "the cash branch's own argument is the module's "
                "DERIVED_CASH = 0, server-derived and never client-supplied "
                "(design D2); the branch DISCARDS it (command.py:277), so no "
                "research price is claimed in either direction",
                "vector_rule": "NO research price is claimed or implemented "
                "(design D3): a research price would be a CLIENT-SENT delta, "
                "because do_command applies the request's per-command vector "
                "before the branch (command.py:40; engine.py:251-271) as "
                "max(current + delta, 0). The derived vector is NEUTRAL and the "
                "endpoint's second post-execution proof half requires every "
                "stored resource to be UNCHANGED",
                "derived": {
                    planned["action"]: {
                        "command": research_envelope.ACTION_COMMANDS[planned["action"]],
                        "args": (
                            [research_envelope.DERIVED_CASH, planned["track"]]
                            if planned["action"] == research_envelope.CASH_ACTION
                            else [planned["track"]]
                        ),
                        "resources_changed": FIXTURE_EXPECTED_VECTOR_SLOTS,
                    }
                    for planned in STEP_PLAN
                },
                "vector_is_neutral": True,
                "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                "envelope_keys": sorted(build_step_envelope(0, research_envelope.ACTION_STEP)),
                "commands_per_batch": 1,
            },
            "command_contract": [
                {
                    "command": record["command"],
                    "action": record["action"],
                    "source": record["source"],
                    "args": record["args"],
                    "argument_order": record["argument_order"],
                    "counters_written": record["counters_written"],
                    "effect": record["effect"],
                    "stamps_instant": record["stamps_instant"],
                    "paired_reset": record["paired_reset"],
                    "reads_a_price": record["reads_a_price"],
                    "charges": record["charges"],
                    "validation": record["validation"],
                }
                for record in research_envelope.BRANCHES
            ],
            "branch_count": len(research_envelope.BRANCHES),
            "instant_writers": [
                dict(entry) for entry in research_envelope.INSTANT_WRITERS
            ],
            "instant_writer_count": research_envelope.INSTANT_WRITER_COUNT,
            "fast_forward": {
                "recorded": True,
                "implemented": False,
                "command": research_envelope.FAST_FORWARD_COMMAND,
                "source": "command.py:905-946, research lines 922-928",
                "read_line": "command.py:923",
                "write_line": "command.py:927",
                "seconds_source": "args[0], CLIENT-SUPPLIED (command.py:906)",
                "formula": "research_timers[i] = max(0, research_timers[i] - seconds)",
                "clamped": True,
                "is_a_research_branch": False,
                "endpoint_action": "none: no action derives fast_forward, no route "
                "exists for it, and no elapsed-time rule is derived from the "
                "instant anywhere (design D7)",
                "contract": research_envelope.FAST_FORWARD_CONTRACT,
            },
            "tracks": [dict(record) for record in research_envelope.TRACKS],
            "track_note": research_envelope.TRACK_RECORD_NOTE,
            "refusals": [
                {"refusal": record["refusal"],
                 "implemented": record["implemented"],
                 "reason": record["reason"]}
                for record in research_envelope.REFUSALS
            ],
            "content": content,
            "probes": probe_records,
            "transactions": transactions,
            "transaction": {
                "count": len(summaries),
                "command_steps": len(transactions),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "placement_count_before": len(first_before["maps"][0][ITEMS_FIELD]),
                "placement_count_after": len(last_after["maps"][0][ITEMS_FIELD]),
                "rows_carrying_a_research_counter": 0,
                "rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "private_state_outside_the_counters_unchanged": True,
                "player_info_unchanged": True,
                "unaddressed_track_unchanged": True,
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "round_trip_to_seed": True,
                "round_trip_note": "the eight steps were planned so the LAST step "
                "restores all three counters to [0, 0], and the harness asserts "
                "that this step's after-state is the FIRST step's before-state "
                "byte-for-byte - the strongest round-trip statement this set of "
                "transitions can make",
                "transition_visibility": {
                    "rule": "EIGHT steps cover four branches over two tracks "
                    "exactly, which leaves no room for an extra priming step. The "
                    "consequence is recorded here rather than left for a reader "
                    "to find: the ONLY recorded transition that is not a "
                    "from-value-to-different-value move is the ITEM branch's "
                    "INSTANT half. The captured order is step, step, cash, cash, "
                    "item, item, reset, reset, so the two cash steps have already "
                    "ZEROED both instants before the item steps run; the item "
                    "branch therefore shows its item half (0 -> 1) and its step "
                    "half (1 -> 0) as real transitions while its instant half is "
                    "0 -> 0. The pairing itself is still established - the branch "
                    "writes all three keys at command.py:287-289 with no branch "
                    "between them, and the recorded leaf diff names exactly the "
                    "three pointers it touches",
                    "item_step_instant_was_already_zero": True,
                    "item_step_observable_leaves": [
                        "/privateState/researchItemNumber/%d"
                        % planned["track"]
                        for planned in STEP_PLAN
                        if planned["action"] == research_envelope.ACTION_ITEM
                    ] + [
                        "/privateState/researchStepNumber/%d" % planned["track"]
                        for planned in STEP_PLAN
                        if planned["action"] == research_envelope.ACTION_ITEM
                    ],
                    "every_other_transition_observable": True,
                    "what_is_still_established": "the four branch EFFECTS and "
                    "their committed source lines are established by the capture "
                    "and by the hermetic suite's own read of command.py; the one "
                    "recorded no-op half is an artefact of needing exactly eight "
                    "steps, not evidence that the branch skips the write",
                },
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) on the RESOURCE "
                "vector only bites when a delta would drive a balance below zero; "
                "the derived vector is the NEUTRAL all-zero vector, so no balance "
                "moves at all and that clamp is never exercised by this fixture. "
                "That the vector really is client-sent is established by probe 1 "
                "above. The research INSTANT's own max(0, …) clamp inside "
                "fast_forward IS exercised, by probes 2 and 3",
                "reward_paid": False,
                "reward_note": "NO reward is paid and none exists: there is no "
                "committed reward for research anywhere in the content, not even a "
                "zero-valued one, so none is invented (design D4)",
                "price_computed": False,
                "price_note": "NO price is computed anywhere and NO stored resource "
                "moves: research_buy_step_cash reads a cash value and discards it, "
                "which probe 1 demonstrates against the live server",
                "readiness_computed": False,
                "readiness_note": "NO readiness, remaining time, progress ratio, "
                "completion fraction, or derived step count is computed anywhere "
                "in this contract, because the legacy server evaluates no research "
                "counter's elapsed time and has no consumer for one (design D1)",
                "counter_bound_applied": False,
                "counter_bound_note": "NO maximum, clamp, or membership rule is "
                "applied to any research counter: the four branches have none, and "
                "a bound they do not have would be an invented rule (design D6). "
                "Authoritative validation belongs to Server v1 / M13",
                "counter_writes": [
                    "engine.apply_resources applies the derived NEUTRAL vector on "
                    "the single command with max(..., 0) per resource, BEFORE the "
                    "branch (command.py:40; engine.py:251-271)",
                    "command.next_research_step increments the addressed track's "
                    "researchStepNumber and stamps its timeStampDoResearch with "
                    "time_now (command.py:268-274) — nothing else",
                    "command.research_buy_step_cash ZEROES the addressed track's "
                    "timeStampDoResearch and nothing else, reading and discarding "
                    "args[0] as `cash` (command.py:276-282)",
                    "command.next_research_item increments the addressed track's "
                    "researchItemNumber and RESETS its researchStepNumber AND its "
                    "timeStampDoResearch TOGETHER (command.py:284-291) — the "
                    "paired reset, which no other branch performs",
                    "command.reset_research_item sets all THREE of the addressed "
                    "track's counters to 0 (command.py:293-300) — nothing else",
                    "command.fast_forward subtracts a CLIENT-SUPPLIED number of "
                    "seconds from EVERY track's timeStampDoResearch, clamped at "
                    "zero (command.py:922-928) — the recorded fourth writer, "
                    "offered by no action and no route",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE carries exactly ONE time-dependent VALUE, "
                    "the research instant the step branch stamps: it appears in "
                    "the two step steps' after.json and in the two cash steps' "
                    "before.json, because the cash branch zeroes the very instant "
                    "the step branch had stamped. The claim is machine-checkable: "
                    "a leaf-level diff of two consecutive runs must differ at "
                    "exactly these paths and nowhere else"
                ),
                "state_leaves": [
                    "/privateState/%s/%d in steps/command_next_research_step_"
                    "track_0/after.json (and therefore that whole document's "
                    "serialization, because the digest covers the payload)"
                    % (research_envelope.KEY_INSTANT, 0),
                    "/privateState/%s/%d in steps/command_next_research_step_"
                    "track_1/after.json"
                    % (research_envelope.KEY_INSTANT, 1),
                    "/privateState/%s/%d in steps/command_research_buy_step_cash_"
                    "track_0/before.json"
                    % (research_envelope.KEY_INSTANT, 0),
                    "/privateState/%s/%d in steps/command_research_buy_step_cash_"
                    "track_1/before.json"
                    % (research_envelope.KEY_INSTANT, 1),
                ],
                "stable_state_leaves": [
                    "steps/login_post/before.json and after.json are both "
                    "byte-stable and identical to each other",
                    "every before.json from the cash step onwards is byte-stable, "
                    "because the cash branch has already zeroed both instants",
                    "every after.json from the item step onwards is byte-stable, "
                    "because the item branch zeroes both instants as part of its "
                    "PAIRED reset",
                    "steps/command_reset_research_item_track_1/after.json is "
                    "byte-stable AND equal to steps/command_next_research_step_"
                    "track_0/before.json, because the eight steps round-trip",
                ],
                "leaves": [
                    "/captured_at_utc in each steps/<name>/request.json",
                    "/captured_at_utc in each steps/<name>/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in each steps/<name>/response.meta.json",
                    "the envelope ts inside each command step's request.json "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                ],
                "stable_by_derivation": (
                    "the eight derived vectors, the derived neutral vectors, every "
                    "placement, and all seven stored resources are byte-stable "
                    "because the derivation is fixed and no resource moves. Only "
                    "the wall-clock instant the step branch stamps is not "
                    "derivable, and it is compared by SHAPE (a strict integer, not "
                    "earlier than the pre-execution one) rather than by value"
                ),
                "documented_normalization": (
                    "research parity applies NO clock normalization: the derived "
                    "counters are compared by value, the unaddressed track and "
                    "every untouched counter are compared by value, and every "
                    "stored resource is compared by value (exactly unchanged, "
                    "because the derived vector is neutral). The ONLY comparison "
                    "that is not by value is the stamped instant, which is checked "
                    "for being a strict integer and for NOT moving backwards: "
                    "engine.timestamp_now has one-second resolution, so two "
                    "commands inside one second legitimately stamp the same value "
                    "and a 'strictly later' rule would refuse a correct transaction"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, construction, "
                    "collect, expand, level, queue, and collection fixtures are "
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
                "capture:   %-46s %s %s -> %d (%d bytes, save unchanged: %s)"
                % (
                    summary["name"],
                    summary["method"],
                    summary["target"],
                    summary["status"],
                    summary["response_bytes"],
                    summary["save_unchanged_by_call"],
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
        print("capture: eight branch-track steps round-tripped to the seed: %s"
              % (save_bytes_sha(last_after) == save_bytes_sha(first_before),))
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except research_envelope.EnvelopeError as error:
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
