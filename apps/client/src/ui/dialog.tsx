/**
 * The client's one modal dialog.
 *
 * The model is `packages/client/src/dialogmodel.ts`: a pure state with a
 * single slot and the ARIA attributes. This file is only its drawing and its
 * keyboard/backdrop behaviour. Later G5.1 tasks put their briefing, combat,
 * result and reward panels in the body; they do not get another overlay.
 *
 * Accessibility is the reason this component exists rather than a plain
 * absolutely-positioned box: `role="dialog"`, `aria-modal`, a labelled
 * heading, Escape and backdrop dismissal, initial focus, a Tab trap and
 * focus restoration are all part of the primitive, not of each panel.
 */
import { useEffect, useRef } from 'react';
import { DIALOG_TITLE_ID, dialogAria, type DialogState } from '@swl/client';

/** The way the player asked the dialog to close. */
export type DialogDismiss = 'escape' | 'backdrop' | 'button';

/** The dialog's props. */
export interface DialogProps {
  /** The dialog's state, owned by the host. */
  readonly state: DialogState;
  /** The host closes the dialog when the player asks it to. */
  readonly onDismiss: (trigger: DialogDismiss) => void;
  /** The hosted panel's content. */
  readonly children?: React.ReactNode;
  /** The label of the close button. */
  readonly closeLabel?: string;
}

/** Focusable descendants, in the order Tab visits them. */
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** The modal dialog, or nothing when it is closed. */
export function Dialog({
  state,
  onDismiss,
  children,
  closeLabel = 'Close',
}: DialogProps): React.JSX.Element | null {
  const panel = useRef<HTMLDivElement>(null);
  // The handler can change on every host render; the listener should not.
  const dismiss = useRef(onDismiss);
  dismiss.current = onDismiss;

  const open = state.dialog !== null;
  const id = state.dialog?.id ?? null;

  // Escape closes; Tab stays inside the dialog. Both are bound to the
  // window so they work no matter which descendant currently has focus.
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        event.preventDefault();
        dismiss.current('escape');
        return;
      }
      if (event.key !== 'Tab') return;
      const root = panel.current;
      if (!root) return;
      const items = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) {
        event.preventDefault();
        root.focus();
        return;
      }
      const first = items[0]!;
      const last = items[items.length - 1]!;
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === root)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Move focus in on open, give it back on close. Re-run when the hosted
  // panel changes so a briefing handed over to combat takes the focus with
  // it. The cleanup is what restores focus, including on a re-host.
  useEffect(() => {
    if (!open) return;
    const previous =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const root = panel.current;
    const first = root?.querySelector<HTMLElement>(FOCUSABLE) ?? null;
    (first ?? root)?.focus();
    return () => {
      previous?.focus();
    };
  }, [open, id]);

  const aria = dialogAria(state);
  if (!aria || !state.dialog) return null;

  return (
    <div
      className="swl-dialog-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onDismiss('backdrop');
      }}
    >
      <div
        ref={panel}
        className={`swl-dialog swl-dialog-${state.dialog.kind}`}
        role={aria.role}
        aria-modal={aria.ariaModal}
        aria-labelledby={aria.ariaLabelledby}
        tabIndex={-1}
      >
        <div className="swl-dialog-head">
          <h2 id={DIALOG_TITLE_ID} className="swl-dialog-title">
            {state.dialog.title}
          </h2>
          <button
            type="button"
            className="swl-dialog-close"
            aria-label={closeLabel}
            onClick={() => onDismiss('button')}
          >
            ×
          </button>
        </div>
        <div className="swl-dialog-body">{children}</div>
      </div>
    </div>
  );
}
