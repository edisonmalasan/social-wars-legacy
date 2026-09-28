#!/usr/bin/env python3
"""Capture the executed-legacy placement fixture: one real ``buy`` command.

What this does, in order (design D9; harness shared with the boot capture):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists,
   and takes the working-tree containment snapshot before anything runs.
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
     ``data`` envelope carrying exactly one ``buy`` command derived with
     :mod:`placement_envelope` from the fresh save's own state

   The fixture placement is House I (item id 1, ``costs={"w":30}``,
   2x2) anchored at ``(51,39)`` — documented as the Manhattan-nearest
   free 2x2 anchor to the Command Center (item 26) anchor ``(51,41)``,
   ties broken row-major (smallest y, then smallest x): the only free
   distance-2 candidates are ``(49,41)`` and ``(51,39)``.
6. Verifies the transaction structurally before publishing: the login
   step left the save byte-identical, the ``buy`` step mutated it, the
   new entry sits at the derived slot with the requested item/cell/team,
   and every resource changed by exactly the derived cost vector under
   the legacy ``max(..., 0)`` clamp (with ``boughtUnits`` gaining the
   item id, as legacy ``buy`` does for player team 1).
7. Stops the server, re-checks the working-tree containment snapshot,
   discards the disposable copy, and writes the fixtures under ``--out``
   (default: ``tests/fixtures/godot-building-placement/``).

Recorded requests and responses are sanitized (design D9): ``user_key``
is redacted, the disposable server's session cookie (``Cookie`` /
``Set-Cookie``) is redacted, and any non-empty ``accessToken`` would be
redacted — the capture crafts ``accessToken=""`` (a documented
placeholder, never a token value), so no recorded field ever carries a
secret. The live requests always send the real values; only the records
are redacted, which also keeps these fields byte-stable across reruns.

Containment (same contract as the boot capture):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change
  there fails the run with exit 6 before fixtures are written.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the boot capture harness):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed, returned an unexpected status, or the
      executed transaction did not match the derived envelope
6     Containment violation (working-tree bytes changed, or the disposable
      corpus saves changed during server startup / login)
7     Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_placement_fixture.py

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
import placement_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-placement"

# The fixture placement intent (design D9, verified against the fresh save:
# only free distance-2 anchors to the Command Center are (49,41) and
# (51,39); row-major tiebreak picks (51,39)).
FIXTURE_ITEM_ID = 1  # House I: costs {"w":30}, 2x2, min_level 1, in_store 1
FIXTURE_ANCHOR_X = 51
FIXTURE_ANCHOR_Y = 39
FIXTURE_ORIENTATION = 0
ANCHOR_RULE = (
    "Manhattan-nearest free 2x2 anchor to the Command Center (item id 26) "
    "anchor (51,41) in the committed fresh save, ties broken row-major "
    "(smallest y, then smallest x); the only free distance-2 candidates "
    "are (49,41) and (51,39), so the rule selects (51,39)"
)

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_buy")


# ------------------------------------------------------------- sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    """Redact secret-valued form fields before recording (design D9)."""
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact the disposable server's session cookie from recorded headers.

    The live request always sends the real cookie (the login step must
    behave like a logged-in client); only the *record* is redacted — it is
    an ephemeral token value of a dead disposable server, it can never be
    replayed (placement parity works from the intent, not over HTTP), and
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
    envelope = placement_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return placement_envelope.data_field(envelope)


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


def config_costs(disposable: Path, item_id: int) -> Any:
    """Raw config ``costs`` for one item, read from the disposable config.

    The executed server loaded exactly these bytes, so the derived envelope
    and the executed behavior share one configuration source.
    """
    config_path = disposable / "config" / "main.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        for entry in config["items"]:
            if int(entry["id"]) == item_id:
                return entry.get("costs")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read item %d costs: %s" % (item_id, error)
        )
    raise CaptureError(
        EXIT_ENVIRONMENT, "item %d is absent from the disposable config" % item_id
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
def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Every expectation is computed from the before-state and the derived
    vector under the legacy rules (``engine.apply_resources`` clamps,
    ``command.buy`` writes ``bought_unit_add`` for player team 1); any
    mismatch means the capture would publish a fixture that contradicts
    its own derivation, so the run fails with exit 5.
    """
    try:
        command_entry = envelope["commands"][0]
        args = command_entry[2]
        vector = command_entry[3]
        slot, item_id, x, y, player = args[0], args[1], args[2], args[3], args[4]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    entry = map_after["items"].get(str(slot))
    if not isinstance(entry, list) or len(entry) != 8:
        raise CaptureError(
            EXIT_REQUEST,
            "after-state has no eight-field entry at derived slot %d" % slot,
        )
    if [entry[0], entry[1], entry[2], entry[7]] != [item_id, x, y, player]:
        raise CaptureError(
            EXIT_REQUEST,
            "persisted entry %r does not match the derived [item, x, y, player]"
            % [entry[0], entry[1], entry[2], entry[7]],
        )
    if int(slot) <= max(int(key) for key in map_before["items"]):
        raise CaptureError(
            EXIT_REQUEST, "derived slot %d was already occupied" % slot
        )

    # Legacy apply_resources: max(current + delta, 0) per slot.
    resource_keys = {2: ("maps", "gold"), 3: ("maps", "wood"), 4: ("maps", "oil"),
                     5: ("maps", "steel"), 1: ("maps", "xp")}
    for index, (scope, key) in resource_keys.items():
        current = map_before[key]
        expected = max(current + vector[index], 0)
        observed = map_after[key]
        if observed != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (key, current, observed, expected),
            )
    expected_cash = max(before["playerInfo"]["cash"] + vector[6], 0)
    if after["playerInfo"]["cash"] != expected_cash:
        raise CaptureError(
            EXIT_REQUEST,
            "cash changed unexpectedly: %r -> %r (expected %r)"
            % (before["playerInfo"]["cash"], after["playerInfo"]["cash"], expected_cash),
        )
    # Legacy command.buy: bought_unit_add(save, item_id) for player team 1.
    bought_before = list(before["privateState"].get("boughtUnits", []))
    bought_after = list(after["privateState"].get("boughtUnits", []))
    expected_bought = bought_before if item_id in bought_before else bought_before + [item_id]
    if bought_after != expected_bought:
        raise CaptureError(
            EXIT_REQUEST,
            "boughtUnits changed unexpectedly: %r -> %r (expected %r)"
            % (bought_before, bought_after, expected_bought),
        )


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy placement fixture "
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

    # Fixtures are staged OUTSIDE the working tree and published only after
    # every check passed, so a failed run writes nothing into the repo.
    staging = Path(tempfile.mkdtemp(prefix="compat-placement-capture-staging-"))
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
                "Login form (USERID + GAMEVERSION) exactly as the boot capture "
                "sends it; recorded for session fidelity — command.php performs "
                "no session validation. user_key would be redacted if present.",
            )
        )

        # --- derive the buy envelope from the before-state -----------------
        costs = config_costs(disposable, FIXTURE_ITEM_ID)
        before_buy = canonical_save(save_path)
        envelope = placement_envelope.build_envelope(
            item_id=FIXTURE_ITEM_ID,
            x=FIXTURE_ANCHOR_X,
            y=FIXTURE_ANCHOR_Y,
            costs=costs,
            items=before_buy["maps"][0]["items"],
            orientation=FIXTURE_ORIENTATION,
        )
        data = placement_envelope.data_field(envelope)
        buy_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the buy command --------------------------------------
        buy_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(buy_form),
            cookie=cookie,
            timeout=30.0,
        )
        if buy_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_buy: expected HTTP 200, got %r" % buy_result["status"],
            )
        after_buy = canonical_save(save_path)
        if save_bytes_sha(before_buy) == save_bytes_sha(after_buy):
            raise CaptureError(
                EXIT_REQUEST,
                "command_buy did not persist any save change; refusing to "
                "publish a non-transaction fixture",
            )
        body = buy_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_buy",
                buy_result,
                body,
                before_buy,
                after_buy,
                buy_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying one buy command; "
                "user_key is redacted in this record (design D9); accessToken "
                "is the crafted empty placeholder, never a token value.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_buy, after_buy, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_buy response is not the legacy {\"result\": \"success\"}: %r"
                % (response_payload,),
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

        if not args.keep_disposable and disposable is not None:
            shutil.rmtree(disposable, ignore_errors=False)
            disposable = None

        manifest = {
            "schema": "godot-building-placement/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "buy transaction; the executed-legacy parity oracle for the "
                "Compatibility API v0 placement endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_placement_fixture.py"
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
                "item_id": FIXTURE_ITEM_ID,
                "item_name": "House I",
                "anchor": [FIXTURE_ANCHOR_X, FIXTURE_ANCHOR_Y],
                "orientation": FIXTURE_ORIENTATION,
                "anchor_rule": ANCHOR_RULE,
                "grid_extent": placement_envelope.GRID_EXTENT,
                "bounds_rule": "anchor-based 0..99; footprints may extend past "
                "the edge (the fresh save's Harbour already does)",
                "costs_raw": costs,
                "derived": {
                    "slot": envelope["commands"][0][2][0],
                    "player_team": envelope["commands"][0][2][4],
                    "resources_changed": envelope["commands"][0][3],
                    "envelope_keys": sorted(envelope),
                    "status": "derived-provisional (design D4): the Flash client "
                    "is never executed, so its envelope is unobservable",
                },
            },
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "persisted_slot": str(envelope["commands"][0][2][0]),
                "entry_field_order": [
                    "item", "x", "y", "timestamp", "orientation", "store", "attr", "player",
                ],
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures."
                ),
                "pre_run": pre_groups,
                "post_run": post_groups,
                "pre_combined_sha256": pre_combined,
                "post_combined_sha256": post_combined,
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
                "capture:   %-12s %s %s -> %d (%d bytes, save unchanged: %s)"
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
            "capture: derived slot %d, resources %s"
            % (
                envelope["commands"][0][2][0],
                envelope["commands"][0][3],
            )
        )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except placement_envelope.EnvelopeError as error:
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
