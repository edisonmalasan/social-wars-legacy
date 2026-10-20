#!/usr/bin/env node
/**
 * Extract the tutorial's steps from the decompiled client.
 *
 * The tutorial is not one list. It is a base list of steps plus a number
 * of **conditional blocks** appended to it, each behind a flag:
 *
 *   steps = new Array({ ... })                 the base tutorial
 *   if (Base.Main.abVisitGeneralTutorial) {     the "visit the General" variant
 *      steps.push({ ... })
 *   }
 *
 * So each step is recorded with the gate it sits behind, because a player
 * only sees the steps whose gate is true for them.
 *
 * The scanner has to skip string literals: a step's title and lesson are
 * `Language.getLiteral("...")` calls, and a `)` inside one of them would
 * end the array early.
 *
 * Usage:
 *   node scripts/extract-tutorial-steps.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const SOURCE = path.join(ROOT, '.work/as/basesec/scripts/core/TutorialMain.as');
const OUT = path.join(ROOT, 're/data/tutorial-steps.json');

const ALIGNMENTS = ['ALIGN_TOP', 'ALIGN_BOTTOM', 'ALIGN_LEFT', 'ALIGN_RIGHT'];

/** The index just past the object literal at `start`, skipping strings. */
function skipStrings(source, start) {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let index = start; index < source.length; index++) {
    const char = source[index];
    if (inString) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') inString = false;
      continue;
    }
    if (char === '"') inString = true;
    else if (char === '{') depth += 1;
    else if (char === '}') {
      depth -= 1;
      if (depth === 0) return index + 1;
    }
  }
  return source.length;
}

/** The fields of one step. */
function parseFields(raw) {
  const fields = {};
  const pattern = /"(\w+)"\s*:\s*("(?:[^"\\]|\\.)*"|[^,}]+)/g;
  let match;
  while ((match = pattern.exec(raw)) !== null) {
    const key = match[1];
    const value = match[2].trim();
    if (ALIGNMENTS.includes(value)) {
      fields[key] = value;
    } else if (value.startsWith('"') && value.endsWith('"')) {
      const inner = value.slice(1, -1);
      // The client's own literals are a mix of booleans and strings.
      if (inner === 'true') fields[key] = true;
      else if (inner === 'false') fields[key] = false;
      else fields[key] = inner;
    } else if (value === 'true') {
      fields[key] = true;
    } else if (value === 'false') {
      fields[key] = false;
    } else {
      const number = Number(value);
      fields[key] = Number.isFinite(number) ? number : value;
    }
  }
  return fields;
}

/** The `if (...)` a push sits behind, if any. */
function gateBefore(source, position) {
  const window = source.slice(Math.max(0, position - 4000), position);
  const matches = [...window.matchAll(/if\s*\(([^{()]*)\)\s*\{/g)];
  if (matches.length === 0) return null;
  const condition = matches[matches.length - 1][1].trim();
  return condition || null;
}

async function main() {
  const source = await readFile(SOURCE, 'utf8');

  const constants = {};
  for (const match of source.matchAll(/public static const (STEP_\w+):int = (\d+);/g)) {
    constants[match[1]] = Number(match[2]);
  }

  const steps = [];

  // The base list.
  const base = source.indexOf('steps = new Array(');
  let index = source.indexOf('{', base);
  while (index < source.length) {
    if (source[index] !== '{') {
      index += 1;
      continue;
    }
    const end = skipStrings(source, index);
    const raw = source.slice(index, end);
    if (/"step"\s*:\s*STEP_/.test(raw)) {
      const fields = parseFields(raw);
      const name = fields.step;
      delete fields.step;
      const step = typeof name === 'string' ? (constants[name] ?? 0) : Number(name ?? 0);
      steps.push({ step, gate: null, ...fields });
    }
    index = end;
  }

  // The conditional pushes.
  for (const match of source.matchAll(/steps\.push\(\{/g)) {
    const start = source.indexOf('{', match.index);
    const end = skipStrings(source, start);
    const raw = source.slice(start, end);
    if (!/"step"\s*:\s*STEP_/.test(raw)) continue;
    const fields = parseFields(raw);
    const name = fields.step;
    delete fields.step;
    const step = typeof name === 'string' ? (constants[name] ?? 0) : Number(name ?? 0);
    steps.push({ step, gate: gateBefore(source, match.index), ...fields });
  }

  const manifest = {
    note:
      "The tutorial's steps, extracted from the client's TutorialMain.as. Each " +
      "step names a place on the screen and what the player is expected to do " +
      "there, so the sequence IS the tutorial. The client points at the place " +
      "with an arrow, and the arrow's anchor, rotation and alignment are here. " +
      'The tutorial is not one list: it is a base list plus conditional blocks ' +
      'appended to it, so each step records the gate it sits behind.',
    counts: {
      steps: steps.length,
      constants: Object.keys(constants).length,
      gated: steps.filter((step) => step.gate).length,
    },
    steps,
  };

  await writeFile(OUT, JSON.stringify(manifest, null, 1) + '\n', 'utf8');
  console.log(`wrote ${OUT}`);
  console.log(`  ${manifest.counts.steps} steps, ${manifest.counts.gated} behind a gate`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
