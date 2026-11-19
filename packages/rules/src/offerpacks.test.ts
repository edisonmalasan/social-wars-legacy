import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  offerPackCandidates,
  offerPackPrice,
  offerPackRewardItems,
  offerPackShape,
  offerPackTierForCount,
  parseOfferPackSelection,
  isOfferPackAvailable,
  type OfferPackData,
  type OfferPackRandom,
} from './offerpacks.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function realPacks(): Promise<Map<number, OfferPackData>> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as { offerPacks: OfferPackData[] };
  return new Map(bundle.offerPacks.map((pack) => [pack.id, pack]));
}

function fakeRandom(
  next: () => number,
  int: (min: number, max: number) => number = (min) => min,
): OfferPackRandom {
  return { next, int };
}

describe('the offer-pack shapes', () => {
  it('reads the client\'s own random and super id lists', async () => {
    const packs = await realPacks();
    assert.equal(offerPackShape(packs.get(1)!), 'flat');
    assert.equal(offerPackShape(packs.get(4)!), 'random');
    assert.equal(offerPackShape(packs.get(18)!), 'premium');
    // Pack 19 has an empty type but is in SUPER_PACK_IDS.
    assert.equal(offerPackShape(packs.get(19)!), 'super');
    assert.equal(offerPackShape(packs.get(44)!), 'super');
  });

  it('treats a zero enabled flag or a zero position as hidden', async () => {
    const packs = await realPacks();
    assert.equal(isOfferPackAvailable(packs.get(1)!), true);
    assert.equal(isOfferPackAvailable(packs.get(4)!), false);
    assert.equal(isOfferPackAvailable(packs.get(44)!), true);
  });

  it('reads the three super tiers from the selected-item count', async () => {
    const packs = await realPacks();
    const pack = packs.get(44)!;
    assert.equal(offerPackTierForCount(pack, 1), 0);
    assert.equal(offerPackTierForCount(pack, 2), 1);
    assert.equal(offerPackTierForCount(pack, 4), 2);
    assert.equal(offerPackTierForCount(pack, 0), null);
    assert.equal(offerPackTierForCount(pack, 3), null);
    assert.equal(offerPackTierForCount(packs.get(1)!, 1), null);
  });

  it('prices flat, random and super packs from the content', async () => {
    const packs = await realPacks();
    assert.equal(offerPackPrice(packs.get(1)!, null), 25);
    assert.equal(offerPackPrice(packs.get(4)!, null), 20);
    assert.equal(offerPackPrice(packs.get(44)!, 0), 60);
    assert.equal(offerPackPrice(packs.get(44)!, 1), 100);
    assert.equal(offerPackPrice(packs.get(44)!, 2), 200);
    // Pack 19's own override, even though its type is empty.
    assert.equal(offerPackPrice(packs.get(19)!, 0), 30);
    assert.equal(offerPackPrice(packs.get(19)!, 1), 60);
    assert.equal(offerPackPrice(packs.get(19)!, 2), 100);
    assert.equal(offerPackPrice(packs.get(18)!, null), null);
    assert.equal(offerPackPrice(packs.get(44)!, null), null);
  });
});

describe('the offer-pack selection', () => {
  it('accepts the legacy JSON string and the native array', () => {
    assert.deepEqual(parseOfferPackSelection('["10","11"]'), ['10', '11']);
    assert.deepEqual(parseOfferPackSelection([10, 11]), [10, 11]);
    assert.equal(parseOfferPackSelection('{"items":[]}'), null);
    assert.equal(parseOfferPackSelection('not json'), null);
    assert.equal(parseOfferPackSelection(undefined), null);
  });
});

describe('the offer-pack candidates', () => {
  it('reads item ids, not the random thresholds', async () => {
    const packs = await realPacks();
    assert.deepEqual(offerPackCandidates(packs.get(4)!), [67, 85, 1046, 1037]);
    assert.equal(offerPackCandidates(packs.get(18)!), null);
  });

  it('refuses a malformed item id', async () => {
    const packs = await realPacks();
    // 1072.1224 is not an item id; pack 35 is hidden, but its data is still
    // rejected rather than normalised into an unplaceable store entry.
    assert.equal(offerPackCandidates(packs.get(35)!), null);
  });
});

describe('rolling an offer pack', () => {
  it('grants every item of a flat pack', async () => {
    const packs = await realPacks();
    assert.deepEqual(
      offerPackRewardItems(packs.get(1)!, null, fakeRandom(() => 0)),
      [1042, 84],
    );
  });

  it('rolls a random pack against its thresholds', async () => {
    const packs = await realPacks();
    const pack = packs.get(4)!;
    assert.deepEqual(offerPackRewardItems(pack, null, fakeRandom(() => 0)), [67]);
    assert.deepEqual(offerPackRewardItems(pack, null, fakeRandom(() => 0.5)), [85]);
    assert.deepEqual(offerPackRewardItems(pack, null, fakeRandom(() => 0.95)), [1037]);
    // The last threshold is 100, so a one still falls back to the last id.
    assert.deepEqual(offerPackRewardItems(pack, null, fakeRandom(() => 1)), [1037]);
  });

  it('rolls the three super tiers from the three rarity rows', async () => {
    const packs = await realPacks();
    const pack = packs.get(44)!;

    // Tier 0: one from rows 1+2.
    assert.deepEqual(offerPackRewardItems(pack, 0, fakeRandom(() => 0)), [1223]);
    // Tier 1: one from all three rows, then one from rows 1+2.
    assert.deepEqual(offerPackRewardItems(pack, 1, fakeRandom(() => 0)), [1210, 1223]);
    // Tier 2: one rare, then three from rows 1+2.
    assert.deepEqual(offerPackRewardItems(pack, 2, fakeRandom(() => 0)), [
      1210,
      1223,
      1223,
      1223,
    ]);
  });

  it('weights tier one\'s first pick by the rows\' lengths', async () => {
    const packs = await realPacks();
    const pack = packs.get(44)!;
    // Row 0 has 3 items; index 3 is the first item of row 1.
    let calls = 0;
    assert.deepEqual(
      offerPackRewardItems(
        pack,
        1,
        fakeRandom(
          () => 0,
          (min) => (calls++ === 0 ? 3 : min),
        ),
      ),
      [1223, 1223],
    );
  });

  it('refuses an invalid tier or a malformed pack', async () => {
    const packs = await realPacks();
    assert.equal(offerPackRewardItems(packs.get(44)!, 3, fakeRandom(() => 0)), null);
    assert.equal(offerPackRewardItems(packs.get(35)!, 2, fakeRandom(() => 0)), null);
  });
});
