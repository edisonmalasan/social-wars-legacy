#!/usr/bin/env python3
"""One live GameApi phase against **Server v1**: start ``apps/server-v1`` on its
own loopback port, run one Godot command against it, tear the service down, and
prove the teardown really happened.

    python -B apps/client-godot/server_v1_live_phase.py --port 5057 -- \\
        <Godot executable> --headless --path apps/client-godot ... -- \\
        --gameapi=server_v1 --gameapi-endpoint=http://127.0.0.1:5057

The disposable corpus's player id is appended by this script as
``--player-id=<stem>``, after the caller's own user-arguments separator, because
the id does not exist until the corpus does.

## Why this is a second harness and not a parameter of ``compat_live_phase.py``

Everything in that harness is v0-shaped, and reusing it would have meant either
changing what 23 delivered phases depend on or threading v1 conditionals
through them:

* readiness is ``GET /v0/session`` -> 200, a route v1 does not have;
* the service it starts is ``apps/compat-api/run.py``;
* it finds the disposable corpus by grepping for ``built disposable corpus at``;
  v1 prints a JSON banner instead;
* it identifies a corpus save by listing ``<corpus>/saves`` and does not know
  v1's ``<pid>.save.json`` naming, so it cannot tell the harness which player id
  the client should address;
* its corpus prefix is ``socialwars-compat-``.

Perturbing a harness that twenty-three archived phases already pass through is
the failure mode this repository records repeatedly. This file is separate, and
the compat harness is not touched.

## v1 readiness

There is no health route to add, because a health route is a route v1 does not
have. Readiness is a real ``POST /v1/collect`` for an unknown save, which must
answer **404** with ``code == "unknown_player"``. That one request proves the
ASGI app is serving, that the delivered route exists, and that the refusal
vocabulary is live - all three, none of them vacuously. A socket-level
"something is listening" probe would only prove the third.

## Containment

* ``run.py`` is started exactly as its own module documents it (pinned
  interpreter, ``-B``, ``--port``), binds ``127.0.0.1`` only, builds a
  disposable corpus in the system temp root, and removes that corpus on the
  clean-stop path;
* this script proves the corpus is gone, that no new ``socialwars-server-v1-*``
  directory is left in temp, that the working tree still has no ``saves/``
  directory, and that the port answers **no** listener;
* the wrapped command's output is piped and pumped, so the caller's log capture
  sees the engine output interleaved with the ``PASS``/``FAIL`` lines and the
  final ``LIVE-PHASE-SUMMARY`` record;
* runs no Flash/Ruffle/ActionScript code and opens no network but loopback.

## The port probe is a CONNECT probe, not a bind probe

``run.py`` asserts the port free with ``bind()`` because it is about to bind.
After teardown the question is different: "is anything still LISTENING?", and on
Windows a ``bind()`` probe cannot distinguish "in use" from "cannot bind" - it
answers the wrong question. So the post-teardown check connects, and treats a
successful connection as a failure. The pre-phase check does the same for the
same reason: a listener that somehow survived would still refuse the bind on a
``SO_REUSEADDR`` socket.

## Exit codes

* ``0`` - every check passed, including the teardown checks
* ``1`` - at least one check failed (each failure is printed as ``FAIL``)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICE = os.path.join("apps", "server-v1", "run.py")
COLLECT_PATH = "/v1/collect"
STARTUP_DEADLINE_SECONDS = 90
GODOT_TIMEOUT_SECONDS = 600
CORPUS_PREFIX = "socialwars-server-v1-"
SAVE_SUFFIX = ".save.json"

failures = []
passed = 0


def check(name, ok, detail=""):
    global passed
    line = "%s %s%s" % ("PASS" if ok else "FAIL", name, (" :: " + detail) if detail else "")
    print(line)
    if ok:
        passed += 1
    else:
        failures.append(name)


def port_has_listener(port):
    """True when something ACCEPTS a loopback connection on ``port``.

    Used for both "is the port free before the phase" and "was the port released
    after teardown".  A bind probe is the wrong instrument for either question on
    Windows; see the module docstring.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(2.0)
    try:
        probe.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def readiness(port, player_id="readiness-probe-unknown-save"):
    """POST /v1/collect for an unknown save -> (status, body dict).

    v1 answers every refusal with an HTTP status AND a structured body, so both
    are returned and the caller checks both.  A connection failure yields
    ``(None, {})`` and is not distinguished here from a body the caller cannot
    read; the caller asserts the exact pair it requires.
    """
    url = "http://127.0.0.1:%d%s" % (port, COLLECT_PATH)
    payload = json.dumps({"player_id": player_id, "row": 0}).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, ConnectionError, OSError):
        return None, {}
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, {}


