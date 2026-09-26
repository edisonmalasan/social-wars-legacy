#!/usr/bin/env python3
"""In-process adapter over the *unchanged* legacy boot modules (design D2).

The Compatibility API never re-implements legacy behavior: it imports the
legacy modules themselves and initializes their state in exactly the order
``server.py`` does::

    from get_game_config import get_game_config     # reads ./config, applies
                                                     # patches, mods, dedup
    from get_player_info import get_player_info, ...
    from sessions import load_saves, load_static_villages, load_quests, ...
    load_saves(); load_static_villages(); load_quests()

``bundle.py`` builds every legacy path from ``"."`` (the process working
directory), so the process must **chdir into a corpus directory** before the
first legacy import. That corpus contains ``config/``, ``mods/``, ``villages/``
and a ``saves/`` directory — never the working tree. Two consequences are part
of the contract and are asserted here:

* ``config/`` is read exactly once, at the first legacy import, so every later
  corpus must carry a byte-identical ``config/main.json`` (otherwise the
  already-loaded configuration would silently belong to another corpus).
* ``sessions.load_saves()`` creates ``./saves`` when it is missing, so a corpus
  without ``saves/`` is refused *before* legacy code runs.

Legacy modules are imported with ``sys.dont_write_bytecode`` forced on, so no
``__pycache__`` is written next to preserved sources. Nothing in this module
calls ``sessions.save_session``: the adapter has no persistence path at all.

Corpus construction (``build_corpus``) copies ``config/``, ``mods/`` and
``villages/`` and seeds ``saves/<pid>.save.json`` from
``tests/saves/fresh-player.json`` — byte-for-byte when the seed is not
mutated.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SEED_SAVE = REPO_ROOT / "tests" / "saves" / "fresh-player.json"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from hashing import directory_entries, sha256_file  # noqa: E402

# Directories the legacy boot modules read through bundle.py's "." paths.
CORPUS_COPY_DIRS = ("config", "mods", "villages")

_STATE: Dict[str, object] = {}


class LegacyBootError(Exception):
    """Initialization or resolution failure with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def corpus_layout_problems(corpus: Path) -> List[str]:
    """Paths a corpus must provide before legacy modules are imported."""
    problems: List[str] = []
    checks = (
        ("config/main.json", (corpus / "config" / "main.json").is_file()),
        ("villages/initial.json", (corpus / "villages" / "initial.json").is_file()),
        ("villages/quest", (corpus / "villages" / "quest").is_dir()),
        ("saves", (corpus / "saves").is_dir()),
    )
    for label, ok in checks:
        if not ok:
            problems.append(label)
    return problems


def build_corpus(
    destination: Path,
    seed: Path = SEED_SAVE,
    repo_root: Path = REPO_ROOT,
    mutate: Optional[Callable[[Dict[str, object]], None]] = None,
) -> Dict[str, object]:
    """Create a disposable legacy corpus and seed it with one save.

    ``mutate`` (test-only) receives the parsed seed document before it is
    written; when it is ``None`` the seed file is copied verbatim, so the
    seeded save keeps the seed's own SHA-256.
    """
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise LegacyBootError(
            "corpus_not_empty", "corpus destination is not empty: %s" % destination
        )
    if not seed.is_file():
        raise LegacyBootError("seed_missing", "seed save not found: %s" % seed)

    document = json.loads(seed.read_text(encoding="utf-8"))
    try:
        pid = str(document["playerInfo"]["pid"])
    except (KeyError, TypeError) as error:
        raise LegacyBootError("seed_invalid", "seed has no playerInfo.pid: %s" % error)
    if not pid:
        raise LegacyBootError("seed_invalid", "seed playerInfo.pid is empty")

    destination.mkdir(parents=True, exist_ok=True)
    for name in CORPUS_COPY_DIRS:
        source = repo_root / name
        if not source.is_dir():
            raise LegacyBootError("source_missing", "legacy directory missing: %s" % source)
        shutil.copytree(source, destination / name)

    saves_dir = destination / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    target = saves_dir / ("%s.save.json" % pid)
    if mutate is None:
        shutil.copy2(seed, target)
    else:
        mutate(document)
        with open(target, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, indent=4)
            stream.write("\n")

    return {
        "corpus": str(destination),
        "pid": pid,
        "seed": str(seed),
        "seed_sha256": sha256_file(seed),
        "save_sha256": sha256_file(target),
        "save_bytes_copied_verbatim": mutate is None,
        "copied_dirs": list(CORPUS_COPY_DIRS),
    }


