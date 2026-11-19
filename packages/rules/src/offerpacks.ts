/**
 * Offer packs: the store's bundles of buildings, units and resources.
 *
 * The original client owns almost all of this logic. `PromotionPacks.as`
 * decides which pack is flat, random or super, which super tier a selection
 * means, and what each tier costs. The upstream server then believes the
 * client's item list and credits whatever it names
 * (`upstream/socialwarriors/command.py`, `buy_offer_pack`).
 *
 * This module is the server-side replacement for that trust. It reads the
 * pack's **content** shape and derives the price and the reward from it:
 *
 * - a **flat** pack grants every item in its list;
 * - a **random** pack rolls once against the list's thresholds;
 * - a **super** pack has three rarity rows, and the number of items the
 *   client selected chooses the tier (1, 2 or 4 items);
 * - a **premium** pack is not an item pack at all: it opens the premium
 *   purchase flow, so `buy_offer_pack` must never sell it.
 *
 * The selection list is only a **tier selector**. Its item ids are never
 * granted, because a client could otherwise name any item it liked.
 */

import type { Random } from './random.ts';

/** The shapes the content's `items` column takes for an offer pack. */
export type OfferPackItems = number[] | [number, number][] | number[][];

/** One offer pack, as the content bundle stores it. */
export interface OfferPackData {
  id: number;
  name: string;
  /** `''`, `premium_account` or `super`. */
  type?: string;
  /** The content's 1/0 flag. A missing value is treated as enabled. */
  enabled?: number | boolean;
  /** The store position. Zero means hidden. */
  position?: number;
  cost_cash: number;
  gold: number;
  wood: number;
  oil: number;
  steel: number;
  mana: number;
  xp: number;
  items: OfferPackItems | null;
}

/** How a pack's items are granted. */
export type OfferPackShape = 'flat' | 'random' | 'super' | 'premium';

/**
 * The packs the client treats as random packs.
 *
 * The content leaves pack 4's `type` empty, so the client's own id list is
 * the authority (`PromotionPacks.RANDOM_PACK_IDS`).
 */
export const RANDOM_PACK_IDS: readonly number[] = [4];

/**
 * The packs the client treats as super packs.
 *
 * The content leaves pack 19's `type` empty, so the client's own id list is
 * the authority (`PromotionPacks.SUPER_PACK_IDS`).
 */
export const SUPER_PACK_IDS: readonly number[] = [6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 19, 20];

/** The default cash prices for the three super tiers. */
export const SUPER_PACK_PRICES: readonly number[] = [60, 100, 200];

/** The per-pack price overrides (`PromotionPacks.PACK_PRICES`). */
export const SUPER_PACK_PRICE_OVERRIDES: Readonly<Record<number, readonly number[]>> = {
  19: [30, 60, 100],
};

/** The random source the rolls need. `Random` satisfies it. */
export interface OfferPackRandom {
  next(): number;
  int(min: number, max: number): number;
}

/** Which kind of pack this is. */
export function offerPackShape(pack: Pick<OfferPackData, 'id' | 'type'>): OfferPackShape {
  if (pack.type === 'premium_account') return 'premium';
  if (pack.type === 'super' || SUPER_PACK_IDS.includes(pack.id)) return 'super';
  if (RANDOM_PACK_IDS.includes(pack.id)) return 'random';
  return 'flat';
}

/**
 * Whether the store may sell this pack at all.
 *
 * The client hides a pack whose `enabled` flag is zero or whose position is
 * zero. A missing field is not a reason to hide a pack from a hand-written
 * content bundle, so only an explicit zero hides it.
 */
export function isOfferPackAvailable(pack: OfferPackData): boolean {
  if (pack.enabled !== undefined && Number(pack.enabled) === 0) return false;
  if (pack.position !== undefined && Number(pack.position) <= 0) return false;
  return true;
}

/** The tier a super pack's selected-item count means, or null. */
export function offerPackTierForCount(pack: OfferPackData, count: number): number | null {
  if (offerPackShape(pack) !== 'super') return null;
  if (count === 1) return 0;
  if (count === 2) return 1;
  if (count === 4) return 2;
  return null;
}

/**
 * The cash price of a pack at a tier.
 *
 * A flat or random pack has one price. A super pack's price is the tier's,
 * with pack 19's own override. `null` means the pack cannot be priced, and
 * the caller must refuse it rather than sell it for nothing.
 */
export function offerPackPrice(pack: OfferPackData, tier: number | null): number | null {
  const shape = offerPackShape(pack);
  if (shape === 'premium') return null;

  if (shape === 'super') {
    if (tier === null || !Number.isInteger(tier) || tier < 0 || tier > 2) return null;
    const prices = SUPER_PACK_PRICE_OVERRIDES[pack.id] ?? SUPER_PACK_PRICES;
    const price = prices[tier];
    return typeof price === 'number' && Number.isFinite(price) && price >= 0 ? price : null;
  }

  const price = Number(pack.cost_cash);
  return Number.isFinite(price) && price >= 0 ? price : null;
}

