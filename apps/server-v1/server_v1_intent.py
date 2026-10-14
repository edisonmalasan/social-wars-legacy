#!/usr/bin/env python3
"""Request-intent parsing: what a v1 request is allowed to say.

**Task 2.4 and design D3.**  A v1 request expresses *what the player wants to
happen*.  It never expresses what it costs or what it yields.  This module is
the only place a request body becomes an intent, and it **refuses** — never
clamps, coerces, ignores, or partially honours — any request that carries a
resource, experience, health, damage, or result delta.

Why refusal rather than the two alternatives, both named in design D3:

* **Clamping** reproduces the anti-pattern under new names.  The preserved
  server applies an eight-slot client vector at ``command.py:40`` before the
  first branch condition is tested at ``:42``, each slot as
  ``max(current + delta, 0)`` (``engine.py:251-271``).  v1 refuses the vector,
  so the clamp has nothing to clamp.
* **Ignoring** the field is worse than clamping: a request carrying a delta
  would answer success, and the client would believe it paid a different
  amount.  A refusal is a value the client can distinguish from a transport
  failure, which is the spec's own requirement.

The refusal vocabulary is a **closed key set per action**, and this is a
narrowing of v0's behaviour on purpose.  v0's envelopes parse six keys and
discard five of them; a v1 request carrying any key outside the action's schema
is refused with ``unknown_request_field`` rather than dropped.  Two distinct
codes are used for one decision so the refusal *says which* it is:

``client_supplied_delta``
    the request carried a field whose name is a known delta-shaped field —
    one of the seven stored resources' names, ``xp``, or one of the explicitly
    listed legacy shapes (``resources_changed``, ``hp``, ``health``, ``damage``,
    ``result``, ``deltas``, ``resources``, ``amount``, ``price``, ``cost``,
    ``rewards``, ``payout``, ``amounts``, ``gains``, ``income``, ``vector``) —
    under **any** spelling a request could plausibly use.  This is the D3 case
    and it is refused as a structural input error, 400.

``unknown_request_field``
    the request carried any other key the action's schema does not define.

The delta-key check is **case-insensitive** and matches a declared delta word
against the whole key or against one half of it (see :func:`_is_delta_key`),
so ``Gold``, ``GOLD``, ``wood_delta``, and ``resources_Changed`` are all
recognised.  A bare-substring match was tried first and rejected while writing
this module: it would classify an innocent key such as ``wooden_fence_style``
as a delta attempt.  Matching is narrower still — a key that merely *contains*
a resource word, as ``instant_cost_report`` or ``my_gold_pick`` do, is
``unknown_request_field`` rather than a false delta accusation.  Both
directions of that distinction are pinned over the whole vocabulary by
``tests/test_intent.py``.

The allowed keys for the three delivered actions:

``collect``
    ``player_id`` — the save this intent is about, a non-empty string.  ``row``
    — the addressable placed row, a **non-negative** integer.  Both required.

``collection``
    ``player_id`` — the save this intent is about, a non-empty string.
    ``collection_id`` — the committed collection id, an integer that **may be
    zero or negative**, so the slice can refuse it as an *aliased id* rather
    than the request layer calling it malformed (see
    :data:`NON_NEGATIVE_ADDRESSING`).  Both required.

``magic``
    ``player_id`` — the save this intent is about, a non-empty string.
    ``magic_id`` — the committed magic id, an integer that **may be zero or
    negative**: the preserved ``buy_magic``/``use_magic`` branches never index
    the committed table, so there is no positional clamp for a non-positive id
    to alias and the slice refuses it as ``unknown_magic_id`` rather than this
    layer calling it malformed (see :data:`NON_NEGATIVE_ADDRESSING`).
    ``operation`` — one of the closed set in :data:`INTENT_OPERATION_VALUES`.
    All three required.

``combat``
    ``player_id`` — the save this intent is about, a non-empty string.
    ``unit_id`` — the committed unit identity, an integer that **may be zero or
    negative**, for the same measured reason as ``magic_id``: the preserved
    ``end_attack`` branch never indexes the committed table, so zero and every
    negative id name no row rather than aliasing a position.  Both required, and
    **no** third key: the route carries exactly one action, so there is no
    ``operation`` row for it in :data:`INTENT_OPERATION_FIELDS`.

``reward``
    ``player_id`` — the save this intent is about, a non-empty string.
    ``operation`` — one of ``weekly`` or ``daily``, the two reward cursors the
    preserved server keeps (design D1 of the reward line).  Both required.

    **This is the first delivered action with no addressing field.**  Every
    other action names the row, ledger, or content row it is about; a reward
    transaction names a *cursor*, and the cursor's position is what v1 must
    **derive** from recorded state — so accepting it from the client is the one
    thing this line exists to prevent.  Declared in
    :data:`NO_ADDRESSING_FIELD_ACTIONS` rather than inferred from the schema's
    length, and :meth:`Intent.addressed_path` reports ``/privateState`` — the
    container, truthfully, because the specific key is the domain's to resolve
    and report.

``combat`` — ``player_id``, ``unit_id``.  See above.
    ``reward`` — ``player_id``, ``operation``.  See above; the first action with
    no addressing field.

Each action's schema is closed over its own keys, so a ``collect`` request
that carries ``collection_id`` is an ``unknown_request_field`` and vice versa.
Nothing else is accepted.  Notably absent and deliberately *not* accepted:
``amount``, ``resource``, ``tier``, ``time``, ``now``, ``price``, ``cash``,
``prize``, ``item_ids`` and any of the delta keys.

**Two shapes are recognised rather than merely unknown, and both are decided by
the domain.**  Recognition is a request-layer act; the *reason* is not, because
a layer that only reads key names has no rule about what the transaction would
have done.

``attacker_units``
    The preserved ``end_attack`` branch's *actual* destruction wire shape — the
    list whose ``unit[2] - unit[3]`` is the count it destroys
    (``command.py:866-872``) — so a request carrying it is refused by name,
    through :data:`DESTRUCTION_KEYS`, rather than being treated as an arbitrary
    unknown key.  The refusal is the **domain's**
    (``client_dictated_destruction``, 409), and this module carries the figure
    **verbatim** in :attr:`Intent.destruction_request` and computes nothing from
    it.  The sibling spellings ``victim`` and ``victim_units`` are **not** in
    that set: neither is a destruction, so both remain
    ``unknown_request_field`` (400).

``next_id``, ``offset``, ``successor``, and the grant shapes
    The reward line's five channels (design D5): a client-sent cursor
    contribution (:data:`REWARD_CURSOR_KEYS`, carried verbatim in
    :attr:`Intent.cursor_request`) and a client-sent grant
    (:data:`REWARD_GRANT_KEYS`, carried in :attr:`Intent.grant_request`).
    Recognised here, refused **by the domain by name** — the spec requires each
    grant shape to be "refused with its own named reason", which a single
    ``unknown_request_field`` cannot express.  This module carries the **channel
    name**, never a refusal code, for the reason recorded on
    :func:`parse_intent`.

**The cursor channel is resolved before the grant channels**, which is a
deliberate, recorded **difference from v0**: ``apps/compat-api``'s
``CLIENT_KEY_REFUSALS`` is ordered item, item_index, cell, player, next_id,
amount, price (``rewards_envelope.py:830-838``), so a v0-shaped request naming
both a cursor and a grant is answered about the grant.  v1 answers about the
cursor first because the cursor is the one input this line exists to make
impossible, and naming the cursor says the more important thing about the
request.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Dict, FrozenSet, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from server_v1_refusals import Refusal, RefusalCode

#: The delivered actions.  A mapping rather than a single constant, so the
#: allowed key set is a property of the *action* and adding a route adds a row
#: instead of a branch.
INTENT_SCHEMAS: Dict[str, FrozenSet[str]] = {
    "collect": frozenset({"player_id", "row"}),
    "collection": frozenset({"player_id", "collection_id"}),
    "magic": frozenset({"player_id", "magic_id", "operation"}),
    "combat": frozenset({"player_id", "unit_id"}),
    "reward": frozenset({"player_id", "operation"}),
}

#: The one addressing field each action requires, and therefore the one field
#: that tells the two intents apart.  Deliberately a **second** row per action
#: rather than a branch at the parse site, so adding a route cannot forget to
#: declare how it is addressed: the closed key set above already guarantees
#: exactly this field is present, because for every delivered action
#: ``allowed == required``.  That held for the first two actions and is
#: **deliberately no longer true**: ``magic`` carries a third key, ``operation``,
#: which is a required key but **not** an addressing field.  The addressing
#: contract that does hold is stated by :data:`ADDRESSING_FIELDS` on its own, and
#: the extra key is declared beside it in :data:`INTENT_OPERATION_FIELDS` rather
#: than being inferred from a schema's length.
#:
#: **``reward`` is the one action with no row here**, and the exception is
#: declared in :data:`NO_ADDRESSING_FIELD_ACTIONS` so that
#: ``ADDRESSING_FIELDS[action]`` is never reached for it.  It is not a gap: a
#: reward transaction addresses a **cursor**, and the cursor's successor is the
#: one value this line derives rather than accepts (design D5).
ADDRESSING_FIELDS: Dict[str, str] = {
    "collect": "row",
    "collection": "collection_id",
    "magic": "magic_id",
    "combat": "unit_id",
}

#: The delivered actions that declare **no** addressing field.
#:
#: ``reward`` is the only member.  A reward request names a player and an
#: operation and nothing else: the cursor it would advance is derived from the
#: recorded document, so there is no address for the client to supply, and
#: :meth:`Intent.addressed_path` reports the container ``/privateState`` — where
#: both cursors live — rather than inventing a pointer to a key the domain has
#: not yet read.  Declared rather than inferred, so the parse site's
#: ``ADDRESSING_FIELDS[action]`` lookup is total over the delivered actions and
#: a sixth action cannot join the reward shape by accident.
NO_ADDRESSING_FIELD_ACTIONS: FrozenSet[str] = frozenset({"reward"})

#: The one action that declares no operation field, named as data.
#:
#: ``combat`` is the one delivered action whose schema length equals its
#: addressing contract, so it is also the one where the extra-key argument on
#: :data:`ADDRESSING_FIELDS` does not apply: the route carries exactly one
#: action, and a second operation name over a single action would be line 3's D7
#: problem restated on a route with nothing to distinguish.  Declared rather than
#: inferred so a future fifth action cannot add an operation by accident.
NO_OPERATION_FIELD_ACTIONS: FrozenSet[str] = frozenset({"combat"})

#: The preserved branches' **actual destruction wire shapes**, per action.
#:
#: ``attacker_units`` is not an invented spelling: it is the name the preserved
#: ``end_attack`` branch gives the list it iterates at ``command.py:866``, whose
#: ``unit[2] - unit[3]`` is the number of rows the transaction destroys
#: (``command.py:868-872``).  Recognising it is what lets a v1 request that
#: speaks the preserved dialect be refused **by name** -- the domain's own
#: ``client_dictated_destruction`` (409) -- rather than as an arbitrary unknown
#: key, while the domain still never computes a count from it.
#:
#: **Only the destruction shape is listed.**  ``victim`` and ``victim_units`` are
#: not destruction figures, so they stay ``unknown_request_field`` (400); adding
#: them here would widen the rule from "names what would be destroyed" to "looks
#: like the branch", which is the substring-matching mistake
#: :func:`_is_delta_key` records and rejected.
DESTRUCTION_KEYS: Dict[str, FrozenSet[str]] = {
    "combat": frozenset({"attacker_units"}),
}

#: Client-sent **reward-cursor** keys, recognised per action and carried
#: verbatim into :attr:`Intent.cursor_request` (design D5).
#:
#: **The only action that has a row is ``reward``,** and it is the only place in
#: the repository where a cursor may be sent at all: every other action's target
#: is an address, and an address the client may name.  A reward cursor is the
#: opposite — it is the value v1 derives — so recognising its spellings lets the
#: domain refuse them **by name** instead of answering a v0-shaped request as an
#: arbitrary unknown field.
#:
#: **Every entry is anchored, and the three kinds of anchor are labelled.**
#:
#: ``next_id``
#:     **Measured.**  It is the preserved branch's own argument name: the daily
#:     branch computes ``next_id = args[1] + 1`` (``command.py:445``), and
#:     ``apps/compat-api/rewards_envelope.py:835`` refuses exactly this spelling
#:     as ``client_supplied_next_id``.
#: ``offset``, ``successor``
#:     **Quoted from the line's own spec**, which names "a next id, an offset, or
#:     any other cursor contribution" as the things a request must not carry.
#:     ``offset`` and ``successor`` are the two additional words it spells, and
#:     neither is a v0 spelling — they are here because the spec promises the
#:     refusal covers "any other cursor contribution", and a rule that only knew
#:     ``next_id`` would not.
#: ``bonus_next_id``, ``weekly_reward_index``
#:     **Derived** from the two stored field names in snake_case
#:     (``bonusNextId`` and ``weeklyRewardIndex``, per
#:     ``apps/compat-api/rewards_envelope.py``).  A client holding a save, or one
#:     built from the stored shape, names the field it knows; refusing that by
#:     name is the difference between "you may not dictate the cursor" and "that
#:     key does not exist".
#:
#: **Deliberately not widened** to ``cursor``, ``next_cursor``, ``new_cursor`` or
#: ``index``: none of those is a preserved spelling, a spec word, or a stored
#: field name, and adding them would be the substring-matching mistake
#: :func:`_is_delta_key` records and rejected.  A key outside this set is
#: ``unknown_request_field`` (400) — a *different* and equally correct answer
#: for a key that is not a cursor contribution.
REWARD_CURSOR_KEYS: Dict[str, FrozenSet[str]] = {
    "reward": frozenset(
        {
            "next_id",
            "offset",
            "successor",
            "bonus_next_id",
            "weekly_reward_index",
        }
    ),
}

#: Client-sent **reward-grant** keys, recognised per action and carried into
#: :attr:`Intent.grant_request` **keyed by channel**, never by value
#: (design D5).
#:
#: The spec requires that a request carrying "an item id, a cell, a player
#: identity, or a map index" has "each ... refused with its own named reason", so
#: the *channel* — not the refusal code — is what crosses the layer boundary:
#: this module names ``"item"``, and ``server_v1_reward.py`` owns the mapping from
#: channel to reason.  A layer that only reads key names has no rule about what a
#: transaction would have granted, which is the same division the destruction
#: channel records.
#:
#: **Every channel and every spelling is anchored.**
#:
#: ``item``, ``item_index``, ``cell``, ``player``
#:     **Measured** — these are four of the seven rows of v0's
#:     ``CLIENT_KEY_REFUSALS`` (``rewards_envelope.py:830-838``), each refused
#:     there by its own code, and each read by the preserved branches: the daily
#:     arm writes the client's item id into storage and a deduplicating unit list
#:     (``command.py:444-463``), and the weekly arm reads a cell and a player
#:     from the client (``command.py:345-363``).
#: ``x``, ``y``
#:     **Measured** — v0's own aliases for ``cell``
#:     (``rewards_envelope.py:847-848``).  Both map to the ``cell`` channel, so
#:     a request sending ``x`` and ``y`` is still one refusal about one cell.
#:
#: ``amount`` and ``price`` are **not** here: they are already declared delta
#: words, so they are refused earlier and by a different code
#: (``client_supplied_delta``), and duplicating them would make which of the two
#: answers depends on the order of two tables.
REWARD_GRANT_KEYS: Dict[str, Dict[str, str]] = {
    "reward": {
        "item": "item",
        "item_index": "map_index",
        "cell": "cell",
        "x": "cell",
        "y": "cell",
        "player": "player",
    },
}

#: The four grant channels, closed, in the order the domain resolves them.
#:
#: Closed so the domain's channel-to-reason mapping is total over the carried
#: set: a request naming a channel outside this list could not be answered, so
#: ``tests/test_intent.py`` asserts :data:`REWARD_GRANT_KEYS` is closed over it.
#: **The order is v1's, not v0's** — see the module docstring's note on the
#: cursor channel.
REWARD_GRANT_CHANNELS: Tuple[str, ...] = ("item", "map_index", "cell", "player")

#: The one **non-addressing** required key each action declares, and therefore
#: the one field whose *value* is a closed vocabulary rather than an address.
#:
#: ``operation`` is the third key of the magic intent and exists because the
#: preserved surface really does distinguish two request kinds
#: (``buy_magic``/``use_magic``), so collapsing them at the request layer would
#: either discard the client's intent or force the domain to guess which branch
#: it is standing in for.  It is declared here **as data** rather than as an
#: ``if`` in :func:`parse_intent` or in the transport, for the reason design D1
#: of the magic line records: a closed set that lives in a table cannot be
#: extended by editing a branch, and ``tests/test_intent.py`` asserts every
#: declared action with a value set closes over exactly the values it declares.
#:
#: The reward line adds ``reward`` here, which is what makes
#: :data:`NO_OPERATION_FIELD_ACTIONS` a one-member set rather than the whole
#: complement: the preserved reward surface distinguishes **two** arms
#: (``weekly_reward``/``win_daily_bonus``) over one cursor field each, so it has
#: exactly the structure the magic line introduced ``operation`` for.
INTENT_OPERATION_FIELDS: Dict[str, str] = {
    "magic": "operation",
    "reward": "operation",
}

#: The closed value set for each declared operation field, keyed by the **action**
#: rather than by the field's name.
#:
#: **Rekeyed from the field name by the reward line, and the old keying was a
#: latent defect.**  The first version was keyed ``"operation"``, with the
#: comment above it promising that "a second action reusing ``operation`` cannot
#: silently share or override the first's vocabulary" — but a mapping with one
#: key has exactly one row, so a second action *could* not be added at all, and
#: the promise was kept by the type rather than by the rule.  The reward line is
#: the first real collision: both ``magic`` and ``reward`` declare a field
#: literally named ``operation`` over **disjoint** value sets
#: (``{"buy", "use"}`` and ``{"weekly", "daily"}``).  Keying by action makes
#: the disjointness a structural property that
#: :func:`parse_intent` can enforce, instead of one of the two sets quietly
#: winning.
#:
#: A value outside an action's set is ``malformed_request`` — a request-shape
#: error, decided here, in the one module that owns request shape.
INTENT_OPERATION_VALUES: Dict[str, FrozenSet[str]] = {
    "magic": frozenset({"buy", "use"}),
    "reward": frozenset({"weekly", "daily"}),
}

#: Actions whose addressing field may legally be **negative**.
#:
#: ``row`` is a placement index, so it cannot: a negative row is a malformed
#: request, and the intent layer says so.  ``collection_id`` is a committed
#: **id**, and the preserved server reaches it through the positional index
#: ``max(0, collection - 1)`` (``get_game_config.py:170-175``), which means the
#: integer zero and every negative id land on collection one.  Refusing a
#: negative collection id here as ``malformed_request`` would be the *wrong*
#: refusal for the *right* reason: it would report a request-shape error where
#: the domain has a named rule about an **aliased id**.  So the intent layer
#: accepts any integer and lets the slice refuse it as ``aliased_collection_id``
#: (design D3), which is the refusal that names the collision it resolves to.
#:
#: The asymmetry is deliberate and measured rather than assumed: a request
#: carrying ``row: -1`` must be refused, and refusing the *other* negative the
#: same way would hide the alias rule the slice exists to apply.
NON_NEGATIVE_ADDRESSING: FrozenSet[str] = frozenset({"row"})

#: Keys whose *name* says the client is trying to dictate an outcome.  Matched
#: case-folded, on whole underscore-separated segments, against the request's
#: own key.  Includes the seven stored resource names so a request naming
#: ``wood`` or ``gold`` is refused by name rather than merely flagged unknown,
#: and includes the legacy envelope's own field name so a v0-shaped request
#: aimed at v1 is recognised for what it is.
DELTA_KEYS: FrozenSet[str] = frozenset(
    {
        # the seven stored resources, plus experience
        "xp",
        "gold",
        "wood",
        "oil",
        "steel",
        "cash",
        "mana",
        # the legacy envelope's resource vector field, under its own name and
        # the v0 spelling
        "resources_changed",
        "resource_changed",
        "resources",
        "resource",
        "deltas",
        "delta",
        "vector",
        # experience / health / damage / result, as design D3 names them
        "experience",
        "exp",
        "hp",
        "health",
        "life",
        "damage",
        "result",
        "results",
        "outcome",
        # prices and amounts, which are the client-dictated form of a delta
        "amount",
        "amounts",
        "price",
        "prices",
        "cost",
        "costs",
        "reward",
        "rewards",
        "payout",
        "income",
        "gain",
        "gains",
    }
)

#: Words that may sit **beside** a declared delta word to qualify it, in either
#: order, and are themselves never a delta word on their own unless they also
#: appear in :data:`DELTA_KEYS` (several do: ``amount``, ``price``, ``cost``,
#: ``reward``, ``payout``, ``income``, ``vector``, ``delta``).  This set is what
#: ``wood_delta``, ``damage_amount``, ``gold_value`` and ``delta_wood`` match
#: on, and what ``instant_cost_report`` does not: there the head is
#: ``instant_cost``, which is not a declared word.
#:
#: ``change``/``changed`` are here for symmetry with the two declared
#: multi-part words; they are redundant for those two keys, which already match
#: whole, and are kept so ``resource_changed``-shaped spellings stay
#: recognisable if the vocabulary is ever re-spelled.
DELTA_MODIFIERS: FrozenSet[str] = frozenset(
    {
        "delta",
        "deltas",
        "change",
        "changed",
        "amount",
        "amounts",
        "value",
        "gain",
        "gains",
        "price",
        "prices",
        "cost",
        "costs",
        "reward",
        "rewards",
        "payout",
        "income",
        "vector",
    }
)


class Intent(BaseModel):
    """A validated player intent: what should happen, and about what.

    One addressing field and one operation, exactly one of each set.  They are
    ``Optional`` rather than split into separate models because
    :func:`parse_intent` constructs them from :data:`ADDRESSING_FIELDS` and
    :data:`INTENT_OPERATION_FIELDS` and the transport never builds an ``Intent``
    itself — so the "which one is set" question is answered at construction
    rather than at every use, and :meth:`addressed_path` reports the address that
    is.  A reward intent sets **no** addressing field, by
    :data:`NO_ADDRESSING_FIELD_ACTIONS`, and carries its client-sent cursor and
    grant inputs instead.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    player_id: str
    #: A placement row index.  Set for ``collect``; ``None`` otherwise.
    row: Optional[int] = None
    #: A committed collection id.  Set for ``collection``; ``None`` otherwise.
    #: May be **zero or negative**, on purpose — see
    #: :data:`NON_NEGATIVE_ADDRESSING`.
    collection_id: Optional[int] = None
    #: A committed magic id.  Set for ``magic``; ``None`` otherwise.  Also
    #: **not** in :data:`NON_NEGATIVE_ADDRESSING`, and for the opposite reason to
    #: ``collection_id``: the preserved ``buy_magic``/``use_magic`` branches
    #: never index the committed table, so there is no positional clamp for zero
    #: or a negative to alias and no ``aliased_magic_id`` refusal is warranted.
    #: The slice refuses them as ``unknown_magic_id``, which is the true
    #: statement — they name no committed row at all.
    magic_id: Optional[int] = None
    #: A committed **unit** id.  Set for ``combat``; ``None`` otherwise.  Also
    #: **not** in :data:`NON_NEGATIVE_ADDRESSING`, for the same reason as
    #: ``magic_id``: the preserved ``end_attack`` branch never indexes the
    #: committed table, so zero and every negative id name no committed unit row
    #: and there is no positional clamp for one to alias.  The slice refuses them
    #: as ``unaddressable_row``, which is the true statement -- they name no
    #: committed row at all.
    unit_id: Optional[int] = None
    #: Which of the action's declared operations the client asked for.  Set for
    #: every action in :data:`INTENT_OPERATION_FIELDS`; ``None`` otherwise.  A
    #: value outside the action's closed set never reaches here: it is refused
    #: as ``malformed_request`` in :func:`parse_intent`.
    operation: Optional[str] = None
    #: The preserved branch's destruction shape, carried **verbatim**, or
    #: ``None``.
    #:
    #: ``Any`` rather than a declared type on purpose: this value is never
    #: interpreted, counted, bounded, or compared, and typing it as a list would
    #: be an invitation to read it as one.  The domain reports it beside the code
    #: that refused it and derives nothing from it.
    destruction_request: Optional[Any] = None
    #: A reward cursor the client tried to send, carried **verbatim**, or
    #: ``None``.
    #:
    #: ``Any`` for the same reason :attr:`destruction_request` is: the value is
    #: never read, incremented, clamped, or compared here.  It exists so the
    #: domain can refuse the request **by name** with the offending spelling
    #: beside the code, rather than the request layer reporting a key that
    #: happens to be one of several.
    cursor_request: Optional[Any] = None
    #: Client-sent reward-grant inputs, keyed by **channel** (see
    #: :data:`REWARD_GRANT_KEYS`), valued verbatim.  Empty — not ``None`` — when
    #: the request carried none, so "no grant" is one testable value rather than
    #: two spellings of absence.  Keyed by channel rather than by the literal
    #: spelling because the domain's rule is about *what was granted*, and
    #: ``x``/``y`` must reach it as the one cell they are.
    grant_request: Dict[str, Any] = Field(default_factory=dict)

    def addressed_path(self) -> str:
        """A JSON-pointer-ish description of what this intent addresses.

        Used in refusal detail so a client can see exactly which row, ledger
        key, or committed magic row was addressed.  It reports the address, never
        a balance.

        ``combat`` resolves to ``/maps/0/items``, the **container**, and not to a
        key inside it: a combat identity is a committed **item id**, and the
        rows it could name are every key whose slot 0 equals it -- which may be
        none, one, or several, and which no JSON pointer can express.  Naming the
        container is the honest address; the domain reports the actual matching
        keys beside it.

        ``reward`` resolves to ``/privateState``, the **container** and not a
        key inside it, for the same reason and a second one: the two cursors
        live under two different keys of that object, and which one is addressed
        is the *operation's* answer, not the request's.  A pointer to a key here
        would assert a resolution this layer has not made; the domain reports the
        real :func:`server_v1_reward.reward_cursor_path` beside this one.
        """
        if self.collection_id is not None:
            return "/privateState/collections"
        if self.magic_id is not None:
            return "/privateState/magics/%d" % self.magic_id
        if self.unit_id is not None:
            return "/maps/0/items"
        if self.action in NO_ADDRESSING_FIELD_ACTIONS:
            return "/privateState"
        return "/maps/0/items/%d" % self.row


