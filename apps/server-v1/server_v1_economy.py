#!/usr/bin/env python3
"""The economy authority: the one place a Server v1 resource delta is derived.

**Task 2.3 and design D2.**  Every balance change v1 makes passes through
:func:`derive_collection_payout`, and that function is the *only* place in
``apps/server-v1/`` where a resource delta is computed.  The rule is enforced
three ways, not asserted in prose:

1. :class:`ResourceDerivation` cannot be constructed without the module-private
   :data:`_ISSUANCE_TOKEN`, so the domain's typed success value (which *requires*
   a derivation — task 2.2) can only be built from a number produced here.
2. ``tests/test_boundary_invariant.py`` walks the AST of every module under
   ``apps/server-v1/`` and asserts :class:`ResourceDerivation` is constructed in
   **exactly one** file, that :class:`~server_v1_outcomes.Success` is
   constructed in exactly one file, and that neither the app nor the runner
   constructs either.  Injecting a second derivation fails that test.
3. Nothing in this module reads a client value.  Every input is either a
   committed content field or a recorded instant, and the request contributes
   nothing but *which row* to look at.

Provenance of the rules, per the spec's "Evidence distinguishes established
behaviour from derived authority":

**ESTABLISHED** (committed legacy source, and the executed-legacy fixture under
``tests/fixtures/godot-building-collect/``):

* the item income fields exist and are string-encoded — ``collect "20"``,
  ``collect_type "w"``, ``collect_xp "1"``, ``max_collects "0"`` for the
  committed Tree ``905``;
* the ladder globals are committed and parallel: ``COLLECT_MINUTES
  [5, 60, 240, 480]``, ``COLLECT_MULTIPLIER [0.25, 1, 2, 3]``;
* ``COLLECT_MINUTES`` is expressed in **minutes** while both recorded instants
  are Unix **seconds**;
* the collection instant is a whole number of seconds, and a row's recorded
  instant of ``0`` means "never collected", which makes elapsed time unbounded;
* the seven stored resource paths (see :mod:`server_v1_repository`).

**DERIVED**, with the rejected alternative named in each case:

* **DERIVED — the rung is the highest committed threshold the elapsed time has
  reached, clamped at the top rung.**  Rejected alternative: interpolating past
  the last rung, which would make the last multiplier unbounded.  No legacy
  branch reads either global, so nothing about a ladder was ever *observed*;
  the committed fixture only shows a single transaction, at the top rung.
* **DERIVED — the multiplier scales the amount.**  Rejected alternative: a flat
  payout, which would make ``COLLECT_MULTIPLIER`` dead content — the two arrays
  are parallel and four long, so a rule that ignored the second would have no
  effect at all.
* **DERIVED — the same rung scales ``collect_xp``.**  Rejected alternative: a
  flat ``collect_xp``, which would leave the payout's two halves inconsistent.
* **DERIVED — below the first committed rung nothing is derived.**  Rejected
  alternative: paying a fraction of the first rung's ``0.25`` multiplier, which
  would invent an amount no committed threshold authorises.
* **DERIVED — ``collect_type`` is a closed vocabulary mapping to the stored
  resource names.**  Rejected alternative: inventing a mana mapping for a
  content value no item records.  The census is **measured over the 900 loaded
  items**: ``g`` 853, ``w`` 23, ``o`` 11, ``s`` 11, ``c`` 2 — five distinct
  values and no sixth, so the five-entry map is exactly the committed set.
  **Corrected after measurement.**  This bullet originally read ``g`` (731)
  across "the 778 stored items".  Only the four minority counts were right; the
  majority was 122 low and the total 122 low, so the figure had been carried
  over from a differently-scoped count rather than measured.  Recorded in
  ``docs/legacy-m13-collect-v1.md``; the conclusion is unchanged.
* **DERIVED — a non-zero ``max_collects`` is refused, not interpreted.**
  Rejected alternatives: reading it as a per-collection limit, or ignoring it.
  Measured over the same 900 items the values are ``"0"`` on **889**, ``"25"``
  on **9**, and ``"100"`` on **2**.  **Corrected after measurement**: the
  original text said ``"0"`` for 767 of 778.  Nothing in the repository says
  which of three plausible readings is meant, and ``max_collects`` has **zero**
  legacy consumers across all seven root modules, so the refusal has no oracle
  for it to disagree with.

**The claim is limited to this**: a payout that grows in four committed rungs
derived from an item's committed income fields, mapped onto v1's own resource
names.  It is never a claim about any specific amount the legacy client paid —
the legacy client paid whatever it sent, and the server applied it.
"""

