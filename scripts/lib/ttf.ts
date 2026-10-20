/**
 * A minimal TrueType parser.
 *
 * The client embeds two fonts as SWF font libraries, and the roadmap
 * requires the text metrics to be *tuned to match* the originals. That
 * needs the original metrics measured, not guessed, so the pipeline reads
 * them out of the extracted TTF.
 *
 * Only what the client needs is parsed: the units per em, the vertical
 * metrics, the character map, and the advance width of every glyph.
 */

/** The vertical metrics of a font. */
export interface FontMetrics {
  /** The design units per em. */
  unitsPerEm: number;
  /** The typographic ascender, in design units. */
  ascender: number;
  /** The typographic descender, in design units (negative). */
  descender: number;
  /** The line gap, in design units. */
  lineGap: number;
  /** The number of glyphs. */
  numGlyphs: number;
  /** The advance width per character, in design units. */
  advances: Map<string, number>;
  /** The font's family name, if it has one. */
  familyName: string | null;
  /** The font's full name. */
  fullName: string | null;
  /** The PostScript name. */
  postScriptName: string | null;
  /** The characters the font actually covers. */
  coveredCharacters: string[];
}

function u16(buffer, offset) {
  return buffer.readUInt16BE(offset);
}
function i16(buffer, offset) {
  return buffer.readInt16BE(offset);
}
function u32(buffer, offset) {
  return buffer.readUInt32BE(offset);
}

/** Parse the tables out of a TTF. */
function readTables(buffer) {
  if (buffer.length < 12) throw new Error('not a font');
  const tag = u32(buffer, 0);
  // 0x00010000 is TrueType outlines, 'true' is the older Apple format,
  // 'OTTO' is CFF outlines and 'ttcf' is a collection.
  if (tag !== 0x00010000 && tag !== 0x74727565 && tag !== 0x4f54544f && tag !== 0x74746366) {
    throw new Error(`unsupported font format 0x${tag.toString(16)}`);
  }
  const numTables = u16(buffer, 4);
  const tables = new Map();
  for (let i = 0; i < numTables; i++) {
    const record = 12 + i * 16;
    const name = buffer.toString('latin1', record, record + 4);
    tables.set(name, { offset: u32(buffer, record + 8), length: u32(buffer, record + 12) });
  }
  return tables;
}

/** The character map, as code point -> glyph id. */
function readCmap(buffer, table) {
  const map = new Map();
  const base = table.offset;
  const numTables = u16(buffer, base + 2);

  let best = null;
  for (let i = 0; i < numTables; i++) {
    const record = base + 4 + i * 8;
    const platform = u16(buffer, record);
    const encoding = u16(buffer, record + 2);
    const offset = base + u32(buffer, record + 4);
    const score =
      platform === 3 && encoding === 10 ? 5 : platform === 3 && encoding === 1 ? 4 : platform === 0 ? 3 : 0;
    if (score > 0 && (!best || score > best.score)) best = { offset, score };
  }
  if (!best) return map;

  const format = u16(buffer, best.offset);
  if (format === 4) {
    const segCountX2 = u16(buffer, best.offset + 6);
    const segCount = segCountX2 / 2;
    const endCodes = best.offset + 14;
    const startCodes = endCodes + segCountX2 + 2;
    const idDeltas = startCodes + segCountX2;
    const idRangeOffsets = idDeltas + segCountX2;
    for (let s = 0; s < segCount; s++) {
      const end = u16(buffer, endCodes + s * 2);
      const start = u16(buffer, startCodes + s * 2);
      const delta = i16(buffer, idDeltas + s * 2);
      const rangeOffset = u16(buffer, idRangeOffsets + s * 2);
      if (start > end) continue;
      for (let code = start; code <= end && code !== 0xffff; code++) {
        let glyph;
        if (rangeOffset === 0) {
          glyph = (code + delta) & 0xffff;
        } else {
          const glyphIndexAddress = idRangeOffsets + s * 2 + rangeOffset + (code - start) * 2;
          glyph = u16(buffer, glyphIndexAddress);
          if (glyph !== 0) glyph = (glyph + delta) & 0xffff;
        }
        if (glyph !== 0) map.set(code, glyph);
      }
    }
  } else if (format === 12) {
    const nGroups = u32(buffer, best.offset + 12);
    for (let g = 0; g < nGroups; g++) {
      const group = best.offset + 16 + g * 12;
      const startChar = u32(buffer, group);
      const endChar = u32(buffer, group + 4);
      const startGlyph = u32(buffer, group + 8);
      for (let code = startChar; code <= endChar; code++) {
        map.set(code, startGlyph + (code - startChar));
      }
    }
  }
  return map;
}

