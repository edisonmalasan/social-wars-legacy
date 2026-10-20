/**
 * The battle loop: cadence, shooters and the tick.
 *
 * Everything here is ported from the decompiled client and is pure: no wall
 * clock, no unseeded randomness, no I/O. A battle is a function of its
 * initial state and its seed, which is what makes the golden-master
 * differential test against the original client possible.
 *
 * ## The tick rate
 *
 * The client runs at **30 frames per second** (`attack_interval` is counted in
 * frames, not seconds), so a `attack_interval` of 35 is about 1.17 seconds.
 *
 * ## The cadence
 *
 * A unit fires on the frames where
 *
 *     (frame + phase) % attack_interval === 0
 *
 * where `phase` is a random integer in 0..4 taken once, when the unit is
 * created (`IsoFightingElement.as:171` — `Math.floor(Math.random() * 5)`). The
 * phase exists so that a group of units does not all fire on the same frame.
 *
 * A **building** fires on the frames where
 *
 *     frame % attack_interval === 0
 *
 * with **no phase** (`IsoBuilding.as:486`) — buildings fire in global
 * lockstep.
 *
 * ## The shooters
 *
 * A building has a set of *attack points* — the places on it that a
 * projectile can leave from, one per corner per facing. On its attack frame
 * it fires from every attack point, but the list is truncated to
 * `maxShooters` (`BasicFortressDelegate.as:55-57`).
 *
 * For an ordinary turret or fortress `maxShooters` is `Infinity`, so it fires
 * from every attack point. For a **bunker** it is the number of units the
 * bunker contains (`BunkerDelegate.as:73` — `maxShooters =
 * self.vUnitsContained.length`), so a bunker fires once per garrisoned unit
 * and an empty bunker fires not at all.
 *
 * Every shot deals the building's own `attack` value, which comes straight
 * from the config (`IsoElement.as:267` — `uiAttack = building.attack`). It
 * is **not** scaled by the garrison.
 */

/** The client runs at 30 frames per second. */
export const FRAMES_PER_SECOND = 30;

/** The number of distinct attack phases a unit can have. */
export const ATTACK_PHASE_COUNT = 5;

/**
 * The random phase a unit takes when it is created.
 *
 * `IsoFightingElement.as:171`: `this.iDelayAttack = Math.floor(Math.random() * 5)`.
 *
 * @param random a value in [0, 1)
 */
export function attackPhase(random: number): number {
  return Math.floor(random * ATTACK_PHASE_COUNT) % ATTACK_PHASE_COUNT;
}

/**
 * Does a unit fire on this frame?
 *
 * `(frame + phase) % attack_interval === 0` (`IsoUnit.as:653`).
 */
export function unitFiresOnFrame(frame: number, phase: number, attackInterval: number): boolean {
  if (attackInterval <= 0) return false;
  return (frame + phase) % attackInterval === 0;
}

/**
 * Does a building fire on this frame?
 *
 * `frame % attack_interval === 0` (`IsoBuilding.as:486`) — no phase, so
 * buildings fire in global lockstep.
 */
export function buildingFiresOnFrame(frame: number, attackInterval: number): boolean {
  if (attackInterval <= 0) return false;
  return frame % attackInterval === 0;
}

/** A building's attack configuration. */
export interface BuildingAttack {
  /** How many attack points it has for the current facing. */
  attackPoints: number;
  /** How many units are garrisoned inside it. */
  garrison: number;
  /** True for a bunker, whose shooters are limited by the garrison. */
  isBunker: boolean;
}

/**
 * How many shots a building fires on its attack frame.
 *
 * `BasicFortressDelegate.onAttack` truncates the attack points to
 * `maxShooters`. For a bunker that is the number of garrisoned units, so an
 * empty bunker fires nothing and a bunker with three soldiers fires three
 * shots. Every other building fires from all of its attack points.
 */
export function shooterCount(building: BuildingAttack): number {
  if (building.isBunker) {
    return Math.min(building.attackPoints, Math.max(0, building.garrison));
  }
  return building.attackPoints;
}

/**
 * The damage a building deals in one attack frame.
 *
 * Each shot deals the building's own `attack`, so the total is the number of
 * shots times that value. The `attack` is the config's value, unchanged by
 * the garrison.
 */
export function buildingAttackDamage(building: BuildingAttack, attack: number): number {
  return shooterCount(building) * attack;
}

/** One combatant in the simulation. */
export interface Combatant {
  readonly id: string;
  readonly kind: 'unit' | 'building';
  /** The item id, for the content lookup. */
  readonly itemId: number;
  readonly attack: number;
  readonly defense: number;
  readonly life: number;
  readonly attackRange: number;
  /** Frames at 30 fps. */
  readonly attackInterval: number;
  /** For a unit: the random phase. For a building: unused. */
  readonly phase: number;
  /** For a building: its attack configuration. */
  readonly building?: BuildingAttack;
  /** The fighting-type property keys this combatant carries. */
  readonly properties: Readonly<Record<string, unknown>>;
  /** The `best_against` key and multiplier. */
  readonly bestAgainst: string | null;
  readonly bestAgainstMult: number;
}

/**
 * The frames on which a combatant fires.
 *
 * Yields every frame in `[0, frameCount)` on which the combatant attacks.
 */
export function* attackFrames(combatant: Combatant, frameCount: number): Generator<number> {
  for (let frame = 0; frame < frameCount; frame++) {
    const fires =
      combatant.kind === 'unit'
        ? unitFiresOnFrame(frame, combatant.phase, combatant.attackInterval)
        : buildingFiresOnFrame(frame, combatant.attackInterval);
    if (fires) yield frame;
  }
}

/**
 * The number of attack frames in a window.
 *
 * Useful for the golden-master diff: it is a cheap, seed-independent check
 * that the cadence matches.
 */
export function countAttackFrames(
  combatant: Combatant,
  frameCount: number,
): number {
  let n = 0;
  for (const _ of attackFrames(combatant, frameCount)) n++;
  return n;
}
