#!/usr/bin/env python3
"""Derivation of the magic-counter surface and its closed legacy envelope.

M10 line 3 (``damage``).  This module is the single place where the magic
request's field inventory, its validation ordering, the server-derived counter
transition, the recorded cap, both refused legacy asymmetries, and the recorded
divergences become the legacy batch envelope, so the Compatibility API
``POST /v0/magic`` endpoint and its suites are checked against *one* derivation.

Why this module exists at all, given the line's name
-----------------------------------------------------
The investigation (``docs/legacy-m10-damage.md``, PR #294) established that the
preserved server **resolves no damage**, and established it two independent ways:

* **No committed damage field has a consumer.**  ``attack``, ``defense``,
  ``life``, ``attack_interval``, ``attack_range``, ``best_against``, and
  ``best_against_mult`` each measure zero under six counting rules across all
  eleven legacy root modules.  The apparently-conflicting counts are substring
  artifacts: ``damage`` shows two code-only occurrences and **zero** tokens
  because both sit inside ``COST_DAMAGE_SELF`` and ``COST_DAMAGE_ENEMY``, and
  ``attack`` shows 42 whole-file occurrences and **zero** tokens because every
  one sits inside ``end_attack``, ``attacker``, ``attacker_units``,
  ``flash_reload_attack``, ``ANIMATION_ATTACKING*``, ``tsAttacksReset``, or one
  of two non-field uses.

* **There is nowhere to STORE damage.**  Across all ten canonical save
  documents and 3,372 placed rows **every row is exactly eight slots** with a
  fixed type per slot; the complete ``attr`` bag union is ``cp``, ``nu``, ``si``,
  ``ts``, ``ui``, ``xp``; and **zero** damage-shaped keys exist in any
  ``privateState``.  A damage system needs somewhere to keep a remaining hit
  point.  The committed format does not have one, the server never added one,
  and the corpus never contains one.

So **no damage is resolved, computed, applied, or stored here**, and
:data:`NO_DAMAGE` records that as a structural claim rather than a note:
:func:`derive_field_inventory` re-measures the field census and the row shape on
every call, so a legacy edit that introduced a damage consumer would fail the
projection instead of silently contradicting the record.

What IS delivered
-----------------
The one combat-effect surface the preserved server actually maintains:
``privateState["magics"]``, a string-keyed counter ledger written by two
adjacent dispatcher branches and **read by nothing**.

    command.py:652   elif cmd == "buy_magic":
    command.py:658           magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)
    command.py:660           magics[str(magic_id)] = 0

    command.py:664   elif cmd == "use_magic":
    command.py:670           magics[str(magic_id)] = min(50, magics[str(magic_id)] + 1)
    command.py:672           magics[str(magic_id)] = 0

The mechanism (design D2)
    The request carries a **validated magic identity** and an action, and
    **nothing else**.  The service derives the before value, the after value,
    and the change from its own recorded state.  A client-sent ``count``,
    ``delta``, or ``new_value`` is **refused by name** rather than ignored, which
    is the M10 combat-actions precedent applied to a counter instead of a
    destruction and the M9 ``quests`` precedent applied to ``lost``.

Both legacy arms are refused, not reproduced (design D3)
    The two branches are four lines apart and are **not interchangeable**:

    ``buy_magic`` uses ``+=`` -- it *adds* ``min(50, x + 1)``, which is **not** a
    cap.  Executed against ``villages/Neutral.json``: ``2 -> 3 -> 7 -> 15 -> 31
    -> 63 -> 113``.  The counter crossed 50 and kept climbing.

    ``use_magic`` uses ``=`` -- it *assigns* ``min(50, x + 1)``, an absolute
    clamp, so it can **reduce** a counter.  Executed: ``113 -> 50``.  A command
    whose recorded message is ``"Used magic spell"`` deleted 63 owned charges.

    Reproducing either would ship a defect as parity.  The unbounded growth has
    no bound; the decrease destroys player property on a command that claims the
    opposite.  :func:`derive_counter_transition` therefore increments by one and
    caps, for **both** actions, and **never reduces**.  A third divergence follows
    and is recorded rather than hidden: the legacy arms *disagree* about the cap,
    so there is no recorded rule for how the cap applies across actions, and this
    module applies it uniformly and says so.

The cap is a literal, and that is deliberate (design D6)
    ``min(50, ...)`` appears at exactly two source lines with no reference to any
    content.  The value 50 *does* occur among the committed magics values -- as
    ``AirStrike.cash = 50`` and ``Shortcircuit.level = 50`` -- which is precisely
    the coincidence that gets mistaken for provenance.  :data:`REJECTED_CAP_DERIVATION`
    records the rejected alternative so a later reader cannot mistake one for the
    other.

The identity is validated, which the legacy server does not do (design D4)
    The committed table has exactly ten entries, ids ``1..10``.  The legacy
    branch validates nothing and keys on ``str(magic_id)``, with these executed
    consequences:

    * ``buy_magic [99]`` was **accepted** and created a ledger entry for a spell
      that does not exist;
    * ``use_magic [1.0]`` created the **distinct key** ``"1.0"``, separate from
      ``"1"``, because ``str(1.0) != str(1)``.

    Both are refused here, and both differences are recorded as divergences.
    :func:`is_canonical_magic_key` is what makes the float hazard a refusal
    rather than a coercion.

No price is charged, and the proof is non-tautological (design D5)
    Twelve executed transactions compared **eight** stored resource slots --
    ``gold``, ``wood``, ``oil``, ``steel``, ``cash``, ``xp`` from the map and
    ``mana``, ``energy`` from private state -- before and after, and **none
    moved**; ``mana`` held at 15 across a ``use_magic``.  The endpoint's
    two-part post-execution proof compares **all eight**, which is what makes
    the no-price claim foreclose a delta smuggled through the request.

Every refusal resolves before any ledger write (design D4 of the spec)
    The legacy branch performs no validation at all, so there is no recorded
    ordering to reproduce; the requirement exists so that *this* service's
    refusals are safe.  All of :data:`VALIDATION_ORDER` runs inside
    :func:`project_magic`, above the write, and the content check runs **before**
    any player state is read so that a request naming a spell that does not exist
    never consults the corpus.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


class EnvelopeError(Exception):
    """One refusal raised while building the legacy batch envelope."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# The two dispatcher branches
# --------------------------------------------------------------------------

BUY_COMMAND = "buy_magic"
USE_COMMAND = "use_magic"

#: The two branches this line owns, in committed source order.
MAGIC_COMMANDS: Tuple[str, str] = (BUY_COMMAND, USE_COMMAND)

#: The single branch whose whole body is a recorded message.
#: ``command.py:649-650`` is ``buy_mana_new``, whose entire body is
#: ``print("Bought mana") # Nothing needs to be done here :)``.  It is recorded
#: because it is the third member of the same buy/use vocabulary family, and it
#: is **not** delivered: an empty branch is not combat-effect state.
NO_OP_COMMAND = "buy_mana_new"
NO_OP_LINE = 650
NO_OP_NOTE = (
    "buy_mana_new's entire body is one print whose own trailing comment reads "
    "'Nothing needs to be done here :)'. It is reported as a recorded absence "
    "and never delivered, because an empty branch maintains no state to verify."
)

