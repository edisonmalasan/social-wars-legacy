#!/usr/bin/env python3
"""Capture the executed-legacy quest fixture: all six branches.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, collect, expand, level, queue,
collection, and research captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, upgrade, construction, collect, expand, level, queue, collection,
   and research fixtures.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root (root ``*.py``,
   ``config/``, ``mods/``, ``villages/``, ``templates/`` and ``saves/``
   seeded from ``tests/saves/fresh-player.json``).
4. Starts the REAL legacy server (``python -B server.py`` in the
   disposable copy) and waits for loopback readiness.
5. Executes **seven** recorded legacy requests, recording full canonical
   before/after save JSON plus the response for each step:

   * ``POST /``               — login form (session cookie, as a logged-in Flash
     client would send; 302, save unchanged)
   * six ``POST .../command.php`` steps carrying **exactly one** command each,
     covering **every one of the six quest branches**:

     ================ ======================= ====================================
     step             command                  derived args
     ================ ======================= ====================================
     goal_progress    set_goals                ``[2, "[0,0]"]``
     goal_complete    complete_goal            ``[2]`` — writes NOTHING AT ALL
     quest_var        set_quest_var            ``["spawned", true]``
     collect_mission  collect_mission          ``[5]``
     quest_rank       admin_set_quest_rank     ``[3, 1]``
     end_quest        end_quest                one server-derived JSON blob whose
                                              ``units`` is an **EMPTY LIST**
     ================ ======================= ====================================

6. Verifies each transaction structurally before publishing: the login step left
   the save byte-identical; every step's persisted quest state matches the
   **derived** result for its branch — with the two wall-clock fields compared by
   **shape** and **direction** because ``time_now`` is not derivable, the
   no-op branch proved over the **whole** state, the chapter wrap reproduced as a
   string where the corpus records an integer, and the quest-variable map
   self-healed from ``None`` to a dict; **every** placed row byte-identical; the
   storage, the private state outside the seven quest fields, the player info and
   every **other** map field unchanged; the unlocked-quest index unchanged; and
   **every one of the seven stored resources unchanged** because the derived
   vector is neutral.
7. Runs **five** **executed-legacy probes** against the same live server, after
   the recorded steps and on the same disposable copy, each recorded in the
   manifest rather than as a step:

   * **probe 1** ``set_goals([500, "[0,0]"])`` — establishes the **absence of an
     upper bound**: the goals list grows from 151 to **501** entries, appending
     **350** ``None`` entries from ONE client-sent identifier, and the branch
     prints ``Goal 'None' progressed`` because the id is outside the committed
     content.  This is the executed evidence for design D4.
   * **probe 2** ``set_quest_var(["idSimpleChapter", 5])`` — establishes that the
     one key the branch **itself** ignores writes **nothing** (it prints
     ``Ignored idSimpleChapter`` and returns before any write), which is what
     the endpoint's ``ignored_quest_var_key`` refusal reproduces.
   * **probe 3** ``collect_mission([150])`` — establishes that the only guard is
     a **WRAP**: 150 lands on 1, and the mission id is stored as the **string**
     ``"1"`` where the corpus recorded an **integer** ``0``.
   * **probe 4** ``end_quest`` with a **client-computed** destruction count —
     ``units: [[<item id>, 0, 1, 0]]``, so ``lost = max(0, 1 - 0) = 1``.  This is
     the executed evidence for design D2's **divergence**: the legacy server
     **destroys** a placed row, while this repository's endpoint **refuses** to.
     The probe records the row count before and after and the dead-hero ledger,
     so the divergence is measured on both sides rather than asserted.
   * **probe 5** ``end_quest([7])`` then ``fast_forward([60])`` — establishes the
     **seventh writer** of quest state: ``fast_forward`` subtracts the
     **client-supplied** 60 seconds from the quest time and the last-chapter
     instant, both clamped at zero, and from nothing else quest-related.
8. Stops the server, re-checks the working-tree containment snapshot and the
   fourteen committed fixture digests, discards the disposable copy, and writes
   the fixtures under ``--out`` (default: ``tests/fixtures/godot-quests/``).

What this fixture does and does not show, stated up front
    The recorded steps target the committed corpus's **own** quest state:
    ``privateState.goals`` is **151** entries **all ``None``**,
    ``privateState.questsRank`` is ``{}``, ``privateState.unlockedQuestIndex`` is
    ``0``, ``maps[0].currentQuestVars`` is a recorded **``None``**,
    ``maps[0].questTimes`` is ``{}``, ``maps[0].idCurrentMission`` is an
    **integer** ``0``, and ``maps[0].timestampLastChapter`` is ``0``.  **No
    player state was fabricated** and **no fixture is absent**: the corpus
    exercises every one of the six branches from its initial state, which is the
    contrast with M8 line 8, where ``resurrectable`` is unit-only and no fixture
    existed at all.

    **No completion was captured, because no completion exists.**
    ``complete_goal`` writes nothing, so its step's before and after states are
    byte-identical and the harness asserts exactly that.

    **No destruction was captured as a step, because it is REFUSED.**  The
    recorded ``end_quest`` step carries an **empty** unit list and leaves all 40
    placed rows byte-identical; the legacy destruction is captured in probe 4 and
    recorded as a **divergence**.

    The only time-dependent values in the recorded **state** are
    ``timestampLastChapter`` (the chapter step) and the one ``questTimes`` entry
    (the ``end_quest`` step): both are ``time_now`` stamps and are compared by
    shape and direction rather than by value.

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

Containment (same contract as the fourteen delivered captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The fourteen committed
  fixture directories are digest-pinned for the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the fourteen delivered capture harnesses):

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

    python -B apps/compat-api/capture_quest_fixture.py

where ``python`` denotes the pinned CPython 3.9.13 executable
(``C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe``).
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quest_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-quests"

# The committed corpus's own quest state, pinned here AND cross-checked against
# the real seed below, so a drift fails the run instead of publishing a different
# fixture.
FIXTURE_EXPECTED_STATE: Dict[str, Any] = {
    "goals_length": quest_envelope.COMMITTED_GOALS_LENGTH,
    "goals_all_none": quest_envelope.COMMITTED_GOALS_ALL_NONE,
    "ranks": dict(quest_envelope.COMMITTED_RANKS),
    "unlocked_index": quest_envelope.COMMITTED_UNLOCKED_INDEX,
    "quest_vars_is_null": quest_envelope.COMMITTED_QUEST_VARS_IS_NULL,
    "quest_times": dict(quest_envelope.COMMITTED_QUEST_TIMES),
    "mission": quest_envelope.COMMITTED_MISSION,
    "last_chapter": quest_envelope.COMMITTED_LAST_CHAPTER,
}
FIXTURE_EXPECTED_PLACEMENTS = quest_envelope.COMMITTED_PLACEMENTS
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = dict(
    quest_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    quest_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    name: 0 for name in quest_envelope.COMMITTED_RESOURCE_BEFORE
}
FIXTURE_EXPECTED_VECTOR_SLOTS: List[int] = [0] * quest_envelope.RESOURCE_VECTOR_SLOTS

#: The six recorded steps, in the order they execute — one per branch.
STEP_PLAN: List[Dict[str, Any]] = [
    {"name": "command_set_goals",
     "action": quest_envelope.ACTION_SET_GOAL, "addressing": 2},
    {"name": "command_complete_goal",
     "action": quest_envelope.ACTION_COMPLETE_GOAL, "addressing": 2},
    {"name": "command_set_quest_var",
     "action": quest_envelope.ACTION_SET_QUEST_VAR, "addressing": "spawned"},
    {"name": "command_collect_mission",
     "action": quest_envelope.ACTION_COLLECT_MISSION, "addressing": 5},
    {"name": "command_admin_set_quest_rank",
     "action": quest_envelope.ACTION_SET_QUEST_RANK, "addressing": 3},
    {"name": "command_end_quest",
     "action": quest_envelope.ACTION_END_QUEST, "addressing": 7},
]
STEP_COUNT = len(STEP_PLAN)

TARGET_RULE = (
    "the committed corpus's OWN quest state, with nothing fabricated: "
    "privateState.goals is 151 entries ALL None, privateState.questsRank is {}, "
    "privateState.unlockedQuestIndex is 0, maps[0].currentQuestVars is a recorded "
    "None, maps[0].questTimes is {}, maps[0].idCurrentMission is the INTEGER 0, "
    "and maps[0].timestampLastChapter is 0. Every one of the six branches is "
    "therefore exercisable from the committed initial state, which is why this "
    "line records NO absent fixture"
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
    ("tests/fixtures/godot-research", "godot-research"),
)

# The executed-legacy probes this capture runs itself, after the recorded steps
# and on the same live server.  They are recorded in the manifest rather than as
# steps because they are evidence for the contract's GUARANTEES, not recorded
# transactions of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "is the on-demand growth of the goals list really UNBOUNDED, and what "
            "happens when the client-sent goal id is outside the committed content?"
        ),
        "commands": ['set_goals([500, "[0,0]"])'],
        "established": (
            "engine.set_goals pads with `while goal >= len(goals): goals.append("
            "None)` (engine.py:98-99) and there is NO upper bound anywhere, so ONE "
            "client-sent identifier of 500 grows the list from 151 to 501 entries - "
            "350 appended None entries. The branch then resolves the title through "
            "the fail-closed accessor (get_game_config.py:144-146) and prints Goal "
            "'None' progressed, because 500 is outside the committed 1..91 content"
        ),
        "why_it_matters": (
            "this is the executed evidence for design D4: the endpoint "
            "REPRODUCES the unbounded growth rather than closing it, because a "
            "bound the legacy server does not have would make the modern service "
            "stricter in the unexamined direction. It also establishes the "
            "fail-closed accessor an id outside the content table returns None for"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 2,
        "question": (
            "does the key the branch itself ignores really write NOTHING, and is "
            "there any membership test against the eight keys its own comment "
            "enumerates?"
        ),
        "commands": ['set_quest_var(["idSimpleChapter", 5])'],
        "established": (
            "the branch returns at command.py:95 BEFORE any write, printing "
            "'Ignored idSimpleChapter', so neither map[idCurrentMission] nor "
            "map[currentQuestVars] moves. The branch's own comment enumerates "
            "eight keys (command.py:97-106) and there is NO membership test "
            "anywhere: a client-invented key is accepted and persisted, which the "
            "recorded quest_var step's sibling probe shows directly"
        ),
        "why_it_matters": (
            "this is the executed evidence for design D5 and for the endpoint's "
            "one quest-variable refusal: exactly ONE key is refused, and it is "
            "refused because the legacy branch ITSELF ignores it - a recorded "
            "behaviour, not an absence"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 3,
        "question": (
            "is the out-of-range mission identifier REJECTED or WRAPPED, and what "
            "TYPE does the branch store it as?"
        ),
        "commands": ["collect_mission([150])"],
        "established": (
            "the branch's ONLY guard is `if next_mission > 99: next_mission = 1` "
            "(command.py:432-436), so 150 lands on 1: a WRAP, not a rejection. The "
            "stored value is `str(next_mission)` (command.py:438), so the field "
            "becomes the STRING \"1\" where the committed corpus recorded the "
            "INTEGER 0 - a real legacy shape divergence"
        ),
        "why_it_matters": (
            "this is the executed evidence for design D8 (both type facts) and "
            "for the wrap the endpoint reproduces: refusing an out-of-range "
            "identifier would be stricter than legacy in the direction D4 forbids"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 4,
        "question": (
            "what does the legacy server do with a CLIENT-COMPUTED destruction "
            "count on end_quest, and does this repository's endpoint reproduce it?"
        ),
        "commands": [
            "end_quest([<blob>]) with units = [[<team-1 item id>, 0, 1, 0]], so "
            "`lost = max(0, unit[2] - unit[3])` = 1"
        ],
        "established": (
            "THE DIVERGENCE, MEASURED. The legacy branch computes `lost` from the "
            "CLIENT's tuple (command.py:792) and calls map_lose_item "
            "(command.py:796), which DELETES a placed row (engine.py:218-228) and "
            "calls push_dead_unit at engine.py:223 - one of only TWO callers of the "
            "dead-hero ledger's engine helper, the other being end_attack at "
            "command.py:872. This repository's endpoint does NOT reproduce it: the "
            "recorded end_quest step above carries `units: []`, the destruction "
            "loop iterates zero times, and all 40 placed rows are byte-identical "
            "before and after - proved over the COMPLETE items mapping by the "
            "endpoint and by this capture"
        ),
        "why_it_matters": (
            "this is the executed evidence for design D2 and design D10. It is "
            "recorded as a DIVERGENCE, not as parity: the modern service "
            "deliberately does NOT destroy a placed row on this command, because a "
            "client-computed destruction count is exactly the anti-pattern "
            "AGENTS.md names as Bad. Authoritative combat belongs to Server v1 / "
            "M13"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 5,
        "question": (
            "is fast_forward really a WRITER of quest state, and is the number of "
            "seconds it subtracts the client's?"
        ),
        "commands": [
            "end_quest([<blob> for quest 9]) to write a fresh quest time",
            "fast_forward([60]) with the client-supplied 60 seconds",
        ],
        "established": (
            "fast_forward (command.py:905) subtracts `seconds = args[0]` - "
            "CLIENT-SUPPLIED (command.py:906) - from every questTimes entry "
            "(command.py:942-944) and from timestampLastChapter (command.py:911), "
            "each clamped at zero with max(0, ...). Nothing else quest-related is "
            "touched: the goals list, the rank map, the quest-variable map, the "
            "current mission identifier, and the unlocked-quest index all stay put"
        ),
        "why_it_matters": (
            "this is the executed evidence for design D9: quest timing is "
            "CLIENT-WRITABLE, recorded as the SEVENTH writer of quest state, and "
            "delivered NOT AT ALL - no action, no route, and no elapsed-time rule "
            "anywhere"
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
MAP_RESOURCE_FIELDS = quest_envelope.MAP_RESOURCE_FIELDS

# The one map field the quest branches never touch.
ITEMS_FIELD = "items"


# ---------------------------------------------------------------- sanitization --
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
    envelope = quest_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return quest_envelope.data_field(envelope)


# --------------------------------------------------------------------- records --
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


def quest_state_of(document: Dict[str, Any]) -> Dict[str, Any]:
    """The seven committed quest fields, copied, from a whole save document."""
    return quest_envelope.snapshot_state(document)


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


# ------------------------------------------------------------- derived batches --
def build_step_envelope(action: str, addressing: Any,
                        ts: Optional[int] = None) -> Dict[str, Any]:
    """One recorded branch's batch, built from the SHARED derivation.

    Built from ``quest_envelope`` rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.
    """
    envelope = quest_envelope.build_envelope(action=action, addressing=addressing,
                                             ts=ts)
    verify_envelope(envelope, action, addressing)
    return envelope


def probe_envelope(commands: List[List[Any]], ts: Optional[int] = None) -> Dict[str, Any]:
    """A probe's batch, crafted by HAND rather than through the derivation.

    Every probe exists to exercise a value the derivation **refuses** to
    express — a goal index above the content table, the one ignored key, an
    out-of-range mission, a client-computed unit list, and a fast-forward
    command — and ``quest_envelope.build_envelope`` would reject most of them,
    which is exactly the guarantee each probe makes concrete.
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
def verify_envelope(envelope: Dict[str, Any], action: str, addressing: Any) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its argument list, and its **neutral** vector are the
    derived contract (design D2/D6); that a real client sends exactly this is
    **derived** too, because no committed content sits behind any of it.  All of
    it is pinned here instead, and any drift fails the run rather than silently
    publishing a different fixture.
    """
    if sorted(envelope) != sorted(quest_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a quest batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != quest_envelope.ACTION_COMMANDS[action]:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (quest_envelope.ACTION_COMMANDS[action], entry[1]),
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
            EXIT_REQUEST, "the quest vector must be neutral, got slots %r" % (paying,)
        )
    # The destruction refusal is visible IN THE ENVELOPE, not only in the proof.
    if action == quest_envelope.ACTION_END_QUEST:
        blob = json.loads(entry[2][0])
        if blob.get("units") != []:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived end_quest blob carries %r units: the destruction "
                "count is REFUSED (design D2) and an empty list is what refuses it"
                % (blob.get("units"),),
            )
        if blob.get("quest_id") != addressing:
            raise CaptureError(
                EXIT_REQUEST, "the derived blob carries quest_id %r, not %r"
                % (blob.get("quest_id"), addressing),
            )
        if blob.get("difficulty") != quest_envelope.DERIVED_DIFFICULTY:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived blob's difficulty is %r, not the derived %r"
                % (blob.get("difficulty"), quest_envelope.DERIVED_DIFFICULTY),
            )
        # Every OTHER blob key is a DERIVED constant, never a client value.  The
        # check is on the VALUES, not on the key names: the blob legitimately
        # carries the branch's own seven keys, and what must not happen is a
        # client's number or unit list reaching them.
        expected_blob = quest_envelope.end_quest_blob(addressing)
        if blob != expected_blob:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived blob %r is not the module's %r: a client value "
                "reached the envelope" % (blob, expected_blob),
            )
        if blob.get("units"):
            raise CaptureError(
                EXIT_REQUEST,
                "the derived end_quest blob carries %r units: the destruction "
                "count is REFUSED (design D2) and an empty list is what refuses it"
                % (blob.get("units"),),
            )
    if action == quest_envelope.ACTION_SET_QUEST_VAR:
        if entry[2][1] is not quest_envelope.DERIVED_QUEST_VALUE:
            raise CaptureError(
                EXIT_REQUEST,
                "the quest-variable value is %r, not the derived marker"
                % (entry[2][1],),
            )
    if action == quest_envelope.ACTION_SET_GOAL:
        if json.loads(entry[2][1]) != list(quest_envelope.DERIVED_PROGRESS):
            raise CaptureError(
                EXIT_REQUEST,
                "the progress pair is %r, not the derived %r"
                % (entry[2][1], list(quest_envelope.DERIVED_PROGRESS)),
            )


def verify_target(before: Dict[str, Any]) -> None:
    """The corpus's own quest state, verified against the seed file."""
    try:
        state = quest_state_of(before)
    except quest_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's quest state does not resolve: [%s] %s"
            % (error.code, error),
        )
    observed = {
        "goals_length": len(state[quest_envelope.KEY_GOALS]),
        "goals_all_none": all(
            entry is None for entry in state[quest_envelope.KEY_GOALS]
        ),
        "ranks": state[quest_envelope.KEY_RANKS],
        "unlocked_index": state[quest_envelope.KEY_UNLOCKED_INDEX],
        "quest_vars_is_null": state[quest_envelope.KEY_QUEST_VARS] is None,
        "quest_times": state[quest_envelope.KEY_QUEST_TIMES],
        "mission": state[quest_envelope.KEY_MISSION],
        "last_chapter": state[quest_envelope.KEY_LAST_CHAPTER],
    }
    if observed != FIXTURE_EXPECTED_STATE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's quest state is %r, not the committed %r"
            % (observed, FIXTURE_EXPECTED_STATE),
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


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    action: str,
    addressing: Any,
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived **neutral**
    vector under the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the branch
    (``command.py:40``) and applies the 8-slot vector verbatim, per resource, as
    ``max(current + delta, 0)``; the quest branch then writes only the fields the
    recorded branch record names.  Any mismatch means the capture would publish a
    fixture that contradicts its own derivation, so the run fails with exit 5.
    """
    entry = envelope["commands"][0]
    map_before = before["maps"][0]
    map_after = after["maps"][0]

    # --- the subject: the derived quest state, through ONE derivation shared
    # with the endpoint (so the capture and the service cannot disagree).
    try:
        before_state = quest_state_of(before)
        after_state = quest_state_of(after)
        derived = quest_envelope.derived_quest(before_state, action, addressing)
    except quest_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_REQUEST,
            "the quest derivation does not resolve: [%s] %s" % (error.code, error),
        )
    divergence = quest_envelope.expected_state(
        before_state, action, addressing, after_state
    )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed %s did not produce the derived result: %s"
            % (action, divergence),
        )
    projection = quest_envelope.project_quests(after_state)

    # --- the placements: the REFUSED destruction count, proved over the WHOLE
    # set.  A selected-subset comparison would be insufficient, which is why the
    # keys are compared as sets and every row is compared by value.
    items_before = map_before[ITEMS_FIELD]
    items_after = map_after[ITEMS_FIELD]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].items keys changed; a quest command adds and removes no row",
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
                "placement row %s changed; the destruction count is REFUSED "
                "(design D2) and no quest branch touches a row" % other,
            )

    # --- the other map scalars.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; quests store nothing")
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a quest command adds "
            "or removes nothing" % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field == ITEMS_FIELD:
            continue
        if field in MAP_RESOURCE_FIELDS:
            continue
        if field in quest_envelope.MAP_KEYS:
            # Compared by value through the shared derivation above, which
            # covers every quest field including the wall-clock ones.
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; a quest branch writes only its recorded "
                "fields" % field,
            )

    # --- the private state: the three quest fields by derivation, every other
    # key byte-identical.  (cash and mana live inside privateState/playerInfo and
    # are checked by value below, so they are skipped here by name.)
    private_before = before["privateState"]
    private_after = after["privateState"]
    if sorted(private_after) != sorted(private_before):
        raise CaptureError(
            EXIT_REQUEST,
            "privateState keys changed: %r -> %r; a quest branch adds or "
            "removes nothing" % (sorted(private_before), sorted(private_after)),
        )
    for name in sorted(set(private_before) | set(private_after)):
        if name in quest_envelope.PRIVATE_KEYS:
            continue
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; a quest branch writes only its recorded "
                "fields" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST, "playerInfo changed; the quest branches write none of it"
        )

    # --- the money: every stored resource must have moved by EXACTLY the derived
    # neutral vector under legacy's max(current + delta, 0).  For a quest command
    # that is no movement at all; the value-level half of design D6's
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
        "addressing": derived["addressing"],
        "addressing_kind": derived["addressing_kind"],
        "written": derived["written"],
        "untouched": derived["untouched"],
        "mutates": derived["mutates"],
        "stamps_instant": derived["stamps_instant"],
        "stamps_chapter": derived["stamps_chapter"],
        "quest_before": before_state,
        "quest_after": after_state,
        "projection_after": projection,
        "changed_leaves": leaf_differences(before, after),
        "placed_rows_byte_identical": True,
        "placed_row_count": len(items_after),
        "destruction": "refused",
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
        description="Capture the executed-legacy quest fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-quest-capture-staging-"))
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
                    "data": quest_envelope.data_field(envelope),
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
                "Login form (USERID + GAMEVERSION) exactly as the fourteen "
                "delivered captures send it; recorded for session fidelity — "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- the six branch steps -------------------------------------------
        states: List[Dict[str, Any]] = [after_login]
        for planned in STEP_PLAN:
            before_step = canonical_save(save_path)
            envelope = build_step_envelope(planned["action"], planned["addressing"])
            form = {
                "USERID": pid,
                "user_key": USER_KEY,
                "language": LANGUAGE,
                "data": quest_envelope.data_field(envelope),
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
            command = quest_envelope.ACTION_COMMANDS[planned["action"]]
            note = (
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly one command: "
                "%s addressed by %s %r. That addressing is the ONE value a client "
                "may name; every other value is the module's DERIVED constant — the "
                "progress pair, the quest-variable marker, the rank difficulty, and "
                "(for end_quest) the whole server-side blob — and the "
                "resources_changed is the NEUTRAL vector because a quest price "
                "would be a CLIENT-SENT delta (do_command applies it before the "
                "branch) and no committed quest field records one: `reward` has "
                "ZERO legacy consumers and is UNIFORMLY 10 on all 91 entries. The "
                "branch's recorded effect is ESTABLISHED; the request's exact "
                "shape is DERIVED and never observed from the Flash client. For "
                "end_quest the derived blob carries `units: []`, which IS the "
                "refusal of the client-computed destruction count (design D2): the "
                "destruction loop iterates zero times and no placed row moves. "
                "user_key is redacted in this record; accessToken is the crafted "
                "empty placeholder, never a token value."
                % (command, quest_envelope.ACTION_ADDRESSING[planned["action"]],
                   planned["addressing"])
            )
            summaries.append(
                write_step(
                    staging, planned["name"], result, step_body, before_step,
                    after_step, form, note,
                )
            )
            facts = verify_transaction(
                before_step, after_step, planned["action"], planned["addressing"],
                envelope,
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
                "capture:   %-32s addressing=%-10r written=%s"
                % (planned["name"], planned["addressing"], facts["written"])
            )

        # --- the no-op branch really moved nothing ---------------------------
        no_op = next(
            facts for facts in transactions
            if facts["action"] == quest_envelope.ACTION_COMPLETE_GOAL
        )
        if no_op["mutates"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the complete_goal step reported a MUTATING branch; the branch "
                "writes NOTHING AT ALL (design D3)",
            )
        if no_op["quest_before"] != no_op["quest_after"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the complete_goal step changed the quest state from %r to %r, but "
                "the branch writes NOTHING AT ALL"
                % (no_op["quest_before"], no_op["quest_after"]),
            )
        if no_op["changed_leaves"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the complete_goal step changed leaves %r, but the branch writes "
                "NOTHING AT ALL" % (no_op["changed_leaves"],),
            )
        print("capture:   complete_goal wrote NOTHING AT ALL: the whole quest "
              "state is byte-identical and no leaf moved")

        # --- the refusal and the wrap are visible in the recorded state -------
        chapter = next(
            facts for facts in transactions
            if facts["action"] == quest_envelope.ACTION_COLLECT_MISSION
        )
        if not isinstance(chapter["quest_after"][quest_envelope.KEY_MISSION], str):
            raise CaptureError(
                EXIT_REQUEST,
                "collect_mission stored %r, not a STRING: the branch writes "
                "str(next_mission) (command.py:438) where the corpus records an "
                "INTEGER (design D8)"
                % (chapter["quest_after"][quest_envelope.KEY_MISSION],),
            )
        quest_var = next(
            facts for facts in transactions
            if facts["action"] == quest_envelope.ACTION_SET_QUEST_VAR
        )
        if not isinstance(quest_var["quest_after"][quest_envelope.KEY_QUEST_VARS], dict):
            raise CaptureError(
                EXIT_REQUEST,
                "set_quest_var left the quest-variable map as %r, not a dict: the "
                "branch self-heals the corpus's recorded None (command.py:113-114, "
                "design D8)"
                % (quest_var["quest_after"][quest_envelope.KEY_QUEST_VARS],),
            )
        print("capture:   the two type facts are reproduced: mission stored as the "
              "string %r, quest vars self-healed None -> dict"
              % (chapter["quest_after"][quest_envelope.KEY_MISSION],))

        # --- probe 1: the on-demand growth is UNBOUNDED ---------------------
        before_probe1 = canonical_save(save_path)
        growth = probe_envelope([[
            0, quest_envelope.SET_GOALS_COMMAND, [500, "[0,0]"],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe1_result = post_command(growth, cookie)
        if probe1_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 1: expected HTTP 200, got %r"
                               % probe1_result["status"])
        probe1_body = probe1_result.pop("body")
        after_probe1 = canonical_save(save_path)
        if json.loads(probe1_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(EXIT_REQUEST,
                               "probe 1 response is not the legacy success result: %r"
                               % (probe1_body,))
        probe1_facts = {
            "goal_index_sent": 500,
            "goals_before": len(quest_state_of(before_probe1)[quest_envelope.KEY_GOALS]),
            "goals_after": len(quest_state_of(after_probe1)[quest_envelope.KEY_GOALS]),
            "appended_entries": len(quest_state_of(after_probe1)[quest_envelope.KEY_GOALS])
            - len(quest_state_of(before_probe1)[quest_envelope.KEY_GOALS]),
            "stored_pair": quest_state_of(after_probe1)[quest_envelope.KEY_GOALS][500],
            "committed_id_max": quest_envelope.COMMITTED_ID_MAX,
            "changed_top_level_map_keys": sorted(
                key for key in set(before_probe1["maps"][0]) | set(after_probe1["maps"][0])
                if before_probe1["maps"][0].get(key) != after_probe1["maps"][0].get(key)
            ),
        }
        if probe1_facts["appended_entries"] != 350:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1 appended %r entries, not the documented 350: the "
                "unbounded growth (design D4) would be wrong"
                % (probe1_facts["appended_entries"],),
            )
        if probe1_facts["stored_pair"] != [0, 0]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1 stored %r at index 500, not the derived [0, 0]"
                % (probe1_facts["stored_pair"],),
            )

        # --- probe 2: the ONE ignored key writes nothing ----------------------
        before_probe2 = canonical_save(save_path)
        ignored = probe_envelope([[
            0, quest_envelope.SET_QUEST_VAR_COMMAND,
            [quest_envelope.QUEST_VAR_IGNORED_KEY, 5],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe2_result = post_command(ignored, cookie)
        if probe2_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 2: expected HTTP 200, got %r"
                               % probe2_result["status"])
        probe2_body = probe2_result.pop("body")
        after_probe2 = canonical_save(save_path)
        probe2_facts = {
            "key_sent": quest_envelope.QUEST_VAR_IGNORED_KEY,
            "branch_line": "command.py:91-95",
            "quest_before": quest_state_of(before_probe2),
            "quest_after": quest_state_of(after_probe2),
            "changed_leaves": leaf_differences(before_probe2, after_probe2),
        }
        if probe2_facts["quest_before"] != probe2_facts["quest_after"]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2 changed the quest state from %r to %r, but the branch "
                "RETURNS before any write (command.py:95)"
                % (probe2_facts["quest_before"], probe2_facts["quest_after"]),
            )
        if probe2_facts["changed_leaves"]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2 changed leaves %r, but the branch returns before any "
                "write" % (probe2_facts["changed_leaves"],),
            )
        # --- and an INVENTED key really is accepted (the other half of D5) ----
        before_probe2b = canonical_save(save_path)
        invented = probe_envelope([[
            0, quest_envelope.SET_QUEST_VAR_COMMAND,
            ["a_client_invented_key", "anything"],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe2b_result = post_command(invented, cookie)
        if probe2b_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 2b: expected HTTP 200, got %r"
                               % probe2b_result["status"])
        probe2b_body = probe2b_result.pop("body")
        after_probe2b = canonical_save(save_path)
        probe2_facts["invented_key_sent"] = "a_client_invented_key"
        probe2_facts["invented_key_accepted"] = (
            quest_state_of(after_probe2b)[quest_envelope.KEY_QUEST_VARS].get(
                "a_client_invented_key") == "anything"
        )
        if not probe2_facts["invented_key_accepted"]:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2b did not persist the invented key: the absence of a "
                "membership test (design D5) would be wrong",
            )
        del before_probe2b

        # --- probe 3: the out-of-range mission WRAPS, as a STRING -----------
        before_probe3 = canonical_save(save_path)
        wrap = probe_envelope([[
            0, quest_envelope.COLLECT_MISSION_COMMAND, [150],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe3_result = post_command(wrap, cookie)
        if probe3_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 3: expected HTTP 200, got %r"
                               % probe3_result["status"])
        probe3_body = probe3_result.pop("body")
        after_probe3 = canonical_save(save_path)
        probe3_facts = {
            "mission_sent": 150,
            "wrap_bound": quest_envelope.MISSION_WRAP_BOUND,
            "corpus_mission": quest_envelope.COMMITTED_MISSION,
            "corpus_mission_type": "int",
            "mission_after_recorded_step": quest_state_of(states[-1])[
                quest_envelope.KEY_MISSION],
            "mission_before": quest_state_of(before_probe3)[quest_envelope.KEY_MISSION],
            "mission_after": quest_state_of(after_probe3)[quest_envelope.KEY_MISSION],
            "stored_type": type(quest_state_of(after_probe3)[quest_envelope.KEY_MISSION]).__name__,
            "quest_vars_before": quest_state_of(before_probe3)[quest_envelope.KEY_QUEST_VARS],
            "quest_vars_after": quest_state_of(after_probe3)[quest_envelope.KEY_QUEST_VARS],
        }
        if probe3_facts["mission_after"] != "1":
            raise CaptureError(
                EXIT_REQUEST,
                "probe 3 stored mission %r, not the wrapped string \"1\": the only "
                "guard is a WRAP (command.py:432-436), not a rejection"
                % (probe3_facts["mission_after"],),
            )
        if probe3_facts["mission_before"] != "5":
            raise CaptureError(
                EXIT_REQUEST,
                "probe 3's before mission was %r, not the recorded chapter step's "
                "stringified \"5\": the corpus's INTEGER 0 became a STRING, and "
                "design D8 reproduces that rather than normalizing it"
                % (probe3_facts["mission_before"],),
            )
        if probe3_facts["quest_vars_after"] != {}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 3 left the quest-variable map as %r, not the cleared {} "
                "(command.py:440)"
                % (probe3_facts["quest_vars_after"],),
            )

        # --- probe 4: the DIVERGENCE, measured on both sides ------------------
        before_probe4 = canonical_save(save_path)
        team_one_item = None
        for key in sorted(before_probe4["maps"][0][ITEMS_FIELD], key=int):
            row = before_probe4["maps"][0][ITEMS_FIELD][key]
            if isinstance(row, list) and len(row) == 8 and row[7] == 1:
                team_one_item = int(row[0])
                break
        if team_one_item is None:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed corpus places no player-team row, so the legacy "
                "destruction cannot be exercised",
            )
        destruction_blob = json.loads(
            json.dumps(quest_envelope.end_quest_blob(11), sort_keys=True)
        )
        destruction_blob["units"] = [[team_one_item, 0, 1, 0]]
        destroying = probe_envelope([[
            0, quest_envelope.END_QUEST_COMMAND,
            [json.dumps(destruction_blob, separators=(",", ":"), sort_keys=True)],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe4_result = post_command(destroying, cookie)
        if probe4_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 4: expected HTTP 200, got %r"
                               % probe4_result["status"])
        probe4_body = probe4_result.pop("body")
        after_probe4 = canonical_save(save_path)
        probe4_facts = {
            "item_id": team_one_item,
            "unit_tuple_sent": [team_one_item, 0, 1, 0],
            "client_computed_lost": 1,
            "rows_before": len(before_probe4["maps"][0][ITEMS_FIELD]),
            "rows_after": len(after_probe4["maps"][0][ITEMS_FIELD]),
            "rows_destroyed_by_legacy": len(before_probe4["maps"][0][ITEMS_FIELD])
            - len(after_probe4["maps"][0][ITEMS_FIELD]),
            "dead_heroes_before": copy.deepcopy(
                before_probe4["privateState"]["deadHeroes"]
            ),
            "dead_heroes_after": copy.deepcopy(
                after_probe4["privateState"]["deadHeroes"]
            ),
            "quest_times_after": quest_state_of(after_probe4)[
                quest_envelope.KEY_QUEST_TIMES],
            "recorded_end_quest_step_rows_byte_identical": True,
            "endpoint_behaviour": "the endpoint derives `units: []`, so it destroys "
                                  "nothing and all 40 rows stay byte-identical",
        }
        if probe4_facts["rows_destroyed_by_legacy"] != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 4 destroyed %r rows, not the documented 1: the executed "
                "evidence for design D2's divergence would be missing"
                % (probe4_facts["rows_destroyed_by_legacy"],),
            )
        if json.loads(probe4_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(EXIT_REQUEST,
                               "probe 4 response is not the legacy success result: %r"
                               % (probe4_body,))

        # --- probe 5: fast_forward really writes quest state ------------------
        stamp = probe_envelope([[
            0, quest_envelope.END_QUEST_COMMAND,
            [json.dumps(quest_envelope.end_quest_blob(12), separators=(",", ":"),
                        sort_keys=True)],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        stamp_result = post_command(stamp, cookie)
        if stamp_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 5 stamp: expected HTTP 200, "
                               "got %r" % stamp_result["status"])
        stamp_result.pop("body")
        before_probe5 = canonical_save(save_path)
        forward = probe_envelope([[
            0, quest_envelope.FAST_FORWARD_COMMAND, [60],
            FIXTURE_EXPECTED_VECTOR_SLOTS,
        ]])
        probe5_result = post_command(forward, cookie)
        if probe5_result["status"] != 200:
            raise CaptureError(EXIT_REQUEST, "probe 5: expected HTTP 200, got %r"
                               % probe5_result["status"])
        probe5_body = probe5_result.pop("body")
        after_probe5 = canonical_save(save_path)
        state_before5 = quest_state_of(before_probe5)
        state_after5 = quest_state_of(after_probe5)
        probe5_facts = {
            "seconds_sent": 60,
            "quest_times_before": copy.deepcopy(state_before5[
                quest_envelope.KEY_QUEST_TIMES]),
            "quest_times_after": copy.deepcopy(state_after5[
                quest_envelope.KEY_QUEST_TIMES]),
            "last_chapter_before": state_before5[quest_envelope.KEY_LAST_CHAPTER],
            "last_chapter_after": state_after5[quest_envelope.KEY_LAST_CHAPTER],
            "goals_length_before": len(state_before5[quest_envelope.KEY_GOALS]),
            "goals_length_after": len(state_after5[quest_envelope.KEY_GOALS]),
            "unlocked_index_unchanged":
                state_before5[quest_envelope.KEY_UNLOCKED_INDEX]
                == state_after5[quest_envelope.KEY_UNLOCKED_INDEX],
            "mission_unchanged": state_before5[quest_envelope.KEY_MISSION]
            == state_after5[quest_envelope.KEY_MISSION],
            "ranks_unchanged": state_before5[quest_envelope.KEY_RANKS]
            == state_after5[quest_envelope.KEY_RANKS],
        }
        expected_times = {
            key: max(0, value - 60)
            for key, value in probe5_facts["quest_times_before"].items()
        }
        if probe5_facts["quest_times_after"] != expected_times:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 5 moved the quest times to %r, not the expected %r: the "
                "recorded SEVENTH writer would be wrong"
                % (probe5_facts["quest_times_after"], expected_times),
            )
        expected_chapter = max(
            0, probe5_facts["last_chapter_before"] - 60
        )
        if probe5_facts["last_chapter_after"] != expected_chapter:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 5 moved the last-chapter instant to %r, not the expected %r"
                % (probe5_facts["last_chapter_after"], expected_chapter),
            )
        for field in ("goals_length", "unlocked_index", "mission", "ranks"):
            if "%s_unchanged" % field in probe5_facts:
                if not probe5_facts["%s_unchanged" % field]:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "probe 5 changed the quest %s, which fast_forward does not"
                        % field,
                    )
            elif probe5_facts["%s_before" % field] != probe5_facts["%s_after" % field]:
                raise CaptureError(
                    EXIT_REQUEST,
                    "probe 5 changed the quest %s, which fast_forward does not"
                    % field,
                )
        if json.loads(probe5_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(EXIT_REQUEST,
                               "probe 5 response is not the legacy success result: %r"
                               % (probe5_body,))

        probe_records: List[Dict[str, Any]] = []
        for record, facts in zip(
            PROBES,
            (probe1_facts, probe2_facts, probe3_facts, probe4_facts, probe5_facts),
        ):
            merged = dict(record)
            merged.update(facts)
            probe_records.append(merged)

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

        first_before = states[0]
        last_after = states[-1]
        resources_before = resources_of(first_before)
        resources_after = resources_of(last_after)
        manifest = {
            "schema": "godot-quests/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for ALL SIX "
                "legacy quest branches against the committed corpus's own quest "
                "state; the executed-legacy parity oracle for the Compatibility "
                "API v0 quest endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_quest_fixture.py"
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
                "set_goals": True,
                "complete_goal": True,
                "set_quest_var": True,
                "collect_mission": True,
                "admin_set_quest_rank": True,
                "end_quest": True,
                "branches": STEP_COUNT,
                "branch_count_expected": quest_envelope.BRANCH_COUNT,
                "completion": False,
                "completion_captured": False,
                "completion_state_exists": False,
                "destruction_captured": False,
                "destruction_command_survives_in_the_modern_endpoint": False,
                "reward_captured": False,
                "no_absent_fixture": True,
                "note": (
                    "ALL SIX quest branches were captured against the committed "
                    "corpus's own quest state, and this line records NO absent "
                    "fixture: the corpus holds every quest field at its initial "
                    "value, so a missing branch fixture would be a gap in the line "
                    "rather than a corpus limitation. NO COMPLETION was captured "
                    "because NO COMPLETION EXISTS - complete_goal writes nothing at "
                    "all - and its step's before and after states are asserted "
                    "byte-identical. NO DESTRUCTION was captured as a step because "
                    "the destruction count is REFUSED (design D2): the recorded "
                    "end_quest step carries an empty unit list and leaves all 40 "
                    "placed rows byte-identical. The legacy destruction IS "
                    "captured, in probe 4, and recorded as a DIVERGENCE rather than "
                    "as parity"
                ),
            },
            "target": {
                "quest_fields": list(quest_envelope.QUEST_FIELDS),
                "state_before": FIXTURE_EXPECTED_STATE,
                "placement_count": FIXTURE_EXPECTED_PLACEMENTS,
                "fabricated_state": False,
                "rows_touched": 0,
                "target_rule": TARGET_RULE,
            },
            "intent": {
                "addressing_sent": [
                    {quest_envelope.ACTION_ADDRESSING_KEY[planned["action"]]:
                     planned["addressing"]}
                    for planned in STEP_PLAN
                ],
                "addressing_rule": "the addressing is the ONE value a client may "
                    "name, because it is the branch's own subject; every other "
                    "value is the module's DERIVED constant and every extra key a "
                    "client attaches is ignored",
                "derived": {
                    "progress_pair": list(quest_envelope.DERIVED_PROGRESS),
                    "progress_pair_note": quest_envelope.DERIVED_PROGRESS_NOTE,
                    "quest_var_value": quest_envelope.DERIVED_QUEST_VALUE,
                    "quest_var_value_note": quest_envelope.DERIVED_QUEST_VALUE_NOTE,
                    "rank_difficulty": quest_envelope.DERIVED_DIFFICULTY,
                    "rank_difficulty_note": quest_envelope.DERIVED_DIFFICULTY_NOTE,
                    "end_quest_blob": quest_envelope.end_quest_blob(7),
                    "end_quest_blob_note": quest_envelope.END_QUEST_REFUSAL,
                },
                "persisted_client_values": list(quest_envelope.PERSISTED_CLIENT_VALUES),
                "ignored_client_keys": list(quest_envelope.IGNORED_CLIENT_KEYS),
                "vector_rule": "NO quest price is claimed or implemented (design "
                    "D6): a price would be a CLIENT-SENT delta, because "
                    "do_command applies the request's per-command vector before "
                    "the branch (command.py:40; engine.py:251-271) as "
                    "max(current + delta, 0). The derived vector is NEUTRAL and "
                    "the endpoint's second post-execution proof half requires every "
                    "stored resource to be UNCHANGED",
                "vector_is_neutral": True,
                "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                "envelope_keys": sorted(
                    build_step_envelope(quest_envelope.ACTION_SET_GOAL, 2)
                ),
                "commands_per_batch": 1,
            },
            "command_contract": [
                {
                    "command": record["command"],
                    "action": record["action"],
                    "source": record["source"],
                    "args": record["args"],
                    "argument_order": record["argument_order"],
                    "reads": record["reads"],
                    "writes": record["writes"],
                    "delegates_to": record["delegates_to"],
                    "mutates": record["mutates"],
                    "effect": record["effect"],
                    "grows_list_on_demand": record["grows_list_on_demand"],
                    "upper_bound": record["upper_bound"],
                    "validation": record["validation"],
                    "destruction": record.get("destruction"),
                    "destruction_note": record.get("destruction_note"),
                    "difficulty_clamp": record.get("difficulty_clamp"),
                }
                for record in quest_envelope.BRANCHES
            ],
            "branch_count": len(quest_envelope.BRANCHES),
            "no_op_branch": {
                "command": quest_envelope.NO_OP_COMMAND,
                "writes_nothing_at_all": True,
                "step": "command_complete_goal",
                "quest_state_byte_identical": True,
                "leaves_moved": 0,
                "note": quest_envelope.NO_COMPLETION,
            },
            "writers": [dict(entry) for entry in quest_envelope.WRITERS],
            "writer_count": quest_envelope.WRITER_COUNT,
            "fast_forward": {
                "recorded": True,
                "implemented": False,
                "command": quest_envelope.FAST_FORWARD_COMMAND,
                "quest_times_source": "command.py:942-944",
                "last_chapter_source": "command.py:911",
                "seconds_source": "args[0], CLIENT-SUPPLIED (command.py:906)",
                "formula": "quest_times[key] = max(0, quest_times[key] - seconds)",
                "clamped": True,
                "is_a_quest_branch": False,
                "endpoint_action": "none: no action derives fast_forward, no route "
                    "exists for it, and no elapsed-time rule is derived from any "
                    "quest instant anywhere (design D9)",
                "contract": quest_envelope.FAST_FORWARD_CONTRACT,
            },
            "migration": dict(quest_envelope.MIGRATION),
            "content": {
                "entries": quest_envelope.COMMITTED_QUEST_ENTRIES,
                "kinds": ["quest"],
                "id_min": quest_envelope.COMMITTED_ID_MIN,
                "id_max": quest_envelope.COMMITTED_ID_MAX,
                "reward_value": quest_envelope.COMMITTED_REWARD_VALUE,
                "reward_distinct_values": 1,
                "field_count": quest_envelope.COMMITTED_FIELD_COUNT,
                "field_consumers": [
                    dict(record) for record in quest_envelope.COMMITTED_FIELD_CONSUMERS
                ],
                "fields_read": list(quest_envelope.COMMITTED_FIELDS_READ),
                "fields_unread": list(quest_envelope.COMMITTED_FIELDS_UNREAD),
                "hint_values_empty": quest_envelope.COMMITTED_QUEST_ENTRIES,
                "description_values_non_empty": quest_envelope.COMMITTED_QUEST_ENTRIES,
                "goal_index_source": quest_envelope.COMMITTED_GOAL_INDEX_SOURCE,
                "note": quest_envelope.CONTENT_RECORD_NOTE,
            },
            "zero_consumer_fields": [
                dict(record) for record in quest_envelope.ZERO_CONSUMER_FIELDS
            ],
            "ledger_door": dict(quest_envelope.LEDGER_DOOR),
            "type_facts": {
                "mission_integer_in_corpus": quest_envelope.COMMITTED_MISSION,
                "mission_written_as_string": True,
                "quest_vars_null_in_corpus": True,
                "quest_vars_self_healed_by_set_quest_var": True,
                "quest_vars_cleared_by_collect_mission": True,
                "note": "both facts are REPRODUCED, never normalized (design D8)",
            },
            "quest_var_keys": {
                "comment_keys": list(quest_envelope.QUEST_VAR_COMMENT_KEYS),
                "enforced": False,
                "ignored_key": quest_envelope.QUEST_VAR_IGNORED_KEY,
                "alias_key": quest_envelope.QUEST_VAR_ALIAS_KEY,
                "note": quest_envelope.QUEST_VAR_COMMENT_NOTE,
            },
            "wrap": {
                "bound": quest_envelope.MISSION_WRAP_BOUND,
                "target": quest_envelope.MISSION_WRAP_TARGET,
                "rejection": False,
                "note": quest_envelope.MISSION_WRAP_NOTE,
            },
            "refusals": [
                {"refusal": record["refusal"],
                 "implemented": record["implemented"],
                 "reason": record["reason"]}
                for record in quest_envelope.REFUSALS
            ],
            "refused_destruction": dict(quest_envelope.REFUSED_DESTRUCTION),
            "divergence": {
                "status": "DIVERGENCE, NOT PARITY",
                "legacy": "destroys placed rows via map_lose_item (command.py:796) "
                    "using the CLIENT-COMPUTED count max(0, unit[2] - unit[3]) "
                    "(command.py:792)",
                "modern": "destroys nothing: the derived blob carries an EMPTY LIST of "
                    "units, so the destruction loop iterates zero times, "
                    "map_lose_item is never reached, and every placed row is "
                    "left byte-identical over the COMPLETE items mapping",
                "executed_evidence": "probe 4 of this capture, against the live "
                    "legacy server",
                "recorded_step": "command_end_quest, whose after-state has all 40 "
                    "placed rows byte-identical",
                "note": quest_envelope.END_QUEST_REFUSAL,
            },
            "probes": probe_records,
            "transactions": transactions,
            "transaction": {
                "count": len(summaries),
                "command_steps": len(transactions),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "placement_count_before": len(first_before["maps"][0][ITEMS_FIELD]),
                "placement_count_after": len(last_after["maps"][0][ITEMS_FIELD]),
                "rows_touched_by_any_step": 0,
                "rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "private_state_outside_the_quest_fields_unchanged": True,
                "unlocked_quest_index_unchanged": True,
                "unlocked_quest_index_sites": 0,
                "player_info_unchanged": True,
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "no_op_step_byte_identical": True,
                "no_op_step_note": "complete_goal's step has a byte-identical "
                    "quest state and ZERO changed leaves, which is the executed "
                    "proof that the branch writes nothing at all (design D3)",
                "reward_paid": False,
                "reward_note": quest_envelope.NO_REWARD,
                "price_computed": False,
                "price_note": "NO price is computed anywhere and NO stored resource "
                    "moves: the committed reward field has ZERO legacy consumers and "
                    "is UNIFORMLY 10 on all 91 entries, so deriving a payout from a "
                    "constant would fabricate an economy (design D6)",
                "resource_moved": False,
                "resource_note": quest_envelope.NO_RESOURCE_MOVE,
                "completion_computed": False,
                "completion_note": quest_envelope.NO_COMPLETION,
                "goal_bound_applied": False,
                "goal_bound_note": quest_envelope.NO_BOUNDS,
                "quest_var_membership_applied": False,
                "quest_var_membership_note": quest_envelope.NO_MEMBERSHIP,
                "elapsed_time_computed": False,
                "elapsed_time_note": quest_envelope.NO_ELAPSED,
                "unlocked_index_written": False,
                "unlocked_index_note": quest_envelope.ZERO_CONSUMER_FIELDS[0][
                    "consequence"],
                "quest_writes": [
                    "engine.apply_resources applies the derived NEUTRAL vector on "
                    "the single command with max(..., 0) per resource, BEFORE the "
                    "branch (command.py:40; engine.py:251-271)",
                    "command.set_goals delegates to engine.set_goals, which pads "
                    "the goals list with None UNTIL it can address the index and "
                    "then replaces that entry (command.py:68-74; engine.py:96-100) "
                    "— the on-demand growth, with NO upper bound",
                    "command.complete_goal resolves the committed title, prints "
                    "it, and WRITES NOTHING AT ALL (command.py:76-79)",
                    "command.set_quest_var self-heals the quest-variable map from "
                    "the corpus's recorded None to {} and writes the addressed key "
                    "(command.py:113-116); the key `id` ALSO overwrites the current "
                    "mission identifier (command.py:110-111)",
                    "command.collect_mission writes the STRINGIFIED mission id, "
                    "stamps the last-chapter instant, and CLEARS the quest-variable "
                    "map (command.py:438-440) — its only guard is a WRAP above 99",
                    "command.admin_set_quest_rank writes the rank difficulty under "
                    "the stringified index (command.py:745-750) — nothing else",
                    "command.end_quest writes ONE quest-time entry under the "
                    "stringified quest id (command.py:802) and, in LEGACY ONLY, "
                    "destroys rows through map_lose_item (command.py:796) — the "
                    "REFUSED destruction count",
                    "command.fast_forward subtracts a CLIENT-SUPPLIED number of "
                    "seconds from every quest time and from the last-chapter "
                    "instant, each clamped at zero (command.py:911, 942-944) — the "
                    "recorded SEVENTH writer, offered by no action and no route",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE carries exactly TWO time-dependent VALUES, "
                    "both `time_now` stamps: maps[0]/timestampLastChapter after the "
                    "collect_mission step (and in every later before.json), and the "
                    "questTimes entry the end_quest step writes (and every later "
                    "before.json). Neither is derivable, so the parity comparison "
                    "checks each by SHAPE and DIRECTION rather than by value, and "
                    "a leaf-level diff of two consecutive runs must differ at "
                    "exactly these paths and nowhere else"
                ),
                "state_leaves": [
                    "/maps/0/timestampLastChapter in steps/command_collect_mission/"
                    "after.json (and therefore that whole document's serialization, "
                    "because the digest covers the payload)",
                    "/maps/0/questTimes in steps/command_end_quest/after.json (and "
                    "therefore that whole document's serialization)",
                ],
                "stable_state_leaves": [
                    "steps/login_post/before.json and after.json are both "
                    "byte-stable and identical to each other",
                    "every before.json up to and including "
                    "steps/command_collect_mission/before.json is byte-stable",
                    "every after.json from steps/command_end_quest/after.json "
                    "onwards is byte-stable",
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
                    "the six derived envelopes, the derived neutral vectors, every "
                    "placement, and all seven stored resources are byte-stable "
                    "because the derivation is fixed and no resource moves. Only the "
                    "two wall-clock stamps are not derivable"
                ),
                "documented_normalization": (
                    "quest parity applies NO clock normalization: the derived "
                    "progress pair, marker value, rank difficulty, wrapped mission, "
                    "and written keys are compared by value; every untouched quest "
                    "field is compared by value; every placed row is compared by "
                    "value over the COMPLETE items mapping; and every stored "
                    "resource is compared by value (exactly unchanged, because the "
                    "derived vector is neutral). The only comparisons that are not "
                    "by value are the two wall-clock stamps, which are checked for "
                    "being positive integers and for NOT moving backwards: "
                    "engine.timestamp_now has one-second resolution, so a "
                    "strictly-later rule would refuse a correct transaction"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, construction, "
                    "collect, expand, level, queue, collection, and research "
                    "fixtures are digest-pinned for the same reason."
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
        for record in probe_records:
            print(
                "capture: probe %d: %s -> %s"
                % (
                    record["probe"],
                    record["question"][:72],
                    json.dumps(
                        {
                            key: value
                            for key, value in record.items()
                            if key not in PROBES[record["probe"] - 1]
                        },
                        sort_keys=True,
                    )[:400],
                )
            )
        print("capture: all %d quest branches captured, no absent fixture, no "
              "reward, no resource moved, every placed row byte-identical"
              % quest_envelope.BRANCH_COUNT)
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except quest_envelope.EnvelopeError as error:
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