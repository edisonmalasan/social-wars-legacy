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
    #: The request dictated how many rows the transaction destroys.  The
    #: preserved branch derives its count as ``max(0, unit[2] - unit[3])``
    #: (``command.py:868``) over two numbers the **client** sends, so the count
    #: is client-dictated and v1 refuses it outright: it is not applied, and it
    #: is not narrowed to a v1-derived figure either, because no committed value
    #: names an outcome for this action (design D5).
    #:
    #: **One code, not four.**  The same branch also reads and discards four
    #: other client quantities — ``honor``, ``resources``, ``resources_victim``
    #: and ``townhall_gold``.  Those are refused by the existing
    #: ``client_supplied_delta`` **key-name** channel rather than by a code each,
    #: because a code per un-derivable quantity is how a closed vocabulary stops
    #: being closed.
    CLIENT_DICTATED_DESTRUCTION = "client_dictated_destruction"

    # -- reward cursors (godot-rewards): five separate client-dictated inputs -
    #
    # **Why five codes and not one.**  The line's spec requires that "a request
    # carrying a next id, an offset, or any other cursor contribution ... SHALL
    # be refused as a structural input error" *and* that a request carrying "an
    # item id, a cell, a player identity, or a map index" has "each ... refused
    # with its own named reason".  A single code would satisfy the first
    # sentence and fail the second, so the four grant shapes are separate.  The
    # cursor is **one** code because the spec groups every cursor key into one
    # reason, and ``apps/compat-api/rewards_envelope.py``'s
    # ``CLIENT_KEY_REFUSALS`` has exactly one cursor row
    # (``client_supplied_next_id``) among its seven.
    #
    # **All five are 400, which diverges from two recorded precedents, and that
    # is deliberate.**  ``apps/compat-api`` answers all five with **409**
    # (``compat_service.py:1753-1766``), and v1's own
    # :data:`CLIENT_DICTATED_DESTRUCTION` answers its structurally identical
    # "you may not say how many" case with **409**.  v1 chooses **400** because
    # the deciding question is never about stored state: each refusal is
    # resolved by inspecting the *request body alone*, before the player, the
    # document, or the cursor is consulted, and the spec's own wording for the
    # cursor case is "a structural input error".  A status that implied
    # "well-formed request, conflicting state" would be untrue of all five.
    # ``tests/test_reward.py`` asserts the split rather than the set.
    CLIENT_DICTATED_CURSOR = "client_dictated_cursor"
    CLIENT_DICTATED_ITEM_GRANT = "client_dictated_item_grant"
    CLIENT_DICTATED_CELL = "client_dictated_cell"
    CLIENT_DICTATED_PLAYER = "client_dictated_player"
    CLIENT_DICTATED_MAP_INDEX = "client_dictated_map_index"

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
    # Decided from the request body alone; see the enum's comment for why these
    # five are 400 where v0 says 409 and where v1's own destruction code says
    # 409.
    RefusalCode.CLIENT_DICTATED_CURSOR: 400,
    RefusalCode.CLIENT_DICTATED_ITEM_GRANT: 400,
    RefusalCode.CLIENT_DICTATED_CELL: 400,
    RefusalCode.CLIENT_DICTATED_PLAYER: 400,
    RefusalCode.CLIENT_DICTATED_MAP_INDEX: 400,
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
    RefusalCode.CLIENT_DICTATED_DESTRUCTION: 409,
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
    RefusalCode.CLIENT_DICTATED_DESTRUCTION: (
        "the request carried a destruction count, which v1 refuses rather than "
        "applies or narrows to a v1-derived figure"
    ),
    RefusalCode.CLIENT_DICTATED_CURSOR: (
        "the request carried a next id, offset, or successor for a reward "
        "cursor, whose successor v1 derives from the recorded cursor alone"
    ),
    RefusalCode.CLIENT_DICTATED_ITEM_GRANT: (
        "the request carried an item id, which the preserved daily branch would "
        "write into storage and v1 refuses rather than grants"
    ),
    RefusalCode.CLIENT_DICTATED_CELL: (
        "the request carried a placement cell, whose coordinates the preserved "
        "weekly branch would read from the client"
    ),
    RefusalCode.CLIENT_DICTATED_PLAYER: (
        "the request carried a player identity beyond the one the save document "
        "is addressed by"
    ),
    RefusalCode.CLIENT_DICTATED_MAP_INDEX: (
        "the request carried a map index, which the preserved branch would read "
        "from the client when it writes a granted item"
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
    # **The status difference is deliberate, so it is recorded here rather than
    # left to be discovered as an inconsistency.**  The counterpart is
    # ``apps/compat-api/combat_envelope.py``'s refusal named
    # ``client_dictated_destruction``, the same literal v1 reuses as its code
    # *value*; its rule text is the ``CLIENT_DICTATED_REFUSAL`` constant there,
    # which v1 does not import (the table is documentation, not a dependency).
    #
    # v0's answer is a **4xx** because v0 applies the client-sent resource
    # vector *before* the dispatcher chain opens (``command.py:40``), so a
    # destruction figure reaches stored state as part of a request v0 treats as
    # structurally wrong.  v1's answer is a **409** because the request is
    # well-formed and the player exists: it names an action whose outcome
    # conflicts with what the client is allowed to decide.  The codes agree; the
    # statuses do not, and deliberately so.
    RefusalCode.CLIENT_DICTATED_DESTRUCTION: "client_dictated_destruction",
    # The five reward counterparts, all ``client_supplied_*`` in v0's vocabulary
    # and all **409** there (see ``compat_service.py:1753-1766``).  The code
    # names correspond one-for-one; the statuses deliberately do not, and the
    # reason is recorded at the enum member rather than left to be found as an
    # inconsistency.
    RefusalCode.CLIENT_DICTATED_CURSOR: "client_supplied_next_id",
    RefusalCode.CLIENT_DICTATED_ITEM_GRANT: "client_supplied_item",
    RefusalCode.CLIENT_DICTATED_CELL: "client_supplied_cell",
    RefusalCode.CLIENT_DICTATED_PLAYER: "client_supplied_player",
    RefusalCode.CLIENT_DICTATED_MAP_INDEX: "client_supplied_item_index",
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
