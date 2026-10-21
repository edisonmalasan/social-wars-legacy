#!/usr/bin/env node
/**
 * Check that the report set still agrees with the implementation.
 *
 * The report set in `re/docs` is the project's account of what the
 * original game was. It was written once, from the analysis, and it
 * states **numbers**: how many commands there are, how many items, how
 * many goals, how many unit delegates.
 *
 * Those numbers are facts about the **implementation** as well as about
 * the analysis, and the implementation moves: a command is added, a
 * delta changes the item count. So the report set is **checked** against
 * the code, and a number that has changed in one and not the other
 * fails the build.
 *
 * A report set that has drifted is worse than none: it is the thing
 * somebody trusts.
 *
 * Usage:
 *   node scripts/check-report-sync.mjs
 */
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/**
 * The claims.
 *
 * Each one is a number the report set states, and where it states it.
 * The `count` is how the number is found in the code, and the `says` is
 * what the report set has to contain for the claim to hold.
 */
export const CLAIMS = [
  {
    what: 'the commands the client can send',
    count: async () => {
      const source = await readFile(
        path.join(ROOT, 'packages/protocol/src/commands.ts'),
        'utf8',
      );
      const table = source.slice(source.indexOf('export const COMMAND_TABLE'));
      return (table.match(/^  [a-z0-9_]+: \{$/gm) ?? []).length;
    },
    expected: 94,
    file: 're/docs/00-EXECUTIVE-SUMMARY.md',
    says: '| Distinct command names the client can send | **94** |',
  },
  {
    what: 'the content items',
    count: async () => {
      const bundle = JSON.parse(
        await readFile(
          path.join(ROOT, 'packages/content/dist/content-bundle.json'),
          'utf8',
        ),
      );
      return bundle.items.length;
    },
    expected: 900,
    file: 're/docs/00-EXECUTIVE-SUMMARY.md',
    says: '**900 items**',
  },
  {
    what: 'the unit delegates',
    count: async () => {
      const map = JSON.parse(
        await readFile(
          path.join(ROOT, 're/data/item-delegate-map.json'),
          'utf8',
        ),
      );
      return map.counts.unitDelegates;
    },
    expected: 229,
    file: 're/docs/02-combat-and-units.md',
    says: '**229 unit delegates**',
  },
  {
    what: 'the goals',
    count: async () => {
      const goals = JSON.parse(
        await readFile(path.join(ROOT, 're/data/goals.json'), 'utf8'),
      );
      const list = goals.goals ?? goals.items ?? [];
      return list.length;
    },
    expected: 134,
    file: 're/docs/13-goal-system.md',
    says: '134 goals',
  },
];

/** Whether the report set still agrees with the code. */
export async function checkClaims() {
  const problems = [];

  for (const claim of CLAIMS) {
    const file = path.join(ROOT, claim.file);
    if (!existsSync(file)) {
      problems.push(`${claim.file} is missing`);
      continue;
    }
    const text = await readFile(file, 'utf8');
    if (!text.includes(claim.says)) {
      problems.push(
        `${claim.file} no longer says '${claim.says}' about ${claim.what}`,
      );
      continue;
    }
    const count = await claim.count();
    if (count === null || count === undefined) {
      problems.push(`the count for ${claim.what} could not be found`);
      continue;
    }
    if (count !== claim.expected) {
      problems.push(
        `the code has ${count} ${claim.what}, and the report says ${claim.expected}`,
      );
    }
  }

  return problems;
}

async function main() {
  const problems = await checkClaims();
  if (problems.length > 0) {
    console.error('the report set no longer agrees with the implementation:');
    for (const problem of problems) console.error(`  ${problem}`);
    console.error('');
    console.error(
      'The report set is the project\'s account of the original game, and a\n' +
        'number that has changed in the code but not in the report is a lie\n' +
        'waiting to be believed.',
    );
    process.exit(1);
  }

  console.log(`the report set agrees with the implementation (${CLAIMS.length} claims)`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
