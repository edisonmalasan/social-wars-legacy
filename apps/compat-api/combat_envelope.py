#!/usr/bin/env python3
"""Derivation of the combat-action surface and its closed legacy envelope.

M10 line 2 (``combat-actions``).  This module is the single place where the
combat request's field inventory, its validation ordering, the server-derived
destruction set, both kill contracts, and the recorded divergence become the
legacy batch envelope, so the Compatibility API ``POST /v0/combat`` endpoint and
its suites are checked against *one* derivation.

The mechanism (design D1)
    The request carries the **identity** of the unit that was lost -- its
    committed item id -- and **nothing else**.  The service derives

    * the **eligible rows**: placed rows whose recorded slot 0 equals that item
      id **and** whose recorded slot 7 is truthy, exactly as
      ``engine.map_lose_item`` tests them (``engine.py:221``);
    * the **addressed row**: the *first* eligible row in the save's own recorded
      map-key order, which is the iteration order ``map_lose_item`` uses
      (``for index in map_items``) and therefore the order it pops;
    * the **destruction count**: exactly **one**, always, because there is no
      combat rule to derive any other number with.

The legacy count is ``max(0, unit[2] - unit[3])`` on two client numbers
(``command.py:868``), labelled only ``A`` and ``B`` in the committed source.
That subtraction is **REFUSED, never reproduced** (design D1/D2): reproducing it
would make this server a pass-through for a client-computed casualty figure,
which is the ``AGENTS.md`` "Bad" pattern and the identical anti-pattern the M9
``quests`` line refused in ``end_quest``.

Why one and not "however many match"
    ``map_lose_item`` loops ``while qty > 0`` and returns the moment a pass finds
    no match (``engine.py:226-227``), so its apparent safety against
    over-deletion is **exhaustion of matches, not a check**.  Mistaking one for
    the other is how an untrusted count survives review, so no loop count is
    derived here and no clamp is applied: one is the largest destruction the
    service can justify without inventing a combat rule.

    Exhaustion is equally a **silent under-deletion**, and this is measured
    rather than argued: an identity with **no** matching row left the loop's very
    first pass unmatched, so nothing was destroyed at all, yet the branch still
    printed ``Lost 1`` because its print sits *before* its call and is not
    conditional on it (``command.py:871-872``; see
    :data:`PRINTED_COUNT_IS_A_REQUEST`).  The legacy count therefore answers two
    questions neither the response nor the save can: how many were asked for, and
    not how many were actually destroyed.  Reading it as the second -- which is
    what its name invites -- would put the whole untrusted subtraction back in
    play, which is why exactly one is derived and the response reports the
    **derived** figure against the state it was measured from.

Both ledger gates, and no third (design D1, D7)
    ``engine.push_dead_unit`` (``engine.py:149-170``) records the loss in
    ``privateState["deadHeroes"]`` only when the row is on **player team 1**
    (``engine.py:151``) **and** its committed ``properties`` carry
    ``resurrectable > 0`` (``engine.py:159,162``).  Those are the only two
    conditions the helper checks, and this module derives no third.

    The **team asymmetry** between the two helpers is recorded, never exercised
    and never refused (design D7): ``map_lose_item`` accepts any **truthy**
    recorded team while ``push_dead_unit`` records only team one, so a non-team-one
    row would be destroyed yet never enter the ledger.  All 441 committed unit
    rows are team one, so the case is unreachable from the committed corpus, and
    refusing it would invent a bound the oracle does not have.

The two kill commands (design D5)
    ``kill`` (``command.py:169-181``) looks the row up and **deletes it**, and
    **never** touches the ledger -- structurally, not by observation.
    ``kill_iid`` (``command.py:183-187``) **writes nothing**: its body binds
    two locals from ``args`` and then prints, and every assignment target is a
    bare ``Name``.  It is therefore delivered as a
    **proven no-op** rather than refused, because an empty branch is a behaviour
    the preserved server has and a client can be verified against.

Every refusal resolves before dispatch (design D3)
    The legacy branch's two unguarded absent-value dereferences sit on **opposite
    sides** of its write loop: omitting ``attacker_units`` raises at
    ``command.py:866`` before the loop body runs, while omitting ``victim`` raises
    at ``command.py:874`` after ``map_lose_item`` already ran.  Both answer HTTP
    500 and the **persisted** save is byte-identical either way, because
    ``command.py`` dispatches the whole batch first and calls ``save_session`` only
    afterwards (``command.py:30,32``) -- an exception anywhere in a batch discards
    every mutation it made.  Measured, including a two-command batch whose first
    command was valid and printed its destruction: the persisted state did not
    move.  The failure mode is a **discarded** save, not a partially applied one,
    and the persistence boundary is the **batch**.  Every check here still resolves
    before dispatch, so a refusal can never leave a half-applied state whatever a
    future persistence change does.

Three guards the branch does have, all found by execution rather than by reading
    * an **empty** blob short-circuits at ``command.py:818``'s ``if not
      response:``, prints "Error: Failed to parse command." and **answers
      success** with no change -- so the key that raises against a non-empty blob
      is answered successfully against an empty one;
    * an identity with **no** matching row makes ``map_lose_item`` return at once,
      yet the branch still printed ``Lost 1``: the print at ``command.py:871`` runs
      **before** the call at ``command.py:872`` and is not conditional on it, so
      the branch's printed count reports what the client **asked for**, never what
      it destroyed (:data:`PRINTED_COUNT_IS_A_REQUEST`);
    * ``map_lose_item`` therefore **never** over-deletes -- but only because it
      runs out of matches, not because anything bounds it.

The field inventory is re-derived, never transcribed (design D4)
    :func:`derive_field_inventory` reads ``command.py`` **as bytes** on every
    verification run and classifies each key the legacy branch reads.  Nothing
    here transcribes a key list, so a legacy edit fails the guard instead of
    silently contradicting the record.

MEASURED CORRECTION against the committed investigation and the approved delta
    Four figures in ``docs/legacy-m10-combat.md`` and in the ``combat-actions``
    spec deltas do not reproduce.  They are recorded in
    :data:`FIELD_INVENTORY_CORRECTION` and :data:`CORPUS_CORRECTION` with both
    numbers side by side and are **not** silently replaced.

Shared derivation
    The envelope primitives are imported unchanged from
    :mod:`placement_envelope` -- ``ENVELOPE_KEYS``, ``EnvelopeError``,
    ``is_strict_int``, ``payload_json``, and ``data_field`` -- so every earlier
    delivered derivation, fixture, and suite keeps passing untouched.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# One shared derivation.  Nothing here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    is_strict_int,
    payload_json,
)

# ---------------------------------------------------------- the commands ----
#: The three legacy branches this line delivers, each executed by the unchanged
#: legacy dispatcher through :mod:`compat_legacy`.
END_ATTACK_COMMAND = "end_attack"
KILL_COMMAND = "kill"
KILL_IID_COMMAND = "kill_iid"

#: The single dispatcher branch whose client blob this line reads
#: (``command.py:808-885``).
COMBAT_BRANCH = END_ATTACK_COMMAND

#: The **closed** action vocabulary this route accepts.  One action names one
#: legacy branch, and nothing else is accepted.
ACTION_RESOLVE = "resolve"
ACTION_KILL = "kill"
ACTION_KILL_IID = "kill_iid"
ACTIONS = (ACTION_RESOLVE, ACTION_KILL, ACTION_KILL_IID)
ACTION_COUNT = len(ACTIONS)

#: Which legacy branch each action dispatches, and the ONE value a client may
#: name for it.  The addressing is the branch's own subject -- a unit identity for
#: the combat resolution, a map key for the row removal, an item id for the
#: item-keyed no-op -- and every other value is derived.
ACTION_COMMAND = {
    ACTION_RESOLVE: END_ATTACK_COMMAND,
    ACTION_KILL: KILL_COMMAND,
    ACTION_KILL_IID: KILL_IID_COMMAND,
}
ACTION_ADDRESSING_KEY = {
    ACTION_RESOLVE: "item_id",
    ACTION_KILL: "map_key",
    ACTION_KILL_IID: "item_id",
}
ACTION_ADDRESSING = {
    ACTION_RESOLVE: "the committed item id of the unit that was lost",
    ACTION_KILL: "the map key of the placed row to remove",
    ACTION_KILL_IID: "the committed item id the legacy branch only prints",
}
BRANCHES = (
    {
        "action": ACTION_RESOLVE,
        "command": END_ATTACK_COMMAND,
        "kind": "dispatcher-branch",
        "source": "command.py:808-885",
        "addressing_key": "item_id",
        "destroys_rows": True,
        "reaches_ledger": True,
        "through": "map_lose_item (engine helper, engine.py:215-228) -> "
                   "push_dead_unit (engine helper, engine.py:149-170)",
        "note": "the sole mutation path in the whole branch; the client payload's "
                "destruction count is refused rather than reproduced",
    },
    {
        "action": ACTION_KILL,
        "command": KILL_COMMAND,
        "kind": "dispatcher-branch",
        "source": "command.py:169-181",
        "addressing_key": "map_key",
        "destroys_rows": True,
        "reaches_ledger": False,
        "through": None,
        "note": "deletes the addressed row and NEVER touches privateState"
                "['deadHeroes']; the branch holds no push_dead_unit call, so the "
                "ledger's non-participation is a property of the branch rather "
                "than an observation of one request",
    },
    {
        "action": ACTION_KILL_IID,
        "command": KILL_IID_COMMAND,
        "kind": "dispatcher-branch",
        "source": "command.py:183-187",
        "addressing_key": "item_id",
        "destroys_rows": False,
        "reaches_ledger": False,
        "through": None,
        "note": "WRITES NOTHING: the branch binds two locals from args, every "
                "assignment target is a bare Name, and its only call is one "
                "print, so it is delivered as a proven no-op rather than "
                "refused (design D5)",
    },
)

# -------------------------------------------------------- the row shape -----
#: The committed map row shape (``engine.map_add_item``, ``engine.py:8-31``):
#: ``[item, x, y, timestamp, orientation, store, attr, player]``.
MAP_ROW_SLOTS = 8
SLOT_ITEM_ID = 0
SLOT_CELL_X = 1
SLOT_CELL_Y = 2
SLOT_ATTR = 6
SLOT_PLAYER = 7

#: Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
#: cash, mana] (``engine.apply_resources``, ``engine.py:251-271``).
RESOURCE_VECTOR_SLOTS = 8

#: The seven stored resource slots the endpoint's post-execution proof compares.
#: Every one of them, never a subset: that is what makes the no-resource-moved
#: claim non-tautological.
RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")

#: The ledger's own save location.
LEDGER_KEY = "deadHeroes"
PRIVATE_STATE_KEY = "privateState"

#: The committed player team ``push_dead_unit`` requires (``engine.py:151``).
PLAYER_TEAM = 1

#: The committed ``properties`` flag ``push_dead_unit`` names
#: (``engine.py:159,162``), read from the RAW configuration string.
RESURRECTABLE_FLAG = "resurrectable"
PROPERTIES_FIELD = "properties"

# ----------------------------------------------------------- the gates ------
GATE_TEAM_ONE = {
    "gate": "player_team_one",
    "checks": "the destroyed row's slot 7 (player) equals 1",
    "source": "engine.py:151 (push_dead_unit)",
    "committed": True,
    "note": "push_dead_unit returns False when item[7] != 1, so a row on another "
            "team is destroyed by map_lose_item yet never enters the ledger",
}
GATE_RESURRECTABLE = {
    "gate": "resurrectable_positive",
    "checks": "the committed properties object carries resurrectable and "
              "int(resurrectable) > 0",
    "source": "engine.py:159,162 (push_dead_unit)",
    "committed": True,
    "note": "push_dead_unit returns False when the flag is absent AND when it is "
            "present but not greater than zero, so an absent flag is a REFUSAL "
            "and never a zero",
}

#: Both gates, in the helper's own order, and the machine-readable form of
#: "no third gate is invented".
GATES = (GATE_TEAM_ONE, GATE_RESURRECTABLE)
GATE_COUNT = 2

NO_THIRD_GATE = (
    "EXACTLY TWO GATES EXIST AND NO THIRD IS INVENTED. push_dead_unit "
    "(engine.py:149-170) performs two checks and no more: the row's player team "
    "(engine.py:151) and the committed resurrectable flag (engine.py:159,162). "
    "Absent from the helper are every check a reader might expect: no level "
    "check, no cost check, no capacity check, no cooldown, no per-type check, and "
    "no check that the row is a unit rather than a building. Adding any of them "
    "would make this client STRICTER than the legacy server, which is a parity "
    "break in the opposite direction from the usual risk"
)

# ------------------------------------------------ the team asymmetry (D7) ---
TEAM_ASYMMETRY = {
    "status": "RECORDED, NOT EXERCISED, NOT REFUSED",
    "row_removal_helper": {
        "helper": "map_lose_item",
        "source": "engine.py:215-228",
        "accepts": "ANY TRUTHY recorded team (`map_items[index][7]`, engine.py:221)",
        "is_dispatcher_branch": False,
    },
    "ledger_helper": {
        "helper": "push_dead_unit",
        "source": "engine.py:149-170",
        "accepts": "PLAYER TEAM 1 ONLY (`if item[7] != 1: return False`, "
                   "engine.py:151)",
        "is_dispatcher_branch": False,
    },
    "consequence": "a non-team-one unit row would be DESTROYED and would never "
                   "ENTER THE LEDGER",
    "committed_unit_rows": 441,
    "committed_unit_rows_on_team_one": 441,
    "exercised": False,
    "exercised_note": "unreachable from the committed corpus: every one of the "
                      "441 committed unit rows across the committed save "
                      "documents is on player team one, which is the value "
                      "push_dead_unit requires",
    "refused": False,
    "refused_note": "refusing it would invent a bound the oracle does not have, "
                    "which is the same reasoning that leaves the M6 tile-geometry "
                    "gap recorded rather than closed",
}

# ------------------------------------------ the field inventory (design D4) --
#: The legacy source the inventory is re-derived from, repository-relative.
LEGACY_SOURCE_RELATIVE = "command.py"

#: The dispatcher-branch delimiter, matched against the committed source.
_BRANCH_RE = re.compile(r'^\s*(?:el)?if\s+cmd\s*==\s*"([A-Za-z_]+)"\s*:\s*$')

#: The membership test the twelve read keys each carry.  This is the *only*
#: pattern this module transcribes from the legacy source, and it is a syntax
#: form rather than a key name: no key is ever written here.
_MEMBERSHIP_RE = re.compile(r'^\s*if\s+"([A-Za-z_]+)"\s+in\s+response:\s*$')

#: The row-removal helper whose single call site inside the branch defines the
#: mutation region.  It is located by searching for the call, never by naming a
#: key, so a legacy edit that moved the loop is still detected.
_ROW_REMOVAL_CALL = "map_lose_item("

_FATE_DISCARDED = "discarded"
_FATE_PRINT = "print_only"
_FATE_MUTATION = "mutation_path"

#: The three fates, as a closed vocabulary.  ``derive_field_inventory`` reports
#: every key with exactly one of them, and asserts the three sets partition the
#: inventory.
FATES = (_FATE_DISCARDED, _FATE_PRINT, _FATE_MUTATION)

#: The recorded-versus-measured correction, kept beside the derivation rather
#: than dropped.  The committed investigation ``docs/legacy-m10-combat.md:125``
#: states "Eleven keys are read from the client blob (command.py:839-862). Seven
#: reach nothing at all" and its own table then lists **eight** discarded rows;
#: the proposal ``proposal.md:41-42`` names **eight** keys while saying seven.
#: Measured from the branch, there are **twelve** read keys and **nine** reach
#: nothing: ``voluntary_end`` (``command.py:839-840``) is absent from both the
#: prose and the table.
FIELD_INVENTORY_CORRECTION = {
    "recorded_read_key_count": 11,
    "measured_read_key_count": 12,
    "recorded_discarded_count": 7,
    "recorded_discarded_count_in_the_own_table": 8,
    "measured_discarded_count": 9,
    "key_absent_from_the_recorded_table": "voluntary_end",
    "omitted_in_both": "voluntary_end (command.py:839-840)",
    "counting_rules_measured": [
        "a key is READ exactly when the branch carries an `if \"<key>\" in "
        "response:` test for it; the branch's dispatch form (`elif cmd ==`) is "
        "what delimits the branch, and the membership tests are matched as bytes",
        "a key REACHES NOTHING when it has zero occurrences of the bare word after the "
        "membership block has ENDED, quote-stripped so a comment cannot contribute "
        "and an assignment from the blob cannot count as a use. The block does not "
        "end at its last membership test: each test is followed by the line that "
        "transports the value out of the blob, and that transport is not a use "
        "either. Measured rather than assumed -- stopping at the last test filed "
        "resources_victim as print-only on the strength of its OWN assignment line "
        "and undercounted the discarded set by one",
        "a key is the MUTATION PATH when one of its post-block occurrences is "
        "inside the region delimited by the `for` loop whose body contains the "
        "branch's only row-removal call",
        "a key is PRINT-ONLY when it has post-block occurrences and none inside "
        "that region; it is derived as the complement of the two derived sets, "
        "and the identity discarded + print_only + mutation == total is asserted",
    ],
    "record_left_intact": (
        "The committed investigation's CONCLUSION is unchanged: eleven of the "
        "keys it names do reach nothing, which is the finding this capability "
        "was chartered to record. Only the counts are corrected, and the "
        "correction is measured rather than asserted."
    ),
}

#: The recorded-versus-measured corpus correction, beside the figures this module
#: publishes.  Every per-document row figure and every total in the committed
#: investigation's table reproduces exactly; the three derived prose figures do
#: not.
CORPUS_CORRECTION = {
    "measured_unit_rows": 441,
    "measured_unit_rows_on_team_one": 441,
    "measured_unit_rows_resurrectable": 429,
    "measured_placed_rows": 3372,
    "measured_documents": 10,
    "measured_documents_with_unit_rows": 7,
    "measured_documents_with_non_empty_ledger": 4,
    "recorded_documents": 11,
    "recorded_documents_with_non_empty_ledger": 5,
    "recorded_neutral_ledger_keys": 29,
    "measured_neutral_ledger_keys": 28,
    "reproduces_exactly": [
        "3,372 placed rows across the committed save documents",
        "441 committed unit rows",
        "441 committed unit rows on player team one",
        "429 satisfying the resurrectable gate",
        "every per-document row count in the committed table",
        "the 7 committed documents that carry unit rows",
        "Kiriakos 9 ledger keys, Nerri 9, Scarlet 2",
    ],
    "does_not_reproduce": [
        "'11 documents' measures 10: 8 under villages/ and 2 under tests/saves/. "
        "tests/saves/manifest.json is a manifest, not a save, and the "
        "villages/quest/ directory holds 23 quest documents of a different "
        "shape. The committed table itself lists exactly ten rows.",
        "'five village saves carry a non-empty deadHeroes ledger' measures "
        "FOUR, and the committed record's own enumeration names exactly four.",
        "Neutral.json's ledger holds 28 keys, not the recorded 29. The change's "
        "design.md D8 and proposal.md already state 28, so the investigation's "
        "table row is the outlier.",
    ],
    "counting_rules_measured": [
        "a committed save document is a *.json file under villages/ or "
        "tests/saves/ whose document carries maps[0].items",
        "`items` is an OBJECT keyed by map key, not a list; the iteration order "
        "is the JSON object's own insertion order, which is what "
        "`for index in map_items` walks",
        "a unit row is a placed row whose slot 0 is a legacy_id of "
        "packages/game-content/normalized/units.json",
        "the player team is slot 7 (`if item[7] != 1`, engine.py:151); slot 6 is "
        "the attribute bag, so a census that reads slot 6 as the team measures "
        "zero team-one rows",
        "the ledger is privateState.deadHeroes, NOT maps[0].deadHeroes; no "
        "committed document carries the latter",
        "resurrectable is a `properties` FLAG stored as a STRING in the "
        "normalized package, so int(\"0\") is 0 and a non-empty String being "
        "truthy must not be read as the integer one",
    ],
}

# ------------------------------------------------------- the refusals ------
REASON_UNKNOWN_ACTION = "unknown_action"
REASON_INVALID_ACTION = "invalid_action"
REASON_MISSING_ITEM_ID = "missing_item_id"
REASON_INVALID_ITEM_ID = "invalid_item_id"
REASON_MISSING_MAP_KEY = "missing_map_key"
REASON_INVALID_MAP_KEY = "invalid_map_key"
REASON_CLIENT_DICTATED_DESTRUCTION = "client_dictated_destruction"
REASON_NO_ELIGIBLE_ROW = "no_eligible_row"
REASON_UNADDRESSABLE_ROW = "unaddressable_row"
REASON_INVALID_LEDGER = "invalid_ledger"
REASON_INVALID_VECTOR = "invalid_vector"
REASON_INVALID_TIMESTAMP = "invalid_timestamp"
REASON_INVALID_PAYLOAD = "invalid_payload"

#: Client keys carrying a destruction count, a ``sent``/``survived`` pair, or the
#: legacy payload key itself.  Every one is **refused before dispatch** with
#: :data:`REASON_CLIENT_DICTATED_DESTRUCTION`, an empty payload, and no state
#: change (design D2).
#:
#: The legacy payload keys are exactly the keys ``end_attack`` reads, and they
#: are built from the derived inventory rather than transcribed: this tuple is
#: only used when the inventory cannot be derived at all.
DESTRUCTION_COUNT_KEYS = (
    "lost",
    "losses",
    "destroyed",
    "destroyed_count",
    "units_lost",
    "quantity",
    "qty",
    "count",
)
SENT_SURVIVED_KEYS = ("sent", "survived")

CLIENT_DICTATED_REFUSAL = (
    "A CLIENT-DICTATED DESTRUCTION COUNT IS REFUSED, NEVER REPRODUCED. The "
    "legacy branch derives its destruction count as max(0, unit[2] - unit[3]) "
    "(command.py:868) on two numbers the CLIENT supplies, and the committed "
    "source labels them only 'A' and 'B' with the comment 'number of loses is A "
    "- B' -- nothing establishes what they mean. This operation therefore "
    "destroys exactly ONE row, derived from its own recorded state. Reproducing "
    "the subtraction would make this server a pass-through for a "
    "client-computed casualty figure, which is the AGENTS.md Bad pattern and the "
    "identical anti-pattern the godot-quests line refused in end_quest. The "
    "difference is recorded as a DIVERGENCE, never as parity"
)

REFUSED_COUNT_NOTE = (
    "The legacy branch's apparent safety against over-deletion is EXHAUSTION OF "
    "MATCHES, NOT A CHECK: map_lose_item loops `while qty > 0` and returns the "
    "moment one pass finds no match (engine.py:218-227). Mistaking exhaustion "
    "for a bound is how an untrusted count survives review, so no loop count is "
    "derived here and no clamp is applied"
)

#: The printed count is a **request**, never an outcome.  Found by execution, not
#: by reading the branch: the unconditional ``print("Lost", lost)`` at
#: ``command.py:871`` executes **before** the ``map_lose_item`` call at ``:872``
#: and is not guarded by its result, so a committed item id with **zero** placed
#: rows -- nothing destroyed at all -- still printed ``Lost 1``.  This is recorded
#: because the branch's own log is the strongest-looking piece of evidence
#: *against* this line's refusal, and a future reader would otherwise cite it as
#: proof the count describes what happened.
PRINTED_COUNT_IS_A_REQUEST = (
    "THE BRANCH'S PRINTED COUNT REPORTS WHAT THE CLIENT ASKED FOR, NOT WHAT IT "
    "DESTROYED. The print at command.py:871 precedes the row-removal call at "
    ":872 and is not conditional on it, so `Lost N` is printed from the "
    "client-supplied subtraction whether or not a single row matched. MEASURED: "
    "item id 923 -- a committed unit id with zero placed rows -- printed `Lost 1` "
    "and destroyed nothing. Reading that log as an outcome count would reinstate "
    "the untrusted subtraction, which is why the count is refused and the one "
    "server-derived destruction is proved against the persisted state instead"
)

# --------------------------------------------------- the non-rules (D-note) --
NO_COMBAT = (
    "NO COMBAT IS RESOLVED OF ANY KIND. attack, defense, life, attack_interval, "
    "attack_range, best_against, best_against_mult, and velocity each measure "
    "ZERO legacy consumers across the seven legacy root modules, so the committed "
    "numbers are CONTENT and never rules. This contract computes no damage, no "
    "attack outcome, no defence application, no hit chance, and no life or "
    "interval arithmetic. No mission is dispatched, resolved, or completed either: "
    "the mission vocabulary remains owned by the godot-mission-vocabulary "
    "capability and nothing here references a mission field"
)

NO_COST_OR_REWARD = (
    "NO HONOUR, REWARD, OR RESOURCE MOVEMENT OF ANY KIND. The committed blob keys "
    "are `honor` (US spelling, command.py:846-847), `resources`, "
    "`resources_victim`, and `townhall_gold`; each is read from the client blob and "
    "DISCARDED, the committed honor schedule has zero legacy consumers, and the "
    "branch writes no resource field at all. The derived resource vector is "
    "therefore the neutral all-zero one and the endpoint's post-execution proof "
    "requires EVERY stored resource to be unchanged, which is what forecloses a "
    "vector smuggled through the request"
)

NO_SYRINGE_COST = (
    "NO SYRINGE COST IS CHARGED. The committed syringes field is carried by all "
    "429 units and all 470 buildings and has zero legacy consumers, and no "
    "combat-adjacent revival is delivered here, so no cost is charged and no "
    "stored resource moves"
)

NO_PLACEMENT_VALIDATION = (
    "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED. map_lose_item "
    "tests only the item id and the team's truthiness (engine.py:221) and "
    "inventory selection adds no check of its own, so this contract reproduces "
    "that absence rather than filling it. Inventing a check here would make this "
    "client STRICTER than the legacy server. The gap is recorded as a Server v1 "
    "/ M13 requirement, exactly as godot-building-move, godot-building-collect, "
    "and godot-stored-item-placement already do"
)

#: Every refusal, as one machine-readable list.  ``implemented`` is the flag that
#: separates two opposite obligations, which is why the split exists: a **True**
#: entry is a guard this line actively enforces, while a **False** entry is a rule
#: it deliberately declines to add.  Reading a False entry as an omission is the
#: mistake this field prevents.
REFUSALS = (
    {
        "refusal": "client_dictated_destruction",
        "implemented": True,
        "rule": CLIENT_DICTATED_REFUSAL,
        "note": REFUSED_COUNT_NOTE,
    },
    {
        "refusal": "combat_resolution",
        "implemented": False,
        "rule": NO_COMBAT,
    },
    {
        "refusal": "no_cost_or_reward",
        "implemented": False,
        "rule": NO_COST_OR_REWARD,
    },
    {
        "refusal": "syringe_cost",
        "implemented": False,
        "rule": NO_SYRINGE_COST,
    },
    {
        "refusal": "placement_validation",
        "implemented": False,
        "rule": NO_PLACEMENT_VALIDATION,
    },
)

# ----------------------------------------------- the ordering guarantee ----
VALIDATION_ORDER = (
    {"step": 1, "check": "action_is_in_the_closed_vocabulary",
     "resolves": "before dispatch"},
    {"step": 2, "check": "no_client_dictated_destruction_key",
     "resolves": "before dispatch", "code": REASON_CLIENT_DICTATED_DESTRUCTION},
    {"step": 3, "check": "addressing_present_and_well_typed",
     "resolves": "before dispatch"},
    {"step": 4, "check": "eligible_row_resolves",
     "resolves": "before dispatch", "code": REASON_NO_ELIGIBLE_ROW},
    {"step": 5, "check": "addressed_row_resolves",
     "resolves": "before dispatch", "code": REASON_UNADDRESSABLE_ROW},
    {"step": 6, "check": "ledger_readable",
     "resolves": "before dispatch", "code": REASON_INVALID_LEDGER},
    {"step": 7, "check": "destruction_set_derived",
     "resolves": "before dispatch"},
    {"step": 8, "check": "derivation_ready_to_execute",
     "resolves": "before dispatch"},
    {"step": 9, "check": "destruction", "resolves": "THE WRITE STEP"},
    {"step": 10, "check": "post_execution_proof", "resolves": "after dispatch"},
)
VALIDATION_ORDER_STEPS = len(VALIDATION_ORDER)
DESTRUCTION_STEP = 9

ORDERING_RULE = (
    "EVERY VALIDATION COMPLETES BEFORE ANY ROW IS REMOVED (design D3). The legacy "
    "branch's two unguarded absent-value dereferences sit on OPPOSITE SIDES of its "
    "write loop: omitting attacker_units raises at command.py:866 before the loop "
    "body runs, while omitting victim raises at command.py:874 after map_lose_item "
    "already ran. Both answer HTTP 500 -- and the PERSISTED save is byte-identical "
    "in both cases, because command.py dispatches the whole batch first and calls "
    "save_session only afterwards (command.py:30,32), so an exception anywhere in "
    "the batch discards every mutation it made. MEASURED, including a two-command "
    "batch whose first command was valid: the branch printed its destruction and "
    "the persisted state did not move. The failure mode is therefore a DISCARDED "
    "save rather than a partially applied one, and the persistence boundary is the "
    "BATCH, not the command. Reproducing that ordering inside this endpoint is "
    "still refused: every check resolves before dispatch so a refusal can never "
    "leave a half-applied state, whatever a future persistence change does"
)

# ------------------------------------------------------ the divergence -----
DIVERGENCE_RECORD = {
    "status": "DIVERGENCE, NOT PARITY",
    "legacy_status": "the legacy server can destroy an ARBITRARY number of rows "
                     "from one request",
    "modern_status": "this operation destroys AT MOST ONE, derived server-side",
    "reason": CLIENT_DICTATED_REFUSAL,
    "recorded_not_narrowed": (
        "The divergence is recorded rather than narrowed, because narrowing it "
        "would require a combat rule the preserved source does not contain. The "
        "executed legacy capture measures the real difference against a committed "
        "village document and the fixture records it as a divergence field, so it "
        "cannot be reported as parity by omission"
    ),
    "unobserved_request_shape": (
        "Whether the real Flash client ever sent a MULTI-UNIT loss in one payload "
        "is never observed: the client was never executed. If it did, this "
        "operation under-delivers against it, and that is recorded as a claim "
        "limit rather than resolved"
    ),
}

#: The empty branch, delivered rather than refused (design D5).
KILL_IID_CONTRACT = {
    "command": KILL_IID_COMMAND,
    "source": "command.py:183-187",
    "local_bindings": ["item_id", "reason_str"],
    "statement_writes_save_state": False,
    "body": "print(\"Killed\", str(get_name_from_item_id(item_id)))",
    "mutates": [],
    "resources_move": False,
    "delivered": "as a proven no-op",
    "not_delivered": "as a refusal",
    "why": (
        "The branch WRITES NOTHING -- measured by every assignment target in "
        "its body being a bare Name and its only call being one print -- which "
        "is a stronger "
        "statement than any single observed request showing nothing changed. "
        "Refusing a command that does nothing would misrepresent the preserved "
        "server as having a rule to violate, and would leave a client with no "
        "verifiable behaviour to code against. Its INTENT is unknown: nothing "
        "observes whether a real client sent it, or what it was meant to do"
    ),
    "reaches_ledger": False,
}

#: ``kill`` deletes the row and never touches the ledger.
KILL_CONTRACT = {
    "command": KILL_COMMAND,
    "source": "command.py:169-181",
    "deletes_addressed_row": True,
    "reaches_ledger": False,
    "ledger_references": 0,
    "missing_row_behaviour": (
        "map_get_item's falsy branch prints 'Error: item not found.' and RETURNS, "
        "and the server still answers the legacy success result, so a client "
        "cannot distinguish this outcome from a real deletion by the response "
        "alone. This endpoint REFUSES it instead, which is a recorded divergence "
        "and not parity"
    ),
    "note": (
        "The ledger's non-participation is asserted as a property of the branch, "
        "not inferred from one request that happened not to change it: the branch "
        "contains no reference to privateState['deadHeroes'] and no call to "
        "push_dead_unit at all"
    ),
}

# ------------------------------------------------------------ provenance ----
PROVENANCE = {
    "capability": "godot-combat-actions",
    "milestone": "M10 line 2",
    "investigation": "docs/legacy-m10-combat.md (PR #288)",
    "design": "openspec/changes/combat-actions/design.md",
    "legacy_source": LEGACY_SOURCE_RELATIVE,
    "combat_branch": "%s (command.py:808-885)" % COMBAT_BRANCH,
    "kill_branch": "kill (command.py:169-181)",
    "kill_iid_branch": "kill_iid (command.py:183-187)",
    "row_removal_helper": "map_lose_item (engine.py:215-228)",
    "ledger_helper": "push_dead_unit (engine.py:149-170)",
    "ledger_fourth_door_owner": "godot-unit-behaviors",
    "quest_path_caller": "godot-quests",
    "interpretation": (
        "Every field inventory, fates, corpus figure, and ordering step in this "
        "module is RE-DERIVED from the committed legacy source and the committed "
        "content package on every verification run. Nothing is transcribed, so a "
        "legacy edit fails the guard instead of silently contradicting the record"
    ),
}

NON_CLAIMS = [
    "NO FLASH, RUFFLE, ACTIONSCRIPT, OR BROWSER EXECUTED. The executed-legacy "
    "capture drives the unchanged legacy Python server over loopback only.",
    "NO CLIENT-DICTATED DESTRUCTION COUNT IS REPRODUCED IN EITHER DIRECTION. The "
    "legacy server subtracts two client numbers; this operation destroys exactly "
    "one server-derived row and the difference is a DIVERGENCE, never parity.",
    "THE LEGACY BRANCH'S PRINTED LOSS COUNT IS NOT TREATED AS AN OUTCOME COUNT. "
    "It is printed before the row-removal call it appears to describe and is not "
    "conditional on it, so an identity with zero matching rows still printed it. "
    "It is evidence of what a client requested and of nothing else.",
    "NO DAMAGE, HEALTH, DEFENCE, HIT CHANCE, OR LIFE ARITHMETIC IS DELIVERED OR "
    "CLAIMED. attack, defense, life, attack_interval, attack_range, best_against, "
    "best_against_mult, and velocity each measure zero legacy consumers, so the "
    "committed numbers are content and never rules.",
    "NO MISSION IS DISPATCHED, RESOLVED, OR COMPLETED, and the mission vocabulary "
    "remains owned by godot-mission-vocabulary. No MISSION_* field is referenced "
    "anywhere in this line's delivered code.",
    "NO HONOUR OR REWARD IS PAID AND NO STORED RESOURCE MOVES. The committed blob "
    "keys are `honor` (US spelling), `resources`, "
    "resources_victim, and townhall_gold are read and discarded; the derived "
    "vector is neutral and the proof requires every stored resource unchanged.",
    "NO SYRINGE COST IS CHARGED, because the committed syringes field has zero "
    "legacy consumers.",
    "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED. That absence is "
    "reproduced, not filled, and is recorded as a Server v1 / M13 gap.",
    "THE TEAM ASYMMETRY between map_lose_item's truthy-team acceptance and "
    "push_dead_unit's team-one requirement is RECORDED AS A CODE FACT AND NOT "
    "EXERCISED, because no committed unit row is on a team other than one. It is "
    "not refused, which would invent a bound the oracle does not have.",
    "THE ITEM-KEYED KILL IS DELIVERED AS A PROVEN NO-OP, not as a refusal, and no "
    "replacement meaning is invented for it. Its intent is unknown.",
    "PARITY COVERS THE RECORDED TRANSACTIONS AGAINST THE COMMITTED VILLAGE "
    "DOCUMENTS ONLY, and no progressed-player save exists for this line beyond "
    "those two committed documents.",
    "NO WINDOWED CAPTURE AND NO PIXEL-PARITY ORACLE ARE CLAIMED, because nothing "
    "is rendered by this line.",
]

__all__ = [
    "ACTIONS",
    "ACTION_ADDRESSING",
    "COMBAT_PAYLOAD_KEY",
    "COMBAT_PAYLOAD_SHAPE",
    "DERIVED_REASON",
    "DERIVED_SENT",
    "DERIVED_SURVIVED",
    "DERIVED_UNKNOWN",
    "DERIVED_VICTIM_NAME",
    "ACTION_ADDRESSING_KEY",
    "ACTION_COMMAND",
    "ACTION_COUNT",
    "ACTION_KILL",
    "ACTION_KILL_IID",
    "ACTION_RESOLVE",
    "BRANCHES",
    "CLIENT_DICTATED_REFUSAL",
    "COMBAT_BRANCH",
    "CORPUS_CORRECTION",
    "DESTRUCTION_COUNT_KEYS",
    "DESTRUCTION_STEP",
    "DIVERGENCE_RECORD",
    "ENVELOPE_KEYS",
    "END_ATTACK_COMMAND",
    "EnvelopeError",
    "FATES",
    "FIELD_INVENTORY_CORRECTION",
    "GATES",
    "GATE_COUNT",
    "GATE_RESURRECTABLE",
    "GATE_TEAM_ONE",
    "KILL_COMMAND",
    "KILL_CONTRACT",
    "KILL_IID_COMMAND",
    "KILL_IID_CONTRACT",
    "LEDGER_KEY",
    "LEGACY_SOURCE_RELATIVE",
    "MAP_ROW_SLOTS",
    "NON_CLAIMS",
    "NO_COMBAT",
    "NO_COST_OR_REWARD",
    "NO_PLACEMENT_VALIDATION",
    "NO_SYRINGE_COST",
    "NO_THIRD_GATE",
    "ORDERING_RULE",
    "PLAYER_TEAM",
    "PRINTED_COUNT_IS_A_REQUEST",
    "PRIVATE_STATE_KEY",
    "PROPERTIES_FIELD",
    "PROVENANCE",
    "REASON_CLIENT_DICTATED_DESTRUCTION",
    "REASON_INVALID_ACTION",
    "REASON_INVALID_ITEM_ID",
    "REASON_INVALID_LEDGER",
    "REASON_INVALID_MAP_KEY",
    "REASON_INVALID_PAYLOAD",
    "REASON_INVALID_TIMESTAMP",
    "REASON_INVALID_VECTOR",
    "REASON_MISSING_ITEM_ID",
    "REASON_MISSING_MAP_KEY",
    "REASON_NO_ELIGIBLE_ROW",
    "REASON_UNADDRESSABLE_ROW",
    "REASON_UNKNOWN_ACTION",
    "REFUSED_COUNT_NOTE",
    "REFUSALS",
    "RESOURCE_NAMES",
    "RESOURCE_VECTOR_SLOTS",
    "RESURRECTABLE_FLAG",
    "SENT_SURVIVED_KEYS",
    "SLOT_ATTR",
    "SLOT_CELL_X",
    "SLOT_CELL_Y",
    "SLOT_ITEM_ID",
    "SLOT_PLAYER",
    "TEAM_ASYMMETRY",
    "VALIDATION_ORDER",
    "VALIDATION_ORDER_STEPS",
    "actions",
    "address_row",
    "branches",
    "build_envelope",
    "clear_derived_identity",
    "combat_payload",
    "committed_resurrectable",
    "conflicts",
    "derive_field_inventory",
    "expected_ledger_increment",
    "gates",
    "is_action",
    "is_item_id",
    "is_map_key",
    "neutral_vector",
    "project_combat",
    "project_ledger",
    "refused_client_keys",
    "refusals",
    "select_eligible_rows",
    "set_derived_identity",
    "team_asymmetry",
    "validation_order",
    "validate_vector",
]


# --------------------------------------------------------- the vocabulary ----
def actions() -> Tuple[str, ...]:
    """The closed action vocabulary, in committed order."""
    return ACTIONS


def is_action(value: Any) -> bool:
    """Whether ``value`` names an action this route dispatches.

    JSON delivers an exact string, and this route dispatches nothing else: a
    ``bytes`` value is refused because it cannot come from a request body and
    accepting it would widen the vocabulary to a second spelling of the same
    name.
    """
    return isinstance(value, str) and value in ACTIONS


def branches() -> List[Dict[str, Any]]:
    """The three delivered branches as fresh records a caller may mutate."""
    return [dict(record) for record in BRANCHES]


def gates() -> List[Dict[str, Any]]:
    """Both ledger gates, in the helper's own order, as fresh records."""
    return [dict(gate) for gate in GATES]


