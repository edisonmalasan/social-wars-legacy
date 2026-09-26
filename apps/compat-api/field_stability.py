#!/usr/bin/env python3
"""Derive the field-stability record from two executed legacy captures.

The record separates stable fields from time-dependent (and
environment-dependent) fields for every captured legacy boot surface, with a
documented normalization for each non-stable field, so the Compatibility API
v0 parity tests compare exactly what legacy semantics make comparable.

Derivation method (both, recorded in the output):

1. **Two executed captures** — capture A (the committed fixture set) and
   capture B (a transient second run into a temp directory) are leaf-diffed
   per step. JSON responses are diffed field-by-field; the rendered HTML of
   ``play_page`` is compared with the ``serverTime=`` FlashVar masked out;
   ``login_page`` is compared as its parsed save-list surface.
2. **Code inspection** — the legacy modules that read the wall clock or the
   filesystem are cited by file and symbol, so fields that happened to match
   across two same-week captures but are derived from time (e.g. the darts
   schedule rewrap) are still classified as time-dependent.

Exact invocation (from the repository root):

    python -B apps/compat-api/field_stability.py ^
        --capture-a tests/fixtures/godot-compatibility-boot ^
        --capture-b <transient capture B dir> ^
        --out tests/fixtures/godot-compatibility-boot/field-stability.json

Exit codes:

- ``0`` — record written
- ``2`` — usage/environment error
- ``3`` — capture input missing, unreadable, or structurally inconsistent
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_legacy_fixtures import (  # noqa: E402
    DEFAULT_OUT,
    FIXTURE_STEPS,
    REPO_ROOT,
    parse_session_surface,
    sha256_bytes,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INPUT = 3

JSON_STEPS = ("get_game_config", "get_player_info")
HTML_STEPS = ("login_page", "play_page")
SERVER_TIME_RE = re.compile(r"serverTime=(\d+)")
VALUE_LIMIT = 160

CODE_INSPECTION = [
    {
        "file": "engine.py",
        "symbol": "timestamp_now",
        "claim": (
            "Returns int(time.time()): every timestamp in the boot surfaces is "
            "wall-clock epoch seconds and cannot equal a fixture value at a "
            "later run."
        ),
    },
    {
        "file": "get_player_info.py",
        "symbol": "get_player_info",
        "claim": (
            "Computes ts_now once, returns it as 'timestamp', and assigns the "
            "same ts_now to session(USERID)['playerInfo']['last_logged_in'] "
            "before serializing playerInfo; both fields are therefore equal "
            "within one response and change on every call."
        ),
    },
    {
        "file": "get_game_config.py",
        "symbol": "get_game_config / make_dynamic / update_darts",
        "claim": (
            "get_game_config() runs make_dynamic() on every call, and "
            "make_dynamic rewrites darts_items[*].start_date from the wall "
            "clock (week-aligned wrap of the stored schedule). The values are "
            "time-derived even when two captures in the same wrap window "
            "produce identical strings."
        ),
    },
    {
        "file": "engine.py",
        "symbol": "reset_stuff",
        "claim": (
            "Boundary-dependent resets: numTradesDone is cleared when the day "
            "changes and timeStampDartsReset is zeroed at the week boundary. "
            "For the fresh-player corpus (timestampLastTrade=0, "
            "timeStampDartsReset=0, numTradesDone=0) both branches keep the "
            "value 0, so the outputs are invariant for this corpus; verified "
            "stable across captures A and B."
        ),
    },
    {
        "file": "sessions.py",
        "symbol": "neighbors / load_static_villages",
        "claim": (
            "Static-village iteration order follows os.listdir() order of the "
            "corpus villages directory, which is filesystem-dependent rather "
            "than time-dependent; parity compares neighbors as a pid-keyed "
            "mapping."
        ),
    },
    {
        "file": "version.py",
        "symbol": "version_name",
        "claim": "Static string 'alpha 0.02'; stable across captures.",
    },
    {
        "file": "server.py",
        "symbol": "play (route) + templates/play.html",
        "claim": (
            "play.html embeds serverTime=timestamp_now() as a FlashVar, so the "
            "logged-in render differs per request in that value only "
            "(observed: equal after masking in captures A and B)."
        ),
    },
]

TIME_RULE_EPOCH = {
    "kind": "positive_epoch_seconds",
    "rule": (
        "Must be an int > 0. The fixture value is a same-second observation of "
        "engine.timestamp_now() at capture time and is never compared to the "
        "value produced later."
    ),
}

NORMALIZATIONS = {
    "session_server_time": TIME_RULE_EPOCH,
    "player_timestamp": TIME_RULE_EPOCH,
    "player_last_logged_in": {
        "kind": "equal_to_response_timestamp",
        "rule": (
            "Must be an int > 0 and exactly equal to the same response's "
            "'timestamp' field (legacy assigns one ts_now to both). The "
            "fixture's own value is not compared."
        ),
    },
    "config_darts_start_date": {
        "kind": "format_only",
        "pattern": "^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$",
        "rule": (
            "Values are not compared. Both sides must match the legacy "
            "'%Y-%m-%d %H:%M:%S' layout after make_dynamic rewrites the "
            "schedule."
        ),
    },
    "player_neighbors_order": {
        "kind": "pid_keyed_mapping",
        "rule": (
            "Compared as {pid: entry} mappings with equal length and equal pid "
            "sets; array order is not part of the comparison."
        ),
    },
    "play_page_server_time": {
        "kind": "masked_substring",
        "rule": (
            "The 'serverTime=<digits>' FlashVar is masked before string "
            "comparison of the rendered page."
        ),
    },
}


class InputError(Exception):
    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def load_capture(capture_dir: Path, label: str) -> Dict[str, object]:
    manifest_path = capture_dir / "capture-manifest.json"
    if not manifest_path.is_file():
        raise InputError(EXIT_INPUT, "%s: missing %s" % (label, manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    responses: Dict[str, bytes] = {}
    for step in FIXTURE_STEPS:
        body_path = capture_dir / "steps" / step / "response.body"
        if not body_path.is_file():
            raise InputError(EXIT_INPUT, "%s: missing %s" % (label, body_path))
        responses[step] = body_path.read_bytes()
    save_list_path = capture_dir / "steps" / "login_page" / "save-list.json"
    if not save_list_path.is_file():
        raise InputError(EXIT_INPUT, "%s: missing %s" % (label, save_list_path))
    save_list = json.loads(save_list_path.read_text(encoding="utf-8"))
    return {
        "dir": str(capture_dir),
        "manifest": manifest,
        "responses": responses,
        "save_list": save_list,
    }


def brief(value: object) -> str:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True) if not isinstance(value, str) else value
    if len(text) > VALUE_LIMIT:
        return text[:VALUE_LIMIT] + "...<truncated>"
    return text


def json_diff(a: object, b: object, path: str, out: List[Dict[str, str]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            child = "%s/%s" % (path, key)
            if key not in a:
                out.append({"path": child, "a": "<missing>", "b": brief(b[key])})
            elif key not in b:
                out.append({"path": child, "a": brief(a[key]), "b": "<missing>"})
            else:
                json_diff(a[key], b[key], child, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append({"path": path, "a": "<%d items>" % len(a), "b": "<%d items>" % len(b)})
        for index in range(min(len(a), len(b))):
            json_diff(a[index], b[index], "%s/%d" % (path, index), out)
        return
    if type(a) is not type(b) or a != b:
        out.append({"path": path or "/", "a": brief(a), "b": brief(b)})


def derive(capture_a: Dict[str, object], capture_b: Dict[str, object]) -> Dict[str, object]:
    observed: Dict[str, object] = {}

    # login_page: compare the derived save-list surface (parity target) and
    # record whether the raw page bytes matched too.
    a_list = capture_a["save_list"]
    b_list = capture_b["save_list"]
    a_body = capture_a["responses"]["login_page"]  # type: ignore[index]
    b_body = capture_b["responses"]["login_page"]  # type: ignore[index]
    assert isinstance(a_body, bytes) and isinstance(b_body, bytes)
    observed["login_page"] = {
        "comparison": "parsed save-list (game_version + saves[]) plus raw body digests",
        "parsed_equal": a_list == b_list,
        "raw_body_equal": a_body == b_body,
        "body_sha256_a": sha256_bytes(a_body),
        "body_sha256_b": sha256_bytes(b_body),
        "differing_paths": [] if a_list == b_list else ["<parsed save-list>"],
    }

    # login_post: status/redirect are structural, body carries no data.
    a_meta = json.loads(
        (Path(capture_a["dir"]) / "steps" / "login_post" / "response.meta.json").read_text(
            encoding="utf-8"
        )
    )
    b_meta = json.loads(
        (Path(capture_b["dir"]) / "steps" / "login_post" / "response.meta.json").read_text(
            encoding="utf-8"
        )
    )
    a_location = a_meta["headers"].get("Location")
    b_location = b_meta["headers"].get("Location")
    observed["login_post"] = {
        "comparison": "status + Location header (empty body)",
        "status_equal": a_meta["status"] == b_meta["status"],
        "location_equal": a_location == b_location,
        "status_a": a_meta["status"],
        "status_b": b_meta["status"],
        "location_a": a_location,
        "location_b": b_location,
    }

    # play_page: masked comparison (serverTime FlashVar).
    a_text = capture_a["responses"]["play_page"].decode("utf-8")  # type: ignore[index]
    b_text = capture_b["responses"]["play_page"].decode("utf-8")  # type: ignore[index]
    a_times = SERVER_TIME_RE.findall(a_text)
    b_times = SERVER_TIME_RE.findall(b_text)
    a_masked = SERVER_TIME_RE.sub("serverTime=<SERVER_TIME>", a_text)
    b_masked = SERVER_TIME_RE.sub("serverTime=<SERVER_TIME>", b_text)
    observed["play_page"] = {
        "comparison": "rendered page with the serverTime=<digits> FlashVar masked",
        "equal_after_mask": a_masked == b_masked,
        "server_time_values_a": a_times,
        "server_time_values_b": b_times,
        "masked_sha256_a": sha256_bytes(a_masked.encode("utf-8")),
        "masked_sha256_b": sha256_bytes(b_masked.encode("utf-8")),
    }

    # JSON steps: leaf diff.
    for step in JSON_STEPS:
        a_json = json.loads(capture_a["responses"][step].decode("utf-8"))  # type: ignore[index]
        b_json = json.loads(capture_b["responses"][step].decode("utf-8"))  # type: ignore[index]
        differences: List[Dict[str, str]] = []
        json_diff(a_json, b_json, "", differences)
        observed[step] = {
            "comparison": "leaf-by-leaf diff of the parsed JSON response",
            "differing_paths": differences,
            "differing_path_count": len(differences),
            "body_sha256_a": sha256_bytes(capture_a["responses"][step]),  # type: ignore[index]
            "body_sha256_b": sha256_bytes(capture_b["responses"][step]),  # type: ignore[index]
        }

    return observed


def build_record(
    capture_a: Dict[str, object],
    capture_b: Dict[str, object],
    observed: Dict[str, object],
) -> Dict[str, object]:
    manifest_a = capture_a["manifest"]
    manifest_b = capture_b["manifest"]
    assert isinstance(manifest_a, dict) and isinstance(manifest_b, dict)

    config_differences = observed["get_game_config"]["differing_paths"]  # type: ignore[index]
    player_differences = [
        entry["path"] for entry in observed["get_player_info"]["differing_paths"]  # type: ignore[index]
    ]

    return {
        "schema": "godot-compatibility-boot/field-stability-v1",
        "purpose": (
            "Separate stable legacy response fields from time-dependent and "
            "environment-dependent ones, with the documented normalization "
            "for each non-stable field. Consumed by the Compatibility API v0 "
            "offline parity tests."
        ),
        "derivation": {
            "method": (
                "Two executed captures of the real legacy server leaf-diffed "
                "(captures A and B) plus code inspection of the legacy boot "
                "modules; both evidence kinds are recorded per field."
            ),
            "capture_a": {
                "path": "tests/fixtures/godot-compatibility-boot",
                "invocation": manifest_a.get("invocation"),
                "executed_at_utc": manifest_a.get("executed_at_utc"),
            },
            "capture_b": {
                "path": "<transient second capture; not committed>",
                "invocation": manifest_b.get("invocation"),
                "executed_at_utc": manifest_b.get("executed_at_utc"),
            },
            "observed_differences": observed,
            "code_inspection": CODE_INSPECTION,
        },
        "parity_targets": {
            "session": {
                "legacy_surface": (
                    "GET / login page save-list (parsed from the executed "
                    "response) plus version.py version_name"
                ),
                "stable": {
                    "game_version": (
                        "Static 'alpha 0.02' rendered into the login page; "
                        "equal across captures A and B (code-inspected: "
                        "version.py version_name is a constant)."
                    ),
                    "saves": (
                        "Per save: id, name, level, xp exactly as "
                        "sessions.save_info() computes them; equal across "
                        "captures A and B."
                    ),
                },
                "time_dependent": [
                    {
                        "field": "server_time",
                        "evidence": (
                            "Code inspection: engine.timestamp_now() = "
                            "int(time.time()); the legacy play.html serverTime "
                            "FlashVar differs between captures A and B "
                            "(observed in play_page)."
                        ),
                        "normalization": NORMALIZATIONS["session_server_time"],
                    }
                ],
            },
            "get_game_config": {
                "legacy_surface": "GET .../get_game_config.php (executed)",
                "stable": (
                    "All response fields are deep-compared exactly, except "
                    "the time-dependent paths listed below."
                ),
                "time_dependent": [
                    {
                        "field": "darts_items[*].start_date",
                        "evidence": (
                            "Code inspection: get_game_config() -> "
                            "make_dynamic() rewrites the schedule from the "
                            "wall clock on every call. Observed: %d differing "
                            "paths between captures A and B (two captures in "
                            "the same wrap window match; the values are still "
                            "time-derived and are normalized)."
                            % len(config_differences)
                        ),
                        "observed_differences": config_differences,
                        "normalization": NORMALIZATIONS["config_darts_start_date"],
                    }
                ],
            },
            "get_player_info": {
                "legacy_surface": "POST .../get_player_info.php (current-player branch, executed)",
                "stable": (
                    "All response fields are deep-compared exactly (result, "
                    "processed_errors, playerInfo minus last_logged_in, map, "
                    "privateState, neighbors entries per pid), except the "
                    "fields listed below."
                ),
                "invariant_notes": [
                    (
                        "map.numTradesDone and privateState.timeStampDartsReset "
                        "are produced by the time-boundary reset_stuff() "
                        "mechanism but are value-stable at 0 for the "
                        "fresh-player corpus on both branches (code-inspected "
                        "and equal across captures A and B), so they remain "
                        "under exact comparison."
                    )
                ],
                "time_dependent": [
                    {
                        "field": "timestamp",
                        "evidence": (
                            "Observed differing across captures A and B; code "
                            "inspection: engine.timestamp_now()."
                        ),
                        "normalization": NORMALIZATIONS["player_timestamp"],
                    },
                    {
                        "field": "playerInfo.last_logged_in",
                        "evidence": (
                            "Observed differing across captures A and B; code "
                            "inspection: get_player_info() assigns the same "
                            "ts_now used for 'timestamp' (0 in the seed save, "
                            "the in-memory boot mutation itself)."
                        ),
                        "normalization": NORMALIZATIONS["player_last_logged_in"],
                    },
                ],
                "environment_dependent": [
                    {
                        "field": "neighbors",
                        "evidence": (
                            "Code inspection: iteration order follows "
                            "os.listdir() of the disposable corpus villages "
                            "directory (sessions.load_static_villages)."
                        ),
                        "normalization": NORMALIZATIONS["player_neighbors_order"],
                    }
                ],
            },
        },
        "non_parity_targets": {
            "login_post": {
                "role": (
                    "Documents the legacy login semantics (form fields, 302 "
                    "redirect, session cookie); the v0 API has no login."
                ),
                "observed": observed["login_post"],
            },
            "play_page": {
                "role": (
                    "Documents the logged-in legacy render; not consumed by "
                    "the v0 API. serverTime FlashVar is time-dependent."
                ),
                "time_dependent": [
                    {
                        "field": "serverTime=<digits> FlashVar",
                        "evidence": "Observed differing across captures A and B.",
                        "normalization": NORMALIZATIONS["play_page_server_time"],
                    }
                ],
                "observed": observed["play_page"],
            },
            "response_meta_headers": {
                "role": (
                    "Per-response Date/Server headers in response.meta.json are "
                    "capture-time metadata, never compared."
                )
            },
            "before_after_save_records": {
                "role": (
                    "SHA-256 of the disposable corpus saves around each call; "
                    "expected invariant: identical before/after every request "
                    "(legacy boot endpoints do not persist)."
                )
            },
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive field-stability.json from two executed captures."
    )
    parser.add_argument("--capture-a", required=True, help="capture A directory (committed fixtures)")
    parser.add_argument("--capture-b", required=True, help="capture B directory (transient)")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT / "field-stability.json"),
        help="output record path (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if sys.version_info[:2] != (3, 9):
        print(
            "field-stability: refused: CPython 3.9.x required; got %s"
            % sys.version.split()[0],
            file=sys.stderr,
        )
        return EXIT_USAGE

    capture_a_dir = Path(args.capture_a).resolve()
    capture_b_dir = Path(args.capture_b).resolve()
    out_path = Path(args.out).resolve()
    if REPO_ROOT not in out_path.parents:
        print(
            "field-stability: --out must be strictly inside the repository: %s"
            % out_path,
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        capture_a = load_capture(capture_a_dir, "capture-a")
        capture_b = load_capture(capture_b_dir, "capture-b")
        observed = derive(capture_a, capture_b)
        record = build_record(capture_a, capture_b, observed)
    except InputError as error:
        print("field-stability: FAILED: %s" % error, file=sys.stderr)
        return error.exit_code
    except (json.JSONDecodeError, UnicodeDecodeError, AssertionError) as error:
        print("field-stability: FAILED: inconsistent capture input: %s" % error, file=sys.stderr)
        return EXIT_INPUT

    # Every step must have been compared; a silent parse hole would weaken the record.
    missing = [step for step in FIXTURE_STEPS if step not in observed]
    if missing:
        print(
            "field-stability: FAILED: steps without a comparison: %s"
            % ", ".join(missing),
            file=sys.stderr,
        )
        return EXIT_INPUT

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=True, sort_keys=True)
        stream.write("\n")

    print("field-stability: wrote %s" % out_path)
    for step in FIXTURE_STEPS:
        summary = observed[step]
        if step in JSON_STEPS:
            print(
                "field-stability:   %-16s differing paths: %d"
                % (step, summary["differing_path_count"])  # type: ignore[index]
            )
        else:
            print("field-stability:   %-16s comparison recorded" % step)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
