#!/usr/bin/env node
/**
 * Run the cheat battery.
 *
 * The battery is the server's own check that it does not trust the
 * client: eleven attacks, each run against the **real** authority layer,
 * each of which must have no effect.
 *
 * This is the **release gate**. The battery is mutation-tested, so a
 * weakening of the authority layer is caught by exactly the attack it
 * weakens - which means a battery that passes is evidence, and a battery
 * that fails is a server that trusts the client.
 *
 * Usage:
 *   node scripts/run-cheat-battery.mjs
 */
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { costContentFrom } from '@swl/rules';
import { createCheatContext, runCheatBattery } from '@swl/rules';

const ROOT = process.cwd();
const BUNDLE = path.join(ROOT, 'packages/content/dist/content-bundle.json');

async function main() {
  const bundle = JSON.parse(await readFile(BUNDLE, 'utf8'));
  const content = costContentFrom(bundle);

  const context = createCheatContext(content);
  const report = runCheatBattery(context);

  console.log(`the cheat battery: ${report.results.length} attacks`);
  for (const result of report.results) {
    const mark = result.caught ? 'caught' : 'ESCAPED';
    console.log(`  ${mark.padEnd(8)} ${result.id}  ${result.name}`);
  }

  if (report.uncaught.length > 0) {
    console.error('');
    console.error(`FAIL: ${report.uncaught.length} attack(s) got through:`);
    for (const id of report.uncaught) {
      const failure = report.results.find((r) => r.id === id)?.failure ?? '?';
      console.error(`  ${id}: ${failure}`);
    }
    console.error('');
    console.error('The server trusted the client. A release must not carry that.');
    process.exit(1);
  }

  console.log('');
  console.log(`OK: all ${report.caught.length} attacks had no effect.`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
