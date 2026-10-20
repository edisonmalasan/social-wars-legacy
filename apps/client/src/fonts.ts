/**
 * The client's fonts.
 *
 * The game's two faces — Arial Rounded MT Bold and Komika Axis — are
 * proprietary, so the client uses **Nunito** and **Rubik Mono One**
 * instead, both under the SIL Open Font License 1.1.
 *
 * The substitution is not a swap. The game's layout was sized for the
 * **original** fonts' metrics, so the substitute is **scaled** to occupy
 * the same width, and the text still fits its boxes. The scale is
 * measured against the real font files, and it is a parameter rather
 * than a constant, because it depends on which file actually ships.
 *
 * The faces themselves are **not** in the repository: they are fetched
 * at build time, and the client's stylesheet names them. The fallback is
 * the platform's own UI font, so the game is playable if the fetch
 * fails — the layout shifts, but nothing breaks.
 */
import {
  FONT_SUBSTITUTES,
  CLIENT_FONTS,
  type ClientFont,
} from '@swl/client';

/** The CSS stack for a face, with the substitute first and the fallback after. */
export function fontStack(font: ClientFont, fallback = 'system-ui, sans-serif'): string {
  const substitute = FONT_SUBSTITUTES[font].name.replace(/\s+/g, '');
  return `"${substitute}", ${fallback}`;
}

/**
 * The `@font-face` rules.
 *
 * The `local()` source finds a face the player already has; the `url()`
 * source fetches it. The `font-display: swap` means the text appears
 * with the fallback and is re-laid out when the face arrives, rather
 * than the page being invisible until then.
 */
export function fontFaceCss(baseUrl: string): string {
  return CLIENT_FONTS.map((font) => {
    const substitute = FONT_SUBSTITUTES[font];
    const file = substitute.name.replace(/\s+/g, '');
    return [
      '@font-face {',
      `  font-family: "${file}";`,
      '  font-display: swap;',
      `  src: local("${substitute.name}"), url("${baseUrl}/${file}.woff2") format("woff2");`,
      '}',
    ].join('\n');
  }).join('\n\n');
}

/**
 * The stylesheet the client loads.
 *
 * It declares the faces and sets the two **stacks** the game uses: the
 * body font for the interface and the display font for the headings.
 */
export function clientCss(baseUrl = '/fonts'): string {
  return [
    fontFaceCss(baseUrl),
    '',
    ':root {',
    '  --swl-font-body: "Nunito", system-ui, sans-serif;',
    '  --swl-font-display: "RubikMonoOne", system-ui, sans-serif;',
    '}',
  ].join('\n');
}
