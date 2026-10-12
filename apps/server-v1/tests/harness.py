#!/usr/bin/env python3
"""Shared harness for the Server v1 tests.

* put ``apps/server-v1`` on ``sys.path`` with absolute paths and force
  ``sys.dont_write_bytecode``, so running the suite never writes a
  ``__pycache__`` beside the application modules;
* re-export the corpus helpers, so a test module has one import for
  "disposable store";
* provide the **planted control** helper task 1.4 requires.

No network beyond loopback, no Flash, no Ruffle, no ActionScript, and no
browser: the only socket any test opens is on ``127.0.0.1``, and the only one it
*connects* to is v1's own port, started by the test.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.dont_write_bytecode = True

TESTS_DIR = Path(__file__).resolve().parent
SERVICE_DIR = TESTS_DIR.parent
REPO_ROOT = SERVICE_DIR.parents[1]

for _path in (str(TESTS_DIR), str(SERVICE_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "godot-building-collect"
COLLECT_STEP = FIXTURE_ROOT / "steps" / "command_collect"

from server_v1_corpus import (  # noqa: E402,F401
    REPO_ROOT as CORPUS_REPO_ROOT,
    ContainmentError,
    assert_port_free,
    build_corpus,
    corpus_save_bytes,
    corpus_save_path,
    port_is_free,
    remove_corpus,
    seed_document,
    seed_player_id,
    working_tree_save_files,
    working_tree_saves_dir_exists,
)
from server_v1_content import load_content  # noqa: E402,F401
from server_v1_repository import FilesystemSaveRepository  # noqa: E402,F401
from server_v1_settings import DEFAULT_PORT, HOST  # noqa: E402,F401


class PlantedListener:
    """A socket bound on a port, so an enumeration can be shown to *see* it.

    Task 1.4 asks for the check that "a port that cannot see its own rules fails
    rather than reporting zero".  A bare "is the port free?" assertion is
    vacuously true when the assertion mechanism itself is broken — it would
    report *free* for a port something is listening on and the containment story
    would still read as a pass.  The control here is therefore:

    1. bind a real listener on the port under test;
    2. run **the same enumeration** the assertion uses;
    3. require it to report the port as **not** free;
    4. close the listener and require the enumeration to report free again.

    A step that cannot fail makes every later step of this line's containment
    evidence worth nothing, so it is part of the suite rather than a comment.
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._socket: socket.socket = None  # type: ignore[assignment]

    def __enter__(self) -> "PlantedListener":
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self.port))
        self._socket.listen(1)
        return self

    def __exit__(self, *exc_info: object) -> bool:
        if self._socket is not None:
            self._socket.close()
        return False


__all__ = [
    "COLLECT_STEP",
    "FIXTURE_ROOT",
    "PlantedListener",
    "REPO_ROOT",
    "SERVICE_DIR",
    "TESTS_DIR",
    "ContainmentError",
    "assert_port_free",
    "build_corpus",
    "corpus_save_bytes",
    "corpus_save_path",
    "load_content",
    "port_is_free",
    "remove_corpus",
    "seed_document",
    "seed_player_id",
    "working_tree_save_files",
    "working_tree_saves_dir_exists",
]
