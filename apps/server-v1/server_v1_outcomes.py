#!/usr/bin/env python3
"""The typed success value, and the outcome union the domain returns.

**Task 2.2.**  A :class:`Success` cannot be constructed without a
:class:`~server_v1_economy.ResourceDerivation`.  That is not a convention — it
is a constructor signature: ``derivation`` is a required, non-optional field of
a frozen model whose own construction is gated behind the economy's issuance
token.  So a "successful" collection with a hand-written delta is
unconstructible, and the only way to obtain a derivation is to have the economy
authority derive one from committed content and recorded state.

The union :data:`Outcome` is what every domain service returns: a
:class:`Success`, a :class:`CollectionSuccess`, a :class:`MagicSuccess`, or a
:class:`~server_v1_refusals.Refusal`.  There is no other arm, and there is no
``None`` — a domain function that has decided nothing has a bug, and the type
says so.  **The third and fourth arms are further successes, not refusal
variants**: a collection *grant* is a genuinely different transaction from a
collection *payout*, and the difference is a shape difference (no row, no rung,
a prize in storage and a price in cash) rather than a value difference, so it
earns its own frozen model with its own required derivation; and a magic
*counter transition* is a third shape again — no row, no rung, no elapsed time,
**no price and no deltas at all** — so it earns a third.

What a :class:`Success` carries:

* ``action`` — the action that happened, so the transport cannot report a
  success for a different request than the one that ran;
* ``derivation`` — the server-derived deltas and the rung they came from;
* ``instant`` — the instant the transaction recorded, so a client can see the
  server's own clock rather than guessing;
* ``state`` — the *after* state the domain verified with its post-execution
  proof: every stored resource, and the addressed row's recorded instant.

The last field is what makes the proof reportable rather than merely performed.
A domain that mutated and then said "success" without re-reading the store would
be asserting something it had not checked; ``Success.state`` is required, so the
caller must have read it back.

No ``http_status`` here, and no payload method: the transport builds the body
from the domain value, and :data:`REFUSAL_HTTP_STATUS` lives in
:mod:`server_v1_refusals` with the refusal codes.  A success is always 200 —
that is the one status the transport is allowed to know without asking the
domain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from server_v1_economy import CollectionGrant, ResourceDerivation
from server_v1_refusals import Refusal

#: The success status, the one status the transport knows without asking.
SUCCESS_HTTP_STATUS = 200


class Success(BaseModel):
    """An action the domain decided to perform, with its derivation attached."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    #: Required and non-optional: this is task 2.2's whole mechanism.
    derivation: ResourceDerivation
    #: The instant the transaction recorded (Unix seconds).
    instant: int
    #: Every stored resource after execution, read back from the store.  The
    #: post-execution proof in :mod:`server_v1_collect` fills this, so a caller
    #: cannot report a success without having verified the state it reports.
    state: Dict[str, int] = Field(min_length=1)
    #: The addressed row's recorded instant after execution.
    row_instant: int

    def payload(self) -> Dict[str, Any]:
        """The transport body for this success (envelope added by the route).

        Reports the **derivation**, never a client figure — the spec's first
        scenario requires the response to report the derivation rather than
        echo anything the client sent, and v1's request had no figures to echo
        anyway.
        """
        return {
            "result": "success",
            "action": self.action,
            "instant": self.instant,
            "rung": {
                "index": self.derivation.rung_index,
                "threshold_seconds": self.derivation.rung_threshold_seconds,
                "multiplier": self.derivation.rung_multiplier,
            },
            "derivation_id": self.derivation.derivation_id,
            "derived_deltas": dict(self.derivation.deltas),
            "resources_after": dict(self.state),
            "row_instant": self.row_instant,
        }


#: What a domain service returns.  Four arms, no ``None``.  The same shape as
#: :data:`server_v1_intent.IntentOutcome`: three successes and one refusal.  The
#: transport tests the arm with ``isinstance``; nothing raises here.
#:
#: **Why a second success type rather than a wider first one.**
#: :class:`Success` is shaped around a collection transaction: a ladder rung,
#: an addressed row, and that row's recorded instant.  A collection **grant**
#: has no row, no rung, and no elapsed time - its shape is a prize in storage, a
#: price in cash, and an id appended to a ledger.  Widening :class:`Success`
#: would have meant optional fields that are ``None`` for one transaction and
#: populated for the other, and an optional field is a field a caller must
#: remember to check.  Three frozen models with a shared ``payload()`` keep the
#: transport's translation step total: ``dict(value.payload())`` works for all
#: three arms, and none of them can be constructed without its own derivation.
#: :class:`MagicSuccess` is the same argument a third time: it has no row, no
#: rung, no elapsed time, **no price**, and no deltas of any kind, so folding it
#: into either predecessor would have meant a ladder of ``None``s.
#:
#: Declared **after** every class it names: the union is a runtime value and
#: ``Union`` resolves its arguments when it is evaluated, so a union above the
#: class it names raises ``NameError``.  That is the one ordering constraint in
#: this module and it is a Python rule rather than a preference.