#: What parsing returns: either an intent or a refusal.  Two arms, no ``None``,
#: the same shape as :data:`server_v1_outcomes.Outcome`.  The transport tests
#: the arm with ``isinstance``; nothing raises here.
#:
#: **Why returned rather than raised.**  The first version of this module raised
#: its refusals, and the test suite failed with 89 errors of the form
#: ``TypeError: assertRaises() arg 1 must be an exception type`` -- because
#: ``Refusal`` is a frozen Pydantic model, not an exception, so every ``raise``
#: in this module was itself a ``TypeError: exceptions must derive from
#: BaseException``.  The smoke run that reported delta requests as "refused at
#: the intent layer" had swallowed that ``TypeError`` and was therefore
#: reporting a defect as a pass.  Returning is also what the change's own design
#: says: "a typed refusal channel **returned** by the domain and translated to
#: HTTP by the transport".  Control flow by exception would have made the
#: transport's translation step optional rather than total.
IntentOutcome = Union[Intent, Refusal]


def _segments(key: str) -> Tuple[str, ...]:
    """A request key split into case-folded underscore segments.

    ``"Wood_Delta"`` -> ``("wood", "delta")``.  Splitting on underscore and
    folding case means a key is judged on its **words**, which is what makes
    ``wood_delta`` a delta attempt and ``wooden_fence`` not one.
    """
    return tuple(part for part in key.strip().casefold().split("_") if part)


