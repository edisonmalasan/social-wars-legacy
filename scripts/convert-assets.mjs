#!/usr/bin/env node
/**
 * Group D â€” the asset converter.
 *
 * Turns the vendored SWF art into renderable, versioned images plus a frame
 * manifest.
 *
 * Three measurements shaped this design (see re/docs/17-asset-pipeline.md):
 *
 *  1. A sprite SWF is a *library* of nested `DefineSprite` timelines, not an
 *     animation. The 862 sprites have a median of ONE top-level frame, so
 *     `-export frame` would throw the art away. The export mode is
 *     `-export sprite`, which flattens every nested timeline.
 *
 *  2. FFDec accepts a **directory** as input, so one JVM invocation converts a
 *     whole group. A per-file invocation costs ~6 s of JVM startup for a
 *     ~1 s export, which would be 2 hours of pure startup for 1 116 files.
 *     The converter therefore splits a group into N chunks and runs N JVMs at
 *     once.
 *
 *  3. The frames are mostly duplicates: a 43 KB sprite exported to 170 PNGs
 *     contains only **12** distinct images, because an animation holds each
 *     frame for many ticks. So the converter deduplicates by content hash
 *     into a content-addressed store, and the manifest maps
 *     (swf, symbol, frame) to a stored image.
 *
 * Usage:
 *   node scripts/convert-assets.mjs                        # every group
 *   node scripts/convert-assets.mjs --group sprites
 *   node scripts/convert-assets.mjs --limit 40 --jobs 6    # a sample
 *
 * Requires FFDec. Set FF_DEC to the path of ffdec-cli.exe, or leave it at the
 * default install location used during the investigation.
 */
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFile, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'upstream/socialwarriors/assets');
const WORK = path.join(ROOT, '.work/frames');
const STORE = path.join(WORK, 'store');
const CHUNKS = path.join(WORK, 'chunks');
const OUT = path.join(ROOT, 're/data');

const DEFAULT_FFDEC =
  process.env.FF_DEC ||
  'C:/Users/Edison/AppData/Local/Temp/opencode/socialwarriors/tools/ffdec/ffdec-cli.exe';

/** The asset groups, in the order the roadmap lists them. */
const GROUPS = ['sprites', 'fx', 'characters_2', 'magic', 'images', 'externalized', 'swf', 'fonts'];

function parseArgs(argv) {
  const args = {
    groups: GROUPS,
    limit: Infinity,
    jobs: 6,
    out: path.join(ROOT, 're/data/frame-manifest.json'),
    noResume: false,
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--group') args.groups = [argv[++i]];
    else if (argv[i] === '--limit') args.limit = Number(argv[++i]);
    else if (argv[i] === '--jobs') args.jobs = Number(argv[++i]);
    else if (argv[i] === '--out') args.out = path.resolve(argv[++i]);
    else if (argv[i] === '--no-resume') args.noResume = true;
  }
  return args;
}

/** The width and height from a PNG's IHDR chunk. */
function pngSize(buffer) {
  if (buffer.length < 24 || buffer.readUInt32BE(0) !== 0x89504e47) return null;
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

/** Remove a directory, tolerating a file that is still locked by a dying process. */
async function removeDir(dir) {
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      await rm(dir, { recursive: true, force: true, maxRetries: 3, retryDelay: 250 });
      return;
    } catch (error) {
      if (attempt === 4) {
        console.warn(`  ! could not remove ${dir}: ${error.code ?? error.message}`);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
    }
  }
}

/** Run a bounded number of tasks at once. */
async function pool(items, limit, worker) {
  const results = new Array(items.length);
  let next = 0;
  const runners = Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, async () => {
    for (;;) {
      const index = next++;
      if (index >= items.length) return;
      results[index] = await worker(items[index], index);
    }
  });
  await Promise.all(runners);
  return results;
}

async function listSwf(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const name of await readdir(dir)) {
    if (name.endsWith('.swf')) out.push(name);
  }
  return out.sort();
}

