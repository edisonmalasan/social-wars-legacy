import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  EARNS_LABEL,
  RESOURCE_HINT,
  RESOURCE_TOOLTIPS,
  iconPanelTooltip,
  literalText,
  marketplaceUnitTip,
  panelAttack,
  resourcePanel,
  resourceTooltip,
  specialAttackTooltip,
  unitPanel,
  unitTooltip,
  type UnitItem,
} from './tooltips.ts';
import { parseXpTable, type XpLevelRow } from '@swl/rules';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface BundleItem {
  id: number;
  name: string;
  type: string;
  collect?: number;
  collect_type?: string;
  attack?: number;
  life?: number;
  attack_interval?: number;
  attack_range?: number;
  velocity?: number;
  population?: number;
}

interface ContentBundle {
  items: BundleItem[];
  globals: { UNIT_XP_LEVELS_MULTIPLIERS_10: unknown };
}

async function readBundle(): Promise<ContentBundle> {
  return JSON.parse(
    await readFile(
      path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
      'utf8',
    ),
  ) as ContentBundle;
}

describe('the resource tooltips', () => {
  it('are the client own sentences', () => {
    assert.equal(
      RESOURCE_TOOLTIPS.energy,
      'Food: Used to feed units',
    );
    assert.equal(
      RESOURCE_TOOLTIPS.wood,
      'Wood: Used to build basic constructions',
    );
    assert.equal(
      RESOURCE_TOOLTIPS.steel,
      'Stone: Used to build defensive constructions',
    );
    assert.equal(
      RESOURCE_TOOLTIPS.gold,
      'Gold: Used to pay military units',
    );
  });

  it('are found by the resource key', () => {
    assert.equal(resourceTooltip('wood'), RESOURCE_TOOLTIPS.wood);
    assert.equal(resourceTooltip('e'), null);
    assert.equal(resourceTooltip('m'), null);
  });
});

describe('the resource building panel', () => {
  it('shows the name, the resource and the amount', () => {
    const panel = resourcePanel({
      name: 'Wood Factory',
      collect_type: 'w',
      collect: 150,
    });
    assert.equal(panel.kind, 'resource');
    assert.equal(panel.name, 'Wood Factory');
    assert.equal(panel.resource, 'w');
    assert.equal(panel.earns, 150);
  });

  it('shows the client own literals', () => {
    const panel = resourcePanel({
      name: 'Wood Factory',
      collect_type: 'w',
      collect: 150,
    });
    assert.equal(panel.earnsLabel, EARNS_LABEL);
    assert.equal(panel.earnsLabel, 'Earns:');
    assert.equal(panel.hint, RESOURCE_HINT);
    assert.equal(
      panel.hint,
      'Select a peasant and click this resource to harvest it.',
    );
  });
});

describe('the unit panel', () => {
  const unit: UnitItem = {
    name: 'Soldier I',
    attack: 20,
    life: 50,
    attack_interval: 35,
    attack_range: 5,
    velocity: 1,
    population: 1,
  };

  it('shows the unit own statistics', () => {
    const panel = unitPanel(unit);
    assert.equal(panel.kind, 'unit');
    assert.equal(panel.name, 'Soldier I');
    assert.equal(panel.attackRange, 5);
    assert.equal(panel.velocity, 1);
    assert.equal(panel.life, 50);
    assert.equal(panel.population, 1);
  });

  it('puts the attack interval in the defence slot, as the client does', () => {
    // The client does this in both the tooltip and the extended portrait,
    // so it is the client's behaviour and not a slip in one of them.
    const panel = unitPanel(unit);
    assert.equal(panel.attackInterval, 35);
    assert.equal((panel as unknown as { defense: number }).defense, undefined);
  });

  it('shows the effective attack when it is given', () => {
    assert.equal(unitPanel(unit, 33).attack, 33);
    assert.equal(unitPanel(unit).attack, 20);
  });

  it('carries the special description only when there is one', () => {
    assert.equal(unitPanel(unit).specialDescription, undefined);
    assert.equal(unitPanel(unit, 20, 'A special unit.').specialDescription, 'A special unit.');
  });
});

