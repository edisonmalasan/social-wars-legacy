/**
 * The marketplace — the auction house.
 *
 * The upstream server ships this subsystem **complete but disabled**:
 * `upstream/socialwarriors/auctions.py` implements the object model,
 * `upstream/socialwarriors/config/auctionhouse.json` holds the seed data,
 * and `server.py:197-288` has the three routes — commented out. The client
 * is the specification: `data/MarketplaceInfo.as`,
 * `data/MarketplaceUnitInfo.as` and `popups/marketplace/*`.
 *
 * ## The three endpoints
 *
 * | Endpoint | Request | Response |
 * |---|---|---|
 * | `bets/get_bets_list.php` | `user_id`, `level` | `{"bets": [...]}` |
 * | `bets/get_bet_detail.php` | `uuid`, `checkFinish` | the listing, flat |
 * | `bets/set_bet.php` | `user_id`, `uuid`, `round`, `bet`, `client_id`, `session_id` | `{"betResult": "OK"}` |
 *
 * (`re/docs/15-social-layer-contracts.md` §1.3.)
 *
 * ## What a bid is
 *
 * The client's own help popup (`popups/marketplace/PopupMarketplaceHelp.as:20`)
 * is the only description of the game that survives:
 *
 * > - If more than one player has bid at the end of the 1st round, a 2nd
 * >   round of 30 secs. will start.
 * > - Bid again to get the unit!
 * > - When there's a round where only one player has bid, the bid will end
 * >   and that player will get the unit!
 *
 * So a bid is a **qualification for the next round**, not a purchase: the
 * round advances while more than one player bids, and the round that only
 * one player bids decides the listing. The winner pays the price — the
 * client deducts `currentPrice` gold when it wins
 * (`data/MarketplaceUnitInfo.as:201-202`) — and everybody pays the small
 * cash fee (`betPrice`) for each bid they place
 * (`popups/marketplace/PopupMarketplaceUnit.as:330-331`).
 *
 * ## The rules of a bid
 *
 * A bid is accepted when all of these hold:
 *
 * 1. the round is **open** — a bid that arrives after the window shut is
 *    refused with the client's own `100`, "This bet is outdated";
 * 2. the round the player bids on is the **running** one — the client
 *    sends the round it knows about
 *    (`popups/marketplace/PopupMarketplaceUnit.as:338`) and the upstream
 *    ignores it (`auctions.py:180`);
 * 3. the amount **meets the current price** — the price starts at the
 *    configured one and moves up by one increment with every bid
 *    (`auctions.py:199`), so two players cannot bid the same amount: the
 *    second one is told that somebody made a higher bid in the meantime,
 *    the client's own `200`;
 * 4. the player does not hold more than three of the **leading** bids
 *    (`popups/marketplace/PopupMarketplaceUnit.as:313`);
 * 5. the player can pay the **price and the fee**
 *    (`popups/marketplace/PopupMarketplaceUnit.as:317-324`).
 *
 * ## The rules the upstream never wrote
 *
 * The upstream marks the round logic as a TODO (`auctions.py:124`) and
 * recycles a listing back to round 1 when it expires. The client expects
 * the rounds, so the client wins: an expired round with more than one
 * bidder starts the next round instead of recycling the listing.
 *
 * ## Purity
 *
 * The service is pure: the state is passed in and the new state is
 * returned, and **the clock is a parameter**. There is no `Date.now()`, no
 * randomness and no I/O, so a test is deterministic.
 */

/**
 * The error vocabulary.
 *
 * `100` and `200` are the **client's own** codes — the client switches on
 * them and shows a different message for each
 * (`popups/marketplace/PopupMarketplaceUnit.as:275-288`). They must be
 * exactly these numbers.
 *
 * The `9xx` codes are this server's own. The client has no message for
 * them and shows its generic one ("There were some error..."), so their
 * numbers only have to be different from `100` and `200`.
 */
