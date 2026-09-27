#!/usr/bin/env python3
"""Opt-in loopback smoke for the documented Compatibility API start command.

This script is **not** picked up by the unittest suite (discovery matches
``test_*.py``); it is an explicit, single-shot check that the real service
starts on the loopback port, answers the documented endpoints, reports the
structured error paths, and cleans its disposable corpus up again.

Invocation (from the repository root, pinned interpreter)::

    python -B apps/compat-api/tests/smoke_loopback.py

Exit codes:

- ``0`` — every check passed
- ``1`` — at least one check failed (each failure is printed as ``FAIL``)

Containment / prerequisites:

- binds only ``127.0.0.1`` (port 5056 must be free — a second instance is
  started deliberately to assert the documented ``3`` port-busy exit);
- builds its own temporary corpus under the system temp directory and removes
  it again (both on normal stop and on the port-busy path);
- never writes to the repository; the final check asserts the working tree
  still has no ``saves/`` directory;
- runs no Flash/Ruffle/ActionScript code and opens no external network.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = "http://127.0.0.1:5056"
PID = "00000000-0000-4000-8000-000000000001"
STARTUP_DEADLINE_SECONDS = 90

failures = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" :: " + detail) if detail else ""))
    if not ok:
        failures.append(name)


def http(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = raw
        return err.code, parsed


def main():
    out_path = os.path.join(tempfile.gettempdir(), "compat-smoke-out.txt")
    err_path = os.path.join(tempfile.gettempdir(), "compat-smoke-err.txt")
    for path in (out_path, err_path):
        if os.path.exists(path):
            os.remove(path)

    out_f = open(out_path, "w", encoding="utf-8")
    err_f = open(err_path, "w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-B", os.path.join("apps", "compat-api", "run.py")],
        cwd=REPO,
        stdout=out_f,
        stderr=err_f,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    print("server pid %d" % server.pid)

    status = None
    session = None
    deadline = time.time() + STARTUP_DEADLINE_SECONDS
    while time.time() < deadline:
        if server.poll() is not None:
            break
        try:
            status, session = http("GET", "/v0/session")
            break
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)

    if server.poll() is not None:
        out_f.close()
        err_f.close()
        check("server stays up", False, "exited early with code %s" % server.returncode)
        print(open(err_path, encoding="utf-8", errors="replace").read())
        return 1

    check("GET /v0/session -> 200", status == 200, str(status))
    check("session protocol compat-v0", session.get("protocol") == "compat-v0")
    check("session ok true", session.get("ok") is True)
    check("session game_version alpha 0.02", session.get("game_version") == "alpha 0.02",
          repr(session.get("game_version")))
    check("session server_time is an int", isinstance(session.get("server_time"), int),
          repr(session.get("server_time")))
    saves = session.get("saves")
    check("session saves list holds our pid",
          isinstance(saves, list) and any(s.get("id") == PID for s in saves if isinstance(s, dict)),
          repr(saves))
    check("session save entry shape",
          isinstance(saves, list) and all(sorted(s) == ["id", "level", "name", "xp"] for s in saves),
          repr(saves[:1]))

    status, body = http("POST", "/v0/bootstrap", {"user_id": PID})
    check("POST /v0/bootstrap known pid -> 200", status == 200, str(status))
    if status == 200:
        check("bootstrap envelope keys",
              sorted(body) == ["config", "game_version", "ok", "player_info", "protocol", "saves", "server_time"],
              str(sorted(body)))
        check("bootstrap ok true", body.get("ok") is True)
        check("bootstrap config is an object", isinstance(body.get("config"), dict))
        info = body.get("player_info")
        check("bootstrap player_info is an object",
              isinstance(info, dict) and "last_logged_in" in info.get("playerInfo", {}),
              str(type(info)))
        check("bootstrap saves has our pid",
              isinstance(body.get("saves"), list)
              and any(s.get("id") == PID for s in body["saves"] if isinstance(s, dict)))

    status, body = http("POST", "/v0/bootstrap", {})
    check("POST bootstrap missing user_id -> 400", status == 400, str(status))
    check("missing_user_id error shape",
          isinstance(body, dict) and body.get("ok") is False
          and body.get("protocol") == "compat-v0"
          and body.get("error", {}).get("code") == "missing_user_id",
          str(body)[:200])

    status, body = http("POST", "/v0/bootstrap", {"user_id": "no-such-user"})
    check("POST bootstrap unknown pid -> 404", status == 404, str(status))
    check("unknown_user_id error code",
          isinstance(body, dict) and body.get("error", {}).get("code") == "unknown_user_id",
          str(body)[:200])

    status, body = http("GET", "/v0/nope")
    check("GET unknown path -> 404 JSON", status == 404, str(status))
    check("not_found error shape",
          isinstance(body, dict) and set(body) == {"protocol", "ok", "error"}
          and body.get("error", {}).get("code") == "not_found",
          str(body)[:200])

    # Port-busy path: a second instance on the same port must exit 3 and,
    # because it created its corpus and is returning normally, remove it.
    busy_corpus = os.path.join(tempfile.gettempdir(), "socialwars-compat-busy-smoke")
    if os.path.exists(busy_corpus):
        shutil.rmtree(busy_corpus)
    second = subprocess.run(
        [sys.executable, "-B", os.path.join("apps", "compat-api", "run.py"), "--corpus", busy_corpus],
        cwd=REPO, capture_output=True, timeout=120,
    )
    check("second instance on busy port exits 3", second.returncode == 3,
          "code=%s stderr=%s" % (second.returncode, second.stderr.decode("utf-8", "replace")[:200]))
    check("busy-port instance removed its own corpus", not os.path.exists(busy_corpus))

    # Clean stop: Ctrl+Break reaches the child's new process group and takes
    # run.py's documented KeyboardInterrupt path (exit 0, corpus removed).
    try:
        server.send_signal(signal.CTRL_BREAK_EVENT)
    except (AttributeError, OSError, ValueError):  # pragma: no cover - non-Windows
        server.kill()
    try:
        code = server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        print("server did not stop after CTRL_BREAK; killing")
        server.kill()
        code = server.wait(timeout=30)
    out_f.close()
    err_f.close()
    check("server stop exit code 0", code == 0, str(code))

    log = open(out_path, encoding="utf-8", errors="replace").read()
    corpus_line = [ln for ln in log.splitlines() if "disposable corpus at" in ln]
    if corpus_line:
        kept = corpus_line[0].split("corpus at ", 1)[1].split(" (", 1)[0]
        leftover = []
        if os.path.exists(kept):
            leftover = [p for p, _dirs, _files in os.walk(kept)]
        check("default corpus removed on stop", not os.path.exists(kept),
              "%s leftover=%s" % (kept, leftover[:10]))
        if os.path.exists(kept):
            shutil.rmtree(kept, ignore_errors=True)
    else:
        check("corpus line in server log", False, log[:300])

    check("working-tree saves/ absent",
          not os.path.exists(os.path.join(REPO, "saves")),
          os.path.join(REPO, "saves"))
    return 1 if failures else 0


if __name__ == "__main__":
    result = main()
    print("SMOKE RESULT: %s (%d failure(s))" % ("PASS" if result == 0 else "FAIL", len(failures)))
    sys.exit(result)
