#!/usr/bin/env python3
"""Capture the executed-legacy reward-cursor fixture: ``weekly_reward`` and ``win_daily_bonus``.

Contract: ``docs/legacy-m10-rewards.md`` (OpenSpec change ``2026-10-05-rewards``,
task group 1).  Read that record for the measurements; this module executes them
and refuses to publish unless every one reproduces.

Seven transactions against **one** committed village document --
``villages/Neutral.json``, recorded at ``weeklyRewardIndex`` **3** and
``bonusNextId`` **2** -- driven as **one interleaved sequence** against **one**
disposable legacy server.

**One sequence, and the linkage is load-bearing.**  The recorded cursors are
the point of the fixture: ``weeklyRewardIndex`` 3 advances to **4**, a position
the three-entry weekly schedule **cannot answer**, and ``bonusNextId`` 2 advances
to 3.  Those numbers only mean anything if each transaction really ran against
its predecessor's recorded state, so the capture asserts that linkage over the
**whole** document at every link rather than comparing one cursor.  The oversized
next-id probe is the link that would break first: it is the only step whose
oracle result is *not* the recorded value advanced by one, so if the sequence
were not linked the probe's "before" would not be the successor the previous step
left behind.

One server is also **required** rather than one per transaction:
``sessions.load_saves()`` caches the corpus in a module global at import time, so
a running server never re-reads the save file from disk.  Restoring the seed
between steps on one server would leave the *in memory* corpus already mutated and
silently produce a different result.

What this fixture establishes, and what it deliberately does not:

* **ESTABLISHED** -- that ``weekly_reward`` has **two arms chosen by the client's
  argument count**, and that **both** arms stamp and advance the cursor whether or
  not anything was granted: four or fewer arguments prints *"Won resources"*,
  moves ``weeklyRewardIndex``, and leaves the rest of the document byte-identical,
  while five or more place a row and record the item through a **deduplicating**
  unit-list helper.
* **ESTABLISHED** -- that the **short** arm's whole-document leaf diff is
  **exactly two paths**, the cursor and the stamp.  That is the clean
  demonstration the contract asks for: a reward was "won", the cursor advanced,
  and nothing anywhere else in the document moved.
* **ESTABLISHED** -- **both halves of both grant helpers, by execution.**  Three
  transactions each move one of the three places a grant could land, and one
  moves the placed rows while the unit list stands still.  This is not
  completeness for its own sake: the delivered route's four-part grant proof is
  three *"unchanged"* assertions and one *"cursor moved"* assertion, and an
  unchanged-assertion over a field that cannot change proves nothing.  A fixture
  that only ever exercised the non-granting arms would leave all three halves of
  the proof vacuous.
* **ESTABLISHED** -- the divergence that is **observable in the source and not
  only in an executed record**: ``win_daily_bonus`` advances a **client-supplied**
  cursor and then, if the result exceeds the literal ``5``, **overwrites it with
  the first position**.  A deliberately oversized client next id therefore moves
  the recorded cursor **backwards**, and this fixture executes that rather than
  arguing it.
* **ESTABLISHED** -- that **no stored resource moves** in any of the seven
  transactions: all **eight** slots are byte-identical across every step, so
  neither branch charges or credits anything.
* **RECORDED AS DIVERGENCES, NEVER AS PARITY** -- the client-sent item in both
  branches, the client-sent next id, and the arity-selected third divergence.
  The capture asserts the differences rather than asserting parity.
* **NOT ESTABLISHED, AND NOT CLAIMED** -- anything about what was granted *by the
  game*.  The grant is **client-sent** in both branches: the non-granting arms
  grant nothing at all, and the granting arms place or store whatever integer the
  client sent, with no content lookup, no bound, and no eligibility test.  The
  captured ids happen to be ones the weekly schedule names, which is what makes
  the append observable -- it is **not** evidence that the schedule selects them.

No Flash, Ruffle, ActionScript, or browser executes.  Every network call is
loopback to ``127.0.0.1:5055``.
"""

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.version_info[:2] != (3, 9):
    sys.stderr.write(
        "capture: pinned interpreter is CPython 3.9, this is %d.%d\n"
        % sys.version_info[:2]
    )
    raise SystemExit(2)

from capture_legacy_fixtures import (  # noqa: E402
    CaptureError,
    DYNAMIC_ROOT,
    EXIT_CONTAINMENT,
    EXIT_ENVIRONMENT,
    EXIT_OK,
    EXIT_PORT_BUSY,
    EXIT_REQUEST,
    EXIT_SERVER,
    GAME_VERSION,
    LANGUAGE,
    LEGACY_HOST,
    LEGACY_PORT,
    REPO_ROOT,
    USER_KEY,
    build_disposable,
    canonical_digest,
    containment_snapshot,
    extract_session_cookie,
    http_request,
    iso_now,
    port_is_free,
    read_tail,
    save_group_record,
    sha256_bytes,
    sha256_file,
    snapshot_combined,
    start_server,
    stop_server,
    wait_ready,
    write_bytes,
    write_json,
)

from placement_envelope import (  # noqa: E402
    ENVELOPE_KEYS,
    data_field,
    parse_data_field,
    payload_json,
)

import rewards_envelope  # noqa: E402

# --- This line's own constants ---------------------------------------------

SCHEMA = "rewards-cursor-fixture-v1"

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "godot-rewards"

SEED = REPO_ROOT / "villages" / "Neutral.json"

SEED_PID = "Neutral"

# The committed cursors, verbatim from villages/Neutral.json.  Recorded as
# constants so a rerun fails loudly if the seed ever changes, rather than
# silently producing a different fixture.
SEED_WEEKLY_CURSOR = 3
SEED_DAILY_CURSOR = 2
SEED_WEEKLY_STAMP = 1686569823
SEED_DAILY_STAMP = 1688653422
SEED_PLACED_ROWS = 549
SEED_UNIT_LIST_LENGTH = 135
# The seed's storage, recorded because it is EMPTY and that is load-bearing: an
# empty storage is what lets one transaction move it from {} to exactly one entry,
# which is the only way this capture shows the storage clause of the delivered
# route's four-part grant proof capable of failing at all.
SEED_STORAGE: Dict[str, int] = {}

FIXTURE_TS = 1700000000

WEEKLY_COMMAND = "weekly_reward"
DAILY_COMMAND = "win_daily_bonus"
COMMANDS = (WEEKLY_COMMAND, DAILY_COMMAND)

# The two bounds, each from its own kind of source.  The weekly one is DERIVED
# by rewards_envelope from the committed schedule; the daily one is a hardcoded
# literal transcribed from the preserved branch.  Neither is typed here as a
# bound: the capture recomputes both and asserts they agree, so a change in
# either source fails the capture rather than being silently baked in.
WEEKLY_ARITY_THRESHOLD = 4
WEEKLY_SHORT_ARGS: List[Any] = []

# The long arm's five client-sent values, in the branch's own read order
# (``command.py:347-351``).  Two variants are captured, differing ONLY in the
# client-sent item id, and the difference is the whole point:
#
# * ``WEEKLY_LONG_ABSENT_ITEM`` is one of the five unit ids the weekly schedule's
#   single list-valued rung names, and the seed's unit list does **not** carry it,
#   so ``bought_unit_add`` (``engine.py:86-89``) **appends** and the list grows.
# * ``WEEKLY_LONG_PRESENT_ITEM`` is one of the same five and the seed's list
#   **does** carry it, so the very same helper **deduplicates** and the list
#   stands still.
#
# Both facts are read from the preserved source; capturing both turns them into
# executed ones, and -- the reason this costs a second transaction -- it makes
# the delivered route's "the unit list is byte-identical" clause non-vacuous.  A
# clause that only ever sees a list which cannot move proves nothing.  The same
# argument applies to storage, which is why the daily granting arm is captured
# too: all THREE "unchanged" halves of the four-part grant proof are shown to be
# capable of failing.
WEEKLY_LONG_ABSENT_ITEM = 1198
WEEKLY_LONG_PRESENT_ITEM = 1055
WEEKLY_LONG_ABSENT_ARGS: List[Any] = [600, WEEKLY_LONG_ABSENT_ITEM, 58, 47, 1]
WEEKLY_LONG_PRESENT_ARGS: List[Any] = [601, WEEKLY_LONG_PRESENT_ITEM, 58, 47, 1]

# The daily branch's two client-sent values (``command.py:445-446``).  ``item = 0``
# takes the ``else`` arm, which is what makes the cursor move observable on its
# own; a positive item takes the granting arm and writes the storage; the
# oversized next id is the probe that moves the cursor BACKWARDS.
#
# ``args[1]`` is the cursor the step runs AGAINST, so it is a different number on
# every daily step -- the branch advances whatever it is sent.  Each value below
# is therefore written against the step it belongs to, and
# :func:`command_arguments` asserts the invariant ``args[1] == expect_before``
# on every step recorded as sending the recorded cursor.  Two of the four daily
# steps originally sent the seed's value while claiming a later "before", which
# is exactly what that assertion exists to catch.
DAILY_SHORT_ARGS: List[Any] = [0, SEED_DAILY_CURSOR]
DAILY_GRANTING_ITEM = WEEKLY_LONG_ABSENT_ITEM
DAILY_GRANTING_ARGS: List[Any] = [DAILY_GRANTING_ITEM, SEED_DAILY_CURSOR + 1]
DAILY_OVERSIZED_NEXT_ID = 99
DAILY_OVERSIZED_ARGS: List[Any] = [0, DAILY_OVERSIZED_NEXT_ID]
# The position the oversized probe lands on, taken from the delivered contract's
# own wrap target rather than retyped, so the fixture cannot disagree with the
# arithmetic it is demonstrating.
DAILY_AFTER_BACKWARDS_ARGS: List[Any] = [
    0,
    rewards_envelope.DAILY_WRAP_TARGET,
]

NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]

# The three printed forms that name NO item, transcribed from the preserved
# branches.  The two that DO name an item are **derived from committed content**
# instead, by :func:`committed_item_name`, because the legacy name is
# ``get_attribute_from_item_id(id, "name")`` -- a committed string, not a
# literal in this file.  An earlier draft of this capture hardcoded the granting
# arm's message as "Won Metal Draggy"; item 1055 is in fact ``Mr. Treat``, so the
# literal was both unfaithful and unmaintainable.
PRINTED_WEEKLY_SHORT = "Won resources"
PRINTED_DAILY_RESOURCES = "Rewarded resources"
PRINTED_WEEKLY_ITEM = "Won %s"
PRINTED_DAILY_GRANTED = "Put %s in storage"

CURSOR_KEYS = {
    WEEKLY_COMMAND: rewards_envelope.WEEKLY_CURSOR_KEY,
    DAILY_COMMAND: rewards_envelope.DAILY_CURSOR_KEY,
}
STAMP_KEYS = {
    WEEKLY_COMMAND: rewards_envelope.WEEKLY_STAMP_KEY,
    DAILY_COMMAND: rewards_envelope.DAILY_STAMP_KEY,
}

# The four preserved arm names, read from the contract's own recorded tables
# rather than typed here, so a rename upstream cannot leave this capture calling
# a long arm "short" while asserting the wrong effects.  Ordered: the weekly
# branch's arms are selected by ARGUMENT COUNT and the daily branch's by the
# SIGN of a client-sent item, which is why the two pairs are asserted differently.
WEEKLY_LONG_ARM = str(rewards_envelope.WEEKLY_ARMS[0]["arm"])
WEEKLY_SHORT_ARM = str(rewards_envelope.WEEKLY_ARMS[1]["arm"])
DAILY_GRANTING_ARM = str(rewards_envelope.DAILY_ARMS[0]["arm"])
DAILY_RESOURCES_ARM = str(rewards_envelope.DAILY_ARMS[1]["arm"])

REDACTED = "<redacted>"
SENSITIVE_FORM_KEYS = ("user_key",)
SENSITIVE_ENVELOPE_KEYS = ("accessToken",)
SENSITIVE_HEADER_KEYS = ("Cookie", "Set-Cookie")

# **EIGHT** slots, not the seven ``engine.apply_resources`` writes.  The committed
# investigation compared all eight and found none moving, and
# ``privateState['energy']`` is a real stored resource that no legacy branch
# writes -- which is exactly why it is absent from that function.  A seven-slot
# comparison would be narrower than the evidence it claims to reproduce.
RESOURCE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
    "energy": ("privateState", "energy"),
}
RESOURCE_COUNT = len(RESOURCE_SLOTS)

# Already-committed fixture directories whose bytes this run must not change.
# The set is asserted against every other directory on disk by this line's
# offline parity suite, so a new predecessor cannot be added without appearing
# here first.
PROTECTED_FIXTURES = (
    "godot-building-collect",
    "godot-building-construction",
    "godot-building-expand",
    "godot-building-move",
    "godot-building-placement",
    "godot-building-sell",
    "godot-building-store",
    "godot-building-upgrade",
    "godot-building-xp",
    "godot-combat-actions",
    "godot-compatibility-boot",
    "godot-damage",
    "godot-item-purchase",
    "godot-quests",
    "godot-research",
    "godot-stored-item-placement",
    "godot-tutorial",
    "godot-unit-collection",
    "godot-unit-experience",
    "godot-unit-queues",
)


