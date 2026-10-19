/**
 * Combat: the damage pipeline.
 *
 * This is a port of `core/isoengine/IsoFightingElement.recibirAtaque` from the
 * decompiled client, stage for stage. The stages, in order:
 *
 *   1. shield            - a shield absorbs part of the hit
 *   2. delegate veto     - a unit may refuse the attack entirely
 *   3. counter           - x best_against_mult, if the TARGET carries the
 *                          attacker's `best_against` property key
 *   4. attack modifier   - x statsModifier.attackModifier
 *   5. global multiplier - x the global multiplier
 *   6. unit xp bonus     - + the attacker's unit-XP extra attack
 *   7. siege             - the siege rules (inert in the shipped content,
 *                          because no item has scf=81)
 *   8. tutorial          - a tutorial-only damage reduction
 *   9. crit / variance   - 10% crit: (base + |variance|) x 1.5
 *  10. defence           - - the target's defence
 *  11. round             - the result is rounded
 *  12. clamp             - at least 1 damage
 *
 * Every source of randomness goes through the injected `Random`, so a battle is
 * reproducible from its seed.
 */

import type { Random } from './random.js';

/** The stat fields a combatant needs. Mirrors `core/Stats.as`. */
export interface CombatStats {
  attack: number;
  defense: number;
  life: number;
  attack_range: number;
  /** Attack interval in FRAMES at 30 fps — not seconds. */
  attack_interval: number;
  /** The fighting-type key, e.g. "ft_flying". The target is countered when it
   *  carries this key in its `properties`. */
  best_against: string | null;
  best_against_mult: number;
  /** The properties bag, which carries the fighting-type flags. */
  properties: Record<string, unknown>;
  /** A shield absorbs this fraction of the damage (0..1). */
  shield?: number;
}

/** The per-attacker tunables the pipeline needs. */
export interface CombatContext {
  /** Global damage multiplier. */
  globalMultiplier?: number;
  /** The attacking unit's XP level bonus, as a flat damage addition. */
  extraAttack?: number;
  /** The tutorial damage reduction, if the tutorial is active. */
  tutorialReduction?: number;
  /** Whether the siege rules apply. */
  siege?: { attackerScf: number; defenderScf: number; multiplier: number };
  /** Whether a critical hit is possible. */
  critChance?: number;
  /** The variance range, symmetric. The client uses +/-4. */
  variance?: number;
  /**
   * The per-unit attack modifier, from the attacking unit's stats.
   *
   * The client applies `statsModifier.attackModifier`, which is a multiplier the
   * unit's own statistics carry (buffs, hero levels, item upgrades). It is
   * injected here so this module stays free of item lookups.
   */
  attackModifier?: number;
  /**
   * Whether the defender's delegate refuses the attack outright.
   *
   * A unit that cannot be attacked at all — a garrisoned unit, a building under
   * construction — vetoes here, and the attack deals no damage.
   */
  defenderVetoes?: boolean;
}

export interface DamageOptions {
  /** The variance applied to this hit. Supplied by the caller so the whole
   *  battle can be replayed from a single roll per attack. */
  variance?: number;
}

export interface DamageResult {
  /** The damage dealt, after every stage. */
  damage: number;
  /** Whether the attack was refused by the target's delegate. */
  vetoed: boolean;
  /** Whether the hit was a critical hit. */
  crit: boolean;
  /** The counter multiplier that applied, if any. */
  counterMultiplier: number;
  /** The stages, in order, for the golden-master diff. */
  stages: { name: string; value: number }[];
}

const DEFAULTS = {
  critChance: 0.1,
  variance: 4,
} as const;

/**
 * Apply the damage pipeline.
 *
 * @param attacker  the attacking unit's stats
 * @param defender  the defending unit's stats
 * @param random    the seeded generator
 * @param context   per-attack tunables
 */
