#!/usr/bin/env python3
"""Capture the executed-legacy collect fixture: one real ``collect`` command.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, and construction captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, upgrade, and construction fixtures.
2. Detects a port conflict on ``127.0.0.1:5055`` before starting anything.
3. Builds a disposable copy under the system temp root (root ``*.py``,
   ``config/``, ``mods/``, ``villages/``, ``templates/`` and ``saves/``
   seeded from ``tests/saves/fresh-player.json``).
4. Starts the REAL legacy server (``python -B server.py`` in the
   disposable copy) and waits for loopback readiness.
5. Executes two legacy requests, recording full canonical before/after
   save JSON plus the response for each step:

   * ``POST /``                       — login form (session cookie, as a
     logged-in Flash client would send; 302, save unchanged)
   * ``POST .../command.php``         — the crafted ``<64-hex>;<json>``
     ``data`` envelope carrying exactly **one** derived command —
     ``[0,"collect",[2],[0,3,0,60,0,0,0,0]]`` — as produced by
     :mod:`collect_envelope`

   The fixture collection is the placed **Tree** (item id 905) at map slot
   ``2``, anchored at ``(53,39)`` in the fresh-player corpus: committed
   ``collect "20"``, ``collect_type "w"``, ``collect_xp "1"``,
   ``max_collects "0"``, ``attr {}`` and ``timestamp 0``.  It is the corpus's
   cheapest honest choice because **every one of the 40 rows carries
   ``item[3] == 0``**, so the elapsed time is unbounded and the **top** ladder
   rung is deterministic in every run: ``20 x 3 = 60`` wood and
   ``1 x 3 = 3`` xp, the derived vector ``[0, 3, 0, 60, 0, 0, 0, 0]``.  The
   corpus's only income-bearing rows are the decorations (the Tree at slot 2
   and the Trees / Small forest at slots 21-28) because the real factories are
   not placed — recorded as a claim limit, not hidden.  Slot ``2`` is the same
   row the store fixture puts into storage in **its own independent
   transaction** (each capture seeds a fresh corpus), so both fixtures stay
   independently readable.
6. Verifies the transaction structurally before publishing: the login step
   left the save byte-identical, the collection step mutated it, the row at
   key ``"2"`` **still exists** afterwards holding item ``905`` at the
   **same cell** ``(53,39)`` with the same orientation, stored-unit payload,
   attribute bag, and player team, its ``timestamp`` is a fresh wall-clock
   collection instant **strictly greater** than the before-state's, the
   placement count stays ``40``, every other row is byte-identical, and the
   whole ``privateState`` (``boughtUnits []``, ``deadHeroes {}``),
   ``maps[0].store`` (``{}``), ``playerInfo``, and every other map field are
   unchanged while **every stored resource moved by exactly the derived
   delta**: ``xp 4 -> 7`` and ``wood 2000 -> 2060``, with gold, oil, steel,
   cash, and mana untouched.  The recorded request itself is pinned: exactly
   one command, the fixture index, and the content-derived payout.
7. Stops the server, re-checks the working-tree containment snapshot and the
   committed boot/placement/purchase/move/sell/store/upgrade/construction
   fixture digests, discards the disposable copy, and writes the fixtures
   under ``--out`` (default: ``tests/fixtures/godot-building-collect/``).

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

Containment (same contract as the boot, placement, purchase, move, sell, store,
upgrade, and construction captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The committed boot,
  placement, purchase, move, sell, store, upgrade, and construction fixtures
  are digest-pinned for the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the boot, placement, purchase, move, sell, store,
upgrade, and construction capture harnesses):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed, returned an unexpected status, or the
      executed transaction did not match the derived envelope
6     Containment violation (working-tree bytes changed, a committed fixture
      directory changed, or the disposable corpus saves changed during
      server startup / login)
7     Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_collect_fixture.py

where ``python`` denotes the pinned CPython 3.9.13 executable
(``C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe``).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_envelope  # noqa: E402
from capture_legacy_fixtures import (  # noqa: E402
    DYNAMIC_ROOT,
    EXIT_CONTAINMENT,
    EXIT_ENVIRONMENT,
    EXIT_PORT_BUSY,
    EXIT_REQUEST,
    EXIT_SERVER,
    EXIT_WRITE,
    FRESH_PLAYER_SAVE,
    GAME_VERSION,
    LANGUAGE,
    LEGACY_HOST,
    LEGACY_PORT,
    REPO_ROOT,
    USER_KEY,
    CaptureError,
    build_disposable,
    clear_previous_fixtures,
    containment_snapshot,
    dir_group_record,
    extract_session_cookie,
    http_request,
    iso_now,
    port_is_free,
    read_tail,
    save_group_record,
    snapshot_combined,
    start_server,
    stop_server,
    wait_ready,
    write_bytes,
    write_json,
)
from hashing import sha256_bytes  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-collect"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a
# corpus and initialize live legacy state).  The item's income fields and the
# collection ladder are read from it here and pinned against the committed
# constants, so a config drift fails the run instead of publishing a different
# fixture.
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The fixture collection intent (verified against the committed config and fresh
# save: slot "2" holds [905, 53, 39, 0, 0, [], {}, 1]; the config's income
# fields for item 905 are collect "20", collect_type "w", collect_xp "1",
# max_collects "0"; the ladder is [5, 60, 240, 480] x [0.25, 1, 2, 3]).
FIXTURE_ITEM_INDEX = 2
FIXTURE_ITEM_ID = 905  # Tree: the placed income-bearing building this fixture collects
FIXTURE_ITEM_NAME = "Tree"
FIXTURE_X = 53
FIXTURE_Y = 39
FIXTURE_COLLECT_AMOUNT = 20
FIXTURE_COLLECT_TYPE = "w"
FIXTURE_COLLECT_XP = 1
FIXTURE_MAX_COLLECTS = 0
# The committed ladder (config/main.json globals).  Every row of the fresh
# corpus carries item[3] == 0, so the elapsed time is unbounded and the TOP
# rung is the deterministic one for every run.
FIXTURE_LADDER_MINUTES = [5, 60, 240, 480]
FIXTURE_LADDER_MULTIPLIERS = [0.25, 1, 2, 3]
FIXTURE_EXPECTED_TIER = 3  # the top committed rung, index 3
# The derived payout: xp 1 x 3 in slot 1, wood 20 x 3 in slot 3, and the
# unread slot 0 and the never-produced mana slot 7 left zero (design D6).
FIXTURE_EXPECTED_VECTOR = [0, 3, 0, 60, 0, 0, 0, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 40  # no key is added or removed
# The exact resource movement the derived payout must produce, under legacy's
# ``max(current + delta, 0)`` per slot.  The corpus's other five resources sit
# far above zero, so **this fixture never exercises that clamp** — recorded as
# a claim limit rather than hidden.
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {"xp": 3, "wood": 60}
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
TARGET_RULE = (
    "the placed Tree decoration (item id 905) at map slot 2 anchored at (53,39) "
    "in the committed fresh save, whose committed income is collect 20, "
    "collect_type 'w', collect_xp 1, max_collects 0 — the fresh corpus has no "
    "row with a recent collection instant (every row's item[3] is 0), so the "
    "elapsed time is unbounded and the top committed ladder rung applies "
    "deterministically; the corpus's only income-bearing rows are decorations "
    "because the real factories are not placed, and slot 2 is the same row the "
    "store fixture puts into storage in its own independent transaction, so "
    "both fixtures stay independently readable"
)

# Committed fixtures that must be byte-identical across this run.
PROTECTED_FIXTURES = (
    ("tests/fixtures/godot-compatibility-boot", "godot-compatibility-boot"),
    ("tests/fixtures/godot-building-placement", "godot-building-placement"),
    ("tests/fixtures/godot-item-purchase", "godot-item-purchase"),
    ("tests/fixtures/godot-building-move", "godot-building-move"),
    ("tests/fixtures/godot-building-sell", "godot-building-sell"),
    ("tests/fixtures/godot-building-store", "godot-building-store"),
    ("tests/fixtures/godot-building-upgrade", "godot-building-upgrade"),
    ("tests/fixtures/godot-building-construction", "godot-building-construction"),
)

# The two executed-legacy probes that shaped this line.  They were run against
# the real legacy server inside a disposable copy by the recorded investigation
# (``docs/legacy-collect-income.md`` and this change's design) and are recorded
# here so the fixture states its own evidence base rather than only its result.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does the collect branch actually write, and is the "
            "client-sent resource vector applied verbatim?"
        ),
        "command": "collect(2)",
        "vector": [0, 7, -5, 60, 0, 0, 0, 0],
        "row_before": [905, 53, 39, 0, 0, [], {}, 1],
        "row_after": "[905, 53, 39, <wall-clock>, 0, [], {}, 1]",
        "resources": "xp 4 -> 11; wood 2000 -> 2060; gold 2000 -> 1995",
        "response": '{"result":"success"}',
        "established": (
            "the branch stamps ONLY the row's timestamp (command.py:136-147) and "
            "the client-sent vector is applied verbatim, per resource, including "
            "a negative delta (engine.apply_resources runs before the branch, "
            "command.py:40 / engine.py:251-271). Nothing else in the save moves."
        ),
        "clamp_not_exercised": (
            "a -5 gold delta on a 2000 balance stays positive, so the "
            "max(..., 0) clamp did not bite; the clamp only bites when a delta "
            "would drive a balance below zero, which the derived payouts of this "
            "change never do"
        ),
    },
    {
        "probe": 2,
        "question": (
            "what happens when a collection runs on a row whose construction "
            "was just started — is the shared item[3] field merely ambiguous or "
            "actually destructive?"
        ),
        "command": "activate(11, 3600) then collect(11)",
        "vector": [0, 1, 0, 20, 0, 0, 0, 0],
        "row_before": [22, 58, 48, 0, 0, [], {}, 1],
        "row_after": '[22, 58, 48, <collect instant>, 0, [], {"cp": 3600}, 1]',
        "resources": "xp 4 -> 5; wood 2000 -> 2020; every other row, the private "
        "state, and playerInfo byte-identical",
        "response": '{"result":"success"}',
        "established": (
            "item[3] moved to the COLLECT instant while attr['cp'] = 3600 "
            "SURVIVED, so the row still advertises a full hour of construction "
            "but its start instant is now the collection time: the delivered "
            "construction line's remaining-time derivation "
            "cp - (now - item[3]) measures the countdown from the wrong epoch "
            "and silently restarts an active build's timer — and legacy reports "
            "success"
        ),
        "consequence": (
            "this is the evidence for the design D5 construction_in_progress "
            "refusal: the client offers no Collect action for such a row AND "
            "the endpoint fails closed before the dispatcher runs, so a client "
            "that ignores the client-side rule still cannot corrupt the "
            "construction timers the delivered construction line depends on"
        ),
        "not_observed_from_client": (
            "which stamp a real client sends first, and whether it avoids this "
            "state at all — never observed, because Flash is never executed in "
            "this repository"
        ),
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_collect")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5}


# --------------------------------------------------------- committed config --
def config_item_attribute(item_id: int, attribute: str) -> Any:
    """A raw committed item attribute, or ``None`` when the item is unknown.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (see :data:`CONFIG_MAIN`).  The income fields are then resolved with
    exactly the rules :meth:`compat_legacy.LegacyBoot.item_collect_amount` /
    ``item_collect_type`` / ``item_collect_xp`` / ``item_max_collects`` use
    server-side: a missing attribute, a non-integer value, and a negative value
    all mean **no resolvable value** (and are never coerced), while a resolved
    ``0`` stays a real value because ``collect "0"`` is what 727 of the 778
    stored items record.
    """
    try:
        document = json.loads(CONFIG_MAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    known: Dict[int, Dict[str, Any]] = {}
    for entry in document.get("items") or []:
        try:
            known[int(entry["id"])] = entry
        except (KeyError, TypeError, ValueError):
            continue
    item = known.get(item_id)
    if item is None:
        return None
    return item.get(attribute)


def config_non_negative_int(item_id: int, attribute: str) -> Optional[int]:
    """A committed item attribute as a non-negative ``int``, or ``None``."""
    raw = config_item_attribute(item_id, attribute)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def config_collect_amount(item_id: int) -> Optional[int]:
    """The item's committed collection amount (possibly ``0``), or ``None``."""
    return config_non_negative_int(item_id, "collect")