# --- the recorded transactions ---------------------------------------------
# ``expect`` is the oracle's own post-state, recomputed and asserted from the
# branches' arithmetic.  ``modern`` states what this capability derives instead,
# and where the two differ the step is marked ``divergence`` -- never ``parity``.
#
# ONE interleaved sequence: every step's ``expect_before`` is its predecessor's
# ``expect_after``, and the capture asserts that linkage step by step.
#
# The argument LISTS are CRAFTED and CLIENT-SUPPLIED on purpose.  The legacy
# branches read them and validate nothing, which is the finding.
def _step(command: str, args: List[Any], before: int, after: int,
          **extra: Any) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "command": command,
        "args": list(args),
        "argument_count": len(args),
        "cursor_key": CURSOR_KEYS[command],
        "expect_before": before,
        "expect_after": after,
        "parity": False,
    }
    entry.update(extra)
    # ONE derived predicate for "this step is expected to move a place a grant
    # could land", read from the three separate flags rather than re-deciding it
    # at each check.  Two of the three were previously covered by a single
    # `grants_a_row` test, which would have asserted that the storage-granting
    # step moved ONLY the cursor and the instant while it demonstrably also wrote
    # the storage -- the assertion and the record contradicting each other.
    entry["grant_landing_place_expected"] = bool(
        entry.get("grants_a_row")
        or entry.get("grants_unit_list_append")
        or entry.get("grants_into_storage")
    )
    return entry


TRANSACTIONS: List[Dict[str, Any]] = [
    # --- step 1: the short weekly arm, which grants nothing -----------------
    _step(
        WEEKLY_COMMAND,
        WEEKLY_SHORT_ARGS,
        SEED_WEEKLY_CURSOR,
        4,
        name="weekly_short_arm_grants_nothing",
        note=(
            "Zero arguments, so the branch takes its else arm: it prints 'Won "
            "resources', stamps the weekly instant, and advances the cursor. The "
            "whole-document leaf diff is EXACTLY TWO paths -- the cursor and the "
            "stamp -- which is the clean demonstration that a reward was won, a "
            "cursor moved, and nothing anywhere else changed."
        ),
        arm="short",
        grants_nothing=True,
        placed_rows_before=SEED_PLACED_ROWS,
        placed_rows_after=SEED_PLACED_ROWS,
        expect_placed_rows_after=SEED_PLACED_ROWS,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH,
        expect_storage_after=SEED_STORAGE,
        # 3 -> 4, and the weekly schedule has THREE entries, so position 4 is one
        # the schedule CANNOT answer.  Recorded rather than refused: the branch
        # does not read the schedule at all.
        successor_unaddressable=True,
        parity=True,
        parity_note=(
            "For the short arm the oracle's transition and this capability's "
            "derived transition are the same number, because the branch advances "
            "the recorded cursor by the derived bound's own modulo arithmetic and "
            "the short arm grants nothing."
        ),
    ),
    # --- step 2: the long weekly arm APPENDING an absent unit ---------------
    _step(
        WEEKLY_COMMAND,
        WEEKLY_LONG_ABSENT_ARGS,
        4,
        0,
        name="weekly_long_arm_appends_an_absent_unit",
        note=(
            "Five arguments, so the branch takes its granting arm: it places the "
            "CLIENT-SENT item at the CLIENT-SENT index, cell, and player team, and "
            "records the item through the deduplicating unit-list helper. The "
            "client-sent unit id is one the weekly schedule's list-valued rung "
            "names and the seed's list does NOT, so the list grows 135 -> 136 and "
            "the placed-row count 549 -> 550. This is the THIRD divergence -- the "
            "arm is selected by the CLIENT'S ARITY, so one command has two "
            "different effects."
        ),
        arm="long",
        grants_a_row=True,
        grants_unit_list_append=True,
        placed_rows_before=SEED_PLACED_ROWS,
        placed_rows_after=SEED_PLACED_ROWS + 1,
        expect_placed_rows_after=SEED_PLACED_ROWS + 1,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after=SEED_STORAGE,
        unit_item_sent=WEEKLY_LONG_ABSENT_ITEM,
        unit_item_was_absent=True,
        placed_index_sent=WEEKLY_LONG_ABSENT_ARGS[0],
        placed_item_sent=WEEKLY_LONG_ABSENT_ARGS[1],
        placed_cell_sent=[WEEKLY_LONG_ABSENT_ARGS[2], WEEKLY_LONG_ABSENT_ARGS[3]],
        placed_player_sent=WEEKLY_LONG_ABSENT_ARGS[4],
        modern_refuses="client_supplied_item / client_supplied_cell / "
                       "client_supplied_player / client_supplied_item_index",
        divergence="arity_selects_the_arm",
    ),
    # --- step 3: the SAME arm, DEDUPLICATING a present unit -----------------
    # Identical to step 2 except for the client-sent item id, and the outcome
    # differs in the unit list only: the row is still placed, but the list does
    # not grow.  This is what executes engine.py:88's `if item not in
    # boughtUnits` rather than citing it.
    _step(
        WEEKLY_COMMAND,
        WEEKLY_LONG_PRESENT_ARGS,
        0,
        1,
        name="weekly_long_arm_deduplicates_a_present_unit",
        note=(
            "The same granting arm, the same arity, and the same cell and player "
            "team -- only the client-sent item id differs, and it is one the seed's "
            "list already carries. The row is STILL placed (550 -> 551) while the "
            "unit list stands at 136. The placed-row half of the four-part grant "
            "proof and the unit-list half therefore have OPPOSITE outcomes under "
            "one request, which is only observable by executing both."
        ),
        arm="long",
        grants_a_row=True,
        placed_rows_before=SEED_PLACED_ROWS + 1,
        placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after=SEED_STORAGE,
        unit_item_sent=WEEKLY_LONG_PRESENT_ITEM,
        unit_item_was_absent=False,
        placed_index_sent=WEEKLY_LONG_PRESENT_ARGS[0],
        placed_item_sent=WEEKLY_LONG_PRESENT_ARGS[1],
        placed_cell_sent=[WEEKLY_LONG_PRESENT_ARGS[2], WEEKLY_LONG_PRESENT_ARGS[3]],
        placed_player_sent=WEEKLY_LONG_PRESENT_ARGS[4],
        modern_refuses="client_supplied_item / client_supplied_cell / "
                       "client_supplied_player / client_supplied_item_index",
        divergence="arity_selects_the_arm",
    ),
    # --- step 4: the short daily arm ----------------------------------------
    _step(
        DAILY_COMMAND,
        DAILY_SHORT_ARGS,
        SEED_DAILY_CURSOR,
        3,
        name="daily_short_arm_grants_nothing",
        note=(
            "The recorded cursor is sent as args[1], so the branch's 'args[1] + 1' "
            "advances the RECORDED value and item 0 takes the else arm. 2 -> 3."
        ),
        arm="resources",
        grants_nothing=True,
        placed_rows_before=SEED_PLACED_ROWS + 2,
        placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after=SEED_STORAGE,
        next_id_sent=SEED_DAILY_CURSOR,
        next_id_sent_is_the_recorded_cursor=True,
        # The delivered route DERIVES args[1] from the recorded cursor, so its
        # number is the recorded one here and the two agree.
        parity=True,
        parity_note=(
            "The delivered route sends the RECORDED cursor as args[1] rather than "
            "the recorded successor, so the oracle's 'args[1] + 1' and the derived "
            "successor are the same number. What differs is WHERE that number comes "
            "from, which is recorded as the next-id divergence."
        ),
    ),
    # --- step 5: the GRANTING daily arm, which writes the storage ------------
    # The third of the three "unchanged" halves of the four-part grant proof. The
    # seed's storage is EMPTY, so this step is the only way the capture can show
    # that the storage clause of the delivered route's proof could ever fail.
    _step(
        DAILY_COMMAND,
        DAILY_GRANTING_ARGS,
        3,
        4,
        name="daily_granting_arm_lands_in_storage",
        note=(
            "A positive client-sent item takes the granting arm, which calls BOTH "
            "grant helpers: the deduplicating unit-list one and the ACCUMULATING "
            "storage one. The storage was empty and becomes exactly one entry for "
            "the client-sent id, while the unit list does NOT grow because step 2 "
            "already added that id. One grant, two landing places, two different "
            "rules -- executed rather than read at engine.py:70-75 and 86-89."
        ),
        arm="granting",
        grants_into_storage=True,
        placed_rows_before=SEED_PLACED_ROWS + 2,
        placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after={str(DAILY_GRANTING_ITEM): 1},
        unit_item_sent=DAILY_GRANTING_ITEM,
        unit_item_was_absent=False,
        storage_item_sent=DAILY_GRANTING_ITEM,
        next_id_sent=DAILY_GRANTING_ARGS[1],
        next_id_sent_is_the_recorded_cursor=True,
        modern_refuses="client_supplied_item",
        divergence="client_supplied_item",
    ),
    # --- step 6: the OVERSIZED client next id, executed ---------------------
    _step(
        DAILY_COMMAND,
        DAILY_OVERSIZED_ARGS,
        4,
        1,
        name="daily_oversized_next_id_moves_the_cursor_backwards",
        note=(
            "The client sends a next id of 99. The branch computes 100, sees that "
            "it exceeds the hardcoded literal 5, and OVERWRITES it with 1 -- so the "
            "recorded cursor moves 4 -> 1, BACKWARDS. This is the sharpest "
            "divergence in the line and it is executed rather than argued: the "
            "backwards move is visible in the preserved source at command.py:446 "
            "and 451-452, and this transaction demonstrates it."
        ),
        arm="resources",
        grants_nothing=True,
        placed_rows_before=SEED_PLACED_ROWS + 2,
        placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after={str(DAILY_GRANTING_ITEM): 1},
        next_id_sent=DAILY_OVERSIZED_NEXT_ID,
        next_id_sent_is_the_recorded_cursor=False,
        moved_backwards=True,
        modern_derives_after=5,
        modern_refuses="client_supplied_next_id",
        divergence="client_supplied_next_id",
    ),
    # --- step 7: the daily arm on the unaddressable position ---------------
    # 4 -> 1 above left the recorded cursor ON the first position, so this step
    # runs it back up.  It exists because the delivered route's whole-document
    # containment allowlist must be exercised over a step whose oracle
    # predecessor moved BACKWARDS: if the sequence were not linked, this step's
    # "before" would not be 1.
    _step(
        DAILY_COMMAND,
        DAILY_AFTER_BACKWARDS_ARGS,
        1,
        2,
        name="daily_after_the_backwards_move",
        note=(
            "Driven after the backwards move, so its recorded 'before' is the 1 the "
            "previous step wrote. This link is what proves the sequence is one: on "
            "a fresh seed the cursor would have been 2 and this step's before would "
            "differ."
        ),
        arm="resources",
        grants_nothing=True,
        placed_rows_before=SEED_PLACED_ROWS + 2,
        placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_placed_rows_after=SEED_PLACED_ROWS + 2,
        expect_unit_list_after=SEED_UNIT_LIST_LENGTH + 1,
        expect_storage_after={str(DAILY_GRANTING_ITEM): 1},
        next_id_sent=DAILY_AFTER_BACKWARDS_ARGS[1],
        next_id_sent_is_the_recorded_cursor=True,
        parity=True,
        parity_note=(
            "As on step 4: the delivered route feeds the recorded cursor to the "
            "branch, so the two transitions agree numerically."
        ),
    ),
]

for _index, _entry in enumerate(TRANSACTIONS, start=1):
    _entry["step"] = _index

RECORDED_STEPS = tuple("txn_%s" % entry["name"] for entry in TRANSACTIONS)

SEQUENCE_NOTE = (
    "All %d steps are ONE interleaved sequence against ONE disposable, because "
    "the recorded cursors only mean anything if each step ran against its "
    "predecessor's recorded state -- and the oversized probe is the link that "
    "would break first, since it is the only step whose oracle result is not the "
    "recorded value advanced by one." % len(TRANSACTIONS)
)

# The recorded weekly cursor ladder: 3 -> 4 -> 0 -> 1.  Position 4 is one the
# weekly schedule cannot answer, and the modulo wraps 4 to 0.
RECORDED_WEEKLY_LADDER = [4, 0, 1]
# The recorded daily cursor ladder, in which the SIXTH step moves BACKWARDS.
RECORDED_DAILY_LADDER = [3, 4, 1, 2]


# --- helpers ---------------------------------------------------------------


