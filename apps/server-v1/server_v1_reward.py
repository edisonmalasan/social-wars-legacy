#!/usr/bin/env python3
"""M13 line 5 - the reward cursors become authoritative (design D1-D8).

This module is the **only** place in Server v1 where a reward cursor is
computed.  :func:`advance_reward` is the whole public surface; every helper below
it is private and exists so the derivation can be pinned as an inventory rather
than trusted as a convention (design D2, and the anti-invention guard
``tests/test_reward.py`` enforces).

**The line's whole argument is one substitution.**  The preserved daily branch
(``command.py:444-463``) computes ``next_id = args[1] + 1`` and then, at
:451, ``if next_id > 5: next_id = 1``.  The arithmetic is the server's own; its
*input* is the client's.  The weekly branch (``command.py:345-363``) is the same
shape, ``(stored + 1) % get_weekly_reward_length()``, with the stored term read
from the request.  So this module **keeps the arithmetic and replaces the input**:
the successor comes from the cursor the recorded document already carries.

**What that costs, stated plainly.**  The preserved daily branch can move a
recorded cursor **backwards** - an oversized client-sent next id takes a stored
``4`` to ``1``, which the committed fixture at ``tests/fixtures/godot-rewards/``
executes rather than argues.  This line does **not** reproduce that.  Reproducing
a client-directed cursor regression would defeat the entire purpose of making the
cursor authoritative, so the move is recorded as a **divergence** and is
unreachable through the delivered route.

**Three things this module deliberately does not do**, each because the oracle
gives nothing to derive from:

* **It pays nothing.**  Neither branch credits a stored resource.  The daily
  arm's "grant" is a client-sent item id written into storage and a
  deduplicating unit list; its non-granting arm only ``print``s.  Applying
  ``DAILY_GOLD_REWARDS`` would diverge from an oracle that pays nothing, so the
  committed schedules are reported and left unread.
* **It derives no eligibility rule.**  ``timestampLastBonus`` is written at
  ``command.py:454`` and subtracted at ``command.py:914`` inside
  ``fast_forward``, where the subtracted number is **client-supplied** - and it
  has **zero readers** across all eleven legacy modules.  There is no daily
  window, cooldown, or already-claimed check anywhere in the preserved server to
  reproduce.  The instant is written, reported, and never consulted.
* **It reproduces no grant.**  Every grant-shaped input is refused by name.

**The two bounds are not the same kind of number**, which is why
:data:`DAILY_BOUND` is a literal and :func:`_weekly_bound` is a derivation:

* daily
    the **literal** ``5`` at ``command.py:451``.  It happens to equal
    ``len(DAILY_GOLD_REWARDS)``, and that agreement is a **coincidence** - see
    :data:`DAILY_BOUND_REJECTED_DERIVATION`.  A derivation the oracle never
    performed is one legacy edit away from silently becoming a different rule.
* weekly
    the **preserved helper's own result**, reproduced rule for rule at
    :func:`_weekly_bound` rather than approximated, because the helper's floor and
    its list-valued-only ``max`` are both load-bearing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from pydantic import BaseModel

from server_v1_content import CommittedContent, ContentError
from server_v1_intent import Intent
from server_v1_outcomes import (
    PRESERVED_REWARD_BEHAVIOUR,
    Outcome,
    Refusal,
    RewardSuccess,
)
from server_v1_refusals import RefusalCode
from server_v1_repository import RepositoryError, SaveRepository

#: This line's action name, and the two arms it carries.
#:
#: The two spellings are the **v1** vocabulary, deliberately not the legacy
#: branch names: ``/v1/reward`` names the surface, and the request names which
#: cursor it wants advanced, not which legacy branch it thinks it is calling.
ACTION = "reward"

#: The closed two-value operation set, mirrored from
#: ``server_v1_intent.INTENT_OPERATIONS["reward"]`` and pinned against it by
#: ``tests/test_reward.py``.  A copy is necessary because the domain must be
#: total over its own surface without importing the request layer's table as a
#: second source of truth at runtime; the pin is what keeps them from drifting.
OPERATIONS: Tuple[str, str] = ("weekly", "daily")

#: The daily bound: the **preserved literal** at ``command.py:451``.
#:
#: Recorded as data with its provenance rather than inlined in the derivation, so
#: a reader can see that this number came from a line of legacy source and not
#: from a computation performed here.
DAILY_BOUND: int = 5

#: Why :data:`DAILY_BOUND` is **not** ``len(DAILY_GOLD_REWARDS)``, retained as
#: the rejected alternative.
#:
#: The committed schedule holds exactly five entries, so the two numbers agree
#: today.  They are different *kinds* of number: one is what the legacy server
#: compared against, the other is how many rows a table happens to have.  A
#: future edit that added or removed a schedule row would silently change a
#: rule the oracle never wrote.  The agreement is therefore recorded as a
#: **coincidence**, in these words, rather than resolved in favour of the
#: derivation - which is the mistake the delivered v0 line also declined to make.
DAILY_BOUND_REJECTED_DERIVATION: Dict[str, Any] = {
    "rejected": "len(DAILY_GOLD_REWARDS)",
    "reason": (
        "the preserved branch compares against a literal at command.py:451; it "
        "never asks the schedule how long it is"
    ),
    "agrees_today": True,
    "agreement_is": "a coincidence, not a derivation",
}

#: The bought-unit list's real location, measured from the committed corpus.
#:
#: ``privateState.boughtUnits`` and **not** ``maps[0].boughtUnits`` -- the latter
#: key is absent from the fresh-player document entirely, so a proof half reading
#: it would compare ``None`` with ``None`` and pass for any service, including
#: one that never looked.  The spec names this list explicitly, so it gets its
#: own half rather than riding on the whole-document comparison.
BOUGHT_UNITS_PATH: Tuple[str, str] = ("privateState", "boughtUnits")

#: The four grant channels, carried by ``server_v1_intent`` keyed by channel, and
#: mapped here to the reason each is refused by.
#:
#: The spec requires that "an item id, a cell, a player identity, or a map index"
#: has "each ... refused with its own named reason", so this mapping is a total
#: one-to-one: a single code would satisfy the cursor requirement and fail the
#: grant one.  The mapping lives in the **domain**, not in the request layer,
#: because whether a request's item id *would have been granted* is a rule about
#: the transaction and the request layer has no transaction.
GRANT_CHANNEL_REFUSALS: Dict[str, RefusalCode] = {
    "item": RefusalCode.CLIENT_DICTATED_ITEM_GRANT,
    "map_index": RefusalCode.CLIENT_DICTATED_MAP_INDEX,
    "cell": RefusalCode.CLIENT_DICTATED_CELL,
    "player": RefusalCode.CLIENT_DICTATED_PLAYER,
}


class PostConditionViolation(Exception):
    """Raised when the post-execution proof fails.

    A dedicated exception rather than a ``Refusal``, because the proof failing
    means the **service** is wrong, not the request - so it is answered ``500``
    as ``post_condition_violation`` and never presented as something the client
    did.
    """


class RewardTransition(BaseModel):
    """The derived cursor transition, before it is written.

    A frozen value rather than four loose locals, so the thing that is *derived*
    is one object that can be reported, compared, and pinned independently of the
    I/O around it.

    **``frozen=True``, and that is load-bearing rather than stylistic.**  The
    derivation happens before the write, so a mutable transition could be
    adjusted between :func:`_derive` and the proof -- and the proof compares the
    *stored* value against ``transition.cursor_after``, so a post-derivation
    edit would silently redefine what "derived" means.  ``test_reward.py`` holds
    the frozen-ness by assignment rather than by reading the docstring.
    """

    model_config = {"frozen": True}

    cursor_before: int
    cursor_after: int
    bound: int
    bound_provenance: str


def advance_reward(
    intent: Intent,
    content: CommittedContent,
    repository: SaveRepository,
    now: int,
) -> Outcome:
    """Advance one reward cursor from recorded state, or refuse it by name.

    ``now`` is the service's own clock, passed in rather than read here so a test
    can pin it.  It is never a request value: the reward intent has no field it
    could arrive in, and the only thing written from it is the stamped instant -
    which, as :data:`PRESERVED_REWARD_BEHAVIOUR` records, nothing ever reads.
    """
    # ---- 1. the client-sent channels, refused before the document ---------
    # Both channels resolve **before** any write, so a refused request leaves
    # the whole document byte-identical (design D8).  The cursor channel is
    # resolved first: it is the one input this line exists to make impossible.
    if intent.cursor_request is not None:
        return _refuse(
            RefusalCode.CLIENT_DICTATED_CURSOR,
            "the request carried a reward cursor contribution; v1 derives the "
            "successor from the recorded cursor alone",
            {
                "player_id": intent.player_id,
                "operation": intent.operation,
                "sent": intent.cursor_request,
                "sent_is": "carried verbatim and never read, compared, or clamped",
                "derived_from": "/privateState",
            },
        )

    for channel in ("item", "map_index", "cell", "player"):
        if channel in intent.grant_request:
            return _refuse(
                GRANT_CHANNEL_REFUSALS[channel],
                "the request carried a client-dictated %s; the preserved branch "
                "would have granted from it and v1 grants nothing" % channel,
                {
                    "player_id": intent.player_id,
                    "operation": intent.operation,
                    "channel": channel,
                    "sent": intent.grant_request[channel],
                    "sent_is": "carried verbatim and never read",
                },
            )

    if intent.operation not in OPERATIONS:  # pragma: no cover - parse_intent
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "a reward intent must name one of %s" % (list(OPERATIONS),),
            {"operation": intent.operation, "declared": list(OPERATIONS)},
        )

    # ---- 2. read ----------------------------------------------------------
    try:
        document = repository.read(intent.player_id)
        # **Deep-copied, not aliased and not ``raw()``.**  ``raw`` hands back
        # the live mapping, and the "nothing else moved" half of the proof
        # compares two documents -- taking the before side by reference would
        # make that half compare the after-state with itself, which is exactly
        # the aliasing hazard ``server_v1_magic`` records.  ``snapshot()`` is
        # the deep copy, and the docstring already names this reason.
        before_document = document.snapshot()
        # **Copied, not aliased**, for the reason ``server_v1_magic`` records:
        # the live mapping would change underneath the proof the moment the
        # write happened, and the "nothing else moved" half would compare the
        # after-state with itself.
        before_resources = dict(document.resources())
        before_storage = dict(document.storage())
        before_bought = list(document.private_state().get(BOUGHT_UNITS_PATH[1], []))
        cursor_before = document.reward_cursor(intent.operation)
        instant_before = document.reward_stamp(intent.operation)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 3. the derivation ------------------------------------------------
    try:
        transition = _derive(cursor_before, intent.operation, content)
    except ContentError as error:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed content is unusable: %s" % error,
            {"content_code": error.code},
        )

    # ---- 4. write ---------------------------------------------------------
    try:
        document.set_reward_cursor(intent.operation, transition.cursor_after)
        document.set_reward_stamp(intent.operation, now)
        # **The repository write is load-bearing and was missing from the first
        # draft.**  ``set_reward_cursor`` mutates the in-memory document; without
        # this line the whole transaction computed a successor, proved it
        # against the in-memory copy, reported it, and **persisted nothing** --
        # and the proof could not have caught it, because both sides of the
        # comparison were the same unpersisted object.  ``test_reward.py`` reads
        # the cursor back through a **second** ``repository.read`` for exactly
        # this reason, so a missing write fails the suite rather than passing it.
        repository.write(document)
        after_document = document.snapshot()
        after_resources = dict(document.resources())
        after_storage = dict(document.storage())
        after_bought = list(document.private_state().get(BOUGHT_UNITS_PATH[1], []))
    except RepositoryError as error:  # pragma: no cover - writes above succeeded
        return _repository_refusal(error, intent)

    # ---- 5. the two-part proof -------------------------------------------
    try:
        proof = (
            ("cursor advanced to its derived successor",
             after_storage is not None
             and _cursor_now(after_document, intent.operation)
             == transition.cursor_after),
            ("no stored resource moved", after_resources == before_resources),
            ("no item was granted into storage", after_storage == before_storage),
            ("the bought-unit list is byte-identical", after_bought == before_bought),
            ("nothing else in the document moved",
             set(_changed_leaf_paths(before_document, after_document))
             <= set(_expected_leaf_paths(intent.operation))),
        )
    except RepositoryError as error:  # pragma: no cover - read-back is total
        return _repository_refusal(error, intent)

    if not all(held for _, held in proof):
        failed = [check for check, held in proof if not held]
        raise PostConditionViolation(
            "reward proof failed: %s" % "; ".join(failed)
        )

    changed = tuple(_changed_leaf_paths(before_document, after_document))

    return RewardSuccess(
        action=ACTION,
        operation=intent.operation,
        cursor_before=transition.cursor_before,
        cursor_after=transition.cursor_after,
        cursor_change=transition.cursor_after - transition.cursor_before,
        bound={
            "value": transition.bound,
            "provenance": transition.bound_provenance,
            "daily_literal": DAILY_BOUND,
            "daily_rejected_derivation": DAILY_BOUND_REJECTED_DERIVATION,
        },
        instant_before=instant_before,
        instant_after=now,
        cursor_path=reward_cursor_path(intent.operation),
        state=after_resources,
        proof=proof,
        leaf_paths_changed=changed,
        schedules={
            "read": False,
            "daily": "DAILY_GOLD_REWARDS",
            "weekly": "MONDAY_BONUS_REWARDS",
            "reason": (
                "both have zero legacy readers and paying from either would "
                "diverge from an oracle that pays nothing"
            ),
        },
        addressability=_addressability(
            cursor_before, intent.operation, transition.bound
        ),
    )


def declared_operations() -> Tuple[str, ...]:
    """The closed operation set, so a test enumerates it rather than regexes it."""
    return OPERATIONS


def reward_cursor_path(operation: str) -> str:
    """The real storage path of ``operation``'s cursor.

    The request addresses ``/privateState`` - the container - because which key
    inside it is addressed is the *operation's* answer, not the request's.  This
    function reports the key the domain actually resolved.
    """
    return "/privateState/%s" % CURSOR_KEYS[operation]


#: The stored field names, mirrored from ``SaveRepository.REWARD_CURSOR_PATHS``
#: and pinned against it by ``tests/test_reward.py``.  Reported beside the
#: container path so a reader can see the two-step address rather than only the
#: end of it.
CURSOR_KEYS: Dict[str, str] = {"weekly": "weeklyRewardIndex", "daily": "bonusNextId"}


# --------------------------------------------------------------------------
# The derivation.  One place, and the inventory the suite pins.
# --------------------------------------------------------------------------


def _derive(cursor: int, operation: str, content: CommittedContent) -> RewardTransition:
    """Derive ``operation``'s successor from ``cursor``.  The whole derivation.

    Daily keeps the preserved literal's rule - add one, then wrap above the
    bound to the bound's floor.  Weekly keeps the preserved helper's rule - add
    one, then wrap modulo the bound.

    The two differ in where the wrap lands, and that difference is the legacy
    behaviour rather than a choice made here: the daily branch compares ``> 5``
    and assigns ``1``, while the weekly branch reduces modulo the length.  Both
    are transcribed because both are what the oracle does.
    """
    if operation == "daily":
        after = cursor + 1
        if after > DAILY_BOUND:
            after = 1
        bound = DAILY_BOUND
        provenance = "the preserved literal at command.py:451"
    else:
        bound = _weekly_bound(content)
        after = (cursor + 1) % bound
        provenance = "get_weekly_reward_length()'s own result"

    return RewardTransition(
        cursor_before=cursor,
        cursor_after=after,
        bound=bound,
        bound_provenance=provenance,
    )


def _addressable_positions(operation: str, bound: int) -> Tuple[int, ...]:
    """The cursor values ``operation``'s own arithmetic can address.

    Derived from the arithmetic rather than assumed, and the two arms disagree
    here in exactly the way they disagree about where the wrap lands:

    * daily
        the preserved branch compares ``> 5`` and assigns ``1``, so the
        positions it can *store* are ``1..5`` and it has no arithmetic that
        produces ``0``.  A stored ``0`` is therefore an off-ladder seed -- and
        the committed corpus carries exactly that, ``bonusNextId`` being ``0``
        in seven of its ten reward-bearing documents.
    * weekly
        the branch reduces **modulo**, so ``0`` is an ordinary position and the
        addressable set is ``0..bound-1``.

    This asymmetry is not normalised away: the corpus seed that is off-ladder
    for one arm is on-ladder for the other, and a suite that collapsed the two
    would report no gap for a document the daily arm cannot address.
    """
    if operation == "daily":
        return tuple(range(1, bound + 1))
    return tuple(range(bound))


def _addressability(cursor: int, operation: str, bound: int) -> Dict[str, Any]:
    """Report an off-ladder stored cursor, and derive **no** rule to resolve it.

    Task 1.4's third report.  The corpus records a cursor the daily bound cannot
    address, and the honest response is to say so beside the answer rather than
    clamp the stored value into range -- clamping would write a number the
    oracle never wrote and make the stored value disagree with the reported
    one.

    Every field here is a **report**.  ``clamped`` is hard ``0`` because the
    transaction clamps nothing, and the suite asserts it rather than trusting it.
    """
    addressable = _addressable_positions(operation, bound)
    gaps = [cursor] if cursor not in addressable else []
    return {
        "bound": bound,
        "addressable_positions": list(addressable),
        "unaddressable_cursors": gaps,
        "gap_reported": bool(gaps),
        "clamped": 0,
        "resolution": (
            "no rule was derived: the stored cursor is reported as it stands and "
            "is not clamped, because the preserved server had no bound to clamp "
            "it against and deriving one here would invent a rule the oracle "
            "does not have"
        ),
    }


def _weekly_bound(content: CommittedContent) -> int:
    """``get_weekly_reward_length``'s own result, derived the same way.

    The preserved helper (``get_game_config.py:195-204``) seeds ``length = 1``
    and then takes ``max`` over the entries whose ``value`` is a **list**.  That
    is the whole rule and it is transcribed rather than approximated, because
    both halves are load-bearing:

    * the floor means a schedule whose every ``value`` were scalar returns
      **1**, not ``0``;
    * the maximum is over **list-valued** entries, so it is the item count
      *inside* one rung, never the rung count.

    The two numbers differ for the committed schedule - the bound is **5** and
    the schedule's cardinality is **3** - which is exactly why the bound cannot
    be read as "how many rewards there are".
    """
    schedule = content.globals_object().get("MONDAY_BONUS_REWARDS")
    if not isinstance(schedule, list):
        raise ContentError("unreadable_content", "MONDAY_BONUS_REWARDS is not a list")

    length = 1
    for rung in schedule:
        if not isinstance(rung, dict):
            raise ContentError("unreadable_content", "a weekly rung is not an object")
        value = rung.get("value")
        if isinstance(value, list):
            length = max(length, len(value))
    return length


# --------------------------------------------------------------------------
# Proof instrumentation.
# --------------------------------------------------------------------------


def _cursor_now(document: Mapping[str, Any], operation: str) -> Any:
    """Read the cursor back out of a raw document for the proof's first half."""
    state = document.get("privateState")
    if not isinstance(state, dict):  # pragma: no cover - read above succeeded
        return None
    return state.get(CURSOR_KEYS[operation])


