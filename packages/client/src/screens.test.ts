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
      implemented: 167,
      dropped: 52,
      planned: 41,
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

describe('the roster, team-thumbnail and unit-XP screen family decisions', () => {
  // These six deferrals said the behaviour had no rendered model. They are
  // reclassified only because the one dialog now really draws that behaviour
  // from the server's army, its accepted team and the rules' XP table. The
  // proprietary portraits stay excluded; only the behaviour is claimed.
  const ROSTER_SCREENS = [
    'PopupAllUnitsMC.as',
    'PopupGenericUnitSelectorMC.as',
    'popups/PopupGenericUnitSelector.as',
    'GUI/UnitXPLevelInfoDisplay.as',
    'popups/teamSelection/ThumbSelectedUnit.as',
    'popups/teamSelection/ThumbUnit.as',
  ];

  it('records each rendered screen as implemented against the roster panel', async () => {
    const all = await screens();
    for (const path of ROSTER_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/roster\.tsx`/);
      assert.match(screen!.decisionNote, /art|portrait|asset/i);
    }
  });

  it('leaves the all-units roster as already implemented against armyView', async () => {
    // This one was reclassified in G5.6: the result popup already draws the
    // army section. It is not flipped again — the new panel is a second
    // reading of the same model, not a new behaviour for this screen.
    const all = await screens();
    const screen = all.find((entry) => entry.path === 'popups/PopupAllUnits.as');
    assert.ok(screen);
    assert.equal(screen!.decision, 'implemented');
    assert.match(screen!.decisionNote, /`packages\/client\/src\/army\.ts`/);
  });

  it('leaves the assault portrait planned', async () => {
    // Its only remaining content is Zynga's portrait artwork: the clone
    // draws text rows and state, so flipping this would claim art it does
    // not render and model no new behaviour. PortraitTrainQueue is no
    // longer in this guard — the unitportraits panel now draws its states.
    const all = await screens();
    const path = 'GUI/PortraitAssault.as';
    const screen = all.find((entry) => entry.path === path);
    assert.ok(screen, `${path} is not in the inventory`);
    assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
    assert.match(screen!.decisionNote, /licensed|portraits/i);
  });
});

describe('the reusable UI-chrome screen family decisions', () => {
  // These deferrals said there was no selection state, popover, slider,
  // acknowledgement, request gesture, attachment lifecycle, cover or modal
  // ordering. All are now modelled and drawn by apps/client/src/ui/chrome.tsx
  // over the existing camera, dialog and request models — with the original
  // art deliberately excluded from every claim.
  const CHROME_SCREENS = [
    'ButtonTabAsset.as',
    'GUI/SubCategory.as',
    'GUI/Tab.as',
    'GUI/SpeakerBox.as',
    'GUI/ZoomSlider.as',
    'GUI/attachables/AttachableVisualElement.as',
    'IconCollect.as',
    'ButtonSpeedUpNoIconAsset.as',
    'ButtonSpeedUpWideAsset.as',
    'GuiCover.as',
    'PopOverMC.as',
    'TabMC.as',
    'popups/PopOver.as',
    'popups/PopupObject.as',
  ];

  it('records each modelled screen against the chrome panel', async () => {
    const all = await screens();
    for (const path of CHROME_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/chrome\.tsx`/);
    }
  });

  it('records the exploration cover as the shared primitive, not an exploration screen', async () => {
    // Both cover movieclips are art-only overlays with no methods beyond their
    // constructor. The reusable Cover draws the dimming + click-to-dismiss
    // behaviour for both; the claim stops at the behaviour, so the note must
    // exclude the exploration art and say there is no exploration view to host
    // it rather than pretending a screen was rendered.
    const all = await screens();
    const cover = all.find((entry) => entry.path === 'GuiCoverExplorationMC.as');
    assert.ok(cover, 'GuiCoverExplorationMC.as is not in the inventory');
    assert.equal(cover!.decision, 'implemented');
    assert.match(cover!.decisionNote, /`apps\/client\/src\/ui\/chrome\.tsx`/);
    assert.match(cover!.decisionNote, /dimming, click-to-dismiss/i);
    assert.match(cover!.decisionNote, /art stays excluded/i);
    assert.match(cover!.decisionNote, /no exploration view/i);
    assert.match(cover!.decisionNote, /primitive, not an exploration screen/i);
  });

  it('leaves the ones that need capture state or popup art planned', async () => {
    // The cover primitive now closes both cover deferrals, even though the
    // clone still has no exploration view to host the exploration one. A
    // capture icon has no server capture outcome to model; the info popup
    // movieclips still need their multiline popup art. The timed, repositioned
    // readout panel itself is implemented in detailpanels.tsx.
    const LEFT_PLANNED = [
      'IconoCapturadoMC.as',
      'InfoPopupMC.as',
      'InfoPopupManaMc.as',
      'TooltipMultilineMC.as',
    ];
    const all = await screens();
    for (const path of LEFT_PLANNED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
      assert.match(screen!.decisionNote, /^Deferred: /);
    }
  });
});