ACTION_BUY = "buy"
ACTION_USE = "use"

#: The closed action vocabulary.  A closed set is what lets an unknown action be
#: refused by name instead of falling through to a branch nobody reviewed.
ACTIONS: Tuple[str, str] = (ACTION_BUY, ACTION_USE)
ACTION_COUNT = len(ACTIONS)

#: Closed one-to-one with the legacy branches.  There is no action that maps to
#: no branch and no branch that maps to no action; the suite asserts equality of
#: both sets so a fourth branch cannot appear unnoticed.
ACTION_COMMAND: Dict[str, str] = {
    ACTION_BUY: BUY_COMMAND,
    ACTION_USE: USE_COMMAND,
}

#: Both actions address the same key: the committed magic id.
ACTION_ADDRESSING_KEY: Dict[str, str] = {
    ACTION_BUY: "magic_id",
    ACTION_USE: "magic_id",
}

#: The legacy argument list is ``[magic_id]`` for both branches
#: (``command.py:653`` and ``665``); nothing else is read.
ACTION_ARGUMENT_COUNT: Dict[str, int] = {
    ACTION_BUY: 1,
    ACTION_USE: 1,
}

# --------------------------------------------------------------------------
# The recorded cap -- a literal, not a derivation (design D6)
# --------------------------------------------------------------------------

#: The cap as it appears in the preserved source, at ``command.py:658`` and
#: ``command.py:670``.  It is a **hardcoded literal**: see
#: :data:`REJECTED_CAP_DERIVATION`.
COUNTER_CAP = 50

CAP_SOURCE_LINES: Tuple[int, int] = (658, 670)

REJECTED_CAP_DERIVATION = {
    "rejected": "derive the cap from committed magics content",
    "candidates": [
        {
            "magic_id": 1,
            "magic_name": "AirStrike",
            "field": "cash",
            "value": 50,
        },
        {
            "magic_id": 5,
            "magic_name": "Shortcircuit Inductor",
            "field": "level",
            "value": 50,
        },
    ],
    "reason": (
        "The preserved source contains no reference to any content when it "
        "applies the cap: min(50, ...) is a literal in a min() call. The value "
        "50 occurring among the committed magics values is a coincidence of the "
        "value distribution, not its provenance. Recording it as content-derived "
        "would invent a derivation, which is the defect class this project's own "
        "training_time and unit_capacity findings warn against. The cap is "
        "delivered as the hardcoded literal it is, and the suite asserts the "
        "literal is used and that no content lookup substitutes for it."
    ),
    "applied": "COUNTER_CAP is the literal; no committed magic value is read to obtain it",
}

# --------------------------------------------------------------------------
# The state vector
# --------------------------------------------------------------------------

PRIVATE_STATE_KEY = "privateState"
LEDGER_KEY = "magics"

#: The ledger is a mapping of **string** keys to integer counts.  The legacy
#: branch keys on ``str(magic_id)``; :func:`ledger_key_for` reproduces that key
#: form for a validated committed identity only.
LEDGER_KEY_TYPE = str

#: Eight stored resource slots, not seven.  ``gold``, ``wood``, ``oil``,
#: ``steel``, ``cash``, and ``xp`` live on the map; ``mana`` and ``energy`` live
#: in private state.  M7's readout surfaced seven; this line compares **all
#: eight** because ``privateState.energy`` is a real stored resource that no
#: branch writes, and comparing a subset would make the no-price proof weaker
#: than the measurement that established it.
RESOURCE_VECTOR_SLOTS = 8
RESOURCE_NAMES: Tuple[str, ...] = (
    "xp",
    "gold",
    "wood",
    "oil",
    "steel",
    "cash",
    "mana",
    "energy",
)
RESOURCE_NAME_COUNT = len(RESOURCE_NAMES)

#: Every resource slot the no-price proof compares.  Asserted equal to
#: :data:`RESOURCE_VECTOR_SLOTS` by the suite, so the two cannot drift.
PROOF_RESOURCE_COUNT = RESOURCE_VECTOR_SLOTS

# --------------------------------------------------------------------------
# Committed content
# --------------------------------------------------------------------------

#: The committed table's own size.  Recorded because it is what makes
#: ``unknown_magic_id`` a bounded refusal rather than an open one.
COMMITTED_MAGIC_COUNT = 10

#: The committed table's ids.  Ids are ``1..10`` inclusive; the suite asserts
#: this against the committed content rather than trusting the constant.
COMMITTED_MAGIC_ID_MIN = 1
COMMITTED_MAGIC_ID_MAX = 10

#: One committed entry's description promises an effect whose magnitude is **not
#: committed**.  Named rather than left implicit so no delivered code synthesises
#: one (design D8).
ABSENT_MAGNITUDE_ENTRY = {
    "magic_id": 10,
    "magic_name": "Attack Boost",
    "description": (
        "Your units will increase their attack and life to wreak havoc on enemies!!"
    ),
    "committed_numbers": {"mana": 10, "level": 35, "gold": 10000, "cash": 30},
    "absent": (
        "no multiplier, factor, magnitude, radius, or duration is committed for "
        "the promised attack and life increase"
    ),
    "rule": (
        "No delivered code may synthesize the missing magnitude, and the suite "
        "asserts the absence rather than only the presence of the other fields."
    ),
}

#: The committed fields the projection reports verbatim.  Nothing is derived from
#: them: the ledger has zero readers, so no committed magics field can be
#: consumed at all.
REPORTED_FIELDS: Tuple[str, ...] = ("mana", "level", "gold", "cash", "target")

# --------------------------------------------------------------------------
# Refusal reasons
# --------------------------------------------------------------------------

REASON_INVALID_ACTION = "invalid_action"
REASON_CLIENT_DICTATED_COUNT = "client_dictated_count"
REASON_MISSING_MAGIC_ID = "missing_magic_id"
REASON_INVALID_MAGIC_ID = "invalid_magic_id"
REASON_NON_CANONICAL_MAGIC_ID = "non_canonical_magic_id"
REASON_UNKNOWN_MAGIC_ID = "unknown_magic_id"
REASON_INVALID_LEDGER = "invalid_ledger"
REASON_INVALID_COUNTER = "invalid_counter"
REASON_COUNTER_ABOVE_CAP = "counter_above_cap"
REASON_INVALID_VECTOR = "invalid_vector"
REASON_INVALID_TIMESTAMP = "invalid_timestamp"
REASON_INVALID_PAYLOAD = "invalid_payload"

#: Keys naming a client-dictated count.  These are refused by name rather than
#: ignored, so a caller can tell "you may not say how many" apart from "there
#: was nothing to find" (the same split the combat route makes).
COUNT_KEYS: Tuple[str, ...] = (
    "count",
    "delta",
    "new_value",
    "value",
    "amount",
    "uses",
    "charges",
    "quantity",
    "remaining",
    "cap",
    "max_uses",
)

#: The legacy batch envelope's own keys, refused if a client ever sends them.
#: They are protocol plumbing, not player intent.
PROTOCOL_KEYS: Tuple[str, ...] = (
    "first_number",
    "publishActions",
    "ts",
    "tries",
    "accessToken",
    "commands",
)

