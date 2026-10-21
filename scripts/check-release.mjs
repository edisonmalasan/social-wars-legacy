#!/usr/bin/env node
/**
 * Check the release checklist.
 *
 * A checklist is a list of things to do at the worst possible moment,
 * when nobody has time to read it carefully. So it is checked:
 *
 * 1. every command it names **exists** — a script under `scripts/` or a
 *    `pnpm` script — because a checklist that names a command that no
 *    longer exists fails exactly when it is needed;
 * 2. every step of the CI's **gate** is mentioned by it, so the
 *    checklist covers the whole gate and not half of it;
 * 3. it names the **licence gate**, the **rollback** and the
 *    **backups**, because those are the three that a release is not
 *    allowed to forget.
 *
 * Usage:
 *   node scripts/check-release.mjs
 */
import { existsSync } from 'node:fs';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The checklist. */
const CHECKLIST = 'docs/RELEASE.md';

/** The workflow whose gate the checklist has to cover. */
const WORKFLOW = '.github/workflows/ci.yml';

/**
 * The words the checklist has to use.
 *
 * The three that a release is not allowed to forget: the licence
 * position, the way back, and the copies.
 */
const REQUIRED = [
  'LICENSING.md',
  'rollback',
  'backups',
  'deploy.mjs',
  'check-backups.mjs',
  'migrate',
];

/** The commands the checklist must mention. */
const GATE = [
  'verify-upstream.mjs',
  'typecheck',
  'lint',
  'test:integration',
  'check-coverage.mjs',
  'golden-master.mjs',
  'soak-server.mjs',
  'load-test.mjs',
  'build:content',
  'verify-command-catalogue.mjs',
  'check-roadmap.mjs',
  'run-cheat-battery.mjs',
  'check-no-flash.mjs',
  'check-licensing.mjs',
  'build-licence-report.mjs',
  'check-adrs.mjs',
  'check-security-review.mjs',
  'check-corrections.mjs',
  'check-report-sync.mjs',
  'check-reproducible-build.mjs',
  'smoke-test-client.mjs',
  'e2e-test.mjs',
];

/** The `pnpm` scripts, for the commands that are not scripts. */
async function pnpmScripts() {
  const manifest = JSON.parse(
    await readFile(path.join(ROOT, 'package.json'), 'utf8'),
  );
  return new Set(Object.keys(manifest.scripts ?? {}));
}

async function main() {
  const problems = [];

  const checklistPath = path.join(ROOT, CHECKLIST);
  if (!existsSync(checklistPath)) {
    console.error(`there is no ${CHECKLIST}.`);
    process.exit(1);
  }
  const checklist = await readFile(checklistPath, 'utf8');

  // --- 1. The words --------------------------------------------------------
  for (const word of REQUIRED) {
    if (!checklist.includes(word)) {
      problems.push(`the checklist does not mention "${word}"`);
    }
  }

  // --- 2. Every command it names exists ------------------------------------
  const scripts = await pnpmScripts();
  const available = new Set(
    (await readdir(path.join(ROOT, 'scripts'))).map((name) => name),
  );
  for (const match of checklist.matchAll(/`([^`\n]+)`/g)) {
    const command = match[1];
    // Only the commands that name a script or a pnpm script.
    const script = /(?:^|\s)scripts\/([A-Za-z0-9_.-]+\.mjs)/.exec(command);
    if (script && !available.has(script[1])) {
      problems.push(`the checklist names scripts/${script[1]}, which is not there`);
    }
    // `pnpm <script>` and `pnpm --filter <package> <script>` both name
    // a script, and an option is not one.
    const pnpm = /pnpm(?:\s+--filter\s+\S+)?\s+([A-Za-z0-9:_-]+)/.exec(command);
    if (pnpm && !pnpm[1].startsWith('-') && !scripts.has(pnpm[1])) {
      problems.push(`the checklist names "pnpm ${pnpm[1]}", which is not a script`);
    }
  }

  // --- 3. The whole gate is covered ----------------------------------------
  for (const step of GATE) {
    if (!checklist.includes(step)) {
      problems.push(`the checklist does not mention "${step}"`);
    }
  }

  // --- 4. The workflow's gate is in the checklist --------------------------
  // Every `run:` in the workflow's Verify job names something the
  // checklist must cover.
  const workflow = await readFile(path.join(ROOT, WORKFLOW), 'utf8');
  const verify = workflow.split(/\n  [a-z]/)[0] ?? workflow;
  for (const match of verify.matchAll(/node (scripts\/[A-Za-z0-9_.-]+\.mjs)/g)) {
    if (!checklist.includes(match[1])) {
      problems.push(`the CI runs ${match[1]}, and the checklist does not mention it`);
    }
  }

  if (problems.length > 0) {
    console.error('the release checklist is not in order:');
    for (const problem of problems) console.error(`  ${problem}`);
    process.exit(1);
  }

  console.log('the release checklist is in order, and it covers the whole gate');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
