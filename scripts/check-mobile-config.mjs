#!/usr/bin/env node
/**
 * Validate the mobile shell's Capacitor configuration — config only, no build.
 *
 * `apps/mobile/` is a deliberately config-only scaffold: a plain
 * `capacitor.config.ts`, a dependency-free `package.json` and a README. A
 * read-only audit established that native Android/iOS builds are blocked on
 * this host (no JDK, Android SDK or Xcode), but the **configuration** is
 * independently verifiable. This script does exactly that, and nothing more.
 *
 * It proves, from the files on disk:
 *   1. the config is present, parseable and exports a real object with an
 *      application id, a name, a webDir and a non-downgraded server URL;
 *   2. the webDir resolves to the output the shared web client actually
 *      builds to (apps/client's `build.outDir`), so `cap sync` would copy the
 *      shipped client — this does NOT require a build to be present;
 *   3. the package declares the scripts the README documents and stays
 *      dependency-free (the Capacitor toolchain is installed only at native
 *      work time, as the README says);
 *   4. the README's factual claims match what is actually on disk — the
 *      three-file scaffold, no native project, the shared client files it
 *      points at, and the workspace prerequisites.
 *
 * A malformed, dangling or incoherent config fails loudly. This script never
 * runs `cap`, never generates a native project, and never claims a device or
 * emulator build.
 *
 * Usage:
 *   node scripts/check-mobile-config.mjs
 */
