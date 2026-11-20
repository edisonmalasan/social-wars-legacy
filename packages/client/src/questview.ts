/**
 * The quest interface's pure view models.
 *
 * This module never touches the DOM, the network or the clock, and it never
 * decides a game outcome. It reads three things and nothing else:
 *
 * - the **server's** world (`activeQuestState`, `questsRank`),
 * - the **content's** quests (`QUEST_IDS`, the event channels), and
 * - the **player's** own gestures (a chosen slot, a chosen difficulty).
 *
 * Every counter, HP value, kill, win and reward shown by the interface comes
 * from a server answer. A model here can only *read* those values and turn
 * them into rows and buttons; it cannot invent a progress the server has not
 * made. In particular, the "Finish quest" button is always offered as a
 * gesture — whether it wins is decided by `end_quest` on the server.
 */
import type { CommandOutcome, Reward } from '@swl/protocol';
import { QUEST_IDS, getQuestSpec, questTitle } from '@swl/rules';

import { chapterMap, type QuestSlot } from './chapters.ts';
import { activeQuestState, type ActiveQuestStateView } from './featurestate.ts';
import type { WorldSnapshot } from './session.ts';
import { REFUSED_WITHOUT_OUTCOME, type DialogContent } from './dialogmodel.ts';

/** The three difficulties the loading popup offers. */
export type QuestDifficulty = 1 | 2 | 3;

/** A quest's event channel, as the content bundle stores it. */
export interface QuestEventSource {
  readonly kind: 'truckArrivals' | 'eligibleEnemies' | 'civilianEvacuations';
  readonly refs: readonly string[];
  readonly count: number;
}

/** A quest the chapter map offers as a gesture the player can pick. */
export interface QuestChoice {
  /** The quest's one-based index in the client's play order. */
  readonly index: number;
  /** The authoritative quest id. */
  readonly questId: string;
  /** The rules' display title. */
  readonly title: string;
  /** The rank the server reached it at. */
  readonly rank: number;
  /** The content's unlock level. */
  readonly levelUnlock: number;
  /** Whether the map still locks the slot. */
  readonly locked: boolean;
  /** Whether the player's level meets the unlock level. */
  readonly unlocked: boolean;
  /** Whether this is the server's active quest. */
  readonly active: boolean;
}

/**
 * One chapter slot as a pickable quest.
 *
 * The slot itself comes from the client's own chapter model, which already
 * knows which ones the server has ranked and which are still locked. The
 * level gate is applied here as a second reading of the content.
 */
export function questChoice(
  slot: QuestSlot,
  playerLevel: number,
  activeQuestId: string | null = null,
): QuestChoice | null {
  const questId = QUEST_IDS[slot.index - 1];
  if (!questId) return null;
  const locked = slot.locked || playerLevel < slot.levelUnlock;
  return {
    index: slot.index,
    questId,
    title: questTitle(questId) ?? questId,
    rank: slot.rank,
    levelUnlock: slot.levelUnlock,
    locked,
    unlocked: !locked,
    active: questId === activeQuestId,
  };
}

/** Every pickable quest slot of the chapter map. */
export function questChoices(
  ranks: Readonly<Record<number, number>>,
  minLevels: Readonly<Record<number, number>>,
  playerLevel: number,
  activeQuestId: string | null = null,
  numQuests?: number,
): QuestChoice[] {
  const slots = chapterMap(ranks, {
    minLevels,
    ...(numQuests === undefined ? {} : { numQuests }),
  });
  const out: QuestChoice[] = [];
  for (const slot of slots) {
    const choice = questChoice(slot, playerLevel, activeQuestId);
    if (choice) out.push(choice);
  }
  return out;
}

/** Normalise a player's difficulty choice to the client's 1-3 stars. */
export function questDifficulty(value: unknown): QuestDifficulty {
  if (typeof value !== 'number' || !Number.isInteger(value)) return 1;
  return Math.min(3, Math.max(1, value)) as QuestDifficulty;
}

/** The briefing the player reads before asking the server to start. */
export interface QuestBriefing {
  readonly questId: string;
  readonly title: string;
  readonly subtitle: string;
  readonly difficulty: QuestDifficulty;
  readonly canStart: boolean;
}

