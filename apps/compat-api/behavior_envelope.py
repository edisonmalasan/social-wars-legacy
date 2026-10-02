#!/usr/bin/env python3
"""Derivation of the legacy resurrectable-unit counter and the revival envelope.

M8 line 8 (``basic behaviors``), the final M8 deliver line.  Unlike the three
lines before it this one delivers a **mechanism**, because the committed content
offers one: ``privateState["deadHeroes"]`` is a **string-keyed count per item
id** and three dispatcher branches reach it.  This module is the single place
where the ledger's projection, both of its gates, the three-door inventory, and
the revival intent become the legacy batch envelope, so the Compatibility API
``POST /v0/resurrect`` endpoint and its suite are checked against *one*
derivation — exactly the arrangement the twelve delivered lines already use.

The mechanism (design D1)
    ``engine.push_dead_unit`` (``engine.py:149-171``) increments
    ``privateState["deadHeroes"][str(item_id)]``, creating the key at ``1``.
    ``engine.resurrect_hero`` (``engine.py:172-182``) decrements it and
    **deletes** the key when the count reaches zero.  Three branches reach
    them: ``kill`` (``command.py:169-181``) deletes the row and **never**
    touches the ledger; ``sell`` (``command.py:149-167``) calls
    ``push_dead_unit`` **only** when ``reason == "KILL"`` and through the
    **engine helper**, not through a branch; and ``resurrect_hero``
    (``command.py:625-635``) calls the decrement and then re-places the row.

Both gates, and no third (design D1)
    ``push_dead_unit`` returns ``False`` unless the row is on **player team 1**
    (``engine.py:151``) and its committed ``properties`` carry
    ``resurrectable > 0`` (``engine.py:159,162``).  Those are the **only** two
    conditions the helper checks, and this module derives no third: an added
    eligibility rule would be a rule the legacy server does not have.

The client sends a cell, never a value (design D2)
    The legacy branch takes ``index``, ``item_id``, ``x``, ``y`` **and**
    ``used_syringe`` all from the client, which is the untrusted pattern
    ``godot-building-move`` and ``godot-building-collect`` already record.
    This contract keeps the legacy *behaviour* and rejects the legacy *trust*:
    the request body carries **only** a player identifier and a cell
    (``x``, ``y``), and the service derives

    * the **map key** by resolving the addressed cell against the save's own
      placement rows — every row records its committed ``(x, y)`` in slots 1
      and 2, so the cell *is* an addressable object in committed state; and
    * the revived **item id** from the player's own recorded ledger, which is
      the only place a *dead* unit's identity survives, since the row is gone.

    The cell therefore chooses **where** the revival lands and the ledger
    chooses **what** is revived.  That division is **DERIVED**, and the
    rejected alternative is retained in :data:`RESOLUTION_RULE`: taking the
    item id from the addressed row's own slot 0 instead, which would mean
    reviving the row that is *already standing* at that cell and is therefore
    not dead at all.  Nothing in the source asserts which pairing the Flash
    client used — the committed investigation records that
    ``resurrect_hero``'s caller supplies ``item_id`` independently of
    whatever was in the ledger, and this contract keeps that independence out
    of the trust boundary rather than keeping it in the behaviour.

    Two refusals resolve the target before the dispatcher runs, because both
    would otherwise reach ``engine.resurrect_hero`` and persist a save: an
    addressed cell that names **no** placement row, and a player whose ledger
    records **nothing** to revive.  A cell held by more than one row and a
    ledger holding more than one entry are refused too rather than resolved by
    an invented tie-break.

No syringe cost, and no resource movement (design D3)
    ``used_syringe`` is read from ``args[4]`` and **discarded**
    (``command.py:630``, and the local is never used again in the branch).  The
    obvious counterpart is the committed ``syringes`` field — carried by all
    429 units with **6 distinct values** and **zero** legacy consumers — so
    **no syringe cost is ever charged** and the derivation sends a literal
    ``0``.  The response never echoes the discarded value.  The endpoint's
    post-execution proof therefore includes the **"every stored resource is
    unchanged"** half, which is what makes the no-cost claim
    non-tautological: a cost smuggled through the resource vector would have to
    show up there.

No combat, and no placement validation (design D5)
    The revived row is re-placed by ``engine.map_add_item``
    (``engine.py:8-31``) with **no** occupancy, bounds, type, or terrain check
    — the same absence ``godot-building-move`` and ``godot-building-collect``
    already record — so this contract reproduces it and records the gap as a
    Server v1 / M13 requirement rather than filling it.  ``attack``,
    ``defense``, ``life``, ``attack_interval``, ``attack_range``,
    ``best_against``, and ``best_against_mult`` each measure **zero** legacy
    consumers, so nothing here resolves damage, an outcome, a hit, or a life
    total.

``clicks_to_build`` is referenced, never reimplemented (design D6)
    ``engine.map_add_item`` reads it once (``engine.py:26``) and, when it is
    positive, seeds ``attr["nc"] = 0`` on a fresh team-1 placement.  That
    counter is already reported and deliberately **not** consumed by the
    delivered ``godot-building-construction`` capability, which owns it.  This
    module records the relationship and reimplements nothing: the re-placement
    is executed by the unchanged legacy ``map_add_item``, not reproduced here.

The committed corpus
    ``tests/saves/fresh-player.json`` records
    ``privateState["deadHeroes"] == {}`` — an empty ledger — and places 40 rows
    across **40 distinct cells**, all of committed type ``b``, so **0 of 40**
    placed rows are resurrectable and **no unit row exists at all**.  A
    one-shot executed-legacy fixture is therefore impossible without first
    manufacturing a unit row, which the delivered ``godot-unit-instances``
    capability already refused.  **No executed-legacy fixture is claimed here**,
    and the cause is a **corpus limitation with a named cause** — not, as on
    the three refusal lines, the absence of behaviour.

    The endpoint's live verification therefore runs against a **disposable**
    corpus copy **seeded** with one resurrectable ledger entry through the
    documented, opt-in :data:`SEED_ENVIRONMENT` seam.  Seeding a throwaway
    copy is not manufacturing coverage in preserved material: the committed
    corpus and every delivered fixture directory stay byte-identical, which is
    what the no-manufactured-coverage boundary requires.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, ``GRID_EXTENT``,
    ``in_grid``, and ``EnvelopeError`` — so every delivered derivation, its
    fixture, and its suite keeps passing untouched.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions`` [],
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioural effect.  The batch carries **exactly one** command:
    ``[0, "resurrect_hero", [map_key, item_id, x, y, 0], neutral]``.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# One shared derivation.  The placement module is imported unchanged — nothing
# here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    GRID_EXTENT,
    data_field,
    in_grid,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# ------------------------------------------------------------ the command --
RESURRECT_COMMAND = "resurrect_hero"

# The legacy argument indexes the branch reads (``command.py:626-630``).  All
# five are positional; there is no keyword form and no sixth argument.
ARG_INDEX = 0
ARG_ITEM_ID = 1
ARG_X = 2
ARG_Y = 3
ARG_USED_SYRINGE = 4
LEGACY_ARGUMENT_COUNT = 5

#: The derived ``used_syringe``.  ``args[4]`` is bound to a local and **never
#: read again** (``command.py:630`` is the branch's last use of it), so the
#: value is inert: the choice of ``0`` changes nothing at all, and is recorded
#: as a **derivation**, never an observation.
DERIVED_USED_SYRINGE = 0
SYRINGE_DISCARD_NOTE = (
    "args[4] is bound to the local `used_syringe` (command.py:630) and is NEVER "
    "READ AGAIN anywhere in the branch, so it is DISCARDED: the statement after "
    "it is the ledger decrement and the re-placement. The committed counterpart "
    "is the item's own `syringes` field, which is carried by all 429 committed "
    "units, takes 6 distinct values, and has ZERO occurrences across the seven "
    "legacy modules (command.py, engine.py, sessions.py, server.py, constants.py, "
    "get_game_config.py, version.py) - so NO SYRINGE COST IS EVER CHARGED. The "
    "derivation sends a literal 0, the value is therefore irrelevant, and the "
    "response NEVER ECHOES the discarded argument"
)

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

#: The seven stored resource slots the endpoint's post-execution proof compares.
#: Every one of them, never a subset: that is what makes the no-cost claim
#: non-tautological.
RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")

# The committed map row shape (``engine.map_add_item``, ``engine.py:31``):
# ``[item, x, y, timestamp, orientation, store, attr, player]``.
MAP_ROW_SLOTS = 8
SLOT_ITEM_ID = 0
SLOT_CELL_X = 1
SLOT_CELL_Y = 2
SLOT_PLAYER = 7

#: The committed player team the increment gate names (``engine.py:151``).
PLAYER_TEAM = 1

# The committed ``properties`` flag the increment gate names
# (``engine.py:159,162``), read from the RAW configuration string.
RESURRECTABLE_FLAG = "resurrectable"
PROPERTIES_FIELD = "properties"

# The ledger's own save location.  ``version.py:26-30`` initialises it to
# ``None`` and then coerces a non-object to ``{}``, which is a **migration**
# path and is recorded as such, never as gameplay.
LEDGER_KEY = "deadHeroes"
PRIVATE_STATE_KEY = "privateState"
LEDGER_MIGRATION_NOTE = (
    "privateState['deadHeroes'] is initialised to None and then coerced to {} "
    "by version.py:26-30 ('Applied hospital fix'). That is a SAVE MIGRATION, not "
    "behaviour: no branch ever creates the key, so a save that never held it "
    "receives an empty ledger from the migration rather than from gameplay. "
    "Recorded, never treated as a rule"
)

# --------------------------------------------------------- the named gates --
GATE_TEAM = {
    "gate": "player_team_one",
    "checks": "the dying row's slot 7 (player) equals 1",
    "source": "engine.py:151 (push_dead_unit)",
    "committed": True,
    "note": "push_dead_unit returns False when item[7] != 1, so a row on "
            "another team never enters the ledger no matter how resurrectable "
            "its committed properties say it is",
}
GATE_RESURRECTABLE = {
    "gate": "resurrectable_positive",
    "checks": "the committed properties object carries resurrectable and "
              "int(resurrectable) > 0",
    "source": "engine.py:159,162 (push_dead_unit)",
    "committed": True,
    "note": "push_dead_unit returns False when the flag is absent AND when it "
            "is present but not greater than zero, so an absent flag is a "
            "REFUSAL, never a zero",
}

#: Both gates, in the helper's own order, and the machine-readable form of
#: "no third gate is invented".
GATES = (GATE_TEAM, GATE_RESURRECTABLE)
GATE_COUNT = 2

NO_THIRD_GATE = (
    "EXACTLY TWO GATES EXIST AND NO THIRD IS INVENTED. push_dead_unit "
    "(engine.py:149-171) performs two checks and no more: the row's player "
    "team (engine.py:151) and the committed resurrectable flag "
    "(engine.py:159,162). Everything else a reader might expect is absent from "
    "the helper: no level check, no cost check, no capacity check, no "
    "cooldown, no per-type check, and no check that the row is a unit rather "
    "than a building. Adding any of them here would make this client STRICTER "
    "than the legacy server, which is a parity break in the opposite direction "
    "from the usual risk"
)

# ------------------------------------------------------- the three doors --
#: ``kill`` reaches nothing.  ``sell`` reaches the ledger only behind the
#: combat-reason guard and only through the engine helper.  ``resurrect_hero``
#: decrements.  ``push_dead_unit`` is an ENGINE HELPER, not a branch, which is
#: what keeps the named-branch count and the ledger-reaching count separately
#: meaningful.
COMMAND_INVENTORY = (
    {
        "command": "kill",
        "kind": "dispatcher-branch",
        "source": "command.py:169-181",
        "reaches_ledger": False,
        "effect": "looks the row up, deletes it, and prints; it NEVER touches "
                  "privateState['deadHeroes'], so a combat kill records no "
                  "death in the ledger",
        "mutates_also": "map['items']: the addressed row is deleted",
    },
    {
        "command": "sell",
        "kind": "dispatcher-branch",
        "source": "command.py:149-167",
        "reaches_ledger": True,
        "guard": "reason == 'KILL'",
        "through": "push_dead_unit (engine helper, engine.py:149-171)",
        "effect": "calls push_dead_unit ONLY when the reason is the combat "
                  "reason, which increments deadHeroes[str(item_id)] by one, "
                  "creating the key at 1, subject to BOTH gates",
        "mutates_also": "map['items']: the addressed row is deleted",
        "closed_in_practice": "the delivered godot-building-sell capability "
                              "derives its own sell reason and accepts none from "
                              "the client, so the KILL guard is closed in "
                              "practice while remaining open in the source. That "
                              "recorded claim is CORRECT AND UNCHANGED: this "
                              "guard is the ONLY door into the dead-hero ledger",
    },
    {
        "command": "resurrect_hero",
        "kind": "dispatcher-branch",
        "source": "command.py:625-635",
        "reaches_ledger": True,
        "through": "resurrect_hero (engine helper, engine.py:172-182)",
        "effect": "decrements deadHeroes[str(item_id)] and DELETES the key when "
                  "the count reaches zero",
        "mutates_also": "map['items']: map_add_item re-places the row at "
                        "CLIENT-SUPPLIED index/x/y with no occupancy, bounds, "
                        "type, or terrain check (engine.py:8-31)",
        "discarded_argument": "args[4], used_syringe, is read and DISCARDED",
    },
)

#: The engine helper, recorded separately so the named-branch count and the
#: ledger-reaching command count stay distinguishable.
ENGINE_HELPERS = (
    {
        "helper": "push_dead_unit",
        "source": "engine.py:149-171",
        "is_dispatcher_branch": False,
        "effect": "the increment, behind both gates",
    },
    {
        "helper": "resurrect_hero",
        "source": "engine.py:172-182",
        "is_dispatcher_branch": False,
        "effect": "the decrement, deleting the key at zero",
    },
)

#: The 63 named dispatcher branches the committed catalog records, measured by
#: the client suite out of ``command.py`` in the same run.  Two of them reach
#: the ledger and one of those two is closed in practice.
NAMED_BRANCH_COUNT = 63
LEDGER_REACHING_COMMANDS = ("sell", "resurrect_hero")
LEDGER_REACHING_COMMAND_COUNT = len(LEDGER_REACHING_COMMANDS)
BRANCHES_THAT_BYPASS_LEDGER = ("kill",)

# --------------------------------------------------- the committed fields --
#: The committed behavioural fields with **zero** legacy consumers across the
#: seven legacy root modules, with their measured distinct-value counts over the
#: 429 committed unit definitions.  Reported as CONTENT ONLY.
#:
#: MEASURED CORRECTION against ``docs/legacy-unit-behaviors.md``: that record
#: says "twenty" of "twenty-two" behavioural committed fields have zero legacy
#: consumers and then **names twenty-one** of them.  The named list is
#: authoritative — it is countable, and every one of its twenty-one entries
#: measures **zero** — so the field count is **21**, and with the two fields that
#: DO have consumers (``resurrectable`` and ``clicks_to_build``) the behavioural
#: total is **23**, not 22.  The rejected figures are recorded in
#: :data:`ZERO_CONSUMER_COUNT_RECORDED` and :data:`BEHAVIOURAL_FIELD_COUNT_RECORDED`
#: rather than dropped, and every figure in the list is re-measured by the client
#: suite in the same run.
ZERO_CONSUMER_FIELDS = (
    {"field": "attack", "legacy_reads": 0, "unit_distinct": 131},
    {"field": "attack_interval", "legacy_reads": 0, "unit_distinct": 12},
    {"field": "attack_range", "legacy_reads": 0, "unit_distinct": 14},
    {"field": "best_against", "legacy_reads": 0, "unit_distinct": 5},
    {"field": "best_against_mult", "legacy_reads": 0, "unit_distinct": 5},
    {"field": "defense", "legacy_reads": 0, "unit_distinct": 1},
    {"field": "life", "legacy_reads": 0, "unit_distinct": 150},
    {"field": "velocity", "legacy_reads": 0, "unit_distinct": 11},
    {"field": "collect_type", "legacy_reads": 0, "unit_distinct": None},
    {"field": "collect_xp", "legacy_reads": 0, "unit_distinct": None},
    {"field": "max_collects", "legacy_reads": 0, "unit_distinct": None},
    {"field": "syringes", "legacy_reads": 0, "unit_distinct": 6},
    {"field": "volume", "legacy_reads": 0, "unit_distinct": 3},
    {"field": "training_time", "legacy_reads": 0, "unit_distinct": None},
    {"field": "unit_capacity", "legacy_reads": 0, "unit_distinct": None},
    {"field": "expiration", "legacy_reads": 0, "unit_distinct": None},
    {"field": "population", "legacy_reads": 0, "unit_distinct": None},
    {"field": "min_level", "legacy_reads": 0, "unit_distinct": 21},
    {"field": "activation", "legacy_reads": 0, "unit_distinct": None},
    {"field": "gift_level", "legacy_reads": 0, "unit_distinct": 8},
    {"field": "build_time", "legacy_reads": 0, "unit_distinct": None},
)

#: The twenty-one measured zero-consumer fields, and the two that are not, as one
#: countable record.  The recorded figures beside them are the ones the committed
#: investigation states; they are retained verbatim so the correction is visible.
ZERO_CONSUMER_COUNT = 21
ZERO_CONSUMER_COUNT_RECORDED = 20
BEHAVIOURAL_FIELD_COUNT = 23
BEHAVIOURAL_FIELD_COUNT_RECORDED = 22

#: The seven committed combat fields the delta names, restated as a closed set
#: so "no combat is resolved" is checkable against a list rather than a phrase.
COMBAT_FIELDS = (
    "attack", "defense", "life", "attack_interval", "attack_range",
    "best_against", "best_against_mult",
)

#: Every behavioural ``properties`` flag on the committed unit definitions with
#: its measured positive count.  All of them have zero legacy consumers.
UNIT_PROPERTY_FLAGS = (
    {"flag": "animal", "positive": 2},
    {"flag": "bulldozable", "positive": 424},
    {"flag": "fireman", "positive": 1},
    {"flag": "ft_armored", "positive": 157},
    {"flag": "ft_building", "positive": 2},
    {"flag": "ft_flying", "positive": 135, "carried": 137},
    {"flag": "ft_ground", "positive": 134},
    {"flag": "harvester", "positive": 5},
    {"flag": "healer", "positive": 3},
    {"flag": "human", "positive": 126},
    {"flag": "mechanic", "positive": 301},
    {"flag": "resurrectable", "positive": 426, "carried": 426},
    {"flag": "seeStealthUnits", "positive": 427},
    {"flag": "waterborne", "positive": 2},
    {"flag": "worker", "positive": 5},
)

#: The measured committed distribution of the two fields this line reads, so the
#: eligibility it enforces is anchored in content rather than asserted.
#: ``resurrectable`` is a ``properties`` flag; ``syringes`` and
#: ``clicks_to_build`` are top-level item fields.
#:
#: MEASURED CORRECTION against ``docs/legacy-unit-behaviors.md``.  That record
#: reports ``clicks_to_build`` as "429 of 429 units, **3 distinct**".  Measured
#: over the committed package the field takes **two** distinct values in total —
#: ``0`` and ``1`` — and only **one** of them over the units, which is ``0`` on
#: all 429.  The third value the record counts is not in the content: the
#: buildings take ``0`` on 172 and ``1`` on 298, and the single committed special
#: (id ``925``, committed type ``l``, "Expandable Land") is the 299th row with
#: ``1``.  The rejected figure is retained here rather than quietly dropped.
RESURRECTABLE_UNITS_POSITIVE = 426
RESURRECTABLE_UNITS_OF = 429
RESURRECTABLE_BUILDINGS_POSITIVE = 0
RESURRECTABLE_BUILDINGS_OF = 470
SYRINGES_UNIT_VALUES = {"0": 2, "1": 120, "2": 48, "3": 256, "4": 1, "5": 2}
SYRINGES_BUILDING_VALUES = {"0": 470}
SYRINGES_SPECIAL_VALUE = "0"
CLICKS_TO_BUILD_UNIT_VALUES = {"0": 429}
CLICKS_TO_BUILD_BUILDING_VALUES = {"0": 172, "1": 298}
CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT = 2
CLICKS_TO_BUILD_DISTINCT_RECORDED = 3
CLICKS_TO_BUILD_CORRECTION = (
    "CORRECTION, MEASURED AGAINST THE COMMITTED INVESTIGATION: that record "
    "reports clicks_to_build as '429 of 429 units, 3 distinct'. Measured over "
    "the committed content package the field takes TWO distinct values in "
    "total (0 and 1) and only ONE of them over the units, which is 0 on all "
    "429. The buildings take 0 on 172 and 1 on 298; the 299th row carrying 1 is "
    "the single committed SPECIAL (id 925, committed type 'l', Expandable Land), "
    "which is neither a unit nor a building. The recorded 3 is retained beside "
    "the measured 2 so a later reader can re-derive the choice"
)

#: The two behavioural committed fields that **do** have legacy consumers, as one
#: countable record.  Everything else in the behavioural set measures zero, and
#: the recorded figures beside these are the ones the committed investigation
#: states, retained verbatim so the corrections above stay visible.
CONSUMED_BEHAVIOURAL_FIELDS = (
    {
        "field": RESURRECTABLE_FLAG,
        "kind": "properties flag",
        "legacy_reads": 2,
        "source": "engine.py:159,162 (push_dead_unit)",
        "units_positive": RESURRECTABLE_UNITS_POSITIVE,
        "units_of": RESURRECTABLE_UNITS_OF,
        "buildings_positive": RESURRECTABLE_BUILDINGS_POSITIVE,
        "buildings_of": RESURRECTABLE_BUILDINGS_OF,
        "note": "the FIRST committed field in this project whose legacy consumer "
                "is a MUTATION OF PRIVATE STATE rather than a read, and the "
                "reason this line delivers a mechanism rather than a refusal",
    },
    {
        "field": "clicks_to_build",
        "kind": "top-level item field",
        "legacy_reads": 1,
        "source": "engine.py:26 (map_add_item)",
        "units_distinct": CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT,
        "units_distinct_recorded": CLICKS_TO_BUILD_DISTINCT_RECORDED,
        "unit_values": dict(CLICKS_TO_BUILD_UNIT_VALUES),
        "building_values": dict(CLICKS_TO_BUILD_BUILDING_VALUES),
        "note": "seeds attr['nc'] = 0 on a fresh team-1 placement when positive; "
                "that counter is owned by godot-building-construction and is "
                "referenced here, never reimplemented",
    },
)

UNIT_ONLY_NOTE = (
    "resurrectable is a UNIT-ONLY committed flag: it is positive on %d of the "
    "%d committed unit definitions and on %d of the %d committed building "
    "definitions, so it never appears on a building at all. That is why the "
    "committed corpus - which places only buildings - holds no resurrectable "
    "row, and why a one-shot executed-legacy fixture is impossible here without "
    "first manufacturing a unit row"
    % (
        RESURRECTABLE_UNITS_POSITIVE,
        RESURRECTABLE_UNITS_OF,
        RESURRECTABLE_BUILDINGS_POSITIVE,
        RESURRECTABLE_BUILDINGS_OF,
    )
)

# -------------------------------------------------------- the refusals ----
NO_SYRINGE_COST = (
    "NO SYRINGE COST IS CHARGED AND NO STORED RESOURCE MOVES. `used_syringe` is "
    "read from args[4] (command.py:630) and DISCARDED, and the committed "
    "`syringes` field it would be paid in has ZERO occurrences across the seven "
    "legacy modules, so the legacy server charges nothing. Charging one would "
    "invent an economy the repository does not contain. The endpoint proves the "
    "no-cost claim with the 'every stored resource is unchanged' half of its "
    "post-execution proof, comparing the FULL resource set rather than a subset, "
    "which is what forecloses a cost smuggled through the request's own resource "
    "vector (legacy applies that vector BEFORE the branch, command.py:40 and "
    "engine.py:251-271)"
)

NO_COMBAT = (
    "NO COMBAT IS RESOLVED OF ANY KIND. attack, defense, life, attack_interval, "
    "attack_range, best_against, and best_against_mult each have ZERO legacy "
    "consumers, so the committed numbers are CONTENT and never rules: this "
    "contract computes no damage, no attack outcome, no defence application, no "
    "hit chance, and no life or interval arithmetic, and a reader who wanted a "
    "combat model out of them must bring evidence the legacy contract does not "
    "contain. The ledger's own two-sided counter is the whole death model the "
    "server has"
)

NO_PLACEMENT_VALIDATION = (
    "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED TO THE REVIVED "
    "PLACEMENT. The legacy branch re-places the row through engine.map_add_item "
    "(engine.py:8-31) with no such check, and this contract reproduces that "
    "absence rather than filling it: inventing an occupancy check here would "
    "make this client STRICTER than the legacy server. The gap is recorded as a "
    "Server v1 / M13 requirement, exactly as godot-building-move, "
    "godot-building-place, and godot-building-upgrade already do"
)

#: The three refusals, as one machine-readable list, in the delta's order.
REFUSALS = (
    {"refusal": "syringe_cost", "implemented": False, "rule": NO_SYRINGE_COST},
    {"refusal": "combat_resolution", "implemented": False, "rule": NO_COMBAT},
    {
        "refusal": "placement_validation",
        "implemented": False,
        "rule": NO_PLACEMENT_VALIDATION,
    },
)

# ------------------------------------------------ the resolution contract --
RESOLUTION_RULE = (
    "THE CELL CHOOSES WHERE THE REVIVAL LANDS AND THE LEDGER CHOOSES WHAT IS "
    "REVIVED; NEITHER IS EVER TAKEN FROM THE CLIENT. The request body carries "
    "only {user_id, x, y}. The MAP KEY is derived by resolving the addressed "
    "cell against the save's own placement rows, each of which records its "
    "committed (x, y) in slots 1 and 2; the addressed key is the one whose row "
    "records exactly that cell. The ITEM ID is derived from the player's own "
    "recorded deadHeroes ledger, because the revived row is not on the map and "
    "the ledger is the only place a dead unit's identity survives"
)

REJECTED_RESOLUTION = (
    "REJECTED: taking the revived item id from the ADDRESSED ROW's own slot 0. "
    "That would mean reviving the row already standing at that cell, which is "
    "precisely the row that is NOT dead, and it would make the ledger's own key "
    "decorative. The legacy caller supplies item_id independently of whatever "
    "was in the ledger - nothing checks the pairing - so both readings are "
    "behaviourally available and the choice is recorded as DERIVED rather than "
    "observed. The retained alternative is kept visible so a later reader can "
    "re-derive the choice rather than inherit it"
)

DERIVED_PAIRING = (
    "THE DEATH/RESURRECTION PAIRING IS DERIVED, NOT ASSERTED. push_dead_unit "
    "and resurrect_hero are complementary and share privateState['deadHeroes'], "
    "but no comment and no dispatch path asserts that they are a pair: the "
    "legacy author's own comment on the increment says only 'Tries to push item "
    "to deadHeroes if it is ressurectable and on player team'. Nothing in this "
    "contract asserts the pairing as a server guarantee either"
)

CLICKS_TO_BUILD_BOUNDARY = (
    "clicks_to_build is REFERENCED AND NOT REIMPLEMENTED. Its single legacy "
    "read is engine.py:26, inside map_add_item, where a positive value seeds "
    "attr['nc'] = 0 on a freshly placed team-1 row. That counter is the "
    "construction-click counter already reported and deliberately not consumed "
    "by the delivered godot-building-construction capability, which owns it. "
    "This line records the relationship and reimplements nothing: the "
    "re-placement is executed by the UNCHANGED legacy map_add_item. Note also "
    "that the committed clicks_to_build is 0 on ALL 429 unit definitions, so a "
    "revived UNIT never seeds the counter at all - a measurement, not an "
    "assumption"
)

FIXTURE_NOT_CAPTURED = (
    "NO EXECUTED-LEGACY BEHAVIOUR FIXTURE WAS CAPTURED, AND THE REASON IS A "
    "CORPUS LIMITATION WITH A NAMED CAUSE - NOT, as on the three refusal lines "
    "before this one, the absence of behaviour. resurrectable is a UNIT-ONLY "
    "committed flag (positive on %d of %d units, on %d of %d buildings), the "
    "committed corpus places ONLY buildings across %d rows and %d distinct cells, "
    "so 0 of its placed rows are resurrectable and it places NO unit row at all, "
    "and its privateState['deadHeroes'] is present and {}. Capturing one would "
    "require MANUFACTURING A UNIT ROW first, which the delivered "
    "godot-unit-instances capability already refused and recorded as the right "
    "call. No unit row was manufactured in the committed corpus or in any "
    "delivered fixture directory"
    % (
        RESURRECTABLE_UNITS_POSITIVE,
        RESURRECTABLE_UNITS_OF,
        RESURRECTABLE_BUILDINGS_POSITIVE,
        RESURRECTABLE_BUILDINGS_OF,
        40,
        40,
    )
)

# ------------------------------------------------------- the named codes --
REASON_INVALID_CELL = "invalid_cell"
REASON_UNRESOLVABLE_CELL = "unresolvable_cell"
REASON_AMBIGUOUS_CELL = "ambiguous_cell"
REASON_UNRESOLVABLE_LEDGER_ENTRY = "unresolvable_ledger_entry"
REASON_AMBIGUOUS_LEDGER = "ambiguous_ledger"
REASON_NOT_RESURRECTABLE = "not_resurrectable"
REASON_INVALID_LEDGER = "invalid_ledger"
REASON_INVALID_ITEM_ID = "invalid_item_id"

# The codes the endpoint maps onto HTTP 409: both are **content** refusals
# resolved before the legacy dispatcher runs, so the corpus stays
# byte-identical on every one of them.
CONFLICT_REASONS = (
    REASON_UNRESOLVABLE_CELL,
    REASON_AMBIGUOUS_CELL,
    REASON_UNRESOLVABLE_LEDGER_ENTRY,
    REASON_AMBIGUOUS_LEDGER,
    REASON_NOT_RESURRECTABLE,
)

# ------------------------------------------------- the verification seam --
#: The opt-in environment variable through which a **disposable** corpus copy is
#: seeded with one resurrectable ledger entry so the endpoint's positive path can
#: be exercised end to end.  It is **absent by default**: no normal run, no
#: unittest, and no other live phase is affected, and the committed corpus is
#: never a target of it.  A malformed value is a named refusal, never a silent
#: no-op, so a typo can never make a seeding claim quietly false.
SEED_ENVIRONMENT = "COMPAT_SEED_DEAD_HEROES"

__all__ = [
    "ARG_ITEM_ID",
    "ARG_INDEX",
    "ARG_USED_SYRINGE",
    "ARG_X",
    "ARG_Y",
    "BEHAVIOURAL_FIELD_COUNT",
    "BEHAVIOURAL_FIELD_COUNT_RECORDED",
    "BRANCHES_THAT_BYPASS_LEDGER",
    "CLICKS_TO_BUILD_BOUNDARY",
    "CLICKS_TO_BUILD_BUILDING_VALUES",
    "CLICKS_TO_BUILD_CORRECTION",
    "CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT",
    "CLICKS_TO_BUILD_DISTINCT_RECORDED",
    "CLICKS_TO_BUILD_UNIT_VALUES",
    "COMBAT_FIELDS",
    "COMMAND_INVENTORY",
    "CONFLICT_REASONS",
    "CONSUMED_BEHAVIOURAL_FIELDS",
    "DERIVED_PAIRING",
    "DERIVED_USED_SYRINGE",
    "ENVELOPE_KEYS",
    "ENGINE_HELPERS",
    "EnvelopeError",
    "FIXTURE_NOT_CAPTURED",
    "GATES",
    "GATE_COUNT",
    "GATE_RESURRECTABLE",
    "GATE_TEAM",
    "GRID_EXTENT",
    "LEDGER_KEY",
    "LEDGER_MIGRATION_NOTE",
    "LEDGER_REACHING_COMMANDS",
    "LEDGER_REACHING_COMMAND_COUNT",
    "LEGACY_ARGUMENT_COUNT",
    "MAP_ROW_SLOTS",
    "NAMED_BRANCH_COUNT",
    "NO_COMBAT",
    "NO_PLACEMENT_VALIDATION",
    "NO_SYRINGE_COST",
    "NO_THIRD_GATE",
    "PLAYER_TEAM",
    "PRIVATE_STATE_KEY",
    "PROPERTIES_FIELD",
    "REFUSALS",
    "REJECTED_RESOLUTION",
    "RESOURCE_NAMES",
    "RESOURCE_VECTOR_SLOTS",
    "RESOLUTION_RULE",
    "RESURRECT_COMMAND",
    "RESURRECTABLE_BUILDINGS_OF",
    "RESURRECTABLE_BUILDINGS_POSITIVE",
    "RESURRECTABLE_FLAG",
    "RESURRECTABLE_UNITS_OF",
    "RESURRECTABLE_UNITS_POSITIVE",
    "REASON_AMBIGUOUS_CELL",
    "REASON_AMBIGUOUS_LEDGER",
    "REASON_INVALID_CELL",
    "REASON_INVALID_ITEM_ID",
    "REASON_INVALID_LEDGER",
    "REASON_NOT_RESURRECTABLE",
    "REASON_UNRESOLVABLE_CELL",
    "REASON_UNRESOLVABLE_LEDGER_ENTRY",
    "SEED_ENVIRONMENT",
    "SLOT_CELL_X",
    "SLOT_CELL_Y",
    "SLOT_ITEM_ID",
    "SLOT_PLAYER",
    "SYRINGE_DISCARD_NOTE",
    "SYRINGES_BUILDING_VALUES",
    "SYRINGES_UNIT_VALUES",
    "UNIT_ONLY_NOTE",
    "UNIT_PROPERTY_FLAGS",
    "ZERO_CONSUMER_COUNT",
    "ZERO_CONSUMER_COUNT_RECORDED",
    "ZERO_CONSUMER_FIELDS",
    "address_cell",
    "build_envelope",
    "committed_resurrectable",
    "committed_syringes",
    "data_field",
    "expected_ledger",
    "gates",
    "in_grid",
    "is_strict_int",
    "ledger_entries",
    "ledger_divergence",
    "neutral_vector",
    "parse_data_field",
    "parse_seed",
    "payload_json",
    "project_ledger",
    "project_resurrection",
    "resolve_target",
    "seed_ledger_from_environment",
    "unit_only_note",
    "validate_cell",
    "validate_seed",
    "validate_vector",
]


# ------------------------------------------------------------ the vocabulary --
def gates() -> List[Dict[str, Any]]:
    """Both legacy gates, in the helper's own order, as fresh records."""
    return [dict(gate) for gate in GATES]


