#!/usr/bin/env node
/**
 * Roadmap task B6 — the UI screen inventory.
 *
 * The modern client must rebuild the whole UI: the original Flash UI chrome is not in
 * the asset tree. This script inventories every UI class in the decompiled client so the
 * rebuild has a backlog rather than a surprise.
 *
 * Outputs:
 *   re/data/ui-screens.json
 */
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const AS = path.join(ROOT, '.work/as/basesec/scripts');
const OUT = path.join(ROOT, 're/data');

const read = (p) => readFile(p, 'utf8');

/** Directories that hold user-interface code. */
const UI_DIRS = ['popups', 'GUI'];
/**
 * Top-level files whose name marks them as UI. Most of the top-level UI is a
 * `*MC.as` movie clip; the prefix list catches the non-MC ones.
 */
const UI_FILE_RE =
  /^(Popup|PopOver|InfoButton|InfoPopup|Button|Dialog|Tab|Menu|HUD|Gui|GUI|Screen|Panel|Counter|Badge|Toast|Tooltip|Icon|Store|SquareTool|Goals|Signal|Hint|Dropdown|Bottom)/;

async function walk(dir, rel = '') {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    if (e.isDirectory()) {
      out.push(...(await walk(path.join(dir, e.name), path.join(rel, e.name))));
    } else if (e.isFile() && e.name.endsWith('.as')) {
      out.push(path.join(rel, e.name));
    }
  }
  return out;
}

/**
 * Classify a UI class by what it does, from its declared surface.
 * The classification is deliberately mechanical: it is a backlog, not a design.
 */
function classify(rel, src) {
  const cls = /public class (\w+)/.exec(src)?.[1] ?? null;
  const extendsName = /public class \w+ extends ([\w.<>]+)/.exec(src)?.[1] ?? null;
  const opens = /public function (?:open|show|display|showPopup|addPopup)\b/.test(src);
  const closes = /public function (?:close|hide|dispose|remove)\b/.test(src);
  const isPopup = /extends PopupObject/.test(src) || /extends Popup\w*MC/.test(src) || rel.startsWith('popups');
  const isGui = rel.startsWith('GUI');
  const isMc = /MC$/.test(cls ?? '') || /extends MovieClip/.test(src);
  const isInfoButton = /InfoButton/.test(cls ?? '');
  const isTab = /Tab/.test(cls ?? '');
  const isButton = /Button/.test(cls ?? '');
  const literals = [...new Set([...src.matchAll(/getLiteral\("([^"]*)"\)/g)].map((x) => x[1]))];
  const images = [...new Set([...src.matchAll(/["']([\w/-]+\.(?:png|jpg|swf))["']/g)].map((x) => x[1]))];
  const functions = [...new Set([...src.matchAll(/(?<!override )\bpublic function\s+(\w+)\s*\(/g)].map((x) => x[1]))];
  const overrides = [...new Set([...src.matchAll(/override\s+public function\s+(\w+)\s*\(/g)].map((x) => x[1]))];

  let kind = 'other';
  if (isPopup) kind = 'popup';
  else if (isGui) kind = 'gui-panel';
  else if (isInfoButton) kind = 'info-button';
  else if (isTab) kind = 'tab';
  else if (isButton) kind = 'button';
  else if (isMc) kind = 'movieclip';

  return {
    class: cls,
    path: rel.replace(/\\/g, '/'),
    kind,
    extends: extendsName,
    isMovieClip: isMc,
    hasOpen: opens,
    hasClose: closes,
    literals: literals.slice(0, 12),
    literalCount: literals.length,
    images: images.slice(0, 12),
    functions: functions.filter((f) => !['get', 'set'].includes(f)).slice(0, 20),
    overrides: overrides.slice(0, 20),
    bytes: src.length,
  };
}

async function main() {
  const files = [];
  for (const d of UI_DIRS) files.push(...(await walk(path.join(AS, d), d)));
  const topLevel = (await readdir(AS, { withFileTypes: true }))
    .filter((e) => e.isFile() && e.name.endsWith('.as'))
    .filter((e) => UI_FILE_RE.test(e.name) || /MC$/.test(e.name))
    .map((e) => e.name);
  files.push(...topLevel);

  const screens = [];
  for (const rel of files.sort()) {
    const src = await read(path.join(AS, ...rel.split(/[\\/]/)));
    screens.push(classify(rel, src));
  }

  const byKind = {};
  for (const s of screens) byKind[s.kind] = (byKind[s.kind] ?? 0) + 1;

  await mkdir(OUT, { recursive: true });
  await writeFile(
    path.join(OUT, 'ui-screens.json'),
    JSON.stringify(
      {
        note:
          'Inventory of every UI class in the decompiled client. The original Flash UI ' +
          'chrome is not in the asset tree, so the modern client must rebuild it; this ' +
          'is the backlog.',
        counts: { total: screens.length, byKind },
        screens,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );
  console.log(`UI classes inventoried : ${screens.length}`);
  console.log('by kind               :', JSON.stringify(byKind));
  console.log('\nwrote re/data/ui-screens.json');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