def refusals() -> List[Dict[str, Any]]:
    """The five recorded refusals as fresh records."""
    return [dict(entry) for entry in REFUSALS]


def validation_order() -> List[Dict[str, Any]]:
    """The validation ordering as fresh records."""
    return [dict(step) for step in VALIDATION_ORDER]


def team_asymmetry() -> Dict[str, Any]:
    """The recorded team asymmetry as a fresh record."""
    return json.loads(json.dumps(TEAM_ASYMMETRY))


def conflicts() -> Dict[str, Any]:
    """Both recorded-versus-measured correction blocks as fresh records."""
    return {
        "field_inventory": json.loads(json.dumps(FIELD_INVENTORY_CORRECTION)),
        "corpus": json.loads(json.dumps(CORPUS_CORRECTION)),
    }


# ------------------------------------------ the field inventory derivation --
def _strip_string_literals(line: str) -> str:
    """Replace every string literal with empty quotes.

    Two states, so an apostrophe inside a double-quoted string cannot end the
    scan early -- a one-pass regex desynchronised on exactly that and made three
    downstream scans vacuously true, which was found by measurement rather than
    by reading the code.
    """
    out: List[str] = []
    quote = ""
    for character in line:
        if quote:
            if character == "\\":
                continue
            if character == quote:
                quote = ""
                out.append('""')
            continue
        if character in ('"', "'"):
            quote = character
            continue
        out.append(character)
    return "".join(out)