def command_inventory() -> List[Dict[str, Any]]:
    """The three-door inventory as fresh records a caller may keep and mutate."""
    return [dict(entry) for entry in COMMAND_INVENTORY]


def ledger_reaching_commands() -> Tuple[str, ...]:
    """The named branches that reach the ledger, in committed source order."""
    return LEDGER_REACHING_COMMANDS


def refusals() -> List[Dict[str, Any]]:
    """The three recorded refusals as fresh records."""
    return [dict(entry) for entry in REFUSALS]


# ------------------------------------------------------------ derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D3).

    A revival has no derivable price and no syringe cost, and any cost a client
    attached would be a client-trusted mint or burn because ``do_command``
    applies the request's vector *before* the branch (``command.py:40``,
    ``engine.py:251-271``).  The only honest vector is the neutral one, and a
    fresh list is returned on every call so a caller cannot mutate the
    derivation for the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal: a positive entry would be a
    client-trusted mint and a negative one a client-trusted burn under legacy's
    ``max(current + delta, 0)`` clamp.  Refusing anything but zero is what
    forecloses the smuggling — the derivation cannot express it, so the
    endpoint cannot send it.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be an integer, got %r"
                % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d is %r: a revival moves no resource, "
                "so only the neutral all-zero vector is derivable" % (index, value),
            )
    return list(vector)


