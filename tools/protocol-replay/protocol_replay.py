"""Contained four-command legacy replay; reports remain private evidence."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from typing import Any, Dict, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "e8c98a03c902eba70323538dc5d4eaba2f2927a1"
MAX_COMMANDS = 256
MAX_RESULT_BYTES = 32 * 1024 * 1024
CHILD_TIMEOUT = 30
SENTINEL = 1700000000
ROUTE = "/dynamic/menvswomen/srvsexwars/command.php"
ERROR_MESSAGE = "Legacy request failed; exception text omitted."
ORACLE_FILES = (
    "bundle.py", "command.py", "constants.py", "engine.py",
    "get_game_config.py", "sessions.py", "version.py", "config/main.json",
    "config/patch/patches.txt", "config/patch/atom_fusion_item.json",
    "config/patch/unit_patch.json", "config/patch/atom_fusion_items_data.json",
    "config/patch/atom_fusion_powerup.json", "config/patch/targets.json",
    "mods/mods.txt", "villages/initial.json",
)


class ReplayError(Exception):
    """Only fixed categories may cross the diagnostic boundary."""


def load_diff():
    spec = importlib.util.spec_from_file_location(
        "replay_state_diff", ROOT / "tools/state-diff/state_diff.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


try:
    diff = load_diff()
except Exception:
    # Even a missing comparison dependency must not print an import traceback.
    diff = None


def number(value: Any) -> bool:
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def execution_clear(value: Any) -> bool:
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is str and diff.REDACTED in item:
            return False
        if type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
    return True


def validate_record(record: Any) -> Dict[str, Any]:
    diff.inspect_inputs([(record, "record")])
    if type(record) is not dict or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ReplayError("record invalid")
    request = record.get("request")
    if type(request) is not dict or request.get("method") != "POST" or request.get("path") != ROUTE:
        raise ReplayError("record unsupported")
    for role in ("before", "after"):
        state = record.get(role)
        if state is None:
            raise ReplayError("evidence unavailable")
        if type(state) is not dict:
            raise ReplayError("record invalid")
    correlation = record.get("correlation")
    if type(correlation) is not dict:
        raise ReplayError("record invalid")
    player = correlation.get("player_id")
    if type(player) is not str or not player or not execution_clear(player):
        raise ReplayError("record invalid")
    for role in ("before", "after"):
        info = record[role].get("playerInfo")
        if type(info) is not dict or info.get("pid") != player:
            raise ReplayError("record invalid")
    envelope = record.get("commands")
    if type(envelope) is not dict or not all(key in envelope for key in (
            "first_number", "publishActions", "ts", "tries", "accessToken", "commands")):
        raise ReplayError("record invalid")
    commands = envelope["commands"]
    if type(commands) is not list:
        raise ReplayError("record invalid")
    if len(commands) > MAX_COMMANDS:
        raise ReplayError("replay limit exceeded")
    before = record["before"]
    maps = before.get("maps")
    if type(maps) is not list:
        raise ReplayError("record invalid")
    empty_level = False
    for comm in commands:
        if type(comm) is not list or len(comm) != 4 or not execution_clear(comm):
            raise ReplayError("record invalid")
        index, name, args, resources = comm
        if type(index) is not int or not 0 <= index < len(maps):
            raise ReplayError("record invalid")
        if type(name) is not str or name not in ("complete_tutorial", "level_up", "ping", "set_variables"):
            raise ReplayError("record unsupported")
        if type(args) is not list or type(resources) is not list or len(resources) != 8 or not all(number(v) for v in resources):
            raise ReplayError("record invalid")
        if name in ("ping", "set_variables"):
            valid = not args
        elif name == "level_up" and not args:
            empty_level = True
            valid = True
        else:
            valid = len(args) == 1 and type(args[0]) is int
        if not valid:
            raise ReplayError("record invalid")
        map_state = maps[index]
        if type(map_state) is not dict or not all(number(map_state.get(k)) for k in ("xp", "gold", "wood", "oil", "steel")):
            raise ReplayError("record invalid")
        private = before.get("privateState")
        if type(private) is not dict or not number(private.get("mana")) or not number(before["playerInfo"].get("cash")):
            raise ReplayError("record invalid")
    response = record.get("response")
    if type(response) is not dict or type(response.get("status")) is not int or "body" not in response or "error" not in record:
        raise ReplayError("record invalid")
    if record.get("outcome") == "success":
        if record["error"] is not None or response["status"] != 200 or response["body"] != {"result": "success"} or empty_level:
            raise ReplayError("record invalid")
    elif record.get("outcome") == "failure":
        error = record["error"]
        if not empty_level or type(error) is not dict or error.get("type") != "IndexError" or error.get("phase") != "command" or error.get("message") != ERROR_MESSAGE or response["status"] != 500 or response["body"] is not None:
            raise ReplayError("record unsupported")
    else:
        raise ReplayError("record invalid")
    return record


def minimal_environment() -> Dict[str, str]:
    # No PYTHON*, recorder settings, proxy settings, or user profile variables.
    return {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}


def regular_unlinked(path: Path, root: Path) -> None:
    try:
        for component in (path,) + tuple(path.parents):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise OSError()
            if component == root:
                break
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1:
            raise OSError()
    except (OSError, ValueError):
        raise ReplayError("oracle unavailable") from None


def git_bytes(root: Path, *args: str) -> bytes:
    git = shutil.which("git")
    if git is None:
        raise ReplayError("oracle unavailable")
    env = minimal_environment()
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
                "GIT_ALLOW_PROTOCOL": "", "GIT_OPTIONAL_LOCKS": "0"})
    try:
        result = subprocess.run([git, "--no-replace-objects", "-C", str(root),
                                 "-c", "core.fsmonitor=false", *args],
                                env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=CHILD_TIMEOUT, check=True)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise ReplayError("oracle unavailable") from None


def verify_oracle(root: Path = ROOT) -> Dict[str, bytes]:
    """Return checked bytes, so copy cannot reread a changed checkout file."""
    manifest_path = ROOT / "tools/protocol-replay/oracle-manifest.json"
    regular_unlinked(manifest_path, ROOT)
    try:
        manifest = diff.load_input(str(manifest_path), "oracle")
        if type(manifest) is not dict or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1 or manifest.get("baseline") != BASELINE or set(manifest["files"]) != set(ORACLE_FILES):
            raise ValueError()
        output = {}
        for name in ORACLE_FILES:
            entry = manifest["files"][name]
            blob_id = git_bytes(root, "rev-parse", BASELINE + ":" + name).decode("ascii").strip()
            if type(entry["size"]) is not int or blob_id != entry["blob"]:
                raise ValueError()
            blob = git_bytes(root, "cat-file", "blob", blob_id)
            object_digest = hashlib.sha1(b"blob " + str(len(blob)).encode("ascii") + b"\0" + blob).hexdigest()
            if len(blob) != entry["size"] or object_digest != blob_id:
                raise ValueError()
            path = root / name
            regular_unlinked(path, root)
            with path.open("rb") as source:
                checked = source.read(len(blob) * 2 + 1)
            # Every reviewed input is UTF-8 text. Only CRLF/LF is normalized.
            blob.decode("utf-8")
            checked.decode("utf-8")
            if checked.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
                raise ValueError()
            output[name] = checked
        return output
    except ReplayError:
        raise
    except (KeyError, TypeError, ValueError, OSError, diff.DiffError):
        raise ReplayError("oracle drift") from None


def supported_interpreter() -> bool:
    return (sys.platform == "win32" and platform.python_implementation() == "CPython"
            and sys.version_info[:3] == (3, 9, 13) and sys.maxsize > 2 ** 32
            and platform.machine().upper() in ("AMD64", "X86_64"))


def run_child(directory: Path) -> Dict[str, Any]:
    """Drain a bounded result pipe while enforcing an independent wall limit."""
    command = [sys.executable, "-I", "-B", str(directory / "replay_child.py")]
    try:
        child = subprocess.Popen(command, cwd=str(directory), env=minimal_environment(),
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL)
    except OSError:
        raise ReplayError("child unavailable") from None
    data = bytearray()
    exceeded = threading.Event()
    read_failed = threading.Event()

    def drain():
        try:
            while True:
                chunk = child.stdout.read(65536)
                if not chunk:
                    return
                if len(data) + len(chunk) > MAX_RESULT_BYTES:
                    exceeded.set()
                    child.kill()
                    return
                data.extend(chunk)
        except Exception:
            read_failed.set()
            try:
                child.kill()
            except OSError:
                pass

    reader = threading.Thread(target=drain, daemon=True)
    try:
        reader.start()
    except Exception:
        child.kill()
        child.wait()
        child.stdout.close()
        raise ReplayError("child failed") from None
    timed_out = False
    try:
        try:
            child.wait(timeout=CHILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            child.wait()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        reader.join()
        child.stdout.close()
    if timed_out:
        raise ReplayError("child timeout")
    if exceeded.is_set():
        raise ReplayError("replay limit exceeded")
    if read_failed.is_set() or child.returncode != 0:
        raise ReplayError("child failed")
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=diff.unique_object,
                            parse_float=diff.finite_number, parse_constant=diff.reject_constant)
        if type(result) is not dict:
            raise ValueError()
        if "failure" in result:
            categories = {"dependency failed", "legacy failed", "persistence failed", "child failed", "replay limit exceeded"}
            if result["failure"] not in categories:
                raise ValueError()
            raise ReplayError(result["failure"])
        return result
    except ReplayError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ReplayError("child failed") from None


def execute(record: Dict[str, Any], oracle: Dict[str, bytes], sentinel: int = SENTINEL) -> Dict[str, Any]:
    if not supported_interpreter():
        raise ReplayError("interpreter unsupported")
    # Ignore TMP/TEMP override destinations; use the Windows system temp root.
    base = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Temp"
    try:
        resolved = base.resolve()
        if resolved == ROOT or ROOT in resolved.parents or resolved in ROOT.parents:
            raise OSError()
        temporary = tempfile.TemporaryDirectory(prefix="socialwars-replay-", dir=str(resolved))
    except (OSError, ValueError):
        raise ReplayError("containment failed") from None
    try:
        directory = Path(temporary.name)
        for name, data in oracle.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (directory / "saves").mkdir()
        (directory / "replay_child.py").write_bytes((ROOT / "tools/protocol-replay/replay_child.py").read_bytes())
        seed = {"before": record["before"], "commands": record["commands"], "sentinel": sentinel}
        (directory / "input.json").write_bytes(json.dumps(seed, ensure_ascii=True, allow_nan=False).encode("ascii"))
        return run_child(directory)
    except ReplayError:
        raise
    except (OSError, ValueError, TypeError):
        raise ReplayError("containment failed") from None
    finally:
        try:
            temporary.cleanup()
        except Exception:
            raise ReplayError("cleanup failed") from None


def make_report(record: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        actual = result["state"]
        if type(actual) is not dict or result["outcome"] not in ("success", "IndexError") or type(result["response"]) is not dict or type(result["persisted"]) is not bool:
            raise ValueError()
        secrets = diff.inspect_inputs([(record, "record"), (result, "actual")])
        # Player correlation is known private data even though it is not an
        # authentication key in the shared sensitive-key policy.
        secrets.add(record["correlation"]["player_id"])
        actual_info = actual.get("playerInfo")
        if type(actual_info) is dict and type(actual_info.get("pid")) is str and actual_info["pid"]:
            secrets.add(actual_info["pid"])
        persisted = result["persisted"]
        if persisted:
            saved = result["saved_state"]
            if type(saved) is not dict or diff.structural_changes(actual, saved):
                raise ReplayError("persistence failed")
        elif result["saved_state"] is not None:
            raise ReplayError("persistence failed")
        state = diff.make_report(diff.structural_changes(record["after"], actual), secrets)
        expected_outcome = "success" if record["outcome"] == "success" else "IndexError"
        comparisons = {
            "outcome": "equal" if result["outcome"] == expected_outcome else "different",
            "response": "equal" if not diff.structural_changes({k: record["response"][k] for k in ("status", "body")}, result["response"]) else "different",
            "persistence": "equal" if persisted == (record["outcome"] == "success") else "different",
        }
        equal = state["comparison"] == "equal" and all(v == "equal" for v in comparisons.values())
        return {"schema_version": 1, "policy": "legacy-command-replay-v1",
                "replay": "match" if equal else "different", "state": state, **comparisons}
    except ReplayError:
        raise
    except (KeyError, TypeError, ValueError):
        raise ReplayError("child failed") from None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ReplayError("arguments invalid")


def parse_arguments(argv: Optional[Sequence[str]]):
    parser = Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    replay = commands.add_parser("replay", allow_abbrev=False)
    replay.add_argument("--record", required=True, action="append")
    args = parser.parse_args(argv)
    if len(args.record) != 1:
        raise ReplayError("arguments invalid")
    args.record = args.record[0]
    return args


def main(argv=None, stdout=None, stderr=None) -> int:
    output = sys.stdout.buffer if stdout is None else stdout
    diagnostic = sys.stderr if stderr is None else stderr
    try:
        if diff is None:
            raise ReplayError("dependency failed")
        args = parse_arguments(argv)
        record = validate_record(diff.load_input(args.record, "record"))
        oracle = verify_oracle()
        result = execute(record, oracle)
        report = make_report(record, result)
        data = diff.serialize_report(report)
        try:
            if output.write(data) != len(data):
                raise OSError()
            output.flush()
        except Exception:
            raise ReplayError("output failed") from None
        return 0 if report["replay"] == "match" else 1
    except MemoryError:
        category = "replay limit exceeded"
    except ReplayError as error:
        category = str(error)
    except diff.DiffError as error:
        category = ("comparison path ambiguity" if str(error) == "comparison path ambiguity"
                    else "report serialization failed" if str(error) == "report serialization failed"
                    else "replay limit exceeded" if "limit exceeded" in str(error)
                    else "record invalid")
    except Exception:
        category = "replay failed"
    try:
        if stderr is None:
            diagnostic.buffer.write((category + "\n").encode("ascii"))
        else:
            diagnostic.write(category + "\n")
        diagnostic.flush()
    except Exception:
        pass
    return 2


if __name__ == "__main__":
    status = main()
    if status == 2:
        sys.stdout = None
    sys.exit(status)
