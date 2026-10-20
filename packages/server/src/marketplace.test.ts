import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  BET_RESULT_OK,
  MARKETPLACE_ERRORS,
  MarketplaceService,
  sortMarketplaceListings,
  type MarketplaceConfig,
  type MarketplaceListing,
} from './marketplace.ts';

/**
 * The seed data, read from the vendored upstream
 * (`upstream/socialwarriors/config/auctionhouse.json`). The upstream is a
 * test fixture, so the real file is the fixture.
 */
const SEED = JSON.parse(
  readFileSync(
    new URL('../../../upstream/socialwarriors/config/auctionhouse.json', import.meta.url),
    'utf8',
  ),
) as { auctions: MarketplaceConfig[] };

const CONFIGS: MarketplaceConfig[] = SEED.auctions;

/** A fixed clock. Nothing in the service reads a clock of its own. */
const T0 = 1_700_000_000;

/** Listing "1" runs for 120 minutes, listing "2" for 60, listing "3" for 120. */
const END_1 = T0 + 120 * 60;
const END_2 = T0 + 60 * 60;
const END_3 = T0 + 120 * 60;

function service(): MarketplaceService {
  const market = new MarketplaceService(CONFIGS);
  // The listings are created the first time the clock reaches them, so the
  // service is primed at T0 — the moment the auction house opens.
  market.getBetsList({ userId: 'alice', level: 8 }, T0);
  return market;
}

const alice = { name: 'Alice', picture: 'alice.png', gold: 1_000_000, cash: 1_000 };
const bob = { name: 'Bob', picture: 'bob.png', gold: 1_000_000, cash: 1_000 };

describe('the seed configuration', () => {
  it('is the upstream own auction house config', () => {
    assert.equal(CONFIGS.length, 3);
    assert.deepEqual(CONFIGS[0], {
      uuid: '1',
      unit: 1167,
      level: 1,
      interval: 120,
      price: 5000,
      priceIncrement: 1000,
      betPrice: 2,
    });
    assert.equal(CONFIGS[1]?.uuid, '2');
    assert.equal(CONFIGS[1]?.price, 1000);
    assert.equal(CONFIGS[1]?.priceIncrement, 200);
    assert.equal(CONFIGS[2]?.uuid, '3');
    assert.equal(CONFIGS[2]?.unit, 1226);
    assert.equal(CONFIGS[2]?.level, 2);
    assert.equal(CONFIGS[2]?.price, 8000);
    assert.equal(CONFIGS[2]?.priceIncrement, 1500);
  });

  it('opens the listings with the configured prices and fees', () => {
    const market = service();
    const list = market.getBetsList({ userId: 'alice', level: 8 }, T0);
    assert.equal(list.success, true);
    assert.equal(list.bets?.length, 3);
    const one = list.bets?.find((bet) => bet.uuid === '1');
    assert.equal(one?.idUnit, 1167);
    assert.equal(one?.level, 1);
    assert.equal(one?.beginPrice, 5000);
    assert.equal(one?.currentPrice, 5000);
    assert.equal(one?.priceIncrement, 1000);
    assert.equal(one?.betPrice, 2);
    assert.equal(one?.round, 1);
    assert.equal(one?.beginDate, T0);
    assert.equal(one?.endDate, END_1);
    const three = list.bets?.find((bet) => bet.uuid === '3');
    assert.equal(three?.level, 2);
    assert.equal(three?.endDate, END_3);
  });
});

describe('the error vocabulary', () => {
  it('keeps the client own numbers exactly', () => {
    // The client switches on these two numbers and shows a different
    // message for each (`popups/marketplace/PopupMarketplaceUnit.as:275-288`).
    assert.equal(MARKETPLACE_ERRORS.ERR_BET_OUTDATED, 100);
    assert.equal(MARKETPLACE_ERRORS.ERR_BET_TOO_LOW, 200);
  });

  it('keeps the server own numbers away from the client own ones', () => {
    const codes = Object.values(MARKETPLACE_ERRORS);
    assert.equal(new Set(codes).size, codes.length);
    assert.ok(!codes.includes(100) || codes.filter((code) => code === 100).length === 1);
    for (const code of codes) {
      assert.ok(code >= 900 || code === 100 || code === 200, `unexpected code ${code}`);
    }
  });
});

describe('the level gate', () => {
  it('locks the auction house below level 8', () => {
    // The client's own floor (`data/MarketplaceInfo.as:24`), enforced
    // client-side at `GUI/GuiManager.as:647-650`.
    const result = service().getBetsList({ userId: 'alice', level: 7 }, T0);
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_MARKETPLACE_LOCKED);
    assert.equal(result.bets, undefined);
  });

  it('opens it at level 8, and does not filter the listings by their tier', () => {
    // A listing's own `level` is the unit's tier, not a requirement on the
    // player, so all three listings are visible.
    const result = service().getBetsList({ userId: 'alice', level: 8 }, T0);
    assert.equal(result.success, true);
    assert.equal(result.bets?.length, 3);
  });
});

