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
:class:`Success`, a :class:`CollectionSuccess`, or a
:class:`~server_v1_refusals.Refusal`.  There is no other arm, and there is no
``None`` — a domain function that has decided nothing has a bug, and the type
says so.  **The third arm is a second success, not a refusal variant**: a
collection *grant* is a genuinely different transaction from a collection
*payout*, and the difference is a shape difference (no row, no rung, a prize in
storage and a price in cash) rather than a value difference, so it earns its own
frozen model with its own required derivation.

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

from typing import Any, Dict, Tuple, Union

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


#: What a domain service returns.  Three arms, no ``None``.  The same shape as
#: :data:`server_v1_intent.IntentOutcome`: two successes and one refusal.  The
#: transport tests the arm with ``isinstance``; nothing raises here.
#:
#: **Why a second success type rather than a wider first one.**
#: :class:`Success` is shaped around a collection transaction: a ladder rung,
#: an addressed row, and that row's recorded instant.  A collection **grant**
#: has no row, no rung, and no elapsed time - its shape is a prize in storage, a
#: price in cash, and an id appended to a ledger.  Widening :class:`Success`
#: would have meant optional fields that are ``None`` for one transaction and
#: populated for the other, and an optional field is a field a caller must
#: remember to check.  Two frozen models with a shared ``payload()`` keep the
#: transport's translation step total: ``dict(value.payload())`` works for both
#: arms, and neither arm can be constructed without its own derivation.
#:
#: Declared **after** both classes: the union is a runtime value and ``Union``
#: resolves its arguments when it is evaluated, so a union above the class it
#: names raises ``NameError``.  That is the one ordering constraint in this
#: module and it is a Python rule rather than a preference.


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


__all__ = ["SUCCESS_HTTP_STATUS", "CollectionSuccess", "Outcome", "Success"]


#: What a domain service returns.  Three arms, no ``None``.
#:
#: The two successes are separate frozen models rather than one model with
#: optional halves, and :class:`CollectionSuccess`'s own docstring says why.
#: Declared last, after both classes it names, because ``Union`` resolves its
#: arguments when it is evaluated: the first version of this module put the
#: union above ``CollectionSuccess`` and the service failed to import at all.
Outcome = Union[Success, CollectionSuccess, Refusal]
