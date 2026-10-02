#!/usr/bin/env python3
"""Derivation of the legacy ``complete_tutorial`` envelope and the tutorial gate.

M9 line 3 (``tutorial/progression``) — the **last** M9 deliver item with no
delivered line, and the smallest legacy surface in the whole family: **one
branch**, **one write**, **one stored field**.  The contract is committed in
``docs/legacy-m9-tutorial.md`` (PR #264), which measured it over all **eleven**
root ``.py`` modules with comments and docstrings stripped.  Nothing here is
inferred from a converted asset package.

What legacy actually does (established — ``command.py:60-66``)
    ================================ ================================================
    line                                effect
    ================================ ================================================
    ``command.py:60``                   ``elif cmd == "complete_tutorial":``
    ``command.py:61``                   ``tutorial_step = args[0]`` — a **local**
    ``command.py:62``                   ``print("Tutorial step", …)`` — a log line
    ``command.py:63``                   ``if tutorial_step >= 25 or
                                         tutorial_step == 15:``
    ``command.py:64``                   ``print("Tutorial COMPLETED!")``
    ``command.py:65``                   ``save["playerInfo"]["completed_tutorial"] = 1``
    ``command.py:66``                   ``return``
    ================================ ================================================

``complete_tutorial`` is the **entire** legacy tutorial surface: six quoted
occurrences of ``tutorial`` on five lines, all inside this one branch, with zero
occurrences in the other ten root modules.

The four decisions this module exists to record

    **D1 — the gate is a DISJUNCTION with a NINE-VALUE HOLE.**  Completion follows
    ``tutorial_step >= 25 or tutorial_step == 15`` over the **client's**
    ``args[0]``, used raw.  Executed-legacy probe, each value on its own freshly
    seeded server (``docs/legacy-m9-tutorial.md`` §2.4):

    =========== ======== ==========================
    step sent   HTTP    ``completed_tutorial``
    =========== ======== ==========================
    ``-1``      200     ``0 -> 0``  declines
    ``0``       200     ``0 -> 0``  declines
    ``1``       200     ``0 -> 0``  declines
    ``14``      200     ``0 -> 0``  declines
    ``15``      200     ``0 -> 1``  **completes**
    ``15.0``    200     ``0 -> 1``  **completes** (a distinct wire value)
    ``16``      200     ``0 -> 0``  **declines — in the hole**
    ``24``      200     ``0 -> 0``  **declines — the hole's upper edge**
    ``true``    200     ``0 -> 0``  declines (``True`` satisfies neither arm)
    ``25``      200     ``0 -> 1``  **completes**
    ``10**9``   200     ``0 -> 1``  **completes** (no upper bound)
    =========== ======== ==========================

    So **steps 16 through 24 inclusive do not complete the tutorial**, there is
    **no upper bound** and **no lower bound**, and **no type check** is applied.
    The gate is recorded here as :data:`GATE_LOWER_ARM` / :data:`GATE_EXACT_ARM`
    and evaluated by exactly one named predicate, :func:`gate_satisfied`.  The
    hole is :data:`GATE_HOLE_LOW` … :data:`GATE_HOLE_HIGH`, recorded as data
    rather than described in prose, so a test can enumerate it.

    **The boundary arithmetic is ALREADY PINNED elsewhere and is NOT claimed as
    new work.**  ``tools/protocol-replay/test_protocol_replay.py:173-179``
    (``test_tutorial_boundaries``) covers steps 14, 15, 24, 25, 26, and -1 — but
    against a **stub oracle inside the replay harness**, not the executed legacy
    server, so it is not an executed-legacy oracle.  This module *references*
    that coverage (:data:`REPLAY_BOUNDARY_STEPS`) and adds the executed fixture,
    rather than presenting the table as new.

    **D2 — the three 500-raising input shapes are REFUSED, not reproduced
    (the one deliberate divergence).**  ``"15"`` (a string), a missing step
    (``[]``), and ``[null]`` each raise inside the branch — ``TypeError`` for the
    string comparison, ``IndexError`` for the missing argument — and escape as an
    unhandled **HTTP 500**.  This module raises :class:`EnvelopeError` with
    ``invalid_step``, ``missing_step``, and ``null_step`` instead.

    Three alternatives were considered and rejected.  Reproducing the 500 is
    rejected because a crash is not a behaviour and makes the contract
    untestable.  Coercing a malformed step to ``0`` — so it merely declines — is
    rejected because it invents a value the client never sent and hides a
    malformed request.  **Reproducing the flag silently and refusing loudly** is
    what is delivered instead.

    The divergence is confined to the **response**, and the state outcomes agree.
    That is checked, not asserted: executed evidence shows a raising step changed
    **zero** leaves even with a full client resource ladder attached
    (``docs/legacy-m9-tutorial.md`` §2.8), so the legacy crash discards the
    already-applied vector rather than persisting it.  The one case worth naming
    is a JSON ``true``: legacy treats it as ``True``, which satisfies neither
    arm, so it declines and leaves the flag alone; refusing it as a non-integer
    also leaves the flag alone.  Same state, different response.

    **D3 — ``tutorial_step`` is a LOCAL and is NEVER PERSISTED, so NO stored step,
    resume position, or progress ratio is introduced.**  Four quoted occurrences
    on three lines: bound from ``args[0]``, printed, compared twice.  Nothing
    writes it to ``save``.  **The legacy tutorial records a terminal boolean and
    nothing else.**  A partially-progressed save is therefore *unrepresentable*
    in the legacy save shape, which is also why the committed corpus holds no
    mid-tutorial save: all 31 village saves carry the key, 30 record ``1``, and
    the single ``0`` is ``villages/initial.json``, the new-player template.
    ``tests/saves/fresh-player.json`` records ``0`` too, so the ``0 -> 1``
    transition is genuinely exercisable and **no player state was fabricated**.

    **D4 — the derived vector is NEUTRAL and completion is derived server-side.**
    ``do_command`` applies each command's 8-slot vector **before** the branch
    (``command.py:40``; ``engine.apply_resources``, ``engine.py:251-271``) as
    ``max(current + delta, 0)`` per resource, so a client-sent vector is a
    client-trusted mint or burn on **this** command exactly as on any other.
    :func:`validate_vector` therefore refuses anything but the all-zero vector,
    and the endpoint's post-execution proof requires that **every** stored
    resource is **unchanged**.

    That proof is **non-tautological here**, and anchored: an executed-legacy
    transaction was captured in which **one** tutorial request moved **all seven**
    stored resources *and* the flag in the same call — step ``15`` with the
    ladder ``[101, 3, 7, 11, 13, 17, 19, 23]``, changing eight leaves, with slot
    0's ``unknown`` value correctly **absent** from the changed set because
    ``engine.py:253`` reads and discards it.  The same ladder also persists on a
    **non-completing** step (``24``), so the movement is a property of the
    client-sent vector rather than of completion.  The capture records that
    minting transaction as a second case so both directions are evidenced.

``completed_tutorial`` is **write-only** — one occurrence in the whole legacy
server, the write at ``command.py:65``, with **zero readers** in any of the
eleven modules: the **tenth** committed field in this project with no legacy
consumer, and the second write-only progression counter family after line 1's
research counters.  It reaches the client only because ``get_player_info.py:15``
includes the whole ``playerInfo`` dict wholesale — by dict inclusion, not by any
server-side naming of the field.

No committed tutorial content exists to derive from: ``tutorial`` has **zero**
occurrences in ``config/main.json`` at any depth and **zero** across all
normalized packages under ``packages/game-content/normalized``.  There is
therefore no committed step list, step count, gate definition, tutorial text, or
reward — and **none is invented here**.  The gate thresholds below are recorded
as the **legacy server's rule**; nothing here claims what the Flash client counts
as a step, because Flash is never executed in this repository.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, and
    ``EnvelopeError`` — so every delivered derivation, its fixture, and its suite
    keep passing untouched.  A tutorial step has **no target cell and no
    footprint**, so ``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep
    the sibling modules' import shape identical (``expand_envelope`` and
    ``store_envelope`` do the same); nothing here validates a cell and that is
    not a gameplay claim.

No gameplay validation
    Legacy performs no ownership, state, or gameplay validation for this command:
    it will complete on step ``10**9`` if a client asks, and it will decline on
    step ``-1``.  This contract reproduces those absences rather than closing
    them — a bound the legacy server does not have would be an invented rule, and
    authoritative validation belongs to Server v1 (M13).

Provenance: established versus derived
    **Established** from committed legacy source, the committed command catalog,
    the committed corpus, and **40 executed-legacy probe transactions** (28 of
    them conclusive): that ``complete_tutorial`` takes ``args[0]`` as the step;
    that the gate is the recorded disjunction with the nine-value hole and no
    bounds and no type check; that the flag is written once with the value ``1``
    into the save-level ``playerInfo`` record and read by nothing; that the step
    is never persisted; that the client-sent 8-slot vector is applied before the
    branch; that a raising step answers an unhandled 500 and changes nothing;
    that the branch's ``return`` does **not** abort the rest of the batch; and
    the corpus facts recorded under :data:`COMMITTED_FLAG_BEFORE` and
    :data:`COMMITTED_PLACEMENTS`.

    **Derived-provisional and never observed from the Flash client**: that the
    Flash client ever sends a step at all, and that it counts steps the way the
    gate implies.  The request's exact shape is derived; its effect is
    established.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

# One shared derivation.  The placement module is imported unchanged — nothing
# here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    GRID_EXTENT,
    data_field,
    in_grid,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# The single legacy command this deliver line executes (established,
# command.py:60; the ``complete_tutorial`` row of
# docs/legacy-protocol/commands.json).
COMPLETE_TUTORIAL_COMMAND = "complete_tutorial"

# The save-level record the flag lives in, and the flag's own name (established,
# command.py:65).  ``maps[0]`` has no such key at all, which is why the endpoint
# reads and proves the flag through the player record.
PLAYER_INFO_RECORD = "playerInfo"
FLAG_KEY = "completed_tutorial"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# Design D1 — the committed gate, as data.  Both arms are recorded separately so
# a test can enumerate them and a future line can supersede one without
# re-deriving the other.
GATE_LOWER_ARM = 25
GATE_EXACT_ARM = 15

# The nine values between the arms that the gate does NOT complete.  Recorded as
# data rather than prose so the hole is machine-checkable; the range is
# inclusive at both ends and is exactly ``GATE_EXACT_ARM + 1`` …
# ``GATE_LOWER_ARM - 1``.
GATE_HOLE_LOW = GATE_EXACT_ARM + 1
GATE_HOLE_HIGH = GATE_LOWER_ARM - 1
GATE_HOLE_SIZE = GATE_HOLE_HIGH - GATE_HOLE_LOW + 1

# The absent bounds, recorded as data so the absence is assertable rather than
# merely described.  Legacy clamps neither and checks neither.
GATE_HAS_UPPER_BOUND = False
GATE_HAS_LOWER_BOUND = False
GATE_HAS_TYPE_CHECK = False

# The steps already covered by the committed replay-harness boundary test
# (tools/protocol-replay/test_protocol_replay.py:173-179).  Referenced, NOT
# reimplemented: that test runs against a stub oracle inside the harness, so it
# is not an executed-legacy oracle and this line adds the executed fixture beside
# it rather than claiming the table as new work.
REPLAY_BOUNDARY_STEPS: Tuple[int, ...] = (14, 15, 24, 25, 26, -1)
REPLAY_ORACLE_IS_EXECUTED_LEGACY = False

# The committed corpus facts, pinned here AND cross-checked against the real
# seed by the capture and the offline tests, so a corpus drift fails the run
# instead of publishing a different fixture.
COMMITTED_FLAG_BEFORE = 0
COMMITTED_FLAG_AFTER = 1
COMMITTED_PLACEMENTS = 40
COMMITTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}

# Design D2 — the three input shapes the legacy branch answers with an unhandled
# HTTP 500.  Named here so the endpoint's refusals and the divergence record
# cannot drift from the list.
LEGACY_RAISING_SHAPES: Tuple[str, ...] = ("string_step", "missing_step", "null_step")
LEGACY_RAISING_STATUS = 500

# Design D4 — the executed-legacy transaction in which ONE tutorial request moved
# all seven stored resources alongside the flag.  Recorded as data so the
# endpoint's "nothing moved" proof is anchored to a real observation rather than
# to a claim about one.
MINTING_LADDER: Tuple[int, ...] = (101, 3, 7, 11, 13, 17, 19, 23)
MINTING_STEP = GATE_EXACT_ARM
MINTING_RESOURCES_MOVED = 7
MINTING_CHANGED_LEAVES = 8

# The eleven root modules the committed investigation swept for the tutorial
# vocabulary, with the one module that writes the flag.  Recorded so a later line
# can re-run the same sweep and compare rather than trust this note.
LEGACY_MODULES: Tuple[str, ...] = (
    "auctions.py",
    "bundle.py",
    "command.py",
    "constants.py",
    "engine.py",
    "get_game_config.py",
    "get_player_info.py",
    "legacy_command_recorder.py",
    "server.py",
    "sessions.py",
    "version.py",
)
TUTORIAL_OCCURRENCES = 6
TUTORIAL_OCCURRENCE_LINES = 5
FLAG_OCCURRENCES = 1
STEP_OCCURRENCES = 4
#: ``get_player_info.py`` line 15 includes the whole ``playerInfo`` dict, which is
#: the only reason the flag reaches the client at all.
FLAG_CLIENT_VIA_WHOLE_DICT_LINE = 15

#: The flag has exactly one writer and zero readers, in any of the eleven modules.
FLAG_WRITER_LINES = ("command.py:65",)
FLAG_READER_COUNT = 0

#: The corpus census the committed investigation measured.
CORPUS_VILLAGE_SAVES = 31
CORPUS_SAVES_RECORDING_COMPLETE = 30
CORPUS_ONLY_INCOMPLETE_SAVE = "villages/initial.json"

#: Zero committed tutorial content, at any depth, anywhere.
COMMITTED_CONTENT_OCCURRENCES = 0
COMMITTED_CONTENT_FILES_CHECKED = 20

__all__ = [
    "COMMITTED_CONTENT_FILES_CHECKED",
    "COMMITTED_CONTENT_OCCURRENCES",
    "COMMITTED_FLAG_AFTER",
    "COMMITTED_FLAG_BEFORE",
    "COMMITTED_PLACEMENTS",
    "COMMITTED_RESOURCE_BEFORE",
    "CORPUS_ONLY_INCOMPLETE_SAVE",
    "CORPUS_SAVES_RECORDING_COMPLETE",
    "CORPUS_VILLAGE_SAVES",
    "COMPLETE_TUTORIAL_COMMAND",
    "ENVELOPE_KEYS",
    "FLAG_CLIENT_VIA_WHOLE_DICT_LINE",
    "FLAG_KEY",
    "FLAG_OCCURRENCES",
    "FLAG_READER_COUNT",
    "FLAG_WRITER_LINES",
    "GATE_EXACT_ARM",
    "GATE_HAS_LOWER_BOUND",
    "GATE_HAS_TYPE_CHECK",
    "GATE_HAS_UPPER_BOUND",
    "GATE_HOLE_HIGH",
    "GATE_HOLE_LOW",
    "GATE_HOLE_SIZE",
    "GATE_LOWER_ARM",
    "LEGACY_MODULES",
    "LEGACY_RAISING_SHAPES",
    "LEGACY_RAISING_STATUS",
    "MINTING_CHANGED_LEAVES",
    "MINTING_LADDER",
    "MINTING_RESOURCES_MOVED",
    "MINTING_STEP",
    "PLAYER_INFO_RECORD",
    "REPLAY_BOUNDARY_STEPS",
    "REPLAY_ORACLE_IS_EXECUTED_LEGACY",
    "RESOURCE_VECTOR_SLOTS",
    "STEP_OCCURRENCES",
    "TUTORIAL_OCCURRENCES",
    "TUTORIAL_OCCURRENCE_LINES",
    "EnvelopeError",
    "build_envelope",
    "completed_flag",
    "data_field",
    "gate_hole_steps",
    "gate_record",
    "gate_satisfied",
    "gate_verdict",
    "in_grid",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
    "project_tutorial_state",
    "step_kind",
    "validate_step",
    "validate_vector",
]


# --------------------------------------------------- the one named predicate --
def validate_step(step: Any) -> int:
    """Validate a client-supplied tutorial step and return it as an integer.

    The step is legitimate **intent** — "I reached step N" — so it is accepted;
    what is refused is a value this contract cannot compare.  Three named
    refusals, one per legacy 500-raising shape (design **D2**), each raised before
    anything is derived or executed:

    * ``missing_step`` — the step key is absent, which is legacy's ``args[0]``
      ``IndexError``;
    * ``null_step`` — the step is JSON ``null``;
    * ``invalid_step`` — anything else that is not an integer, which is legacy's
      ``TypeError`` on the comparison.

    A ``bool`` is refused as ``invalid_step``: ``True`` is an ``int`` in Python
    and would silently satisfy neither gate arm, so accepting it would carry a
    value whose wire type the contract does not model.  Legacy *declines* a
    ``true`` and so does this refusal — **the state outcome is identical and only
    the response differs**, which is the confinement design D2 claims.

    A **float** is also refused, though legacy would accept ``15.0`` and complete
    on it (``15.0 == 15`` is ``True``).  Refusing it is the same confinement: a
    float step leaves the flag untouched here, and a declined ``15.0`` leaves it
    untouched there.  The measured fact is recorded as
    :data:`LEGACY_ACCEPTS_FLOAT_STEP` rather than reproduced.
    """
    if step is None:
        raise EnvelopeError("null_step", "step must be an integer, got null")
    if isinstance(step, bool) or not isinstance(step, int):
        # One vocabulary with :func:`step_kind`, so a refusal and a report name
        # the same wire kind rather than a Python class name.
        raise EnvelopeError(
            "invalid_step",
            "step must be an integer, got %s" % step_kind(step),
        )
    return int(step)


def require_step(payload: Any) -> int:
    """The step a validated request body carries, or a named refusal.

    Separated from :func:`validate_step` because the **absence** of the key is a
    different failure from a present-but-wrong value, and the endpoint must be
    able to tell the two apart to report ``missing_step`` rather than
    ``invalid_step``.
    """
    if not isinstance(payload, dict):
        raise EnvelopeError("invalid_payload", "request body must be a JSON object")
    if STEP_KEY not in payload:
        raise EnvelopeError("missing_step", "step is required")
    return validate_step(payload[STEP_KEY])


#: The single request key the operation reads.  Nothing else is consulted, which
#: is what makes the operation intent-only: no outcome, no stored flag, and no
#: resource vector can arrive.
STEP_KEY = "step"

#: Measured, not reproduced: legacy's gate is a Python comparison, so a float
#: ``15.0`` completes it (``15.0 == 15``).  Recorded because it is the one wire
#: type whose legacy outcome differs from this contract's refusal in *no* way
#: that reaches the save.
LEGACY_ACCEPTS_FLOAT_STEP = True


# --------------------------------------------------------- the named gate ----
def gate_satisfied(step: Any) -> bool:
    """``True`` when the committed gate completes the tutorial for ``step``.

    **This is the one named place the gate exists.**  It evaluates the committed
    disjunction exactly as legacy does — ``step >= 25 or step == 15`` — and
    nothing else.  Every caller (the endpoint, the capture, the offline tests, and
    the client-side mirror) resolves a step through this function, so a future
    revision of the thresholds is **one** edit rather than an audit.

    :func:`validate_step` is deliberately **not** called here: this predicate
    answers "does the gate fire for this value", and the input domain is a
    separate question the caller settles first.  It is nonetheless **total** — it
    returns ``False`` for every value that is not a strict integer rather than
    raising ``TypeError`` — so a caller can never crash on an unvalidated value,
    and so the predicate is a safe mirror for the client, which parses every JSON
    number as a float.

    **What totality costs, stated plainly.**  For a non-integer this predicate is
    **not** a reproduction of legacy, and must not be read as one.  Legacy raises
    ``TypeError`` on a string (escaping as HTTP 500) and on ``None``; it *accepts
    and completes* a float ``15.0``, because ``15.0 == 15``.  Returning ``False``
    for a float therefore reports the outcome this contract **refuses**, which is
    the same state outcome legacy's own completion would leave here (the flag is
    untouched, since the refusal precedes any dispatch) but is not the outcome
    legacy's save would hold.  :data:`LEGACY_ACCEPTS_FLOAT_STEP` records the
    measured legacy fact, and no caller may consult this predicate for a
    non-integer without :func:`validate_step` having settled the type first.
    """
    if not is_strict_int(step):
        return False
    return step >= GATE_LOWER_ARM or step == GATE_EXACT_ARM


def gate_verdict(step: Any) -> str:
    """Which arm of the disjunction fires for ``step``, or ``"none"``.

    A named reporting helper so the two arms can be told apart in a report and in
    a fixture record, instead of a bare boolean hiding which arm applied.  Returns
    ``"lower_arm"``, ``"exact_arm"``, or ``"none"``.

    Total over the same domain as :func:`gate_satisfied`, with the same caveat
    documented there: for a non-integer this reports what this contract refuses,
    not what legacy's comparison would have done.

    Note the ordering, which mirrors legacy's own ``or`` short-circuit: the
    ``>=`` arm is tested first, so a step satisfying **both** (``25`` and above)
    is reported as ``"lower_arm"``.
    """
    if not is_strict_int(step):
        return "none"
    if step >= GATE_LOWER_ARM:
        return "lower_arm"
    if step == GATE_EXACT_ARM:
        return "exact_arm"
    return "none"


def gate_hole_steps() -> List[int]:
    """Every step the committed gate does **not** complete, in ascending order.

    The nine values :data:`GATE_HOLE_LOW` … :data:`GATE_HOLE_HIGH`, computed from
    the two arm constants rather than typed out, so the list cannot drift from
    the thresholds it claims to describe.  Returned as a fresh list on every call.
    """
    return list(range(GATE_HOLE_LOW, GATE_HOLE_HIGH + 1))


def gate_record() -> Dict[str, Any]:
    """The committed gate as a reportable record, verbatim.

    Every field is a committed fact or an absence, and nothing is derived from
    another: both arms, the hole's bounds and size, the three absent properties,
    the three legacy 500-raising shapes, and the replay-harness coverage this line
    references rather than reclaims.  Used by the endpoint's answer, the capture
    manifest, and the client's report so the three cannot disagree.
    """
    return {
        "command": COMPLETE_TUTORIAL_COMMAND,
        "expression": "tutorial_step >= %d or tutorial_step == %d"
        % (GATE_LOWER_ARM, GATE_EXACT_ARM),
        "lower_arm": GATE_LOWER_ARM,
        "exact_arm": GATE_EXACT_ARM,
        "hole_low": GATE_HOLE_LOW,
        "hole_high": GATE_HOLE_HIGH,
        "hole_size": GATE_HOLE_SIZE,
        "hole_steps": gate_hole_steps(),
        "has_upper_bound": GATE_HAS_UPPER_BOUND,
        "has_lower_bound": GATE_HAS_LOWER_BOUND,
        "has_type_check": GATE_HAS_TYPE_CHECK,
        "raising_shapes": list(LEGACY_RAISING_SHAPES),
        "raising_status": LEGACY_RAISING_STATUS,
        "replay_boundary_steps": list(REPLAY_BOUNDARY_STEPS),
        "replay_oracle_is_executed_legacy": REPLAY_ORACLE_IS_EXECUTED_LEGACY,
    }


# ------------------------------------------------------------- projections ---
def completed_flag(player_info: Any) -> Optional[Any]:
    """The recorded completion flag from a ``playerInfo`` record, or ``None``.

    Returns the value **verbatim** — no coercion, no defaulting, no boolean
    folding — so a recorded ``1`` is reported as the integer ``1`` and a
    recorded ``0`` as ``0``, exactly as the save holds them.

    ``None`` means the flag could not be read as a stored value: the record is
    absent or not a mapping, or it carries no such key.  It is a **graceful
    refusal**, never an exception, and the caller turns it into a fail-closed
    answer rather than defaulting to "not complete" — defaulting would present an
    unreadable state as a resolved one, which is exactly what this line forbids.
    """
    if not isinstance(player_info, dict):
        return None
    if FLAG_KEY not in player_info:
        return None
    return player_info[FLAG_KEY]


def project_tutorial_state(player_info: Any) -> Dict[str, Any]:
    """A typed, read-only projection of one player's tutorial state.

    Deliberately carries **one** value.  It derives **no** step, **no** progress
    ratio, **no** remaining time, and **no** completion, because the legacy save
    stores **no step** (design **D3**) and a projection that derived one would be
    inventing the field the whole line refuses to invent.

    ``resolvable`` is ``False`` when the flag could not be read, and
    ``completed`` is then ``None`` — never ``False``.  The two are different
    claims: "the save says no" and "the save does not say", and collapsing them
    would make an unreadable state look like a decided one.
    """
    flag = completed_flag(player_info)
    if flag is None:
        return {
            "resolvable": False,
            "record": PLAYER_INFO_RECORD,
            "key": FLAG_KEY,
            "completed": None,
            "stored": None,
        }
    return {
        "resolvable": True,
        "record": PLAYER_INFO_RECORD,
        "key": FLAG_KEY,
        "completed": bool(flag),
        "stored": flag,
    }


def step_kind(step: Any) -> str:
    """The wire kind of a step value, named — used by the reports and refusals.

    ``"integer"``, ``"float"``, ``"boolean"``, ``"string"``, ``"null"``, or
    ``"missing"``.  Recorded so the two shapes legacy completes on (``15`` and
    ``15.0``) and this contract refuses can be described precisely rather than
    paraphrased.
    """
    if step is None:
        return "null"
    if isinstance(step, bool):
        return "boolean"
    if isinstance(step, int):
        return "integer"
    if isinstance(step, float):
        return "float"
    if isinstance(step, str):
        return "string"
    return type(step).__name__


# --------------------------------------------------------- derived vector ----
def neutral_vector() -> List[int]:
    """The derived 8-slot ``resources_changed`` for a tutorial step: all zeros.

    Design **D4**.  Completing a tutorial moves no resource — there is no
    committed reward of any kind — so the only honest vector is the neutral one.
    A fresh list on every call, so a caller can never mutate the derivation for
    the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal.  This is the line's sharpest
    refusal: ``complete_tutorial`` is dispatched with a client-sent vector like
    every other command, and an executed-legacy transaction exists in which the
    **same command** moved all seven stored resources alongside the flag.  Legacy
    adds each slot to the stored balance as ``max(current + delta, 0)``, so a
    positive entry is a client-trusted **mint** and a negative one a
    client-trusted **burn**.  Refusing anything but zero here is what forecloses
    it: the derivation cannot express the vector, so the endpoint cannot send it.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be an integer, got %r" % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d is %r: a tutorial step moves no resource, "
                "so only the neutral all-zero vector is derivable" % (index, value),
            )
    return list(vector)