def temp_corpora():
    try:
        return set(
            entry
            for entry in os.listdir(tempfile.gettempdir())
            if entry.startswith(CORPUS_PREFIX)
        )
    except OSError:
        return set()


def parse_banner(log_text):
    """The JSON banner ``run.py`` prints on stdout, as a dict.

    The banner is pretty-printed JSON with ``indent=4``, so it cannot be split
    out by lines.  It is located by ``raw_decode`` from the first ``{``, which
    tolerates uvicorn's own logging lines appearing before or after it.
    """
    start = log_text.find("{")
    if start == -1:
        return {}
    try:
        banner, _ = json.JSONDecoder().raw_decode(log_text[start:])
    except ValueError:
        return {}
    return banner if isinstance(banner, dict) else {}


def read_service_log(out_path, err_path):
    text = ""
    for path in (out_path, err_path):
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                text += handle.read()
    return text


def corpus_player_id(corpus):
    """The one save v1 built, by stem - ``<pid>.save.json`` - or ``""``.

    v1's corpus holds exactly one save; a harness that picked the first of
    several would be guessing, and guessing here would silently drive the client
    at an unproven identity.  Exactly one is required and the count is checked.
    """
    if not corpus:
        return ""
    saves_dir = os.path.join(corpus, "saves")
    try:
        entries = sorted(os.listdir(saves_dir))
    except OSError:
        return ""
    matched = [e for e in entries if e.endswith(SAVE_SUFFIX)]
    if len(matched) != 1:
        return ""
    return matched[0][: -len(SAVE_SUFFIX)]


