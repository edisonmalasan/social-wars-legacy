#!/usr/bin/env python3
"""The ``collect`` vertical slice: decide, derive, prove, then write.

**Tasks 4.1–4.4.**  This is the first action on the v1 boundary, and it exists
to demonstrate all three boundary properties on one transaction:

* a **derived** payout (task 4.1) — the server computes the amount from
  committed content and a recorded instant; the client sent a row address and
  nothing else;
* **named refusals** through the typed channel with the store byte-identical
  (task 4.2);
* a **two-part post-execution proof** (task 4.3) that the recorded instant
  moved forward *and* every stored resource changed by exactly the derived
  delta, checked by reading the store back after the write.

**Decide before mutate** (spec: "A refused action moves nothing").  The order
in :func:`collect` is not incidental:

1. read the document;
2. decide, in a fixed order, producing a :class:`Refusal` **or** a
   :class:`~server_v1_economy.ResourceDerivation` — nothing here writes;
3. only if step 2 produced a derivation, apply the deltas and the new instant to
   the in-memory document, having first taken a whole-document snapshot;
4. write the document once;
5. read the document back and run the two-part proof;
6. return a :class:`~server_v1_outcomes.Success` carrying the verified state.

A refusal at any point in step 2 returns before step 3, so no write is issued
at all and the file on disk keeps its exact pre-request bytes — which is what
task 4.2 asks the tests to assert.  This is the inversion the spec asks for: the
preserved server applies the client's resource vector at ``command.py:40`` and
only then opens the ``if cmd ==`` chain at ``:42``, so a command that is
subsequently declined has already had the vector applied.

The refusals, each with its reason and where the decision is made:

============================ ================================= ============
code                         decided in                               meaning
============================ ================================= ============
``unaddressable_row``        here, against the store                  no row
``construction_in_progress`` here, against the store                  the row carries construction state
``unknown_player``           the repository                           no save
``unreadable_state``         the repository / this slice              state it cannot read
``no_committed_income``      the economy authority                    no usable income fields
``capped_collection``        the economy authority                    a non-zero cap
``below_first_rung``         the economy authority                    no rung reached
``unreadable_content``       the economy authority / content          content it cannot read
``post_condition_violation`` here, after the write                    the store is not what the derivation required
============================ ================================= ============

The two row-level checks live here rather than in the economy because they are
questions about **stored state**, and the economy authority is only about
committed content plus one recorded instant.  Keeping them here is also what
makes ``item[3]``'s dual meaning (established: written by both ``activate`` and
``collect``) visible in exactly one place.

**The two-part proof** is :func:`_prove`, and it is written so that *neither*
half can pass while the other is violated.  ``tests/test_collect.py`` injects
each half's violation in turn — an instant that does not move forward, and a
resource that moves by something other than the derived delta — and both are
observed to fail with :class:`PostConditionViolation`, which the slice converts
into a ``post_condition_violation`` refusal **after writing the pre-request
snapshot back**.  Restoring rather than leaving a half-written store is the
honest response: a proof that failed has not established what the store now
holds, so v1 does not claim it, and it puts back the bytes it found.  That
restore is a second write, so a post-condition refusal is *not* byte-identical
in the way a decision-time refusal is — it is byte-identical by having been
rolled back rather than by having never written.  The two cases are reported
separately in ``post_condition_violation``'s ``detail`` so a reader can tell
them apart, and both are covered by tests.
"""

from __future__ import annotations

from typing import Any, Dict

from server_v1_content import CommittedContent, ContentError
from server_v1_economy import EconomyError, ResourceDerivation, derive_collection_payout
from server_v1_intent import Intent
from server_v1_outcomes import Outcome, Success
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES, RepositoryError, SaveRepository

ACTION = "collect"


class PostConditionViolation(Exception):
    """The executed transaction did not produce the state its derivation required.

    Never a client-visible gameplay answer: the slice converts it into a
    ``post_condition_violation`` refusal and rolls the store back.
    """


