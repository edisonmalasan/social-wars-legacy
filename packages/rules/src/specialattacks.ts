/**
 * The fifteen special-attack classes.
 *
 * Most of a special attack is **animation**: the unit lunges, teleports,
 * beams, spins, swallows. A server does not need any of that — it needs to
 * know what the attack *does* to the world. So each class is described here
 * by its parameters and its **outcome**, and the client is left to play the
 * animation on top of the state change the server sends.
 *
 * The classes live in `core/generalAttacks/specials/`.
 *
 * | Class | What the server has to reproduce |
 * |---|---|
 * | `RegularShootSpecialAttack` | one projectile per muzzle point per animation frame; the damage per shot falls back to `uiAttack / frames / points` |
 * | `AreaDamageSpecialAttack` | area damage, shared across the units hit, capped at `numUnits` |
 * | `MeleeSpecialAttack` | damage to the current target at the animation frame; falls back to `uiAttack / frames` |
 * | `ChargeAttack` | moves `attackRange × rangeModifier` tiles and damages along the way |
 * | `GoEnemyAndComeBackSpecialAttack` | runs to the nearest enemy and back; no damage of its own |
 * | `ApproachEnemySpecialAttack` | teleports next to the nearest enemy, then area damage |
 * | `SpawnDroneSpecialAttack` | spawns up to `maxMinions` drones; the owner takes `percent × minion.maxLife` when one dies |
 * | `DeployMineSpecialAttack` | places up to `maxNumMines` neutral mines next to the owner |
 * | `EatSpecialAttack` | swallows up to `grabPoints` units lighter than itself; damage equals the attacker's own max life |
 * | `BeamAndEatSpecialAttack` | beams the nearest enemy, drags it over and consumes it; the damage lands on release |
 * | `ShootProjectilesAttack` | bursts of projectiles; area damage on landing |
 * | `ShootBombSpecialAttack` | lobs bombs; area damage of `bombRadius` on landing |
 * | `MultiLaserSpecialAttack` | beams up to `unitsPerShot` enemies |
 * | `VortexSpecialAttack` | deletes the weakest enemies and bleeds the rest |
 * | `WhirlwindSpecialAttack` | ticks `ticks` times over `duration` seconds, damaging everything in range each tick |
 */

/** The fifteen classes. */
export const SPECIAL_ATTACK_CLASSES = [
  'RegularShootSpecialAttack',
  'AreaDamageSpecialAttack',
  'MeleeSpecialAttack',
  'ChargeAttack',
  'GoEnemyAndComeBackSpecialAttack',
  'ApproachEnemySpecialAttack',
  'SpawnDroneSpecialAttack',
  'DeployMineSpecialAttack',
  'EatSpecialAttack',
  'BeamAndEatSpecialAttack',
  'ShootProjectilesAttack',
  'ShootBombSpecialAttack',
  'MultiLaserSpecialAttack',
  'VortexSpecialAttack',
  'WhirlwindSpecialAttack',
] as const;

export type SpecialAttackClass = (typeof SPECIAL_ATTACK_CLASSES)[number];

/** How a special attack hits. */
export type SpecialAttackShape =
  /** A single target. */
  | 'single'
  /** An area around the attacker or an impact point. */
  | 'area'
  /** A burst of projectiles. */
  | 'burst'
  /** A cone or line of beams. */
  | 'beam'
  /** The attacker moves. */
  | 'movement'
  /** The attacker spawns something. */
  | 'spawn'
  /** The attacker consumes the target. */
  | 'consume'
  /** Damage over time around the attacker. */
  | 'pulse';

/** What a special attack does, in the terms a server needs. */
export interface SpecialAttackSpec {
  class: SpecialAttackClass;
  /** How it hits. */
  shape: SpecialAttackShape;
  /** Does it deal damage at all? */
  dealsDamage: boolean;
  /** Does it move the attacker? */
  movesAttacker: boolean;
  /** Does it spawn units? */
  spawns: boolean;
  /** Does it change the target's position? */
  movesTarget: boolean;
}

