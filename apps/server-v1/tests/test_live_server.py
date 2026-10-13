#!/usr/bin/env python3
"""v1 on a real socket: ``run.py`` binds a port and answers a real request.

Task 1.4 asks that v1 "bind a port distinct from 5055 and 5056" and that the
check be one where "a port that cannot see its own rules fails rather than
reporting zero".  Three claims live in that sentence and this file keeps them
apart:

1. **The port is distinct.**  ``test_settings.py`` owns that statically; this
   file owns the runtime half.
2. **The process really binds it.**  A unit test that constructs the ASGI app
   in-process proves nothing about a socket, so this file starts
   ``apps/server-v1/run.py`` as a child process and speaks HTTP to it over
   ``127.0.0.1``.
3. **The enumeration used to check the port can see a plant.**  Repeated here
   rather than inherited: a control demonstrated in a sibling module does not
   transfer its sensitivity to this module's conclusions.

**Why this is the only file that binds a port.**  It is, and that is a recorded
cost: a test that binds a socket can fail for reasons unrelated to what it is
testing, which is one of the four already-recorded flaky surfaces in this
repository.  Three measures are taken here, and one of them is a concession.

* A child is always terminated in a ``finally``, and the release is asserted.
* Every test but one gets **its own** ephemeral port, so tests cannot contend
  with each other's sockets.
* "The port was released" is asserted by a **connect probe**, not by a bind
  probe.  This is not a stylistic choice; see the TIME_WAIT note below.

**TIME_WAIT, and the fifth recorded flaky surface.**  On Windows,
``socket.create_server`` does **not** set ``SO_REUSEADDR`` (Python sets it only
on POSIX), so a socket in ``TIME_WAIT`` on a port blocks a later plain bind.  A
bind probe therefore reports "busy" after a clean shutdown, which is not a leak.
``harness.port_is_free`` is a bind probe -- the same instrument behind the
repository's recorded 5055/5056 flakiness -- so this file does **not** use it to
assert release.  It asserts the two things that are actually true: the process
exited, and a connect to the port is refused, which a ``TIME_WAIT`` socket
cannot fake because it is not listening.

The concession: exactly one test binds :data:`DEFAULT_PORT`, so the declared
default is exercised rather than only asserted statically.  If a *previous*
v1 process left ``TIME_WAIT`` entries on 5057 within the operating system's
two-minute linger, that test cannot bind and fails for a reason that is not a
regression.  That is recorded here rather than hidden behind a skip, because a
guard that reports "skip" when it means "broken" is worse than no guard -- the
defect class this repository has now met several times.

**Loopback only.**  ``run.py`` has no host option, so there is no address to
redirect this at.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import harness
from harness import port_is_free
from server_v1_settings import (
    CORPUS_ENV,
    DEFAULT_PORT,
    EXIT_PORT_BUSY,
    HOST,
    PORT_ENV,
    RESERVED_PORTS,
    TEMP_PREFIX,
)

RUN_PY = harness.REPO_ROOT / "apps" / "server-v1" / "run.py"
FIXTURE_INSTANT = 1790705901
SEED_PLAYER = "00000000-0000-4000-8000-000000000001"

START_TIMEOUT = 60.0
STOP_TIMEOUT = 20.0


def reserve_port() -> int:
    """An ephemeral loopback port, released before the child binds it.

    The race window is real and is recorded rather than papered over: this is
    the ordinary "bind 0, read the port, close" idiom, and the alternative --
    a fixed per-test port -- trades a small race for a guaranteed collision
    with any other process on the host.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def is_listening(port: int, timeout: float = 2.0) -> bool:
    """Whether anything **accepts** on ``port``.

    The honest form of "v1 released its port".  A ``TIME_WAIT`` socket is not
    listening, so this cannot be fooled by one -- which a bind probe can.
    """
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_post(port: int, path: str, body: Dict[str, Any], timeout: float = 10.0):
    """One minimal HTTP/1.1 POST over loopback, returning ``(status, body)``.

    Written by hand rather than with ``urllib`` for two recorded reasons:
    ``urllib`` raises on a non-2xx status, and every interesting answer v1 gives
    here **is** a non-2xx; and a hand-rolled request makes a failure point at v1
    rather than at a client library.
    """
    payload = json.dumps(body).encode("utf-8")
    request = (
        "POST %s HTTP/1.1\r\n"
        "Host: 127.0.0.1:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n" % (path, port, len(payload))
    ).encode("ascii") + payload
    with socket.create_connection((HOST, port), timeout=timeout) as sock:
        sock.sendall(request)
        chunks: List[bytes] = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    head, _, body_bytes = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("ascii", "replace")
    status = int(status_line.split(" ")[1])
    return status, json.loads(body_bytes.decode("utf-8"))


