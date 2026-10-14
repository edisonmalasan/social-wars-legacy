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
:class:`Success`, a :class:`CollectionSuccess`, a :class:`MagicSuccess`, a
:class:`CombatSuccess`, a :class:`RewardSuccess`, or a
:class:`~server_v1_refusals.Refusal`.  There is no other arm, and there is no
``None`` — a domain function that has decided nothing has a bug, and the type
says so.  **The third and later arms are further successes, not refusal
variants**: a collection *grant* is a genuinely different transaction from a
collection *payout*, and the difference is a shape difference (no row, no rung,
a prize in storage and a price in cash) rather than a value difference, so it
earns its own frozen model with its own required derivation; and a magic
*counter transition* is a third shape again — no row, no rung, no elapsed time,
**no price and no deltas at all** — so it earns a third.

**The reward arm (M13 line 5) is a counter transition with the counter replaced
by a cursor, and it is a distinct shape for a reason the other four do not
have: it is the only one that writes a value it did not pay for.**  Every other
success either moves a client-free derivation into a stored row, grants a
committed prize, or advances a bounded counter.  A reward success advances a
cursor **and grants nothing**, so a reader who saw only "the cursor moved" would
conclude the player was paid.  :class:`RewardSuccess` therefore carries the
no-payout claim as a **field** (:attr:`RewardSuccess.derived_payout`,
:attr:`RewardSuccess.paid`) and proves it by comparing the **whole** stored
resource set, rather than leaving it to the prose above.

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


#: The preserved branch's recorded behaviour, quoted in the response so a client
#: can see the divergence rather than infer it.  **Data, not a second
#: derivation**, and the same reasoning as :data:`PRESERVED_MAGIC_BEHAVIOUR`:
#: nothing in v1 reproduces a legacy combat value, because there is no committed
#: value that names one.
#:
#: **Declared here, not in :mod:`server_v1_combat`,** for the reason
#: :data:`PRESERVED_MAGIC_BEHAVIOUR` gives: the dependency runs the other way.
PRESERVED_COMBAT_BEHAVIOUR: Dict[str, str] = {
    "destruction": (
        "command.py:868 computes lost = max(0, unit[2] - unit[3]) from two numbers "
        "the CLIENT sends, and command.py:872 destroys that many rows through "
        "map_lose_item, so the count is client-dictated in full; the committed "
        "source labels the two numbers only 'A' and 'B'"
    ),
    "ledger": (
        "engine.py:223 pushes each destroyed row onto privateState['deadHeroes'] "
        "through push_dead_unit, which requires the row's team to be exactly 1 "
        "(engine.py:151) and the item's committed resurrectable to be greater than "
        "zero (engine.py:159-162); v1 reports both gates and credits nothing"
    ),
    "absent_value": (
        "command.py:866 and :874 dereference attacker_units and victim without a "
        "None check, so an omitted shape raises, the batch is discarded before the "
        "save is written (command.py:30,32), and the response is an HTTP 500; this "
        "is established by execution on fixture steps 2 and 4, not reasoned"
    ),
    "reached": (
        "map_lose_item has exactly two call sites -- command.py:796 (end_quest) and "
        "command.py:872 (end_attack) -- so two branches reach one helper; "
        "godot-unit-behaviors counted push_dead_unit's callers and map_lose_item "
        "separately and called it three doors, and that archived line is not edited"
    ),
}


