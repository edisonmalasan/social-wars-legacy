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
import { fetchNeighbours, type Neighbour } from '@swl/client';
import {
  Tutorial,
  type TutorialStep,
} from '@swl/client';
import { tutorialState } from '@swl/rules';

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
import type { CommandOutcome, NativeCommand, NativeResponse } from '@swl/protocol';
import type { ContentBundle, ContentItem } from '@swl/content';
import {
  buy,
  claimDailyBonus,
  completeTutorial,
  finishBuilding,
  finishView,
  takeTrainedUnit,
  type ItemType,
} from '@swl/client';
import {
  activeQuestFromWorld,
  activeQuestState,
  activeQuestView,
  briefingDialog,
  briefingView,
  combatDialog,
  endQuest,
  questActionOnServer,
  questDifficulty,
  questResultView,
  reportQuestKill,
  resultDialog,
  startQuestOnServer,
  type ActiveQuestStateView,
  type QuestActionChoice,
  type QuestActionRequest,
  type QuestChoice,
  type QuestLedgerSummary,
  type QuestResult,
  type QuestStartBody,
} from '@swl/client';

import { mountUi } from './ui/mount.tsx';
import { uiCss } from './ui/css.ts';
import type { TutorialOverlayProps } from './ui/tutorial.tsx';
import type { QuestPanelView } from './ui/quests.tsx';
import { questViewOptions } from './ui/state.ts';
import {
  CLOSED_DIALOG,
  closeDialog,
  feedbackFrom,
  openDialog,
  type DialogId,
  type DialogKind,
  type DialogState,
  type FeedbackMessage,
} from '@swl/client';

const STAGE = document.getElementById('stage');
const GAME = document.getElementById('game');
const UI = document.getElementById('ui');

