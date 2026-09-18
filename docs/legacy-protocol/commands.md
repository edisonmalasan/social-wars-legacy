# Legacy command inventory

Source-grounded inventory of the legacy Social Wars command dispatcher (`command.py`, invoked through `command.php`), verified offline by `tools/command-catalog/verify_commands.py` against `commands.json` in this directory.

- **Evidence status: source inspection only.** Every entry below mirrors `commands.json`; this document is a readable view, not a separate record. Only four commands (`complete_tutorial`, `level_up`, `ping`, `set_variables`) have contained replay evidence in `tools/protocol-replay`; all other entries rest on source inspection alone.
- **Count note:** the approved proposal estimated 64 named branches, but the source contains **63** literal `cmd ==` comparisons (`command.py:42-953`) plus the unhandled `else` fallthrough (`command.py:954-956`). The extra proposal-table row, `push_dead_unit`, is an engine helper called from the `sell` KILL path, not a dispatcher branch.
- **Client-trust warning:** every command in a batch is preceded by `apply_resources` of client-sent `resources_changed` deltas (`command.py:40`), clamped at zero and never validated against costs. The server trusts the client for amounts everywhere.

## Envelope contract

One `command.php` POST carries a 64-char hash, a semicolon, and a JSON payload with `first_number`, `publishActions`, `ts`, `tries`, `accessToken`, and `commands`. The envelope fields other than `commands` are parsed and then unread. Each entry of `commands` is a `[map_id, cmd, args, resources_changed]` tuple: `map_id` indexes `save[maps]`, `cmd` is the command name, `args` is the positional argument list, and `resources_changed` is the 8-element delta list `[unknown, xp, gold, wood, oil, steel, cash, mana]` applied via `apply_resources` (`engine.py:251-271`) before dispatch. After the batch, `save_session(USERID)` persists the whole player save (`command.py:32`), even when the batch hit only the unhandled fallthrough.

## Town buildings and map objects

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `buy` | args[0] item_index (int); args[1] item_id (int); args[2] x (int); args[3] y (int); args[4] playerID / player team (int); args[5] orientation (int); args[6] unknown; args[7] reason (str) | bought_unit_add(save, item_id) when playerID == 1 (engine.py:86-90); map_add_item(map, item_index, item_id, x, y, orientation, player) (engine.py:8-32); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item_id, coordinates, orientation, player team, reason; resources_changed deltas |
| `move` | args[0] item_index; args[1] x; args[2] y; args[3] frame; args[4] string | item[1] = x, item[2] = y; missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and target coordinates; resources_changed deltas |
| `sell` | args[0] item_index; args[1] reason (str) | reason KILL routes the item through push_dead_unit (engine.py:149-171), which may mark it resurrectable; map_delete_item(map, item_index) (engine.py:48-53); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and reason string; resources_changed deltas |
| `batch_remove` | args[0] index_list JSON (list of item indexes) | map_delete_item for every listed index; unknown indexes are ignored inside map_delete_item; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | full index list; resources_changed deltas |
| `orient` | args[0] item_index; args[1] orientation | item[4] = int(orientation); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and orientation; resources_changed deltas |
| `add_click` | args[0] index | add_click(item) (engine.py:125-131); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |
| `activate_item_click` | args[0] index | activate_item_click(item) (engine.py:132-136); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |
| `buy_si_help` | args[0] index | buy_si_help(item) (engine.py:137-143); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas (the cost) |
| `finish_si` | args[0] index | finish_si(item) (engine.py:144-148); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |

## Town expansion

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `expand` | args[0] expansion (int-like) | map[expansions] += [int(expansion)]; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | expansion id; resources_changed deltas |

## Economy and trade

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `collect` | args[0] item_index | item[3] = time_now (collect timer); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas (the actual income) |
| `trade_resource` | args[0] resource_type (read but unused); args[1] sold flag: 1 sold, 2 bought (read but unused) | map[numTradesDone] = min(20, numTradesDone + 1); map[timestampLastTrade] = time_now; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | trade amounts and direction; resources_changed deltas |
| `set_resource_allies` | args[0] resource; args[1] index (map item index) | when the item exists: item[3] = time_now and finish_si(item); always: map[resourceAlliesMarket] = resource; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | resource value and item index; resources_changed deltas |

