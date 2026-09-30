#!/usr/bin/env python3
"""Capture the executed-legacy level fixture: one real ``level_up`` command.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, collect, and expand captures):

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
5. Executes two recorded legacy requests, recording full canonical
   before/after save JSON plus the response for each step:

   * ``POST /``                       — login form (session cookie, as a
     logged-in Flash client would send; 302, save unchanged)
   * ``POST .../command.php``         — the crafted ``<64-hex>;<json>``
     ``data`` envelope carrying exactly **one** command —
     ``[0,"level_up",[1],[0,0,0,0,0,0,0,0]]`` — as produced by
     :mod:`level_envelope`

6. Verifies the transaction structurally before publishing: the login step
   left the save byte-identical, the recorded level after execution **equals
   the level the committed curve derives for the stored experience**, every
   placement row is byte-identical and the count stays ``40``, ``store`` /
   ``privateState`` / ``playerInfo`` and every **other** map field (including
   ``map_sizes``, which the committed corpus does not record, so its *absence*
   is asserted by the whole-key-set check) are unchanged, and **every one of the
   seven stored resources is unchanged** because the derived vector is neutral.
7. Runs one **executed-legacy probe** against the same live server, after the
   recorded step and on the same disposable copy, which is recorded in the
   manifest rather than as a step: ``level_up(2)`` carrying a client-sent
   ``[0, 500, 0, 0, 0, 0, 0, 0]`` vector.  It establishes the two facts the
   endpoint's neutral vector and its second proof half exist for: the branch
   moves the level, and a **client-sent** vector moves a balance — so proving
   that *nothing* moved is a real check and not a tautology.
8. Stops the server, re-checks the working-tree containment snapshot and the
   ten committed fixture digests, discards the disposable copy, and writes the
   fixtures under ``--out`` (default:
   ``tests/fixtures/godot-building-xp/``).

What this fixture does and does not show, stated up front
    The recorded transaction carries the **service-derived** level for the
    committed corpus: ``maps[0].xp`` is ``4``, the committed curve's ladder is
    ``0, 40, 60, 100, …``, so the one-based conversion (design D1) derives
    **level 1** — and the committed save already records ``level 1``.  The
    recorded transaction therefore leaves ``maps[0].level`` **at 1**, and every
    byte of the corpus save is identical before and after: the branch writes the
    value the client sent, and the client sent the value the save already held.

    That is not a defect in the fixture; it is the corpus condition behind the
    endpoint's ``level_already_current`` refusal, and this fixture is the
    executed evidence for it.  The **level movement** the endpoint's success
    path promises is established by **probe 1** below, executed against the same
    live server in the same run.

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

There are **no time-dependent fields in the recorded state or the recorded
response**: ``level_up`` writes the integer the client sent into the map and the
derived vector is neutral, so ``before.json``, ``after.json``, and
``response.body`` are byte-identical across reruns.  The manifest's
``time_dependent_fields`` block says so explicitly and lists only the
record-metadata and envelope-clock leaves, so a leaf-level diff of two
consecutive runs can never silently widen.

Containment (same contract as the boot, placement, purchase, move, sell, store,
upgrade, construction, collect, and expand captures):

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

Exit codes (shared with the boot, placement, purchase, move, sell, store,
upgrade, construction, collect, and expand capture harnesses):

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

    python -B apps/compat-api/capture_level_fixture.py

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
import level_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-xp"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a
# corpus and initialize live legacy state).  The level curve is read from it
# here and pinned against the module's own constants, so a config drift fails
# the run instead of publishing a different fixture.
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The committed level curve (config/main.json, top-level ``levels``): 100
# positional entries with NO stable id, every entry carrying four fully native
# fields — name (a LABEL, not an identifier: 44 distinct names across 100
# entries), exp_required (the XP ladder, strictly increasing with no duplicate
# and no non-positive gap), reward_type (one of the letter set s/w/g/c, the
# same vocabulary as items[].costs and NOT the server's resource names) and
# reward_amount (exactly 1, 50, or 250).  Nothing in the legacy server reads
# any of it.
FIXTURE_SCHEDULE_LENGTH = 100
FIXTURE_FIRST_THRESHOLDS = (0, 40, 60, 100, 200, 350, 550, 800)
FIXTURE_FINAL_THRESHOLD = 2016089205
# The committed corpus's own experience and recorded level.  These two numbers
# are the EVIDENCE for design D1: at xp 4 the zero-based reading implies level
# 0 while the save records level 1, which is the contradiction that rejects it.
FIXTURE_EXPECTED_XP = 4
FIXTURE_EXPECTED_LEVEL_BEFORE = 1
# The level the one-based conversion derives for that experience, cross-checked
# against the real configuration below rather than assumed.
FIXTURE_DERIVED_LEVEL = 1
FIXTURE_EXPECTED_LEVEL_AFTER = FIXTURE_DERIVED_LEVEL
FIXTURE_EXPECTED_VECTOR: List[int] = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 40  # no key is added or removed
# The committed corpus's other map scalars the executed transaction must leave
# untouched.  ``map_sizes`` is deliberately NOT pinned to a value: the committed
# corpus does not record that field at all (nor does any committed legacy
# source or the committed config), so its absence is enforced by the
# whole-key-set equality check in verify_transaction instead.
FIXTURE_EXPECTED_INCREASED_POPULATION = 0
FIXTURE_EXPECTED_MAP_SIZES_PRESENT = False
# The exact resource movement the derived neutral vector produces.  A level-up
# moves no resource, so the movement is zero in all seven slots and the legacy
# per-resource clamp is never exercised by this fixture — recorded as a claim
# limit rather than hidden.  Probe 1 below is the executed evidence that the
# client-sent vector *would* move a balance here.
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    FIXTURE_EXPECTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    "xp": 0,
    "gold": 0,
    "wood": 0,
    "oil": 0,
    "steel": 0,
    "cash": 0,
    "mana": 0,
}
TARGET_RULE = (
    "the level the committed one-based curve derives for the corpus's own "
    "stored experience (maps[0].xp = 4): the ladder starts 0, 40, 60, 100, … "
    "so the highest level the experience meets is 1, and the corpus already "
    "records level 1. The level is therefore DERIVED (design D1/D3) — never "
    "client-supplied — and the recorded transaction re-writes the identical "
    "value, which is exactly the condition behind the endpoint's "
    "level_already_current refusal. The level MOVEMENT the success path "
    "promises is established by probe 1, executed against this same server"
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

# The executed-legacy probe this capture runs itself, after the recorded step and
# on the same live server.  It is recorded in the manifest rather than as a step
# because it is evidence for the derivation's guarantees, not a recorded
# transaction of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does the level_up branch actually write, and what happens "
            "when the client-sent resource vector is not neutral?"
        ),
        "commands": [
            'level_up([2]) with a CLIENT-SENT vector [0, 500, 0, 0, 0, 0, 0, 0]',
        ],
        "level_before": 1,
        "level_after": 2,
        "xp_before": 4,
        "xp_after": 504,
        "changed_top_level_map_keys": ["level", "xp"],
        "other_resources": "gold 2000, wood 2000, oil 2000, steel 2000, "
        "playerInfo.cash 5 and privateState.mana 0 all unchanged",
        "response": '{"result":"success"}',
        "established": (
            "the branch assigns args[0] to map['level'] and writes NOTHING else "
            "(command.py:81-85): not the placements, not store, not "
            "map_sizes, not increasedPopulation, not privateState, not playerInfo. "
            "The experience move is entirely client-sent: apply_resources runs "
            "BEFORE the branch (command.py:40; engine.py:251-271) and applies "
            "the 8-slot vector verbatim per resource as max(current + delta, 0)"
        ),
        "why_it_matters": (
            "this is the executed evidence for the derived NEUTRAL vector and "
            "for the endpoint's second post-execution proof half. A level-up "
            "that carried a non-zero vector would move a balance through this "
            "very branch, so proving after execution that EVERY stored resource "
            "is unchanged is what distinguishes a correct level-up from a "
            "resource-minting exploit wearing its clothes (design D5). Without "
            "probe 1 the 'nothing moved' proof would be a tautology"
        ),
        "executed_in_this_capture": True,
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_level_up")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5,
                         "cash": 6, "mana": 7}

# The map fields that hold a slot of the 8-slot vector.  ``cash`` and ``mana``
# live outside the map (``playerInfo`` / ``privateState``), so they are absent
# here by construction.
MAP_RESOURCE_FIELDS = ("xp", "gold", "wood", "oil", "steel")

# Every other map field the executed transaction must leave byte-identical,
# named explicitly so the pre-publish check is readable, and then enforced for
# the **whole** key set (including the fields the corpus does not record).
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
)

# The one map field the branch owns: ``level``.  It is the transaction's subject
# and the only field a level-up may write.
LEVEL_FIELD = "level"


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


def config_level_entries() -> List[Any]:
    """The committed ``levels`` curve, or a refusal.

    Validated as a schedule with the *same* :func:`level_envelope.schedule_length`
    rule the service adapter uses, so a malformed table fails this run rather
    than producing a different ladder here and there.
    """
    entries = config_document().get("levels")
    if level_envelope.schedule_length(entries) is None:
        raise CaptureError(
            EXIT_ENVIRONMENT, "the committed config has no levels curve"
        )
    return list(entries)  # type: ignore[arg-type]


def config_level_entry(position: int) -> Optional[Dict[str, Any]]:
    """The committed curve entry at a positional index, or ``None`` out of range.

    Resolved through the envelope module's own accessors, so the curve the
    capture reads and the curve the endpoint derives from can never drift apart.
    """
    try:
        return level_envelope.entry_for_level(position + 1, config_level_entries())
    except level_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed level curve does not resolve: [%s] %s"
            % (error.code, error),
        )


def config_thresholds() -> List[int]:
    """The committed experience ladder, or a refusal."""
    try:
        return level_envelope.thresholds_from_entries(config_level_entries())
    except level_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed level curve does not resolve: [%s] %s"
            % (error.code, error),
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
    replayed (level parity works from the intent, not over HTTP), and
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
    envelope = level_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return level_envelope.data_field(envelope)


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
    collected: List[str] = []

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


# ------------------------------------------------------- derived batch ------
def build_fixture_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded batch: one ``level_up`` carrying the neutral vector.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.  The level
    is the one the committed one-based curve derives for the corpus's stored
    experience, and the vector is the neutral one this derivation can express.
    """
    derived = derive_fixture_level()
    if derived != FIXTURE_DERIVED_LEVEL:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the derived level drifted from the pinned %d: %d"
            % (FIXTURE_DERIVED_LEVEL, derived),
        )
    vector = level_envelope.neutral_vector()
    if vector != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the derived neutral vector drifted from the pinned %r: %r"
            % (FIXTURE_EXPECTED_VECTOR, vector),
        )
    return level_envelope.build_envelope(level=derived, vector=vector, ts=ts)


