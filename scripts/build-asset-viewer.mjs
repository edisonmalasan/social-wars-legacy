#!/usr/bin/env node
/**
 * Build the asset viewer.
 *
 * A single self-contained HTML page that shows **every content item** at
 * three zoom levels, so that missing art is visible rather than inferred.
 *
 * The page is generated from the repository's own records:
 *
 *   re/data/asset-manifest.json   what every item resolves to, and what
 *                                 does not
 *   re/data/frame-manifest.json   the atlas regions, when the atlases have
 *                                 been packed
 *
 * The atlases are a build artefact, so the viewer is regenerated after the
 * packer runs. Until then it shows the items with their art marked as
 * pending, which is itself worth seeing: it says exactly how much art is
 * missing before a single pixel is drawn.
 *
 * Usage:
 *   node scripts/build-asset-viewer.mjs
 */
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const ASSET_MANIFEST = path.join(ROOT, 're/data/asset-manifest.json');
const FRAME_MANIFEST = path.join(ROOT, 're/data/frame-manifest.json');
const BUNDLE = path.join(ROOT, 'packages/content/dist/content-bundle.json');
const OUT = path.join(ROOT, 're/data/asset-viewer.html');

/** The zoom levels the viewer draws at. */
const ZOOMS = [0.5, 1, 2];

/** Escape a string for the HTML. */
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * The atlas region for an item's sprite, when the atlases are packed.
 *
 * The frame manifest's symbols are keyed by `swf/symbol`, and the
 * manifest's images carry the region.
 */
function atlasLookup(frameManifest) {
  if (!frameManifest) return { regions: new Map(), packed: false };
  const regions = new Map();
  const images = frameManifest.images ?? {};
  for (const symbol of frameManifest.symbols ?? []) {
    const swf = symbol.swf ?? '';
    if (!swf.startsWith('sprites/')) continue;
    const sprite = swf.slice('sprites/'.length).replace(/\.swf$/, '');
    const frame = (symbol.frames ?? [])[0];
    if (!frame) continue;
    const image = images[frame.image];
    if (!image || !image.atlas) continue;
    regions.set(sprite, { atlas: image.atlas, trim: image.trim ?? null });
  }
  return { regions, packed: true };
}

async function main() {
  if (!existsSync(ASSET_MANIFEST)) {
    console.error(`no asset manifest at ${ASSET_MANIFEST}`);
    console.error('run: node scripts/build-asset-manifest.mjs');
    process.exit(1);
  }
  const assets = JSON.parse(await readFile(ASSET_MANIFEST, 'utf8'));
  const bundle = JSON.parse(await readFile(BUNDLE, 'utf8'));

  let frameManifest = null;
  try {
    frameManifest = JSON.parse(await readFile(FRAME_MANIFEST, 'utf8'));
  } catch {
    // The atlases have not been packed yet.
  }
  const { regions, packed } = atlasLookup(frameManifest);

  const items = bundle.items ?? [];
  const itemAssets = new Map((assets.itemAssets ?? []).map((entry) => [entry.id, entry]));

  // The missing lists hold `{ id, name, imgName }` records.
  const missing = new Set((assets.missing?.sprites ?? []).map((entry) => entry.id));
  const missingThumbs = new Set((assets.missing?.thumbnails ?? []).map((entry) => entry.id));

  // --- the rows -----------------------------------------------------------
  const rows = [];
  for (const item of items) {
    const sprite = item.img_name ?? '';
    const asset = itemAssets.get(item.id);
    const region = regions.get(sprite.replace(/\.swf$/, ''));
    const hasSprite = sprite !== '' && !missing.has(item.id);
    const hasThumb = !missingThumbs.has(item.id);

    const cells = ZOOMS.map((zoom) => {
      if (!hasSprite || !region) {
        return `<td class="zoom pending"><span>${escapeHtml(sprite || '—')}</span></td>`;
      }
      const trim = region.trim;
      const width = trim ? trim.width : 0;
      const height = trim ? trim.height : 0;
      return (
        `<td class="zoom">` +
        `<div class="frame" style="width:${Math.round(width * zoom)}px;height:${Math.round(height * zoom)}px">` +
        `<div class="art" style="width:${width}px;height:${height}px;` +
        `transform:scale(${zoom});` +
        `background-image:url('../.work/frames/atlases/${escapeHtml(region.atlas.file)}');` +
        `background-position:-${trim ? trim.x : 0}px -${trim ? trim.y : 0}px` +
        `"></div></div></td>`
      );
    }).join('');

    rows.push(
      `<tr class="${hasSprite ? '' : 'missing'}">` +
        `<td class="id">${item.id}</td>` +
        `<td class="name">${escapeHtml(item.name)}</td>` +
        `<td class="sprite">${escapeHtml(sprite)}</td>` +
        `<td class="thumb">${hasThumb && asset?.thumbs?.length ? escapeHtml(asset.thumbs[0]) : '—'}</td>` +
        cells +
        `</tr>`,
    );
  }

  const missingCount = missing.size;
  const summary =
    `${items.length} items, ${items.length - missingCount} with art, ` +
    `${missingCount} missing a sprite. ` +
    (packed
      ? `The atlases are packed: ${regions.size} sprites are on them.`
      : `The atlases are not packed yet, so the art columns are pending.`);

  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Social Wars Legacy — asset viewer</title>
<style>
  body { font: 13px/1.5 system-ui, sans-serif; margin: 0; padding: 16px; background: #14161a; color: #e8e8ea; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  p.summary { margin: 0 0 16px; color: #9aa0aa; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border-bottom: 1px solid #262a31; padding: 4px 8px; text-align: left; vertical-align: middle; }
  th { position: sticky; top: 0; background: #14161a; color: #9aa0aa; font-weight: 500; }
  tr.missing td { background: #2a1a1c; }
  td.id { width: 60px; color: #7f8792; }
  td.sprite, td.thumb { color: #9aa0aa; font-family: ui-monospace, monospace; font-size: 12px; }
  td.zoom { padding: 2px; }
  td.pending span { color: #5a606a; font-size: 11px; }
  .frame { overflow: hidden; }
  .art { image-rendering: pixelated; transform-origin: 0 0; }
</style>
</head>
<body>
<h1>Asset viewer</h1>
<p class="summary">${escapeHtml(summary)}</p>
<table>
<thead><tr>
  <th>id</th><th>name</th><th>sprite</th><th>thumbnail</th>
  ${ZOOMS.map((zoom) => `<th>${zoom}×</th>`).join('')}
</tr></thead>
<tbody>
${rows.join('\n')}
</tbody>
</table>
</body>
</html>
`;

  await writeFile(OUT, html, 'utf8');
  const hash = createHash('sha256').update(html).digest('hex').slice(0, 16);
  console.log(`wrote ${OUT}`);
  console.log(`  ${items.length} items, ${html.length} bytes, sha256 ${hash}`);
  console.log(`  ${summary}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
