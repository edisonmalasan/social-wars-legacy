#!/usr/bin/env python3
"""Capture executed legacy boot fixtures from the real legacy Flask server.

What this does, in order:

1. Verifies the parent interpreter is CPython 3.9 and that the working-tree
   containment snapshot (root ``*.py``, ``config/``, ``mods/``, ``villages/``,
   ``templates/``, ``tests/saves/``, ``saves/``) is taken before anything runs.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root containing only what
   the legacy server needs: root ``*.py``, ``config/``, ``mods/``,
   ``villages/``, ``templates/``, and ``saves/`` seeded from
   ``tests/saves/fresh-player.json``.
4. Starts the REAL legacy server (``python -B server.py`` in the disposable
   copy, same interpreter as the parent) and waits for loopback readiness.
5. Performs the legacy requests with exact recorded parameters and records,
   per call, ``before``/``response``/``after`` SHA-256 of the disposable
   corpus saves:

   * ``GET  /``                        — login page / session save list
   * ``POST /``                        — login form (USERID + GAMEVERSION)
   * ``GET  /play.html``               — logged-in session render (cookie)
   * ``GET  .../get_game_config.php``  — USERID, user_key, language query
   * ``POST .../get_player_info.php``  — USERID, user_key, language form
     (current-player branch: no ``user`` field, so ``user`` is ``None``)

6. Stops the server (``taskkill /T /F`` + waits), confirms the port is free,
   re-checks the working-tree containment snapshot, discards the disposable
   copy, and writes the fixtures under ``--out`` (default:
   ``tests/fixtures/godot-compatibility-boot/``).

Containment:

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs, villages,
  templates, and tests/saves are read only; any byte change there fails the
  run with exit 6 before fixtures are written.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript, or
  external network. The legacy command recorder env var is stripped from the
  child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes:

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or returned an unexpected status
6     Containment violation (working-tree bytes changed, or the disposable
      corpus saves changed during server startup)
7     Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_legacy_fixtures.py

where ``python`` denotes the pinned CPython 3.9.13 executable
(``C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe``).
The child server process reuses ``sys.executable`` (the same interpreter).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hashing import canonical_digest, sha256_bytes, sha256_file  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_HOST = "127.0.0.1"
LEGACY_PORT = 5055
DYNAMIC_ROOT = "/dynamic/menvswomen/srvsexwars"
FRESH_PLAYER_SAVE = REPO_ROOT / "tests" / "saves" / "fresh-player.json"
DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-compatibility-boot"

# Request parameters are the legacy client's own FlashVars values from
# templates/play.html (user_key, language) and the login form's default game
# version from templates/login.html / sessions.new_village().
USER_KEY = "123456789"
LANGUAGE = "en"
GAME_VERSION = "Basesec_1.5.4.swf"

COPY_ROOT_PY = sorted(path.name for path in REPO_ROOT.glob("*.py"))
COPY_DIRS = ("config", "mods", "villages", "templates")

# Working-tree groups snapshotted before and after the run.
CONTAINMENT_GROUPS_ROOT_PY = "root_python"

OPTION_RE = re.compile(
    r'<option value="(?P<id>[^"]+)" title="[^"]*">'
    r"(?P<name>.*?) ~ level (?P<level>\d+) \((?P<xp>\d+) xp\)</option>"
)
VERSION_RE = re.compile(r"By the Social Warriors team ~ (?P<version>[^<\r\n]+)")
SESSION_COOKIE_RE = re.compile(r"session=([^;]+)")

EXIT_OK = 0
EXIT_ENVIRONMENT = 2
EXIT_PORT_BUSY = 3
EXIT_SERVER = 4
EXIT_REQUEST = 5
EXIT_CONTAINMENT = 6
EXIT_WRITE = 7

FIXTURE_STEPS = (
    "login_page",
    "login_post",
    "play_page",
    "get_game_config",
    "get_player_info",
)


class CaptureError(Exception):
    """Failure with an assigned process exit code."""

    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dir_group_record(dir_path: Path, rel_prefix: str = "") -> Dict[str, object]:
    """Digest record for an existing directory tree (relative POSIX paths)."""
    if not dir_path.is_dir():
        return {"exists": False, "files": 0, "sha256": "absent"}
    entries: List[Tuple[str, str]] = []
    for path in sorted(dir_path.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(dir_path).as_posix()
        if rel_prefix:
            relative = rel_prefix + "/" + relative
        entries.append((relative, sha256_file(path)))
    return {
        "exists": True,
        "files": len(entries),
        "sha256": canonical_digest(entries),
    }


def containment_snapshot() -> Dict[str, Dict[str, object]]:
    """Byte state of every working-tree path this run is allowed to read."""
    groups: Dict[str, Dict[str, object]] = {}
    root_py: List[Tuple[str, str]] = [
        (name, sha256_file(REPO_ROOT / name)) for name in COPY_ROOT_PY
    ]
    groups[CONTAINMENT_GROUPS_ROOT_PY] = {
        "exists": True,
        "files": len(root_py),
        "sha256": canonical_digest(root_py),
    }
    for name in ("config", "mods", "villages", "templates"):
        groups[name] = dir_group_record(REPO_ROOT / name, name)
    groups["tests/saves"] = dir_group_record(REPO_ROOT / "tests" / "saves", "tests/saves")
    groups["saves"] = dir_group_record(REPO_ROOT / "saves", "saves")
    return groups


def snapshot_combined(groups: Dict[str, Dict[str, object]]) -> str:
    return canonical_digest(
        (name, str(record.get("sha256", "absent"))) for name, record in groups.items()
    )


def save_group_record(saves_dir: Path) -> Dict[str, object]:
    """Before/after record for the disposable corpus saves directory."""
    if not saves_dir.is_dir():
        raise CaptureError(EXIT_CONTAINMENT, "corpus saves directory missing: %s" % saves_dir)
    files: List[Dict[str, object]] = []
    entries: List[Tuple[str, str]] = []
    for path in sorted(saves_dir.iterdir()):
        if not path.is_file():
            continue
        digest = sha256_file(path)
        files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": digest})
        entries.append((path.name, digest))
    return {
        "captured_at_utc": iso_now(),
        "scope": "disposable corpus saves directory (one entry per file)",
        "files": files,
        "files_count": len(files),
        "sha256": canonical_digest(entries),
    }


def port_is_free(host: str, port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree in sorted order (deterministic creation order)."""
    for path in sorted(src.rglob("*")):
        relative = path.relative_to(src)
        target = dst / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def build_disposable(tmp_parent: Path) -> Tuple[Path, str, str]:
    """Create the disposable legacy runtime; returns (root, pid, seed_sha)."""
    disposable = Path(tempfile.mkdtemp(prefix="socialwars-capture-", dir=str(tmp_parent)))
    for name in COPY_ROOT_PY:
        shutil.copy2(REPO_ROOT / name, disposable / name)
    for name in COPY_DIRS:
        copy_tree(REPO_ROOT / name, disposable / name)
    seed = json.loads(FRESH_PLAYER_SAVE.read_text(encoding="utf-8"))
    try:
        pid = str(seed["playerInfo"]["pid"])
    except (KeyError, TypeError) as error:
        raise CaptureError(EXIT_ENVIRONMENT, "fresh save has no playerInfo.pid: %s" % error)
    if not pid:
        raise CaptureError(EXIT_ENVIRONMENT, "fresh save pid is empty")
    saves_dir = disposable / "saves"
    saves_dir.mkdir(parents=True, exist_ok=False)
    seed_target = saves_dir / ("%s.save.json" % pid)
    shutil.copy2(FRESH_PLAYER_SAVE, seed_target)
    return disposable, pid, sha256_file(seed_target)


