#!/usr/bin/env python3
"""The magic-counter vertical slice: validate, derive a bounded increment, prove.

**The third action on the v1 boundary, and the first that moves no stored
resource at all.**  ``collect`` derives a payout and ``complete_collection``
derives a debit; this one derives a **counter**, and the refusal to charge
anything is the finding rather than an omission (design D2).

The preserved branches it replaces (``command.py:652-663`` and ``664-675``) are
twelve lines and they perform no validation at all:

.. code-block:: python

    if command == "buy_magic":
        ...
        if str(magic_id) in privateState["magics"]:
            privateState["magics"][str(magic_id)] += min(50, ...)
        else:
            privateState["magics"][str(magic_id)] = 0

Four facts compose into the hole this slice closes, all measured before the
proposal rather than after:

====================================  ==========================================
fact                                   where
====================================  ==========================================
**no price is charged**: twelve        ``tests/fixtures/godot-damage/``, all
executed-legacy transactions moved     twelve steps, zero of eight slots
**zero** of eight resource slots
``min(50, …)`` bounds the              ``command.py:658`` and ``:670``
**increment**, so ``buy`` is unbounded
the identity is unvalidated;           ``str(magic_id)`` as a dict key
``str(magic_id)`` is the key
the absent-key arm writes **0**, not   the ``else`` arm of both branches
``1``
====================================  ==========================================

## The price is refused, and the refusal is the deliverable (design D2)

The committed magic table carries **four** numeric columns -- ``gold``, ``cash``,
``mana``, ``level`` -- and **none of them is named a price**.  There is no
``cashPrice``-style disambiguator, no ``prize`` beside it, and nothing anywhere
in the eleven legacy root modules that reads any of the four.  Three candidate
charges were each rejected against a measurement rather than a preference:

* ``gold`` -- the most expensive column (cheapest ``10000``) would refuse the
  fresh corpus 10 of 10 and make the route's success unreachable in the
  committed live phase;
* ``mana`` -- the column whose *name* matches a stored resource, whose meaning is
  least established, and which the fixture recorded **not** moving across a
  ``use_magic``;
* ``cash`` -- sits beside ``gold`` and ``mana`` with nothing to disambiguate it.

The decisive measurement is not an argument at all: the twelve executed-legacy
transactions in ``tests/fixtures/godot-damage/`` moved **zero** of the eight
resource slots ``engine.apply_resources`` unpacks, across both arms and every
identity the fixture sent.  A charge of any size therefore contradicts recorded
evidence rather than merely lacking support for it.

So there is no price in this module, and -- this is the part that is easy to get
wrong -- there is also **no mechanism** by which a legacy client could have paid
one: ``engine.apply_resources`` (``engine.py:251-271``) applies a
**client-sent** eight-slot vector at ``command.py:40``, before the first branch
condition at ``:42``, and v1 refuses that vector at the intent layer
(``client_supplied_delta``).

## The cap is the recorded literal ``50``, and a counter above it is refused (design D6)

The preserved source applies ``50`` with no reference to any content beside it,
and v1 uses the literal for the same reason ``godot-damage`` recorded: a
derivation from committed content would be an invention wearing the recorded
number's name.  **The rejected alternative is retained here**, in
:data:`COUNTER_CAP_PROVENANCE`, rather than deleted.

Both preserved asymmetries are refused:

* the counter does not grow without bound (``buy_magic``'s ``+=`` is unbounded);
* an operation never reduces an existing counter (``use_magic``'s ``=`` turns a
  counter of ``113`` into ``50``, which is a destruction wearing the assignment's
  clothes).

A recorded counter **already above** the cap is refused with
``counter_above_cap`` rather than clamped, because clamping with
``min(cap, before + 1)`` returns the cap -- that *is* the charge-destroying
decrease, in v1's clothes -- and leaving it alone would answer success for an
operation that changed nothing.

## Both operations are the same transition, and that is a finding (design D7)

The two preserved arms differ in exactly one token, and the difference is two
defects.  Remove both and the arms are identical, so v1 implements **one**
bounded transition and accepts both operation names for it.  The response says so
explicitly rather than letting a reader infer an oversight.

## What a counter *means* is unknown, and the naming records that (design D4)

Both arms **increase**.  Nothing in the preserved source ever **decreases** a
``magics`` entry, and no branch reads the map.  "Charges" is therefore a derived
reading, and this line's own measurement is what makes it visibly so.  Every
identifier, field name, and refusal message here says **counter**, never charge,
spell count, or ownership flag.  A refused alternative recorded in the design
follows from the same fact: declining to operate on an identity the player has no
counter for would be a rule the preserved server has no statement of.

## The post-execution proof (design D9), two halves over four ordered checks

1. **The addressed ledger key equals the derived transition**, every
   unaddressed key is byte-identical and keeps its recorded position, and
   **exactly one** document leaf path changed.  *This half is a specification
   check, not an evidence claim:* v1 is the only implementation writing this save
   on this path, so comparing v1's written value against v1's derived value
   could not fail for an interesting reason.  It is presented as such rather than
   dressed as parity with the preserved branch, which is not executed here and
   which v1 diverges from by design on every ``buy`` and every absent key.
2. **Every one of the seven stored resources v1 knows about is byte-identical.**
   *This is the falsifiable half, and it is falsifiable because of D2:* each of
   the three rejected charges would move exactly one of the seven, so a charge of
   any size fails half 2.

All four properties are enforced on every execution; the **order** in which they
are enforced is ``addressed``, ``unaddressed``, ``resources``, ``leaf``, and that
order is itself a decision.  The resource half is enforced **third** so the half
D9 calls the evidence is also the half a *reported* violation names: a charge
moves a leaf outside the addressed key as well, so checking the leaf first would
report every injected charge as a leaf violation and leave the evidential half
reachable in theory but unreachable in practice.

One wording note, recorded because it is a **deviation from the requirement's
literal text**: that requirement says "exactly one stored leaf path changed", and
that is exactly what is enforced for every transition that moves the counter.  It
cannot hold at the cap, where the derived value equals the recorded one
(``min(50, before + 1)`` is ``50`` when ``before`` is ``50``) and the write
writes back the value it read -- which is what the preserved ``use_magic`` arm
does at that same recorded value.  The enforced property is therefore "**at most**
one leaf changed, and it is the addressed ledger key's", which is the part that
carries the weight;
:data:`~server_v1_outcomes.PRESERVED_MAGIC_BEHAVIOUR`'s ``same_number`` entry
states the agreement that makes the no-op faithful rather than invented.

Note the measured difference from ``godot-damage``, which compared **eight**
slots: the eight-slot vector's eighth target is read into ``unknown`` and never
written, so ``privateState.energy`` is not one of v1's seven.  That is a
difference between two layers, recorded rather than papered over.

A **refused** operation leaves the ledger, every other key, and all seven stored
resources byte-identical, because every refusal resolves before any write.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from server_v1_content import CommittedContent, ContentError
from server_v1_intent import INTENT_OPERATION_VALUES, Intent
from server_v1_outcomes import (
    PRESERVED_MAGIC_BEHAVIOUR,
    MagicSuccess,
    Outcome,
)
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES, RepositoryError, SaveRepository

ACTION = "magic"

#: The recorded cap, **a literal**, at ``command.py:658`` and ``:670``.
COUNTER_CAP = 50

#: The recorded literal's provenance and the derivation this line rejected.
#: Kept as data rather than as a comment so a test can assert the rejected
#: alternative is still declared (design D6).
COUNTER_CAP_PROVENANCE: Dict[str, Any] = {
    "cap": COUNTER_CAP,
    "cap_is": "the literal 50 in the preserved branches",
    "cap_lines": ["command.py:658", "command.py:670"],
    "applies_to": "the counter, as an upper bound on the derived transition",
    "rejected": "derive the cap from committed magics content",
    "why_rejected": (
        "the preserved source applies the literal with no content reference, and "
        "the coincidence is not evidence either way because the value 50 really "
        "does occur in the committed table: it is the cash price of magic 1 and "
        "the level of magic 5, one row each. So a content derivation could have "
        "returned this exact number -- the strongest possible coincidence -- and "
        "the only ground for the literal is still provenance: the source writes "
        "50 next to nothing else"
    ),
    "measured_50_in_committed_content": {
        "cash": [1],
        "level": [5],
        "mana": [],
        "gold": [],
        "target": [],
    },
}

#: The preserved branches' own recorded behaviour, per operation, as **data**.
#: There is deliberately no code here that reproduces a legacy value: the point
#: is for a client to be able to see the divergence, and a second derivation
#: living beside v1's would be exactly the "one place a derived value can be
#: born" rule design D8 in ``server_v1_refusals`` exists to prevent (design D7).
#:
#: A **projection** of two entries of
#: :data:`server_v1_outcomes.PRESERVED_MAGIC_BEHAVIOUR`, not a second
#: transcription of them.  The canonical table has to live on
#: ``server_v1_outcomes`` because that is the module this one imports, so
#: reading it is what keeps the response body and the refusal detail from saying
#: two different things about the same preserved arm.
PRESERVED_BRANCH_BEHAVIOUR: Dict[str, str] = {
    operation: PRESERVED_MAGIC_BEHAVIOUR[operation] for operation in ("buy", "use")
}

#: The preserved branches' absent-key arm, which is the fourth asymmetry and the
#: one the fresh corpus reaches first because its ledger is ``{}``.  Read from the
#: canonical table for the same reason as :data:`PRESERVED_BRANCH_BEHAVIOUR`.
PRESERVED_ABSENT_KEY_BEHAVIOUR: str = PRESERVED_MAGIC_BEHAVIOUR["absent_key"]

#: The committed columns this slice reports and the reason it reads none of them
#: to produce a value (design D2).  Declared as data so the anti-invention guard
#: has a table to compare against rather than a list of names in prose.
REPORTED_COMMITTED_FIELDS: Tuple[str, ...] = (
    "name",
    "gold",
    "cash",
    "mana",
    "level",
    "target",
)

#: The committed columns that carry a number, and are therefore the ones an
#: invented price would have to be computed from.  The guard the hermetic suite
#: runs compares this table against what the module actually reads.
NUMERIC_COMMITTED_COLUMNS: Tuple[str, ...] = ("gold", "cash", "mana", "level")


class PostConditionViolation(Exception):
    """The executed transaction did not produce the state it derived.

    Never a client-visible game answer: the slice converts it into a
    ``post_condition_violation`` refusal and rolls the store back, exactly as
    ``server_v1_collect`` and ``server_v1_collection`` do.
    """


class _IssuanceToken:
    """Module-private marker; only :func:`issue_magic_transition` holds one."""

    __slots__ = ()


_ISSUANCE_TOKEN = _IssuanceToken()


class MagicTransition(BaseModel):
    """The committed-bound magic counter transition: one bounded increment.

    **Not a resource derivation, and deliberately not shaped like one.**
    ``server_v1_economy`` owns every value that moves a *stored resource*, and
    ``tests/test_boundary_invariant.py`` asserts that by walking the economy's
    frozen ``BaseModel`` subclasses.  A counter is not a stored resource: no
    branch of ``engine.apply_resources`` can move one, and the whole point of
    design D2 is that this line moves nothing.  Putting the model in the economy
    would have made it a fourth ``Derivation`` and widened a guard that is
    correctly narrow; putting it here keeps the economy's boundary honest and
    leaves this slice's own construction site guarded by the same shape -- a
    private token, so a ``MagicTransition`` with a hand-written value is
    unconstructible outside this module.

    What it carries, every field read from the store or derived here, and none
    of it computed from a request field:

    ``magic_id``
        the committed id the transition is for, which is the id the ledger key
        is written under;
    ``operation``
        which of the two declared operation names produced it.  Both produce the
        same value; the field exists so the response can report what was asked,
        not so the two can be told apart;
    ``before`` / ``after``
        the recorded counter before the write, and the value derived from it;
    ``had_recorded_entry``
        whether the ledger already carried the key.  This is what makes the
        preserved branches' ``else`` arm visible in the response;
    ``cap`` / ``at_cap``
        the recorded literal bound and whether the derived value reached it;
    ``transition_id``
        a per-transition identifier, so two transitions in one log are
        distinguishable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    magic_id: int
    operation: str
    before: int
    after: int
    had_recorded_entry: bool
    cap: int = Field(default=COUNTER_CAP)
    at_cap: bool
    transition_id: str = Field(default_factory=lambda: uuid4().hex)

    #: The committed row this transition was derived from, decoded, for the
    #: response.  Read-only and private, so a caller cannot widen the payload by
    #: mutating the mapping after construction.
    _committed: Mapping[str, Any] = PrivateAttr(default_factory=dict)

    #: :data:`COUNTER_CAP_PROVENANCE`, carried on the value rather than restated
    #: beside it.  A response reporting ``cap`` has to be able to say where the
    #: number came from, and :mod:`server_v1_outcomes` cannot import this module
    #: without a circular import, so the provenance travels with the transition
    #: exactly as the committed row does.
    _cap_provenance: Mapping[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self, **values: Any) -> None:
        if values.pop("__token__", None) is not _ISSUANCE_TOKEN:
            raise TypeError(
                "MagicTransition is issued only by server_v1_magic; a magic "
                "success cannot be constructed without a transition derived here"
            )
        committed = dict(values.pop("committed", {}))
        cap_provenance = dict(values.pop("cap_provenance", {}))
        super().__init__(**values)
        object.__setattr__(self, "_committed", _read_only(committed))
        object.__setattr__(
            self, "_cap_provenance", _read_only(cap_provenance or COUNTER_CAP_PROVENANCE)
        )

    @property
    def committed(self) -> Mapping[str, Any]:
        """The committed inputs this transition was derived from, read-only."""
        return self._committed

    @property
    def cap_provenance(self) -> Mapping[str, Any]:
        """Where :attr:`cap` came from, including the rejected alternative."""
        return self._cap_provenance


