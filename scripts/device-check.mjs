#!/usr/bin/env node
/**
 * Android / touch-device capability check.
 *
 * A real-device touch test needs a real device. This script **detects** one
 * and says exactly what it found; it never invents a device, and it never
 * claims a touch test ran when no input was injected. When nothing is plugged
 * in it exits successfully with the explicit reason `NO DEVICE`, so a CI job
 * can tell "nothing to test" apart from "the test failed".
 *
 * No new dependencies: only Node's standard library and the Android SDK's
 * own `adb`, which is discovered on this machine rather than assumed.
 *
 * Usage:
 *   node scripts/device-check.mjs
 *   node scripts/device-check.mjs --json
 *   node scripts/device-check.mjs --out capability.json
 *   node scripts/device-check.mjs --apk path/to/app-debug-unsigned.apk
 *
 * The optional `--apk` only *points at* an existing unsigned debug APK. This
 * script never builds one and never writes native output into the repository.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, statSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const EXE = process.platform === 'win32' ? 'adb.exe' : 'adb';

/** Run a command, returning its captured output instead of throwing. */
function run(command, args, timeoutMs = 15_000) {
  try {
    const result = spawnSync(command, args, {
      encoding: 'utf8',
      timeout: timeoutMs,
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    });
    return {
      ok: result.status === 0 && !result.error,
      status: result.status,
      stdout: String(result.stdout ?? ''),
      stderr: String(result.stderr ?? ''),
      error: result.error ? String(result.error.message ?? result.error) : null,
    };
  } catch (error) {
    return { ok: false, status: null, stdout: '', stderr: '', error: String(error) };
  }
}

const clean = (text) => String(text ?? '').replace(/\r/g, '').trim();

/** Every plausible place `adb` lives, de-duplicated, most explicit first. */
function adbCandidates() {
  const paths = [];
  if (process.env.ADB) paths.push(process.env.ADB);
  // A bare name is tried too: it resolves through PATH when there is one.
  paths.push(EXE);
  for (const root of [
    process.env.ANDROID_HOME,
    process.env.ANDROID_SDK_ROOT,
    process.platform === 'win32'
      ? path.join(os.homedir(), 'AppData', 'Local', 'Android', 'Sdk')
      : path.join(os.homedir(), 'Android', 'Sdk'),
    '/usr/lib/android-sdk',
    '/opt/android-sdk',
    '/Applications/Android Studio.app/sdk',
  ]) {
    if (root) paths.push(path.join(root, 'platform-tools', EXE));
  }
  return [...new Set(paths)];
}

/** Find a working `adb`, not merely a file with that name. */
function findAdb() {
  const tried = [];
  for (const candidate of adbCandidates()) {
    // A bare name is allowed to fail existsSync (PATH lookup); an absolute
    // path must exist before it is worth spawning.
    if (candidate !== EXE && !existsSync(candidate)) continue;
    const version = run(candidate, ['version']);
    tried.push({ path: candidate, ok: version.ok });
    if (version.ok && /Android Debug Bridge/i.test(version.stdout)) {
      return {
        found: true,
        path: candidate,
        version: clean(version.stdout.split('\n')[0]),
        tried,
      };
    }
  }
  return { found: false, path: null, version: null, tried };
}

/** Parse `adb devices -l`; only a device in the `device` state is usable. */
function parseDevices(text) {
  const devices = [];
  for (const raw of clean(text).split('\n').slice(1)) {
    const match = /^(\S+)\s+(device|unauthorized|offline)\b(.*)$/.exec(raw.trim());
    if (!match) continue;
    const [, serial, state, rest] = match;
    const tokens = new Map();
    for (const token of rest.trim().split(/\s+/)) {
      const split = token.indexOf(':');
      if (split > 0) tokens.set(token.slice(0, split), token.slice(split + 1));
    }
    devices.push({
      serial,
      state,
      model: tokens.get('model') ?? null,
      product: tokens.get('product') ?? null,
      transportId: tokens.get('transport_id') ?? null,
      _usable: state === 'device',
    });
  }
  return devices;
}

/** Ask one device a getprop; a failed query yields null, never a guess. */
function getprop(adb, serial, property) {
  const result = run(adb, ['-s', serial, 'shell', 'getprop', property]);
  if (!result.ok) return null;
  const value = clean(result.stdout);
  return value || null;
}

/** The touchscreen features Android reports for a device. */
function touchFeatures(adb, serial) {
  const result = run(adb, ['-s', serial, 'shell', 'pm', 'list', 'features']);
  if (!result.ok) return { reported: false, features: [], touchscreen: null };
  const features = clean(result.stdout)
    .split('\n')
    .map((line) => clean(line).replace(/^feature:/, ''))
    .filter(Boolean);
  return {
    reported: true,
    features: features.filter((feature) => /touchscreen|faketouch/i.test(feature)),
    touchscreen: features.includes('android.hardware.touchscreen'),
  };
}