export function resolveDamage(
  attacker: CombatStats,
  defender: CombatStats,
  random: Random,
  context: CombatContext = {},
  options: DamageOptions = {},
): DamageResult {
  const stages: { name: string; value: number }[] = [];

  let damage = attacker.attack;
  stages.push({ name: 'attack', value: damage });

  // 1. Shield.
  if (attacker.shield && attacker.shield > 0) {
    damage *= 1 - attacker.shield;
    stages.push({ name: 'afterShield', value: damage });
  }

  // 2. Delegate veto. The client checks whether the defender's delegate refuses
  //    the attack; a unit that cannot be attacked at all (a garrisoned unit, a
  //    building under construction) vetoes here. The caller passes the verdict
  //    through the context so this module stays free of item lookups.
  const vetoed = context.defenderVetoes === true;
  if (vetoed) {
    stages.push({ name: 'vetoed', value: 0 });
    return { damage: 0, vetoed: true, crit: false, counterMultiplier: 1, stages };
  }

  // 3. Counter. The attacker's `best_against` names a PROPERTY KEY; if the
  //    target carries that key in its properties, the attacker's multiplier
  //    applies. This is why "Antiaircraft battery" (best_against=ft_flying,
  //    mult=20) hits any target with the ft_flying property.
  let counterMultiplier = 1;
  if (attacker.best_against && attacker.best_against_mult > 1) {
    if (attacker.best_against in defender.properties) {
      counterMultiplier = attacker.best_against_mult;
      damage *= counterMultiplier;
    }
  }
  stages.push({ name: 'afterCounter', value: damage });

  // 4. Attack modifier.
  const attackModifier = context.attackModifier ?? 1;
  if (attackModifier !== 1) {
    damage *= attackModifier;
    stages.push({ name: 'afterAttackModifier', value: damage });
  }

  // 5. Global multiplier.
  const globalMultiplier = context.globalMultiplier ?? 1;
  if (globalMultiplier !== 1) {
    damage *= globalMultiplier;
    stages.push({ name: 'afterGlobalMultiplier', value: damage });
  }

  // 6. Unit XP bonus.
  if (context.extraAttack) {
    damage += context.extraAttack;
    stages.push({ name: 'afterUnitXp', value: damage });
  }

  // 7. Siege. Inert in the shipped content, because no item carries scf=81.
  if (context.siege) {
    damage *= context.siege.multiplier;
    stages.push({ name: 'afterSiege', value: damage });
  }

  // 8. Tutorial reduction.
  if (context.tutorialReduction) {
    damage *= 1 - context.tutorialReduction;
    stages.push({ name: 'afterTutorial', value: damage });
  }

  // 9. Crit and variance.
  const critChance = context.critChance ?? DEFAULTS.critChance;
  const varianceRange = context.variance ?? DEFAULTS.variance;
  const variance = options.variance ?? random.int(-varianceRange, varianceRange);
  const crit = random.chance(critChance);
  if (crit) {
    damage = (damage + Math.abs(variance)) * 1.5;
  } else {
    damage += variance;
  }
  stages.push({ name: 'afterCrit', value: damage });

  // 10. Defence.
  damage -= defender.defense;
  stages.push({ name: 'afterDefense', value: damage });

  // 11. Round.
  damage = Math.round(damage);
  stages.push({ name: 'afterRound', value: damage });

  // 12. Clamp.
  if (damage < 1) damage = 1;
  stages.push({ name: 'final', value: damage });

  return { damage, vetoed: false, crit, counterMultiplier, stages };
}

/**
 * The attack range rule, which differs between units and buildings.
 *
 * A unit can reach `attack_range + max(0, targetWidth - 2 * attack_range)`.
 * A building uses its exact `attack_range`, measured centre to centre.
 */
export function effectiveRange(
  attacker: Pick<CombatStats, 'attack_range'>,
  targetWidth: number,
  kind: 'unit' | 'building',
): number {
  if (kind === 'building') return attacker.attack_range;
  return attacker.attack_range + Math.max(0, targetWidth - 2 * attacker.attack_range);
}

/**
 * The target-selection score.
 *
 * Lower is better. From `IsoFightingElement`:
 *
 *   score = 1000 - distance
 *         + 150 if the target is a unit
 *         + 100 if the target is the town hall
 *         +  75 if the target is collectable
 *         +  50 if the target is the attacker itself
 */
export function targetScore(options: {
  distance: number;
  isUnit?: boolean;
  isTownHall?: boolean;
  isCollectable?: boolean;
  isSelf?: boolean;
}): number {
  let score = 1000 - options.distance;
  if (options.isUnit) score += 150;
  if (options.isTownHall) score += 100;
  if (options.isCollectable) score += 75;
  if (options.isSelf) score += 50;
  return score;
}

/**
 * The attack interval, in frames at 30 fps.
 *
 * The client ticks at 30 fps and `attack_interval` counts frames. Units take a
 * random 0-4 frame phase so they do not all fire in lockstep; buildings have no
 * phase and fire in global lockstep.
 */
export function attackIntervalFrames(stats: CombatStats, random: Random): number {
  return stats.attack_interval;
}

/** The random phase a unit gets, so units desynchronise from each other. */
export function unitAttackPhase(random: Random): number {
  return random.int(0, 4);
}
