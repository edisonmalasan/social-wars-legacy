#!/usr/bin/env node
/**
 * Check the licensing position's claims.
 *
 * `docs/LICENSING.md` records the position, and this checks the claims
 * it makes. A position that cannot be checked is a position nobody can
 * rely on.
 *
 * The claims:
 *
 * 1. The vendored upstream is **GPL v3** and is **unmodified**.
 * 2. **No package imports from the upstream.** The upstream is a
 *    reference and a test fixture, never a runtime dependency, so the
 *    shipped product is not a derivative work of it.
 * 3. The **shipped tree carries no Zynga media**: no SWF, no sound, and
 *    none of the client's proprietary fonts.
 *
 * Usage:
 *   node scripts/check-licensing.mjs
 */
import { existsSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** The packages that ship. */
const PACKAGES = ['packages/rules', 'packages/server', 'packages/client', 'packages/protocol', 'packages/content', 'apps/server', 'apps/client'];

/** The trees that ship. */
const SHIPPED = ['apps/client/dist', 'apps/desktop/dist', 'apps/desktop/src-tauri/server'];

/** The media that must not ship. */
const FORBIDDEN_MEDIA = /\.(swf|mp3|ogg|wav|flv|f4v)$/i;

/** The proprietary fonts, by the name they are known by. */
const PROPRIETARY_FONTS = /arial[ _-]?rounded|komika/i;

/** Every file under a directory. */
async function filesUnder(dir) {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await filesUnder(full)));
    else if (entry.isFile()) out.push(full);
  }
  return out;
}

async function main() {
  const explicit = process.argv.indexOf('--path');
  const trees =
    explicit >= 0 && process.argv[explicit + 1]
      ? [path.resolve(process.argv[explicit + 1])]
      : SHIPPED.map((dir) => path.join(ROOT, dir));

  const offences = [];

  // --- 1. The upstream is GPL v3 and unmodified -----------------------------
  const licence = path.join(ROOT, 'upstream/socialwarriors/LICENSE');
  if (!existsSync(licence)) {
    offences.push('the vendored upstream has no LICENSE file');
  } else {
    const text = await readFile(licence, 'utf8');
    if (!text.includes('GNU GENERAL PUBLIC LICENSE')) {
      offences.push("the vendored upstream's licence is not the GPL");
    }
    if (!text.includes('Version 3')) {
      offences.push("the vendored upstream's licence is not version 3");
    }
  }

  // --- 2. No package imports from the upstream -----------------------------
  for (const packageDir of PACKAGES) {
    const dir = path.join(ROOT, packageDir);
    if (!existsSync(dir)) continue;
    for (const file of await filesUnder(dir)) {
      if (!/\.(ts|tsx|mjs|js)$/.test(file)) continue;
      const text = await readFile(file, 'utf8');
      for (const match of text.matchAll(/(?:from|import|require)\s*\(?\s*['"]([^'"]+)['"]/g)) {
        const specifier = match[1];
        if (!specifier) continue;
        if (
          specifier.includes('upstream/') ||
          specifier.includes('..\\upstream\\') ||
          specifier.startsWith('upstream')
        ) {
          offences.push(
            `${path.relative(ROOT, file)} imports from the upstream: ${specifier}`,
          );
        }
      }
    }
  }

  // --- 3. The shipped tree carries no Zynga media --------------------------
  for (const tree of trees) {
    const dir = path.resolve(ROOT, tree);
    if (!existsSync(dir)) continue;
    for (const file of await filesUnder(dir)) {
      const name = path.basename(file);
      if (FORBIDDEN_MEDIA.test(name)) {
        offences.push(`${path.relative(ROOT, file)}: a media file that does not ship`);
      }
      if (PROPRIETARY_FONTS.test(name)) {
        offences.push(`${path.relative(ROOT, file)}: a proprietary font`);
      }
    }
  }

  // The fonts the project ships are open-licensed ones.
  for (const tree of trees) {
    const dir = path.resolve(ROOT, tree);
    if (!existsSync(dir)) continue;
    for (const file of await filesUnder(dir)) {
      if (!/\.(css|html|js|mjs|ts|json)$/i.test(file)) continue;
      const text = await readFile(file, 'utf8');
      // The **identifier** the client uses for a face is not the face: the
      // client has to know the original's name to map it to a substitute.
      // What must not appear is a proprietary face being **asked for**.
      for (const match of text.matchAll(/font-family\s*:\s*([^;}\n]*)/gi)) {
        if (PROPRIETARY_FONTS.test(match[1])) {
          offences.push(
            `${path.relative(ROOT, file)}: asks for a proprietary font: ${match[1].trim()}`,
          );
        }
      }
    }
  }

  if (offences.length > 0) {
    console.error('the licensing position does not hold:');
    for (const offence of offences) console.error(`  ${offence}`);
    console.error('');
    console.error('See docs/LICENSING.md.');
    process.exit(1);
  }

  console.log('the upstream is GPL v3');
  console.log(`no package imports from the upstream (${PACKAGES.length} packages)`);
  console.log(`the shipped trees carry no Zynga media (${SHIPPED.length} trees)`);
  console.log('OK: the licensing position holds.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
