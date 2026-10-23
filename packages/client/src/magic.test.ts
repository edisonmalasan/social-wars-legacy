import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  MAGIC_BOOK_PAGE_SIZE,
  MAGIC_LAB_PAGE_SIZE,
  magicBook,
  magicEntries,
  magicInputFromWorld,
  magicLab,
  magicPlayerFromWorld,
  magicProgress,
  paginate,
  selectedMagic,
  type MagicInput,
  type MagicPlayer,
} from './magic.ts';
import type { WorldSnapshot } from './session.ts';

const GLOBALS = {
  MANA_PER_PURCHASE: 5,
  COST_MANA_CASH: 1,
  COST_MANA_GOLD: 10_000,
  NUM_SPELL_USES_LVL2: 25,
  NUM_SPELL_USES_LVL3: 50,
};

const SPELLS = [
  {
    id: 1,
    name: 'Spell One',
    description: 'The first spell.',
    mana: 8,
    level: 20,
    gold: 30_000,
    cash: 50,
    area: '[5,7,9]',
    target: 2,
    img_name: 'one',
  },
  {
    id: 2,
    name: 'Spell Two',
    description: 'The second spell.',
    mana: 4,
    level: 5,
    gold: 100,
    cash: 1,
    area: '[5,7,9]',
    target: 1,
    img_name: 'two',
  },
  {
    id: 3,
    name: 'Spell Three',
    description: 'The third spell.',
    mana: 12,
    level: 5,
    gold: 200,
    cash: 2,
    area: '[25,30,35]',
    target: 2,
    img_name: 'three',
  },
  {
    id: 4,
    name: 'Spell Four',
    description: 'The fourth spell.',
    mana: 5,
    level: 1,
    gold: 10,
    cash: 1,
    area: '[5,7,9]',
    target: 0,
    img_name: 'four',
  },
  {
    id: 5,
    name: 'Spell Five',
    description: 'The fifth spell.',
    mana: 6,
    level: 30,
    gold: 50,
    cash: 3,
    area: '[5,7,9]',
    target: 1,
    img_name: 'five',
  },
  {
    id: 6,
    name: 'Spell Six',
    description: 'The sixth spell.',
    mana: 7,
    level: 40,
    gold: 60,
    cash: 4,
    area: '[5,7,9]',
    target: 2,
    img_name: 'six',
  },
  {
    id: 7,
    name: 'Spell Seven',
    description: 'The seventh spell.',
    mana: 9,
    level: 50,
    gold: 70,
    cash: 5,
    area: '[5,7,9]',
    target: 0,
    img_name: 'seven',
  },
  {
    id: 8,
    name: 'Spell Eight',
    description: 'The eighth spell.',
    mana: 10,
    level: 60,
    gold: 80,
    cash: 6,
    area: '[5,7,9]',
    target: 1,
    img_name: 'eight',
  },
];

const PLAYER: MagicPlayer = {
  level: 20,
  gold: 100_000,
  cash: 1_000,
  mana: 20,
  magics: {},
  disabledSpells: [],
};

function input(over: Partial<MagicPlayer> = {}): MagicInput {
  return {
    spells: SPELLS,
    globals: GLOBALS,
    player: { ...PLAYER, ...over },
  };
}

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

describe('the magic entries', () => {
  it('are ordered by unlock level and keep the content order for ties', () => {
    const entries = magicEntries(input());
    assert.deepEqual(
      entries.map((entry) => entry.id),
      [4, 2, 3, 1, 5, 6, 7, 8],
    );
  });

  it('labels a spell learned, available or blocked', () => {
    const entries = magicEntries(
      input({
        level: 20,
        magics: { '1': 0, '2': 0 },
      }),
    );
    const byId = new Map(entries.map((entry) => [entry.id, entry]));
    assert.equal(byId.get(1)!.status, 'learned');
    assert.equal(byId.get(2)!.status, 'learned');
    assert.equal(byId.get(3)!.status, 'available');
    assert.equal(byId.get(5)!.status, 'blocked');
  });

  it('keeps a cash-bought spell learned below its unlock level', () => {
    const entry = magicEntries(input({ level: 1, magics: { '1': 0 } })).find(
      (candidate) => candidate.id === 1,
    )!;
    assert.equal(entry.known, true);
    assert.equal(entry.status, 'learned');
    assert.equal(entry.available, false);
  });

  it('gives the area for the spell level', () => {
    const entries = magicEntries(input({ magics: { '3': 25 } }));
    const spell = entries.find((entry) => entry.id === 3)!;
    assert.equal(spell.level, 2);
    assert.equal(spell.areaForLevel, 30);
    assert.equal(
      magicEntries(input()).find((entry) => entry.id === 3)!.areaForLevel,
      null,
    );
  });
});

