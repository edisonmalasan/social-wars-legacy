import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { contentPathFrom } from './content-path.ts';

/** A stand-in for apps/server/src/main.ts, in a tree with a workspace root. */
const MODULE_URL = pathToFileURL(
  path.join(path.parse(process.cwd()).root, 'repo', 'apps', 'server', 'src', 'main.ts'),
);

describe('contentPathFrom', () => {
  it('resolves the bundle relative to the server module', () => {
    const resolved = contentPathFrom(MODULE_URL);
    assert.equal(
      resolved.split(path.sep).slice(-4).join('/'),
      'packages/content/dist/content-bundle.json',
      'the bundle must resolve to the workspace-root packages/content/dist directory',
    );
  });

  it('does not depend on the working directory', () => {
    const expected = contentPathFrom(MODULE_URL);
    const original = process.cwd();
    try {
      process.chdir(path.parse(original).root);
      assert.equal(contentPathFrom(MODULE_URL), expected);
    } finally {
      process.chdir(original);
    }
  });
});

describe('the server entry point', () => {
  it('uses the module-relative resolver for its content path', async () => {
    const source = await readFile(new URL('./main.ts', import.meta.url), 'utf8');
    const declaration = source
      .split('\n')
      .find((line) => line.includes('const CONTENT_PATH ='));
    assert.ok(declaration, 'main.ts must declare CONTENT_PATH');
    assert.match(declaration, /contentPathFrom\(import\.meta\.url\)/);
    assert.doesNotMatch(
      declaration,
      /process\.cwd\(\)/,
      'pnpm --filter runs the server with cwd=apps/server, so cwd must not be used',
    );
  });
});