describe('the sort order', () => {
  it('puts the listings that close soonest first', () => {
    // `data/MarketplaceInfo.as:118`: `["isPrivate","endDate"]` with
    // `[Array.NUMERIC | Array.DESCENDING, Array.NUMERIC]`.
    const list = service().getBetsList({ userId: 'alice', level: 8 }, T0);
    // Listing "2" closes after 60 minutes, "1" and "3" after 120, and the
    // two that tie keep their configuration order.
    assert.deepEqual(list.bets?.map((bet) => bet.uuid), ['2', '1', '3']);
  });

  it('puts the listings the player takes part in first', () => {
    const market = service();
    market.getBetsList({ userId: 'alice', level: 8 }, T0);
    const bid = market.setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice },
      T0,
    );
    assert.equal(bid.success, true);

    const forAlice = market.getBetsList({ userId: 'alice', level: 8 }, T0);
    assert.deepEqual(forAlice.bets?.map((bet) => bet.uuid), ['1', '2', '3']);

    // Somebody else sees the ordinary order.
    const forBob = market.getBetsList({ userId: 'bob', level: 8 }, T0);
    assert.deepEqual(forBob.bets?.map((bet) => bet.uuid), ['2', '1', '3']);
  });

  it('sorts a plain list the same way', () => {
    const listings: MarketplaceListing[] = [
      { ...blank('a'), endDate: 100 },
      { ...blank('b'), endDate: 50 },
      { ...blank('c'), endDate: 50, isPrivate: true },
    ];
    assert.deepEqual(
      sortMarketplaceListings(listings).map((listing) => listing.uuid),
      ['c', 'b', 'a'],
    );
  });
});

describe('the minimum bid', () => {
  it('refuses a bid under the current price', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 4999, player: alice },
      T0,
    );
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_TOO_LOW);
    assert.equal(result.betResult, 200);
  });

  it('takes a bid at the current price', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice },
      T0,
    );
    assert.equal(result.success, true);
    assert.equal(result.betResult, BET_RESULT_OK);
    assert.equal(result.cashCost, 2);
  });

  it('lifts the price by one increment', () => {
    // `auctions.py:199`: `currentPrice = bet_amount + priceIncrement`.
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const detail = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, T0);
    assert.equal(detail.detail?.currentPrice, 6000);
  });
});

describe('two players bidding the same amount', () => {
  it('refuses the second one, because the price has already moved past it', () => {
    const market = service();
    const first = market.setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice },
      T0,
    );
    assert.equal(first.success, true);

    const second = market.setBet(
      { userId: 'bob', uuid: '1', round: 1, bet: 5000, player: bob },
      T0,
    );
    assert.equal(second.success, false);
    assert.equal(second.error, MARKETPLACE_ERRORS.ERR_BET_TOO_LOW);
    assert.equal(second.betResult, 200);

    // Only the first bid is recorded.
    const detail = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, T0);
    assert.deepEqual(detail.detail?.betUsers.map((bidder) => bidder.user_id), ['alice']);
  });

  it('takes the second one when it meets the new price', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const second = market.setBet(
      { userId: 'bob', uuid: '1', round: 1, bet: 6000, player: bob },
      T0,
    );
    assert.equal(second.success, true);
    const detail = market.getBetDetail({ userId: 'bob', uuid: '1', checkFinish: false }, T0);
    assert.equal(detail.detail?.currentPrice, 7000);
  });
});

describe('a bid on a closed round', () => {
  it('refuses a bid that arrives after the round shut', () => {
    const market = service();
    const late = market.setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice },
      END_1,
    );
    assert.equal(late.success, false);
    assert.equal(late.error, MARKETPLACE_ERRORS.ERR_BET_OUTDATED);
    assert.equal(late.betResult, 100);
  });

  it('refuses a bid on a round that is not the running one', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 2, bet: 5000, player: alice },
      T0,
    );
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_OUTDATED);
  });

  it('keeps the bid out of the listing', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, END_1);
    const detail = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, END_1);
    assert.deepEqual(detail.detail?.betUsers, []);
  });
});

