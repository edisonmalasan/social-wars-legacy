## Why

The endpoint catalog inventories where requests enter the legacy server, but `command.py` — the 956-line dispatcher behind `command.php` — is the core game-behavior specification, and only 4 of its 64 named commands have any focused behavioral evidence (recorder/replay cover `complete_tutorial`, `level_up`, `ping`, `set_variables`). A source-grounded command catalog is the next roadmap objective before domain-by-domain migration, so every migrated behavior starts from recorded legacy semantics rather than rediscovery.

## What Changes

- Add a reviewed machine-readable command catalog and readable documentation covering the `command.php` envelope, all 64 named dispatcher commands, and the unhandled-command fallthrough.
- Record per command: domain, positional argument shape, client-sent resource deltas, state read, state modified, persistence effects, client-trusted fields and security concerns, observed fixtures, replacement API placeholder, and migration status.
- Record the envelope contract: `first_number`, `publishActions`, `ts`, `tries`, `accessToken`, and the per-command `[map_id, cmd, args, resources_changed]` tuple, including that `apply_resources` runs from client-sent deltas before dispatch.
- Add a read-only offline verifier that checks catalog structure, command coverage, and source references against current source without importing or executing the legacy application; reject unsupported dispatch syntax instead of silently dropping it.
- Add focused regression tests for command extraction, drift detection, catalog consistency, and containment.
- Leave all legacy handlers and behavior unchanged; classify unknown, debug, time-manipulation (`fast_forward`), and event-system commands explicitly rather than repairing them.

## Source-grounded command inventory

References below identify the dispatcher in `command.py` at proposal time. The envelope is parsed at `command.py:9-32`; dispatch runs at `command.py:34-956` with client-sent resources applied at `command.py:40` before any branch. Unknown names fall through to the `else` at `command.py:954-956`, which logs and returns from `do_command` while the batch continues and `save_session` still runs at `command.py:32`. Counts below come from reading the `if cmd ==` / `elif cmd ==` chain; the implementation must verify them against source rather than trusting this list.

| Command | Domain (proposed) | Notes |
| --- | --- | --- |
| `buy` | buildings/units | Placement with 8 positional args; `playerID == 1` queues unit |
| `move`, `orient`, `sell` | buildings | Town-object mutation |
| `store_item`, `place_stored_item`, `sell_stored_item`, `store_add_items`, `buy_stored_item_cash` | storage | Stored-inventory moves |
| `collect` | economy | Income collection |
| `complete_tutorial`, `level_up`, `add_xp_unit` | progression | Replay evidence exists for first two |
| `set_goals`, `complete_goal` | quests/goals | Goal progress and completion |
| `set_quest_var`, `admin_set_quest_rank` | quests | Quest variable mutation |
| `push_unit`, `pop_unit`, `push_queue_unit`, `push_queue_unit2`, `pop_queue_unit` | units | Unit production queues |
| `kill`, `kill_iid`, `resurrect_hero`, `push_dead_unit` | combat/units | Damage, death, revive paths |
| `end_quest`, `end_attack`, `collect_mission` | missions/combat | Mission resolution |
| `next_research_item`, `next_research_step`, `reset_research_item`, `research_buy_step_cash` | research | Research timers and cash steps |
| `complete_collection`, `unit_collections_completed` | collections | Collection completion |
| `add_inventory_item`, `remove_inventory_item`, `activate`, `activate_item_click`, `add_click`, `use_magic`, `buy_magic`, `buy_mana_new` | inventory/magic | Item and magic handling |
| `buy_powerups`, `buy_offer_pack`, `buy_premium_account`, `buy_si_help`, `finish_si` | monetization | Cash/premium paths |
| `trade_resource`, `set_resource_allies` | economy/social | Resource exchange |
| `expand` | town | Zone expansion |
| `weekly_reward`, `win_daily_bonus` | rewards | Timed reward claims |
| `darts_reset`, `darts_new_free`, `darts_shoot_balloon` | events | Event minigame state |
| `soulmixer_speedup` | events | Event timer manipulation |
| `batch_remove` | buildings | Bulk removal |
| `first_time_marketplace`, `rt_open_graph_unit` | social/tracking | Flags and publish tracking |
| `fast_forward` | debug/time | Rewinds many server timestamps; never a production client path |
| `flash_debug`, `ping`, `set_variables` | diagnostics | `ping`/`set_variables` have replay evidence |
| unhandled names | dispatcher | Logged at `command.py:954-956`, batch continues |

The implementation must distinguish all 64 named branches plus the fallthrough, verify the envelope contract, and document per-command client trust (notably the pre-dispatch `apply_resources` of client-sent deltas and any premium/time effects) without gameplay-parity claims.

## Capabilities

### New Capabilities

- `command-catalog`: Source-grounded, evidence-labeled inventory of legacy dispatcher commands with deterministic offline consistency verification.

### Modified Capabilities

None.

## Impact

Adds `docs/legacy-protocol/commands.json`, `docs/legacy-protocol/commands.md`, and focused tooling/tests under `tools/command-catalog/`; updates documentation links and executed-check references. Uses Python 3.9 standard-library tooling, with no dependency upgrade, server import, network, browser, Flash, save mutation, modern API, content normalization, or gameplay change. Broad M2 gameplay coverage and progressed-player saves remain unavailable; this change does not claim them.
