import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  CLOSED_DIALOG,
  DIALOG_TITLE_ID,
  closeDialog,
  dialogAction,
  dialogAria,
  feedbackFrom,
  openDialog,
} from './dialogmodel.ts';

describe('the dialog model', () => {
  it('opens a labelled dialog from a closed state', () => {
    const state = openDialog(CLOSED_DIALOG, 'brief-1', 'briefing', 'Battle Briefing');
    assert.ok(state.dialog);
    assert.equal(state.dialog.id, 'brief-1');
    assert.equal(state.dialog.kind, 'briefing');
    assert.equal(state.dialog.title, 'Battle Briefing');
    // The seed is a constant; opening must not write into it.
    assert.equal(CLOSED_DIALOG.dialog, null);
  });

  it('does not mutate the state it was given', () => {
    const first = openDialog(CLOSED_DIALOG, 'a', 'alert', 'A');
    const second = openDialog(first, 'b', 'combat', 'B');
    assert.equal(first.dialog?.id, 'a');
    assert.equal(second.dialog?.id, 'b');
  });

  it('clears the dialog when it closes', () => {
    const opened = openDialog(CLOSED_DIALOG, 'x', 'result', 'Result');
    const closed = closeDialog(opened);
    assert.equal(closed.dialog, null);
    assert.equal(opened.dialog?.id, 'x');
  });

  it('replaces an open dialog instead of stacking a second one', () => {
    let state = openDialog(CLOSED_DIALOG, 'one', 'briefing', 'One');
    state = openDialog(state, 'two', 'reward', 'Two');
    assert.equal(state.dialog?.id, 'two');
    // There is exactly one slot — no hidden list to open a duplicate into.
    assert.equal((state as unknown as { dialogs?: unknown }).dialogs, undefined);
  });

  it('closes on both the Escape and the backdrop actions', () => {
    const opened = openDialog(CLOSED_DIALOG, 'x', 'confirm', 'Confirm?');
    assert.equal(dialogAction(opened, { type: 'escape' }).dialog, null);
    assert.equal(dialogAction(opened, { type: 'backdrop' }).dialog, null);
    assert.equal(opened.dialog?.id, 'x');
  });

  it('exposes the ARIA attributes of an open dialog, and none when closed', () => {
    const opened = openDialog(CLOSED_DIALOG, 'x', 'combat', 'Combat');
    const aria = dialogAria(opened);
    assert.ok(aria);
    assert.equal(aria.role, 'dialog');
    assert.equal(aria.ariaModal, true);
    assert.equal(aria.ariaLabelledby, DIALOG_TITLE_ID);
    assert.equal(dialogAria(CLOSED_DIALOG), null);
    assert.equal(dialogAria(closeDialog(opened)), null);
  });

  it('keeps every dialog kind', () => {
    const kinds = ['briefing', 'combat', 'result', 'reward', 'confirm', 'alert'] as const;
    for (const kind of kinds) {
      const state = openDialog(CLOSED_DIALOG, kind, kind, kind);
      assert.equal(state.dialog?.kind, kind);
    }
  });
});

describe('the feedback model', () => {
  it('maps a success and a refusal to distinct messages with the refusal reason', () => {
    const outcomes = [
      { index: 0, ok: true, result: { kind: 'none' } },
      {
        index: 1,
        ok: false,
        error: { code: 'insufficient-resources', message: 'Not enough wood', status: 402 },
      },
    ];
    const messages = feedbackFrom(outcomes, false);
    assert.equal(messages.length, 2);
    assert.equal(messages[0]!.tone, 'success');
    assert.equal(messages[1]!.tone, 'error');
    assert.match(messages[0]!.text, /0/);
    assert.match(messages[1]!.text, /Not enough wood/);
    assert.match(messages[1]!.text, /insufficient-resources/);
  });

  it('still reports a refusal when the answer carries no outcomes', () => {
    const messages = feedbackFrom([], false);
    assert.equal(messages.length, 1);
    assert.equal(messages[0]!.tone, 'error');
    assert.match(messages[0]!.text, /refused/i);
  });

  it('says nothing when an empty batch succeeds', () => {
    assert.deepEqual(feedbackFrom([], true), []);
  });

  it('falls back to the typed code when there is no human message', () => {
    const messages = feedbackFrom(
      [{ index: 2, ok: false, error: { code: 'forbidden-command' } }],
      false,
    );
    assert.equal(messages[0]!.tone, 'error');
    assert.match(messages[0]!.text, /forbidden-command/);
  });

  it('trusts a refused outcome even when the response claims success', () => {
    const messages = feedbackFrom(
      [{ index: 3, ok: false, error: { code: 'command-failed', message: 'The attack failed' } }],
      true,
    );
    assert.equal(messages.length, 1);
    assert.equal(messages[0]!.tone, 'error');
    assert.match(messages[0]!.text, /The attack failed/);
  });

  it('does not mutate the outcomes it reads', () => {
    const outcomes = [
      { index: 0, ok: true, result: { kind: 'none' } },
      { index: 1, ok: false, error: { code: 'invalid-argument', message: 'Bad id' } },
    ];
    feedbackFrom(outcomes, false);
    assert.equal(outcomes.length, 2);
    assert.equal(outcomes[1]!.error?.message, 'Bad id');
  });
});
