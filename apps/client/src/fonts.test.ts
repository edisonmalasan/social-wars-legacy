import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { CLIENT_FONTS, FONT_SUBSTITUTES } from '@swl/client';

import { clientCss, fontFaceCss, fontStack } from './fonts.ts';

describe("the client's fonts", () => {
  it('uses the substitutes, never the proprietary faces', () => {
    for (const font of CLIENT_FONTS) {
      const stack = fontStack(font);
      assert.ok(
        !/arial|komika/i.test(stack),
        `the stack names a proprietary face: ${stack}`,
      );
    }
  });

  it('puts the substitute first and the fallback after', () => {
    const stack = fontStack('ArialRoundedBold');
    assert.ok(stack.startsWith('"Nunito"'), stack);
    assert.ok(stack.includes('system-ui'), stack);
  });

  it('names the display font for the headings', () => {
    const stack = fontStack('KomikaAxis');
    assert.ok(stack.startsWith('"RubikMonoOne"'), stack);
  });

  it('declares a face for each of the client fonts', () => {
    const css = fontFaceCss('/fonts');
    for (const font of CLIENT_FONTS) {
      const substitute = FONT_SUBSTITUTES[font];
      const file = substitute.name.replace(/\s+/g, '');
      assert.ok(css.includes(`font-family: "${file}"`), `no face for ${file}`);
      assert.ok(css.includes(`url("/fonts/${file}.woff2")`), `no url for ${file}`);
    }
  });

  it('swaps the face rather than blocking on it', () => {
    // `font-display: swap` means the text appears with the fallback and
    // is re-laid out when the face arrives, rather than the page being
    // invisible until then.
    const css = fontFaceCss('/fonts');
    assert.equal((css.match(/font-display: swap/g) ?? []).length, CLIENT_FONTS.length);
  });

  it('sets the two stacks the game uses', () => {
    const css = clientCss('/fonts');
    assert.ok(css.includes('--swl-font-body: "Nunito"'), css);
    assert.ok(css.includes('--swl-font-display: "RubikMonoOne"'), css);
  });
});