describe('the rounds', () => {
  it('starts the next round when more than one player has bid', () => {
    // The client's own rule ("If more than one player has bid at the end of
    // the 1st round, a 2nd round of 30 secs. will start",
    // `popups/marketplace/PopupMarketplaceHelp.as:20`).
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.setBet({ userId: 'bob', uuid: '1', round: 1, bet: 6000, player: bob }, T0);

    // The round closes at END_1, but it only settles 60 seconds later
    // (`auctions.py:120`).
    const during = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: true }, END_1 + 10);
    assert.equal(during.detail?.round, 1);
    assert.equal(during.detail?.betWinner, undefined);
    assert.equal(during.settlements.length, 0);

    const after = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: true }, END_1 + 60);
    assert.equal(after.detail?.round, 2);
    assert.deepEqual(after.detail?.betUsers, []);
    assert.deepEqual(
      after.detail?.betUsersPrev.map((bidder) => bidder.user_id),
      ['alice', 'bob'],
    );
    // The second round lasts 30 seconds.
    assert.equal(after.detail?.endDate, END_1 + 60 + 30);
    assert.equal(after.detail?.beginDate, END_1 + 60);
  });

  it('decides the listing when only one player has bid', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);

    const settled = market.getBetDetail(
      { userId: 'alice', uuid: '1', checkFinish: true },
      END_1 + 60,
    );
    assert.equal(settled.detail?.betWinner, 'alice');
    assert.equal(settled.detail?.finished, true);
    assert.equal(settled.detail?.won, true);
    assert.equal(settled.detail?.isWinning, true);
    assert.equal(settled.settlements.length, 1);
    assert.equal(settled.settlements[0]?.userId, 'alice');
    assert.equal(settled.settlements[0]?.itemId, 1167);
    assert.equal(settled.settlements[0]?.level, 1);
    // The winner pays the listing's current price — the client deducts
    // exactly that (`data/MarketplaceUnitInfo.as:201-202`).
    assert.equal(settled.settlements[0]?.goldCost, 6000);
  });

  it('does not report the winner to somebody who is not asking for it', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const without = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, END_1 + 60);
    assert.equal(without.detail?.betWinner, undefined);
    const with_ = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: true }, END_1 + 60);
    assert.equal(with_.detail?.betWinner, 'alice');
  });

  it('refuses a bid on a listing that has been decided', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: true }, END_1 + 60);
    const late = market.setBet(
      { userId: 'bob', uuid: '1', round: 1, bet: 99999, player: bob },
      END_1 + 60,
    );
    assert.equal(late.success, false);
    assert.equal(late.error, MARKETPLACE_ERRORS.ERR_BET_OUTDATED);
  });

  it('refuses a bid while the round is settling', () => {
    // The round closed, but it has not been decided yet: the grace period
    // is about the outcome, not about the bid.
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const late = market.setBet(
      { userId: 'bob', uuid: '1', round: 1, bet: 99999, player: bob },
      END_1 + 30,
    );
    assert.equal(late.success, false);
    assert.equal(late.error, MARKETPLACE_ERRORS.ERR_BET_OUTDATED);
  });

  it('shows the loser a decided listing it did not win', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.setBet({ userId: 'bob', uuid: '1', round: 1, bet: 6000, player: bob }, T0);
    const forBob = market.getBetDetail(
      { userId: 'bob', uuid: '1', checkFinish: true },
      END_1 + 120,
    );
    // Two players bid, so the round advanced and nobody has won.
    assert.equal(forBob.detail?.round, 2);
    assert.equal(forBob.detail?.betWinner, undefined);
    assert.equal(forBob.detail?.finished, false);
    assert.equal(forBob.detail?.isPrivate, true);
  });

  it('cycles a listing nobody bid on back to a fresh first round', () => {
    // The upstream recycles an expired listing (`auctions.py:119-143`).
    const market = service();
    const later = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, END_1 + 60);
    assert.equal(later.detail?.round, 1);
    assert.equal(later.detail?.currentPrice, 5000);
    assert.equal(later.detail?.beginPrice, 5000);
    assert.equal(later.detail?.endDate, END_1 + 120 * 60);
  });
});

describe('the listing flags', () => {
  it('tells the player that it is taking part and that it leads', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const list = market.getBetsList({ userId: 'alice', level: 8 }, T0);
    const one = list.bets?.find((bet) => bet.uuid === '1');
    assert.equal(one?.isPrivate, true);
    assert.equal(one?.isWinning, true);
    assert.equal(one?.won, false);
    assert.equal(one?.finished, false);

    const other = list.bets?.find((bet) => bet.uuid === '2');
    assert.equal(other?.isPrivate, false);
    assert.equal(other?.isWinning, false);
  });

  it('follows the lead to the other player', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.setBet({ userId: 'bob', uuid: '1', round: 1, bet: 6000, player: bob }, T0);
    const list = market.getBetsList({ userId: 'alice', level: 8 }, T0);
    const one = list.bets?.find((bet) => bet.uuid === '1');
    assert.equal(one?.isWinning, false);
    const forBob = market.getBetsList({ userId: 'bob', level: 8 }, T0);
    assert.equal(forBob.bets?.find((bet) => bet.uuid === '1')?.isWinning, true);
  });

  it('keeps a player in the running while the previous round is the one before', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.setBet({ userId: 'bob', uuid: '1', round: 1, bet: 6000, player: bob }, T0);
    const after = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: true }, END_1 + 60);
    assert.equal(after.detail?.isPrivate, true);
    assert.equal(after.detail?.isWinning, false);
  });
});