def _file_sha256(path: Path) -> str:
    return sha256_file(path)


class LegacyBoot:
    """Initialized legacy state plus the read-only boot operations."""

    def __init__(self, corpus: Path, previous_cwd: str) -> None:
        self.corpus = corpus
        self.previous_cwd = previous_cwd
        self._sessions = _import("sessions")
        self._config = _import("get_game_config")
        self._player = _import("get_player_info")
        self._engine = _import("engine")
        self._version = _import("version")

    # --- legacy constants -------------------------------------------------
    @property
    def game_version(self) -> str:
        return str(self._version.version_name)

    @property
    def version_code(self) -> str:
        return str(self._version.version_code)

    # --- legacy calls -----------------------------------------------------
    def server_time(self) -> int:
        return int(self._engine.timestamp_now())

    def known_user_ids(self) -> List[str]:
        return list(self._sessions.all_saves_userid())

    def session_list(self) -> List[Dict[str, object]]:
        """Legacy ``all_saves_info()`` renamed into the v0 envelope shape."""
        return [
            {
                "id": entry["userid"],
                "name": entry["name"],
                "xp": entry["xp"],
                "level": entry["level"],
            }
            for entry in self._sessions.all_saves_info()
        ]

    def config(self) -> dict:
        """Legacy ``get_game_config()`` payload (live configuration object)."""
        return self._config.get_game_config()

    def player_info(self, user_id: str) -> dict:
        """Legacy ``get_player_info(USERID)`` including its in-memory effects."""
        if user_id not in self.known_user_ids():
            raise LegacyBootError("unknown_user_id", "no save for user id %r" % user_id)
        return self._player.get_player_info(user_id)

    # --- state / containment helpers -------------------------------------
    def reload_state(self) -> None:
        """Re-run the three ``server.py`` loaders (as login does per request)."""
        self._sessions.load_saves()
        self._sessions.load_static_villages()
        self._sessions.load_quests()

    def save_records(self) -> List[Dict[str, object]]:
        """SHA-256 of every file in this corpus's saves directory."""
        saves_dir = self.corpus / "saves"
        if not saves_dir.is_dir():
            raise LegacyBootError("corpus_layout", "corpus has no saves directory")
        return [
            {"path": path, "sha256": digest}
            for path, digest in directory_entries(saves_dir, "saves")
        ]


def _import(name: str):
    try:
        return __import__(name)
    except ImportError as error:
        raise LegacyBootError(
            "legacy_import",
            "legacy module %r could not be imported from the repository root: %s"
            % (name, error),
        )


def initialize(corpus: Path, repo_root: Path = REPO_ROOT) -> LegacyBoot:
    """Chdir into ``corpus`` and initialize legacy state like ``server.py``.

    Re-initializing is allowed (later corpora reload saves/villages/quests
    exactly as ``server.py`` re-runs ``load_saves()`` on every login) but the
    already-loaded configuration is only valid for a byte-identical
    ``config/main.json``.
    """
    corpus_path = Path(corpus).resolve()
    problems = corpus_layout_problems(corpus_path)
    if problems:
        raise LegacyBootError(
            "corpus_layout",
            "corpus %s is missing: %s" % (corpus_path, ", ".join(problems)),
        )

    repo_config = Path(repo_root) / "config" / "main.json"
    corpus_config = corpus_path / "config" / "main.json"
    if not repo_config.is_file():
        raise LegacyBootError("source_missing", "legacy config missing: %s" % repo_config)
    if sha256_file(repo_config) != sha256_file(corpus_config):
        raise LegacyBootError(
            "config_mismatch",
            "corpus config/main.json differs from the legacy config; the legacy "
            "configuration is read once at import",
        )

    previous_cwd = os.getcwd()
    os.chdir(str(corpus_path))

    repo_text = str(Path(repo_root).resolve())
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)

    # server.py import order: get_game_config, get_player_info, sessions.
    _import("get_game_config")
    _import("get_player_info")
    sessions = _import("sessions")

    boot = LegacyBoot(corpus_path, previous_cwd)
    # server.py init order: load_saves, load_static_villages, load_quests.
    sessions.load_saves()
    sessions.load_static_villages()
    sessions.load_quests()

    _STATE["boot"] = boot
    return boot


def initialized() -> bool:
    return "boot" in _STATE


def current() -> LegacyBoot:
    boot = _STATE.get("boot")
    if boot is None:
        raise LegacyBootError(
            "not_initialized",
            "legacy state is not initialized; call initialize(corpus) first",
        )
    assert isinstance(boot, LegacyBoot)
    return boot