/** The specification of each class. */
export const SPECIAL_ATTACKS: Record<SpecialAttackClass, SpecialAttackSpec> = {
  RegularShootSpecialAttack: {
    class: 'RegularShootSpecialAttack',
    shape: 'single',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  AreaDamageSpecialAttack: {
    class: 'AreaDamageSpecialAttack',
    shape: 'area',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  MeleeSpecialAttack: {
    class: 'MeleeSpecialAttack',
    shape: 'single',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  ChargeAttack: {
    class: 'ChargeAttack',
    shape: 'movement',
    dealsDamage: true,
    movesAttacker: true,
    spawns: false,
    movesTarget: false,
  },
  GoEnemyAndComeBackSpecialAttack: {
    class: 'GoEnemyAndComeBackSpecialAttack',
    shape: 'movement',
    // It runs to the nearest enemy and back; the damage is the unit's
    // ordinary attack, not a special one.
    dealsDamage: false,
    movesAttacker: true,
    spawns: false,
    movesTarget: false,
  },
  ApproachEnemySpecialAttack: {
    class: 'ApproachEnemySpecialAttack',
    shape: 'area',
    dealsDamage: true,
    movesAttacker: true,
    spawns: false,
    movesTarget: false,
  },
  SpawnDroneSpecialAttack: {
    class: 'SpawnDroneSpecialAttack',
    shape: 'spawn',
    dealsDamage: false,
    movesAttacker: false,
    spawns: true,
    movesTarget: false,
  },
  DeployMineSpecialAttack: {
    class: 'DeployMineSpecialAttack',
    shape: 'spawn',
    dealsDamage: false,
    movesAttacker: false,
    spawns: true,
    movesTarget: false,
  },
  EatSpecialAttack: {
    class: 'EatSpecialAttack',
    shape: 'consume',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: true,
  },
  BeamAndEatSpecialAttack: {
    class: 'BeamAndEatSpecialAttack',
    shape: 'consume',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: true,
  },
  ShootProjectilesAttack: {
    class: 'ShootProjectilesAttack',
    shape: 'burst',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  ShootBombSpecialAttack: {
    class: 'ShootBombSpecialAttack',
    shape: 'burst',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  MultiLaserSpecialAttack: {
    class: 'MultiLaserSpecialAttack',
    shape: 'beam',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  VortexSpecialAttack: {
    class: 'VortexSpecialAttack',
    shape: 'pulse',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
  WhirlwindSpecialAttack: {
    class: 'WhirlwindSpecialAttack',
    shape: 'pulse',
    dealsDamage: true,
    movesAttacker: false,
    spawns: false,
    movesTarget: false,
  },
};

/** The parameters a special attack is configured with. */
export interface SpecialAttackConfig {
  /** The attacker's own attack value. */
  attack: number;
  /** The animation frames the attack spans. */
  frames?: number;
  /** The number of muzzle points the attack fires from. */
  points?: number;
  /** The number of units an area attack catches. */
  numUnits?: number;
  /** The number of tiles the attack covers, for an area or a beam. */
  range?: number;
  /** The number of projectiles per burst. */
  projectilesPerBurst?: number;
  /** The number of firing points. */
  shootingPoints?: number;
  /** The number of units a beam hits. */
  unitsPerShot?: number;
  /** The radius of a bomb's blast. */
  bombRadius?: number;
  /** The number of ticks a pulse attack makes. */
  ticks?: number;
  /** How long a pulse attack lasts, in seconds. */
  durationSeconds?: number;
  /** The number of units the attack spawns. */
  maxMinions?: number;
  /** The number of mines the attack places. */
  maxNumMines?: number;
  /** The fraction of a minion's life the owner takes when it dies. */
  ownerDamagePercent?: number;
  /** The attacker's own max life, for the consume attacks. */
  maxLife?: number;
  /** The health below which the vortex deletes an enemy. */
  enemyMaxHealthToBeAbsorbed?: number;
  /** The number of enemies the vortex deletes. */
  numKills?: number;
}

/** What a special attack does to the world. */
export interface SpecialAttackOutcome {
  /** The damage dealt to each affected unit. */
  damagePerTarget: number;
  /** How many units are affected. */
  targets: number;
  /** The total damage. */
  totalDamage: number;
  /** Units the attack spawns. */
  spawns: number;
  /** How far the attacker moves, in tiles. */
  attackerMovesTiles: number;
  /** Whether the target is removed from the map. */
  consumesTarget: boolean;
}

/**
 * Resolve a special attack into its outcome.
 *
 * The damage rules are the client's own fallbacks, which is what the server
 * needs when the client does not send a per-shot figure:
 *
 * - `RegularShootSpecialAttack`: `attack / frames / points` per shot
 * - `MeleeSpecialAttack`: `attack / frames`
 * - `EatSpecialAttack`: the attacker's own max life
 * - `VortexSpecialAttack`: `attack × 0.3` as a damage-over-time, and a
 *   full `attack` on the second frame
 */
export function resolveSpecialAttack(
  spec: SpecialAttackSpec,
  config: SpecialAttackConfig,
): SpecialAttackOutcome {
  const outcome: SpecialAttackOutcome = {
    damagePerTarget: 0,
    targets: 1,
    totalDamage: 0,
    spawns: 0,
    attackerMovesTiles: 0,
    consumesTarget: false,
  };

  switch (spec.class) {
    case 'RegularShootSpecialAttack': {
      const frames = Math.max(1, config.frames ?? 1);
      const points = Math.max(1, config.points ?? 1);
      outcome.damagePerTarget = config.attack / frames / points;
      outcome.targets = points;
      break;
    }
    case 'MeleeSpecialAttack': {
      const frames = Math.max(1, config.frames ?? 1);
      outcome.damagePerTarget = config.attack / frames;
      break;
    }
    case 'AreaDamageSpecialAttack': {
      const numUnits = Math.max(1, config.numUnits ?? 1);
      outcome.damagePerTarget = config.attack / numUnits;
      outcome.targets = numUnits;
      break;
    }
    case 'ApproachEnemySpecialAttack': {
      const numUnits = Math.max(1, config.numUnits ?? 1);
      outcome.damagePerTarget = config.attack / numUnits;
      outcome.targets = numUnits;
      outcome.attackerMovesTiles = config.range ?? 0;
      break;
    }
    case 'ChargeAttack': {
      outcome.damagePerTarget = config.attack;
      outcome.attackerMovesTiles = config.range ?? 0;
      break;
    }
    case 'GoEnemyAndComeBackSpecialAttack': {
      outcome.attackerMovesTiles = config.range ?? 0;
      break;
    }
    case 'SpawnDroneSpecialAttack': {
      outcome.spawns = config.maxMinions ?? 0;
      break;
    }
    case 'DeployMineSpecialAttack': {
      outcome.spawns = config.maxNumMines ?? 0;
      break;
    }
    case 'EatSpecialAttack': {
      outcome.damagePerTarget = config.maxLife ?? config.attack;
      outcome.consumesTarget = true;
      break;
    }
    case 'BeamAndEatSpecialAttack': {
      outcome.damagePerTarget = config.attack;
      outcome.targets = 1;
      outcome.consumesTarget = true;
      break;
    }
    case 'ShootProjectilesAttack': {
      const points = Math.max(1, config.shootingPoints ?? 1);
      outcome.damagePerTarget = config.attack;
      outcome.targets = points;
      break;
    }
    case 'ShootBombSpecialAttack': {
      const burst = Math.max(1, config.projectilesPerBurst ?? 1);
      const affected = Math.max(1, config.numUnits ?? 1);
      outcome.damagePerTarget = config.attack / affected;
      outcome.targets = affected * burst;
      break;
    }
    case 'MultiLaserSpecialAttack': {
      outcome.damagePerTarget = config.attack;
      outcome.targets = Math.max(1, config.unitsPerShot ?? 1);
      break;
    }
    case 'VortexSpecialAttack': {
      // The vortex deletes the weakest enemies outright and bleeds the rest
      // at 30% of the attack, over 10 ticks.
      outcome.damagePerTarget = config.attack * 0.3;
      outcome.targets = Math.max(1, config.numKills ?? 1);
      break;
    }
    case 'WhirlwindSpecialAttack': {
      const ticks = Math.max(1, config.ticks ?? 1);
      outcome.damagePerTarget = config.attack / ticks;
      outcome.targets = 1;
      break;
    }
  }

  outcome.totalDamage = outcome.damagePerTarget * outcome.targets;
  return outcome;
}

/**
 * The damage the vortex deletes outright.
 *
 * The vortex removes up to `numKills` enemies whose health is at or below
 * `enemyMaxHealthToBeAbsorbed`, and bleeds the rest.
 */
export function vortexAbsorbed(
  enemyHealth: number,
  enemyMaxHealthToBeAbsorbed: number,
  numKills: number,
): boolean {
  return enemyHealth <= enemyMaxHealthToBeAbsorbed && numKills > 0;
}

/**
 * The damage the owner of a spawner takes when a minion dies.
 *
 * `withDamageOwnerOnDead(percent)` deals `percent × minion.maxLife`.
 */
export function minionDeathDamage(
  minionMaxLife: number,
  ownerDamagePercent: number,
): number {
  return (ownerDamagePercent / 100) * minionMaxLife;
}
