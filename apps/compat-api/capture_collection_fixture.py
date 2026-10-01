#!/usr/bin/env python3
"""Capture the executed-legacy collection-completion fixture (contained).

M8 line 5 (``collection``), design D3/D6.  One recorded transaction: a real
``complete_collection`` against the committed fresh-player corpus, carrying a
**neutral** vector and the collection id whose committed prize is a **unit**.

Why this capture exists and what it is worth
-------------------------------------------
This is the **first content-derived, server-authoritative unit acquisition** in
the project.  ``command.complete_collection`` (``command.py:504-523``) calls
``get_collection_prize(collection_id)``, which reads the loaded configuration's
committed ``collections`` table positionally (``get_game_config.py:170-175``)
and returns ``json.loads(collections[index]['prize'])``.  The branch then grants
every entry of that bag into ``map["store"]`` through ``engine.add_store_item``
(``engine.py:70-75``) and appends the id to ``privateState["collections"]`` when
it is absent.  So the **client names which collection** and the **server decides
what it receives** — the only legacy acquisition route whose ids come from
committed content, and the completion the delivered ``godot-unit-production``
acquisition finding needed.

The committed corpus records ``maps[0]["store"] == {}`` and
``privateState["collections"] == []``, so the grant is a real, observable write
against an **empty** storage and an **empty** ledger — **no fabricated player
state** is involved.

Scope, deliberately stopped (design D6)
--------------------------------------
The capture records the **grant into storage** and stops there.  It does **not**
chain ``place_stored_item``, which would put the granted unit on the map: the
stored-item round trip is a **carried follow-up**, and delivering it here would
widen this line past its contract.  The manifest records that the two steps
together form a committed path by which a unit enters a town and that **only the
first step is delivered here**, so the fixture is never read as "a unit was
placed".

What is deliberately **not** in this capture
--------------------------------------------
* **No eligibility check**, because none exists: the committed ``item_ids``
  requirement list is read by **no** branch, so a client may name any of the ten
  committed collections (design D2 — recorded, not fixed).
* **No unit income, no cap semantics, and no experience**, because no committed
  unit records a positive ``collect``, ``max_collects`` is ``0`` on every unit,
  and ``collect_xp`` has no legacy reader while the only writer takes a
  client-sent amount (design D5).
* **No pixel parity** and no claim about what the Flash client displayed.

The probe
---------
The capture runs **one probe** against the same live server after the recorded
steps.  It is not a recorded transaction; it is recorded in the manifest because
it is the executed evidence for two otherwise-tautological claims:

1. the derived vector really is **NEUTRAL by necessity** — a completion carrying
   a client-sent non-zero slot moves a balance through this very branch, which is
   what makes "every stored resource is unchanged" a real constraint;
2. the committed ``item_ids`` requirement list really is **never consulted** — a
   completion of a collection whose items are demonstrably absent still grants
   the prize and appends the id.

Exit codes (identical to the twelve delivered captures)
=======================================================
0    Success
1    Unexpected/unclassified error
2    Environment or precondition failure (including a refused derivation)
3    Port conflict: 127.0.0.1:5055 already in use
4    Legacy server failed to start, crashed, or the port stayed busy
5    A legacy request failed, returned an unexpected status, or the executed
     transaction did not match the derived envelope
6    Containment violation (working-tree bytes changed, a committed fixture
     directory changed, or the disposable corpus saves changed during server
     startup / login)
7    Fixture write failure
===== ======================================================================

Exact invocation (from the repository root):

    python -B apps/compat-api/capture_collection_fixture.py

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
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collection_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-unit-collection"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a corpus
# and initialize live legacy state).
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The committed corpus target, pinned here AND cross-checked against the real
# configuration and the real save below, so a drift fails the run instead of
# publishing a different fixture.
FIXTURE_COLLECTION_ID = collection_envelope.COMMITTED_COLLECTION_ID
FIXTURE_COLLECTION_NAME = collection_envelope.COMMITTED_COLLECTION_NAME
FIXTURE_PRIZE_ID = collection_envelope.COMMITTED_PRIZE_ID
FIXTURE_PRIZE_QUANTITY = collection_envelope.COMMITTED_PRIZE_QUANTITY
FIXTURE_EXPECTED_VECTOR: List[int] = [0] * collection_envelope.RESOURCE_VECTOR_SLOTS
FIXTURE_EXPECTED_PLACEMENTS = collection_envelope.COMMITTED_PLACEMENTS
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = dict(
    collection_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    collection_envelope.COMMITTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    name: 0 for name in collection_envelope.COMMITTED_RESOURCE_BEFORE
}
FIXTURE_EXPECTED_STORE_AFTER: Dict[str, int] = {
    str(FIXTURE_PRIZE_ID): FIXTURE_PRIZE_QUANTITY
}
FIXTURE_EXPECTED_LEDGER_AFTER: List[int] = [FIXTURE_COLLECTION_ID]
TARGET_RULE = (
    "the committed fresh-player corpus records maps[0]['store'] == {} and "
    "privateState['collections'] == [], so the committed grant is an observable "
    "write into an EMPTY storage and an EMPTY ledger - with NO fabricated player "
    "state, which is what makes this the FIRST content-derived, server-"
    "authoritative unit acquisition in the project. Collection id 1 is chosen "
    "because its committed prize is unit 1085 Metal Draggy; the other five unit "
    "prizes (1062, 1096, 1073, 1010, 1056) are equally exercisable against the "
    "same corpus"
)

# Committed fixtures that must be byte-identical across this run.  This is the
# twelve delivered directories: the eleven `godot-*` fixture directories plus
# the boot fixture's own.
PROTECTED_FIXTURES = (
    ("tests/fixtures/godot-compatibility-boot", "godot-compatibility-boot"),
    ("tests/fixtures/godot-building-placement", "godot-building-placement"),
    ("tests/fixtures/godot-item-purchase", "godot-item-purchase"),
    ("tests/fixtures/godot-building-move", "godot-building-move"),
    ("tests/fixtures/godot-building-sell", "godot-building-sell"),
    ("tests/fixtures/godot-building-store", "godot-building-store"),
    ("tests/fixtures/godot-building-upgrade", "godot-building-upgrade"),
    ("tests/fixtures/godot-building-construction", "godot-building-construction"),
    ("tests/fixtures/godot-building-collect", "godot-building-collect"),
    ("tests/fixtures/godot-building-expand", "godot-building-expand"),
    ("tests/fixtures/godot-building-xp", "godot-building-xp"),
    ("tests/fixtures/godot-unit-queues", "godot-unit-queues"),
)

# The executed-legacy probe this capture runs itself, after the recorded step and
# on the same live server.  It is recorded in the manifest rather than as a step
# because it is evidence for the derivation's guarantees, not a recorded
# transaction of this fixture.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does a collection completion actually write, and does a "
            "client-sent resource vector really move a balance through it?"
        ),
        "commands": [
            "complete_collection([1, 0]) with a CLIENT-SENT vector "
            "[0, 500, 0, 0, 0, 0, 0, 0]",
        ],
        "grant_note": "maps[0]['store'] grew from {'1085': 1} to {'1085': 2}, so "
            "the committed bag was granted a SECOND time from the same already-"
            "completed collection",
        "ledger_note": "privateState['collections'] stayed [1]: the append is "
            "if-absent (command.py:517), so the LEDGER is idempotent while the "
            "GRANT is not",
        "xp_before": 4,
        "xp_after": 504,
        "changed_top_level_map_keys": ["store", "xp"],
        "other_resources": "gold 2000, wood 2000, oil 2000, steel 2000, "
        "playerInfo.cash 5 and privateState.mana 0 all unchanged",
        "response": '{"result":"success"}',
        "established": (
            "the branch writes ONLY map['store'] and (when absent) the private "
            "state's collection ledger (command.py:504-523): the experience "
            "move is entirely client-sent, because apply_resources runs BEFORE "
            "the branch (command.py:40; engine.py:251-271) and applies the 8-slot "
            "vector verbatim per resource as max(current + delta, 0)"
        ),
        "why_it_matters": (
            "two claims in this contract would otherwise be tautologies. (a) The "
            "derived NEUTRAL vector: a completion carrying a non-zero slot moves a "
            "balance through this very branch, so requiring that EVERY stored "
            "resource be unchanged after execution distinguishes a correct "
            "completion from a resource-minting exploit wearing its clothes "
            "(design D1/D5). (b) The append-if-absent rule: the ledger staying at "
            "[1] while the prize was granted AGAIN is the executed proof that the "
            "ledger is idempotent and the grant is not, which is exactly what the "
            "endpoint's second proof half has to reproduce"
        ),
        "executed_in_this_capture": True,
    },
    {
        "probe": 2,
        "question": (
            "does the legacy server check that a collection's items were actually "
            "collected before granting its prize?"
        ),
        "commands": [
            "complete_collection([10, 0]) — collection 10 'Animal Collection', "
            "whose committed item_ids are [61, 62, 63, 64, 65] and whose "
            "committed prize is unit 1056 Elephant rider; the corpus places NONE "
            "of those five items",
        ],
        "grant_note": "maps[0]['store'] gained '1056': 1, on top of the "
            "already-granted '1085': 2",
        "ledger_note": "privateState['collections'] grew from [1] to [1, 10]",
        "response": '{"result":"success"}',
        "established": (
            "NO eligibility check exists. The committed `item_ids` requirement "
            "list is read by NO branch in the legacy source (zero quoted "
            "\"item_ids\" occurrences across the ten legacy root modules), and "
            "the completion branch never looks at the caller's collection state: "
            "the only read of privateState['collections'] is the append-if-absent "
            "test at command.py:517"
        ),
        "why_it_matters": (
            "it is the executed evidence for design D2's authority gap. A caller "
            "may name ANY of the ten committed collections and receive whatever "
            "that collection genuinely grants. This contract RECORDS that gap and "
            "implements no check, because adding one would invent a rule the "
            "legacy server does not have; authoritative validation belongs to a "
            "later server-authoritative milestone. The probe also shows the "
            "grant's contents stay content-derived even when eligibility is "
            "unchecked: the client chose WHICH collection, never WHAT it received"
        ),
        "executed_in_this_capture": True,
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_complete_collection")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5,
                         "cash": 6, "mana": 7}

# The map fields that hold a slot of the 8-slot vector.  ``cash`` and ``mana``
# live outside the map (``playerInfo`` / ``privateState``), so they are absent
# here by construction.
MAP_RESOURCE_FIELDS = ("xp", "gold", "wood", "oil", "steel")

# Every other map field the executed transaction must leave byte-identical,
# named explicitly so the pre-publish check is readable, and then enforced for
# the **whole** key set (including the fields the corpus does not record).
MAP_FIELDS_THAT_MUST_NOT_MOVE = (
    "id",
    "items",
    "level",
    "currentQuestVars",
    "expirableUnitsTime",
    "idCurrentMission",
    "idCurrentTreasure",
    "increasedPopulation",
    "numTradesDone",
    "questTimes",
    "race",
    "receivedAssists",
    "reputation",
    "rescue",
    "sizeX",
    "sizeY",
    "speed",
    "expansions",
)

ITEMS_FIELD = "items"

# The JSON pointers of the only two leaves this transaction may move, and the
# pointer of the single storage entry it writes.
STORE_POINTER = "/maps/0/store"
LEDGER_POINTER = "/privateState/collections"
GRANTED_POINTER = "/maps/0/store/%d" % FIXTURE_PRIZE_ID


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The stored legacy configuration, or a refusal.

    Read directly from the repository (never by importing a legacy module: doing
    so would chdir into a corpus and initialize live legacy state).
    """
    try:
        with CONFIG_MAIN.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "cannot read the committed configuration %s: %s" % (CONFIG_MAIN, error),
        )
    if not isinstance(document, dict):
        raise CaptureError(
            EXIT_ENVIRONMENT, "the committed configuration is not a JSON object"
        )
    return document