def child_environment() -> Dict[str, str]:
    env = dict(os.environ)
    # The opt-in legacy command recorder must never be armed during capture.
    env.pop("SOCIALWARS_COMMAND_RECORD_DIR", None)
    # Imports resolve from the child script directory; drop inherited paths.
    env.pop("PYTHONPATH", None)
    return env


def start_server(disposable: Path) -> Tuple[subprocess.Popen, Path, Path]:
    stdout_path = disposable / "server.stdout.log"
    stderr_path = disposable / "server.stderr.log"
    stdout_handle = open(stdout_path, "wb")
    stderr_handle = open(stderr_path, "wb")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            [sys.executable, "-B", "server.py"],
            cwd=str(disposable),
            env=child_environment(),
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()
    return process, stdout_path, stderr_path


def wait_ready(process: subprocess.Popen, host: str, port: int, timeout_s: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(0.5)
        try:
            probe.connect((host, port))
            return True
        except OSError:
            pass
        finally:
            probe.close()
        time.sleep(0.25)
    return False


def stop_server(process: subprocess.Popen, host: str, port: int) -> Optional[str]:
    """Stop the server process tree; returns an error message or None."""
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            process.kill()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return "server process %d did not exit" % process.pid
    # The port must be free again (detects a lingering listener we did not reap).
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if port_is_free(host, port):
            return None
        time.sleep(0.25)
    return "port %s:%d still in use after stopping the server" % (host, port)


def http_request(
    port: int,
    method: str,
    path: str,
    query: Optional[Dict[str, str]] = None,
    form: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, object]:
    target = path
    if query:
        target = path + "?" + urlencode(query)
    headers: Dict[str, str] = {
        "Host": "%s:%d" % (LEGACY_HOST, port),
        "Accept": "*/*",
        "Connection": "close",
    }
    body: Optional[bytes] = None
    if form is not None:
        body = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if cookie:
        headers["Cookie"] = cookie
    connection = HTTPConnection(LEGACY_HOST, port, timeout=timeout)
    try:
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        status = response.status
        reason = response.reason
        response_headers = response.getheaders()
    finally:
        connection.close()
    return {
        "method": method,
        "target": target,
        "path": path,
        "query": query or {},
        "form": form,
        "headers_sent": headers,
        "status": status,
        "reason": reason,
        "response_headers": {key: value for key, value in response_headers},
        "body": data,
    }


def parse_session_surface(body: bytes) -> Dict[str, object]:
    """Derive the legacy session save list from the executed login page."""
    text = body.decode("utf-8", errors="strict")
    version_match = VERSION_RE.search(text)
    if not version_match:
        raise CaptureError(
            EXIT_REQUEST,
            "login page no longer renders 'By the Social Warriors team ~ <version>'; "
            "templates/login.html drifted from the capture parser",
        )
    options = OPTION_RE.findall(text)
    if not options:
        raise CaptureError(
            EXIT_REQUEST,
            "login page rendered no <option> save entries; "
            "templates/login.html drifted from the capture parser",
        )
    saves = [
        {
            "id": option_id,
            "name": html.unescape(option_name),
            "level": int(option_level),
            "xp": int(option_xp),
        }
        for option_id, option_name, option_level, option_xp in options
    ]
    return {
        "derived_from": "steps/login_page/response.body",
        "parsing": (
            "templates/login.html rendering: option value=userid, option text "
            "'<name> ~ level <level> (<xp> xp)'; game version from "
            "'By the Social Warriors team ~ <version>'. Names are HTML-unescaped."
        ),
        "game_version": html.unescape(version_match.group("version").strip()),
        "saves": saves,
    }


def extract_session_cookie(response: Dict[str, object]) -> str:
    set_cookie = str(response["response_headers"].get("Set-Cookie", ""))
    match = SESSION_COOKIE_RE.search(set_cookie)
    if not match:
        raise CaptureError(EXIT_REQUEST, "login POST set no session cookie")
    return "session=" + match.group(1)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=True, sort_keys=True)
        stream.write("\n")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as stream:
        stream.write(data)