def collect(
    intent: Intent,
    content: CommittedContent,
    repository: SaveRepository,
    now: int,
) -> Outcome:
    """Execute one collection intent, or refuse it by name.

    ``now`` is the service's own clock, passed in rather than read here, so a
    test can pin it to the executed-legacy fixture's capture instant and make
    the task 4.4 comparison deterministic.  It is never a request value: the
    intent has no field it could arrive in.
    """
    # ---- 1. read ----------------------------------------------------------
    try:
        document = repository.read(intent.player_id)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 2. decide, writing nothing --------------------------------------
    try:
        # A balance this service cannot read is a refusal, reported before any
        # row question, because a derivation against an unread balance would be
        # a derivation against a guess.
        document.resources()
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    if document.row(intent.row) is None:
        return _refuse(
            RefusalCode.UNADDRESSABLE_ROW,
            "save %r has no placement at row %d" % (intent.player_id, intent.row),
            {"player_id": intent.player_id, "row": intent.row},
        )

    try:
        under_construction = document.row_is_under_construction(intent.row)
    except RepositoryError as error:
        return _repository_refusal(error, intent)
    if under_construction:
        # ESTABLISHED that item[3] serves both roles; DERIVED that v1 refuses
        # rather than collecting over a build (the executed probe recorded in
        # docs/legacy-collect-income.md left the countdown running and legacy
        # answered success).  Rejected alternative: collecting anyway, which
        # would overwrite a build's start instant with a collection instant.
        return _refuse(
            RefusalCode.CONSTRUCTION_IN_PROGRESS,
            "row %d carries construction state, so its recorded instant is a "
            "build start rather than a last-collection instant" % intent.row,
            {"player_id": intent.player_id, "row": intent.row},
        )

    try:
        item_id = document.row_item_id(intent.row)
        last_collected_at = document.row_instant(intent.row)
        before_resources = document.resources()
        before_instant = document.row_instant(intent.row)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    try:
        derivation = derive_collection_payout(
            content,
            item_id=item_id,
            last_collected_at=last_collected_at,
            now=now,
        )
    except EconomyError as error:
        return _refuse(error.code, str(error), error.detail)
    except ContentError as error:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            "committed content is unusable: %s" % error,
            {"content_code": error.code},
        )

    # ---- 3. apply, in memory only ----------------------------------------
    # The snapshot is taken *after* the decision and *before* the first
    # mutation, so a rollback restores the exact bytes the request found.
    snapshot = document.snapshot()
    try:
        for name in STORED_RESOURCE_NAMES:
            delta = derivation.delta_for(name)
            if delta:
                document.set_resource(name, before_resources[name] + delta)
        document.set_row_instant(intent.row, now)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 4. write once ----------------------------------------------------
    try:
        repository.write(document)
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 5. read back and prove -------------------------------------------
    try:
        after = repository.read(intent.player_id)
        after_resources = after.resources()
        after_instant = after.row_instant(intent.row)
    except RepositoryError as error:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the store could not be read back after the write: %s" % error,
            {"half": "read_back", "cause": error.code, "rolled_back": restored},
        )

    try:
        _prove(
            before_instant=before_instant,
            after_instant=after_instant,
            before_resources=before_resources,
            after_resources=after_resources,
            derivation=derivation,
        )
    except PostConditionViolation as violation:
        restored = _rollback(repository, intent, snapshot)
        return _refuse(
            RefusalCode.POST_CONDITION_VIOLATION,
            "the executed collection did not produce its derived post-state: %s"
            % violation,
            {
                "half": _violated_half(
                    before_instant, after_instant, before_resources, after_resources, derivation
                ),
                "addressed_path": intent.addressed_path(),
                "rolled_back": restored,
            },
        )

    # ---- 6. report --------------------------------------------------------
    return Success(
        action=ACTION,
        derivation=derivation,
        instant=after_instant,
        state=after_resources,
        row_instant=after_instant,
    )


def _prove(
    *,
    before_instant: int,
    after_instant: int,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    derivation: ResourceDerivation,
) -> None:
    """The two-part post-execution proof (task 4.3).

    Half one: **the collection instant moved forward** — strictly forward.  A
    proof that only checked "changed" would pass on an instant that moved
    backwards, and on the ``now < last_collected_at`` state the economy already
    refuses separately.

    Half two: **every stored resource changed by exactly the derived delta.**
    Checked over the *complete* stored set, not only over the resources the
    derivation names: a resource absent from the derivation must be
    **unchanged**, so a store that quietly altered gold as well fails rather
    than passes.  This is what makes the proof non-tautological — a derivation
    that moved nothing cannot satisfy half one, and a derivation that moved the
    wrong amount cannot satisfy half two.

    Both halves raise :class:`PostConditionViolation` naming the specific
    mismatch, so a failure says which rule broke rather than only that one did.
    """
    if after_instant <= before_instant:
        raise PostConditionViolation(
            "the collection instant did not move forward: %d -> %d"
            % (before_instant, after_instant)
        )
    for name in STORED_RESOURCE_NAMES:
        expected = before_resources[name] + derivation.delta_for(name)
        if after_resources.get(name) != expected:
            raise PostConditionViolation(
                "stored resource %r moved by %r, not by the derived %r "
                "(before %r, expected %r, after %r)"
                % (
                    name,
                    after_resources.get(name, 0) - before_resources[name],
                    derivation.delta_for(name),
                    before_resources[name],
                    expected,
                    after_resources.get(name),
                )
            )


def _violated_half(
    before_instant: int,
    after_instant: int,
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    derivation: ResourceDerivation,
) -> str:
    """Which half of the proof failed, for the refusal's ``detail``.

    Computed rather than assumed: the same string is asserted by the injection
    tests, so a half that fails for a different reason than the one reported
    would be caught.
    """
    if after_instant <= before_instant:
        return "instant_moved_forward"
    return "resources_matched_derivation"


def _rollback(
    repository: SaveRepository, intent: Intent, snapshot: Dict[str, Any]
) -> bool:
    """Write the pre-request snapshot back; report whether it succeeded.

    Best effort, and it **says** whether it worked rather than pretending.  A
    rollback that fails is a store whose contents v1 does not know, which is a
    worse state than the failed proof, so it is reported in the refusal's
    ``rolled_back`` detail instead of being swallowed.
    """
    try:
        current = repository.read(intent.player_id)
        current.raw.clear()
        current.raw.update(snapshot)
        repository.write(current)
    except RepositoryError:
        return False
    return True


def _repository_refusal(error: RepositoryError, intent: Intent) -> Refusal:
    """Map a repository failure onto a refusal code.

    The repository names two kinds of failure — "no such save" and "state I
    cannot read" — and the domain distinguishes them, because they mean
    different things to a client: 404 for an address that does not exist, 500
    for a store this service cannot reason about.  Deliberately not disguised
    as a gameplay answer.
    """
    if error.code == "unknown_player":
        return _refuse(
            RefusalCode.UNKNOWN_PLAYER, str(error), {"player_id": intent.player_id}
        )
    return _refuse(
        RefusalCode.UNREADABLE_STATE,
        str(error),
        {"player_id": intent.player_id, "cause": error.code},
    )


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=dict(detail))


__all__ = ["ACTION", "PostConditionViolation", "collect"]
