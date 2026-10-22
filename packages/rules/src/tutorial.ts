/**
 * The tutorial's progression.
 *
 * The tutorial is a **scripted sequence of pointers**: each step names a
 * place on the screen and what the player is expected to do there. The
 * client walks the steps and tells the server which one it reached.
 *
 * The server does not police the *order* — the tutorial is a guided tour,
 * and the client may go back a step — but it does own two things:
 *
 * - **which steps exist**, so a client cannot invent one; and
 * - **how far the player has got**, which is the *furthest* step reached,
 *   because the tutorial can be walked backwards.
 *
 * The grants are the server's business, and they are policed elsewhere:
 * the tutorial points at the actions, and the actions are the commands
 * the server already checks.
 */

/**
 * The tutorial's step numbers.
 *
 * The client's own `TutorialMain.STEP_*` constants, which run from 100 to
 * 138. They are the game's, not the client's: a step number is a fact
 * about the game, like a collect period.
 */
export const TUTORIAL_STEPS: readonly number[] = [
  100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
  115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129,
  130, 131, 133, 134, 135, 136, 138,
];

/** Whether a step is one the tutorial has. */
export function isTutorialStep(step: number): boolean {
  return TUTORIAL_STEPS.includes(step);
}

/** The player's tutorial state. */
export interface TutorialState {
  /** The furthest step the player has reached. Zero when they have not started. */
  step: number;
  /** Whether the tutorial has been finished. */
  complete: boolean;
}

/** The state of a player who has not started the tutorial. */
export const NO_TUTORIAL: TutorialState = { step: 0, complete: false };

/**
 * The state after a step.
 *
 * The step must be one the tutorial has, and the player's step only ever
 * goes **forwards**: the client can walk back through the tutorial, and
 * the furthest step is the one that counts.
 */
export function advanceTutorial(
  state: TutorialState,
  step: number,
): { ok: true; state: TutorialState } | { ok: false; reason: string } {
  if (!isTutorialStep(step)) {
    return { ok: false, reason: 'unknown-step' };
  }
  if (state.complete) {
    // The tutorial is finished, and finishing it is final.
    return { ok: true, state };
  }
  // The last step is the congratulation: reaching it is finishing the
  // tutorial, and the client's own tutorial ends there.
  const complete = step === TUTORIAL_STEPS[TUTORIAL_STEPS.length - 1];
  return {
    ok: true,
    state: { step: Math.max(state.step, step), complete },
  };
}

/** The state after the tutorial is finished. */
export function finishTutorial(state: TutorialState): TutorialState {
  return { step: state.step, complete: true };
}

/** Where the tutorial's state lives in the private state. */
export const TUTORIAL_STATE_KEY = 'tutorial';

/**
 * The player's tutorial state, read out of the private state.
 *
 * A private state with nothing in it is a player who has not started the
 * tutorial, and a private state with something odd in it is treated the
 * same way rather than trusted.
 */
export function tutorialState(privateState: Record<string, unknown>): TutorialState {
  const raw = privateState[TUTORIAL_STATE_KEY];
  if (!raw || typeof raw !== 'object') return NO_TUTORIAL;
  const record = raw as { step?: unknown; complete?: unknown };
  const step = Number(record.step);
  return {
    step: Number.isFinite(step) && step > 0 ? step : 0,
    complete: record.complete === true,
  };
}
