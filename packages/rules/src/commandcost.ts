/**
 * Server-computed command costs.
 *
 * This is the anti-cheat core.
 *
 * The original protocol has the **client** declare the resource delta for
 * every command: the `command.php` body carries a `res` vector, and the
 * upstream server applies it verbatim. A player can therefore send
 * `"res": [0, 0, 1000000, 0, 0, 0, 0, 0]` with a `buy` and simply be
 * given a million gold. That is finding F3, and non-negotiable 3 exists
 * to prevent it.
 *
 * So the clone does the opposite: **the server computes the cost from the
 * content bundle and the command's own arguments.** The client's declared
 * delta is not merely ignored — the API below has no parameter for it, so
 * there is nowhere to put it.
 *
 * The cost of each command is derived from the shipped data, not from a
 * hand-written table, so the two cannot drift apart.
 */

import {
  magicCatalogFrom,
  magicPrice,
  manaPack,
  type MagicPayment,
  type MagicSpellDefinition,
} from './magic.ts';

/** The player's resources, by resource key: `g`, `w`, `o`, `s`, `c`, `e`, `x`, `m`. */
export type Resources = Record<string, number>;

/** What a command spends and what it grants. */
export interface CommandCost {
  /** The resources the command spends. */
  cost: Resources;
  /** The resources the command grants. */
  gain: Resources;
}

/** An empty cost. */
export const NO_COST: CommandCost = { cost: {}, gain: {} };

/** The part of a content item the cost table needs. */
export interface CostItem {
  id: number;
  name: string;
  /** The build cost, by resource key. */
  costs: Resources;
  /** The cash price of one unit trained in this building. */
  costUnitCash: number;
  /** The cash price of a premium upgrade to this item. */
  premiumUpgradeCosts: Resources;
}

/** An offer pack. */
export interface CostOfferPack {
  id: number;
  name: string;
  cost_cash: number;
  gold: number;
  wood: number;
  oil: number;
  steel: number;
  mana: number;
  xp: number;
  items: number[];
}

/** A resource pack from the store. */
export interface CostResourcePack {
  /** The resource the pack gives, by key: `g`, `w`, `o` or `s`. */
  resource: string;
  /** How much of it the pack gives. */
  amount: number;
  /** What the pack costs, by resource key. */
  price: Resources;
}

/** The content the cost table reads. */
export interface CostContent {
  items: Map<number, CostItem>;
  offerPacks: Map<number, CostOfferPack>;
  /** The store's resource packs. */
  resourcePacks: CostResourcePack[];
  globals: Record<string, unknown>;
  expansionPrices: { coins: number; cash: number }[];
  /** The market's sell percentage. */
  marketSellPercentage: number;
  /** The number of trades the market allows per period. */
  marketMaxTrades: number;
  /** The market's per-trade increment. */
  marketIncrement: number;
  /** The gold price of 100 units, by resource. */
  marketBaseCosts: Record<string, number>;
  /** The magic and tech spells, by id. */
  magics: Map<number, MagicSpellDefinition>;
}

/** The client-side constants the costs depend on. */
export const CONFIG = {
  /** `Config.MULTIPLIER_PEASANTS` */
  multiplierPeasants: 0.2,
  /** `Config.DIVISOR_SELL` */
  divisorSell: 20,
  /** `Config.COST_BUY_ATTACK` */
  costBuyAttack: 30,
  /** `Config.COST_BUY_SPYINGS` */
  costBuySpyings: 15,
  /** `Config.BUY_GOLD_CASH` */
  buyGoldCash: 5,
  /** `Config.BUY_GOLD_GOLD` */
  buyGoldGold: 2500,
} as const;

