import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  EARNS_LABEL,
  RESOURCE_HINT,
  RESOURCE_TOOLTIPS,
  panelAttack,
  resourcePanel,
  resourceTooltip,
  unitPanel,
  unitTooltip,
  type UnitItem,
} from './tooltips.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
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

describe('the real content', () => {
  it('fills the panels from the bundle', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as {
      items: {
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
      }[];
    };

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
});
