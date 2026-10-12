#!/usr/bin/env python3
"""Disposable corpora for Server v1, and the containment assertions on them.

Nothing in ``apps/server-v1/`` writes into the working tree, ever.  Both the
test suite and ``run.py`` build a **corpus** under the system temp root: a
directory holding a copy of the committed content, a copy of the mods list, and
one seeded save.  ``tests/test_containment.py`` asserts the properties that make
that claim checkable rather than aspirational.

A corpus for v1 needs three things and **not** four.  It copies:

* ``config/`` — the committed configuration, the patches, and the patch list;
* ``mods/`` — the mod list, read the same way legacy reads it;
* ``saves/<pid>.save.json`` — the seeded save, named as legacy names it.

It deliberately does **not** copy ``villages/``: v1 loads no static village and
no quest file in this line, and copying preserved directories a service never
reads would make a containment claim about files it does not control.

**"Corpus removed" and "corpus contents removed" are different claims.**  The
Compatibility API's ``remove_corpus`` calls ``shutil.rmtree`` with
``ignore_errors=True``, which removes the files *and* the directories but
suppresses any error doing so — so on a locked file it can leave a partial tree
behind while reporting nothing.  :func:`remove_corpus` here does the same removal
and then **asserts** the directory is gone, raising :class:`ContainmentError` if
anything survived.  ``tests/test_containment.py`` runs the whole
build/execute/remove cycle **twice** (task 3.3: "re-running the check so a
single pass is not mistaken for a guarantee") and asserts both the working tree
is unchanged and the port is free after each.
"""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from server_v1_repository import FilesystemSaveRepository
from server_v1_settings import TEMP_PREFIX

#: Where the committed content lives, relative to the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SAVE = REPO_ROOT / "tests" / "saves" / "fresh-player.json"

#: Directories a corpus copies from the repository.
CORPUS_COPY_DIRS: Tuple[str, ...] = ("config", "mods")

#: Directories a corpus deliberately does not copy, and why.  Recorded rather
#: than omitted: an absent entry and an unrecorded one look identical until
#: someone asks why ``villages/`` is missing.
CORPUS_OMITTED_DIRS: Dict[str, str] = {
    "villages": "v1 loads no static village and no quest file in this line",
    "assets": "v1 reads no asset in this line",
    "tests": "preserved fixtures and saves are read from the repository, never copied",
}


class ContainmentError(Exception):
    """A containment assertion failed."""


def seed_document() -> Dict[str, Any]:
    """The committed seed save, parsed.

    Read fresh each call so a test cannot mutate the process-wide seed by
    accident.
    """
    if not SEED_SAVE.is_file():
        raise ContainmentError("seed save not found: %s" % SEED_SAVE)
    return json.loads(SEED_SAVE.read_text(encoding="utf-8"))


def seed_player_id(document: Optional[Dict[str, Any]] = None) -> str:
    """The seed's ``playerInfo.pid`` as a string, which is the save's name."""
    doc = seed_document() if document is None else document
    try:
        pid = doc["playerInfo"]["pid"]
    except (KeyError, TypeError) as error:
        raise ContainmentError("seed save has no playerInfo.pid: %s" % error)
    text = str(pid)
    if not text:
        raise ContainmentError("seed save playerInfo.pid is empty")
    return text


def build_corpus(
    mutate: Optional[Callable[[Dict[str, Any]], None]] = None,
    directory: Optional[Path] = None,
) -> Path:
    """Create a disposable corpus in the system temp root; return its path.

    With ``mutate`` ``None`` the seed file is copied **verbatim**, so the corpus
    save keeps the seed's own bytes — including its CRLF line endings — which
    is what lets a test assert that a refused request leaves those exact bytes
    untouched rather than a re-rendered equivalent.

    With a ``mutate`` the parsed document is written in v1's own LF form, so a
    test that needs a specific row state does not start from bytes v1 could
    never have written.
    """
    destination = Path(
        directory if directory is not None else tempfile.mkdtemp(prefix=TEMP_PREFIX)
    )
    if destination.exists() and any(destination.iterdir()):
        raise ContainmentError("corpus destination is not empty: %s" % destination)

    for name in CORPUS_COPY_DIRS:
        source = REPO_ROOT / name
        if not source.is_dir():
            raise ContainmentError("committed directory missing: %s" % source)
        shutil.copytree(str(source), str(destination / name))

    saves = destination / "saves"
    saves.mkdir(parents=True, exist_ok=True)
    pid = seed_player_id()
    target = saves / ("%s%s" % (pid, FilesystemSaveRepository.FILE_SUFFIX))
    if mutate is None:
        shutil.copy2(str(SEED_SAVE), str(target))
    else:
        document = seed_document()
        mutate(document)
        with open(target, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, indent=4)
    return destination


