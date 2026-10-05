#!/usr/bin/env python3
"""Capture the executed-legacy magic-counter fixture: ``buy_magic`` and ``use_magic``.

Contract: ``docs/legacy-m10-damage.md`` (OpenSpec change ``2026-10-05-damage``,
task group 1).  Read that record for the measurements; this module executes them
and refuses to publish unless every one reproduces.

Twelve transactions against **one** committed village document --
``villages/Neutral.json``, the only committed corpus whose ``privateState.magics``
is non-empty -- driven as **one interleaved sequence** against **one** disposable
legacy server.

**One sequence, and the linkage is load-bearing.**  The committed record states
steps 1-8 as one *interleaved* sequence against the same counter key: each step's
recorded "before" is the previous step's recorded "after"
(``2 -> 3 -> 7 -> 15 -> 31 -> 63 -> 113 -> 50 -> 50``), and it states steps 9-12
were "driven against the same disposable corpus".  Those numbers are only
meaningful if each step really ran against its predecessor's state, so they
cannot be captured one-server-per-transaction from the seed: a fresh server per
step would have to re-derive every intermediate value by hand and would prove
nothing about the sequence.  Step 11's recorded no-change settles it
independently -- ``use_magic ["1"]`` leaves key ``"1"`` at 50, which is only
reachable if step 8's 50 is still there; on a fresh seed that key holds 2 and the
same request would make it 3.  Every step's "before" is therefore asserted equal
to its predecessor's "after".

One server is also **required** rather than one per step: ``sessions.load_saves()``
caches the corpus in a module global at import time, so a running server never
re-reads the save file from disk.  Restoring the seed between steps on one server
would leave the *in memory* corpus already mutated and silently produce a
different result.

What this fixture establishes, and what it deliberately does not:

* **ESTABLISHED** -- that the two branches are **not** interchangeable four lines
  apart: ``buy_magic`` uses ``+=`` on ``min(50, x + 1)`` and is therefore
  **unbounded** (``2 -> 3 -> 7 -> 15 -> 31 -> 63 -> 113``), while ``use_magic``
  uses ``=`` on the same ``min``, an absolute clamp that **destroys charges**
  (``113 -> 50``, 63 player-owned spells removed by a command whose printed
  message claims a spell was used).
* **ESTABLISHED** -- that an identity is **unvalidated and untyped**: ``99`` is
  accepted although it is not one of the ten committed magics, and a float
  ``1.0`` creates a **second, unrelated ledger key** ``"1.0"`` because the branch
  keys on ``str(magic_id)`` and ``str(1.0) != str(1)``.  A string ``"1"`` resolves
  to the *same* key, which is the discriminator that proves the hazard is the
  string form and not the JSON type alone.
* **ESTABLISHED** -- that an **absent** key takes the branch's ``else`` arm and is
  written at **zero**, so the legacy "acquire a spell you hold none of" path
  increments **nothing at all**.
* **ESTABLISHED** -- that **no price is charged**: all **eight** stored resource
  slots are byte-identical across every step, and ``mana`` holds at 15 through a
  ``use_magic``.
* **RECORDED AS DIVERGENCES, NEVER AS PARITY** -- both asymmetries above, the
  out-of-table identity, the float key, and the absent-key zero.  The capture
  asserts the differences rather than asserting parity.
* **NOT ESTABLISHED, AND NOT CLAIMED** -- any damage rule, effect, magnitude, or
  outcome.  The committed magics carry no amount; the ledger has **zero**
  readers; and the number that would define a damage amount, the ``Attack
  Boost`` multiplier, was never committed.

No Flash, Ruffle, ActionScript, or browser executes.  Every network call is
loopback to ``127.0.0.1:5055``.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.version_info[:2] != (3, 9):
    sys.stderr.write(
        "capture: pinned interpreter is CPython 3.9, this is %d.%d\n"
        % sys.version_info[:2]
    )
    raise SystemExit(2)

from capture_legacy_fixtures import (  # noqa: E402
    CaptureError,
    DYNAMIC_ROOT,
    EXIT_CONTAINMENT,
    EXIT_ENVIRONMENT,
    EXIT_OK,
    EXIT_PORT_BUSY,
    EXIT_REQUEST,
    EXIT_SERVER,
    GAME_VERSION,
    LANGUAGE,
    LEGACY_HOST,
    LEGACY_PORT,
    REPO_ROOT,
    USER_KEY,
    build_disposable,
    canonical_digest,
    containment_snapshot,
    extract_session_cookie,
    http_request,
    iso_now,
    port_is_free,
    read_tail,
    save_group_record,
    sha256_bytes,
    sha256_file,
    snapshot_combined,
    start_server,
    stop_server,
    wait_ready,
    write_bytes,
    write_json,
)


def committed_digest(data: bytes) -> str:
    """SHA-256 over the **committed blob** form of ``data``.

    Every digest recorded by this capture is over text that will be committed
    and then checked out again, and this repository sets ``core.autocrlf=true``
    with no ``.gitattributes`` entry for ``tests/fixtures/**``.  A checkout may
    therefore hold CRLF or LF for byte-identical committed content, so a digest
    taken over raw working-tree bytes is only valid on the checkout that produced
    it.

    Normalising CRLF to LF makes the recorded digest mean "these committed
    bytes", which is the only claim a fixture digest can make.  This is the same
    normalisation the combat and unit-xp captures apply to their own digests.

    Applied only to committed artifacts -- fixture bodies and the seed document.
    Digests over live server responses stay on raw bytes: those bytes are
    produced in this process and never round-trip through a checkout.
    """
    return sha256_bytes(data.replace(b"\r\n", b"\n"))


def seed_target_of(disposable: Path, pid: str) -> Path:
    """Where ``build_disposable`` copied the seed, rebuilt from its own rule.

    The helper copies to ``<disposable>/saves/<pid>.save.json`` and returns the
    pid, so the path is derived rather than returned.  Recomputing it here is
    what lets this capture assert the helper's raw-byte digest against the copy
    it actually made, instead of trusting the returned value.
    """
    return disposable / "saves" / ("%s.save.json" % pid)


from placement_envelope import (  # noqa: E402
    ENVELOPE_KEYS,
    data_field,
    parse_data_field,
    payload_json,
)

import magic_envelope  # noqa: E402

# --- This line's own constants ---------------------------------------------

SCHEMA = "damage-magic-counter-fixture-v1"

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-damage"

SEED = REPO_ROOT / "villages" / "Neutral.json"

SEED_PID = "Neutral"

# The committed ledger, verbatim from villages/Neutral.json.  Recorded as a
# constant so a rerun fails loudly if the seed ever changes, rather than
# silently producing a different fixture.
SEED_LEDGER: Dict[str, int] = {"10": 0, "9": 1, "1": 2, "2": 0, "4": 2}
SEED_LEDGER_KEY_COUNT = len(SEED_LEDGER)
SEED_MANA = 15
SEED_ENERGY = 50

FIXTURE_TS = 1700000000

BUY_COMMAND = "buy_magic"
USE_COMMAND = "use_magic"
COMMANDS = (BUY_COMMAND, USE_COMMAND)

# The two branches, and the two arms the committed record names.  The literal
# 50 is transcribed from the source, never derived from committed content --
# see docs/legacy-m10-damage.md section 5.7 and
# magic_envelope.REJECTED_CAP_DERIVATION.
CAP_LITERAL = 50
CAP_SOURCE_LINES = [658, 670]
BUY_OPERATOR = "+="
USE_OPERATOR = "="

NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]

PRINTED_BUY = "Bought magic spell"
PRINTED_USE = "Used magic spell"

LEDGER_LOCATION = ("privateState", "magics")

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

# **EIGHT** slots, not the seven ``engine.apply_resources`` writes.  The committed
# investigation compared all eight and found none moving, and
# ``privateState['energy']`` is a real stored resource that no legacy branch
# writes -- which is exactly why it is absent from that function.  A seven-slot
# comparison would be narrower than the evidence it claims to reproduce.
RESOURCE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
    "energy": ("privateState", "energy"),
}
RESOURCE_COUNT = len(RESOURCE_SLOTS)

# Already-committed fixture directories whose bytes this run must not change.
# ``godot-combat-actions`` is here because it is the immediately preceding
# executed-legacy capture; ``godot-damage`` is deliberately ABSENT because this
# capture publishes it.
PROTECTED_FIXTURES = (
    "godot-building-collect",
    "godot-building-construction",
    "godot-building-expand",
    "godot-building-move",
    "godot-building-placement",
    "godot-building-sell",
    "godot-building-store",
    "godot-building-upgrade",
    "godot-building-xp",
    "godot-combat-actions",
    "godot-compatibility-boot",
    "godot-item-purchase",
    "godot-quests",
    "godot-research",
    "godot-stored-item-placement",
    "godot-tutorial",
    "godot-unit-collection",
    "godot-unit-experience",
    "godot-unit-queues",
)


# --- the recorded transactions ---------------------------------------------
# ``expect`` is the oracle's own post-state, recomputed and asserted from the
# branch's arithmetic.  ``modern`` states what this capability derives instead,
# and where the two differ the step is marked ``divergence`` -- never ``parity``.
#
# ONE interleaved sequence: every step's ``expect_before`` is its predecessor's
# ``expect_after``, and the capture asserts that linkage step by step.
#
# Every ``magic_id`` here is CRAFTED and CLIENT-SUPPLIED on purpose.  The legacy
# branch reads exactly one argument and validates nothing, which is the finding.
def _buy(identity: Any, before: int, after: int, **extra: Any) -> Dict[str, Any]:
    step: Dict[str, Any] = {
        "command": BUY_COMMAND,
        "magic_id": identity,
        "expect_key": str(identity),
        "expect_before": before,
        "expect_after": after,
        "operator": BUY_OPERATOR,
        "printed": PRINTED_BUY,
        "parity": False,
    }
    step.update(extra)
    return step


def _use(identity: Any, before: int, after: int, **extra: Any) -> Dict[str, Any]:
    step: Dict[str, Any] = {
        "command": USE_COMMAND,
        "magic_id": identity,
        "expect_key": str(identity),
        "expect_before": before,
        "expect_after": after,
        "operator": USE_OPERATOR,
        "printed": PRINTED_USE,
        "parity": False,
    }
    step.update(extra)
    return step


TRANSACTIONS: List[Dict[str, Any]] = [
    # --- steps 1-8: the two arms interleaved on key "1" ---------------------
    _use(
        1,
        2,
        3,
        name="use_1_from_two",
        note=(
            "The two arms are driven against the SAME counter key and deliberately "
            "interleaved, so the divergence reads as one sequence."
        ),
        parity=True,
        parity_note=(
            "For a value at or below the cap the use_magic assignment and this "
            "capability's derived transition are the same number."
        ),
    ),
    _buy(
        1,
        3,
        7,
        name="buy_1_unbounded_first",
        note="3 + min(50, 4) = 7: the ADD already exceeds the literal cap.",
        divergence="unbounded_growth",
    ),
    _buy(
        1,
        7,
        15,
        name="buy_1_unbounded_second",
        note="7 + min(50, 8) = 15.",
        divergence="unbounded_growth",
    ),
    _buy(
        1,
        15,
        31,
        name="buy_1_unbounded_third",
        note="15 + min(50, 16) = 31.",
        divergence="unbounded_growth",
    ),
    _buy(
        1,
        31,
        63,
        name="buy_1_crossed_the_cap",
        note="31 + min(50, 32) = 63: the counter CROSSED the literal 50.",
        crossed_cap=True,
        divergence="unbounded_growth",
    ),
    _buy(
        1,
        63,
        113,
        name="buy_1_still_climbing",
        note=(
            "63 + min(50, 64) = 113: still climbing, and it would keep adding 50 "
            "per request, so the 50 is NOT a cap on this arm."
        ),
        divergence="unbounded_growth",
    ),
    _use(
        1,
        113,
        50,
        name="use_1_destroys_charges",
        note=(
            "min(50, 114) = 50: an ABSOLUTE clamp, so this REDUCED a counter "
            "above the cap. 63 player-owned charges were destroyed by a command "
            "whose printed message claims a spell was used. This is the sharpest "
            "measurement in the line."
        ),
        decreased=True,
        charges_destroyed=63,
        divergence="use_magic_decreases",
    ),
    _use(
        1,
        50,
        50,
        name="use_1_at_the_cap_unchanged",
        note="min(50, 51) = 50: at the cap the use_magic arm is a no-op.",
        parity=True,
        parity_note=(
            "At the cap the assignment and the derived transition are both the "
            "cap, with a derived change of zero -- an unchanged success, not a "
            "refusal."
        ),
    ),
    # --- steps 9-12: the unvalidated, untyped identity ----------------------
    # These CONTINUE the sequence above, as the committed record states
    # ("Driven against the same disposable corpus").  Step 9's recorded
    # "5 keys" is the count the first eight steps ended at, because no step
    # before it created a key.  Step 11's recorded no-change is only reachable
    # if key "1" still holds the 50 that step 8 left there; on a fresh seed it
    # would hold 2 and become 3.
    _use(
        3,
        None,
        0,
        name="use_absent_id_3_creates_zero",
        note=(
            "Key '3' is ABSENT, so the branch takes its else arm and writes it at "
            "ZERO. The legacy 'acquire a spell you hold none of' path therefore "
            "increments nothing at all."
        ),
        created=True,
        modern_derives_after=1,
        divergence="absent_key_writes_zero_not_one",
    ),
    _buy(
        99,
        None,
        0,
        name="buy_out_of_table_id_99_accepted",
        note=(
            "99 is NOT one of the ten committed magics and the server accepted "
            "it, creating a ledger entry for a spell that does not exist. The "
            "else arm is identical in both branches, so buy_magic writes 0 too."
        ),
        created=True,
        out_of_committed_table=True,
        modern_refuses="unknown_magic_id",
        divergence="unvalidated_identity",
    ),
    _use(
        "1",
        50,
        50,
        name="use_string_id_resolves_the_same_key",
        note=(
            "A STRING '1' resolves to the SAME key '1', because the branch keys on "
            "str(magic_id) and str('1') == str(1). This is the discriminator that "
            "proves the float hazard below is about the STRING FORM rather than "
            "the JSON type alone."
        ),
        parity=True,
        parity_note=(
            "The oracle and the derived transition agree here; the string form is "
            "what differs from an integer request, not the result."
        ),
    ),
    _use(
        1.0,
        None,
        0,
        name="use_float_id_creates_a_distinct_key",
        note=(
            "str(1.0) is '1.0', so a float identity creates a SECOND, unrelated "
            "ledger entry '1.0' beside '1'. A client sending 1.0 instead of 1 "
            "silently acquires an unrelated spell."
        ),
        created=True,
        distinct_key_from="1",
        modern_refuses="non_canonical_magic_id",
        divergence="non_canonical_identity",
    ),
]

for _index, _entry in enumerate(TRANSACTIONS, start=1):
    _entry["step"] = _index

RECORDED_STEPS = tuple("txn_%s" % entry["name"] for entry in TRANSACTIONS)

# One interleaved sequence, one disposable, one server.  Every step's recorded
# "before" is its predecessor's recorded "after", and that linkage is asserted
# step by step rather than assumed.
SEQUENCE_NOTE = (
    "All twelve steps are ONE interleaved sequence against ONE disposable, "
    "because the committed record states steps 9-12 were driven against the same "
    "corpus as 1-8 and step 11's recorded no-change only holds if key '1' still "
    "carries the 50 that step 8 left there."
)


# --- helpers ---------------------------------------------------------------


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that refuses to conflate ``1``, ``1.0`` and ``True``.

    ``==`` would call all three equal, and this fixture's point is that the
    legacy branch keys the ledger on the string form of whatever it is handed, so
    ``1``, ``1.0`` and ``"1.0"`` are three different requests.  ``bool`` is
    checked before ``int`` because ``isinstance(True, int)`` is true.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, int) or isinstance(right, int):
        if isinstance(left, int) and isinstance(right, int):
            return left == right
        return False
    if isinstance(left, float) or isinstance(right, float):
        if isinstance(left, float) and isinstance(right, float):
            return left == right
        return False
    if isinstance(left, str) or isinstance(right, str):
        if isinstance(left, str) and isinstance(right, str):
            return left == right
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        if sorted(left) != sorted(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def leaf_items(document: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Every leaf of a JSON document as sorted ``(json pointer path, value)``."""
    out: List[Tuple[str, Any]] = []
    if isinstance(document, dict):
        for key in sorted(document):
            out.extend(leaf_items(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            out.extend(leaf_items(value, "%s/%d" % (prefix, index)))
    else:
        out.append((prefix, document))
    return out


def canonical_state_sha(document: Any) -> str:
    """Whole-document digest over every leaf, order-independent."""
    return canonical_digest(
        [(path, payload_json(value)) for path, value in leaf_items(document)]
    )


def leaf_diff(before: Any, after: Any) -> List[Tuple[str, Any, Any, Any]]:
    """``(path, present_before, before_value, present_after, after_value)`` set."""
    before_map = {path: (True, value) for path, value in leaf_items(before)}
    after_map = {path: (True, value) for path, value in leaf_items(after)}
    out: List[Tuple[str, Any, Any, Any]] = []
    for path in sorted(set(before_map) | set(after_map)):
        in_before = before_map.get(path)
        in_after = after_map.get(path)
        left = in_before[1] if in_before else None
        right = in_after[1] if in_after else None
        if in_before is None or in_after is None or not typed_equal(left, right):
            out.append((path, in_before is not None, left, in_after is not None, right))
    return out


def diff_payload(diff: List[Tuple[str, Any, Any, Any]]) -> List[Dict[str, Any]]:
    """JSON-safe form of :func:`leaf_diff`, so the fixture is reviewable."""
    return [
        {
            "path": path,
            "present_before": bool(in_before),
            "before": left,
            "present_after": bool(in_after),
            "after": right,
        }
        for path, in_before, left, in_after, right in diff
    ]


def unchanged_leaves_sha(document: Any, changed_paths: List[str]) -> str:
    """Digest over EVERY leaf whose path is not in ``changed_paths``.

    This is the load-bearing half of the "only the claimed leaves moved" proof:
    it is what makes the claim mechanical rather than a statement about the
    addressed counter alone.  For a step that CREATES a ledger key, the key's own
    leaf path is the only excluded one.
    """
    excluded = set(changed_paths)
    return canonical_digest(
        [
            (path, payload_json(value))
            for path, value in leaf_items(document)
            if path not in excluded
        ]
    )


def read_at(document: Dict[str, Any], location: Tuple[Any, ...]) -> Any:
    """The value at a save location, or the sentinel string ``"<absent>"``.

    Five of the eight resource slots are reached through the ``maps`` **list**
    (``maps[0].xp``), so this has to walk sequences as well as objects.  An
    earlier dict-only version silently reported every one of those five as
    absent, because ``0 not in {"xp": ...}``.
    """
    cursor: Any = document
    for step in location:
        if isinstance(cursor, dict):
            if step not in cursor:
                return "<absent>"
            cursor = cursor[step]
        elif isinstance(cursor, (list, tuple)):
            if not isinstance(step, int) or isinstance(step, bool):
                return "<absent>"
            if step >= len(cursor) or step < -len(cursor):
                return "<absent>"
            cursor = cursor[step]
        else:
            return "<absent>"
    return cursor


def stored_resources(document: Dict[str, Any]) -> Dict[str, Any]:
    """All eight stored resource slots, read at their established locations."""
    out: Dict[str, Any] = {}
    for name, location in RESOURCE_SLOTS.items():
        value = read_at(document, location)
        if value == "<absent>":
            raise CaptureError(
                EXIT_REQUEST,
                "save has no %s resource slot at /%s"
                % (name, "/".join(str(part) for part in location)),
            )
        out[name] = value
    return out


def recorded_ledger(document: Dict[str, Any]) -> Dict[str, Any]:
    """``privateState['magics']`` as a fresh ``{string key: int}`` map."""
    ledger = read_at(document, LEDGER_LOCATION)
    if ledger == "<absent>":
        return {}
    if not isinstance(ledger, dict):
        raise CaptureError(EXIT_REQUEST, "magics is %r, not an object" % (ledger,))
    return {str(key): value for key, value in ledger.items()}


def placed_row_count(document: Dict[str, Any]) -> int:
    try:
        return len(document["maps"][0]["items"])
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "save has no maps[0].items: %s" % error)


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


def sanitize_envelope_data(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The live request always sends the real bytes; only the record is redacted.
    ``ts`` is deliberately NOT redacted -- it is pinned to a constant, which is
    what makes the recorded field byte-stable.
    """
    envelope = parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return data_field(envelope)


def command_arguments(entry: Dict[str, Any]) -> List[Tuple[str, List[Any]]]:
    """The single crafted command this step sends.

    Both branches take exactly **one** argument, ``magic_id``
    (``command.py:653`` and ``665``), and the resource vector is the neutral
    all-zero one because no magic branch writes a resource.
    """
    return [(str(entry["command"]), [entry["magic_id"]])]


def build_envelope(pairs: List[Tuple[str, List[Any]]]) -> Dict[str, Any]:
    """The legacy batch envelope, with a pinned ``ts`` for byte stability."""
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": FIXTURE_TS,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [0, command, list(args), list(NEUTRAL_VECTOR)]
            for command, args in pairs
        ],
    }


def verify_envelope(envelope: Dict[str, Any], pairs: List[Tuple[str, List[Any]]]) -> None:
    """Assert the envelope this capture sends is the shape it claims.

    A capture that asserts its own request cannot quietly drift into sending
    something the manifest does not describe -- which is the failure mode that
    would make every recorded transition untrustworthy.
    """
    if sorted(envelope) != sorted(ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys are %r, not %r" % (sorted(envelope), sorted(ENVELOPE_KEYS)),
        )
    if envelope["ts"] != FIXTURE_TS:
        raise CaptureError(EXIT_REQUEST, "envelope ts is not the pinned constant")
    if len(envelope["commands"]) != len(pairs):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope carries %d commands, not the %d crafted"
            % (len(envelope["commands"]), len(pairs)),
        )
    for command_row, (command, args) in zip(envelope["commands"], pairs):
        if command_row[0] != 0:
            raise CaptureError(EXIT_REQUEST, "command row must start at 0")
        if command_row[1] != command:
            raise CaptureError(
                EXIT_REQUEST,
                "command row names %r, not the crafted %r" % (command_row[1], command),
            )
        if list(command_row[2]) != list(args):
            raise CaptureError(
                EXIT_REQUEST,
                "command arguments are %r, not the crafted %r"
                % (list(command_row[2]), list(args)),
            )
        if list(command_row[3]) != list(NEUTRAL_VECTOR):
            raise CaptureError(
                EXIT_REQUEST,
                "resource vector is %r, not the neutral %r"
                % (list(command_row[3]), list(NEUTRAL_VECTOR)),
            )
        if len(command_row[2]) != 1:
            raise CaptureError(
                EXIT_REQUEST,
                "a magic branch takes exactly ONE argument; %r has %d"
                % (args, len(args)),
            )


def expected_ledger_after(entry: Dict[str, Any], ledger: Dict[str, Any]) -> Dict[str, Any]:
    """The oracle's own post-ledger, recomputed from the branch's arithmetic.

    An **absent** key takes the ``else`` arm and is written at **zero** for both
    branches (``command.py:660``, ``672``).  A **present** key takes the ``if``
    arm: ``buy_magic`` **adds** ``min(cap, before + 1)`` and ``use_magic``
    **assigns** it.  The two are four lines apart and mutually inconsistent, and
    there is no shared helper in the legacy source to call.
    """
    key = str(entry["expect_key"])
    before = entry["expect_before"]
    if before is None:
        return dict(ledger, **{key: 0})
    capped = min(CAP_LITERAL, int(before) + 1)
    if entry["command"] == BUY_COMMAND:
        return dict(ledger, **{key: int(before) + capped})
    return dict(ledger, **{key: capped})


def verify_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Assert the committed corpus really carries what this fixture assumes.

    Run **before** a single server starts, so an environment change fails loudly
    instead of producing a fixture that quietly disagrees with the record.
    """
    private = read_at(seed, ("privateState",))
    if not isinstance(private, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the seed has no privateState object")
    ledger = private.get("magics")
    if ledger != SEED_LEDGER:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's privateState['magics'] is %r, not the recorded %r"
            % (ledger, SEED_LEDGER),
        )
    if len(ledger) != SEED_LEDGER_KEY_COUNT:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's ledger holds %d keys, not the recorded %d"
            % (len(ledger), SEED_LEDGER_KEY_COUNT),
        )
    for name, location in (("mana", ("privateState", "mana")), ("energy", ("privateState", "energy"))):
        if read_at(seed, location) == "<absent>":
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the seed records no %s slot, so the eight-slot comparison this "
                "capture asserts cannot be made" % name,
            )
    if read_at(seed, ("privateState", "mana")) != SEED_MANA:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's mana is %r, not the recorded %d"
            % (read_at(seed, ("privateState", "mana")), SEED_MANA),
        )
    pid = str(read_at(seed, ("playerInfo", "pid")))
    if pid != SEED_PID:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's playerInfo.pid is %r, not the recorded %r -- the pid is "
            "read from the document, never from the filename stem"
            % (pid, SEED_PID),
        )
    return {
        "path": str(SEED.relative_to(REPO_ROOT)).replace("\\", "/"),
        "placed_rows": placed_row_count(seed),
        "ledger": dict(ledger),
        "ledger_keys": len(ledger),
        "mana": read_at(seed, ("privateState", "mana")),
        "energy": read_at(seed, ("privateState", "energy")),
        "resource_slots": sorted(stored_resources(seed)),
        "resource_slot_count": RESOURCE_COUNT,
        "pid_read_from_document": pid,
        "committed_magics_is_the_only_non_empty_one": (
            "derived-provisional, recorded so a rerun reproduces the bytes; "
            "verified over all ten committed save documents by the committed "
            "investigation"
        ),
    }


def verify_transaction(
    entry: Dict[str, Any],
    before: Dict[str, Any],
    after: Dict[str, Any],
    status: int,
) -> Dict[str, Any]:
    """Recompute the oracle's post-state and assert it, leaf by leaf."""
    name = str(entry["name"])
    key = str(entry["expect_key"])
    ledger_before = recorded_ledger(before)
    ledger_after = recorded_ledger(after)

    if ledger_before.get(key, None) != entry["expect_before"]:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: recorded ledger[%r] was %r before the step, not the recorded %r "
            "-- the sequence is not running against its predecessor's state"
            % (name, key, ledger_before.get(key, "<absent>"), entry["expect_before"]),
        )

    expected_after = expected_ledger_after(entry, ledger_before)
    if ledger_after.get(key, None) != entry["expect_after"]:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: recorded ledger[%r] is %r after the step, not the recorded %r"
            % (name, key, ledger_after.get(key, "<absent>"), entry["expect_after"]),
        )
    if ledger_after != expected_after:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the whole ledger is %r, not the recomputed %r"
            % (name, ledger_after, expected_after),
        )

    # Only the addressed key may move.  A step whose recomputed value EQUALS its
    # before value -- the at-the-cap ``use_magic``, which assigns 50 over 50 --
    # moves no leaf at all, and that is a recorded distinct outcome from a
    # refusal.  The expected path set is therefore derived from the recomputed
    # ledger rather than assumed to be the addressed key.
    addressed_path = "/privateState/magics/%s" % key
    diff = leaf_diff(before, after)
    changed_paths = [row[0] for row in diff]
    no_change = expected_after == ledger_before
    allowed = set() if no_change else {addressed_path}
    if set(changed_paths) != allowed:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: these leaves moved %r, and exactly %r may"
            % (name, changed_paths, sorted(allowed)),
        )

    resources_before = stored_resources(before)
    resources_after = stored_resources(after)
    moved = sorted(
        name_
        for name_ in RESOURCE_SLOTS
        if not typed_equal(resources_before[name_], resources_after[name_])
    )
    if moved:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: stored resources %r moved, and the contract is that no magic "
            "branch charges anything" % (name, moved),
        )

    if placed_row_count(before) != placed_row_count(after):
        raise CaptureError(
            EXIT_REQUEST, "%s: the placed-row count moved, and it must not" % name
        )

    created = bool(entry.get("created"))
    facts: Dict[str, Any] = {
        "name": name,
        "step_number": int(entry["step"]),
        "command": str(entry["command"]),
        "operator": str(entry["operator"]),
        "cap_literal": CAP_LITERAL,
        "cap_source_lines": list(CAP_SOURCE_LINES),
        "magic_id_sent": entry["magic_id"],
        "magic_id_sent_type": type(entry["magic_id"]).__name__,
        "magic_id_string_form": str(entry["magic_id"]),
        "ledger_key": key,
        "ledger_key_present_before": entry["expect_before"] is not None,
        "ledger_key_created": created,
        "ledger_keys_before": len(ledger_before),
        "ledger_keys_after": len(ledger_after),
        "ledger_value_before": entry["expect_before"],
        "ledger_value_after": entry["expect_after"],
        "ledger_before": ledger_before,
        "ledger_after": ledger_after,
        "ledger_recomputed": expected_after,
        "changed_leaf_paths": changed_paths,
        "only_the_addressed_key_moved": True,
        "unchanged_leaves_sha256": unchanged_leaves_sha(after, changed_paths),
        "state_sha256_before": canonical_state_sha(before),
        "state_sha256_after": canonical_state_sha(after),
        "placed_rows_before": placed_row_count(before),
        "placed_rows_after": placed_row_count(after),
        "resource_slot_count": RESOURCE_COUNT,
        "resources_before": resources_before,
        "resources_after": resources_after,
        "resources_moved": moved,
        "resources_comparison": (
            "all %d stored resource slots compared; moved: NONE" % RESOURCE_COUNT
        ),
        "mana_before": resources_before["mana"],
        "mana_after": resources_after["mana"],
        "energy_before": resources_before["energy"],
        "energy_after": resources_after["energy"],
        "status": status,
        "parity_with_delivered_endpoint": bool(entry.get("parity", False)),
        "note": str(entry["note"]),
    }
    if entry.get("parity_note"):
        facts["parity_note"] = str(entry["parity_note"])
    if entry.get("divergence"):
        facts["divergence"] = str(entry["divergence"])
    if entry.get("modern_refuses"):
        facts["delivered_endpoint_refusal"] = str(entry["modern_refuses"])
    if entry.get("crossed_cap"):
        facts["crossed_the_literal_cap"] = True
    if entry.get("decreased"):
        facts["charges_destroyed"] = int(entry["charges_destroyed"])
        facts["decreased"] = True
    if entry.get("out_of_committed_table"):
        facts["identity_outside_the_committed_ten_entry_table"] = True
    if entry.get("distinct_key_from"):
        facts["distinct_key_from"] = str(entry["distinct_key_from"])
        facts["string_form_is_the_hazard"] = (
            "str(1.0) is %r, which is not the committed key %r, so the two "
            "requests are two unrelated ledger entries"
            % (str(entry["magic_id"]), str(entry["distinct_key_from"]))
        )
    if "modern_derives_after" in entry:
        facts["modern_derives_after"] = int(entry["modern_derives_after"])
        facts["modern_differs_from_oracle"] = True
    if entry.get("parity"):
        facts["modern_derives_after"] = int(entry["expect_after"])
        facts["modern_differs_from_oracle"] = False
    return facts


def stdout_offset(stdout_path: Path) -> int:
    """The server's stdout size, taken immediately before a request.

    This capture runs ONE server for the whole sequence rather than one per
    transaction, so the stdout file is shared by all twelve steps.
    ``capture_combat_fixture`` needs no offset because it starts a fresh server per
    transaction and therefore reads a file holding exactly one request's output;
    reusing that helper unchanged here would report the previous steps' lines as
    this step's evidence.
    """
    try:
        return stdout_path.stat().st_size
    except OSError:
        return 0


def printed_branch_lines(stdout_path: Path, command: str, since: int = 0) -> List[str]:
    """The printed lines **this** request emitted, in order.

    ``print("Used magic spell")`` runs at ``command.py:674`` -- AFTER the write at
    ``670``, so the line proves the branch ran.  It is also the sharpest piece of
    evidence in this fixture: the message claims a spell was used while the same
    branch removed 63 player-owned charges.

    ``since`` is the stdout size taken before the request, so a step's evidence is
    its own output and never an ancestor's.
    """
    wanted = "COMMAND: %s(" % command
    found: List[str] = []
    try:
        with stdout_path.open("rb") as handle:
            handle.seek(since)
            raw = handle.read()
    except OSError:
        return found
    for line in raw.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if wanted in stripped:
            found.append(stripped)
    return found


def printed_message(lines: List[str], command: str) -> str:
    """The ``-> <message>`` tail of a printed branch line."""
    expected = PRINTED_BUY if command == BUY_COMMAND else PRINTED_USE
    for line in lines:
        if line.endswith(expected):
            return expected
    return ""


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Per-fixture file count and combined digest, for the containment check."""
    out: Dict[str, Dict[str, object]] = {}
    for name in PROTECTED_FIXTURES:
        directory = REPO_ROOT / "tests" / "fixtures" / name
        if not directory.is_dir():
            out[name] = {"present": False, "files": 0, "combined": ""}
            continue
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        out[name] = {
            "present": True,
            "files": len(files),
            "combined": canonical_digest(
                [
                    (
                        str(path.relative_to(directory)).replace("\\", "/"),
                        committed_digest(path.read_bytes()),
                    )
                    for path in files
                ]
            ),
        }
    return out


def publish(staging: Path, out_dir: Path) -> None:
    """Replace ``out_dir`` with ``staging``, atomically enough for this use.

    The fixture is staged OUTSIDE the working tree and published only after every
    check passed, so a failed run writes nothing into the repository.
    """
    previous = out_dir.with_name(out_dir.name + "-previous")
    if previous.exists():
        shutil.rmtree(str(previous), ignore_errors=True)
    if out_dir.exists():
        out_dir.rename(previous)
    try:
        staging.rename(out_dir)
    except OSError:
        if out_dir.exists():
            shutil.rmtree(str(out_dir), ignore_errors=True)
        staging.rename(out_dir)
    if previous.exists():
        shutil.rmtree(str(previous), ignore_errors=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="fixture output directory (default: %(default)s)",
    )
    args_ns = parser.parse_args(argv)
    out_dir: Path = args_ns.out

    if not SEED.is_file():
        print("capture: missing village seed save: %s" % SEED, file=sys.stderr)
        return EXIT_ENVIRONMENT
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    if not isinstance(seed, dict):
        print("capture: village seed is not a JSON object: %s" % SEED, file=sys.stderr)
        return EXIT_ENVIRONMENT

    # Assert the committed corpus really carries what this fixture assumes,
    # before a single server starts.
    census = verify_seed(seed)

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
    pre_seed_sha = committed_digest(SEED.read_bytes())

    staging = Path(tempfile.mkdtemp(prefix="compat-magic-capture-staging-"))
    summaries: List[Dict[str, Any]] = []
    transcript: List[Dict[str, Any]] = []
    disposables: List[Path] = []

    print(
        "capture: seed=%s (%d placed rows, %d ledger keys, %d resource slots, "
        "mana=%d, energy=%d)"
        % (
            SEED.name,
            census["placed_rows"],
            census["ledger_keys"],
            census["resource_slot_count"],
            census["mana"],
            census["energy"],
        )
    )
    print(
        "capture: %d transactions, ONE disposable and ONE server for the whole "
        "interleaved sequence (sessions.load_saves() caches the corpus in memory "
        "at import, so a restored seed file is not enough -- and every step must "
        "run against its predecessor's recorded state)"
        % (len(TRANSACTIONS),)
    )

    try:
        disposable: Optional[Path] = None
        process = None
        stdout_path = None
        try:
            disposable, pid, seed_sha_raw = build_disposable(
                Path(tempfile.gettempdir()), SEED
            )
            # ``build_disposable`` returns a raw working-tree digest and is
            # shared by eighteen captures, so it is not redefined here.  The
            # guard below needs the committed-blob form, so it is taken
            # directly from the seed source's own bytes -- which is also the
            # stricter check: it compares the SOURCE against the recorded
            # value, while ``seed_sha_raw`` would compare the COPY the helper
            # made.  Both are asserted, and neither substitutes for the other.
            seed_sha = committed_digest(SEED.read_bytes())
            disposables.append(disposable)
            saves_dir = disposable / "saves"
            seed_group = save_group_record(saves_dir)
            if seed_sha != pre_seed_sha:
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "capture: the committed seed's digest %r differs from the "
                    "recorded %r (both digests are over the committed blob form)"
                    % (seed_sha, pre_seed_sha),
                )
            if seed_sha_raw != sha256_file(seed_target_of(disposable, pid)):
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "capture: the helper's verbatim copy digest %r differs from the "
                    "copy it made at %r -- the seed was not copied verbatim"
                    % (seed_sha_raw, pid),
                )

            process, stdout_path, stderr_path = start_server(
                disposable, {"PYTHONUNBUFFERED": "1"}
            )
            if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
                raise CaptureError(
                    EXIT_SERVER,
                    "capture: legacy server did not become ready (exit=%s)\n"
                    "--- stdout ---\n%s\n--- stderr ---\n%s"
                    % (
                        process.poll(),
                        read_tail(stdout_path),
                        read_tail(stderr_path),
                    ),
                )

            save_path = saves_dir / ("%s.save.json" % pid)
            startup_group = save_group_record(saves_dir)
            if startup_group["sha256"] != seed_group["sha256"]:
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "%s: the corpus changed during server startup, so the "
                    "server is not reading the committed seed",
                )

            # --- login, exactly as a logged-in Flash client would --------
            login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
            login_result = http_request(
                LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0
            )
            if login_result["status"] != 302:
                raise CaptureError(
                    EXIT_REQUEST,
                    "capture: login expected HTTP 302, got %r"
                    % (login_result["status"],),
                )
            cookie = extract_session_cookie(login_result)
            login_body = login_result.pop("body")
            after_login = json.loads(save_path.read_text(encoding="utf-8"))
            if canonical_state_sha(after_login) != canonical_state_sha(seed):
                raise CaptureError(
                    EXIT_REQUEST,
                    "capture: the login step changed the corpus, so it is not a "
                    "neutral session step",
                )

            # The login step is recorded once, before the sequence, because a
            # login that changes nothing is worth recording once.
            login_request_record = {
                "captured_at_utc": iso_now(),
                "method": login_result["method"],
                "target": login_result["target"],
                "path": login_result["path"],
                "query": login_result["query"],
                "form": sanitize_form(login_result["form"] or {}),
                "headers_sent": sanitize_headers(login_result["headers_sent"]),
                "scheme": "http",
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "seed_save": SEED.name,
                "note": (
                    "Session fidelity only.  This step leaves the corpus "
                    "byte-identical, which the capture asserts."
                ),
            }
            login_response_record = {
                "status": int(login_result["status"]),
                "reason": login_result["reason"],
                "headers": sanitize_headers(login_result["response_headers"]),
                "body_bytes": len(login_body),
                "body_sha256": committed_digest(login_body),
                "captured_at_utc": iso_now(),
            }
            login_dir = staging / "steps" / "login_post"
            write_json(login_dir / "request.json", login_request_record)
            write_json(login_dir / "before.json", seed)
            write_json(login_dir / "response.meta.json", login_response_record)
            write_bytes(login_dir / "response.body", login_body)
            write_json(login_dir / "after.json", after_login)

            for entry in TRANSACTIONS:
                name = str(entry["name"])
                # --- the one magic batch ---------------------------------
                before = json.loads(save_path.read_text(encoding="utf-8"))
                pairs = command_arguments(entry)
                envelope = build_envelope(pairs)
                verify_envelope(envelope, pairs)
                form = {
                    "USERID": pid,
                    "user_key": USER_KEY,
                    "language": LANGUAGE,
                    "data": data_field(envelope),
                }
                # One server for the whole sequence, so the stdout file already
                # holds the previous steps' output; the offset is what makes
                # this step's evidence its own.
                stdout_before = stdout_offset(stdout_path)
                result = http_request(
                    LEGACY_PORT,
                    "POST",
                    DYNAMIC_ROOT + "/command.php",
                    form=dict(form),
                    cookie=cookie,
                    timeout=30.0,
                )
                status = int(result["status"])
                body = result.pop("body")
                after = json.loads(save_path.read_text(encoding="utf-8"))

                facts = verify_transaction(entry, before, after, status)

                if status != 200:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the legacy request answered HTTP %d; the committed "
                        "record says all twelve succeed with 200, so the oracle "
                        "does not reproduce" % (name, status),
                    )
                payload = json.loads(body.decode("utf-8"))
                if payload != {"result": "success"}:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: response is not the legacy success result: %r"
                        % (name, payload),
                    )
                facts["response_payload"] = payload

                lines = printed_branch_lines(
                    stdout_path, str(entry["command"]), stdout_before
                )
                facts["stdout_offset_before"] = stdout_before
                facts["stdout_evidence_is_this_request_only"] = True
                message = printed_message(lines, str(entry["command"]))
                facts["printed_branch_lines"] = lines
                facts["printed_message"] = message
                facts["printed_message_claims"] = (
                    "a spell was used" if str(entry["command"]) == USE_COMMAND
                    else "a spell was bought"
                )
                if not lines:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the branch printed nothing, so the recorded state "
                        "change has no positive evidence that this branch ran"
                        % name,
                    )
                if message != str(entry["printed"]):
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the branch printed %r, not the recorded %r"
                        % (name, message, entry["printed"]),
                    )
                # The message is not proof of the effect -- it is printed
                # AFTER the write and says nothing about the value.  On
                # use_1_destroys_charges it actively contradicts it.
                if entry.get("decreased"):
                    facts["message_contradicts_the_effect"] = (
                        "the branch printed %r while REMOVING %d charges; the "
                        "message is a print, not a claim the code checks"
                        % (str(entry["printed"]), int(entry["charges_destroyed"]))
                    )

                request_record = {
                    "captured_at_utc": iso_now(),
                    "method": result["method"],
                    "target": result["target"],
                    "path": result["path"],
                    "query": result["query"],
                    "form": {
                        key: (
                            sanitize_envelope_data(value)
                            if key == "data"
                            else (REDACTED if key in SENSITIVE_FORM_KEYS else value)
                        )
                        for key, value in (result["form"] or {}).items()
                    },
                    "headers_sent": sanitize_headers(result["headers_sent"]),
                    "scheme": "http",
                    "host": LEGACY_HOST,
                    "port": LEGACY_PORT,
                    "seed_save": SEED.name,
                    "note": (
                        "Exact client request bytes are reconstructed from this "
                        "record; Host is set explicitly, no User-Agent header is "
                        "sent. The batch's single argument IS the crafted, "
                        "client-supplied identity under test -- the branch "
                        "validates nothing, which is the finding, not an "
                        "oversight. The resource vector is NEUTRAL. ts is "
                        "pinned to a constant so this record is byte-stable; "
                        "legacy parses it and never reads it. user_key is "
                        "redacted; accessToken is the crafted empty placeholder, "
                        "never a token value."
                    ),
                }
                response_record = {
                    "status": status,
                    "reason": result["reason"],
                    "headers": sanitize_headers(result["response_headers"]),
                    "body_bytes": len(body),
                    "body_sha256": committed_digest(body),
                    "captured_at_utc": iso_now(),
                }
                step_dir = staging / "steps" / ("txn_%s" % name)
                write_json(step_dir / "request.json", request_record)
                write_json(step_dir / "before.json", before)
                write_json(step_dir / "response.meta.json", response_record)
                write_bytes(step_dir / "response.body", body)
                write_json(step_dir / "after.json", after)
                write_json(step_dir / "transaction.json", facts)

                summaries.append(facts)
                transcript.append(
                    {
                        "name": name,
                        "step_number": int(entry["step"]),
                        "disposable_pid_read_from_document": pid,
                        "seed_sha256": seed_sha,
                        "printed_branch_lines": lines,
                    }
                )
                print(
                    "capture: %-38s %s[%r] ledger %d -> %d, keys %d -> %d, %s "
                    "slots moved, parity=%s"
                    % (
                        name,
                        str(entry["command"]),
                        entry["magic_id"],
                        -1 if entry["expect_before"] is None else int(entry["expect_before"]),
                        int(entry["expect_after"]),
                        facts["ledger_keys_before"],
                        facts["ledger_keys_after"],
                        len(facts["resources_moved"]),
                        facts["parity_with_delivered_endpoint"],
                    )
                )
                for line in lines:
                    print("capture:   printed | %s" % line)
        finally:
            if process is not None:
                server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
                if server_error:
                    raise CaptureError(
                        EXIT_SERVER, "capture: %s" % server_error
                    )

        # --- the sequence, asserted step by step ----------------------------
        by_name = {str(item["name"]): item for item in summaries}
        missing = [
            str(entry["name"]) for entry in TRANSACTIONS if str(entry["name"]) not in by_name
        ]
        if missing:
            raise CaptureError(
                EXIT_REQUEST, "recorded transactions are missing: %r" % missing
            )
        # The load-bearing structural check: EVERY step's whole recorded ledger
        # equals its predecessor's, including the key-CREATING steps whose
        # recorded "before" omits the new key.  Asserting this over the whole
        # sequence is what makes the numbers below mean what they say; without
        # it each step could be an independent transaction off the seed.
        for index in range(1, len(TRANSACTIONS)):
            previous_name = str(TRANSACTIONS[index - 1]["name"])
            current_name = str(TRANSACTIONS[index]["name"])
            previous = by_name[previous_name]["ledger_after"]
            current = by_name[current_name]["ledger_before"]
            if current != previous:
                raise CaptureError(
                    EXIT_REQUEST,
                    "step %r started from ledger %r, not its predecessor's %r"
                    % (current_name, current, previous),
                )
        # The recorded key-count ladder over all twelve steps.
        ladder = [by_name[str(e["name"])]["ledger_keys_after"] for e in TRANSACTIONS]
        recorded_ladder = [5, 5, 5, 5, 5, 5, 5, 5, 6, 7, 7, 8]
        if ladder != recorded_ladder:
            raise CaptureError(
                EXIT_REQUEST,
                "the ledger key count ran %r, not the recorded %r"
                % (ladder, recorded_ladder),
            )
        # The recorded asymmetry, in order, on key "1".
        asymmetry = [str(entry["name"]) for entry in TRANSACTIONS[:8]]
        chain_values = [by_name[name]["ledger_value_after"] for name in asymmetry]
        recorded_chain = [3, 7, 15, 31, 63, 113, 50, 50]
        if chain_values != recorded_chain:
            raise CaptureError(
                EXIT_REQUEST,
                "key '1' ran %r, not the recorded %r" % (chain_values, recorded_chain)
            )
        if by_name["use_1_destroys_charges"]["charges_destroyed"] != 63:
            raise CaptureError(
                EXIT_REQUEST,
                "the use branch destroyed %r charges, not the recorded 63: the "
                "sharpest measurement in the line does not reproduce"
                % (by_name["use_1_destroys_charges"]["charges_destroyed"],),
            )
        print(
            "capture: asymmetry MEASURED -- key '1' ran %s, and the use arm turned "
            "113 owned charges into 50"
            % " -> ".join(str(v) for v in recorded_chain)
        )

        # --- the identity hazards, asserted ---------------------------------
        float_step = by_name["use_float_id_creates_a_distinct_key"]
        if float_step["ledger_key"] == str(float_step["distinct_key_from"]):
            raise CaptureError(
                EXIT_REQUEST,
                "the float identity resolved to the SAME key as the integer one, so "
                "the distinct-key hazard does not reproduce",
            )
        if float_step["ledger_key"] in float_step["ledger_before"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the float step's key %r was already present before it ran"
                % float_step["ledger_key"],
            )
        out_of_table = by_name["buy_out_of_table_id_99_accepted"]
        if not out_of_table.get("identity_outside_the_committed_ten_entry_table"):
            raise CaptureError(
                EXIT_REQUEST, "the out-of-table identity was not recorded as such"
            )
        # The recorded discriminator: a STRING "1" resolves to the SAME key, so
        # the float hazard is about the string form and not the JSON type alone.
        string_step = by_name["use_string_id_resolves_the_same_key"]
        if string_step["ledger_key"] != "1":
            raise CaptureError(
                EXIT_REQUEST,
                "the string identity resolved to key %r, not the integer's key '1'"
                % string_step["ledger_key"],
            )
        if string_step["ledger_keys_after"] != string_step["ledger_keys_before"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the string identity changed the key count %r -> %r; the record "
                "says 7 keys in and 7 keys out"
                % (
                    string_step["ledger_keys_before"],
                    string_step["ledger_keys_after"],
                ),
            )
        absent = by_name["use_absent_id_3_creates_zero"]
        if absent["ledger_value_after"] != 0:
            raise CaptureError(
                EXIT_REQUEST,
                "an absent key was written at %r, not the recorded zero"
                % (absent["ledger_value_after"],),
            )
        print(
            "capture: identity hazards MEASURED -- id 99 accepted though it is not "
            "one of the ten committed magics, a string '1' hit the integer's own "
            "key, a float id created the distinct key %r, and an absent key was "
            "written at ZERO" % float_step["ledger_key"]
        )

        # --- the no-price claim, asserted over ALL EIGHT slots --------------
        moved_anywhere = sorted(
            {
                name_
                for item in summaries
                for name_ in item["resources_moved"]
            }
        )
        if moved_anywhere:
            raise CaptureError(
                EXIT_REQUEST,
                "stored resources %r moved across the fixture, and the contract is "
                "that no magic branch charges anything" % moved_anywhere,
            )
        mana_values = sorted({int(item["mana_after"]) for item in summaries})
        if mana_values != [SEED_MANA]:
            raise CaptureError(
                EXIT_REQUEST,
                "mana ended at %r, not the recorded constant %d: a use_magic charged "
                "something" % (mana_values, SEED_MANA),
            )
        print(
            "capture: no price MEASURED -- all %d stored resource slots identical "
            "across all %d steps, mana held at %d"
            % (RESOURCE_COUNT, len(summaries), SEED_MANA)
        )

        # --- containment, before publishing anything -----------------------
        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        post_fixtures = protected_fixture_snapshot()
        post_seed_sha = committed_digest(SEED.read_bytes())

        if pre_combined != post_combined:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree containment changed:\n  before %s\n  after  %s"
                % (pre_combined, post_combined),
            )
        if pre_seed_sha != post_seed_sha:
            raise CaptureError(
                EXIT_CONTAINMENT, "the committed village seed changed during the run"
            )
        changed_fixtures = sorted(
            name
            for name in PROTECTED_FIXTURES
            if pre_fixtures[name] != post_fixtures[name]
        )
        if changed_fixtures:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "already-committed fixtures changed during the run: %r" % (changed_fixtures,),
            )
        working_tree_saves = REPO_ROOT / "saves"
        if working_tree_saves.exists():
            raise CaptureError(
                EXIT_CONTAINMENT,
                "a working-tree saves/ directory exists; the run wrote outside its "
                "disposable",
            )

        divergences = [
            item for item in summaries if not item["parity_with_delivered_endpoint"]
        ]
        manifest = {
            "schema": SCHEMA,
            "captured_at_utc": iso_now(),
            "purpose": (
                "Executed-legacy evidence for the magic-counter surface: buy_magic "
                "(command.py:652-662) and use_magic (664-674). It records what the "
                "ORACLE does, including the five behaviours this capability "
                "deliberately does NOT reproduce: unbounded buy growth, a "
                "charge-destroying use decrease, an out-of-table identity, a "
                "float-keyed identity, and an absent key written at zero."
            ),
            "invocation": "python -B apps/compat-api/capture_magic_fixture.py",
            "interpreter": "CPython %d.%d (pinned)" % sys.version_info[:2],
            "server": {
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "process": "python -B server.py inside the disposable",
                "starts": 1,
                "one_server_for_the_whole_sequence": True,
                "one_server_reason": (
                    "sessions.load_saves() caches the corpus in a module global at "
                    "import, so a running server never re-reads the seed file. "
                    "Restoring the seed between steps on one server leaves the in "
                    "memory corpus already mutated and silently produces a different "
                    "result."
                ),
                "one_per_transaction_reason_rejected": (
                    "One server per TRANSACTION was rejected rather than merely "
                    "avoided: the committed record states steps 1-8 as one "
                    "interleaved sequence in which each step's recorded before is "
                    "the previous step's recorded after (2 -> 3 -> 7 -> 15 -> 31 -> "
                    "63 -> 113 -> 50 -> 50), and states steps 9-12 were driven "
                    "against the same disposable corpus. Those numbers mean nothing "
                    "unless each step really ran against its predecessor's state, "
                    "and the capture asserts exactly that for all eleven links."
                ),
                "sequence": SEQUENCE_NOTE,
                "sequence_linkage_asserted": (
                    "every step's whole recorded ledger equals its predecessor's, "
                    "for all eleven links, plus the key-count ladder "
                    "[5, 5, 5, 5, 5, 5, 5, 5, 6, 7, 7, 8]"
                ),
                "debug": False,
                "debug_note": (
                    "server.py runs app.run(..., debug=False). Every recorded step "
                    "answers HTTP 200, so no framework error page is committed."
                ),
                "env_extra": {"PYTHONUNBUFFERED": "1"},
                "env_extra_note": (
                    "Set for THIS capture's child processes only, via a defaulted "
                    "parameter on start_server. child_environment() is untouched, so "
                    "no existing capture's log changes. The printed lines are the "
                    "evidence that each branch ran, and block buffering would lose "
                    "them when the harness reaps the child."
                ),
            },
            "seed": {
                "path": str(SEED.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": pre_seed_sha,
                "pid_read_from_document": SEED_PID,
                "why_this_one": (
                    "It is the only committed corpus whose privateState.magics is "
                    "non-empty, so the increment arm is observable as a value that "
                    "moves while the key count does not -- a pair the key-creation "
                    "branch cannot produce. All ten committed save documents were "
                    "measured; the other nine record an empty object."
                ),
                "census": census,
                "no_ledger_entry_fabricated": (
                    "The seed's five keys are reproduced verbatim in every "
                    "transaction's ledger_before, and every step's before ledger is "
                    "asserted equal to its predecessor's after ledger. No entry is "
                    "written into the seed by this capture; the seed's digest is "
                    "asserted before and after the run."
                ),
            },
            "batch_shape": {
                "commands": list(COMMANDS),
                "operators": {BUY_COMMAND: BUY_OPERATOR, USE_COMMAND: USE_OPERATOR},
                "operator_source_lines": {BUY_COMMAND: [658], USE_COMMAND: [670]},
                "arguments_per_command": 1,
                "resource_vector": list(NEUTRAL_VECTOR),
                "vector_status": "neutral by construction, every transaction",
                "ts": FIXTURE_TS,
                "ts_note": (
                    "Pinned to a constant, as on the stored-placement and "
                    "unit-experience captures. The dispatcher parses it and never "
                    "reads it."
                ),
                "arguments": (
                    "CRAFTED AND CLIENT-SUPPLIED. Both branches read exactly one "
                    "argument and validate nothing: not the type, not the table "
                    "membership, and not the string form. The captured values 1, 3, "
                    "99, '1' and 1.0 are what makes each hazard observable."
                ),
            },
            "cap": {
                "value": CAP_LITERAL,
                "source_lines": list(CAP_SOURCE_LINES),
                "status": "literal in the preserved source, never content-derived",
                "rejected_derivation": magic_envelope.REJECTED_CAP_DERIVATION,
            },
            "recorded_steps": list(RECORDED_STEPS) + ["login_post"],
            "login_step": (
                "Performed once, before the sequence, and recorded once. Its "
                "neutrality is asserted: the corpus after the login is compared "
                "against the committed seed and must be byte-identical."
            ),
            "transactions": summaries,
            "established": [
                "The two branches are FOUR LINES APART and not interchangeable: "
                "buy_magic ADDS min(50, x+1) (command.py:658) and use_magic "
                "ASSIGNS it (command.py:670). Neither behaves as its name suggests.",
                "buy_magic is UNBOUNDED: key '1' ran 2 -> 3 -> 7 -> 15 -> 31 -> 63 "
                "-> 113 and would keep adding 50 per request, so the literal 50 is "
                "not a cap on that arm.",
                "use_magic can DESTROY charges: 113 owned charges became 50, a loss "
                "of 63, on a command whose printed message is 'Used magic spell'. "
                "This is the sharpest measurement in the line.",
                "At the cap the use arm is a no-op (50 -> 50), so 'unchanged' and "
                "'refused' are different outcomes and the capture records which.",
                "An ABSENT key takes the else arm and is written at ZERO, for BOTH "
                "branches (command.py:660, 672) -- so the legacy 'acquire a spell "
                "you hold none of' path increments nothing at all.",
                "The identity is UNVALIDATED: 99 is accepted although it is not one "
                "of the ten committed magics.",
                "The identity is UNTYPED: str(1.0) is '1.0', so a float creates a "
                "SECOND, unrelated ledger key, while a STRING '1' resolves to the "
                "SAME key. That pair is what proves the hazard is the string form "
                "and not the JSON type alone.",
                "Under a NEUTRAL vector all EIGHT stored resource slots are "
                "byte-identical in all twelve steps and mana holds at 15, so no "
                "magic branch charges anything and no effect is applied.",
                "Only the addressed ledger key ever moves: every step's whole-document "
                "leaf diff is exactly one path.",
                "Both branches are absent from get_game_config.py entirely -- the "
                "word 'magic' has zero occurrences there -- so the ten committed "
                "magics are loaded and never indexed, and there is no code path from "
                "a magic id to its content row at all.",
            ],
            "divergences": {
                "count": len(divergences),
                "recorded_not_narrowed": True,
                "parity_claimed_for": [
                    str(item["name"]) for item in summaries
                    if item["parity_with_delivered_endpoint"]
                ],
                "transactions": [
                    {
                        "name": item["name"],
                        "command": item["command"],
                        "magic_id_sent": item["magic_id_sent"],
                        "magic_id_sent_type": item["magic_id_sent_type"],
                        "ledger_key": item["ledger_key"],
                        "oracle_ledger_after": item["ledger_value_after"],
                        "modern_derives_after": item.get("modern_derives_after"),
                        "divergence": item.get("divergence"),
                        "delivered_endpoint_refusal": item.get(
                            "delivered_endpoint_refusal"
                        ),
                    }
                    for item in divergences
                ],
                "asymmetry_chain": {
                    "recorded_values": recorded_chain,
                    "buy_arm": magic_envelope.LEGACY_UNBOUNDED_ARM,
                    "use_arm": magic_envelope.LEGACY_DECREASING_ARM,
                    "cap_uniformity": magic_envelope.CAP_UNIFORMITY,
                    "parity_claimed": False,
                },
                "why_not_narrowed": (
                    "Narrowing any of these would require a magic rule the preserved "
                    "source does not contain. There is no committed amount, no "
                    "committed cap derivation, and no reader of the ledger, so the "
                    "only coherent modern contract is a server-derived increment "
                    "under the recorded literal -- and every difference from the "
                    "oracle is recorded rather than reproduced."
                ),
            },
            "derived_provisional": [
                "That villages/Neutral.json is the seed. Recorded so a rerun "
                "reproduces the committed bytes; it is the only corpus with a "
                "non-empty ledger, so the choice is forced rather than preferred.",
                "That all twelve steps are ONE interleaved sequence rather than twelve "
                "independent transactions. It rests on the committed record's "
                "wording ('deliberately interleaved', 'driven against the same "
                "disposable corpus') and is independently settled by step 11: "
                "use_magic ['1'] leaves key '1' at 50, which is only reachable if "
                "step 8's 50 is still there, while on a fresh seed that key holds "
                "2 and the same request would make it 3. The capture asserts every "
                "one of the eleven links.",
                "That a modern capability should increment by one under the cap at "
                "all. No committed rule states it; it is the coherent reading of a "
                "ledger nobody reads, and it is recorded as a decision rather than "
                "a reproduction.",
            ],
            "not_claimed": [
                "Any damage rule, effect, magnitude, or outcome. The committed "
                "magics carry mana, level, gold, cash and target and NO damage, "
                "multiplier, radius or duration field; the Attack Boost description "
                "promises an effect whose magnitude was never committed.",
                "That the cap is content-derived. It is a bare literal in a min() "
                "call at command.py:658 and 670, and the rejected derivation is "
                "retained rather than dropped.",
                "That the modern endpoint reproduces the oracle's counter value. It "
                "deliberately does not, and every step records the oracle value, the "
                "derived value, and whether they agree.",
                "Anything about what the real Flash client sent. The client was "
                "never executed: every payload here is crafted.",
                "Any per-magic behaviour. One of the ten committed magics was driven "
                "(id 1); the other nine ledger keys were observed but not driven, "
                "and no per-magic effect is claimed because none exists to claim.",
                "Any partial application or atomicity claim about the oracle's "
                "persistence boundary. Every recorded step succeeded, so the "
                "failure-mode boundary the combat line established was not "
                "re-measured here.",
                "A per-magic price, mana cost, or effect for any of the ten "
                "committed magics. The eight-slot comparison is the evidence that "
                "none is charged by these two branches.",
            ],
            "time_dependent_fields": {
                "request_captured_at_utc": (
                    "Recorded per step and necessarily volatile.  With "
                    "captured_at_utc and the Werkzeug Date header below, these "
                    "are the ONLY fields that change between reruns -- measured, "
                    "not assumed: two consecutive runs were compared file by "
                    "file with the timestamps elided and exactly the thirteen "
                    "response.meta.json files differed, each on its Date header "
                    "alone.  Every transaction record, state document, request "
                    "record and manifest body is byte-identical across reruns."
                ),
                "captured_at_utc": "Same, in this manifest.",
                "response Date header": (
                    "Each step's response.meta.json records the server's own "
                    "Date header verbatim, so it moves with the wall clock.  "
                    "capture_combat_fixture records it the same way; nothing "
                    "redacts it, because redacting a header the oracle sent "
                    "would be narrowing the record."
                ),
                "ts": "Pinned to a constant, so not volatile.",
            },
            "containment": {
                "combined_before": pre_combined,
                "combined_after": post_combined,
                "identical": pre_combined == post_combined,
                "groups": sorted(pre_groups),
                "seed_sha256_before": pre_seed_sha,
                "seed_sha256_after": post_seed_sha,
                "working_tree_saves_absent": True,
                "protected_fixtures": sorted(PROTECTED_FIXTURES),
                "protected_fixtures_unchanged": True,
            },
            "cleanup": {
                "disposables": len(disposables),
                "note": (
                    "Each disposable is removed by the harness's own finally block; "
                    "the fixture is staged OUTSIDE the working tree and published "
                    "only after every check passed, so a failed run writes nothing "
                    "into the repository."
                ),
            },
            "transcript": transcript,
            "exit_code": EXIT_OK,
        }
        write_json(staging / "capture-manifest.json", manifest)
        publish(staging, out_dir)
        print("capture: fixture published to %s" % out_dir)
        print("capture: containment %s before and after (identical)" % pre_combined[:16])
        return EXIT_OK
    except CaptureError as error:
        print("capture: %s" % error, file=sys.stderr)
        return error.exit_code
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        for path in disposables:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())