/**
 * The build menu.
 *
 * The build window is a set of **tabs**, one per category, and each tab
 * lists the items of that category. The list's order is the client's, and
 * it is not the order the content is in:
 *
 * ```as3
 * building.sortInt = parseInt(building.display_order);
 * if (!itemUnlocked(building.id) && parseInt(building.min_level) > Player.iLevel) {
 *   building.sortInt += 10000;
 * }
 * buildingArray.sortOn(["sortInt"], Array.NUMERIC);
 * ```
 *
 * (`GUI/BuildingWindow.as:331-341`.)
 *
 * Two details:
 *
 * - `itemUnlocked` **always returns false** in this build
 *   (`core/Base.as:7993-7995`), so the condition is simply "the player is
 *   too low a level for it". The clone reproduces that rather than
 *   inventing an unlock system the client does not have.
 * - the items that are too low a level are pushed **10 000 down the
 *   list**, not hidden: the player can still see them, further down, and
 *   knows they exist.
 */
import type { Resources } from '@swl/rules';

/** An item the build menu can show. */
export interface BuildMenuItem {
  id: number;
  name: string;
  /** The category the item belongs to, which is the tab. */
  categoryId: number;
  /** The sub-category within the tab. */
  subcategoryId: number;
  /** Where the item sits in the list. */
  displayOrder: number;
  /** The level the player must be at. */
  minLevel: number;
  /** The build cost, by resource key. */
  costs: Resources;
  /** Seconds to build. */
  buildTime: number;
  /** How many clicks the build needs. 0 means instant. */
  clicksToBuild: number;
  /** Whether the item can be bought with cash. */
  inStore: boolean;
}

/** One entry of the build menu. */
export interface BuildMenuEntry extends BuildMenuItem {
  /** Whether the player is too low a level for it. */
  locked: boolean;
  /** The sort key the client uses. */
  sortInt: number;
}

/** How far down the list an item the player cannot afford yet goes. */
export const LOCKED_OFFSET = 10_000;

/**
 * The sort key the client gives an item.
 *
 * The locked items are pushed down the list by 10 000, so they keep their
 * order relative to each other and appear after everything the player can
 * actually build.
 */
export function sortKey(item: BuildMenuItem, playerLevel: number): number {
  const locked = item.minLevel > playerLevel;
  return item.displayOrder + (locked ? LOCKED_OFFSET : 0);
}

/**
 * The build menu for one category.
 *
 * The order is the client's, and it is stable: two items with the same
 * sort key keep the order they came in.
 */
export function buildMenu(
  items: readonly BuildMenuItem[],
  playerLevel: number,
  categoryId?: number,
): BuildMenuEntry[] {
  const inCategory =
    categoryId === undefined
      ? items
      : items.filter((item) => item.categoryId === categoryId);

  const entries = inCategory.map((item) => {
    const locked = item.minLevel > playerLevel;
    return {
      ...item,
      locked,
      sortInt: item.displayOrder + (locked ? LOCKED_OFFSET : 0),
    };
  });

  // A stable sort, so the order the items came in is kept for the ones
  // that tie.
  return entries
    .map((entry, index) => ({ entry, index }))
    .sort((a, b) => a.entry.sortInt - b.entry.sortInt || a.index - b.index)
    .map(({ entry }) => entry);
}

/** A category, and its sub-categories. */
export interface BuildTab {
  id: number;
  name: string;
  /** The sub-categories within it. */
  subcategories: { id: number; name: string }[];
}

/**
 * The build menu's tabs.
 *
 * The client's tabs are the **sub-categories**, and the category is the
 * group they hang off.
 */
export function buildTabs(
  categories: Record<string, { id: number; name: string; sub?: { id: number; name: string }[] }>,
): BuildTab[] {
  return Object.values(categories)
    .map((category) => ({
      id: category.id,
      name: category.name,
      subcategories: (category.sub ?? []).map((sub) => ({ id: sub.id, name: sub.name })),
    }))
    .sort((a, b) => a.id - b.id);
}