/** The command names this module prices. */
export const PRICED_COMMANDS = [
  'buy',
  'place_stored_item',
  'sell_stored_item',
  'exchange_cash',
  'buy_offer_pack',
  'buy_premium_account',
  'buy_resources',
  'buy_powerups',
  'darts_shoot_balloon',
  'expand',
  'premium_upgrade',
  'trade_resource',
  'level_up',
  'attack_player',
  'spy_player',
  'buy_magic',
  'buy_mana_new',
  'use_magic',
] as const;

export type PricedCommand = (typeof PRICED_COMMANDS)[number];

function add(target: Resources, source: Resources): Resources {
  const out: Resources = { ...target };
  for (const [key, value] of Object.entries(source)) {
    out[key] = (out[key] ?? 0) + value;
  }
  return out;
}

/** The payment resource a native magic command names, if it is valid. */
function paymentOr(value: unknown): MagicPayment | null {
  return value === 'g' || value === 'c' ? value : null;
}

/**
 * Build the cost content from a built content bundle.
 *
 * Every caller that needs the cost table needs the same view of the
 * bundle, and building it by hand in five places is how they drift apart.
 * This is the one way to make it.
 */
export function costContentFrom(bundle: {
  items: {
    id: number;
    name: string;
    costs: Record<string, number>;
    cost_unit_cash: number;
    premium_upgrade_costs: Record<string, number>;
  }[];
  offerPacks: CostOfferPack[];
  globals: Record<string, unknown>;
  expansionPrices: { coins: number; cash: number }[];
  magics?: unknown[];
}): CostContent {
  const globals = bundle.globals;

  // The store's resource packs name the resource by its own key.
  const packs = (globals['RESOURCE_PACKS'] ?? []) as Record<string, unknown>[];
  const resourcePacks: CostResourcePack[] = [];
  for (const pack of packs) {
    const price = (pack['price'] ?? {}) as Record<string, number>;
    for (const [resource, amount] of Object.entries(pack)) {
      if (resource === 'price' || resource === 'img') continue;
      if (typeof amount !== 'number') continue;
      resourcePacks.push({ resource, amount, price: { ...price } });
    }
  }

  return {
    items: new Map(
      bundle.items.map((item) => [
        item.id,
        {
          id: item.id,
          name: item.name,
          costs: item.costs,
          costUnitCash: item.cost_unit_cash,
          premiumUpgradeCosts: item.premium_upgrade_costs ?? {},
        },
      ]),
    ),
    offerPacks: new Map(bundle.offerPacks.map((pack) => [pack.id, pack])),
    resourcePacks,
    globals,
    expansionPrices: bundle.expansionPrices,
    marketSellPercentage: globals['MARKET_SELL_PERCENTAGE'] as number,
    marketMaxTrades: globals['MARKET_MAX_NUM_TRADES'] as number,
    marketIncrement: globals['MARKET_INCREMENT'] as number,
    marketBaseCosts: globals['MARKET_BASE_COSTS'] as Record<string, number>,
    magics: magicCatalogFrom(Array.isArray(bundle.magics) ? bundle.magics : []),
  };
}

/**
 * The cost of a command, computed from the content and the arguments.
 *
 * Returns `null` for a command this module does not price — a command with
 * no resource cost, or one that is not implemented yet. The server must
 * treat that as "no cost", never as "accept the client's number".
 */
