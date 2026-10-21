#!/usr/bin/env node
/**
 * Enumerate the third-party licences.
 *
 * Every dependency the project ships has a licence, and a project that
 * cannot say what its dependencies' licences are cannot say whether it
 * is allowed to ship them.
 *
 * So the dependencies are **enumerated**, and the enumeration is
 * **checked**: a dependency that is not in the table below fails the
 * build, so a new one has to be classified before it can be used.
 *
 * The report is written to `docs/LICENCES.md`, and it is generated so
 * that it cannot drift from the manifests.
 *
 * Usage:
 *   node scripts/build-licence-report.mjs
 *   node scripts/build-licence-report.mjs --check   check only, do not write
 */
import { existsSync } from 'node:fs';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/**
 * The known licences.
 *
 * A dependency that is not here is an error, not a gap: the point of
 * the table is that somebody looked.
 */
export const LICENCES = {
  // The JavaScript and TypeScript.
  '@electric-sql/pglite': { licence: 'Apache-2.0', why: 'the database' },
  '@types/node': { licence: 'MIT', why: 'the type definitions' },
  typescript: { licence: 'Apache-2.0', why: 'the language' },
  'pixi.js': { licence: 'MIT', why: "the client's renderer" },
  vite: { licence: 'MIT', why: "the client's build" },

  // The Rust.
  tauri: { licence: 'MIT OR Apache-2.0', why: 'the desktop shell' },
  'tauri-build': { licence: 'MIT OR Apache-2.0', why: "the shell's build" },
  serde: { licence: 'MIT OR Apache-2.0', why: 'the serialisation' },
  'serde_json': { licence: 'MIT OR Apache-2.0', why: 'the serialisation' },
  tempfile: { licence: 'MIT OR Apache-2.0', why: 'the tests' },
  rustls: { licence: 'Apache-2.0 OR ISC OR MIT', why: "the shell's certificate check" },
  'rustls-native-certs': {
    licence: 'Apache-2.0 OR ISC OR MIT',
    why: "the operating system's certificate roots",
  },
  'rustls-pki-types': { licence: 'MIT OR Apache-2.0', why: "the certificate's types" },
  ring: { licence: 'Apache-2.0 AND ISC', why: "the certificate's fingerprint" },

  // The fonts, which are not a package but are shipped.
  nunito: {
    licence: 'SIL Open Font License 1.1',
    why: 'the substitute for Arial Rounded MT Bold',
  },
  rubikmoneone: {
    licence: 'SIL Open Font License 1.1',
    why: 'the substitute for Komika Axis',
  },
};

/** The licences that are acceptable to ship. */
export const PERMITTED = [
  'MIT',
  'Apache-2.0',
  'MIT OR Apache-2.0',
  // A three-way choice, and it is *more* permissive than the two-way
  // one: ISC joins the alternatives.
  'Apache-2.0 OR ISC OR MIT',
  // A conjunction, and it is *more* restrictive than Apache-2.0 alone:
  // both licences apply.
  'Apache-2.0 AND ISC',
  'SIL Open Font License 1.1',
  'BSD-2-Clause',
  'BSD-3-Clause',
  'ISC',
  'Zlib',
  'CC0-1.0',
  'Unlicense',
];

/** The workspace's own packages, which are not third-party. */
const OWN = /^@swl\//;

/** Every package's manifest. */
async function manifests() {
  const found = [];

  // The root, which holds the workspace's own tooling.
  const rootFile = path.join(ROOT, 'package.json');
  if (existsSync(rootFile)) {
    const manifest = JSON.parse(await readFile(rootFile, 'utf8'));
    found.push({
      where: '.',
      dependencies: manifest.dependencies ?? {},
      devDependencies: manifest.devDependencies ?? {},
    });
  }

  for (const directory of ['packages', 'apps']) {
    const base = path.join(ROOT, directory);
    if (!existsSync(base)) continue;
    for (const name of await readdir(base)) {
      const file = path.join(base, name, 'package.json');
      if (!existsSync(file)) continue;
      const manifest = JSON.parse(await readFile(file, 'utf8'));
      found.push({
        where: `${directory}/${name}`,
        dependencies: manifest.dependencies ?? {},
        devDependencies: manifest.devDependencies ?? {},
      });
    }
  }
  return found;
}

