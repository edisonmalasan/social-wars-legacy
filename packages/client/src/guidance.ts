/**
 * The "click here" guidance.
 *
 * The client points at things the player has not looked at yet, in two
 * places:
 *
 * - the **tutorial's arrow**, which points at a place on the screen and
 *   says what the player is expected to do there. The steps are in
 *   `re/data/tutorial-steps.json` and the state machine is in
 *   `tutorial.ts`.
 * - the **goals panel's markers**: up to three "CLICK HERE!" badges, one
 *   on each of the three goal slots, marking the goals the player has
 *   not visited yet.
 *
 * This module is the second one.
 *
 * ## The client's rule
 *
 * ```as3
 * // popups/PopupGoals.as:328-345
 * var _loc3_:Array = [mcGoal1, mcGoal2, mcGoal3];
 * var _loc4_:Array = [this.newgoal1, this.newgoal2, this.newgoal3];
 * var _loc5_:Array = this.goalManager.getActiveGoals(0, 3);
 * ...
 * this.prepareGoalIcon(_loc3_[_loc6_], _loc4_[_loc6_], _loc5_[_loc6_], _loc6_);
 * ```
 *
 * ```as3
 * // popups/PopupGoals.as:360-368
 * if (!param1.contains(param2) && !this.bClicked1
 *     && !Base.Main.tutorialMode && !_loc5_.isVisited()) {
 *    param1.addChild(param2);
 * } else if (param1.contains(param2)) {
 *    param1.removeChild(param2);
 * }
 * ```
 *
 * So the marker is shown when the goal has **not been visited**, the
 * tutorial is **not** running, and the marker has **not been clicked**.
 *
 * ## The client's quirk
 *
 * The condition reads `bClicked1` for **all three** markers, even though
 * the client keeps `bClicked1`, `bClicked2` and `bClicked3` separately.
 * So clicking the **first** badge suppresses the badges on all three
 * goals, while clicking the second or the third suppresses only that one.
 *
 * That is the client's behaviour, and the client is the specification, so
 * the clone reproduces it. It is recorded here so that it is a decision
 * and not an accident.
 */

/** A goal, as the guidance panel sees it. */
export interface GuidanceGoal {
  /** The goal's index in the goal list. */
  index: number;
  /** Whether the player has visited it. */
  visited: boolean;
  /** Whether it is completed. */
  completed: boolean;
}

/**
 * The goals that are active at an offset.
 *
 * The client's own rule (`managers/GoalManager.as:545-568`): the goals
 * that are not completed, counted from the offset, up to a count.
 *
 * The offset counts the **incomplete** goals only, so a completed goal
 * in the middle of the list does not take up a slot.
 */
export function activeGoals(
  goals: readonly GuidanceGoal[],
  offset = 0,
  count = 0,
): GuidanceGoal[] {
  const out: GuidanceGoal[] = [];
  let seen = 0;
  for (const goal of goals) {
    if (goal.completed) continue;
    if (seen === offset) {
      out.push(goal);
      if (count > 0 && out.length >= count) break;
    } else {
      seen += 1;
    }
  }
  return out;
}

/** How many goal slots carry a marker. */
export const MARKER_SLOTS = 3;

/** The literal on the markers. */
export const CLICK_HERE_LABEL = 'CLICK HERE!';

/** The options for the markers. */
export interface MarkerOptions {
  /** Whether the tutorial is running. */
  tutorialMode?: boolean;
  /** Whether the first marker has been clicked. */
  firstMarkerClicked?: boolean;
}

/**
 * Whether each of the goal slots carries a "CLICK HERE!" marker.
 *
 * The list is the slots in order, and it is empty when there are fewer
 * goals than slots.
 */
export function markerSlots(
  goals: readonly GuidanceGoal[],
  options: MarkerOptions = {},
): boolean[] {
  const tutorial = options.tutorialMode === true;
  // The client's quirk: the check is on the FIRST marker only.
  const clicked = options.firstMarkerClicked === true;

  const shown = activeGoals(goals, 0, MARKER_SLOTS).map(
    (goal) => !clicked && !tutorial && !goal.visited,
  );

  // The client's loop leaves the unused slots hidden.
  while (shown.length < MARKER_SLOTS) shown.push(false);
  return shown;
}

/**
 * The slots that carry a marker, with the goal each one marks.
 *
 * This is what the renderer needs: which slot to draw the badge on, and
 * which goal it points at.
 */
export function markedGoals(
  goals: readonly GuidanceGoal[],
  options: MarkerOptions = {},
): { slot: number; goal: GuidanceGoal }[] {
  const slots = markerSlots(goals, options);
  const active = activeGoals(goals, 0, MARKER_SLOTS);
  const out: { slot: number; goal: GuidanceGoal }[] = [];
  active.forEach((goal, index) => {
    if (slots[index]) out.push({ slot: index, goal });
  });
  return out;
}
