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
 * ## The atlas pages are loaded on demand
 *
 * There are 3 590 atlas pages, 31.8 GB of them, and a scene of a few
 * hundred sprites touches a few dozen. So a page is fetched when a
 * sprite needs it and not before, and no more than a few are fetched at
 * once. Loading them all up front would fetch 31.8 GB to draw a
 * village.
 */
import { Application, Assets, Container, Rectangle, Sprite, Texture } from 'pixi.js';

import type { FrameManifest, Viewport } from '@swl/client';

import type { SceneSprite } from './scene.ts';
import { STAGE_HEIGHT, STAGE_WIDTH } from '@swl/client';
import { stageLayout, type StageLayout } from '@swl/client';

export { STAGE_HEIGHT, STAGE_WIDTH } from '@swl/client';

/** How many atlas pages are fetched at once. */
export const MAX_CONCURRENT_PAGES = 8;

/** What the renderer needs to start. */
export interface RendererOptions {
  /** The element the canvas goes into. */
  element: HTMLElement;
  /** The frame manifest, for the atlas. */
  manifest: FrameManifest;
  /** Where the atlas pages are. */
  atlasBase: string;
}

/** The world renderer. */
export class WorldRenderer {
  private readonly app: Application;
  private readonly world = new Container();
  private readonly pages = new Map<string, Texture>();
  private readonly pending = new Map<string, Promise<void>>();
  private readonly missing = new Set<string>();
  private readonly options: RendererOptions;
  private readonly queue: string[] = [];
  private scene: readonly SceneSprite[] = [];

  /** Called when a page arrives, so the scene can be drawn again. */
  onPageLoaded: (() => void) | null = null;

  private constructor(app: Application, options: RendererOptions) {
    this.app = app;
    this.options = options;
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
    return new WorldRenderer(app, options);
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
   * A sprite whose page has not arrived yet is not drawn, and the page
   * is fetched. When it arrives the scene is drawn again.
   */
  draw(scene: readonly SceneSprite[]): void {
    this.scene = scene;
    this.world.removeChildren();

    for (const sprite of scene) {
      const drawn = this.spriteFor(sprite);
      if (drawn) this.world.addChild(drawn);
    }
  }

  /** One sprite, or null when its page has not arrived. */
  private spriteFor(scene: SceneSprite): Sprite | null {
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

  /** Fetch a page, at most a few at a time. */
  private requestPage(file: string): void {
    if (this.pages.has(file) || this.pending.has(file) || this.missing.has(file)) return;
    if (!this.queue.includes(file)) this.queue.push(file);
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

  /** The canvas, for the interface to sit over. */
  get canvas(): HTMLCanvasElement {
    return this.app.canvas;
  }

  /**
   * Fit the stage to the window.
   *
   * The stage is a fixed 760 by 600 and it is **scaled** to fit, rather
   * than reflowed: the game's layout is not fluid, and reflowing it
   * would put the panels on top of each other. The scale is a **whole
   * number** where it can be, so the pixel art stays sharp.
   */
  fit(element: HTMLElement): StageLayout {
    const layout = stageLayout({
      width: element.clientWidth || window.innerWidth,
      height: element.clientHeight || window.innerHeight,
    });
    element.style.transform = `translate(-50%, -50%) scale(${layout.scale})`;
    return layout;
  }

  /** The viewport the scene is drawn in. */
  get viewport(): Viewport {
    return { topX: 0, topY: 0, buildOutlineOffsetY: 0 };
  }
}
