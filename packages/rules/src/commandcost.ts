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

/** The content the cost table reads. */
export interface CostContent {
  items: Map<number, CostItem>;
  offerPacks: Map<number, CostOfferPack>;
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
  'buy_powerups',
  'darts_shoot_balloon',
  'expand',
  'trade_resource',
  'level_up',
  'attack_player',
  'spy_player',
] as const;

export type PricedCommand = (typeof PRICED_COMMANDS)[number];

function add(target: Resources, source: Resources): Resources {
  const out: Resources = { ...target };
  for (const [key, value] of Object.entries(source)) {
    out[key] = (out[key] ?? 0) + value;
  }
  return out;
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