describe('paging', () => {
  it('splits the list and clamps an out-of-range page', () => {
    const page = paginate([1, 2, 3, 4, 5, 6, 7], 0, 3);
    assert.equal(page.pageCount, 3);
    assert.deepEqual(page.items, [1, 2, 3]);
    assert.equal(page.canPrev, false);
    assert.equal(page.canNext, true);

    const last = paginate([1, 2, 3, 4, 5, 6, 7], 99, 3);
    assert.equal(last.page, 2);
    assert.deepEqual(last.items, [7]);
    assert.equal(last.canPrev, true);
    assert.equal(last.canNext, false);
  });

  it('has one empty page when there is nothing', () => {
    const page = paginate([], 4, 3);
    assert.deepEqual(page, {
      page: 0,
      pageCount: 1,
      items: [],
      canPrev: false,
      canNext: false,
    });
  });

  it('uses the Research LAB and spell book page sizes', () => {
    assert.equal(MAGIC_LAB_PAGE_SIZE, 6);
    assert.equal(MAGIC_BOOK_PAGE_SIZE, 3);
  });
});

describe('the Research LAB', () => {
  it('shows six spells a page and the mana pack', () => {
    const first = magicLab(input({ cash: 10, gold: 10_000 }));
    assert.equal(first.page, 0);
    assert.equal(first.pageCount, 2);
    assert.equal(first.items.length, 6);
    assert.equal(first.canPrev, false);
    assert.equal(first.canNext, true);
    assert.equal(first.mana, 20);
    assert.deepEqual(first.pack, {
      amount: 5,
      price: { c: 1, g: 10_000 },
    });
    assert.deepEqual(first.canBuyMana, { c: true, g: true });
  });

  it('shows the rest on the second page and reports short funds', () => {
    const second = magicLab(input({ cash: 0, gold: 0 }), 1);
    assert.equal(second.page, 1);
    assert.equal(second.items.length, 2);
    assert.equal(second.canPrev, true);
    assert.equal(second.canNext, false);
    assert.deepEqual(second.canBuyMana, { c: false, g: false });
  });
});

describe('the selected spell', () => {
  it('is null for a spell the content does not have', () => {
    assert.equal(selectedMagic(input(), 999), null);
  });

  it('shows the buy panel at the unlock level', () => {
    const selection = selectedMagic(input({ level: 20, magics: {} }), 1)!;
    assert.equal(selection.zone, 'buy');
    assert.equal(selection.stars, 0);
    assert.equal(selection.progress, 0);
    assert.equal(selection.nextLevelUses, null);
    assert.equal(selection.canBuyGold, true);
    assert.equal(selection.canBuyCash, true);
    assert.equal(selection.canCast, false);
    assert.equal(selection.needsMana, false);
    assert.equal(selection.manaGrant, 8);
  });

  it('locks the gold button below the unlock level but leaves cash live', () => {
    const selection = selectedMagic(input({ level: 1, magics: {} }), 1)!;
    assert.equal(selection.zone, 'locked');
    assert.equal(selection.canBuyGold, false);
    assert.equal(selection.canBuyCash, true);
  });

  it('checks the price against the wallet', () => {
    const selection = selectedMagic(input({ gold: 0, cash: 0, magics: {} }), 1)!;
    assert.equal(selection.canBuyGold, false);
    assert.equal(selection.canBuyCash, false);
  });

  it('shows the known panel and the first star at zero uses', () => {
    const selection = selectedMagic(input({ magics: { '1': 0 } }), 1)!;
    assert.equal(selection.zone, 'known');
    assert.equal(selection.stars, 1);
    assert.equal(selection.progress, 0);
    assert.equal(selection.nextLevelUses, 25);
    assert.equal(selection.canCast, true);
    assert.equal(selection.canBuyGold, false);
    assert.equal(selection.canBuyCash, false);
  });

  it('fills the bar on the way to level 2', () => {
    const selection = selectedMagic(input({ magics: { '1': 10 } }), 1)!;
    assert.equal(selection.stars, 1);
    assert.equal(selection.progress, 0.4);
    assert.equal(selection.nextLevelUses, 25);
  });

  it('starts the second bar at level 2 and fills it at level 3', () => {
    const level2 = selectedMagic(input({ magics: { '1': 25 } }), 1)!;
    assert.equal(level2.stars, 2);
    assert.equal(level2.progress, 0);
    assert.equal(level2.nextLevelUses, 50);

    const level3 = selectedMagic(input({ magics: { '1': 50 } }), 1)!;
    assert.equal(level3.stars, 3);
    assert.equal(level3.progress, 1);
    assert.equal(level3.nextLevelUses, null);
  });

  it('tells a learned spell with too little mana that it needs mana', () => {
    const selection = selectedMagic(input({ magics: { '1': 0 }, mana: 7 }), 1)!;
    assert.equal(selection.canCast, false);
    assert.equal(selection.needsMana, true);
  });
});