# ----------------------------------------------------------- the ledger ----
def project_ledger(raw: Any) -> Dict[str, Any]:
    """The **read-only** projection of ``privateState['deadHeroes']``, verbatim.

    Returns
        ``{ok, reason, error, resolvable, entries, entry_count, total,
        recorded_type, recorded_present, recorded_keys, recorded_state}``

    ``entries`` keeps each recorded **string** item id with its recorded count
    **exactly as recorded** — no threshold, no cap, no clamp, and no count
    derived from another.

    The projection is **fail-closed**.  An absent ledger, a non-object ledger, a
    non-string key, and a non-integer count are each reported as
    ``ok: false`` with ``resolvable: false``, the offending recorded state kept
    intact in ``recorded_state``, and **no** substituted entry — so an
    unresolvable ledger can never be read as an empty one.  The recorded keys
    are still reported, because "which keys are present" is a fact even when a
    value is unreadable.
    """
    header: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "resolvable": False,
        "entries": [],
        "entry_count": 0,
        "total": 0,
        "recorded_type": type(raw).__name__,
        "recorded_present": raw is not None,
        "recorded_keys": [],
        "recorded_state": raw,
    }
    if raw is None:
        header["error"] = (
            "privateState['deadHeroes'] is ABSENT (null): a save that never held "
            "the key receives an empty ledger from the version.py migration, "
            "never from gameplay, so this is reported UNRESOLVABLE rather than "
            "presented as an empty ledger that was resolved"
        )
        header["reason"] = REASON_INVALID_LEDGER
        return header
    if not isinstance(raw, Mapping):
        header["error"] = (
            "privateState['deadHeroes'] is %s, not a JSON object, so it is not a "
            "string-keyed count per item id" % type(raw).__name__
        )
        header["reason"] = REASON_INVALID_LEDGER
        return header
    for key in raw:
        if not isinstance(key, str):
            # A JSON object always carries string keys, so a non-string one can
            # only come from a caller-built mapping.  Report it rather than
            # coercing it: the ledger is a STRING-keyed count per item id.
            header["error"] = (
                "the ledger key %r is %s, not the text of an item id"
                % (key, type(key).__name__)
            )
            header["reason"] = REASON_INVALID_LEDGER
            return header
    keys = sorted(raw)
    header["recorded_keys"] = list(keys)
    entries: List[Dict[str, Any]] = []
    total = 0
    for key in keys:
        value = raw[key]
        if not is_strict_int(value):
            header["error"] = (
                "the ledger count for item id %r is %r, not an integer; the "
                "legacy helpers add and subtract it directly, so a non-integer "
                "is unreadable rather than coercible" % (key, value)
            )
            header["reason"] = REASON_INVALID_LEDGER
            return header
        entries.append({"item_id": key, "count": int(value)})
        total += int(value)
    header.update(
        {
            "ok": True,
            "resolvable": True,
            "entries": entries,
            "entry_count": len(entries),
            "total": total,
        }
    )
    return header