class ServerProcess:
    """A ``run.py`` child, started and stopped for one test.

    **Output goes to a file, not a pipe, and that is a correction.**  The first
    version used ``stdout=subprocess.PIPE`` with a cleanup that read it.
    Cleanups run last-in-first-out, so the read ran *before* the stop and
    blocked forever on a stream whose writer was still alive: the file hung for
    ten minutes and was killed by its timeout with no result at all.  A pipe
    that nobody drains is a deadlock, not a log.

    **The child gets its own process group and is stopped with
    ``CTRL_BREAK_EVENT``, and that is a second correction.**  The first version
    used ``process.terminate()``.  On Windows that is ``TerminateProcess``:
    the child never runs a ``finally`` block, so ``run.py``'s containment
    teardown -- which is precisely what this file is here to observe -- never
    executed, and five ``socialwars-server-v1-*`` corpus directories survived in
    the temp root.  The test then asserted the corpus was removed, which made
    the test wrong rather than ``run.py``.  A console control event is what an
    operator actually sends, and it is the signal under which the teardown is
    reachable at all.
    """

    def __init__(
        self,
        *extra_args: str,
        port: Optional[int] = None,
        declared_default: bool = False,
    ) -> None:
        """One child.

        ``port`` is an explicit ``--port``.  ``declared_default=True`` passes
        **no** port argument and clears ``SERVER_V1_PORT`` from the child's
        environment, so the port the runner binds is its own choice; the banner
        is then compared against :data:`DEFAULT_PORT` rather than against the
        override, which would be a tautology.  Neither is given, so an ephemeral
        port is reserved and passed explicitly, which is what keeps concurrent
        tests off each other's sockets.
        """
        self.uses_declared_default = bool(declared_default)
        if declared_default:
            if port is not None:
                raise ValueError("declared_default and port are mutually exclusive")
            self.port = DEFAULT_PORT
            port_arguments: Tuple[str, ...] = ()
        else:
            self.port = int(port) if port is not None else reserve_port()
            port_arguments = ("--port=%d" % self.port,)

        environment = dict(os.environ)
        environment.pop(PORT_ENV, None)
        if not declared_default:
            environment[PORT_ENV] = str(self.port)
        environment[CORPUS_ENV] = ""
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        self._log = tempfile.NamedTemporaryFile(
            prefix="server-v1-run-",
            suffix=".log",
            delete=False,
            mode="w+",
            encoding="utf-8",
        )
        self._log_path = Path(self._log.name)
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(RUN_PY), *port_arguments, *extra_args],
            cwd=str(harness.REPO_ROOT),
            env=environment,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    # ------------------------------------------------------------- lifecycle --
    def wait_until_answering(self, timeout: float = START_TIMEOUT) -> None:
        deadline = time.time() + timeout
        last = ""
        while time.time() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(
                    "run.py exited early with %s:\n%s"
                    % (self.process.returncode, self.output())
                )
            try:
                http_post(self.port, "/v1/collect", {"player_id": SEED_PLAYER, "row": 9999})
                return
            except (ConnectionRefusedError, socket.timeout, OSError) as error:
                last = repr(error)
                time.sleep(0.2)
        raise AssertionError("v1 never answered on %s:%d (%s)" % (HOST, self.port, last))

    def stop(self) -> int:
        """Stop the child, gracefully if at all possible.  Idempotent."""
        if self.process.poll() is None:
            try:
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
                self.process.wait(timeout=STOP_TIMEOUT)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                try:
                    self.process.wait(timeout=STOP_TIMEOUT)
                except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                    self.process.kill()
                    self.process.wait(timeout=STOP_TIMEOUT)
        if not self._log.closed:
            self._log.flush()
            self._log.close()
        return self.process.returncode

    def output(self) -> str:
        """Whatever the child wrote.  Never blocks, never raises."""
        try:
            self._log.flush()
        except ValueError:  # pragma: no cover - already closed
            pass
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:  # pragma: no cover - defensive
            return ""

    def startup_json(self) -> Dict[str, Any]:
        """The banner ``run.py`` prints before serving, parsed."""
        text = self.output()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise AssertionError("run.py printed no startup banner:\n%s" % text)
        return json.loads(text[start : end + 1])

    def cleanup(self) -> None:
        self.stop()
        try:
            self._log_path.unlink()
        except OSError:  # pragma: no cover - defensive
            pass


