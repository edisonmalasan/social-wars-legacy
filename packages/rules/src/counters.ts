/**
 * The counters.
 *
 * `best_against` in the config names a *property key*, and `best_against_mult`
 * is the multiplier. An attacker whose `best_against` key is present on the
 * target's properties hits it harder.
 *
 * In the shipped content exactly **four** items have a multiplier above 1.
 * Everything else is a plain 1x, which means the "counter" is really just a
 * match/no-match test.
 *
 * | Item | Key | Multiplier |
 * |---|---|---|
 * | Antiaircraft battery | `ft_flying` | 20x |
 * | Demolition Tank | `ft_building` | 15x |
 * | Mortar Thrower | `ft_building` | 10x |
 * | B52 | `ft_building` | 5x |
 *
 * Note the sentinel: 138 offer packs and chained items carry
 * `best_against = "-1"` with a multiplier of 2. **"-1" is not a property key** —
 * no item has it — so those never counter anything. The value is a
 * "no counter" marker, not a multiplier that means something.
 */

/** The four real counters, by the id they have in the shipped config. */
export const COUNTERS = [
  { id: 1065, name: 'Antiaircraft battery', bestAgainst: 'ft_flying', multiplier: 20 },
  { id: 1069, name: 'Demolition Tank', bestAgainst: 'ft_building', multiplier: 15 },
  { id: 1060, name: 'Mortar Thrower', bestAgainst: 'ft_building', multiplier: 10 },
  { id: 1068, name: 'B52', bestAgainst: 'ft_building', multiplier: 5 },
] as const;

/** The sentinel the config uses for "this item has no counter". */
export const NO_COUNTER = '-1';

/**
 * The multiplier an attacker applies to a target.
 *
 * Returns 1 when the attacker has no counter, when its `best_against` is the
 * "no counter" sentinel, or when the target does not carry the key.
 */
export function counterMultiplier(
  attacker: { bestAgainst: string | null; multiplier: number },
  targetProperties: Readonly<Record<string, unknown>>,
): number {
  if (!attacker.bestAgainst) return 1;
  if (attacker.bestAgainst === NO_COUNTER) return 1;
  if (!(attacker.bestAgainst in targetProperties)) return 1;
  return attacker.multiplier > 1 ? attacker.multiplier : 1;
}