export const MARKETPLACE_ERRORS = {
  /**
   * "This bet is outdated." The client's own code
   * (`popups/marketplace/PopupMarketplaceUnit.as:277-280`): the client
   * destroys the listing and closes the popup.
   */
  ERR_BET_OUTDATED: 100,
  /**
   * "Someone made highger bid in a meantime. Please try again." The
   * client's own code (`popups/marketplace/PopupMarketplaceUnit.as:282-284`):
   * the client refreshes the listing and lets the player bid again.
   */
  ERR_BET_TOO_LOW: 200,
  /** The listing does not exist. */
  ERR_BET_NOT_FOUND: 900,
  /** The player cannot pay the price or the fee. */
  ERR_BET_NOT_AFFORDABLE: 901,
  /**
   * The player holds too many of the leading bids and has to wait for
   * somebody else to bid.
   */
  ERR_BET_LIMIT_REACHED: 902,
  /** The player is below the level the auction house opens at. */
  ERR_MARKETPLACE_LOCKED: 903,
} as const;

export type MarketplaceErrorCode = (typeof MARKETPLACE_ERRORS)[keyof typeof MARKETPLACE_ERRORS];

/** The `betResult` the client reads as a good bid. */
export const BET_RESULT_OK = 'OK';

/**
 * The level the auction house opens at.
 *
 * The client's own (`data/MarketplaceInfo.as:24`), enforced client-side
 * when the player opens the marketplace (`GUI/GuiManager.as:647-650`).
 */
export const MIN_MARKETPLACE_LEVEL = 8;

/** A bidder, as the client reads it (`popups/marketplace/BidderRenderer.as:36-41`). */
export interface MarketplaceBidder {
  /** The bidder's id — the session id the client sends as `user_id`. */
  user_id: string;
  /** The bidder's name (`fb_name`). */
  fb_name: string;
  /** The gold the bidder committed. */
  bet: number;
  /** The bidder's picture (`fb_picture`). */
  fb_picture: string;
}

/**
 * One listing, as the upstream's `auctions/auctions.json` holds it.
 *
 * The field names are the upstream's, so the state can be persisted as it
 * is. `betUsers` and `betUsersPrev` are the two bidder lists; the upstream
 * also keeps `bidders` and `prevRoundBidders`, which are redundant copies
 * of the same two lists (`auctions.py:197-198`) that the client never
 * reads, so they are not ported.
 */
export interface MarketplaceListingState {
  /** The listing's id. */
  uuid: string;
  /** The item id being auctioned. */
  idUnit: number;
  /** The unit's tier — the stars the client draws (`popups/marketplace/PopupMarketplaceUnit.as:57-67`). */
  level: number;
  /** When the current round opened, in seconds. */
  beginDate: number;
  /** When the current round closes, in seconds. */
  endDate: number;
  /** The price the listing opened at. */
  beginPrice: number;
  /** The price the next bid has to meet or beat. */
  currentPrice: number;
  /** The minimum increment between two bids. */
  priceIncrement: number;
  /** The cash fee for placing a bid. */
  betPrice: number;
  /** The round, 1-based. */
  round: number;
  /** The bidders of the current round, in the order they bid. */
  betUsers: MarketplaceBidder[];
  /** The bidders of the previous round. */
  betUsersPrev: MarketplaceBidder[];
  /** The rounds each user took part in. */
  userRounds: Record<string, number[]>;
  /** The winner, once the listing has been decided. */
  winnerId: string | null;
  /** The price the winner paid. */
  winnerPrice: number | null;
}

/** A listing, as the client sees it. */
export interface MarketplaceListing {
  uuid: string;
  idUnit: number;
  level: number;
  beginDate: number;
  endDate: number;
  beginPrice: number;
  currentPrice: number;
  priceIncrement: number;
  betPrice: number;
  round: number;
  /**
   * Whether the player is taking part in the listing.
   *
   * The client uses it to decide whether it has to keep polling for the
   * outcome (`data/MarketplaceUnitInfo.as:103-112`), and it sorts the
   * listings the player takes part in to the top
   * (`data/MarketplaceInfo.as:118`). The upstream always sends `0`
   * (`auctions.py:162`), which would leave the client unable to learn
   * that it won, so the client wins here.
   */
  isPrivate: boolean;
  /** Whether the player leads the current round. */
  isWinning: boolean;
  /** Whether the player won the listing. */
  won: boolean;
  /** Whether the listing has been decided. */
  finished: boolean;
  /** The bidders of the current round. */
  betUsers: MarketplaceBidder[];
  /** The bidders of the previous round. */
  betUsersPrev: MarketplaceBidder[];
}

