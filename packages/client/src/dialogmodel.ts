/**
 * The model behind the client's one dialog and its feedback channel.
 *
 * This is **pure state**, not a view: it never touches the DOM, the clock or
 * the network, and it never decides a game outcome. The world is the
 * server's; this module only remembers which panel the player is looking at
 * and turns the server's typed outcomes into sentences the player can read.
 *
 * G5.1 hosts briefings, combat, results and rewards in the same dialog, so
 * there is exactly **one** slot. Opening a second dialog replaces the first
 * rather than stacking an overlay on top of it: two modal dialogs would each
 * claim to be the one the player is talking to, and the second one's
 * backdrop would cover the first one's controls.
 */

/** A caller's name for a dialog, so hosts can tell their panels apart. */
export type DialogId = string;

/** The kinds of panel the one dialog can host. */
export type DialogKind =
  | 'briefing'
  | 'combat'
  | 'result'
  | 'reward'
  | 'confirm'
  | 'alert';

/** The content of the one open dialog. */
export interface DialogContent {
  /** The host's name for this panel. */
  readonly id: DialogId;
  /** Which panel it is. */
  readonly kind: DialogKind;
  /** The heading, which also labels the dialog for assistive technology. */
  readonly title: string;
}

/** The dialog's whole state. One slot, open or empty. */
export interface DialogState {
  /** The open panel, or null when nothing is open. */
  readonly dialog: DialogContent | null;
}

/** The state with no dialog open. Shared, frozen, and never mutated. */
export const CLOSED_DIALOG: DialogState = Object.freeze({ dialog: null });

/** The id of the heading that labels the dialog element. */
export const DIALOG_TITLE_ID = 'swl-dialog-title';

/**
 * Open (or replace) the dialog.
 *
 * The returned state is new; the one passed in is left alone. Because there
 * is only one slot, an already-open dialog is replaced, never duplicated.
 */
export function openDialog(
  state: DialogState,
  id: DialogId,
  kind: DialogKind,
  title: string,
): DialogState {
  void state;
  return { dialog: { id, kind, title } };
}

/** Close the dialog, leaving any other host state alone. */
export function closeDialog(state: DialogState): DialogState {
  void state;
  return CLOSED_DIALOG;
}

/** The ways a player can dismiss a modal dialog. */
export type DialogDismissAction =
  | { readonly type: 'escape' }
  | { readonly type: 'backdrop' }
  | { readonly type: 'close' };

/**
 * Apply a dismissal to the dialog state.
 *
 * Every dismissal means the same thing here — the dialog closes. The action
 * exists so a host can keep one pure reducer for its keyboard, backdrop and
 * button handlers rather than three slightly different close paths.
 */
export function dialogAction(
  state: DialogState,
  action: DialogDismissAction,
): DialogState {
  void action;
  return closeDialog(state);
}

/** The ARIA attributes of an open dialog. */
export interface DialogAria {
  readonly role: 'dialog';
  readonly ariaModal: true;
  readonly ariaLabelledby: typeof DIALOG_TITLE_ID;
}

/**
 * The ARIA attributes the dialog element needs, or null when it is closed.
 *
 * The heading carries `DIALOG_TITLE_ID`, so `ariaLabelledby` always points
 * at the visible title rather than at a hidden duplicate label.
 */
export function dialogAria(state: DialogState): DialogAria | null {
  if (!state.dialog) return null;
  return {
    role: 'dialog',
    ariaModal: true,
    ariaLabelledby: DIALOG_TITLE_ID,
  };
}

/* -------------------------------------------------------------------------
 * Feedback
 * ---------------------------------------------------------------------- */

/** How a feedback message should be read aloud and drawn. */
export type FeedbackTone = 'success' | 'error';

/** One sentence shown to the player. */
export interface FeedbackMessage {
  readonly tone: FeedbackTone;
  readonly text: string;
}

/**
 * The shape of a `NativeResponse` outcome that feedback needs.
 *
 * Structural on purpose: the model does not depend on the protocol package,
 * so it can be driven by a real `CommandOutcome` or by a test literal. Only
 * the machine code and the human explanation are used; every other field is
 * ignored.
 */
export interface FeedbackOutcome {
  readonly index: number;
  readonly ok: boolean;
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
}

/** The fallback when the server refused the request without an outcome. */
export const REFUSED_WITHOUT_OUTCOME = 'The server refused the request.';

/** The fallback when an error carries neither a message nor a code. */
const NO_REASON = 'no reason given';

function successText(index: number): string {
  return `Command ${index} succeeded.`;
}

function refusalText(outcome: FeedbackOutcome): string {
  const code = outcome.error?.code;
  const message = outcome.error?.message;
  const reason = message || code || NO_REASON;
  const at = `Command ${outcome.index}`;
  return code ? `${at} was refused (${code}): ${reason}` : `${at} was refused: ${reason}`;
}

/**
 * Turn the server's typed outcomes into messages the player can read.
 *
 * `ok` is the response's own flag. It is used **only** to catch a refusal
 * that carries no per-command outcome, so a rejected request is never
 * silent. Individual outcomes win over the flag: a refused outcome is shown
 * as an error even if a response wrongly claims success.
 *
 * This is a reading of the server's answer, not a decision. It produces
 * sentences; it never changes the world, the wallet or a quest.
 */
export function feedbackFrom(
  outcomes: readonly FeedbackOutcome[],
  ok: boolean,
): readonly FeedbackMessage[] {
  const messages: FeedbackMessage[] = [];
  let sawRefusal = false;
  for (const outcome of outcomes) {
    if (outcome.ok === true) {
      messages.push({ tone: 'success', text: successText(outcome.index) });
    } else {
      sawRefusal = true;
      messages.push({ tone: 'error', text: refusalText(outcome) });
    }
  }
  if (!ok && !sawRefusal) {
    messages.push({ tone: 'error', text: REFUSED_WITHOUT_OUTCOME });
  }
  return messages;
}
