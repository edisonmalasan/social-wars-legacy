/**
 * The assault loot.
 *
 * When an attack ends, the attacker gets gold and XP. The client computes
 * both and **declares** them in the `end_attack` payload (finding F5), so
 * a player can claim any amount. The server has to compute them.
 *
 * The rules are in `core/battle/Assault.as`.
 *
 * ## The gold
 *
 * The gold comes from **one** place: the victim's town hall.
 *
 * ```as3
 * if (the victim is the town hall) {
 *   if (conquest) gold = opponentPlayer.level * 100;
 *   else {
 *     pct = GOLD_STOLEN_BOTTOM_PCT + random() * (GOLD_STOLEN_TOP_PCT - GOLD_STOLEN_BOTTOM_PCT);
 *     gold = clamp(floor(opponentPlayer.gold * pct / 100), minGoldStolen(), maxGoldStolen());
 *   }
 * }
 * else gold = 0;
 * ```
 *
 * `minGoldStolen()` is 0 and `maxGoldStolen()` is the attacker's level
 * band.
 *
 * ## The XP
 *
 * ```as3
 * xp = ceil(gold * 0.05);
 * if (xp == 0 && the building is not a wall) xp = 1;
 * ```
 *
 * So a win is worth at least one XP, unless what was destroyed was a
 * wall.
 *
 * ## The caps
 *
 * Two caps are *intended*:
 *
 * - `MAX_GOLD_ASSAULT`, checked after every kill. **It is not in the
 *   config's globals at all**, so `Base.Items.globals.MAX_GOLD_ASSAULT` is
 *   `undefined`, and the comparison against `undefined` is always false.
 *   The cap never fires. That is the client's behaviour and it is
 *   reproduced here rather than "fixed", because a faithful clone that
 *   quietly changes the economy is not a faithful clone.
 * - `maxGoldStolen()`, the attacker's level band. This one does apply.
 *
 * ## The flat win
 *
 * ```as3
 * if (the player won && iGoldGained == 0) iGoldGained = 25;
 * ```
 *
 * So a win is worth at least 25 gold.
 */
import type { Random } from './random.ts';

/** The attacker's level bands, and the most gold each may take. */
export interface GoldBand {
  lvl: number;
  max: number;
}

/** The loot rules. */
export interface LootRules {
  /** The lowest percentage of the victim's gold that may be taken. */
  goldStolenBottomPct: number;
  /** The highest percentage of the victim's gold that may be taken. */
  goldStolenTopPct: number;
  /** The attacker's level bands. */
  maxGoldStolenTable: readonly GoldBand[];
  /** The flat gold a win with no loot is worth. */
  flatWinGold: number;
}

/**
 * The client's own band table.
 *
 * The duplicate `lvl: 80` is the client's, and it has a consequence: the
 * 22 500 row is **unreachable**. The loop stops at the first row whose
 * level is not below the player's, and both level-80 rows have the same
 * level, so a player of level 81 or more passes both of them and lands on
 * the 25 000 row. Reproduced as it is.
 */
export const DEFAULT_LOOT_RULES: LootRules = {
  goldStolenBottomPct: 15,
  goldStolenTopPct: 35,
  maxGoldStolenTable: [
    { lvl: 10, max: 2500 },
    { lvl: 20, max: 5000 },
    { lvl: 30, max: 7500 },
    { lvl: 40, max: 10000 },
    { lvl: 50, max: 12500 },
    { lvl: 60, max: 15000 },
    { lvl: 70, max: 17500 },
    { lvl: 80, max: 20000 },
    { lvl: 80, max: 22500 },
    { lvl: 99, max: 25000 },
  ],
  flatWinGold: 25,
};

/**
 * The most gold an attacker of a given level may take.
 *
 * Ported from `Assault.maxGoldStolen` (core/battle/Assault.as:600-628).
 */
export function maxGoldStolen(
  attackerLevel: number,
  rules: LootRules = DEFAULT_LOOT_RULES,
): number {
  const table = rules.maxGoldStolenTable;
  let index = 0;
  while (index < table.length && attackerLevel > table[index]!.lvl) {
    index += 1;
  }
  if (index < table.length) return table[index]!.max;
  // The client's loop walks off the end of the table above level 99 and
  // then reads `.max` off nothing, which throws. The clone does not crash:
  // the last band applies.
  return table.length > 0 ? table[table.length - 1]!.max : 0;
}

/**
 * The gold taken from a victim's town.
 *
 * The percentage is **random**, between the bottom and the top bands, and
 * the result is clamped to the attacker's band.
 *
 * A conquest takes a fixed amount instead: the victim's level times 100.
 */
export function stolenGold(
  victimGold: number,
  attackerLevel: number,
  random: Random,
  rules: LootRules = DEFAULT_LOOT_RULES,
): number {
  const bottom = rules.goldStolenBottomPct;
  const top = rules.goldStolenTopPct;
  const pct = bottom + random.next() * (top - bottom);
  const raw = Math.floor((victimGold * pct) / 100);
  const min = 0;
  const max = maxGoldStolen(attackerLevel, rules);
  return Math.max(Math.min(raw, max), min);
}

/** The gold a conquest takes. */
export function conquestGold(victimLevel: number): number {
  return victimLevel * 100;
}

/** What one kill is worth. */
export interface KillLoot {
  /** The gold. */
  gold: number;
  /** The XP. */
  xp: number;
}

/**
 * What destroying one thing is worth.
 *
 * The XP is 5 % of the gold, rounded up, and at least 1 for anything that
 * is not a wall.
 */
export function lootForDestroying(
  gold: number,
  options: { isWall?: boolean } = {},
): KillLoot {
  let xp = Math.ceil(gold * 0.05);
  if (xp === 0 && !options.isWall) {
    xp = 1;
  }
  return { gold, xp };
}

/**
 * The whole of an attack's loot.
 *
 * The client's own cap on the total gold is **not** applied: the constant
 * it would use is missing from the config, so the cap never fires in the
 * original. The band cap in `stolenGold` is the one that applies.
 */
export function assaultLoot(
  options: {
    /** Whether the attacker won. */
    won: boolean;
    /** The gold taken from the victim's town hall. */
    townHallGold: number;
    /** The XP from the kills. */
    xp: number;
    /** The attacker's level. */
    attackerLevel: number;
  },
  rules: LootRules = DEFAULT_LOOT_RULES,
): KillLoot {
  let gold = options.townHallGold;
  if (options.won && gold === 0) {
    gold = rules.flatWinGold;
  }
  return { gold, xp: options.xp };
}
