#!/usr/bin/env node
/**
 * A deterministic clock for the end-to-end server process.
 *
 * This is a **test fixture**, loaded only by the e2e harness's server child
 * through `NODE_OPTIONS=--import=...`. It is never used by the shipped
 * server. The harness writes an offset (in seconds) to the file named by
 * `SWL_E2E_CLOCK_FILE`; this module adds that offset to the real clock, so
 * the server's own `Date.now()` decides when a production cycle is due
 * without the test sleeping through a five-minute wait.
 *
 * Nothing here grants a resource, moves a counter or changes a save. The
 * offset is only the server's clock; every rule still runs in the real
 * applier over the real database.
 */
import { readFileSync, statSync } from 'node:fs';
import process from 'node:process';

const file = process.env['SWL_E2E_CLOCK_FILE'];
if (!file) throw new Error('the e2e clock fixture needs SWL_E2E_CLOCK_FILE');

const realNow = Date.now.bind(Date);
let offsetSeconds = 0;
let lastMtime = -1;

// The offset is re-read only when the harness changes the file. The stat is
// cheap; the server calls this clock on most requests.
Date.now = () => {
  try {
    const mtime = statSync(file).mtimeMs;
    if (mtime !== lastMtime) {
      lastMtime = mtime;
      const value = Number(readFileSync(file, 'utf8').trim());
      if (Number.isFinite(value)) offsetSeconds = value;
    }
  } catch {
    // Not written yet: the clock is the real one.
  }
  return realNow() + offsetSeconds * 1000;
};