def config_item(item_id: int) -> Optional[Dict[str, Any]]:
    """The stored configuration row for ``item_id``, or ``None``."""
    for row in config_document().get("items", []):
        if isinstance(row, dict) and str(row.get("id")) == str(item_id):
            return row
    return None


def config_name(item_id: int) -> str:
    """The stored item's committed name, or ``""``."""
    row = config_item(item_id)
    return str(row.get("name", "")) if row else ""


def config_type(item_id: int) -> str:
    """The stored item's committed ``type`` (``u``/``b``/``l``), or ``""``."""
    row = config_item(item_id)
    return str(row.get("type", "")) if row else ""


# ------------------------------------------------------------ sanitization --
def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact sent
    bytes; this keeps the record secret-free even if that placeholder ever
    changes.  The field is rebuilt with :func:`collection_envelope.data_field`,
    so the digest stays valid against the recorded payload and a reader can
    verify it - which is what makes the redaction auditable rather than merely
    quiet.  This is the eleven delivered captures' own rule.
    """
    envelope = collection_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return collection_envelope.data_field(envelope)


# ----------------------------------------------------------------- records --
def canonical_save(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise CaptureError(EXIT_REQUEST, "the persisted save is not a JSON object")
    return document


def save_bytes_sha(document: Dict[str, Any]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return sha256_bytes(payload)


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven stored resource values the legacy code maintains."""
    return {
        "xp": int(document["maps"][0]["xp"]),
        "gold": int(document["maps"][0]["gold"]),
        "wood": int(document["maps"][0]["wood"]),
        "oil": int(document["maps"][0]["oil"]),
        "steel": int(document["maps"][0]["steel"]),
        "cash": int(document["playerInfo"]["cash"]),
        "mana": int(document["privateState"]["mana"]),
    }


