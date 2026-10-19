#!/usr/bin/env node
/**
 * Roadmap task B2 — the full SWF corpus.
 *
 * The vendored asset tree holds 1 176 SWF files. Most of them are pure vector art
 * (sprite timelines, FX, characters) and contain no ActionScript at all, so
 * decompiling all of them would waste hours to produce nothing. What the clone
 * actually needs is a *characterisation* of every file:
 *
 *   - is it art or code?
 *   - if code, which classes does it contain and how big is the ABC block?
 *   - if art, how many frames, what is the stage size, does it loop?
 *   - what is its SHA-256 (so the content bundle can reference it)
 *
 * This script parses the SWF container natively (no JVM, no decompiler) and emits
 * that census. Files that contain ActionScript are listed for the decompiler.
 *
 * Outputs:
 *   re/data/swf-corpus.json
 */
import { createHash } from 'node:crypto';
import { readFile, readdir, writeFile, mkdir, stat } from 'node:fs/promises';
import { inflateSync } from 'node:zlib';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'upstream/socialwarriors/assets');
const OUT = path.join(ROOT, 're/data');

/** SWF tag ids we care about. */
const TAGS = {
  0: 'End', 1: 'ShowFrame', 2: 'DefineShape', 4: 'PlaceObject', 5: 'RemoveObject',
  6: 'DefineBits', 7: 'DefineButton', 8: 'JPEGTables', 9: 'SetBackgroundColor',
  10: 'DefineFont', 11: 'DefineText', 12: 'DoAction', 13: 'DefineFontInfo',
  14: 'DefineSound', 17: 'DefineButtonSound', 20: 'DefineBitsLossless',
  21: 'DefineBitsJPEG2', 22: 'DefineShape2', 23: 'DefineButtonCxform', 24: 'Protect',
  26: 'PlaceObject2', 28: 'RemoveObject2', 32: 'DefineShape3', 33: 'DefineText2',
  34: 'DefineButton2', 35: 'DefineBitsLossless2', 36: 'DefineBitsJPEG3',
  37: 'DefineEditText', 39: 'DefineSprite', 43: 'FrameLabel', 46: 'DefineMorphShape',
  48: 'DefineFont2', 56: 'ExportAssets', 57: 'ImportAssets', 58: 'EnableDebugger',
  59: 'DoInitAction', 60: 'DefineVideoStream', 61: 'VideoFrame', 62: 'DefineFontInfo2',
  65: 'ScriptLimits', 69: 'FileAttributes', 70: 'PlaceObject3', 74: 'CSMTextSettings',
  75: 'DefineFont3', 76: 'SymbolClass', 77: 'Metadata', 82: 'DoABC', 83: 'DefineShape4',
  87: 'DefineBinaryData', 89: 'StartSound2', 91: 'DefineFont4', 93: 'EnableTelemetry',
  94: 'PlaceObject4',
};

function inflateIfNeeded(buf) {
  if (buf[0] === 0x43 && buf[1] === 0x57 && buf[2] === 0x53) {
    return Buffer.concat([Buffer.from(buf.subarray(0, 8)), inflateSync(buf.subarray(8))]);
  }
  return buf;
}

/** Parse the SWF header, RECT and the tag stream. */
function parseSwf(buf) {
  const signature = buf.toString('latin1', 0, 3);
  const version = buf[3];
  const declaredLength = buf.readUInt32LE(4);
  let off = 8;

  // RECT: the first 5 bits of the first byte are the bit count.
  const nbits = buf[8] >> 3;
  const rectBytes = Math.ceil((5 + 4 * nbits) / 8);
  const rect = buf.subarray(8, 8 + rectBytes);
  off = 8 + rectBytes;

  const frameRateRaw = buf.readUInt16LE(off);
  off += 2;
  const frameCount = buf.readUInt16LE(off);
  off += 2;

  const tagCounts = {};
  const abc = [];
  let frames = 0;
  let endTag = false;

  while (off + 2 <= buf.length) {
    const code = buf.readUInt16LE(off);
    off += 2;
    // RECORDHEADER: the tag id is the UPPER 10 bits, the length the LOWER 6.
    // A length of 0x3F means a UI32 length follows.
    let tagId = code >> 6;
    let length = code & 0x3f;
    if (length === 0x3f) {
      length = buf.readUInt32LE(off);
      off += 4;
    }
    const body = buf.subarray(off, off + length);
    off += length;

    const name = TAGS[tagId] ?? `Tag${tagId}`;
    tagCounts[name] = (tagCounts[name] ?? 0) + 1;
    if (tagId === 1) frames += 1;
    if (tagId === 82) {
      // DoABC: UI32 flags, a NUL-terminated name, then the ABC block.
      const nameEnd = body.indexOf(0, 4);
      const abcName = body.toString('utf8', 4, nameEnd);
      const abcStart = nameEnd + 1;
      abc.push({ name: abcName, bytes: body.length - abcStart, offset: abcStart });
    }
    if (tagId === 0) { endTag = true; break; }
  }

  return {
    signature,
    version,
    declaredLength,
    compressed: signature === 'CWS',
    stage: { nbits, rectBytes },
    frameRate: frameRateRaw / 256,
    frameCount,
    frames,
    tagCounts,
    tagTotal: Object.values(tagCounts).reduce((a, b) => a + b, 0),
    abc,
    hasActionScript: abc.length > 0,
    endTag,
  };
}