def committed_digest(data: bytes) -> str:
    """SHA-256 over the **committed blob** form of ``data``.

    Every digest recorded by this capture is over text that will be committed
    and then checked out again, and this repository sets ``core.autocrlf=true``
    with no ``.gitattributes`` entry for ``tests/fixtures/**``.  A checkout may
    therefore hold CRLF or LF for byte-identical committed content, so a digest
    taken over raw working-tree bytes is only valid on the checkout that produced
    it.

    Normalising CRLF to LF makes the recorded digest mean "these committed
    bytes", which is the only claim a fixture digest can make.  This is the same
    normalisation the damage and unit-experience captures apply.
    """
    return sha256_bytes(data.replace(b"\r\n", b"\n"))


def seed_target_of(disposable: Path, pid: str) -> Path:
    """Where ``build_disposable`` copied the seed, rebuilt from its own rule."""
    return disposable / "saves" / ("%s.save.json" % pid)


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that refuses to conflate ``1``, ``1.0`` and ``True``."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, int) or isinstance(right, int):
        if isinstance(left, int) and isinstance(right, int):
            return left == right
        return False
    if isinstance(left, float) or isinstance(right, float):
        if isinstance(left, float) and isinstance(right, float):
            return left == right
        return False
    if isinstance(left, str) or isinstance(right, str):
        if isinstance(left, str) and isinstance(right, str):
            return left == right
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        if sorted(left) != sorted(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def leaf_items(document: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Every leaf of a JSON document as sorted ``(json pointer path, value)``.

    Containers are **not** recorded; :func:`container_paths` records those, so an
    added or emptied container is still a difference.
    """
    out: List[Tuple[str, Any]] = []
    if isinstance(document, dict):
        for key in sorted(document):
            out.extend(leaf_items(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            out.extend(leaf_items(value, "%s/%d" % (prefix, index)))
    else:
        out.append((prefix, document))
    return out


def container_paths(document: Any, prefix: str = "") -> List[Tuple[str, int]]:
    """Every container node of a JSON document with its child count."""
    out: List[Tuple[str, int]] = []
    if isinstance(document, dict):
        out.append((prefix, len(document)))
        for key in sorted(document):
            out.extend(container_paths(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        out.append((prefix, len(document)))
        for index, value in enumerate(document):
            out.extend(container_paths(value, "%s/%d" % (prefix, index)))
    return out


def canonical_state_sha(document: Any) -> str:
    """Whole-document digest over every leaf and container, order-independent.

    Containers are included here because a row placed by a granting arm adds
    ``/maps/0/items/600`` **and** grows ``/maps/0/items`` from 549 to 550; a
    leaves-only digest would record the new row but not the size change, which is
    the same defect class the delivered allowlist exists to catch.  It also means
    an **added or emptied container** is still a difference, since
    :func:`leaf_items` records nothing for one.

    The two sets of paths are **disjoint** -- a node is either a container or a
    leaf, never both -- which is what lets them share one canonical digest:
    :func:`canonical_digest` requires unique paths and raises otherwise, so a
    collision here would be a loud failure rather than a silently weaker digest.
    The node kind is recorded in the digest half of the pair, not in the path.
    """
    parts: List[Tuple[str, str]] = [
        (path, "leaf %s" % payload_json(value)) for path, value in leaf_items(document)
    ]
    parts.extend(
        (path, "container %d" % size) for path, size in container_paths(document)
    )
    return canonical_digest(parts)


def leaf_diff(before: Any, after: Any) -> List[Tuple[str, Any, Any, Any, Any]]:
    """``(path, present_before, before, present_after, after)`` over leaves."""
    before_map = {path: (True, value) for path, value in leaf_items(before)}
    after_map = {path: (True, value) for path, value in leaf_items(after)}
    out: List[Tuple[str, Any, Any, Any, Any]] = []
    for path in sorted(set(before_map) | set(after_map)):
        in_before = before_map.get(path)
        in_after = after_map.get(path)
        left = in_before[1] if in_before else None
        right = in_after[1] if in_after else None
        if in_before is None or in_after is None or not typed_equal(left, right):
            out.append((path, in_before is not None, left, in_after is not None, right))
    return out


def diff_payload(diff: List[Tuple[str, Any, Any, Any, Any]]) -> List[Dict[str, Any]]:
    """JSON-safe form of :func:`leaf_diff`, so the fixture is reviewable."""
    return [
        {
            "path": path,
            "present_before": bool(in_before),
            "before": left,
            "present_after": bool(in_after),
            "after": right,
        }
        for path, in_before, left, in_after, right in diff
    ]


def read_at(document: Dict[str, Any], location: Tuple[Any, ...]) -> Any:
    """The value at a save location, or the sentinel string ``"<absent>"``.

    Five of the eight resource slots are reached through the ``maps`` **list**
    (``maps[0].xp``), so this has to walk sequences as well as objects.  An
    earlier dict-only version silently reported every one of those five as
    absent, because ``0 not in {"xp": ...}``.
    """
    cursor: Any = document
    for step in location:
        if isinstance(cursor, dict):
            if step not in cursor:
                return "<absent>"
            cursor = cursor[step]
        elif isinstance(cursor, (list, tuple)):
            if not isinstance(step, int) or isinstance(step, bool):
                return "<absent>"
            if step >= len(cursor) or step < -len(cursor):
                return "<absent>"
            cursor = cursor[step]
        else:
            return "<absent>"
    return cursor


def stored_resources(document: Dict[str, Any]) -> Dict[str, Any]:
    """All eight stored resource slots, read at their established locations."""
    out: Dict[str, Any] = {}
    for name, location in RESOURCE_SLOTS.items():
        value = read_at(document, location)
        if value == "<absent>":
            raise CaptureError(
                EXIT_REQUEST,
                "save has no %s resource slot at /%s"
                % (name, "/".join(str(part) for part in location)),
            )
        out[name] = value
    return out


def placed_rows(document: Dict[str, Any]) -> List[Any]:
    try:
        rows = document["maps"][0][rewards_envelope.MAP_ITEMS_KEY]
    except (KeyError, IndexError, TypeError) as error:
        raise CaptureError(EXIT_REQUEST, "save has no maps[0].items: %s" % error)
    if not isinstance(rows, dict):
        raise CaptureError(EXIT_REQUEST, "maps[0].items is not an object")
    return [rows[key] for key in sorted(rows)]


def placed_row_count(document: Dict[str, Any]) -> int:
    return len(placed_rows(document))


def unit_list(document: Dict[str, Any]) -> Any:
    """The unit list as it stands, or the absent sentinel.

    Read **verbatim, as a list including its order**: the preserved helper
    deduplicates rather than accumulating, so a repeat grant leaves it
    byte-identical, and an order-preserving copy is what makes that claim
    mechanical instead of a statement about the length alone.
    """
    value = read_at(document, ("privateState", rewards_envelope.WEEKLY_UNIT_LIST_KEY))
    if value == "<absent>":
        return "<absent>"
    if not isinstance(value, list):
        raise CaptureError(
            EXIT_REQUEST,
            "privateState.%s is %s, not a list"
            % (rewards_envelope.WEEKLY_UNIT_LIST_KEY, type(value).__name__),
        )
    return list(value)


def storage(document: Dict[str, Any]) -> Any:
    """The storage mapping verbatim, or the absent sentinel."""
    value = read_at(document, ("maps", 0, rewards_envelope.DAILY_STORE_KEY))
    if value == "<absent>":
        return "<absent>"
    if not isinstance(value, dict):
        raise CaptureError(
            EXIT_REQUEST, "maps[0].store is %s, not an object" % type(value).__name__
        )
    return {str(key): value[key] for key in sorted(value)}


def sanitize_form(form: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_FORM_KEYS else value)
        for key, value in form.items()
    }


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        key: (REDACTED if key in SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


def sanitize_envelope_data(data: str) -> str:
    """Redact any non-empty token in the recorded ``data`` field.

    The live request always sends the real bytes; only the record is redacted.
    ``ts`` is deliberately NOT redacted -- it is pinned to a constant, which is
    what makes the recorded field byte-stable.
    """
    envelope = parse_data_field(data)
    changed = False
    for key in SENSITIVE_ENVELOPE_KEYS:
        if envelope.get(key):
            envelope[key] = REDACTED
            changed = True
    if not changed:
        return data
    return data_field(envelope)


def expected_cursor_after(entry: Dict[str, Any]) -> int:
    """The oracle's post-cursor, recomputed from the branches' own arithmetic.

    Transcribed, not invented:

    * ``weekly_reward`` writes ``(before + 1) % get_weekly_reward_length()``, so
      the successor is a modulo by the **derived** bound (design D3);
    * ``win_daily_bonus`` writes ``args[1] + 1`` and then overwrites it with 1 if
      the result exceeds the **hardcoded literal** ``5``.  The value it overwrites
      with is the source of the backwards move, so it is recomputed here rather
      than transcribed: a step whose recorded "after" is below its recorded
      "before" is only legitimate when the client-supplied next id is the cause.

    The client-sent cursor is therefore **never** assumed to be the recorded one.
    """
    command = str(entry["command"])
    before = int(entry["expect_before"])
    if command == WEEKLY_COMMAND:
        bound = rewards_envelope.weekly_bound(committed_schedules()[
            rewards_envelope.WEEKLY_SCHEDULE_KEY
        ])
        return (before + 1) % bound
    supplied = int(entry["args"][1])
    successor = supplied + 1
    if successor > rewards_envelope.DAILY_BOUND_LITERAL:
        return rewards_envelope.DAILY_WRAP_TARGET
    return successor


def committed_item_name(item_id: Any) -> str:
    """The committed display name for an item id, exactly as the server reads it.

    ``get_name_from_item_id`` is ``get_attribute_from_item_id(id, "name")``
    (``get_game_config.py:127``), i.e. the committed ``name`` string -- so the
    expected printed message is **derived from content**, not transcribed here.
    The granting arms both print that name, which makes those two printed lines a
    content check as well as a branch check: a mistranscribed literal would have
    been indistinguishable from a branch that printed the wrong item.
    """
    document = json.loads(
        (REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
    )
    for row in document.get("items", []):
        if str(row.get("id")) == str(item_id):
            name = row.get("name")
            if isinstance(name, str):
                return name
            break
    raise CaptureError(
        EXIT_ENVIRONMENT,
        "config/main.json carries no name for item %r" % (item_id,),
    )


def committed_schedules() -> Dict[str, Any]:
    """Both committed reward schedules, read from the raw served configuration.

    Read from ``config/main.json`` rather than hardcoded, because the weekly bound
    this capture recomputes is *supposed* to be derived from committed content.
    Transcribing the schedule would make the derivation circular.
    """
    document = json.loads((REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
    globals_block = document.get(rewards_envelope.GLOBALS_KEY)
    if not isinstance(globals_block, dict):
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "config/main.json carries no %r object" % rewards_envelope.GLOBALS_KEY,
        )
    out: Dict[str, Any] = {}
    for action in rewards_envelope.ACTIONS:
        key = rewards_envelope.ACTION_SCHEDULE_KEY[action]
        if key not in globals_block:
            raise CaptureError(
                EXIT_ENVIRONMENT, "config/main.json carries no %r schedule" % key
            )
        out[key] = globals_block[key]
    return out


def await_clock_past(stamp_value: Any, where: str) -> int:
    """Block until the wall clock has moved strictly past a recorded instant.

    Both preserved branches write ``time_now`` **unconditionally**
    (``command.py:361`` and ``:454``), so every step's stamped instant should
    change.  It does not necessarily: ``time_now`` is a whole Unix second, and
    two steps dispatched inside the same second write the same value.  Asserting
    "the instant changed" against a clock the capture does not control would be
    asserting something about the wall clock rather than about the branch, and it
    would fail intermittently instead of deterministically -- which is the
    seventh recorded flaky surface in this project, in a new place.

    So the capture **waits for the condition it is about to assert**: it blocks
    until the current second is strictly greater than the instant the step is
    about to overwrite.  That makes the recorded stamp change observable and the
    assertion exact, costing at most a second per step.  Nothing else about a
    transaction depends on the wait -- it happens before the request is sent,
    never during it.

    A missing or non-integer recorded instant returns immediately: that is the
    absence the ``absent_stamp`` refusal exists for, and this capture is
    establishing the oracle's behaviour on a corpus that carries the field, so it
    must not paper over the other case.
    """
    if not isinstance(stamp_value, int) or isinstance(stamp_value, bool):
        return 0
    waited = 0
    while int(time.time()) <= int(stamp_value):
        time.sleep(0.02)
        waited += 1
    return waited


def command_arguments(entry: Dict[str, Any]) -> List[Tuple[str, List[Any]]]:
    """The single crafted command this step sends, with its arm proved reachable.

    The resource vector is the neutral all-zero one because neither branch
    charges anything.  What is checked here is the **arm selector**, and the two
    branches select differently, so the two checks are deliberately different
    shapes rather than one shared assertion:

    * ``weekly_reward`` chooses its arm on ``len(args) > 4`` and nothing else.
      The delivered contract always sends zero, which is the non-granting arm, so
      a step recorded as the **long** arm must send strictly more -- otherwise
      the "one command, two effects" divergence would be recorded from a
      request that in fact took the same arm as the modern contract, and the
      whole third divergence would be unproven.
    * ``win_daily_bonus`` chooses its arm on the **sign of a client-sent item**
      and always takes exactly two arguments, so its arity must match the
      delivered count on every step including the oversized-next-id probe, while
      its recorded arm must agree with the sign of ``args[0]``.  The oversized
      probe differs from the parity step in the *value* of ``args[1]``, never in
      the arity.

    The count is looked up through the derived command-to-action **inverse**,
    not by transcribing a second table here: this capture addresses the
    preserved commands by their legacy names, while the delivered contract keys
    everything on the modern action.  Two spellings of the same mapping is where
    the two reward branches could silently swap.
    """
    args = list(entry["args"])
    command = str(entry["command"])
    action = rewards_envelope.ACTION_FOR_COMMAND[command]
    delivered_count = int(rewards_envelope.ACTION_ARGUMENT_COUNT[action])
    sent = len(args)
    arm = str(entry.get("arm", ""))
    where = "%s (%s)" % (str(entry["name"]), command)

    if command == WEEKLY_COMMAND:
        if arm == WEEKLY_LONG_ARM:
            if sent <= delivered_count:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s is recorded as the long arm but sends %d arguments, which "
                    "is not more than the delivered contract's %d, so it would "
                    "take the same arm and prove nothing"
                    % (where, sent, delivered_count),
                )
        elif arm == WEEKLY_SHORT_ARM:
            if sent != delivered_count:
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s is recorded as the short arm but sends %d arguments "
                    "against the delivered contract's %d"
                    % (where, sent, delivered_count),
                )
        else:
            raise CaptureError(
                EXIT_REQUEST,
                "%s records arm %r, which is neither recorded weekly arm"
                % (where, arm),
            )
        return [(command, args)]

    if sent != delivered_count:
        raise CaptureError(
            EXIT_REQUEST,
            "%s sends %d arguments, but the delivered contract records %d for "
            "that command" % (where, sent, delivered_count),
        )
    item = args[0]
    # The daily branch advances ``args[1]`` itself, so a step recorded as
    # feeding it the RECORDED cursor must send exactly its own "before".  This
    # is the invariant the seed's constant cannot express, because the cursor
    # moves during the sequence.
    if entry.get("next_id_sent_is_the_recorded_cursor") and args[1] != int(
        entry["expect_before"]
    ):
        raise CaptureError(
            EXIT_REQUEST,
            "%s sends next id %r while recorded as sending its own recorded "
            "cursor %r" % (where, args[1], entry["expect_before"]),
        )
    if arm == DAILY_GRANTING_ARM and not item > 0:
        raise CaptureError(
            EXIT_REQUEST,
            "%s is recorded as the granting arm but sends item %r, and the "
            "branch tests item > 0" % (where, item),
        )
    if arm == DAILY_RESOURCES_ARM and item > 0:
        raise CaptureError(
            EXIT_REQUEST,
            "%s is recorded as the resources arm but sends item %r, which takes "
            "the granting arm" % (where, item),
        )
    return [(command, args)]


def build_envelope(pairs: List[Tuple[str, List[Any]]]) -> Dict[str, Any]:
    """The legacy batch envelope, with a pinned ``ts`` for byte stability."""
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": FIXTURE_TS,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [0, command, list(args), list(NEUTRAL_VECTOR)]
            for command, args in pairs
        ],
    }


def verify_envelope(envelope: Dict[str, Any], pairs: List[Tuple[str, List[Any]]]) -> None:
    """Assert the envelope this capture sends is the shape it claims.

    A capture that asserts its own request cannot quietly drift into sending
    something the manifest does not describe -- which is the failure mode that
    would make every recorded transition untrustworthy.
    """
    if sorted(envelope) != sorted(ENVELOPE_KEYS):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope keys are %r, not %r" % (sorted(envelope), sorted(ENVELOPE_KEYS)),
        )
    if envelope["ts"] != FIXTURE_TS:
        raise CaptureError(EXIT_REQUEST, "envelope ts is not the pinned constant")
    if len(envelope["commands"]) != len(pairs):
        raise CaptureError(
            EXIT_REQUEST,
            "envelope carries %d commands, not the %d crafted"
            % (len(envelope["commands"]), len(pairs)),
        )
    for command_row, (command, args) in zip(envelope["commands"], pairs):
        if command_row[0] != 0:
            raise CaptureError(EXIT_REQUEST, "command row must start at 0")
        if command_row[1] != command:
            raise CaptureError(
                EXIT_REQUEST,
                "command row names %r, not the crafted %r" % (command_row[1], command),
            )
        if list(command_row[2]) != list(args):
            raise CaptureError(
                EXIT_REQUEST,
                "command arguments are %r, not the crafted %r"
                % (list(command_row[2]), list(args)),
            )
        if list(command_row[3]) != list(NEUTRAL_VECTOR):
            raise CaptureError(
                EXIT_REQUEST,
                "resource vector is %r, not the neutral %r"
                % (list(command_row[3]), list(NEUTRAL_VECTOR)),
            )


def verify_seed(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Assert the committed corpus really carries what this fixture assumes.

    Run **before** a single server starts, so an environment change fails loudly
    instead of producing a fixture that quietly disagrees with the record.
    """
    private = read_at(seed, ("privateState",))
    if not isinstance(private, dict):
        raise CaptureError(EXIT_ENVIRONMENT, "the seed has no privateState object")
    for key, expected in (
        (rewards_envelope.WEEKLY_CURSOR_KEY, SEED_WEEKLY_CURSOR),
        (rewards_envelope.DAILY_CURSOR_KEY, SEED_DAILY_CURSOR),
        (rewards_envelope.WEEKLY_STAMP_KEY, SEED_WEEKLY_STAMP),
        (rewards_envelope.DAILY_STAMP_KEY, SEED_DAILY_STAMP),
    ):
        actual = private.get(key, "<absent>")
        if actual != expected:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the seed's privateState[%r] is %r, not the recorded %r"
                % (key, actual, expected),
            )
    for name, location in RESOURCE_SLOTS.items():
        if read_at(seed, location) == "<absent>":
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the seed records no %s slot, so the eight-slot comparison this "
                "capture asserts cannot be made" % name,
            )
    pid = str(read_at(seed, ("playerInfo", "pid")))
    if pid != SEED_PID:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's playerInfo.pid is %r, not the recorded %r -- the pid is "
            "read from the document, never from the filename stem"
            % (pid, SEED_PID),
        )
    rows = placed_row_count(seed)
    if rows != SEED_PLACED_ROWS:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed places %d rows, not the recorded %d" % (rows, SEED_PLACED_ROWS),
        )
    units = unit_list(seed)
    if not isinstance(units, list) or len(units) != SEED_UNIT_LIST_LENGTH:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's unit list holds %r entries, not the recorded %d"
            % (len(units) if isinstance(units, list) else units, SEED_UNIT_LIST_LENGTH),
        )
    store = storage(seed)
    if store != SEED_STORAGE:
        raise CaptureError(
            EXIT_ENVIRONMENT,
            "the seed's storage is %r, not the recorded empty object, so the "
            "granting arms' storage effect would not be observable" % store,
        )
    committed_items = read_at(seed, ("maps", 0, "items"))
    for label, args in (
        ("absent-unit", WEEKLY_LONG_ABSENT_ARGS),
        ("present-unit", WEEKLY_LONG_PRESENT_ARGS),
    ):
        long_index = str(args[0])
        if long_index in committed_items:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the seed already carries map index %r, so the %s granting arm "
                "would overwrite a committed row rather than add one"
                % (long_index, label),
            )
    # The two client-sent unit ids are chosen for OPPOSITE reasons -- one absent
    # from the seed's list so the helper appends, one present so it deduplicates
    # -- and both must be ids the weekly schedule's own list-valued rung names.
    # Asserting it here is what stops the pair from decaying into two arbitrary
    # numbers that merely happen to work.
    weekly_units: List[int] = []
    for entry_row in committed_schedules()[rewards_envelope.WEEKLY_SCHEDULE_KEY]:
        if isinstance(entry_row, dict) and isinstance(entry_row.get("value"), list):
            weekly_units.extend(int(value) for value in entry_row["value"])
    for label, item_id, should_be_absent in (
        ("absent-unit", WEEKLY_LONG_ABSENT_ITEM, True),
        ("present-unit", WEEKLY_LONG_PRESENT_ITEM, False),
    ):
        if item_id not in weekly_units:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the %s client-sent item %d is not one the weekly schedule's "
                "list-valued rung names (%r)" % (label, item_id, weekly_units),
            )
        is_absent = item_id not in units
        if is_absent != should_be_absent:
            raise CaptureError(
                EXIT_ENVIRONMENT,
                "the %s client-sent item %d is %s the seed's unit list, which "
                "breaks the append/deduplicate pair this fixture is built on"
                % (label, item_id, "absent from" if is_absent else "present in"),
            )
    return {
        "path": str(SEED.relative_to(REPO_ROOT)).replace("\\", "/"),
        "placed_rows": rows,
        "weekly_cursor": SEED_WEEKLY_CURSOR,
        "daily_cursor": SEED_DAILY_CURSOR,
        "weekly_stamp": SEED_WEEKLY_STAMP,
        "daily_stamp": SEED_DAILY_STAMP,
        "unit_list_length": len(units),
        "weekly_schedule_unit_ids": weekly_units,
        "absent_item": WEEKLY_LONG_ABSENT_ITEM,
        "absent_item_is_absent_from_the_unit_list": True,
        "present_item": WEEKLY_LONG_PRESENT_ITEM,
        "present_item_is_in_the_unit_list": True,
        "storage": store,
        "storage_is_empty_so_the_grant_lands_visibly": store == SEED_STORAGE,
        "resource_slots": sorted(stored_resources(seed)),
        "resource_slot_count": RESOURCE_COUNT,
        "pid_read_from_document": pid,
        "why_this_one": (
            "It is one of only two committed corpora whose weekly cursor is above "
            "1, and at 3 its successor lands on position 4 -- a position the "
            "three-entry weekly schedule CANNOT answer. villages/Nerri.json at 2 "
            "would land on 3, which the schedule also cannot answer but is the "
            "smaller demonstration."
        ),
    }


