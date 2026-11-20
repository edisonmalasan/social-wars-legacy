/**
 * The building-management view models.
 *
 * This is **pure derived state**, not a view and not a decision. It reads the
 * server's map item and the content's own numbers and turns them into the
 * small objects the info and recruit panels draw. It never spends a resource,
 * decides an outcome, touches the DOM or reads the clock itself: the caller
 * supplies `now` in unix seconds, so a test can hold time still.
 *
 * The server stays the authority. A countdown here is a presentation of the
 * server's `ts` (queue timestamp) and the content's training time; a Finish
 * or Take command may still be refused by the server, and that refusal goes
 * through the feedback channel. Nothing in this module grants a unit or
 * finishes a build.
 */

/** A building's hurry-up action, drawn while it is still being built. */
export interface FinishView {
  /** Whole seconds of build time left; 0 means the build has finished. */
  readonly remainingSeconds: number;
  /** The build clicks the request carries, from the content. */
  readonly clicksToBuild: number;
}

/**
 * The hurry-up view of a building, or null once the build has finished.
 *
 * `startedAt` and `now` are unix seconds; `buildTime` and `clicksToBuild` are
 * the content's own numbers. The time left is a display estimate — the
 * server decides the build's state when the request is applied.
 */
export function finishView(
  startedAt: number,
  buildTime: number,
  clicksToBuild: number,
  now: number,
): FinishView | null {
  if (!Number.isFinite(startedAt) || !Number.isFinite(buildTime) || buildTime <= 0) {
    return null;
  }
  const elapsed = Math.max(0, now - startedAt);
  const remaining = Math.max(0, buildTime - elapsed);
  if (remaining <= 0) return null;
  return { remainingSeconds: Math.ceil(remaining), clicksToBuild };
}

/** A building's upgrade action, drawn from the content's next tier. */
export interface UpgradeView {
  /** The next tier's name, from the content. */
  readonly nextName: string;
  /** The requirement line: the tier's own `min_level`, from the content. */
  readonly requirement: string;
}

/**
 * The upgrade view for a building, or null when the content gives it no
 * next tier. The requirement is a statement of the content's `min_level`,
 * not a claim that the player may upgrade: the server checks the level and
 * the free tiles itself.
 */
export function upgradeView(
  nextName: string | null,
  nextMinLevel: number | null,
  playerLevel: number,
): UpgradeView | null {
  if (!nextName || nextMinLevel === null || !Number.isFinite(nextMinLevel)) return null;
  return {
    nextName,
    requirement: playerLevel < nextMinLevel
      ? `Requires level ${nextMinLevel}`
      : `Next tier · level ${nextMinLevel}`,
  };
}

/** The server's training queue, read from a map item's attribute bag. */
export interface TrainingView {
  /** How many units are queued (`nu`). */
  readonly queued: number;
  /** The unit being trained (`ui`), or 0 when the bag names none. */
  readonly unitItemId: number;
  /** Whole seconds left on the current unit; 0 when it is ready. */
  readonly remainingSeconds: number;
  /** Whether the queue holds a finished unit the player can take. */
  readonly readyToTake: boolean;
}

/** A finite number in an attribute bag, or a fallback. */
function bagNumber(value: unknown, fallback: number): number {
  const number = Number(value ?? fallback);
  return Number.isFinite(number) ? number : fallback;
}

/**
 * Read the training queue from the server's attribute bag.
 *
 * The upstream keeps `nu` (queue length), `ts` (when the current unit
 * started, in unix seconds) and `ui` (its item id) in the map item's
 * attribute bag. `trainingTime` is the content's seconds for one unit and
 * `now` is the caller's unix second.
 *
 * A unit is only ever shown as ready when **all** of these hold: the queue is
 * non-empty, `ts` is present and finite (a real server start), the content's
 * training time is positive, and the countdown has elapsed. A missing or
 * malformed `ts` falls back to `now` only to keep the countdown display
 * conservative; it is never a start time we can claim finished. Without a
 * positive content duration a finished timestamp says nothing either. Both
 * cases would fabricate a ready unit and offer a Take command the server is
 * certain to refuse.
 */
export function trainingView(
  attributes: Readonly<Record<string, unknown>> | null | undefined,
  trainingTime: number,
  now: number,
): TrainingView {
  const queued = bagNumber(attributes?.['nu'], 0);
  const unitItemId = bagNumber(attributes?.['ui'], 0);
  const rawStart = attributes?.['ts'];
  const parsedStart = Number(rawStart);
  const hasRealStart =
    rawStart !== undefined && rawStart !== null && Number.isFinite(parsedStart);
  // `now` is a display-only fallback: it keeps the countdown at its full
  // length when the server has not given us a start, but it is not evidence
  // that training finished.
  const startedAt = hasRealStart ? parsedStart : now;
  const duration = Number.isFinite(trainingTime) && trainingTime > 0 ? trainingTime : 0;
  const elapsed = Math.max(0, now - startedAt);
  // No queue means no countdown to draw.
  const remaining = queued > 0 ? Math.max(0, duration - elapsed) : 0;
  return {
    queued,
    unitItemId,
    remainingSeconds: Math.ceil(remaining),
    readyToTake: queued > 0 && hasRealStart && duration > 0 && remaining <= 0,
  };
}

/** The input the info panel needs for one building. */
export interface BuildingInfoInput {
  /** The building's name, from the content. */
  readonly name: string;
  /** The next tier's name, or null when there is none. */
  readonly nextName: string | null;
  /** The next tier's level requirement, or null when there is none. */
  readonly nextMinLevel: number | null;
  /** The player's level, from the server's answer. */
  readonly playerLevel: number;
  /** When the building was placed, in unix seconds. */
  readonly startedAt: number;
  /** The content's build time in seconds. */
  readonly buildTime: number;
  /** The content's build clicks, carried by a Finish request. */
  readonly clicksToBuild: number;
  /** The caller's unix second. */
  readonly now: number;
}

/** What the info panel draws for a building. */
export interface BuildingInfoView {
  /** The building's name, always shown. */
  readonly name: string;
  /** The upgrade action, or null. */
  readonly upgrade: UpgradeView | null;
  /** The hurry-up action, or null. */
  readonly finish: FinishView | null;
}

/**
 * A building's info view.
 *
 * Unlike the resource panel, this exists for **every** building: the Command
 * Center, houses, walls and decorations all have a name and may have an
 * upgrade or a hurry-up action. That is why a non-producing building still
 * gets a panel.
 */
export function buildingInfoView(input: BuildingInfoInput): BuildingInfoView {
  return {
    name: input.name,
    upgrade: upgradeView(input.nextName, input.nextMinLevel, input.playerLevel),
    finish: finishView(input.startedAt, input.buildTime, input.clicksToBuild, input.now),
  };
}

/** One trainable unit card, from the content. */
export interface UnitCard {
  /** The unit's item id, sent when the player trains it. */
  readonly itemId: number;
  /** The unit's name, from the content. */
  readonly name: string;
}

/** What the recruit panel draws for a training building. */
export interface RecruitView {
  /** The building's name, from the content. */
  readonly buildingName: string;
  /** The units the building can train, from the content. */
  readonly units: readonly UnitCard[];
  /** The server's queue, from the building's attribute bag. */
  readonly queue: TrainingView;
}