export function computeCommandCost(
  content: CostContent,
  command: string,
  args: readonly unknown[],
): CommandCost | null {
  switch (command) {
    case 'buy': {
      // args: isoID, item id, tx, ty, playerID, frame, auto-acquired
      const item = content.items.get(Number(args[1]));
      if (!item) return null;
      const cost: Resources = { ...item.costs };
      if (item.costUnitCash > 0) {
        cost['c'] = (cost['c'] ?? 0) + item.costUnitCash;
      }
      return { cost, gain: {} };
    }

    case 'place_stored_item': {
      // args: isoID, building id, tx, ty, playerID, ...
      const item = content.items.get(Number(args[1]));
      if (!item) return null;
      return { cost: { ...item.costs }, gain: {} };
    }

    case 'sell_stored_item': {
      // args: isoID, item id
      const item = content.items.get(Number(args[1]));
      if (!item) return null;
      // The market pays 75% of the build cost, and it is paid in GOLD.
      const gain: Resources = {};
      for (const [key, amount] of Object.entries(item.costs)) {
        if (key === 'c') continue; // cash is not sellable for cash
        const gold = Math.round(amount * content.marketSellPercentage);
        if (gold > 0) gain['g'] = (gain['g'] ?? 0) + gold;
      }
      return { cost: {}, gain };
    }

    case 'exchange_cash': {
      // 5 cash buys 2500 gold.
      return { cost: { c: CONFIG.buyGoldCash }, gain: { g: CONFIG.buyGoldGold } };
    }

    case 'buy_offer_pack': {
      // args: offer pack id, JSON array of item ids
      const pack = content.offerPacks.get(Number(args[0]));
      if (!pack) return null;
      const gain: Resources = {};
      if (pack.gold) gain['g'] = pack.gold;
      if (pack.wood) gain['w'] = pack.wood;
      if (pack.oil) gain['o'] = pack.oil;
      if (pack.steel) gain['s'] = pack.steel;
      if (pack.mana) gain['m'] = pack.mana;
      if (pack.xp) gain['x'] = pack.xp;
      return { cost: { c: pack.cost_cash }, gain };
    }

    case 'buy_premium_account': {
      // args: package index (0..5)
      const packages = content.globals['PREMIUM_ACCOUNTS'] as { price: number }[] | undefined;
      const pack = packages?.[Number(args[0])];
      if (!pack) return null;
      return { cost: { c: pack.price }, gain: {} };
    }

    case 'buy_resources': {
      // The native form carries the resource and the amount; the price
      // comes from the store's own pack table, never from the client.
      const resource = String(args[0] ?? '');
      const amount = Number(args[1]);
      const pack = content.resourcePacks.find(
        (candidate) => candidate.resource === resource && candidate.amount === amount,
      );
      if (!pack) return null;
      return { cost: { ...pack.price }, gain: { [resource]: amount } };
    }

    case 'premium_upgrade': {
      // args: the old iso id, the new iso id, the new building's item id,
      // and the click count (-1 when the building needs none).
      const item = content.items.get(Number(args[2]));
      if (!item) return null;
      const costs = item.premiumUpgradeCosts ?? {};
      if (Object.keys(costs).length === 0) return null;
      return { cost: { ...costs }, gain: {} };
    }

    case 'buy_powerups': {
      // args: power-up level index
      const levels = content.globals['SOUL_MIXER_POWERUPS_LEVELS'] as
        | { cash_cost: number }[]
        | undefined;
      const level = levels?.[Number(args[0])];
      if (!level) return null;
      return { cost: { c: level.cash_cost }, gain: {} };
    }

    case 'darts_shoot_balloon': {
      // The shot is free once a day; the client sends the delta, but the
      // server charges the cash itself when the shot was not free.
      const cost = Number(content.globals['DART_COST_CASH'] ?? 20);
      return { cost: { c: cost }, gain: {} };
    }

    case 'expand': {
      // args: tile id, price, type. The price is computed from the
      // expansion table, never taken from the argument.
      const owned = Number(args[0]);
      const price = content.expansionPrices[owned];
      if (!price) return null;
      const cost: Resources = {};
      if (price.coins) cost['g'] = price.coins;
      if (price.cash) cost['c'] = price.cash;
      return { cost, gain: {} };
    }

    case 'trade_resource': {
      // args: resource key, sell 1/0. The amount is NOT in the arguments
      // on this path, so the price is for the standard 100-unit trade.
      const resource = String(args[0] ?? '');
      const base = content.marketBaseCosts[resource];
      if (base === undefined) return null;
      return { cost: { g: base }, gain: {} };
    }

    case 'level_up': {
      // args: the new level. The cost is the unit's XP level-up price,
      // which depends on the unit's life.
      return null; // needs the unit; see computeLevelUpCost
    }

    case 'attack_player': {
      // Attacking costs 30 energy.
      return { cost: { e: CONFIG.costBuyAttack }, gain: {} };
    }

    case 'spy_player': {
      // Spying costs 15 energy.
      return { cost: { e: CONFIG.costBuySpyings }, gain: {} };
    }

    case 'buy_magic': {
      // args: spell id, payment resource. The price is the spell's own, and
      // the purchase's mana grant is applied by the applier only after the
      // spell is actually learned.
      const spell = content.magics.get(Number(args[0]));
      if (!spell) return null;
      const payment = paymentOr(args[1]);
      if (!payment) return null;
      const price = magicPrice(spell, payment);
      if (!price) return null;
      return { cost: { [price.resource]: price.amount }, gain: {} };
    }

    case 'buy_mana_new': {
      // args: mana amount, payment resource. There is one pack; an amount
      // that does not match it is not a purchase the server can price.
      const pack = manaPack(content.globals);
      if (Number(args[0]) !== pack.amount) return null;
      const payment = paymentOr(args[1]);
      if (!payment || pack.price[payment] <= 0) return null;
      return { cost: { [payment]: pack.price[payment] }, gain: {} };
    }

    case 'use_magic': {
      // args: spell id. The mana cost is the spell's own; whether the spell
      // is learned is the applier's check, after the wallet is settled.
      const spell = content.magics.get(Number(args[0]));
      if (!spell) return null;
      return { cost: { m: spell.mana }, gain: {} };
    }

    default:
      return null;
  }
}