def _branch_span(lines: Sequence[str], name: str) -> Tuple[int, int]:
    """The half-open line span of one ``cmd == "<name>"`` branch."""
    start: Optional[int] = None
    for index, line in enumerate(lines):
        match = _BRANCH_RE.match(line)
        if match is None:
            continue
        if match.group(1) != name:
            continue
        start = index
        break
    if start is None:
        raise EnvelopeError(
            REASON_INVALID_PAYLOAD,
            "the legacy source declares no %r dispatcher branch" % name,
        )
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _BRANCH_RE.match(lines[index]) is not None:
            end = index
            break
    return start, end


def _row_removal_region(lines: Sequence[str], span: Tuple[int, int]) -> Optional[Tuple[int, int]]:
    """The line span of the branch's only row-removal loop, or ``None``.

    Located by searching for the row-removal **call**, never by naming a key, so
    the mutation region is discovered rather than transcribed and a legacy edit
    that moved the loop still fails the guard.
    """
    call_line: Optional[int] = None
    for index in range(span[0], span[1]):
        if _ROW_REMOVAL_CALL in _strip_string_literals(lines[index]):
            call_line = index
            break
    if call_line is None:
        return None
    # Walk backwards to the enclosing ``for`` statement and forwards to the end of
    # its body, by indentation.
    for_start: Optional[int] = None
    for index in range(call_line, span[0] - 1, -1):
        if re.match(r"^\s*for\s+\w+\s+in\s+\w+:", lines[index]):
            for_start = index
            break
    if for_start is None:
        return None
    indent = len(lines[for_start]) - len(lines[for_start].lstrip())
    for_end = span[1]
    for index in range(for_start + 1, span[1]):
        stripped = lines[index].strip()
        if stripped == "":
            continue
        current = len(lines[index]) - len(lines[index].lstrip())
        if current <= indent:
            for_end = index
            break
    return for_start, for_end


