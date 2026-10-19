#!/usr/bin/env node
/**
 * Roadmap task B7 — the social layer contracts.
 *
 * The upstream server answers `{}` for every `alliance/?method=...` variant and has the
 * `bets/*` routes commented out, so the real contract has to be recovered from the
 * client. It is fully recoverable: `core/Config.as` names every endpoint, and each call
 * site shows the request parameters it sends and the response fields it reads.
 *
 * Outputs:
 *   re/data/service-contracts.json
 */
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const AS = path.join(ROOT, '.work/as/basesec/scripts');
const OUT = path.join(ROOT, 're/data');

const read = (p) => readFile(p, 'utf8');

async function walk(dir, rel = '') {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    if (e.isDirectory()) out.push(...(await walk(path.join(dir, e.name), path.join(rel, e.name))));
    else if (e.isFile() && e.name.endsWith('.as')) out.push(path.join(rel, e.name));
  }
  return out;
}

async function main() {
  const configSrc = await read(path.join(AS, 'core/Config.as'));

  // 1. every SERVICE_* constant
  const services = [];
  for (const m of configSrc.matchAll(
    /public static const (SERVICE_\w+):String = "([^"]+)"/g,
  )) {
    services.push({ constant: m[1], path: m[2] });
  }

  // 2. error codes the client understands
  const errSrc = await read(path.join(AS, 'data/AllianceServiceError.as')).catch(() => '');
  const errorCodes = [...errSrc.matchAll(/public static const (ERR_\w+):uint = (\d+)/g)].map((m) => ({
    constant: m[1],
    code: Number(m[2]),
  }));

  // 3. call sites: request parameters and response fields
  const files = await walk(AS);
  const byConstant = new Map(services.map((s) => [s.constant, { ...s, callSites: [] }]));

  for (const rel of files) {
    const src = await read(path.join(AS, ...rel.split(/[\\/]/)));
    for (const m of src.matchAll(
      /callService\(\s*Config\.(SERVICE_\w+)\s*,\s*([\s\S]{0,1200}?)\)\s*[,;]/g,
    )) {
      const constant = m[1];
      const entry = byConstant.get(constant);
      if (!entry) continue;
      const body = m[2];
      // Request parameter keys: object-literal keys plus `params.<key> =` assignments.
      const literalKeys = [...body.matchAll(/[{,]\s*"(\w+)"\s*:/g)].map((x) => x[1]);
      const assignKeys = [...body.matchAll(/\bparams\.(\w+)\s*=/g)].map((x) => x[1]);
      // Response fields the success callback reads.
      const responseFields = [...new Set(
        [...body.matchAll(/\bparam\d+\.(\w+)/g)].map((x) => x[1]),
      )];
      entry.callSites.push({
        file: rel.replace(/\\/g, '/'),
        requestParams: [...new Set([...literalKeys, ...assignKeys])],
        responseFields: responseFields.slice(0, 25),
      });
    }
  }

  const out = {
    note:
      'Service endpoints and their request/response contract, recovered from ' +
      'core/Config.as and every ServiceManager.callService() call site in the ' +
      'decompiled client.',
    counts: {
      endpoints: services.length,
      endpointsWithCallSites: [...byConstant.values()].filter((e) => e.callSites.length).length,
      totalCallSites: [...byConstant.values()].reduce((n, e) => n + e.callSites.length, 0),
      allianceEndpoints: services.filter((s) => s.path.startsWith('alliance/')).length,
      betsEndpoints: services.filter((s) => s.path.startsWith('bets/')).length,
      errorCodes: errorCodes.length,
    },
    allianceErrorCodes: errorCodes,
    services: [...byConstant.values()],
  };

  await mkdir(OUT, { recursive: true });
  await writeFile(
    path.join(OUT, 'service-contracts.json'),
    JSON.stringify(out, null, 1) + '\n',
    'utf8',
  );

  console.log(`endpoints              : ${out.counts.endpoints}`);
  console.log(`  alliance variants    : ${out.counts.allianceEndpoints}`);
  console.log(`  bets endpoints       : ${out.counts.betsEndpoints}`);
  console.log(`endpoints with call sites: ${out.counts.endpointsWithCallSites}`);
  console.log(`total call sites       : ${out.counts.totalCallSites}`);
  console.log(`alliance error codes   : ${out.counts.errorCodes}`);
  console.log('\nwrote re/data/service-contracts.json');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