/** A briefing model: content titles, a player-chosen difficulty, no outcome. */
export function briefingView(choice: QuestChoice, difficulty: unknown): QuestBriefing {
  return {
    questId: choice.questId,
    title: choice.title,
    subtitle: getQuestSpec(choice.questId)?.subtitle ?? '',
    difficulty: questDifficulty(difficulty),
    canStart: choice.unlocked && !choice.active,
  };
}

/** One server counter, as a row the combat panel can draw. */
export interface QuestCounterView {
  readonly name: string;
  readonly value: number;
}

/** One roster element, with the server's own HP and alive flag. */
export interface QuestElementView {
  readonly ref: string;
  readonly hp: number;
  readonly alive: boolean;
  /** Whether losing this element loses the quest (from the rules, not the client). */
  readonly key: boolean;
  readonly label: string;
}

/** A button the interface offers. The server still decides what it does. */
export type QuestActionChoice =
  | {
      readonly kind: 'strike';
      readonly ref: string;
      readonly label: string;
      readonly enabled: boolean;
    }
  | {
      readonly kind: 'event';
      readonly action: 'truck-arrival' | 'eligible-enemy' | 'civilian-evacuation';
      readonly ref: string;
      readonly label: string;
      readonly enabled: boolean;
    }
  | {
      readonly kind: 'kill-report';
      readonly ref: string;
      readonly label: string;
      readonly enabled: boolean;
    }
  | { readonly kind: 'end'; readonly label: string; readonly enabled: boolean };

/** The options the combat panel reads from the rules and the content. */
export interface QuestViewOptions {
  /** The quest's losing elements, from its rules spec. */
  readonly keyRefs?: readonly string[];
  /** The quest's event channel, from the content bundle. */
  readonly event?: QuestEventSource;
  /** Display names for refs, from the content's items. */
  readonly labels?: Readonly<Record<string, string>>;
}

/** The active quest as the combat panel draws it. */
export interface ActiveQuestView {
  readonly questId: string;
  readonly title: string;
  readonly counters: readonly QuestCounterView[];
  readonly elements: readonly QuestElementView[];
  readonly events: readonly string[];
  readonly actions: readonly QuestActionChoice[];
}

/** Read one event channel's action from the server's counters and dedupe keys. */
function eventAction(
  event: QuestEventSource,
  counters: Readonly<Record<string, number>>,
  events: readonly string[],
): QuestActionChoice[] {
  const action =
    event.kind === 'truckArrivals'
      ? 'truck-arrival'
      : event.kind === 'eligibleEnemies'
        ? 'eligible-enemy'
        : 'civilian-evacuation';
  const counterName =
    event.kind === 'truckArrivals'
      ? 'trucksArrived'
      : event.kind === 'eligibleEnemies'
        ? 'bastardsAlive'
        : 'workersInVillages';
  const label =
    event.kind === 'truckArrivals'
      ? 'Arrive truck'
      : event.kind === 'eligibleEnemies'
        ? 'Mark enemy eligible'
        : 'Evacuate civilian';
  const value = counters[counterName] ?? 0;
  const out: QuestActionChoice[] = [];
  for (const ref of event.refs) {
    // The content's count is only a display hint: it never grants progress.
    // The server still refuses a duplicate or an over-count arrival.
    const seen =
      event.kind === 'truckArrivals'
        ? false
        : events.includes(`${event.kind === 'eligibleEnemies' ? 'eligible' : 'evac'}:${ref}`);
    const targetReached =
      event.kind === 'truckArrivals' ? value >= event.count : value <= 0;
    out.push({
      kind: 'event',
      action,
      ref,
      label: `${label} (${ref})`,
      enabled: !seen && !targetReached,
    });
  }
  return out;
}

/**
 * The buttons for one active quest: strikes on live non-key elements, the
 * strictly two-argument kill report for elements the server has killed, the
 * quest's event channel, and a Finish gesture that sends `end_quest`.
 */