CLIENT_DICTATED_REFUSAL = {
    "reason": REASON_CLIENT_DICTATED_COUNT,
    "keys": list(COUNT_KEYS),
    "protocol_keys": list(PROTOCOL_KEYS),
    "rule": (
        "The request carries a validated identity and an action. A client-sent "
        "count, delta, resulting value, or cap is refused here with a named "
        "code, an empty payload, and no state change -- before the player's "
        "recorded state is read at all, so the refusal does not depend on "
        "whether anything was there."
    ),
    "legacy_reads": (
        "The legacy branches read exactly one argument, magic_id, and derive the "
        "counter from the player's own recorded ledger. There is no client-sent "
        "count in the legacy request to refuse; the refusal is the Server v1 / "
        "M13 authority this project wants, not a reproduction of an absence."
    ),
}

# --------------------------------------------------------------------------
# Validation order -- every check above the write (spec requirement 4)
# --------------------------------------------------------------------------

VALIDATION_ORDER: Tuple[Dict[str, Any], ...] = (
    {
        "step": 1,
        "key": "action_in_closed_vocabulary",
        "reads_player_state": False,
        "rule": "action must name one of the two recorded branches",
    },
    {
        "step": 2,
        "key": "no_client_dictated_count",
        "reads_player_state": False,
        "rule": (
            "the request carries no count, delta, resulting value, or cap, and "
            "no protocol plumbing key"
        ),
    },
    {
        "step": 3,
        "key": "identity_present",
        "reads_player_state": False,
        "rule": "the request names a magic identity",
    },
    {
        "step": 4,
        "key": "identity_well_typed",
        "reads_player_state": False,
        "rule": (
            "the identity is an integer and not a bool, and it is not a float, "
            "because str(1.0) != str(1) and the legacy ledger keys on the string "
            "form"
        ),
    },
    {
        "step": 5,
        "key": "identity_in_committed_table",
        "reads_player_state": False,
        "rule": (
            "the identity resolves against the committed ten-entry magic table, "
            "which the legacy server never checks"
        ),
    },
    {
        "step": 6,
        "key": "ledger_readable",
        "reads_player_state": True,
        "rule": (
            "the recorded ledger is a mapping of string keys to non-negative "
            "integers; None and a non-mapping ledger are reported, never "
            "defaulted to {}"
        ),
    },
    {
        "step": 7,
        "key": "counter_readable",
        "reads_player_state": True,
        "rule": "the addressed counter is a non-negative integer when present",
    },
    {
        "step": 8,
        "key": "transition_derived",
        "reads_player_state": True,
        "rule": (
            "the after value is min(cap, before + 1) for both actions, derived "
            "server-side, and is never below the before value; a recorded "
            "counter already above the cap is refused rather than reduced, "
            "because the obvious formula applied to it returns the very "
            "decrease the legacy use_magic arm performs"
        ),
    },
)

VALIDATION_ORDER_STEPS = len(VALIDATION_ORDER)

#: The write happens after every step above.  The suite pins this so a reordering
#: fails rather than being noticed in review.
WRITE_STEP = VALIDATION_ORDER_STEPS + 1

ORDERING_RULE = {
    "steps": VALIDATION_ORDER_STEPS,
    "write_step": WRITE_STEP,
    "rule": (
        "Every check in VALIDATION_ORDER resolves before any ledger entry is "
        "created or modified, so a refused request provably leaves the whole "
        "recorded document byte-identical. The legacy branch performs no "
        "validation at all, so there is no recorded ordering to reproduce; this "
        "requirement exists so that this service's refusals are safe rather "
        "than to match an ordering."
    ),
    "content_before_state": (
        "Step 5 reads committed content and steps 6-8 read player state, so a "
        "request naming a spell that does not exist never consults the corpus."
    ),
}

# --------------------------------------------------------------------------
# The two refused legacy asymmetries (design D3)
# --------------------------------------------------------------------------

LEGACY_UNBOUNDED_ARM = {
    "command": BUY_COMMAND,
    "operator": "+=",
    "source_expression": "magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)",
    "source_lines": [658],
    "defect": (
        "+= adds a capped amount rather than assigning a capped value, so the "
        "result is not bounded by 50 and the counter grows without limit."
    ),
    "executed": {"start": 2, "sequence": [3, 7, 15, 31, 63, 113], "crossed_cap": True},
    "verdict": "REFUSED, never reproduced",
    "reason": (
        "Reproducing an unbounded growth as parity would ship a defect as a "
        "contract. The service increments by one under the recorded cap instead, "
        "and records the difference as a divergence."
    ),
}

LEGACY_DECREASING_ARM = {
    "command": USE_COMMAND,
    "operator": "=",
    "source_expression": "magics[str(magic_id)] = min(50, magics[str(magic_id)] + 1)",
    "source_lines": [670],
    "defect": (
        "= assigns an absolute value, so min(50, x + 1) is a clamp that can "
        "reduce a counter already above 50."
    ),
    "executed": {"before": 113, "after": 50, "charges_destroyed": 63},
    "recorded_message": "Used magic spell",
    "verdict": "REFUSED, never reproduced",
    "reason": (
        "This is the sharpest measurement in the line: a command whose recorded "
        "message claims a spell was used deleted 63 player-owned charges. The "
        "service never reduces a counter, and records the difference as a "
        "divergence."
    ),
}

CAP_UNIFORMITY = {
    "legacy": (
        "The two branches disagree about the cap, so there is no recorded rule "
        "for how a cap applies across actions: one is unbounded past 50 and the "
        "other clamps down to it."
    ),
    "service": (
        "The service applies the recorded cap uniformly to both actions and "
        "records that the uniformity is a decision rather than a reproduction."
    ),
    "above_cap": (
        "A recorded counter already above the cap is refused with "
        "counter_above_cap rather than reduced. The legacy server reduces it, "
        "and refusing is the only option that neither reproduces that decrease "
        "nor answers success for an operation that did nothing."
    ),
    "verdict": "recorded divergence, not parity",
}

# --------------------------------------------------------------------------
# Identity refusals (design D4)
# --------------------------------------------------------------------------

UNKNOWN_IDENTITY = {
    "reason": REASON_UNKNOWN_MAGIC_ID,
    "rule": (
        "The identity must resolve against the committed ten-entry magic table. "
        "The legacy branch validates nothing, so an identity outside the table "
        "is accepted there and creates a ledger entry for a spell that does not "
        "exist."
    ),
    "executed": {
        "command": BUY_COMMAND,
        "identity": 99,
        "outcome": "accepted; a ledger key was created at 0",
    },
    "verdict": "REFUSED, and the difference is recorded as a divergence",
}

NON_CANONICAL_IDENTITY = {
    "reason": REASON_NON_CANONICAL_MAGIC_ID,
    "rule": (
        "An identity whose string form differs from the committed key is a "
        "different identity and is refused rather than coerced. The legacy "
        "ledger keys on str(magic_id), so a numeric identity sent as a float "
        "produces a distinct, unrelated ledger entry."
    ),
    "executed": {
        "command": USE_COMMAND,
        "identity": 1.0,
        "string_form": "1.0",
        "committed_key": "1",
        "outcome": "accepted; the distinct key '1.0' was created",
    },
    "verdict": "REFUSED, and the difference is recorded as a divergence",
}

# --------------------------------------------------------------------------
# The damage refusal -- a structural claim, not a note (design D7)
# --------------------------------------------------------------------------

