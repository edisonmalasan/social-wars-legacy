#!/usr/bin/env node
/**
 * Check the corrections policy.
 *
 * The policy is a promise, and a promise nobody checks is a wish. So
 * this checks that:
 *
 * 1. the policy **exists** and says what a request may ask for;
 * 2. the **notices** point at it — the attribution, the licensing
 *    position and the README — because a policy nobody is told about
 *    does not exist;
 * 3. the **log** is well formed: a table, with a date, a request and an
 *    answer in every row, and at least one row.
 *
 * The log is append-only, and this does not check that: the log's
 * history is in the repository's own history.
 *
 * Usage:
 *   node scripts/check-corrections.mjs
 */
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The policy. */
const POLICY = 'docs/CORRECTIONS.md';

/** The notices that must point at the policy. */
const NOTICES = ['README.md', 'docs/ATTRIBUTION.md', 'docs/LICENSING.md'];

/** The words the policy has to use, so that it really is a policy. */
const REQUIRED = [
  'A request',
  'removed',
  'credited differently',
  'The log',
];

async function main() {
  const problems = [];

  const policyPath = path.join(ROOT, POLICY);
  if (!existsSync(policyPath)) {
    console.error(`there is no ${POLICY}.`);
    process.exit(1);
  }
  const policy = await readFile(policyPath, 'utf8');

  for (const word of REQUIRED) {
    if (!policy.includes(word)) {
      problems.push(`the policy does not mention "${word}"`);
    }
  }

  // The policy has to say **where** to write, or it is not an address.
  if (!/open a draft issue/i.test(policy)) {
    problems.push('the policy does not say where to write');
  }

  // The notices have to point at it.
  for (const notice of NOTICES) {
    const file = path.join(ROOT, notice);
    if (!existsSync(file)) {
      problems.push(`${notice} is missing`);
      continue;
    }
    const text = await readFile(file, 'utf8');
    if (!text.includes('CORRECTIONS.md')) {
      problems.push(`${notice} does not point at the corrections policy`);
    }
  }

  // The log.
  const log = /## The log([\s\S]*)$/.exec(policy);
  if (!log) {
    problems.push('the policy has no log');
  } else {
    const rows = log[1]
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.startsWith('|') && !line.startsWith('| ---'))
      // The header row is not an entry.
      .filter((line) => !/^\|\s*The date\s*\|/i.test(line));
    if (rows.length === 0) {
      problems.push('the log has no entries');
    }
    for (const row of rows) {
      const cells = row
        .split('|')
        .map((cell) => cell.trim())
        .filter((cell) => cell.length > 0);
      if (cells.length < 3) {
        problems.push(`a log row is not a date, a request and an answer: ${row}`);
        continue;
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(cells[0])) {
        problems.push(`a log row has no date: ${row}`);
      }
      if (cells[1].length === 0) problems.push(`a log row has no request: ${row}`);
      if (cells[2].length === 0) problems.push(`a log row has no answer: ${row}`);
    }
  }

  if (problems.length > 0) {
    console.error('the corrections policy is not in order:');
    for (const problem of problems) console.error(`  ${problem}`);
    process.exit(1);
  }

  console.log('the corrections policy is in order, and the notices point at it');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
