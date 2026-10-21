#!/usr/bin/env node
/**
 * The project's own linter.
 *
 * The type-check finds the type errors, and this finds the **project's**
 * errors — the ones that are true of this repository and not of
 * TypeScript.
 *
 * There are two rules, and both of them exist because the project
 * **runs in a browser**:
 *
 * 1. **The browser bundle must not reach a `node:` import.** The client
 *    is a browser application: the web build, the desktop shell's web
 *    view and the mobile build all run it in a web view, and a `node:`
 *    import in the graph is a build failure at best.
 * 2. **The rules engine must not import `node:`.** It runs in a browser
 *    worker for the offline mode, so it has to be free of the platform
 *    (ADR 2).
 *
 * The first rule is a **reachability** check, not a grep: a module that
 * imports `node:` is fine if nothing the browser loads reaches it, and
 * the check says so.
 *
 * Usage:
 *   node scripts/lint-project.mjs
 */
import { existsSync, statSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The browser application: its entry point. */
const BROWSER_ENTRY = 'apps/client/src/main.ts';

/** The packages that run in a browser. */
const BROWSER_SAFE = [
  'packages/client/src',
  'packages/rules/src',
  'packages/protocol/src',
  'apps/client/src',
];

/** The workspace packages, and where they live. */
const WORKSPACE = {
  '@swl/client': 'packages/client/src',
  '@swl/rules': 'packages/rules/src',
  '@swl/protocol': 'packages/protocol/src',
  '@swl/server': 'packages/server/src',
  '@swl/content': 'packages/content/src',
};

/** The imports of a module, and which of them are type-only. */
function importsOf(source) {
  const found = [];
  const pattern = /(?:^|\n)\s*(?:import|export)\s+(type\s+)?([^;]*?)\s*from\s*['"]([^'"]+)['"]/g;
  for (const match of source.matchAll(pattern)) {
    const typeOnly = Boolean(match[1]);
    const specifier = match[3];
    found.push({ specifier, typeOnly });
  }
  // A bare `import 'x'` has no `from`.
  for (const match of source.matchAll(/(?:^|\n)\s*import\s+['"]([^'"]+)['"]/g)) {
    found.push({ specifier: match[1], typeOnly: false });
  }
  return found;
}

/** Resolve a specifier to a file, or null. */
function resolve(specifier, from) {
  if (specifier.startsWith('node:')) return { node: true };
  if (specifier.startsWith('.')) {
    const base = path.resolve(path.dirname(from), specifier);
    for (const candidate of [
      base,
      `${base}.ts`,
      `${base}.tsx`,
      path.join(base, 'index.ts'),
    ]) {
      if (!existsSync(candidate)) continue;
      if (statSync(candidate).isFile()) return { file: candidate };
    }
    return null;
  }
  const workspace = WORKSPACE[specifier];
  if (workspace) {
    return resolve('./index.ts', path.join(ROOT, workspace, 'index.ts'));
  }
  // A package outside the workspace: it is somebody else's code, and
  // whether it is browser-safe is its business.
  return { external: true };
}

/** Every module the browser reaches, and the `node:` imports among them. */
async function browserGraph() {
  const seen = new Set();
  const offences = [];
  const queue = [path.join(ROOT, BROWSER_ENTRY)];

  while (queue.length > 0) {
    const file = queue.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    if (!existsSync(file)) continue;

    const source = await readFile(file, 'utf8');
    for (const entry of importsOf(source)) {
      if (entry.typeOnly) continue;
      const resolved = resolve(entry.specifier, file);
      if (!resolved) continue;
      if (resolved.node) {
        offences.push(
          `${path.relative(ROOT, file)} imports ${entry.specifier}, and the browser reaches it`,
        );
        continue;
      }
      if (resolved.file) queue.push(resolved.file);
    }
  }

  return { seen, offences };
}

/** The `node:` imports in a package's runtime modules. */
async function packageOffences(directory) {
  const { readdir } = await import('node:fs/promises');
  const base = path.join(ROOT, directory);
  if (!existsSync(base)) return [];
  const offences = [];
  for (const name of await readdir(base)) {
    if (!name.endsWith('.ts') || name.endsWith('.test.ts')) continue;
    const file = path.join(base, name);
    const source = await readFile(file, 'utf8');
    for (const entry of importsOf(source)) {
      if (entry.typeOnly) continue;
      if (entry.specifier.startsWith('node:')) {
        offences.push(
          `${path.relative(ROOT, file)} imports ${entry.specifier}`,
        );
      }
    }
  }
  return offences;
}

async function main() {
  const problems = [];

  // Rule 1.
  const graph = await browserGraph();
  problems.push(...graph.offences);

  // Rule 2: the rules engine runs in a browser worker.
  problems.push(...(await packageOffences('packages/rules/src')));

  if (problems.length > 0) {
    console.error("the project's own rules are broken:");
    for (const problem of problems) console.error(`  ${problem}`);
    console.error('');
    console.error(
      'The client runs in a browser: the web build, the desktop shell\'s web view\n' +
        'and the mobile build all run it in a web view.',
    );
    process.exit(1);
  }

  console.log(
    `the project's rules hold: the browser bundle reaches ${graph.seen.size} ` +
      'module(s) and none of them needs node',
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
