#!/usr/bin/env python3
"""Capture the executed-legacy expand fixture: one real ``expand`` command.

What this does, in order (harness shared with the boot, placement, purchase,
move, sell, store, upgrade, construction, and collect captures):

1. Verifies the parent interpreter is CPython 3.9, the seed save exists, and
   takes the working-tree containment snapshot before anything runs — plus a
   digest snapshot of the already committed boot, placement, purchase, move,
   sell, store, upgrade, construction, and collect fixtures.
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
     ``data`` envelope carrying exactly **one** command —
     ``[0,"expand",[0],[0,0,0,0,0,0,0,0]]`` — as produced by
     :mod:`expand_envelope`

   The fixture expansion is **id 0**: the committed ``expansion_prices``
   schedule is a 98-row positional table with **no stable id**, and indexes
   ``0..3`` are all zero, so id 0 is a real committed **free** expansion and
   its derived debit is the all-zero vector.  That is the only kind of
   expansion this corpus can honestly buy: design D3 refuses any row recording
   a positive ``neighbors`` or ``inventory_qte`` requirement, and **94 of the
   98 committed rows record one — including every id the corpus itself owns**
   (``35, 36, 45, 46``, all at ``neighbors 15`` / ``inventory_qte 30``).  The
   requirement refusal is stated, not worked around; see the module docstring
   of :mod:`expand_envelope` and the fixture README.
6. Verifies the transaction structurally before publishing: the login step
   left the save byte-identical, the expansion step mutated it, the owned
   list grew by **exactly one** entry equal to the sent id **at the end** with
   the existing ``[35, 36, 45, 46]`` unchanged, in order, and **not
   deduplicated**, the placement count stays ``40`` and every row is
   byte-identical, ``level`` / ``increasedPopulation`` / ``store`` /
   ``privateState`` / ``playerInfo`` and every **other** map field (including
   ``map_sizes``, which the committed corpus does not record, so its *absence*
   is asserted by the whole-key-set check) are unchanged, and **every one of
   the seven stored resources is unchanged** because the derived debit is the
   all-zero vector.  The recorded request itself is pinned: exactly one
   command, the fixture id, and the content-derived debit.
7. Stops the server, re-checks the working-tree containment snapshot and the
   committed boot/placement/purchase/move/sell/store/upgrade/construction/
   collect fixture digests, discards the disposable copy, and writes the
   fixtures under ``--out`` (default: ``tests/fixtures/godot-building-expand/``).

Recorded requests and responses are sanitized: ``user_key`` is redacted, the
disposable server's session cookie (``Cookie`` / ``Set-Cookie``) is redacted,
and any non-empty ``accessToken`` would be redacted — the capture crafts
``accessToken=""`` (a documented placeholder, never a token value), so no
recorded field ever carries a secret.  The live requests always send the real
values; only the records are redacted, which also keeps these fields
byte-stable across reruns.

There are **no time-dependent fields in the recorded state or the recorded
response**: an expansion writes an int the client sent into a list, and the
derived debit is the all-zero vector, so ``before.json``, ``after.json``, and
``response.body`` are byte-identical across reruns.  The manifest's
``time_dependent_fields`` block says so explicitly and lists only the
record-metadata and envelope-clock leaves, so a leaf-level diff of two
consecutive runs can never silently widen.

Containment (same contract as the boot, placement, purchase, move, sell, store,
upgrade, construction, and collect captures):

* The only working-tree paths written are the fixture files under ``--out``
  (sanctioned capture output). ``saves/``, legacy sources, configs,
  villages, templates, and tests/saves are read only; any byte change there
  fails the run with exit 6 before fixtures are written. The committed boot,
  placement, purchase, move, sell, store, upgrade, construction, and collect
  fixtures are digest-pinned for the same reason.
* Everything else lives in a disposable copy that is removed before exit
  (unless ``--keep-disposable``).
* Loopback ``127.0.0.1`` only; no browser, Flash, Ruffle, ActionScript,
  or external network. The legacy command recorder env var is stripped
  from the child so the recorder can never write.
* Bytecode writing is disabled for parent and child (``-B`` plus
  ``sys.dont_write_bytecode``).

Exit codes (shared with the boot, placement, purchase, move, sell, store,
upgrade, construction, and collect capture harnesses):

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

    python -B apps/compat-api/capture_expand_fixture.py

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
import expand_envelope  # noqa: E402
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-building-expand"

# The committed legacy configuration (static content, read directly: this tool
# must not import any legacy module, because doing so would chdir into a
# corpus and initialize live legacy state).  The expansion schedule is read
# from it here and pinned against the committed constants, so a config drift
# fails the run instead of publishing a different fixture.
CONFIG_MAIN = REPO_ROOT / "config" / "main.json"

# The committed expansion schedule (config/main.json, top-level
# ``expansion_prices``): 98 positional rows with NO stable id, every row
# carrying the four fully native numbers ``coins`` / ``cash`` / ``neighbors`` /
# ``inventory_qte``.  Indexes 0..3 are all zero (the free expansions), index 4
# is 2500/5/1/1, index 5 is 5000/8/2/2, and per-field saturation starts at
# coins index 14, cash index 11, neighbors index 18, and inventory_qte index
# 33 — so the whole row equals 100000/20/15/30 from index 33 to 97.  The
# 4-entry ``town_prices`` / ``map_prices`` schedules (levels 15/25/35/45) are
# deliberately NOT used: the corpus's own [35, 36, 45, 46] is only a valid
# index into THIS table.
FIXTURE_SCHEDULE_LENGTH = 98
FIXTURE_FREE_INDEXES = (0, 1, 2, 3)
# The fixture intent: expansion id 0, a committed free row, so the derived
# debit is the all-zero vector.  See the module docstring for why no priced
# row is purchasable on this corpus under design D3.
FIXTURE_EXPANSION_ID = 0
FIXTURE_PRICE: Dict[str, int] = {
    "coins": 0,
    "cash": 0,
    "neighbors": 0,
    "inventory_qte": 0,
}
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
# The committed corpus's own owned-expansions ledger, and the ledger the
# executed transaction must produce: exactly one appended id, at the end, with
# the existing four unchanged, in order, and not deduplicated.
FIXTURE_EXPECTED_EXPANSIONS_BEFORE = [35, 36, 45, 46]
FIXTURE_EXPECTED_EXPANSIONS_AFTER = [35, 36, 45, 46, 0]
FIXTURE_EXPECTED_PLACEMENTS_BEFORE = 40
FIXTURE_EXPECTED_PLACEMENTS_AFTER = 40  # no key is added or removed
# The committed corpus's map level and the two other map scalars the executed
# probe recorded as untouched.  ``map_sizes`` is deliberately NOT pinned to a
# value: the committed corpus does not record that field at all (nor does any
# committed legacy source or the committed config), so its absence is enforced
# by the whole-key-set equality check in verify_transaction instead.
FIXTURE_EXPECTED_LEVEL = 1
FIXTURE_EXPECTED_INCREASED_POPULATION = 0
FIXTURE_EXPECTED_MAP_SIZES_PRESENT = False
# The exact resource movement the derived debit must produce, under legacy's
# ``max(current + delta, 0)`` per slot.  A zero-cost committed row derives the
# all-zero vector, so **no** resource moves and the clamp is never exercised by
# this fixture — recorded as a claim limit rather than hidden.  The clamp's
# reachability is established by probe 1 below.
FIXTURE_EXPECTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
FIXTURE_EXPECTED_RESOURCE_AFTER: Dict[str, int] = dict(
    FIXTURE_EXPECTED_RESOURCE_BEFORE
)
FIXTURE_EXPECTED_RESOURCE_DELTA: Dict[str, int] = {
    "xp": 0,
    "gold": 0,
    "wood": 0,
    "oil": 0,
    "steel": 0,
    "cash": 0,
    "mana": 0,
}
TARGET_RULE = (
    "expansion id 0 — a FREE row of the committed 98-entry positional "
    "expansion_prices schedule (indexes 0..3 all record coins 0, cash 0, "
    "neighbors 0, inventory_qte 0), so the derived debit is the all-zero "
    "vector. It is the only kind of expansion this corpus can honestly buy: "
    "design D3 refuses any row recording a positive neighbors or "
    "inventory_qte requirement, and 94 of the 98 committed rows record one — "
    "including EVERY id the corpus itself owns (35, 36, 45, 46, all at "
    "neighbors 15 and inventory_qte 30), so none of them could have been "
    "bought. The requirement refusal is stated, never worked around"
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
    ("tests/fixtures/godot-building-collect", "godot-building-collect"),
)

# The three executed-legacy probes that shaped this line.  They were run
# against the real legacy server inside a disposable copy by the recorded
# investigation (``docs/legacy-town-expansion.md`` and this change's design)
# and are recorded here so the fixture states its own evidence base rather than
# only its result.
PROBES: List[Dict[str, Any]] = [
    {
        "probe": 1,
        "question": (
            "what does the expand branch actually write, and what happens when "
            "the client-sent debit exceeds the balance?"
        ),
        "commands": [
            "expand(4) with the neutral vector [0,0,0,0,0,0,0,0]",
            "expand(5) with the expansion_prices[5] debit [0,0,-5000,0,0,0,-8,0]",
        ],
        "expansions_before": [35, 36, 45, 46],
        "expansions_after": [35, 36, 45, 46, 4, 5],
        "changed_top_level_map_keys": ["expansions", "gold"],
        "resources": "gold 2000 -> 0; playerInfo.cash 5 -> 0; xp, wood, oil, "
        "steel, mana unchanged",
        "response": '{"result":"success"} for both batches',
        "established": (
            "the branch appends and changes NOTHING else (command.py:211-216): "
            "not items, not level, not map_sizes, not increasedPopulation, not "
            "privateState, not the rest of playerInfo. The price is entirely "
            "client-sent and applied verbatim per resource as "
            "max(current + delta, 0) (engine.py:251-271)"
        ),
        "clamp_reached": (
            "the per-resource clamp finally bit, for real, for the first time "
            "in this family: a client-sent -5000 gold debit against a 2000 "
            "balance landed on 0 rather than -500, and the 5 cash against 5 "
            "cash reached 0 exactly. That is the strongest available argument "
            "for a SERVER-DERIVED price and for refusing an unaffordable "
            "expansion instead of reproducing the clamp (design D6)"
        ),
    },
    {
        "probe": 2,
        "question": (
            "can the legacy server arbitrate the expansion id space at all?"
        ),
        "commands": [
            "expand(999)",
            "expand(35) (a duplicate the corpus already owns)",
            "expand(-1)",
        ],
        "responses": "all three answered {\"result\":\"success\"}",
        "expansions_after_999": [35, 36, 45, 46, 999],
        "established": (
            "NO. The server accepts 999 (an id the 98-row committed schedule "
            "does not price), a duplicate of an owned id, and a negative id, "
            "all answering success. There is no range check, no dedup, no "
            "ordering rule, no level gate, and no requirement check; a "
            "repository-wide search finds exactly three references to "
            "map['expansions'] in the whole legacy server, all three inside "
            "the branch"
        ),
        "consequence": (
            "this is the evidence for the endpoint's TWO guards, and for the "
            "derived D1 id space: unknown_expansion_id (404) for an id the "
            "committed schedule does not price, and already_expanded (409) for "
            "an id the player's own ledger already contains. Without them a "
            "client could buy an expansion no committed row prices and could "
            "append a repeat, corrupting the only ledger this line maintains"
        ),
    },
    {
        "probe": 3,
        "question": "what happens when the expansion id is not an integer?",
        "commands": ['expand("abc")'],
        "response": "an unhandled HTTP 500 raised by int(\"abc\") inside the branch",
        "established": (
            "the branch coerces its argument with int() and does not guard it, "
            "so a non-integer id crashes the request instead of being refused"
        ),
        "consequence": (
            "this is the evidence for the endpoint's structural "
            "invalid_expansion_id (400) check: the value is refused before the "
            "dispatcher runs, so a client can never turn a malformed id into "
            "an unhandled server error"
        ),
    },
]

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

STEPS = ("login_post", "command_expand")

# Stored resource name -> index in the legacy 8-slot vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
RESOURCE_VECTOR_SLOTS = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5,
                         "cash": 6, "mana": 7}

# Every other map field the executed transaction must leave byte-identical,
# named explicitly so the pre-publish check is readable, and then enforced for
# the **whole** key set (including the fields the corpus does not record).
MAP_FIELDS_THAT_MUST_NOT_MOVE = (
    "id",
    "items",
    "level",
    "store",
    "xp",
    "gold",
    "wood",
    "oil",
    "steel",
    "currentQuestVars",
    "expirableUnitsTime",
    "idCurrentMission",
    "idCurrentTreasure",
    "increasedPopulation",
    "numTradesDone",
    "questTimes",
    "race",
    "receivedAssists",
    "resourceAlliesMarket",
    "resourcesTraded",
    "skin",
    "timestamp",
    "timestampLastChapter",
    "timestampLastTrade",
    "timestampLastTreasure",
    "world_id",
)


# --------------------------------------------------------- committed config --
def config_document() -> Dict[str, Any]:
    """The committed configuration document, or a refusal.

    Read straight from ``config/main.json`` so this tool imports no legacy
    module (see :data:`CONFIG_MAIN`).
    """
    try:
        document = json.loads(CONFIG_MAIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CaptureError(
            EXIT_ENVIRONMENT, "could not read the committed config: %s" % error
        )
    if not isinstance(document, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the committed config is not an object")
    return document


def config_expansion_schedule() -> List[Any]:
    """The committed ``expansion_prices`` schedule, or a refusal.

    Validated as a schedule with the *same* :func:`expand_envelope.schedule_length`
    rule the endpoint uses, so a malformed table fails this run rather than
    producing a different debit here and there.
    """
    schedule = config_document().get("expansion_prices")
    if expand_envelope.schedule_length(schedule) is None:
        raise CaptureError(
            EXIT_ENVIRONMENT, "the committed config has no expansion_prices schedule"
        )
    return list(schedule)  # type: ignore[arg-type]


def config_expansion_price(expansion_id: int) -> Optional[Dict[str, Any]]:
    """The committed price row for ``expansion_id``, or ``None`` out of range.

    Resolved with the *same* :func:`expand_envelope.price_for` rule the endpoint
    uses, so the request the capture sends and the debit the service derives can
    never drift apart.
    """
    try:
        return expand_envelope.price_for(
            expansion_id, config_expansion_schedule()
        )
    except expand_envelope.EnvelopeError as error:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed expansion schedule does not resolve: [%s] %s"
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
    replayed (expand parity works from the intent, not over HTTP), and
    redacting it keeps reruns byte-stable for these fields.
    """
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_data_field(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The capture crafts ``accessToken=""`` so the recorded field is the exact
    sent bytes; this keeps the record secret-free even if that placeholder ever
    changes.
    """
    envelope = expand_envelope.parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return expand_envelope.data_field(envelope)


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
    """The recorded batch: one ``expand`` carrying the content-derived debit.

    Built from the shared derivation rather than hand-written, so the captured
    request and the Compatibility API endpoint can never drift apart.  The debit
    is the derived one the endpoint would derive for this id: the id's own
    committed row in the 98-entry positional ``expansion_prices`` schedule,
    with the row's gold-named ``coins`` in the gold slot and its ``cash`` in the
    cash slot, each negated, and the six slots no expansion price names left
    zero.  For the fixture's free id 0 that is the all-zero vector.
    """
    row = config_expansion_price(FIXTURE_EXPANSION_ID)
    if row is None:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the committed expansion schedule has no row for the fixture id %d"
            % FIXTURE_EXPANSION_ID,
        )
    debit = expand_envelope.resource_vector_for(row)
    if debit != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the derived debit drifted from the pinned %r: %r"
            % (FIXTURE_EXPECTED_VECTOR, debit),
        )
    return expand_envelope.build_envelope(
        expansion_id=FIXTURE_EXPANSION_ID, vector=debit, ts=ts
    )


# -------------------------------------------------------- transaction check --
def verify_envelope(envelope: Dict[str, Any]) -> None:
    """Pin the derived envelope shape the recorded request will carry.

    The single command, its argument, and its resource vector are the derived
    contract (design D1/D2/D6); that a real client sends exactly this — and that
    the id a real client would buy and the price it would derive are the
    committed ones — is **derived** (design D1), because no legacy branch reads
    the content behind them.  All of it is pinned here against the committed
    config and fresh save instead, and any drift fails the run rather than
    silently publishing a different fixture.
    """
    if sorted(envelope) != sorted(expand_envelope.ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys %s are not the six legacy keys" % sorted(envelope),
        )
    commands = envelope["commands"]
    if len(commands) != 1:
        raise CaptureError(
            EXIT_REQUEST,
            "an expansion batch must carry exactly one command, got %d" % len(commands),
        )
    entry = commands[0]
    if entry[0] != 0:
        raise CaptureError(EXIT_REQUEST, "map id must be 0 on the command")
    if entry[1] != expand_envelope.EXPAND_COMMAND:
        raise CaptureError(
            EXIT_REQUEST,
            "the command must be %r, got %r"
            % (expand_envelope.EXPAND_COMMAND, entry[1]),
        )
    if entry[2] != [FIXTURE_EXPANSION_ID]:
        raise CaptureError(
            EXIT_REQUEST,
            "expand args must be [%d], got %r" % (FIXTURE_EXPANSION_ID, entry[2]),
        )
    if entry[3] != FIXTURE_EXPECTED_VECTOR:
        raise CaptureError(
            EXIT_REQUEST,
            "the derived debit drifted: %r (expected %r)"
            % (entry[3], FIXTURE_EXPECTED_VECTOR),
        )
    # The six slots this derivation can never fill stay zero, and the whole
    # vector is a debit: no slot may be positive.
    for index in expand_envelope.ALWAYS_ZERO_SLOTS:
        if entry[3][index] != 0:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived vector filled always-zero slot %d: %r"
                % (index, entry[3]),
            )
    paying = [index for index, value in enumerate(entry[3]) if value]
    if paying:
        raise CaptureError(
            EXIT_REQUEST,
            "the free fixture row must derive the all-zero vector, got slots %r"
            % (paying,),
        )


def verify_transaction(
    before: Dict[str, Any],
    after: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    """Structural proof that the executed save matches the derived envelope.

    Expectations are computed from the before-state and the derived debit under
    the legacy rules, in the order legacy applies them:
    ``engine.apply_resources`` (``engine.py:251-271``) runs **before** the
    branch (``command.py:40``) and applies the 8-slot vector verbatim, per
    resource, as ``max(current + delta, 0)``; ``command.expand``
    (``command.py:211-216``) then appends the id to ``map["expansions"]`` and
    writes nothing else.  Any mismatch means the capture would publish a fixture
    that contradicts its own derivation, so the run fails with exit 5.
    """
    try:
        entry = envelope["commands"][0]
        sent_id = entry[2][0]
        map_before = before["maps"][0]
        map_after = after["maps"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise CaptureError(EXIT_REQUEST, "envelope/save shape unexpected: %s" % error)

    # --- the ledger: exactly one appended id, at the end, nothing else moved.
    expansions_before = map_before["expansions"]
    expansions_after = map_after["expansions"]
    if not isinstance(expansions_before, list) or not isinstance(
        expansions_after, list
    ):
        raise CaptureError(EXIT_REQUEST, "maps[0].expansions is not a list")
    if expansions_before != FIXTURE_EXPECTED_EXPANSIONS_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "the before-state ledger is %r, not the committed %r"
            % (expansions_before, FIXTURE_EXPECTED_EXPANSIONS_BEFORE),
        )
    expected_after = list(expansions_before) + [sent_id]
    if expansions_after != expected_after:
        raise CaptureError(
            EXIT_REQUEST,
            "the owned-expansions ledger is %r after execution, not the "
            "documented %r: the sent id %r must be appended exactly once, at "
            "the end, with every existing entry unchanged and in order"
            % (expansions_after, expected_after, sent_id),
        )
    if len(expansions_after) != len(expansions_before) + 1:
        raise CaptureError(
            EXIT_REQUEST,
            "the owned-expansions ledger grew by %d entries, not exactly one"
            % (len(expansions_after) - len(expansions_before)),
        )
    # The pre-existing entries are untouched: same values, same order, and NOT
    # deduplicated (legacy neither deduplicates nor orders).
    if expansions_after[:-1] != expansions_before:
        raise CaptureError(
            EXIT_REQUEST,
            "the pre-existing ledger entries changed or were reordered: %r -> %r"
            % (expansions_before, expansions_after[:-1]),
        )
    for entry_id in expansions_before:
        if entry_id == sent_id:
            raise CaptureError(
                EXIT_REQUEST,
                "the fixture id %r was already owned; the committed ledger %r "
                "must not contain it" % (sent_id, expansions_before),
            )

    # --- the placements: none is added, removed, or changed.
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
    if sorted(items_after, key=int) != sorted(items_before, key=int):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].item keys changed; an expansion adds and removes none"
        )
    if len(items_after) != FIXTURE_EXPECTED_PLACEMENTS_AFTER:
        raise CaptureError(
            EXIT_REQUEST,
            "placement count is %d (expected %d)"
            % (len(items_after), FIXTURE_EXPECTED_PLACEMENTS_AFTER),
        )
    for other in items_before:
        if items_after[other] != items_before[other]:
            raise CaptureError(
                EXIT_REQUEST,
                "placement row %s changed; an expansion rewrites no placement "
                "at all" % other,
            )

    # --- the other map scalars the executed probe recorded as untouched.
    if map_after["level"] != FIXTURE_EXPECTED_LEVEL:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].level is %r, not the committed %r"
            % (map_after["level"], FIXTURE_EXPECTED_LEVEL),
        )
    if map_after["increasedPopulation"] != FIXTURE_EXPECTED_INCREASED_POPULATION:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].increasedPopulation is %r, not the committed %r"
            % (
                map_after["increasedPopulation"],
                FIXTURE_EXPECTED_INCREASED_POPULATION,
            ),
        )
    if map_after["store"] != map_before["store"]:
        raise CaptureError(
            EXIT_REQUEST, "maps[0].store changed; an expansion stores nothing"
        )
    if ("map_sizes" in map_after) != FIXTURE_EXPECTED_MAP_SIZES_PRESENT:
        raise CaptureError(
            EXIT_REQUEST,
            "maps[0].map_sizes presence changed (before: %s, after: %s); the "
            "committed corpus does not record the field and an expansion must "
            "never create it"
            % ("map_sizes" in map_before, "map_sizes" in map_after),
        )

    # --- the whole key set, so a field this tool does not name cannot move
    # either (this is what enforces `map_sizes` staying absent).
    if sorted(map_after) != sorted(map_before):
        raise CaptureError(
            EXIT_REQUEST,
            "the map's top-level keys changed: %r -> %r; an expansion appends "
            "one int and adds or removes nothing" % (sorted(map_before), sorted(map_after)),
        )
    for field in sorted(set(map_before) | set(map_after)):
        if field == "expansions":
            continue
        if map_after.get(field) != map_before.get(field):
            raise CaptureError(
                EXIT_REQUEST,
                "maps[0].%s changed; the branch writes only map['expansions']"
                % field,
            )
    for field in MAP_FIELDS_THAT_MUST_NOT_MOVE:
        if field in map_before and field not in map_after:
            raise CaptureError(
                EXIT_REQUEST, "maps[0].%s was removed" % field
            )

    # --- the private state and the player info.
    private_before = before["privateState"]
    private_after = after["privateState"]
    for name in sorted(set(private_before) | set(private_after)):
        if private_after.get(name) != private_before.get(name):
            raise CaptureError(
                EXIT_REQUEST,
                "privateState.%s changed; no expand branch writes it" % name,
            )
    if after["playerInfo"] != before["playerInfo"]:
        raise CaptureError(
            EXIT_REQUEST,
            "playerInfo changed; the expand branch writes none of it",
        )

    # --- the money: every stored resource must have moved by EXACTLY the
    # derived debit under legacy's max(current + delta, 0).  For a free
    # committed row that is the all-zero vector, so all seven are unchanged;
    # the value-level half of design D5's post-execution proof, asserted here
    # against the executed legacy server itself.
    total = list(entry[3])
    before_resources = resources_of(before)
    after_resources = resources_of(after)
    if before_resources != FIXTURE_EXPECTED_RESOURCE_BEFORE:
        raise CaptureError(
            EXIT_REQUEST,
            "the before-state resources %r are not the documented %r"
            % (before_resources, FIXTURE_EXPECTED_RESOURCE_BEFORE),
        )
    for name in sorted(RESOURCE_VECTOR_SLOTS):
        delta = total[RESOURCE_VECTOR_SLOTS[name]]
        if delta != FIXTURE_EXPECTED_RESOURCE_DELTA[name]:
            raise CaptureError(
                EXIT_REQUEST,
                "the derived debit for %s is %r, not the documented %r"
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


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Digest record per already-committed fixture directory."""
    return {
        label: dir_group_record(REPO_ROOT / relative, relative)
        for relative, label in PROTECTED_FIXTURES
    }


# --------------------------------------------------------------------- main --
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the executed-legacy expand fixture "
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
    staging = Path(tempfile.mkdtemp(prefix="compat-expand-capture-staging-"))
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
                "placement, purchase, move, sell, store, upgrade, construction, "
                "and collect captures send it; recorded for session fidelity — "
                "command.php performs no session validation. user_key would be "
                "redacted if present.",
            )
        )

        # --- derive the expansion envelope from the committed content -----
        before_expand = canonical_save(save_path)
        if before_expand["maps"][0]["expansions"] != FIXTURE_EXPECTED_EXPANSIONS_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's ledger is %r, not the committed %r"
                % (
                    before_expand["maps"][0]["expansions"],
                    FIXTURE_EXPECTED_EXPANSIONS_BEFORE,
                ),
            )
        if before_expand["maps"][0]["level"] != FIXTURE_EXPECTED_LEVEL:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's map level is %r, not the committed %r"
                % (before_expand["maps"][0]["level"], FIXTURE_EXPECTED_LEVEL),
            )
        if resources_of(before_expand) != FIXTURE_EXPECTED_RESOURCE_BEFORE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's resources are %r, not the committed %r"
                % (resources_of(before_expand), FIXTURE_EXPECTED_RESOURCE_BEFORE),
            )
        if before_expand["maps"][0]["store"] != {}:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fresh save's storage is not empty; the fixture assumes %r"
                % (before_expand["maps"][0]["store"],),
            )
        # The schedule is resolved from the committed configuration, never
        # hardcoded into the request; the pinned constants are only the
        # cross-check that fails the run if the committed config drifts.
        schedule = config_expansion_schedule()
        if len(schedule) != FIXTURE_SCHEDULE_LENGTH:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed expansion schedule has %d rows, not the pinned %d"
                % (len(schedule), FIXTURE_SCHEDULE_LENGTH),
            )
        resolved_price = config_expansion_price(FIXTURE_EXPANSION_ID)
        if resolved_price != FIXTURE_PRICE:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed configuration resolves expansion %d to %r, not "
                "the pinned %r"
                % (FIXTURE_EXPANSION_ID, resolved_price, FIXTURE_PRICE),
            )
        # The requirements rule the endpoint enforces, checked against the real
        # schedule here so the fixture's own row is provably purchasable: a
        # positive neighbors or inventory_qte would be refused.
        try:
            unmet = expand_envelope.unmet_requirements(resolved_price)
        except expand_envelope.EnvelopeError as error:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed expansion row does not resolve: [%s] %s"
                % (error.code, error),
            )
        if unmet:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the fixture's own committed row records %s requirements (%r); "
                "it must be a purchasable free row"
                % (unmet, resolved_price),
            )
        # The committed census the endpoint's refusals and the client readout
        # depend on, asserted against the real table rather than assumed.
        free = [
            index
            for index, row in enumerate(schedule)
            if not expand_envelope.unmet_requirements(row)
        ]
        if tuple(free) != FIXTURE_FREE_INDEXES:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed schedule's requirement-free indexes are %r, not "
                "the pinned %r" % (free, list(FIXTURE_FREE_INDEXES)),
            )
        # The corpus consequence, asserted rather than explained away: the
        # purchasable set and the free set are the SAME four indexes, so no
        # priced row is reachable on this corpus under design D3 and the
        # delivered end-to-end transaction must use a zero-cost committed row.
        zero_cost = [
            index
            for index, row in enumerate(schedule)
            if expand_envelope.resource_vector_for(row) == [0] * 8
        ]
        if zero_cost != free:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the committed schedule's zero-cost indexes %r differ from its "
                "requirement-free indexes %r; the corpus consequence this "
                "fixture depends on (only the free rows are purchasable) no "
                "longer holds" % (zero_cost, free),
            )
        envelope = build_fixture_envelope()
        verify_envelope(envelope)
        data = expand_envelope.data_field(envelope)
        expand_form = {
            "USERID": pid,
            "user_key": USER_KEY,
            "language": LANGUAGE,
            "data": data,
        }

        # --- step 2: the single-command expansion batch -------------------
        expand_result = http_request(
            LEGACY_PORT,
            "POST",
            DYNAMIC_ROOT + "/command.php",
            form=dict(expand_form),
            cookie=cookie,
            timeout=30.0,
        )
        if expand_result["status"] != 200:
            raise CaptureError(
                EXIT_REQUEST,
                "command_expand: expected HTTP 200, got %r"
                % expand_result["status"],
            )
        after_expand = canonical_save(save_path)
        if save_bytes_sha(before_expand) == save_bytes_sha(after_expand):
            raise CaptureError(
                EXIT_REQUEST,
                "command_expand did not persist any save change; refusing to "
                "publish a non-transaction fixture",
            )
        body = expand_result.pop("body")
        summaries.append(
            write_step(
                staging,
                "command_expand",
                expand_result,
                body,
                before_expand,
                after_expand,
                expand_form,
                "command.php form (USERID, user_key, language, data) with the "
                "derived <64-hex>;<json> envelope carrying exactly one command: "
                "an expand whose single argument is the expansion id and whose "
                "resources_changed is the CONTENT-DERIVED DEBIT "
                "[0, 0, 0, 0, 0, 0, 0, 0] — the id's own committed row in the "
                "98-entry positional expansion_prices schedule records coins 0 "
                "and cash 0, so both components are zero and the vector is "
                "legally all-zero; the six slots no expansion price names are "
                "zero as well. No amount, resource, price, time, or resource "
                "delta is client-supplied. The id-space indexing is DERIVED "
                "(design D1: the corpus's own [35, 36, 45, 46] is only a valid "
                "index into this table), the coins->gold naming is ESTABLISHED by "
                "the committed client assets expansion_gold.jpg and "
                "expansion_cash.jpg (design D2), and the branch's single append "
                "with the verbatim per-resource application under the "
                "max(..., 0) clamp is ESTABLISHED. user_key is redacted in this "
                "record; accessToken is the crafted empty placeholder, never a "
                "token value.",
            )
        )

        # --- structural verification of the executed transaction -----------
        verify_transaction(before_expand, after_expand, envelope)
        response_payload = json.loads(body.decode("utf-8"))
        if response_payload != {"result": "success"}:
            raise CaptureError(
                EXIT_REQUEST,
                "command_expand response is not the legacy "
                '{"result": "success"}: %r' % (response_payload,),
            )
        expansions_after = after_expand["maps"][0]["expansions"]
        resources_before = resources_of(before_expand)
        resources_after = resources_of(after_expand)

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
            "schema": "godot-building-expand/legacy-capture-v1",
            "purpose": (
                "Executed request/before/response/after fixtures for one legacy "
                "expand transaction carrying the content-derived debit; the "
                "executed-legacy parity oracle for the Compatibility API v0 "
                "expand endpoint."
            ),
            "invocation": "python -B apps/compat-api/capture_expand_fixture.py"
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
                "expansion_id": FIXTURE_EXPANSION_ID,
                "target_rule": TARGET_RULE,
                "schedule_rule": "the expansion price comes from the 98-entry "
                "positional expansion_prices schedule, indexed by the expansion "
                "id itself (design D1, DERIVED: the legacy server accepted "
                "expand(999), a duplicate, and expand(-1) alike, so it offers "
                "no evidence to arbitrate the id space; the corpus's own "
                "[35, 36, 45, 46] is only a valid index into THIS 98-row table "
                "and is neither a valid 4-entry town_prices/map_prices index nor "
                "a level set). Because the server does no range check, the "
                "endpoint answers unknown_expansion_id (404) for an id outside "
                "the table and already_expanded (409) for an id the player's "
                "own ledger already contains",
                "land_rule": "NOT APPLICABLE, and deliberately: this line is the "
                "unlock LEDGER only. No terrain, grid, cell, footprint, or "
                "placement-bound effect is derived, implemented, or claimed "
                "(design D4). The committed evidence establishes the vocabulary "
                "(the SWF symbols PopupExpandMC and btnBuyExpandTileMC plus "
                "assets/images/en/expansion.png show the client's model is a "
                "purchasable TILE bought through a popup; expansion_gold.jpg and "
                "expansion_cash.jpg show the two price components) but the "
                "committed SWF inspection is symbols-and-tags only and its own "
                "scope statement disclaims timeline semantics, script behavior, "
                "and rendering, so the tile -> cell geometry is NOT derivable "
                "from the preserved evidence. That is a known evidence gap that "
                "bounds visual land growth, and closing it needs new evidence "
                "rather than a derivation",
                "derived": {
                    "command": entry[1],
                    "args": entry[2],
                    "resources_changed": entry[3],
                    "vector_is_a_debit": True,
                    "resource_vector": "unknown, xp, gold, wood, oil, steel, cash, mana",
                    "envelope_keys": sorted(envelope),
                    "price": dict(resolved_price),  # type: ignore[arg-type]
                    "price_fields": {
                        "coins": "the client's gold, ESTABLISHED by the committed "
                        "assets expansion_gold.jpg and expansion_cash.jpg; lands "
                        "in server slot 2 (map['gold'], engine.py:259) negated",
                        "cash": "the client's cash; lands in server slot 6 "
                        "(playerInfo.cash, engine.py:267) negated",
                        "neighbors": "an UNEVALUABLE requirement; a positive value "
                        "is refused with expansion_requirements_unmet (409)",
                        "inventory_qte": "an UNEVALUABLE requirement; a positive "
                        "value is refused with expansion_requirements_unmet (409)",
                    },
                    "always_zero_slots": list(expand_envelope.ALWAYS_ZERO_SLOTS),
                    "schedule": {
                        "key": "expansion_prices",
                        "entries": len(schedule),
                        "stable_id": False,
                        "id_space": "the positional index 0..%d" % (len(schedule) - 1),
                        "fields": list(expand_envelope.COMMITTED_ROW_FIELDS),
                        "requirement_free_indexes": list(free),
                        "zero_cost_indexes": [
                            index
                            for index, row in enumerate(schedule)
                            if expand_envelope.resource_vector_for(row) == [0] * 8
                        ],
                        "rows_recording_a_requirement": len(schedule) - len(free),
                        "cheapest_non_zero": expand_envelope.row_snapshot(
                            schedule[4]
                        ),
                        "saturated_row": expand_envelope.row_snapshot(
                            schedule[-1]
                        ),
                        "first_index_whose_row_equals_the_last_row": next(
                            index
                            for index, row in enumerate(schedule)
                            if dict(row) == dict(schedule[-1])
                        ),
                        "field_saturation_first_index": {
                            field: next(
                                index
                                for index, row in enumerate(schedule)
                                if row.get(field) == schedule[-1].get(field)
                            )
                            for field in expand_envelope.COMMITTED_ROW_FIELDS
                        },
                        "unused_schedules": {
                            "town_prices": 4,
                            "map_prices": 4,
                            "note": "both carry levels 15/25/35/45 and are "
                            "deliberately NOT used by this line",
                        },
                    },
                    "decisions": {
                        "D1_id_space": "the price comes from expansion_prices, "
                        "indexed by the expansion id ITSELF. DERIVED. Supporting "
                        "evidence: the corpus's own [35, 36, 45, 46] is a valid "
                        "index into the 98-entry table and is NOT a valid index "
                        "into the 4-entry town_prices/map_prices schedules nor a "
                        "level set (36 and 46 are not levels). The executed probe "
                        "is exactly why it is derived: the server accepted "
                        "expand(999), a duplicate expand(35), and expand(-1), all "
                        "answering success, so the id space cannot be settled by "
                        "observing the server. Two consequences are carried: a "
                        "level-1 fresh player owning four saturated-price "
                        "(coins 100000) expansions is not a coherent game state, "
                        "which is recorded as a reason to distrust the reading and "
                        "bounds the claim to 'the price the committed table "
                        "assigns to the id'; and because the server does not "
                        "range-check, an id outside the schedule is REFUSED "
                        "(unknown_expansion_id 404) and an owned id is REFUSED "
                        "(already_expanded 409). Rejected alternatives: indexing "
                        "the four-entry schedules by level, and indexing by "
                        "len(map['expansions'])",
                        "D2_gold_naming": "the schedule's gold-named 'coins' field "
                        "is the client's 'gold' and lands in server slot 2, with "
                        "'cash' landing in slot 6. ESTABLISHED BY COMMITTED ASSET "
                        "EVIDENCE: assets/images/en/expansion_gold.jpg and "
                        "expansion_cash.jpg are two distinct committed images — "
                        "the expansion popup's two price components — and the "
                        "client's own icon for one of them is named gold. Note the "
                        "config's two resource namings: items[].costs uses the "
                        "letter set (g/c/w/o/s) while the price schedules use the "
                        "word set (coins/cash), so a word key is a second naming "
                        "layer and the committed asset name is the bridge, not an "
                        "inference. Rejected alternative: reading 'coins' as an "
                        "unlabelled resource and guessing its slot",
                        "D3_requirements": "a row recording a POSITIVE 'neighbors' "
                        "or 'inventory_qte' fails closed with "
                        "expansion_requirements_unmet (409); nothing the delivered "
                        "stack can read (no neighbour count, no inventory quantity "
                        "in the bootstrap, the GameApi, or the corpus) evaluates "
                        "either, and the legacy server ignores both. DERIVED. "
                        "Rejected alternatives: enforcing a neighbour count or an "
                        "inventory quantity from state nothing delivers, and "
                        "ignoring the requirement. CONSEQUENCE, stated not hidden: "
                        "94 of the 98 committed rows record a positive requirement "
                        "— including EVERY id the corpus owns (35, 36, 45, 46, all "
                        "at neighbors 15 / inventory_qte 30), so none of them could "
                        "have been bought and the only purchasable entries in the "
                        "whole schedule are the free indexes 0..3. The line "
                        "therefore delivers a real ZERO-COST expansion on this "
                        "corpus and refuses the priced ones, which is correct under "
                        "the evidence and wrong for gameplay",
                        "D4_land_gap": "this change delivers the unlock LEDGER and "
                        "nothing about land. NOT IMPLEMENTED and NOT CLAIMED: no "
                        "terrain growth, no grid enlargement, no new buildable "
                        "cells, and no change to the placement bounds the delivered "
                        "placement line enforces. The committed evidence "
                        "establishes the vocabulary (a purchasable TILE bought "
                        "through a popup, priced in gold and cash) but NOT the "
                        "tile -> cell geometry, because the committed SWF "
                        "inspection is symbols-and-tags only and its own scope "
                        "statement disclaims timeline semantics, script behavior, "
                        "and rendering. A known evidence gap that bounds visual "
                        "land growth; closing it requires new evidence (an "
                        "extracted geometry table, a rendered reference, or an "
                        "authoritative spec), not a derivation",
                        "D5_intent_and_proof": "the request carries only the save "
                        "id and the expansion id; the price, the debit, the "
                        "requirement check, and the time are the service's own. "
                        "After execution the endpoint requires BOTH that the owned "
                        "list grew by exactly one entry equal to the sent id AT THE "
                        "END with every existing entry unchanged and in order and "
                        "never reordered or deduplicated, AND that every stored "
                        "resource changed by EXACTLY the derived debit; any other "
                        "outcome fails closed with internal_error rather than "
                        "reporting the legacy success. The second half is the first "
                        "endpoint's value-level proof to exist specifically to catch "
                        "a wrong SERVER-DERIVED price, which would otherwise mint "
                        "or burn the wrong amount",
                        "D6_affordability": "a balance that does not cover the "
                        "server-derived debit fails closed with "
                        "insufficient_resources (409) BEFORE execution. DERIVED. "
                        "Rejected alternative: reproducing legacy's per-resource "
                        "max(current + delta, 0) clamp, whose reachability is "
                        "established by the executed probe (a client-sent -5000 "
                        "gold debit against a 2000 balance landed on 0, not "
                        "-500). Because the debit here is server-derived, the "
                        "endpoint can know whether the balance covers it, and "
                        "silently under-charging would make the post-state proof "
                        "ambiguous — a balance that moved by less than the derived "
                        "debit is indistinguishable from a wrong derivation",
                    },
                    "status": "established: the command's argument shape and its "
                    "single effect (map['expansions'] += [int(expansion)], "
                    "command.py:211-216), that the price is the client-sent 8-slot "
                    "vector applied verbatim per resource as max(current + delta, "
                    "0) and applied BEFORE the branch (command.py:40, "
                    "engine.py:251-271), that the clamp is REACHABLE, that the "
                    "server accepts an out-of-range id, a duplicate, and a negative "
                    "id, that a non-integer id raises an unhandled server error, "
                    "the committed expansion_prices / town_prices / map_prices "
                    "schedules and their census, the committed client asset names "
                    "that settle coins->gold, and the resulting state of this "
                    "executed transaction. DERIVED and never observed from the "
                    "Flash client: D1 (the id-space indexing), D3 (the "
                    "requirements refusal), D4 (the land gap boundary), and D6 "
                    "(the affordability refusal) together with the debit's sign "
                    "and shape. The claim is that a debit is derived from the "
                    "committed schedule row the id names, NEVER that it is the "
                    "price a coherent player pays",
                },
            },
            "probes": PROBES,
            "transaction": {
                "count": len(summaries),
                "steps": summaries,
                "response_body": '{"result": "success"}',
                "expansions_before": list(FIXTURE_EXPECTED_EXPANSIONS_BEFORE),
                "expansions_after": list(expansions_after),
                "expansion_id_sent": FIXTURE_EXPANSION_ID,
                "ledger_grew_by": len(expansions_after)
                - len(FIXTURE_EXPECTED_EXPANSIONS_BEFORE),
                "existing_entries_unchanged": expansions_after[:-1]
                == FIXTURE_EXPECTED_EXPANSIONS_BEFORE,
                "existing_entries_reordered": False,
                "deduplicated": False,
                "placement_count_before": len(before_expand["maps"][0]["items"]),
                "placement_count_after": len(after_expand["maps"][0]["items"]),
                "map_level_before": before_expand["maps"][0]["level"],
                "map_level_after": after_expand["maps"][0]["level"],
                "map_sizes_present_before": "map_sizes" in before_expand["maps"][0],
                "map_sizes_present_after": "map_sizes" in after_expand["maps"][0],
                "increased_population_before": before_expand["maps"][0][
                    "increasedPopulation"
                ],
                "increased_population_after": after_expand["maps"][0][
                    "increasedPopulation"
                ],
                "store_after": after_expand["maps"][0]["store"],
                "bought_units_before": before_expand["privateState"]["boughtUnits"],
                "bought_units_after": after_expand["privateState"]["boughtUnits"],
                "dead_heroes_after": after_expand["privateState"]["deadHeroes"],
                "resources_before": resources_before,
                "resources_after": resources_after,
                "resource_delta": {
                    name: resources_after[name] - resources_before[name]
                    for name in sorted(resources_before)
                },
                "other_rows_unchanged": True,
                "other_map_fields_unchanged": True,
                "map_key_set_unchanged": True,
                "private_state_unchanged": True,
                "player_info_unchanged": True,
                "clamp_exercised": False,
                "clamp_note": "legacy's max(current + delta, 0) only bites when a "
                "delta would drive a balance below zero; the fixture's committed "
                "row is FREE, so the derived debit is the all-zero vector and no "
                "balance moves at all. The clamp's REACHABILITY is established by "
                "probe 1 above (a client-sent -5000 gold debit against a 2000 "
                "balance landed on 0), and it is exactly what design D6's "
                "insufficient_resources refusal exists to avoid reproducing",
                "requirements_rule_enforced": True,
                "requirements_note": "the endpoint refuses a row recording a "
                "positive neighbors or inventory_qte with "
                "expansion_requirements_unmet (409). The fixture's own committed "
                "row records 0 for both, so it is purchasable; the 94 rows that "
                "do record a requirement — including every id the corpus owns — "
                "are not, and that is stated rather than worked around",
                "land_effect": False,
                "land_note": "NOT claimed and NOT implemented: no land, grid, "
                "cell, footprint, or placement-bound effect (design D4). This "
                "fixture establishes the unlock ledger only: an int appended to "
                "a list",
                "expand_writes": [
                    "engine.apply_resources applies the derived debit on the single "
                    "command with max(..., 0) per resource, BEFORE the branch "
                    "(command.py:40; engine.py:251-271)",
                    "command.expand appends int(args[0]) to map['expansions'] and "
                    "writes NOTHING else (command.py:211-216)",
                    "no branch reads, validates, prices, orders, or deduplicates "
                    "map['expansions'] — a repository-wide search finds exactly "
                    "three references to the word in the whole legacy server, all "
                    "three inside the branch",
                ],
            },
            "time_dependent_fields": {
                "rule": (
                    "the recorded STATE and the recorded RESPONSE carry NO "
                    "time-dependent leaf at all: an expansion writes an int the "
                    "client sent into a list and the derived debit is the "
                    "all-zero vector, so steps/*/before.json, steps/*/after.json, "
                    "and steps/*/response.body are byte-identical across reruns. "
                    "The leaves below are the whole record-metadata and "
                    "envelope-clock surface, and the claim is machine-checkable: a "
                    "leaf-level diff of two consecutive runs must differ at "
                    "exactly these 8 paths and nowhere else"
                ),
                "state_leaves": [],
                "leaves": [
                    "/captured_at_utc in steps/login_post/request.json",
                    "/captured_at_utc in steps/login_post/response.meta.json",
                    "/captured_at_utc in steps/command_expand/request.json",
                    "/captured_at_utc in steps/command_expand/response.meta.json",
                    "/executed_at_utc in capture-manifest.json",
                    "/headers/Date in steps/login_post/response.meta.json",
                    "/headers/Date in steps/command_expand/response.meta.json",
                    "the envelope ts inside steps/command_expand/request.json's "
                    "/form/data (and therefore that whole field's string, because "
                    "the digest covers the payload), since ts is the current time",
                ],
                "stable_by_derivation": (
                    "the ledger, every resource, and every other map field are "
                    "byte-stable because the derivation is fixed: the fixture id 0 "
                    "is a committed free row, so the debit is always the all-zero "
                    "vector [0, 0, 0, 0, 0, 0, 0, 0] and the committed ledger is "
                    "always [35, 36, 45, 46], making /transaction/expansions_after, "
                    "/transaction/resources_after, /transaction/resource_delta, "
                    "/transaction/save_after_sha256, and every leaf of the two "
                    "save documents stable. There is no wall-clock reading anywhere "
                    "in the recorded state — this is the first delivered fixture in "
                    "the family with no time-dependent state leaf at all"
                ),
                "documented_normalization": (
                    "expand parity applies NO clock normalization: the owned list "
                    "is compared by value (exactly the sent id appended at the end) "
                    "and every stored resource by value (exactly the derived "
                    "debit), because neither carries a clock reading. The only "
                    "clock in the transaction is the envelope ts, which legacy "
                    "parses and never reads, and the legacy branch writes no clock "
                    "of its own — unlike collect's item[3] = time_now()"
                ),
            },
            "containment": {
                "method": (
                    "SHA-256 snapshot of every read working-tree group before the "
                    "run and after the server stopped; equal or the run fails "
                    "before writing fixtures. The already committed boot, "
                    "placement, purchase, move, sell, store, upgrade, construction, "
                    "and collect fixtures are digest-pinned for the same reason."
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
            "capture: derived command %s%s with resources %s (a DEBIT: the "
            "committed row is coins 0 / cash 0)"
            % (entry[1], entry[2], entry[3])
        )
        print(
            "capture: ledger %r -> %r (grew by exactly %d appended id at the "
            "end, existing entries unchanged, in order, not deduplicated)"
            % (
                FIXTURE_EXPECTED_EXPANSIONS_BEFORE,
                expansions_after,
                len(expansions_after) - len(FIXTURE_EXPECTED_EXPANSIONS_BEFORE),
            )
        )
        print(
            "capture: placements %d -> %d, level %r, increasedPopulation %r, "
            "map_sizes present %s, store %r, boughtUnits %r -> %r, deadHeroes %r"
            % (
                len(before_expand["maps"][0]["items"]),
                len(after_expand["maps"][0]["items"]),
                after_expand["maps"][0]["level"],
                after_expand["maps"][0]["increasedPopulation"],
                "map_sizes" in after_expand["maps"][0],
                after_expand["maps"][0]["store"],
                before_expand["privateState"]["boughtUnits"],
                after_expand["privateState"]["boughtUnits"],
                after_expand["privateState"]["deadHeroes"],
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

    except expand_envelope.EnvelopeError as error:
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