/**
 * The cost of levelling a unit up.
 *
 * `ceil(life / divisor)`, with the divisor from the XP level table.
 */
export function computeLevelUpCost(
  xpTable: readonly { cashDivisor: number }[],
  life: number,
  level: number,
): number {
  const row = xpTable[level];
  if (!row || row.cashDivisor <= 0) return 0;
  return Math.ceil(life / row.cashDivisor);
}

/** The result of applying a cost to a player's wallet. */
export interface CostResult {
  /** Whether the player could afford it and the command was applied. */
  ok: boolean;
  /** Why it was refused, if it was. */
  reason?: 'insufficient-resources' | 'unknown-cost';
  /** The resources after the command. */
  resources: Resources;
}

/**
 * Apply a computed cost to a player's wallet.
 *
 * The player must be able to afford the whole cost; a partial purchase is
 * never applied. The client's own claimed delta is not involved.
 */
export function applyCommandCost(
  resources: Resources,
  cost: CommandCost | null,
): CostResult {
  if (cost === null) {
    // A command with no computed cost costs nothing. It must NOT fall back
    // to accepting the client's number.
    return { ok: true, resources: { ...resources } };
  }

  for (const [key, amount] of Object.entries(cost.cost)) {
    if ((resources[key] ?? 0) < amount) {
      return {
        ok: false,
        reason: 'insufficient-resources',
        resources: { ...resources },
      };
    }
  }

  const next: Resources = { ...resources };
  for (const [key, amount] of Object.entries(cost.cost)) {
    next[key] = (next[key] ?? 0) - amount;
  }
  for (const [key, amount] of Object.entries(cost.gain)) {
    next[key] = (next[key] ?? 0) + amount;
  }
  return { ok: true, resources: next };
}

/**
 * The wallet after a command, ignoring anything the client claimed.
 *
 * This is the function the server's command handler calls. It is
 * deliberately small: the cost is computed, checked and applied, and the
 * client's `res` vector is never read.
 */
export function settleCommand(
  content: CostContent,
  resources: Resources,
  command: string,
  args: readonly unknown[],
): CostResult {
  const cost = computeCommandCost(content, command, args);
  return applyCommandCost(resources, cost);
}