/** The advance widths, by glyph id. */
function readHmtx(buffer, tables, numGlyphs, numberOfHMetrics) {
  const advances = [];
  const hmtx = tables.get('hmtx');
  if (!hmtx) return advances;
  for (let i = 0; i < numberOfHMetrics; i++) {
    advances.push(u16(buffer, hmtx.offset + i * 4));
  }
  // The remaining glyphs reuse the last advance.
  const last = advances.length > 0 ? advances[advances.length - 1]! : 0;
  while (advances.length < numGlyphs) advances.push(last);
  return advances;
}

/** The font's names. */
function readNames(buffer, tables) {
  const names = new Map();
  const name = tables.get('name');
  if (!name) return names;
  const count = u16(buffer, name.offset + 2);
  const stringOffset = name.offset + u16(buffer, name.offset + 4);
  for (let i = 0; i < count; i++) {
    const record = name.offset + 6 + i * 12;
    const platform = u16(buffer, record);
    const encoding = u16(buffer, record + 2);
    const language = u16(buffer, record + 4);
    const nameId = u16(buffer, record + 6);
    const length = u16(buffer, record + 8);
    const offset = u16(buffer, record + 10);
    const start = stringOffset + offset;
    let value;
    if (platform === 3 || (platform === 0)) {
      // UTF-16BE
      value = Buffer.from(buffer.subarray(start, start + length)).swap16().toString('utf16le');
    } else {
      value = buffer.toString('latin1', start, start + length);
    }
    if (!names.has(nameId) || (platform === 3 && language === 0x409)) {
      names.set(nameId, value);
    }
  }
  return names;
}

/** Read a font's metrics. */
export function parseFont(buffer) {
  const tables = readTables(buffer);

  const head = tables.get('head');
  const hhea = tables.get('hhea');
  const maxp = tables.get('maxp');
  if (!head || !hhea || !maxp) throw new Error('the font is missing a required table');

  const unitsPerEm = u16(buffer, head.offset + 18);
  const ascender = i16(buffer, hhea.offset + 4);
  const descender = i16(buffer, hhea.offset + 6);
  const lineGap = i16(buffer, hhea.offset + 8);
  const numberOfHMetrics = u16(buffer, hhea.offset + 34);
  const numGlyphs = u16(buffer, maxp.offset + 4);

  const cmap = readCmap(buffer, tables.get('cmap'));
  const glyphAdvances = readHmtx(buffer, tables, numGlyphs, numberOfHMetrics);
  const names = readNames(buffer, tables);

  const advances = new Map();
  const covered = [];
  for (const [code, glyph] of cmap) {
    const advance = glyphAdvances[glyph];
    if (advance === undefined) continue;
    advances.set(String.fromCodePoint(code), advance);
    covered.push(String.fromCodePoint(code));
  }
  covered.sort();

  return {
    unitsPerEm,
    ascender,
    descender,
    lineGap,
    numGlyphs,
    advances,
    familyName: names.get(1) ?? null,
    fullName: names.get(4) ?? null,
    postScriptName: names.get(6) ?? null,
    coveredCharacters: covered,
  };
}
