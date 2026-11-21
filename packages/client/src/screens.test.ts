import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { buildMenu } from './buildmenu.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface Screen {
  path: string;
  kind: string;
  decision: string;
  decisionNote: string;
}

interface ScreenInventory {
  counts: { total: number; byDecision: Record<string, number> };
  screens: Screen[];
}

async function inventory(): Promise<ScreenInventory> {
  return JSON.parse(
    await readFile(path.join(repoRoot(), 're/data/ui-screens.json'), 'utf8'),
  ) as ScreenInventory;
}

async function screens(): Promise<Screen[]> {
  return (await inventory()).screens;
}

describe('the screen inventory', () => {
  it('lists the client 260 screens', async () => {
    const all = await screens();
    assert.equal(all.length, 260);
  });

  it('checks the recorded decision counts against the screens', async () => {
    // The roadmap quotes these counts, so the header and the records must
    // agree and a hand-edit of either one must fail a test.
    const { counts, screens: all } = await inventory();
    assert.equal(counts.total, 260);
    assert.deepEqual(counts.byDecision, {
      implemented: 94,
      dropped: 52,
      planned: 114,
    });
    const recomputed: Record<string, number> = {};
    for (const screen of all) {
      recomputed[screen.decision] = (recomputed[screen.decision] ?? 0) + 1;
    }
    assert.deepEqual(recomputed, counts.byDecision);
  });

  it('gives every screen a decision', async () => {
    const all = await screens();
    for (const screen of all) {
      assert.ok(
        ['implemented', 'dropped', 'planned'].includes(screen.decision),
        `${screen.path} has the decision "${screen.decision}"`,
      );
    }
  });

  it('names a model that exists for every implemented screen', async () => {
    const all = await screens();
    const root = repoRoot();
    for (const screen of all) {
      if (screen.decision !== 'implemented') continue;
      const match = /`([^`]+)`/.exec(screen.decisionNote);
      assert.ok(match, `${screen.path} names no model`);
      const model = match![1]!;
      assert.ok(
        existsSync(path.join(root, model.replace(/\//g, path.sep))),
        `${screen.path} names ${model}, which does not exist`,
      );
    }
  });

  it('gives every dropped screen a reason', async () => {
    const all = await screens();
    const dropped = all.filter((screen) => screen.decision === 'dropped');
    assert.ok(dropped.length > 0, 'nothing is dropped');
    for (const screen of dropped) {
      assert.ok(
        screen.decisionNote.startsWith('Dropped: '),
        `${screen.path} is dropped without a reason`,
      );
      assert.ok(
        screen.decisionNote.length > 40,
        `${screen.path} is dropped without saying why`,
      );
    }
  });

  it('gives every planned screen a checked deferral reason', async () => {
    // A planned screen is in-scope work, not a finished one. Its note must
    // say what is missing or what unblocks it, so deferrals stay testable
    // rather than being a synonym for "we never got round to it".
    const all = await screens();
    const planned = all.filter((screen) => screen.decision === 'planned');
    assert.ok(planned.length > 0, 'nothing is planned');
    for (const screen of planned) {
      assert.ok(
        screen.decisionNote.startsWith('Deferred: '),
        `${screen.path} is planned without a "Deferred: " reason`,
      );
      assert.ok(
        screen.decisionNote.length > 40,
        `${screen.path} is planned without saying what is missing or how it unblocks`,
      );
    }
  });

  it('drops the upstream administrative panel', async () => {
    // The clone has no administrative interface: a panel that could edit
    // the rules would be the `flash_debug` hole again.
    const all = await screens();
    const admin = all.find((screen) => screen.path === 'GUI/AdminPanel.as');
    assert.ok(admin, 'the admin panel is not in the inventory');
    assert.equal(admin!.decision, 'dropped');
  });

  it('drops the cross-promotion to the other Zynga games', async () => {
    const all = await screens();
    for (const screen of all) {
      if (!screen.path.includes('cross')) continue;
      assert.equal(screen.decision, 'dropped', `${screen.path} is not dropped`);
    }
  });

  it('drops the screens that take real money', async () => {
    const all = await screens();
    for (const screen of all) {
      if (!/PopupBuy(Gold|Mana)/.test(screen.path)) continue;
      assert.equal(screen.decision, 'dropped', `${screen.path} is not dropped`);
    }
  });

  it('records the social screens as out of scope for the client', async () => {
    // The server keeps and serves the alliance and auction services, but
    // the web client does not surface them (ADR 20). A server model is not
    // a client screen: these are dropped with a reason, or still planned.
    const all = await screens();
    const social = all.filter(
      (screen) =>
        screen.path.startsWith('popups/alliances/') ||
        screen.path.startsWith('popups/marketplace/') ||
        screen.path === 'PopupAlliancesCenterAsset.as',
    );
    assert.ok(social.length > 0, 'there are no social screens in the inventory');
    assert.ok(
      social.some((screen) => screen.decision === 'dropped'),
      'none of the social screens is visibly out of scope',
    );
    for (const screen of social) {
      assert.ok(
        ['dropped', 'planned'].includes(screen.decision),
        `${screen.path} is ${screen.decision}, not dropped or planned`,
      );
      if (screen.decision === 'dropped') {
        assert.ok(
          screen.decisionNote.startsWith('Dropped: '),
          `${screen.path} is dropped without a reason`,
        );
      }
    }
  });
});

describe('the screens the clone has modelled', () => {
  it('models the daily and Monday bonus screens from the server state', async () => {
    const all = await screens();
    const paths = [
      'GUI/MondayBonusButton.as',
      'popups/MondayBonusPopUp.as',
      'PopupNewDailyMC.as',
      'popups/PopupNewDaily.as',
    ];
    for (const path of paths) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not modelled`);
      assert.match(screen!.decisionNote, /`packages\/client\/src\/bonus\.ts`/);
    }
  });

  it('really does model the build menu', async () => {
    // The inventory claims the build window is implemented, so the model
    // has to exist and work.
    const items = [
      {
        type: 'b' as const,
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
      },
    ];
    assert.equal(buildMenu(items, 10).length, 1);
  });
});