async function* walk(dir, rel = '') {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) yield* walk(p, r);
    else if (e.isFile() && e.name.endsWith('.swf')) yield r;
  }
}

async function main() {
  const files = [];
  for await (const rel of walk(ASSETS)) files.push(rel);
  files.sort();

  const entries = [];
  const withCode = [];
  for (const rel of files) {
    const abs = path.join(ASSETS, ...rel.split('/'));
    const raw = await readFile(abs);
    const info = await stat(abs);
    let parsed = null;
    let error = null;
    try {
      parsed = parseSwf(inflateIfNeeded(raw));
    } catch (e) {
      error = e.message;
    }
    const entry = {
      path: rel,
      bytes: info.size,
      sha256: createHash('sha256').update(raw).digest('hex'),
      ...(parsed
        ? {
            swfVersion: parsed.version,
            compressed: parsed.compressed,
            declaredLength: parsed.declaredLength,
            frameRate: Math.round(parsed.frameRate * 100) / 100,
            frameCount: parsed.frameCount,
            frames: parsed.frames,
            tagTotal: parsed.tagTotal,
            topTags: Object.entries(parsed.tagCounts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([k, v]) => ({ tag: k, count: v })),
            hasActionScript: parsed.hasActionScript,
            abcBlocks: parsed.abc.map((a) => ({ name: a.name, bytes: a.bytes })),
            // A sprite carries only an auto-generated MovieClip document class and
            // frame scripts. Anything under 4 KiB of ABC is that stub, not logic.
            codeClass: !parsed.hasActionScript
              ? 'none'
              : parsed.abc.reduce((n, a) => n + a.bytes, 0) < 4096
                ? 'stub'
                : 'real',
          }
        : { parseError: error }),
    };
    entries.push(entry);
    if (entry.hasActionScript) withCode.push(rel);
  }

  const byGroup = {};
  for (const e of entries) {
    const g = e.path.includes('/') ? e.path.slice(0, e.path.indexOf('/')) : '(root)';
    byGroup[g] = byGroup[g] ?? { files: 0, bytes: 0, stub: 0, real: 0, none: 0 };
    byGroup[g].files += 1;
    byGroup[g].bytes += e.bytes;
    byGroup[g][e.codeClass ?? 'none'] += 1;
  }

  const codeClassCounts = { none: 0, stub: 0, real: 0 };
  for (const e of entries) codeClassCounts[e.codeClass ?? 'none'] += 1;
  const realCode = entries.filter((e) => e.codeClass === 'real').map((e) => e.path);

  await mkdir(OUT, { recursive: true });
  await writeFile(
    path.join(OUT, 'swf-corpus.json'),
    JSON.stringify(
      {
        note:
          'Census of every SWF in the vendored asset tree, parsed natively from the ' +
          'container. codeClass: "real" = contains gameplay logic, "stub" = only an ' +
          'auto-generated MovieClip document class and frame scripts, "none" = no ABC.',
        counts: {
          swfFiles: entries.length,
          ...codeClassCounts,
          totalBytes: entries.reduce((n, e) => n + e.bytes, 0),
        },
        byGroup,
        filesWithRealCode: realCode,
        entries,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );

  console.log(`SWF files scanned        : ${entries.length}`);
  console.log(`  with real gameplay code: ${codeClassCounts.real}`);
  console.log(`  with a stub class only : ${codeClassCounts.stub}`);
  console.log(`  with no ActionScript   : ${codeClassCounts.none}`);
  console.log(`total bytes              : ${(entries.reduce((n, e) => n + e.bytes, 0) / 1048576).toFixed(1)} MB`);
  console.log('\nby group:');
  for (const [g, v] of Object.entries(byGroup)) {
    console.log(`  ${g.padEnd(14)} ${String(v.files).padStart(5)} files ${(v.bytes / 1048576).toFixed(1).padStart(7)} MB  real=${v.real} stub=${v.stub} none=${v.none}`);
  }
  console.log('\nfiles with real gameplay code:');
  for (const f of realCode.slice(0, 70)) console.log('  ', f);
  if (realCode.length > 70) console.log(`   ... and ${realCode.length - 70} more`);
  console.log('\nwrote re/data/swf-corpus.json');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