describe('the leading bids of one player', () => {
  it('refuses the fourth leading bid in a row', () => {
    // The client refuses it at the third (`popups/marketplace/PopupMarketplaceUnit.as:313`).
    const market = service();
    assert.equal(
      market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0).success,
      true,
    );
    assert.equal(
      market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 6000, player: alice }, T0).success,
      true,
    );
    assert.equal(
      market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 7000, player: alice }, T0).success,
      true,
    );
    const fourth = market.setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 8000, player: alice },
      T0,
    );
    assert.equal(fourth.success, false);
    assert.equal(fourth.error, MARKETPLACE_ERRORS.ERR_BET_LIMIT_REACHED);
  });

  it('lets the player bid again once somebody else has outbid them', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 6000, player: alice }, T0);
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 7000, player: alice }, T0);
    market.setBet({ userId: 'bob', uuid: '1', round: 1, bet: 8000, player: bob }, T0);
    const again = market.setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 9000, player: alice },
      T0,
    );
    assert.equal(again.success, true);
  });
});

describe('the wallet', () => {
  it('refuses a bid the player cannot pay in gold', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: { gold: 100, cash: 100 } },
      T0,
    );
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_NOT_AFFORDABLE);
  });

  it('refuses a bid the player cannot pay the fee for', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: { gold: 1_000_000, cash: 1 } },
      T0,
    );
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_NOT_AFFORDABLE);
  });

  it('takes the bid when the player can pay both', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice },
      T0,
    );
    assert.equal(result.success, true);
    assert.equal(result.cashCost, 2);
  });
});

describe('the detail payload', () => {
  it('is the listing, flat, with the state again under betDetail', () => {
    // The client copies `param1.betDetail` into its own listing
    // (`data/MarketplaceUnitInfo.as:179`) and reads `param1.round` and
    // `param1.endDate` at the top level (`data/MarketplaceUnitInfo.as:170`).
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const result = market.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, T0);
    const detail = result.detail;
    assert.ok(detail);
    assert.equal(detail.round, 1);
    assert.equal(detail.endDate, END_1);
    assert.equal(typeof detail.betDetail, 'object');
    assert.equal(Array.isArray(detail.betDetail), false);
    assert.equal(detail.betDetail.round, 1);
    assert.equal(detail.betDetail.endDate, END_1);
    assert.deepEqual(detail.betUsers.map((bidder) => bidder.user_id), ['alice']);
    assert.equal(detail.betUsers[0]?.fb_name, 'Alice');
    assert.equal(detail.betUsers[0]?.bet, 5000);
    assert.deepEqual(detail.betUsersPrev, []);
  });

  it('refuses a listing that does not exist', () => {
    const result = service().getBetDetail({ userId: 'alice', uuid: '999', checkFinish: false }, T0);
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_NOT_FOUND);
  });

  it('refuses a bid on a listing that does not exist', () => {
    const result = service().setBet(
      { userId: 'alice', uuid: '999', round: 1, bet: 100, player: alice },
      T0,
    );
    assert.equal(result.success, false);
    assert.equal(result.error, MARKETPLACE_ERRORS.ERR_BET_NOT_FOUND);
  });
});

describe('the state', () => {
  it('round trips through the persistence layer', () => {
    const market = service();
    market.setBet({ userId: 'alice', uuid: '1', round: 1, bet: 5000, player: alice }, T0);
    const saved = market.state();
    assert.equal(saved.length, 3);
    const restored = new MarketplaceService(CONFIGS, Object.fromEntries(saved.map((l) => [l.uuid, l])));
    const detail = restored.getBetDetail({ userId: 'alice', uuid: '1', checkFinish: false }, T0);
    assert.equal(detail.detail?.currentPrice, 6000);
    assert.deepEqual(detail.detail?.betUsers.map((bidder) => bidder.user_id), ['alice']);
  });
});

/** A listing with nothing but an id, for the sort test. */
function blank(uuid: string): MarketplaceListing {
  return {
    uuid,
    idUnit: 0,
    level: 0,
    beginDate: 0,
    endDate: 0,
    beginPrice: 0,
    currentPrice: 0,
    priceIncrement: 0,
    betPrice: 0,
    round: 1,
    isPrivate: false,
    isWinning: false,
    won: false,
    finished: false,
    betUsers: [],
    betUsersPrev: [],
  };
}