/**
 * The detail payload.
 *
 * It is the listing **flat** — the client reads `param1.round` and
 * `param1.endDate` at the top level (`data/MarketplaceUnitInfo.as:170`) —
 * plus the state again under `betDetail`, which is what the client copies
 * into its own listing (`data/MarketplaceUnitInfo.as:179`). The upstream
 * sends `betDetail` as an empty array (`auctions.py:166`), which leaves
 * the client with nothing to update, so the client wins here.
 */
export interface MarketplaceBetDetail extends MarketplaceListing {
  /** The listing's state, for the client to copy. */
  betDetail: MarketplaceListing;
  /** The winner, once the round has been decided. */
  betWinner?: string;
}

/** What a decided listing gives its winner. */
export interface MarketplaceSettlement {
  /** The listing's id. */
  uuid: string;
  /** The winner's user id. */
  userId: string;
  /** The item id the winner receives. */
  itemId: number;
  /** The unit's tier. */
  level: number;
  /** The gold the winner pays. */
  goldCost: number;
}

/** The seed configuration, as `config/auctionhouse.json` has it. */
export interface MarketplaceConfig {
  /** The listing's id. */
  uuid: string;
  /** The item id being auctioned. */
  unit: number;
  /** The unit's tier. */
  level: number;
  /** How many minutes the first round lasts. */
  interval: number;
  /** The price the listing opens at. */
  price: number;
  /** The minimum increment between two bids. */
  priceIncrement: number;
  /** The cash fee for placing a bid. */
  betPrice: number;
}

/** The rules the service applies. */
export interface MarketplaceRules {
  /**
   * The level a player needs before the auction house opens.
   *
   * The client's own (`data/MarketplaceInfo.as:24`), enforced client-side
   * (`GUI/GuiManager.as:647-650`). The server repeats it, because the
   * server is the authority.
   */
  minLevel: number;
  /**
   * How many of the leading bids one player may hold before they have to
   * wait for somebody else to bid.
   *
   * The client's own (`popups/marketplace/PopupMarketplaceUnit.as:313`),
   * counted over the bids sorted by amount
   * (`data/MarketplaceUnitInfo.as:216-228`).
   */
  maxLeadingSelfBids: number;
  /**
   * How long a round after the first lasts, in seconds.
   *
   * The client's own ("a 2nd round of 30 secs. will start",
   * `popups/marketplace/PopupMarketplaceHelp.as:20`).
   */
  extraRoundSeconds: number;
  /**
   * How long after a round closes before it is decided, in seconds.
   *
   * The upstream's grace period (`auctions.py:120`): a listing that had
   * bettors is not recycled within 60 seconds of its round closing. Here
   * the same grace period delays the **decision**, so that the client can
   * poll for the outcome — it keeps asking while the round and its end
   * date are the ones it already knows
   * (`data/MarketplaceUnitInfo.as:166-176`).
   */
  settleDelaySeconds: number;
}

export const DEFAULT_MARKETPLACE_RULES: MarketplaceRules = {
  minLevel: MIN_MARKETPLACE_LEVEL,
  maxLeadingSelfBids: 3,
  extraRoundSeconds: 30,
  settleDelaySeconds: 60,
};

/** The player, for the parts of a bid the rules need. */
export interface MarketplacePlayer {
  /** The player's display name (`fb_name`). */
  name?: string;
  /** The player's picture (`fb_picture`). */
  picture?: string;
  /** The player's gold. Unknown means the check is skipped. */
  gold?: number;
  /** The player's cash. Unknown means the check is skipped. */
  cash?: number;
}

/** The request of `bets/get_bets_list.php`. */
export interface MarketplaceListParams {
  /** The player's id. */
  userId: string;
  /**
   * The player's level.
   *
   * The client sends `max(playerLevel, 8)` (`core/Base.as:7650`).
   *
   * UNKNOWN: what the server does with it beyond the level floor. The
   * upstream takes it and ignores it (`auctions.py:203`), and a listing's
   * own `level` is the **unit's** tier, not a requirement on the player
   * (`popups/marketplace/PopupMarketplaceUnit.as:57-67`), so no filter is
   * ported on it.
   */
  level: number;
}

