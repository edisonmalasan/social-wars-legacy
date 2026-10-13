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

## Collection phases seed the corpus, and that is declared, not hidden

``--seed-collection=<id>`` copies one committed row's ``item_ids`` and
``cashPrice`` into the disposable corpus save before the wrapped command runs.

It exists because **the committed fresh-player corpus cannot exercise a grant**:
its ``maps[0]["store"]`` is ``{}`` so it holds none of the fifty distinct item ids
the ten committed collections require, and its ``playerInfo.cash`` is ``5``
against a cheapest committed price of ``9``.  A collection phase without the seed
could drive only refusals, which would leave the line's central claim with no
executed evidence.

The seed is **scaffolding, not derivation**: it copies two committed fields and
decides nothing about eligibility, affordability or the prize.  What it wrote is
printed and carried in the ``seeded`` field of the ``LIVE-PHASE-SUMMARY`` record.
The seed runs **before** the pre-command digest is taken, so
``--expect-save-mutation`` measures the grant rather than the seed.

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
COLLECTION_PATH = "/v1/collection"
MAGIC_PATH = "/v1/magic"
#: The combat route is a **report**, not a mutation: it resolves a committed unit
#: identity, reports both ``push_dead_unit`` gates and destroys nothing. It has no
#: ``--expect-save-mutation`` phase because there is no save to expect to move.
COMBAT_PATH = "/v1/combat"
#: The only route paths this harness will write into a summary. A closed set
#: rather than a free string, because a typo in ``--route-path`` would
#: otherwise produce a passing phase whose evidence file names a route that
#: does not exist -- the same class of defect as a summary that names the
#: wrong one, and the reason ``--route-path`` exists at all.
#:
#: ``/v1/magic`` was **added** to the set rather than the banner check below
#: generalised into a count, and that is the point: a count still passes when the
#: routes are named wrongly or reported out of order, and this harness has
#: already shipped one summary that named the wrong route for a passing phase,
#: which is the whole reason ``--route-path`` exists in the first place.
KNOWN_ROUTE_PATHS = (COLLECT_PATH, COLLECTION_PATH, COMBAT_PATH, MAGIC_PATH)
#: The route list the service must print in its startup banner, **in this exact
#: order**. Named once so the banner check below and a reader of this file
#: cannot disagree about how many routes v1 serves or what they are called.
EXPECTED_BANNER_ROUTES = [
    "POST %s" % COLLECT_PATH,
    "POST %s" % COLLECTION_PATH,
    "POST %s" % COMBAT_PATH,
    "POST %s" % MAGIC_PATH,
]
STARTUP_DEADLINE_SECONDS = 90
GODOT_TIMEOUT_SECONDS = 600
CORPUS_PREFIX = "socialwars-server-v1-"
SAVE_SUFFIX = ".save.json"
#: How many times the committed price the seed puts in the save's cash balance.
#: Above one so the grant is affordable even if some later step charged again;
#: the service is what decides affordability, and this harness must not be the
#: reason a grant happens.
SEED_CASH_MULTIPLE = 2
#: How many of each required item the seed puts in storage. One is the minimum
#: that satisfies "the player holds it"; the eligibility rule is the service's.
SEED_ITEM_QUANTITY = 1

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


def save_path(corpus, player_id):
    return os.path.join(corpus, "saves", player_id + SAVE_SUFFIX)


def save_digest(corpus, player_id):
    path = save_path(corpus, player_id)
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return ""


