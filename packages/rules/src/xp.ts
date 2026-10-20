/**
 * Unit XP and levelling.
 *
 * A unit that fights earns XP equal to the **effective damage it deals to enemy
 * units**. Damage dealt to buildings earns nothing.
 *
 * The table lives in the config as `globals.UNIT_XP_LEVELS_MULTIPLIERS_10`:
 * one row per level, each `[xpMultiplier, flatAttackBonus, lifePercentBonus,
 * cashDivisor]`.
 *
 * ```
 * level  xp multiplier  flat attack  life %  cash divisor
 *   0            0              0       0        -
 *   1            5              2      20       50
 *   2           10              2      20       25
 *   3           20              3      20       12
 *   4           40              3      20        6
 *   5           65              4      20        4
 *   6           95              4      25        3
 *   7          125              4      25      2.5
 *   8          160              4      25        2
 *   9          200              4      25      1.5
 * ```
 *
 * Ported from `core/UnitXPLevelInfo.as`:
 *
 *   - `getRequiredXpForLevel(life, level) = table[level][0] * life`
 *   - the level is the highest `L` with `xp <= requiredXpForLevel(life, L)`
 *   - the bonuses are **cumulative** over every level passed
 *   - `maxLevel = table.length - 1`
 *
 * At the maximum level the bonuses are **+30 attack and 3x base HP**
 * (2+2+3+3+4+4+4+4+4 = 30, and 5x20% + 4x25% = 200% extra).
 *
 * Levelling up with cash costs `ceil(life / cashDivisor)` and grants exactly
 * the missing XP plus 1 (`CmdPlaceStoredItem.as:38`).
 */

/** One row of the XP table. */
export interface XpLevelRow {
  /** The XP needed for this level, as a multiple of the unit's base life. */
  xpMultiplier: number;
  /** The flat attack this level grants. */
  flatAttack: number;
  /** The percentage of base life this level grants. */
  lifePercent: number;
  /** The divisor for the cash cost of levelling into this level. */
  cashDivisor: number;
}

/** The bonuses a unit has at a given level. */
export interface LevelBonuses {
  level: number;
  /** Added to the base attack. */
  extraAttack: number;
  /** Added to the base life, as a percentage. */
  extraLifePercent: number;
  /** The total life, as a multiple of the base. */
  lifeMultiplier: number;
}

/**
 * Normalise the config's table into typed rows.
 *
 * The config stores each row as `[xpMultiplier, flatAttack, lifePercent, cashDivisor]`.
 */
export function parseXpTable(raw: unknown): XpLevelRow[] {
  if (!Array.isArray(raw)) throw new Error('UNIT_XP_LEVELS_MULTIPLIERS_10 is not an array');
  return raw.map((row, index) => {
    if (!Array.isArray(row) || row.length < 3) {
      throw new Error(`row ${index} of the XP table is malformed`);
    }
    return {
      xpMultiplier: Number(row[0]),
      flatAttack: Number(row[1]),
      lifePercent: Number(row[2]),
      cashDivisor: row.length > 3 ? Number(row[3]) : 0,
    };
  });
}

/** The XP needed to reach a level. */
export function xpForLevel(table: readonly XpLevelRow[], life: number, level: number): number {
  const row = table[level];
  if (!row) throw new RangeError(`no XP row for level ${level}`);
  return row.xpMultiplier * life;
}

/** The highest level, which is `table.length - 1`. */
export function maxLevel(table: readonly XpLevelRow[]): number {
  return table.length - 1;
}

/**
 * The level a unit has earned.
 *
 * The client walks up from level 1 and **breaks** when `xp <= required`, so a
 * unit needs one point *more* than the threshold to advance. That is exactly
 * why a paid level-up grants "the missing XP plus 1"
 * (`CmdPlaceStoredItem.as:38`).
 *
 * A consequence worth knowing: **level 9 cannot be reached by XP alone.** The
 * loop breaks at `xp <= required(9)`, so plain XP tops out at level 8; only
 * paying for the level — which grants `required(9) + 1` — reaches level 9.
 */
export function levelForXp(table: readonly XpLevelRow[], life: number, xp: number): number {
  let level = 0;
  for (let candidate = 1; candidate < table.length; candidate++) {
    if (xp <= xpForLevel(table, life, candidate)) break;
    level = candidate;
  }
  return level;
}

/**
 * The cumulative bonuses at a level.
 *
 * Every level passed contributes its flat attack and its percentage of base
 * life.
 */
export function bonusesForLevel(
  table: readonly XpLevelRow[],
  life: number,
  level: number,
): LevelBonuses {
  let extraAttack = 0;
  let extraLifePercent = 0;
  for (let candidate = 1; candidate <= level && candidate < table.length; candidate++) {
    const row = table[candidate]!;
    extraAttack += row.flatAttack;
    extraLifePercent += row.lifePercent;
  }
  return {
    level,
    extraAttack,
    extraLifePercent,
    lifeMultiplier: 1 + extraLifePercent / 100,
  };
}

/**
 * The cash cost of levelling into a level.
 *
 * `ceil(life / cashDivisor)`.
 */
export function levelUpCost(table: readonly XpLevelRow[], life: number, level: number): number {
  const row = table[level];
  if (!row) throw new RangeError(`no XP row for level ${level}`);
  if (row.cashDivisor <= 0) return 0;
  return Math.ceil(life / row.cashDivisor);
}

/**
 * The XP a level-up with cash grants.
 *
 * The client grants exactly the missing XP plus 1
 * (`CmdPlaceStoredItem.as:38`).
 */
export function xpForPaidLevelUp(
  table: readonly XpLevelRow[],
  life: number,
  level: number,
): number {
  return xpForLevel(table, life, level) + 1;
}

/**
 * The XP an attacker earns from a hit.
 *
 * XP is earned from the **effective damage dealt to a unit**. Damage dealt to
 * a building earns nothing (`IsoFightingElement.as:477-480` — the XP is only
 * awarded when the defender's `building.type == TYPE_UNIT`).
 */
export function xpEarned(effectiveDamage: number, targetIsUnit: boolean): number {
  return targetIsUnit ? effectiveDamage : 0;
}
