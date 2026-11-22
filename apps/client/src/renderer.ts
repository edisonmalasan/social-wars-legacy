/**
 * The renderer.
 *
 * **PixiJS v8** draws the world: thousands of sprites, filtered and
 * animated, on a WebGL2 canvas. React draws the interface, over the
 * top (see ADR 4).
 *
 * The renderer is deliberately **thin**. Everything that can be decided
 * without a GPU is decided in `scene.ts` — the projection, the depth
 * sort and the frame choice — so that the rules can be tested without
 * one. What is left here is the drawing.
 *
 * ## Two art modes, chosen before the first draw
 *
 * **Atlas mode** fetches the original game's atlas pages on demand. There
 * are 3 590 pages, 31.8 GB of them, and a scene of a few hundred sprites
 * touches a few dozen. So a page is fetched when a sprite needs it and not
 * before, and no more than a few are fetched at once. Loading them all up
 * front would fetch 31.8 GB to draw a village. This path stays intact for
 * builds that ship the pages.
 *
 * **Original art mode** draws clean-room CC0 motifs instead. The motifs
 * are generated in the browser from `@swl/art`, rasterised into canvases
 * and uploaded as textures. Nothing is fetched at all: in this mode the
 * renderer never asks for an atlas page, so a build without the pages has
 * no missing resources and makes no failing request. The mode is fixed at
 * construction, never probed with a request that could itself fail.
 */
import { Application, Assets, Container, Rectangle, Sprite, Texture } from 'pixi.js';

import type { CameraState, FrameManifest, Viewport, ViewportSize } from '@swl/client';

import {
  atlasPageRequest,
  DEFAULT_MOTIFS,
  motifFor,
  svgDataUri,
  type ArtMode,
} from './originalart-textures.ts';
import type { SceneSprite } from './scene.ts';
import { STAGE_HEIGHT, STAGE_WIDTH } from '@swl/client';
import { viewportOf, type StageLayout } from '@swl/client';
import { initialCamera } from '@swl/client';
import { fitStage } from './viewport.ts';
import { TouchGestureGuard, type TouchPoint } from './touch.ts';

export { STAGE_HEIGHT, STAGE_WIDTH } from '@swl/client';
export type { ArtMode } from './originalart-textures.ts';

/** How many atlas pages are fetched at once. */
export const MAX_CONCURRENT_PAGES = 8;

/** The side of a generated motif, in stage pixels. */
const MOTIF_SIZE = 64;

/**
 * Rasterise one generated SVG into a canvas.
 *
 * WebKit does not reliably upload an SVG data URL straight to a WebGL
 * texture, so the SVG is decoded through an `HTMLImageElement` and painted
 * into a plain canvas; the canvas is what Pixi uploads. A decode failure
 * still yields a self-contained mark, so a flaky engine cannot turn into a
 * missing texture or a console error. No network request is ever made:
 * the image's source is a `data:` URL produced by the adapter.
 */
async function motifCanvas(svg: string): Promise<HTMLCanvasElement> {
  const canvas = document.createElement('canvas');
  canvas.width = MOTIF_SIZE;
  canvas.height = MOTIF_SIZE;
  const context = canvas.getContext('2d');
  if (!context) return canvas;
  try {
    const image = new Image();
    image.decoding = 'sync';
    image.src = svgDataUri(svg);
    if (typeof image.decode === 'function') {
      await image.decode();
    } else {
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve();
        image.onerror = () => reject(new Error('the SVG image could not be decoded'));
      });
    }
    context.drawImage(image, 0, 0, MOTIF_SIZE, MOTIF_SIZE);
  } catch {
    // A plain, original mark: still a real texture, and still no fetch.
    context.fillStyle = '#2c4654';
    context.fillRect(0, 0, MOTIF_SIZE, MOTIF_SIZE);
    context.fillStyle = '#e9a63f';
    context.fillRect(8, 8, MOTIF_SIZE - 16, MOTIF_SIZE - 16);
  }
  return canvas;
}

/** What the renderer needs to start. */
export interface RendererOptions {
  /** The element the canvas goes into. */
  element: HTMLElement;
  /** The frame manifest, for the atlas. */
  manifest: FrameManifest;
  /** Where the atlas pages are. */
  atlasBase: string;
  /** Which art to draw: fetched atlas pages or generated CC0 motifs. */
  artMode: ArtMode;
}

/** The world renderer. */
export class WorldRenderer {
  private readonly app: Application;
  private readonly world = new Container();
  private readonly pages = new Map<string, Texture>();
  private readonly pending = new Map<string, Promise<void>>();
  private readonly missing = new Set<string>();
  /** One texture per generated motif, ready before the first scene is drawn. */
  private readonly originalTextures = new Map<string, Texture>();
  private readonly options: RendererOptions;
  private readonly queue: string[] = [];
  private scene: readonly SceneSprite[] = [];
  private state: CameraState = initialCamera();

  /** Called when a page arrives, so the scene can be drawn again. */
  onPageLoaded: (() => void) | null = null;

