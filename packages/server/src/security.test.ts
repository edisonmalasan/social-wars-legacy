import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

import { isSafeIdentifier } from './backup.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function serverSources(): Promise<{ name: string; text: string }[]> {
  const out: { name: string; text: string }[] = [];
  for (const dir of ['packages/server/src', 'apps/server/src']) {
    const full = path.join(repoRoot(), dir);
    if (!existsSync(full)) continue;
    for (const name of await readdir(full)) {
      if (!name.endsWith('.ts') || name.endsWith('.test.ts')) continue;
      out.push({
        name: `${dir}/${name}`,
        text: await readFile(path.join(full, name), 'utf8'),
      });
    }
  }
  return out;
}

/** The code of a source file, with the comments stripped. */
function code(text: string): string {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => !line.startsWith('*') && !line.startsWith('//') && !line.startsWith('/*'))
    .join('\n');
}

/**
 * Whether an interpolated expression is an identifier the file checks.
 *
 * SQL has no placeholder for an identifier, so a table name has to go
 * into the statement as text. That is the one place a name can be
 * injected into, so the file has to **check** it first.
 *
 * An expression qualifies when the file calls `isSafeIdentifier` on it,
 * or when it is a constant the file never changes.
 */
function isCheckedIdentifier(body: string, expression: string): boolean {
  // Checked.
  if (body.includes(`isSafeIdentifier(${expression})`)) return true;
  // A constant: an upper-case name, or one that is assigned once from a
  // literal and never changed.
  if (/^[A-Z_][A-Z0-9_]*$/.test(expression)) return true;
  const assigned = new RegExp(`(?:const|let)\\s+${expression}\\s*=\\s*'[^']*'`).test(body);
  return assigned;
}

describe('the server has no injection surface', () => {
  it('never interpolates a value into SQL', async () => {
    const sources = await serverSources();
    const offences: string[] = [];

    for (const { name, text } of sources) {
      const body = code(text);
      // Every query and exec call, with its statement.
      const calls = body.matchAll(/\.(query|exec)\(\s*([`'"][^`'"]*[`'"])/g);
      for (const call of calls) {
        const statement = call[2]!;
        // A template literal may interpolate only an identifier, never a
        // value. An identifier is either a name the file never changes, or
        // one the file **checks** before it is used.
        for (const interpolation of statement.matchAll(/\$\{([^}]*)\}/g)) {
          const expression = interpolation[1]!.trim();
          if (!isCheckedIdentifier(body, expression)) {
            offences.push(`${name}: \${${expression}} is not a checked identifier`);
          }
        }
      }
    }

    assert.deepEqual(
      offences,
      [],
      `a value is interpolated into SQL:\n  ${offences.join('\n  ')}`,
    );
  });

  it('passes its values as parameters', async () => {
    const sources = await serverSources();
    // A statement that mentions a column and compares it must use a
    // placeholder, not the value.
    const suspicious = /WHERE\s+\w+\s*=\s*['"`]/i;
    const offences: string[] = [];
    for (const { name, text } of sources) {
      if (suspicious.test(code(text))) offences.push(name);
    }
    assert.deepEqual(offences, [], `a value is compared in SQL:\n  ${offences.join('\n  ')}`);
  });

  it('passes every value as a parameter', async () => {
    const sources = await serverSources();
    const offences: string[] = [];

    for (const { name, text } of sources) {
      const body = code(text);
      // A statement with a placeholder must pass its values as the second
      // argument, never in the statement's text.
      const calls = body.matchAll(
        /\.(query|exec)\(\s*([`'"][^`'"]*[`'"])([^)]*)\)/g,
      );
      for (const call of calls) {
        const statement = call[2]!;
        const rest = call[3] ?? '';
        if (/\$[1-9]/.test(statement) && !rest.trim()) {
          offences.push(`${name}: a placeholder with no parameters`);
        }
        // The values must be in the parameters, not in the text.
        if (/\$\{/.test(statement)) continue; // checked above
      }
    }

    assert.deepEqual(offences, [], offences.join('\n  '));
  });
});

describe('the table names are checked', () => {
  it('accepts a plain identifier', () => {
    assert.equal(isSafeIdentifier('player_saves'), true);
    assert.equal(isSafeIdentifier('social'), true);
    assert.equal(isSafeIdentifier('Schema_Migrations_2'), true);
  });

  it('refuses anything that is not one', () => {
    for (const name of [
      'players; DROP TABLE players',
      "players' OR '1'='1",
      'players --',
      'players players',
      '',
      '2players',
      'players)',
    ]) {
      assert.equal(isSafeIdentifier(name), false, `${name} was accepted`);
    }
  });
});

describe('the credentials', () => {
  it('are not committed', async () => {
    // The repository is scanned for the shapes a credential takes. The
    // rules are deliberately loose, and the list is short, because a
    // scanner that cries wolf gets switched off.
    const root = repoRoot();
    const patterns: { pattern: RegExp; why: string }[] = [
      {
        pattern: /AKIA[0-9A-Z]{16}/,
        why: 'an AWS access key',
      },
      {
        pattern: /-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----/,
        why: 'a private key',
      },
      {
        pattern: /gh[pousr]_[A-Za-z0-9]{36,}/,
        why: 'a GitHub token',
      },
      {
        pattern: /xox[baprs]-[A-Za-z0-9-]{10,}/,
        why: 'a Slack token',
      },
    ];

    const offences: string[] = [];

    async function scan(dir: string, depth: number): Promise<void> {
      if (depth > 4) return;
      let entries;
      try {
        entries = await readdir(dir, { withFileTypes: true });
      } catch {
        return;
      }
      for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          // The vendored upstream and the build outputs are not the
          // repository's own source.
          if (['node_modules', '.git', 'upstream', 're', 'graphify-out', '.work'].includes(entry.name)) {
            continue;
          }
          await scan(full, depth + 1);
          continue;
        }
        if (!/\.(ts|mjs|js|json|yml|yaml|toml|env|md)$/.test(entry.name)) continue;
        const text = await readFile(full, 'utf8');
        for (const { pattern, why } of patterns) {
          if (pattern.test(text)) {
            offences.push(`${path.relative(root, full)}: ${why}`);
          }
        }
      }
    }

    await scan(root, 0);
    assert.deepEqual(offences, [], `a credential is committed:\n  ${offences.join('\n  ')}`);
  });
});