## Stored inventory

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `store_item` | args[0] item_index | item popped via map_pop_item (engine.py:42-47), then add_store_item(map, item_id) (engine.py:70-76); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |
| `place_stored_item` | args[0] item_index; args[1] item_id; args[2] x; args[3] y; args[4] playerID; args[5] orientation; args[6] unknown_autoactivable_bool; args[7] unknown_imgIndex | remove_store_item(map, item_id) (engine.py:77-85); map_add_item at the given coordinates (engine.py:8-32); bought_unit_add(save, item_id) (engine.py:86-90); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item_id, coordinates, orientation, player team; resources_changed deltas |
| `sell_stored_item` | args[0] item_id | remove_store_item(map, item_id); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item_id; resources_changed deltas (the proceeds) |
| `store_add_items` | args[0] item_id_list (list) | add_store_item plus bought_unit_add for every listed item_id; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | full item_id list; resources_changed deltas |
| `buy_stored_item_cash` | args[0] item_id | bought_unit_add(save, item_id) plus add_store_item(map, item_id); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item_id; resources_changed deltas (the price) |

## Tutorial, level, and unit XP

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `complete_tutorial` | args[0] tutorial_step (int) | save[playerInfo][completed_tutorial] = 1 when tutorial_step >= 25 or == 15; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | tutorial_step value; resources_changed deltas |
| `level_up` | args[0] new_level (int) | map[level] = new_level with no range or XP validation; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | new_level value; resources_changed deltas |
| `add_xp_unit` | args[0] item_index; args[1] xp_gain; args[2] level (optional; presence changes only the log line) | item attr xp created or incremented by xp_gain; missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and xp_gain; resources_changed deltas |

## Goals and quest state

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `set_goals` | args[0] goal_id; args[1] progress JSON: [visited, currentStep] | set_goals(save[privateState], goal_id, progress) (engine.py:96-101); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | goal_id and full progress vector; resources_changed deltas |
| `complete_goal` | args[0] goal_id | None; branch only logs completion; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (no command-specific state to persist) | goal_id; resources_changed deltas |
| `set_quest_var` | args[0] key (str); args[1] value | map[idCurrentMission] = value when key == 'id'; map[currentQuestVars][key] = value (dict created when falsy); key 'idSimpleChapter' is explicitly ignored and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | quest key and value; resources_changed deltas |
| `admin_set_quest_rank` | args[0] quest_index; args[1] difficulty | privateState[questsRank][str(quest_index)] = difficulty with no validation; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | quest index and difficulty; resources_changed deltas |

## Units and production queues

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `push_unit` | args[0] index_unit; args[1] index_building | unit popped via map_pop_item, then push_unit(unit, building) (engine.py:54-57); missing unit or building logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | unit and building indexes; resources_changed deltas |
| `pop_unit` | args[0] index_building; args[1] index_unit; args[2] item_id; args[3] x; args[4] y; args[5] playerID; args[6] unknown (read but unused) | popped unit rewritten to item_id/x/y/playerID, then map_add_item_from_item (engine.py:33-35); missing building or empty garrison logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | building index, replacement item_id, coordinates, player team; resources_changed deltas |
| `resurrect_hero` | args[0] index; args[1] item_id; args[2] x; args[3] y; args[4] used_syringe (read but unused) | resurrect_hero(save[privateState], item_id); map_add_item(map, index, item_id, x, y); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item_id and revive coordinates; resources_changed deltas (the syringe cost) |
| `push_queue_unit` | args[0] index | push_queue_unit(item) (engine.py:183-190); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |
| `push_queue_unit2` | args[0] atom_fusion_index; args[1] unit_id | push_queue_unit2(atom_fusion, unit_id) (engine.py:206-214); missing fusion item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | fusion index and unit_id; resources_changed deltas |
| `pop_queue_unit` | args[0] index | pop_queue_unit(item) (engine.py:191-205); missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index; resources_changed deltas |

## Combat resolution

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `kill` | args[0] item_index; args[1] reason (str) | map_delete_item(map, item_index); missing item logs an error and returns early; unlike sell, never touches the dead-unit pool; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and reason string; resources_changed deltas |
| `kill_iid` | args[0] item_id; args[1] reason_str | None; branch only logs; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (no command-specific state to persist) | item_id and reason string; resources_changed deltas |
| `end_attack` | args[0] response JSON (voluntary_end/victim/attacker/resources/honor/duration/townhall_gold/win/different_island/victim_units/attacker_units/resources_victim); args[1] unknown (read but unused) | attacker losses removed via map_lose_item; unparseable JSON logs an error and returns early; explicit TODOs: victim save untouched, no attack logs written; like end_quest, a response without attacker_units reaches a for-loop over None and raises; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | entire battle report including loot and honor; resources_changed deltas |

