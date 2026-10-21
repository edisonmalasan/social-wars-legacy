/**
 * The projectiles.
 *
 * A projectile is a thing that flies from one place to another and
 * lands. The original client has three models of it — a **parabolic**
 * one, a **grenade** and a **movie** — and they differ only in the
 * curve they fly along and in how long they take.
 *
 * This is a port of the client's own code, because the client is the
 * specification:
 *
 * - `battle/projectiles/models/ParabolicProjectile.as` — the flight and
 *   the landing;
 * - `battle/projectiles/models/Grenade.as` — the same flight with a
 *   different curve;
 * - `battle/projectiles/models/MovieProjectile.as` — the flight with a
 *   random nudge and a length taken from the clip;
 * - `battle/projectiles/AbstractProjectile.as` — where the projectile
 *   starts, and what happens when it lands;
 * - `battle/projectiles/ProjectileDefinition.as` — the numbers, and
 *   their defaults.
 *
 * ## The random source is a parameter
 *
 * The client's own code calls `Math.random()`. This does not: the
 * random source is **passed in**, so that the same seed gives the same
 * flight, and so that the port can be tested at all. The *order* of
 * the calls is the client's, because the order is part of the flight.
 *
 * ## What this is not
 *
 * The art is not here, and it cannot be. The effect assets are
 * Zynga's, and the shipped product carries no Zynga art; the art has
 * to be re-created or licensed before the projectiles can be drawn.
 * What is here is the **flight**: where the projectile is at each
 * step, which way it points, and when it lands.
 */
import { Random } from '@swl/rules';

/** A point, in the client's own terms. */
export interface Point {
  x: number;
  y: number;
}

/**
 * The easing, as the client uses it.
 *
 * The client's own easings come from GreenSock, and they are functions
 * of the step, the start, the range and the number of steps.
 */
export type Easing = (
  step: number,
  start: number,
  range: number,
  steps: number,
) => number;

/** A projectile's numbers. */
export interface ProjectileDefinition {
  /** Which effect the projectile draws. */
  readonly projectileId: string;
  /** How fast it crosses the map. */
  readonly speed: number;
  /** How high the arc is. Zero is a straight line. */
  readonly curve: number;
  /** How far the landing point is scattered. */
  readonly randomOffset: number;
  /** How much of the arc is vertical. */
  readonly verticalOffset: number;
  /** How far the **start** is scattered. */
  readonly startOffset: number;
  /** The easing, when there is one. */
  readonly easing: Easing | null;
  /** The effect's scale. */
  readonly projectileScale: number;
  /** The effect's fatness. */
  readonly projectileScaleFatness: number;
  /** The effect drawn when it lands. */
  readonly blastId: string;
  /** The blast's radius. */
  readonly blastRadius: number;
  /** Whether the blast turns with the projectile. */
  readonly blastRotation: boolean;
  /** Whether the blast stays. */
  readonly blastPermanent: boolean;
  /** The blast's scale. */
  readonly blastScale: number;
  /** The effect drawn along the way. */
  readonly trailId: string;
  /** How many trail effects are drawn per step. */
  readonly trailsPerStep: number;
}

/**
 * The definition's defaults.
 *
 * The client's own `ProjectileDefinition` constructor, with its
 * defaults: a speed of 10, no curve, a scatter of 20 and no easing.
 */
export const DEFAULT_DEFINITION: ProjectileDefinition = {
  projectileId: '',
  speed: 10,
  curve: 0,
  randomOffset: 20,
  verticalOffset: 0.5,
  startOffset: 0,
  easing: null,
  projectileScale: 1,
  projectileScaleFatness: 1,
  blastId: '',
  blastRadius: 100,
  blastRotation: false,
  blastPermanent: false,
  blastScale: 1,
  trailId: '',
  trailsPerStep: 3,
};

/** Which of the client's three models a projectile flies by. */
export type ProjectileModel = 'parabolic' | 'grenade' | 'movie';

/** A projectile in flight. */
export interface Projectile {
  /** The numbers it flies by. */
  readonly definition: ProjectileDefinition;
  /** Which model it flies by. */
  readonly model: ProjectileModel;
  /** Where it started. */
  readonly start: Point;
  /** Where it is. */
  x: number;
  y: number;
  /** Where it was, before the last step. */
  readonly old: Point;
  /** Which way it points, in degrees. */
  rotation: number;
  /** Which step it is on. */
  step: number;
  /** How much a step moves it. */
  stepIncrement: number;
  /** How many steps it takes. */
  steps: number;
  /** How far it moves per step. */
  readonly delta: Point;
  /** The height of the arc. */
  curve: number;
  /** The clip's frames, for the movie model. */
  readonly frames: number;
  /** Whether it has landed. */
  landed: boolean;
  /** Whether it is done. */
  finished: boolean;
}

