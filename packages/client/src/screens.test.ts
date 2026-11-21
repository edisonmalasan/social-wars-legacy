import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { buildMenu } from './buildmenu.ts';
import {
  assaultCountdown,
  assaultHistory,
  battleOptions,
  lastAssaultResult,
  specialAttackHud,
} from './featurestate.ts';
import type { WorldSnapshot } from './session.ts';

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
      implemented: 114,
      dropped: 52,
      planned: 94,
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

  it('models the mission countdown from the server timer', async () => {
    const all = await screens();
    const timer = all.find((entry) => entry.path === 'GUI/CountdownTimer.as');
    assert.ok(timer);
    assert.equal(timer!.decision, 'implemented');
    assert.match(timer!.decisionNote, /`packages\/client\/src\/questview\.ts`/);
  });

  it('models the offer-pack store screens from the content and wallet', async () => {
    const all = await screens();
    const paths = [
      'PopupGetPackMC.as',
      'PopupGotPackMC.as',
      'popups/PopupGetPack.as',
      'popups/PopupGotPack.as',
    ];
    for (const path of paths) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not modelled`);
      assert.match(screen!.decisionNote, /`packages\/client\/src\/store\.ts`/);
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

/**
 * A save with the fields every world has. Assault selectors must read only
 * the server's own keys: a world with none of them is an older save, not a
 * source of invented outcomes, loot, history, charges or countdowns.
 */
function world(privateState: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState,
  } as unknown as WorldSnapshot;
}

describe('the assault result receipt', () => {
  it('reads the server-owned win flag without inventing loot', () => {
    const view = lastAssaultResult(world({ lastAssaultWon: true }))!;
    assert.equal(view.won, true);
    assert.equal(view.settled, false);
    assert.deepEqual(view.loot, []);
    assert.equal(view.unitsAlive, null);
    assert.equal(view.unitsDead, null);
    assert.equal(view.opponent, null);
    assert.equal(view.recordedAt, null);
  });

  it('reads the exact loot rows and army counts the server persisted', () => {
    const view = lastAssaultResult(world({
      lastAssaultWon: true,
      lastAssaultResult: {
        won: true,
        rewards: [{ resource: 'gold', amount: 1200 }, { resource: 'xp', amount: 60 }],
        unitsAlive: 14,
        unitsDead: 3,
        opponent: 'village-9',
        recordedAt: 1_700_000_000,
      },
    }))!;
    assert.equal(view.won, true);
    assert.equal(view.settled, true);
    assert.deepEqual(view.loot, [
      { resource: 'gold', amount: 1200 },
      { resource: 'xp', amount: 60 },
    ]);
    assert.equal(view.unitsAlive, 14);
    assert.equal(view.unitsDead, 3);
    assert.equal(view.opponent, 'village-9');
    assert.equal(view.recordedAt, 1_700_000_000);
  });

  it('ignores malformed rows rather than paying a resource the server did not', () => {
    const view = lastAssaultResult(world({
      lastAssaultWon: false,
      lastAssaultResult: {
        won: false,
        rewards: [
          { resource: 'gold', amount: 10 },
          { resource: 'not-a-resource', amount: 50 },
          { resource: 'xp', amount: 'sixty' },
          null,
        ],
        unitsAlive: Number.NaN,
        unitsDead: -1,
        opponent: 42,
        recordedAt: 'later',
      },
    }))!;
    assert.equal(view.won, false);
    assert.deepEqual(view.loot, [{ resource: 'gold', amount: 10 }]);
    assert.equal(view.unitsAlive, null);
    assert.equal(view.unitsDead, -1);
    assert.equal(view.opponent, null);
    assert.equal(view.recordedAt, null);
  });

  it('is null when the server has answered no assault at all', () => {
    assert.equal(lastAssaultResult(world()), null);
  });
});

describe('the assault battle history', () => {
  it('reads the sent and received lists the server actually answered', () => {
    const view = assaultHistory(world({
      attacksSent: [
        { opponent: 'village-9', won: true, gold: 1200, at: 1_700_000_000 },
        { opponent: 'village-3', won: false, gold: 0, at: 1_699_990_000 },
      ],
      attacksReceived: [{ opponent: 'village-7', won: false, gold: 30, at: 1_699_980_000 }],
      tsAttacksReset: 1_700_360_000,
    }))!;
    assert.equal(view.sent.length, 2);
    assert.deepEqual(view.sent[0], {
      opponent: 'village-9', won: true, gold: 1200, at: 1_700_000_000,
    });
    assert.equal(view.received.length, 1);
    assert.equal(view.received[0]!.opponent, 'village-7');
    assert.equal(view.resetAt, 1_700_360_000);
  });

  it('skips malformed rows instead of inventing a battle', () => {
    const view = assaultHistory(world({
      attacksSent: [null, 'battle', {}, { opponent: 7, won: 'yes', gold: [], at: 'now' }],
    }))!;
    assert.deepEqual(view.sent, []);
    assert.equal(view.received.length, 0);
    assert.equal(view.resetAt, null);
  });

  it('is null when the save has no history keys', () => {
    assert.equal(assaultHistory(world()), null);
  });
});

describe('the assault countdown', () => {
  it('counts down from the server reset timestamp', () => {
    assert.deepEqual(assaultCountdown(world({ tsAttacksReset: 1_700_010_000 }), 1_700_000_000), {
      endsAt: 1_700_010_000,
      secondsRemaining: 10_000,
    });
  });

  it('never shows a negative countdown', () => {
    const view = assaultCountdown(world({ tsAttacksReset: 1_700_000_000 }), 1_700_000_001)!;
    assert.equal(view.secondsRemaining, 0);
  });

  it('is null when the server published no reset timestamp', () => {
    assert.equal(assaultCountdown(world(), 0), null);
    assert.equal(assaultCountdown(world({ tsAttacksReset: 'soon' }), 0), null);
  });
});

describe('the defensive battle options', () => {
  it('reads the strategy the server owns', () => {
    assert.deepEqual(battleOptions(world({ strategy: 3 })), { selected: 3 });
  });

  it('is null when the server published no usable strategy', () => {
    for (const raw of [undefined, 0, 5, 'defensive', Number.NaN]) {
      assert.equal(battleOptions(world({ strategy: raw })), null, String(raw));
    }
  });
});

describe('the special-attack charge HUD', () => {
  it('lists only the classes the server publishes, with the rules shape', () => {
    const view = specialAttackHud(world({
      specialAttackCharges: {
        ChargeAttack: { ready: true, charge: 1 },
        VortexSpecialAttack: { ready: false, charge: 0.25, limit: true },
      },
    }));
    assert.deepEqual(view, [
      { id: 'ChargeAttack', shape: 'movement', ready: true, charge: 1, limit: false },
      { id: 'VortexSpecialAttack', shape: 'pulse', ready: false, charge: 0.25, limit: true },
    ]);
  });

  it('ignores unknown classes and never invents a charge', () => {
    const view = specialAttackHud(world({
      specialAttackCharges: {
        MadeUpAttack: { ready: true, charge: 1 },
        MeleeSpecialAttack: { ready: 'yes', charge: Number.NaN },
      },
    }));
    assert.deepEqual(view, [
      { id: 'MeleeSpecialAttack', shape: 'single', ready: null, charge: null, limit: false },
    ]);
  });

  it('is empty when the server publishes no charge state', () => {
    assert.deepEqual(specialAttackHud(world()), []);
  });
});

describe('the assault screen family decisions', () => {
  const ASSAULT_SCREENS = [
    'PopupAssaultHistoryMC.as',
    'popups/PopupAssaultHistory.as',
    'PopupAttackFinishedMC.as',
    'popups/PopupAttackFinished.as',
    'GUI/AssaultCountdown.as',
    'GUI/PortraitSpecialAttack.as',
    'GUI/PortraitSpecialAttackLimit.as',
    'popups/PopUpBattleOptions.as',
  ];

  it('records each screen as implemented against a model that exists', async () => {
    const all = await screens();
    for (const path of ASSAULT_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`packages\/client\/src\/featurestate\.ts`/);
    }
  });

  it('records the army roster behind the result screen against its model', async () => {
    const all = await screens();
    const roster = all.find((entry) => entry.path === 'popups/PopupAllUnits.as');
    assert.ok(roster);
    assert.equal(roster!.decision, 'implemented');
    assert.match(roster!.decisionNote, /`packages\/client\/src\/army\.ts`/);
  });
});

describe('the onboarding screen family decisions', () => {
  // These six deferrals said the behaviour was already modelled but not
  // rendered. They are reclassified only because a real panel now draws it.
  const ONBOARDING_SCREENS = [
    'PopupIntroMC.as',
    'PopupHelpIslandMC.as',
    'PopupMissionInfoMC.as',
    'popups/PopupNextMission.as',
    'PopupConfirmMC.as',
    'popups/PopupConfirm.as',
  ];

  it('records each rendered screen as implemented against its panel', async () => {
    const all = await screens();
    for (const path of ONBOARDING_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/onboarding\.tsx`/);
    }
  });

  it('leaves the purely cosmetic quest-loading animation planned', async () => {
    // There is no behaviour to model here: the briefing already hands over
    // to the server-owned combat panel, and the original's only extra is a
    // full-screen loading animation behind Zynga's art licence. Flipping it
    // would grow the count without modelling anything.
    const all = await screens();
    const loading = all.find((entry) => entry.path === 'popups/PopupLoadingQuest.as');
    assert.ok(loading);
    assert.equal(loading!.decision, 'planned');
    assert.match(loading!.decisionNote, /^Deferred: .*cosmetic/);
  });
});