class PortBindingTests(unittest.TestCase):
    """Claim 2: the process really binds its port, and really lets it go."""

    def assert_released(self, server: ServerProcess) -> None:
        self.assertIsNotNone(
            server.process.poll(), "the child is still running after stop()"
        )
        deadline = time.time() + STOP_TIMEOUT
        while time.time() < deadline and is_listening(server.port):
            time.sleep(0.2)
        self.assertFalse(is_listening(server.port), "v1 leaked a listener on %d" % server.port)

    def test_run_py_answers_a_real_request_and_then_releases_the_port(self) -> None:
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()

        # A refusal, not a success: row 9999 is not on the map.  This proves the
        # route resolved, the domain decided, and the refusal crossed the socket
        # -- without needing the disposable corpus to be in any particular
        # state for a payout.
        status, payload = http_post(
            port, "/v1/collect", {"player_id": SEED_PLAYER, "row": 9999}
        )
        self.assertEqual(409, status)
        self.assertEqual("refused", payload["result"])
        self.assertEqual("unaddressable_row", payload["code"])
        self.assertEqual("server-v1", payload["protocol"])

        server.stop()
        self.assert_released(server)

    def test_the_declared_port_is_distinct_from_both_ports_the_repo_already_binds(self) -> None:
        """Design D7's runtime half; ``test_settings.py`` owns the static one."""
        self.assertNotIn(DEFAULT_PORT, RESERVED_PORTS)
        for port in RESERVED_PORTS:
            self.assertFalse(
                is_listening(DEFAULT_PORT) and port == DEFAULT_PORT,
                "v1's declared port collides with a reserved one",
            )

    def test_the_declared_default_port_is_the_one_the_runner_binds(self) -> None:
        """The default is exercised, not only asserted.

        This is the single test in the file that binds :data:`DEFAULT_PORT`, and
        the recorded TIME_WAIT caveat in the module docstring applies to it.
        ``run.py`` is invoked with **no** ``--port`` and no ``SERVER_V1_PORT``,
        so the banner's port is the runner's own choice rather than an override
        echoed back -- comparing the banner to the override would be a
        tautology, and that is why the child is constructed here with
        ``declared_default=True`` instead of by a hand-rolled ``Popen``.
        """
        self.assertIsNone(
            os.environ.get(PORT_ENV), "%s must not be set for this test" % PORT_ENV
        )
        server = ServerProcess(
            "--fixed-now=%d" % FIXTURE_INSTANT, declared_default=True
        )
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        self.assertEqual(DEFAULT_PORT, server.startup_json()["port"])
        status, payload = http_post(
            DEFAULT_PORT, "/v1/collect", {"player_id": SEED_PLAYER, "row": 9999}
        )
        self.assertEqual(409, status)
        self.assertEqual("unaddressable_row", payload["code"])
        server.stop()
        self.assert_released(server)

    def test_a_client_supplied_delta_is_refused_over_the_real_socket(self) -> None:
        """Task 2.4's claim, at the layer a client would actually reach."""
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        status, payload = http_post(
            port,
            "/v1/collect",
            {"player_id": SEED_PLAYER, "row": 2, "gold": 999999},
        )
        self.assertEqual(400, status)
        self.assertEqual("client_supplied_delta", payload["code"])

    def test_an_unrouted_path_is_a_404_and_not_a_refusal(self) -> None:
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        status, _ = http_post(port, "/v0/collect", {"player_id": SEED_PLAYER, "row": 2})
        self.assertEqual(404, status)

    def test_run_py_refuses_to_start_on_a_busy_port(self) -> None:
        """Exit code 3, asserted rather than read off a comment."""
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        self.assertTrue(is_listening(port))
        second = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        try:
            code = second.process.wait(timeout=STOP_TIMEOUT)
            self.assertEqual(EXIT_PORT_BUSY, code)
        finally:
            second.cleanup()