def ledger_entries(raw: Any) -> Dict[str, Any]:
    """A projected ledger's entries under their own keys, or a refusal.

    ``{item_id text: count}``, exactly as recorded.  Convenience over
    :func:`project_ledger` for the two callers that only need the mapping; it
    performs the identical projection, so there is no second definition that
    could drift.
    """
    projection = project_ledger(raw)
    if not bool(projection.get("ok", False)):
        raise EnvelopeError(
            str(projection.get("reason", REASON_INVALID_LEDGER)),
            str(projection.get("error", "")),
        )
    return {str(entry["item_id"]): int(entry["count"]) for entry in projection["entries"]}


def expected_ledger(before: Any, item_id: Any) -> Dict[str, Any]:
    """The ledger the decrement leaves behind, with the delete-at-zero rule.

    Reproduces ``engine.resurrect_hero`` (``engine.py:172-182``) exactly:

    * an item id the ledger does not hold is a **silent no-op** — the helper
      returns before touching anything — so the ledger is unchanged and
      ``removed`` is ``False``;
    * a count of ``1`` decrements to zero and the key is **DELETED**, never
      stored as a zero;
    * a count above ``1`` decrements and the key stays.

    The surviving entries keep their recorded **string** keys and their recorded
    insertion order, so a comparison against the persisted ledger is a
    value comparison rather than a re-ordering.
    """
    projection = project_ledger(before)
    if not bool(projection.get("ok", False)):
        raise EnvelopeError(
            str(projection.get("reason", REASON_INVALID_LEDGER)),
            str(projection.get("error", "")),
        )
    if not is_strict_int(item_id):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "item_id must be an integer, got %s" % type(item_id).__name__,
        )
    key = str(int(item_id))
    out: Dict[str, int] = {}
    for entry in projection["entries"]:  # type: ignore[union-attr]
        out[str(entry["item_id"])] = int(entry["count"])
    present = key in out
    count_before = out.get(key, 0)
    count_after = max(0, count_before - 1)
    removed = False
    if present:
        if count_after <= 0:
            del out[key]
            removed = True
        else:
            out[key] = count_after
    return {
        "entries": out,
        "present_before": present,
        "count_before": count_before,
        "count_after": count_after,
        "removed": removed,
        "item_id": key,
    }