def derive_fixture_level() -> int:
    """The level the committed curve derives for the committed experience.

    Resolved through the envelope module's single named conversion and the real
    committed curve, then cross-checked against the pinned constant — a config
    drift fails the run instead of publishing a different fixture.
    """
    thresholds = config_thresholds()
    try:
        derived = level_envelope.derived_level_for(FIXTURE_EXPECTED_XP, thresholds)
    except level_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed level curve does not resolve: [%s] %s"
            % (error.code, error),
        )
    if derived is None:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed curve's floor is above the corpus experience %d"
            % FIXTURE_EXPECTED_XP,
        )
    return derived


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its **derived** argument, and its **neutral** vector are
    the derived contract (design D1/D3/D5); that a real client sends exactly
    this is **derived** too, because no legacy branch reads the content behind
    it.  All of it is pinned here against the committed config and fresh save
    instead, and any drift fails the run rather than silently publishing a
    different fixture.
    """
    if sorted(envelope) != sorted(level_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a level-up batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != level_envelope.LEVEL_UP_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (level_envelope.LEVEL_UP_COMMAND, entry[1]),
        )
    if entry[2] != [FIXTURE_DERIVED_LEVEL]:
        raise CaptureError(
            EXIT_REQUEST,
            "level_up args must be [%d], got %r"
            % (FIXTURE_DERIVED_LEVEL, entry[2]),
        )
    if len(entry[2]) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "level_up takes exactly one positional argument (command.py:82), got %r"
            % (entry[2],),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived neutral vector drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR),
        )
    # Every slot is zero: a level-up moves no resource, and any non-zero slot
    # would be a client-trusted mint or burn this derivation must never send.
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying:
        raise CaptureError(
            EXIT_REQUEST,
            "the level-up vector must be neutral, got slots %r" % (paying,),
        )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived neutral
    vector under the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the
    branch (``command.py:40``) and applies the 8-slot vector verbatim, per
    resource, as ``max(current + delta, 0)``; ``command.level_up``
    (``command.py:81-85``) then assigns ``args[0]`` to ``map["level"]`` and
    writes nothing else.  Any mismatch means the capture would publish a
    fixture that contradicts its own derivation, so the run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_level = entry[2][0]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    # --- the subject: the recorded level is exactly the derived level.
    if LEVEL_FIELD not in map_before or LEVEL_FIELD not in map_after:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].%s is absent (before: %s, after: %s); a level-up assigns it "
            "and never removes it"
            % (LEVEL_FIELD, LEVEL_FIELD in map_before, LEVEL_FIELD in map_after),
        )
    if map_before[LEVEL_FIELD] != FIXTURE_EXPECTED_LEVEL_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "the before-state level is %r, not the committed %r"
            % (map_before[LEVEL_FIELD], FIXTURE_EXPECTED_LEVEL_BEFORE),
        )
    if sent_level != FIXTURE_DERIVED_LEVEL:
        raise CaptureError(
            EXIT_REQUEST,
            "the sent level %r is not the derived %d"
            % (sent_level, FIXTURE_DERIVED_LEVEL),
        )
    if map_after[LEVEL_FIELD] != FIXTURE_DERIVED_LEVEL:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].level is %r after execution, not the derived %d: the "
            "branch writes exactly the value the client sent"
            % (map_after[LEVEL_FIELD], FIXTURE_DERIVED_LEVEL),
        )
    if map_after[LEVEL_FIELD] != FIXTURE_EXPECTED_LEVEL_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].level is %r, not the pinned after-state %r"
            % (map_after[LEVEL_FIELD], FIXTURE_EXPECTED_LEVEL_AFTER),
        )
    # The recorded-level movement, stated rather than assumed: on the committed
    # corpus the derived level EQUALS the recorded one, so the transaction
    # writes an identical value.  That is the corpus condition behind the
    # endpoint's level_already_current refusal, and the movement the success
    # path promises is established by probe 1.
    level_moved = map_before[LEVEL_FIELD] != map_after[LEVEL_FIELD]

    # --- the placements: none is added, removed, or changed.
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
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].item keys changed; a level-up adds and removes none"
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS_AFTER),
        )
    for other in items_before:
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; a level-up rewrites no placement at all"
                % other,
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
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; a level-up stores nothing")
    if ("map_sizes" in map_after) != FIXTURE_EXPECTED_MAP_SIZES_PRESENT:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].map_sizes presence changed (before: %s, after: %s); the "
            "committed corpus does not record the field and a level-up must "
            "never create it"
            % ("map_sizes" in map_before, "map_sizes" in map_after),
        )

    # --- the whole key set, so a field this tool does not name cannot move
    # either (this is what enforces ``map_sizes`` staying absent).
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a level-up writes one "
            "int and adds or removes nothing"
            % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field == LEVEL_FIELD:
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the branch writes only map['level']" % field,
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
                "privateState.%s changed; no level_up branch writes it" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST,
            "playerInfo changed; the level_up branch writes none of it",
        )

    # --- the money: every stored resource must have moved by EXACTLY the
    # derived neutral vector under legacy's max(current + delta, 0).  For a
    # level-up that is no movement at all; the value-level half of design D5's
    # post-execution proof, asserted here against the executed legacy server
    # itself.
    total = list(entry[3])
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    if before_resources != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "the before-state resources %r are not the documented %r"
            % (before_resources, FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
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
    _ = level_moved  # the movement is reported in the manifest, not asserted


def verify_probe_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof for the executed probe, returning its observed facts.

    The probe is the executed evidence for the two facts the derived neutral
    vector and the endpoint's "nothing moved" proof rest on: the branch writes
    the level it is given, and a **client-sent** non-zero slot moves a balance
    through it.  So the probe asserts exactly that — the level moved to the sent
    value, the sent experience moved by exactly the sent delta, and every other
    stored resource and every other field is untouched.
    """
    try:
        entry = envelope["commands"][0]
        sent_level = entry[2][0]
        sent_vector = list(entry[3])
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "probe envelope/save shape unexpected: %s" % error)
    if map_after[LEVEL_FIELD] != sent_level:
        raise CaptureError(
            EXIT_REQUEST,
            "probe: maps[0].level is %r, not the sent %r"
            % (map_after[LEVEL_FIELD], sent_level),
        )
    if map_before[LEVEL_FIELD] == map_after[LEVEL_FIELD]:
        raise CaptureError(
            EXIT_REQUEST,
            "probe: maps[0].level did not move, so the branch writes no level at all",
        )
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
        if field == LEVEL_FIELD:
            continue
        if field in MAP_RESOURCE_FIELDS:
            # The map's own resource fields are the client-sent vector's
            # territory (engine.apply_resources) and were already checked by
            # value above; cash and mana live outside the map entirely.
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "probe: maps[0].%s changed, but the branch writes only "
                "map['level'] (the experience move is the client-sent vector)"
                % field,
            )
    return {
        "level_before": map_before[LEVEL_FIELD],
        "level_after": map_after[LEVEL_FIELD],
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


def build_probe_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The probe's batch: one ``level_up`` with a client-sent vector.

    Crafted by hand rather than through the derivation, because the whole point
    is the vector the derivation **refuses** to express: :func:`validate_vector`
    would reject it, which is exactly the guarantee the probe makes concrete.
    """
    if ts is None:
        ts = 1700000000
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, level_envelope.LEVEL_UP_COMMAND, [2], [0, 500, 0, 0, 0, 0, 0, 0]]],
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
        description="Capture the executed-legacy level fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-level-capture-staging-"))
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
                "placement, purchase, move, sell, store, upgrade, construction, "
                "collect, and expand captures send it; recorded for session "
                "fidelity — command.php performs no session validation. user_key "
                "would be redacted if present.",
            )
        )

        # --- derive the level_up envelope from the committed content ------
        before_level = canonical_save(save_path)
        if before_level["maps"][0][LEVEL_FIELD] != FIXTURE_EXPECTED_LEVEL_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's recorded level is %r, not the committed %r"
                % (
                    before_level["maps"][0][LEVEL_FIELD],
                    FIXTURE_EXPECTED_LEVEL_BEFORE,
                ),
            )
        if resources_of(before_level)["xp"] != FIXTURE_EXPECTED_XP:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's stored experience is %r, not the committed %r"
                % (
                    resources_of(before_level)["xp"],
                    FIXTURE_EXPECTED_XP,
                ),
            )
        if resources_of(before_level) != FIXTURE_EXPECTED_RESOURCE_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's resources are %r, not the committed %r"
                % (resources_of(before_level), FIXTURE_EXPECTED_RESOURCE_BEFORE),
            )
        if before_level["maps"][0]["store"] != {}:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's storage is not empty; the fixture assumes %r"
                % (before_level["maps"][0]["store"],),
            )
        # The committed curve, read from the committed configuration, never
        # hardcoded into the request; the pinned constants are only the
        # cross-check that fails the run if the committed config drifts.
        entries = config_level_entries()
        if len(entries) != FIXTURE_SCHEDULE_LENGTH:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed level curve has %d entries, not the pinned %d"
                % (len(entries), FIXTURE_SCHEDULE_LENGTH),
            )
        thresholds = config_thresholds()
        if tuple(thresholds[: len(FIXTURE_FIRST_THRESHOLDS)]) != FIXTURE_FIRST_THRESHOLDS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed curve's first thresholds are %r, not the pinned %r"
                % (thresholds[: len(FIXTURE_FIRST_THRESHOLDS)], FIXTURE_FIRST_THRESHOLDS),
            )
        if thresholds[-1] != FIXTURE_FINAL_THRESHOLD:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed curve's final threshold is %r, not the pinned %r"
                % (thresholds[-1], FIXTURE_FINAL_THRESHOLD),
            )
        # Design D1's decisive evidence, asserted against the real schedule
        # rather than explained: the corpus's own experience and recorded level
        # are self-consistent only under the ONE-BASED reading.
        if level_envelope.derived_level_for(
            FIXTURE_EXPECTED_XP, thresholds
        ) != FIXTURE_DERIVED_LEVEL:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the one-based reading no longer derives level %d for %d "
                "experience"
                % (FIXTURE_DERIVED_LEVEL, FIXTURE_EXPECTED_XP),
            )
        # The REJECTED zero-based reading, spelled out here and nowhere else in
        # production code: under it ``map["level"]`` **is** the schedule index,
        # so the level it implies for an experience is the highest index whose
        # threshold the experience meets, with no ``+ 1``.  It is computed here
        # as plain index arithmetic precisely because this module must never use
        # it: the run fails if that reading ever starts to agree with the corpus,
        # since the contradiction is the whole evidence for D1.
        zero_based_derived = max(
            index
            for index, required in enumerate(thresholds)
            if required <= FIXTURE_EXPECTED_XP
        )
        if zero_based_derived == FIXTURE_EXPECTED_LEVEL_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the rejected zero-based reading now AGREES with the corpus "
                "(it derives level %r, the save records %r), so the evidence "
                "that rejects it no longer holds"
                % (zero_based_derived, FIXTURE_EXPECTED_LEVEL_BEFORE),
            )
        entry_one = config_level_entry(0)
        entry_two = config_level_entry(1)
        if entry_one is None or entry_two is None:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed curve has no first or second entry",
            )
        if entry_one["name"] != level_envelope.COMMITTED_LEVEL_ONE_NAME:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the curve's first entry is %r, not the pinned %r"
                % (entry_one["name"], level_envelope.COMMITTED_LEVEL_ONE_NAME),
            )
        if entry_two["name"] != level_envelope.COMMITTED_LEVEL_TWO_NAME:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the curve's second entry is %r, not the pinned %r"
                % (entry_two["name"], level_envelope.COMMITTED_LEVEL_TWO_NAME),
            )
        envelope = build_fixture_envelope()
        verify_envelope(envelope)
        data = level_envelope.data_field(envelope)
        level_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the single-command level_up batch ---------------------
        level_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(level_form),
            cookie=cookie,
            timeout=30.0,
        )
        if level_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_level_up: expected HTTP 200, got %r"
                % level_result["status"],
            )
        after_level = canonical_save(save_path)
        body = level_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_level_up",
                level_result,
                body,
                before_level,
                after_level,
                level_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly one command: "
                "a level_up whose single argument is the SERVICE-DERIVED LEVEL "
                "and whose resources_changed is the NEUTRAL VECTOR "
                "[0, 0, 0, 0, 0, 0, 0, 0] — the level the committed one-based "
                "levels curve (design D1) implies for the corpus's own 4 stored "
                "experience. No level, experience, reward, time, or resource "
                "delta is client-supplied: the level is DERIVED, and the "
                "one-based index interpretation is DERIVED-PROVISIONAL with the "
                "rejected zero-based alternative contradicted by the corpus "
                "(xp 4 would imply level 0 while the save records 1). The "
                "branch's single assignment from a client integer with no range "
                "check and no experience validation, and the verbatim per-"
                "resource application under the max(..., 0) clamp before it, are "
                "ESTABLISHED. user_key is redacted in this record; accessToken "
                "is the crafted empty placeholder, never a token value.",
            )
        )

        # --- structural verification of the recorded transaction -----------
        verify_transaction(before_level, after_level, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_level_up response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
            )
        resources_before = resources_of(before_level)
        resources_after = resources_of(after_level)
        level_moved = before_level["maps"][0][LEVEL_FIELD] != after_level["maps"][0][
            LEVEL_FIELD
        ]
        recorded_leaf_diff = leaf_differences(before_level, after_level)

        # --- the executed-legacy probe (not a recorded step) ---------------
        probe_envelope = build_probe_envelope()
        probe_data = level_envelope.data_field(probe_envelope)
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
        probe_facts = verify_probe_transaction(
            before_probe, after_probe, probe_envelope
        )
        if json.loads(probe_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe response is not the legacy success result: %r" % (probe_body,),
            )
        probe_record = dict(PROBES[0])
        probe_record.update(probe_facts)
        print(
            "capture: probe level %r -> %r, xp %r -> %r, changed map keys %r"
            % (
                probe_facts["level_before"],
                probe_facts["level_after"],
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

        entry = envelope["commands"][0]
        manifest = {
            "schema": "godot-building-xp/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "level_up transaction carrying the service-derived level and the "
                "neutral vector; the executed-legacy parity oracle for the "
                "Compatibility API v0 level_up endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_level_fixture.py"
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
                "level_sent": FIXTURE_DERIVED_LEVEL,
                "target_rule": TARGET_RULE,
                "index_base_rule": "the committed levels curve is ONE-BASED: "
                "stored level n is levels[n - 1], and the conversion lives in "
                "exactly one named function (level_envelope.entry_index_for_level). "
                "This is DERIVED-PROVISIONAL (design D1) and the REJECTED "
                "alternative is the ZERO-BASED reading, which the committed corpus "
                "CONTRADICTS: at xp 4 it implies level 0 while the save records "
                "level 1, whereas the one-based reading places level 1 at 0 "
                "experience and 4 >= 0 holds",
                "reward_rule": "NO level reward is paid and none is derived "
                "(design D7): every committed entry carries reward_type and "
                "reward_amount, and NO legacy branch reads either, so paying one "
                "would invent an economy — the same discipline the expansion "
                "neighbors / inventory_qte requirements received",
                "unit_xp_rule": "unit experience (add_xp_unit) is OUT OF SCOPE: the "
                "committed corpus has no unit placements and 0 of its 40 placed "
                "rows carry attr['xp']",
                "derived": {
                    "command": entry[1],
                    "args": entry[2],
                    "resources_changed": entry[3],
                    "vector_is_neutral": True,
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "conversion": "entry_index_for_level(level, entries) -> "
                    "level - 1, the single named one-based conversion",
                    "curve": {
                        "key": "levels",
                        "entries": len(entries),
                        "stable_id": False,
                        "id_space": "the stored level 1..%d" % len(entries),
                        "index_base": level_envelope.INDEX_BASE,
                        "derivation_status": level_envelope.DERIVATION_STATUS,
                        "rejected_alternative": level_envelope.REJECTED_ALTERNATIVE,
                        "fields": list(level_envelope.COMMITTED_ENTRY_FIELDS),
                        "first_thresholds": list(FIXTURE_FIRST_THRESHOLDS),
                        "final_threshold": thresholds[-1],
                        "strictly_increasing": True,
                        "duplicate_thresholds": 0,
                        "distinct_names": len(
                            {str(row.get("name")) for row in entries}
                        ),
                        "name_is_a_label": True,
                        "reward_types": sorted(
                            {str(row.get("reward_type")) for row in entries}
                        ),
                        "reward_amounts": sorted(
                            {row.get("reward_amount") for row in entries}
                        ),
                        "first_entry": level_envelope.entry_snapshot(entries[0]),
                        "second_entry": level_envelope.entry_snapshot(entries[1]),
                        "final_entry": level_envelope.entry_snapshot(entries[-1]),
                        "read_by_the_legacy_server": False,
                    },
                    "decisions": {
                        "D1_index_base": "the committed curve is ONE-BASED: stored "
                        "level n is levels[n - 1], and the conversion lives in "
                        "exactly one named function "
                        "(level_envelope.entry_index_for_level) so a later change "
                        "with better evidence revises one function rather than "
                        "auditing the codebase. DERIVED-PROVISIONAL. The REJECTED alternative is "
                        "the ZERO-BASED reading, and the corpus CONTRADICTS it: at "
                        "xp 4 the zero-based curve implies level 0 while the save "
                        "records level 1, while the one-based reading maps level 1 "
                        "to levels[0] ('Slave', exp_required 0) and 4 >= 0 holds. "
                        "Guessing zero-based would shift EVERY level by one and the "
                        "error would stay invisible until a player saw the wrong "
                        "level name",
                        "D2_recorded_level_unverified": "the recorded level is "
                        "written from a client-supplied integer with no range check "
                        "and no experience validation, so it is NOT evidence of "
                        "anything the curve implies. Two distinct facts exist and "
                        "are never conflated: the derived level and the recorded "
                        "level. The endpoint reports BOTH and refuses rather than "
                        "reconciling a disagreement (level_already_current when they "
                        "are equal, xp_below_threshold when the recorded level sits "
                        "above what the stored experience supports)",
                        "D3_derived_target": "the request carries only the save id. "
                        "The target level is derived server-side from the stored "
                        "experience and the committed curve; a client-supplied level "
                        "(or new_level, or xp) key is IGNORED, exactly as the collect "
                        "and expand endpoints ignore client-supplied amounts and "
                        "prices. This closes the legacy hole where any client could "
                        "set level 99",
                        "D4_fail_closed_refusals": "both refusals are answered "
                        "BEFORE the dispatcher runs, so the corpus is byte-identical "
                        "on every error path: level_already_current (409) and "
                        "xp_below_threshold (409)",
                        "D5_two_part_proof": "after execution the endpoint requires "
                        "BOTH that the recorded level is EXACTLY the derived level "
                        "AND that EVERY stored resource is UNCHANGED. The second "
                        "half is what forecloses vector smuggling: level_up is "
                        "dispatched with a client-sent vector like every other "
                        "command, so a non-zero vector would move a balance through "
                        "this very branch (probe 1 executes that), and proving that "
                        "NOTHING moved is what distinguishes a correct level-up from "
                        "a resource-minting exploit wearing its clothes",
                        "D6_unaffordable_next_level": "the curve's next threshold and "
                        "the remaining experience are REPORTED as information only "
                        "— no gate, no penalty, no skip. The endpoint simply refuses a "
                        "request the stored experience cannot support "
                        "(xp_below_threshold)",
                        "D7_no_tuning_no_rewards": "the committed exp_required values "
                        "are preserved VERBATIM: nothing is rebalanced, smoothed, or "
                        "interpolated. reward_type / reward_amount are consumed by no "
                        "legacy branch and are therefore REFUSED rather than "
                        "invented. Unit experience and the tutorial are out of scope "
                        "because the corpus cannot exercise them",
                    },
                    "status": "established: the command's argument shape and its "
                    "single effect (map['level'] = new_level, command.py:81-85), that "
                    "the client-sent 8-slot vector is applied verbatim per resource "
                    "as max(current + delta, 0) and applied BEFORE the branch "
                    "(command.py:40; engine.py:251-271), that NOTHING in the legacy "
                    "server reads the committed levels curve (zero references across "
                    "command.py, engine.py, sessions.py, server.py, constants.py), "
                    "the committed curve and its census, that 0 of the corpus's 40 "
                    "placed rows carry unit experience, and the resulting state of "
                    "this executed transaction. DERIVED and never observed from the "
                    "Flash client: D1 (the one-based index interpretation, with the "
                    "rejected zero-based alternative stated), D2 (reporting the "
                    "recorded-versus-derived disagreement rather than reconciling it), "
                    "and D3 (the derived target itself). The claim is that the "
                    "recorded level is the one the committed curve implies for the "
                    "stored experience, NEVER one observed a Flash client send, and "
                    "no reward is claimed for any level",
                },
            },
            "probes": [probe_record],
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "stored_xp_before": resources_before["xp"],
                "level_before": before_level["maps"][0][LEVEL_FIELD],
                "level_after": after_level["maps"][0][LEVEL_FIELD],
                "derived_level": FIXTURE_DERIVED_LEVEL,
                "level_moved": level_moved,
                "level_moved_note": "the recorded level did NOT move on this corpus, "
                "and that is the honest recorded fact: the service-derived level for "
                "xp 4 is 1 and the corpus already records 1, so the branch wrote an "
                "identical value. This is exactly the condition behind the "
                "endpoint's level_already_current refusal, and probe 1 (executed in "
                "this same run against this same server) is the evidence that the "
                "branch moves the level when the derived level differs",
                "recorded_leaf_differences": recorded_leaf_diff,
                "placement_count_before": len(before_level["maps"][0]["items"]),
                "placement_count_after": len(after_level["maps"][0]["items"]),
                "map_sizes_present_before": "map_sizes" in before_level["maps"][0],
                "map_sizes_present_after": "map_sizes" in after_level["maps"][0],
                "increased_population_before": before_level["maps"][0][
                    "increasedPopulation"
                ],
                "increased_population_after": after_level["maps"][0][
                    "increasedPopulation"
                ],
                "store_after": after_level["maps"][0]["store"],
                "bought_units_before": before_level["privateState"]["boughtUnits"],
                "bought_units_after": after_level["privateState"]["boughtUnits"],
                "dead_heroes_after": after_level["privateState"]["deadHeroes"],
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
                "reward_paid": False,
                "reward_note": "NO level reward is paid and none is derived: every "
                "committed entry carries reward_type and reward_amount and NO legacy "
                "branch reads either, so the neutral vector is the whole economic "
                "content of a level-up under this contract (design D7)",
                "level_up_writes": [
                    "engine.apply_resources applies the derived NEUTRAL vector on the "
                    "single command with max(..., 0) per resource, BEFORE the branch "
                    "(command.py:40; engine.py:251-271)",
                    "command.level_up assigns args[0] to map['level'] and writes "
                    "NOTHING else (command.py:81-85)",
                    "no branch reads, validates, ranges, or derives map['level'] "
                    "against map['xp'], and NOTHING in the legacy server reads the "
                    "committed levels curve — a repository-wide search finds zero "
                    "references to it in command.py, engine.py, sessions.py, "
                    "server.py, and constants.py",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE and the recorded RESPONSE carry NO "
                    "time-dependent leaf at all: level_up writes the integer the "
                    "client sent into the map and the derived vector is the neutral "
                    "all-zero vector, so steps/*/before.json, steps/*/after.json, "
                    "and steps/*/response.body are byte-identical across reruns. "
                    "The leaves below are the whole record-metadata and "
                    "envelope-clock surface, and the claim is machine-checkable: a "
                    "leaf-level diff of two consecutive runs must differ at "
                    "exactly these 8 paths and nowhere else"
                ),
                "state_leaves": [],
                "leaves": [
                    "/captured_at_utc in steps/login_post/request.json",
                    "/captured_at_utc in steps/login_post/response.meta.json",
                    "/captured_at_utc in steps/command_level_up/request.json",
                    "/captured_at_utc in steps/command_level_up/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in steps/login_post/response.meta.json",
                    "/headers/Date in steps/command_level_up/response.meta.json",
                    "the envelope ts inside steps/command_level_up/request.json's "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                ],
                "stable_by_derivation": (
                    "the recorded level and every resource are byte-stable because "
                    "the derivation is fixed: the committed ladder's floor is 0, the "
                    "corpus's stored experience is 4, and the one-based conversion "
                    "therefore always derives level 1, so /transaction/level_after, "
                    "/transaction/resources_after, /transaction/resource_delta, "
                    "/transaction/save_after_sha256, /transaction/"
                    "recorded_leaf_differences and every leaf of the two save "
                    "documents are stable. There is no wall-clock reading anywhere "
                    "in the recorded state — unlike collect's item[3] = time_now(), "
                    "the level_up branch writes no clock of its own"
                ),
                "documented_normalization": (
                    "level parity applies NO clock normalization: the recorded level "
                    "is compared by value (exactly the derived level) and every "
                    "stored resource by value (exactly unchanged, because the "
                    "derived vector is neutral). The only clock in the transaction is "
                    "the envelope ts, which legacy parses and never reads, and the "
                    "legacy branch writes no clock of its own"
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
                "capture:   %-22s %s %s -> %d (%d bytes, save unchanged: %s)"
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
            "capture: derived command %s%s with resources %s (NEUTRAL: a level-up "
            "moves no resource and no reward is paid)"
            % (entry[1], entry[2], entry[3])
        )
        print(
            "capture: level %r -> %r (derived %d, moved: %s), stored xp %d"
            % (
                before_level["maps"][0][LEVEL_FIELD],
                after_level["maps"][0][LEVEL_FIELD],
                FIXTURE_DERIVED_LEVEL,
                level_moved,
                resources_before["xp"],
            )
        )
        print(
            "capture: recorded state leaf differences: %r"
            % (recorded_leaf_diff,)
        )
        print(
            "capture: placements %d -> %d, increasedPopulation %r, map_sizes present "
            "%s, store %r, boughtUnits %r -> %r, deadHeroes %r"
            % (
                len(before_level["maps"][0]["items"]),
                len(after_level["maps"][0]["items"]),
                after_level["maps"][0]["increasedPopulation"],
                "map_sizes" in after_level["maps"][0],
                after_level["maps"][0]["store"],
                before_level["privateState"]["boughtUnits"],
                after_level["privateState"]["boughtUnits"],
                after_level["privateState"]["deadHeroes"],
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

    except level_envelope.EnvelopeError as error:
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