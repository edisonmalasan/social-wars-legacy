#!/usr/bin/env node
/**
 * Group E4 — the one-scenario Flash-client differential: an HONEST evidence audit.
 *
 * The roadmap asks for a diff of the rules engine against the original Flash
 * client. The repository contains exactly ONE real captured `end_quest`
 * payload (re/evidence/live/command-payloads.txt, the batch #33 line). This
 * script reads that capture and reports precisely what it proves and what it
 * does not. It is strictly read-only: it never edits the evidence file and it
 * never mutates game state.
 *
 * VERDICT: no comparison can be made. The capture's `res` vector is the
 * client-DECLARED 8-slot resource delta that the upstream `command.php`
 * applied verbatim (re/docs/06-LIVE-SESSION-PROTOCOL.md §3.3 and §9 item 6).
 * It is the client's own claim, not a server-computed outcome. The client's
 * `win` flag and losses are likewise self-reported and explicitly untrusted.
 * Diffing the pure rules engine against that vector would be circular — it
 * would compare our computation against the thing our computation is meant to
 * replace. There is also no seed, no enemy roster, no server quest state and
 * no wallet-before/after in the capture, so there are no inputs with which to
 * drive the deterministic simulation either.
 *
 * This script therefore exits 0 with a truthful "cannot compare" report. E4's
 * Flash-differential item stays open; it needs a Flash rig that both drives
 * the scenarios and records the authoritative server result.
 */
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const CAPTURE = path.join(ROOT, 're/evidence/live/command-payloads.txt');

const RESOURCE_ORDER = ['energy', 'xp', 'gold', 'wood', 'oil', 'steel', 'cash', 'mana'];