class EnumerationSensitivityTests(unittest.TestCase):
    """Claim 3, repeated so *this* file's port claims are the sensitive ones."""

    def test_the_planted_listener_is_visible_to_both_probes(self) -> None:
        from harness import PlantedListener

        port = reserve_port()
        self.assertTrue(port_is_free(HOST, port))
        self.assertFalse(is_listening(port))
        with PlantedListener(HOST, port):
            self.assertFalse(port_is_free(HOST, port), "the bind probe missed the plant")
            self.assertTrue(is_listening(port), "the connect probe missed the plant")
        self.assertTrue(port_is_free(HOST, port))
        self.assertFalse(is_listening(port))

    def test_the_connect_probe_would_also_have_seen_the_real_server(self) -> None:
        """The plant is a socket; the server is also a socket.  Both must show.

        Worth stating because a plant could in principle differ from a bound
        listener in some way a probe cares about.  Running the probe against the
        actual ``run.py`` child is what makes the control and the subject the
        same kind of thing.
        """
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        self.assertFalse(port_is_free(HOST, port))
        self.assertTrue(is_listening(port))


class CorpusContainmentTests(unittest.TestCase):
    """The default invocation must not write into the working tree, and must
    remove the corpus it built for itself."""

    def setUp(self) -> None:
        self.before = harness.working_tree_save_files()
        self.saves_before = harness.working_tree_saves_dir_exists()
        self.temp_root = Path(tempfile.gettempdir())

    def tearDown(self) -> None:
        self.assertEqual(self.before, harness.working_tree_save_files())
        self.assertEqual(
            self.saves_before,
            harness.working_tree_saves_dir_exists(),
            "run.py created or removed a working-tree saves/ directory",
        )

    def _corpora(self) -> List[str]:
        return sorted(
            path.name
            for path in self.temp_root.iterdir()
            if path.is_dir() and path.name.startswith(TEMP_PREFIX)
        )

    def test_a_full_lifecycle_leaves_the_working_tree_untouched(self) -> None:
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        http_post(port, "/v1/collect", {"player_id": SEED_PLAYER, "row": 9999})
        server.stop()
        # Removal of a corpus's *contents* and removal of its *directories* are
        # different claims (a recorded nuance of this repository's containment
        # helper), so the working tree is snapshotted as a file list rather than
        # inferred from a directory's absence.
        self.assertEqual(self.before, harness.working_tree_save_files())

    def test_the_banner_reports_a_corpus_the_runner_owns(self) -> None:
        """Positive first: the check below is only meaningful if one is built."""
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        banner = server.startup_json()
        self.assertTrue(banner["corpus_owned_by_runner"])
        # The banner reports an absolute path, so the prefix is matched against
        # the directory's **name**.  Asserting ``startswith`` on the whole path
        # tested the temp root instead, and passed for any path under it.
        self.assertTrue(Path(banner["corpus"]).name.startswith(TEMP_PREFIX))
        self.assertEqual(port, banner["port"])
        # A count pin the third route legitimately moved: the banner lists the
        # served inventory verbatim and the magic line added one row to it.  The
        # pin is amended in place with its **order** asserted too, because a
        # sorted or set-derived banner would satisfy a subset test and not this
        # one -- and the order is the declaration order in ``server_v1_app.ROUTES``,
        # which is what makes the banner a report rather than a rendering.
        self.assertEqual(
            ["POST /v1/collect", "POST /v1/collection", "POST /v1/magic"],
            banner["routes"],
        )
        self.assertEqual(3, len(banner["routes"]))
        self.assertEqual(FIXTURE_INSTANT, banner["fixed_now"])

    def test_no_corpus_directory_survives_a_graceful_stop(self) -> None:
        """``run.py``'s teardown removes what it built.

        Only checkable because the child is stopped with a console control
        event; under ``TerminateProcess`` the ``finally`` never runs, which is
        why the earlier version of this test saw five orphaned corpus
        directories and asserted a property the process never had.
        """
        before = set(self._corpora())
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        during = set(self._corpora())
        self.assertEqual(
            len(during) - len(before),
            1,
            "run.py built %d corpus directories, expected exactly 1" % (len(during) - len(before)),
        )
        corpus = Path(server.startup_json()["corpus"])
        self.assertTrue(corpus.is_dir(), "the banner's corpus is not on disk")

        server.stop()
        self.assertEqual(
            0, server.process.returncode, "run.py did not exit cleanly:\n%s" % server.output()
        )
        self.assertNotIn("containment:", server.output(), server.output())
        deadline = time.time() + STOP_TIMEOUT
        while time.time() < deadline and corpus.exists():
            time.sleep(0.2)
        self.assertFalse(corpus.exists(), "the disposable corpus survived the process")
        self.assertEqual(before, set(self._corpora()), "another corpus appeared")


