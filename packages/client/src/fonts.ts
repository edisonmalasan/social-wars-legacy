/**
 * The text metrics.
 *
 * The game fits its text into boxes, and the boxes were sized for the
 * **original** fonts: Arial Rounded MT Bold and Komika Axis, both
 * proprietary. The clone substitutes open-licensed faces, and the
 * substituted face has to be **scaled** so the text occupies the same
 * width and the game's layout still fits.
 *
 * So the metrics the client uses are the ORIGINAL advance widths, scaled.
 * The originals are measured in `re/data/fonts.json` — the advance width
 * of every printable ASCII character, in the font's own design units —
 * and the scale is the ratio between the substitute's advance width and
 * the original's, measured once against the real font files.
 *
 * The scale is a **parameter**, not a constant baked in here, because it
 * depends on which font file is actually shipped. A scale of 1 means "not
 * tuned yet", and the roadmap says so.
 */

/** The font faces the client uses. */
export const CLIENT_FONTS = ['ArialRoundedBold', 'KomikaAxis'] as const;

export type ClientFont = (typeof CLIENT_FONTS)[number];

/** The open-licensed face that replaces a proprietary one. */
export interface FontSubstitute {
  /** The face's name. */
  name: string;
  /** Its licence. */
  licence: string;
  /** Where to get it. */
  url: string;
  /** Why this face. */
  note: string;
}

/** The substitutes. */
export const FONT_SUBSTITUTES: Record<ClientFont, FontSubstitute> = {
  ArialRoundedBold: {
    name: 'Nunito',
    licence: 'SIL Open Font License 1.1',
    url: 'https://fonts.google.com/specimen/Nunito',
    note:
      'A rounded, heavy geometric sans, the closest open-licensed match for ' +
      'Arial Rounded MT Bold. The substitute is scaled to match the original ' +
      "advance widths rather than used at its own size, so the game's text " +
      'fits the same boxes.',
  },
  KomikaAxis: {
    name: 'Rubik Mono One',
    licence: 'SIL Open Font License 1.1',
    url: 'https://fonts.google.com/specimen/Rubik+Mono+One',
    note:
      'A wide, display-oriented face, matching the game title and heading ' +
      "style. The Komika Axis face is used only for headings and large " +
      'labels, so the substitution affects a small part of the interface.',
  },
};

/** The metrics of one face. */
export interface FontMetrics {
  /** The face's name. */
  family: string;
  /** The design units per em. */
  unitsPerEm: number;
  /** The advance width of each character, in design units. */
  advances: Record<string, number>;
  /** The typographic ascender, in design units. */
  ascender: number;
  /** The typographic descender, in design units. (negative) */
  descender: number;
}

/** The metrics of the original faces, from `re/data/fonts.json`. */
export interface OriginalFontMetrics {
  [font: string]: FontMetrics;
}

/**
 * The width of a string, in design units.
 *
 * A character with no measured advance - one the font does not cover -
 * counts as **zero**, which is what the client's own text layout does
 * with a missing glyph.
 */
export function measure(
  metrics: FontMetrics,
  text: string,
  scale = 1,
): number {
  let width = 0;
  for (const char of text) {
    width += metrics.advances[char] ?? 0;
  }
  return width * scale;
}

/**
 * The width of a string in **pixels**, at a size in points.
 *
 * The design units are scaled to the point size and then by the
 * substitute's own scale factor.
 */
export function measurePixels(
  metrics: FontMetrics,
  text: string,
  sizePoints: number,
  scale = 1,
): number {
  return (measure(metrics, text, scale) * sizePoints) / metrics.unitsPerEm;
}

/**
 * The scale a substitute needs.
 *
 * It is the ratio between the substitute's advance width and the
 * original's, so the text occupies the same space. A scale of 1 means the
 * substitute has not been tuned yet, and the roadmap says so.
 */
export function scaleFor(originalWidth: number, substituteWidth: number): number {
  if (originalWidth === 0) return 1;
  return originalWidth / substituteWidth;
}

/**
 * The fonts the client loads, and where each one comes from.
 *
 * The client's own `FontsLoader` builds the URL as
 * `<dir>/<lang>_<font>.swf`, and the clone's fonts are **web fonts**,
 * so the name is enough.
 */
export interface LoadedFont {
  /** The name the client asks for. */
  name: ClientFont;
  /** The face that answers. */
  substitute: FontSubstitute;
  /** The file the face is served from. */
  file: string;
}

/** The fonts the client loads. */
export function loadedFonts(base = '/assets/fonts/'): LoadedFont[] {
  return CLIENT_FONTS.map((name) => ({
    name,
    substitute: FONT_SUBSTITUTES[name],
    file: `${base}${FONT_SUBSTITUTES[name].name.replace(/\s+/g, '')}-${name}.woff2`,
  }));
}

/**
 * The resources the fonts come from.
 *
 * The two faces are recorded per language in the client, and only the
 * English ones ship; the Turkish and Greek variants are missing, and the
 * client falls back. So the clone ships one set and falls back the same
 * way.
 */
export const FONT_LANGUAGES = ['en'] as const;

/** The languages the client's fonts exist in. */
export const CLIENT_FONT_LANGUAGES = ['en', 'tr', 'el'] as const;

/**
 * Whether a language's fonts are available.
 *
 * The client loads fonts for English, Turkish and Greek, but only the
 * English ones ship - the Turkish and Greek variants are missing, and the
 * client falls back. So the clone ships one set and falls back the same
 * way.
 */
export function hasFontsFor(language: string): boolean {
  return (FONT_LANGUAGES as readonly string[]).includes(language);
}