def ledger_divergence(before: Any, after: Any, item_id: Any) -> Optional[str]:
    """The first way the persisted ledger diverges from the derivation, or None.

    The **first half** of the endpoint's two-part post-execution proof, kept
    here so the endpoint and the offline tests compare against *one* derivation
    instead of two hand-written checks.
    """
    derived = expected_ledger(before, item_id)
    projection = project_ledger(after)
    if not bool(projection.get("ok", False)):
        return "the persisted ledger is unreadable: %s" % str(projection.get("error", ""))
    persisted = {
        str(entry["item_id"]): int(entry["count"])
        for entry in projection["entries"]  # type: ignore[union-attr]
    }
    if derived["removed"] and str(item_id) in persisted:
        return (
            "the ledger still holds item id %r with count %r after a revival that "
            "reached zero: engine.resurrect_hero DELETES the key at zero "
            "(engine.py:178-179), never stores a zero"
            % (str(item_id), persisted[str(item_id)])
        )
    for key, value in derived["entries"].items():
        if persisted.get(key) != value:
            return (
                "the ledger holds %r = %r after the revival, not the derived %r"
                % (key, persisted.get(key), value)
            )
    for key, value in persisted.items():
        if key in derived["entries"]:
            continue
        before_value = before.get(key) if isinstance(before, Mapping) else None
        if value != before_value:
            return (
                "the revival moved ledger entry %r from %r to %r, which the "
                "decrement never does" % (key, before_value, value)
            )
    return None


