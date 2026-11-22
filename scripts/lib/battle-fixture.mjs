/**
 * A deterministic, seeded large-battle fixture.
 *
 * The GPU benchmark needs a scene with **hundreds of real combatants**, and it
 * needs that scene to be the same on every run — otherwise a frame-timing
 * number is not comparable with the next one. This module builds that scene
 * from the repository's own rules and content.
 *
 * It is deliberately **pure**:
 *
 *   - no file system and no network (content is injected by the caller);
 *   - no `Date.now()` and no `Math.random()`;
 *   - every random choice comes from the rules engine's seeded `Random`;
 *   - the same `(seed, content, armySize)` always produces the same object.
 *
 * The same rule holds for the server's simulation: `simulateFixture` is just a
 * call to `simulateBattle`, so the fixture can be checked for determinism all
 * the way through the combat pipeline, not only at construction.
 *
 * Usage:
 *   import { createBattleFixture } from './lib/battle-fixture.mjs';
 *   const fixture = createBattleFixture({ seed, content: bundle.items });
 */

import { Random, hashSeed } from '../../packages/rules/src/random.ts';
import { attackPhase } from '../../packages/rules/src/battle.ts';
import { simulateBattle } from '../../packages/rules/src/simulate.ts';

/** The seed used when the caller does not supply one. */
export const DEFAULT_SEED = 'swl-large-battle-v1';

/**
 * Combatants per side. 150 + 150 is enough to stress a renderer without
 * making the fixture itself slow to build or to simulate.
 */
export const DEFAULT_ARMY_SIZE = 150;

/** A finite number, or a fallback. Content from older bundles may omit a stat. */
function num(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}

/**
 * The usable units: real content units with a life and an attack interval.
 *
 * Sorted by id before any randomness is applied, so the pool does not depend
 * on the order in which a bundle happens to list its items.
 */
function unitPool(content) {
  if (!Array.isArray(content)) {
    throw new TypeError('content must be an array of content items');
  }
  return content
    .filter(
      (item) =>
        item &&
        item.type === 'u' &&
        Number.isFinite(item.life) &&
        item.life > 0 &&
        num(item.attack_interval, 0) > 0,
    )
    .slice()
    .sort((a, b) => Number(a.id) - Number(b.id));
}

/**
 * One side of the battle: `armySize` units picked from the content pool, with
 * seeded stats, phases and grid positions.
 *
 * The two armies occupy adjacent halves of one grid, so the opposing front
 * lines are one tile apart — the closest the original's range-1 units can
 * reach. Positions, like everything else, come only from the seed.
 */
function buildArmy(prefix, pool, armySize, columns, baseTx, random) {
  const elements = [];
  for (let i = 0; i < armySize; i++) {
    const item = pool[random.int(0, pool.length - 1)];
    const attackInterval = num(item.attack_interval, 30);
    const properties =
      item.properties && typeof item.properties === 'object' ? { ...item.properties } : {};
    const life = num(item.life, 1);

    elements.push({
      id: `${prefix}-${i}`,
      kind: 'unit',
      itemId: Number(item.id),
      attack: num(item.attack, 1),
      defense: num(item.defense, 0),
      life,
      attack_range: num(item.attack_range, 1),
      attack_interval: attackInterval,
      // A unit's phase is a seeded roll in the real client too.
      phase: attackPhase(random.next()),
      health: life,
      maxLife: life,
      tx: baseTx + (i % columns),
      ty: 2 + Math.floor(i / columns),
      width: Math.max(1, num(item.width, 1)),
      height: Math.max(1, num(item.height, 1)),
      subcatFunctional: num(item.subcat_functional, 0),
      properties,
      best_against:
        typeof item.best_against === 'string' ? item.best_against : null,
      best_against_mult: num(item.best_against_mult, 1),
      collect: 0,
    });
  }
  return elements;
}

/**
 * The world snapshot the client renders for this fixture.
 *
 * A map item's tuple is `[itemId, tx, ty, unused, orientation]` — the same
 * shape the server sends and the client reads (`packages/client/src/session.ts`).
 * The keys are the map's own ids and must be unique strings.
 */
function toWorld(attackers, defenders) {
  const items = {};
  let isoId = 1;
  for (const element of [...attackers, ...defenders]) {
    items[String(isoId++)] = [element.itemId, element.tx, element.ty, 0, 0];
  }
  return {
    maps: [
      {
        id: 0,
        items,
        level: 1,
        xp: 0,
        expansions: [],
      },
    ],
    privateState: {},
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  };
}

/**
 * Build the fixture. Pure: nothing is read from disk and nothing is mutated.
 *
 * @param options.seed      the seed (string or number)
 * @param options.content   the content bundle's `items` array
 * @param options.armySize  combatants per side (default 150)
 * @returns a `battle` input for `simulateBattle` and a `world` for the client
 */
export function createBattleFixture(options = {}) {
  const {
    seed = DEFAULT_SEED,
    content,
    armySize = DEFAULT_ARMY_SIZE,
  } = options;
  if (!Number.isInteger(armySize) || armySize < 1) {
    throw new RangeError('armySize must be a positive integer');
  }

  const pool = unitPool(content);
  if (pool.length === 0) {
    throw new Error('the content has no usable units for the battle fixture');
  }

  const random = new Random(hashSeed(String(seed)));
  const columns = Math.max(1, Math.ceil(Math.sqrt(armySize)));
  const attackers = buildArmy('A', pool, armySize, columns, 2, random);
  const defenders = buildArmy('D', pool, armySize, columns, 2 + columns, random);

  // Ten seconds at 30 fps is the simulation's default; a fixture this large
  // needs longer to resolve, but still finishes quickly.
  const battle = {
    seed: String(seed),
    attackers,
    defenders,
    maxFrames: 600,
  };

  return {
    seed: String(seed),
    armySize,
    attackerCount: attackers.length,
    defenderCount: defenders.length,
    combatantCount: attackers.length + defenders.length,
    // A short, stable fingerprint of the whole battle input. FNV-1a is what
    // the rules use to turn a seed string into a number, so no extra source
    // of randomness or state is introduced here.
    fingerprint: hashSeed(JSON.stringify(battle)).toString(16).padStart(8, '0'),
    battle,
    world: toWorld(attackers, defenders),
  };
}

/**
 * Run the fixture through the rules engine's battle simulation.
 *
 * `simulateBattle` works on copies, so the fixture is unchanged and two runs
 * give byte-identical outcomes for the same seed.
 */
export function simulateFixture(fixture) {
  return simulateBattle(fixture.battle);
}