def issue_magic_transition(**values: Any) -> MagicTransition:
    """Construct a :class:`MagicTransition`.  The only construction site.

    Named to match ``server_v1_economy``'s two public issuers so the shape of
    "one module may produce this value" reads the same across all three slices;
    it is a **separate authority** rather than a second economy, because a
    counter is not a resource (see :class:`MagicTransition`).
    """
    values.setdefault("cap_provenance", COUNTER_CAP_PROVENANCE)
    return MagicTransition(__token__=_ISSUANCE_TOKEN, **values)


def apply_magic(
    intent: Intent,
    content: CommittedContent,
    repository: SaveRepository,
    now: int,
) -> Outcome:
    """Execute one magic-counter intent, or refuse it by name.

    ``now`` is the service's own clock, passed in rather than read here, so a
    test can pin it.  It is never a request value: the intent has no field it
    could arrive in.  **The preserved branches record no instant at all**, so
    nothing in the store holds this one -- it is reported so the client can see
    the server's clock, and the field that would hold it does not exist.
    """
    # ---- 1. read ----------------------------------------------------------
    try:
        document = repository.read(intent.player_id)
        before_resources = dict(document.resources())
        # **Copied, not aliased.**  ``SaveDocument.magic_ledger`` hands back the
        # live mapping on purpose -- ``set_magic_counter`` has to write through
        # it -- so a snapshot taken by reference would change underneath the
        # proof the moment the write happened, and the "unaddressed keys are
        # byte-identical" half would compare the after-state with itself.  That
        # is the aliasing version of the defect ``test_collection.py`` records as
        # "a value comparison would be satisfied by a service that wrote the same
        # values back", and it is the reason this line is a copy.
        before_ledger = dict(document.magic_ledger())
        before_level = _recorded_map_level(document)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 2. validate the identity against the committed table -------------
    # Every refusal below resolves before any write, so a refused request leaves
    # the whole document byte-identical, ledger included (design D8).  The
    # preserved server's ordering cannot be reproduced because it performs no
    # validation at all.
    magic_id = intent.magic_id
    if magic_id is None:  # pragma: no cover - parse_intent guarantees this
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "a magic intent addresses no magic id",
            {"addressing_field": "magic_id", "received": None},
        )

    try:
        committed_row = content.magic_row(magic_id)
    except ContentError as error:  # pragma: no cover - no magic read raises today
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed content is unusable: %s" % error,
            {"content_code": error.code},
        )
    if committed_row is None:
        return _unknown_magic(content, magic_id)

    committed = _committed_report(content, magic_id, before_level)
    if committed is None:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed magic %d resolved but has no usable %s field"
            % (magic_id, "or ".join(REPORTED_COMMITTED_FIELDS)),
            {"magic_id": magic_id, "fields": list(REPORTED_COMMITTED_FIELDS)},
        )

    # ---- 3. the recorded prior counter -----------------------------------
    try:
        had_entry = str(magic_id) in before_ledger
        before = document.magic_counter(magic_id)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 4. the bounded derivation ---------------------------------------
    if before > COUNTER_CAP:
        return _refuse(
            RefusalCode.COUNTER_ABOVE_CAP,
            "the recorded counter %d for magic %d is above the recorded cap %d, "
            "so no next value can be derived from it; the recorded counter is "
            "reported, not reduced" % (before, magic_id, COUNTER_CAP),
            {
                "player_id": intent.player_id,
                "magic_id": magic_id,
                "recorded_counter": before,
                "cap": COUNTER_CAP,
                "cap_is": COUNTER_CAP_PROVENANCE["cap_is"],
                "legacy_behaviour": PRESERVED_BRANCH_BEHAVIOUR["use"],
                "rolled_back": False,
            },
        )

    transition = issue_magic_transition(
        magic_id=magic_id,
        operation=str(intent.operation),
        before=before,
        after=before + 1 if before + 1 < COUNTER_CAP else COUNTER_CAP,
        had_recorded_entry=had_entry,
        at_cap=(before + 1) >= COUNTER_CAP,
        committed=committed,
    )

    # ---- 5. apply, in memory only ----------------------------------------
    snapshot = document.snapshot()
    try:
        document.set_magic_counter(magic_id, transition.after)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 6. write once ----------------------------------------------------
    try:
        repository.write(document)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 7. read back and prove -------------------------------------------
    try:
        after = repository.read(intent.player_id)
        after_resources = dict(after.resources())
        after_ledger = dict(after.magic_ledger())
        after_raw = after.snapshot()
    except RepositoryError as error:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the store could not be read back after the write: %s" % error,
            {"half": "read_back", "cause": error.code, "rolled_back": restored},
        )

    try:
        _prove(
            transition=transition,
            magic_id=magic_id,
            before_resources=before_resources,
            after_resources=after_resources,
            before_ledger=before_ledger,
            after_ledger=after_ledger,
            before_document=snapshot,
            after_document=after_raw,
        )
    except PostConditionViolation as violation:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the executed transaction did not produce its derived post-state: %s"
            % violation,
            {
                "half": _violated_half(
                    transition=transition,
                    magic_id=magic_id,
                    before_resources=before_resources,
                    after_resources=after_resources,
                    before_ledger=before_ledger,
                    after_ledger=after_ledger,
                    before_document=snapshot,
                    after_document=after_raw,
                ),
                "addressed_path": intent.addressed_path(),
                "rolled_back": restored,
            },
        )

    # ---- 8. report --------------------------------------------------------
    return MagicSuccess(
        action=ACTION,
        transition=transition,
        instant=now,
        state=after_resources,
        counter_after=transition.after,
        ledger_after=tuple(_ordered_ledger(after_ledger)),
    )


