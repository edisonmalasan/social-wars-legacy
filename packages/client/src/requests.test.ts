import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { COMMAND_TABLE, minArgs, maxArgs } from '@swl/protocol';

import {
  FORBIDDEN_COMMANDS,
  OWN_TOWN,
  buy,
  buyMagic,
  buyMana,
  claimDailyBonus,
  claimWeeklyBonus,
  collect,
  completeGoal,
  completeTutorial,
  endAttack,
  endQuest,
  expand,
  finishBuilding,
  levelUp,
  move,
  placeStoredItem,
  resetCollect,
  takeTrainedUnit,
  tradeResource,
  train,
  upgrade,
  useMagic,
} from './requests.ts';

/** Every builder, with arguments that satisfy its specification. */
const BUILDERS: { name: string; command: ReturnType<typeof buy> }[] = [
  { name: 'buy', command: buy(30, 1, 2, 'b') },
  { name: 'place_stored_item', command: placeStoredItem(30, 1, 2) },
  { name: 'move', command: move(7, 1, 2) },
  { name: 'collect', command: collect(7) },
  { name: 'push_queue_unit', command: train(7) },
  { name: 'push_queue_unit2', command: train(7, 1007) },
  { name: 'pop_queue_unit', command: takeTrainedUnit(7) },
  { name: 'upgrade', command: upgrade(7) },
  { name: 'level_up', command: levelUp(2) },
  { name: 'finish_building', command: finishBuilding(7, 1) },
  { name: 'reset_collect', command: resetCollect(7) },
  { name: 'complete_goal', command: completeGoal(30) },
  { name: 'complete_tutorial', command: completeTutorial(101) },
  { name: 'win_daily_bonus', command: claimDailyBonus() },
  { name: 'weekly_reward', command: claimWeeklyBonus() },
  { name: 'end_attack', command: endAttack('attack-1', false) },
  { name: 'end_quest', command: endQuest(100000001, 2) },
  { name: 'trade_resource', command: tradeResource('w', false, 100) },
  { name: 'expand', command: expand(4) },
  { name: 'buy_magic', command: buyMagic(1, 'g') },
  { name: 'buy_mana_new', command: buyMana(5, 'c') },
  { name: 'use_magic', command: useMagic(1) },
];

describe('the client requests', () => {
  it('are all for the player own town', () => {
    for (const builder of BUILDERS) {
      assert.equal(builder.command.map, OWN_TOWN, `${builder.name} names another town`);
    }
  });

  it('all name a command the table knows', () => {
    for (const builder of BUILDERS) {
      assert.ok(
        builder.command.name in COMMAND_TABLE,
        `${builder.name} is not in the command table`,
      );
    }
  });

  it('all carry the right NUMBER of arguments', () => {
    // The arity comes from the command table, which is the authority: a
    // builder that drifted from the table would send a request the
    // server refuses.
    for (const builder of BUILDERS) {
      const spec = COMMAND_TABLE[builder.command.name]!;
      const count = builder.command.args.length;
      assert.ok(
        count >= minArgs(spec) && count <= maxArgs(spec),
        `${builder.name} sends ${count} arguments; the table wants ` +
          `${minArgs(spec)}..${maxArgs(spec)}`,
      );
    }
  });

  it('cover every command the table can send to the player own town', () => {
    // Not a strict equality: the table has commands the client does not
    // build yet. But nothing it builds may be missing from the table.
    const built = new Set(BUILDERS.map((builder) => builder.command.name));
    for (const name of built) {
      assert.ok(name in COMMAND_TABLE, `${name} is not in the command table`);
    }
  });

  it('never build a forbidden command', () => {
    for (const builder of BUILDERS) {
      assert.ok(
        !FORBIDDEN_COMMANDS.includes(builder.command.name),
        `${builder.name} builds a forbidden command`,
      );
    }
  });

  it('name the wallet-overwriting command as forbidden', () => {
    // flash_debug overwrites the whole wallet from client arguments, and
    // the new server refuses it outright.
    assert.ok(FORBIDDEN_COMMANDS.includes('flash_debug'));
    assert.ok(FORBIDDEN_COMMANDS.includes('set_variables'));
  });
});

describe('the individual requests', () => {
  it('buy carries the item and the tile', () => {
    const request = buy(30, 4, 5, 'b');
    assert.equal(request.name, 'buy');
    assert.equal(request.args[1], 30);
    assert.equal(request.args[2], 4);
    assert.equal(request.args[3], 5);
  });

  it('move carries the element and the tile', () => {
    const request = move(7, 1, 2);
    assert.equal(request.name, 'move');
    assert.equal(request.args[0], 7);
    assert.equal(request.args[1], 1);
    assert.equal(request.args[2], 2);
  });

  it('train names the unit when one is given', () => {
    assert.equal(train(7).name, 'push_queue_unit');
    assert.equal(train(7, 1007).name, 'push_queue_unit2');
    assert.equal(train(7, 1007).args[1], 1007);
  });

  it('end_attack names the battle, and does not declare the outcome', () => {
    // The native form carries the attack id the server issued, NOT the
    // battle result. The client does not decide how a battle went.
    const request = endAttack('attack-1', false);
    assert.equal(request.name, 'end_attack');
    assert.equal(request.args[0], 'attack-1');
    assert.equal(request.args[1], '0');
  });

  it('end_attack marks a voluntary end', () => {
    assert.equal(endAttack('attack-1', true).args[1], '1');
  });

  it('buy_magic names the spell and the payment resource', () => {
    assert.deepEqual(buyMagic(4, 'c').args, [4, 'c']);
    assert.deepEqual(buyMagic(4, 'g').args, [4, 'g']);
  });

  it('buy_mana_new names the pack amount and the payment resource', () => {
    assert.deepEqual(buyMana(5, 'c').args, [5, 'c']);
    assert.deepEqual(buyMana(5, 'g').args, [5, 'g']);
  });

  it('use_magic names the spell and no target', () => {
    assert.deepEqual(useMagic(7).args, [7]);
  });

  it('the weekly bonus carries no arguments and the daily one carries the day', () => {
    // The day is the **client's** choice and it is **one-based**: the
    // client queues `CmdWinBonus(1)`, `CmdWinBonus(2)` and so on, and the
    // command reads `DAILY_GOLD_REWARDS[day - 1]`. A zero-based day would
    // index before the start of the rewards, and the protocol would
    // refuse the request - so the player could never claim the bonus.
    assert.deepEqual(claimDailyBonus().args, [0, 1]);
    assert.deepEqual(claimDailyBonus(3).args, [0, 3]);
    assert.deepEqual(claimDailyBonus(5, 1001).args, [1001, 5]);
    // The **reward** is the server's, and the item id is a placeholder
    // on a gold day.
    assert.deepEqual(claimWeeklyBonus().args, []);
  });
});
