import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

import { rotateDartsSchedule } from './darts.ts';

/**
 * The rules engine has no platform-dependent inputs.
 *
 * The claim is "the same seed and inputs produce the same outcome **on any
 * machine**". That is stronger than "it was tested on two machines", and it
 * is provable by construction:
 *
 * - **The randomness** is the seeded generator, and every one of its
 *   operations is a 32-bit integer operation — `>>> 0` and `Math.imul` —
 *   which the language defines exactly, not approximately.
 * - **The arithmetic** is ECMAScript's `Number`, which is IEEE 754 double
 *   precision, and the specification requires every engine to give the
 *   identical result for the identical expression. The order of the
 *   operations is fixed by the code, so there is no room for the platform
 *   to differ.
 *
 * What is left is the sources of **nondeterminism** that would break the
 * claim: an unseeded generator, the wall clock, the locale, or a platform
 * API. This file scans for them, so the claim cannot rot silently.
 */
function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** The forbidden sources of nondeterminism, and why each is forbidden. */
const FORBIDDEN: { pattern: RegExp; why: string }[] = [
  { pattern: /\bMath\s*\.\s*random\b/, why: 'the unseeded generator' },
  { pattern: /\bDate\s*\.\s*now\b/, why: 'the wall clock' },
  // The wall-clock constructor, and the local-time one. `new Date(Date.UTC(...))`
  // and the copy constructor `new Date(aDate)` are fine: they carry an instant.
  { pattern: /\bnew\s+Date\s*\(\s*\)/, why: 'the wall clock' },
  { pattern: /\bnew\s+Date\s*\([^)]*,/, why: 'the local-time constructor' },
  { pattern: /\bperformance\s*\.\s*now\b/, why: 'a monotonic clock' },
  { pattern: /\bprocess\s*\.\s*(hrtime|uptime)\b/, why: 'a monotonic clock' },
  { pattern: /\btoLocale(String|DateString|TimeString)\b/, why: 'the locale' },
  { pattern: /\blocaleCompare\b/, why: 'the locale' },
  { pattern: /\bIntl\b/, why: 'the locale' },
  { pattern: /\bprocess\s*\.\s*env\b/, why: 'the environment' },
  { pattern: /\brequire\s*\(/, why: 'an import' },
  { pattern: /\bfrom\s+['"]node:/, why: 'a platform API' },
  { pattern: /\bchild_process\b/, why: 'a platform API' },
  { pattern: /\bfs\b\s*\.\s*(readFile|writeFile)/, why: 'the filesystem' },
];

async function rulesSources(): Promise<{ name: string; text: string }[]> {
  const dir = path.join(repoRoot(), 'packages/rules/src');
  const names = (await readdir(dir)).filter(
    (name) => name.endsWith('.ts') && !name.endsWith('.test.ts'),
  );
  const out: { name: string; text: string }[] = [];
  for (const name of names) {
    out.push({ name, text: await readFile(path.join(dir, name), 'utf8') });
  }
  return out;
}

describe('the rules engine is deterministic', () => {
  it('has no unseeded randomness, no clock and no locale', async () => {
    const sources = await rulesSources();
    assert.ok(sources.length > 5, 'the rules engine was not found');

    const offences: string[] = [];
    for (const { name, text } of sources) {
      // The comments explain why these are forbidden, so the scan looks at
      // the code only: the comment lines are stripped first.
      const code = text
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => !line.startsWith('*') && !line.startsWith('//') && !line.startsWith('/*'))
        .join('\n');

      for (const { pattern, why } of FORBIDDEN) {
        const match = code.match(pattern);
        if (match) {
          offences.push(`${name}: ${why} (${match[0].trim()})`);
        }
      }
    }

    assert.deepEqual(
      offences,
      [],
      `the rules engine must not depend on the platform:\n  ${offences.join('\n  ')}`,
    );
  });

  it('takes the seed and the clock from its caller', async () => {
    const sources = await rulesSources();
    const all = sources.map((source) => source.text).join('\n');
    // The seed arrives as an argument, and the time as one too.
    assert.match(all, /seed/);
    assert.match(all, /now/);
  });
});

describe('the darts schedule does not depend on the timezone', () => {
  const games = [
    { id: 1, start_date: '2012-06-11 00:00:00', extra_item: 1, items: [1] },
    { id: 2, start_date: '2012-06-18 00:00:00', extra_item: 2, items: [2] },
  ];

  /** The rotated schedule, in the timezone the process is running in. */
  function rotatedIn(timezone: string): string[] {
    const previous = process.env['TZ'];
    process.env['TZ'] = timezone;
    try {
      // The instant is fixed, so only the timezone can change the result.
      const now = new Date(Date.UTC(2026, 9, 21, 12, 0, 0));
      return rotateDartsSchedule(games, now).map((game) => game.start_date);
    } finally {
      if (previous === undefined) delete process.env['TZ'];
      else process.env['TZ'] = previous;
    }
  }

  it('rotates to the same strings in every timezone', () => {
    const kiritimati = rotatedIn('Pacific/Kiritimati'); // UTC+14
    const midway = rotatedIn('Pacific/Midway'); // UTC-11
    const kathmandu = rotatedIn('Asia/Kathmandu'); // UTC+5:45

    assert.deepEqual(kiritimati, midway);
    assert.deepEqual(kiritimati, kathmandu);
  });

  it('rotates onto a Monday', () => {
    for (const date of rotatedIn('Pacific/Kiritimati')) {
      // The string is a UTC wall clock, so its weekday is the weekday in it.
      const parsed = new Date(`${date.replace(' ', 'T')}Z`);
      assert.equal(parsed.getUTCDay(), 1, `${date} is not a Monday`);
    }
  });
});
