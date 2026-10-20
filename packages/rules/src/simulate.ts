/**
 * The battle simulation.
 *
 * The original game resolves a battle **on the client**: the client runs
 * the fight frame by frame, rolls the damage, and sends the result to the
 * server, which believes it (finding F5). A client that claims a win gets
 * a win.
 *
 * This module is the opposite: the server runs the **whole** fight, from a
 * server-issued seed, and the client's claim is ignored. Same seed, same
 * armies, same outcome — on any machine.
 *
 * ## The loop
 *
 * The client ticks at 30 frames a second (`FRAMES_PER_SECOND`). A unit
 * fires on the frames where `frame % attack_interval == phase`, and it
 * takes a random phase of 0 to 4 so the units do not all fire in lockstep.
 * A building has no phase and fires in global lockstep.
 *
 * ## The distance
 *
 * From `IsoEngine.distance` (core/isoengine/IsoEngine.as:2017-2035):
 *
 * ```as3
 * offset = int(building.width - 1 >> 1);
 * centre = (tx - offset, ty - offset);
 * distance = int(Math.sqrt(dx * dx + dy * dy));
 * ```
 *
 * The distance is **truncated to an integer**, and the centres are offset
 * by half the building's footprint, so a wide building's centre is not its
 * bottom-left tile.
 *
 * ## The targeting
 *
 * From `bucleNearestUnits` (core/isoengine/IsoEngine.as:1686-1721): the
 * candidates within range are scored, and the highest score wins. A
 * candidate with no attack of its own is penalised by `AGGRO_RANGE`, so a
 * passive building is only shot once there is nothing better to shoot.
 */
import { Random, hashSeed } from './random.ts';
import {
  resolveDamage,
  selectTarget,
  type CombatContext,
  type CombatStats,
  type TargetCandidate,
} from './combat.ts';
import {
  buildingFiresOnFrame,
  shooterCount,
  unitFiresOnFrame,
  type BuildingAttack,
} from './battle.ts';

/** An element on the field: a unit or a building. */
export interface SimElement extends CombatStats {
  /** The element's id, for the events and the outcome. */
  id: string;
  /** The content item id. */
  itemId: number;
  /** The element's current health. */
  health: number;
  /** The element's maximum life. */
  maxLife: number;
  /** The element's tile x. */
  tx: number;
  /** The element's tile y. */
  ty: number;
  /** The footprint's width, in tiles. */
  width: number;
  /** The footprint's height, in tiles. */
  height: number;
  /** The unit's random attack phase, 0 to 4. */
  phase: number;
  /** The content's `subcat_functional`. */
  subcatFunctional: number;
  /** Whether the element is a unit or a building. */
  kind: 'unit' | 'building';
  /** The building's remaining collect, for the targeting score. */
  collect?: number;
  /** The building's attack points: how many shooters it has. */
  attackPoints?: number;
  /** Whether the building is a bunker. */
  isBunker?: boolean;
  /** The units garrisoned inside a building. */
  garrison?: SimElement[];
}

/** One shot, for the replay and the golden-master diff. */
export interface BattleEvent {
  /** The frame the shot was fired on. */
  frame: number;
  /** The shooter's id. */
  attacker: string;
  /** The target's id. */
  target: string;
  /** The damage dealt. */
  damage: number;
  /** Whether it was a critical hit. */
  crit: boolean;
  /** Whether the hit killed the target. */
  killed: boolean;
}

/** What the simulation needs. */
export interface BattleInput {
  /** The server-issued seed. */
  seed: string;
  /** The attacking side. */
  attackers: readonly SimElement[];
  /** The defending side. */
  defenders: readonly SimElement[];
  /** The maximum number of frames the fight may last. */
  maxFrames?: number;
  /** The per-attack tunables. */
  context?: CombatContext;
  /** The damage options, such as the variance. */
  options?: { variance?: number; critChance?: number };
}

/** The result of a battle. */
export interface BattleOutcome {
  /** Who won. */
  winner: 'attackers' | 'defenders' | 'draw';
  /** How many frames the fight lasted. */
  frames: number;
  /** The damage the attackers dealt. */
  attackerDamage: number;
  /** The damage the defenders dealt. */
  defenderDamage: number;
  /** The ids of the attackers that died. */
  attackerLosses: string[];
  /** The ids of the defenders that died. */
  defenderLosses: string[];
  /** Every shot, in order. */
  events: BattleEvent[];
}

/** How long a fight may last, in frames. Ten seconds at 30 fps. */
export const DEFAULT_MAX_FRAMES = 300;

/**
 * The distance between two elements, in tiles.
 *
 * Ported from `IsoEngine.distance` (core/isoengine/IsoEngine.as:2017-2035):
 * the euclidean distance between the **centres**, with the centre offset
 * by half the footprint, truncated to an integer.
 */
