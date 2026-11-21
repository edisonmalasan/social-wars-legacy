/**
 * The store screens' model: the offer packs the client may show and the
 * commands that ask to buy them.
 *
 * Every price, shape, selection rule and reward comes from the client's own
 * rules and the server's content. This module only reads them and builds the
 * **request**; it never credits an item or spends cash. The premium pack is
 * left out entirely: it opens a real-money flow, which this client does not
 * implement.
 */
import {
  isOfferPackAvailable,
  offerPackCandidates,
  offerPackPrice,
  offerPackShape,
  offerPackTierForCount,
  type OfferPackData,
  type OfferPackShape,
} from '@swl/rules';

import { buyOfferPack, type NativeCommand } from './requests.ts';

/** One buyable tier of a super pack. */
export interface StoreTierView {
  /** How many items the player selects, which is the tier the server prices. */
  readonly count: number;
  /** The cash price of this tier, from the client's own table. */
  readonly price: number;
  /** Whether the player's wallet can cover it. Presentation only. */
  readonly affordable: boolean;
  /** The request that asks the server to buy at this tier. */
  readonly command: NativeCommand;
}

/** One offer pack as the store can draw it. */
export interface StorePackView {
  readonly id: number;
  readonly name: string;
  readonly shape: OfferPackShape;
  /** The price of a flat or random pack; null for a super pack. */
  readonly price: number | null;
  /** Whether the wallet covers the base price. */
  readonly affordable: boolean;
  /** The three selections a super pack accepts; empty for other shapes. */
  readonly tiers: readonly StoreTierView[];
  /** The request for a flat or random pack; null for a super pack. */
  readonly command: NativeCommand | null;
}

/** Read a content row only when it really is an offer pack. */
function asPack(value: unknown): OfferPackData | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const row = value as Record<string, unknown>;
  const id = row['id'];
  const name = row['name'];
  const cost = row['cost_cash'];
  if (
    typeof id !== 'number' || !Number.isInteger(id) || id <= 0 ||
    typeof name !== 'string' || name.length === 0 ||
    typeof cost !== 'number' || !Number.isFinite(cost) || cost < 0
  ) {
    return null;
  }
  return {
    id,
    name,
    type: typeof row['type'] === 'string' ? row['type'] : '',
    enabled: typeof row['enabled'] === 'number' ? row['enabled'] : undefined,
    position: typeof row['position'] === 'number' ? row['position'] : undefined,
    cost_cash: cost,
    gold: Number(row['gold']) || 0,
    wood: Number(row['wood']) || 0,
    oil: Number(row['oil']) || 0,
    steel: Number(row['steel']) || 0,
    mana: Number(row['mana']) || 0,
    xp: Number(row['xp']) || 0,
    items: Array.isArray(row['items']) ? (row['items'] as OfferPackData['items']) : null,
  };
}

/**
 * The store's packs, in the content's order.
 *
 * Unavailable and premium packs are left out. A super tier whose selection
 * cannot be formed from the pack's own candidates is left out too, so no buy
 * button is drawn for a request the server would refuse.
 */
export function storePacks(raw: readonly unknown[], cash: number): readonly StorePackView[] {
  const out: StorePackView[] = [];
  for (const entry of raw) {
    const pack = asPack(entry);
    if (!pack || !isOfferPackAvailable(pack)) continue;
    const shape = offerPackShape(pack);
    if (shape === 'premium') continue;
    const candidates = offerPackCandidates(pack) ?? [];

    if (shape === 'super') {
      const tiers: StoreTierView[] = [];
      for (const count of [1, 2, 4]) {
        const tier = offerPackTierForCount(pack, count);
        const price = tier === null ? null : offerPackPrice(pack, tier);
        if (tier === null || price === null || candidates.length < count) continue;
        tiers.push({
          count,
          price,
          affordable: cash >= price,
          command: buyOfferPack(pack.id, candidates.slice(0, count)),
        });
      }
      out.push({
        id: pack.id,
        name: pack.name,
        shape,
        price: null,
        affordable: false,
        tiers,
        command: null,
      });
      continue;
    }

    const price = offerPackPrice(pack, null);
    if (price === null) continue;
    out.push({
      id: pack.id,
      name: pack.name,
      shape,
      price,
      affordable: cash >= price,
      tiers: [],
      command: buyOfferPack(pack.id, candidates),
    });
  }
  return out;
}