## Missions

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `collect_mission` | args[0] next_mission (int-like) | next_mission > 99 wraps to 1; map[idCurrentMission] = str(next_mission); map[timestampLastChapter] = time_now; map[currentQuestVars] = {}; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | next mission number; resources_changed deltas |
| `end_quest` | args[0] response JSON with win/duration/units/map/difficulty/voluntary_end/quest_id | lost units (unit[2] - unit[3] when positive) removed via map_lose_item (engine.py:215-229); unparseable JSON or missing quest_id logs an error and returns early; map[questTimes][str(quest_id)] = time_now; source-visible fragility: a response without a units list reaches a for-loop over None and raises before stamping quest time; Batch-level save_session(USERID) persists the whole player save after the command batc... | entire battle outcome report; resources_changed deltas (the rewards) |

## Research tracks

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `next_research_step` | args[0] type (0 Area 51, 1 Robotic Center) | researchStepNumber[type] += 1; timeStampDoResearch[type] = time_now; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | research type index; resources_changed deltas |
| `research_buy_step_cash` | args[0] cash (read but unused); args[1] type | timeStampDoResearch[type] = 0; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | research type index; resources_changed deltas (the cash cost) |
| `next_research_item` | args[0] type | researchItemNumber[type] += 1; researchStepNumber[type] = 0; timeStampDoResearch[type] = 0; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | research type index; resources_changed deltas |
| `reset_research_item` | args[0] type | researchItemNumber, researchStepNumber and timeStampDoResearch for type all set to 0; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | research type index; resources_changed deltas |

## Collections

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `unit_collections_completed` | args[0] collection_id | unit_collection_complete(save, collection_id); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | collection_id; resources_changed deltas |
| `complete_collection` | args[0] collection_id; args[1] bought flag (log label only) | every prize key added via add_store_item(map, int(key), prize[key]); collection_id appended to privateState[collections] when absent; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | collection_id; resources_changed deltas |

## Inventory and magic

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `activate` | args[0] item_id (used as a map item INDEX via map_get_item, despite the name); args[1] activate (int) | activate > 0: item[3] = time_now and item[6][cp] = args[1]; else item[3] = time_now and item[6] = {}; missing item logs an error and returns early; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item index and CP value; resources_changed deltas |
| `add_inventory_item` | args[0] item; args[1] quantity | inventory_add(save[privateState], item, quantity) (engine.py:109-115); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item and quantity; resources_changed deltas |
| `remove_inventory_item` | args[0] item; args[1] quantity | inventory_remove(save[privateState], item, quantity) (engine.py:116-124); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item and quantity; resources_changed deltas |
| `buy_mana_new` | no args read | None; branch only logs 'Bought mana'; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (no command-specific state to persist) | resources_changed deltas (the price and the mana) |
| `buy_magic` | args[0] magic_id | known spell: magics[str(magic_id)] += min(50, count + 1); unknown spell: magics[str(magic_id)] = 0; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | magic_id; resources_changed deltas (the price) |
| `use_magic` | args[0] magic_id | known spell: magics[str(magic_id)] = min(50, count + 1); unknown spell: magics[str(magic_id)] = 0; the branch never decrements stock (preserved source quirk); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | magic_id; resources_changed deltas |

## Offers, powerups, and premium

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `buy_premium_account` | args[0] package_index | expired premium: timeStampEndPremium = time_now + days * 86400; active premium: extended by days * 86400; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | package index; resources_changed deltas (the price) |
| `buy_offer_pack` | args[0] package_id (read but unused); args[1] item_list JSON (list of item ids) | add_store_item(map, item) for every id in the client-sent list; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | full item list and package id; resources_changed deltas (the price) |
| `buy_powerups` | args[0] powerup_index (read but unused) | None; branch body is a TODO that only logs; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (no command-specific state to persist) | resources_changed deltas (the price and any effect) |

## Timed rewards

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `weekly_reward` | args[0] item_index; args[1] item_id; args[2] x; args[3] y; args[4] playerID; longer arg lists grant the item, shorter ones grant resources only | item branch: map_add_item plus bought_unit_add; always: timeStampMondayBonus = time_now; weeklyRewardIndex = (index + 1) % get_weekly_reward_length(); Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | prize item and coordinates (item branch); resources_changed deltas |
| `win_daily_bonus` | args[0] item (item_id; <= 0 means resources only); args[1] bonus id; next id = args[1] + 1, wraps to 1 above 5 | timestampLastBonus = time_now; bonusNextId = next_id (wrapped); item > 0: bought_unit_add plus add_store_item; else resources-only log; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | prize item and bonus id; resources_changed deltas |

