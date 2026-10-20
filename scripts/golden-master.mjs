#!/usr/bin/env node
/**
 * Group E4 — the golden-master harness.
 *
 * The rules engine is only trustworthy if it produces the *same* answer
 * every time, and if that answer is *recorded* so a change can be diffed
 * against it. This harness does both.
 *
 *   node scripts/golden-master.mjs            # check against the recorded master
 *   node scripts/golden-master.mjs --record   # re-record the master
 *   node scripts/golden-master.mjs --list     # list the scenarios
 *
 * The corpus lives in `re/data/golden-corpus.json` and the recorded answers in
 * `re/data/golden-master.json`. Both are committed, so a change to the
 * rules that alters an outcome shows up as a diff in the review, and CI
 * fails on it.
 *
 * A difference is not automatically a failure — some changes are meant to
 * change the outcome. That is a judgement call, and this harness only
 * reports it; a human decides.
 */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { resolveDamage, effectiveRange, scoreTarget, selectTarget } from '../packages/rules/src/combat.ts';
import { counterMultiplier, COUNTERS } from '../packages/rules/src/counters.ts';
import { attackPhase, buildingFiresOnFrame, shooterCount, unitFiresOnFrame } from '../packages/rules/src/battle.ts';
import { bonusesForLevel, levelForXp, levelUpCost, xpEarned, xpForLevel } from '../packages/rules/src/xp.ts';
import { collect } from '../packages/rules/src/economy.ts';
import { marketPrice, trade } from '../packages/rules/src/market.ts';
import { dailyBonusReadiness, mondayBonusState } from '../packages/rules/src/bonuses.ts';
import { upgradeCost, premiumUpgradeCost, speedUpCost } from '../packages/rules/src/building.ts';
import { simpleDamage, damageOverTime, directKillDamage } from '../packages/rules/src/damage.ts';
import { resolveSpecialAttack, SPECIAL_ATTACKS } from '../packages/rules/src/specialattacks.ts';
import { resolveServerCombat } from '../packages/rules/src/authority.ts';
import { Random, hashSeed } from '../packages/rules/src/random.ts';

const ROOT = process.cwd();
const CORPUS = path.join(ROOT, 're/data/golden-corpus.json');
const MASTER = path.join(ROOT, 're/data/golden-master.json');

/**
 * The scenario kinds. Each one takes the scenario's `input` and returns a
 * JSON-able answer.
 */
const KINDS = {
  'combat-damage': (input) => {
    const random = new Random(hashSeed(input.seed ?? 'golden'));
    const result = resolveDamage(input.attacker, input.defender, random, input.context ?? {}, {
      variance: input.variance,
    });
    return { damage: result.damage, crit: result.crit, counterMultiplier: result.counterMultiplier, stages: result.stages };
  },

  'combat-server': (input) => {
    const outcome = resolveServerCombat(input);
    return {
      damage: outcome.damage,
      crit: outcome.crit,
      variance: outcome.variance,
      defenderHealthAfter: outcome.defenderHealthAfter,
      killed: outcome.killed,
      counterMultiplier: outcome.counterMultiplier,
    };
  },

  'target-score': (input) => scoreTarget(input.candidate),

  'target-select': (input) => {
    const picked = selectTarget(input.candidates);
    return { handle: picked?.handle ?? null, score: picked ? scoreTarget(picked).score : null };
  },

  'counter': (input) =>
    counterMultiplier(input.attacker, input.targetProperties),

  'cadence': (input) => {
    const frames = [];
    for (let frame = 0; frame < input.frameCount; frame++) {
      const fires =
        input.kind === 'unit'
          ? unitFiresOnFrame(frame, input.phase, input.interval)
          : buildingFiresOnFrame(frame, input.interval);
      if (fires) frames.push(frame);
    }
    return { phase: attackPhase(input.random), frames };
  },

  'shooters': (input) => shooterCount(input.building),

  'xp-level': (input) => ({
    level: levelForXp(input.table, input.life, input.xp),
    bonuses: bonusesForLevel(input.table, input.life, levelForXp(input.table, input.life, input.xp)),
  }),

  'xp-cost': (input) => ({
    cost: levelUpCost(input.table, input.life, input.level),
    required: xpForLevel(input.table, input.life, input.level),
  }),

  'xp-earned': (input) => xpEarned(input.damage, input.targetIsUnit),

  'collect': (input) => collect(input.producer, input.periodIndex, input.periods),

  'market-price': (input) =>
    marketPrice(input.rules, input.resource, input.amount, input.tradesSoFar, input.selling ?? false),

  'market-trade': (input) => trade(input.rules, input.current, input.resource, input.amount, input.selling ?? false),

  'daily-bonus': (input) =>
    dailyBonusReadiness(input.lastBonusAt, input.now, input.tzOffsetHours),

  'monday-bonus': (input) => mondayBonusState(input.dayOfWeek, input.lastCollectedDay, input.today),

  'upgrade-cost': (input) => upgradeCost(input.oldBuilding, input.newBuilding),

  'premium-upgrade': (input) => premiumUpgradeCost(input.building, input.pricing),

  'speed-up': (input) => speedUpCost(input.remainingMs, input.rules),

  'damage-class': (input) => {
    switch (input.class) {
      case 'SimpleDamage':
        return simpleDamage(input.target, input.amount, input.context, input.filter);
      case 'DamageOverTime':
        return damageOverTime(input.target, input.total, input.ticks, input.intervalMs, input.context);
      case 'DirectKillDamage':
        return directKillDamage(input.target, input.maxLife, input.context);
      default:
        throw new Error(`unknown damage class ${input.class}`);
    }
  },

  'special-attack': (input) =>
    resolveSpecialAttack(SPECIAL_ATTACKS[input.class], input.config),
};

