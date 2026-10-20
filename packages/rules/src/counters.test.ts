import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { COUNTERS, NO_COUNTER, counterMultiplier } from './counters.ts';

/** The repository root, found by walking up to the workspace file. */
function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

const BUNDLE = path.join(repoRoot(), 'packages/content/dist/content-bundle.json');

/** The shape of a content item the counters care about. */
interface ContentItem {
  id: number;
  name: string;
  best_against: string | null;
  best_against_mult: number;
}

interface ContentBundle {
  items: ContentItem[];
}

async function loadBundle(): Promise<ContentBundle> {
  return JSON.parse(await readFile(BUNDLE, 'utf8')) as ContentBundle;
}

describe('the counters', () => {
  it('applies the multiplier only when the target carries the key', () => {
    const attacker = { bestAgainst: 'ft_flying', multiplier: 20 };
    assert.equal(counterMultiplier(attacker, { ft_flying: 1 }), 20);
    assert.equal(counterMultiplier(attacker, { ft_ground: 1 }), 1);
    assert.equal(counterMultiplier(attacker, {}), 1);
  });

  it('treats the "-1" sentinel as no counter', () => {
    const attacker = { bestAgainst: NO_COUNTER, multiplier: 2 };
    assert.equal(counterMultiplier(attacker, { '-1': 1 }), 1);
    assert.equal(counterMultiplier(attacker, {}), 1);
  });

  it('treats a 1x best_against as a plain match', () => {
    const attacker = { bestAgainst: 'ft_ground', multiplier: 1 };
    assert.equal(counterMultiplier(attacker, { ft_ground: 1 }), 1);
  });

  it('matches the shipped content exactly', async () => {
    const bundle = await loadBundle();
    const real = bundle.items
      .filter((i) => i.best_against && i.best_against_mult > 1)
      .filter((i) => i.best_against !== NO_COUNTER)
      .map((i) => ({
        id: i.id,
        name: i.name,
        bestAgainst: i.best_against,
        multiplier: i.best_against_mult,
      }))
      .sort((a, b) => b.multiplier - a.multiplier);

    assert.deepEqual(real, COUNTERS.map((c) => ({ ...c })));
  });

  it('has exactly four real counters, and nothing else above 1x', async () => {
    const bundle = await loadBundle();
    const above = bundle.items.filter((i) => i.best_against_mult > 1);
    const real = above.filter((i) => i.best_against !== NO_COUNTER);
    assert.equal(real.length, 4);
    // The rest are the "-1" offer packs, which never counter anything.
    assert.equal(above.length - real.length, 138);
  });
});