/** The request of `bets/get_bet_detail.php`. */
export interface MarketplaceDetailParams {
  /**
   * The player's id.
   *
   * The request itself carries no user id — the client sends only `uuid`
   * and `checkFinish` (`popups/marketplace/PopupMarketplaceUnit.as:463`) —
   * so the server takes it from the session, as the upstream does
   * (`server.py:244`).
   */
  userId: string;
  /** The listing's id. */
  uuid: string;
  /**
   * Whether the caller wants the round's outcome.
   *
   * The client sets it when it polls for the result of a round that just
   * closed (`data/MarketplaceUnitInfo.as:137-140`). The upstream only
   * reports the winner when it is set (`auctions.py:174-176`).
   */
  checkFinish: boolean;
}

/** The request of `bets/set_bet.php`. */
export interface MarketplaceBetParams {
  /** The player's id. */
  userId: string;
  /** The listing's id. */
  uuid: string;
  /**
   * The round the player is bidding on.
   *
   * The client sends the round it knows about
   * (`popups/marketplace/PopupMarketplaceUnit.as:338`). The upstream
   * ignores it (`auctions.py:180`); the client needs it to tell a stale
   * bid from a fresh one.
   */
  round: number;
  /**
   * The amount the player bids, in gold.
   *
   * The client sends the price it sees (`popups/marketplace/PopupMarketplaceUnit.as:339`).
   */
  bet: number;
  /** The player, for the name, the picture and the wallet. */
  player?: MarketplacePlayer;
  /**
   * The client's id (`client_id`). The upstream never reads it, and the
   * rules do not need it.
   */
  clientId?: string;
  /**
   * The session id (`session_id`) — the client's `userKey`, or the literal
   * `"ludorules"` (`popups/marketplace/PopupMarketplaceUnit.as:341`). The
   * upstream never reads it either.
   */
  sessionId?: string;
}

/** The answer of every operation. */
export interface MarketplaceResult {
  /** Whether the operation succeeded. */
  success: boolean;
  /** The error code, when it failed. */
  error?: MarketplaceErrorCode;
  /** The wire `betResult`: `"OK"` or the error code. */
  betResult?: string | MarketplaceErrorCode;
  /** The bets, for the list operation. */
  bets?: MarketplaceListing[];
  /** The listing's detail, for the detail operation. */
  detail?: MarketplaceBetDetail;
  /** The cash the bid cost. */
  cashCost?: number;
  /** The listings that were decided while the call ran. */
  settlements: MarketplaceSettlement[];
}

/**
 * The client's sort order.
 *
 * `data/MarketplaceInfo.as:118` sorts the bids by `["isPrivate","endDate"]`
 * with `[Array.NUMERIC | Array.DESCENDING, Array.NUMERIC]`: the listings
 * the player takes part in come first, and the ones that close soonest
 * come first inside each group. The same order is the marketplace popup's
 * own default (`popups/marketplace/PopupMarketplace.as:216-220`).
 *
 * The sort is stable, so listings that tie keep their configuration order.
 */
export function sortMarketplaceListings(
  listings: readonly MarketplaceListing[],
): MarketplaceListing[] {
  return [...listings].sort((a, b) => {
    const priv = (b.isPrivate ? 1 : 0) - (a.isPrivate ? 1 : 0);
    if (priv !== 0) return priv;
    return a.endDate - b.endDate;
  });
}

/**
 * The marketplace service.
 *
 * It is pure: the state is passed in and the new state is returned, with
 * no clock and no randomness of its own. The clock is a parameter, so a
 * test is deterministic.
 */
export class MarketplaceService {
  private readonly rules: MarketplaceRules;
  private readonly configs = new Map<string, MarketplaceConfig>();
  private readonly listings = new Map<string, MarketplaceListingState>();

  constructor(
    configs: readonly MarketplaceConfig[] = [],
    state: Readonly<Record<string, MarketplaceListingState>> = {},
    rules: MarketplaceRules = DEFAULT_MARKETPLACE_RULES,
  ) {
    this.rules = rules;
    for (const config of configs) {
      this.configs.set(config.uuid, config);
    }
    for (const [uuid, listing] of Object.entries(state)) {
      this.listings.set(uuid, {
        ...listing,
        betUsers: listing.betUsers.map((bidder) => ({ ...bidder })),
        betUsersPrev: listing.betUsersPrev.map((bidder) => ({ ...bidder })),
        userRounds: { ...listing.userRounds },
      });
    }
  }

