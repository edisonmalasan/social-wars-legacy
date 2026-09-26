#!/usr/bin/env python3
"""Shared harness for the Compatibility API v0 tests.

Responsibilities:

* put ``apps/compat-api`` and the repository root on ``sys.path`` using
  absolute paths (the tests chdir into corpora), and force
  ``sys.dont_write_bytecode`` so no ``__pycache__`` is written next to
  preserved legacy sources;
* build disposable corpora (config + mods + villages + seeded save) in the
  system temp root and remove them afterwards;
* load the committed legacy fixtures and the field-stability record;
* compare a compat payload with a captured legacy payload field-by-field,
  pruning exactly the paths the field-stability record documents as
  time-dependent, and returning the pruned values so every normalization is
  asserted rather than assumed;
* provide a socket guard used to prove the offline parity runs open no
  connection at all.

Corpora live under the system temp root, never in the working tree.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Pattern, Tuple

sys.dont_write_bytecode = True

TESTS_DIR = Path(__file__).resolve().parent
COMPAT_DIR = TESTS_DIR.parent
REPO_ROOT = COMPAT_DIR.parents[1]

for _path in (str(TESTS_DIR), str(COMPAT_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "godot-compatibility-boot"
SEED_SAVE = REPO_ROOT / "tests" / "saves" / "fresh-player.json"

import compat_legacy  # noqa: E402
import compat_service  # noqa: E402
from field_stability import json_diff  # noqa: E402
from hashing import directory_entries  # noqa: E402

CORPUS_TEMP_PREFIX = "socialwars-compat-test-"

# Prune lists are exactly the paths field-stability.json documents.
CONFIG_PRUNES: List[Pattern[str]] = [re.compile(r"^/darts_items/\d+/start_date$")]
PLAYER_PRUNES: List[Pattern[str]] = [
    re.compile(r"^/timestamp$"),
    re.compile(r"^/playerInfo/last_logged_in$"),
]


# ---------------------------------------------------------------- fixtures --
def load_field_stability() -> Dict[str, object]:
    return json.loads((FIXTURES / "field-stability.json").read_text(encoding="utf-8"))


def load_step(step: str) -> Dict[str, object]:
    """Load one captured step: request, before, response, after, metadata."""
    base = FIXTURES / "steps" / step
    record: Dict[str, object] = {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads((base / "response.meta.json").read_text(encoding="utf-8")),
        "body": (base / "response.body").read_bytes(),
    }
    save_list = base / "save-list.json"
    if save_list.is_file():
        record["save_list"] = json.loads(save_list.read_text(encoding="utf-8"))
    return record


def load_seed() -> Dict[str, object]:
    return json.loads(SEED_SAVE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ corpus --
def build_test_corpus(mutate: Optional[Callable[[Dict[str, object]], None]] = None) -> Path:
    """Disposable corpus in the system temp root (caller removes it)."""
    destination = Path(tempfile.mkdtemp(prefix=CORPUS_TEMP_PREFIX))
    compat_legacy.build_corpus(destination, mutate=mutate)
    return destination


def remove_corpus(corpus: Optional[Path]) -> None:
    if corpus is not None and corpus.exists():
        shutil.rmtree(str(corpus), ignore_errors=True)


def save_hashes(corpus: Path) -> List[Dict[str, str]]:
    """SHA-256 of every file in ``<corpus>/saves``, sorted by path."""
    records = [
        {"path": path, "sha256": digest}
        for path, digest in directory_entries(corpus / "saves", "saves")
    ]
    records.sort(key=lambda entry: str(entry["path"]))
    return records


def read_seeded_save(corpus: Path) -> Dict[str, object]:
    files = sorted((corpus / "saves").iterdir())
    if not files:
        raise AssertionError("corpus has no save file")
    return json.loads(files[0].read_text(encoding="utf-8"))


# --------------------------------------------------------------- comparison --
def prune_paths(
    document: object, patterns: Iterable[Pattern[str]]
) -> Tuple[object, List[Tuple[str, object]]]:
    """Remove matching leaves from a copy; return the copy and removed values."""
    collected: List[Tuple[str, object]] = []
    pattern_list = list(patterns)

    def walk(node: object, path: str) -> object:
        if isinstance(node, dict):
            rebuilt: Dict[str, object] = {}
            for key in node:
                child = "%s/%s" % (path, key)
                if any(pattern.match(child) for pattern in pattern_list):
                    collected.append((child, node[key]))
                    continue
                rebuilt[key] = walk(node[key], child)
            return rebuilt
        if isinstance(node, list):
            result = []
            for index, item in enumerate(node):
                child = "%s/%d" % (path, index)
                if any(pattern.match(child) for pattern in pattern_list):
                    collected.append((child, item))
                    continue
                result.append(walk(item, child))
            return result
        return node

    return walk(document, ""), collected


def by_pid(entries: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """Neighbors as a pid-keyed mapping (legacy order is environment-bound)."""
    mapping: Dict[str, Dict[str, object]] = {}
    for entry in entries:
        pid = str(entry.get("pid"))
        if pid in mapping:
            raise AssertionError("duplicate pid in neighbors: %r" % (pid,))
        mapping[pid] = entry
    return mapping


def sort_neighbors(document: Dict[str, object]) -> Dict[str, object]:
    """Return a copy whose ``neighbors`` array is ordered by pid."""
    neighbors = document.get("neighbors")
    if not isinstance(neighbors, list):
        raise AssertionError("payload has no neighbors array")
    copy = dict(document)
    copy["neighbors"] = sorted(neighbors, key=lambda entry: str(entry.get("pid")))
    return copy


def diff_documents(expected: object, actual: object) -> List[str]:
    differences: List[Dict[str, str]] = []
    json_diff(expected, actual, "", differences)
    return ["%s: fixture=%s compat=%s" % (d["path"], d["a"], d["b"]) for d in differences]


# ------------------------------------------------------------ socket guard --
class _NoConnectSocket(socket.socket):
    """Socket that refuses to connect: offline tests must open no connection."""

    def connect(self, *args: object, **kwargs: object):  # type: ignore[override]
        raise AssertionError("offline test attempted a network connection: %r" % (args,))

    def connect_ex(self, *args: object, **kwargs: object):  # type: ignore[override]
        raise AssertionError("offline test attempted a network connection: %r" % (args,))


class offline:
    """Context manager proving no connection is opened inside its body."""

    def __enter__(self) -> "offline":
        self._original = socket.socket
        socket.socket = _NoConnectSocket  # type: ignore[misc, assignment]
        return self

    def __exit__(self, *exc_info: object) -> bool:
        socket.socket = self._original  # type: ignore[misc]
        return False


def port_is_free(host: str, port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()
