#!/usr/bin/env python3
"""Run Server v1 on its own loopback port, over a disposable corpus.

**Loopback only.**  ``server_v1_settings.HOST`` is ``127.0.0.1`` and there is
deliberately no host option, for the same reason ``apps/compat-api/run.py`` has
none: a server that can be pointed at a routable interface is a server that can
be reached from off-host.

**Containment.**  With no ``SERVER_V1_CORPUS`` in the environment, ``run.py``
builds a disposable corpus in the system temp root from the committed content
and the committed seed save, serves against it, and removes it on exit — so the
default invocation cannot write into the working tree.  With the variable set,
it serves against the named directory and does **not** remove it, because a
directory the operator chose is not the runner's to delete.  Either way the port
is asserted free before binding and reported released after.

Exit codes are the module's process-level contract, not gameplay claims:
``0`` clean, ``2`` environment unusable, ``3`` the port is not free,
``4`` the server exited with an error.

Two additions are recorded rather than hidden:

* **uvicorn is a dependency** design D4 does not name (see ``requirements.txt``).
  FastAPI cannot bind a port without an ASGI server, and task 1.4 requires v1 to
  bind its own port, so the addition is forced by the milestone's own tasks.
* **the clock is injectable** (``--fixed-now``), so a test can serve v1 and
  compare it against the executed-legacy fixture's recorded capture instant.
  With no flag the service reads the real clock, which is its production
  behaviour.

**Two defects found by ``tests/test_live_server.py``, both fixed here rather than
in the test, because in both cases the test was right and this module was
wrong.**

1. *``EXIT_PORT_BUSY = 3`` was unreachable.*  The first version handed
   ``uvicorn.run(app, host=..., port=...)`` the port and wrapped it in
   ``except OSError``.  uvicorn does not raise: on a bind failure it logs
   ``error while attempting to bind on address`` and calls ``sys.exit(1)``
   itself, so the ``OSError`` handler never ran and the process exited **1**.
   Measured on this host by holding the port and starting the runner: exit
   ``1``, not ``3``, with the documented contract contradicting the
   behaviour.  The port is now bound by **this** module through
   ``uvicorn.Config.bind_socket()`` and handed to ``Server.run(sockets=...)``,
   so a bind failure is an ordinary ``OSError`` raised at a point whose exit
   code is chosen here.  This is also strictly better operationally: the port
   is bound before the banner is printed, so the banner never claims a port
   the process does not hold.

2. *There was no graceful stop on Windows, so the containment teardown could
   never run.*  ``run.py`` removes the corpus it built in a ``finally``.  On
   Windows neither of the signals a supervisor actually sends reaches that
   block: ``Popen.terminate()`` is ``TerminateProcess``, which kills the
   process outright, and ``CTRL_BREAK_EVENT`` — sent to a
   ``CREATE_NEW_PROCESS_GROUP`` child — raises **no** Python exception unless a
   handler is installed for it.  Both were measured with a minimal child
   process: without a handler the child died with ``0xC000013A``
   (``STATUS_CONTROL_C_EXIT``) and printed nothing, so ``finally`` was skipped.
   Six ``socialwars-server-v1-*`` corpus directories survived in the temp root
   that way.  :func:`_install_console_handlers` now registers ``SIGINT`` **and**
   ``SIGBREAK``, which was re-measured to deliver a ``KeyboardInterrupt`` and
   run the teardown.  ``SIGTERM`` is registered too, so the same holds for a
   POSIX supervisor.

3. *"the port is asserted free before binding" was never true.*  The sentence
   was in this docstring from the first draft and no line performed the check.
   The fix in (1) made that worse rather than better: uvicorn's
   ``bind_socket`` sets ``SO_REUSEADDR``, which on Windows permits binding a
   port another process is *already listening on*, so a second ``run.py``
   started successfully and both served on one port.  ``main`` now calls
   ``assert_port_free`` first -- an instrument that deliberately does **not**
   set ``SO_REUSEADDR``, which is exactly what lets it see the other listener.

All three were found by one test file, ``tests/test_live_server.py``, and none
of the three was in that file: each time the module's own prose turned out to
be the wrong thing to believe.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import List, Optional

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402

from server_v1_app import ROUTES, create_app  # noqa: E402
from server_v1_content import load_content  # noqa: E402
from server_v1_corpus import (  # noqa: E402
    REPO_ROOT,
    ContainmentError,
    assert_port_free,
    build_corpus,
    remove_corpus,
)
from server_v1_repository import FilesystemSaveRepository  # noqa: E402
from server_v1_settings import (  # noqa: E402
    CORPUS_ENV,
    DEFAULT_PORT,
    EXIT_ENVIRONMENT,
    EXIT_OK,
    EXIT_PORT_BUSY,
    EXIT_SERVER,
    HOST,
    PORT_ENV,
    PROTOCOL,
    assert_port_is_distinct,
)


def _install_console_handlers() -> List[str]:
    """Make a console interrupt reach this process's ``finally`` blocks.

    Returns the signals it actually registered, so the caller can report them
    rather than assume.  A signal this platform does not have is skipped, not
    raised: ``SIGBREAK`` exists only on Windows and registering it on POSIX is
    an ``AttributeError``.

    The handler raises :class:`KeyboardInterrupt` rather than shutting down
    itself.  That is deliberate: the cleanup this exists to enable is the
    ``finally`` in :func:`main`, and a handler that merely set a flag would let
    ``uvicorn`` keep serving, so the corpus would still not be removed.  The
    interrupt is caught immediately below the serve call.

    **Registering a handler is what makes the signal work at all.**  Measured
    on this host: a ``CREATE_NEW_PROCESS_GROUP`` child sent
    ``CTRL_BREAK_EVENT`` died with ``0xC000013A`` and printed nothing when no
    handler was installed, and delivered a ``KeyboardInterrupt`` once one was.
    Without this function the containment teardown in :func:`main` is
    unreachable on Windows, which is what left six orphaned corpus directories
    in the temp root.
    """
    def handler(signum: int, frame: object) -> None:  # noqa: ANN001 - signal signature
        raise KeyboardInterrupt(signum)

    registered: List[str] = []
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        number = getattr(signal, name, None)
        if number is None:
            continue
        try:
            signal.signal(number, handler)
        except (OSError, ValueError):  # pragma: no cover - platform dependent
            continue
        registered.append(name)
    return registered


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Serve %s on %s:%d (loopback only)." % (PROTOCOL, HOST, DEFAULT_PORT),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get(PORT_ENV, DEFAULT_PORT)),
        help="loopback TCP port to bind (default %d, env %s)" % (DEFAULT_PORT, PORT_ENV),
    )
    parser.add_argument(
        "--corpus",
        default=os.environ.get(CORPUS_ENV),
        help="serve an existing corpus directory instead of building a disposable one",
    )
    parser.add_argument(
        "--fixed-now",
        type=int,
        default=None,
        help="serve with a pinned clock (Unix seconds) instead of the real clock",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        assert_port_is_distinct()
    except AssertionError as error:
        sys.stderr.write("environment: %s\n" % error)
        return EXIT_ENVIRONMENT

    owned_corpus: Optional[Path] = None
    if args.corpus:
        corpus = Path(args.corpus)
    else:
        try:
            corpus = owned_corpus = build_corpus()
        except ContainmentError as error:
            sys.stderr.write("environment: %s\n" % error)
            return EXIT_ENVIRONMENT

    try:
        content = load_content(corpus)
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        sys.stderr.write("environment: committed content is unusable: %s\n" % error)
        remove_corpus(owned_corpus)
        return EXIT_ENVIRONMENT

    repository = FilesystemSaveRepository(corpus)
    clock = (lambda: args.fixed_now) if args.fixed_now is not None else (lambda: int(time.time()))

    app = create_app(content, repository, clock)

    # The port is asserted free **before** it is bound, and this is not
    # redundant with the bind.  It was, until this line: the module docstring
    # claimed the check and no code performed it.  uvicorn's ``bind_socket``
    # sets ``SO_REUSEADDR``, which on Windows permits binding a port another
    # process is already listening on -- so a second ``run.py`` did not fail,
    # it *joined*, and both served on one port.  ``port_is_free`` deliberately
    # does not set that option, which is what makes it able to see the other
    # listener at all.
    try:
        assert_port_free(HOST, args.port)
    except ContainmentError as error:
        sys.stderr.write("port: %s\n" % error)
        remove_corpus(owned_corpus)
        return EXIT_PORT_BUSY

    # The port is bound here, before the server starts and before the banner is
    # printed, so a bind failure is an OSError this module handles and can name
    # an exit code for.  Handing the port to uvicorn instead would let uvicorn
    # sys.exit(1) from inside its own startup, which is what made
    # EXIT_PORT_BUSY unreachable until it was found by measurement.
    config = uvicorn.Config(app, host=HOST, port=args.port, log_level="warning")
    try:
        socket_ = config.bind_socket()
    except OSError as error:
        sys.stderr.write("port: could not bind %s:%d: %s\n" % (HOST, args.port, error))
        remove_corpus(owned_corpus)
        return EXIT_PORT_BUSY

    sys.stdout.write(
        json.dumps(
            {
                "protocol": PROTOCOL,
                "host": HOST,
                "port": args.port,
                "corpus": str(corpus),
                "corpus_owned_by_runner": owned_corpus is not None,
                "content": content.provenance(),
                # Read from the app's own inventory rather than transcribed, so
                # the banner cannot under-report a delivered route: a third
                # route would be listed by ``ROUTES`` and not by this list.
                "routes": sorted(ROUTES),
                "fixed_now": args.fixed_now,
            },
            indent=4,
            sort_keys=True,
        )
        + "\n"
    )
    sys.stdout.flush()

    _install_console_handlers()
    server = uvicorn.Server(config)
    try:
        server.run(sockets=[socket_])
    except OSError as error:
        sys.stderr.write("server: %s\n" % error)
        remove_corpus(owned_corpus)
        return EXIT_SERVER
    except KeyboardInterrupt:
        # Reached only if the handler's interrupt escapes uvicorn's own
        # shutdown path.  Not a failure: the interrupt asked for the stop.
        pass
    finally:
        # Containment: the port is released by the time the socket closes, and
        # the corpus this runner created is removed.  Both are asserted rather
        # than assumed, and a failure to remove is reported on stderr with the
        # path, because a half-removed corpus is a fact the operator needs.
        try:
            assert_port_free(HOST, args.port)
        except ContainmentError as error:
            sys.stderr.write("containment: %s\n" % error)
        if owned_corpus is not None:
            try:
                remove_corpus(owned_corpus)
            except ContainmentError as error:
                sys.stderr.write("containment: %s\n" % error)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
