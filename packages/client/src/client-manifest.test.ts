import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface ClientManifest {
  counts: { symbols: number; images: number };
  images: Record<string, unknown>;
  symbols: { swf: string; symbol: string; frames: { frame: number; image: string }[] }[];
}

async function clientManifest(): Promise<ClientManifest | null> {
  const file = path.join(repoRoot(), 'apps/client/public/frame-manifest.json');
  if (!existsSync(file)) return null;
  return JSON.parse(await readFile(file, 'utf8')) as ClientManifest;
}

describe("the client's manifest", () => {
  it('is much smaller than the asset pipeline manifest', async () => {
    const client = await clientManifest();
    if (!client) return; // The manifest has not been built yet.

    const pipeline = path.join(repoRoot(), 're/data/frame-manifest.json');
    if (!existsSync(pipeline)) return;

    const before = (await readFile(pipeline, 'utf8')).length;
    const after = (await readFile(
      path.join(repoRoot(), 'apps/client/public/frame-manifest.json'),
      'utf8',
    )).length;

    // The browser cannot be sent 118 MB of JSON, so the client's manifest
    // has to be a small fraction of the pipeline's.
    assert.ok(
      after < before / 10,
      `the client's manifest is ${(after / 1e6).toFixed(1)} MB and the pipeline's is ${(before / 1e6).toFixed(1)} MB`,
    );
  });

  it('holds only the symbols the content items refer to', async () => {
    const client = await clientManifest();
    if (!client) return;

    const content = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as { items: { img_name?: string }[] };

    const wanted = new Set(
      content.items.map((item) => item.img_name).filter((name): name is string => !!name),
    );
    assert.ok(wanted.size > 0);

    for (const symbol of client.symbols) {
      const name = symbol.swf.slice(symbol.swf.lastIndexOf('/') + 1).replace(/\.swf$/, '');
      assert.ok(wanted.has(name), `the manifest holds ${name}, which no item asks for`);
    }
  });

  it('holds one symbol per SWF, and the client draws that one', async () => {
    const client = await clientManifest();
    if (!client) return;

    // The client instantiates the sheet itself and picks the drawing by
    // its frame number, so the sheet - the SWF's root symbol - is the only
    // one it needs.
    const swfs = client.symbols.map((symbol) => symbol.swf);
    assert.equal(new Set(swfs).size, swfs.length, 'a SWF has more than one symbol');
  });

  it('has an image for every frame it names', async () => {
    const client = await clientManifest();
    if (!client) return;

    for (const symbol of client.symbols) {
      for (const frame of symbol.frames) {
        assert.ok(
          client.images[frame.image],
          `the frame ${frame.frame} of ${symbol.symbol} names an image that is not there`,
        );
      }
    }
  });

  it('counts what it holds', async () => {
    const client = await clientManifest();
    if (!client) return;

    assert.equal(client.counts.symbols, client.symbols.length);
    assert.equal(client.counts.images, Object.keys(client.images).length);
  });
});
