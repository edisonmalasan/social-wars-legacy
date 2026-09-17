"""Private child adapter, copied to disposable storage; never a server."""
import json
import os
from pathlib import Path
import sys

MAX_RESULT_BYTES = 32 * 1024 * 1024
ALIAS = "replay-player"


class NullSink:
    def write(self, text):
        return len(text)

    def flush(self):
        pass


def run():
    root = Path.cwd().resolve()
    sys.path.insert(0, str(root))  # Explicit pinned copy; -I excludes ambient cwd.
    # This is a containment guard, not a hostile-code OS sandbox.
    def audit(event, args):
        if event.startswith(("socket.", "subprocess.", "os.system", "os.startfile", "webbrowser.")):
            raise RuntimeError()
        if event == "import" and args[0] in ("server", "legacy_command_recorder"):
            raise RuntimeError()
        if event == "open":
            filename, mode, flags = args
            if isinstance(filename, (str, bytes, os.PathLike)):
                target = Path(os.fsdecode(filename)).resolve()
                writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
                if writing and root not in target.parents:
                    raise RuntimeError()
                if not writing and (root / "saves" == target or root / "saves" in target.parents) and target.name != ALIAS + ".save.json":
                    raise RuntimeError()
    sys.addaudithook(audit)
    seed = json.loads((root / "input.json").read_text(encoding="ascii"))
    try:
        import command
        import sessions
    except Exception:
        return {"failure": "dependency failed"}
    sessions.SAVES_DIR = str(root / "saves")
    sessions.__dict__["__saves"] = {ALIAS: seed["before"]}
    command.timestamp_now = lambda: seed["sentinel"]
    outcome = "success"
    try:
        command.command(ALIAS, seed["commands"])
    except IndexError:
        outcome = "IndexError"
    except OSError:
        return {"failure": "persistence failed"}
    except Exception:
        return {"failure": "legacy failed"}
    state = sessions.session(ALIAS)
    save = root / "saves" / (ALIAS + ".save.json")
    entries = list((root / "saves").iterdir())
    if entries != ([save] if save.exists() else []):
        return {"failure": "persistence failed"}
    if save.exists() != (outcome == "success"):
        return {"failure": "persistence failed"}
    saved = None
    if save.exists():
        try:
            if save.stat().st_size > MAX_RESULT_BYTES:
                return {"failure": "replay limit exceeded"}
            saved = json.loads(save.read_text(encoding="ascii"))
        except Exception:
            return {"failure": "persistence failed"}
    return {"state": state, "outcome": outcome, "persisted": save.exists(),
            "saved_state": saved,
            "response": {"status": 200, "body": {"result": "success"}} if outcome == "success" else {"status": 500, "body": None}}


if __name__ == "__main__":
    output = sys.stdout.buffer
    sys.stdout = NullSink()
    sys.stderr = NullSink()
    try:
        result = run()
        data = json.dumps(result, ensure_ascii=True, allow_nan=False).encode("ascii")
        if len(data) > MAX_RESULT_BYTES:
            data = b'{"failure":"replay limit exceeded"}'
        output.write(data)
        output.flush()
    except BaseException:
        try:
            output.write(b'{"failure":"child failed"}')
            output.flush()
        except BaseException:
            pass
        sys.exit(2)
