"""SHA-256 helpers shared by the Compatibility API v0 tooling.

Canonical digest rules used everywhere in ``apps/compat-api``:

* File digest: SHA-256 of the file bytes, lowercase hex.
* Directory digest: for every file under the directory, a line
  ``"<file sha256 hex>  <relative posix path>\\n"`` (two spaces) in ascending
  ordinal order of the relative path; the directory digest is the SHA-256 of
  the concatenated UTF-8 bytes of those lines.

This is the same canonical algorithm implemented by
``apps/client-godot/verify.ps1`` and ``apps/client-godot/scripts/package_paths.gd``
(``directory_digest``), so later verification scripts can re-check these
records with either implementation.

These helpers only read files. They never write.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

MISSING_DIGEST = "absent"


def sha256_bytes(data: bytes) -> str:
    """SHA-256 of a byte string as lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes as lowercase hex."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(entries: Iterable[Tuple[str, str]]) -> str:
    """SHA-256 over ordinal-sorted ``"<sha>  <path>\\n"`` lines.

    ``entries`` yields ``(relative posix path, sha256 hex)`` pairs. Paths must
    be unique; duplicates are a programming error and raise.
    """
    material: List[Tuple[str, str]] = []
    seen = set()
    for path, digest in entries:
        if path in seen:
            raise ValueError("duplicate path in canonical digest: %r" % (path,))
        seen.add(path)
        material.append((path, digest))
    material.sort(key=lambda item: item[0])
    digest = hashlib.sha256()
    for path, file_digest in material:
        digest.update(("%s  %s\n" % (file_digest, path)).encode("utf-8"))
    return digest.hexdigest()


def directory_entries(dir_path: Path, prefix: str = "") -> List[Tuple[str, str]]:
    """Sorted ``(posix relative path, sha256)`` entries for every file below.

    The relative path is relative to ``dir_path`` (or to ``prefix`` when a
    combined logical name is wanted), always with forward slashes.
    """
    root = Path(dir_path)
    if not root.is_dir():
        raise FileNotFoundError("directory not found: %s" % (dir_path,))
    entries: List[Tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if prefix:
            relative = prefix + "/" + relative
        entries.append((relative, sha256_file(path)))
    entries.sort(key=lambda item: item[0])
    return entries


def directory_digest(dir_path: Path, prefix: str = "") -> Dict[str, object]:
    """Canonical digest record for a directory tree that must exist."""
    entries = directory_entries(dir_path, prefix)
    return {
        "exists": True,
        "files": len(entries),
        "sha256": canonical_digest(entries),
    }


def missing_directory_record() -> Dict[str, object]:
    """Record for a directory that does not exist (state to be re-checked)."""
    return {"exists": False, "files": 0, "sha256": MISSING_DIGEST}


def record_digest(record: Dict[str, object]) -> str:
    """The digest contribution of a directory record (``absent`` when missing)."""
    if not record.get("exists", False):
        return MISSING_DIGEST
    return str(record["sha256"])


def combined_digest(named_records: Dict[str, Dict[str, object]]) -> str:
    """Canonical digest over ``"<record digest>  <group name>\\n"`` lines."""
    return canonical_digest(
        (name, record_digest(record)) for name, record in named_records.items()
    )