def leaf_differences(before: Any, after: Any) -> List[str]:
    """Every JSON pointer whose value differs between two documents."""
    collected: List[str] = []

    def walk(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                child = "%s/%s" % (path, key)
                if key not in left or key not in right:
                    collected.append(child)
                else:
                    walk(left[key], right[key], child)
            return
        if isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                collected.append(path)
                return
            for index, (one, two) in enumerate(zip(left, right)):
                walk(one, two, "%s/%d" % (path, index))
            return
        if left != right:
            collected.append(path)

    walk(before, after, "")
    return collected


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


# --------------------------------------------------------- derived batches --
def build_complete_envelope(ts: Optional[int] = None) -> Dict[str, Any]:
    """The recorded batch: one ``complete_collection`` with the neutral vector.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.
    """
    envelope = collection_envelope.build_envelope(
        collection_id=FIXTURE_COLLECTION_ID, ts=ts
    )
    verify_envelope(envelope)
    return envelope


def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its **two-argument** list (the collection id and the
    print-only ``bought`` flag), and its **neutral** vector are the derived
    contract (design D1/D5); that a real client sends exactly this is **derived**
    too, because no legacy branch reads any content behind it.  All of it is
    pinned here against the committed config and fresh save instead, and any
    drift fails the run rather than silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(collection_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "a collection batch must carry exactly one command, got %d"
            % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != collection_envelope.COMPLETE_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (collection_envelope.COMPLETE_COMMAND, entry[1]),
        )
    if entry[2] != [FIXTURE_COLLECTION_ID, collection_envelope.DERIVED_BOUGHT]:
        raise CaptureError(
            EXIT_REQUEST,
            "args must be [%d, %d] — the collection id and the print-only "
            "`bought` flag, which writes nothing anywhere"
            % (FIXTURE_COLLECTION_ID, collection_envelope.DERIVED_BOUGHT),
        )
    if len(entry[2]) != 2:
        raise CaptureError(
            EXIT_REQUEST,
            "complete_collection takes exactly two positional arguments, got %r"
            % (entry[2],),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived neutral vector drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR),
        )
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying:
        raise CaptureError(
            EXIT_REQUEST,
            "the collection vector must be neutral, got slots %r" % (paying,),
        )


