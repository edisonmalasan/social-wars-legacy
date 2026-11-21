#!/usr/bin/env node
/**
 * Assert that the desktop shell's `frontendDist` is the **real** web client.
 *
 * `prepare-desktop.mjs` used to leave a 162-byte placeholder in
 * `apps/desktop/dist`. Tauri happily packages it, and the shell then opens
 * an empty window. This check proves the built client is there instead:
 * the page carries a module script with a hashed asset, which the
 * placeholder does not have.
 *
 * Usage:
 *   node scripts/check-desktop-dist.mjs
 */
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const INDEX = path.join(ROOT, 'apps/desktop/dist/index.html');

async function main() {
  if (!existsSync(INDEX)) {
    console.error(`FAIL: no desktop frontend at ${path.relative(ROOT, INDEX)}`);
    console.error('Run: node scripts/prepare-desktop.mjs');
    process.exit(1);
  }

  const html = await readFile(INDEX, 'utf8');
  const problems = [];
  if (!/<script\b/i.test(html)) {
    problems.push('there is no script tag: this is the placeholder, not the built client');
  }
  if (!/src\s*=\s*["']\.?\/?assets\//i.test(html)) {
    problems.push('the page does not load the built client from ./assets/');
  }

  if (problems.length > 0) {
    console.error('FAIL: the desktop shell would ship a placeholder:');
    for (const problem of problems) console.error(`  ${problem}`);
    console.error('');
    console.error('Run: pnpm --filter @swl/app-client build && node scripts/prepare-desktop.mjs');
    process.exit(1);
  }

  console.log('OK: the desktop frontend is the built web client.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