def verify_transaction(
    entry: Dict[str, Any],
    before: Dict[str, Any],
    after: Dict[str, Any],
    status: int,
) -> Dict[str, Any]:
    """Recompute the oracle's post-state and assert it, leaf by leaf."""
    name = str(entry["name"])
    command = str(entry["command"])
    cursor_key = str(entry["cursor_key"])
    stamp_key = STAMP_KEYS[command]

    cursor_before = read_at(before, ("privateState", cursor_key))
    cursor_after = read_at(after, ("privateState", cursor_key))
    stamp_before = read_at(before, ("privateState", stamp_key))
    stamp_after = read_at(after, ("privateState", stamp_key))

    if cursor_before != entry["expect_before"]:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the recorded cursor was %r before the step, not the recorded %r "
            "-- the sequence is not running against its predecessor's state"
            % (name, cursor_before, entry["expect_before"]),
        )
    if cursor_after != entry["expect_after"]:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the recorded cursor is %r after the step, not the recorded %r"
            % (name, cursor_after, entry["expect_after"]),
        )
    recomputed = expected_cursor_after(entry)
    if int(cursor_after) != recomputed:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the recorded cursor is %r, not the %r recomputed from the "
            "branch's own arithmetic" % (name, cursor_after, recomputed),
        )

    # The instant is stamped UNCONDITIONALLY by both branches, so it must move
    # and it must not be the value it held.  The value itself is a wall clock,
    # so it is compared by shape rather than by equality -- and it is recorded
    # as a volatile field, which is why a successful step cannot be compared by
    # whole-document equality while a refused one can.
    if typed_equal(stamp_before, stamp_after):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the instant was not re-stamped (still %r); both branches write "
            "it unconditionally (command.py:361, command.py:454)"
            % (name, stamp_after),
        )
    if not isinstance(stamp_after, int) or isinstance(stamp_after, bool):
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the instant is %r after the step, not an integer" % (name, stamp_after),
        )

    diff = leaf_diff(before, after)
    changed_paths = [row[0] for row in diff]

    # The four places a grant could land, checked per step rather than once for
    # the fixture.  A granting step is EXPECTED to change the placed rows, the
    # unit list, and the storage; a non-granting step is expected to change
    # NONE of them, and that expectation is what makes the delivered route's
    # containment proof non-tautological rather than vacuous.
    rows_before = placed_rows(before)
    rows_after = placed_rows(after)
    units_before = unit_list(before)
    units_after = unit_list(after)
    store_before = storage(before)
    store_after = storage(after)

    expect_rows = int(entry["expect_placed_rows_after"])
    expect_units = int(entry["expect_unit_list_after"])
    if len(rows_after) != expect_rows:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the placed-row count is %d after the step, not the recorded %d"
            % (name, len(rows_after), expect_rows),
        )
    if len(rows_after) == len(rows_before):
        unchanged = rows_after == rows_before
    else:
        # A granting arm APPENDS by key, so the shared keys must all be
        # byte-identical; a replacement would be a different behaviour.
        before_map = dict(read_at(before, ("maps", 0, "items")))
        after_map = dict(read_at(after, ("maps", 0, "items")))
        added = sorted(set(after_map) - set(before_map))
        removed = sorted(set(before_map) - set(after_map))
        if removed:
            raise CaptureError(
                EXIT_REQUEST,
                "%s: the granting arm REMOVED map keys %r; the preserved helper "
                "writes one key and removes none" % (name, removed),
            )
        if added != [str(entry["placed_index_sent"])]:
            raise CaptureError(
                EXIT_REQUEST,
                "%s: the granting arm added map keys %r, not the recorded %r"
                % (name, added, [str(entry["placed_index_sent"])]),
            )
        for key in before_map:
            if not typed_equal(before_map[key], after_map[key]):
                raise CaptureError(
                    EXIT_REQUEST,
                    "%s: the granting arm CHANGED the committed row at key %r, "
                    "which it only appends" % (name, key),
                )
        unchanged = True
    if not unchanged:
        raise CaptureError(
            EXIT_REQUEST, "%s: an existing placed row changed" % name
        )
    if len(units_after) != expect_units:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the unit list holds %d entries after the step, not the recorded "
            "%d" % (name, len(units_after), expect_units),
        )
    # The list's ORDER is preserved by the preserved helper, so a length match
    # plus an order-sensitive comparison is what "byte-identical" means here.
    if expect_units == len(units_before):
        if not typed_equal(units_before, units_after):
            raise CaptureError(
                EXIT_REQUEST,
                "%s: the unit list has the recorded length but is not "
                "byte-identical" % name,
            )
    else:
        shared = list(units_before)
        appended = list(units_after)
        if appended[: len(shared)] != shared:
            raise CaptureError(
                EXIT_REQUEST,
                "%s: the unit list's recorded entries are not a prefix of the "
                "post-state, so the helper did not append" % name,
            )
        if appended[len(shared):] != [entry["unit_item_sent"]]:
            raise CaptureError(
                EXIT_REQUEST,
                "%s: the unit list appended %r, not the recorded client-sent item"
                % (name, appended[len(shared):]),
            )

    # The storage clause of the four-part grant proof, asserted the same way as
    # the other two: the recorded post-state is compared exactly.  Two of the
    # seven steps move it, and that is what makes the delivered route's
    # "storage is byte-identical" assertion non-vacuous.
    expect_store = dict(entry["expect_storage_after"])
    if store_after != expect_store:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the storage is %r after the step, not the recorded %r"
            % (name, store_after, expect_store),
        )
    if store_before == store_after and store_after != expect_store:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the storage stood still at %r, which cannot satisfy the recorded "
            "post-state %r" % (name, store_after, expect_store),
        )
    if entry.get("grants_into_storage") and store_before == store_after:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: the granting step is recorded as writing the storage, but the "
            "storage did not move" % name,
        )

    # The non-granting steps' leaf diff is EXACTLY the cursor and the instant.
    # This is the fixture's cleanest claim, so it is asserted per step and not
    # merely reported.
    if not entry["grant_landing_place_expected"]:
        allowed = {
            "/privateState/%s" % cursor_key,
            "/privateState/%s" % stamp_key,
        }
        if set(changed_paths) != allowed:
            raise CaptureError(
                EXIT_REQUEST,
                "%s: these leaves moved %r, and exactly %r may -- this is the "
                "demonstration that this arm grants nothing at all"
                % (name, changed_paths, sorted(allowed)),
            )

    resources_before = stored_resources(before)
    resources_after = stored_resources(after)
    moved = sorted(
        slot
        for slot in RESOURCE_SLOTS
        if not typed_equal(resources_before[slot], resources_after[slot])
    )
    if moved:
        raise CaptureError(
            EXIT_REQUEST,
            "%s: stored resources %r moved, and the contract is that no reward "
            "branch charges or credits anything" % (name, moved),
        )

    facts: Dict[str, Any] = {
        "name": name,
        "step_number": int(entry["step"]),
        "command": command,
        "arm": str(entry["arm"]),
        "args_sent": list(entry["args"]),
        "argument_count": int(entry["argument_count"]),
        "arity_selects_the_arm": (
            "command.py:346 tests len(args) > 4, so the CLIENT's argument count "
            "picks between granting and not granting" if command == WEEKLY_COMMAND
            else "not applicable: the daily branch is not arity-selected"
        ),
        "cursor_key": cursor_key,
        "cursor_before": cursor_before,
        "cursor_after": cursor_after,
        # BOTH cursors, not only the addressed one.  Each step advances exactly
        # one of them, so the *other* must be byte-identical across the step --
        # and recording both is what lets the sequence-linkage check below be one
        # uniform comparison instead of two special cases.  An earlier version
        # chained the addressed cursor of every step against its predecessor's,
        # which compared the weekly ladder against the daily one and reported a
        # break where there was none.
        "both_cursors": {
            key: {
                "before": read_at(before, ("privateState", key)),
                "after": read_at(after, ("privateState", key)),
            }
            for key in rewards_envelope.CURSORS
        },
        "cursor_recomputed": recomputed,
        "cursor_moved_backwards": int(cursor_after) < int(cursor_before),
        "instant_key": stamp_key,
        "instant_before": stamp_before,
        "instant_after_shape": type(stamp_after).__name__,
        "instant_is_volatile": True,
        "instant_compared_by": (
            "shape only, never by value: the branch stamps the wall clock"
        ),
        "changed_leaf_paths": changed_paths,
        "changed_leaf_count": len(changed_paths),
        "leaf_diff": diff_payload(diff),
        "only_the_cursor_and_instant_moved": not entry["grant_landing_place_expected"],
        "state_sha256_before": canonical_state_sha(before),
        "state_sha256_after": canonical_state_sha(after),
        "placed_rows_before": len(rows_before),
        "placed_rows_after": len(rows_after),
        "placed_rows_recorded": int(entry["placed_rows_before"]),
        "unit_list_length_before": len(units_before),
        "unit_list_length_after": len(units_after),
        "unit_list_byte_identical": typed_equal(units_before, units_after),
        "storage_before": store_before,
        "storage_after": store_after,
        "storage_byte_identical": store_before == store_after,
        "resource_slot_count": RESOURCE_COUNT,
        "resources_before": resources_before,
        "resources_after": resources_after,
        "resources_moved": moved,
        "resources_comparison": (
            "all %d stored resource slots compared; moved: NONE" % RESOURCE_COUNT
        ),
        "status": status,
        "parity_with_delivered_endpoint": bool(entry.get("parity", False)),
        "note": str(entry["note"]),
    }
    if entry.get("parity_note"):
        facts["parity_note"] = str(entry["parity_note"])
    if entry.get("divergence"):
        facts["divergence"] = str(entry["divergence"])
    if entry.get("modern_refuses"):
        facts["delivered_endpoint_refusal"] = str(entry["modern_refuses"])
    if "modern_derives_after" in entry:
        facts["modern_derives_after"] = int(entry["modern_derives_after"])
        facts["modern_differs_from_oracle"] = True
    if entry.get("parity"):
        facts["modern_derives_after"] = int(entry["expect_after"])
        facts["modern_differs_from_oracle"] = False
    if entry.get("grants_a_row"):
        facts["placed_index_sent"] = int(entry["placed_index_sent"])
        facts["placed_item_sent"] = int(entry["placed_item_sent"])
        facts["placed_cell_sent"] = list(entry["placed_cell_sent"])
        facts["placed_player_sent"] = int(entry["placed_player_sent"])
        facts["grant_is_client_sent"] = True
    if entry.get("successor_unaddressable"):
        facts["successor_unaddressable"] = True
        facts["successor_position"] = int(entry["expect_after"])
        facts["weekly_schedule_cardinality"] = len(
            committed_schedules()[rewards_envelope.WEEKLY_SCHEDULE_KEY]
        )
        facts["note_on_the_gap"] = rewards_envelope.NO_CURSOR_SELECTION
    if "next_id_sent" in entry:
        facts["next_id_sent"] = int(entry["next_id_sent"])
        facts["next_id_sent_is_the_recorded_cursor"] = bool(
            entry["next_id_sent_is_the_recorded_cursor"]
        )
    if entry.get("moved_backwards"):
        facts["moved_backwards"] = True
        facts["backwards_move_cause"] = (
            "the client sent next id %d, the branch computed %d, and 'if next_id > "
            "%d: next_id = %d' overwrote it with %d -- so a LARGER client value "
            "moves the recorded cursor DOWN"
            % (
                int(entry["next_id_sent"]),
                int(entry["next_id_sent"]) + 1,
                rewards_envelope.DAILY_BOUND_LITERAL,
                rewards_envelope.DAILY_WRAP_TARGET,
                rewards_envelope.DAILY_WRAP_TARGET,
            )
        )
    return facts


