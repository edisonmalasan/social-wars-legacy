import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { LOCKED_OFFSET, buildMenu, buildTabs, sortKey, type BuildMenuItem } from './buildmenu.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

function item(over: Partial<BuildMenuItem> = {}): BuildMenuItem {
  return {
    id: 1,
    name: 'House I',
    categoryId: 1,
    subcategoryId: 11,
    displayOrder: 10,
    minLevel: 1,
    costs: { w: 30 },
    buildTime: 5,
    clicksToBuild: 1,
    inStore: true,
    ...over,
  };
}

describe('the build menu order', () => {
  it('is the display order', () => {
    const items = [
      item({ id: 1, displayOrder: 30 }),
      item({ id: 2, displayOrder: 10 }),
      item({ id: 3, displayOrder: 20 }),
    ];
    assert.deepEqual(
      buildMenu(items, 10).map((entry) => entry.id),
      [2, 3, 1],
    );
  });

  it('pushes the items the player is too low a level for down the list', () => {
    const items = [
      item({ id: 1, displayOrder: 10, minLevel: 1 }),
      item({ id: 2, displayOrder: 20, minLevel: 50 }),
      item({ id: 3, displayOrder: 30, minLevel: 1 }),
    ];
    // The locked item keeps its place relative to the others, but it goes
    // after everything the player can build.
    assert.deepEqual(
      buildMenu(items, 10).map((entry) => entry.id),
      [1, 3, 2],
    );
  });

  it('does not lock an item the player is exactly at the level for', () => {
    const entry = buildMenu([item({ minLevel: 10 })], 10)[0]!;
    assert.equal(entry.locked, false);
    assert.equal(entry.sortInt, 10);
  });

  it('locks an item one level above the player', () => {
    const entry = buildMenu([item({ minLevel: 11 })], 10)[0]!;
    assert.equal(entry.locked, true);
    assert.equal(entry.sortInt, 10 + LOCKED_OFFSET);
  });

  it('is stable for the items that tie', () => {
    const items = [
      item({ id: 1, displayOrder: 10 }),
      item({ id: 2, displayOrder: 10 }),
      item({ id: 3, displayOrder: 10 }),
    ];
    assert.deepEqual(
      buildMenu(items, 10).map((entry) => entry.id),
      [1, 2, 3],
    );
  });

  it('filters to one category', () => {
    const items = [
      item({ id: 1, categoryId: 1 }),
      item({ id: 2, categoryId: 7 }),
    ];
    assert.deepEqual(
      buildMenu(items, 10, 1).map((entry) => entry.id),
      [1],
    );
  });

  it('computes the sort key the same way', () => {
    assert.equal(sortKey(item({ displayOrder: 10, minLevel: 1 }), 10), 10);
    assert.equal(sortKey(item({ displayOrder: 10, minLevel: 50 }), 10), 10 + LOCKED_OFFSET);
  });
});

describe('the build tabs', () => {
  it('are the categories, with their sub-categories', () => {
    const tabs = buildTabs({
      '1': { id: 1, name: 'Village', sub: [{ id: 11, name: 'Houses' }] },
      '2': { id: 2, name: 'Military' },
    });
    assert.equal(tabs.length, 2);
    assert.equal(tabs[0]!.name, 'Village');
    assert.deepEqual(tabs[0]!.subcategories, [{ id: 11, name: 'Houses' }]);
    assert.deepEqual(tabs[1]!.subcategories, []);
  });
});

describe('the real content', () => {
  it('gives every item a display order', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as { items: { display_order?: number }[] };
    for (const entry of bundle.items) {
      assert.equal(
        typeof entry.display_order,
        'number',
        'an item has no display order',
      );
    }
  });

  it('builds a menu with every item in it', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as {
      items: {
        id: number;
        name: string;
        category_id: number;
        subcategory_id: number;
        display_order: number;
        min_level: number;
        costs: Record<string, number>;
        build_time: number;
        clicks_to_build: number;
        in_store: boolean;
      }[];
      categories: Record<string, { id: number; name: string; sub?: { id: number; name: string }[] }>;
    };

    const items: BuildMenuItem[] = bundle.items.map((entry) => ({
      id: entry.id,
      name: entry.name,
      categoryId: entry.category_id,
      subcategoryId: entry.subcategory_id,
      displayOrder: entry.display_order,
      minLevel: entry.min_level,
      costs: entry.costs,
      buildTime: entry.build_time,
      clicksToBuild: entry.clicks_to_build,
      inStore: entry.in_store === true,
    }));

    // A level-1 player sees the level-1 items first, and the rest after.
    const menu = buildMenu(items, 1);
    assert.equal(menu.length, items.length);
    const firstLocked = menu.findIndex((entry) => entry.locked);
    assert.ok(firstLocked > 0, 'something is locked at level 1');
    for (let index = 0; index < firstLocked; index++) {
      assert.equal(menu[index]!.locked, false);
    }

    // The tabs cover the content's categories.
    const tabs = buildTabs(bundle.categories);
    assert.ok(tabs.length > 0);
    for (const tab of tabs) {
      assert.ok(
        items.some((entry) => entry.categoryId === tab.id),
        `the tab ${tab.name} has no items`,
      );
    }
  });
});
