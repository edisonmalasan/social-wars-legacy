#!/usr/bin/env python3
"""The combat-authority vertical slice: resolve an identity, report both gates, destroy nothing.

**The fourth action on the v1 boundary, and the first that writes nothing at all.**
``collect`` derives a payout, ``complete_collection`` derives a debit and
``buy_magic``/``use_magic`` derive a bounded counter.  This one derives
**nothing** — not a resource, not a counter, not a count of destroyed rows — and
that absence is the finding rather than an omission (design D2).

The preserved branch it replaces is ``end_attack`` (``command.py:808-885``), and
its entire stored effect is **one call**:

.. code-block:: python

    for unit in attacker_units:                            # :866
        lost = max(0, unit[2] - unit[3])  # A - B         # :868
        if lost > 0:
            map_lose_item(map, privateState, unit[0], lost)  # :872

``unit`` is a list the **client** sent, and ``lost`` is a subtraction of two
numbers the client sent — the branch's own comment at ``:867`` labels them only
``A`` and ``B`` and names neither.  So both the item id and the number of rows
destroyed are client-dictated in full, and ``map_lose_item``
(``engine.py:215-228``) turns each destroyed row into **two** pieces of
authoritative state: the row itself disappears, and ``push_dead_unit``
(``engine.py:149-170``) increments ``privateState["deadHeroes"]`` behind two
gates.

## No derivation, and the reason is measured rather than preferred

Six independent measurements converge on "there is nothing here to derive" and
they are stated in ``design.md`` D2.  The two that decide it:

* **The only quantity the branch computes** is ``max(0, A - B)`` over two client
  numbers.
* **No committed column names this branch's outcome.**  The nine committed combat
  fields in :data:`ZERO_CONSUMER_COMBAT_FIELDS` measure **0** legacy occurrences
  in every view over the preserved modules — and ``attack``, the only one that
  appears at all, has a **whole-word** count of ``0`` and all twelve of its
  whole-file occurrences sit inside longer identifiers
  (``end_attack``, ``attacker``, ``attacker_units``, ``flash_reload_attack``).

Three alternatives were each **rejected against a measurement**:

``destroy exactly one row``
    that ``1`` is a property of ``combat_payload``'s own construction, and the
    same Compatibility API route destroyed **two** rows for the client figure
    ``A=3, B=1`` at committed fixture step 7.  Promoting a fixture's convenience
    into server authority is the same class of error as promoting a test's input
    into a schema.

``destroy every eligible row``
    the client still chooses *which* unit, the server still cannot say how many,
    and ``map_lose_item``'s bound is realised from the save, so a client naming
    a unit with no matching row gets a **silent success** and no destruction at
    all.  That is the client-dictated destruction wearing a different spelling.

``derive the count from committed attack minus committed defense``
    neither field is read by anything.

## The two gates are reported, never enforced (design D3)

``push_dead_unit`` gates the ledger behind exactly two conditions and only two:

======================================  ==========================================
gate                                    preserved behaviour
======================================  ==========================================
the row's recorded player team is ``1``  ``engine.py:151`` — **exactly** 1, not
                                        any truthy value
committed ``resurrectable`` is over 0   ``engine.py:159,162`` — an **absent**
                                        key returns ``False`` and is never read
                                        as ``0``
======================================  ==========================================

Both are **resolved and reported, and neither is acted on**.  The gates belong to
``godot-unit-behaviors``, which owns the ledger; this slice states what they
would have said and destroys nothing for either answer.  Reporting rather than
enforcing is the decision and it is v0's established posture carried forward:
``combat_envelope.TEAM_ASYMMETRY`` already records the asymmetry without
exercising or refusing it.

**Absence is reported as absence.**  An identity with no row on the recorded map
reports ``row_present: false`` and carries no team, and the operation succeeds.
That is measured-necessary rather than a convenience:
``tests/saves/fresh-player.json`` places **40** rows and **0** unit rows, so
refusing on the absence would leave the committed corpus with no exercisable
success and the live phase with nothing to drive.

**The team asymmetry is recorded and not reconciled.**  ``map_lose_item``
accepts any **truthy** team (``engine.py:221``) while ``push_dead_unit``
requires **exactly** ``1`` (``engine.py:151``), so on a team-3 row the preserved
server destroys the row and credits nothing.  Why one helper is permissive and
the other exact is **unknown**; every committed unit row is on team 1, so the
corpus exercises nothing.

## This module has no arithmetic and no mutator, and both absences are structural

There is no ``repository.write`` call, no ``set_*`` accessor used, and no
rollback — because there is nothing to roll back.  Every refusal therefore
resolves **before** :meth:`SaveDocument.snapshot` is reached, so a refused
request leaves the whole persisted document byte-identical (design D4), and a
successful one leaves it byte-identical too.

The two absences are guards rather than comments.  ``tests/test_combat.py``
walks this file's AST and fails on any ``Mult``/``Div``/``FloorDiv``/``Mod``/
``Pow``/``LShift``/``BitAnd`` node — so "this domain derives nothing" is
mechanically true rather than argued — and it pins the module's whole function
inventory, so an invented ``destruction_count_for`` or ``honor_payout`` cannot
be added without a reviewer reading a failing suite.  Both are proven to fire
by injection.

**The no-arithmetic rule is also why this module formats no string with
``%``**: the percent operator is one of the seven banned nodes, so every message
here is an f-string.  That is a consequence worth stating, because the first
version of the sibling slices used ``%`` throughout and this one cannot.

## The post-execution proof (design D6), five ordered checks

1. ``identity_resolved_to_reported_row`` — the committed block the response
   carries equals a **fresh** read of the committed unit row, so a carried-forward
   value cannot masquerade as a resolved one.
2. ``reported_gates_match_content_and_state`` — both reported gates equal a
   **fresh** read of committed content and of recorded state.
3. ``no_leaf_path_changed`` — the **leaf census**: every leaf path whose value
   differs between the two documents, which is empty here and **names which
   leaves moved** if it ever is not.
4. ``whole_document_unchanged`` — the two documents serialise to the **same
   bytes**, every key included.
5. ``resources_unchanged`` — all seven stored resources v1 knows about.

**The order is load-bearing and it is the reverse of line 3's.**  The leaf
census runs *before* the whole-document comparison, so a destruction is reported
as *which leaves moved* rather than only as a document diff; line 3's slice had
the opposite order available and recorded why the ordering matters.

Checks 1 and 2 are the **specification** half: v1 is the only implementation
writing this save on this path, so comparing v1's report against v1's own
reading could not fail for an interesting reason, and it is presented as such
rather than dressed as parity with the preserved branch, which is not executed
here.  Checks 3 and 4 are the **falsifiable** half and they are the strongest
such instrument in this project: every alternative this design rejected moves at
least one leaf through ``map_lose_item``, which either deletes a row from
``maps[0].items`` or increments ``privateState["deadHeroes"]``, and **both** are
inside the comparison's scope.  Any destruction of **any** size at **any**
identity fails them.  Line 1's proof could be satisfied by a wrong amount, line
2's by a wrong prize, line 3's by a single debited resource; this one cannot be
satisfied by a wrong destruction, because it does not admit one.

## No rollback, and what the two ``None`` dereferences are here instead

``end_attack`` dereferences ``victim`` at ``:874`` and ``attacker_units`` at
``:866`` without a ``None`` check.  Both shapes raise, and the raise **discards
the whole save** rather than partially applying it, because ``command.py:30,32``
dispatches the batch before saving.

Their status is a **split**, stated precisely:

* **established** — both are reachable, and both were **executed**: committed
  fixture steps ``resolve_absent_attacker_units`` and ``resolve_absent_victim``
  answer HTTP **500** with the persisted document byte-identical;
* **unknown** — whether a *real client* ever sent either shape, because the Flash
  client was never executed and every fixture payload is crafted.

Neither raise is **representable** in v1: the request carries one integer and no
list and no victim object, so the shapes that cause them have no request
encoding (design D4).  A request that carries the branch's own wire shape
instead is refused by name rather than dereferenced — see
:data:`server_v1_intent.DESTRUCTION_KEYS`.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

from server_v1_content import CommittedContent, ContentError
from server_v1_intent import Intent
from server_v1_outcomes import (
    PRESERVED_COMBAT_BEHAVIOUR,
    CombatSuccess,
    Outcome,
)
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES, RepositoryError, SaveRepository

#: The route's own action name, in v1's vocabulary and never ``command.py``'s.
#: Naming a v1 route after a legacy branch would make v1's vocabulary a subset of
#: the 63 branch names, which is the inheritance the boundary exists to stop.
ACTION = "combat"

#: The nine committed combat columns this slice reports **verbatim** and reads no
#: value from.  Every one of them measures **zero** legacy occurrences over the
#: preserved modules; ``attack`` is the only member that appears at all, and its
#: whole-word count is ``0``.
#:
#: They are reported as **strings** because that is how the committed ``items``
#: table stores them, and they are never read as numbers.  The suite pins this
#: table against what the module actually reads, so a member added here has to be
#: a member the module touches.
ZERO_CONSUMER_COMBAT_FIELDS: Tuple[str, ...] = (
    "attack",
    "defense",
    "life",
    "attack_interval",
    "attack_range",
    "best_against",
    "best_against_mult",
    "min_level",
    "syringes",
)

#: The committed columns that identify the resolved row itself, reported beside
#: the combat columns so a client can see *which* row was named.
IDENTITY_COMMITTED_FIELDS: Tuple[str, ...] = ("id", "name", "type")

#: The recorded literal the first gate tests against, as a literal rather than a
#: derivation.  ``engine.py:151`` is ``if item[7] != 1: return False``; nothing in
#: the committed content names a team's value, and the number is never compared
#: against any committed column.
LEDGER_TEAM = 1

#: The two helpers' asymmetry, as **data** so the response can carry it verbatim
#: and a test can assert the same statement is present in the module and on the
#: wire.  It is reported and never reconciled, because no committed row and no
#: legacy line explains why one helper is permissive and the other exact.
TEAM_ASYMMETRY: Dict[str, Any] = {
    "selector_test": (
        "map_lose_item selects a row whose slot 7 is TRUTHY (engine.py:221), so "
        "any recorded team it does not read as 0 is eligible for destruction"
    ),
    "ledger_test": (
        "push_dead_unit requires slot 7 to be exactly 1 (engine.py:151) and "
        "returns False for every other team"
    ),
    "consequence": (
        "on a team-3 row the preserved server destroys the row and credits "
        "nothing to the dead-hero ledger"
    ),
    "reconciled": False,
    "why_not_reconciled": (
        "unknown: no committed row and no legacy line explains the difference, and "
        "every committed unit row in the corpus is on team 1, so the asymmetry is "
        "unexercisable rather than merely unexplained"
    ),
}

#: The two unguarded absent-value dereferences, recorded with the split between
#: what the committed fixture **established** and what remains **unknown**.
#: ``design.md`` D4; ``PRESERVED_COMBAT_BEHAVIOUR["absent_value"]`` carries the
#: same two facts on the wire.
NONE_DEREFERENCE_FACTS: Dict[str, Any] = {
    "representable_in_v1": False,
    "why_not_representable": (
        "a v1 combat request carries one integer identity and no list and no "
        "victim object, so neither shape has a request encoding; a request "
        "carrying the branch's own attacker_units wire shape is refused by name "
        "instead of being dereferenced"
    ),
    "reachability": "established by execution",
    "reachability_evidence": (
        "committed fixture steps resolve_absent_attacker_units and "
        "resolve_absent_victim both execute the corresponding shape against the "
        "real legacy server and both answer HTTP 500 with the persisted document "
        "byte-identical"
    ),
    "a_raise_discards_the_whole_save": True,
    "a_raise_discards_evidence": (
        "command.py:30,32 dispatches the batch before saving, so a raise skips "
        "save_session entirely and the failure mode is a discarded save rather "
        "than a partially applied one"
    ),
    "did_a_real_client_send_either": "unknown",
    "why_unknown": (
        "the Flash client was never executed and every committed fixture payload "
        "is crafted, so the client that would have triggered either raise is not "
        "observable from this repository"
    ),
}

#: ``map_lose_item``'s call sites, as **data**, with the module named at each.
#: ``design.md`` D11 and task 9.12: **two** branches reach **one** helper.
#: ``godot-unit-behaviors`` called the dead-hero ledger's entry "three doors",
#: which counted ``push_dead_unit``'s own two callers and ``map_lose_item``
#: separately.  That archived line is not edited; the discrepancy is recorded here
#: and the suite names the module at each call site rather than inheriting either
#: figure.
MAP_LOSE_ITEM_CALL_SITES: Tuple[Tuple[str, str, str], ...] = (
    ("command.py", "796", "end_quest"),
    ("command.py", "872", "end_attack"),
)

#: The dead-hero ledger's key, reported so a client can see that the whole-document
#: comparison covered it rather than being told it did.
DEAD_HERO_LEDGER_PATH = "/privateState/deadHeroes"


def apply_combat(
    intent: Intent,
    content: CommittedContent,
    repository: SaveRepository,
    now: int,
) -> Outcome:
    """Execute one combat intent, or refuse it by name.  **Nothing is written.**

    ``now`` is the service's own clock, passed in rather than read here so a test
    can pin it.  It is never a request value: the intent has no field it could
    arrive in, and the preserved branch records no instant for this action.

    The five steps below are ordered so that **every refusal resolves before
    :meth:`SaveDocument.snapshot` is reached** (design D4).  The suite asserts
    that ordering against this file's own source rather than trusting it.
    """
    # ---- 1. the client-dictated destruction, refused before anything is read --
    unit_id = intent.unit_id
    if unit_id is None:  # pragma: no cover - parse_intent guarantees this
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "a combat intent addresses no unit id",
            {"addressing_field": "unit_id", "received": None},
        )
    if intent.destruction_request is not None:
        return _destruction_refusal(intent, unit_id)

    # ---- 2. read the store -------------------------------------------------
    try:
        document = repository.read(intent.player_id)
        before_resources = dict(document.resources())
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    # ---- 3. resolve the identity against the committed unit table -----------
    try:
        committed_row = content.unit_row(unit_id)
    except ContentError as error:  # pragma: no cover - no unit read raises today
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            f"committed content is unusable: {error}",
            {"content_code": error.code},
        )
    if committed_row is None:
        return _unknown_unit(content, unit_id)

    # ---- 4. snapshot: reached only when no refusal can follow ---------------
    try:
        before_document = document.snapshot()
        committed = _committed_report(content, unit_id, committed_row)
        gates = _gate_report(content, document, unit_id)
    except ContentError as error:
        return _refuse(
            RefusalCode.UNREADABLE_CONTENT,
            f"committed content is unusable: {error}",
            {"content_code": error.code, "requested_unit_id": unit_id},
        )
    except RepositoryError as error:
        return _repository_refusal(error, intent)

    destruction = _destruction_report(intent, unit_id)

    # ---- 5. read back and prove -------------------------------------------
    try:
        after = repository.read(intent.player_id)
        after_resources = dict(after.resources())
        after_document = after.snapshot()
    except RepositoryError as error:
        return _proof_refusal(
            intent, unit_id, "read_back", str(error), None, None
        )

    checks = _checks(
        unit_id=unit_id,
        content=content,
        document=after,
        committed=committed,
        gates=gates,
        before_resources=before_resources,
        after_resources=after_resources,
        before_document=before_document,
        after_document=after_document,
    )
    broken = [name for name, held, message in checks if not held]
    if broken:
        detail = {
            name: message for name, held, message in checks if not held
        }
        return _proof_refusal(
            intent,
            unit_id,
            broken[0],
            detail[broken[0]],
            tuple(broken),
            _changed_leaf_paths(before_document, after_document),
        )

    return CombatSuccess(
        action=ACTION,
        unit_id=unit_id,
        instant=now,
        state=after_resources,
        committed=committed,
        gates=gates,
        team_asymmetry=dict(TEAM_ASYMMETRY),
        destruction=destruction,
        proof=tuple((name, held) for name, held, message in checks),
        leaf_paths_changed=(),
        document_unchanged=True,
    )


# ------------------------------------------------------------------ refusals --


def _destruction_refusal(intent: Intent, unit_id: int) -> Refusal:
    """The one domain-level refusal this slice owns, and it is total (design D5).

    The request carried the preserved branch's own destruction wire shape, so it
    is refused by name rather than dereferenced, narrowed, or partially honoured.
    The figure is reported **verbatim** beside the code that refused it, so a
    client can see what it sent; nothing in this module counts it, bounds it, or
    turns it into any other number.

    **One code, not four.**  The same branch also reads and discards ``honor``,
    ``resources``, ``resources_victim`` and ``townhall_gold``, and those are
    closed by the existing ``client_supplied_delta`` **key-name** channel rather
    than by a code each.  Three or four codes for one decision is how a closed
    vocabulary stops being closed.

    The status difference from the v0 counterpart is deliberate and is recorded
    on ``RefusalCode.CLIENT_DICTATED_DESTRUCTION``: v0's is a 4xx because v0
    applies the client-sent resource vector before the dispatcher opens, while
    v1's is a **409** because the request is well-formed and the player exists
    and it conflicts with what the client may decide.
    """
    return _refuse(
        RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        (
            f"unit {unit_id} was resolved, but the request also carried a "
            "destruction figure, so nothing is destroyed: the preserved branch's "
            "count is max(0, A - B) over two numbers the client sends "
            "(command.py:868) and no committed value names its outcome, so v1 "
            "applies no count and derives none"
        ),
        {
            "player_id": intent.player_id,
            "requested_unit_id": unit_id,
            "requested_destruction": intent.destruction_request,
            "requested_destruction_is": (
                "the preserved branch's own wire shape, carried verbatim and "
                "neither counted, bounded, nor converted into any other figure"
            ),
            "applied": False,
            "count_derived": False,
            "rows_destroyed": 0,
            "ledger_credited": False,
            "preserved_rule": PRESERVED_COMBAT_BEHAVIOUR["destruction"],
            "rolled_back": False,
            "rollback_note": (
                "there is no write in this module, so no rollback was started; "
                "the document is byte-identical because nothing was ever written"
            ),
        },
    )


def _unknown_unit(content: CommittedContent, unit_id: int) -> Refusal:
    """The identity refusal, with the committed unit id space reported.

    Refused rather than aliased for a measured reason: the preserved branch never
    indexes the committed table at all — it takes ``unit[0]`` from the client's
    own list and uses it as a saved id — so ``0`` and every negative id simply
    name nothing.  There is no positional clamp here for a non-positive id to
    collide with, which is the same asymmetry ``server_v1_magic`` records for
    ``magic_id`` and the reason ``unit_id`` is deliberately **not** in
    :data:`server_v1_intent.NON_NEGATIVE_ADDRESSING`.

    The code is ``unaddressable_row``, an existing member of the closed table,
    rather than a second new one: this line adds exactly one code
    (``client_dictated_destruction``) and inventing an identity code as well
    would make two additions where the design settled on one.
    """
    committed_ids = content.unit_ids()
    return _refuse(
        RefusalCode.UNADDRESSABLE_ROW,
        (
            f"unit id {unit_id} names no row of the committed unit table, which "
            f"holds {len(committed_ids)} rows; the three committed id spaces "
            "have zero overlap, so a building or the one special cannot resolve "
            "here either"
        ),
        {
            "requested_unit_id": unit_id,
            "committed_unit_ids": list(committed_ids),
            "committed_unit_rows": len(committed_ids),
            "committed_table_is": "items, restricted to the rows whose type is u",
            "resolved_row": None,
            "non_positive_is_not_clamped": True,
            "why_not_clamped": (
                "the preserved branch never indexes the committed table, so zero "
                "and every negative id name no row at all rather than aliasing a "
                "position; a clamp would be a second addressing rule"
            ),
            "rolled_back": False,
        },
    )


def _proof_refusal(
    intent: Intent,
    unit_id: int,
    half: str,
    message: str,
    failed: Optional[Tuple[str, ...]],
    leaf_paths: Optional[Tuple[str, ...]],
) -> Refusal:
    """A failed proof, reported as the integrity code it is rather than as a
    gameplay answer.

    There is nothing to roll back: this module performs no write, so the document
    is byte-identical whether the proof held or not, and ``rolled_back`` is
    reported as ``False`` with the reason rather than as a claim about work that
    was never started.
    """
    detail: Dict[str, Any] = {
        "player_id": intent.player_id,
        "requested_unit_id": unit_id,
        "half": half,
        "cause": message,
        "addressed_path": intent.addressed_path(),
        "rolled_back": False,
        "rollback_note": (
            "this module performs no write, so there was nothing to roll back; "
            "the whole-document comparison is itself part of the proof that failed"
        ),
    }
    if failed is not None:
        detail["failed_checks"] = list(failed)
    if leaf_paths is not None:
        detail["leaf_paths_changed"] = list(leaf_paths)
    return _refuse(RefusalCode.POST_CONDITION_VIOLATION, message, detail)


def _repository_refusal(error: RepositoryError, intent: Intent) -> Refusal:
    """Map a store or content failure onto the shared codes, as every slice does.

    Every refusal this module can produce resolves before any write, so the
    refusal branch needs no rollback and says so.
    """
    if error.code == "unknown_player":
        return _refuse(
            RefusalCode.UNKNOWN_PLAYER, str(error), {"player_id": intent.player_id}
        )
    return _refuse(
        RefusalCode.UNREADABLE_STATE,
        str(error),
        {
            "player_id": intent.player_id,
            "cause": error.code,
            "rolled_back": False,
        },
    )


# ------------------------------------------------------------------- reports --


def _committed_report(
    content: CommittedContent, unit_id: int, committed_row: Mapping[str, Any]
) -> Dict[str, Any]:
    """The committed unit row, verbatim, and the nine columns nothing reads.

    **No value here is computed from another.**  Every combat column is reported
    exactly as the committed ``items`` table stores it — as a **string**, because
    that is the committed encoding — and none of them is read as a number, since
    no committed value names this branch's outcome (design D2).  The identity
    columns are reported beside them so a client can see *which* row was named.

    The ``id`` column is the **committed id**, which is the column the
    repository's normalized package names ``legacy_id``; it is not the row's
    position in the committed array, and the response says so.
    """
    report: Dict[str, Any] = {}
    for field in IDENTITY_COMMITTED_FIELDS:
        value = committed_row.get(field)
        report[field] = value if isinstance(value, (str, int)) else None
    report["resolved_id"] = unit_id
    report["id_keyed_by"] = (
        "the committed id column, which the normalized package calls legacy_id, "
        "not the row's position in the committed array"
    )
    report["resolved_against"] = (
        "the committed items rows whose type column is u; the three committed id "
        "spaces have zero overlap, so a building or the special cannot resolve"
    )
    report["combat_fields"] = {
        field: committed_row.get(field) for field in ZERO_CONSUMER_COMBAT_FIELDS
    }
    report["combat_fields_stored_as"] = (
        "strings in the committed items table; reported verbatim and never read "
        "as a number"
    )
    report["combat_fields_legacy_consumers"] = 0
    report["combat_fields_note"] = (
        "each of these nine measures zero legacy occurrences over the preserved "
        "modules, and the only one that appears at all (attack) has a whole-word "
        "count of 0 with all twelve whole-file occurrences inside longer "
        "identifiers, so no committed column names this branch's outcome"
    )
    return report


def _rows_report(document: Any, unit_id: int) -> List[Dict[str, Any]]:
    """Every recorded row carrying the addressed committed id, in stored order.

    **A report, not a selection.**  The preserved helper walks the map in the
    save's own key order and consumes the first match; this reader hands back
    **every** matching key in that same order and removes nothing, because v1
    destroys nothing and a reader that picked one would be choosing on the
    client's behalf.

    The per-row ``would_pass_team_gate`` is the preserved comparison
    ``item[7] == 1`` (``engine.py:151``) applied to one recorded row.  It is not a
    verdict about the transaction — nothing here is enforced — and it is reported
    per row because "would the gate pass" is ill-defined for an identity with
    several rows and :func:`_gate_report` therefore aggregates rather than picks.
    """
    rows: List[Dict[str, Any]] = []
    for key in document.rows_for_item_id(unit_id):
        team = document.row_team(key)
        rows.append(
            {
                "key": key,
                "recorded_team": team,
                "would_pass_team_gate": team == LEDGER_TEAM,
            }
        )
    return rows


def _gate_report(
    content: CommittedContent, document: Any, unit_id: int
) -> Dict[str, Any]:
    """Both recorded gates, resolved from committed content and recorded state.

    **Reported, never enforced, never acted on** (design D3).  Each gate carries
    its own presence flag, so an absent committed ``resurrectable`` is reported
    as absent and never as ``0`` — the preserved helper returns ``False`` on an
    absent key (``engine.py:159-160``) rather than reading it, and a reader that
    collapsed the two would report a committed fact the source never states.

    The **row** half is an absence when the addressed identity has no row, and an
    absence is reported: ``row_present`` is ``false``, the per-row list is empty,
    and every team verdict is ``null`` rather than ``false``.  The fresh corpus
    places 40 rows and **0** unit rows, so this is the case the committed live
    phase actually exercises, and reporting it is what distinguishes this route
    from one that refuses everything that corpus contains.

    ``resurrectable`` lives inside the committed row's ``properties``
    **embedded-JSON string**, not at the top level of the row — measured, and a
    correction to the design's and the task's wording.  The committed values are
    the **string** ``"1"`` on 426 of 429 units and the key is **absent** on ids
    ``923``, ``933`` and ``1176``; ``0`` of 470 buildings carry it at all.
    """
    flag = content.unit_flag(unit_id, "resurrectable")
    positive = content.unit_flag_is_positive(unit_id, "resurrectable")
    rows = _rows_report(document, unit_id)
    present = bool(rows)
    return {
        "gate_one_team": {
            "preserved_test": (
                "push_dead_unit requires the row's recorded slot 7 to be exactly "
                "1 and returns False otherwise (engine.py:151)"
            ),
            "source": (
                "maps[0].items[key][7] of every recorded row whose item id is the "
                "addressed committed identity"
            ),
            "row_present": present,
            "row_count": len(rows),
            "rows": rows,
            "recorded_team": rows[0]["recorded_team"] if rows else None,
            "every_row_would_pass": (
                bool(rows) and all(row["would_pass_team_gate"] for row in rows)
            )
            if present
            else None,
            "any_row_would_pass": (
                any(row["would_pass_team_gate"] for row in rows) if present else None
            ),
            "absence_reported_as": (
                "null verdicts and an empty row list, because the gate has no "
                "input when no recorded row carries the identity"
            ),
        },
        "gate_two_resurrectable": {
            "preserved_test": (
                "push_dead_unit reads the committed properties object, returns "
                "False when the key is absent, and otherwise compares "
                "int(resurrectable) > 0 (engine.py:155-162)"
            ),
            "source": "the committed unit row's properties object",
            "stored_as": (
                "an embedded JSON string inside the committed items row, not a "
                "top-level column of it"
            ),
            "present": flag is not None,
            "committed_value": flag,
            "committed_value_is": (
                "the committed value verbatim; the committed encoding is the "
                "string, and it is compared as a number exactly as the preserved "
                "helper does, never by truthiness"
            ),
            "would_pass": positive,
            "absent_is_read_as_zero": False,
            "absence_note": (
                "an absent key is reported as absent and never as 0, because the "
                "preserved helper returns False on an absent key rather than "
                "reading one"
            ),
        },
        "enforced": False,
        "enforced_note": (
            "neither gate is a precondition here: the transaction destroys "
            "nothing, so there is no operation for a gate to stand in front of "
            "(design D3)"
        ),
    }


def _destruction_report(intent: Intent, unit_id: int) -> Dict[str, Any]:
    """What the request tried to destroy and why nothing was, as data.

    This is the **success** half of the destruction decision: a request that
    carried the branch's wire shape never reaches here, because
    :func:`_destruction_refusal` resolved first.  So on every success the field
    is ``null``, and the report says what the value would have been — which is
    the point: a client can see that there is a shape it may not send, without v1
    ever having computed a number from it.
    """
    return {
        "requested": None,
        "refused_by_code": RefusalCode.CLIENT_DICTATED_DESTRUCTION.value,
        "refused_status": 409,
        "requested_is_none_because": (
            "a request carrying the branch's destruction shape is refused before "
            "the identity is resolved, so a successful request never had one"
        ),
        "applied": False,
        "count_derived": False,
        "count": None,
        "count_refused_because": (
            "no committed value names this branch's outcome: the nine committed "
            "combat columns have zero legacy consumers, and the preserved branch's "
            "only quantity is a subtraction of two client numbers (design D2)"
        ),
        "preserved_rule": PRESERVED_COMBAT_BEHAVIOUR["destruction"],
        "ledger_rule": PRESERVED_COMBAT_BEHAVIOUR["ledger"],
        "rejected_alternatives": {
            "destroy_one_row": (
                "v0's resolve action reports destruction: 1, but that 1 is a "
                "property of combat_payload's own construction and the same v0 "
                "route destroyed two rows for A=3, B=1 at committed fixture step "
                "7, so one is a fixture convenience rather than a rule"
            ),
            "destroy_every_eligible_row": (
                "the client still chooses which unit and the server still cannot "
                "say how many; the count is still client-dictated in a different "
                "spelling, and an identity with no matching row would get a "
                "silent success"
            ),
            "derive_from_attack_minus_defense": (
                "neither committed column is read by anything and attack is not "
                "even a whole-word occurrence in the preserved source"
            ),
        },
    }


# --------------------------------------------------------------------- proof --


def _checks(
    *,
    unit_id: int,
    content: CommittedContent,
    document: Any,
    committed: Dict[str, Any],
    gates: Dict[str, Any],
    before_resources: Dict[str, int],
    after_resources: Dict[str, int],
    before_document: Any,
    after_document: Any,
) -> Tuple[Tuple[str, bool, str], ...]:
    """The five proof checks, in the order :func:`apply_combat` walks them.

    Returns ``(check, held, failure_message)`` triples where an **empty** message
    means the check held.  One ordered list is walked by both the caller and
    :func:`_proof_refusal`, so the reported half cannot drift from the enforced
    one.

    **Checks 1 and 2 re-read their subject** rather than comparing a carried
    forward value with itself, which is what keeps them falsifiable at all: a
    projection that reported the same object it read would be vacuously true.
    Checks 3 and 4 compare two whole documents over the store, and check 5 covers
    the seven stored resources — the **complete** set v1 knows about, never a
    subset.
    """
    checks: List[Tuple[str, bool, str]] = []

    # 1. the identity resolves to the committed row the response reports.
    fresh_row = content.unit_row(unit_id)
    fresh_report = (
        None
        if fresh_row is None
        else {field: fresh_row.get(field) for field in IDENTITY_COMMITTED_FIELDS}
    )
    reported_identity = {
        field: committed.get(field) for field in IDENTITY_COMMITTED_FIELDS
    }
    if fresh_report != reported_identity or committed.get("resolved_id") != unit_id:
        checks.append(
            (
                "identity_resolved_to_reported_row",
                False,
                f"the response reports {reported_identity!r} for unit {unit_id}, "
                f"which a fresh read of the committed unit table resolves to "
                f"{fresh_report!r}",
            )
        )
    else:
        checks.append(("identity_resolved_to_reported_row", True, ""))

    # 2. both reported gates match committed content and recorded state.
    fresh_flag = content.unit_flag(unit_id, "resurrectable")
    fresh_positive = content.unit_flag_is_positive(unit_id, "resurrectable")
    fresh_rows = _rows_report(document, unit_id)
    reported_flag = gates["gate_two_resurrectable"]["committed_value"]
    reported_positive = gates["gate_two_resurrectable"]["would_pass"]
    reported_rows = gates["gate_one_team"]["rows"]
    reported_present = gates["gate_one_team"]["row_present"]
    if (
        fresh_flag != reported_flag
        or fresh_positive != reported_positive
        or fresh_rows != reported_rows
        or bool(fresh_rows) != reported_present
    ):
        checks.append(
            (
                "reported_gates_match_content_and_state",
                False,
                "the reported gates do not match a fresh read: committed "
                f"resurrectable {reported_flag!r} against {fresh_flag!r}, "
                f"rows {reported_rows!r} against {fresh_rows!r}",
            )
        )
    else:
        checks.append(("reported_gates_match_content_and_state", True, ""))

    # 3. the leaf census -- empty here, and it NAMES what moved if it is not.
    changed = _changed_leaf_paths(before_document, after_document)
    if changed:
        checks.append(
            (
                "no_leaf_path_changed",
                False,
                f"the stored document changed at {changed!r}, and this "
                "transaction destroys nothing and derives no count",
            )
        )
    else:
        checks.append(("no_leaf_path_changed", True, ""))

    # 4. the whole document, as serialised bytes.
    before_bytes = _serialise(before_document)
    after_bytes = _serialise(after_document)
    if before_bytes != after_bytes:
        checks.append(
            (
                "whole_document_unchanged",
                False,
                "the stored document serialises to different bytes before and "
                f"after: {len(before_bytes)} bytes against {len(after_bytes)}",
            )
        )
    else:
        checks.append(("whole_document_unchanged", True, ""))

    # 5. every stored resource v1 knows about, never a subset.
    moved = sorted(
        name
        for name in STORED_RESOURCE_NAMES
        if after_resources.get(name) != before_resources[name]
    )
    if moved:
        checks.append(
            (
                "resources_unchanged",
                False,
                f"stored resource(s) {moved!r} moved; this transaction charges "
                "and pays nothing",
            )
        )
    else:
        checks.append(("resources_unchanged", True, ""))

    return tuple(checks)


def _changed_leaf_paths(before: Any, after: Any, prefix: str = "") -> List[str]:
    """Every **leaf** path whose value differs between two parsed documents.

    A leaf is a scalar; a dict or list is walked and a list of a different length
    reports its own length as the changed path.  The helper exists so "nothing
    changed" is a **measurement** over the whole document rather than a claim
    about the one key the slice would have written, which is the difference
    between a proof and an assertion.  It is the same shape as the sibling
    slices' helper, kept here because the domain runs the check itself and a test
    helper is not reachable from a module.
    """
    if isinstance(before, dict) and isinstance(after, dict):
        paths: List[str] = []
        for key in sorted(set(before) | set(after), key=str):
            paths.extend(
                _changed_leaf_paths(
                    before.get(key), after.get(key), "{}/{}".format(prefix, key)
                )
            )
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths = []
        if len(before) != len(after):
            return [f"{prefix or '/'}/length"]
        for index in range(len(before)):
            paths.extend(
                _changed_leaf_paths(
                    before[index],
                    after[index],
                    "{}/{}".format(prefix, index),
                )
            )
        return paths
    if before == after and type(before) is type(after):
        return []
    return [prefix or "/"]


def _serialise(document: Any) -> str:
    """A document's **serialised bytes**, for the whole-document comparison.

    A string rather than a value comparison, because "byte-identical" is the
    claim this boundary makes and a string is what it can be about.  Python's
    ``json.dumps`` preserves the parsed key order, so two documents serialise
    identically exactly when every key and every value is identical, and no key
    reorder can hide behind a sort.
    """
    return json.dumps(document, separators=(",", ":"))


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=dict(detail))


__all__ = [
    "ACTION",
    "DEAD_HERO_LEDGER_PATH",
    "IDENTITY_COMMITTED_FIELDS",
    "LEDGER_TEAM",
    "MAP_LOSE_ITEM_CALL_SITES",
    "NONE_DEREFERENCE_FACTS",
    "TEAM_ASYMMETRY",
    "ZERO_CONSUMER_COMBAT_FIELDS",
    "apply_combat",
]