/** Parse the single real `end_quest` capture; never modify it. */
function parseCapture(text) {
  const lines = text.split(/\r?\n/);
  const found = [];
  lines.forEach((line, i) => {
    const m = line.match(/^\s*cmd\s+end_quest\s+args=(\[.*\])\s+res=(\[[^\]]*\])\s*$/);
    if (!m) return;
    const argMatch = m[1].match(/^\[\s*'((?:[^'\\]|\\.)*)'\s*\]$/);
    if (!argMatch) throw new Error(`unrecognised args shape on line ${i + 1}`);
    // The evidence stores the JSON blob inside single quotes, without escapes.
    const json = argMatch[1].replace(/\\(["\\])/g, '$1');
    const payload = JSON.parse(json);
    const res = m[2]
      .slice(1, -1)
      .split(',')
      .map((n) => n.trim())
      .filter((n) => n !== '')
      .map(Number);
    // The batch header is the nearest preceding `--- batch #N ...` line.
    let batch = '(not found)';
    for (let j = i - 1; j >= 0; j--) {
      const b = lines[j].match(/--- batch #\d+/);
      if (b) {
        batch = b[0];
        break;
      }
    }
    found.push({ line: i + 1, batch, payload, res, raw: line.trim() });
  });
  return found;
}

function printRows(rows) {
  for (const [label, value, evidence] of rows) {
    console.log(`  ${label.padEnd(24)} ${value}`);
    console.log(`  ${''.padEnd(24)} ↳ ${evidence}`);
  }
}

async function main() {
  let text;
  try {
    text = await readFile(CAPTURE, 'utf8');
  } catch (error) {
    console.error(`cannot read the capture: ${CAPTURE}`);
    console.error(error);
    process.exit(1);
  }

  const captures = parseCapture(text);

  console.log('=== E4 flash differential — read-only evidence audit ===');
  console.log(`evidence file : ${path.relative(ROOT, CAPTURE)}`);
  console.log(`end_quest captures found : ${captures.length}`);
  if (captures.length !== 1) {
    console.log('');
    console.log('NOTE: the one-scenario scope assumption no longer holds. Re-audit');
    console.log('      before claiming any differential; this report covers only');
    console.log('      captures that were actually present.');
  }

  for (const c of captures) {
    const p = c.payload;
    const losses = Array.isArray(p.units)
      ? p.units.map((u) => Math.max(0, Number(u[2]) - Number(u[3])))
      : [];

    console.log('');
    console.log(`--- captured command (${path.relative(ROOT, CAPTURE)}:${c.line}, ${c.batch}) ---`);
    console.log(`  ${c.raw}`);

    console.log('');
    console.log('WHAT THE CAPTURE PROVES');
    printRows([
      [
        'command',
        'end_quest (one real live capture)',
        `${path.relative(ROOT, CAPTURE)}:${c.line}; this is the only end_quest line in the file`,
      ],
      [
        'quest id',
        `${p.quest_id} = QUEST_01_BAZOOKA`,
        're/docs/03-commands-quests-economy.md:744 and packages/rules/src/quest.ts:99,547-548',
      ],
      [
        'declared difficulty',
        String(p.difficulty),
        're/docs/06-LIVE-SESSION-PROTOCOL.md:262 (server clamps to 1..3)',
      ],
      ['declared map', String(p.map), 're/docs/06-LIVE-SESSION-PROTOCOL.md:263'],
      [
        'declared voluntary_end',
        String(p.voluntary_end),
        'the player ended the quest early (re/docs/06-LIVE-SESSION-PROTOCOL.md:265)',
      ],
      [
        'declared win',
        String(p.win),
        'CLIENT-DECLARED — re/docs/06-LIVE-SESSION-PROTOCOL.md:270-272',
      ],
      ['declared duration', `${p.duration} s`, 're/docs/06-LIVE-SESSION-PROTOCOL.md:268'],
      [
        'declared losses',
        JSON.stringify(losses) + ' (A - B = 0)',
        'units [item_id, sent, A, B]; 1007 = Soldier (re/docs/06-LIVE-SESSION-PROTOCOL.md:224,267,270)',
      ],
      [
        'declared res vector',
        JSON.stringify(c.res),
        `8-slot order [${RESOURCE_ORDER.join(', ')}] (re/docs/06-LIVE-SESSION-PROTOCOL.md:147)`,
      ],
    ]);

    console.log('');
    console.log('WHAT THE `res` VECTOR ACTUALLY IS');
    console.log('  The client declares the resource delta for every command; the upstream');
    console.log('  server applies it verbatim. It is NOT an independently computed outcome.');
    console.log('    - re/docs/06-LIVE-SESSION-PROTOCOL.md:379-380 (§9 item 6)');
    console.log('    - re/docs/03-commands-quests-economy.md:1032 (reward delta is client-controlled)');
    console.log('    - packages/rules/src/commandcost.ts:5-16 (why the clone refuses to read it)');
    console.log(`  Here all ${c.res.length} slots are zero, so the client claimed no reward. That`);
    console.log('  is consistent with a voluntary loss, but it is still only a claim.');

    console.log('');
    console.log('WHAT THE UPSTREAM SERVER DID WITH IT');
    console.log('  upstream/socialwarriors/command.py:752-806 parses the client JSON, removes');
    console.log('  client-declared unit losses, stamps questTimes[quest_id], and prints');
    console.log('  Won/Failed from the client `win` flag. It computes NO outcome, validates');
    console.log('  NO victory and grants NO loot of its own.');

    console.log('');
    console.log('WHAT THE CAPTURE DOES NOT CONTAIN (the evidence gap)');
    const gaps = [
      ['server-issued seed', 'no seed is captured, so the deterministic battle cannot be replayed'],
      ['server-computed outcome', 'no authoritative loot/damage/victory result exists to diff against'],
      ['wallet before / after', 'no authoritative wallet snapshot; `res` is the client claim itself'],
      ['active quest state', 'no validated kills, script events or ledger events (packages/server/src/apply.ts:3286-3321)'],
      ['enemy roster / map state', 'no defenders or map contents to feed the pure simulation'],
      ['trustworthy win', 'the `win` flag is self-reported and explicitly untrusted'],
      ['an end_quest price path', 'the rules engine never prices end_quest (packages/rules/src/commandcost.ts:119-138,221-417)'],
      ['a Flash rig', 'the other 49 golden scenarios were never driven through the original client'],
    ];
    for (const [name, detail] of gaps) {
      console.log(`  - ${name.padEnd(24)} ${detail}`);
    }

    console.log('');
    console.log('COMPARISON ATTEMPTED: none.');
    console.log('  Every value the capture records is either a client declaration (args and');
    console.log('  res, applied verbatim upstream) or metadata. Diffing the pure rules engine');
    console.log('  against those values would validate nothing: it would compare our result');
    console.log('  with the claim our server is designed to ignore. There is no independent');
    console.log('  server-side result in the capture to use as a differential oracle.');

    console.log('');
    console.log('VERDICT: insufficient evidence — E4 stays blocked.');
    console.log('  Exact gap: ONE captured end_quest request whose `res` is the client-declared');
    console.log('  resource delta (applied verbatim by the upstream server), with no captured');
    console.log('  server-side outcome, seed, quest state or wallet snapshot to compare against.');
    console.log('  Closing E4 needs a Flash rig that drives all 50 scenarios AND records the');
    console.log('  authoritative server result for each. This script does not close E4.');
  }

  console.log('');
  console.log('exit 0 — the audit ran; the honest result is "cannot compare".');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