  /**
   * Called when the player clicks the map.
   *
   * The coordinates are the canvas's own, so the click is in the
   * stage's pixels however the stage is scaled.
   */
  onClick: ((x: number, y: number) => void) | null = null;

  private constructor(app: Application, options: RendererOptions) {
    this.app = app;
    this.options = options;
  }

  /**
   * Rasterise every generated motif once, before any scene is drawn.
   *
   * `draw()` is synchronous, so the textures must already exist by the time
   * it runs. Decoding is done here, while `start()` is awaiting anyway.
   */
  private async prepareOriginalArt(): Promise<void> {
    for (const motif of DEFAULT_MOTIFS) {
      const canvas = await motifCanvas(motif.svg);
      this.originalTextures.set(motif.id, Texture.from(canvas));
    }
  }

  /** Start the renderer. */
  static async start(options: RendererOptions): Promise<WorldRenderer> {
    const app = new Application();
    await app.init({
      width: STAGE_WIDTH,
      height: STAGE_HEIGHT,
      background: '#10131a',
      antialias: true,
      // The game's art is pixel art at 1:1, so the canvas is not scaled
      // by the renderer: the **stage** is scaled, and the art keeps its
      // pixels sharp only at whole numbers.
      resolution: 1,
      autoDensity: false,
      preference: 'webgl',
    });

    options.element.appendChild(app.canvas);

    const renderer = new WorldRenderer(app, options);

    // Original art needs no atlas pages, but its textures must exist before
    // the first draw. Atlas mode needs no preparation: pages arrive later.
    if (options.artMode === 'original') await renderer.prepareOriginalArt();

    // The gesture guard. A mouse click keeps the original, immediate path;
    // touch is deferred to release so a pinch or the second tap of a double
    // tap cannot fire a second command. The guard only decides *whether to
    // ask* — the server still decides what happens (see touch.ts).
    const touchGuard = new TouchGestureGuard();
    const isTouch = (event: PointerEvent): boolean =>
      event.pointerType === 'touch' || event.pointerType === 'pen';

    // The click, in the canvas's own pixels. The stage is scaled by a
    // CSS transform, so the position is taken back into the canvas's
    // coordinates rather than the window's.
    const pointOf = (event: PointerEvent): TouchPoint | null => {
      const rect = app.canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      return {
        x: ((event.clientX - rect.left) / rect.width) * app.canvas.width,
        y: ((event.clientY - rect.top) / rect.height) * app.canvas.height,
      };
    };

    app.canvas.addEventListener('pointerdown', (event) => {
      const point = pointOf(event);
      if (!point) return;
      if (!isTouch(event)) {
        renderer.onClick?.(point.x, point.y);
        return;
      }
      // Capture so a release just outside the canvas still arrives. A
      // synthetic event has no active pointer to capture, so ignore that.
      try {
        app.canvas.setPointerCapture(event.pointerId);
      } catch {
        /* synthetic pointer — no capture needed */
      }
      touchGuard.down(event.pointerId, point);
    });

    app.canvas.addEventListener('pointermove', (event) => {
      if (!isTouch(event)) return;
      const point = pointOf(event);
      if (point) touchGuard.move(event.pointerId, point);
    });

    app.canvas.addEventListener('pointerup', (event) => {
      if (!isTouch(event)) return;
      const point = pointOf(event);
      if (!point) {
        touchGuard.cancel();
        return;
      }
      if (touchGuard.up(event.pointerId, event.timeStamp, point)) {
        renderer.onClick?.(point.x, point.y);
      }
    });

    app.canvas.addEventListener('pointercancel', (event) => {
      if (isTouch(event)) touchGuard.cancel();
    });

    return renderer;
  }

  /**
   * Draw a scene.
   *
   * The sprites are added in the scene's order, which is the depth
   * order, and PixiJS draws a container's children back to front. The
   * depth is **not** given to PixiJS as a `zIndex`, because the scene
   * has already sorted them, and sorting twice would be sorting once too
   * many.
   *
   * In atlas mode a sprite whose page has not arrived yet is not drawn,
   * and the page is fetched; when it arrives the scene is drawn again.
   * In original art mode every sprite is drawn from a motif rasterised
   * before the first draw, with no page request at all.
   */
  draw(scene: readonly SceneSprite[]): void {
    this.scene = scene;
    this.world.removeChildren();

    for (const sprite of scene) {
      const drawn = this.spriteFor(sprite);
      if (drawn) this.world.addChild(drawn);
    }
  }

