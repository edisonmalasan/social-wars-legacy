#!/usr/bin/env python3
"""Capture the executed-legacy construction fixture: one real two-command batch.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, and upgrade captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, and upgrade fixtures.
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
     ``[0,"activate",[11,5],zeros]`` then ``[0,"add_click",[11],zeros]`` —
     as produced by :mod:`construction_envelope`

   The fixture construction is the placed **Turret I** (item id 22) at map
   slot ``11``, anchored at ``(58,48)`` in the fresh-player corpus: committed
   ``build_time "5"`` and ``clicks_to_build "1"``, ``attr {}`` and
   ``timestamp 0``, so the corpus has no construction in progress and the
   fixture must *start* one.  Slot ``11`` is the same row the move fixture
   repositions in **its own independent transaction** (each capture seeds a
   fresh corpus), so both fixtures stay independently readable.
6. Verifies the transaction structurally before publishing: the login step
   left the save byte-identical, the construction step mutated it, the row at
   key ``"11"`` **still exists** afterwards holding item ``22`` at the
   **same cell** ``(58,48)``, its ``timestamp`` is a fresh wall-clock stamp,
   ``attr`` is exactly ``{"cp": 5, "nc": 1}`` — the derived countdown equal to
   the item's committed ``build_time`` and a click counter equal to its
   ``clicks_to_build`` — the placement count stays ``40``, every other row is
   byte-identical, and the whole ``privateState`` (``boughtUnits []``,
   ``deadHeroes {}``), ``maps[0].store`` (``{}``), ``playerInfo``, every other
   map field, and all seven resources are unchanged (the derived vectors are
   neutral).  The recorded request itself is pinned: exactly two commands in
   the recorded order, the committed derived duration, and both neutral
   vectors.
7. Stops the server, re-checks the working-tree containment snapshot and the
   committed boot/placement/purchase/move/sell/store/upgrade fixture digests,
   discards the disposable copy, and writes the fixtures under ``--out``
   (default: ``tests/fixtures/godot-building-construction/``).

The third construction command is recorded but **not** executed here: see the
``omitted_step`` manifest block and the fixture README — the completing
command's effect (deleting the click counter) is established by the earlier
recorded investigation probe, and the endpoint's per-action proof covers it.
The two-command form was chosen precisely because it leaves **both** the
countdown and the click counter visible in the committed after-state.

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
  placement, purchase, move, sell, store, and upgrade fixtures are
  digest-pinned for the same reason.
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

    python -B apps/compat-api/capture_construction_fixture.py

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
import construction_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-construction"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a
# corpus and initialize live legacy state).  The fixture's build time and
# click requirement are read from it here and pinned against the committed
# constants.
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The fixture construction intent (verified against the committed config and
# fresh save: slot "11" holds [22, 58, 48, 0, 0, [], {}, 1] and the config's
# build_time for item 22 is "5", clicks_to_build "1").
FIXTURE_ITEM_INDEX = 11
FIXTURE_ITEM_ID = 22  # Turret I: the placed building this fixture constructs
FIXTURE_ITEM_NAME = "Turret I"
FIXTURE_X = 58
FIXTURE_Y = 48
FIXTURE_BUILD_TIME = 5  # item 22's committed build_time, in seconds
FIXTURE_CLICKS_TO_BUILD = 1  # item 22's committed click requirement
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 40  # no key is added or removed
# The row's attribute bag after the recorded batch: the derived countdown
# (``cp``) the start writes and the click counter (``nc``) the click raises.
# ``nc`` equals the item's committed ``clicks_to_build`` of 1 — one click
# completes this building's clicks, which is a *client* reading of a value no
# server branch ever compares.
FIXTURE_EXPECTED_ATTR_AFTER: Dict[str, int] = {"cp": 5, "nc": 1}
TARGET_RULE = (
    "the placed Turret I (item id 22) at map slot 11 anchored at (58,48) in "
    "the committed fresh save, whose committed build_time is 5 and whose "
    "clicks_to_build is 1 — the fresh corpus has no construction in progress "
    "(every row's attr is {} and every timestamp is 0), so this fixture "
    "starts one and leaves both the countdown and the click counter visible; "
    "slot 11 is the same row the move fixture repositions in its own "
    "independent transaction, so the two fixtures stay independently readable"
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
)

# The completing command, recorded but deliberately NOT executed by this tool.
# Its effect — deleting ``attr["nc"]`` — is established by the executed
# investigation probe recorded in docs/legacy-construction-timing.md (probe C)
# and by the unchanged legacy dispatcher (command.py:537-548; engine.py:132-135),
# and it is covered by the Compatibility API v0 endpoint's per-action
# ``finish`` post-execution proof.  Recording it here keeps the whole contract
# in the manifest without publishing a second transaction.
OMITTED_STEP: Dict[str, Any] = {
    "what": (
        "the third construction command, activate_item_click, which completes "
        "the build by deleting attr['nc']"
    ),
    "command": construction_envelope.ACTIVATE_ITEM_CLICK_COMMAND,
    "args": [FIXTURE_ITEM_INDEX],
    "why_not_captured": (
        "the executed fixture sends the two-command form — a start followed by "
        "a build click — because it leaves BOTH the countdown and the click "
        "counter visible in the committed after-state, which is what makes it a "
        "useful oracle; adding the completing command would delete the counter "
        "and hide the counter's value"
    ),
    "established_by": (
        "the executed-legacy investigation probe recorded in "
        "docs/legacy-construction-timing.md (probe C: add_click, then "
        "activate_item_click, then a zero-duration activate), and by the "
        "unchanged legacy dispatcher itself — command.py:537-548 calls "
        "engine.activate_item_click (engine.py:132-135), which deletes "
        "attr['nc'] and writes nothing else"
    ),
    "covered_by": (
        "the Compatibility API v0 /v0/construction endpoint's per-action "
        "post-execution proof: after a 'finish' the row's attribute bag must "
        "NOT contain 'nc', and any other outcome fails closed with "
        "internal_error"
    ),
    "not_observed_from_client": (
        "whether the Flash client sends activate_item_click immediately at "
        "nc == clicks_to_build or only after a visual build effect — never "
        "observed, because Flash is never executed in this repository"
    ),
}

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_construction")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5}


# --------------------------------------------------------- committed config --
def config_item_attribute(item_id: int, attribute: str) -> Any:
    """A raw committed item attribute, or ``None`` when the item is unknown.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (see :data:`CONFIG_MAIN`).  The build time is then resolved with
    exactly the rule :meth:`compat_legacy.LegacyBoot.item_build_time` uses
    server-side: a missing attribute, a non-integer value, and a zero or
    negative value all mean **no resolvable duration** (and are never
    coerced).
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
    return item.get(attribute)