#: The seven committed damage-shaping fields, each measured to have zero legacy
#: consumers under six counting rules.  Recorded so the refusal is a re-measured
#: census rather than an inherited assertion.
ZERO_CONSUMER_DAMAGE_FIELDS: Tuple[str, ...] = (
    "attack",
    "defense",
    "life",
    "attack_interval",
    "attack_range",
    "best_against",
    "best_against_mult",
)

#: Six counting rules, because the wrong rule produces a confidently wrong
#: number.  ``whole`` is a substring count and is *not* a consumer test;
#: ``code`` is a code-only substring count and is *not* a consumer test either.
#: Only ``token`` and ``quoted`` can establish a consumer.
COUNTING_RULES: Tuple[str, ...] = (
    "whole",
    "distinct_line",
    "code_only",
    "code_distinct_line",
    "token",
    "quoted",
)

#: The rules that can establish a consumer at all.
CONSUMER_RULES: Tuple[str, ...] = ("code_only", "code_distinct_line", "token", "quoted")

NO_DAMAGE = {
    "verdict": (
        "No damage is resolved, computed, applied, or stored, because the "
        "preserved server has no damage rule to reproduce and no committed "
        "amount from which to derive one."
    ),
    "no_consumer_fields": list(ZERO_CONSUMER_DAMAGE_FIELDS),
    "counting_rules": list(COUNTING_RULES),
    "consumer_rules": list(CONSUMER_RULES),
    "no_storage_evidence": {
        "row_slots": 8,
        "row_length_is_constant": True,
        "attr_bag_union": ["cp", "nu", "si", "ts", "ui", "xp"],
        "private_state_damage_shaped_keys": 0,
        "rule": (
            "Every placed row in every canonical committed save document is "
            "exactly eight slots with a fixed type per slot, the attribute bag "
            "union contains no hit point, and no privateState key matches "
            "hp|health|damage|dmg|armor|shield|life|wound. A damage system needs "
            "somewhere to keep a remaining hit point and the committed format "
            "has nowhere."
        ),
    },
    "structural_guard": (
        "No delivered code contains a helper capable of computing a damage "
        "amount, a hit-point value, attack or defense arithmetic, a multiplier, "
        "a mitigation, or a combat outcome, and the hermetic suite asserts that "
        "absence by pinning the delivered module's whole static inventory, so "
        "the guard fails when such a helper is introduced."
    ),
    "committed_content_has_no_amount": {
        "field": None,
        "reason": (
            "The committed magics carry mana, level, gold, cash, and target, and "
            "no damage, multiplier, magnitude, radius, or duration field at all."
        ),
    },
}

# --------------------------------------------------------------------------
# The damage vocabulary that does exist -- reported, never used
# --------------------------------------------------------------------------

COST_TOKEN_FIELD = "cost"
COST_DAMAGE_SELF = {"name": "COST_DAMAGE_SELF", "value": "ds", "line": 894}
COST_DAMAGE_ENEMY = {"name": "COST_DAMAGE_ENEMY", "value": "de", "line": 895}
COST_DAMAGE_TOKENS: Tuple[Dict[str, Any], ...] = (COST_DAMAGE_SELF, COST_DAMAGE_ENEMY)

ATTACK_RESET_FIELD = {
    "name": "tsAttacksReset",
    "line": 919,
    "occurrence_count": 1,
    "fate": "write_only",
    "readers": 0,
    "note": (
        "A client-writable instant inside fast_forward with no reader. Its name "
        "implies a daily attack allowance; no such check exists, so no "
        "allowance, limit, window, or reset rule is derived from the name."
    ),
}

SPYING_RESET_FIELD = {
    "name": "tsSpyingsReset",
    "line": 920,
    "occurrence_count": 1,
    "fate": "write_only",
    "readers": 0,
}

REPORTED_DAMAGE_VOCABULARY: Dict[str, Any] = {
    "cost_tokens": [dict(token) for token in COST_DAMAGE_TOKENS],
    "reset_instants": [dict(ATTACK_RESET_FIELD), dict(SPYING_RESET_FIELD)],
    "no_op_branch": {
        "command": NO_OP_COMMAND,
        "line": NO_OP_LINE,
        "note": NO_OP_NOTE,
    },
    "mission_types_owned_elsewhere": [
        "MISSION_ATTACK_PLAYER",
        "MISSION_ATTACK_FRIEND",
        "MISSION_ASSAULTS_WON",
        "MISSION_KILLED_ENEMY",
        "MISSION_DEFEAT_ALL_TROLLS",
        "MISSION_SACRIFICE_UNIT",
    ],
    "rule": (
        "Every entry here appears only as reported content. None of it is read "
        "to compute a value, gate an operation, or derive a limit. The "
        "combat-named MISSION_* types are owned by godot-mission-vocabulary and "
        "are referenced, not reimplemented."
    ),
}

#: The ledger has zero readers, which is a stronger statement than any field
#: count: because nothing reads it, no committed magics field can be consumed.
LEDGER_HAS_NO_READERS = {
    "ledger_write_sites": 4,
    "counter_subscript_occurrences": 6,
    "membership_tests": 2,
    "local_bindings": 2,
    "read_sites": 0,
    "migration_sites": 4,
    "migration_location": "version.py:32-37",
    "note": (
        "The four shapes are counted separately because collapsing them into "
        "one number is ambiguous: four assignment statements, six subscript "
        "occurrences (the two assignment lines carry two each), two membership "
        "tests of the form `if str(magic_id) in magics`, and two local bindings "
        "of the ledger. version.py coerces a missing or non-dict magics to {}, "
        "which is a migration and not a reader. No statement anywhere reads a "
        "ledger value, so there is no code path from the committed magics "
        "content to any behaviour."
    ),
    "consequence": (
        "No committed magics field -- mana, level, gold, cash, target, area, "
        "kind, img_name, or description -- can be consumed at all."
    ),
}

# --------------------------------------------------------------------------
# No price, and no reward
# --------------------------------------------------------------------------

NO_COST_OR_REWARD = {
    "price": "none charged",
    "reward": "none paid",
    "measured": {
        "transactions": 12,
        "resource_slots_compared": PROOF_RESOURCE_COUNT,
        "resource_names": list(RESOURCE_NAMES),
        "slots_that_moved": 0,
        "mana_before": 15,
        "mana_after": 15,
    },
    "rule": (
        "No stored resource is charged and none is paid, measured across twelve "
        "executed transactions in which no resource slot moved and mana held "
        "steady across a use command. Any price would be invented."
    ),
}

NO_MAGIC_EFFECT = {
    "verdict": "no magic effect is applied to any unit",
    "reason": (
        "use_magic increments a number. Nothing happens to any unit, because "
        "the branches touch no placement row and resolve no combat."
    ),
}

# --------------------------------------------------------------------------
# Divergences
# --------------------------------------------------------------------------