  /** One sprite, or null when its art is not available yet. */
  private spriteFor(scene: SceneSprite): Sprite | null {
    if (this.options.artMode === 'original') {
      // No page, no Assets.load: the motif is a pure function of the item's
      // identity and the texture was rasterised at start-up.
      const motif = motifFor({
        id: scene.id,
        frame: scene.frame?.frame,
        atlasX: scene.art?.atlas.x,
        atlasY: scene.art?.atlas.y,
      });
      const texture = motif ? this.originalTextures.get(motif.id) : undefined;
      if (!texture) return null;
      const sprite = new Sprite(texture);
      sprite.anchor.set(0.5, 0.5);
      sprite.x = scene.x;
      sprite.y = scene.y - scene.elevation;
      return sprite;
    }

    if (!scene.art) return null;
    const region = scene.art.atlas;
    const page = this.pages.get(region.file);
    if (!page) {
      this.requestPage(region.file);
      return null;
    }

    const texture = new Texture({
      source: page.source,
      frame: new Rectangle(region.x, region.y, region.width, region.height),
    });

    const sprite = new Sprite(texture);
    // The projection gives the item's **top corner**, and the art's
    // anchor is the top corner of the *trimmed* image, so the trim
    // offset has to come back off.
    const trim = scene.art.trim;
    sprite.x = scene.x + (trim ? trim.x : 0);
    sprite.y = scene.y + (trim ? trim.y : 0) - scene.elevation;
    return sprite;
  }

  /** Fetch a page, at most a few at a time. Original art never fetches. */
  private requestPage(file: string): void {
    const known = new Set([...this.pages.keys(), ...this.pending.keys(), ...this.missing]);
    const next = atlasPageRequest(this.options.artMode, file, known);
    if (!next) return;
    if (!this.queue.includes(next)) this.queue.push(next);
    this.pump();
  }

  /** Start as many queued fetches as the limit allows. */
  private pump(): void {
    while (this.pending.size < MAX_CONCURRENT_PAGES && this.queue.length > 0) {
      const file = this.queue.shift()!;
      const promise = Assets.load(`${this.options.atlasBase}/${file}`)
        .then((texture) => {
          this.pages.set(file, texture as Texture);
        })
        .catch(() => {
          this.missing.add(file);
        })
        .then(() => {
          this.pending.delete(file);
          // The scene is drawn again, so the sprites that were waiting for
          // this page appear.
          this.draw(this.scene);
          this.onPageLoaded?.();
          this.pump();
        });
      this.pending.set(file, promise);
    }
  }

  /** The atlas pages that could not be loaded. */
  get missingAtlasPages(): string[] {
    return [...this.missing];
  }

  /** How many pages have been fetched. */
  get loadedPages(): number {
    return this.pages.size;
  }

  /** Which art mode this renderer was started in (read-only). */
  get artMode(): ArtMode {
    return this.options.artMode;
  }

  /**
   * How many sprites were actually added to the world container.
   *
   * This is not the scene's length: a sprite waiting for a page is in the
   * scene but not drawn. In original art mode it is the number of generated
   * motifs on the stage, which is what an end-to-end check can assert.
   */
  get drawnSprites(): number {
    return this.world.children.length;
  }

  /** The canvas, for the interface to sit over. */
  get canvas(): HTMLCanvasElement {
    return this.app.canvas;
  }

  /**
   * Run the render loop.
   *
   * The game is animated, so the client has to keep drawing: the loop is
   * what advances the sprites and what keeps the screen alive between
   * the world's changes.
   *
   * The callback is given the **frames per second** the loop is
   * running at, so the client can measure it and say whether the frame
   * rate holds.
   */
  run(onTick: (framesPerSecond: number) => void): void {
    let last = performance.now();
    let frames = 0;
    let elapsed = 0;

    this.app.ticker.add(() => {
      const now = performance.now();
      frames += 1;
      elapsed += now - last;
      last = now;
      // The rate is measured over a second, because a frame's own
      // duration says nothing about the rate.
      if (elapsed >= 1000) {
        onTick((frames * 1000) / elapsed);
        frames = 0;
        elapsed = 0;
      }
    });
  }

  /**
   * Fit the stage to the window.
   *
   * The stage is a fixed 760 by 600 and it is **scaled** to fit, rather
   * than reflowed: the game's layout is not fluid, and reflowing it
   * would put the panels on top of each other. The scale is a **whole
   * number** where it can be, so the pixel art stays sharp.
   */
  fit(element: HTMLElement, viewport: ViewportSize): StageLayout {
    // The element is a fixed 760x600, so its own clientWidth/clientHeight
    // describe the stage and would give a scale of 1 everywhere. Fit to the
    // window instead, and apply only the scale to the element (its internal
    // 760x600 coordinate space is unchanged).
    const layout = fitStage(element, viewport);
    element.style.transform = `translate(-50%, -50%) scale(${layout.scale})`;
    return layout;
  }

  /** The viewport the scene is drawn in. */
  get viewport(): Viewport {
    return viewportOf(this.camera);
  }

  /**
   * The camera.
   *
   * The scene is drawn in the camera's viewport, so moving the camera
   * moves the map and the scene is drawn again.
   */
  get camera(): CameraState {
    return this.state;
  }

  /** Move the camera, and draw the scene again. */
  setCamera(camera: CameraState): void {
    this.state = camera;
    this.draw(this.scene);
  }
}