/** Split a list into N roughly equal chunks. */
function chunk(items, n) {
  const size = Math.max(1, Math.ceil(items.length / n));
  const out = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!existsSync(DEFAULT_FFDEC)) {
    console.error(`FFDec not found at ${DEFAULT_FFDEC}`);
    console.error('Set FF_DEC to the path of ffdec-cli.exe.');
    process.exit(2);
  }

  await mkdir(STORE, { recursive: true });
  await mkdir(CHUNKS, { recursive: true });
  await mkdir(path.dirname(args.out), { recursive: true });

  // 0. Resume. A conversion of the whole corpus takes a while, and it may be
  //    interrupted. The manifest is the record of what has been done, so an
  //    existing manifest is loaded and the SWFs it already covers are skipped.
  //    The store is content-addressed, so re-running is cheap and safe.
  const symbols = [];
  const uniqueStore = new Map();
  let pngTotal = 0;
  let bytesTotal = 0;
  const doneSwf = new Set();

  if (!args.noResume && existsSync(args.out)) {
    try {
      const previous = JSON.parse(await readFile(args.out, 'utf8'));
      for (const symbol of previous.symbols ?? []) {
        symbols.push(symbol);
        doneSwf.add(symbol.swf);
      }
      for (const [hash, image] of Object.entries(previous.images ?? {})) {
        uniqueStore.set(hash, image);
        bytesTotal += image.bytes ?? 0;
      }
      pngTotal = previous.counts?.pngFrames ?? 0;
      console.log(
        `resuming: ${doneSwf.size} SWF files and ${uniqueStore.size} images already in ${args.out}`,
      );
    } catch (error) {
      console.warn(`  ! could not read the existing manifest, starting fresh: ${error.message}`);
    }
  }

  // 1. Build the chunk list: each chunk is a directory of SWFs that one JVM
  //    invocation will convert.
  const jobs = [];
  let skipped = 0;
  for (const group of args.groups) {
    const dir = path.join(ASSETS, group);
    const all = await listSwf(dir);
    const names = [];
    for (const name of all) {
      if (doneSwf.has(`${group}/${name}`)) {
        skipped += 1;
        continue;
      }
      names.push(name);
    }
    const limited = names.slice(0, Math.max(0, args.limit - skipped));
    const perChunk = Math.max(1, Math.ceil(limited.length / args.jobs));
    for (let i = 0; i < limited.length; i += perChunk) {
      jobs.push({ group, names: limited.slice(i, i + perChunk) });
    }
  }
  const todo = jobs.reduce((n, j) => n + j.names.length, 0);
  console.log(
    `converting ${todo} SWF files in ${jobs.length} batches` +
      (skipped ? ` (${skipped} already done)` : ''),
  );
  console.log(`FFDec: ${DEFAULT_FFDEC}`);

  let done = 0;
  const started = Date.now();

  /**
   * Write the manifest. Called after every batch, so an interrupted run keeps
   * everything it has already converted and the next run resumes from there.
   */
  const writeManifest = async () => {
    symbols.sort((a, b) =>
      a.swf === b.swf ? a.symbol.localeCompare(b.symbol) : a.swf.localeCompare(b.swf),
    );
    const manifest = {
      note:
        'The asset conversion manifest. Every (swf, symbol, frame) maps to a ' +
        'content-addressed image in the frame store. Produced by ' +
        'scripts/convert-assets.mjs. The store itself is a build artefact.',
      groups: args.groups,
      counts: {
        swfFiles: new Set(symbols.map((s) => s.swf)).size,
        symbols: symbols.length,
        pngFrames: pngTotal,
        uniqueImages: uniqueStore.size,
        deduplicationRatio: pngTotal ? Number((uniqueStore.size / pngTotal).toFixed(4)) : 0,
        rawPngBytes: bytesTotal,
        storeBytes: [...uniqueStore.values()].reduce((n, u) => n + u.bytes, 0),
      },
      images: Object.fromEntries(uniqueStore),
      symbols,
    };
    await writeFile(args.out, JSON.stringify(manifest, null, 1) + '\n', 'utf8');
    return manifest;
  };

  // 2. Convert each batch. Every batch gets its own directory under a
  //    run-scoped path, so a directory left behind by an interrupted run (and
  //    possibly still locked by a dying JVM) can never block a later one.
  const runId = `run-${process.pid}-${Date.now().toString(36)}`;
  const runDir = path.join(CHUNKS, runId);
  await mkdir(runDir, { recursive: true });

  await pool(jobs, args.jobs, async (job, index) => {
    const chunkDir = path.join(runDir, `batch-${index}`);
    await removeDir(chunkDir);
    await mkdir(chunkDir, { recursive: true });

    // Copy the chunk in, because FFDec takes a directory of inputs. A file that
    // is still locked by a previous run is skipped rather than failing the batch.
    const copied = [];
    for (const name of job.names) {
      try {
        await copyFile(path.join(ASSETS, job.group, name), path.join(chunkDir, name));
        copied.push(name);
      } catch (error) {
        console.warn(`  ! could not stage ${name}: ${error.code ?? error.message}`);
      }
    }
    if (copied.length === 0) {
      console.warn(`  ! batch ${index}: nothing to convert`);
      return;
    }

    const outDir = path.join(runDir, `out-${index}`);
    await removeDir(outDir);
    await mkdir(outDir, { recursive: true });

    try {
      await execFileAsync(DEFAULT_FFDEC, ['-export', 'sprite', outDir, chunkDir], {
        cwd: ROOT,
        timeout: 3_600_000,
        maxBuffer: 64 * 1024 * 1024,
      });
    } catch (error) {
      console.warn(`  ! batch ${index}: ${error.message.split('\n')[0]}`);
    }

    // 3. Walk the output: <outdir>/<swf>.swf/DefineSprite_<id>/<frame>.png
    let entries;
    try {
      entries = await readdir(outDir, { withFileTypes: true });
    } catch {
      entries = [];
    }

    for (const swfEntry of entries) {
      if (!swfEntry.isDirectory()) continue;
      const swfName = swfEntry.name; // "<name>.swf"
      const swfDir = path.join(outDir, swfEntry.name);

      let symbolDirs;
      try {
        symbolDirs = await readdir(swfDir, { withFileTypes: true });
      } catch {
        continue;
      }

      for (const symbolEntry of symbolDirs) {
        if (!symbolEntry.isDirectory()) continue;
        const symbol = symbolEntry.name;
        const symbolDir = path.join(swfDir, symbolEntry.name);

        let files;
        try {
          files = await readdir(symbolDir);
        } catch {
          continue;
        }
        const pngs = files.filter((f) => f.endsWith('.png'));
        if (pngs.length === 0) continue;

        const frames = [];
        for (const file of pngs) {
          const frameIndex = Number(file.replace(/\.png$/, ''));
          if (!Number.isFinite(frameIndex)) continue;
          const buffer = await readFile(path.join(symbolDir, file));
          const hash = createHash('sha256').update(buffer).digest('hex');
          pngTotal += 1;
          bytesTotal += buffer.length;

          if (!uniqueStore.has(hash)) {
            const size = pngSize(buffer);
            await writeFile(path.join(STORE, `${hash}.png`), buffer);
            uniqueStore.set(hash, {
              file: `${hash}.png`,
              width: size?.width ?? 0,
              height: size?.height ?? 0,
              bytes: buffer.length,
            });
          }
          frames.push({ frame: frameIndex, image: hash });
        }
        frames.sort((a, b) => a.frame - b.frame);
        symbols.push({
          swf: `${job.group}/${swfName}`,
          symbol,
          frameCount: frames.length,
          uniqueFrames: new Set(frames.map((f) => f.image)).size,
          frames,
        });
      }
    }

    await removeDir(chunkDir);
    await removeDir(outDir);

    done += 1;
    const elapsed = (Date.now() - started) / 1000;
    console.log(
      `  batch ${done}/${jobs.length}  ${pngTotal} frames  ${uniqueStore.size} unique  ` +
        `${(bytesTotal / 1048576).toFixed(1)} MB png  ${elapsed.toFixed(0)}s`,
    );

    // Write the manifest after every batch, so an interrupted run keeps
    // everything it has already converted and the next run resumes from here.
    await writeManifest();
  });

  const manifest = await writeManifest();

  console.log('');
  console.log(`swf files converted : ${manifest.counts.swfFiles}`);
  console.log(`symbols             : ${manifest.counts.symbols}`);
  console.log(`png frames written  : ${pngTotal}`);
  console.log(
    `unique images       : ${uniqueStore.size}  ` +
      `(${((1 - manifest.counts.deduplicationRatio) * 100).toFixed(1)}% were duplicates)`,
  );
  console.log(`raw png bytes       : ${(bytesTotal / 1048576).toFixed(1)} MB`);
  console.log(`store bytes         : ${(manifest.counts.storeBytes / 1048576).toFixed(1)} MB`);
  console.log(`elapsed             : ${((Date.now() - started) / 1000).toFixed(0)}s`);
  console.log(`\nwrote ${args.out}`);
  console.log(`image store: ${STORE}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