describe('the battle spell book', () => {
  it('is empty until a spell is learned', () => {
    const book = magicBook(input());
    assert.deepEqual(book.items, []);
    assert.equal(book.pageCount, 1);
    assert.equal(book.mana, 20);
  });

  it('lists only learned spells, three a page and in id order', () => {
    const book = magicBook(input({ magics: { '3': 0, '1': 0, '2': 0 } }));
    assert.deepEqual(
      book.items.map((spell) => spell.id),
      [1, 2, 3],
    );
    assert.equal(book.canNext, false);

    const many = magicBook(input({ magics: { '1': 0, '2': 0, '3': 0, '4': 0 } }), 1);
    assert.equal(many.page, 1);
    assert.equal(many.pageCount, 2);
    assert.deepEqual(
      many.items.map((spell) => spell.id),
      [4],
    );
  });

  it('separates the quest veto from the mana check', () => {
    const book = magicBook(
      input({ magics: { '1': 0, '2': 0 }, mana: 4, disabledSpells: [2] }),
    );
    const [one, two] = book.items;
    assert.equal(one!.enabled, true);
    assert.equal(one!.castable, false);
    assert.equal(two!.enabled, false);
    assert.equal(two!.castable, false);
  });

  it('uses the spell level for the area', () => {
    const book = magicBook(input({ magics: { '3': 25 }, mana: 100 }));
    assert.equal(book.items[0]!.level, 2);
    assert.equal(book.items[0]!.areaForLevel, 30);
  });
});

describe('the progress bar', () => {
  it('is empty when unlearned or never cast', () => {
    assert.equal(magicProgress(null, GLOBALS), 0);
    assert.equal(magicProgress(0, GLOBALS), 0);
  });

  it('runs to 25 and then to 50', () => {
    assert.equal(magicProgress(24, GLOBALS), 0.96);
    assert.equal(magicProgress(25, GLOBALS), 0);
    assert.equal(magicProgress(37, GLOBALS), 0.48);
    assert.equal(magicProgress(50, GLOBALS), 1);
    assert.equal(magicProgress(500, GLOBALS), 1);
  });

  it('does not divide by a bad threshold', () => {
    assert.equal(
      magicProgress(1, { NUM_SPELL_USES_LVL2: 0, NUM_SPELL_USES_LVL3: 0 }),
      1,
    );
  });
});

describe('the server snapshot', () => {
  function world(over: Partial<WorldSnapshot> = {}): WorldSnapshot {
    return {
      maps: [{ id: 0, items: {}, level: 12 }],
      privateState: { magics: { '1': 0 }, mana: 4 },
      resources: { g: 500, c: 70, m: 9 },
      ...over,
    };
  }

  it('reads the level, wallet, mana and learned spells', () => {
    const player = magicPlayerFromWorld(world());
    assert.deepEqual(player, {
      level: 12,
      gold: 500,
      cash: 70,
      mana: 4,
      magics: { '1': 0 },
      disabledSpells: [],
    });
  });

  it('falls back to the wallet mana when the mirror is missing', () => {
    assert.equal(
      magicPlayerFromWorld(world({ privateState: { magics: {} } })).mana,
      9,
    );
  });

  it('passes the quest-disabled spells through', () => {
    assert.deepEqual(magicPlayerFromWorld(world(), [1, 2]).disabledSpells, [1, 2]);
  });

  it('builds the input with the content', () => {
    const built = magicInputFromWorld(world(), SPELLS, GLOBALS);
    assert.equal(built.spells.length, SPELLS.length);
    assert.equal(built.globals, GLOBALS);
    assert.equal(built.player.level, 12);
  });
});

describe('the real content', () => {
  it('has ten spells and two Research LAB pages', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as { magics?: unknown[]; globals: Record<string, unknown> };
    const built = {
      spells: bundle.magics ?? [],
      globals: bundle.globals,
      player: { ...PLAYER, magics: {} },
    };
    const entries = magicEntries(built);
    assert.equal(entries.length, 10);
    for (let index = 1; index < entries.length; index++) {
      assert.ok(
        entries[index - 1]!.unlockLevel <= entries[index]!.unlockLevel,
        'the spells are not in unlock order',
      );
    }
    const lab = magicLab(built);
    assert.equal(lab.pageCount, 2);
    assert.equal(lab.items.length, 6);
    assert.equal(magicLab(built, 1).items.length, 4);
  });

  it('lists all ten learned spells over four spell-book pages', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as { magics?: unknown[]; globals: Record<string, unknown> };
    const magics = Object.fromEntries(
      (bundle.magics ?? []).map((raw) => [String((raw as { id: number }).id), 0]),
    );
    const built = {
      spells: bundle.magics ?? [],
      globals: bundle.globals,
      player: { ...PLAYER, magics },
    };
    assert.equal(magicBook(built).pageCount, 4);
    assert.equal(magicBook(built, 0).items.length, 3);
    assert.equal(magicBook(built, 3).items.length, 1);
  });
});