  /** The state, for the persistence layer. */
  state(): MarketplaceListingState[] {
    return [...this.listings.values()].map((listing) => ({
      ...listing,
      betUsers: listing.betUsers.map((bidder) => ({ ...bidder })),
      betUsersPrev: listing.betUsersPrev.map((bidder) => ({ ...bidder })),
      userRounds: { ...listing.userRounds },
    }));
  }

  /** The failure helper. */
  private fail(code: MarketplaceErrorCode, settlements: MarketplaceSettlement[]): MarketplaceResult {
    return { success: false, error: code, betResult: code, settlements };
  }

  /**
   * Create the listings the configuration asks for and the state does not
   * have yet.
   *
   * The upstream creates them at start-up (`auctions.py:36-43`); here they
   * are created the first time the clock reaches them, so that the service
   * never needs a clock of its own.
   */
  private ensureListings(now: number): void {
    for (const config of this.configs.values()) {
      if (this.listings.has(config.uuid)) continue;
      this.listings.set(config.uuid, {
        uuid: config.uuid,
        idUnit: config.unit,
        level: config.level,
        beginDate: now,
        endDate: now + config.interval * 60,
        beginPrice: config.price,
        currentPrice: config.price,
        priceIncrement: config.priceIncrement,
        betPrice: config.betPrice,
        round: 1,
        betUsers: [],
        betUsersPrev: [],
        userRounds: {},
        winnerId: null,
        winnerPrice: null,
      });
    }
  }

  /**
   * Move the listings on to where the clock says they are.
   *
   * The upstream does this on every read (`auctions.py:204`, `auctions.py:222`).
   */
  private advance(now: number): MarketplaceSettlement[] {
    const settlements: MarketplaceSettlement[] = [];
    for (const listing of this.listings.values()) {
      if (listing.winnerId !== null) continue;
      if (now < listing.endDate) continue;
      const bidders = distinctBidders(listing.betUsers);
      if (bidders.length === 0) {
        // Nobody bid: the listing cycles back to a fresh first round, the
        // way the upstream recycles it (`auctions.py:119-143`).
        this.recycle(listing, now);
        continue;
      }
      // The round is decided 60 seconds after it closed: the upstream's
      // grace period (`auctions.py:120`). The client polls for the outcome
      // while the round and its end date are the ones it already knows
      // (`data/MarketplaceUnitInfo.as:166-176`).
      if (now < listing.endDate + this.rules.settleDelaySeconds) continue;
      if (bidders.length === 1) {
        settlements.push(this.resolve(listing, bidders[0]!.user_id));
      } else {
        this.nextRound(listing, now);
      }
    }
    return settlements;
  }

  /**
   * Cycle a listing back to a fresh first round.
   *
   * The upstream keeps the phase of the old window, so the listing comes
   * back at the same point of its interval (`auctions.py:127-133`).
   */
  private recycle(listing: MarketplaceListingState, now: number): void {
    const config = this.configs.get(listing.uuid);
    const seconds = (config?.interval ?? 60) * 60;
    const difference = now - listing.endDate;
    const remaining = ((difference % seconds) + seconds) % seconds;
    listing.beginDate = now - remaining;
    listing.endDate = listing.beginDate + seconds;
    listing.beginPrice = config?.price ?? listing.beginPrice;
    listing.currentPrice = listing.beginPrice;
    listing.priceIncrement = config?.priceIncrement ?? listing.priceIncrement;
    listing.betPrice = config?.betPrice ?? listing.betPrice;
    listing.level = config?.level ?? listing.level;
    listing.round = 1;
    listing.betUsers = [];
    listing.betUsersPrev = [];
    listing.userRounds = {};
  }

  /**
   * Start the next round.
   *
   * The upstream never does this — it marks the round logic as a TODO
   * (`auctions.py:124`) and recycles the listing instead. The client
   * expects the rounds (`data/MarketplaceUnitInfo.as:184-189`), so the
   * client wins.
   */
  private nextRound(listing: MarketplaceListingState, now: number): void {
    listing.round += 1;
    listing.betUsersPrev = listing.betUsers;
    listing.betUsers = [];
    listing.beginDate = now;
    listing.endDate = now + this.rules.extraRoundSeconds;
  }

