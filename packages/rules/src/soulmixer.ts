/**
 * Atom Fusion (the "soul mixer"): the pure rules behind the mixing popup.
 *
 * The specification is the client, `popups/PopupSoulMixer.as` (client 1.5.4),
 * not the upstream Python server — the upstream server has no fusion at all.
 * The relevant methods are `generateResultUnit()` (lines 465-507),
 * `getUnitIndexByPower()` (509-531), `isUnitExcluded()` (533-546),
 * `getResultPower()` (548-561), `applyPowerup()` (563-593) and
 * `checkLegacy()` (628-638). `core/Utils.as:57-60` supplies
 * `getRandom(lo, hi) = Math.random() * (hi - lo + 1) + lo`.
 *
 * The client rolls its randomness with `Math.random()`. Here every roll is
 * taken from an injected seedable source instead, so a fusion can be
 * re-derived server-side from the same seed. The arithmetic is otherwise
 * literal: the same `ceil`, `floor`, `0.3`/`0.7` weights, the 10 floor, the
 * 220 redraw and the power-up order increments.
 *
 * ` breeding_order` comes from the content pipeline
 * (`tools/atom_fusion_builder.py`: `min(floor(life/20), 240)`, with
 * `sm_training_time = 2000 * breeding_order` seconds). Items with a
 * `breeding_order` of zero or less are not candidates, and neither are the
 * two inputs, any earlier result, or the units excluded by the builder
 * (`tools/atom_fusion_excluded_units.json`).
 *
 * No I/O, no wall clock, no unseeded randomness: everything is a function of
 * the catalog, the inputs and the injected random source.
 */

/** The part of a random source the rules need. `Random` satisfies this. */
export interface SoulMixerRandom {
  /** The next value in [0, 1). */
  next(): number;
}

/** A content item as the mixer sees it. */
export interface SoulMixerItemData {
  id: number;
  /** The upstream `breeding_order`; content sometimes stores it as text. */
  breeding_order: number | string;
}

/** One selectable unit: its id and its `breeding_order`, used as power. */
export interface SoulMixerCandidate {
  id: number;
  power: number;
}

/** The prepared candidate list, sorted ascending by power. */
export interface SoulMixerCatalog {
  candidates: SoulMixerCandidate[];
  /** The largest `breeding_order` of any candidate. */
  maxPower: number;
  /** Power by item id, for the two units being mixed. */
  powerById: Map<number, number>;
}

/** One entry of `globals.SOUL_MIXER_POWERUPS_LEVELS`. */
export interface SoulMixerPowerupLevel {
  cash_cost: number;
  order_increment: number;
}

/** The six power-up levels from `config/patch/atom_fusion_powerup.json`. */
export const SOUL_MIXER_POWERUPS: readonly SoulMixerPowerupLevel[] = [
  { cash_cost: 1, order_increment: 1 },
  { cash_cost: 2, order_increment: 2 },
  { cash_cost: 4, order_increment: 4 },
  { cash_cost: 8, order_increment: 8 },
  { cash_cost: 15, order_increment: 15 },
  { cash_cost: 20, order_increment: 20 },
];

/** The client's high-power threshold (`if (_loc4_ > 220)`). */
export const SOUL_MIXER_HIGH_POWER = 220;

/** `Constants.ID_UNIT_METALLIC_RED_DRAGON`. */
export const ID_UNIT_METALLIC_RED_DRAGON = 1226;

/** `Constants.ID_UNIT_SPARTAN_MECH`. */
export const ID_UNIT_SPARTAN_MECH = 1263;

/** The literal text of the client's pre-level-20 refusal. */
export const SOUL_MIXER_LEVEL20_GATE_MESSAGE =
  "Neither Spartan Mech or Red Metallic Dragon can't be mixed before you reach level 20";

function integer(value: number | string): number {
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? Math.trunc(number) : 0;
}

function clampLevel(levelIndex: number): number {
  if (!Number.isFinite(levelIndex)) return 0;
  return Math.min(Math.max(Math.trunc(levelIndex), 0), SOUL_MIXER_POWERUPS.length - 1);
}