def clear_previous_fixtures(out_dir: Path) -> None:
    """Remove only this command's own outputs so reruns are deterministic."""
    steps_dir = out_dir / "steps"
    if steps_dir.is_dir():
        shutil.rmtree(steps_dir)
    manifest = out_dir / "capture-manifest.json"
    if manifest.is_file():
        manifest.unlink()


def run_step(
    name: str,
    out_dir: Path,
    saves_dir: Path,
    port: int,
    method: str,
    path: str,
    query: Optional[Dict[str, str]] = None,
    form: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
    expect_status: int = 200,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Execute one legacy request with before/response/after save records."""
    before = save_group_record(saves_dir)
    result = http_request(port, method, path, query=query, form=form, cookie=cookie)
    after = save_group_record(saves_dir)

    status = int(result["status"])  # type: ignore[arg-type]
    if status != expect_status:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: expected HTTP %d, got %d" % (name, expect_status, status),
        )

    body = result.pop("body")  # type: ignore[misc]
    step_dir = out_dir / "steps" / name
    request_record = {
        "captured_at_utc": iso_now(),
        "method": result["method"],
        "target": result["target"],
        "path": result["path"],
        "query": result["query"],
        "form": result["form"],
        "headers_sent": result["headers_sent"],
        "scheme": "http",
        "host": LEGACY_HOST,
        "port": port,
        "note": (
            "Exact client request bytes are reconstructed from this record; "
            "Host is set explicitly, no User-Agent header is sent."
        ),
    }
    response_record = {
        "status": status,
        "reason": result["reason"],
        "headers": result["response_headers"],
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "captured_at_utc": iso_now(),
    }
    write_json(step_dir / "request.json", request_record)
    write_json(step_dir / "before.json", before)
    write_json(step_dir / "response.meta.json", response_record)
    write_bytes(step_dir / "response.body", body)
    write_json(step_dir / "after.json", after)

    summary = {
        "name": name,
        "method": method,
        "path": result["path"],
        "target": result["target"],
        "status": status,
        "response_bytes": len(body),
        "response_sha256": response_record["body_sha256"],
        "saves_sha256_before": before["sha256"],
        "saves_sha256_after": after["sha256"],
        "saves_unchanged_by_call": before["sha256"] == after["sha256"],
    }
    return summary, {"before": before, "after": after, "body": body, "result": result}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture executed legacy boot fixtures (contained, loopback only)."
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
    if not COPY_ROOT_PY:
        print("capture: no root *.py files found in %s" % REPO_ROOT, file=sys.stderr)
        return EXIT_ENVIRONMENT

    out_dir = Path(args.out).resolve()
    if REPO_ROOT not in out_dir.parents:
        # Fixture output must stay inside the repository working tree.
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

    # Fixture files are staged OUTSIDE the working tree and published only
    # after every check passed, so a failed run writes nothing into the repo.
    staging = Path(tempfile.mkdtemp(prefix="compat-capture-staging-"))
    disposable: Optional[Path] = None
    process: Optional[subprocess.Popen] = None
    server_error: Optional[str] = None

    try:
        disposable, pid, seed_sha = build_disposable(Path(tempfile.gettempdir()))
        saves_dir = disposable / "saves"
        # Canonical group digest of the seeded saves BEFORE the server starts,
        # so the startup comparison uses the same digest space as later records.
        seed_group = save_group_record(saves_dir)
        print("capture: disposable copy: %s" % disposable)
        print("capture: starting legacy server on %s:%d ..." % (LEGACY_HOST, LEGACY_PORT))
        process, stdout_path, stderr_path = start_server(disposable)
        if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
            tail_out = read_tail(stdout_path)
            tail_err = read_tail(stderr_path)
            raise CaptureError(
                EXIT_SERVER,
                "legacy server did not become ready (exit=%s)\n--- stdout ---\n%s"
                "\n--- stderr ---\n%s" % (process.poll(), tail_out, tail_err),
            )
        print("capture: legacy server ready (pid %d)" % process.pid)

        startup_record = save_group_record(saves_dir)
        if startup_record["sha256"] != seed_group["sha256"]:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "server startup rewrote the seeded corpus saves (group %s -> %s); "
                "the post-migration fresh corpus must not be rewritten at load"
                % (seed_group["sha256"], startup_record["sha256"]),
            )

        summaries: List[Dict[str, object]] = []

        summary, detail = run_step(
            "login_page", staging, saves_dir, LEGACY_PORT,
            "GET", "/", expect_status=200,
        )
        summaries.append(summary)

        save_list = parse_session_surface(detail["body"])  # type: ignore[arg-type]
        write_json(staging / "steps" / "login_page" / "save-list.json", save_list)

        summary, detail = run_step(
            "login_post", staging, saves_dir, LEGACY_PORT,
            "POST", "/",
            form={"USERID": pid, "GAMEVERSION": GAME_VERSION},
            expect_status=302,
        )
        summaries.append(summary)
        cookie = extract_session_cookie(detail["result"])  # type: ignore[arg-type]

        summary, _detail = run_step(
            "play_page", staging, saves_dir, LEGACY_PORT,
            "GET", "/play.html", cookie=cookie, expect_status=200,
        )
        summaries.append(summary)

        summary, _detail = run_step(
            "get_game_config", staging, saves_dir, LEGACY_PORT,
            "GET", DYNAMIC_ROOT + "/get_game_config.php",
            query={"USERID": pid, "user_key": USER_KEY, "language": LANGUAGE},
            expect_status=200,
        )
        summaries.append(summary)

        summary, _detail = run_step(
            "get_player_info", staging, saves_dir, LEGACY_PORT,
            "POST", DYNAMIC_ROOT + "/get_player_info.php",
            form={"USERID": pid, "user_key": USER_KEY, "language": LANGUAGE},
            expect_status=200,
        )
        summaries.append(summary)

        # Stop the server before any containment re-check.
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

        final_saves = save_group_record(saves_dir)
        if final_saves["sha256"] != str(summaries[0]["saves_sha256_before"]):
            raise CaptureError(
                EXIT_CONTAINMENT,
                "disposable corpus saves changed across the capture sequence",
            )

        if not args.keep_disposable and disposable is not None:
            shutil.rmtree(disposable, ignore_errors=False)
            disposable = None

        manifest = {
            "schema": "godot-compatibility-boot/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for the legacy "
                "boot endpoints; parity oracle for Compatibility API v0 tests."
            ),
            "invocation": "python -B apps/compat-api/capture_legacy_fixtures.py"
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
                "pid": pid,
            },
            "requests": {
                "count": len(summaries),
                "login_surface_requests": 3,
                "dynamic_endpoint_requests": 2,
                "steps": summaries,
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
                "capture:   %-16s %s %s -> %d (%d bytes, saves unchanged: %s)"
                % (
                    summary["name"],
                    summary["method"],
                    summary["target"],
                    summary["status"],
                    summary["response_bytes"],
                    summary["saves_unchanged_by_call"],
                )
            )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return EXIT_OK

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


def read_tail(path: Path, limit: int = 4000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return "<unreadable>"
    return data[-limit:].decode("utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
