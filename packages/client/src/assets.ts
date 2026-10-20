/**
 * The asset bundle.
 *
 * The client loads one manifest and gets:
 *
 * - a **build id**, one hash over every asset's content hash. It is
 *   appended to every asset URL, so a changed asset means a changed URL
 *   and **a stale cache is impossible** rather than unlikely.
 * - the **index**: which atlas page each sprite is on, and where in it.
 *   The renderer should not have to know how the atlases are laid out.
 * - the sounds, keyed by their content hash, so the client asks for a
 *   sound by what it is rather than by where it happens to live.
 */

/** Where a sprite's art sits in an atlas. */
export interface SpriteRegion {
  /** The content hash of the image, which is the sprite's identity. */
  hash: string;
  /** The atlas page's file name. */
  file: string;
  x: number;
  y: number;
  width: number;
  height: number;
  /** Where the art was cut from the original image. */
  trim: { x: number; y: number; width: number; height: number } | null;
  /** How many frames the sprite has. */
  frames: number;
}

/** One asset. */
export interface BundleAsset {
  /** Where the asset lives, relative to the asset root. */
  path: string;
  bytes: number;
  sha256: string;
  /** Whether the asset's bytes live inside a SWF rather than in a file. */
  embedded?: boolean;
  source?: string;
}

/** The bundle the client loads. */
export interface AssetBundle {
  /** The build id: one hash over every asset's content hash. */
  buildId: string;
  counts: {
    images: number;
    sounds: number;
    sprites: number;
    atlases: number;
  };
  images: Record<string, BundleAsset>;
  sounds: Record<string, BundleAsset>;
  sprites: Record<string, SpriteRegion>;
  atlases: Record<string, { file: string; x: number; y: number; width: number; height: number }>;
}

/**
 * The URL of an atlas page.
 *
 * The build id is the cache buster: the page's contents change only when
 * the assets change, so the id changes only then, and the browser
 * fetches the new page exactly when it has to.
 */
export function atlasUrl(bundle: AssetBundle, file: string, base = '/assets/'): string {
  return `${base}atlases/${file}?v=${bundle.buildId}`;
}

/** The URL of a sound. */
export function soundUrl(
  bundle: AssetBundle,
  sha256: string,
  base = '/assets/',
): string | null {
  const sound = bundle.sounds[sha256];
  if (!sound) return null;
  return `${base}${sound.path}?v=${bundle.buildId}`;
}

/** The URL of an image. */
export function imageUrl(
  bundle: AssetBundle,
  sha256: string,
  base = '/assets/',
): string | null {
  const image = bundle.images[sha256];
  if (!image) return null;
  return `${base}${image.path}?v=${bundle.buildId}`;
}

/** A sprite's region, or null when the sprite is not in the bundle. */
export function spriteOf(bundle: AssetBundle, name: string): SpriteRegion | null {
  return bundle.sprites[name] ?? null;
}

/**
 * The position the art is drawn at.
 *
 * The trimmed region is the art's own top-left corner, so it is drawn at
 * the tile's position **less** the trim offset. Getting this wrong moves
 * every building up and to the left by however much transparent margin
 * was cut away.
 */
export function drawPosition(
  region: SpriteRegion,
  tileX: number,
  tileY: number,
): { x: number; y: number } {
  const trim = region.trim;
  return {
    x: tileX - (trim ? trim.x : 0),
    y: tileY - (trim ? trim.y : 0),
  };
}

/**
 * Whether the bundle is usable.
 *
 * A bundle with no build id would serve stale assets without saying so,
 * so it is refused rather than used.
 */
export function isUsable(bundle: AssetBundle | null | undefined): bundle is AssetBundle {
  return Boolean(
    bundle &&
      typeof bundle.buildId === 'string' &&
      bundle.buildId.length === 64 &&
      bundle.sprites !== undefined &&
      bundle.images !== undefined,
  );
}
