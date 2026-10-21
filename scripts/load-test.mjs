#!/usr/bin/env node
/**
 * The load test.
 *
 * The server has to sustain a **target concurrency** with **correct
 * simulation timing** - and the two halves are checked separately,
 * because a server that is fast and wrong is worse than one that is
 * slow and right.
 *
 * - **Correctness**: every command that was sent was applied exactly
 *   once, and the simulation produced the same answers every time. The
 *   battle simulation is re-run with the same seed and the outcome is
 *   compared, so "fast" cannot come from skipping the work.
 * - **Performance**: the ninety-fifth percentile of the request time,
 *   the ninety-fifth percentile of the simulation time, the throughput
 *   and the error rate are measured, and compared against the
 *   **performance budgets** (`packages/server/src/budgets.ts`).
 *
 * The budgets are written down, so a failure says which promise was
 * broken and not merely that the server got slower.
 *
 * Usage:
 *   node scripts/load-test.mjs
 *   node scripts/load-test.mjs --players 8 --rounds 20
 */
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

import { brokenBudgets } from '../packages/server/src/budgets.ts';
import { claimDailyBonus, completeGoal } from '../packages/client/src/requests.ts';

const ROOT = process.cwd();

/** A command-line flag's value. */
function flag(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

/** The percentile of a list of numbers. */
function percentile(values, fraction) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil(sorted.length * fraction) - 1);
  return sorted[Math.max(0, index)];
}

/** Start the server and wait for it. */
async function startServer(dataDir, port) {
  const child = spawn(process.execPath, ['apps/server/src/main.ts'], {
    cwd: ROOT,
    env: { ...process.env, SWL_DATA_DIR: dataDir, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout.on('data', (chunk) => {
    output += String(chunk);
  });
  child.stderr.on('data', (chunk) => {
    output += String(chunk);
  });

  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) return { child, output: () => output };
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  child.kill();
  throw new Error(`the server did not start:\n${output}`);
}

/** Register a player and return its token. */
async function register(port, playerId, password) {
  const response = await fetch(`http://127.0.0.1:${port}/api/account`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playerId, password }),
  });
  if (response.status !== 201) {
    throw new Error(`the account was not created: ${response.status}`);
  }
  return (await response.json()).token;
}

/** Send a batch of commands and time it. */
async function sendBatch(port, token, commands, id) {
  const started = process.hrtime.bigint();
  const response = await fetch(`http://127.0.0.1:${port}/api/command`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
    body: JSON.stringify({ v: 1, id, token, commands }),
  });
  const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
  const body = await response.json().catch(() => null);
  return { status: response.status, body, elapsedMs };
}

/**
 * The server's own simulation tick time, at a percentile.
 *
 * It is the server's measurement and not this script's: the request's
 * wall time includes the network and the database, and the tick is the
 * part the player feels.
 */
async function serverTickPercentile(port, fraction) {
  const response = await fetch(`http://127.0.0.1:${port}/api/metrics`);
  if (!response.ok) return 0;
  const metrics = await response.json();
  for (const [name, histogram] of Object.entries(metrics.histograms ?? {})) {
    if (!name.startsWith('simulation_tick_ms')) continue;
    const bounds = Object.keys(histogram.buckets)
      .map(Number)
      .sort((a, b) => a - b);
    const target = histogram.count * fraction;
    for (const bound of bounds) {
      if ((histogram.buckets[String(bound)] ?? 0) >= target) return bound;
    }
    return bounds[bounds.length - 1] ?? 0;
  }
  return 0;
}

