#!/usr/bin/env node
/**
 * Check that the security review's claims are covered.
 *
 * The review names the test that covers each claim, and a review that
 * points at a test which is not there is a review that has drifted.
 *
 * So the names are **checked**: every file the review names must exist,
 * and every file it names must be **run** by the suite.
 *
 * Usage:
 *   node scripts/check-security-review.mjs
 */
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The review. */
const REVIEW = path.join(ROOT, 'docs/SECURITY.md');

/** The files the review may name, and where they live. */
const PLACES = [
  'packages/server/src',
  'packages/rules/src',
  'packages/client/src',
  'packages/protocol/src',
  'apps/server/src',
  'apps/client/src',
  'scripts',
];

/** The suite's own file, so the tests are known to run. */
const PACKAGE = path.join(ROOT, 'package.json');

async function main() {
  if (!existsSync(REVIEW)) {
    console.error('there is no security review.');
    process.exit(1);
  }
  const text = await readFile(REVIEW, 'utf8');

  // The names of the tests and scripts the review points at.
  const named = new Set();
  for (const match of text.matchAll(/`([A-Za-z0-9_.-]+\.(?:test\.ts|mjs))`/g)) {
    named.add(match[1]);
  }

  if (named.size === 0) {
    console.error('the review names no tests at all.');
    process.exit(1);
  }

  const missing = [];
  for (const name of named) {
    const found = PLACES.some((place) =>
      existsSync(path.join(ROOT, place, name)),
    );
    if (!found) missing.push(name);
  }

  if (missing.length > 0) {
    console.error('the review names files that are not there:');
    for (const name of missing) console.error(`  ${name}`);
    console.error('');
    console.error(
      'A review that points at a test which is not there is a review that\n' +
        'has drifted.',
    );
    process.exit(1);
  }

  // The tests must be **run**. The suite's glob has to cover the place
  // each one lives in.
  const manifest = JSON.parse(await readFile(PACKAGE, 'utf8'));
  const suite = manifest.scripts?.test ?? '';
  const uncovered = [];
  for (const name of named) {
    if (!name.endsWith('.test.ts')) continue;
    const place = PLACES.find((candidate) =>
      existsSync(path.join(ROOT, candidate, name)),
    );
    if (!place) continue;
    // The suite's globs are per package, so the place has to be covered
    // by one of them.
    const covered = suite.includes(place) || suite.includes('packages/*/src') || suite.includes('apps/*/src');
    if (!covered) uncovered.push(`${name} (${place})`);
  }

  if (uncovered.length > 0) {
    console.error('the review names tests the suite does not run:');
    for (const name of uncovered) console.error(`  ${name}`);
    process.exit(1);
  }

  console.log(`the security review's claims are covered (${named.size} file(s) named)`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
