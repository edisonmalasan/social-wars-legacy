#!/usr/bin/env node
/**
 * Measure the test coverage and **enforce a threshold**.
 *
 * The threshold is the point. A coverage number that is only reported
 * is a number that is only read; a number that **fails the build** is
 * one that cannot quietly go down.
 *
 * The floors are set where the project is today, with a little room:
 *
 * - **85 %** of the lines
 * - **80 %** of the functions
 * - **70 %** of the branches
 *
 * The branches are lower than the lines because a branch is a
 * *decision*, and a decision that is not taken is often a decision that
 * cannot be taken: a defensive branch for a case the type system has
 * already ruled out, for instance.
 *
 * The measurement is Node's own, so there is no extra dependency and no
 * second opinion to reconcile.
 *
 * Usage:
 *   node scripts/check-coverage.mjs
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The floors. */
export const THRESHOLDS = {
  lines: 85,
  functions: 80,
  branches: 70,
};

const args = [
  '--test',
  '--experimental-test-coverage',
  '--test-coverage-include=packages/*/src/**/*.ts',
  '--test-coverage-exclude=**/*.test.ts',
  '--test-coverage-exclude=**/index.ts',
  `--test-coverage-lines=${THRESHOLDS.lines}`,
  `--test-coverage-functions=${THRESHOLDS.functions}`,
  `--test-coverage-branches=${THRESHOLDS.branches}`,
  'packages/*/src/**/*.test.ts',
  'apps/*/src/**/*.test.ts',
];

const result = spawnSync(process.execPath, args, {
  cwd: ROOT,
  stdio: 'inherit',
});

if (result.status !== 0) {
  console.error('');
  console.error(
    `the coverage is below the floors: ${THRESHOLDS.lines}% of the lines, ` +
      `${THRESHOLDS.functions}% of the functions and ` +
      `${THRESHOLDS.branches}% of the branches.`,
  );
  process.exit(result.status ?? 1);
}

console.log('');
console.log(
  `the coverage is above the floors: ${THRESHOLDS.lines}% of the lines, ` +
    `${THRESHOLDS.functions}% of the functions and ` +
    `${THRESHOLDS.branches}% of the branches.`,
);
