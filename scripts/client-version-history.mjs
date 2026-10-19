#!/usr/bin/env node
/**
 * Roadmap task B1 — the client's own version history.
 *
 * `upstream/socialwarriors/assets/flash/` holds 58 builds of the game client,
 * `Basesec_1.4.5.swf` through `Basesec_1.5.4.swf`. Each embeds its own
 * `Config.as`, so the client history can be recovered without decompiling 58 SWFs:
 * the interesting values (the server key, endpoint names, flashvar names, ...)
 * are string constants in the ABC constant pool, and therefore present as plain
 * ASCII in the decompressed SWF.
 *
 * This script:
 *   1. inflates each build (CWS -> FWS),
 *   2. extracts the printable string set,
 *   3. records which protocol-relevant strings appear in each build,
 *   4. reports, per string, the first and last build it appears in.
 *
 * Output: re/data/client-version-history.json
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { inflateSync } from 'node:zlib';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const FLASH_DIR = path.join(ROOT, 'upstream/socialwarriors/assets/flash');
const OUT_DIR = path.join(ROOT, 're/data');
const OUT_FILE = path.join(OUT_DIR, 'client-version-history.json');

/** The protocol-relevant strings worth tracking across the client history. */
const TRACKED = [
  // identity
  '4vVSD8dftv6hdfb1Hnk9',
  'SexWars',
  // dynamic API root
  'menvswomen', 'srvsexwars',
  // endpoints
  'command.php', 'get_game_config.php', 'get_player_info.php',
  'track_game_status.php', 'sync_error_track.php', 'crossdomain.xml',
  'get_bets_list.php', 'set_bet.php', 'get_bet_detail.php',
  'get_user_world.php', 'get_continent_ranking.php', 'get_public_player_info.php',
  'set_sex_player.php', 'report_error_init.php', 'get_continent.php',
  'register_found_item.php', 'clean_assaults.php',
  // flashvars
  'staticUrl', 'dynamicUrl', 'skiphash12341', 'fb_sig_user', 'user_key',
  'accessToken', 'lastLoggedIn', 'friendsInfo', 'publishActions', 'first_number',
  'forceSyncError', 'forceAttackReload', 'forceQuestReload', 'sp_ref_cat',
  'sp_ref_uid', 'serverTime', 'dailyBonus', 'spdebug',
  // protocol behaviour
  'skiphash', 'ownueg', 'weird.txt', 'SEC',
  // command vocabulary
  'complete_tutorial', 'flash_debug', 'end_attack', 'end_quest', 'rt_open_graph_unit',
  'push_queue_unit', 'pop_queue_unit', 'add_click', 'activate_item_click',
  'set_quest_var', 'set_help_map', 'batch_remove', 'darts_reset',
];

/** The two server keys the client shipped with, in rotation order. */
const SERVER_KEYS = [
  { key: '3m0d3pwiupoetn7ysa02', note: 'the original production key' },
  { key: '4vVSD8dftv6hdfb1Hnk9', note: 'the rotated key the shipped 1.5.4 build signs with' },
];

/** Printable runs of 6+ characters. */
function extractStrings(buf) {
  const out = [];
  let start = -1;
  for (let i = 0; i < buf.length; i++) {
    const c = buf[i];
    if (c >= 0x20 && c < 0x7f) {
      if (start < 0) start = i;
    } else if (start >= 0) {
      if (i - start >= 6) out.push(buf.toString('latin1', start, i));
      start = -1;
    }
  }
  if (start >= 0 && buf.length - start >= 6) out.push(buf.toString('latin1', start));
  return out;
}

function inflateIfNeeded(buf) {
  if (buf[0] === 0x43 /* C */ && buf[1] === 0x57 /* W */ && buf[2] === 0x53 /* S */) {
    return Buffer.concat([Buffer.from(buf.subarray(0, 8)), inflateSync(buf.subarray(8))]);
  }
  return buf;
}

function versionOf(name) {
  const m = /^Basesec_(\d+)\.(\d+)\.(\d+)\.swf$/.exec(name);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

function cmpVersion(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

async function main() {
  const { readdir } = await import('node:fs/promises');
  const names = (await readdir(FLASH_DIR)).filter((n) => /^Basesec_.*\.swf$/.test(n));
  names.sort((a, b) => {
    const va = versionOf(a), vb = versionOf(b);
    return va && vb ? cmpVersion(va, vb) : a.localeCompare(b);
  });

  const builds = [];
  for (const name of names) {
    const raw = inflateIfNeeded(await readFile(path.join(FLASH_DIR, name)));
    const strings = extractStrings(raw);
    const set = new Set(strings);
    const present = {};
    for (const t of TRACKED) if (set.has(t)) present[t] = true;
    const serverKey =
      SERVER_KEYS.find((k) => set.has(k.key))?.key ?? null;
    builds.push({
      file: name,
      version: versionOf(name)?.join('.') ?? null,
      bytes: raw.length,
      stringCount: strings.length,
      serverKey,
      present,
    });
    process.stdout.write(`  ${name}  strings=${strings.length}\n`);
  }

  // For each tracked string: which builds contain it?
  const presence = {};
  for (const t of TRACKED) {
    const inBuilds = builds.filter((b) => b.present[t]).map((b) => b.version);
    presence[t] = {
      count: inBuilds.length,
      first: inBuilds[0] ?? null,
      last: inBuilds[inBuilds.length - 1] ?? null,
      presentIn: inBuilds,
    };
  }

  const summary = {
    note:
      'Recovered by inflating each client build and reading its ABC string pool. ' +
      'Not a full decompilation; presence/absence of a literal only. The server key ' +
      'rotation was additionally confirmed by decompiling core/Config.as from the ' +
      'boundary builds 1.4.27 and 1.4.28.',
    upstreamCommit: 'c3fceeb1f8e93734a293b9bc25ae6025656f6822',
    builds: builds.length,
    versionRange: [builds[0]?.version, builds[builds.length - 1]?.version],
    serverKeyRotation: {
      '3m0d3pwiupoetn7ysa02': {
        builds: builds.filter((b) => b.serverKey === '3m0d3pwiupoetn7ysa02').map((b) => b.version),
        note: 'the original production key',
      },
      '4vVSD8dftv6hdfb1Hnk9': {
        builds: builds.filter((b) => b.serverKey === '4vVSD8dftv6hdfb1Hnk9').map((b) => b.version),
        note: 'the rotated key the shipped 1.5.4 build signs with',
      },
      rotatedAt: '1.4.28',
    },
    presence,
    perBuild: builds,
  };

  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(OUT_FILE, JSON.stringify(summary, null, 1) + '\n', 'utf8');
  console.log(`\nwrote ${OUT_FILE}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
