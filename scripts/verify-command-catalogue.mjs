#!/usr/bin/env node
/**
 * Cross-check the three sources of the command list.
 *
 * There are three independent records of which commands the client can send,
 * and they must agree:
 *
 *   A. the decompiled client's own command classes - every `Cmd*.as`,
 *      `AdminCmd*.as` and `SystemCmd*.as` that calls `super("<name>")`.
 *      This is the **authority**: the client is the specification.
 *   B. the report's catalogue table in
 *      `re/docs/03-commands-quests-economy.md`, transcribed from the same
 *      classes.
 *   C. the protocol package's `COMMAND_NAMES`.
 *
 * The upstream's `command.py` is also checked, but only as a *report*: it
 * handles 62 of the 92 and silently drops the rest, which is a finding
 * about the upstream, not an error here.
 *
 * This check exists because the list drifted once already. It was 59 names
 * when the client sends 92, and it carried two names that do not exist at
 * all. A check that names the thing it expects to exist is worth more than
 * a count that merely looks right.
 *
 * Usage:
 *   node scripts/verify-command-catalogue.mjs
 */
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const COMMANDS_DIR = path.join(ROOT, '.work/as/basesec/scripts/commands');
const REPORT = path.join(ROOT, 're/docs/03-commands-quests-economy.md');
const PROTOCOL = path.join(ROOT, 'packages/protocol/src/index.ts');
const UPSTREAM = path.join(ROOT, 'upstream/socialwarriors/command.py');

/**
 * The client's own command classes.
 *
 * A class names itself in **two** ways: `super("<name>")`, and
 * `commandID = "<name>"` for a subclass that overrides its parent's name
 * (`CmdCollectAlliancesBonus` does the second, and it is how
 * `win_alliance_daily_bonus` exists at all).
 *
 * And a name may contain a **digit**: `push_queue_unit2` is a real
 * command. A regex that allows neither misses two commands, silently.
 */
async function clientCommands() {
  const names = new Map();
  let files;
  try {
    files = await readdir(COMMANDS_DIR);
  } catch {
    return null;
  }
  for (const file of files) {
    if (!file.endsWith('.as')) continue;
    const body = await readFile(path.join(COMMANDS_DIR, file), 'utf8');
    const found = new Set([
      ...[...body.matchAll(/super\(\s*"([a-z_0-9]+)"\s*\)/g)].map((m) => m[1]),
      ...[...body.matchAll(/commandID\s*=\s*"([a-z_0-9]+)"/g)].map((m) => m[1]),
    ]);
    for (const name of found) names.set(name, file);
  }
  return names;
}

/** The report's catalogue. */
async function catalogueCommands() {
  const report = await readFile(REPORT, 'utf8');
  const names = new Map();
  for (const line of report.split('\n')) {
    const match = line.match(/^\|\s*(\d+)\s*\|\s*`([a-z_0-9]+)`\s*\|/);
    if (match) names.set(match[2], { row: Number(match[1]), class: match[2] });
  }
  return names;
}

/** The protocol package's list. */
async function protocolCommands() {
  const source = await readFile(PROTOCOL, 'utf8');
  const match = source.match(/COMMAND_NAMES\s*=\s*\[([\s\S]*?)\]\s*as const/);
  if (!match) return null;
  return new Set(
    match[1]
      .split(',')
      .map((s) => s.trim().replace(/^'|'$/g, ''))
      .filter((s) => s.length > 0),
  );
}

/** The upstream's handled commands. */
async function upstreamCommands() {
  try {
    const source = await readFile(UPSTREAM, 'utf8');
    return new Set([...source.matchAll(/cmd\s*==\s*["']([a-z_0-9]+)["']/g)].map((m) => m[1]));
  } catch {
    return null;
  }
}

function difference(a, b) {
  return [...a].filter((x) => !b.has(x)).sort();
}

async function main() {
  const client = await clientCommands();
  if (!client) {
    console.error('the decompiled client is not available at .work/as/basesec/scripts/commands');
    console.error('run: node scripts/decompile-client.mjs');
    process.exit(2);
  }

  const catalogue = await catalogueCommands();
  const protocol = await protocolCommands();
  const upstream = await upstreamCommands();

  const clientSet = new Set(client.keys());
  const catalogueSet = new Set(catalogue.keys());

  let failures = 0;

  console.log(`the client's command classes : ${clientSet.size}`);
  console.log(`the report's catalogue        : ${catalogueSet.size}`);
  console.log(`the protocol's COMMAND_NAMES  : ${protocol ? protocol.size : 0}`);
  console.log(`the upstream handles          : ${upstream ? upstream.size : 0}`);
  console.log('');

  // A vs B: the catalogue must transcribe the client exactly.
  const clientOnly = difference(clientSet, catalogueSet);
  const catalogueOnly = difference(catalogueSet, clientSet);
  if (clientOnly.length === 0 && catalogueOnly.length === 0) {
    console.log('OK: the catalogue transcribes the client exactly.');
  } else {
    failures += 1;
    console.log('DIFFERS: the catalogue and the client disagree.');
    for (const name of clientOnly) console.log(`  only in the client  : ${name}`);
    for (const name of catalogueOnly) console.log(`  only in the catalogue: ${name}`);
  }
  console.log('');

  // The catalogue's rows must be numbered 1..n with no gaps, or a row was
  // dropped when it was transcribed.
  const rows = [...catalogue.values()].map((entry) => entry.row).sort((a, b) => a - b);
  const expected = rows.map((_, index) => index + 1);
  if (rows.length === expected.length && rows.every((row, index) => row === expected[index])) {
    console.log(`OK: the catalogue's rows are numbered 1..${rows.length} with no gaps.`);
  } else {
    failures += 1;
    console.log('DIFFERS: the catalogue has a gap in its row numbers.');
    console.log(`  rows found: ${rows.join(', ')}`);
  }
  console.log('');

  // A vs C: the protocol's list must be the client's list.
  if (protocol) {
    const missing = difference(clientSet, protocol);
    const extra = difference(protocol, clientSet);
    if (missing.length === 0 && extra.length === 0) {
      console.log('OK: COMMAND_NAMES is the client command list.');
    } else {
      failures += 1;
      console.log('DIFFERS: COMMAND_NAMES is not the client command list.');
      for (const name of missing) console.log(`  missing : ${name}`);
      for (const name of extra) console.log(`  unknown : ${name}`);
    }
    console.log('');
  }

  // The upstream's gaps are a finding, not an error.
  if (upstream) {
    const dropped = difference(clientSet, upstream);
    console.log(
      `the upstream silently drops ${dropped.length} of the ${clientSet.size} ` +
        `commands the client can send.`,
    );
  }

  if (failures > 0) {
    console.log('');
    console.log(`${failures} check(s) failed.`);
    process.exit(1);
  }
  console.log('');
  console.log('Every source agrees.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