/** Where the content and the atlas live. */
const CONTENT_URL = '/content-bundle.json';
const MANIFEST_URL = '/frame-manifest.json';
const ATLAS_BASE = '/atlases';
/** Where the measured font scale lives. */
const FONT_SCALE_URL = '/font-scale.json';
/** Where the tutorial's steps live. */
const TUTORIAL_URL = '/tutorial-steps.json';

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
  ) => Promise<{
    ok: boolean;
    latencyMs: number;
    sprites: number;
    /** The server's own outcome of the first command, when it answered. */
    outcome?: CommandOutcome | null;
  }>;
  /**
   * Open the shared dialog. The G5.1 panels use this one primitive; a host
   * supplies the panel's id, kind and heading, never its game outcome.
   */
  showDialog?: (id: DialogId, kind: DialogKind, title: string) => void;
  /** Close the shared dialog. */
  dismissDialog?: () => void;
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
  /** The tutorial step the client is showing, or null when it is not. */
  tutorialStep: () => number | null;
  /**
   * Walk the tutorial one step and record the reached step with the
   * server. The answer says whether the server kept it and what step is
   * showing next.
   */
  advanceTutorial: () => Promise<{ ok: boolean; step: number | null }>;
  /** Skip the tutorial, recording it as finished. */
  skipTutorial: () => Promise<{ ok: boolean }>;
  /**
   * Start a quest in the server's own state. The difficulty is the one the
   * player chose to play; the server decides whether to accept it and owns
   * the resulting active quest.
   */
  startQuest: (
    questId: string,
    difficulty?: number,
  ) => Promise<QuestResult<QuestStartBody>>;
  /**
   * Apply one authoritative quest action (a strike, an arrival, an eligible
   * enemy or an evacuation) on the server, which owns the ledger it moves.
   */
  questAction: (
    questId: string,
    action: QuestActionRequest,
  ) => Promise<QuestResult<QuestLedgerSummary>>;
  /** The strictly two-argument `killed` write the client reports. */
  reportQuestKill: typeof reportQuestKill;
  /** The `end_quest` request, whose reward the server computes. */
  endQuest: typeof endQuest;
  /** The active quest read from the server's answer, never fabricated. */
  activeQuest: () => ActiveQuestStateView | null;
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
  const tutorialSteps = await json<{ steps: TutorialStep[] }>(TUTORIAL_URL);

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

  /**
   * The tutorial.
   *
   * The steps are the client's own, and the **progression is the
   * server's**: the furthest step the server recorded is where the
   * tutorial resumes, and each step the player reaches is sent back. A
   * finished tutorial is not shown again.
   */
  const tutorial = new Tutorial(tutorialSteps.steps);
  const storedTutorial = tutorialState(world.privateState);
  if (storedTutorial.step > 0 && !storedTutorial.complete) {
    tutorial.jumpTo(storedTutorial.step);
  }
  let tutorialRunning = !storedTutorial.complete && tutorial.current !== null;

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
  /** The map id of the selected element, for its server attribute bag. */
  let selectedIso: number | null = null;
  let neighbours: Neighbour[] = [];
  /**
   * The one open dialog and the feedback channel. Neither is a reading of
   * the world: they are the client's own UI state, kept here so every
   * redraw shows the same panel and the same last answer's messages.
   */
  let dialogState: DialogState = CLOSED_DIALOG;
  let feedback: readonly FeedbackMessage[] = [];
  /**
   * The quest panel in the one dialog, and the difficulty the player chose.
   * Neither is a game outcome: the first is a reading of the server's active
   * quest or answer, the second is only sent to the server with the start and
   * finish requests.
   */
  let questPanel: QuestPanelView | null = null;
  let chosenDifficulty: 1 | 2 | 3 = 1;

  /** The interface is redrawn when the placement or the selection changes. */
  function drawInterface(): void {
    ui?.draw(world, placing, selected, neighbours, tutorialProps(), {
      dialog: dialogState,
      feedback,
      questPanel,
      onDialogDismiss: () => {
        dialogState = closeDialog(dialogState);
        questPanel = null;
        drawInterface();
      },
      onQuestPick: openQuestSlot,
      onQuestStart: (questId, difficulty) => {
        void beginQuest(questId, difficulty);
      },
      onQuestAction: (questId, action) => {
        void applyQuestGesture(questId, action);
      },
      selectedIso,
      now: Math.floor(Date.now() / 1000),
      onUpgrade,
      onFinish,
      onTrain,
      onTake,
    });
  }

  /** Read the server's current active quest into the panel that is open. */
  function refreshQuestPanel(): void {
    if (questPanel?.kind !== 'combat') return;
    const view = activeQuestFromWorld(
      world,
      questViewOptions(content, questPanel.active.questId),
    );
    if (view) {
      questPanel = { kind: 'combat', active: view };
      return;
    }
    // The server cleared the active quest: close a panel that has no subject.
    questPanel = null;
    dialogState = closeDialog(dialogState);
  }

  /** Open the shared dialog on the server's authoritative active quest. */
  function openCombat(questId: string): void {
    const view = activeQuestFromWorld(world, questViewOptions(content, questId));
    if (!view) {
      gestureRefusal('the server has no active quest');
      return;
    }
    questPanel = { kind: 'combat', active: view };
    const panel = combatDialog(questId);
    dialogState = openDialog(dialogState, panel.id, panel.kind, panel.title);
    drawInterface();
  }

  /** A chapter slot is a gesture: brief an unplayed quest or resume an active one. */
  function openQuestSlot(choice: QuestChoice): void {
    if (choice.active) {
      openCombat(choice.questId);
      return;
    }
    if (!choice.unlocked) {
      gestureRefusal('that quest is still locked');
      return;
    }
    const briefing = briefingView(choice, chosenDifficulty);
    questPanel = { kind: 'briefing', briefing };
    const panel = briefingDialog(briefing);
    dialogState = openDialog(dialogState, panel.id, panel.kind, panel.title);
    drawInterface();
  }

  /** The tutorial's drawing, or null when it is not running. */
  function tutorialProps(): TutorialOverlayProps | null {
    const step = tutorialRunning ? tutorial.current : null;
    if (!step) return null;
    return {
      step,
      position: tutorial.position + 1,
      total: tutorial.length,
      onNext: () => {
        void advanceTutorial();
      },
      onSkip: () => {
        void skipTutorial();
      },
    };
  }

  /**
   * Walk the tutorial one step forward and tell the server.
   *
   * The step the player **reaches** is the one sent, so the server's
   * furthest step is where a later session resumes. The last step has no
   * next one, and reaching it is finishing the tutorial: the last step
   * itself is sent, and the server marks it complete.
   */
  async function advanceTutorial(): Promise<{ ok: boolean; step: number | null }> {
    const current = tutorial.current;
    if (!current || !tutorialRunning) return { ok: false, step: null };
    tutorial.next();
    const next = tutorial.current;
    if (!next) tutorialRunning = false;
    const reached = next?.step ?? current.step;
    const result = await run([completeTutorial(reached)]);
    if (!result.ok) {
      // The server refused the record, so the client does not keep a
      // progress the server does not have.
      tutorial.previous();
      tutorialRunning = true;
    }
    drawInterface();
    return { ok: result.ok, step: tutorial.current?.step ?? null };
  }

  /** Skip the tutorial, which is finishing it outright. */
  async function skipTutorial(): Promise<{ ok: boolean }> {
    const last = tutorial.last;
    if (!last) return { ok: false };
    tutorial.finish();
    tutorialRunning = false;
    const result = await run([completeTutorial(last.step)]);
    drawInterface();
    return { ok: result.ok };
  }

  /**
   * The other players.
   *
   * The strip is the server's list, and it is fetched on its own: the
   * strip does not have to be right to the millisecond, and the
   * player's action should not wait for it.
   */
  async function refreshNeighbours(): Promise<void> {
    neighbours = await fetchNeighbours(signedIn);
    drawInterface();
  }

  /**
   * The build menu's item.
   *
   * Picking one **begins** a placement; it does not build anything.
   */
  function onPick(itemId: number, type: ItemType): void {
    // The menu entry carries its own wire type: a unit must be requested as
    // a unit, not as the building the old code hardcoded here.
    interaction.beginPlacement(itemId, type);
    placing = itemId;
    selected = null;
    selectedIso = null;
    drawInterface();
  }

  /** A local gesture refusal, surfaced on the same typed channel as the server's. */
  function gestureRefusal(refusal: string): void {
    feedback = [{ tone: 'error', text: `That action is not available (${refusal}).` }];
    drawInterface();
  }

  /** Upgrade the selected building. The server checks the level, tiles and cost. */
  function onUpgrade(): void {
    const gesture = interaction.upgradeSelected();
    if (!gesture.ok) {
      gestureRefusal(gesture.refusal);
      return;
    }
    void run([gesture.command]);
  }

  /** Hurry the selected building's construction, carrying the content's clicks. */
  function onFinish(): void {
    if (selected === null || selectedIso === null) return;
    const item = content.items.find((entry) => entry.id === selected);
    if (!item) return;
    void run([finishBuilding(selectedIso, item.clicks_to_build)]);
  }

  /** Train a unit in the selected building. The server prices it. */
  function onTrain(unitItemId: number): void {
    const gesture = interaction.trainSelected(unitItemId);
    if (!gesture.ok) {
      gestureRefusal(gesture.refusal);
      return;
    }
    void run([gesture.command]);
  }

  /** Take the finished unit out of the selected building's queue. */
  function onTake(): void {
    if (selectedIso === null) return;
    void run([takeTrainedUnit(selectedIso)]);
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
   * A goal's claim.
   *
   * The client sends the command and the server decides whether the goal
   * is really complete. Its answer redraws both the panel and the scene.
   */
  function onCommand(command: NativeCommand): void {
    void run([command]);
  }

  /**
   * The interface.
   *
   * It is drawn from the **same** world the scene is: one answer, one
   * drawing. The interface asks the server for nothing of its own.
   */
  // Reload recovery. The server's saved active quest is the only source for
  // the restored panel: the client reads it back after the world request and
  // hosts it in the same dialog the player was using before the restart.
  const restored = activeQuestState(world);
  if (restored?.questId) {
    const view = activeQuestFromWorld(world, questViewOptions(content, restored.questId));
    if (view) {
      questPanel = { kind: 'combat', active: view };
      const panel = combatDialog(restored.questId);
      dialogState = openDialog(dialogState, panel.id, panel.kind, panel.title);
    }
  }

  const ui = UI ? mountUi(UI, content, onPick, onCollect, onCommand) : null;
  drawInterface();
  void refreshNeighbours();

  // Countdowns are a presentation of the server's timestamps. Redraw once a
  // second while something is selected so they advance; the server still
  // decides when a unit is really finished or a build is done.
  window.setInterval(() => {
    if (selected !== null) drawInterface();
  }, 1000);

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
      selectedIso = null;
    } else {
      const definition = content.items.find((entry) => entry.id === found.itemId);
      const tuple = world.maps[0]?.items?.[String(found.isoId)];
      const build = finishView(
        Number(tuple?.[3] ?? 0),
        definition?.build_time ?? 0,
        definition?.clicks_to_build ?? 0,
        Math.floor(Date.now() / 1000),
      );
      const element = definition?.type === 'u' ? 'unit' : 'building';
      interaction.selectElement(
        found.isoId,
        found.itemId,
        element,
        element === 'building' && build !== null,
      );
      selected = found.itemId;
      selectedIso = found.isoId;
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
    // The answer's outcomes used to be discarded, so a refusal was silent.
    // Read them into the feedback channel before the redraw below; the
    // server stays the authority — these are only sentences, not state.
    feedback = result.ok
      ? feedbackFrom(result.response.outcomes, result.response.ok)
      : [{ tone: 'error', text: `The request failed (${result.reason}).` }];
    world = await fetchWorld();
    scene = buildScene(sceneItems(world, content), renderer.viewport, atlas);
    renderer.draw(scene);
    // The world the interface draws is the same one the quest panel reads.
    refreshQuestPanel();
    // The interface is redrawn from the same answer, so the numbers in
    // the top bar and the buildings on the map never disagree.
    drawInterface();
    const latencyMs = performance.now() - started;
    // The neighbour strip is refreshed on its own, outside the measured
    // window: the player's action should not wait for the list.
    void refreshNeighbours();
    return {
      ok: result.ok,
      latencyMs,
      sprites: scene.length,
      outcome: result.ok ? (result.response.outcomes[0] ?? null) : null,
    };
  }

  /**
   * Start a quest on the server, then redraw from the server's answer.
   *
   * A start is not a command: only the server may create an active quest and
   * seed its ledger. The client asks, then reads the state back.
   */
  async function startQuest(
    questId: string,
    difficulty?: number,
  ): Promise<QuestResult<QuestStartBody>> {
    const result = await startQuestOnServer(signedIn, questId, difficulty);
    world = await fetchWorld();
    drawInterface();
    return result;
  }

  /**
   * Apply one authoritative quest action.
   *
   * The answer already carries the server's ledger summary — its counters and
   * its elements' HP — so the client does not need a second world request to
   * know what the server decided. The panel is redrawn from that summary: no
   * extra request, and no local counter or HP value of the client's own.
   */
  async function questAction(
    questId: string,
    action: QuestActionRequest,
  ): Promise<QuestResult<QuestLedgerSummary>> {
    const result = await questActionOnServer(signedIn, questId, action);
    if (result.ok && result.body && questPanel?.kind === 'combat') {
      const view = activeQuestView(
        {
          questId: result.body.questId,
          counters: result.body.counters,
          elements: result.body.elements,
          events: result.body.events,
        },
        questViewOptions(content, questId),
      );
      if (view) questPanel = { kind: 'combat', active: view };
    }
    drawInterface();
    return result;
  }

  /** The briefing's Start button: ask the server, then host the live panel. */
  async function beginQuest(questId: string, difficulty: 1 | 2 | 3): Promise<void> {
    const result = await startQuest(questId, difficulty);
    if (!result.ok || !result.body) {
      feedback = [
        { tone: 'error', text: `The server refused the quest start (${result.status}).` },
      ];
      drawInterface();
      return;
    }
    chosenDifficulty = questDifficulty(difficulty);
    feedback = [{ tone: 'success', text: `The server started ${result.body.questId}.` }];
    openCombat(questId);
  }

  /**
   * One button of the combat panel.
   *
   * Strikes, events and the two-argument kill report are requests the player
   * makes; the Finish button sends `end_quest` and its result is read from the
   * answer. No branch here decides that the quest was won.
   */
  async function applyQuestGesture(questId: string, action: QuestActionChoice): Promise<void> {
    if (action.kind === 'strike' || action.kind === 'event') {
      const request: QuestActionRequest =
        action.kind === 'strike'
          ? { type: 'strike', ref: action.ref }
          : { type: action.action, ref: action.ref };
      const result = await questAction(questId, request);
      feedback = result.ok
        ? [{ tone: 'success', text: 'The server applied the quest action.' }]
        : [
            {
              tone: 'error',
              text: `The server refused the quest action (${result.status}).`,
            },
          ];
      drawInterface();
      return;
    }
    if (action.kind === 'kill-report') {
      // The native, strictly two-argument write. The server accepts it only
      // when its own ledger already marks the element dead.
      await run([reportQuestKill(action.ref)]);
      return;
    }
    // A player's gesture. The server's outcome — never a client condition —
    // becomes the result dialog, including its rewards when it answered any.
    const result = await run([endQuest(questId, chosenDifficulty)]);
    const view = questResultView(questId, result.outcome ?? null);
    questPanel = { kind: 'result', result: view };
    const panel = resultDialog(questId, view);
    dialogState = openDialog(dialogState, panel.id, panel.kind, panel.title);
    drawInterface();
  }

  // The debug handle. The end-to-end test drives the client through it,
  // and a developer can look at the client's own state in the console.
  const handle: ClientHandle = {
    session,
    send: (commands) => sendCommands(session.token, commands),
    run,
    showDialog: (id, kind, title) => {
      dialogState = openDialog(dialogState, id, kind, title);
      drawInterface();
    },
    dismissDialog: () => {
      dialogState = closeDialog(dialogState);
      drawInterface();
    },
    claimDailyBonus,
    buy,
    framesPerSecond: () => framesPerSecond,
    selectedItem: () => selected,
    tutorialStep: () => (tutorialRunning ? tutorial.current?.step ?? null : null),
    advanceTutorial,
    skipTutorial,
    startQuest,
    questAction,
    reportQuestKill,
    endQuest,
    activeQuest: () => activeQuestState(world),
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
