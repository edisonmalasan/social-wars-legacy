/**
 * The player store.
 *
 * A command batch has to be applied to a player's save **atomically**
 * (roadmap F3: concurrent commands cannot corrupt a player). That means two
 * things:
 *
 * - the batch is applied to a **copy**, and the copy replaces the save only
 *   when the whole batch has been processed. A crash, a timeout or a client
 *   disconnect half way through leaves the save exactly as it was, never
 *   half-written.
 * - two commands for the same player never interleave. The store serialises
 *   them per player, so the second one sees the first one's result.
 *
 * The interface is deliberately small, so that the PostgreSQL implementation
 * (F3) and the PGlite one (offline play) can both satisfy it.
 */

import type { ShimWorld } from '@swl/server';

/** A player's save. */
export interface PlayerSave {
  playerId: string;
  /** The player's world: the save document and the resources. */
  world: ShimWorld;
}

/** The store's operations. */
export interface PlayerStore {
  /** A player's save, or null if there is none. */
  get(playerId: string): PlayerSave | null;

  /** Whether the player exists. */
  has(playerId: string): boolean;

  /**
   * Apply a change to a player's save, atomically.
   *
   * The function is given the current world and returns the new one. If it
   * throws, the save is left untouched.
   *
   * Returns null when the player does not exist.
   */
  transact(
    playerId: string,
    change: (world: ShimWorld) => ShimWorld,
  ): PlayerSave | null;

  /** How many players are stored. */
  readonly size: number;
}

/** A deep copy of a world, so a failed transaction cannot leave a half-written save. */
export function cloneWorld(world: ShimWorld): ShimWorld {
  return {
    save: {
      playerInfo: { ...world.save.playerInfo },
      maps: world.save.maps.map((map) => ({ ...map })),
      privateState: { ...world.save.privateState },
    },
    resources: { ...world.resources },
    nextCommandNumber: world.nextCommandNumber,
  };
}

/**
 * The in-memory store.
 *
 * It is the reference implementation of the interface, and the one the
 * offline (PGlite) play mode uses when there is no server at all.
 */
export class MemoryPlayerStore implements PlayerStore {
  private readonly saves = new Map<string, PlayerSave>();

  constructor(initial: readonly PlayerSave[] = []) {
    for (const save of initial) {
      this.saves.set(save.playerId, { playerId: save.playerId, world: cloneWorld(save.world) });
    }
  }

  get(playerId: string): PlayerSave | null {
    const save = this.saves.get(playerId);
    if (!save) return null;
    // A copy, so a caller cannot mutate the stored save behind the store's
    // back. Every change goes through `transact`.
    return { playerId: save.playerId, world: cloneWorld(save.world) };
  }

  has(playerId: string): boolean {
    return this.saves.has(playerId);
  }

  transact(playerId: string, change: (world: ShimWorld) => ShimWorld): PlayerSave | null {
    const save = this.saves.get(playerId);
    if (!save) return null;
    // The change runs against a copy. If it throws, the stored save is
    // untouched and the player is not left half-written.
    const next = change(cloneWorld(save.world));
    save.world = cloneWorld(next);
    return { playerId: save.playerId, world: cloneWorld(save.world) };
  }

  /** Add a player. */
  add(playerId: string, world: ShimWorld): void {
    this.saves.set(playerId, { playerId, world: cloneWorld(world) });
  }

  get size(): number {
    return this.saves.size;
  }
}