## Event minigames

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `darts_reset` | args[0] seed (client-chosen) | dartsRandomSeed = seed; dartsBalloonsShot = []; dartsHasFree = True; dartsGotExtra = False; timeStampDartsReset and timeStampDartsNewFree = time_now; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | random seed; resources_changed deltas |
| `darts_new_free` | no args read | dartsHasFree = True; timeStampDartsNewFree = time_now; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | resources_changed deltas |
| `darts_shoot_balloon` | args[0] target index; args[1] won_extra flag | target appended when new; dartsHasFree = False; timeStampDartsNewFree = time_now; dartsGotExtra = True when won_extra; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | target index and win flag; resources_changed deltas (the winnings) |
| `soulmixer_speedup` | args[0] atom_fusion_index | atom_fusion[6][ts] = 0, clearing the training timer; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | fusion index; resources_changed deltas (the cost) |

## Social and tracking flags

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `rt_open_graph_unit` | args[0] item | str(item) appended when not already present; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | item id; resources_changed deltas |
| `first_time_marketplace` | no args read | privateState[marketPlaceFirstTime] = True; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | resources_changed deltas |

## Diagnostics (debug-labeled, never production)

**Debug-labeled commands: never a production client path.** `flash_debug` overwrites absolute resource balances from client values; `ping` and `set_variables` are heartbeats that still apply client-sent deltas. A modern replacement must not reproduce `flash_debug`.

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `flash_debug` | args[0] cash; args[1] unknown (ignored); args[2] xp; args[3] gold; args[4] oil; args[5] steel; args[6] wood | playerInfo[cash] = cash; map xp/gold/oil/steel/wood overwritten with the client values; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). | entire resource state; resources_changed deltas |
| `ping` | no args read | None; branch only logs 'Pong'; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (no command-specific state to persist) | resources_changed deltas |
| `set_variables` | no args read | None; branch only logs 'Set player resources'; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (persists the pre-dispatch delta application) | resources_changed deltas (the entire effect) |

## Time-manipulation (never production)

**Time-manipulation command: never a production client path.** `fast_forward` rewinds nearly every server-side cooldown by a client-chosen interval. A modern replacement must not reproduce it.

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `fast_forward` | args[0] seconds (int) | rewinds map timestamp/timestampLastChapter/timestampLastTreasure/timestampLastTrade, privateState timestampLastBonus/timestampLastAllianceBonus/timeStampDartsNewFree/tsAttacksReset/tsSpyingsReset, every research timer, every item timer and atom-fusion ts, and every quest time by seconds (floored at 0); weekly fields timeStampMondayBonus and timeStampDartsReset are explicitly left untouched (commented out); Batch-l... | arbitrary rewind interval; resources_changed deltas |

## Dispatcher fallthrough

Unknown command names reach the `else` fallthrough at `command.py:954-956`: the name and args are logged, `do_command` returns, the batch continues, and batch persistence still runs. A modern API must reject unknown intents explicitly instead of absorbing them while still applying their resource deltas.

| Command | Args | State and persistence | Client trust |
| --- | --- | --- | --- |
| `(unhandled)` | any unknown cmd string with any args | None; branch logs the unknown name and returns from do_command while the batch continues; Batch-level save_session(USERID) persists the whole player save after the command batch (command.py:32; sessions.py:248-255). (still runs for the batch, persisting deltas and earlier commands) | unknown command names are accepted without error; resources_changed deltas |

## Alliance-adjacent behavior

Alliance gameplay is **not implemented**: the `alliance/` route returns an empty placeholder object (see `endpoints.json`). The only alliance-adjacent dispatcher command is `set_resource_allies`, which sets the `resourceAlliesMarket` market field (and finishes one indexed item); it is not overstated as social behavior here.

## Notes on evidence

- All behavioral descriptions come from reading `command.py` and the helpers it calls (`engine.py`, `sessions.py`, `get_game_config.py`); none were executed for this inventory.
- Contained replay evidence for `complete_tutorial`, `level_up`, `ping`, and `set_variables` exists in `tools/protocol-replay`; that evidence does not establish progressed-player or general gameplay parity.
- Admin-named (`admin_set_quest_rank`), debug (`flash_debug`), and time-manipulation (`fast_forward`) paths are labeled explicitly and are never a production client path.
- No credentials or private player records appear in this inventory.