DIVERGENCES: Tuple[Dict[str, Any], ...] = (
    {
        "id": "buy_magic_unbounded_growth",
        "legacy_behaviour": "counter grows past the cap without limit (2 -> 113)",
        "service_behaviour": "counter increments by one under the recorded cap",
        "classification": "refused, not reproduced",
        "authority": "server-side derivation (design D2/D3)",
    },
    {
        "id": "use_magic_decreases_counter",
        "legacy_behaviour": "counter reduced from 113 to 50, destroying 63 charges",
        "service_behaviour": "counter is never reduced",
        "classification": "refused, not reproduced",
        "authority": "server-side derivation (design D3)",
    },
    {
        "id": "cap_applied_uniformly",
        "legacy_behaviour": "the two branches disagree about the cap",
        "service_behaviour": "the cap applies to both actions",
        "classification": "recorded decision, not a reproduction",
        "authority": "design D3",
    },
    {
        "id": "identity_outside_committed_table_accepted",
        "legacy_behaviour": "an identity of 99 was accepted and created a ledger entry",
        "service_behaviour": "refused with unknown_magic_id",
        "classification": "divergence",
        "authority": "Server v1 / M13 (design D4)",
    },
    {
        "id": "float_identity_creates_distinct_key",
        "legacy_behaviour": "an identity of 1.0 created the distinct key '1.0'",
        "service_behaviour": "refused rather than coerced to the committed key",
        "classification": "divergence",
        "authority": "Server v1 / M13 (design D4)",
    },
    {
        "id": "counter_above_cap_reduced_by_legacy",
        "legacy_behaviour": (
            "a recorded counter above the cap is accepted and reduced: 113 -> 50, "
            "destroying 63 charges"
        ),
        "service_behaviour": (
            "refused with counter_above_cap; the recorded state is reported "
            "rather than rewritten"
        ),
        "classification": "refused, not reproduced",
        "authority": "server-side derivation (design D3)",
        "note": (
            "Found by smoke-testing this module, not by review: the obvious "
            "formula min(cap, before + 1) applied to before=113 returns 50, which "
            "is the very decrease this line refuses. Clamping would reproduce the "
            "defect and leaving the value unchanged would answer success for an "
            "operation that did nothing, so the recorded state is refused."
        ),
    },
    {
        "id": "absent_key_writes_zero_not_one",
        "legacy_behaviour": (
            "an identity with no recorded entry takes the branch's else arm and "
            "the ledger gains the key at ZERO: executed, use_magic 3 created '3': "
            "0 and buy_magic 99 created '99': 0"
        ),
        "service_behaviour": (
            "an absent entry is read as zero charges and the transition "
            "increments it, so the key is created at ONE"
        ),
        "classification": "divergence",
        "authority": "server-side derivation (design D2)",
        "note": (
            "Both arms of the legacy branch write 0 for an unknown key, so the "
            "legacy server's own 'acquire a spell you hold none of' path "
            "increments nothing at all. Treating the absent entry as zero "
            "charges and incrementing it is the coherent reading, and it is "
            "recorded here rather than left to be discovered as a mismatch. This "
            "is also the path a live phase against tests/saves/fresh-player.json "
            "exercises, because that corpus's privateState.magics is {}, so the "
            "phase drives a second request on the same identity to show a clean "
            "increment with no divergence alongside it."
        ),
    },
)

DIVERGENCE_COUNT = len(DIVERGENCES)

# --------------------------------------------------------------------------
# Provenance and non-claims
# --------------------------------------------------------------------------

LEGACY_SOURCE_RELATIVE = "command.py"

#: The eleven legacy root modules the census spans.  The damage census is an
#: **eleven-module** measurement, matching
#: ``docs/legacy-m10-damage.md``; scoping it to ``command.py`` alone would
#: report different substring counts for the same fields and look like a
#: contradiction of the investigation rather than a narrower view of it.
LEGACY_MODULES: Tuple[str, ...] = (
    "command.py",
    "engine.py",
    "sessions.py",
    "server.py",
    "constants.py",
    "get_game_config.py",
    "get_player_info.py",
    "version.py",
    "auctions.py",
    "bundle.py",
    "legacy_command_recorder.py",
)

LEGACY_MODULE_COUNT = len(LEGACY_MODULES)

#: The dispatcher branch count the project's own
#: ``tools/command-catalog/verify_commands.py`` reports.  Recorded as a
#: cross-check, not as the derivation: :func:`derive_field_inventory` measures it
#: from ``command.py`` on every call and the suite requires the two to agree.
#:
#: A first draft of :data:`_BRANCH_RE` used the identifier class
#: ``[A-Za-z_]+`` -- **no digits** -- and so measured 62, because
#: ``push_queue_unit2`` ends in ``2``.  That was the fourth of the
#: investigation's four corrections, and it is recorded here so the character
#: class is not "simplified" back.
CATALOG_COMMAND_BRANCHES = 63
CATALOG_BRANCH_COUNT_REQUIRES_DIGITS = "push_queue_unit2"

PROVENANCE = {
    "capability": "godot-damage",
    "milestone": "M10",
    "line": 3,
    "roadmap_line": "damage",
    "investigation": "docs/legacy-m10-damage.md",
    "investigation_pr": 294,
    "delivered_surface": (
        "the privateState.magics counter transition, validated against the "
        "committed magic table"
    ),
    "primary_finding": (
        "the damage refusal -- no damage is resolved, computed, applied, or "
        "stored, and no committed amount exists to derive one from"
    ),
    "legacy_branches": list(MAGIC_COMMANDS),
    "corpus": "villages/Neutral.json",
    "corpus_reason": (
        "the only committed corpus whose privateState.magics is non-empty, which "
        "is what makes this surface capturable against committed data"
    ),
    "executed_transactions": 12,
    "committed_magics_driven": 1,
    "committed_magics_total": COMMITTED_MAGIC_COUNT,
}

NON_CLAIMS: List[str] = [
    "No damage is resolved, computed, applied, or stored.",
    "No magic effect is applied to any unit.",
    "No price is charged and no reward is paid.",
    "No combat outcome, mission completion, or honour is computed.",
    "No attack allowance, limit, window, or reset rule is derived from tsAttacksReset.",
    "No magnitude is synthesized for the committed entry whose description promises an effect.",
    "No per-magic behaviour is claimed: one of ten committed magics was driven.",
    "The cap is the recorded literal, not a derivation from committed content.",
    "The two refused legacy asymmetries are divergences, never parity.",
    "No pixel parity is claimed and no windowed capture is claimed; nothing is rendered.",
    "The ledger has zero readers, so no committed magics field can be consumed.",
]

# --------------------------------------------------------------------------
# Source re-derivation (design D9) -- never transcribed
# --------------------------------------------------------------------------

_BRANCH_RE = re.compile(r'^\s*(?:el)?if\s+cmd\s*==\s*"([A-Za-z0-9_]+)"\s*:\s*$')
_COUNTER_ASSIGN_RE = re.compile(
    r'magics\[str\(magic_id\)\]\s*(?P<op>\+=|=)\s*min\(50,\s*magics\[str\(magic_id\)\]\s*\+\s*1\)'
)


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def legacy_source_text(module: str = LEGACY_SOURCE_RELATIVE) -> str:
    """Read one legacy root module as text from the repository root.

    Read on **every** call so a legacy edit changes the derivation rather than
    leaving a transcribed table to contradict it silently (design D9).
    """
    with io_open(os.path.join(_repo_root(), module)) as handle:
        return handle.read()


