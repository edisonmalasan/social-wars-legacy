/**
 * The roadmap's item counts.
 *
 * The roadmap is a **list of items**, and an item that is silently
 * swallowed is worse than an item that is visibly unfinished. That
 * happened: a block-end rule that ended an item's block at the next
 * blank line ate fourteen items across two groups, because the items
 * are packed with no blank line between them.
 *
 * So the count is checked. Each group has a **floor** - the number of
 * items it had the last time somebody looked - and a group with fewer
 * items than its floor is a failure.
 *
 * The floor is a file, so raising it is a deliberate act rather than a
 * side effect of an edit.
 */

/** The roadmap's items, by group. */
export interface GroupCount {
  /** How many items the group has. */
  items: number;
  /** How many are done. */
  done: number;
  /** How many are still open. */
  open: number;
}

/** The roadmap's items, by group. */
export function groupCounts(text: string): Record<string, GroupCount> {
  const groups: Record<string, GroupCount> = {};
  let current: string | null = null;
  for (const line of text.split('\n')) {
    const match = /^## Group ([A-I])/.exec(line);
    if (match) {
      current = match[1]!;
      groups[current] ??= { items: 0, done: 0, open: 0 };
      continue;
    }
    if (!current) continue;
    if (/^\s*- \[x\]/.test(line)) {
      groups[current]!.items += 1;
      groups[current]!.done += 1;
    } else if (/^\s*- \[ \]/.test(line)) {
      groups[current]!.items += 1;
      groups[current]!.open += 1;
    }
  }
  return groups;
}

/** A group whose item count is below its floor. */
export interface BelowFloor {
  group: string;
  /** The floor. */
  minimum: number;
  /** What the group actually has. */
  actual: number;
  /** How many items are missing. */
  missing: number;
}

/**
 * The groups whose item count is below its floor.
 *
 * @param text the roadmap
 * @param floor the recorded minimum, by group
 */
export function groupsBelowFloor(
  text: string,
  floor: Record<string, number>,
): BelowFloor[] {
  const counts = groupCounts(text);
  const below: BelowFloor[] = [];
  for (const [group, minimum] of Object.entries(floor)) {
    const actual = counts[group]?.items ?? 0;
    if (actual < minimum) {
      below.push({ group, minimum, actual, missing: minimum - actual });
    }
  }
  return below;
}

/** The floor, as it should be recorded. */
export function floorFor(text: string): Record<string, number> {
  const counts = groupCounts(text);
  const floor: Record<string, number> = {};
  for (const [group, count] of Object.entries(counts)) {
    floor[group] = count.items;
  }
  return floor;
}