export function questActions(
  active: ActiveQuestStateView,
  options: QuestViewOptions = {},
): readonly QuestActionChoice[] {
  const actions: QuestActionChoice[] = [];
  const keyRefs = options.keyRefs ?? [];
  const labels = options.labels ?? {};
  for (const [ref, element] of Object.entries(active.elements)) {
    const label = labels[ref] ?? ref;
    if (element.alive) {
      // Striking a losing element loses the quest: offer no such button.
      if (!keyRefs.includes(ref)) {
        actions.push({
          kind: 'strike',
          ref,
          label: `Strike ${label}`,
          enabled: true,
        });
      }
    } else {
      actions.push({
        kind: 'kill-report',
        ref,
        label: `Report kill: ${label}`,
        enabled: true,
      });
    }
  }
  if (options.event) {
    actions.push(...eventAction(options.event, active.counters, active.events));
  }
  // Never guessed: the player may always *ask* to finish, and the server
  // decides whether the request is a win, a refusal or a reward.
  actions.push({ kind: 'end', label: 'Finish quest', enabled: true });
  return actions;
}

/** An active quest view, or null when the save has no authoritative quest. */
export function activeQuestView(
  active: ActiveQuestStateView,
  options: QuestViewOptions = {},
): ActiveQuestView | null {
  if (!active.questId) return null;
  const keyRefs = options.keyRefs ?? [];
  const labels = options.labels ?? {};
  return {
    questId: active.questId,
    title: questTitle(active.questId) ?? active.questId,
    counters: Object.entries(active.counters)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => a.name.localeCompare(b.name)),
    elements: Object.entries(active.elements)
      .map(([ref, element]) => ({
        ref,
        hp: element.hp,
        alive: element.alive,
        key: keyRefs.includes(ref),
        label: labels[ref] ?? ref,
      }))
      .sort((a, b) => a.ref.localeCompare(b.ref)),
    events: [...active.events],
    actions: questActions(active, options),
  };
}

/**
 * Recover the active panel from `/api/world`.
 *
 * This is the reload path: the server's saved active quest is the only source
 * of the counters and HP shown on the restored panel. A bare `{ questId }`
 * seed has no ledger, and reads as no panel at all.
 */
export function activeQuestFromWorld(
  world: WorldSnapshot,
  options: QuestViewOptions = {},
): ActiveQuestView | null {
  const active = activeQuestState(world);
  return active ? activeQuestView(active, options) : null;
}

/** The result of `end_quest`, read only from the server's own answer. */
export interface QuestResultView {
  readonly won: boolean;
  readonly title: string;
  readonly message: string;
  readonly kind: 'result' | 'reward';
  /** Rewards the server answered with, never a client-computed row. */
  readonly rewards: readonly Reward[];
}

/** Build the result model from one command outcome. */
export function questResultView(
  questId: string,
  outcome: CommandOutcome | null,
  fallback: string = REFUSED_WITHOUT_OUTCOME,
): QuestResultView {
  if (!outcome) {
    return {
      won: false,
      title: 'Quest not finished',
      message: fallback,
      kind: 'result',
      rewards: [],
    };
  }
  if (outcome.ok) {
    return {
      won: true,
      title: 'Quest complete',
      message: `The server completed ${questTitle(questId) ?? questId}.`,
      kind: 'reward',
      rewards: outcome.result.kind === 'rewards' ? outcome.result.rewards : [],
    };
  }
  const code = outcome.error.code;
  const message = outcome.error.message || code || REFUSED_WITHOUT_OUTCOME;
  return {
    won: false,
    title: 'Quest not finished',
    message: code ? `${code}: ${message}` : message,
    kind: 'result',
    rewards: [],
  };
}

/** The one dialog's id for a quest panel. */
export function questDialogId(
  kind: 'briefing' | 'combat' | 'result',
  questId: string,
): string {
  return `quest:${kind}:${questId}`;
}

/** Host a briefing in the shared dialog. */
export function briefingDialog(briefing: QuestBriefing): DialogContent {
  return {
    id: questDialogId('briefing', briefing.questId),
    kind: 'briefing',
    title: briefing.title,
  };
}

/** Host the authoritative combat panel in the shared dialog. */
export function combatDialog(questId: string): DialogContent {
  return {
    id: questDialogId('combat', questId),
    kind: 'combat',
    title: questTitle(questId) ?? questId,
  };
}

/** Host the server's result in the shared dialog. */
export function resultDialog(questId: string, result: QuestResultView): DialogContent {
  return {
    id: questDialogId('result', questId),
    kind: result.kind,
    title: result.title,
  };
}
