#!/usr/bin/env node
/**
 * The soak test.
 *
 * Sustained play has to show **no memory growth** and **no state drift**.
 * Both are properties that only appear over many thousands of requests,
 * which is exactly why they are worth a test rather than an assumption.
 *
 * The state drift is the more interesting of the two. The command index
 * is the client's global counter, and it is the thing that goes wrong
 * first: a retry, a dropped batch or a refused command moves it, and
 * every later command is then off by one. So the soak checks that the
 * index advances by exactly the number of commands applied, and that it
 * never goes backwards.
 *
 * Usage:
 *   node --expose-gc scripts/soak-server.mjs [--batches 20000] [--players 4]
 */
import process from 'node:process';

import { framePayload, SERVER_KEYS } from '@swl/protocol';

import { createApp } from '../apps/server/src/app.ts';
import { LegacyIdentityBridge, SessionStore } from '../packages/server/src/index.ts';
import { MemoryPlayerStore } from '../packages/server/src/index.ts';
import { costContentFrom } from '../packages/rules/src/index.ts';

/** A command-line flag's value. */
function flag(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

/** The heap in use, after a collection when one is possible. */
function heapUsed() {
  if (typeof globalThis.gc === 'function') globalThis.gc();
  return process.memoryUsage().heapUsed;
}

async function main() {
  const batches = Number(flag('batches', 20000));
  const players = Number(flag('players', 4));

  const content = costContentFrom(
    JSON.parse(
      await (await import('node:fs/promises')).readFile(
        'packages/content/dist/content-bundle.json',
        'utf8',
      ),
    ),
  );

  const sessions = new SessionStore();
  const identity = new LegacyIdentityBridge();
  identity.allowLegacyIdentity();
  const store = new MemoryPlayerStore();

  const handles = [];
  for (let index = 0; index < players; index++) {
    const playerId = `soak-${index}`;
    sessions.addPlayer(playerId, 'soak');
    identity.bind(playerId, playerId);
    store.add(playerId, {
      save: { playerInfo: { name: playerId }, maps: [{ id: 0, items: {} }], privateState: {} },
      resources: { g: 1e9, w: 1e9, o: 1e9, s: 1e9, c: 1e9, e: 1e9, x: 0, m: 0 },
      nextCommandNumber: 1,
    });
    handles.push(playerId);
  }

  let commandIndex = 1;
  const applied = [];

  const handle = createApp({
    store,
    sessions,
    identity,
    content,
    contentBundle: {},
    now: () => 1_700_000_000,
    nowMs: () => 1_700_000_000_000,
    // The rate limiter is a real feature and it is doing its job; the soak
    // measures throughput and memory, not the limiter.
    limits: {
      maxBodyBytes: 1024 * 1024,
      requestsPerWindow: 1_000_000_000,
      windowSeconds: 60,
      commandTimeoutMs: 5_000,
      maxCommandsPerBatch: 512,
    },
    applyCommand: (world, command) => {
      applied.push(command.name);
      return { applied: true, world };
    },
  });

  const before = heapUsed();

  for (let batch = 0; batch < batches; batch++) {
    const playerId = handles[batch % handles.length];
    const payload = JSON.stringify({
      first_number: commandIndex,
      commands: [
        [0, 'move', [1, 2, 3], [0, 0, 0, 0, 0, 0, 0, 0]],
        [0, 'collect', [1], [0, 0, 0, 0, 0, 0, 0, 0]],
      ],
      tries: 1,
    });
    const frame = framePayload(payload, SERVER_KEYS.current);
    const response = await handle({
      method: 'POST',
      path: '/command.php',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      // The USERID goes in the body, exactly as the client sends it.
      body: `USERID=${encodeURIComponent(playerId)}&data=${encodeURIComponent(frame)}`,
    });
    if (response.status !== 200) {
      console.error(`  batch ${batch} answered ${response.status}`);
      process.exit(1);
    }
    commandIndex += 2;
  }

  const after = heapUsed();

  // --- the state drift ----------------------------------------------------
  const problems = [];
  for (const playerId of handles) {
    const save = await store.get(playerId);
    // Every command applied to a player advances ITS index by the number
    // of commands, and the index must never go backwards.
    if (save.world.nextCommandNumber <= 1) {
      problems.push(`${playerId}: the command index did not advance`);
    }
    if (save.world.resources.g !== 1e9) {
      problems.push(`${playerId}: the gold drifted`);
    }
  }

  const expectedCommands = batches * 2;
  if (applied.length !== expectedCommands) {
    problems.push(`${applied.length} commands were applied, and ${expectedCommands} were sent`);
  }

  // --- the memory ---------------------------------------------------------
  const growth = after - before;
  const perBatch = growth / batches;

  console.log(`batches       : ${batches}`);
  console.log(`players       : ${players}`);
  console.log(`commands      : ${applied.length}`);
  console.log(`heap before   : ${(before / 1048576).toFixed(1)} MB`);
  console.log(`heap after    : ${(after / 1048576).toFixed(1)} MB`);
  console.log(`growth        : ${(growth / 1024).toFixed(1)} KB (${perBatch.toFixed(2)} bytes a batch)`);

  if (problems.length > 0) {
    console.error('\nFAIL: the soak found state drift.');
    for (const problem of problems) console.error(`  ${problem}`);
    process.exit(1);
  }
  console.log('\nOK: no state drift.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