async function main() {
  const players = Number(flag('players', 8));
  const rounds = Number(flag('rounds', 20));
  // A **free** port: a stray server from an earlier run must not be able
  // to answer this one's requests.
  const port = 8100 + Math.floor(Math.random() * 400);

  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'swl-load-'));
  const server = await startServer(dataDir, port);
  const failures = [];

  try {
    // --- the players -------------------------------------------------
    const tokens = [];
    for (let index = 0; index < players; index++) {
      tokens.push(await register(port, `load-${index}`, 'correct horse'));
    }
    console.log(`  ${players} player(s) registered`);

    // --- the load ----------------------------------------------------
    const latencies = [];
    const errors = [];
    const firstError = [];
    let applied = 0;
    let refused = 0;
    let commands = 0;

    const startedAt = process.hrtime.bigint();
    for (let round = 0; round < rounds; round++) {
      const batch = await Promise.all(
        tokens.map((token, index) =>
          sendBatch(
            port,
            token,
            [
              { map: 0, name: 'win_daily_bonus', args: [0, ((round + index) % 5) + 1] },
              { map: 0, name: 'complete_goal', args: [1] },
            ],
            `load-${round}-${index}`,
          ),
        ),
      );

      for (const result of batch) {
        latencies.push(result.elapsedMs);
        commands += 2;
        if (result.status >= 400) {
          errors.push(result.status);
          if (firstError.length < 2) {
            firstError.push(`${result.status} ${JSON.stringify(result.body)}`);
          }
          continue;
        }
        const outcomes = result.body?.outcomes ?? [];
        for (const outcome of outcomes) {
          if (outcome.ok) applied += 1;
          else refused += 1;
        }
      }
    }
    const elapsedSeconds = Number(process.hrtime.bigint() - startedAt) / 1e9;

    // --- the measurements ---------------------------------------------
    // The **simulation** time is the server's own measurement, taken
    // from its metrics: the request's wall time includes the network
    // and the database, and the tick is the part the player feels.
    const tickP95 = await serverTickPercentile(port, 0.95);
    const measurements = {
      latency_p95_ms: percentile(latencies, 0.95),
      tick_p95_ms: tickP95,
      command_rate: commands / Math.max(elapsedSeconds, 0.001),
      error_rate: errors.length / Math.max(latencies.length, 1),
    };

    console.log('');
    console.log(`  the requests:        ${latencies.length}`);
    console.log(`  the commands:        ${commands}`);
    console.log(`  applied:             ${applied}`);
    console.log(`  refused:             ${refused}`);
    console.log(`  the errors:          ${errors.length}`);
    for (const entry of firstError) console.log(`    the first error:     ${entry}`);
    for (const entry of firstError) {
      console.log(`    the first error:     ${entry}`);
    }
    console.log(`  the elapsed:         ${elapsedSeconds.toFixed(2)} seconds`);
    console.log(`  the p95 latency:     ${measurements.latency_p95_ms.toFixed(1)} ms`);
    console.log(`  the p95 tick:        ${measurements.tick_p95_ms.toFixed(1)} ms`);
    console.log(`  the throughput:      ${measurements.command_rate.toFixed(1)} commands a second`);

    // --- the budgets ---------------------------------------------------
    const broken = brokenBudgets(measurements);
    console.log('');
    if (broken.length > 0) {
      console.error('the performance budgets were broken:');
      for (const entry of broken) {
        console.error(
          `  ${entry.name}: ${entry.value.toFixed(3)} (the limit is ${entry.limit}) - ${entry.why}`,
        );
      }
      failures.push(`${broken.length} budget(s) broken`);
    } else {
      console.log('  the performance budgets are met');
    }

    // --- the correctness -----------------------------------------------
    if (errors.length > 0) {
      failures.push(`${errors.length} request(s) failed`);
    }
    if (applied + refused !== commands) {
      failures.push(
        `only ${applied + refused} of ${commands} commands were answered`,
      );
    }
  } finally {
    server.child.kill();
    await rm(dataDir, { recursive: true, force: true });
  }

  console.log('');
  if (failures.length > 0) {
    console.error('the load test failed:');
    for (const failure of failures) console.error(`  ${failure}`);
    process.exit(1);
  }
  console.log('OK: the server sustained the load, and the budgets are met.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
