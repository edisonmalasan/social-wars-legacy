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

/** Behaviour facts extracted from one delegate source file. */
function analyseDelegate(name, src) {
  const overrides = [...src.matchAll(/override\s+public function\s+(\w+)\s*\(/g)].map((x) => x[1]);
  const ownFunctions = [...src.matchAll(/(?<!override )\bpublic function\s+(\w+)\s*\(/g)]
    .map((x) => x[1])
    .filter((f) => !['get', 'set'].includes(f));

  // arAttacks[n] = new SpecialUnitAttack(...)  /  SpecialUnitAttackSpawn / SpecialUnitAttackLimit
  const attacks = [];
  const attackRe = /new\s+(SpecialUnitAttack\w*)\s*\(([\s\S]{0,1500}?)\)\s*;/g;
  let am;
  while ((am = attackRe.exec(src))) {
    const args = am[2];
    const literals = [...args.matchAll(/getLiteral\("([^"]*)"\)/g)].map((x) => x[1]);
    // The slot index is assigned just before the constructor: `arAttacks[n] = new ...`
    const before = src.slice(Math.max(0, am.index - 120), am.index);
    const index = /arAttacks\[(\d+)\]\s*=\s*$/.exec(before)?.[1];
    const icon = /"([a-z0-9_]+)"\s*,\s*(?:Language|null|"")/.exec(args)?.[1] ?? null;
    // The handler is the `this.<method>` argument that is not a literal.
    const handlers = [...args.matchAll(/this\.(\w+)/g)].map((x) => x[1]);
    const handler = handlers.find((h) => !/^(cooldown|frames|specialDesc)$/i.test(h)) ?? null;
    attacks.push({
      index: index !== undefined ? Number(index) : null,
      kind: am[1],
      name: literals[0] ?? null,
      icon,
      handler,
      extraLiterals: literals.slice(1, 4),
    });
  }

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