# ------------------------------------------------------ the cell resolution --
def validate_cell(x: Any, y: Any) -> Tuple[int, int]:
    """Check an addressed cell structurally, or refuse it.

    Only **strict** integers are legal.  A ``bool`` is an ``int`` in Python and
    would address cell (0/1, 0/1); a float would address a cell legacy's own
    ``int``-free comparison would never match; and a string would raise out of
    the row comparison.  All three are refused here, before the dispatcher runs.

    Grid bounds are **anchor-based** (``0..GRID_EXTENT-1``), the same rule the
    move and placement derivations use.  That is a structural refusal on a shape
    the legacy branch never validated; it is recorded as such and is *not* a
    gameplay claim, and it is the only bounds notion in this contract.
    """
    if not is_strict_int(x) or not is_strict_int(y):
        raise EnvelopeError(
            REASON_INVALID_CELL,
            "x and y must be integers, got %s/%s"
            % (type(x).__name__, type(y).__name__),
        )
    if not in_grid(x, y):
        raise EnvelopeError(
            REASON_INVALID_CELL,
            "the addressed cell (%r, %r) is outside the 0..%d town grid"
            % (x, y, GRID_EXTENT - 1),
        )
    return int(x), int(y)


def address_cell(items: Any, x: Any, y: Any) -> Dict[str, Any]:
    """Resolve an addressed cell to the map key that stands there.

    Returns
        ``{ok, reason, error, map_keys, map_key, resolved, ambiguous,
        cell_recorded, row_recorded, occupant_item_id}``

    Every placement row records its own committed ``(x, y)`` in slots 1 and 2
    (``engine.map_add_item``, ``engine.py:31``), so the cell is an addressable
    object in committed state.  **Zero** rows → ``unresolvable_cell``; **more
    than one** → ``ambiguous_cell`` rather than an invented tie-break.  A row
    that is not a row is never read as standing at any cell.
    """
    cell_x, cell_y = validate_cell(x, y)
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "map_keys": [],
        "map_key": None,
        "resolved": False,
        "ambiguous": False,
        "cell_recorded": [x, y],
        "row_recorded": None,
        "occupant_item_id": None,
    }
    if not isinstance(items, Mapping):
        out["reason"] = REASON_INVALID_LEDGER
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
        if row[SLOT_CELL_X] == cell_x and row[SLOT_CELL_Y] == cell_y:
            matches.append(str(key))
    matches.sort(key=lambda text: int(text) if text.lstrip("-").isdigit() else 0)
    out["map_keys"] = matches
    if not matches:
        out["reason"] = REASON_UNRESOLVABLE_CELL
        out["error"] = (
            "no placement row records the cell (%d, %d), so the addressed cell "
            "resolves to no revival target" % (cell_x, cell_y)
        )
        return out
    if len(matches) > 1:
        out["ambiguous"] = True
        out["reason"] = REASON_AMBIGUOUS_CELL
        out["error"] = (
            "%d placement rows record the cell (%d, %d) (%s), and the legacy "
            "contract records no tie-break between them, so none is invented "
            "here" % (len(matches), cell_x, cell_y, ", ".join(matches))
        )
        return out
    key = matches[0]
    row = items[key]
    out.update(
        {
            "ok": True,
            "reason": "",
            "error": "",
            "map_key": int(key),
            "resolved": True,
            "row_recorded": list(row),
            "occupant_item_id": row[SLOT_ITEM_ID],
        }
    )
    return out