/** The Rust dependencies, and the size of the tree. */
async function rustDependencies() {
  const file = path.join(ROOT, 'apps/desktop/src-tauri/Cargo.toml');
  if (!existsSync(file)) return { direct: [], transitive: 0 };
  const text = await readFile(file, 'utf8');

  const direct = [];
  let section = '';
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('[')) {
      section = trimmed;
      continue;
    }
    if (section !== '[dependencies]' && section !== '[build-dependencies]') continue;
    if (!trimmed || trimmed.startsWith('#')) continue;
    const match = /^([A-Za-z0-9_-]+)\s*=\s*(.*)$/.exec(trimmed);
    if (!match) continue;
    // The version is either the value itself, or it is inside an inline
    // table: `tauri = { version = "2", features = [] }`.
    const inline = /version\s*=\s*"([^"]+)"/.exec(match[2]);
    const plain = match[2]
      .replace(/[{}]/g, '')
      .split(',')[0]
      .trim()
      .replace(/^"|"$/g, '');
    direct.push({ name: match[1], version: inline ? inline[1] : plain });
  }

  // The lockfile says how many crates the tree actually has.
  let transitive = 0;
  const lock = path.join(ROOT, 'apps/desktop/src-tauri/Cargo.lock');
  if (existsSync(lock)) {
    const text2 = await readFile(lock, 'utf8');
    transitive = (text2.match(/^\[\[package\]\]/gm) ?? []).length;
  }

  return { direct, transitive };
}

/** The report. */
export async function buildReport() {
  const packages = await manifests();
  const rust = await rustDependencies();

  const npm = new Map();
  for (const entry of packages) {
    for (const [name, version] of Object.entries({
      ...entry.dependencies,
      ...entry.devDependencies,
    })) {
      if (OWN.test(name)) continue;
      if (!npm.has(name)) npm.set(name, { version, where: new Set() });
      npm.get(name).where.add(entry.where);
    }
  }

  const rows = [];
  const unknown = [];

  for (const [name, info] of [...npm.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const known = LICENCES[name];
    if (!known) {
      unknown.push(name);
      rows.push({ name, version: info.version, licence: 'UNKNOWN', why: 'not classified' });
      continue;
    }
    rows.push({
      name,
      version: info.version,
      licence: known.licence,
      why: known.why,
      where: [...info.where].join(', '),
    });
  }

  const rustRows = rust.direct.map((entry) => {
    const known = LICENCES[entry.name];
    if (!known) unknown.push(entry.name);
    return {
      name: entry.name,
      version: entry.version,
      licence: known?.licence ?? 'UNKNOWN',
      why: known?.why ?? 'not classified',
    };
  });

  return { npm: rows, rust: rustRows, transitive: rust.transitive, unknown };
}

/** The report, as Markdown. */
export function reportMarkdown(report) {
  const npmRows = report.npm
    .map(
      (row) =>
        `| \`${row.name}\` | ${row.version} | ${row.licence} | ${row.why} |`,
    )
    .join('\n');
  const rustRows = report.rust
    .map(
      (row) =>
        `| \`${row.name}\` | ${row.version} | ${row.licence} | ${row.why} |`,
    )
    .join('\n');

  return `# The third-party licences

Every dependency the project ships has a licence, and this file says
what each one is. It is **generated** by
\`node scripts/build-licence-report.mjs\`, so it cannot drift from the
manifests, and a dependency that is not classified **fails the build**.

See [\`LICENSING.md\`](LICENSING.md) for the position on the project's
own assets, and [\`ATTRIBUTION.md\`](ATTRIBUTION.md) for the notices the
original project asks for.

## The JavaScript and TypeScript

| The dependency | The version | The licence | Why it is here |
|---|---|---|---|
${npmRows}

## The Rust

| The crate | The version | The licence | Why it is here |
|---|---|---|---|
${rustRows}

The tree has **${report.transitive}** crates in total, pinned by
\`Cargo.lock\`. The direct ones are above; the rest are Tauri\'s, and
each carries its own licence.

## The fonts

| The face | The licence | Why |
|---|---|---|
| Nunito | SIL Open Font License 1.1 | the substitute for Arial Rounded MT Bold |
| Rubik Mono One | SIL Open Font License 1.1 | the substitute for Komika Axis |

The client\'s own faces are **proprietary** and are not shipped.

## The assets

There are none. The art, the sounds and the configuration are Zynga\'s,
they cannot be shipped, and the clone re-creates them. See
[\`LICENSING.md\`](LICENSING.md).
`;
}

async function main() {
  const report = await buildReport();

  if (report.unknown.length > 0) {
    console.error('these dependencies have no classified licence:');
    for (const name of report.unknown) console.error(`  ${name}`);
    console.error('');
    console.error(
      'Add them to the LICENCES table in scripts/build-licence-report.mjs.',
    );
    process.exit(1);
  }

  // Every licence has to be one that is acceptable to ship.
  for (const row of [...report.npm, ...report.rust]) {
    if (!PERMITTED.includes(row.licence)) {
      console.error(
        `the licence of ${row.name} is "${row.licence}", which is not one that may be shipped`,
      );
      process.exit(1);
    }
  }

  if (process.argv.includes('--check')) {
    console.log('the licences are classified and permitted');
    return;
  }

  const out = path.join(ROOT, 'docs/LICENCES.md');
  await writeFile(out, reportMarkdown(report), 'utf8');
  console.log(`wrote ${out}`);
  console.log(`  ${report.npm.length} JavaScript dependenc(ies)`);
  console.log(`  ${report.rust.length} direct Rust dependenc(ies)`);
  console.log(`  ${report.transitive} crates in the tree`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
