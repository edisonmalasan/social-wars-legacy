import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';

import {
  ROSTER_DIALOG_ID,
  UNIT_XP_HINT,
  UNIT_XP_LABEL,
  UNIT_XP_LEVEL_UP,
  rosterDialog,
  rosterPanel,
  teamThumbnails,
  unitXpByItem,
  unitXpPanel,
} from './state.ts';

/** The small XP table the tests use; the rules' own row shape. */
const TABLE = [
  [0, 0, 0, 0],
  [5, 2, 20, 50],
  [10, 2, 20, 25],
  [20, 3, 20, 12],
];

function bundle(): ContentBundle {
  return {
    items: [
      {
        id: 7,
        name: 'Marine',
        type: 'u',
        group_type: 'infantry',
        training_time: 5,
        life: 100,
      } as ContentItem,
      {
        id: 8,
        name: 'Archer',
        type: 'u',
        group_type: 'ranged',
        training_time: 7,
        life: 50,
      } as ContentItem,
    ],
    levels: [],
    globals: { UNIT_XP_LEVELS_MULTIPLIERS_10: TABLE },
    categories: {},
    questEvents: {},
  } as unknown as ContentBundle;
}

/** A world whose store and placed units are the server's, never the client's. */
function world(): WorldSnapshot {
  return {
    maps: [
      {
        id: 0,
        store: { 7: 3, 8: 2 },
        items: {
          11: [7, 1, 1, 0, 0, 0, { xp: 501 }],
          12: [7, 2, 1, 0, 0, 0, { xp: 300 }],
          13: [8, 3, 1, 0, 0, 0, { xp: 251 }],
        },
      },
    ],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

describe('the unit-XP read from the server and the rules', () => {
  it('reads the highest xp the server stored for each unit type', () => {
    const read = unitXpByItem(world());
    assert.equal(read.get(7), 501, 'the higher of the two placed Marines');
    assert.equal(read.get(8), 251);
  });

  it('ignores malformed item tuples and attributes', () => {
    const malformed = world();
    malformed.maps[0]!.items['14'] = [7, 4, 1, 0, 0, 0, { xp: 'lots' }] as unknown as number[];
    malformed.maps[0]!.items['15'] = [null, 4, 1] as unknown as number[];
    const read = unitXpByItem(malformed);
    assert.equal(read.get(7), 501);
    assert.deepEqual([...read.keys()].sort(), [7, 8]);
  });

  it('uses the rules threshold, not a rounded-up guess', () => {
    const b = bundle();
    // A Marine has 100 life, so level 1 needs 5 * 100 = 500 xp. The client's
    // loop breaks on `<=`, so exactly 500 is still level zero.
    assert.equal(unitXpPanel(b, 7, 500)!.level, 0);
    assert.equal(unitXpPanel(b, 7, 501)!.level, 1);
    assert.equal(unitXpPanel(b, 7, 1001)!.level, 2);
  });

  it('draws the client\'s own literals and the rules\' bonuses', () => {
    const card = unitXpPanel(bundle(), 7, 501)!;
    assert.equal(card.title, UNIT_XP_LEVEL_UP);
    assert.equal(card.label, UNIT_XP_LABEL);
    assert.equal(card.hint, UNIT_XP_HINT);
    assert.equal(card.hint, 'Defeat enemies to level up your unit!!');
    assert.equal(card.level, 1);
    assert.equal(card.maxLevel, 3);
    assert.equal(card.stars, '★☆☆');
    assert.equal(card.attackBonus, 2);
    assert.equal(card.lifeBonusPercent, 20);
    assert.equal(card.nextLevelXp, 1000);
  });

  it('shows no next level at the maximum, with cumulative bonuses', () => {
    const card = unitXpPanel(bundle(), 7, 99_999)!;
    assert.equal(card.level, 3);
    assert.equal(card.nextLevelXp, null);
    assert.equal(card.attackBonus, 7);
    assert.equal(card.lifeBonusPercent, 60);
  });

  it('has no card for a non-unit or a malformed table', () => {
    const b = bundle();
    (b.items[0] as ContentItem).type = 'b';
    assert.equal(unitXpPanel(b, 7, 501), null);
    const empty = bundle();
    empty.globals = {};
    assert.equal(unitXpPanel(empty, 7, 501)!.level, 0);
  });
});

describe('the roster panel', () => {
  it('lists only server-accounted units with content names and rules levels', () => {
    const view = rosterPanel(bundle(), world(), 1_700_000_000);
    assert.equal(view.units.length, 2);
    assert.deepEqual(
      view.units.map((unit) => [unit.name, unit.available, unit.xp, unit.level]),
      [
        ['Marine', 5, 501, 1],
        ['Archer', 3, 251, 1],
      ],
    );
    assert.equal(view.units[0]!.card.name, 'Marine');
    assert.equal(view.teamAccepted, false);
    assert.deepEqual(view.thumbnails, []);
  });

  it('greys out a quest-excluded group without hiding the unit', () => {
    const view = rosterPanel(bundle(), world(), 0, null, ['infantry']);
    assert.equal(view.units[0]!.allowed, false);
    assert.equal(view.units[1]!.allowed, true);
    assert.equal(view.units.length, 2);
  });

  it('echoes the team the server accepted and deactivates the rest', () => {
    const view = rosterPanel(bundle(), world(), 0, [
      { unitId: 7, count: 2 },
      { unitId: 999, count: 1 },
    ]);
    assert.equal(view.teamAccepted, true);
    assert.equal(view.thumbnails.length, 2);
    assert.deepEqual(view.thumbnails[0], {
      itemId: 7,
      name: 'Marine',
      level: 1,
      count: 2,
      active: true,
    });
    assert.deepEqual(view.thumbnails[1], {
      itemId: 8,
      name: 'Archer',
      level: 1,
      count: 0,
      active: false,
    });
  });

  it('never claims a team from malformed or empty server rows', () => {
    const army = rosterPanel(bundle(), world(), 0).units;
    assert.deepEqual(teamThumbnails(army, []), []);
    assert.deepEqual(teamThumbnails(army, [{ unitId: 7, count: 0 }]), []);
    assert.deepEqual(teamThumbnails(army, [{ unitId: 7, count: -2 }]), []);
    const onlyUnknown = teamThumbnails(army, [{ unitId: 999, count: 1 }]);
    assert.equal(onlyUnknown.length, 2, 'all shown deactivated');
    assert.ok(onlyUnknown.every((thumb) => !thumb.active));
  });

  it('uses the one dialog, never a second modal', () => {
    const panel = rosterDialog();
    assert.equal(panel.id, ROSTER_DIALOG_ID);
    assert.equal(panel.kind, 'alert');
    assert.equal(panel.title, 'Your Army');
  });
});