def config_build_time(item_id: int) -> Optional[int]:
    """The item's committed build time as a positive int, or ``None``."""
    raw = config_item_attribute(item_id, "build_time")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        seconds = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return seconds


def config_clicks_to_build(item_id: int) -> Optional[int]:
    """The item's committed click requirement as a positive int, or ``None``."""
    raw = config_item_attribute(item_id, "clicks_to_build")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        clicks = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if clicks <= 0:
        return None
    return clicks


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
    replayed (construction parity works from the intent, not over HTTP), and
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
    envelope = construction_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return construction_envelope.data_field(envelope)


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


# ------------------------------------------------------- derived batch ------
def build_fixture_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded batch: one construction start, then one build click.

    Built from the two shared derivations rather than hand-written, so the
    captured request and the Compatibility API endpoint can never drift apart.
    The batch is composed here (and **only** here) because the executed
    fixture records one construction in progress with both halves visible,
    while the endpoint executes exactly one command per call.
    """
    start = construction_envelope.build_envelope_start(
        item_index=FIXTURE_ITEM_INDEX, duration=FIXTURE_BUILD_TIME, ts=ts
    )
    click = construction_envelope.build_envelope_click(
        item_index=FIXTURE_ITEM_INDEX, ts=ts
    )
    return {
        "first_number": start["first_number"],
        "publishActions": start["publishActions"],
        "ts": start["ts"],
        "tries": start["tries"],
        "accessToken": start["accessToken"],
        "commands": list(start["commands"]) + list(click["commands"]),
    }


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The two commands, their order, and their argument values are the executed
    contract (design D1/D2); the Flash client is never executed, so that a
    real construction sends exactly this pair, and that the duration a client
    sends is the item's ``build_time`` rather than its ``activation`` field or
    a speedup-adjusted figure, are **derived-provisional** (design D4).  The
    neutral price vectors are derived too.  All of it is pinned here against
    the committed config and fresh save instead, and any drift fails the run
    rather than silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(construction_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 2:
        raise CaptureError(
            EXIT_REQUEST,
            "a construction batch must carry exactly two commands, got %d"
            % len(commands),
        )

    start_entry, click_entry = commands
    if start_entry[0] != 0 or click_entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on both commands")
    if start_entry[1] != construction_envelope.ACTIVATE_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the first command must be %r, got %r"
            % (construction_envelope.ACTIVATE_COMMAND, start_entry[1]),
        )
    if click_entry[1] != construction_envelope.ADD_CLICK_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the second command must be %r, got %r"
            % (construction_envelope.ADD_CLICK_COMMAND, click_entry[1]),
        )

    expected_start_args = [FIXTURE_ITEM_INDEX, FIXTURE_BUILD_TIME]
    if start_entry[2] != expected_start_args:
        raise CaptureError(
            EXIT_REQUEST,
            "activate args must be %r, got %r" % (expected_start_args, start_entry[2]),
        )
    expected_click_args = [FIXTURE_ITEM_INDEX]
    if click_entry[2] != expected_click_args:
        raise CaptureError(
            EXIT_REQUEST,
            "add_click args must be %r, got %r" % (expected_click_args, click_entry[2]),
        )
    for label, entry in (("activate", start_entry), ("add_click", click_entry)):
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
    under the legacy rules, in the order legacy applies them:
    ``command.activate`` (``command.py:412-429``) resolves the row with
    ``engine.map_get_item`` and, because the derived duration is **positive**,
    writes ``item[3] = timestamp_now()`` and ``item[6]["cp"] = duration`` —
    it does **not** clear the bag; ``command.add_click``
    (``command.py:525-536``) then calls ``engine.add_click``
    (``engine.py:125-130``), which raises the counter seeded by the purchase
    half (``engine.map_add_item``, ``engine.py:25-28``) to 1.
    ``engine.apply_resources`` (``engine.py:251-271``) applies the neutral
    vectors with a per-slot ``max(..., 0)``, once per command.  No branch here
    touches ``privateState``, ``maps[0].store``, or ``playerInfo``, and no
    branch compares ``nc`` with ``clicks_to_build`` — the server has no
    completion rule at all.  Any mismatch means the capture would publish a
    fixture that contradicts its own derivation, so the run fails with exit 5.
    """
    try:
        start_entry, click_entry = envelope["commands"]
        key = str(start_entry[2][0])
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
        raise CaptureError(EXIT_REQUEST, "no placement row at index %s to build" % key)
    if len(row_before) != 8:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is not an eight-field entry" % key,
        )
    if int(row_before[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row is item %r, not the fixture item %d"
            % (row_before[0], FIXTURE_ITEM_ID),
        )
    if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row is anchored at %r, not the documented %r"
            % ([row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
        )
    # The fresh corpus has no construction in progress, which is what makes
    # this fixture a start rather than an observation.
    if row_before[6] != {}:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row's attr is %r, not the committed empty bag"
            % (row_before[6],),
        )
    if row_before[3] != 0:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row's timestamp is %r, not the committed 0"
            % (row_before[3],),
        )

    # A construction action must never destroy or move the row: the key
    # survives, holding the same item at the very same cell.
    if key not in items_after:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is absent after the construction; the "
            "pair only rewrites the row's timestamp and attribute bag" % key,
        )
    row_after = items_after[key]
    if not isinstance(row_after, list) or len(row_after) != 8:
        raise CaptureError(EXIT_REQUEST, "the constructed row is not an eight-field entry")
    if int(row_after[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "the constructed row holds item %r, not the fixture item %d"
            % (row_after[0], FIXTURE_ITEM_ID),
        )
    if [row_after[1], row_after[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "the constructed row is anchored at %r, not the pre-execution cell %r"
            % ([row_after[1], row_after[2]], [FIXTURE_X, FIXTURE_Y]),
        )
    # The fresh wall-clock start instant: the one documented time-dependent
    # value in the recorded state.  Remaining time is cp - (now - item[3]),
    # a pure client derivation over data the server never interprets.
    stamp = row_after[3]
    if not isinstance(stamp, int) or isinstance(stamp, bool) or stamp <= 0:
        raise CaptureError(
            EXIT_REQUEST, "the constructed row's timestamp is not a wall-clock stamp: %r"
            % (stamp,)
        )
    if stamp < row_before[3]:
        raise CaptureError(
            EXIT_REQUEST,
            "the constructed row's timestamp %r predates the before-state's %r; "
            "activate stamps the current time" % (stamp, row_before[3]),
        )
    # Everything else about the row is untouched: the construction writes only
    # the timestamp and the attribute bag.
    for field, label in ((4, "orientation"), (5, "store"), (7, "player team")):
        if row_after[field] != row_before[field]:
            raise CaptureError(
                EXIT_REQUEST,
                "the constructed row's %s changed %r -> %r; the pair writes only "
                "item[3] and item[6]" % (label, row_before[field], row_after[field]),
            )
    if row_after[5] != []:
        raise CaptureError(
            EXIT_REQUEST,
            "the constructed row carries a stored-unit payload: %r" % (row_after[5],),
        )
    if row_after[6] != FIXTURE_EXPECTED_ATTR_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "the constructed row's attr is %r, not the derived countdown and "
            "click counter %r (activate sets cp, add_click raises the "
            "purchase-seeded nc)"
            % (row_after[6], FIXTURE_EXPECTED_ATTR_AFTER),
        )

    # No key is added or removed: the pair rewrites exactly one entry in place.
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].item keys changed; the pair adds and removes none"
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
                "placement row %s changed; a construction rewrites only the row "
                "it addresses" % other,
            )

    # Legacy apply_resources: max(current + delta, 0) per slot, applied once
    # per command.  Both derived vectors are neutral, so no resource may move.
    total = [
        sum(entry[3][slot] for entry in envelope["commands"])
        for slot in range(construction_envelope.RESOURCE_VECTOR_SLOTS)
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

    # A construction stores nothing, records no purchase, and leaves the whole
    # private state alone: no branch here calls bought_unit_add, push_dead_unit,
    # buy_si_help, or finish_si.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; a construction stores never")
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; no construction command writes it" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST, "playerInfo changed; neither command writes any of it"
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field in ("items", "store", "xp", "gold", "wood", "oil", "steel"):
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the pair writes only the addressed row" % field,
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
        description="Capture the executed-legacy construction fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-construction-capture-staging-"))
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
                "placement, purchase, move, sell, store, and upgrade captures "
                "send it; recorded for session fidelity — command.php performs "
                "no session validation. user_key would be redacted if present.",
            )
        )

        # --- derive the construction envelope from the committed content ----
        before_construction = canonical_save(save_path)
        row_before = before_construction["maps"][0]["items"].get(
            str(FIXTURE_ITEM_INDEX)
        )
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
                % (FIXTURE_ITEM_INDEX, [row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
            )
        if int(row_before[0]) != FIXTURE_ITEM_ID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's index %d holds item %r, not %d"
                % (FIXTURE_ITEM_INDEX, row_before[0], FIXTURE_ITEM_ID),
            )
        if row_before[6] != {} or row_before[3] != 0:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's index %d already carries construction state "
                "(attr %r, timestamp %r); the fixture assumes none"
                % (FIXTURE_ITEM_INDEX, row_before[6], row_before[3]),
            )
        if before_construction["maps"][0]["store"] != {}:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's storage is not empty; the fixture assumes %r"
                % (before_construction["maps"][0]["store"],),
            )
        # The duration and the click requirement are resolved from the
        # committed configuration, never hardcoded into the request; the pinned
        # constants are only the cross-check that fails the run if the committed
        # config drifts.
        resolved_build_time = config_build_time(FIXTURE_ITEM_ID)
        if resolved_build_time != FIXTURE_BUILD_TIME:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's build_time to "
                "%r, not the pinned %d"
                % (FIXTURE_ITEM_ID, resolved_build_time, FIXTURE_BUILD_TIME),
            )
        resolved_clicks = config_clicks_to_build(FIXTURE_ITEM_ID)
        if resolved_clicks != FIXTURE_CLICKS_TO_BUILD:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's clicks_to_build "
                "to %r, not the pinned %d"
                % (FIXTURE_ITEM_ID, resolved_clicks, FIXTURE_CLICKS_TO_BUILD),
            )
        envelope = build_fixture_envelope()
        verify_envelope(envelope)
        data = construction_envelope.data_field(envelope)
        construction_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the two-command construction batch --------------------
        construction_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(construction_form),
            cookie=cookie,
            timeout=30.0,
        )
        if construction_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_construction: expected HTTP 200, got %r"
                % construction_result["status"],
            )
        after_construction = canonical_save(save_path)
        if save_bytes_sha(before_construction) == save_bytes_sha(after_construction):
            raise CaptureError(
                EXIT_REQUEST,
                "command_construction did not persist any save change; refusing "
                "to publish a non-transaction fixture",
            )
        body = construction_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_construction",
                construction_result,
                body,
                before_construction,
                after_construction,
                construction_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly two "
                "commands in the recorded order: an activate whose two "
                "arguments are the legacy map index and the item's committed "
                "build_time (resolved server-side from config/main.json, never "
                "client-supplied, and the only way the countdown is derived), "
                "then an add_click whose single argument is the same map index "
                "and which raises the click counter the purchase half seeded; "
                "both commands carry the neutral all-zero resources_changed "
                "vector (no building cost is claimed); user_key is redacted in "
                "this record; accessToken is the crafted empty placeholder, "
                "never a token value. The completing activate_item_click is "
                "recorded in the manifest's omitted_step block and is NOT part "
                "of this batch, so the committed after-state keeps both the "
                "countdown and the counter visible.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_construction, after_construction, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_construction response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
            )
        row_after = after_construction["maps"][0]["items"][str(FIXTURE_ITEM_INDEX)]

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

        start_entry, click_entry = envelope["commands"]
        manifest = {
            "schema": "godot-building-construction/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "two-command construction transaction; the executed-legacy "
                "parity oracle for the Compatibility API v0 construction "
                "endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_construction_fixture.py"
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
                "cell": [FIXTURE_X, FIXTURE_Y],
                "actions": ["start", "click"],
                "target_rule": TARGET_RULE,
                "bounds_rule": "not applicable: a construction has no target cell "
                "of its own — the pair rewrites only the addressed row's "
                "timestamp and attribute bag, and the cell is the recorded "
                "anchor the capture pins",
                "derived": {
                    "command_order": [
                        construction_envelope.ACTIVATE_COMMAND,
                        construction_envelope.ADD_CLICK_COMMAND,
                    ],
                    "activate": {
                        "command": start_entry[1],
                        "args": start_entry[2],
                        "duration_status": "derived from committed content: the "
                        "addressed row's item's committed build_time, read "
                        "through config/main.json and never accepted from a "
                        "client; the committed configuration also records an "
                        "'activation' field, but using it would be a different "
                        "claim with no evidence, and a speedup-adjusted figure "
                        "would fabricate a price for a mechanism deliberately out "
                        "of scope",
                        "clearing_branch": "activate with a non-positive duration "
                        "would clear the row's WHOLE attribute bag "
                        "(command.py:425-427), destroying nc and any si entries; "
                        "this contract only ever sends the positive derived "
                        "duration and exposes no cancel action",
                        "resources_changed": start_entry[3],
                    },
                    "add_click": {
                        "command": click_entry[1],
                        "args": click_entry[2],
                        "counter_status": "established: add_click raises "
                        "attr['nc'] and seeds it to 1 when absent "
                        "(command.py:525-536; engine.py:125-130). The counter is "
                        "SEEDED by the purchase half — engine.map_add_item "
                        "writes attr['nc'] = 0 for a player == 1 item whose "
                        "config has clicks_to_build > 0 (engine.py:25-28) — and "
                        "the fresh corpus's row carries attr {} only because it "
                        "was placed before the corpus was recorded",
                        "threshold_status": "no server-side completion rule "
                        "exists: no branch compares nc with clicks_to_build, so "
                        "the threshold is the client's",
                        "resources_changed": click_entry[3],
                    },
                    "duration": FIXTURE_BUILD_TIME,
                    "duration_source": "item %d's committed build_time in "
                    "config/main.json" % FIXTURE_ITEM_ID,
                    "clicks_to_build": FIXTURE_CLICKS_TO_BUILD,
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "status": "established: the three commands' argument shapes "
                    "and effects, that they write only the row's timestamp and "
                    "attribute bag, that the click counter is seeded by the "
                    "purchase half, the cp/timestamp shape of an activation, "
                    "that a non-positive duration clears the whole bag, that no "
                    "server-side completion rule exists, and the resulting state "
                    "from this executed transaction. derived and never observed "
                    "from the Flash client: that a real construction sends these "
                    "commands, and that the duration a client sends is the "
                    "item's committed build_time rather than its activation "
                    "field or a speedup-adjusted figure. The committed "
                    "configuration records no price for building, so both derived "
                    "vectors are neutral and NO building cost is claimed",
                },
            },
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "row_before": list(row_before),
                "row_after": list(row_after),
                "entry_field_order": [
                    "item", "x", "y", "timestamp", "orientation", "store", "attr", "player",
                ],
                "placement_count_before": len(before_construction["maps"][0]["items"]),
                "placement_count_after": len(after_construction["maps"][0]["items"]),
                "key_reused": str(FIXTURE_ITEM_INDEX),
                "attr_before": list(row_before)[6],
                "attr_after": list(row_after)[6],
                "store_after": after_construction["maps"][0]["store"],
                "bought_units_before": before_construction["privateState"]["boughtUnits"],
                "bought_units_after": after_construction["privateState"]["boughtUnits"],
                "dead_heroes_after": after_construction["privateState"]["deadHeroes"],
                "resources_after": {
                    "xp": after_construction["maps"][0]["xp"],
                    "gold": after_construction["maps"][0]["gold"],
                    "wood": after_construction["maps"][0]["wood"],
                    "oil": after_construction["maps"][0]["oil"],
                    "steel": after_construction["maps"][0]["steel"],
                    "cash": after_construction["playerInfo"]["cash"],
                    "mana": after_construction["privateState"]["mana"],
                },
                "other_rows_unchanged": True,
                "private_state_unchanged": True,
                "player_info_unchanged": True,
                "building_cost_claimed": False,
                "speedups_in_scope": False,
                "friend_assist_in_scope": False,
                "cancel_action_offered": False,
                "construction_writes": [
                    "command.activate with a positive duration writes item[3] = "
                    "timestamp_now() and item[6]['cp'] = duration, and nothing "
                    "else (command.py:421-424)",
                    "command.add_click writes only item[6]['nc'] through "
                    "engine.add_click (command.py:533; engine.py:125-130)",
                    "engine.apply_resources applies the derived neutral delta on "
                    "both commands with max(..., 0), so no resource changes",
                    "no branch compares nc with clicks_to_build, and no branch "
                    "writes privateState, maps[0].store, or playerInfo",
                ],
            },
            "omitted_step": OMITTED_STEP,
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
                    "the envelope ts inside command_construction/request.json's "
                    "/form/data (and therefore that field's sha256 digest), "
                    "because ts is the current time",
                    "the constructed row's wall-clock start instant: "
                    "/maps/0/items/%d/3 in command_construction/after.json, and "
                    "the two manifest leaves derived from it — "
                    "/transaction/row_after/3 and "
                    "/transaction/steps/1/save_after_sha256" % FIXTURE_ITEM_INDEX,
                ],
                "documented_normalization": (
                    "construction parity compares the row's start time as a "
                    "positive integer greater than the before-state's, never by "
                    "value: legacy stamps it with timestamp_now() and the "
                    "remaining time is cp - (now - item[3]), a client "
                    "derivation no server branch ever computes; no other clock "
                    "field is written"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, and upgrade fixtures "
                    "are digest-pinned for the same reason."
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
            "capture: derived commands %s%s then %s%s, both resources %s"
            % (
                start_entry[1],
                start_entry[2],
                click_entry[1],
                click_entry[2],
                FIXTURE_EXPECTED_VECTOR,
            )
        )
        print(
            "capture: slot %d (%s) at cell %r constructed in place, placements "
            "%d -> %d, store %r, boughtUnits %r -> %r, deadHeroes %r"
            % (
                FIXTURE_ITEM_INDEX,
                FIXTURE_ITEM_NAME,
                [row_before[1], row_before[2]],
                len(before_construction["maps"][0]["items"]),
                len(after_construction["maps"][0]["items"]),
                after_construction["maps"][0]["store"],
                before_construction["privateState"]["boughtUnits"],
                after_construction["privateState"]["boughtUnits"],
                after_construction["privateState"]["deadHeroes"],
            )
        )
        print(
            "capture: constructed row %r (the timestamp is the documented "
            "time-dependent field: the construction's start instant)"
            % (list(row_after),)
        )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except construction_envelope.EnvelopeError as error:
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