from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from server_v1_content import CommittedContent, ContentError
from server_v1_refusals import RefusalCode

#: ``COLLECT_MINUTES`` is committed in minutes; recorded instants are seconds.
#: This is the **only** place the conversion happens.  Getting it wrong would
#: make the five-minute rung read as five *seconds* and pay the top rung almost
#: immediately, so ``tests/test_economy.py`` asserts every boundary from both
#: sides (299/300, 3599/3600, 14399/14400, 28799/28800).
SECONDS_PER_COMMITTED_MINUTE = 60

#: The committed ``collect_type`` vocabulary, mapped to **v1's stored resource
#: names** rather than to the legacy eight-slot vector's indexes.  The names are
#: the save document's own field names (``server_v1_repository``), so this table
#: is the single join between committed content and stored state.
COLLECT_TYPE_RESOURCES: Dict[str, str] = {
    "g": "gold",
    "w": "wood",
    "o": "oil",
    "s": "steel",
    "c": "cash",
}

#: The experience a collection pays is stored under its own name.
EXPERIENCE_RESOURCE = "xp"

#: Resources this derivation can never pay, asserted by the tests.  ``mana`` is
#: here because no committed item records a mana collect type — the slot exists
#: in the save but nothing in committed content produces it.
NEVER_PAID_RESOURCES: Tuple[str, ...] = ("mana",)