describe('the expansion and collections screen family decisions', () => {
  // These four deferrals said there was no rendered expansion result, no
  // buy-for prompt/messages, no client expansion model behind the popup, and
  // no collections catalogue. Each is reclassified only because a real panel
  // now draws that behaviour from the content and the server's own answers.
  const RECLASSIFIED: readonly { path: string; model: RegExp }[] = [
    {
      path: 'GUI/ItemButtonLargeExpand2.as',
      model: /`apps\/client\/src\/ui\/state\.ts`/,
    },
    {
      path: 'PopupExpandMC.as',
      model: /`apps\/client\/src\/ui\/expansion\.tsx`/,
    },
    {
      path: 'popups/PopupExpand.as',
      model: /`apps\/client\/src\/ui\/expansion\.tsx`/,
    },
    {
      path: 'popups/InventoryTabCollections.as',
      model: /`apps\/client\/src\/ui\/collections\.tsx`/,
    },
  ];

  it('records each rendered screen as implemented against its model', async () => {
    const all = await screens();
    for (const { path, model } of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, model);
    }
  });

  it('says the celebrated art and the share popup stay excluded', async () => {
    const all = await screens();
    const popup = all.find((entry) => entry.path === 'popups/PopupExpand.as');
    assert.ok(popup);
    assert.match(popup!.decisionNote, /art|Share!/i);
    const catalogue = all.find((entry) => entry.path === 'popups/InventoryTabCollections.as');
    assert.ok(catalogue);
    assert.match(catalogue!.decisionNote, /read-only|never claimed/i);
  });

  it('leaves the screens with no modelled behaviour planned', async () => {
    // The lost-item discovery share flow has no server outcome to read and no
    // behaviour the new panels draw. The drag-to-position cell is now a real
    // presentation in detailpanels.tsx, so it is no longer in this list.
    const LEFT_PLANNED = ['popups/PopUpLost.as'];
    const all = await screens();
    for (const path of LEFT_PLANNED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
      assert.match(screen!.decisionNote, /^Deferred: /);
    }
  });
});