describe('the unit tooltip', () => {
  const unit: UnitItem = {
    name: 'Soldier I',
    attack: 20,
    life: 50,
    attack_interval: 35,
    attack_range: 5,
    velocity: 1,
    population: 1,
  };

  it('shows the life and the population too', () => {
    const tooltip = unitTooltip(unit);
    assert.equal(tooltip.life, 50);
    assert.equal(tooltip.population, 1);
    assert.equal(tooltip.attackInterval, 35);
    assert.equal(tooltip.attackRange, 5);
  });

  it('shows the effective attack when it is given', () => {
    assert.equal(unitTooltip(unit, 44).attack, 44);
  });
});

describe('the attack the panel shows', () => {
  it('is the effective attack times the match-up bonus', () => {
    assert.equal(panelAttack(20, 1.5), '30');
    assert.equal(panelAttack(20, 1), '20');
    assert.equal(panelAttack(20, 2), '40');
  });

  it('adds the XP level extra attack as text', () => {
    assert.equal(panelAttack(20, 1.5, 5), '30+5');
    assert.equal(panelAttack(20, 1, 0), '20');
  });
});

describe('the literal parameters', () => {
  it('fills #0# the way the client does', () => {
    assert.equal(literalText('Play #0#!', ['Dragon City']), 'Play Dragon City!');
    assert.equal(literalText('Max #0# drones', [3]), 'Max 3 drones');
    assert.equal(literalText('No tokens'), 'No tokens');
  });
});

describe('the icon panel tooltips', () => {
  it('keeps the client own sentences', () => {
    assert.equal(iconPanelTooltip('dailyBonus'), 'Get your daily Bonus!');
    assert.equal(iconPanelTooltip('mondayBonus'), 'Get your Monday Bonus!');
    assert.equal(iconPanelTooltip('dragonCityMobile'), 'Dragon City Mobile');
  });

  it('fills the cross-promotion game name', () => {
    assert.equal(
      iconPanelTooltip('gameCrossPromotion', ['Dragon City']),
      'Play Dragon City!',
    );
  });

  it('has none for the buttons that pass no text', () => {
    for (const button of ['offer', 'video', 'facebookPromotion']) {
      assert.equal(iconPanelTooltip(button), null, button);
    }
  });
});

describe('the special attack tooltips', () => {
  it('is the sentence when the attack has one', () => {
    assert.equal(specialAttackTooltip({ tooltip: 'Spawn drone' }), 'Spawn drone');
  });

  it('is null when the attack has none', () => {
    assert.equal(specialAttackTooltip({ tooltip: '' }), null);
    assert.equal(specialAttackTooltip({ tooltip: null }), null);
    assert.equal(specialAttackTooltip({}), null);
  });

  it('fills the seconds token', () => {
    assert.equal(
      specialAttackTooltip({ tooltip: 'Adds extra power for #0# seconds!' }, [11]),
      'Adds extra power for 11 seconds!',
    );
  });
});

describe('the marketplace unit tip', () => {
  const table: XpLevelRow[] = parseXpTable([
    [0, 0, 0, 0],
    [5, 2, 20, 50],
    [10, 2, 20, 25],
    [20, 3, 20, 12],
    [40, 3, 20, 6],
  ]);
  const worker: UnitItem = {
    name: 'Worker I',
    attack: 6,
    life: 25,
    attack_interval: 35,
    attack_range: 1,
    velocity: 5,
    population: 1,
  };

  it('shows the listing one level low', () => {
    const tip = marketplaceUnitTip(worker, 4, table);
    // Tier 4 is evaluated as level 3: +2+2+3 attack and three 20% life steps.
    assert.equal(tip.attack, 13);
    assert.equal(tip.life, 40);
  });

  it('shows no bonus at tier 1', () => {
    const tip = marketplaceUnitTip(worker, 1, table);
    assert.equal(tip.attack, 6);
    assert.equal(tip.life, 25);
  });

  it('truncates the extra life at each level, not the total', () => {
    const seven: UnitItem = { ...worker, life: 7 };
    const tip = marketplaceUnitTip(seven, 4, table);
    // 7 * 20% is 1.4; three levels add 1 each, not floor(4.2) = 4.
    assert.equal(tip.life, 10);
  });

  it('keeps the base range, population, velocity and interval', () => {
    const tip = marketplaceUnitTip(worker, 4, table);
    assert.equal(tip.attackRange, 1);
    assert.equal(tip.population, 1);
    assert.equal(tip.velocity, 5);
    assert.equal(tip.attackInterval, 35);
  });
});

