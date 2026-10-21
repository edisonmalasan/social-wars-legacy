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
import { AtlasIndex, type FrameManifest, type WorldSnapshot } from '@swl/client';
import { cameraCentredOn, MAP_HEIGHT, MAP_WIDTH, type CameraState } from '@swl/client';
import { Interaction, pixelToTile } from '@swl/client';

import { buildScene, type SceneItem } from './scene.ts';
import { WorldRenderer, STAGE_HEIGHT, STAGE_WIDTH } from './renderer.ts';
import { applyFontScales, clientCss, type FontScaleFile } from './fonts.ts';
import {
  authorizationHeader,
  forgetSession,
  isExpired,
  readSession,
  rememberSession,
  signIn,
  sendCommands,
  type ClientSession,
} from '@swl/client';
import type { NativeCommand, NativeResponse } from '@swl/protocol';
import type { ContentBundle, ContentItem } from '@swl/content';
import { buy, claimDailyBonus } from '@swl/client';

import { mountUi } from './ui/mount.tsx';
import { uiCss } from './ui/css.ts';

const STAGE = document.getElementById('stage');
const GAME = document.getElementById('game');
const UI = document.getElementById('ui');

/** Where the content and the atlas live. */
const CONTENT_URL = '/content-bundle.json';
const MANIFEST_URL = '/frame-manifest.json';
const ATLAS_BASE = '/atlases';
/** Where the measured font scale lives. */
const FONT_SCALE_URL = '/font-scale.json';

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

/** The interface's stylesheet, the same way. */
function installUiStyles(): void {
  const style = document.createElement('style');
  style.textContent = uiCss();
  document.head.appendChild(style);
}