def save_digest(corpus, player_id):
    path = os.path.join(corpus, "saves", player_id + SAVE_SUFFIX)
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="server_v1_live_phase.py",
        description="start Server v1, run one Godot command, tear down.",
    )
    parser.add_argument("--port", type=int, default=5057, help="loopback port (default 5057)")
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=STARTUP_DEADLINE_SECONDS,
        help="seconds to wait for POST /v1/collect to refuse (default %d)"
        % STARTUP_DEADLINE_SECONDS,
    )
    parser.add_argument(
        "--godot-timeout",
        type=int,
        default=GODOT_TIMEOUT_SECONDS,
        help="seconds to wait for the wrapped command (default %d)" % GODOT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--name", default="server-v1-live", help="label used in the summary")
    parser.add_argument(
        "--expect-save-mutation",
        action="store_true",
        help="fail unless the disposable corpus save changes while the wrapped "
        "command runs",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("FAIL a command is required after --")
        print("LIVE-PHASE-SUMMARY %s" % json.dumps({"name": args.name, "ok": False}))
        return 1

    if any(argument.startswith("--player-id=") for argument in command):
        # The id is derived in-phase from the corpus this harness starts, so a
        # caller cannot supply one: two candidate identities in one phase would
        # make every downstream assertion ambiguous. Refused, not overwritten.
        print("FAIL do not pass --player-id=; this harness supplies it in-phase")
        print("LIVE-PHASE-SUMMARY %s" % json.dumps({"name": args.name, "ok": False}))
        return 1

    before = temp_corpora()
    out_path = os.path.join(tempfile.gettempdir(), "server-v1-live-phase-out.txt")
    err_path = os.path.join(tempfile.gettempdir(), "server-v1-live-phase-err.txt")
    for path in (out_path, err_path):
        if os.path.exists(path):
            os.remove(path)

    listening_before = port_has_listener(args.port)
    check(
        "loopback port %d has no listener before the phase" % args.port,
        not listening_before,
    )
    if listening_before:
        print("LIVE-PHASE-SUMMARY %s" % json.dumps({
            "name": args.name, "port": args.port, "ok": False,
            "checks_passed": passed, "checks_failed": len(failures),
            "failures": failures,
        }))
        return 1

    out_f = open(out_path, "w", encoding="utf-8")
    err_f = open(err_path, "w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-B", SERVICE, "--port", str(args.port)],
        cwd=REPO,
        stdout=out_f,
        stderr=err_f,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    print("server pid %d (python %s)" % (server.pid, sys.version.split()[0]))

    status = None
    body = {}
    deadline = time.time() + args.startup_timeout
    while time.time() < deadline:
        if server.poll() is not None:
            break
        status, body = readiness(args.port)
        if status is not None:
            break
        time.sleep(0.5)

    ready = (
        status == 404
        and body.get("code") == "unknown_player"
        and body.get("protocol") == "server-v1"
        and server.poll() is None
    )
    check(
        "POST /v1/collect refuses an unknown save with 404/unknown_player "
        "within %ds" % args.startup_timeout,
        ready,
        "status=%r code=%r server_exit=%r" % (status, body.get("code"), server.poll()),
    )

    corpus = ""
    player_id = ""
    digest_before = ""
    if ready:
        banner = parse_banner(read_service_log(out_path, err_path))
        corpus = str(banner.get("corpus") or "")
        check("service banner names the disposable corpus", bool(corpus), corpus)
        check(
            "service banner reports one route",
            banner.get("routes") == ["POST /v1/collect"],
            str(banner.get("routes")),
        )
        check(
            "service banner reports v1 on the port under test",
            banner.get("port") == args.port and banner.get("host") == "127.0.0.1",
            "host=%r port=%r" % (banner.get("host"), banner.get("port")),
        )
        player_id = corpus_player_id(corpus)
        check(
            "the disposable corpus holds exactly one %s save" % SAVE_SUFFIX,
            bool(player_id),
            corpus,
        )
        if player_id and args.expect_save_mutation:
            digest_before = save_digest(corpus, player_id)
            check(
                "pre-command corpus save digest recorded",
                bool(digest_before),
                "%s=%s" % (player_id, digest_before[:16]),
            )

    godot_exit = None
    if ready and player_id:
        # The player id is only knowable once the disposable corpus exists, which
        # is after readiness, so the wrapped command's `--player-id=` argument is
        # appended HERE rather than by the caller.  The client's suite reads it
        # from the engine's user-argument list, so it lands after the `--`
        # separator the caller already provided.
        command += ["--player-id=" + player_id]
        print("running: %s" % " ".join(command))
        process = None
        pumped = []
        pump_error = [None]
        try:
            process = subprocess.Popen(
                command,
                cwd=REPO,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as error:
            check("wrapped command could start", False, str(error))

        if process is not None:
            def pump():
                try:
                    for line in process.stdout:
                        pumped.append(line)
                        sys.stdout.write(line)
                        sys.stdout.flush()
                except Exception as error:  # pragma: no cover - defensive
                    pump_error[0] = str(error)

            reader = threading.Thread(target=pump, daemon=True)
            reader.start()
            try:
                godot_exit = process.wait(timeout=args.godot_timeout)
            except subprocess.TimeoutExpired:
                godot_exit = None
                process.kill()
                process.wait(timeout=30)
                check("wrapped command finished within %ds" % args.godot_timeout, False)
            reader.join(timeout=30)
            if pump_error[0] is not None:
                check("wrapped command output was captured", False, pump_error[0])
            check(
                "wrapped command exits 0",
                godot_exit == 0,
                "exit=%r" % (godot_exit,),
            )
    elif ready:
        check("wrapped command runs against a ready service", False, "no player id")
    else:
        check("wrapped command runs against a ready service", False, "service not ready")

    digest_after = ""
    if args.expect_save_mutation and corpus and player_id:
        digest_after = save_digest(corpus, player_id)
        check(
            "the disposable corpus save mutated by the live collection",
            bool(digest_before) and bool(digest_after) and digest_before != digest_after,
            "%s before=%s after=%s"
            % (player_id, digest_before[:16], digest_after[:16]),
        )

    # Clean stop: Ctrl+Break reaches the child's new process group and takes
    # run.py's documented KeyboardInterrupt path (exit 0, corpus removed).  That
    # handler was added in run.py itself after this teardown proved unreachable.
    server_exit = None
    if server.poll() is None:
        try:
            server.send_signal(signal.CTRL_BREAK_EVENT)
        except (AttributeError, OSError, ValueError):  # pragma: no cover - non-Windows
            server.kill()
        try:
            server_exit = server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print("server did not stop after CTRL_BREAK; killing")
            server.kill()
            server_exit = server.wait(timeout=30)
    else:
        server_exit = server.returncode
    out_f.close()
    err_f.close()

    check("service stop exit code 0", server_exit == 0, "exit=%r" % (server_exit,))

    if corpus:
        check("disposable corpus removed on stop", not os.path.exists(corpus), corpus)
        if os.path.exists(corpus):
            shutil.rmtree(corpus, ignore_errors=True)

    leftovers = sorted(temp_corpora() - before)
    check(
        "no new %s* directory left in temp" % CORPUS_PREFIX,
        not leftovers,
        ", ".join(leftovers),
    )
    check(
        "working-tree saves/ absent",
        not os.path.exists(os.path.join(REPO, "saves")),
        os.path.join(REPO, "saves"),
    )
    check(
        "loopback port %d answers no listener after teardown" % args.port,
        not port_has_listener(args.port),
    )

    # A failure this harness cannot explain is a failure this project will
    # rediscover as an unexplained red. The first battery run died with
    # `server_exit=1` and no diagnostic here at all: `run.py` writes both of
    # its streams to files under TEMP, keeps them, and never mentions them, so
    # the cause was findable only by opening one by hand. (It was
    # `ModuleNotFoundError: No module named 'uvicorn'` on the pinned
    # interpreter - see docs/legacy-baseline.md.) Bounded tail, reason printed,
    # and only when something actually failed.
    if failures:
        for label, stream_path in (("stdout", out_path), ("stderr", err_path)):
            print("service %s tail (%s):" % (label, stream_path))
            try:
                with open(stream_path, "r", encoding="utf-8", errors="replace") as fh:
                    tail = fh.read()[-2000:].rstrip()
            except OSError as exc:
                tail = "<unreadable: %s>" % exc
            for line in tail.splitlines()[-25:]:
                print("  | %s" % line)
        for entry in failures:
            print("failed check: %s" % entry)


    summary = {
        "name": args.name,
        "port": args.port,
        "endpoint": "http://127.0.0.1:%d" % args.port,
        "route": "POST %s" % COLLECT_PATH,
        "readiness_status": status,
        "readiness_code": body.get("code"),
        "godot_exit": godot_exit,
        "server_exit": server_exit,
        "corpus": corpus,
        "player_id": player_id,
        "command": command,
        "checks_passed": passed,
        "checks_failed": len(failures),
        "failures": failures,
        "save_mutation_checked": bool(args.expect_save_mutation),
        "ok": not failures,
    }
    print("LIVE-PHASE-SUMMARY %s" % json.dumps(summary, sort_keys=True))
    if failures:
        print("live phase FAILED %d check(s): %s" % (len(failures), "; ".join(failures)))
        return 1
    print("live phase PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