def committed_collections(corpus):
    """The ``collections`` array the *service itself* reads, as a list.

    Read from ``<corpus>/config/main.json`` and not from the repository's
    normalized package, because the service loads ``config/main.json`` out of the
    corpus it was handed: seeding from a different document than the one the
    service reads would be seeding against a second source of truth, and the two
    could disagree without anything noticing.
    """
    path = os.path.join(corpus, "config", "main.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    rows = document.get("collections")
    return rows if isinstance(rows, list) else None


def seed_collection(corpus, player_id, collection_id):
    """Put one collection's requirements and its price into the corpus save.

    Returns a record of what was written, or ``{"ok": False, "error": ...}``.

    ## Why this exists at all

    **The committed fresh-player corpus cannot exercise a collection grant, and
    the proposal's premise that it could is false.**  Measured, not assumed:

    * every one of the ten committed collections requires **five** item ids, and
      the corpus's ``maps[0]["store"]`` is ``{}`` - it holds none of the fifty
      distinct requirement ids across the table;
    * the corpus's ``playerInfo.cash`` is **5**, and the cheapest committed
      ``cashPrice`` is **9** (collection 7).  Even a perfectly eligible player
      would be refused for affordability.

    So an unseeded collection phase could only ever drive refusals, and the
    phase's whole purpose - proving the server *grants* - would be unreachable.
    The alternative was to drop the live phase for this route, which would have
    left the line's central claim with no executed evidence at all.  Seeding a
    **disposable** corpus is the smaller departure, and it is declared rather
    than silent: the record below is printed and carried in the phase summary.

    ## What this is not

    * **It is not a second derivation.**  It copies one committed row's
      ``item_ids`` and ``cashPrice`` into the save.  It decides nothing about
      eligibility, nothing about affordability, and nothing about the prize.  The
      service still reads its own content and still derives its own answer; if
      the two ever disagreed, the phase would go red, which is the property that
      makes the seed safe to use.
    * **It does not reproduce the alias rule.**  ``collection_id`` must be
      ``>= 1`` here and the committed row is read at ``collection_id - 1``; an
      id that the preserved branch would clamp onto row 0 is **refused** by this
      harness rather than silently seeded as collection 1, because a harness that
      reimplemented the domain's indexing rule would be a second place where that
      rule could drift.
    * **It writes nothing the phase keeps.**  The corpus is disposable and is
      removed on the clean-stop path, and the working tree is asserted to hold no
      ``saves/`` directory afterwards.

    ## Ordering, which matters

    The seed runs **before** ``digest_before`` is recorded.  Otherwise the
    ``--expect-save-mutation`` check would compare "untouched corpus" against
    "granted corpus" and pass for the wrong reason - on the seed alone, even if
    the grant never happened.  Recording the digest after the seed is what makes
    that check measure the grant.
    """
    if collection_id < 1:
        return {"ok": False, "error": "collection id %r must be >= 1" % collection_id}
    rows = committed_collections(corpus)
    if rows is None:
        return {"ok": False, "error": "no readable collections array in the corpus"}
    position = collection_id - 1
    if position >= len(rows):
        return {
            "ok": False,
            "error": "collection %d is position %d of %d committed rows"
            % (collection_id, position, len(rows)),
        }
    row = rows[position]
    if not isinstance(row, dict):
        return {"ok": False, "error": "committed row %d is not an object" % position}

    requirement_text = row.get("item_ids")
    price_text = row.get("cashPrice")
    try:
        requirements = json.loads(requirement_text) if isinstance(
            requirement_text, str) else requirement_text
        price = int(price_text)
    except (TypeError, ValueError) as error:
        return {"ok": False, "error": "committed row %d is not readable: %s" % (position, error)}
    if not isinstance(requirements, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) for value in requirements
    ):
        return {"ok": False, "error": "committed row %d item_ids is not a list of ids" % position}

    path = save_path(corpus, player_id)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        return {"ok": False, "error": "corpus save is unreadable: %s" % error}
    try:
        store = document["maps"][0]["store"]
        info = document["playerInfo"]
    except (KeyError, IndexError, TypeError) as error:
        return {"ok": False, "error": "corpus save has no store/playerInfo: %s" % error}
    if not isinstance(store, dict) or not isinstance(info, dict):
        return {"ok": False, "error": "corpus save store/playerInfo is not an object"}

    added = []
    for item_id in requirements:
        key = str(item_id)
        held = store.get(key)
        if isinstance(held, bool) or not isinstance(held, int) or held < SEED_ITEM_QUANTITY:
            store[key] = SEED_ITEM_QUANTITY
            added.append(item_id)
    cash_before = info.get("cash")
    if isinstance(cash_before, bool) or not isinstance(cash_before, int):
        return {"ok": False, "error": "corpus save cash is not an integer: %r" % (cash_before,)}
    cash_after = max(cash_before, price * SEED_CASH_MULTIPLE)
    info["cash"] = cash_after

    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=4)
    except OSError as error:
        return {"ok": False, "error": "corpus save could not be seeded: %s" % error}

    return {
        "ok": True,
        "collection_id": collection_id,
        "position": position,
        "requirement_ids": requirements,
        "committed_price": price,
        "items_added": added,
        "quantity_per_item": SEED_ITEM_QUANTITY,
        "cash_before": cash_before,
        "cash_after": cash_after,
    }


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
    parser.add_argument(
        "--seed-collection",
        type=int,
        default=None,
        help="seed the disposable corpus save with that collection's committed "
        "requirements and price, so a grant is reachable at all; the "
        "fresh-player corpus holds neither (see seed_collection)",
    )
    parser.add_argument(
        "--route-path",
        default=COLLECT_PATH,
        help="the route this phase exercises, recorded in the summary. "
        "Defaults to %s because that is the collect phase. It is an explicit "
        "argument rather than a constant because the first version of this "
        "harness wrote the collect route into EVERY summary: the "
        "collection-live-v1 phase reported \"route\": \"POST /v1/collect\" "
        "while it had just driven POST /v1/collection, so the evidence file "
        "named the wrong route for a passing phase. A reader of that summary "
        "would have believed the collect route was the one exercised, and no "
        "assertion would have caught it, because the route under test is "
        "chosen by the Godot suite the caller passes, not by this harness."
        % COLLECT_PATH,
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

    for reserved in ("--player-id=", "--corpus="):
        if any(argument.startswith(reserved) for argument in command):
            # Both are derived in-phase from the corpus this harness starts, so a
            # caller cannot supply one: two candidate identities -- or two
            # candidate corpora -- in one phase would make every downstream
            # assertion ambiguous. Refused, not overwritten.
            print("FAIL do not pass %s; this harness supplies it in-phase" % reserved)
            print("LIVE-PHASE-SUMMARY %s" % json.dumps({"name": args.name, "ok": False}))
            return 1

    if args.route_path not in KNOWN_ROUTE_PATHS:
        print(
            "FAIL --route-path %r is not a route this harness knows; known: %s"
            % (args.route_path, ", ".join(KNOWN_ROUTE_PATHS))
        )
        print(
            "LIVE-PHASE-SUMMARY %s"
            % json.dumps({"name": args.name, "ok": False, "route_path": args.route_path})
        )
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
    seeded = {}
    if ready:
        banner = parse_banner(read_service_log(out_path, err_path))
        corpus = str(banner.get("corpus") or "")
        check("service banner names the disposable corpus", bool(corpus), corpus)
        check(
            "service banner reports exactly the %d delivered routes, in order"
            % len(EXPECTED_BANNER_ROUTES),
            banner.get("routes") == EXPECTED_BANNER_ROUTES,
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
        if player_id and args.seed_collection is not None:
            # BEFORE the pre-command digest, deliberately: see
            # `seed_collection`'s "Ordering, which matters".
            seeded = seed_collection(corpus, player_id, args.seed_collection)
            check(
                "disposable corpus seeded with collection %d's committed "
                "requirements and price" % args.seed_collection,
                bool(seeded.get("ok")),
                json.dumps(seeded, sort_keys=True),
            )
            if seeded.get("ok"):
                print("seeded corpus: %s" % json.dumps(seeded, sort_keys=True))
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
        # ...and the corpus **path**, for the same reason.  Task 7.3 asks the
        # magic phase to assert, per operation, that "exactly one leaf path
        # changed" and that all seven stored resources are byte-identical -- and
        # neither is answerable from the response alone: the response reports
        # what the server chose to say, so a client that diffed it would be
        # diffing the server's own summary of itself.  The file is the evidence.
        #
        # The corpus lives in the system temp root, is disposable, and is removed
        # on teardown; the wrapped command may **read** it and nothing else.  It
        # is passed alongside `--player-id=` rather than in place of it, and both
        # are refused if the caller supplies one, so two candidate corpora can
        # never be in play at once.
        command += ["--corpus=" + corpus]
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
        # The route the CALLER's suite exercises, not this harness's readiness
        # probe. Readiness is always a POST /v1/collect for an unknown save --
        # see the module docstring -- so deriving this from COLLECT_PATH
        # reported the collect route for the collection phase, which is the bug
        # --route-path's help text records.
        "route": "POST %s" % args.route_path,
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
        # Carried so the summary states what scaffolding the phase applied, rather
        # than leaving a reader to assume the corpus was untouched. `{}` means
        # nothing was seeded.
        "seeded": seeded,
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
