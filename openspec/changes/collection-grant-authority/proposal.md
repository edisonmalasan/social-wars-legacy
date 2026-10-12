# Proposal

## Why

`POST /v1/collect` (M13 line 1) proved the authority boundary on a surface where the
legacy server happened to derive the answer itself. The next surface is the one where
the legacy server derives **nothing at all**, and where the modern layer has knowingly
left the hole open and labelled it.

Measured on `POST /v0/collection` (`apps/compat-api/compat_service.py:5938`) and on the
branch it executes, `complete_collection` (`command.py:504-523`):

- **The grant is committed content.** The item bag comes from
  `get_collection_prize(collection_id)` (`get_game_config.py:170-175`), a
  `json.loads` of the loaded configuration's `collections` table. A client can choose
  *which* collection; it cannot choose *what* is granted. This part is already right,
  and it is why v0's post-execution proof is non-tautological.
- **Eligibility is never checked.** v0 says so itself, in its own response body:
  `eligibility={"checked": False, "rule": NO_ELIGIBILITY_CHECK}`
  (`compat_service.py:6170-6173`). The committed `item_ids` requirement list - present
  on **all 10** collections, surviving normalization - is read by **no branch at all**.
- **No price is charged.** The branch's entire effect is the grant, a ledger append, and
  a `print`. The committed `cashPrice` field (35 on every row) has **zero** legacy
  consumers, so the "purchase" cost, if any, rides the client-sent vector that
  `command.py:40` applies before the branch is even selected.
- **The grant is not idempotent.** `command.py:517-518` appends the collection id only
  `if collection_id not in privateState["collections"]`, so the **ledger** is
  idempotent while the **grant** is not.

Put together, those four facts are an **unbounded, unconditional, free grant**. A caller
may name any of the ten committed collections, receive its committed prize, and repeat.
Nothing in the preserved server or in v0 stops it, and v0 actively reports that it does
not stop it.

This is the strongest authority hole in the dispatched-but-non-authoritative half of the
command surface, and it was selected by measurement rather than preference. The
selection was made against decision **D6** of `docs/legacy-m13-authority.md` - that
`collect` was chosen because v0's implementation is already proven against a captured
executed-legacy fixture - applied to the routed surface rather than to the unrouted one.
The full measurement:

- **63** named branches in `command.py`; **34** of them are proven by a captured
  executed-legacy fixture, located by searching committed fixture bytes for the escaped
  JSON command token.
- **40** branches are dispatched by a v0 route; **23** have no route behind either server.
- The intersection of *routed* and *fixture-proven* is **33**. `collect` was one; **32**
  remain, and they form the selection pool this line draws from.
- Only **1** of the 23 unrouted branches is fixture-proven at all (`add_xp_unit`), and
  it is Class D - an unvalidated client amount, which D6 explicitly rejected for
  `collect` too.
- Among the 32, `complete_collection` is the **only** one whose grant half is already
  server-derived from committed content. Every peer is client-dictated: `place_stored_item`
  and `sell_stored_item` take a client item id, `buy_stored_item_cash` takes a client item
  id and charges nothing, `weekly_reward` and `win_daily_bonus` take a client item,
  `expand` takes a client expansion id, `level_up` takes a client level.

## What Changes

- **`POST /v1/collection`** added to `apps/server-v1/`, executing the same single
  `complete_collection` intent through the same authority boundary line 1 delivered. The
  request carries a save identity and a collection id, and nothing else.
- **The one-time rule becomes enforceable.** The ledger append at `command.py:517-518`
  is the committed record that a collection was already claimed. v1 treats it as the
  authority for "already granted" and refuses a repeat with a typed refusal, closing the
  unbounded half of the hole.
- **Eligibility is verified from committed `item_ids`,** which is the field that decides
  whether the caller may claim the collection at all. This is derived from committed
  content, not invented, and the rejected alternative is recorded.
- **The committed `cashPrice` is derived, and the client vector is refused.** v1 charges
  the committed price server-side; a request carrying a resource delta is refused
  outright, which is the boundary's existing rule and not a new one.
- **The one-based alias is exposed, not absorbed.** `get_collection_prize` indexes
  `max(0, collection - 1)`, so collection ids **0 and 1 resolve to the same prize**, as
  does every negative id. v0 already reports this (`requested` / `resolved` /
  `clamped` / `aliased` / `alias_of`). v1 refuses an id that does not name a distinct
  committed collection rather than silently serving the clamped one.
- **No new refusal code may be invented by the route.** The status table lives in
  `server_v1_refusals.py` and is extended there, because line 1 recorded that v0's 24
  per-route derivations are what happens when each route grows its own answer.

## Non-goals

- **No change to `apps/compat-api/**`.** It is the parity oracle, not the thing being
  replaced. Line 1's D1 (coexistence) holds unchanged.
- **No SQL, PostgreSQL, or Alembic migration.** Line 1's D4 defers them to M14.
- **No conversion of any other v0 route**, and no adoption of v1 for any delivered
  gameplay flow.
- **No claim about what the Flash client displayed.** Every derivation below is derived
  from committed content and the preserved branch, never observed from the client.
- **No windowed capture and no pixel-parity claim**, because nothing is rendered.

## Impact

- Affected specs: `server-v1-collection-grant` (new), `server-v1-authority-boundary`
  (extended - the boundary gains a second worked slice).
- Affected code: `apps/server-v1/` only, plus the client-side `ServerV1Api` facade the
  boundary already registered.
- The Compatibility API suite stays at its recorded baseline as a **verified** figure,
  because this change adds no v0 route and touches no `apps/compat-api/**` file.