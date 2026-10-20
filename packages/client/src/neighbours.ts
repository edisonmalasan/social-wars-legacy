/**
 * The neighbour strip.
 *
 * The strip is the row of the players next to you: their name, their
 * level and their town hall's portrait. The client shows a neighbour's
 * **Facebook photo**, which the clone does not have — the original's
 * `graph.facebook` calls are inert here — so the portrait is a
 * placeholder and the rest of the strip is the game's.
 *
 * ## The order
 *
 * The **server** decides the order, and it is not the client's:
 *
 * ```python
 * # upstream/sessions.py:neighbors()
 * for key in __villages:      # the static villages first
 *     ...
 * for key in __saves:        # then the other players
 *     ...
 * ```
 *
 * The general, Mike, is skipped — he is not a neighbour anybody can
 * hurry up.
 *
 * ## The hurry-up
 *
 * A building whose production is ready shows the neighbours' "hurry up"
 * icons, so a neighbour can be asked to collect it:
 *
 * ```as3
 * // core/isoengine/IsoBuilding.as:1064
 * var ready = this.iconsHurryUp.length > 0
 *   || (this.activation > 0 && this.collected_at >= this.activation);
 * ```
 *
 * So the rule is: the building's countdown has **finished**.
 */
import type { Resources } from '@swl/rules';

/** A neighbour, as the server describes them. */
export interface Neighbour {
  /** The player's id. */
  id: string;
  /** Their name. */
  name: string;
  /** Their level. */
  level: number;
  /** Their experience. */
  xp: number;
  /** Their resources. */
  resources: Resources;
  /**
   * Whether they are one of the game's **static villages** rather than
   * another player.
   */
  static: boolean;
}

/** One entry of the strip. */
export interface NeighbourEntry {
  /** The neighbour. */
  neighbour: Neighbour;
  /** Whether the player's town hall can be hurried up. */
  canHurryUp: boolean;
  /**
   * The portrait.
   *
   * The client shows the neighbour's Facebook photo, and the clone has
   * none, so the portrait is a placeholder.
   */
  portrait: 'placeholder';
}

/** The general, Mike, is not a neighbour anybody can hurry up. */
const GENERAL_IDS = ['100000030', '100000031'];

/** Whether a neighbour is the general. */
export function isGeneral(neighbour: Neighbour): boolean {
  return GENERAL_IDS.includes(neighbour.id);
}

/**
 * The strip.
 *
 * The order is the server's, and the general is left out of the hurry-up
 * but kept in the strip — the client shows him too.
 */
export function neighbourStrip(
  neighbours: readonly Neighbour[],
  options: { canHurryUp?: boolean } = {},
): NeighbourEntry[] {
  const canHurryUp = options.canHurryUp === true;
  return neighbours.map((neighbour) => ({
    neighbour,
    canHurryUp: canHurryUp && !isGeneral(neighbour),
    portrait: 'placeholder' as const,
  }));
}

/** A building, as the hurry-up rule sees it. */
export interface HurryUpBuilding {
  /** The building's reference id. */
  id: string;
  /** How long its countdown is, in seconds. Zero means it does not collect. */
  activation: number;
  /** How long the countdown has run, in seconds. */
  collectedAt: number;
}

/**
 * Whether a building's production is ready to be collected.
 *
 * The client's own rule: the building collects at all, and its countdown
 * has finished.
 */
export function isReadyToCollect(building: HurryUpBuilding): boolean {
  return building.activation > 0 && building.collectedAt >= building.activation;
}

/**
 * The buildings whose production is ready.
 *
 * These are the ones that show the neighbours' "hurry up" icons.
 */
export function buildingsToHurryUp(
  buildings: readonly HurryUpBuilding[],
): HurryUpBuilding[] {
  return buildings.filter(isReadyToCollect);
}
