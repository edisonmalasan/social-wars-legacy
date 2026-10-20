/**
 * The client's command requests.
 *
 * Every action the player takes becomes a **request**: the client builds a
 * command, sends it with an idempotency key, and renders the server's
 * answer. It never decides the outcome itself.
 *
 * These are the builders, and they are deliberately thin. Each one produces
 * a `NativeCommand` — a name and its positional arguments, in the order
 * the command table lists them — and nothing else. There is no
 * "optimistically apply" step here, because that is the *renderer's* job
 * and it is explicitly provisional (see `predictions.ts`).
 *
 * The argument order comes from the command table, which is the
 * authority: `packages/protocol/src/commands.ts`.
 */
import type { CommandName, NativeCommand } from '@swl/protocol';

/** The client's own town. */
export const OWN_TOWN = 0;

/**
 * Build a command.
 *
 * The map is always the player's own town for now; the neighbouring
 * towns are reached through the assault commands, which carry the
 * victim's id in their own arguments.
 */
function command(name: CommandName, args: readonly unknown[]): NativeCommand {
  return { map: OWN_TOWN, name, args };
}

/** Buy a building or a unit and place it. */
export function buy(itemId: number, tx: number, ty: number, type: 'b' | 'u' | 'n'): NativeCommand {
  return command('buy', [0, itemId, tx, ty, 1, 0, 0, type]);
}

/** Put a stored building on the map. */
export function placeStoredItem(
  itemId: number,
  tx: number,
  ty: number,
  imgIndex = 0,
  unitLevel?: number,
  requiredXp?: number,
): NativeCommand {
  return command('place_stored_item', [
    0,
    itemId,
    tx,
    ty,
    1,
    0,
    0,
    imgIndex,
    ...(unitLevel === undefined ? [] : [unitLevel]),
    ...(requiredXp === undefined ? [] : [requiredXp]),
  ]);
}

/** Move a building or a unit to another tile. */
export function move(isoId: number, tx: number, ty: number, frame = 0): NativeCommand {
  return command('move', [isoId, tx, ty, frame, 'move']);
}

/**
 * Collect a building's production.
 *
 * The collect period is the **server's**: the native form carries only the
 * element's id, so the client cannot choose which period's multiplier it
 * gets.
 */
export function collect(isoId: number): NativeCommand {
  return command('collect', [isoId]);
}

/** Start training a unit. */
export function train(isoId: number, unitItemId?: number): NativeCommand {
  return unitItemId === undefined
    ? command('push_queue_unit', [isoId])
    : command('push_queue_unit2', [isoId, unitItemId]);
}

/** Take the finished unit out of the training queue. */
export function takeTrainedUnit(isoId: number): NativeCommand {
  return command('pop_queue_unit', [isoId]);
}

/** Upgrade a building to its next tier. */
export function upgrade(isoId: number): NativeCommand {
  return command('upgrade', [isoId]);
}

/** Level the player up. */
export function levelUp(newLevel: number): NativeCommand {
  return command('level_up', [newLevel]);
}

/** Hurry a build up. */
export function finishBuilding(isoId: number, clicksToBuild: number): NativeCommand {
  return command('finish_building', [isoId, clicksToBuild]);
}

/** Re-activate a depleted wonder. */
export function resetCollect(isoId: number): NativeCommand {
  return command('reset_collect', [isoId]);
}

/** Tell the server a goal is done. The server checks its own state. */
export function completeGoal(goalId: number): NativeCommand {
  return command('complete_goal', [goalId]);
}

/**
 * Claim the daily bonus.
 *
 * The item id and the day index are both the **server's**: it computes the
 * day from its own clock, and it ignores what the client claims.
 */
export function claimDailyBonus(): NativeCommand {
  return command('win_daily_bonus', [0, 0]);
}

/** Claim the weekly bonus. */
export function claimWeeklyBonus(): NativeCommand {
  return command('weekly_reward', []);
}

/**
 * Finish an attack.
 *
 * The native form carries the **attack id** the server issued, not the
 * battle result: the client does not declare the outcome of a battle, it
 * names the battle. The server re-simulates it from its own seed.
 */
export function endAttack(attackId: string, voluntaryEnd: boolean): NativeCommand {
  return command('end_attack', [attackId, voluntaryEnd ? '1' : '0']);
}

/**
 * Finish a quest.
 *
 * The difficulty is the server's to award: the client sends the quest
 * and the difficulty it *was* playing, and the server checks both
 * against its own state.
 */
export function endQuest(questId: number, difficulty: number): NativeCommand {
  return command('end_quest', [questId, difficulty]);
}

/** Trade a resource at the market. */
export function tradeResource(resource: string, selling: boolean, amount: number): NativeCommand {
  return command('trade_resource', [resource, selling ? 1 : 0, amount]);
}

/** Expand the town. */
export function expand(tileId: number): NativeCommand {
  return command('expand', [tileId]);
}

/**
 * The commands the client sends, and the ones it must never send.
 *
 * `flash_debug` overwrites the whole wallet from client arguments, and
 * the new server refuses it outright (non-negotiable 6). The list is here
 * so the client's own code cannot reach for it by accident.
 */
export const FORBIDDEN_COMMANDS: readonly CommandName[] = ['flash_debug', 'set_variables'];