/**
 * Prepare the candidate list: keep only units with a positive
 * `breeding_order`, sort them ascending by power, and record the maximum.
 *
 * Mirrors the loop and `sortOn("power", Array.NUMERIC)` in
 * `generateResultUnit()`. The upstream builder's exclusion list has already
 * removed its units from the content, so only `breeding_order > 0` needs
 * checking here.
 */
export function buildSoulMixerCatalog(items: readonly SoulMixerItemData[]): SoulMixerCatalog {
  const candidates: SoulMixerCandidate[] = [];
  const powerById = new Map<number, number>();
  let maxPower = 0;
  for (const item of items) {
    const power = integer(item.breeding_order);
    if (power <= 0) continue;
    candidates.push({ id: item.id, power });
    powerById.set(item.id, power);
    if (power > maxPower) maxPower = power;
  }
  // JavaScript's sort is stable; equal powers keep their content order.
  candidates.sort((a, b) => a.power - b.power);
  return { candidates, maxPower, powerById };
}

/**
 * `getResultPower()` plus the high-power redraw from `generateResultUnit()`.
 *
 * `Utils.getRandom(0, 12)` is `random * 13`, so its floor is one draw of
 * `rng.next()`. The redraw over `[220, maxPower]` is likewise one draw.
 * Both draws are taken from the injected source, in the client's order.
 */
export function soulMixerResultPower(
  a: number,
  b: number,
  maxPower: number,
  rng: SoulMixerRandom,
): number {
  const low = Math.min(a, b);
  const high = Math.max(a, b);
  let power = Math.ceil(low * 0.3 + high * 0.7);
  if (power < 10) power = 10;
  power += Math.floor(rng.next() * 13);
  if (power === high) power++;
  if (power > SOUL_MIXER_HIGH_POWER) {
    power = Math.floor(
      rng.next() * (maxPower - SOUL_MIXER_HIGH_POWER + 1) + SOUL_MIXER_HIGH_POWER,
    );
  }
  return power;
}

/**
 * The first non-excluded candidate with `power >= p`, or the last index when
 * none qualifies (`getUnitIndexByPower()`). An empty list yields `-1`, as it
 * does in the AS3.
 */
export function getUnitIndexByPower(
  candidates: readonly SoulMixerCandidate[],
  power: number,
  excluded: ReadonlySet<number>,
): number {
  for (let index = 0; index < candidates.length; index++) {
    const candidate = candidates[index]!;
    if (!excluded.has(candidate.id) && candidate.power >= power) return index;
  }
  return candidates.length - 1;
}

/** The candidate at an index, with a clear failure for an invalid one. */
function pickAt(catalog: SoulMixerCatalog, index: number): SoulMixerPick {
  const candidate = catalog.candidates[index];
  if (index < 0 || candidate === undefined) throw new RangeError('no soul mixer candidate at that index');
  return { index, id: candidate.id, power: candidate.power };
}

/** A chosen unit: its index in the sorted list, id and power. */
export interface SoulMixerPick {
  index: number;
  id: number;
  power: number;
}

/**
 * Mix two units. The two inputs and every id in `priorResults` are excluded,
 * so neither an input nor an earlier result can be produced again.
 */
export function mixUnits(
  catalog: SoulMixerCatalog,
  inputA: number,
  inputB: number,
  rng: SoulMixerRandom,
  priorResults: readonly number[] = [],
): SoulMixerPick {
  if (catalog.candidates.length === 0) throw new RangeError('empty soul mixer catalog');
  const a = catalog.powerById.get(inputA);
  const b = catalog.powerById.get(inputB);
  if (a === undefined || b === undefined) throw new RangeError('soul mixer input is not a candidate');
  const excluded = new Set<number>([inputA, inputB, ...priorResults]);
  const power = soulMixerResultPower(a, b, catalog.maxPower, rng);
  return pickAt(catalog, getUnitIndexByPower(catalog.candidates, power, excluded));
}

/**
 * One `applyPowerup()` step. The current unit and every id in `excludedIds`
 * cannot be chosen again. Below 220 the chosen index is advanced by the
 * level's `order_increment`; at or above 220 a fresh power is drawn over
 * `[220, maxPower]` instead.
 */