describe('the extracted attack table', () => {
  it('records the tooltip and the cannot message', async () => {
    const data = JSON.parse(
      await readFile(
        path.join(repoRoot(), 're/data/unit-behaviour.json'),
        'utf8',
      ),
    ) as {
      units: {
        attacks: {
          index: number | null;
          kind: string;
          name: string | null;
          icon: string | null;
          handler: string | null;
          cantMessage: string | null;
          tooltip: string | null;
        }[];
      }[];
    };
    const attacks = data.units.flatMap((unit) => unit.attacks);
    assert.equal(attacks.length, 478);

    assert.deepEqual(
      attacks.find((attack) => attack.name === 'Acid Rain'),
      {
        index: 0,
        kind: 'SpecialUnitAttack',
        name: 'Acid Rain',
        icon: 'btn_liquid_mech_acid_rain',
        handler: 'acidRainAttack',
        cantMessage: 'No target',
        tooltip: 'Acid Rain',
      },
    );

    const direct = attacks.filter((attack) => attack.kind !== 'SpecialUnitAttackCreator');
    assert.equal(direct.length, 302);
    assert.ok(
      direct.every((attack) => attack.tooltip),
      'a direct attack lost its tooltip',
    );

    const factories = attacks.filter(
      (attack) => attack.kind === 'SpecialUnitAttackCreator',
    );
    assert.equal(factories.length, 176);
    assert.ok(
      factories.every((attack) => attack.tooltip === null),
      'a factory-built attack gained a tooltip',
    );

    const templated = attacks
      .filter((attack) => attack.tooltip?.includes('#0#'))
      .map((attack) => attack.tooltip);
    assert.deepEqual(templated, [
      'Adds extra power for #0# seconds!',
      'Adds extra power for #0# seconds!',
      'Hides the Snipper for #0# seconds',
      'Hides the Snipper for #0# seconds',
    ]);
  });
});

describe('the real content', () => {
  it('fills the panels from the bundle', async () => {
    const bundle = await readBundle();

    const producers = bundle.items.filter((item) => item.collect);
    assert.ok(producers.length > 10, 'the content has no resource buildings');
    for (const item of producers) {
      const panel = resourcePanel({
        name: item.name,
        collect_type: item.collect_type ?? 'w',
        collect: item.collect ?? 0,
      });
      assert.ok(panel.earns > 0, `${item.name} earns nothing`);
      assert.ok(
        ['w', 'o', 's', 'c', 'g'].includes(panel.resource),
        `${item.name} produces ${panel.resource}`,
      );
    }

    const units = bundle.items.filter((item) => item.attack && item.life);
    assert.ok(units.length > 10, 'the content has no units');
    for (const item of units) {
      const panel = unitPanel({
        name: item.name,
        attack: item.attack ?? 0,
        life: item.life ?? 0,
        attack_interval: item.attack_interval ?? 0,
        attack_range: item.attack_range ?? 0,
        velocity: item.velocity ?? 0,
        population: item.population ?? 0,
      });
      assert.ok(panel.attack > 0, `${item.name} has no attack`);
      assert.ok(panel.life > 0, `${item.name} has no life`);
    }
  });

  it('fills the marketplace tip from the bundle', async () => {
    const bundle = await readBundle();
    const table = parseXpTable(bundle.globals.UNIT_XP_LEVELS_MULTIPLIERS_10);
    const soldier = bundle.items.find((item) => item.id === 1020);
    assert.ok(soldier, 'Soldier II is missing from the bundle');

    const tip = marketplaceUnitTip(
      {
        name: soldier.name,
        attack: soldier.attack ?? 0,
        life: soldier.life ?? 0,
        attack_interval: soldier.attack_interval ?? 0,
        attack_range: soldier.attack_range ?? 0,
        velocity: soldier.velocity ?? 0,
        population: soldier.population ?? 0,
      },
      3,
      table,
    );
    // Tier 3 is evaluated as level 2: +4 attack, and 2 x 20% of 55 life.
    assert.deepEqual(tip, {
      name: 'Soldier II',
      life: 77,
      attack: 16,
      attackRange: 6,
      population: 1,
      velocity: 5,
      attackInterval: 35,
    });
  });
});