# ------------------------------------------------------------------ resolve --


def _unknown_magic(content: CommittedContent, magic_id: int) -> Refusal:
    """The identity refusal, with the committed id space reported (design D3).

    Refused rather than aliased for a **measured** reason: unlike
    ``complete_collection``, the preserved branches never index the committed
    table at all -- they use the client's value as a dictionary key -- so zero and
    every negative id simply name nothing.  There is no positional clamp for a
    non-positive id to collide with, and inventing one would be a second
    addressing rule with the same name.
    """
    committed_ids = content.magic_ids()
    return _refuse(
        RefusalCode.UNKNOWN_MAGIC_ID,
        "magic id %d names no row of the committed magic table, which holds %d "
        "rows" % (magic_id, len(committed_ids)),
        {
            "requested_magic_id": magic_id,
            "committed_ids": list(committed_ids),
            "committed_rows": len(committed_ids),
            "committed_table_is": "magics",
            "resolved_row": None,
        },
    )


def _committed_report(
    content: CommittedContent, magic_id: int, player_level: Any
) -> Optional[Dict[str, Any]]:
    """The committed row, verbatim, beside the player's recorded level.

    **No value here is computed from another.**  ``gold``, ``cash``, ``mana`` and
    ``level`` are read as committed integers and reported as such, which is the
    whole of design D2: the table carries them, nothing names them a price, and
    v1 therefore reads them and charges nothing.  ``area`` is decoded from its
    committed embedded-JSON string and the coercion is recorded rather than
    interpreted (design Q6).

    ``kind`` is **absent from the raw committed table entirely** -- measured, all
    ten rows -- so the reader returns ``None`` and it is reported as ``None``
    rather than filled in from elsewhere.  The normalized package does declare
    one (``"magic"``, asserted over all ten rows in
    ``tests/test_magic.py``), but that is the *package's* attribute and reading
    it would mean v1 consulting a second artifact for a value the server's own
    table does not carry.  The two facts are reported side by side rather than
    reconciled, exactly as the level pair below is.

    The player's recorded ``maps[0].level`` is reported **beside** the committed
    ``level`` and the two are **not compared** (design D5).  The gate is a
    deferred authority gap, not a denial: ``0`` of 33 committed documents at
    level 1 reach any magic, so enforcing it would make the route unexercisable
    on the committed live phase; ``min_level`` has zero occurrences across all
    eleven legacy modules, so there is no established gate spelling to
    reproduce; and no legacy comparison of a player's level against any content
    ``level`` exists anywhere in the preserved source.

    ``None`` is returned when the row has no usable ``name``, which is the one
    field a magic the client could not even name would lack; the caller turns
    that into ``unreadable_content``.
    """
    name = content.magic_field(magic_id, "name")
    if not isinstance(name, str) or name == "":
        return None
    report: Dict[str, Any] = {"id": magic_id, "name": name}
    for field in ("gold", "cash", "mana", "level", "target"):
        value = content.magic_field(magic_id, field)
        report[field] = (
            value if isinstance(value, int) and not isinstance(value, bool) else None
        )
    area = content.magic_area(magic_id)
    report["area"] = None if area is None else list(area)
    report["area_stored_as"] = "an embedded JSON string in the committed table"
    report["kind"] = content.magic_field(magic_id, "kind")
    report["kind_source"] = (
        "the raw committed magics table carries no kind column at all, so this "
        "is None; the normalized package declares kind 'magic' on all ten rows, "
        "and reading that here would mean consulting a second artifact for a "
        "value the server's own table does not carry"
    )
    report["player_level"] = player_level
    report["level_compared"] = False
    report["level_gate_enforced"] = False
    report["level_gate_deferred_because"] = (
        "min_level has zero legacy occurrences and no legacy branch compares a "
        "player level against a committed magic level, so there is no recorded "
        "gate to reproduce; 0 of 33 committed documents at level 1 reach any "
        "magic, so enforcing one would make this route unexercisable on the "
        "committed corpus (design D5)"
    )
    report["price_charged"] = None
    report["price_refused_because"] = (
        "no committed column is named a price, nothing in the eleven legacy root "
        "modules reads any of the four, and the twelve executed-legacy "
        "transactions in tests/fixtures/godot-damage/ moved zero of the eight "
        "resource slots engine.apply_resources unpacks (design D2)"
    )
    return report


