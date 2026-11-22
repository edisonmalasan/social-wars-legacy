import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';
import {
  RESEARCH_STEP_SECONDS,
  RESEARCH_TOTAL_STEPS,
  SOUL_MIXER_POWERUPS,
} from '@swl/rules';

import {
  ATOM_FUSION_NO_INPUTS,
  ATOM_FUSION_NO_POWER,
  ATOM_FUSION_NO_RESULT,
  RESEARCH_NO_TIMESTAMP,
  atomFusionPanel,
  formatResearchTime,
  fusionDialog,
  researchPanel,
} from './state.ts';

/** The content ids the two research tracks name, in the rules' order. */
const AREA_51_IDS = [1048, 1096, 1097, 1099, 1098, 1100];
const ROBOTIC_IDS = [1062, 1101, 1075, 1141, 1085, 1105];

function item(id: number, name: string, breedingOrder?: number): ContentItem {
  return {
    id,
    name,
    type: 'u',
    extra: breedingOrder === undefined ? {} : { breeding_order: String(breedingOrder) },
  } as unknown as ContentItem;
}

function bundle(): ContentBundle {
  return {
    items: [
      item(1002, 'Red Tank', 7),
      item(1003, 'Tank II', 18),
      item(1007, 'Soldier', 2),
      item(1050, 'Fusion Result', 240),
      item(1226, 'Red Metallic Dragon', 60),
      ...AREA_51_IDS.map((id, index) => item(id, `Area unit ${index}`)),
      ...ROBOTIC_IDS.map((id, index) => item(id, `Robot unit ${index}`)),
    ],
  } as unknown as ContentBundle;
}

function world(privateState: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState,
  } as unknown as WorldSnapshot;
}

const NOW = 1_700_000_000;

describe('the Atom Fusion panel', () => {
  it('draws the content candidates and the rules prices from a fresh, empty save', () => {
    const view = atomFusionPanel(bundle(), world());
    assert.equal(view.title, 'ATOM FUSION');
    assert.deepEqual(
      view.candidates.map((candidate) => [candidate.itemId, candidate.power]),
      [[1007, 2], [1002, 7], [1003, 18], [1226, 60], [1050, 240]],
    );
    assert.equal(view.candidates[0]!.name, 'Soldier');
    assert.deepEqual(view.inputs, []);
    assert.equal(view.powerPreview, null);
    assert.equal(view.result, null);
    assert.equal(view.speedup, null);
    assert.equal(view.gateMessage, null);
    assert.equal(view.powerupRows.length, SOUL_MIXER_POWERUPS.length);
    assert.deepEqual(
      view.powerupRows.map((row) => row.cashCost),
      SOUL_MIXER_POWERUPS.map((row) => row.cash_cost),
    );
    assert.deepEqual(
      view.powerupRows.map((row) => row.orderIncrement),
      SOUL_MIXER_POWERUPS.map((row) => row.order_increment),
    );
    assert.deepEqual(view.powerupRows[2]!.command, {
      map: 0,
      name: 'buy_powerups',
      args: [2],
    });
  });

  it('copies only the units, power and grant the server actually published', () => {
    const view = atomFusionPanel(
      bundle(),
      world({
        soulMixer: {
          inputA: 1007,
          inputB: 1003,
          powerUpLevel: 2,
          resultPower: 240,
          resultItemId: 1050,
          isoId: 42,
        },
      }),
    );
    assert.deepEqual(view.inputs, [
      { itemId: 1007, name: 'Soldier', power: 2 },
      { itemId: 1003, name: 'Tank II', power: 18 },
    ]);
    assert.equal(view.powerPreview, 240);
    assert.deepEqual(view.result, { itemId: 1050, name: 'Fusion Result', power: 240 });
    assert.deepEqual(view.speedup, { map: 0, name: 'soulmixer_speedup', args: [42] });
    assert.equal(view.powerupRows[2]!.current, true);
    assert.equal(ATOM_FUSION_NO_INPUTS.length > 0, true);
    assert.equal(ATOM_FUSION_NO_POWER.length > 0, true);
    assert.equal(ATOM_FUSION_NO_RESULT.length > 0, true);
  });

  it('never rolls a power or invents a grant from a training timestamp', () => {
    const view = atomFusionPanel(
      bundle(),
      world({ atom_fusion: [, , , , , , { ts: NOW }], soulMixer: { inputA: 1007, inputB: 1003 } }),
    );
    assert.equal(view.powerPreview, null);
    assert.equal(view.result, null);
    assert.equal(view.speedup, null);
  });

  it('reads the level-20 refusal from the pure gate, not from the client', () => {
    const inputs = { inputA: 1226, inputB: 1007 };
    const at = (level: number): WorldSnapshot => {
      const w = world({ soulMixer: inputs });
      (w.maps[0] as { level?: number }).level = level;
      return w;
    };
    assert.match(atomFusionPanel(bundle(), at(19)).gateMessage ?? '', /Spartan Mech or Red Metallic Dragon/);
    assert.equal(atomFusionPanel(bundle(), at(20)).gateMessage, null);
  });

  it('treats malformed server fields as absent', () => {
    for (const raw of [42, 'mixing', [], { inputA: 'soon', resultPower: NaN, resultItemId: -1 }]) {
      const view = atomFusionPanel(bundle(), world({ soulMixer: raw }));
      assert.deepEqual(view.inputs, []);
      assert.equal(view.powerPreview, null);
      assert.equal(view.result, null);
    }
  });

  it('renders no result, power or speedup from tampered/absent server values', () => {
    const view = atomFusionPanel(
      bundle(),
      world({ soulMixer: { resultItemId: '999999', resultPower: 'soon', isoId: -1 } }),
    );
    assert.equal(view.powerPreview, null);
    assert.equal(view.result, null);
    assert.equal(view.speedup, null);
    assert.deepEqual(view.inputs, []);
  });
});

