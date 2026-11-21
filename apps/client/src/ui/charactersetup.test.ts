import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';
import { DAMAGE_CLASSES } from '@swl/rules';

import {
  ATTACK_SYMBOL_DAMAGE,
  ATTACK_SYMBOL_RANGE,
  ATTACK_SYMBOL_SPEED,
  ATTACK_SYMBOL_VELOCITY,
  HOSPITAL_ASK,
  HOSPITAL_AVAILABLE,
  HOSPITAL_DESCRIPTION,
  HOSPITAL_HELP,
  HOSPITAL_HELP_BUTTON,
  HOSPITAL_MAX_UNITS,
  HOSPITAL_RESURRECT,
  HOSPITAL_RESURRECT_FOR,
  HOSPITAL_SYRINGES,
  HOSPITAL_TITLE,
  SYRINGE_ITEM_ID,
  attackSymbolsPanel,
  characterSetupDialog,
  hospitalPanel,
} from './state.ts';

function bundle(): ContentBundle {
  return {
    items: [
      {
        id: 1050,
        name: 'Medic',
        type: 'u',
        extra: { syringes: '1' },
      },
      {
        id: 1062,
        name: 'MegaBot',
        type: 'u',
        extra: { syringes: '3' },
      },
      {
        id: 1168,
        name: 'Blue Steel Draggy',
        type: 'u',
        extra: { syringes: '2' },
      },
    ],
  } as unknown as ContentBundle;
}

function world(
  deadHeroes: Record<string, number> = {},
  store: Record<string, number> = {},
): WorldSnapshot {
  return {
    maps: [{ id: 0, items: { 1: [1, 4, 4, 0, 0] }, store }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: { deadHeroes },
  } as unknown as WorldSnapshot;
}

describe('the hospital panel', () => {
  it('reads only the server deadHeroes and the content names and costs', () => {
    const view = hospitalPanel(bundle(), world({ '1050': 3, '1062': 1 }, { '35': 7 }));
    assert.equal(view.title, HOSPITAL_TITLE);
    assert.equal(view.syringesAvailable, 7);
    assert.deepEqual(
      view.dead.map((row) => ({ id: row.itemId, name: row.name, count: row.count, syringes: row.syringes })),
      [
        { id: 1050, name: 'Medic', count: 3, syringes: 1 },
        { id: 1062, name: 'MegaBot', count: 1, syringes: 3 },
      ],
    );
  });

  it('sends the catalogue resurrect_hero request, never a local revival', () => {
    const view = hospitalPanel(bundle(), world({ '1168': 2 }));
    const row = view.dead[0]!;
    assert.equal(row.resurrect.map, 0);
    assert.equal(row.resurrect.name, 'resurrect_hero');
    // A fresh iso id (the map already owns 1), neutral tile, resource cost.
    assert.deepEqual(row.resurrect.args, [2, 1168, 0, 0, 0]);
    assert.deepEqual(row.resurrectWithSyringe, {
      map: 0,
      name: 'resurrect_hero',
      args: [2, 1168, 0, 0, 1],
    });
  });

  it('skips malformed server rows instead of inventing a dead unit', () => {
    const view = hospitalPanel(
      bundle(),
      world({ '1050': 2, '0': 4, '9999': 1, bad: 5, '1062': -3, '1168': 'two' } as unknown as Record<string, number>),
    );
    assert.deepEqual(view.dead.map((row) => row.itemId), [1050]);
  });

  it('shows no units and no syringes when the save has neither', () => {
    const view = hospitalPanel(bundle(), world());
    assert.deepEqual(view.dead, []);
    assert.equal(view.syringesAvailable, 0);
  });

  it('uses the client own literals verbatim, checked against the inventory', () => {
    const inventory = JSON.parse(
      readFileSync(path.join(process.cwd(), 're/data/ui-screens.json'), 'utf8'),
    ) as { screens: { path: string; literals: string[] }[] };
    const hospital = inventory.screens.find(
      (screen) => screen.path === 'popups/PopupHospital.as',
    );
    assert.ok(hospital, 'the hospital popup is not in the inventory');
    for (const literal of [
      HOSPITAL_TITLE,
      HOSPITAL_DESCRIPTION,
      HOSPITAL_HELP,
      HOSPITAL_SYRINGES,
      HOSPITAL_AVAILABLE,
      HOSPITAL_RESURRECT_FOR,
      HOSPITAL_RESURRECT,
      HOSPITAL_MAX_UNITS,
      HOSPITAL_ASK,
      HOSPITAL_HELP_BUTTON,
    ]) {
      assert.ok(hospital!.literals.includes(literal), `not a client literal: ${literal}`);
    }
    assert.equal(SYRINGE_ITEM_ID, 35);
  });
});

describe('the attack-symbol tooltip', () => {
  it('is built only from the client literals and the rules damage classes', () => {
    const view = attackSymbolsPanel();
    assert.deepEqual(
      view.stats.map((row) => [row.symbol, row.label]),
      [
        ['uiAttack', ATTACK_SYMBOL_DAMAGE],
        ['attack_interval', ATTACK_SYMBOL_SPEED],
        ['attack_range', ATTACK_SYMBOL_RANGE],
        ['velocity', ATTACK_SYMBOL_VELOCITY],
      ],
    );
    assert.deepEqual(view.damageClasses, [...DAMAGE_CLASSES]);
  });

  it('uses the RecuadroInfo literals verbatim, checked against the inventory', () => {
    const inventory = JSON.parse(
      readFileSync(path.join(process.cwd(), 're/data/ui-screens.json'), 'utf8'),
    ) as { screens: { path: string; literals: string[] }[] };
    const recuadro = inventory.screens.find(
      (screen) => screen.path === 'GUI/RecuadroInfo.as',
    );
    assert.ok(recuadro, 'RecuadroInfo is not in the inventory');
    for (const literal of [
      ATTACK_SYMBOL_DAMAGE,
      ATTACK_SYMBOL_SPEED,
      ATTACK_SYMBOL_RANGE,
      ATTACK_SYMBOL_VELOCITY,
    ]) {
      assert.ok(recuadro!.literals.includes(literal), `not a client literal: ${literal}`);
    }
  });
});

describe('the shared dialog descriptors', () => {
  it('gives each panel a distinct id in the one dialog', () => {
    const hospital = characterSetupDialog('hospital');
    const symbols = characterSetupDialog('attack-symbols');
    assert.equal(hospital.id, 'charactersetup-hospital');
    assert.equal(symbols.id, 'charactersetup-attack-symbols');
    assert.equal(hospital.title, HOSPITAL_TITLE);
    assert.notEqual(hospital.id, symbols.id);
  });
});