def remove_corpus(corpus: Optional[Path]) -> None:
    """Remove a corpus and **assert** it is gone.

    The assertion is the point.  ``shutil.rmtree(..., ignore_errors=True)``
    alone reports success whether or not it succeeded, so a partially removed
    corpus would look exactly like a removed one.
    """
    if corpus is None:
        return
    corpus = Path(corpus)
    if not corpus.exists():
        return
    shutil.rmtree(str(corpus), ignore_errors=True)
    if corpus.exists():
        survivors: List[str] = []
        for path in sorted(corpus.rglob("*")):
            survivors.append(str(path.relative_to(corpus)))
        raise ContainmentError(
            "corpus was not removed; %d entries survive: %s"
            % (len(survivors), survivors[:10])
        )


def corpus_save_path(corpus: Path, player_id: Optional[str] = None) -> Path:
    """The file one player's save occupies inside a corpus."""
    pid = seed_player_id() if player_id is None else player_id
    return Path(corpus) / "saves" / ("%s%s" % (pid, FilesystemSaveRepository.FILE_SUFFIX))


def corpus_save_bytes(corpus: Path, player_id: Optional[str] = None) -> bytes:
    """The raw bytes of a corpus save — read in binary, never through text mode.

    Line endings are the whole point of a byte-identical assertion, so this
    returns ``bytes`` and every comparison of it is between two ``bytes``.
    """
    return corpus_save_path(corpus, player_id).read_bytes()


def working_tree_save_files() -> List[str]:
    """Every save file in the working tree, relative and sorted.

    ``saves/`` is the directory legacy and v0 both create at run time, and
    ``tests/saves/`` is preserved material.  This line must never write into
    either; ``tests/test_containment.py`` snapshots this before and after every
    execution.
    """
    found: List[str] = []
    for relative in ("saves", "tests/saves"):
        directory = REPO_ROOT / relative
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                found.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    return sorted(found)


def working_tree_saves_dir_exists() -> bool:
    """Whether a working-tree ``saves/`` directory exists at all.

    Separate from :func:`working_tree_save_files` because the two claims are
    different: an empty ``saves/`` directory still breaks
    ``apps/client-godot/verify-boot.ps1``'s recorded-absent guard even with no
    files in it, so a corpus-cleanup check that only counted files would miss
    it.
    """
    return (REPO_ROOT / "saves").is_dir()


def port_is_free(host: str, port: int) -> bool:
    """Whether ``(host, port)`` can be bound right now.

    A **bind** probe, matching ``compat_test_harness.port_is_free``.  On Windows
    it cannot distinguish "in use" from "cannot bind", which is one of the four
    already-recorded flaky surfaces this repository has around port assertions;
    :func:`assert_port_free` is therefore written to be **re-runnable** and is
    re-run by ``tests/test_containment.py`` rather than trusted once.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def assert_port_free(host: str, port: int, attempts: int = 3) -> bool:
    """Assert a port is free, allowing ``attempts`` tries before giving up.

    Three attempts with no sleep between them, deliberately: the recorded
    flakiness is Windows refusing a bind for a moment, not a slow listener, so
    a retry is the right response and a long sleep would only make a failure
    slower to report.
    """
    outcomes = [port_is_free(host, port) for _ in range(attempts)]
    if any(outcomes):
        return True
    raise ContainmentError(
        "port %s:%d was not free in %d attempts" % (host, port, attempts)
    )


__all__ = [
    "CORPUS_COPY_DIRS",
    "CORPUS_OMITTED_DIRS",
    "REPO_ROOT",
    "SEED_SAVE",
    "ContainmentError",
    "assert_port_free",
    "build_corpus",
    "corpus_save_bytes",
    "corpus_save_path",
    "port_is_free",
    "remove_corpus",
    "seed_document",
    "seed_player_id",
    "working_tree_save_files",
    "working_tree_saves_dir_exists",
]