class CollectionSuccess(BaseModel):
    """A collection completion the domain decided to perform, with its grant.

    The same three guarantees :class:`Success` carries, restated for a grant
    because they are what makes the success reportable rather than merely
    claimed:

    * ``grant`` is **required and non-optional**, and a
      :class:`~server_v1_economy.CollectionGrant` can only be issued by the
      economy authority.  A "successful" completion with a hand-written price
      or prize is therefore unconstructible.
    * ``state`` is the **after** state the domain verified by reading the store
      back, so a caller cannot report a success without having read it.
    * ``prize_stored_after`` and ``ledger_after`` are the two remaining halves
      of design **D7**'s post-execution proof - the granted quantity as it now
      stands in storage, and the ledger as it now stands - both read back from
      the store after the write rather than carried forward from the in-memory
      document.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    #: Required and non-optional: the mechanism, not a convention.
    grant: CollectionGrant
    #: The instant the transaction recorded (Unix seconds).
    instant: int
    #: Every stored resource after execution, read back from the store.
    state: Dict[str, int] = Field(min_length=1)
    #: The granted prize item's quantity in storage **after** the grant.
    prize_stored_after: int
    #: The collection ledger **after** the grant, read back from the store.
    ledger_after: Tuple[int, ...]

    def payload(self) -> Dict[str, Any]:
        """The transport body for this success (envelope added by the route).

        Reports the **derived** figures, never a client figure: the committed
        price, the committed prize, the committed requirement set the server
        evaluated, the id it resolved to, and the clamp flag.  There is no
        client figure to echo, because the request carried none.
        """
        return {
            "result": "success",
            "action": self.action,
            "instant": self.instant,
            "collection": {
                "requested_id": self.grant.requested_collection_id,
                "resolved_id": self.grant.resolved_collection_id,
                "position": self.grant.position,
                "clamp_moved": self.grant.clamp_moved,
                "grant_id": self.grant.grant_id,
            },
            "requirement_ids": list(self.grant.requirement_ids),
            "derived_price": self.grant.price,
            "derived_deltas": dict(self.grant.deltas),
            "resources_after": dict(self.state),
            "granted_item_id": self.grant.prize_item_id,
            "granted_quantity": self.grant.prize_quantity,
            "prize_stored_after": self.prize_stored_after,
            "ledger_after": list(self.ledger_after),
        }


#: The preserved branches' recorded behaviour, quoted in the response so a client
#: can see the divergence rather than infer it.  **Data, not a second
#: derivation**: nothing in v1 reproduces a legacy counter value, because a
#: second derivation beside v1's own is the thing design D8 in
#: ``server_v1_refusals`` exists to prevent (design D7).
#:
#: **Declared here, not in :mod:`server_v1_magic`,** because the module dependency
#: runs the other way: ``server_v1_magic`` imports this one for
#: :class:`MagicSuccess`, so this table cannot import the slice's own copy without
#: a circular import.  Keeping the canonical copy on the lower module lets the
#: slice *read* it -- ``server_v1_magic.PRESERVED_BRANCH_BEHAVIOUR`` is a projection
#: of two of these four entries, not a second transcription -- rather than restate
#: three strings that could drift apart without anything noticing.
PRESERVED_MAGIC_BEHAVIOUR: Dict[str, str] = {
    "buy": (
        "command.py:652-663 grows the counter with += and min(50, ...) on the "
        "INCREMENT, so repeated purchases climb past the cap without limit"
    ),
    "use": (
        "command.py:664-675 ASSIGNS min(50, before + 1), so a recorded counter "
        "above the cap is reduced to the cap rather than refused"
    ),
    "absent_key": (
        "both branches take the else arm for an identity with no recorded entry "
        "and write that entry at 0, so the preserved server increments nothing "
        "where this slice writes its derived value"
    ),
    "same_number": (
        "the preserved use arm's min(50, before + 1) is this slice's rule, so "
        "the two agree exactly while the recorded counter is at or below the cap; "
        "the preserved buy arm is unbounded and never agrees at or above it"
    ),
}


def _divergence_reasons(
    *, operation: str, had_recorded_entry: bool, before: int, after: int, cap: int
) -> Tuple[str, ...]:
    """The conditions under which v1's value is known to differ, by name.

    Each entry is a **reason**, stated from values already visible in the
    response; none of them is a verdict computed by re-deriving what the
    preserved branch would have written.  A successful transaction whose reasons
    are empty would mean the two agree here, which the recorded behaviour makes
    reachable for ``use`` at every recorded counter from ``0`` through the cap
    and unreachable for ``buy`` once ``before + 1`` exceeds it.

    **A third branch was here and was measured out.**  It read
    ``operation == "use" and had_recorded_entry and before + 1 != after``, and
    named ``unexpected_use_transition``.  Against v1's own derivation
    (``after == min(cap, before + 1)``) that condition is ``true`` at exactly one
    recorded value -- ``before == cap``, where ``before + 1`` is ``51`` and
    ``after`` is ``50`` -- and that is precisely where the preserved ``use_magic``
    arm **agrees** with v1, because it computes ``min(50, before + 1)`` too.  So
    the only counter value on which it could fire was a counter on which it
    reported a divergence that does not exist, and on every other value it was
    unreachable.  A divergence list whose sole extra member is a false positive is
    worse than a shorter list, so it was removed; the check it was standing in for
    -- that ``use`` agrees with the recorded rule across the whole range -- is a
    **test** now (``test_the_use_arm_agrees_with_the_recorded_rule_across_its_whole_
    range``), which is where a comparison over derived values belongs.
    """
    reasons: List[str] = []
    if not had_recorded_entry:
        reasons.append("preserved_absent_key_arm_writes_zero")
    if operation == "buy" and before + 1 > cap:
        reasons.append("preserved_buy_increment_is_unbounded")
    return tuple(reasons)


class MagicSuccess(BaseModel):
    """A magic-counter transition the domain decided to perform.

    **The first v1 success that moves no stored resource at all**, and the only
    one whose transaction is not about a resource.  That is the whole of design
    D2 and it is why this model exists separately from :class:`Success` and
    :class:`CollectionSuccess` rather than being folded into either:

    * it has no ladder, no rung, no elapsed time, and no price;
    * it has a **committed row reported verbatim** beside the player's recorded
      level, with the two deliberately **not compared**;
    * it carries **no deltas at all**, because there is nothing to charge.

    The three guarantees the other two successes carry are restated, because they
    are what makes a success reportable rather than merely claimed:

    * ``transition`` is **required and non-optional**, and a
      :class:`~server_v1_magic.MagicTransition` can only be issued by that
      module's own token, so a hand-written counter value is unconstructible;
    * ``state`` is the seven stored resources read **back** from the store, so a
      caller cannot report a success without having read what it reports;
    * ``ledger_after`` is the magic ledger **after** the write, read back, so the
      "exactly one leaf path changed" proof is over the store's own bytes rather
      than over an in-memory value the slice carried forward.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    #: Required and non-optional: the mechanism, not a convention.
    transition: Any
    #: The instant the transaction reported (Unix seconds).  **The preserved
    #: branches record no instant at all**, so nothing in the store holds this
    #: one; it is reported so a client can see the server's own clock.
    instant: int
    #: Every stored resource after execution, read back from the store.
    state: Dict[str, int] = Field(min_length=1)
    #: The addressed counter after execution, equal to the derived value.
    counter_after: int
    #: The magic ledger's own keys after execution, in stored order.
    ledger_after: Tuple[str, ...]

    def payload(self) -> Dict[str, Any]:
        """The transport body for this success (envelope added by the route).

        Reports the **derived** figures, never a client figure, and the
        **committed row verbatim** -- never a value computed from it.  There is
        no ``derived_deltas`` key at all rather than an empty one, because a
        charge of nothing is the claim this line exists to make and an empty
        mapping invites a reader to treat it as a formatting accident.
        """
        transition = self.transition
        committed = dict(transition.committed)
        return {
            "result": "success",
            "action": self.action,
            "instant": self.instant,
            "magic": {
                "requested_id": transition.magic_id,
                "resolved_id": transition.magic_id,
                "operation": transition.operation,
                "ledger_key": str(transition.magic_id),
                "transition_id": transition.transition_id,
            },
            "counter": {
                "before": transition.before,
                "after": transition.after,
                "had_recorded_entry": transition.had_recorded_entry,
                "cap": transition.cap,
                "at_cap": transition.at_cap,
                "cap_is": transition.cap_provenance["cap_is"],
            },
            "committed": committed,
            "resources_after": dict(self.state),
            "stored_resources_compared": sorted(self.state),
            "counter_after": self.counter_after,
            "ledger_after": list(self.ledger_after),
            "same_transition_for_both_operations": True,
            "divergences": list(
                _divergence_reasons(
                    operation=str(transition.operation),
                    had_recorded_entry=bool(transition.had_recorded_entry),
                    before=int(transition.before),
                    after=int(transition.after),
                    cap=int(transition.cap),
                )
            ),
            "preserved_branch_behaviour": PRESERVED_MAGIC_BEHAVIOUR,
            "price_charged": None,
        }


__all__ = [
    "PRESERVED_MAGIC_BEHAVIOUR",
    "SUCCESS_HTTP_STATUS",
    "CollectionSuccess",
    "MagicSuccess",
    "Outcome",
    "Success",
]


#: What a domain service returns.  Four arms, no ``None``.
#:
#: The three successes are separate frozen models rather than one model with
#: optional halves, and :class:`CollectionSuccess`'s own docstring says why;
#: :class:`MagicSuccess` carries the same argument with nothing left to remove.
#: Declared last, after every class it names, because ``Union`` resolves its
#: arguments when it is evaluated: the first version of this module put the
#: union above ``CollectionSuccess`` and the service failed to import at all.
Outcome = Union[Success, CollectionSuccess, MagicSuccess, Refusal]
