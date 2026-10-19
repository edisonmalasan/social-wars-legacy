#!/usr/bin/env node
/**
 * Decompile the client SWFs with JPEXS (FFDec) into a working directory.
 *
 * The decompilation is an intermediate artefact, not a deliverable: it is large and
 * derived from upstream GPL-v3 content, so it lives in `.work/` (git-ignored) and only
 * the *derived tables* are committed, under `re/data/`.
 *
 *   node scripts/decompile-client.mjs            # Basesec_1.5.4.swf only
 *   node scripts/decompile-client.mjs --all      # every non-flash SWF too (B2)
 *
 * Requires FF_DEC (path to ffdec-cli.exe) in the environment, or the default install
 * location used during the investigation.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, statSync, rmSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const WORK = path.join(ROOT, '.work');
const ASSETS = path.join(ROOT, 'upstream/socialwarriors/assets');

const DEFAULT_FFDEC =
  process.env.FF_DEC ||
  'C:/Users/Edison/AppData/Local/Temp/opencode/socialwarriors/tools/ffdec/ffdec-cli.exe';

/** The client build the analysis is based on. */
const CLIENT = 'flash/Basesec_1.5.4.swf';

function ffdec() {
  const exe = DEFAULT_FFDEC;
  if (!existsSync(exe)) {
    console.error(`FFDec not found at ${exe}`);
    console.error('Set FF_DEC to the path of ffdec-cli.exe.');
    process.exit(2);
  }
  return exe;
}

function exportScript(swfPath, outDir) {
  mkdirSync(outDir, { recursive: true });
  const exe = ffdec();
  execFileSync(exe, ['-export', 'script', outDir, swfPath], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function countAs(dir) {
  let n = 0;
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith('.as')) n += 1;
    }
  };
  walk(dir);
  return n;
}

function main() {
  const all = process.argv.includes('--all');
  mkdirSync(WORK, { recursive: true });

  const clientSwf = path.join(ASSETS, CLIENT);
  const clientOut = path.join(WORK, 'as', 'basesec');
  rmSync(clientOut, { recursive: true, force: true });
  console.log(`decompiling ${CLIENT} ...`);
  const t0 = Date.now();
  exportScript(clientSwf, clientOut);
  console.log(`  -> ${clientOut} (${countAs(clientOut)} .as files, ${((Date.now() - t0) / 1000).toFixed(1)}s)`);

  if (all) {
    // Every SWF outside assets/flash: the sprite / FX / character / magic corpus.
    const groups = ['sprites', 'fx', 'characters_2', 'magic', 'swf', 'externalized'];
    for (const g of groups) {
      const dir = path.join(ASSETS, g);
      if (!existsSync(dir)) continue;
      const files = readdirSync(dir).filter((f) => f.endsWith('.swf'));
      let done = 0;
      for (const f of files) {
        const out = path.join(WORK, 'as', g, f.replace(/\.swf$/, ''));
        try {
          exportScript(path.join(dir, f), out);
        } catch (e) {
          console.warn(`  ! failed ${f}: ${e.message}`);
        }
        done += 1;
        if (done % 50 === 0) console.log(`  ${g}: ${done}/${files.length}`);
      }
      console.log(`  ${g}: ${files.length} SWFs decompiled`);
    }
  }
}

main();