/**
 * Resolve a string that names a value at the root of the corpus.
 *
 * The corpus holds the shared data (the XP table, the collect periods, the
 * market rules) once, and the scenarios refer to it by name, so the data
 * cannot drift between scenarios.
 */
function resolve(value, corpus) {
  if (typeof value === 'string' && value in corpus) {
    const referenced = corpus[value];
    if (referenced && typeof referenced === 'object') {
      // Deep-copy, so a scenario cannot mutate the shared data.
      return JSON.parse(JSON.stringify(referenced));
    }
    return referenced;
  }
  if (Array.isArray(value)) {
    return value.map((item) => resolve(item, corpus));
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, item] of Object.entries(value)) {
      out[key] = resolve(item, corpus);
    }
    return out;
  }
  return value;
}

/** Run one scenario. */
function runScenario(scenario, corpus) {
  const kind = KINDS[scenario.kind];
  if (!kind) throw new Error(`unknown scenario kind ${scenario.kind}`);
  return kind(resolve(scenario.input, corpus));
}

async function main() {
  const args = process.argv.slice(2);
  const record = args.includes('--record');
  const list = args.includes('--list');

  const corpus = JSON.parse(await readFile(CORPUS, 'utf8'));

  if (list) {
    for (const scenario of corpus.scenarios) {
      console.log(`  ${scenario.id.padEnd(42)} ${scenario.kind}`);
    }
    return;
  }

  console.log(`running ${corpus.scenarios.length} golden-master scenarios...`);
  const results = {};
  for (const scenario of corpus.scenarios) {
    results[scenario.id] = runScenario(scenario, corpus);
  }

  if (record) {
    await writeFile(
      MASTER,
      JSON.stringify(
        {
          note:
            'The recorded answers of the golden-master corpus. Produced by ' +
            'scripts/golden-master.mjs --record. A difference here means the ' +
            'rules engine changed its mind.',
          corpus: corpus.scenarios.length,
          results,
        },
        null,
        1,
      ) + '\n',
      'utf8',
    );
    console.log(`recorded ${corpus.scenarios.length} scenarios -> ${MASTER}`);
    return;
  }

  // Check.
  let master;
  try {
    master = JSON.parse(await readFile(MASTER, 'utf8'));
  } catch {
    console.error(`no golden master at ${MASTER}`);
    console.error('run: node scripts/golden-master.mjs --record');
    process.exit(1);
  }

  let differences = 0;
  let missing = 0;
  for (const scenario of corpus.scenarios) {
    const expected = master.results?.[scenario.id];
    if (expected === undefined) {
      console.log(`  NEW      ${scenario.id}`);
      missing += 1;
      continue;
    }
    const actual = results[scenario.id];
    const a = JSON.stringify(actual);
    const b = JSON.stringify(expected);
    if (a !== b) {
      differences += 1;
      console.log(`  DIFFERS  ${scenario.id}`);
      console.log(`    expected: ${b}`);
      console.log(`    actual  : ${a}`);
    }
  }

  const extra = Object.keys(master.results ?? {}).filter(
    (id) => !corpus.scenarios.some((s) => s.id === id),
  );
  for (const id of extra) {
    console.log(`  REMOVED  ${id}`);
    differences += 1;
  }

  console.log('');
  console.log(`scenarios    : ${corpus.scenarios.length}`);
  console.log(`differences  : ${differences}`);
  console.log(`new          : ${missing}`);
  if (differences || missing) {
    console.log('');
    console.log('The rules engine changed its mind. If that is intended, re-record');
    console.log('the master:  node scripts/golden-master.mjs --record');
    process.exit(1);
  }
  console.log('The golden-master corpus matches. No unexplained differences.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