def _recorded_map_level(document: Any) -> Any:
    """The player's recorded ``maps[0].level``, verbatim, or ``None``.

    ``None`` is a real answer here and is reported as such: the field is absent
    from no committed document, but a shape this service cannot read must not be
    silently reported as level ``0``, and no level is ever compared against it.
    """
    try:
        value = document.first_map().get("level")
    except RepositoryError:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


# --------------------------------------------------------------------- proof --


def _half_checks(
    *,
    transition: MagicTransition,
    magic_id: int,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    before_ledger: Mapping[str, Any],
    after_ledger: Mapping[str, Any],
    before_document: Any,
    after_document: Any,
) -> Tuple[Tuple[str, str], ...]:
    """Each proof half, in the order :func:`_prove` enforces them.

    Returns ``(half_name, failure_message)`` pairs where an **empty** message
    means the half held.  One ordered list is walked by both :func:`_prove` and
    :func:`_violated_half`, so the reported half cannot drift from the enforced
    one.
    """
    checks: List[Tuple[str, str]] = []

    # 1. the addressed key holds exactly the derived value.
    addressed = str(magic_id)
    if after_ledger.get(addressed) != transition.after:
        checks.append(
            (
                "addressed_key_matched_transition",
                "the ledger key %r became %r, not the derived %r"
                % (addressed, after_ledger.get(addressed), transition.after),
            )
        )
    else:
        checks.append(("addressed_key_matched_transition", ""))

    # 2. every unaddressed key is byte-identical and keeps its position.
    unaddressed_changed = sorted(
        key
        for key in set(before_ledger) | set(after_ledger)
        if key != addressed and before_ledger.get(key) != after_ledger.get(key)
    )
    if unaddressed_changed:
        checks.append(
            (
                "unaddressed_keys_unchanged",
                "unaddressed ledger key(s) %r changed" % (unaddressed_changed,),
            )
        )
    elif [k for k in before_ledger if k != addressed] != [
        k for k in after_ledger if k != addressed
    ]:
        # Both sides are filtered to the **unaddressed** keys, in stored order.
        # Comparing the raw key lists instead would report the addressed key's
        # own presence as an unaddressed key having moved, so a ledger that
        # already carried the key would fail the half it is being written by.
        checks.append(
            (
                "unaddressed_keys_unchanged",
                "the unaddressed keys moved position: %r -> %r"
                % (
                    [k for k in before_ledger if k != addressed],
                    [k for k in after_ledger if k != addressed],
                ),
            )
        )
    else:
        checks.append(("unaddressed_keys_unchanged", ""))

    # 3. every stored resource is byte-identical.  **The falsifiable half.**
    #
    # **Enforced third, not fourth, and the order is deliberate.**  A charge of
    # any size also moves a leaf path *outside* the addressed ledger key, so with
    # the ownership half first the falsifiable half would be unreachable: every
    # injected charge would be reported as `exactly_one_leaf_path_changed` and the
    # design's claim that "a charge of any size fails half 2" would be true only
    # of the property rather than of the report.  Nothing is dropped by the
    # reordering -- all four properties are enforced on every execution, and
    # :func:`_violated_half` walks this same ordered list -- so the only thing it
    # changes is *which* half is named, and the one design D9 calls the evidence
    # is the one a reader is now told.
    moved = sorted(
        name
        for name in STORED_RESOURCE_NAMES
        if after_resources.get(name) != before_resources[name]
    )
    if moved:
        checks.append(
            (
                "resources_unchanged",
                "stored resource(s) %r moved; this transaction charges nothing, "
                "so no stored resource may change" % (moved,),
            )
        )
    else:
        checks.append(("resources_unchanged", ""))

    # 4. every changed leaf path is the addressed key's, and there is at most one.
    #
    # **``at most one``, and why.**  The spec's requirement reads "exactly one
    # stored leaf path changed", and for every non-boundary transition that is
    # literally true and enforced.  It cannot be true of the **recorded no-op**:
    # at the cap, ``after == before`` (``min(50, before + 1)`` is ``50`` when
    # ``before`` is ``50``), so the write v1 performs writes the value it read.
    # That is not an invented leniency -- it is what the preserved ``use_magic``
    # arm does at exactly the same recorded value, which is why
    # ``PRESERVED_MAGIC_BEHAVIOUR["same_number"]`` says the two agree *at or
    # below* the cap.  So the property that survives every case is the one that
    # carries the weight: **nothing outside the addressed ledger key may move**.
    # The count is still bounded, and a second leaf inside the addressed key --
    # which a dict-to-something-else rewrite would produce -- is still a failure.
    changed = _changed_leaf_paths(before_document, after_document)
    expected = [
        path
        for path in changed
        if path.startswith("/privateState/magics/%s" % addressed)
    ]
    if changed != expected or len(changed) > 1:
        checks.append(
            (
                "exactly_one_leaf_path_changed",
                "the document changed at %r, which is not the addressed ledger "
                "key %r and at most one leaf" % (changed, addressed),
            )
        )
    else:
        checks.append(("exactly_one_leaf_path_changed", ""))

    return tuple(checks)


