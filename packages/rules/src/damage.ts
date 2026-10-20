/**
 * The damage classes.
 *
 * A damage class is what happens to a unit *after* it is hit. Ten of them
 * exist, and they are the difference between "it took 30 damage" and "it
 * took 30 damage and it is now burning, stunned and being pushed backwards".
 *
 * Ported from `core/generalAttacks/damages/` and
 * `core/generalAttacks/specials/AreaDamageSpecialAttack.as`.
 *
 * Everything here is a **pure function**: the damage classes take a target
 * and return a new target. The client implements them with timers, tweens
 * and colour filters, none of which a server can or should reproduce — the
 * server needs the *state change*, and the client can play the animation on
 * top of it.
 *
 * ## The common guard
 *
 * Every damage class refuses a target that is null, dead, not a unit, or
 * that fails the class's filter function:
 *
 * ```
 * return param1 != null && !param1.bDead && param1 is IsoUnit && _loc2_;
 * ```
 *
 * ## Shared damage
 *
 * `numTargets` is how many units the hit is spread across. A damage that
 * hits three units deals a third each (`damage / numTargets`), and
 * `AreaDamageSpecialAttack` uses the same division.
 */

/** A status effect on a unit. */
export type Effect =
  /** Damage over time. */
  | { kind: 'burn'; damagePerTick: number; ticksRemaining: number; intervalMs: number }
  /** Damage over time, expressed as damage per second. */
  | { kind: 'bleed'; damagePerSecond: number; secondsRemaining: number }
  /** The unit is stunned and cannot act. */
  | { kind: 'dizzy'; damagePerTick: number; ticksRemaining: number; intervalMs: number; durationMs: number }
  /** The unit is incapacitated. */
  | { kind: 'incapacitated' }
  /** The unit was pushed. */
  | { kind: 'pushed'; tiles: number }
  /** A damage that has not fired yet. */
  | { kind: 'delayed'; delayMs: number; damage: number; kindInner: string }
  /** The unit is on fire. */
  | { kind: 'incinerate'; damagePerTick: number; ticksRemaining: number; intervalMs: number };

/** A unit a damage class can be applied to. */
export interface DamageTarget {
  id: string;
  /** Only units take damage. */
  isUnit: boolean;
  isDead: boolean;
  health: number;
  maxLife: number;
  x: number;
  y: number;
  effects: Effect[];
}

/** The context a damage is applied in. */
export interface DamageContext {
  /** The attacker, for the record. */
  attackerId: string;
  /** How many units the hit is spread across. At least 1. */
  numTargets: number;
}

/** The result of applying a damage. */
export interface DamageEffectResult {
  /** Whether the damage was applied at all. */
  applied: boolean;
  /** The immediate damage dealt. 0 for a pure effect. */
  damage: number;
  /** The target's health after the damage. */
  health: number;
  /** Whether the target died. */
  dead: boolean;
  /** The target's effects after the damage. */
  effects: Effect[];
}

/** The common guard every damage class shares. */
export function canApplyDamage(
  target: DamageTarget | null,
  filter?: (target: DamageTarget) => boolean,
): boolean {
  if (!target) return false;
  if (target.isDead) return false;
  if (!target.isUnit) return false;
  if (filter && !filter(target)) return false;
  return true;
}

function share(amount: number, context: DamageContext): number {
  return amount / Math.max(1, context.numTargets);
}

function result(
  applied: boolean,
  target: DamageTarget,
  damage: number,
  effects: Effect[],
): DamageEffectResult {
  const health = Math.max(0, target.health - damage);
  return {
    applied,
    damage,
    health,
    dead: health <= 0,
    effects,
  };
}

/**
 * `SimpleDamage` — an immediate hit.
 *
 * The damage is shared across the targets when `numTargets` is above 1.
 */
export function simpleDamage(
  target: DamageTarget,
  amount: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const damage = share(amount, context);
  return result(true, target, damage, target.effects);
}

/**
 * `DamageOverTime` — a burn that ticks.
 *
 * `totalDamage` is spread over `numTicks` ticks, `tickInterval` apart.
 */
export function damageOverTime(
  target: DamageTarget,
  totalDamage: number,
  numTicks: number,
  tickIntervalMs: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const perTick = share(totalDamage, context) / Math.max(1, numTicks);
  const effect: Effect = {
    kind: 'burn',
    damagePerTick: perTick,
    ticksRemaining: numTicks,
    intervalMs: tickIntervalMs,
  };
  return result(true, target, 0, [...target.effects, effect]);
}

/**
 * `BleedingDamage` — a bleed, expressed as damage per second.
 *
 * The client calls `receiveDamageOverTime(attacker, damage / numTargets /
 * (time / 1000), time / 1000)`, so the damage is spread over the duration
 * **in seconds**.
 */