class CombatSuccess(BaseModel):
    """A combat resolution that resolved an identity and destroyed nothing.

    **The first v1 success that writes nothing at all**, and therefore the one
    whose post-execution proof is the strongest instrument in this repository:
    the *entire* persisted document, every key, is byte-identical after the
    request -- not the addressed subtree, not the seven stored resources, and not
    the dead-hero ledger alone.

    That is what makes this model separate from the other three rather than a
    fourth instance of one of them:

    * it carries **no derivation**, because this surface has none to carry -- the
      preserved branch's only quantity is a subtraction of two client numbers,
      and no committed column names an outcome;
    * it carries the **refused** client figure beside the code that refused it,
      so a client can see what it sent and why it was not applied, without v1
      ever having computed a count from it;
    * it carries both committed gates **reported**, with
      :attr:`gates_enforced` fixed at ``False`` -- the gates are facts about what
      the preserved server *would* have done, and the transaction has nothing to
      gate because it destroys nothing;
    * it carries the proof as **ordered named checks**
      (:attr:`proof`), so a reader can see which half is a specification check
      and which half is the falsifiable one, rather than being told in prose.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    #: The committed unit identity the request named, verified against the
    #: committed unit table before anything else happened.
    unit_id: int
    #: The instant the transaction reported (Unix seconds).  The preserved branch
    #: records no instant for this action, so nothing in the store holds it.
    instant: int
    #: Every stored resource, read **back** from the store after the
    #: (non-)write, so a caller cannot report a success without having read what
    #: it reports.
    state: Dict[str, int] = Field(min_length=1)
    #: The committed row facts, verbatim and never compared.
    committed: Dict[str, Any]
    #: Both recorded gates, each reported with its own presence flag so an
    #: absent committed value is never reported as a zero.
    gates: Dict[str, Any]
    #: The two helpers' asymmetry, stated rather than reconciled.
    team_asymmetry: Dict[str, Any]
    #: What the request tried to destroy and why it was not applied.  Carries
    #: the refused figure **verbatim** -- never a count v1 derived from it.
    destruction: Dict[str, Any]
    #: The post-execution proof: ordered ``(check, held)`` pairs.  An empty
    #: tuple would be a success reporting no proof at all, which is not a state
    #: this model is allowed to be constructed into.
    proof: Tuple[Tuple[str, bool], ...] = Field(min_length=1)
    #: Every leaf path that differed between the pre-request and post-request
    #: documents.  Empty on every success this surface can produce, and reported
    #: rather than asserted, so a destruction would name *which* leaves moved.
    leaf_paths_changed: Tuple[str, ...]
    #: Whether the whole persisted document was byte-identical across the
    #: transaction.  The falsifiable half of the proof.
    document_unchanged: bool
    #: Whether either reported gate was enforced as a precondition.  A constant
    #: ``False``, declared so a reader does not have to infer it from the
    #: absence of a refusal.
    gates_enforced: bool = False

    def payload(self) -> Dict[str, Any]:
        """The transport body for this success (envelope added by the route).

        Reports the committed facts and the **refused** figure, and carries no
        ``derived_deltas`` key at all rather than an empty one -- exactly as the
        magic slice does, because a destruction of nothing is the claim this
        slice exists to make and an empty mapping invites a reader to treat it
        as a formatting accident.
        """
        return {
            "result": "success",
            "action": self.action,
            "instant": self.instant,
            "combat": {
                "unit_id": self.unit_id,
                "identity_field": "unit_id",
                "identity_resolved_against": "the committed items rows with type u",
            },
            "committed": dict(self.committed),
            "gates": dict(self.gates),
            "gates_enforced": self.gates_enforced,
            "team_asymmetry": dict(self.team_asymmetry),
            "destruction": dict(self.destruction),
            "rows_destroyed": 0,
            "resources_after": dict(self.state),
            "stored_resources_compared": sorted(self.state),
            "proof": [list(entry) for entry in self.proof],
            "leaf_paths_changed": list(self.leaf_paths_changed),
            "document_unchanged": self.document_unchanged,
            "derived_damage": None,
            "derived_destruction_count": None,
            "damage_derived": False,
            "derivation_performed": None,
            "ledger_credited": False,
            "ledger_covered_by": (
                "the whole-document comparison, not a subset read: the dead-hero "
                "ledger is one key among every key compared"
            ),
            "preserved_branch_behaviour": PRESERVED_COMBAT_BEHAVIOUR,
        }


__all__ = [
    "PRESERVED_COMBAT_BEHAVIOUR",
    "PRESERVED_MAGIC_BEHAVIOUR",
    "PRESERVED_REWARD_BEHAVIOUR",
    "SUCCESS_HTTP_STATUS",
    "CollectionSuccess",
    "CombatSuccess",
    "MagicSuccess",
    "Outcome",
    "RewardSuccess",
    "Success",
]


#: What the two preserved reward branches actually do, reported beside every
#: reward success so a client can see the gap between the oracle and this line
#: without reading either.
#:
#: **Every entry is a recorded fact, and none is a v1 behaviour.**  This is the
#: same discipline :data:`PRESERVED_COMBAT_BEHAVIOUR` records, and it matters
#: more here: the reward branches *sound* like payouts -- one is called
#: ``win_daily_bonus`` and the committed table is called ``DAILY_GOLD_REWARDS`` --
#: so a reader who saw only "the daily cursor advanced" would have every reason
#: to think gold changed hands.
PRESERVED_REWARD_BEHAVIOUR: Dict[str, str] = {
    "weekly_branch": (
        "weekly_reward (command.py:345-363): the new cursor is "
        "(stored + 1) % get_weekly_reward_length(), so the arithmetic is the "
        "server's while its input is the client's"
    ),
    "weekly_client_input": (
        "the preserved branch reads the next cursor from the request, so a "
        "client could move the weekly cursor anywhere the modulus allowed"
    ),
    "weekly_stamped_instant": (
        "timeStampMondayBonus is written by the branch and read by nothing: "
        "no legacy module consumes it, so no eligibility rule exists to "
        "reproduce"
    ),
    "daily_branch": (
        "win_daily_bonus (command.py:444-463): next_id = args[1] + 1 and "
        "if next_id > 5: next_id = 1, so an oversized client-sent value wraps "
        "a recorded 4 back to 1"
    ),
    "daily_backwards_move": (
        "that wrap moves the recorded cursor BACKWARDS, 4 -> 1, and this line "
        "records it as a divergence rather than reproducing it, because "
        "reproducing a client-directed cursor regression would defeat the "
        "purpose of making the cursor authoritative"
    ),
    "daily_grant": (
        "the daily arm's grant is a client-sent item id written into storage "
        "and a deduplicating unit list, which is exactly why v1 refuses a "
        "client-sent item by name and pays nothing"
    ),
    "daily_bound_literal": (
        "the daily bound 5 is the literal in the preserved source "
        "(command.py:451, the `if next_id > 5` test), not a length; it "
        "coincides with len(DAILY_GOLD_REWARDS) == 5 and the agreement is a "
        "coincidence. command.py:446 is the OTHER line -- `next_id = args[1] + "
        "1` -- which is the client input this line replaces, so citing it as the "
        "bound's provenance would point a reader at the very thing the "
        "derivation refuses. The table said :446 and was corrected here; "
        "test_reward.py asserts the corrected figure so it cannot regress"
    ),
    "paid": (
        "neither branch credits a stored resource: the daily arm writes an "
        "item into storage and the non-granting arm only prints"
    ),
    "schedules": (
        "DAILY_GOLD_REWARDS and MONDAY_BONUS_REWARDS are reported and left "
        "unread; applying either would diverge from an oracle that pays "
        "nothing"
    ),
}


class RewardSuccess(BaseModel):
    """A reward cursor that advanced, with the no-payout claim as a field.

    **The only success in this module that proves its own emptiness**, and the
    reason is structural rather than stylistic.  The other four either carry a
    :class:`~server_v1_economy.ResourceDerivation` or carry none because there
    is nothing to derive; this one carries a *movement* -- the cursor really did
    change in the stored document -- beside the absence of every consequence a
    movement of that name would normally imply.  A reader can therefore not
    infer "paid" from "advanced", which is the inference this line exists to
    prevent.

    Three fields make that claim falsifiable rather than asserted:

    * :attr:`derived_payout` is ``None`` and :attr:`paid` is ``False``, declared
      so a reader is not left to infer them from a missing key;
    * :attr:`state` is the **complete** stored resource set read back after the
      transaction, and the post-execution proof compares every one of its
      members against the pre-request value, so a grant of any size at any
      resource fails;
    * :attr:`leaf_paths_changed` reports **every** leaf that moved in the whole
      document, so the two the cursor and its stamped instant are expected to
      be is a checkable set rather than a promise.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    #: Which cursor was advanced: ``weekly`` or ``daily``, verbatim from the
    #: intent's closed operation set.  Never a third value.
    operation: str
    #: The cursor read **from the recorded document** before the transaction.
    #: Reported so a client can see that the successor came from here and not
    #: from itself.
    cursor_before: int
    #: The derived successor: ``stored + 1``, then the bound's own rule.
    cursor_after: int
    #: ``cursor_after - cursor_before``, signed.  Reported as its own field so a
    #: backwards move would be visible as a negative rather than hidden inside
    #: two unsigned values a reader must subtract by hand.
    cursor_change: int
    #: The bound applied, and **where it came from** -- the preserved literal
    #: for daily, the accessor's own count for weekly.  Both spellings, because
    #: the whole point of this line's bound split is that the two are not the
    #: same kind of number.
    bound: Dict[str, Any]
    #: The stamped instant before and after.  Written and reported; never read
    #: to decide anything, because no legacy module reads it.
    instant_before: int
    instant_after: int
    #: The cursor's real storage path beside the request's container address,
    #: because the request addresses no key and the domain resolves one.
    cursor_path: str
    #: Every stored resource, read back after the transaction.
    state: Dict[str, int] = Field(min_length=1)
    #: Ordered ``(check, held)`` pairs.  A reward success reporting no proof at
    #: all is not a state this model can be constructed into.
    proof: Tuple[Tuple[str, bool], ...] = Field(min_length=1)
    #: Every leaf path that differed between the pre-request and post-request
    #: documents.  Expected to be exactly the cursor and the stamped instant;
    #: reported rather than asserted, so a third movement would name itself.
    leaf_paths_changed: Tuple[str, ...]
    #: The post-execution no-payout facts, as fields rather than as prose.
    derived_payout: None = None
    paid: bool = False
    #: The committed schedules, **reported and unread**.  Each entry carries its
    #: own count so a reader can see that the schedule exists and that nothing
    #: was read from it.
    schedules: Dict[str, Any]
    #: Whether an eligibility, cooldown, daily-window, weekly-period, or
    #: already-claimed rule was consulted.  A constant ``False``: the stamped
    #: instant has no reader in the preserved server, so there is no rule to
    #: apply and deriving one would be an invention.
    eligibility_derived: bool = False
    #: Where the stored cursor sat relative to the bound's own addressable
    #: positions, reported rather than enforced (task 1.4's third report).
    #:
    #: The committed corpus carries ``bonusNextId`` as ``0`` in seven of its ten
    #: reward-bearing documents, and the daily branch's arithmetic can only
    #: produce ``1..5`` -- so a real corpus document sits off that arm's ladder.
    #: Clamping it into range would write a number the oracle never wrote and
    #: make the stored value disagree with the reported one, so the gap is
    #: reported and nothing is derived to close it.
    #:
    #: **Shape is closed and asserted by** ``tests/test_reward.py``: ``bound``,
    #: ``addressable_positions``, ``unaddressable_cursors``, ``gap_reported``,
    #: ``clamped``, and ``resolution``.  ``clamped`` is hard ``0`` and the suite
    #: asserts it rather than trusting it, because a field named for a thing the
    #: line refuses to do is worth nothing unless something checks it.
    addressability: Dict[str, Any] = Field(default_factory=dict)

    def payload(self) -> Dict[str, Any]:
        """The transport body for this success (envelope added by the route).

        Carries **no** ``derived_deltas`` key and **no** ``grant`` key, rather
        than empty ones.  Both would invite a reader to treat the absence as a
        formatting accident instead of the claim it is, and ``derived_deltas``
        is in fact the key every one of the other three successes uses for a
        real, server-derived figure.
        """
        return {
            "result": "success",
            "action": self.action,
            "instant": self.instant_after,
            "reward": {
                "operation": self.operation,
                "cursor_before": self.cursor_before,
                "cursor_after": self.cursor_after,
                "cursor_change": self.cursor_change,
                "cursor_path": self.cursor_path,
                "cursor_derived_from": "the recorded cursor, never the request",
                "bound": dict(self.bound),
                "instant_before": self.instant_before,
                "instant_after": self.instant_after,
                "instant_gating": False,
                # Task 1.4's third report, emitted beside the bound it is
                # relative to.  **Absent when there is no gap would be wrong**
                # -- the whole claim is that the transaction always says where
                # the stored cursor sat -- so it is emitted unconditionally,
                # with ``gap_reported: false`` when there is nothing to report.
                "addressability": dict(self.addressability),
            },
            "resources_after": dict(self.state),
            "stored_resources_compared": sorted(self.state),
            "proof": [list(entry) for entry in self.proof],
            "leaf_paths_changed": list(self.leaf_paths_changed),
            "derived_payout": None,
            "paid": False,
            "eligibility_derived": False,
            "schedules": dict(self.schedules),
            "preserved_branch_behaviour": PRESERVED_REWARD_BEHAVIOUR,
        }


#: What a domain service returns.  Six arms, no ``None``.
#:
#: The five successes are separate frozen models rather than one model with
#: optional halves, and :class:`CollectionSuccess`'s own docstring says why;
#: :class:`MagicSuccess` carries the same argument with nothing left to remove,
#: :class:`CombatSuccess` the same argument once more, now with no derivation at
#: all and a whole-document proof in place of a transition, and
#: :class:`RewardSuccess` it once more for a different reason -- it moves a
#: stored value while paying nothing.  Declared last, after every class it
#: names, because ``Union`` resolves its arguments when it is evaluated: the
#: first version of this module put the union above ``CollectionSuccess`` and the
#: service failed to import at all.
Outcome = Union[
    Success,
    CollectionSuccess,
    MagicSuccess,
    CombatSuccess,
    RewardSuccess,
    Refusal,
]
