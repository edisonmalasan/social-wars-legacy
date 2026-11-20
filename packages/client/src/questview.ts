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
import {
  QUESTS_WITH_TEAMS,
  QUEST_IDS,
  getQuestSpec,
  questTitle,
  type Army,
} from '@swl/rules';

import type { ArmyUnitView } from './army.ts';
import { chapterMap, type QuestSlot } from './chapters.ts';
import {
  activeQuestState,
  type ActiveQuestStateView,
  type LastQuestRewardView,
} from './featurestate.ts';
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
  /** Whether this quest's client popup offers a team selection. */
  readonly teamQuest: boolean;
  /** The army the server's save says the player can field, for team quests. */
  readonly army: readonly ArmyUnitView[];
}

/**
 * A briefing model: content titles, a player-chosen difficulty, no outcome.
 *
 * The army passed in is already a reading of the server's save. This function
 * only decides whether the quest offers team selection at all, from the rules'
 * `QUESTS_WITH_TEAMS`; it never decides which units may be fielded.
 */
export function briefingView(
  choice: QuestChoice,
  difficulty: unknown,
  army: readonly ArmyUnitView[] = [],
): QuestBriefing {
  return {
    questId: choice.questId,
    title: choice.title,
    subtitle: getQuestSpec(choice.questId)?.subtitle ?? '',
    difficulty: questDifficulty(difficulty),
    canStart: choice.unlocked && !choice.active,
    teamQuest: QUESTS_WITH_TEAMS.has(choice.questId),
    army,
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
  /** The team the server bound to this quest, echoed straight from the save. */
  readonly team?: Army;
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
    ...(active.team !== undefined ? { team: active.team } : {}),
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

/** The next mission, read from the server's ranks and unlock rules. */
export interface QuestResultNext {
  /** The server's one-based play index (the key ranks are stored under). */
  readonly index: number;
  /** The authoritative next quest id. */
  readonly questId: string;
  /** The rules' display title. */
  readonly title: string;
  /** Whether the server says the mission can be started now. */
  readonly available: boolean;
}

/** The server readings the result screen uses for its next-step actions. */
export interface QuestResultOptions {
  /** The player's quest ranks, keyed by the server's play index. */
  readonly ranks?: Readonly<Record<number, number>>;
  /** The content's per-quest unlock levels, keyed by play index. */
  readonly minLevels?: Readonly<Record<number, number>>;
  /** The player's level, for the unlock restriction. */
  readonly playerLevel?: number;
  /** Any quest the server still has active. */
  readonly activeQuestId?: string | null;
  /** How many quests the content has. */
  readonly numQuests?: number;
}

/** The result of `end_quest`, read only from the server's own answer. */
export interface QuestResultView {
  /** The quest the server answered for. */
  readonly questId: string;
  readonly won: boolean;
  readonly title: string;
  readonly message: string;
  readonly kind: 'result' | 'reward';
  /** Rewards the server answered with, never a client-computed row. */
  readonly rewards: readonly Reward[];
  /** Whether the server confirmed the mission was completed. */
  readonly missionComplete: boolean;
  /** The rank the server recorded, when it answered a win. */
  readonly rank: number | null;
  /** The next mission the server's progress makes available, if any. */
  readonly next: QuestResultNext | null;
}

/** The rank the server recorded for a quest, keyed by its play index. */
function questRankOf(questId: string, options: QuestResultOptions): number | null {
  const playIndex = getQuestSpec(questId)?.playIndex;
  if (playIndex === undefined) return null;
  return options.ranks?.[playIndex] ?? null;
}

/**
 * The next mission, from the server's ranks — never a client guess.
 *
 * The server keys ranks by the quest's play index, and the first unranked
 * quest is the one in progress (`chapters.ts`). A mission is offered only
 * when the server has ranked it or made it the one in progress, the content's
 * level gate is met, and no quest is currently active.
 */
function nextQuestResult(questId: string, options: QuestResultOptions): QuestResultNext | null {
  // Without the server's ranks there is no authoritative progression to read;
  // a client that guessed a next mission here would be inventing one.
  if (!options.ranks) return null;
  const playIndex = getQuestSpec(questId)?.playIndex;
  if (playIndex === undefined) return null;
  const index = playIndex + 1;
  const nextId = QUEST_IDS[index];
  if (!nextId) return null;
  const ranks = options.ranks ?? {};
  let firstUnranked = 1;
  for (let at = 1; at <= QUEST_IDS.length; at += 1) {
    if (ranks[at] !== undefined) firstUnranked = at + 1;
  }
  const maxQuests = options.numQuests ?? QUEST_IDS.length - 1;
  const unlockedByServer = ranks[index] !== undefined || firstUnranked === index;
  const levelOk = (options.playerLevel ?? 0) >= (options.minLevels?.[index] ?? 0);
  const available =
    index <= maxQuests && unlockedByServer && levelOk && options.activeQuestId !== nextId;
  return { index, questId: nextId, title: questTitle(nextId) ?? nextId, available };
}

/** Build the result model from one command outcome. */
export function questResultView(
  questId: string,
  outcome: CommandOutcome | null,
  fallback: string = REFUSED_WITHOUT_OUTCOME,
  options: QuestResultOptions = {},
): QuestResultView {
  if (!outcome) {
    return {
      questId,
      won: false,
      title: 'Quest not finished',
      message: fallback,
      kind: 'result',
      rewards: [],
      missionComplete: false,
      rank: null,
      next: null,
    };
  }
  if (outcome.ok) {
    return {
      questId,
      won: true,
      title: 'Quest complete',
      message: `The server completed ${questTitle(questId) ?? questId}.`,
      kind: 'reward',
      rewards: outcome.result.kind === 'rewards' ? outcome.result.rewards : [],
      missionComplete: true,
      rank: questRankOf(questId, options),
      next: nextQuestResult(questId, options),
    };
  }
  const code = outcome.error.code;
  const message = outcome.error.message || code || REFUSED_WITHOUT_OUTCOME;
  return {
    questId,
    won: false,
    title: 'Quest not finished',
    message: code ? `${code}: ${message}` : message,
    kind: 'result',
    rewards: [],
    missionComplete: false,
    rank: null,
    next: null,
  };
}

/** Which action of a result dialog the player pressed. */
export type QuestResultAction = 'retry' | 'next';

/**
 * The choice a result action opens, or `null` when the action must be refused.
 *
 * The server keys ranks by the quest's **zero-based playIndex**, while the
 * chapter map indexes one-based slots and maps slot `i` to `QUEST_IDS[i-1]`.
 * Looking the freshly unlocked mission up through `questChoices`/`chapterMap`
 * therefore sees the wrong slot and reads it as locked — the Next button
 * renders, but the gesture is refused. Synthesise the choice from the very
 * same authoritative reading that rendered the button instead:
 *
 * - `next` is allowed only when `nextQuestResult` still reports that exact
 *   mission as available from the server's ranks and unlock levels;
 * - `retry` is allowed only for a won quest the server actually ranked;
 * - the returned choice carries `index = playIndex + 1` and the rank at
 *   `ranks[playIndex]`, and is explicitly unlocked.
 *
 * A `null` result is fail-closed: the host refuses the gesture.
 */
export function questResultActionChoice(
  result: QuestResultView,
  questId: string,
  action: QuestResultAction,
  options: QuestResultOptions,
): QuestChoice | null {
  const spec = getQuestSpec(questId);
  if (!spec) return null;
  const playIndex = spec.playIndex;
  const ranks = options.ranks ?? {};

  if (action === 'next') {
    // Recompute from the server's ranks at action time — the exact same gate
    // the renderer used — rather than trusting a possibly stale label.
    const next = nextQuestResult(result.questId, options);
    if (!next || next.questId !== questId || !next.available) return null;
  } else {
    // Retry/replay is a gesture for a quest the server really completed.
    if (!result.won || result.questId !== questId || ranks[playIndex] === undefined) return null;
  }

  return {
    index: playIndex + 1,
    questId,
    title: questTitle(questId) ?? questId,
    rank: ranks[playIndex] ?? 0,
    levelUnlock: options.minLevels?.[playIndex] ?? 0,
    locked: false,
    unlocked: true,
    active: false,
  };
}

/**
 * Rebuild a result screen from the server's persisted receipt.
 *
 * The rows are the ones the server already paid; this never replays the
 * reward transaction. It is the reconnect counterpart of `questResultView`.
 */
export function questResultFromReceipt(
  receipt: LastQuestRewardView,
  options: QuestResultOptions = {},
): QuestResultView {
  return {
    questId: receipt.questId,
    won: true,
    title: 'Quest reward',
    message: `The server paid the reward for ${questTitle(receipt.questId) ?? receipt.questId}.`,
    kind: 'reward',
    rewards: receipt.rewards,
    missionComplete: true,
    rank: receipt.rank,
    next: nextQuestResult(receipt.questId, options),
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