/** Fetch and parse a JSON file. */
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${url} answered ${response.status}`);
  }
  return (await response.json()) as T;
}

/**
 * The items on the map, by tile.
 *
 * A click has to find what is under it, and the tiles are the
 * **server's** — the client looks them up rather than guessing.
 */
function itemsByTile(
  world: WorldSnapshot,
): Map<string, { isoId: number; itemId: number }> {
  const out = new Map<string, { isoId: number; itemId: number }>();
  for (const [isoId, tuple] of Object.entries(world.maps[0]?.items ?? {})) {
    const tx = Number(tuple[1]);
    const ty = Number(tuple[2]);
    if (!Number.isFinite(tx) || !Number.isFinite(ty)) continue;
    out.set(`${tx},${ty}`, { isoId: Number(isoId), itemId: Number(tuple[0]) });
  }
  return out;
}

/**
 * The camera's first position.
 *
 * The camera opens on the player's own town: the **first** building on
 * the map, which is the Command Center the server gives every new
 * player. The map's middle is the fallback, so a world with nothing on
 * it still opens in the right place.
 */
function cameraFor(world: WorldSnapshot): CameraState {
  const first = Object.values(world.maps[0]?.items ?? {})[0];
  const tx = Number(first?.[1] ?? MAP_WIDTH / 2);
  const ty = Number(first?.[2] ?? MAP_HEIGHT / 2);
  return cameraCentredOn(tx, ty);
}

/** The items of a map, as the scene sees them. */function sceneItems(world: WorldSnapshot, content: ContentBundle): SceneItem[] {
  const map = world.maps[0];
  if (!map) return [];

  // The bundle holds its items as a **list**, so they are indexed by
  // id once. (They used to be looked up as if they were a map, which
  // meant that no item was ever found and nothing was ever drawn.)
  const definitions = new Map<number, ContentItem>();
  for (const item of content.items) definitions.set(item.id, item);

  const items: SceneItem[] = [];
  for (const [id, tuple] of Object.entries(map.items ?? {})) {
    const [itemId, tx, ty, , orientation] = tuple as [
      number, number, number, number, number,
    ];
    const definition = definitions.get(itemId);
    if (!definition) continue;

    items.push({
      id,
      itemId,
      tx,
      ty,
      width: definition.width ?? 1,
      walkable: definition.properties?.['walkable'] !== undefined,
      // The elevation is not in the content: in the original it comes
      // from the art's own anchor, and the trimmed frame already
      // carries it.
      elevation: 0,
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

/**
 * The client's debug handle.
 *
 * It is what the end-to-end test drives, and it is the client's own code
 * rather than a test's imitation of it.
 */
export interface ClientHandle {
  /** The session the client is playing with. */
  session: ClientSession;
  /** Send a batch of commands, the way the client does. */
  send: (commands: readonly NativeCommand[]) => Promise<{
    ok: boolean;
    response?: NativeResponse;
  }>;
  /**
   * Send a batch of commands, then draw what the server said.
   *
   * This is the whole loop: the client asks, the server decides, and the
   * client draws the answer. The answer carries the **outcomes** and not
   * the world, so the world is fetched again.
   *
   * The elapsed time is the **input-to-render latency**: from the command
   * leaving the client to the new world being on the screen.
   */
  run: (
    commands: readonly NativeCommand[],
  ) => Promise<{ ok: boolean; latencyMs: number; sprites: number }>;
  /**
   * The client's own request builders.
   *
   * The end-to-end test drives them, so the test exercises the request
   * the game really makes and not a test's imitation of it.
   */
  claimDailyBonus: typeof claimDailyBonus;
  /**
   * Buy a building and place it.
   *
   * The client asks; the server checks the level, the cost, the
   * population and the limits, and places it if the rules allow it.
   */
  buy: typeof buy;
  /** The frames per second the render loop is running at. */
  framesPerSecond: () => number;
  /**
   * The item the player selected on the map, or null.
   *
   * The selection is the client's own: it knows what the player
   * clicked, and the server decides what happens to it.
   */
  selectedItem: () => number | null;
  /**
   * How many sprites are on the stage.
   *
   * A sprite that is off the stage is in the scene but not on the
   * screen, so this is what says the player can see their town.
   */
  visibleSprites: () => number;
}

/** The browser's storage, or null when it refuses to be used. */
function safeStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * Ask the player to sign in.
 *
 * The client signs in with a **credential** and the server issues a
 * **session token**, so there is a name and a password and nothing else.
 * The form is the plainest one that works, because the interface is not
 * built yet.
 */
function askForSignIn(): Promise<ClientSession | null> {
  return new Promise((resolve) => {
    const form = document.createElement('form');
    form.id = 'signin';
    form.innerHTML = [
      '<label>Name <input name="playerId" autocomplete="username" required></label>',
      '<label>Password <input name="password" type="password" autocomplete="current-password" required></label>',
      '<button type="submit">Play</button>',
      '<p id="signin-error"></p>',
    ].join('');
    form.style.cssText = 'position:absolute;inset:0;display:grid;gap:8px;place-content:center;font:16px sans-serif;color:#eee;background:#10131a';
    STAGE?.appendChild(form);

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const playerId = String(data.get('playerId') ?? '');
      const password = String(data.get('password') ?? '');
      const error = form.querySelector('#signin-error');
      void signIn('/api/session', playerId, password).then((result) => {
        if (result.ok) {
          form.remove();
          resolve(result.session);
          return;
        }
        if (error) {
          error.textContent =
            result.reason === 'unknown-player'
              ? 'There is no player with that name.'
              : result.reason === 'invalid-credentials'
                ? 'That password is not right.'
                : 'The server could not be reached.';
        }
        resolve(null);
      });
    });
  });
}

async function main(): Promise<void> {
  if (!STAGE || !GAME) throw new Error('the page has no stage');

  installStyles();
  installUiStyles();
  status('starting');

  // The session. A stored one is used, and if there is none the player
  // signs in.
  const storage = safeStorage();
  let session = readSession(storage);
  if (session && isExpired(session, Math.floor(Date.now() / 1000))) {
    // The token is no good any more, and there is no point sending it.
    forgetSession(storage);
    session = null;
  }
  if (!session) {
    session = await askForSignIn();
    if (!session) {
      status('failed', 'not signed in');
      return;
    }
    rememberSession(storage, session);
  }
  // The session is known to be there now, and the closures below need it
  // to be a session rather than a session that might be null.
  const signedIn: ClientSession = session;

  const manifest = await json<FrameManifest>(MANIFEST_URL);
  const content = await json<ContentBundle>(CONTENT_URL);

  // The substitute fonts' scale. It is measured against the file that
  // ships, and it is **optional**: without it the text is a little
  // narrower than the original's and the game still reads.
  const scales = await json<FontScaleFile>(FONT_SCALE_URL).catch(() => null);
  if (scales) applyFontScales(scales, document.documentElement);

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

  /**
   * The world, and the scene that draws it.
   *
   * The world is fetched again after every command, because the answer
   * carries the outcomes and not the world: the client asks, the server
   * decides, and the client draws what the server said.
   */
  let world = await fetchWorld();
  // The camera opens on the player's own town, so the town is on the
  // screen rather than off in the corner of a hundred-tile map.
  renderer.setCamera(cameraFor(world));
  let scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
  renderer.draw(scene);

  async function fetchWorld(): Promise<WorldSnapshot> {
    return json<WorldSnapshot>('/api/world', {
      headers: { authorization: authorizationHeader(signedIn) },
    });
  }

  /**
   * The placement in progress.
   *
   * It is the client's own state — the client knows what the player is
   * about to place, and the server decides whether it happens.
   */
  const interaction = new Interaction();
  let placing: number | null = null;
  let selected: number | null = null;

  /** The interface is redrawn when the placement or the selection changes. */
  function drawInterface(): void {
    ui?.draw(world, placing, selected);
  }

  /**
   * The build menu's item.
   *
   * Picking one **begins** a placement; it does not build anything.
   */
  function onPick(itemId: number): void {
    interaction.beginPlacement(itemId, 'b');
    placing = itemId;
    selected = null;
    drawInterface();
  }

  /**
   * The selected building's production.
   *
   * The server decides what is collected and how much: the client's
   * request names the building and nothing else.
   */
  function onCollect(): void {
    const gesture = interaction.collectSelected();
    if (!gesture.ok) return;
    void run([gesture.command]);
  }

  /**
   * The interface.
   *
   * It is drawn from the **same** world the scene is: one answer, one
   * drawing. The interface asks the server for nothing of its own.
   */
  const ui = UI ? mountUi(UI, content, onPick, onCollect) : null;
  ui?.draw(world, placing, selected);

  // The map's click. The click is a **gesture**: the client turns it
  // into a command and the server decides the outcome.
  renderer.onClick = (x, y) => {
    const tile = pixelToTile(x, y, renderer.viewport);

    if (interaction.selection.kind === 'placement') {
      const gesture = interaction.placeTo(tile.tx, tile.ty);
      if (!gesture.ok) return;
      interaction.clear();
      placing = null;
      void run([gesture.command]);
      return;
    }

    // Otherwise the click selects what is under it.
    const found = itemsByTile(world).get(`${tile.tx},${tile.ty}`);
    if (!found) {
      interaction.clear();
      selected = null;
    } else {
      interaction.selectElement(found.isoId, found.itemId, 'building');
      selected = found.itemId;
    }
    drawInterface();
  };

  /**
   * Send a batch of commands and draw the answer.
   *
   * The elapsed time is the **input-to-render latency**.
   */
  async function run(commands: readonly NativeCommand[]) {
    const started = performance.now();
    const result = await sendCommands(signedIn.token, commands);
    world = await fetchWorld();
    scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
    renderer.draw(scene);
    // The interface is redrawn from the same answer, so the numbers in
    // the top bar and the buildings on the map never disagree.
    ui?.draw(world);
    return {
      ok: result.ok,
      latencyMs: performance.now() - started,
      sprites: scene.length,
    };
  }

  // The debug handle. The end-to-end test drives the client through it,
  // and a developer can look at the client's own state in the console.
  const handle: ClientHandle = {
    session,
    send: (commands) => sendCommands(session.token, commands),
    run,
    claimDailyBonus,
    buy,
    framesPerSecond: () => framesPerSecond,
    selectedItem: () => selected,
    visibleSprites: () =>
      scene.filter(
        (sprite) =>
          sprite.x >= 0 &&
          sprite.x < STAGE_WIDTH &&
          sprite.y >= 0 &&
          sprite.y < STAGE_HEIGHT,
      ).length,
  };
  (window as unknown as { __swl?: ClientHandle }).__swl = handle;

  // The render loop. The game is animated, so the client keeps drawing:
  // the loop is what advances the sprites and what keeps the screen
  // alive between the world's changes.
  let framesPerSecond = 0;
  renderer.run((rate) => {
    framesPerSecond = rate;
  });

  // The stage is scaled to fit the window, and it is scaled again when
  // the window changes.
  const fit = () => {
    const layout = renderer.fit(STAGE!);
    if (layout.tooSmall) {
      // Better to say so than to ship a game nobody can read.
      status('started', 'the window is too small for the text to be readable');
    }
    return layout;
  };
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
