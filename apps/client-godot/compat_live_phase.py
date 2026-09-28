#!/usr/bin/env python3
"""One live GameApi phase: start the Compatibility API, run one Godot command
against it, tear the service down, and prove the teardown really happened.

This script is **not** picked up by the compat unittest suite (discovery is
scoped to ``apps/compat-api``); it is an explicit, single-shot orchestration
step used by ``verify-boot.ps1``::

    python -B apps/client-godot/compat_live_phase.py --port 5056 -- \\
        <Godot executable> --headless --path apps/client-godot ...

Exit codes:

- ``0`` - every check passed, including the teardown checks
- ``1`` - at least one check failed (each failure is printed as ``FAIL``)

Containment / prerequisites:

- the service is started exactly as documented (``run.py``), binds only
  ``127.0.0.1``, and the Godot command is expected to dial only that loopback
  endpoint; no external network is opened by this script;
- the service runs from a disposable corpus under the system temp directory
  and removes it on the clean-stop path; this script proves the corpus is
  gone, that no new ``socialwars-compat-*`` directory is left behind, that
  the port is free again, and that the working tree still has no ``saves/``
  directory;
- ``--expect-save-mutation`` additionally snapshots every file under the
  running corpus's ``saves/`` directory after readiness, re-reads them after
  the wrapped command, and fails unless at least one save changed — the
  proof that a live ``POST /v0/place`` really persisted through the legacy
  dispatcher into the disposable corpus (the placement-live phase);
- the wrapped command's stdout/stderr are piped and pumped through this
  script (inherited grandchild handles are not usable here), so the caller's
  log capture sees the engine output interleaved with the ``PASS``/``FAIL``
  lines and the final ``LIVE-PHASE-SUMMARY`` record;
- runs no Flash/Ruffle/ActionScript code and opens no external network.
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
SERVICE = os.path.join("apps", "compat-api", "run.py")
STARTUP_DEADLINE_SECONDS = 90
GODOT_TIMEOUT_SECONDS = 600
CORPUS_PREFIX = "socialwars-compat-"

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


def session_status(port):
    """GET /v0/session -> HTTP status, or None when nothing is listening."""
    url = "http://127.0.0.1:%d/v0/session" % port
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code
    except (urllib.error.URLError, ConnectionError, OSError):
        return None


def port_is_free(port):
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def temp_corpora():
    try:
        return set(
            entry
            for entry in os.listdir(tempfile.gettempdir())
            if entry.startswith(CORPUS_PREFIX)
        )
    except OSError:
        return set()


def parse_corpus_path(log_text):
    for line in log_text.splitlines():
        marker = "built disposable corpus at "
        if marker in line:
            return line.split(marker, 1)[1].split(" (", 1)[0]
    return ""


def read_server_log(out_path, err_path):
    """The service output written so far (the corpus marker lands here at
    startup, long before the wrapped command runs)."""
    text = ""
    for path in (out_path, err_path):
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                text += handle.read()
    return text


def save_digests(corpus):
    """SHA-256 per file under ``<corpus>/saves`` (empty when the corpus or
    its saves directory cannot be read)."""
    if not corpus:
        return {}
    saves_dir = os.path.join(corpus, "saves")
    digests = {}
    try:
        entries = sorted(os.listdir(saves_dir))
    except OSError:
        return {}
    for entry in entries:
        path = os.path.join(saves_dir, entry)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as handle:
                digests[entry] = hashlib.sha256(handle.read()).hexdigest()
        except OSError:
            return {}
    return digests


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="compat_live_phase.py",
        description="start the Compatibility API, run one Godot command, tear down.",
    )
    parser.add_argument("--port", type=int, default=5056, help="loopback port (default 5056)")
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=STARTUP_DEADLINE_SECONDS,
        help="seconds to wait for GET /v0/session (default %d)" % STARTUP_DEADLINE_SECONDS,
    )
    parser.add_argument(
        "--godot-timeout",
        type=int,
        default=GODOT_TIMEOUT_SECONDS,
        help="seconds to wait for the wrapped command (default %d)" % GODOT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--name", default="live-phase", help="label used in the summary")
    parser.add_argument(
        "--expect-save-mutation",
        action="store_true",
        help="fail unless at least one file under the corpus saves/ changes "
        "while the wrapped command runs (placement-live)",
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

    before = temp_corpora()
    out_path = os.path.join(tempfile.gettempdir(), "compat-live-phase-out.txt")
    err_path = os.path.join(tempfile.gettempdir(), "compat-live-phase-err.txt")
    for path in (out_path, err_path):
        if os.path.exists(path):
            os.remove(path)

    free_before = port_is_free(args.port)
    check("loopback port %d is free before the phase" % args.port, free_before)
    if not free_before:
        print("LIVE-PHASE-SUMMARY %s" % json.dumps({
            "name": args.name, "port": args.port, "ok": False,
            "checks": len(failures), "failures": failures,
        }))
        return 1

    # Start the service exactly as the compat README documents it: pinned
    # interpreter, -B, run.py, disposable corpus (the default). A new process
    # group lets the clean stop reach run.py's documented interrupt path.
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
    deadline = time.time() + args.startup_timeout
    while time.time() < deadline:
        if server.poll() is not None:
            break
        status = session_status(args.port)
        if status is not None:
            break
        time.sleep(0.5)

    ready = status == 200 and server.poll() is None
    check(
        "GET /v0/session -> 200 within %ds" % args.startup_timeout,
        ready,
        "status=%r server_exit=%r" % (status, server.poll()),
    )

    # Opt-in placement proof: snapshot every corpus save while the service
    # is up but before the wrapped command runs, then compare afterwards.
    mutation_corpus = ""
    digests_before = {}
    if args.expect_save_mutation and ready:
        mutation_corpus = parse_corpus_path(read_server_log(out_path, err_path))
        check(
            "service log names the corpus before the command",
            bool(mutation_corpus),
            mutation_corpus,
        )
        digests_before = save_digests(mutation_corpus)
        check(
            "pre-command corpus save snapshot recorded",
            bool(digests_before),
            ", ".join(sorted(digests_before)),
        )

    godot_exit = None
    if ready:
        print("running: %s" % " ".join(command))
        # The wrapped engine's output is piped and pumped line by line rather
        # than inherited: on this platform a grandchild of the caller's own
        # stdout (this script, itself started with a redirected stdout) never
        # receives a usable handle, and its markers would be lost. Pumping
        # keeps the caller's log complete and interleaved with the PASS/FAIL
        # lines.
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
    else:
        check("wrapped command runs against a ready service", False, "service not ready")

    if args.expect_save_mutation:
        digests_after = save_digests(mutation_corpus)
        changed = sorted(
            name
            for name in set(digests_before) | set(digests_after)
            if digests_before.get(name) != digests_after.get(name)
        )
        check(
            "corpus save mutated by the live placement",
            bool(changed),
            ", ".join(changed),
        )

    # Clean stop: Ctrl+Break reaches the child's new process group and takes
    # run.py's documented KeyboardInterrupt path (exit 0, corpus removed).
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

    server_log = ""
    for path in (out_path, err_path):
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                server_log += handle.read()

    corpus = parse_corpus_path(server_log)
    check("service log names the disposable corpus", bool(corpus), server_log[:300])
    if corpus:
        check(
            "disposable corpus removed on stop",
            not os.path.exists(corpus),
            corpus,
        )
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
    check("loopback port %d released after teardown" % args.port, port_is_free(args.port))

    summary = {
        "name": args.name,
        "port": args.port,
        "endpoint": "http://127.0.0.1:%d" % args.port,
        "godot_exit": godot_exit,
        "server_exit": server_exit,
        "corpus": corpus,
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