def derive_field_inventory(source_text: Optional[str] = None) -> Dict[str, Any]:
    """Re-derive the combat request's field inventory from ``command.py`` bytes.

    Returns
        ``{ok, reason, error, source, branch, branch_span, keys, key_count,
        discarded, print_only, mutation_path, fates, partition, correction,
        row_removal_region}``

    **Nothing here is transcribed.**  The keys are the branch's own
    ``if "<key>" in response:`` tests, read as bytes; the mutation region is the
    branch's only row-removal loop, found by searching for the call; and
    ``discarded`` is every key with no occurrence after the membership-test block,
    quote-stripped so neither a comment nor the assignment that transports the
    value can count as a use.  ``print_only`` is derived as the complement, and
    the three-way partition is asserted, so a key that fits none of them fails
    here instead of being quietly filed under one.

    This function reads no file unless ``source_text`` is omitted, in which case
    it reads the committed ``command.py`` bytes -- so an offline caller may hand
    it any text at all, which is what makes the drift guard testable by
    injection.
    """
    header: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "source": LEGACY_SOURCE_RELATIVE,
        "branch": COMBAT_BRANCH,
        "branch_span": None,
        "keys": [],
        "key_count": 0,
        "discarded": [],
        "print_only": [],
        "mutation_path": [],
        "fates": list(FATES),
        "partition": False,
        "correction": json.loads(json.dumps(FIELD_INVENTORY_CORRECTION)),
        "row_removal_region": None,
    }
    if source_text is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            LEGACY_SOURCE_RELATIVE,
        )
        try:
            with open(path, "rb") as handle:
                source_text = handle.read().decode("utf-8")
        except OSError as error:
            header["reason"] = REASON_INVALID_PAYLOAD
            header["error"] = "cannot read %s: %s" % (LEGACY_SOURCE_RELATIVE, error)
            return header
    lines = source_text.split("\n")
    try:
        span = _branch_span(lines, COMBAT_BRANCH)
    except EnvelopeError as failure:
        header["reason"] = failure.code
        header["error"] = str(failure)
        return header
    header["branch_span"] = [span[0] + 1, span[1]]

    # The read keys, in committed file order, each with the line its own
    # membership test declares it on, and the end of the block that transports
    # them.  Both are collected in ONE pass, so the recorded declaration line can
    # never disagree with the key list it accompanies.
    keys: List[str] = []
    declared: Dict[str, int] = {}
    block_end = span[0]
    for index in range(span[0], span[1]):
        match = _MEMBERSHIP_RE.match(lines[index])
        if match is None:
            continue
        if match.group(1) not in keys:
            keys.append(match.group(1))
            declared[match.group(1)] = index + 1
        block_end = index + 1
    # The membership block is NOT finished at its last membership test: each test
    # is followed by the line that transports the value out of the blob, and that
    # transport is not a use either.  Measured, not assumed: stopping at the last
    # test filed `resources_victim` as print-only on the strength of its OWN
    # assignment line and undercounted the discarded set by one.
    #
    # The discriminator is a subscript of `response` -- quote-stripped, so it is
    # the transport form rather than any particular key name.  Scanning forward
    # while it holds stops at the first line that does not transport from the blob,
    # which is the blank/comment line before the branch's first real use.
    while block_end < span[1] and "response[" in _strip_string_literals(lines[block_end]):
        block_end += 1
    if not keys:
        header["reason"] = REASON_INVALID_PAYLOAD
        header["error"] = "the %s branch reads no client keys" % COMBAT_BRANCH
        return header

    region = _row_removal_region(lines, span)
    header["row_removal_region"] = None if region is None else [region[0] + 1, region[1]]

    mutation: List[str] = []
    printing: List[str] = []
    discarded: List[str] = []
    records: List[Dict[str, Any]] = []
    for key in keys:
        sites: List[int] = []
        in_region = False
        pattern = re.compile(r"\b%s\b" % re.escape(key))
        for index in range(block_end, span[1]):
            if not pattern.search(_strip_string_literals(lines[index])):
                continue
            sites.append(index)
            if region is not None and region[0] <= index < region[1]:
                in_region = True
        if not sites:
            fate = _FATE_DISCARDED
            discarded.append(key)
        elif in_region:
            fate = _FATE_MUTATION
            mutation.append(key)
        else:
            # Derived as the complement of the two sets above. The three-way
            # partition asserted below is what keeps this honest.
            fate = _FATE_PRINT
            printing.append(key)
        records.append(
            {
                "key": key,
                "fate": fate,
                # The line this key's own membership test is declared on, and the
                # lines its name occurs on afterwards.  The two are reported
                # separately and never conflated: a declaration is not a use, which
                # is precisely how a discarded key would look if they were merged.
                "tested_at": "command.py:%d" % declared[key],
                "post_test_sites": ["command.py:%d" % (site + 1) for site in sites],
                "post_test_site_count": len(sites),
                "post_test_distinct_lines": len(set(sites)),
                "inside_row_removal_region": in_region,
            }
        )
    partition = sorted(discarded + printing + mutation) == sorted(keys)
    header.update(
        {
            "ok": True,
            "reason": "",
            "error": "",
            "keys": records,
            "key_count": len(keys),
            "key_names": list(keys),
            "discarded": discarded,
            "print_only": printing,
            "mutation_path": mutation,
            "partition": partition,
        }
    )
    return header