def parse_intent(action: str, body: Any) -> IntentOutcome:
    """Turn a request body into an :class:`Intent`, or return a refusal.

    The result is an :data:`IntentOutcome` in both directions: this function
    **returns** its refusals rather than raising them, for the reason recorded
    on :data:`IntentOutcome`.  A caller that forgets to test the arm gets a
    :class:`Refusal` object where it expected an intent, which fails on the
    next attribute access -- loud, rather than a silently empty intent.

    The checks run in a fixed order and every one of them refuses rather than
    repairs, so the *first* reason a request fails is the reason reported:

    1. the body is a JSON object (``malformed_request``);
    2. no key is delta-shaped (``client_supplied_delta``);
    3. the preserved branch's own destruction shape is recognised and carried
       rather than answered as an unknown key -- **not a refusal here**, see
       :data:`DESTRUCTION_KEYS`;
    3b. the reward line's two channels are recognised and carried for the same
       reason: a client-sent cursor (:data:`REWARD_CURSOR_KEYS`) and the four
       client-sent grant shapes (:data:`REWARD_GRANT_KEYS`).  **The cursor is
       recognised first**, which is a recorded difference from v0's order;
    4. no key is outside the action's schema (``unknown_request_field``);
    5. the required keys are present and correctly typed
       (``malformed_request``);
    6. the action's declared ``operation``, if it declares one, names one of its
       declared values (``malformed_request``).

    Step 3 decides nothing.  It recognises a key, excludes it from the closed-key
    set at step 4, and carries its value into :attr:`Intent.destruction_request`;
    the domain then refuses the request **by name**.  A layer that only reads key
    names has no rule about what a transaction would have destroyed, so naming
    ``client_dictated_destruction`` here would be this module deciding a
    question it cannot see.  Step 3b is the same rule applied to the reward
    channels, and carries the **channel name** rather than the request's literal
    spelling, so ``x`` and ``y`` reach the domain as the one cell they are and
    the domain answers about the cell rather than about a coordinate.

    Order matters for a client: a request carrying both a delta and an unknown
    key is reported as a delta attempt, because that is the security-relevant
    statement about it, and a request carrying an unknown key *instead of* the
    required one is reported as unknown-field rather than as missing, so the
    client is not told to supply a field it already sent.

    No value from ``body`` ever reaches a balance.  The only values that leave
    this function are the action name, the player id, the one addressing value
    the action declares (**or none**, for an action in
    :data:`NO_ADDRESSING_FIELD_ACTIONS`), its declared operation, and the
    recognised destruction, cursor, and grant shapes carried verbatim.
    """
    if action not in INTENT_SCHEMAS:
        # Not reachable through the delivered route; a fail-closed answer rather
        # than a KeyError, because an unknown action must never be parsed with
        # some other action's schema.
        return _refuse(
            RefusalCode.UNKNOWN_REQUEST_FIELD,
            "no intent schema is declared for action %r" % action,
            {"action": action},
        )
    allowed = INTENT_SCHEMAS[action]

    if not isinstance(body, Mapping):
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "the request body must be a JSON object",
            {"received": type(body).__name__},
        )

    # (2) delta check, before the unknown-key check, on every key present.
    delta_keys = sorted(key for key in body if _is_delta_key(str(key)))
    if delta_keys:
        return _refuse(
            RefusalCode.CLIENT_SUPPLIED_DELTA,
            "a v1 request carries intent only; the field %r dictates an outcome "
            "and is refused rather than clamped, coerced, or ignored"
            % delta_keys[0],
            {"delta_fields": delta_keys, "refused_field": delta_keys[0]},
        )

    # (2b) the preserved branch's own destruction shape, **recognised** here and
    # **decided** by the domain.
    #
    # ``attacker_units`` is not a delta *resource* but it does dictate an
    # outcome, so the closed-key check below must not answer it as an arbitrary
    # unknown field; the domain owns the decision and names the refusal, because a
    # decision about what a transaction would have destroyed belongs to the domain
    # and not to a layer that only reads key names (design D4, D5).
    #
    # What happens here is **recognition and carriage**: the key is recognised,
    # excluded from the unknown-key set, and its value carried into
    # :attr:`Intent.destruction_request` verbatim.  Nothing in this module
    # interprets, counts, bounds, or compares it, and this module names no
    # domain refusal code.
    destruction_keys = DESTRUCTION_KEYS.get(action, frozenset())
    carried = sorted(str(key) for key in body if str(key) in destruction_keys)

    # (3b) the reward line's two channels, recognised and carried exactly as the
    # destruction shape above is -- and **decided by the domain**, for the same
    # reason: whether a request's item id would have been granted, or whether its
    # cursor would have moved, is a rule about the transaction, and this module
    # has no transaction.
    #
    # The cursor is resolved **before** the grants.  v0's order is the reverse
    # for this pair (``rewards_envelope.py:830-838``: item, item_index, cell,
    # player, next_id), so this is a recorded difference and not an accident: the
    # cursor is the one input the reward line exists to make impossible, so a
    # request naming both is answered about that first.
    cursor_keys = REWARD_CURSOR_KEYS.get(action, frozenset())
    carried_cursor = sorted(str(key) for key in body if str(key) in cursor_keys)

    grant_table = REWARD_GRANT_KEYS.get(action, {})
    #: Keyed by **channel**, so two spellings of one channel (``x`` and ``y``)
    #: collapse to one entry -- last write wins deterministically because the
    #: loop is over ``sorted(body)`` -- and the domain answers about the cell
    #: once.  The literal spelling is not carried: the domain reports the
    #: channel, which is the thing it can act on, and this layer has no reason
    #: to prefer one coordinate name over the other.
    carried_grants: Dict[str, Any] = {}
    for key in sorted(str(key) for key in body):
        channel = grant_table.get(key)
        if channel is not None:
            carried_grants[channel] = body[key]

    # (3c) everything this action neither defines nor recognises.  The
    # recognised shapes are excluded **here** and only here: including them
    # would answer a preserved-dialect request as an arbitrary unknown field
    # and the domain's named refusal would be unreachable.
    recognised = allowed | destruction_keys | cursor_keys | frozenset(grant_table)
    unknown = sorted(str(key) for key in body if str(key) not in recognised)
    if unknown:
        return _refuse(
            RefusalCode.UNKNOWN_REQUEST_FIELD,
            "the request carried the field %r, which the %r intent schema does "
            "not define" % (unknown[0], action),
            {"unknown_fields": unknown, "allowed_fields": sorted(allowed)},
        )

    # (4) required keys, typed.
    player_id = body.get("player_id")
    if not isinstance(player_id, str) or player_id == "":
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "player_id must be a non-empty string",
            {"received": type(player_id).__name__},
        )

    # (5b) the addressing value, for an action that declares one.  An action in
    # :data:`NO_ADDRESSING_FIELD_ACTIONS` has no addressing step at all, so
    # ``target`` stays ``None`` and every addressing field below stays ``None``
    # -- which is the truthful state, not a default: the request named no
    # address, and the domain reports the container.
    addressing: Optional[str] = None
    target: Optional[int] = None
    if action not in NO_ADDRESSING_FIELD_ACTIONS:
        addressing = ADDRESSING_FIELDS[action]
        target = body.get(addressing)
        # ``bool`` is an ``int`` in Python, so ``True`` would address row 1.
        if isinstance(target, bool) or not isinstance(target, int):
            return _refuse(
                RefusalCode.MALFORMED_REQUEST,
                "%s must be an integer" % addressing,
                {"addressing_field": addressing, "received": type(target).__name__},
            )
        if addressing in NON_NEGATIVE_ADDRESSING and target < 0:
            return _refuse(
                RefusalCode.MALFORMED_REQUEST,
                "%s must be a non-negative integer" % addressing,
                {"addressing_field": addressing, "received": target},
            )

    # (5c) the action's declared operation, from its closed value set.
    #
    # Declared as data (:data:`INTENT_OPERATION_VALUES`) rather than as a branch
    # here or in the transport, so a fourth operation can only be added by
    # editing the table -- and the table is what a test reads to assert the set
    # is exactly what the delivered domain accepts.  A request naming no
    # operation field, a non-string operation, and an undeclared operation value
    # are one refusal with three different ``received`` spellings rather than
    # three refusals, because they are one fact: the request does not name an
    # operation this action declares.
    #
    # The lookup is keyed by **action**, not by the field's name: ``magic`` and
    # ``reward`` both declare a field literally named ``operation`` over
    # disjoint value sets, and keying by field would have let one set answer for
    # the other.
    operation_field = INTENT_OPERATION_FIELDS.get(action)
    operation: Optional[str] = None
    if operation_field is not None:
        operation_values = INTENT_OPERATION_VALUES[action]
        raw_operation = body.get(operation_field)
        if not isinstance(raw_operation, str) or raw_operation not in operation_values:
            return _refuse(
                RefusalCode.MALFORMED_REQUEST,
                "%s must be one of %s" % (operation_field, sorted(operation_values)),
                {
                    "operation_field": operation_field,
                    "allowed_operations": sorted(operation_values),
                    "received": raw_operation
                    if isinstance(raw_operation, str)
                    else type(raw_operation).__name__,
                },
            )
        operation = raw_operation

    return Intent(
        action=action,
        player_id=player_id,
        # The field the action declares as its own is the one that is set; the
        # other stays ``None``.  Two conditional expressions rather than an
        # ``**{addressing: target}`` unpack, because that form cannot be
        # type-checked and would let a mis-declared table produce an intent
        # with neither field set.
        row=target if addressing == "row" else None,
        collection_id=target if addressing == "collection_id" else None,
        magic_id=target if addressing == "magic_id" else None,
        unit_id=target if addressing == "unit_id" else None,
        operation=operation,
        # The recognised destruction field's value, verbatim and unexamined.
        # ``carried`` is sorted, so a request naming two recognised shapes would
        # carry the first by name -- which is why the table lists exactly one
        # shape per action, and why the domain reports the carried key beside
        # the value rather than reporting a value alone.
        destruction_request=body[carried[0]] if carried else None,
        cursor_request=body[carried_cursor[0]] if carried_cursor else None,
        grant_request=carried_grants,
    )