def _prove(
    *,
    transition: MagicTransition,
    magic_id: int,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    before_ledger: Mapping[str, Any],
    after_ledger: Mapping[str, Any],
    before_document: Any,
    after_document: Any,
) -> None:
    """The post-execution proof (design D9), four ordered checks.

    Two of the four are the **specification** half: v1 is the only implementation
    writing this save on this path, so they state what v1 promised rather than
    what the preserved server did.  One is the falsifiable one, and it is
    falsifiable because of design D2 -- any charge at all moves one of the seven.

    The **order** is the module's decision and is enforced here exactly as
    :func:`_half_checks` and :func:`_violated_half` walk it:
    ``addressed_key_matched_transition``, ``unaddressed_keys_unchanged``,
    ``resources_unchanged``, ``exactly_one_leaf_path_changed``.  Putting the
    resource check third is what makes an injected charge *report* as a charge;
    see the note on :func:`_half_checks`.
    """
    for _half, message in _half_checks(
        transition=transition,
        magic_id=magic_id,
        before_resources=before_resources,
        after_resources=after_resources,
        before_ledger=before_ledger,
        after_ledger=after_ledger,
        before_document=before_document,
        after_document=after_document,
    ):
        if message:
            raise PostConditionViolation(message)


def _violated_half(**kwargs: Any) -> str:
    """Which half of the proof failed, in the order the proof enforces them.

    Walks the same ordered list :func:`_prove` does, so a half that has not
    failed cannot be reported.  ``"none"`` is only reachable if the proof and
    this function disagree about what a failure is, which is itself a defect.
    """
    for half, message in _half_checks(**kwargs):  # type: ignore[arg-type]
        if message:
            return half
    return "none"