def config_collect_xp(item_id: int) -> Optional[int]:
    """The item's committed collection experience (possibly ``0``), or ``None``."""
    return config_non_negative_int(item_id, "collect_xp")


def config_max_collects(item_id: int) -> Optional[int]:
    """The item's committed collection cap (possibly ``0``), or ``None``."""
    return config_non_negative_int(item_id, "max_collects")


def config_collect_type(item_id: int) -> Optional[str]:
    """The item's committed collection resource type verbatim, or ``None``."""
    raw = config_item_attribute(item_id, "collect_type")
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    return text or None


def config_ladder() -> Tuple[List[int], List[float]]:
    """The committed collection ladder, or a refusal.

    Read from ``config/main.json``'s ``globals``: ``COLLECT_MINUTES`` and the
    parallel ``COLLECT_MULTIPLIER``.  The pair is validated with the *same*
    :func:`collect_envelope.collect_ladder` rule the endpoint uses, so a
    malformed ladder fails this run rather than producing a different payout
    here and there.
    """
    try:
        document = json.loads(CONFIG_MAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    globals_object = document.get("globals")
    if not isinstance(globals_object, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the committed config has no globals")
    pair = (globals_object.get("COLLECT_MINUTES"), globals_object.get("COLLECT_MULTIPLIER"))
    try:
        return collect_envelope.collect_ladder(pair)
    except collect_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed collection ladder does not resolve: [%s] %s"
            % (error.code, error),
        )


# ------------------------------------------------------------ sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    """Redact secret-valued form fields before recording."""
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact the disposable server's session cookie from recorded headers.

    The live request always sends the real cookie (the login step must behave
    like a logged-in client); only the *record* is redacted — it is an
    ephemeral token value of a dead disposable server, it can never be
    replayed (collect parity works from the intent, not over HTTP), and
    redacting it keeps reruns byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact
    sent bytes; this keeps the record secret-free even if that placeholder
    ever changes.
    """
    envelope = collect_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return collect_envelope.data_field(envelope)


# ----------------------------------------------------------------- records --
def canonical_save(path: Path) -> Dict[str, Any]:
    """Full parsed save document from a corpus save file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "could not read corpus save %s: %s" % (path, error))
    if not isinstance(document, dict):
        raise CaptureError(EXIT_REQUEST, "corpus save is not a JSON object: %s" % path)
    return document


