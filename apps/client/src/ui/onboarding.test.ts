import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { CommandOutcome } from '@swl/protocol';
import {
  CLOSED_DIALOG,
  openDialog,
  questResultView,
  type QuestChoice,
  type TutorialStep,
  type WorldSnapshot,
} from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';
import { QUEST_IDS, getQuestSpec } from '@swl/rules';

import {
  CONFIRM_NO,
  CONFIRM_YES,
  confirmPanel,
  missionInfoPanel,
  nextMissionPanel,
  onboardingDialog,
  tutorialHelpView,
} from './state.ts';

/** A story quest id the clone's tests already use. */
const Q02 = '100000002';

function step(overrides: Partial<TutorialStep>): TutorialStep {
  return { step: 100, gate: null, ...overrides };
}

function world(): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {}, store: { 7: 3 } }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

function bundle(): ContentBundle {
  return {
    items: [
      {
        id: 7,
        name: 'Marine',
        type: 'u',
        group_type: 'infantry',
        training_time: 5,
      } as ContentItem,
    ],
    levels: [],
    globals: {},
    categories: {},
    questEvents: {},
  } as unknown as ContentBundle;
}

function choice(overrides: Partial<QuestChoice> = {}): QuestChoice {
  return {
    index: 1,
    questId: Q02,
    title: 'BLOW THE POWER PLANT',
    rank: 0,
    levelUnlock: 1,
    locked: false,
    unlocked: true,
    active: false,
    ...overrides,
  };
}

describe('the intro and help panel', () => {
  it('draws the client\'s own step literals, in the tutorial\'s own order', () => {
    const steps = [
      step({
        step: 100,
        title: 'Language.getLiteral("WELCOME, SOLDIER!")',
        lesson: 'Language.getLiteral("Welcome Soldier!\\nYou\\\'ve been appointed!")',
        skippable: true,
      }),
      step({
        step: 101,
        title: 'Language.getLiteral("COMMAND CENTER")',
        lesson: 'Language.getLiteral("Click on the command center.")',
      }),
    ];
    const view = tutorialHelpView(steps, steps[1]!);
    assert.equal(view.total, 2);
    assert.equal(view.currentPosition, 2);
    assert.deepEqual(
      view.steps.map((entry) => [entry.step, entry.position, entry.title, entry.current]),
      [
        [100, 1, 'WELCOME, SOLDIER!', false],
        [101, 2, 'COMMAND CENTER', true],
      ],
    );
    assert.equal(view.steps[0]!.lesson, "Welcome Soldier!\nYou've been appointed!");
    assert.equal(view.steps[0]!.skippable, true);
    assert.equal(view.steps[1]!.skippable, false);
  });

  it('is empty, and has no current position, when the client has no steps', () => {
    const view = tutorialHelpView([], null);
    assert.equal(view.total, 0);
    assert.equal(view.currentPosition, 0);
    assert.deepEqual(view.steps, []);
  });
});

describe('the mission-info panel', () => {
  it('reads the briefing from the authoritative choice, content and save', () => {
    const view = missionInfoPanel(bundle(), world(), choice(), 3, 1_700_000_000);
    assert.equal(view.questId, Q02);
    assert.equal(view.title, 'BLOW THE POWER PLANT');
    assert.equal(view.subtitle, getQuestSpec(Q02)?.subtitle ?? '');
    assert.equal(view.difficulty, 3);
    assert.equal(view.canStart, true);
    // The server's store is the only source for the fielded army.
    assert.deepEqual(view.army, [
      {
        itemId: 7,
        name: 'Marine',
        groupType: 'infantry',
        available: 3,
        allowed: true,
      },
    ]);
  });

  it('cannot start an active or locked mission', () => {
    const active = missionInfoPanel(bundle(), world(), choice({ active: true }), 1, 0);
    assert.equal(active.canStart, false);
    const locked = missionInfoPanel(
      bundle(), world(), choice({ locked: true, unlocked: false }), 1, 0,
    );
    assert.equal(locked.canStart, false);
  });
});

describe('the next-mission panel', () => {
  const outcome: CommandOutcome = {
    index: 0,
    ok: true,
    result: { kind: 'rewards', rewards: [{ resource: 'gold', amount: 4000 }] },
  };

  it('offers only the mission the server\'s ranks and unlock levels allow', () => {
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const nextIndex = playIndex + 1;
    const options = {
      ranks: { [playIndex]: 1 },
      playerLevel: 1,
      numQuests: QUEST_IDS.length - 1,
    };
    const result = questResultView(Q02, outcome, undefined, options);
    const view = nextMissionPanel(result, options)!;
    assert.equal(view.questId, QUEST_IDS[nextIndex]);
    // The choice's index is the one-based slot, not the zero-based array index.
    assert.equal(view.index, nextIndex + 1);
    assert.equal(view.available, true);
    assert.equal(view.won, true);
    assert.equal(view.rank, 1);
    assert.deepEqual(view.rewards, [{ resource: 'gold', amount: 4000 }]);
  });

  it('fails closed when the server has no next mission or still locks it', () => {
    assert.equal(nextMissionPanel(questResultView(Q02, outcome), {}), null);
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const nextIndex = playIndex + 1;
    const locked = {
      ranks: { [playIndex]: 1 },
      playerLevel: 1,
      minLevels: { [nextIndex]: 10 },
      numQuests: QUEST_IDS.length - 1,
    };
    const result = questResultView(Q02, outcome, undefined, locked);
    // The result still names a mission, but the action gate refuses it.
    assert.ok(result.next);
    assert.equal(nextMissionPanel(result, locked), null);
  });
});

describe('the yes/no confirmation panel', () => {
  it('uses the client\'s own button texts', () => {
    assert.deepEqual(confirmPanel('Start this mission?'), {
      message: 'Start this mission?',
      yes: 'YES',
      no: 'NO',
    });
    assert.equal(CONFIRM_YES, 'YES');
    assert.equal(CONFIRM_NO, 'NO');
  });

  it('gives each panel its own gesture id but keeps one dialog slot', () => {
    const kinds = ['intro', 'help', 'mission', 'next', 'confirm'] as const;
    const ids = kinds.map((kind) => onboardingDialog(kind, `title:${kind}`).id);
    assert.deepEqual(ids, [
      'onboarding-intro',
      'onboarding-help',
      'onboarding-mission',
      'onboarding-next',
      'onboarding-confirm',
    ]);
    assert.equal(new Set(ids).size, 5);

    const first = onboardingDialog('mission', 'A');
    const second = onboardingDialog('confirm', 'B');
    const opened = openDialog(openDialog(CLOSED_DIALOG, first.id, first.kind, first.title),
      second.id, second.kind, second.title);
    assert.equal(opened.dialog?.id, second.id);
  });
});
