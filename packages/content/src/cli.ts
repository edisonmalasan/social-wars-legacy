/**
 * Content build entry point.
 *
 *   node packages/content/src/build.ts            # build and write the bundle
 *   node packages/content/src/build.ts --check     # validate only, for CI
 *   node packages/content/src/build.ts --out <f>  # write somewhere else
 */
import path from 'node:path';

import { buildContent, writeBundle, REPO_ROOT } from './build.ts';

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const check = args.includes('--check');
  const outIndex = args.indexOf('--out');
  const outFile =
    outIndex >= 0 && args[outIndex + 1]
      ? path.resolve(args[outIndex + 1]!)
      : path.join(REPO_ROOT, 'packages/content/dist/content-bundle.json');

  const { bundle, problems, warnings } = await buildContent();

  console.log(`upstream commit   : ${bundle.upstreamCommit}`);
  console.log(`patches applied   : ${bundle.patchesApplied.join(', ')}`);
  console.log(`items             : ${bundle.items.length}`);
  console.log(`levels            : ${bundle.levels.length}`);
  console.log(`config goals      : ${bundle.goals.length}`);
  console.log(`globals           : ${Object.keys(bundle.globals).length}`);
  console.log(`property keys     : ${Object.keys(bundle.propertyKeys).length}`);
  console.log(`subcat_functionals: ${Object.keys(bundle.subcatFunctionals).length}`);
  console.log(`client-only items : ${bundle.clientOnlyItemIds.length}`);
  console.log(`items with no asset: ${bundle.assetlessItemIds.length}`);
  console.log(`build id          : ${bundle.buildId}`);

  if (warnings.length > 0) {
    console.log(`\n${warnings.length} warning(s):`);
    for (const w of warnings.slice(0, 20)) console.log(`  - ${w}`);
    if (warnings.length > 20) console.log(`  ... and ${warnings.length - 20} more`);
  }

  if (problems.length > 0) {
    console.error(`\n${problems.length} ERROR(s):`);
    for (const p of problems.slice(0, 40)) console.error(`  - ${p}`);
    if (problems.length > 40) console.error(`  ... and ${problems.length - 40} more`);
    process.exit(1);
  }

  if (!check) {
    const file = await writeBundle(bundle, outFile);
    console.log(`\nwrote ${file}`);
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
