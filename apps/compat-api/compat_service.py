#!/usr/bin/env python3
"""Compatibility API v0 service (design D3, spec: bootstrap service).

Surface (loopback only, port :5056):

``GET /v0/session``
    ``{protocol, ok, game_version, server_time, saves:[{id,name,xp,level}]}``
    where ``saves`` is the legacy ``all_saves_info()`` result renamed into the
    documented envelope, mirroring the legacy login save list.

``POST /v0/bootstrap`` with JSON ``{"user_id": "<save id>"}``
    ``{protocol, ok, game_version, server_time, saves, config, player_info}``
    where ``config`` is the legacy ``get_game_config()`` payload and
    ``player_info`` is the legacy ``get_player_info()`` payload.

``POST /v0/place`` with JSON ``{"user_id", "item_id", "x", "y", "orientation"?}``
    ``{protocol, ok, game_version, server_time, result, placement, resources}``
    — an intent only. The legacy batch envelope (price vector, next free
    slot, documented placeholders) is derived internally (design D4 of the
    ``building-placement`` change), the unchanged legacy ``command()``
    dispatcher executes it in-process, and the answer carries the legacy
    ``result`` plus the authoritative superset: the persisted eight-field
    ``placement`` entry and the current ``resources`` (design D7). This is
    the one state-mutating surface; the contract accepts no client-supplied
    resource deltas — extra keys are ignored.

``POST /v0/purchase`` with JSON ``{"user_id", "item_id"}``
    ``{protocol, ok, game_version, server_time, result, store, resources}``
    — also an intent only, and the second state-mutating surface. The legacy
    batch envelope is derived internally from the item's config ``costs``
    (the cash-only price on the legacy 8-slot resource vector, one
    ``buy_stored_item_cash`` command whose single argument is the item id,
    and the documented placeholders — design D2 of the ``building-purchase``
    change), the unchanged legacy ``command()`` dispatcher executes it
    in-process, and the answer carries the legacy ``result`` plus the
    authoritative superset: the full post-execution ``store`` mapping and the
    current ``resources`` (design D4). The contract accepts no client-supplied
    price, quantity, or resource deltas — extra keys are ignored.

``POST /v0/move`` with JSON ``{"user_id", "item_index", "x", "y"}``
    ``{protocol, ok, game_version, server_time, result, placement, resources}``
    — an intent only, and the third state-mutating surface. The legacy batch
    envelope is derived internally (one ``move`` command whose five arguments
    are the legacy map index, the target coordinates, and the two documented
    placeholders the branch discards, with the **neutral** derived resource
    vector — design D2/D6 of the ``building-move`` change), the unchanged
    legacy ``command()`` dispatcher executes it in-process, and the answer
    carries the legacy ``result`` plus the authoritative superset: the
    persisted eight-field ``placement`` entry re-read from the save after
    execution and the current ``resources`` (design D4). The contract accepts
    no client-supplied price, resource deltas, ``frame``, or ``string`` — the
    extra keys are ignored. ``item_index`` is the legacy map key as an
    integer and must resolve to a row in the corpus save *before* the
    dispatcher runs, because legacy's own missing-item path is a silent no-op
    that would otherwise be reported as a success.

``POST /v0/sell`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, resources}``
    — an intent only, and the fourth state-mutating surface. The legacy batch
    envelope is derived internally (one ``sell`` command whose two arguments
    are the legacy map index and the **derived** reason the branch treats as a
    log label, with the **neutral** derived resource vector — design D2/D3 of
    the ``building-sell`` change), the unchanged legacy ``command()``
    dispatcher executes it in-process, and the answer carries the legacy
    ``result`` plus the authoritative superset: the eight-field row **as it
    was read before execution** (``removed``), the current ``resources``, and
    a post-execution re-read proving the legacy key is gone from the
    persisted save (design D5). The contract accepts no client-supplied
    reason, refund, price, or resource deltas — the extra keys are ignored,
    so no client can claim the combat ``KILL`` reason and reach
    ``push_dead_unit``. Because the committed configuration records no
    building-sale refund rule, the derived vector is neutral and **this
    service claims no refund at all**. ``item_index`` must resolve to a row
    in the corpus save *before* the dispatcher runs, for the same
    missing-item reason the move line documents, and a row that survives
    execution fails closed with ``internal_error`` instead of claiming a
    removal that never happened.

``POST /v0/store`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, store,
    resources}`` — an intent only, and the fifth state-mutating surface. The
    legacy batch envelope is derived internally (one ``store_item`` command
    whose single argument is the legacy map index, with the **neutral**
    derived resource vector — design D2/D6 of the ``building-store`` change),
    the unchanged legacy ``command()`` dispatcher executes it in-process, and
    the answer carries the legacy ``result`` plus the two-sided authoritative
    superset: the eight-field row **as it was read before execution**
    (``removed``), the **full post-execution storage mapping** (``store``), and
    the current ``resources`` (design D4). The contract accepts no
    client-supplied quantity, price, or resource deltas — the extra keys are
    ignored. Because the committed configuration records no price for
    storing and legacy has no capacity check at all, the derived vector is
    neutral: **this service claims no storing cost and no capacity rule**, and
    ``add_store_item``'s default quantity of exactly ``1`` is the only
    quantity the branch ever uses. The legacy branch deliberately does not
    write ``privateState.boughtUnits`` (unlike ``buy`` /
    ``place_stored_item`` / ``buy_stored_item_cash``), and this endpoint
    reproduces that exactly. ``item_index`` must resolve to a row in the
    corpus save *before* the dispatcher runs, because legacy's missing-item
    path is a silent early return that still persists the batch; and the
    endpoint additionally proves **both** halves of the move after execution
    (the popped key is absent from the map **and** the item's id is present in
    the storage), failing closed with ``internal_error`` if either is untrue.

``POST /v0/upgrade`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, upgraded,
    resources}`` — an intent only, and the sixth state-mutating surface.  An
    upgrade is **one legacy batch with two commands in a forced order**: a
    ``sell`` carrying the committed upgrade reason ``"UPGR"``
    (``constants.py:970``) followed by a ``buy`` of the target tier that
    reuses the row's own map key, cell, orientation, and player team
    (``command.py:42-58``: ``buy`` takes its key and cell from the client,
    which is exactly how the pair replaces the row in place).  The legacy batch
    envelope is derived internally — the target tier from the committed
    configuration's ``upgrades_to``, the reason from the committed legacy
    constant, the cell / orientation / player from the row being replaced, and
    the **neutral** derived resource vector on **both** commands (design
    D2/D4 of the ``building-upgrade`` change) — the unchanged legacy
    ``command()`` dispatcher executes it in-process, and the answer carries
    the legacy ``result`` plus the two-sided authoritative superset: the
    eight-field row **as it was read before execution** (``removed``), the
    eight-field row **re-read from the persisted save after execution**
    (``upgraded``), and the current ``resources`` (design D5).  The contract
    accepts no client-supplied target tier, reason, coordinates, orientation,
    player, quantity, price, or resource deltas — the extra keys are ignored.

    Because the committed configuration records no upgrade price anywhere, the
    derived vector is neutral and **this service claims no upgrade cost of any
    kind** — not the target tier's ``costs``, not the difference between
    tiers, and nothing about ``premium_upgrade_costs``.  ``item_index`` must
    resolve to a row in the corpus save *before* the dispatcher runs, because
    legacy's missing-item path is a silent early return that still persists
    the save; a placement whose item has no resolvable next tier answers
    ``no_upgrade_path`` (400) before the dispatcher runs, so a building that
    cannot be upgraded is never reduced to a bare sale; and after execution
    the endpoint proves **all three** facts of the replacement — the key still
    exists, its item id equals the derived target tier, and its cell equals the
    pre-execution cell — failing closed with ``internal_error`` otherwise.
    That proof exists because legacy answers ``{"result":"success"}`` for the
    *reverse* command order while leaving the key absent, so a success status
    is not evidence of an upgrade.  The legacy client's own upgrade rules — the
    level gate, the daily-upgrade limit, and the space check — are known to
    exist and are deliberately **not** enforced here: none is enforced by the
    legacy server and none can be reproduced from the repository.

``POST /v0/construction`` with JSON ``{"user_id", "item_index", "action"}``
    ``{protocol, ok, game_version, server_time, result, previous, row, action,
    resources}`` — an intent only, and the seventh state-mutating surface.  One
    call carries **exactly one** of the three legacy construction commands; the
    action names an *outcome* and the service chooses the command and derives
    every argument (design D2 of the ``building-construction`` change):
    ``"start"`` → ``activate`` with a duration derived from the addressed
    placement's item's committed ``build_time``, ``"click"`` → ``add_click``,
    ``"finish"`` → ``activate_item_click``.  The action vocabulary is **closed**;
    anything else fails closed with ``invalid_action`` before the dispatcher
    runs.  The unchanged legacy ``command()`` dispatcher executes the batch
    in-process, and the answer carries the legacy ``result`` plus the
    authoritative superset: the eight-field row **as it was read before
    execution** (``previous``), the eight-field row **re-read from the
    persisted save after execution** (``row``), the **resolved** ``action``,
    and the current ``resources`` (design D5).  Unlike every earlier line this
    contract carries **no derived placeholder argument at all**, and it accepts
    no client-supplied duration, price, quantity, or resource deltas — the
    extra keys (``duration``, ``price``, ``resources_changed``, ``count``, …)
    are ignored, so no client value can influence the countdown.

    A placement whose item has **no resolvable positive committed build time**
    answers ``no_build_time`` (400) before the dispatcher runs, so an
    unbuildable row is never handed a coerced duration.  That refusal is
    load-bearing: legacy's ``activate`` with a non-positive duration does not
    cancel a build, it **clears the row's whole attribute bag**, destroying
    the click counter and any friend-assistance entries
    (``command.py:425-427``), so this contract only ever sends a positive
    derived duration and exposes **no cancel action** (design D6).

    Because the committed configuration records no price for building, the
    derived vector is neutral and **this service claims no building cost at
    all**; the loaded ``BUILD_SPEEDUP_PRICING`` / ``BUILD_SPEEDUP_MIN_TIME``
    globals price a *speedup*, which is a separate mechanism deliberately out
    of scope (design D4).  No
    branch compares the click counter with the item's ``clicks_to_build``, so
    the completion threshold and the remaining time (``cp - (now - item[3])``)
    are **client-side derivations with no server enforcement**; whether a build
    may start on a row that already carries construction state is the client's
    call, and authoritative validation belongs to Server v1 (M13).

    After execution the endpoint proves the per-action post-condition
    (design D3) and fails closed with ``internal_error`` on any other outcome:
    the row still exists and is a list (a construction action must never
    destroy a row), and then ``start`` → ``attr["cp"]`` equals the derived
    duration, ``click`` → ``attr["nc"]`` is present and at least ``1``,
    ``finish`` → ``attr["nc"]`` is absent.

``POST /v0/collect`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, previous, row, payout,
    tier, reference_time, resources}`` — an intent only, and the eighth
    state-mutating surface.  This is the **first** line in this family whose
    derived resource vector is deliberately *not* neutral, because for the
    first time the committed configuration describes the action's effect
    (design D1-D6 of the ``building-collect`` change).  The unchanged legacy
    ``command()`` dispatcher executes one ``collect`` command in-process; that
    branch writes **only** ``item[3] = time_now`` (``command.py:136-147``) and
    the income is the client-sent 8-slot vector applied verbatim per resource
    as ``max(current + delta, 0)`` by ``engine.apply_resources`` before the
    branch runs (``engine.py:251-271``), so the payout this service derives is
    **the vector it sends**.  The answer carries the legacy ``result`` plus the
    authoritative superset: the eight-field row **as it was read before
    execution** (``previous``), the eight-field row **re-read from the persisted
    save after execution** (``row``), the derived ``payout`` and the ladder
    ``tier`` it came from, the ``reference_time`` the elapsed time was computed
    against, and the current ``resources`` (design D8).

    Nothing but the save id and the index enters the contract: no amount,
    resource, tier, time, price, or resource delta is accepted from a client —
    the extra keys (``amount``, ``resource``, ``tier``, ``time``, ``price``,
    ``resources_changed``, ``collect``, ``collect_type``, ``collect_xp``,
    ``max_collects``, …) are ignored.  The payout is therefore derived entirely
    from committed content and the addressed row's own state: the amount from
    the item's committed ``collect``, the resource from its committed
    ``collect_type``, the experience from its committed ``collect_xp``, each
    scaled by the committed ladder rung (``COLLECT_MINUTES`` /
    ``COLLECT_MULTIPLIER``) the row's elapsed time has actually reached,
    **clamped at the top rung**.  The vector's unread ``unknown`` slot and its
    never-produced ``mana`` slot are always zero.

    Five content/guard conflicts fail closed with **409** and no mutation, each
    a **derived-provisional** decision that refuses rather than guesses:
    ``capped_collection`` for an item whose committed ``max_collects`` is
    non-zero (only ``0`` is implemented, because nothing says what a non-zero
    cap limits), ``unknown_collect_type`` for a ``collect_type`` outside the
    committed five ``g/w/o/s/c`` (the committed census is 731/23/11/11/2 and no
    item records a mana type), ``no_income`` for an item whose committed
    ``collect`` is ``0`` (727 of 778 stored items, including 39 of the corpus's
    40 placed rows), ``too_early`` when no committed rung is reached
    (``COLLECT_MINUTES[0] = 5``; a sub-rung amount would be invented), and
    ``construction_in_progress`` for a row whose attribute bag carries a
    countdown ``cp`` or a click counter ``nc``.

    That last refusal is **required, not defensive** (design D5): ``item[3]``
    is *both* a construction start instant (written by ``activate``) and a
    last-collection instant (written by ``collect``), and an executed-legacy
    probe showed ``activate(11, 3600)`` followed by ``collect(11)`` leaving
    ``[22, 58, 48, <collect instant>, 0, [], {"cp": 3600}, 1]`` — the build's
    start instant overwritten while the countdown survived, silently restarting
    an active build's timer, with the legacy server answering
    ``{"result":"success"}``.  The delivered construction line reads that same
    field as a build's start instant, so this endpoint refuses the collection
    **before** the dispatcher runs and the corpus is left byte-identical.

    After execution the endpoint proves the post-state in **two** ways
    (design D8) and fails closed with ``internal_error`` on any other outcome:
    the row still exists, is an eight-field list, and its recorded collection
    instant moved **strictly forward**; **and** every stored resource changed by
    **exactly** the derived delta.  The second check is what makes a reduced or
    diverging payout *reported* rather than trusted — legacy's ``max(…, 0)``
    clamp would otherwise let a short credit look like a success.  The
    pre-execution ``resources`` are read **before** dispatch so the comparison
    is against the state the batch actually started from.

``POST /v0/expand`` with JSON ``{"user_id", "expansion_id"}``
    ``{protocol, ok, game_version, server_time, result, expansions_before,
    expansions_after, debit, price, resources}`` — an intent only, and the
    ninth state-mutating surface.  The unchanged legacy ``command()``
    dispatcher executes one ``expand`` command in-process; that branch writes
    **only** ``map["expansions"] += [int(expansion)]`` (``command.py:211-216``)
    and the price is the client-sent 8-slot vector applied verbatim per
    resource as ``max(current + delta, 0)`` by ``engine.apply_resources``
    before the branch runs (``engine.py:251-271``), so the **debit** this
    service derives is **the vector it sends**.  The answer carries the legacy
    ``result`` plus the authoritative superset: the owned-expansions list
    **before** execution, the same list **after** execution, the derived
    ``debit``, the committed schedule ``price`` row it came from, and the
    current ``resources`` (design D5).

    Nothing but the save id and the expansion id enters the contract: no
    amount, resource, price, time, requirement flag, or resource delta is
    accepted from a client — the extra keys (``coins``, ``cash``, ``price``,
    ``amount``, ``neighbors``, ``inventory_qte``, ``time``,
    ``resources_changed``, …) are ignored.  The debit is therefore derived
    entirely from committed content: the cost from the id's own row in the
    98-entry positional ``expansion_prices`` schedule (design D1, derived),
    the schedule's gold-named ``coins`` into the server's ``gold`` resource and
    its ``cash`` into the server's ``cash`` resource (design D2, **established
    by committed client asset names** — ``assets/images/en/expansion_gold.jpg``
    and ``expansion_cash.jpg`` are the popup's two price components), as a
    **debit**, so a zero-cost row derives the all-zero vector and is legal.
    Six of the eight slots are always zero: the unread ``unknown`` slot 0 and
    every slot no expansion price names (experience, wood, oil, steel, mana).

    Three content/guard conflicts fail closed with **409** and no mutation,
    each answering **before** the dispatcher runs: ``unknown_expansion_id``
    (404) for an id outside the committed schedule, ``already_expanded`` (409)
    for an id the player's own list already contains, and
    ``expansion_requirements_unmet`` (409) for a row recording a positive
    ``neighbors`` or ``inventory_qte``.  A fourth, ``insufficient_resources``
    (409), refuses a balance that does not cover the derived debit.

    The first two guards are **required, not defensive** (design D1): the
    legacy server does no range check and no dedup at all, and an
    executed-legacy probe had ``expand(999)``, a duplicate ``expand(35)``, and
    ``expand(-1)`` all answer ``{"result":"success"}`` — so a client that
    ignored the client's own rules could buy an expansion no committed row
    prices and could append a repeat, corrupting the only ledger this line
    maintains.

    The requirements refusal is **refusal, not omission** (design D3): the
    server ignores both fields and nothing the delivered stack can read
    evaluates either — no neighbour count and no inventory quantity is exposed
    by the bootstrap, the client's ``GameApi``, or the corpus.  The consequence
    is recorded rather than worked around: **every id the corpus owns
    (``35, 36, 45, 46``) records ``neighbors 15`` and ``inventory_qte 30``, so
    none of them could have been bought under this rule, and 94 of the 98
    committed rows record a positive requirement** — the only purchasable
    entries in the whole schedule are the free indexes ``0..3``.

    The affordability refusal is the **rejected alternative to reproducing the
    clamp** (design D6).  An executed-legacy probe showed the clamp is
    reachable for the first time in this family: a client-sent ``-2500`` gold
    debit against a ``2000`` balance landed on ``0``, not ``-500``.  Because the
    debit here is **server-derived**, the endpoint can know whether the balance
    covers it, and silently under-charging would make the post-state proof
    ambiguous (a balance that moved by less than the derived debit is
    indistinguishable from a bug), so the refusal is the safe direction.

    After execution the endpoint proves the post-state in **two** ways
    (design D5) and fails closed with ``internal_error`` on any other outcome:
    the owned list grew by **exactly one** entry, equal to the sent id,
    **at the end**, with every existing entry unchanged and in order and never
    reordered or deduplicated; **and every** stored resource changed by
    **exactly** the derived debit.  The second half is what makes a wrong
    server-derived price *reported* rather than trusted — this is the first
    endpoint whose value-level proof exists specifically to catch a derivation
    that would mint or burn the wrong amount — and the pre-execution
    ``resources`` are read **before** dispatch so the comparison is against
    the state the batch actually started from.

    **No land, grid, or cell effect is claimed or implemented** (design D4):
    nothing here reads a terrain, a grid extent, a cell, a footprint, or a
    placement bound, and no claim is made that a bought expansion makes any
    area of the town buildable.  The committed evidence establishes the
    *vocabulary* — the SWF symbols ``PopupExpandMC`` and
    ``btnBuyExpandTileMC`` plus ``assets/images/en/expansion.png`` show the
    client's model is a purchasable **tile** bought through a popup, and the
    two committed price-component images show it is priced in gold and cash —
    but the committed SWF inspection is symbols-and-tags only and its own
    scope statement disclaims timeline semantics, script behavior, and
    rendering, so the **tile → cell geometry is not derivable from the
    preserved evidence**.  The gap is a known evidence gap that bounds visual
    land growth; closing it needs new evidence, not a derivation.

``POST /v0/level_up`` with JSON ``{"user_id"}``
    ``{protocol, ok, game_version, server_time, result, derived_level,
    level_before, level_after, curve, resources}`` — an intent only, and the
    **tenth** state-mutating surface.  This is the first line in this family
    whose legacy command carries **no committed content behind it at all**:
    ``command.level_up`` takes one positional argument and writes
    ``map["level"] = new_level`` — one line, with **no range check and no
    experience validation** (``command.py:81-85``; the catalog's own security
    note reads "Client sets the map level directly; XP/level consistency is not
    verified server-side") — and **nothing in the legacy server reads the
    committed ``levels`` curve** (zero references across ``command.py``,
    ``engine.py``, ``sessions.py``, ``server.py``, ``constants.py``).  That
    absence is what makes this the first surface where a **real guard** is
    possible rather than merely an intent-only refusal: the curve that
    constrains the level is committed content, and the committed corpus decides
    its index base.

    Only the save id enters the contract: **no level, no experience, no reward,
    no time, and no resource delta is accepted from a client** — the extra keys
    (``level``, ``new_level``, ``xp``, ``experience``, ``reward_type``,
    ``reward_amount``, ``resources_changed``, …) are ignored, so no client value
    can influence the target (design D3).  The endpoint reads the stored
    experience, derives the level the committed curve implies for it, refuses
    anything but that outcome, and dispatches the unchanged legacy ``command()``
    with the **derived** level and a **neutral** vector.

    Two refusals fail closed with **409** and no mutation, both answering
    **before** the dispatcher runs (design D4): ``level_already_current`` when
    the recorded level already equals the derived level (there is nothing to do,
    and executing ``level_up`` would rewrite an identical value), and
    ``xp_below_threshold`` when the stored experience cannot support advancing
    past the recorded level — a recorded level the curve places *above* the
    stored experience, or one the curve has no entry for.  **The committed
    corpus lands in the first refusal**: it records ``xp 4`` / ``level 1`` and
    the curve places level 1 at ``0``, so the derived level already equals the
    recorded one and the endpoint answers ``level_already_current``.  The
    success path is therefore reachable only from a state whose recorded level
    is **below** the curve's derived level — a recorded-versus-derived
    disagreement the legacy server has no opinion about.

    The **recorded** level is treated as unverified against the curve (design
    D2): the server wrote it from a client integer, so it is evidence of what a
    client once asked for and of nothing else.  Two distinct facts therefore
    exist and are never conflated — the derived level, and the recorded level,
    reported as ``level_before`` and ``level_after``.

    The ``curve`` block reports the **committed facts used** and the provenance
    of the interpretation, so a client never has to re-derive any of it:
    ``entries`` (the committed length), ``index_base`` (``"one-based"``),
    ``derivation_status`` (``"derived-provisional"``), ``rejected_alternative``
    (``"zero-based"``), the derived level's own ``entry_name`` /
    ``entry_exp_required``, the next level's ``next_level`` / ``next_name`` /
    ``next_exp_required``, the ``remaining`` experience, and the stored ``xp``
    the ladder was applied to.  The ``next_*`` and ``remaining`` fields are
    ``null`` at the curve's top level — a completed curve is reported, never
    extended.

    The one-based conversion lives in exactly one named function,
    ``level_envelope.entry_index_for_level``, and the endpoint resolves every
    level through it.  The rejected **zero-based** reading is reported in the
    ``curve`` block because the committed corpus contradicts it directly: at
    ``xp 4`` the zero-based reading implies level 0 while the save records
    level 1.

    After execution the endpoint proves the post-state in **two** ways (design
    D5) and fails closed with ``internal_error`` on any other outcome: the
    recorded level is **exactly** the derived level; **and every** stored
    resource is **unchanged**.  The second half is the family's third proof and
    the reason it matters here: ``level_up`` is dispatched with a client-sent
    vector like every other command, so a non-neutral vector would silently move
    a balance — proving that *nothing* moved is what distinguishes a correct
    level-up from a resource-minting exploit wearing its clothes.  The
    pre-execution ``resources`` are read **before** dispatch so the comparison
    starts from the state the batch actually saw.

    **No level reward is paid** (design D7): every committed entry carries
    ``reward_type`` and ``reward_amount``, and **no legacy branch reads either**,
    so paying one would invent an economy — the same discipline the expansion
    ``neighbors`` / ``inventory_qte`` requirements received.  The committed
    ``exp_required`` values are preserved **verbatim**; nothing is rebalanced,
    smoothed, or interpolated.  Unit experience (``add_xp_unit``) and the
    tutorial are out of scope: the committed corpus has no unit placements and
    0 of its 40 placed rows carry ``attr["xp"]``.

``POST /v0/queue`` with JSON ``{"user_id", "map_key", "action"}``
    ``{protocol, ok, game_version, server_time, result, action, map_key,
    previous, row, queue, resources}`` — an intent only, and the **eleventh**
    state-mutating surface, specified by the ``godot-unit-queues`` capability.
    One call carries **exactly one** of the two legacy
    queue commands, chosen by the **closed** action vocabulary (design D2):
    ``"push"`` derives ``push_queue_unit`` and ``"pop"`` derives
    ``pop_queue_unit``.  Both take **only** the legacy map index — no cost, no
    duration, no training time, no count, no readiness, and no outcome is
    accepted from a client, and the extra keys (``cost``, ``price``,
    ``training_time``, ``sm_training_time``, ``duration``, ``count``, ``nu``,
    ``ready``, ``remaining``, ``resources_changed``, ``vector``, ``unit_id``, …)
    are **ignored** (design D4).  The unchanged legacy ``command()`` dispatcher
    executes the batch in-process and the answer carries the legacy ``result``
    plus the authoritative superset: the eight-field row **as read before
    execution** (``previous``), the same row **re-read from the persisted save
    after execution** (``row``), the resolved ``action`` and ``map_key``, the
    **projected queue** (``queue``), and the current ``resources``.

    **This is the first surface whose legacy command has no server-side rule at
    all to reproduce** (design D1/D2/D5).  ``push_queue_unit``
    (``command.py:676-685`` → ``engine.py:183-189``) increments ``nu`` or sets
    it to ``1`` and stamps ``ts``; ``pop_queue_unit`` (``command.py:699-708`` →
    ``engine.py:191-204``) decrements, re-stamps ``ts`` on a partial decrement, and
    at **zero deletes ``nu``, ``ts``, and ``ui`` together**.  Nothing reads a
    queue's elapsed time, **no command completes a queue**, and no command
    materialises a unit from one — so this endpoint computes **no** readiness,
    **no** remaining time, **no** progress ratio, and **no** completion, and
    **no** count bound (the engine sets none, and a recorded absence is not
    permission to invent a cap).

    The atom-fusion push ``push_queue_unit2`` is **deliberately not exposed**
    (design D7): it takes a **client-supplied** unit id and nothing in this
    repository establishes which ids a client sends, so offering the intent would
    mean inventing a value; the client-side projection reports an unresolvable
    ``ui`` with its recorded value intact instead.

    **No queue cost is implemented** (design D4): a queue's price would be a
    **client-sent** delta, because ``do_command`` applies the request's vector
    before the branch (``command.py:40``, ``engine.py:251-271``), so the derived
    vector is **NEUTRAL** and the second post-execution proof half requires that
    **every** stored resource be **unchanged**.  The ``soulmixer_speedup``
    contract is **recorded and implemented not at all** (design D6): the legacy
    branch needs ``ts`` **and** ``ui``, raises ``KeyError`` without them, reads
    the duration from the queued unit, treats it as seconds, divides by an hour,
    **charges nothing**, and its own author labelled the formula *"quite
    useless"* — so no cost, no timer, and no speedup is offered here, and this
    route has no speedup action at all.

    Validation is structural fail-closed and **precedes** the dispatcher: a JSON
    object body, a resolvable save, a target key, an action inside the closed
    set, an addressable row, a readable attribute bag, and a derivable count.
    ``map_key`` must resolve to a row in the corpus save **before** dispatch,
    because legacy's missing-item path is a silent early return that still
    persists the batch; every other failure below also returns before the
    dispatcher runs, so the corpus is untouched on every error path.

``POST /v0/resurrect`` with JSON ``{"user_id", "x", "y"}``
    ``{protocol, ok, game_version, server_time, result, map_key, item_id,
    count_before, count_after, removed, cell, occupant_item_id,
    committed_resurrectable, committed_syringes, gates, ledger_before,
    ledger_after, placement_before, placement_after, syringe, resolution,
    clicks_to_build, refusals, no_third_gate, resources}`` — the **thirteenth**
    state-mutating surface, specified by the ``godot-unit-behaviors``
    capability, and the **first M8 surface whose mechanism reaches private
    state**.  One call carries **exactly one** legacy ``resurrect_hero`` command
    (``command.py:625-635``) and the request carries **only** a save identity and
    a cell: no map key, no item id, no syringe count, no price, and no resource
    delta is accepted, and every such key (``map_key``, ``index``, ``item_id``,
    ``used_syringe``, ``syringe``, ``cost``, ``price``, ``resources_changed``,
    ``vector``, …) is **ignored** (design D2).  The service derives the **map
    key** by resolving the addressed cell against the save's own placement rows
    and the **item id** from the player's own recorded
    ``privateState["deadHeroes"]`` ledger.

    **The three doors and the two gates** are named on the response rather than
    asserted silently: ``gates`` carries both of ``push_dead_unit``'s
    conditions — the row on **player team 1** (``engine.py:151``) and the
    committed ``resurrectable > 0`` (``engine.py:159,162``) — and **no third** is
    evaluated.  ``kill`` never reaches the ledger, ``sell`` reaches it only
    behind the ``KILL`` guard and only through the ``push_dead_unit`` **engine
    helper**, and ``resurrect_hero`` decrements with the **delete-at-zero** rule
    (``engine.py:178-179``).

    **The refused targets resolve BEFORE the dispatcher runs**, so the corpus is
    byte-identical on every one of them: an addressed cell that names no
    placement row (``unresolvable_cell``) or more than one (``ambiguous_cell``),
    a ledger that records nothing to revive
    (``unresolvable_ledger_entry``) or more than one entry (``ambiguous_ledger``),
    and a resolved entry whose committed ``resurrectable`` is not greater than
    zero (``not_resurrectable``).  Each returns a **named code with an empty
    payload** — never a partial one.

    **The two-part post-execution proof** (design D3/D5): the ledger entry is
    **gone** after a revival that reached zero, compared against the derived
    decrement; the addressed key's row now records the **derived** item id at the
    **addressed** cell; and **every** stored resource is **unchanged**, comparing
    the **full** resource set.  That last half is what makes the **no syringe
    cost** claim non-tautological: ``used_syringe`` is read from ``args[4]`` and
    **discarded** (``command.py:630``) while the committed ``syringes`` field has
    **zero** legacy consumers, so a cost could only ever arrive smuggled through
    the request's own vector, which legacy applies **before** the branch.

``POST /v0/collection`` with JSON ``{"user_id", "collection_id"}``
    ``{protocol, ok, game_version, server_time, result, collection_id, grant,
    prize, index, eligibility, store_before, store_after, ledger_before,
    ledger_after, ledger_appended, refusals, resources}`` — the **twelfth**
    state-mutating surface, specified by the ``godot-unit-collection``
    capability, and the **first whose payload is entirely content-derived**.
    One call carries **exactly one** legacy ``complete_collection`` command and
    the request carries **only** a save identity and a collection id: no prize,
    no item id, no quantity, no price, and no resource delta is accepted, and
    every such key (``prize``, ``item_id``, ``quantity``, ``item``, ``cost``,
    ``price``, ``resources_changed``, ``vector``, …) is **ignored** (design D1).
    The service looks the grant up in the loaded configuration's committed
    ``collections`` table through ``get_collection_prize``
    (``get_game_config.py:170-175``) and grants **exactly** what that collection
    grants.

    **The two-part post-execution proof is content-derived**, which is what makes
    it non-tautological: the granted id **and** quantity are compared with the
    **committed** prize bag and no other stored key may move, while the private
    state's collection ledger must match the derived one — **exactly one appended
    id** when the id was absent, or nothing appended when it was already there
    (``command.py:517-518`` is an append-if-absent, so the ledger is idempotent
    while the grant is not).  Every stored resource is **unchanged** as well,
    because the derived vector is neutral (design D1/D5).

    **The index is one-based and derived-provisional** (design D3): the id selects
    the table positionally through ``max(0, collection_id - 1)``, and the
    response reports the resolved index, whether the clamp moved it, and the id an
    aliased id resolves to — **collection id 0 and collection id 1 resolve to the
    same committed prize**, as does every negative id.

    **No eligibility check is performed and none is added** (design D2): the
    committed ``item_ids`` requirement list is read by no branch at all, so a
    caller may name **any** of the ten committed collections.  What a caller
    cannot do is choose the contents.  **No unit income, no cap semantics, and no
    experience** are derived either (design D5) — see ``collection_envelope``.

    After execution the endpoint proves the post-state in **two** ways
    (design D4) and fails closed with ``internal_error`` on any other outcome:
    the recorded ``attr`` bag matches the **derived** result for the action —
    including the exact count, the three-key teardown, the inert no-op on a row
    whose count is absent, and every key the branch does not own compared by
    value; **and every** stored resource is **unchanged**.  The start instant is
    compared by **shape** (a strict integer that does not move **backwards**)
    because the branch stamps the wall clock and its value is not derivable;
    ``engine.timestamp_now`` has one-second resolution, so two commands inside
    one second legitimately stamp the same value and a "strictly later" rule
    would refuse a correct transaction.

Deviation recorded for review: the bootstrap envelope also carries ``saves``
(the session envelope plus ``config`` and ``player_info``). Design D3 lists
only ``config`` and ``player_info``; the extra key is a superset of D3 and
keeps the envelope uniform for the boot client.

Structured errors (always JSON, always ``ok:false``, never a partial payload):

=======================  ====  =========================================================
code                     HTTP  when
=======================  ====  =========================================================
``invalid_payload``      400  body missing, not JSON, or not a JSON object
``missing_user_id``      400  ``user_id`` absent, null, or an empty string
``invalid_user_id``      400  ``user_id`` present but not a string
``unknown_user_id``      404  well-formed id that names no save
``missing_item_id``      400  ``/v0/place`` or ``/v0/purchase`` body carries no ``item_id``
``invalid_item_id``      400  ``item_id`` present but not an integer (``bool`` excluded)
``unknown_item_id``      404  integer id absent from the loaded config
``missing_item_index``   400  ``/v0/move``, ``/v0/sell``, ``/v0/store``,
                                ``/v0/upgrade``, ``/v0/construction``, or
                                ``/v0/collect`` body carries no ``item_index``
``invalid_item_index``   400  ``item_index`` present but not an integer (``bool``
                                excluded)
``unknown_item_index``   404  integer index that names no row in the save's
                                ``map["items"]`` (legacy would silently no-op)
``no_upgrade_path``      400  ``/v0/upgrade``: the addressed placement's item
                                has no resolvable next tier in the committed
                                configuration (missing reference, the ``-1`` /
                                ``0`` sentinels, or an unresolvable id) — the
                                legacy dispatcher never runs, so such a row is
                                never reduced to a bare sale
``missing_action``       400  ``/v0/construction`` body carries no ``action``
``invalid_action``       400  ``action`` present but not a string, or outside
                                the closed set ``{"start", "click", "finish"}``
``no_build_time``        400  ``/v0/construction`` with ``action "start"``: the
                                addressed placement's item has no resolvable
                                **positive** committed ``build_time`` (absent,
                                non-integer, zero, or negative) — the legacy
                                dispatcher never runs, so a non-positive
                                duration can never reach ``activate`` and
                                clear the row's whole attribute bag
``invalid_duration``     400  derived start duration is not a positive integer
                                (server-side derivation failure; never client
                                input)
``missing_expansion_id`` 400  ``/v0/expand`` body carries no ``expansion_id``
``invalid_expansion_id`` 400  ``expansion_id`` present but not an integer
                                (``bool`` excluded).  Legacy would raise
                                ``int("abc")`` out of the branch and answer an
                                unhandled HTTP 500
``unknown_expansion_id`` 404  integer id outside the committed
                                ``expansion_prices`` schedule.  The legacy
                                server does **no** range check at all — an
                                executed-legacy probe had ``expand(999)``
                                answer success — and an id the table does not
                                price must never be bought at a price no
                                committed row states
``already_expanded``     409  ``/v0/expand``: the expansion id is already in the
                                player's ``map["expansions"]`` ledger.  Legacy
                                neither deduplicates nor orders (a duplicate
                                ``expand(35)`` answered success in the
                                executed-legacy probe), so a repeat is refused
                                rather than appended
``expansion_requirements_unmet``
                          409  ``/v0/expand``: the addressed committed row
                                records a positive ``neighbors`` or
                                ``inventory_qte`` requirement (94 of the 98
                                stored rows, including **every** id the
                                committed corpus owns).  The legacy server
                                ignores both fields and nothing the delivered
                                stack can read evaluates either — no neighbour
                                count and no inventory quantity is exposed by
                                the bootstrap, the client's ``GameApi``, or the
                                corpus — so the requirement is refused, never
                                invented
``insufficient_resources``
                          409  ``/v0/expand``: a stored balance does not cover
                                the **server-derived** debit.  The legacy
                                per-resource clamp would silently under-charge
                                (an executed-legacy probe had a ``-2500`` gold
                                debit against a ``2000`` balance land on
                                ``0``), and a partially applied debit is
                                indistinguishable from a wrong derivation, so
                                the refusal is the recorded alternative to
                                reproducing the clamp
``level_already_current``
                          409  ``/v0/level_up``: the recorded level already
                                equals the level the committed curve derives
                                for the stored experience.  The committed
                                corpus lands here (``xp 4`` / ``level 1``, and
                                the curve places level 1 at ``0``): there is
                                nothing to do, and executing ``level_up`` would
                                rewrite an identical value.  The legacy
                                dispatcher never runs
``xp_below_threshold``    409  ``/v0/level_up``: the stored experience cannot
                                support advancing past the recorded level — a
                                recorded level the committed curve places above
                                the stored experience, or one the curve has no
                                entry for.  The recorded level is client-sourced
                                and unverified (design D2), so a disagreement is
                                **reported**, never reconciled, and never paid
                                for.  The legacy dispatcher never runs
``capped_collection``    409  ``/v0/collect``: the addressed placement's item
                                records a **non-zero** committed ``max_collects``
                                — only ``0`` is implemented, because nothing in
                                the repository says whether a non-zero cap
                                limits one collection, a daily total, or a
                                building's lifetime output.  The legacy
                                dispatcher never runs, and the cap is never
                                interpreted
``unknown_collect_type`` 409  ``/v0/collect``: the addressed placement's item
                                records a ``collect_type`` outside the
                                committed vocabulary ``{g, w, o, s, c}`` (the
                                census is 731/23/11/11/2 over the 778 stored
                                items, and no item records a mana type, so the
                                vector's ``mana`` slot is always zero).  The
                                value is refused, never coerced into an assumed
                                resource
``no_income``            409  ``/v0/collect``: the addressed placement's item
                                records a committed collection amount of ``0``,
                                or none it can describe (absent, non-integer, or
                                negative) — 727 of the 778 stored items and 39 of
                                the corpus's 40 placed rows.  The legacy
                                dispatcher never runs
``too_early``            409  ``/v0/collect``: the addressed row's elapsed time
                                since its recorded collection instant has
                                reached **no** committed ladder rung
                                (``COLLECT_MINUTES[0] = 5``), so a payout would
                                have to be invented.  No corpus row carries a
                                recent instant, so this path is covered by a
                                stubbed instant rather than by a fixture
``construction_in_progress``
                          409  ``/v0/collect``: the addressed row's attribute
                                bag carries a construction countdown (``cp``) or
                                a build-click counter (``nc``).  ``collect``
                                writes the same ``item[3]`` that
                                ``activate`` stamps as a build's start instant,
                                and an executed-legacy probe showed the
                                countdown surviving the overwrite while the
                                legacy server answered success.  Refused before
                                the dispatcher runs, so the delivered
                                construction timers are never corrupted
``missing_map_key``      400  ``/v0/queue`` body carries no ``map_key``
``invalid_map_key``      400  ``map_key`` present but not an integer (``bool``
                                excluded).  Legacy would raise out of
                                ``map_get_item`` on a non-integer and answer an
                                unhandled HTTP 500
``unknown_map_key``      404  integer key that names no row in the save's
                                ``map["items"]`` (legacy logs an error and returns
                                early, a silent no-op that still persists the
                                batch)
``invalid_attr``         500  the addressed row carries no object attribute bag,
                                or a ``nu`` that is not a non-negative integer —
                                a server-side shape failure, never client input
``missing_collection_id`` 400 ``/v0/collection`` body carries no ``collection_id``
``invalid_collection_id`` 400 ``collection_id`` present but not a strict integer
                                (``bool``, float, and string all excluded — legacy
                                would raise out of ``collection - 1`` or index the
                                table with a fractional index)
``unknown_collection_id`` 409 ``/v0/collection``: the one-based index
                                ``max(0, collection_id - 1)`` lands outside the
                                committed 10-entry ``collections`` table.
                                ``get_collection_prize`` returns ``None`` there
                                and the branch's next statement raises
                                ``TypeError``, so this is refused **before** the
                                dispatcher runs.  A **negative** or zero id is
                                NOT this code: the clamp resolves it to index 0,
                                so it is answered with the id-1 grant and
                                ``index.aliased: true``
``invalid_reason``       400  derived reason is not a string (server-side
                                derivation failure; never client input)
``missing_cell``         400  ``/v0/resurrect`` body carries no ``x`` or no ``y``
``invalid_cell``         400  ``/v0/resurrect`` ``x``/``y`` present but not strict
                                integers (``bool``, float, and string all
                                excluded), or outside the shared ``0..99`` anchor
                                range — a structural refusal on a shape legacy
                                never validated, not a gameplay claim
``unresolvable_cell``    409  ``/v0/resurrect``: no placement row records the
                                addressed cell, so it resolves to no revival
                                target.  Refused **before** the dispatcher runs,
                                so the corpus is unchanged
``ambiguous_cell``       409  ``/v0/resurrect``: more than one placement row
                                records the addressed cell and the legacy
                                contract records no tie-break, so none is invented
``unresolvable_ledger_entry`` 409 ``/v0/resurrect``: the player's
                                ``privateState["deadHeroes"]`` is empty, so the
                                addressed cell resolves to no recorded ledger
                                entry.  **This is what the committed corpus itself
                                produces.**
``ambiguous_ledger``     409  ``/v0/resurrect``: the ledger holds more than one
                                entry and no committed rule chooses between them
``not_resurrectable``    409  ``/v0/resurrect``: the resolved ledger entry's
                                committed ``properties`` carry no
                                ``resurrectable`` flag, or one that is not greater
                                than zero — ``push_dead_unit`` would have refused
                                it at ``engine.py:159-162``, so it could never have
                                entered the ledger through the legacy increment
``invalid_coordinates``  400  ``x``/``y`` missing, not integers, or outside ``0..99``
``invalid_orientation``  400  ``orientation`` present but not an integer
``costs_not_cash``       400  ``/v0/purchase`` item's config price is not a cash
                               price (absent, empty, another resource, mixed)
``bad_request``          400  other malformed requests Flask rejects
``not_found``            404  unknown path
``method_not_allowed``   405  known path, unsupported method
``internal_error``       500  unhandled server failure (including legacy
                              execution raising after validation passed)
=======================  ====  =========================================================

Persistence scope (design D6, spec ``godot-compatibility-boot``): the
session and bootstrap endpoints never persist — this module never calls
``sessions.save_session`` for them and every call leaves the saves
byte-identical. ``POST /v0/place``, ``POST /v0/purchase``,
``POST /v0/move``, ``POST /v0/sell``, ``POST /v0/store``,
``POST /v0/upgrade``, ``POST /v0/construction``, ``POST /v0/collect``,
``POST /v0/expand``, ``POST /v0/level_up``, ``POST /v0/queue``,
``POST /v0/collection``, and ``POST /v0/resurrect``
execute the unchanged legacy ``command()`` dispatcher, which
persists through legacy ``save_session`` into the **service corpus's**
``saves/`` and nowhere else; the service never opens a working-tree file for
writing, and it never binds anywhere except ``127.0.0.1`` (the bind address
lives here so both the start command and the tests read one constant).
"""

