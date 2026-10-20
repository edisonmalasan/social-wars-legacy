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
 */
import { Application, Assets, Container, Rectangle, Sprite, Texture } from 'pixi.js';

import type { FrameManifest, Viewport } from '@swl/client';

import type { SceneSprite } from './scene.ts';

/** The stage's size, in the client's own terms. */
export const STAGE_WIDTH = 760;
export const STAGE_HEIGHT = 600;

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
  private readonly options: RendererOptions;

  private constructor(app: Application, options: RendererOptions) {
    this.app = app;
    this.options = options;
  }

  /** Start the renderer and load the atlas. */
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
    await renderer.loadAtlas();
    return renderer;
  }

  /** Load the atlas pages and build the textures for the regions. */
  private async loadAtlas(): Promise<void> {
    const files = new Set<string>();
    for (const image of Object.values(this.options.manifest.images ?? {})) {
      if (image.atlas) files.add(image.atlas.file);
    }

    for (const file of files) {
      const texture = await Assets.load(`${this.options.atlasBase}/${file}`);
      this.pages.set(file, texture as Texture);
    }
  }

  /**
   * Draw a scene.
   *
   * The sprites are added in the scene's order, which is the depth
   * order, and PixiJS draws a container's children back to front. The
   * depth is **not** given to PixiJS as a `zIndex`, because the scene
   * has already sorted them, and sorting twice would be sorting once too
   * many.
   */
  draw(scene: readonly SceneSprite[]): void {
    this.world.removeChildren();

    for (const sprite of scene) {
      const drawn = this.spriteFor(sprite);
      if (drawn) this.world.addChild(drawn);
    }
  }

  /** One sprite, or null when the art is not in the atlas. */
  private spriteFor(scene: SceneSprite): Sprite | null {
    if (!scene.art) return null;
    const page = this.pages.get(scene.art.atlas.file);
    if (!page) return null;

    const region = scene.art.atlas;
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
  fit(element: HTMLElement): number {
    const available = Math.min(
      element.clientWidth / STAGE_WIDTH,
      element.clientHeight / STAGE_HEIGHT,
    );
    const scale = Math.max(1, Math.floor(available * 100) / 100);
    element.style.transform = `translate(-50%, -50%) scale(${scale})`;
    return scale;
  }

  /** The viewport the scene is drawn in. */
  get viewport(): Viewport {
    return { topX: 0, topY: 0, buildOutlineOffsetY: 0 };
  }
}
