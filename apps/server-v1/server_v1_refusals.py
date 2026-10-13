#!/usr/bin/env python3
"""The typed refusal value and Server v1's refusal vocabulary.

**Decision (task 2.6): a fresh, deliberately small v1 set — not a curated
subset of the Compatibility API's 104 constants.**  The rationale, recorded
here because the decision belongs with the codes:

* ``docs/legacy-m13-authority.md`` §5 measured **104** declared
  ``ERROR_*``-family constants across **24** v0 routes, of which **three** are
  declared and referenced nowhere.  That vocabulary is *route*-shaped: the
  names exist because a particular route needed one, which is precisely the
  shape design **D2** refuses to inherit.
* design D1 keeps v0 serving and design's non-goals forbid "shared code between
  v0 and v1 domain layers in this line".  Reusing v0's constants would couple
  v1 to the surface v1 is meant eventually to replace, and would make v1's
  domain vocabulary a function of a surface that is scheduled to be retired.
* The *names* v1 uses describe the **domain reason**, not the route that hit
  it: ``BELOW_FIRST_RUNG`` rather than v0's ``too_early``,
  ``UNADDRESSABLE_ROW`` rather than v0's ``unknown_item_index``.

Where v0 has an equivalent code, :data:`V0_EQUIVALENT_CODES` records it.  That
table is **documentation, not an import**: it exists so the two surfaces can be
compared by a human without a code-level dependency, and
``tests/test_refusals.py`` asserts no v1 module imports anything from
``apps/compat-api``.

**The status code lives here, not in the transport.**  D2 requires the route to
"translate the returned outcome"; a per-route status table is how v0 ended up
with 24 answers to the same question.  :data:`REFUSAL_HTTP_STATUS` is one
closed mapping, asserted by test to cover every declared code exactly once, and
``server_v1_app.py`` reads it without ever naming a code.

**Round-tripping (task 2.1).**  ``Refusal`` is a frozen Pydantic model, so the
value the domain produces *is* the value the transport serialises.  There is
no second representation to drift.  ``tests/test_refusals.py`` round-trips
**every** declared code through ``json.loads(refusal.model_dump_json())`` back
into a model and asserts equality, so a code that cannot survive the wire fails
rather than being reported as covered.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping

from pydantic import BaseModel, ConfigDict, Field


class RefusalCode(str, Enum):
    """Every reason Server v1's domain can decline an action.

    A closed enum, not free strings.  ``tests/test_refusals.py`` asserts both
    directions: every ``RefusalCode.X`` any v1 module names is declared here,
    and every code declared here is used somewhere in ``apps/server-v1/``.  A
    declared-but-unused code is dead vocabulary — the same defect
    ``docs/legacy-m13-authority.md`` §5 found three of in v0 — and a
    used-but-undeclared code could not have been constructed at all, since the
    enum is the only way to name one.
    """

    # -- structural input errors: the request itself is not a v1 request ------
    MALFORMED_REQUEST = "malformed_request"
    CLIENT_SUPPLIED_DELTA = "client_supplied_delta"
    UNKNOWN_REQUEST_FIELD = "unknown_request_field"

    # -- addressability and content ----------------------------------------
    UNKNOWN_PLAYER = "unknown_player"
    UNADDRESSABLE_ROW = "unaddressable_row"
    NO_COMMITTED_INCOME = "no_committed_income"
    CAPPED_COLLECTION = "capped_collection"
    BELOW_FIRST_RUNG = "below_first_rung"
    CONSTRUCTION_IN_PROGRESS = "construction_in_progress"
    #: The requested collection id does not name a distinct committed
    #: collection: the integer zero and every negative id clamp to the first row
    #: through the legacy ``max(0, collection - 1)`` index, so they resolve to
    #: collection 1 and are refused rather than served its prize (design D3).
    ALIASED_COLLECTION_ID = "aliased_collection_id"
    #: No committed collection resolves at the id's position (design D3).
    UNRESOLVABLE_COLLECTION = "unresolvable_collection"
    #: The player does not hold every committed ``item_ids`` entry (design D4).
    COLLECTION_NOT_ELIGIBLE = "collection_not_eligible"
    #: The collection is already in the player's recorded ledger (design D6).
    COLLECTION_ALREADY_CLAIMED = "collection_already_claimed"
    #: The stored cash is below the collection's committed ``cashPrice``
    #: (design D5).  Note this is **affordability**, which is a different
    #: question from ``no_committed_income``/``capped_collection``: those two are
    #: about content v1 refuses to interpret, this one is about a balance v1
    #: read.
    INSUFFICIENT_CASH = "insufficient_cash"
    #: The requested magic id names no distinct committed magic row.  Unlike
    #: ``ALIASED_COLLECTION_ID`` there is no clamped neighbour to distinguish:
    #: the preserved ``buy_magic``/``use_magic`` branches never index the
    #: committed table at all, so zero and every negative simply resolve to
    #: nothing rather than aliasing another row (design D3 of this line).
    UNKNOWN_MAGIC_ID = "unknown_magic_id"
    #: The player's recorded counter for this magic is already above the
    #: recorded literal bound, so the bounded derivation cannot produce a value
    #: from it.  The recorded counter is reported, never rewritten (design D6).
    COUNTER_ABOVE_CAP = "counter_above_cap"

    # -- server-side integrity: never a client-visible gameplay answer -------
    UNREADABLE_STATE = "unreadable_state"
    UNREADABLE_CONTENT = "unreadable_content"
    POST_CONDITION_VIOLATION = "post_condition_violation"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


#: The one closed code -> HTTP status table (see the module docstring).
REFUSAL_HTTP_STATUS: Dict[RefusalCode, int] = {
    # Structural: the client sent something that is not a v1 request.  These
    # are the codes design **D3** requires — refused, never clamped, coerced,
    # or partially honoured.
    RefusalCode.MALFORMED_REQUEST: 400,
    RefusalCode.CLIENT_SUPPLIED_DELTA: 400,
    RefusalCode.UNKNOWN_REQUEST_FIELD: 400,
    # No such save in this repository.
    RefusalCode.UNKNOWN_PLAYER: 404,
    # The request is well formed and the player exists, but the requested
    # action conflicts with recorded state or committed content.
    RefusalCode.UNADDRESSABLE_ROW: 409,
    RefusalCode.NO_COMMITTED_INCOME: 409,
    RefusalCode.CAPPED_COLLECTION: 409,
    RefusalCode.BELOW_FIRST_RUNG: 409,
    RefusalCode.CONSTRUCTION_IN_PROGRESS: 409,
    RefusalCode.ALIASED_COLLECTION_ID: 409,
    RefusalCode.UNRESOLVABLE_COLLECTION: 409,
    RefusalCode.COLLECTION_NOT_ELIGIBLE: 409,
    RefusalCode.COLLECTION_ALREADY_CLAIMED: 409,
    RefusalCode.INSUFFICIENT_CASH: 409,
    RefusalCode.UNKNOWN_MAGIC_ID: 409,
    RefusalCode.COUNTER_ABOVE_CAP: 409,
    # Something on this server is wrong.  These are deliberately *not*
    # disguised as gameplay answers.
    RefusalCode.UNREADABLE_STATE: 500,
    RefusalCode.UNREADABLE_CONTENT: 500,
    RefusalCode.POST_CONDITION_VIOLATION: 500,
}


#: Human-readable, deliberately non-actionable descriptions of each code's
#: *kind*.  These are documentation strings, not messages: a ``Refusal``'s
#: message is written where the refusal is decided, because only the deciding
#: code knows the values involved.
REFUSAL_CODE_PURPOSE: Dict[RefusalCode, str] = {
    RefusalCode.MALFORMED_REQUEST: "the request body is not a JSON object",
    RefusalCode.CLIENT_SUPPLIED_DELTA: (
        "the request carried a resource, experience, health, damage, or result "
        "delta, which v1 refuses rather than clamps or discards"
    ),
    RefusalCode.UNKNOWN_REQUEST_FIELD: (
        "the request carried a field outside the action's intent schema"
    ),
    RefusalCode.UNKNOWN_PLAYER: "no save document exists for the named player",
    RefusalCode.UNADDRESSABLE_ROW: "no placement exists at the named row key",
    RefusalCode.NO_COMMITTED_INCOME: (
        "committed content records no collection income for the row's item"
    ),
    RefusalCode.CAPPED_COLLECTION: (
        "committed content records a non-zero collection cap, which v1 refuses "
        "rather than interprets"
    ),
    RefusalCode.BELOW_FIRST_RUNG: (
        "the row's recorded instant has not reached the first committed ladder "
        "rung, so no payout can be derived"
    ),
    RefusalCode.CONSTRUCTION_IN_PROGRESS: (
        "the row carries construction state and its instant is a build start, "
        "not a last-collection instant"
    ),
    RefusalCode.ALIASED_COLLECTION_ID: (
        "the requested collection id clamps to the first committed collection "
        "and therefore names no distinct collection"
    ),
    RefusalCode.UNRESOLVABLE_COLLECTION: (
        "no committed collection resolves at the position the requested id "
        "addresses"
    ),
    RefusalCode.COLLECTION_NOT_ELIGIBLE: (
        "the player does not hold every item id in the collection's committed "
        "requirement list"
    ),
    RefusalCode.COLLECTION_ALREADY_CLAIMED: (
        "the collection is already present in the player's recorded collection "
        "ledger, so the prize has already been granted"
    ),
    RefusalCode.INSUFFICIENT_CASH: (
        "the player's stored cash is below the collection's committed price"
    ),
    RefusalCode.UNKNOWN_MAGIC_ID: (
        "the requested magic id names no distinct row of the committed magic "
        "table"
    ),
    RefusalCode.COUNTER_ABOVE_CAP: (
        "the player's recorded counter for this magic is already above the "
        "recorded literal bound, so no next value can be derived from it"
    ),
    RefusalCode.UNREADABLE_STATE: "stored state this service cannot read",
    RefusalCode.UNREADABLE_CONTENT: "committed content this service cannot read",
    RefusalCode.POST_CONDITION_VIOLATION: (
        "the executed transaction did not produce the post-state its own "
        "derivation required"
    ),
}


#: The v0 code each v1 code corresponds to, as **documentation only**.  No v1
#: module imports this; ``tests/test_refusals.py`` asserts that.  v0 names that
#: do not appear here have no v1 counterpart in this line, because v1 does not
#: implement the route that raised them.
V0_EQUIVALENT_CODES: Dict[RefusalCode, str] = {
    RefusalCode.MALFORMED_REQUEST: "invalid_payload / bad_request",
    RefusalCode.CLIENT_SUPPLIED_DELTA: "(none — v0 has no such check; this is D3)",
    RefusalCode.UNKNOWN_REQUEST_FIELD: "(none — v0 ignores extra keys entirely)",
    RefusalCode.UNKNOWN_PLAYER: "unknown_user_id",
    RefusalCode.UNADDRESSABLE_ROW: "unknown_item_index",
    RefusalCode.NO_COMMITTED_INCOME: "no_income",
    RefusalCode.CAPPED_COLLECTION: "capped_collection",
    RefusalCode.BELOW_FIRST_RUNG: "too_early",
    RefusalCode.CONSTRUCTION_IN_PROGRESS: "construction_in_progress",
    RefusalCode.ALIASED_COLLECTION_ID: "(none — v0 clamps and serves it)",
    RefusalCode.UNRESOLVABLE_COLLECTION: "(none — v0 raises or clamps)",
    RefusalCode.COLLECTION_NOT_ELIGIBLE: "(none — v0 reports eligibility unchecked)",
    RefusalCode.COLLECTION_ALREADY_CLAIMED: "(none — v0 grants again)",
    RefusalCode.INSUFFICIENT_CASH: "(none — v0 charges nothing)",
    RefusalCode.UNKNOWN_MAGIC_ID: "unknown_magic_id",
    RefusalCode.COUNTER_ABOVE_CAP: "counter_above_cap",
    RefusalCode.UNREADABLE_STATE: "internal_error",
    RefusalCode.UNREADABLE_CONTENT: "internal_error",
    RefusalCode.POST_CONDITION_VIOLATION: "internal_error",
}


class Refusal(BaseModel):
    """A typed domain decision that an action did not happen.

    Frozen, so a refusal that has been handed to the transport cannot be
    edited into a different reason on the way out — which is the transport's
    whole remaining degree of freedom (design D2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: RefusalCode
    message: str
    #: Structured, JSON-safe context.  Every value is a scalar or a container
    #: of scalars, so ``model_dump_json`` -> ``json.loads`` -> ``model_validate``
    #: is lossless; ``tests/test_refusals.py`` asserts that for every code with
    #: a populated ``detail``.
    detail: Dict[str, Any] = Field(default_factory=dict)

    def payload(self) -> Dict[str, Any]:
        """The transport body for this refusal (envelope added by the route)."""
        return {
            "result": "refused",
            "code": self.code.value,
            "message": self.message,
            "detail": dict(self.detail),
        }

    @property
    def http_status(self) -> int:
        """The one status this code maps to (see :data:`REFUSAL_HTTP_STATUS`)."""
        return REFUSAL_HTTP_STATUS[self.code]


def json_safe(value: Any) -> bool:
    """Whether ``value`` survives ``model_dump_json`` -> ``validate`` unchanged.

    A guard the round-trip test uses to explain a failure rather than to
    discover one: a non-JSON value in ``detail`` is the only way a round trip
    can lose information, and this says so directly.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and json_safe(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(json_safe(item) for item in value)
    return False


__all__ = [
    "REFUSAL_CODE_PURPOSE",
    "REFUSAL_HTTP_STATUS",
    "V0_EQUIVALENT_CODES",
    "Refusal",
    "RefusalCode",
    "json_safe",
]
