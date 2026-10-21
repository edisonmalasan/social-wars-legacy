import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { CLIENT_FONTS, FONT_SUBSTITUTES } from '@swl/client';

import { applyFontScales, clientCss, fontFaceCss, fontStack } from './fonts.ts';

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
      // The file is named the way the client's own model names it, so
      // the stylesheet and the model agree on what is fetched.
      assert.ok(
        css.includes(`url("/fonts/${file}-${font}.woff2")`),
        `no url for ${file}`,
      );
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

  it('starts the scales at the not-tuned-yet value', () => {
    const css = clientCss('/fonts');
    assert.ok(css.includes('--swl-font-scale-body: 1'), css);
    assert.ok(css.includes('--swl-font-scale-display: 1'), css);
  });
});

describe('the measured scale', () => {
  function fakeElement() {
    const set: Record<string, string> = {};
    return {
      set,
      target: {
        style: {
          setProperty: (name: string, value: string) => {
            set[name] = value;
          },
        },
      },
    };
  }

  it('is applied to the variable each face uses', () => {
    const { set, target } = fakeElement();
    applyFontScales({ scales: { ArialRoundedBold: 1.0183, KomikaAxis: 0.7344 } }, target);
    assert.equal(set['--swl-font-scale-body'], '1.0183');
    assert.equal(set['--swl-font-scale-display'], '0.7344');
  });

  it('leaves a face alone when it has no measured scale', () => {
    const { set, target } = fakeElement();
    applyFontScales({ scales: { ArialRoundedBold: 1.0183 } }, target);
    assert.equal(set['--swl-font-scale-body'], '1.0183');
    assert.equal(set['--swl-font-scale-display'], undefined);
  });

  it('leaves a scale that is not a number alone', () => {
    const { set, target } = fakeElement();
    applyFontScales(
      { scales: { ArialRoundedBold: Number.NaN, KomikaAxis: 0 } },
      target,
    );
    assert.equal(set['--swl-font-scale-body'], undefined);
    assert.equal(set['--swl-font-scale-display'], undefined);
  });
});
