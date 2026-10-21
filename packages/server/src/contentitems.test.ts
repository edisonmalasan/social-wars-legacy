import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { contentItems, populationRules } from './contentitems.ts';

const BUNDLE = {
  items: [
    {
      id: 1,
      name: 'House I',
      type: 'b',
      costs: { w: 30 },
      build_time: 5,
      training_time: 0,
      clicks_to_build: 1,
      min_level: 1,
      unit_capacity: 0,
      population: 3,
      building_limit_same_id: -1,
      building_limit_same_scf: -1,
      subcategory_id: 11,
      width: 2,
      height: 2,
      trains_ids: [],
      upgrades_to: 47,
      properties: { grants_population: 1 },
    },
    {
      id: 1001,
      name: 'Soldier',
      type: 'u',
      costs: { g: 200 },
      build_time: 0,
      training_time: 60,
      clicks_to_build: 0,
      min_level: 3,
      unit_capacity: 0,
      population: 1,
      building_limit_same_id: -1,
      building_limit_same_scf: -1,
      subcategory_id: 41,
      width: 1,
      height: 1,
      trains_ids: [],
      upgrades_to: null,
      properties: {},
    },
  ],
};

describe('the content items', () => {
  it('are the bundle\'s items, by id', () => {
    const items = contentItems(BUNDLE);
    assert.equal(items.size, 2);
    const house = items.get(1)!;
    assert.equal(house.name, 'House I');
    assert.deepEqual(house.costs, { w: 30 });
    assert.equal(house.buildTime, 5);
    assert.equal(house.minLevel, 1);
    assert.equal(house.population, 3);
    assert.equal(house.subcategoryId, 11);
    assert.equal(house.width, 2);
    assert.equal(house.upgradesTo, 47);
  });

  it('know which items are units and which grant population', () => {
    const items = contentItems(BUNDLE);
    assert.equal(items.get(1)!.type, 'b');
    assert.equal(items.get(1)!.grantsPopulation, true);
    assert.equal(items.get(1001)!.type, 'u');
    assert.equal(items.get(1001)!.grantsPopulation, false);
    assert.equal(items.get(1001)!.population, 1);
  });

  it('skip an item that has no id', () => {
    const items = contentItems({ items: [{ name: 'Nameless' }, { id: 7, name: 'Seven' }] });
    assert.equal(items.size, 1);
    assert.equal(items.get(7)!.name, 'Seven');
  });

  it('tolerate a bundle with nothing in it', () => {
    assert.equal(contentItems({}).size, 0);
    assert.equal(contentItems({ items: [] }).size, 0);
  });
});

describe('the population rules', () => {
  it('are the content\'s own numbers', () => {
    const rules = populationRules({
      START_MAX_POPULATION: 20,
      MAX_POPULATION_CAP: 175,
      MAX_POPULATION_PER_LEVEL: 3,
    });
    assert.equal(rules.startMaxPopulation, 20);
    assert.equal(rules.maxPopulationCap, 175);
    assert.equal(rules.maxPopulationPerLevel, 3);
  });

  it('fall back to the game\'s own numbers', () => {
    const rules = populationRules({});
    assert.equal(rules.startMaxPopulation, 20);
    assert.equal(rules.maxPopulationCap, 175);
    assert.equal(rules.maxPopulationPerLevel, 3);
  });
});