export function applySoulMixerPowerup(
  catalog: SoulMixerCatalog,
  current: SoulMixerCandidate,
  levelIndex: number,
  rng: SoulMixerRandom,
  excludedIds: Iterable<number> = [],
): SoulMixerPick {
  if (catalog.candidates.length === 0) throw new RangeError('empty soul mixer catalog');
  const excluded = new Set<number>(excludedIds);
  excluded.add(current.id);
  const level = clampLevel(levelIndex);
  let index: number;
  if (current.power >= SOUL_MIXER_HIGH_POWER) {
    const power = Math.floor(
      rng.next() * (catalog.maxPower - SOUL_MIXER_HIGH_POWER + 1) + SOUL_MIXER_HIGH_POWER,
    );
    index = getUnitIndexByPower(catalog.candidates, power, excluded);
  } else {
    index = getUnitIndexByPower(catalog.candidates, current.power, excluded);
    index += SOUL_MIXER_POWERUPS[level]!.order_increment;
    // The AS3 walks forward over excluded units. Stop at the last candidate
    // rather than indexing past the end; the client would fault there.
    while (index < catalog.candidates.length - 1 && excluded.has(catalog.candidates[index]!.id)) {
      index++;
    }
  }
  return pickAt(catalog, index);
}

/** The cash price of a power-up level, clamped to the six shipped levels. */
export function soulMixerCashCost(levelIndex: number): number {
  return SOUL_MIXER_POWERUPS[clampLevel(levelIndex)]!.cash_cost;
}

/** The whole fusion: the mix followed by the requested power-ups. */
export interface SoulMixerOutcome {
  result: SoulMixerPick;
  powerups: SoulMixerPick[];
  /** Every id that has been consumed or produced. */
  excludedIds: number[];
}

/**
 * Run `mixUnits()` and then each requested power-up in order, accumulating
 * exclusions exactly as the popup does (`_excludedUnitsIds` grows on every
 * step). `powerupLevels` is a list of level indices, one per `buy_powerups`
 * command the client sends.
 */
export function fuseWithPowerups(
  catalog: SoulMixerCatalog,
  inputA: number,
  inputB: number,
  powerupLevels: readonly number[],
  rng: SoulMixerRandom,
  priorResults: readonly number[] = [],
): SoulMixerOutcome {
  const result = mixUnits(catalog, inputA, inputB, rng, priorResults);
  const excluded = new Set<number>([inputA, inputB, ...priorResults, result.id]);
  const powerups: SoulMixerPick[] = [];
  let current = result;
  for (const level of powerupLevels) {
    const next = applySoulMixerPowerup(catalog, current, level, rng, excluded);
    powerups.push(next);
    excluded.add(next.id);
    current = next;
  }
  return { result, powerups, excludedIds: [...excluded] };
}

/** The result of the popup's `checkLegacy()` gate. */
export interface Level20GateResult {
  allowed: boolean;
  /** The client's literal message when refused; `null` when allowed. */
  message: string | null;
}

/**
 * Below level 20, a Red Metallic Dragon (1226) or a Spartan Mech (1263) in
 * either slot refuses the fusion. Returns the refused state rather than
 * throwing, so the caller can surface the client's exact message.
 */
export function checkSoulMixerLevel20Gate(
  level: number,
  inputA: number,
  inputB: number,
): Level20GateResult {
  const blocked =
    level < 20 &&
    (inputA === ID_UNIT_METALLIC_RED_DRAGON ||
      inputB === ID_UNIT_METALLIC_RED_DRAGON ||
      inputA === ID_UNIT_SPARTAN_MECH ||
      inputB === ID_UNIT_SPARTAN_MECH);
  return blocked
    ? { allowed: false, message: SOUL_MIXER_LEVEL20_GATE_MESSAGE }
    : { allowed: true, message: null };
}

/** The cash the popup shows for a speed-up (`ceil(timeLeft / 3600)`). */
export function soulMixerSpeedupCost(smTrainingTime: number, elapsedSeconds: number): number {
  return Math.max(0, Math.ceil((smTrainingTime - elapsedSeconds) / 3600));
}

/** `breeding_order = min(floor(life / 20), 240)` from the upstream builder. */
export function breedingOrderFromLife(life: number): number {
  return Math.min(Math.floor(life / 20), 240);
}

/** `sm_training_time = 2000 * breeding_order`, in seconds. */
export function soulMixerTrainingTime(breedingOrder: number): number {
  return 2000 * breedingOrder;
}
