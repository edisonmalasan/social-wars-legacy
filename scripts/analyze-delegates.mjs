#!/usr/bin/env node
/**
 * Roadmap task B3 — unit and building behaviour tables.
 *
 * The client's gameplay behaviour is split across three places:
 *
 *   1. `core/Constants.as`              - 724 ID_* constants (item ids)
 *   2. `core/isoengine/delegates/DelegatesManager.as` - the authoritative
 *      `registerDelegate(<Class>, <config>, Constants.ID_*)` mapping from
 *      item id to behaviour class
 *   3. `core/isoengine/delegates/{units,buildings}/*.as` - the behaviour
 *      itself: overridden hooks, special attacks, projectiles, damage types
 *
 * This script joins the three and emits machine-readable tables, so the rules
 * engine can be written from data rather than from prose.
 *
 * Outputs:
 *   re/data/item-delegate-map.json    - item id -> delegate, config name
 *   re/data/unit-behaviour.json       - per-unit behaviour
 *   re/data/building-behaviour.json   - per-building behaviour
 */
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const AS = path.join(ROOT, '.work/as/basesec/scripts');
const OUT = path.join(ROOT, 're/data');

const read = (p) => readFile(p, 'utf8');

/** `public static const ID_FOO:uint = 123;` -> { ID_FOO: 123 } */
async function parseConstants() {
  const src = await read(path.join(AS, 'core/Constants.as'));
  const out = {};
  for (const m of src.matchAll(/public static const (ID_\w+)\s*:\s*\w+\s*=\s*(\d+)/g)) {
    out[m[1]] = Number(m[2]);
  }
  return out;
}

/**
 * `registerDelegate(DroneDelegate,{...},Constants.ID_UNIT_DRONE,...)`.
 * The call is spread over multiple lines, so match from one `registerDelegate(`
 * to the balancing close paren.
 */
async function parseDelegateRegistrations() {
  const src = await read(path.join(AS, 'core/isoengine/delegates/DelegatesManager.as'));
  const out = [];
  const re = /registerDelegate\s*\(\s*([A-Za-z_]\w*)\s*,/g;
  let m;
  while ((m = re.exec(src))) {
    // Walk forward from the call's own opening paren to its matching close paren,
    // so a config object containing nested braces/parens stays intact.
    const open = src.indexOf('(', m.index);
    let i = open;
    let depth = 0;
    let inStr = null;
    for (; i < src.length; i++) {
      const ch = src[i];
      if (inStr) {
        if (ch === '\\') i++;
        else if (ch === inStr) inStr = null;
        continue;
      }
      if (ch === '"' || ch === "'") { inStr = ch; continue; }
      if (ch === '(') depth++;
      else if (ch === ')') {
        depth--;
        if (depth === 0) break;
      }
    }
    const args = src.slice(open + 1, i);
    const ids = [...args.matchAll(/Constants\.(ID_\w+)/g)].map((x) => x[1]);
    const cfg = args.slice(args.indexOf(',') + 1);
    const projectiles = [...cfg.matchAll(/ProjectileDefinition\.(\w+)/g)].map((x) => x[1]);
    const specialDesc = /"specialDesc"\s*:\s*Language\.getLiteral\("([^"]*)"\)/.exec(cfg);
    out.push({
      delegate: m[1],
      idConstants: ids,
      projectiles: [...new Set(projectiles)],
      specialDesc: specialDesc ? specialDesc[1] : null,
    });
  }
  return out;
}

/** Decode the body of an AS3 string literal. */
function decodeAs3String(raw) {
  const simple = {
    n: '\n',
    r: '\r',
    t: '\t',
    b: '\b',
    f: '\f',
    v: '\v',
    0: '\0',
  };
  return raw.replace(/\\(u[0-9a-fA-F]{4}|[\s\S])/g, (_, escape) => {
    if (escape.length === 5 && escape[0] === 'u') {
      return String.fromCharCode(Number.parseInt(escape.slice(1), 16));
    }
    return simple[escape] ?? escape;
  });
}

