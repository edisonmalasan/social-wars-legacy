/**
 * The web client's entry point.
 *
 * It loads the content bundle and the frame manifest, asks the server
 * for the player's world, and draws it.
 *
 * The **server owns the world**: the client's tile positions, its
 * resources and its buildings all come from the server's answer, and
 * the client draws them. It never decides an outcome.
 */
import { AtlasIndex, type FrameManifest } from '@swl/client';

import { buildScene, type SceneItem } from './scene.ts';
import { WorldRenderer } from './renderer.ts';

const STAGE = document.getElementById('stage');
const GAME = document.getElementById('game');

/** Where the content and the atlas live. */
const CONTENT_URL = '/content-bundle.json';
const MANIFEST_URL = '/frame-manifest.json';
const ATLAS_BASE = '/atlases';

/** The player's world, as the server sends it. */
interface ServerWorld {
  maps: { id: number; items: Record<string, number[]> }[];
  privateState: Record<string, unknown>;
}

/** Fetch and parse a JSON file. */
async function json<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} answered ${response.status}`);
  }
  return (await response.json()) as T;
}

/** The items of a map, as the scene sees them. */
function sceneItems(
  world: ServerWorld,
  content: { items: Record<string, { width?: number; properties?: Record<string, unknown>; elevation?: number; img_name?: string }> },
): SceneItem[] {
  const map = world.maps[0];
  if (!map) return [];

  const items: SceneItem[] = [];
  for (const [id, tuple] of Object.entries(map.items ?? {})) {
    const [itemId, tx, ty, , orientation] = tuple as [
      number, number, number, number, number,
    ];
    const definition = content.items[String(itemId)];
    if (!definition) continue;

    items.push({
      id,
      tx,
      ty,
      width: definition.width ?? 1,
      walkable: definition.properties?.['walkable'] !== undefined,
      elevation: definition.elevation ?? 0,
      // The client's art is named `img_name`, and the symbol within the
      // SWF is the item's own id.
      swf: definition.img_name ?? '',
      symbol: String(itemId),
      orientation: orientation ?? 0,
      animation: 0,
    });
  }
  return items;
}

async function main(): Promise<void> {
  if (!STAGE || !GAME) throw new Error('the page has no stage');

  const manifest = await json<FrameManifest>(MANIFEST_URL);
  const content = await json<{ items: Record<string, never> }>(CONTENT_URL);

  const renderer = await WorldRenderer.start({
    element: GAME,
    manifest,
    atlasBase: ATLAS_BASE,
  });
  const atlas = new AtlasIndex(manifest);

  const world = await json<ServerWorld>('/api/world');
  const scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
  renderer.draw(scene);

  // The stage is scaled to fit the window, and it is scaled again when
  // the window changes.
  const fit = () => renderer.fit(STAGE!);
  fit();
  window.addEventListener('resize', fit);
}

main().catch((error) => {
  console.error('[client] could not start:', error);
  const element = document.getElementById('game');
  if (element) {
    element.textContent = `The client could not start: ${String(error)}`;
  }
});