class EconomyError(Exception):
    """A derivation this service cannot make, with a stable machine code.

    The code is a :class:`~server_v1_refusals.RefusalCode` **value**, not a
    string.  That is not stylistic: the first draft of this module carried
    ``code: str`` and raised ``EconomyError("no_committed_income", ...)``, which
    meant the five codes the economy raises were named only by bare string
    literals — invisible to the vocabulary guard, which reads
    ``RefusalCode.X`` attribute references.  Five codes would then have looked
    "used" only because the guard's own file listed them.  Typing the field as
    the enum makes the economy name its reasons in the domain vocabulary, which
    is what the transport relies on, and makes an undeclared reason
    unconstructible.
    """

    def __init__(
        self,
        code: RefusalCode,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class ResourceDerivation(BaseModel):
    """A server-derived set of balance changes, with its own provenance.

    Frozen, and its mappings are frozen **too**.  A derivation that has been
    handed to the success value cannot be edited into a different payout on the
    way out, which is the whole remaining degree of freedom the transport has.

    **Corrected while writing this line's tests.**  The first version declared
    ``deltas`` and ``committed`` as ordinary ``Dict`` fields on a
    ``frozen=True`` model and documented exactly the guarantee above.  That
    guarantee was **false**, and the test that found it is
    ``tests/test_economy.py::test_a_derivation_cannot_be_edited_in_place``:
    ``frozen=True`` blocks *attribute* assignment, not mutation of a contained
    ``dict``, so ``derivation.deltas["gold"] = 999`` succeeded and the transport
    could have reported a payout the server never derived.  Both mappings are
    now module-private :class:`~types.MappingProxyType` values behind
    read-only properties, which makes the documented claim true rather than
    aspirational.  ``frozen=True`` alone was a guard that looked like one.

    ``deltas`` is keyed by **stored resource name** and covers *only* the
    resources this transaction pays.  A resource absent from the mapping is a
    resource that must not change — which is what makes the two-part
    post-execution proof in :mod:`server_v1_collect` able to assert "every
    stored resource changed by exactly the derived delta" over the complete
    stored set rather than only over the ones that happened to move.

    The private construction gate: :func:`_issue` is the only caller, and it
    requires :data:`_ISSUANCE_TOKEN`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: The committed rung the payout came from: its index and its committed
    #: threshold in seconds, so the response can report *which* rule paid it.
    rung_index: int
    rung_threshold_seconds: int
    rung_multiplier: float
    #: Elapsed seconds the rung was selected from.
    elapsed_seconds: int
    #: A per-derivation identifier, so two derivations in one request are
    #: distinguishable in a log or a test failure.
    derivation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    #: Named resource -> integer delta.  Never negative: this authority only
    #: pays, and a debit belongs to a different domain with its own derivation.
    _deltas: Mapping[str, int] = PrivateAttr(default_factory=dict)
    #: The committed inputs, echoed so a reader can check the derivation against
    #: content without re-deriving it.
    _committed: Mapping[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self, **values: Any) -> None:
        # Identity, not containment: a caller cannot produce a token because the
        # class is module-private and nothing else holds a reference to one.
        # An earlier draft compared with ``in``, which raised ``TypeError`` on a
        # non-iterable — recorded because the failure mode looked like the gate
        # rejecting a legitimate derivation.
        if values.pop("__token__", None) is not _ISSUANCE_TOKEN:
            raise TypeError(
                "ResourceDerivation is issued only by server_v1_economy; a "
                "success cannot be constructed without a derivation here"
            )
        deltas = dict(values.pop("deltas", {}))
        committed = dict(values.pop("committed", {}))
        super().__init__(**values)
        object.__setattr__(self, "_deltas", MappingProxyType(deltas))
        object.__setattr__(self, "_committed", MappingProxyType(committed))

    @property
    def deltas(self) -> Mapping[str, int]:
        """Named resource -> integer delta, read-only."""
        return self._deltas

    @property
    def committed(self) -> Mapping[str, Any]:
        """The committed inputs this payout was derived from, read-only."""
        return self._committed

    def delta_for(self, resource: str) -> int:
        """The derived change to one stored resource; ``0`` when unpaid."""
        return int(self.deltas.get(resource, 0))

    def applies_to(self, resource: str) -> bool:
        """Whether this derivation claims to change ``resource`` at all."""
        return resource in self.deltas


class _IssuanceToken:
    """Module-private marker; only :func:`_issue` holds a reference."""

    __slots__ = ()


_ISSUANCE_TOKEN = _IssuanceToken()


def _issue(**values: Any) -> ResourceDerivation:
    """Construct a :class:`ResourceDerivation`.  The only construction site."""
    return ResourceDerivation(__token__=_ISSUANCE_TOKEN, **values)


def issue_collection_grant(**values: Any) -> "CollectionGrant":
    """Construct a :class:`CollectionGrant`.  The only construction site.

    Shares :data:`_ISSUANCE_TOKEN` with :func:`_issue` because the token's
    meaning is "this module's economy authority derived it", and a collection
    grant is derived by the same authority from committed content and recorded
    state.  Splitting it into a second token would suggest a second economy,
    which is the thing design **D8** in ``server_v1_refusals`` exists to
    prevent: one place a derived value can be born.
    """
    return CollectionGrant(__token__=_ISSUANCE_TOKEN, **values)


class CollectionGrant(BaseModel):
    """The committed-derived collection grant: cost, yield, and requirements.

    The second derivation this authority issues, and the first that is a
    **debit** rather than a payout.  That is deliberate and is recorded on the
    field below rather than discovered in a balance: :class:`ResourceDerivation`
    explicitly refuses negative deltas because "a debit belongs to a different
    domain with its own derivation", so this is that derivation.

    **Why this is not a :class:`ResourceDerivation`.**  A collection has no
    ladder, no rung, and no elapsed time.  Forcing it into the payout
    derivation would have required inventing four values that mean nothing here
    (``rung_index``, ``rung_threshold_seconds``, ``rung_multiplier``,
    ``elapsed_seconds``), and an invented ``rung_index=0`` would have read as a
    claim that the committed rung zero paid for it.  The two derivations share
    the issuance gate and nothing else, which is the honest shape: same
    authority, different question.

    What it carries, all of it either read from the committed table or read from
    the store, none of it computed from a request field:

    ``requested_collection_id``
        the id the client sent, echoed so the response can report what was
        asked rather than what was resolved;
    ``resolved_collection_id``
        the committed table's own ``id`` at the position the request addressed,
        which is the id the ledger is written with;
    ``position``
        the 0-based position actually used, i.e. ``max(0, requested - 1)``;
    ``clamp_moved``
        whether the legacy clamp changed the addressed position, reported so the
        two can never be silently conflated (a grant whose ``clamp_moved`` is
        true is unreachable through this service - the slice refuses it - and
        the field exists so a reader can see that, not so a caller can rely on
        it);
    ``requirement_ids``
        the committed ``item_ids`` the eligibility check evaluated;
    ``price``
        the committed ``cashPrice``, in stored cash;
    ``prize_item_id`` / ``prize_quantity``
        the committed ``prize``, which is exactly one entry on every committed
        row;
    ``grant_id``
        a per-grant identifier, so two grants in one log are distinguishable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    requested_collection_id: int
    resolved_collection_id: int
    position: int
    clamp_moved: bool
    requirement_ids: Tuple[int, ...]
    price: int
    prize_item_id: int
    prize_quantity: int
    grant_id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    #: The **signed** change to each stored resource.  Negative is legal here and
    #: only here: this derivation debits ``cash`` by the committed price and
    #: changes nothing else, so the post-execution proof can assert over the
    #: complete stored set rather than over the one key it expects to move.
    _deltas: Mapping[str, int] = PrivateAttr(default_factory=dict)
    #: The committed row this grant came from, decoded, for the response.
    _committed: Mapping[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self, **values: Any) -> None:
        if values.pop("__token__", None) is not _ISSUANCE_TOKEN:
            raise TypeError(
                "CollectionGrant is issued only by server_v1_economy; a "
                "collection success cannot be constructed without a grant here"
            )
        deltas = dict(values.pop("deltas", {}))
        committed = dict(values.pop("committed", {}))
        super().__init__(**values)
        object.__setattr__(self, "_deltas", MappingProxyType(deltas))
        object.__setattr__(self, "_committed", MappingProxyType(committed))

    @property
    def deltas(self) -> Mapping[str, int]:
        """Named resource -> **signed** derived change, read-only."""
        return self._deltas

    @property
    def committed(self) -> Mapping[str, Any]:
        """The committed inputs this grant was derived from, read-only."""
        return self._committed

    def delta_for(self, resource: str) -> int:
        """The derived change to one stored resource; ``0`` when untouched."""
        return int(self.deltas.get(resource, 0))

    def applies_to(self, resource: str) -> bool:
        """Whether this grant claims to change ``resource`` at all."""
        return resource in self.deltas


def derive_collection_payout(
    content: CommittedContent,
    *,
    item_id: int,
    last_collected_at: int,
    now: int,
) -> ResourceDerivation:
    """Derive one collection's payout from committed content and recorded state.

    This is the authority.  It reads **no** request field other than the item
    identity the repository resolved from the client's row address, and it
    computes no value the client supplied.  The order of its checks is
    deliberate and is the "decide before mutate" requirement: every refusal is
    decided here, before any caller has written anything.

    Raises :class:`EconomyError` with one of these codes, all declared in
    :class:`~server_v1_refusals.RefusalCode`:

    ``no_committed_income``
        the item records no usable ``collect`` amount, no ``collect_type``, or a
        non-integer ``collect_xp``;
    ``capped_collection``
        the item records a non-zero ``max_collects``, which v1 refuses to
        interpret (DERIVED — see the module docstring);
    ``below_first_rung``
        the elapsed time has not reached the first committed threshold, so no
        amount can be derived (DERIVED);
    ``unreadable_content``
        the committed ladder is not a usable non-empty pair of equal length.
    """
    ladder = _ladder_or_refuse(content)

    amount = content.item_non_negative_int(item_id, "collect")
    resource_type = content.item_attribute(item_id, "collect_type")
    experience = content.item_non_negative_int(item_id, "collect_xp")
    cap = content.item_non_negative_int(item_id, "max_collects")

    if cap:
        raise EconomyError(
            RefusalCode.CAPPED_COLLECTION,
            "committed content records a collection cap for item %d, which v1 "
            "refuses rather than interprets" % item_id,
            {"item_id": item_id, "max_collects": cap},
        )

    if amount is None or amount == 0 or not resource_type or experience is None:
        raise EconomyError(
            RefusalCode.NO_COMMITTED_INCOME,
            "committed content records no collection income for item %d" % item_id,
            {
                "item_id": item_id,
                "collect": content.item_attribute(item_id, "collect"),
                "collect_type": content.item_attribute(item_id, "collect_type"),
                "collect_xp": content.item_attribute(item_id, "collect_xp"),
            },
        )

    resource = COLLECT_TYPE_RESOURCES.get(resource_type)
    if resource is None:
        raise EconomyError(
            RefusalCode.UNREADABLE_CONTENT,
            "committed collect_type %r maps to no stored resource" % resource_type,
            {
                "item_id": item_id,
                "collect_type": resource_type,
                "known_collect_types": sorted(COLLECT_TYPE_RESOURCES),
            },
        )

    elapsed = _elapsed_or_refuse(last_collected_at, now, item_id)
    rung = _rung_or_refuse(elapsed, ladder)
    multiplier = ladder.multipliers[rung]

    deltas: Dict[str, int] = {EXPERIENCE_RESOURCE: _scale(experience, multiplier)}
    deltas[resource] = _scale(amount, multiplier)

    return _issue(
        deltas=deltas,
        rung_index=rung,
        rung_threshold_seconds=ladder.minutes[rung] * SECONDS_PER_COMMITTED_MINUTE,
        rung_multiplier=multiplier,
        elapsed_seconds=elapsed,
        committed={
            "item_id": item_id,
            "collect": amount,
            "collect_type": resource_type,
            "collect_xp": experience,
            "max_collects": cap,
            "resource": resource,
            "ladder_minutes": list(ladder.minutes),
            "ladder_multipliers": list(ladder.multipliers),
            "ladder_unit": "minutes",
            "seconds_per_committed_minute": SECONDS_PER_COMMITTED_MINUTE,
        },
    )


class Ladder:
    """A validated committed ladder, in minutes and multipliers."""

    __slots__ = ("minutes", "multipliers")

    def __init__(self, minutes: Tuple[int, ...], multipliers: Tuple[float, ...]) -> None:
        self.minutes = minutes
        self.multipliers = multipliers


def _ladder_or_refuse(content: CommittedContent) -> Ladder:
    try:
        minutes, multipliers = content.collect_ladder()
    except ContentError as error:
        raise EconomyError(
            RefusalCode.UNREADABLE_CONTENT, "committed collection ladder is unusable: %s" % error
        )
    return Ladder(minutes, multipliers)


def _elapsed_or_refuse(last_collected_at: int, now: int, item_id: int) -> int:
    """Elapsed whole seconds, or a refusal for a state that cannot be elapsed.

    A recorded instant in the **future** is refused rather than clamped to zero:
    the fixture replay in ``tests/test_parity_v0_collect.py`` fixes ``now`` to
    the recorded capture instant, and a store whose instant has run ahead of it
    is a state this authority reports rather than silently pays nothing for.
    """
    if isinstance(last_collected_at, bool) or not isinstance(last_collected_at, int):
        raise EconomyError(
            RefusalCode.UNREADABLE_STATE,
            "recorded collection instant is not an integer for item %d" % item_id,
            {"item_id": item_id},
        )
    if isinstance(now, bool) or not isinstance(now, int):
        raise EconomyError(
            RefusalCode.UNREADABLE_STATE, "current time is not an integer", {"item_id": item_id}
        )
    if now < last_collected_at:
        raise EconomyError(
            RefusalCode.UNREADABLE_STATE,
            "recorded collection instant %d is later than the current time %d"
            % (last_collected_at, now),
            {"item_id": item_id, "last_collected_at": last_collected_at, "now": now},
        )
    return now - last_collected_at


def _rung_or_refuse(elapsed: int, ladder: Ladder) -> int:
    """The highest committed rung ``elapsed`` has reached, clamped at the top.

    DERIVED, with the rejected alternative named in the module docstring:
    interpolating past the last rung.  ``None`` — the caller refuses — below the
    first committed threshold, also derived.
    """
    reached: Optional[int] = None
    for index, minutes in enumerate(ladder.minutes):
        if elapsed >= minutes * SECONDS_PER_COMMITTED_MINUTE:
            reached = index
    if reached is None:
        raise EconomyError(
            RefusalCode.BELOW_FIRST_RUNG,
            "%d elapsed seconds has not reached the first committed ladder rung"
            % elapsed,
            {
                "elapsed_seconds": elapsed,
                "first_rung_seconds": ladder.minutes[0]
                * SECONDS_PER_COMMITTED_MINUTE,
            },
        )
    return reached


def _scale(value: int, multiplier: float) -> int:
    """A rung-scaled amount, rounded to a whole resource.

    Every committed product of a committed amount and a committed multiplier is
    already an integer (``20 * 0.25 = 5``, ``1 * 0.25 = 0.25`` is *not* — see
    below).  Rounding exists so a future fractional multiplier can never put a
    float on a stored integer balance.

    The rounding rule itself is **DERIVED**: half away from zero, i.e.
    ``int(scaled + 0.5)`` for a positive product.  Rejected alternative: floor,
    which would systematically pay a fraction *less* than the committed
    multiplier states, and banker's rounding, which would make ``0.5`` round to
    an even number and make the payout depend on parity rather than on content.
    With the committed ladder the only fractional product that can arise is
    ``collect_xp 1 x 0.25``, which this rule resolves to ``0`` — a first-rung
    collection of the committed Tree pays wood and no experience.  That is
    recorded rather than smoothed over: the committed content does not say
    whether a first-rung experience should round to zero or to one.
    """
    scaled = float(value) * float(multiplier)
    if scaled <= 0:
        return 0
    if scaled.is_integer():
        return int(scaled)
    return int(scaled + 0.5)


__all__ = [
    "COLLECT_TYPE_RESOURCES",
    "EXPERIENCE_RESOURCE",
    "NEVER_PAID_RESOURCES",
    "SECONDS_PER_COMMITTED_MINUTE",
    "CollectionGrant",
    "EconomyError",
    "Ladder",
    "ResourceDerivation",
    "derive_collection_payout",
    "issue_collection_grant",
]
