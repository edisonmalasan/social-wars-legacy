#!/usr/bin/env node
/**
 * Group D — the embedded sounds.
 *
 * `assets/sounds/` holds 140 standalone MP3s, and the config's `sounds` list
 * points at 139 of them. But the client also carries audio *inside* a SWF:
 * `assets/swf/dynamic2.swf` embeds 27 sound classes, each with an
 * `[Embed(source="/_assets/N_Name.mp3")]` attribute, and the audio is baked
 * into the SWF as `DefineSound` tags.
 *
 * Those 27 are NOT in the server's config, and they are not the same
 * recordings as the standalone files. So the audio set is bigger than the
 * config suggests, and the extra sounds are only recoverable from the SWF.
 *
 * This script extracts them and records what is genuinely new.
 *
 * Usage:
 *   node scripts/extract-embedded-sounds.mjs
 */
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'upstream/socialwarriors/assets');
const SOUNDS = path.join(ASSETS, 'sounds');
const WORK = path.join(ROOT, '.work/sounds');
const OUT = path.join(ROOT, 're/data/embedded-sounds.json');

const DEFAULT_FFDEC =
  process.env.FF_DEC ||
  'C:/Users/Edison/AppData/Local/Temp/opencode/socialwarriors/tools/ffdec/ffdec-cli.exe';

/** The SWFs that carry audio. */
const SOURCES = ['swf/dynamic2.swf'];

const sha = (buffer) => createHash('sha256').update(buffer).digest('hex');

async function main() {
  if (!existsSync(DEFAULT_FFDEC)) {
    console.error(`FFDec not found at ${DEFAULT_FFDEC}`);
    process.exit(2);
  }
  await mkdir(WORK, { recursive: true });

  // 1. The standalone sounds, hashed.
  const standalone = new Map();
  for (const name of await readdir(SOUNDS)) {
    if (!name.toLowerCase().endsWith('.mp3') && !name.toLowerCase().endsWith('.wav')) continue;
    const buffer = await readFile(path.join(SOUNDS, name));
    standalone.set(sha(buffer), { name, bytes: buffer.length });
  }
  console.log(`${standalone.size} standalone sounds in assets/sounds/`);

  // 2. Extract the embedded ones.
  const embedded = [];
  for (const source of SOURCES) {
    const swf = path.join(ASSETS, source);
    if (!existsSync(swf)) continue;
    const outDir = path.join(WORK, source.replace(/\//g, '_').replace(/\.swf$/, ''));
    await rm(outDir, { recursive: true, force: true });
    await mkdir(outDir, { recursive: true });

    console.log(`extracting the sounds from ${source} ...`);
    await execFileAsync(DEFAULT_FFDEC, ['-export', 'sound', outDir, swf], {
      cwd: ROOT,
      timeout: 300_000,
      maxBuffer: 32 * 1024 * 1024,
    });

    for (const name of await readdir(outDir)) {
      const buffer = await readFile(path.join(outDir, name));
      const hash = sha(buffer);
      const duplicate = standalone.get(hash);
      embedded.push({
        source,
        name,
        bytes: buffer.length,
        sha256: hash,
        // The embed names look like "21_BuildSound.mp3": the number is the
        // sound id the runtime library uses.
        id: /^(\d+)_/.exec(name)?.[1] ? Number(/^(\d+)_/.exec(name)[1]) : null,
        className: name.replace(/^\d+_/, '').replace(/\.(mp3|wav)$/i, ''),
        duplicatesStandalone: duplicate ? duplicate.name : null,
      });
    }
  }

  embedded.sort((a, b) => (a.id ?? 0) - (b.id ?? 0) || a.name.localeCompare(b.name));

  const unique = embedded.filter((e) => e.duplicatesStandalone === null);
  const duplicates = embedded.filter((e) => e.duplicatesStandalone !== null);

  // 3. The config's sounds, for the comparison.
  const config = JSON.parse(
    await readFile(path.join(ROOT, 'upstream/socialwarriors/config/main.json'), 'utf8'),
  );
  const configFiles = new Set((config.sounds ?? []).map((s) => s.file));
  const notInConfig = unique.filter((e) => !configFiles.has(e.className.toLowerCase()));

  const result = {
    note:
      'The audio embedded in the client SWFs, extracted and compared with the ' +
      'standalone files in assets/sounds/. These sounds are NOT in the server ' +
      "config's sounds list, and they are not duplicates of the standalone " +
      'files, so the audio set is larger than the config suggests.',
    counts: {
      standaloneSounds: standalone.size,
      embeddedSounds: embedded.length,
      embeddedUnique: unique.length,
      embeddedDuplicatingAStandaloneFile: duplicates.length,
      embeddedNotNamedInTheConfig: notInConfig.length,
    },
    embedded,
    summary: {
      uniqueNames: unique.map((e) => e.className),
      notInConfig: notInConfig.map((e) => e.className),
    },
  };

  await writeFile(OUT, JSON.stringify(result, null, 1) + '\n', 'utf8');

  console.log('');
  console.log(`standalone sounds       : ${result.counts.standaloneSounds}`);
  console.log(`embedded sounds        : ${result.counts.embeddedSounds}`);
  console.log(`  unique to the SWF    : ${result.counts.embeddedUnique}`);
  console.log(`  duplicating a file   : ${result.counts.embeddedDuplicatingAStandaloneFile}`);
  console.log(`  not named in config  : ${result.counts.embeddedNotNamedInTheConfig}`);
  console.log(`\nwrote ${OUT}`);
  console.log(`extracted files: ${WORK}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
