#!/usr/bin/env python3
"""Derivation of the legacy ``expand`` command envelope and its debit.

The town-expansion deliver line of M7, and the **second** line in this family
whose derived resource vector is deliberately *not* neutral: the committed
configuration prices an expansion (``expansion_prices``), so the service can
derive a real debit instead of refusing to invent one.  Unlike the collect
line, whose derived vector is a **credit** that can never reach legacy's
per-resource clamp, this line's debit **can** — the executed probe recorded in
``docs/legacy-town-expansion.md`` showed a client-sent ``-2500`` gold debit
against a ``2000`` balance landing on ``0`` rather than ``-500``.  That is the
first executed evidence in the family that the clamp is reachable, and it is
the strongest available argument for a *server-derived* price and for
refusing an unaffordable expansion instead of letting the clamp under-charge.

The client sends an *intent only* — a save id and the expansion id — and never
an amount, a resource, a price, a time, a requirement flag, or a resource
delta.  This module is the single place where that intent becomes the legacy
batch envelope, so the executed-legacy fixture capture
(``capture_expand_fixture.py``) and the Compatibility API ``POST /v0/expand``
endpoint are checked against *one* derivation, exactly as the placement,
purchase, move, sell, store, upgrade, construction, and collect deliver lines
already do.

Shared derivation: the serialization and structural helpers are imported
unchanged from :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
``payload_json``, ``data_field``, ``parse_data_field``, ``EnvelopeError``,
``GRID_EXTENT``, and ``in_grid`` — so every delivered derivation, its fixture,
and its suite keeps passing untouched.  An expansion has **no target cell and no
footprint**, so ``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep
the sibling modules' import shape identical (``store_envelope`` and
``move_envelope`` do the same); nothing here validates a cell and that is not a
gameplay claim.  See "No land, grid, or cell effect" below.

What legacy actually does (established)
    ``command.expand`` takes exactly one positional argument, coerces it with
    ``int()``, and appends it to ``map["expansions"]`` — nothing else
    (``command.py:211-216``; the ``expand`` row of
    ``docs/legacy-protocol/commands.json`` and ``commands.md``).  The **price
    is not computed by the server at all**: ``engine.apply_resources`` runs
    *before* the branch (``command.py:40``, ``engine.py:251-271``) and applies
    the client-sent 8-slot vector ``[unknown, xp, gold, wood, oil, steel, cash,
    mana]`` verbatim, per resource, as ``max(current + delta, 0)``.  Nothing in
    the legacy server reads, validates, prices, orders, or deduplicates
    ``map["expansions"]``: a repository-wide search finds exactly three
    references to the word in the whole server, all three inside that branch.
    The committed command catalog records the same and adds the security note
    "client unlocks any expansion id; no adjacency, level, or cost
    verification".

The four derivation decisions (design D1, D2, D3, D6)
    **D1 — the price comes from ``expansion_prices``, indexed by the expansion
    id itself (derived).**  Three readings were in competition: the 98-entry
    ``expansion_prices`` schedule indexed by the id sent to ``expand``; the
    4-entry ``town_prices`` / ``map_prices`` schedules indexed by town level;
    or the count of expansions already owned.  The decisive evidence is the
    corpus's own value: ``[35, 36, 45, 46]`` is a valid ``expansion_prices``
    index (``0..97``), is **not** a valid ``town_prices`` / ``map_prices``
    index (``0..3``), and is **not** a level set either — the schedules'
    ``level`` values are ``15, 25, 35, 45``, and while ``35`` and ``45``
    appear in the owned list, ``36`` and ``46`` do not.  So the owned list is
    read as ids into the positional table.  *Rejected alternatives:* indexing
    the four-entry schedules by level, and indexing by
    ``len(map["expansions"])``.

    This is a **derivation, and the executed probe is exactly why**: the server
    accepted ``expand(999)``, a duplicate ``expand(35)``, and ``expand(-1)``
    alike, all answering success, so the server offers **no** evidence to
    arbitrate the id space and the question cannot be settled by observing it.
    Two consequences are carried explicitly.  First, a level-1 fresh player
    owning four saturated-price (``coins 100000``) expansions is not a coherent
    game state; that is recorded as a reason to distrust the reading, and it is
    why the claim stops at "the price the committed table assigns to the id",
    never at "the price a coherent player would pay".  Second, because the
    server does not range-check, :func:`price_for` refuses an id outside the
    schedule and the endpoint answers ``unknown_expansion_id`` — otherwise a
    client could buy expansion ``999`` for a price derived from a table that has
    no entry ``999``.  A duplicate is refused the same way
    (``already_expanded``), because legacy neither deduplicates nor orders and a
    repeated id would silently corrupt the ledger.

    **D2 — ``coins`` is the client's ``gold``, and lands in server slot 2
    (established by committed client asset evidence).**  The asset registry
    carries ``assets/images/en/expansion_gold.jpg`` **and**
    ``assets/images/en/expansion_cash.jpg`` — two distinct committed images,
    the expansion popup's two price components — and the client's own icon for
    one of them is named ``gold`` while the other is named ``cash``.  So the
    schedule's word-named ``coins`` field is the client's ``gold`` and the
    server's ``gold`` slot (``engine.py:259``, ``map["gold"]``) is the target;
    ``cash`` is unambiguous (slot 6, ``playerInfo.cash``).  The derived vector
    for an expansion priced ``coins C, cash K`` is ``[0, 0, -C, 0, 0, 0, -K,
    0]``, and a zero-priced expansion derives the all-zero vector — **legal**,
    because the free expansions ``0..3`` exist in the committed table.

    A vocabulary note, so the two namings are not mistaken for a slip: the
    committed configuration uses **two** resource namings.  ``items[].costs``
    uses the *letter* set (``g``, ``c``, ``w``, ``s``, ``o`` — 279/375/128/110/69
    occurrences), while the price schedules use the *word* set (``coins``,
    ``cash``).  A word-keyed price field is therefore a second naming layer, and
    the bridge between the layers is the client's own committed asset name, not
    an inference about which resource "coins" *might* be.

    **D3 — the ``neighbors`` and ``inventory_qte`` requirements are refused,
    never invented (derived).**  The server ignores both.  Nothing any
    delivered surface can currently read can evaluate either: no neighbour
    count and no inventory quantity is exposed by the delivered bootstrap, the
    client's ``GameApi``, or the corpus.  The collect line's precedent is to
    refuse rather than guess, and it applies unchanged, so
    :func:`unmet_requirements` reports every field whose recorded value is not
    a usable zero and the endpoint answers ``expansion_requirements_unmet``
    (409) **before** the dispatcher runs.  *Rejected alternatives:* enforcing a
    neighbour count or an inventory quantity from state nothing delivers, and
    ignoring the requirement.

    This has a striking, honest consequence on the committed corpus that the
    tests assert rather than hide: **every id the corpus owns (``35, 36, 45,
    46``) records ``neighbors 15`` and ``inventory_qte 30``, so none of them
    could have been bought under this rule, and the only purchasable entries in
    the whole 98-row schedule are the free ones — indexes ``0..3``, priced
    ``0`` coins and ``0`` cash.**  94 of the 98 rows record a positive
    requirement.  The line therefore delivers a real **zero-cost** expansion on
    this corpus and refuses the priced ones, which is the correct outcome under
    the evidence and the wrong outcome for gameplay; it is recorded as a claim
    limit rather than patched by lowering the bar.

    **D6 — an insufficient balance fails closed rather than reproducing the
    clamp (derived).**  Two options were available.  Reproducing the clamp is
    what every earlier line does, because their prices were client-sent and
    there was nothing to compare against.  Here the debit is **server-derived**,
    so the endpoint can know whether the balance covers it, and silently
    under-charging to the clamp would make the post-execution proof ambiguous
    (the balance moved by less than the derived debit, which is indistinguishable
    from a bug).  So an insufficient balance fails closed
    ``insufficient_resources`` (409) before execution.  *Rejected alternative:*
    reproducing the clamp.  The clamp's own reachability — established by the
    probe — is what makes this the safer choice rather than an arbitrary one.

The vector is a debit, and a wrong derivation mints or burns resources
    Every slot this derivation fills is ``0`` or **negative**: legacy adds the
    vector to the stored balance, so a positive entry is a **mint** and a
    wrong negative magnitude is a **burn** — a client-trusted one, because the
    value travels in the envelope this service composes.  That is why
    :func:`validate_vector` refuses any positive entry outright and why the
    endpoint's second post-execution proof half compares **every** stored
    resource against **exactly** the derived debit: a derivation that were
    wrong (in sign, in slot, or in magnitude) is *reported* as a fail-closed
    ``internal_error`` rather than returned as a success.  The probe below
    records the executed-legacy proof that a client-sent debit larger than the
    balance is applied **short** of the requested amount (the clamp), which is
    exactly the ambiguity the proof exists to make impossible to hide.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  The batch carries **exactly
    one** command.

No land, grid, or cell effect
    **No claim is made and none is implemented** that a bought expansion makes
    any area of the town buildable, enlarges the grid, adds a cell, or moves
    any placement bound.  The server's only effect is an ``int`` in a list, and
    **no committed source maps an expansion id to land geometry**: the committed
    evidence establishes the *vocabulary* — the SWF symbols
    ``PopupExpandMC`` and ``btnBuyExpandTileMC`` plus ``assets/images/en/
    expansion.png`` show the client's model is a purchasable **tile** bought
    through a popup, and ``expansion_gold.jpg`` / ``expansion_cash.jpg`` show
    the two price components — but the committed SWF inspection is
    symbols-and-tags only and its own scope statement disclaims timeline
    semantics, script behavior, and rendering, so the **tile → cell geometry is
    not derivable from the preserved evidence**.  This module therefore contains
    no terrain, grid, cell, footprint, bounds, or placement logic of any kind;
    it reads one committed price row and composes one command.  The gap is a
    known evidence gap that bounds visual land growth (design D4), named here
    and in the fixture README so a later change can close it with new evidence
    instead of rediscovering that it is missing.

No gameplay validation
    Ownership of an id, the level gate, adjacency, and the *order* in which
    expansions may be bought are **not** enforced here beyond the two guards the
    server omits and the evidence demands (the schedule range and the
    duplicate); no branch reads ``expansion_prices``, ``town_prices``, or
    ``map_prices``, and legacy performs no validation of any kind.  Offering the
    action is the client's job, and authoritative validation belongs to Server v1
    (M13).

Provenance: established versus derived
    **Established** from committed legacy source, executed-legacy probes, and
    committed asset evidence: the command's argument shape and its single effect
    (``map["expansions"] += [int(expansion)]``); that the price is the
    client-sent vector applied verbatim per resource under the
    ``max(…, 0)`` clamp; that the clamp is **reachable** (a ``-2500`` gold debit
    against a ``2000`` balance landed on ``0``); that the server accepts an
    out-of-range id (``999``), a duplicate id (``35``), and a negative id
    (``-1``) alike, all answering success, and raises an unhandled HTTP 500 on a
    non-integer id; the committed ``expansion_prices`` / ``town_prices`` /
    ``map_prices`` schedules and their census; the committed images naming the
    expansion price's gold and cash components; and the corpus facts (a level-1
    fresh player whose ``expansions`` is ``[35, 36, 45, 46]``, 40 placements,
    ``xp 4`` / ``gold 2000`` / ``wood 2000`` / ``oil 2000`` / ``steel 2000`` /
    ``cash 5`` / ``mana 0``, empty storage, level 1).  **Derived and never
    observed from the Flash client**: D1, D3, D6 above, and the debit's sign
    and shape.  Flash is never executed in this repository, so the claim is that
    a debit is derived from the committed schedule row the id names, never that
    it is the price a coherent player pays.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
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
# command.py:211-216).
EXPAND_COMMAND = "expand"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The two price components a committed expansion row can name, and the vector
# slot each one lands in (design D2).  ``coins`` is the client's ``gold`` —
# established by the committed assets ``expansion_gold.jpg`` and
# ``expansion_cash.jpg``, the expansion popup's two price components — and
# ``cash`` is unambiguous.
PRICE_GOLD_FIELD = "coins"
PRICE_CASH_FIELD = "cash"
GOLD_SLOT = 2
CASH_SLOT = 6
PRICE_FIELDS = (PRICE_GOLD_FIELD, PRICE_CASH_FIELD)

# The two requirement fields a committed row may carry (design D3).  Nothing
# the delivered stack can read evaluates either, so a row recording a positive
# one is refused rather than paid under an invented rule.
NEIGHBORS_FIELD = "neighbors"
INVENTORY_QTE_FIELD = "inventory_qte"
REQUIREMENT_FIELDS = (NEIGHBORS_FIELD, INVENTORY_QTE_FIELD)

# Every field the committed census records on a row of ``expansion_prices``
# ("coins"/"cash"/"neighbors"/"inventory_qte" on all 98 stored entries).
COMMITTED_ROW_FIELDS = PRICE_FIELDS + REQUIREMENT_FIELDS

# The slots this derivation can never fill.  Slot 0 is unread by every branch
# and no expansion price names experience, wood, oil, steel, or mana, so slots
# 1, 3, 4, 5, and 7 are structurally zero; asserted by the suite and enforced
# by :func:`resource_vector_for` and :func:`validate_vector` themselves.
ALWAYS_ZERO_SLOTS = (0, 1, 3, 4, 5, 7)

# The two slots a derived debit can fill.
DEBIT_SLOTS: Dict[str, int] = {
    PRICE_GOLD_FIELD: GOLD_SLOT,
    PRICE_CASH_FIELD: CASH_SLOT,
}

# The committed corpus's own owned-expansions list, and the four indexes the
# committed schedule prices at zero.  Both are cross-checked against the real
# config and the real save by the suite; they are recorded here so the
# derivation's own tests can state the facts they depend on.
COMMITTED_FREE_INDEXES = (0, 1, 2, 3)
COMMITTED_SCHEDULE_LENGTH = 98
COMMITTED_OWNED_EXPANSIONS = (35, 36, 45, 46)

__all__ = [
    "ALWAYS_ZERO_SLOTS",
    "CASH_SLOT",
    "COMMITTED_FREE_INDEXES",
    "COMMITTED_OWNED_EXPANSIONS",
    "COMMITTED_ROW_FIELDS",
    "COMMITTED_SCHEDULE_LENGTH",
    "DEBIT_SLOTS",
    "ENVELOPE_KEYS",
    "EXPAND_COMMAND",
    "EnvelopeError",
    "GOLD_SLOT",
    "GRID_EXTENT",
    "INVENTORY_QTE_FIELD",
    "NEIGHBORS_FIELD",
    "PRICE_CASH_FIELD",
    "PRICE_FIELDS",
    "PRICE_GOLD_FIELD",
    "RESOURCE_VECTOR_SLOTS",
    "build_envelope",
    "data_field",
    "in_grid",
    "is_strict_int",
    "parse_data_field",
    "payload_json",
    "price_for",
    "resource_vector_for",
    "row_snapshot",
    "schedule_length",
    "unmet_requirements",
    "validate_vector",
]


def schedule_length(schedule: Any) -> Optional[int]:
    """The committed schedule's length, or ``None`` if it is not a schedule.

    A schedule is a non-empty sequence of committed rows; a string, a mapping,
    or an empty sequence is "not a schedule" here and is reported by the
    caller's own refusal rather than coerced into a length.  The range rule of
    design **D1** is expressed in exactly one place — ``0 <= expansion_id <
    schedule_length(schedule)`` — so the pure derivation and the service's
    adapter accessor cannot disagree about the id space.
    """
    if isinstance(schedule, (str, bytes)) or not isinstance(schedule, Sequence):
        return None
    if not schedule:
        return None
    return len(schedule)


def price_for(expansion_id: Any, schedule: Any) -> Optional[Dict[str, Any]]:
    """The committed price row for ``expansion_id``, or ``None`` out of range.

    Design **D1**: the id indexes the 98-entry positional
    ``expansion_prices`` schedule, and an id outside it is **refused** rather
    than priced — the legacy server does no range check at all (it accepted
    ``expand(999)`` answering success), so refusing here is the only thing that
    keeps an unsupported id from being bought at a price no committed row
    states.  ``None`` therefore means exactly "the committed schedule has no
    row for this id", and the caller turns it into the structured
    ``unknown_expansion_id`` conflict.

    A non-integer id is a different failure and raises with
    ``invalid_expansion_id``: ``command.expand`` would raise ``int("abc")`` out
    of the branch and the legacy route answers an unhandled HTTP 500, so this
    contract never lets one reach the dispatcher.

    The row is returned **verbatim** as a shallow copy — no coercion, no
    defaulting — so the requirement rule (design D3) and the cost rule
    (design D2) are applied by :func:`unmet_requirements` and
    :func:`resource_vector_for` where the shape rules live.  A row that is not
    a mapping is returned as it is and refused by those helpers with
    ``invalid_price``; a real corpus has all 98 rows as mappings.

    Raises :class:`EnvelopeError` with ``invalid_expansion_id``.
    """
    if not is_strict_int(expansion_id):
        raise EnvelopeError(
            "invalid_expansion_id",
            "expansion_id must be an integer, got %s" % type(expansion_id).__name__,
        )
    length = schedule_length(schedule)
    if length is None:
        raise EnvelopeError(
            "invalid_price", "the committed expansion schedule is not a sequence of rows"
        )
    if expansion_id < 0 or expansion_id >= length:
        return None
    row = schedule[expansion_id]  # type: ignore[index]
    if isinstance(row, Mapping):
        return dict(row)
    return row  # type: ignore[return-value]


def unmet_requirements(row: Any) -> List[str]:
    """The requirement fields a committed row records, in the committed order.

    Design **D3**: a row is purchasable only when **both** ``neighbors`` and
    ``inventory_qte`` record a usable zero.  A field is reported as unmet when
    its recorded value is a **positive** integer, and equally when it is a
    value this contract cannot read as a zero at all — absent is the only
    exception, because a row that records no requirement has none.  Failing
    closed on an unusable value is deliberate: a requirement this service
    cannot evaluate must never be silently treated as satisfied.

    A row that is not a mapping fails closed with ``invalid_price`` rather than
    reporting "no unmet requirements" for content it could not read.

    Raises :class:`EnvelopeError` with ``invalid_price``.
    """
    if not isinstance(row, Mapping):
        raise EnvelopeError(
            "invalid_price",
            "a committed expansion price row must be a mapping, got %s"
            % type(row).__name__,
        )
    unmet: List[str] = []
    for field in REQUIREMENT_FIELDS:
        if field not in row:
            continue
        value = row[field]
        if value is None:
            continue
        if is_strict_int(value) and value == 0:
            continue
        unmet.append(field)
    return unmet


def _committed_cost(row: Mapping[Any, Any], field: str) -> int:
    """One committed cost as a non-negative ``int``, or a refusal.

    A missing field, a ``bool``, a non-integer, and a **negative** amount are
    all refusals: a negative cost would put a *positive* entry on the legacy
    vector, which is a client-trusted **mint** and exactly the shape
    :func:`validate_vector` refuses to send.  A resolved ``0`` is a real value
    here — the free expansions ``0..3`` record ``coins 0`` and ``cash 0`` — and
    it is what makes the derived debit the all-zero vector.
    """
    if field not in row:
        raise EnvelopeError(
            "invalid_cost",
            "the committed expansion price records no %r component" % (field,),
        )
    value = row[field]
    if not is_strict_int(value):
        raise EnvelopeError(
            "invalid_cost",
            "the committed %s cost must be an integer, got %s"
            % (field, type(value).__name__),
        )
    if value < 0:
        raise EnvelopeError(
            "invalid_cost",
            "the committed %s cost must not be negative, got %r" % (field, value),
        )
    return int(value)


def resource_vector_for(row: Any) -> List[int]:
    """The derived 8-slot ``resources_changed`` **debit** for one expansion.

    Design **D2**: the row's ``coins`` lands in the gold slot and its ``cash``
    in the cash slot, each as a **negative** delta, so a priced expansion is a
    debit and a free one is the all-zero vector.  The requirement fields are
    deliberately **not** read here: they are not a price, and applying one
    would be the invented requirement rule design D3 refuses.  An id whose row
    is blocked is refused by :func:`unmet_requirements` before this runs.

    A fresh list on every call, so a caller can never mutate the derivation
    for the next one.  Raises :class:`EnvelopeError` with ``invalid_price`` for
    a row that is not a mapping, and ``invalid_cost`` for a missing, boolean,
    non-integer, or negative cost.
    """
    if not isinstance(row, Mapping):
        raise EnvelopeError(
            "invalid_price",
            "a committed expansion price row must be a mapping, got %s"
            % type(row).__name__,
        )
    vector = [0] * RESOURCE_VECTOR_SLOTS
    for field, slot in sorted(DEBIT_SLOTS.items()):
        vector[slot] = -_committed_cost(row, field)
    # Belt and braces: the six slots this derivation can never fill.
    for index in ALWAYS_ZERO_SLOTS:
        vector[index] = 0
    return vector


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` **debit** before it is sent.

    The vector must be a list of exactly eight **non-positive** integers.
    Legacy adds each slot to the stored balance, so a positive entry is a
    client-trusted mint and a negative magnitude is a client-trusted burn; both
    are derivation failures here, never values this contract will send.  The
    six slots this derivation can never fill must be exactly ``0``.  A list
    that is otherwise a valid debit still fails closed with ``invalid_vector``
    rather than being sent.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value) or value > 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be a non-positive integer (the "
                "vector is a debit), got %r" % (index, value),
            )
        if index in ALWAYS_ZERO_SLOTS and value != 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d is a slot this derivation can never "
                "fill, got %r" % (index, value),
            )
    return list(vector)


def build_envelope(
    expansion_id: Any,
    vector: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``expand`` command.

    ``expansion_id`` is the expansion id as an integer; whether it indexes the
    committed schedule and whether the player already owns it are **not**
    checked here (the endpoint resolves both against the corpus before
    executing, and legacy's ``expand`` is a silent no-op on neither — it
    appends whatever int it is given).  ``vector`` is the derived debit from
    :func:`resource_vector_for` — never a client value.

    Raises :class:`EnvelopeError` with ``invalid_expansion_id``,
    ``invalid_vector``, or ``invalid_timestamp``.
    """
    if not is_strict_int(expansion_id):
        raise EnvelopeError(
            "invalid_expansion_id",
            "expansion_id must be an integer, got %s" % type(expansion_id).__name__,
        )
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
        "commands": [[0, EXPAND_COMMAND, [expansion_id], checked]],
    }


# ------------------------------------------------------------------ helpers --
def row_snapshot(row: Any) -> Tuple[Any, ...]:
    """A comparable, order-stable snapshot of a committed row.

    Used by the capture tool's pre-publish checks and by the offline tests, so
    a row is compared by its **committed field values in the committed field
    order** rather than by mapping iteration order.  A row that is not a
    mapping is returned as a one-element tuple carrying its type name, so a
    malformed row is still *reported* rather than raising out of a check.
    """
    if not isinstance(row, Mapping):
        return ("<%s>" % type(row).__name__,)
    return tuple((field, row.get(field)) for field in COMMITTED_ROW_FIELDS)
