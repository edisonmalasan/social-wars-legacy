#!/usr/bin/env python3
"""Start the Compatibility API v0 service on loopback (design D3).

Documented start command, from the repository root, with the pinned
interpreter (``python`` below is the pinned CPython 3.9.13 executable, never
the PATH interpreter)::

    python -B apps/compat-api/run.py

The service binds **only** ``127.0.0.1`` at port ``5056`` (``--port`` /
``COMPAT_API_PORT`` override; there is no host option by design).

Corpus mechanics — the legacy modules resolve every path from the process
working directory, so the process chdirs into a *disposable corpus* before the
legacy imports:

* default: a fresh temporary corpus is built from ``config/``, ``mods/`` and
  ``villages/`` and seeded from ``tests/saves/fresh-player.json``, then
  removed when the server stops;
* ``--corpus PATH`` (or ``COMPAT_CORPUS``): use ``PATH`` — built and seeded
  when it does not exist yet, used as-is when it does. A corpus that this run
  created is removed on exit unless ``--keep-corpus`` is given; a corpus that
  already existed is never removed.

Exit codes:

- ``0`` — server stopped cleanly (including Ctrl+C / Ctrl+Break)
- ``2`` — usage, environment, corpus layout, or legacy initialization failure
- ``3`` — the requested port is already in use
- ``4`` — the server failed to run for any other reason
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import compat_legacy  # noqa: E402
import compat_service  # noqa: E402
from hashing import directory_entries  # noqa: E402

EXIT_OK = 0
EXIT_ENVIRONMENT = 2
EXIT_PORT_BUSY = 3
EXIT_SERVER = 4

TEMP_PREFIX = "socialwars-compat-"


def port_is_free(host: str, port: int) -> bool:
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def parse_port(raw: Optional[str]) -> int:
    if raw is None or raw == "":
        return compat_service.DEFAULT_PORT
    try:
        port = int(raw)
    except (TypeError, ValueError):
        raise SystemExit(EXIT_ENVIRONMENT)
    if not 1 <= port <= 65535:
        raise SystemExit(EXIT_ENVIRONMENT)
    return port


def prepare_corpus(requested: Optional[str]) -> "tuple[Path, bool]":
    """Return ``(corpus_path, created_by_this_run)``."""
    if requested:
        path = Path(requested).expanduser().resolve()
        if path.exists():
            return path, False
        record = compat_legacy.build_corpus(path)
        print(
            "compat-api: built corpus at %s (pid %s, save sha256 %s)"
            % (record["corpus"], record["pid"], record["save_sha256"])
        )
        return path, True
    path = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    record = compat_legacy.build_corpus(path)
    print(
        "compat-api: built disposable corpus at %s (pid %s, save sha256 %s)"
        % (record["corpus"], record["pid"], record["save_sha256"])
    )
    return path, True


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Compatibility API v0 on loopback (127.0.0.1:5056 by default).",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="TCP port to bind on 127.0.0.1 (default: %d, env COMPAT_API_PORT)"
        % compat_service.DEFAULT_PORT,
    )
    parser.add_argument(
        "--corpus",
        default=None,
        help="corpus directory to serve from (default: disposable temp corpus, "
        "env COMPAT_CORPUS)",
    )
    parser.add_argument(
        "--keep-corpus",
        action="store_true",
        help="do not delete a corpus this run created",
    )
    args = parser.parse_args(argv)

    raw_port = args.port if args.port is not None else os.environ.get("COMPAT_API_PORT")
    try:
        port = parse_port(raw_port)
    except SystemExit:
        print(
            "compat-api: invalid port %r (expected 1-65535)" % (raw_port,),
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT

    # Windows delivers Ctrl+Break as SIGBREAK, whose default disposition is to
    # terminate the process without unwinding; map it onto KeyboardInterrupt so
    # both console interrupts take the documented clean-stop path below.
    try:
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    except (AttributeError, OSError, ValueError):  # pragma: no cover - non-Windows
        pass

    requested_corpus = args.corpus if args.corpus is not None else os.environ.get("COMPAT_CORPUS")
    created = False
    corpus: Optional[Path] = None
    try:
        corpus, created = prepare_corpus(requested_corpus)
        problems = compat_legacy.corpus_layout_problems(corpus)
        if problems:
            print(
                "compat-api: corpus %s is missing: %s"
                % (corpus, ", ".join(problems)),
                file=sys.stderr,
            )
            return EXIT_ENVIRONMENT
        if not port_is_free(compat_service.HOST, port):
            print(
                "compat-api: port %d on %s is already in use"
                % (port, compat_service.HOST),
                file=sys.stderr,
            )
            return EXIT_PORT_BUSY

        compat_legacy.initialize(corpus)
        app = compat_service.create_app()
        boot = compat_legacy.current()
        save_files = [
            path for path, _digest in directory_entries(boot.corpus / "saves", "saves")
        ]
        print(
            "compat-api: Compatibility API v0 (protocol %s) starting on "
            "http://%s:%d - loopback only, read-only"
            % (compat_service.PROTOCOL, compat_service.HOST, port)
        )
        print("compat-api: corpus %s (%d save file(s))" % (corpus, len(save_files)))
        print(
            "compat-api: endpoints GET /v0/session, POST /v0/bootstrap; "
            "game version %s" % boot.game_version
        )
        app.run(
            host=compat_service.HOST,
            port=port,
            debug=False,
            threaded=False,
            use_reloader=False,
        )
        return EXIT_OK
    except KeyboardInterrupt:
        print("compat-api: interrupted; shutting down")
        return EXIT_OK
    except compat_legacy.LegacyBootError as error:
        print("compat-api: legacy initialization failed [%s]: %s" % (error.code, error), file=sys.stderr)
        return EXIT_ENVIRONMENT
    except OSError as error:
        print("compat-api: server could not bind or run: %s" % error, file=sys.stderr)
        return EXIT_PORT_BUSY if port_is_free(compat_service.HOST, port) else EXIT_SERVER
    except Exception as error:  # pragma: no cover - unexpected failure path
        print("compat-api: server failed: %s" % error, file=sys.stderr)
        return EXIT_SERVER
    finally:
        if corpus is not None and created and not args.keep_corpus:
            # The legacy modules chdir'd into the corpus, and Windows refuses
            # to delete a directory that is still a live process's working
            # directory, so leave the corpus before removing it.
            try:
                os.chdir(str(HERE))
            except OSError:  # pragma: no cover - HERE always exists
                pass
            shutil.rmtree(str(corpus), ignore_errors=True)
            if corpus.exists():
                print(
                    "compat-api: WARNING corpus %s was not fully removed" % corpus,
                    file=sys.stderr,
                )
            else:
                print("compat-api: removed corpus %s" % corpus)
        elif corpus is not None and created:
            print("compat-api: kept corpus %s" % corpus)


if __name__ == "__main__":
    sys.exit(main())