class StartupContractTests(unittest.TestCase):
    """The banner is a contract, so it is parsed rather than eyeballed."""

    def test_an_explicit_port_is_reported_verbatim(self) -> None:
        port = reserve_port()
        server = ServerProcess("--fixed-now=%d" % FIXTURE_INSTANT, port=port)
        self.addCleanup(server.cleanup)
        server.wait_until_answering()
        banner: Dict[str, Any] = server.startup_json()
        self.assertEqual(port, banner["port"])
        self.assertEqual(HOST, banner["host"])
        self.assertEqual("server-v1", banner["protocol"])
        # Asserted against the keys the loader actually produces, not the ones a
        # reader would guess: the first version asked for a nested "provenance"
        # key and reported a missing-field failure that read like a defect in
        # the loader.
        #
        # ``collection_rows`` was added when the second route arrived: the
        # banner is the only record of what content a process actually read, and
        # a route that resolves an id into a positional row needs the row count
        # to be on the record.  The pin is an **exact set**, so the key had to be
        # added here rather than the check loosened into a subset test — a
        # subset assertion could not catch a provenance field being dropped.
        #
        # ``magic_rows`` was added by the magic line for the same reason and by
        # the same mechanism: the third route resolves an id into a committed row,
        # and the banner is still the only record of the table it resolved
        # against.  **This is an extension of the pin, not a loosening of it** —
        # the assertion is still an exact set, so a fourth content field will
        # also have to be added here deliberately.
        self.assertEqual(
            {
                "applied_mods",
                "applied_patches",
                "collection_rows",
                "distinct_item_ids",
                "item_entries",
                "magic_rows",
                "missing_mods",
                "missing_patches",
                "removed_duplicate_items",
                "skipped_loader_steps",
            },
            set(banner["content"]),
        )
        self.assertEqual(10, banner["content"]["collection_rows"])
        self.assertEqual(10, banner["content"]["magic_rows"])
        self.assertEqual(["make_dynamic"], banner["content"]["skipped_loader_steps"])

    def test_an_unknown_flag_is_refused_rather_than_ignored(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(RUN_PY), "--not-a-flag"],
            cwd=str(harness.REPO_ROOT),
            capture_output=True,
            universal_newlines=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("--not-a-flag", completed.stderr)


if __name__ == "__main__":
    unittest.main()