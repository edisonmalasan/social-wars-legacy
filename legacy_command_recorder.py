"""Opt-in observation of the legacy command boundary (Python 3.9 stdlib)."""

import copy
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

DESTINATION_ENV = "SOCIALWARS_COMMAND_RECORD_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parent
REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset((
    "userkey", "accesstoken", "authorization", "proxyauthorization",
    "cookie", "cookies", "setcookie", "signature", "datahash",
    "password", "secret", "token", "sessionid", "apikey",
))
HEADER_ALLOWLIST = ("Content-Type", "Content-Length", "Accept")


def sensitive(key):
    return "".join(c for c in str(key).lower() if c.isalnum()) in SENSITIVE_KEYS


def secret_values(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if sensitive(key):
                collect_strings(item, found)
            else:
                found.update(secret_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.update(secret_values(item))
    return found


def collect_strings(value, found):
    if isinstance(value, str) and value:
        found.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            collect_strings(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            collect_strings(item, found)


def sanitize(value, secrets=()):
    if isinstance(value, dict):
        return {sanitize(str(key), secrets): REDACTED if sensitive(key)
                else sanitize(item, secrets) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                value = value.replace(secret, REDACTED)
    return value


def validate_destination(destination, root=REPOSITORY_ROOT):
    path = Path(destination)
    if not path.is_absolute():
        raise ValueError("destination must be absolute")
    path = path.resolve()
    root = Path(root).resolve()
    # Reject ancestors too: writing to the checkout's parent is needlessly broad.
    if path == root or root in path.parents or path in root.parents:
        raise ValueError("destination must be outside the repository")
    if path.exists() and not path.is_dir():
        raise ValueError("destination must be a directory")
    return path


def diagnostic(phase):
    """Never print exception text, paths, payloads, or credentials."""
    message = "Legacy command recorder: %s failed; check external destination and recorder configuration."
    try:
        logging.getLogger(__name__).warning(message, phase)
        return
    except Exception:
        pass
    try:
        sys.stderr.write((message % phase) + "\n")
    except Exception:
        pass


def persist(destination, record):
    destination = validate_destination(destination)
    serialized = json.dumps(record, sort_keys=True, ensure_ascii=True,
                            allow_nan=False, indent=2) + "\n"
    destination.mkdir(parents=True, exist_ok=True)
    destination = validate_destination(destination)
    # An exclusive claim also protects against deliberately repeated record IDs.
    while True:
        name = uuid.uuid4().hex
        target = destination / (name + ".json")
        claim = destination / (name + ".claim")
        try:
            descriptor = os.open(str(claim), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        os.close(descriptor)
        if target.exists():
            claim.unlink()
            continue
        break
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=str(destination), suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        if validate_destination(destination) != destination:
            raise ValueError("destination changed")
        os.replace(str(temporary), str(target))
        return target
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        claim.unlink()


class Observation:
    def __init__(self, request, state_reader):
        self.request = request
        self.state_reader = state_reader
        self.destination = None
        self.player = None
        self.parsed = None
        self.before = None
        self.after = None
        self.response = None
        self.phase = "parse"
        self.started = None
        self.duration = None
        self.secrets = set()

    def __enter__(self):
        configured = os.environ.get(DESTINATION_ENV)
        if configured:
            try:
                self.destination = validate_destination(configured)
                self.started = time.perf_counter()
                values = self.request.values.to_dict(flat=False)
                self.secrets.update(secret_values(values))
                self.secrets.update(secret_values(dict(self.request.headers)))
                collect_strings(dict(self.request.cookies), self.secrets)
                raw = self.request.values.get("data", "")
                if raw:
                    self.secrets.add(raw[:64])
            except Exception:
                diagnostic("configuration")
                self.destination = None
        return self

    def snapshot(self):
        try:
            return copy.deepcopy(self.state_reader(self.player))
        except Exception:
            diagnostic("snapshot")
            return None

    def executing(self, player, parsed):
        if self.destination is None:
            return
        try:
            self.player = player
            self.parsed = copy.deepcopy(parsed)
            self.before = self.snapshot()
            self.phase = "command"
            self.started = time.perf_counter()
        except Exception:
            diagnostic("snapshot")

    def completed(self, response):
        if self.destination is None:
            return
        try:
            self.duration = time.perf_counter() - self.started
            self.after = self.snapshot()
            self.response = copy.deepcopy(response)
            self.phase = "response"
        except Exception:
            diagnostic("snapshot")

    def __exit__(self, error_type, error, traceback):
        if self.destination is None:
            return False
        try:
            if error_type is not None:
                self.duration = time.perf_counter() - self.started
                if self.player is None:
                    self.player = self.request.values.get("USERID")
                self.after = self.snapshot()
                if self.phase == "parse":
                    self.before = copy.deepcopy(self.after)
            status = self.response[1] if self.response else (
                getattr(error, "code", None) or 500)
            record = {
                "schema_version": 1, "record_id": uuid.uuid4().hex,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "request": {"method": self.request.method, "path": self.request.path,
                            "headers": {key: self.request.headers[key] for key in HEADER_ALLOWLIST
                                        if key in self.request.headers}},
                "correlation": {"player_id": self.player},
                "commands": self.parsed, "before": self.before, "after": self.after,
                "response": {"status": status, "body": self.response[0] if self.response else None},
                "outcome": "failure" if error_type else "success",
                "duration_seconds": self.duration,
                "error": {"type": error_type.__name__[:80], "phase": self.phase,
                          "message": "Legacy request failed; exception text omitted."} if error_type else None,
            }
            self.secrets.update(secret_values(record))
            persist(self.destination, sanitize(record, self.secrets))
        except Exception:
            diagnostic("record construction or persistence")
        return False
