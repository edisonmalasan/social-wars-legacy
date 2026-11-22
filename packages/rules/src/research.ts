/**
 * Research centres: the pure rules for Area 51 and the Robotic Center.
 *
 * The specification is the client, `popups/PopupResearchCenter.as` (1.5.4),
 * where it disagrees with the upstream Python `command.py`. All state is
 * server-owned; these functions take a state value and return a new one.
 * `nowSeconds` is always supplied by the caller — there is no wall clock here.
 *
 * The client's rules:
 *
 * - 10 steps per item, 6 hours per step (`TOTAL_STEPS`, `_stepTime.value`).
 * - `next_research_step` increments `researchStepNumber[type]`; it restarts
 *   `timeStampDoResearch[type]` only when the client's `restartCountdown`
 *   flag is true (`goNextStep()`, lines 402-422). Friend help sends false,
 *   which is why the upstream server's unconditional timestamp write is
 *   wrong.
 * - `research_buy_step_cash` zeroes the timestamp to skip the wait but does
 *   not increment the step (`clickGetnow()`, lines 433-447).
 * - `next_research_item` grants the item and advances `researchItemNumber`.
 *   The client wraps after the sixth item (`nextResearchItem()`, lines
 *   522-539); upstream uses a bare `+= 1`, which is the disagreement the
 *   client wins.
 * - `reset_research_item` zeroes the item, step and timestamp for one type.
 * - Closing the hire popup grants `2 * friendCount` steps, capped at 10, and
 *   consumes `privateState.roboticSocialHelp` (`closeHireResults()`, lines
 *   235-257).
 *
 * The cash price comes from the research item at the current item number
 * (`getCash()`, lines 292-296), never from the client's command argument.
 */

/** Area 51 is research type 0 (`Constants.ID_BUILDING_AREA_51`). */
export const RESEARCH_TYPE_AREA_51 = 0;
/** The Robotic Center is research type 1 (`ID_BUILDING_ROBOTIC_CENTER`). */
export const RESEARCH_TYPE_ROBOTIC = 1;

/** The research type index. */
export type ResearchType = typeof RESEARCH_TYPE_AREA_51 | typeof RESEARCH_TYPE_ROBOTIC;

/** `PopupResearchCenter.TOTAL_STEPS`. */
export const RESEARCH_TOTAL_STEPS = 10;

/** `_stepTime.value = 6 * 60 * 60`. */
export const RESEARCH_STEP_SECONDS = 6 * 60 * 60;

/** `PopupResearchCenter.FRIENDS_MULTIPLIER`. */
export const RESEARCH_FRIENDS_MULTIPLIER = 2;

/** The client has six item slots, and wraps at six. */
export const RESEARCH_ITEM_COUNT = 6;

/** `Constants.ID_BUILDING_AREA_51`. */
export const RESEARCH_BUILDING_AREA_51 = 139;

/** `Constants.ID_BUILDING_ROBOTIC_CENTER`. */
export const RESEARCH_BUILDING_ROBOTIC = 86;

/** `CASH_SMALL` / `CASH_BIG` in the popup. */
export const RESEARCH_CASH_SMALL = 3;
export const RESEARCH_CASH_BIG = 15;

/** One item in a research track. */
export interface ResearchItem {
  id: number;
  cash: number;
}

/**
 * The Robotic Center track, in `init()` order:
 * Bumblebee, Celestial Mega Mech, Supreme Bot, Samurai Bot, Metal Draggy,
 * Metallic Dragon.
 */
export const ROBOTIC_RESEARCH_ITEMS: readonly ResearchItem[] = [
  { id: 1062, cash: RESEARCH_CASH_BIG },
  { id: 1101, cash: RESEARCH_CASH_SMALL },
  { id: 1075, cash: RESEARCH_CASH_SMALL },
  { id: 1141, cash: RESEARCH_CASH_SMALL },
  { id: 1085, cash: RESEARCH_CASH_SMALL },
  { id: 1105, cash: RESEARCH_CASH_SMALL },
];

/**
 * The Area 51 track, in `init()` order:
 * Black Aircraft, Stealth Plane, Red Draggy, Red Dragon, Blue Draggy,
 * Blue Dragon.
 */
export const AREA_51_RESEARCH_ITEMS: readonly ResearchItem[] = [
  { id: 1048, cash: RESEARCH_CASH_SMALL },
  { id: 1096, cash: RESEARCH_CASH_BIG },
  { id: 1097, cash: RESEARCH_CASH_SMALL },
  { id: 1099, cash: RESEARCH_CASH_BIG },
  { id: 1098, cash: RESEARCH_CASH_SMALL },
  { id: 1100, cash: RESEARCH_CASH_BIG },
];

/** The three per-type arrays of `privateState`, plus the help list. */
export interface ResearchState {
  /** `researchItemNumber[type]`: which of the six items is being researched. */
  itemNumber: [number, number];
  /** `researchStepNumber[type]`: steps completed for the current item. */
  stepNumber: [number, number];
  /** `timeStampDoResearch[type]`: when the current step started, in seconds. */
  timestamp: [number, number];
  /** `privateState.roboticSocialHelp`: friends who have not helped yet. */
  roboticSocialHelp: string[];
}

/** The authoritative state a new player starts with. */
export function initialResearchState(): ResearchState {
  return { itemNumber: [0, 0], stepNumber: [0, 0], timestamp: [0, 0], roboticSocialHelp: [] };
}

