/**
 * Original-art textures: the adapter between a game sprite's identity and a
 * clean-room CC0 motif from `@swl/art`.
 *
 * This module is deliberately **pure** and **browser-safe**:
 *
 * - it imports only the browser entry of `@swl/art` (no `node:` built-in);
 * - the same identity always yields the same motif, on any machine;
 * - it produces `data:image/svg+xml;charset=utf-8,` URLs, so nothing is
 *   fetched and no file from the original game is ever read;
 * - the generated SVG has no external references of any kind.
 *
 * The renderer uses `motifFor` to choose a motif for each item on the map. A
 * later, richer motif catalogue can be handed to `createMotifMapper` without
 * changing the renderer: only the catalogue changes, not the identity
 * contract. Rasterising the SVG into a texture is the renderer's job; this
 * module never touches a DOM node.
 */
import { buildIcons, LICENCE } from '@swl/art/browser';

/** The exact URL prefix of every inline SVG this module produces. */
export const SVG_DATA_PREFIX = 'data:image/svg+xml;charset=utf-8,';

/** The generator's own dedication, carried with the artwork. */
export const ORIGINAL_ART_LICENCE: typeof LICENCE = LICENCE;

/** Which art the world renderer draws. */
export type ArtMode = 'atlas' | 'original';

/** The configuration shipped in `public/art-mode.json`. */
export interface ArtModeConfig {
  readonly mode?: unknown;
  readonly licence?: unknown;
}

/**
 * Pick the renderer's art mode.
 *
 * Only an explicit `original` selects original art. Anything else — an
 * absent file, a failed fetch, a future typo, or `atlas` — keeps the atlas
 * path, so the atlas build stays fully functional when its pages exist.
 */
export function resolveArtMode(config: ArtModeConfig | null | undefined): ArtMode {
  return config?.mode === 'original' ? 'original' : 'atlas';
}

/** Encode generated SVG text as an inline image source. No file is read. */
export function svgDataUri(svg: string): string {
  return `${SVG_DATA_PREFIX}${encodeURIComponent(svg)}`;
}

/** The identity of one piece of game art, as far as the client knows it. */
export interface ArtIdentity {
  /** The item's reference id (the map element's id). */
  readonly id?: string | number;
  /** The content item's id, when the caller has it. */
  readonly itemId?: string | number;
  /** The SWF and symbol the manifest names, when the caller has them. */
  readonly swfName?: string;
  readonly symbol?: string;
  /** The frame within the symbol, when the caller has it. */
  readonly frame?: string | number;
  /** The atlas region, used as a fallback when only the art is known. */
  readonly atlasX?: number;
  readonly atlasY?: number;
}

/** One clean-room motif, ready to be rasterised by the renderer. */
export interface OriginalMotif {
  readonly id: string;
  readonly svg: string;
  readonly src: string;
  readonly licence: typeof LICENCE;
}

/** A stable string key, independent of the order fields were supplied in. */
export function identityKey(identity: ArtIdentity): string {
  const field = (name: string, value: string | number | undefined): string =>
    value === undefined ? '' : `${name}=${String(value)};`;
  const region =
    identity.atlasX !== undefined && identity.atlasY !== undefined
      ? `${identity.atlasX},${identity.atlasY}`
      : undefined;
  return (
    field('id', identity.id) +
    field('itemId', identity.itemId) +
    field('swf', identity.swfName) +
    field('symbol', identity.symbol) +
    field('frame', identity.frame) +
    field('atlas', region)
  );
}

/** FNV-1a, 32-bit: a small, stable hash of the identity key. */
function hashOf(key: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < key.length; i += 1) {
    hash ^= key.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/**
 * Build a deterministic identity -> motif mapping over `catalog`.
 *
 * Passing a different catalogue is the extension point for richer motifs:
 * the renderer keeps calling `motifFor(identity)` and never learns where the
 * motif came from. Within one catalogue the same key always picks the same
 * entry, and an empty catalogue yields null rather than throwing.
 */
export function createMotifMapper(
  catalog: readonly OriginalMotif[],
): (identity: ArtIdentity) => OriginalMotif | null {
  if (catalog.length === 0) return () => null;
  return (identity) => catalog[hashOf(identityKey(identity)) % catalog.length] ?? null;
}

/** Build the default catalogue from the generator's in-memory artefacts. */
export function buildDefaultMotifs(): readonly OriginalMotif[] {
  const decoder = new TextDecoder();
  const motifs: OriginalMotif[] = [];
  for (const file of buildIcons()) {
    if (!file.path.startsWith('icons/') || !file.path.endsWith('.svg')) continue;
    if (file.path === 'icons/sprite-sheet.svg') continue;
    const id = file.path.slice('icons/'.length, -'.svg'.length);
    const svg = decoder.decode(file.bytes);
    motifs.push({ id, svg, src: svgDataUri(svg), licence: ORIGINAL_ART_LICENCE });
  }
  return motifs;
}

/** The generator's motifs, in the generator's own order. */
export const DEFAULT_MOTIFS: readonly OriginalMotif[] = buildDefaultMotifs();

/** The mapping the renderer uses. */
export const motifFor = createMotifMapper(DEFAULT_MOTIFS);

/**
 * Pure decision: the atlas page to request next, or null.
 *
 * Original art mode never requests a page; atlas mode requests one that is
 * neither loaded, pending nor known-missing. Keeping this decision pure
 * makes the "atlas mode still fetches" behaviour unit-testable without a GPU.
 */
export function atlasPageRequest(
  mode: ArtMode,
  file: string,
  known: ReadonlySet<string>,
): string | null {
  return mode === 'atlas' && !known.has(file) ? file : null;
}