def _changed_leaf_paths(before: Any, after: Any, prefix: str = "") -> List[str]:
    """Every **leaf** path whose value differs between two parsed documents.

    A leaf is a scalar or a container of scalars; a dict or list is walked.  The
    helper exists so "exactly one leaf path changed" is a *measurement* over the
    whole document rather than a claim about the one key the slice wrote, which
    is the difference between a proof and an assertion.  It is the same shape as
    ``tests/test_collection.py``'s helper, kept here because the domain runs the
    check itself and a test helper is not reachable from a module.
    """
    if isinstance(before, dict) and isinstance(after, dict):
        paths: List[str] = []
        for key in sorted(set(before) | set(after), key=str):
            paths.extend(
                _changed_leaf_paths(before.get(key), after.get(key), "%s/%s" % (prefix, key))
            )
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths = []
        if len(before) != len(after):
            return ["%s/length" % (prefix or "/")]
        for index in range(len(before)):
            paths.extend(
                _changed_leaf_paths(
                    before[index], after[index], "%s/%d" % (prefix, index)
                )
            )
        return paths
    if before == after and type(before) is type(after):
        return []
    return [prefix or "/"]


# -------------------------------------------------------------------- helpers --


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=dict(detail))


def _repository_refusal(error: RepositoryError, intent: Intent) -> Refusal:
    """Map a repository failure onto a refusal code, as both slices do."""
    if error.code == "unknown_player":
        return _refuse(
            RefusalCode.UNKNOWN_PLAYER, str(error), {"player_id": intent.player_id}
        )
    return _refuse(
        RefusalCode.UNREADABLE_STATE,
        str(error),
        {"player_id": intent.player_id, "cause": error.code},
    )