def _expected_leaf_paths(operation: str) -> Tuple[str, ...]:
    """The only two leaf paths a successful reward may change.

    Both are **paths**, not bare key names.  An earlier draft returned the bare
    stamp key here, so the set comparison was ``{...} <= {"/privateState/
    bonusNextId", "timestampLastBonus"}`` -- which no document satisfies, and
    which made the fourth proof half fail on *every* successful transaction
    rather than on the tampering it exists to catch.  A guard that fires on the
    success path measures nothing.
    """
    return ("/privateState/%s" % CURSOR_KEYS[operation],
            "/privateState/%s" % _stamp_key(operation))


def _stamp_key(operation: str) -> str:
    return "timeStampMondayBonus" if operation == "weekly" else "timestampLastBonus"


def _changed_leaf_paths(before: Any, after: Any, prefix: str = "") -> List[str]:
    """Every leaf path whose value differs between two documents.

    Copied in spirit from the other v1 domains; reimplemented here rather than
    imported so this module's derivation stays the only thing it owns and the
    suite can pin its whole inventory.
    """
    changed: List[str] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            changed.extend(
                _changed_leaf_paths(
                    before.get(key), after.get(key), "%s/%s" % (prefix, key)
                )
            )
    elif before != after:
        changed.append(prefix)
    return changed


# --------------------------------------------------------------------------
# Refusal plumbing.
# --------------------------------------------------------------------------


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=detail)


def _repository_refusal(error: RepositoryError, intent: Intent) -> Refusal:
    return Refusal(
        code=RefusalCode(error.code),
        message=str(error),
        detail={
            "player_id": intent.player_id,
            "operation": intent.operation,
            "repository_code": error.code,
        },
    )


__all__ = [
    "ACTION",
    "DAILY_BOUND",
    "DAILY_BOUND_REJECTED_DERIVATION",
    "GRANT_CHANNEL_REFUSALS",
    "OPERATIONS",
    "PostConditionViolation",
    "PRESERVED_REWARD_BEHAVIOUR",
    "RewardTransition",
    "advance_reward",
    "declared_operations",
    "reward_cursor_path",
]