def stdout_offset(stdout_path: Path) -> int:
    """The server's stdout size, taken immediately before a request.

    This capture runs ONE server for the whole sequence rather than one per
    transaction, so the stdout file is shared by all seven steps.  A per-step
    server would need no offset; reusing a shared server with that helper would
    report the previous steps' lines as this step's evidence.
    """
    try:
        return stdout_path.stat().st_size
    except OSError:
        return 0


def printed_branch_lines(stdout_path: Path, command: str, since: int = 0) -> List[str]:
    """The printed lines **this** request emitted, in order.

    ``since`` is the stdout size taken before the request, so a step's evidence
    is its own output and never an ancestor's.
    """
    wanted = "COMMAND: %s(" % command
    found: List[str] = []
    try:
        with stdout_path.open("rb") as handle:
            handle.seek(since)
            raw = handle.read()
    except OSError:
        return found
    for line in raw.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if wanted in stripped:
            found.append(stripped)
    return found


def printed_message_template(entry: Dict[str, Any]) -> str:
    """The UNINTERPOLATED text the preserved branch's ``print`` appends.

    Kept separate from :func:`expected_printed_message` because the two must not be
    conflated.  This capture's first draft asked ``"%s" in expected_message`` to
    decide whether a message names an item -- but ``expected_printed_message``
    *substitutes* the committed name, so its output can never contain a ``%s`` and
    the recorded field was ``null`` for all seven steps.  The field existed, was
    checked by the parity suite, and was structurally incapable of carrying
    evidence: a check that cannot fail is not a check.  Deciding from the template
    makes the two functions differ in exactly one thing, which is the substitution.

    Transcribed from the two branches' ``print`` calls (``command.py:355``,
    ``:456``, ``:459``); no other part of the preserved server prints these.
    """
    command = str(entry["command"])
    arm = str(entry["arm"])
    if command == WEEKLY_COMMAND:
        return PRINTED_WEEKLY_SHORT if arm == WEEKLY_SHORT_ARM else PRINTED_WEEKLY_ITEM
    if arm == DAILY_GRANTING_ARM:
        return PRINTED_DAILY_GRANTED
    return PRINTED_DAILY_RESOURCES


def printed_message_item(entry: Dict[str, Any]) -> Optional[Any]:
    """The item id this step's message NAMES, or ``None`` when it names no item.

    The two placeholders are what select a name, so the item is taken from the same
    branch of the same decision that produced the template above -- never inferred
    from the rendered text.
    """
    command = str(entry["command"])
    arm = str(entry["arm"])
    if command == WEEKLY_COMMAND:
        if arm == WEEKLY_SHORT_ARM:
            return None
        return entry["unit_item_sent"]
    if arm == DAILY_GRANTING_ARM:
        return entry["storage_item_sent"]
    return None


def expected_printed_message(entry: Dict[str, Any]) -> str:
    """The exact text the preserved branch's ``print`` appends to its line.

    Derived from the branch and from committed content, never transcribed as a
    whole.  The two messages that name an item are built from
    ``get_attribute_from_item_id(id, "name")``, so a content change fails the
    capture instead of being baked into a literal; the two that name no item are
    the branches' own fixed strings.
    """
    template = printed_message_template(entry)
    item = printed_message_item(entry)
    if item is None:
        return template
    return template % committed_item_name(item)


def printed_tail(line: str, expected: str) -> str:
    """The ``-> <text>`` tail of a printed branch line, or ``""``."""
    if " -> " not in line:
        return ""
    tail = line.rsplit(" -> ", 1)[1].strip()
    return tail if tail == expected else ""