# --------------------------------------------------------------- envelope ----
def build_envelope(
    step: Any,
    vector: Any = None,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``complete_tutorial`` command.

    ``step`` is the client's **intent** and the **only** thing this envelope can
    carry.  It is validated by :func:`validate_step`, so a non-integer, a missing
    step, and a ``None`` step are all refused here with their named codes before
    anything is derived — the same three shapes legacy answers with an unhandled
    500, refused rather than reproduced (design **D2**).

    No upper or lower bound is applied to a step that **is** an integer.  Legacy
    has none, and a bound it does not have would be an invented rule: ``10**9``
    completes in legacy and is accepted here for the same reason, and ``-1``
    declines in both.

    ``vector`` defaults to the neutral :func:`neutral_vector` and is validated by
    :func:`validate_vector`, so a caller supplying one must supply the neutral
    one (design **D4**).  ``ts`` defaults to the current time; it is parsed and
    then unread by legacy code, so parity normalizes it.

    The batch carries **exactly one** command: ``[0, "complete_tutorial",
    [step], vector]``.

    Raises :class:`EnvelopeError` with ``null_step``, ``invalid_step``,
    ``missing_step``, ``invalid_vector``, or ``invalid_timestamp``.
    """
    checked_step = validate_step(step)
    if vector is None:
        vector = neutral_vector()
    checked = validate_vector(vector)
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, COMPLETE_TUTORIAL_COMMAND, [checked_step], checked]],
    }