/**
 * The client's interaction.
 *
 * What the player does, and what it turns into. The rule the whole design
 * rests on is that the client **requests**: selecting is local, and every
 * action that changes the world becomes a command the server answers.
 *
 * The client checks what it can - a building under construction cannot be
 * moved, a tile that is taken cannot be built on - and the server decides
 * everything else. A refusal here is a refusal of the *gesture*, not of the
 * outcome: the server may still refuse a command the client thought was
 * fine, and the answer to that is the server's.
 */
import {
  buy,
  collect,
  move,
  placeStoredItem,
  train,
  upgrade,
  type NativeCommand,
} from './requests.ts';

/** What the player has selected. */
export type Selection =
  /** Nothing. */
  | { kind: 'none' }
  /** An element on the map. */
  | {
      kind: 'element';
      isoId: number;
      itemId: number;
      element: 'unit' | 'building';
      /** Whether the building is still being constructed. */
      underConstruction: boolean;
    }
  /** A building or a unit being placed. */
  | { kind: 'placement'; itemId: number; itemType: 'b' | 'u' | 'n' };

/** Why a gesture cannot be turned into a command. */
export type Refusal =
  | 'nothing-selected'
  | 'under-construction'
  | 'not-on-the-map'
  | 'tile-taken';

/** The outcome of a gesture. */
export type Gesture =
  | { ok: true; command: NativeCommand }
  | { ok: false; refusal: Refusal };

/** The client's interaction state. */
export class Interaction {
  private current: Selection = { kind: 'none' };

  /** What is selected. */
  get selection(): Selection {
    return this.current;
  }

  /** Select an element on the map. */
  selectElement(
    isoId: number,
    itemId: number,
    element: 'unit' | 'building',
    underConstruction = false,
  ): Selection {
    this.current = { kind: 'element', isoId, itemId, element, underConstruction };
    return this.current;
  }

  /** Begin placing a building or a unit. */
  beginPlacement(itemId: number, itemType: 'b' | 'u' | 'n' = 'b'): Selection {
    this.current = { kind: 'placement', itemId, itemType };
    return this.current;
  }

  /** Select nothing. */
  clear(): void {
    this.current = { kind: 'none' };
  }

  /**
   * Move the selected element to a tile.
   *
   * A building that is still being constructed cannot be moved: the client
   * shows the bulldoze cursor instead.
   */
  moveTo(tx: number, ty: number): Gesture {
    if (this.current.kind !== 'element') {
      return { ok: false, refusal: 'nothing-selected' };
    }
    if (this.current.underConstruction) {
      return { ok: false, refusal: 'under-construction' };
    }
    return { ok: true, command: move(this.current.isoId, tx, ty) };
  }

  /**
   * Place the building or the unit being placed.
   *
   * A stored building is placed from the store; anything else is bought
   * first, and the server prices it.
   */
  placeTo(tx: number, ty: number, fromStore = false): Gesture {
    if (this.current.kind !== 'placement') {
      return { ok: false, refusal: 'nothing-selected' };
    }
    return {
      ok: true,
      command: fromStore
        ? placeStoredItem(this.current.itemId, tx, ty)
        : buy(this.current.itemId, tx, ty, this.current.itemType),
    };
  }

  /** Collect the selected building's production. */
  collectSelected(): Gesture {
    if (this.current.kind !== 'element') {
      return { ok: false, refusal: 'nothing-selected' };
    }
    return { ok: true, command: collect(this.current.isoId) };
  }

  /** Start training in the selected building. */
  trainSelected(unitItemId?: number): Gesture {
    if (this.current.kind !== 'element') {
      return { ok: false, refusal: 'nothing-selected' };
    }
    return { ok: true, command: train(this.current.isoId, unitItemId) };
  }

  /** Upgrade the selected building. */
  upgradeSelected(): Gesture {
    if (this.current.kind !== 'element') {
      return { ok: false, refusal: 'nothing-selected' };
    }
    if (this.current.element !== 'building') {
      return { ok: false, refusal: 'not-on-the-map' };
    }
    return { ok: true, command: upgrade(this.current.isoId) };
  }
}
