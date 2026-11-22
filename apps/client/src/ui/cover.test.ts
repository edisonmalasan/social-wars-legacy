/**
 * The evidence behind the two cover entries in `re/data/ui-screens.json`.
 *
 * `GuiCover.as` and `GuiCoverExplorationMC.as` are art-only overlays in the
 * original client: neither has a method beyond its constructor. The clone
 * claims the behaviour with one reusable primitive and never claims the
 * proprietary artwork, so both decisions rest on the same drawn contract.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

function source(name: string): string {
  return readFileSync(path.join(process.cwd(), 'apps/client/src/ui', name), 'utf8');
}

describe('the reusable cover primitive', () => {
  const chrome = source('chrome.tsx');
  const css = source('css.ts');

  it('dims the surface it covers and dismisses on a click', () => {
    assert.match(chrome, /export function Cover\(/);
    assert.match(chrome, /className = 'swl-chrome-cover'/);
    assert.match(chrome, /onClick=\{onDismiss\}/);
    const rule = /\.swl-chrome-cover\s*\{([^}]*)\}/.exec(css);
    assert.ok(rule, 'the cover has no stylesheet rule');
    assert.match(rule![1]!, /inset:\s*0/);
    assert.match(rule![1]!, /var\(--swl-scrim\)/);
  });

  it('shares one dismissal shape with the chrome popover', () => {
    assert.match(chrome, /<Cover onDismiss=\{\(\) => setPopoverOpen\(false\)\} \/>/);
    assert.match(chrome, /event\.key !== 'Escape'/);
    assert.match(chrome, />\s*Got it\s*</);
  });

  it('has no exploration view that could claim an exploration screen', () => {
    // The exploration cover is recorded as the primitive, not as a rendered
    // exploration view: no such view exists in the clone, so no art is claimed.
    for (const name of ['chrome.tsx', 'state.ts', 'css.ts', 'root.tsx']) {
      assert.doesNotMatch(source(name), /exploration/i, `${name} claims an exploration view`);
    }
  });
});