def verify_target(before: Dict[str, Any]) -> None:
    """The corpus's own collection target, verified against the real config."""
    store = before["maps"][0].get("store")
    if store != {}:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's storage is %r, not the committed {}; the fixture "
            "assumes an EMPTY storage so the committed grant is an observable "
            "write" % (store,),
        )
    ledger = before["privateState"].get("collections")
    if ledger != []:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's collection ledger is %r, not the committed []; the "
            "fixture assumes an EMPTY ledger" % (ledger,),
        )
    if resources_of(before) != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save's resources are %r, not the committed %r"
            % (resources_of(before), FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    items = before["maps"][0][ITEMS_FIELD]
    if len(items) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save holds %d placements, not the pinned %d"
            % (len(items), FIXTURE_EXPECTED_PLACEMENTS),
        )
    if before["privateState"].get("boughtUnits") != []:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the fresh save already records bought units; a completion records "
            "none, which the fixture relies on",
        )
    # The committed collection row behind the target, read from the stored
    # configuration the running server itself loads, so the pinned name and prize
    # are the ones legacy would read.
    table = config_document().get("collections")
    if not isinstance(table, list):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed configuration carries no collections table",
        )
    projected = collection_envelope.project_prize(table, FIXTURE_COLLECTION_ID)
    if not bool(projected.get("ok", False)):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "collection id %d does not resolve in the committed configuration: %s"
            % (FIXTURE_COLLECTION_ID, projected.get("error", "")),
        )
    if str(projected["name"]) != FIXTURE_COLLECTION_NAME:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed collection %d is named %r, not the pinned %r"
            % (FIXTURE_COLLECTION_ID, projected["name"], FIXTURE_COLLECTION_NAME),
        )
    if projected["prize"] != FIXTURE_EXPECTED_STORE_AFTER:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed collection %d grants %r, not the pinned %r"
            % (FIXTURE_COLLECTION_ID, projected["prize"],
               FIXTURE_EXPECTED_STORE_AFTER),
        )
    if config_type(FIXTURE_PRIZE_ID) != "u":
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed prize id %d has type %r, not 'u'; this fixture's whole "
            "point is a UNIT prize"
            % (FIXTURE_PRIZE_ID, config_type(FIXTURE_PRIZE_ID)),
        )
    if config_name(FIXTURE_PRIZE_ID) != "Metal Draggy":
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed prize id %d is named %r, not the pinned 'Metal Draggy'"
            % (FIXTURE_PRIZE_ID, config_name(FIXTURE_PRIZE_ID)),
        )


# -------------------------------------------------------- transaction check --
def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived neutral
    vector under the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the branch
    (``command.py:40``) and applies the 8-slot vector verbatim, per resource, as
    ``max(current + delta, 0)``; the branch then grants the **committed** prize
    into the storage and appends the id to the ledger.  Any mismatch means the
    capture would publish a fixture that contradicts its own derivation, so the
    run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_id = entry[2][0]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    if sent_id != FIXTURE_COLLECTION_ID:
        raise CaptureError(
            EXIT_REQUEST,
            "the sent collection id %r is not the pinned %d"
            % (sent_id, FIXTURE_COLLECTION_ID),
        )

    # --- the subject: the committed grant and the ledger, through ONE derivation
    # shared with the endpoint (so the capture and the service cannot disagree).
    try:
        divergence = collection_envelope.expected_grant(
            map_before["store"],
            map_after["store"],
            FIXTURE_EXPECTED_STORE_AFTER,
            collection_id=FIXTURE_COLLECTION_ID,
            before_ledger=before["privateState"]["collections"],
            after_ledger=after["privateState"]["collections"],
        )
    except collection_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_REQUEST,
            "the collection derivation does not resolve: [%s] %s" % (error.code, error),
        )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "the executed completion did not produce the committed grant: %s"
            % divergence,
        )
    if map_after["store"] != FIXTURE_EXPECTED_STORE_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].store is %r after the completion, not the committed %r"
            % (map_after["store"], FIXTURE_EXPECTED_STORE_AFTER),
        )
    if after["privateState"]["collections"] != FIXTURE_EXPECTED_LEDGER_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "privateState.collections is %r after the completion, not the derived "
            "%r (exactly ONE appended id)"
            % (after["privateState"]["collections"], FIXTURE_EXPECTED_LEDGER_AFTER),
        )

    # --- the placements: none is added, removed, or changed.
    items_before = map_before[ITEMS_FIELD]
    items_after = map_after[ITEMS_FIELD]
    if not isinstance(items_before, dict) or not isinstance(items_after, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not a mapping")
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].item keys changed; a completion places and removes none",
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS),
        )
    for other in items_before:
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; a completion writes into the storage, "
                "never onto the map" % other,
            )

    # --- the other map scalars.
    if map_after.get("increasedPopulation") != map_before.get("increasedPopulation"):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].increasedPopulation changed from %r to %r"
            % (map_before.get("increasedPopulation"),
               map_after.get("increasedPopulation")),
        )
    if map_after.get("level") != map_before.get("level"):
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].level changed from %r to %r; a completion grants a stored "
            "item, never experience"
            % (map_before.get("level"), map_after.get("level")),
        )
    if map_after.get("expansions") != map_before.get("expansions"):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].expansions changed; a completion grants none"
        )

    # --- the whole key set, so a field this tool does not name cannot move
    # either.
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; a completion writes the "
            "storage and the private ledger and adds or removes nothing"
            % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field == ITEMS_FIELD or field == "store":
            continue
        if field in MAP_RESOURCE_FIELDS:
            # The map's own resource fields are the client-sent vector's
            # territory; they are checked by value below.
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the completion branch writes the storage and "
                "the private collection ledger only" % field,
            )
    for field in MAP_FIELDS_THAT_MUST_NOT_MOVE:
        if field in map_before and field not in map_after:
            raise CaptureError(EXIT_REQUEST, "maps[0].%s was removed" % field)

    # --- the rest of the private state and the player info.
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if name == "collections":
            continue
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; the completion branch writes only "
                "privateState['collections']" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST,
            "playerInfo changed; the completion branch writes none of it",
        )

    # --- the money: every stored resource must have moved by EXACTLY the derived
    # neutral vector under legacy's max(current + delta, 0).  For a completion
    # that is no movement at all; the value-level half of design D1's
    # post-execution proof, asserted here against the executed legacy server.
    total = list(entry[3])
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        delta = total[RESOURCE_VECTOR_SLOTS[name]]
        if delta != FIXTURE_EXPECTED_RESOURCE_DELTA[name]:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived vector for %s is %r, not the documented %r"
                % (name, delta, FIXTURE_EXPECTED_RESOURCE_DELTA[name]),
            )
        current = before_resources[name]
        expected = max(current + delta, 0)
        if after_resources[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "resource %s changed unexpectedly: %r -> %r (expected %r)"
                % (name, current, after_resources[name], expected),
            )
    if after_resources != FIXTURE_EXPECTED_RESOURCE_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "the after-state resources %r are not the documented %r"
            % (after_resources, FIXTURE_EXPECTED_RESOURCE_AFTER),
        )
    return {
        "collection_id": FIXTURE_COLLECTION_ID,
        "command": collection_envelope.COMPLETE_COMMAND,
        "store_before": dict(map_before["store"]),
        "store_after": dict(map_after["store"]),
        "granted": {
            str(FIXTURE_PRIZE_ID): FIXTURE_PRIZE_QUANTITY,
        },
        "grant_pointer": GRANTED_POINTER,
        "ledger_before": list(private_before["collections"]),
        "ledger_after": list(private_after["collections"]),
        "ledger_pointer": LEDGER_POINTER,
        "ledger_appended": True,
        "changed_leaves": leaf_differences(before, after),
    }