def save_bytes_sha(document: Dict[str, Any]) -> str:
    """SHA-256 of the canonical serialization used for fixture records."""
    return sha256_bytes(
        json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True).encode("utf-8")
    )


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven stored resource values the legacy code maintains."""
    first_map = document["maps"][0]
    return {
        "xp": first_map["xp"],
        "gold": first_map["gold"],
        "wood": first_map["wood"],
        "oil": first_map["oil"],
        "steel": first_map["steel"],
        "cash": document["playerInfo"]["cash"],
        "mana": document["privateState"]["mana"],
    }


def request_record(
    result: Dict[str, Any],
    form: Dict[str, str],
    note: str,
) -> Dict[str, Any]:
    """The recorded request: exact sent bytes except redacted secrets."""
    recorded_form = sanitize_form(dict(form))
    if "data" in recorded_form:
        recorded_form["data"] = sanitize_data_field(form["data"])
    return {
        "captured_at_utc": iso_now(),
        "method": result["method"],
        "target": result["target"],
        "path": result["path"],
        "query": result["query"],
        "form": recorded_form,
        "headers_sent": sanitize_headers(result["headers_sent"]),
        "scheme": "http",
        "host": LEGACY_HOST,
        "port": LEGACY_PORT,
        "note": note,
    }


def response_record(result: Dict[str, Any], body: bytes) -> Dict[str, Any]:
    return {
        "status": result["status"],
        "reason": result["reason"],
        "headers": sanitize_headers(result["response_headers"]),
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "captured_at_utc": iso_now(),
    }


def write_step(
    staging: Path,
    name: str,
    result: Dict[str, Any],
    body: bytes,
    before: Dict[str, Any],
    after: Dict[str, Any],
    form: Dict[str, str],
    note: str,
) -> Dict[str, Any]:
    """Write one step's request/before/response/after records (full saves)."""
    step_dir = staging / "steps" / name
    write_json(step_dir / "request.json", request_record(result, form, note))
    write_json(step_dir / "before.json", before)
    write_bytes(step_dir / "response.body", body)
    write_json(step_dir / "response.meta.json", response_record(result, body))
    write_json(step_dir / "after.json", after)
    return {
        "name": name,
        "method": result["method"],
        "path": result["path"],
        "target": result["target"],
        "status": result["status"],
        "response_bytes": len(body),
        "response_sha256": sha256_bytes(body),
        "save_before_sha256": save_bytes_sha(before),
        "save_after_sha256": save_bytes_sha(after),
        "save_unchanged_by_call": save_bytes_sha(before) == save_bytes_sha(after),
    }