from __future__ import annotations

import copy
import os
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

import compat_legacy
import behavior_envelope
import collect_envelope
import collection_envelope
import construction_envelope
import expand_envelope
import level_envelope
import move_envelope
import placement_envelope
import purchase_envelope
import queue_envelope
import sell_envelope
import store_envelope
import upgrade_envelope
import research_envelope
import quest_envelope

PROTOCOL = "compat-v0"
HOST = "127.0.0.1"
DEFAULT_PORT = 5056

ERROR_INVALID_PAYLOAD = "invalid_payload"
ERROR_MISSING_USER_ID = "missing_user_id"
ERROR_INVALID_USER_ID = "invalid_user_id"
ERROR_UNKNOWN_USER_ID = "unknown_user_id"
ERROR_MISSING_ITEM_ID = "missing_item_id"
ERROR_INVALID_ITEM_ID = "invalid_item_id"
ERROR_UNKNOWN_ITEM_ID = "unknown_item_id"
ERROR_MISSING_ITEM_INDEX = "missing_item_index"
ERROR_INVALID_ITEM_INDEX = "invalid_item_index"
ERROR_UNKNOWN_ITEM_INDEX = "unknown_item_index"
ERROR_NO_UPGRADE_PATH = "no_upgrade_path"
ERROR_MISSING_ACTION = "missing_action"
ERROR_INVALID_ACTION = "invalid_action"
ERROR_NO_BUILD_TIME = "no_build_time"
ERROR_CAPPED_COLLECTION = "capped_collection"
ERROR_UNKNOWN_COLLECT_TYPE = "unknown_collect_type"
ERROR_NO_INCOME = "no_income"
ERROR_TOO_EARLY = "too_early"
ERROR_CONSTRUCTION_IN_PROGRESS = "construction_in_progress"
ERROR_INVALID_REASON = "invalid_reason"
ERROR_INVALID_COORDINATES = "invalid_coordinates"
ERROR_INVALID_ORIENTATION = "invalid_orientation"
ERROR_INVALID_DURATION = "invalid_duration"
ERROR_COSTS_NOT_CASH = "costs_not_cash"
ERROR_MISSING_EXPANSION_ID = "missing_expansion_id"
ERROR_INVALID_EXPANSION_ID = "invalid_expansion_id"
ERROR_UNKNOWN_EXPANSION_ID = "unknown_expansion_id"
ERROR_ALREADY_EXPANDED = "already_expanded"
ERROR_EXPANSION_REQUIREMENTS_UNMET = "expansion_requirements_unmet"
ERROR_INSUFFICIENT_RESOURCES = "insufficient_resources"
ERROR_LEVEL_ALREADY_CURRENT = "level_already_current"
ERROR_XP_BELOW_THRESHOLD = "xp_below_threshold"
ERROR_MISSING_MAP_KEY = "missing_map_key"
ERROR_INVALID_MAP_KEY = "invalid_map_key"
ERROR_UNKNOWN_MAP_KEY = "unknown_map_key"
ERROR_MISSING_COLLECTION_ID = "missing_collection_id"
ERROR_INVALID_COLLECTION_ID = "invalid_collection_id"
ERROR_UNKNOWN_COLLECTION_ID = "unknown_collection_id"
ERROR_INVALID_ATTR = "invalid_attr"
ERROR_MISSING_CELL = "missing_cell"
ERROR_INVALID_CELL = "invalid_cell"
ERROR_UNRESOLVABLE_CELL = "unresolvable_cell"
ERROR_AMBIGUOUS_CELL = "ambiguous_cell"
ERROR_UNRESOLVABLE_LEDGER_ENTRY = "unresolvable_ledger_entry"
ERROR_AMBIGUOUS_LEDGER = "ambiguous_ledger"
ERROR_NOT_RESURRECTABLE = "not_resurrectable"
ERROR_MISSING_TRACK = "missing_track"
ERROR_INVALID_TRACK = "invalid_track"
ERROR_UNRESOLVABLE_RESEARCH_STATE = "unresolvable_research_state"
ERROR_MISSING_GOAL_INDEX = "missing_goal_index"
ERROR_INVALID_GOAL_INDEX = "invalid_goal_index"
ERROR_MISSING_QUEST_VAR_KEY = "missing_key"
ERROR_INVALID_QUEST_VAR_KEY = "invalid_key"
ERROR_IGNORED_QUEST_VAR_KEY = "ignored_quest_var_key"
ERROR_MISSING_MISSION = "missing_mission"
ERROR_INVALID_MISSION = "invalid_mission"
ERROR_MISSING_QUEST_INDEX = "missing_quest_index"
ERROR_INVALID_QUEST_INDEX = "invalid_quest_index"
ERROR_MISSING_QUEST_ID = "missing_quest_id"
ERROR_INVALID_QUEST_ID = "invalid_quest_id"
ERROR_UNRESOLVABLE_QUEST_STATE = "unresolvable_quest_state"
ERROR_BAD_REQUEST = "bad_request"
ERROR_NOT_FOUND = "not_found"
ERROR_METHOD_NOT_ALLOWED = "method_not_allowed"
ERROR_INTERNAL = "internal_error"