def protected_fixture_snapshot() -> Dict[str, Dict[str, object]]:
    """Per-fixture file count and combined digest, for the containment check."""
    out: Dict[str, Dict[str, object]] = {}
    for name in PROTECTED_FIXTURES:
        directory = REPO_ROOT / "tests" / "fixtures" / name
        if not directory.is_dir():
            out[name] = {"present": False, "files": 0, "combined": ""}
            continue
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        out[name] = {
            "present": True,
            "files": len(files),
            "combined": canonical_digest(
                [
                    (
                        str(path.relative_to(directory)).replace("\\", "/"),
                        committed_digest(path.read_bytes()),
                    )
                    for path in files
                ]
            ),
        }
    return out


def publish(staging: Path, out_dir: Path) -> None:
    """Replace this capture's own outputs, preserving the hand-authored README.

    The same scope as ``capture_unit_xp_fixture.py``: ``steps/`` and
    ``capture-manifest.json``, and nothing else.  A wholesale directory replace --
    which is what this function did first, by renaming the old directory aside and
    renaming the staging directory into place -- silently deletes ``README.md`` on
    every rerun, and that README carries the measured inventory figures, the
    containment table, and the claim limits, none of which any run can regenerate.
    This line lost its own README to exactly that, and four parity checks then
    failed on a missing file rather than on anything about the fixture.

    The staging directory is OUTSIDE the working tree and published only after
    every check has passed, so a failed run writes nothing into the repository.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("steps", "capture-manifest.json"):
        target = out_dir / name
        if target.is_dir():
            shutil.rmtree(str(target))
        elif target.exists():
            target.unlink()
    shutil.copytree(str(staging / "steps"), str(out_dir / "steps"))
    shutil.copy2(str(staging / "capture-manifest.json"), str(out_dir / "capture-manifest.json"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="fixture output directory (default: %(default)s)",
    )
    args_ns = parser.parse_args(argv)
    out_dir: Path = args_ns.out

    if not SEED.is_file():
        print("capture: missing village seed save: %s" % SEED, file=sys.stderr)
        return EXIT_ENVIRONMENT
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    if not isinstance(seed, dict):
        print("capture: village seed is not a JSON object: %s" % SEED, file=sys.stderr)
        return EXIT_ENVIRONMENT

    # Assert the committed corpus really carries what this fixture assumes,
    # before a single server starts.
    census = verify_seed(seed)
    schedules = committed_schedules()
    derived_weekly_bound = rewards_envelope.weekly_bound(
        schedules[rewards_envelope.WEEKLY_SCHEDULE_KEY]
    )
    weekly_cardinality = len(schedules[rewards_envelope.WEEKLY_SCHEDULE_KEY])
    daily_cardinality = len(schedules[rewards_envelope.DAILY_SCHEDULE_KEY])
    print(
        "capture: seed=%s (%d placed rows, weekly cursor %d, daily cursor %d, %d "
        "resource slots)"
        % (
            SEED.name,
            census["placed_rows"],
            census["weekly_cursor"],
            census["daily_cursor"],
            census["resource_slot_count"],
        )
    )
    print(
        "capture: weekly bound DERIVED from the committed schedule = %d while the "
        "schedule holds %d entries; daily bound is the preserved literal %d while "
        "the unread schedule holds %d entries"
        % (
            derived_weekly_bound,
            weekly_cardinality,
            rewards_envelope.DAILY_BOUND_LITERAL,
            daily_cardinality,
        )
    )

    if not port_is_free(LEGACY_HOST, LEGACY_PORT):
        print(
            "capture: port conflict: %s:%d is already in use; refusing to start "
            "the legacy server" % (LEGACY_HOST, LEGACY_PORT),
            file=sys.stderr,
        )
        return EXIT_PORT_BUSY

    pre_groups = containment_snapshot()
    pre_combined = snapshot_combined(pre_groups)
    pre_fixtures = protected_fixture_snapshot()
    pre_seed_sha = committed_digest(SEED.read_bytes())

    staging = Path(tempfile.mkdtemp(prefix="compat-rewards-capture-staging-"))
    summaries: List[Dict[str, Any]] = []
    transcript: List[Dict[str, Any]] = []
    disposables: List[Path] = []

    print(
        "capture: %d transactions, ONE disposable and ONE server for the whole "
        "interleaved sequence (sessions.load_saves() caches the corpus in memory "
        "at import, so a restored seed file is not enough -- and every step must "
        "run against its predecessor's recorded state)"
        % (len(TRANSACTIONS),)
    )

    try:
        disposable: Optional[Path] = None
        process = None
        stdout_path = None
        try:
            disposable, pid, seed_sha_raw = build_disposable(
                Path(tempfile.gettempdir()), SEED
            )
            seed_sha = committed_digest(SEED.read_bytes())
            disposables.append(disposable)
            saves_dir = disposable / "saves"
            seed_group = save_group_record(saves_dir)
            if seed_sha != pre_seed_sha:
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "capture: the committed seed's digest %r differs from the "
                    "recorded %r (both digests are over the committed blob form)"
                    % (seed_sha, pre_seed_sha),
                )
            if seed_sha_raw != sha256_file(seed_target_of(disposable, pid)):
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "capture: the helper's verbatim copy digest %r differs from the "
                    "copy it made at %r -- the seed was not copied verbatim"
                    % (seed_sha_raw, pid),
                )

            process, stdout_path, stderr_path = start_server(
                disposable, {"PYTHONUNBUFFERED": "1"}
            )
            if not wait_ready(process, LEGACY_HOST, LEGACY_PORT):
                raise CaptureError(
                    EXIT_SERVER,
                    "capture: legacy server did not become ready (exit=%s)\n"
                    "--- stdout ---\n%s\n--- stderr ---\n%s"
                    % (
                        process.poll(),
                        read_tail(stdout_path),
                        read_tail(stderr_path),
                    ),
                )

            save_path = saves_dir / ("%s.save.json" % pid)
            startup_group = save_group_record(saves_dir)
            if startup_group["sha256"] != seed_group["sha256"]:
                raise CaptureError(
                    EXIT_ENVIRONMENT,
                    "capture: the corpus changed during server startup, so the "
                    "server is not reading the committed seed",
                )

            # --- login, exactly as a logged-in Flash client would --------
            login_form = {"USERID": pid, "GAMEVERSION": GAME_VERSION}
            login_result = http_request(
                LEGACY_PORT, "POST", "/", form=dict(login_form), timeout=30.0
            )
            if login_result["status"] != 302:
                raise CaptureError(
                    EXIT_REQUEST,
                    "capture: login expected HTTP 302, got %r"
                    % (login_result["status"],),
                )
            cookie = extract_session_cookie(login_result)
            login_body = login_result.pop("body")
            after_login = json.loads(save_path.read_text(encoding="utf-8"))
            if canonical_state_sha(after_login) != canonical_state_sha(seed):
                raise CaptureError(
                    EXIT_REQUEST,
                    "capture: the login step changed the corpus, so it is not a "
                    "neutral session step",
                )

            login_request_record = {
                "captured_at_utc": iso_now(),
                "method": login_result["method"],
                "target": login_result["target"],
                "path": login_result["path"],
                "query": login_result["query"],
                "form": sanitize_form(login_result["form"] or {}),
                "headers_sent": sanitize_headers(login_result["headers_sent"]),
                "scheme": "http",
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "seed_save": SEED.name,
                "note": (
                    "Session fidelity only.  This step leaves the corpus "
                    "byte-identical, which the capture asserts."
                ),
            }
            login_response_record = {
                "status": int(login_result["status"]),
                "reason": login_result["reason"],
                "headers": sanitize_headers(login_result["response_headers"]),
                "body_bytes": len(login_body),
                "body_sha256": committed_digest(login_body),
                "captured_at_utc": iso_now(),
            }
            login_dir = staging / "steps" / "login_post"
            write_json(login_dir / "request.json", login_request_record)
            write_json(login_dir / "before.json", seed)
            write_json(login_dir / "response.meta.json", login_response_record)
            write_bytes(login_dir / "response.body", login_body)
            write_json(login_dir / "after.json", after_login)

            for entry in TRANSACTIONS:
                name = str(entry["name"])
                before = json.loads(save_path.read_text(encoding="utf-8"))
                await_clock_past(
                    read_at(
                        before,
                        ("privateState", STAMP_KEYS[str(entry["command"])]),
                    ),
                    name,
                )
                pairs = command_arguments(entry)
                envelope = build_envelope(pairs)
                verify_envelope(envelope, pairs)
                form = {
                    "USERID": pid,
                    "user_key": USER_KEY,
                    "language": LANGUAGE,
                    "data": data_field(envelope),
                }
                stdout_before = stdout_offset(stdout_path)
                result = http_request(
                    LEGACY_PORT,
                    "POST",
                    DYNAMIC_ROOT + "/command.php",
                    form=dict(form),
                    cookie=cookie,
                    timeout=30.0,
                )
                status = int(result["status"])
                body = result.pop("body")
                after = json.loads(save_path.read_text(encoding="utf-8"))

                facts = verify_transaction(entry, before, after, status)

                if status != 200:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the legacy request answered HTTP %d; the committed "
                        "record says all seven succeed with 200, so the oracle does "
                        "not reproduce" % (name, status),
                    )
                payload = json.loads(body.decode("utf-8"))
                if payload != {"result": "success"}:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: response is not the legacy success result: %r"
                        % (name, payload),
                    )
                facts["response_payload"] = payload

                lines = printed_branch_lines(
                    stdout_path, str(entry["command"]), stdout_before
                )
                facts["stdout_offset_before"] = stdout_before
                facts["stdout_evidence_is_this_request_only"] = True
                facts["printed_branch_lines"] = lines
                if not lines:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the branch printed nothing, so the recorded state "
                        "change has no positive evidence that this branch ran"
                        % name,
                    )
                expected_tail = expected_printed_message(entry)
                tail = printed_tail(lines[-1], expected_tail)
                facts["printed_message"] = tail
                facts["printed_message_claims"] = expected_tail
                facts["printed_message_template"] = printed_message_template(entry)
                named_item = printed_message_item(entry)
                facts["printed_message_names_a_committed_item"] = (
                    "%s" % named_item if named_item is not None else None
                )
                # The name the branch printed must be the COMMITTED name, decided
                # here rather than asserted downstream, so a content change fails
                # the capture instead of being committed into a fixture.
                facts["printed_message_item_name_committed"] = (
                    committed_item_name(named_item) if named_item is not None else None
                )
                if not tail:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "%s: the branch printed %r, not the recorded %r"
                        % (name, lines[-1], expected_tail),
                    )
                # The message is not proof of the effect -- it is printed AFTER
                # the write and says nothing about the value.  On the
                # non-granting arms it claims a reward was won while the leaf diff
                # shows nothing but a cursor and a stamp.
                if not entry["grant_landing_place_expected"]:
                    facts["message_contradicts_the_absence_of_a_grant"] = (
                        "the branch printed %r while its whole-document leaf diff is "
                        "exactly the cursor and the instant" % expected_tail
                    )

                request_record = {
                    "captured_at_utc": iso_now(),
                    "method": result["method"],
                    "target": result["target"],
                    "path": result["path"],
                    "query": result["query"],
                    "form": {
                        key: (
                            sanitize_envelope_data(value)
                            if key == "data"
                            else (REDACTED if key in SENSITIVE_FORM_KEYS else value)
                        )
                        for key, value in (result["form"] or {}).items()
                    },
                    "headers_sent": sanitize_headers(result["headers_sent"]),
                    "scheme": "http",
                    "host": LEGACY_HOST,
                    "port": LEGACY_PORT,
                    "seed_save": SEED.name,
                    "note": (
                        "Exact client request bytes are reconstructed from this "
                        "record; Host is set explicitly, no User-Agent header is "
                        "sent. The batch's argument LIST IS THE CRAFTED, "
                        "CLIENT-SUPPLIED payload under test -- including the "
                        "weekly arm's arity, which is what selects between granting "
                        "and not granting, and the daily arm's next id, which is "
                        "what the cursor is computed from. The branches validate "
                        "none of it, which is the finding, not an oversight. The "
                        "resource vector is NEUTRAL. ts is pinned to a constant so "
                        "this record is byte-stable; legacy parses it and never "
                        "reads it. user_key is redacted; accessToken is the crafted "
                        "empty placeholder, never a token value."
                    ),
                }
                response_record = {
                    "status": status,
                    "reason": result["reason"],
                    "headers": sanitize_headers(result["response_headers"]),
                    "body_bytes": len(body),
                    "body_sha256": committed_digest(body),
                    "captured_at_utc": iso_now(),
                }
                step_dir = staging / "steps" / ("txn_%s" % name)
                write_json(step_dir / "request.json", request_record)
                write_json(step_dir / "before.json", before)
                write_json(step_dir / "response.meta.json", response_record)
                write_bytes(step_dir / "response.body", body)
                write_json(step_dir / "after.json", after)
                write_json(step_dir / "transaction.json", facts)

                summaries.append(facts)
                transcript.append(
                    {
                        "name": name,
                        "step_number": int(entry["step"]),
                        "disposable_pid_read_from_document": pid,
                        "seed_sha256": seed_sha,
                        "printed_branch_lines": lines,
                    }
                )
                print(
                    "capture: %-46s %s%s %s %s -> %s, %d leaf paths, rows %d -> %d, "
                    "%s slots moved, parity=%s"
                    % (
                        name,
                        str(entry["command"]),
                        list(entry["args"]),
                        str(entry["cursor_key"]),
                        int(entry["expect_before"]),
                        int(entry["expect_after"]),
                        len(facts["changed_leaf_paths"]),
                        facts["placed_rows_before"],
                        facts["placed_rows_after"],
                        len(facts["resources_moved"]),
                        facts["parity_with_delivered_endpoint"],
                    )
                )
                for line in lines:
                    print("capture:   printed | %s" % line)
        finally:
            if process is not None:
                server_error = stop_server(process, LEGACY_HOST, LEGACY_PORT)
                if server_error:
                    raise CaptureError(
                        EXIT_SERVER, "capture: %s" % server_error
                    )

        # --- the sequence, asserted step by step ----------------------------
        by_name = {str(item["name"]): item for item in summaries}
        missing = [
            str(entry["name"])
            for entry in TRANSACTIONS
            if str(entry["name"]) not in by_name
        ]
        if missing:
            raise CaptureError(
                EXIT_REQUEST, "recorded transactions are missing: %r" % missing
            )
        # The load-bearing structural check, over the WHOLE DOCUMENT rather than
        # one cursor: each step's recorded "after" must equal its successor's
        # recorded "before" at every path.  The daily cursor alone would not
        # catch a mutation elsewhere in the document between two steps.
        #
        # The cursor check then runs over **both** cursors, uniformly: each step
        # advances one and must leave the other alone, so comparing the addressed
        # cursor to its predecessor's addressed cursor would compare the weekly
        # ladder against the daily one.
        for index in range(1, len(TRANSACTIONS)):
            previous = by_name[str(TRANSACTIONS[index - 1]["name"])]
            current = by_name[str(TRANSACTIONS[index]["name"])]
            if previous["state_sha256_after"] != current["state_sha256_before"]:
                raise CaptureError(
                    EXIT_REQUEST,
                    "step %r did not start from its predecessor's recorded state"
                    % current["name"],
                )
            for key in rewards_envelope.CURSORS:
                expected = previous["both_cursors"][key]["after"]
                observed = current["both_cursors"][key]["before"]
                if observed != expected:
                    raise CaptureError(
                        EXIT_REQUEST,
                        "step %r started from %s %r, not its predecessor's %r"
                        % (current["name"], key, observed, expected),
                    )

        weekly_steps = [
            by_name[str(e["name"])]
            for e in TRANSACTIONS
            if str(e["command"]) == WEEKLY_COMMAND
        ]
        weekly_ladder = [int(item["cursor_after"]) for item in weekly_steps]
        if weekly_ladder != RECORDED_WEEKLY_LADDER:
            raise CaptureError(
                EXIT_REQUEST,
                "the weekly cursor ran %r, not the recorded %r"
                % (weekly_ladder, RECORDED_WEEKLY_LADDER),
            )
        daily_steps = [
            by_name[str(e["name"])]
            for e in TRANSACTIONS
            if str(e["command"]) == DAILY_COMMAND
        ]
        daily_ladder = [int(item["cursor_after"]) for item in daily_steps]
        if daily_ladder != RECORDED_DAILY_LADDER:
            raise CaptureError(
                EXIT_REQUEST,
                "the daily cursor ran %r, not the recorded %r"
                % (daily_ladder, RECORDED_DAILY_LADDER),
            )
        backwards = by_name["daily_oversized_next_id_moves_the_cursor_backwards"]
        if not backwards.get("moved_backwards"):
            raise CaptureError(
                EXIT_REQUEST,
                "the oversized next id did not move the recorded cursor backwards, "
                "so the sharpest divergence in the line does not reproduce: it went "
                "%r -> %r"
                % (backwards["cursor_before"], backwards["cursor_after"]),
            )
        print(
            "capture: cursor ladders MEASURED -- weekly %s (position 4 is one the "
            "three-entry schedule cannot answer), daily %s with the sixth step "
            "moving BACKWARDS from an oversized client next id"
            % (
                " -> ".join(str(v) for v in RECORDED_WEEKLY_LADDER),
                " -> ".join(str(v) for v in RECORDED_DAILY_LADDER),
            )
        )

        # --- the two arms, asserted -----------------------------------------
        short = by_name["weekly_short_arm_grants_nothing"]
        if short["changed_leaf_count"] != 2:
            raise CaptureError(
                EXIT_REQUEST,
                "the short weekly arm moved %d leaf paths, not the recorded two; "
                "the clean demonstration that it grants nothing does not reproduce"
                % (short["changed_leaf_count"],),
            )
        long_arm = by_name["weekly_long_arm_appends_an_absent_unit"]
        if long_arm["placed_rows_after"] != SEED_PLACED_ROWS + 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the long weekly arm placed %d rows, not the recorded %d"
                % (long_arm["placed_rows_after"], SEED_PLACED_ROWS + 1),
            )
        if long_arm["unit_list_length_after"] != SEED_UNIT_LIST_LENGTH + 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the long weekly arm left the unit list at %d, not the recorded "
                "%d -- the appending half of the helper was not exercised"
                % (long_arm["unit_list_length_after"], SEED_UNIT_LIST_LENGTH + 1),
            )
        # The SAME arm and the SAME arity, with a unit id the list already
        # carries.  Both halves of the deduplicating helper are therefore
        # executed, which is what stops the delivered route's "the unit list is
        # byte-identical" clause from being satisfied by a list that simply
        # cannot change.
        dedup_arm = by_name["weekly_long_arm_deduplicates_a_present_unit"]
        if dedup_arm["unit_list_length_after"] != long_arm["unit_list_length_after"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the deduplicating step left the unit list at %d while the "
                "appending step left it at %d; the two halves of the preserved "
                "helper did not reproduce"
                % (
                    dedup_arm["unit_list_length_after"],
                    long_arm["unit_list_length_after"],
                ),
            )
        if dedup_arm["placed_rows_after"] != dedup_arm["placed_rows_before"] + 1:
            raise CaptureError(
                EXIT_REQUEST,
                "the deduplicating step placed %d rows from %d; the row half and "
                "the list half must disagree, not both"
                % (
                    dedup_arm["placed_rows_after"],
                    dedup_arm["placed_rows_before"],
                ),
            )
        grant_arm = by_name["daily_granting_arm_lands_in_storage"]
        if grant_arm["storage_after"] == SEED_STORAGE:
            raise CaptureError(
                EXIT_REQUEST,
                "the daily granting arm left the storage at %r, so the delivered "
                "route's storage clause could never fail and would be vacuous"
                % (grant_arm["storage_after"],),
            )
        if grant_arm["unit_list_length_after"] != dedup_arm["unit_list_length_after"]:
            raise CaptureError(
                EXIT_REQUEST,
                "the daily granting arm moved the unit list from %d to %d while the "
                "storage also moved; the two helpers have different rules"
                % (
                    dedup_arm["unit_list_length_after"],
                    grant_arm["unit_list_length_after"],
                ),
            )
        print(
            "capture: all three grant landing places MEASURED -- %d arguments moved "
            "exactly %d leaf paths and granted nothing; %d arguments placed a row "
            "(%d -> %d); the same %d arguments with a present unit id left the list "
            "at %d; a positive daily item moved the storage %r -> %r"
            % (
                len(WEEKLY_SHORT_ARGS),
                short["changed_leaf_count"],
                len(WEEKLY_LONG_ABSENT_ARGS),
                long_arm["placed_rows_before"],
                long_arm["placed_rows_after"],
                len(WEEKLY_LONG_PRESENT_ARGS),
                dedup_arm["unit_list_length_after"],
                SEED_STORAGE,
                grant_arm["storage_after"],
            )
        )

        # --- the no-price claim, asserted over ALL EIGHT slots --------------
        moved_anywhere = sorted(
            {
                slot
                for item in summaries
                for slot in item["resources_moved"]
            }
        )
        if moved_anywhere:
            raise CaptureError(
                EXIT_REQUEST,
                "stored resources %r moved across the fixture, and the contract is "
                "that no reward branch charges or credits anything"
                % moved_anywhere,
            )
        print(
            "capture: no price MEASURED -- all %d stored resource slots identical "
            "across all %d steps"
            % (RESOURCE_COUNT, len(summaries))
        )

        # --- containment, before publishing anything -----------------------
        post_groups = containment_snapshot()
        post_combined = snapshot_combined(post_groups)
        post_fixtures = protected_fixture_snapshot()
        post_seed_sha = committed_digest(SEED.read_bytes())

        if pre_combined != post_combined:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "working-tree containment changed:\n  before %s\n  after  %s"
                % (pre_combined, post_combined),
            )
        if pre_seed_sha != post_seed_sha:
            raise CaptureError(
                EXIT_CONTAINMENT, "the committed village seed changed during the run"
            )
        changed_fixtures = sorted(
            name_
            for name_ in PROTECTED_FIXTURES
            if pre_fixtures[name_] != post_fixtures[name_]
        )
        if changed_fixtures:
            raise CaptureError(
                EXIT_CONTAINMENT,
                "already-committed fixtures changed during the run: %r"
                % (changed_fixtures,),
            )
        working_tree_saves = REPO_ROOT / "saves"
        if working_tree_saves.exists():
            raise CaptureError(
                EXIT_CONTAINMENT,
                "a working-tree saves/ directory exists; the run wrote outside its "
                "disposable",
            )

        divergences = [
            item for item in summaries if not item["parity_with_delivered_endpoint"]
        ]
        manifest = {
            "schema": SCHEMA,
            "captured_at_utc": iso_now(),
            "purpose": (
                "Executed-legacy evidence for the two reward branches: "
                "weekly_reward (command.py:345-363) and win_daily_bonus "
                "(444-463). It records what the ORACLE does, including the three "
                "behaviours this capability deliberately does NOT reproduce: the "
                "client-sent granted item, the client-sent next cursor, and the "
                "client-arity-selected arm."
            ),
            "invocation": "python -B apps/compat-api/capture_rewards_fixture.py",
            "interpreter": "CPython %d.%d (pinned)" % sys.version_info[:2],
            "server": {
                "host": LEGACY_HOST,
                "port": LEGACY_PORT,
                "process": "python -B server.py inside the disposable",
                "starts": 1,
                "one_server_for_the_whole_sequence": True,
                "one_server_reason": (
                    "sessions.load_saves() caches the corpus in a module global at "
                    "import, so a running server never re-reads the seed file. "
                    "Restoring the seed between steps on one server leaves the in "
                    "memory corpus already mutated and silently produces a "
                    "different result."
                ),
                "one_per_transaction_reason_rejected": (
                    "One server per TRANSACTION was rejected rather than merely "
                    "avoided: the recorded cursors are the point of this fixture, "
                    "and the oversized next-id probe's recorded before (4) is only "
                    "reachable if the previous step really advanced the cursor. The "
                    "capture asserts whole-document linkage for all six links."
                ),
                "sequence": SEQUENCE_NOTE,
                "sequence_linkage_asserted": (
                    "every step's whole recorded state digest equals its "
                    "predecessor's, for all six links, plus both cursor ladders "
                    "weekly %s and daily %s"
                    % (RECORDED_WEEKLY_LADDER, RECORDED_DAILY_LADDER)
                ),
                "debug": False,
                "debug_note": (
                    "server.py runs app.run(..., debug=False). Every recorded step "
                    "answers HTTP 200, so no framework error page is committed."
                ),
                "env_extra": {"PYTHONUNBUFFERED": "1"},
                "env_extra_note": (
                    "Set for THIS capture's child processes only, via a defaulted "
                    "parameter on start_server. child_environment() is untouched, so "
                    "no existing capture's log changes. The printed lines are the "
                    "evidence that each branch ran, and block buffering would lose "
                    "them when the harness reaps the child."
                ),
            },
            "seed": {
                "path": str(SEED.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": pre_seed_sha,
                "pid_read_from_document": SEED_PID,
                "why_this_one": census["why_this_one"],
                "census": census,
                "no_cursor_fabricated": (
                    "The seed's two cursors and two instants are reproduced "
                    "verbatim in every transaction's before state, and every step's "
                    "before state is asserted equal to its predecessor's after "
                    "state. Nothing is written into the seed by this capture; its "
                    "digest is asserted before and after the run."
                ),
            },
            "batch_shape": {
                "commands": list(COMMANDS),
                "arguments_per_command": {
                    # Keyed by the LEGACY command name, which is what this
                    # capture addresses, and valued from the contract's
                    # action-keyed table through the derived inverse.  Indexing
                    # that table by command name was a plain key error, and it
                    # is the second time this capture has needed the inverse.
                    command: rewards_envelope.ACTION_ARGUMENT_COUNT[
                        rewards_envelope.ACTION_FOR_COMMAND[command]
                    ]
                    for command in COMMANDS
                },
                "weekly_arm_threshold": WEEKLY_ARITY_THRESHOLD,
                "weekly_arm_threshold_source": "command.py:346 (len(args) > 4)",
                "resource_vector": list(NEUTRAL_VECTOR),
                "vector_status": "neutral by construction, every transaction",
                "ts": FIXTURE_TS,
                "ts_note": (
                    "Pinned to a constant, as on the damage and unit-experience "
                    "captures. The dispatcher parses it and never reads it."
                ),
                "arguments": (
                    "CRAFTED AND CLIENT-SUPPLIED. The weekly branch reads zero or "
                    "five and tests only the COUNT; the daily branch reads an item "
                    "and a next id and validates neither. The captured values are "
                    "what makes each divergence observable."
                ),
            },
            "bounds": {
                "weekly": {
                    "derived_bound": derived_weekly_bound,
                    "schedule": rewards_envelope.WEEKLY_SCHEDULE_KEY,
                    "cardinality": weekly_cardinality,
                    "exceeds_cardinality_by": derived_weekly_bound - weekly_cardinality,
                    "source": rewards_envelope.WEEKLY_BOUND_SOURCE,
                    "status": "derived from committed content by the delivered "
                              "envelope, recomputed here and asserted",
                },
                "daily": {
                    "bound": rewards_envelope.DAILY_BOUND_LITERAL,
                    "source": rewards_envelope.DAILY_BOUND_SOURCE,
                    "schedule": rewards_envelope.DAILY_SCHEDULE_KEY,
                    "cardinality": daily_cardinality,
                    "exceeds_cardinality_by": (
                        rewards_envelope.DAILY_BOUND_LITERAL - daily_cardinality
                    ),
                    "rejected_derivation": (
                        rewards_envelope.DAILY_BOUND_REJECTED_DERIVATION
                    ),
                },
                "note": (
                    "The weekly bound is derived from the schedule's LIST-VALUED "
                    "entries and is NOT its entry count, so a bound of %d sits "
                    "beside %d entries. The daily bound is a hardcoded literal whose "
                    "agreement with an unread schedule's entry count is a "
                    "coincidence of the value distribution, not its provenance."
                    % (derived_weekly_bound, weekly_cardinality)
                ),
            },
            "recorded_steps": list(RECORDED_STEPS) + ["login_post"],
            "login_step": (
                "Performed once, before the sequence, and recorded once. Its "
                "neutrality is asserted: the corpus after the login is compared "
                "against the committed seed and must be byte-identical."
            ),
            "transactions": summaries,
            "established": [
                "weekly_reward has TWO ARMS CHOSEN BY THE CLIENT'S ARGUMENT COUNT "
                "(command.py:346 tests len(args) > 4), and BOTH arms stamp and "
                "advance the cursor whether or not anything was granted.",
                "The SHORT weekly arm grants NOTHING: its whole-document leaf diff "
                "is exactly TWO paths, the cursor and the instant, while it prints "
                "'Won resources'. That is the clean demonstration in this line.",
                "The LONG weekly arm places a row: 549 -> 550 placed rows, with the "
                "client-sent item at the client-sent index, cell, and player team, "
                "and every pre-existing row byte-identical.",
                "The long arm also APPENDED to the unit list, 135 -> 136, because the "
                "client-sent item was absent from it, AND the SAME arm with a "
                "client-sent item the list already carried left the list at 136 "
                "while STILL placing a row (550 -> 551). Both halves of the "
                "preserved DEDUPLICATING helper (engine.py:86-89) are therefore "
                "executed rather than cited, and the row half and the list half "
                "are shown to disagree under one request.",
                "win_daily_bonus moves the recorded cursor BACKWARDS when the client "
                "sends an oversized next id: 4 -> 1. This is observable in the "
                "preserved source (command.py:446 computes args[1] + 1 and 451-452 "
                "overwrites anything above the literal 5 with 1) and this fixture "
                "EXECUTES it rather than arguing it.",
                "The granting daily arm calls BOTH grant helpers at once: the "
                "deduplicating unit-list one and the ACCUMULATING storage one. The "
                "seed's storage was empty and became exactly {'1198': 1} while the "
                "unit list stood still, so one grant landed in two places by two "
                "different rules (engine.py:70-75 and 86-89).",
                "No arm charges or credits anything: all EIGHT stored resource "
                "slots are byte-identical in all seven steps.",
                "Neither branch DERIVES what to grant. Both take the item id from "
                "the client, with no content lookup, no bound, and no eligibility "
                "test, and the cursor's only other occurrence is a comment.",
            ],
            "divergences": {
                # A COUNT of diverging transactions, which is 4, beside a count of
                # divergence CLASSES, which is 3.  The two are different numbers
                # because two of the four transactions share the arity class --
                # steps 2 and 3 are the same arm with the same five arguments and
                # differ only in whether the granted id was already in the unit
                # list.  Recording only one of the two counts is how "3
                # divergences" came to read as "three transactions" in this
                # manifest's own key names, which is false; both are named here and
                # the offline parity suite asserts both against the transactions.
                "transaction_count": len(divergences),
                "class_count": len(
                    {str(item.get("divergence")) for item in divergences}
                ),
                "recorded_not_narrowed": True,
                "parity_claimed_for": [
                    str(item["name"])
                    for item in summaries
                    if item["parity_with_delivered_endpoint"]
                ],
                "transactions": [
                    {
                        "name": item["name"],
                        "command": item["command"],
                        "args_sent": item["args_sent"],
                        "oracle_cursor_after": item["cursor_after"],
                        "modern_derives_after": item.get("modern_derives_after"),
                        "divergence": item.get("divergence"),
                        "delivered_endpoint_refusal": item.get(
                            "delivered_endpoint_refusal"
                        ),
                    }
                    for item in divergences
                ],
                "divergence_classes": {
                    "client_supplied_item": (
                        "Both branches take the granted item from the client, and "
                        "the weekly branch takes the index, cell, and player team "
                        "with it. The delivered route accepts none of them and "
                        "grants nothing."
                    ),
                    "client_supplied_next_id": (
                        "The daily branch advances a client-sent cursor and then "
                        "overwrites anything above the literal 5 with 1, so a "
                        "larger client value moves the recorded cursor backwards. "
                        "Recorded SEPARATELY from the item divergence because this "
                        "one is observable in the preserved source rather than only "
                        "in an executed record. The delivered route derives the "
                        "successor from the recorded cursor instead."
                    ),
                    "arity_selects_the_arm": (
                        "The weekly branch selects between granting and not "
                        "granting on the client's argument count, so the same "
                        "command with five arguments places a row and with four "
                        "does not. The delivered route has NO arm: it always sends "
                        "the short, non-granting argument list and reports each "
                        "arm's recorded effect instead."
                    ),
                },
                "why_not_narrowed": (
                    "Reproducing any of these would require deriving what to grant, "
                    "and nothing in the preserved server derives it. The weekly "
                    "schedule's only consumer returns an int (its length), the "
                    "letters 'g' and 'c' are decoded nowhere, and both cursors have "
                    "zero readers. So the coherent modern contract is a cursor "
                    "transition with no grant, and every difference from the oracle "
                    "is recorded rather than reproduced."
                ),
            },
            "derived_provisional": [
                "That villages/Neutral.json is the seed. Recorded so a rerun "
                "reproduces the committed bytes; seven committed documents carry a "
                "weekly cursor above 0, and this one's successor lands on the "
                "unaddressable position 4, so the choice is forced by what the "
                "fixture must demonstrate rather than preferred.",
                "That all seven steps are ONE interleaved sequence rather than seven "
                "independent transactions. It is settled independently by the "
                "oversized probe: it is the SIXTH step and its recorded before is 4, "
                "which is only reachable if the granting daily step before it "
                "advanced the recorded cursor from 3, and its recorded after is 1 "
                "rather than the successor. The capture asserts all six links over "
                "the whole document and over BOTH cursors.",
                "That a modern capability should derive the successor from the "
                "recorded cursor at all. No committed rule states it; it is the "
                "coherent reading of a cursor nobody reads, and it is recorded as a "
                "decision rather than a reproduction.",
            ],
            "not_claimed": [
                "Anything about WHAT WAS GRANTED. The grant is client-sent in both "
                "branches: the non-granting arms grant nothing at all, and the "
                "granting arms place or store whatever integer the client sent. No "
                "committed rule says which item, and the one schedule with a "
                "consumer uses it for its LENGTH only. The captured item ids "
                "happen to be ones the weekly schedule names, which is what makes "
                "the list append observable -- that is NOT evidence the schedule "
                "selects them, and the branch never reads it.",
                "That the daily bound is content-derived. It is a hardcoded literal "
                "at command.py:451 in a branch whose only reader of that schedule "
                "does not exist, and the rejected derivation is retained rather "
                "than dropped.",
                "That a type letter names a resource. Six independent searches "
                "across all eleven preserved modules return zero, so reading 'g' as "
                "gold or 'c' as cash would be an invention rather than a "
                "reproduction. Nothing here maps a letter onto a slot.",
                "That the modern endpoint reproduces the oracle's cursor value. It "
                "deliberately does not where the two differ, and every step records "
                "the oracle value, the derived value, and whether they agree.",
                "Anything about what the real Flash client sent. The client was "
                "never executed: every payload here is crafted, and the weekly arm's "
                "arity in particular was chosen by this capture.",
                "Any eligibility, cooldown, window, or already-claimed rule. The "
                "stamped instant has no reader anywhere in the preserved server, so "
                "there is nothing to reproduce.",
                "That the two cursors are read by anything. Each is read only by the "
                "expression that overwrites it.",
            ],
            "time_dependent_fields": {
                "state_documents": (
                    "THE WHOLE-DOCUMENT STATE FILES ARE NECESSARILY VOLATILE, AND "
                    "MEASURED AS SUCH. Both preserved branches write the wall clock "
                    "UNCONDITIONALLY (command.py:361 and command.py:454), so every "
                    "step's before.json and after.json carries a different instant "
                    "on every run. This was measured, not assumed: two consecutive "
                    "runs were compared file by file with the line endings "
                    "normalised, and 37 of the 48 files differed -- every state "
                    "document, every request record, every transaction record and "
                    "this manifest. An earlier draft of this capture claimed the "
                    "opposite, that only the six response Date headers moved; that "
                    "claim was copied from a capture whose branch does not stamp a "
                    "wall clock, and it was false here. CONSEQUENCE FOR VERIFICATION: "
                    "a test must RECOMPUTE each transaction's state digest from the "
                    "committed bytes rather than compare it to a fixed constant, "
                    "which is exactly what this line's parity test does. The capture "
                    "compensates for the same-second collision by waiting for the "
                    "wall clock to move past the instant each step is about to "
                    "overwrite, so the stamp change is observed rather than raced "
                    "for."
                ),
                "request_captured_at_utc": (
                    "Recorded per step and necessarily volatile, for the ordinary "
                    "reason that a record says when it was taken."
                ),
                "captured_at_utc": "Same, in this manifest.",
                "response Date header": (
                    "Each step's response.meta.json records the server's own Date "
                    "header verbatim, so it moves with the wall clock. Nothing "
                    "redacts it, because redacting a header the oracle sent would be "
                    "narrowing the record."
                ),
                "instant_stamped_by_the_oracle": (
                    "The branch's own instant field moves every step, because the "
                    "branch stamps the wall clock. That is a STATE difference, not a "
                    "record difference: it is recorded in each transaction's "
                    "`instant_before` and `instant_is_volatile`, and the executed "
                    "value is compared by shape only."
                ),
                "ts": "Pinned to a constant, so not volatile.",
            },
            "containment": {
                "combined_before": pre_combined,
                "combined_after": post_combined,
                "identical": pre_combined == post_combined,
                "groups": sorted(pre_groups),
                "seed_sha256_before": pre_seed_sha,
                "seed_sha256_after": post_seed_sha,
                "working_tree_saves_absent": True,
                "protected_fixtures": sorted(PROTECTED_FIXTURES),
                "protected_fixtures_unchanged": True,
            },
            "cleanup": {
                "disposables": len(disposables),
                "note": (
                    "Each disposable is removed by the harness's own finally block; "
                    "the fixture is staged OUTSIDE the working tree and published "
                    "only after every check passed, so a failed run writes nothing "
                    "into the repository."
                ),
            },
            "transcript": transcript,
            "exit_code": EXIT_OK,
        }
        write_json(staging / "capture-manifest.json", manifest)
        publish(staging, out_dir)
        print("capture: fixture published to %s" % out_dir)
        print("capture: containment %s before and after (identical)" % pre_combined[:16])
        return EXIT_OK
    except CaptureError as error:
        print("capture: %s" % error, file=sys.stderr)
        return error.exit_code
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        for path in disposables:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())