/** Copy the state so a transition never mutates its input. */
function cloneState(state: ResearchState): ResearchState {
  return {
    itemNumber: [state.itemNumber[0], state.itemNumber[1]],
    stepNumber: [state.stepNumber[0], state.stepNumber[1]],
    timestamp: [state.timestamp[0], state.timestamp[1]],
    roboticSocialHelp: state.roboticSocialHelp.slice(),
  };
}

function checkType(type: number): ResearchType {
  if (type !== RESEARCH_TYPE_AREA_51 && type !== RESEARCH_TYPE_ROBOTIC) {
    throw new RangeError('unknown research type');
  }
  return type;
}

/** The items of a research track. */
export function researchItemsFor(type: number): readonly ResearchItem[] {
  return checkType(type) === RESEARCH_TYPE_ROBOTIC ? ROBOTIC_RESEARCH_ITEMS : AREA_51_RESEARCH_ITEMS;
}

/** The research type that owns a building id, or `null`. */
export function researchTypeForBuilding(buildingId: number): ResearchType | null {
  if (buildingId === RESEARCH_BUILDING_AREA_51) return RESEARCH_TYPE_AREA_51;
  if (buildingId === RESEARCH_BUILDING_ROBOTIC) return RESEARCH_TYPE_ROBOTIC;
  return null;
}

/** The item at a slot, wrapping at six (`_statusItem` in the client). */
export function researchItemAt(type: number, itemNumber: number): ResearchItem {
  const items = researchItemsFor(type);
  const slot = ((Math.trunc(itemNumber) % RESEARCH_ITEM_COUNT) + RESEARCH_ITEM_COUNT) % RESEARCH_ITEM_COUNT;
  return items[slot]!;
}

/**
 * The cash price of the item currently being researched. This is what the
 * server must charge, not the `cash` argument of `research_buy_step_cash`.
 */
export function researchCashCost(type: number, itemNumber: number): number {
  return researchItemAt(type, itemNumber).cash;
}

/** `next_research_step`: one more step; the countdown restarts only if asked. */
export function nextResearchStep(
  state: ResearchState,
  type: number,
  restartCountdown: boolean,
  nowSeconds: number,
): ResearchState {
  const index = checkType(type);
  const next = cloneState(state);
  next.stepNumber[index]++;
  if (restartCountdown) next.timestamp[index] = nowSeconds;
  return next;
}

/** The result of a cash speed-up: a new state and the cash to debit. */
export interface ResearchBuyStepResult {
  state: ResearchState;
  /** The cash the server should take from the wallet. */
  cashCost: number;
}

/**
 * `research_buy_step_cash`: skip the wait by zeroing the timestamp. The step
 * count is deliberately unchanged — paying buys time, not progress.
 */
export function researchBuyStepCash(state: ResearchState, type: number): ResearchBuyStepResult {
  const index = checkType(type);
  const next = cloneState(state);
  next.timestamp[index] = 0;
  return { state: next, cashCost: researchCashCost(index, next.itemNumber[index]) };
}

/** The result of collecting a finished research item. */
export interface ResearchItemResult {
  state: ResearchState;
  /** The item id granted, or `null` when the step was not finished. */
  grantedItemId: number | null;
}

/**
 * `next_research_item`: on the tenth step, grant the current item, advance
 * the item slot modulo six, and reset the step and timestamp. Before the
 * tenth step nothing changes.
 */
export function nextResearchItem(state: ResearchState, type: number): ResearchItemResult {
  const index = checkType(type);
  if (state.stepNumber[index] < RESEARCH_TOTAL_STEPS) {
    return { state, grantedItemId: null };
  }
  const grantedItemId = researchItemAt(index, state.itemNumber[index]).id;
  const next = cloneState(state);
  next.itemNumber[index] = (next.itemNumber[index] + 1) % RESEARCH_ITEM_COUNT;
  next.stepNumber[index] = 0;
  next.timestamp[index] = 0;
  return { state: next, grantedItemId };
}

/** `reset_research_item`: zero the three arrays for one type. */
export function resetResearchItem(state: ResearchState, type: number): ResearchState {
  const index = checkType(type);
  const next = cloneState(state);
  next.itemNumber[index] = 0;
  next.stepNumber[index] = 0;
  next.timestamp[index] = 0;
  return next;
}

/** The result of closing the hire-friends popup. */
export interface RoboticHelpResult {
  state: ResearchState;
  /** The number of friends whose help was consumed. */
  friendCount: number;
  /** The number of steps actually added, after the cap at ten. */
  stepsGranted: number;
}

/**
 * `finish_robotic_help`: each pending friend grants two Robotic Center steps,
 * capped at ten. Reaching the cap clears the timestamp. The help list is
 * consumed on the first call, so a second call grants nothing.
 */
export function finishRoboticHelp(state: ResearchState): RoboticHelpResult {
  const index = RESEARCH_TYPE_ROBOTIC;
  const friendCount = state.roboticSocialHelp.length;
  const next = cloneState(state);
  const before = next.stepNumber[index];
  next.stepNumber[index] = Math.min(
    RESEARCH_TOTAL_STEPS,
    before + friendCount * RESEARCH_FRIENDS_MULTIPLIER,
  );
  const stepsGranted = next.stepNumber[index] - before;
  if (next.stepNumber[index] >= RESEARCH_TOTAL_STEPS) next.timestamp[index] = 0;
  next.roboticSocialHelp = [];
  return { state: next, friendCount, stepsGranted };
}
