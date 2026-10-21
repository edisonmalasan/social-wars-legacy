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
import { claimDailyBonus } from '@swl/client';

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
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
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

  /**
   * The world, and the scene that draws it.
   *
   * The world is fetched again after every command, because the answer
   * carries the outcomes and not the world: the client asks, the server
   * decides, and the client draws what the server said.
   */
  let world = await fetchWorld();
  let scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
  renderer.draw(scene);

  async function fetchWorld(): Promise<ServerWorld> {
    return json<ServerWorld>('/api/world', {
      headers: { authorization: authorizationHeader(signedIn) },
    });
  }

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
  };
  (window as unknown as { __swl?: ClientHandle }).__swl = handle;

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
