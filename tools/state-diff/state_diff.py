"""Read-only, value-free structural evidence comparison (Python 3.9 stdlib)."""

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 128
MAX_NODES = 1_000_000
MAX_CHANGES = 100_000
REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset((
    "userkey", "accesstoken", "authorization", "proxyauthorization",
    "cookie", "cookies", "setcookie", "signature", "datahash",
    "password", "secret", "token", "sessionid", "apikey",
))
MISSING = object()


class DiffError(Exception):
    """Carries only a fixed diagnostic, never an underlying exception."""


@dataclass(frozen=True)
class Change:
    operation: str
    components: Tuple[str, ...]
    before_type: str
    after_type: str


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise DiffError("arguments invalid")


def sensitive(key: str) -> bool:
    return "".join(c for c in key.lower() if c.isalnum()) in SENSITIVE_KEYS


def json_type(value: Any) -> str:
    if value is MISSING:
        return "missing"
    labels = {type(None): "null", bool: "boolean", int: "integer",
              float: "number", str: "string", dict: "object", list: "array"}
    try:
        return labels[type(value)]
    except KeyError:
        raise DiffError("comparison input invalid") from None


def unique_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def finite_number(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError()
    return value


def reject_constant(text: str) -> None:
    raise ValueError()


def load_input(filename: str, role: str) -> Any:
    try:
        path = Path(filename)
        # Check before open as well as after: a FIFO/device must not be read.
        if not stat.S_ISREG(path.stat().st_mode):
            raise OSError()
        with path.open("rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise OSError()
            if info.st_size > MAX_INPUT_BYTES:
                raise DiffError(role + " input limit exceeded")
            data = source.read(MAX_INPUT_BYTES + 1)
    except DiffError:
        raise
    except (OSError, ValueError):
        raise DiffError(role + " input read failed") from None
    if len(data) > MAX_INPUT_BYTES:
        raise DiffError(role + " input limit exceeded")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_float=finite_number, parse_constant=reject_constant)
    except RecursionError:
        raise DiffError("comparison limit exceeded") from None
    except (ValueError, UnicodeError):
        raise DiffError(role + " input invalid") from None


def inspect_inputs(roots: Sequence[Tuple[Any, str]]) -> Set[str]:
    """Validate every node, including unchanged subtrees/record metadata.

    Count nodes across all supplied roots; keys are checked as strings but are
    not value nodes. Sensitive subtrees collect nonempty string values, as the
    recorder does, without treating their dictionary keys as secret values.
    """
    secrets = set()
    nodes = 0
    for root, role in roots:
        stack = [(root, 0, False)]
        while stack:
            value, parent_depth, protected = stack.pop()
            nodes += 1
            if nodes > MAX_NODES:
                raise DiffError("comparison limit exceeded")
            kind = json_type(value)
            if kind == "number" and not math.isfinite(value):
                raise DiffError(role + " input invalid")
            if kind == "string":
                try:
                    value.encode("utf-8")
                except UnicodeError:
                    raise DiffError(role + " input invalid") from None
                if protected and value:
                    secrets.add(value)
            if kind in ("object", "array"):
                depth = parent_depth + 1
                if depth > MAX_DEPTH:
                    raise DiffError("comparison limit exceeded")
                if kind == "object":
                    for key, child in value.items():
                        if type(key) is not str:
                            raise DiffError(role + " input invalid")
                        try:
                            key.encode("utf-8")
                        except UnicodeError:
                            raise DiffError(role + " input invalid") from None
                        stack.append((child, depth, protected or sensitive(key)))
                else:
                    stack.extend((child, depth, protected) for child in value)
    return secrets


def structural_changes(before: Dict[str, Any], after: Dict[str, Any]) -> List[Change]:
    changes = []
    stack = [(before, after, ())]
    while stack:
        old, new, path = stack.pop()
        old_type, new_type = json_type(old), json_type(new)
        operation = None
        if old is MISSING:
            operation = "added"
        elif new is MISSING:
            operation = "removed"
        elif old_type != new_type:
            operation = "changed"
        elif old_type == "object":
            for key in reversed(sorted(old.keys() | new.keys())):
                stack.append((old.get(key, MISSING), new.get(key, MISSING), path + (key,)))
        elif old_type == "array":
            for index in reversed(range(max(len(old), len(new)))):
                stack.append((old[index] if index < len(old) else MISSING,
                              new[index] if index < len(new) else MISSING,
                              path + (str(index),)))
        elif old != new:
            operation = "changed"
        if operation:
            if len(changes) >= MAX_CHANGES:
                raise DiffError("comparison limit exceeded")
            changes.append(Change(operation, path, old_type, new_type))
    return changes


def protect_component(component: str, secrets: Sequence[str]) -> str:
    # Keep replacements separate from original text so one secret cannot
    # rewrite a placeholder inserted for another secret.
    pieces = [(component, False)]
    for secret in secrets:
        next_pieces = []
        for text, replaced in pieces:
            if replaced:
                next_pieces.append((text, True))
                continue
            parts = text.split(secret)
            for index, part in enumerate(parts):
                if index:
                    next_pieces.append((REDACTED, True))
                next_pieces.append((part, False))
        pieces = next_pieces
    return "".join(text for text, _ in pieces)


def make_report(changes: Sequence[Change], secrets: Set[str]) -> Dict[str, Any]:
    ordered_secrets = sorted(secrets, key=lambda value: (-len(value), value))
    seen = set()
    entries = []
    for change in changes:
        components = [protect_component(part, ordered_secrets) for part in change.components]
        path = "".join("/" + part.replace("~", "~0").replace("/", "~1") for part in components)
        if path in seen:
            raise DiffError("comparison path ambiguity")
        seen.add(path)
        entries.append({"operation": change.operation, "path": path,
                        "before_type": change.before_type, "after_type": change.after_type})
    return {"schema_version": 1, "policy": "structural-json-types-v1",
            "comparison": "different" if entries else "equal",
            "change_count": len(entries), "changes": entries}


def compare_states(before: Dict[str, Any], after: Dict[str, Any],
                   record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if type(before) is not dict or type(after) is not dict:
        raise DiffError("comparison input invalid")
    roots = [(record, "record")] if record is not None else [(before, "before"), (after, "after")]
    secrets = inspect_inputs(roots)
    return make_report(structural_changes(before, after), secrets)


def parse_arguments(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    compare = commands.add_parser("compare", allow_abbrev=False)
    compare.add_argument("--before")
    compare.add_argument("--after")
    compare.add_argument("--record")
    args = parser.parse_args(argv)
    if args.record is not None:
        if args.before is not None or args.after is not None:
            raise DiffError("arguments invalid")
    elif args.before is None or args.after is None:
        raise DiffError("arguments invalid")
    return args


def report_from_arguments(args: argparse.Namespace) -> Dict[str, Any]:
    if args.record is not None:
        record = load_input(args.record, "record")
        if type(record) is not dict or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
            raise DiffError("record schema invalid")
        if record.get("before") is None or record.get("after") is None:
            raise DiffError("record evidence unavailable")
        if type(record["before"]) is not dict or type(record["after"]) is not dict:
            raise DiffError("record boundary invalid")
        return compare_states(record["before"], record["after"], record)
    before = load_input(args.before, "before")
    after = load_input(args.after, "after")
    for value, role in ((before, "before"), (after, "after")):
        if type(value) is not dict:
            raise DiffError(role + " boundary invalid")
    return compare_states(before, after)


def serialize_report(report: Dict[str, Any]) -> bytes:
    try:
        return (json.dumps(report, ensure_ascii=True, sort_keys=True,
                           allow_nan=False, indent=2) + "\n").encode("utf-8")
    except MemoryError:
        raise
    except Exception:
        raise DiffError("report serialization failed") from None


def main(argv: Optional[Sequence[str]] = None, stdout: Any = None, stderr: Any = None) -> int:
    output = sys.stdout.buffer if stdout is None else stdout
    diagnostic = sys.stderr if stderr is None else stderr
    try:
        args = parse_arguments(argv)
        report = report_from_arguments(args)
        data = serialize_report(report)
        try:
            written = output.write(data)
            if written != len(data):
                raise OSError()
            output.flush()
        except MemoryError:
            raise
        except Exception:
            raise DiffError("output failed") from None
        return 0 if report["comparison"] == "equal" else 1
    except MemoryError:
        message = "comparison limit exceeded"
    except DiffError as error:
        message = str(error)
    try:
        if stderr is None:
            diagnostic.buffer.write((message + "\n").encode("ascii"))
        else:
            diagnostic.write(message + "\n")
        diagnostic.flush()
    except (OSError, ValueError, TypeError):
        # Both sinks can fail; the non-success exit remains authoritative.
        return 2
    return 2


if __name__ == "__main__":
    status = main()
    if status == 2:
        # Suppress a second unsafe interpreter-shutdown broken-pipe diagnostic.
        sys.stdout = None
    sys.exit(status)