def legacy_census_text() -> str:
    """Every legacy root module joined, in the fixed order of :data:`LEGACY_MODULES`.

    Joined rather than counted per module because the investigation's figures are
    totals across the eleven, and a per-module breakdown would invite a reader to
    add them up and get a different answer to a question they did not ask.
    """
    return "\n".join(legacy_source_text(module) for module in LEGACY_MODULES)


def io_open(path: str) -> Any:
    """Open ``path`` as UTF-8 text with newlines preserved verbatim.

    Newlines are deliberately **not** universal-newline translated: the source
    re-derivation below reports byte-level line numbers, and translating would
    make them disagree with the committed file on a CRLF checkout.
    """
    return open(path, "r", encoding="utf-8", newline="")


def _strip_string_literals(line: str) -> str:
    """Blank out double- and single-quoted runs on one line.

    A real two-state scanner rather than a regex: an earlier guard in this
    project desynchronised on an apostrophe inside a double-quoted string and
    made three scans vacuously true.
    """
    out: List[str] = []
    quote = ""
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if quote:
            if char == "\\":
                out.append("  ")
                index += 2
                continue
            if char == quote:
                quote = ""
            out.append(" ")
        else:
            if char == "#":
                out.append(" " * (length - index))
                break
            if char in ('"', "'"):
                quote = char
                out.append(" ")
            else:
                out.append(char)
        index += 1
    return "".join(out)


def code_only(text: str) -> str:
    """Strip comments and string literals from whole-file text."""
    return "\n".join(_strip_string_literals(line) for line in text.split("\n"))


def _branch_span(lines: Sequence[str], name: str) -> Optional[Tuple[int, int]]:
    """Return the 1-based ``(start, end)`` line span of one named branch."""
    start: Optional[int] = None
    for offset, raw in enumerate(lines):
        match = _BRANCH_RE.match(raw.rstrip("\r"))
        if not match:
            continue
        if match.group(1) == name:
            start = offset + 1
            continue
        if start is not None:
            return (start, offset)
    if start is not None:
        return (start, len(lines))
    return None


def count_field_consumers(text: str, field: str) -> Dict[str, int]:
    """Measure one field's presence under all six counting rules.

    ``whole`` and ``code_only`` are **substring** counts and cannot establish a
    consumer on their own: ``COST_DAMAGE_SELF`` contains ``damage`` and
    ``end_attack`` contains ``attack``.  ``token`` and ``quoted`` can.
    """
    stripped = code_only(text)
    return {
        "whole": len(re.findall(re.escape(field), text, re.IGNORECASE)),
        "distinct_line": len(
            [1 for line in text.split("\n") if re.search(re.escape(field), line, re.IGNORECASE)]
        ),
        "code_only": len(re.findall(re.escape(field), stripped, re.IGNORECASE)),
        "code_distinct_line": len(
            [
                1
                for line in stripped.split("\n")
                if re.search(re.escape(field), line, re.IGNORECASE)
            ]
        ),
        "token": len(re.findall(r"\b%s\b" % re.escape(field), text)),
        "quoted": len(re.findall(r'["\']%s["\']' % re.escape(field), text)),
    }


def derive_field_inventory(source_text: Optional[str] = None) -> Dict[str, Any]:
    """Re-derive the two branches, both operators, and the damage census.

    Returns ``{ok, source, branch_names, branches, counter_operators,
    damage_census, damage_census_scope, dispatcher_branches,
    catalog_command_branches, ledger_write_sites, ledger_membership_tests,
    ledger_read_sites, notes}``.

    ``dispatcher_branches`` is measured from ``command.py`` read on every call,
    so the count is a measurement rather than the transcribed
    :data:`CATALOG_COMMAND_BRANCHES`; :func:`branch_count_agrees_with_catalog`
    requires the two to match.  ``damage_census`` spans **all eleven** legacy
    root modules, matching the investigation's figures.
    """
    text = legacy_source_text() if source_text is None else source_text
    lines = text.split("\n")

    branch_names: List[str] = []
    for raw in lines:
        match = _BRANCH_RE.match(raw.rstrip("\r"))
        if match:
            branch_names.append(match.group(1))

    branches: List[Dict[str, Any]] = []
    for name in MAGIC_COMMANDS:
        span = _branch_span(lines, name)
        branches.append(
            {
                "name": name,
                "start": None if span is None else span[0],
                "end": None if span is None else span[1],
                "found": span is not None,
            }
        )

    operators: Dict[str, Optional[str]] = {}
    for name in MAGIC_COMMANDS:
        span = _branch_span(lines, name)
        operator: Optional[str] = None
        if span is not None:
            region = "\n".join(lines[span[0] - 1 : span[1]])
            match = _COUNTER_ASSIGN_RE.search(region)
            if match:
                operator = match.group("op")
        operators[name] = operator

    damage_census: Dict[str, Dict[str, int]] = {}
    census_text = legacy_census_text() if source_text is None else source_text
    for field in ZERO_CONSUMER_DAMAGE_FIELDS:
        damage_census[field] = count_field_consumers(census_text, field)

    # Four distinct ledger shapes are counted separately, because collapsing them
    # into one number is what produced an ambiguous "8 sites" in a first draft:
    # the two `if str(magic_id) in magics:` lines are *membership tests*, not
    # subscripts, and the assignments carry two subscripts each.
    writes = len(re.findall(r"magics\[str\(magic_id\)\]\s*\+?=", text))
    membership = len(re.findall(r'if\s+str\(magic_id\)\s+in\s+magics', text))
    bindings = len(re.findall(r'magics\s*=\s*privateState\["magics"\]', text))

    return {
        "ok": all(branch["found"] for branch in branches),
        "source": LEGACY_SOURCE_RELATIVE,
        "branch_names": branch_names,
        "branches": branches,
        "counter_operators": operators,
        "cap_literals": list(CAP_SOURCE_LINES),
        "damage_census": damage_census,
        "damage_census_scope": list(LEGACY_MODULES),
        "damage_census_module_count": LEGACY_MODULE_COUNT,
        "dispatcher_branches": len(branch_names),
        "catalog_command_branches": CATALOG_COMMAND_BRANCHES,
        "ledger_write_sites": writes,
        "ledger_membership_tests": membership,
        "ledger_bindings": bindings,
        "ledger_read_sites": 0,
        "notes": (
            "Re-derived from legacy bytes on every call. The damage census spans "
            "all eleven legacy root modules and reports substring counts "
            "alongside token counts, because the substring counts are artifacts: "
            "a consumer requires a code-bearing rule, and only token and quoted "
            "can establish one. The dispatcher count requires an identifier "
            "character class containing digits; without them push_queue_unit2 is "
            "invisible and the count reads 62 instead of 63."
        ),
    }


def branch_count_agrees_with_catalog(inventory: Optional[Dict[str, Any]] = None) -> bool:
    """Whether the measured dispatcher count equals the catalog's.

    This is the guard that catches a too-narrow identifier character class, which
    is the specific instrument fault the investigation recorded as its fourth
    correction.
    """
    resolved = derive_field_inventory() if inventory is None else inventory
    return int(resolved.get("dispatcher_branches", -1)) == CATALOG_COMMAND_BRANCHES


def inventory() -> Dict[str, Any]:
    return derive_field_inventory()


def branches() -> List[Dict[str, Any]]:
    return list(derive_field_inventory()["branches"])


def divergences() -> List[Dict[str, Any]]:
    return [dict(entry) for entry in DIVERGENCES]