def _ordered_ledger(ledger: Mapping[str, Any]) -> Sequence[str]:
    """The ledger's own keys, in stored order -- insertion order, not sorted."""
    return list(ledger.keys())


def _read_only(mapping: Dict[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(mapping)


def _rollback(
    repository: SaveRepository, intent: Intent, snapshot: Dict[str, Any]
) -> bool:
    """Write the pre-request snapshot back; report whether it succeeded."""
    try:
        current = repository.read(intent.player_id)
        current.raw.clear()
        current.raw.update(snapshot)
        repository.write(current)
    except RepositoryError:
        return False
    return True


def declared_operations() -> Tuple[str, ...]:
    """The closed operation set this slice accepts, read from the intent table.

    A reader rather than a second declaration: the operation set is data in
    :data:`server_v1_intent.INTENT_OPERATION_VALUES` (design D1), and a second
    copy here would be a place the two could drift.
    """
    return tuple(sorted(INTENT_OPERATION_VALUES["operation"]))


__all__ = [
    "ACTION",
    "COUNTER_CAP",
    "COUNTER_CAP_PROVENANCE",
    "NUMERIC_COMMITTED_COLUMNS",
    "PRESERVED_ABSENT_KEY_BEHAVIOUR",
    "PRESERVED_BRANCH_BEHAVIOUR",
    "REPORTED_COMMITTED_FIELDS",
    "MagicTransition",
    "PostConditionViolation",
    "apply_magic",
    "declared_operations",
    "issue_magic_transition",
]