describe('the character-setup, recovery and attack-tooltip screen family decisions', () => {
  // Three deferrals had real content behind them: the server owns
  // `deadHeroes` and the syringe count, the content owns the unit names and
  // costs, and the rules own the ten damage classes. They are reclassified
  // only because a real panel now draws those readings in the one dialog.
  const RECLASSIFIED = [
    'PopupHospitalMC.as',
    'popups/PopupHospital.as',
    'TooltipSimbolosAtaqueMC.as',
  ];

  it('records each rendered screen as implemented against the new panel', async () => {
    const all = await screens();
    for (const path of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/charactersetup\.tsx`/);
      assert.match(screen!.decisionNote, /art|proprietary/i);
    }
  });

  it('leaves the gender-choice popups planned with the precise gate', async () => {
    // `hasSex` is not in the new save and `set_sex_player.php` is not a
    // command or a new-server endpoint. A male/female panel would have no
    // server field to read and no request to send, so flipping either would
    // invent a client-only character rule rather than model the game.
    const LEFT_PLANNED = ['PopupChooseGenderMC.as', 'popups/PopupChooseGender.as'];
    const all = await screens();
    for (const path of LEFT_PLANNED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
      assert.match(screen!.decisionNote, /^Deferred: /);
      assert.match(screen!.decisionNote, /set_sex_player\.php/);
      assert.match(screen!.decisionNote, /no .*field|not a field/i);
    }
  });
});

describe('the inventory-cell and info-popup screen family decisions', () => {
  // Both deferrals said a behaviour was not modelled, not that art or a rule
  // was missing. Each is reclassified only because a real inline panel now
  // draws it from the server's store / the HUD's own popover model. Neither
  // owns an outcome: Place still sends a request and the popup invents no
  // readout.
  const RECLASSIFIED = [
    'GUI/InventoryItem.as',
    'GUI/InfoPopup.as',
  ];

  it('records each rendered screen as implemented against the detail panel', async () => {
    const all = await screens();
    for (const path of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/detailpanels\.tsx`/);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('records the research-centre shell and popup as implemented against the panel', async () => {
    // The old note called this the magic tech tree and said the server applied
    // none of the research commands. The pure rules and the panel now draw the
    // AREA 51 / ROBOTIC CENTER behaviour from the server's own save, so both
    // the shell and its popup are implemented; the animation art stays out.
    const all = await screens();
    for (const path of ['PopupResearchCenterMC.as', 'popups/PopupResearchCenter.as']) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/fusion\.tsx`/);
      assert.match(screen!.decisionNote, /timestamp|server/i);
      assert.match(screen!.decisionNote, /art|SWF/i);
    }
  });
});

describe('the Atom Fusion screen family decisions', () => {
  // The popup's behaviour is now genuinely modelled: the content supplies the
  // breeding_order candidates and names, the pure rules supply the power-up
  // table, and the server's save supplies the two inputs, the rolled power and
  // the granted item. The art-only movieclip and the already-reclassified
  // help/turbina screens are asserted separately rather than flipped again.
  const RECLASSIFIED = ['popups/PopupSoulMixer.as'];

  it('records the fusion popup as implemented against the panel', async () => {
    const all = await screens();
    for (const path of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/fusion\.tsx`/);
      assert.match(screen!.decisionNote, /server/i);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('leaves the art-only shell planned with a corrected note', async () => {
    // `PopupBreedingMC.as` is the movieclip shell PopupSoulMixer extends. It
    // has no literals, state or gestures of its own, so flipping it would
    // claim the Zynga artwork rather than a modelled behaviour.
    const all = await screens();
    const shell = all.find((entry) => entry.path === 'PopupBreedingMC.as');
    assert.ok(shell);
    assert.equal(shell!.decision, 'planned', 'the art-only shell should stay planned');
    assert.match(shell!.decisionNote, /^Deferred: /);
    assert.match(shell!.decisionNote, /art-only|artwork/i);
    assert.match(shell!.decisionNote, /no separate breeding/i);
  });

  it('does not re-classify the already implemented help and turbine screens', async () => {
    // Those three were flipped in the earlier help/turbina increment; the new
    // fusion panel draws a different screen and must not change their state.
    const all = await screens();
    for (const path of [
      'PopupSoulMixerHelpMC.as',
      'popups/PopupSoulMixerHelp.as',
      'popups/SoulMixer/SoulMixerTurbina.as',
    ]) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} should stay implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/soulmixerhelp\.tsx`/);
    }
  });
});

describe('the mystery-box screen family decisions', () => {
  // These four deferrals said the boxes' rules were not modelled. They are
  // reclassified only because the one dialog now really draws both screens:
  // pack 4's four candidates and a super pack's three rarity rows and tiers
  // come from the content, the literals are the client's own, and the result
  // is read from the store the server granted into — never rolled locally.
  const RECLASSIFIED = [
    'PopupMisteryMC.as',
    'popups/PopupMistery.as',
    'PopupSuperMisteryBoxMC.as',
    'popups/PopupSuperMistery.as',
  ];

  it('records each rendered screen as implemented against the box panel', async () => {
    const all = await screens();
    for (const path of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/mystery\.tsx`/);
      assert.match(screen!.decisionNote, /server|store/i);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('leaves the unrelated screens with no modelled behaviour planned', async () => {
    // Flipping a deferral must not become a general amnesty: these remain
    // planned because no authoritative answer or modelled gesture exists.
    // The research-centre shell is no longer here — its panel is implemented.
    const LEFT_PLANNED = ['popups/PopUpLost.as', 'PopupBreedingMC.as'];
    const all = await screens();
    for (const path of LEFT_PLANNED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
      assert.match(screen!.decisionNote, /^Deferred: /);
    }
  });
});

describe('the soul-mixer help and turbine screen decisions', () => {
  // Only the presentation is drawn here: the four help steps are the recovered
  // literal, and the turbine reads server-owned state when present (otherwise
  // a labelled placeholder). The separate fusion panel now draws the fusion
  // itself from server state; the art-only breeding shell stays planned.
  const RECLASSIFIED = [
    'PopupSoulMixerHelpMC.as',
    'popups/PopupSoulMixerHelp.as',
    'popups/SoulMixer/SoulMixerTurbina.as',
  ];

  it('records the rendered help and turbine screens as implemented', async () => {
    const all = await screens();
    for (const path of RECLASSIFIED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/soulmixerhelp\.tsx`/);
    }
    const help = all.find((entry) => entry.path === 'popups/PopupSoulMixerHelp.as');
    assert.match(help!.decisionNote, /verbatim/);
    assert.match(help!.decisionNote, /fusion rule/);
    const turbine = all.find(
      (entry) => entry.path === 'popups/SoulMixer/SoulMixerTurbina.as',
    );
    assert.match(turbine!.decisionNote, /placeholder|countdown/i);
    assert.match(turbine!.decisionNote, /server/);
  });

  it('leaves the art-only breeding shell planned', async () => {
    // Reclassifying the help copy must not imply the art shell is drawn. The
    // fusion popup itself now has a real panel and is asserted in its own
    // family block above; only the movieclip with no behaviour stays planned.
    const LEFT_PLANNED = ['PopupBreedingMC.as'];
    const all = await screens();
    for (const path of LEFT_PLANNED) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'planned', `${path} should stay planned`);
      assert.match(screen!.decisionNote, /^Deferred: /);
    }
  });
});

describe('the player-owned resource market screen family decisions', () => {
  // Only the two class-A screens are reclassified. `ButtonMarketMC.as` has no
  // behaviour of its own: its gesture is now drawn in the chrome and its panel
  // is hosted by the one dialog. `popups/ButtonMarket.as` has the buy/sell
  // refresh and the 24-hour sentence, now drawn from the server's counters and
  // wallet with the exhaustion caption kept display-only. The ADR 20 auction
  // screens and every art-only shell are untouched.
  const MARKET_SCREENS = ['ButtonMarketMC.as', 'popups/ButtonMarket.as'];

  it('records each rendered screen as implemented against the market panel', async () => {
    const all = await screens();
    for (const path of MARKET_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/market\.tsx`/);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('says the exhaustion text is display-only and the request is authoritative', async () => {
    const all = await screens();
    const button = all.find((entry) => entry.path === 'popups/ButtonMarket.as');
    assert.ok(button);
    assert.match(button!.decisionNote, /display only/i);
    assert.match(button!.decisionNote, /server/i);
    assert.match(button!.decisionNote, /trade_resource/);
  });

  it('leaves the ADR 20 marketplaces and the art-only market shells alone', async () => {
    const all = await screens();
    for (const path of [
      'PopupMarketMC.as',
      'PopupMarketplaceAsset.as',
      'popups/marketplace/PopupMarketplace.as',
    ]) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.notEqual(screen!.decision, 'implemented', `${path} was reclassified`);
    }
  });
});

describe('the store item-button screen family decisions', () => {
  // These three deferrals had no rendered store front. They are reclassified
  // only because a real panel now draws the item-button chrome from the
  // content's offer packs and the server's cash, with original art only. The
  // purchase gesture is the catalogue's buy_offer_pack; no limit warning is
  // drawn because the store has no server-owned limit to read.
  const STORE_SCREENS = [
    'StoreMC.as',
    'GUI/ItemButtonLarge.as',
    'GUI/ItemButtonLargeResources.as',
  ];

  it('records each rendered screen as implemented against the store-item front', async () => {
    const all = await screens();
    for (const path of STORE_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/storeitems\.tsx`/);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('says the only purchase gesture is buy_offer_pack and no limit is claimed', async () => {
    const all = await screens();
    const large = all.find((entry) => entry.path === 'GUI/ItemButtonLarge.as');
    assert.ok(large);
    assert.match(large!.decisionNote, /buy_offer_pack/);
    assert.match(large!.decisionNote, /server-owned limit/i);
    const resources = all.find((entry) => entry.path === 'GUI/ItemButtonLargeResources.as');
    assert.ok(resources);
    assert.match(resources!.decisionNote, /server's cash/i);
  });

  it('leaves the ADR 20 marketplaces and the art-only shells alone', async () => {
    const all = await screens();
    for (const path of [
      'PopupMarketMC.as',
      'PopupMarketplaceAsset.as',
      'popups/marketplace/PopupMarketplace.as',
    ]) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.notEqual(screen!.decision, 'implemented', `${path} was reclassified`);
    }
  });
});

describe('the unit-portrait screen family decisions', () => {
  // These three deferrals said no GUI panel drew the portrait states. They
  // are reclassified only because unitportraits.tsx really draws them from
  // the server's TrainingView and its owned-unit rows, with original SVG
  // geometry. No proprietary art is claimed and no roll, grant or command
  // is moved into the client. No other portrait screen is touched here.
  const PORTRAIT_SCREENS = [
    'GUI/Portrait.as',
    'GUI/PortraitTrainQueue.as',
    'GUI/AnimatedUnit.as',
  ];

  it('records each drawn portrait as implemented against the portrait panel', async () => {
    const all = await screens();
    for (const path of PORTRAIT_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/unitportraits\.tsx`/);
    }
  });

  it('says the state is server-owned and no art or roll is claimed', async () => {
    const all = await screens();
    for (const path of PORTRAIT_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.match(screen!.decisionNote, /server/i);
      assert.match(screen!.decisionNote, /art/i);
      assert.match(screen!.decisionNote, /roll/i);
      assert.match(screen!.decisionNote, /command/i);
    }
  });
});

describe('the resource-button and icon-chrome screen family decisions', () => {
  // All five deferrals said a shortcut/tab/icon had no rendered equivalent.
  // They are reclassified only because a real panel now draws that
  // presentation with original inline SVG. The readout stays the server's and
  // the only gesture is the catalogue's trade_resource: no behaviour is added,
  // and no proprietary art or ADR 20 screen is claimed.
  const RESOURCE_BUTTON_SCREENS = [
    'ButtonResourceMC.as',
    'ButtonSmallLargeTextWithIconResourcesMC.as',
    'ButtonSmallWithIconResourcesMC.as',
    'IconResourcesMC.as',
    'GUI/ResourcesTab.as',
  ];

  it('records each rendered screen as implemented against the chrome panel', async () => {
    const all = await screens();
    for (const path of RESOURCE_BUTTON_SCREENS) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.equal(screen!.decision, 'implemented', `${path} is not implemented`);
      assert.match(screen!.decisionNote, /`apps\/client\/src\/ui\/resourcebuttons\.tsx`/);
      assert.match(screen!.decisionNote, /art/i);
    }
  });

  it('says the server keeps the values and the pricing', async () => {
    const all = await screens();
    for (const path of RESOURCE_BUTTON_SCREENS) {
      const screen = all.find((entry) => entry.path === path)!;
      assert.match(screen.decisionNote, /server/i);
      assert.match(screen.decisionNote, /trade_resource/);
      assert.match(screen.decisionNote, /no client-side|never a client|prices/i);
    }
  });

  it('leaves the art-only and ADR 20 screens alone', async () => {
    const all = await screens();
    for (const path of [
      'PopupMarketMC.as',
      'PopupMarketplaceAsset.as',
      'popups/marketplace/PopupMarketplace.as',
    ]) {
      const screen = all.find((entry) => entry.path === path);
      assert.ok(screen, `${path} is not in the inventory`);
      assert.notEqual(screen!.decision, 'implemented', `${path} was reclassified`);
    }
  });
});