/** Describe one connected device using only what adb actually answered. */
function describeDevice(adb, device) {
  const limitations = [];
  const api = getprop(adb, device.serial, 'ro.build.version.sdk');
  if (api !== null && !/^\d+$/.test(api)) limitations.push('the API level was not numeric');
  const touch = touchFeatures(adb, device.serial);
  if (!touch.reported) limitations.push('pm list features did not answer');

  return {
    serial: device.serial,
    state: device.state,
    model: getprop(adb, device.serial, 'ro.product.model') ?? device.model,
    apiLevel: api !== null && /^\d+$/.test(api) ? Number(api) : null,
    androidVersion: getprop(adb, device.serial, 'ro.build.version.release'),
    characteristics: getprop(adb, device.serial, 'ro.build.characteristics'),
    touch,
    limitations,
  };
}

/** Inspect an existing APK path; build nothing. */
function inspectApk(apkPath) {
  if (!apkPath) return null;
  const resolved = path.resolve(apkPath);
  if (!existsSync(resolved)) {
    return { path: resolved, exists: false, sizeBytes: null, note: 'path does not exist' };
  }
  return {
    path: resolved,
    exists: true,
    sizeBytes: statSync(resolved).size,
    note: 'existing file only; this script did not build or install it',
  };
}

function parseArgs(argv) {
  const args = { json: false, out: null, apk: null };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === '--json') args.json = true;
    else if (flag === '--out') args.out = argv[++i] ?? null;
    else if (flag === '--apk') args.apk = argv[++i] ?? null;
    else if (flag === '--help' || flag === '-h') args.help = true;
    else throw new Error(`unknown argument: ${flag}`);
  }
  if ((args.out === null && argv.includes('--out')) || (args.apk === null && argv.includes('--apk'))) {
    throw new Error('--out and --apk need a path');
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node scripts/device-check.mjs [--json] [--out <file>] [--apk <path>]');
    return;
  }

  const adb = findAdb();
  const raw = adb.found ? run(adb.path, ['devices', '-l']) : null;
  const parsed = raw ? parseDevices(raw.stdout) : [];
  const usable = parsed.filter((device) => device._usable);
  const devices = usable.map((device) => describeDevice(adb.path, device));

  const report = {
    schemaVersion: 1,
    tool: 'scripts/device-check.mjs',
    detected: devices.length > 0,
    reason: adb.found ? (devices.length ? 'DEVICE_PRESENT' : 'NO DEVICE') : 'ADB_NOT_FOUND',
    adb: { found: adb.found, path: adb.path, version: adb.version, tried: adb.tried },
    devices,
    nonUsableDevices: parsed.filter((device) => !device._usable),
    touchTests: {
      performed: 0,
      reason: 'capability detection only; no touch input was injected by this script',
    },
    apk: inspectApk(args.apk),
    warnings: [],
  };
  if (!adb.found) report.warnings.push('adb was not found; no device could be queried');
  if (devices.length === 0 && adb.found) {
    report.warnings.push('adb answered but no device is in the "device" state');
  }
  for (const device of devices) {
    if (device.touchscreen === null) {
      report.warnings.push(`${device.serial}: touchscreen capability was not reported`);
    }
  }

  const json = JSON.stringify(report, null, 2);
  if (args.out) {
    writeFileSync(path.resolve(args.out), `${json}\n`, 'utf8');
  }
  if (args.json) {
    console.log(json);
  } else {
    console.log(`adb: ${adb.found ? `${adb.path} (${adb.version})` : 'NOT FOUND'}`);
    console.log(`detected: ${report.detected ? 'yes' : 'no'}`);
    console.log(`reason: ${report.reason}`);
    if (devices.length === 0) {
      console.log('NO DEVICE: no connected Android device or emulator was detected; no touch test was run.');
    } else {
      for (const device of devices) {
        console.log(
          `  ${device.serial}: model=${device.model ?? 'unknown'} ` +
            `api=${device.apiLevel ?? 'unknown'} ` +
            `touchscreen=${device.touchscreen === null ? 'unknown' : device.touchscreen}`,
        );
      }
    }
    console.log(`touch tests performed: ${report.touchTests.performed} (${report.touchTests.reason})`);
    if (report.apk) {
      console.log(
        `apk: ${report.apk.exists ? `${report.apk.path} (${report.apk.sizeBytes} bytes)` : 'NOT FOUND'}` +
          ' — not built or installed by this script',
      );
    }
    if (args.out) console.log(`report written to ${path.resolve(args.out)}`);
    console.log('REPORT (JSON):');
    console.log(json);
  }
  // A missing device is a successful check with a negative result, not an
  // error: there was nothing to test, and this never pretends otherwise.
}

try {
  main();
} catch (error) {
  console.error(`device-check: ${String(error)}`);
  process.exitCode = 1;
}
