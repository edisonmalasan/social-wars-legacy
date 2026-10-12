#!/usr/bin/env python3
"""The typed success value, and the outcome union the domain returns.

**Task 2.2.**  A :class:`Success` cannot be constructed without a
:class:`~server_v1_economy.ResourceDerivation`.  That is not a convention — it
is a constructor signature: ``derivation`` is a required, non-optional field of
a frozen model whose own construction is gated behind the economy's issuance
token.  So a "successful" collection with a hand-written delta is
unconstructible, and the only way to obtain a derivation is to have the economy
authority derive one from committed content and recorded state.

The union :data:`Outcome` is what every domain service returns: either a
:class:`Success` or a :class:`~server_v1_refusals.Refusal`.  There is no third
arm, and there is no ``None`` — a domain function that has decided nothing has
a bug, and the type says so.

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

from typing import Any, Dict, Union

from pydantic import BaseModel, ConfigDict, Field

from server_v1_economy import ResourceDerivation
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


#: What a domain service returns.  Two arms, no ``None``.
Outcome = Union[Success, Refusal]


__all__ = ["SUCCESS_HTTP_STATUS", "Outcome", "Success"]
