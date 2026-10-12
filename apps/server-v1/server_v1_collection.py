#!/usr/bin/env python3
"""The collection-grant vertical slice: decide, derive, grant, then prove.

**Tasks 2.1-2.7.**  The second action on the v1 boundary, and the first whose
authority is a **grant** rather than a payout.  ``collect`` derives what a row
*yields*; ``complete_collection`` derives what a player *may have* and what it
*was worth*, both from committed content, and then grants it.

The preserved branch this replaces (``command.py:504-523``) is fourteen lines and
it grants **unconditionally**:

.. code-block:: python

    prize = get_collection_prize(collection_id)   # committed content
    for key in prize:
        add_store_item(map, int(key), prize[key])  # granted, no check
    if collection_id not in privateState["collections"]:
        privateState["collections"].append(collection_id)  # conditional

Three facts compose into the hole this slice closes, and all three were measured
before the proposal rather than after:

= ========================================================== ===================
# fact                                                         where
= ========================================================== ===================
1 the prize is committed content, so it *can* be derived        ``get_game_config.py:170-175``
2 ``item_ids`` and ``cashPrice`` have **zero** legacy           six counting rules
  consumers across all seven root modules                       over 7 modules
3 the grant is unconditional while the ledger append is          ``command.py:517-518``
  conditional, so a repeat completion grants again
= ========================================================== ===================

v1 adds three rules the branch does not have: **eligibility** from
``item_ids``, a **price** from ``cashPrice``, and a **once-only** gate on the
ledger.  Each is DERIVED (design D4, D5, D6), so each is a **divergence** from
the preserved branch and never parity — there is no oracle for a rule the
preserved server does not implement, which is the same position
``godot-darts-premium`` recorded for ``PREMIUM_ACCOUNTS``.

## Refusal order, and why it is not arbitrary

The five decisions run in a fixed order, and the order is a reportability
choice rather than an optimisation:

1. **alias / unresolvable id** (design D3) — the request addresses something
   that is not a distinct committed collection, so there is nothing to price,
   grant, or gate.  A refusal that answered "you already claimed this" for an id
   that names nothing would be reporting a fact about a different request.
2. **content readability** — the row resolved, so its fields exist; if they do
   not decode there is no requirement set, no price and no prize to derive, and
   the honest answer is ``unreadable_content`` (500), not a gameplay one.
3. **already claimed** (design D6) — the strongest true statement about a
   repeat.  Checked **before** eligibility so a repeat completion is answered
   with the reason it is being refused *for*, rather than with "you no longer
   hold the items", which is a true statement about a different question.
4. **eligibility** (design D4) — may the player have it at all.
5. **affordability** (D5) — last, because it is the only one that is a question
   about the player's balance rather than about the collection itself.  The
   progression "may you claim -> do you qualify -> can you pay" is the order
   each rule is *about*, and it means each has an independently reachable
   refusal: a request that fails 3 and 4 is reported as 3, so the tests can pin
   each code without needing a state that satisfies all the others.

None of the five uses a value from the request.  The only request value is the
id, and the id decides *which* committed row is read, never what anything costs.

## The design's corpus premise is corrected here, not quietly inherited

``design.md`` recorded that the fresh-player corpus "**can** exercise the grant"
because ``maps[0].store == {}`` and ``privateState.collections == []``.  That
was true of the *preserved* branch and is **false of this one**: the committed
collection 1 requires ``item_ids`` ``[66,67,68,69,70]``, and the corpus holds none
of them, so a first completion is refused ``collection_not_eligible``.  The
corpus is therefore not a ready-made grant; a grant needs the requirement items
**seeded into storage first**, which is what
``apps/client-godot/tests/test_collection_v1.gd``'s live scenario does and
records.  The design's claim about *the ledger* still holds — the corpus ledger
is empty, so the once-only gate is genuinely reachable for a first claim — and
it is only the prematurity of the grant that was wrong.

## The post-execution proof (design D7)

Four ordered halves, no one of which can pass while another is violated, and
all four enforced by one list :func:`_half_checks` walks:

* **storage, granted quantity**: the granted prize item's quantity moved by
  exactly the committed prize quantity.  A store that granted an extra unit,
  or re-granted an old one, fails.
* **storage, no unexpected key**: no stored key appeared that was not there
  before, **besides the granted item's own key** — which is expected to appear
  when the player held none, and is excluded by name rather than by skipping the
  half, so an un-granted extra key still fails.  A key that **vanished** is not
  caught, and that limit is recorded in :func:`_prove`'s docstring rather than
  quietly widened.
* **resources**: **every** stored resource changed by exactly the derived
  delta — ``cash`` by ``-price`` and all six others by zero.  Checked over the
  complete stored set, so a store that also moved ``gold`` fails.
* **ledger**: exactly one appended id, the derived one, and nothing else
  changed.  The comparison is against the whole derived list, so a re-ordered
  or partially-written ledger fails.

The ``resources`` half is what makes the ``cashPrice`` claim non-tautological:
the preserved branch charges nothing, so a service that granted everything and
charged nothing would fail on the ``cash`` half alone.  It is the third of this
project's "the proof must be able to fail on the thing the line claims" forms,
after ``collect``'s instant-moved-forward and ``expand``'s appended-id halves.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple, Union

from server_v1_content import CommittedContent, ContentError
from server_v1_economy import issue_collection_grant
from server_v1_intent import Intent
from server_v1_outcomes import CollectionSuccess, Outcome
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES, RepositoryError, SaveRepository

ACTION = "collection"


class PostConditionViolation(Exception):
    """The executed grant did not produce the state its derivation required.

    Never a client-visible game answer: the slice converts it into a
    ``post_condition_violation`` refusal and rolls the store back, exactly as
    ``server_v1_collect`` does.  The rollback is a second write, so this
    refusal is byte-identical *by having been put back*, never by having never
    written — and the two cases are reported separately in its ``detail``.
    """


def complete_collection(
    intent: Intent,
    content: CommittedContent,
    repository: SaveRepository,
    now: int,
) -> Outcome:
    """Execute one collection-completion intent, or refuse it by name.

    ``now`` is the service's own clock, passed in rather than read here, so a
    test can pin it.  It is never a request value: the intent has no field it
    could arrive in.  Note that the preserved branch records **no** instant at
    all, so nothing in the store holds this one — it is reported so the client
    can see the server's clock, and the field that would hold it does not exist.
    """
    # ---- 1. read ----------------------------------------------------------
    try:
        document = repository.read(intent.player_id)
        before_resources = document.resources()
        before_storage = document.storage()
        before_ledger = document.ledger()
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 2. resolve the id (design D2, D3) --------------------------------
    resolved = _resolve(content, intent.collection_id)
    if isinstance(resolved, Refusal):
        return resolved
    position, resolved_id, clamp_moved = resolved

    # ---- 3. content readability ------------------------------------------
    try:
        price = content.collection_cash_price(position)
        requirement_ids = content.collection_requirement_ids(position)
        prize = content.collection_prize(position)
    except ContentError as error:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed content is unusable: %s" % error,
            {"content_code": error.code},
        )
    if price is None:
        return _unreadable_row_field(position, "cashPrice", resolved_id)
    if requirement_ids is None:
        return _unreadable_row_field(position, "item_ids", resolved_id)
    if prize is None:
        return _unreadable_row_field(position, "prize", resolved_id)
    prize_item_id, prize_quantity = prize

    # ---- 4. decide, writing nothing --------------------------------------
    # 4a. the once-only gate (design D6), deliberately before eligibility.
    if resolved_id in before_ledger:
        return _refuse(
            RefusalCode.COLLECTION_ALREADY_CLAIMED,
            "collection %d is already in save %r's recorded collection ledger"
            % (resolved_id, intent.player_id),
            {
                "player_id": intent.player_id,
                "collection_id": resolved_id,
                "ledger_before": list(before_ledger),
                "ledger_is": "privateState.collections",
            },
        )

    # 4b. eligibility (design D4): hold every committed requirement id.
    missing: List[int] = []
    held_ids: List[int] = []
    for item_id in requirement_ids:
        try:
            quantity = document.storage_quantity(item_id)
        except RepositoryError as error:
            return _repository_refusal(error, intent)
        if quantity < 1:
            missing.append(item_id)
        else:
            held_ids.append(item_id)
    if missing:
        return _refuse(
            RefusalCode.COLLECTION_NOT_ELIGIBLE,
            "save %r does not hold every committed requirement for collection %d"
            % (intent.player_id, resolved_id),
            {
                "player_id": intent.player_id,
                "collection_id": resolved_id,
                "requirement_ids": list(requirement_ids),
                "missing_requirement_ids": missing,
                "held_requirement_ids": held_ids,
                "storage_is": "maps[0].store",
            },
        )

    # 4c. affordability (design D5): the derived price against the read balance.
    if before_resources["cash"] < price:
        return _refuse(
            RefusalCode.INSUFFICIENT_CASH,
            "collection %d costs %d cash, which save %r does not hold"
            % (resolved_id, price, intent.player_id),
            {
                "player_id": intent.player_id,
                "collection_id": resolved_id,
                "derived_price": price,
                "cash_before": before_resources["cash"],
                "shortfall": price - before_resources["cash"],
                "cash_is": "playerInfo.cash",
                "cash_price_is": "committed collections.cashPrice",
            },
        )

    grant = issue_collection_grant(
        requested_collection_id=intent.collection_id,
        resolved_collection_id=resolved_id,
        position=position,
        clamp_moved=clamp_moved,
        requirement_ids=requirement_ids,
        price=price,
        prize_item_id=prize_item_id,
        prize_quantity=prize_quantity,
        deltas={"cash": -price},
        committed={
            "row_position": position,
            "collection_id": resolved_id,
            "requested_collection_id": intent.collection_id,
            "item_ids": list(requirement_ids),
            "cashPrice": price,
            "prize": {"item_id": prize_item_id, "quantity": prize_quantity},
        },
    )

    # ---- 5. apply, in memory only ----------------------------------------
    # The snapshot is taken after the decision and before the first mutation,
    # so a rollback restores the exact bytes the request found.
    snapshot = document.snapshot()
    prize_before = before_storage.get(str(prize_item_id), 0)
    try:
        document.set_resource("cash", before_resources["cash"] - price)
        document.set_storage_quantity(prize_item_id, prize_before + prize_quantity)
        document.set_ledger(tuple(before_ledger) + (resolved_id,))
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
        after_resources = after.resources()
        after_storage = after.storage()
        after_ledger = after.ledger()
    except RepositoryError as error:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the store could not be read back after the write: %s" % error,
            {"half": "read_back", "cause": error.code, "rolled_back": restored},
        )

    try:
        _prove(
            grant=grant,
            before_resources=before_resources,
            after_resources=after_resources,
            before_storage=before_storage,
            after_storage=after_storage,
            before_ledger=before_ledger,
            after_ledger=after_ledger,
        )
    except PostConditionViolation as violation:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the executed grant did not produce its derived post-state: %s" % violation,
            {
                "half": _violated_half(
                    grant=grant,
                    before_resources=before_resources,
                    after_resources=after_resources,
                    before_storage=before_storage,
                    after_storage=after_storage,
                    before_ledger=before_ledger,
                    after_ledger=after_ledger,
                ),
                "addressed_path": intent.addressed_path(),
                "rolled_back": restored,
            },
        )

    # ---- 8. report --------------------------------------------------------
    return CollectionSuccess(
        action=ACTION,
        grant=grant,
        instant=now,
        state=after_resources,
        prize_stored_after=_quantity(after_storage, prize_item_id),
        ledger_after=tuple(after_ledger),
    )


# --------------------------------------------------------------------- resolve --


def _resolve(
    content: CommittedContent, collection_id: int
) -> Union["Tuple[int, int, bool]", Refusal]:
    """Resolve a requested collection id to a committed row position.

    Returns ``(position, resolved_id, clamp_moved)``, or a **refusal** when the
    id does not name a distinct committed collection.  The refusal is returned
    rather than raised because "the table is unreadable" and "this id names
    nothing" are different answers (500 versus 409) and a union of a
    three-tuple and a ``Refusal`` with no third sentinel is the honest way to
    carry both: the caller's ``isinstance`` test is total, and a third
    representation would be a value with no name.

    **The positional index is ESTABLISHED and the refusal is DERIVED.**
    ``get_collection_prize`` (``get_game_config.py:170-175``) computes
    ``index = max(0, collection - 1)`` and indexes the array, which means id
    ``1`` and position ``0`` agree only because the committed ids happen to run
    ``1..10`` in array order.  v1 keeps that positional addressing (design D2:
    a second addressing rule with the same name would be worse than one odd
    index) and refuses the two things it makes possible (design D3).

    The clamp is computed against ``collection_id - 1`` rather than against the
    resolved row so the flag describes the **request**, not the outcome: an id
    of ``0`` is aliased even though the row it lands on is a perfectly good
    committed collection, and that is the whole point of the refusal.
    """
    rows = content.collection_rows()
    if not rows:
        return _refuse(
            RefusalCode.UNRESOLVABLE_COLLECTION,
            "the committed collections table is empty, so id %d addresses nothing"
            % collection_id,
            {"requested_collection_id": collection_id, "committed_rows": 0},
        )

    # Every value below ``1`` clamps: ``max(0, -1)``, ``max(0, -5)``, ... all
    # equal ``0``.  The one thing the client learns is which id it collides
    # with, which is read from the committed table rather than assumed to be
    # ``1`` — an assumption would be wrong the day a row is inserted at the
    # head with a different committed id.
    if collection_id < 1:
        aliases = content.collection_id(0)
        return _refuse(
            RefusalCode.ALIASED_COLLECTION_ID,
            "collection id %d clamps to committed position 0 through the legacy "
            "max(0, id-1) index, so it addresses collection %r and is refused "
            "rather than granted" % (collection_id, aliases),
            {
                "requested_collection_id": collection_id,
                "clamped_position": 0,
                "aliases_collection_id": aliases,
                "legacy_index": "max(0, collection - 1)",
            },
        )

    position = collection_id - 1
    if position >= len(rows):
        return _refuse(
            RefusalCode.UNRESOLVABLE_COLLECTION,
            "collection id %d resolves to position %d, and the committed table "
            "holds only %d rows" % (collection_id, position, len(rows)),
            {
                "requested_collection_id": collection_id,
                "resolved_position": position,
                "committed_rows": len(rows),
                "resolves_to": None,
            },
        )

    resolved_id = content.collection_id(position)
    if resolved_id is None:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed row at position %d has no usable id" % position,
            {"row_position": position, "field": "id"},
        )

    # ``clamp_moved`` is derived, not assumed: the committed table's own
    # ``id`` at the resolved position is compared against the requested id, so
    # a re-ordered or renumbered committed table reports the disagreement
    # instead of hiding it.
    return (position, int(resolved_id), int(resolved_id) != int(collection_id))


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=dict(detail))


def _unreadable_row_field(position: int, field: str, resolved_id: int) -> Refusal:
    return _refuse(
        RefusalCode.UNREADABLE_CONTENT,
        "committed collection %d at position %d has no usable %r field"
        % (resolved_id, position, field),
        {"row_position": position, "collection_id": resolved_id, "field": field},
    )


def _repository_refusal(error: RepositoryError, intent: Intent) -> Refusal:
    """Map a repository failure onto a refusal code, as ``collect`` does."""
    if error.code == "unknown_player":
        return _refuse(
            RefusalCode.UNKNOWN_PLAYER, str(error), {"player_id": intent.player_id}
        )
    return _refuse(
        RefusalCode.UNREADABLE_STATE,
        str(error),
        {"player_id": intent.player_id, "cause": error.code},
    )


def _half_checks(
    *,
    grant: Any,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    before_storage: Dict[str, Any],
    after_storage: Dict[str, Any],
    before_ledger: Sequence[int],
    after_ledger: Sequence[int],
) -> Tuple[Tuple[str, str], ...]:
    """Each proof half, in the order :func:`_prove` enforces them.

    Returns ``(half_name, failure_message)`` pairs where an **empty** message
    means the half held.  One ordered list is walked by both :func:`_prove` and
    :func:`_violated_half`, which is what makes the reported half unable to
    drift from the enforced one — the defect this shape replaces was a
    ``_violated_half`` that recomputed three conditions independently and could
    have reported a half that had not actually failed.
    """
    # 1. storage: the granted item moved by exactly the committed quantity.
    granted_before = _quantity(before_storage, grant.prize_item_id)
    granted_after = _quantity(after_storage, grant.prize_item_id)
    checks: List[Tuple[str, str]] = [
        (
            "storage_granted_quantity",
            ""
            if granted_after - granted_before == grant.prize_quantity
            else "the granted item %d moved by %r, not by the committed %r"
            % (
                grant.prize_item_id,
                granted_after - granted_before,
                grant.prize_quantity,
            ),
        )
    ]
    # 2. storage: no key appeared **besides the granted one**.  The granted
    #    item's key is expected to appear when the player held none, so it is
    #    excluded by name rather than the half being skipped: an un-granted extra
    #    key still fails.  **Disappeared is not checked here**: the quantity half
    #    above fails if a tracked item's count moves, but a whole key vanishing
    #    is caught only for the granted item.  That is deliberate rather than an
    #    oversight — see the note in ``_prove``.
    granted_key = str(grant.prize_item_id)
    gained = sorted((set(after_storage) - set(before_storage)) - {granted_key})
    if gained:
        checks.append(
            (
                "storage_gained_an_unexpected_key",
                "the store gained the unexpected key(s) %r" % (gained,),
            )
        )
    else:
        checks.append(("storage_gained_an_unexpected_key", ""))

    # 3. resources: every stored resource moved by exactly the derived delta.
    moved_wrong = sorted(
        name
        for name in STORED_RESOURCE_NAMES
        if after_resources.get(name) != before_resources[name] + grant.delta_for(name)
    )
    if moved_wrong:
        checks.append(
            (
                "resources_matched_derivation",
                "stored resource(s) %r did not move by the derived delta" % (moved_wrong,),
            )
        )
    else:
        checks.append(("resources_matched_derivation", ""))

    # 4. ledger: exactly one appended id, the derived one, nothing else changed.
    derived_ledger = list(before_ledger) + [grant.resolved_collection_id]
    if list(after_ledger) != derived_ledger:
        checks.append(
            (
                "ledger_matched_derived",
                "the collection ledger became %r, not the derived %r"
                % (list(after_ledger), derived_ledger),
            )
        )
    else:
        checks.append(("ledger_matched_derived", ""))
    return tuple(checks)


def _prove(
    *,
    grant: Any,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    before_storage: Dict[str, Any],
    after_storage: Dict[str, Any],
    before_ledger: Sequence[int],
    after_ledger: Sequence[int],
) -> None:
    """The post-execution proof (design D7), in four ordered halves.

    **A store key that vanished without a trace is not caught.**  This is
    recorded rather than fixed: the granted item's quantity is checked, so a
    grant that removed and re-added it would be caught, but a *different*
    stored item being deleted leaves no "gained key" trace and no quantity
    check of its own.  The half that would catch it is a whole-store
    before/after key comparison, and adding it here would make every refused
    rollback path responsible for restoring a store it reads before deciding —
    which is a different change than this slice is.  The corpus holds exactly
    one stored key after a grant, so the gap is not reachable from the
    committed fixture either way; it is recorded as a limit, and
    ``tests/test_collection.py`` asserts the gap is at least *reported*.
    """
    for half, message in _half_checks(
        grant=grant,
        before_resources=before_resources,
        after_resources=after_resources,
        before_storage=before_storage,
        after_storage=after_storage,
        before_ledger=before_ledger,
        after_ledger=after_ledger,
    ):
        if message:
            raise PostConditionViolation(message)


def _violated_half(**kwargs: Any) -> str:
    """Which half of the proof failed, in the order the proof enforces them.

    Walks the same ordered list :func:`_prove` does, so a half that has not
    failed cannot be reported.  ``"none"`` is only reachable if the proof and
    this function disagree about what a failure is, which is itself a defect.
    """
    for half, message in _half_checks(  # type: ignore[arg-type]
        **kwargs
    ):
        if message:
            return half
    return "none"


def _quantity(storage: Dict[str, Any], item_id: int) -> int:
    """A stored quantity as an int, with ``0`` for an absent or unreadable key."""
    raw = storage.get(str(item_id), 0)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return raw


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


__all__ = ["ACTION", "PostConditionViolation", "complete_collection"]