def intent_from_json(action: str, raw: bytes) -> IntentOutcome:
    """Decode a raw request body and parse it, or return a refusal.

    JSON decoding lives here rather than in the route for two reasons.  The
    first is that a body which is not JSON is a **structural input error**, and
    the module that owns structural input errors is the one that should name it
    — a route that reached into the refusal vocabulary to say so would be a
    transport naming a reason, which is exactly what design D2 forbids.
    ``tests/test_boundary_invariant.py`` asserts this file names no refusal code
    outside its own import, so adding one here would be a deliberate exception.

    The second is that the decode is part of *intent parsing*: the body's bytes
    are the client's claim, and turning them into an intent is parsing, not
    serving.  The route reads a request object and hands over its bytes.

    A decode failure of **any** kind is one refusal, not a crash: ``json`` raises
    ``JSONDecodeError`` on bad syntax and ``UnicodeDecodeError`` on bytes that
    are not text, and a client sending either gets ``malformed_request``.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "the request body is not UTF-8 text",
            {"received": "undecodable-bytes", "detail": str(error)[:80]},
        )
    try:
        body = json.loads(text)
    except ValueError as error:
        return _refuse(
            RefusalCode.MALFORMED_REQUEST,
            "the request body is not valid JSON",
            {"received": "invalid-json", "detail": str(error)[:80]},
        )
    return parse_intent(action, body)


def _is_delta_key(key: str) -> bool:
    """Whether a request key names a client-dictated outcome.

    A key is a delta key when it **is** a declared delta word, or when one
    leading or trailing part is a declared modifier and what remains **is** a
    declared delta word::

        gold                      -> the word itself
        wood_delta                -> word + modifier
        delta_wood                -> modifier + word
        gold_value                -> word + modifier
        damage_amount             -> word + modifier
        resources_changed         -> a declared multi-part word itself
        amount_resource_changed   -> modifier + a multi-part word

    Both halves of that rule are checked against
    :data:`DELTA_KEYS` and :data:`DELTA_MODIFIERS`, so the recogniser cannot
    drift from the vocabulary.

    **Corrected while writing this module's tests.**  The first version matched
    when *any* segment was a declared word, with a second loop composing
    adjacent pairs.  That was wrong twice over, and the docstring claimed
    otherwise:

    * it accused ``instant_cost_report`` (``cost``) and ``my_gold_pick``
      (``gold``) of dictating an outcome — precisely the two keys the original
      docstring named as the reason the bare-substring design had been rejected,
      so the *documented* rationale was not the *implemented* rule;
    * the composition loop was **dead code**: every multi-part entry in
      :data:`DELTA_KEYS` (``resources_changed``, ``resource_changed``) already
      matched through its own first segment (``resources``, ``resource``), so
      the loop could never be the deciding branch for any key.

    The whole-key rule above replaces both loops.  It is narrower, which
    means ``my_gold`` and ``gold_rich``-shaped keys that merely *contain* a
    word now report ``unknown_request_field`` instead — recorded as a narrowing
    of the diagnostic, never of the refusal, since every such request is refused
    either way (the schema is closed).  A bare substring search over the whole
    key remains rejected: ``wooden_fence`` would be accused.

    The first cut of the replacement compared only the last two parts, so it
    failed on a modifier beside a **multi-part** declared word:
    ``amount_resource_changed`` splits as head ``amount_resource`` (not a
    declared word) and tail ``changed`` (a modifier), and so was unknown-field.
    That was found by a test asserting the rule over the **whole** vocabulary
    rather than a chosen example list, which is the argument for keeping that
    test over-total.  The rule now removes one leading or trailing modifier
    part and compares the remainder whole.
    """
    normalised = "_".join(_segments(key))
    if not normalised:
        return False
    if normalised in DELTA_KEYS:
        return True
    parts = normalised.split("_")
    if len(parts) < 2:
        return False
    if parts[-1] in DELTA_MODIFIERS and "_".join(parts[:-1]) in DELTA_KEYS:
        return True
    return parts[0] in DELTA_MODIFIERS and "_".join(parts[1:]) in DELTA_KEYS


def _refuse(code: RefusalCode, message: str, detail: Dict[str, Any]) -> Refusal:
    return Refusal(code=code, message=message, detail=dict(detail))


__all__ = [
    "ADDRESSING_FIELDS",
    "DELTA_KEYS",
    "DELTA_MODIFIERS",
    "DESTRUCTION_KEYS",
    "INTENT_OPERATION_FIELDS",
    "INTENT_OPERATION_VALUES",
    "INTENT_SCHEMAS",
    "NO_ADDRESSING_FIELD_ACTIONS",
    "NO_OPERATION_FIELD_ACTIONS",
    "NON_NEGATIVE_ADDRESSING",
    "REWARD_CURSOR_KEYS",
    "REWARD_GRANT_CHANNELS",
    "REWARD_GRANT_KEYS",
    "Intent",
    "IntentOutcome",
    "intent_from_json",
    "parse_intent",
]
