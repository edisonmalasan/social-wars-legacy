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
import { clientCss } from './fonts.ts';

const STAGE = document.getElementById('stage');
const GAME = document.getElementById('game');

/** Where the content and the atlas live. */
const CONTENT_URL = '/content-bundle.json';
const MANIFEST_URL = '/frame-manifest.json';
const ATLAS_BASE = '/atlases';

/**
 * The stylesheet.
 *
 * It is **injected** rather than linked, so the fonts' base URL is the
 * client's own configuration and the sheet is built from the same
 * module the tests check.
 */
function installStyles(): void {
  const style = document.createElement('style');
  style.textContent = clientCss('/fonts');
  document.head.appendChild(style);
}

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
      itemId,
      tx,
      ty,
      width: definition.width ?? 1,
      walkable: definition.properties?.['walkable'] !== undefined,
      elevation: definition.elevation ?? 0,
      orientation: orientation ?? 0,
      animation: 0,
    });
  }
  return items;
}

/**
 * The client's status.
 *
 * It is written into the page, so that a **headless** run can check it:
 * the smoke test reads the DOM and sees whether the client started.
 */
function status(state: string, detail = ''): void {
  const element = document.getElementById('status');
  if (!element) return;
  element.textContent = detail ? `${state}: ${detail}` : state;
  element.setAttribute('data-state', state);
}

async function main(): Promise<void> {
  if (!STAGE || !GAME) throw new Error('the page has no stage');

  installStyles();
  status('starting');

  const manifest = await json<FrameManifest>(MANIFEST_URL);
  const content = await json<{ items: Record<string, never> }>(CONTENT_URL);

  const renderer = await WorldRenderer.start({
    element: GAME,
    manifest,
    atlasBase: ATLAS_BASE,
  });
  const atlas = new AtlasIndex(manifest);

  // The atlas pages are fetched as the scene needs them, so the scene is
  // drawn again when a page arrives.
  renderer.onPageLoaded = () => {
    status('started', `${renderer.loadedPages} atlas page(s)`);
  };

  const world = await json<ServerWorld>('/api/world');
  const scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
  renderer.draw(scene);

  // The stage is scaled to fit the window, and it is scaled again when
  // the window changes.
  const fit = () => renderer.fit(STAGE!);
  fit();
  window.addEventListener('resize', fit);

  if (renderer.missingAtlasPages.length > 0) {
    status(
      'started',
      `${renderer.missingAtlasPages.length} atlas page(s) could not be loaded`,
    );
  } else {
    status('started', `${scene.length} sprites`);
  }
}

main().catch((error) => {
  console.error('[client] could not start:', error);
  status('failed', String(error));
  const element = document.getElementById('game');
  if (element) {
    element.textContent = `The client could not start: ${String(error)}`;
  }
});