# --------------------------------------------------------- the derived set --
def is_item_id(value: Any) -> bool:
    """Whether ``value`` is a strict integer item id.

    A ``bool`` is an ``int`` in Python and would address item 1 or 0; a float and
    a string are refused outright, because legacy's own ``row[0] == item``
    comparison never matched either.
    """
    return is_strict_int(value)


def is_map_key(value: Any) -> bool:
    """Whether ``value`` is a strict integer map key."""
    return is_strict_int(value)


def select_eligible_rows(items: Any, item_id: Any) -> Dict[str, Any]:
    """The rows ``map_lose_item`` would consider, in the order it would pop them.

    Returns
        ``{ok, reason, error, item_id, eligible_keys, eligible_count, addressed,
        addressed_row, truthy_team_only}``

    Eligibility is exactly the two conditions ``map_lose_item`` tests
    (``engine.py:221``): the row's recorded slot 0 equals the item id **and** the
    row's recorded slot 7 is **truthy**.  The addressed row is the **first**
    eligible row in the save's own recorded map-key order, which is the iteration
    order ``for index in map_items`` walks and therefore the order it pops.

    A row that is not an 8-slot row is never eligible, so a malformed row can
    neither be destroyed nor be counted as a candidate.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "item_id": item_id,
        "eligible_keys": [],
        "eligible_count": 0,
        "addressed": False,
        "addressed_key": None,
        "addressed_row": None,
        "truthy_team_only": True,
    }
    if not is_item_id(item_id):
        out["reason"] = REASON_INVALID_ITEM_ID
        out["error"] = "item_id must be an integer, got %s" % type(item_id).__name__
        return out
    if not isinstance(items, Mapping):
        out["reason"] = REASON_INVALID_PAYLOAD
        out["error"] = "the player's placements are %s, not an object" % type(
            items
        ).__name__
        return out
    matches: List[str] = []
    for key in items:
        row = items[key]
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            continue
        if len(row) != MAP_ROW_SLOTS:
            continue
        if row[SLOT_ITEM_ID] != int(item_id):
            continue
        if not row[SLOT_PLAYER]:
            continue
        matches.append(str(key))
    out["eligible_keys"] = matches
    out["eligible_count"] = len(matches)
    if not matches:
        out["reason"] = REASON_NO_ELIGIBLE_ROW
        out["error"] = (
            "no placed row records item id %d on a truthy team: map_lose_item "
            "matches a row only when its slot 0 equals the item id AND its slot 7 "
            "is truthy (engine.py:221), so there is nothing this identity can "
            "destroy" % int(item_id)
        )
        return out
    key = matches[0]
    out.update(
        {
            "ok": True,
            "reason": "",
            "error": "",
            "addressed": True,
            "addressed_key": key,
            "addressed_row": list(items[key]),
        }
    )
    return out


def address_row(items: Any, map_key: Any) -> Dict[str, Any]:
    """Resolve an addressed map key to its placed row, or refuse it.

    Returns
        ``{ok, reason, error, map_key, row, addressed}``

    ``kill`` looks the row up with ``map_get_item``, whose falsy branch prints and
    returns while the server still answers success (``command.py:173-176``).  This
    refuses it instead, which is a recorded divergence and not parity.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "map_key": map_key,
        "row": None,
        "addressed": False,
    }
    if not is_map_key(map_key):
        out["reason"] = REASON_INVALID_MAP_KEY
        out["error"] = "map_key must be an integer, got %s" % type(map_key).__name__
        return out
    if not isinstance(items, Mapping):
        out["reason"] = REASON_INVALID_PAYLOAD
        out["error"] = "the player's placements are %s, not an object" % type(
            items
        ).__name__
        return out
    key = str(int(map_key))
    row = items.get(key)
    if row is None:
        out["reason"] = REASON_UNADDRESSABLE_ROW
        out["error"] = (
            "no placed row stands at map key %s: the legacy kill branch prints "
            "'Error: item not found.' and returns without any change while the "
            "server still answers success (command.py:173-176), which this "
            "endpoint refuses instead of reproducing" % key
        )
        return out
    out.update(
        {"ok": True, "reason": "", "error": "", "row": list(row), "addressed": True}
    )
    return out