# ------------------------------------------------------- derived batch ------
def build_fixture_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded batch: one ``collect`` carrying the content-derived payout.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.  The
    payout is the derived one the endpoint would derive for this row: the
    item's committed ``collect`` scaled by the top committed rung's multiplier
    in the slot its committed ``collect_type`` names, its committed
    ``collect_xp`` scaled by the same rung in the experience slot, and the
    unread ``unknown`` slot and the never-produced ``mana`` slot left zero.
    """
    payout = collect_envelope.payout_for(
        amount=FIXTURE_COLLECT_AMOUNT,
        resource_type=FIXTURE_COLLECT_TYPE,
        experience=FIXTURE_COLLECT_XP,
        tier=FIXTURE_EXPECTED_TIER,
        ladder=(FIXTURE_LADDER_MINUTES, FIXTURE_LADDER_MULTIPLIERS),
    )
    if payout != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the derived payout drifted from the pinned %r: %r"
            % (FIXTURE_EXPECTED_VECTOR, payout),
        )
    return collect_envelope.build_envelope(item_index=FIXTURE_ITEM_INDEX, vector=payout, ts=ts)


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its argument, and its resource vector are the derived
    contract (design D1/D2/D6/D7); that a real client sends exactly this — and
    that the amount, experience, resource, and rung a real client would use are
    the committed ones — is **derived-provisional** (design D1/D2), because no
    legacy branch reads the content behind them.  All of it is pinned here
    against the committed config and fresh save instead, and any drift fails
    the run rather than silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(collect_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a collection batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != collect_envelope.COLLECT_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r" % (collect_envelope.COLLECT_COMMAND, entry[1]),
        )
    if entry[2] != [FIXTURE_ITEM_INDEX]:
        raise CaptureError(
            EXIT_REQUEST,
            "collect args must be [%d], got %r" % (FIXTURE_ITEM_INDEX, entry[2]),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived resource vector drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR),
        )
    # The two slots the derivation can never fill stay zero (design D6).
    for index in collect_envelope.ALWAYS_ZERO_SLOTS:
        if entry[3][index] != 0:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived vector filled always-zero slot %d: %r"
                % (index, entry[3]),
            )
    # Exactly one resource slot plus the experience slot carry a value.
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying != [collect_envelope.EXPERIENCE_SLOT, 3]:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived vector pays unexpected slots %r (expected the "
            "experience slot and the wood slot)" % (paying,),
        )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived payout under
    the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the
    branch (``command.py:40``) and applies the 8-slot vector verbatim, per
    resource, as ``max(current + delta, 0)``; ``command.collect``
    (``command.py:136-147``) then resolves the row and writes
    ``item[3] = time_now()`` and nothing else.  No branch here touches
    ``privateState``, ``maps[0].store``, or ``playerInfo``.  Any mismatch means
    the capture would publish a fixture that contradicts its own derivation, so
    the run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        key = str(entry[2][0])
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    items_before = map_before["items"]
    items_after = map_after["items"]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if len(items_before) != FIXTURE_EXPECTED_PLACEMENTS_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "before-state placement count is %d (expected %d)"
            % (len(items_before), FIXTURE_EXPECTED_PLACEMENTS_BEFORE),
        )

    row_before = items_before.get(key)
    if not isinstance(row_before, list):
        raise CaptureError(EXIT_REQUEST, "no placement row at index %s to collect" % key)
    if len(row_before) != 8:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is not an eight-field entry" % key,
        )
    if int(row_before[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row is item %r, not the fixture item %d"
            % (row_before[0], FIXTURE_ITEM_ID),
        )
    if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row is anchored at %r, not the documented %r"
            % ([row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
        )
    # The fresh corpus carries no collection clock and no construction state,
    # which is what makes this fixture an observation of the top rung rather
    # than a partial one.
    if row_before[6] != {}:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row's attr is %r, not the committed empty bag"
            % (row_before[6],),
        )
    if row_before[3] != 0:
        raise CaptureError(
            EXIT_REQUEST,
            "the fixture row's timestamp is %r, not the committed 0"
            % (row_before[3],),
        )

    # A collection must never destroy or move the row: the key survives, holding
    # the same item at the very same cell.
    if key not in items_after:
        raise CaptureError(
            EXIT_REQUEST,
            "placement row at index %s is absent after the collection; the "
            "branch only rewrites the row's timestamp" % key,
        )
    row_after = items_after[key]
    if not isinstance(row_after, list) or len(row_after) != 8:
        raise CaptureError(EXIT_REQUEST, "the collected row is not an eight-field entry")
    if int(row_after[0]) != FIXTURE_ITEM_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "the collected row holds item %r, not the fixture item %d"
            % (row_after[0], FIXTURE_ITEM_ID),
        )
    if [row_after[1], row_after[2]] != [FIXTURE_X, FIXTURE_Y]:
        raise CaptureError(
            EXIT_REQUEST,
            "the collected row is anchored at %r, not the pre-execution cell %r"
            % ([row_after[1], row_after[2]], [FIXTURE_X, FIXTURE_Y]),
        )
    # The fresh wall-clock collection instant: the one documented
    # time-dependent value in the recorded state.  It must move STRICTLY
    # forward, because a collection that fails to re-stamp its clock paid an
    # income for nothing.
    stamp = row_after[3]
    if not isinstance(stamp, int) or isinstance(stamp, bool) or stamp <= 0:
        raise CaptureError(
            EXIT_REQUEST, "the collected row's timestamp is not a wall-clock stamp: %r"
            % (stamp,)
        )
    if stamp <= row_before[3]:
        raise CaptureError(
            EXIT_REQUEST,
            "the collected row's timestamp %r does not move strictly forward "
            "from the before-state's %r; collect stamps the current time"
            % (stamp, row_before[3]),
        )
    # Everything else about the row is untouched: the branch writes only the
    # timestamp.  In particular the attribute bag is NOT cleared and no
    # construction state appears — which is what design D5's refusal protects.
    for field, label in ((4, "orientation"), (5, "store"), (6, "attr"), (7, "player team")):
        if row_after[field] != row_before[field]:
            raise CaptureError(
                EXIT_REQUEST,
                "the collected row's %s changed %r -> %r; the branch writes only "
                "item[3]" % (label, row_before[field], row_after[field]),
            )
    if row_after[6] != {}:
        raise CaptureError(
            EXIT_REQUEST,
            "the collected row carries construction state %r; a collection must "
            "never introduce any" % (row_after[6],),
        )
    if row_after[5] != []:
        raise CaptureError(
            EXIT_REQUEST,
            "the collected row carries a stored-unit payload: %r" % (row_after[5],),
        )

    # No key is added or removed: the branch rewrites exactly one entry in place.
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].item keys changed; a collection adds and removes none"
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS_AFTER),
        )

    # Every other row is byte-identical: the branch writes exactly one entry.
    for other in items_before:
        if other == key:
            continue
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; a collection rewrites only the row "
                "it addresses" % other,
            )

    # Legacy apply_resources: max(current + delta, 0) per slot, applied once
    # for the single command.  EVERY stored resource must have moved by exactly
    # the derived delta — the value-level half of design D8's post-execution
    # proof, asserted here against the executed legacy server itself.
    total = list(entry[3])
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    if before_resources != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "the before-state resources %r are not the documented %r"
            % (before_resources, FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    slot_of = {
        "xp": collect_envelope.EXPERIENCE_SLOT,
        "gold": 2,
        "wood": 3,
        "oil": 4,
        "steel": 5,
        "cash": 6,
        "mana": 7,
    }
    for name in sorted(slot_of):
        delta = total[slot_of[name]]
        if delta != FIXTURE_EXPECTED_RESOURCE_DELTA.get(name, 0):
            raise CaptureError(
                EXIT_REQUEST,
                "the derived delta for %s is %r, not the documented %r"
                % (name, delta, FIXTURE_EXPECTED_RESOURCE_DELTA.get(name, 0)),
            )
        current = before_resources[name]
        expected = max(current + delta, 0)
        if after_resources[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (name, current, after_resources[name], expected),
            )

    # A collection stores nothing, records no purchase, and leaves the whole
    # private state alone: no branch here calls bought_unit_add,
    # push_dead_unit, buy_si_help, finish_si, or add_store_item.
    if map_after["store"] != map_before["store"]:
        raise CaptureError(EXIT_REQUEST, "maps[0].store changed; a collection stores never")
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; no collect branch writes it" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST, "playerInfo changed; the collect branch writes none of it"
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field in (
            "items",
            "store",
            "xp",
            "gold",
            "wood",
            "oil",
            "steel",
        ):
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the branch writes only the addressed row" % field,
            )


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    return {
        label: dir_group_record(REPO_ROOT / relative, relative)
        for relative, label in PROTECTED_FIXTURES
    }


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy collect fixture "
        "(contained, loopback only)."
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="fixture output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-disposable",
        action="store_true",
        help="do not delete the disposable copy (for debugging only)",
    )
    args = parser.parse_args(argv)

    if sys.version_info[:2] != (3, 9):
        print(
            "capture: refused: this command must run under CPython 3.9.x "
            "(pinned baseline); got %s" % sys.version.split()[0],
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT
    if not FRESH_PLAYER_SAVE.is_file():
        print("capture: missing seed save: %s" % FRESH_PLAYER_SAVE, file=sys.stderr)
        return EXIT_ENVIRONMENT

    out_dir = Path(args.out).resolve()
    if REPO_ROOT not in out_dir.parents:
        print(
            "capture: --out must be strictly inside the repository: %s" % out_dir,
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT

    if not port_is_free(LEGACY_HOST, LEGACY_PORT):
        print(
            "capture: port conflict: %s:%d is already in use; refusing to start "
            "the legacy server" % (LEGACY_HOST, LEGACY_PORT),
            file=sys.stderr,
        )
        return EXIT_PORT_BUSY

    pre_groups = containment_snapshot()
    pre_combined = snapshot_combined(pre_groups)
    pre_fixtures = protected_fixture_snapshot()

    # Fixtures are staged OUTSIDE the working tree and published only after
    # every check passed, so a failed run writes nothing into the repo.
    staging = Path(tempfile.mkdtemp(prefix="compat-collect-capture-staging-"))
    disposable: Optional[Path] = None
    process = None
    try:
        disposable, pid, seed_sha = build_disposable(Path(tempfile.gettempdir()))
        saves_dir = disposable / "saves"
        seed_group = save_group_record(saves_dir)
        print("capture: disposable copy: %s" % disposable)
        print("capture: starting legacy server on %s:%d ..." % (LEGACY_HOST, LEGACY_PORT))
        process, stdout_path, stderr_path = start_server(disposable)
        if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
            raise CaptureError(
                EXIT_SERVER,
                "legacy server did not become ready (exit=%s)\n--- stdout ---\n%s"
                "\n--- stderr ---\n%s"
                % (process.poll(), read_tail(stdout_path), read_tail(stderr_path)),
            )
        print("capture: legacy server ready (pid %d)" % process.pid)

        startup_record = save_group_record(saves_dir)
        if startup_record["sha256"] != seed_group["sha256"]:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "server startup rewrote the seeded corpus saves (group %s -> %s)"
                % (seed_group["sha256"], startup_record["sha256"]),
            )

        summaries: List[Dict[str, Any]] = []
        save_path = saves_dir / ("%s.save.json" % pid)

        # --- step 1: login (session cookie, save must stay identical) ------
        before_login = canonical_save(save_path)
        login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
        login_result = http_request(
            LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0
        )
        if login_result["status"] != 302:
            raise CaptureError(
                EXIT_REQUEST,
                "login_post: expected HTTP 302, got %r" % login_result["status"],
            )
        after_login = canonical_save(save_path)
        if save_bytes_sha(before_login) != save_bytes_sha(after_login):
            raise CaptureError(
                EXIT_CONTAINMENT,
                "login_post mutated the disposable corpus save; the login step "
                "must leave it byte-identical",
            )
        body = login_result.pop("body")
        cookie = extract_session_cookie(login_result)
        summaries.append(
            write_step(
                staging,
                "login_post",
                login_result,
                body,
                before_login,
                after_login,
                login_form,
                "Login form (USERID + GAMEVERSION) exactly as the boot, "
                "placement, purchase, move, sell, store, upgrade, and "
                "construction captures send it; recorded for session fidelity — "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- derive the collection envelope from the committed content ----
        before_collect = canonical_save(save_path)
        row_before = before_collect["maps"][0]["items"].get(
            str(FIXTURE_ITEM_INDEX)
        )
        if not isinstance(row_before, list) or len(row_before) != 8:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save has no eight-field row at index %d"
                % FIXTURE_ITEM_INDEX,
            )
        if [row_before[1], row_before[2]] != [FIXTURE_X, FIXTURE_Y]:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save anchors index %d at %r, not the documented %r"
                % (FIXTURE_ITEM_INDEX, [row_before[1], row_before[2]], [FIXTURE_X, FIXTURE_Y]),
            )
        if int(row_before[0]) != FIXTURE_ITEM_ID:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's index %d holds item %r, not %d"
                % (FIXTURE_ITEM_INDEX, row_before[0], FIXTURE_ITEM_ID),
            )
        if row_before[6] != {} or row_before[3] != 0:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's index %d already carries state (attr %r, "
                "timestamp %r); the fixture assumes neither construction state "
                "nor a collection clock"
                % (FIXTURE_ITEM_INDEX, row_before[6], row_before[3]),
            )
        if before_collect["maps"][0]["store"] != {}:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's storage is not empty; the fixture assumes %r"
                % (before_collect["maps"][0]["store"],),
            )
        # The income fields and the ladder are resolved from the committed
        # configuration, never hardcoded into the request; the pinned constants
        # are only the cross-check that fails the run if the committed config
        # drifts.
        resolved_amount = config_collect_amount(FIXTURE_ITEM_ID)
        if resolved_amount != FIXTURE_COLLECT_AMOUNT:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's collect to %r, "
                "not the pinned %d"
                % (FIXTURE_ITEM_ID, resolved_amount, FIXTURE_COLLECT_AMOUNT),
            )
        resolved_type = config_collect_type(FIXTURE_ITEM_ID)
        if resolved_type != FIXTURE_COLLECT_TYPE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's collect_type to "
                "%r, not the pinned %r"
                % (FIXTURE_ITEM_ID, resolved_type, FIXTURE_COLLECT_TYPE),
            )
        if resolved_type not in collect_envelope.COLLECT_RESOURCE_SLOTS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed collect_type %r is outside the closed vocabulary %s"
                % (resolved_type, sorted(collect_envelope.COLLECT_RESOURCE_SLOTS)),
            )
        resolved_xp = config_collect_xp(FIXTURE_ITEM_ID)
        if resolved_xp != FIXTURE_COLLECT_XP:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's collect_xp to %r, "
                "not the pinned %d"
                % (FIXTURE_ITEM_ID, resolved_xp, FIXTURE_COLLECT_XP),
            )
        resolved_cap = config_max_collects(FIXTURE_ITEM_ID)
        if resolved_cap != FIXTURE_MAX_COLLECTS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves item %d's max_collects to "
                "%r, not the pinned %d (only 0 is implemented; a non-zero cap is "
                "refused with capped_collection)"
                % (FIXTURE_ITEM_ID, resolved_cap, FIXTURE_MAX_COLLECTS),
            )
        minutes_tuple, multipliers_tuple = config_ladder()
        if list(minutes_tuple) != FIXTURE_LADDER_MINUTES:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed COLLECT_MINUTES resolve to %r, not the pinned %r"
                % (list(minutes_tuple), FIXTURE_LADDER_MINUTES),
            )
        if list(multipliers_tuple) != FIXTURE_LADDER_MULTIPLIERS:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed COLLECT_MULTIPLIER resolve to %r, not the pinned %r"
                % (list(multipliers_tuple), FIXTURE_LADDER_MULTIPLIERS),
            )
        # Every corpus row carries item[3] == 0, so the elapsed time against any
        # present instant is unbounded and the TOP rung is the deterministic
        # one.  Asserted rather than assumed.
        for other_key, other_row in before_collect["maps"][0]["items"].items():
            if int(other_row[3]) != 0:
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "corpus row %s carries a collection instant %r, so the "
                    "top-rung derivation would not be deterministic"
                    % (other_key, other_row[3]),
                )
        envelope = build_fixture_envelope()
        verify_envelope(envelope)
        data = collect_envelope.data_field(envelope)
        collect_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the single-command collection batch -------------------
        collect_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(collect_form),
            cookie=cookie,
            timeout=30.0,
        )
        if collect_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_collect: expected HTTP 200, got %r"
                % collect_result["status"],
            )
        after_collect = canonical_save(save_path)
        if save_bytes_sha(before_collect) == save_bytes_sha(after_collect):
            raise CaptureError(
                EXIT_REQUEST,
                "command_collect did not persist any save change; refusing to "
                "publish a non-transaction fixture",
            )
        body = collect_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_collect",
                collect_result,
                body,
                before_collect,
                after_collect,
                collect_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly one command: "
                "a collect whose single argument is the legacy map index and "
                "whose resources_changed is the CONTENT-DERIVED payout [0, 3, "
                "0, 60, 0, 0, 0, 0] — xp 1 x 3 in slot 1 and wood 20 x 3 in "
                "slot 3, both scaled by the top committed ladder rung, with the "
                "unread slot 0 and the never-produced mana slot 7 left zero; "
                "no amount, resource, tier, or time is client-supplied. The "
                "amount formula, the experience scaling, and the rung choice "
                "are DERIVED and never observed from the Flash client, while "
                "the branch's effect (item[3] = time_now and nothing else) and "
                "the vector's verbatim per-resource application with the "
                "max(..., 0) clamp are ESTABLISHED. user_key is redacted in this "
                "record; accessToken is the crafted empty placeholder, never a "
                "token value.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_collect, after_collect, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_collect response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
            )
        row_after = after_collect["maps"][0]["items"][str(FIXTURE_ITEM_INDEX)]
        resources_before = resources_of(before_collect)
        resources_after = resources_of(after_collect)

        # --- stop the server before any containment re-check ---------------
        server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
        process = None
        if server_error:
            raise CaptureError(EXIT_SERVER, server_error)
        print("capture: legacy server stopped; port %d free again" % LEGACY_PORT)

        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        if post_groups != pre_groups:
            changed = sorted(
                name
                for name in set(pre_groups) | set(post_groups)
                if pre_groups.get(name) != post_groups.get(name)
            )
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree bytes changed during the run: %s" % ", ".join(changed),
            )

        post_fixtures = protected_fixture_snapshot()
        if post_fixtures != pre_fixtures:
            changed = sorted(
                label
                for label in set(pre_fixtures) | set(post_fixtures)
                if pre_fixtures.get(label) != post_fixtures.get(label)
            )
            raise CaptureError(
                EXIT_CONTAINMENT,
                "committed fixtures changed during the run: %s" % ", ".join(changed),
            )

        if not args.keep_disposable and disposable is not None:
            shutil.rmtree(disposable, ignore_errors=False)
            disposable = None

        entry = envelope["commands"][0]
        manifest = {
            "schema": "godot-building-collect/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "collect transaction carrying the content-derived payout; the "
                "executed-legacy parity oracle for the Compatibility API v0 "
                "collect endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_collect_fixture.py"
            + ("" if not argv else " " + " ".join(argv)),
            "executed_at_utc": iso_now(),
            "exit_code": 0,
            "interpreter": {
                "executable": sys.executable,
                "version": sys.version,
                "requirement": "CPython 3.9.x (pinned baseline for this change)",
            },
            "server": {
                "command": [sys.executable, "-B", "server.py"],
                "cwd": "<disposable copy under the system temp root>",
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "readiness": "TCP connect loop on 127.0.0.1:%d (no extra HTTP request)"
                % LEGACY_PORT,
                "stopped_by": "taskkill /T /F <pid>, wait, then port-free re-check",
                "output_logs": "server.stdout.log / server.stderr.log inside the "
                "disposable copy (removed with the copy; not committed)",
                "port_free_before_start": True,
                "port_free_after_stop": True,
                "command_recorder_env": "SOCIALWARS_COMMAND_RECORD_DIR stripped from child",
            },
            "corpus": {
                "seed": {
                    "path": "tests/saves/fresh-player.json",
                    "file_sha256": seed_sha,
                    "saves_group_sha256_before_server_start": seed_group["sha256"],
                },
                "seeded_as": "saves/<pid>.save.json in the disposable copy",
                "startup_preserved_seed": True,
                "login_preserved_seed": True,
                "pid": pid,
            },
            "intent": {
                "item_index": FIXTURE_ITEM_INDEX,
                "item_id": FIXTURE_ITEM_ID,
                "item_name": FIXTURE_ITEM_NAME,
                "cell": [FIXTURE_X, FIXTURE_Y],
                "target_rule": TARGET_RULE,
                "bounds_rule": "not applicable: a collection has no target cell of "
                "its own — the branch rewrites only the addressed row's "
                "timestamp, and the cell is the recorded anchor the capture pins",
                "derived": {
                    "command": entry[1],
                    "args": entry[2],
                    "collect": FIXTURE_COLLECT_AMOUNT,
                    "collect_type": FIXTURE_COLLECT_TYPE,
                    "collect_xp": FIXTURE_COLLECT_XP,
                    "max_collects": FIXTURE_MAX_COLLECTS,
                    "resources_changed": entry[3],
                    "tier": FIXTURE_EXPECTED_TIER,
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "ladder": {
                        "minutes": list(minutes_tuple),
                        "multipliers": list(multipliers_tuple),
                        "rungs": [
                            {
                                "index": index,
                                "after_minutes": minutes_tuple[index],
                                "multiplier": multipliers_tuple[index],
                                "tree_payout": {
                                    "resource_slot": collect_envelope.COLLECT_RESOURCE_SLOTS[
                                        FIXTURE_COLLECT_TYPE
                                    ],
                                    "resource": "wood",
                                    "amount": int(
                                        FIXTURE_COLLECT_AMOUNT * multipliers_tuple[index]
                                    ),
                                    "experience": int(
                                        FIXTURE_COLLECT_XP * multipliers_tuple[index]
                                    ),
                                },
                            }
                            for index in range(len(minutes_tuple))
                        ],
                    },
                    "decisions": {
                        "D1_amount_formula": "amount = collect x the multiplier of the "
                        "highest committed rung the elapsed time has reached, clamped "
                        "at the top rung. DERIVED-PROVISIONAL: the two ladder globals "
                        "are parallel four-element arrays and no legacy branch reads "
                        "either, so the pairing is an inference. Rejected alternative: "
                        "a flat collect, or extrapolating past the last rung",
                        "D2_experience_scaling": "collect_xp is scaled by the same "
                        "rung as the amount. DERIVED-PROVISIONAL. Rejected "
                        "alternative: a flat collect_xp, which is equally "
                        "unobservable and is recorded so a later change can revisit "
                        "it with evidence",
                        "D3_sub_first_rung": "no rung reached fails closed with "
                        "too_early; the endpoint never derives a sub-five-minute "
                        "amount from the 0.25 multiplier. DERIVED-PROVISIONAL. "
                        "Rejected alternatives: a quarter of the amount, and "
                        "silently paying nothing",
                        "D4_cap_semantics": "a non-zero committed max_collects fails "
                        "closed with capped_collection; only 0 is implemented "
                        "(767 of 778 stored items record 0, and the corpus's income "
                        "rows all record 0). DERIVED-PROVISIONAL: nothing says "
                        "whether a non-zero cap limits one collection, a daily "
                        "total, or a lifetime output",
                        "D5_shared_field": "a collection is refused on a row whose "
                        "attribute bag carries cp or nc, in BOTH layers (the client "
                        "offers no Collect action; the endpoint fails closed with "
                        "construction_in_progress before the dispatcher runs). "
                        "ESTABLISHED RISK, DERIVED RULE: the executed probe below "
                        "showed the countdown surviving the overwrite while legacy "
                        "answered success; what the legacy client itself does is "
                        "never observed",
                        "D6_resource_mapping": "g->gold (slot 2), w->wood (3), o->oil "
                        "(4), s->steel (5), c->cash (6); the unread slot 0 and the "
                        "never-produced mana slot 7 are always zero, because no item "
                        "records a mana collect type. DERIVED-PROVISIONAL. Rejected "
                        "alternative: a 'm' mapping for a content value no item "
                        "records",
                        "D7_intent_only": "the request carries only the save id and "
                        "the row index; the amount, resource, experience, rung, and "
                        "reference instant are the service's own, derived from "
                        "committed content and the row's own instant",
                        "D8_two_part_proof": "after execution the row must still "
                        "exist, be an eight-field list, and its recorded collection "
                        "instant must move STRICTLY FORWARD, AND every stored "
                        "resource must have changed by EXACTLY the derived delta; "
                        "any other outcome fails closed with internal_error rather "
                        "than reporting the legacy success",
                    },
                    "status": "established: the command's argument shape and its "
                    "single effect (item[3] = time_now, command.py:136-147), that "
                    "the income is the client-sent 8-slot vector applied verbatim "
                    "per resource as max(current + delta, 0) and applied BEFORE the "
                    "branch (command.py:40, engine.py:251-271), the per-item income "
                    "content fields, the ladder globals, the corpus facts, that a "
                    "collection on a just-started construction overwrites the "
                    "build's start instant while the countdown survives, and the "
                    "resulting state from this executed transaction. DERIVED and "
                    "never observed from the Flash client: the amount formula (D1), "
                    "the experience scaling (D2), the sub-first-rung refusal (D3), "
                    "the cap semantics (D4), the shared-field refusal rule (D5), "
                    "and the cash/mana mapping (D6). The claim is that a payout "
                    "grows in four committed rungs derived from an item's committed "
                    "income fields, never any specific amount the legacy client "
                    "pays",
                },
            },
            "probes": PROBES,
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "row_before": list(row_before),
                "row_after": list(row_after),
                "entry_field_order": [
                    "item", "x", "y", "timestamp", "orientation", "store", "attr", "player",
                ],
                "placement_count_before": len(before_collect["maps"][0]["items"]),
                "placement_count_after": len(after_collect["maps"][0]["items"]),
                "key_reused": str(FIXTURE_ITEM_INDEX),
                "attr_before": list(row_before)[6],
                "attr_after": list(row_after)[6],
                "store_after": after_collect["maps"][0]["store"],
                "bought_units_before": before_collect["privateState"]["boughtUnits"],
                "bought_units_after": after_collect["privateState"]["boughtUnits"],
                "dead_heroes_after": after_collect["privateState"]["deadHeroes"],
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "other_rows_unchanged": True,
                "private_state_unchanged": True,
                "player_info_unchanged": True,
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) only bites when a "
                "delta would drive a balance below zero; the derived payout is a "
                "credit added to balances that sit far above zero, so this fixture "
                "never exercises the clamp",
                "cap_semantics_implemented": False,
                "cap_note": "only a committed max_collects of 0 is implemented; a "
                "non-zero cap is refused with capped_collection rather than "
                "interpreted",
                "friend_assist_in_scope": False,
                "construction_overlap": "item[3] is BOTH a construction start "
                "instant (activate) and a last-collection instant (collect); the "
                "endpoint refuses a row carrying cp or nc with "
                "construction_in_progress before the dispatcher runs, and the "
                "recorded after-state's attr bag is still {}",
                "collect_writes": [
                    "engine.apply_resources applies the derived payout on the single "
                    "command with max(..., 0) per resource, BEFORE the branch "
                    "(command.py:40; engine.py:251-271)",
                    "command.collect resolves the row and writes item[3] = "
                    "time_now() and nothing else (command.py:136-147)",
                    "no branch compares the elapsed time with COLLECT_MINUTES, reads "
                    "COLLECT_MULTIPLIER or max_collects, and no branch writes "
                    "privateState, maps[0].store, or playerInfo",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "every other leaf of every committed file is byte-identical "
                    "across reruns; the leaves below are the whole documented "
                    "time-dependent surface, and the claim is machine-checkable: "
                    "a leaf-level diff of two consecutive runs must differ at "
                    "exactly these 11 paths and nowhere else"
                ),
                "leaves": [
                    "/captured_at_utc in steps/login_post/request.json",
                    "/captured_at_utc in steps/login_post/response.meta.json",
                    "/captured_at_utc in steps/command_collect/request.json",
                    "/captured_at_utc in steps/command_collect/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in steps/login_post/response.meta.json",
                    "/headers/Date in steps/command_collect/response.meta.json",
                    "the envelope ts inside steps/command_collect/request.json's "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                    "the collected row's wall-clock collection instant: "
                    "/maps/0/items/%d/3 in steps/command_collect/after.json, and "
                    "the two manifest leaves derived from it — "
                    "/transaction/row_after/3 and "
                    "/transaction/steps/1/save_after_sha256" % FIXTURE_ITEM_INDEX,
                ],
                "stable_by_derivation": (
                    "the resource movement is byte-stable because the derived "
                    "payout is fixed: every corpus row's item[3] is 0, so the "
                    "top committed rung applies deterministically and the payout "
                    "is always [0, 3, 0, 60, 0, 0, 0, 0], making "
                    "/transaction/resources_after, /transaction/resource_delta, "
                    "and the resource leaves of the two save documents stable"
                ),
                "documented_normalization": (
                    "collect parity compares the row's collection instant as a "
                    "positive integer STRICTLY GREATER than the before-state's, "
                    "never by value: legacy stamps it with timestamp_now() and no "
                    "branch interprets it. The reference instant the rung was "
                    "computed against is a service-side value the endpoint reports "
                    "as reference_time, never a recorded legacy field. No other "
                    "clock field is written"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, and "
                    "construction fixtures are digest-pinned for the same reason."
                ),
                "pre_run": pre_groups,
                "post_run": post_groups,
                "pre_combined_sha256": pre_combined,
                "post_combined_sha256": post_combined,
                "protected_fixtures": {
                    "paths": [relative for relative, _label in PROTECTED_FIXTURES],
                    "pre_run": pre_fixtures,
                    "post_run": post_fixtures,
                    "identical": True,
                },
                "identical": True,
                "working_tree_saves_unchanged": True,
                "fixture_output": str(out_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
                "only_working_tree_writes": "fixture files under --out",
                "disposable_copy_removed": args.keep_disposable is False,
                "loopback_only": True,
                "no_flash_browser_external_network": True,
            },
            "cleanup": {
                "disposable_removed_before_manifest_write": args.keep_disposable is False,
                "server_stopped_within_run": True,
            },
        }

        try:
            write_json(staging / "capture-manifest.json", manifest)
            out_dir.mkdir(parents=True, exist_ok=True)
            clear_previous_fixtures(out_dir)
            shutil.move(str(staging / "steps"), str(out_dir / "steps"))
            shutil.move(
                str(staging / "capture-manifest.json"),
                str(out_dir / "capture-manifest.json"),
            )
        except OSError as error:
            raise CaptureError(EXIT_WRITE, "could not write fixtures: %s" % error)

        print("capture: wrote %d step fixtures to %s" % (len(summaries), out_dir))
        for summary in summaries:
            print(
                "capture:   %-22s %s %s -> %d (%d bytes, save unchanged: %s)"
                % (
                    summary["name"],
                    summary["method"],
                    summary["target"],
                    summary["status"],
                    summary["response_bytes"],
                    summary["save_unchanged_by_call"],
                )
            )
        print(
            "capture: derived command %s%s with resources %s (tier %d of the "
            "committed ladder)"
            % (
                entry[1],
                entry[2],
                entry[3],
                FIXTURE_EXPECTED_TIER,
            )
        )
        print(
            "capture: slot %d (%s) at cell %r collected in place, placements "
            "%d -> %d, store %r, boughtUnits %r -> %r, deadHeroes %r, attr %r -> %r"
            % (
                FIXTURE_ITEM_INDEX,
                FIXTURE_ITEM_NAME,
                [row_before[1], row_before[2]],
                len(before_collect["maps"][0]["items"]),
                len(after_collect["maps"][0]["items"]),
                after_collect["maps"][0]["store"],
                before_collect["privateState"]["boughtUnits"],
                after_collect["privateState"]["boughtUnits"],
                after_collect["privateState"]["deadHeroes"],
                list(row_before)[6],
                list(row_after)[6],
            )
        )
        for name in sorted(resources_before):
            print(
                "capture:   %-5s %d -> %d (delta %+d)"
                % (
                    name,
                    resources_before[name],
                    resources_after[name],
                    resources_after[name] - resources_before[name],
                )
            )
        print(
            "capture: collected row %r (the timestamp is the documented "
            "time-dependent field: the collection instant)"
            % (list(row_after),)
        )
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except collect_envelope.EnvelopeError as error:
        print(
            "capture: FAILED: could not derive the envelope: [%s] %s"
            % (error.code, error),
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT
    except CaptureError as error:
        print("capture: FAILED: %s" % error, file=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        print("capture: interrupted", file=sys.stderr)
        return 130
    finally:
        if process is not None:
            leftover = stop_server(process, LEGACY_HOST, LEGACY_PORT)
            if leftover:
                print("capture: stop problem: %s" % leftover, file=sys.stderr)
        if disposable is not None and not args.keep_disposable:
            shutil.rmtree(disposable, ignore_errors=True)
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
