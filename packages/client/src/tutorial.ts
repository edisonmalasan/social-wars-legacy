/**
 * The tutorial.
 *
 * The tutorial is a **scripted sequence of pointers**. Each step names a
 * place on the screen and what the player is expected to do there, and
 * the client draws an arrow at it. So the sequence *is* the tutorial.
 *
 * The steps are extracted from the client's `TutorialMain.as` into
 * `re/data/tutorial-steps.json`, and they are not one list: the base
 * list is 27 steps, and **six more** are appended when the
 * "visit the General" variant is on. Each step therefore records the
 * gate it sits behind, and a player only sees the steps whose gate is
 * true for them.
 *
 * The client's own step order is not the numeric order of the step
 * constants — the house-building steps are interleaved with the goal
 * steps — so the **order in the list is the order**, and the step number
 * is only an identifier.
 */

/** One step. */
export interface TutorialStep {
  /** The step's number, which is only an identifier. */
  step: number;
  /** The condition the step sits behind, or null for the base list. */
  gate: string | null;
  /** Where the pointer points. */
  x?: number;
  y?: number;
  /** Where the arrow is anchored. */
  ax?: number;
  ay?: number;
  /** The arrow's rotation. */
  arot?: number;
  /** How the arrow is aligned to its anchor. */
  ava?: string;
  /** The circle the pointer is drawn in. */
  cx?: number;
  cy?: number;
  /** The circle's radius. */
  cr?: number;
  /** Whether the step shows a button. */
  haveButton?: boolean;
  /** What the step does when it is entered. */
  ef?: string;
  /** What the step does when it is left backwards. */
  nf?: string;
  /** The step's title, as a language-literal expression. */
  title?: string;
  /** The step's lesson, as a language-literal expression. */
  lesson?: string;
  /** Whether the player may skip the step. */
  skippable?: boolean;
  /** The ground marker. */
  marcaSuelo?: number;
}

/** The flags that decide which variant a player sees. */
export type TutorialGates = Record<string, boolean>;

/** The client's literal wrapper: `Language.getLiteral("...")`. */
const LITERAL = /^Language\.getLiteral\(\s*"((?:[^"\\]|\\.)*)"\s*\)$/s;

/**
 * The text of a tutorial literal.
 *
 * The extractor keeps the client's own expression - `Language
 * .getLiteral("WELCOME, SOLDIER!")` - because that is the evidence, and
 * the interface needs the string inside it. A missing literal, or the
 * client's own `null`, is the empty string.
 *
 * The escapes are the ActionScript ones: `\n` is a line break, and `\'`
 * and `\"` are the quotes themselves.
 */
export function tutorialLiteral(expression: unknown): string {
  if (typeof expression !== 'string') return '';
  const trimmed = expression.trim();
  if (trimmed === '' || trimmed === 'null') return '';
  const match = LITERAL.exec(trimmed);
  if (!match) return trimmed;
  return match[1]!.replace(/\\(.)/gs, (_match, character: string) =>
    character === 'n' ? '\n' : character === 't' ? '\t' : character,
  );
}

/**
 * The tutorial's state.
 *
 * The player's position is an **index into the steps they can see**, not
 * a step number: the gated steps are not in their list, so the indices
 * shift.
 */
export class Tutorial {
  private readonly steps: TutorialStep[];
  private index = 0;

  constructor(steps: readonly TutorialStep[], gates: TutorialGates = {}) {
    // The steps whose gate is true for this player, in the client's order.
    this.steps = steps.filter((step) => {
      if (!step.gate) return true;
      return gates[step.gate] === true;
    });
  }

  /** How many steps this player has. */
  get length(): number {
    return this.steps.length;
  }

  /** The steps this player sees. */
  get visible(): readonly TutorialStep[] {
    return this.steps;
  }

  /** The step the player is on, or null when the tutorial is over. */
  get current(): TutorialStep | null {
    return this.steps[this.index] ?? null;
  }

  /** The index of the current step. */
  get position(): number {
    return this.index;
  }

  /** Whether the tutorial is over. */
  get finished(): boolean {
    return this.index >= this.steps.length;
  }

  /** Move to the next step. */
  next(): void {
    if (this.index < this.steps.length) this.index += 1;
  }

  /** Move back a step. */
  previous(): void {
    if (this.index > 0) this.index -= 1;
  }

  /** The last step this player sees, or null when there are none. */
  get last(): TutorialStep | null {
    return this.steps[this.steps.length - 1] ?? null;
  }

  /** Finish the tutorial outright, which is what skipping does. */
  finish(): void {
    this.index = this.steps.length;
  }

  /** Skip the tutorial, if the current step allows it. */
  skip(): boolean {
    const step = this.current;
    if (!step || step.skippable !== true) return false;
    this.index = this.steps.length;
    return true;
  }

  /** Move to a step by its number, which is how the client resumes. */
  jumpTo(stepNumber: number): boolean {
    const index = this.steps.findIndex((step) => step.step === stepNumber);
    if (index < 0) return false;
    this.index = index;
    return true;
  }

  /**
   * Whether a step is the one the tutorial is on.
   *
   * The client compares against the step's **number** in several places,
   * so the number has to be comparable from outside.
   */
  isCurrent(stepNumber: number): boolean {
    return this.current?.step === stepNumber;
  }
}