describe('the research-centre panel', () => {
  it('draws the rules track and the client literals with no server state', () => {
    const view = researchPanel(bundle(), world(), 0, NOW);
    assert.equal(view.title, 'AREA 51');
    assert.equal(view.totalSteps, RESEARCH_TOTAL_STEPS);
    assert.equal(view.stepSeconds, RESEARCH_STEP_SECONDS);
    assert.equal(view.step, null);
    assert.equal(view.item, null);
    assert.equal(view.countdown, null);
    assert.equal(view.friendHelp, null);
    assert.deepEqual(view.track.map((entry) => entry.id), AREA_51_IDS);
    assert.deepEqual(view.researchCommand, {
      map: 0,
      name: 'next_research_step',
      args: [0, true],
    });
    assert.equal(view.speedupCommand, null);
    assert.equal(view.collectCommand, null);
    assert.match(view.hint, /every 6 hours/);
    assert.match(RESEARCH_NO_TIMESTAMP, /server/);
  });

  it('counts down only from the timestamp the server published', () => {
    const view = researchPanel(
      bundle(),
      world({
        researchItemNumber: [2, 1],
        researchStepNumber: [4, 10],
        timeStampDoResearch: [0, NOW - 7200],
      }),
      1,
      NOW,
    );
    assert.equal(view.step, 10);
    assert.deepEqual(view.item, { id: ROBOTIC_IDS[1], name: 'Robot unit 1', cash: 3 });
    assert.equal(view.countdown?.secondsRemaining, RESEARCH_STEP_SECONDS - 7200);
    assert.equal(view.countdown?.label, '4:00:00');
    assert.equal(view.countdown?.due, false);
    assert.deepEqual(view.collectCommand, { map: 0, name: 'next_research_item', args: [1] });
    assert.deepEqual(view.speedupCommand, { map: 0, name: 'research_buy_step_cash', args: [3, 1] });

    const area51 = researchPanel(
      bundle(),
      world({ researchItemNumber: [2, 1], timeStampDoResearch: [0, NOW - 7200] }),
      0,
      NOW,
    );
    // A zero timestamp is no countdown at all, never a full six-hour guess.
    assert.equal(area51.countdown, null);
    assert.equal(area51.collectCommand, null);
  });

  it('never shows a negative wait and offers Get only on the tenth step', () => {
    const view = researchPanel(
      bundle(),
      world({ researchStepNumber: [9], timeStampDoResearch: [NOW + 500] }),
      0,
      NOW,
    );
    assert.equal(view.countdown?.secondsRemaining, RESEARCH_STEP_SECONDS);
    assert.equal(view.collectCommand, null);
    assert.deepEqual(view.researchCommand, {
      map: 0,
      name: 'next_research_step',
      args: [0, true],
    });
    assert.equal(formatResearchTime(RESEARCH_STEP_SECONDS), '6:00:00');
  });

  it('reads the friend-help prompt and its gesture from the server list', () => {
    const view = researchPanel(
      bundle(),
      world({ roboticSocialHelp: ['friend-a', 'friend-b', ''] }),
      1,
      NOW,
    );
    assert.ok(view.friendHelp);
    assert.deepEqual(view.friendHelp!.friends, ['friend-a', 'friend-b']);
    assert.deepEqual(view.friendHelp!.command, {
      map: 0,
      name: 'finish_robotic_help',
      args: [JSON.stringify(['friend-a', 'friend-b'])],
    });
    assert.match(view.friendHelp!.hint, /2 steps/);
    // Area 51 has no social-help track, even with the same save field.
    const area51 = researchPanel(
      bundle(),
      world({ roboticSocialHelp: ['friend-a'] }),
      0,
      NOW,
    );
    assert.equal(area51.friendHelp, null);
  });

  it('reads malformed save arrays as absent instead of fabricating a state', () => {
    for (const raw of [undefined, 'soon', {}, [NaN, -1]]) {
      const view = researchPanel(
        bundle(),
        world({
          researchItemNumber: raw,
          researchStepNumber: raw,
          timeStampDoResearch: raw,
        }),
        0,
        NOW,
      );
      assert.equal(view.step, null);
      assert.equal(view.item, null);
      assert.equal(view.countdown, null);
    }
  });

  it('reads the server-owned researchState record by type', () => {
    const view = researchPanel(
      bundle(),
      world({
        researchState: {
          itemNumber: [2, 1],
          stepNumber: [4, 10],
          timestamp: [0, NOW - 7200],
          roboticSocialHelp: ['friend-a', 'friend-b'],
        },
      }),
      1,
      NOW,
    );
    assert.equal(view.step, 10);
    assert.deepEqual(view.item, { id: ROBOTIC_IDS[1], name: 'Robot unit 1', cash: 3 });
    assert.equal(view.countdown?.secondsRemaining, RESEARCH_STEP_SECONDS - 7200);
    assert.equal(view.countdown?.label, '4:00:00');
    assert.deepEqual(view.friendHelp!.friends, ['friend-a', 'friend-b']);
    assert.deepEqual(view.collectCommand, { map: 0, name: 'next_research_item', args: [1] });

    const area51 = researchPanel(
      bundle(),
      world({ researchState: { itemNumber: [2, 1], stepNumber: [4, 10], timestamp: [NOW - 7200, 0] } }),
      0,
      NOW,
    );
    assert.equal(area51.step, 4);
    assert.equal(area51.countdown?.secondsRemaining, RESEARCH_STEP_SECONDS - 7200);
    assert.equal(area51.friendHelp, null);
  });

  it('prefers the server-owned record over the legacy typed fields', () => {
    const view = researchPanel(
      bundle(),
      world({
        researchState: {
          itemNumber: [0, 1],
          stepNumber: [0, 7],
          timestamp: [0, 0],
          roboticSocialHelp: [],
        },
        researchItemNumber: [5, 5],
        researchStepNumber: [9, 9],
        timeStampDoResearch: [NOW, NOW],
        roboticSocialHelp: ['legacy'],
      }),
      1,
      NOW,
    );
    assert.equal(view.step, 7);
    assert.deepEqual(view.item, { id: ROBOTIC_IDS[1], name: 'Robot unit 1', cash: 3 });
    assert.equal(view.countdown, null);
    assert.equal(view.friendHelp, null);
  });

  it('falls back to the legacy fields when the server record is malformed', () => {
    for (const raw of ['soon', 42, []]) {
      const view = researchPanel(
        bundle(),
        world({
          researchState: raw,
          researchItemNumber: [2, 1],
          researchStepNumber: [4, 10],
          timeStampDoResearch: [0, NOW - 7200],
          roboticSocialHelp: ['friend-a'],
        }),
        1,
        NOW,
      );
      assert.equal(view.step, 10);
      assert.equal(view.countdown?.secondsRemaining, RESEARCH_STEP_SECONDS - 7200);
      assert.deepEqual(view.friendHelp!.friends, ['friend-a']);
    }
  });

  it('renders tampered or absent server values as empty', () => {
    const view = researchPanel(
      bundle(),
      world({
        researchState: {
          itemNumber: ['x', NaN],
          stepNumber: [null, -1],
          timestamp: [undefined, 'later'],
          roboticSocialHelp: 42,
        },
      }),
      1,
      NOW,
    );
    assert.equal(view.step, null);
    assert.equal(view.item, null);
    assert.equal(view.countdown, null);
    assert.equal(view.friendHelp, null);
    assert.equal(view.speedupCommand, null);
    assert.equal(view.collectCommand, null);
  });
});

describe('the three panels share the one dialog', () => {
  it('gives each panel a distinct id in the same single slot', () => {
    const ids = [
      fusionDialog('atom').id,
      fusionDialog(0).id,
      fusionDialog(1).id,
    ];
    assert.deepEqual(ids, ['fusion-atom', 'research-area51', 'research-robotic']);
    assert.equal(new Set(ids).size, 3);
    for (const kind of ['atom', 0, 1] as const) {
      const panel = fusionDialog(kind);
      assert.equal(panel.kind, 'alert');
      assert.ok(panel.title.length > 0);
    }
  });
});