export function distanceBetween(a: SimElement, b: SimElement): number {
  const ax = a.tx - ((a.width - 1) >> 1);
  const ay = a.ty - ((a.height - 1) >> 1);
  const bx = b.tx - ((b.width - 1) >> 1);
  const by = b.ty - ((b.height - 1) >> 1);
  const dx = ax - bx;
  const dy = ay - by;
  return Math.trunc(Math.sqrt(dx * dx + dy * dy));
}

/** How many shots a building fires at once. */
export function shotsOf(element: SimElement): number {
  if (element.kind !== 'building') return 1;
  const attack: BuildingAttack = {
    attackPoints: element.attackPoints ?? 0,
    garrison: element.garrison?.length ?? 0,
    isBunker: element.isBunker ?? false,
  };
  return Math.max(1, shooterCount(attack));
}

/**
 * Whether an element fires on a frame.
 *
 * A unit fires on the frames where `frame % attack_interval == phase`; a
 * building has no phase and fires in lockstep.
 */
export function firesOnFrame(element: SimElement, frame: number): boolean {
  if (element.kind === 'unit') {
    return unitFiresOnFrame(frame, element.phase, element.attack_interval);
  }
  return buildingFiresOnFrame(frame, element.attack_interval);
}

/** The target, as the targeting sees it. */
function asCandidate(
  shooter: SimElement,
  target: SimElement,
): TargetCandidate & { element: SimElement } {
  return {
    kind: target.kind,
    distance: distanceBetween(shooter, target),
    subcatFunctional: target.subcatFunctional,
    collect: target.collect,
    uiAttack: target.attack,
    passive: target.attack === 0,
    element: target,
  };
}

/**
 * Simulate a battle.
 *
 * The result is a pure function of the seed and the two armies: the same
 * inputs always produce the same fight, on any machine, in any process.
 */
export function simulateBattle(input: BattleInput): BattleOutcome {
  const random = new Random(hashSeed(input.seed));
  const maxFrames = input.maxFrames ?? DEFAULT_MAX_FRAMES;

  // The living elements of each side. The caller's arrays are not
  // modified: the simulation works on copies.
  const attackers = input.attackers.map((element) => ({ ...element }));
  const defenders = input.defenders.map((element) => ({ ...element }));

  const events: BattleEvent[] = [];
  let attackerDamage = 0;
  let defenderDamage = 0;
  const attackerLosses: string[] = [];
  const defenderLosses: string[] = [];

  /** One side fires at the other. */
  function fire(shooters: SimElement[], targets: SimElement[], side: 'attackers' | 'defenders') {
    for (const shooter of shooters) {
      // A unit that died earlier in this frame does not get to shoot back.
      if (shooter.health <= 0) continue;
      if (!firesOnFrame(shooter, frame)) continue;
      const living = targets.filter((target) => target.health > 0);
      if (living.length === 0) return;

      for (let shot = 0; shot < shotsOf(shooter); shot++) {
        const candidates = living
          .map((target) => asCandidate(shooter, target))
          .filter((candidate) => candidate.distance < shooter.attack_range);
        if (candidates.length === 0) break;

        const chosen = selectTarget(candidates);
        if (!chosen) break;
        const target = chosen.element;

        const result = resolveDamage(shooter, target, random, input.context ?? {}, input.options ?? {});
        const before = target.health;
        target.health = Math.max(0, target.health - result.damage);
        const killed = before > 0 && target.health <= 0;

        if (side === 'attackers') attackerDamage += result.damage;
        else defenderDamage += result.damage;

        events.push({
          frame,
          attacker: shooter.id,
          target: target.id,
          damage: result.damage,
          crit: result.crit,
          killed,
        });

        if (killed) {
          if (side === 'attackers') defenderLosses.push(target.id);
          else attackerLosses.push(target.id);
        }
      }
    }
  }

  let frame = 0;
  for (; frame < maxFrames; frame++) {
    fire(attackers, defenders, 'attackers');
    fire(defenders, attackers, 'defenders');

    if (attackers.every((element) => element.health <= 0)) break;
    if (defenders.every((element) => element.health <= 0)) break;
  }

  const attackersAlive = attackers.some((element) => element.health > 0);
  const defendersAlive = defenders.some((element) => element.health > 0);

  let winner: BattleOutcome['winner'] = 'draw';
  if (attackersAlive && !defendersAlive) winner = 'attackers';
  else if (defendersAlive && !attackersAlive) winner = 'defenders';

  return {
    winner,
    frames: frame,
    attackerDamage,
    defenderDamage,
    attackerLosses,
    defenderLosses,
    events,
  };
}