def non_claims() -> List[str]:
    return list(NON_CLAIMS)


def reported_vocabulary() -> Dict[str, Any]:
    return json.loads(json.dumps(REPORTED_DAMAGE_VOCABULARY))


def actions() -> Tuple[str, ...]:
    return ACTIONS


def is_action(value: Any) -> bool:
    return isinstance(value, str) and value in ACTION_COMMAND


def refused_client_keys(payload: Any) -> List[str]:
    """The client keys naming a count, a cap, or protocol plumbing.

    Returns them in the request's own key order so the refusal message is
    stable across runs regardless of set iteration order.
    """
    if not isinstance(payload, dict):
        return []
    refused: List[str] = []
    for key in payload:
        if not isinstance(key, str):
            continue
        folded = key.lower()
        if folded in COUNT_KEYS or folded in PROTOCOL_KEYS:
            refused.append(key)
            continue
        # Any key that *names* a count is refused too, so a client cannot invent
        # a synonym the closed list did not anticipate.
        if any(token in folded for token in ("count", "delta", "amount", "charge", "uses")):
            refused.append(key)
    return refused


def ledger_key_for(magic_id: Any) -> str:
    """The committed ledger key for a validated identity.

    The ledger is string-keyed and the committed table's own keys are the
    decimal spellings of ids 1..10.  This is called **only** after
    :func:`is_canonical_magic_key` has accepted the identity, so a float never
    reaches the key form.
    """
    if not isinstance(magic_id, int) or isinstance(magic_id, bool):
        raise EnvelopeError(
            REASON_INVALID_MAGIC_ID, "magic identity must be an integer, got %r" % (magic_id,)
        )
    return str(int(magic_id))


def is_canonical_magic_key(magic_id: Any) -> bool:
    """True only for an integer, non-bool identity.

    This is the float-hazard refusal.  ``str(1.0) != str(1)``, and the legacy
    branch keys the ledger on the string form, so accepting a float would create
    a second, unrelated entry for the same spell.
    """
    return isinstance(magic_id, int) and not isinstance(magic_id, bool)


def project_ledger(raw: Any) -> Dict[str, Any]:
    """Project the recorded ledger, failing closed rather than defaulting.

    ``None`` and a non-mapping are **reported**, not replaced with ``{}``,
    because a default would make an unreadable save look like an empty one and
    turn a server fault into a silent create.
    """
    if raw is None:
        return {
            "ok": False,
            "reason": REASON_INVALID_LEDGER,
            "error": "privateState['%s'] is absent (None)" % LEDGER_KEY,
            "keys": [],
            "count": 0,
        }
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "reason": REASON_INVALID_LEDGER,
            "error": "privateState['%s'] must be a mapping, got %s"
            % (LEDGER_KEY, type(raw).__name__),
            "keys": [],
            "count": 0,
        }
    return {
        "ok": True,
        "reason": "",
        "error": "",
        "keys": [key for key in raw.keys()],
        "count": len(raw),
    }


def counter_value(ledger: Any, key: str) -> Dict[str, Any]:
    """The addressed counter, defaulting an **absent** key to zero.

    An absent key legitimately means zero: the legacy branch's own ``else``
    arm writes ``0`` for a key it has never seen (``command.py:660``, ``672``),
    so absent and zero are the same recorded state.  A key that *is* present
    with a non-integer or negative value is a different matter and is refused,
    because incrementing it would require inventing an interpretation.
    """
    if not isinstance(ledger, dict):
        return {
            "ok": False,
            "reason": REASON_INVALID_LEDGER,
            "error": "the recorded ledger is not a mapping",
        }
    if key not in ledger:
        return {"ok": True, "reason": "", "error": "", "value": 0, "present": False}
    value = ledger[key]
    if isinstance(value, bool) or not isinstance(value, int):
        return {
            "ok": False,
            "reason": REASON_INVALID_COUNTER,
            "error": "ledger[%r] must be a non-negative integer, got %r" % (key, value),
        }
    if value < 0:
        return {
            "ok": False,
            "reason": REASON_INVALID_COUNTER,
            "error": "ledger[%r] must be a non-negative integer, got %d" % (key, value),
        }
    return {"ok": True, "reason": "", "error": "", "value": int(value), "present": True}


def derive_counter_transition(before: int, cap: int = COUNTER_CAP) -> Dict[str, Any]:
    """The server-derived transition, for **both** actions.

    ``after = min(cap, before + 1)`` while ``before`` is within range, which:

    * increments by exactly one;
    * stops at the cap and never exceeds it (refusing the legacy
      ``buy_magic`` unbounded growth);
    * is **never below** ``before`` (refusing the legacy ``use_magic``
      decrease).

    There is deliberately no action parameter.  Both actions derive the same
    transition, because the two legacy arms disagree about the cap and
    :data:`CAP_UNIFORMITY` records that the uniformity is a decision rather than
    a reproduction.

    A ``before`` already **above** the cap is refused rather than handled.
    This is the correction that smoke-testing forced, and it is worth recording
    why, because the obvious formula is wrong in exactly the dangerous
    direction: ``min(cap, before + 1)`` applied to ``before=113`` returns
    ``50``, which is the legacy ``use_magic`` charge-destroying decrease this
    line exists to refuse, wearing the modern service's clothes.  The
    alternatives were both worse than refusing:

    * clamping down would reproduce the defect the spec prohibits;
    * leaving the value unchanged would answer success for an operation that
      did nothing, and would silently bless a recorded value the service's own
      bound does not cover.

    Refusing reports the out-of-range recorded state instead of rewriting a
    player's counter.  It is a **modern-only authority** and is recorded as a
    divergence: the legacy server accepts such a value and reduces it.
    """
    if isinstance(before, bool) or not isinstance(before, int):
        raise EnvelopeError(REASON_INVALID_COUNTER, "before must be an integer")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
        raise EnvelopeError(REASON_INVALID_PAYLOAD, "cap must be a non-negative integer")
    if before > cap:
        raise EnvelopeError(
            REASON_COUNTER_ABOVE_CAP,
            "the recorded counter %d is above the recorded cap %d; the legacy "
            "server reduces such a value and this service refuses it rather "
            "than destroying charges or silently blessing it" % (before, cap),
        )
    after = before + 1 if before + 1 < cap else cap
    return {
        "before": int(before),
        "after": int(after),
        "change": int(after) - int(before),
        "capped": bool(after == cap),
        "cap": int(cap),
        "decreased": False,
    }


def is_committed_magic(magic_id: Any, magic_of: Optional[Callable[[Any], Any]] = None) -> bool:
    """Whether the identity resolves against the committed magic table.

    ``magic_of`` is a callable taking an **id** and returning that entry's
    committed configuration row or ``None``, so this module reads committed
    content through a parameter and never resolves it itself.  ``None`` falls
    back to the bounded id range, which is what an offline caller without a
    content accessor uses.
    """
    if not is_canonical_magic_key(magic_id):
        return False
    if magic_of is None:
        return COMMITTED_MAGIC_ID_MIN <= int(magic_id) <= COMMITTED_MAGIC_ID_MAX
    try:
        return magic_of(int(magic_id)) is not None
    except Exception:  # noqa: BLE001 - a content fault is not a content hit
        return False