def build_probe_envelope(
    collection_id: int = FIXTURE_COLLECTION_ID, ts: Optional[int] = None
) -> Dict[str, Any]:
    """The first probe's batch: a completion with a **client-sent** vector.

    Crafted by hand rather than through the derivation, because the whole point
    is the vector the derivation **refuses** to express:
    :func:`collection_envelope.validate_vector` would reject it, which is exactly
    the guarantee the probe makes concrete.
    """
    if ts is None:
        ts = 1700000000
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [
                0,
                collection_envelope.COMPLETE_COMMAND,
                [collection_id, collection_envelope.DERIVED_BOUGHT],
                [0, 500, 0, 0, 0, 0, 0, 0],
            ]
        ],
    }


def verify_probe_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
    prize: Dict[str, int],
    expected_ledger: List[int],
) -> Dict[str, Any]:
    """Structural proof for one executed probe, returning its observed facts.

    The probe asserts exactly what it was run to establish: the sent experience
    moved by exactly the sent delta, the committed prize was granted again from
    the **already-completed** collection while the ledger did **not** grow, and
    every other stored field is untouched.
    """
    try:
        entry = envelope["commands"][0]
        sent_vector = list(entry[3])
        sent_id = entry[2][0]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "probe envelope/save shape unexpected: %s" % error)
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        expected = max(before_resources[name] + sent_vector[RESOURCE_VECTOR_SLOTS[name]], 0)
        if after_resources[name] != expected:
            raise CaptureError(
                EXIT_REQUEST,
                "probe: resource %s went %r -> %r, not the sent-delta %r"
                % (name, before_resources[name], after_resources[name], expected),
            )
    try:
        divergence = collection_envelope.expected_grant(
            map_before["store"],
            map_after["store"],
            prize,
            collection_id=sent_id,
            before_ledger=before["privateState"]["collections"],
            after_ledger=after["privateState"]["collections"],
        )
    except collection_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_REQUEST,
            "probe: the collection derivation does not resolve: [%s] %s"
            % (error.code, error),
        )
    if divergence is not None:
        raise CaptureError(
            EXIT_REQUEST,
            "probe: the executed completion did not produce the committed grant: %s"
            % divergence,
        )
    if after["privateState"]["collections"] != expected_ledger:
        raise CaptureError(
            EXIT_REQUEST,
            "probe: privateState.collections is %r, not the derived %r"
            % (after["privateState"]["collections"], expected_ledger),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field in MAP_RESOURCE_FIELDS:
            # The map's own resource fields are the client-sent vector's
            # territory and were already checked by value above; cash and mana
            # live outside the map entirely.
            continue
        if field == ITEMS_FIELD or field == "store":
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "probe: maps[0].%s changed, but the branch writes only the "
                "storage and the collection ledger (the experience move is the "
                "client-sent vector)" % field,
            )
    return {
        "store_before": dict(map_before["store"]),
        "store_after": dict(map_after["store"]),
        "ledger_before": list(before["privateState"]["collections"]),
        "ledger_after": list(after["privateState"]["collections"]),
        "xp_before": before_resources["xp"],
        "xp_after": after_resources["xp"],
        "changed_top_level_map_keys": [
            field
            for field in sorted(set(map_before) | set(map_after))
            if map_after.get(field) != map_before.get(field)
        ],
        "leaf_differences": leaf_differences(before, after),
        "resources_before": before_resources,
        "resources_after": after_resources,
    }


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    return {
        label: dir_group_record(REPO_ROOT / relative, relative)
        for relative, label in PROTECTED_FIXTURES
    }


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy collection-completion fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-collection-capture-staging-"))
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
        transaction: Dict[str, Any] = {}
        save_path = saves_dir / ("%s.save.json" % pid)

        # --- step 1: login (session cookie, save must stay identical) ------
        before_login = canonical_save(save_path)
        verify_target(before_login)
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
                "Login form (USERID + GAMEVERSION) exactly as the eleven "
                "delivered captures send it; recorded for session fidelity — "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- step 2: the completion ----------------------------------------
        before_complete = canonical_save(save_path)
        if save_bytes_sha(before_complete) != save_bytes_sha(before_login):
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the corpus changed between the login and the completion step",
            )
        complete_envelope = build_complete_envelope()
        complete_data = collection_envelope.data_field(complete_envelope)
        complete_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": complete_data,
        }
        complete_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(complete_form),
            cookie=cookie,
            timeout=30.0,
        )
        if complete_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_complete_collection: expected HTTP 200, got %r"
                % complete_result["status"],
            )
        after_complete = canonical_save(save_path)
        complete_body = complete_result.pop("body")
        complete_note = (
            "command.php form (USERID, user_key, language, data) with the "
            "derived <64-hex>;<json> envelope carrying exactly one command: "
            "[[0,\"complete_collection\",[1,0],[0,0,0,0,0,0,0,0]]] — the "
            "collection id and the print-only `bought` flag, and NOTHING else. "
            "The client names WHICH collection; the server looks up WHAT it "
            "grants in the committed `collections` table "
            "(get_collection_prize: index = max(0, collection - 1), then "
            "json.loads(collections[index]['prize'])), so no prize, item id, "
            "quantity, or price is sent and the resources_changed is the NEUTRAL "
            "vector because a completion's price would be a client-sent delta "
            "(do_command applies it before the branch). The recorded effects are "
            "the COMMITTED prize written into map['store'] by "
            "engine.add_store_item, the id appended to "
            "privateState['collections'] by an IF-ABSENT append, and the "
            "ABSENCE of any eligibility check — the committed `item_ids` "
            "requirement list is read by no branch. user_key is redacted in this "
            "record; accessToken is the crafted empty placeholder, never a token "
            "value."
        )
        summaries.append(
            write_step(
                staging,
                "command_complete_collection",
                complete_result,
                complete_body,
                before_complete,
                after_complete,
                complete_form,
                complete_note,
            )
        )
        transaction = verify_transaction(
            before_complete, after_complete, complete_envelope
        )
        if json.loads(complete_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_complete_collection response is not the legacy "
                '{"result": "success"}: %r' % (complete_body,),
            )
        # The transaction's own leaf-level diff is the machine-checkable proof
        # that only the two intended leaves moved.  The ledger reports as the
        # CONTAINER path rather than as an appended index because a list that
        # grows differs at the list itself: `leaf_differences` walks element by
        # element only when the lengths match, so an append is reported one level
        # up.  Both observed paths are pinned here.
        if transaction["changed_leaves"] != [
            GRANTED_POINTER, LEDGER_POINTER
        ]:
            raise CaptureError(
                EXIT_REQUEST,
                "the recorded transaction must differ from its own before-state at "
                "exactly the granted storage entry and the collection ledger, got "
                "%r" % (transaction["changed_leaves"],),
            )
        print(
            "capture: complete_collection grant %r, ledger %r -> %r"
            % (
                transaction["store_after"],
                transaction["ledger_before"],
                transaction["ledger_after"],
            )
        )

        # --- the executed-legacy probes (not recorded steps) ---------------
        probe_records: List[Dict[str, Any]] = []

        probe_one_envelope = build_probe_envelope()
        probe_one_data = collection_envelope.data_field(probe_one_envelope)
        probe_one_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": probe_one_data,
        }
        before_probe_one = canonical_save(save_path)
        probe_one_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(probe_one_form),
            cookie=cookie,
            timeout=30.0,
        )
        if probe_one_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1: expected HTTP 200, got %r" % probe_one_result["status"],
            )
        probe_one_body = probe_one_result.pop("body")
        after_probe_one = canonical_save(save_path)
        probe_one_facts = verify_probe_transaction(
            before_probe_one,
            after_probe_one,
            probe_one_envelope,
            {"1085": 1},
            [FIXTURE_COLLECTION_ID],
        )
        if json.loads(probe_one_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 1 response is not the legacy success result: %r"
                % (probe_one_body,),
            )
        probe_one_record = dict(PROBES[0])
        probe_one_record.update(probe_one_facts)
        probe_records.append(probe_one_record)
        print(
            "capture: probe 1 store %r -> %r, ledger %r -> %r, xp %r -> %r"
            % (
                probe_one_facts["store_before"],
                probe_one_facts["store_after"],
                probe_one_facts["ledger_before"],
                probe_one_facts["ledger_after"],
                probe_one_facts["xp_before"],
                probe_one_facts["xp_after"],
            )
        )

        # Probe 2 completes collection 10, whose committed item_ids are absent
        # from the corpus entirely, to establish that no eligibility check runs.
        probe_two_envelope = build_probe_envelope(collection_id=10)
        probe_two_data = collection_envelope.data_field(probe_two_envelope)
        probe_two_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": probe_two_data,
        }
        before_probe_two = canonical_save(save_path)
        probe_two_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(probe_two_form),
            cookie=cookie,
            timeout=30.0,
        )
        if probe_two_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2: expected HTTP 200, got %r" % probe_two_result["status"],
            )
        probe_two_body = probe_two_result.pop("body")
        after_probe_two = canonical_save(save_path)
        probe_two_facts = verify_probe_transaction(
            before_probe_two,
            after_probe_two,
            probe_two_envelope,
            {"1056": 1},
            [FIXTURE_COLLECTION_ID, 10],
        )
        if json.loads(probe_two_body.decode("utf-8")) != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "probe 2 response is not the legacy success result: %r"
                % (probe_two_body,),
            )
        probe_two_record = dict(PROBES[1])
        probe_two_record.update(probe_two_facts)
        probe_records.append(probe_two_record)
        print(
            "capture: probe 2 store %r -> %r, ledger %r -> %r"
            % (
                probe_two_facts["store_before"],
                probe_two_facts["store_after"],
                probe_two_facts["ledger_before"],
                probe_two_facts["ledger_after"],
            )
        )

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

        resources_before = resources_of(before_login)
        resources_after = resources_of(after_complete)
        manifest = {
            "schema": "godot-unit-collection/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for a legacy "
                "complete_collection on the committed corpus's empty storage and "
                "empty collection ledger; the executed-legacy parity oracle for "
                "the Compatibility API v0 collection endpoint and the project's "
                "FIRST content-derived, server-authoritative unit acquisition."
            ),
            "invocation": "python -B apps/compat-api/capture_collection_fixture.py"
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
            "captured": {
                "completion": True,
                "stored_item_placement_chained": False,
                "note": (
                    "A complete_collection WAS captured and the stored-item "
                    "placement step was NOT CHAINED. The two together form a "
                    "committed, server-derived path by which a unit enters a "
                    "town (complete_collection -> map['store'] -> "
                    "place_stored_item), but the round trip is a SEPARATE "
                    "carried follow-up and delivering it here would widen this "
                    "line past its contract. THIS FIXTURE THEREFORE EVIDENCES A "
                    "GRANT INTO STORAGE AND NOT A UNIT PLACED ON THE MAP; the "
                    "placement count is unchanged at 40 across the whole "
                    "transaction and no map row is written"
                ),
            },
            "target": {
                "collection_id": FIXTURE_COLLECTION_ID,
                "collection_name": FIXTURE_COLLECTION_NAME,
                "committed_prize": {str(FIXTURE_PRIZE_ID): FIXTURE_PRIZE_QUANTITY},
                "committed_prize_item_name": config_name(FIXTURE_PRIZE_ID),
                "committed_prize_item_type": config_type(FIXTURE_PRIZE_ID),
                "store_before": before_login["maps"][0]["store"],
                "ledger_before": before_login["privateState"]["collections"],
                "fabricated_state": False,
                "target_rule": TARGET_RULE,
            },
            "grant": {
                "derived_from_committed_content": True,
                "derivation": (
                    "the granted id and quantity were DERIVED from the committed "
                    "collections table by get_collection_prize(collection_id) -> "
                    "json.loads(collections[max(0, collection_id - 1)]['prize']); "
                    "nothing about the grant came from the request, and the "
                    "endpoint's post-execution proof compares the persisted "
                    "storage against THAT committed bag rather than against any "
                    "client-supplied expectation"
                ),
                "committed_table": "config/main.json -> collections (10 entries)",
                "index_base": "one-based, derived-provisional",
                "index_rejected_alternative": "zero-based",
                "index_rule": collection_envelope.INDEX_RULE,
                "alias_rule": collection_envelope.ALIAS_RULE,
                "no_eligibility_check": collection_envelope.NO_ELIGIBILITY_CHECK,
                "bought_flag": collection_envelope.BOUGHT_NOTE,
                "six_unit_collections": [
                    1, 2, 3, 5, 6, 10
                ],
                "four_building_collections": [4, 7, 8, 9],
                "grant_pointer": GRANTED_POINTER,
            },
            "intent": {
                "collection_id_sent": FIXTURE_COLLECTION_ID,
                "collection_id_rule": "the collection id is the completion's ONLY "
                "meaningful argument (command.py:505); no prize, item id, "
                "quantity, price, or resource delta is accepted, and the extra "
                "keys a client might add are ignored",
                "vector_rule": "NO completion price is claimed or implemented "
                "(design D5): a completion's price would be a CLIENT-SENT delta, "
                "because do_command applies the request's per-command vector "
                "before the branch (command.py:40; engine.py:251-271) as "
                "max(current + delta, 0). The derived vector is NEUTRAL and the "
                "endpoint requires every stored resource to be UNCHANGED",
                "derived": {
                    "command": complete_envelope["commands"][0][1],
                    "args": complete_envelope["commands"][0][2],
                    "resources_changed": complete_envelope["commands"][0][3],
                    "bought_flag": collection_envelope.DERIVED_BOUGHT,
                    "bought_note": collection_envelope.BOUGHT_NOTE,
                },
                "vector_is_neutral": True,
                "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                "envelope_keys": sorted(complete_envelope),
                "commands_per_batch": 1,
                "status": "established: the branch's exact argument list, the "
                "COMMITTED prize it grants, the append-if-absent ledger rule, "
                "the ABSENCE of any eligibility check, and the resulting states "
                "of this executed transaction. DERIVED and never observed from "
                "the Flash client: that a real client sends exactly this batch, "
                "that the `bought` flag is 0, and that the derived vector is "
                "neutral. The claim is about what the legacy server does with a "
                "collection id, NEVER about what a Flash client sent, and no "
                "cost, income, cap, or experience award is claimed",
            },
            "refusals": [dict(entry) for entry in collection_envelope.REFUSALS],
            "harvester": collection_envelope.HARVESTER_RECORD,
            "acquisition": {
                "content_derived_routes": [
                    dict(entry)
                    for entry in collection_envelope.CONTENT_DERIVED_ROUTES
                ],
                "client_supplied_routes": [
                    dict(entry)
                    for entry in collection_envelope.CLIENT_SUPPLIED_ROUTES
                ],
                "client_supplied_routes_implemented": 0,
                "note": collection_envelope.ACQUISITION_NOTE,
                "not_an_acquisition_route": collection_envelope.NOT_ACQUISITION,
            },
            "probes": probe_records,
            "transaction": transaction,
            "recorded_steps": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "placement_count_before": len(before_login["maps"][0][ITEMS_FIELD]),
                "placement_count_after": len(after_complete["maps"][0][ITEMS_FIELD]),
                "store_before": before_login["maps"][0]["store"],
                "store_after": after_complete["maps"][0]["store"],
                "ledger_before": before_login["privateState"]["collections"],
                "ledger_after": after_complete["privateState"]["collections"],
                "bought_units_before": before_login["privateState"]["boughtUnits"],
                "bought_units_after": after_complete["privateState"]["boughtUnits"],
                "dead_heroes_after": after_complete["privateState"]["deadHeroes"],
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "other_rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "map_key_set_unchanged": True,
                "private_state_unchanged_except_ledger": True,
                "player_info_unchanged": True,
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) only bites when a "
                "delta would drive a balance below zero; the derived vector is the "
                "NEUTRAL all-zero vector, so no balance moves at all and the clamp "
                "is never exercised by this fixture. That the vector really is "
                "client-sent and really would move a balance through this very "
                "branch is established by probe 1 above",
                "unit_placed": False,
                "unit_note": "NO unit is placed, garrisoned, or spawned on the map "
                "by this transaction: the committed prize went into "
                "map['store'] and the placement count is unchanged. The "
                "stored-item placement step was deliberately NOT chained (design "
                "D6)",
                "xp_awarded": False,
                "xp_note": "NO experience is awarded: `collect_xp` is never read "
                "and the only command writing a placed row's attr['xp'] takes a "
                "client-sent amount, which this line refuses (design D5). The "
                "corpus's xp is unchanged at 4",
                "income_derived": False,
                "income_note": "NO income and NO payout are derived: no committed "
                "unit records a positive `collect` (0 of 429), `max_collects` is "
                "0 on every unit, and no collect field has a legacy consumer "
                "(design D5)",
                "cap_interpreted": False,
                "cap_note": "NO cap is interpreted: max_collects is 0 on all 429 "
                "units, so the cap building-collect refuses has NO unit analogue "
                "and no threshold exists to read",
                "eligibility_checked": False,
                "eligibility_note": "NO eligibility check runs, before or after "
                "execution: the committed `item_ids` requirement list is read by "
                "no branch at all, so a caller may name ANY of the ten committed "
                "collections. Recorded, not fixed (design D2); probe 2 is the "
                "executed evidence",
                "grant_writes": [
                    "engine.apply_resources applies the derived NEUTRAL vector on "
                    "the single command with max(..., 0) per resource, BEFORE the "
                    "branch (command.py:40; engine.py:251-271)",
                    "get_collection_prize reads the committed collections table "
                    "positionally and json.loads the selected row's `prize` "
                    "(get_game_config.py:170-175)",
                    "engine.add_store_item creates map['store'][str(item_id)] with "
                    "the committed quantity when the key is absent and increments "
                    "it when present (engine.py:70-75) — nothing else",
                    "complete_collection appends the collection id to "
                    "privateState['collections'] ONLY when it is absent "
                    "(command.py:517-518) — nothing else",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE and the recorded RESPONSE carry NO "
                    "time-dependent value at all: complete_collection writes only "
                    "the storage and the collection ledger, and neither touches a "
                    "clock. The only wall-clock values in this fixture are "
                    "record metadata and the envelope `ts`, listed below, so a "
                    "leaf-level diff of two consecutive runs must differ at exactly "
                    "these paths and nowhere else"
                ),
                "state_leaves": [],
                "stable_state_leaves": [
                    "steps/command_complete_collection/before.json is byte-stable",
                    "steps/command_complete_collection/after.json is byte-stable",
                    "the login step's before.json and after.json are both "
                    "byte-stable and identical to each other",
                ],
                "leaves": [
                    "/captured_at_utc in steps/login_post/request.json",
                    "/captured_at_utc in steps/login_post/response.meta.json",
                    "/captured_at_utc in steps/command_complete_collection/request.json",
                    "/captured_at_utc in steps/command_complete_collection/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in steps/login_post/response.meta.json",
                    "/headers/Date in steps/command_complete_collection/response.meta.json",
                    "the envelope ts inside the command step's request.json "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                ],
                "stable_by_derivation": (
                    "the granted id and quantity, the appended ledger id, the "
                    "placement count, and all seven stored resources are "
                    "byte-stable because the derivation is fixed: collection 1's "
                    "committed prize is {1085: 1} into an EMPTY storage, so the "
                    "grant writes exactly that entry, and the ledger is empty, so "
                    "exactly one id is appended"
                ),
                "documented_normalization": (
                    "collection parity applies NO clock normalization at all: the "
                    "granted id and quantity are compared by value against the "
                    "COMMITTED bag, the ledger is compared entry by entry, and "
                    "every stored resource is compared by value (exactly "
                    "unchanged, because the derived vector is neutral). There is "
                    "no instant in this transaction whose value is not derivable"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The twelve already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, construction, "
                    "collect, expand, level, and queue fixtures are digest-pinned "
                    "for the same reason."
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
                "capture:   %-28s %s %s -> %d (%d bytes, save unchanged: %s)"
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
            "capture: complete_collection via %s: store %r -> %r, ledger %r -> %r"
            % (
                transaction["command"],
                transaction["store_before"],
                transaction["store_after"],
                transaction["ledger_before"],
                transaction["ledger_after"],
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
        print("capture: working-tree containment identical: %s" % pre_combined)
        return 0

    except collection_envelope.EnvelopeError as error:
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