/** The distance between two points. */
export function distance(a: Point, b: Point): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Launch a projectile.
 *
 * The client's `init`: the start is scattered by the definition's
 * `startOffset`, the landing point is scattered by its `randomOffset`,
 * the number of steps is the distance divided by the speed, and the
 * step begins a little way along the flight.
 *
 * The client's order of the random calls is kept, because the order is
 * part of the flight.
 */
export function launchProjectile(
  definition: ProjectileDefinition = DEFAULT_DEFINITION,
  start: Point,
  target: Point,
  random: () => number = Math.random,
  model: ProjectileModel = 'parabolic',
  frames = 1,
): Projectile {
  // The start, scattered.
  const origin: Point = { x: start.x, y: start.y };
  if (definition.startOffset) {
    origin.x += random() * definition.startOffset - definition.startOffset / 2;
    origin.y += random() * definition.startOffset - definition.startOffset / 2;
  }

  // The landing point, scattered.
  const landing: Point = { x: target.x, y: target.y };
  landing.x += random() * definition.randomOffset - definition.randomOffset / 2;
  landing.y += random() * definition.randomOffset - definition.randomOffset / 2;

  let steps = distance(origin, landing) / definition.speed;
  if (steps < 1) steps = 1;

  const delta: Point = {
    x: (landing.x - origin.x) / steps,
    y: (landing.y - origin.y) / steps,
  };

  const projectile: Projectile = {
    definition,
    model,
    start: origin,
    x: origin.x,
    y: origin.y,
    old: { x: origin.x, y: origin.y },
    rotation: (Math.atan2(delta.y, delta.x) * 180) / Math.PI,
    // The step begins a little way along the flight.
    step: random() * 0.94 + 0.05,
    stepIncrement: 1,
    steps,
    delta,
    curve: definition.curve !== 0 ? steps * 4 * definition.curve : 0,
    frames,
    landed: false,
    finished: false,
  };

  // The movie model nudges the flight and takes its length from the
  // clip: `MovieProjectile.as`.
  if (model === 'movie') {
    projectile.delta.x += random() - 0.5;
    projectile.delta.y += random() - 0.5;
    projectile.steps = frames;
    projectile.rotation = 0;
  }

  // The client ticks once at the end of `init`, so the first position
  // is already computed.
  tickProjectile(projectile, random);
  return projectile;
}

/**
 * Advance a projectile by one step.
 *
 * The client's `tick`: the position is the start plus the delta times
 * the step, the arc is added when there is one, and the projectile
 * lands when the step passes the end.
 */
export function tickProjectile(
  projectile: Projectile,
  random: () => number = Math.random,
): Projectile {
  void random;

  if (projectile.step >= projectile.steps) {
    projectile.x = projectile.start.x + projectile.delta.x * projectile.steps;
    projectile.y = projectile.start.y + projectile.delta.y * projectile.steps;
    projectile.landed = true;
    projectile.finished = true;
    return projectile;
  }

  projectile.old.x = projectile.x;
  projectile.old.y = projectile.y;

  const easing = projectile.definition.easing;
  if (easing !== null) {
    projectile.x = easing(
      projectile.step,
      projectile.start.x,
      projectile.delta.x * projectile.steps,
      projectile.steps,
    );
    projectile.y = easing(
      projectile.step,
      projectile.start.y,
      projectile.delta.y * projectile.steps,
      projectile.steps,
    );
  } else {
    projectile.x = projectile.start.x + projectile.delta.x * projectile.step;
    projectile.y = projectile.start.y + projectile.delta.y * projectile.step;
  }

  if (projectile.definition.curve !== 0) {
    if (projectile.model === 'grenade') {
      // The grenade's arc: `Grenade.as`.
      const t = projectile.step / projectile.steps;
      projectile.y +=
        -Math.abs(Math.sin(t * Math.PI * (1 + t * t * 3))) *
        projectile.curve *
        (1 - t);
    } else {
      // The parabola: `ParabolicProjectile.as`.
      projectile.y +=
        -Math.sin((projectile.step / projectile.steps) * Math.PI) * projectile.curve;
    }
    // The projectile turns to face the way it is actually going.
    projectile.rotation =
      (Math.atan2(projectile.y - projectile.old.y, projectile.x - projectile.old.x) *
        180) /
      Math.PI;
  }

  projectile.step += projectile.stepIncrement;
  return projectile;
}

/**
 * A seeded random source.
 *
 * The client's own randomness is `Math.random`, and a port that cannot
 * be reproduced cannot be tested. This is the **rules engine's** own
 * generator, so a battle's randomness and its visuals can be made to
 * agree: the same seed gives the same flight every time.
 */
export function seededRandom(seed: number | string): () => number {
  const random = new Random(seed);
  return () => random.next();
}
