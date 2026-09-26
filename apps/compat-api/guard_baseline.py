#!/usr/bin/env python3
"""SHA-256 guard set for the ``godot-compatibility-boot`` OpenSpec change.

Task 1.4 requires a pre-change baseline over exactly the paths the change must
leave byte-identical:

============================  ==============================================
group                         contents
============================  ==============================================
``legacy_sources``            every root-level ``*.py`` (the legacy server)
``config``                    ``config/`` (recursive)
``conversion_packages``       ``assets/converted/buildings/0001_house_1_m``
                              and ``assets/converted/units/10033_wild_elephant``
                              (the same two packages M4 ``verify.ps1`` guards)
``registry_manifests``        ``tools/asset-registry/conversions.json``,
                              ``inspection.json``, ``image_extraction.json``
                              (the same three M4 ``verify.ps1`` guards)
``m4_evidence``               ``apps/client-godot/evidence/first-render/
                              first-render.png`` and ``report.json``
``saves``                     ``tests/saves/`` plus the working-tree
                              ``saves/`` directory (recorded ``absent`` while
                              the repository has none)
============================  ==============================================

Digest rules are the shared canonical rules in ``hashing.py``: a file digest is
the SHA-256 of its bytes; a group digest is the SHA-256 of the ordinal-sorted
``"<sha256>  <repo-relative posix path>\\n"`` lines of every file in the group.

Commands (from the repository root, pinned CPython 3.9.x, ``-B``):

    python -B apps/compat-api/guard_baseline.py generate
    python -B apps/compat-api/guard_baseline.py verify

Exit codes:

- ``0`` — baseline written (``generate``) / every group byte-identical (``verify``)
- ``1`` — ``verify`` found a changed, added, or missing guarded path
- ``2`` — usage or environment error (wrong interpreter, path outside the repo,
          missing baseline, guarded path missing)

Scope limits: digests cover worktree bytes under the repository's
``core.autocrlf=true`` checkout, so the baseline is evidence for this checkout,
not a cross-checkout fingerprint. The tool only reads guarded paths and writes
the single baseline file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(HERE))
from hashing import (  # noqa: E402
    MISSING_DIGEST,
    canonical_digest,
    directory_entries,
    sha256_file,
)

SCHEMA = "godot-compatibility-boot/guard-baseline-v1"
DEFAULT_BASELINE = REPO_ROOT / "tests" / "fixtures" / "godot-compatibility-boot" / "guard-baseline.json"

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2

# group name -> (kind, repo-relative paths); "dirs" are recursive, "files" are
# single files, "optional_dirs" are recorded as absent when not present.
GROUPS: Dict[str, Tuple[str, List[str]]] = {
    "legacy_sources": ("files", None),  # resolved from the root glob below
    "config": ("dirs", ["config"]),
    "conversion_packages": (
        "dirs",
        [
            "assets/converted/buildings/0001_house_1_m",
            "assets/converted/units/10033_wild_elephant",
        ],
    ),
    "registry_manifests": (
        "files",
        [
            "tools/asset-registry/conversions.json",
            "tools/asset-registry/inspection.json",
            "tools/asset-registry/image_extraction.json",
        ],
    ),
    "m4_evidence": (
        "files",
        [
            "apps/client-godot/evidence/first-render/first-render.png",
            "apps/client-godot/evidence/first-render/report.json",
        ],
    ),
    "saves": ("optional_dirs", ["tests/saves", "saves"]),
}

GROUP_ORDER = (
    "legacy_sources",
    "config",
    "conversion_packages",
    "registry_manifests",
    "m4_evidence",
    "saves",
)


class GuardError(Exception):
    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def legacy_source_paths() -> List[str]:
    return sorted(path.name for path in REPO_ROOT.glob("*.py"))


def group_files(name: str) -> Dict[str, Optional[str]]:
    """Map repo-relative posix path -> sha256 (``None`` = absent path)."""
    kind, paths = GROUPS[name]
    if name == "legacy_sources":
        paths = legacy_source_paths()
        kind = "files"
    files: Dict[str, Optional[str]] = {}
    for rel in paths:
        absolute = REPO_ROOT / rel
        if kind == "files":
            if not absolute.is_file():
                raise GuardError(EXIT_USAGE, "guarded file missing: %s" % rel)
            files[rel] = sha256_file(absolute)
            continue
        if not absolute.is_dir():
            if kind == "optional_dirs":
                files[rel] = None
                continue
            raise GuardError(EXIT_USAGE, "guarded directory missing: %s" % rel)
        for path, digest in directory_entries(absolute, rel):
            files[path] = digest
    return files


def group_record(name: str) -> Dict[str, object]:
    files = group_files(name)
    present = {path: digest for path, digest in files.items() if digest is not None}
    absent = sorted(path for path, digest in files.items() if digest is None)
    return {
        "files": {path: present[path] for path in sorted(present)},
        "files_count": len(present),
        "absent_paths": absent,
        "sha256": canonical_digest(present.items()) if present else MISSING_DIGEST,
    }


def baseline_document() -> Dict[str, object]:
    from datetime import datetime, timezone

    groups = {name: group_record(name) for name in GROUP_ORDER}
    return {
        "schema": SCHEMA,
        "purpose": (
            "Pre-change byte baseline of every path the godot-compatibility-boot "
            "change must leave identical; verified again in the final state."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": {
            "file": "sha256 of the file bytes, lowercase hex",
            "group": (
                'SHA-256 of the ordinal-sorted "<sha256>  <repo-relative posix '
                'path>\\n" lines of every file in the group'
            ),
            "digest_source": "worktree bytes under core.autocrlf=true",
        },
        "groups": groups,
        "combined_sha256": canonical_digest(
            (name, str(groups[name]["sha256"])) for name in GROUP_ORDER
        ),
    }


def load_baseline(path: Path) -> Dict[str, object]:
    if not path.is_file():
        raise GuardError(EXIT_USAGE, "baseline not found: %s (run generate first)" % path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GuardError(EXIT_USAGE, "baseline unreadable: %s" % error)
    if document.get("schema") != SCHEMA:
        raise GuardError(
            EXIT_USAGE,
            "baseline schema mismatch: %r (expected %r)"
            % (document.get("schema"), SCHEMA),
        )
    if not isinstance(document.get("groups"), dict):
        raise GuardError(EXIT_USAGE, "baseline has no groups object")
    return document


def compare(document: Dict[str, object]) -> List[str]:
    """Return a value-free list of human-readable mismatch findings.

    The file map of every group is diffed unconditionally (not only when the
    group digest moved), and each recorded group digest is re-derived from the
    baseline's own file map, so a hand-edited baseline cannot hide a change.
    """
    problems: List[str] = []
    recorded: Dict[str, object] = document["groups"]  # type: ignore[index]
    for name in GROUP_ORDER:
        if name not in recorded:
            problems.append("%s: group missing from baseline" % name)
            continue
        expected = recorded[name]
        if not isinstance(expected, dict):
            problems.append("%s: baseline group is not an object" % name)
            continue
        actual = group_record(name)
        before: Dict[str, object] = expected.get("files") or {}
        after: Dict[str, object] = actual["files"]
        if not isinstance(before, dict):
            problems.append("%s: baseline file map is not an object" % name)
            continue
        for path in sorted(set(before) | set(after), key=str):
            if path not in before:
                problems.append("%s: added %s" % (name, path))
            elif path not in after:
                problems.append("%s: removed %s" % (name, path))
            elif before[path] != after[path]:
                problems.append("%s: changed %s" % (name, path))
        before_absent = set(expected.get("absent_paths") or [])
        after_absent = set(actual["absent_paths"] or [])
        for path in sorted(before_absent ^ after_absent):
            problems.append("%s: presence changed %s" % (name, path))
        if expected.get("sha256") != actual["sha256"]:
            problems.append("%s: group digest changed" % name)
        recomputed = canonical_digest(
            (path, str(digest)) for path, digest in before.items()
        )
        if recomputed != expected.get("sha256"):
            problems.append(
                "%s: baseline group digest is inconsistent with its own file map"
                % name
            )
    if "combined_sha256" in document:
        recomputed = canonical_digest(
            (name, str(group_record(name)["sha256"])) for name in GROUP_ORDER
        )
        if recomputed != document["combined_sha256"]:
            problems.append("combined: digest changed")
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command",
        choices=("generate", "verify"),
        help="write the baseline, or re-check every guarded path against it",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="baseline file path (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if sys.version_info[:2] != (3, 9):
        print(
            "guard-baseline: refused: CPython 3.9.x required; got %s"
            % sys.version.split()[0],
            file=sys.stderr,
        )
        return EXIT_USAGE

    baseline_path = Path(args.baseline).resolve()
    if REPO_ROOT not in baseline_path.parents:
        print(
            "guard-baseline: --baseline must be strictly inside the repository: %s"
            % baseline_path,
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        if args.command == "generate":
            document = baseline_document()
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            with open(baseline_path, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(document, stream, indent=2, ensure_ascii=True, sort_keys=True)
                stream.write("\n")
            print("guard-baseline: wrote %s" % baseline_path)
            for name in GROUP_ORDER:
                record = document["groups"][name]  # type: ignore[index]
                print(
                    "guard-baseline:   %-20s %3d file(s)  %s"
                    % (name, record["files_count"], record["sha256"])
                )
            print(
                "guard-baseline:   %-20s %s"
                % ("combined", document["combined_sha256"])
            )
            return EXIT_OK

        document = load_baseline(baseline_path)
        problems = compare(document)
    except GuardError as error:
        print("guard-baseline: FAILED: %s" % error, file=sys.stderr)
        return error.exit_code

    if problems:
        print("guard-baseline: FAILED: guarded bytes differ", file=sys.stderr)
        for problem in problems:
            print("guard-baseline:   %s" % problem, file=sys.stderr)
        return EXIT_MISMATCH
    print(
        "guard-baseline: OK - %d group(s), combined %s"
        % (len(GROUP_ORDER), document.get("combined_sha256"))
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