  /**
   * Decide a listing.
   *
   * The winner pays the listing's current price — the client deducts
   * exactly that when it wins (`data/MarketplaceUnitInfo.as:201-202`).
   */
  private resolve(
    listing: MarketplaceListingState,
    winnerId: string,
  ): MarketplaceSettlement {
    listing.winnerId = winnerId;
    listing.winnerPrice = listing.currentPrice;
    return {
      uuid: listing.uuid,
      userId: winnerId,
      itemId: listing.idUnit,
      level: listing.level,
      goldCost: listing.currentPrice,
    };
  }

  /** The leader of the current round — the highest bid. */
  private leader(listing: MarketplaceListingState): MarketplaceBidder | null {
    let best: MarketplaceBidder | null = null;
    for (const bidder of listing.betUsers) {
      if (!best || bidder.bet > best.bet) best = bidder;
    }
    return best;
  }

  /**
   * How many of the leading bids belong to one player.
   *
   * The client counts them over the bids sorted by amount, from the top
   * (`data/MarketplaceUnitInfo.as:216-228`).
   */
  private leadingSelfBids(listing: MarketplaceListingState, userId: string): number {
    const sorted = [...listing.betUsers].sort((a, b) => b.bet - a.bet);
    let count = 0;
    for (const bidder of sorted) {
      if (bidder.user_id !== userId) break;
      count += 1;
    }
    return count;
  }

  /** The listing, as the client sees it. */
  private view(listing: MarketplaceListingState, userId: string): MarketplaceListing {
    // The player is taking part while they are in the current round or in
    // the one before it — a player who bid in the last round is still in
    // the running until the round that follows is decided.
    const isPrivate =
      listing.betUsers.some((bidder) => bidder.user_id === userId) ||
      listing.betUsersPrev.some((bidder) => bidder.user_id === userId);
    return {
      uuid: listing.uuid,
      idUnit: listing.idUnit,
      level: listing.level,
      beginDate: listing.beginDate,
      endDate: listing.endDate,
      beginPrice: listing.beginPrice,
      currentPrice: listing.currentPrice,
      priceIncrement: listing.priceIncrement,
      betPrice: listing.betPrice,
      round: listing.round,
      isPrivate,
      // The client's own rule: the leader is the top of the bids sorted by
      // amount (`popups/marketplace/PopupMarketplaceUnit.as:245-248`). The
      // upstream calls the last bidder the winner instead
      // (`auctions.py:168-173`); the client wins.
      isWinning: this.leader(listing)?.user_id === userId,
      // The upstream always sends `1` (`auctions.py:164`), which would
      // make the client drop every live listing
      // (`data/MarketplaceInfo.as:85-91`); the client wins.
      won: listing.winnerId === userId,
      // The upstream calls a listing finished when its window closed
      // (`auctions.py:165`). The client uses the flag to stop polling for
      // the outcome (`data/MarketplaceUnitInfo.as:95-102`), so the flag
      // has to mean "the outcome is known".
      finished: listing.winnerId !== null,
      betUsers: listing.betUsers.map((bidder) => ({ ...bidder })),
      betUsersPrev: listing.betUsersPrev.map((bidder) => ({ ...bidder })),
    };
  }

  /**
   * `bets/get_bets_list.php` — the listings the player can see.
   */
  getBetsList(params: MarketplaceListParams, now: number): MarketplaceResult {
    if (params.level < this.rules.minLevel) {
      // The auction house opens at level 8 (`data/MarketplaceInfo.as:24`).
      // The client's own menu blocks the player before this can happen
      // (`GUI/GuiManager.as:647-650`), so this is the server's answer to a
      // request the client should not make.
      return this.fail(MARKETPLACE_ERRORS.ERR_MARKETPLACE_LOCKED, []);
    }
    this.ensureListings(now);
    const settlements = this.advance(now);
    const bets = sortMarketplaceListings(
      [...this.listings.values()].map((listing) => this.view(listing, params.userId)),
    );
    return { success: true, bets, settlements };
  }