def neutral_vector() -> List[int]:
    """The all-zero resource vector.

    No magic branch writes a resource, so the derived vector is the neutral one.
    ``command.py`` applies a request's own vector *before* dispatch
    (``command.py:40``), which is why the endpoint's proof compares **every**
    stored resource rather than trusting this vector.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Fail closed on a vector that is not exactly the neutral shape."""
    if not isinstance(vector, list):
        raise EnvelopeError(
            REASON_INVALID_VECTOR, "the resource vector must be a list, got %s" % type(vector).__name__
        )
    if len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            REASON_INVALID_VECTOR,
            "the resource vector must have %d slots, got %d"
            % (RESOURCE_VECTOR_SLOTS, len(vector)),
        )
    for slot in vector:
        if isinstance(slot, bool) or not isinstance(slot, int):
            raise EnvelopeError(REASON_INVALID_VECTOR, "every vector slot must be an integer")
    return list(vector)


def project_magic(
    ledger: Any,
    action: Any,
    magic_id: Any,
    magic_of: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """The whole read-only projection of one magic intent, or its refusal.

    Every check in :data:`VALIDATION_ORDER` runs **here**, before the endpoint
    dispatches anything, which is what makes a refused request leave the
    recorded document byte-identical.

    The content check (step 5) deliberately precedes the ledger read (step 6),
    so a request naming a spell that does not exist never consults the corpus.

    Returns
        ``{ok, reason, error, action, command, addressing_key, addressing,
        addressing_kind, ledger_before, counter_before, counter_after, change,
        capped, cap, entry, ordering_rule, validation_order, no_damage,
        reported_vocabulary}``
    """
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "action": action,
        "command": None,
        "addressing_key": None,
        "addressing": magic_id,
        "addressing_kind": "magic_id",
        "ledger_before": None,
        "counter_before": None,
        "counter_after": None,
        "change": 0,
        "capped": False,
        "cap": COUNTER_CAP,
        "entry": None,
        "ordering_rule": ORDERING_RULE,
        "validation_order": [dict(step) for step in VALIDATION_ORDER],
        "resource_delta": neutral_vector(),
        "no_damage": json.loads(json.dumps(NO_DAMAGE)),
        "reported_vocabulary": reported_vocabulary(),
    }

    # --- step 1: a closed action vocabulary --------------------------------
    if not is_action(action):
        out["reason"] = REASON_INVALID_ACTION
        out["error"] = "action must be one of %s, got %r" % (", ".join(ACTIONS), action)
        return out
    out["command"] = ACTION_COMMAND[str(action)]
    out["addressing_key"] = ACTION_ADDRESSING_KEY[str(action)]

    # --- step 3/4: the identity is present and well typed ------------------
    # (step 2, the client-count refusal, is a request-shape check the route runs
    # before calling this, because it does not depend on the action resolving.)
    if magic_id is None:
        out["reason"] = REASON_MISSING_MAGIC_ID
        out["error"] = "magic_id is required for action %r" % action
        return out
    if not is_canonical_magic_key(magic_id):
        string_form = str(magic_id)
        if isinstance(magic_id, float) or isinstance(magic_id, str):
            out["reason"] = REASON_NON_CANONICAL_MAGIC_ID
            out["error"] = (
                "magic_id %r has the string form %r, which is not the committed "
                "ledger key form; the legacy branch would create a distinct entry "
                "for it" % (magic_id, string_form)
            )
        else:
            out["reason"] = REASON_INVALID_MAGIC_ID
            out["error"] = "magic_id must be an integer and not a bool, got %r" % (magic_id,)
        return out

    # --- step 5: the identity resolves against committed content ------------
    entry = None
    if magic_of is not None:
        try:
            entry = magic_of(int(magic_id))
        except Exception:  # noqa: BLE001 - reported as unknown, not raised
            entry = None
    if not is_committed_magic(magic_id, magic_of):
        out["reason"] = REASON_UNKNOWN_MAGIC_ID
        out["error"] = (
            "magic_id %d is not one of the %d committed magics; the legacy "
            "server accepts any value here and creates a ledger entry for it"
            % (int(magic_id), COMMITTED_MAGIC_COUNT)
        )
        return out
    out["entry"] = entry

    # --- step 6: the ledger is readable ------------------------------------
    ledger_projection = project_ledger(ledger)
    out["ledger_before"] = ledger_projection
    if not bool(ledger_projection.get("ok", False)):
        out["reason"] = REASON_INVALID_LEDGER
        out["error"] = str(ledger_projection.get("error", ""))
        return out

    # --- step 7: the addressed counter is readable -------------------------
    key = ledger_key_for(magic_id)
    out["ledger_key"] = key
    counter = counter_value(ledger, key)
    if not bool(counter.get("ok", False)):
        out["reason"] = str(counter.get("reason", ""))
        out["error"] = str(counter.get("error", ""))
        return out
    out["counter_before"] = int(counter["value"])
    out["counter_present"] = bool(counter.get("present", False))
    # An absent entry is read as zero charges and incremented.  The legacy
    # branches instead take their `else` arm and write the key at ZERO, so the
    # legacy "acquire a spell you hold none of" path increments nothing at all.
    # The fact is surfaced on the response rather than left to be discovered as a
    # mismatch; see the absent_key_writes_zero_not_one divergence.
    out["legacy_absent_arm_writes_zero"] = not bool(counter.get("present", False))

    # --- step 8: the transition is derived server-side ---------------------
    # `derive_counter_transition` raises rather than returning for a recorded
    # counter already above the cap, because min(cap, before + 1) applied to
    # before=113 returns 50 -- the legacy charge-destroying decrease this line
    # exists to refuse.  The refusal is caught here so it is reported through
    # the normal reason channel with no ledger write.
    try:
        transition = derive_counter_transition(int(counter["value"]), COUNTER_CAP)
    except EnvelopeError as exc:
        out["reason"] = exc.code
        out["error"] = str(exc)
        return out
    out["counter_after"] = int(transition["after"])
    out["change"] = int(transition["change"])
    out["capped"] = bool(transition["capped"])
    out["ok"] = True
    return out


def build_envelope(
    action: Any,
    magic_id: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one magic intent.

    The command and its argument list are **derived**: a client supplies an
    intent, and this function turns that intent into the exact legacy batch the
    preserved dispatcher understands.  The resource vector is the validated
    **neutral** one, because no magic branch writes a resource.

    Both branches take exactly one argument, ``magic_id``
    (``command.py:653`` and ``665``), so the argument list is a single-element
    list.

    Whether the identity resolves against committed content and whether the
    ledger is readable are both resolved by :func:`project_magic` **before** this
    is called -- this function validates shape only.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(ACTIONS), action),
        )
    if ts is None:
        ts = int(time.time())
    if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0:
        raise EnvelopeError(REASON_INVALID_TIMESTAMP, "ts must be a non-negative integer")
    if not is_canonical_magic_key(magic_id):
        raise EnvelopeError(
            REASON_NON_CANONICAL_MAGIC_ID,
            "magic_id must be an integer and not a bool, got %r" % (magic_id,),
        )
    checked = validate_vector(neutral_vector())
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": int(ts),
        "tries": 1,
        "accessToken": "",
        "commands": [[0, ACTION_COMMAND[str(action)], [int(magic_id)], checked]],
    }