def project_ledger(raw: Any) -> Dict[str, Any]:
    """The **read-only** projection of ``privateState['deadHeroes']``, verbatim.

    Imported unchanged from :mod:`behavior_envelope` rather than reimplemented,
    so the ledger's projection exists in exactly one place across the delivered
    code and this line's proof cannot drift from ``godot-unit-behaviors``'s.
    """
    from behavior_envelope import project_ledger as project  # local: cycle-free

    return project(raw)


def committed_resurrectable(properties: Any) -> Optional[int]:
    """One committed definition's ``properties.resurrectable``, or ``None``.

    Imported unchanged from :mod:`behavior_envelope`, which documents the R2
    coercion boundary: the legacy helper reads the **raw configuration string**
    through ``json.loads`` (``engine.py:154-162``) while the committed normalized
    package stores ``properties`` as an **object``, and a committed flag is a
    *string*, so an explicit conversion is the only correct read.
    """
    from behavior_envelope import committed_resurrectable as read  # local

    return read(properties)


def expected_ledger_increment(
    ledger: Any, item_id: Any, team: Any, flag: Any
) -> Dict[str, Any]:
    """The ledger ``push_dead_unit`` leaves behind, or proof it wrote nothing.

    Reproduces ``engine.push_dead_unit`` (``engine.py:149-170``) exactly:

    * the row must be on **player team 1** (``engine.py:151``) -- any other team
      returns ``False`` and the ledger is untouched, even though
      ``map_lose_item`` destroyed the row (design D7);
    * the committed ``properties`` must carry ``resurrectable`` at all
      (``engine.py:159``), so an **absent** flag is a refusal and never a zero;
    * and it must be **greater than zero** (``engine.py:162``);
    * when both gates hold the count **increments by one**, creating the key at
      ``1`` when it is absent (``engine.py:164-167``).

    The surviving entries keep their recorded **string** keys and their recorded
    insertion order, so a comparison against the persisted ledger is a value
    comparison rather than a re-ordering.
    """
    projection = project_ledger(ledger)
    if not bool(projection.get("ok", False)):
        raise EnvelopeError(
            REASON_INVALID_LEDGER, str(projection.get("error", ""))
        )
    if not is_item_id(item_id):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "item_id must be an integer, got %s" % type(item_id).__name__,
        )
    key = str(int(item_id))
    entries: Dict[str, int] = {}
    for entry in projection["entries"]:  # type: ignore[union-attr]
        entries[str(entry["item_id"])] = int(entry["count"])

    team_one = team == PLAYER_TEAM
    # ``None`` is the ABSENT flag, which the helper treats as a refusal
    # (``engine.py:159``) rather than a zero -- so it is checked before the type
    # rule, which exists only to keep a ``bool`` or a container out of ``int``.
    flag_present = flag is not None
    if flag_present and (isinstance(flag, bool) or not isinstance(flag, (int, str))):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "the committed resurrectable flag must be read as an integer or its "
            "string form, got %s" % type(flag).__name__,
        )
    flag_positive = False
    if flag_present:
        try:
            flag_positive = int(flag) > 0
        except ValueError:
            raise EnvelopeError(
                REASON_INVALID_ITEM_ID,
                "the committed resurrectable flag %r is not an integer" % (flag,),
            )
    written = bool(team_one and flag_positive)
    before = entries.get(key, 0)
    present = key in entries
    after = before + 1 if written else before
    if written:
        entries[key] = after
    return {
        "entries": entries,
        "written": written,
        "present_before": present,
        "count_before": before,
        "count_after": after,
        "item_id": key,
        "gates": {
            "player_team_one": {
                "recorded_team": team,
                "required": PLAYER_TEAM,
                "holds": bool(team_one),
            },
            "resurrectable_positive": {
                "recorded_flag": flag,
                "present": bool(flag_present),
                "positive": bool(flag_positive),
                "holds": bool(flag_positive),
            },
        },
    }