# ------------------------------------------------- the committed flag ------
def committed_resurrectable(properties: Any) -> Optional[int]:
    """One committed definition's ``properties.resurrectable``, or ``None``.

    The legacy helper reads the **raw configuration string** through
    ``get_attribute_from_item_id`` and then ``json.loads`` it
    (``engine.py:154-162``), while the committed normalized package stores
    ``properties`` as an **object**.  Both representations are accepted here,
    which is the R2 coercion boundary M8 line 1 recorded: the legacy reads are
    not against the committed normalized bytes, and the two agree on *values*,
    never on *representation*.

    ``None`` means **absent or unreadable**, which the helper treats as a
    refusal (``engine.py:159-160``).  A committed flag is a *string* in the
    normalized package, so it is converted explicitly: a non-empty String is
    truthy in GDScript and in Python a non-empty ``str`` is truthy too, so
    ``int(value or 0)`` would collapse the committed ``"0"`` to the integer one.
    An explicit conversion is the only correct read.
    """
    decoded: Any = properties
    if isinstance(decoded, (str, bytes)):
        text = decoded.decode("utf-8", "replace") if isinstance(decoded, bytes) else decoded
        if text.strip() == "":
            # push_dead_unit tests `if not properties: return False`, so an EMPTY
            # blob is an absent flag - a refusal, never a decode failure.
            return None
        try:
            decoded = json.loads(text)
        except ValueError as error:
            raise EnvelopeError(
                REASON_INVALID_ITEM_ID,
                "the committed properties blob is not valid JSON: %s" % error,
            )
    if not isinstance(decoded, Mapping):
        return None
    if RESURRECTABLE_FLAG not in decoded:
        return None
    raw = decoded[RESURRECTABLE_FLAG]
    if isinstance(raw, bool):
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not (text.lstrip("-").isdigit()):
            return None
        return int(text)
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float) and raw == int(raw):
        return int(raw)
    return None


def committed_syringes(item: Any) -> Optional[int]:
    """One committed item's ``syringes`` field, or ``None`` when it carries none.

    ``syringes`` is a **top-level** item field, not a ``properties`` flag: it is
    carried by all 429 committed units and all 470 committed buildings, takes
    **6 distinct values** over the units, and has **zero** occurrences across the
    seven legacy modules.  It is therefore **content only** — reported, never
    used to compute a cost, because charging one would invent an economy the
    repository does not contain.
    """
    if not isinstance(item, Mapping) or "syringes" not in item:
        return None
    raw = item["syringes"]
    if isinstance(raw, bool):
        return None
    if isinstance(raw, str):
        text = raw.strip()
        return int(text) if text.lstrip("-").isdigit() else None
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float) and raw == int(raw):
        return int(raw)
    return None


def unit_only_note() -> str:
    """The measured unit-only distribution, read from this module's constants."""
    return UNIT_ONLY_NOTE


