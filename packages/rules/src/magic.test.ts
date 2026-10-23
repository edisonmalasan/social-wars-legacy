import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  isMagicLearned,
  magicCatalogFrom,
  magicLevelGate,
  magicPrice,
  magicSpellFrom,
  magicUses,
  magicUsesMap,
  manaPack,
  manaRewardPerLevel,
  parseMagicArea,
  spellLevel,
  spellLevelThresholds,
  spellUseCap,
  type MagicSpellDefinition,
} from './magic.ts';

const GLOBALS = {
  MANA_PER_PURCHASE: 5,
  COST_MANA_CASH: 1,
  COST_MANA_GOLD: 10_000,
  NUM_SPELL_USES_LVL2: 25,
  NUM_SPELL_USES_LVL3: 50,
  MANA_REWARD_PER_LEVEL: 2,
};

const AIRSTRIKE: MagicSpellDefinition = {
  id: 1,
  name: 'AirStrike',
  description: 'Call some aircraft units to bomb the zone and turn enemies into ashes!!',
  mana: 8,
  level: 38,
  gold: 30_000,
  cash: 50,
  area: [5, 7, 9],
  target: 2,
  imgName: 'tech_airstrike',
};

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

describe('the magic catalog', () => {
  it('parses the area JSON text the config stores', () => {
    assert.deepEqual(parseMagicArea('[5,7,9]'), [5, 7, 9]);
    assert.deepEqual(parseMagicArea([5, '7', 9]), [5, 7, 9]);
    assert.deepEqual(parseMagicArea('not json'), []);
    assert.deepEqual(parseMagicArea(null), []);
  });

  it('maps one entry and skips an entry with no id', () => {
    assert.deepEqual(
      magicSpellFrom({
        id: '1',
        name: 'AirStrike',
        description: 'Call some aircraft units to bomb the zone and turn enemies into ashes!!',
        mana: '8',
        level: 38,
        gold: 30_000,
        cash: 50,
        area: '[5,7,9]',
        target: 2,
        img_name: 'tech_airstrike',
      }),
      AIRSTRIKE,
    );
    assert.equal(magicSpellFrom({ name: 'no id' }), null);
    assert.equal(magicSpellFrom(null), null);
  });

  it('indexes by id and keeps the first of a duplicate', () => {
    const catalog = magicCatalogFrom([
      { id: 1, name: 'first', mana: 8, level: 1, gold: 1, cash: 1 },
      { id: 1, name: 'second', mana: 8, level: 1, gold: 1, cash: 1 },
      { id: 2, name: 'second spell', mana: 4, level: 2, gold: 2, cash: 2 },
    ]);
    assert.equal(catalog.size, 2);
    assert.equal(catalog.get(1)?.name, 'first');
    assert.equal(catalog.get(2)?.name, 'second spell');
  });

  it('has the ten shipped spells, with usable economy fields', async () => {
    const bundle = JSON.parse(
      await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
    ) as { magics?: unknown[] };
    const catalog = magicCatalogFrom(bundle.magics ?? []);
    assert.equal(catalog.size, 10);
    for (const spell of catalog.values()) {
      assert.ok(spell.mana > 0, `spell ${spell.id} has no mana cost`);
      assert.ok(spell.level >= 1, `spell ${spell.id} has no unlock level`);
      assert.ok(spell.gold > 0, `spell ${spell.id} has no gold price`);
      assert.ok(spell.cash > 0, `spell ${spell.id} has no cash price`);
      assert.ok(spell.area.length > 0, `spell ${spell.id} has no area`);
    }
    assert.deepEqual(catalog.get(1), AIRSTRIKE);
  });
});

describe('the spell counters', () => {
  it('distinguishes "absent" from "learned but never cast"', () => {
    assert.equal(magicUses({}, 1), null);
    assert.equal(isMagicLearned({}, 1), false);
    assert.equal(magicUses({ '1': 0 }, 1), 0);
    assert.equal(isMagicLearned({ '1': 0 }, 1), true);
    assert.equal(magicUses({ '1': '0' }, 1), null);
    assert.equal(magicUses({ '1': -1 }, 1), null);
  });

  it('copies the map before a caller mutates it', () => {
    const original = { '1': 3, '2': 49, bad: 'x', negative: -1 };
    const copy = magicUsesMap(original);
    assert.deepEqual(copy, { '1': 3, '2': 49 });
    copy['1'] = 4;
    assert.equal(original['1'], 3);
  });

  it('derives spell levels at 25 and 50 uses', () => {
    assert.equal(spellLevel(null, GLOBALS), 0);
    assert.equal(spellLevel(-1, GLOBALS), 0);
    assert.equal(spellLevel(0, GLOBALS), 1);
    assert.equal(spellLevel(24, GLOBALS), 1);
    assert.equal(spellLevel(25, GLOBALS), 2);
    assert.equal(spellLevel(49, GLOBALS), 2);
    assert.equal(spellLevel(50, GLOBALS), 3);
    assert.equal(spellLevel(999, GLOBALS), 3);
  });

  it('reads both thresholds from the globals', () => {
    assert.deepEqual(spellLevelThresholds(GLOBALS), { level2: 25, level3: 50 });
    assert.deepEqual(spellLevelThresholds({}), { level2: 25, level3: 50 });
  });

  it('never lets the third threshold fall below the second', () => {
    assert.deepEqual(
      spellLevelThresholds({ NUM_SPELL_USES_LVL2: 30, NUM_SPELL_USES_LVL3: 10 }),
      { level2: 30, level3: 30 },
    );
  });

  it('caps the stored counter at the third level threshold', () => {
    assert.equal(spellUseCap(GLOBALS), 50);
    assert.equal(spellUseCap({}), 50);
    assert.equal(
      spellUseCap({ NUM_SPELL_USES_LVL2: 30, NUM_SPELL_USES_LVL3: 10 }),
      30,
    );
  });
});

describe('the magic economy', () => {
  it('reads the fixed mana pack from the globals', () => {
    assert.deepEqual(manaPack(GLOBALS), {
      amount: 5,
      price: { c: 1, g: 10_000 },
    });
  });

  it('prices a spell in the resource the command names', () => {
    assert.deepEqual(magicPrice(AIRSTRIKE, 'g'), { resource: 'g', amount: 30_000 });
    assert.deepEqual(magicPrice(AIRSTRIKE, 'c'), { resource: 'c', amount: 50 });
  });

  it('lets cash bypass the unlock level, but not gold', () => {
    assert.equal(magicLevelGate(AIRSTRIKE, 1, 'c'), true);
    assert.equal(magicLevelGate(AIRSTRIKE, 37, 'g'), false);
    assert.equal(magicLevelGate(AIRSTRIKE, 38, 'g'), true);
  });

  it('grants two mana per level by default', () => {
    assert.equal(manaRewardPerLevel(GLOBALS), 2);
    assert.equal(manaRewardPerLevel({}), 2);
  });
});