def envelope(boot: compat_legacy.LegacyBoot, **extra: Any) -> Dict[str, Any]:
    """The documented v0 envelope: protocol flag, legacy version, server time."""
    payload: Dict[str, Any] = {
        "protocol": PROTOCOL,
        "ok": True,
        "game_version": boot.game_version,
        "server_time": boot.server_time(),
    }
    payload.update(extra)
    return payload


def error_payload(code: str, message: str) -> Dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "ok": False,
        "error": {"code": code, "message": message},
    }


def error_response(status: int, code: str, message: str) -> Tuple[Dict[str, Any], int]:
    return error_payload(code, message), status


def _resolve_user_id(payload: Any) -> Tuple[Optional[str], Optional[Tuple[Dict[str, Any], int]]]:
    """Validate a bootstrap body; returns ``(user_id, error_response)``."""
    if payload is None:
        return None, error_response(
            400, ERROR_INVALID_PAYLOAD, "request body must be a JSON object"
        )
    if not isinstance(payload, dict):
        return None, error_response(
            400, ERROR_INVALID_PAYLOAD, "request body must be a JSON object"
        )
    if "user_id" not in payload:
        return None, error_response(400, ERROR_MISSING_USER_ID, "user_id is required")
    value = payload["user_id"]
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, error_response(
            400, ERROR_MISSING_USER_ID, "user_id must be a non-empty string"
        )
    if not isinstance(value, str):
        return None, error_response(
            400, ERROR_INVALID_USER_ID, "user_id must be a string"
        )
    return value, None


def _legacy_boot_error(
    failure: compat_legacy.LegacyBootError,
) -> Tuple[Dict[str, Any], int]:
    """Map a legacy adapter precondition failure onto a structured error.

    Messages carry only the adapter's own diagnostic (client-supplied ids
    and error codes), never save content.
    """
    if failure.code == "unknown_user_id":
        return error_response(404, ERROR_UNKNOWN_USER_ID, str(failure))
    return error_response(500, ERROR_INTERNAL, "%s: %s" % (failure.code, failure))


def _seed_dead_heroes(boot: compat_legacy.LegacyBoot) -> Dict[str, Any]:
    """Apply the opt-in dead-hero seed to the running corpus, if one was asked for.

    The committed corpus records ``privateState["deadHeroes"] == {}`` and places
    no resurrectable row at all, so ``POST /v0/resurrect``'s positive path cannot
    be exercised against it — and no executed-legacy fixture exists either,
    because capturing one would require manufacturing a unit row first (the
    committed investigation's named cause).

    This is the verification seam that lets the live phase drive one real
    revival: it is **absent by default**, so no normal run, no unittest, and no
    other live phase is affected, and a malformed value is a named refusal
    rather than a silent no-op so a typo can never make a seeding claim quietly
    false.  It writes the **in-memory** save of the running corpus only — the
    corpus the live-phase harness builds under the system temp root and removes
    on stop — and never a committed save.  The derivation and the format live in
    :mod:`behavior_envelope`; only the trigger lives here.
    """
    raw = os.environ.get(behavior_envelope.SEED_ENVIRONMENT)
    if raw is None:
        return {"seeded": False, "reason": "not requested", "error": ""}
    result: Dict[str, Any] = {
        "seeded": False,
        "reason": "",
        "error": "",
        "user_id": "",
        "after": None,
    }
    user_ids = boot.known_user_ids()
    if not user_ids:
        result["reason"] = "no save"
        result["error"] = "the running corpus holds no save to seed"
        return result
    user_id = str(user_ids[0])
    seeded = behavior_envelope.seed_ledger_from_environment(
        boot.save_document(user_id), raw
    )
    result["seeded"] = bool(seeded.get("seeded", False))
    result["reason"] = str(seeded.get("reason", ""))
    result["error"] = str(seeded.get("error", ""))
    result["user_id"] = user_id
    result["after"] = seeded.get("after")
    return result


def _committed_item(
    boot: compat_legacy.LegacyBoot, item_id: int
) -> Optional[Dict[str, Any]]:
    """One item id's committed configuration row, verbatim, or ``None``.

    Read from the **loaded legacy configuration** rather than the committed
    normalized package: ``push_dead_unit`` reads the **raw configuration
    string** through ``get_attribute_from_item_id`` and then ``json.loads`` it
    (``engine.py:154-162``), so the endpoint evaluates the gate against exactly
    the bytes the legacy helper would have read — its ``properties`` is a raw
    JSON **string** here.  The committed normalized package stores the same
    values as an **object**, which is the R2 coercion boundary M8 line 1
    recorded: the two agree on *values*, never on *representation*.

    The row is located by its own native ``id`` column, exactly as
    ``get_item_from_id`` does (``get_game_config.py:119-125``).  Item ids are
    unique across the loaded items — measured over the whole committed set, 0
    duplicates — so there is nothing to disambiguate, and a last-match scan
    reproduces the id-to-position index's own last-wins behaviour.  ``None``
    means the loaded configuration holds no such item, which the legacy gate
    treats exactly like an absent flag.
    """
    config = boot.config()
    items = config.get("items")
    if not isinstance(items, list):
        return None
    found: Optional[Dict[str, Any]] = None
    for row in items:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get("id")) != int(item_id):
                continue
        except (TypeError, ValueError):
            continue
        found = row
    return dict(found) if found is not None else None