/**
 * Parse the command's selected-item argument.
 *
 * The legacy command sends a JSON string; the native command may send an
 * array. Either is accepted, but anything else is not a selection.
 */
export function parseOfferPackSelection(value: unknown): unknown[] | null {
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string') return null;
  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isItemId(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

function flatItems(items: OfferPackData['items']): number[] | null {
  if (!Array.isArray(items)) return null;
  const out: number[] = [];
  for (const value of items) {
    if (!isItemId(value)) return null;
    out.push(value);
  }
  return out;
}

function randomItems(items: OfferPackData['items']): [number, number][] | null {
  if (!Array.isArray(items)) return null;
  const out: [number, number][] = [];
  for (const pair of items) {
    if (!Array.isArray(pair) || pair.length !== 2) return null;
    const [id, threshold] = pair;
    if (
      !isItemId(id) ||
      typeof threshold !== 'number' ||
      !Number.isFinite(threshold) ||
      threshold < 0 ||
      threshold > 100
    ) {
      return null;
    }
    out.push([id, threshold]);
  }
  return out.length > 0 ? out : null;
}

function superRows(items: OfferPackData['items']): number[][] | null {
  if (!Array.isArray(items) || items.length !== 3) return null;
  const rows: number[][] = [];
  for (const row of items) {
    if (!Array.isArray(row)) return null;
    const ids: number[] = [];
    for (const id of row) {
      if (!isItemId(id)) return null;
      ids.push(id);
    }
    rows.push(ids);
  }
  return rows;
}

/**
 * Every item a pack could grant, or null when its content is malformed.
 *
 * The caller uses this to prove every possible reward exists **before** it
 * rolls or mutates the store. A malformed id such as `1072.1224` is
 * therefore refused rather than turned into an unplaceable store entry.
 */
export function offerPackCandidates(pack: OfferPackData): number[] | null {
  switch (offerPackShape(pack)) {
    case 'flat':
      return flatItems(pack.items);
    case 'random': {
      const pairs = randomItems(pack.items);
      return pairs === null ? null : pairs.map(([id]) => id);
    }
    case 'super': {
      const rows = superRows(pack.items);
      return rows === null ? null : rows.flat();
    }
    case 'premium':
      return null;
  }
}

/**
 * Roll a pack's reward.
 *
 * Flat packs grant their whole list. Random packs roll `Math.random() * 100`
 * against the thresholds, as `PromotionPacks.buyPack` does. Super packs use
 * the tier's rows:
 *
 * - tier 0: one item from the uncommon/common rows;
 * - tier 1: one item from all three rows, weighted by row length, plus one
 *   from uncommon/common;
 * - tier 2: one rare item plus three from uncommon/common.
 *
 * The original uses `Math.round` to index the rows, which makes the end
 * items half as likely. This implementation uses a uniform pick: the
 * distribution is a server choice, while the **shape** of the reward is the
 * client's.
 *
 * The result is null when the pack is malformed or the tier is invalid.
 */
export function offerPackRewardItems(
  pack: OfferPackData,
  tier: number | null,
  random: OfferPackRandom,
): number[] | null {
  const shape = offerPackShape(pack);

  if (shape === 'flat') return flatItems(pack.items);

  if (shape === 'random') {
    const pairs = randomItems(pack.items);
    if (pairs === null) return null;
    if (!pairs.some(([, threshold]) => threshold > 0)) return null;

    const roll = random.next() * 100;
    for (const [id, threshold] of pairs) {
      if (roll < threshold) return [id];
    }
    // The content's last threshold is 100, so this is only a fallback for a
    // hand-written table that never reaches 100.
    return [pairs[pairs.length - 1]![0]];
  }

  if (shape === 'super') {
    if (tier === null || !Number.isInteger(tier) || tier < 0 || tier > 2) return null;
    const rows = superRows(pack.items);
    if (rows === null) return null;

    const uncommon = [...rows[1]!, ...rows[2]!];
    if (uncommon.length === 0) return null;
    const pick = (pool: readonly number[]): number =>
      pool[random.int(0, pool.length - 1)]!;

    if (tier === 0) return [pick(uncommon)];

    if (tier === 1) {
      const all = [...rows[0]!, ...uncommon];
      return [pick(all), pick(uncommon)];
    }

    if (rows[0]!.length === 0) return null;
    return [pick(rows[0]!), pick(uncommon), pick(uncommon), pick(uncommon)];
  }

  return null;
}

/** The seed a server-side roll uses. Kept here so cost and applier agree. */
export function offerPackSeed(
  packId: number,
  tier: number | null,
  commandNumber: number,
  rollNumber: number,
): string {
  return `offer-pack:${packId}:${tier ?? 'flat'}:${commandNumber}:${rollNumber}`;
}

/** A convenience type for callers that already have a `Random`. */
export type OfferPackRng = Random;