# ------------------------------------------------------- the request shape --
def refused_client_keys(payload: Any, inventory: Optional[Sequence[str]] = None) -> List[str]:
    """Every client key this route REFUSES, in sorted order.

    Three families, all refused before dispatch (design D2):

    1. a **destruction count** -- ``lost``, ``losses``, ``destroyed``, and their
       siblings;
    2. the two **subtraction operands** the legacy count is computed from --
       ``sent`` and ``survived``;
    3. the **legacy payload key** itself -- any of the keys ``end_attack`` reads.

    The third family is built from the derived inventory, so it tracks a legacy
    edit instead of drifting from it.  When the inventory cannot be derived the
    derived set is empty and only the first two families are refused, which is
    reported rather than silently widened.
    """
    if not isinstance(payload, Mapping):
        return []
    derived = set(inventory or ())
    refused: List[str] = []
    for key in payload:
        name = str(key)
        if name in DESTRUCTION_COUNT_KEYS or name in SENT_SURVIVED_KEYS:
            refused.append(name)
            continue
        if name in derived:
            refused.append(name)
    return sorted(set(refused))


# -------------------------------------------------------- derived vector ----
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed``.

    No combat branch writes a resource, and any delta a client attached would be a
    client-trusted mint or burn because ``do_command`` applies the request's
    vector *before* the branch (``command.py:40``, ``engine.apply_resources``,
    ``engine.py:251-271``).  A fresh list is returned on every call so a caller
    cannot mutate the derivation for the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal.  Refusing anything else is what
    forecloses smuggling: the derivation cannot express it, so the endpoint cannot
    send it.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            REASON_INVALID_VECTOR,
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                REASON_INVALID_VECTOR,
                "resources_changed slot %d must be an integer, got %r"
                % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                REASON_INVALID_VECTOR,
                "resources_changed slot %d is %r: a combat action moves no "
                "resource, so only the neutral all-zero vector is derivable"
                % (index, value),
            )
    return list(vector)