/** The index of the paren that closes the one at `open`. */
function closeOf(src, open) {
  let depth = 0;
  let quote = null;
  for (let i = open; i < src.length; i++) {
    const ch = src[i];
    if (quote) {
      if (ch === '\\') i++;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === '(') {
      depth++;
    } else if (ch === ')') {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/** Split a call's arguments at the top-level commas. */
function splitTopLevel(text) {
  const args = [];
  let depth = 0;
  let start = 0;
  let quote = null;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quote) {
      if (ch === '\\') i++;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth--;
    } else if (ch === ',' && depth === 0) {
      args.push(text.slice(start, i).trim());
      start = i + 1;
    }
  }
  args.push(text.slice(start).trim());
  return args;
}

/** The value of a plain `"…"` argument, or null. */
function as3String(expr) {
  if (!expr || expr.length < 2 || expr[0] !== '"' || expr[expr.length - 1] !== '"') {
    return null;
  }
  return decodeAs3String(expr.slice(1, -1));
}

/** The source literal of a `Language.getLiteral("…")` argument, or null. */
function languageLiteral(expr) {
  if (!expr || !/^Language\.getLiteral\s*\(/.test(expr)) return null;
  const open = expr.indexOf('(');
  const close = closeOf(expr, open);
  if (close < 0) return null;
  return as3String(splitTopLevel(expr.slice(open + 1, close))[0]);
}

/** The text of a literal argument: `Language.getLiteral("…")` or `"…"`. */
function textOf(expr) {
  return languageLiteral(expr) ?? as3String(expr);
}

/** The method named by a function argument, bare or dotted. */
function functionRef(expr) {
  const text = (expr ?? '').trim();
  if (!text || text === 'null' || text === 'undefined') return null;
  const match = /^(?:this\.)?([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)$/.exec(text);
  return match ? match[1] : null;
}

/** The `arAttacks[n]` slot immediately before a constructor call. */
function attackIndexBefore(src, at) {
  const before = src.slice(Math.max(0, at - 160), at);
  const index = /arAttacks\[(\d+)\]\s*=\s*$/.exec(before)?.[1];
  return index === undefined ? null : Number(index);
}

/** `new SpecialUnitAttack(...)`, `…Spawn`, `…Limit`. */
function directAttacks(src) {
  const out = [];
  const re = /\bnew\s+(SpecialUnitAttack(?:Spawn|Limit)?)\s*\(/g;
  let match;
  while ((match = re.exec(src))) {
    const open = src.indexOf('(', match.index);
    const close = closeOf(src, open);
    if (close < 0) continue;
    const args = splitTopLevel(src.slice(open + 1, close));
    out.push({
      pos: match.index,
      index: attackIndexBefore(src, match.index),
      kind: match[1],
      name: textOf(args[4]),
      icon: as3String(args[5]),
      handler: functionRef(args[7]),
      cantMessage: textOf(args[6]),
      tooltip: textOf(args[9]),
    });
  }
  return out;
}

/**
 * `new SpecialUnitAttackCreator(id).withAttackName(...)...`
 *
 * The factory has no tooltip method; its `create()` calls the constructor
 * with nine arguments, so the attack's tooltip is the constructor default.
 */
function creatorAttacks(src) {
  const out = [];
  const re = /\bnew\s+SpecialUnitAttackCreator\s*\(\s*(\d+)\s*\)/g;
  let match;
  while ((match = re.exec(src))) {
    const open = src.indexOf('(', match.index);
    const close = closeOf(src, open);
    if (close < 0) continue;
    const attack = {
      pos: match.index,
      index: null,
      kind: 'SpecialUnitAttackCreator',
      name: null,
      icon: null,
      handler: null,
      cantMessage: null,
      tooltip: null,
    };
    let cursor = close + 1;
    for (;;) {
      const call = /^\s*\.\s*(with[A-Za-z]+)\s*\(/.exec(src.slice(cursor));
      if (!call) break;
      const methodOpen = cursor + call[0].lastIndexOf('(');
      const methodClose = closeOf(src, methodOpen);
      if (methodClose < 0) break;
      const args = splitTopLevel(src.slice(methodOpen + 1, methodClose));
      switch (call[1]) {
        case 'withAttackName':
          attack.name = languageLiteral(args[0]);
          break;
        case 'withImageThumbName':
          attack.icon = as3String(args[0]);
          break;
        case 'withCantMessage':
          attack.cantMessage = textOf(args[0]);
          break;
        case 'withOnAttack':
          attack.handler = functionRef(args[0]);
          break;
      }
      cursor = methodClose + 1;
    }
    out.push(attack);
  }
  return out;
}

/** Behaviour facts extracted from one delegate source file. */
function analyseDelegate(name, src) {
  const overrides = [...src.matchAll(/override\s+public function\s+(\w+)\s*\(/g)].map((x) => x[1]);
  const ownFunctions = [...src.matchAll(/(?<!override )\bpublic function\s+(\w+)\s*\(/g)]
    .map((x) => x[1])
    .filter((f) => !['get', 'set'].includes(f));

  const attacks = [...directAttacks(src), ...creatorAttacks(src)]
    .sort((a, b) => a.pos - b.pos)
    .map(({ pos, ...attack }) => attack);

  const projectiles = [...new Set([...src.matchAll(/ProjectileDefinition\.(\w+)/g)].map((x) => x[1]))];
  const damageClasses = [...new Set([
    ...[...src.matchAll(/new\s+(\w*Damage\w*)\s*\(/g)].map((x) => x[1]),
    ...[...src.matchAll(/\b(\w*Damage\w*)\b(?=\s*\.)/g)].map((x) => x[1]),
  ])];
  const specialAttackTypes = [...new Set([
    ...[...src.matchAll(/\b(\w*SpecialAttack\w*)\b/g)].map((x) => x[1]),
  ])];
  const spawnedIds = [...new Set([...src.matchAll(/Constants\.(ID_\w+)/g)].map((x) => x[1]))];
  const constants = [...src.matchAll(/private (?:static )?const\s+(\w+)\s*:\s*\w+\s*=\s*([-\d.]+)/g)].map(
    (x) => ({ name: x[1], value: Number(x[2]) }),
  );
  const literals = [...new Set([...src.matchAll(/getLiteral\("([^"]*)"\)/g)].map((x) => x[1]))];
  const imports = [...new Set([...src.matchAll(/import\s+([\w.]+)\s*;/g)].map((x) => x[1]))];

  return {
    delegate: name,
    bytes: src.length,
    overrides: [...new Set(overrides)],
    ownFunctions: [...new Set(ownFunctions)].filter((f) => !overrides.includes(f)),
    attacks,
    projectiles,
    damageClasses: damageClasses.filter((d) => d && d !== 'Damage'),
    specialAttackTypes: specialAttackTypes.filter((t) => t && t !== 'SpecialUnitAttack'),
    spawnedIds,
    constants,
    literals,
    imports,
  };
}

async function listAs(dir) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    if (e.isFile() && e.name.endsWith('.as')) out.push(e.name);
  }
  return out;
}

async function main() {
  const constants = await parseConstants();
  const registrations = await parseDelegateRegistrations();

  // item id -> delegate
  const byItem = new Map();
  for (const r of registrations) {
    for (const idc of r.idConstants) {
      const id = constants[idc];
      if (id === undefined) continue;
      if (!byItem.has(id)) byItem.set(id, { itemId: id, idConstant: idc, delegate: r.delegate, specialDesc: r.specialDesc, projectiles: r.projectiles });
    }
  }

  // Config names, so the table is human-readable.
  let configById = {};
  try {
    const cfg = JSON.parse(
      await read(path.join(ROOT, 'upstream/socialwarriors/config/main.json')),
    );
    configById = Object.fromEntries(cfg.items.map((i) => [Number(i.id), i.name]));
  } catch (e) {
    console.warn('config/main.json not readable, names omitted:', e.message);
  }

  const units = [];
  const buildings = [];
  for (const [dir, bucket] of [
    ['core/isoengine/delegates/units', units],
    ['core/isoengine/delegates/buildings', buildings],
  ]) {
    for (const file of await listAs(path.join(AS, dir))) {
      const name = file.replace(/\.as$/, '');
      const src = await read(path.join(AS, dir, file));
      const behaviour = analyseDelegate(name, src);
      const items = [...byItem.values()].filter((b) => b.delegate === name);
      behaviour.items = items.map((b) => ({
        itemId: b.itemId,
        idConstant: b.idConstant,
        name: configById[b.itemId] ?? null,
      }));
      behaviour.registeredProjectiles = [...new Set(items.flatMap((b) => b.projectiles))];
      bucket.push(behaviour);
    }
  }

  const itemMap = [...byItem.values()]
    .map((b) => ({
      itemId: b.itemId,
      name: configById[b.itemId] ?? null,
      idConstant: b.idConstant,
      delegate: b.delegate,
      specialDesc: b.specialDesc,
      registeredProjectiles: b.projectiles,
    }))
    .sort((a, b) => a.itemId - b.itemId);

  await mkdir(OUT, { recursive: true });
  await writeFile(
    path.join(OUT, 'item-delegate-map.json'),
    JSON.stringify(
      {
        note:
          'Item id -> behaviour delegate, from core/isoengine/delegates/DelegatesManager.as ' +
          'and core/Constants.as. Names come from config/main.json.',
        counts: {
          itemIdsMapped: itemMap.length,
          unitDelegates: units.length,
          buildingDelegates: buildings.length,
          registrationsParsed: registrations.length,
          idConstants: Object.keys(constants).length,
        },
        items: itemMap,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );
  await writeFile(
    path.join(OUT, 'unit-behaviour.json'),
    JSON.stringify({ note: 'Per-unit-delegate behaviour extracted from the decompiled AS3.', units }, null, 1) + '\n',
    'utf8',
  );
  await writeFile(
    path.join(OUT, 'building-behaviour.json'),
    JSON.stringify({ note: 'Per-building-delegate behaviour extracted from the decompiled AS3.', buildings }, null, 1) + '\n',
    'utf8',
  );

  const withAttacks = [...units, ...buildings].filter((d) => d.attacks.length);
  console.log(`item ids mapped to a delegate : ${itemMap.length}`);
  console.log(`unit delegates               : ${units.length}`);
  console.log(`building delegates           : ${buildings.length}`);
  console.log(`delegates with special attacks: ${withAttacks.length}`);
  console.log(`total special attacks        : ${withAttacks.reduce((n, d) => n + d.attacks.length, 0)}`);
  console.log(`delegates not mapped to an item: ${[...units, ...buildings].filter((d) => !d.items.length).length}`);
  console.log(`\nwrote re/data/{item-delegate-map,unit-behaviour,building-behaviour}.json`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
