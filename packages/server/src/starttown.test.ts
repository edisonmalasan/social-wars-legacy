import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  COMMAND_CENTER_ITEM_ID,
  COMMAND_CENTER_TILE,
  MAP_SIZE,
  MAX_FREE_ENERGY,
  STARTING_XP,
  initialWorld,
  startingTown,
} from './starttown.ts';

describe('the starting town', () => {
  it('has the Command Center', () => {
    const town = startingTown();
    assert.equal(Object.keys(town).length, 1);
    const tuple = town['1']!;
    assert.equal(tuple[0], COMMAND_CENTER_ITEM_ID);
  });

  it('puts it in the middle of the map, with room around it', () => {
    const tuple = startingTown()['1']!;
    assert.equal(tuple[1], COMMAND_CENTER_TILE.x);
    assert.equal(tuple[2], COMMAND_CENTER_TILE.y);
    // Four tiles wide, so the town has room on every side.
    assert.ok(tuple[1]! >= 4);
    assert.ok(tuple[2]! >= 4);
    assert.ok(tuple[1]! + 4 < MAP_SIZE);
    assert.ok(tuple[2]! + 4 < MAP_SIZE);
  });

  it('speaks the upstream\'s tuple shape', () => {
    const tuple = startingTown()['1']!;
    // [itemId, x, y, timestamp, orientation, store, attrs, owner]
    assert.equal(tuple.length, 8);
    assert.equal(typeof tuple[0], 'number');
    assert.equal(typeof tuple[1], 'number');
    assert.equal(typeof tuple[2], 'number');
    assert.equal(typeof tuple[3], 'number');
    assert.equal(typeof tuple[4], 'number');
    assert.ok(Array.isArray(tuple[5]));
    assert.equal(typeof tuple[6], 'object');
    assert.equal(tuple[7], 1);
  });

  it('gives the Command Center the attribute bag the rules read', () => {
    const attrs = startingTown()['1']![6]!;
    assert.equal(attrs['width'], 4);
    assert.equal(attrs['height'], 4);
    assert.equal(attrs['collect'], 0);
    assert.equal(attrs['unitsInside'], 0);
  });
});

describe('a new player', () => {
  it('gets the town, the resources and the command counter', () => {
    const world = initialWorld('somebody');
    assert.equal(world.save.playerInfo['pid'], 'somebody');
    const map = world.save.maps[0]!;
    assert.equal(Object.keys(map['items'] as object).length, 1);
    assert.equal(world.resources.g, 2000);
    assert.equal(world.resources.e, MAX_FREE_ENERGY);
    assert.equal(world.nextCommandNumber, 1);
  });

  it('starts at the first level, with the XP the original starts with', () => {
    const map = initialWorld('somebody').save.maps[0]!;
    assert.equal(map['level'], 1);
    assert.equal(map['xp'], STARTING_XP);
  });

  it('starts with no dark matter and no spells', () => {
    const state = initialWorld('somebody').save.privateState;
    assert.equal(state['mana'], 0);
    assert.deepEqual(state['magics'], {});
  });
});