export function bleedingDamage(
  target: DamageTarget,
  amount: number,
  timeMs: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const seconds = timeMs / 1000;
  const effect: Effect = {
    kind: 'bleed',
    damagePerSecond: share(amount, context) / seconds,
    secondsRemaining: seconds,
  };
  return result(true, target, 0, [...target.effects, effect]);
}

/**
 * `IncinerateDamage` — the unit catches fire.
 *
 * `damagePerTicks` is the damage per tick, over `ticks` ticks, `ticksInterval`
 * apart.
 */
export function incinerateDamage(
  target: DamageTarget,
  damagePerTick: number,
  ticks: number,
  tickIntervalMs: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const effect: Effect = {
    kind: 'incinerate',
    damagePerTick: share(damagePerTick, context),
    ticksRemaining: ticks,
    intervalMs: tickIntervalMs,
  };
  return result(true, target, 0, [...target.effects, effect]);
}

/**
 * `DizzyDamage` — per-tick damage and a stun.
 *
 * The client computes `damagePerTick = damage / numTicks` and the effect
 * lasts `duration` ms.
 */
export function dizzyDamage(
  target: DamageTarget,
  amount: number,
  durationMs: number,
  numTicks: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const effect: Effect = {
    kind: 'dizzy',
    damagePerTick: share(amount, context) / Math.max(1, numTicks),
    ticksRemaining: numTicks,
    intervalMs: 1000,
    durationMs,
  };
  return result(true, target, 0, [...target.effects, effect]);
}

/**
 * `PushInAirDamage` — damage and a shove.
 *
 * The unit is pushed `tiles` tiles away from the attacker.
 */
export function pushInAirDamage(
  target: DamageTarget,
  amount: number,
  tiles: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const damage = share(amount, context);
  const effect: Effect = { kind: 'pushed', tiles };
  return result(true, target, damage, [...target.effects, effect]);
}

/**
 * `DirectKillDamage` — an instant kill.
 *
 * The kill only happens when the target's health is at or below
 * `maxLife`; otherwise the damage does nothing at all. The unit is also
 * incapacitated.
 */
export function directKillDamage(
  target: DamageTarget,
  maxLife: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  if (maxLife !== -1 && target.health > maxLife) {
    // The kill is conditional and the condition failed.
    return result(false, target, 0, target.effects);
  }
  const effects: Effect[] = [...target.effects, { kind: 'incapacitated' }];
  return { applied: true, damage: target.health, health: 0, dead: true, effects };
}

/**
 * `DelayedDamage` — a damage that fires later.
 *
 * The client wraps another damage class and applies it after `_delay` ms.
 */
export function delayedDamage(
  target: DamageTarget,
  innerDamage: number,
  delayMs: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const effect: Effect = {
    kind: 'delayed',
    delayMs,
    damage: share(innerDamage, context),
    kindInner: 'simple',
  };
  return result(true, target, 0, [...target.effects, effect]);
}

/**
 * `SequencedDamage` — several damages, applied in order.
 *
 * The client keeps a list and applies them one after another, tracking which
 * index each target has reached.
 */
export function sequencedDamage(
  target: DamageTarget,
  damages: readonly number[],
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  const total = damages.reduce((sum, d) => sum + share(d, context), 0);
  return result(true, target, total, target.effects);
}

/**
 * `AreaDamageSpecialAttack` — an area hit.
 *
 * The damage is **shared** across every unit the area caught, and the number
 * of units hit is capped at `numUnits`. So a hit that catches three units
 * deals `damage / 3` to each.
 */
export function areaDamage(
  target: DamageTarget,
  amount: number,
  numUnits: number,
  context: DamageContext,
  filter?: (target: DamageTarget) => boolean,
): DamageEffectResult {
  if (!canApplyDamage(target, filter)) {
    return { applied: false, damage: 0, health: target?.health ?? 0, dead: target?.isDead ?? false, effects: target?.effects ?? [] };
  }
  // The area caps the number of units it hits, and the damage is shared
  // across exactly that many.
  const shared = { ...context, numTargets: Math.max(1, Math.min(numUnits, context.numTargets)) };
  return simpleDamage(target, amount, shared, filter);
}

/** The names of the ten damage classes, for the manifest and the tests. */
export const DAMAGE_CLASSES = [
  'SimpleDamage',
  'DamageOverTime',
  'BleedingDamage',
  'DelayedDamage',
  'DirectKillDamage',
  'DizzyDamage',
  'IncinerateDamage',
  'PushInAirDamage',
  'SequencedDamage',
  'AreaDamageSpecialAttack',
] as const;

export type DamageClass = (typeof DAMAGE_CLASSES)[number];
