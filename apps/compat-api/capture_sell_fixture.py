#!/usr/bin/env python3
"""Capture the executed-legacy sell fixture: one real ``sell`` command.

What this does, in order (design D10; harness shared with the boot,
placement, purchase, and move captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, and
   move fixtures.
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
     ``data`` envelope carrying exactly one ``sell`` command derived with
     :mod:`sell_envelope`

   The fixture sell is the Turret I (item id 22, 1x1) at map slot ``20``,
   anchored at ``(41,48)`` in the fresh-player corpus.  Slot 20 is the
   *second* Turret I in map-slot order, chosen so this fixture's target
   differs from the move fixture's slot 11 and the two stay independently
   readable.
6. Verifies the transaction structurally before publishing: the login
   step left the save byte-identical, the sell step mutated it, the row at
   key ``"20"`` is **absent** afterwards, **every** other placement row, the
   storage mapping, the whole ``privateState`` (including ``deadHeroes``),
   ``boughtUnits``, every other map field, and every resource are unchanged
   (the derived vector is neutral), and the placement count drops ``40 ->
   39``.  The recorded request itself is pinned: exactly one command,
   ``[0, "sell", [20, ""], [0,0,0,0,0,0,0,0]]``.
7. Stops the server, re-checks the working-tree containment snapshot and the
   committed boot/placement/purchase/move fixture digests, discards the
   disposable copy, and writes the fixtures under ``--out``
   (default: ``tests/fixtures/godot-building-sell/``).

Recorded requests and responses are sanitized (design D10): ``user_key``
is redacted, the disposable server's session cookie (``Cookie`` /
``Set-Cookie``) is redacted, and any non-empty ``accessToken`` would be
redacted — the capture crafts ``accessToken=""`` (a documented
placeholder, never a token value), so no recorded field ever carries a
secret. The live requests always send the real values; only the records
are redacted, which also keeps these fields byte-stable across reruns.

Containment (same contract as the boot, placement, purchase, and move
captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change
  there fails the run with exit 6 before fixtures are written. The committed
  boot, placement, purchase, and move fixtures are digest-pinned for the
  same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the boot, placement, purchase, and move capture
harnesses):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed, returned an unexpected status, or the
      executed transaction did not match the derived envelope
6     Containment violation (working-tree bytes changed, the committed
      boot/placement/purchase/move fixtures changed, or the disposable
      corpus saves changed during server startup / login)
7     Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_sell_fixture.py

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
import sell_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-sell"

# The fixture sell intent (design D10, verified against the fresh save: slot
# "20" holds [22, 41, 48, 0, 0, [], {}, 1] and is the second Turret I in
# map-slot order, so this fixture's target differs from the move fixture's
# slot 11 and the two stay independently readable).
FIXTURE_ITEM_INDEX = 20
FIXTURE_ITEM_ID = 22  # Turret I: 1x1 building, the row sold by the fixture
FIXTURE_ITEM_NAME = "Turret I"
FIXTURE_X = 41
FIXTURE_Y = 48
FIXTURE_REASON = ""  # the derived reason (design D3), never chosen by a client
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 39
TARGET_RULE = (
    "the Turret I (item id 22) at map slot 20 anchored at (41,48) in the "
    "committed fresh save — the second Turret I in map-slot order, chosen so "
    "this fixture's target differs from the move fixture's slot 11 and the "
    "two fixtures stay independently readable; a sell has no target cell"
)

# Committed fixtures that must be byte-identical across this run.
PROTECTED_FIXTURES = (
    ("tests/fixtures/godot-compatibility-boot", "godot-compatibility-boot"),
    ("tests/fixtures/godot-building-placement", "godot-building-placement"),
    ("tests/fixtures/godot-item-purchase", "godot-item-purchase"),
    ("tests/fixtures/godot-building-move", "godot-building-move"),
)

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_sell")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5}


# ------------------------------------------------------------- sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    """Redact secret-valued form fields before recording (design D10)."""
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact the disposable server's session cookie from recorded headers.

    The live request always sends the real cookie (the login step must
    behave like a logged-in client); only the *record* is redacted — it is
    an ephemeral token value of a dead disposable server, it can never be
    replayed (sell parity works from the intent, not over HTTP), and
    redacting it keeps reruns byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the
    exact sent bytes; this keeps the record secret-free even if that
    placeholder ever changes.
    """
    envelope = sell_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return sell_envelope.data_field(envelope)


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

    The command choice, the two argument values (the legacy map index and the
    derived empty reason), and the neutral price vector are all
    derived-provisional (design D1/D2/D3/D7): Flash is never executed, so
    they are pinned here against the committed config and fresh save
    instead, and any drift fails the run rather than silently publishing a
    different fixture.
    """
    command_entry = envelope["commands"][0]
    if len(envelope["commands"]) != 1:
        raise CaptureError(EXIT_REQUEST, "envelope must carry exactly one command")
    if sorted(envelope) != sorted(sell_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    if command_entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0, got %r" % (command_entry[0],))
    if command_entry[1] != sell_envelope.SELL_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "command must be %r, got %r"
            % (sell_envelope.SELL_COMMAND, command_entry[1]),
        )
    expected_args = [FIXTURE_ITEM_INDEX, FIXTURE_REASON]
    if command_entry[2] != expected_args:
        raise CaptureError(
            EXIT_REQUEST,
            "sell args must be %r, got %r" % (expected_args, command_entry[2]),
        )
    if command_entry[2][1] != sell_envelope.DEFAULT_REASON:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived reason must be the empty string, got %r" % (command_entry[2][1],),
        )
    if command_entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "derived neutral price vector drifted: %r (expected %r)"
            % (command_entry[3], FIXTURE_EXPECTED_VECTOR),
        )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived vector
    under the legacy rules: ``command.sell`` deletes exactly the addressed row
    with ``engine.map_delete_item`` (``command.py:162``, ``engine.py:48-52``)
    and writes nothing else, and ``engine.apply_resources``
    (``engine.py:251-271``) applies the neutral vector with a per-slot
    ``max(..., 0)``.  The derived reason is not ``"KILL"``, so
    ``push_dead_unit`` never runs and ``privateState`` must be untouched.
    Any mismatch means the capture would publish a fixture that contradicts
    its own derivation, so the run fails with exit 5.
    """
    try:
        command_entry = envelope["commands"][0]
        args = command_entry[2]
        vector = command_entry[3]
        item_index, reason = args[0], args[1]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    if reason != sell_envelope.DEFAULT_REASON:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed envelope's reason is not the derived empty string: %r" % (reason,),
        )

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

    # The single legacy write: the addressed row is gone, and exactly it.
    key = str(item_index)
    row_before = items_before.get(key)
    if not isinstance(row_before, list):
        raise CaptureError(
            EXIT_REQUEST, "no placement row at index %d to sell" % item_index
        )
    if len(row_before) != 8:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %d is not an eight-field entry" % item_index,
        )
    if key in items_after:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %d survived the sell" % item_index,
        )
    if int(row_before[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "sold row is item %r, not the fixture item %d"
            % (row_before[0], FIXTURE_ITEM_ID),
        )
    if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "sold row is anchored at %r, not the documented %r"
            % ([row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
        )

    expected_keys = sorted(set(items_before) - {key}, key=int)
    if sorted(items_after, key=int) != expected_keys:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].item keys changed beyond the single removed row %r" % (key,),
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS_AFTER),
        )

    # Every other row is byte-identical: a sell touches exactly one entry.
    for other in items_before:
        if other == key:
            continue
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; sell deletes only the addressed row" % other,
            )

    # Legacy apply_resources: max(current + delta, 0) per slot.  The derived
    # vector is neutral, so no resource may move at all.
    for key_name, index in sorted(RESOURCE_VECTOR_SLOTS.items()):
        current = map_before[key_name]
        expected = max(current + vector[index], 0)
        observed = map_after[key_name]
        if observed != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (key_name, current, observed, expected),
            )
    expected_cash = max(before["playerInfo"]["cash"] + vector[6], 0)
    if after["playerInfo"]["cash"] != expected_cash:
        raise CaptureError(
            EXIT_REQUEST,
            "cash changed unexpectedly: %r -> %r (expected %r)"
            % (before["playerInfo"]["cash"], after["playerInfo"]["cash"], expected_cash),
        )
    if after["privateState"]["mana"] != max(before["privateState"]["mana"] + vector[7], 0):
        raise CaptureError(
            EXIT_REQUEST,
            "mana changed unexpectedly: %r -> %r"
            % (before["privateState"]["mana"], after["privateState"]["mana"]),
        )

    # A sell stores nothing, records no purchase, and — because the reason is
    # the derived empty string, never "KILL" — never routes the row through
    # push_dead_unit, so the whole privateState (deadHeroes included) stands.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; sell writes storage never")
    if after["privateState"] != before["privateState"]:
        changed = sorted(
            name
            for name in set(before["privateState"]) | set(after["privateState"])
            if before["privateState"].get(name) != after["privateState"].get(name)
        )
        raise CaptureError(
            EXIT_REQUEST,
            "privateState changed (%s); the derived reason must not reach "
            "push_dead_unit" % ", ".join(changed),
        )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(EXIT_REQUEST, "playerInfo changed; sell writes none of it")
    for field in sorted(set(map_before) | set(map_after)):
        if field in ("items", "store", "xp", "gold", "wood", "oil", "steel"):
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; sell writes only the addressed row's removal" % field,
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
        description="Capture the executed-legacy sell fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-sell-capture-staging-"))
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
                "placement, purchase, and move captures send it; recorded for "
                "session fidelity — command.php performs no session "
                "validation. user_key would be redacted if present.",
            )
        )

        # --- derive the sell envelope from the before-state ----------------
        before_sell = canonical_save(save_path)
        row_before = before_sell["maps"][0]["items"].get(str(FIXTURE_ITEM_INDEX))
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
        envelope = sell_envelope.build_envelope(item_index=FIXTURE_ITEM_INDEX)
        verify_envelope(envelope)
        data = sell_envelope.data_field(envelope)
        sell_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the sell command --------------------------------------
        sell_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(sell_form),
            cookie=cookie,
            timeout=30.0,
        )
        if sell_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_sell: expected HTTP 200, got %r" % sell_result["status"],
            )
        after_sell = canonical_save(save_path)
        if save_bytes_sha(before_sell) == save_bytes_sha(after_sell):
            raise CaptureError(
                EXIT_REQUEST,
                "command_sell did not persist any save change; refusing to "
                "publish a non-transaction fixture",
            )
        body = sell_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_sell",
                sell_result,
                body,
                before_sell,
                after_sell,
                sell_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying one sell command "
                "whose two arguments are the map index and the derived empty "
                "reason (design D3 — never chosen by a client, so the combat "
                'KILL reason and push_dead_unit are unreachable), and whose '
                "resources_changed is the neutral all-zero vector; user_key is "
                "redacted in this record (design D10); accessToken is the "
                "crafted empty placeholder, never a token value.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_sell, after_sell, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_sell response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
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

        command_entry = envelope["commands"][0]
        manifest = {
            "schema": "godot-building-sell/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "sell transaction; the executed-legacy parity oracle for the "
                "Compatibility API v0 sell endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_sell_fixture.py"
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
                "from_cell": [FIXTURE_X, FIXTURE_Y],
                "to_cell": None,
                "target_rule": TARGET_RULE,
                "bounds_rule": "not applicable: a sell has no target cell and no "
                "grid input, so nothing here is bounds-checked",
                "derived": {
                    "command": command_entry[1],
                    "args": command_entry[2],
                    "reason": command_entry[2][1],
                    "reason_status": "derived, never chosen (design D3): the "
                    "endpoint accepts no reason from the client, so no client "
                    'can claim "KILL" and reach push_dead_unit',
                    "resources_changed": command_entry[3],
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "status": "derived-provisional (design D1/D2/D3/D7): the "
                    "Flash client is never executed, so its envelope, its sell "
                    "command, its argument values, and any refund it sends are "
                    "unobservable; the committed configuration records no "
                    "building-sale refund rule, so the derived vector is "
                    "neutral and no refund is claimed",
                },
            },
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "removed_row_before": list(row_before),
                "removed_row_after": None,
                "entry_field_order": [
                    "item", "x", "y", "timestamp", "orientation", "store", "attr", "player",
                ],
                "placement_count_before": len(before_sell["maps"][0]["items"]),
                "placement_count_after": len(after_sell["maps"][0]["items"]),
                "store_after": after_sell["maps"][0]["store"],
                "bought_units_after": after_sell["privateState"]["boughtUnits"],
                "dead_heroes_after": after_sell["privateState"]["deadHeroes"],
                "resources_after": {
                    "xp": after_sell["maps"][0]["xp"],
                    "gold": after_sell["maps"][0]["gold"],
                    "wood": after_sell["maps"][0]["wood"],
                    "oil": after_sell["maps"][0]["oil"],
                    "steel": after_sell["maps"][0]["steel"],
                    "cash": after_sell["playerInfo"]["cash"],
                    "mana": after_sell["privateState"]["mana"],
                },
                "other_rows_unchanged": True,
                "private_state_unchanged": True,
                "refund_claimed": False,
                "state_writes": [
                    "command.sell deletes exactly the addressed row with "
                    "engine.map_delete_item (command.py:162; engine.py:48-52) "
                    "and writes nothing else",
                    "the derived reason is not 'KILL', so push_dead_unit never "
                    "runs and privateState (deadHeroes included) is untouched",
                    "engine.apply_resources applies the derived neutral delta "
                    "with max(..., 0), so no resource changes",
                ],
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, and move fixtures are digest-pinned "
                    "for the same reason."
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
                "capture:   %-14s %s %s -> %d (%d bytes, save unchanged: %s)"
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
            "capture: derived command %s%s, resources %s"
            % (
                command_entry[1],
                command_entry[2],
                command_entry[3],
            )
        )
        print(
            "capture: slot %d (%s) cell %r removed, placements %d -> %d, store "
            "%r, boughtUnits %r, deadHeroes %r"
            % (
                FIXTURE_ITEM_INDEX,
                FIXTURE_ITEM_NAME,
                [row_before[1], row_before[2]],
                len(before_sell["maps"][0]["items"]),
                len(after_sell["maps"][0]["items"]),
                after_sell["maps"][0]["store"],
                after_sell["privateState"]["boughtUnits"],
                after_sell["privateState"]["deadHeroes"],
            )
        )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except sell_envelope.EnvelopeError as error:
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
