/**
 * The HUD's model.
 *
 * The top bar shows the player's resources, their level, their population
 * and their energy, and each of them opens a popover that explains the
 * number. This module is the **model** of that: what the HUD shows, where
 * each number comes from, and what each popover says.
 *
 * It is a model and not a renderer on purpose. The rendering needs PixiJS
 * and a browser, and the *content* — the texts, the thresholds, the number
 * formatting — is the part that has to be exactly right, and that can be
 * tested.
 *
 * ## The number formatting
 *
 * From `GUI/GuiManager.as:1046`:
 *
 * ```as3
 * var text = "" + value;
 * var groups = [];
 * while (text.length > 0) {
 *   var at = Math.max(text.length - 3, 0);
 *   groups.unshift(text.slice(at, text.length));
 *   text.length = at;
 * }
 * return groups.join(",");
 * ```
 *
 * The digits are grouped in threes from the right and joined with commas.
 * It groups the **string**, so a negative number comes out as "-1,234"
 * rather than "-1,234" with the sign outside the first group — which is
 * the same thing here, but it is worth knowing that the algorithm is
 * textual.
 */

/** A number, formatted the client's way. */
export function formatNumber(value: number): string {
  const text = String(value);
  const groups: string[] = [];
  let at = text.length;
  while (at > 0) {
    const from = Math.max(at - 3, 0);
    groups.unshift(text.slice(from, at));
    at = from;
  }
  return groups.join(',');
}

/** The resources the HUD shows. */
export type HudResource = 'gold' | 'wood' | 'oil' | 'steel' | 'cash';

/** The player's state, as the HUD reads it. */
export interface HudState {
  /** The player's gold. */
  gold: number;
  /** The gold a silo holds. */
  maxGold: number;
  wood: number;
  maxWood: number;
  oil: number;
  maxOil: number;
  steel: number;
  maxSteel: number;
  cash: number;
  /** The population the player's buildings and units use. */
  population: number;
  /** The population the player's current level allows. */
  populationMaxCurrent: number;
  /** The most population any level allows. */
  populationMaxAllowed: number;
  /** The player's level. */
  level: number;
  /** The XP towards the next level. */
  experience: number;
  /** The XP the next level needs. */
  expRequired: number;
  /** The energy the player has. */
  energy: number;
  /** The most energy the player may hold. */
  maxEnergy: number;
}

/** A popover's two lines. */
export interface Popover {
  /** The line that says what the number is. */
  firstLine: string;
  /** The line that says what to do about it, when there is something. */
  warningLine: string | null;
}

/** The popover for a resource. */
export function resourcePopover(state: HudState, resource: HudResource): Popover {
  if (resource === 'cash') {
    // Cash has no maximum, so it has no warning.
    return { firstLine: `You have ${formatNumber(state.cash)} of cash`, warningLine: null };
  }
  const current = state[resource];
  const max = state[`max${resource[0]!.toUpperCase()}${resource.slice(1)}` as 'maxGold'];
  const full = current >= max;
  return {
    firstLine: `You have ${formatNumber(current)} / ${formatNumber(max)} of ${resource}`,
    warningLine: full ? 'Build more Silos to get more space' : null,
  };
}

/** The population popover. */
export function populationPopover(state: HudState): Popover {
  const atTheLimit = state.population >= state.populationMaxCurrent;
  const atTheAbsoluteLimit = state.population >= state.populationMaxAllowed;

  if (atTheAbsoluteLimit) {
    return {
      firstLine: "You've reached the max population",
      warningLine: `Reach level ${state.level + 1} to get an increase of ${3} in population limit`,
    };
  }
  return {
    firstLine:
      `You have ${formatNumber(state.population)} / ${formatNumber(state.populationMaxCurrent)} ` +
      'of population\nBuild more houses to increase this limit',
    warningLine: atTheLimit ? 'Build more Houses to get more population' : null,
  };
}

/** The experience popover. */
export function experiencePopover(state: HudState): Popover {
  return {
    firstLine: `You need ${formatNumber(state.expRequired - state.experience)} XP to reach level ${state.level + 1}`,
    warningLine: null,
  };
}

/** The army text in the top bar: the population over the limit. */
export function armyText(state: HudState): string {
  return `${state.population}/${state.populationMaxCurrent}`;
}

/**
 * The energy's state.
 *
 * The client shows the energy as a bar that refills over time, and the
 * bar's colour changes as the energy runs out. The rules are the energy
 * rules in `packages/rules/src/economy.ts`.
 */
export interface EnergyDisplay {
  /** The energy the player has. */
  energy: number;
  /** The most the player may hold. */
  max: number;
  /** The fraction of the bar that is full, 0 to 1. */
  fraction: number;
  /** Whether the energy is low enough that the client warns. */
  low: boolean;
}

/** The energy the HUD shows. */
export function energyDisplay(state: HudState): EnergyDisplay {
  const max = Math.max(1, state.maxEnergy);
  const fraction = Math.max(0, Math.min(1, state.energy / max));
  return {
    energy: state.energy,
    max: state.maxEnergy,
    fraction,
    // The client warns when the energy is below a fifth of the maximum.
    low: fraction <= 0.2,
  };
}