import { existsSync, readdirSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const MOBILE = path.join(ROOT, 'apps/mobile');
const CONFIG = path.join(MOBILE, 'capacitor.config.ts');
const PKG = path.join(MOBILE, 'package.json');
const README = path.join(MOBILE, 'README.md');
const VITE = path.join(ROOT, 'apps/client/vite.config.ts');
const ROOT_PKG = path.join(ROOT, 'package.json');

/** The honest, always-printed boundary of what this check proves. */
const NOT_RUN = 'native Android/iOS builds NOT RUN — no JDK/Android SDK/Xcode';

/** The three files the README says are the whole scaffold. */
const SCAFFOLD_FILES = ['README.md', 'capacitor.config.ts', 'package.json'];

/** Scripts the README documents and the package must therefore declare. */
const SCRIPTS = {
  sync: 'cap sync',
  'add:android': 'cap add android',
  'add:ios': 'cap add ios',
  'open:android': 'cap open android',
  'open:ios': 'cap open ios',
};

/** Shared client files the README names as the one renderer. */
const SHARED_CLIENT_FILES = [
  'apps/client/src/renderer.ts',
  'apps/client/src/touch.ts',
  'apps/client/src/ui/css.ts',
  'apps/client/index.html',
];

function rel(p) {
  return path.relative(ROOT, p).split(path.sep).join('/');
}

/** Pull a quoted string value out of a `key: '...'` pair. */
function stringField(text, key, problems, label) {
  const match = new RegExp(`\\b${key}\\s*:\\s*['"]([^'"]*)['"]`).exec(text);
  if (!match) {
    problems.push(`${label}: no string field "${key}"`);
    return null;
  }
  return match[1];
}

/** Validate capacitor.config.ts as text — no execution of its code. */
function validateConfig(text, problems, notes) {
  if (!/\bconst\s+config\s*=\s*\{/.test(text)) {
    problems.push('capacitor.config.ts: no `const config = { ... }` object');
  }
  if (!/\bexport\s+default\s+config\s*;?/.test(text)) {
    problems.push('capacitor.config.ts: no `export default config`');
  }

  const appId = stringField(text, 'appId', problems, 'capacitor.config.ts');
  const appName = stringField(text, 'appName', problems, 'capacitor.config.ts');
  const webDir = stringField(text, 'webDir', problems, 'capacitor.config.ts');

  if (appId !== null && !/^[a-z][a-z0-9]*(\.[a-z0-9]+)+$/.test(appId)) {
    problems.push(`capacitor.config.ts: appId "${appId}" is not a reverse-DNS application id`);
  }
  if (appName !== null && appName.trim() === '') {
    problems.push('capacitor.config.ts: appName is empty');
  }
  if (webDir !== null && webDir.trim() === '') {
    problems.push('capacitor.config.ts: webDir is empty');
  }

  let serverUrl = null;
  const serverBlock = /\bserver\s*:\s*\{([\s\S]*?)\}/.exec(text);
  if (!serverBlock) {
    problems.push('capacitor.config.ts: no `server: { ... }` block');
  } else {
    const block = serverBlock[1];
    const urlMatch = /\burl\s*:\s*([^,\n}]+)/.exec(block);
    if (!urlMatch) {
      problems.push('capacitor.config.ts: the server block has no `url`');
    } else {
      const token = urlMatch[1].trim();
      if (token === 'serverUrl') {
        const constant = /\bconst\s+serverUrl\s*=\s*['"]([^'"]*)['"]/.exec(text);
        if (!constant) {
          problems.push('capacitor.config.ts: `url: serverUrl` but no `const serverUrl` string');
        } else {
          serverUrl = constant[1];
        }
      } else {
        const quoted = /^(['"])([\s\S]*)\1$/.exec(token);
        if (quoted) serverUrl = quoted[2];
        else problems.push(`capacitor.config.ts: server.url is neither a string nor serverUrl: ${token}`);
      }
    }

    const cleartext = /\bcleartext\s*:\s*(true|false)\b/.exec(block);
    if (!cleartext) {
      problems.push('capacitor.config.ts: the server block has no boolean `cleartext`');
    } else if (cleartext[1] !== 'false') {
      problems.push('capacitor.config.ts: server.cleartext must stay false (never downgrade the authenticated server)');
    }
  }

  if (serverUrl !== null) {
    if (serverUrl.includes('REPLACE-WITH-YOUR-SERVER')) {
      notes.push('server.url is the documented placeholder: replace it with the real deployment before `cap sync`');
    } else if (!/^https:\/\//.test(serverUrl)) {
      problems.push(`capacitor.config.ts: server.url "${serverUrl}" is not https`);
    }
  }

  return { appId, appName, webDir, serverUrl };
}

/** webDir must resolve to the directory the shared client actually builds to. */
function validateWebDir(webDir, viteText, problems, notes) {
  if (webDir === null) return;
  if (path.isAbsolute(webDir)) {
    problems.push(`capacitor.config.ts: webDir "${webDir}" is absolute; it must be relative to apps/mobile`);
    return;
  }
  const outDir = /\boutDir\s*:\s*['"]([^'"]+)['"]/.exec(viteText);
  if (!outDir) {
    problems.push('apps/client/vite.config.ts: no `build.outDir` to compare webDir against');
    return;
  }
  const expected = path.resolve(ROOT, 'apps/client', outDir[1]);
  const actual = path.resolve(MOBILE, webDir);
  if (actual !== expected) {
    problems.push(
      `capacitor.config.ts: webDir "${webDir}" resolves to ${rel(actual)}, ` +
        `but the client builds to ${rel(expected)}`,
    );
    return;
  }
  notes.push(`webDir "${webDir}" resolves to the client build output (${rel(expected)})`);
  notes.push(
    existsSync(expected)
      ? `the built client is present at ${rel(expected)}`
      : `the built client is not in this tree; a config check does not require a build`,
  );
}

/** The package must declare the documented scripts and stay dependency-free. */
function validatePackage(pkg, problems, notes) {
  if (pkg.name !== '@swl/app-mobile') {
    problems.push(`apps/mobile/package.json: name is ${JSON.stringify(pkg.name)}, expected "@swl/app-mobile"`);
  }
  if (pkg.private !== true) problems.push('apps/mobile/package.json: `private` must be true');
  if (pkg.type !== 'module') problems.push('apps/mobile/package.json: `type` must be "module"');

  for (const [name, command] of Object.entries(SCRIPTS)) {
    if (pkg.scripts?.[name] !== command) {
      problems.push(
        `apps/mobile/package.json: script "${name}" is ${JSON.stringify(pkg.scripts?.[name])}, expected "${command}"`,
      );
    }
  }

  const installed = Object.keys(pkg.dependencies ?? {}).concat(Object.keys(pkg.devDependencies ?? {}));
  const capacitor = installed.filter((name) => name.startsWith('@capacitor/'));
  if (capacitor.length > 0) {
    problems.push(
      `apps/mobile/package.json declares Capacitor dependencies (${capacitor.join(', ')}), ` +
        'but the README says they are installed only at native-work time',
    );
  } else {
    notes.push('the package is dependency-free; the Capacitor toolchain is installed only at native-work time');
  }
}

/** The README's factual claims must match the files actually present. */
function validateReadme(text, ctx, problems) {
  if (!text.includes('@swl/app-mobile')) {
    problems.push('README: does not name the @swl/app-mobile package its commands target');
  }
  if (ctx.webDir && !text.includes(ctx.webDir)) {
    problems.push(`README: does not state the configured webDir "${ctx.webDir}"`);
  }
  if (!/\bcleartext\b/i.test(text) || !/server\.url/.test(text)) {
    problems.push('README: does not describe server.url and cleartext=false');
  }
  if (!/no\s+device\s+or\s+emulator/i.test(text)) {
    problems.push('README: does not state that no device or emulator was used');
  }
  if (!text.includes('@capacitor/cli') || !text.includes('@capacitor/core')) {
    problems.push('README: does not document installing @capacitor/cli and @capacitor/core at native-work time');
  }
  if (!text.includes('Node.js >= 22') || !text.includes('pnpm 12.6.0')) {
    problems.push('README: does not state the workspace Node.js >= 22 / pnpm 12.6.0 prerequisites');
  }

  const want = SCAFFOLD_FILES.slice().sort();
  const got = ctx.entries.slice().sort();
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    problems.push(`README claims the scaffold is ${want.join(', ')}; apps/mobile/ holds ${got.join(', ')}`);
  }
  for (const file of SHARED_CLIENT_FILES) {
    if (!ctx.sharedPresent.includes(file)) {
      problems.push(`README references ${file}, which is not present in the shared web client`);
    }
  }
}

/** The workspace versions the README cites must be the real ones. */
function validateRootPackage(text, problems) {
  let pkg;
  try {
    pkg = JSON.parse(text);
  } catch (error) {
    problems.push(`root package.json: invalid JSON (${error.message})`);
    return;
  }
  if (pkg.engines?.node !== '>=22') {
    problems.push(`root package.json: engines.node is ${JSON.stringify(pkg.engines?.node)}, README claims >=22`);
  }
  if (pkg.packageManager !== 'pnpm@12.6.0') {
    problems.push(`root package.json: packageManager is ${JSON.stringify(pkg.packageManager)}, README claims pnpm@12.6.0`);
  }
}

/** Pure validation over already-read inputs, so it can be self-tested. */
function validateAll(inputs) {
  const problems = [];
  const notes = [];

  let pkg;
  try {
    pkg = JSON.parse(inputs.pkgText);
  } catch (error) {
    problems.push(`apps/mobile/package.json: invalid JSON (${error.message})`);
    pkg = {};
  }

  const cfg = validateConfig(inputs.configText, problems, notes);
  validateWebDir(cfg.webDir, inputs.viteText, problems, notes);
  validatePackage(pkg, problems, notes);
  validateRootPackage(inputs.rootPkgText, problems);
  validateReadme(inputs.readmeText, {
    webDir: cfg.webDir,
    entries: inputs.entries,
    sharedPresent: inputs.sharedPresent,
  }, problems);

  return { problems, notes };
}

/** Prove the validator rejects malformed/dangling variants of the real inputs. */
function selfTest(inputs) {
  const cases = [
    ['clean inputs', inputs, false],
    ['appId removed', { ...inputs, configText: inputs.configText.replace(/appId\s*:\s*['"][^'"]*['"]\s*,?/, '') }, true],
    ['appId malformed', { ...inputs, configText: inputs.configText.replace(/com\.socialwarslegacy\.app/, 'not-a-dns-id') }, true],
    ['webDir dangling', { ...inputs, configText: inputs.configText.replace(/\.\.\/client\/dist/, '../client/nope') }, true],
    ['cleartext downgraded', { ...inputs, configText: inputs.configText.replace(/cleartext\s*:\s*false/, 'cleartext: true') }, true],
    ['server URL downgraded', { ...inputs, configText: inputs.configText.replace(/https:\/\/REPLACE-WITH-YOUR-SERVER\.example/, 'http://insecure.example') }, true],
    ['script missing', { ...inputs, pkgText: inputs.pkgText.replace(/"sync"\s*:\s*"cap sync"\s*,?/, '') }, true],
    ['package malformed', { ...inputs, pkgText: '{' }, true],
    ['no-device claim removed', { ...inputs, readmeText: inputs.readmeText.replace(/no\s+device\s+or\s+emulator/gi, '') }, true],
    ['native project appears', { ...inputs, entries: [...inputs.entries, 'android'] }, true],
  ];

  let ran = 0;
  for (const [name, input, shouldFail] of cases) {
    if (shouldFail && JSON.stringify(input) === JSON.stringify(inputs)) continue; // tamper did not apply
    const { problems } = validateAll(input);
    if (shouldFail && problems.length === 0) {
      throw new Error(`self-test: "${name}" was accepted but should have failed`);
    }
    if (!shouldFail && problems.length > 0) {
      throw new Error(`self-test: "${name}" failed unexpectedly: ${problems.join('; ')}`);
    }
    ran += 1;
  }
  console.log(`OK: validator self-test passed (${ran} cases, including malformed and dangling config).`);
}

async function main() {
  const problems = [];
  for (const [file, label] of [[CONFIG, 'capacitor.config.ts'], [PKG, 'package.json'], [README, 'README.md'], [VITE, 'apps/client/vite.config.ts'], [ROOT_PKG, 'root package.json']]) {
    if (!existsSync(file)) problems.push(`${label} is missing: ${rel(file)}`);
  }
  if (problems.length > 0) {
    console.error('FAIL: the mobile Capacitor configuration cannot be checked:');
    for (const problem of problems) console.error(`  ${problem}`);
    console.error(NOT_RUN);
    process.exit(1);
  }

  const [configText, pkgText, readmeText, viteText, rootPkgText] = await Promise.all([
    readFile(CONFIG, 'utf8'),
    readFile(PKG, 'utf8'),
    readFile(README, 'utf8'),
    readFile(VITE, 'utf8'),
    readFile(ROOT_PKG, 'utf8'),
  ]);

  const inputs = {
    configText,
    pkgText,
    readmeText,
    viteText,
    rootPkgText,
    entries: readdirSync(MOBILE),
    sharedPresent: SHARED_CLIENT_FILES.filter((file) => existsSync(path.join(ROOT, file))),
  };

  const { problems: found, notes } = validateAll(inputs);
  selfTest(inputs);

  if (found.length > 0) {
    console.error('FAIL: the mobile Capacitor configuration is not coherent with the shipped web client:');
    for (const problem of found) console.error(`  ${problem}`);
    console.error(NOT_RUN);
    process.exit(1);
  }

  console.log('OK: the mobile Capacitor config is coherent with the shipped web client (config validation only).');
  for (const note of notes) console.log(`  ${note}`);
  console.log(NOT_RUN);
}

main().catch((error) => {
  console.error(error);
  console.error(NOT_RUN);
  process.exit(1);
});
