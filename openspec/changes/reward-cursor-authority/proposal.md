# Proposal

## Why

`/v0/reward` refuses to grant a daily or weekly bonus, but the one quantity the legacy
branches genuinely compute for themselves - the **cursor** - is still whatever the client
last sent. `command.py:446` computes `args[1] + 1` and `command.py:451` clamps it, so the
arithmetic is the server's own while its *input* is not; and `timestampLastBonus` has no
reader anywhere, so nothing bounds how often the branch may run. M10 line 1 recorded this
as an absence of behaviour. It is not an absence of authority: it is the branch's authority
defect, and it is the strongest remaining candidate in the pool because it is the only one
where the stored outcome is **server-computed arithmetic on a client-dictated input**.

## What Changes

- Add `POST /v1/reward` with a closed two-action vocabulary covering `win_daily_bonus`
  (primary) and `weekly_reward`, mirroring `/v1/magic`'s `operation` shape, which already
  covers two branches behind one route.
- The successor cursor is derived by the server from the **stored** cursor, never from a
  client-sent next id. The legacy backwards move (`4 -> 1` on an oversized next id) is
  recorded as a **divergence**, not reproduced.
- Every grant-shaped input - the client-sent item id, the client-sent cursor, and the cell
  and player the weekly long arm would place at - is refused by name with an empty payload
  and no change to the recorded document.
- **No payout is derived.** `command.py` credits nothing on either branch; its non-granting
  arm only prints. Applying `DAILY_GOLD_REWARDS` would diverge from the oracle, so the
  committed ladder stays unread exactly as it is today.
- **No eligibility rule is derived.** `timestampLastBonus` has zero readers, so the
  preserved server has no cooldown, daily window, or already-claimed check to reproduce,
  and the response reports the stored instant without consulting it.
- Both a bound and a schedule are **reported, never enforced**: the daily bound is the
  branch literal `5`, not the derived `len(DAILY_GOLD_REWARDS)`, and the rejected
  derivation is retained beside it as the delivered line already does.
- `/v0/reward` is **not** modified. It remains the parity oracle and the client's v0 path.

## Capabilities

### New Capabilities
- `server-v1-reward-authority`: Server v1 derives the daily and weekly reward cursor from
  recorded state, refuses every grant-shaped input, and pays nothing.

### Modified Capabilities
- `server-v1-authority-boundary`: gains a fifth worked transaction. This one is the first
  in the milestone whose success path moves **no** stored resource and **no** cursor that
  the client sent, so the boundary's claim that refusal is a typed domain decision is
  demonstrated on a transaction whose entire content is a derived transition.

## Impact

- **New**: `apps/server-v1/server_v1_reward.py`, its typed result module, its test module,
  the route registration, and the client-side typed result plus hermetic suite.
- **Unchanged**: `apps/compat-api/**` in its entirety - `/v0/reward` and its 7-transaction
  executed-legacy fixture under `tests/fixtures/godot-rewards/` are the oracle this line is
  measured against, not a thing being replaced.
- **New refusal codes** on the closed `server_v1_refusals` table, which line 4 left at
  exactly 20.
- **Counts that move**: v1 routes 4 to 5; authoritative branches 5 to 7; non-authoritative
  branches 58 to 56; non-authoritative v0 routes 20 to 19. Each is asserted, not restated.
- No SQL, no PostgreSQL, no Alembic migration, per line 4's D4.