# ----------------------------------------------------------- the resolution --
def resolve_target(
    items: Any, ledger: Any, x: Any, y: Any, item_of: Any
) -> Dict[str, Any]:
    """Resolve an addressed cell to a revival target, or refuse it.

    ``item_of`` is a callable taking the resolved **item id** and returning that
    item's committed configuration row (or ``None``), so this module reads
    committed content through a parameter and never resolves it itself.  The row
    is the **raw** configuration shape ``push_dead_unit`` reads: its
    ``properties`` is the RAW JSON **string** the helper ``json.loads``es
    (``engine.py:154-162``) and its ``syringes`` is the top-level item field.
    The committed normalized package stores ``properties`` as an **object**
    instead — the R2 coercion boundary M8 line 1 recorded — so both
    representations are accepted and the two are read on their own terms.

    Returns
        ``{ok, reason, error, map_key, item_id, count_before, cell,
        occupant_item_id, committed_resurrectable, committed_syringes,
        gates, refusal}``

    Both gates are evaluated here, in the order ``push_dead_unit`` evaluates
    them, and **no third** is evaluated.  Every refusal resolves **before** the
    legacy dispatcher runs, so the corpus is byte-identical on all of them.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "reason": "",
        "error": "",
        "map_key": None,
        "item_id": None,
        "count_before": 0,
        "cell": [x, y],
        "occupant_item_id": None,
        "committed_resurrectable": None,
        "committed_syringes": None,
        "gates": gates(),
        "refusal": None,
        "resolution_rule": RESOLUTION_RULE,
        "rejected_resolution": REJECTED_RESOLUTION,
    }
    try:
        addressed = address_cell(items, x, y)
    except EnvelopeError as failure:
        out["reason"] = failure.code
        out["error"] = str(failure)
        out["refusal"] = failure.code
        return out
    out["occupant_item_id"] = addressed.get("occupant_item_id")
    out["map_key"] = addressed.get("map_key")
    if not bool(addressed.get("ok", False)):
        out["reason"] = str(addressed.get("reason", ""))
        out["error"] = str(addressed.get("error", ""))
        out["refusal"] = str(addressed.get("reason", ""))
        return out

    projection = project_ledger(ledger)
    if not bool(projection.get("ok", False)):
        out["reason"] = REASON_INVALID_LEDGER
        out["error"] = str(projection.get("error", ""))
        out["refusal"] = REASON_INVALID_LEDGER
        return out
    entries = {
        str(entry["item_id"]): int(entry["count"])
        for entry in projection["entries"]  # type: ignore[union-attr]
    }
    if not entries:
        out["reason"] = REASON_UNRESOLVABLE_LEDGER_ENTRY
        out["error"] = (
            "the addressed cell (%s, %s) resolves to no recorded ledger entry: "
            "the player's deadHeroes ledger is EMPTY, so there is nothing to "
            "revive there"
            % (str(x), str(y))
        )
        out["refusal"] = out["reason"]
        return out
    if len(entries) > 1:
        out["reason"] = REASON_AMBIGUOUS_LEDGER
        out["error"] = (
            "the player's deadHeroes ledger holds %d entries (%s) and the legacy "
            "contract records no rule for choosing between them from a cell, so "
            "none is invented here"
            % (len(entries), ", ".join(sorted(entries, key=lambda t: int(t))))
        )
        out["refusal"] = out["reason"]
        return out
    item_id = sorted(entries, key=lambda text: int(text))[0]
    out["item_id"] = int(item_id)
    out["count_before"] = int(entries[item_id])

    item = item_of(int(item_id))
    flag = committed_resurrectable(
        item.get(PROPERTIES_FIELD) if isinstance(item, Mapping) else None
    )
    out["committed_resurrectable"] = flag
    out["committed_syringes"] = committed_syringes(item)
    if flag is None:
        out["reason"] = REASON_NOT_RESURRECTABLE
        out["error"] = (
            "the resolved ledger entry names item id %s, whose committed "
            "properties carry NO resurrectable flag; push_dead_unit refuses an "
            "absent flag (engine.py:159-160), so this entry could never have "
            "entered the ledger through the legacy increment"
            % item_id
        )
        out["refusal"] = out["reason"]
        return out
    if flag <= 0:
        out["reason"] = REASON_NOT_RESURRECTABLE
        out["error"] = (
            "the resolved ledger entry names item id %s, whose committed "
            "resurrectable is %d; push_dead_unit requires it to be greater than "
            "zero (engine.py:162), so this entry is not resurrectable"
            % (item_id, flag)
        )
        out["refusal"] = out["reason"]
        return out
    out.update({"ok": True, "reason": "", "error": "", "refusal": None})
    return out


def project_resurrection(
    items: Any, ledger: Any, x: Any, y: Any, item_of: Any
) -> Dict[str, Any]:
    """The whole read-only projection of one addressed revival, or its refusal.

    The single entry point the endpoint uses, so the resolution, both gates, and
    the delete-at-zero derivation exist in exactly one place.
    """
    target = resolve_target(items, ledger, x, y, item_of)
    projection = project_ledger(ledger)
    out = {
        "projection": target,
        "ledger_before": projection,
        "ledger_after": None,
        "map_key": target.get("map_key"),
        "item_id": target.get("item_id"),
        "count_before": target.get("count_before", 0),
        "count_after": None,
        "removed": False,
        "syringe_charged": 0,
        "resource_delta": neutral_vector(),
        "syringe_discarded": DERIVED_USED_SYRINGE,
        "syringe_discard_note": SYRINGE_DISCARD_NOTE,
        "no_syringe_cost": NO_SYRINGE_COST,
        "no_combat": NO_COMBAT,
        "no_placement_validation": NO_PLACEMENT_VALIDATION,
        "no_third_gate": NO_THIRD_GATE,
        "clicks_to_build_boundary": CLICKS_TO_BUILD_BOUNDARY,
    }
    if bool(target.get("ok", False)):
        derived = expected_ledger(ledger, target["item_id"])
        out["ledger_after"] = {
            "entries": [
                {"item_id": key, "count": value}
                for key, value in derived["entries"].items()  # type: ignore[union-attr]
            ],
            "entry_count": len(derived["entries"]),  # type: ignore[arg-type]
            "total": sum(derived["entries"].values()),  # type: ignore[arg-type]
            "resolvable": True,
        }
        out["count_after"] = derived["count_after"]  # type: ignore[index]
        out["removed"] = derived["removed"]  # type: ignore[index]
    return out


# ----------------------------------------------------- the verification seam --
def validate_seed(raw: Any) -> Dict[str, int]:
    """Parse one ``COMPAT_SEED_DEAD_HEROES`` value into ``{item_id: count}``.

    The format is ``item_id=count`` pairs separated by commas, e.g.
    ``"1001=2"``.  Every pair must name a non-negative integer item id and a
    **positive** integer count: a zero seed would be a ledger entry the legacy
    decrement deletes without ever having been incremented, which is a state
    legacy cannot produce.  A malformed value is a named refusal, never a
    silent no-op.
    """
    text = ("" if raw is None else str(raw)).strip()
    if text == "":
        raise EnvelopeError(SEED_ENVIRONMENT, "the seed value is empty")
    bag: Dict[str, int] = {}
    for part in text.split(","):
        chunk = part.strip()
        if chunk == "":
            raise EnvelopeError(
                SEED_ENVIRONMENT, "the seed value has an empty pair in %r" % text
            )
        if "=" not in chunk:
            raise EnvelopeError(
                SEED_ENVIRONMENT,
                "the seed pair %r is not item_id=count" % chunk,
            )
        item_text, count_text = chunk.split("=", 1)
        item_text = item_text.strip()
        count_text = count_text.strip()
        if not item_text.isdigit() or not count_text.isdigit():
            raise EnvelopeError(
                SEED_ENVIRONMENT,
                "the seed pair %r must name two non-negative integers" % chunk,
            )
        count = int(count_text)
        if count < 1:
            raise EnvelopeError(
                SEED_ENVIRONMENT,
                "the seed count for item id %s is %d: a zero count is a ledger "
                "entry legacy's increment never produces" % (item_text, count),
            )
        bag[item_text] = count
    return bag


def parse_seed(raw: Any) -> Optional[Dict[str, int]]:
    """The parsed seed, or ``None`` when the environment variable is absent.

    Absent is ``None``, never an empty bag: an unset variable and an empty one
    are different states and only the second is a named refusal.
    """
    if raw is None:
        return None
    return validate_seed(raw)


def seed_ledger_from_environment(save: Any, raw: Any = None) -> Dict[str, Any]:
    """Seed a **disposable** save's ledger from the environment, or do nothing.

    Returns
        ``{seeded, reason, error, before, after}``

    The write is in-memory only, exactly as the unit-level suite's
    :func:`set_state` writes a disposable corpus copy: it is a verification
    seam, never a claim about legacy behaviour, and it never targets a
    committed save.  An **absent** variable leaves the save untouched and is
    reported as ``seeded: False`` with ``reason: "not requested"``.
    """
    if raw is None:
        raw = os.environ.get(SEED_ENVIRONMENT)
    result: Dict[str, Any] = {
        "seeded": False,
        "reason": "not requested" if raw is None else "",
        "error": "",
        "before": None,
        "after": None,
    }
    private = (save or {}).get(PRIVATE_STATE_KEY) if isinstance(save, Mapping) else None
    if not isinstance(private, dict):
        result["reason"] = SEED_ENVIRONMENT
        result["error"] = "the save carries no privateState object"
        return result
    before = private.get(LEDGER_KEY)
    result["before"] = None if before is None else dict(before)
    if raw is None:
        return result
    try:
        bag = validate_seed(raw)
    except EnvelopeError as failure:
        result["reason"] = SEED_ENVIRONMENT
        result["error"] = str(failure)
        return result
    private[LEDGER_KEY] = dict(bag)
    result["seeded"] = True
    result["after"] = dict(bag)
    return result


# ------------------------------------------------------------ the envelope --
def build_envelope(
    map_key: Any,
    item_id: Any,
    x: Any,
    y: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one revival.

    ``map_key`` and ``item_id`` are **service-derived** values (see
    :func:`resolve_target`), never client-sent, and ``used_syringe`` is the
    derived inert ``0``.  The batch carries **exactly one** command and a
    **neutral** vector (design D3): no price, no cost, and no resource delta is
    expressed here, because none is derivable and none is accepted from a
    client.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread
    by legacy code, so parity normalizes it).  Raises :class:`EnvelopeError`
    with ``invalid_map_key``, ``invalid_item_id``, ``invalid_coordinates``,
    ``invalid_vector``, or ``invalid_timestamp``.  Whether the addressed cell is
    free, whether the named ledger entry exists, and whether its committed flag
    is positive are all resolved by :func:`resolve_target` **before** this is
    called — this function validates shape only.
    """
    if not is_strict_int(map_key):
        raise EnvelopeError(
            "invalid_map_key",
            "map_key must be an integer, got %s" % type(map_key).__name__,
        )
    if not is_strict_int(item_id):
        raise EnvelopeError(
            REASON_INVALID_ITEM_ID,
            "item_id must be an integer, got %s" % type(item_id).__name__,
        )
    cell_x, cell_y = validate_cell(x, y)
    checked = validate_vector(neutral_vector())
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [
            [
                0,
                RESURRECT_COMMAND,
                [
                    int(map_key),
                    int(item_id),
                    cell_x,
                    cell_y,
                    DERIVED_USED_SYRINGE,
                ],
                checked,
            ]
        ],
    }