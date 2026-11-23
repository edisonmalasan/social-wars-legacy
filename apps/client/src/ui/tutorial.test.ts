/**
 * The tutorial's presentation contract.
 *
 * The step list, its position and the Next/Skip callbacks all come from the
 * server-driven model; this file only checks the drawing: a white speech
 * bubble with a CSS tail, a bold blue title, reachable controls and no new
 * geometry or art assets.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

function source(name: string): string {
  return readFileSync(path.join(process.cwd(), 'apps/client/src/ui', name), 'utf8');
}

const css = source('css.ts');
const tutorial = source('tutorial.tsx');

/** A declaration from the shared token block. */
function token(name: string): string {
  const root = /:root\s*\{([^}]*)\}/.exec(css);
  assert.ok(root, 'the shared token block is missing');
  const match = new RegExp(`${name}:\\s*([^;]+);`).exec(root![1]!);
  assert.ok(match, `${name} token is missing`);
  return match![1]!.trim();
}

/** The bodies of the stylesheet rules with this selector. */
function rules(selector: string): string[] {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))].map(
    (match) => match[1]!,
  );
}

/** The body of one stylesheet rule, by exact selector. */
function rule(selector: string): string {
  const bodies = rules(selector);
  assert.ok(bodies.length > 0, `${selector} has no stylesheet rule`);
  return bodies[0]!;
}

describe('the tutorial speech bubble', () => {
  it('fills the box with the white bubble token', () => {
    assert.equal(token('--swl-bubble'), '#ffffff');
    assert.match(rule('.swl-tutorial-bubble'), /background:\s*var\(--swl-bubble\)/);
  });

  it('draws the tail in CSS, with no image asset', () => {
    const outlines = rules('.swl-tutorial-bubble::before');
    const tails = rules('.swl-tutorial-bubble::after');
    assert.match(
      outlines.find((body) => /border-bottom/.test(body)) ?? '',
      /border-bottom:\s*\d+px solid var\(--swl-ochre\)/,
    );
    assert.ok(
      tails.some((body) => /content:\s*['"]{2}/.test(body)),
      'the tail pseudo-element has no generated content',
    );
    assert.match(
      tails.find((body) => /border-bottom/.test(body)) ?? '',
      /border-bottom:\s*\d+px solid var\(--swl-bubble\)/,
    );
    assert.doesNotMatch(tutorial, /<img\b|url\(/);
  });

  it('sets a bold blue title and dark body ink on the white fill', () => {
    assert.match(
      rule('.swl-tutorial-bubble .swl-tutorial-title'),
      /color:\s*var\(--swl-bubble-title\)/,
    );
    assert.match(
      rule('.swl-tutorial-bubble .swl-tutorial-title'),
      /font-weight:\s*(?:bold|[7-9]00)/,
    );
    const title = token('--swl-bubble-title').replace('#', '');
    const red = parseInt(title.slice(0, 2), 16);
    const green = parseInt(title.slice(2, 4), 16);
    const blue = parseInt(title.slice(4, 6), 16);
    assert.ok(blue > red * 1.5 && blue > green * 1.5, 'the title colour is blue');
    assert.match(
      rule('.swl-tutorial-bubble .swl-tutorial-lesson'),
      /color:\s*var\(--swl-bubble-ink\)/,
    );
  });

  it('keeps Next and Skip reachable with a visible focus ring', () => {
    for (const button of ['next', 'skip']) {
      assert.match(
        rule(`.swl-tutorial-bubble .swl-tutorial-${button}:focus-visible`),
        /outline:\s*2px solid/,
      );
    }
    assert.match(tutorial, /className="swl-tutorial-next" onClick=\{onNext\}/);
    assert.match(tutorial, /className="swl-tutorial-skip" onClick=\{onSkip\}/);
  });

  it('keeps the server-driven step contract and the existing stage geometry', () => {
    assert.match(tutorial, /export interface TutorialOverlayProps/);
    for (const prop of [
      'step: TutorialStep',
      'position: number',
      'total: number',
      'onNext: () => void',
      'onSkip?: () => void',
    ]) {
      assert.ok(tutorial.includes(prop), `${prop} changed`);
    }
    assert.match(tutorial, /className="swl-tutorial-box swl-tutorial-bubble"/);
    assert.match(tutorial, /STEP \{position\} OF \{total\}/);
    assert.match(tutorial, /className="swl-tutorial-title"/);
    assert.match(rule('.swl-tutorial-box'), /width:\s*286px/);
    assert.match(rule('.swl-tutorial'), /z-index:\s*20/);
    assert.doesNotMatch(tutorial, /Date\.now|Math\.random|fetch\(/);
  });
});
