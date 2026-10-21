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
 * the check says so. It follows the static imports, the re-exports and
 * the **dynamic** imports, because a dynamic import is still an import:
 * the browser fetches the chunk and runs it.
 *
 * It resolves the workspace's **subpath** exports too — `@swl/server/apply`
 * is the applier, and not the package's index — because that is how the
 * code reaches the server's authority without pulling in the sessions
 * and the credentials, which need the platform.
 *
 * Usage:
 *   node scripts/lint-project.mjs
 */
import { existsSync, statSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/**
 * The modules that have to be browser-safe.
 *
 * - the client application, because it is a browser application;
 * - the rules engine, because it runs in a browser worker for the
 *   offline mode;
 * - the applier, because it is the **authority**, and it is reachable
 *   on its own: the server package's index pulls in the sessions and the
 *   credentials, which need the platform, so the applier has its own
 *   entry point and stays free of it.
 */
const BROWSER_SAFE_ENTRIES = [
  'apps/client/src/main.ts',
  'packages/rules/src/index.ts',
  'packages/server/src/apply.ts',
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
  const pattern =
    /(?:^|\n)\s*(?:import|export)\s+(type\s+)?([^;]*?)\s*from\s*['"]([^'"]+)['"]/g;
  for (const match of source.matchAll(pattern)) {
    found.push({ specifier: match[3], typeOnly: Boolean(match[1]) });
  }
  // A bare `import 'x'` has no `from`.
  for (const match of source.matchAll(/(?:^|\n)\s*import\s+['"]([^'"]+)['"]/g)) {
    found.push({ specifier: match[1], typeOnly: false });
  }
  // A **dynamic** import is still an import: the browser fetches the
  // chunk and runs it, so the module is in the graph.
  for (const match of source.matchAll(/\bimport\(\s*['"]([^'"]+)['"]\s*\)/g)) {
    found.push({ specifier: match[1], typeOnly: false });
  }
  return found;
}

/** A file, if it is one. */
function asFile(candidate) {
  if (!existsSync(candidate)) return null;
  if (!statSync(candidate).isFile()) return null;
  return candidate;
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
      const file = asFile(candidate);
      if (file) return { file };
    }
    return null;
  }

  // A workspace package: the whole of it.
  const workspace = WORKSPACE[specifier];
  if (workspace) {
    const file = asFile(path.join(ROOT, workspace, 'index.ts'));
    return file ? { file } : null;
  }

  // A workspace package's **subpath**: `@swl/server/apply` is the
  // applier, and not the package's index. That is the whole point of
  // the subpath — it keeps the platform-dependent modules out.
  for (const [name, directory] of Object.entries(WORKSPACE)) {
    if (!specifier.startsWith(`${name}/`)) continue;
    const rest = specifier.slice(name.length + 1);
    const base = path.join(ROOT, directory, rest);
    for (const candidate of [base, `${base}.ts`, path.join(base, 'index.ts')]) {
      const file = asFile(candidate);
      if (file) return { file };
    }
    return null;
  }

  // A package outside the workspace: it is somebody else's code, and
  // whether it is browser-safe is its business.
  return { external: true };
}

/** Every module the browser reaches, and the `node:` imports among them. */
async function browserGraph(entry) {
  const seen = new Set();
  const offences = [];
  const queue = [path.join(ROOT, entry)];

  while (queue.length > 0) {
    const file = queue.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    if (!existsSync(file)) continue;

    const source = await readFile(file, 'utf8');
    for (const entryImport of importsOf(source)) {
      if (entryImport.typeOnly) continue;
      const resolved = resolve(entryImport.specifier, file);
      if (!resolved) continue;
      if (resolved.node) {
        offences.push(
          `${path.relative(ROOT, file)} imports ${entryImport.specifier}, and the browser reaches it`,
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
        offences.push(`${path.relative(ROOT, file)} imports ${entry.specifier}`);
      }
    }
  }
  return offences;
}

async function main() {
  const problems = [];

  // Rules 1 and 3: the entries that have to be browser-safe.
  let reached = 0;
  for (const entry of BROWSER_SAFE_ENTRIES) {
    const graph = await browserGraph(entry);
    reached += graph.seen.size;
    for (const offence of graph.offences) {
      problems.push(`${entry}: ${offence}`);
    }
  }

  // Rule 2: the rules engine runs in a browser worker.
  problems.push(...(await packageOffences('packages/rules/src')));

  if (problems.length > 0) {
    console.error("the project's own rules are broken:");
    for (const problem of problems) console.error(`  ${problem}`);
    console.error('');
    console.error(
      "The client runs in a browser: the web build, the desktop shell's web view\n" +
        'and the mobile build all run it in a web view.',
    );
    process.exit(1);
  }

  console.log(
    `the project's rules hold: the browser reaches ${reached} module(s) ` +
      'and none of them needs node',
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