def create_app(legacy: Optional[compat_legacy.LegacyBoot] = None) -> Flask:
    """Build the v0 Flask app over an already-initialized legacy boot state."""
    boot = legacy if legacy is not None else compat_legacy.current()
    # Applied once, before the first request, so the opt-in seeded ledger is
    # visible to ``POST /v0/resurrect`` exactly as a persisted one would be.
    app_seed = _seed_dead_heroes(boot)
    if str(app_seed.get("reason", "")) != "not requested":
        print(
            "compat-api: dead-hero seed %s for %s: seeded=%s after=%r%s"
            % (
                behavior_envelope.SEED_ENVIRONMENT,
                app_seed.get("user_id", "") or "(no save)",
                app_seed.get("seeded"),
                app_seed.get("after"),
                (" error=%s" % app_seed["error"]) if app_seed.get("error") else "",
            )
        )

    app = Flask(__name__, static_folder=None)

    @app.get("/v0/session")
    def v0_session() -> Response:
        return jsonify(envelope(boot, saves=boot.session_list()))

    @app.post("/v0/bootstrap")
    def v0_bootstrap() -> Tuple[Dict[str, Any], int]:
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )
        body = envelope(
            boot,
            saves=boot.session_list(),
            config=boot.config(),
            player_info=boot.player_info(user_id),
        )
        return body, 200

    @app.post("/v0/place")
    def v0_place() -> Tuple[Dict[str, Any], int]:
        """Execute one placement intent through the unchanged legacy path.

        Validation is structural fail-closed (design D5): resolvable save,
        integer item id present in config, integer anchor in the town grid.
        Gameplay rules (grid bounds display, occupancy, affordability) are
        the client's job exactly as they were Flash's — legacy ``buy``
        performs no validation either — and anti-cheat validation belongs
        to Server v1 (M13).  Every failure below returns before the legacy
        dispatcher runs, so the corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_id" not in payload:
            return error_response(400, ERROR_MISSING_ITEM_ID, "item_id is required")
        item_id = payload["item_id"]
        if not placement_envelope.is_strict_int(item_id):
            return error_response(
                400, ERROR_INVALID_ITEM_ID, "item_id must be an integer"
            )
        if not boot.has_item(item_id):
            return error_response(
                404, ERROR_UNKNOWN_ITEM_ID, "no config item with id %d" % item_id
            )

        x = payload.get("x")
        y = payload.get("y")
        if (
            not placement_envelope.is_strict_int(x)
            or not placement_envelope.is_strict_int(y)
            or not placement_envelope.in_grid(x, y)
        ):
            return error_response(
                400,
                ERROR_INVALID_COORDINATES,
                "x and y must be integers with anchors inside the "
                "0..%d town grid" % (placement_envelope.GRID_EXTENT - 1),
            )

        orientation = payload.get("orientation", 0)
        if not placement_envelope.is_strict_int(orientation):
            return error_response(
                400, ERROR_INVALID_ORIENTATION, "orientation must be an integer"
            )

        # Derive the legacy envelope from this save's own state (design D4).
        try:
            envelope_payload = placement_envelope.build_envelope(
                item_id=item_id,
                x=x,
                y=y,
                costs=boot.item_costs(item_id),
                items=boot.map_items(user_id),
                orientation=orientation,
            )
        except placement_envelope.EnvelopeError as failure:
            if failure.code.startswith("costs_"):
                # Derived from committed config, not from client input:
                # the config itself is unresolvable, so this is server-side.
                return error_response(
                    500, ERROR_INTERNAL, "config costs not derivable: %s" % failure.code
                )
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        slot = envelope_payload["commands"][0][2][0]  # type: ignore[index]
        try:
            placement = boot.map_items(user_id).get(str(slot))
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(placement, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                placement=placement,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/purchase")
    def v0_purchase() -> Tuple[Dict[str, Any], int]:
        """Execute one purchase intent through the unchanged legacy path.

        Validation is structural fail-closed (design D3/D5): a JSON object
        body, a resolvable save, an integer item id present in config, and a
        cash-only config price (design D2).  The level gate and cash
        affordability are gameplay rules the client owns exactly as they were
        Flash's — legacy ``buy_stored_item_cash`` performs no validation at
        all — and anti-cheat validation belongs to Server v1 (M13).  Every
        failure below returns before the legacy dispatcher runs, so the corpus
        is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_id" not in payload:
            return error_response(400, ERROR_MISSING_ITEM_ID, "item_id is required")
        item_id = payload["item_id"]
        if not purchase_envelope.is_strict_int(item_id):
            return error_response(
                400, ERROR_INVALID_ITEM_ID, "item_id must be an integer"
            )
        if not boot.has_item(item_id):
            return error_response(
                404, ERROR_UNKNOWN_ITEM_ID, "no config item with id %d" % item_id
            )

        # Derive the legacy envelope from the loaded config (design D2).  The
        # contract carries no price, quantity, or resource delta: extra keys
        # are ignored so the client's own derivation can never win.
        try:
            envelope_payload = purchase_envelope.build_envelope(
                item_id=item_id,
                costs=boot.item_costs(item_id),
            )
        except purchase_envelope.EnvelopeError as failure:
            if failure.code == ERROR_COSTS_NOT_CASH:
                # The item exists but is not priced in cash alone, so this
                # command's price is not derivable — the client should not
                # have offered the item (a derivation boundary, not a
                # gameplay rule).
                return error_response(400, ERROR_COSTS_NOT_CASH, str(failure))
            if failure.code.startswith("costs_"):
                # Derived from committed config, not from client input:
                # the config itself is unresolvable, so this is server-side.
                return error_response(
                    500, ERROR_INTERNAL, "config costs not derivable: %s" % failure.code
                )
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Read back what actually landed: the whole storage mapping (design
        # D4) so the client needs no arithmetic for pre-existing contents.
        try:
            store = boot.map_store(user_id)
        except compat_legacy.LegacyBootError:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        if not isinstance(store, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        try:
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        return (
            envelope(
                boot,
                result="success",
                store=store,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/move")
    def v0_move() -> Tuple[Dict[str, Any], int]:
        """Execute one move intent through the unchanged legacy path.

        Validation is structural fail-closed (design D3/D5): a JSON object
        body, a resolvable save, an integer item index that names a row in
        the corpus save, and integer anchor coordinates inside the town grid.
        Grid bounds as a *gameplay* rule, footprint occupancy (with the moving
        building's own cells excluded), and the refusal of a no-op move to the
        cell the building already occupies are the client's job exactly as
        they were Flash's — legacy ``move`` performs no validation at all — and
        anti-cheat validation belongs to Server v1 (M13).  The item index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:126-129``) is a silent early return
        that still persists the save: reporting that as a success would claim a
        state change that never happened.  Every failure below returns before
        the legacy dispatcher runs, so the corpus is untouched on every error
        path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not move_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        x = payload.get("x")
        y = payload.get("y")
        if (
            not move_envelope.is_strict_int(x)
            or not move_envelope.is_strict_int(y)
            or not move_envelope.in_grid(x, y)
        ):
            return error_response(
                400,
                ERROR_INVALID_COORDINATES,
                "x and y must be integers with anchors inside the "
                "0..%d town grid" % (move_envelope.GRID_EXTENT - 1),
            )

        # Resolve the index against the corpus before deriving: an index that
        # names no row must fail closed, never reach legacy's silent no-op.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )

        # Derive the legacy envelope (design D6): the neutral resource vector
        # and the discarded frame/string placeholders are the module's, never
        # the client's.  The contract carries no price or resource delta:
        # extra keys are ignored so the client's own derivation can never win.
        try:
            envelope_payload = move_envelope.build_envelope(
                item_index=item_index,
                x=x,
                y=y,
            )
        except move_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Read back what actually landed: the persisted eight-field row at that
        # key (design D4), so the client never has to reconstruct it.
        try:
            placement = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(placement, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                placement=placement,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/sell")
    def v0_sell() -> Tuple[Dict[str, Any], int]:
        """Execute one sell intent through the unchanged legacy path.

        Validation is structural fail-closed (design D4/D6): a JSON object
        body, a resolvable save, and an integer item index that names a row in
        the corpus save.  Whether the building is sellable at all, who owns
        it, and what it refunds are the client's job exactly as they were
        Flash's — legacy ``sell`` performs no validation at all — and
        anti-cheat validation belongs to Server v1 (M13).  The index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:154-156``) is a silent early return
        that still persists the save: reporting that as a success would claim
        a removal that never happened.

        No reason is accepted from the client (design D3): the envelope's is
        the derived empty string, so no client can claim ``"KILL"`` and reach
        ``push_dead_unit``.  No price, refund, or resource delta is accepted
        either; the derived vector is neutral, so **this endpoint claims no
        refund** — the committed configuration records no building-sale
        refund rule and the legacy refund travels only in client-sent deltas
        (design D2).  Every failure below returns before the legacy dispatcher
        runs, so the corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not sell_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to remove is the one the persisted save no longer
        # holds afterwards (design D5).
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            removed = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(removed, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # A copy: the in-memory row is the one the legacy dispatcher deletes
        # from the map, so the response must not alias live state.
        removed_row = list(removed)

        # Derive the legacy envelope (design D2/D3/D7): the neutral resource
        # vector and the derived reason are the module's, never the client's.
        # The contract carries no reason, refund, price, or resource delta:
        # extra keys are ignored so the client's own derivation can never win.
        try:
            envelope_payload = sell_envelope.build_envelope(item_index=item_index)
        except sell_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the removal: re-read the map after execution and fail closed
        # if the key survives.  Legacy's branch deleted it, but reporting a
        # removal that the persisted save does not show would be a fabricated
        # authoritative answer (design D5).
        try:
            still_present = boot.has_map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not remove the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/store")
    def v0_store() -> Tuple[Dict[str, Any], int]:
        """Execute one store intent through the unchanged legacy path.

        Validation is structural fail-closed (design D4/D5): a JSON object
        body, a resolvable save, and an integer item index that names a row in
        the corpus save.  Whether the placement is a building the player may
        store at all, who owns it, and whether storage is full are the client's
        job exactly as they were Flash's — legacy ``store_item`` performs no
        validation at all — and anti-cheat validation belongs to Server v1
        (M13).  The index is resolved here rather than left to legacy, because
        legacy's missing-item path (``command.py:222-224``) logs an error and
        returns early while the batch still persists: reporting that as a
        success would claim a state change that never happened.

        No quantity is accepted from the client (design D3): the branch calls
        ``engine.add_store_item(map, item_id)`` without its third argument, so
        legacy's default of exactly ``1`` is the only quantity it can use.  No
        price or resource delta is accepted either; the derived vector is
        neutral, so **this endpoint claims no storing cost** — the committed
        configuration records no storing price — and, because the catalog
        records that legacy has *no* capacity check, **no capacity rule is
        claimed** either.  The legacy branch deliberately does not write
        ``privateState.boughtUnits`` (unlike ``buy`` /
        ``place_stored_item`` / ``buy_stored_item_cash``), and that is
        reproduced exactly rather than "fixed".

        Every failure below returns before the legacy dispatcher runs, so the
        corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not store_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to store is the one the persisted save no longer holds
        # afterwards (design D4/D5).  The item id is read from the row here for
        # the same reason: it is what legacy's ``add_store_item`` increments,
        # so it is what the storage proof below must look for.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            removed = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(removed, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # A copy: the in-memory row is the one the legacy dispatcher pops
        # from the map, so the response must not alias live state.
        removed_row = list(removed)
        item_id = removed_row[0] if removed_row else None
        if not store_envelope.is_strict_int(item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to store",
            )

        # Derive the legacy envelope (design D2/D6): the neutral resource
        # vector is the module's, never the client's.  The contract carries no
        # quantity, price, or resource delta: extra keys are ignored so the
        # client's own derivation can never win.
        try:
            envelope_payload = store_envelope.build_envelope(item_index=item_index)
        except store_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove BOTH halves of the move from the persisted save: the popped key
        # must be gone *and* the item's id must be present in the storage.
        # Reporting either half that the save does not show would be a
        # fabricated authoritative answer (design D4), so each fails closed.
        try:
            still_present = boot.has_map_item(user_id, item_index)
            store = boot.map_store(user_id)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not remove the placement entry",
            )
        if not isinstance(store, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        if str(item_id) not in store:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                store=store,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/upgrade")
    def v0_upgrade() -> Tuple[Dict[str, Any], int]:
        """Execute one upgrade intent through the unchanged legacy path.

        An upgrade is one legacy batch with **two** commands in a forced
        order — a ``sell`` with the committed ``UPGR`` reason followed by a
        ``buy`` of the target tier reusing the row's own key and cell
        (design D1).  Validation is structural fail-closed (design D3/D7): a
        JSON object body, a resolvable save, an integer item index that names
        a row in the corpus save, and a placement whose item has a resolvable
        next tier in the committed configuration.  Whether the building is
        upgradeable *today* is the client's job — legacy performs no
        validation of any kind — and the legacy client's level gate, daily
        limit, and space check are deliberately not implemented (design D6);
        authoritative validation belongs to Server v1 (M13).  The index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:154-156``) is a silent early return
        that still persists the save: reporting that as a success would claim an
        upgrade that never happened.

        Nothing but the index enters the contract: no target tier, no reason,
        no coordinates, no orientation, no player, no quantity, no price, and
        no resource deltas are accepted from a client — the extra keys are
        ignored.  Because the committed configuration records no upgrade
        price, the derived vector is neutral, so **this endpoint claims no
        upgrade cost of any kind** (design D4).

        After execution the endpoint proves the replacement from the persisted
        save with all three documented facts (design D3) and fails closed with
        ``internal_error`` on any other outcome — including the outcome the
        *reverse* command order produces, which the legacy server itself
        reports as a success.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not upgrade_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to upgrade is the one the two derived commands replace.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            removed = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(removed, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # Copies: the legacy dispatcher deletes this very list from the map
        # and writes a new one in its place, so the response must never alias
        # live state.
        removed_row = list(removed)
        if len(removed_row) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        source_item_id = removed_row[0]
        if not upgrade_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to upgrade",
            )
        # The cell, orientation, and player come from the row being replaced:
        # the buy half reuses the very same key and cell so the pair upgrades
        # in place instead of re-keying the building (design D2).
        source_x, source_y = removed_row[1], removed_row[2]
        source_orientation = removed_row[4]
        source_player = removed_row[7]

        # The target tier comes from the committed configuration's
        # ``upgrades_to``, never from the client.  ``None`` means the item has
        # no upgrade path (missing reference, the -1/0 sentinels, or an id the
        # config does not resolve), and answering here — before the dispatcher
        # runs — is exactly what keeps an un-upgradeable building from being
        # reduced to a bare sale (design D3).
        try:
            target_item_id = boot.item_upgrade_to(source_item_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if target_item_id is None:
            return error_response(
                400,
                ERROR_NO_UPGRADE_PATH,
                "item %d has no resolvable next tier in the configuration"
                % source_item_id,
            )

        # Derive the legacy envelope (design D2/D4/D8): the committed reason,
        # the neutral resource vector on both commands, and the buy half's
        # discarded placeholders are the module's, never the client's.
        try:
            envelope_payload = upgrade_envelope.build_envelope(
                item_index=item_index,
                target_item_id=target_item_id,
                x=source_x,
                y=source_y,
                player=source_player,
                orientation=source_orientation,
            )
        except upgrade_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result —
        # which is precisely why it is NOT taken as proof of an upgrade.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the replacement from the persisted save (design D3).  All three
        # facts are required: the key still exists, its item id is the derived
        # target tier, and its cell is the pre-execution cell.  The reverse
        # command order — which legacy also reports as a success — leaves the
        # key absent and is caught by the first check; reporting either row
        # without proving it would be a fabricated authoritative answer.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            upgraded = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(upgraded, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the upgraded placement entry",
            )
        upgraded_row = list(upgraded)
        if len(upgraded_row) != 8 or not upgrade_envelope.is_strict_int(
            upgraded_row[0]
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field upgraded row",
            )
        if upgraded_row[0] != target_item_id:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d holds item %r after execution, not the "
                "derived target tier %r"
                % (item_index, upgraded_row[0], target_item_id),
            )
        if [upgraded_row[1], upgraded_row[2]] != [source_x, source_y]:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d sits at %r after execution, not at the "
                "pre-execution cell %r"
                % (item_index, [upgraded_row[1], upgraded_row[2]], [source_x, source_y]),
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                upgraded=upgraded_row,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/construction")
    def v0_construction() -> Tuple[Dict[str, Any], int]:
        """Execute one construction intent through the unchanged legacy path.

        One call carries **exactly one** of the three legacy construction
        commands, chosen by the closed action vocabulary (design D2): a
        ``"start"`` derives ``activate`` with a duration read from the
        addressed placement's item's committed ``build_time``, a ``"click"``
        derives ``add_click``, and a ``"finish"`` derives
        ``activate_item_click``.  The three commands are three *outcomes* of one
        client-side state machine, not one transaction, so they are never
        composed into a single batch here.

        Validation is structural fail-closed (design D3/D7): a JSON object body,
        a resolvable save, an integer item index that names a row in the corpus
        save, an action inside the closed set, and — for a start only — an item
        whose committed build time resolves to a **positive** integer.  The
        index is resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:416-419``, ``528-531``, ``539-542``)
        logs an error and returns early while the batch still persists:
        reporting that as a success would claim a state change that never
        happened.  Legacy performs no ownership, state, or gameplay validation
        of any kind: whether a build may start on a row that already carries
        construction state, and whether the counter has reached the item's
        ``clicks_to_build`` (which **no** branch compares), are client-side
        rules exactly as they were Flash's; authoritative validation belongs to
        Server v1 (M13).

        Nothing but the index and the action enters the contract: no duration,
        price, quantity, or resource delta is accepted from a client — the
        extra keys are ignored.  The start duration is therefore derived from
        committed content alone, which is why this line has no derived
        placeholder argument at all.  Because the committed configuration
        records no price for building, the derived vector is neutral, so
        **this endpoint claims no building cost** (design D4).  A non-positive
        duration is refused twice over — ``no_build_time`` when committed
        content cannot supply one, ``invalid_duration`` if the derivation ever
        produced one — because legacy's ``activate`` with a non-positive
        duration **clears the addressed row's whole attribute bag**
        (``command.py:425-427``), destroying the click counter and any
        friend-assist entries; this contract therefore exposes no cancel action
        at all (design D6).

        After execution the endpoint proves the per-action post-condition
        (design D3) and fails closed with ``internal_error`` on any other
        outcome: the row still exists and is a list, and then the action's own
        check — a start carries the derived countdown, a click carries a
        counter of at least one, a completion carries none.  Reporting a
        construction that the persisted save does not show would be a fabricated
        authoritative answer.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not construction_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        if "action" not in payload:
            return error_response(400, ERROR_MISSING_ACTION, "action is required")
        action = payload["action"]
        if not construction_envelope.is_action(action):
            return error_response(
                400,
                ERROR_INVALID_ACTION,
                "action must be one of %s"
                % ", ".join(sorted(construction_envelope.ACTIONS)),
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to build is the row the three commands mutate in place.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            previous = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(previous, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # Copies: the legacy dispatcher mutates this very row **in place** —
        # ``activate`` writes ``item[3]`` and ``item[6]``, and
        # ``add_click`` / ``activate_item_click`` mutate the same attribute-bag
        # dict — so a shallow list copy would still alias the live bag and the
        # "before" row would report the after-state.  The bag and the stored-unit
        # payload are copied too.
        previous_row = list(previous)
        if isinstance(previous_row[6], dict):
            previous_row[6] = dict(previous_row[6])
        if isinstance(previous_row[5], list):
            previous_row[5] = list(previous_row[5])
        if len(previous_row) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        source_item_id = previous_row[0]
        if not construction_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to build",
            )

        # The start duration comes from the item's committed ``build_time``,
        # never from the client.  ``None`` means no resolvable positive
        # duration (absent, non-integer, zero, or negative), and answering here
        # — before the dispatcher runs — is what keeps an unbuildable row from
        # ever reaching ``activate``'s attribute-bag-clearing branch
        # (design D3/D6).  Only a start resolves one: a click and a completion
        # carry no duration argument at all.
        duration: Optional[int] = None
        if action == construction_envelope.ACTION_START:
            try:
                duration = boot.item_build_time(source_item_id)
            except compat_legacy.LegacyBootError as failure:
                return _legacy_boot_error(failure)
            if duration is None:
                return error_response(
                    400,
                    ERROR_NO_BUILD_TIME,
                    "item %d has no resolvable positive committed build time"
                    % source_item_id,
                )

        # Derive the legacy envelope (design D2/D4): the command, every one of
        # its arguments, and the neutral resource vector are the module's, never
        # the client's.
        try:
            if action == construction_envelope.ACTION_START:
                assert duration is not None
                envelope_payload = construction_envelope.build_envelope_start(
                    item_index=item_index, duration=duration
                )
            elif action == construction_envelope.ACTION_CLICK:
                envelope_payload = construction_envelope.build_envelope_click(
                    item_index=item_index
                )
            else:
                envelope_payload = construction_envelope.build_envelope_finish(
                    item_index=item_index
                )
        except construction_envelope.EnvelopeError as failure:
            if failure.code == "invalid_duration":
                # A server-side derivation failure: committed content
                # produced a duration this contract must never send.
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result —
        # which is precisely why it is NOT taken as proof of a construction.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the per-action post-condition from the persisted save
        # (design D3).  A construction action must never destroy the row, and
        # each action has an exactly checkable post-condition: a start records
        # the derived countdown, a click raises the counter to at least one,
        # and a completion consumes it.  Any other outcome — including a
        # surviving row the action never touched — is reported, not claimed.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            updated = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(updated, list) or len(updated) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field placement row",
            )
        updated_row = list(updated)
        attr = updated_row[6]
        if not isinstance(attr, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d carries no attribute bag after execution"
                % item_index,
            )
        if action == construction_envelope.ACTION_START:
            assert duration is not None
            if attr.get("cp") != duration:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d records countdown %r after execution, "
                    "not the derived build time %r"
                    % (item_index, attr.get("cp"), duration),
                )
        elif action == construction_envelope.ACTION_CLICK:
            clicks = attr.get("nc")
            if not construction_envelope.is_strict_int(clicks) or clicks < 1:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d records click counter %r after "
                    "execution, not an integer of at least 1"
                    % (item_index, clicks),
                )
        else:
            if "nc" in attr:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d still carries the click counter %r "
                    "after a completion"
                    % (item_index, attr.get("nc")),
                )
        return (
            envelope(
                boot,
                result="success",
                previous=previous_row,
                row=updated_row,
                action=action,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/collect")
    def v0_collect() -> Tuple[Dict[str, Any], int]:
        """Execute one collection intent through the unchanged legacy path.

        One call carries **exactly one** legacy ``collect`` command, whose
        single argument is the addressed placement's legacy map index
        (``command.py:136-147``).  That branch writes **only**
        ``item[3] = time_now``; the income travels in the client-sent 8-slot
        resource vector, which ``engine.apply_resources`` applies before the
        branch runs as ``max(current + delta, 0)`` per resource
        (``command.py:40``, ``engine.py:251-271``).  This line is therefore the
        first in the family whose derived vector is **not** neutral: the
        committed configuration describes the income, so the vector is derived
        from it and never from a client.

        Validation is structural fail-closed first, then the content and guard
        refusals, all **before** the dispatcher runs (design D1-D6): a JSON
        object body, a resolvable save, an integer item index that names a row
        in the corpus save, a row that carries no construction state, an item
        with a usable committed income and no cap, a collect type inside the
        committed vocabulary, and an elapsed time that has reached a committed
        ladder rung.  The index is resolved here rather than left to legacy
        because legacy's missing-item path (``command.py:139-142``) logs an
        error and returns early while the batch still persists: reporting that
        as a success would claim a state change that never happened.

        The construction-state refusal is load-bearing rather than defensive.
        ``item[3]`` is *both* a construction start instant (written by
        ``activate``) and a last-collection instant (written by ``collect``),
        and an executed-legacy probe showed ``activate(11, 3600)`` then
        ``collect(11)`` leaving ``[22, 58, 48, <collect instant>, 0, [],
        {"cp": 3600}, 1]``: the build's start instant overwritten while the
        countdown survived, silently restarting an active build's timer, with
        the legacy server answering ``{"result":"success"}``.  The delivered
        construction line reads that same field as a build's start instant, so
        this endpoint refuses a row carrying ``cp`` or ``nc`` **before**
        executing and leaves the corpus byte-identical (design D5).

        The remaining four refusals are derived-provisional and refuse rather
        than guess: a non-zero committed ``max_collects`` is never interpreted
        (only ``0`` is implemented), a ``collect_type`` outside the committed
        five is never coerced into an assumed resource, a committed amount of
        ``0`` (727 of 778 stored items) is not an income, and an elapsed time
        that reached no committed rung (``COLLECT_MINUTES[0] = 5``) must not
        have a payout invented for it.  No legacy branch reads any of the
        content behind these rules, so every one of them is marked
        derived-provisional wherever it is recorded; authoritative validation
        belongs to Server v1 (M13).

        Nothing but the save id and the index enters the contract: no amount,
        resource, tier, time, price, or resource delta is accepted from a
        client — the extra keys are ignored, so no client value can influence
        the payout.  Legacy performs no ownership, state, or gameplay
        validation of any kind, so the endpoint's own validation is structural
        fail-closed only.

        After execution the endpoint proves the post-state in **two** ways
        (design D8) and fails closed with ``internal_error`` on any other
        outcome: the row still exists, is an eight-field list, and its recorded
        collection instant moved **strictly forward**; **and** every stored
        resource changed by **exactly** the derived delta.  The value-level
        check is what turns a reduced or diverging payout — including one a
        clamp would have shortened — into a reported failure instead of a
        trusted success, and the pre-execution ``resources`` are read before
        dispatch so the comparison starts from the state the batch actually saw.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not collect_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            previous = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(previous, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # Copies: the legacy dispatcher mutates this very row **in place** —
        # ``collect`` writes ``item[3]`` — so a shallow list copy would still
        # alias the live list and the "before" row would report the
        # after-state.  The **length is checked before any field is indexed**,
        # so a row that is not an eight-field entry is reported rather than
        # raising an IndexError out of the route.
        if len(previous) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        previous_row = list(previous)
        if isinstance(previous_row[6], dict):
            previous_row[6] = dict(previous_row[6])
        if isinstance(previous_row[5], list):
            previous_row[5] = list(previous_row[5])
        source_item_id = previous_row[0]
        if not collect_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to collect",
            )
        collection_instant = previous_row[3]
        if not collect_envelope.is_strict_int(collection_instant):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer collection instant",
            )

        # Design D5: refuse a row carrying construction state before anything
        # else can be derived.  A countdown (``cp``) or a build-click counter
        # (``nc``) means ``item[3]`` is a construction start instant, and
        # executing ``collect`` here would overwrite it while the countdown
        # survived — silently restarting an active build's timer, which the
        # legacy server nonetheless reports as a success.
        attr = previous_row[6]
        if isinstance(attr, dict):
            for key in ("cp", "nc"):
                if key in attr:
                    return error_response(
                        409,
                        ERROR_CONSTRUCTION_IN_PROGRESS,
                        "the placement at index %d is under construction "
                        "(attr['%s'] = %r); collecting it would overwrite the "
                        "build's start instant" % (item_index, key, attr[key]),
                    )
        elif attr not in ({}, None):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no readable attribute bag",
            )

        # The pre-execution resources are read **before** dispatch so the
        # value-level post-execution proof compares against the state the batch
        # actually started from (design D8).
        try:
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # The four income fields come from the item's committed content, never
        # from a client.  ``None`` means the committed content cannot describe
        # them, and each of the three refusals answers before the dispatcher
        # runs (design D4/D6).
        try:
            amount = boot.item_collect_amount(source_item_id)
            resource_type = boot.item_collect_type(source_item_id)
            experience = boot.item_collect_xp(source_item_id)
            cap = boot.item_max_collects(source_item_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if amount is None or amount <= 0:
            return error_response(
                409,
                ERROR_NO_INCOME,
                "item %d records no committed collection income" % source_item_id,
            )
        if cap is None or cap != 0:
            return error_response(
                409,
                ERROR_CAPPED_COLLECTION,
                "item %d records a committed collection cap of %r, and this "
                "service implements only the uncapped 0" % (source_item_id, cap),
            )
        if resource_type is None or (
            isinstance(resource_type, str)
            and resource_type not in collect_envelope.COLLECT_RESOURCE_SLOTS
        ):
            return error_response(
                409,
                ERROR_UNKNOWN_COLLECT_TYPE,
                "item %d records collect_type %r, which is not one of %s"
                % (
                    source_item_id,
                    resource_type,
                    sorted(collect_envelope.COLLECT_RESOURCE_SLOTS),
                ),
            )

        # The elapsed time is measured against this service's own clock, never
        # a client value, and never extrapolated past the top rung (design D1).
        reference_time = boot.server_time()
        ladder = boot.collect_ladder()
        if ladder is None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed collection ladder does not resolve",
            )
        try:
            elapsed = reference_time - collection_instant
            tier = collect_envelope.tier_for(elapsed, ladder)
        except collect_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, failure.code)
        # Design D3: below the first committed rung no amount is invented.
        if tier is None:
            first_rung_seconds = collect_envelope.threshold_seconds_for(0, ladder)
            return error_response(
                409,
                ERROR_TOO_EARLY,
                "the placement at index %d has been collecting for %d seconds, "
                "which reaches no committed ladder rung (the first waits %d "
                "seconds, committed as %d minutes)"
                % (item_index, elapsed, first_rung_seconds, ladder[0][0]),
            )

        # Derive the legacy envelope (design D1/D2/D6): the command, its single
        # argument, and the content-derived payout are the module's, never the
        # client's.
        try:
            payout = collect_envelope.payout_for(
                amount=amount,
                resource_type=resource_type,
                experience=experience,
                tier=tier,
                ladder=ladder,
            )
            envelope_payload = collect_envelope.build_envelope(
                item_index=item_index, vector=payout
            )
        except collect_envelope.EnvelopeError as failure:
            if failure.code == "unknown_collect_type":
                return error_response(409, failure.code, str(failure))
            if failure.code == "invalid_vector":
                # A server-side derivation failure: the committed content
                # produced a vector this contract must never send.
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command() returns
        # without raising, so reaching here IS the legacy result — which is
        # precisely why it is NOT taken as proof that the payout landed.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D8).  A collection must never destroy a
        # row and must re-stamp its collection instant **forward**; the
        # reported value is legacy's own wall clock, so the comparison is
        # structural and never by value.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            updated = boot.map_item(user_id, item_index)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(updated, list) or len(updated) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field placement row",
            )
        updated_row = list(updated)
        new_instant = updated_row[3]
        if not collect_envelope.is_strict_int(new_instant):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d records a non-integer collection instant "
                "%r after execution" % (item_index, new_instant),
            )
        if new_instant <= collection_instant:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d records collection instant %r after "
                "execution, which does not move strictly forward from %r"
                % (item_index, new_instant, collection_instant),
            )
        # The value-level half of the proof: every stored resource must have
        # moved by **exactly** the derived delta.  A clamp that reduced a
        # payout, a partial application, or any other divergence is reported
        # here rather than returned as a success.
        payout_by_name = {
            "xp": payout[collect_envelope.EXPERIENCE_SLOT],
            "gold": payout[2],
            "wood": payout[3],
            "oil": payout[4],
            "steel": payout[5],
            "cash": payout[6],
            "mana": payout[7],
        }
        for name in sorted(payout_by_name):
            expected = max(resources_before[name] + payout_by_name[name], 0)
            if resources_after[name] != expected:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the derived %r "
                    "(it was %r, the derived delta is %r)"
                    % (
                        name,
                        resources_after[name],
                        expected,
                        resources_before[name],
                        payout_by_name[name],
                    ),
                )
        return (
            envelope(
                boot,
                result="success",
                previous=previous_row,
                row=updated_row,
                payout=payout,
                tier=tier,
                reference_time=reference_time,
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/expand")
    def v0_expand() -> Tuple[Dict[str, Any], int]:
        """Execute one expansion intent through the unchanged legacy path.

        One call carries **exactly one** legacy ``expand`` command, whose single
        argument is the expansion id the client addressed
        (``command.py:211-216``).  That branch writes **only**
        ``map["expansions"] += [int(expansion)]``; the price travels in the
        client-sent 8-slot resource vector, which ``engine.apply_resources``
        applies before the branch runs as ``max(current + delta, 0)`` per
        resource (``command.py:40``, ``engine.py:251-271``).  This line is the
        second in the family whose derived vector is **not** neutral, and the
        first whose vector is a **debit** — so the vector is derived from
        committed content and never from a client.

        Validation is structural fail-closed first, then the two guards and the
        two content refusals, all **before** the dispatcher runs (design
        D1/D3/D6): a JSON object body, a resolvable save, an integer expansion
        id, an id the committed ``expansion_prices`` schedule prices, an id the
        player's own ledger does not already contain, a row recording no
        positive ``neighbors`` / ``inventory_qte`` requirement, and a balance
        that covers the derived debit.

        The range and duplicate guards are **required, not defensive**.  The
        legacy server does neither: an executed-legacy probe had ``expand(999)``
        (an id the schedule does not price), a duplicate ``expand(35)``, and
        ``expand(-1)`` all answer ``{"result":"success"}``, and no branch reads,
        validates, prices, orders, or deduplicates ``map["expansions"]`` at all.
        So this contract refuses the two things the server lets through and
        that would corrupt the only ledger it maintains, before the dispatcher
        ever runs.

        The requirements refusal is **refusal, not omission**.  The server
        ignores both fields and nothing the delivered stack can read evaluates
        either: no neighbour count and no inventory quantity is exposed by the
        bootstrap, the client's ``GameApi``, or the corpus.  The consequence is
        stated rather than worked around — every id the corpus owns records
        ``neighbors 15`` / ``inventory_qte 30``, and 94 of the 98 committed
        rows record a positive requirement, so the only purchasable entries are
        the free indexes ``0..3``.

        The affordability refusal is the recorded alternative to reproducing
        the clamp (design D6).  The clamp is **reachable**: an executed-legacy
        probe had a client-sent ``-2500`` gold debit against a ``2000`` balance
        land on ``0`` rather than ``-500``.  Because the debit here is
        server-derived, the endpoint can know whether the balance covers it, and
        silently under-charging would make the post-state proof ambiguous — a
        balance that moved by less than the derived debit is indistinguishable
        from a wrong derivation.

        Nothing but the save id and the id enters the contract: no amount,
        resource, price, time, requirement flag, or resource delta is accepted
        from a client — the extra keys are ignored, so no client value can
        influence the debit.  Legacy performs no ownership, state, or gameplay
        validation of any kind, so the endpoint's own validation is structural
        fail-closed plus the two guards and two content refusals named above.

        After execution the endpoint proves the post-state in **two** ways
        (design D5) and fails closed with ``internal_error`` on any other
        outcome: the owned list grew by **exactly one** entry equal to the sent
        id **at the end**, with every existing entry unchanged and in order and
        never reordered or deduplicated; **and every** stored resource changed by
        **exactly** the derived debit.  The value-level half is what turns a
        wrong server-derived price into a reported failure instead of a trusted
        success — a derivation with the wrong sign, slot, or magnitude would
        otherwise mint or burn the wrong amount and be reported as a success —
        and the pre-execution ``resources`` are read before dispatch so the
        comparison starts from the state the batch actually saw.

        **No land, grid, cell, or placement-bound effect** is read, derived, or
        claimed (design D4); see the module docstring for the committed
        evidence that establishes the tile vocabulary and the committed scope
        statement that excludes the tile → cell geometry.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "expansion_id" not in payload:
            return error_response(
                400, ERROR_MISSING_EXPANSION_ID, "expansion_id is required"
            )
        expansion_id = payload["expansion_id"]
        if not expand_envelope.is_strict_int(expansion_id):
            # Legacy would raise int("abc") out of the branch and answer an
            # unhandled HTTP 500, so the value never reaches the dispatcher.
            return error_response(
                400, ERROR_INVALID_EXPANSION_ID, "expansion_id must be an integer"
            )
        # A negative id is a structurally unresolvable value, not an
        # out-of-range one: the committed schedule's id space is
        # ``0..size-1`` and Python would otherwise resolve ``-1`` to the
        # schedule's **last** row, pricing a negative id from a positive one.
        if expansion_id < 0:
            return error_response(
                400,
                ERROR_INVALID_EXPANSION_ID,
                "expansion_id must not be negative, got %d" % expansion_id,
            )

        # Both pre-execution reads happen **before** dispatch: the owned
        # ledger, for the range / duplicate checks and the structural half of
        # the post-execution proof, and the resources, for the value-level half
        # (design D5).  ``map_expansions`` returns a copy, because the legacy
        # dispatcher appends to that very list in place.
        try:
            expansions_before = boot.map_expansions(user_id)
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        for entry in expansions_before:
            if not expand_envelope.is_strict_int(entry):
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the owned-expansions ledger carries an entry this service "
                    "cannot reason about: %r" % (entry,),
                )
        # Design D1: the id space is the committed schedule's positional index.
        # The length is the one number the range rule needs, read from the
        # loaded configuration and never from a client.
        try:
            schedule_size = boot.expansion_price_count()
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if schedule_size is None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed expansion schedule does not resolve",
            )
        if expansion_id < 0 or expansion_id >= schedule_size:
            return error_response(
                404,
                ERROR_UNKNOWN_EXPANSION_ID,
                "the committed expansion schedule has no price row for id %d "
                "(it holds %d rows, indexes 0..%d)"
                % (expansion_id, schedule_size, schedule_size - 1),
            )
        # Design D1, second guard: the legacy server neither deduplicates nor
        # orders the ledger — a duplicate expand(35) answered success in the
        # executed-legacy probe — so a repeat is refused rather than appended.
        if expansion_id in expansions_before:
            return error_response(
                409,
                ERROR_ALREADY_EXPANDED,
                "expansion %d is already in this player's owned-expansions list"
                % expansion_id,
            )

        # The committed row, verbatim and never coerced.  A row the loaded
        # configuration cannot produce (a schedule drift) is a server-side
        # derivation failure, reported rather than priced against.
        try:
            row = boot.expansion_price(expansion_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if row is None:
            # The range check above already passed, so the loaded
            # configuration genuinely cannot produce a row for an id it says it
            # holds: a server-side content failure, never a client value, and
            # never a price invented from an absent row.
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed expansion schedule holds %d rows but produced no "
                "row for id %d" % (schedule_size, expansion_id),
            )

        # Design D3: an unevaluable requirement is refused, never invented.
        try:
            unmet = expand_envelope.unmet_requirements(row)
        except expand_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, failure.code)
        if unmet:
            return error_response(
                409,
                ERROR_EXPANSION_REQUIREMENTS_UNMET,
                "expansion %d records %s requirements (%s), and nothing this "
                "service can read evaluates them"
                % (
                    expansion_id,
                    " and ".join(unmet),
                    ", ".join(
                        "%s=%r" % (field, row.get(field)) for field in unmet
                    ),
                ),
            )

        # Design D2: the debit is derived from the committed row alone.
        try:
            debit = expand_envelope.resource_vector_for(row)
        except expand_envelope.EnvelopeError as failure:
            # invalid_price / invalid_cost are server-side derivation
            # failures: the committed content produced something this contract
            # must never send, and no client value is involved.
            return error_response(500, ERROR_INTERNAL, failure.code)

        # Design D6: refuse an unaffordable balance rather than reproduce the
        # clamp.  A named slot whose balance plus its (negative) debit would
        # fall below zero is refused, because legacy's max(..., 0) would
        # under-charge silently and the value-level proof could then no longer
        # distinguish a short charge from a wrong derivation.
        slot_of = {"gold": expand_envelope.GOLD_SLOT, "cash": expand_envelope.CASH_SLOT}
        for name in sorted(slot_of):
            delta = debit[slot_of[name]]
            if delta == 0:
                continue
            if resources_before[name] + delta < 0:
                return error_response(
                    409,
                    ERROR_INSUFFICIENT_RESOURCES,
                    "expansion %d costs %d %s and this player holds %d; the "
                    "derived debit would leave a negative balance"
                    % (expansion_id, -delta, name, resources_before[name]),
                )

        # Derive the legacy envelope (design D1/D2): the command, its single
        # argument, and the content-derived debit are the module's, never the
        # client's.
        try:
            envelope_payload = expand_envelope.build_envelope(
                expansion_id=expansion_id, vector=debit
            )
        except expand_envelope.EnvelopeError as failure:
            if failure.code in ("invalid_price", "invalid_cost", "invalid_vector"):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command() returns
        # without raising, so reaching here IS the legacy result — which is
        # precisely why it is NOT taken as proof that the right id was appended
        # and the right amount was charged.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D5).  Part one: the owned list grew by
        # exactly one entry, equal to the sent id, at the end, with every
        # existing entry unchanged and in order.  Legacy's branch is an
        # append, so anything else is a ledger corruption.
        try:
            expansions_after = boot.map_expansions(user_id)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        expected_list = list(expansions_before) + [expansion_id]
        if expansions_after != expected_list:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the owned-expansions list is %r after execution, not the "
                "documented %r (the sent id %d appended once, at the end, with "
                "every existing entry unchanged and in order)"
                % (expansions_after, expected_list, expansion_id),
            )
        # Part two: every stored resource changed by **exactly** the derived
        # debit.  The affordability refusal above makes the clamp a no-op, so
        # the exact sum is unambiguous.
        debit_by_name = {
            "xp": debit[1],
            "gold": debit[expand_envelope.GOLD_SLOT],
            "wood": debit[3],
            "oil": debit[4],
            "steel": debit[5],
            "cash": debit[expand_envelope.CASH_SLOT],
            "mana": debit[7],
        }
        for name in sorted(debit_by_name):
            expected = resources_before[name] + debit_by_name[name]
            if resources_after[name] != expected:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the derived %r "
                    "(it was %r, the derived debit is %r)"
                    % (
                        name,
                        resources_after[name],
                        expected,
                        resources_before[name],
                        debit_by_name[name],
                    ),
                )
        return (
            envelope(
                boot,
                result="success",
                expansions_before=list(expansions_before),
                expansions_after=list(expansions_after),
                debit=debit,
                price=dict(row) if hasattr(row, "items") else row,
                resources=resources_after,
            ),
            200,
        )

    @app.errorhandler(400)
    def on_bad_request(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(400, ERROR_BAD_REQUEST, "malformed request")

    @app.errorhandler(404)
    def on_not_found(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(404, ERROR_NOT_FOUND, "unknown endpoint")

    @app.errorhandler(405)
    def on_method_not_allowed(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(405, ERROR_METHOD_NOT_ALLOWED, "method not allowed")

    @app.errorhandler(500)
    def on_internal_error(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(500, ERROR_INTERNAL, "internal server error")

    @app.post("/v0/queue")
    def v0_queue() -> Tuple[Dict[str, Any], int]:
        """Execute one production-queue intent through the unchanged legacy path.

        One call carries **exactly one** of the two legacy queue commands, chosen
        by the **closed** action vocabulary (design D2): ``"push"`` derives
        ``push_queue_unit`` and ``"pop"`` derives ``pop_queue_unit``.  Each takes
        **only** the legacy map index (``command.py:676-708``), so the intent
        carries a save identity and a target key and nothing else.

        Validation is structural fail-closed, and every failure below returns
        **before** the legacy dispatcher runs, so the corpus is byte-identical on
        every error path: a JSON object body, a resolvable save, an integer
        ``map_key`` that names a row in the corpus save, an ``action`` inside the
        closed set, a readable eight-field row with an object attribute bag, and
        a derivable count.  The key is resolved here rather than left to legacy
        because legacy's missing-item path (``command.py:680-682``,
        ``702-704``) logs an error and returns early **while the batch still
        persists** — reporting that as a success would claim a queue change that
        never happened.

        **Design D1/D2 — no readiness and no completion.**  Every occurrence of
        ``attr["ts"]`` in the legacy source is a write or a deletion, and no
        command completes a queue, so there is no server-side completion rule to
        reproduce: this route computes **no** readiness, **no** remaining time,
        **no** progress ratio, and **no** completion, and it materialises no unit
        from a queue.  The absence is a recorded property of the legacy contract,
        not a missing feature.

        **Design D5 — no producer, duration, level, or count rule.**  The three
        queue branches validate nothing: not that the item is a training
        producer, not ``training_time``, not ``min_level``, and not a bound on
        the count.  None of those is added here, and in particular **no maximum
        count is applied** — the engine sets none, and an invented cap would be a
        rule the legacy server does not have.

        **Design D4 — a neutral vector and a two-part proof.**  A queue's cost
        would be a **client-sent** delta, because ``do_command`` applies the
        request's vector before the branch (``command.py:40``,
        ``engine.py:251-271``), so the derived vector is neutral and the second
        proof half requires that **every** stored resource be **unchanged**.  The
        first half requires the persisted ``attr`` bag to match the **derived**
        result for the action — the exact count, the three-key teardown, the
        inert no-op on a row whose count is absent, and every key the branch does
        not own compared by value.  The start instant is compared by **shape**
        (a strict integer, not earlier than the pre-execution one) because the
        branch stamps the wall clock and its value is not derivable;
        ``engine.timestamp_now`` has one-second resolution, so two commands
        inside one second legitimately stamp the same value.

        **Design D6 — the atom-fusion speedup is recorded and not implemented.**
        ``push_queue_unit2`` is not in the closed set because its unit id is a
        client-supplied argument no evidence constrains, and
        ``soulmixer_speedup`` has no action here at all: the legacy branch needs
        ``ts`` **and** ``ui``, raises ``KeyError`` without them, reads the
        duration from the queued unit, charges nothing, and its own author
        labelled the formula *"quite useless"*.  No cost, no timer, and no
        speedup is offered.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "map_key" not in payload:
            return error_response(400, ERROR_MISSING_MAP_KEY, "map_key is required")
        map_key = payload["map_key"]
        if not queue_envelope.is_strict_int(map_key):
            return error_response(
                400, ERROR_INVALID_MAP_KEY, "map_key must be an integer"
            )

        if "action" not in payload:
            return error_response(400, ERROR_MISSING_ACTION, "action is required")
        action = payload["action"]
        if not queue_envelope.is_action(action):
            return error_response(
                400,
                ERROR_INVALID_ACTION,
                "action must be one of %s"
                % ", ".join(sorted(queue_envelope.ACTIONS)),
            )

        # Resolve the key against the corpus before deriving, and read the
        # eight-field row while it is still there: a key that names no row must
        # fail closed rather than reach legacy's silent early return, and the row
        # the client addressed is the row the two commands mutate in place.
        try:
            known = boot.has_map_item(user_id, map_key)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_MAP_KEY,
                "no placement with key %d in this save's map" % map_key,
            )
        try:
            previous = boot.map_item(user_id, map_key)
            previous_attr = boot.map_item_attr(user_id, map_key)
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(previous, list) or len(previous) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        # Copies: the legacy dispatcher mutates this very row **in place** — both
        # helpers write or delete keys of the row's own attribute bag — so a
        # shallow list copy would still alias the live bag and the "before" row
        # would report the after-state.  The bag and the stored-unit payload are
        # copied too.
        previous_row = list(previous)
        if isinstance(previous_row[6], dict):
            previous_row[6] = dict(previous_row[6])
        if isinstance(previous_row[5], list):
            previous_row[5] = list(previous_row[5])

        # The derived post-execution bag, computed BEFORE dispatch and against a
        # copy of the live bag, so the derivation cannot be influenced by what
        # execution writes.
        try:
            queue_envelope.derived_queue(previous_attr, action)
        except queue_envelope.EnvelopeError as failure:
            if failure.code == "invalid_action":
                return error_response(400, failure.code, str(failure))
            # invalid_attr is a server-side shape failure: the addressed row's
            # bag or count is unreadable, never a client value.
            return error_response(500, ERROR_INVALID_ATTR, str(failure))

        # Derive the legacy envelope (design D2/D4): the command, its single
        # argument, and the neutral resource vector are the module's, never the
        # client's.  The contract carries no cost, duration, count, readiness, or
        # outcome: the extra keys are ignored so a client value can never win.
        try:
            envelope_payload = queue_envelope.build_envelope(
                map_key=map_key, action=action
            )
        except queue_envelope.EnvelopeError as failure:
            if failure.code in ("invalid_vector", "invalid_timestamp"):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy HTTP
        # route returns {"result": "success"} whenever command() returns without
        # raising, so reaching here IS the legacy result — which is precisely why
        # it is NOT taken as proof of a queue effect.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D4).  Part one: the persisted attribute bag
        # matches the DERIVED result for the action.  Part two: every stored
        # resource is unchanged, which is the neutral vector's own guarantee and
        # what forecloses a smuggled vector.  Either half failing is a reported
        # failure, not a success.
        try:
            still_present = boot.has_map_item(user_id, map_key)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            updated = boot.map_item(user_id, map_key)
            after_attr = boot.map_item_attr(user_id, map_key)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(updated, list) or len(updated) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field placement row",
            )
        updated_row = list(updated)
        divergence = queue_envelope.expected_attr(previous_attr, action, after_attr)
        if divergence is not None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at key %d does not carry the derived queue result: %s"
                % (map_key, divergence),
            )
        for name in sorted(resources_after):
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution "
                    "%r: a queue moves no resource, so the derived neutral "
                    "vector requires every stored resource to be unchanged"
                    % (name, resources_after[name], resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                action=action,
                map_key=map_key,
                previous=previous_row,
                row=updated_row,
                queue=queue_envelope.project_queue(after_attr),
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/collection")
    def v0_collection() -> Tuple[Dict[str, Any], int]:
        """Execute one collection completion through the unchanged legacy path.

        One call carries **exactly one** legacy ``complete_collection`` command
        (``command.py:504-523``), and the request body carries **only** a save
        identity and a collection id.  **No prize, item id, quantity, price, or
        resource delta is accepted** (design D1): the grant is looked up in the
        loaded configuration's committed ``collections`` table through
        ``get_collection_prize`` (``get_game_config.py:170-175``), so the server
        decides what a caller receives and a client-supplied expectation can
        never become the endpoint's own proof.  Any such key is ignored — the
        same intent-only discipline the collect, expand, and level-up routes use
        for amounts and prices.

        **The core decision, D1 — the grant is content-derived.**  This is the
        first route whose payload is *fully* committed, and that is what makes
        its post-execution proof non-tautological: the proof compares the
        persisted storage against the **committed** prize bag, not against
        anything the client sent.

        Validation is structural fail-closed, and every failure below returns
        **before** the legacy dispatcher runs, so the corpus is byte-identical on
        every error path: a JSON object body, a resolvable save, a **strict
        integer** collection id, and an id the committed table resolves.  The
        resolvability check is load-bearing rather than defensive — for an
        out-of-range id ``get_collection_prize`` returns ``None`` and the
        branch's very next statement (``for key in prize``) raises ``TypeError``,
        so reporting success would claim a grant that never happened.

        **The one-based index and its alias (design D3).**  The id selects the
        table positionally through ``max(0, collection - 1)``.  The clamp is
        reported rather than absorbed: **collection id 0 and collection id 1
        resolve to the same committed prize**, as does every negative id.  The
        response carries the resolved index, whether the clamp moved it, and the
        id an aliased id resolves to, so no caller can present an aliased id as a
        distinct collection.

        **Design D2 — no eligibility check, and none added.**  Nothing in the
        legacy source verifies that a collection was earned: the committed
        ``item_ids`` requirement list is read by no branch at all, and the
        ledger is read only to decide whether to append.  So a caller may name
        **any** of the ten committed collections, and this route adds no check —
        that would invent a rule the legacy server does not have, and
        authoritative validation belongs to a later server-authoritative
        milestone.  What a caller *cannot* do is choose the contents.

        **Design D1/D5 — a neutral vector and a two-part proof.**  A completion
        has no committed price, and any cost would be a **client-sent** delta
        because ``do_command`` applies the request's vector before the branch
        (``command.py:40``, ``engine.py:251-271``), so the derived vector is
        neutral.  The proof then has two value-level halves against the
        **committed** bag: part one, the granted id **and quantity** equal the
        committed prize exactly and no other stored key moved; part two, the
        collection ledger matches the derived one — **exactly one appended id**
        when the id was absent, or **nothing appended** when it was already there
        (``command.py:517-518`` is an append-if-absent, so the ledger is
        idempotent while the grant is not).  Either half failing is a reported
        failure, not a success.

        **Design D5 — no unit income, no cap semantics, no experience.**  The
        ``collect`` command is field-agnostic (it re-stamps slot 3 and does
        nothing else), no collect field has a legacy consumer, 0 of 429 units
        record a positive ``collect``, and ``max_collects`` is 0 on every unit —
        so nothing here pays out, caps, or awards experience.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "collection_id" not in payload:
            return error_response(
                400, ERROR_MISSING_COLLECTION_ID, "collection_id is required"
            )
        collection_id = payload["collection_id"]
        if not collection_envelope.is_strict_int(collection_id):
            return error_response(
                400,
                ERROR_INVALID_COLLECTION_ID,
                "collection_id must be an integer",
            )

        # The committed table, and the read-only projection of the named id.  The
        # projection is the ONLY source of the grant: no prize key is read from
        # the request, so a client-supplied prize/item/quantity cannot win.
        table = boot.collection_table()
        if table is None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the loaded legacy configuration carries no collections table",
            )
        try:
            projected = collection_envelope.project_prize(table, collection_id)
        except collection_envelope.EnvelopeError as failure:
            # A content-side shape failure (the table is not a list), never a
            # client value.
            return error_response(500, ERROR_INTERNAL, failure.code)
        if not bool(projected.get("ok", False)):
            code = str(projected.get("reason", ""))
            if code == collection_envelope.REASON_INVALID_COLLECTION_ID:
                return error_response(
                    400, ERROR_INVALID_COLLECTION_ID, str(projected.get("error", ""))
                )
            if code == collection_envelope.REASON_INVALID_PRIZE:
                return error_response(
                    500, ERROR_INTERNAL, str(projected.get("error", ""))
                )
            return error_response(
                409,
                ERROR_UNKNOWN_COLLECTION_ID,
                str(projected.get("error", "")),
            )

        # The pre-execution storage and ledger.  Both accessors return copies, so
        # the legacy dispatcher's in-place writes cannot reach them.
        try:
            store_before = dict(boot.map_store(user_id))
            ledger_before = boot.private_collections(user_id)
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Derive the legacy envelope (design D1/D5): the command, the collection
        # id, the print-only `bought` flag, and the neutral resource vector are
        # the module's, never the client's.
        try:
            envelope_payload = collection_envelope.build_envelope(
                collection_id=collection_id
            )
        except collection_envelope.EnvelopeError as failure:
            if failure.code in ("invalid_vector", "invalid_timestamp"):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy HTTP
        # route returns {"result": "success"} whenever command() returns without
        # raising, so reaching here IS the legacy result — which is precisely why
        # it is NOT taken as proof that the right item was granted.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D1).  Both halves are value comparisons
        # against the COMMITTED bag; either half failing is a reported failure.
        try:
            store_after = dict(boot.map_store(user_id))
            ledger_after = boot.private_collections(user_id)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        divergence = collection_envelope.expected_grant(
            store_before,
            store_after,
            projected["prize"],
            collection_id=collection_id,
            before_ledger=ledger_before,
            after_ledger=ledger_after,
        )
        if divergence is not None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the completion did not carry the committed grant: %s" % divergence,
            )
        try:
            derived_ledger = collection_envelope.expected_ledger(
                ledger_before, collection_id
            )
        except collection_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, failure.code)
        for name in sorted(resources_after):
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution %r: "
                    "a completion moves no resource, so the derived neutral "
                    "vector requires every stored resource to be unchanged"
                    % (name, resources_after[name], resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                collection_id=int(collection_id),
                grant={
                    "command": collection_envelope.COMPLETE_COMMAND,
                    "item_id": str(projected["entries"][0]["item_id"]),
                    "quantity": int(projected["entries"][0]["quantity"]),
                    "item_count": int(projected["item_count"]),
                    "quantity_total": int(projected["quantity_total"]),
                    "derived_from": "the committed collections table: the "
                        "service looks up what the named collection grants and "
                        "accepts no prize, item id, or quantity from the client",
                },
                prize={
                    "name": str(projected["name"]),
                    "id_column": str(projected["id_column"]),
                    "bag": dict(projected["prize"]),
                    "entries": [dict(entry) for entry in projected["entries"]],
                },
                index={
                    "base": "one-based",
                    "derivation_status": "derived-provisional",
                    "rejected_alternative": "zero-based",
                    "rule": collection_envelope.INDEX_RULE,
                    "alias_rule": collection_envelope.ALIAS_RULE,
                    "requested": int(projected["requested_index"]),
                    "resolved": int(projected["index"]),
                    "clamped": bool(projected["clamped"]),
                    "aliased": bool(projected["aliased"]),
                    "alias_of": (
                        int(projected["alias_of"])
                        if projected["alias_of"] is not None
                        else None
                    ),
                },
                eligibility={
                    "checked": False,
                    "rule": collection_envelope.NO_ELIGIBILITY_CHECK,
                },
                store_before=store_before,
                store_after=store_after,
                ledger_before=list(ledger_before),
                ledger_after=list(ledger_after),
                ledger_appended=bool(derived_ledger["appended"]),
                refusals=[dict(entry) for entry in collection_envelope.REFUSALS],
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/resurrect")
    def v0_resurrect() -> Tuple[Dict[str, Any], int]:
        """Execute one revival intent through the unchanged legacy path.

        One call carries **exactly one** legacy ``resurrect_hero`` command
        (``command.py:625-635``), and the request body carries **only** a save
        identity and a cell.  **No map key, item id, syringe count, price, or
        resource delta is accepted** (design D2): the service derives the map
        key from the addressed cell's own placement row and the item id from the
        player's own recorded ledger, so a client-supplied expectation can never
        become the endpoint's own proof.  Every such key is ignored, exactly as a
        client amount or price is ignored on the collect, expand, level-up, and
        collection routes.

        **Design D1/D2 — a mechanism, and a derived target.**  This is the first
        M8 surface whose transaction is both server-derived and state-mutating
        since ``collection``, and the first committed field in this project
        whose legacy consumer is a mutation of private state.  The cell chooses
        *where* the revival lands and the ledger chooses *what* is revived;
        both readings are recorded, and the rejected alternative is retained in
        ``projection.rejected_resolution``.

        **Both gates are evaluated here and only these two**: the dying row's
        player team (``engine.py:151``) and the committed
        ``resurrectable > 0`` (``engine.py:159,162``).  No third is invented —
        the delta's "derive no further eligibility" made structural.  The gate
        is applied to the *ledger entry's* item rather than to a row, because
        the revived row is not on the map; that is the recorded consequence of
        deriving the item id from the ledger, and it is why the response reports
        the resolved entry's own committed flag beside it.

        **Design D3 — no syringe cost, and a neutral vector.**  ``used_syringe``
        is read from ``args[4]`` and **discarded** (``command.py:630``), and the
        committed ``syringes`` field it would be paid in has zero legacy
        consumers, so the derivation sends a literal ``0`` and the response
        never echoes the discarded argument.  Because legacy applies the
        request's own vector *before* the branch (``command.py:40``), the only
        honest vector is neutral and the proof's second half proves that **every**
        stored resource is unchanged.

        **Design D5 — the revived placement is not validated.**  The legacy
        branch re-places the row through ``engine.map_add_item`` with no
        occupancy, bounds, type, or terrain check, and this route reproduces
        that absence rather than filling it.  The one bounds notion present
        (``0..99``) is the shared anchor range the other delivered routes already
        apply for structural safety, and it is recorded as such rather than as a
        gameplay claim.

        The two-part post-execution proof fails closed with ``internal_error``
        on any other outcome: the ledger entry is **gone** after a revival that
        reached zero, the addressed key's row now records the **derived** item
        id, and **every** stored resource is **unchanged**.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        # The request carries a cell and NOTHING else.  An absent coordinate is
        # a 400 with its own code so a missing key is never confused with a
        # present-but-unusable one.
        for axis in ("x", "y"):
            if axis not in payload:
                return error_response(
                    400, ERROR_MISSING_CELL, "%s is required" % axis
                )
        cell_x = payload["x"]
        cell_y = payload["y"]

        # The pre-execution snapshots.  ``map_items`` returns the live dict and
        # ``save_document`` the live save, so BOTH are deep-copied here: the
        # legacy dispatcher's writes are in place, and a before-snapshot that
        # aliased them would report the after-state as the before-state.
        try:
            items_before = {
                str(key): list(value)  # type: ignore[call-overload]
                for key, value in boot.map_items(user_id).items()
            }
            save_before = boot.save_document(user_id)
            private_before = save_before.get("privateState")
            ledger_before = (
                None
                if not isinstance(private_before, dict)
                else private_before.get(behavior_envelope.LEDGER_KEY)
            )
            ledger_snapshot = (
                None if ledger_before is None else dict(ledger_before)
            )
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # The derivation (design D1/D2).  Everything below — the cell
        # resolution, the ledger resolution, both gates, and the delete-at-zero
        # decrement — lives in behavior_envelope, so the endpoint, the offline
        # tests, and the report all compare against ONE derivation.
        projection = behavior_envelope.project_resurrection(
            items_before, ledger_before, cell_x, cell_y,
            lambda item_id: _committed_item(boot, item_id),
        )
        target = projection["projection"]  # type: ignore[index]
        if not bool(target.get("ok", False)):
            reason = str(target.get("reason", ""))  # type: ignore[union-attr]
            messages = {
                behavior_envelope.REASON_INVALID_CELL: (400, ERROR_MISSING_CELL
                    if "x" not in payload or "y" not in payload
                    else ERROR_INVALID_CELL),
                behavior_envelope.REASON_UNRESOLVABLE_CELL: (
                    409, ERROR_UNRESOLVABLE_CELL),
                behavior_envelope.REASON_AMBIGUOUS_CELL: (409, ERROR_AMBIGUOUS_CELL),
                behavior_envelope.REASON_UNRESOLVABLE_LEDGER_ENTRY: (
                    409, ERROR_UNRESOLVABLE_LEDGER_ENTRY),
                behavior_envelope.REASON_AMBIGUOUS_LEDGER: (
                    409, ERROR_AMBIGUOUS_LEDGER),
                behavior_envelope.REASON_NOT_RESURRECTABLE: (
                    409, ERROR_NOT_RESURRECTABLE),
                behavior_envelope.REASON_INVALID_LEDGER: (500, ERROR_INTERNAL),
                behavior_envelope.REASON_INVALID_ITEM_ID: (500, ERROR_INTERNAL),
            }
            status, code = messages.get(reason, (500, ERROR_INTERNAL))
            return error_response(
                status,
                code,
                "%s (%s)" % (str(target.get("error", "")), reason),  # type: ignore[union-attr]
            )

        map_key = int(target["map_key"])  # type: ignore[index,arg-type]
        item_id = int(target["item_id"])  # type: ignore[index,arg-type]

        try:
            envelope_payload = behavior_envelope.build_envelope(
                map_key, item_id, cell_x, cell_y
            )
        except behavior_envelope.EnvelopeError as failure:
            if failure.code in ("invalid_vector", "invalid_timestamp"):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into THIS corpus only; the legacy HTTP
        # route answers {"result": "success"} whenever command() returns without
        # raising, so reaching here IS the legacy result — which is precisely why
        # it is NOT taken as proof that the right unit was revived.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D3/D5).  Three halves, all value
        # comparisons against the derivation; any of them failing is a reported
        # failure, not a success.
        try:
            items_after_raw = boot.map_items(user_id)
            save_after = boot.save_document(user_id)
            private_after = save_after.get("privateState")
            ledger_after = (
                None
                if not isinstance(private_after, dict)
                else private_after.get(behavior_envelope.LEDGER_KEY)
            )
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        divergence = behavior_envelope.ledger_divergence(
            ledger_snapshot, ledger_after, item_id
        )
        if divergence is not None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the revival did not carry the derived decrement: %s" % divergence,
            )
        derived_ledger = behavior_envelope.expected_ledger(
            ledger_snapshot, item_id
        )
        if int(derived_ledger["count_after"]) != int(  # type: ignore[index]
            projection["count_after"]  # type: ignore[index]
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the derived decrement disagrees with the projected one: %r vs %r"
                % (derived_ledger["count_after"], projection["count_after"]),  # type: ignore[index]
            )
        placement_after = items_after_raw.get(str(map_key))
        if not isinstance(placement_after, list) or len(placement_after) != (
            behavior_envelope.MAP_ROW_SLOTS
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "map key %d holds no committed row after the revival" % map_key,
            )
        if placement_after[behavior_envelope.SLOT_ITEM_ID] != item_id:
            return error_response(
                500,
                ERROR_INTERNAL,
                "map key %d records item %r after the revival, not the derived %d"
                % (
                    map_key,
                    placement_after[behavior_envelope.SLOT_ITEM_ID],
                    item_id,
                ),
            )
        if placement_after[behavior_envelope.SLOT_CELL_X] != cell_x or (
            placement_after[behavior_envelope.SLOT_CELL_Y] != cell_y
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "map key %d records cell %r after the revival, not the addressed "
                "(%r, %r)"
                % (
                    map_key,
                    (
                        placement_after[behavior_envelope.SLOT_CELL_X],
                        placement_after[behavior_envelope.SLOT_CELL_Y],
                    ),
                    cell_x,
                    cell_y,
                ),
            )
        for name in behavior_envelope.RESOURCE_NAMES:
            if name not in resources_before or name not in resources_after:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "stored resource %s is missing from one side of the proof: "
                    "the comparison covers the FULL resource set, never a subset"
                    % name,
                )
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution "
                    "%r: a revival moves no resource — no syringe cost is "
                    "charged and no resource is converted"
                    % (name, resources_after[name], resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                map_key=map_key,
                item_id=item_id,
                count_before=int(projection["count_before"]),  # type: ignore[index]
                count_after=int(derived_ledger["count_after"]),  # type: ignore[index]
                removed=bool(derived_ledger["removed"]),  # type: ignore[index]
                cell=[int(cell_x), int(cell_y)],
                occupant_item_id=target.get("occupant_item_id"),
                committed_resurrectable=target.get("committed_resurrectable"),
                committed_syringes=target.get("committed_syringes"),
                gates=behavior_envelope.gates(),
                ledger_before=(
                    []
                    if ledger_snapshot is None
                    else [
                        {"item_id": key, "count": ledger_snapshot[key]}
                        for key in sorted(ledger_snapshot, key=lambda t: int(t))
                    ]
                ),
                ledger_after=(
                    []
                    if ledger_after is None
                    else [
                        {"item_id": str(key), "count": ledger_after[key]}
                        for key in sorted(ledger_after, key=lambda t: int(t))
                    ]
                ),
                placement_before=list(items_before[str(map_key)]),
                placement_after=list(placement_after),
                syringe={
                    "charged": 0,
                    "discarded_argument": behavior_envelope.DERIVED_USED_SYRINGE,
                    "echoed": False,
                    "committed_syringes_reported_as_content_only": target.get(
                        "committed_syringes"
                    ),
                    "note": behavior_envelope.SYRINGE_DISCARD_NOTE,
                    "rule": behavior_envelope.NO_SYRINGE_COST,
                },
                resolution={
                    "rule": behavior_envelope.RESOLUTION_RULE,
                    "rejected_alternative": behavior_envelope.REJECTED_RESOLUTION,
                    "derivation_status": "derived",
                    "pairing": behavior_envelope.DERIVED_PAIRING,
                },
                clicks_to_build=behavior_envelope.CLICKS_TO_BUILD_BOUNDARY,
                refusals=behavior_envelope.refusals(),
                no_third_gate=behavior_envelope.NO_THIRD_GATE,
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/quests")
    def v0_quests() -> Tuple[Dict[str, Any], int]:
        """Execute one quest intent through the unchanged legacy path.

        One call carries **exactly one** of the six legacy quest branches
        (``command.py:68-74``, ``76-79``, ``87-117``, ``430-442``, ``745-750``,
        ``752-806``), chosen by the **closed** action vocabulary.

        **The client sends a player identifier and the branch's own addressing,
        and nothing else.**  The addressing is the branch's own subject — a goal
        index, a quest-variable key, a mission identifier, a rank index, or a
        quest identifier — and every other value is
        :mod:`quest_envelope`'s ``DERIVED_*`` constant: the progress pair, the
        quest-variable value, the rank difficulty, and the whole ``end_quest``
        blob.  Any ``progress``, ``value``, ``difficulty``, ``win``,
        ``voluntary_end``, ``duration``, ``map``, ``units``, ``lost``,
        ``reward``, ``price``, ``cost``, ``resources_changed``, ``vector``,
        ``seconds``, or ``fast_forward`` key a client attaches is **ignored**, so
        a request carrying every one of them changes nothing and the response
        echoes no ignored value.

        **Design D2 — the destruction count is REFUSED and the difference from
        the legacy server is a DIVERGENCE, not parity.**  The legacy branch
        destroys placed rows through ``map_lose_item`` (``command.py:796``) using
        a count the **client** computed, ``max(0, unit[2] - unit[3])``
        (``command.py:792``).  This route derives the blob server-side with
        ``units`` as an **empty list**, so the destruction loop
        (``command.py:790``) iterates zero times, ``map_lose_item`` is never
        reached, and every placed row is left **byte-identical** — proved over
        the **complete** ``items`` mapping, not a selected subset.  The response
        reports that as a divergence rather than as parity.

        **Design D3 — ``complete_goal`` is delivered as a no-op on purpose.**  It
        mutates nothing (it resolves the committed title, prints it, and
        returns), so the route executes the real branch and its post-execution
        proof requires the **whole** quest state to be byte-identical.  No
        completion flag, ledger, or reward exists.

        **Design D4/D5 — no bound and no membership rule is added.**
        ``set_goals`` grows the goals list on demand with **no upper bound**, so
        the endpoint reproduces that growth rather than closing it; the one
        structural refusal is a **negative** goal index, because Python would
        otherwise write ``goals[-1]``.  ``set_quest_var`` accepts **any**
        key — an invented one is persisted, as legacy does — and refuses exactly
        the one key the branch itself ignores, ``idSimpleChapter``.

        **Design D6 — a neutral vector and a two-part proof.**  No quest price
        exists: the committed ``reward`` field has **zero** legacy consumers and
        is **uniformly the value 10** on all 91 entries, so the derived vector is
        neutral.  The proof's first half requires the persisted quest state to
        match the **derived** result for the action — every field it writes, every
        field it does not, and the two wall-clock fields compared by **shape** and
        **direction** — plus every placed row byte-identical.  The second half
        requires **every** stored resource to be **unchanged**.

        **Design D7 — ``unlockedQuestIndex`` is reported and never written.**  It
        has **zero** legacy sites, so no action here touches it and the proof
        fails closed if one ever does.

        **Design D9 — no fast-forward operation is delivered.**  ``fast_forward``
        subtracts a **client-supplied** number of seconds from every quest time
        and from the last-chapter instant; it is recorded in
        ``quest_envelope.FAST_FORWARD_CONTRACT`` and exposed by **no** action and
        **no** route.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "action" not in payload:
            return error_response(400, ERROR_MISSING_ACTION, "action is required")
        action = payload["action"]
        if not quest_envelope.is_action(action):
            return error_response(
                400,
                ERROR_INVALID_ACTION,
                "action must be one of %s"
                % ", ".join(sorted(quest_envelope.ACTIONS)),
            )

        # --- the ONE value a client may name: the branch's own addressing ----
        addressing_key = quest_envelope.ACTION_ADDRESSING_KEY[str(action)]
        missing_code = ERROR_MISSING_ACTION
        invalid_code = ERROR_INVALID_ACTION
        if str(action) == quest_envelope.ACTION_SET_GOAL \
                or str(action) == quest_envelope.ACTION_COMPLETE_GOAL:
            missing_code = ERROR_MISSING_GOAL_INDEX
            invalid_code = ERROR_INVALID_GOAL_INDEX
        elif str(action) == quest_envelope.ACTION_SET_QUEST_VAR:
            missing_code = ERROR_MISSING_QUEST_VAR_KEY
            invalid_code = ERROR_INVALID_QUEST_VAR_KEY
        elif str(action) == quest_envelope.ACTION_COLLECT_MISSION:
            missing_code = ERROR_MISSING_MISSION
            invalid_code = ERROR_INVALID_MISSION
        elif str(action) == quest_envelope.ACTION_SET_QUEST_RANK:
            missing_code = ERROR_MISSING_QUEST_INDEX
            invalid_code = ERROR_INVALID_QUEST_INDEX
        else:
            missing_code = ERROR_MISSING_QUEST_ID
            invalid_code = ERROR_INVALID_QUEST_ID
        if addressing_key not in payload:
            return error_response(
                400,
                missing_code,
                "%s is required for a %s (%s)"
                % (addressing_key, action,
                   quest_envelope.ACTION_ADDRESSING[str(action)]),
            )
        addressing = payload[addressing_key]
        if str(action) == quest_envelope.ACTION_SET_QUEST_VAR:
            if str(addressing) == quest_envelope.QUEST_VAR_IGNORED_KEY:
                return error_response(
                    409,
                    ERROR_IGNORED_QUEST_VAR_KEY,
                    "the legacy set_quest_var branch explicitly IGNORES %r "
                    "(command.py:91-95), so it is refused rather than persisted: "
                    "the game's own comment explains the key is dropped to let a "
                    "player reach chapter 99"
                    % quest_envelope.QUEST_VAR_IGNORED_KEY,
                )
            if not quest_envelope.is_quest_var_key(addressing):
                return error_response(
                    400, invalid_code, "key must be a non-empty string, got %r"
                    % (addressing,),
                )
        elif str(action) in (
            quest_envelope.ACTION_SET_GOAL,
            quest_envelope.ACTION_COMPLETE_GOAL,
        ):
            if not quest_envelope.is_goal_index(addressing):
                return error_response(
                    400,
                    invalid_code,
                    "goal_index must be a non-negative integer, got %r; the goals "
                    "list grows on demand with NO upper bound, so a large index is "
                    "accepted, but a negative one would alias goals[-1] in Python "
                    "and that is refused structurally"
                    % (addressing,),
                )
        elif str(action) == quest_envelope.ACTION_COLLECT_MISSION:
            if not quest_envelope.is_mission(addressing):
                return error_response(
                    400, invalid_code,
                    "mission must be an integer, got %r" % (addressing,),
                )
        elif str(action) == quest_envelope.ACTION_SET_QUEST_RANK:
            if not quest_envelope.is_quest_rank_index(addressing):
                return error_response(
                    400, invalid_code,
                    "quest_index must be an integer, got %r" % (addressing,),
                )
        else:
            if not quest_envelope.is_quest_id(addressing):
                return error_response(
                    400, invalid_code,
                    "quest_id must be an integer, got %r" % (addressing,),
                )

        # Both pre-execution reads happen **before** dispatch.  The snapshots are
        # deep-enough COPIES, because the legacy branches mutate these very
        # containers in place: a by-reference snapshot would alias the live state
        # and report the after-state as the before-state.
        try:
            before_state = quest_envelope.snapshot_state(boot.save_document(user_id))
            items_before = copy.deepcopy(boot.map_items(user_id))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        except quest_envelope.EnvelopeError as failure:
            # A server-side state failure, never a client value: the endpoint
            # must be able to address its own state, so an unresolvable quest
            # state fails closed instead of being defaulted to zeros.
            return error_response(409, ERROR_UNRESOLVABLE_QUEST_STATE, str(failure))
        try:
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # The derived post-execution state, computed BEFORE dispatch against the
        # copied snapshot, so the derivation cannot be influenced by what
        # execution writes.
        try:
            derived = quest_envelope.derived_quest(before_state, action, addressing)
        except quest_envelope.EnvelopeError as failure:
            if failure.code == quest_envelope.REASON_INVALID_ACTION:
                return error_response(400, ERROR_INVALID_ACTION, str(failure))
            if failure.code == quest_envelope.REASON_IGNORED_KEY:
                return error_response(409, ERROR_IGNORED_QUEST_VAR_KEY, str(failure))
            if failure.code in (
                quest_envelope.REASON_INVALID_GOAL_INDEX,
                quest_envelope.REASON_INVALID_KEY,
                quest_envelope.REASON_INVALID_MISSION,
                quest_envelope.REASON_INVALID_QUEST_INDEX,
                quest_envelope.REASON_INVALID_QUEST_ID,
            ):
                return error_response(400, invalid_code, str(failure))
            return error_response(409, ERROR_UNRESOLVABLE_QUEST_STATE, str(failure))

        # Derive the legacy envelope (design D2/D6): the command, its argument
        # list, and the neutral resource vector are the module's, never the
        # client's.
        try:
            envelope_payload = quest_envelope.build_envelope(
                action=action, addressing=addressing
            )
        except quest_envelope.EnvelopeError as failure:
            if failure.code in (
                quest_envelope.REASON_INVALID_VECTOR,
                quest_envelope.REASON_INVALID_TIMESTAMP,
                quest_envelope.REASON_INVALID_PAYLOAD,
            ):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It persists
        # via legacy save_session into this corpus only; the legacy HTTP route
        # returns {"result": "success"} whenever command() returns without
        # raising, so reaching here IS the legacy result -- which is precisely
        # why it is NOT taken as proof that the right fields were written and
        # that nothing else moved.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D2/D3/D4/D6).  Part one: the persisted quest
        # state matches the DERIVED result for the action, with every untouched
        # field compared by value and the two wall-clock fields compared by shape
        # and direction; plus EVERY placed row byte-identical, which is what
        # proves the refused destruction count stayed refused.  Part two: every
        # stored resource is unchanged, which is the neutral vector's own
        # guarantee and what forecloses a smuggled vector.  Either half failing is
        # a reported failure, not a success.
        try:
            after_state = quest_envelope.snapshot_state(boot.save_document(user_id))
            items_after = boot.map_items(user_id)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        except quest_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, str(failure))
        divergence = quest_envelope.expected_state(
            before_state, str(action), addressing, after_state
        )
        if divergence is not None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the persisted quest state does not carry the derived result for a "
                "%s: %s" % (derived["action"], divergence),
            )
        if items_after != items_before:
            changed = sorted(
                set(str(key) for key in items_before) | set(str(key) for key in items_after)
            )
            moved = [
                key for key in changed
                if items_before.get(key) != items_after.get(key)
            ]
            return error_response(
                500,
                ERROR_INTERNAL,
                "placed rows changed under a %s (map keys %s): no quest branch "
                "destroys a placed row, and the client-computed destruction count "
                "is refused by contract (design D2)"
                % (derived["command"], moved),
            )
        for name in sorted(resources_after):
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution "
                    "%r: a quest action moves no resource, so the derived neutral "
                    "vector requires every stored resource to be unchanged"
                    % (name, resources_after[name], resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                action=str(action),
                addressing=derived["addressing"],
                addressing_kind=derived["addressing_kind"],
                command=derived["command"],
                derived={
                    "written": derived["written"],
                    "untouched": derived["untouched"],
                    "mutates": derived["mutates"],
                    "stamps_instant": derived["stamps_instant"],
                    "stamps_chapter": derived["stamps_chapter"],
                    "progress_pair": list(quest_envelope.DERIVED_PROGRESS),
                    "quest_var_value": quest_envelope.DERIVED_QUEST_VALUE,
                    "difficulty": quest_envelope.DERIVED_DIFFICULTY,
                    "wrapped_mission": (
                        quest_envelope.wrap_mission(addressing)
                        if str(action) == quest_envelope.ACTION_COLLECT_MISSION
                        else None
                    ),
                },
                previous=quest_envelope.project_quests(before_state),
                quests=quest_envelope.project_quests(after_state),
                quest_state=quest_envelope.copy_state(after_state),
                branches=[dict(record) for record in quest_envelope.BRANCHES],
                branch_count=quest_envelope.BRANCH_COUNT,
                writers=[dict(record) for record in quest_envelope.WRITERS],
                writer_count=quest_envelope.WRITER_COUNT,
                fast_forward_offered=False,
                reward_paid=0,
                reward_derived_from_content=False,
                unlocked_quest_index=after_state[quest_envelope.KEY_UNLOCKED_INDEX],
                unlocked_quest_index_written=False,
                destruction={
                    "status": "REFUSED",
                    "legacy_status": "DIVERGENCE, NOT PARITY",
                    "client_supplied_units_ignored": True,
                    "derived_units": 0,
                    "placed_rows_before": len(items_before),
                    "placed_rows_after": len(items_after),
                    "placed_rows_byte_identical": True,
                    "ledger_door": quest_envelope.LEDGER_DOOR,
                    "note": quest_envelope.END_QUEST_REFUSAL,
                },
                end_quest_blob=(
                    quest_envelope.end_quest_blob(addressing)
                    if str(action) == quest_envelope.ACTION_END_QUEST
                    else None
                ),
                ignored_client_keys=list(quest_envelope.IGNORED_CLIENT_KEYS),
                persisted_client_values=list(quest_envelope.PERSISTED_CLIENT_VALUES),
                refusals=[
                    {"refusal": record["refusal"], "implemented": record["implemented"]}
                    for record in quest_envelope.REFUSALS
                ],
                refused_destruction=dict(quest_envelope.REFUSED_DESTRUCTION),
                migration=dict(quest_envelope.MIGRATION),
                content_note=quest_envelope.CONTENT_RECORD_NOTE,
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/research")
    def v0_research() -> Tuple[Dict[str, Any], int]:
        """Execute one research intent through the unchanged legacy path.

        One call carries **exactly one** of the four legacy research commands
        (``command.py:268-300``), chosen by the **closed** action vocabulary
        (design D2): ``next_step`` derives ``next_research_step``,
        ``buy_step_cash`` derives ``research_buy_step_cash``, ``next_item``
        derives ``next_research_item``, and ``reset_item`` derives
        ``reset_research_item``.

        **Design D2 — the client sends a player identifier and a track, and
        nothing else.**  No counter value, no research instant, and no cash
        amount is accepted: the extra keys are **ignored**, so a request
        carrying ``step: 999``, ``timestamp: 1``, or ``cash: 2500`` changes
        nothing.  The cash branch's own argument is the module's
        :data:`research_envelope.DERIVED_CASH` (**0**), server-derived, which
        the branch then **discards** anyway.  Every counter and every instant in
        the response is therefore the service's own derivation, and the response
        echoes **no** ignored client value.

        Validation is structural fail-closed, and every failure below returns
        **before** the legacy dispatcher runs, so the corpus is byte-identical on
        every error path: a JSON object body, a resolvable save, an **action**
        inside the closed set, a **track** that is an integer the two-entry
        vector addresses, and a research vector that resolves (all three
        counters present, lists of length 2, all integers, none negative).

        **Design D6 — no bounds, membership rule, or clamp is added.**  The four
        legacy branches validate **nothing**: no bounds check, no numeric clamp,
        no membership test, no exception guard, and no existence check.  A track
        outside the vector would raise ``IndexError`` in legacy and a large track
        number would let a counter grow without limit; both are recorded as
        Server v1 / M13 gaps and neither is reproduced.  The only structural
        check here is that the route can address its own state.

        **Design D3 — a neutral vector and a two-part proof.**  A research action
        has no committed price (``research_buy_step_cash`` reads a cash value
        and charges nothing), and any price would be a **client-sent** delta
        because ``do_command`` applies the request's vector before the branch
        (``command.py:40``, ``engine.py:251-271``), so the derived vector is
        neutral.  The proof's first half requires the persisted vector to match
        the **derived** result for the action — the exact counters, the item
        branch's **paired** step-and-instant reset, the cash branch's
        instant-only zeroing, the unaddressed track byte-identical, and the
        stamped instant compared by **shape** and **direction** rather than by
        value.  The second half requires **every** stored resource to be
        **unchanged**, which is what forecloses a client minting or burning a
        balance through this path.

        **Design D1 — no readiness, completion, remaining time, or unlock.**  All
        three counters are **write-only** in the legacy source, so there is no
        server-side rule to reproduce: this route computes none of them, and the
        response's projection carries an explicitly **empty** ``derived`` block
        as the machine-readable form of that absence.

        **Design D7 — no fast-forward operation is delivered.**  The research
        instant has five writers and the fifth is ``fast_forward``, which
        subtracts a **client-supplied** number of seconds from every track.  It
        is recorded in ``research_envelope.FAST_FORWARD_CONTRACT`` and exposed by
        **no** action and **no** route.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "action" not in payload:
            return error_response(400, ERROR_MISSING_ACTION, "action is required")
        action = payload["action"]
        if not research_envelope.is_action(action):
            return error_response(
                400,
                ERROR_INVALID_ACTION,
                "action must be one of %s"
                % ", ".join(sorted(research_envelope.ACTIONS)),
            )

        if "track" not in payload:
            return error_response(400, ERROR_MISSING_TRACK, "track is required")
        track = payload["track"]
        if not research_envelope.is_track(track):
            return error_response(
                400,
                ERROR_INVALID_TRACK,
                "track must be an integer in 0..%d, got %r"
                % (research_envelope.TRACK_COUNT - 1, track),
            )

        # Both pre-execution reads happen **before** dispatch.  The snapshot is a
        # deep-enough COPY (research_envelope.copy_vector rebuilds each list),
        # because the legacy dispatcher mutates these very lists in place: a
        # by-reference snapshot would alias the live state and report the
        # after-state as the before-state.
        try:
            save_document = boot.save_document(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        try:
            before_vector = research_envelope.snapshot_counters(save_document)
        except research_envelope.EnvelopeError as failure:
            # A server-side state failure, never a client value: the endpoint
            # must be able to address its own state, so an unresolvable vector
            # fails closed instead of being defaulted to zeros.
            return error_response(409, ERROR_UNRESOLVABLE_RESEARCH_STATE,
                                  str(failure))
        try:
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # The derived post-execution vector, computed BEFORE dispatch against the
        # copied snapshot, so the derivation cannot be influenced by what
        # execution writes.
        try:
            derived = research_envelope.derived_research(
                before_vector, track, action
            )
        except research_envelope.EnvelopeError as failure:
            if failure.code == research_envelope.REASON_INVALID_ACTION:
                return error_response(400, failure.code, str(failure))
            if failure.code == research_envelope.REASON_INVALID_TRACK:
                return error_response(400, ERROR_INVALID_TRACK, str(failure))
            return error_response(409, ERROR_UNRESOLVABLE_RESEARCH_STATE,
                                  str(failure))

        # Derive the legacy envelope (design D2/D3): the command, its argument
        # list, and the neutral resource vector are the module's, never the
        # client's.
        try:
            envelope_payload = research_envelope.build_envelope(
                track=track, action=action
            )
        except research_envelope.EnvelopeError as failure:
            if failure.code in (
                research_envelope.REASON_INVALID_VECTOR,
                research_envelope.REASON_INVALID_TIMESTAMP,
                research_envelope.REASON_INVALID_CASH,
            ):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It persists
        # via legacy save_session into this corpus only; the legacy HTTP route
        # returns {"result": "success"} whenever command() returns without
        # raising, so reaching here IS the legacy result -- which is precisely
        # why it is NOT taken as proof that the right counters were written and
        # that nothing else moved.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D3).  Part one: the persisted vector matches
        # the DERIVED result for the action, with the unaddressed track and every
        # counter the branch does not own compared by value.  Part two: every
        # stored resource is unchanged, which is the neutral vector's own
        # guarantee and what forecloses a smuggled vector.  Either half failing is
        # a reported failure, not a success.
        try:
            after_vector = research_envelope.snapshot_counters(
                boot.save_document(user_id)
            )
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        except research_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, str(failure))
        divergence = research_envelope.expected_state(
            before_vector, action, track, after_vector
        )
        if divergence is not None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the persisted research vector does not carry the derived result "
                "for a %s on track %d: %s"
                % (derived["action"], derived["track"], divergence),
            )
        for name in sorted(resources_after):
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution "
                    "%r: a research action moves no resource, so the derived "
                    "neutral vector requires every stored resource to be "
                    "unchanged" % (name, resources_after[name],
                                    resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                action=action,
                track=derived["track"],
                previous=research_envelope.project_research(before_vector),
                research=research_envelope.project_research(after_vector),
                command=derived["command"],
                derived={
                    # The step and item values are always derivable; only the
                    # INSTANT is not, because the step branch stamps the wall
                    # clock (command.py:272), so that one field is reported as
                    # null and the typed shape says so.
                    "step": derived["step"],
                    "item": derived["item"],
                    "instant": None if derived["stamps_instant"]
                    else derived["instant"],
                    "stamps_instant": derived["stamps_instant"],
                    "paired_reset": derived["paired_reset"],
                    "written": derived["written"],
                    "untouched_counters": derived["untouched_counters"],
                },
                counters=after_vector,
                tracks=[record["track"] for record in research_envelope.TRACKS],
                tracks_source=[
                    {key: value for key, value in record.items()}
                    for record in research_envelope.TRACKS
                ],
                cash_charged=0,
                cash_argument_ignored=True,
                price_computed=False,
                fast_forward_offered=False,
                resources=resources_after,
            ),
            200,
        )

    @app.post("/v0/level_up")
    def v0_level_up() -> Tuple[Dict[str, Any], int]:
        """Execute one level-up intent through the unchanged legacy path.

        One call carries **exactly one** legacy ``level_up`` command, whose
        single argument is the **service-derived** target level
        (``command.py:81-85``).  That branch takes exactly one positional
        argument and writes ``map["level"] = new_level`` — one line, with **no
        range check and no experience validation** — and **nothing in the legacy
        server reads the committed ``levels`` curve**: zero references across
        ``command.py``, ``engine.py``, ``sessions.py``, ``server.py``, and
        ``constants.py``.  The curve is therefore content the client owns, and
        this contract derives the target from it rather than reading it from the
        client (design D3).

        Nothing but the save id enters the request: no level, no experience, no
        reward, no time, and no resource delta is accepted from a client — the
        extra keys are ignored, so a request carrying ``level: 99`` changes
        nothing and the legacy hole where any client could set level 99 is
        closed here.

        **Design D1 — the curve is one-based and the conversion lives in exactly
        one named function.**  Stored level *n* is ``levels[n - 1]``; every
        level this route resolves goes through
        :func:`level_envelope.entry_index_for_level`, and no other place in the
        repository indexes the curve by its own arithmetic.  The interpretation
        is **derived-provisional** and the rejected **zero-based** alternative
        is contradicted by the committed corpus: at ``xp 4`` the zero-based
        reading implies level 0 while the save records level 1.  Both facts are
        reported in the ``curve`` block, so a client mirrors them rather than
        re-deriving them.

        **Design D2 — the recorded level is unverified and a disagreement is
        reported, never smoothed.**  The legacy branch wrote it from a client
        integer, so the stored value is evidence of what a client once asked for
        and nothing else.  The derived level and the recorded level are two
        distinct facts and are never conflated: the response reports both
        (``derived_level``, ``level_before``, ``level_after``) and the two
        refusals below exist precisely so neither value is silently reconciled.

        **Design D4 — both refusals precede the dispatcher**, so the corpus is
        byte-identical on every error path: ``level_already_current`` when the
        recorded level already equals the derived level (there is nothing to do,
        and executing ``level_up`` would rewrite an identical value — **this is
        what the committed corpus does**, recording ``xp 4`` / ``level 1`` while
        the curve places level 1 at ``0``), and ``xp_below_threshold`` when the
        stored experience cannot support advancing past the recorded level.

        **Design D5 — the post-state proof is the level *and the absence of
        resource movement*.**  ``level_up`` is dispatched with a client-sent
        vector like every other command, and the derived vector is **neutral**:
        proving after execution that **every** stored resource is **unchanged**
        is what forecloses vector smuggling — a resource-minting exploit
        wearing a level-up's clothes — and is why a correct level-up cannot be
        confused with a moved balance.  Both halves fail closed with
        ``internal_error`` rather than reporting the legacy success.

        **Design D7 — nothing is tuned and no reward is paid.**  The committed
        ``exp_required`` values are used verbatim; the committed
        ``reward_type`` / ``reward_amount`` are consumed by no legacy branch, so
        they are refused rather than invented, and unit experience and the
        tutorial are out of scope.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        # Both pre-execution reads happen **before** dispatch: the recorded
        # level, for the two refusals and the structural half of the
        # post-execution proof, and the resources, for the value-level half and
        # for the stored experience the level is derived from (design D5).
        try:
            level_before = boot.map_level(user_id)
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if level_before is None:
            # The recorded level is absent or not an integer.  It is never
            # coerced into a starting point for the comparison below, because
            # coercing it would invent authority the legacy server never had.
            return error_response(
                500,
                ERROR_INTERNAL,
                "this save records no level this service can read as an integer",
            )

        # The committed curve, read from the loaded configuration through the
        # delivered accessors: the entry count first, then every entry at its
        # own **positional** index (never through the level conversion, which
        # is the envelope module's single named function).
        try:
            entry_count = boot.level_entry_count()
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if entry_count is None:
            return error_response(
                500, ERROR_INTERNAL, "the committed level curve does not resolve"
            )
        try:
            rows = [boot.level_entry(position) for position in range(entry_count)]
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        try:
            thresholds = level_envelope.thresholds_from_entries(rows)
        except level_envelope.EnvelopeError as failure:
            # A server-side content failure: the committed curve cannot supply a
            # strictly increasing ladder, so no level is derivable from it.
            return error_response(500, ERROR_INTERNAL, failure.code)

        # The curve facts the answer reports.  Every level is resolved through
        # the one named conversion.
        try:
            derived = level_envelope.derived_level_for(
                resources_before["xp"], thresholds
            )
            curve_entry = level_envelope.entry_for_level(derived, rows)
            next_position = level_envelope.entry_index_for_level(
                derived + 1, entry_count
            )
            next_threshold = level_envelope.next_threshold(
                resources_before["xp"], thresholds
            )
            remaining = level_envelope.remaining_for(
                resources_before["xp"], thresholds
            )
            recorded_threshold = level_envelope.threshold_for(
                level_before, thresholds
            )
        except level_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, failure.code)
        if derived is None:
            # The committed curve's floor sits above this player's experience,
            # so no level is derivable at all.  A content/state failure, never a
            # value this contract may round into place.
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed level curve begins at %d experience and this "
                "player has %d" % (thresholds[0], resources_before["xp"]),
            )
        if not isinstance(curve_entry, dict) or not isinstance(
            curve_entry.get("exp_required"), int
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed level curve holds no readable entry for level %d"
                % derived,
            )
        try:
            next_entry = (
                boot.level_entry(next_position)
                if next_position is not None
                else None
            )
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Design D4, first refusal: there is nothing to do.  Answering here —
        # before the dispatcher runs — is what keeps a level that already
        # equals the derived one from being rewritten as a transaction.
        if level_before == derived:
            return error_response(
                409,
                ERROR_LEVEL_ALREADY_CURRENT,
                "the recorded level is already %d, which is the level the "
                "committed curve derives for %d stored experience"
                % (derived, resources_before["xp"]),
            )
        # Design D4, second refusal, and the recorded-versus-derived
        # disagreement (design D2): the recorded level sits **above** what the
        # stored experience supports, so no advancement is derivable.  Reported
        # with both values and the threshold that separates them; never
        # reconciled, never paid for.
        if recorded_threshold is None:
            return error_response(
                409,
                ERROR_XP_BELOW_THRESHOLD,
                "the recorded level %d has no entry in the committed curve "
                "(which holds %d levels), so the stored experience %d cannot be "
                "checked against it" % (level_before, entry_count, resources_before["xp"]),
            )
        if resources_before["xp"] < recorded_threshold:
            return error_response(
                409,
                ERROR_XP_BELOW_THRESHOLD,
                "the stored experience %d cannot reach the recorded level %d, "
                "whose committed threshold is %d; the committed curve derives "
                "level %d" % (
                    resources_before["xp"],
                    level_before,
                    recorded_threshold,
                    derived,
                ),
            )

        # Derive the legacy envelope (design D1/D3/D5): the command, the
        # **derived** level, and the **neutral** vector are the module's, never
        # the client's.
        try:
            envelope_payload = level_envelope.build_envelope(level=derived)
        except level_envelope.EnvelopeError as failure:
            if failure.code in ("invalid_level", "invalid_vector", "invalid_timestamp"):
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command() returns
        # without raising, so reaching here IS the legacy result — which is
        # precisely why it is NOT taken as proof that the right level was written
        # and that nothing else moved.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D5).  Part one: the recorded level is
        # exactly the derived level.  Part two: **every** stored resource is
        # unchanged — the neutral vector's own guarantee, and what forecloses a
        # smuggled vector.  Either half failing is a reported failure, not a
        # success.
        try:
            level_after = boot.map_level(user_id)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if level_after != derived:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the recorded level is %r after execution, not the derived %d"
                % (level_after, derived),
            )
        for name in sorted(resources_after):
            if resources_after[name] != resources_before[name]:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the pre-execution %r: "
                    "a level-up moves no resource, so the derived neutral vector "
                    "requires every stored resource to be unchanged"
                    % (name, resources_after[name], resources_before[name]),
                )
        return (
            envelope(
                boot,
                result="success",
                derived_level=derived,
                level_before=level_before,
                level_after=level_after,
                curve={
                    "entries": entry_count,
                    "index_base": level_envelope.INDEX_BASE,
                    "derivation_status": level_envelope.DERIVATION_STATUS,
                    "rejected_alternative": level_envelope.REJECTED_ALTERNATIVE,
                    "entry_name": curve_entry.get("name"),
                    "entry_exp_required": curve_entry["exp_required"],
                    "next_level": derived + 1 if next_position is not None else None,
                    "next_name": (
                        next_entry.get("name")
                        if isinstance(next_entry, dict)
                        else None
                    ),
                    "next_exp_required": next_threshold,
                    "remaining": remaining,
                    "xp": resources_before["xp"],
                },
                resources=resources_after,
            ),
            200,
        )

    app.config["COMPAT_LEGACY_CORPUS"] = str(boot.corpus)
    return app
