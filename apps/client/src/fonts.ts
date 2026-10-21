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
 * The `url()` source comes **first**, so the face that ships is the
 * face that is used: the scale is measured against that file, and a
 * face the player happens to have installed would be a different one.
 * The `local()` source is the fallback, for a player who would rather
 * not download it.
 *
 * The `font-display: swap` means the text appears with the fallback and
 * is re-laid out when the face arrives, rather than the page being
 * invisible until then.
 */
export function fontFaceCss(baseUrl: string): string {
  return CLIENT_FONTS.map((font) => {
    const substitute = FONT_SUBSTITUTES[font];
    const file = substitute.name.replace(/\s+/g, '');
    return [
      '@font-face {',
      `  font-family: "${file}";`,
      '  font-display: swap;',
      `  src: url("${baseUrl}/${file}-${font}.woff2") format("woff2"), local("${substitute.name}");`,
      '}',
    ].join('\n');
  }).join('\n\n');
}

/**
 * The CSS variable each client's font's scale goes into.
 *
 * The two faces are used for different things — the body face for the
 * interface and the display face for the headings — so each has its own
 * scale.
 */
export const FONT_SCALE_VARIABLES: Record<ClientFont, string> = {
  ArialRoundedBold: '--swl-font-scale-body',
  KomikaAxis: '--swl-font-scale-display',
};

/**
 * The stylesheet the client loads.
 *
 * It declares the faces and sets the two **stacks** the game uses: the
 * body font for the interface and the display font for the headings.
 *
 * The two **scales** start at 1 — the "not tuned yet" value — and the
 * client sets them from the measured file, so the substitute's text
 * occupies the same width as the original's did.
 */
export function clientCss(baseUrl = '/fonts'): string {
  return [
    fontFaceCss(baseUrl),
    '',
    ':root {',
    '  --swl-font-body: "Nunito", system-ui, sans-serif;',
    '  --swl-font-display: "RubikMonoOne", system-ui, sans-serif;',
    '  --swl-font-scale-body: 1;',
    '  --swl-font-scale-display: 1;',
    '}',
  ].join('\n');
}

/**
 * The measured scales, as the client reads them.
 *
 * The file is written by `scripts/fetch-fonts.mjs`, which measures the
 * file that actually ships against the original's advance widths.
 */
export interface FontScaleFile {
  /** What the file is. */
  note?: string;
  /** The scale for each client font, by the font's name. */
  scales: Partial<Record<ClientFont, number>>;
}

/**
 * Apply the measured scales.
 *
 * A scale that is missing or is not a number is **left alone**, so the
 * stylesheet's own "not tuned yet" value of 1 stands: the text is a
 * little narrower than the original's, and the game still reads.
 */
export function applyFontScales(
  file: FontScaleFile,
  target: { style: { setProperty: (name: string, value: string) => void } },
): void {
  for (const [font, variable] of Object.entries(FONT_SCALE_VARIABLES)) {
    const scale = file.scales?.[font as ClientFont];
    if (typeof scale !== 'number' || !Number.isFinite(scale) || scale <= 0) continue;
    target.style.setProperty(variable, String(scale));
  }
}
