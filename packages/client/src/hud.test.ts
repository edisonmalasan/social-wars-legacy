import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  armyText,
  energyDisplay,
  experiencePopover,
  formatNumber,
  populationPopover,
  resourcePopover,
  type HudState,
} from './hud.ts';

const STATE: HudState = {
  gold: 1234567,
  maxGold: 2000000,
  wood: 500,
  maxWood: 1000,
  oil: 100,
  maxOil: 1000,
  steel: 0,
  maxSteel: 1000,
  cash: 250,
  population: 30,
  populationMaxCurrent: 40,
  populationMaxAllowed: 175,
  level: 12,
  experience: 40,
  expRequired: 100,
  energy: 10,
  maxEnergy: 50,
};

describe('the number formatting', () => {
  it('groups the digits in threes', () => {
    assert.equal(formatNumber(0), '0');
    assert.equal(formatNumber(7), '7');
    assert.equal(formatNumber(999), '999');
    assert.equal(formatNumber(1000), '1,000');
    assert.equal(formatNumber(1234567), '1,234,567');
    assert.equal(formatNumber(1000000), '1,000,000');
  });

  it('groups a negative number the same way the client does', () => {
    // The client groups the STRING, so the sign ends up inside the first
    // group.
    assert.equal(formatNumber(-1234), '-1,234');
  });
});

describe('the resource popovers', () => {
  it('says what the player has and what it fits in', () => {
    const popover = resourcePopover(STATE, 'gold');
    assert.equal(popover.firstLine, 'You have 1,234,567 / 2,000,000 of gold');
    assert.equal(popover.warningLine, null);
  });

  it('warns when the resource is full', () => {
    const state = { ...STATE, oil: 1000 };
    const popover = resourcePopover(state, 'oil');
    assert.equal(popover.warningLine, 'Build more Silos to get more space');
  });

  it('gives the cash no maximum and no warning', () => {
    const popover = resourcePopover(STATE, 'cash');
    assert.equal(popover.firstLine, 'You have 250 of cash');
    assert.equal(popover.warningLine, null);
  });

  it('does not warn when the resource is below its maximum', () => {
    assert.equal(resourcePopover(STATE, 'wood').warningLine, null);
  });
});

describe('the population popover', () => {
  it('says what the player uses and what it fits in', () => {
    const popover = populationPopover(STATE);
    assert.ok(popover.firstLine.startsWith('You have 30 / 40 of population'));
    assert.ok(popover.firstLine.includes('Build more houses to increase this limit'));
    assert.equal(popover.warningLine, null);
  });

  it('warns when the population is at the level limit', () => {
    const state = { ...STATE, population: 40 };
    const popover = populationPopover(state);
    assert.equal(popover.warningLine, 'Build more Houses to get more population');
  });

  it('says the max population when the absolute limit is reached', () => {
    const state = { ...STATE, population: 175 };
    const popover = populationPopover(state);
    assert.equal(popover.firstLine, "You've reached the max population");
    assert.ok(popover.warningLine?.startsWith('Reach level 13 to get an increase of'));
  });
});

describe('the experience popover', () => {
  it('says how much XP is left to the next level', () => {
    const popover = experiencePopover(STATE);
    assert.equal(popover.firstLine, 'You need 60 XP to reach level 13');
  });
});

describe('the army text', () => {
  it('is the population over the limit', () => {
    assert.equal(armyText(STATE), '30/40');
  });
});

describe('the energy display', () => {
  it('is the fraction of the bar that is full', () => {
    const display = energyDisplay({ ...STATE, energy: 25, maxEnergy: 50 });
    assert.equal(display.fraction, 0.5);
    assert.equal(display.low, false);
  });

  it('warns when the energy is low', () => {
    const display = energyDisplay({ ...STATE, energy: 5, maxEnergy: 50 });
    assert.equal(display.fraction, 0.1);
    assert.equal(display.low, true);
  });

  it('never goes below zero or above one', () => {
    assert.equal(energyDisplay({ ...STATE, energy: -5, maxEnergy: 50 }).fraction, 0);
    assert.equal(energyDisplay({ ...STATE, energy: 500, maxEnergy: 50 }).fraction, 1);
  });
});