  /**
   * `bets/get_bet_detail.php` — one listing.
   */
  getBetDetail(params: MarketplaceDetailParams, now: number): MarketplaceResult {
    this.ensureListings(now);
    const settlements = this.advance(now);
    const listing = this.listings.get(params.uuid);
    if (!listing) {
      // The upstream answers `None` (`auctions.py:230`), which the client
      // reads as a failure (`popups/marketplace/PopupMarketplaceUnit.as:236-240`).
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_NOT_FOUND, settlements);
    }
    const view = this.view(listing, params.userId);
    const detail: MarketplaceBetDetail = {
      ...view,
      betDetail: view,
      betUsers: listing.betUsers.map((bidder) => ({ ...bidder })),
      betUsersPrev: listing.betUsersPrev.map((bidder) => ({ ...bidder })),
      betWinner: params.checkFinish ? (listing.winnerId ?? undefined) : undefined,
    };
    return { success: true, detail, settlements };
  }

  /**
   * `bets/set_bet.php` — a player bids on a listing.
   */
  setBet(params: MarketplaceBetParams, now: number): MarketplaceResult {
    this.ensureListings(now);
    const listing = this.listings.get(params.uuid);
    // Whether the round was open when the request arrived. It is judged
    // before the listings are moved on, so that a bid on a round that has
    // just closed is told so, instead of landing in the round that follows
    // it.
    const roundClosed = listing !== undefined && now >= listing.endDate;
    const settlements = this.advance(now);
    if (!listing) {
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_NOT_FOUND, settlements);
    }
    // The round has to be open. A bid that arrives after the window shut
    // is a bid on a round that is over ("This bet is outdated",
    // `popups/marketplace/PopupMarketplaceUnit.as:277-280`).
    if (roundClosed) {
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_OUTDATED, settlements);
    }
    // The player has to be bidding on the round that is running. The
    // upstream ignores the round (`auctions.py:180`), but the client
    // needs it to tell a stale bid from a fresh one.
    if (params.round !== listing.round) {
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_OUTDATED, settlements);
    }
    // The bid has to meet the price. This is also what makes two players
    // bidding the same amount impossible: the first bid lifts the price
    // above the amount, so the second one is told that somebody made a
    // higher bid in the meantime
    // (`popups/marketplace/PopupMarketplaceUnit.as:282-284`).
    if (params.bet < listing.currentPrice) {
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_TOO_LOW, settlements);
    }
    // The player may not hold the lead over and over: the client refuses
    // the third leading bid (`popups/marketplace/PopupMarketplaceUnit.as:313`).
    if (this.leadingSelfBids(listing, params.userId) >= this.rules.maxLeadingSelfBids) {
      return this.fail(MARKETPLACE_ERRORS.ERR_BET_LIMIT_REACHED, settlements);
    }
    // The player has to be able to pay the price and the fee. The client
    // checks both before it bids
    // (`popups/marketplace/PopupMarketplaceUnit.as:317-324`).
    const player = params.player;
    if (player) {
      if (player.gold !== undefined && player.gold < params.bet) {
        return this.fail(MARKETPLACE_ERRORS.ERR_BET_NOT_AFFORDABLE, settlements);
      }
      if (player.cash !== undefined && player.cash < listing.betPrice) {
        return this.fail(MARKETPLACE_ERRORS.ERR_BET_NOT_AFFORDABLE, settlements);
      }
    }
    // The bid is accepted. The price moves up by one increment, so the
    // next bid has to be higher (`auctions.py:199`).
    listing.betUsers.push({
      user_id: params.userId,
      fb_name: player?.name ?? '',
      bet: params.bet,
      fb_picture: player?.picture ?? '',
    });
    listing.currentPrice = params.bet + listing.priceIncrement;
    const rounds = listing.userRounds[params.userId] ?? [];
    if (!rounds.includes(listing.round)) rounds.push(listing.round);
    listing.userRounds[params.userId] = rounds;
    return {
      success: true,
      betResult: BET_RESULT_OK,
      cashCost: listing.betPrice,
      settlements,
    };
  }
}

/** The distinct bidders of a list, in the order they first bid. */
function distinctBidders(bidders: readonly MarketplaceBidder[]): MarketplaceBidder[] {
  const seen = new Set<string>();
  const distinct: MarketplaceBidder[] = [];
  for (const bidder of bidders) {
    if (seen.has(bidder.user_id)) continue;
    seen.add(bidder.user_id);
    distinct.push(bidder);
  }
  return distinct;
}
