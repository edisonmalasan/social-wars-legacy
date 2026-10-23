<!--
  Generated investigation artifact.
  Source of truth for the details inside is the file it was produced from:
  decompiled ActionScript 3 (FFDec 26.3.0) of assets/flash/Basesec_1.5.4.swf,
  the Python server sources, and live traffic captured from a real Adobe Flash
  Player session against the local server.
-->

# Command Catalogue, Economy, Quests & Goals

> **Scope:** Static decompilation of all 94 client command classes, cross-checked against the Python server dispatch table and config/main.json globals.
>
> **Method:** Static decompilation of all 94 client command classes, cross-checked against the Python server dispatch table and config/main.json globals.
>
> **Subject:** per-command wire contract, economy rules, quest state machine, goal system, client/server gaps
>
> Part of the Social Wars reverse-engineering report set. See [`../README.md`](../README.md)
> for the document map and [`../docs/00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the
> cross-cutting conclusions.

---

# 03 — Command Catalogue, Economy, Quests & Goals (Social Wars Flash client)

**Sources**

| What | Path |
| --- | --- |
| Decompiled AS3 client | `<as3-root>\scripts\` |
| Python server | `<upstream-repo>\command.py`, `engine.py`, `constants.py`, `get_game_config.py` |
| Game config (server copy of `get_game_config.php`) | `<upstream-repo>\config\main.json` |

**Client version:** `Config.VERSION = "1.5.4"`, `Config.SERVER_KEY = "4vVSD8dftv6hdfb1Hnk9"`, `Config.GAME_NAME = "SexWars"` (branded Social Wars).

---

## 0. Transport model (read this first)

### 0.1 Command array shape

`commands/Command.as`:

```as3
public function serialize() : Array {
   return [ Base.Main.townID, this.commandID, this.args, this.resourcesVariation ];
}
```

So one command on the wire is a **4-element array**:

| Index | Meaning |
| --- | --- |
| `comm[0]` | town / map id (`Base.Main.townID`, 0 = own town) |
| `comm[1]` | **command name** (the wire string, e.g. `"buy"`) |
| `comm[2]` | `args` — an `Array` of positional arguments (types vary per command) |
| `comm[3]` | `resourcesVariation` — an **8-slot int vector** of *client-declared* resource deltas |

`CommandManager.getCommandData()` JSON-encodes the whole command array and POSTs it to `command.php`.

### 0.2 The 8-slot resource vector (`comm[3]`)

`commands/Command.as`:

```as3
public static const RESOURCE_ENERGY:int = 0;
public static const RESOURCE_XP:int    = 1;
public static const RESOURCE_GOLD:int  = 2;
public static const RESOURCE_WOOD:int  = 3;
public static const RESOURCE_OIL:int   = 4;
public static const RESOURCE_STEEL:int = 5;
public static const RESOURCE_CASH:int  = 6;
public static const RESOURCE_MANA:int  = 7;
public static const NUM_RESOURCES:int  = 8;
```

`setResource(amount, key)` maps the short keys:

| key | slot | resource |
| --- | --- | --- |
| `"e"` | 0 | energy |
| `"x"` | 1 | XP (experience) |
| `"g"` | 2 | gold |
| `"w"` | 3 | wood |
| `"o"` | 4 | oil |
| `"s"` | 5 | steel |
| `"c"` | 6 | cash (premium currency) |
| `"m"` | 7 | mana |

**Critical:** `setResource()` is a *client-side prediction* only. The client applies `comm[3]` to its own counters (`ResourceManager.adjustResourcesByCommand`) and sends the same vector to the server, which blindly applies it (`engine.py::apply_resources`). The server never recomputes the delta — it trusts the client. See §5.

`setResource(amount, key, notTokenized=true)` adds to `_resourcesVariation` but **not** to `_resourcesNotTokenized`; the "not tokenized" vector is what is actually added to the displayed player counters. `CmdKill`/`CmdKillIid`/`CmdCollect` (partial) use the `true` flag: the value is reported to the server but not added to the player's visible stock (battle loot / server-computed amounts).

`Command.involvesCash` → true if `resourcesVariation[6] != 0`. When true, `CommandManager.queueCommand` starts a 10 ms timer that flushes the packet immediately (bypassing the normal `Base.Main.push_time` batch timer) — cash is expected to be re-validated server-side instantly.

### 0.3 Packet framing

`CommandManager.sendPacket()`:

```
POST <serverUrl>/command.php?USERID=<phpsessid>&user_key=<userKey>&language=<loc>
body: URLVariables
   data     = HMAC-SHA256(payload, Config.SERVER_KEY) as hex  ++  ";"  ++ payload
   client_id= <Base.Main.clientId>
payload (JSON):
   { first_number, commands:[ ... ], tries, publishActions, ts, flashVersion, accessToken }
```

`Crypto.constructHashAndPayload` → `Hex.fromArray(hash(payload, key)) + ";" + payload`, where `hash` is HMAC-SHA256 with the **payload as the key** and the **SERVER_KEY as the message** (`Crypto.hash(param1, param2)` → `HMAC.compute(stringToByteArray(param2), stringToByteArray(param1))`).

Server error strings the client understands (`CommandManager.commandSentHandler`): `client_id`, `no_client_id`, `hash`, `user_key`, `json`, `timehack`, `bad_flash_version`.

Retries: up to 3 (`currentPacket.tries >= 3` → `ERROR_TIMEOUT`). A packet is considered stale after **30 s**; a session is considered expired after **2700 s** (45 min) between sends.

`CommandManager.add(cmd, ...rest)` pushes a *different* shape (`{"cmd":…,"args":[…]}`) — **dead code**, never called anywhere in the client. Ignore it.

### 0.4 Queueing rules

`CommandManager.queueCommand(cmd, force)`:
* Commands are only queued when `force == true` **or** `gameMode == GAME_MODE_NORMAL` **or** (`gameMode == GAME_MODE_NEIGHBOUR` and `cmd is CmdAssistNeighbour`).
* `force == true` bypasses the game-mode gate but **not** the `gameMode == NORMAL` check for resource application? — no: `adjustResourcesByCommand` is called for every queued command that passes the gate. `force` only relaxes the *mode* gate. **Caveat: commands queued with `force=true` in a non-NORMAL mode are still applied to the local resource counters.**
* Every 20th queued command (and only for `Base.Player.iLevel >= 10`) a `SystemCmdDebugResources` (`flash_debug`) is appended — it reports the *absolute* current cash/energy/xp/gold/oil/steel/wood to the server.
* `Config.TIMER_UNITMOVE_COMMANDS = 6000` ms — a separate timer that emits `move` commands for units that moved.
* `Config.TIMER_COMMANDS = 6` (legacy constant, the real batch interval is `Base.Main.push_time` seconds).

---

## 1. THE COMMAND CATALOGUE

94 distinct wire names, from 94 command classes in `scripts/commands/`.

Notation for the **Δ res** column — `slot:amount`, only non-zero entries shown, `+` = client credits the player, `−` = client debits:
* `e`=energy(0) `x`=XP(1) `g`=gold(2) `w`=wood(3) `o`=oil(4) `s`=steel(5) `c`=cash(6) `m`=mana(7)
* `*` suffix = `notTokenized` (reported to server, **not** added to visible counters)
* `Σ` = the delta comes from a runtime object/array, not a literal

**Server** column: `Y` = handled by `command.py::do_command`; `N` = falls through to `print(f"Unhandled command '{cmd}' -> args", args)`.

| # | Wire name (`comm[1]`) | AS3 class | Arguments (`comm[2]`, in order) | Δ res (`comm[3]`) | Server |
| --- | --- | --- | --- | --- | --- |
| 1 | `accept_collect_help` | `CmdAcceptCollectHelp` | `0: int` isoID of the helped building; `1: String` friend fbid | — | **N** |
| 2 | `activate` | `CmdActivate` | `0: int` isoID; `1: int` collect-period index `cp` (0..3) | — | Y |
| 3 | `activate_item_click` | `CmdActivateItemClick` | `0: int` isoID; `1: String` JSON of `inventory_ids` *(only if building has inventory_ids)* | — | Y |
| 4 | `add_click` | `CmdAddClick` | `0: int` isoID | — | Y |
| 5 | `add_inventory_item` | `CmdAddInventoryItem` | `0: int` inventory item id; `1: int` quantity | `c:−qty*item.cashPrice` (only if `withCash==true`) | Y |
| 6 | `add_xp_unit` | `CmdAddUnitXP` | `0: uint` unit isoID; `1: uint` xp amount; `2: uint` unit level *(only if non-zero)* | `c:−param3` (if non-zero) | Y |
| 7 | `admin_set_quest_rank` | `AdminCmdSetQuestRank` | `0: String` quest index (as `String(Quest.iQuest)`); `1: String` difficulty ("1".."3") | — | Y |
| 8 | `apply_rewards_ranking` | `CmdApplyRewardsRanking` | `0: String` JSON of the reward payload | `c:+param1` | **N** |
| 9 | `assist_neighbor` | `CmdAssistNeighbour` | `0: String` neighbour fbid; `1: String` JSON array of `[tx,ty,buildingId]` clicks | `g:+10/clk`, `x:+3/clk` (`Config.ASSIST_CLICK_REWARD_GOLD/XP`) | **N** |
| 10 | `assist_receive` | `CmdAssistReceive` | `0: int` building **item id** (not isoID) | Σ from `param2` map (`g/w/o/s/c`) | **N** |
| 11 | `attack_player` | `CmdAttackPlayer` | `0: String` target fbid | — | **N** |
| 12 | `batch_remove` | `CmdBatchRemove` | `0: String` JSON array of isoIDs to delete | — | Y |
| 13 | `buy` | `CmdBuy` | `0: int` isoID; `1: int` building/item id; `2: int` tx; `3: int` ty; `4: int` playerID (1=self); `5: int` frame; `6: int` auto-activable 0/1; `7: String` type `"b"`/`"u"`/`"n"` | if paid: `Σ −building.costs` (per key, or `c:−cost_unit_cash`); `x:+building.xp` | Y |
| 14 | `buy_magic` | `CmdBuyMagic` | `0: int` magic spell id | `c/−param2` of `param4` type; `m:+param3` | Y |
| 15 | `buy_mana_new` | `CmdBuyManaNew` | *(no args)* | `−param2` of `param3` type; `m:+param1` | Y |
| 16 | `buy_offer_pack` | `CmdBuyOfferPack` | `0: int` offer pack id; `1: String` JSON array of selected item ids | `c:−price` (the pack's `cost_cash`, or the super-pack tier price); `x:+pack.xp`; `g:+pack.gold`; `s:+pack.steel`; `o:+pack.oil`; `w:+pack.wood` | Y |
| 17 | `buy_powerups` | `CmdSoulMixerPowerups` | `0: int` power-up level index | `c:−SOUL_MIXER_POWERUPS_LEVELS[i].cash_cost` | Y |
| 18 | `buy_premium_account` | `CmdBuyPremiumAccount` | `0: uint` package index (0..5) | `c:−package.price` | Y |
| 19 | `buy_resources` | `CmdBuyResources` | *(no args)* | `+gained` map (resource→amount); `−cost` map | **N** |
| 20 | `buy_si_help` | `CmdBuySiHelp` | `0: int` isoID | `c:−socialItem.worker_cost` | Y |
| 21 | `buy_stored_item_cash` | `CmdBuyStoredItemCash` | `0: int` item id | `c:−param2` | Y |
| 22 | `clean_attacks` | `CmdCleanAttacks` | *(no args)* | — | **N** |
| 23 | `clean_received_assists` | `CmdCleanReceivedAssists` | `0: String` neighbour fbid | — | **N** |
| 24 | `clear_message` | `CmdClearMessage` | *(no args)* | — | **N** |
| 25 | `collect` | `CmdCollect` | `0: int` isoID of the resource building | `Σ: +amount` of `building.collect_type`; `x:+building.collect_xp`; premium: `+ceil(v*50/100)` per non-cash entry; the optional `param3` map is added with the **not-tokenized** flag (`*`) | Y |
| 26 | `collect_mission` | `CmdCollectChapter` | `0: int` **next** chapter id | Σ from `param2` map (chapter rewards) | Y |
| 27 | `complete_collection` | `CmdCompleteCollection` | `0: int` collection id; `1: int` bought 0/1 | `c:−collection.cashPrice` (if bought) | Y |
| 28 | `complete_goal` | `CmdCompleteGoal` | `0: int` goal id | Σ `RewardResource.amount` per reward | Y |
| 29 | `complete_tutorial` | `CmdCompleteTutorial` | `0: int` tutorial step | — | Y |
| 30 | `cross_promotion_finished` | `CmdCrossPromotionFinished` | `0: String` cross-promo id | — | **N** |
| 31 | `darts_new_free` | `CmdDartsNewFree` | *(no args)* | — | Y |
| 32 | `darts_reset` | `CmdDartsReset` | `0: int` random seed | — | Y |
| 33 | `darts_shoot_balloon` | `CmdDartsShootTarget` | `0: int` target index (0..24); `1: int` won-extra 0/1 | `c:−dartCost` (only if the shot was **not** free) | Y |
| 34 | `end_attack` | `CmdEndAttack` | `0: String` JSON battle result; `1: String` voluntary end `"1"/"0"` | `g:+resources.g`; `x:+resources.x`; premium `+ceil(v*50/100)` on both | Y |
| 35 | `end_quest` | `CmdEndQuest` | `0: String` JSON `{map,units,win,duration,voluntary_end,quest_id,difficulty}` | Σ `RewardResource.amount`; premium `+amount*50/100` (non-cash) | Y |
| 36 | `exchange_cash` | `CmdExchangeCash` | *(no args)* | `c:−5`; `g:+2500` (`Config.BUY_GOLD_CASH / BUY_GOLD_GOLD`) | **N** |
| 37 | `expand` | `CmdExpand` | `0: int` expansion tile id | `−price` of `param3` type (`g` or `c`) | Y |
| 38 | `fast_forward` | `CmdFastForward` | `0: int` seconds | — | Y |
| 39 | `finish_building` | `CmdFinishBuilding` | `0: int` isoID; `1: int` clicks_to_build (−1 if none) | `c:−speedUpCost` via `useAsSpeedUp()` | **N** |
| 40 | `finish_robotic_help` | `CmdFinishRoboticHelp` | `0: String` JSON array | — | **N** |
| 41 | `finish_si` | `CmdFinishSi` | `0: int` isoID; `1: int` *(only if ≠ −1)*; `2: int` amount *(only if `param4 != "n"`)* | `+param3` of `param4` type | Y |
| 42 | `flash_debug` | `SystemCmdDebugResources` | `0: int` cash; `1: int` energy; `2: int` xp; `3: int` gold; `4: int` oil; `5: int` steel; `6: int` wood | — (absolute values, not deltas) | Y |
| 43 | `kill` | `CmdKill` | `0: int` isoID; `1: String` building type | Σ `*` (not tokenized) | Y |
| 44 | `kill_iid` | `CmdKillIid` | `0: int` **item id**; `1: String` building type | Σ `*` | Y |
| 45 | `level_up` | `CmdLevelUp` | `0: int` new level | `+LevelInfo.reward_amount` of `LevelInfo.reward_type` | Y |
| 46 | `load_map` | `CmdLoadMap` | `0: String` map id | — | **N** (admin only) |
| 47 | `modify_energy` | `CmdModifyEnergy` | *(no args)* | `e:+param1` | **N** |
| 48 | `modify_position_universe` | `CmdModifyPositionUniverse` | `0: int`; `1: int` | — | **N** |
| 49 | `move` | `CmdMove` | `0: int` isoID; `1: int` tx; `2: int` ty; `3: int` frame; `4: String` reason text (`"Unitat <id>"` for unit moves) | — | Y |
| 50 | `next_research_item` | `CmdNextResearchItem` | `0: uint` research type (0=Area 51, 1=Robotic Center) | — | Y |
| 51 | `next_research_step` | `CmdNextResearchStep` | `0: uint` research type; `1: Boolean` | — | Y |
| 52 | `orient` | `CmdOrient` | `0: int` isoID; `1: int` frame | — | Y |
| 53 | `ping` | `CmdPing` | *(no args)* | — | Y |
| 54 | `place_gift` | `CmdPlaceGift` | `0: int` isoID; `1: int` building id; `2: int` tx; `3: int` ty; `4: int` frame | `x:+building.xp` | **N** |
| 55 | `place_stored_item` | `CmdPlaceStoredItem` | `0: int` isoID; `1: int` building id; `2: int` tx; `3: int` ty; `4: int` playerID; `5: int` frame; `6: int` auto-activable 0/1; `7: int` imgIndex; `8: int` unitLevel+1 & `9: int` requiredXP *(only for a marketplace-won unit)* | — | Y |
| 56 | `pop_queue_unit` | `CmdPopQueueUnit` | `0: int` isoID | `c:−param2` (if > 0) | Y |
| 57 | `pop_unit` | `CmdPopUnit` | `0: int` building isoID; `1: int` unit isoID; `2: int` unit item id; `3: int` x, `4: int` y, `5: int` playerID, `6: int` unit frame *(only when `param3 == false`)* | — | Y |
| 58 | `premium_upgrade` | `CmdPremiumUpgrade` | `0: int` OLD isoID; `1: int` NEW isoID; `2: int` new building id; `3: int` clicks_to_build (−1) | `−costs` per key (premium upgrade cost = `ceil(build_time/60/5)*1` cash) | **N** |
| 59 | `push_queue_unit` | `CmdPushQueueUnit` | `0: int` isoID | `−param2` costs map (unit cost); `x:+StaticData(iIDUnitTrained).xp` | Y |
| 60 | `push_queue_unit2` | `CmdPushUnitSM` | `0: int` isoID; `1: int` trained unit id | — | Y |
| 61 | `push_unit` | `CmdPushUnit` | `0: int` **unit** isoID; `1: int` **building** isoID | — | Y |
| 62 | `remove_inventory_item` | `CmdRemoveInventoryItem` | `0: int` inventory item id; `1: int` quantity | — | Y |
| 63 | `research_buy_step_cash` | `CmdResearchStepBuyCash` | `0: int` cash cost; `1: uint` research type | `c:−param1` | Y |
| 64 | `reset` | `CmdReset` | *(no args)* | — | **N** (admin only) |
| 65 | `reset_collect` | `CmdResetCollect` | `0: int` isoID | `c:−param2` | **N** |
| 66 | `reset_position_univers` | `CmdResetPositionUniverse` | *(no args)* | — | **N** |
| 67 | `reset_research_item` | `CmdResetResearchItem` | `0: uint` research type | — | Y |
| 68 | `reset_world_change` | `CmdResetIslandChange` | *(no args)* | — | **N** |
| 69 | `resurrect_hero` | `CmdResurrect` | `0: int` isoID; `1: int` item id; `2: int` x; `3: int` y; `4: int` usedSyringe 0/1 | if **no** syringe: `−param6[i]` of `param7[i]` type | Y |
| 70 | `rt_open_graph_unit` | `CmdNewOpenGraphUnit` | `0: int` unit item id | — | Y |
| 71 | `save_map` | `CmdSaveMap` | `0: String` map id | — | **N** (admin only) |
| 72 | `sell` | `CmdSell` | `0: int` isoID; `1: String` reason (`KILL`,`CLEAN`,`SQEST`,`CQEST`,`REGEN`,`TREAS`,`HARV`,`STABL`,`UPGR`,`FARM`,`BLDZE`,`RECDR`,`DEBUG`,`VEHIC`,`ACTIV`,`ATRZO`,`COLQS`,`BOSS`,`OUTOB`,`SUMMON`) | `+costs[k]/20` for each non-cash `k` (only when `param3==true`) | Y |
| 73 | `sell_gift` | `CmdSellGift` | `0: int` item id | `+costs[k]/20` per non-cash `k` | **N** |
| 74 | `sell_stored_item` | `CmdSellStoredItem` | `0: int` item id | `+costs[k]/20` per non-cash `k` | Y |
| 75 | `set_goals` | `CmdSetGoals` | `0: int` goal id; `1: String` JSON `[visited?1:0, currentStep]` | — | Y |
| 76 | `set_help_map` | `CmdSetHelpMap` | `0: String` | — | **N** |
| 77 | `set_quest_var` | `CmdSetQuestVar` | `0: String` key; `1: String` JSON value | — | Y |
| 78 | `set_resource_allies` | `CmdSetResourceAllies` | `0: String` resource key the allies market offers (`"w"/"s"/"o"/"g"`); `1: int` isoID | — | Y |
| 79 | `set_strategy` | `CmdSetStrategy` | `0: int` defensive strategy | — | **N** |
| 80 | `set_variables` | `AdminCmdSetVariables` | *(no args!)* | Σ `setResource(obj[k], k)` for every key of the object | Y (server just prints) |
| 81 | `soulmixer_speedup` | `CmdSoulMixerSpeedup` | `0: int` isoID | `c:−param2` | Y |
| 82 | `spy_player` | `CmdSpyPlayer` | `0: String` target fbid | — | **N** |
| 83 | `store_add_items` | `CmdStoreAddItems` | `0: Array` of item ids (raw array, **not** JSON-string) | — | Y |
| 84 | `store_item` | `CmdStoreItem` | `0: int` isoID | — | Y |
| 85 | `system_receive_mana` | `CmdReceiveMana` | `0: int` mana amount | `m:+param1` | **N** |
| 86 | `system_receive_si_help` | `CmdSystemReceiveSiHelp` | `0: int`; `1: String` | — | **N** (admin only) |
| 87 | `system_reset_quest` | `SystemCmdResetQuest` | *(no args)* | — | **N** (admin only) |
| 88 | `trade_resource` | `CmdTradeResource` | `0: String` resource key; `1: int` sell 1/0 | sell: `g:+cost`, `−amount` of resource; buy: `g:−cost`, `+amount` | Y |
| 89 | `unit_collections_completed` | `CmdUnitCollectionCompleted` | `0: int` collection id | `c:+1` | Y |
| 90 | `upgrade` | `CmdUpgrade` | `0: int` isoID | — | **N** |
| 91 | `use_magic` | `CmdUseMagic` | `0: int` magic spell id | `m:−spell.manaCost` | Y |
| 92 | `weekly_reward` | `CmdCollectMondayBonus` | *(no args for resource rewards)*; for a unit reward: `0: int` isoID, `1: int` building id, `2: int` 0, `3: int` 0, `4: int` PLAYER_SELF | `g:+value` / `c:+value` / `w,o,s:+value` | Y |
| 93 | `win_alliance_daily_bonus` | `CmdCollectAlliancesBonus` (extends `CmdCollectMondayBonus`, overrides `commandID`) | same shape as `weekly_reward` | same as `weekly_reward` | **N** |
| 94 | `win_daily_bonus` | `CmdWinBonus` | `0: int` item id (0 for gold days); `1: int` day index 1..5 | `g:+DAILY_GOLD_REWARDS[day-1]` | Y |

### 1.1 Where each command is fired from (client call sites)

| Command | Fired from |
| --- | --- |
| `buy` | `MapInitializer`, `IsoBuilding`, `IsoElement`, `IsoEngine`, `Base`, `GoalHarbor`, `GoalManager`, `PopupSelectRobot`, `AdminPanel` (15 sites) |
| `sell` | `MapInitializer`, `Base`, `IsoElement`, `IsoFightingElement`, `AdminPanel` (14 sites) |
| `collect` | `IsoBuilding.collect()`, `IsoElement` |
| `move` | `Base` (drag), `CommandManager` (unit-move timer, every 6 s) |
| `end_quest` | `AbstractQuest.sendResults()`, `PopupWeeklyQuestFinished` |
| `set_quest_var` | `Chapter.saveChapterStatus()`, `Chapter.cleanChapterStatus()` |
| `flash_debug` | `CommandManager.queueCommand` (every 20th command, level ≥ 10) |
| `ping` | `Base` tick, every 9000 frames, only when `gameMode != NORMAL` |
| `weekly_reward` | `MondayBonusPopUp` |
| `win_daily_bonus` | `PopupNewDaily` (5 call sites, one per day) |
| `darts_*` | `PopupDarts` |
| `assist_neighbor` | `NeighbourManager` |
| `attack_player` / `spy_player` / `end_attack` / `clean_attacks` | `Assault` |
| `set_goals` / `complete_goal` | `AbstractGoal.save()` / `AbstractGoal.deliverReward()` |
| `level_up` | `ResourceManager.onLevelUp` (auto-queued on level change) |
| `modify_energy` | `PlayerStatus.load()` (tops energy up to `ENERGY_MAX_REGULAR_VALUE` on login) |
| `expand` | `IsoTerrain.purchaseLand()` |
| `place_gift` / `place_stored_item` | `Base` (gift placement) |
| `premium_upgrade` | `IsoBuilding` (premium-speed upgrade path) |
| `upgrade` | `IsoInteractiveElement.doUpgrade()` (unit level-up) |
| `end_attack` / `end_quest` etc. | see above |

### 1.2 Argument type notes / gotchas

* `collect_mission` argument 0 is the **next** chapter id (`Base.Main.currentQuestId = chapterNumber + 1`), not the finished one.
* `sell` argument 1 is a *reason string*, not an enum index.
* `push_unit` is (unitIsoID, buildingIsoID) — the opposite order from `pop_unit` (buildingIsoID, unitIsoID).
* `premium_upgrade` argument 0 is the **old** isoID and argument 1 the **new** one — a clone must remove the old building and add the new one.
* `place_stored_item` may carry 2 extra trailing args for a marketplace-won unit (level+1 and the XP needed for that level).
* `activate` argument 1 is the *collect-period index* (`cp` 0..3 → `COLLECT_MINUTES` / `COLLECT_MULTIPLIER`), and the server stores it in `item.attr["cp"]` and treats `>0` as "activated".
* `store_add_items` argument 0 is a **raw AS3 Array** (JSON-encoded by the outer payload encoder), whereas `batch_remove` / `set_goals` / `set_quest_var` / `assist_neighbor` / `end_attack` / `end_quest` / `apply_rewards_ranking` / `finish_robotic_help` carry a **JSON string** inside `args[0]`/`args[1]`.
* `darts_shoot_balloon` argument 1 is "won the extra/major prize", **not** "was free". The free-shot decision is expressed by the *absence* of a cash delta.
* `set_variables` (`AdminCmdSetVariables`) sends **no args** — the resource vector *is* the payload.

---

## 2. ECONOMY RULES

### 2.1 Resource types

| Resource | key | Slot | Where stored (client) | Where stored (server) |
| --- | --- | --- | --- | --- |
| Energy | `e` | 0 | `Base.Player.iEnergy` (`privateState.energy`) | not tracked by the Python server |
| XP | `x` | 1 | `Base.Player.iExperience` (`map.xp`) | `map["xp"]` |
| Gold | `g` | 2 | `Base.Player.iGold` (`map.gold`) | `map["gold"]` |
| Wood | `w` | 3 | `Base.Player.iWood` (`map.wood`) | `map["wood"]` |
| Oil | `o` | 4 | `Base.Player.iOil` (`map.oil`) | `map["oil"]` |
| Steel | `s` | 5 | `Base.Player.iSteel` (`map.steel`) | `map["steel"]` |
| Cash | `c` | 6 | `Base.Player.iCash` (`playerInfo.cash`) | `save["playerInfo"]["cash"]` |
| Mana | `m` | 7 | `Base.Player.iMana` (`privateState.mana`) | `save["privateState"]["mana"]` |

Other cost keys exist in `Constants` but are **not** part of the 8-slot vector: `ds` (damage self), `de` (damage enemy), `t` (time), `zz`, `h` (heal), `abs` (absorbed). `setResource()` silently ignores them.

### 2.2 Storage caps

* Base cap (`globals.BASE_RESOURCE_LIMITS`): `{"g":20000,"o":20000,"s":20000,"w":20000}` — i.e. **20 000** of each of gold/oil/steel/wood. Cash and mana are uncapped.
* `globals.DEPOT_LIMITS` = `{"g":[1,7,17,27],"o":[1,8,18,28],"w":[1,5,15,25],"s":[1,6,16,26]}` — the **player levels** at which depot tiers 1..4 unlock per resource. `Base.getDepotState(item)` walks this array to compute the depot tier for a resource.
* Silo buildings (`ID_BUILDING_SILO_1/2/3` = 932/941/942) raise the storage; `globals.LIMIT_PER_LEVEL_SILO = 0.2` (20 % per silo level) — **UNVERIFIED** how it is applied (the client does not compute the number; the server's `getResourceLimitsMap` only reports `BASE_RESOURCE_LIMITS`).
* `Base.Player.getResourceLimitsMap()` returns only `w,s,g,o` from `BASE_RESOURCE_LIMITS` — the client never sees a larger cap. **The server is authoritative for real caps.**
* `globals.MAX_MINES_WOOD/OIL/STONE/GOLD = 1` — at most one vein of each type per island.
* `globals.INITIAL_LIMIT_PER_WALL = 80`, `LIMIT_PER_LEVEL_WALL = 6`, `LIMIT_PER_LEVEL_TOWER = 4`, `INITIAL_PER_LEVEL_TOWER = 20`.

### 2.3 Collection (production) rules

* `building.collect` = base amount per collection cycle; `building.collect_type` = the resource produced (`g/w/o/s`); `building.collect_xp` = XP granted.
* Amount formula (both in `CmdCollect` and in `IsoBuilding.collect`):

  ```
  base   = floor(building.collect * Iso.getResourceMultiplier(el))     // multiplier is always 1 in this build
  mult   = COLLECT_MULTIPLIER[cp-1]      // cp = chosen collect period index (1..4)
  if unitsInside > 1:
      amount = floor( floor( base + (units-1) * base * MULTIPLIER_PEASANTS ) * mult )
  else:
      amount = floor( base * mult )
  ```
  `Config.MULTIPLIER_PEASANTS = 0.2` — each extra worker inside a mill adds 20 % of the base.
* Anti-hack guard in the client: if `unitsContained > building.unit_capacity` the client logs `"HACK DETECTED - jsbermeo: the units in this building are higher than the building capacity!"` and collects **0**. **This is a client-side-only check** — see §5.
* Collect period choices: `globals.COLLECT_MINUTES = [5, 60, 240, 480]` minutes, and `globals.COLLECT_MULTIPLIER = [0.25, 1, 2, 3]` — the 4 options are (5 min, ×0.25), (60 min, ×1), (240 min, ×2), (480 min, ×3). `cp` is stored on the building (`attrs.cp`) and re-sent with `activate`.
* `globals.TIMER_HARVEST = 1000` (ms animation), `globals.CONSTRUCTING_TIME = 1000`, `globals.TIMER_DEAD_DISAPPEAR = 4000`.
* `globals.COLLECT_HELP_SECONDS = 3600` — a friend help grants 1 h of production.
* Premium accounts add `Config.PREMIUM_ACCOUNT_BONUS_PERCENTAGE = 50` % of every collected resource **and** the XP (ceiling).

### 2.4 Population

`PlayerStatus.updatePopulation()`:

```
maxCurrent = min( START_MAX_POPULATION + Σ(uiPopulationGranted of population buildings),
                   MAX_POPULATION_CAP + Iso.getAdditionalPopulation() )
current    = Σ(unit.iPopulationCount of player units) + Iso.countPlayerElementsBeignTrainedPopulation()
```

* `globals.START_MAX_POPULATION = 20`
* `globals.MAX_POPULATION_CAP = 175`
* `globals.MAX_POPULATION_PER_LEVEL = 3` (the GUI warns "Reach level N to get an increase of 1 in population limit")
* `Base.Main` refuses to place a unit if `iPopulationCurrent + unit.population > iPopulationMaxAllowed` (hard cap) or `> iPopulationMaxCurrent` (soft cap).
* `map.increasedPopulation` (server) is added on top of the cap.

### 2.5 Energy

| Rule | Value | Source |
| --- | --- | --- |
| Max free energy | **30** | `globals.ENERGY_MAX_REGULAR_VALUE` |
| Regen interval | **300 000 ms = 5 min** for **+1** | `globals.ENERGY_INCREASE_ENERGY_INTERVAL` |
| First tick | after `Base.Player.secsRemainingEnergyIncrease` s (from the server) | `ResourceManager.initResources()` |
| Construction cost | 1 energy | `globals.ENERGY_CONSTRUCTION_COST` |
| Assist (friend help) cost | 1 energy | `globals.ENERGY_ASSIST_QTY` |
| Attack cost | 30 | `Config.COST_BUY_ATTACK` |
| Spying cost | 15 | `Config.COST_BUY_SPYINGS` |
| Extra-energy packs | 10/20/30/40 energy for 10/20/30/40 cash | `globals.ENERGY_COSTS` / `PERMISSION_COSTS`, `PERMISSION_PACK_UNITS` |
| Show add-energy button limit | 3 | `globals.SHOW_ADD_ENERGY_BUTTON_LIMIT` |

On login the client compares `privateState.energy` to 30 and, if short, **queues `modify_energy` with the deficit** — the client asks the server for free energy. The Python server does not implement `modify_energy` (prints "Unhandled command").

### 2.6 Level-up / XP curve

* The curve is **server data**: `config/main.json → levels[]` — 100 entries, each `{name, exp_required, reward_type, reward_amount}`.
* First entries: `Slave`(0 xp, `s`50), `Servant`(40, `w`250), `Peon`(60, `s`250), `Peasant`(100, `g`250), `Villager`(200, `c`1), `Scout`(350, `c`1) … last: `Conqueror`(2 016 089 205, `c`1).
* `Config.EXP_MIN = Config.EXP_MAX = 5000` (legacy placeholders; the real values come from `arLevelList`).
* Level check (`PlayerStatus.checkForLevelUp`): `iExperience >= arLevelList[iLevel].exp_required` → level up; `uiExpMin = arLevelList[level-1].exp_required`, `uiExpMax = arLevelList[level].exp_required`.
* On level-up the client **auto-queues `level_up(newLevel)`** (`ResourceManager.onLevelUp`) and the level reward is added: `setResource(arLevelList[newLevel-1].reward_amount, arLevelList[newLevel-1].reward_type)`.
* `map.level` is set by the server on `level_up`.
* `globals.MANA_REWARD_PER_LEVEL = 2` and `globals.LEVEL_MAGIC = 2` — mana awarded per level (the client-side level-up path only adds the level reward from `levels[]`; the mana grant is server-side in the original).

### 2.7 Town hall / expansion / new town

* **Expansion** (`CmdExpand`): the client pops `PopupExpand`, adds the tile to `Base.Main.ownedGrid`, computes the price from `Base.Items.expansionPriceList[ownedGrid.length-1]` (`.coins` or `.cash` depending on `ExpandTabNew2.PAYMENT_MODE`), and sends `expand(tileId, price, type)`.
  `config/main.json → expansion_prices` (first 4 entries are free — the starting 4×4 grid):
  `[{0,0},{0,0},{0,0},{0,0}, {coins:2500,cash:5,neighbors:1}, {5000,8,2}, {10000,10,3}, {15000,12,4}, {20000,14,5}, {25000,16,6}, {30000,18,7}, {40000,20,8}, {50000,20,9}, {75000,20,10}, {100000,20,11}, {100000,20,12}, {100000,20,13}, {100000,20,14}, …]`
* **New town / new map** (`town_prices`, `map_prices`): `[{coins:100000,cash:20,level:15}, {300000,20,25}, {550000,20,35}, {1000000,20,45}]`. `Config.TOWN_PRICE_GOLD = 100000`, `Config.TOWN_PRICE_CASH = 22` (legacy constants; the config table is authoritative).
* `Config.MULTIPLIER_UNLOCK = 1/3` — town-hall unlock multiplier.
* `TownManager.loadTown(fbid, townId)` switches the active `townID` and reloads the map; `TownManager.hasSecondTown()` = `maps.length > 1`; `getSecondRace()` = `maps[1].r`.
* **Chapter (island) unlocking**: `MapInitializer.doSpawnChapter(id)` tries up to 10 chapters, skipping islands the player already owns (`islandsAvailable()`), wrapping around `Config.NUM_CHAPTERS = 9`. Chapter definitions: `ChapterManager.CHAPTER_01_KEY=1 … CHAPTER_08_LURKER=8, CHAPTER_09_SIMPLE=9`; islands `[1],[3],[1],[2],[3],[2],[1],[3],[]`.
* `MapManager` map ids: player map = 1, quests 101..114, hardcore 117..122, 123, 124, 126, 125, weekly 149.

### 2.8 Building costs, build times, upgrades

All per-item data lives in `config/main.json → items[]` and is consumed by `core/StaticData.as`:

| Field | Meaning |
| --- | --- |
| `costs` | JSON object `{"g":..,"w":..,"o":..,"s":..}` (cash is *not* in `costs`; units use `cost_unit_cash`) |
| `cost_unit_cash` | cash price of a single unit trained in this building |
| `build_time` | seconds to construct (or train) |
| `xp` | XP granted on completion |
| `min_level` | minimum player level to place |
| `upgrades_to` | id of the upgraded building (upgrade chain) |
| `syringes` | number of hero-resurrection syringes (Hospital) |
| `training_time` | unit training time (default 3 if NaN) — but `StaticData.training_time` getter returns **5** unconditionally (`Base.Main.abTimedUpgrades || true ? 5 : this._training_time`) |
| `clicks_to_build` | number of friend clicks needed to finish a "socially-built" building |
| `unit_capacity` | max units inside a building |
| `population` | population consumed by the unit |
| `building_limit_same_id` | max copies of the building |
| `building_limit_same_scf` | max copies per sub-category/functional group |
| `max_collects`, `volume`, `max_elem_vol` | storage / collect caps |
| `sm_training_time` | Atom Fusion (Soul Mixer) training time |

**Upgrade rules** (client, `IsoBuilding` upgrade path):
* Requires `player level >= item.min_level` of the *target* building, and a free tile.
* Non-premium upgrade: the old building is removed (`SELL_REASON_UPGRADE`) and the new one added; the old building's cost is **refunded at 1/20** (`Config.DIVISOR_SELL = 20`) and the new building's `costs` are charged.
* Premium upgrade (`param2 == true`): cost = `StaticData.premium_upgrade_costs` = `ceil(build_time / 60 / UPGRADE_SPEEDUP_PRICING[0]) * UPGRADE_SPEEDUP_PRICING[1]` = `ceil(minutes/5) * 1` **cash** (`globals.UPGRADE_SPEEDUP_PRICING = [5,1]`).
* Speed-up (hurry) of a normal build: `globals.BUILD_SPEEDUP_MIN_TIME = 10` s minimum remaining time; `globals.COST_HURRY_UP = 2` (cash) — the client sends `finish_building` and calls `useAsSpeedUp(cost)`.

### 2.9 Market (own market) and Allies market

**Own market** (`ButtonMarket`, `PopupMarket`):
* Tradeable resources: wood, oil, steel (gold is the currency). `globals.MARKET_BASE_COSTS = {"o":100,"s":150,"w":100}` gold per 100 units.
* Trade amounts: `globals.MARKET_AMOUNT_TRADE = [100,200,300]`.
* Price formula: `cost = round(base * (amount/100) * (1 + traded[resource] * MARKET_INCREMENT))`, `MARKET_INCREMENT = 0.02`; on sell `cost = round(cost * MARKET_SELL_PERCENTAGE)` with `MARKET_SELL_PERCENTAGE = 0.75`.
* Limits: `globals.MARKET_MAX_NUM_TRADES = 20` per `MARKET_PERIOD_HOURS = 20` hours; the counter resets when `now - map.timestampLastTrade > 3600*MARKET_PERIOD_HOURS`. (`engine.py::reset_stuff` instead resets daily: `now // 86400 != last_trade // 86400` → mismatch with the client.)
* The `trade_resource` command carries `(resourceKey, sell?1:0)`; the client also applies the gold/resource delta itself. The server only counts trades.

**Allies market** (`ID_BUILDING_ALLIES_MARKET = 74`):
* `globals.ALLIES_MARKET_INITIAL_COLLECT = {"w":125,"s":125,"o":125,"g":125}`, `globals.ALLIES_MARKET_INCREMENTAL_COLLECT` = the same.
* `Config.RESOURCES_MARKET_PER_ALLY = 125` — each additional helper (friend) adds 125 units.
* `CmdSetResourceAllies` tells the server which resource the market currently offers; `finish_si` delivers the amount.
* Alliance daily bonus: `globals.ALLIANCE_DAILY_BONUS_REWARDS = [{"type":"g","value":150,"members":0},{"g":1500,5},{"g":5000,25},{"c":1,45}]` — collected with `win_alliance_daily_bonus` (not implemented by the Python server).

### 2.10 Weekly "Monday bonus" cycle

* Rewards: `globals.MONDAY_BONUS_REWARDS = [{"type":"g","value":2500}, {"type":"u","value":[1055,1033,1046,1063,1198]}, {"type":"c","value":5}]` — 3 entries, so the weekly reward index cycles with period 3. The unit entry has 5 possible units, indexed by `privateState.weeklyRewardIndex` (server: `weeklyRewardIndex = (weeklyRewardIndex + 1) % get_weekly_reward_length()` where length = max list length = 5 — **the server uses 5, the client uses 3 for the outer cycle**: mismatch, see §5).
* Availability: `Base.as` — if `Utils.getWeekDayFromTimeStamp() == WEEKDAY_MONDAY` and the collected date != today → `STATE_READY_TO_COLLECT`; if it was already collected today → `STATE_COLLECTED`; on SUNDAY → `STATE_NOT_READY` (visible but not claimable); other days → hidden.
* The client sends `weekly_reward` with the reward object; for a unit reward it also sends 5 positional args so the server can spawn the unit on the map.
* `privateState.timeStampMondayBonus` is set by the server on claim.

### 2.11 Daily bonus cycle

* `globals.DAILY_GOLD_REWARDS = [100, 250, 500, 1000, 0]` — a 5-day cycle: days 1-4 give gold, **day 5 gives a hero** (item id, `CmdWinBonus(5, itemGuanyat)`).
* `privateState.bonusNextId` holds the next day (1..5, 0 = use `consecutiveDays`).
* `Utils.isDailyBonusReady(lastBonusTs, nowTs, tzModifier)` returns `[ready, reset]`: `floor((last/3600+tz)/24)` vs `floor((now/3600+tz)/24)` — a day boundary in the player's local time zone. `reset == true` means the streak restarts at day 1.
* `win_daily_bonus` args = `[itemId, dayIndex]`; the server sets `timestampLastBonus = now` and `bonusNextId = dayIndex+1` (wrapping to 1 after 5).

### 2.12 Darts minigame cycle

* Weekly prize tables in `config/main.json → darts_items[]`: each entry `{id, start_date, items:[6 unit ids], extra_item}` (the "major" prize). The server rewrites `start_date` so each week starts on a Monday (`get_game_config.py::update_darts`).
* Board: `PopupDarts.NUM_TARGETS = 25` balloons; `NUM_ITEMS = 6` prize units (`NUM_RARE_ITEMS = 2`, `NUM_UNCOMMON_ITEMS = 2`).
* Free shot: one per day (`dartsHasFree`). `checkForDartsReset()` → if `timeStampDartsReset < currentWeekStart` → `darts_reset(seed)` (new board + free shot); else if not the same day and fewer than 25 balloons shot → `darts_new_free()`.
* Paid shot: `DART_COST_CASH = 20` cash (charged via the `darts_shoot_balloon` resource delta, only when the shot was not free).
* `darts_shoot_balloon(targetIndex, wonExtra)` — `wonExtra` = 1 when the last remaining "extra"/major prize was discovered.
* `store_add_items([itemId])` is sent for every won unit (and for the major prize).

### 2.13 Premium account

* `globals.PREMIUM_ACCOUNTS = [{"time":360,"price":800},{"time":180,"price":450},{"time":30,"price":80},{"time":7,"price":40},{"time":3,"price":20},{"time":1,"price":8}]` — index 0 = 360 days / 800 cash, … index 5 = 1 day / 8 cash.
* `buy_premium_account(packageIndex)` → the client extends `premiumAccountTimeExpire` locally and sends the package index; the server does the same (`timeStampEndPremium += days*86400`).
* Premium effects: `+50 %` on collected resources, `+50 %` on quest rewards (non-cash), `+50 %` on attack gold/XP.
* `globals.MANA_PER_PURCHASE = 5`, `globals.COST_MANA_CASH = 1`, `globals.COST_MANA_GOLD = 10000`, `globals.NUM_SPELL_USES_LVL2 = 25`, `NUM_SPELL_USES_LVL3 = 50`.

### 2.14 Other economy constants worth knowing

| Constant | Value |
| --- | --- |
| `Config.DIVISOR_SELL` | 20 (refund = cost / 20) |
| `Config.MULTIPLIER_PEASANTS` | 0.2 |
| `Config.MULTIPLIER_UNLOCK` | 1/3 |
| `Config.PREMIUM_ACCOUNT_BONUS_PERCENTAGE` | 50 |
| `Config.BUY_GOLD_CASH` / `BUY_GOLD_GOLD` | 5 / 2500 |
| `Config.RESOURCES_MARKET_PER_ALLY` | 125 |
| `Config.ASSIST_CLICK_REWARD_GOLD` / `_XP` | 10 / 3 |
| `Config.FRIENDS_ASSIST_DIVISOR` | 0.25 |
| `Config.FRIENDS_ASSIST_EXPERIENCE` | 10 |
| `Config.ATTACKS_MAX` | 3 |
| `Config.ATTACKS_PERIOD_HOURS` | [0.5, 6] |
| `Config.ATTACKS_SAME_PLAYER_HOURS` | 4 |
| `Config.ATTACKS_MIN_LEVEL` | 8 |
| `Config.QUESTS_PERIOD_HOURS` | 4 (per-quest cooldown) |
| `Config.QUESTS_MIN_LEVEL` | 4 |
| `Config.NUM_CHAPTERS` | 9 |
| `Config.GIFT_BUILD_TIME` | 5 s |
| `Config.RESURRECT_MULTIPLIER` | 500 |
| `globals.MAX_GOLD_STOLEN` | 20 000 |
| `globals.GOLD_STOLEN_BOTTOM_PCT` / `TOP_PCT` | 15 % / 35 % |
| `globals.MAX_GOLD_QUEST` | *not present in this config* — the client reads `Base.Items.globals.MAX_GOLD_QUEST` (undefined ⇒ `undefined` comparison ⇒ the gold cap in `Quest.elementKilled` is effectively never hit) |
| `globals.SPYINGS_MAX` / `SPYINGS_PERIOD_HOURS` | 3 / 24 |
| `globals.MIN_LEVEL_ATTACKS_1/2/3` | 10 / 15 / 20 |
| `globals.MIN_LEVEL_ATTACK_SIEGE_1/2/3` | 25 / 30 / 35 |
| `globals.NUM_ACTIVE_MISSIONS` | 5 (simultaneous active goals) |

### 2.15 Offer packs and mystery boxes

The store's cash packs are `config/main.json → offer_packs` (44 entries; the
schema is in [`04-python-server-and-data.md` §8.10](./04-python-server-and-data.md#810-offer_packs-44)).
The client has **three** purchase shapes, and they are not interchangeable:

| Shape | How to recognise it | What the client does | What the server must grant |
| --- | --- | --- | --- |
| Flat pack | `items` is a flat array of ids (or `null` for the premium entry) | Adds **every** id to the store | Every id in the pack |
| Random pack | Pack id is in `PromotionPacks.RANDOM_PACK_IDS` — only **4** | Rolls `Math.random() * 100`, then takes the first pair `[itemId, threshold]` whose threshold is greater than the roll; adds **one** item | One item, chosen by the **server's** roll |
| Super mystery pack | Pack `type` is `"super"`, or the id is in `PromotionPacks.SUPER_PACK_IDS` — `6-14`, `17`, `19`, `20` | Rolls **one**, **two** or **four** items from three rarity rows; see below | The same count, chosen by the **server's** roll |

The click path is `core/PromotionPacks.as`:

* `buyPack(packId)` (`:127-180`) checks `canAfford(pack.cost_cash)`, adds the
  selected items to the local store, and queues
  `CmdBuyOfferPack(pack, itemIds)`. For a flat pack the ids are all of
  `pack.items`; for pack 4 the loop above selects exactly one pair's id.
* `PopupMistery.as` is only the display for pack 4: it shows the four possible
  prizes as Rare / Uncommon / Common / Common.
* `PopupSuperMistery.as` (`:397-421`) has three Buy buttons with prices
  `[60, 100, 200]` by default. `PromotionPacks.PACK_PRICES` overrides pack 19 to
  `[30, 60, 100]`; every other super pack uses the default. It calls
  `buySuperPack(packId, tier, price)`.
* `buySuperPack` (`PromotionPacks.as:182-290`) treats `items` as **three rows**:
  row 0 = rare, row 1 = uncommon, row 2 = common. The tiers are:
  * tier 0 (first button): **one** item from rows 1+2;
  * tier 1 (second button): **one** rare plus **one** item from rows 1+2;
  * tier 2 (third button): **one** rare plus **three** items from rows 1+2.
  The client's picks use `Math.round(Math.random() * (n - 1))`, which is not a
  uniform choice.

`CmdBuyOfferPack` sends only `[packId, JSON array of selected ids]`
(`commands/CmdBuyOfferPack.as`). It also declares the pack's resource delta:
`c:−price`, `x:+xp`, `g:+gold`, `s:+steel`, `o:+oil`, `w:+wood`. The super
pack's price is the tier price, which the client has already copied into
`pack.cost_cash` before constructing the command.

**Trust boundary.** The Python upstream parses the client's `item_list` and
adds every id to `map["store"]` (`upstream/socialwarriors/command.py:710-718`).
That grants any item in any quantity for free. The clone must ignore the item
list as a *source of truth*: price the pack from content, roll the random or
super selection server-side, and add only the resulting ids to the store. The
super tier is identifiable from the selected-item count — 1, 2 or 4 — because
the three tiers grant exactly those counts. A count other than 1, 2 or 4 is
invalid. The `place_stored_item` side must then **decrement** the store entry
when the item is placed; otherwise a pack item can be placed repeatedly.

The premium entry is pack **18**: `type` is `"premium_account"`, `items` is
`null`, and `cost_cash` is 0. It never sends `buy_offer_pack`; the store opens
`PopupPremiumAccount` instead (`PromotionPacks.as:396-398`). The actual purchase
is `buy_premium_account(packageIndex)` with the `PREMIUM_ACCOUNTS` index, as
specified in §2.13. The premium is a server-owned timestamp, not a store item
(see [ADR 0013](../../docs/adr/0013-the-premium-is-a-timestamp.md)).

Known data defects to handle explicitly:

* Pack 18 is the premium entry and must not be sold as a normal pack.
* Pack 35 and packs 37-43 contain the malformed id `1072.1224` in the super
  rows. The upstream turns that into the store key `"1072.1224"`. The clone
  should reject the malformed entry (or normalise it deliberately) rather than
  creating an unplaceable store item.
* `enabled` and `position` decide whether a pack is shown; `position = 0` is
  hidden. The server should refuse a disabled or hidden pack even if the client
  sends its id.

---

## 3. QUEST SYSTEM

There are **two distinct systems** in the client:

1. **Chapters / "missions"** — the story campaign on the *player map* (`scripts/chapters/`). State is persisted in `map.currentQuestVars` and synced with `set_quest_var`.
2. **Quests** — the assault missions on separate maps (`scripts/quest/`), selected from the "Missions World" screen.

### 3.1 Chapters (campaign / island missions)

**Selection & triggering**
* `Config.NUM_CHAPTERS = 9` chapters. `ChapterManager.chapterDefinitions` maps chapter id → constructor + islands:
  `1 CHAPTER_01_KEY → Chapter01Key (island 1)`, `2 CHAPTER_02_GUILLE → Chapter02Guille (island 3)`, `3 CHAPTER_03_BAZOOKA (island 2)`, `4 CHAPTER_04_JEEPS (island 1)`, `5 CHAPTER_05_SIEGE_CONVENTIONAL (island 3)`, `6 CHAPTER_06_MEGATANK (island 2)`, `7 CHAPTER_07_SIEGE_ELEPHANT (island 1)`, `8 CHAPTER_08_LURKER (island 3)`, `9 CHAPTER_09_SIMPLE → SimpleChapter (islands [])`.
* Spawning: `MapInitializer.doSpawnChapter(id)` — tries up to 10 times, wrapping `id = id % NUM_CHAPTERS + 1`, skipping chapters whose islands the player already owns. `GoalCompleteChapter.onPopupclosed()` also triggers the spawn.
* The chapter is placed on a remote island; the player travels there, kills the defenders, and collects the treasure.

**Quest-variable state machine** (`Chapter.createEmptyStatus(id)` — this is the canonical shape, and it matches the server's `currentQuestVars`):

```json
{
  "id": <int chapter id>,
  "spawned": false,
  "ended": false,
  "visited": false,
  "activators": [],   // chapter-segment ids whose activator was collected
  "boss": [],         // indices into arBosses
  "treasure": [],     // indices into arTreasures
  "killed": []        // chapter element ids already killed
}
```

Transitions (each mutation is persisted by `Chapter.saveChapterStatus(key)` → `CmdSetQuestVar(key, value)` → `set_quest_var`):

| Key | Set to `true` / pushed when |
| --- | --- |
| `id` | `onClosePopup()` — the chapter was actually spawned on the map (also saves `spawned`) |
| `spawned` | `onClosePopup()` (after the mission-start popup is closed) |
| `ended` | `ChapterManager.finalizeChapter()` — the chapter was completed |
| `visited` | `Chapter.visited` flag; set on `SimpleChapter`/`AbstractQuest` when the player has any record of the quest (`Base.Player.questsRank[Quest.iQuest]`) |
| `activators` | `onActivatorCollected()` — pushes the chapter-segment id of the activator whose defenders were all killed |
| `boss` | `onBossKilled()` — pushes the index of the killed boss |
| `treasure` | `onTreasureCollected()` — pushes the treasure index |
| `killed` | `saveElementKilled(elementId)` — pushes a chapter element id that was killed (so a re-entered chapter does not respawn it) |
| `translation` | `checkQuestState()` — the localisable string table for the chapter (saved once) |
| `idSimpleChapter` | `SimpleChapter.init()` — the *simple* (endless) chapter id; saved via `saveChapterStatus("idSimpleChapter")` |
| `playerLevel`, `startTile` | `SimpleChapter.init()` — the level/tile the simple chapter was generated for |

`Chapter.cleanChapterStatus()` resets every key to its empty value (deletes `id`) and sends one `set_quest_var` per key.

**Victory conditions** (`Chapter.checkQuestState` / `onActivatorCollected`):
`activators.length >= NUM_ACTIVATORS` **AND** `boss.length >= arBosses.length` **AND** `treasure.length >= NUM_TREASURES` → `end()`. `Chapter` defaults: `NUM_TREASURES=0`, `NUM_ACTIVATORS=0`, `ACTIVATOR_AREA=15`, `QUEST_WITH_ENDERS=true`, `ENDERS_WITH_BOSS=false`, `TREASURE_AS_ATREZZO=false`, `KEEP_ENEMIES_IDENTITY=false`, `TREASURE_WITH_STEPS=false`.

**Rewards:** `globals.REWARDS_CHAPTERS = [{}, {g:250,w:200}, {g:500,o:400}, {g:750,s:600}, {g:1000,w:800}, {g:1250,o:1000}, {g:1500,s:1200}, {g:1750,w:1400}, {g:2000,o:1600}, {g:2250,s:1800}, {g:2500,w:2000}, {g:2750,o:2200}, {g:3000,s:2400}]` — indexed by chapter id. `SimpleChapter` chapters (id ≥ 9) use their own `chapterData.reward` object.

**Completion wire format:** `CmdCollectChapter(nextChapterId, rewardsObject)` → `collect_mission` with `args[0] = nextChapterId` and the reward delta in `comm[3]`. The server sets `map.idCurrentMission`, `map.timestampLastChapter` and clears `map.currentQuestVars`.

**Simple chapters (endless mode, chapter 9+):** `SimpleChapterData.getChapterData(id)` picks a chapter definition; `chapterStatus.idSimpleChapter` stores the current one. The server currently **ignores `idSimpleChapter`** (`command.py` explicitly ignores that key) so the chapter never advances past 1 on the server — the client keeps its own copy in `map.currentQuestVars` (which the server *does* store generically).

### 3.2 Assault quests (`scripts/quest/`)

**Quest ids and classes** (`quest/Quest.as`):

| Constant | Id string | Class | Map id | Title |
| --- | --- | --- | --- | --- |
| `QUEST_01_BAZOOKA` | `100000001` | `Quest01Bazooka` | 101 | DEFEAT THE ENEMY |
| `QUEST_02_CENTRAL_NUCLEAR` | `100000002` | `Quest02CentralNuclear` | 102 | BLOW THE POWER PLANT |
| `QUEST_03_DEFEND_CONVOY_AUTO` | `100000003` | `Quest03DefendConvoyAuto` | 103 | DEFEND THE CONVOY |
| `QUEST_04_SUPERTANK` | `100000004` | `Quest04Supertank` | 104 | STOP THE BIG WEAPON |
| `QUEST_05_ASSAULT_CONVOY` | `100000005` | `Quest05AssaultConvoy` | 105 | (speech.title) |
| `QUEST_06_AIRSTRIKE` | `100000006` | `Quest06Airstrike` | 106 | AIRSTRIKE! |
| `QUEST_07_SHIP` | `100000007` | `Quest07Ship` | 107 | (dynamic) |
| `QUEST_08_ROCKET` | `100000008` | `Quest08Rocket` | 108 | (dynamic) |
| `QUEST_09_LABORATORIES` | `100000009` | `Quest09Laboratories` | 109 | (dynamic) |
| `QUEST_10_SPECIAL_OPS` | `100000010` | `Quest10SpecialOps` | 110 | (dynamic) |
| `QUEST_11_SAVE_VILLAGES` | `100000011` | `Quest11SaveVillages` | 111 | (dynamic) |
| `QUEST_12_TANKBOSS` | `100000012` | `Quest12TankBoss` | 112 | THE MECHANICAL MENACE |
| `QUEST_13_TYRANNOSAURUS` | `100000013` | `Quest13Tyrannosaurus` | 113 | DEFEAT THE DINOSAURS |
| `QUEST_14_SPY_2` | `100000014` | `Quest14Spy2` | 114 | The River |
| `QUEST_15_HARDCORE1` | `100000017` | `Quest15HCCrusaderBase1` | 117 | VIKINGS BEACHHEAD |
| `QUEST_16_HARDCORE2` | `100000018` | `Quest16HCAliens` | 118 | KILL THE ALIENS |
| `QUEST_17_HARDCORE3` | `100000019` | `Quest17HCArachnids` | 119 | ARACHNID MENACE |
| `QUEST_18_HARDCORE4` | `100000020` | `Quest18HCDragons` | 120 | ERRADICATE THE DRAGONS |
| `QUEST_19_HARDCORE5` | `100000021` | `Quest19HC` | 121 | DR.SHOCK'S MECH ARMY |
| `QUEST_20_HARDCORE6` | `100000022` | `Quest20HC` | 122 | DR.SHOCK'S MONSTERS |
| `QUEST_21_HARDCORE7` | `100000023` | *(no class — not playable)* | 123 | — |
| `QUEST_22_HARDCORE8` | `100000024` | *(no class — not playable)* | 124 | — |
| `QUEST_22_HARDCORE9` | `100000026` | `Quest23HC` | 126 | THE WICKED NEBULARS |
| `QUEST_23_HARDCORE10` | `100000025` | `Quest24HC` | 125 | DR. SHOCK STRIKES BACK |
| `QUEST_WEEKLY_01` | `100000049` | `QuestWeekly01` | 149 | Weekly Mission! |
| `QUEST_DEFEND_CONVOY` | `100000100` | *(no class)* | — | — |

**Play order** (`Quest.questIds`, the array the reward table is indexed by):

```
[0]  QUEST_WEEKLY_01            100000049
[1]  QUEST_01_BAZOOKA           100000001
[2]  QUEST_06_AIRSTRIKE         100000006
[3]  QUEST_03_DEFEND_CONVOY_AUTO 100000003
[4]  QUEST_04_SUPERTANK         100000004
[5]  QUEST_05_ASSAULT_CONVOY    100000005
[6]  QUEST_02_CENTRAL_NUCLEAR   100000002
[7]  QUEST_07_SHIP              100000007
[8]  QUEST_08_ROCKET            100000008
[9]  QUEST_09_LABORATORIES      100000009
[10] QUEST_10_SPECIAL_OPS       100000010
[11] QUEST_11_SAVE_VILLAGES     100000011
[12] QUEST_12_TANKBOSS          100000012
[13] QUEST_13_TYRANNOSAURUS     100000013
[14] QUEST_14_SPY_2             100000014
[15] QUEST_15_HARDCORE1         100000017
[16] QUEST_16_HARDCORE2         100000018
[17] QUEST_17_HARDCORE3         100000019
[18] QUEST_18_HARDCORE4         100000020
[19] QUEST_19_HARDCORE5         100000021
[20] QUEST_20_HARDCORE6         100000022
[21] QUEST_22_HARDCORE9         100000026
[22] QUEST_23_HARDCORE10        100000025
```

`Quest.numQuests` = `questIds.length - 1` = **23** playable quests (index 0 = weekly). `Quest.getQuestId(index)` returns `questIds[index]`.

**Quest lifecycle**
1. `Quest.loadQuest(index, army)` → `setQuest(id)` (instantiates the class) → `prepareInit()` → `Base.Main.loadMap(questId, "", GAME_MODE_ASSAULT)` → `PopupLoadingQuest`.
2. `Quest.mapLoaded()` → `currentQuest.mapLoaded()`; the quest counts enemy units, classifies reinforcements / activators / key elements, and marks deco/atrezzo as neutral.
3. `Quest.start()` → `currentQuest.start()` (intro cutscene, `friendlyAreas` → `MapInitializer.convertAreaToFriendly`).
4. During play: `Quest.elementKilled(el)` → `currentQuest.elementKilled(el)` returns `[gold, xp]`; `Quest.elementCollected(el)` → `currentQuest.elementCollected(el)`.
5. `Quest.end()` → recovers units, sets `bFinished`, dispatches `questEnd` with `{id, difficulty, win}` and `questFinished`.
6. `AbstractQuest.sendResults()` → builds the JSON result and queues `CmdEndQuest` + `AdminCmdSetQuestRank`.

**Difficulty**
* `AbstractQuest._difficulty` ∈ {1,2,3}. Difficulty 1 = as authored. Difficulty 2 spawns **one extra copy** of every enemy unit next to it. Difficulty 3 spawns **two** extra copies. (`AbstractQuest.difficulty` setter: for each enemy unit, difficulty 3 adds one, then both 2 and 3 add one more.)
* `Quest.DIFFICULTY_MULTIPLIER = 0.5`.
* `Quest01Bazooka` and `Quest13Tyrannosaurus` override the `difficulty` getter (they compute their own).
* Level gates: `globals.QUESTS_MIN_LEVELS = {"100000021":40, "100000022":40, "100000025":40, "100000026":40}` (the 4 hardcore quests with teams). `Config.QUESTS_MIN_LEVEL = 4` (mutable).
* `Config.QUESTS_WITH_TEAMS = [QUEST_19_HARDCORE5, QUEST_20_HARDCORE6, QUEST_22_HARDCORE9, QUEST_23_HARDCORE10]`.

**Cooldowns**
* `Config.QUESTS_PERIOD_HOURS = 4` → `Quest._timeForNextQuestPlay(id) = 4*3600 - (now - map.questTimes[id])`.
* `Quest.timeForNextQuestPlay()` = the **max** over all quests (global gate) when `Base.Main.abTimerQuests` is true, otherwise the per-quest gate.
* The weekly quest (`QUEST_WEEKLY_01`) is available only on **Sunday** (`Utils.getWeekDayFromTimeStamp() == WEEKDAY_SUNDAY`) and at most once every 24 h.

**Victory conditions per quest family**
* `AbstractQuest.elementKilled`: killing a **key element** (`keyIds`) calls `defeat()` → immediate loss. Killing all remaining foes (`remainingFoes <= 0`) calls `enableActivator()`. If the player's army reaches 0 → `prepareQuestEnd(3)` (3 s timer) → loss.
* `QuestHardcore` (quests 15-20, 22, 23): **kill every enemy unit on the map**. `remainingFoes` counted in `mapLoaded`; `enemyKilled` decrements; at 0 → end cutscene → `CutScene.addEndQuest(true)` → win.
* `QuestWeekly01`: kill all 5 gun bots (each opens a treasure chest) within **90 s** (`TIME_LIMIT = 90`); the player army is 4 units (`ID_UNIT_BUMBLEBEE` ×2, `ID_UNIT_DREADNOUGHT` ×2) and `Quest.numPlayerUnitsNow = 100` (so the player never "loses" by attrition). End reasons: `armyKilled`, `allBotsKilled`, `timerEnd`, `playerLeft`.
* `Quest03DefendConvoyAuto`: defeat all enemies before they destroy the allied convoy.
* `Quest01Bazooka`: defeat the Orc Commander (key element). `Quest07Ship`: steal the ship then destroy the command center. `Quest08Rocket`: stop the rocket launch. `Quest09Laboratories`: get the radio, call the airstrike, destroy the labs. `Quest10SpecialOps`: steal the laptop from the bunker (kill everyone first). `Quest11SaveVillages`: steal the cargo ships and rescue the allies before the airstrike. `Quest12TankBoss`, `Quest13Tyrannosaurus`, `Quest14Spy2` (stealth, one spy only), `Quest02CentralNuclear` (blow the plant then the CC), `Quest04Supertank`, `Quest05AssaultConvoy` (kill the truck), `Quest06Airstrike` (call air reinforcements).

**Unit recovery**
`AbstractQuest.getRecoveredUnitsPercentage()` defaults to `Constants.PERCENT_UNITS_RECOVERED_ISLE = 60` (`PERCENT_UNITS_RECOVERED_BOSS = 70` exists but is not used by `AbstractQuest`).
`Quest.recoverUnits(army, pct)`:
```
totalKilled = Σ army[i][FIELD_KILLED]
lost        = totalKilled - ceil(totalKilled * pct/100)
then randomly remove up to 50 units from FIELD_RECOVERED until `lost` units are un-recovered
```
`AbstractQuest.getFreeUnits()` returns bonus units (e.g. `Quest01Bazooka`).

**Rewards**
* `AbstractQuest.sendResults()` pushes: `RewardResource(gold, Quest.iGoldGained)`, `RewardResource(xp, Quest.iXPGained)`; if the player **won**, also `globals.REWARDS_QUESTS[Quest.questIds.indexOf(Quest.idQuest)]`:
  ```
  REWARDS_QUESTS = [ {}, {g:1500,w:400}, {g:2000,w:600}, {g:2500,o:800}, {g:3000,s:1000},
                     {g:3500,w:1200}, {g:4000,o:1400}, {g:4500,s:1600}, {g:5000,o:1800},
                     {g:5500,s:2000}, {g:6000,w:2200}, {g:6500,o:2400}, {g:7000,s:2600},
                     {g:7500,w:2800}, {g:8000,o:3000}, {g:10000,s:3200}, {g:12000,w:3500},
                     {g:14000,o:3500}, {g:16000,s:3500}, {g:18000,w:3800}, {g:20000,o:4000},
                     {g:22000,s:4000}, {g:24000,w:4200} ]
  ```
  and for the `"g"` key it additionally grants `RewardResource(xp, min(round(g/4), arLevelList[level].exp_required/3))`.
* Gold/XP earned in combat (`AbstractQuest.elementKilled`): enemy buildings with `attack > 0` give 5 gold and `ceil(5*0.05) = 1` XP; enemy units give 0 gold; a non-wall building always gives at least 1 XP. The **player** can gain XP but the player-side XP is capped at `iXPGained <= iGoldGained/2` (`Quest.end`).
* `Quest.elementKilled` caps the gold at `Base.Items.globals.MAX_GOLD_QUEST` (absent from this config → the cap never triggers).
* `globals.ISLE_ORDER` = the order in which quest islands are unlocked: `["100000006","100000007","100000008","100000002","100000012","100000021","100000022","100000003","100000028","100000014","100000013","100000020","100000015","100000019","100000018","100000023","100000011","100000033"]` (note `100000028` and `100000033` have **no** class in this build).
* `PopupWeeklyQuestFinished` sends `AdminCmdSetQuestRank(String(Quest.iQuest), "1")` + `CmdEndQuest`.

**Quest rank**
`Base.Player.questsRank` is `privateState.questsRank` — a map `questIndex → difficulty` (string). `PlayerStatus.updateQuestRank(index, difficulty)` keeps the **max**. `AdminCmdSetQuestRank(index, difficulty)` syncs it to the server. `GoalCompleteQuest` uses `Base.Player.questsRank[questIds.indexOf(questId)]` to check completion.

**`end_quest` payload** (`AbstractQuest.sendResults`):
```json
{ "map": <townID>, "units": <player army array>, "win": 0|1,
  "duration": <seconds>, "voluntary_end": 0|1, "quest_id": "<quest id string>",
  "difficulty": 1|2|3 }
```
`units` entries are `[itemId, sentToBattle, A, B]` — the server computes `lost = max(0, A - B)`.

**`end_attack` payload** (`Assault.as`): `{voluntary_end, victim{name,...}, attacker{...}, resources{g,x}, honor, duration, townhall_gold, win, different_island, victim_units[], attacker_units[], resources_victim}`.

### 3.3 Quest id → name cross-check with `constants.py`

`constants.py::Quests.QUEST` (server):

| id | server name | client class | status |
| --- | --- | --- | --- |
| 100000001 | QUEST 01: BAZOOKA | `Quest01Bazooka` | OK |
| 100000002 | QUEST 02: CENTRAL_NUCLEAR | `Quest02CentralNuclear` | OK |
| 100000003 | QUEST 03: DEFEND_CONVOY_AUTO | `Quest03DefendConvoyAuto` | OK |
| 100000004 | QUEST 04: SUPERTANK | `Quest04Supertank` | OK |
| 100000005 | QUEST 05: ASSAULT_CONVOY | `Quest05AssaultConvoy` | OK |
| 100000006 | QUEST 06: AIRSTRIKE | `Quest06Airstrike` | OK |
| 100000007 | QUEST 07: SHIP | `Quest07Ship` | OK |
| 100000008 | QUEST 08: ROCKET | `Quest08Rocket` | OK |
| 100000009 | QUEST 09: LABORATORIES | `Quest09Laboratories` | OK |
| 100000010 | QUEST 10: SPECIAL_OPS | `Quest10SpecialOps` | OK |
| 100000011 | QUEST 11: SAVE_VILLAGES | `Quest11SaveVillages` | OK |
| 100000012 | QUEST 12: TANKBOSS | `Quest12TankBoss` | OK |
| 100000013 | QUEST 13: TYRANNOSAURUS | `Quest13Tyrannosaurus` | OK |
| 100000014 | QUEST 14: SPY_2 | `Quest14Spy2` | OK |
| 100000017 | QUEST 15: HARDCORE1 | `Quest15HCCrusaderBase1` | OK |
| 100000018 | QUEST 16: HARDCORE2 | `Quest16HCAliens` | OK |
| 100000019 | QUEST 17: HARDCORE3 | `Quest17HCArachnids` | OK |
| 100000020 | QUEST 18: HARDCORE4 | `Quest18HCDragons` | OK |
| 100000021 | QUEST 19: HARDCORE5 | `Quest19HC` | OK |
| 100000022 | QUEST 20: HARDCORE6 | `Quest20HC` | OK |
| 100000023 | QUEST 21: HARDCORE7 | — | server only, no client class |
| 100000024 | QUEST: ISLA_RUBEN3D | — | **server dict bug** (see below) |
| 100000025 | QUEST: ISLA_KASPAR | `Quest24HC` (HARDCORE10) | **server dict bug** |
| 100000026 | QUEST: ISLA_EGG2 | `Quest23HC` (HARDCORE9) | **server dict bug** |
| 100000027 | QUEST: ISLA_EGG1 | — | server only |
| 100000028 | QUEST: BOSS_DRAGON_1 | — | server only (also in `ISLE_ORDER`) |
| 100000049 | QUEST: WEEKLY_01 | `QuestWeekly01` | OK |
| 100000100 | QUEST: DEFEND_CONVOY | — | server only |

> **`constants.py` BUG (real, reproducible):** the `Quests.QUEST` dict literal contains **duplicate keys**. Python keeps the *last* value, so:
> * `"100000024"` resolves to `"QUEST: ISLA_RUBEN3D"` (not HARDCORE8)
> * `"100000025"` resolves to `"QUEST: ISLA_KASPAR"` (not HARDCORE10)
> * `"100000026"` resolves to `"QUEST: ISLA_EGG2"` (not HARDCORE9)
> A clone must fix this dict (or use the client's mapping, which is authoritative).

---

## 4. GOALS SYSTEM

### 4.1 Model

* `core/goals/Goal.as` (interface) + `AbstractGoal.as` (base) + 30 concrete classes.
* Each goal has: `id` (int), `currentStep`, `numSteps` (`_steps`), `active` (bool), `visited` (bool), `rewards: Vector.<AbstractReward>`, `host` (a `Character` that talks to you), `literals` (6 strings: TITLE, INTRO, DESCRIPTION, INSTRUCTIONS, HINT, COMPLETE — from `TranslationGoals`).
* `isCompleted()` = `currentStep >= numSteps`.
* `GoalManager` registers **134** goals. Only `globals.NUM_ACTIVE_MISSIONS = 5` are active at once: `checkAllGoals()` walks the list in order, activates every incomplete goal, and stops after 5 *incomplete* ones; when one completes, the next is activated.
* `GoalManager.addGoal(goal, host, reward, index?)` — the reward can be an int (→ gold) or an object (→ per-resource `RewardResource`). Every goal's reward in this build is **10 gold** (`config/main.json → goals[].reward = 10`).

### 4.2 Goal progress & persistence

* `AbstractGoal.save()` → `CmdSetGoals(id, [visited?1:0, currentStep])` → wire `set_goals` with `args = [goalId, JSON.stringify([visited, currentStep])]`.
* `AbstractGoal.initialize(data)` reads the server's `privateState.goals[id]` array: `visited = data[0] == 1`, `currentStep = parseInt(data[1])`.
* `AbstractGoal.deliverReward()` → each `AbstractReward.deliver()` then `CmdCompleteGoal(id, rewards)` → wire `complete_goal` with `args = [goalId]` and the reward deltas in `comm[3]`.
* `AbstractGoal.checkComplete()` → on completion: `complete.dispatch(this)` → `save()` → `deactivate()`.
* The server stores progress via `engine.py::set_goals(privateState, goal_id, progress)` (a sparse list, `None`-padded) and **ignores** `complete_goal` beyond printing.

### 4.3 Goal types (30 classes)

| Class | Constructor args | Completes when | Signal hooked |
| --- | --- | --- | --- |
| `GoalAction` | `(id, actionId, steps)` | `Base.Main.actionTriggered` fires with that action id | `actionTriggered` |
| `GoalAddAllies` | `(id, steps)` | the invite popup is closed | — (`onPopupclosed`) |
| `GoalAlliesMarketTrade` | `(id, {res:amount})` | the allies market delivers ≥ the requested amount of each resource | `Base.Iso.alliesMarketTrade` |
| `GoalAssistNeighbourBuilding` | `(id, steps)` | the player assists a neighbour's building `steps` times | `Base.Iso.neighbourBuildingAssisted` |
| `GoalAttackPlayer` | `(id, attacks, friendsOnly=false, victoryRequired=false)` | `Assault.attackEnd` with a non-voluntary attack, matching the friend filter and (optionally) a win | `Assault.attackEnd` |
| `GoalBuildId` | `(id, [itemIds], steps, updateOnActivate=false, storeCategory=-1, storeSubcategory=-1, storePosition=-1, trainBuilding=-1)` | that many of the listed item ids are built by the player | `Base.Iso.elementBuilt` |
| `GoalBuildProperty` | `(id, property, steps, updateOnActivate=false)` | that many buildings with the given `PropertyManager` property are built | `Base.Iso.elementBuilt` |
| `GoalCollect` | `(id, property, resourceKey, steps)` | that many elements with the property **and** `collect_type == resourceKey` are collected | `Base.Iso.elemCollected` |
| `GoalCompleteChapter` | `(id, chapterId, spawnChapter=false)` | `ChapterManager.chapterFinished` fires with that chapter id | `ChapterManager.chapterFinished` |
| `GoalCompleteQuest` | `(id, questId, minDifficulty=1, winRequired=true)` | `Quest.questEnd` for that quest with the required difficulty and (optionally) a win | `Quest.questEnd` |
| `GoalDailyBouns` | `(id, days)` | the daily bonus is won `days` times (`_currentStep` starts at 1) | `Base.Iso.dailyBounsWon` |
| `GoalDoubleClick` | `(id)` | the player double-clicks a unit | `Base.Iso.doubleClick` |
| `GoalExpand` | `(id, steps)` | that many tiles are purchased | `Base.Iso.tilePurchased` |
| `GoalHarbor` | `(id)` | the first quest is completed (also spawns 12 units + cutscene on popup close) | `Quest.questEnd` |
| `GoalMarketTrade` | `(id, {res:amount})` | the market delivers ≥ the requested amount of each resource | `Base.Iso.marketTrade` |
| `GoalModifyPlayerStats` | `(id, {res:delta})` | the player spends/gains at least that much of a resource (e.g. `{"c":-1}` = spend 1 cash) | `Base.Resources.playerStatsModified` |
| `GoalMove` | `(id, buildingProperty, steps)` | that many buildings with the property are moved | `Base.Iso.buildingMoved` |
| `GoalOpenPopup` | `(id, popupClass)` | that popup is opened | `Base.PopUp.popupOpened` |
| `GoalPopUnit` | `(id, buildingIds|property|delegate, unitIds|property, steps)` | a matching unit is popped out of a matching building | `Base.Iso.unitPopped` |
| `GoalPushUnit` | `(id, buildingIds|property|delegate, unitIds|property, steps)` | a matching unit is pushed into a matching building | `Base.Iso.unitPushed` |
| `GoalReachPopulation` | `(id, population)` | the player's current population reaches the target | `Base.Player.populationModified` |
| `GoalSelectTime` | `(id, buildingProperty, resourceKey, steps, timeIdx=0)` | a factory's collect period is set to ≥ `timeIdx` | `Base.Iso.timeSelected` |
| `GoalSocialBuildingOpened` | `(id, buildingId)` | that social building is opened (allies building / recon center) | `Base.Iso.socialBuildingOpened` |
| `GoalSpy` | `(id, steps)` | `Assault.spyEnd` with a non-voluntary spy | `Assault.spyEnd` |
| `GoalStoreItem` | `(id, itemIds|property, steps)` | that many items are stored | `Base.Iso.itemStored` |
| `GoalVisitNeighbour` | `(id, [fbid], countAll=false)` | that many (or any) neighbours are visited | `Base.Iso.neighbourVisited` |

Rewards classes (`core/goals/rewards/`): `AbstractReward`, `RewardElement` (an item), `RewardResource` (a resource id + amount).

### 4.4 Goal id → type → title (134 goals)

Titles are the **client's** `TranslationGoals` literals (authoritative for the UI). The `config/main.json → goals[]` titles differ (the config table only covers ids 1..91 and its titles are shifted).

| id | class | title |
| --- | --- | --- |
| 1 | GoalBuildId | BUILD A HOUSE |
| 3 | GoalBuildProperty | BUILD A CORN FIELD |
| 4 | GoalPushUnit | SEND WORKER TO FIELD |
| 5 | GoalCollect | CUT TREES AND GET WOOD |
| 6 | GoalAction | LET'S ZOOM! |
| 8 | GoalBuildProperty | TRAIN 2 WORKERS |
| 9 | GoalBuildId | BUILD A GOLD FACTORY |
| 10 | GoalPushUnit | SEND WORKER TO GOLD FACTORY |
| 11 | GoalSelectTime | SELECT WORKING TIME |
| 13 | GoalPopUnit | GET WORKER OUT OF GOLD FACTORY |
| 14 | GoalCollect | EXTRACT 3 STEEL |
| 16 | GoalDoubleClick | DOUBLE CLICK |
| 17 | GoalCompleteChapter | RESCUE YOUR COMRADES! (chapter 1) |
| 18 | GoalBuildId | BUILD A WOOD FACTORY |
| 19 | GoalBuildProperty | TRAIN 2 MORE WORKERS |
| 20 | GoalPushUnit | SEND 1 WORKER TO WOOD FACTORY |
| 21 | GoalCollect | COLLECT GOLD FACTORY |
| 22 | GoalBuildId | BUILD 4 MORE HOUSES |
| 23 | GoalCollect | EXTRACT 3 GOLD |
| 24 | GoalBuildId | BUILD BAZOOKA ACADEMY |
| 25 | GoalBuildId | TRAIN 3 LIGHT BAZOOKA |
| 26 | GoalHarbor | THE BAZOOKA KILLER (MISSION 1) |
| 27 | GoalBuildProperty | BUILD 3 DECORATIONS |
| 28 | GoalCollect | CHOP DOWN 7 MORE TREES |
| 29 | GoalCollect | COLLECT 10 OIL |
| 30 | GoalBuildId | BUILD 2 TURRETS NEAR COMMAND CENTER |
| 31 | GoalBuildId | BUILD A WALL |
| 32 | GoalMove | MOVE A WALL |
| 33 | GoalBuildId | BUILD A JEEP GARAGE |
| 34 | GoalBuildId | TRAIN 3 MACHINE GUN JEEPS |
| 36 | GoalBuildId | BUILD A BUNKER |
| 37 | GoalPushUnit | MOVE UNIT TO BUNKER |
| 39 | GoalBuildId | MORE SHELTER! |
| 40 | GoalVisitNeighbour | VISIT YOUR GENERAL! |
| 41 | GoalBuildId | BUILD A STEEL FACTORY |
| 42 | GoalSelectTime | SELECT STEEL TO BUILD |
| 43 | GoalPushUnit | ADD WORKER TO STEEL FACTORY |
| 44 | GoalBuildId | BUILD A MARKET |
| 45 | GoalModifyPlayerStats | SPEND 1 CASH |
| 46 | GoalBuildId | BUILD A SILO |
| 47 | GoalOpenPopup | CHECK COLLECTIONS |
| 48 | GoalDailyBouns | GET DAILY BONUS! |
| 49 | GoalReachPopulation | REACH POPULATION 40 |
| 50 | GoalCollect | HARVEST 10 GOLD VEINS |
| 51 | GoalBuildId | BUILD AN OIL FACTORY |
| 52 | GoalAttackPlayer | ATTACK A PLAYER! |
| 53 | GoalCollect | COLLECT STEEL FACTORY |
| 54 | GoalCollect | COLLECT OIL FACTORY |
| 55 | GoalMarketTrade | BUY 200 STEEL ON MARKET |
| 56 | GoalMarketTrade | BUY 100 WOOD ON MARKET |
| 57 | GoalAttackPlayer | DEFEAT A FRIEND! |
| 58 | GoalOpenPopup | CHECK ATTACKS! |
| 59 | GoalBuildId | BUILD HOUSE II |
| 60 | GoalStoreItem | STORE A DECORATION |
| 61 | GoalBuildId | OPEN RECON CENTER |
| 62 | GoalMarketTrade | SELL 100 WOOD ON MARKET |
| 63 | GoalExpand | EXPAND 1 MORE ACRE |
| 64 | GoalSpy | USE RECON CENTER |
| 65 | GoalAttackPlayer | DEFEAT 3 PLAYERS! |
| 66 | GoalCompleteQuest | BLOW UP THE NUCLEAR PLANT! (MISSION 6) |
| 67 | GoalBuildId | UPGRADE THE SOLDIER ACADEMY |
| 69 | GoalBuildId | BUILD 2 TURRET II |
| 70 | GoalBuildId | BUILD 20 WALL II |
| 71 | GoalSocialBuildingOpened | CALL FOR REINFORCEMENTS |
| 72 | GoalBuildId | UPGRADE THE BAZOOKA ACADEMY |
| 73 | GoalBuildId | TRAIN 5 BAZOOKA SOLDIERS |
| 74 | GoalCompleteChapter | RESCUE YOUR FRIEND!! (CHAPTER 2) |
| 79 | GoalBuildId | UPGRADE YOUR MARKET |
| 80 | GoalBuildProperty | BUILD 8 TURRETS |
| 81 | GoalAssistNeighbourBuilding | HELP A FRIEND! |
| 82 | GoalBuildId | UPGRADE THE CC |
| 84 | GoalAlliesMarketTrade | OBTAIN WOOD IN THE ALLIES MARKET |
| 85 | GoalAddAllies | CALL YOUR ALLIES! |
| 86 | GoalBuildId | BUILD AN ALLIES MARKET |
| 87 | GoalSelectTime | SELECT WORKING TIME (gold) |
| 88 | GoalPushUnit | SEND WORKER TO OIL FACTORY |
| 89 | GoalBuildId | TURRET III |
| 90 | GoalCompleteQuest | PROTECT THE ALLIED CONVOY! (MISSION 3) |
| 91 | GoalBuildId | GRAPE FIELD |
| 92 | GoalBuildId | RECRUITIMENT PRIZE |
| 93 | GoalBuildId | HOSPITAL |
| 94 | GoalCompleteChapter | RETRIEVE OUR JEEPS (CHAPTER 4) |
| 95 | GoalBuildId | UPGRADE YOUR WOOD FACTORY II |
| 96 | GoalCompleteQuest | DESTROY THE MEGATANK (MISSION 4) |
| 97 | GoalBuildId | BUILD TANK ACADEMY I |
| 99 | GoalBuildId | UPGRADE YOUR GOLD FACTORY |
| 100 | GoalBuildId | BUILD BUNKER II |
| 101 | GoalCompleteQuest | DESTROY THE TRUCK (MISSION 5) |
| 102 | GoalBuildId | COW FARM |
| 103 | GoalBuildId | JEEP GARAGE II |
| 104 | GoalBuildId | UPGRADE YOUR STEEL FACTORY |
| 106 | GoalBuildId | UPGRADE THE OIL FACTORY II |
| 107 | GoalBuildId | UPGRADE TO WALL III |
| 108 | GoalBuildId | HELICOPTER HANGAR I |
| 109 | GoalBuildId | HOUSE III |
| 110 | GoalCompleteQuest | CALL FOR AIR REINFORCEMENTS (MISSION 2) |
| 111 | GoalBuildId | BUNKER III |
| 112 | GoalBuildId | FORTRESS I |
| 113 | GoalBuildId | Mechanical Garage |
| 115 | GoalBuildId | UPGRADE THE SOLDIER ACADEMY |
| 116 | GoalBuildId | UPGRADE YOUR WOOD FACTORY |
| 117 | GoalBuildId | UPGRADE THE BAZOOKA ACADEMY |
| 118 | GoalCompleteQuest | STEAL THE SHIP! (MISSION 7) |
| 119 | GoalBuildId | UPGRADE YOUR GOLD FACTORY |
| 120 | GoalBuildId | UPGRADE YOUR WALLS |
| 121 | GoalBuildId | Hangar I |
| 123 | GoalBuildId | UPGRADE THE MARKET |
| 124 | GoalBuildId | UPGRADE YOUR CC III |
| 125 | GoalBuildId | UPGRADE THE STEEL FACTORY |
| 126 | GoalCompleteQuest | STOP THE ROCKET LAUNCHING! (MISSION 8) |
| 127 | GoalBuildId | UPGRADE YOUR TANK ACADEMY I |
| 129 | GoalBuildId | UPGRADE YOUR HELICOPTER HANGAR |
| 130 | GoalCompleteChapter | DEFEND FROM ASSAULT! (CHAPTER 9) |
| 131 | GoalBuildId | UPGRADE THE OIL FACTORY |
| 132 | GoalBuildId | TURRET IV |
| 133 | GoalBuildId | Jeep garage III |
| 134 | GoalCompleteQuest | DESTROY THE LABS (MISSION 9) |
| 135 | GoalBuildId | UPGRADE YOUR WALLS |
| 136 | GoalBuildId | UPGRADE YOUR HANGAR |
| 137 | GoalBuildId | UPGRADE YOUR WOOD FACTORY |
| 138 | GoalCompleteChapter | DESTROY THE MEGATANK (CHAPTER 10) |
| 139 | GoalBuildId | UPGRADE THE COMMAND CENTER IV |
| 141 | GoalBuildId | UPGRADE YOUR TANK ACADEMY |
| 142 | GoalCompleteQuest | STEAL THE LAPTOP (MISSION 10) |
| 143 | GoalBuildId | UPGRADE YOUR GOLD FACTORY |
| 144 | GoalBuildId | UPGRADE YOUR HELICOPTER HANGAR |
| 145 | GoalCompleteChapter | ELEPHANTS COMING! (CHAPTER 11) |
| 146 | GoalBuildId | UPGRADE YOUR STEEL FACTORY |
| 147 | GoalBuildId | UPGRADE THE HANGAR |
| 148 | GoalBuildId | UPGRADE THE OIL FACTORY IV |
| 149 | GoalCompleteQuest | RESCUE YOUR CITIZEN (MISSION 11) |
| 150 | GoalCompleteChapter | T-REX ASSAULT! (CHAPTER 12) |
| 151 | GoalCompleteQuest | THE KILLER ROBOT (MISSION 12) |
| 152 | GoalCompleteChapter | RESCUE THE BAZOOKA SOLDIERS! (CHAPTER 3) |

**Goal ids present in `config/main.json` but never registered by the client:** `2, 7, 12, 15, 35, 38, 68, 75, 76, 77, 78, 83` (dead config rows).
**Goal ids registered by the client but absent from `config/main.json`:** `92..152` except `98, 105, 114, 122, 128, 140`. The server's `get_attribute_from_goal_id()` returns `None` for these → the server logs `Goal 'None' progressed.`

---

## 5. GAPS / RISKS FOR A CLONE

### 5.1 Client → server commands the Python server IGNORES (32 of 94)

`command.py` prints `Unhandled command '<x>' -> args` for these. They are still **applied** to the player's resources by `engine.py::apply_resources` (which runs *before* the dispatch), but their **game state** is discarded:

| Command | Consequence for the current server |
| --- | --- |
| `accept_collect_help` | friend-assist production time is never granted |
| `apply_rewards_ranking` | ranking rewards (cash + items) are lost |
| `assist_neighbor` | **assisting a neighbour is completely non-functional**; the client also grants itself `10` gold / `3` XP per click locally, so the helper is paid by the client |
| `assist_receive` | the assisting player's reward (gold/resources) is lost |
| `attack_player` | the PvP attack is not recorded at all (only `end_attack` is) |
| `buy_resources` | the cash→resource store purchase is not recorded (but the resources are still credited) |
| `clean_attacks` | the attack log never clears |
| `clean_received_assists` | received assists never clear |
| `clear_message` | the server message is re-shown every login |
| `cross_promotion_finished` | cross-promo state never recorded |
| `exchange_cash` | cash→gold exchange: the client credits itself +2500 gold and −5 cash, and `apply_resources` applies the same delta — it *works by accident*, but the server keeps no ledger of it |
| `finish_building` | **build completion is never recorded** — the server has no notion of "building finished", so construction timers/build state are absent |
| `finish_robotic_help` | research-center friend help is lost |
| `load_map` / `save_map` / `reset` | admin/editor only |
| `modify_energy` | **the client asks for free energy on every login and never gets it**; energy is entirely server-untracked |
| `modify_position_universe` | exploration-mode position is lost |
| `place_gift` | placing a gifted building is not recorded on the server |
| `premium_upgrade` | **upgrades are not recorded** — the server still has the old building |
| `reset` / `reset_collect` / `reset_world_change` / `reset_position_univers` | wonder/collect reset, island change, universe reset — all lost |
| `sell_gift` | selling a gift gives the client the refund but the server keeps the gift in stock |
| `set_help_map` | help-island state lost |
| `set_strategy` | the defensive strategy is never stored |
| `spy_player` | spying is not recorded (only `end_attack` is) |
| `system_receive_mana` | mana grants (e.g. from level-up) are credited by `apply_resources` but not recorded in `privateState.mana` separately — actually `apply_resources` *does* update `privateState.mana`, so it is consistent |
| `system_receive_si_help` | admin only |
| `system_reset_quest` | admin only |
| `upgrade` | unit level-up is not recorded |
| `win_alliance_daily_bonus` | the alliance daily bonus is credited but the alliance bonus timer is never set |

**Priority fixes for a clone (gameplay-breaking first):** `finish_building`, `premium_upgrade`, `upgrade`, `assist_neighbor` + `assist_receive`, `attack_player` + `spy_player`, `modify_energy`, `buy_resources`, `place_gift`, `set_strategy`, `win_alliance_daily_bonus`, `clear_message`, `clean_attacks`.

### 5.2 Server-handled command the client never sends (1)

* `first_time_marketplace` — the server sets `privateState.marketPlaceFirstTime = True`. The client has no such command; the "first time in the Auction House" flag is therefore never set. Dead code on the server (or a missing client command). Note the auction house is in `auctions.py`, a separate PHP service in the original game.

### 5.3 Trust boundaries the client exploits (exploitable)

1. **The server applies the client's own resource deltas.** `engine.py::apply_resources` does `map["gold"] = max(map["gold"] + gold, 0)`. The client can send any delta vector with any command. **There is zero server-side validation of costs.** A modified client can send `buy` with `comm[3] = [0,0,0,0,0,0,0,0]` and build anything for free, or send a positive gold delta out of nowhere.
   *The original Zynga server recomputed everything; the Python clone does not. A "clone" must either (a) recompute costs server-side from `config/main.json` and ignore `comm[3]`, or (b) at minimum cross-check `comm[3]` against the expected cost of the command.*

2. **`flash_debug` overwrites the player's whole wallet.** `command.py` does `playerInfo["cash"] = cash; map["xp"] = xp; map["gold"] = gold; ...` from the client's arguments. The client sends it every 20 commands for level ≥ 10. A malicious client can set cash/gold/oil/steel/wood/xp to arbitrary values. **This is the single most exploitable hole.** It should be removed or restricted to a debug build.

3. **`set_variables`** is an admin command that sets arbitrary resources with no args and no auth check. Any client can call it. (It is meant for the admin panel but is reachable from the normal command channel.)

4. **`complete_goal` / `set_goals` are trusted.** The server stores the client's `[visited, currentStep]` verbatim. A client can mark every goal as complete and claim the 10-gold reward for all 134 goals (≈1340 gold, and every goal's `complete_goal` grants the reward delta the client declares). The server must recompute goal completion from the game state.

5. **`end_quest` / `end_attack` results are trusted.** The client reports `win`, `duration`, `voluntary_end`, `difficulty`, the number of units lost, and the loot (`resources.g`, `resources.x`) in the JSON payload. The server's `end_quest` only *removes* units (from the client-declared loss count) and records the timestamp — it never validates that the quest was actually won. A client can report `"win":1` and a huge gold reward. **The `end_quest` reward delta in `comm[3]` is what actually credits the gold** — that is entirely client-controlled.

6. **`kill` / `kill_iid` loot is client-declared.** `setResource(..., true)` (not tokenized) means the loot is reported to the server but not shown locally; the server must compute the loot. It does not.

7. **`collect` amount is client-computed.** The client computes `floor(collect * mult * (1 + 0.2*(units-1)))` and the anti-cheat check (`units > unit_capacity → 0`) is **client-side only**. A modified client can collect unlimited resources.

8. **`buy` cost is client-declared** and the `building.costs` check (`CmdBuy` throws in debug builds when a cost is negative) is client-side only.

9. **`trade_resource` / `buy_resources` / `exchange_cash` are all "client-declared" exchanges.** The market price formula is client-side.

10. **`darts_shoot_balloon` is unauthenticated.** The client tells the server which target it shot and whether it won the major prize; the server records it without checking the board state or the free-shot flag.

11. **`weekly_reward` / `win_daily_bonus` can be replayed.** The server sets `timeStampMondayBonus = now` and advances `weeklyRewardIndex`, so a replay *within the same second* is blocked for the Monday bonus — but `win_daily_bonus` has **no timestamp check at all**: a client can call it repeatedly with `args = [0, 4]` and receive 1000 gold every time (the client-side `PopupNewDaily` guard is the only thing preventing it, and the *gold delta itself* is in `comm[3]`, which the server applies blindly). The claimed hero id (`args[0]`) is also unvalidated — any item id can be injected into the store.

12. **`resurrect_hero` pays the syringe cost from the client.** If `usedSyringe == 0` the client declares the resource cost; the server does not check that the player has syringes.

13. **No `collect`/`build` timer validation.** The server has no build timers, no production timers (except `item[3] = time_now` on collect) and no energy accounting. A clone must add them.

14. **The weekly-reward cycle length differs.** The client cycles the *outer* `MONDAY_BONUS_REWARDS` list (3 entries: gold / unit / cash), while `get_weekly_reward_length()` returns the length of the **longest list** (5, the unit list) — so the server advances `weeklyRewardIndex` 0→1→2→3→4→0 while the client only ever uses indices 0,1,2. Index 3 and 4 would make the client index out of range on `param1.value[weeklyRewardIndex]` (the unit list has 5 entries so no crash, but the reward would be a unit the client never intended). **Fix:** make the server cycle over `len(MONDAY_BONUS_REWARDS)` = 3, or make the client use a 5-entry table.

15. **Market reset period mismatch.** The client resets the trade counter after `MARKET_PERIOD_HOURS = 20` h; `engine.py::reset_stuff` resets it on a **day** boundary (`now // 86400`). The client also says "Come back in 24 hours to trade more!". Pick one.

16. **`numTradesDone` overflow.** `command.py` does `map["numTradesDone"] = min(20, num_trades)` but prints `20-num_trades` (can go negative).

17. **`complete_tutorial` semantics.** The client sends `complete_tutorial(step)` for every tutorial step reached; the server only sets `completed_tutorial = 1` when `step >= 25 or step == 15`. The client stores `Base.Player.playerInfo.completed_tutorial = step + ""` locally. The two are inconsistent (the client wants the *step*, the server wants a flag).

18. **`end_quest` unit-loss semantics.** The server computes `lost = max(0, unit[2] - unit[3])` where `unit[2]` = "sent to battle" and `unit[3]` = "recovered" per the comment — but the client's `Assault.FIELD_*` layout must be checked to make sure the indices match (`FIELD_INIT`, `FIELD_KILLED`, `FIELD_RECOVERED`). **UNVERIFIED** — the field order was not confirmed in this pass.

19. **`admin_set_quest_rank` is unauthenticated** — a client can set its quest rank to difficulty 3 for any quest, which unlocks `GoalCompleteQuest` goals (`GoalCompleteQuest` reads `Base.Player.questsRank`, which the client also controls locally).

20. **`set_quest_var` is unauthenticated** — the client can write any quest variable, including `id` (the current chapter) and `ended`. A clone must whitelist the keys and the value shapes.

21. **The `idSimpleChapter` special case.** The server explicitly ignores that key, so the endless-chapter progression is client-only. The client's own copy lives in `map.currentQuestVars` (which the server stores generically) — so a clone should either honour it or remove the client's dependence on it.

### 5.4 Other risks / incomplete areas

* **`Base.Items.globals.MAX_GOLD_QUEST` is missing from `config/main.json`** → the per-quest gold cap never applies. `Quest.elementKilled` compares `Quest.iGoldGained > Base.Items.globals.MAX_GOLD_QUEST`, and `undefined` makes the comparison false.
* **`globals.SOUL_MIXER_POWERUPS_LEVELS` is missing from the config** → `CmdSoulMixerPowerups` will throw / credit NaN cash. The Atom Fusion (Soul Mixer) feature is only partly wired.
* **`globals.COLLECT_MULTIPLIER` / `COLLECT_MINUTES` are used, but `Base.getDepotState` only reads `DEPOT_LIMITS`** — the real storage cap from silos is never computed client-side; the server must own it.
* **`Config.EXP_MIN`/`EXP_MAX` = 5000** are dead values; the real curve is `levels[].exp_required`.
* **`Config.NUM_CHAPTERS = 9` but `REWARDS_CHAPTERS` has 13 entries** and `REWARDS_QUESTS` has 24 entries matching `questIds.length = 24` exactly.
* **The `chapterDefinitions` / `questFactory` / `questMaps` dictionaries are only populated for the ids listed above** — `100000023`, `100000024`, `100000027`, `100000028`, `100000033`, `100000100` have no client implementation even though the server's `Quests.QUEST` lists them and `ISLE_ORDER` references `100000028` / `100000033`.
* **The `assault` (PvP) flow is only half-implemented server-side**: `attack_player` / `spy_player` are unhandled, `end_attack` does not touch the victim, and `Config.COST_BUY_ATTACK` (30) / `COST_BUY_SPYINGS` (15) are not charged anywhere.
* **Alliance services are a separate HTTP API** (`Config.SERVICE_ALLIANCE_*`, `alliance/?method=…`) — not part of the command channel.
* **The Auction House is a separate service** (`auctions.py` server-side; `ID_BUILDING_MARKETPLACE = 261`).
* **Cross-game promotions** (`Config.CROSS_ITEMS` = Social Empires `10020`, Dragon City `10078`) are triggered by `cross_promotion_finished` — unhandled.
* **The client is the only place `Base.Items.globals` is decoded** (`GameDataManager` JSON-decodes `DEPOT_LIMITS`); a cross-platform client must reproduce `GameDataManager`'s decoding of the config (levels, items, globals, goals, darts_items, offer_packs, collections, magics, neighbor_assists, town_prices, map_prices, findable_items, level_ranking_reward, units_collections_categories, inventory_items).
