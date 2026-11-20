/**
 * The player's army, as a reading of the server's own save.
 *
 * This is derived presentation state, not a grant and not a decision. The
 * counts come from the three fields the server owns: `maps[0].store` (bought
 * but unplaced), the units placed on the map, and training queues whose real
 * start timestamp has elapsed. The names, group types and training times come
 * from the content. Nothing here can create a unit the server does not have.
 */
import { trainingView } from './management.ts';
import type { WorldSnapshot } from './session.ts';

/** The part of a content item the army needs to name and check a unit. */
export interface ArmyItemDefinition {
  /** The content id of the item. */
  readonly id: number;
  /** The content's name, never a client label. */
  readonly name: string;
  /** The content's type letter; only `'u'` is a unit. */
  readonly type: string;
  /** The content's `group_type`, for a quest's exclusion filter. */
  readonly groupType: string;
  /** The content's seconds to train one unit. */
  readonly trainingTime: number;
}

/** One unit type the server says the player can field. */
export interface ArmyUnitView {
  /** The content id sent with a team request. */
  readonly itemId: number;
  /** The name from the content. */
  readonly name: string;
  /** The content's group type. */
  readonly groupType: string;
  /** How many the server's save accounts for. */
  readonly available: number;
  /** False when the quest excludes this group type; display only. */
  readonly allowed: boolean;
}

/**
 * The army the interface may draw, in the content's order.
 *
 * An unknown id, a non-positive quantity, a building, an in-progress training
 * queue and another map are all ignored rather than guessed at. An excluded
 * group type is still shown — greyed out — so the player can see what they
 * own, but the server alone decides whether it may be fielded.
 */
export function armyView(
  world: WorldSnapshot,
  definitions: readonly ArmyItemDefinition[],
  now: number,
  excludedGroupTypes: readonly string[] = [],
): ArmyUnitView[] {
  const byId = new Map<number, ArmyItemDefinition>();
  for (const definition of definitions) {
    if (
      Number.isInteger(definition.id) && definition.id > 0 && definition.type === 'u' &&
      !byId.has(definition.id)
    ) {
      byId.set(definition.id, definition);
    }
  }
  const counts = new Map<number, number>();
  const add = (id: number, count: number): void => {
    if (!byId.has(id) || !Number.isInteger(count) || count <= 0) return;
    counts.set(id, (counts.get(id) ?? 0) + count);
  };

  const map = world.maps[0];
  const store = map?.store;
  if (store && typeof store === 'object' && !Array.isArray(store)) {
    for (const [key, value] of Object.entries(store)) {
      add(Number(key), Number(value));
    }
  }
  for (const tuple of Object.values(map?.items ?? {})) {
    if (!Array.isArray(tuple)) continue;
    add(Number(tuple[0]), 1);
    const attrs: unknown = tuple[6];
    if (!attrs || typeof attrs !== 'object' || Array.isArray(attrs)) continue;
    const bag = attrs as Record<string, unknown>;
    const queue = trainingView(bag, byId.get(Number(bag['ui']))?.trainingTime ?? 0, now);
    if (queue.readyToTake) add(queue.unitItemId, queue.queued);
  }

  const out: ArmyUnitView[] = [];
  for (const definition of byId.values()) {
    const available = counts.get(definition.id) ?? 0;
    if (available <= 0) continue;
    out.push({
      itemId: definition.id,
      name: definition.name,
      groupType: definition.groupType,
      available,
      allowed: !excludedGroupTypes.includes(definition.groupType),
    });
  }
  return out;
}