# ------------------------------------------------------- the projection -----
def project_combat(
    items: Any,
    ledger: Any,
    action: Any,
    addressing: Any,
    item_of: Any,
    inventory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The whole read-only projection of one combat intent, or its refusal.

    Every check in :data:`VALIDATION_ORDER` runs **here**, before the endpoint
    dispatches anything, which is what makes a refused request leave the recorded
    document byte-identical (design D3).  ``item_of`` is a callable taking an
    **item id** and returning that item's committed configuration row (or
    ``None``), so this module reads committed content through a parameter and
    never resolves it itself.

    ``inventory`` is an already-derived field inventory, passed in so the
    endpoint can refuse the D2 client keys and project from **one** derivation
    rather than two independent reads of ``command.py``.  ``None`` derives it
    here, so an offline caller need not thread it through.

    Returns
        ``{ok, reason, error, action, command, addressing_key, addressing,
        addressing_kind, eligible, addressed_row, ledger_before, ledger_after,
        destruction, ledger_written, gates, resource_delta, inventory}``
    """
    if inventory is None:
        inventory = derive_field_inventory()
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "action": action,
        "command": None,
        "addressing_key": None,
        "addressing": addressing,
        "addressing_kind": "",
        "eligible": None,
        "addressed_row": None,
        "ledger_before": None,
        "ledger_after": None,
        "destruction": 0,
        "ledger_written": False,
        "gates": gates(),
        "resource_delta": neutral_vector(),
        "inventory": inventory,
        "ordering_rule": ORDERING_RULE,
        "validation_order": validation_order(),
    }
    if not is_action(action):
        out["reason"] = REASON_INVALID_ACTION
        out["error"] = "action must be one of %s, got %r" % (
            ", ".join(ACTIONS), action
        )
        return out
    out["command"] = ACTION_COMMAND[str(action)]
    out["addressing_key"] = ACTION_ADDRESSING_KEY[str(action)]
    out["addressing_kind"] = ACTION_ADDRESSING[str(action)]

    # --- step 3: the addressing is well typed ------------------------------
    if str(action) == ACTION_KILL:
        if not is_map_key(addressing):
            out["reason"] = REASON_INVALID_MAP_KEY
            out["error"] = "map_key must be an integer, got %r" % (addressing,)
            return out
    else:
        if not is_item_id(addressing):
            out["reason"] = REASON_INVALID_ITEM_ID
            out["error"] = "item_id must be an integer, got %r" % (addressing,)
            return out

    # --- the ledger is read before anything is destroyed --------------------
    ledger_projection = project_ledger(ledger)
    out["ledger_before"] = ledger_projection
    if not bool(ledger_projection.get("ok", False)):
        out["reason"] = REASON_INVALID_LEDGER
        out["error"] = str(ledger_projection.get("error", ""))
        return out

    if str(action) == ACTION_KILL:
        # --- steps 4/5: the addressed row resolves --------------------------
        resolved = address_row(items, addressing)
        if not bool(resolved.get("ok", False)):
            out["reason"] = str(resolved.get("reason", ""))
            out["error"] = str(resolved.get("error", ""))
            return out
        out["addressed_row"] = resolved.get("row")
        out["eligible"] = {
            "ok": True,
            "reason": "",
            "error": "",
            "item_id": int(addressing),
            "eligible_keys": [str(addressing)],
            "eligible_count": 1,
            "addressed": True,
            "addressed_key": str(addressing),
            "addressed_row": resolved.get("row"),
        }
        # --- `kill` NEVER touches the ledger (design D5) ---------------------
        out.update(
            {
                "ok": True,
                "reason": "",
                "error": "",
                "destruction": 1,
                "ledger_written": False,
                "ledger_after": {
                    "entries": {
                        str(entry["item_id"]): int(entry["count"])
                        for entry in ledger_projection["entries"]  # type: ignore[index]
                    },
                    "written": False,
                    "item_id": None,
                    "note": "the kill branch holds no reference to "
                            "privateState['deadHeroes'] and no call to "
                            "push_dead_unit, so no ledger change is derived for "
                            "it at all",
                },
            }
        )
        return out

    if str(action) == ACTION_KILL_IID:
        # --- design D5: a proven no-op, delivered rather than refused -------
        out.update(
            {
                "ok": True,
                "reason": "",
                "error": "",
                "destruction": 0,
                "ledger_written": False,
                "ledger_after": {
                    "entries": {
                        str(entry["item_id"]): int(entry["count"])
                        for entry in ledger_projection["entries"]  # type: ignore[index]
                    },
                    "written": False,
                    "item_id": None,
                    "note": "the branch writes nothing -- every assignment "
                            "target in its body is a bare Name and its only call "
                            "is one print -- so no "
                            "ledger change is derived for it at all",
                },
            }
        )
        return out

    # --- step 4: an eligible row resolves ----------------------------------
    eligible = select_eligible_rows(items, addressing)
    out["eligible"] = eligible
    if not bool(eligible.get("ok", False)):
        out["reason"] = str(eligible.get("reason", ""))
        out["error"] = str(eligible.get("error", ""))
        return out
    row = eligible.get("addressed_row") or []
    out["addressed_row"] = row

    # --- steps 6/7: the ledger increment, behind BOTH gates and no third ----
    committed = item_of(int(row[SLOT_ITEM_ID]))
    flag = committed_resurrectable(
        committed.get(PROPERTIES_FIELD) if isinstance(committed, Mapping) else None
    )
    try:
        derived = expected_ledger_increment(ledger, addressing, row[SLOT_PLAYER], flag)
    except EnvelopeError as failure:
        out["reason"] = failure.code
        out["error"] = str(failure)
        return out
    out["ledger_after"] = derived
    out["ledger_written"] = bool(derived["written"])
    out["committed_resurrectable"] = flag
    out.update(
        {
            "ok": True,
            "reason": "",
            "error": "",
            # ALWAYS ONE. Never a count, never a loop, never a clamp.
            "destruction": 1,
        }
    )
    return out


# ------------------------------------------------------------ the envelope --
def build_envelope(
    action: Any,
    addressing: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one combat intent.

    The command and its argument list are **derived**: a client supplies an
    intent, and this function turns that intent into the exact legacy batch the
    preserved dispatcher understands.  The resource vector is the validated
    **neutral** one, because no combat branch writes a resource.

    ``kill``'s argument list is ``[map_key, reason]`` and ``kill_iid``'s is
    ``[item_id, reason]`` (``command.py:170-171`` and ``184-185``); both take a
    reason the branch binds to a local and uses **only inside a print**
    (``command.py:181`` and ``187``), so the derived reason is a recorded
    derived-provisional placeholder and is never trusted for behaviour.
    ``end_attack``'s argument list is ``[payload, unknown]`` (``command.py:810``
    and ``813``), where ``args[1]`` is bound to ``unknown`` and **never used**.

    Whether an eligible row exists, whether the addressed key resolves, and
    whether both ledger gates hold are all resolved by :func:`project_combat`
    **before** this is called -- this function validates shape only.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(ACTIONS), action),
        )
    name = str(action)
    checked = validate_vector(neutral_vector())
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError(
            REASON_INVALID_TIMESTAMP, "ts must be a non-negative integer"
        )
    if name == ACTION_KILL:
        if not is_map_key(addressing):
            raise EnvelopeError(
                REASON_INVALID_MAP_KEY,
                "map_key must be an integer, got %s" % type(addressing).__name__,
            )
        arguments: List[Any] = [int(addressing), DERIVED_REASON]
    elif name == ACTION_KILL_IID:
        if not is_item_id(addressing):
            raise EnvelopeError(
                REASON_INVALID_ITEM_ID,
                "item_id must be an integer, got %s" % type(addressing).__name__,
            )
        arguments = [int(addressing), DERIVED_REASON]
    else:
        if not is_item_id(addressing):
            raise EnvelopeError(
                REASON_INVALID_ITEM_ID,
                "item_id must be an integer, got %s" % type(addressing).__name__,
            )
        arguments = [combat_payload(str(action)), DERIVED_UNKNOWN]
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, ACTION_COMMAND[name], arguments, checked]],
    }


#: The derived reason the two kill branches receive.  Both bind it to a local
#: and use it only inside an f-string (``command.py:181`` and ``187``), so it has
#: no stored effect; the choice of ``0`` changes nothing and is recorded as a
#: derivation, never an observation.
DERIVED_REASON = 0

#: ``end_attack``'s ``args[1]``, bound to the local ``unknown`` and **never used**
#: anywhere in the branch (``command.py:810``).
DERIVED_UNKNOWN = 0

#: The client blob ``end_attack`` parses from ``args[0]`` (``command.py:813``).
#: It is derived from the request's own intent and carries exactly one entry --
#: the lost unit's identity -- so the branch's destruction loop iterates once and
#: the ``lost`` arithmetic is fed a pair the server itself wrote.
COMBAT_PAYLOAD_KEY = "attacker_units"
COMBAT_PAYLOAD_SHAPE = "derived"


def combat_payload(action: str = ACTION_RESOLVE) -> str:
    """The derived client blob ``end_attack`` parses, as its JSON text.

    The blob carries **exactly one** key, the branch's own ``attacker_units``,
    holding **one** tuple of four integers.  The tuple is the legacy tuple shape
    ``[item_id, sent_to_battle, A, B]`` (``command.py:867``), and it is built so
    the branch's own arithmetic yields exactly the **one** destruction this
    operation derives: ``A = 1`` and ``B = 0`` give
    ``max(0, 1 - 0) == 1``.

    Every other key the branch reads is **absent**, so each keeps its own
    ``None``/``False`` default and contributes nothing -- which is what makes
    "the destroyed set is server-derived" a property of the bytes on the wire
    rather than a promise.  ``victim`` is supplied as a name record so the
    branch's ``if "name" in victim`` (``command.py:874``) does not raise on a
    ``None``; that member is read only by the branch's final ``print``.

    Nothing here is client-supplied.  The identity inside the tuple is the
    addressing value :func:`project_combat` already resolved, so the wire bytes
    carry the server's own derivation and never a client number.
    """
    if not is_action(action):
        raise EnvelopeError(REASON_INVALID_ACTION, "unknown action %r" % (action,))
    if str(action) == ACTION_KILL:
        raise EnvelopeError(
            REASON_INVALID_ACTION, "kill does not dispatch a client blob"
        )
    return payload_json(
        {
            COMBAT_PAYLOAD_KEY: [
                [int(_DERIVED_IDENTITY), 0, DERIVED_SENT, DERIVED_SURVIVED]
            ],
            "victim": {"name": DERIVED_VICTIM_NAME},
        }
    )


#: The identity the derived blob's single tuple carries.  ``project_combat``
#: sets it before :func:`combat_payload` is called; it is a module global rather
#: than a parameter so the legacy branch's own ``json.loads`` sees the value
#: without this module having to thread it through the envelope builder twice.
#: It is reset by :func:`clear_derived_identity` on every call site, and the
#: projection asserts it was set.
_DERIVED_IDENTITY = 0

#: The two operands of the branch's subtraction, **derived** so that
#: ``max(0, sent - survived)`` is exactly the one destruction this operation
#: derives.  This is the opposite of trusting a client pair: the server writes
#: both ends of the subtraction itself, from its own selection.
DERIVED_SENT = 1
DERIVED_SURVIVED = 0

#: The victim name the derived blob carries, so the branch's final print has a
#: name to read.  It is never stored and never reaches a resource.
DERIVED_VICTIM_NAME = "derived"


def set_derived_identity(item_id: Any) -> None:
    """Record the identity the derived blob's single tuple will carry."""
    global _DERIVED_IDENTITY
    if not is_item_id(item_id):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "item_id must be an integer, got %s" % type(item_id).__name__,
        )
    _DERIVED_IDENTITY = int(item_id)


def clear_derived_identity() -> None:
    """Reset the derived identity, so no stale value can reach the wire."""
    global _DERIVED_IDENTITY
    _DERIVED_IDENTITY = 0